"""Normalize closed native/source evidence for paginated VChart reports.

Only copies immutable raw images and preserves their fingerprints. Source
parse errors and explicit native restrictions remain separate classifications.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
from functools import lru_cache


def identity(path):
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}


@lru_cache(maxsize=8)
def closed_manifest(parent):
    return read(parent/'run.json'),identity(parent/'run.json')


def evidence(path):
    """Bind every original byte to a closed run, never to a mutable checkout."""
    path=path.resolve(strict=True)
    parent=next((p for p in (path,*path.parents) if (p/'run.json').is_file()),None)
    if parent is None:raise ValueError('Evidence must belong to a closed Run: '+str(path))
    manifest,manifest_identity=closed_manifest(parent)
    if manifest.get('status')=='RUNNING' or not manifest.get('finishedAtUtc'):
        raise ValueError('Evidence Run is not closed: '+str(parent))
    relative=path.relative_to(parent).as_posix()
    if path.is_symlink() or manifest.get('artifacts',{}).get(relative)!=identity(path):
        raise ValueError('Closed Run artifact fingerprint differs: '+str(path))
    return {'run':str(parent),'manifest':manifest_identity,
            'runStatus':manifest['status'],'sourceTreeSha256':manifest.get('source',{}).get('sourceTreeSha256'),
            'sourceUnchanged':manifest.get('sourceUnchanged'),
            'path':relative,**identity(path)}


def unique(rows,label):
    result={}
    for row in rows:
        key=row['id']
        if not isinstance(key,str) or not key or key.casefold() in {k.casefold() for k in result}:
            raise ValueError('Duplicate/invalid '+label+' ID: '+str(key))
        result[key]=row
    return result


def read(path):
    return json.loads(path.read_text('utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')


def copy(source, target):
    proof=evidence(source)
    shutil.copyfile(source,target)
    if identity(source)!=identity(target):raise ValueError('Raw byte copy drift')
    return proof


def child(root, name):
    path = root / name
    if Path(name).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Evidence case escaped root')
    path.mkdir(parents=True, exist_ok=False)
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--supplier', type=Path, required=True)
    p.add_argument('--bridge', type=Path, required=True)
    p.add_argument('--bridge-fixtures', type=Path, required=True)
    p.add_argument('--mermaid', type=Path, required=True)
    p.add_argument('--oracle', type=Path, required=True)
    p.add_argument('--mermaid-fixtures', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    provenance={}
    def copied(source,target):
        provenance[target.relative_to(args.out).as_posix()]=copy(source,target)
    for root,name in [(args.supplier,'result.json'),(args.bridge,'result.json'),
                      (args.mermaid,'results.json'),(args.oracle,'vchart-mermaid-source-summary.json')]:
        evidence(root/name)
    bridge_out = args.out / 'bridge'
    bridge_out.mkdir()
    fixtures = unique(read(args.bridge_fixtures)['cases'],'bridge fixture')
    native_bridge=unique(read(args.bridge/'result.json')['cases'],'bridge result')
    if set(fixtures)!=set(native_bridge) or len(fixtures)!=68:
        raise ValueError('Complete bridge68 denominator differs')
    bridge_rows = []
    for row in read(args.bridge / 'result.json')['cases']:
        fixture = fixtures[row['id']]
        folder = child(bridge_out, row['id'])
        original = Path(fixture['origin']['casePath']).relative_to('tests/cases')
        expected_png = args.supplier / original / 'expected.png'
        assert hashlib.sha256(expected_png.read_bytes()).hexdigest() == fixture['origin']['pngSha256']
        copied(expected_png, folder / 'expected.png')
        for filename in ('actual.png', 'actual.scene.json', 'spec.json', 'result.json'):
            copied(args.bridge / row['id'] / filename, folder / filename)
        scene=base64.b64decode(fixture['origin']['sceneBytesBase64'],validate=True)
        if hashlib.sha256(scene).hexdigest()!=fixture['origin']['sceneSha256']:
            raise ValueError('Bridge source scene fingerprint differs')
        copied(args.supplier/original/'expected.scene.json',folder/'expected.scene.json')
        if (folder/'expected.scene.json').read_bytes()!=scene:
            raise ValueError('Source scene bytes differ from source capture fixture')
        if read(folder/'spec.json')!=fixture['spec']:raise ValueError('Bridge spec differs from frozen source fixture')
        bridge_rows.append({**row, 'origin': {k: v for k, v in fixture['origin'].items() if 'Base64' not in k}})
    write(bridge_out / 'result.json', {'results': bridge_rows,'sourceFixture':identity(args.bridge_fixtures)})
    mermaid_out = args.out / 'mermaid'
    mermaid_out.mkdir()
    source_rows = unique(read(args.oracle / 'vchart-mermaid-source-summary.json')['cases'],'Mermaid oracle')
    doc = read(args.mermaid_fixtures)
    fixture_rows = unique(doc['cases'] + doc.get('unsupportedCases', []),'Mermaid fixture')
    native_mermaid=unique(read(args.mermaid/'results.json')['cases'],'Mermaid native')
    if set(fixture_rows)!=set(source_rows) or set(fixture_rows)!=set(native_mermaid) or len(fixture_rows)!=42:
        raise ValueError('Complete Mermaid42 denominator differs')
    mermaid_rows = []
    for original in read(args.mermaid / 'results.json')['cases']:
        row = dict(original)
        id = row['id']
        fixture = fixture_rows[id]
        source_row = source_rows[id]
        folder = child(mermaid_out, id)
        (folder / 'input.mmd').write_text(fixture['source'], 'utf-8')
        for suffix in ('png', 'svg', 'pdf', 'jpg', 'webp', 'scene.json', 'diagnostic.json'):
            original_file=args.mermaid/(id+'.'+suffix)
            if original_file.exists():copied(original_file,folder/('actual.'+suffix))
        for suffix in ('png', 'svg', 'json', 'error.json'):
            original_file=args.oracle/(id+'.'+suffix)
            if original_file.exists():copied(original_file,folder/('expected.'+suffix))
        if row['status']=='CHECKS_PASSED' and not (folder/'actual.png').exists():
            raise ValueError('Rendered native case is missing PNG: '+id)
        if source_row['status']=='captured' and not (folder/'expected.png').exists():
            raise ValueError('Captured source case is missing PNG: '+id)
        if source_row['status']!='captured' and not (folder/'expected.error.json').exists():
            raise ValueError('Source rejection is missing its diagnostic: '+id)
        errors = []
        source_json = args.oracle / (id + '.json')
        if source_json.exists():
            visible = re.sub(r'\s+', '', ''.join(str(t.get('text') or '') for t in read(source_json).get('texts', [])))
            for text in fixture.get('expectedText', []):
                if re.sub(r'\s+', '', text) not in visible:
                    errors.append('source-visible-text-disagrees:' + text)
        if not source_row['expectationMatches']:
            errors.append('original-expectation-mismatch')
        if row['status'] not in ('CHECKS_PASSED', 'EXPECTED_ERROR', 'DIAGNOSTIC_ERROR'):
            errors.append('native-check-failed')
        row.update(source=source_row, comparisonErrors=errors,
                   status='REVIEW_FAILURE' if errors else row['status'])
        row['classification']=('COMPARISON_FAILURE' if errors else
            'EXPLICIT_NATIVE_RESTRICTION' if row.get('nativeRestrictionOnly') else
            'SOURCE_REJECTED_INPUT' if source_row['status']!='captured' else
            'EXPLICIT_NATIVE_DIAGNOSTIC' if row['status']=='DIAGNOSTIC_ERROR' else
            'RENDERED_AUTOMATED_CHECKS_PASSED')
        write(folder / 'result.json', row)
        mermaid_rows.append(row)
    write(mermaid_out / 'result.json', {'results': mermaid_rows})
    result = {'bridge': {'cases': len(bridge_rows), 'failed': sum(r['status'] != 'PASS' for r in bridge_rows)},
              'mermaid': {'cases': len(mermaid_rows), 'failed': sum(bool(r['comparisonErrors']) for r in mermaid_rows)}}
    write(args.out / 'result.json', result)
    write(args.out/'raw-provenance.json',{'schema':'py-mermaid-vchart-normalized-provenance/v1',
          'functionalStatus':'NOT_REEVALUATED','rawAssets':provenance,
          'fixtures':{'bridge':identity(args.bridge_fixtures),'mermaid':identity(args.mermaid_fixtures)}})
    print(json.dumps(result))
    return int(result['bridge']['failed'] or result['mermaid']['failed'])


if __name__ == '__main__':
    raise SystemExit(main())
