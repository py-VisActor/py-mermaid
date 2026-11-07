"""Offset-preserving line lexemes for the temporal Jison languages."""
import re
from ...runtime.common import error

def lines(document,hash_comments=True,semicolons=False,inline_percent_comments=True):
    text=document.cleaned;out=[];pos=0
    # accDescr's multiline lexical state consumes everything through its
    # closing brace, including newlines, before normal statement scanning.
    while pos<len(text):
        match=re.match(r'[ \t]*accDescr\s*\{',text[pos:],re.I)
        if match:
            end=text.find('}',pos+match.end())
            if end<0:raise error(document,pos,'Unclosed accDescr block')
            out.append((pos,text[pos:end+1].strip()));pos=end+1;continue
        end=text.find('\n',pos)
        if end<0:end=len(text)
        value=text[pos:end]
        accessibility=bool(re.match(r'\s*acc(?:Title|Descr)\s*:',value,re.I))
        if hash_comments and not accessibility:value=value.split('#',1)[0]
        if not accessibility:
            if inline_percent_comments:value=value.split('%%',1)[0]
            elif re.match(r'^\s*%%(?!\{)',value):value=''
        if value.strip():
            if not semicolons and ';' in value:raise error(document,pos+value.index(';'),'Unexpected semicolon')
            out.append((pos,value.strip()))
        pos=end+1
    return out

def metadata(text,meta):
    match=re.fullmatch(r'title\s+(.*)',text,re.I)
    if match:meta['title']=match[1];return True
    match=re.fullmatch(r'(accTitle|accDescr)\s*:\s*(.*)',text,re.I)
    if match:meta[match[1].lower()]=match[2].strip();return True
    match=re.fullmatch(r'accDescr\s*\{(.*)\}',text,re.I|re.S)
    if match:meta['accdescr']=match[1].strip();return True
    return False

def langium_metadata(document):
    """Mask common Langium terminals without changing any source offset."""
    from dataclasses import replace
    text=document.cleaned;meta={};chars=list(text)
    pattern=re.compile(r'(?m)^[\t ]*(?:accDescr\s*\{[^}]*\}|(?:title(?:[\t ]|(?=\r?\n|$))|accTitle[\t ]*:|accDescr[\t ]*:)[^\r\n]*)')
    for match in pattern.finditer(text):
        raw=match[0]
        if raw.strip()=='title':meta['title']=''
        else:metadata(raw.strip(),meta)
        for i in range(match.start(),match.end()):
            if chars[i] not in '\r\n':chars[i]=' '
    for key,value in tuple(meta.items()):
        if key=='accdescr' and '\n' in value:value='\n'.join(line.strip() for line in value.splitlines());value=re.sub(r'[\r\n]{2,}','\n',value)
        meta[key]=re.sub(r'[\t ]{2,}',' ',value.strip())
    return replace(document,cleaned=''.join(chars)),meta

def plain_label(text):return re.sub(r'<br\s*/?>','\n',text,flags=re.I)

def wrapped(p,text,width,size=None,family=None,hyphenate=False):
    """Measured greedy line wrapping used by source timeline/actor legends."""
    result=[]
    for paragraph in plain_label(text).split('\n'):
        current=''
        for word in paragraph.split():
            candidate=(current+' '+word).strip()
            if p.measure(candidate,size=size,family=family,html=False).width<=width:current=candidate;continue
            if current:result.append(current)
            current=word
            if hyphenate and p.measure(current,size=size,family=family,html=False).width>width:
                part=''
                for char in word:
                    if part and p.measure(part+char+'-',size=size,family=family,html=False).width>width:result.append(part+'-');part=char
                    else:part+=char
                current=part
        result.append(current)
    return p.measure('\n'.join(result),size=size,family=family,html=False)
