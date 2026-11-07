"""Compare raw fixed-source SVG/metadata with actual native scene and pixels."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from PIL import Image,ImageColor
from support_c import cases,logical_arrow_components,native_projection,svg_projection


def read(path):return json.loads(path.read_text('utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def compact(value):return ''.join(value.split())


def errors_for(probe,projection,*,source=False,raw=None):
    kind=probe['type'];errors=[]
    if kind in ('endpoint','activation'):
        if len(projection['messages'])!=1:return ['message-count']
        m=projection['messages'][0];actors=projection['actors']
        for end,actor,expected in [('start',probe['sender'],probe['startOffset']),('end',probe['receiver'],probe['endOffset'])]:
            if abs(m[end][0]-actors[actor]-expected)>.05:errors.append(end+'-offset')
    elif kind=='central':
        expected=sorted(projection['actors'][c['actor']]+c['offset'] for c in probe['circles'])
        actual=sorted(c[0] for c in projection['circles'])
        if len(actual)!=len(expected) or any(abs(a-b)>.05 for a,b in zip(actual,expected)):errors.append('central-actor-relative-position')
    elif kind=='number':
        if len(projection['numbers'])!=1 or abs(projection['numbers'][0][0]-projection['actors'][probe['anchor']])>.05:errors.append('number-actor-anchor')
    elif kind=='self':
        if len(projection['messages'])!=1:return ['self-count']
        m=projection['messages'][0];cx=projection['actors'][probe['sender']]
        if abs(m['start'][0]-cx-probe['startOffset'])>.05:errors.append('self-start-offset')
        if abs(m['end'][0]-cx-1)>.05:errors.append('self-end-offset')
        if abs(m['end'][1]-m['start'][1]-(25 if probe['angular'] else 20))>.05:errors.append('self-height')
    elif kind=='frame':
        count=projection['frameCount']
        if count!=probe['requiredFrames']:errors.append('frame-count')
    elif kind=='comment':
        comments=projection['comments'];visible=''.join(c['text'] for c in comments)
        if compact(visible)!=compact(probe['visible']):errors.append('comment-visible-text')
        if source:
            spans=[s for c in comments for s in c['spans']]
            bold=any(s.get('font-weight') in ('bold','700') for s in spans)
            italic=any(s.get('font-style')=='italic' for s in spans)
        else:
            bold=any(c.get('font_weight') in ('bold','700') for c in comments)
            italic=any(c.get('font_style')=='italic' for c in comments)
        if bold!=probe['bold']:errors.append('comment-bold-token')
        if italic!=probe['italic']:errors.append('comment-italic-token')
    elif kind=='info':
        texts=raw['texts'] if source else raw['trace']
        found=[t for t in texts if t.get('text')==probe['version']]
        if len(found)!=1:return ['version-text-count']
        t=found[0];size=float(str(t['fontSize'] if source else t['font_size']).removesuffix('px'))
        if size!=probe['fontSize']:errors.append('version-font-size')
        if ImageColor.getrgb(t['fill'] if source else t['color'])!=ImageColor.getrgb(probe['color']):errors.append('version-paint')
    elif kind=='arrows':
        expected=probe['expected']
        if len(projection['messages'])!=len(expected):return ['all-26-message-count']
        for i,(m,e) in enumerate(zip(projection['messages'],expected)):
            if source:
                for field,side in [('markerStart','start'),('markerEnd','end')]:
                    match=re.search(r'(filled-head|arrowhead|crosshead|solidTopArrowHead|solidBottomArrowHead|stickTopArrowHead|stickBottomArrowHead)\)$',m[field])
                    actual=match[1] if match else ''
                    if actual!=e[side]:errors.append(f'arrow-{i}-{side}')
                if (m['class']=='messageLine1')!=e['dashed']:errors.append(f'arrow-{i}-dash')
            else:
                if bool(m['dash'])!=e['dashed']:errors.append(f'arrow-{i}-dash')
                components=projection['arrowComponents'].get('message-'+str(i),[])
                components,component_errors=logical_arrow_components(components)
                errors.extend(f'arrow-{i}-'+e for e in component_errors)
                expected_markers=[v for v in (e['start'],e['end']) if v]
                if len(components)!=len(expected_markers):errors.append(f'arrow-{i}-component-count')
                wanted=Counter({'arrowhead':'point','crosshead':'cross','filled-head':'open'}.get(marker,'half') for marker in expected_markers)
                actual=Counter('half' if c['kind']=='message-arrow' else c['marker'] for c in components)
                if actual!=wanted:errors.append(f'arrow-{i}-kind-multiplicity')
    else:raise ValueError('Unknown branch check '+kind)
    return errors


def main():
    import xml.etree.ElementTree as ET
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--oracle',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--fixtures',type=Path,help='Explicit follow-up fixture file; absent preserves the original frozen48')
    a=p.parse_args();rows=[]
    if a.out.exists():raise ValueError('Output must be a new file')
    manifest=read(a.native/'results.json');native_ids={c['id']:c for c in manifest['cases']}
    if manifest['source']['sourceTreeSha256']!='b605642cc285e95735f18d32f13ff8f98908bcae8e3fefb46120891edf42e268' or not manifest['sourceUnchanged']:raise ValueError('Native baseline/source identity differs')
    fixture_path=a.fixtures or Path(__file__).with_name('cases-C.json')
    selected=read(fixture_path)['cases']
    if len({c['id'] for c in selected})!=len(selected):raise ValueError('Duplicate probe fixture IDs')
    for case in selected:
        identifier=case['id'];row=dict(id=identifier,branch=case['branchProbe']['branch'],expected=case['branchProbe'],classification='TOOL_ERROR')
        try:
            op=a.oracle/(identifier+'.json');sp=a.oracle/(identifier+'.svg');np=a.native/(identifier+'.scene.json')
            original=read(op);scene=read(np);source=svg_projection(sp.read_text('utf8'));native=native_projection(scene)
            source['frameCount']=sum(e.attrib.get('data-et')=='control-structure' for e in ET.fromstring(sp.read_text('utf8')).iter())
            layout=scene.get('layout',{})
            native['frameCount']=len(layout.get('fragments',[])) if isinstance(layout,dict) else 0
            se=errors_for(case['branchProbe'],source,source=True,raw=original);ne=errors_for(case['branchProbe'],native,raw=scene)
            # Reject blank/no-op transport independently from geometry metadata.
            for directory,errors in [(a.oracle,se),(a.native,ne)]:
                im=Image.open(directory/(identifier+'.png')).convert('RGB')
                if len(set(im.getdata()))<4:errors.append('actual-png-no-ink')
            if native_ids.get(identifier,{}).get('status')!='CHECKS_PASSED':ne.append('native-content-gate')
            classification='SOURCE_EXPECTATION_MISMATCH' if se else 'NATIVE_BRANCH_DIFFERENCE' if ne else 'VERIFIED'
            row.update(classification=classification,sourceCheck='FAIL' if se else 'PASS',nativeCheck='FAIL' if ne else 'PASS',sourceErrors=se,nativeErrors=ne,sourceActual=source,nativeActual=native,
                       functionalReviewRequired=bool(ne and not se),
                       evidence={str(path):sha(path) for path in (op,sp,np,a.oracle/(identifier+'.png'),a.native/(identifier+'.png'))})
        except Exception as exc:row['error']=type(exc).__name__+': '+str(exc)
        rows.append(row)
    counts=dict(Counter(r['classification'] for r in rows));result=dict(schema='py-mermaid-branch-probe-C/v1',status='PASS' if all(r['classification']=='VERIFIED' for r in rows) else 'FAIL',sourceTreeSha256=manifest['source']['sourceTreeSha256'],backend=manifest['backend'],branches=rows,counts=counts,
        fixtures={'path':str(fixture_path.resolve()),'sha256':sha(fixture_path),'caseIds':[c['id'] for c in selected]},
        note='Source expectation mismatches are tool/source-contract findings. Native predicate differences (including exact coordinates) require source/native visual and semantic review; this tool never automatically claims a confirmed functional gap. No product invocation by this comparison tool.')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':result['status'],'counts':counts}));return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())
