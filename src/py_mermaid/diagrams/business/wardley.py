"""Wardley grammar/DB and percentage-coordinate projection renderer."""
from dataclasses import dataclass,replace
import math
import re
from ...runtime.common import make_diagram,config_dict,error
from ..temporal._syntax import metadata,langium_metadata

DEC=r'\d+\.\d+'
NAME=r'(?:"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z][A-Za-z0-9_()& -]*?|\w(?:[-\w]*\w)?)'

@dataclass(frozen=True)
class Node:
    id:str
    label:str
    x:float
    y:float
    kind:str='component'
    offset_x:object=None
    offset_y:object=None
    inertia:bool=False
    strategy:str=''
    pipeline:bool=False
    in_pipeline:bool=False

@dataclass(frozen=True)
class Wardley:
    nodes:tuple=()
    links:tuple=()
    trends:tuple=()
    pipelines:tuple=()
    notes:tuple=()
    annotations:tuple=()
    annotations_box:object=None
    accelerators:tuple=()
    stages:tuple=()
    boundaries:tuple=()
    size:object=None
    title:str=''
    accessibility:tuple=()

def name(v):
    v=v.strip()
    return v[1:-1] if v[:1] in ('"',"'") else v

def parse(document,config):
    masked,common=langium_metadata(document);s=masked.cleaned;records=[];pos=0
    for raw in s.splitlines(keepends=True):
        rawvalue=raw.strip()
        quote=None;cut=len(rawvalue);i=0
        while i<len(rawvalue):
            ch=rawvalue[i]
            if quote:
                if ch=='\\':i+=2;continue
                if ch==quote:quote=None
            elif ch in ('"',"'"):quote=ch
            elif rawvalue.startswith('%%',i):cut=i;break
            i+=1
        rawvalue=rawvalue[:cut].rstrip()
        if rawvalue:records.append((pos,rawvalue))
        pos+=len(raw)
    if not records or records[0][1]!='wardley-beta':raise error(document,0,'Expected wardley-beta')
    anchors=[];components=[];pipelines=[];links=[];evolves=[];notes=[];annotations=[];abox=None;accelerators=[];stages=();boundaries=();size=None;meta={'title':document.title or '',**common};i=1
    def percent(v,at):
        value=float(v);value=value*100 if value<=1 else value
        if not 0<=value<=100:raise error(document,at,'Coordinate must be between 0-1 or 0-100')
        return value
    def component(v,at,pipeline=False):
        count=DEC if pipeline else DEC+r'\s*,\s*'+DEC
        m=re.fullmatch(r'component\s+('+NAME+r')\s*\[('+count+r')\]\s*(?:label\s*\[(-?\d+)\s*,\s*(-?\d+)\])?\s*(?:\((build|buy|outsource|market)\))?\s*(inertia|\(inertia\))?',v)
        if not m:raise error(document,at,'Invalid Wardley component')
        values=[percent(x,at) for x in m[2].split(',')]
        return (name(m[1]),values,None if m[3] is None else int(m[3]),None if m[4] is None else int(m[4]),m[5] or '',bool(m[6]))
    while i<len(records):
        at,v=records[i];i+=1
        if metadata(v,meta):continue
        m=re.fullmatch(r'size\s*\[(\d+)\s*,\s*(\d+)\]',v)
        if m:size=(int(m[1]),int(m[2]));continue
        if v.startswith('evolution '):
            names=[];bs=[]
            for stage in v[10:].split('->'):
                m=re.fullmatch(r'\s*('+NAME+r')(?:\s*@\s*('+DEC+r'))?(?:\s*/\s*('+NAME+r'))?\s*',stage)
                if not m:raise error(document,at,'Invalid evolution stage')
                names.append(name(m[1])+(' / '+name(m[3]) if m[3] else ''))
                if m[2] is not None:bs.append(float(m[2]))
            if len(names)<2:raise error(document,at,'Evolution needs at least two stages')
            stages=tuple(names);boundaries=tuple(bs);continue
        if v.startswith('component '):components.append(component(v,at));continue
        m=re.fullmatch(r'(anchor|note|accelerator|deaccelerator)\s+('+NAME+r')\s*\[('+DEC+r')\s*,\s*('+DEC+r')\]',v)
        if m:
            item=(name(m[2]),percent(m[4],at),percent(m[3],at))
            if m[1]=='anchor':anchors.append(item)
            elif m[1]=='note':
                if m[2][0] not in ('"',"'"):raise error(document,at,'Note requires quoted text')
                notes.append(item)
            else:accelerators.append((m[1],)+item)
            continue
        m=re.fullmatch(r'pipeline\s+('+NAME+r')\s*\{',v)
        if m:
            children=[]
            while i<len(records) and records[i][1]!='}':children.append(component(records[i][1],records[i][0],True));i+=1
            if i>=len(records) or not children:raise error(document,at,'Expected nonempty pipeline and closing brace')
            i+=1;pipelines.append((name(m[1]),tuple(children),at));continue
        m=re.fullmatch(r'evolve\s+('+NAME+r')\s+('+DEC+r')',v)
        if m:evolves.append((name(m[1]),percent(m[2],at)));continue
        m=re.fullmatch(r'annotations\s*\[([\d.]+)\s*,\s*([\d.]+)\]',v)
        if m:
            if abox is None:abox=(percent(m[2],at),percent(m[1],at))
            continue
        m=re.fullmatch(r'annotation\s+(\d+)\s*,\s*\[([\d.]+)\s*,\s*([\d.]+)\]\s*(".*"|\'.*\')',v)
        if m:annotations.append((int(m[1]),percent(m[3],at),percent(m[2],at),name(m[4])));continue
        # Tokenize links independently so arrows and semicolon labels cannot
        # be swallowed by names containing spaces or hyphens.
        m=re.fullmatch(r'('+NAME+r')\s*(\+<>|\+>|\+<)?\s*(-->|-\.->|->|>|\+\'[^\']*\'(?:<>|<|>))?\s*('+NAME+r')\s*(\+<>|\+>|\+<)?\s*(;[^\r\n]+)?',v)
        if not m:raise error(document,at,'Invalid Wardley statement')
        arrow=m[3] or '';port=m[2] or m[5] or '';flow='bidirectional' if '<>' in port else 'backward' if '<' in port else 'forward' if '>' in port else ''
        am=re.match(r"\+'([^']*)'",arrow);label=am[1] if am else (m[6] or '')
        if not flow and arrow.startswith('+'):flow='bidirectional' if '<>' in arrow else 'backward' if '<' in arrow else 'forward' if '>' in arrow else ''
        links.append((name(m[1]),name(m[4]),'-.->' in arrow or '.-.' in arrow,label,flow))
    nodes={}
    for label,x,y in anchors:nodes[label]=Node(label,label,x,y,'anchor')
    for label,values,ox,oy,strategy,inertia in components:
        old=nodes.get(label)
        nodes[label]=Node(label,label,values[1],values[0],offset_x=ox if ox is not None else old.offset_x if old else None,offset_y=oy if oy is not None else old.offset_y if old else None,inertia=inertia,strategy=strategy)
    pipes={}
    for parent,children,at in pipelines:
        if parent not in nodes:raise error(document,at,'Pipeline must reference an existing component')
        nodes[parent]=replace(nodes[parent],pipeline=True);ids=[]
        for label,values,ox,oy,_,_ in children:
            ident=parent+'_'+label;nodes[ident]=Node(ident,label,values[0],nodes[parent].y,'pipeline-component',ox,oy,in_pipeline=True);ids.append(ident)
        pipes[parent]=tuple(ids)
    def resolve(label):return label if label in nodes else next((n.id for n in nodes.values() if n.label==label),label)
    links=tuple((resolve(a),resolve(b),dash,label,flow) for a,b,dash,label,flow in links)
    trends={}
    for label,target in evolves:
        if label in nodes:trends[label]=(label,target,nodes[label].y)
    model=Wardley(tuple(nodes.values()),links,tuple(trends.values()),tuple(pipes.items()),tuple(notes),tuple(annotations),abox,tuple(accelerators),stages,boundaries,size,meta['title'],tuple(meta.items()))
    return make_diagram('wardley',document,config,model)

async def build(diagram,p):
    c=config_dict(diagram);cfg=c.get('wardley-beta',{});tv=c['themeVariables'];t=tv.get('wardley',{});m=diagram.model
    w,h=m.size or (cfg.get('width',900),cfg.get('height',600));pad=cfg.get('padding',48);r=cfg.get('nodeRadius',6);sq=r*1.6;fs=cfg.get('axisFontSize',12);ls=cfg.get('labelFontSize',10);offset=cfg.get('nodeLabelOffset',8)
    colors={'backgroundColor':tv.get('background','#fff'),'axisColor':'#000','axisTextColor':tv.get('primaryTextColor','#222'),'gridColor':'rgba(100,100,100,.2)','componentFill':'#fff','componentStroke':'#000','componentLabelColor':tv.get('primaryTextColor','#222'),'linkStroke':'#000','evolutionStroke':'#dc3545','annotationStroke':'#000','annotationTextColor':tv.get('primaryTextColor','#222'),'annotationFill':tv.get('background','#fff')};colors.update(t);t=colors
    from ._source_styles import styles
    p.add_styles(styles('wardley',t));node_parent=None
    def st(cls,tag='path',**base):return p.style(cls,tag=tag,base=base,ancestors=(('g',('wardley-map',),''),('g',tuple(cls.split()),''))+((node_parent,) if node_parent else ()))
    def txt(text,x,y,cls='',size=ls,color=None,align='left',middle=False,weight='normal',rotation=0):
        style=st(cls,'text',font_size=size,text_color=color or t['axisTextColor'],font_weight=weight)
        box=p.measure(str(text),html=False,style=style);left=x-(box.width/2 if align=='center' else box.width if align=='right' else 0);top=y-(box.height/2 if middle else box.ascent)
        if rotation:
            angle=math.radians(rotation);dx=left-x;dy=top-y;left=x+math.cos(angle)*dx-math.sin(angle)*dy;top=y+math.sin(angle)*dx+math.cos(angle)*dy
            p.text(box,left,top,align='left',rotation=rotation,style=style)
        else:p.text(box,x,top,align=align,style=style)
        return box
    def line(x,y,u,v,cls='',color=None,width=1,dash=(),opacity=1):p.line(x,y,u,v,style=st(cls,fill='none',stroke=color or t['axisColor'],stroke_width=width,dash=dash,opacity=opacity))
    def circle(x,y,radius,cls='',fill=None,stroke=None,width=1):p.ellipse(x,y,radius,radius,style=st(cls,'circle',fill=fill or t['componentFill'],stroke=stroke or t['componentStroke'],stroke_width=width))
    def xy(x,y):return pad+x*(w-2*pad)/100,h-pad-y*(h-2*pad)/100
    p.rect(0,0,w,h,style=st('wardley-background','rect',fill=t['backgroundColor'],stroke='none'))
    if m.title:txt(m.title,w/2,pad/2,'wardley-title',fs*1.05,align='center',middle=True,weight='bold')
    line(pad,h-pad,w-pad,h-pad,'wardley-axes');line(pad,pad,pad,h-pad,'wardley-axes')
    txt('Evolution',w/2,h-pad/4,'wardley-axis-label wardley-axis-label-x',fs,align='center',weight='bold')
    txt('Visibility',pad/3,h/2,'wardley-axis-label wardley-axis-label-y',fs,align='center',weight='bold',rotation=-90)
    stages=m.stages or ('Genesis','Custom Built','Product','Commodity');previous=0
    for i,stage in enumerate(stages):
        if len(m.boundaries)==len(stages):start=previous;end=m.boundaries[i];previous=end
        else:start=i/len(stages);end=(i+1)/len(stages)
        x=pad+start*(w-2*pad)
        if i:line(x,pad,x,h-pad,color='#000',dash=(5,5),opacity=.8)
        txt(stage,pad+(start+end)/2*(w-2*pad),h-pad/1.5,'wardley-stage-label',fs-2,align='center')
    if cfg.get('showGrid',False):
        for i in range(1,4):
            x=pad+(w-2*pad)*i/4;y=h-pad-(h-2*pad)*i/4
            line(x,pad,x,h-pad,'wardley-grid',color=t['gridColor'],dash=(2,6));line(pad,y,w-pad,y,'wardley-grid',color=t['gridColor'],dash=(2,6))
    positions={n.id:list(xy(n.x,n.y)) for n in m.nodes};nodes={n.id:n for n in m.nodes};pipelines=dict(m.pipelines)
    for parent,ids in m.pipelines:
        if not ids:continue
        ordered=sorted(ids,key=lambda ident:nodes[ident].x)
        for a,b in zip(ordered,ordered[1:]):line(*positions[a],*positions[b],'wardley-pipeline-evolution-link',t['linkStroke'],dash=(4,4))
        left=min(positions[i][0] for i in ids);right=max(positions[i][0] for i in ids);y=positions[ids[-1]][1];top=y-r*2
        positions[parent]=[(left+right)/2,top-sq/6]
        p.rect(left-15,top,right-left+30,r*4,radius=4,style=st('wardley-pipeline-box','rect',fill='none',stroke=t['componentStroke'],stroke_width=1.5))
    for a,b,dash,label,flow in m.links:
        if a not in positions or b not in positions or a in pipelines.get(b,()):continue
        x,y=positions[a];u,v=positions[b];dx=u-x;dy=v-y;dist=math.hypot(dx,dy)
        # Source produces non-painted NaN endpoints for coincident centers.
        if not dist:continue
        ar=sq/math.sqrt(2) if nodes[a].pipeline else r;br=sq/math.sqrt(2) if nodes[b].pipeline else r
        x1=x+dx/dist*ar;y1=y+dy/dist*ar;x2=u-dx/dist*br;y2=v-dy/dist*br
        line(x1,y1,x2,y2,'wardley-link wardley-link--dashed' if dash else 'wardley-link',t['linkStroke'],dash=(4,4) if dash else ())
        if flow in ('forward','bidirectional'):p.marker(x2,y2,dx,dy,size=5,color=t['linkStroke'])
        if flow in ('backward','bidirectional'):p.marker(x1,y1,-dx,-dy,size=5,color=t['linkStroke'])
        if label:
            angle=math.degrees(math.atan2(dy,dx));angle+=180 if angle>90 or angle<-90 else 0
            txt(label,(x+u)/2+dy/dist*8,(y+v)/2-dx/dist*8,'wardley-link-label',align='center',middle=True,rotation=angle)
    for ident,tx,ty in m.trends:
        x,y=positions[ident];u,v=xy(tx,ty);dx=u-x;dy=v-y;dist=math.hypot(dx,dy)
        if dist>r+2:u-=dx/dist*(r+2);v-=dy/dist*(r+2)
        line(x,y,u,v,'wardley-trend',t['evolutionStroke'],dash=(4,4));p.marker(u,v,dx,dy,size=6,color=t['evolutionStroke'])
    for n in m.nodes:
        node_parent=('g',('wardley-node','wardley-node--'+n.kind),n.id)
        x,y=positions[n.id];strategy=n.strategy
        if strategy:circle(x,y,r*2,'wardley-'+strategy+'-overlay',{'outsource':'#666','buy':'#ccc','build':'#eee','market':'white'}[strategy],'#000' if strategy=='build' else t['componentStroke'])
        if not n.pipeline and strategy!='market' and n.kind!='anchor':circle(x,y,r)
        if strategy=='market':
            tr=r*1.2;pts=((x,y-tr),(x-tr*math.cos(math.pi/6),y+tr*.5),(x+tr*math.cos(math.pi/6),y+tr*.5))
            for a,b in zip(pts,pts[1:]+pts[:1]):line(*a,*b,'wardley-market-line',t['componentStroke'])
            for u,v in pts:circle(u,v,r*.7,'wardley-market-dot','white',width=2)
        if n.pipeline:p.rect(x-sq/2,y-sq/2,sq,sq,style=st('','rect',fill=t['componentFill'],stroke=t['componentStroke'],stroke_width=1))
        if n.inertia:
            extra=(sq/2 if n.pipeline else r)+15+(r+10 if strategy else 0);height=sq if n.pipeline else r*2
            line(x+extra,y-height/2,x+extra,y+height/2,'wardley-inertia',t['componentStroke'],6)
        anchor=n.kind=='anchor';ox=n.offset_x if n.offset_x is not None else 0 if anchor else offset+(10 if strategy else 0);oy=n.offset_y if n.offset_y is not None else -3 if anchor else -offset-(10 if strategy else 0)
        txt(n.label,x+ox,y+oy,'wardley-node-label',color=t['componentLabelColor'],align='center' if anchor else 'left',middle=anchor,weight='bold' if anchor else 'normal')
    node_parent=None
    for number,x,y,text in m.annotations:
        u,v=xy(x,y);circle(u,v,10,'wardley-annotation',t['annotationFill'],t['annotationStroke'],1.5);txt(number,u,v,'wardley-annotation',10,t['annotationTextColor'],'center',True,'bold')
    if m.annotations_box and m.annotations:
        entries=sorted((a for a in m.annotations if a[3]),key=lambda a:a[0]);measures=[p.measure(f'{a[0]}. {a[3]}',size=11,html=False) for a in entries]
        if entries:
            bw=max(b.width for b in measures)+125;bh=len(entries)*16+20+max(b.height for b in measures)/2;bx,by=xy(*m.annotations_box);bx=max(pad,min(bx,w-pad-bw));by=max(pad,min(by,h-pad-bh))
            p.rect(bx,by,bw,bh,radius=4,style=st('wardley-annotations-box','rect',fill=t['annotationFill'],stroke=t['annotationStroke'],stroke_width=1.5))
            for i,a in enumerate(entries):txt(f'{a[0]}. {a[3]}',bx+10,by+10+(i+1)*16,'wardley-annotations-box',11,t['annotationTextColor'],middle=True)
    for text,x,y in m.notes:txt(text,*xy(x,y),'wardley-notes',11,weight='bold')
    for kind,text,x,y in m.accelerators:
        u,v=xy(x,y);points=((0,-15),(40,-15),(40,-23),(60,0),(40,23),(40,15),(0,15))
        if kind=='deaccelerator':points=tuple((60-a,b) for a,b in points)
        p.polygon(tuple((u+a,v+b) for a,b in points),style=st('wardley-'+kind,fill='white',stroke=t['componentStroke'],stroke_width=1));txt(text,u+30,v+30,'',10,align='center',weight='bold')
    return p.finish(width=w,height=h,padding=0)
