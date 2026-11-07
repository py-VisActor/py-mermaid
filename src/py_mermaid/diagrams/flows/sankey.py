"""Sankey RFC4180 grammar and actual d3-sankey flow geometry."""
from dataclasses import dataclass
import csv,io,math,re
from ...runtime.common import make_diagram,config_dict,error
from ..charts._syntax import theme
from types import SimpleNamespace
from ..charts._vchart_bridge import geometry

TABLEAU=('#4e79a7','#f28e2c','#e15759','#76b7b2','#59a14f','#edc949','#af7aa1','#ff9da7','#9c755f','#bab0ab')

@dataclass(frozen=True)
class Sankey:
    nodes:tuple[str,...]
    links:tuple[tuple[str,str,float],...]

def parse(document,config):
    source=document.cleaned.lstrip();head=re.match(r'(sankey-beta|sankey)[ \t]*\r?\n',source,re.I)
    if not head:raise error(document,0,'Sankey CSV requires header followed by newline')
    data=source[head.end():];nodes={};links=[]
    try:
        for row in csv.reader(io.StringIO(data,newline=''),strict=True):
            if not row:continue
            if len(row)!=3:raise error(document,0,'Sankey CSV requires exactly source,target,value')
            a,b,value=(s.strip() for s in row)
            match=re.match(r'^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?',value)
            if not match:raise error(document,0,'Sankey value produces non-finite flow','INVALID_SANKEY_VALUE')
            numeric=float(match[0])
            if not math.isfinite(numeric):raise error(document,0,'Sankey flow is not finite','INVALID_SANKEY_VALUE')
            nodes.setdefault(a,None);nodes.setdefault(b,None);links.append((a,b,numeric))
    except csv.Error as exc:raise error(document,0,'Invalid Sankey CSV: '+str(exc)) from exc
    if not links:raise error(document,len(document.cleaned),'Sankey CSV requires a record')
    return make_diagram('sankey',document,config,Sankey(tuple(nodes),tuple(links)))

async def build(diagram,p):
    c=config_dict(diagram);q=c.get('sankey',{});width=q.get('width',600);height=q.get('height',400);show=q.get('showValues',True);alignment=q.get('nodeAlignment','justify')
    raw_nodes,raw_links=geometry('sankey',diagram.source,diagram.model.nodes,diagram.model.links,width,height,node_width=q.get('nodeWidth',10),node_gap=q.get('nodePadding',12)+(15 if show else 0),alignment=alignment)
    nodes=[SimpleNamespace(**v) for v in raw_nodes];by_id={n.id:n for n in nodes}
    links=[SimpleNamespace(**{**v,'source':by_id[v['source']],'target':by_id[v['target']]}) for v in raw_links]
    colors={n.id:q.get('nodeColors',{}).get(n.id,TABLEAU[i%len(TABLEAU)]) for i,n in enumerate(nodes)}
    central=max(nodes,key=lambda n:n.value).layer if nodes else 0
    for n in nodes:
        if n.y1>=n.y0:p.rect(n.x0,n.y0,n.x1-n.x0,n.y1-n.y0,fill=colors[n.id],stroke='none',line_width=0,id='node-'+n.id,role='sankey-node')
    outlined=q.get('labelStyle','legacy')=='outlined'
    for n in nodes:
        right=n.layer>=central if outlined else n.x0<width/2;x=n.x1+6 if right else n.x0-6;align='left' if right else 'right';value=math.floor(n.value*100+.5)/100
        label=n.id+('\n'+q.get('prefix','')+f'{value:g}'+q.get('suffix','') if show else '')
        text=p.measure(label,size=14,html=False);y=(n.y0+n.y1)/2-(text.ascent if show else text.ascent-14*.35)
        if outlined:
            style=p.style(('sankey-label-bg',),tag='text',id='outline-'+n.id,base={'text_color':theme(c,'textColor','#333'),'text_stroke_color':theme(c,'mainBkg',theme(c,'background','#fff')),'text_stroke_width':4,'line_join':'round','font_size':14})
            p.text(text,x,y,align=align,html=False,style=style,id='outline-'+n.id)
        p.text(text,x,y,align=align,html=False,color=theme(c,'textColor','#333'),id='label-'+n.id)
    for link in links:
        a=link.source;b=link.target;mid=(a.x1+b.x0)/2;path=f'M{a.x1:g},{link.y0:g}C{mid:g},{link.y0:g} {mid:g},{link.y1:g} {b.x0:g},{link.y1:g}';mode=q.get('linkColor','gradient')
        color=colors[a.id] if mode in ('source','gradient') else colors[b.id] if mode=='target' else mode
        base={'fill':'none','stroke':color,'stroke_width':max(1,link.width),'stroke_opacity':.5,'blend_mode':'multiply'}
        if mode=='gradient':base.update(stroke_gradient=((0,colors[a.id]),(1,colors[b.id])),gradient_direction=(0,0,1,0))
        style=p.style(('link',),tag='path',id='flow-'+str(link.index),base=base)
        p.path(path,style=style,id='flow-'+str(link.index),role='sankey-link')
    return p.finish(padding=0,layout={'kind':'sankey','nodes':tuple((n.id,n.x0,n.y0,n.x1,n.y1,n.value,n.layer) for n in nodes),'links':tuple((l.index,l.source.id,l.target.id,l.width,l.y0,l.y1) for l in links)})
