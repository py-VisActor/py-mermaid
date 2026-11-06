"""Mindmap Jison/DB semantics and the measured native layout adapters."""
from __future__ import annotations
from dataclasses import dataclass,replace
import math
import re
from ...runtime.common import make_diagram,error,config_dict,sanitize_text
from ..modeling._support import label_style,number,clip_endpoint


@dataclass(frozen=True)
class MindNode:
    id:str
    node_id:str
    label:str
    level:int
    parent:str|None
    shape:str
    classes:tuple[str,...]=()
    icon:str|None=None
    section:int|None=None
    depth:int=0
    padding:float=10.


@dataclass(frozen=True)
class MindmapModel:
    nodes:tuple[MindNode,...]


def _records(text):
    # NODE string states, unlike ordinary IDs, permit literal newlines.
    offset=0;start=0;quote=False;markdown=False;buffer=''
    for line in text.splitlines(keepends=True):
        if not buffer:start=offset
        buffer+=line;offset+=len(line)
        # Delimiters are lexical; quoted labels have no backslash escape rule.
        quote=False;markdown=False;i=0
        while i<len(buffer):
            if not quote and buffer.startswith('"`',i):quote=True;markdown=True;i+=2;continue
            if quote and markdown and buffer.startswith('`"',i):quote=False;markdown=False;i+=2;continue
            if not markdown and buffer[i]=='"':quote=not quote
            i+=1
        if not quote:yield start,buffer.rstrip('\r\n');buffer=''
    if buffer:yield start,buffer


def parse(document,config):
    records=list(_records(document.cleaned));header=False;nodes=[];base=0;conf=config.get('mindmap') or {};pad=number(conf.get('padding'),10)
    for offset,line in records:
        if not line.strip() or line.lstrip().startswith('%%'):continue
        if not header:
            match=re.match(r'\s*mindmap\b',line,re.I)
            if not match:raise error(document,offset,'Expected mindmap header')
            header=True;line=line[match.end():];offset+=match.end()
            if not line.strip():continue
        indent=len(line)-len(line.lstrip());body=line[indent:]
        if body.startswith(':::') or body.startswith('::icon('):
            if not nodes:raise error(document,offset,'Mindmap decoration has no node','UNKNOWN_REFERENCE')
            if body.startswith(':::'):nodes[-1]=replace(nodes[-1],classes=(sanitize_text(body[3:],config),))
            else:
                match=re.fullmatch(r'::icon\(([^)]+)\)\s*',body)
                if not match:raise error(document,offset,'Invalid mindmap icon decoration')
                nodes[-1]=replace(nodes[-1],icon=sanitize_text(match[1],config))
            continue
        open_match=re.search(r'\(-|\)\)|\(\(|\{\{|[\[(\)]',body)
        if body.startswith('-)'):open_match=re.match(r'-\)',body)
        shape='default';node_id=label=body
        if open_match:
            opener=open_match[0];node_id=body[:open_match.start()];tail=body[open_match.end():]
            if tail.startswith('"`'):
                end=tail.find('`"',2)
                if end<0:raise error(document,offset+indent+open_match.end(),'Unterminated markdown node label')
                label=tail[2:end];closing=tail[end+2:]
            elif tail.startswith('"'):
                end=tail.find('"',1)
                if end<0:raise error(document,offset+indent+open_match.end(),'Unterminated node label')
                label=tail[1:end];closing=tail[end+1:]
            else:
                match=re.fullmatch(r'([^\)\]\(\}]+)(\)\)|\}\}|\(-|-\)|\(\(|[\])\(])\s*',tail)
                if not match:raise error(document,offset+indent,'Unterminated mindmap node')
                label=match[1];closing=match[2]
            if not re.fullmatch(r'(?:\)\)|\}\}|\(-|-\)|\(\(|[\])\(])\s*',closing):raise error(document,offset+indent,'Invalid mindmap closing delimiter')
            if not label:raise error(document,offset+indent,'Empty mindmap node description')
            shape={'[':'rect','(':'rounded' if closing.strip()==')' else 'cloud','((':'circle',')':'cloud','))':'bang','{{':'hexagon'}.get(opener,'default')
            if not node_id:node_id=label
        elif any(c in body for c in '{}]'):raise error(document,offset+indent,'Invalid mindmap node ID')
        if not nodes:base=indent;level=0;parent=None;depth=0;section=None
        else:
            level=indent-base;parent_node=next((n for n in reversed(nodes) if n.level<level),None)
            if parent_node is None:raise error(document,offset+indent,'There can be only one root','MULTIPLE_ROOTS')
            parent=parent_node.id;depth=parent_node.depth+1
            section=sum(n.parent==parent for n in nodes)%11 if parent_node.level==0 else parent_node.section
            if conf.get('colorBy')=='depth':section=(depth-1)%11
        nodes.append(MindNode(str(len(nodes)),sanitize_text(node_id,config),sanitize_text(label,config),level,parent,shape,section=section,depth=depth,padding=pad*(2 if shape in ('rounded','rect','hexagon') else 1)))
    if not header or not nodes:raise error(document,len(document.cleaned),'Mindmap requires a root')
    return make_diagram('mindmap',document,config,MindmapModel(tuple(nodes)))


def _style(p,config,node):
    from ...rendering.styles.flowchart import apply_declarations
    tv=config.get('themeVariables') or {};name=config.get('theme','');neo=config.get('look')=='neo';root=node.parent is None;i=0 if root else (node.section or 0)+1
    fill=tv.get('git0','#ececff') if root else tv.get('cScale'+str(i),'#ececff');stroke='none';color=tv.get('gitBranchLabel0','#333') if root else tv.get('cScaleLabel'+str(i),'#333')
    if neo:
        fill=tv.get('mainBkg',fill) if ('redux' in name if root else name in ('redux','redux-dark','neutral')) else fill
        stroke=tv.get('nodeBorder','#333') if name in ('redux','redux-dark') else tv.get('cScale'+str(i),fill)
        color=tv.get('nodeBorder','#333') if ('redux' in name if root else name in ('redux','redux-dark')) else tv.get('cScaleLabel'+str(1 if name=='neutral' else i),color)
    base={'fill':fill,'stroke':stroke,'text_color':color,'stroke_width':number(tv.get('strokeWidth'),2) if neo else 0}
    if neo and tv.get('useGradient') and tv.get('mainBkg'):
        base['fill']=tv['mainBkg'];base['stroke_gradient']=((0.,tv.get('gradientStart','#777')),(1.,tv.get('gradientStop','#333')))
    classes=('mindmap-node','section-root','section--1',*node.classes) if root else ('mindmap-node','section-'+str(node.section),*node.classes)
    style=p.style(classes,id=node.id,base=base)
    if neo and tv.get('dropShadow'):style=apply_declarations(style,'filter:'+tv['dropShadow'],kind='node')
    return style


def _basis_path(points):
    """d3-shape 3.2.0 curve/basis.js open-line branch, pure values."""
    def xy(x,y):return f'{x:.12g},{y:.12g}'
    if not points:return ''
    out=['M'+xy(points[0].x,points[0].y)]
    if len(points)==1:return out[0]+'Z'
    if len(points)==2:return out[0]+'L'+xy(points[1].x,points[1].y)
    a,b=points[:2];out.append('L'+xy((5*a.x+b.x)/6,(5*a.y+b.y)/6))
    for c in (*points[2:],points[-1]):
        out.append('C'+xy((2*a.x+b.x)/3,(2*a.y+b.y)/3)+' '+xy((a.x+2*b.x)/3,(a.y+2*b.y)/3)+' '+xy((a.x+4*b.x+c.x)/6,(a.y+4*b.y+c.y)/6))
        a,b=b,c
    out.append('L'+xy(b.x,b.y));return ' '.join(out)


async def build(diagram,painter):
    from ...runtime.graph import layout_graph
    config=config_dict(diagram);conf=config.get('mindmap') or {};tv=config.get('themeVariables') or {};nodes=[];geometries={};labels={};styles={};shapes={};icon_size=40.
    for node in diagram.model.nodes:
        s=_style(painter,config,node);styles[node.id]=s;label=painter.measure(node.label,label_kind='markdown',width=number(conf.get('maxNodeWidth'),200),style=label_style(s));labels[node.id]=label
        shape=node.shape
        if shape=='default':shape='rounded' if 'redux' in config.get('theme','').lower() else 'defaultMindmapNode'
        shapes[node.id]=shape;lh=label.height
        if shape=='defaultMindmapNode':w=label.width+4*node.padding;h=lh+node.padding
        elif shape=='circle':w=h=math.hypot(label.width,lh)+2*(16 if config.get('look')=='neo' else node.padding)
        else:
            g=painter.shape_geometry('round' if shape=='rounded' else shape,label.width,lh,padding=15 if shape=='rounded' else 10 if shape=='rect' else node.padding);geometries[node.id]=g;w,h=g.width,g.height
        nodes.append({'id':node.id,'width':w,'height':h,'shape':shape})
    by_id={n.id:n for n in diagram.model.nodes};edges=[{'id':'edge_'+n.parent+'_'+n.id,'source':n.parent,'target':n.id} for n in diagram.model.nodes if n.parent is not None]
    algorithm=config.get('layout','elk') if config.get('_explicitRootLayout') else 'cose-bilkent'
    layout=await layout_graph(nodes,edges,config=config,algorithm=algorithm)
    neo=config.get('look')=='neo';painter.rough_enabled=True
    for edge in edges:
        node=by_id[edge['target']];parent=by_id[edge['source']];i=(node.section or 0)+1;depth=parent.level+1;points=list(layout.edges[edge['id']])
        for pos,other,id in ((0,1,parent.id),(-1,-2,node.id)):
            if len(points)>1:points[pos]=clip_endpoint(layout.nodes[id],points[other],'circle' if shapes[id]=='circle' or algorithm=='tidy-tree' and shapes[id] in ('cloud','bang') else 'rect')
        stroke=tv.get('nodeBorder','#333') if neo and ('redux' in config.get('theme','') or config.get('theme')=='neo-dark') else tv.get('cScale'+str(i),'#333')
        width=max(10-depth*2,2) if neo else 17-3*(depth+1)
        s=painter.style(('edge','section-edge-'+str(node.section),'edge-depth-'+str(depth)),tag='path',id=edge['id'],base={'fill':'none','stroke':stroke,'stroke_width':width})
        painter.path(_basis_path(points),style=s,id=edge['id'],role='edge')
    for node in diagram.model.nodes:
        b=layout.nodes[node.id];s=styles[node.id];shape=shapes[node.id];label=labels[node.id];painter.rough_enabled=shape!='defaultMindmapNode'
        if shape=='circle':painter.ellipse(b.x+b.width/2,b.y+b.height/2,b.width/2,b.height/2,style=s,id=node.id)
        elif shape=='defaultMindmapNode':
            x,y,w,h=b.x,b.y,b.width,b.height;r=5
            path=f'M{x} {y+h-r} V{y+r} Q{x} {y} {x+r} {y} H{x+w-r} Q{x+w} {y} {x+w} {y+r} V{y+h if neo else y+h-r}'
            path+=(f' H{x} Z' if neo else f' Q{x+w} {y+h} {x+w-r} {y+h} H{x+r} Q{x} {y+h} {x} {y+h-r} Z')
            painter.path(path,style=s,id=node.id)
            if not(neo and tv.get('useGradient')):painter.line(x,y+h,x+w,y+h,stroke=tv.get('cScaleInv'+str((node.section if node.section is not None else -1)+1),'#333'),line_width=3,id=node.id)
        else:
            g=geometries[node.id];transform=(1,0,0,1,b.x,b.y);painter.path(g.outline,style=s,transform=transform,id=node.id)
            for path in g.details:painter.path(path,style=replace(s,fill='none'),transform=transform,id=node.id)
        label_y=b.y+(b.height-label.height)/2
        if node.icon and not config.get('htmlLabels',True):
            bg=painter.style(('background',),id=node.id,base={'fill':s.fill,'stroke':'none'});painter.rect(b.x+(b.width-label.width)/2-2,label_y-2,label.width+4,label.height+4,style=bg,id=node.id,role='label-background')
        painter.text(label,b.x+(b.width-label.width)/2,label_y,style=s,id=node.id)
    return painter.finish(layout=layout,padding=number(conf.get('padding'),10))
