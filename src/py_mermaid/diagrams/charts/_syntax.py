"""Value-only lexical utilities for the fixed chart languages.

The scanner retains offsets and nesting; separators inside quotes, lists and
object bodies are not mistaken for statement boundaries.
"""
from dataclasses import dataclass
import re
from ...runtime.common import error

@dataclass(frozen=True)
class Token:
    value:str
    offset:int
    quoted:bool=False
    end:int=0

def tokens(document):
    source=document.cleaned;out=[];i=0
    identifier=re.compile(r'[\w\u0080-\uffff](?:[-\w\u0080-\uffff]*[\w\u0080-\uffff])?')
    numeric=re.compile(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)')
    while i<len(source):
        c=source[i]
        if c in ' \t\r':i+=1;continue
        if source.startswith('%%',i):
            end=source.find('\n',i);i=len(source) if end<0 else end;continue
        if c in '\n;':out.append(Token('\n',i,end=i+1));i+=1;continue
        if c in '\"\'':
            start=i;quote=c;i+=1;value=[]
            while i<len(source) and source[i]!=quote:
                if source[i]=='\\' and i+1<len(source):
                    i+=1;value.append({'n':'\n','r':'\r','t':'\t'}.get(source[i],source[i]));i+=1
                else:value.append(source[i]);i+=1
            if i==len(source):raise error(document,start,'Unterminated chart string')
            out.append(Token(''.join(value),start,True,i+1));i+=1;continue
        if source.startswith('-->',i):out.append(Token('-->',i,end=i+3));i+=3;continue
        if source.startswith(':::',i):out.append(Token(':::',i,end=i+3));i+=3;continue
        matches=[m for m in (identifier.match(source,i),numeric.match(source,i)) if m]
        match=max(matches,key=lambda m:m.end()) if matches else None
        if match:out.append(Token(match[0],i,end=match.end()));i=match.end();continue
        out.append(Token(c,i,end=i+1));i+=1
    return tuple(out)

def statements(document):
    result=[];current=[];stack=[]
    for t in tokens(document):
        if not t.quoted:
            if t.value in '[{(':stack.append(t.value)
            elif t.value in ']})':
                if not stack or '[{('.index(stack.pop())!=']})'.index(t.value):raise error(document,t.offset,'Unbalanced chart delimiter')
            elif t.value=='\n' and not stack:
                if current:result.append(tuple(current));current=[]
                continue
        current.append(t)
    if stack:raise error(document,len(document.cleaned),'Unclosed chart delimiter')
    if current:result.append(tuple(current))
    return result

def words(seq):
    out=[];previous=None
    for t in seq:
        if t.value=='\n':continue
        if previous and t.offset>previous.end:out.append(' ')
        out.append(t.value);previous=t
    return ''.join(out)

def scalar(document,t):
    try:value=float(t.value)
    except ValueError:raise error(document,t.offset,'Expected a numeric chart value') from None
    import math
    if not math.isfinite(value):raise error(document,t.offset,'Chart values must be finite')
    return value

def split(seq,separator=','):
    result=[];part=[];depth=0
    for t in seq:
        if not t.quoted and t.value in '[{(':depth+=1
        elif not t.quoted and t.value in ']})':depth-=1
        if t.value==separator and not t.quoted and not depth:result.append(tuple(part));part=[]
        elif t.value!='\n':part.append(t)
    if part:result.append(tuple(part))
    return result

def common_statement(seq,meta):
    name=seq[0].value.lower()
    if name=='title':meta['title']=words(seq[1:]);return True
    if name in ('acctitle','accdescr'):
        values=seq[1:]
        if values and values[0].value==':':values=values[1:]
        if values and values[0].value=='{':values=values[1:-1]
        meta[name]=words(values);return True
    return False

def theme(config,key,default):return config.get('themeVariables',{}).get(key,default)

def number(value,default):
    if isinstance(value,(int,float)):return float(value)
    match=re.match(r'[-+]?[\d.]+',str(value))
    return float(match[0]) if match else default

def palette(config,prefix='cScale',count=12):
    fallback=('#ececff','#ffffde','#ffdfdf','#cde498','#b5dbd9','#c7d5eb','#e8d4e8','#ffd8b1','#dceaff','#e5e5e5','#fde2e4','#d4f1f4')
    return tuple(theme(config,prefix+str(i+1 if prefix=='pie' else i),fallback[i%len(fallback)]) for i in range(count))
