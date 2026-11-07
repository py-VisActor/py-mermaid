"""Finalize closed VChart/Mermaid evidence, never run products or infer PASS from HTML.

PASS means the declared retained local static contract, not a PyPI publication.
The exact 22 legacy gaps and two source-valid embedding restrictions stay visible.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from run_support import ROOT,file_identity,verify_run,write_json

PROFILES=('cpu','auto','gpu')
KINDS={'pie','quadrantChart','xychart','radar','treemap','sankey','venn'}
COMMIT='1fb7869866dd619168d840291c9c54b4f129758b'
WHEEL='45b66f82d0c74a8d15306b117d93ad2d88c26d2997719306336bcc92b7ce49e2'
SDIST='fee51a35d75b7f8572e76b0028d63c833f6e01c670c7ea41dc412386b3bcef7f'
REQUIRED={'host-pip-check','supplier-unit','supplier-strict-reference','bridge-contracts','mermaid-original',
          'regression-bootstrap','regression-dependencies',
          *('supplier-native-'+b for b in PROFILES),*('mermaid-native-'+b for b in PROFILES),
          *('regression-'+n for n in ('f011','f012','f013','f014','math','bulk','html_host','pixel_compare','tooling'))}


def require(value,message):
    if not value:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def resolve(path):
    p=Path(path);return (p if p.is_absolute() else ROOT/p).resolve(strict=True)
def proof(path):
    p=resolve(path)
    try:name=p.relative_to(ROOT).as_posix()
    except ValueError:name=str(p)
    return {'path':name,**file_identity(p)}
def checked(item,base=ROOT):
    p=Path(item['path']);p=(p if p.is_absolute() else base/p).resolve(strict=True)
    actual=file_identity(p)
    require(actual['sha256']==item['sha256'],'Evidence SHA changed: '+str(p))
    if 'bytes' in item:require(actual['bytes']==item['bytes'],'Evidence size changed: '+str(p))
    return p
def rows_by_id(rows,expected,label):
    ids=[r['id'] for r in rows]
    require(len(ids)==len(set(ids)) and set(ids)==set(expected),label+' ID denominator mismatch')
    return {r['id']:r for r in rows}
def closed_run(path,source=None):
    path=resolve(path);data=read(path/'run.json')
    require(data.get('status')=='SUCCESS' and data.get('finishedAtUtc'),'Run must be closed SUCCESS: '+str(path))
    require(data.get('sourceUnchanged') is True,'Run source changed: '+str(path))
    if source:require(data['source']['sourceTreeSha256']==source,'Run is not the same candidate: '+str(path))
    require(data.get('commands') and all(c.get('exitCode')==0 and c.get('status')=='SUCCESS' and c.get('finishedAtUtc') for c in data['commands']),
            'Run has unsuccessful/unclosed commands: '+str(path))
    integrity=verify_run(path)
    require(integrity['integrityStatus']=='PASS','Closed run artifacts changed: '+str(integrity['errors'][:5]))
    return data
def command_methods(run,data):
    result={}
    for command in data['commands']:
        text='\n'.join((run/command[k]).read_text(encoding='utf8') for k in ('stdout','stderr'))
        counts=[int(n) for n in re.findall(r'Ran (\d+) tests? in ',text)]
        if counts:
            require('FAILED (' not in text and len(re.findall(r'^OK\s*$',text,re.M))>=len(counts),
                    'Unittest completion is not OK: '+command['name'])
            result[command['name']]=counts
    for name in ('supplier-unit','bridge-contracts'):
        require(result.get(name) and sum(result[name])>0,'Missing real unittest completion: '+name)
    return result


def archive_candidate(run,data):
    p=run/'artifacts/consumer-candidate.zip';manifest=read(run/'artifacts/consumer-candidate.json')
    require(file_identity(p)==data['consumerCandidateArchive'],'Candidate archive fingerprint mismatch')
    with zipfile.ZipFile(p) as z:
        names=z.namelist();require(len(names)==len(set(names)) and set(names)==set(manifest),'Candidate archive entries mismatch')
        for name in names:
            require(not name.startswith('/') and '..' not in Path(name).parts,'Unsafe candidate archive entry')
            raw=z.read(name);require({'sha256':sha(raw),'bytes':len(raw)}==manifest[name],'Candidate archive member changed: '+name)
        for name,digest in data['source']['files'].items():
            require(manifest.get(name,{}).get('sha256')==digest,'Product bytes differ from source snapshot: '+name)
        for name,identity in data['hostTestSources'].items():require(manifest.get(name)==identity,'Host test snapshot changed: '+name)
        require(manifest.get('tools/run_vchart_validation.py')==data['validationTool'],'Validation driver not archived exactly')
        original=z.read('tests/vchart_integration/cases-mermaid-charts.json')
    return {'archive':proof(p),'manifest':proof(run/'artifacts/consumer-candidate.json')},json.loads(original)


def supplier_contract(run,data):
    require(data.get('supplierSourceUnchanged') is True,'Supplier source changed')
    release=data['supplierRelease'];require(release['dirtySource'] is False and release['version']=='0.1.1','Unreviewed supplier build')
    distributions=release['distributions']
    require({v['sha256'] for v in distributions.values()}=={WHEEL,SDIST},'Supplier distribution bytes changed')
    expected={p.removeprefix('tests/cases/').removesuffix('/spec.json') for p in data['supplierInputs'] if p.endswith('/spec.json')}
    require(len(expected)==225,'Supplier fixed input denominator changed')
    profiles=[]
    for backend in PROFILES:
        directory=run/('artifacts/native-'+backend);native=read(directory/'result.json')
        require(native['status']=='PASS' and native['cases']==native['passed']==225,'Supplier native contract incomplete')
        require(native['backend']==backend and native['version']==release['version'],'Supplier profile/version mismatch')
        require(len(native['types'])==len(set(native['types']))==68 and set(native['types'])==set(native['exportedTypes']),
                'Supplier 68 type/export denominator mismatch')
        require('site-packages' in native['module'],'Supplier imported checkout instead of installed package')
        rows=rows_by_id(native['results'],expected,'Supplier '+backend)
        for id,row in rows.items():
            require(row['status']=='PASS','Supplier case failed: '+id)
            for key,file in [('specSha256','spec.json'),('expectedPngSha256','expected.png'),('expectedSceneSha256','expected.scene.json')]:
                require(row['source'][key]==data['supplierInputs']['tests/cases/'+id+'/'+file]['sha256'],'Supplier source input mismatch '+id)
            for fmt,asset in row['exports'].items():checked({'path':str(directory/id/('actual.'+fmt)),**asset})
        profiles.append(proof(directory/'result.json'))
    reference=read(run/'artifacts/reference/report.json')
    require(reference['passed'] is True and reference['types']==68 and reference['cases']==225,'Unchanged strict reference gate failed')
    flat=[(kind+'/'+case,row) for kind,cases in reference['results'].items() for case,row in cases.items()]
    require({id for id,_ in flat}==expected and all(row['passed'] for _,row in flat),'Reference case denominator/failure')
    return {'release':release,'native':profiles,'reference':proof(run/'artifacts/reference/report.json')}


def dsl_contract(run,data,frozen):
    directory=run/'artifacts';fixtures=read(directory/'mermaid-oracle.fixtures.json')
    # bulk_capture normalizes group; no source/config/expectation may change.
    frozen_cases=frozen['cases']+frozen.get('unsupportedCases',[])
    rows=rows_by_id(fixtures['cases'],[c['id'] for c in frozen_cases],'Frozen DSL input')
    for case in frozen_cases:
        actual=dict(rows[case['id']]);actual.pop('group',None);expected=dict(case);expected.pop('group',None)
        require(actual==expected,'DSL fixture changed after candidate archive: '+case['id'])
    require(len(rows)==42 and {r['kind'] for r in rows.values()}==KINDS,'DSL source denominator changed')
    rendered={id for id,c in rows.items() if c['expect']=='render' and not c.get('nativeExpectedErrorCodes')}
    negatives={id for id,c in rows.items() if c['expect']=='syntax_error'}
    restricted={id for id,c in rows.items() if c.get('nativeExpectedErrorCodes')}
    require((len(rendered),len(negatives),len(restricted))==(30,10,2),'DSL classification changed')
    oracle=read(directory/'mermaid-oracle/manifest.json')
    require(oracle['identity']['package']=='mermaid@12.2.0' and oracle['identity']['commit']==COMMIT,'Canonical Mermaid source changed')
    require(oracle['fixtureSha256']==file_identity(directory/'mermaid-oracle.fixtures.json')['sha256'],'Original fixture SHA mismatch')
    original=rows_by_id(oracle['cases'],rows,'Original DSL')
    for id,row in original.items():
        require(row['status']==('error' if id in negatives else 'captured'),'Original source status mismatch: '+id)
        require((directory/'mermaid-oracle'/ (id+('.error.json' if id in negatives else '.json'))).is_file(),'Missing original raw JSON '+id)
        if id not in negatives:require((directory/'mermaid-oracle'/(id+'.png')).is_file(),'Missing original raw PNG '+id)
    bridge=read(directory/'bridge-specs/result.json')
    supplier_types=set(read(directory/'native-cpu/result.json')['types'])
    require(len(bridge['cases'])==68 and {r['type'] for r in bridge['cases']}==supplier_types and all(r['status']=='PASS' for r in bridge['cases']),
            'Mermaid public VChart bridge 68 types incomplete')
    proofs=[]
    for backend in PROFILES:
        p=directory/('mermaid-'+backend);native=read(p/'results.json')
        require(native['sourceUnchanged'] is True and native['source']['sourceTreeSha256']==data['source']['sourceTreeSha256'],'DSL profile candidate changed')
        require(native['failed']==0 and native['normalRendered']==30 and native['restrictionDiagnostics']==2,'DSL profile checks failed')
        require(set(native['exportedKinds'])==KINDS and set(native['exportFormats'])=={'svg','pdf','jpg','webp'},'DSL export matrix incomplete')
        export_matrix={kind:[] for kind in KINDS}
        cases=rows_by_id(native['cases'],rows,'DSL '+backend)
        for id,row in cases.items():
            if id in rendered:
                require(row['status']=='CHECKS_PASSED' and not row.get('checks'),'Native render failed: '+id)
                require(row['controls']['whiteNoopRejected'] is True,'No-op control missing: '+id)
                require((p/(id+'.png')).is_file() and (p/(id+'.scene.json')).is_file(),'Missing actual native scene/PNG '+id)
                exports=row.get('exports',[])
                if exports:
                    require(len(exports)==4 and {a['format'] for a in exports}=={'svg','pdf','jpg','webp'},'DSL static exports incomplete '+id)
                    export_matrix[row['kind']].append(id)
                for asset in exports:
                    path=checked(asset);require(path.is_relative_to(p.resolve()),'Export points outside candidate profile')
            elif id in negatives:require(row['status']=='EXPECTED_ERROR' and row['errorCode'] in rows[id]['expectedErrorCodes'],'Source syntax error mismatch '+id)
            else:require(row['status']=='DIAGNOSTIC_ERROR' and row['nativeRestrictionOnly'] is True and row['errorCode'] in rows[id]['nativeExpectedErrorCodes'],'Restriction hidden/misclassified '+id)
        require(all(len(ids)==1 for ids in export_matrix.values()),'DSL exports must cover exactly one positive per kind (28 assets/profile)')
        proofs.append(proof(p/'results.json'))
    return {'fixture':proof(directory/'mermaid-oracle.fixtures.json'),'oracle':proof(directory/'mermaid-oracle/manifest.json'),
            'bridge':proof(directory/'bridge-specs/result.json'),'profiles':proofs},rendered,rows


def visual_contract(path,run,source,rendered):
    review=read(path)
    require(review.get('verdict') in ('PASS','PASS_WITH_DOCUMENTED_SOURCE_DIFFERENCES'),'Visual review is not positive human acceptance')
    require(resolve(review['baselineRun'])==run,'Visual review is bound to an old candidate run')
    if review.get('sourceTreeSha256'):require(review['sourceTreeSha256']==source,'Visual source SHA mismatch')
    require(review['actualViewedPairs']==len(rendered),'Visual pair count mismatch')
    rows=rows_by_id(review['cases'],rendered,'Visual review')
    for id,row in rows.items():
        require(row['binding']=='PASS' and row['visualConclusion'] in ('PASS','PASS_WITH_DOCUMENTED_SOURCE_DIFFERENCES'),
                'Unaccepted actual visual case '+id)
        require(bool(row.get('observation')),'Human visual observation missing '+id)
        for profile,dirname in [('oracle','mermaid-oracle'),('cpu','mermaid-cpu')]:
            item=row['images'][profile];p=checked(item)
            require(p==(run/'artifacts'/dirname/(id+'.png')).resolve(),'Visual is not final raw '+profile+' PNG '+id)
            method=item.get('reviewMethod')
            if profile=='oracle' and method=='SHA256_IDENTICAL_TO_PREVIOUS_ACTUALLY_VIEWED_RAW_ORIGINAL':
                previous=item.get('previousReview') or review.get('previousOriginalReview')
                require(previous,'Missing actual prior source review proof '+id)
                older=read(checked(previous));old=next(c for c in older['cases'] if c['id']==id)['images']['oracle']
                checked(old);require(old['sha256']==item['sha256'] and old['reviewMethod']=='actual_raw_view_image','Original reuse was never actually viewed '+id)
            else:require(method=='actual_raw_view_image','Visual review is automatic/hash-only '+id)
    return proof(path)


def installation_contract(paths,source):
    result=[];modes=[]
    for path in paths:
        path=resolve(path);run=closed_run(path,source);mode=run['result']['artifactKind'];modes.append(mode)
        require(mode in ('wheel','sdist'),'Unknown fresh installation mode')
        installed=read(path/'artifacts/installed/result.json')
        require(installed['status']=='PASS' and installed['isolated'] is True and installed['renderedTypes']==68,'Fresh installation incomplete')
        require(installed['forbiddenProductionImports'] is False and installed['mathGlyphVerified'] is True,'Installed runtime imports/math failed')
        require(installed['versions']['py-visactor-vchart']=='0.1.1' and installed['versions']['py-skia-canvas']=='0.1.0a18','Installed dependency versions differ')
        direct=installed['vchartDirectUrl'];require(direct['archive_info']['hashes']['sha256']==WHEEL and '/releases/download/py-visactor-vchart-v0.1.1/' in direct['url'],
                'Installed supplier is not the approved exact release asset')
        require(any(WHEEL in d for d in installed['mermaidRequiresDist']),'Dependency metadata lacks approved supplier hash')
        require(len(installed['cases'])==68 and all(c['status']=='PASS' for c in installed['cases']),'Fresh install 68 PNG cases failed')
        require(installed['realELK']['nodes']>0 and installed['realELK']['edges']>0 and set(installed['vectorExports'])=={'svg','pdf'},'Installed ELK/vector checks missing')
        for module,p in installed['modulePaths'].items():
            if module.startswith(('py_mermaid','py_vchart','py_katex','pyelk')):require('site-packages' in p,'Installed import leaked checkout '+module)
        resolver=next(c for c in run['commands'] if c['name']=='resolver-install')
        require('--no-deps' not in resolver['argv'] and '--find-links' not in resolver['argv'] and 'https://pypi.org/simple' in resolver['argv'],
                'Fresh install bypassed normal dependency resolution')
        require(run['result']['pypiStatus']=='blocked','PyPI publication status misrepresented')
        result.append({'mode':mode,'manifest':proof(path/'run.json'),'installed':proof(path/'artifacts/installed/result.json')})
    require(sorted(modes)==['sdist','wheel'],'Need two independent wheel/sdist fresh installations')
    return result


def ci_contract(path):
    path=resolve(path);ci=read(path);base=path.parent
    api=read(base/'github-evidence.json')
    require(ci['workflowConclusion']=='failure' and api['run']['conclusion']=='failure','Do not declare complete CI workflow successful')
    require(len([j for j in api['jobs'] if j['name'].startswith('validate ') and j['conclusion']=='success'])==4,'Four CI validation jobs required')
    require(next(j for j in api['jobs'] if j['name']=='publish')['conclusion']=='failure' and next(j for j in api['jobs'] if j['name']=='verify')['conclusion']=='skipped','PyPI failure status missing')
    artifacts={a['id']:a for a in api['artifacts']}
    require(len(ci['matrix'])==len(artifacts)==4 and {m['artifactId'] for m in ci['matrix']}==set(artifacts),
            'CI artifacts incomplete/duplicated')
    for matrix in ci['matrix']:
        archive=checked(matrix['zip'],base);require('sha256:'+file_identity(archive)['sha256']==artifacts[matrix['artifactId']]['digest'],'CI ZIP is not API digest')
        with zipfile.ZipFile(archive) as z:
            install=json.loads(z.read('install/result.json'));require(install['status']=='PASS','CI install failed')
            for mode,digest in [('wheel',WHEEL),('sdist',SDIST)]:
                require(install['installations'][mode]['distribution']['sha256']==digest,'CI installed distribution mismatch')
                r=json.loads(z.read('install/'+mode+'/render/result.json'))
                require(r['status']=='PASS' and r['passed']==r['cases']==225 and len(r['types'])==68 and 'site-packages' in r['module'],'CI native result incomplete')
                require(len(r['results'])==225 and all(x['status']=='PASS' for x in r['results']),'CI actual225 incomplete')
                log=z.read('install/'+mode+'/native-host-contracts.stderr.log').decode()
                require(re.search(r'Ran 36 tests in ',log) and re.search(r'\nOK\s*$',log) and 'skipped=' not in log,'CI36 methods incomplete')
                require('skia-python' not in z.read('install/'+mode+'/install.stdout.log').decode().lower(),'CI installed forbidden default runtime')
    return {'summary':proof(path),'api':proof(base/'github-evidence.json'),'validationJobs':4,'externalInstallations':8,'casesPerInstallation':225,'nativeMethodsPerInstallation':36}


def release_contract(path):
    path=resolve(path);release=read(path)
    require(release['draft'] is False and release['prerelease'] is False and release['tag_name']=='py-visactor-vchart-v0.1.1','GitHub release is not stable reviewed tag')
    for digest in (WHEEL,SDIST):require(any(a.get('digest')=='sha256:'+digest and a['state']=='uploaded' for a in release['assets']),'GitHub release asset SHA missing')
    run=next((p for p in path.parents if (p/'run.json').is_file()),None);require(run,'Release proof lacks closed Run')
    closed_run(run)
    return proof(path)


def finalize(args):
    run=resolve(args.p4);data=closed_run(run);source=data['source']['sourceTreeSha256']
    require(REQUIRED<={c['name'] for c in data['commands']},'P4 required command groups missing')
    candidate,frozen=archive_candidate(run,data)
    methods=command_methods(run,data)
    supplier=supplier_contract(run,data);dsl,rendered,rows=dsl_contract(run,data,frozen)
    visual=visual_contract(resolve(args.visual_review),run,source,rendered)
    installs=installation_contract(args.install_runs,source)
    ci=ci_contract(args.ci_summary);release=release_contract(args.release_proof)
    return {'schema':'py-mermaid-vchart-acceptance/v1','status':'PASS','candidateRun':proof(run/'run.json')['path'].removesuffix('/run.json'),
        'sourceTreeSha256':source,'p4Manifest':proof(run/'run.json'),'candidateArchive':candidate,
        'scope':'DECLARED_RETAINED_STATIC_LOCAL_ACCEPTED','unittestMethodsByCommand':methods,
        'supplier':supplier,'mermaid':dsl,'visualReview':visual,'freshInstallations':installs,'ciValidation':ci,
        'publication':{'github':'STABLE_RELEASED','releaseProof':release,'pypi':'BLOCKED_INVALID_PUBLISHER',
                       'workflowConclusion':'failure','verify':'skipped'},
        'remaining':{'legacyConfirmedBranchGaps':22,'sourceValidEmbeddingRestrictions':[{'id':id,'reason':rows[id]['reason']} for id in rows if rows[id].get('nativeExpectedErrorCodes')],
                     'exclusions':['Dagre','interaction','video/audio','arbitrary HTML/CSS extension']},
        'limits':'PASS is not a PyPI publication, arbitrary static option completion, or exact native/reference pixel equivalence.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--p4',required=True,type=Path);parser.add_argument('--visual-review',required=True,type=Path)
    parser.add_argument('--install-runs',required=True,nargs=2,type=Path);parser.add_argument('--ci-summary',required=True,type=Path)
    parser.add_argument('--release-proof',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(argv);out=args.out.resolve();require(not out.exists(),'Output directory must be new')
    out.mkdir(parents=True)
    try:
        summary=finalize(args);write_json(out/'summary.json',summary)
        print(json.dumps({'status':'PASS','summary':str(out/'summary.json')}));return 0
    except Exception as exc:
        write_json(out/'rejection.json',{'status':'REJECTED','reason':type(exc).__name__+': '+str(exc)})
        print(json.dumps({'status':'REJECTED','reason':str(exc)}));return 2


if __name__=='__main__':raise SystemExit(main())
