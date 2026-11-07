"""Build/publish iteration pages with standard logs; optionally verify via a local server."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from run_support import ROOT, Run, file_identity


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,default=ROOT/'tools/report_specs/iteration-rounds.json')
    parser.add_argument('--page-size',type=int,default=12)
    parser.add_argument('--publish-dir',type=Path,default=ROOT/'reports')
    parser.add_argument('--base-url',help='Already running report server URL, e.g. http://127.0.0.1:8765/; enables browser QA')
    args=parser.parse_args()
    spec=args.spec.resolve(strict=True);document=json.loads(spec.read_text('utf8'))
    with Run('REPORT-ROUNDS','delivery') as run:
        run.input(spec)
        for item in document['sourceReport'].values():run.input(ROOT/item['path'])
        for group in document['rounds']:
            for name in group.get('caseFiles',[]):run.input(ROOT/name)
        for entry in document.get('history',[]):run.input(ROOT/entry['html']['path'])
        for name in ('tools/build_report_rounds.py','tools/qa_report_rounds.cjs','tools/run_report_rounds.py'):
            run.input(ROOT/name)
        generated=run.path/'report/iterations'
        result=run.command('paginate-original-report',[sys.executable,str(ROOT/'tools/build_report_rounds.py'),
            '--spec',str(spec),'--out',str(generated),'--page-size',str(args.page_size)],timeout=180)
        if result['exitCode']:return result['exitCode']
        target=args.publish_dir.resolve()/run.id
        shutil.copytree(generated,target)
        run.data['publishedArtifacts']={str(path):file_identity(path) for path in target.rglob('*') if path.is_file()}
        run.data['result']={'report':str(target/'index.html'),'reportManifest':str(target/'report.json')}
        if args.base_url:
            url=args.base_url.rstrip('/')+'/'+run.id+'/index.html'
            run.data['result']['reportUrl']=url
            qa=run.command('paged-browser-qa',['node',str(ROOT/'tools/qa_report_rounds.cjs'),
                '--url',url,'--report',str(target/'report.json'),'--out',str(run.path/'artifacts/viewer')],timeout=180)
            if qa['exitCode']:return qa['exitCode']
        run.event('report_published',**run.data['result'])
    print(json.dumps({'runId':run.id,'status':run.data['status'],'sourceUnchanged':run.data['sourceUnchanged'],
        'browserQA':'EXECUTED' if args.base_url else 'NOT_EXECUTED',**run.data['result']},ensure_ascii=False))
    return int(run.data['status']!='SUCCESS')


if __name__=='__main__':
    raise SystemExit(main())
