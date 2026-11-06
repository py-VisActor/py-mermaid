"""SysML requirement/element records, typed relations and compartment paint."""
from dataclasses import dataclass,replace
import re
from ._support import label_style,statements,unquote,styles,theme,paint_edges,number,node_style,paint_title
from .class_diagram import Relation


@dataclass(frozen=True)
class Requirement:
    name:str
    type:str
    requirement_id:str=''
    text:str=''
    risk:str=''
    verify_method:str=''
    classes:tuple=('default',)
    styles:tuple=()


@dataclass(frozen=True)
class Element:
    name:str
    type:str=''
    doc_ref:str=''
    classes:tuple=('default',)
    styles:tuple=()


@dataclass(frozen=True)
class RequirementModel:
    requirements:tuple[Requirement,...]
    elements:tuple[Element,...]
    relations:tuple[Relation,...]
    definitions:tuple
    direction:str='TB'
    acc_title:str=''
    acc_description:str=''


_TYPES={'requirement':'Requirement','functionalrequirement':'Functional Requirement','interfacerequirement':'Interface Requirement','performancerequirement':'Performance Requirement','physicalrequirement':'Physical Requirement','designconstraint':'Design Constraint'}
_RELATIONS=('contains','copies','derives','satisfies','verifies','refines','traces')


def parse(document,config):
    from ...runtime.common import make_diagram,error
    items=statements(document.cleaned,semicolon=False);requirements={};elements={};relations=[];defs={};direction='TB';acc_title='';acc_description='';i=0;header=False
    def fields(target,default):
        nonlocal i
        if i>=len(items) or items[i].text!='{':raise error(document,len(document.cleaned),'Expected requirement block')
        i+=1;result={}
        while i<len(items) and items[i].text!='}':
            item=items[i];i+=1
            if ':' not in item.text:raise error(document,item.offset,'Expected a property and colon')
            name,value=item.text.split(':',1);name=name.strip().lower();value=unquote(value)
            if name not in target:raise error(document,item.offset,'Invalid requirement property '+name)
            if name=='risk':
                if value.lower() not in ('low','medium','high'):raise error(document,item.offset,'Invalid requirement risk')
                value=value.capitalize()
            if name=='verifymethod':
                if value.lower() not in ('analysis','demonstration','inspection','test'):raise error(document,item.offset,'Invalid verify method')
                value=value.capitalize()
            # Right-recursive Jison actions run from the last field backwards:
            # the first duplicate field in source wins.
            result.setdefault(target[name],value)
        if i>=len(items):raise error(document,len(document.cleaned),'Unterminated requirement body')
        i+=1;return {**default,**result}
    while i<len(items):
        item=items[i];i+=1;text=item.text;lower=text.lower()
        if lower=='requirementdiagram':
            if header:raise error(document,item.offset,'Duplicate requirementDiagram header')
            header=True;continue
        if re.match(r'accTitle\s*:',text,re.I):acc_title=text.split(':',1)[1].strip();continue
        if re.match(r'accDescr\s*:',text,re.I):acc_description=text.split(':',1)[1].strip();continue
        if lower=='accdescr' and i<len(items) and items[i].text=='{':
            i+=1;parts=[]
            while i<len(items) and items[i].text!='}':parts.append(items[i].text);i+=1
            if i==len(items):raise error(document,item.offset,'Unterminated accessibility description')
            i+=1;acc_description='\n'.join(parts).strip();continue
        if not header:raise error(document,item.offset,'Expected requirementDiagram')
        if lower.startswith('#'):continue
        match=re.fullmatch(r'direction\s+(TB|BT|LR|RL)',text,re.I)
        if match:direction=match[1].upper();continue
        match=re.fullmatch(r'(requirement|functionalRequirement|interfaceRequirement|performanceRequirement|physicalRequirement|designConstraint|element)\s+(.+?)(?:\:\:\:([\w,]+))?',text,re.I|re.S)
        if match:
            kind,name,classes=match.groups()
            reserved={'requirementdiagram','id','text','risk','verifymethod','requirement','functionalrequirement','interfacerequirement','performancerequirement','physicalrequirement','designconstraint','low','medium','high','analysis','demonstration','inspection','test','element','contains','copies','derives','satisfies','verifies','refines','traces','type','docref','style','classdef','class'}
            if not name.startswith(chr(34)) and name.split()[0].lower() in reserved:raise error(document,item.offset,'Reserved keyword cannot be a requirement identifier')
            name=unquote(name)
            if kind.lower()=='element':
                values=fields({'type':'type','docref':'doc_ref'},{});node=elements.setdefault(name,Element(name,**values))
                if classes:elements[name]=replace(node,classes=(*node.classes,*classes.split(',')))
            else:
                values=fields({'id':'requirement_id','text':'text','risk':'risk','verifymethod':'verify_method'},{});node=requirements.setdefault(name,Requirement(name,_TYPES[kind.lower()],**values))
                if classes:requirements[name]=replace(node,classes=(*node.classes,*classes.split(',')))
            continue
        match=re.fullmatch(r'(.+?)\s*(<-|-)\s*('+'|'.join(_RELATIONS)+r')\s*(->|-)\s*(.+)',text,re.I|re.S)
        if match:
            a,left,kind,right,b=match.groups();a=unquote(a);b=unquote(b)
            if (left,right) not in (('<-','-'),('-','->')):raise error(document,item.offset,'Invalid requirement relation direction')
            if left=='<-':a,b=b,a
            relations.append(Relation('requirementEdge'+str(len(relations)),a,b,'none','none' if kind.lower()=='contains' else 'open',kind.lower()!='contains','&lt;&lt;'+kind.lower()+'&gt;&gt;'));continue
        match=re.fullmatch(r'(classDef|class|style)\s+(.+?)\s+(.+)',text,re.I|re.S)
        if match:
            cmd,names,value=match.groups()
            for id in (unquote(n.strip()) for n in names.split(',')):
                if cmd.lower()=='classdef':defs[id]=(*defs.get(id,()),*styles(value));continue
                collection=requirements if id in requirements else elements
                if id in collection:
                    node=collection[id];collection[id]=replace(node,classes=(*node.classes,*value.split(','))) if cmd.lower()=='class' else replace(node,styles=(*node.styles,*styles(value)))
            continue
        match=re.fullmatch(r'(.+?)\:\:\:([\w,]+)',text)
        if match:
            id=unquote(match[1]);collection=requirements if id in requirements else elements
            if id in collection:collection[id]=replace(collection[id],classes=(*collection[id].classes,*match[2].split(',')))
            continue
        raise error(document,item.offset,'Invalid requirement statement: '+text)
    if not header:raise error(document,0,'Missing requirementDiagram')
    return make_diagram('requirement',document,config,RequirementModel(tuple(requirements.values()),tuple(elements.values()),tuple(relations),tuple(defs.items()),direction,acc_title,acc_description))


async def build(diagram,painter):
    from ...runtime.graph import layout_graph
    from ...runtime.common import config_dict,error
    model=diagram.model;config=config_dict(diagram);conf=config.get('requirement') or {};palette=theme(config);padding=10.;defs=dict(model.definitions);boxes={};nodes=[];known=set();node_styles={}
    painter.rough_enabled=True
    for index,node in enumerate((*model.requirements,*model.elements)):
        tv=config.get('themeVariables') or {};s=node_style(painter,config,('node','reqBox',*node.classes),node.name,model.definitions,node.styles,fill=tv.get('requirementBackground',palette['fill']),stroke=tv.get('requirementBorderColor',palette['stroke']),index=index);node_styles[node.name]=s
        if isinstance(node,Requirement):
            stereotype='&lt;&lt;'+node.type+'&gt;&gt;';body=tuple(prefix+value for prefix,value in (('ID: ',node.requirement_id),('Text: ',node.text),('Risk: ',node.risk),('Verification: ',node.verify_method)) if value)
        else:stereotype='&lt;&lt;Element&gt;&gt;';body=tuple(prefix+value for prefix,value in (('Type: ',node.type),('Doc Ref: ',node.doc_ref)) if value)
        lines=(stereotype,node.name,*body);measured=tuple(painter.measure(text,style=replace(label_style(s),font_weight='bold' if i==1 else s.font_weight)) for i,text in enumerate(lines));w=max(m.width for m in measured)+padding*2;h=sum(m.height for m in measured)+padding*2+20;boxes[node.name]=measured;known.add(node.name);nodes.append({'id':node.name,'width':w,'height':h})
    edges=[]
    for e in model.relations:
        if e.source not in known or e.target not in known:raise error(diagram.source,0,'Requirement relation references an undeclared object','UNKNOWN_REFERENCE')
        label=painter.measure(e.label);edges.append({'id':e.id,'source':e.source,'target':e.target,'label':e.label,'label_width':label.width,'label_height':label.height})
    layout=await layout_graph(nodes,edges,config=config,direction=model.direction,node_spacing=number(conf.get('nodeSpacing'),50),rank_spacing=number(conf.get('rankSpacing'),50));paint_edges(painter,layout,model.relations,palette)
    for edge in model.relations:
        if edge.label!='&lt;&lt;contains&gt;&gt;':continue
        points=layout.edges.get(edge.id,())
        if len(points)>1:
            import math
            a,b=points[:2];dx=b.x-a.x;dy=b.y-a.y;length=math.hypot(dx,dy) or 1;cx=a.x+dx/length*10;cy=a.y+dy/length*10;painter.ellipse(cx,cy,9,9,fill='none',stroke=palette['edge'],id=edge.id,role='containment-marker');painter.line(cx-9,cy,cx+9,cy,stroke=palette['edge'],id=edge.id);painter.line(cx,cy-9,cx,cy+9,stroke=palette['edge'],id=edge.id)
    for node in (*model.requirements,*model.elements):
        b=layout.nodes[node.name];s=node_styles[node.name];stroke=s.stroke;color=s.text_color;painter.rect(b.x,b.y,b.width,b.height,style=s,id=node.name);y=b.y+padding
        for i,m in enumerate(boxes[node.name]):
            painter.text(m,b.x+(b.width-m.width)/2 if i<2 else b.x+padding,y,style=s,id=node.name,role='requirement-name' if i==1 else 'requirement-property');y+=m.height
            if i==1:painter.line(b.x,y+10,b.x+b.width,y+10,style=s,id=node.name,role='compartment-divider');y+=20
    paint_title(diagram,painter,layout,'requirementDiagramTitleText',number(conf.get('titleTopMargin'),25))
    return painter.finish(layout=layout,padding=number(conf.get('diagramPadding'),8))
