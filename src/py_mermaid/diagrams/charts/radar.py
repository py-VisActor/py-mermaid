"""Radar Langium semantics and source radial/Catmull-Rom geometry."""
from dataclasses import dataclass
import math,re
from ...runtime.common import make_diagram,config_dict,error
from ._syntax import statements,common_statement,words,split,scalar,theme,number,palette
from ._scales import closed_round

@dataclass(frozen=True)
class Radar:
    axes:tuple[tuple[str,str],...]
    curves:tuple[tuple[str,str,tuple[float,...]],...]
    options:tuple[tuple[str,object],...]
    title:str=''
    accessibility:tuple=()

def _named(document,seq):
    if not seq or seq[0].quoted or not re.fullmatch(r'\w(?:[-\w]*\w)?',seq[0].value):raise error(document,seq[0].offset if seq else 0,'Expected radar identifier')
    name=seq[0].value
    if len(seq)==1:return name,name
    if len(seq)!=4 or seq[1].value!='[' or not seq[2].quoted or seq[3].value!=']':raise error(document,seq[1].offset,'Expected radar ["label"]')
    return name,seq[2].value

def parse(document,config):
    rows=statements(document);meta={'title':document.title};axes=[];curves=[];raw=[]
    options={'showLegend':True,'ticks':5,'max':None,'min':0,'graticule':'circle'}
    if not rows or rows[0][0].value!='radar-beta':raise error(document,0,'Expected radar-beta')
    head=rows.pop(0)[1:]
    if head and head[0].value==':':head=head[1:]
    if head:rows.insert(0,head)
    fragments=[]
    for row in rows:
        if row[0].value.lower() in ('title','acctitle','accdescr'):fragments.append(row);continue
        start=depth=0
        for i,t in enumerate(row):
            if i and depth==0 and not t.quoted and t.value in ('axis','curve',*options):fragments.append(row[start:i]);start=i
            if not t.quoted and t.value in '[{':depth+=1
            elif not t.quoted and t.value in ']}':depth-=1
        fragments.append(row[start:])
    rows=fragments
    for row in rows:
        if common_statement(row,meta):continue
        cmd=row[0].value
        if cmd=='axis':
            for group in split(row[1:]):axes.append(_named(document,group))
        elif cmd=='curve':
            for group in split(row[1:]):
                opening=next((i for i,t in enumerate(group) if t.value=='{' and not t.quoted),-1)
                if opening<0 or group[-1].value!='}':raise error(document,row[0].offset,'Expected radar curve entries in braces')
                name,label=_named(document,group[:opening]);entries=[]
                for entry in split(group[opening+1:-1]):
                    if len(entry)==1:entries.append((None,scalar(document,entry[0])))
                    elif len(entry) in (2,3) and (len(entry)==2 or entry[1].value==':'):entries.append((entry[0].value,scalar(document,entry[-1])))
                    else:raise error(document,entry[0].offset if entry else group[opening].offset,'Invalid radar curve entry')
                    if entries[-1][1]<0:raise error(document,entry[-1].offset,'Radar NUMBER grammar requires nonnegative values')
                    if not re.fullmatch(r'(?:[0-9]+\.[0-9]+|0|[1-9][0-9]*)',entry[-1].value):raise error(document,entry[-1].offset,'Invalid radar NUMBER literal')
                if not entries:raise error(document,group[opening].offset,'Radar curves require entries')
                raw.append((name,label,entries))
        else:
            for group in split(row):
                if len(group)!=2 or group[0].value not in options:raise error(document,group[0].offset if group else row[0].offset,'Unknown radar option')
                name=group[0].value;value=group[1]
                if name=='showLegend':
                    if value.value not in ('true','false'):raise error(document,value.offset,'Expected radar boolean')
                    options[name]=value.value=='true'
                elif name=='graticule':
                    if value.value not in ('circle','polygon'):raise error(document,value.offset,'Expected circle or polygon graticule')
                    options[name]=value.value
                else:
                    numeric=scalar(document,value)
                    if not re.fullmatch(r'(?:[0-9]+\.[0-9]+|0|[1-9][0-9]*)',value.value):raise error(document,value.offset,'Radar options require nonnegative NUMBER')
                    options[name]=min(32,numeric) if name=='ticks' else numeric
    # Source parser populates all axes before resolving any curve references.
    names=[name for name,label in axes]
    for name,label,entries in raw:
        if entries[0][0] is None:
            if any(axis is not None for axis,v in entries):raise error(document,0,'Cannot mix numeric and named radar entries')
            values=tuple(v for axis,v in entries)
        else:
            if not axes:raise error(document,0,'Axes must be populated before curves for reference entries')
            if any(axis not in names for axis,v in entries):raise error(document,0,'Unresolved radar axis reference')
            values=[]
            for axis,label_ in axes:
                matches=[v for key,v in entries if key==axis]
                if not matches:raise error(document,0,'Missing entry for axis '+label_)
                values.append(matches[0])
            values=tuple(values)
        curves.append((name,label,values))
    return make_diagram('radar',document,config,Radar(tuple(axes),tuple(curves),tuple(options.items()),meta.get('title',''),tuple((k,v) for k,v in meta.items() if k!='title')))

async def build(diagram,p):
    model=diagram.model;config=config_dict(diagram);cfg=config.get('radar',{});style=dict(config.get('themeVariables',{}).get('radar',{}));style.update({k:v for k,v in cfg.items() if k in ('axisColor','axisLabelFontSize','axisStrokeWidth','graticuleColor','graticuleOpacity','graticuleStrokeWidth','curveOpacity','curveStrokeWidth','legendFontSize')})
    options=dict(model.options);width=cfg.get('width',600);height=cfg.get('height',600)
    ml=cfg.get('marginLeft',50);mr=cfg.get('marginRight',50);mt=cfg.get('marginTop',50);mb=cfg.get('marginBottom',50)
    cx=ml+width/2;cy=mt+height/2;radius=min(width,height)/2;n=len(model.axes);colors=palette(config)
    def points(r):return tuple((cx+r*math.cos(math.tau*i/n-math.pi/2),cy+r*math.sin(math.tau*i/n-math.pi/2)) for i in range(n))
    ticks=options['ticks']
    for i in range(math.ceil(ticks)):
        r=radius*(i+1)/ticks
        kwargs=dict(fill=style.get('graticuleColor','#ddd'),stroke=style.get('graticuleColor','#ddd'),line_width=style.get('graticuleStrokeWidth',1),opacity=style.get('graticuleOpacity',.3),id='graticule-'+str(i))
        if options['graticule']=='circle':p.ellipse(cx,cy,r,r,**kwargs)
        else:p.polygon(points(r),**kwargs)
    for i,(name,label) in enumerate(model.axes):
        a=math.tau*i/n-math.pi/2;c=math.cos(a);s=math.sin(a)
        p.line(cx,cy,cx+radius*cfg.get('axisScaleFactor',1)*c,cy+radius*cfg.get('axisScaleFactor',1)*s,stroke=style.get('axisColor','#333'),line_width=style.get('axisStrokeWidth',1),id='axis-'+name)
        text=p.measure(label,size=style.get('axisLabelFontSize',16));x=cx+(radius*cfg.get('axisLabelFactor',1.05)+4)*c;y=cy+(radius*cfg.get('axisLabelFactor',1.05)+4)*s
        align='left' if c>.01 else 'right' if c<-.01 else 'center';y-=text.ascent if s<-.01 else 0 if s>.01 else text.height/2
        p.text(text,x,y,align=align,color=style.get('axisColor','#333'),id='axis-label-'+name)
    maximum=options['max'] if options['max'] is not None else max((v for name,label,values in model.curves for v in values),default=-math.inf);minimum=options['min']
    for i,(name,label,values) in enumerate(model.curves):
        if len(values)==n and n:
            if maximum==minimum:raise error(diagram.source,0,'Radar min/max produce non-finite radius','INVALID_GEOMETRY')
            pts=tuple((cx+radius*(min(max(v,minimum),maximum)-minimum)/(maximum-minimum)*math.cos(math.tau*j/n-math.pi/2),cy+radius*(min(max(v,minimum),maximum)-minimum)/(maximum-minimum)*math.sin(math.tau*j/n-math.pi/2)) for j,v in enumerate(values))
            kwargs=dict(fill=colors[i%len(colors)],stroke=colors[i%len(colors)],line_width=style.get('curveStrokeWidth',2),opacity=style.get('curveOpacity',.5),id='curve-'+name)
            if options['graticule']=='circle':p.path(closed_round(pts,cfg.get('curveTension',.17)),**kwargs)
            else:p.polygon(pts,**kwargs)
        if options['showLegend']:
            x=cx+(width/2+mr)*.75;y=cy-(height/2+mt)*.75+i*20
            p.rect(x,y,12,12,fill=colors[i%len(colors)],stroke=colors[i%len(colors)],opacity=style.get('curveOpacity',.5),id='legend-'+name)
            p.text(label,x+16,y,size=style.get('legendFontSize',14),id='legend-label-'+name)
    if model.title:p.text(model.title,cx,cy-height/2-mt,align='center',color=theme(config,'titleColor','#333'),role='title')
    return p.finish(width=width+ml+mr,height=height+mt+mb,padding=0,layout={'kind':'radar','axisCount':n,'min':minimum,'max':maximum})
