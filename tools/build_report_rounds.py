"""Paginate a closed raw A/B report by explicit iteration membership.

No rendering or new acceptance: retain case statuses and embedded image bytes.
The source report and historical reports are never rewritten.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re

from run_support import ROOT, file_identity, write_json

CSS = """*{box-sizing:border-box}body{margin:0;background:#f1f4f8;color:#1b2838;font:15px/1.6 system-ui,sans-serif}
header,main,footer{max-width:1440px;margin:auto;padding:20px 28px}header{background:#fff;border-bottom:1px solid #dbe2ec}
h1{font-size:25px;margin:10px 0}h2{font-size:18px;margin:0 0 10px;overflow-wrap:anywhere}h3{font-size:14px}
a{color:#1758a8;text-decoration:none}a:hover{text-decoration:underline}.muted,small{color:#596a80}
.rounds,.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr));gap:16px}
.panel,.case{background:#fff;border:1px solid #dbe2ec;border-radius:12px;padding:20px;margin:0 0 20px}
.rounds .panel{display:flex;flex-direction:column;align-items:flex-start}.panel p{margin:8px 0 18px}.primary{background:#1758a8;color:#fff;padding:9px 16px;border-radius:7px;margin-top:auto;display:inline-block}
nav,.toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap}nav{margin:12px 0}input,select{font:inherit;padding:7px 10px;border:1px solid #bdc9d9;border-radius:6px;max-width:100%}input{width:310px}
.badge{font-size:12px;border-radius:4px;padding:3px 7px;background:#fff0cb}.ok{background:#def0e4}
.image{border:1px solid #e1e6ee;border-radius:8px;padding:12px;overflow:auto}.image img{max-width:100%;height:auto;display:block;margin:auto}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:12px;max-height:360px;overflow:auto}code{overflow-wrap:anywhere}summary{cursor:pointer;color:#596a80;margin:8px 0}
.hidden{display:none!important}.absent{padding:20px;background:#fff1f1}.lookup-results{list-style:none;padding:0}.lookup-results a{display:block;padding:8px;border-bottom:1px solid #edf0f5}
.note{border-left:3px solid #8ca9cc;padding-left:12px}.page-label{font-weight:600}.case{scroll-margin-top:12px}
@media(max-width:600px){header,main,footer{padding:16px}.case,.panel{padding:14px}h1{font-size:21px}}
"""


def escape(value):
    return html.escape(str(value), quote=True)


def json_script(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")


def document(title, body, *, navigation="", note="", script=""):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><style>{CSS}</style></head><body>'
            f'<header>{navigation}<h1>{escape(title)}</h1>'
            + (f'<p class="note">{escape(note)}</p>' if note else '')
            + f'</header><main>{body}</main><footer class="muted">原始 A/B 图片 · 按轮次分页 · 不重新渲染或修改验收结果</footer>'
            + (f'<script>{script}</script>' if script else '') + '</body></html>')


def lookup(entries):
    return ('<section class="panel"><label>定位案例 <input id="lookup" placeholder="输入案例名称或图种"></label>'
            '<div id="lookup-hint" class="muted">输入后显示匹配入口，每次最多 10 项。</div>'
            '<ul id="lookup-results" class="lookup-results"></ul></section>'), """
const entries=ENTRIES, input=document.querySelector('#lookup'), list=document.querySelector('#lookup-results');
input.addEventListener('input',()=>{const q=input.value.trim().toLowerCase();list.replaceChildren();
 const found=q?entries.filter(e=>(e.id+' '+e.kind).toLowerCase().includes(q)):[];
 document.querySelector('#lookup-hint').textContent=q?found.length+' 个匹配，显示前 10 个':'输入后显示匹配入口，每次最多 10 项。';
 for(const e of found.slice(0,10)){const li=document.createElement('li'),a=document.createElement('a');a.href=e.href;a.textContent=e.id+' · '+e.kind;li.append(a);list.append(li);}});
""".replace('ENTRIES', json_script(entries))


def page_nav(pages, current):
    options=''.join(f'<option value="{escape(p)}"'+(' selected' if i==current else '')+f'>第 {i+1} / {len(pages)} 页</option>' for i,p in enumerate(pages))
    previous=f'<a rel="prev" href="{pages[current-1]}">上一页</a>' if current else '<span class="muted">上一页</span>'
    following=f'<a rel="next" href="{pages[current+1]}">下一页</a>' if current+1<len(pages) else '<span class="muted">下一页</span>'
    return f'<nav>{previous}<label>跳页 <select class="page-select">{options}</select></label>{following}</nav>'


def checked_path(item, base):
    path=(base/item['path']).resolve(strict=True)
    if file_identity(path)['sha256']!=item['sha256']:
        raise ValueError('Source fingerprint differs: '+str(path))
    return path


def embedded_counts(text):
    counts=Counter()
    for mime,encoded in re.findall(r'(?:src|href)="data:image/(png|svg\+xml);base64,([^"]+)"',text):
        raw=base64.b64decode(encoded,validate=True)
        counts[(mime,hashlib.sha256(raw).hexdigest(),len(raw))]+=1
    return counts


def build(spec, out, *, base=ROOT, page_size=12):
    if type(page_size) is not int or not 1<=page_size<=24:
        raise ValueError('Page size must be between 1 and 24')
    if spec.get('schema')!='py-mermaid-report-rounds-spec/v1':
        raise ValueError('Unexpected round spec schema')
    source=spec['sourceReport']
    source_html=checked_path(source['html'],base)
    metadata_path=checked_path(source['metadata'],base)
    metadata=json.loads(metadata_path.read_text('utf8'))
    if file_identity(source_html)!=metadata['report']:
        raise ValueError('Source report HTML and metadata differ')
    body=source_html.read_text('utf8')
    cards={}
    for match in re.finditer(r'<article class="case"\s.*?</article>',body,re.S):
        raw=match.group()
        identifier=re.search(r'\bdata-search="([^" ]+)',raw)
        if not identifier:raise ValueError('Case article has no identity')
        # data-search is lowercased by the source generator; recover case-sensitive ID from h2.
        heading=re.search(r'<h2>([^< ]+) ',raw)
        if not heading:raise ValueError('Case article has no heading')
        identifier=html.unescape(heading[1])
        if identifier in cards:raise ValueError('Duplicate case article: '+identifier)
        cards[identifier]=raw
    rows={row['id']:row for row in metadata['cases']}
    if len(rows)!=len(metadata['cases']) or set(rows)!=set(cards):
        raise ValueError('Case articles and source metadata denominator differ')
    for identifier,raw in cards.items():
        state=re.search(r'\bdata-status="([^"]+)"',raw)
        if not state or state[1]!=rows[identifier]['status']:
            raise ValueError('Case HTML status differs from source metadata: '+identifier)
    expected=Counter()
    for path,identity in metadata['rawEmbeddedArtifacts'].items():
        mime='png' if path.endswith('.png') else 'svg+xml' if path.endswith('.svg') else None
        if mime:expected[(mime,identity['sha256'],identity['bytes'])]+=1
    actual=embedded_counts(body)
    if actual!=expected:raise ValueError('Embedded source image bytes/count differ')
    assigned=set();rounds=[];round_ids=set()
    for group in spec['rounds']:
        identifier=group['id']
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',identifier) or identifier in round_ids:
            raise ValueError('Invalid/duplicate round ID')
        round_ids.add(identifier)
        ids=list(group.get('caseIds',[]))
        for name in group.get('caseFiles',[]):
            ids.extend(row['id'] for row in json.loads((base/name).read_text('utf8'))['cases'])
        if not ids or len(set(ids))!=len(ids) or assigned&set(ids) or not set(ids)<=rows.keys():
            raise ValueError('Duplicate/unknown/empty round case membership: '+identifier)
        assigned.update(ids);rounds.append({**group,'caseIds':ids})
    if assigned!=set(rows):raise ValueError('Round membership omits source cases')
    if not rounds:raise ValueError('No rounds')
    # Validate explicit historic links before writing anything. No latest-directory guessing.
    history=[]
    for entry in spec.get('history',[]):
        checked_path(entry['html'],base)
        history.append(entry)
    out.mkdir(parents=True,exist_ok=False)
    note=spec.get('scopeNote','')
    report={'schema':'py-mermaid-report-rounds/v1','sourceTreeSha256':metadata['sourceTreeSha256'],
            'functionalStatus':'NOT_EVALUATED','sourceReportFunctionalStatus':metadata['functionalStatus'],
            'sourceReport':source,'counts':metadata['counts'],'caseCount':len(rows),
            'pageSize':page_size,'scopeNote':note,'rounds':[],'pages':[],
            'history':history,'resampling':False,'installationVerification':False}
    all_entries=[];index_cards=[];all_embedded=Counter()
    for group in rounds:
        folder=out/'rounds'/group['id'];folder.mkdir(parents=True)
        ids=group['caseIds'];chunks=[ids[i:i+page_size] for i in range(0,len(ids),page_size)]
        filenames=[f'page-{i+1:03}.html' for i in range(len(chunks))]
        entries=[]
        counts=Counter(rows[i]['status'] for i in ids)
        report['rounds'].append({'id':group['id'],'title':group['title'],'caseCount':len(ids),'counts':dict(counts),'pageCount':len(chunks),'href':f"rounds/{group['id']}/index.html"})
        for page_number,chunk in enumerate(chunks):
            for identifier in chunk:
                entry={'id':identifier,'kind':rows[identifier]['kind'],'href':filenames[page_number]+'#case-'+identifier}
                entries.append(entry);all_entries.append({**entry,'href':f"rounds/{group['id']}/"+entry['href']})
            nav=page_nav(filenames,page_number)
            profiles=sorted({b for identifier in chunk for b in rows[identifier]['native']})
            default='auto' if 'auto' in profiles else profiles[0] if profiles else ''
            options=''.join(f'<option'+(' selected' if p==default else '')+f'>{escape(p)}</option>' for p in profiles)
            controls=f'<div class="toolbar"><label>搜索当前页 <input id="search" placeholder="案例名称或图种"></label><label>Python 后端 <select id="backend">{options}</select></label><span id="count"></span></div>'
            articles=[]
            for identifier in chunk:
                raw=cards[identifier].replace('<article ',f'<article id="case-{escape(identifier)}" ',1)
                for profile in profiles:
                    raw=raw.replace(f'<section class="image"><h3>B · Python {escape(profile)}</h3>',f'<section class="image" data-profile="{escape(profile)}"><h3>B · Python {escape(profile)}</h3>')
                articles.append(raw)
            script="""
document.querySelectorAll('.page-select').forEach(s=>s.addEventListener('change',()=>location.href=s.value));
const cards=[...document.querySelectorAll('.case')];function filter(){const q=document.querySelector('#search').value.toLowerCase();let n=0;for(const c of cards){const show=!q||c.dataset.search.includes(q);c.classList.toggle('hidden',!show);n+=show}document.querySelector('#count').textContent=n+' / '+cards.length}
document.querySelector('#search').addEventListener('input',filter);filter();
function backend(){for(const e of document.querySelectorAll('[data-profile]'))e.classList.toggle('hidden',e.dataset.profile!==document.querySelector('#backend').value)}document.querySelector('#backend').addEventListener('change',backend);backend();
"""
            content=document(group['title']+f' · 第 {page_number+1}/{len(chunks)} 页',
                nav+controls+''.join(articles)+nav,
                navigation='<nav><a href="../../index.html">全部轮次</a><a href="index.html">本轮概览</a></nav>',note=note,script=script)
            target=folder/filenames[page_number];target.write_text(content,encoding='utf8')
            observed=embedded_counts(content);all_embedded.update(observed)
            report['pages'].append({'path':target.relative_to(out).as_posix(),'roundId':group['id'],
                'caseIds':chunk,'caseStatuses':{i:rows[i]['status'] for i in chunk},'report':file_identity(target),
                'rawPNG':sum(n for (mime,_,_),n in observed.items() if mime=='png'),
                'rawSVG':sum(n for (mime,_,_),n in observed.items() if mime=='svg+xml')})
        search,script=lookup(entries)
        overview=f'<section class="panel"><p>{escape(group.get("description",""))}</p><p>{len(ids)} 个案例 · {len(chunks)} 页 · 每页最多 {page_size} 例</p><a class="primary" href="{filenames[0]}">打开本轮对比</a>{page_nav(filenames,0)}</section>'+search
        target=folder/'index.html';target.write_text(document(group['title'],overview,navigation='<a href="../../index.html">← 全部轮次</a>',note=note,script=script+"document.querySelectorAll('.page-select').forEach(s=>s.onchange=()=>location.href=s.value);"),encoding='utf8')
        report['rounds'][-1]['report']=file_identity(target)
        index_cards.append(f'<section class="panel"><h2>{escape(group["title"])}</h2><p>{escape(group.get("description",""))}</p><p class="muted">{len(ids)} 个案例 · {len(chunks)} 页</p><a class="primary" href="rounds/{group["id"]}/index.html">查看这一轮</a></section>')
    if all_embedded!=expected:raise ValueError('Paginated image denominator/bytes differ')
    search,script=lookup(all_entries)
    historic=''.join(f'<p><a href="{escape(e["href"])}">{escape(e["title"])}</a> <small>{escape(e.get("description","历史独立报告"))}</small></p>' for e in history)
    summary=f'<p class="muted">{len(rows)} 个案例按 {len(rounds)} 轮分开查看；每页最多 {page_size} 例。默认只展示所选 Python 后端。</p>'
    content=summary+'<div class="rounds">'+''.join(index_cards)+'</div>'+search
    if historic:content+='<section class="panel"><h2>更早轮次</h2>'+historic+'</section>'
    content+='<details><summary>证据说明</summary><p>此页仅重新组织已保存报告，不重新运行渲染或验收。案例状态、图片及历史候选保持不变。</p><p>来源候选 <code>'+escape(metadata['sourceTreeSha256'])+'</code></p><p><a href="report.json">分页索引与原报告指纹</a></p></details>'
    target=out/'index.html';target.write_text(document(spec.get('title','Mermaid 迭代对比报告'),content,note=note,script=script),encoding='utf8')
    report['report']=file_identity(target)
    report['rawPNGVerified']=sum(n for (mime,_,_),n in all_embedded.items() if mime=='png')
    report['rawSVGVerified']=sum(n for (mime,_,_),n in all_embedded.items() if mime=='svg+xml')
    write_json(out/'report.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--page-size',default=12,type=int)
    args=parser.parse_args()
    result=build(json.loads(args.spec.read_text('utf8')),args.out,page_size=args.page_size)
    print(json.dumps({'report':str((args.out/'index.html').resolve()),'rounds':len(result['rounds']),'pages':len(result['pages']),'cases':result['caseCount'],'rawPNG':result['rawPNGVerified'],'rawSVG':result['rawSVGVerified']},ensure_ascii=False))


if __name__=='__main__':
    main()
