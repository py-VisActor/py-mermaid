"""Class grammar, scoped namespace DB, compartment geometry and static paint.

Sources: classDiagram.jison, classDb.ts, classTypes.ts and unified classRenderer.
Legacy and v2 headers use the same value model; layout is the retained ELK policy.
"""
from __future__ import annotations
from dataclasses import dataclass,replace
import html
import re
from ._support import label_style,statements,unquote,styles,css,theme,paint_edges,draw_note,number,node_style,paint_title


@dataclass(frozen=True)
class Member:
    id:str
    visibility:str=''
    parameters:str=''
    return_type:str=''
    classifier:str=''
    method:bool=False
    @property
    def display(self):
        text=self.visibility+generic(self.id)
        if self.method:text+='('+generic(self.parameters)+')'+(' : '+generic(self.return_type) if self.return_type else '')
        return text.strip()


@dataclass(frozen=True)
class Class:
    id:str
    label:str
    generic_type:str=''
    members:tuple[Member,...]=()
    methods:tuple[Member,...]=()
    annotations:tuple[str,...]=()
    classes:tuple[str,...]=('default',)
    styles:tuple[tuple[str,str],...]=()
    parent:str|None=None
    interface:bool=False


@dataclass(frozen=True)
class Namespace:
    id:str
    label:str
    parent:str|None=None
    explicit:bool=False


@dataclass(frozen=True)
class Note:
    id:str
    text:str
    target:str=''
    parent:str|None=None


@dataclass(frozen=True)
class Relation:
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


@dataclass(frozen=True)
class ClassModel:
    classes:tuple[Class,...]
    namespaces:tuple[Namespace,...]
    relations:tuple[Relation,...]
    notes:tuple[Note,...]
    definitions:tuple[tuple[str,tuple],...]
    direction:str='TB'
    acc_title:str=''
    acc_description:str=''


def generic(value):
    def process(text):
        count=text.count('~')
        if count<=1:return text
        leading=count%2!=0 and text.startswith('~')
        if leading:text=text[1:]
        chars=list(text)
        while '~' in chars and chars.index('~')!=len(chars)-1-chars[::-1].index('~'):
            first=chars.index('~');last=len(chars)-1-chars[::-1].index('~');chars[first]='<';chars[last]='>'
        return ('~' if leading else '')+''.join(chars)
    parts=re.split('(,)',value);out=[];i=0
    while i<len(parts):
        text=parts[i]
        if text==',' and i>0 and i+1<len(parts) and parts[i-1].count('~')==1 and parts[i+1].count('~')==1:
            text=parts[i-1]+','+parts[i+1];i+=1;out.pop()
        out.append(process(text));i+=1
    return ''.join(out)


def class_name(value):
    value=unquote(value.strip())
    match=re.fullmatch(r'(.+?)~(.*)~',value)
    return (match[1],match[2]) if match else (value,'')


def member(value):
    value=value.strip();visibility='';classifier='';params='';return_type=''
    method=bool(re.search(r'\(.*\)',value))
    if method:
        match=re.search(r'([#+~-])?(.+)\((.*)\)([\s$*])?(.*)([$*])?',value)
        if match:
            visibility=(match[1] or '').strip();name=match[2];params=match[3].strip();classifier=(match[4] or '').strip();return_type=(match[5] or '').strip()
            if not classifier and return_type.endswith(('$','*')):classifier=return_type[-1];return_type=return_type[:-1]
        else:name=value
    else:
        if value[:1] in ('#','+','~','-'):visibility=value[0];value=value[1:]
        if value.endswith(('$','*')):classifier=value[-1];value=value[:-1]
        name=value
    name=(' ' if name.startswith(' ') else '')+name.strip()
    return Member(name,visibility,params,return_type,classifier,method)


_NAME=r'(?:`[^`]+`|[\w\u0080-\uffff.\-]+)(?:~[^~]*~)?'
_REL=re.compile(r'^(?P<a>'+_NAME+r')\s*(?:"(?P<al>[^"]*)"\s*)?(?P<l><\||\|>|\(\)|[o*<>])?\s*(?P<line>--|\.\.)\s*(?P<r><\||\|>|\(\)|[o*<>])?\s*(?:"(?P<bl>[^"]*)"\s*)?(?P<b>'+_NAME+r')\s*(?::(?P<label>.*))?$')
_MARK={'<|':'extension','|>':'extension','o':'aggregation','*':'composition','<':'dependency','>':'dependency','()':'lollipop',None:'none'}


def parse(document,config):
    from ...runtime.common import make_diagram,error,sanitize_text
    source=document.cleaned;tokens=statements(source,semicolon=False);classes={};namespaces={};relations=[];notes=[];definitions={};stack=[];direction='TB';acc_title='';acc_description=''
    if not tokens or tokens[0].text not in ('classDiagram','classDiagram-v2'):raise error(document,0,'Expected classDiagram header')
    if len(tokens)==1:raise error(document,len(source),'Class diagram requires a statement')
    i=1
    def ensure(raw,parent=None):
        id,type_=class_name(sanitize_text(raw,config))
        if id not in classes:classes[id]=Class(id,id,type_,parent=parent)
        elif parent is not None:classes[id]=replace(classes[id],parent=parent)
        return id
    def add_member(id,text):
        id=ensure(id);text=sanitize_text(text,config).strip()
        if text.startswith('<<') and text.endswith('>>'):classes[id]=replace(classes[id],annotations=(*classes[id].annotations,text[2:-2]));return
        if not text:return
        value=member(text);field='methods' if value.method else 'members';classes[id]=replace(classes[id],**{field:(*getattr(classes[id],field),value)})
    while i<len(tokens):
        token=tokens[i];text=token.text;i+=1;parent=stack[-1] if stack else None
        if text=='}':
            if not stack:raise error(document,token.offset,'Unexpected namespace terminator')
            stack.pop();continue
        if text=='{':raise error(document,token.offset,'Unexpected opening structure')
        if stack and not text.startswith(('class ','namespace ','note ')):raise error(document,token.offset,'Namespace bodies permit classes, namespaces and notes only')
        if text.startswith('namespace '):
            match=re.fullmatch(r'namespace\s+('+_NAME+r')(?:\["(.*?)"\])?',text,re.S)
            if not match or i>=len(tokens) or tokens[i].text!='{':raise error(document,token.offset,'Namespace requires a block')
            name=unquote(match[1]);qualified=parent+'.'+name if parent else name;parts=qualified.split('.')
            for n in range(1,len(parts)+1):
                id='.'.join(parts[:n]);previous=namespaces.get(id);leaf=n==len(parts)
                namespaces[id]=Namespace(id,match[2] if leaf and match[2] is not None else previous.label if previous else parts[n-1],'.'.join(parts[:n-1]) or None,leaf or bool(previous and previous.explicit))
            stack.append(qualified);i+=1;continue
        if text.startswith('classDef '):
            match=re.fullmatch(r'classDef\s+([\w,]+)\s+(.+)',text,re.S)
            if not match:raise error(document,token.offset,'Invalid classDef')
            for name in match[1].split(','):definitions[name]=(*definitions.get(name,()),*styles(match[2]))
            continue
        if text.startswith('style '):
            match=re.fullmatch(r'style\s+(\w+)\s+(.+)',text,re.S)
            if not match:raise error(document,token.offset,'Invalid class style')
            if match[1] in classes:classes[match[1]]=replace(classes[match[1]],styles=styles(match[2]))
            continue
        if text.startswith('cssClass '):
            match=re.fullmatch(r'cssClass\s+"([^"]*)"\s+(\w+)',text)
            if not match:raise error(document,token.offset,'Invalid cssClass')
            for id in match[1].split(','):
                if id in classes:classes[id]=replace(classes[id],classes=(*classes[id].classes,match[2]))
            continue
        if text.startswith(('click ','link ','callback ')):
            # Navigation/callback metadata is excluded; initial clickable style
            # remains a real source class, without executing callback strings.
            match=re.match(r'(?:click|link|callback)\s+('+_NAME+r')\s+.+',text,re.S)
            if not match:raise error(document,token.offset,'Invalid static click statement')
            id=class_name(match[1])[0]
            if id in classes:classes[id]=replace(classes[id],classes=(*classes[id].classes,'clickable'))
            continue
        if text.startswith('note '):
            match=re.fullmatch(r'note(?:\s+for\s+('+_NAME+r'))?\s+"(.*)"',text,re.S)
            if not match:raise error(document,token.offset,'Expected quoted class note')
            notes.append(Note('note'+str(len(notes)),sanitize_text(match[2],config),class_name(match[1])[0] if match[1] else '',parent));continue
        if text.startswith('direction '):
            if text[10:].strip() not in ('TB','BT','LR','RL'):raise error(document,token.offset,'Invalid class direction')
            direction=text[10:].strip();continue
        if text.startswith(('accTitle:','accTitle :')):acc_title=text.split(':',1)[1].strip();continue
        if text.startswith(('accDescr:','accDescr :')):acc_description=text.split(':',1)[1].strip();continue
        if text=='accDescr' and i<len(tokens) and tokens[i].text=='{':
            i+=1;parts=[]
            while i<len(tokens) and tokens[i].text!='}':parts.append(tokens[i].text);i+=1
            if i==len(tokens):raise error(document,token.offset,'Unterminated accessibility description')
            i+=1;acc_description='\n'.join(parts).strip();continue
        match=_REL.fullmatch(text)
        if match:
            a=class_name(sanitize_text(match['a'],config))[0];b=class_name(sanitize_text(match['b'],config))[0];left=_MARK[match['l']];right=_MARK[match['r']]
            if left=='lollipop' and right=='none':
                ensure(match['b']);id='interface'+str(sum(c.interface for c in classes.values()));classes[id]=Class(id,a,interface=True);a=id
            elif right=='lollipop' and left=='none':
                ensure(match['a']);id='interface'+str(sum(c.interface for c in classes.values()));classes[id]=Class(id,b,interface=True);b=id
            else:ensure(match['a']);ensure(match['b'])
            relations.append(Relation('edge'+str(len(relations)),a,b,left,right,match['line']=='..',sanitize_text((match['label'] or '').strip(),config),sanitize_text(match['al'] or '',config),sanitize_text(match['bl'] or '',config)));continue
        match=re.fullmatch(r'<<([\w-]+)>>\s*('+_NAME+r')',text)
        if match:
            id=class_name(match[2])[0]
            if id not in classes:raise error(document,token.offset,'Annotation refers to an undeclared class')
            classes[id]=replace(classes[id],annotations=(*classes[id].annotations,match[1]));continue
        if text.startswith('class '):
            match=re.fullmatch(r'class\s+('+_NAME+r')(?:\s*\["(.*?)"\])?(?:\s*:::(\w+))?(?:\s*<<([\w-]+)>>)?',text,re.S)
            if not match:raise error(document,token.offset,'Invalid class declaration')
            id=ensure(match[1],parent)
            if match[2] is not None:classes[id]=replace(classes[id],label=sanitize_text(match[2],config))
            if match[3]:classes[id]=replace(classes[id],classes=(*classes[id].classes,match[3]))
            if match[4]:classes[id]=replace(classes[id],annotations=(*classes[id].annotations,match[4]))
            if i<len(tokens) and tokens[i].text=='{':
                i+=1
                while i<len(tokens) and tokens[i].text!='}':add_member(id,tokens[i].text);i+=1
                if i==len(tokens):raise error(document,token.offset,'Unterminated class body')
                i+=1
            continue
        match=re.fullmatch(r'('+_NAME+r')\s*:\s*(.*)',text,re.S)
        if match:add_member(match[1],match[2]);continue
        # The source memberStatement accepts a bare identifier but creates no
        # class. Do not synthesize an invisible undeclared class here.
        if re.fullmatch(_NAME,text):continue
        raise error(document,token.offset,'Unrecognized class statement: '+text)
    if stack:raise error(document,len(source),'Unterminated namespace')
    return make_diagram('classDiagram',document,config,ClassModel(tuple(classes.values()),tuple(namespaces.values()),tuple(relations),tuple(notes),tuple(definitions.items()),direction,acc_title,acc_description))


async def build(diagram,painter):
    from ...runtime.graph import layout_graph
    from ...runtime.common import config_dict
    model=diagram.model;config=config_dict(diagram);conf=config.get('class') or {};palette=theme(config);defs=dict(model.definitions);padding=number(conf.get('padding'),16);rows={};sizes={};node_data=[];node_styles={};color_index=0
    painter.rough_enabled=True
    hierarchical=conf.get('hierarchicalNamespaces',True)
    namespaces={n.id:n for n in model.namespaces}
    def parent(id):
        if hierarchical:return id
        while id and not namespaces[id].explicit:id=namespaces[id].parent
        return id
    for node in model.classes:
        source_style=node_style(painter,config,('node',*node.classes),node.id,model.definitions,node.styles,index=None if node.interface else color_index)
        node_styles[node.id]=source_style
        if not node.interface:color_index+=1
        groups=[]
        if node.annotations:groups.append((('«'+node.annotations[0]+'»',None),))
        groups.append(((node.label+('&lt;'+html.escape(generic(node.generic_type))+'&gt;' if node.generic_type else ''),'header'),))
        if not node.interface:
            if node.members or node.methods or not conf.get('hideEmptyMembersBox',False):
                groups.append(tuple((html.escape(m.display),m) for m in node.members));groups.append(tuple((html.escape(m.display),m) for m in node.methods))
        measured=[];w=40.;h=padding*2
        for group in groups:
            values=[]
            for text,m in group:
                text_style=replace(label_style(source_style),font_weight='bold' if m=='header' else source_style.font_weight,font_style='italic' if isinstance(m,Member) and m.classifier=='*' else source_style.font_style)
                box=painter.measure(text,style=text_style)
                values.append((box,m));w=max(w,box.width);h+=box.height
            measured.append(tuple(values));h+=8
        if node.interface:w=h=24.
        else:w+=padding*2
        rows[node.id]=measured;sizes[node.id]=(w,h);node_data.append({'id':node.id,'width':w,'height':h,'parent':parent(node.parent)})
    for note in model.notes:
        box=painter.measure(note.text,width=number(conf.get('wrappingWidth'),250));w=box.width+24;h=box.height+24;sizes[note.id]=(w,h);node_data.append({'id':note.id,'width':w,'height':h,'parent':parent(note.parent)})
    edges=list(model.relations)
    for note in model.notes:
        if note.target in sizes:edges.append(Relation('edgeNote'+note.id,note.id,note.target,dashed=True))
    edge_data=[]
    for edge in edges:
        label=painter.measure(edge.label) if edge.label else None
        edge_data.append({'id':edge.id,'source':edge.source,'target':edge.target,'label':edge.label,'label_width':label.width if label else 0,'label_height':label.height if label else 0})
    parents=[{'id':n.id,'parent':n.parent if hierarchical else None,'padding':padding,'title_height':painter.measure(n.label if hierarchical else n.id).height+8} for n in model.namespaces if hierarchical or n.explicit]
    layout=await layout_graph(node_data,edge_data,config=config,direction=model.direction,parents=parents,node_spacing=number((config.get('state') or {}).get('nodeSpacing'),50),rank_spacing=number((config.get('state') or {}).get('rankSpacing'),50))
    for n in model.namespaces:
        box=layout.groups.get(n.id)
        if box is not None:
            s=node_style(painter,config,('cluster','namespace'),n.id,fill=palette['group'],stroke=palette['groupStroke']);painter.rect(box.x,box.y,box.width,box.height,style=s,id=n.id,role='namespace');painter.text(n.label if hierarchical else n.id,box.x+padding,box.y+4,style=label_style(s),id=n.id)
    layout=paint_edges(painter,layout,edges,palette,{n.id:'circle' for n in model.classes if n.interface})
    for node in model.classes:
        box=layout.nodes[node.id];s=node_styles[node.id];stroke=s.stroke;text_color=s.text_color
        if node.interface:
            painter.ellipse(box.x+box.width/2,box.y+box.height/2,box.width/2,box.height/2,style=s,id=node.id);label=painter.measure(node.label,style=s);painter.text(label,box.x+(box.width-label.width)/2,box.y-label.height-4,style=s,id=node.id);continue
        painter.rect(box.x,box.y,box.width,box.height,style=s,id=node.id)
        y=box.y+padding
        for index,group in enumerate(rows[node.id]):
            if index>0 and (index>=len(rows[node.id])-2):painter.line(box.x,y-4,box.x+box.width,y-4,style=s,id=node.id,role='compartment-divider')
            for label,m in group:
                x=box.x+(box.width-label.width)/2 if m=='header' or m is None else box.x+padding
                painter.text(label,x,y,style=s,id=node.id,role='member' if isinstance(m,Member) else 'label')
                if isinstance(m,Member) and m.classifier=='$':painter.line(x,y+label.height-2,x+label.width,y+label.height-2,stroke=text_color,id=node.id,role='static-member-underline')
                y+=label.height
            y+=8
    for note in model.notes:
        box=layout.nodes[note.id];draw_note(painter,box.x,box.y,box.width,box.height,note.text,palette,note.id)
    paint_title(diagram,painter,layout,'classDiagramTitleText',number((config.get('state') or {}).get('titleTopMargin'),25))
    return painter.finish(layout=layout,padding=8)
