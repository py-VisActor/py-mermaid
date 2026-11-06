"""State grammar, compound/concurrent state documents and native state paint."""
from dataclasses import dataclass,replace
import re
from ._support import label_style,statements,styles,unquote,theme,paint_edges,draw_note,number,node_style,paint_title
from .class_diagram import Relation,Note


@dataclass(frozen=True)
class State:
    id:str
    labels:tuple[str,...]=()
    kind:str='default'
    parent:str|None=None
    classes:tuple[str,...]=()
    styles:tuple=()
    direction:str='TB'
    group:bool=False
    region:bool=False


@dataclass(frozen=True)
class StateNote:
    id:str
    target:str
    text:str
    side:str='right of'
    parent:str|None=None


@dataclass(frozen=True)
class StateModel:
    states:tuple[State,...]
    relations:tuple[Relation,...]
    notes:tuple[StateNote,...]
    definitions:tuple
    direction:str='TB'
    hide_empty:bool=False
    scale:float|None=None
    acc_title:str=''
    acc_description:str=''


def parse(document,config):
    from ...runtime.common import make_diagram,error,sanitize_text
    items=statements(document.cleaned,semicolon=False);nodes={};relations=[];notes=[];defs={};stack=[];region_counts={};direction='TB';hide=False;scale=None;acc_title='';acc_description='';i=1
    if not items or items[0].text.lower() not in ('statediagram','statediagram-v2'):raise error(document,0,'Expected stateDiagram')
    def parent():return stack[-1]['region'] or stack[-1]['id'] if stack else None
    def ensure(raw,kind='default',label=None,first=True):
        match=re.fullmatch(r'(.+?)(?:\:\:\:(\w+))?',raw.strip());id=match[1].strip();classes=(match[2],) if match[2] else ()
        if id=='[*]':id=(parent() or 'root')+('_start' if first else '_end');kind='start' if first else 'end'
        if id not in nodes:nodes[id]=State(id,(),kind,parent(),classes)
        else:
            n=nodes[id];nodes[id]=replace(n,kind=kind if kind!='default' else n.kind,classes=(*n.classes,*classes))
        if label is not None:nodes[id]=replace(nodes[id],labels=(*nodes[id].labels,sanitize_text(label.strip(),config)))
        return id
    def open_region(id,ordinal):
        rid=id+'::region'+str(ordinal);nodes[rid]=State(rid,kind='divider',parent=id,group=True,region=True)
        return rid
    while i<len(items):
        token=items[i];text=token.text;i+=1;lower=text.lower()
        if text=='}':
            if not stack:raise error(document,token.offset,'Unexpected state close')
            stack.pop();continue
        if text=='{':raise error(document,token.offset,'Unexpected state block')
        if text=='--':
            if not stack:raise error(document,token.offset,'Concurrency divider requires a composite')
            frame=stack[-1];id=frame['id'];count=region_counts.get(id,0)
            if not count:
                first=open_region(id,0)
                for key,n in tuple(nodes.items()):
                    if n.parent==id and key!=first:nodes[key]=replace(n,parent=first)
            count+=1;region_counts[id]=count;frame['region']=open_region(id,count);continue
        if lower=='hide empty description':hide=True;continue
        match=re.fullmatch(r'scale\s+(\d+)\s+width',text,re.I)
        if match:scale=float(match[1]);continue
        match=re.fullmatch(r'direction\s+(TB|BT|LR|RL)',text,re.I)
        if match:
            if stack:nodes[stack[-1]['id']]=replace(nodes[stack[-1]['id']],direction=match[1].upper())
            else:direction=match[1].upper()
            continue
        match=re.fullmatch(r'(classDef|class|style)\s+([\w,]+)\s+(.+)',text,re.I|re.S)
        if match:
            cmd,ids,value=match.groups()
            for id in ids.split(','):
                if cmd.lower()=='classdef':defs[id]=styles(value.replace(';',''));continue
                if cmd.lower()=='style':ensure(id);nodes[id]=replace(nodes[id],styles=styles(value.replace(';','')))
                else:ensure(id);nodes[id]=replace(nodes[id],classes=(*nodes[id].classes,*value.split(',')))
            continue
        if re.match(r'accTitle\s*:',text,re.I):acc_title=text.split(':',1)[1].strip();continue
        if re.match(r'accDescr\s*:',text,re.I):acc_description=text.split(':',1)[1].strip();continue
        if lower=='accdescr' and i<len(items) and items[i].text=='{':
            i+=1;parts=[]
            while i<len(items) and items[i].text!='}':parts.append(items[i].text);i+=1
            if i==len(items):raise error(document,token.offset,'Unterminated accessibility description')
            i+=1;acc_description='\n'.join(parts);continue
        if lower.startswith('click '):
            if not re.fullmatch(r'click\s+\S+\s+(?:href\s+)?"[^"]*"(?:\s+"[^"]*")?',text,re.I):raise error(document,token.offset,'Invalid state click statement')
            continue
        match=re.fullmatch(r'note\s+(left of|right of)\s+([^:\s]+)(?:\s*:\s*(.*))?',text,re.I|re.S)
        if match:
            side,target,value=match.groups();ensure(target)
            if value is None:
                parts=[]
                while i<len(items) and items[i].text.lower()!='end note':parts.append(items[i].text);i+=1
                if i==len(items):raise error(document,token.offset,'Unterminated state note')
                i+=1;value='\n'.join(parts).strip()
            notes.append(StateNote(target+'----note',target,sanitize_text(value,config),side.lower(),nodes[target].parent));continue
        match=re.fullmatch(r'note\s+"(.*)"\s+as\s+(\S+)',text,re.I|re.S)
        if match:
            # Grammar accepts standalone floating notes, but no semantic action
            # creates them in the fixed DB. Preserve that source no-op.
            continue
        if '-->' in text:
            match=re.fullmatch(r'([^\s:]+(?:::\:\w+)?)\s*-->\s*([^\s:]+(?:::\:\w+)?)(?:\s*:\s*(.*))?',text,re.S)
            if not match:raise error(document,token.offset,'Invalid state transition')
            a=ensure(match[1],first=True);b=ensure(match[2],first=False);relations.append(Relation('stateEdge'+str(len(relations)),a,b,end_marker='point',label=(match[3] or '').strip()));continue
        match=re.fullmatch(r'state\s+(?:"(.*)"\s+as\s+([^\s]+)|([^\s]+))(?:\s+(?:<<|\[\[)(fork|join|choice)(?:>>|\]\]))?',text,re.I|re.S)
        if match:
            label,alias,bare,kind=match.groups();extra=None
            if alias and ':' in alias:alias,extra=alias.split(':',1)
            id=ensure(alias or bare,kind.lower() if kind else 'default',label)
            if extra is not None:ensure(id,label=extra)
            if i<len(items) and items[i].text=='{':nodes[id]=replace(nodes[id],group=True);stack.append({'id':id,'region':None});i+=1
            continue
        match=re.fullmatch(r'([^:\s]+)(?:\s*:\s*(.*))?',text,re.S)
        if match:ensure(match[1],label=match[2]);continue
        raise error(document,token.offset,'Invalid state statement')
    if stack:raise error(document,len(document.cleaned),'Unterminated composite state')
    for node in nodes.values():
        if node.group and len(node.labels)>1:raise error(document,0,'Group nodes can only have a label','INVALID_STATE_DESCRIPTION')
    return make_diagram('stateDiagram',document,config,StateModel(tuple(nodes.values()),tuple(relations),tuple(notes),tuple(defs.items()),direction,hide,scale,acc_title,acc_description))


async def build(diagram,painter):
    from ...runtime.graph import layout_graph
    from ...runtime.common import config_dict
    model=diagram.model;config=config_dict(diagram);conf=config.get('state') or {};palette=theme(config);defs=dict(model.definitions);nodes=[];parents=[];labels={};padding=number(conf.get('padding'),16);node_styles={};group_slots={};slot=0;by_id={s.id:s for s in model.states};painter.rough_enabled=True
    def group_slot(state):
        nonlocal slot
        if state.id in group_slots:return group_slots[state.id]
        if state.region and state.parent in by_id:value=group_slot(by_id[state.parent])
        else:
            value=slot;slot+=1
            if state.styles or any(defs.get(c) for c in state.classes):value=None
        group_slots[state.id]=value;return value
    for state in model.states:
        tv=config.get('themeVariables') or {};classes=('cluster','statediagram-cluster','default',*state.classes) if state.group else ('node','statediagram-state','default',*state.classes);s=node_style(painter,config,classes,state.id,model.definitions,state.styles,fill=tv.get('compositeBackground',palette['group']) if state.group else palette['fill'],stroke=palette['groupStroke'] if state.group else palette['stroke'],index=group_slot(state) if state.group else None);node_styles[state.id]=s
        label=state.labels[0] if state.labels else state.id
        if state.group:parents.append({'id':state.id,'parent':state.parent,'direction':state.direction,'padding':padding,'title_height':0 if state.region else painter.measure(label).height+padding});continue
        boxes=tuple(painter.measure(v,style=replace(label_style(s),font_weight='bold' if i==0 and len(state.labels)>1 else s.font_weight),label_kind='markdown') for i,v in enumerate(state.labels or (state.id,)));labels[state.id]=boxes
        if state.kind in ('start','end'):w=h=14.
        elif state.kind in ('fork','join'):w,h=(70.,10.) if model.direction in ('TB','BT') else (10.,70.)
        elif state.kind=='choice':w=h=34.
        else:w=max(60,max(b.width for b in boxes)+padding*2);h=max(35,sum(b.height for b in boxes)+padding*2)
        nodes.append({'id':state.id,'width':w,'height':h,'parent':state.parent})
    edges=list(model.relations)
    for note in model.notes:
        b=painter.measure(note.text,width=200);nodes.append({'id':note.id,'width':b.width+24,'height':b.height+24,'parent':note.parent});a,b=(note.id,note.target) if note.side=='left of' else (note.target,note.id);edges.append(Relation('noteEdge'+note.id,a,b,dashed=True))
    edge_data=[]
    for e in edges:
        label=painter.measure(e.label) if e.label else None;edge_data.append({'id':e.id,'source':e.source,'target':e.target,'label':e.label,'label_width':label.width if label else 0,'label_height':label.height if label else 0})
    layout=await layout_graph(nodes,edge_data,config=config,direction=model.direction,parents=parents,node_spacing=number(conf.get('nodeSpacing'),50),rank_spacing=number(conf.get('rankSpacing'),50))
    for state in model.states:
        if not state.group:continue
        b=layout.groups[state.id];s=node_styles[state.id];painter.rect(b.x,b.y,b.width,b.height,style=s,radius=0 if state.region else 5,dash=(5,5) if state.region else (),id=state.id,role='concurrency-region' if state.region else 'composite-state')
        if not state.region:
            title=painter.measure(state.labels[0] if state.labels else state.id,style=label_style(s),label_kind='markdown');inner=replace(s,fill=(config.get('themeVariables') or {}).get('compositeBackground',palette['group']));painter.rect(b.x+1,b.y+title.height+padding,b.width-2,max(0,b.height-title.height-padding-1),style=inner,radius=3,id=state.id,role='composite-body');painter.text(title,b.x+padding,b.y+4,style=s,id=state.id)
    layout=paint_edges(painter,layout,edges,palette,{s.id:('circle' if s.kind in ('start','end') else 'diamond') for s in model.states if s.kind in ('start','end','choice')})
    for state in model.states:
        if state.group:continue
        b=layout.nodes[state.id];s=node_styles[state.id];fill=s.fill;stroke=s.stroke;color=s.text_color
        if state.kind in ('start','end'):
            if state.kind=='end':painter.ellipse(b.x+b.width/2,b.y+b.height/2,b.width/2,b.height/2,fill=fill,stroke=stroke,id=state.id)
            painter.ellipse(b.x+b.width/2,b.y+b.height/2,b.width/2-(3 if state.kind=='end' else 0),b.height/2-(3 if state.kind=='end' else 0),fill=stroke,stroke=stroke,id=state.id);continue
        if state.kind in ('fork','join'):painter.rect(b.x,b.y,b.width,b.height,fill=stroke,stroke=stroke,id=state.id);continue
        if state.kind=='choice':painter.polygon(((b.x+b.width/2,b.y),(b.x+b.width,b.y+b.height/2),(b.x+b.width/2,b.y+b.height),(b.x,b.y+b.height/2)),fill=fill,stroke=stroke,id=state.id);continue
        painter.rect(b.x,b.y,b.width,b.height,style=s,radius=5,id=state.id);y=b.y+padding
        for i,label in enumerate(labels[state.id]):
            painter.text(label,b.x+padding if i else b.x+(b.width-label.width)/2,y,style=s,id=state.id,role='state-description' if i else 'label');y+=label.height
            if i==0 and len(labels[state.id])>1:painter.line(b.x,y+3,b.x+b.width,y+3,stroke=stroke,id=state.id,role='description-divider');y+=6
    for note in model.notes:
        b=layout.nodes[note.id];draw_note(painter,b.x,b.y,b.width,b.height,note.text,palette,note.id)
    paint_title(diagram,painter,layout,'statediagramTitleText',number(conf.get('titleTopMargin'),25))
    return painter.finish(layout=layout,padding=number(conf.get('diagramPadding'),8))
