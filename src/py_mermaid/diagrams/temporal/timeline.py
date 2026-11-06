"""Timeline's source LR/TD measured period/event-column algorithms."""
from dataclasses import dataclass
import re
from ...runtime.common import make_diagram,config_dict,error
from ..charts._syntax import number,theme,palette
from ._syntax import lines,metadata,wrapped
from ._paint import TemporalPainter

@dataclass(frozen=True)
class Period:
    text:str
    section:str
    events:tuple[str,...]

@dataclass(frozen=True)
class Timeline:
    direction:str
    title:str
    sections:tuple[str,...]
    periods:tuple[Period,...]
    accessibility:tuple=()

def parse(document,config):
    rows=lines(document,hash_comments=False,semicolons=True);meta={'title':document.title};sections=[];current='';tasks=[]
    if not rows:raise error(document,0,'Expected timeline')
    match=re.fullmatch(r'timeline(?:\s+(LR|TD))?',rows[0][1],re.I)
    if not match:raise error(document,0,'Expected timeline [LR|TD]')
    direction=(match[1] or 'LR').upper()
    for offset,text in rows[1:]:
        if metadata(text,meta):continue
        match=re.fullmatch(r'section\s+([^:]+)',text,re.I)
        if match:current=match[1];sections.append(current);continue
        event=re.search(r':\s',text);hash_at=text.find('#')
        if hash_at>=0 and (event is None or hash_at<event.start()):text=text[:hash_at]
        if not text.strip():continue
        parts=re.split(r':\s',text)
        if ':' in parts[0]:raise error(document,offset,'Timeline events start with colon followed by whitespace')
        if parts[0].strip():tasks.append([parts[0].strip(),current,[]])
        if len(parts)>1:
            if not tasks:raise error(document,offset,'Timeline event has no preceding period','MISSING_TIMELINE_PERIOD')
            tasks[-1][2].extend(p.strip() for p in parts[1:])
    periods=tuple(Period(text,section,tuple(events)) for text,section,events in tasks)
    return make_diagram('timeline',document,config,Timeline(direction,meta.get('title',''),tuple(sections),periods,tuple((k,v) for k,v in meta.items() if k!='title')))

async def build(diagram,p):
    from ._source_styles import timeline as source_styles
    cfg_all=config_dict(diagram);tv=cfg_all['themeVariables']
    if tv.get('useGradient') and tv.get('gradientStart') and tv.get('gradientStop'):p.register_gradient(p.render_id+'-gradient',((0,tv['gradientStart']),(1,tv['gradientStop'])),direction=(0,0,1,0))
    p.add_styles(source_styles(tv,cfg_all.get('theme','default'),cfg_all.get('look','classic'),p.render_id))
    p=TemporalPainter(p,'timeline')
    m=diagram.model;c=config_dict(diagram);cfg=c.get('timeline',{});size=number(c.get('fontSize',16),16);left=cfg.get('leftMargin',50);colors=palette(c);redux='redux' in c.get('theme','');dark='dark' in c.get('theme','');slots=c.get('themeVariables',{}).get('borderColorArray',());color_theme='color' in c.get('theme','') and bool(slots);height_records=[]
    def measure(text,width,padding,maxh=0):
        label=wrapped(p,text,width,size=size);return label,max(label.height+size*1.1*.5+padding,maxh)
    def node(text,x,y,width,padding,minimum,section,id):
        limit=c.get('themeVariables',{}).get('THEME_COLOR_LIMIT',12)
        section=section%limit if isinstance(limit,(int,float)) and limit else section
        if isinstance(section,float) and section.is_integer():section=int(section)
        p.section=section;p.text_classes=('section-'+str(section-1),)
        label,height=measure(text,width,padding,minimum);totalwidth=width+padding*2
        color=slots[section%len(slots)] if color_theme else theme(c,'mainBkg',colors[section%len(colors)]) if redux else colors[section%len(colors)]
        fill=theme(c,'mainBkg','#333') if redux and dark and color_theme else color;stroke=slots[int(section)%len(slots)] if color_theme else theme(c,'nodeBorder','#333') if redux else 'none'
        radius=0 if redux else 5
        d=f'M{x:g},{y+height-5:g}V{y+radius:g}Q{x:g},{y:g} {x+radius:g},{y:g}H{x+totalwidth-radius:g}Q{x+totalwidth:g},{y:g} {x+totalwidth:g},{y+radius:g}V{y+height:g}H{x:g}Z'
        p.path(d,fill=fill,stroke=stroke,line_width=number(theme(c,'strokeWidth',1),1),id=id)
        if not redux:p.line(x,y+height,x+totalwidth,y+height,stroke=theme(c,'cScaleInv'+str(section),'#333'),line_width=3,id=id+'-baseline')
        p.text(label,x+totalwidth/2,y+(padding if redux else padding/2)+size*.55,align='center',html=False,color=theme(c,'nodeBorder','#333') if redux else theme(c,'cScaleLabel'+str(section),'#333'),weight=str(theme(c,'fontWeight','normal')) if redux else 'normal',id=id+'-text')
        height_records.append((id,x,y,totalwidth,height));return totalwidth,height
    if m.direction=='TD':
        axisx=50+left+230;sectionwidth=580;periodwidth=200;eventwidth=300;pad=5
        maxsection=max((measure(s,sectionwidth,pad)[1] for s in m.sections),default=0)
        maxtask=max((measure('[object Object]',periodwidth,pad)[1] for task in m.periods),default=0)
        maxevents=max((sum(measure(e,eventwidth,pad,50)[1] for e in task.events)+max(0,len(task.events)-1)*10 for task in m.periods),default=0)
        spacing=max(maxtask,maxevents)+30;mastery=50
        groups=[(s,[task for task in m.periods if task.section==s]) for s in m.sections] if m.sections else [('',list(m.periods))]
        for section,(name,tasks) in enumerate(groups):
            if m.sections:
                _,sh=node(name,axisx-230,mastery,sectionwidth,pad,maxsection,section,f'section-{section}');start=mastery+sh+20
            else:sh=0;start=mastery
            for i,task in enumerate(tasks):
                yy=start+i*spacing;tw,th=node(task.text,axisx-230,yy,periodwidth,pad,maxtask,section,f'period-{section}-{i}');ey=yy
                for j,event in enumerate(task.events):
                    ew,eh=node(event,axisx+50,ey,eventwidth,pad,0,section,f'event-{section}-{i}-{j}');p.line(axisx,ey+eh/2,axisx+50,ey+eh/2,stroke='#000',line_width=2,dash=(5,5),id=f'event-link-{section}-{i}-{j}');p.marker(axisx+50,ey+eh/2,1,0,color='#000',size=6);ey+=eh+10
                if not m.sections and not cfg.get('disableMulticolor',False):section+=1
            if m.sections:mastery+=sh+20+spacing*max(len(tasks),1)-(60 if tasks else 0)
        bottom=max((y+h for id,x,y,w,h in height_records),default=50)+size*.5+20
        p.line(axisx,50-size*2,axisx,bottom,stroke='#000',line_width=4,id='timeline-axis');p.marker(axisx,bottom,0,1,color='#000',size=8)
    else:
        maxsection=max((measure(s,150,20)[1]+20 for s in m.sections),default=0);maxtask=max((measure('[object Object]',150,20)[1]+20 for task in m.periods),default=0)
        maxevents=max((sum(measure(e,150,20,50)[1] for e in task.events)+max(0,len(task.events)-1)*10 for task in m.periods),default=0)
        x=50+left;groups=[(s,[task for task in m.periods if task.section==s]) for s in m.sections] if m.sections else [('',list(m.periods))]
        for section,(name,tasks) in enumerate(groups):
            if m.sections:node(name,x,50,200*max(len(tasks),1)-50,20,maxsection,section,f'section-{section}')
            tasky=50+maxsection+50 if m.sections else 50
            for i,task in enumerate(tasks):
                tx=x+i*200;tw,th=node(task.text,tx,tasky,150,20,maxtask,section,f'period-{section}-{i}');ey=tasky+200
                for j,event in enumerate(task.events):
                    ew,eh=node(event,tx,ey,150,20,50,section,f'event-{section}-{i}-{j}');ey+=eh+10
                if task.events:
                    end=tasky+maxtask+100+maxevents+100;p.line(tx+95,tasky+maxtask,tx+95,end,stroke='#000',line_width=2,dash=(5,5),id=f'event-stem-{section}-{i}');p.marker(tx+95,end,0,1,color='#000',size=6)
                if not m.sections and not cfg.get('disableMulticolor',False):section+=1
            x+=200*max(len(tasks),1)
        axisy=maxsection+maxtask+150 if m.sections else maxtask+100
        p.line(left,axisy,x+3*left,axisy,stroke='#000',line_width=4,id='timeline-axis');p.marker(x+3*left,axisy,1,0,color='#000',size=8)
    if m.title:p.text(m.title,(max((x+w for id,x,y,w,h in height_records),default=left)-left)/2,20-size*2,weight='bold',size=size*2,html=False,role='title')
    return p.finish(padding=cfg.get('padding',50),layout={'kind':'timeline','direction':m.direction,'boxes':tuple(height_records)})
