"""Gantt task dependency compilation, exclusion calendar and time-scale bars."""
from dataclasses import dataclass,replace
from datetime import datetime,timedelta
import math,re
from ...runtime.common import make_diagram,config_dict,error
from ..charts._syntax import theme,number
from ._syntax import lines,metadata,plain_label
from ._dates import parse_date,fallback_date,duration,add,invalid,time_ticks,axis_format,DAYS
from ._civil import epoch_seconds

@dataclass(frozen=True)
class Task:
    id:str
    text:str
    section:str
    previous:str|None
    start:str|None
    end:str
    tags:tuple[str,...]
    order:int
    offset:int
    classes:tuple=()

@dataclass(frozen=True)
class Gantt:
    title:str
    sections:tuple[str,...]
    tasks:tuple[Task,...]
    date_format:str
    axis_format:str
    tick_interval:str
    excludes:tuple[str,...]
    includes:tuple[str,...]
    inclusive:bool
    top_axis:bool
    weekday:str
    weekend:str
    today_marker:str
    accessibility:tuple=()

def parse(document,config):
    rows=lines(document,hash_comments=False,inline_percent_comments=False);meta={'title':document.title};sections=[];section='';tasks=[];previous=None;counter=0;order=0
    options=dict(dateformat='',axisformat='',tickinterval='',todaymarker='',weekday='sunday',weekend='saturday');excludes=[];includes=[];inclusive=topaxis=False
    if not rows or rows[0][1].lower()!='gantt':raise error(document,0,'Expected gantt')
    for offset,text in rows[1:]:
        if metadata(text,meta):continue
        parts=text.split(None,1);command=parts[0];name=command.lower();value=parts[1].strip() if len(parts)>1 else ''
        # Jison recognizes only weekday\s+<known day> and weekend\s+<known
        # weekend>. A label such as `Weekday :a, ...` is taskTxt, not a broken
        # directive. The lexer is case-insensitive and \s also accepts tabs.
        days=DAYS if name=='weekday' else ('friday','saturday')
        day_directive=name not in ('weekday','weekend') or re.match('(?:'+'|'.join(days)+')',value,re.I)
        if name in options and day_directive:
            if name=='weekday' and value.lower() not in DAYS:raise error(document,offset,'Invalid gantt weekday')
            if name=='weekend' and value.lower() not in ('friday','saturday'):raise error(document,offset,'Invalid gantt weekend')
            if name in ('weekday','weekend'):value=value.lower()
            options[name]=value;continue
        if name in ('excludes','includes'):
            target=excludes if name=='excludes' else includes
            for token in re.split(r'[\s,]+',value.lower()):
                if token and token not in target:target.append(token)
            continue
        if name=='inclusiveenddates' and not value:inclusive=True;continue
        if name=='topaxis' and not value:topaxis=True;continue
        if name=='section':section=value;sections.append(section);continue
        if name=='click':
            if not re.fullmatch(r'[^\s]+\s+(?:(?:href\s+"[^"]*"|call\s+[^()]+(?:\([^)]*\))?)\s*){1,2}',value):raise error(document,offset,'Malformed gantt click statement')
            ids=value.split(None,1)[0].split(',')
            tasks=[replace(task,classes=(*task.classes,'clickable')) if task.id in ids else task for task in tasks]
            continue # Interaction is excluded; its visible CSS class is retained.
        if ':' not in text:raise error(document,offset,'Expected gantt task : date/duration data')
        label,data=text.split(':',1);data=data.split('#',1)[0];pieces=[s.strip() for s in data.split(',')];tags=[]
        while pieces and pieces[0] in ('active','done','crit','milestone','vert'):tags.append(pieces.pop(0))
        if not 1<=len(pieces)<=3:raise error(document,offset,'Gantt task requires duration, start/end, or id/start/end')
        if len(pieces)==3:id,start,end=pieces
        else:
            counter+=1;id='task'+str(counter);start=None if len(pieces)==1 else pieces[0];end=pieces[-1]
        row=-1 if 'vert' in tags else order
        if row>=0:order+=1
        tasks.append(Task(id,label,section,previous,start,end,tuple(tags),row,offset));previous=id
    return make_diagram('gantt',document,config,Gantt(meta.get('title',''),tuple(sections),tuple(tasks),options['dateformat'],options['axisformat'],options['tickinterval'],tuple(excludes),tuple(includes),inclusive,topaxis,options['weekday'],options['weekend'],options['todaymarker'],tuple((k,v) for k,v in meta.items() if k!='title')))

def compile_tasks(model,document,now=None):
    now=now or datetime.now();today=now.replace(hour=0,minute=0,second=0,microsecond=0);index={t.id:t for t in model.tasks};resolved={};active=set();diagnostics=[]
    def references(text,keyword,field):
        match=re.match(r'^'+keyword+r'\s+([\d\w\- ]+)',text)
        if not match:return None
        ids=[s for s in match[1].split(' ') if s];dates=[];unknown=[]
        for id in ids:
            if id not in index:unknown.append(id)
            else:dates.append(resolve(index[id])[field])
        if unknown:diagnostics.append('Gantt: '+keyword+' references unknown task id(s): '+', '.join(unknown))
        return (max(dates) if keyword=='after' else min(dates)) if dates else today
    def resolve(task):
        if task.offset in resolved:return resolved[task.offset]
        if task.offset in active:raise error(document,task.offset,'Cyclic gantt task dependency','CYCLIC_GANTT_DEPENDENCY')
        if len(active)>=100:raise error(document,task.offset,'Gantt forward dependency compilation exceeded100 passes','GANTT_COMPILE_LIMIT')
        active.add(task.offset)
        if task.start is None:
            if task.previous not in index:raise error(document,task.offset,'A duration-only first task has no previous task','MISSING_PREVIOUS_TASK')
            start=resolve(index[task.previous])[1]
        else:
            start=references(task.start,'after',1)
            if start is None:start=parse_date(task.start,model.date_format,start=True) or fallback_date(task.start)
            if start is None:raise error(document,task.offset,'Invalid date:'+task.start,'INVALID_DATE')
        end=references(task.end,'until',0)
        if end is None:
            end=parse_date(task.end,model.date_format)
            if end is not None:
                if model.inclusive:end=add(end,1,'d')
            else:
                span=duration(task.end)
                if span:end=add(start,*span)
                else:end=start;diagnostics.append(f'Gantt: "{task.end}" is neither a valid date nor a valid duration; source assigns zero duration')
        manual=parse_date(task.end,'YYYY-MM-DD') is not None;render_end=None
        if model.excludes and not manual:
            current=add(start,1,'d');was_invalid=False;limit=add(end,10000,'d')
            while current<=end:
                if not was_invalid:render_end=end
                was_invalid=invalid(current,model.date_format,model.excludes,model.includes,model.weekend)
                if was_invalid:
                    end=add(end,1,'d')
                    if end>limit:raise error(document,task.offset,'Failed to find a valid date that was not excluded after10,000 iterations','EXCLUDED_DATE_LIMIT')
                current=add(current,1,'d')
        active.remove(task.offset);resolved[task.offset]=(start,end,render_end);return resolved[task.offset]
    result=[(task,*resolve(task)) for task in model.tasks]
    return result,tuple(dict.fromkeys(diagnostics))

async def build(diagram,p):
    from ._paint import TemporalPainter
    from ._source_styles import gantt as source_styles
    p.add_styles(source_styles(config_dict(diagram)['themeVariables']))
    p=TemporalPainter(p,'gantt');p.text_classes=('taskText',)
    m=diagram.model;c=config_dict(diagram);q={'barHeight':20,'barGap':4,'topPadding':50,'rightPadding':75,'leftPadding':75,'gridLineStartPadding':35,'fontSize':11,'sectionFontSize':11,'numberSectionStyles':4,'titleTopMargin':25,'axisFormat':'%Y-%m-%d',**c.get('gantt',{})};now=datetime.now();tasks,diagnostics=compile_tasks(m,diagram.source,now)
    if not tasks:raise error(diagram.source,0,'Gantt has no finite task time domain','EMPTY_GANTT')
    width=q.get('useWidth') if q.get('useWidth') is not None else p.viewport_width;left=q['leftPadding'];right=q['rightPadding'];top=q['topPadding'];bar=q['barHeight'];gap=bar+q['barGap'];rows=[entry for entry in tasks if 'vert' not in entry[0].tags];categories=list(dict.fromkeys(t.section for t,start,end,render in rows));orders={t.offset:t.order for t,start,end,render in rows};categoryheights={s:sum(t.section==s for t,start,end,render in rows) for s in categories}
    if q.get('displayMode')=='compact':
        offset=0
        for section in categories:
            timeline=[]
            for t,start,end,render in sorted((entry for entry in rows if entry[0].section==section),key=lambda v:(v[1],v[0].order)):
                lane=next((i for i,time in enumerate(timeline) if start>=time),len(timeline))
                if lane==len(timeline):timeline.append(end)
                else:timeline[lane]=end
                orders[t.offset]=lane+offset
            categoryheights[section]=len(timeline);offset+=len(timeline)
    height=2*top+sum(categoryheights.values())*gap;minimum=min(start for t,start,end,render in tasks);maximum=max(end for t,start,end,render in tasks);minimum_epoch=epoch_seconds(minimum);extent=epoch_seconds(maximum)-minimum_epoch
    # D3 scaleTime interpolates Date epoch milliseconds. Calendar-day addition
    # preserves wall time, but a bar crossing DST spans23/25 elapsed hours.
    def scale(value):return math.floor(((epoch_seconds(value)-minimum_epoch)/extent if extent else .5)*(width-left-right)+.5)
    # Section row backgrounds and labels use insertion-order categories, while
    # task bodies retain source task order and are painted by start time.
    seen=set()
    for t,start,end,render in rows:
        order=orders[t.offset]
        if order in seen:continue
        seen.add(order);slot=categories.index(t.section)%max(1,q['numberSectionStyles']);bg=theme(c,'sectionBkgColor' if slot==0 else 'sectionBkgColor2' if slot==2 else 'altSectionBkgColor','#ccc')
        p.section=slot
        p.rect(0,top+order*gap-2,width-right/2,gap,fill=bg,stroke='none',opacity=.2,id='section-row-'+str(order))
    if m.excludes or m.includes:
        if (maximum-minimum).days<=5*366:
            day=minimum;run=None;ranges=[]
            while day<=maximum:
                bad=invalid(day,m.date_format,m.excludes,m.includes,m.weekend)
                if bad and run is None:run=day
                elif not bad and run is not None:ranges.append((run,day));run=None
                day=add(day,1,'d')
            if run is not None:ranges.append((run,day))
            for i,(a,b) in enumerate(ranges):p.rect(left+scale(a),q['gridLineStartPadding'],max(0,scale(b)-scale(a)),max(0,height-top-q['gridLineStartPadding']),fill=theme(c,'excludeBkgColor','#eee'),stroke='none',id='excluded-'+str(i))
    tick_values=time_ticks(minimum,maximum,m.tick_interval or q.get('tickInterval'),m.weekday);fmt=m.axis_format or ('%d' if m.date_format in ('D','DD') else q['axisFormat'])
    for i,value in enumerate(tick_values):
        x=left+scale(value);y=height-50
        p.line(x,y,x,q['gridLineStartPadding'],stroke=theme(c,'gridColor','#ccc'),line_width=1,opacity=.8,id='grid-'+str(i));p.text(axis_format(value,fmt),x,y+3,size=10,align='center',color=theme(c,'textColor','#333'),html=False,id='tick-'+str(i))
        if m.top_axis or q.get('topAxis'):p.text(axis_format(value,fmt),x,top-14,size=10,align='center',html=False,id='top-tick-'+str(i))
    boxes=[]
    for t,start,end,render in sorted(tasks,key=lambda e:e[1]):
        p.text_classes=('taskText',)
        tags=set(t.tags);x=left+scale(start);y=orders.get(t.offset,-1)*gap+top;w=scale(render or end)-scale(start);h=bar
        if 'vert' in tags:y=q['gridLineStartPadding'];w=.08*bar;h=len(rows)*gap+bar*2
        milestone='milestone' in tags
        if milestone:x=left+scale(start)+(scale(end)-scale(start))/2-bar/2;w=bar
        active='active' in tags;done='done' in tags;critical='crit' in tags
        slot=categories.index(t.section)%max(1,q['numberSectionStyles']) if t.section in categories else 0
        taskclass=('activeCrit' if critical else 'active') if active else ('doneCrit' if critical else 'done') if done else 'crit' if critical else 'task'
        p.extra[t.id]=('task',taskclass+str(slot),*t.classes,*(['milestone'] if milestone else []),*(['vert'] if 'vert' in tags else []))
        fill=theme(c,'activeTaskBkgColor' if active else 'doneTaskBkgColor' if done else 'critBkgColor' if critical else 'taskBkgColor','#8a90dd')
        stroke=theme(c,'critBorderColor' if critical else 'activeTaskBorderColor' if active else 'doneTaskBorderColor' if done else 'taskBorderColor','#555')
        if w>=0:
            if milestone:
                half=bar*.8/math.sqrt(2);cx=x+bar/2;cy=y+bar/2
                p.polygon(((cx,cy-half),(cx+half,cy),(cx,cy+half),(cx-half,cy)),fill=fill,stroke=stroke,line_width=2,id=t.id,role='milestone')
            else:p.rect(x,y,w,h,fill=fill,stroke=stroke,line_width=2,radius=3,id=t.id,role='vertical-marker' if 'vert' in tags else 'task')
        label=p.measure(plain_label(t.text),size=q['fontSize'],html=False);outside=label.width>w
        if 'vert' in tags:tx=x;ty=q['gridLineStartPadding']+len(rows)*gap+60-label.ascent;align='left'
        else:
            ty=y+bar/2+(q['fontSize']/2-2)-label.ascent
            if outside:
                toleft=(x-left+w)+label.width+1.5*left>width;tx=x-5 if toleft else x+w+5;align='right' if toleft else 'left'
            else:tx=x+w/2;align='center'
        textcolor=theme(c,'taskTextOutsideColor' if outside else 'taskTextDarkColor' if active or done else 'critTextColor' if critical else 'taskTextColor','#333')
        textclasses=[]
        if active:textclasses.append(('activeCritText' if critical else 'activeText')+str(slot))
        if done:textclasses.append(('doneCritText' if critical else 'doneText')+str(slot))
        elif critical:textclasses.append('critText'+str(slot))
        if milestone:textclasses.append('milestoneText')
        if 'vert' in tags:textclasses.append('vertText')
        textclasses.extend((('taskTextOutsideLeft' if align=='right' else 'taskTextOutsideRight'),'taskTextOutside'+str(slot)) if outside else ('taskText','taskText'+str(slot)))
        p.extra[t.id+'-label']=tuple(textclasses)+t.classes
        if active:textcolor=theme(c,'taskTextDarkColor',textcolor)
        if done:textcolor=theme(c,'taskTextOutsideColor' if outside else 'taskTextDarkColor',textcolor)
        if 'vert' in tags:textcolor=theme(c,'vertLineColor',textcolor)
        p.text_classes=p.extra[t.id+'-label']
        label=p.measure(plain_label(t.text),size=15 if 'vert' in tags else q['fontSize'],italic=milestone,weight='bold' if 'clickable' in t.classes else 'normal',color=textcolor,html=False)
        ty=(q['gridLineStartPadding']+len(rows)*gap+60 if 'vert' in tags else y+bar/2+(q['fontSize']/2-2))-label.ascent
        p.text(label,tx,ty,align=align,color=textcolor,html=False,id=t.id+'-label');boxes.append((t.id,x,y,w,h,start.isoformat(),end.isoformat()))
    prior=0
    p.text_classes=('sectionTitle',)
    for i,section in enumerate(categories):
        count=categoryheights[section];label=p.measure(plain_label(section),size=number(q['sectionFontSize'],11),html=False);p.text(label,10,top+(prior+count/2)*gap-label.height/2,color=theme(c,'titleColor','#333'),html=False,id='category-'+str(i));prior+=count
    if m.today_marker!='off':
        # The source can position it outside the data extent, but the fixed
        # viewBox clips a marker entirely outside the physical chart.
        x=left+scale(now);style={k.strip():v.strip() for part in m.today_marker.split(',') if ':' in part for k,v in (part.split(':',1),)}
        if 0<=x<=width:p.line(x,q['gridLineStartPadding'],x,height-50,stroke=style.get('stroke',theme(c,'todayLineColor','#f00')),line_width=number(style.get('stroke-width',2),2),dash=tuple(float(s) for s in re.split(r'[\s]+',style.get('stroke-dasharray','').strip()) if s),id='today-marker')
    if m.title:p.text(m.title,width/2,q['titleTopMargin']-number(theme(c,'fontSize',16),16),align='center',color=theme(c,'titleColor','#333'),html=False,role='title')
    return p.finish(width=width,height=height,padding=0,layout={'kind':'gantt','tasks':tuple(boxes),'domain':(minimum.isoformat(),maximum.isoformat()),'calendar':(m.excludes,m.includes)},diagnostics=diagnostics)
