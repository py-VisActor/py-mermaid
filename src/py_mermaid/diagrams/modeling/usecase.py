"""Usecase Chevrotain grammar semantics translated to native values and paint.

The lexer retains token offsets, metadata/JSON brace nesting, explicit edge IDs
and declaration/reference distinction. No callbacks or animation are executed.
"""
from dataclasses import dataclass,replace
import json
import re
from ._support import label_style,styles,theme,paint_edges,draw_note,number,node_style,paint_title
from .class_diagram import Relation


@dataclass(frozen=True)
class Token:
    text:str
    offset:int
    kind:str='word'


@dataclass(frozen=True)
class JsonObject:
    properties:tuple


@dataclass(frozen=True)
class UsecaseNode:
    id:str
    label:str
    kind:str='usecase'
    shape:str='ellipse'
    label_kind:str='text'
    parent:str|None=None
    stereotype:str=''
    classes:tuple=()
    styles:tuple=()
    metadata:tuple=()
    value:object=None
    generated:bool=False


@dataclass(frozen=True)
class Boundary:
    id:str
    label:str
    shape:str='rect'
    label_kind:str='text'
    members:tuple=()
    classes:tuple=()
    styles:tuple=()


@dataclass(frozen=True)
class UsecaseEdge:
    id:str
    source:str
    target:str
    start_marker:str='none'
    end_marker:str='none'
    dashed:bool=False
    label:str=''
    source_label:str=''
    target_label:str=''
    styles:tuple=()
    classes:tuple=()
    kind:str='association'
    min_length:int=1
    explicit:bool=False
    label_kind:str='text'


@dataclass(frozen=True)
class UsecaseModel:
    nodes:tuple[UsecaseNode,...]
    boundaries:tuple[Boundary,...]
    edges:tuple[UsecaseEdge,...]
    definitions:tuple
    direction:str='LR'
    acc_title:str=''
    acc_description:str=''


_OP=re.compile(r'--\|>|\.\.>|<--+|--+>|--o|o--|--x|x--|--+|:::|<<|>>|@\{')


def _lex(document):
    from ...runtime.common import error
    source=document.cleaned;i=0;tokens=[]
    while i<len(source):
        c=source[i];start=i
        if c in ' \t':i+=1;continue
        if c in '\r\n':
            if source.startswith('\r\n',i):i+=1
            tokens.append(Token('\n',start,'newline'));i+=1;continue
        if source.startswith('%%',i) and not source[source.rfind('\n',0,i)+1:i].strip():
            end=source.find('\n',i);i=end if end>=0 else len(source);continue
        if source.startswith('"`',i):
            end=source.find('`"',i+2)
            if end<0:raise error(document,i,'Unterminated Markdown label')
            tokens.append(Token(source[i+2:end],i,'markdown'));i=end+2;continue
        if c in ('"',"'"):
            end=source.find(c,i+1)
            if end<0 or '\n' in source[i+1:end] or '\r' in source[i+1:end]:raise error(document,i,'Unterminated quoted label')
            tokens.append(Token(source[i+1:end],i,'string'));i=end+1;continue
        # JSON declaration is the sole context with JSON escape semantics.
        match=re.match(r'json[\t ]+(\w+)[\t ]*@[\t ]*(?=\{)',source[i:])
        if match:
            raw_start=i+len(match[0]);decoder=json.JSONDecoder(parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
            try:value,end=decoder.raw_decode(source[raw_start:])
            except (ValueError,json.JSONDecodeError) as exc:raise error(document,raw_start+getattr(exc,'pos',0),'Invalid usecase JSON') from exc
            if not isinstance(value,dict):raise error(document,raw_start,'JSON declaration requires an object')
            tokens.append(Token(match[1],i,'json-id'));tokens.append(Token(source[raw_start:raw_start+end],raw_start,'json'));i=raw_start+end;continue
        if i==0 and source.startswith('usecase-beta',i):
            tokens.append(Token('usecase-beta',i));i+=len('usecase-beta');continue
        match=_OP.match(source,i)
        if match:tokens.append(Token(match[0],i,'operator'));i=match.end();continue
        match=re.match(r'\w+',source[i:],re.ASCII)
        if match:tokens.append(Token(match[0],i));i+=len(match[0]);continue
        tokens.append(Token(c,i,'punctuation'));i+=1
    tokens.append(Token('EOF',len(source),'eof'));return tokens


def _label(tokens,source=None):
    if len(tokens)==1 and tokens[0].kind in ('string','markdown'):return tokens[0].text,'markdown' if tokens[0].kind=='markdown' else 'text'
    if source is not None and tokens:return source[tokens[0].offset:tokens[-1].offset+len(tokens[-1].text)].strip(),'text'
    return ' '.join(t.text for t in tokens).strip(),'text'


def _freeze(value):
    if isinstance(value,dict):return JsonObject(tuple((k,_freeze(v)) for k,v in value.items()))
    if isinstance(value,list):return tuple(_freeze(v) for v in value)
    return value


def parse(document,config):
    from ...runtime.common import make_diagram,error
    ts=_lex(document);i=0;nodes={};boundaries={};edge_drafts=[];assignments=[];class_assignments=[];style_assignments=[];defs={};notes=[];direction='LR';acc_title='';acc_description='';parent=None;generated_origins={};counter=0
    def take(value=None):
        nonlocal i
        t=ts[i];i+=1
        if value is not None and t.text!=value:raise error(document,t.offset,'Expected '+value+', got '+t.text)
        return t
    def at(value):return ts[i].text==value
    def endline():
        if not at('\n') and not at('EOF'):raise error(document,ts[i].offset,'Expected end of usecase statement')
        if at('\n'):take()
    def ident():
        t=take()
        if t.kind not in ('word','string','markdown'):raise error(document,t.offset,'Expected an identifier')
        id=t.text if t.kind=='word' else re.sub(r'\W','_',t.text,flags=re.ASCII)
        if t.kind!='word':
            if id in generated_origins and generated_origins[id]!=t.text:raise error(document,t.offset,'Generated usecase ID collision')
            generated_origins[id]=t.text
        return id,t
    def metadata():
        take('@{');values=[]
        while at('\n'):take()
        while not at('}'):
            if at('EOF'):raise error(document,ts[i].offset,'Unterminated usecase metadata')
            key=take()
            if key.kind not in ('word','string'):raise error(document,key.offset,'Invalid metadata key')
            take(':');value=take()
            if value.kind not in ('word','string'):raise error(document,value.offset,'Invalid metadata value')
            values.append((key.text,True if value.text=='true' and value.kind=='word' else False if value.text=='false' and value.kind=='word' else value.text))
            if at(','):take()
            elif not at('\n') and not at('}'):raise error(document,ts[i].offset,'Expected metadata separator')
            while at('\n'):take()
        take('}');return tuple(values)
    def suffix():
        classes=[]
        if at(':::'):
            take();classes.append(take().text)
            while at(','):take();classes.append(take().text)
        return tuple(classes)
    def entity(kind='usecase',declare=False):
        id,t=ident();label=t.text;label_kind='markdown' if t.kind=='markdown' else 'text';shape='ellipse';explicit=t.kind!='word'
        if at('(') or at('['):
            opener=take().text;closer=')' if opener=='(' else ']';parts=[]
            while not at(closer):
                if at('EOF') or at('\n'):raise error(document,ts[i].offset,'Unterminated usecase label')
                parts.append(take())
            take(closer);label,label_kind=_label(parts,document.cleaned);shape='rect' if opener=='[' else 'ellipse';explicit=True
        meta=metadata() if at('@{') else ();stereotype=''
        if at('<<'):
            take();parts=[]
            while not at('>>'):
                if at('\n') or at('EOF'):raise error(document,ts[i].offset,'Unterminated stereotype')
                parts.append(take())
            take('>>');stereotype=' '.join(p.text for p in parts).strip()
        classes=suffix();declaration=declare or explicit or bool(meta) or bool(stereotype)
        if parent and not declaration:declaration=True
        draft=UsecaseNode(id,label,kind,shape,label_kind,parent,stereotype,classes,metadata=meta,generated=t.kind!='word')
        if declaration:register(draft,t.offset)
        return draft,declaration,t.offset
    def register(draft,offset):
        if draft.id in boundaries:raise error(document,offset,'Symbol already declared as a system boundary')
        old=nodes.get(draft.id)
        if old:
            if old.kind!=draft.kind:raise error(document,offset,'Conflicting usecase symbol kinds')
            if old.generated!=draft.generated or old.generated and old.label!=draft.label:raise error(document,offset,'Generated and explicit ID collision')
            if old.parent and draft.parent and old.parent!=draft.parent:raise error(document,offset,'Usecase belongs to conflicting boundaries')
            if old.label!=old.id and draft.label!=draft.id and old.label!=draft.label:raise error(document,offset,'Conflicting usecase labels')
            if old.shape!=draft.shape:raise error(document,offset,'Conflicting usecase shapes')
            meta=dict(old.metadata)
            for key,value in draft.metadata:
                if key in meta and meta[key]!=value:raise error(document,offset,'Conflicting declaration metadata')
                meta[key]=value
            nodes[draft.id]=replace(old,label=draft.label if draft.label!=draft.id else old.label,label_kind=draft.label_kind if draft.label!=draft.id else old.label_kind,parent=old.parent or draft.parent,stereotype=old.stereotype or draft.stereotype,classes=tuple(dict.fromkeys((*old.classes,*draft.classes))),metadata=tuple(meta.items()))
        else:nodes[draft.id]=draft
    if take().text!='usecase-beta':raise error(document,0,'Expected usecase-beta')
    endline()
    while not at('EOF'):
        if at('\n'):take();continue
        start=ts[i]
        if start.text=='end':
            take()
            if parent is None:raise error(document,start.offset,'Unexpected boundary end')
            parent=None;endline();continue
        if start.text=='direction':
            take();value=take()
            if parent or value.text not in ('TD','TB','BT','LR','RL'):raise error(document,value.offset,'Invalid usecase direction')
            direction='TB' if value.text=='TD' else value.text;endline();continue
        if start.text in ('accTitle','accDescr'):
            take();parts=[]
            if at('{'):
                take()
                while not at('}'):
                    if at('EOF'):raise error(document,start.offset,'Unterminated accessibility description')
                    parts.append(take())
                take('}')
            else:
                take(':')
                while not at('\n') and not at('EOF'):parts.append(take())
            value=' '.join(p.text for p in parts).strip()
            if start.text=='accTitle':acc_title=value
            else:acc_description=value
            endline();continue
        if start.kind=='json-id':
            if parent:raise error(document,start.offset,'JSON declarations are not permitted inside a boundary')
            id=take().text;raw=take();value=json.loads(raw.text);draft=UsecaseNode(id,id,'json','json-table',classes=suffix(),value=_freeze(value))
            if id in nodes or id in boundaries:raise error(document,start.offset,'Duplicate JSON symbol')
            nodes[id]=draft;endline();continue
        if start.text in ('classDef','class','style'):
            if parent:raise error(document,start.offset,'Boundary body permits declarations only')
            cmd=take().text;ids=[ident()[0]]
            while at(','):take();ids.append(ident()[0])
            first=ts[i].offset;parts=[]
            while not at('\n') and not at('EOF'):parts.append(take())
            value=document.cleaned[first:ts[i].offset].strip()
            if not value:raise error(document,start.offset,'Empty usecase style/class statement')
            if cmd=='classDef':
                for id in ids:defs[id]=styles(value)
            elif cmd=='class':class_assignments.append((tuple(ids),tuple(x.strip() for x in value.split(',')),start.offset))
            else:
                if len(ids)!=1:raise error(document,start.offset,'style accepts one target')
                style_assignments.append((ids[0],styles(value),start.offset))
            endline();continue
        if start.text=='note':
            if parent:raise error(document,start.offset,'Notes are not permitted inside boundaries')
            take();take('for');target=ident()[0];parts=[]
            while not at('\n') and not at('EOF'):parts.append(take())
            label,kind=_label(parts,document.cleaned);notes.append((target,label,kind,start.offset));endline();continue
        if start.text=='systemBoundary':
            if parent:raise error(document,start.offset,'Nested system boundaries are not supported by the source grammar')
            take();node,_,offset=entity('boundary');nodes.pop(node.id,None)
            if node.id in boundaries:raise error(document,offset,'Duplicate boundary')
            meta=dict(node.metadata)
            if any(k!='type' or v not in ('rect','package') for k,v in meta.items()):raise error(document,offset,'Invalid boundary metadata')
            boundaries[node.id]=Boundary(node.id,node.label,meta.get('type','rect'),node.label_kind,classes=node.classes);parent=node.id;endline();continue
        # A standalone metadata assignment is delayed until all declarations
        # and explicit edge IDs are known, matching the source model builder.
        if i+1<len(ts) and ts[i+1].text=='@{':
            id,_=ident();meta=metadata();assignments.append((id,meta,start.offset));endline();continue
        actor=start.text=='actor'
        if actor:take()
        first,declared,offset=entity('actor' if actor else 'usecase',declare=actor)
        if actor:
            while at(','):take();entity('actor',declare=True)
        if at('\n') or at('EOF'):
            if not declared:register(first,offset)
            endline();continue
        if parent:raise error(document,ts[i].offset,'Boundary body permits declarations only')
        explicit_id=None
        if ts[i].kind=='word' and ts[i+1].text=='@':explicit_id=take().text;take('@')
        op=take();label='';label_kind='text';relation_type='association';end_marker='none';start_marker='none';dashed=False;minlen=max(1,op.text.count('-')-1)
        if op.text=='..>':
            take(':');semantic=take().text.lower()
            if semantic not in ('include','extend'):raise error(document,op.offset,'Invalid semantic relationship')
            relation_type=semantic;label=semantic;dashed=True;end_marker='point'
        elif op.text=='--|>':relation_type='generalization';end_marker='extension'
        elif re.fullmatch(r'--+>|<--+|--+|--o|o--|--x|x--',op.text):
            if op.text.startswith('<'):start_marker='point'
            elif op.text.startswith('o'):start_marker='circle'
            elif op.text.startswith('x'):start_marker='cross'
            elif op.text.endswith('>'):end_marker='point'
            elif op.text.endswith('o'):end_marker='circle'
            elif op.text.endswith('x'):end_marker='cross'
            if op.text in ('--','<--','o--','x--'):
                j=i
                while ts[j].text not in ('\n','EOF') and not re.fullmatch(r'--+>|--+|--o|--x',ts[j].text):j+=1
                if ts[j].text not in ('\n','EOF'):
                    label,label_kind=_label(ts[i:j],document.cleaned);i=j;right=take().text
                    minlen=max(1,right.count('-')-1)
                    if right.endswith('>'):end_marker='point'
                    elif right.endswith('o'):end_marker='circle'
                    elif right.endswith('x'):end_marker='cross'
        else:raise error(document,op.offset,'Invalid usecase relationship operator')
        target,target_declared,target_offset=entity()
        id=explicit_id or 'edge-'+str(counter)
        if explicit_id is None:counter+=1
        edge_drafts.append((UsecaseEdge(id,first.id,target.id,start_marker,end_marker,dashed,label,kind=relation_type,min_length=minlen,explicit=explicit_id is not None,label_kind=label_kind),first,declared,offset,target,target_declared,target_offset))
        endline()
    if parent:raise error(document,len(document.cleaned),'Unterminated usecase boundary')
    edges={}
    for edge,a,ad,ao,b,bd,bo in edge_drafts:
        for node,declared,offset in ((a,ad,ao),(b,bd,bo)):
            if node.id not in nodes and node.id not in boundaries:register(replace(node,classes=()),offset)
            elif node.classes and not declared:raise error(document,offset,'Classes on a relationship reference require a declaration')
        if edge.id in edges or edge.id in nodes or edge.id in boundaries:raise error(document,ao,'Duplicate edge or symbol ID')
        kinds=(nodes.get(edge.source),nodes.get(edge.target))
        if any(n is None or n.kind not in ('actor','usecase','json') for n in kinds):raise error(document,ao,'Invalid relationship endpoint kind')
        if edge.kind in ('include','extend') and any(n.kind!='usecase' for n in kinds):raise error(document,ao,'Include/extend require usecase endpoints')
        if edge.kind=='generalization' and (kinds[0].kind!=kinds[1].kind or kinds[0].kind not in ('actor','usecase')):raise error(document,ao,'Invalid generalization endpoint kinds')
        if any(n.kind=='json' for n in kinds) and (edge.start_marker in ('circle','cross') or edge.end_marker in ('circle','cross') or edge.kind!='association'):raise error(document,ao,'JSON relationships permit point or markerless association only')
        edges[edge.id]=edge
    def apply_meta(id,meta,offset,replace_values):
        if id in nodes:
            node=nodes[id];values=dict(node.metadata)
            for key,value in meta:
                valid=(key=='business' and isinstance(value,bool)) or node.kind=='actor' and (key=='type' and value in ('normal','hollow','awesome') or key=='icon' and isinstance(value,str))
                if not valid:raise error(document,offset,'Invalid '+node.kind+' metadata '+key)
                if not replace_values and key in values and values[key]!=value:raise error(document,offset,'Conflicting metadata')
                values[key]=value
            nodes[id]=replace(node,metadata=tuple(values.items()))
        elif id in boundaries:
            if any(k!='type' or v not in ('rect','package') for k,v in meta):raise error(document,offset,'Invalid boundary metadata')
            boundaries[id]=replace(boundaries[id],shape=dict(meta).get('type',boundaries[id].shape))
        elif id in edges and edges[id].explicit:
            if any(not(k=='animate' and isinstance(v,bool) or k=='animation' and v in ('fast','slow')) for k,v in meta):raise error(document,offset,'Invalid edge metadata')
            # Animation is deliberately excluded; static initial paint remains.
        else:raise error(document,offset,'Unresolved metadata target '+id)
    for id,node in tuple(nodes.items()):apply_meta(id,node.metadata,0,False)
    for id,meta,offset in assignments:apply_meta(id,meta,offset,True)
    for id,node in nodes.items():
        meta=dict(node.metadata)
        if node.kind=='actor':
            if meta.get('icon') and meta.get('type','normal')!='normal':raise error(document,0,'Icon conflicts with actor type')
            if meta.get('business') and (meta.get('icon') or meta.get('type')=='awesome'):raise error(document,0,'Business actors require normal/hollow geometry')
        elif node.shape=='rect' and meta.get('business'):raise error(document,0,'Rectangular business usecase is invalid')
    for ids,classes,offset in class_assignments:
        for id in ids:
            target=nodes if id in nodes else boundaries if id in boundaries else edges
            if id not in target:raise error(document,offset,'Unresolved class target '+id)
            target[id]=replace(target[id],classes=tuple(dict.fromkeys((*target[id].classes,*classes))))
    for id,value,offset in style_assignments:
        target=nodes if id in nodes else boundaries if id in boundaries else edges
        if id not in target:raise error(document,offset,'Unresolved style target '+id)
        target[id]=replace(target[id],styles=(*target[id].styles,*value))
    for id,b in tuple(boundaries.items()):boundaries[id]=replace(b,members=tuple(n.id for n in nodes.values() if n.parent==id))
    for index,(target,label,kind,offset) in enumerate(notes):
        if target not in nodes or nodes[target].kind not in ('actor','usecase'):raise error(document,offset,'Note target must be an actor or usecase')
        id='note-'+str(index);nodes[id]=UsecaseNode(id,label,'note','note',kind,metadata=(('target',target),));edges[id+'-edge']=UsecaseEdge(id+'-edge',id,target,dashed=True)
    return make_diagram('usecase',document,config,UsecaseModel(tuple(nodes.values()),tuple(boundaries.values()),tuple(edges.values()),tuple(defs.items()),direction,acc_title,acc_description))


def _json_rows(value,path=''):
    rows=[]
    if isinstance(value,JsonObject):
        if not value.properties:return [(path,'{}')]
        for k,v in value.properties:rows.extend(_json_rows(v,path+'.'+k if path else k))
    elif isinstance(value,tuple):
        if not value:return [(path,'[]')]
        scalar=all(not isinstance(v,tuple) for v in value)
        for i,v in enumerate(value):rows.extend(_json_rows(v,(path if i==0 else '') if scalar else path+'['+str(i)+']'))
    else:rows.append((path,'null' if value is None else 'true' if value is True else 'false' if value is False else str(value)))
    return rows


async def build(diagram,painter):
    from ...runtime.common import config_dict
    from ...runtime.graph import layout_graph
    model=diagram.model;config=config_dict(diagram);conf=config.get('usecase') or {};palette=theme(config);defs=dict(model.definitions);nodes=[];measurements={};stereotypes={};json_rows={};node_styles={};actor_paint={};painter.rough_enabled=True;tv=config.get('themeVariables') or {};ordered=tuple(n for kind in ('actor','usecase','note','json') for n in model.nodes if n.kind==kind);color_index=0
    def measure(text,node):return painter.measure(text,label_kind=node.label_kind,width=number(conf.get('wrappingWidth'),250),style=label_style(node_styles[node.id]))
    for node in ordered:
        actor=node.kind=='actor';fill=tv.get('usecaseActorBkg',tv.get('actorBkg',palette['fill'])) if actor else tv.get('usecaseBkg',palette['fill']);stroke=tv.get('usecaseActorBorder',tv.get('actorBorder',tv.get('primaryColor',palette['stroke']))) if actor else tv.get('usecaseBorder',palette['stroke']);s=node_style(painter,config,('node','default','usecase-'+('actor' if actor else node.shape),*node.classes),node.id,model.definitions,node.styles,fill=fill,stroke=stroke,index=color_index if conf.get('colorScheme')=='rotate' and node.kind in ('actor','usecase') else None,base_extra={'font_size':number(conf.get(('actor' if actor else 'usecase')+'FontSize'),14 if actor else 12),'font_family':conf.get(('actor' if actor else 'usecase')+'FontFamily',tv.get('fontFamily','sans-serif')),'font_weight':conf.get(('actor' if actor else 'usecase')+'FontWeight','normal'),'stroke_width':2} if node.kind in ('actor','usecase') else None);node_styles[node.id]=s
        if actor:
            from ._usecase_glyphs import actor_styles
            caption,stereotype_style,glyph=actor_styles(painter,node,config,model.definitions,fill,stroke,color_index if conf.get('colorScheme')=='rotate' else None);node_styles[node.id]=caption;actor_paint[node.id]=(glyph,caption,stereotype_style)
        if node.kind in ('actor','usecase'):color_index+=1
        box=measure(node.label,node);measurements[node.id]=box;stereotype=painter.measure('\u00ab'+node.stereotype+'\u00bb',label_kind=node.label_kind,width=number(conf.get('wrappingWidth'),250),style=actor_paint[node.id][2] if actor else node_styles[node.id]) if node.stereotype else None;stereotypes[node.id]=stereotype;label_width=max(box.width,stereotype.width if stereotype else 0,number(conf.get('minNodeWidth'),0) if node.kind!='actor' and node.label else 0);label_height=box.height+(stereotype.height+2 if stereotype else 0)
        if node.kind=='actor':w=max(label_width,56)+20;h=72+8+label_height+20
        elif node.kind=='json':
            rows=_json_rows(node.value);json_rows[node.id]=tuple((painter.measure(k,style=s),painter.measure(v,style=s)) for k,v in rows);w=max(120,max((a.width+b.width+30 for a,b in json_rows[node.id]),default=120));h=sum(max(a.height,b.height)+12 for a,b in json_rows[node.id])+16
        else:w=label_width+(40 if node.shape=='ellipse' else 20);h=label_height+(40 if node.shape=='ellipse' else 20)
        nodes.append({'id':node.id,'width':w,'height':h,'parent':node.parent,'spreadPorts':node.kind=='usecase' and node.shape=='ellipse'})
    edges=[]
    for edge in model.edges:
        b=painter.measure(edge.label,label_kind=edge.label_kind) if edge.label else None;edges.append({'id':edge.id,'source':edge.source,'target':edge.target,'label':edge.label,'label_width':b.width if b else 0,'label_height':b.height if b else 0,'min_length':edge.min_length})
    parents=[{'id':g.id,'padding':20,'title_height':painter.measure(g.label,label_kind=g.label_kind).height+14} for g in model.boundaries]
    layout=await layout_graph(nodes,edges,config=config,direction=model.direction,parents=parents,node_spacing=number(conf.get('nodeSpacing'),50),rank_spacing=number(conf.get('rankSpacing'),50))
    for index,g in enumerate(model.boundaries):
        b=layout.groups[g.id];s=node_style(painter,config,('cluster','default','system-boundary',*g.classes),g.id,model.definitions,g.styles,fill=tv.get('usecaseBoundaryBkg',palette['group']),stroke=tv.get('usecaseBoundaryBorder',palette['groupStroke']),index=index);painter.rect(b.x,b.y,b.width,b.height,style=s,id=g.id,role='system-boundary')
        if g.shape=='package':painter.rect(b.x,b.y-14,min(90,b.width/2),14,style=s,id=g.id,role='package-tab')
        painter.text(g.label,b.x+12,b.y+5,style=label_style(s),label_kind=g.label_kind,id=g.id)
    compiled=[]
    for e in model.edges:
        style={}
        for c in e.classes:style.update(dict(defs.get(c,())))
        if e.kind in ('include','extend'):style['stroke']=tv.get('usecase'+e.kind.capitalize()+'Line',palette['edge'])
        style.update(dict(e.styles));compiled.append(replace(e,styles=tuple(style.items())))
    layout=paint_edges(painter,layout,compiled,palette,{n.id:'ellipse' for n in model.nodes if n.kind=='usecase' and n.shape!='rect'})
    for node in ordered:
        b=layout.nodes[node.id];label=measurements[node.id];s=node_styles[node.id];fill=s.fill;stroke=s.stroke;color=s.text_color;meta=dict(node.metadata)
        if node.kind=='note':draw_note(painter,b.x,b.y,b.width,b.height,node.label,palette,node.id);continue
        if node.kind=='actor':
            from ._usecase_glyphs import paint_actor
            glyph,caption,stereotype_style=actor_paint[node.id];paint_actor(painter,node,b,label,stereotypes[node.id],glyph,meta,caption,stereotype_style);continue
        if node.kind=='json':
            painter.rect(b.x,b.y,b.width,b.height,fill=fill,stroke=stroke,id=node.id);key_width=max((a.width for a,_ in json_rows[node.id]),default=0)+16;y=b.y+8
            for a,v in json_rows[node.id]:
                height=max(a.height,v.height)+12;painter.text(a,b.x+8,y,color=color,id=node.id,role='json-key');painter.text(v,b.x+key_width+8,y,color=color,id=node.id,role='json-value');y+=height;painter.line(b.x,y,b.x+b.width,y,stroke=stroke,id=node.id)
            painter.line(b.x+key_width,b.y,b.x+key_width,b.y+b.height,stroke=stroke,id=node.id);continue
        if node.shape=='rect':painter.rect(b.x,b.y,b.width,b.height,style=s,id=node.id)
        else:painter.ellipse(b.x+b.width/2,b.y+b.height/2,b.width/2,b.height/2,style=s,id=node.id)
        stereotype=stereotypes[node.id];lh=label.height+(stereotype.height+2 if stereotype else 0);y=b.y+(b.height-lh)/2
        if stereotype:painter.text(stereotype,b.x+(b.width-stereotype.width)/2,y,style=s,id=node.id,role='stereotype');y+=stereotype.height+2
        painter.text(label,b.x+(b.width-label.width)/2,y,style=s,id=node.id)
        if meta.get('business'):
            import math
            rx=b.width/2;ry=b.height/2;inset=2;lw=max(label.width,stereotype.width if stereotype else 0);x1=lw/2+inset;x2=rx-inset;y1=ry*math.sqrt(max(0,1-(x1/rx)**2));y2=-ry*math.sqrt(max(0,1-(x2/rx)**2));painter.line(b.x+rx+x1,b.y+ry+y1,b.x+rx+x2,b.y+ry+y2,stroke=stroke,line_width=s.stroke_width,id=node.id,role='business-usecase-mark')
    paint_title(diagram,painter,layout,'usecaseDiagramTitleText',number(conf.get('titleTopMargin'),25))
    return painter.finish(layout=layout,padding=number(conf.get('diagramPadding'),8))
