"""VChart DSL v1 deterministic lowering; no chart/runtime/native dependency.

Normative source: docs/VCHART_DSL_DESIGN.md and syntax/vchart-v1.ebnf.
Container ownership and array construction modes are tracked independently
from Python value equality, so False/0 and empty object/array remain distinct.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math

from ...model.flowchart import MermaidError
from ...model.vchart_dsl import (Node, SpecSpan, LoweredVChart, MAX_BYTES,
                                MAX_DEPTH, MAX_VALUES, dsl_error)


def _encoded(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':'))


@dataclass(frozen=True)
class _Binding:
    value: object
    declaration: Node


class _Lowerer:
    def __init__(self, text):
        self.text=text
        self.spec={};self.maps={};self.svgs={}
        self.bindings={}
        self.atomic={};self.opened={};self.array_modes={}
        self.resource_owners={}
        self.source_map=[SpecSpan((),0,len(text),'spec')]
        self.values=3  # The three output namespace objects.
        self.bytes=6   # {}, {}, {} before their members are inserted.

    def fail(self,node,message,code='VCHART_DSL_SYNTAX',path=(),related=()):
        raise dsl_error(self.text,node.start,node.end,message,code,path=path,
                        related=tuple((n.start,n.end) for n in related))

    def node(self,node):
        if not isinstance(node,Node):
            raise dsl_error(self.text,0,0,'Invalid DSL AST node')
        if (type(node.start) is not int or type(node.end) is not int or
                not 0<=node.start<=node.end<=len(self.text)):
            raise dsl_error(self.text,0,0,'AST span does not belong to this source')
        return node

    def tick(self,node,path,depth):
        self.values+=1
        if self.values>MAX_VALUES or depth>MAX_DEPTH:
            self.fail(node,'Expanded DSL value/depth budget exceeded','VCHART_DSL_BUDGET',path)

    def byte_budget(self,size,node,path=()):
        if size>MAX_BYTES:
            self.fail(node,'Serialized DSL values exceed8MiB','VCHART_DSL_BUDGET',path)
        return size

    def add_bytes(self,size,node,path=()):
        self.bytes+=size
        self.byte_budget(self.bytes,node,path)

    def record(self,node,path,namespace,emit,declaration=None):
        if emit:
            self.source_map.append(SpecSpan(tuple(path),node.start,node.end,namespace,
                declaration.start if declaration else None,declaration.end if declaration else None))

    def clone(self,value,node,path,namespace,emit,declaration,depth):
        """Count every expansion while creating independent mutable containers."""
        self.tick(node,path,depth)
        self.record(node,path,namespace,emit,declaration)
        if isinstance(value,dict):
            result={};size=2
            for key,item in value.items():
                cloned,amount=self.clone(item,node,(*path,key),namespace,emit,declaration,depth+1)
                size+=len(_encoded(key))+1+amount+(1 if result else 0)
                self.byte_budget(size,node,path);result[key]=cloned
            return result,size
        if isinstance(value,list):
            result=[];size=2
            for index,item in enumerate(value):
                cloned,amount=self.clone(item,node,(*path,index),namespace,emit,declaration,depth+1)
                size+=amount+(1 if result else 0)
                self.byte_budget(size,node,path);result.append(cloned)
            return result,size
        return value,self.byte_budget(len(_encoded(value)),node,path)

    def value(self,node,path=(),namespace='spec',emit=True,depth=None):
        self.node(node)
        depth=len(path) if depth is None else depth
        if node.kind=='reference':
            if not isinstance(node.value,str) or node.value not in self.bindings:
                self.fail(node,'Undefined or forward DSL reference: '+str(node.value),'VCHART_DSL_REFERENCE',path)
            bound=self.bindings[node.value]
            return self.clone(bound.value,node,path,namespace,emit,bound.declaration,depth)
        self.tick(node,path,depth)
        self.record(node,path,namespace,emit)
        if node.kind=='literal':
            value=node.value
            if type(value) not in (str,int,float,bool,type(None)) or type(value) is float and not math.isfinite(value):
                self.fail(node,'DSL literal must be a finite JSON scalar',path=path)
            try:size=len(_encoded(value))
            except (ValueError,OverflowError) as exc:
                self.fail(node,'Invalid JSON scalar: '+str(exc),path=path)
            return value,self.byte_budget(size,node,path)
        if node.kind=='array':
            result=[];size=2
            for index,child in enumerate(node.children):
                value,amount=self.value(child,(*path,index),namespace,emit,depth+1)
                size+=amount+(1 if result else 0)
                self.byte_budget(size,node,path);result.append(value)
            return result,size
        if node.kind=='object':
            result={};owners={};size=2
            for member in node.children:
                self.node(member)
                if member.kind!='member' or type(member.value) is not str or len(member.children)!=1:
                    self.fail(member,'Invalid object member AST',path=path)
                key=member.value
                if key in result:
                    self.fail(member,'Duplicate object key: '+key,'VCHART_DSL_DUPLICATE_WRITE',(*path,key),[owners[key]])
                value,amount=self.value(member.children[0],(*path,key),namespace,emit,depth+1)
                size+=len(_encoded(key))+1+amount+(1 if result else 0)
                self.byte_budget(size,node,path);result[key]=value;owners[key]=member
            return result,size
        if node.kind=='table':
            columns=node.value
            if (not isinstance(columns,tuple) or not columns or
                    any(type(c) is not str or not c for c in columns) or len(set(columns))!=len(columns)):
                self.fail(node,'Table columns must be nonempty, unique strings','VCHART_DSL_TABLE_ARITY',path)
            result=[];size=2
            for index,row in enumerate(node.children):
                self.node(row)
                if row.kind!='array' or len(row.children)!=len(columns):
                    self.fail(row,'Table row length differs from columns','VCHART_DSL_TABLE_ARITY',(*path,index))
                self.tick(row,(*path,index),depth+1)
                self.record(row,(*path,index),namespace,emit)
                record={};amount=2
                for column,child in zip(columns,row.children):
                    value,part=self.value(child,(*path,index,column),namespace,emit,depth+2)
                    amount+=len(_encoded(column))+1+part+(1 if record else 0)
                    self.byte_budget(amount,row,(*path,index));record[column]=value
                size+=amount+(1 if result else 0)
                self.byte_budget(size,node,path);result.append(record)
            return result,size
        self.fail(node,'Unknown DSL value kind: '+str(node.kind),path=path)

    def path(self,node):
        path=node.value
        if (not isinstance(path,tuple) or not path or type(path[0]) is not str or
                any(type(key) not in (str,int) or type(key) is int and key<0 for key in path)):
            self.fail(node,'Invalid property path AST')
        if len(path)>MAX_DEPTH:self.fail(node,'Property path exceeds depth128','VCHART_DSL_BUDGET',path)
        return path

    def guard(self,path,node,*,assign=False):
        for count in range(1,len(path)+1):
            prefix=path[:count]
            if prefix in self.atomic:
                code='VCHART_DSL_DUPLICATE_WRITE' if assign and prefix==path else 'VCHART_DSL_PATH_CONFLICT'
                self.fail(node,'Property is already owned by an atomic write',code,path,[self.atomic[prefix]])

    def mode(self,path,mode,node):
        previous=self.array_modes.get(path)
        if previous is not None and previous!=mode:
            self.fail(node,'Array literal/indexed/append modes cannot be mixed','VCHART_DSL_PATH_CONFLICT',path,
                      [self.opened[path]] if path in self.opened else [])
        self.array_modes[path]=mode

    def lookup(self,parent,key,path,node,scope=0):
        if isinstance(parent,dict):
            if type(key) is not str:self.fail(node,'Object path requires a string key','VCHART_DSL_PATH_CONFLICT',path)
            return key in parent,parent.get(key)
        if isinstance(parent,list):
            if type(key) is not int:self.fail(node,'Array path requires an integer index','VCHART_DSL_PATH_CONFLICT',path)
            # An axis/series block's already-appended ancestor is an internal
            # address. Only indices written in this property's own path select
            # indexed construction; revisiting its lexical block prefix does
            # not change the array's construction mode.
            if len(path)-1>=scope:self.mode(path[:-1],'indexed',node)
            if key>len(parent):self.fail(node,'Array index would create a hole','VCHART_DSL_PATH_CONFLICT',path)
            return key<len(parent),parent[key] if key<len(parent) else None
        self.fail(node,'Scalar cannot contain a property path','VCHART_DSL_PATH_CONFLICT',path)

    def put(self,parent,key,value,size,path,node):
        if isinstance(parent,dict):
            self.add_bytes(len(_encoded(key))+1+size+(1 if parent else 0),node,path)
            parent[key]=value
        else:
            self.add_bytes(size+(1 if parent else 0),node,path)
            parent.append(value)

    def container(self,path,node,kind=dict,mode=None,scope=0):
        self.guard(path,node)
        current=self.spec
        for index,key in enumerate(path):
            here=path[:index+1]
            desired=kind if index==len(path)-1 else list if type(path[index+1]) is int else dict
            exists,value=self.lookup(current,key,here,node,scope)
            if exists:
                if type(value) is not desired:
                    self.fail(node,'Path changes an existing container type','VCHART_DSL_PATH_CONFLICT',here,
                              [self.opened[here]] if here in self.opened else [])
            else:
                self.tick(node,here,len(here));value=desired()
                self.put(current,key,value,2,here,node)
                self.opened[here]=node;self.record(node,here,'spec',True)
            current=value
        if kind is list and mode is not None:self.mode(path,mode,node)
        return current

    def assignment(self,path,owner,value_node,scope=0):
        self.guard(path,owner,assign=True)
        parent=self.container(path[:-1],owner,list if type(path[-1]) is int else dict,
                              scope=scope) if len(path)>1 else self.spec
        exists,_=self.lookup(parent,path[-1],path,owner,scope)
        if exists:
            self.fail(owner,'Whole assignment cannot replace an opened container','VCHART_DSL_PATH_CONFLICT',path,
                      [self.opened[path]] if path in self.opened else [])
        value,size=self.value(value_node,path)
        self.put(parent,path[-1],value,size,path,owner)
        self.atomic[path]=owner

    def statements(self,nodes,prefix=(),root=True):
        for node in nodes:
            self.node(node)
            if node.kind=='assignment':
                if len(node.children)!=1:self.fail(node,'Assignment requires one value')
                self.assignment((*prefix,*self.path(node)),node,node.children[0],len(prefix))
            elif node.kind=='group':
                path=(*prefix,*self.path(node))
                self.container(path,node,scope=len(prefix))
                self.statements(node.children,path,False)
            elif not root:
                self.fail(node,'Only properties/configuration blocks are allowed in this block')
            elif node.kind=='let':
                if type(node.value) is not str or not node.value or len(node.children)!=1:
                    self.fail(node,'Invalid let declaration AST')
                if node.value in self.bindings:
                    self.fail(node,'DSL variable cannot be rebound: '+node.value,'VCHART_DSL_REFERENCE',
                              related=[self.bindings[node.value].declaration])
                value,_=self.value(node.children[0],emit=False)
                self.bindings[node.value]=_Binding(value,node)
            elif node.kind=='size':
                if len(node.children)!=2:self.fail(node,'Size requires width and height')
                for key,value in zip(('width','height'),node.children):
                    if value.kind!='literal' or type(value.value) not in (int,float):
                        self.fail(value,'Size requires numeric literals')
                    self.assignment((key,),node,value)
            elif node.kind in ('axis','series'):
                if type(node.value) is not str or not node.value:self.fail(node,'Invalid component header')
                name,key=('axes','orient') if node.kind=='axis' else ('series','type')
                array=self.container((name,),node,list,'append');index=len(array);path=(name,index)
                self.tick(node,path,len(path));self.put(array,index,{},2,path,node)
                self.opened[path]=node;self.record(node,path,'spec',True)
                # Header-owned key uses the statement's original span; no
                # fabricated token positions or generated JSON coordinates.
                literal=Node('literal',node.value,(),node.start,node.end)
                self.assignment((*path,key),node,literal,len(path))
                self.statements(node.children,path,False)
            elif node.kind=='resource':
                if (not isinstance(node.value,tuple) or len(node.value)!=2 or
                        node.value[0] not in ('map','svg') or type(node.value[1]) is not str or
                        not node.value[1] or len(node.children)!=1):
                    self.fail(node,'Invalid resource declaration','INVALID_RESOURCE')
                kind,name=node.value;identity=(kind,name)
                if identity in self.resource_owners:
                    self.fail(node,'Duplicate inline resource: '+kind+'/'+name,'VCHART_DSL_RESOURCE_CONFLICT',
                              (name,),[self.resource_owners[identity]])
                target=self.maps if kind=='map' else self.svgs
                value,size=self.value(node.children[0],(name,),kind)
                if (kind=='map' and not isinstance(value,dict)) or (kind=='svg' and type(value) is not str):
                    self.fail(node,'Map resources require objects; SVG resources require strings','INVALID_RESOURCE',(name,))
                self.put(target,name,value,size,(name,),node);self.resource_owners[identity]=node
            else:self.fail(node,'Unknown DSL statement: '+str(node.kind))

    def run(self,ast):
        self.node(ast)
        if ast.kind!='document' or not ast.children:
            self.fail(ast,'DSL document requires an initial type header')
        header=self.node(ast.children[0])
        if header.kind!='header':self.fail(header,'DSL document requires an initial type header')
        if type(header.value) is not str or not header.value:self.fail(header,'Invalid chart type header')
        literal=Node('literal',header.value,(),header.start,header.end)
        self.assignment(('type',),header,literal)
        self.statements(ast.children[1:])
        # Value construction already accounts for encoded bytes. The final
        # streaming guard is independent, including all three namespaces.
        encoder=json.JSONEncoder(ensure_ascii=True,allow_nan=False,separators=(',',':'))
        remaining=MAX_BYTES
        def serialize(value):
            nonlocal remaining
            parts=[]
            for chunk in encoder.iterencode(value):
                remaining-=len(chunk)
                if remaining<0:self.fail(ast,'Serialized DSL values exceed8MiB','VCHART_DSL_BUDGET')
                parts.append(chunk)
            return ''.join(parts)
        spec_json=serialize(self.spec);maps_json=serialize(self.maps);serialize(self.svgs)
        return LoweredVChart(spec_json,maps_json,tuple(self.svgs.items()),tuple(self.source_map),())


def lower_dsl(text, ast=None):
    """Compile frozen syntax to JSON/resources with original code-point spans."""
    if not isinstance(text,str):raise MermaidError('DSL source must be str',code='INVALID_INPUT')
    if len(text.encode('utf-8','surrogatepass'))>MAX_BYTES:
        raise dsl_error(text,0,len(text),'DSL document exceeds8MiB','VCHART_DSL_BUDGET')
    if ast is None:
        from .parser import parse_dsl
        ast=parse_dsl(text)
    return _Lowerer(text).run(ast)
