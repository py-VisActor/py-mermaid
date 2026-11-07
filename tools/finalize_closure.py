"""Verify closed closure evidence without rendering or inferring publication.

Actual source exceptions and Windows NOT_VERIFIED DST cases remain explicit.
A passing computational receipt is not Linux CI, visual review or a release.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import zipfile
import hashlib

from run_support import ROOT,file_identity,verify_run,write_json

COMMIT='1fb7869866dd619168d840291c9c54b4f129758b'
PROFILES=('cpu','auto','gpu')
REQUIRED={'freeze-independent-inputs','source-A-getters-and-geometry','source-B-calendar-and-actual-ELK',
          'source-all-static-draws','source-original-branch-C-ABNF','original-branch-regressions','native-B-independent-values-and-real-layouts','source-B-parity','closure-specific-five-formats',
          *('closure-unit-'+name for name in ('parser','dates','layout','sequence','collapsed','eventmodeling')),
          *('source-event-actual-paint-'+name for name in PROFILES),
          *('native-static-'+name for name in PROFILES),*('source-collapsed-actual-paint-'+name for name in PROFILES),*('source-C-actual-paint-'+name for name in PROFILES)}

def require(ok,message):
    if not ok:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def relative(path):
    p=Path(path).resolve()
    return p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p)
def proof(path):return {'path':relative(path),**file_identity(Path(path))}
def child(base,name):
    p=Path(name);require(not p.is_absolute() and '..' not in p.parts,'Unsafe artifact path')
    original=base/p;p=original.resolve(strict=True)
    require(p.is_relative_to(base.resolve()) and p.is_file() and not original.is_symlink(),'Unsafe/nonfile artifact')
    return p
def indexed(rows):
    require(isinstance(rows,list),'Expected a record list')
    result={row['id']:row for row in rows}
    require(len(result)==len(rows) and len({str(key).casefold() for key in result})==len(result),'Duplicate IDs')
    return result

_runs={}
def closed(path,source=None):
    path=Path(path).resolve(strict=True)
    if path not in _runs:
        data=read(path/'run.json')
        require(data.get('status')=='SUCCESS' and data.get('finishedAtUtc'),'Run is not closed SUCCESS: '+str(path))
        require(data.get('sourceUnchanged') is True,'Run source changed: '+str(path))
        commands=data.get('commands',[])
        require(commands and len({c['name'] for c in commands})==len(commands),'Missing/duplicate command records')
        require(all(c.get('exitCode')==0 and c.get('status')=='SUCCESS' and c.get('finishedAtUtc') for c in commands),'Failed/unclosed command')
        integrity=verify_run(path)
        require(integrity['integrityStatus']=='PASS','Run integrity failed: '+str(integrity['errors'][:4]))
        _runs[path]=data
    data=_runs[path]
    if source:require(data['source']['sourceTreeSha256']==source,'Different nested candidate: '+str(path))
    return path,data

def methods(run,data):
    counts={}
    for command in data['commands']:
        text='\n'.join(child(run,command[k]).read_text(encoding='utf8') for k in ('stdout','stderr'))
        values=[int(x) for x in re.findall(r'Ran (\d+) tests? in ',text)]
        if values:
            require('FAILED (' not in text and len(re.findall(r'^OK(?: \([^\n]*\))?\s*$',text,re.M))>=len(values),
                    'Missing real unittest OK: '+command['name'])
            counts[command['name']]={'methods':sum(values),'suites':values,
                                    'skipped':sum(int(x) for x in re.findall(r'^OK \(skipped=(\d+)\)',text,re.M))}
    for name in ('closure-unit-parser','closure-unit-dates','closure-unit-layout','closure-unit-sequence','closure-unit-collapsed','closure-unit-eventmodeling','original-branch-regressions'):
        require(name in counts and counts[name]['methods']>0,'Missing real unit execution: '+name)
    return counts

def capsule(run,data):
    path=child(run,'artifacts/candidate.zip')
    require(file_identity(path)==data['candidateArchive'],'Candidate archive changed')
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist();require(len(names)==len(set(names)),'Duplicate archive names')
        for name in names:require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Unsafe archive member')
        for name,digest in data['source']['files'].items():
            require(hashlib.sha256(archive.read(name)).hexdigest()==digest,'Archived source differs: '+name)
        for name,expected in data['testTools'].items():
            raw=archive.read(name)
            require({'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}==expected,'Archived test/tool differs: '+name)
        refs={group:json.loads(archive.read('references/closure-'+group+'-assertions.json')) for group in ('A','B','C')}
        scope=json.loads(archive.read('references/closure-batch-scope.json'))
        inputs={Path(name).stem[len('cases-'):]:archive.read(name) for name in names if name.startswith('tests/closure/cases-') and name.endswith('.json')}
        require({'A','B','C','shared','event'}<=set(inputs),'Missing closure input groups')
    return refs,scope,inputs

def frozen(run,source,inputs):
    folder=run/'artifacts/frozen';identity=read(folder/'identity.json')
    require(identity['source']['sourceTreeSha256']==source and identity.get('productBehaviorExecuted') is False,'Frozen source identity differs')
    raw={}
    for group in inputs:
        file=folder/('cases-'+group+'.json');actual=file_identity(file)
        require(actual==identity['inputs']['tests/closure/cases-'+group+'.json'],'Frozen raw input identity differs')
        require(file.read_bytes()==inputs[group],'Raw input differs from candidate archive')
        raw[group]=read(file)
    all_rows=indexed(read(folder/'all-cases.json')['cases']);rendered=indexed(read(folder/'cases.json')['cases'])
    browser=indexed(read(folder/'browser-cases.json')['cases'])
    require(set(browser)==set(rendered) and set(rendered)<=set(all_rows),'Frozen rendered/browser input denominator differs')
    for key,row in rendered.items():
        require(row==all_rows[key] and {k:v for k,v in browser[key].items() if k!='browserResources'}==row,'Normalized browser inputs changed')
    derived={'all':len(all_rows),'renderOrError':len(rendered),'parserOnly':len(all_rows)-len(rendered)}
    require(identity['counts']==derived and identity['groups']==dict(Counter(r['group'] for r in rendered.values())),'Dynamic frozen counts differ')
    require(sum(len(doc['cases']) for doc in raw.values())==len(all_rows),'Raw group denominator differs')
    return raw,rendered,identity

def source_and_profiles(run,source,raw,rendered):
    source_a=read(run/'artifacts/source-A/results.json')
    require(source_a['status']=='PASS' and not source_a['errors'] and source_a['sourceIdentity']['commit']==COMMIT,'Source A producer failed')
    a=indexed(source_a['cases']);require(set(a)=={r['id'] for r in raw['A']['cases']},'Source A case denominator differs')
    require(source_a['fixture']['sha256']==file_identity(run/'artifacts/frozen/cases-A.json')['sha256'],'Source A fixture identity differs')
    require(all(not row['errors'] for row in a.values()),'Source A predicate errors')
    require(source_a.get('geometryControls') and all(not c['errors'] for c in source_a['geometryControls']),'Source A geometry control missing/failed')
    b=read(run/'artifacts/comparison-B.json');source_b=read(run/'artifacts/source-B/values/oracle-b.json')
    extra_b=read(run/'artifacts/source-B/source-extra.json');browser_b=read(run/'artifacts/source-B/browser-manifest.json')
    fixture=file_identity(run/'artifacts/frozen/cases-B.json')['sha256']
    require(all(doc['fixtureSha256']==fixture for doc in (b,source_b,extra_b,browser_b)),'B source/input identity differs')
    require(source_b['identity']['commit']==COMMIT and source_b['identity']['bundleSha256']==extra_b['identity']['bundleSha256']==browser_b['identity']['bundleSha256'],'B fixed original identity differs')
    require(len(b['rows'])==len(raw['B']['pureProbes'])+len(raw['B']['sourceProbes']),'B pure denominator differs')
    indexed(b['rows']);bcases=indexed(b['cases'])
    require(set(bcases)=={r['id'] for r in raw['B']['cases']},'B diagram denominator differs')
    require(all(row['status'] in ('PASS','SOURCE_EXCEPTION') for row in b['rows']),'B value parity failed')
    pending=[r for r in b['cases'] if r['status']=='NOT_VERIFIED']
    allowed_pending={r['id'] for r in raw['B']['cases'] if r.get('closure',{}).get('nativeRequiresRealTZ')}
    require(all(r['status']=='PASS' or r['id'] in allowed_pending and r['status']=='NOT_VERIFIED' for r in b['cases']),'B layout parity failed')
    if pending:require(run_platform(run).startswith('Windows'),'Linux real TZ was not verified')
    require(b['status']==('PASS_WITH_EXPLICIT_UNVERIFIED' if pending else 'PASS'),'B comparison summary contradicts records')
    original=read(run/'artifacts/oracle/manifest.json');original_cases=indexed(original['cases'])
    require(set(original_cases)==set(rendered) and original['identity']['commit']==COMMIT,'Original rendered denominator/source differs')
    require(original['fixtureSha256']==file_identity(run/'artifacts/frozen/browser-cases.json')['sha256'],'Original rendered input changed')
    profiles=[]
    for profile in PROFILES:
        folder=run/('artifacts/native-'+profile);native=read(folder/'results.json');identity=read(folder/'identity.json')
        require(native['sourceUnchanged'] is True and native['source']['sourceTreeSha256']==identity['source']['sourceTreeSha256']==source,'Profile candidate mismatch')
        require(native['backend']==identity['backend']==profile and native['failed']==0,'Native profile failed')
        cases=indexed(native['cases']);require(set(cases)==set(rendered),'Native profile denominator differs')
        for key,row in cases.items():
            error=rendered[key]['expect'] in ('syntax_error','error')
            require(row['status']==('EXPECTED_ERROR' if error else 'CHECKS_PASSED'),'Unexpected native case status: '+key)
            if error:
                require(original_cases[key]['status']=='error','Original did not reject expected error: '+key)
                require(not rendered[key].get('expectedErrorCodes') or row['errorCode'] in rendered[key]['expectedErrorCodes'],'Wrong native error code')
            else:
                require(original_cases[key]['status']=='captured' and row.get('checks')==[],'Original/native draw incomplete: '+key)
                require(row.get('controls') and all(row['controls'].values()),'No-op/content mutation control failed')
                require((folder/(key+'.png')).is_file() and (folder/(key+'.scene.json')).is_file(),'Actual PNG/scene absent')
                engine=row['backend']['renderer'];require(engine==('CPU' if profile=='cpu' else 'GPU') if profile!='auto' else engine in ('CPU','GPU'),'Actual backend differs')
        c=read(run/('artifacts/comparison-C-'+profile+'.json'));crows=indexed(c['cases'])
        require(c['status']=='PASS' and c['nativeSourceUnchanged'] is True and c['nativeSource']['sourceTreeSha256']==source,'C profile predicates failed')
        require(set(crows)=={r['id'] for r in raw['C']['cases']} and c['fixtureCount']==len(crows),'C denominator differs')
        require(all(r['status']=='VERIFIED' and not r['sourceErrors'] and not r['nativeErrors'] for r in crows.values()),'C source/native predicate mismatch')
        cp=run/('artifacts/comparison-collapsed-'+profile+'.json');paint=read(cp);prows=indexed(paint['cases'])
        require(paint['status']=='PASS' and paint['sourceIndependent'] is True and paint['nativeSource']['sourceTreeSha256']==source,'Collapsed actual-paint comparison failed')
        require(set(prows)=={r['id'] for r in raw['shared']['cases']},'Collapsed actual-paint denominator differs')
        require(paint['fixture']['sha256']==file_identity(run/'artifacts/frozen/cases-shared.json')['sha256'],'Collapsed fixture changed')
        require(all(r['status']=='PASS' and not r['errors'] and r.get('negativeControls') and all(r['negativeControls'].values()) for r in prows.values()),'Collapsed paint/pixel controls failed')
        ep=run/('artifacts/comparison-event-'+profile+'.json');event=read(ep);erows=indexed(event['cases'])
        require(event['status']=='PASS' and event['nativeSource']['sourceTreeSha256']==source,'Event actual-paint comparison failed')
        require(set(erows)=={r['id'] for r in raw['event']['cases']},'Event actual-paint denominator differs')
        require(event['fixture']['sha256']==file_identity(run/'artifacts/frozen/cases-event.json')['sha256'],'Event fixture changed')
        require(all(r['status']=='PASS' and not r['errors'] and r.get('negativeControls') and all(r['negativeControls'].values()) for r in erows.values()),'Event nonocclusion/pixel controls failed')
        profiles.append({'backend':profile,'cases':len(cases),'statuses':dict(Counter(r['status'] for r in cases.values())),
                         'eventPaintCases':len(erows),'comparisonEvent':proof(ep),
                         'sourceCPredicates':len(crows),'collapsedPaintCases':len(prows),'comparisonCollapsed':proof(cp),'results':proof(folder/'results.json'),'comparisonC':proof(run/('artifacts/comparison-C-'+profile+'.json'))})
    return {'sourceA':{'cases':len(a),'result':proof(run/'artifacts/source-A/results.json')},
            'sourceB':{'pure':len(raw['B']['pureProbes']),'host':len(raw['B']['sourceProbes']),'cases':len(bcases),
                       'sourceExceptions':[r for r in b['rows'] if r['status']=='SOURCE_EXCEPTION'],
                       'notVerified':pending,'result':proof(run/'artifacts/comparison-B.json')},'profiles':profiles}

def run_platform(run):return read(run/'run.json')['environment']['platform']

def exports(run,source,rendered):
    directory=run/'artifacts/closure-exports';data=read(directory/'exports.json')
    require(data['schema']=='py-mermaid-bulk-exports/v1' and data['sourceUnchanged'] is True and data['source']['sourceTreeSha256']==source,'Export candidate mismatch')
    requested=data['requestedCaseIds'];require(requested and len(set(requested))==len(requested) and set(requested)<=set(rendered),'Export requested input denominator differs')
    expected={(case,profile,fmt) for case in requested for profile in PROFILES for fmt in ('png','jpg','webp','svg','pdf')}
    rows=data['cases'];require(len(rows)==len(expected) and {(r['fixture'],r['backend'],r['format']) for r in rows}==expected,'Export combinations missing/duplicated')
    require(len({r['artifact'].casefold() for r in rows})==len(rows),'Export paths collide')
    for row in rows:
        require(row['status']=='CHECKS_PASSED' and row['errors']==[],'Export did not pass')
        file=child(directory,row['artifact'])
        require(file_identity(file)=={k:row[k] for k in ('sha256','bytes')},'Saved export SHA/bytes differs')
        engine=row['actualBackend']['renderer']
        require(engine==('CPU' if row['backend']=='cpu' else 'GPU') if row['backend']!='auto' else engine in ('CPU','GPU'),'Export actual backend differs')
        raw=file.read_bytes()
        if row['format']=='pdf':require(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-2048:],'Invalid actual PDF file')
        elif row['format']=='svg':
            from xml.etree import ElementTree
            require(ElementTree.fromstring(raw).tag.endswith('svg'),'Invalid actual SVG file')
        else:
            from PIL import Image
            with Image.open(file) as image:
                require(image.size==(row['width'],row['height']),'Saved raster size mismatch')
    return {'requestedCaseIds':requested,'profiles':list(PROFILES),'formats':['png','jpg','webp','svg','pdf'],
            'actualSavedFiles':len(rows),'result':proof(directory/'exports.json')}

def original_b_freeze(raw_b):
    directory=ROOT/'references/closure-source-B';provenance=read(directory/'provenance.json')
    require(provenance['role']=='FIXED_ORIGINAL_ONLY_NOT_NATIVE_GOLDENS' and provenance['fixedCommit']==COMMIT,'Frozen B source role/identity differs')
    for entry in provenance['entries']:
        require(file_identity(child(directory,entry['path']))=={k:entry[k] for k in ('sha256','bytes')},'Frozen original B bytes changed')
    require(read(directory/'cases-B.json')==raw_b,'Frozen source B inputs differ from final inputs')
    donor=provenance['originalRun'];path=ROOT/donor['path'];data=read(path/'run.json')
    require(file_identity(path/'run.json')==donor['manifest'] and data['finishedAtUtc'],'Original donor manifest changed/unclosed')
    command=next(c for c in data['commands'] if c['name']==donor['sourceCommand'])
    require(command['exitCode']==donor['sourceCommandExitCode']==0,'Original source donor command failed')
    for entry in provenance['entries']:
        origin=(ROOT/entry['originalArtifact']).resolve(strict=True)
        require(origin.is_relative_to(path.resolve()),'Original donor path escaped Run')
        require(data['artifacts'][origin.relative_to(path).as_posix()]=={k:entry[k] for k in ('sha256','bytes')},'Frozen source not a recorded original artifact')
    return {'provenance':proof(directory/'provenance.json'),'counts':provenance['counts'],
            'originalDonorStatus':donor['status'],'sourceProducerExitCode':0,
            'note':'Failing full original donor preserved; only successful source producer reused. No native observations frozen as original.'}

def visual_receipt(path,run,source):
    data=read(path)
    require(data.get('status')=='PASS' and data.get('sourceTreeSha256')==source and (ROOT/data.get('candidateRun','')).resolve()==run,
            'Visual review candidate/status differs')
    attachments=[]
    def visit(value):
        if isinstance(value,dict):
            name=value.get('rawPath') or value.get('path')
            if isinstance(name,str) and 'sha256' in value and 'bytes' in value:
                file=Path(name);file=(file if file.is_absolute() else ROOT/file).resolve(strict=True)
                require(file.is_relative_to(ROOT) and file.is_file(),'Visual attachment outside repository')
                require(file_identity(file)=={k:value[k] for k in ('sha256','bytes')},'Visual attachment changed: '+str(file))
                attachments.append(proof(file))
            for child_value in value.values():visit(child_value)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(data)
    require(any(Path(p['path']).suffix.lower() in ('.png','.jpg','.webp','.svg') for p in attachments),
            'Visual receipt has no actual reviewed image byte identities')
    return {'receipt':proof(path),'attachmentsChecked':attachments}

def installations(run,data,source):
    if not any(c['name']=='fresh-development-wheel-and-sdist' for c in data['commands']):return []
    summary=read(run/'artifacts/development-install/installation.json')
    require(summary['status']=='PASS' and summary['sourceTreeSha256']==source,'Development install summary failed')
    rows=summary['installations'];require(len(rows)==2 and {r['kind'] for r in rows}=={'wheel','sdist'},'Both actual artifact installs required')
    results=[]
    for row in rows:
        nested=Path(row['manifest']).resolve().parent;_,record=closed(nested,source)
        native=read(nested/'artifacts/installed/result.json');units=read(nested/'artifacts/unit-contracts/result.json')
        require(row['status']==native['status']==units['status']=='PASS' and native['isolated'] is True and units['isolated'] is True,'Installed artifact verification failed')
        require(native['actualMathGlyphs'] is True and native['realELK'] is True and native['forbiddenProductionFallbacks'] is False,'Installed real native capabilities missing')
        require(len(native['vchart'])==len({r['type'] for r in native['vchart']})==68 and all(r['status']=='PASS' for r in native['vchart']),'Installed supplier68 incomplete')
        comparison=read(nested/'artifacts/installed-B-comparison.json')
        require(comparison['status'] in ('PASS','PASS_WITH_EXPLICIT_UNVERIFIED'),'Installed original B parity failed')
        unverified=[r['id'] for r in comparison['cases'] if r['status']=='NOT_VERIFIED']
        require(not unverified or run_platform(nested).startswith('Windows'),'Actual Linux TZ evidence missing from installed artifact')
        for export in native['exports']:
            require(file_identity(nested/('artifacts/installed/representative.'+export['format']))=={k:export[k] for k in ('sha256','bytes')},'Installed export fingerprint differs')
        results.append({'kind':row['kind'],'run':relative(nested),'manifest':proof(nested/'run.json'),
                        'installed':proof(nested/'artifacts/installed/result.json'),'unitContracts':proof(nested/'artifacts/unit-contracts/result.json'),
                        'originalParity':proof(nested/'artifacts/installed-B-comparison.json'),'unverifiedRealTZ':unverified,
                        'sourceTreeSha256':record['source']['sourceTreeSha256'],'artifact':row['distribution']})
    return results

def branch_coverage(refs,scope,raw,results):
    families=scope['functionalFamilies'];expected=[branch for family in families for branch in family['branches']]
    require(len(expected)==len(set(expected))==scope['originalUnrepairedBranchRecords'],'Original branch denominator changed')
    aset=set(refs['A']['coverage']['knownNineGapBranches']);bset={r['id'] for r in refs['B']['legacyBranchSource']}
    mapped=[]
    for family in families:
        for branch in family['branches']:
            if branch in aset:
                group='A';evidence={'referenceField':'closure-A-assertions.coverage.knownNineGapBranches',
                    'sourceResult':results['sourceA']['result'],'unitCommand':'closure-unit-parser',
                    'mappingDepth':'Declared source/test group coverage, not invented per-expression exhaustive coverage'}
            elif branch in bset:
                group='B';evidence={'referenceField':'closure-B-assertions.legacyBranchSource','sourceParity':results['sourceB']['result'],
                    'unitCommands':['closure-unit-dates','closure-unit-layout'],'mappingDepth':'Full frozen B source/helper/public-case group checked; specific legacy branch declared in source assertions'}
            else:
                candidates=[r['id'] for r in raw['C']['cases'] if r['closureProbe'].get('branch')==branch or 'C-sequence-'+r['closureProbe']['type']==branch]
                require(candidates,'Original branch has no actual assertion mapping: '+branch)
                group='C';evidence={'caseIds':candidates,'profilePredicates':[p['comparisonC'] for p in results['profiles']],
                    'unitCommand':'closure-unit-sequence'}
            mapped.append({'id':branch,'family':family['id'],'group':group,'status':'SCOPED_SOURCE_AND_NATIVE_EVIDENCE_VERIFIED','evidence':evidence})
    require(len(mapped)==len(expected),'Missing old branch mapping')
    return mapped

def nested_runs(run,data,source):
    result=[]
    for name in ('full-retained-historical-static-matrix','existing-vchart-dsl-all-types-matrix'):
        commands=[c for c in data['commands'] if c['name']==name]
        if not commands:continue
        text=child(run,commands[0]['stdout']).read_text(encoding='utf8');candidates=[]
        for line in text.splitlines():
            try:record=json.loads(line)
            except ValueError:continue
            if isinstance(record,dict) and isinstance(record.get('run'),str):candidates.append(Path(record['run']))
        require(candidates,'Nested command emitted no actual Run: '+name)
        candidate,child_data=closed(candidates[-1],source)
        if 'testToolsUnchanged' in child_data:require(child_data['testToolsUnchanged'] is True,'Nested tools changed')
        summaries=[]
        if name=='existing-vchart-dsl-all-types-matrix':
            for backend in PROFILES:
                path=candidate/('artifacts/matrix-'+backend+'/result.json');matrix=read(path)
                require(matrix['backend']==backend and matrix['sourceUnchanged'] is True and matrix['source']['sourceTreeSha256']==source and matrix['failed']==0,'Nested DSL matrix failed')
                require(all(row['status']=='PASS' and row['exactPixels'] is True for row in matrix['cases']),'Nested DSL row failed')
                summaries.append({'backend':backend,'cases':len(matrix['cases']),'types':len(matrix['types']),'result':proof(path),
                                  'exportFiles':sum(len(row.get('exports',[])) for row in matrix['cases'])})
        else:
            for path in candidate.glob('artifacts/**/results.json'):
                doc=read(path)
                if 'failed' in doc and isinstance(doc.get('cases'),list):
                    require(doc['failed']==0,'Nested historical group failed: '+str(path))
                    summaries.append({'result':proof(path),'cases':len(doc['cases']),'backend':doc.get('backend')})
        require(summaries,'Nested Run has no real result summaries')
        result.append({'command':name,'run':relative(candidate),'manifest':proof(candidate/'run.json'),'status':child_data['status'],'results':summaries})
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--visual-review',type=Path)
    args=parser.parse_args();run,data=closed(args.run);source=data['source']['sourceTreeSha256']
    require(data['scope']=='CLOSURE-P4' and data.get('testToolsUnchanged') is True,'Need frozen final closure P4')
    require(REQUIRED<={c['name'] for c in data['commands']},'Final command denominator incomplete')
    refs,scope,inputs=capsule(run,data);raw,rendered,identity=frozen(run,source,inputs)
    counts=methods(run,data);results=source_and_profiles(run,source,raw,rendered)
    branches=branch_coverage(refs,scope,raw,results);nested=nested_runs(run,data,source)
    export_result=exports(run,source,rendered);frozen_b=original_b_freeze(raw['B'])
    installed=installations(run,data,source)
    legacy_source=read(run/'artifacts/original-branch-C-ABNF/abnf.json')
    require(legacy_source['package']=='@mermaid-js/parser@2.0.1' and legacy_source.get('cases'),'Fresh fixed original legacy parser evidence missing')
    branch_log=next(c for c in data['commands'] if c['name']=='original-branch-regressions')
    branch_text='\n'.join(child(run,branch_log[k]).read_text(encoding='utf8') for k in ('stdout','stderr'))
    info_method='test_all_eleven_theme_version_roles_and_existing_css_override'
    require(info_method in branch_text,'Info dark-role retained regression was not executed')
    visual=None
    if args.visual_review:
        visual=visual_receipt(args.visual_review,run,source)
    output=args.out.resolve();require(not output.is_relative_to(run),'Cannot write into closed P4')
    output.parent.mkdir(parents=True,exist_ok=True)
    result={'schema':'py-mermaid-closure-verification/v1','status':'PASS','candidateRun':relative(run),'sourceTreeSha256':source,
        'meaning':'Closed computational closure evidence; not an inferred publication or exhaustive branch proof',
        'runManifest':proof(run/'run.json'),'frozenCounts':identity['counts'],'frozenGroups':identity['groups'],
        'unittest':counts,'totalMethods':sum(r['methods'] for r in counts.values()),'results':results,'originalBranchRecords':len(branches),
        'branchEvidence':branches,'nestedRuns':nested,'installations':installed,'visualReview':visual,
        'actualExports':export_result,'frozenOriginalB':frozen_b,
        'additionalRetainedRepairs':[{'id':'info-dark-three-theme-textColor','status':'SCOPED_REGRESSION_EXECUTED_PASS',
            'notPartOfOriginal22':True,'evidence':{'command':'original-branch-regressions','method':info_method,
            'stdout':proof(child(run,branch_log['stdout'])),'stderr':proof(child(run,branch_log['stderr']))},
            'scope':'All11theme version roles and CSS override assertion was executed; extra dark3role fix is not hidden in the original22 count.'}],
        'linuxRealTZVerifiedInThisRun':not bool(results['sourceB']['notVerified']) and not run_platform(run).startswith('Windows'),
        'remainingExternalReleaseGates':['Formal clean reviewed wheel/sdist installation on Windows and Linux']+(['Linux actual-TZ installed artifact evidence'] if results['sourceB']['notVerified'] else [])+([] if visual else ['Actual manual raw-image review']),
        'publicationStatus':'NOT_INFERRED_FROM_LOCAL_TESTS','supplierDelegation':scope.get('userDelegatedToVChart'),
        'limits':['Source exceptions retained separately from native failures.','Windows aware-offset arithmetic is not Linux system timezone verification.',
                  'Original22 are finite source-declared branch groups; no arbitrary configuration cross-product coverage claimed.',
                  'Venn4/Treemap formatting and supplier field audit remain user-delegated; no chart capability expansion.']}
    write_json(output,result,exclusive=True);print(json.dumps({'status':'PASS','out':str(output),'sourceTreeSha256':source,'methods':result['totalMethods'],'branches':len(branches)}));return 0

if __name__=='__main__':raise SystemExit(main())
