"""Frozen grouped DSL verification; retain first failures before any repair."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

from run_support import ROOT, Run, file_identity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase', choices=('first', 'final'), default='first')
    p.add_argument('--profiles', nargs='+', choices=('cpu', 'auto', 'gpu'), default=['cpu', 'auto', 'gpu'])
    p.add_argument('--regressions', action='store_true')
    args = p.parse_args()
    with Run('VCHART-DSL-P3' if args.phase == 'first' else 'VCHART-DSL-P4', 'batch') as run:
        print(run.path, flush=True)
        capsule = {name: ROOT / name for name in run.data['source']['files']}
        for folder in ('tests', 'tools'):
            for file in (ROOT / folder).rglob('*'):
                if file.is_file() and not file.is_symlink() and '__pycache__' not in file.parts and file.suffix != '.pyc':
                    capsule[file.relative_to(ROOT).as_posix()] = file
        for file in (ROOT / 'references').glob('vchart*.json'):
            capsule[file.relative_to(ROOT).as_posix()] = file
        for file in (ROOT / 'docs/proposals/vchart-v1').rglob('*'):
            if file.is_file():
                capsule[file.relative_to(ROOT).as_posix()] = file
        with zipfile.ZipFile(run.path / 'artifacts/candidate.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for name, file in sorted(capsule.items()):
                z.writestr(name, file.read_bytes())
        run.data['candidateArchive'] = file_identity(run.path / 'artifacts/candidate.zip')
        run.data['testTools'] = {name: file_identity(file) for name, file in capsule.items() if name.startswith(('tests/', 'tools/'))}
        run.save()
        def command(name, argv, timeout=1800):
            result = run.command(name, list(map(str, argv)), timeout=timeout)
            print(name, result['exitCode'], flush=True)
            return result['exitCode'] == 0
        corpus = run.path / 'artifacts/corpus'
        if not command('freeze-independent-source-corpus', [sys.executable, ROOT / 'tools/vchart_dsl_corpus.py', '--out', corpus]):
            return 1
        command('comparison-negative-controls', [sys.executable, ROOT / 'tools/check_vchart_dsl_controls.py'])
        for name in ('syntax', 'compiler', 'api', 'cli', 'resources'):
            command('dsl-unit-' + name, [sys.executable, '-m', 'unittest', 'discover', '-s', ROOT / 'tests/vchart_dsl', '-p', 'test_' + name + '.py', '-v'])
        command('existing-vchart-contracts', [sys.executable, '-m', 'unittest', 'discover', '-s', ROOT / 'tests/vchart_integration', '-v'])
        for profile in args.profiles:
            command('dsl-matrix-' + profile, [sys.executable, ROOT / 'tools/vchart_dsl_matrix.py', '--corpus', corpus,
                    '--out', run.path / ('artifacts/matrix-' + profile), '--backend', profile, '--exports'])
        if args.regressions:
            for folder in ('bootstrap', 'dependencies', 'f011', 'f012', 'f013', 'f014', 'math', 'bulk', 'html_host', 'pixel_compare', 'tooling'):
                command('regression-' + folder, [sys.executable, '-m', 'unittest', 'discover', '-s', ROOT / 'tests' / folder, '-v'])
        run.data['testToolsUnchanged'] = all(file_identity(ROOT / name) == identity for name, identity in run.data['testTools'].items())
        run.data['functionalStatus'] = 'FAILED' if any(c['exitCode'] for c in run.data['commands']) else 'CHECKS_PASSED_VISUAL_REVIEW_REQUIRED'
        run.save()
    print(json.dumps({'run': str(run.path), 'status': run.data['status'], 'sourceUnchanged': run.data['sourceUnchanged'],
                      'testToolsUnchanged': run.data['testToolsUnchanged']}))
    return int(run.data['status'] != 'SUCCESS' or not run.data['sourceUnchanged'] or not run.data['testToolsUnchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
