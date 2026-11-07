"""Event-modeling Langium entities and source event-sourced lane positioning."""
from dataclasses import dataclass
import re
import math
from ...runtime.common import make_diagram,config_dict,error,sanitize_text

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
    s=document.cleaned;tokens=[];pos=0;metadata_tokens={}
    # EM_DATA_INLINE is deliberately greedy on its line, while block data
    # requires a newline after '{', matching the source lexer precedence.
    # Terminal priority is observable: a bare title is EM_ID, but inline
    # leading spaces can let EM_TITLE win before EM_WS. A newline begins
    # EM_WS instead, which greedily consumes subsequent indentation.
    pat=re.compile(r'(?P<id>[_a-zA-Z]\w*)|(?P<fid>\d{1,3})|(?P<inline>\{[^\r\n]*\}|"[^\r\n]*"|\'[^\r\n]*\')|(?P<block>\{[\t ]*\r?\n(?:[\s\S]*?\r?\n)?\}(?:\r?\n|(?!\S)))|(?P<accdescr>[\t ]*accDescr(?:[\t ]*:(?:[^\r\n]*?(?=%%)|[^\r\n]*)|\s*\{[^}]*\}))|(?P<acctitle>[\t ]*accTitle[\t ]*:(?:[^\r\n]*?(?=%%)|[^\r\n]*))|(?P<title>[\t ]*title(?:[\t ][^\r\n]*?(?=%%)|[\t ][^\r\n]*|))|(?P<space>\s+)|(?P<comment>%%[^\r\n]*|/\*[\s\S]*?\*/|//[^\r\n]*)|->>|\[\[|\]\]|`|\.|:')
    for m in pat.finditer(s):
        if m.start()!=pos:raise error(document,pos,'Invalid event-modeling token')
        pos=m.end();v=m[0]
        if m.lastgroup in ('title','acctitle','accdescr'):metadata_tokens[m.start()]=m.lastgroup
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
        if at in metadata_tokens:
            # Prefixed EM_* terminals are not CommonValueConverter names;
            # DefaultValueConverter preserves the whole token. commonDb
            # then sanitizes and applies only its accessibility leading trim.
            key=metadata_tokens[at];value=sanitize_text(keyword,config)
            if key=='acctitle':value=re.sub(r'^\s+','',value)
            elif key=='accdescr':value=re.sub(r'\n\s+','\n',value)
            meta[key]=value
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



def _source_encode_entities(text):
    """Fixed Diagram.encodeEntities transport, restricted to this raw data.

    Do not mutate the public parser/model or generic rich-label consumers.
    JS dot excludes all four line terminators and JS \w is ASCII here.
    """
    not_line=r'[^\r\n\u2028\u2029]*'
    for prefix in ('style','classDef'):
        text=re.sub(prefix+not_line+r':\S*#'+not_line+r';',
                    lambda match:match[0][:-1],text)
    def entity(match):
        inner=match[0][1:-1]
        marker='\ufb02\u00b0\u00b0' if re.fullmatch(r'\+?[0-9]+',inner) else '\ufb02\u00b0'
        return marker+inner+'\u00b6\u00df'
    return re.sub(r'#[A-Za-z0-9_]+;',entity,text)


def _source_decode_entities(text):
    # Source mermaidAPI decodes the completed SVG after rendering. Decode the
    # protected data here immediately before its one direct-HTML paint parse.
    return text.replace('\ufb02\u00b0\u00b0','&#').replace('\ufb02\u00b0','&').replace('\u00b6\u00df',';')

def _source_text_dimensions(p,text):
    """Port utils.calculateTextDimensions' literal SVG-text measurement policy.

    Source draws the markup string using text(), not HTML, for dimensions.
    Final box painting still parses the HTML. Native public TextBox bounds
    supply the owner-thread font measurement in place of SVG getBBox; no
    offscreen DOM or layout fallback is involved.
    """
    if not text:return {'width':0,'height':0,'lineHeight':0}
    def rounded(value):
        # JS Math.round for the nonnegative bbox metrics, including NaN/Inf
        # preservation for the source preferred-family decision below.
        return math.floor(value+.5) if math.isfinite(value) else value
    dimensions=[]
    for family in ('sans-serif','"trebuchet ms", verdana, arial, sans-serif'):
        width=height=line_height=0
        for line in re.split(r'<\/?br\s*\/?>',text,flags=re.I):
            # SVG text() collapses only XML ASCII whitespace and trims edges.
            # Do not use \s: NBSP/EM spaces and raw markup are source content.
            # Empty source lines use U200B *before* normalization, so a
            # nonempty whitespace-only line is not converted to that sentinel.
            literal=re.sub(r'[\t\r\n ]+',' ',line or '\u200b').strip(' ')
            measured=p.measure(literal,size=16,weight='700',family=family,
                               html=False,literal=True)
            maximum=math.nan if math.isnan(width) or math.isnan(measured.width) else max(width,measured.width)
            width=rounded(maximum)
            current_height=rounded(measured.height)
            height+=current_height
            line_height=math.nan if math.isnan(current_height) or math.isnan(line_height) else rounded(max(line_height,current_height))
        dimensions.append({'width':width,'height':height,'lineHeight':line_height})
    fallback,preferred=dimensions
    if any(math.isnan(preferred[key]) for key in ('height','width','lineHeight')) or all(
            fallback[key]>preferred[key] for key in ('height','width','lineHeight')):
        return fallback
    return preferred


def _source_wrap_label(p,text,max_width=430):
    """Fixed utils.wrapLabel/breakString, with the same bold font contract.

    Existing br markup is returned untouched. Word-space and current-line
    widths are measured independently, as in the source, rather than measuring
    a combined rich-text candidate or normalizing tabs/newlines as words.
    """
    if not text or re.search(r'<\/?br\s*\/?>',text,flags=re.I):return text
    words=[word for word in text.split(' ') if word]
    completed=[];next_line=''
    for index,word in enumerate(words):
        word_width=_source_text_dimensions(p,word+' ')['width']
        next_width=_source_text_dimensions(p,next_line)['width']
        if word_width>max_width:
            fragments=[];current='';characters=list(word)
            for position,character in enumerate(characters):
                candidate=current+character
                if _source_text_dimensions(p,candidate)['width']>=max_width:
                    fragments.append(candidate if position+1==len(characters) else candidate+'-')
                    current=''
                else:current=candidate
            completed.extend([next_line,*fragments]);next_line=current
        elif next_width+word_width>=max_width:
            completed.append(next_line);next_line=word
        else:next_line=' '.join(part for part in (next_line,word) if part)
        if index+1==len(words):completed.append(next_line)
    return '<br/>'.join(part for part in completed if part)

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
        label=_source_wrap_label(p,sanitize_text(name,c))
        content='<b>'+label+'</b>';hasdata=False;raw=_source_encode_entities(f.data_inline)
        if raw:
            raw=raw[raw.find('{')+1:];raw=raw[:max(0,raw.rfind('}')-1)];hasdata=True
        if f.data_reference:
            raw=_source_encode_entities(data[f.data_reference]);raw=raw[raw.find('{\n')+2:];raw=raw[:max(0,raw.rfind('}')-1)];hasdata=True
        if hasdata:
            value=_source_wrap_label(p,sanitize_text(raw,c)).replace(' ','&nbsp;')
            if f.data_reference:value+='<br/>'
            content+='<br/><br/><code style="text-align: left; display: block;max-width:430px">'+value+'</code>'
        # renderD3Box always uses foreignObject .html(box.text); global
        # htmlLabels controls flow labels, not this renderer's own HTML.
        dimensions=_source_text_dimensions(p,content)
        width=max(80,min(450,dimensions['width']/(3 if hasdata else 1)+20))+20;height=max(80,min(750,dimensions['height']+20))+20
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
        text=p.measure(_source_decode_entities(b['content']),width=b['w']-20,align='center',html=True,raw_html=True);p.text(text,b['x']+b['w']/2,by+10+(b['h']-20-text.height)/2,align='center')
    for a,b in relations:
        ay=a['lane']['y']+15;by=b['lane']['y']+15;up=ay>by
        x=a['x']+a['w']*2/3;u=b['x']+b['w']/3;y1=ay if up else ay+a['h'];y2=by+b['h'] if up else by
        st=p.style('em-relation',tag='path',base={'fill':'none','stroke':t.get('emRelationStroke','#000'),'stroke_width':1})
        p.line(x,y1,u,y2,style=st);p.marker(u,y2,u-x,y2-y1,color=t.get('emArrowhead','#000000'),size=10)
    return p.finish(padding=c.get('eventmodeling',{}).get('padding',30))
