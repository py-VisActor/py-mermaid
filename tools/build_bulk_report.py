"""Read-only evidence to a self-contained raw A/B static HTML report.

No renderer invocation, resampling, cropping, alignment or acceptance by pixels.
Every raw image is embedded byte-for-byte; links retain JSON/SVG/unit evidence.
"""
from __future__ import annotations
import argparse
import base64
from collections import Counter
import html
import json
from pathlib import Path
import sys
from bulk_support import load_cases,write
from run_support import ROOT,file_identity,verify_run


def main():
    p=argparse.ArgumentParser();p.add_argument('--fixtures',nargs='+',required=True,type=Path)
    p.add_argument('--oracle',required=True,type=Path);p.add_argument('--native',nargs='+',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);p.add_argument('--unit-runs',nargs='*',default=[],type=Path)
    p.add_argument('--comparison',nargs='*',default=[],type=Path)
    p.add_argument('--required-profiles',nargs='*',default=None)
    p.add_argument('--acceptance',type=Path,help='Explicit same-candidate local acceptance and hashed visual-review evidence')
    p.add_argument('--scope-note',default='',help='Known remaining scope, displayed visibly and saved in report metadata')
    p.add_argument('--allow-subset',action='store_true',help='Targeted verification report only; cannot carry whole-batch acceptance')
    args=p.parse_args()
    if args.allow_subset and args.acceptance:p.error('Subset reports cannot carry whole-batch acceptance')
    args.out.mkdir(parents=True,exist_ok=False)
    cases=load_cases(args.fixtures,require_all=not args.allow_subset)
    oracle=json.loads((args.oracle/'manifest.json').read_text('utf-8'))
    native=[(d,json.loads((d/'results.json').read_text('utf-8'))) for d in args.native]
    comparisons=[(d,json.loads((d/'comparison.json').read_text('utf-8'))) for d in args.comparison]
    identities={m['source']['sourceTreeSha256'] for d,m in native}
    if len(identities)!=1 or not all(m['sourceUnchanged'] for d,m in native):raise ValueError('Native evidence candidate mismatch/drift')
    rows=[];evidence={};source=next(iter(identities))
    def link(path):return path.resolve().as_uri()
    def img(path,label):
        if not path.is_file():return '<div class="absent">未生成图片</div>'
        raw=path.read_bytes();evidence[str(path.resolve())]=file_identity(path)
        return '<img loading="lazy" alt="'+html.escape(label)+'" src="data:image/png;base64,'+base64.b64encode(raw).decode()+'">'
    def details(data):return '<details><summary>检查记录</summary><pre>'+html.escape(json.dumps(data,ensure_ascii=False,indent=2))+'</pre></details>'
    def original_svg(id):
        path=args.oracle/(id+'.svg')
        if not path.is_file():return ''
        evidence[str(path.resolve())]=file_identity(path)
        return '<a download="'+html.escape(id,quote=True)+'.svg" href="data:image/svg+xml;base64,'+base64.b64encode(path.read_bytes()).decode()+'">下载原始 SVG</a>'
    oracle_by={r['id']:r for r in oracle['cases']}
    for case in cases:
        id=case['id'];a=oracle_by.get(id,{'status':'missing'})
        variants=[]
        for directory,manifest in native:
            found=next((r for r in manifest['cases'] if r['id']==id),None)
            if found:variants.append((directory,manifest['backend'],found))
        errors=[r for _,_,r in variants if r['status'] in ('FAILED','ERROR')]
        required=set(args.required_profiles or [m['backend'] for _,m in native])
        if required!={b for _,b,_ in variants}:errors.append({'missingProfiles':sorted(required-{b for _,b,_ in variants})})
        checks=[{**r,'backend':m.get('backend')} for _,m in comparisons for r in m['cases'] if r['id']==id]
        if any(c['status']=='REVIEW' for c in checks):errors.append({'sourceComparison':'REVIEW'})
        expected_error=case['expect'] in ('syntax_error','error')
        oracle_issue=(case['expect']=='render' and a['status']!='captured') or (expected_error and a['status']=='captured')
        if case['expect']=='excluded_by_static_scope':state='EXCLUDED'
        elif case['expect']=='upstream_defect':
            if case.get('officialExpect')=='content_loss':
                from source_defect_checks import content_loss_errors
                confirmed=not content_loss_errors(case,args.oracle)
            elif case.get('officialExpect')=='degenerate_render':
                svg=args.oracle/(id+'.svg');contract=case.get('sourceGeometry',{})
                import re
                attrs=contract.get('nonfiniteAttributes',[]);body=svg.read_text('utf-8') if svg.is_file() else ''
                count=len(re.findall(r'\b(?:'+('|'.join(re.escape(x) for x in attrs) or '(?!)')+r')\s*=\s*"(?:NaN|[+-]?Infinity)"',body))
                confirmed=count>=contract.get('minimumMatches',1)
            else:
                error=args.oracle/(id+'.error.json')
                confirmed=error.is_file() and bool(json.loads(error.read_text('utf-8')).get('sourceError'))
            state='UPSTREAM_CONFIRMED' if confirmed and variants and not errors and (not case.get('nativeMustRender') or all(r['status']=='CHECKS_PASSED' for _,_,r in variants)) else 'REVIEW_FAILURE'
        elif not variants or errors or oracle_issue:state='REVIEW_FAILURE'
        else:state='CHECKS_PASSED_REVIEW_REQUIRED'
        row={'id':id,'kind':case['kind'],'group':case['group'],'status':state,'oracle':a,
             'native':{b:r for _,b,r in variants},'origin':case['origin'],'sourceComparisons':checks}
        rows.append(row)
    counters=Counter(r['status'] for r in rows)
    unit=[]
    for d in args.unit_runs:
        manifest=json.loads((d/'run.json').read_text('utf-8'))
        if manifest['source']['sourceTreeSha256']!=source or not manifest['sourceUnchanged']:raise ValueError('Unit evidence not same candidate')
        unit.append({'runId':manifest['runId'],'status':manifest['status'],'commands':manifest['commands'],
                     'manifest':str((d/'run.json').resolve()),'sha256':file_identity(d/'run.json')['sha256']})
    acceptance=None
    if args.acceptance:
        acceptance=json.loads(args.acceptance.read_text('utf-8'))
        if acceptance.get('functionalStatus')!='RETAINED_STATIC_LOCAL_ACCEPTED' or acceptance.get('sourceTreeSha256')!=source:
            raise ValueError('Acceptance status/candidate differs')
        if acceptance.get('fixtureCount')!=len(cases) or {m['backend'] for _,m in native}!={'cpu','auto','gpu'}:
            raise ValueError('Acceptance requires the complete fixture and three-profile report')
        if counters.get('REVIEW_FAILURE',0):raise ValueError('Acceptance cannot override failed automatic checks')
        def evidence_file(item):
            path=(ROOT/item['path']).resolve(strict=True)
            if file_identity(path)['sha256']!=item['sha256']:raise ValueError('Acceptance evidence fingerprint differs: '+str(path))
            return path
        p4=evidence_file(acceptance['p4Manifest']);proof=json.loads(p4.read_text('utf-8'))
        if (proof['scope']!='BULK-P4' or proof['kind']!='final' or proof['status']!='SUCCESS' or not proof['sourceUnchanged']
            or proof['source']['sourceTreeSha256']!=source or any(c['exitCode']!=0 for c in proof['commands'])):
            raise ValueError('Acceptance requires a successful closed whole P4 candidate')
        required={'unit-'+g for g in ('a','b','c','shared')}
        required|={'native-'+b+'-'+g for b in ('cpu','auto','gpu') for g in ('A','B','C','shared')}
        required|={'zenuml-source-structure-'+b for b in ('cpu','auto','gpu')}
        required|={'legacy-'+g+'-'+b for g in ('f011','f012','f013','f014') for b in ('cpu','auto','gpu')}
        required|={'compare-native-'+b+'-'+g for b in ('cpu','auto','gpu') for g in ('A','B','C','shared')}
        required|={'regression-'+g for g in ('f011','f012','f013','f014','math')}
        required|={'verification-tools-'+g for g in ('bootstrap','tooling','pixel_compare')}
        required|={'all-kinds-five-formats','complete-theme-variable-parity'}
        control_ids={c['id'] for c in cases if 'controlExpected' in c}
        if control_ids:
            required|={'unit-html-host','html-control-five-formats',*('html-control-state-'+b for b in ('cpu','auto','gpu'))}
            controls=acceptance.get('htmlControlVerification',[])
            if len(controls)!=3:raise ValueError('HTML control verification incomplete')
            profiles=set()
            for item in controls:
                checked=json.loads(evidence_file(item).read_text('utf8'))
                if (checked.get('status')!='PASS' or not checked.get('sourceUnchanged') or checked.get('source',{}).get('sourceTreeSha256')!=source
                    or {c['id'] for c in checked.get('cases',[])}!=control_ids or any(c.get('status')!='PASS' for c in checked.get('cases',[]))):
                    raise ValueError('HTML control verification incomplete or candidate differs')
                profiles.add(checked.get('backend'))
            if profiles!={'cpu','auto','gpu'}:raise ValueError('HTML control verification incomplete')
            export_item=acceptance.get('htmlControlExports')
            if not export_item:raise ValueError('HTML control exports incomplete')
            exported=json.loads(evidence_file(export_item).read_text('utf8'))
            requested=exported.get('requestedCaseIds') or []
            records=exported.get('cases',[])
            expected_keys={item['tag']+':'+item.get('type','text' if item['tag']=='input' else '') for c in cases for item in c.get('controlExpected',[])}
            selected_keys={item['tag']+':'+item.get('type','text' if item['tag']=='input' else '') for c in cases if c['id'] in requested for item in c.get('controlExpected',[])}
            if (exported.get('source',{}).get('sourceTreeSha256')!=source or not exported.get('sourceUnchanged') or not requested
                or not set(requested)<=control_ids or selected_keys!=expected_keys
                or {(r.get('fixture'),r.get('backend'),r.get('format')) for r in records}!={(c,b,f) for c in requested for b in ('cpu','auto','gpu') for f in ('png','jpg','webp','svg','pdf')}
                or any(r.get('status')!='CHECKS_PASSED' for r in records)):
                raise ValueError('HTML control exports incomplete or candidate differs')
            export_manifest=evidence_file(export_item)
            if len(requested)!=len(set(requested)) or len(records)!=len(requested)*15 or len({r['artifact'] for r in records})!=len(records):
                raise ValueError('HTML control exports incomplete: duplicate selections or saved artifacts')
            for row in records:
                artifact=(export_manifest.parent/row['artifact']).resolve(strict=True)
                if not artifact.is_relative_to(export_manifest.parent) or file_identity(artifact)!={'sha256':row.get('sha256'),'bytes':row['bytes']}:
                    raise ValueError('HTML control exports incomplete: saved artifact differs')
            if not export_manifest.is_relative_to(p4.parent):
                repair_item=acceptance.get('exportRepair')
                if not repair_item:raise ValueError('HTML export repair proof incomplete')
                repair_manifest=evidence_file(repair_item['manifest']);repair=json.loads(repair_manifest.read_text('utf8'))
                if (repair.get('scope')!='HTML-HOST-P4-EXPORT' or repair.get('kind')!='repair' or repair.get('status')!='SUCCESS'
                    or not repair.get('sourceUnchanged') or not repair.get('finishedAtUtc') or repair.get('source',{}).get('sourceTreeSha256')!=source
                    or len(repair.get('commands',[]))!=2 or {c['name'] for c in repair['commands']}!={'all-kinds-five-formats','html-control-five-formats'}
                    or any(c.get('exitCode')!=0 for c in repair['commands']) or verify_run(repair_manifest.parent)['integrityStatus']!='PASS'
                    or export_manifest!=(repair_manifest.parent/'artifacts/html-control-exports/exports.json').resolve()
                    or evidence_file(acceptance['exports']['proof'])!=(repair_manifest.parent/'artifacts/exports/exports.json').resolve()):
                    raise ValueError('HTML export repair proof incomplete or candidate differs')
        if not required<={c['name'] for c in proof['commands']} or not any(u['runId']==proof['runId'] and u['status']=='SUCCESS' for u in unit):
            raise ValueError('Acceptance is missing whole-candidate matrix/unit evidence')
        visual=json.loads(evidence_file(acceptance['visualReview']).read_text('utf-8'))
        if visual.get('sourceTreeSha256')!=source or visual.get('status')!='PASS':raise ValueError('Visual review candidate/status differs')
        if {c['kind'] for c in visual['cases']}!={c['kind'] for c in cases}:raise ValueError('Visual review does not cover all retained kinds')
        case_by={c['id']:c for c in cases}
        for reviewed in visual['cases']:
            id=reviewed['id']
            if id not in case_by or reviewed['kind']!=case_by[id]['kind']:raise ValueError('Unknown visual review case')
            if evidence_file(reviewed['original'])!=(args.oracle/(id+'.png')).resolve():raise ValueError('Visual review original image differs')
            if evidence_file(reviewed['native']) not in {(directory/(id+'.png')).resolve() for directory,_ in native}:
                raise ValueError('Visual review native image differs')
        for row in rows:
            if row['status']=='CHECKS_PASSED_REVIEW_REQUIRED':row['status']='CHECKS_PASSED'
        counters=Counter(r['status'] for r in rows)
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
    '<title>静态 Mermaid 批次 A/B 对比</title><style>body{font:15px system-ui;margin:0;color:#17212b;background:#eef1f5}header{padding:22px;background:#fff;position:sticky;top:0;z-index:2;border-bottom:1px solid #ccd3dc}h1{font-size:22px;margin:0 0 8px}code{overflow-wrap:anywhere}input,select{padding:8px;margin:8px 8px 0 0}main{padding:18px}.case{background:white;border-radius:10px;padding:18px;margin-bottom:20px;border:1px solid #ccd3dc}.case h2{font-size:17px;overflow-wrap:anywhere}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:12px}.image{border:1px solid #ddd;padding:10px;overflow:auto}.image img{max-width:100%;height:auto;background:#fff}.image h3{font-size:14px}.badge{font-size:12px;background:#f2dca7;padding:4px 8px;border-radius:4px}.ok{background:#d9eddc}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;padding:12px;max-height:480px;overflow:auto}summary{cursor:pointer;margin:10px 0}.absent{padding:30px;background:#f7eeee}a{color:#1765b0}small{color:#536171}.hidden{display:none}</style>',
    '<header><h1>静态 Mermaid 批次：原始 A/B 图片</h1>',
    ('<div>本轮定向分支核实：'+str(len(cases))+' 个输入；不是全部保留图种验收。</div>' if args.allow_subset else '<div>31 个保留入口；29 新增 + 2 流程图回归。统计图表、矩形树图、桑基图、韦恩图（7 入口）暂缓。</div>'),
    ('<p class="badge">'+html.escape(args.scope_note)+'</p>') if args.scope_note else '',
    '<div>候选 <code>'+source+'</code></div>',
    '<div>像素差仅诊断；图片保持原始字节。'+('本候选已结合来源单测和全部31类型的代表/复杂样例画面复核，完成保留静态范围本地验收。' if acceptance else '检查通过仍须结合来源单测和画面复核。')+'安装验证未执行。</div>',
    '<label>搜索 <input id="search" placeholder="图种、case、功能"></label><select id="status"><option value="">所有状态</option>'+''.join('<option>'+html.escape(s)+'</option>' for s in sorted(counters))+'</select>',
    '<span id="count"></span></header><main>',details({'caseCounts':dict(counters),'acceptance':acceptance,'unitEvidence':unit,'oracleIdentity':oracle['identity']})]
    for case,row in zip(cases,rows):
        id=case['id'];ok=row['status'] in ('CHECKS_PASSED_REVIEW_REQUIRED','CHECKS_PASSED')
        parts.append('<article class="case" data-status="'+row['status']+'" data-search="'+html.escape((id+' '+case['kind']+' '+' '.join(case.get('features',[]))).lower(),quote=True)+'"><h2>'+html.escape(id)+' <small>'+html.escape(case['kind'])+'</small> <span class="badge '+('ok' if ok else '')+'">'+row['status']+'</span></h2>')
        parts.append('<details><summary>原始输入与来源</summary><pre>'+html.escape(case['source'])+'</pre>'+details(case)+'</details><div class="grid">')
        parts.append('<section class="image"><h3>A · 官方固定源 / 浏览器</h3>'+img(args.oracle/(id+'.png'),id+' official')+original_svg(id)+details(row['oracle'])+'</section>')
        for directory,manifest in native:
            backend=manifest['backend']
            if not any(r['id']==id for r in manifest['cases']):continue
            parts.append('<section class="image"><h3>B · Python '+html.escape(backend)+'</h3>'+img(directory/(id+'.png'),id+' '+backend)+details({'native':row['native'][backend],
                'sourceComparisons':[c for c in row['sourceComparisons'] if c.get('backend') in (None,backend)]})+'</section>')
        parts.append('</div></article>')
    parts.append('</main><script>const cards=[...document.querySelectorAll(".case")];function filter(){const q=document.querySelector("#search").value.toLowerCase(),s=document.querySelector("#status").value;let n=0;for(const c of cards){const show=(!q||c.dataset.search.includes(q))&&(!s||c.dataset.status===s);c.classList.toggle("hidden",!show);n+=show}document.querySelector("#count").textContent=n+" / "+cards.length}document.querySelector("#search").oninput=filter;document.querySelector("#status").onchange=filter;filter();</script></html>')
    (args.out/'index.html').write_text(''.join(parts),encoding='utf-8')
    write(args.out/'report.json',{'schema':'py-mermaid-bulk-report/v1','sourceTreeSha256':source,'counts':dict(counters),'cases':rows,
        'unitEvidence':unit,'rawEmbeddedArtifacts':evidence,'report':file_identity(args.out/'index.html'),
        'functionalStatus':'RETAINED_STATIC_LOCAL_ACCEPTED' if acceptance else 'SOURCE_TESTS_AND_VISUAL_REVIEW_REQUIRED',
        'acceptance':acceptance,'scopeNote':args.scope_note,'subsetVerification':args.allow_subset,'resampling':False,'installationVerification':False})
    print(json.dumps({'report':str((args.out/'index.html').resolve()),'counts':dict(counters)},ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
