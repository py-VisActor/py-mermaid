"""Pure source $$ delimiter protection and lazy native TeX typesetting bridge."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import math,re
from ...model.flowchart import MermaidError

# common.ts katexRegex has no dotAll flag. New lines are label boundaries;
# TeX's escaped matrix row markers stay intact inside a matched formula.
KATEX_REGEX=re.compile(r'\$\$(.*?)\$\$')

@dataclass(frozen=True)
class Formula:
    tex:str
    position:int
    token:str

def protect_math(text:str):
    formulas={};prefix='\ue200KATEX'+sha256(text.encode('utf8')).hexdigest()[:16]
    while prefix in text:prefix+='X'
    def replace(match):
        token=prefix+str(len(formulas))+'\ue201'
        formulas[token]=Formula(match[1],match.start()+2,token)
        return token
    return KATEX_REGEX.sub(replace,text),formulas

def cache_key(tex,style):
    # Include the entire frozen style and source display setting. No native
    # object, process-global macro state, or other node's mutable state is cached.
    return sha256(repr((tex,style,True)).encode('utf8')).hexdigest()

def typeset_formula(tex,style,position=0,*,resources=None,fallback_fonts=()):
    try:
        from py_katex import typeset,Options
        from py_katex.model import ParseError
    except ImportError as exc:
        raise MermaidError('Mathematical labels require py-visactor-katex==0.1.0 (import py_katex)',code='MATH_DEPENDENCY') from exc
    # createText.ts collapses actual double backslashes once in HTML mode.
    normalized=[];positions=[];i=0
    while i<len(tex):
        positions.append(i);normalized.append(tex[i])
        i+=2 if tex[i:i+2]=='\\\\' else 1
    positions.append(len(tex))
    try:box=typeset(''.join(normalized),options=Options(resources=resources,fallback_fonts=fallback_fonts),font_size=style.font_size,display_mode=True,color=style.text_color)
    except ParseError as exc:
        raise MermaidError(f'Math at label offset {position+positions[min(max(0,exc.position),len(positions)-1)]}: {exc}',code='MATH_'+exc.code) from exc
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (box.width,box.height,box.depth)) or box.width<0 or box.height+box.depth<0:
        raise MermaidError('Invalid mathematical label geometry',code='INVALID_MATH_BOX')
    return box


def recolor_math(box,color):
    """CSS text shadow affects text/path paint, never decodes an image as text."""
    from dataclasses import replace
    from py_katex.model import Glyph,Rule,Path,CommandGroup
    def commands(items):
        out=[]
        for item in items:
            if isinstance(item,CommandGroup):out.append(replace(item,commands=commands(item.commands)))
            elif isinstance(item,(Glyph,Rule,Path)):out.append(replace(item,color=color))
        return tuple(out)
    return replace(box,commands=commands(box.commands))
