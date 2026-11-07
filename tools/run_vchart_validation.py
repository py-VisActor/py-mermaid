"""Standard grouped validation for the published VChart integration.

Development builds are explicitly marked and never eligible for publication.
Every execution uses a fresh immutable run directory and preserves failures.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

from run_support import ROOT, Run, file_identity, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--supplier', type=Path, default=ROOT.parent / 'py-vchart')
    p.add_argument('--supplier-python', type=Path, required=True)
    p.add_argument('--phase', choices=['first', 'final'], default='first')
    p.add_argument('--packages', type=Path, help='Reviewed clean release package directory for final validation')
    p.add_argument('--profiles', nargs='+', choices=['cpu', 'auto', 'gpu'], default=['cpu'])
    p.add_argument('--regressions', action='store_true')
    args = p.parse_args()
    args.supplier_python = args.supplier_python.resolve(strict=True)
    supplier = args.supplier.resolve(strict=True)
    # Wheel builders append hash directories and nested license paths. A short
    # Windows TEMP avoids MAX_PATH failures without changing packaged licenses.
    temporary_parent = Path('C:/t') if sys.platform == 'win32' else None
    if temporary_parent is not None:
        temporary_parent.mkdir(exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix='vc-', dir=temporary_parent)
    temporary_env = {'TEMP': temporary.name, 'TMP': temporary.name, 'TMPDIR': temporary.name}
    with Run('VCHART-P3' if args.phase == 'first' else 'VCHART-P4', 'batch') as run:
        print(run.path, flush=True)
        fixture_files = sorted((supplier / 'tests/cases').rglob('*'))
        run.data['supplierInputs'] = {p.relative_to(supplier).as_posix(): file_identity(p)
                                     for p in fixture_files if p.is_file()}
        runtime = [p for p in (supplier / 'src/py_vchart').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        runtime += [supplier / name for name in ('README.md', 'pyproject.toml')]
        runtime += list(supplier.glob('LICENSE*'))
        run.data['supplierSource'] = {p.relative_to(supplier).as_posix(): file_identity(p) for p in sorted(runtime)}
        run.data['validationTool'] = file_identity(Path(__file__))
        run.data['hostTestSources'] = {p.relative_to(ROOT).as_posix(): file_identity(p)
            for p in sorted((ROOT / 'tests/vchart_integration').glob('*')) if p.is_file()}
        run.data['supplierTestSources'] = {p.relative_to(supplier).as_posix(): file_identity(p)
            for p in sorted((supplier / 'tests').glob('*.py'))}
        # The consumer starts from a deliberately retained dirty tree. Preserve
        # its actual bytes, not only a HEAD that cannot reproduce this candidate.
        snapshots = {relative: ROOT / relative for relative in run.data['source']['files']}
        for directory in ('tests', 'tools'):
            for path in (ROOT / directory).rglob('*'):
                if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    snapshots[path.relative_to(ROOT).as_posix()] = path
        snapshots['README.en.md'] = ROOT / 'README.en.md'
        archive_manifest = {}
        with zipfile.ZipFile(run.path / 'artifacts/consumer-candidate.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for relative, path in sorted(snapshots.items()):
                raw = path.read_bytes()
                expected = run.data['source']['files'].get(relative)
                actual = hashlib.sha256(raw).hexdigest()
                if expected is not None and actual != expected:
                    raise ValueError('Candidate changed before archival: ' + relative)
                archive.writestr(relative, raw)
                archive_manifest[relative] = {'bytes': len(raw), 'sha256': actual}
        write_json(run.path / 'artifacts/consumer-candidate.json', archive_manifest)
        run.data['consumerCandidateArchive'] = file_identity(run.path / 'artifacts/consumer-candidate.zip')
        run.save()
        def command(name, argv, cwd=ROOT, env=None):
            result = run.command(name, list(map(str, argv)), cwd=cwd, env={**temporary_env, **(env or {})}, timeout=3600)
            print(name, result['exitCode'], flush=True)
            return result['exitCode'] == 0
        if args.phase == 'first':
            packages = run.path / 'artifacts/supplier-build/packages'
            if not command('development-build', [args.supplier_python, supplier / 'tools/release_artifacts.py',
                           'build', '--allow-dirty', '--out', packages.parent], supplier):
                return 1
        else:
            if args.packages is None:
                p.error('final requires --packages with a clean reviewed build')
            packages = args.packages.resolve(strict=True)
        manifest = json.loads((packages / 'release-manifest.json').read_text('utf-8'))
        if args.phase == 'final' and manifest.get('dirtySource'):
            raise ValueError('Final package validation rejects development artifacts')
        wheel = next(packages.glob('*.whl'))
        for name, expected in manifest['distributions'].items():
            assert file_identity(packages / name) == expected
        run.data['supplierRelease'] = manifest
        # Install the actual wheel, not an editable sibling or a PYTHONPATH fallback.
        if not command('install-supplier-host', [sys.executable, '-m', 'pip', 'install', '--force-reinstall', '--no-deps', wheel]):
            return 1
        if not command('host-runtime-dependencies', [sys.executable, '-m', 'pip', 'install', 'numpy>=1.26']):
            return 1
        if not command('host-editable-metadata', [sys.executable, '-m', 'pip', 'install', '-e', ROOT]):
            return 1
        if not command('install-supplier-tests', [args.supplier_python, '-m', 'pip', 'install', '--force-reinstall', '--no-deps', wheel], supplier):
            return 1
        env = {'PYTHONPATH': str(ROOT / 'src'), 'PYTHONUTF8': '1'}
        # Execute every first group before any source repair. Keep all failures.
        command('host-pip-check', [sys.executable, '-m', 'pip', 'check'])
        command('supplier-unit', [args.supplier_python, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], supplier)
        command('supplier-strict-reference', [args.supplier_python, supplier / 'tools/visual/check_cartesian.py',
                '--all', '--output', run.path / 'artifacts/reference'], supplier)
        for backend in args.profiles:
            command('supplier-native-' + backend, [sys.executable, '-I', supplier / 'tools/release_smoke.py',
                    '--out', run.path / ('artifacts/native-' + backend), '--backend', backend,
                    '--expected-version', manifest['version'], '--forbid-source', supplier / 'src'], supplier)
        command('bridge-contracts', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/vchart_integration', '-v'],
                env={**env, 'VCHART_ARTIFACTS': str(run.path / 'artifacts/bridge-specs')})
        cases = ROOT / 'tests/vchart_integration/cases-mermaid-charts.json'
        command('mermaid-original', ['node', ROOT / 'tools/oracle/vchart_mermaid_capture.cjs',
                '--fixtures', cases, '--out', run.path / 'artifacts/mermaid-oracle'], env=env)
        for backend in args.profiles:
            command('mermaid-native-' + backend, [sys.executable, ROOT / 'tools/vchart_mermaid_probe.py',
                    '--fixtures', cases, '--out', run.path / ('artifacts/mermaid-' + backend), '--backend', backend,
                    '--export-formats', 'svg', 'pdf', 'jpg', 'webp'], env=env)
        if args.regressions:
            # The prior branch audit contains intentional failing reproducers;
            # it remains separate evidence, not a silently skipped green suite.
            for directory in ('bootstrap', 'dependencies', 'f011', 'f012', 'f013', 'f014', 'math',
                              'bulk', 'html_host', 'pixel_compare', 'tooling'):
                command('regression-' + directory, [sys.executable, '-m', 'unittest', 'discover',
                        '-s', ROOT / 'tests' / directory, '-v'], env=env)
        current = {p.relative_to(supplier).as_posix(): file_identity(p) for p in sorted(runtime)}
        run.data['supplierSourceUnchanged'] = current == run.data['supplierSource']
        run.data['functionalStatus'] = 'FAILED' if any(c['exitCode'] for c in run.data['commands']) else 'CHECKS_PASSED_VISUAL_REVIEW_REQUIRED'
        run.save()
    print(json.dumps({'run': str(run.path), 'status': run.data['status'],
                      'sourceUnchanged': run.data['sourceUnchanged'], 'supplierSourceUnchanged': run.data['supplierSourceUnchanged']}))
    return int(run.data['status'] != 'SUCCESS' or not run.data['sourceUnchanged'] or not run.data['supplierSourceUnchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
