"""Port of sequenceDiagram.jison actions and SequenceDB lifecycle validation.

Statement scanning tracks quotes and participant metadata, not line splitting:
semicolons/newlines delimit source statements except inside @{...} and strings.
"""
from dataclasses import replace
import re,math
from .model import Actor,ActorBox,Event,Sequence
from py_mermaid.runtime.common import make_diagram,error
from py_mermaid.config.values import freeze_value,thaw_value
from py_mermaid.parsing.yaml_json import load_yaml_json


ARROWS=('<<-->>','<<->>','-->>','->>','--|\\','--|/','--\\\\','--//','/|--','\\|--','//--','\\\\--',
        '-|\\','-|/','-\\\\','-//','/|-','\\|-','//-','\\\\-','-->','--x','--)','->','-x','-)')
ARROW_PATTERN='|'.join(re.escape(a) for a in sorted(ARROWS,key=len,reverse=True))
_SIGNAL=re.compile(r'^(?P<from>.*?)\s*(?P<left>\(\))?\s*(?P<arrow>'+ARROW_PATTERN+r')\s*(?P<activity>[+-]|\(\))?\s*(?P<to>[^:]+):(?P<label>.*)$',re.S)
KINDS=frozenset(('actor','boundary','collections','control','database','entity','participant','queue'))
BLOCKS=frozenset(('loop','opt','alt','par','par_over','critical','break','rect','box'))


def statements(text):
    start=0;depth=0;quote='';escaped=False;i=0
    while i<len(text):
        c=text[i]
        if quote:
            if c==quote and not escaped:quote=''
            escaped=c=='\\' and not escaped
        elif c in '\"\'' and (depth or not text[start:i].strip()):quote=c
        elif c=='{' and (depth or i and text[i-1]=='@' or re.fullmatch(r'\s*accDescr\s*',text[start:i],re.I)):depth+=1
        elif c=='}' and depth:depth-=1
        elif c=='#' and not depth:
            entity=re.match(r'#(?:[A-Za-z][A-Za-z0-9]*|[0-9]+);',text[i:])
            if entity:i+=len(entity[0]);continue
            # Source sequence lexer treats # as comment, independently of
            # the generic %% preprocessor. Entity spellings remain lexer data
            # only when encoded by the source before this boundary.
            yield text[start:i].strip(),start
            i=text.find('\n',i)
            if i<0:return
            start=i+1
        elif c in '\n;' and not depth:
            value=text[start:i].strip()
            if value:yield value,start
            start=i+1
        i+=1
    value=text[start:].strip()
    if value:yield value,start


def parse(document,config):
    options=config.get('sequence',{})
    actors={};events=[];boxes=[];stack=[];metadata=[];title=document.title
    current_box=None;box_data=[];pending_create=None;pending_destroy=None
    activations={};sequence_visible=False;index=1.;step=1.
    default_wrap=bool(config.get('wrap',options.get('wrap',False)))
    def fail(offset,message,code='SYNTAX_ERROR'):raise error(document,offset,message,code=code)
    def message(text):
        text=text.strip();match=re.match(r'^:?(no)?wrap:',text,re.I)
        return (text[match.end():].strip(),not bool(match[1])) if match else (text,default_wrap)
    def actor(name,*,label=None,kind=None,meta=None,offset=0,declared=False):
        nonlocal current_box
        name=name.strip()
        if not name or re.search(r'[<>:\n,;@]',name):fail(offset,'Invalid participant identifier')
        old=actors.get(name)
        if old and current_box is not None and old.box is not None and old.box!=current_box:fail(offset,'A participant must only be defined in one Box','DUPLICATE_PARTICIPANT_BOX')
        if old and not declared:return name
        doc=meta or {};kind=str(doc.get('type',kind or (old.kind if old else 'participant')))
        text,wrap=message(str(label if label is not None else doc.get('alias',old.label if old else name)))
        actors[name]=Actor(name,text,kind,wrap,old.box if old and old.box is not None else current_box,
                           old.created if old else None,old.destroyed if old else None,freeze_value(doc))
        return name
    def activation(name,active,offset):
        actor(name,offset=offset)
        count=activations.get(name,0)
        if not active and count<1:fail(offset,'Trying to inactivate an inactive participant ('+name+')','INACTIVE_PARTICIPANT')
        activations[name]=count+(1 if active else -1)
        events.append(Event('activate' if active else 'deactivate',source=name,offset=offset))
    entries=list(statements(document.cleaned))
    if not entries or entries[0][0].lower()!='sequencediagram':fail(0,'Expected sequenceDiagram')
    for line,offset in entries[1:]:
        if line.startswith('%%'):continue
        word,_,tail=line.partition(' ');command=word.lower();tail=tail.strip()
        if command in {'participant','actor','create'}:
            creating=command=='create'
            if creating:
                match=re.match(r'(participant|actor)\s+(.+)',tail,re.I)
                if not match:fail(offset,'create requires participant or actor')
                command=match[1].lower();tail=match[2]
            meta={};label=None
            declaration=re.match(r'^([^<>:\n,;@]+?)(?:\s*@\{([\s\S]*)\})?(?:\s+as\s+([\s\S]*))?$',tail,re.I)
            if not declaration:fail(offset,'Invalid participant declaration')
            name=declaration[1].strip()
            if declaration[2] is not None:
                try:meta=load_yaml_json('{'+declaration[2]+'}')
                except Exception as exc:fail(offset,'Invalid participant metadata: '+str(exc),'INVALID_METADATA')
                if not isinstance(meta,dict):fail(offset,'Participant metadata must be a mapping','INVALID_METADATA')
            label=declaration[3]
            if creating and name in actors:fail(offset,'Cannot create a participant with a duplicate id','DUPLICATE_PARTICIPANT')
            actor(name,label=label,kind='actor' if command=='actor' else 'participant',meta=meta,offset=offset,declared=True)
            if creating:
                actors[name]=replace(actors[name],created=len(events));pending_create=name
            continue
        if command=='destroy':
            actor(tail,offset=offset);pending_destroy=tail
            actors[tail]=replace(actors[tail],destroyed=len(events));continue
        if command in {'activate','deactivate'}:activation(tail,command=='activate',offset);continue
        if command=='autonumber':
            values=tail.split()
            if values==['off']:sequence_visible=False
            else:
                if len(values)>2 or any(not re.fullmatch(r'(?:\d+(?:\.\d{1,2})?|\.\d{1,2})',v) for v in values):fail(offset,'Invalid autonumber start/step')
                sequence_visible=True
                if values:
                    value=float(values[0]);new_step=float(values[1]) if len(values)>1 else 1.
                    if not math.isfinite(value) or not math.isfinite(new_step):fail(offset,'Nonfinite sequence number','INVALID_NUMBER')
                    if value:index=value
                    if new_step:step=new_step
            continue
        if command in {'title','title:'}:title=tail;continue
        if re.match(r'^acc(?:Title|Descr)\b',line,re.I):metadata.append(('accessibility',line));continue
        if command in {'link','links','properties','details'}:
            m=re.match(r'^([^:]+):(.*)$',tail,re.S)
            if not m:fail(offset,'Expected actor: metadata')
            actor(m[1],offset=offset)
            if command=='properties':
                import json
                try:properties=json.loads(m[2].strip())
                except (ValueError,TypeError):properties=None
                if isinstance(properties,dict):
                    name=m[1].strip();previous=thaw_value(actors[name].metadata)
                    previous['properties']={**previous.get('properties',{}),**properties}
                    actors[name]=replace(actors[name],metadata=freeze_value(previous))
            # Popup/navigation/DOM details do not alter static sequence paint.
            metadata.append((command,(m[1].strip(),m[2].strip())));continue
        if command in BLOCKS:
            if command=='box':
                if current_box is not None:fail(offset,'Nested participant boxes are not allowed')
                m=re.match(r'^((?:rgba?|hsla?)\s*\([^)]*\)|\w+)?\s*(.*)$',tail,re.I)
                color=m[1] or 'transparent';label=m[2]
                from py_mermaid.config.colors import channels
                try:channels(color)
                except Exception:color='transparent';label=tail
                label,wrap=message(label);current_box=len(box_data);box_data.append((label,color,wrap))
            else:
                label,wrap=message(tail);events.append(Event(command+'_start',text=label,wrap=wrap,offset=offset))
            stack.append(command);continue
        if command=='end':
            if tail or not stack:fail(offset,'Unmatched end')
            block=stack.pop()
            if block=='box':current_box=None
            else:events.append(Event(block+'_end',offset=offset))
            continue
        if command in {'else','and','option'}:
            expected={'else':{'alt'},'and':{'par','par_over'},'option':{'critical'}}[command]
            if not stack or stack[-1] not in expected:fail(offset,'Unexpected '+command+' outside its fragment')
            label,wrap=message(tail);events.append(Event(command,text=label,wrap=wrap,offset=offset));continue
        note=re.match(r'^note\s+(left\s+of|right\s+of|over)\s+([^:]+):(.*)$',line,re.I|re.S)
        if note:
            names=[s.strip() for s in note[2].split(',')]
            if len(names)>2 or (note[1].lower()!='over' and len(names)!=1):fail(offset,'Invalid note actor placement')
            for name in names:actor(name,offset=offset)
            text,wrap=message(note[3]);events.append(Event('note',names[0],names[-1],text,wrap=wrap,placement=re.sub(r'\s+',' ',note[1].lower()),offset=offset));continue
        signal=_SIGNAL.fullmatch(line)
        if signal:
            src=actor(signal['from'],offset=offset);dst=actor(signal['to'],offset=offset)
            if pending_create:
                if dst!=pending_create:fail(offset,'Created participant has no associated creating message','INVALID_CREATE_MESSAGE')
                pending_create=None
            elif pending_destroy:
                if pending_destroy not in {src,dst}:fail(offset,'Destroyed participant has no associated destroying message','INVALID_DESTROY_MESSAGE')
                pending_destroy=None
            text,wrap=message(signal['label']);connection=('dual' if signal['left'] and signal['activity']=='()' else 'source' if signal['left'] else 'target' if signal['activity']=='()' else '')
            events.append(Event('message',src,dst,text,signal['arrow'],wrap,connection=connection,number=index if sequence_visible or options.get('showSequenceNumbers',False) else None,offset=offset))
            index=math.floor((index+step)*100+.5)/100
            if signal['activity']=='+':activation(dst,True,offset)
            elif signal['activity']=='-':activation(src,False,offset)
            continue
        # Jison INVALID token lines may be ignored, but complete malformed
        # statements must never become a successful empty diagram here.
        fail(offset,'Invalid sequence statement: '+line)
    if stack:fail(len(document.cleaned),'Unclosed '+stack[-1]+' block')
    for i,(label,color,wrap) in enumerate(box_data):boxes.append(ActorBox(label,color,tuple(a.id for a in actors.values() if a.box==i),wrap))
    return make_diagram('sequence',document,config,Sequence(tuple(actors.values()),tuple(events),tuple(boxes),title,freeze_value(metadata)))

