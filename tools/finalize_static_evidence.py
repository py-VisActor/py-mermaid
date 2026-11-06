"""Join same-candidate static evidence before its enclosing Run closes.

This reads actual comparison/unittest results and verifies source identities.
It performs no rendering, installation, building or publishing itself.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from run_support import source_identity, write_json


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--profiles',nargs='+',required=True)
    parser.add_argument('--unit-runs',nargs='+',type=Path,required=True)
    parser.add_argument('--regression-run',type=Path,required=True)
    parser.add_argument('--out-spec',type=Path,required=True)
    args=parser.parse_args();candidate=read(args.artifacts/'source-candidate.json')
    if source_identity()!=candidate:raise ValueError('Product candidate changed during acceptance')
    checksum=candidate['sourceTreeSha256'];fixture=read(args.artifacts/'cases.json');profiles={};passed=True
    for profile in args.profiles:
        result=read(args.artifacts/('compare-'+profile)/'report.json')
        row={}
        for key in ('cases','negativeCases','renderErrorCases','unsupportedCases'):
            expected={case['id'] for case in fixture.get(key,[])};actual=[case['id'] for case in result.get(key,[])]
            if len(actual)!=len(set(actual)) or set(actual)!=expected:raise ValueError('Comparison denominator mismatch '+profile+'/'+key)
            row[key]=len(actual)
        row['functionalStatus']=result['functionalStatus'];profiles[profile]=row
        passed=passed and result['functionalStatus']=='PASS'
    methods=0;groups=[]
    for run in args.unit_runs:
        data=read(run/'run.json')
        if data['source']['sourceTreeSha256']!=checksum:raise ValueError('Unit evidence candidate mismatch')
        if data['status']!='RUNNING' and (data['status']!='SUCCESS' or not data.get('sourceUnchanged')):raise ValueError('Unit run was not a stable success')
        for command in data['commands']:
            argv=command['argv']
            if not any(argv[index:index+2]==['-m','unittest'] for index in range(len(argv)-1)):continue
            if command.get('exitCode')!=0:raise ValueError('A unit group did not pass')
            log=(run/command['stderr']).read_text(encoding='utf-8')
            counts=re.findall(r'^Ran (\d+) tests? in ',log,re.M)
            if not counts or not re.search(r'^OK\s*$',log,re.M):raise ValueError('Missing successful actual unittest result')
            count=int(counts[-1]);methods+=count;groups.append({'run':str(run),'group':command['name'],'passed':count})
    regressions=read(args.regression_run/'run.json')
    if regressions['source']['sourceTreeSha256']!=checksum or regressions['status']!='SUCCESS' or not regressions.get('sourceUnchanged'):raise ValueError('Legacy visual evidence mismatch or failure')
    legacy={}
    for scope in ('f011','f012','f013'):
        legacy[scope]={}
        for profile in ('cpu','auto','gpu'):
            result=read(args.regression_run/'artifacts'/scope/('compare-'+profile)/'report.json')
            if result['functionalStatus']!='PASS':raise ValueError('Legacy visual regression failed')
            legacy[scope][profile]={key:len(result.get(key,[])) for key in ('cases','negativeCases','renderErrorCases','unsupportedCases')}
    summary={'scope':'F01.4','sourceTreeSha256':checksum,'wheelSha256':None,
             'tests':{'passed':methods,'total':methods,'groups':groups},'profiles':profiles,
             'legacyVisualRegressions':{'run':str(args.regression_run),'profiles':legacy},
             'functionalStatus':'PASS' if passed else 'FAIL','installationValidation':{'status':'NOT_EXECUTED'},
             'note':'Actual same-candidate results; math independently deferred; Dagre/interaction excluded; no installation/build/publish'}
    write_json(args.artifacts/'summary.json',summary,exclusive=True)
    spec={'schema':'py-mermaid-render-report-spec/v1','scope':'F01.4','title':'流程图静态收口 · F01.4',
          'final':str(args.artifacts),'oracle':str(args.artifacts/'oracle'),'fixtures':str(args.artifacts/'cases.json'),
          'profiles':args.profiles,'defaultCase':'static-style-overview','exportSamples':str(args.artifacts/'static-exports')}
    write_json(args.out_spec,spec,exclusive=True)
    print(json.dumps({'functionalStatus':summary['functionalStatus'],'source':checksum,'unittestMethods':methods,'profiles':profiles}))
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
