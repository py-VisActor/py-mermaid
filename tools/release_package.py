"""Build reviewed files once, verify isolated installs, and read back PyPI bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.parse
import urllib.request
import zipfile

from run_support import ROOT, Run, file_identity, source_identity, write_json


def project():
    return tomllib.loads((ROOT / 'pyproject.toml').read_text('utf-8'))['project']


def read(path):
    return json.loads(Path(path).read_text('utf-8'))


def validate_original_b(name):
    directory = (ROOT / name).resolve(strict=True)
    if not directory.is_relative_to((ROOT / 'references').resolve()) or not directory.is_dir():
        raise ValueError('Original source reference must stay inside references/')
    if read(directory / 'provenance.json')['role'] != 'FIXED_ORIGINAL_ONLY_NOT_NATIVE_GOLDENS':
        raise ValueError('Only fixed original source observations are eligible')
    if file_identity(directory / 'cases-B.json') != file_identity(ROOT / 'tests/closure/cases-B.json'):
        raise ValueError('Original B source reference does not match the reviewed fixture bytes')
    return directory


def original_b_reference(*, required=True):
    fixture = file_identity(ROOT / 'tests/closure/cases-B.json')
    matches = [name for name in ('references/closure-source-B', 'references/closure-source-B-dst')
               if (ROOT / name / 'cases-B.json').is_file()
               and file_identity(ROOT / name / 'cases-B.json') == fixture]
    if len(matches) == 1:
        return validate_original_b(matches[0])
    if required or matches:
        raise ValueError('Need exactly one byte-matching frozen original B source reference')
    return None


def checked_distributions(manifest, packages):
    if manifest['project'] != project()['name'] or manifest['version'] != project()['version']:
        raise ValueError('Release manifest project/version differs from candidate')
    entries = manifest['distributions']
    if len(entries) != 2 or sum(n.endswith('.whl') for n in entries) != 1 or sum(n.endswith('.tar.gz') for n in entries) != 1:
        raise ValueError('Exactly one wheel and one sdist required')
    files = []
    for name, identity in entries.items():
        if Path(name).name != name or '/' in name or '\\' in name:
            raise ValueError('Unsafe distribution filename')
        file = (packages / name).resolve(strict=True)
        if not file.is_relative_to(packages.resolve()) or file_identity(file) != identity:
            raise ValueError('Reviewed distribution changed: ' + name)
        files.append(file)
    return files


def verification_fixture():
    """Freeze independent source fixtures; never ask the compiler for goldens."""
    from vchart_dsl_corpus import format_spec
    vchart = read(ROOT / 'tests/vchart_integration/cases-vchart.json')
    for row in vchart['cases']:
        row['dslSource'] = format_spec(row['spec'], row['maps'], row['svgs'])
    candidates = []
    for file in sorted((ROOT / 'tests/bulk').glob('cases-*.json')):
        candidates.extend(read(file)['cases'])
    candidates.extend(read(ROOT / 'tests/vchart_integration/cases-mermaid-charts.json')['cases'])
    representatives = {}
    for row in candidates:
        if row.get('expect') == 'render' and not row.get('expectedNativeError') and row.get('expectedText'):
            representatives.setdefault(row['kind'], row)
    for kind, header in (('flowchart-v2', 'flowchart'), ('flowchart-elk', 'flowchart-elk')):
        representatives[kind] = {'id': 'release-' + kind, 'kind': kind,
            'source': header + ' TD\n A[Alpha] --> B[Beta]\n', 'config': {}, 'expectedText': ['Alpha', 'Beta'], 'expect': 'render'}
    wanted = read(ROOT / 'references/bulk-scope.json')['upstreamInventory']
    if set(wanted) != set(representatives):
        raise ValueError('Independent release fixtures lost diagram kinds: ' + repr(set(wanted) - set(representatives)))
    closure = []
    for file in sorted((ROOT / 'tests/closure').glob('cases-*.json')):
        closure.extend(read(file).get('cases', []))
    return {'schema': 'py-mermaid-release-inputs/v1', 'diagrams': [representatives[k] for k in wanted],
            'vchart': vchart['cases'], 'closure': closure,
            'supplierLock': read(ROOT / 'references/vchart-release-lock.json')}


def build(args):
    args.out.mkdir(parents=True, exist_ok=False)
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT))
    if dirty and not args.allow_dirty:
        raise ValueError('Commit the complete reviewed candidate first; --allow-dirty is development-only')
    reference_b = original_b_reference(required=not args.allow_dirty)
    source = source_identity()
    with Run('CLOSURE-RELEASE', 'build', runs_dir=args.out / 'logs') as run:
        print(run.path, flush=True)
        packages = args.out / 'packages'
        packages.mkdir()
        result = run.command('build-exact-candidate', [sys.executable, '-m', 'build', '--wheel', '--sdist',
            '--outdir', str(packages), str(ROOT)], timeout=900)
        if result['exitCode']:
            raise RuntimeError('Candidate build failed; see retained logs')
        files = sorted(packages.iterdir())
        if len(files) != 2:
            raise ValueError('Build produced unexpected files')
        data = verification_fixture()
        fixture = args.out / 'verification-inputs.json'
        write_json(fixture, data, exclusive=True)
        inputs = {name: file_identity(ROOT / name) for name in ('tools/release_probe.py', 'tools/release_package.py',
            'tools/check_closure_b.py', 'tests/vchart_integration/cases-vchart.json', 'references/vchart-release-lock.json')}
        for file in sorted((ROOT / 'tests/closure').rglob('*')):
            if file.is_file() and '__pycache__' not in file.parts and file.suffix != '.pyc':
                inputs[file.relative_to(ROOT).as_posix()] = file_identity(file)
        if reference_b is not None:
            for file in reference_b.rglob('*.json'):
                inputs[file.relative_to(ROOT).as_posix()] = file_identity(file)
        manifest = {'schema': 'py-mermaid-release-manifest/v1', 'project': project()['name'], 'version': project()['version'],
            'tag': project()['name'] + '-v' + project()['version'], 'dirtySource': dirty,
            'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'sourceTreeSha256': source['sourceTreeSha256'], 'sourceFiles': source['files'],
            'verificationInputs': inputs, 'verificationFixture': file_identity(fixture),
            'verificationOriginalB': reference_b.relative_to(ROOT).as_posix() if reference_b else None,
            'distributions': {file.name: file_identity(file) for file in files}}
        checked_distributions(manifest, packages)
        # Check actual contents rather than assuming package-data/license globs worked.
        wheel = next(p for p in files if p.suffix == '.whl')
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            for name in ('py_mermaid/py.typed', 'py_mermaid/data/defaults.json'):
                if name == 'py_mermaid/data/defaults.json':
                    if not any(n.startswith('py_mermaid/data/') and n.endswith('.json') for n in names):
                        raise ValueError('Wheel lost generated JSON data')
                elif name not in names:
                    raise ValueError('Wheel lost ' + name)
            for license_ in ('langium-4.4.0-LICENSE', 'dayjs-1.11.21-LICENSE', 'mermaid-LICENSE'):
                if not any(n.endswith('/' + license_) for n in names):
                    raise ValueError('Wheel lost third-party license ' + license_)
        if source_identity() != source:
            raise ValueError('Product changed during release build')
        write_json(args.out / 'release-manifest.json', manifest, exclusive=True)
        run.data['publishedArtifacts'] = {str(p.resolve()): file_identity(p) for p in [*files, fixture, args.out / 'release-manifest.json']}
        run.data['functionalStatus'] = 'BUILT_NOT_INSTALL_OR_RELEASE_ACCEPTED'
        run.save()
    return {'status': 'BUILT_NOT_PUBLISHED', 'manifest': str(args.out / 'release-manifest.json'), 'source': source['sourceTreeSha256']}


def install(args):
    manifest = read(args.manifest)
    files = checked_distributions(manifest, args.packages)
    if manifest.get('dirtySource') and not args.allow_dirty:
        raise ValueError('Development artifacts require explicit --allow-dirty; never a formal release')
    current_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if manifest['sourceCommit'] != current_commit:
        raise ValueError('Release commit differs from checked-out candidate')
    if source_identity()['sourceTreeSha256'] != manifest['sourceTreeSha256']:
        raise ValueError('Checkout differs from reviewed product source')
    for name, identity in manifest['verificationInputs'].items():
        path = (ROOT / name).resolve(strict=True)
        if not path.is_relative_to(ROOT) or file_identity(path) != identity:
            raise ValueError('Verification input differs from reviewed candidate: ' + name)
    original_name = manifest.get('verificationOriginalB', 'references/closure-source-B')
    reference_b = validate_original_b(original_name) if original_name else None
    if reference_b is None and not args.allow_dirty:
        raise ValueError('Formal installation requires independent original B source observations')
    fixture = verification_fixture()
    raw = (json.dumps(fixture, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != manifest['verificationFixture']:
        raise ValueError('Independent fixture corpus differs from reviewed build')
    args.out.mkdir(parents=True, exist_ok=False)
    reports = []
    # Sequential modes avoid shared native/build directory races.
    for file in files:
        if source_identity()['sourceTreeSha256'] != manifest['sourceTreeSha256']:
            raise ValueError('Product changed between isolated distribution checks')
        kind = 'wheel' if file.suffix == '.whl' else 'sdist'
        destination = args.out / kind
        destination.mkdir()
        with Run('CLOSURE-INSTALL', kind, runs_dir=destination / 'logs') as run:
            print(run.path, flush=True)
            with tempfile.TemporaryDirectory(prefix='py-mermaid-release-') as temp:
                external = Path(temp).resolve()
                if external.is_relative_to(ROOT.parent):
                    raise ValueError('Fresh environment must be outside workspace')
                env_dir = external / 'env'
                env = {'PYTHONPATH': '', 'PYTHONNOUSERSITE': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
                       'PYTHONIOENCODING': 'utf-8', 'PIP_CONFIG_FILE': os.devnull}
                def command(name, argv, timeout=1200):
                    result = run.command(name, list(map(str, argv)), cwd=external, env=env, timeout=timeout)
                    if result['exitCode']:
                        raise RuntimeError(name + ' failed; retained logs: ' + str(run.path))
                    return result
                command('fresh-environment', [sys.executable, '-m', 'venv', env_dir])
                python = env_dir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
                command('before-install', [python, '-I', '-m', 'pip', '--isolated', 'list', '--format=json'])
                report = run.path / 'artifacts/pip-report.json'
                command('normal-index-install', [python, '-I', '-m', 'pip', '--isolated', 'install', '--no-input',
                    '--no-cache-dir', '--index-url', 'https://pypi.org/simple', '--report', report, file])
                command('pip-check', [python, '-I', '-m', 'pip', '--isolated', 'check'])
                command('pip-freeze', [python, '-I', '-m', 'pip', '--isolated', 'freeze', '--all'])
                probe = external / 'release_probe.py'
                shutil.copyfile(ROOT / 'tools/release_probe.py', probe)
                copied = external / 'verification-inputs.json'
                copied.write_bytes(raw)
                result_dir = run.path / 'artifacts/installed'
                command('isolated-installed-static-capabilities', [python, '-I', probe, '--fixtures', copied,
                    '--out', result_dir, '--workspace', ROOT.parent, '--expected-version', manifest['version'],
                    '--expected-project', manifest['project'], '--pip-report', report])
                flow = external / 'cli.mmd'
                flow.write_text('flowchart LR\n A[Alpha] --> B[Beta]\n', encoding='utf-8')
                console = env_dir / ('Scripts/py-mermaid.exe' if os.name == 'nt' else 'bin/py-mermaid')
                cli_svg = run.path / 'artifacts/console.svg'
                cli_metadata = run.path / 'artifacts/console.metadata.json'
                command('installed-console-script', [console, flow, '--backend', 'cpu', '-o', cli_svg, '--metadata', cli_metadata])
                if b'<svg' not in cli_svg.read_bytes()[:1500] or b'data:image/png;base64' in cli_svg.read_bytes():
                    raise ValueError('Console script failed actual vector export')
                if read(cli_metadata)['backend']['renderer'] != 'CPU':
                    raise ValueError('Console script used wrong backend')
                dsl_input = external / 'cli.vchart'
                dsl_input.write_text(fixture['vchart'][0]['dslSource'], encoding='utf-8')
                cli_compilation = run.path / 'artifacts/module-compilation.json'
                command('installed-module-compile', [python, '-I', '-m', 'py_mermaid.cli', dsl_input, '--compile', '-o', cli_compilation])
                if read(cli_compilation)['spec'] != fixture['vchart'][0]['spec']:
                    raise ValueError('Installed module CLI changed compiled spec')
                # Portable closure unit suite is copied without any product source.
                suite = external / 'suite'
                shutil.copytree(ROOT / 'tests/closure', suite / 'closure', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                command('verification-only-pillow', [python, '-I', '-m', 'pip', '--isolated', 'install',
                    '--no-input', '--index-url', 'https://pypi.org/simple', 'Pillow==12.3.0'])
                command('isolated-installed-closure-unit-contracts', [python, '-I', probe, '--fixtures', copied,
                    '--workspace', ROOT.parent, '--expected-version', manifest['version'], '--expected-project', manifest['project'], '--suite', suite,
                    '--out', run.path / 'artifacts/unit-contracts'])
                if reference_b is not None:
                    # Only verifier/data are copied, never production code.
                    shutil.copytree(reference_b, external / 'source-B')
                    (external / 'tools').mkdir()
                    shutil.copyfile(ROOT / 'tools/check_closure_b.py', external / 'tools/check_closure_b.py')
                    shutil.copytree(ROOT / 'tests/closure', external / 'tests/closure',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                    native_b = run.path / 'artifacts/installed-B'
                    command('installed-calendar-and-layout-observations', [python, '-I', external / 'tools/check_closure_b.py',
                        '--fixtures', external / 'tests/closure/cases-B.json', '--collect-native', native_b, '--timezone', 'UTC', '--cases'])
                    command('installed-original-parity', [python, '-I', external / 'tools/check_closure_b.py',
                        '--fixtures', external / 'tests/closure/cases-B.json', '--oracle', external / 'source-B', '--native', native_b,
                        '--out', run.path / 'artifacts/installed-B-comparison.json', '--cases'] +
                        (['--require-real-tz'] if os.name != 'nt' else []))
                result = read(result_dir / 'result.json')
                reports.append({'kind': kind, 'distribution': file_identity(file), 'status': result['status'],
                    'manifest': str(run.path / 'run.json'), 'result': str(result_dir / 'result.json')})
                run.data['functionalStatus'] = 'PASS_INSTALLED_DECLARED_STATIC_CONTRACT'
                run.save()
        if not run.data['sourceUnchanged'] or run.data['source']['sourceTreeSha256'] != manifest['sourceTreeSha256']:
            raise ValueError('Installed distribution evidence is not bound to an unchanged reviewed candidate')
    write_json(args.out / 'installation.json', {'status': 'PASS', 'platform': sys.platform,
        'sourceTreeSha256': manifest['sourceTreeSha256'], 'installations': reports}, exclusive=True)
    return {'status': 'PASS', 'installations': len(reports), 'out': str(args.out)}


def pypi(args):
    manifest = read(args.manifest)
    args.out.mkdir(parents=True, exist_ok=False)
    url = 'https://pypi.org/pypi/' + urllib.parse.quote(manifest['project']) + '/' + manifest['version'] + '/json'
    raw = urllib.request.urlopen(url, timeout=60).read()
    (args.out / 'pypi.json').write_bytes(raw)
    data = json.loads(raw)
    actual = {row['filename']: row for row in data['urls']}
    if set(actual) != set(manifest['distributions']):
        raise ValueError('Actual PyPI distribution set differs from reviewed files')
    for name, identity in manifest['distributions'].items():
        row = actual[name]
        if row['digests']['sha256'] != identity['sha256'] or row['size'] != identity['bytes']:
            raise ValueError('PyPI published different bytes: ' + name)
        parsed = urllib.parse.urlsplit(row['url'])
        if parsed.scheme != 'https' or parsed.hostname != 'files.pythonhosted.org':
            raise ValueError('Unexpected PyPI file origin')
        (args.out / name).write_bytes(urllib.request.urlopen(row['url'], timeout=120).read())
    checked_distributions(manifest, args.out)
    write_json(args.out / 'release-manifest.json', manifest, exclusive=True)
    return {'status': 'VERIFIED_ACTUAL_PYPI_BYTES', 'url': url}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('build', 'install', 'pypi'))
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--manifest', type=Path)
    p.add_argument('--packages', type=Path)
    p.add_argument('--allow-dirty', action='store_true')
    args = p.parse_args()
    args.out = args.out.resolve()
    if args.action != 'build' and args.manifest is None:
        p.error('--manifest is required')
    if args.action == 'install' and args.packages is None:
        p.error('--packages is required')
    result = {'build': build, 'install': install, 'pypi': pypi}[args.action](args)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
