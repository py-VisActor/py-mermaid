"""XYChart grammar, source DB transformations and measured component allocator."""
from dataclasses import dataclass
import math
import re
from ...runtime.common import make_diagram,config_dict,error
from ._syntax import statements,common_statement,words,split,scalar
from ._xyaxis import Axis as SourceAxis,text_value
from ._vchart_bridge import geometry


class Axis(SourceAxis):
    def scale(self,value):
        a,b=self.range
        return geometry('position',self.geometry_source,self.kind,self.domain,(a+self.outer,b-self.outer),value,reverse=self.position=='left')

@dataclass(frozen=True)
class Plot:
    kind:str
    title:str
    data:tuple[tuple[str|float,float|None],...]
    labels:tuple[str,...]=()

@dataclass(frozen=True)
class XYChart:
    title:str
    orientation:str
    xkind:str
    xdomain:tuple
    xtitle:str
    ydomain:tuple[float,float]
    ytitle:str
    plots:tuple[Plot,...]
    accessibility:tuple=()

def _text(document,seq):
    if len(seq)==1 and seq[0].quoted:
        value=seq[0].value
        return value[1:-1] if len(value)>=2 and value.startswith('`') and value.endswith('`') else value
    if any(t.quoted or not re.fullmatch(r'[A-Za-z0-9+*=.#_&-]+',t.value) for t in seq):raise error(document,seq[0].offset if seq else 0,'Invalid unquoted XYChart text')
    # Jison ignores whitespace; alphaNum concatenates its lexical tokens.
    return ''.join(t.value for t in seq)

def parse(document,config):
    rows=statements(document);meta={'title':document.title};orientation=config.get('xyChart',{}).get('chartOrientation','vertical');xkind='band';xdomain=();xtitle=ytitle='';ydomain=(math.inf,-math.inf);hasx=hasy=False;plots=[]
    if not rows or rows[0][0].value.lower() not in ('xychart-beta','xychart'):raise error(document,0,'Expected xychart-beta or xychart')
    header=rows.pop(0)[1:]
    if header and header[0].value.lower() in ('vertical','horizontal'):orientation=header[0].value.lower();header=header[1:]
    if header:rows.insert(0,header)
    fragments=[]
    for row in rows:
        if row[0].value.lower() in ('acctitle','accdescr'):fragments.append(row);continue
        start=depth=0
        for i,t in enumerate(row):
            if i and not depth and not t.quoted and t.value.lower() in ('title','x-axis','y-axis','bar','line'):fragments.append(row[start:i]);start=i
            if not t.quoted and t.value=='[':depth+=1
            elif not t.quoted and t.value==']':depth-=1
        fragments.append(row[start:])
    rows=fragments
    for row in rows:
        if row[0].value.lower()=='title':meta['title']=_text(document,row[1:]);continue
        if common_statement(row,meta):continue
        name=row[0].value.lower();rest=row[1:]
        if name in ('x-axis','y-axis'):
            bracket=next((i for i,t in enumerate(rest) if t.value=='['),-1);arrow=next((i for i,t in enumerate(rest) if t.value=='-->'),-1)
            if bracket>=0:
                if name!='x-axis' or rest[-1].value!=']':raise error(document,row[0].offset,'Only x-axis supports band categories')
                title=_text(document,rest[:bracket]);categories=tuple(_text(document,s) for s in split(rest[bracket+1:-1]))
                if not categories:raise error(document,rest[bracket].offset,'Expected x-axis categories')
                xkind='band';xdomain=categories;hasx=True
            elif arrow>=0:
                if arrow<1 or len(rest)!=arrow+2:raise error(document,rest[arrow].offset,'Expected numeric axis min --> max')
                domain=(scalar(document,rest[arrow-1]),scalar(document,rest[arrow+1]));title=_text(document,rest[:arrow-1])
                if name=='x-axis':xkind='linear';xdomain=domain;hasx=True
                else:ydomain=domain;hasy=True
            else:title=_text(document,rest)
            if name=='x-axis':xtitle=title
            else:ytitle=title
        elif name in ('line','bar'):
            bracket=next((i for i,t in enumerate(rest) if t.value=='['),-1)
            if bracket<0 or rest[-1].value!=']':raise error(document,row[0].offset,'Expected XY plot numeric list')
            title=_text(document,rest[:bracket]);values=[];labels=[]
            for item in split(rest[bracket+1:-1]):
                if len(item) not in (1,2) or len(item)==2 and not item[1].quoted:raise error(document,item[0].offset if item else rest[bracket].offset,'Expected plot number and optional quoted point label')
                values.append(scalar(document,item[0]));labels.append(item[1].value if len(item)>1 else '')
            if not values:raise error(document,rest[bracket].offset,'XY plot needs a data point')
            if not hasx:xkind='linear';xdomain=(1.,float(len(values)));hasx=True
            visible=values[:len(xdomain)] if xkind=='band' else values
            if not hasy and visible:ydomain=(min(ydomain[0],min(visible)),max(ydomain[1],max(visible)))
            if xkind=='band':data=tuple((category,visible[i] if i<len(visible) else None) for i,category in enumerate(xdomain))
            else:data=tuple((xdomain[0] if len(values)==1 else xdomain[0]+i*(xdomain[1]-xdomain[0])/(len(values)-1),v) for i,v in enumerate(values))
            plots.append(Plot(name,title,data,tuple(labels) if name=='line' else ()))
        else:raise error(document,row[0].offset,'Unexpected XYChart statement')
    return make_diagram('xychart',document,config,XYChart(meta.get('title',''),orientation,xkind,tuple(xdomain),xtitle,ydomain,ytitle,tuple(plots),tuple((k,v) for k,v in meta.items() if k!='title')))

async def build(diagram,p):
    m=diagram.model;c=config_dict(diagram);q={'width':700,'height':500,'titleFontSize':20,'titlePadding':10,'showTitle':True,'showLegend':True,'legendFontSize':14,'legendPadding':10,'plotReservedSpacePercent':50,'showDataLabel':False,'showDataLabelOutsideBar':False,**c.get('xyChart',{})}
    theme=c.get('themeVariables',{}).get('xyChart',{});w=q['width'];h=q['height'];horizontal=m.orientation=='horizontal'
    if not m.plots:raise error(diagram.source,0,'XYChart renderer requires a plot','EMPTY_XYCHART')
    if not all(math.isfinite(v) for v in m.ydomain):raise error(diagram.source,0,'XYChart has no finite data extent','INVALID_GEOMETRY')
    colors=[s.strip() for s in theme.get('plotColorPalette','#6c8ebf,#d79b00,#82b366,#b85450,#9673a6').split(',')];colors=colors or ['#6c8ebf']
    def axiscolors(prefix):return {key:theme.get(prefix+name,'#333') for key,name in (('titleColor','TitleColor'),('labelColor','LabelColor'),('tickColor','TickColor'),('axisLineColor','LineColor'))}
    xa=Axis(m.xkind,m.xdomain,m.xtitle,q.get('xAxis',{}),p,axiscolors('xAxis'),'x');ya=Axis('linear',m.ydomain,m.ytitle,q.get('yAxis',{}),p,axiscolors('yAxis'),'y')
    xa.geometry_source=ya.geometry_source=diagram.source
    cw=math.floor(w*q['plotReservedSpacePercent']/100);ch=math.floor(h*q['plotReservedSpacePercent']/100);aw=w-cw;ah=h-ch
    title=p.measure(m.title,size=q['titleFontSize']) if m.title else None;titleh=title.height+2*q['titlePadding'] if title and q['showTitle'] and title.height+2*q['titlePadding']<=ah else 0;ah-=titleh
    if horizontal:
        xspace=xa.calculate(aw,ah,'left');aw-=xspace[0];yspace=ya.calculate(aw,ah,'top');ah-=yspace[1];px=xspace[0];py=titleh+yspace[1]
    else:
        xspace=xa.calculate(aw,ah,'bottom');ah-=xspace[1];yspace=ya.calculate(aw,ah,'left');aw-=yspace[0];px=yspace[0];py=titleh
    named=[(i,plot) for i,plot in enumerate(m.plots) if plot.title] if q['showLegend'] else []
    fs=q['legendFontSize'];lp=q['legendPadding'];legendw=legendh=0
    if named:
        labels=[p.measure(plot.title,size=fs) for i,plot in named];legendw=2*lp+1.1*fs+max(t.width for t in labels);legendh=2*lp+len(named)*fs+(len(named)-1)*.5*fs
        if legendw>aw or legendh>ch:named=[];legendw=legendh=0
    aw-=legendw;cw+=max(0,aw);ch+=max(0,ah)
    if horizontal:xa.set_range(py,py+ch);xa.box[:2]=[0,py];ya.set_range(px,px+cw);ya.box[:2]=[px,titleh]
    else:xa.set_range(px,px+cw);xa.box[:2]=[px,py+ch];ya.set_range(py,py+ch);ya.box[:2]=[0,py]
    if any(plot.kind=='bar' for plot in m.plots):xa.pad_bars()
    p.rect(0,0,w,h,fill=theme.get('backgroundColor','#fff'),stroke='none',id='background')
    source_labels=[v for x,v in m.plots[0].data]
    plotted=[]
    for i,plot in enumerate(m.plots):
        color=colors[i%len(colors)];valid=[(j,x,v) for j,(x,v) in enumerate(plot.data) if v is not None]
        vchart=geometry('cartesian',diagram.source,plot.kind,[(x,v) for x,v in plot.data if plot.kind=='line' or v is not None],cw,ch,m.xdomain,m.ydomain,x_kind=m.xkind,horizontal=horizontal,category_padding=xa.outer)
        raw_points=[point for segment in vchart.get('segments',()) for point in segment]
        positions=[(py+y,px+x,j) if horizontal else (px+x,py+y,j) for (j,_,_),(x,y) in zip(valid,raw_points)] if plot.kind=='line' else []
        plotted.append((i,tuple((a,b) for a,b,j in positions)))
        if plot.kind=='line':
            pts=[(b,a) if horizontal else (a,b) for a,b,j in positions]
            if pts:
                path='M'+f'{pts[0][0]:g},{pts[0][1]:g}'+''.join(f'L{x:g},{y:g}' for x,y in pts[1:])+('Z' if len(pts)==1 else '')
                p.path(path,stroke=color,line_width=2,id=f'line-{i}')
            for a,b,j in positions:
                if j<len(plot.labels) and plot.labels[j]:
                    text=p.measure(plot.labels[j],size=12);p.text(text,b+10 if horizontal else a,a-text.height/2 if horizontal else b-10-text.height/2,align='left' if horizontal else 'center',color=color,id=f'point-label-{i}-{j}')
        else:
            bars=[]
            for (j,_,_),bounds in zip(valid,vchart.get('bars',())):
                x0,y0,x1,y1=bounds
                # Mermaid barPlot.ts retains the VChart projected center but
                # sizes the bar from axis outer padding / tick distance.
                breadth=min(xa.outer*2,xa.tick_distance())*.95
                if horizontal:
                    center=(y0+y1)/2;y0=center-breadth/2;y1=center+breadth/2
                else:
                    center=(x0+x1)/2;x0=center-breadth/2;x1=center+breadth/2
                rect=(px+x0,py+y0,x1-x0,y1-y0)
                if rect[2]<0 or rect[3]<0:continue # negative SVG sizes do not paint.
                p.rect(*rect,fill=color,stroke=color,line_width=0,id=f'bar-{i}-{j}');bars.append((rect,text_value(source_labels[j]) if j<len(source_labels) and source_labels[j] is not None else ''))
            if q['showDataLabel']:
                valid=[(r,label) for r,label in bars if r[2]>0 and r[3]>0 and label];sizes=[]
                for r,label in valid:
                    size=r[3]*.7 if horizontal else r[2]/(len(label)*.7)
                    while size>0 and (size*len(label)*.7>r[2]-(10 if horizontal else 0) or not horizontal and 10+size>r[3]):size-=1
                    sizes.append(size)
                size=math.floor(min(sizes,default=0))
                if size>0:
                    for j,(r,label) in enumerate(valid):
                        x,y,bwidth,bheight=r;outside=q['showDataLabelOutsideBar'];text=p.measure(label,size=size)
                        p.text(text,x+bwidth+(10 if outside else -10) if horizontal else x+bwidth/2,y+bheight/2-text.height/2 if horizontal else y+(-10 if outside else 10),align=('left' if outside else 'right') if horizontal else 'center',color=theme.get('dataLabelColor','#333'),id=f'bar-label-{i}-{j}')
    if titleh:
        half=min(title.width,w)/2;center=min(max(px+cw/2,half),w-half);p.text(title,center,titleh/2-title.height/2,align='center',color=theme.get('titleColor','#333'),role='title')
    xa.draw();ya.draw()
    if named:
        lx=px+cw+lp;ly=py+max((ch-legendh)/2,0)+lp
        for row,(i,plot) in enumerate(named):
            y=ly+row*fs*1.5;marker=fs*.75
            if plot.kind=='bar':p.rect(lx,y,marker,marker,fill=colors[i%len(colors)],stroke='none',id=f'legend-{i}')
            else:p.line(lx,y+marker/2,lx+marker,y+marker/2,stroke=colors[i%len(colors)],line_width=2,id=f'legend-{i}')
            p.text(plot.title,lx+fs*1.1,y,size=fs,color=theme.get('legendTextColor','#333'),id=f'legend-label-{i}')
    return p.finish(width=w,height=h,padding=0,background=theme.get('backgroundColor','#fff'),layout={'kind':'xychart','plot':(px,py,cw,ch),'series':tuple(plotted),'xDomain':m.xdomain,'yDomain':m.ydomain})
