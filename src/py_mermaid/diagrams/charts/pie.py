"""Fixed Pie Langium/DB and d3 pie/arc static renderer."""
from dataclasses import dataclass
import math
import re
from ...runtime.common import make_diagram,config_dict,error
from ._syntax import statements,common_statement,scalar,theme,number,palette
from ._scales import arc
from ._vchart_bridge import geometry

@dataclass(frozen=True)
class Pie:
    sections:tuple[tuple[str,float],...]
    show_data:bool=False
    title:str=''
    accessibility:tuple=()

def parse(document,config):
    rows=statements(document);meta={'title':document.title};sections={};show=False
    if not rows or rows[0][0].value!='pie':raise error(document,0,'Expected pie')
    head=rows.pop(0)[1:]
    if head and head[0].value=='showData':show=True;head=head[1:]
    if head:rows.insert(0,head)
    for row in rows:
        if common_statement(row,meta):continue
        if len(row)!=3 or not row[0].quoted or row[1].value!=':':raise error(document,row[0].offset,'Expected a quoted pie section followed by : value')
        if not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?',row[2].value):raise error(document,row[2].offset,'Invalid pie numeric literal')
        value=scalar(document,row[2])
        if value<0:raise error(document,row[2].offset,f'"{row[0].value}" has invalid value: {value}. Negative values are not allowed in pie charts. All slice values must be >= 0.','INVALID_PIE_VALUE')
        sections.setdefault(row[0].value,value)
    return make_diagram('pie',document,config,Pie(tuple(sections.items()),show,meta.get('title',''),tuple((k,v) for k,v in meta.items() if k!='title')))

async def build(diagram,p):
    model=diagram.model;config=config_dict(diagram);cfg=config.get('pie',{});colors=palette(config,'pie')
    center=225.;r=185.;outer=number(theme(config,'pieOuterStrokeWidth',2),2)
    total=sum(v for _,v in model.sections);sections=[(k,v) for k,v in model.sections if total and v/total>=.01]
    kept=sum(v for _,v in sections);hole=cfg.get('donutHole',0);hole=hole if 0<hole<=.9 else 0
    position=cfg.get('legendPosition','right');labelsize=number(theme(config,'pieSectionTextSize',17),17)
    legends=[p.measure(f'{k} [{v:g}]' if model.show_data else k,size=number(theme(config,'pieLegendTextSize',17),17)) for k,v in model.sections]
    longest=max((t.width for t in legends),default=0);legendh=22*len(legends);dx=dy=0.;width=490.;height=450.
    if position=='top':dy=legendh+22;height+=legendh
    elif position=='bottom':height+=legendh
    elif position=='left':dx=longest+22;width+=dx
    elif position not in ('center',):width+=longest+22
    cx=center+dx;cy=center+dy
    p.ellipse(cx,cy,r+outer/2,r+outer/2,fill='none',stroke=theme(config,'pieOuterStrokeColor','#333'),line_width=outer,id='pie-outer')
    vchart_arcs=geometry('pie',diagram.source,[v for _,v in sections],r,hole)
    section_order={k:i for i,(k,v) in enumerate(model.sections)}
    for (k,v),(vstart,vend,_,_) in zip(sections,vchart_arcs):
        angle=vstart+math.pi/2;end=vend+math.pi/2;idx=section_order[k];highlight=cfg.get('highlightSlice')==k;radius=r*1.05 if highlight else r
        p.path(arc(cx,cy,radius,angle,end,hole*radius),fill=colors[idx%len(colors)],stroke=theme(config,'pieStrokeColor','#fff'),line_width=number(theme(config,'pieStrokeWidth',2),2),opacity=1 if highlight else float(theme(config,'pieOpacity',.7)),id='slice-'+str(idx),role='pie-slice')
        mid=(angle+end)/2;distance=r*cfg.get('textPosition',.75)
        label=p.measure(str(math.floor(v/total*100+.5))+'%',size=labelsize)
        p.text(label,cx+math.sin(mid)*distance,cy-math.cos(mid)*distance-label.height/2,align='center',color=theme(config,'pieSectionTextColor','#333'),id='slice-label-'+str(idx))
    if model.title:
        # pieRenderer's y=25 is an SVG alphabetic baseline, not a top edge.
        title=p.measure(model.title,size=number(theme(config,'pieTitleTextSize',25),25))
        p.text(title,center,25-title.ascent,align='center',color=theme(config,'pieTitleTextColor','#333'),role='title')
    for i,((label,value),text) in enumerate(zip(model.sections,legends)):
        if position=='center':x=center-longest/2-22;y=center+i*22-legendh/2
        elif position=='top':x=center-longest/2-22;y=center+i*22-r
        elif position=='bottom':x=center-longest/2-22;y=center+i*22+r+22
        elif position=='left':x=center-r-22;y=center+i*22-legendh/2
        else:x=center+216;y=center+i*22-legendh/2
        p.rect(x,y,18,18,fill=colors[i%len(colors)],stroke=colors[i%len(colors)],id='legend-'+str(i))
        p.text(text,x+22,y+14-text.ascent,color=theme(config,'pieLegendTextColor','#333'),id='legend-text-'+str(i))
    return p.finish(width=width,height=height,padding=0,layout={'kind':'pie','angles':tuple((k,v/kept*math.tau) for k,v in sections) if kept else ()})
