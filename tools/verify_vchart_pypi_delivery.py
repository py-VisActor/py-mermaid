"""Verify the PyPI channel change against accepted rendering and real installs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from run_support import ROOT, file_identity, source_identity, verify_run, write_json


def read(path):
    return json.loads(Path(path).read_text('utf-8'))


def closed(path, same_source=None):
    path = path.resolve(strict=True)
    data = read(path / 'run.json')
    assert data['status'] == 'SUCCESS' and data['sourceUnchanged'] is True, path
    assert verify_run(path)['integrityStatus'] == 'PASS', path
    assert all(c['exitCode'] == 0 for c in data['commands']), path
    if same_source:
        assert data['source'] == same_source, 'Install/check candidate differs'
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-p4', required=True, type=Path)
    parser.add_argument('--published-run', required=True, type=Path)
    parser.add_argument('--install-runs', required=True, nargs=2, type=Path)
    parser.add_argument('--checks-run', required=True, type=Path)
    parser.add_argument('--ci', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    current = source_identity()
    previous = closed(args.previous_p4)
    changed = {name for name in current['files'].keys() | previous['source']['files'].keys()
               if current['files'].get(name) != previous['source']['files'].get(name)}
    assert changed <= {'pyproject.toml', 'README.md'}, 'Rendering source changed'
    published = closed(args.published_run)
    lock = read(ROOT / 'references/vchart-release-lock.json')
    metadata = read(args.published_run / 'artifacts/pypi-metadata.json')
    distributions = previous['supplierRelease']['distributions']
    assets = {a['filename']: a for a in metadata['urls']}
    assert lock['requirement'] == f"py-visactor-vchart=={metadata['info']['version']}"
    assert lock['delivery'] == 'pypi' and lock['pypi']['published'] is True
    for name, expected in distributions.items():
        assert assets[name]['digests']['sha256'] == expected['sha256']
        assert file_identity(args.published_run / 'artifacts/pypi' / name) == expected
    installs = []
    for path in args.install_runs:
        run = closed(path, current)
        installed = read(path / 'artifacts/installed/result.json')
        pip_report = read(path / 'artifacts/pip-install-report.json')
        download = next(p['download_info'] for p in pip_report['install']
                        if p['metadata']['name'].lower().replace('_', '-') == 'py-visactor-vchart')
        assert installed['status'] == 'PASS' and installed['renderedTypes'] == 68
        assert installed['delivery'] == 'pypi' and installed['vchartDirectUrl'] is None
        assert download == installed['vchartResolvedDownload']
        assert download['url'] == lock['asset']['url']
        assert download['archive_info']['hashes']['sha256'] == lock['asset']['sha256']
        assert installed['mathGlyphVerified'] and installed['realELK']['nodes'] == 3
        assert installed['realELK']['edges'] == 2 and set(installed['vectorExports']) == {'svg', 'pdf'}
        assert not installed['forbiddenProductionImports']
        installs.append({'run': str(path), 'kind': run['result']['artifactKind'],
                         'consumerArtifactSha256': run['result']['consumerArtifactSha256'],
                         'resolvedDownload': download})
    assert {item['kind'] for item in installs} == {'wheel', 'sdist'}
    checks = closed(args.checks_run, current)
    methods = {}
    for command in checks['commands']:
        text = (args.checks_run / command['stderr']).read_text('utf-8')
        counts = re.findall(r'Ran (\d+) tests? in ', text)
        if counts:
            assert re.search(r'^OK\s*$', text, re.M)
            methods[command['name']] = sum(map(int, counts))
    assert methods.get('integration-tests') == 156
    api = read(args.ci / 'github-evidence.json')
    workflow = json.loads(api['run']['content'])
    jobs = api['jobs']['jobs']
    assert workflow['conclusion'] == 'success' and workflow['run_attempt'] == 2
    assert workflow['head_sha'] == lock['sourceCommit']
    assert len(jobs) == 6 and all(j['conclusion'] == 'success' for j in jobs)
    artifact = next(a for a in api['artifacts']['artifacts'] if a['name'] == 'pypi-verification')
    archive = args.ci / 'pypi-verification.zip'
    assert artifact['digest'] == 'sha256:' + file_identity(archive)['sha256']
    with zipfile.ZipFile(archive) as z:
        assert read_json_bytes(z.read('installed-from-pypi/result.json'))['status'] == 'PASS'
        for name, expected in distributions.items():
            raw = z.read('pypi/' + name)
            assert {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected
        for kind in ('wheel', 'sdist'):
            rendered = read_json_bytes(z.read('installed-from-pypi/' + kind + '/render/result.json'))
            assert rendered['status'] == 'PASS' and rendered['passed'] == rendered['cases'] == 225
            assert len(rendered['types']) == 68 and all(r['status'] == 'PASS' for r in rendered['results'])
            assert 'site-packages' in rendered['module']
            text = z.read('installed-from-pypi/' + kind + '/native-host-contracts.stderr.log').decode()
            assert re.search(r'Ran 36 tests in ', text) and re.search(r'\nOK\s*$', text)
    args.out.mkdir(parents=True, exist_ok=False)
    write_json(args.out / 'summary.json', {
        'schema': 'py-mermaid-vchart-pypi-delivery/v1', 'status': 'PASS', 'published': True,
        'requirement': lock['requirement'], 'pypi': lock['pypi'], 'renderingSourceUnchanged': True,
        'previousAcceptedRendering': str(args.previous_p4), 'packagingOnlyChangedFiles': sorted(changed),
        'sourceTreeSha256': current['sourceTreeSha256'], 'freshInstallations': installs,
        'checksRun': str(args.checks_run), 'actualMethods': methods,
        'workflow': {'url': workflow['html_url'], 'attempt': 2, 'conclusion': 'success', 'jobs': 6},
        'ciArchive': {'path': str(archive), **file_identity(archive)},
        'ciPyPIInstallations': {'wheel': '225/68/36 PASS', 'sdist': '225/68/36 PASS'},
        'historicalEvidencePreserved': True,
        'note': 'Publication/packaging supplement; retained static scope and earlier limits unchanged.'})
    print(json.dumps({'status': 'PASS', 'summary': str(args.out / 'summary.json')}))


def read_json_bytes(raw):
    return json.loads(raw.decode('utf-8'))


if __name__ == '__main__':
    main()
