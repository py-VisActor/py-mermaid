"""Publish a paginated DSL report from closed acceptance evidence, without rendering."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from run_support import ROOT, Run, file_identity, source_identity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--wheel', required=True, type=Path)
    p.add_argument('--sdist', required=True, type=Path)
    p.add_argument('--visual-review', required=True, type=Path)
    p.add_argument('--base-url', default='http://127.0.0.1:8765/')
    args = p.parse_args()
    candidate = args.run.resolve(strict=True)
    data = json.loads((candidate / 'run.json').read_text('utf-8'))
    if source_identity() != data['source']:
        raise ValueError('Current product differs from the frozen candidate')
    with Run('VCHART-DSL-P5', 'delivery') as run:
        print(run.path, flush=True)
        for path in (candidate / 'run.json', args.wheel / 'run.json', args.sdist / 'run.json', args.visual_review):
            run.input(path)
        archive = run.path / 'artifacts/tool-sources'
        archive.mkdir()
        for name in ('run_vchart_dsl_delivery.py', 'finalize_vchart_dsl_evidence.py',
                     'build_vchart_dsl_report.py', 'qa_vchart_dsl_report.cjs', 'run_support.py'):
            shutil.copyfile(ROOT / 'tools' / name, archive / name)
            assert file_identity(ROOT / 'tools' / name) == file_identity(archive / name)
        accepted = run.path / 'artifacts/acceptance.json'
        report = ROOT / 'reports' / run.id
        url = args.base_url.rstrip('/') + '/' + run.id + '/index.html'
        commands = [
            ('finalize-closed-evidence', [sys.executable, ROOT / 'tools/finalize_vchart_dsl_evidence.py',
             '--run', candidate, '--wheel', args.wheel, '--sdist', args.sdist,
             '--visual-review', args.visual_review, '--out', accepted]),
            ('build-round-six-report', [sys.executable, ROOT / 'tools/build_vchart_dsl_report.py',
             '--matrix', candidate / 'artifacts/matrix-cpu', '--acceptance', accepted,
             '--visual-review', args.visual_review, '--out', report]),
            ('qa-live-report', ['node', ROOT / 'tools/qa_vchart_dsl_report.cjs', '--report', report,
             '--url', url, '--out', run.path / 'artifacts/report-qa']),
        ]
        for name, argv in commands:
            result = run.command(name, list(map(str, argv)), timeout=600)
            print(name, result['exitCode'], flush=True)
            if result['exitCode']:
                return 1
        shutil.copyfile(report / 'manifest.json', run.path / 'artifacts/report-manifest.json')
        run.data['functionalStatus'] = 'DECLARED_DSL_STATIC_SCOPE_ACCEPTED_WITH_DOCUMENTED_LIMITS'
        run.data['result'] = {'url': url, 'report': str(report), 'acceptance': str(accepted),
                              'providerPublication': 'PyPI py-visactor-vchart==0.1.1 published',
                              'consumerPublication': 'Local implementation; not published by this task'}
        run.save()
    print(json.dumps({'run': str(run.path), 'status': run.data['status'], **run.data['result']}))
    return int(run.data['status'] != 'SUCCESS' or not run.data['sourceUnchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
