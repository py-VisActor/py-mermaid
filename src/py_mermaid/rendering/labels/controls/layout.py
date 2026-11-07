"""Static UA control intent in CSS pixels, using injected public text metrics.

Mermaid delegates these elements to its foreignObject HTML host. This module
provides that host's initial-state intent, not a browser screenshot emulator.
No Canvas/DOM/font objects are created or retained here.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import math
import re
import unicodedata

from ....model.controls import ControlLayout, ControlPaint, ControlSpec
from ....model.flowchart import MermaidError, ResolvedStyle, MeasuredTextRun
from ...styles.flowchart import _split
from .color_values import is_valid_css_color

_SIDES = ('top', 'right', 'bottom', 'left')
CONTROL_CSS_PROPERTIES = frozenset({
    'width','height','min-width','max-width','min-height','max-height','box-sizing',
    'padding','margin','border','border-width','border-style','border-color',
    'border-radius','background','background-color','accent-color','appearance',
    '-webkit-appearance','resize','overflow','overflow-x','overflow-y','vertical-align',
    *('padding-'+s for s in _SIDES), *('margin-'+s for s in _SIDES),
    *('border-'+s for s in _SIDES),
    *('border-'+s+'-'+p for s in _SIDES for p in ('width','style','color')),
})


def _error(message, code='UNSUPPORTED_CONTROL_CSS'):
    return MermaidError(message, code=code)


def parse_control_declarations(css):
    """Tokenize all declarations; names are partitioned, not silently dropped.

    Generic text properties are validated by the shared CSS resolver. This
    parser only owns the control properties in CONTROL_CSS_PROPERTIES.
    """
    result = []
    for item in _split(re.sub(r'/\*.*?\*/', '', css, flags=re.S), ';'):
        if not item.strip():
            continue
        if ':' not in item:
            raise _error('Control CSS declaration requires a colon')
        name, value = item.split(':', 1)
        name, value = name.strip().lower(), value.strip()
        important = bool(re.search(r'!\s*important\s*$', value, re.I))
        value = re.sub(r'!\s*important\s*$', '', value, flags=re.I).strip()
        if not name or not value:
            raise _error('Control CSS declaration is empty')
        result.append((name, value, important))
    return tuple(result)


def split_control_style(css):
    """Return (generic text CSS, control box/paint CSS), both CSS strings."""
    groups = ([], [])
    for name, value, important in parse_control_declarations(css):
        groups[int(name in CONTROL_CSS_PROPERTIES)].append(name+':'+value+(' !important' if important else ''))
    return tuple(';'.join(group) for group in groups)


def control_ua_style(tag, parent, *, disabled=False, input_type=''):
    """Low-priority UA base; the caller subsequently applies author CSS."""
    if tag in ('meter', 'progress', 'fieldset'):
        return replace(parent, display='block' if tag=='fieldset' else 'inline-block',background='transparent')
    monospace=tag=='textarea' or tag=='input' and input_type in ('date','month','week','time','datetime-local')
    return replace(parent, font_family='monospace' if monospace else 'Arial, sans-serif',
                   font_size=40/3, font_weight='normal', font_style='normal',
                   text_align='left', line_height=1.2, line_height_px=None,
                   decoration='', text_transform='none', white_space='pre-wrap' if tag=='textarea' else 'normal',
                   text_color='#6d6d6d' if disabled else '#000000',
                   current_color='#6d6d6d' if disabled else '#000000',background='transparent',display='inline-block')


def _value(metrics, name):
    value = metrics.get(name, 0) if isinstance(metrics, Mapping) else getattr(metrics, name, 0)
    if not isinstance(value, (int,float)) or not math.isfinite(value):
        raise _error('Invalid public Canvas metric '+name, 'INVALID_MEASUREMENT')
    return float(value)


def _integer(value, default, minimum=1):
    match = re.match(r'^[\t\n\f\r ]*\+?(\d+)', str(value))
    if not match:return default
    number=int(match[1])
    return number if number>=minimum else default


def _accent(value, current):
    """Ignore invalid accent declarations like the fixed source HTML host.

    CSS Color 4 absolute colors are checked by the pure color provider rather
    than misclassified by Khroma's older grammar. Context-dependent CSS color
    expressions need their own resolver and are diagnosed, never called invalid.
    """
    value=value.strip()
    if value.lower() in ('auto','initial','unset','inherit','revert','revert-layer'):
        return '#1675d1'
    if value.lower()=='currentcolor':
        value=current
    if is_valid_css_color(value):
        return value
    if value.lower() in ('accentcolor','accentcolortext','activetext','buttonborder','buttonface','buttontext','canvas','canvastext','field','fieldtext','graytext','highlight','highlighttext','linktext','mark','marktext','selecteditem','selecteditemtext','visitedtext') or re.match(r'^(?:color-mix|light-dark|contrast-color|device-cmyk)\s*\(|^(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(\s*from\b',value,re.I):
        raise _error('Context-dependent accent color needs an explicit color resolver')
    return '#1675d1'


def _characters(text):
    """Keep combining/variation/ZWJ clusters intact at emergency wraps."""
    groups=[]
    for char in text:
        join=bool(groups) and (unicodedata.combining(char) or char in ('\ufe0e','\ufe0f','\u200d') or groups[-1].endswith('\u200d'))
        if join:groups[-1]+=char
        else:groups.append(char)
    return groups


def _declarations(spec, style):
    winners = {}
    def put(name,value,important):
        if name not in winners or important or not winners[name][1]:
            winners[name]=(value,important)
    def four(value):
        parts=[p for p in _split(value,' ') if p]
        if len(parts)==1:return parts*4
        if len(parts)==2:return [parts[0],parts[1],parts[0],parts[1]]
        if len(parts)==3:return [parts[0],parts[1],parts[2],parts[1]]
        if len(parts)==4:return parts
        raise _error('Invalid control box shorthand')
    def border(value):
        width,kind,color='medium','none','currentColor'
        for token in [v for v in _split(value,' ') if v]:
            if token in ('none','hidden','solid','dashed','dotted','double','inset','outset','groove','ridge'):kind=token
            elif re.fullmatch(r'(?:thin|medium|thick|[\d.]+(?:px|pt|em|rem)?)',token):width=token
            else:color=token
        return width,kind,color
    for name, value, important in parse_control_declarations(spec.attr('style')):
        if name not in CONTROL_CSS_PROPERTIES:continue
        if name in ('padding','margin'):
            for side,item in zip(_SIDES,four(value)):put(name+'-'+side,item,important)
        elif name in ('border-width','border-style','border-color'):
            for side,item in zip(_SIDES,four(value)):put('border-'+side+'-'+name.split('-')[1],item,important)
        elif name=='border' or name in ('border-'+s for s in _SIDES):
            for side in _SIDES if name=='border' else (name.split('-')[1],):
                for suffix,item in zip(('width','style','color'),border(value)):put('border-'+side+'-'+suffix,item,important)
        elif name=='background':put('background-color',value,important)
        elif name=='overflow':
            parts=[v for v in _split(value,' ') if v]
            if len(parts) not in (1,2):raise _error('Invalid control overflow shorthand')
            put('overflow-x',parts[0],important);put('overflow-y',parts[-1],important)
        else:put(name,value,important)
    custom = dict(style.custom_properties)
    def expand(value, depth=0):
        if depth>24:
            raise _error('Control CSS variable cycle')
        match = re.search(r'var\(\s*(--[\w-]+)\s*(?:,([^()]*))?\)', value)
        if not match:
            if 'var(' in value:
                raise _error('Unresolved control CSS variable')
            return value
        replacement = custom.get(match[1], match[2])
        if replacement is None:
            raise _error('Undefined control CSS variable '+match[1])
        return expand(value[:match.start()]+replacement+value[match.end():], depth+1)
    return {k:expand(v[0]).strip() for k,v in winners.items()}


def layout_control(spec: ControlSpec, style: ResolvedStyle, measure, *,
                   content_layout=None, asset_loader=None,
                   containing_width=None, containing_height=None) -> ControlLayout:
    """Produce immutable local paints; text y is baseline, circles use bboxes.

    Measures return the public TextMetrics fields (object or Mapping). Percent
    dimensions require a finite containing size; an indefinite reference is
    auto, as for an indefinite CSS containing block. Total dimensions include
    margins; clip applies only to text/images/content_runs, never outer chrome.
    """
    if spec.tag not in ('input','button','select','textarea','meter','progress','fieldset'):
        raise _error('Unknown static control '+spec.tag, 'INVALID_HTML_CONTROL')
    if spec.hidden or spec.input_type=='hidden' or style.display=='none':
        return ControlLayout(spec, 0, 0, 0)
    css = _declarations(spec, style)
    size = style.font_size
    if not math.isfinite(size) or size<0:
        raise _error('Invalid control font size', 'INVALID_MEASUREMENT')
    metrics = measure('Mg', style)
    ascent = _value(metrics,'fontBoundingBoxAscent') or _value(metrics,'actualBoundingBoxAscent')
    descent = _value(metrics,'fontBoundingBoxDescent') or _value(metrics,'actualBoundingBoxDescent')
    cell = style.line_height_px if style.line_height_px is not None else max(0,size*style.line_height)
    advance = lambda text, st=style: _value(measure(text,st),'width')
    def length(value, reference=None):
        value=value.strip().lower()
        if value in ('auto','none','normal','initial','unset'):
            return None
        keywords={'thin':1.,'medium':3.,'thick':5.}
        if value in keywords:
            return keywords[value]
        match=re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+))(px|pt|pc|in|cm|mm|em|rem|ex|ch|%)?',value)
        if not match:
            raise _error('Unsupported control CSS length '+value)
        n=float(match[1]);unit=match[2] or 'px'
        if unit=='%' and reference is None:
            return None
        if unit=='ex':
            metric=measure('x',style);scale=_value(metric,'actualBoundingBoxAscent')+_value(metric,'actualBoundingBoxDescent')
        elif unit=='ch':scale=advance('0')
        else:scale={'px':1,'pt':96/72,'pc':16,'in':96,'cm':96/2.54,'mm':96/25.4,'em':size,'rem':16,'%':(reference or 0)/100}[unit]
        result=n*scale
        if not math.isfinite(result):raise _error('Nonfinite control length')
        return result
    def sides(name, default):
        parts=_split(css.get(name,''),' ')
        parts=[x for x in parts if x]
        if not parts:values=list(default)
        elif len(parts)==1:values=parts*4
        elif len(parts)==2:values=[parts[0],parts[1],parts[0],parts[1]]
        elif len(parts)==3:values=[parts[0],parts[1],parts[2],parts[1]]
        elif len(parts)==4:values=parts
        else:raise _error('Invalid '+name+' shorthand')
        return [css.get('border-'+s+'-'+name.split('-')[1] if name.startswith('border-') else name+'-'+s,values[i]) for i,s in enumerate(_SIDES)]
    rtl=style.direction=='rtl'
    disabled=spec.disabled and spec.tag!='fieldset'
    color=style.text_color or '#000000'
    content_style=replace(style,opacity=1,filter_chain=(),brightness=1,shadow_opacity=0,
                          text_color=color,current_color=color,background='transparent')
    accent=_accent(css.get('accent-color','auto'),style.current_color or color)
    def paint_color(value):
        if value.lower()=='currentcolor':return color
        if re.search(r'url\s*\(|gradient\s*\(|[;{}<>]',value,re.I):
            raise _error('Control box paint requires a static solid color')
        return value
    accent=paint_color(accent)
    paints=[]
    def paint(kind, **kw):
        paints.append(ControlPaint(kind, **kw))
    def text(value,x,y,*,st=style,fill=None):
        if value:
            paint('text',x=x,y=y,text=value,fill=fill or color,font_family=st.font_family,font_size=st.font_size,
                  font_weight=st.font_weight,font_style=st.font_style,decoration=st.decoration,direction=st.direction,
                  letter_spacing=st.letter_spacing,word_spacing=st.word_spacing,text_shadows=st.text_shadows,
                  text_stroke_color=st.text_stroke_color,text_stroke_width=st.text_stroke_width)
    kind=spec.input_type if spec.tag=='input' else spec.tag
    # Computed source UA defaults differ across input families. Author
    # box-sizing still wins; no captured pixel dimensions are transplanted.
    default_box_sizing='border-box' if spec.tag in ('button','select','meter','progress') or kind in ('button','submit','reset','search','checkbox','radio','color') else 'content-box'
    box_sizing=css.get('box-sizing',default_box_sizing)
    native=css.get('appearance',css.get('-webkit-appearance','auto'))!='none'
    if box_sizing not in ('content-box','border-box'):
        raise _error('Unsupported control box-sizing')
    if css.get('resize','none') not in ('none','both','horizontal','vertical','block','inline'):
        raise _error('Unsupported control resize')
    for property_ in ('overflow','overflow-x','overflow-y'):
        if css.get(property_,'auto') not in ('visible','hidden','clip','auto','scroll'):
            raise _error('Unsupported control '+property_)
    padding_default=('2px','2px','2px','2px')
    border_default=1.
    if kind in ('checkbox','radio','range','meter','progress','image'):
        padding_default=('0px',)*4;border_default=0.
    elif kind in ('button','submit','reset') or spec.tag=='button':
        padding_default=('2px','6px','2px','6px')
    if spec.tag=='fieldset':
        padding_default=(str(cell)+'px',str(size*.75)+'px',str(size*.625)+'px',str(size*.75)+'px')
        border_default=2.
    padding=[max(0,length(v,containing_width) or 0) for v in sides('padding',padding_default)]
    margin=[length(v,containing_width) or 0 for v in sides('margin',('0px',)*4)]
    border_style='solid';border_color='#a0a0a0';border_width=border_default
    def border_tokens(value, width, bs, bc):
        for token in [v for v in _split(value,' ') if v]:
            if token in ('none','hidden','solid','dashed','dotted','double','inset','outset','groove','ridge'):bs=token
            elif re.fullmatch(r'(?:thin|medium|thick|[\d.]+(?:px|pt|em|rem)?)',token):width=max(0,length(token) or 0)
            else:bc=paint_color(token)
        return width,bs,bc
    if 'border' in css:border_width,border_style,border_color=border_tokens(css['border'],border_width,border_style,border_color)
    widths=[max(0,length(v) or 0) for v in sides('border-width',(str(border_width)+'px',)*4)]
    styles=sides('border-style',(border_style,)*4)
    colors=[paint_color(c) for c in sides('border-color',(border_color,)*4)]
    for i,s in enumerate(_SIDES):
        if 'border-'+s in css:widths[i],styles[i],colors[i]=border_tokens(css['border-'+s],widths[i],styles[i],colors[i])
        if styles[i] in ('none','hidden'):widths[i]=0
        if styles[i] not in ('none','hidden','solid','dashed','dotted','double','inset','outset','groove','ridge'):
            raise _error('Unsupported control border style')
    top,right,bottom,left=widths
    pt,pr,pb,pl=padding
    chrome_w=left+right+pl+pr;chrome_h=top+bottom+pt+pb
    label=spec.text if spec.tag=='button' else spec.value
    legend_text=spec.legend_text
    legend_markup=getattr(spec,'legend_markup','')
    caption_runs=();caption_offset=(0.,0.);legend_w=advance(legend_text);legend_h=cell if legend_text else 0
    if spec.tag=='fieldset' and legend_markup:
        if content_layout is None:raise _error('Fieldset caption requires content_layout','INVALID_HTML_CONTROL')
        legend_w,legend_h,_,caption_runs=content_layout(legend_markup,content_style,math.inf)
    elif spec.tag=='fieldset' and legend_text:
        caption_runs=(MeasuredTextRun(legend_text,0,ascent,legend_w,ascent,descent,
                      style.font_family,size,style.font_weight,style.font_style,color,
                      decoration=style.decoration,direction=style.direction,
                      letter_spacing=style.letter_spacing,word_spacing=style.word_spacing,
                      text_shadows=style.text_shadows,text_stroke_color=style.text_stroke_color,
                      text_stroke_width=style.text_stroke_width,
                      opacity=1 if style.visibility=='visible' else 0),)
    if spec.tag=='fieldset':
        pt=max(pt,legend_h);chrome_h=top+bottom+pt+pb
    if kind in ('button','submit','reset') and spec.tag=='input':
        label=spec.value if 'value' in dict(spec.attributes) else {'button':'','submit':'Submit','reset':'Reset'}[kind]
    rich=None;rich_width=0.;rich_height=cell
    intrinsic_w=advance('0')*_integer(spec.attr('size'),20)
    intrinsic_h=cell
    if kind in ('checkbox','radio'):
        intrinsic_w=intrinsic_h=size if native else 0
    elif kind=='range':intrinsic_w=10*size;intrinsic_h=1.2*size
    elif kind in ('meter','progress'):
        intrinsic_w=(5 if kind=='meter' else 10)*size;intrinsic_h=size
    elif kind=='color':intrinsic_w=3*size;intrinsic_h=1.5*size
    elif kind=='file':intrinsic_w=advance('Choose Files' if spec.multiple else 'Choose File')+advance('No file chosen')+2*size
    elif kind=='image':
        identifier=spec.attr('src')
        if identifier:
            if asset_loader is None:raise _error('Input image requires explicit resource loader','RESOURCE_NOT_FOUND')
            intrinsic_w,intrinsic_h=asset_loader(identifier,'control-image',dict(spec.attributes),style,False)
        else:intrinsic_w=advance(spec.attr('alt','Submit Query'));intrinsic_h=cell
    elif spec.tag in ('button','fieldset') or kind in ('submit','reset','button'):
        if spec.inner_markup:
            if content_layout is None:raise _error('Button rich content requires content_layout','INVALID_HTML_CONTROL')
            rich=content_layout(spec.inner_markup,content_style,math.inf)
            rich_width,rich_height=rich[:2]
            intrinsic_w,intrinsic_h=rich_width,rich_height
        else:intrinsic_w=advance(label or spec.text);intrinsic_h=cell
        if spec.tag=='fieldset':
            intrinsic_w=max(intrinsic_w,legend_w)
    elif kind=='textarea':
        intrinsic_w=advance('0')*_integer(spec.attr('cols'),20)
        intrinsic_h=cell*_integer(spec.attr('rows'),2)
    elif kind=='select':
        group_style=replace(style,font_weight='bold')
        intrinsic_w=max([advance(o.label)+(size if o.group else 0) for o in spec.options]+
                        [advance(o.group,group_style) for o in spec.options if o.group]+[0])+size*1.5
        intrinsic_h=cell*_integer(spec.attr('size'),4 if spec.multiple else 1)
    elif kind in ('date','month','week','time','datetime-local'):
        templates={'date':'mm/dd/yyyy','month':'September 0000','week':'Week 00, 0000','time':'--:-- --','datetime-local':'mm/dd/yyyy, --:-- --'}
        intrinsic_w=advance(templates[kind])+size*1.5
    def dimension(axis,intrinsic,chrome,reference):
        value=length(css[axis],reference) if axis in css else None
        # Width/height attributes are relevant to image input, not text inputs.
        if value is None and kind=='image' and spec.attr(axis):
            raw=spec.attr(axis)
            if re.fullmatch(r'\d+(?:\.\d+)?',raw):value=float(raw)
        border_box=box_sizing=='border-box'
        result=intrinsic+chrome if value is None else max(chrome,value if border_box else value+chrome)
        lo=length(css['min-'+axis],reference) if 'min-'+axis in css else None
        hi=length(css['max-'+axis],reference) if 'max-'+axis in css else None
        if hi is not None:result=min(result,max(chrome,hi if border_box else hi+chrome))
        if lo is not None:result=max(result,max(chrome,lo if border_box else lo+chrome))
        return max(0,result)
    w=dimension('width',intrinsic_w,chrome_w,containing_width)
    if rich is not None:
        rich=content_layout(spec.inner_markup,content_style,max(0,w-chrome_w))
        intrinsic_h=rich[1]
    if kind=='image' and intrinsic_w>0 and intrinsic_h>0:
        explicit_w='width' in css or bool(spec.attr('width'))
        explicit_h='height' in css or bool(spec.attr('height'))
        if explicit_w and not explicit_h:intrinsic_h*=max(0,w-chrome_w)/intrinsic_w
        elif explicit_h and not explicit_w:
            image_h=dimension('height',intrinsic_h,chrome_h,containing_height)
            intrinsic_w*=max(0,image_h-chrome_h)/intrinsic_h
            w=dimension('width',intrinsic_w,chrome_w,containing_width)
    h=dimension('height',intrinsic_h,chrome_h,containing_height)
    if not all(math.isfinite(v) and v>=0 for v in (w,h)):
        raise _error('Invalid control dimensions','INVALID_HTML_CONTROL')
    x0=left+pl;y0=top+pt;cw=max(0,w-chrome_w);ch=max(0,h-chrome_h)
    baseline=y0+(ch-ascent-descent)/2+ascent
    background=css.get('background-color',css.get('background'))
    if background is None:background='transparent' if spec.tag=='fieldset' else '#f3f3f3' if disabled else '#efefef' if spec.tag=='button' or kind in ('button','submit','reset') else '#ffffff'
    if style.background not in ('','transparent') and not any(k in css for k in ('background','background-color')):background=style.background
    background=paint_color(background)
    radius=length(css.get('border-radius','2px'),min(w,h)) or 0
    radius=max(0,min(radius,w/2,h/2))
    ordinary=kind not in ('checkbox','radio','range','meter','progress','image')
    if ordinary or any(k in css for k in ('background','background-color','border','border-width','border-color')):
        paint('roundrect' if radius else 'rect',x=0,y=0,width=w,height=h,fill=background,radius=radius)
    # Side-specific borders remain separate; dashed/dotted segments are pure
    # primitives rather than backend-specific dash state.
    legend_x=w-left-pl-legend_w if rtl else left+pl
    if spec.tag=='fieldset' and legend_w>0:
        # Transparent captions must interrupt the frame, not paint a false
        # white patch over an underlying colored diagram.
        gap0=max(0,legend_x-2);gap1=min(w,legend_x+legend_w+2)
        if top:
            paint('line',x=0,y=top/2,width=gap0,height=0,stroke=colors[0],line_width=top)
            paint('line',x=gap1,y=top/2,width=max(0,w-gap1),height=0,stroke=colors[0],line_width=top)
        for x,y,dx,dy,b,c in ((w-right/2,0,0,h,right,colors[1]),(0,h-bottom/2,w,0,bottom,colors[2]),(left/2,0,0,h,left,colors[3])):
            if b:paint('line',x=x,y=y,width=dx,height=dy,stroke=c,line_width=b)
    elif len(set(widths))==len(set(styles))==len(set(colors))==1 and styles[0]=='solid' and widths[0]>0:
        b=widths[0];paint('roundrect' if radius else 'rect',x=b/2,y=b/2,width=max(0,w-b),height=max(0,h-b),stroke=colors[0],line_width=b,radius=radius)
    else:
        edges=((0,top/2,w,0),(w-right/2,0,0,h),(0,h-bottom/2,w,0),(left/2,0,0,h))
        for i,(x,y,dx,dy) in enumerate(edges):
            b=widths[i]
            if not b:continue
            bs=styles[i]
            if bs in ('dashed','dotted'):
                span=w if dx else h;step=b*(6 if bs=='dashed' else 2);length_=b*(3 if bs=='dashed' else 1)
                for k in range(math.ceil(span/max(step,.01))):
                    start=k*step;extent=min(length_,span-start)
                    paint('line',x=x+(start if dx else 0),y=y+(0 if dx else start),width=extent if dx else 0,height=0 if dx else extent,stroke=colors[i],line_width=b)
            elif bs=='double' and b>=3:
                for offset in (-b/3,b/3):paint('line',x=x+(offset if dy else 0),y=y+(offset if dx else 0),width=dx,height=dy,stroke=colors[i],line_width=b/3)
            else:paint('line',x=x,y=y,width=dx,height=dy,stroke=colors[i],line_width=b)
    content_runs=();content_offset=(x0,y0);clip=(x0,y0,cw,ch)
    def label_x(value, reserve=0):
        tw=advance(value)
        if style.text_align in ('center','middle'):return x0+max(0,(cw-reserve-tw)/2)
        if style.text_align in ('right','end') or rtl:return x0+max(0,cw-reserve-tw)
        return x0
    if kind in ('checkbox','radio'):
        side=min(cw,ch);cx=x0+cw/2;cy=y0+ch/2
        if native and side>0:
            active='#a0a0a0' if disabled else accent
            paint('circle' if kind=='radio' else 'roundrect',x=cx-side/2+.5,y=cy-side/2+.5,width=max(0,side-1),height=max(0,side-1),radius=2,fill=active if spec.checked and kind=='checkbox' else background,stroke=active if spec.checked and kind=='radio' else '#a0a0a0' if disabled else '#767676')
            if spec.checked:
                if kind=='radio':paint('circle',x=cx-side*.19,y=cy-side*.19,width=side*.38,height=side*.38,fill=active)
                else:paint('path',path=f'M{cx-side*.28},{cy} L{cx-side*.07},{cy+side*.22} L{cx+side*.3},{cy-side*.25}',stroke='#ffffff',line_width=max(1,side*.13))
        baseline=h-size*.15
    elif kind=='range':
        if native:
            thumb=min(h,size*1.05);track=max(2,size*.28);start=thumb/2;span=max(0,w-thumb)
            fraction=spec.fraction if spec.fraction is not None else .5
            fraction=max(0,min(1,fraction));position=start+span*(1-fraction if rtl else fraction)
            paint('roundrect',x=start,y=(h-track)/2,width=span,height=track,fill='#d0d0d0',radius=track/2)
            paint('roundrect',x=position if rtl else start,y=(h-track)/2,width=span*fraction,height=track,fill='#b0b0b0' if disabled else accent,radius=track/2)
            paint('circle',x=position-thumb/2,y=(h-thumb)/2,width=thumb,height=thumb,fill='#b0b0b0' if disabled else accent)
        baseline=h-size*.15
    elif kind in ('meter','progress'):
        if native:
            track=max(2,min(h,size*.55));yy=(h-track)/2
            paint('roundrect',x=0,y=yy,width=w,height=track,fill='#e5e5e5',stroke='#b0b0b0',radius=track/2)
            fraction=spec.fraction
            fill=accent
            if kind=='meter':
                def number(name,default):
                    try:n=float(spec.attr(name));return n if math.isfinite(n) else default
                    except ValueError:return default
                low=max(spec.minimum,min(spec.maximum,number('low',spec.minimum)))
                high=max(low,min(spec.maximum,number('high',spec.maximum)))
                optimum=max(spec.minimum,min(spec.maximum,number('optimum',(spec.minimum+spec.maximum)/2)))
                value=spec.minimum+(fraction or 0)*(spec.maximum-spec.minimum)
                band=0 if low<=optimum<=high and low<=value<=high or optimum<low and value<=low or optimum>high and value>=high else 2 if optimum<low and value>high or optimum>high and value<low else 1
                fill=('#269d32','#d7a500','#cf3535')[band]
            if fraction is None:
                paint('roundrect',x=w*.3,y=yy+1,width=w*.4,height=max(0,track-2),fill='#a0a0a0' if disabled else fill,radius=track/2)
            else:
                fraction=max(0,min(1,fraction));extent=max(0,w-2)*fraction
                paint('roundrect',x=w-1-extent if rtl else 1,y=yy+1,width=extent,height=max(0,track-2),fill='#b0b0b0' if disabled else fill,radius=track/2)
        baseline=h-size*.15
    elif kind=='image':
        identifier=spec.attr('src')
        if identifier:paint('image',x=x0,y=y0,width=cw,height=ch,resource_id=identifier)
        else:text(spec.attr('alt','Submit Query'),x0,baseline)
    elif kind=='color':
        inset=max(2,size*.15);paint('rect',x=x0+inset,y=y0+inset,width=max(0,cw-2*inset),height=max(0,ch-2*inset),fill=spec.value or '#000000',stroke='#808080')
    elif kind=='file':
        title='Choose Files' if spec.multiple else 'Choose File';button=advance(title)+size
        xx=x0+cw-button if rtl else x0
        paint('roundrect',x=xx,y=y0,width=button,height=ch,fill='#efefef',stroke='#a0a0a0',radius=2)
        text(title,xx+size/2,baseline)
        text('No file chosen',x0 if rtl else xx+button+size/2,baseline)
    elif kind=='textarea':
        value=spec.value or spec.attr('placeholder')
        placeholder=not spec.value
        logical=value.replace('\r\n','\n').replace('\r','\n').expandtabs(8).split('\n')
        lines=[]
        for line in logical:
            if spec.attr('wrap').lower()=='off' or style.white_space=='pre':lines.append(line);continue
            current=''
            for token in re.findall(r'\S+|\s+',line):
                if not token.isspace() and current and advance(current+token)>cw:
                    lines.append(current);current=''
                for char in _characters(token):
                    if current and advance(current+char)>cw:
                        lines.append(current);current=char
                    else:current+=char
            lines.append(current)
        for i,line in enumerate(lines):text(line,x0+max(0,cw-advance(line)) if rtl else x0,y0+(cell-ascent-descent)/2+ascent+i*cell,fill='#757575' if placeholder else color)
        baseline=h
        if css.get('resize','both')!='none' and native:
            side=min(size*.45,w,h)
            paint('path',path=f'M{w-side},{h-2} L{w-2},{h-side} M{w-side/2},{h-2} L{w-2},{h-side/2}',stroke='#a0a0a0',line_width=1)
    elif kind=='select':
        listbox=spec.multiple or _integer(spec.attr('size'),1)>1
        if listbox:
            rows=[];group=None
            for index,option in enumerate(spec.options):
                if option.group and option.group!=group:rows.append((option.group,None,True));group=option.group
                rows.append((option.label,index,False))
            capacity=max(1,math.floor(ch/cell)) if cell else 1
            selected_row=next((i for i,r in enumerate(rows) if r[1] in spec.selected_indices),0)
            scroll=max(0,selected_row-capacity+1)
            for i,(title,index,heading) in enumerate(rows):
                yy=y0+(i-scroll)*cell
                if index in spec.selected_indices and yy+cell>y0 and yy<y0+ch:
                    paint('rect',x=x0,y=max(yy,y0),width=cw,height=min(yy+cell,y0+ch)-max(yy,y0),fill='#b8b8b8' if disabled else '#1967d2')
                option=spec.options[index] if index is not None else None
                st=replace(style,font_weight='bold') if heading else style
                xx=x0+(size if option and option.group else 0)
                text(title,xx,yy+ascent,st=st,fill='#6d6d6d' if disabled or option and option.disabled else '#ffffff' if index in spec.selected_indices else color)
        else:
            option=spec.options[spec.selected_indices[0]] if spec.selected_indices else None
            value=option.label if option else ''
            text(value,x0+size if rtl else label_x(value,size),baseline)
            clip=(x0+(size if rtl else 0),y0,max(0,cw-size),ch)
            if native:
                center=x0+size*.4 if rtl else w-right-size*.6
                paint('path',path=f'M{center-size*.22},{h/2-size*.1} L{center},{h/2+size*.15} L{center+size*.22},{h/2-size*.1}',stroke=color,line_width=1.3)
    elif spec.tag in ('button','fieldset') or kind in ('button','submit','reset'):
        if rich is not None:
            if content_layout is None:raise _error('Missing rich-content provider','INVALID_HTML_CONTROL')
            rw,rh,_,content_runs=rich
            content_offset=(x0+max(0,(cw-rw)/2),y0+max(0,(ch-rh)/2))
        else:
            value=label or spec.text;text(value,x0+(cw-advance(value))/2,baseline)
        if spec.tag=='fieldset':
            if caption_runs:caption_offset=(legend_x,0)
            elif legend_text:text(legend_text,legend_x,ascent)
    else:
        value=spec.value
        placeholder=not value
        if kind=='password':value='\u2022'*len(value)
        if kind in ('date','time','week','month','datetime-local') and not value:
            value={'date':'mm/dd/yyyy','time':'--:-- --','week':'Week --, ----','month':'--------- ----','datetime-local':'mm/dd/yyyy, --:-- --'}[kind]
        value=value or spec.attr('placeholder')
        reserve=size if kind in ('number','date','time','week','month','datetime-local','search') else 0
        clip=(x0+(reserve if rtl else 0),y0,max(0,cw-reserve),ch)
        text(value,label_x(value,reserve),baseline,fill='#757575' if placeholder else color)
        if native and kind=='number':
            xx=x0 if rtl else w-right-size*.8
            for sign,yy in ((-1,h*.35),(1,h*.65)):
                paint('path',path=f'M{xx},{yy+sign*size*.12} L{xx+size*.2},{yy-sign*size*.12} L{xx+size*.4},{yy+sign*size*.12}',stroke=color,line_width=1)
        elif native and kind in ('date','week','month','datetime-local'):
            xx=x0 if rtl else w-right-size
            paint('rect',x=xx,y=(h-size*.65)/2,width=size*.65,height=size*.65,stroke=color,fill='none')
            paint('line',x=xx,y=(h-size*.65)/2+size*.2,width=size*.65,height=0,stroke=color)
        elif native and kind=='time':
            side=size*.7;xx=x0 if rtl else w-right-size
            paint('circle',x=xx,y=(h-side)/2,width=side,height=side,stroke=color,fill='none')
            paint('path',path=f'M{xx+side/2},{h/2-side*.3} L{xx+side/2},{h/2} L{xx+side*.7},{h/2}',stroke=color)
        elif native and kind=='search' and spec.value:
            xx=x0 if rtl else w-right-size*.8
            paint('path',path=f'M{xx},{h/2-size*.2} l{size*.4},{size*.4} M{xx},{h/2+size*.2} l{size*.4},{-size*.4}',stroke='#757575',line_width=1)
    # Content clips contain the scrollable/overflowing descendants; the frame
    # and control affordances remain at their actual outer geometry.
    if all(css.get(k,'auto')=='visible' for k in ('overflow-x','overflow-y')):
        clip=None
    mt,mr,mb,ml=margin
    shifted=tuple(replace(p,x=p.x+ml,y=p.y+mt) for p in paints) if style.visibility=='visible' else ()
    content_offset=(content_offset[0]+ml,content_offset[1]+mt)
    caption_offset=(caption_offset[0]+ml,caption_offset[1]+mt)
    if clip is not None:clip=(clip[0]+ml,clip[1]+mt,clip[2],clip[3])
    align=css.get('vertical-align','baseline')
    if align not in ('baseline','top','bottom','middle','text-top','text-bottom','sub','super'):
        baseline+=length(align,cell) or 0
    elif align=='sub':baseline-=size*.2
    elif align=='super':baseline+=size*.35
    return ControlLayout(spec,max(0,w+ml+mr),max(0,h+mt+mb),baseline+mt,shifted,tuple(content_runs),content_offset,clip,
                         caption_runs=tuple(caption_runs),caption_offset=caption_offset)
