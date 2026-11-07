"""Reusable staged full-batch evidence runner. Never installs or publishes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import zipfile
from run_support import ROOT,Run,write_json,source_identity,file_identity


def main():
    p=argparse.ArgumentParser()
    p.add_argument('stage',choices=('first','final','report'))
    p.add_argument('--oracle',type=Path,help='Explicit existing fixed oracle directory; absent means fresh capture')
    p.add_argument('--native',nargs='+',type=Path,help='Existing native directories for report-only stage')
    p.add_argument('--fixtures',nargs='+',type=Path,default=[*sorted((ROOT/'tests/bulk').glob('cases-*.json')),*sorted((ROOT/'tests/html_host').glob('cases*.json'))])
    p.add_argument('--profiles',nargs='+',choices=('cpu','auto','gpu'),default=None)
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--legacy-oracle-root',type=Path,help='Fixed F01 source oracle parent, with f011/f012/f013/f014 subdirectories')
    p.add_argument('--skip-legacy-pixels',action='store_true',help='Skip only repeated legacy heatmaps; all legacy render/ink/semantic/geometry gates still execute')
    p.add_argument('--scope-note',default='',help='Explicit remaining scope shown in the report')
    args=p.parse_args()
    profiles=args.profiles or (['cpu'] if args.stage=='first' else ['cpu','auto','gpu'])
    description={'stage':args.stage,'newTestGroups':['A','B','C','shared'],'regressions':['f011','f012','f013','f014','math'],
                 'profiles':profiles,'installs':False,'publication':False,'keepGoing':True,
                 'legacyPixelDiagnosticsSkipped':args.skip_legacy_pixels,'scopeNote':args.scope_note}
    if args.dry_run:print(json.dumps(description,ensure_ascii=False,indent=2));return 0
    if args.stage=='report' and (not args.oracle or not args.native):p.error('report requires --oracle and --native')
    with Run('BULK-P3' if args.stage=='first' else 'BULK-P4' if args.stage=='final' else 'BULK-P5',args.stage) as run:
        write_json(run.path/'artifacts/stage.json',description)
        for f in args.fixtures:run.input(f)
        for f in sorted((ROOT/'references').glob('bulk-*-assertions.json')):run.input(f)
        candidate=source_identity();write_json(run.path/'artifacts/source-candidate.json',candidate)
        with zipfile.ZipFile(run.path/'artifacts/source-candidate.zip','x',zipfile.ZIP_DEFLATED) as archive:
            for relative in candidate['files']:archive.write(ROOT/relative,relative)
        with zipfile.ZipFile(run.path/'artifacts/test-tool-candidate.zip','x',zipfile.ZIP_DEFLATED) as archive:
            for base in ('tests','tools','scripts','docs','references'):
                for file in sorted((ROOT/base).rglob('*')):
                    if file.is_file() and '__pycache__' not in file.parts and file.suffix!='.pyc':
                        archive.write(file,file.relative_to(ROOT));run.input(file)
            for name in ('AGENTS.md','README.en.md'):
                archive.write(ROOT/name,name);run.input(ROOT/name)
        env={'PYTHONPATH':str(ROOT/'src'),'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'}
        def command(name,argv,timeout=1800):return run.command(name,argv,cwd=ROOT,env=env,timeout=timeout)
        frozen=run.path/'artifacts/fixtures'
        collected=command('fixture-freeze',[sys.executable,str(ROOT/'tools/collect_bulk_cases.py'),'--fixtures',*[str(f) for f in args.fixtures],'--out',str(frozen)],120)
        if collected['exitCode']:return collected['exitCode']
        fixture=frozen/'cases.json';native=[]
        control_cases=[c for c in json.loads(fixture.read_text('utf8'))['cases'] if 'controlExpected' in c]
        if any(c['group']!='shared' for c in control_cases):raise ValueError('Static HTML control fixtures must use the shared native group')
        control_fixture=frozen/'html-control-cases.json'
        if control_cases:
            write_json(control_fixture,{'schema':'py-mermaid-bulk-cases/v1','group':'combined','cases':control_cases})
            run.data['staticHtmlControlFixtureCount']=len(control_cases)
        if args.oracle:
            run.input(args.oracle/'manifest.json');run.input(args.oracle/'identity.json')
            original=json.loads((args.oracle/'manifest.json').read_text('utf-8'))
            if original.get('fixtureSha256')!=file_identity(frozen/'browser-cases.json')['sha256']:
                raise ValueError('Explicit reused oracle does not match frozen fixture/config/resources bytes')
            reference=run.path/'artifacts/reused-oracle-source-check'
            checked=command('verify-reused-oracle-source',['node',str(ROOT/'tools/oracle/bulk_capture.cjs'),'--verify-only','--out',str(reference)],180)
            if checked['exitCode'] or original.get('identity')!=json.loads((reference/'identity.json').read_text('utf-8')):
                raise ValueError('Explicit reused oracle does not match current fixed canonical source/plugins and transport identity')
        if args.stage!='report':
            if args.stage=='final':
                original_themes=run.path/'artifacts/original-themes.json'
                command('original-eleven-themes',['node',str(ROOT/'tools/oracle/bulk_themes.mjs'),'--fixtures',str(fixture),'--out',str(original_themes)],120)
                command('complete-theme-variable-parity',[sys.executable,str(ROOT/'tools/check_bulk_themes.py'),'--fixtures',str(fixture),'--oracle',str(original_themes),'--out',str(run.path/'artifacts/theme-parity.json')],120)
            # All grouped first runs execute even after failures. Do not edit
            # product source while this sweep is active.
            for group in ('a','b','c','shared'):
                command('unit-'+group,[sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests/bulk'/group),'-t',str(ROOT/'tests'),'-v'],2400)
            if control_cases:
                command('unit-html-host',[sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests/html_host'),'-v'],2400)
            for group in ('f011','f012','f013','f014','math'):
                command('regression-'+group,[sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'/group),'-v'],2400)
            if args.stage=='final':
                for group in ('bootstrap','tooling','pixel_compare'):
                    command('verification-tools-'+group,[sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'/group),'-v'],1200)
        oracle=args.oracle
        if oracle is None:
            oracle=run.path/'artifacts/oracle'
            command('official-source-capture',['node',str(ROOT/'tools/oracle/bulk_capture.cjs'),'--fixtures',str(frozen/'browser-cases.json'),'--out',str(oracle)],7200)
        if args.stage=='report':native=args.native
        else:
            for backend in profiles:
                for group in ('A','B','C','shared'):
                    directory=run.path/'artifacts'/('native-'+backend+'-'+group);native.append(directory)
                    command('native-'+backend+'-'+group,[sys.executable,str(ROOT/'tools/bulk_validate.py'),'--fixtures',str(fixture),'--group',group,'--backend',backend,'--out',str(directory)],3600)
            if control_cases:
                for backend in profiles:
                    command('html-control-state-'+backend,[sys.executable,str(ROOT/'tools/check_html_controls.py'),
                        '--fixtures',str(control_fixture),'--oracle',str(oracle),'--native',str(run.path/'artifacts'/('native-'+backend+'-shared')),
                        '--out',str(run.path/'artifacts'/('html-control-verification-'+backend))],1800)
        if args.stage=='final':
            for backend in profiles:
                command('zenuml-source-structure-'+backend,[sys.executable,str(ROOT/'tools/check_zenuml_parity.py'),'--fixtures',str(fixture),
                    '--oracle',str(oracle),'--native',str(run.path/'artifacts'/('native-'+backend+'-C')),
                    '--out',str(run.path/'artifacts'/('zenuml-parity-'+backend))],1800)
            command('all-kinds-five-formats',[sys.executable,str(ROOT/'tools/bulk_export.py'),'--fixtures',str(fixture),'--profiles',*profiles,'--out',str(run.path/'artifacts/exports')],7200)
            if control_cases:
                covered=set();kinds=set();selected=[]
                for case in control_cases:
                    keys={item['tag']+':'+item.get('type','text' if item['tag']=='input' else '') for item in case['controlExpected']}
                    if keys and (keys-covered or case['kind'] not in kinds):
                        selected.append(case['id']);covered.update(keys);kinds.add(case['kind'])
                write_json(run.path/'artifacts/html-control-export-selection.json',{'caseIds':selected,'controlTypeCoverage':sorted(covered),'kinds':sorted(kinds)})
                command('html-control-five-formats',[sys.executable,str(ROOT/'tools/bulk_export.py'),'--fixtures',str(control_fixture),
                    '--case-ids',*selected,'--profiles',*profiles,'--out',str(run.path/'artifacts/html-control-exports')],7200)
            # The 297 historical positive diagrams keep their specialized
            # source semantic/geometry comparators and original denominators.
            for group in ('f011','f012','f013','f014'):
                old_fixture=ROOT/'tests'/group/'cases.json';run.input(old_fixture)
                old_oracle=args.legacy_oracle_root/group if args.legacy_oracle_root else run.path/'artifacts'/('legacy-oracle-'+group)
                if args.legacy_oracle_root is None:
                    command('legacy-oracle-'+group,['node',str(ROOT/'tools/oracle/f011_capture.cjs'),'--fixtures',str(old_fixture),'--out',str(old_oracle)],3600)
                else:
                    run.input(old_oracle/'manifest.json');run.input(old_oracle/'identity.json')
                    old_manifest=json.loads((old_oracle/'manifest.json').read_text('utf-8'))
                    if old_manifest.get('fixtureSha256')!=file_identity(old_fixture)['sha256']:
                        raise ValueError('Reused legacy oracle fixture bytes differ or have no immutable fingerprint: '+group)
                    source_check=run.path/'artifacts'/('legacy-source-check-'+group)
                    verified=command('verify-legacy-source-'+group,['node',str(ROOT/'tools/oracle/f011_capture.cjs'),'--verify-only','--out',str(source_check)],180)
                    if verified['exitCode'] or old_manifest.get('identity')!=json.loads((source_check/'identity.json').read_text('utf-8')):
                        raise ValueError('Reused legacy oracle source identity differs: '+group)
                for backend in profiles:
                    command('legacy-'+group+'-'+backend,[sys.executable,str(ROOT/'tools/f011_validate.py'),'--fixtures',str(old_fixture),'--oracle',str(old_oracle),
                        '--out',str(run.path/'artifacts'/('legacy-'+group+'-'+backend)),'--backend',backend,
                        *(['--skip-pixel-diagnostics'] if args.skip_legacy_pixels else [])],7200)
        if (oracle/'manifest.json').is_file():
            comparison_dirs=[]
            for directory in native:
                if not (directory/'results.json').is_file():continue
                comparison=run.path/'artifacts'/('comparison-'+directory.name);comparison_dirs.append(comparison)
                command('compare-'+directory.name,[sys.executable,str(ROOT/'tools/bulk_compare.py'),'--fixtures',str(fixture),'--oracle',str(oracle),'--native',str(directory),'--out',str(comparison),'--pixels'],3600)
            complete=[d for d in native if (d/'results.json').is_file()]
            if complete:
                command('raw-html-report',[sys.executable,str(ROOT/'tools/build_bulk_report.py'),'--fixtures',str(fixture),'--oracle',str(oracle),'--native',*[str(d) for d in complete],
                    '--comparison',*[str(d) for d in comparison_dirs if (d/'comparison.json').is_file()],'--required-profiles',*profiles,
                    '--scope-note',args.scope_note,'--out',str(run.path/'report/bulk')],600)
        run.data['functionalStatus']='GROUPED_RESULTS_REVIEW_REQUIRED'
    print(json.dumps({'runId':run.id,'status':run.data['status'],'sourceUnchanged':run.data['sourceUnchanged'],'run':str(run.path)},ensure_ascii=False))
    return int(run.data['status']!='SUCCESS')


if __name__=='__main__':raise SystemExit(main())
