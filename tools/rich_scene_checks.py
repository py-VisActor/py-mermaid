"""Source-intent, real-pixel and fault-control checks for F01.3 saved scenes.

The checker never calls the product label/style/layout helpers to derive an
expectation. Handwritten fixture intent, official computed styles and actual
PNG foreground are independent inputs.
"""
from __future__ import annotations

import copy
import colorsys
import io
import math
import re

from PIL import Image, ImageColor


def norm(value):
    return ' '.join(str(value or '').split())


def color(value):
    if not isinstance(value,str):return None
    if value in {'none','transparent'}:return (0,0,0,0)
    hsl=re.fullmatch(r'hsla?\(([^)]+)\)',value.strip(),re.I)
    if hsl:
        parts=re.split(r'[,\s/]+',hsl[1].strip())
        if len(parts) not in (3,4) or not all(v.endswith('%') for v in parts[1:3]):return None
        try:
            hue=float(parts[0].removesuffix('deg'))%360
            saturation=max(0,min(1,float(parts[1][:-1])/100));lightness=max(0,min(1,float(parts[2][:-1])/100))
            alpha=float(parts[3].rstrip('%'))/(100 if parts[3].endswith('%') else 1) if len(parts)==4 else 1
            if not all(math.isfinite(x) for x in (hue,saturation,lightness,alpha)):return None
            return (*tuple(round(v*255) for v in colorsys.hls_to_rgb(hue/360,lightness,saturation)),round(max(0,min(1,alpha))*255))
        except ValueError:return None
    match=re.fullmatch(r'rgba?\(([^)]+)\)',value.strip(),re.I)
    if match:
        parts=re.split(r'[,\s/]+',match[1].strip())
        rgb=tuple(round(float(v.rstrip('%'))*(2.55 if v.endswith('%') else 1)) for v in parts[:3])
        alpha=round(float(parts[3].rstrip('%'))*(2.55 if parts[3].endswith('%') else 255)) if len(parts)>3 else 255
        return (*rgb,alpha)
    try:
        result=ImageColor.getrgb(value)
        return (*result,255) if len(result)==3 else result
    except (ValueError,TypeError):return None


def same_color(a,b):
    left,right=color(a),color(b)
    return left is not None and right is not None and max(abs(x-y) for x,y in zip(left,right))<=2


def inside(inner,outer,epsilon=.51):
    return (inner['x']>=outer['x']-epsilon and inner['y']>=outer['y']-epsilon
            and inner['x']+inner['width']<=outer['x']+outer['width']+epsilon
            and inner['y']+inner['height']<=outer['y']+outer['height']+epsilon)


def _weight(value):
    if str(value) in {'bold','bolder'}:return 700
    if str(value) in {'normal','lighter','None'}:return 400
    try:return int(value)
    except (ValueError,TypeError):return 400


def _format_match(run,expected,official=False):
    if expected.get('text') and norm(expected['text']) not in norm(run.get('text')):return False
    aliases={'weight':'fontWeight' if official else 'font_weight',
             'style':'fontStyle' if official else 'font_style',
             'fontSize':'fontSize' if official else 'font_size',
             'color':'color','decoration':'decoration'}
    for key,field in aliases.items():
        if key not in expected:continue
        value=run.get(field)
        if key=='weight':
            if _weight(value)!=_weight(expected[key]):return False
        elif key=='color':
            if not same_color(value,expected[key]):return False
        elif key=='fontSize':
            try:
                if abs(float(str(value).removesuffix('px'))-float(expected[key]))>.1:return False
            except (ValueError,TypeError):return False
        elif key=='decoration':
            if expected[key] not in str(value):return False
        elif str(value)!=str(expected[key]):return False
    return True


def _foreground(image,box,paint,background,opacity=1):
    target,bg=color(paint),color(background)
    if target is None:return False
    if target[3]==0 or opacity==0:return True
    if bg is None:bg=(255,255,255,255)
    alpha=target[3]/255*opacity
    fg=tuple(round(target[i]*alpha+bg[i]*(1-alpha)) for i in range(3))
    if max(abs(fg[i]-bg[i]) for i in range(3))<12:return True
    x0=max(0,math.floor(box['x']));y0=max(0,math.floor(box['y']))
    x1=min(image.width,math.ceil(box['x']+box['width']+1));y1=min(image.height,math.ceil(box['y']+box['height']+1))
    if x1<=x0 or y1<=y0:return not box['width'] or not box['height']
    vector=tuple(fg[i]-bg[i] for i in range(3));length=sum(v*v for v in vector)
    for p in image.crop((x0,y0,x1,y1)).getdata():
        # A one-pixel stroke at a fractional coordinate can cover less than
        # half a pixel. Require paint along the expected color/background
        # blend, rather than requiring a mostly opaque core pixel.
        coverage=sum((p[i]-bg[i])*vector[i] for i in range(3))/length
        residual=sum((p[i]-bg[i]-coverage*vector[i])**2 for i in range(3))
        if .15<=coverage<=1.15 and residual<=max(12**2,length*.006):return True
    return False


def _text_matches(painted,visible):
    rows=[];previous=None
    for event in painted:
        baseline=event.get('points',[{}])[0].get('y') if event.get('points') else None
        if previous is not None and baseline is not None and previous[0] is not None and abs(baseline-previous[0])>max(2,.65*max(event.get('font_size') or 14,previous[1])):
            rows.append('')
        if not rows:rows.append('')
        rows[-1]+=event.get('text') or ''
        previous=(baseline,event.get('font_size') or 14)
    # A layout row break may be explicit or soft wrapping. Only that boundary
    # may consume whitespace; adjacent styled runs must retain exact content.
    pattern=r'\s*'.join(re.escape(norm(row)) for row in rows)
    return re.fullmatch(pattern,norm(visible)) is not None


def check_scene(scene,png,expected,official=None):
    errors=[];diagram=scene['diagram'];layout=scene['layout'];trace=scene['trace'];cfg=diagram['config']
    if [(n['id'],norm(n['label'])) for n in diagram['nodes']]!=[(i,norm(t)) for i,t in expected['nodes']]:errors.append('L1 nodes/labels/order')
    if [(e['source'],e['target']) for e in diagram['edges']]!=[tuple(e) for e in expected['edges']]:errors.append('L1 edge relations/order')
    if diagram['direction']!=expected['direction']:errors.append('L1 direction')
    if 'shapes' in expected and {n['id']:n['shape'] for n in diagram['nodes']}!={i:expected['shapes'].get(i,'square') for i,_ in expected['nodes']}:errors.append('L1 shapes')
    if 'edgeLabels' in expected and [e['label'] for e in diagram['edges']]!=expected['edgeLabels']:errors.append('L1 edge labels')
    for n in diagram['nodes']:
        if n['id'] in expected.get('labelKinds',{}) and n['label_kind']!=expected['labelKinds'][n['id']]:errors.append('L1 node label kind '+n['id'])
    if 'edgeLabelKinds' in expected and [e['label_kind'] for e in diagram['edges']]!=expected['edgeLabelKinds']:errors.append('L1 edge label kinds')
    for group in diagram['groups']:
        if group['id'] in expected.get('groupLabelKinds',{}) and group['label_kind']!=expected['groupLabelKinds'][group['id']]:errors.append('L1 group label kind '+group['id'])
    if 'groups' in expected:
        keys=('id','label','members','parent_id','direction')
        def canonical(groups):return [{k:list(g.get(k,[])) if k=='members' else g.get(k) for k in keys} for g in groups]
        if canonical(diagram['groups'])!=canonical(expected['groups']):errors.append('L1 group membership/direction')
        parents={m:g['id'] for g in expected['groups'] for m in g['members']}
        if any(n['parent_id']!=parents.get(n['id']) for n in diagram['nodes']):errors.append('L1 node parent')
    for key,value in expected.get('expectedConfig',{}).items():
        actual=cfg.get(key)
        if key in {'fill','stroke','edge_color','text_color','background','edge_label_background'}:
            if not same_color(actual,value):errors.append('L1 effective config '+key)
        elif actual!=value:errors.append('L1 effective config '+key)
    if 'diagramTitle' in expected and diagram['title']!=expected['diagramTitle']:errors.append('L1 diagram title')
    rgba=Image.open(io.BytesIO(png)).convert('RGBA')
    white=Image.new('RGBA',rgba.size,'white');image=Image.alpha_composite(white,rgba).convert('RGB')
    if image.size!=(scene['width'],scene['height']):errors.append('L2 encoded dimensions')
    viewport={'x':0,'y':0,'width':image.width,'height':image.height}
    background=color(expected.get('canvasBackground',cfg['background']))
    if background and background[3]==255:
        if any(max(abs(pixel[i]-background[i]) for i in range(3))>3 for pixel in
               (image.getpixel((0,0)),image.getpixel((image.width-1,0)))):
            errors.append('L2 canvas background')
    nodes={n['id']:n['box'] for n in layout['nodes']};groups={g['id']:g['box'] for g in layout['groups']}
    if set(nodes)!={n['id'] for n in diagram['nodes']} or set(groups)!={g['id'] for g in diagram['groups']}:errors.append('L2 placed identities')
    all_boxes={**nodes,**groups}
    def events(kind,identifier):return [e for e in trace if e['kind']==kind and e['semantic_id']==identifier]
    for kind,items in [('node',diagram['nodes']),('group',diagram['groups'])]:
        for item in items:
            painted=events(kind,item['id'])
            if len(painted)!=1:errors.append('L2 missing '+kind+' '+item['id']);continue
            event=painted[0];box=event['box']
            if not inside(box,viewport):errors.append('L3 clipped '+kind+' '+item['id'])
            # Search a narrow border band; text/fill cannot stand in for outline.
            stroke=event.get('stroke') or (cfg['stroke'] if kind=='node' else cfg['group_borders'][0])
            gradient=stroke.startswith('linear-gradient(')
            if gradient:
                stroke=dict(cfg.get('theme_variables',())).get('gradientStart')
            if color(stroke) and color(stroke)[3] and event.get('opacity',1)>0:
                band={'x':box['x']-1,'y':box['y']+box['height']/2-2,'width':max(4,min(box['width']/2,box['height']/2)+2),'height':4}
                if not _foreground(image,band,stroke,event.get('fill') or cfg['fill']):errors.append('L2 unpainted outline '+item['id'])
            fill=event.get('fill') or cfg['fill']
            interior={'x':box['x']+box['width']/4,'y':box['y']+box['height']/4,
                      'width':box['width']/2,'height':box['height']/2}
            if color(fill) and not _foreground(image,interior,fill,cfg['background'],event.get('opacity',1)):
                errors.append('L2 unpainted fill '+item['id'])
    def text_check(kind,identifier,visible,background,formats=()):
        painted=events(kind,identifier)
        if not _text_matches(painted,visible):errors.append('L2 visible text '+kind+'/'+identifier)
        for e in painted:
            box=e.get('box')
            if box is None or not inside(box,viewport):errors.append('L3 clipped text '+kind+'/'+identifier);continue
            if e.get('text','').strip() and not _foreground(image,box,e.get('color') or cfg['text_color'],background,e.get('opacity',1)):
                errors.append('L2 unpainted glyph '+kind+'/'+identifier)
        for requirement in formats:
            if not any(_format_match(e,requirement) for e in painted):errors.append('L2 wrong/missing format '+kind+'/'+identifier+' '+str(requirement))
        return painted
    for node in diagram['nodes']:
        identifier=node['id'];paint=events('node',identifier)
        visible=expected.get('visibleLabels',{}).get(identifier,node['label'])
        texts=text_check('text',identifier,visible,paint[0].get('fill') or cfg['fill'] if paint else cfg['fill'],expected.get('formats',{}).get(identifier,()))
        if paint and any(not inside(t['box'],paint[0]['box']) for t in texts if t.get('box')):errors.append('L3 text outside node '+identifier)
    for index,edge in enumerate(diagram['edges']):
        lines,arrows=events('edge',edge['id']),events('arrow',edge['id'])
        if not lines or len(arrows)!=1:errors.append('L2 missing edge/arrow '+edge['id'])
        if edge['source'] not in all_boxes or edge['target'] not in all_boxes:errors.append('L3 unknown endpoint '+edge['id'])
        for line in lines:
            for a,b in zip(line['points'],line['points'][1:]):
                if math.hypot(a['x']-b['x'],a['y']-b['y'])<4:continue
                mx,my=(a['x']+b['x'])/2,(a['y']+b['y'])/2
                if any(t['kind']=='edge-label-background' and inside({'x':mx,'y':my,'width':0,'height':0},t['box'],2) for t in trace):continue
                if not _foreground(image,{'x':mx-2,'y':my-2,'width':4,'height':4},line.get('stroke') or cfg['edge_color'],cfg['background']):errors.append('L2 unpainted edge '+edge['id'])
        if arrows:
            pts=arrows[0]['points'];x=sum(p['x'] for p in pts)/3;y=sum(p['y'] for p in pts)/3
            if not _foreground(image,{'x':x-2,'y':y-2,'width':4,'height':4},arrows[0].get('fill') or cfg['edge_color'],cfg['background']):errors.append('L2 unpainted arrow '+edge['id'])
            if lines and len(lines[-1]['points'])>1:
                points=lines[-1]['points'];end=points[-1];prior=next((p for p in reversed(points[:-1]) if p!=end),None)
                if prior:
                    tip=pts[0];base={'x':(pts[1]['x']+pts[2]['x'])/2,'y':(pts[1]['y']+pts[2]['y'])/2}
                    if (tip['x']-base['x'])*(end['x']-prior['x'])+(tip['y']-base['y'])*(end['y']-prior['y'])<=0:errors.append('L3 reversed arrow '+edge['id'])
        if edge['label']:
            backgrounds=events('edge-label-background',edge['id'])
            if not backgrounds:errors.append('L2 missing edge label background '+edge['id'])
            visible=expected.get('visibleEdgeLabels',[e['label'] for e in diagram['edges']])[index]
            formats=expected.get('edgeFormats',[[] for _ in diagram['edges']])[index]
            texts=text_check('edge-label',edge['id'],visible,cfg['edge_label_background'],formats)
            if backgrounds and any(not any(inside(t['box'],b['box']) for b in backgrounds) for t in texts if t.get('box')):errors.append('L3 edge text outside background '+edge['id'])
    for group in diagram['groups']:
        identifier=group['id'];paint=events('group',identifier)
        visible=expected.get('visibleGroupLabels',{}).get(identifier,group['label'])
        text_check('group-title',identifier,visible,paint[0].get('fill') or cfg['background'] if paint else cfg['background'],expected.get('groupFormats',{}).get(identifier,()))
        if identifier in groups:
            for member in group['members']:
                if member not in all_boxes or not inside(all_boxes[member],groups[identifier]):errors.append('L3 group containment '+identifier)
    title=expected.get('visibleDiagramTitle',expected.get('diagramTitle',diagram.get('title','')))
    if title:
        text_check('diagram-title','',title,cfg['background'])
        if layout.get('title_box') is None:errors.append('L3 title placement missing')
    elif 'visibleDiagramTitle' in expected:
        if events('diagram-title','') or layout.get('title_box') is not None:errors.append('L2 hidden title painted or placed')
    if official is not None:
        if [(n['id'],norm(n['label'])) for n in official['nodes']]!=[(i,norm(t)) for i,t in expected['nodes']]:errors.append('A source node disagreement')
        if [(e['source'],e['target']) for e in official['edges']]!=[tuple(e) for e in expected['edges']]:errors.append('A source relationship disagreement')
        if len(official['drawnNodes'])!=len(diagram['nodes']) or len(official['drawnEdges'])!=len(diagram['edges']) or len(official['drawnGroups'])!=len(diagram['groups']):errors.append('A drawn denominator disagreement')
        for node in diagram['nodes']:
            drawn=next((n for n in official['drawnNodes'] if n.get('id')==node['id']),None)
            if drawn is None:errors.append('A missing drawn node '+node['id']);continue
            if norm(drawn['visibleLabel']['visible'])!=norm(expected.get('visibleLabels',{}).get(node['id'],node['label'])):errors.append('A visible text disagreement '+node['id'])
            for requirement in expected.get('formats',{}).get(node['id'],()):
                if not any(_format_match(r,requirement,True) for r in drawn['visibleLabel']['runs']):errors.append('A format disagreement '+node['id']+' '+str(requirement))
            painted=events('node',node['id'])
            if painted:
                for field in ('fill','stroke'):
                    if drawn[field].startswith('url('):continue
                    native=painted[0].get(field) or cfg[field]
                    if not same_color(native,drawn[field]):errors.append('L2 paint disagrees with A '+node['id']+'/'+field)
                if drawn['stroke'].startswith('url('):
                    if not str(painted[0].get('stroke','')).startswith('linear-gradient('):errors.append('L2 missing gradient '+node['id'])
                    variables=dict(cfg.get('theme_variables',()))
                    stops=official.get('gradients',[{}])[0].get('stops',[]) if official.get('gradients') else []
                    if len(stops)<2 or not same_color(variables.get('gradientStart'),stops[0]['color']) or not same_color(variables.get('gradientStop'),stops[-1]['color']):errors.append('L2 gradient colors disagree with A '+node['id'])
        for group in diagram['groups']:
            drawn=next((g for g in official['drawnGroups'] if g['id']==group['id'] or g['id'].endswith('-'+group['id'])),None)
            if drawn and norm(drawn['visibleLabel']['visible'])!=norm(expected.get('visibleGroupLabels',{}).get(group['id'],group['label'])):errors.append('A group visible disagreement '+group['id'])
            for requirement in expected.get('groupFormats',{}).get(group['id'],()):
                if not drawn or not any(_format_match(r,requirement,True) for r in drawn['visibleLabel']['runs']):errors.append('A group format disagreement '+group['id'])
        labels=official['drawnEdgeLabels'];label_index=0
        for index,edge in enumerate(diagram['edges']):
            if not edge['label']:continue
            visible=expected.get('visibleEdgeLabels',[e['label'] for e in diagram['edges']])[index]
            if not norm(visible):continue
            drawn=labels[label_index] if label_index<len(labels) else None;label_index+=1
            if drawn is None or norm(drawn['visibleLabel']['visible'])!=norm(visible):errors.append('A edge visible disagreement '+edge['id'])
            for requirement in expected.get('edgeFormats',[[] for _ in diagram['edges']])[index]:
                if drawn is None or not any(_format_match(r,requirement,True) for r in drawn['visibleLabel']['runs']):errors.append('A edge format disagreement '+edge['id'])
        if title and (official.get('title') is None or norm(official['title']['visible'])!=norm(title)):errors.append('A title disagreement')
        if not title and 'visibleDiagramTitle' in expected and official.get('title') and norm(official['title']['visible']):errors.append('A hidden title disagreement')
    return errors


def controls(scene,png,expected):
    result={}
    white=Image.new('RGB',(scene['width'],scene['height']),'white');buf=io.BytesIO();white.save(buf,format='PNG')
    result['white_noop_rejected']=bool(check_scene(scene,buf.getvalue(),expected))
    slight=Image.open(io.BytesIO(png)).convert('RGBA').point(lambda n:min(255,n+1));buf=io.BytesIO();slight.save(buf,format='PNG')
    result['normal_channel_variation_accepted']=not check_scene(scene,buf.getvalue(),expected)
    for kind in ('node','text','edge','arrow','group','group-title','edge-label','edge-label-background','diagram-title'):
        if not any(e['kind']==kind for e in scene['trace']):continue
        if kind in {'text','group-title','edge-label','diagram-title'} and not any(e['kind']==kind and norm(e.get('text')) for e in scene['trace']):continue
        bad=copy.deepcopy(scene);bad['trace']=[e for e in bad['trace'] if e['kind']!=kind]
        result['missing_'+kind+'_rejected']=bool(check_scene(bad,png,expected))
    bad=copy.deepcopy(scene);(bad['diagram']['nodes'] or bad['diagram']['groups'])[0]['label']='WRONG CONTENT'
    result['wrong_content_rejected']=bool(check_scene(bad,png,expected))
    bad=copy.deepcopy(scene);event=next(e for e in bad['trace'] if e.get('box') and e['kind'] in {'text','group-title','diagram-title'});event['box']['x']=-100
    result['clipping_rejected']=bool(check_scene(bad,png,expected))
    if expected.get('formats'):
        bad=copy.deepcopy(scene)
        for event in bad['trace']:
            if event['kind']=='text':event.update(font_weight='WRONG',font_style='WRONG',color='#ff00ff',font_size=999)
        result['wrong_format_rejected']=bool(check_scene(bad,png,expected))
    if scene['diagram']['edges']:
        bad=copy.deepcopy(scene);bad['diagram']['edges'][0]['target']='__WRONG__'
        result['wrong_relation_rejected']=bool(check_scene(bad,png,expected))
        bad=copy.deepcopy(scene);arrow=next(e for e in bad['trace'] if e['kind']=='arrow');tip=arrow['points'][0]
        for p in arrow['points'][1:]:p['x']=2*tip['x']-p['x'];p['y']=2*tip['y']-p['y']
        result['wrong_arrow_rejected']=bool(check_scene(bad,png,expected))
    return result
