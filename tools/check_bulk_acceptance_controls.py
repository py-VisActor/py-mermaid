"""Adversarial read-only checks against a real final report build plan.

Plan JSON contains argv for build_bulk_report.py without --out/--acceptance.
All mutations and subprocess logs are retained below a new output directory.
No renderer is called and original evidence is never modified.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
from run_support import ROOT,file_identity,write_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True,type=Path)
    p.add_argument('--acceptance',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    args=p.parse_args();base=json.loads(args.plan.read_text('utf-8'))['argv']
    if '--out' in base or '--acceptance' in base:raise ValueError('Plan must omit output and acceptance arguments')
    original=json.loads(args.acceptance.read_text('utf-8'));args.out.mkdir(parents=True,exist_ok=False)
    rows=[]
    controls=[('wrong-candidate','Acceptance status/candidate differs'),
                          ('failed-whole-run','successful closed whole P4 candidate'),
                          ('changed-image-bytes','Acceptance evidence fingerprint differs'),
                          ('missing-kind-review','Visual review does not cover all retained kinds'),
                          ('missing-device-profile','complete fixture and three-profile report')]
    if original.get('htmlControlVerification'):
        controls.append(('missing-html-control-proof','HTML control verification incomplete'))
        controls.append(('missing-html-export-proof','HTML control exports incomplete'))
    if original.get('exportRepair'):
        controls.append(('missing-export-repair-proof','HTML export repair proof incomplete'))
    for name,expected in controls:
        directory=args.out/name;directory.mkdir();value=copy.deepcopy(original);argv=list(base)
        if name=='wrong-candidate':value['sourceTreeSha256']='0'*64
        elif name=='failed-whole-run':
            proof=json.loads((ROOT/value['p4Manifest']['path']).read_text('utf-8'));proof['status']='FAILED'
            target=directory/'controlled-failed-manifest.json';write_json(target,proof)
            value['p4Manifest']={'path':str(target.resolve()),**file_identity(target)}
        elif name in ('changed-image-bytes','missing-kind-review'):
            visual=json.loads((ROOT/value['visualReview']['path']).read_text('utf-8'))
            if name=='changed-image-bytes':visual['cases'][0]['native']['sha256']='0'*64
            else:
                kind=visual['cases'][-1]['kind'];visual['cases']=[c for c in visual['cases'] if c['kind']!=kind]
            target=directory/'controlled-visual-review.json';write_json(target,visual)
            value['visualReview']={'path':str(target.resolve()),**file_identity(target)}
        elif name=='missing-html-control-proof':value['htmlControlVerification']=[]
        elif name=='missing-html-export-proof':value.pop('htmlControlExports',None)
        elif name=='missing-export-repair-proof':value.pop('exportRepair',None)
        else:argv=[a for a in argv if not Path(a).name.startswith(('native-auto-','native-gpu-'))]
        acceptance=directory/'controlled-acceptance.json';write_json(acceptance,value)
        argv += ['--acceptance',str(acceptance),'--out',str(directory/'rejected-report')]
        completed=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=180,shell=False)
        (directory/'stdout.log').write_bytes(completed.stdout);(directory/'stderr.log').write_bytes(completed.stderr)
        passed=completed.returncode!=0 and expected in completed.stderr.decode('utf-8',errors='replace')
        row={'control':name,'expectedRejection':expected,'argv':argv,'exitCode':completed.returncode,'rejectedAsRequired':passed}
        write_json(directory/'command.json',row);rows.append(row)
    write_json(args.out/'controls.json',{'schema':'py-mermaid-report-acceptance-controls/v1','cases':rows,'status':'PASS' if all(r['rejectedAsRequired'] for r in rows) else 'FAIL'})
    print(json.dumps({'controls':len(rows),'passed':sum(r['rejectedAsRequired'] for r in rows)}))
    return int(not all(r['rejectedAsRequired'] for r in rows))


if __name__=='__main__':raise SystemExit(main())
