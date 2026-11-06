"""Block Jison hierarchy, source equal-cell recursive sizing and shape rendering."""
from __future__ import annotations
from dataclasses import dataclass,replace
import re
import math
from ...runtime.common import make_diagram,error,config_dict,sanitize_text
from ...model.flowchart import Box,Point
from ..modeling._support import label_style,styles,number,node_style,theme,clip_endpoint
from ._block_arrows import points as arrow_points


@dataclass(frozen=True)
class BlockNode:
    id:str
    label:str
    shape:str='na'
    parent:str='root'
    span:int=1
    columns:int=-1
    directions:tuple[str,...]=()
    children:tuple[str,...]=()
    classes:tuple[str,...]=()
    styles:tuple=()
    color_index:int|None=None


@dataclass(frozen=True)
class BlockEdge:
    id:str
    source:str
    target:str
    label:str=''
    start_marker:str='open'
    end_marker:str='none'
    thick:bool=False
    dotted:bool=False


@dataclass(frozen=True)
class BlockModel:
    nodes:tuple[BlockNode,...]
    edges:tuple[BlockEdge,...]
    definitions:tuple=()
    acc_title:str=''
    acc_description:str=''


_SHAPES={'[]':'square','()':'round','(())':'circle','>]':'odd','{}':'diamond','{{}}':'hexagon','([])':'stadium','[[]]':'subroutine','[()]':'cylinder','((()))':'doublecircle','[//]':'lean_right','[\\\\]':'lean_left','[/\\]':'trapezoid','[\\/]':'inv_trapezoid','<[]>':'block_arrow'}
_OPENERS=tuple(sorted(('(-','-)',')','))','(((','((','{{','{','>','([','(','[[','[|','[(', ')))','[\\','[/','[','<['),key=len,reverse=True))
_CLOSERS=tuple(sorted(('(((', ')))','))','}}','}','(-','-)','((',']]','(','])','\\]','/]',')]',')',']>',']'),key=len,reverse=True))
_LINK=re.compile(r'[xo<]?--+[-xo>]|[xo<]?==+[=xo>]|[xo<]?-?\.+-[xo>]?|~~~+')


class _Parser:
    def __init__(self,document,config):self.doc=document;self.config=config;self.text=document.cleaned;self.pos=0;self.seq=0;self.raw=[];self.edges=[];self.definitions={};self.actions=[];self.edge_counts={};self.acc_title='';self.acc_description=''
    def gap(self):
        while self.pos<len(self.text):
            m=re.match(r'\s+|%%[^\r\n]*',self.text[self.pos:])
            if not m:break
            self.pos+=m.end()
    def generated(self):self.seq+=1;return '__block_'+str(self.seq)
    def expect(self,token):
        if not self.text.startswith(token,self.pos):raise error(self.doc,self.pos,'Expected '+token)
        self.pos+=len(token)
    def node(self,parent):
        self.gap();m=re.match(r'[^\(\[\n\-\)\{\}\s<>:=]+',self.text[self.pos:])
        if not m:raise error(self.doc,self.pos,'Expected block ID')
        id=m[0];self.pos+=m.end();self.gap();opener=next((t for t in _OPENERS if self.text.startswith(t,self.pos)),None);label=id;shape='na';directions=()
        if opener:
            self.pos+=len(opener);self.gap()
            # Jison nodeShapeNLabel consumes STR, not arbitrary NODE_DESCR.
            self.expect('"');start=self.pos
            if self.text.startswith('`',start):raise error(self.doc,start,'Markdown lexical tokens are not block STR arguments')
            end=self.text.find('"',start)
            if end<0:raise error(self.doc,start,'Unterminated block label')
            label=self.text[start:end];self.pos=end+1
            closer=next((t for t in _CLOSERS if self.text.startswith(t,self.pos)),None)
            if opener=='<[':
                self.expect(']>');self.gap();self.expect('(');end=self.text.find(')',self.pos)
                if end<0:raise error(self.doc,self.pos,'Unterminated block arrow directions')
                dirs=tuple(v.strip() for v in self.text[self.pos:end].split(',') if v.strip())
                if not dirs or any(v not in ('right','left','x','y','up','down') for v in dirs):raise error(self.doc,self.pos,'Invalid block arrow direction')
                directions=dirs;shape='block_arrow';self.pos=end+1
            else:
                if not closer:raise error(self.doc,self.pos,'Expected block closing delimiter')
                self.pos+=len(closer);shape=_SHAPES.get(opener+closer,'na')
        self.gap();span=1;m=re.match(r':([0-9]+)',self.text[self.pos:])
        if m:span=int(m[1]);self.pos+=m.end()
        return BlockNode(id,sanitize_text(label or id,self.config),shape,parent,span,directions=directions)
    def document(self,parent='root',nested=False):
        out=[];columns=-1
        while True:
            self.gap()
            if self.pos>=len(self.text):
                if nested:raise error(self.doc,self.pos,'Unterminated composite block')
                break
            m=re.match(r'end\b',self.text[self.pos:])
            if m:
                if not nested:raise error(self.doc,self.pos,'Unexpected block end')
                self.pos+=m.end();break
            m=re.match(r'columns\s+(auto|[0-9]+)\b',self.text[self.pos:])
            if m:columns=-1 if m[1]=='auto' else int(m[1]);self.pos+=m.end();continue
            m=re.match(r'(classDef|class|style)\s+([^\r\n]+)',self.text[self.pos:])
            if m:
                self.pos+=m.end();words=m[2].split(None,1)
                if len(words)!=2:raise error(self.doc,self.pos,'Incomplete block style statement')
                if m[1]=='classDef':self.definitions[words[0]]=self.definitions.get(words[0],())+styles(words[1])
                else:self.actions.append((m[1],tuple(v.strip() for v in words[0].split(',')),words[1]))
                continue
            m=re.match(r'accTitle\s*:\s*([^\n]*)|accDescr\s*:\s*([^\n]*)|accDescr\s*\{([^}]*)\}',self.text[self.pos:])
            if m:
                if m[1] is not None:self.acc_title=m[1]
                else:self.acc_description=m[2] if m[2] is not None else m[3]
                self.pos+=m.end();continue
            m=re.match(r'space(?::([0-9]+))?\b',self.text[self.pos:])
            if m:
                self.pos+=m.end();base=self.generated()
                for i in range(int(m[1] or '1')):out.append(BlockNode(base+'-'+str(i),'','space',parent))
                continue
            m=re.match(r'block(?::|\b)',self.text[self.pos:])
            if m:
                explicit=m[0].endswith(':');self.pos+=m.end();head=self.node(parent) if explicit else BlockNode(self.generated(),'','composite',parent);children,cols=self.document(head.id,True);out.append(replace(head,shape='composite',columns=cols,children=tuple(n.id for n in children)));self.raw.extend(children);continue
            head=self.node(parent);out.append(head)
            while True:
                self.gap();link=_LINK.match(self.text,self.pos);label=''
                if link:op=link[0];self.pos=link.end()
                else:
                    start=re.match(r'[xo<]?(?:--|==|-\.)\s*"([^"\n]*)"\s*',self.text[self.pos:])
                    if not start:break
                    label=start[1];self.pos+=start.end();link=_LINK.match(self.text,self.pos)
                    if not link:raise error(self.doc,self.pos,'Expected block label ending link')
                    op=link[0];self.pos=link.end()
                target=self.node(parent);out.append(target);key=head.id+'-'+target.id;count=self.edge_counts.get(key,0)+1;self.edge_counts[key]=count
                self.edges.append(BlockEdge(str(count)+'-'+key,head.id,target.id,sanitize_text(label,self.config),{'x':'cross','o':'circle','<':'point'}.get(op[0],'open'),{'x':'cross','o':'circle','>':'point'}.get(op[-1],'none'),'==' in op,'.-' in op));head=target
        return out,columns


def parse(document,config):
    p=_Parser(document,config);m=re.match(r'\s*block(?:-beta)?\b',document.cleaned)
    if not m:raise error(document,0,'Expected block header')
    p.pos=m.end();children,cols=p.document();raw=[BlockNode('root','','composite',children=tuple(n.id for n in children),columns=cols),*children,*p.raw];nodes={};order=[];slot=0
    # DB's first occurrence owns placement, later declarations update shape/label.
    def visit(id,path=()):
        nonlocal slot
        if id in path:raise error(document,0,'Cyclic block hierarchy','INVALID_PARENT')
        source=next((n for n in raw if n.id==id),None)
        if source is None:return
        if id not in nodes:
            node=source
            if node.shape=='composite' and id!='root':node=replace(node,color_index=slot);slot+=1
            nodes[id]=node;order.append(id)
            for child in source.children:visit(child,(*path,id))
    visit('root')
    for node in raw:
        if node.id not in nodes:continue
        old=nodes[node.id]
        if node is not old and node.shape!='na':nodes[node.id]=replace(old,shape=node.shape,label=node.label if node.label!=node.id else old.label)
    # Filter duplicates after identity aggregation, preserving the first parent.
    for id in tuple(nodes):nodes[id]=replace(nodes[id],children=tuple(dict.fromkeys(c for c in nodes[id].children if c in nodes and nodes[c].parent==id)))
    for action,ids,value in p.actions:
        for id in ids:
            if id not in nodes:
                if action=='style':raise error(document,0,'Style references an unknown block','UNKNOWN_REFERENCE')
                nodes[id]=BlockNode(id,id);order.append(id)
            nodes[id]=replace(nodes[id],classes=(*nodes[id].classes,value) if action=='class' else nodes[id].classes,styles=styles(value) if action=='style' else nodes[id].styles)
    return make_diagram('block',document,config,BlockModel(tuple(nodes[id] for id in order),tuple(p.edges),tuple(p.definitions.items()),p.acc_title,p.acc_description))


async def build(diagram,painter):
    from ...geometry.shapes import shape_outline_intersection
    config=config_dict(diagram);conf=config.get('block') or {};padding=number(conf.get('padding'),8);model=diagram.model;lookup={n.id:n for n in model.nodes};size={};labels={};styles_by_id={};natural={};positions={};painter.rough_enabled=True
    for node in model.nodes:
        if node.id=='root' or node.shape=='space':size[node.id]=[0.,0.];continue
        s=node_style(painter,config,('node','flowchart-label',*(node.classes or ('default',))),node.id,model.definitions,node.styles,index=node.color_index);styles_by_id[node.id]=s;label=painter.measure(node.label,style=label_style(s));labels[node.id]=label
        if node.shape=='block_arrow':pts,w,h=arrow_points(node.directions,label.width,label.height,padding)
        else:
            shape='square' if node.shape in ('na','composite') else node.shape;g=painter.shape_geometry(shape,label.width,label.height,padding=0 if node.shape=='composite' else padding);natural[node.id]=g;w,h=g.width,g.height
        size[node.id]=[w,h]
    def sizes(id,sibling_w=0.,sibling_h=0.):
        node=lookup[id]
        if not node.children:return
        for child in node.children:sizes(child)
        maxw=max((size[c][0]/(lookup[c].span or 1) for c in node.children if lookup[c].shape!='space'),default=0);maxh=max((size[c][1] for c in node.children if lookup[c].shape!='space'),default=0)
        for child in node.children:
            span=lookup[child].span;size[child]=[maxw*span+padding*(span-1),maxh]
        for child in node.children:sizes(child,maxw,maxh)
        columns=node.columns;num=sum(lookup[c].span for c in node.children);xs=columns if columns>0 and columns<num else len(node.children)
        if xs==0:return
        ys=math.ceil(num/xs);w=xs*(maxw+padding)+padding;h=ys*(maxh+padding)+padding
        if w<sibling_w:
            w,h=sibling_w,sibling_h;cw=(w-xs*padding-padding)/xs;ch=(h-ys*padding-padding)/ys
            for c in node.children:size[c]=[cw,ch]
        if w<size[id][0]:
            w=size[id][0];num=min(len(node.children),columns) if columns>0 else len(node.children)
            for c in node.children:size[c][0]=(w-num*padding-padding)/num
        size[id]=[w,h]
    sizes('root');positions['root']=(0.,0.)
    def place(id):
        node=lookup[id];columns=node.columns
        if columns==0:raise error(diagram.source,0,'Columns must be an integer not equal to zero','INVALID_BLOCK_COLUMNS')
        row_heights={};col=0
        for child in node.children:
            row=col//columns if columns>0 else 0;row_heights[row]=max(row_heights.get(row,0),size[child][1]);col+=min(lookup[child].span,columns-col%columns) if columns>0 else lookup[child].span
        offsets={};yoff=0
        for row,h in sorted(row_heights.items()):offsets[row]=yoff;yoff+=h+padding
        x,y=positions[id];start=x-size[id][0]/2 if x else -padding;row_before=0;col=0
        for child in node.children:
            row=col//columns if columns>0 else 0
            if row!=row_before:start=x-size[id][0]/2 if x else -padding;row_before=row
            w,h=size[child];cx=start+padding+w/2;cy=y-size[id][1]/2+offsets[row]+row_heights[row]/2+padding;positions[child]=(cx,cy);start=cx+w/2;place(child);col+=min(lookup[child].span,columns-col%columns) if columns>0 else lookup[child].span
    place('root');boxes={id:Box(x-size[id][0]/2,y-size[id][1]/2,*size[id]) for id,(x,y) in positions.items() if id!='root'}
    def draw(id):
        node=lookup[id]
        if id!='root' and node.shape!='space':
            b=boxes[id];s=styles_by_id[id];label=labels[id]
            if node.shape=='block_arrow':
                pts,w,h=arrow_points(node.directions,label.width,label.height,padding,b.width if node.span>1 else None);painter.polygon(tuple((b.x+(b.width-w)/2+x,b.y+(b.height-h)/2+y) for x,y in pts),style=s,id=id)
            elif node.shape in ('na','square','round','composite'):painter.rect(b.x,b.y,b.width,b.height,style=s,radius=5 if node.shape=='round' else 0,id=id)
            else:
                g=natural[id];transform=(b.width/g.width,0,0,b.height/g.height,b.x,b.y);painter.path(g.outline,style=s,transform=transform,id=id)
                for d in g.details:painter.path(d,style=replace(s,fill='none'),transform=transform,id=id)
            painter.text(label,b.x+(b.width-label.width)/2,b.y+(b.height-label.height)/2,style=s,id=id)
        for child in node.children:draw(child)
    draw('root');palette=theme(config)
    for edge in model.edges:
        if edge.source not in boxes or edge.target not in boxes:continue # exact source insertEdges guard
        a,b=boxes[edge.source],boxes[edge.target];ac=Point(a.x+a.width/2,a.y+a.height/2);bc=Point(b.x+b.width/2,b.y+b.height/2)
        def intersect(id,box,center,toward):
            n=lookup[id]
            if n.shape in ('na','composite','square','round','block_arrow'):return clip_endpoint(box,toward)
            return shape_outline_intersection(n.shape,box,center,toward)
        start=intersect(edge.source,a,ac,bc);end=intersect(edge.target,b,bc,ac);s=painter.style(('flowchart-link','edge-thickness-thick' if edge.thick else 'edge-thickness-normal','edge-pattern-dotted' if edge.dotted else 'edge-pattern-solid'),tag='path',id=edge.id,base={'fill':'none','stroke':palette['edge'],'stroke_width':3.5 if edge.thick else 1.5,'dash':(3.,3.) if edge.dotted else ()});painter.polyline((start,Point((ac.x+bc.x)/2,(ac.y+bc.y)/2),end),style=s,id=edge.id)
        for at,other,marker in ((start,end,edge.start_marker),(end,start,edge.end_marker)):
            if marker not in ('none','open'):painter.marker(at.x,at.y,at.x-other.x,at.y-other.y,kind=marker,color=s.stroke,id=edge.id)
        if edge.label:
            label=painter.measure(edge.label);painter.text(label,(ac.x+bc.x-label.width)/2,(ac.y+bc.y-label.height)/2,id=edge.id,role='edge-label')
    return painter.finish(layout=('block-recursive-grid',tuple(boxes.items())),padding=5)
