"""Copy verified source captures and refresh selected cases into a NEW directory.

The donor remains immutable. Reuse requires identical IDs and execution inputs
(text/config/offline resources); changed cases must be explicitly refreshed.
Fresh and reused captures must have exactly the same fixed-source identity.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from run_support import ROOT, file_identity, write_json

KEYS=('cases','negativeCases','renderErrorCases','unsupportedCases')


def case_inputs(fixture):
    result={}
    for category in KEYS:
        for case in fixture.get(category,[]):
            if case['id'] in result:raise ValueError('Duplicate oracle case ID')
            result[case['id']]={'category':category,**{key:case.get(key) for key in ('text','config','resources')}}
    return result


def validate_reuse(previous,current,refresh):
    old,new=case_inputs(previous),case_inputs(current)
    if set(old)-set(new):raise ValueError('Oracle denominator removed cases; capture the revised source baseline explicitly')
    if not (set(new)-set(old))<=refresh:raise ValueError('Added oracle cases must be explicitly refreshed')
    if not refresh<=set(new):raise ValueError('Unknown refreshed oracle ID')
    for identifier in new:
        if identifier not in refresh and old[identifier]!=new[identifier]:raise ValueError('Oracle execution input changed: '+identifier)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--source-fixtures',type=Path,required=True)
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--refresh',nargs='*',default=[])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--node',default='node')
    args=parser.parse_args();refresh=set(args.refresh)
    previous=json.loads(args.source_fixtures.read_text(encoding='utf-8'));current=json.loads(args.fixtures.read_text(encoding='utf-8'))
    validate_reuse(previous,current,refresh)
    manifest=json.loads((args.source/'manifest.json').read_text(encoding='utf-8'))
    if any(row['status']=='error' and row['id'] not in refresh for row in manifest['cases']):raise ValueError('Unrefreshed failed source case')
    subset={**({'scope':current['scope']} if 'scope' in current else {}),**{key:[case for case in current.get(key,[]) if case['id'] in refresh] for key in KEYS}}
    subset_path=args.out.parent/'oracle-refresh-cases.json';write_json(subset_path,subset,exclusive=True)
    fresh=args.out.with_name(args.out.name+'-refreshed')
    capture=[args.node,str(ROOT/'tools/oracle/f011_capture.cjs'),'--out',str(fresh)]
    capture += ['--fixtures',str(subset_path)] if refresh else ['--verify-only']
    subprocess.run(capture,check=True)
    identity=json.loads((args.source/'identity.json').read_text(encoding='utf-8'))
    fresh_identity=json.loads((fresh/'identity.json').read_text(encoding='utf-8'))
    if identity!=fresh_identity:raise ValueError('Fixed oracle identity changed')
    fresh_manifest=json.loads((fresh/'manifest.json').read_text(encoding='utf-8')) if refresh else {'cases':[]}
    if any(row['status']=='error' for row in fresh_manifest['cases']):raise ValueError('Refreshed source case failed')
    args.out.mkdir(exist_ok=False)
    reused={}
    for path in args.source.iterdir():
        if path.is_symlink() or not path.is_file():raise ValueError('Oracle donor must contain only regular capture files')
        target=args.out/path.name;shutil.copyfile(path,target)
        if path.name not in {'manifest.json','identity.json'} and not any(path.name.startswith(identifier+'.') for identifier in refresh):
            if file_identity(target)!=file_identity(path):raise ValueError('Reused capture bytes changed')
            reused[path.name]=file_identity(path)
    for path in fresh.iterdir():
        if path.name not in {'manifest.json','identity.json'}:shutil.copyfile(path,args.out/path.name)
    replacements={row['id']:row for row in fresh_manifest['cases']}
    previous_ids={row['id'] for row in manifest['cases']}
    manifest['cases']=[replacements.get(row['id'],row) for row in manifest['cases']]+[row for row in fresh_manifest['cases'] if row['id'] not in previous_ids]
    manifest['reuse']={'source':str(args.source.resolve()),'refresh':sorted(refresh),'verifiedUnchangedFiles':reused,
                       'sourceFixture':file_identity(args.source_fixtures),'currentFixture':file_identity(args.fixtures)}
    write_json(args.out/'manifest.json',manifest)
    print(json.dumps({'out':str(args.out),'refreshed':sorted(refresh),'reusedFiles':len(reused),'identityUnchanged':True}))


if __name__=='__main__':main()
