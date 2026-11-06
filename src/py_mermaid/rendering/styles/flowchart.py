"""Pure Canvas paint/text intents for fixed Mermaid flowchart theme CSS.

Source: styles.ts, diagrams/flowchart/styles.ts and createText.ts. Selectors are
matched to semantic drawing targets; no DOM, browser or selection objects exist.
"""
from __future__ import annotations

from dataclasses import replace
import math
import re

from ...model.flowchart import Flowchart, MermaidError, ResolvedStyle

_TEXT = frozenset({'node-label', 'edge-label', 'group-title', 'title'})
_PROPERTIES = frozenset({'fill','stroke','color','stroke-width','font-size','font-family',
    'font-weight','font-style','font','line-height','opacity','fill-opacity','stroke-opacity',
    'stroke-dasharray','text-decoration','text-decoration-line','background','background-color',
    'text-align','filter','direction','--unused'})
_PROPERTIES |= frozenset({'stroke-linecap','stroke-linejoin','stroke-dashoffset',
    'letter-spacing','word-spacing','text-transform','overflow-wrap','word-wrap',
    'word-break','hyphens','text-shadow','text-overflow','overflow','visibility',
    'animation','animation-name','animation-duration','animation-timing-function',
    'animation-iteration-count','cursor','pointer-events','transition'})
_LAYOUT_CSS = frozenset({'display','white-space','text-anchor','dominant-baseline','max-width'})
_PROPERTIES |= frozenset({'mix-blend-mode','paint-order'})


def _error(message: str) -> MermaidError:
    return MermaidError(message, code='UNSUPPORTED_THEME_CSS')


def _split(text: str, separator: str) -> list[str]:
    parts, start, depth, quote, escaped = [], 0, 0, '', False
    for index, char in enumerate(text):
        if escaped:
            escaped=False;continue
        if char=='\\':
            escaped=True;continue
        if quote:
            if char==quote:quote=''
        elif char in '\"\'':quote=char
        elif char in '([':depth+=1
        elif char in ')]':depth-=1
        elif char==separator and depth==0:
            parts.append(text[start:index]);start=index+1
    if quote or depth:
        raise _error('Unbalanced CSS string or function')
    parts.append(text[start:])
    return parts


def parse_declarations(text: str) -> tuple[tuple[str,str,bool], ...]:
    """Parse declaration values without splitting strings/functions at semicolons."""
    if not isinstance(text,str):raise _error('CSS declarations must be a string')
    result=[]
    for item in _split(re.sub(r'/\*.*?\*/','',text,flags=re.S),';'):
        if not item.strip():continue
        if ':' not in item:raise _error('CSS declaration requires a colon')
        key,value=item.split(':',1);key=key.strip().lower();value=value.strip()
        important=bool(re.search(r'!\s*important\s*$',value,re.I))
        value=re.sub(r'!\s*important\s*$','',value,flags=re.I).strip()
        if not key or not value:raise _error('CSS declaration requires property and value')
        if key not in _PROPERTIES and key not in _LAYOUT_CSS and not key.startswith('--'):
            raise _error(f'CSS property {key!r} has no F01.3 Canvas paint/text meaning')
        result.append((key,value,important))
    return tuple(result)


def parse_css(css: str) -> tuple[tuple[str,tuple[tuple[str,str,bool], ...]], ...]:
    css=re.sub(r'/\*.*?\*/','',css,flags=re.S)
    if not css.strip():return ()
    rules=[];cursor=0
    while cursor<len(css):
        if not css[cursor:].strip():break
        opening=css.find('{',cursor)
        if opening<0:raise _error('CSS rule is missing an opening brace')
        selector=css[cursor:opening].strip()
        if not selector or selector.startswith('@'):
            raise _error('CSS at-rules and external resources require the deferred resource layer')
        quote='';escaped=False;closing=None
        for i in range(opening+1,len(css)):
            char=css[i]
            if escaped:escaped=False;continue
            if char=='\\':escaped=True;continue
            if quote:
                if char==quote:quote=''
            elif char in '\"\'':quote=char
            elif char=='{':raise _error('Nested CSS rules are outside the Canvas declaration contract')
            elif char=='}':closing=i;break
        if closing is None:raise _error('CSS rule is missing a closing brace')
        declarations=parse_declarations(css[opening+1:closing])
        for part in _split(selector,','):
            part=part.strip()
            if not part:raise _error('Empty CSS selector')
            if re.search(r':(?:hover|focus|active|visited|before|after)\b',part):
                continue  # User policy excludes state-dependent/interactive paint.
            if re.search(r'[+~]',re.sub(r'\[[^]]*\]','',part)):
                raise _error('Sibling CSS needs an explicit semantic paint target')
            rules.append((part,declarations))
        cursor=closing+1
    return tuple(rules)


def css_size(value: str, base: float) -> float:
    sizes={'xx-small':9,'x-small':10,'small':13,'medium':16,'large':18,'x-large':24,'xx-large':32}
    if value.lower() in sizes:return float(sizes[value.lower()])
    if value.lower() in {'smaller','larger'}:return base*({'smaller':.8,'larger':1.2}[value.lower()])
    match=re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+))(px|pt|em|rem|%)?',value.strip(),re.I)
    if not match:raise _error(f'Unsupported CSS length {value!r}')
    number=float(match[1]);unit=(match[2] or 'px').lower()
    result=number*({'px':1,'pt':96/72,'em':base,'rem':16,'%':base/100}[unit])
    if not math.isfinite(result) or result<0:raise _error('CSS dimensions must be finite and nonnegative')
    return result


def _opacity(value: str) -> float:
    try:number=float(value.rstrip('%'))/(100 if value.endswith('%') else 1)
    except ValueError:raise _error(f'Invalid CSS opacity {value!r}') from None
    if not math.isfinite(number):raise _error('CSS opacity must be finite')
    return max(0,min(1,number))


def _color(value: str, current: str) -> str:
    if value.lower()=='currentcolor':return current
    if re.search(r'url\s*\(|[<>{};]',value,re.I):
        raise _error('Paint resources/URLs are outside F01.3')
    return value


def _substitute_vars(value: str, custom: dict[str,str], depth: int=0) -> str:
    if depth>32:raise _error('CSS variable cycle or depth budget exceeded')
    match=re.search(r'var\s*\(',value)
    if not match:return value
    level=1;quote='';closing=None
    for index in range(match.end(),len(value)):
        char=value[index]
        if quote:
            if char==quote and (index==0 or value[index-1]!='\\'):quote=''
        elif char in '\"\'':quote=char
        elif char=='(':level+=1
        elif char==')':
            level-=1
            if level==0:closing=index;break
    if closing is None:raise _error('Unclosed CSS variable expression')
    arguments=_split(value[match.end():closing],',');name=arguments[0].strip()
    if not re.fullmatch(r'--[\w-]+',name):raise _error('Invalid CSS variable name')
    if name not in custom and len(arguments)==1:raise _error('Undefined CSS variable '+name)
    replacement=_substitute_vars(custom.get(name,','.join(arguments[1:]).strip()),custom,depth+1)
    return _substitute_vars(value[:match.start()]+replacement+value[closing+1:],custom,depth+1)


def _shadow(style: ResolvedStyle, value: str, *, dark: bool=False) -> ResolvedStyle:
    value=value.strip().rstrip(';').rstrip()
    if value.count('(')!=value.count(')'):
        # Ignore unbalanced user declarations as CSS does. The pinned neo
        # drop-shadow is balanced and reaches the parser below.
        return replace(style,shadow_opacity=0,shadow_blur=0)
    if not value or value=='none':return replace(style,shadow_opacity=0,shadow_blur=0)
    if re.fullmatch(r'url\(\s*[\"\']?#[\w-]*drop-shadow(?:-small)?[\"\']?\s*\)',value):
        offset=2 if 'drop-shadow-small' in value else 4
        return replace(style,shadow_dx=offset,shadow_dy=offset,shadow_blur=0,
                       shadow_color='#ffffff' if dark else '#000000',shadow_opacity=.06)
    if re.fullmatch(r'url\(\s*[\"\']?#[\w-]+[\"\']?\s*\)',value):
        # No matching built-in definition exists: source paint has no filter.
        return replace(style,shadow_opacity=0,shadow_blur=0)
    match=re.fullmatch(r'drop-shadow\((.*)\)',value.strip(),re.I)
    if not match:raise _error('Only static source drop-shadow filters are supported')
    parts=[item for item in _split(match[1],' ') if item]
    length=re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:px|pt|em|rem)?$')
    if len(parts)<2 or not length.fullmatch(parts[0]) or not length.fullmatch(parts[1]):
        raise _error('Drop shadow needs two offset lengths')
    def signed(item):return (-1 if item.startswith('-') else 1)*css_size(item.lstrip('+-'),style.font_size)
    dx,dy=signed(parts[0]),signed(parts[1]);blur=0;index=2
    if len(parts)>2 and length.fullmatch(parts[2]):blur=css_size(parts[2],style.font_size);index=3
    color=' '.join(parts[index:]) or style.current_color or style.text_color
    return replace(style,shadow_dx=dx,shadow_dy=dy,shadow_blur=blur,
                   shadow_color=_color(color,style.current_color or style.text_color),shadow_opacity=1)


def _filter(style: ResolvedStyle,value: str) -> ResolvedStyle:
    """Static source brightness/drop-shadow chain, preserving CSS order."""
    raw=value.strip().rstrip(';').rstrip()
    cleared=replace(style,brightness=1,filter_chain=(),shadow_opacity=0,shadow_blur=0)
    if not raw or raw.lower()=='none':return cleared
    if raw.count('(')!=raw.count(')'):return cleared  # Existing invalid-declaration behavior.
    tokens=[token for token in _split(raw,' ') if token]
    chain=[];seen=set();result=cleared
    for token in tokens:
        bright=re.fullmatch(r'brightness\(\s*([+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(%)?\s*\)',token,re.I)
        if bright:
            if 'brightness' in seen:raise _error('Repeated brightness filters need a separate ordered compositing contract')
            amount=float(bright[1])/(100 if bright[2] else 1)
            if not math.isfinite(amount):raise _error('Brightness must be finite and nonnegative')
            result=replace(result,brightness=amount);chain.append(f'brightness({amount:g})');seen.add('brightness');continue
        if token.lower().startswith(('drop-shadow(','url(')):
            if 'drop-shadow' in seen:raise _error('Multiple drop-shadow filters need a separate compositing contract')
            result=_shadow(result,token,dark=style.shadow_color.lower()=='#ffffff');seen.add('drop-shadow')
            if result.shadow_opacity:
                from ...config.colors import channels,rgba
                red,green,blue,alpha=channels(result.shadow_color)
                color=rgba(red*255,green*255,blue*255,alpha*result.shadow_opacity).replace(' ','')
                chain.append(f'drop-shadow({result.shadow_dx:g}px {result.shadow_dy:g}px {result.shadow_blur:g}px {color})')
            continue
        raise _error('Only static brightness and drop-shadow CSS filters are supported')
    return replace(result,filter_chain=tuple(chain))


def _expand(declarations):
    """Expand font before the cascade; shorthand resets every font longhand."""
    fields=('font-style','font-weight','font-size','line-height','font-family')
    for name,value,*flags in declarations:
        important=bool(flags[0]) if flags else False
        if name!='font':
            yield name,value,important;continue
        if value in {'inherit','initial','unset'}:
            for field in fields:yield field,value,important
            continue
        match=re.fullmatch(r'(.*?)(\d+(?:\.\d+)?(?:px|pt|em|rem|%))(?:/([^\s]+))?\s+(.+)',value,re.I)
        if not match:raise _error('Unsupported CSS font shorthand')
        font_style=font_weight='normal'
        for token in match[1].split():
            if token in {'italic','oblique'}:font_style=token
            elif token in {'bold','bolder','lighter'} or re.fullmatch(r'[1-9]00',token):font_weight=token
            elif token!='normal':raise _error('Unsupported CSS font shorthand component '+token)
        for field,item in zip(fields,(font_style,font_weight,match[2],match[3] or 'normal',match[4])):
            yield field,item,important


def apply_declarations(style: ResolvedStyle, declarations, *, kind: str='node-label',
                       inherited: ResolvedStyle | None=None, svg_text: bool=False, paint_resources=None) -> ResolvedStyle:
    """Apply native paint/font declarations, also used for safe inline HTML style."""
    if isinstance(declarations,str):declarations=parse_declarations(declarations)
    winners={}
    for index,(name,value,important) in enumerate(_expand(declarations)):
        if name in style.important_properties and not important:continue
        rank=(int(important),index)
        if name not in winners or rank>=winners[name][0]:winners[name]=(rank,value)
    values={name:item[1] for name,item in winners.items()}
    important=set(style.important_properties)
    important.update(name for name,(rank,_) in winners.items() if rank[0])
    style=replace(style,important_properties=tuple(sorted(important)))
    custom=dict(style.custom_properties)
    for name,value in values.items():
        if not name.startswith('--'):continue
        if value=='initial':custom.pop(name,None)
        elif value not in {'inherit','unset'}:custom[name]=value
    resolved_custom={}
    for name,value in custom.items():
        try:resolved_custom[name]=_substitute_vars(value,custom)
        except MermaidError:
            # An unused cyclic/invalid variable is not a paint error. A later
            # use without fallback still fails rather than passing var() to Canvas.
            continue
    style=replace(style,custom_properties=tuple(resolved_custom.items()))
    values={name:_substitute_vars(value,resolved_custom) for name,value in values.items() if not name.startswith('--')}
    parent=inherited or style
    if 'color' in values:
        value=values.pop('color')
        inherited_color=parent.current_color or parent.text_color
        color=inherited_color if value in {'inherit','unset'} else 'black' if value=='initial' else _color(value,inherited_color)
        style=replace(style,current_color=color)
        if kind in _TEXT and not svg_text and kind!='title':style=replace(style,text_color=color)
    # Relative element fonts use the parent's computed font, not a UA <small>
    # default or an earlier winning declaration on this same element.
    if 'font-size' in values:
        size=values.pop('font-size')
        style=replace(style,font_size=parent.font_size if size in {'inherit','unset'} else 16 if size=='initial' else css_size(size,parent.font_size))
    for name,value in values.items():
        if value=='unset' and name in {'opacity','display','max-width','background','background-color',
                                       'filter','text-decoration','text-decoration-line','dominant-baseline'}:
            value='initial'
        if value in {'inherit','unset'}:
            field={'color':'text_color','font-family':'font_family','font-weight':'font_weight',
                   'font-style':'font_style','line-height':'line_height','text-align':'text_align',
                   'white-space':'white_space','text-decoration':'decoration','text-decoration-line':'decoration',
                   'fill':'text_color' if kind in _TEXT and (svg_text or kind=='title') else 'fill','stroke':'stroke','stroke-width':'stroke_width',
                   'opacity':'opacity','fill-opacity':'fill_opacity','stroke-opacity':'stroke_opacity',
                   'background':'fill' if kind=='canvas' else 'background',
                   'background-color':'fill' if kind=='canvas' else 'background','display':'display','stroke-dasharray':'dash',
                   'stroke-linecap':'line_cap','stroke-linejoin':'line_join','stroke-dashoffset':'dash_offset',
                   'letter-spacing':'letter_spacing','word-spacing':'word_spacing','text-transform':'text_transform',
                   'overflow-wrap':'overflow_wrap','word-wrap':'overflow_wrap','word-break':'word_break',
                   'hyphens':'hyphens','text-shadow':'text_shadows','max-width':'max_width'}.get(name)
            if field:style=replace(style,**{field:getattr(parent,field)})
            if name=='line-height':style=replace(style,line_height_px=parent.line_height_px)
            if name=='text-anchor':style=replace(style,text_anchor=parent.text_anchor)
            if name=='direction':style=replace(style,direction=parent.direction)
            if name=='filter':
                style=replace(style,**{field:getattr(parent,field) for field in
                    ('shadow_dx','shadow_dy','shadow_blur','shadow_color','shadow_opacity','brightness','filter_chain')})
            continue
        if value=='initial':
            value={'color':'black','fill':'black','stroke':'none','stroke-width':'1px',
                   'font-family':'"Times New Roman", serif','font-weight':'normal','font-style':'normal',
                   'line-height':'normal','text-align':'left','white-space':'normal',
                   'text-decoration':'none','text-decoration-line':'none','opacity':'1','fill-opacity':'1',
                   'stroke-opacity':'1','background':'transparent','background-color':'transparent',
                   'display':'inline','stroke-dasharray':'none','filter':'none','direction':'ltr',
                   'text-anchor':'start','dominant-baseline':'auto','stroke-linecap':'butt',
                   'stroke-linejoin':'miter','stroke-dashoffset':'0','letter-spacing':'normal',
                   'word-spacing':'normal','text-transform':'none','overflow-wrap':'normal',
                   'word-wrap':'normal','word-break':'normal','hyphens':'manual','text-shadow':'none',
                   'visibility':'visible','overflow':'visible','max-width':'none'}.get(name,value)
        if name.startswith('--'):continue
        if name in _LAYOUT_CSS:
            if name=='max-width':
                if value=='none':style=replace(style,max_width=None)
                elif value.endswith('%'):raise _error('Percentage max-width requires a finite containing block')
                else:style=replace(style,max_width=css_size(value,parent.font_size))
                continue
            permitted={'display':{'block','inline','inline-block','table','table-cell','table-row','none'},
                       'white-space':{'normal','nowrap','pre','pre-wrap','break-spaces'},
                       'text-anchor':{'middle','start','end'},'dominant-baseline':{'auto','alphabetic','middle','central'}}
            if value not in permitted[name]:raise _error(f'CSS {name}:{value} is not representable by this label contract')
            if name=='white-space':style=replace(style,white_space=value)
            elif name=='display':style=replace(style,display=value)
            elif name=='text-anchor':style=replace(style,text_anchor=value)
            elif value not in {'auto','alphabetic'}:
                raise _error('Non-alphabetic SVG dominant-baseline requires a deferred text positioning contract')
            continue
        if name in {'color','fill','stroke','background','background-color'}:
            gradient=re.fullmatch(r'''url\(\s*["']?#([^\s)'"<>]+)["']?\s*\)''',value) if name in {'fill','stroke'} else None
            if gradient:
                resource=(paint_resources or {}).get(gradient[1])
                if resource is None:raise _error('Unregistered static gradient: '+gradient[1])
                stops,direction=resource
                if kind in _TEXT and svg_text:raise _error('Text paint-server gradients need a native text-gradient contract')
                style=replace(style,**{name:stops[0][1],name+'_gradient':stops,name+'_gradient_direction':direction})
                continue
            color=_color(value,style.current_color or style.text_color)
            field={'color':'text_color','fill':'text_color' if kind in _TEXT and (svg_text or kind=='title') else 'fill',
                   'stroke':'stroke','background':'fill' if kind=='canvas' else 'background',
                   'background-color':'fill' if kind=='canvas' else 'background'}[name]
            style=replace(style,**{field:color})
            if name=='stroke':style=replace(style,stroke_gradient=(),**({'text_stroke_color':color} if kind in _TEXT and svg_text else {}))
            if name=='fill':style=replace(style,fill_gradient=())
        elif name=='stroke-width':
            amount=css_size(value,style.font_size)
            style=replace(style,stroke_width=amount,**({'text_stroke_width':amount} if kind in _TEXT and svg_text else {}))
        elif name=='mix-blend-mode':
            if value not in {'normal','multiply','screen','overlay','darken','lighten','color-dodge','color-burn','hard-light','soft-light','difference','exclusion','hue','saturation','color','luminosity'}:raise _error('Invalid blend mode')
            style=replace(style,blend_mode='source-over' if value=='normal' else value)
        elif name=='paint-order':
            if value not in {'normal','stroke','stroke fill','stroke fill markers','fill stroke','fill stroke markers'}:raise _error('Unsupported paint order')
        elif name=='font-family':
            if any(c in value for c in '\r\n{}<>'):raise _error('Invalid CSS font family')
            style=replace(style,font_family=value)
        elif name=='font-weight':
            weight={'bolder':'bold','lighter':'normal'}.get(value,value)
            if weight not in {'normal','bold'} and not re.fullmatch(r'[1-9]00',weight):raise _error('Invalid CSS font weight')
            style=replace(style,font_weight=weight)
        elif name=='font-style':
            if value not in {'normal','italic','oblique'}:raise _error('Invalid CSS font style')
            style=replace(style,font_style=value)
        elif name=='line-height':
            absolute=None
            if value=='normal':number=1.2
            elif re.fullmatch(r'\d+(?:\.\d+)?',value):number=float(value)
            else:
                absolute=css_size(value,style.font_size);number=absolute/max(style.font_size,.001)
            style=replace(style,line_height=number,line_height_px=absolute)
        elif name in {'opacity','fill-opacity','stroke-opacity'}:style=replace(style,**{name.replace('-','_'):_opacity(value)})
        elif name=='stroke-dasharray':
            dash=() if value=='none' else tuple(css_size(n,style.font_size) for n in re.split(r'[,\s]+',value) if n)
            style=replace(style,dash=dash)
        elif name=='stroke-dashoffset':
            negative=value.startswith('-')
            style=replace(style,dash_offset=(-1 if negative else 1)*css_size(value.lstrip('+-'),style.font_size))
        elif name in {'stroke-linecap','stroke-linejoin'}:
            allowed={'stroke-linecap':{'butt','round','square'},'stroke-linejoin':{'miter','round','bevel'}}[name]
            if value not in allowed:raise _error('Invalid '+name)
            style=replace(style,**{'line_cap' if name=='stroke-linecap' else 'line_join':value})
        elif name in {'letter-spacing','word-spacing'}:
            amount=0 if value=='normal' else (-1 if value.startswith('-') else 1)*css_size(value.lstrip('+-'),style.font_size)
            style=replace(style,**{name.replace('-','_'):str(amount)+'px'})
        elif name=='text-transform':
            if value not in {'none','uppercase','lowercase','capitalize'}:raise _error('Unsupported text transform')
            style=replace(style,text_transform=value)
        elif name in {'overflow-wrap','word-wrap'}:
            if value not in {'normal','break-word','anywhere'}:raise _error('Unsupported wrapping policy')
            style=replace(style,overflow_wrap=value)
        elif name=='word-break':
            if value not in {'normal','break-all','keep-all','break-word'}:raise _error('Unsupported word break policy')
            style=replace(style,word_break=value)
        elif name=='hyphens':
            if value not in {'none','manual'}:raise _error('Automatic language hyphenation needs the separate language dictionary module')
            style=replace(style,hyphens=value)
        elif name=='text-shadow':
            shadows=[]
            if value!='none':
                for shadow in _split(value,','):
                    components=[part for part in _split(shadow.strip(),' ') if part]
                    lengths=[];colors=[]
                    for part in components:
                        if re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:px|pt|em|rem)?',part):
                            lengths.append((-1 if part.startswith('-') else 1)*css_size(part.lstrip('+-'),style.font_size))
                        else:colors.append(part)
                    if len(lengths) not in {2,3} or len(lengths)==3 and lengths[2]<0:raise _error('Invalid text shadow')
                    shadows.append((lengths[0],lengths[1],lengths[2] if len(lengths)==3 else 0,_color(' '.join(colors) or style.current_color or style.text_color,style.current_color or style.text_color)))
            style=replace(style,text_shadows=tuple(shadows))
        elif name=='visibility':
            if value not in {'visible','hidden','collapse'}:raise _error('Invalid visibility')
            if value!='visible':style=replace(style,opacity=0)
        elif name in {'animation','animation-name','animation-duration','animation-timing-function',
                      'animation-iteration-count','cursor','pointer-events','transition','text-overflow'}:
            continue  # Static snapshot; natural-size labels have no overflow host.
        elif name=='overflow':
            if value not in {'visible','hidden','clip'}:raise _error('Unsupported overflow')
        elif name.startswith('text-decoration'):
            if any(token not in {'none','underline','line-through','overline','solid'} for token in value.split()):raise _error('Unsupported text decoration')
            style=replace(style,decoration='' if value=='none' else value)
        elif name=='text-align':
            if value not in {'left','center','right','start','end'}:raise _error('Unsupported text alignment')
            style=replace(style,text_align=value)
        elif name=='direction':
            if value not in {'ltr','rtl'}:raise _error('CSS direction must be ltr or rtl')
            style=replace(style,direction=value)
        elif name=='filter':
            style=_filter(style,value)
    if style.line_height_px is not None:
        style=replace(style,line_height=style.line_height_px/max(style.font_size,.001))
    return style


def _matches(selector: str, diagram: Flowchart, kind: str, identifier: str, tag: str | None,
             css_classes: tuple[str,...]=(), *, host_classes: tuple[str,...] | None=None) -> bool:
    classes={'flowchart','root'}
    if kind in {'node','node-label'}:classes|={'node','default'}
    if kind in {'group','group-title'}:classes|={'cluster'}
    if kind=='node-label':classes|={'label'}|({'nodeLabel'} if diagram.config.html_labels else set())
    if kind=='edge-label':classes|={'label','edgeLabel'}
    if kind=='group-title':classes|={'cluster-label'}
    if kind=='title':classes|={'flowchartTitleText'}
    semantic_edge=next((e for e in diagram.edges if e.id==identifier),None) if kind in {'edge','edge-label'} else None
    if kind=='edge':
        thickness='invisible' if semantic_edge and semantic_edge.stroke=='invisible' else 'thick' if semantic_edge and semantic_edge.stroke=='thick' else 'normal'
        pattern='dotted' if semantic_edge and semantic_edge.stroke=='dotted' else 'solid'
        classes|={'edgePath','flowchart-link','edge-thickness-'+thickness,'edge-pattern-'+pattern}
    classes.update(css_classes)
    semantic=next((n for n in diagram.nodes if n.id==identifier),None) if kind in {'node','node-label'} else next((g for g in diagram.groups if g.id==identifier),None) if kind in {'group','group-title'} else None
    if semantic is not None:classes.update(semantic.classes)
    if host_classes is not None:classes={'flowchart','root',*host_classes,*css_classes}
    for negation in re.findall(r':not\(([^)]+)\)',selector):
        if _matches(negation,diagram,kind,identifier,tag,css_classes,host_classes=host_classes):return False
    selector=re.sub(r':not\([^)]+\)','',selector)
    attribute=re.compile(r'''\[\s*([\w-]+)\s*(?:(~=|\|=|\^=|\$=|\*=|=)\s*(?:"([^"]*)"|'([^']*)'|([^\]\s]+)))?\s*\]''')
    node_index=next((i for i,n in enumerate(diagram.nodes) if n.id==identifier),0)
    for match in attribute.finditer(selector):
        name,operator,quoted,double_quoted,bare_value=match.groups()
        value=next((v for v in (quoted,double_quoted,bare_value) if v is not None),'')
        if name=='class':
            if operator is None:
                if not classes:return False
            elif operator=='~=':
                if value not in classes:return False
            else:raise _error('Semantic class attributes support presence and token ~= matching only')
            continue
        if name=='data-look':actuals=(diagram.config.look,)
        elif name=='data-theme':actuals=(diagram.config.theme,)
        elif name in {'data-id','id'}:actuals=(identifier,f'flowchart-{identifier}-{node_index}')
        else:raise _error('Unsupported semantic CSS attribute '+name)
        if operator is None:
            if not any(actual not in (None,'') for actual in actuals):return False
            continue
        def accepts(actual):
            actual=str(actual or '')
            if operator=='=':return actual==value
            if operator=='~=':return value in actual.split()
            if operator=='|=':return actual==value or actual.startswith(value+'-')
            if not value:return False
            if operator=='^=':return actual.startswith(value)
            if operator=='$=':return actual.endswith(value)
            return value in actual
        if not any(accepts(actual) for actual in actuals):return False
    selector=attribute.sub('',selector)
    if '[' in selector or ']' in selector:raise _error('Malformed or unsupported semantic CSS attribute selector')
    selector=selector.replace(':root','').replace('&','')
    if ':' in selector:raise _error('Unsupported static CSS pseudo-class')
    if any(c not in classes for c in re.findall(r'\.([\w-]+)',selector)):return False
    node_index=next((i for i,n in enumerate(diagram.nodes) if n.id==identifier),0)
    identifiers={identifier,f'flowchart-{identifier}-{node_index}'}
    if semantic_edge and semantic_edge.source_id:identifiers.add(semantic_edge.source_id)
    if any(i not in identifiers for i in re.findall(r'#([\w-]+)',selector)):return False
    bare=re.sub(r'[.#][\w-]+','',selector)
    tags=re.findall(r'[A-Za-z][\w-]*',bare)
    physical='rect'
    if kind=='node':
        shape=next((n.shape for n in diagram.nodes if n.id==identifier),'square')
        physical='circle' if shape in {'circle','doublecircle'} else 'rect' if shape in {'square','round','subroutine'} else 'polygon' if shape in {'diamond','hexagon','lean_left','lean_right','trapezoid','inv_trapezoid'} else 'path'
    allowed={'svg','g'}
    if host_classes is not None:allowed|={'foreignObject','div','span','p',tag}
    elif kind=='canvas':allowed={'svg'}
    elif kind in {'node','group'}:allowed|={physical}
    elif kind=='edge':allowed|={'path'}
    elif kind=='title' or not diagram.config.html_labels:allowed|={'text','tspan'}
    else:allowed|={'foreignObject','div','span','p'}|({tag} if tag else set())
    return all(t in allowed for t in tags)


def resolve_inline_svg_style(diagram: Flowchart, kind: str, semantic_id: str, *,
                             tag: str, base: ResolvedStyle,
                             css_classes: tuple[str,...]=(),
                             inherited_base: ResolvedStyle | None=None) -> ResolvedStyle:
    """Resolve host CSS on an embedded SVG child, before its own inline style.

    Presentation attributes are in base. An SVG in an img/data URI is isolated
    and must never call this provider. Local node shape inline styles are not
    ancestor CSS rules and therefore do not apply to this child.
    """
    config=diagram.config;variables=dict(config.theme_variables)
    host={'label'};node=next((n for n in diagram.nodes if n.id==semantic_id),None)
    if kind=='node-label' and node is not None:
        host|={'default','nodeLabel',*node.classes}
        if node.shape=='imageSquare':host.add('image-shape')
        elif node.shape in {'icon','iconCircle','iconSquare','iconRounded'}:host.add('icon-shape')
        elif config.look=='handDrawn' and node.shape not in {'stateStart','stateEnd'}:host.add('rough-node')
        else:host.add('node')
    elif kind=='group-title':
        group=next((g for g in diagram.groups if g.id==semantic_id),None)
        host|={'cluster','cluster-label',*(group.classes if group else ())}
    elif kind=='edge-label':host.add('edgeLabel')
    else:raise ValueError('Unknown inline SVG host '+kind)
    style=replace(base,important_properties=());thresholds={}
    if 'node' in host and tag in {'rect','circle','ellipse','polygon','path'}:
        style=replace(style,fill=config.fill,stroke=config.stroke,
                      stroke_width=config.node_stroke_width,stroke_gradient=())
        thresholds={'fill':11,'stroke':11,'stroke-width':11}
        if config.look=='neo' and tag in {'rect','circle','polygon','path'}:
            thresholds['stroke']=21
            if tag=='path':thresholds['stroke-width']=21
            if variables.get('useGradient'):
                start,stop=variables.get('gradientStart'),variables.get('gradientStop')
                if isinstance(start,str) and isinstance(stop,str):style=replace(style,stroke_gradient=((0,start),(1,stop)))
    if 'cluster' in host and tag in {'rect','path'}:
        group=next((g for g in diagram.groups if g.id==semantic_id),None)
        borders=variables.get('borderColorArray',config.group_borders)
        fills=variables.get('bkgColorArray',config.group_fills)
        palette=config.theme in {'redux-color','redux-dark-color'} and isinstance(borders,(tuple,list)) and bool(borders)
        if tag=='rect' or palette:
            slot=group.color_index if group else 0
            style=replace(style,fill=str(fills[slot%len(fills)]) if palette and fills else str(variables.get('clusterBkg',config.fill)),
                stroke=str(borders[slot%len(borders)]) if palette else str(variables.get('clusterBorder',config.stroke)),
                stroke_width=1 if tag=='rect' else style.stroke_width,stroke_gradient=())
            thresholds={'fill':31 if palette else 11,'stroke':31 if palette else 11,'stroke-width':11}
    winners={}
    for order,(selector,declarations) in enumerate(parse_css(config.theme_css)):
        if not _matches(selector,diagram,kind,semantic_id,tag,css_classes,host_classes=tuple(host)):continue
        specificity=_specificity(selector)
        for index,(name,value,important) in enumerate(_expand(declarations)):
            if not important and specificity<thresholds.get(name,0):continue
            rank=(int(important),specificity,order,index)
            if name not in winners or rank>=winners[name][0]:winners[name]=(rank,value)
    return apply_declarations(style,tuple((name,value,bool(rank[0])) for name,(rank,value) in winners.items()),
                              kind='node',inherited=inherited_base or base)


def _specificity(selector: str) -> int:
    return 100*len(re.findall(r'#[\w-]+',selector))+10*len(re.findall(r'\.[\w-]+|\[[^]]+\]|:[\w-]+',selector))+len(re.findall(r'(?:^|[\s>+~])[A-Za-z][\w-]*',selector))


def _theme_specificity(diagram: Flowchart, kind: str, name: str, selector: str, *, inline_tag: bool=False) -> int | None:
    """Explicit source theme declarations beat inherited ancestor declarations.

    This carries provenance on native paint intents, not a recreated element tree.
    None means that this property on an ancestor cannot replace an explicit paint
    declaration on the target. User !important still applies to its own target.
    """
    if inline_tag:return 0
    last=re.split(r'\s+',selector.strip())[-1]
    if kind in {'node','group'} and name in {'fill','stroke','stroke-width','stroke-dasharray','filter'}:
        own=bool(re.search(r'(?:^|\W)(?:rect|circle|ellipse|polygon|path)(?:$|\W)',last)) or any('.'+c in last for c in ('label-container','outer-path','basic')) or '*' in last
        if not own:return None
        if kind=='group':
            variables=dict(diagram.config.theme_variables)
            palette=variables.get('borderColorArray',diagram.config.group_borders)
            gated=diagram.config.theme in {'redux-color','redux-dark-color'} and isinstance(palette,(tuple,list)) and bool(palette)
            if name in {'fill','stroke'} and gated:return 31
        if name in {'stroke','filter'} and diagram.config.look=='neo':return 21
        return 11
    if kind=='edge' and name in {'fill','stroke','stroke-width','stroke-dasharray'}:
        if 'path' not in last and '.flowchart-link' not in last and '*' not in last:return None
        return 10
    if kind in _TEXT:
        if kind=='title':return 10 if name in {'fill','font-size'} else 0
        if name=='font-family':
            if not any(c in last for c in ('.label','.nodeLabel','.edgeLabel','.cluster-label','text','span','p','*')):return None
            return 10
        if name in {'color','fill'}:
            if diagram.config.html_labels and name=='color':
                if not any(c in last for c in ('.nodeLabel','.edgeLabel','span','p','*')):return None
                return 11 if kind=='group-title' else 1
            if not diagram.config.html_labels and name=='fill':
                if 'text' not in last and '*' not in last:return None
                return 11
        if kind=='edge-label' and name in {'background','background-color'}:return 11
    return 0


def resolve_style(diagram: Flowchart, kind: str, semantic_id: str='', *, tag: str | None=None,
                  base: ResolvedStyle | None=None, css_classes: tuple[str,...]=(),
                  inherited_base: ResolvedStyle | None=None) -> ResolvedStyle:
    """Resolve one typed paint/text target against diagram theme and themeCSS."""
    if kind=='diagram-title':kind='title'
    if kind not in {'canvas','node','edge','group',*_TEXT}:raise ValueError('Unknown style target '+kind)
    config=diagram.config;variables=dict(config.theme_variables)
    style=ResolvedStyle(fill=config.fill,stroke=config.stroke,text_color=config.text_color,
        stroke_width=config.node_stroke_width,font_family=config.font_family,font_size=config.font_size,
        line_height=config.line_height,shadow_opacity=config.shadow_opacity)
    if kind in {'node','group'} and config.look=='neo':
        shadow=variables.get('dropShadow')
        if shadow is not None:style=_shadow(style,str(shadow) if shadow else 'none',dark='dark' in config.theme)
        else:style=replace(style,shadow_dx=config.shadow_offset_x,shadow_dy=config.shadow_offset_y,
                           shadow_color='#ffffff' if 'dark' in config.theme else '#000000')
        if variables.get('useGradient'):
            start,stop=variables.get('gradientStart'),variables.get('gradientStop')
            if isinstance(start,str) and isinstance(stop,str):
                style=replace(style,stroke_gradient=((0,start),(1,stop)))
    if kind=='canvas':style=replace(style,fill=config.background,stroke='none',stroke_width=0,shadow_opacity=0)
    if kind=='edge':style=replace(style,fill='none',stroke=config.edge_color,stroke_width=config.edge_stroke_width,shadow_opacity=0)
    if kind=='edge-label':style=replace(style,background=config.edge_label_background,shadow_opacity=0)
    if kind in {'group','group-title'}:
        group=next((g for g in diagram.groups if g.id==semantic_id),None)
        slot=group.color_index if group else 0
        borders=variables.get('borderColorArray',config.group_borders)
        fills=variables.get('bkgColorArray',config.group_fills)
        palette=config.theme in {'redux-color','redux-dark-color'} and isinstance(borders,(tuple,list)) and bool(borders)
        fill=str(fills[slot%len(fills)]) if palette and isinstance(fills,(tuple,list)) and fills else str(variables.get('clusterBkg',config.fill))
        stroke=str(borders[slot%len(borders)]) if palette else str(variables.get('clusterBorder',config.stroke))
        style=replace(style,fill=fill,stroke=stroke,stroke_width=config.group_stroke_width,
                      text_color=str(variables.get('titleColor',config.text_color)))
        if palette:style=replace(style,stroke_gradient=())
    if kind=='title':style=replace(style,font_size=18,line_height=1.1,text_color=str(variables.get('textColor',config.text_color)),shadow_opacity=0)
    if base is not None:style=replace(base,important_properties=())
    semantic=None
    if kind in {'node','node-label'}:semantic=next((n for n in diagram.nodes if n.id==semantic_id),None)
    elif kind in {'group','group-title'}:semantic=next((g for g in diagram.groups if g.id==semantic_id),None)
    elif kind in {'edge','edge-label'}:semantic=next((e for e in diagram.edges if e.id==semantic_id),None)
    if semantic is not None:
        css_classes=tuple(dict.fromkeys((*getattr(semantic,'classes',()),*css_classes)))
    if kind=='node' and semantic is not None:
        shape=semantic.shape
        if shape=='text':style=replace(style,fill='none',stroke_width=0,shadow_opacity=0)
        if shape in {'curlyBraceLeft','curlyBraceRight','curlyBraces'}:style=replace(style,fill='none',shadow_opacity=0)
        if shape=='forkJoin' and config.look=='handDrawn':
            style=replace(style,fill=config.edge_color,stroke=config.edge_color,shadow_opacity=0)
        if shape in {'stateStart','stateEnd'} and config.look=='handDrawn':
            style=replace(style,hachure_color=style.stroke)
        if shape=='filledCircle':style=replace(style,fill=config.stroke)
        if shape=='anchor':
            style=replace(style,fill=config.edge_color,stroke=config.stroke if config.look=='neo' else config.edge_color,
                stroke_width=config.node_stroke_width if config.look=='neo' else 0,shadow_opacity=0)
        if shape=='note' and config.look=='handDrawn':style=replace(style,fill=str(variables.get('noteBkgColor','#fff5ad')),
            stroke=str(variables.get('noteBorderColor',config.stroke)),stroke_gradient=())
        if shape=='collapsedGroup':
            borders=variables.get('borderColorArray',config.group_borders)
            fills=variables.get('bkgColorArray',config.group_fills)
            slot=semantic.color_index or 0
            palette=config.theme in {'redux-color','redux-dark-color'} and isinstance(borders,(tuple,list)) and bool(borders)
            style=replace(style,fill=str(fills[slot%len(fills)]) if palette and fills else str(variables.get('clusterBkg',config.fill)),
                stroke=str(borders[slot%len(borders)]) if palette else str(variables.get('clusterBorder',config.stroke)),stroke_gradient=())
    if kind=='edge' and semantic is not None:
        if semantic.stroke=='thick':style=replace(style,stroke_width=3.5)
        elif semantic.stroke=='invisible':style=replace(style,stroke_width=0)
        if semantic.stroke=='dotted':style=replace(style,dash=(2,))
    winners={}
    for order,(selector,declarations) in enumerate(parse_css(config.theme_css)):
        if tag is not None and base is not None:
            # Parent semantic-label rules have already produced `base`. Only
            # rules targeting this actual inline tag/class apply again; an em
            # length on .nodeLabel must not multiply at every nested <strong>.
            last=re.split(r'[\s>]+',selector.strip())[-1]
            target_tag=re.match(r'^([A-Za-z][\w-]*)',last)
            targets_tag=bool(target_tag and target_tag[1]==tag) or '*' in last
            attribute_classes=re.findall(r'''\[\s*class\s*~=\s*["']?([\w-]+)["']?\s*\]''',last)
            targets_class=any('.'+name in last or name in attribute_classes for name in css_classes)
            if not targets_tag and not targets_class:continue
        if not _matches(selector,diagram,kind,semantic_id,tag,css_classes):continue
        specificity=_specificity(selector)
        for declaration_order,(name,value,important) in enumerate(_expand(declarations)):
            threshold=_theme_specificity(diagram,kind,name,selector,inline_tag=tag is not None and base is not None)
            if threshold is None or (not important and specificity<threshold):continue
            rank=(int(important),specificity,order,declaration_order)
            if name not in winners or rank>=winners[name][0]:winners[name]=(rank,value)
    values=tuple((name,value,bool(rank[0])) for name,(rank,value) in winners.items())
    style=apply_declarations(style,values,kind=kind,inherited=inherited_base,
                             svg_text=kind=='title' or not config.html_labels)
    # Fixed compileStyles concatenates class declarations in class order, then
    # local declarations; styles2String promotes the resulting paint/text to
    # inline !important. Label and shape targets receive distinct properties.
    if semantic is not None and not (tag is not None and base is not None):
        classes=css_classes if kind in {'edge','edge-label'} else ('default','node',*css_classes)
        definitions={item.name:item for item in diagram.class_definitions}
        declarations=[]
        for name in classes:
            definition=definitions.get(name)
            if definition:declarations.extend((*definition.styles,*definition.text_styles))
        if kind in {'edge','edge-label'}:declarations.extend(diagram.default_edge_styles)
        declarations.extend(semantic.styles)
        compiled=[]
        label_properties={'color','font-size','font-family','font-weight','font-style',
            'text-decoration','text-align','text-transform','line-height','letter-spacing',
            'word-spacing','text-shadow','text-overflow','white-space','word-wrap',
            'word-break','overflow-wrap','hyphens','opacity','visibility','display'}
        for declaration in declarations:
            if not declaration.strip():continue
            # bgFill is a legacy FlowDB text-style bookkeeping key, never CSS.
            if declaration.split(':',1)[0].strip()=='bgFill':continue
            for name,value,_ in parse_declarations(declaration):
                if name in {'animation','animation-name'}:continue
                if kind in _TEXT:
                    if name not in label_properties:continue
                    if name=='color' and not config.html_labels:name='fill'
                elif name in label_properties-{'opacity','visibility','display'}:continue
                compiled.append((name,value,True))
        style=apply_declarations(style,compiled,kind=kind,inherited=inherited_base,
            svg_text=kind=='title' or not config.html_labels)
        if kind=='edge':
            animation=semantic.animation or ('fast' if semantic.animate else None)
            if animation in {'fast','slow'}:
                changes={}
                for name,field,value in (('stroke-dasharray','dash',(9,5)),('stroke-dashoffset','dash_offset',900),('stroke-linecap','line_cap','round')):
                    if name not in style.important_properties:changes[field]=value
                style=replace(style,**changes)
    if kind=='node' and semantic is not None and semantic.shape in {'stateStart','stateEnd'} and config.look=='handDrawn':
        style=replace(style,hachure_color=style.stroke)
    return style
