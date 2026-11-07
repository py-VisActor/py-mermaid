"""Verify immutable DSL matrix/install evidence, without executing products.

PASS binds the retained static contract and its actual denominators. It never
claims exhaustive provider branches, or closes the 22 older Mermaid gaps.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile
from xml.etree import ElementTree

from run_support import ROOT, file_identity, verify_run, write_json

PROFILES = ('cpu', 'auto', 'gpu')
GROUPS = {'supplier': 225, 'representative': 68, 'example': 8}
REGRESSIONS = ('bootstrap', 'dependencies', 'f011', 'f012', 'f013', 'f014',
               'math', 'bulk', 'html_host', 'pixel_compare', 'tooling')
UNIT_NAMES = tuple('dsl-unit-' + x for x in ('syntax', 'compiler', 'api', 'cli', 'resources'))
REQUIRED = {'freeze-independent-source-corpus', 'comparison-negative-controls',
            'existing-vchart-contracts', *UNIT_NAMES,
            *('dsl-matrix-' + x for x in PROFILES),
            *('regression-' + x for x in REGRESSIONS)}


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def relative(path):
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def proof(path):
    return {'path': relative(path), **file_identity(Path(path))}


def child(base, name):
    name = Path(name)
    require(not name.is_absolute() and '..' not in name.parts, 'Unsafe evidence path: ' + str(name))
    original = base / name
    result = original.resolve(strict=True)
    require(result.is_relative_to(base.resolve()) and not original.is_symlink(), 'Evidence escapes Run')
    return result


def checked(base, name, expected=None):
    path = child(base, name)
    if expected is not None:
        require(file_identity(path) == expected, 'Artifact bytes changed: ' + str(path))
    return path


def closed(path, source=None):
    path = Path(path).resolve(strict=True)
    data = read(path / 'run.json')
    require(data.get('status') == 'SUCCESS' and data.get('finishedAtUtc'), 'Run is not closed SUCCESS: ' + str(path))
    require(data.get('sourceUnchanged') is True, 'Run product source changed: ' + str(path))
    if source:
        require(data.get('source', {}).get('sourceTreeSha256') == source, 'Candidate source mismatch: ' + str(path))
    commands = data.get('commands', [])
    require(commands and len({c['name'] for c in commands}) == len(commands), 'Missing/duplicate commands')
    require(all(c.get('exitCode') == 0 and c.get('status') == 'SUCCESS' and c.get('finishedAtUtc') for c in commands),
            'Unsuccessful or unclosed command: ' + str(path))
    integrity = verify_run(path)
    require(integrity['integrityStatus'] == 'PASS', 'Run integrity failed: ' + str(integrity['errors'][:5]))
    return path, data


def typed_equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(typed_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(typed_equal(x, y) for x, y in zip(a, b))
    return a == b


def png(path, width, height):
    raw = path.read_bytes()
    require(raw[:8] == b'\x89PNG\r\n\x1a\n' and len(raw) >= 24, 'Invalid PNG')
    require(struct.unpack('>II', raw[16:24]) == (width, height), 'PNG dimensions mismatch: ' + str(path))


def pixels_equal(a, b):
    # Actual decoded pixels, not a digest asserted in a result JSON.
    from PIL import Image
    with Image.open(a) as left, Image.open(b) as right:
        return left.size == right.size and left.convert('RGBA').tobytes() == right.convert('RGBA').tobytes()


def encoding(path, fmt, width, height, vector=False):
    raw = path.read_bytes()
    if fmt == 'svg':
        tree = ElementTree.fromstring(raw)
        require(tree.tag.rsplit('}', 1)[-1] == 'svg' and len(list(tree.iter())) > 1, 'Empty/invalid SVG')
        if vector:
            require(b'data:image/png;base64' not in raw, 'Representative vector is a PNG screenshot')
    elif fmt == 'pdf':
        require(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-2048:], 'Invalid PDF')
    else:
        from PIL import Image
        with Image.open(path) as image:
            require(image.size == (width, height) and image.format.lower() == {'jpg': 'jpeg', 'webp': 'webp'}[fmt],
                    'Raster export encoding/size mismatch')


def archive(run, data):
    path = checked(run, 'artifacts/candidate.zip', data['candidateArchive'])
    with zipfile.ZipFile(path) as zipped:
        names = zipped.namelist()
        require(len(names) == len(set(names)), 'Duplicate candidate archive members')
        for name in names:
            require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe archive member')
        for name, digest in data['source']['files'].items():
            require(hashlib.sha256(zipped.read(name)).hexdigest() == digest, 'Archived product mismatch: ' + name)
        for name, expected in data['testTools'].items():
            raw = zipped.read(name)
            require({'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} == expected,
                    'Archived test/tool mismatch: ' + name)
        fixture = json.loads(zipped.read('tests/vchart_integration/cases-vchart.json'))
        lock = json.loads(zipped.read('references/vchart-release-lock.json'))
    types = {row['type'] for row in fixture['cases']}
    require(len(fixture['cases']) == len(types) == 68, 'Archived representative denominator changed')
    return types, lock, proof(path)


def unittest_counts(run, data):
    result = {}
    for command in data['commands']:
        text = '\n'.join(checked(run, command[k]).read_text(encoding='utf8') for k in ('stdout', 'stderr'))
        counts = [int(n) for n in re.findall(r'Ran (\d+) tests? in ', text)]
        if counts:
            require('FAILED (' not in text and len(re.findall(r'^OK\s*$', text, re.M)) >= len(counts),
                    'Missing real unittest OK completion: ' + command['name'])
            result[command['name']] = counts
    for name in (*UNIT_NAMES, 'existing-vchart-contracts', *('regression-' + x for x in REGRESSIONS)):
        require(result.get(name) and sum(result[name]) > 0, 'Missing real method count: ' + name)
    return result


def matrix(run, profile, source, types, corpus):
    directory = child(run, 'artifacts/matrix-' + profile)
    data = read(directory / 'result.json')
    require(data.get('schema') == 'py-mermaid-vchart-dsl-matrix/v1' and data.get('backend') == profile,
            'Matrix schema/profile mismatch')
    require(data['source']['sourceTreeSha256'] == source and data.get('sourceUnchanged') is True,
            'Matrix is not the frozen candidate')
    require(data.get('providerVersion') == '0.1.1' and data.get('exports') is True and data.get('failed') == 0,
            'Matrix incomplete/provider mismatch')
    require(set(data.get('types', [])) == types, 'Matrix type set mismatch')
    rows = data['cases']
    require(len(rows) == 301 and Counter(r['group'] for r in rows) == Counter(GROUPS), '301 matrix denominator mismatch')
    require(len({(r['group'], r['id'].casefold()) for r in rows}) == 301, 'Duplicate matrix records')
    require({r['type'] for r in rows if r['group'] == 'representative'} == types, 'Representative types incomplete')
    reference = {(r['group'], r['id']): r for r in corpus['cases']}
    require(set(reference) == {(r['group'], r['id']) for r in rows}, 'Matrix/corpus IDs differ')
    exports = 0
    policies = []
    for row in rows:
        require(row.get('status') == 'PASS' and row.get('errors') == [] and row.get('exactPixels') is True,
                'Matrix row did not pass: ' + row['id'])
        original = reference[(row['group'], row['id'])]
        require(all(row[k] == original[k] for k in ('type', 'folder', 'source', 'expected')), 'Matrix input identity changed')
        folder = child(directory, row['folder'])
        require(read(folder / 'result.json') == row, 'Per-case result differs')
        checked(folder, 'source.vchart', row['source'])
        checked(folder, 'expected.spec.json', row['expected'])
        width, height = row['width'], row['height']
        engine = row.get('engine', {}).get('renderer')
        require(engine == 'CPU' if profile == 'cpu' else engine == 'GPU' if profile == 'gpu' else engine in ('CPU', 'GPU'),
                'Actual engine mismatch: ' + row['id'])
        a, b = checked(folder, 'api.png'), checked(folder, 'actual.png')
        png(a, width, height); png(b, width, height)
        require(pixels_equal(a, b), 'Decoded DSL/API pixels differ: ' + row['id'])
        require(typed_equal(read(folder / 'api.scene.json'), read(folder / 'dsl.scene.json')), 'DSL/API scene differs')
        if row['group'] == 'supplier':
            if row['id'] in ('wordCloud/default-filling', 'wordCloud/filled-mask'):
                policy = read(folder / 'native-font-policy.json')
                require(policy == row.get('nativeFontPolicy') and policy.get('status') == 'PASS', 'Word cloud policy missing')
                policies.append({'id': row['id'], 'policy': policy,
                                 'upstreamTextEqual': row.get('upstreamTextEqual'),
                                 'upstreamStructureEqual': row.get('upstreamStructureEqual')})
            else:
                require(row.get('upstreamTextEqual') is True and row.get('upstreamStructureEqual') is True,
                        'Supplier content/structure was lost')
        actual_exports = row.get('exports', [])
        require({e['format'] for e in actual_exports} == ({'svg', 'pdf', 'jpg', 'webp'} if row['group'] == 'representative' else set()),
                'Export format denominator mismatch')
        require(len(actual_exports) == (4 if row['group'] == 'representative' else 0), 'Duplicate exports')
        for item in actual_exports:
            file = checked(folder, item['path'], {k: item[k] for k in ('sha256', 'bytes')})
            encoding(file, item['format'], width, height, vector=row['type'] == 'bar')
            exports += 1
    require(exports == 272, 'Actual exported files incomplete')
    return {'backend': profile, 'cases': 301, 'groups': GROUPS, 'types': 68, 'actualExportFiles': exports,
            'actualDecodedPixelsEqual': True, 'result': proof(directory / 'result.json'), 'wordCloudPolicies': policies}


def installation(path, kind, source, types, lock):
    run, data = closed(path, source)
    require(data.get('kind') == kind, 'Install artifact kind mismatch')
    commands = {c['name']: c for c in data['commands']}
    required = {'build-consumer', 'fresh-venv', 'before-install', 'resolver-install', 'pip-check', 'pip-freeze', 'isolated-installed-render'}
    require(required <= set(commands), 'Installation command chain incomplete')
    before = read(checked(run, commands['before-install']['stdout']))
    require(isinstance(before, list) and not any(p['name'].lower().replace('_','-') == 'py-visactor-vchart' for p in before),
            'Fresh environment already contained the supplier')
    argv = commands['isolated-installed-render']['argv']
    require('-I' in argv and '--dsl' in argv, 'Missing isolated real DSL install probe')
    delivered = read(run / 'artifacts/delivery.json')
    result = read(run / 'artifacts/installed/result.json')
    require(delivered.get('status') == 'PASS' and delivered.get('artifactKind') == kind and delivered.get('freshEnvironmentHadVChart') is False,
            'Fresh install delivery failed')
    require(delivered.get('delivery') == 'pypi' and delivered.get('requirement') == 'py-visactor-vchart==0.1.1', 'Not formal PyPI dependency')
    require(delivered.get('resolvedDownload') == result.get('vchartResolvedDownload'), 'Resolver/probe download mismatch')
    download = delivered['resolvedDownload']
    require(download['url'] == lock['asset']['url'] and download['archive_info']['hashes']['sha256'] == lock['asset']['sha256'],
            'Resolved supplier asset differs from archived release lock')
    pip_report = read(run / 'artifacts/pip-install-report.json')
    resolved = [p for p in pip_report['install'] if p['metadata']['name'].lower().replace('_','-') == 'py-visactor-vchart']
    require(len(resolved) == 1 and resolved[0]['download_info'] == download, 'Actual pip report differs from delivery')
    require(result.get('status') == 'PASS' and result.get('isolated') is True and result.get('delivery') == 'pypi'
            and result.get('vchartDirectUrl') is None and result.get('forbiddenProductionImports') is False, 'Installed isolation/dependency probe failed')
    artifact = delivered['consumerArtifact']
    checked(run, artifact['path'], {k: artifact[k] for k in ('sha256', 'bytes')})
    require(kind == 'wheel' and artifact['path'].endswith('.whl') or kind == 'sdist' and artifact['path'].endswith('.tar.gz'), 'Wrong consumer artifact extension')
    require(result.get('versions', {}).get('py-visactor-vchart') == '0.1.1', 'Installed provider version mismatch')
    require(any(v.replace(' ','') == 'py-visactor-vchart==0.1.1' for v in result.get('mermaidRequiresDist',[])),
            'Installed consumer metadata lacks the exact PyPI requirement')
    fixture = checked(run, 'artifacts/dsl-fixtures.json', delivered['fixture'])
    require(result['dsl']['fixtureSha256'] == file_identity(fixture)['sha256'], 'Installed DSL fixture identity changed')
    require(result.get('renderedTypes') == result['dsl'].get('renderedTypes') == 68 and result['dsl'].get('status') == 'PASS', 'Installed 68+68 denominator mismatch')
    regular, dsl = result['cases'], result['dsl']['cases']
    require(len(regular) == len(dsl) == 68 and {r['type'] for r in regular} == {r['type'] for r in dsl} == types, 'Installed types incomplete')
    require(len({r['id'] for r in regular}) == len({r['id'] for r in dsl}) == 68, 'Duplicate installed IDs')
    by_id = {r['id']: r for r in regular}
    for row in dsl:
        original = by_id[row['id']]
        require(original.get('status') == row.get('status') == 'PASS' and original.get('renderer') == 'CPU'
                and original.get('nonwhitePixels', 0) >= 8 and row.get('specEquivalent') is True and row.get('actualPixelsEqual') is True,
                'Installed real render failed')
        a = checked(run, 'artifacts/installed/' + row['id'] + '.png')
        b = checked(run, 'artifacts/installed/' + row['id'] + '.dsl.png')
        require(file_identity(a)['sha256'] == original['sha256'] and file_identity(b)['sha256'] == row['pngSha256'], 'Installed PNG digest mismatch')
        png(a, original['width'], original['height']); png(b, original['width'], original['height'])
        require(pixels_equal(a, b), 'Installed DSL pixels differ')
    require(any(r['inlineMapCount'] for r in dsl) and any(r['inlineSvgCount'] for r in dsl), 'Installed inline resources untested')
    require(result.get('mathGlyphVerified') is True and result.get('realELK') == {'engine':'pyelk/elk.layered','version':'0.1.0','nodes':3,'edges':2}, 'Installed real math/ELK missing')
    require(set(result.get('vectorExports', [])) == {'svg', 'pdf'}, 'Installed vectors missing')
    encoding(checked(run, 'artifacts/installed/representative.svg'), 'svg', 0, 0, vector=True)
    encoding(checked(run, 'artifacts/installed/representative.pdf'), 'pdf', 0, 0)
    checked(run, 'artifacts/installed/math-and-elk.png')
    require(result.get('modulePaths') and all(Path(p).is_relative_to(Path(result['prefix'])) for p in result['modulePaths'].values()), 'Installed modules not from fresh prefix')
    return {'run': relative(run), 'manifest': proof(run/'run.json'), 'sourceTreeSha256': source,
            'artifact': artifact, 'directSpecs': 68, 'dslSpecs': 68, 'formalPyPI': True,
            'realMathAndELK': True, 'vectorFormats': ['svg','pdf'], 'result': proof(run/'artifacts/installed/result.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--sdist', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--visual-review', type=Path)
    args = parser.parse_args()
    run, data = closed(args.run)
    require(data.get('scope') == 'VCHART-DSL-P4' and data.get('testToolsUnchanged') is True, 'Need frozen final P4/testTools')
    require(REQUIRED <= {c['name'] for c in data['commands']}, 'Final P4 command denominator incomplete')
    source = data['source']['sourceTreeSha256']
    types, lock, capsule = archive(run, data)
    methods = unittest_counts(run, data)
    corpus = read(run/'artifacts/corpus/cases.json')
    require(len(corpus['cases']) == 301, 'Frozen corpus denominator mismatch')
    matrices = [matrix(run, profile, source, types, corpus) for profile in PROFILES]
    installs = [installation(args.wheel,'wheel',source,types,lock), installation(args.sdist,'sdist',source,types,lock)]
    visual = None
    if args.visual_review:
        value = read(args.visual_review)
        require(value.get('status') == 'PASS' and value.get('sourceTreeSha256') == source
                and (ROOT / value.get('candidateRun','')).resolve() == run, 'Visual review candidate/status mismatch')
        visual = proof(args.visual_review)
    output = args.out.resolve()
    require(not any(output.is_relative_to(Path(p).resolve()) for p in (args.run,args.wheel,args.sdist)), 'Cannot write into closed input evidence')
    output.parent.mkdir(parents=True,exist_ok=True)
    result = {'schema':'py-mermaid-vchart-dsl-verification/v1','status':'PASS','candidateRun':relative(run),
              'sourceTreeSha256':source,'candidateManifest':proof(run/'run.json'),'candidateArchive':capsule,
              'counts':{'types':68,'casesPerProfile':301,'supplier':225,'representative':68,'examples':8,
                        'profiles':3,'matrixCases':903,'actualExportFiles':816,'unittestMethods':sum(map(sum,methods.values()))},
              'unittestMethods':methods,'matrices':matrices,'installations':installs,'visualReview':visual,
              'visualReviewStatus':'PASS' if visual else 'NOT_SUPPLIED_SEPARATE_MANUAL_REVIEW_REQUIRED',
              'acceptedScope':'Lossless native DSL v1 to the same public 68-type static provider; evidence-specific tests/matrices/isolated installs.',
              'notClaimed':['Exhaustive option or source-branch coverage','Closure of the 22 previously identified Mermaid branch gaps',
                            'Provider unsupported/disabled-only advanced options','Dagre, interaction, animation, 3D, video/audio, arbitrary browser HTML/CSS'],
              'providerRestrictionsRetained':True,'oldMermaidGapCount':22}
    write_json(output,result,exclusive=True)
    print(json.dumps({'status':'PASS','out':str(output),'sourceTreeSha256':source,'unittestMethods':result['counts']['unittestMethods']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
