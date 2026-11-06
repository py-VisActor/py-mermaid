"""Agentflow-specific actions over the shared fixed flowchart lexical parser."""
from dataclasses import replace
from collections.abc import Mapping
import re
from ..flowchart.parser import _Parser,_Block,_truthy
from ...model.flowchart import FlowNode
from ...config.values import freeze_value,thaw_value
from ...geometry.shape_registry import is_valid_shape

ALIASES={'task':'roundedRect','tool':'subroutine','input':'lean-right','decision':'diamond','refdoc':'lin-doc','action':'hexagon','round':'rect'}
REMOVED=frozenset(('doc','stadium','terminal','circle','trapezoid','inv_trapezoid','inv-trapezoid','doublecircle','double-circle','typeDeclaration','procs','lean_left','lean-left','in-out','cylinder','ellipse','odd','tag-rect','tagged-rectangle','delay','half-rounded-rectangle','lin-rect','lined-rectangle','win-pane','window-pane','curv-trap','curved-trapezoid'))
ALLOWED=frozenset(('roundedRect','subroutine','subprocess','subproc','framed-rectangle','lean-right','diamond','lin-doc','lined-document','hexagon','hex','connector','collapsedGroup'))
KIND={'subroutine':'tool','subprocess':'tool','subproc':'tool','framed-rectangle':'tool','hexagon':'action','hex':'action','lean-right':'input','lin-doc':'refdoc','lined-document':'refdoc','diamond':'decision'}

class AgentParser(_Parser):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.global_nodes=set();self.connectors=set();self.global_blocks=set();self.pending_metadata={};self.diagnostics=[];self.kinds={}

    def node(self):
        ident=super().node()
        if ident=='connectors' and ident not in self.connectors and ident not in self.groups:self.nodes.pop(ident,None)
        return ident

    def metadata(self,identifier):
        from ...parsing.yaml_json import load_yaml_json,YamlError
        from ...parsing.preprocess import _js_string
        start=self.cursor;self.cursor+=2;begin=self.cursor;quote=False;pieces=[];piece=self.cursor
        while self.cursor<len(self.text):
            ch=self.text[self.cursor]
            if ch=='"':
                if quote:pieces.extend((re.sub(r'\n\s*','<br/>',self.text[piece:self.cursor]),'"'));piece=self.cursor+1
                else:pieces.append(self.text[piece:self.cursor+1]);piece=self.cursor+1
                quote=not quote
            elif ch=='}' and not quote:pieces.append(self.text[piece:self.cursor]);break
            elif ch=='^' and not quote:self.error('Unexpected caret in metadata',start=start)
            self.cursor+=1
        if self.cursor>=len(self.text):self.error('Unterminated metadata',start=start)
        self.cursor+=1;content=''.join(pieces);yaml=content+'\n' if '\n' in content else '{\n'+content+'\n}'
        try:doc=load_yaml_json(yaml)
        except YamlError as first:
            # Source retries only commas ending a multiline YAML line.
            retry=re.sub(r',([ \t]*(?:#[^\n]*)?)(?=\n|$)',r'\1',content) if '\n' in content else content
            if retry==content:self.error(str(first),'INVALID_YAML',start=begin,end=self.cursor-1)
            try:doc=load_yaml_json(retry+'\n')
            except YamlError:self.error(str(first),'INVALID_YAML',start=begin,end=self.cursor-1)
        if doc is None:doc={}
        if not isinstance(doc,Mapping):self.error('Metadata must be a mapping','INVALID_METADATA',start=start)
        def clean(v):
            if isinstance(v,Mapping):return {k:clean(x) for k,x in v.items() if k not in ('__proto__','constructor','prototype')}
            if isinstance(v,(list,tuple)):return [clean(x) for x in v]
            return v
        doc=clean(doc)
        if identifier in self.groups:
            group=self.groups[identifier];self.groups[identifier]=replace(group,metadata=freeze_value({**thaw_value(group.metadata),**doc}));return
        for index,edge in enumerate(self.edges):
            if edge.source_id==identifier:
                self.edges[index]=replace(edge,metadata=freeze_value({**thaw_value(edge.metadata),**doc}),curve=doc.get('curve',edge.curve),animate=doc.get('animate',edge.animate),animation=doc.get('animation',edge.animation));return
        if identifier=='connectors' and identifier not in self.connectors:return
        if identifier not in self.nodes:self.nodes[identifier]=FlowNode(identifier,identifier,self.span(start,self.cursor))
        node=self.nodes[identifier];values={**thaw_value(node.metadata),**doc}
        if identifier in self.connectors:self.nodes[identifier]=replace(node,metadata=freeze_value(values));return
        shape=node.shape
        if _truthy(doc.get('shape')):
            value=doc['shape']
            if not isinstance(value,str) or value!=value.lower() or '_' in value:self.error('Shape names must be lowercase','UNSUPPORTED_SHAPE',start=start)
            shape=ALIASES.get(value,value)
            if not is_valid_shape(shape) and shape not in ALLOWED:self.error('No such shape: '+value,'UNSUPPORTED_SHAPE',start=start)
            values['shape']=shape
        label=node.label;raw=node.raw_label;kind=node.label_kind
        if _truthy(doc.get('label')):
            raw=_js_string(doc['label']);label=self.plain(raw,begin,self.cursor-1);kind=doc.get('labelType','text')
            if kind not in ('markdown','text','string'):kind='text'
        self.nodes[identifier]=replace(node,shape=shape,label=label,raw_label=raw,label_kind='text' if kind=='string' else kind,metadata=freeze_value(values))

    def start_flow(self):
        start=self.cursor;global_block=self.keyword('global');self.cursor+=6 if global_block else 4;self.horizontal()
        identifier=None;label='';self.last_kind='text';self.last_raw='';self.last_span=self.span(self.cursor,self.cursor)
        if global_block:
            self.blocks.append(_Block(start,'__global_'+str(start),''));self.global_blocks.add(start);self.statement_end();return
        if self.cursor<len(self.text) and self.text[self.cursor] not in ';\r\n':
            identifier=self.head_identifier();self.horizontal()
            if self.text.startswith('[',self.cursor):self.cursor+=1;label,_=self.delimited_text(']')
        block=_Block(start,identifier,label,label_kind=self.last_kind,raw_label=self.last_raw,label_span=self.last_span)
        pending={}
        if self.text.startswith('@{',self.cursor):
            placeholder=identifier or '__flow_'+str(start);self.nodes.setdefault(placeholder,FlowNode(placeholder,placeholder,self.span(start,self.cursor)));self.metadata(placeholder);pending=thaw_value(self.nodes.pop(placeholder).metadata)
        self.pending_metadata[start]=pending;self.blocks.append(block);self.statement_end()

    def end_group(self):
        if not self.blocks:return super().end_group()
        block=self.blocks[-1]
        if block.start in self.global_blocks:
            self.cursor+=3;self.blocks.pop();self.global_nodes.update(block.members)
            for ident,group in tuple(self.groups.items()):self.groups[ident]=replace(group,members=tuple(x for x in group.members if x not in self.global_nodes))
            self.statement_end();return
        before=set(self.groups);super().end_group()
        ident=block.identifier or next(iter(set(self.groups)-before),'')
        if ident in self.groups:
            group=self.groups[ident];self.groups[ident]=replace(group,members=tuple(dict.fromkeys(x for x in group.members if x not in self.global_nodes)),label=block.label or group.label,direction=block.direction or group.direction,metadata=freeze_value({**thaw_value(group.metadata),**self.pending_metadata.get(block.start,{})}))

    def connector(self):
        start=self.cursor;self.cursor+=9;self.horizontal();ident=self.head_identifier();self.horizontal();label=''
        if self.text.startswith('[',self.cursor):self.cursor+=1;label,_=self.delimited_text(']')
        old=self.nodes.get(ident) if ident in self.connectors else None;self.connectors.add(ident)
        self.nodes[ident]=replace(old,label=label or old.label) if old else FlowNode(ident,label or ident,self.span(start,self.cursor),'roundedRect')
        while self.text.startswith('@{',self.cursor):self.metadata(ident);self.horizontal()
        if self.blocks:self.blocks[-1].members.append(ident)
        self.statement_end()

    def head_identifier(self):
        if self.text.startswith('"',self.cursor):return self.quoted()[0].strip()
        start=self.cursor
        while self.cursor<len(self.text) and self.text[self.cursor] not in '[;\r\n' and not self.text.startswith('@{',self.cursor):self.cursor+=1
        value=self.text[start:self.cursor].strip()
        if not value:self.error('Expected container/connector identifier',start=start)
        return value

    def finish(self):
        parents={}
        for group in reversed(tuple(self.groups.values())):
            kept=[]
            for member in group.members:
                cursor=group.id;seen=set();cycle=False
                while cursor is not None and cursor not in seen:
                    if cursor==member:cycle=True;break
                    seen.add(cursor);cursor=parents.get(cursor)
                if cycle:self.diagnostics.append(f'CONTAINMENT_VIOLATION: Container "{group.id}" cannot contain "{member}" because it already contains it; nesting dropped')
                else:kept.append(member);parents[member]=group.id
            self.groups[group.id]=replace(group,members=tuple(kept))
        for ident,node in tuple(self.nodes.items()):
            shape=ALIASES.get(node.shape,node.shape)
            shape={'square':'roundedRect','squareRect':'roundedRect','rect':'roundedRect','round':'roundedRect','lean_right':'lean-right'}.get(shape,shape)
            if shape in REMOVED:
                self.diagnostics.append(f'SHAPE_REMOVED: {ident}: shape "{shape}" was removed in v0.8.1, using "roundedRect"');shape='roundedRect'
            elif shape not in ALLOWED:
                self.diagnostics.append(f'SHAPE_UNSUPPORTED: {ident}: shape "{shape}" is not supported, using "roundedRect"');shape='roundedRect'
            self.kinds[ident]='connector' if ident in self.connectors else KIND.get(shape,'task')
            self.nodes[ident]=replace(node,shape=shape)
        return super().finish()

    def parse(self):
        self.separators();m=re.match(r'agentflow-beta(?=[\s;]|$)',self.text[self.cursor:])
        if not m:self.error('Expected agentflow-beta','UNKNOWN_DIAGRAM')
        self.cursor+=m.end();self.horizontal();start=self.cursor
        if self.cursor==len(self.text) or self.text[self.cursor] in '\r\n':self.direction='TB'
        else:
            while self.cursor<len(self.text) and not self.text[self.cursor].isspace() and self.text[self.cursor]!=';':self.cursor+=1
            value=self.text[start:self.cursor];self.direction={'<':'RL','>':'LR','^':'BT','v':'TB','BR':'TB'}.get(value,value)
        if self.direction not in ('TD','TB','LR','RL','BT'):self.error('Invalid agentflow direction','UNSUPPORTED_DIRECTION',start=start)
        self.statement_end()
        while self.cursor<len(self.text):
            if self.lexical_direction() or self.accessibility():continue
            if self.keyword('flow') or self.keyword('global'):self.start_flow()
            elif self.keyword('connector'):self.connector()
            elif self.keyword('end'):self.end_group()
            elif self.keyword('direction'):self.group_direction()
            elif self.keyword('style'):self.style_statement('style')
            elif self.keyword('classDef'):self.style_statement('classDef')
            elif self.keyword('class'):self.style_statement('class')
            elif self.keyword('linkStyle'):self.link_style()
            elif self.keyword('click'):self.ignored_click()
            else:
                current=self.node_list();chain=list(current)
                while (link:=self.link()) is not None:
                    self.link_whitespace();target=self.node_list();self.add_links(current,target,link);current=target;chain=list(target)+chain
                if self.blocks:self.blocks[-1].members.extend(chain)
                self.statement_end()
        if self.blocks:self.error('Unterminated flow/global container',start=self.blocks[-1].start)
        return self.finish()
