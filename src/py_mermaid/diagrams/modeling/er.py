"""Entity/relationship grammar and native four-column entity compartments."""
from dataclasses import dataclass,replace
import re
from ._support import label_style,statements,unquote,styles,theme,paint_edges,number,node_style,paint_title
from .class_diagram import Relation


@dataclass(frozen=True)
class Attribute:
    type:str
    name:str
    keys:tuple[str,...]=()
    comment:str=''


@dataclass(frozen=True)
class Entity:
    name:str
    id:str
    alias:str=''
    attributes:tuple[Attribute,...]=()
    classes:tuple[str,...]=('default',)
    styles:tuple=()
    parent:str|None=None


@dataclass(frozen=True)
class Group:
    id:str
    label:str
    members:tuple[str,...]=()
    parent:str|None=None
    direction:str|None=None
    classes:tuple=()
    styles:tuple=()


@dataclass(frozen=True)
class ERModel:
    entities:tuple[Entity,...]
    relations:tuple[Relation,...]
    groups:tuple[Group,...]
    definitions:tuple
    direction:str='TB'
    title:str=''
    acc_title:str=''
    acc_description:str=''


_NAME=r'(?:"[^"\n]+"|[\w\u0080-\uffff.*\-]+)'
_CARD=r'(?:one or zero|one or more|one or many|zero or one|zero or more|zero or many|only one|many\([01]\)|many|one|1\+|0\+|1|\|o|o\||\}o|o\{|\}\||\|\{|\|\||u)'
_CARDS={'|o':'zero_one','o|':'zero_one','one or zero':'zero_one','zero or one':'zero_one','}o':'zero_many','o{':'zero_many','many(0)':'zero_many','many':'zero_many','zero or more':'zero_many','zero or many':'zero_many','0+':'zero_many','}|':'one_many','|{':'one_many','one or more':'one_many','one or many':'one_many','many(1)':'one_many','1+':'one_many','||':'one','1':'one','one':'one','only one':'one','u':'parent'}
_REL=re.compile(r'^('+_NAME+r')(?:\:\:\:([\w,]+))?\s*('+_CARD+r')\s*(optionally to|to|--|\.\.|\.-|-\.)\s*('+_CARD+r')\s*('+_NAME+r')(?:\:\:\:([\w,]+))?\s*:\s*(.*)$',re.I|re.S)


def _attribute_words(text):
    words=[];i=0
    while i<len(text):
        if text[i].isspace():i+=1;continue
        start=i
        if text[i] in ('`','"'):
            quote=text[i];i+=1
            while i<len(text) and text[i]!=quote:i+=1
            if i==len(text):raise ValueError('Unterminated attribute quotation')
            i+=1;words.append(text[start:i]);continue
        if text[i]==',':words.append(',');i+=1;continue
        generic=False
        while i<len(text):
            c=text[i]
            if c=='~':generic=not generic
            if not generic and (c.isspace() or c==','):break
            i+=1
        words.append(text[start:i])
    return words


def parse(document,config):
    from ...runtime.common import make_diagram,error
    items=statements(document.cleaned,semicolon=False);entities={};groups=[];stack=[];relations=[];defs={};direction='TB';title='';acc_title='';acc_description='';i=1
    if not items or items[0].text.lower()!='erdiagram':raise error(document,0,'Expected erDiagram')
    def ensure(name,alias='',membership=True):
        name=unquote(name)
        if name not in entities:entities[name]=Entity(name,'entity-'+name+'-'+str(len(entities)),alias)
        elif alias and not entities[name].alias:entities[name]=replace(entities[name],alias=alias)
        if membership and stack:stack[-1]['members'].append(name)
        return name
    while i<len(items):
        item=items[i];text=item.text;i+=1
        if text.endswith(';') and text.lower().startswith(('style ','classdef ','subgraph ')):text=text[:-1].rstrip()
        if text.lower()=='end':
            if not stack:raise error(document,item.offset,'Unexpected subgraph end')
            group=stack.pop();assigned={n for g in groups for n in g.members};members=tuple(dict.fromkeys(n for n in group['members'] if n not in assigned));groups.append(Group(group['id'],group['label'],members,stack[-1]['id'] if stack else None,group['direction']))
            if stack:stack[-1]['members'].append(group['id'])
            continue
        match=re.fullmatch(r'subgraph\s+('+_NAME+r')(?:\s*\[(.*)\])?',text,re.I|re.S)
        if match:stack.append({'id':unquote(match[1]),'label':unquote(match[2]) if match[2] is not None else unquote(match[1]),'members':[],'direction':None});continue
        match=re.fullmatch(r'direction\s+(TB|BT|LR|RL)',text,re.I)
        if match:
            if stack:stack[-1]['direction']=match[1].upper()
            else:direction=match[1].upper()
            continue
        match=re.fullmatch(r'(classDef|class|style)\s+([\w,.*\-]+)\s+(.+)',text,re.I|re.S)
        if match:
            kind,names,value=match.groups()
            if kind.lower()=='classdef':
                for name in names.split(','):defs[name]=(*defs.get(name,()),*styles(value))
            else:
                for name in names.split(','):
                    if name in entities:
                        node=entities[name];entities[name]=replace(node,classes=(*node.classes,*value.split(','))) if kind.lower()=='class' else replace(node,styles=(*node.styles,*styles(value)))
                    for j,g in enumerate(groups):
                        if g.id==name:groups[j]=replace(g,classes=(*g.classes,*value.split(','))) if kind.lower()=='class' else replace(g,styles=(*g.styles,*styles(value)))
            continue
        if text.startswith('title '):title=text[6:].strip();continue
        if re.match(r'accTitle\s*:',text,re.I):acc_title=text.split(':',1)[1].strip();continue
        if re.match(r'accDescr\s*:',text,re.I):acc_description=text.split(':',1)[1].strip();continue
        if text.lower()=='accdescr' and i<len(items) and items[i].text=='{':
            i+=1;parts=[]
            while i<len(items) and items[i].text!='}':parts.append(items[i].text);i+=1
            if i==len(items):raise error(document,item.offset,'Unterminated description')
            i+=1;acc_description='\n'.join(parts);continue
        match=_REL.fullmatch(text)
        if match:
            a,ac,ca,line,cb,b,bc,label=match.groups();a=ensure(a);b=ensure(b)
            if ac:entities[a]=replace(entities[a],classes=(*entities[a].classes,*ac.split(',')))
            if bc:entities[b]=replace(entities[b],classes=(*entities[b].classes,*bc.split(',')))
            relations.append(Relation('erEdge'+str(len(relations)),a,b,_CARDS[ca.lower()],_CARDS[cb.lower()],line.lower() not in ('--','to'),unquote(label)));continue
        match=re.fullmatch(r'('+_NAME+r')(?:\s*\[('+_NAME+r')\])?(?:\:\:\:([\w,]+))?',text,re.S)
        if not match:raise error(document,item.offset,'Invalid ER statement: '+text)
        id=ensure(match[1],unquote(match[2]) if match[2] else '')
        if match[3]:entities[id]=replace(entities[id],classes=(*entities[id].classes,*match[3].split(',')))
        if i<len(items) and items[i].text=='{':
            i+=1;attributes=[];parts=[]
            while i<len(items) and items[i].text!='}':
                parts.append(items[i].text);i+=1
            if i==len(items):raise error(document,item.offset,'Unterminated entity')
            try:words=_attribute_words('\n'.join(parts))
            except ValueError as exc:raise error(document,item.offset,str(exc)) from exc
            j=0
            while j<len(words):
                if j+1>=len(words):raise error(document,item.offset,'Incomplete entity attribute')
                type_,name=words[j:j+2];j+=2;keys=[];comment=''
                if type_ in ('PK','FK','UK',',') or name in ('PK','FK','UK',',') or type_.startswith('"') or name.startswith('"'):raise error(document,item.offset,'Expected attribute type and name')
                if j<len(words) and words[j] in ('PK','FK','UK'):
                    keys.append(words[j]);j+=1
                    while j<len(words) and words[j]==',':
                        j+=1
                        if j==len(words) or words[j] not in ('PK','FK','UK'):raise error(document,item.offset,'Expected attribute key after comma')
                        keys.append(words[j]);j+=1
                if j<len(words) and words[j].startswith('"'):comment=words[j][1:-1];j+=1
                attributes.append(Attribute(unquote(type_),unquote(name),tuple(keys),comment))
            i+=1;entities[id]=replace(entities[id],attributes=(*entities[id].attributes,*attributes))
    if stack:raise error(document,len(document.cleaned),'Unterminated ER subgraph')
    memberships={name:g.id for g in reversed(groups) for name in g.members}
    for id,node in entities.items():entities[id]=replace(node,parent=memberships.get(id))
    # Relation endpoints recorded by DB use generated entity IDs; model retains
    # user names for stable introspection while the layout uses the same names.
    return make_diagram('er',document,config,ERModel(tuple(entities.values()),tuple(relations),tuple(groups),tuple(defs.items()),direction,title,acc_title,acc_description))


def _card(p,point,other,kind,color,id):
    import math
    x,y=point.x,point.y;dx=x-other.x;dy=y-other.y;length=math.hypot(dx,dy) or 1;ux=dx/length;uy=dy/length
    def marker(offset,name):p.marker(x-ux*offset,y-uy*offset,dx,dy,kind=name,color=color,fill='white',id=id)
    if kind=='one':marker(8,'bar');marker(14,'bar')
    elif kind=='zero_one':marker(8,'bar');marker(19,'zero')
    elif kind=='zero_many':marker(8,'crow');marker(22,'zero')
    elif kind=='one_many':marker(8,'crow');marker(19,'bar')
    elif kind=='parent':marker(8,'open')


async def build(diagram,painter):
    from ...runtime.graph import layout_graph
    from ...runtime.common import config_dict
    model=diagram.model;config=config_dict(diagram);conf=config.get('er') or {};palette=theme(config);defs=dict(model.definitions);padding=number(conf.get('entityPadding'),15);table={};nodes=[];node_styles={};color_index=0
    painter.rough_enabled=True
    group_ids={g.id for g in model.groups}
    for entity in model.entities:
        if entity.name in group_ids:continue
        s=node_style(painter,config,('node','entityBox',*entity.classes),entity.name,model.definitions,entity.styles,index=color_index);node_styles[entity.name]=s;color_index+=1
        header=painter.measure(entity.alias or entity.name,style=replace(label_style(s),font_weight='bold'));rowboxes=[];columns=[0.,0.,0.,0.]
        for a in entity.attributes:
            row=tuple(painter.measure(v,style=label_style(s)) for v in (a.type,a.name,','.join(a.keys),a.comment));rowboxes.append(row)
            for j,b in enumerate(row):columns[j]=max(columns[j],b.width)
        widths=[max(0,w)+padding if w else 0 for w in columns];w=max(number(conf.get('minEntityWidth'),100),header.width+padding*2,sum(widths)+padding*2);h=max(number(conf.get('minEntityHeight'),75),header.height+padding*2+sum(max(b.height for b in row)+padding for row in rowboxes))
        table[entity.name]=(header,rowboxes,widths);nodes.append({'id':entity.name,'width':w,'height':h,'parent':entity.parent})
    edges=[]
    for edge in model.relations:
        m=painter.measure(edge.label);edges.append({'id':edge.id,'source':edge.source,'target':edge.target,'label':edge.label,'label_width':m.width,'label_height':m.height})
    parents=[{'id':g.id,'parent':g.parent,'padding':8,'title_height':painter.measure(g.label).height+12,'direction':g.direction} for g in model.groups]
    layout=await layout_graph(nodes,edges,config=config,direction=model.direction,parents=parents,node_spacing=number(conf.get('nodeSpacing'),50),rank_spacing=number(conf.get('rankSpacing'),50))
    for g in model.groups:
        box=layout.groups[g.id];s=node_style(painter,config,('cluster',*g.classes),g.id,model.definitions,g.styles,fill=palette['group'],stroke=palette['groupStroke']);painter.rect(box.x,box.y,box.width,box.height,style=s,id=g.id,role='group');painter.text(g.label,box.x+8,box.y+4,style=label_style(s),id=g.id)
    # ER cardinalities are two independent marks, not UML relationship arrows.
    plain=[replace(e,start_marker='none',end_marker='none') for e in model.relations];paint_edges(painter,layout,plain,palette)
    for edge in model.relations:
        points=layout.edges.get(edge.id,())
        if len(points)>1:
            # Compound routes may repeat terminal control points. The marker
            # tangent is the first real route segment, not a zero-length leg.
            first=next((point for point in points[1:] if point!=points[0]),points[1])
            last=next((point for point in reversed(points[:-1]) if point!=points[-1]),points[-2])
            _card(painter,points[0],first,edge.start_marker,palette['edge'],edge.id);_card(painter,points[-1],last,edge.end_marker,palette['edge'],edge.id)
    for entity in model.entities:
        if entity.name not in table:continue
        box=layout.nodes[entity.name];head,rows,widths=table[entity.name];s=node_styles[entity.name];stroke=s.stroke;color=s.text_color;painter.rect(box.x,box.y,box.width,box.height,style=s,id=entity.name);painter.text(head,box.x+(box.width-head.width)/2,box.y+padding,style=s,id=entity.name)
        y=box.y+head.height+padding*2;painter.line(box.x,y,box.x+box.width,y,stroke=stroke,id=entity.name,role='header-divider')
        for index,row in enumerate(rows):
            height=max(b.height for b in row)+padding;x=box.x+padding
            if index%2:painter.rect(box.x,y,box.width,height,fill=(config.get('themeVariables') or {}).get('attributeBackgroundColorEven',palette['fill']),stroke='none',id=entity.name,role='attribute-background')
            for j,b in enumerate(row):
                if widths[j]:painter.text(b,x,y+padding/2,style=s,id=entity.name,role='attribute');x+=widths[j]
                if j<3 and widths[j]:painter.line(x-padding/2,y,x-padding/2,y+height,stroke=stroke,id=entity.name,role='attribute-column')
            y+=height
    paint_title(diagram,painter,layout,'erDiagramTitleText',number(conf.get('titleTopMargin'),25))
    return painter.finish(layout=layout,padding=number(conf.get('diagramPadding'),20))
