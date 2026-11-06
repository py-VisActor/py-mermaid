"""F01.1 source-defined cases, official A comparison and real-PNG checks.

Use a fresh --out directory. Pixel metrics remain diagnostic; L1/L2/L3 checks
decide status. This is a development tool and is excluded from product wheels.
"""
from __future__ import annotations

import argparse
import base64
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
from scene_codec import json_ready

ROOT = Path(__file__).resolve().parents[1]


def fixture_resources(case):
    """Explicit offline fixture bytes; never fetch a fixture URL."""
    value=case.get('resources')
    if not value:return None
    from py_mermaid import ResourceBundle, ImageResource, IconResource, FontResource
    return ResourceBundle(
        images=tuple(ImageResource(item['id'],base64.b64decode(item['dataBase64'],validate=True),item.get('mime',''),item.get('sha256','')) for item in value.get('images',[])),
        icons=tuple(IconResource(item['id'],item['svg'],item.get('sha256','')) for item in value.get('icons',[])),
        fonts=tuple(FontResource(item['family'],str((ROOT/item['path']).resolve()),item.get('sha256','')) for item in value.get('fonts',[])))


def norm(text):
    return ' '.join(text.split())


def semantic_errors(diagram, expected):
    errors=[]
    if 'shapes' in expected and {n['id']:n.get('shape','square') for n in diagram['nodes']} != {i:expected['shapes'].get(i,'square') for i,_ in expected['nodes']}:
        errors.append('L1 node shapes')
    if 'edgeLabels' in expected and [e.get('label','') for e in diagram['edges']] != expected['edgeLabels']:
        errors.append('L1 edge labels')
    if 'groups' in expected:
        keys=('id','label','members','parent_id','direction')
        canonical=lambda gs:[{k:list(g.get(k,[])) if k=='members' else g.get(k) for k in keys} for g in gs]
        if canonical(diagram.get('groups',[]))!=canonical(expected['groups']):errors.append('L1 groups/membership/direction')
        parents={m:g['id'] for g in expected['groups'] for m in g['members']}
        if any(n.get('parent_id')!=parents.get(n['id']) for n in diagram['nodes']):errors.append('L1 node parent')
    return errors


def check_scene(scene, png, expected):
    """Check semantic content, measured containment and actual painted pixels."""
    errors = semantic_errors(scene['diagram'],expected)
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
    nodes = {n['id']:n['box'] for n in scene['layout']['nodes']+scene['layout'].get('groups',[])}
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
        # The true left outline of a slanted/concave shape is inside its bbox.
        # Search only the left outer band, away from the centered label.
        if not any(dark_near(b['x']+dx,b['y']+b['height']/2,1) for dx in range(math.ceil(min(b['width']/2,b['height']/2))+2)):
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
                mx,my=(a['x']+b['x'])/2,(a['y']+b['y'])/2
                covered=any(e['kind']=='edge-label-background' and e['box']['x']-2<=mx<=e['box']['x']+e['box']['width']+2 and e['box']['y']-2<=my<=e['box']['y']+e['box']['height']+2 for e in trace)
                if math.hypot(a['x']-b['x'],a['y']-b['y'])>3 and not covered and not dark_near(mx,my):
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
        if edge['source'] not in nodes or edge['target'] not in nodes:
            errors.append('L3 unknown endpoint '+edge['id']);continue
        def on_boundary(point,box,identifier):
            x,y=point['x'],point['y'];l,t=box['x'],box['y'];r,b=l+box['width'],t+box['height'];eps=1e-4
            shape=next((n.get('shape','square') for n in diagram['nodes'] if n['id']==identifier),'square')
            if shape in ('circle','doublecircle'):
                return abs(((x-(l+r)/2)/(box['width']/2))**2+((y-(t+b)/2)/(box['height']/2))**2-1)<eps
            if shape=='diamond':
                return abs(abs(x-(l+r)/2)/(box['width']/2)+abs(y-(t+b)/2)/(box['height']/2)-1)<eps
            if shape not in ('square','subroutine'):
                # Exact source-derived outline equations and off-centre ports
                # have independent unit coverage. Here require a bbox-contained
                # endpoint and actual attachment pixel in the output trace.
                return l-eps<=x<=r+eps and t-eps<=y<=b+eps
            return l-eps<=x<=r+eps and t-eps<=y<=b+eps and min(abs(x-l),abs(x-r),abs(y-t),abs(y-b))<=eps
        attachment=route.get('paint_points')
        first=attachment[0] if attachment else route['sections'][0]['start']
        last=attachment[-1] if attachment else route['sections'][-1]['end']
        if not on_boundary(first,nodes[edge['source']],edge['source']) or not on_boundary(last,nodes[edge['target']],edge['target']):
            errors.append('L3 wrong endpoint '+edge['id'])
    def inside(a,b):
        return a['x']>=b['x']-.01 and a['y']>=b['y']-.01 and a['x']+a['width']<=b['x']+b['width']+.01 and a['y']+a['height']<=b['y']+b['height']+.01
    for group in diagram.get('groups',[]):
        painted=[e for e in trace if e['kind']=='group' and e['semantic_id']==group['id']]
        titles=[e for e in trace if e['kind']=='group-title' and e['semantic_id']==group['id']]
        if len(painted)!=1 or norm(' '.join(e['text'] for e in titles))!=norm(group['label']):errors.append('L2 missing group/title '+group['id']);continue
        frame=painted[0]['box']
        # Colored frames need a distance-from-white check, not a dark threshold.
        if not any(min(image.getpixel((xx,yy)))<245 for xx in range(max(0,int(frame['x'])-1),min(w,int(frame['x'])+2)) for yy in range(max(0,int(frame['y'])+2),min(h,int(frame['y']+frame['height'])-2))):errors.append('L2 unpainted group '+group['id'])
        for member in group['members']:
            if member not in nodes:errors.append('L3 unknown group member '+member);continue
            if not inside(nodes[member],nodes[group['id']]):errors.append('L3 group containment '+group['id']+'/'+member)
        if any(not inside(e['box'],frame) for e in titles):errors.append('L3 title outside group '+group['id'])
    for edge in diagram['edges']:
        if not edge.get('label'):continue
        labels=[e for e in trace if e['kind']=='edge-label' and e['semantic_id']==edge['id']]
        backgrounds=[e for e in trace if e['kind']=='edge-label-background' and e['semantic_id']==edge['id']]
        if norm(' '.join(e['text'] for e in labels))!=norm(edge['label']) or not backgrounds:errors.append('L2 missing edge label '+edge['id'])
        if backgrounds and any(not any(inside(e['box'],b['box']) for b in backgrounds) for e in labels):errors.append('L3 edge label overflow '+edge['id'])
    for event in trace:
        if event['kind'] not in ('group-title','edge-label'):continue
        b=event['box']
        if b['x']<0 or b['y']<0 or b['x']+b['width']>w or b['y']+b['height']>h:
            errors.append('L3 clipped annotation '+event['semantic_id']);continue
        if event['text'].strip() and not any(max(p)<190 for p in image.crop((max(0,int(b['x'])),max(0,int(b['y'])),min(w,math.ceil(b['x']+b['width']+1)),min(h,math.ceil(b['y']+b['height']+1)))).getdata()):errors.append('L2 unpainted annotation '+event['semantic_id'])
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
    for kind in ('node','text','edge','arrow','group','group-title','edge-label','edge-label-background'):
        if not any(e['kind']==kind for e in scene['trace']):continue
        bad=copy.deepcopy(scene);bad['trace']=[e for e in bad['trace'] if e['kind']!=kind]
        outcomes['missing_'+kind+'_rejected']=bool(check_scene(bad,png,case))
    bad=copy.deepcopy(scene);(bad['diagram']['nodes'] or bad['diagram']['groups'])[0]['label']='WRONG CONTENT'
    outcomes['wrong_content_rejected']=bool(check_scene(bad,png,case))
    bad=copy.deepcopy(scene);node=next(e for e in bad['trace'] if e['kind'] in ('node','group-title'));node['box']['x']=-20
    outcomes['clipping_rejected']=bool(check_scene(bad,png,case))
    if scene['diagram']['edges']:
        bad=copy.deepcopy(scene);bad['diagram']['edges'][0]['target']='__WRONG_ENDPOINT__'
        outcomes['wrong_relation_rejected']=bool(check_scene(bad,png,case))
        bad=copy.deepcopy(scene);arrow=next(e for e in bad['trace'] if e['kind']=='arrow');tip=arrow['points'][0]
        for p in arrow['points'][1:]:p['x']=2*tip['x']-p['x'];p['y']=2*tip['y']-p['y']
        outcomes['wrong_arrow_rejected']=bool(check_scene(bad,png,case))
    for key,field in [('shapes','shape'),('edgeLabels','label'),('groups','members')]:
        if key not in case:continue
        bad=copy.deepcopy(scene)
        if key=='shapes' and bad['diagram']['nodes']:bad['diagram']['nodes'][0]['shape']='WRONG'
        elif key=='edgeLabels' and bad['diagram']['edges']:bad['diagram']['edges'][0]['label']='WRONG'
        elif key=='groups' and bad['diagram']['groups']:bad['diagram']['groups'][0]['members']=[] if bad['diagram']['groups'][0]['members'] else ['WRONG']
        else:continue
        outcomes['wrong_'+key+'_rejected']=bool(check_scene(bad,png,case))
    return outcomes


def validate(args, diagnostics):
    fixture=json.loads(args.fixtures.read_text(encoding='utf-8'))
    cases=fixture['cases']
    report={'backend':args.backend,'cases':[],'functionalStatus':'NOT_EVALUATED'}
    static=fixture.get('scope')=='F01.4'
    rich=fixture.get('scope') in {'F01.3','F01.4'}
    for case in cases:
        entry={'id':case['id'],'errors':[]}
        try:
            result=render(case['text'],config=case.get('config'),backend=args.backend,resources=fixture_resources(case));scene=asdict(result);scene.pop('data')
            png=args.out/(case['id']+'.png');png.write_bytes(result.data)
            (args.out/(case['id']+'.json')).write_text(json.dumps(json_ready(scene),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            entry['pngSha256']=hashlib.sha256(result.data).hexdigest();entry['engine']=dict(result.backend)
            official=json.loads((args.oracle/(case['id']+'.json')).read_text(encoding='utf-8'))
            if static:
                from static_flowchart_checks import check_scene as static_check,controls as static_controls
                entry['errors']=static_check(scene,result.data,case,official,(args.oracle/(case['id']+'.png')).read_bytes())
                entry['controls']=static_controls(scene,result.data,case)
            elif rich:
                from rich_scene_checks import check_scene as rich_check,controls as rich_controls
                entry['errors']=rich_check(scene,result.data,case,official)
                entry['controls']=rich_controls(scene,result.data,case)
            else:
                entry['errors']=check_scene(scene,result.data,case)
                entry['controls']=controls(scene,result.data,case)
            if not static:
                if [(n['id'],norm(n['label'])) for n in official['nodes']]!=[(i,norm(t)) for i,t in case['nodes']]:entry['errors'].append('A semantic source disagreement')
                if [(e['source'],e['target']) for e in official['edges']]!=[tuple(e) for e in case['edges']]:entry['errors'].append('A edge source disagreement')
                official_diagram={'nodes':[{**n,'shape':n.get('type','square'),'parent_id':next((g['id'] for g in official.get('groups',[]) if n['id'] in g['members']),None)} for n in official['nodes']], 'edges':official['edges'], 'groups':[{**g,'parent_id':next((p['id'] for p in official.get('groups',[]) if g['id'] in p['members']),None)} for g in official.get('groups',[])]}
                entry['errors']+=['A '+e for e in semantic_errors(official_diagram,case)]
                if len(official.get('drawnGroups',[]))!=len(case.get('groups',[])):entry['errors'].append('A incomplete drawn groups')
                expected_labels=sum(bool(norm(t)) for t in case.get('visibleEdgeLabels',case.get('edgeLabels',[]))) if rich and 'visibleEdgeLabels' in case else sum(bool(e.get('label')) for e in official['edges'])
                if len(official.get('drawnEdgeLabels',[]))!=expected_labels:entry['errors'].append('A incomplete drawn edge labels')
                if len(official['drawnNodes'])!=len(case['nodes']) or len(official['drawnEdges'])!=len(case['edges']):entry['errors'].append('A incomplete drawn structure')
                if any(not e['markerEnd'] for e in official['drawnEdges']):entry['errors'].append('A missing arrow marker')
                for node in official['drawnNodes'] if not rich else []:
                    for css,key in [('fill','fill'),('stroke','stroke')]:
                        if ImageColor.getrgb(node[css])!=ImageColor.getrgb(scene['diagram']['config'][key]):
                            entry['errors'].append('L2 default style disagrees with A: '+css)
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
            parse(case['text'],config=case.get('config'))
            entry['error']='Python accepted invalid official input'
        except MermaidError as error:
            entry.update(status='PASS' if official['rejected'] and error.span is not None else 'FAIL',code=error.code,span=asdict(error.span) if error.span else None)
        report['negativeCases'].append(entry)
    report['renderErrorCases']=[]
    for case in fixture.get('renderErrorCases',[]):
        official=json.loads((args.oracle/(case['id']+'.render-error.json')).read_text(encoding='utf-8'))
        entry={'id':case['id'],'status':'FAIL','parsed':False}
        try:
            parse(case['text'],config=case.get('config'));entry['parsed']=True
            render(case['text'],config=case.get('config'),backend=args.backend)
            entry['error']='Unexpected render success'
        except MermaidError as error:
            accepted_native_parse=entry['parsed'] or case.get('allowNativeParseRejection',False)
            source_defect=official['renderRejected'] or case.get('expectedSourceBlank',False) and official.get('missingShape',False)
            entry.update(code=error.code,message=str(error),status='PASS' if accepted_native_parse and official['parsed'] and source_defect and error.code==case['code'] else 'FAIL')
        report['renderErrorCases'].append(entry)
    report['unsupportedCases']=[]
    for case in fixture.get('unsupportedCases',[]):
        official=json.loads((args.oracle/(case['id']+'.unsupported.json')).read_text(encoding='utf-8'))
        entry={'id':case['id'],'status':'FAIL'}
        try:
            promoted=case.get('promotedMath')
            result=render(case['text'],config=case.get('config'),backend=args.backend)
            if promoted:
                # Historical scope IDs stay in the denominator. Their current
                # capability is checked as mathematics, not silently dropped.
                image=Image.open(io.BytesIO(result.data)).convert('RGB')
                formulas=[event for event in result.trace if event.kind=='math']
                glyphs=[event for event in result.trace if event.kind=='math-glyph']
                errors=[]
                if not official['accepted']:errors.append('Source rejected promoted mathematical syntax')
                if sorted(event.text for event in formulas)!=sorted(promoted['formulas']):errors.append('Missing promoted formula')
                for glyph in promoted['glyphs']:
                    if not any(event.text==glyph for event in glyphs):errors.append('Missing promoted mathematical glyph '+glyph)
                if len({round(event.points[0].y,4) for event in glyphs if event.points})<2:errors.append('Promoted scripts flattened')
                for event in formulas:
                    b=event.box;region=image.crop((max(0,math.floor(b.x)),max(0,math.floor(b.y)),min(image.width,math.ceil(b.x+b.width)),min(image.height,math.ceil(b.y+b.height))))
                    if sum(min(pixel)<180 for pixel in region.getdata())<3:errors.append('Missing promoted actual formula pixels')
                (args.out/(case['id']+'.promoted.png')).write_bytes(result.data)
                entry.update(status='FAIL' if errors else 'PASS',scopeDisposition='implemented_by_math_module',errors=errors)
            else:entry['error']='Native implementation accepted deferred scope'
        except MermaidError as error:
            entry.update(code=error.code,message=str(error),span=asdict(error.span) if error.span else None,
                         status='PASS' if not case.get('promotedMath') and official['accepted'] and error.code in case['codes'] else 'FAIL')
        except Exception:entry['error']=traceback.format_exc()
        report['unsupportedCases'].append(entry)
    report['functionalStatus']='FAIL' if any(e['status']=='FAIL' for e in report['cases']+report['negativeCases']+report['renderErrorCases']+report['unsupportedCases']) else 'PASS'
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
    fixture=json.loads(args.fixtures.read_text(encoding='utf-8'))
    with Run(fixture.get('scope','F01.1'),'pixel-diagnostics',runs_dir=args.out/'logs') as diagnostics:
        diagnostics.input(args.fixtures)
        return validate(args,diagnostics)


if __name__=='__main__':
    raise SystemExit(main())
