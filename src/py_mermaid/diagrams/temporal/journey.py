"""Journey tasks/actors/sections and source score-to-emotion geometry."""
from dataclasses import dataclass,replace
import math,re
import html as html_text
from ...model.flowchart import Box
from ...runtime.common import make_diagram,config_dict,error
from ..charts._syntax import number,theme
from ..charts._scales import arc
from ._syntax import lines,metadata,plain_label,wrapped
from ._paint import TemporalPainter

@dataclass(frozen=True)
class Task:
    text:str
    section:str
    score:float
    people:tuple[str,...]

@dataclass(frozen=True)
class Journey:
    title:str
    sections:tuple[str,...]
    tasks:tuple[Task,...]
    actors:tuple[str,...]
    accessibility:tuple=()

def parse(document,config):
    rows=lines(document);meta={'title':document.title};section='';sections=[];tasks=[]
    if not rows or rows[0][1].lower()!='journey':raise error(document,0,'Expected journey')
    for offset,text in rows[1:]:
        if metadata(text,meta):continue
        match=re.fullmatch(r'section\s+([^:]+)',text,re.I)
        if match:section=match[1];sections.append(section);continue
        if ':' not in text:raise error(document,offset,'Expected journey task : score [: actors]')
        label,_=text.split(':',1)
        # Jison taskData is ':' followed by at least one non-comment character.
        # Keep the raw whitespace: Number(' ')=0 is legal, bare ':' is not.
        raw=document.cleaned[offset:].split('\n',1)[0].rstrip('\r')
        data=raw.split(':',1)[1].split('#',1)[0].split('%%',1)[0]
        if not data:raise error(document,offset+len(label)+1,'Expected journey task data after colon')
        pieces=data.split(':');scoretext=pieces[0].strip()
        if not scoretext:score=0.
        elif re.fullmatch(r'0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+',scoretext):score=float(int(scoretext,0))
        elif re.fullmatch(r'[+-]?(?:Infinity|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)',scoretext):score=float(scoretext)
        else:score=math.nan
        people=tuple(s.strip() for s in pieces[1].split(',')) if len(pieces)>1 else ()
        tasks.append(Task(label,section,score,people))
    actors=tuple(sorted({person for task in tasks for person in task.people}))
    return make_diagram('journey',document,config,Journey(meta.get('title',''),tuple(sections),tuple(tasks),actors,tuple((k,v) for k,v in meta.items() if k!='title')))

async def build(diagram,p):
    from ._source_styles import journey as source_styles
    p.add_styles(source_styles(config_dict(diagram)['themeVariables']))
    p=TemporalPainter(p,'journey');p.text_classes=('label',)
    m=diagram.model;c=config_dict(diagram);q=c.get('journey',{});w=q.get('width',150);h=q.get('height',50);gap=q.get('taskMargin',50);mx=q.get('diagramMarginX',50);my=q.get('diagramMarginY',10);diagnostics=[]
    actorcolors=q.get('actorColours',('#8FBC8F','#7CFC00','#00FFFF','#20B2AA','#B0E0E6','#FFFFE0','#FFD700'));fills=q.get('sectionFills',('#191970','#8B008B','#4B0082','#2F4F4F'));textcolors=q.get('sectionColours',('#fff',));fontsize=q.get('taskFontSize',14);family=q.get('taskFontFamily',c.get('fontFamily'))
    native=p.painter;parent=native.style((),tag='g')
    # svgDraw._drawTextCandidateFunc: FO is the browser's selected switch
    # branch; old/tspan remain SVG text with distinct font/line semantics.
    def draw_label(content,x,y,width,height,classes,ident,colour):
        placement=q.get('textPlacement','fo')
        if placement=='fo':
            # FO's XHTML starts with CSS line-height:normal, not F014's
            # markdown HTML line-height 1.5. Let actual user CSS override the
            # common native normal-line-height convention after this base.
            style=native.style(('label',),tag='div',base=replace(parent,line_height=1.2,line_height_px=None),ancestors=(('div',classes,''),))
            label=native.measure(html_text.escape(content),style=style,html=True,width=width,align='center')
            native.text(label,x+max(0,(width-label.width)/2),y+max(0,(height-label.height)/2),
                        style=style,id=ident,clip=Box(x,y,width,height))
        elif placement=='old':
            style=native.style(classes,tag='text',base=parent)
            label=native.measure(re.sub(r'\s+',' ',content),style=style,html=False)
            baseline=y+height/2+5
            origin=label.runs[0].baseline if label.runs else label.ascent
            native.text(label,x+width/2,baseline-origin,align='center',style=style,id=ident)
        else:
            fs=native.font_size(fontsize,base=parent.font_size,family=parent.font_family)
            style=native.style(classes,tag='text',base={'font_size':fs,'font_family':family,'text_color':colour})
            pieces=re.split(r'<br\s*/?>',content,flags=re.I)
            for j,line in enumerate(pieces):
                label=native.measure(line,style=style,html=False)
                dy=j*fs-fs*(len(pieces)-1)/2
                native.text(label,x+width/2,y+height/2+dy-label.height/2,align='center',style=style,
                            id=ident if j==0 else ident+'-line-'+str(j))
    actorlabels=[wrapped(p,a,q.get('maxLabelWidth',360),hyphenate=True) for a in m.actors]
    initialleft=q.get('leftMargin',150)
    # drawActorLegend only expands the baseline when a rendered line exceeds
    # half conf.leftMargin; it does not add every short actor-name width.
    maxwidth=max((run.width for label in actorlabels for run in label.runs if run.width>initialleft-run.width),default=0)
    left=initialleft+maxwidth
    actorpositions={name:i for i,name in enumerate(m.actors)};y=60.
    for i,(name,label) in enumerate(zip(m.actors,actorlabels)):
        fill=theme(c,'actor'+str(i),actorcolors[i%len(actorcolors)]);p.ellipse(20,y,7,7,fill=fill,stroke='#000',id='actor-'+str(i));p.text(label,40,y+7-label.ascent,color=theme(c,'textColor','#666'),html=False,id='actor-label-'+str(i));y+=max(20,20*len({run.baseline for run in label.runs}))
    last='';sectionnumber=0;fill='#CCC';color='black';tasky=2*h+my;positions=[]
    for i,task in enumerate(m.tasks):
        x=left+i*(gap+w)
        if task.section!=last:
            p.section=sectionnumber
            fill=theme(c,'fillType'+str(sectionnumber),fills[sectionnumber%len(fills)]);color=textcolors[sectionnumber%len(textcolors)];count=1
            while i+count<len(m.tasks) and m.tasks[i+count].section==task.section:count+=1
            sw=w*count+mx*(count-1);p.rect(x,50,sw,h,fill=fill,stroke='#666',line_width=1,radius=3,id='section-'+str(sectionnumber));draw_label(task.section,x,50,sw,h,('journey-section','section-type-'+str(sectionnumber)),'section-label-'+str(sectionnumber),color);last=task.section;sectionnumber+=1
        cx=x+w/2;cy=300+(5-task.score)*30
        p.line(cx,tasky,cx,450,stroke='#666',line_width=1,dash=(4,2),id='task-stem-'+str(i))
        if not math.isfinite(cy):
            # Source-specific SVG numeric-attribute defaults, verified against
            # original NaN/+Infinity/-Infinity SVG/PNG. Each invalid cy/y
            # attribute defaults independently to 0; this is not center-5.
            diagnostics.append(f'Journey task {i}: non-finite source score; SVG attribute defaults applied')
            p.ellipse(cx,0,15,15,fill=theme(c,'faceColor','#FFF8DC'),stroke='#999',line_width=2,id='face-'+str(i))
            for side in (-1,1):p.ellipse(cx+side*5,0,1.5,1.5,fill='#666',stroke='#666',line_width=2,id=f'eye-{i}-{side}')
            if math.isnan(task.score):
                # Neither >3 nor <3 holds, so drawFace chooses ambivalent.
                p.line(cx-5,0,cx+5,0,stroke='#666',line_width=1,id='mouth-'+str(i))
            else:
                # Invalid translate(cx, +/-Infinity) is ignored as a whole:
                # source D3 annulus remains at (0,0). Root SVG starts at x=0,
                # clipping its negative-x half. Record that exact right-hand
                # quarter annulus, not an invented mouth on the default face.
                r=7.5;inner=15/2.2
                if task.score>3:
                    d=f'M{r},0A{r},{r} 0 0,1 0,{r}L0,{inner}A{inner},{inner} 0 0,0 {inner},0Z'
                else:
                    d=f'M0,{-r}A{r},{r} 0 0,1 {r},0L{inner},0A{inner},{inner} 0 0,0 0,{-inner}Z'
                p.path(d,fill='#666',stroke='#666',id='mouth-'+str(i))
        else:
            p.ellipse(cx,cy,15,15,fill=theme(c,'faceColor','#FFF8DC'),stroke='#999',line_width=2,id='face-'+str(i))
            for side in (-1,1):p.ellipse(cx+side*5,cy-5,1.5,1.5,fill='#666',stroke='#666',line_width=2,id=f'eye-{i}-{side}')
            if task.score==3:p.line(cx-5,cy+7,cx+5,cy+7,stroke='#666',line_width=1,id='mouth-'+str(i))
            else:
                start=math.pi/2 if task.score>3 else math.pi*1.5;yy=cy+2 if task.score>3 else cy+7
                p.path(arc(cx,yy,7.5,start,start+math.pi,15/2.2),fill='#666',stroke='#666',id='mouth-'+str(i))
        p.rect(x,tasky,w,h,fill=fill,stroke='#666',line_width=1,radius=3,id='task-'+str(i))
        for j,actor in enumerate(task.people):
            p.extra[f'task-actor-{i}-{j}']=('actor-'+str(actorpositions[actor]),)
            a=actorpositions[actor];p.ellipse(x+14+j*10,tasky,7,7,fill=theme(c,'actor'+str(a),actorcolors[a%len(actorcolors)]),stroke='#000',id=f'task-actor-{i}-{j}')
        draw_label(task.text,x,tasky,w,h,('task',),'task-label-'+str(i),color);positions.append((task.text,x,tasky,cx,cy))
    # drawTasks inserts task.x + task.width + taskMargin, where task.width is
    # diagramMarginX (not conf.width). Preserve that actual source bounds.stopx.
    stopx=max([left]+[row[1]+mx+gap for row in positions])
    width=left+stopx+2*mx;end=width-left-4;axisy=h*4
    p.line(left,axisy,end,axisy,stroke='black',line_width=4,id='activity');p.marker(end,axisy,1,0,kind='point',size=8,color='black')
    if m.title:
        fs=native.font_size(q.get('titleFontSize','4ex'),base=parent.font_size,family=parent.font_family,weight=parent.font_weight,italic=parent.font_style!='normal')
        style=native.style((),tag='text',base={'font_size':fs,'font_family':q.get('titleFontFamily') or parent.font_family,'font_weight':'bold','text_color':q.get('titleColor') or parent.text_color})
        title=native.measure(m.title,style=style,html=False)
        origin=title.runs[0].baseline if title.runs else title.ascent
        native.text(title,left,25-origin,style=style,role='title')
    return p.finish(padding=max(mx,my),layout={'kind':'journey','tasks':tuple(positions),'actors':m.actors},diagnostics=tuple(diagnostics))
