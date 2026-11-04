"""F01.1 source-defined cases, official A comparison and real-PNG checks.

Use a fresh --out directory. Pixel metrics remain diagnostic; L1/L2/L3 checks
decide status. This is a development tool and is excluded from product wheels.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import traceback

from PIL import Image, ImageColor
from py_mermaid import MermaidError, parse, render
from run_support import Run

ROOT = Path(__file__).resolve().parents[1]


def norm(text):
    return ' '.join(text.split())


def check_scene(scene, png, expected):
    """Check semantic content, measured containment and actual painted pixels."""
    errors = []
    diagram = scene['diagram']
    if [(n['id'], norm(n['label'])) for n in diagram['nodes']] != [(i,norm(t)) for i,t in expected['nodes']]:
        errors.append('L1 node identity/label/order')
    if [(e['source'],e['target']) for e in diagram['edges']] != [tuple(e) for e in expected['edges']]:
        errors.append('L1 edge relationships/order')
    if diagram['direction'] != expected['direction']:
        errors.append('L1 direction')
    image = Image.open(io.BytesIO(png)).convert('RGB')
    if image.size != (scene['width'], scene['height']):
        errors.append('L2 encoded dimensions')
    w,h = image.size
    nodes = {n['id']:n['box'] for n in scene['layout']['nodes']}
    trace = scene['trace']
    # A dark pixel is checked only inside a predicted foreground area. A white
    # no-op or a missing text/arrow cannot pass merely because trace exists.
    def dark_near(x,y,radius=2):
        for yy in range(max(0,int(y)-radius),min(h,int(y)+radius+2)):
            for xx in range(max(0,int(x)-radius),min(w,int(x)+radius+2)):
                if max(image.getpixel((xx,yy))) < 190:
                    return True
        return False
    for node in diagram['nodes']:
        events = [e for e in trace if e['kind']=='node' and e['semantic_id']==node['id']]
        texts = [e for e in trace if e['kind']=='text' and e['semantic_id']==node['id']]
        if len(events)!=1 or norm(' '.join(e['text'] for e in texts))!=norm(node['label']):
            errors.append('L2 missing node/text '+node['id']);continue
        b=events[0]['box']
        if min(b['x'],b['y']) < 0 or b['x']+b['width']>w or b['y']+b['height']>h:
            errors.append('L3 clipped node '+node['id'])
        if not dark_near(b['x'], b['y']+b['height']/2):
            errors.append('L2 unpainted node '+node['id'])
        for text in texts:
            t=text['box']
            if (t['x']<b['x']-.01 or t['y']<b['y']-.01 or t['x']+t['width']>b['x']+b['width']+.01
                    or t['y']+t['height']>b['y']+b['height']+.01):
                errors.append('L3 text outside node '+node['id'])
            if text['text'].strip():
                region=image.crop((max(0,math.floor(t['x'])),max(0,math.floor(t['y'])),
                                   min(w,math.ceil(t['x']+t['width']+1)),min(h,math.ceil(t['y']+t['height']+1))))
                if not any(max(p)<190 for p in region.getdata()):
                    errors.append('L2 unpainted text '+node['id'])
    for edge in diagram['edges']:
        lines=[e for e in trace if e['kind']=='edge' and e['semantic_id']==edge['id']]
        arrows=[e for e in trace if e['kind']=='arrow' and e['semantic_id']==edge['id']]
        if not lines or len(arrows)!=1:
            errors.append('L2 missing edge/arrow '+edge['id']);continue
        for line in lines:
            for a,b in zip(line['points'],line['points'][1:]):
                if math.hypot(a['x']-b['x'],a['y']-b['y'])>3 and not dark_near((a['x']+b['x'])/2,(a['y']+b['y'])/2):
                    errors.append('L2 unpainted edge '+edge['id'])
        triangle=arrows[0]['points']
        if not dark_near(sum(p['x'] for p in triangle)/3,sum(p['y'] for p in triangle)/3):
            errors.append('L2 unpainted arrow '+edge['id'])
        last=lines[-1]['points'];previous=next((p for p in reversed(last[:-1]) if p!=last[-1]),None)
        if previous:
            tip=triangle[0];base={'x':(triangle[1]['x']+triangle[2]['x'])/2,'y':(triangle[1]['y']+triangle[2]['y'])/2}
            if (tip['x']-base['x'])*(last[-1]['x']-previous['x'])+(tip['y']-base['y'])*(last[-1]['y']-previous['y'])<=0:
                errors.append('L3 reversed arrow '+edge['id'])
        # Layout endpoint and ordering relations use engine coordinates, so no
        # equality with browser coordinates or natural sizes is required.
        route=next(e for e in scene['layout']['edges'] if e['id']==edge['id'])
        def on_boundary(point,box):
            x,y=point['x'],point['y'];l,t=box['x'],box['y'];r,b=l+box['width'],t+box['height'];eps=1e-4
            return l-eps<=x<=r+eps and t-eps<=y<=b+eps and min(abs(x-l),abs(x-r),abs(y-t),abs(y-b))<=eps
        if not on_boundary(route['sections'][0]['start'],nodes[edge['source']]) or not on_boundary(route['sections'][-1]['end'],nodes[edge['target']]):
            errors.append('L3 wrong endpoint '+edge['id'])
    return errors


def controls(scene,png,case):
    """Fault controls prove the checker rejects missing content and no-op output."""
    import copy
    outcomes={}
    white=Image.new('RGB',(scene['width'],scene['height']),'white');buf=io.BytesIO();white.save(buf,format='PNG')
    outcomes['white_noop_rejected']=bool(check_scene(scene,buf.getvalue(),case))
    slight=image=Image.open(io.BytesIO(png)).convert('RGB').point(lambda x:min(255,x+1))
    buf=io.BytesIO();slight.save(buf,format='PNG')
    outcomes['normal_channel_variation_accepted']=not check_scene(scene,buf.getvalue(),case)
    for kind in ('node','text','edge','arrow'):
        if not any(e['kind']==kind for e in scene['trace']):continue
        bad=copy.deepcopy(scene);bad['trace']=[e for e in bad['trace'] if e['kind']!=kind]
        outcomes['missing_'+kind+'_rejected']=bool(check_scene(bad,png,case))
    bad=copy.deepcopy(scene);bad['diagram']['nodes'][0]['label']='WRONG CONTENT'
    outcomes['wrong_content_rejected']=bool(check_scene(bad,png,case))
    bad=copy.deepcopy(scene);node=next(e for e in bad['trace'] if e['kind']=='node');node['box']['x']=-20
    outcomes['clipping_rejected']=bool(check_scene(bad,png,case))
    if scene['diagram']['edges']:
        bad=copy.deepcopy(scene);bad['diagram']['edges'][0]['target']=bad['diagram']['edges'][0]['source']
        outcomes['wrong_relation_rejected']=bool(check_scene(bad,png,case))
        bad=copy.deepcopy(scene);arrow=next(e for e in bad['trace'] if e['kind']=='arrow');tip=arrow['points'][0]
        for p in arrow['points'][1:]:p['x']=2*tip['x']-p['x'];p['y']=2*tip['y']-p['y']
        outcomes['wrong_arrow_rejected']=bool(check_scene(bad,png,case))
    return outcomes


def validate(args, diagnostics):
    fixture=json.loads(args.fixtures.read_text(encoding='utf-8'))
    cases=fixture['cases']
    report={'backend':args.backend,'cases':[],'functionalStatus':'NOT_EVALUATED'}
    for case in cases:
        entry={'id':case['id'],'errors':[]}
        try:
            result=render(case['text'],backend=args.backend);scene=asdict(result);scene.pop('data')
            png=args.out/(case['id']+'.png');png.write_bytes(result.data)
            (args.out/(case['id']+'.json')).write_text(json.dumps(scene,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            entry['errors']=check_scene(scene,result.data,case)
            official=json.loads((args.oracle/(case['id']+'.json')).read_text(encoding='utf-8'))
            if [(n['id'],norm(n['label'])) for n in official['nodes']]!=[(i,norm(t)) for i,t in case['nodes']]:entry['errors'].append('A semantic source disagreement')
            if [(e['source'],e['target']) for e in official['edges']]!=[tuple(e) for e in case['edges']]:entry['errors'].append('A edge source disagreement')
            if len(official['drawnNodes'])!=len(case['nodes']) or len(official['drawnEdges'])!=len(case['edges']):entry['errors'].append('A incomplete drawn structure')
            if any(not e['markerEnd'] for e in official['drawnEdges']):entry['errors'].append('A missing arrow marker')
            for node in official['drawnNodes']:
                for css,key in [('fill','fill'),('stroke','stroke')]:
                    if ImageColor.getrgb(node[css])!=ImageColor.getrgb(scene['diagram']['config'][key]):
                        entry['errors'].append('L2 default style disagrees with A: '+css)
            entry['controls']=controls(scene,result.data,case)
            if not all(entry['controls'].values()):entry['errors'].append('Comparator fault control failed')
            command=[sys.executable,str(ROOT/'tools/pixel_compare.py'),'--reference',str(args.oracle/(case['id']+'.png')),'--candidate',str(png),'--out',str(args.out/(case['id']+'-pixels'))]
            pixel=diagnostics.command(case['id'],command);entry['pixelDiagnosticExitCode']=pixel['exitCode']
            entry['pixelLogs']={'run':str(diagnostics.path),'stdout':pixel['stdout'],'stderr':pixel['stderr']}
            if pixel['exitCode']:entry['errors'].append('Pixel tool failed to complete')
            entry['pngSha256']=hashlib.sha256(result.data).hexdigest();entry['engine']=dict(result.backend)
            entry['rendererVariation']='Browser/Canvas text metrics, natural sizes and ELK0.9.3/0.12.1 routes can differ; pixels diagnostic only'
        except Exception:
            entry['errors'].append(traceback.format_exc())
        entry['status']='FAIL' if entry['errors'] else 'PASS';report['cases'].append(entry)
    report['negativeCases']=[]
    for case in fixture.get('negativeCases',[]):
        entry={'id':case['id'],'status':'FAIL'}
        official=json.loads((args.oracle/(case['id']+'.negative.json')).read_text(encoding='utf-8'))
        try:
            parse(case['text'])
            entry['error']='Python accepted invalid official input'
        except MermaidError as error:
            entry.update(status='PASS' if official['rejected'] and error.span is not None else 'FAIL',code=error.code,span=asdict(error.span) if error.span else None)
        report['negativeCases'].append(entry)
    report['functionalStatus']='FAIL' if any(e['status']=='FAIL' for e in report['cases']+report['negativeCases']) else 'PASS'
    (args.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'functionalStatus':report['functionalStatus'],'passed':sum(e['status']=='PASS' for e in report['cases']),'total':len(cases)}))
    return 1 if report['functionalStatus']=='FAIL' else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--oracle',type=Path,required=True)
    parser.add_argument('--backend',choices=('auto','cpu','gpu'),default='auto')
    parser.add_argument('--fixtures',type=Path,default=ROOT/'tests/f011/cases.json')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    with Run('F01.1','pixel-diagnostics',runs_dir=args.out/'logs') as diagnostics:
        diagnostics.input(args.fixtures)
        return validate(args,diagnostics)


if __name__=='__main__':
    raise SystemExit(main())
