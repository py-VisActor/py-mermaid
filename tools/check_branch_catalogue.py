"""Check frozen branch/input/source provenance without executing the product.

Catalogue integrity is separate from runtime branch verification. No percentage
of whole-project source branches is inferred from these finite records.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from bulk_support import load_cases
from run_support import ROOT, file_identity, source_identity, write_json


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text('utf-8'))


def proof_path(item):
    path = (ROOT / item['path']).resolve(strict=True)
    require(file_identity(path)['sha256'] == item['sha256'], 'Evidence hash drift: ' + str(path))
    return path


def source_path(ref):
    repository = ref.get('repository', 'mermaid')
    roots = {'mermaid': ROOT / '.local/upstream-mermaid',
             'zenuml-core': ROOT / '.local/bulk-sources/zenuml/source'}
    require(repository in roots, 'Unknown source repository: ' + repository)
    base = roots[repository].resolve(strict=True)
    path = (base / ref['path']).resolve(strict=True)
    require(path.is_relative_to(base), 'Unsafe source path')
    return path


def source_content(ref, maps):
    if ref.get('repository') == 'mermaid-bundle-sourcesContent':
        path = (ROOT / ref['bundleMapPath']).resolve(strict=True)
        require(path.is_relative_to((ROOT / '.local').resolve()), 'Embedded source map outside fixed development inputs')
        if path not in maps:
            maps[path] = {'document': read(path), 'identity': file_identity(path)}
        require(maps[path]['identity']['sha256'] == ref['bundleMapSha256'], 'Embedded source map hash drift')
        document = maps[path]['document']
        indices = [i for i, name in enumerate(document['sources']) if name == ref['path']]
        require(len(indices) == 1, 'Embedded source name missing/ambiguous')
        content = document['sourcesContent'][indices[0]]
        require(isinstance(content, str), 'Embedded source content missing')
        require(hashlib.sha256(content.encode('utf-8')).hexdigest() == ref['sha256'], 'Embedded source content hash drift')
        return content, path.relative_to(ROOT).as_posix() + '::' + ref['path'], {'sha256': ref['sha256'], 'bundleMap': maps[path]['identity']}
    path = source_path(ref)
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'Branch source hash drift: ' + str(path))
    if ref.get('canonicalSha256'):
        base = ROOT / ('.local/bulk-sources/zenuml/source' if ref.get('repository') == 'zenuml-core' else '.local/upstream-mermaid')
        revision = 'HEAD' if ref.get('repository') == 'zenuml-core' else '1fb7869866dd619168d840291c9c54b4f129758b'
        canonical = subprocess.check_output(['git', '-C', str(base), 'show', revision + ':' + ref['path']])
        require(hashlib.sha256(canonical).hexdigest() == ref['canonicalSha256'], 'Canonical source hash drift')
        require(raw.replace(b'\r\n', b'\n') == canonical.replace(b'\r\n', b'\n'), 'Checkout source differs beyond line endings')
    return raw.decode('utf-8-sig'), path.relative_to(ROOT).as_posix(), file_identity(path)


def validate(ledgers, fixture_files):
    source = source_identity()['sourceTreeSha256']
    cases = load_cases(fixture_files, require_all=False)
    identifiers = {case['id'] for case in cases}
    pure_ids = [row['id'] for path in fixture_files for row in read(path).get('pureProbes', [])]
    require(len(pure_ids) == len(set(pure_ids)), 'Duplicate pure probe ID')
    seen = set(); counts = Counter(); references = {}; classifications = Counter(); maps = {}
    for name in ledgers:
        document = read(name)
        require(document.get('schema') == 'py-mermaid-branch-verification/v1', 'Unknown branch catalogue schema')
        require(document.get('baselineSourceTreeSha256') == source, 'Branch candidate differs')
        require(document.get('upstreamCommit') == '1fb7869866dd619168d840291c9c54b4f129758b', 'Branch fixed source differs')
        require(document.get('branches') and document.get('reviewDepth'), 'Empty catalogue/review depth')
        for branch in document['branches']:
            identifier = branch['id']
            require(identifier.casefold() not in seen, 'Duplicate branch ID: ' + identifier)
            seen.add(identifier.casefold())
            require(branch.get('title') and branch.get('predicate') and branch.get('arms') and branch.get('source'),
                    'Branch lacks concrete condition/arms/source: ' + identifier)
            require('sourceExpected' in branch and branch['sourceExpected'] is not None,
                    'Branch lacks independent expected contract: ' + identifier)
            require(branch.get('classification') and branch.get('reason'), 'Branch lacks classification/reason: ' + identifier)
            require(set(branch.get('caseIds', [])) <= identifiers, 'Unknown branch case ID: ' + identifier)
            require(set(branch.get('pureProbeIds', [])) <= set(pure_ids), 'Unknown pure branch probe ID: ' + identifier)
            for ref in branch['source']:
                content, name, identity = source_content(ref, maps)
                lines = content.splitlines()
                require(ref.get('symbol') and isinstance(ref.get('line'), int) and 1 <= ref['line'] <= len(lines),
                        'Invalid source symbol/line: ' + name)
                references[name] = identity
            if branch['classification'] == 'VERIFIED_EXISTING':
                require(branch.get('tests'), 'Existing branch lacks executed tests: ' + identifier)
                for test in branch['tests']:
                    receipt = test.get('executedBy')
                    require(receipt, 'Existing test lacks closed execution receipt')
                    manifest_path = proof_path(receipt['run']); manifest = read(manifest_path)
                    require(manifest.get('status') == 'SUCCESS' and manifest.get('sourceUnchanged') is True and
                            manifest.get('source', {}).get('sourceTreeSha256') == source,
                            'Existing test is not closed unchanged same-candidate evidence')
                    commands = [c for c in manifest['commands'] if c['name'] == receipt['command']]
                    require(len(commands) == 1 and commands[0].get('exitCode') == 0, 'Existing test command failed/missing')
                    stderr = proof_path(receipt['stderr'])
                    require(stderr == (manifest_path.parent / commands[0]['stderr']).resolve(), 'Existing stderr binding differs')
                    test_path = ROOT / test['path']
                    require(file_identity(test_path)['sha256'] == test['sha256'], 'Existing test file hash drift')
                    with zipfile.ZipFile(manifest_path.parent / 'artifacts/test-tool-candidate.zip') as archive:
                        require(hashlib.sha256(archive.read(test['path'])).hexdigest() == test['sha256'],
                                'Existing test archive bytes differ')
                    method = test['symbol'].rsplit('.', 1)[-1]
                    module = test['path'].removeprefix('tests/').removesuffix('.py').replace('/', '.')
                    expected = f'{method} ({module}.{test["symbol"]}) ... ok'
                    require(expected in stderr.read_text('utf-8'), 'Exact existing method did not pass')
            counts[document['group']] += 1
            classifications[branch['classification']] += 1
    return {'schema': 'py-mermaid-branch-catalogue-check/v1', 'catalogueStatus': 'PASS',
            'functionalStatus': 'NOT_EVALUATED', 'sourceTreeSha256': source,
            'globalBranchCoverageEstablished': False, 'branchRecords': sum(counts.values()),
            'groupCounts': dict(counts), 'classifications': dict(classifications), 'newFixtureCount': len(cases), 'pureProbeCount': len(pure_ids),
            'inputs': {str(Path(p)): file_identity(Path(p)) for p in [*ledgers, *fixture_files]},
            'references': references,
            'meaning': 'Finite branch/source/input provenance only; runtime results and coverage boundaries are reported separately.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledgers', type=Path, nargs='+', required=True)
    parser.add_argument('--fixtures', type=Path, nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), 'Output must be new')
    try:
        result = validate(args.ledgers, args.fixtures)
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        result = {'schema': 'py-mermaid-branch-catalogue-check/v1', 'catalogueStatus': 'FAIL',
                  'functionalStatus': 'NOT_EVALUATED', 'error': str(exc)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, result, exclusive=True)
    print(json.dumps({k: v for k, v in result.items() if k not in ('inputs', 'references')}))
    return int(result['catalogueStatus'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
