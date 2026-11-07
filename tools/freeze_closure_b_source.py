"""Freeze only verified original B observations from a closed source producer.

The enclosing Run may have FAILED for unrelated commands. This operation does
not upgrade that Run or claim candidate acceptance; native output is never an
eligible source artifact. The output directory must not exist.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from run_support import ROOT,file_identity,verify_run,write_json

COMMIT='1fb7869866dd619168d840291c9c54b4f129758b'
BUNDLE='ffd1a76f0553952a344c68a9b1502dd5cfb6faab72541307b74679c5abc9cec8'
MAP='8b844955879bad4b284a9603827b8268f11ecb57cd0fbf2f338c24e2afa99679'
PRODUCER='source-B-calendar-and-actual-ELK'

def require(condition,message):
    if not condition:raise ValueError(message)

def read(path):return json.loads(path.read_text(encoding='utf8'))

def inside(path,parent):
    path=path.resolve(strict=True)
    require(path.is_relative_to(parent.resolve()) and path.is_file(),'Artifact escaped donor: '+str(path))
    return path

def freeze(directory,out):
    directory=directory.resolve(strict=True)
    require(directory.is_relative_to(ROOT.resolve()),'Donor must be a repository Run')
    require(not out.resolve().is_relative_to(directory),'Output must not alter the closed donor Run')
    require(not out.exists(),'Output already exists; archive previous bytes separately')
    integrity=verify_run(directory)
    require(integrity['integrityStatus']=='PASS','Donor integrity failed: '+str(integrity['errors']))
    manifest=read(directory/'run.json')
    require(manifest['status'] in ('SUCCESS','FAILED') and manifest['finishedAtUtc'],'Donor is not closed')
    commands=[c for c in manifest['commands'] if c['name']==PRODUCER]
    require(len(commands)==1,'Expected exactly one source producer')
    command=commands[0]
    require(command['exitCode']==0 and command['status']=='SUCCESS' and command['finishedAtUtc'],'Source producer failed/unclosed')
    argv=command['argv']
    fixture=inside(Path(argv[argv.index('--fixtures')+1]),directory)
    source=Path(argv[argv.index('--out')+1]).resolve(strict=True)
    require(source==directory/'artifacts/source-B','Unexpected source output directory')

    def recorded(path):
        path=inside(path,directory);identity=file_identity(path)
        require(manifest['artifacts'].get(path.relative_to(directory).as_posix())==identity,'Unrecorded/changed donor artifact: '+str(path))
        return identity

    fixture_identity=recorded(fixture);doc=read(fixture)
    browser=read(source/'browser-manifest.json');pure=read(source/'values/oracle-b.json');host=read(source/'source-extra.json')
    for item in (browser,pure,host):
        require(item['fixtureSha256']==fixture_identity['sha256'],'Source fixture identity mismatch')
        require(item['identity']['bundleSha256']==BUNDLE and item['identity']['mapSha256']==MAP,'Fixed original bundle/map mismatch')
    require(pure['identity']['commit']==host['identity']['commit']==COMMIT,'Fixed original commit mismatch')

    def rows_match(inputs,actual,label):
        expected={r['id']:r for r in inputs};observed={r['id']:r for r in actual}
        require(len(expected)==len(inputs) and len(observed)==len(actual) and expected.keys()==observed.keys(),label+' denominator mismatch')
        for key,row in expected.items():
            require(row['kind']==observed[key]['kind'] and row['input']==observed[key]['input'],label+' actual input changed: '+key)
            if 'timezone' in row:require(row['timezone']==observed[key]['timezone'],label+' timezone mismatch: '+key)
    rows_match(doc['pureProbes'],pure['rows'],'Pure original')
    rows_match(doc['sourceProbes'],host['rows'],'Host original')
    cases=doc['cases'];ids=[r['id'] for r in cases]
    require(len(set(ids))==len(ids) and len({v.casefold() for v in ids})==len(ids),'Duplicate/nonportable case IDs')
    require({r['id'] for r in browser['results']}==set(ids) and len(browser['results'])==len(ids),'Browser denominator mismatch')
    require(all(r['status']=='CAPTURED' for r in browser['results']),'Browser source capture failed')
    for row in cases:
        actual=read(source/(row['id']+'.json'))
        require(actual['id']==row['id'] and actual['status']=='CAPTURED' and actual['source']==row['source'] and actual['config']==row['config'],'Browser original input changed: '+row['id'])
        require(actual['timezone']==row.get('closure',{}).get('timezone','UTC'),'Browser timezone changed')
        require(set(actual['publicPaint'])=={'ticks','cherries','collapsed'},'Missing updated public paint observer')

    # Verify locked source contents and every module reported by the source VM.
    bundle=ROOT/'.local/f011-oracle/node_modules/mermaid/dist/mermaid.js'
    require(file_identity(bundle)['sha256']==BUNDLE and file_identity(Path(str(bundle)+'.map'))['sha256']==MAP,'Local fixed source identity drift')
    source_map=read(Path(str(bundle)+'.map'))
    modules=dict(zip(source_map['sources'],source_map['sourcesContent']))
    for item in pure['identity']['modules']+host['identity']['modules']:
        name=item.get('name',item.get('path'))
        if item.get('repository')=='mermaid-checkout':
            raw=(ROOT/'.local/upstream-mermaid/packages/mermaid/src'/name).read_bytes()
        else:
            require(name in modules,'Unknown fixed VM module: '+name)
            raw=modules[name].encode('utf8')
        require(hashlib.sha256(raw).hexdigest()==item['sha256'],'Fixed source module changed: '+name)
    wrapper=ROOT/'tools/oracle/closure_b.cjs'
    wrapper_identity=command['toolFiles'].get(str(wrapper))
    require(wrapper_identity is not None,'Source command has no wrapper fingerprint')
    archive=directory/'artifacts/candidate.zip';archive_identity=recorded(archive)
    with zipfile.ZipFile(archive) as zipped:
        raw=zipped.read('tools/oracle/closure_b.cjs')
    require({'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}==wrapper_identity,'Archived original wrapper differs from actual producer')

    selected=[('cases-B.json',fixture),('browser-manifest.json',source/'browser-manifest.json'),
              ('values/oracle-b.json',source/'values/oracle-b.json'),('source-extra.json',source/'source-extra.json')]
    selected.extend((row['id']+'.json',source/(row['id']+'.json')) for row in cases)
    entries=[]
    for name,path in selected:
        entries.append({'path':name,**recorded(path),'originalArtifact':path.relative_to(ROOT).as_posix()})
    # No writes occur until all donor/input/source/archive checks have passed.
    out.mkdir(parents=True,exist_ok=False)
    for (name,path),entry in zip(selected,entries):
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
        require(file_identity(target)=={k:entry[k] for k in ('sha256','bytes')},'Copied bytes changed')
    provenance={'schema':'py-mermaid-closure-B-frozen-original/v1',
        'role':'FIXED_ORIGINAL_ONLY_NOT_NATIVE_GOLDENS','status':'SOURCE_BYTES_VERIFIED',
        'fixedCommit':COMMIT,'bundleSha256':BUNDLE,'mapSha256':MAP,'fixture':fixture_identity,
        'counts':{'pure':len(doc['pureProbes']),'host':len(doc['sourceProbes']),'browser':len(cases)},
        'originalRun':{'path':directory.relative_to(ROOT).as_posix(),'manifest':file_identity(directory/'run.json'),
            'status':manifest['status'],'sourceCommand':PRODUCER,'sourceCommandExitCode':0,
            'producerStdout':{'path':command['stdout'],**recorded(directory/command['stdout'])},
            'producerStderr':{'path':command['stderr'],**recorded(directory/command['stderr'])}},
        'originalWrapper':{'path':'tools/oracle/closure_b.cjs',**wrapper_identity,
            'archive':archive.relative_to(ROOT).as_posix(),'archiveIdentity':archive_identity},
        'entries':entries,'sourcePublicPaintObserver':True,
        'note':'Successful original source command only. Enclosing donor status retained; not final candidate acceptance. No native data frozen.'}
    write_json(out/'provenance.json',provenance,exclusive=True)
    return {'out':str(out),'counts':provenance['counts'],'entries':len(entries),
            'provenance':file_identity(out/'provenance.json'),'donorStatus':manifest['status']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(freeze(args.run,args.out.resolve()),indent=2))

if __name__=='__main__':main()
