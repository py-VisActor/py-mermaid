"""C4 macro grammar, named attributes and original recursive bounds/grid.

The source C4 renderer is intentionally not a graph-layout algorithm. Its
source-ordered rows, boundary rows and relationship geometry are ported here.
"""
from dataclasses import dataclass,replace
import math
import re
from ._support import statements,split_top,unquote,number,node_style


@dataclass(frozen=True)
class C4Element:
    id:str
    kind:str
    label:str
    parent:str='global'
    attributes:tuple=()
    boundary:bool=False


@dataclass(frozen=True)
class C4Relation:
    source:str
    target:str
    label:str
    kind:str='rel'
    attributes:tuple=()


@dataclass(frozen=True)
class C4Model:
    variant:str
    elements:tuple[C4Element,...]
    boundaries:tuple[C4Element,...]
    relations:tuple[C4Relation,...]
    shape_in_row:int=4
    boundary_in_row:int=2
    title:str=''
    acc_description:str=''


_SHAPES={'Person':'person','Person_Ext':'external_person'}
for _base in ('System','Container','Component'):
    for _external in ('','_Ext'):
        for _sub in ('','Db','Queue'):_SHAPES[_base+_sub+_external]=('external_' if _external else '')+_base.lower()+('_'+_sub.lower() if _sub else '')
_BOUNDARIES={'Enterprise_Boundary':'ENTERPRISE','System_Boundary':'SYSTEM','Container_Boundary':'CONTAINER','Boundary':'','Deployment_Node':'node','Node':'node','Node_L':'nodeL','Node_R':'nodeR'}
_RELATIONS={'Rel':'rel','BiRel':'birel','Rel_Up':'rel_u','Rel_U':'rel_u','Rel_Down':'rel_d','Rel_D':'rel_d','Rel_Left':'rel_l','Rel_L':'rel_l','Rel_Right':'rel_r','Rel_R':'rel_r','Rel_Back':'rel_b','RelIndex':'rel_index'}


def _items(text):
    # C4 attributes can span lines; outside strings, newline is a statement
    # delimiter only at parenthesis depth zero. Preserve offsets by masking.
    chars=list(text);quote=False;depth=0
    for i,c in enumerate(text):
        if c=='"':quote=not quote
        elif not quote:
            if c=='(':depth+=1
            elif c==')':depth-=1
            elif c in '\r\n' and depth:chars[i]=' '
    return statements(''.join(chars),semicolon=False)


def _arguments(text):
    values=[]
    for part in split_top(text):
        match=re.fullmatch(r'\$(.*?)\s*=\s*"(.*)"',part,re.S)
        values.append((match[1].strip(),match[2].strip()) if match else unquote(part).strip())
    return values


def _assign(bag,fields,args):
    result=dict(bag)
    for field,value in zip(fields,args):
        if isinstance(value,tuple):key,val=value;result[key]=val
        else:result[field]=value
    return result


def _integer(value,default):
    if isinstance(value,tuple):value=value[1]
    match=re.match(r'\s*[-+]?\d+',str(value))
    return int(match[0]) if match else default


def parse(document,config):
    from ...runtime.common import make_diagram,error
    items=_items(document.cleaned);elements={};boundaries={};relations={};stack=['global'];shape_rows=4;boundary_rows=2;title='';description='';i=1
    if not items or items[0].text not in ('C4Context','C4Container','C4Component','C4Dynamic','C4Deployment'):raise error(document,0,'Expected a C4 diagram header')
    if len(items)==1:raise error(document,len(document.cleaned),'C4 requires a statement')
    variant=items[0].text
    while i<len(items):
        item=items[i];i+=1;text=item.text
        if text=='}':
            if len(stack)==1:raise error(document,item.offset,'Unexpected C4 boundary close')
            stack.pop();continue
        if text=='{':raise error(document,item.offset,'Unexpected C4 boundary opening')
        if text.startswith('title '):title=text[6:].strip();continue
        if re.match(r'accTitle\s*:',text):title=text.split(':',1)[1].strip();continue
        if text.startswith('accDescription '):description=text[15:].strip();continue
        if re.match(r'accDescr\s*:',text):description=text.split(':',1)[1].strip();continue
        if text=='accDescr' and i<len(items) and items[i].text=='{':
            i+=1;parts=[]
            while i<len(items) and items[i].text!='}':parts.append(items[i].text);i+=1
            if i==len(items):raise error(document,item.offset,'Unterminated C4 accessibility description')
            i+=1;description='\n'.join(parts);continue
        match=re.fullmatch(r'(\w+)\s*\((.*)\)',text,re.S)
        if not match:raise error(document,item.offset,'Invalid C4 statement')
        command=match[1];args=_arguments(match[2])
        if command in _SHAPES:
            if len(args)<1 or isinstance(args[0],tuple):raise error(document,item.offset,'C4 element requires an alias')
            id=args[0];kind=_SHAPES[command];label=args[1] if len(args)>1 and not isinstance(args[1],tuple) else '';old=elements.get(id);fields=('descr','sprite','tags','link') if kind.endswith('person') or kind.replace('external_','').startswith('system') else ('techn','descr','sprite','tags','link');attrs=_assign(dict(old.attributes) if old else {},fields,args[2:]);elements[id]=C4Element(id,kind,label,stack[-1],tuple(attrs.items()));continue
        if command in _BOUNDARIES:
            if len(args)<1 or isinstance(args[0],tuple):raise error(document,item.offset,'C4 boundary requires an alias')
            id=args[0];label=args[1] if len(args)>1 and not isinstance(args[1],tuple) else '';old=boundaries.get(id);kind=_BOUNDARIES[command]
            optional=args[2:]
            if command in ('Enterprise_Boundary','System_Boundary','Container_Boundary'):optional=[kind,*optional]
            fields=('type','descr','sprite','tags','link') if kind in ('node','nodeL','nodeR') else ('type','tags','link');attrs=_assign(dict(old.attributes) if old else {},fields,optional)
            if 'type' not in attrs:attrs['type']='node' if kind in ('node','nodeL','nodeR') else ''
            if kind in ('node','nodeL','nodeR'):attrs['nodeType']=kind
            boundaries[id]=C4Element(id,kind,label,stack[-1],tuple(attrs.items()),True)
            if i>=len(items) or items[i].text!='{':raise error(document,item.offset,'C4 boundary requires a body')
            i+=1;stack.append(id);continue
        if command in _RELATIONS:
            kind=_RELATIONS[command]
            if kind=='rel_index':args=args[1:];kind='rel'
            if len(args)<3 or any(isinstance(x,tuple) for x in args[:3]):raise error(document,item.offset,'C4 relation requires source, target and label')
            source,target,label=args[:3];old=relations.get((source,target));attrs=_assign(dict(old.attributes) if old else {},('techn','descr','sprite','tags','link'),args[3:]);relations[source,target]=C4Relation(source,target,label,kind,tuple(attrs.items()));continue
        if command=='UpdateElementStyle':
            if not args or isinstance(args[0],tuple):raise error(document,item.offset,'Element style requires an alias')
            id=args[0];target=elements if id in elements else boundaries
            if id in target:
                node=target[id];attrs=_assign(node.attributes,('bgColor','fontColor','borderColor','shadowing','shape','sprite','techn','legendText','legendSprite'),args[1:]);target[id]=replace(node,attributes=tuple(attrs.items()))
            continue
        if command=='UpdateRelStyle':
            if len(args)<2 or any(isinstance(x,tuple) for x in args[:2]):raise error(document,item.offset,'Relationship style requires two aliases')
            key=tuple(args[:2])
            if key in relations:
                edge=relations[key];attrs=_assign(edge.attributes,('textColor','lineColor','offsetX','offsetY'),args[2:]);relations[key]=replace(edge,attributes=tuple(attrs.items()))
            continue
        if command=='UpdateLayoutConfig':
            if args:
                n=_integer(args[0],0)
                if n>=1:shape_rows=n
            if len(args)>1:
                n=_integer(args[1],0)
                if n>=1:boundary_rows=n
            continue
        raise error(document,item.offset,'Unknown C4 declaration '+command)
    if len(stack)!=1:raise error(document,len(document.cleaned),'Unterminated C4 boundary')
    return make_diagram('c4',document,config,C4Model(variant,tuple(elements.values()),tuple(boundaries.values()),tuple(relations.values()),shape_rows,boundary_rows,title,description))


class Bounds:
    """Exact numeric state of source Bounds.insert, independent of Canvas."""
    def __init__(self,x,y,width_limit):
        self.x=self.stopx=x;self.y=self.stopy=y;self.nx=self.nsx=x;self.ny=self.nsy=y;self.count=0;self.width_limit=width_limit
    def insert(self,w,h,margin,rows,padding_x):
        self.count+=1;x=self.nsx+margin if self.nx==self.nsx else self.nsx+margin*2;y=self.ny+margin*2;right=x+w;bottom=y+h
        if x>=self.width_limit or right>=self.width_limit or self.count>rows:
            x=self.nx+margin+padding_x;y=self.nsy+margin*2;self.nsx=right=x+w;self.ny=self.nsy;self.nsy=bottom=y+h;self.count=1
        self.x=min(self.x,x);self.y=min(self.y,y);self.stopx=max(self.stopx,right);self.stopy=max(self.stopy,bottom);self.nx=min(self.nx,x);self.ny=min(self.ny,y);self.nsx=max(self.nsx,right);self.nsy=max(self.nsy,bottom)
        return x,y


def _shape(node):
    keys={'person':'person','box':'round','rounded':'round','cylinder':'cylinder','database':'cylinder','db':'cylinder','queue':'h-cyl','pipe':'h-cyl','component':'fr-rect'};attrs=dict(node.attributes)
    for key in ('shape','sprite'):
        if str(attrs.get(key,'')).lower() in keys:return keys[str(attrs[key]).lower()]
    for tag in attrs.get('tags','').split(','):
        if tag.strip().lower() in keys:return keys[tag.strip().lower()]
    if node.kind.endswith('person'):return 'person'
    if node.kind.endswith('_db'):return 'cylinder'
    if node.kind.endswith('_queue'):return 'h-cyl'
    return 'round'


async def build(diagram,painter):
    from ...runtime.common import config_dict,error
    from ...model.flowchart import Box
    model=diagram.model;config=config_dict(diagram);conf=config.get('c4') or {};margin=number(conf.get('c4ShapeMargin'),50);padding=number(conf.get('c4ShapePadding'),20);mx=number(conf.get('diagramMarginX'),50);my=number(conf.get('diagramMarginY'),10);width=number(conf.get('width'),216);viewport=painter.viewport_width;geometry={};labels={};boxes={};boundary_boxes={};boundary_labels={};node_styles={};painter.rough_enabled=False
    def font(kind,delta=0,bold=False):
        from ...model.flowchart import MermaidError
        value=conf.get(kind+'FontSize',14);family=conf.get(kind+'FontFamily',config.get('fontFamily'))
        # Only legacy boundary drawing performs JS +2/-2. Element sections
        # use CSS .75em/.82em below, not the obsolete legacy arithmetic.
        if delta:
            if delta>0 and isinstance(value,str):value=value+str(delta)
            else:
                try:value=float(value)+delta
                except (TypeError,ValueError):value=None
        try:size=painter.font_size(value,family=family)
        except MermaidError as exc:
            if exc.code!='INVALID_CONFIG':raise
            # styles.js writes through CSSOM: invalid font-size is dropped
            # whole and inherits its parent, rather than using the option default.
            size=painter.font_size('1em',family=family)
        return {'size':size,'family':family,'weight':'bold' if bold else str(conf.get(kind+'FontWeight','normal'))}

    for node in model.elements:
        attrs=dict(node.attributes);fill=attrs.get('bgColor',conf.get(node.kind+'_bg_color','#08427b'));stroke=attrs.get('borderColor',conf.get(node.kind+'_border_color','#073b6f'));color=attrs.get('fontColor','#ffffff');s=node_style(painter,config,('node','c4-shape','c4-'+node.kind),node.id,inline=(('fill',fill),('stroke',stroke),('color',color)),fill=fill,stroke=stroke,color=color);node_styles[node.id]=s
        base=node.kind.removeprefix('external_').removesuffix('_db').removesuffix('_queue');stereotype={'person':'Person','system':'Software System','container':'Container','component':'Component'}.get(base,base);type_line='['+stereotype+(': '+attrs['techn'] if attrs.get('techn') else '')+']';element_font=font(node.kind);wrap_width=max(32,width-2*padding) if conf.get('wrap',True) else None;rows=(painter.measure(node.label,width=wrap_width,style=s,html=False,**{**element_font,'weight':'bold'}),painter.measure(type_line,width=wrap_width,style=s,html=False,**{**element_font,'size':element_font['size']*.75}))
        if attrs.get('descr'):rows=(*rows,painter.measure(attrs['descr'],width=wrap_width,style=s,html=False,**{**element_font,'size':element_font['size']*.82}))
        labels[node.id]=rows;g=painter.shape_geometry(_shape(node),max(max(r.width for r in rows),width-2*padding),sum(r.height for r in rows)+3*(len(rows)-1),padding=padding);geometry[node.id]=g
    for boundary in model.boundaries:
        attrs=dict(boundary.attributes);rows=[painter.measure(boundary.label,**font('boundary',2,True))]
        if attrs.get('type'):rows.append(painter.measure('['+attrs['type']+']',**font('boundary')))
        if attrs.get('descr'):rows.append(painter.measure(attrs['descr'],**font('boundary',-2)))
        boundary_labels[boundary.id]=tuple(rows)
    # Preserve the original global boundary and recursive row packing. Limits
    # are viewport coordinates as in screen.availWidth, not an ELK fallback.
    all_boundaries=(C4Element('global','global','global','',boundary=True),*model.boundaries)
    def inside(parent_id,parent_bounds):
        children=[g for g in all_boundaries if g.parent==parent_id];limit=parent_bounds.width_limit/max(1,min(model.boundary_in_row,len(children)));current=None
        for index,boundary in enumerate(children):
            # c4Renderer.drawInsideBoundary sets a 48px image reservation for
            # any truthy sprite. The fixed svgDraw has no sprite/image paint
            # consumer: an unknown name still reserves space, not an asset.
            rows=boundary_labels.get(boundary.id,());header=sum(b.height for b in rows)+8+5*max(0,len(rows)-1);header+=48 if dict(boundary.attributes).get('sprite') else 0
            if index==0 or index%model.boundary_in_row==0:x=parent_bounds.x+mx;y=parent_bounds.stopy+my+header
            else:x=(current.stopx+mx if current.stopx!=current.x else current.x);y=current.y
            current=Bounds(x,y,limit)
            for node in model.elements:
                if node.parent!=boundary.id:continue
                g=geometry[node.id];x,y=current.insert(g.width,g.height,margin,model.shape_in_row,number(conf.get('nextLinePaddingX'),0));boxes[node.id]=Box(x,y,g.width,g.height)
            if any(n.parent==boundary.id for n in model.elements):current.stopx+=margin;current.stopy+=margin
            inside(boundary.id,current)
            if boundary.id!='global':boundary_boxes[boundary.id]=Box(current.x,current.y,current.stopx-current.x,current.stopy-current.y)
            parent_bounds.stopy=max(current.stopy+margin,parent_bounds.stopy);parent_bounds.stopx=max(current.stopx+margin,parent_bounds.stopx)
    bounds=Bounds(mx,my,viewport);inside('',bounds)
    for boundary in model.boundaries:
        b=boundary_boxes[boundary.id];attrs=dict(boundary.attributes);s=node_style(painter,config,('c4-boundary','boundary'),boundary.id,fill=attrs.get('bgColor','none'),stroke=attrs.get('borderColor','#444444'),color=attrs.get('fontColor','#444444'),effects=False);painter.rect(b.x,b.y,b.width,b.height,style=s,radius=2.5,dash=() if attrs.get('nodeType') else (7,7),id=boundary.id,role='c4-boundary');y=b.y+8+(48 if attrs.get('sprite') else 0)
        for label in boundary_labels[boundary.id]:painter.text(label,b.x+(b.width-label.width)/2,y,color=attrs.get('fontColor','#444444'),id=boundary.id);y+=label.height+5
    painter.rough_enabled=True
    for node in model.elements:
        b=boxes[node.id];g=geometry[node.id];attrs=dict(node.attributes);s=node_styles[node.id];fill=s.fill;stroke=s.stroke;color=s.text_color;transform=(1,0,0,1,b.x,b.y)
        if _shape(node)=='round':painter.rect(b.x,b.y,b.width,b.height,style=s,radius=12,id=node.id)
        elif g.paint_outline:painter.path(g.outline,style=s,transform=transform,id=node.id)
        for detail in g.details:painter.path(detail,stroke=stroke,transform=transform,id=node.id)
        for part in g.parts:
            colors={'none':'none','node':fill,'stroke':stroke,'white':'white','fill':fill};painter.path(part.path,fill=colors.get(part.fill,part.fill),stroke=stroke if part.stroke=='node' else colors.get(part.stroke,part.stroke),opacity=part.opacity,transform=transform,id=node.id)
        y=b.y+g.label_box.y
        for label in labels[node.id]:painter.text(label,b.x+g.label_box.x+(g.label_box.width-label.width)/2,y,style=s,id=node.id);y+=label.height+3
    painter.rough_enabled=False
    def intersect(id,box,toward):
        from ...geometry.shapes import shape_outline_intersection
        from ...model.flowchart import Point
        center=Point(box.x+box.width/2,box.y+box.height/2)
        if id in geometry:
            node=next(n for n in model.elements if n.id==id)
            from ._support import clip_endpoint
            port=clip_endpoint(box,Point(*toward))
            point=port if _shape(node) in ('round','fr-rect') else shape_outline_intersection(_shape(node),box,port,Point(*toward),outline=geometry[id].outline)
        else:
            from ._support import clip_endpoint
            point=clip_endpoint(box,Point(*toward))
        return point.x,point.y
    endpoints={**boundary_boxes,**boxes}
    for index,edge in enumerate(model.relations):
        if edge.source not in endpoints or edge.target not in endpoints:raise error(diagram.source,0,'C4 relationship references an unknown element','UNKNOWN_REFERENCE')
        a=endpoints[edge.source];b=endpoints[edge.target];x1,y1=intersect(edge.source,a,(b.x+b.width/2,b.y+b.height/2));x2,y2=intersect(edge.target,b,(a.x+a.width/2,a.y+a.height/2));attrs=dict(edge.attributes);stroke=attrs.get('lineColor','#444444')
        if index==0:painter.line(x1,y1,x2,y2,stroke=stroke,id='c4Rel'+str(index))
        else:painter.path(f'M {x1} {y1} Q {x1+(x2-x1)/4} {y1+(y2-y1)/2} {x2} {y2}',stroke=stroke,id='c4Rel'+str(index))
        if edge.kind!='rel_b':painter.marker(x2,y2,x2-x1,y2-y1,kind='point',color=stroke)
        if edge.kind in ('birel','rel_b'):painter.marker(x1,y1,x1-x2,y1-y2,kind='point',color=stroke)
        text=(str(index+1)+': ' if model.variant=='C4Dynamic' else '')+edge.label;label=painter.measure(text,**font('message'));ox=_integer(attrs.get('offsetX',0),0);oy=_integer(attrs.get('offsetY',0),0);x=(x1+x2)/2+ox;y=(y1+y2)/2+oy;painter.text(label,x-label.width/2,y,color=attrs.get('textColor','#444444'),id='c4Rel'+str(index),role='edge-label')
        if attrs.get('techn'):painter.text('['+attrs['techn']+']',x,y+label.height+5,italic=True,color=attrs.get('textColor','#444444'),**font('message'),id='c4Rel'+str(index),role='edge-technology')
    if model.title:painter.text(model.title,max(0,(bounds.stopx-mx)/2-4*mx),my-60,size=22,id='c4Title',role='title')
    return painter.finish(width=bounds.stopx+mx,height=bounds.stopy+my,padding=0,layout=('c4-source-bounds-grid',tuple(boxes.items()),tuple(boundary_boxes.items())))
