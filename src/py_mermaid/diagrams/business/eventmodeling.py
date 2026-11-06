"""Event-modeling Langium entities and source event-sourced lane positioning."""
from dataclasses import dataclass
import re
from ...runtime.common import make_diagram,config_dict,error,sanitize_text
from ..temporal._syntax import metadata,wrapped

TYPES=('rmo','readmodel','ui','cmd','command','evt','event','pcr','processor')
DATA=('json','jsobj','figma','salt','uri','md','html','text')

@dataclass(frozen=True)
class Frame:
    id:str
    type:str
    entity:str
    reset:bool
    sources:tuple=()
    data_reference:str=''
    data_inline:str=''
    offset:int=0

@dataclass(frozen=True)
class EventModel:
    frames:tuple
    data:tuple
    entities:tuple
    notes:tuple
    assertions:tuple
    title:str=''
    accessibility:tuple=()

def parse(document,config):
    s=document.cleaned;tokens=[];pos=0
    # EM_DATA_INLINE is deliberately greedy on its line, while block data
    # requires a newline after '{', matching the source lexer precedence.
    pat=re.compile(r'accDescr\s*\{[^}]*\}|(?:title(?:[ \t]+|(?=\r?\n|$))|accTitle\s*:|accDescr\s*:)[^\r\n]*|\s+|%%[^\r\n]*|/\*[\s\S]*?\*/|//[^\r\n]*|\{[\t ]*\r?\n(?:[\s\S]*?\r?\n)?\}(?:\r?\n|(?!\S))|\{[^\r\n]*\}|"[^\r\n]*"|\'[^\r\n]*\'|->>|\[\[|\]\]|`|\.|\d{1,3}|[_a-zA-Z]\w*|:')
    for m in pat.finditer(s):
        if m.start()!=pos:raise error(document,pos,'Invalid event-modeling token')
        pos=m.end();v=m[0]
        if not v.isspace() and not v.startswith(('%%','//','/*')):tokens.append((v,m.start()))
    if pos!=len(s):raise error(document,pos,'Invalid event-modeling token')
    if not tokens or tokens[0][0]!='eventmodeling':raise error(document,0,'Expected eventmodeling')
    i=1;frames=[];data=[];entities=[];notes=[];assertions=[];meta={'title':document.title or ''}
    def take(value=None):
        nonlocal i
        if i>=len(tokens):raise error(document,len(s),'Unexpected end of event model')
        v,at=tokens[i]
        if value is not None and v!=value:raise error(document,at,'Expected '+value)
        i+=1;return v
    def eid():
        v=take()
        if not re.fullmatch(r'[_a-zA-Z]\w*',v):raise error(document,tokens[i-1][1],'Expected entity identifier')
        return v
    def qualified():
        v=eid()
        while i<len(tokens) and tokens[i][0]=='.':take('.');v+='.'+eid()
        return v
    def fid():
        v=take()
        if not re.fullmatch(r'\d{1,3}',v):raise error(document,tokens[i-1][1],'Expected 1-3 digit frame identifier')
        return v
    def payload(block=False):
        if i<len(tokens) and tokens[i][0]=='`':
            take('`');typ=take()
            if typ not in DATA:raise error(document,tokens[i-1][1],'Unknown data format')
            take('`')
        v=take()
        if not v.startswith(('{','"',"'")) or (block and not re.match(r'\{[\t ]*\r?\n',v)):raise error(document,tokens[i-1][1],'Expected data block' if block else 'Expected inline data')
        return v
    while i<len(tokens):
        keyword,at=tokens[i];i+=1
        if metadata(keyword,meta):continue
        if keyword in ('title','accTitle','accDescr'):
            end=s.find('\n',at)
            if keyword=='accDescr' and i<len(tokens) and tokens[i][0].startswith('{'):end=tokens[i][1]+len(tokens[i][0])
            if end<0:end=len(s)
            if not metadata(s[at:end],meta):raise error(document,at,'Invalid metadata')
            while i<len(tokens) and tokens[i][1]<end:i+=1
        elif keyword in ('tf','timeframe','rf','resetframe'):
            name=fid();typ=take()
            if typ not in TYPES:raise error(document,at,'Unknown model entity type')
            entity=qualified();sources=[];reference='';inline=''
            while i<len(tokens) and tokens[i][0]=='->>':take('->>');sources.append(fid())
            if i<len(tokens) and tokens[i][0]=='[[':take('[[');reference=eid();take(']]')
            if i<len(tokens) and tokens[i][0].startswith(('{','"',"'",'`')):inline=payload()
            if any(f.id==name for f in frames):raise error(document,at,f'Duplicate event modeling frame ID "{name}"')
            frames.append(Frame(name,typ,entity,keyword in ('rf','resetframe'),tuple(sources),reference,inline,at))
        elif keyword=='entity':entities.append(qualified())
        elif keyword=='data':data.append((eid(),payload(True)))
        elif keyword=='note':notes.append((fid(),payload(True)))
        elif keyword=='gwt':
            frame=fid();take('given');parts=[]
            for phase in ('given','when','then'):
                if phase!='given':
                    if phase=='when' and (i>=len(tokens) or tokens[i][0]!='when'):continue
                    take(phase)
                entries=[]
                while i<len(tokens) and tokens[i][0] in TYPES:entries.append((take(),eid()))
                if not entries:raise error(document,at,'Expected '+phase+' statements')
                parts.append((phase,tuple(entries)))
            assertions.append((frame,tuple(parts)))
        else:raise error(document,at,'Unexpected event-modeling statement '+keyword)
    byid={f.id:f for f in frames};dataids={x[0] for x in data}
    allowed={'ui':{'rmo','readmodel'},'pcr':{'rmo','readmodel'},'processor':{'rmo','readmodel'},'rmo':{'evt','event'},'readmodel':{'evt','event'},'cmd':{'ui','pcr','processor'},'command':{'ui','pcr','processor'},'evt':{'cmd','command'},'event':{'cmd','command'}}
    for f in frames:
        for source in f.sources:
            if source not in byid:raise error(document,f.offset,'Unresolved source frame '+source)
            if byid[source].type not in allowed[f.type]:raise error(document,f.offset,'Invalid source entity type '+byid[source].type)
        if f.data_reference and f.data_reference not in dataids:raise error(document,f.offset,'Unresolved data '+f.data_reference)
    for frame,_ in notes+assertions:
        if frame not in byid:raise error(document,0,'Unresolved frame '+frame)
    return make_diagram('eventmodeling',document,config,EventModel(tuple(frames),tuple(data),tuple(entities),tuple(notes),tuple(assertions),meta['title'],tuple(meta.items())))

async def build(diagram,p):
    c=config_dict(diagram);t=c['themeVariables'];m=diagram.model;lanes={};boxes=[];relations=[];previous=None;maxr=0
    data=dict(m.data);canonical={'ui':'Ui','pcr':'Processor','processor':'Processor','rmo':'ReadModel','readmodel':'ReadModel','cmd':'Command','command':'Command','evt':'Event','event':'Event'}
    fallback={'Ui':('white','#dbdada'),'Processor':('#edb3f6','#b88cbf'),'ReadModel':('#d3f1a2','#a3b732'),'Command':('#bcd6fe','#679ac3'),'Event':('#ffb778','#c19a0f')}
    for index,f in enumerate(m.frames):
        parts=f.entity.split('.');namespace=parts[0] if len(parts)==2 else None;name=parts[1] if len(parts)==2 else f.entity
        category=canonical[f.type];boundary=0 if category in ('Ui','Processor') else 100 if category in ('Command','ReadModel') else 200
        prefix=('UI/A: ','C/RM: ','Stream: ')[boundary//100];default=('UI/Automation','Command/Read Model','Events')[boundary//100]
        # Source currently never assigns lane.namespace, so namespace lookup
        # cannot re-use an earlier lane: retain that versioned DB behavior.
        laneindex=max([boundary]+[n for n in lanes if boundary<n<boundary+100])+1 if namespace else boundary
        if laneindex not in lanes:lanes[laneindex]={'index':laneindex,'label':prefix+namespace if namespace else default,'r':0,'height':70,'max':70,'y':0}
        lane=lanes[laneindex]
        label=wrapped(p,sanitize_text(name,c),430,size=16,family='trebuchet ms').text
        content='<b>'+label+'</b>';hasdata=False;raw=f.data_inline
        if raw:
            raw=raw[raw.find('{')+1:];raw=raw[:max(0,raw.rfind('}')-1)];hasdata=True
        if f.data_reference:
            raw=data[f.data_reference];raw=raw[raw.find('{\n')+2:];raw=raw[:max(0,raw.rfind('}')-1)];hasdata=True
        if hasdata:
            value=wrapped(p,sanitize_text(raw,c),430,size=16,family='trebuchet ms').text.replace(' ','&nbsp;')
            if f.data_reference:value+='<br/>'
            content+='<br/><br/><code style="text-align:left;display:block;max-width:430px">'+value+'</code>'
        measured=p.measure(content,size=16,weight='700',family='trebuchet ms')
        width=max(80,min(450,measured.width/(3 if hasdata else 1)+20))+20;height=max(80,min(750,measured.height+20))+20
        if previous is None:x=250
        elif previous['lane']['index']==laneindex and lane['r']:x=lane['r']+10
        elif not boxes:x=250
        else:x=boxes[-1]['r']-90+10
        lane['r']=x+width;lane['max']=max(lane['max'],height);lane['height']=max(70,lane['max'])+30
        box={'frame':f,'lane':lane,'x':x,'r':x+width+10,'w':width,'h':height,'content':content,'category':category};boxes.append(box);maxr=max(maxr,box['r']);previous=box
        sources=[]
        if f.sources:sources=[b for b in boxes if b['frame'].id in f.sources]
        elif not f.reset and index>0:
            source=next((b for b in reversed(boxes[:-1]) if b['lane']['index']!=laneindex),None)
            if source:sources=[source]
        relations.extend((source,box) for source in sources)
    y=0
    for lane in sorted(lanes.values(),key=lambda l:l['index']):lane['y']=y;y+=lane['height']+10
    for lane in sorted(lanes.values(),key=lambda l:l['index']):
        st=p.style('em-swimlane',tag='rect',base={'fill':t.get('emSwimlaneBackgroundOdd','rgb(250,250,250)'),'stroke':t.get('emSwimlaneBackgroundStroke','rgb(240,240,240)')})
        p.rect(0,lane['y'],maxr+15,lane['height'],radius=3,style=st)
        p.text(lane['label'],30,lane['y']+30-p.measure(lane['label'],weight='bold').ascent,weight='bold',html=False)
    for b in boxes:
        fill,stroke=fallback[b['category']];st=p.style('em-box',tag='rect',base={'fill':t.get('em'+b['category']+'Fill',fill),'stroke':t.get('em'+b['category']+'Stroke',stroke)})
        by=b['lane']['y']+15;p.rect(b['x'],by,b['w'],b['h'],radius=3,style=st)
        text=p.measure(b['content'],width=b['w']-20,align='center');p.text(text,b['x']+b['w']/2,by+10+(b['h']-20-text.height)/2,align='center')
    for a,b in relations:
        ay=a['lane']['y']+15;by=b['lane']['y']+15;up=ay>by
        x=a['x']+a['w']*2/3;u=b['x']+b['w']/3;y1=ay if up else ay+a['h'];y2=by+b['h'] if up else by
        st=p.style('em-relation',tag='path',base={'fill':'none','stroke':t.get('emRelationStroke','#000'),'stroke_width':1})
        p.line(x,y1,u,y2,style=st);p.marker(u,y2,u-x,y2-y1,color=t.get('emArrowhead','#000000'),size=10)
    return p.finish(padding=c.get('eventmodeling',{}).get('padding',30))
