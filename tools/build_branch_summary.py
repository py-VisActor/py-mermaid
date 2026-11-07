"""Build short, paged branch conclusions from an explicit verification summary.

This is presentation only: classifications are copied, never promoted to PASS.
Raw original/native images remain in the separately verified comparison pages.
"""
import argparse
from collections import Counter
import html
import json
import math
from pathlib import Path

from run_support import file_identity, write_json


STYLE = '''body{font:15px system-ui;color:#17212b;background:#eef2f7;margin:0;overflow-wrap:anywhere}*{box-sizing:border-box}header,main{padding:24px;max-width:1300px;margin:auto}header{background:white}h1{font-size:24px}a{color:#1765b0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:12px}article,.panel{background:white;border:1px solid #d3dce7;border-radius:10px;padding:20px;margin:16px 0;overflow-wrap:anywhere}.groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:16px}.badge{font-size:13px;background:#e6edf7;padding:5px 8px;border-radius:5px}nav{display:flex;gap:20px;flex-wrap:wrap;margin:18px 0}small{color:#526276}summary{cursor:pointer}code{overflow-wrap:anywhere}'''


def esc(value):
    return html.escape(str(value), quote=True)


def detail(label, value):
    return '<details><summary>' + esc(label) + '</summary><pre>' + esc(json.dumps(value, ensure_ascii=False, indent=2)) + '</pre></details>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--comparison-url', required=True)
    parser.add_argument('--page-size', type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.page_size <= 12:
        raise ValueError('Summary pages must contain at most twelve branch records')
    data = json.loads(args.summary.read_text('utf-8'))
    rows = data['branchRecords']
    if not rows or len({row['id'] for row in rows}) != len(rows):
        raise ValueError('Missing/duplicate branch records')
    args.out.mkdir(parents=True, exist_ok=False)
    groups = sorted({row['group'] for row in rows})
    counts = dict(Counter(row['conclusion']['classification'] for row in rows))
    def shell(title, body):
        return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(title) + '</title><style>' + STYLE + '</style><header><h1>' + esc(title) + '</h1><p>第四轮 · 保留功能分支核实。生产源码只读；原版和原生的实际差异保留，未核实不计通过。</p><small>候选 ' + esc(data['sourceTreeSha256']) + '</small><nav><a href="index.html">核实总览</a><a href="' + esc(args.comparison_url) + '">原始 A/B 分页对比</a></nav></header><main>' + body + '</main></html>'
    pages = []
    for group in groups:
        selected = [row for row in rows if row['group'] == group]
        count = math.ceil(len(selected) / args.page_size)
        for i in range(count):
            subset = selected[i * args.page_size:(i + 1) * args.page_size]
            nav = '<nav>' + ''.join('<a href="group-' + esc(group) + '-page-' + f'{n+1:03d}' + '.html">' + str(n+1) + '</a>' for n in range(count)) + '</nav>'
            body = nav
            for row in subset:
                result = row['conclusion']
                body += '<article id="' + esc(row['id']) + '" data-classification="' + esc(result['classification']) + '"><h2>' + esc(row['id']) + ' · ' + esc(row['title']) + '</h2><span class="badge">' + esc(result['classification']) + '</span><p>' + esc(result['reason']) + '</p>'
                for identifier, url in row.get('caseLinks', {}).items():
                    body += '<p><a href="' + esc(url) + '">' + esc(identifier) + ' · 原始 A/B</a></p>'
                body += detail('条件与来源', {k: row.get(k) for k in ('predicate', 'arms', 'source', 'sourceExpected')})
                body += detail('原版 / 原生事实及证据', result)
                body += '</article>'
            name = 'group-' + group + '-page-' + f'{i+1:03d}' + '.html'
            (args.out / name).write_text(shell(group + ' 组 · 第 ' + str(i+1) + '/' + str(count) + ' 页', body + nav), 'utf-8')
            pages.append({'path': name, 'ids': [row['id'] for row in subset], **file_identity(args.out / name)})
    body = '<div class="panel"><strong>' + esc(data['auditStatus']) + '</strong>' + detail('本轮统计', data.get('counts', {})) + detail('结论分类', counts) + '<p>本轮统计针对明确列出的有限分支，不能当作全项目源码分支覆盖率。</p></div><div class="groups">'
    for group in groups:
        n = sum(row['group'] == group for row in rows)
        body += '<div class="panel"><h2>' + esc(group) + ' 组</h2><p>' + str(n) + ' 条分支记录</p><a href="group-' + esc(group) + '-page-001.html">查看核实结论</a></div>'
    body += '</div>' + detail('范围边界与未展开项', data.get('coverageBoundaries', []))
    body += '<p><a download href="verification.json">下载完整核实 JSON</a></p>'
    (args.out / 'index.html').write_text(shell('分支覆盖核实 · 第四轮', body), 'utf-8')
    with (args.out / 'verification.json').open('xb') as stream:
        stream.write(args.summary.read_bytes())
    write_json(args.out / 'summary-report.json', {'schema': 'py-mermaid-branch-summary-report/v1', 'functionalStatus': 'NOT_EVALUATED',
               'auditStatus': data['auditStatus'], 'sourceTreeSha256': data['sourceTreeSha256'], 'input': file_identity(args.summary),
               'branchRecords': len(rows), 'classifications': counts, 'pages': pages, 'report': file_identity(args.out / 'index.html')}, exclusive=True)
    print(json.dumps({'branchRecords': len(rows), 'pages': len(pages), 'classifications': counts}))


if __name__ == '__main__':
    main()
