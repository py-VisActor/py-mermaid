"""Architecture Langium/DB, direction constraints and static fCoSE rendering."""
from __future__ import annotations
from dataclasses import dataclass,replace
from collections import deque
import re
import math
from ...runtime.common import make_diagram,error,config_dict,sanitize_text
from ...model.flowchart import Point
from ..modeling._support import number
from .packet import _string
from .kanban import _rows
from ._fcose import simulate
from ._architecture_icons import ICONS


@dataclass(frozen=True)
class ArchNode:
    id:str
    kind:str
    parent:str|None=None
    icon:str|None=None
    label:str|None=None
    icon_text:str|None=None


@dataclass(frozen=True)
class ArchEdge:
    source:str
    target:str
    source_dir:str
    target_dir:str
    label:str|None=None
    source_arrow:bool=False
    target_arrow:bool=False
    source_group:bool=False
    target_group:bool=False


@dataclass(frozen=True)
class ArchitectureModel:
    nodes:tuple[ArchNode,...]
    groups:tuple[ArchNode,...]
    edges:tuple[ArchEdge,...]
    alignments:tuple=()
    title:str=''
    acc_title:str=''
    acc_description:str=''


_ID=r'[A-Za-z0-9_](?:[-A-Za-z0-9_]*[A-Za-z0-9_])?'
_TITLE=r'\[(?:"(?:[^"\\]|\\.)*"|\x27(?:[^\x27\\]|\\.)*\x27|[^\[\]\r\n]+)\]'
_STRING=r'"(?:[^"\\]|\\.)*"|\x27(?:[^\x27\\]|\\.)*\x27'


def _title(raw):
    if raw is None:return None
    text=raw[1:-1].strip()
    if len(text)>=2 and text[0]==text[-1] and text[0] in ('"',"'"):text=text[1:-1].replace('\\"','"').replace("\\'","'")
    return text.strip()


def parse(document,config):
    declarations=[];edges=[];hints=[];header=False;title=document.title or '';acc_title='';acc_description=''
    for offset,line in _rows(document.cleaned):
        text=line.strip()
        if not text or text.startswith('%%'):continue
        if not header:
            m=re.match(r'architecture-beta\b',text)
            if not m:raise error(document,offset,'Expected architecture-beta header')
            header=True;text=text[m.end():].strip()
            if not text:continue
        m=re.fullmatch(r'title(?:[\t ]+(.*))?|accTitle\s*:\s*(.*)|accDescr\s*:\s*(.*)|accDescr\s*\{([^}]*)\}',text,re.S)
        if m:
            if text.startswith('title'):title=(m[1] or '').strip()
            elif m[2] is not None:acc_title=m[2].strip()
            else:acc_description=(m[3] if m[3] is not None else m[4] or '').strip()
            continue
        m=re.fullmatch(r'(group|service|junction)\s+('+_ID+r')(?:\s*(\([\w:-]+\)|'+_STRING+r'))?(?:\s*('+_TITLE+r'))?(?:\s+in\s+('+_ID+r'))?\s*',text,re.ASCII|re.S)
        if m:
            kind,id,icon_or_text,label,parent=m.groups()
            if kind=='junction' and (icon_or_text or label):raise error(document,offset,'Junction does not take icon or title')
            if kind=='group' and icon_or_text and not icon_or_text.startswith('('):raise error(document,offset,'Group icon must be a named icon')
            icon=icon_or_text[1:-1].strip() if icon_or_text and icon_or_text.startswith('(') else None;icon_text=_string(icon_or_text) if icon_or_text and not icon else None;declarations.append((offset,ArchNode(id,kind,parent,icon,_title(label),icon_text)));continue
        m=re.fullmatch(r'align\s+(row|column)\s+('+_ID+r'(?:\s+'+_ID+r')+)\s*',text)
        if m:hints.append((offset,m[1],tuple(m[2].split())));continue
        m=re.fullmatch(r'('+_ID+r')(\{group\})?\s*:\s*([LRTB])\s*([<>])?\s*(?:--|-\s*('+_TITLE+r')\s*-)\s*([<>])?\s*([LRTB])\s*:\s*('+_ID+r')(\{group\})?\s*',text,re.S)
        if m:
            a,ag,ad,aa,label,ba,bd,b,bg=m.groups();edges.append((offset,ArchEdge(a,b,ad,bd,_title(label),bool(aa),bool(ba),bool(ag),bool(bg))));continue
        raise error(document,offset,'Invalid architecture statement')
    if not header:raise error(document,0,'Missing architecture header')
    # populateDb groups before services before junctions, regardless of source
    # statement interleaving; declaration order is retained within each kind.
    registered={};groups=[];nodes=[]
    for kind in ('group','service','junction'):
        for offset,node in declarations:
            if node.kind!=kind:continue
            if node.id in registered:raise error(document,offset,'Architecture ID is already in use','DUPLICATE_ID')
            if node.parent is not None:
                if node.parent==node.id:raise error(document,offset,'Architecture element cannot be placed within itself','INVALID_PARENT')
                if node.parent not in registered:raise error(document,offset,'Parent must be created before this element','UNKNOWN_PARENT')
                if registered[node.parent]!='group':raise error(document,offset,'Architecture parent is not a group','INVALID_PARENT')
            registered[node.id]=kind
            (groups if kind=='group' else nodes).append(node)
    lookup={n.id:n for n in nodes};edge_ids=set()
    for offset,edge in edges:
        if edge.source not in registered or edge.target not in registered:raise error(document,offset,'Architecture edge references an unknown element','UNKNOWN_REFERENCE')
        # The fixed DB dereferences nodes.get(id).in; group IDs are not legal
        # service endpoints despite the preliminary registered-ID test.
        if edge.source not in lookup or edge.target not in lookup:raise error(document,offset,'Group ID cannot be used directly as an architecture service endpoint','UPSTREAM_ARCHITECTURE_ENDPOINT')
        a,b=lookup[edge.source],lookup[edge.target]
        if (edge.source_group or edge.target_group) and a.parent and b.parent and a.parent==b.parent:raise error(document,offset,'Group boundary modifier does not pass through two groups','INVALID_GROUP_EDGE')
        key=edge.source+'-'+edge.target
        if key in edge_ids:raise error(document,offset,'Duplicate Cytoscape architecture edge identity','DUPLICATE_EDGE_ID')
        edge_ids.add(key)
    for offset,direction,members in hints:
        if any(id not in lookup for id in members):raise error(document,offset,'Alignment requires services or junctions','UNKNOWN_REFERENCE')
        if len(set(members))!=len(members):raise error(document,offset,'Alignment member listed more than once','DUPLICATE_ID')
    return make_diagram('architecture',document,config,ArchitectureModel(tuple(nodes),tuple(groups),tuple(e for _,e in edges),tuple((d,m) for _,d,m in hints),title,acc_title,acc_description))


def _shift(pos,pair):
    x,y=pos;a,b=pair
    if a in 'LR':return x+(-1 if a=='L' else 1),y+(1 if b=='T' else -1) if b in 'TB' else y
    return (x+(1 if b=='L' else -1) if b in 'LR' else x),y+(1 if a=='T' else -1)


def _constraints(model,config):
    lookup={n.id:n for n in model.nodes};adj={id:{} for id in lookup};group_align={}
    for edge in model.edges:
        a,b=edge.source,edge.target;ad,bd=edge.source_dir,edge.target_dir;pa,pb=lookup[a].parent,lookup[b].parent
        if pa and pb and pa!=pb and (ad in 'LR')==(bd in 'LR'):group_align[tuple(sorted((pa,pb)))]= 'horizontal' if ad in 'LR' else 'vertical'
        if ad!=bd:adj[a][ad+bd]=b;adj[b][bd+ad]=a
    spatial=[];visited=set()
    for first in lookup:
        if first in visited:continue
        positions={first:(0,0)};queue=deque([first])
        while queue:
            id=queue.popleft();visited.add(id)
            for pair,other in adj[id].items():
                if other not in visited:positions[other]=_shift(positions[id],pair);queue.append(other)
        spatial.append(positions)
    horizontal=[];vertical=[];declared={id for _,members in model.alignments for id in members};gap=number(config.get('idealEdgeLengthMultiplier'),1.5)*number(config.get('iconSize'),80);relative=[];pairs=set()
    def flatten(table,direction):
        out=[]
        for coordinate,group_map in table.items():
            arr=list(group_map.items())
            if len(arr)==1:out.append(arr[0][1]);continue
            merged=[]
            for i,(a,aa) in enumerate(arr[:-1]):
                for b,bb in arr[i+1:]:
                    if group_align.get(tuple(sorted((a,b))))==direction or 'default' in (a,b):merged.extend((*aa,*bb))
                    else:out.extend((aa,bb))
            if merged:out.append(merged)
        return [tuple(a) for a in out if len(a)>1 and not any(id in declared for id in a)]
    for pos in spatial:
        h={};v={}
        for id,(x,y) in pos.items():
            group=lookup[id].parent or 'default';h.setdefault(y,{}).setdefault(group,[]).append(id);v.setdefault(x,{}).setdefault(group,[]).append(id)
        horizontal.extend(flatten(h,'horizontal'));vertical.extend(flatten(v,'vertical'))
    for direction,members in model.alignments:
        (horizontal if direction=='row' else vertical).append(members)
        for a,b in zip(members,members[1:]):relative.append((0 if direction=='row' else 1,a,b,gap));pairs.update(((a,b),(b,a)))
    for pos in spatial:
        inv={coordinate:id for id,coordinate in pos.items()};queue=deque([(0,0)]);seen=set()
        while queue:
            at=queue.popleft();seen.add(at);id=inv.get(at)
            if id is None:continue
            for direction,(dx,dy) in (('L',(-1,0)),('R',(1,0)),('T',(0,1)),('B',(0,-1))):
                other_at=(at[0]+dx,at[1]+dy);other=inv.get(other_at)
                if other is None or other_at in seen:continue
                queue.append(other_at)
                if (id,other) in pairs:continue
                a,b=(other,id) if direction in ('L','T') else (id,other);relative.append((0 if direction in 'LR' else 1,a,b,gap))
    return tuple(horizontal),tuple(vertical),tuple(relative)


def _line_clamp(painter,box,max_lines,width,style):
    # Native counterpart of source -webkit-line-clamp. Keep rich run styles,
    # measure the actual last visible line and append a measured ellipsis.
    baselines=sorted(set(r.baseline for r in box.runs))
    if max_lines<=0:return replace(box,width=0.,height=0.,runs=())
    if len(baselines)<=max_lines:return box
    last=baselines[max_lines-1];runs=[r for r in box.runs if r.baseline<=last];ellipsis=painter.measure('\u2026',style=style,html=False);ew=ellipsis.width
    while runs and runs[-1].baseline==last and runs[-1].x+runs[-1].width+ew>width:
        run=runs[-1]
        if not run.text:runs.pop();continue
        text=run.text[:-1]
        if not text:runs.pop();continue
        rs=replace(style,font_family=run.font_family,font_size=run.font_size,font_weight=run.font_weight,font_style=run.font_style);measured=painter.measure(text,style=rs,html=False);runs[-1]=replace(run,text=text,width=measured.width,ink_right=measured.width)
    end=max((r.x+r.width for r in runs if r.baseline==last),default=0.)
    runs.extend(replace(r,x=r.x+end,baseline=last) for r in ellipsis.runs)
    height=max((r.baseline+r.descent for r in runs),default=0.)
    return replace(box,width=min(width,max(box.width,end+ew)),height=height,runs=tuple(runs))


async def build(diagram,painter):
    config=config_dict(diagram);conf=config.get('architecture') or {};tv=config.get('themeVariables') or {};model=diagram.model;icon=number(conf.get('iconSize'),80);padding=number(conf.get('padding'),40);font=number(conf.get('fontSize'),16);horizontal,vertical,relative=_constraints(model,conf);nodes=[{'id':n.id,'parent':n.parent,'width':icon,'height':icon} for n in model.nodes];parents=[{'id':g.id,'parent':g.parent} for g in model.groups];edges=[{'id':str(i),'source':e.source,'target':e.target} for i,e in enumerate(model.edges)];painter.rough_enabled=False
    boxes,groups=simulate(nodes,parents,edges,horizontal=horizontal,vertical=vertical,relative=relative,config=conf)
    from ..modeling._usecase_glyphs import child_style
    svg=painter.style(('architecture',),tag='svg',id=painter.render_id)
    edges_container=child_style(painter,('architecture-edges',),svg)
    services_container=child_style(painter,('architecture-services',),svg)
    groups_container=child_style(painter,('architecture-groups',),svg)
    def draw_icon(name,x,y,size,id,style):
        prefix,key=name.split(':',1) if ':' in name else ('mermaid-architecture',name)
        if prefix=='mermaid-architecture':painter.svg(ICONS.get(key,ICONS['unknown']),x,y,size,size,id=id,style=style)
        else:painter.asset(name,x,y,size,size,kind='icon',id=id,style=style)
    lookup={n.id:n for n in model.nodes}
    # Render edges first, matching source stacking order.
    for i,edge in enumerate(model.edges):
        a,b=boxes[edge.source],boxes[edge.target]
        def endpoint(box,node,direction,group):
            dx,dy={'L':(-1,0),'R':(1,0),'T':(0,-1),'B':(0,1)}[direction];x=box.x+icon/2+dx*icon/2;y=box.y+icon/2+dy*icon/2
            if group:x+=dx*(padding+4);y+=dy*(padding+4+(18 if direction=='B' else 0))
            elif node.kind=='junction':x-=dx*icon/2;y-=dy*icon/2
            return Point(x,y)
        start=endpoint(a,lookup[edge.source],edge.source_dir,edge.source_group);end=endpoint(b,lookup[edge.target],edge.target_dir,edge.target_group);bend=Point(start.x,end.y) if edge.source_dir in 'TB' else Point(end.x,start.y);mid=Point((start.x+end.x)/2,(start.y+end.y)/2) if abs(start.x-end.x)<1e-8 or abs(start.y-end.y)<1e-8 else bend;id='architecture-edge-'+str(i)
        edge_group=child_style(painter,(),edges_container)
        s=child_style(painter,('edge',),edge_group,tag='path',id=id,base={'fill':'none','stroke':tv.get('archEdgeColor','#333'),'stroke_width':number(tv.get('archEdgeWidth'),2)});painter.polyline((start,mid,end),style=s,id=id)
        arrow_size=icon/6
        for point,direction,enabled in ((start,edge.source_dir,edge.source_arrow),(end,edge.target_dir,edge.target_arrow)):
            if not enabled:continue
            dx,dy={'L':(1,0),'R':(-1,0),'T':(0,1),'B':(0,-1)}[direction];tip=Point(point.x+dx*2,point.y+dy*2);base=Point(tip.x-dx*arrow_size,tip.y-dy*arrow_size);arrow_style=child_style(painter,('arrow',),edge_group,tag='polygon',base={'fill':tv.get('archEdgeArrowColor',s.stroke),'stroke':'none'});painter.polygon(((tip.x,tip.y),(base.x-dy*arrow_size/2,base.y+dx*arrow_size/2),(base.x+dy*arrow_size/2,base.y-dx*arrow_size/2)),style=arrow_style,id=id,role='arrow')
        if edge.label:
            xy=(edge.source_dir in 'LR')!=(edge.target_dir in 'LR');width=abs(start.x-end.x)/2 if xy else abs(start.x-end.x) if edge.source_dir in 'LR' else abs(start.y-end.y)/1.5;ls=child_style(painter,('architecture-service-label',),child_style(painter,(),edge_group),tag='text',base={'font_size':font});label=painter.measure(edge.label,html=False,width=width,style=ls);rotation=0 if edge.source_dir in 'LR' else -90
            if xy:
                factors=(1,1) if edge.source_dir+edge.target_dir in ('LT','TL') else (1,-1) if edge.source_dir+edge.target_dir in ('BL','LB') else (-1,-1) if edge.source_dir+edge.target_dir in ('BR','RB') else (-1,1);rotation=-factors[0]*factors[1]*45
            painter.text(label,mid.x-label.width/2,mid.y-label.height/2,rotation=rotation,style=ls,id=id,role='edge-label')
    for node in model.nodes:
        b=boxes[node.id]
        if node.kind=='junction':continue # source transparent 80x80 footprint
        service=child_style(painter,('architecture-service',),services_container,id=painter.render_id+'-service-'+node.id)
        bkg=child_style(painter,(),service)
        if node.icon:draw_icon(node.icon,b.x,b.y,icon,node.id,bkg)
        elif node.icon_text:
            draw_icon('blank',b.x,b.y,icon,node.id,bkg);text_group=child_style(painter,(),bkg);outer_div=child_style(painter,('node-icon-text',),text_group,tag='div');s=child_style(painter,(),outer_div,tag='div',base={'text_color':'#fff','font_size':font});label=painter.measure(sanitize_text(node.icon_text,config),width=max(0,icon-2),style=s);label=_line_clamp(painter,label,max(0,math.floor((icon-2)/s.font_size)),icon-2,s);painter.text(label,b.x+1,b.y+(icon-label.height)/2,style=s,id=node.id,role='icon-text',clip=(b.x,b.y,icon,icon))
        else:
            s=child_style(painter,('node-bkg',),bkg,tag='path',id=painter.render_id+'-node-'+node.id,base={'fill':'none','stroke':tv.get('archGroupBorderColor','#666'),'stroke_width':number(tv.get('archGroupBorderWidth'),2),'dash':(8.,8.)});painter.path(f'M{b.x} {b.y+icon} V{b.y+5} Q{b.x} {b.y} {b.x+5} {b.y} H{b.x+icon-5} Q{b.x+icon} {b.y} {b.x+icon} {b.y+5} V{b.y+icon} Z',style=s,id=node.id)
        if node.label:
            label_group=child_style(painter,(),service);s=child_style(painter,('architecture-service-label',),label_group,tag='text',base={'font_size':font});label=painter.measure(node.label,html=False,width=icon*1.5,style=s);painter.text(label,b.x+(icon-label.width)/2,b.y+icon,style=s,id=node.id)
    for group in model.groups:
        b=groups[group.id];s=child_style(painter,('node-bkg',),groups_container,tag='rect',id=painter.render_id+'-group-'+group.id,base={'fill':'none','stroke':tv.get('archGroupBorderColor','#666'),'stroke_width':number(tv.get('archGroupBorderWidth'),2),'dash':(8.,8.)});painter.rect(b.x,b.y,b.width,b.height,style=s,id=group.id,role='architecture-group');x=b.x+4;y=b.y+2
        label_container=child_style(painter,(),groups_container)
        if group.icon:draw_icon(group.icon,b.x+1,b.y+1,padding*.75,group.id,child_style(painter,(),label_container));x+=padding*.75;y+=font/2-3
        if group.label:
            ls=child_style(painter,('architecture-service-label',),child_style(painter,(),label_container),tag='text',base={'font_size':font});painter.text(group.label,x,y,html=False,width=b.width,style=ls,id=group.id)
    return painter.finish(layout=('architecture-fcose-proof',tuple(boxes.items()),tuple(groups.items()),horizontal,vertical,relative),padding=padding)
