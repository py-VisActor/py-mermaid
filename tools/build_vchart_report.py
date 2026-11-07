"""Publish a paginated native VChart A/B report, preserving raw image bytes."""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import shutil

from build_report_rounds import CSS, document
from collect_vchart_report_inputs import evidence, unique
from run_support import ROOT


def identity(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    escape = html.escape
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--supplier', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mermaid', type=Path, help='Optional native/source combined Mermaid report data')
    p.add_argument('--bridge', type=Path, help='Optional normalized consumer spec API evidence')
    p.add_argument('--rehearsal',action='store_true',help='Old-candidate preview, never final acceptance')
    p.add_argument('--note',default='',help='Explicit manual defects/limitations preserved on every page')
    p.add_argument('--visual-review',type=Path,help='Existing manual review receipt, bound by hash')
    p.add_argument('--acceptance',type=Path,help='Existing acceptance receipt; this tool never creates acceptance')
    args = p.parse_args()
    data = json.loads((args.supplier / 'result.json').read_text('utf-8'))
    supplier_proof=evidence(args.supplier/'result.json')
    if len(unique(data['results'],'supplier'))!=225:raise ValueError('Supplier225 denominator differs')
    if not args.bridge or not args.mermaid:raise ValueError('Report requires supplier225 + bridge68 + Mermaid42')
    args.out.mkdir(parents=True, exist_ok=False)
    attachments={}
    for key,path in [('visualReview',args.visual_review),('acceptance',args.acceptance)]:
        if path:
            value=json.loads(path.read_text('utf-8'))
            candidate=value.get('candidateRun')
            source_sha=value.get('sourceTreeSha256')
            if candidate and (ROOT/candidate).resolve()!=Path(supplier_proof['run']).resolve():
                raise ValueError('Receipt candidate differs from report source run')
            if source_sha and source_sha!=supplier_proof['sourceTreeSha256']:
                raise ValueError('Receipt candidate source hash differs')
            if key=='acceptance' and (args.rehearsal or not (candidate or source_sha)):
                raise ValueError('Acceptance requires a bound candidate and cannot be attached to rehearsal')
            if key=='acceptance' and value.get('status')!='PASS':
                raise ValueError('Acceptance receipt must already have passed its independent checks')
            target=args.out/(key+'.json');shutil.copyfile(path,target)
            attachments[key]={'path':target.name,'sourcePath':str(path.resolve()),'status':value.get('status') or value.get('verdict'),**identity(target)}
    groups = [('VChart 原生 Canvas：固定上游 225 例', data['results'], args.supplier, 'supplier')]
    if args.bridge:
        value = json.loads((args.bridge / 'result.json').read_text('utf-8'))
        groups.append(('Mermaid 统一规格 API：全部 68 类型', value['results'], args.bridge, 'bridge'))
    if args.mermaid:
        value = json.loads((args.mermaid / 'result.json').read_text('utf-8'))
        groups.append(('Mermaid 七类图表语法', value['results'], args.mermaid, 'mermaid'))
    manifest = {'schema': 'py-mermaid-vchart-report/v1', 'source': identity(args.supplier / 'result.json'),
                'purpose':'REHEARSAL_OLD_CANDIDATE_NOT_ACCEPTANCE' if args.rehearsal else 'VALIDATION_EVIDENCE_NOT_NEW_ACCEPTANCE',
                'sourceRun':supplier_proof,'pageSize':12,'manualNote':args.note,'groups':[],
                'functionalStatus':'NOT_REEVALUATED','attachments':attachments,
                'scope':{'included':'225 supplier static cases +68 explicit JSON types +42 Mermaid syntax cases',
                         'notClaimed':['All JS advanced/static options','Dagre, interactive or3D charts','Previously identified22 Mermaid branch gaps','Arbitrary browser HTML/CSS'],
                         'distribution':'Formal GitHub release wheel; PyPI publication remains BLOCKED (invalid-publisher)'},
                'candidate': {'version': data['version'], 'canvas': data['canvas'], 'backend': data['backend']},
                'note': 'New default Canvas and legacy strict reference are distinct validation contracts. Pixels are diagnostic; text, topology and exports are checked independently.',
                'pages': [], 'assets': {}, 'cases': []}
    banner=('旧候选报告预演 · 不作为最终验收' if args.rehearsal else '已有验证证据展示 · 不重新执行或提升验收状态')
    home = ['<p class="note">'+html.escape(banner)+'</p>',
            '<p>本轮新增图表接入。原始上游与 Python 图片逐字节复制；每页最多 12 例。</p>',
            '<p>数字与像素差异须结合内容和可读性审阅。此报告不宣称全部 JS 高级选项或此前 22 条分支缺口已完成。</p>']
    if args.note:home.append('<p class="note">'+html.escape(args.note)+'</p>')
    home.append('<p class="note">交付：GitHub 正式 wheel；PyPI 发布仍受阻（invalid-publisher），不标记为 PyPI 已发布。静态词云的两个重复填充数量差异按独立字体占位策略列出，exact mismatch 并未改写为相等。Treemap 原版透明叶白字不可见保留为源缺陷，不由报告生成器修图。</p>')
    home.append('<p>展示范围：225 个供应方静态案例、68 种显式 JSON 规格与42个七类 Mermaid 语法案例。包括成功绘制、源拒绝输入和显式原生限制；不将全部42例统称为成功绘图。最终接受范围以所附验收记录为准。</p>')
    for key,value in attachments.items():
        home.append('<p><a href="'+value['path']+'">'+escape(key)+' · '+escape(str(value['status']))+'</a></p>')
    for title, rows, root, prefix in groups:
        expected={'supplier':225,'bridge':68,'mermaid':42}[prefix]
        if len(unique(rows,prefix))!=expected:raise ValueError('Report group denominator differs: '+prefix)
        manifest['groups'].append({'id':prefix,'cases':len(rows),'statuses':dict(Counter(r['status'] for r in rows)),
                                   'classifications':dict(Counter('NATIVE_FONT_POLICY_EXACT_MISMATCH' if r.get('nativeFontPolicy') else r.get('classification','AUTOMATED_RESULT_ONLY') for r in rows))})
        proof_file=root.parent/'raw-provenance.json'
        proofs=json.loads(proof_file.read_text('utf-8'))['rawAssets'] if prefix!='supplier' else None
        home.append(f'<section class="panel"><h2>{escape(title)}</h2><p>{escape(str(dict(Counter(r["status"] for r in rows))))}</p><nav>')
        home.append('<p>分类：'+escape(str(manifest['groups'][-1]['classifications']))+'</p>')
        count = (len(rows) + 11) // 12
        for page in range(count):
            name = f'{prefix}-{page + 1:02}.html'
            home.append(f'<a href="{name}">第 {page + 1} 页</a>')
            body = []
            batch = rows[page * 12:(page + 1) * 12]
            for row in batch:
                case_id = row['id']
                relative = Path(case_id)
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('Invalid case path')
                source = (root / relative).resolve(strict=True)
                if not source.is_relative_to(root.resolve()):
                    raise ValueError('Case escaped input root')
                destination = args.out / 'assets' / prefix / relative
                destination.mkdir(parents=True)
                files = []
                for file in sorted(source.iterdir()):
                    if file.is_file() and file.suffix in ('.png', '.svg', '.pdf', '.jpg', '.webp', '.json', '.mmd'):
                        target = destination / file.name
                        if prefix=='supplier':source_proof=evidence(file)
                        else:
                            source_proof=proofs.get(prefix+'/'+relative.as_posix()+'/'+file.name)
                            if source_proof is not None and identity(file)!={k:source_proof[k] for k in ('bytes','sha256')}:
                                raise ValueError('Normalized raw asset drift: '+str(file))
                        shutil.copyfile(file, target)
                        assert identity(file) == identity(target)
                        url = target.relative_to(args.out).as_posix()
                        manifest['assets'][url] = {**identity(target),'sourcePath':str(file.resolve()),
                                                   'originalRunProof':source_proof}
                        files.append((file.name, url))
                category=('NATIVE_FONT_POLICY_EXACT_MISMATCH' if row.get('nativeFontPolicy') else row.get('classification','AUTOMATED_RESULT_ONLY'))
                body.append(f'<article class="case" id="case-{len(manifest["cases"])}" data-group="{prefix}" data-case="{escape(case_id,quote=True)}" data-status="{escape(row["status"],quote=True)}"><h2>{escape(case_id)} · {escape(row["status"])}</h2><p class="badge">{escape(category)}</p><div class="grid">')
                for label, filename in [('固定上游', 'expected.png'), ('Python 原生 Canvas', 'actual.png'), ('原始像素差', 'diff.png')]:
                    match = next((url for name, url in files if name == filename), None)
                    body.append('<figure class="image"><figcaption>' + label + '</figcaption>' +
                                (f'<img loading="lazy" alt="{label}" src="{escape(match, quote=True)}">' if match else '<p>此项未生成图片；状态与原始记录见下方。</p>') + '</figure>')
                body.append('</div>')
                if row.get('nativeFontPolicy'):
                    policy=row['nativeFontPolicy']
                    body.append('<p class="note">允许的原生字体占位差异：原版重复词数量 '+escape(str(policy.get('referenceWordCount')))+
                        '，原生 '+escape(str(policy.get('nativeWordCount')))+'；textEqual='+escape(str(row.get('textEqual')))+
                        '，structureEqual='+escape(str(row.get('structureEqual')))+'，exactRepeatedWordMultiset='+escape(str(policy.get('exactRepeatedWordMultiset')))+
                        '。主体文字、实际核心墨迹与边界通过专门策略验证，重复数量并非精确相等。</p>')
                if prefix=='mermaid' and 'treemap' in str(row.get('kind','')).lower():
                    body.append('<p class="note">源行为注意：透明叶上的白色标签可能在原版中不可见；原始图不重绘、不修色。当前图片仍按此候选的原始结果展示。</p>')
                body.append('<details><summary>原始文件与检查结果</summary><nav>')
                body += [f'<a href="{escape(url, quote=True)}">{escape(name)}</a>' for name, url in files]
                compact = {k: v for k, v in row.items() if k not in ('numericDifferences', 'traceback')}
                body.append('</nav><pre>' + escape(json.dumps(compact, ensure_ascii=False, indent=2)) + '</pre></details></article>')
                manifest['cases'].append({'id': case_id,'group':prefix,'anchor':'case-'+str(len(manifest['cases'])), 'page': name, 'status': row['status'],'classification':category})
            navigation = '<nav><a href="index.html">轮次入口</a>' + ''.join(
                f'<a href="{prefix}-{i + 1:02}.html">{i + 1}</a>' for i in range(count)) + '</nav>'
            (args.out / name).write_text(document(title + f' · {page + 1}/{count}', ''.join(body),
                navigation=navigation, note=banner+'。'+args.note+' 原始图片与检查状态；像素差异不自动等于功能失败或通过。'), 'utf-8')
            manifest['pages'].append({'path': name,'group':prefix, 'cases': len(batch),'report':identity(args.out/name)})
        home.append('</nav></section>')
    (args.out / 'index.html').write_text(document('第五轮 · VChart 图表接入', ''.join(home)), 'utf-8')
    manifest['index']=identity(args.out/'index.html')
    (args.out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps({'pages': len(manifest['pages']), 'cases': len(manifest['cases']), 'rawAssets': len(manifest['assets'])}))


if __name__ == '__main__':
    main()
