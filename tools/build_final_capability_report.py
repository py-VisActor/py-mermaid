"""Paginate an existing final capability review, preserving statuses and bytes.

This tool executes no product, renderer, tests or acceptance logic. A completed
review with unresolved capabilities remains a release-blocked review.
"""
from __future__ import annotations

import argparse
from collections import Counter
import html
import json
from pathlib import Path
import re
import shutil

from build_report_rounds import CSS
from run_support import ROOT, file_identity, write_json

GROUPS = {'functional': '功能缺口', 'chart_limit': '图表供应方限制',
          'release_gate': '发布门禁', 'unverified': '尚未验证'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def original(name):
    path = Path(name)
    path = path if path.is_absolute() else ROOT / path
    resolved = path.resolve(strict=True)
    require(resolved.is_relative_to(ROOT) and resolved.is_file() and not path.is_symlink(),
            'Evidence must be a regular file within ROOT: ' + str(name))
    return resolved


def esc(value):
    return html.escape(str(value), quote=True)


def rendered_json(value):
    return esc(json.dumps(value, ensure_ascii=False, indent=2))


def page(title, body, navigation=''):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + esc(title) + '</title><style>' + CSS +
            '.blocked{background:#fff0ee;border-left:5px solid #b52b20;padding:16px;'
            'overflow-wrap:anywhere}p,li{overflow-wrap:anywhere}</style></head><body>'
            '<header>' + navigation + '<h1>' + esc(title) + '</h1>'
            '<p class="blocked">仍有缺失，暂停正式发布。复查完成不等于能力完整；'
            '本页只展示既有证据，不生成新验收结论。</p></header><main>' + body +
            '</main><footer>状态、分母与限制沿用原始复查；原始附件逐字节复制并核对 SHA-256。</footer></body></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source = original(args.summary)
    data = json.loads(source.read_text(encoding='utf-8-sig'))
    require(data.get('status') == 'REVIEW_COMPLETE_RELEASE_BLOCKED', 'Only an explicitly blocked review is supported')
    require(isinstance(data.get('schema'), str) and data['schema'], 'Review schema missing')
    require(re.fullmatch(r'[0-9a-f]{64}', data.get('sourceTreeSha256', '')), 'Source SHA missing')
    require(isinstance(data.get('candidateRun'), str) and data['candidateRun'], 'Candidate Run missing')
    rows = data.get('items')
    require(isinstance(rows, list) and rows, 'Review items must be a nonempty list')
    ids = set()
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get('id'), str) and row['id'], 'Item ID missing')
        require(row['id'].casefold() not in ids, 'Duplicate case-insensitive item ID')
        ids.add(row['id'].casefold())
        require(row.get('group') in GROUPS and isinstance(row.get('status'), str) and row['status'], 'Item group/status invalid')
        require(isinstance(row.get('title'), str) and isinstance(row.get('detail'), (str, dict, list)), 'Item title/detail missing')
    output = args.out.resolve()
    require(not source.is_relative_to(output), 'Output would contain original summary')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'attachments').mkdir()
    shutil.copyfile(source, output / 'summary.json')
    manifest = {'schema': 'py-mermaid-final-capability-report/v1', 'pageSize': 12,
                'status': data['status'], 'functionalStatus': 'NOT_REEVALUATED',
                'purpose': 'READ_ONLY_REVIEW_DISPLAY_NOT_NEW_ACCEPTANCE',
                'sourceTreeSha256': data['sourceTreeSha256'], 'candidateRun': data['candidateRun'],
                'summary': {'path': 'summary.json', 'originalPath': source.relative_to(ROOT).as_posix(), **file_identity(source)},
                'counts': data.get('counts'), 'scope': data.get('scope'), 'items': [], 'pages': [], 'assets': {}}
    copied = {}

    def attach(item):
        require(isinstance(item, dict) and isinstance(item.get('path'), str), 'Invalid evidence entry')
        path = original(item['path'])
        identity = file_identity(path)
        require(identity == {k: item[k] for k in ('sha256', 'bytes')}, 'Evidence SHA/bytes mismatch: ' + str(path))
        name = path.relative_to(ROOT).as_posix()
        if name not in copied:
            # Numeric unique names avoid Windows case-fold and basename collisions.
            suffix = re.sub(r'[^A-Za-z0-9_.-]', '_', path.name)
            target = 'attachments/' + f'{len(copied) + 1:04d}-' + suffix
            shutil.copyfile(path, output / target)
            require(file_identity(output / target) == identity, 'Copied evidence bytes differ')
            copied[name] = target
            manifest['assets'][target] = {'originalPath': name, **identity}
        return copied[name]

    global_links = [(attach(item), item['path']) for item in data.get('evidence', [])]
    item_links = {row['id']: [(attach(e), e['path']) for e in row.get('evidence', [])] for row in rows}
    home = ['<p>原始状态：<code>' + esc(data['status']) + '</code></p>',
            '<p>候选：<code>' + esc(data['candidateRun']) + '</code>；源码 <code>' + esc(data['sourceTreeSha256']) + '</code></p>',
            '<p>“未验证”“限制”“已确认缺口”和“发布门禁”保持原分类；测试通过不覆盖已知缺口。</p>',
            '<p><a href="summary.json">原始完整复查 JSON</a> · <a href="manifest.json">本报告字节清单</a></p>',
            '<h2>范围与计数</h2><pre>' + rendered_json({'scope': data.get('scope'), 'counts': data.get('counts')}) + '</pre>']
    for group, title in GROUPS.items():
        selected = [row for row in rows if row['group'] == group]
        if not selected:
            continue
        home.append('<section class="panel"><h2>' + esc(title) + ' · ' + str(len(selected)) + '</h2><nav>')
        pages = (len(selected) + 11) // 12
        for index in range(pages):
            name = group + '-' + f'{index + 1:02d}' + '.html'
            batch = selected[index * 12:(index + 1) * 12]
            home.append('<a href="' + name + '">第 ' + str(index + 1) + ' 页</a>')
            body = ''
            for row in batch:
                anchor = 'item-' + str(len(manifest['items']) + 1)
                body += ('<article class="case" id="' + anchor + '" data-case="' + esc(row['id']) +
                         '" data-status="' + esc(row['status']) + '" data-group="' + esc(group) + '">'
                         '<h2>' + esc(row['id']) + ' · ' + esc(row['title']) + '</h2><p class="badge">' + esc(row['status']) + '</p>')
                body += '<pre>' + (esc(row['detail']) if isinstance(row['detail'], str) else rendered_json(row['detail'])) + '</pre>'
                body += '<details><summary>完整原始条目与分支</summary><pre>' + rendered_json(row) + '</pre></details>'
                body += '<ul>' + ''.join('<li><a href="' + target + '">' + esc(label) + '</a></li>' for target, label in item_links[row['id']]) + '</ul></article>'
                manifest['items'].append({'id': row['id'], 'status': row['status'], 'group': group, 'page': name, 'anchor': anchor})
            navigation = '<nav><a href="index.html">复查首页</a>'
            if index:
                navigation += '<a href="' + group + '-' + f'{index:02d}' + '.html">上一页</a>'
            if index + 1 < pages:
                navigation += '<a href="' + group + '-' + f'{index + 2:02d}' + '.html">下一页</a>'
            navigation += '</nav>'
            (output / name).write_text(page(title + ' · 第 ' + str(index + 1) + ' 页', body, navigation), encoding='utf8')
            manifest['pages'].append({'path': name, 'group': group, 'items': len(batch), **file_identity(output / name)})
        home.append('</nav></section>')
    home.append('<h2>完整原始证据</h2><ul>' + ''.join('<li><a href="' + target + '">' + esc(label) + '</a></li>' for target, label in global_links) + '</ul>')
    manifest['itemCount'] = len(rows)
    manifest['actualGroups'] = dict(Counter(row['group'] for row in rows))
    manifest['actualStatuses'] = dict(Counter(row['status'] for row in rows))
    (output / 'index.html').write_text(page('py-mermaid 最终能力复查 · 有缺失，不发布', ''.join(home)), encoding='utf8')
    manifest['index'] = file_identity(output / 'index.html')
    write_json(output / 'manifest.json', manifest, exclusive=True)
    print(json.dumps({'status': 'REPORT_CREATED_NOT_NEW_ACCEPTANCE', 'reviewStatus': data['status'],
                      'out': str(output), 'items': len(rows), 'pages': len(manifest['pages']), 'attachments': len(copied)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
