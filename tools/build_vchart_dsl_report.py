"""Build round-six DSL evidence pages from one closed, immutable matrix Run."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import shutil

from build_report_rounds import CSS
from collect_vchart_report_inputs import evidence
from run_support import ROOT


GROUPS = {'supplier': (225, '225 个固定供应方规格'),
          'representative': (68, '68 类型代表规格'),
          'example': (8, '8 组手写语言与资源示例')}
EXTENSIONS = {'.vchart', '.json', '.png', '.svg', '.pdf', '.jpg', '.jpeg', '.webp'}


def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def page(title, content, navigation='', banner=''):
    esc = html.escape
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + esc(title) + '</title><style>' + CSS + '</style></head><body><header>' + navigation +
            '<h1>' + esc(title) + '</h1><p class="note">' + esc(banner) +
            '</p></header><main>' + content + '</main><footer>原始证据逐字节复制 · '
            '报告仅展示既有结果，不执行产品、不产生新验收结论。</footer></body></html>')


def safe_child(root, relative):
    path = Path(relative)
    if path.is_absolute() or not path.parts or '..' in path.parts or '\\' in relative or ':' in relative:
        raise ValueError('Unsafe matrix case path: ' + relative)
    result = (root / path).resolve(strict=True)
    if not result.is_relative_to(root.resolve()):
        raise ValueError('Matrix case escapes root')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--acceptance', type=Path)
    parser.add_argument('--visual-review', type=Path)
    parser.add_argument('--rehearsal', action='store_true')
    args = parser.parse_args()
    matrix = args.matrix.resolve(strict=True)
    input_path = matrix / 'result.json'
    proof = evidence(input_path)
    data = json.loads(input_path.read_text(encoding='utf-8'))
    if data.get('schema') != 'py-mermaid-vchart-dsl-matrix/v1':
        raise ValueError('Unsupported matrix schema')
    source_sha = data.get('source', {}).get('sourceTreeSha256')
    if not source_sha or source_sha != proof['sourceTreeSha256']:
        raise ValueError('Matrix / closed Run source identity mismatch')
    rows = data['cases']
    if not isinstance(rows, list) or len(rows) != 301:
        raise ValueError('Matrix must preserve 225+68+8=301 case records')
    keys = set()
    for row in rows:
        key = (row.get('group'), str(row.get('id', '')).casefold())
        if key in keys or key[0] not in GROUPS or not key[1] or row.get('status') not in ('PASS', 'FAIL'):
            raise ValueError('Duplicate / invalid matrix case or status: ' + str(key))
        if not isinstance(row.get('type'), str) or not row['type']:
            raise ValueError('Every matrix record needs its actual chart type')
        keys.add(key)
    for group, (count, _) in GROUPS.items():
        if sum(r['group'] == group for r in rows) != count:
            raise ValueError('Matrix group denominator mismatch: ' + group)
    if len({r['type'] for r in rows if r['group'] == 'representative'}) != 68:
        raise ValueError('Representative records must cover 68 distinct types')
    output = args.out.resolve()
    if output == matrix or output.is_relative_to(matrix):
        raise ValueError('Report cannot write into closed matrix evidence')
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'schema': 'py-mermaid-vchart-dsl-report/v1', 'pageSize': 12,
                'purpose': 'REHEARSAL_OLD_CANDIDATE_NOT_ACCEPTANCE' if args.rehearsal else 'VALIDATION_EVIDENCE_NOT_NEW_ACCEPTANCE',
                'functionalStatus': 'NOT_REEVALUATED', 'sourceRun': proof,
                'sourceTreeSha256': source_sha, 'backend': data.get('backend'),
                'sourceResult': {'path': 'matrix.result.json', **identity(input_path)},
                'groups': [], 'cases': [], 'pages': [], 'assets': {}, 'attachments': {},
                'scope': {'distribution': 'PyPI formal py-visactor-vchart==0.1.1',
                          'counts': {'supplier': 225, 'representative': 68, 'example': 8},
                          'typeCount': 68, 'caseCount': 301,
                          'notClaimed': ['Previously identified 22 Mermaid branch gaps',
                                         'Supplier advanced/static restrictions', 'Dagre / interaction / animation / 3D',
                                         'Video/audio and arbitrary browser HTML/CSS']}}
    shutil.copyfile(input_path, output / 'matrix.result.json')
    for key, supplied in [('acceptance', args.acceptance), ('visualReview', args.visual_review)]:
        if supplied is None:
            continue
        value = json.loads(supplied.read_text(encoding='utf-8'))
        candidate = value.get('candidateRun') or value.get('baselineRun')
        if not candidate or not value.get('sourceTreeSha256'):
            raise ValueError('Optional receipt must bind both candidateRun and sourceTreeSha256')
        if (ROOT / candidate).resolve() != Path(proof['run']).resolve() or value['sourceTreeSha256'] != source_sha:
            raise ValueError('Receipt candidate differs from matrix')
        status = value.get('status') or value.get('verdict')
        if not isinstance(status, str) or not status:
            raise ValueError('Receipt needs its existing status, never a report-inferred status')
        if key == 'acceptance' and status.startswith('PASS') and any(row['status'] == 'FAIL' for row in rows):
            raise ValueError('Cannot attach passed acceptance to a matrix retaining failures')
        name = key + '.json'
        shutil.copyfile(supplied, output / name)
        manifest['attachments'][key] = {'path': name, 'sourcePath': str(supplied.resolve()),
                                         'status': status, **identity(output / name)}
    banner = ('旧候选预演 · 不是最终验收。' if args.rehearsal else
              '第六轮证据展示 · 保留原始 PASS/FAIL，不重新接受或提升首轮失败。')
    esc = html.escape
    home = ['<p>正式依赖：PyPI <code>py-visactor-vchart==0.1.1</code>。'
            '主对比为现有 spec API 与新 DSL；固定上游 PNG 仅作额外参考。</p>',
            '<p>225 固定规格、68 类型代表和8组示例有重叠来源；301是案例数，'
            '<strong>不是301种新类型</strong>。有效类型去重为68。</p>',
            '<p>仅保留二维静态能力；供应方已有选项限制、此前22条 Mermaid 分支缺口单独保留。'
            '交互、动画、Dagre、3D、video/audio、任意 HTML/CSS 扩展不在本轮范围。</p>',
            '<p>源候选 <code>' + esc(source_sha) + '</code>；后端 ' + esc(str(data.get('backend'))) +
            '；矩阵原始状态 ' + esc(str(dict(Counter(r['status'] for r in rows)))) + '</p>',
            '<nav><a href="matrix.result.json">原始矩阵结果与检查状态</a></nav>']
    for key, value in manifest['attachments'].items():
        home.append('<p><a href="' + value['path'] + '">' + esc(key + ': ' + value['status']) + '</a></p>')
    for group, (count, title) in GROUPS.items():
        selected = [row for row in rows if row['group'] == group]
        pages = (count + 11) // 12
        manifest['groups'].append({'id': group, 'cases': count, 'statuses': dict(Counter(r['status'] for r in selected))})
        home.append('<section class="panel"><h2>' + esc(title) + '</h2><p>' +
                    esc(str(manifest['groups'][-1]['statuses'])) + '</p><nav>')
        for index in range(pages):
            name = f'{group}-{index + 1:02}.html'
            home.append(f'<a href="{name}">第{index + 1}页</a>')
            body = []
            batch = selected[index * 12:(index + 1) * 12]
            for row in batch:
                case_id = row['id']
                source = safe_child(matrix / group, case_id)
                copied = {}
                for file in sorted(source.rglob('*')):
                    if not file.is_file() or file.suffix.lower() not in EXTENSIONS:
                        continue
                    if file.is_symlink() or not file.resolve().is_relative_to(source):
                        raise ValueError('Unsafe raw asset path')
                    raw_proof = evidence(file)
                    if raw_proof['sourceTreeSha256'] != source_sha or raw_proof['run'] != proof['run']:
                        raise ValueError('Raw case asset belongs to a different candidate')
                    relative = file.relative_to(source)
                    target = output / 'assets' / group / case_id / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(file, target)
                    if identity(file) != identity(target):
                        raise ValueError('Raw byte copy differs')
                    url = target.relative_to(output).as_posix()
                    manifest['assets'][url] = {**identity(target), 'sourcePath': str(file.resolve()),
                                               'originalRunProof': raw_proof}
                    copied[relative.as_posix()] = url
                anchor = 'case-' + str(len(manifest['cases']))
                body.append('<article class="case" id="' + anchor + '" data-group="' + group +
                            '" data-case="' + esc(case_id, quote=True) + '" data-status="' + row['status'] +
                            '"><h2>' + esc(case_id + ' · ' + row['status']) + '</h2><p>类型：' + esc(str(row.get('type'))) + '</p><div class="grid">')
                for label, filename in [('现有 spec API', 'api.png'), ('新 VChart DSL', 'actual.png'),
                                        ('原始差异图（诊断）', 'diff.png'), ('固定上游参考（可选）', 'upstream.png')]:
                    url = copied.get(filename)
                    if filename == 'upstream.png' and url is None:
                        continue
                    body.append('<figure class="image"><figcaption>' + label + '</figcaption>' +
                                ('<img loading="lazy" alt="' + label + '" src="' + esc(url, quote=True) + '">' if url else
                                 '<p class="absent">未生成此图片；不制造占位成功图，请查看原始失败记录。</p>') + '</figure>')
                body.append('</div><details><summary>DSL 源文、原始文件、哈希与检查结果</summary><nav>')
                for filename, url in copied.items():
                    item = manifest['assets'][url]
                    body.append('<a href="' + esc(url, quote=True) + '">' + esc(filename) + '</a>')
                    body.append('<small>' + str(item['bytes']) + ' bytes · SHA256 <code>' + item['sha256'] + '</code></small>')
                body.append('</nav>')
                if 'source.vchart' in copied:
                    body.append('<pre>' + esc((source / 'source.vchart').read_text(encoding='utf-8')) + '</pre>')
                body.append('<pre>' + esc(json.dumps(row, ensure_ascii=False, indent=2)) + '</pre></details></article>')
                manifest['cases'].append({'id': case_id, 'group': group, 'type': row.get('type'), 'status': row['status'],
                                           'page': name, 'anchor': anchor, 'assets': list(copied.values())})
            navigation = '<nav><a href="index.html">第六轮入口</a>' + ''.join(
                f'<a href="{group}-{i + 1:02}.html">{i + 1}</a>' for i in range(pages)) + '</nav>'
            (output / name).write_text(page(title + f' · {index + 1}/{pages}', ''.join(body), navigation, banner), encoding='utf-8')
            manifest['pages'].append({'path': name, 'group': group, 'cases': len(batch), 'report': identity(output / name)})
        home.append('</nav></section>')
    (output / 'index.html').write_text(page('第六轮 · VChart DSL', ''.join(home), banner=banner), encoding='utf-8')
    manifest['index'] = identity(output / 'index.html')
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'pages': len(manifest['pages']), 'cases': len(rows), 'assets': len(manifest['assets']), 'functionalStatus': 'NOT_REEVALUATED'}))


if __name__ == '__main__':
    main()
