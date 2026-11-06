"""Independent F01.4 semantic, static paint and real PNG evidence checks.

No product geometry/style/parser helpers are imported. Source-projected official
data and handwritten fixture intent supply expectations; pixels prove paint.
Exact paths and dimensions across browser/Canvas are diagnostic, not equality.
"""
from __future__ import annotations
from collections import Counter
import copy
import io
import math
from PIL import Image
from rich_scene_checks import norm, inside, color, same_color, _foreground, _text_matches, _format_match


def _marker(value):
    return str(value or 'none').removeprefix('arrow_')


def check_scene(scene, png, expected, official=None, official_png=None):
    errors=[];diagram=scene['diagram'];layout=scene['layout'];trace=scene['trace'];cfg=diagram['config']
    nodes=diagram['nodes'];edges=diagram['edges'];groups=diagram['groups']
    if [(n['id'],norm(n['label'])) for n in nodes]!=[(i,norm(t)) for i,t in expected['nodes']]:errors.append('L1 nodes/labels/order')
    if [(e['source'],e['target']) for e in edges]!=[tuple(e) for e in expected['edges']]:errors.append('L1 edge relations/order')
    if diagram['direction']!=expected['direction']:errors.append('L1 direction')
    if 'shapes' in expected and {n['id']:n['shape'] for n in nodes}!={i:expected['shapes'].get(i,'square') for i,_ in expected['nodes']}:errors.append('L1 shapes')
    if 'edgeLabels' in expected and [e['label'] for e in edges]!=expected['edgeLabels']:errors.append('L1 edge labels')
    if 'groups' in expected:
        keys=('id','label','members','parent_id','direction')
        def canonical(items):return [{k:list(item.get(k,[])) if k=='members' else item.get(k) for k in keys} for item in items]
        if canonical(groups)!=canonical(expected['groups']):errors.append('L1 groups')
    image=Image.open(io.BytesIO(png)).convert('RGBA')
    image=Image.alpha_composite(Image.new('RGBA',image.size,'white'),image).convert('RGB')
    if image.size!=(scene['width'],scene['height']):errors.append('L2 encoded dimensions')
    if expected.get('expectedEmptyRendering') and image.size!=tuple(expected.get('expectedEmptySize',[16,16])):errors.append('L2 empty source viewport')
    viewport={'x':0,'y':0,'width':image.width,'height':image.height}
    measured={n['id']:n for n in scene['measured']}
    placed={n['id']:n.get('paint_box') or n['box'] for n in layout['nodes']+layout['groups']}
    if set(measured)!={n['id'] for n in nodes}:errors.append('L2 measured identities')
    if set(placed)!={n['id'] for n in nodes+groups}:errors.append('L2 placed identities')
    def events(kind,identifier):return [e for e in trace if e['kind']==kind and e['semantic_id']==identifier]
    def text(kind,identifier,visible,background,formats=()):
        runs=events(kind,identifier)
        if not _text_matches(runs,visible):errors.append('L2 text '+kind+'/'+identifier)
        for run in runs:
            box=run.get('box')
            if box is None or not inside(box,viewport):errors.append('L3 clipped text '+identifier);continue
            if norm(run.get('text')) and not _foreground(image,box,run.get('color') or cfg['text_color'],background,run.get('opacity',1)):errors.append('L2 glyph pixels '+identifier)
        for requirement in formats:
            if not any(_format_match(run,requirement) for run in runs):errors.append('L2 text format '+identifier+'/'+str(requirement))
        return runs
    hidden=set(expected.get('hiddenNodes',[]))
    for item in nodes+groups:
        identifier=item['id'];kind='node' if item in nodes else 'group';paint=events(kind,identifier)
        if identifier in hidden:
            if paint:errors.append('L2 hidden node painted '+identifier)
            continue
        if len(paint)!=1:errors.append('L2 missing '+kind+' '+identifier);continue
        event=paint[0];box=event['box']
        if not inside(box,viewport):errors.append('L3 clipped '+kind+' '+identifier)
        size=measured.get(identifier,{})
        # Distinguish virtual asset frames and open strokes from ordinary fills.
        assets=size.get('assets',[])
        stroke=event.get('stroke') or cfg['stroke']
        if str(stroke).startswith('linear-gradient('):stroke=dict(cfg.get('theme_variables',())).get('gradientStart')
        if not assets and event.get('stroke_width',1)>0 and color(stroke) and color(stroke)[3] and event.get('opacity',1)>0:
            if not _foreground(image,box,stroke,event.get('fill') or cfg['background'],event.get('opacity',1)):errors.append('L2 outline pixels '+identifier)
        fill=event.get('fill')
        if not assets and color(fill) and color(fill)[3] and not _foreground(image,box,fill,cfg['background'],event.get('opacity',1)):errors.append('L2 fill pixels '+identifier)
        for asset in events('node-asset',identifier):
            if not asset.get('resource_id') or not inside(asset['box'],viewport):errors.append('L2 invalid asset '+identifier)
            region=image.crop((max(0,int(asset['box']['x'])),max(0,int(asset['box']['y'])),min(image.width,math.ceil(asset['box']['x']+asset['box']['width'])),min(image.height,math.ceil(asset['box']['y']+asset['box']['height']))))
            if region.width and region.height and not any(min(pixel)<245 for pixel in region.getdata()):errors.append('L2 blank asset '+identifier)
        if len(events('node-asset',identifier))!=len(assets):errors.append('L2 asset denominator '+identifier)
        if kind=='node':
            visible=expected.get('visibleLabels',{}).get(identifier,item['label'])
            runs=text('text',identifier,visible,event.get('fill') or cfg['background'],expected.get('formats',{}).get(identifier,()))
            if any(not inside(run['box'],box,1) for run in runs if run.get('box')):errors.append('L3 text outside node '+identifier)
            inline=events('inline-asset',identifier)
            if len(inline)!=sum(bool(run.get('asset_id')) for run in size.get('runs',[])):errors.append('L2 inline asset denominator '+identifier)
            for asset in inline:
                if not asset.get('resource_id') or not inside(asset['box'],viewport):errors.append('L3 inline asset bounds '+identifier)
        else:
            text('group-title',identifier,expected.get('visibleGroupLabels',{}).get(identifier,item['label']),event.get('fill') or cfg['background'],expected.get('groupFormats',{}).get(identifier,()))
            for member in item['members']:
                defect=expected.get('knownSourceDefect',{})
                radial=defect.get('id')=='elk-radial-container-frame' and identifier in defect.get('groups',[])
                if member not in placed or not radial and not inside(placed[member],placed[identifier]):errors.append('L3 group containment '+identifier+'/'+member)
            if expected.get('knownSourceDefect',{}).get('id')=='elk-radial-container-frame' and identifier in expected['knownSourceDefect'].get('groups',[]):
                if not any(member in placed and not inside(placed[member],placed[identifier]) for member in item['members']):errors.append('L3 source radial defect evidence changed '+identifier)
    for index,edge in enumerate(edges):
        identifier=edge['id'];route=next((e for e in layout['edges'] if e['id']==identifier),None)
        lines=events('edge',identifier);markers=events('arrow',identifier)
        if route is None:errors.append('L2 missing route '+identifier);continue
        degenerate=len(route.get('paint_points',[]))<=1 and not route.get('path')
        invisible=edge.get('stroke')=='invisible' or identifier in expected.get('hiddenEdges',[])
        if invisible or degenerate:
            if lines or markers:errors.append('L2 source-invisible edge painted '+identifier)
        else:
            if len(lines)!=1 or not lines[0].get('path'):errors.append('L2 missing real edge path '+identifier)
            wanted=Counter(kind for kind in (edge.get('marker_start','none'),edge.get('marker_end','point')) if kind!='none')
            if Counter(marker.get('marker') for marker in markers)!=wanted:errors.append('L2 marker denominator/kind '+identifier)
            for marker in markers:
                if not marker.get('path') or not marker.get('box') or not inside(marker['box'],viewport):errors.append('L3 marker path/bounds '+identifier);continue
                paint=marker.get('stroke') if marker.get('fill')=='none' else marker.get('fill')
                if not _foreground(image,marker['box'],paint,cfg['background'],marker.get('opacity',1)):errors.append('L2 marker pixels '+identifier)
            for line in lines:
                if not line.get('stroke_width') or not line.get('opacity',1):continue
                for a,b in zip(line['points'],line['points'][1:]):
                    length=math.hypot(a['x']-b['x'],a['y']-b['y'])
                    if length<32:continue  # Source marker clearance can cover short terminal runs.
                    probes=[{'x':a['x']+(b['x']-a['x'])*t-3,'y':a['y']+(b['y']-a['y'])*t-3,'width':6,'height':6} for t in (.3,.4,.5,.6,.7)]
                    # Nodes paint after edges in both implementations. A
                    # nonrouting algorithm may put a third node across a line.
                    probes=[probe for probe in probes if not any(inside(probe,event['box'],2) for event in trace if event['kind']=='node')]
                    if not probes:continue
                    if any(any(inside(probe,bg['box'],4) for bg in events('edge-label-background',identifier)) for probe in probes):continue
                    if not any(_foreground(image,probe,line.get('stroke'),cfg['background'],line.get('opacity',1)) for probe in probes):errors.append('L2 edge pixels '+identifier)
        if edge['source'] not in placed or edge['target'] not in placed:errors.append('L3 unknown edge endpoint '+identifier)
        if edge.get('label'):
            visible=expected.get('visibleEdgeLabels',expected.get('edgeLabels',[e['label'] for e in edges]))[index]
            text('edge-label',identifier,visible,cfg['edge_label_background'],expected.get('edgeFormats',[[] for _ in edges])[index])
            if norm(visible) and not events('edge-label-background',identifier):errors.append('L2 missing edge label background '+identifier)
    title=expected.get('visibleDiagramTitle',expected.get('diagramTitle',diagram.get('title','')))
    if title:text('diagram-title','',title,cfg['background'])
    resources=expected.get('resourceAssertions',{})
    if 'images' in resources and sum(event['kind'] in {'node-asset','inline-asset'} for event in trace)!=resources['images']:
        errors.append('L2 expected resource denominator')
    for paint in resources.get('colors',[]):
        wanted=color(paint)
        if wanted and not any(max(abs(pixel[i]-wanted[i]) for i in range(3))<12 for pixel in image.getdata()):errors.append('L2 expected resource pixel color '+paint)
    for probe in expected.get('fillProbes',[]):
        painted=events('node',probe['node'])
        if not painted:errors.append('L2 fill probe missing node '+probe['node']);continue
        box=painted[0]['box'];x=round(box['x']+box['width']*probe['x']);y=round(box['y']+box['height']*probe['y'])
        wanted=color(probe['color'])
        if not (0<=x<image.width and 0<=y<image.height) or wanted is None or max(abs(image.getpixel((x,y))[i]-wanted[i]) for i in range(3))>12:errors.append('L2 missing node fill region '+probe['node'])
        if official is not None and official_png is not None:
            source=next((node for node in official['drawnNodes'] if node.get('id')==probe['node']),None)
            if source is None:errors.append('A fill probe missing node '+probe['node'])
            else:
                source_image=Image.open(io.BytesIO(official_png)).convert('RGB');source_box=source['box']
                sx=round(source_box['x']+source_box['width']*probe['x']);sy=round(source_box['y']+source_box['height']*probe['y'])
                if not (0<=sx<source_image.width and 0<=sy<source_image.height) or wanted is None or max(abs(source_image.getpixel((sx,sy))[i]-wanted[i]) for i in range(3))>12:errors.append('A fill probe disagrees with source '+probe['node'])
    if official is not None:
        projection=official.get('sourceProjection') or {'nodes':official['nodes'],'edges':official['edges'],'groups':official['groups']}
        if [(n['id'],norm(n['label'])) for n in projection['nodes']]!=[(i,norm(t)) for i,t in expected['nodes']]:errors.append('A projected nodes disagreement')
        if [(e['source'],e['target']) for e in projection['edges']]!=[tuple(e) for e in expected['edges']]:errors.append('A projected edges disagreement')
        if 'oracleShapes' in expected:
            if {n['id']:n.get('shape') for n in projection['nodes']}!=expected['oracleShapes']:errors.append('A source shape disagreement')
        # Public Python model retains TD spelling; the fixed FlowDB stores TB.
        canonical_direction=lambda value:'TB' if value in {'TD','BR'} else value
        if canonical_direction(official['direction'])!=canonical_direction(expected['direction']):errors.append('A direction disagreement')
        if len(official['drawnNodes'])!=len(nodes) or len(official['drawnGroups'])!=len(groups):errors.append('A drawn node/group denominator')
        for item in nodes:
            identifier=item['id'];drawn=next((n for n in official['drawnNodes'] if n.get('id')==identifier),None)
            if drawn is None:errors.append('A missing node '+identifier);continue
            visible=expected.get('visibleLabels',{}).get(identifier,item['label'])
            if norm(drawn['visibleLabel']['visible'])!=norm(visible):errors.append('A visible label disagreement '+identifier)
            for requirement in expected.get('formats',{}).get(identifier,()):
                if not any(_format_match(run,requirement,True) for run in drawn['visibleLabel']['runs']):errors.append('A label format disagreement '+identifier)
            native=events('node',identifier)
            if native and not measured[identifier].get('assets'):
                for field in ('fill','stroke'):
                    # RoughJS open-stroke braces do not gain a filled label
                    # body from a computed CSS fill on their stroke subpaths.
                    if field=='fill' and item['shape'] in {'curlyBraceLeft','curlyBraceRight','curlyBraces'}:continue
                    source=drawn.get(field)
                    if source and source!='none' and not source.startswith('url(') and not same_color(native[0].get(field),source):errors.append('L2 source paint disagreement '+identifier+'/'+field)
        for edge,source in zip(edges,projection['edges']):
            if (edge.get('marker_start'),edge.get('marker_end'))!=(_marker(source.get('markerStart')),_marker(source.get('markerEnd'))):errors.append('A marker semantics '+edge['id'])
            drawn=next((entry for entry in official['drawnEdges'] if entry['id']==source['id']),None)
            native=events('edge',edge['id'])
            if drawn and native and drawn.get('stroke') and not str(drawn['stroke']).startswith('url('):
                if not same_color(native[0].get('stroke'),drawn['stroke']):errors.append('L2 source edge color '+edge['id'])
                if drawn.get('strokeWidth') and abs(float(str(drawn['strokeWidth']).removesuffix('px'))-native[0]['stroke_width'])>.01:errors.append('L2 source edge width '+edge['id'])
    return list(dict.fromkeys(errors))


def controls(scene,png,expected):
    """Mutation controls remain separate from the actual run's functional status."""
    result={}
    white=Image.new('RGB',(scene['width'],scene['height']),'white');buf=io.BytesIO();white.save(buf,format='PNG')
    if not expected.get('expectedEmptyRendering'):
        result['white_noop_rejected']=bool(check_scene(scene,buf.getvalue(),expected))
    else:
        result['empty_source_has_no_invented_ink']=not scene['diagram']['nodes'] and not scene['diagram']['groups'] and not any(event['kind']!='viewport' for event in scene['trace'])
    altered=Image.open(io.BytesIO(png)).convert('RGBA');r,g,b,a=altered.split()
    altered=Image.merge('RGBA',(r.point(lambda v:min(255,v+1)),g.point(lambda v:min(255,v+1)),b.point(lambda v:min(255,v+1)),a))
    buf=io.BytesIO();altered.save(buf,format='PNG')
    result['normal_channel_variation_accepted']=not check_scene(scene,buf.getvalue(),expected)
    for kind in ('node','text','edge','arrow','group','group-title','edge-label','node-asset','inline-asset'):
        if not any(e['kind']==kind for e in scene['trace']):continue
        if kind in {'text','group-title','edge-label'} and not any(e['kind']==kind and norm(e.get('text')) for e in scene['trace']):continue
        bad=copy.deepcopy(scene);bad['trace']=[e for e in bad['trace'] if e['kind']!=kind]
        result['missing_'+kind+'_rejected']=bool(check_scene(bad,png,expected))
    if scene['diagram']['nodes'] or scene['diagram']['groups']:
        bad=copy.deepcopy(scene);(bad['diagram']['nodes'] or bad['diagram']['groups'])[0]['label']='WRONG CONTENT'
        result['wrong_content_rejected']=bool(check_scene(bad,png,expected))
    boxed=next((e for e in scene['trace'] if e.get('box') and e['kind'] in {'node','group','text'}),None)
    if boxed:
        bad=copy.deepcopy(scene);index=scene['trace'].index(boxed);bad['trace'][index]['box']['x']=-1000
        result['clipping_rejected']=bool(check_scene(bad,png,expected))
    if scene['diagram']['edges']:
        bad=copy.deepcopy(scene);bad['diagram']['edges'][0]['target']='__WRONG__'
        result['wrong_relation_rejected']=bool(check_scene(bad,png,expected))
    markers=[e for e in scene['trace'] if e['kind']=='arrow']
    if markers:
        bad=copy.deepcopy(scene)
        for event in bad['trace']:
            if event['kind']=='arrow':event['marker']='wrong';event['path']=''
        result['wrong_marker_rejected']=bool(check_scene(bad,png,expected))
    return result
