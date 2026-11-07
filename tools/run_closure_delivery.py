"""Deliver one closed closure candidate with paged, byte-preserving evidence."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from run_support import ROOT, Run, file_identity, source_identity, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--visual-review', required=True, type=Path)
    parser.add_argument('--base-url', default='http://127.0.0.1:8765/')
    args = parser.parse_args()
    candidate = args.run.resolve(strict=True)
    manifest = json.loads((candidate / 'run.json').read_text('utf8'))
    if manifest['source'] != source_identity():
        raise ValueError('Current product differs from the closed candidate')
    with Run('CLOSURE-P5', 'delivery') as run:
        print(run.path, flush=True)
        for path in [candidate / 'run.json', args.visual_review]:
            run.input(path)
        tools = run.path / 'artifacts/tools'
        tools.mkdir()
        for name in ['run_closure_delivery.py', 'finalize_closure.py', 'build_closure_report.py', 'qa_closure_report.cjs']:
            path = ROOT / 'tools' / name
            run.input(path)
            shutil.copyfile(path, tools / name)
        acceptance = run.path / 'artifacts/acceptance.json'
        report = ROOT / 'reports' / run.id
        url = args.base_url.rstrip('/') + '/' + run.id + '/index.html'
        steps = [
            ('finalize-same-candidate-evidence', [sys.executable, ROOT / 'tools/finalize_closure.py',
                '--run', candidate, '--out', acceptance, '--visual-review', args.visual_review]),
            ('build-paged-static-report', [sys.executable, ROOT / 'tools/build_closure_report.py',
                '--fixtures', candidate / 'artifacts/frozen/cases.json', '--oracle', candidate / 'artifacts/oracle',
                '--native', *[candidate / ('artifacts/native-' + p) for p in ('cpu', 'auto', 'gpu')],
                '--out', report, '--acceptance', acceptance, '--visual-review', args.visual_review]),
            ('verify-live-report-and-attachments', ['node', ROOT / 'tools/qa_closure_report.cjs',
                '--report', report, '--out', run.path / 'artifacts/report-qa', '--url', url]),
        ]
        for name, argv in steps:
            result = run.command(name, list(map(str, argv)), timeout=1800)
            print(name, result['exitCode'], flush=True)
            if result['exitCode']:
                return 1
        write_json(run.path / 'artifacts/delivery.json', {
            'candidateRun': candidate.relative_to(ROOT).as_posix(),
            'sourceTreeSha256': manifest['source']['sourceTreeSha256'],
            'acceptance': file_identity(acceptance), 'reportManifest': file_identity(report / 'manifest.json'),
            'reportUrl': url, 'status': 'LOCAL_STATIC_DELIVERY_NOT_PUBLICATION',
        }, exclusive=True)
        run.data['functionalStatus'] = 'DELIVERED_LOCAL_STATIC_EVIDENCE_RELEASE_GATES_SEPARATE'
        run.save()
    print(json.dumps({'run': str(run.path), 'status': run.data['status'], 'reportUrl': url}))
    return int(run.data['status'] != 'SUCCESS' or not run.data['sourceUnchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
