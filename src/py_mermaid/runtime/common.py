"""Shared native grammar helpers and immutable diagram construction."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime, time, timedelta
import html
import math
import re
from ..config.values import freeze_value, thaw_value
from ..model.flowchart import MermaidError, SourcePosition, SourceSpan
from ..model.scene import Diagram


def make_diagram(kind, document, config, model, diagnostics=()):
    def pure(value, depth=0):
        if depth>256:raise MermaidError('Diagram model depth budget exceeded',code='MODEL_BUDGET')
        if value is None or isinstance(value,(str,bytes,bool,int,float,date,datetime,time,timedelta)):return
        if isinstance(value,tuple):
            for item in value:pure(item,depth+1)
        elif is_dataclass(value):
            if not value.__dataclass_params__.frozen:raise TypeError('Diagram model dataclasses must be frozen')
            for field in fields(value):pure(getattr(value,field.name),depth+1)
        else:raise TypeError('Diagram model must contain immutable pure values, found '+type(value).__name__)
    pure(model)
    return Diagram(kind,document,freeze_value(config),model,tuple(diagnostics))


def config_dict(diagram):
    return thaw_value(diagram.config)


def label_config(config):
    """Pure shared security/font configuration for all native label clients."""
    from ..config.flowchart import resolve_config
    safe={key:config[key] for key in ('theme','look','fontFamily','fontSize','themeVariables','htmlLabels',
        'securityLevel','dompurifyConfig','markdownAutoWrap','handDrawnSeed') if key in config and config[key] is not None}
    if isinstance(config.get('flowchart'),Mapping) and config['flowchart'].get('htmlLabels') is not None:
        safe['flowchart']={'htmlLabels':config['flowchart']['htmlLabels']}
    safe['layout']='elk'
    return resolve_config(safe)


def sanitize_text(text,config):
    """common.ts:sanitizeText boundary, returning inert serialized markup."""
    if not isinstance(text,str):raise MermaidError('Label must be text',code='INVALID_LABEL')
    from ..rendering.labels.sanitize import sanitize_markup
    return sanitize_markup(text,label_config(config)) if text else text


def utf16_length(text):
    return len(text.encode('utf-16-le',errors='surrogatepass'))//2


def immutable_value(value,depth=0):
    """Freeze scene metadata without encoding pure typed geometry as JSON."""
    if depth>256:raise MermaidError('Scene metadata depth exceeded',code='MODEL_BUDGET')
    if is_dataclass(value):
        if not value.__dataclass_params__.frozen:raise TypeError('Scene dataclasses must be frozen')
        return replace(value,**{field.name:immutable_value(getattr(value,field.name),depth+1) for field in fields(value)})
    if isinstance(value,Mapping):
        from .graph import FrozenLookup
        return FrozenLookup(tuple((key,immutable_value(item,depth+1)) for key,item in value.items()))
    if isinstance(value,(tuple,list)):return tuple(immutable_value(item,depth+1) for item in value)
    if value is None or isinstance(value,(str,bytes,bool,int,float,date,datetime,time,timedelta)):return value
    raise TypeError('Scene metadata must be pure values, found '+type(value).__name__)


def error(document, offset, message, code='SYNTAX_ERROR'):
    offset=max(0,min(len(document.cleaned),offset))
    raw=document.processed_to_raw[offset] if document.processed_to_raw else offset
    prefix=document.raw[:raw];start=max(prefix.rfind('\n'),prefix.rfind('\r'))+1
    position=SourcePosition(raw,len(prefix.encode('utf-16-le',errors='surrogatepass'))//2,
                            prefix.replace('\r\n','\n').replace('\r','\n').count('\n')+1,
                            len(prefix[start:].encode('utf-16-le',errors='surrogatepass'))//2)
    return MermaidError(message,code=code,span=SourceSpan(position,position))


def number(value, name='number', *, minimum=None, maximum=None):
    if isinstance(value,bool):raise MermaidError(name+' must be numeric',code='INVALID_NUMBER')
    try:result=float(value)
    except (TypeError,ValueError):raise MermaidError(name+' must be numeric',code='INVALID_NUMBER') from None
    if not math.isfinite(result) or minimum is not None and result<minimum or maximum is not None and result>maximum:
        raise MermaidError(name+' is out of range',code='INVALID_NUMBER')
    return result


def unquote(value):
    value=value.strip()
    if len(value)>=2 and value[0] in ('"',"'",'`') and value[-1]==value[0]:value=value[1:-1]
    return html.unescape(value)


def split_arguments(text, delimiter=','):
    """Split a lexical argument list without breaking nested/quoted arguments."""
    parts=[];start=0;stack=[];quote=None;escaped=False
    pairs={')':'(',']':'[','}':'{'}
    for i,char in enumerate(text):
        if quote:
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char==quote:quote=None
        elif char in ('"',"'",'`'):quote=char
        elif char in '([{':stack.append(char)
        elif char in ')]}':
            if not stack or stack.pop()!=pairs[char]:raise MermaidError('Unbalanced argument delimiter',code='SYNTAX_ERROR')
        elif char==delimiter and not stack:parts.append(text[start:i].strip());start=i+1
    if quote or stack:raise MermaidError('Unterminated quoted or nested argument',code='SYNTAX_ERROR')
    parts.append(text[start:].strip())
    return tuple(parts)


def lines(document, *, skip_header=True):
    offset=0
    for index,line in enumerate(document.cleaned.splitlines(keepends=True)):
        text=line.strip()
        if text and not text.startswith('%%') and (not skip_header or index):
            yield text,offset+len(line)-len(line.lstrip())
        offset+=len(line)
