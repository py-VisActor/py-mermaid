"""One frozen closure sweep; collect every group before any source repair."""
import argparse
import json
import os
from pathlib import Path
import sys
import zipfile

from run_support import ROOT, Run, file_identity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase', choices=('first', 'final'), default='first')
    p.add_argument('--profiles', nargs='+', choices=('cpu', 'auto', 'gpu'), default=['cpu', 'auto', 'gpu'])
    p.add_argument('--regressions', action='store_true')
    p.add_argument('--install', action='store_true', help='Development artifact installation; final formal release uses a clean tagged build')
    p.add_argument('--historical', action='store_true', help='Run the full retained static legacy matrix and five-format checks')
    p.add_argument('--vchart', action='store_true', help='Run all existing DSL/spec equivalence matrices; do not expand supplier chart features')
    p.add_argument('--historical-oracle', type=Path, help='Explicit fixed-source oracle reuse; run_bulk verifies all input/source identities')
    p.add_argument('--legacy-oracle-root', type=Path, help='Explicit fixed F01 source oracle root, independently verified by run_bulk')
    args = p.parse_args()
    with Run('CLOSURE-P3' if args.phase == 'first' else 'CLOSURE-P4', 'batch') as run:
        print(run.path, flush=True)
        files = {name: ROOT / name for name in run.data['source']['files']}
        for folder in ('tests', 'tools', '.github/workflows'):
            for file in (ROOT / folder).rglob('*'):
                if file.is_file() and '__pycache__' not in file.parts and file.suffix != '.pyc':
                    files[file.relative_to(ROOT).as_posix()] = file
        for file in (ROOT / 'references').glob('closure*.json'):
            files[file.relative_to(ROOT).as_posix()] = file
        for name in ('closure-source-B', 'closure-source-B-dst'):
            for file in (ROOT / 'references' / name).rglob('*.json'):
                files[file.relative_to(ROOT).as_posix()] = file
        with zipfile.ZipFile(run.path / 'artifacts/candidate.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, file in sorted(files.items()):
                archive.writestr(name, file.read_bytes())
        run.data['candidateArchive'] = file_identity(run.path / 'artifacts/candidate.zip')
        run.data['testTools'] = {name: file_identity(file) for name, file in files.items() if name.startswith(('tests/', 'tools/', '.github/'))}
        run.save()
        def command(name, argv, timeout=1800, env=None):
            result = run.command(name, list(map(str, argv)), timeout=timeout,
                env={'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8',
                     'PYTHONPATH': os.pathsep.join(str(path) for path in
                         (ROOT / 'src', ROOT / 'tests', ROOT / 'tests/branch_verification')),
                     **(env or {})})
            print(name, result['exitCode'], flush=True)
            return result['exitCode'] == 0
        frozen = run.path / 'artifacts/frozen'
        if not command('freeze-independent-inputs', [sys.executable, ROOT / 'tools/freeze_closure_inputs.py', '--out', frozen]):
            return 1
        # Original producers execute independently; nonzero statuses are retained.
        command('source-A-getters-and-geometry', ['node', ROOT / 'tools/oracle/closure_a.cjs', '--fixtures', frozen / 'cases-A.json', '--out', run.path / 'artifacts/source-A'])
        command('source-B-calendar-and-actual-ELK', ['node', '--experimental-vm-modules', ROOT / 'tools/oracle/closure_b.cjs',
            '--fixtures', frozen / 'cases-B.json', '--out', run.path / 'artifacts/source-B', '--timezone', 'UTC', '--browser'])
        command('source-all-static-draws', ['node', ROOT / 'tools/oracle/bulk_capture.cjs', '--fixtures', frozen / 'browser-cases.json', '--out', run.path / 'artifacts/oracle'], env={'TZ': 'UTC'})
        legacy_c = run.path / 'artifacts/original-branch-C-ABNF'
        command('source-original-branch-C-ABNF', ['node', ROOT / 'tests/branch_verification/oracle_c.cjs', '--out', legacy_c])
        for pattern in ('test_parser.py', 'test_dates.py', 'test_layout.py', 'test_sequence.py', 'test_collapsed.py', 'test_eventmodeling.py'):
            command('closure-unit-' + pattern[5:-3], [sys.executable, '-m', 'unittest', 'discover', '-s', ROOT / 'tests/closure',
                '-t', ROOT / 'tests', '-p', pattern, '-v'])
        command('original-branch-regressions', [sys.executable, '-m', 'unittest', 'discover', '-s', ROOT / 'tests/branch_verification', '-t', ROOT / 'tests', '-v'],
            env={'BRANCH_C_ORACLE': str(legacy_c)})
        native_b = run.path / 'artifacts/native-B'
        command('native-B-independent-values-and-real-layouts', [sys.executable, ROOT / 'tools/check_closure_b.py', '--fixtures', frozen / 'cases-B.json',
            '--collect-native', native_b, '--timezone', 'UTC', '--cases'])
        command('source-B-parity', [sys.executable, ROOT / 'tools/check_closure_b.py', '--fixtures', frozen / 'cases-B.json',
            '--oracle', run.path / 'artifacts/source-B', '--native', native_b, '--out', run.path / 'artifacts/comparison-B.json', '--cases'])
        for profile in args.profiles:
            folder = run.path / ('artifacts/native-' + profile)
            command('native-static-' + profile, [sys.executable, ROOT / 'tools/bulk_validate.py', '--fixtures', frozen / 'cases.json', '--out', folder,
                '--backend', profile], env={'TZ': 'UTC'})
            command('source-C-actual-paint-' + profile, [sys.executable, ROOT / 'tools/check_closure_c.py', '--fixtures', frozen / 'cases-C.json',
                '--oracle', run.path / 'artifacts/oracle', '--native', folder, '--out', run.path / ('artifacts/comparison-C-' + profile + '.json')])
            command('source-collapsed-actual-paint-' + profile, [sys.executable, ROOT / 'tools/check_collapsed_paint.py',
                '--fixtures', frozen / 'cases-shared.json', '--oracle', run.path / 'artifacts/oracle', '--native', folder,
                '--out', run.path / ('artifacts/comparison-collapsed-' + profile + '.json')])
            command('source-event-actual-paint-' + profile, [sys.executable, ROOT / 'tools/check_eventmodeling_paint.py',
                '--fixtures', frozen / 'cases-event.json', '--oracle', run.path / 'artifacts/oracle', '--native', folder,
                '--out', run.path / ('artifacts/comparison-event-' + profile + '.json')])
        command('closure-specific-five-formats', [sys.executable, ROOT / 'tools/bulk_export.py', '--fixtures', frozen / 'cases.json',
            '--profiles', *args.profiles, '--out', run.path / 'artifacts/closure-exports', '--case-ids',
            'CLOSURE-A-cynefin-double-unknown', 'CLOSURE-A-architecture-multiline-services', 'CLOSURE-A-abnf-comment-line',
            'CLOSURE-A-zen-escaped', 'CLOSURE-A-c4-boundary-unknown-sprite', 'CL-B-DATE-WEEKDAY', 'CL-B-AXIS-LOCALE',
            'CL-B-AGENT-GENUINE-SOURCE-VALID', 'CLOSURE-C-self-curved-reverse', 'CLOSURE-C-arrow-gallery-rtl',
            'CLOSURE-C-central-reverse-dual-rtl', 'CLOSURE-C-important-message-paint',
            'CLOSURE-EVENT-chain-revisit', 'CLOSURE-EVENT-data', 'CLOSURE-EVENT-reset-multi',
            'CLOSURE-EVENT-MULTILINE-JSON-AUDIT', 'CLOSURE-EVENT-LITERAL-DATA-HTML'], env={'TZ': 'UTC'})
        if args.regressions:
            for group in ('bootstrap', 'dependencies', 'f011', 'f012', 'f013', 'f014', 'math', 'bulk', 'html_host', 'pixel_compare', 'tooling', 'vchart_integration', 'vchart_dsl'):
                command('regression-' + group, [sys.executable, '-m', 'unittest', 'discover', '-s', ROOT / 'tests' / group, '-v'])
        if args.install:
            packages = run.path / 'artifacts/development-release'
            if command('build-development-candidate', [sys.executable, ROOT / 'tools/release_package.py', 'build', '--out', packages, '--allow-dirty']):
                command('fresh-development-wheel-and-sdist', [sys.executable, ROOT / 'tools/release_package.py', 'install', '--manifest', packages / 'release-manifest.json',
                    '--packages', packages / 'packages', '--out', run.path / 'artifacts/development-install', '--allow-dirty'], timeout=2400)
        if args.historical:
            command('full-retained-historical-static-matrix', [sys.executable, ROOT / 'tools/run_bulk.py', 'final', '--profiles', *args.profiles,
                '--skip-legacy-pixels', '--scope-note', 'Non-VChart closure candidate. Venn/Treemap/provider limits are user-delegated to py-vchart; no chart expansion in this batch.', *(['--oracle', args.historical_oracle.resolve(strict=True)] if args.historical_oracle else []),
                *(['--legacy-oracle-root', args.legacy_oracle_root.resolve(strict=True)] if args.legacy_oracle_root else [])], timeout=7200)
        if args.vchart:
            command('existing-vchart-dsl-all-types-matrix', [sys.executable, ROOT / 'tools/run_vchart_dsl.py', '--phase', 'final', '--profiles', *args.profiles], timeout=3600)
        run.data['testToolsUnchanged'] = all(file_identity(ROOT / name) == value for name, value in run.data['testTools'].items())
        run.data['functionalStatus'] = 'FAILED' if any(row['exitCode'] for row in run.data['commands']) else 'CHECKS_PASSED_ACTUAL_VISUAL_REVIEW_AND_RELEASE_GATES_REQUIRED'
        run.save()
    print(json.dumps({'run': str(run.path), 'status': run.data['status'], 'sourceUnchanged': run.data['sourceUnchanged'], 'testToolsUnchanged': run.data['testToolsUnchanged']}))
    return int(run.data['status'] != 'SUCCESS' or not run.data['sourceUnchanged'] or not run.data['testToolsUnchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
