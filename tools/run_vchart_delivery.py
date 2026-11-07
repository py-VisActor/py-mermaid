"""Finalize and publish a new paginated VChart report from closed evidence."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from run_support import ROOT, Run, file_identity, source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--p4', required=True, type=Path)
    parser.add_argument('--visual-review', required=True, type=Path)
    parser.add_argument('--install-runs', required=True, nargs=2, type=Path)
    parser.add_argument('--ci-summary', required=True, type=Path)
    parser.add_argument('--release-proof', required=True, type=Path)
    parser.add_argument('--base-url', default='http://127.0.0.1:8765/')
    args = parser.parse_args()
    p4 = args.p4.resolve(strict=True)
    candidate = json.loads((p4 / 'run.json').read_text('utf-8'))
    if source_identity() != candidate['source']:
        raise ValueError('Current consumer differs from the reviewed candidate')
    with Run('VCHART-P5', 'delivery') as run:
        print(run.path, flush=True)
        inputs = [p4 / 'run.json', args.visual_review, args.ci_summary, args.release_proof]
        inputs += [path / 'run.json' for path in args.install_runs]
        for path in inputs:
            run.input(path)
        # Postprocessing tools may be newer than the runtime candidate capsule.
        tools = ['run_vchart_delivery.py', 'finalize_vchart_evidence.py',
                 'collect_vchart_report_inputs.py', 'build_vchart_report.py',
                 'build_report_rounds.py', 'qa_vchart_report.cjs', 'run_support.py']
        tool_dir = run.path / 'artifacts/tool-sources'
        tool_dir.mkdir()
        for name in tools:
            shutil.copyfile(ROOT / 'tools' / name, tool_dir / name)
            assert file_identity(ROOT / 'tools' / name) == file_identity(tool_dir / name)
        finalized = run.path / 'artifacts/accepted'
        normalized = run.path / 'artifacts/normalized'
        report = ROOT / 'reports' / run.id
        url = args.base_url.rstrip('/') + '/' + run.id + '/index.html'
        def command(name, argv):
            result = run.command(name, list(map(str, argv)), timeout=600)
            print(name, result['exitCode'], flush=True)
            return result['exitCode'] == 0
        if not command('finalize-accepted-evidence', [sys.executable, ROOT / 'tools/finalize_vchart_evidence.py',
                       '--p4', p4, '--visual-review', args.visual_review, '--install-runs', *args.install_runs,
                       '--ci-summary', args.ci_summary, '--release-proof', args.release_proof, '--out', finalized]):
            return 1
        if not command('normalize-closed-raw-evidence', [sys.executable, ROOT / 'tools/collect_vchart_report_inputs.py',
                       '--supplier', p4 / 'artifacts/native-cpu', '--bridge', p4 / 'artifacts/bridge-specs',
                       '--bridge-fixtures', ROOT / 'tests/vchart_integration/cases-vchart.json',
                       '--mermaid', p4 / 'artifacts/mermaid-cpu', '--oracle', p4 / 'artifacts/mermaid-oracle',
                       '--mermaid-fixtures', ROOT / 'tests/vchart_integration/cases-mermaid-charts.json', '--out', normalized]):
            return 1
        if not command('build-paginated-report', [sys.executable, ROOT / 'tools/build_vchart_report.py',
                       '--supplier', p4 / 'artifacts/native-cpu', '--bridge', normalized / 'bridge',
                       '--mermaid', normalized / 'mermaid', '--visual-review', args.visual_review,
                       '--acceptance', finalized / 'summary.json', '--out', report]):
            return 1
        if not command('qa-paginated-live-report', ['node', ROOT / 'tools/qa_vchart_report.cjs',
                       '--report', report, '--url', url, '--out', run.path / 'artifacts/report-qa']):
            return 1
        shutil.copyfile(report / 'manifest.json', run.path / 'artifacts/report-manifest.json')
        run.data['functionalStatus'] = 'DECLARED_STATIC_SCOPE_ACCEPTED_WITH_DOCUMENTED_LIMITS'
        run.data['result'] = {'report': str(report), 'url': url,
                              'acceptance': str(finalized / 'summary.json'),
                              'publication': 'GitHub stable released; PyPI blocked by invalid-publisher'}
        run.save()
    print(json.dumps({'run': str(run.path), 'status': run.data['status'], **run.data['result']}))
    return int(run.data['status'] != 'SUCCESS' or not run.data['sourceUnchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
