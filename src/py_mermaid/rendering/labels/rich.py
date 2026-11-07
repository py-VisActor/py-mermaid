"""Native label fragments/runs for the fixed Mermaid createText branches.

HTMLParser only interprets inert label markup; no DOM, URL loading, JavaScript,
browser layout or alternative font/shaping implementation is involved.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import html,base64
from html.parser import HTMLParser
import math
import re
import textwrap
import unicodedata
from collections.abc import Callable
from typing import Any

from ...model.flowchart import Box, FlowConfig, MeasuredLine, MeasuredTextRun, MermaidError, ResolvedStyle
from ...model.controls import ControlSpec, ControlLayout
from ..styles import apply_declarations, parse_declarations
from .sanitize import sanitize_markup
from .math import protect_math


@dataclass(frozen=True)
class Fragment:
    text: str
    style: ResolvedStyle
    shift: float = 0.0
    preserve_space: bool = False
    alignment: str = ''
    asset_id: str = ''
    asset_width: float = 0
    asset_height: float = 0
    asset_kind: str = 'image'
    math_key: str = ''
    math_width: float = 0
    math_ascent: float = 0
    math_descent: float = 0
    min_line_height: float = 0
    width_limit: float | None = None
    control: ControlSpec | None = None
    control_layout: ControlLayout | None = None
    control_parent_style: ResolvedStyle | None = None


_DROP = frozenset({"script","iframe","object","embed","template","noscript"})
_RESOURCE = frozenset({"img","image","svg","math","video","audio","canvas","source"})
_BLOCK = frozenset({"p","div","section","article","header","footer","aside","address","blockquote","form",
                    "h1","h2","h3","h4","h5","h6","pre","ul","ol","li","table","tr","dl","dt","dd"})
_INLINE = frozenset({"b","strong","i","em","u","s","strike","del","ins","span","small","big","sub","sup",
                     "code","kbd","samp","var","a","font","mark","abbr","cite","q","label","time","wbr","tt"})


def _ordered_list_sizes(markup: str) -> tuple[int,...]:
    class Counter(HTMLParser):
        def __init__(self):super().__init__();self.counts=[];self.lists=[]
        def handle_starttag(self,tag,attrs):
            if tag=='ol':self.lists.append(len(self.counts));self.counts.append(0)
            elif tag=='ul':self.lists.append(None)
            elif tag=='li' and self.lists and self.lists[-1] is not None:self.counts[self.lists[-1]]+=1
        def handle_endtag(self,tag):
            if tag in {'ol','ul'} and self.lists:self.lists.pop()
    counter=Counter();counter.feed(markup);counter.close();return tuple(counter.counts)


def _inline_svgs(text:str,style=None,resolver=None)->str:
    result=[];cursor=0
    for opening in re.finditer(r'<svg\b[^>]*>',text,re.I):
        if opening.start()<cursor:continue
        depth=1;end=None
        if opening.group().endswith('/>'):end=opening.end()
        else:
            for token in re.finditer(r'</?svg\b[^>]*>',text[opening.end():],re.I):
                raw=token.group();depth+=-1 if raw.startswith('</') else 0 if raw.endswith('/>') else 1
                if depth==0:end=opening.end()+token.end();break
        if end is None:raise MermaidError('Unclosed inline SVG',code='INVALID_RESOURCE')
        svg=text[opening.start():end]
        # An SVG namespace is required by the native standalone SVG decoder.
        if not re.search(r'\bxmlns\s*=',opening.group()):svg=svg.replace('<svg','<svg xmlns="http://www.w3.org/2000/svg"',1)
        if resolver is not None:
            from ...resources.svg import project_inline_svg
            data=project_inline_svg(svg,style,resolver)
        else:data=svg.encode('utf8')
        encoded=base64.b64encode(data).decode('ascii')
        result.extend((text[cursor:opening.start()],'<img data-py-mermaid-inline-svg="true" src="data:image/svg+xml;base64,'+encoded+'">'));cursor=end
    result.append(text[cursor:]);return ''.join(result)

def _deferred(text: str) -> None:
    if re.search(r"\$\$.*?\$\$",text,re.S):
        raise MermaidError("Math labels are handled by the separate math module",code="UNSUPPORTED_SYNTAX")


class _HTML(HTMLParser):
    def __init__(self, style: ResolvedStyle, *, interpret: bool,
                 tag_style=None, svg_text: bool = False, asset_loader=None, image_only=False,math_loader=None,math_tokens=None,raw_html=False):
        super().__init__(convert_charrefs=True)
        self.style=style;self.interpret=interpret;self.tag_style=tag_style;self.svg_text=svg_text
        self.stack: list[tuple[str,ResolvedStyle,float,bool,bool,str,float | None]]=[]
        self.parts: list[Fragment]=[];self.shift=0.0;self.pre=style.white_space in {'pre','pre-wrap','break-spaces'};self.drop=[]
        self.lists=[];self.ol_sizes=iter(());self.hidden=style.display=='none'
        self.alignment=style.text_align;self.asset_loader=asset_loader;self.image_only=image_only
        self.math_loader=math_loader;self.math_tokens=math_tokens or {};self.raw_html=raw_html
        self.width_limit=style.max_width if not svg_text and style.display in {'block','inline-block','table','table-cell'} else None
        self.control_capture=None
        self.control_style=None

    def emit(self,text: str):
        if not text or self.hidden:return
        if len(self.parts)>20_000:raise MermaidError("Label fragment budget exceeded",code="LABEL_BUDGET")
        if self.parts and not self.parts[-1].asset_id and not self.parts[-1].math_key and not self.parts[-1].control and self.parts[-1].style==self.style and self.parts[-1].shift==self.shift and self.parts[-1].preserve_space==self.pre and self.parts[-1].alignment==self.alignment and self.parts[-1].width_limit==self.width_limit:
            self.parts[-1]=replace(self.parts[-1],text=self.parts[-1].text+text)
        else:self.parts.append(Fragment(text,self.style,self.shift,self.pre,self.alignment,width_limit=self.width_limit))

    def line(self):
        if self.parts and not self.parts[-1].text.endswith("\n"):self.emit("\n")

    def _finish_control(self):
        control=self.control_capture.build();style=self.control_style
        self.control_capture=None;self.control_style=None
        # Formula protection is label-wide; text fields keep literal TeX while
        # button inner markup is passed back through the existing math pipeline.
        def restore(value):
            for token,formula in self.math_tokens.items():value=value.replace(token,'$$'+formula.tex+'$$')
            return value
        control=replace(control,text=restore(control.text),value=restore(control.value),inner_markup=restore(control.inner_markup),
            legend_text=restore(control.legend_text),legend_markup=restore(control.legend_markup),
            attributes=tuple((key,restore(value)) for key,value in control.attributes),
            options=tuple(replace(option,label=restore(option.label),value=restore(option.value)) for option in control.options))
        if not self.hidden and not control.hidden and style.display!='none':
            if len(self.parts)>=20_000:raise MermaidError('Label fragment budget exceeded',code='LABEL_BUDGET')
            if style.display in {'block','table','table-row'}:self.line()
            strut=self.style.line_height_px if self.style.line_height_px is not None else self.style.font_size*self.style.line_height
            self.parts.append(Fragment('\ufffc',style,self.shift,True,self.alignment,width_limit=self.width_limit,control=control,control_parent_style=self.style,min_line_height=strut))
            if style.display in {'block','table','table-row'}:self.line()

    def handle_starttag(self,tag,attrs):
        if self.control_capture is not None:
            self.control_capture.start(tag,attrs)
            if self.control_capture.finished:self._finish_control()
            return
        if self.drop:
            if tag in _DROP:self.drop.append(tag)
            return
        if tag in _DROP:self.drop.append(tag);return
        attributes={key.lower():value or '' for key,value in attrs if not key.lower().startswith('on')}
        if tag=='br':self.emit("\n");return
        if tag=='wbr':return
        if not self.interpret:
            # Markup is already sanitized. SVG uses literal textContent, so
            # retain every serialized safe attribute instead of a second allowlist.
            self.emit(self.get_starttag_text());return
        from .controls.semantic import CONTROL_TAGS, ControlCapture
        if tag in CONTROL_TAGS:
            from .controls.layout import control_ua_style, split_control_style
            from .controls.semantic import INPUT_TYPES
            input_type=next((value.lower() for name,value in attrs if name.lower()=='type' and value is not None),'text') if tag=='input' else ''
            if tag=='input' and input_type not in INPUT_TYPES:input_type='text'
            control_style=control_ua_style(tag,self.style,disabled='disabled' in attributes,input_type=input_type)
            control_style=replace(control_style,opacity=1)
            if self.tag_style:control_style=self.tag_style(tag,control_style,tuple(attributes.get('class','').split()),self.style)
            css,control_css=split_control_style(attributes.get('style',''))
            if css:control_style=apply_declarations(control_style,css,inherited=self.style,svg_text=False)
            control_style=replace(control_style,opacity=control_style.opacity*self.style.opacity)
            self.control_style=control_style;self.control_capture=ControlCapture(tag,attrs)
            if self.control_capture.finished:self._finish_control()
            return
        icon_classes=attributes.get('class','')
        icon_match=re.search(r'\b(?:fa[bklrs]?:)?fa-([\w-]+)',icon_classes)
        if tag=='img' or (tag in {'i','span'} and icon_match):
            if self.asset_loader is None:raise MermaidError('Explicit resource bundle is required',code='RESOURCE_NOT_FOUND')
            kind=('svg' if attributes.get('data-py-mermaid-inline-svg')=='true' else 'image') if tag=='img' else 'icon'
            identifier=attributes.get('src','') if kind in {'image','svg'} else (next((part for part in icon_classes.split() if part in {'fa','fas','fab','far','fal','fad','fat'}),'fa')+':'+icon_match[1])
            asset_style=replace(self.style,opacity=1)
            if self.tag_style:asset_style=self.tag_style(tag,asset_style,tuple(icon_classes.split()),self.style)
            # configureLabelImages assigns source image geometry after markup CSS.
            declarations=[(name,value,important) for name,value,important in parse_declarations(attributes.get('style','')) if name not in {'width','height','min-width','max-width','min-height','max-height','object-fit','display'}]
            css=';'.join(name+':'+value+(' !important' if important else '') for name,value,important in declarations)
            asset_style=apply_declarations(asset_style,css,inherited=self.style,svg_text=False)
            asset_style=replace(asset_style,opacity=asset_style.opacity*self.style.opacity)
            width,height=self.asset_loader(identifier,kind,attributes,asset_style,self.image_only)
            if kind in {'image','svg'}:self.line()
            if not self.hidden:self.parts.append(Fragment('\ufffc',asset_style,self.shift,False,self.alignment,identifier,width,height,kind))
            if kind in {'image','svg'}:self.emit('\n')
            return
        if tag=='math':raise MermaidError('Math labels belong to the separate math module',code='UNSUPPORTED_SYNTAX')
        if tag in _RESOURCE:raise MermaidError(f"<{tag}> requires a static native resource mapping",code="UNSUPPORTED_LABEL_RESOURCE")
        if tag=='datalist':
            # Datalist is a popup source; standalone options have no rendered
            # native widget. Select captures these before this branch.
            self.drop.append(tag);return
        if tag=='style':raise MermaidError('HTML style elements require a separate stylesheet host mapping; use themeCSS',code='UNSUPPORTED_LABEL_STYLE_ELEMENT')
        if re.search(r'\bfa[bklrs]?\b|\blabel-icon\b',attributes.get('class','')):
            raise MermaidError("Icon label classes require a matching explicit offline resource",code="UNSUPPORTED_LABEL_RESOURCE")
        if len(self.stack)>=256:raise MermaidError("HTML label nesting budget exceeded",code="LABEL_BUDGET")
        if tag=='hr':self.line();self.emit('―');self.line();return
        if tag in {'td','th'} and self.parts and not self.parts[-1].text.endswith(('\n','\t')):self.emit('\t')
        self.stack.append((tag,self.style,self.shift,self.pre,self.hidden,self.alignment,self.width_limit))
        parent_style=self.style;parent_opacity=self.style.opacity
        self.style=replace(self.style,display='block' if tag in _BLOCK else 'inline',opacity=1,max_width=None)
        if tag in {'b','strong','th'}:self.style=replace(self.style,font_weight='bold',**({'font_style':'normal'} if self.svg_text else {}))
        if tag in {'i','em','cite','var'}:self.style=replace(self.style,font_style='italic',**({'font_weight':'normal'} if self.svg_text else {}))
        if tag in {'u','ins'}:self.style=replace(self.style,decoration=' '.join(filter(None,(self.style.decoration,'underline'))))
        if tag in {'s','strike','del'}:self.style=replace(self.style,decoration=' '.join(filter(None,(self.style.decoration,'line-through'))))
        if tag in {'code','kbd','samp','tt','pre'}:self.style=replace(self.style,font_family='monospace')
        if tag=='pre':self.style=replace(self.style,white_space='pre')
        if tag=='small':self.style=replace(self.style,font_size=self.style.font_size*.8)
        if tag=='big':self.style=replace(self.style,font_size=self.style.font_size*1.2)
        if tag in {'sup','sub'}:
            self.shift+=(.35 if tag=='sup' else -.2)*self.style.font_size
            self.style=replace(self.style,font_size=self.style.font_size*.75)
        if tag.startswith('h') and len(tag)==2 and tag[1].isdigit():
            self.style=replace(self.style,font_weight='bold',font_size=self.style.font_size*{1:2,2:1.5,3:1.17,4:1,5:.83,6:.67}[int(tag[1])])
        if tag=='mark':self.style=replace(self.style,background='yellow')
        if tag=='a' and attributes.get('href') and not re.match(r'\s*(?:javascript|vbscript|data):',attributes['href'],re.I):
            self.style=replace(self.style,text_color='#0000ee',decoration='underline')
        if tag=='font':
            if attributes.get('color'):self.style=apply_declarations(self.style,(('color',attributes['color']),),svg_text=self.svg_text)
            if attributes.get('face'):self.style=replace(self.style,font_family=attributes['face'])
            if attributes.get('size'):
                value=attributes['size']
                if re.fullmatch(r'[+-]?\d+',value):
                    index=int(value)+(3 if value.startswith(('+','-')) else 0)
                    self.style=replace(self.style,font_size={1:10,2:13,3:16,4:18,5:24,6:32,7:48}[min(7,max(1,index))])
        if attributes.get('dir'):
            direction=attributes['dir'].lower()
            if direction not in {'ltr','rtl','auto'}:direction='ltr'
            self.style=replace(self.style,direction=direction)
        if tag in {'p','div','td','th'} and attributes.get('align') in {'left','center','right'}:
            self.style=replace(self.style,text_align=attributes['align'])
        if tag in {'table','tr','td','th'} and attributes.get('bgcolor'):
            self.style=replace(self.style,background=attributes['bgcolor'])
        if self.tag_style:self.style=self.tag_style(tag,self.style,tuple(attributes.get('class','').split()),parent_style)
        declarations=attributes.get('style','')
        if re.search(r'url\s*\(|expression\s*\(|@import',declarations,re.I):
            raise MermaidError("HTML paint resources require explicit static native mapping",code="UNSUPPORTED_LABEL_RESOURCE")
        if declarations:self.style=apply_declarations(self.style,declarations,inherited=parent_style,svg_text=self.svg_text)
        if not self.svg_text and self.style.max_width is not None and self.style.display in {'block','inline-block','table','table-cell'}:
            self.width_limit=min(self.width_limit,self.style.max_width) if self.width_limit is not None else self.style.max_width
        self.style=replace(self.style,opacity=self.style.opacity*parent_opacity)
        self.hidden=self.hidden or self.style.display=='none' or 'hidden' in attributes
        self.pre=self.style.white_space in {'pre','pre-wrap','break-spaces'}
        if self.style.display in {'block','table','table-row'}:
            self.line();self.alignment=self.style.text_align
        if tag in {'ul','ol'}:
            count=next(self.ol_sizes,0) if tag=='ol' else 0
            step=-1 if tag=='ol' and 'reversed' in attributes else 1
            try:start=int(attributes.get('start',str(count if step<0 else 1)))
            except ValueError:start=1
            self.lists.append((tag,start-step,step,attributes.get('type','')))
        if tag=='li':
            if self.lists:
                kind,index,step,marker=self.lists[-1]
                try:index=int(attributes['value'])-step if 'value' in attributes else index
                except ValueError:pass
                index+=step;self.lists[-1]=(kind,index,step,marker)
                label=str(index)
                if marker in {'a','A'} and 0<index<100_000:
                    number=index;label=''
                    while number:number,part=divmod(number-1,26);label=chr(97+part)+label
                    if marker=='A':label=label.upper()
                elif marker in {'i','I'} and 0<index<4000:
                    number=index;label=''
                    for value,digit in ((1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')):
                        count,number=divmod(number,value);label+=digit*count
                    if marker=='i':label=label.lower()
                prefix=label+'. ' if kind=='ol' else {'circle':'◦ ','square':'▪ '}.get(marker,'• ')
                prior=self.pre;self.pre=True;self.emit('  '*(len(self.lists)-1)+prefix);self.pre=prior
            else:self.emit('• ')

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in {'br','hr','wbr','input'}:self.handle_endtag(tag)

    def handle_endtag(self,tag):
        if self.control_capture is not None:
            self.control_capture.end(tag)
            if self.control_capture.finished:self._finish_control()
            return
        if self.drop:
            if tag==self.drop[-1]:self.drop.pop()
            return
        if tag=='br':self.emit('\n');return
        if not self.interpret:
            if tag not in _RESOURCE and tag not in _DROP:self.emit('</'+tag+'>')
            return
        if self.style.display in {'block','table','table-row'}:self.line()
        if tag in {'ul','ol'} and self.lists:self.lists.pop()
        for index in range(len(self.stack)-1,-1,-1):
            if self.stack[index][0]==tag:
                _,self.style,self.shift,self.pre,self.hidden,self.alignment,self.width_limit=self.stack[index];del self.stack[index:];break

    def handle_data(self,data):
        if self.control_capture is not None:
            self.control_capture.data(data);return
        if not self.drop:
            if self.math_tokens:
                pattern='('+'|'.join(re.escape(token) for token in self.math_tokens)+')'
                for part in re.split(pattern,data):
                    formula=self.math_tokens.get(part)
                    if formula is None:self._text_data(part)
                    elif not self.hidden:
                        if self.math_loader is None:raise MermaidError('Math label measurement callback is missing',code='MATH_DEPENDENCY')
                        # KaTeX .katex font shorthand resets normal style/weight,
                        # scales1.21em and line-height1.2; tag CSS may override.
                        math_style=replace(self.style,font_size=self.style.font_size*1.21,font_weight='normal',font_style='normal',line_height=1.2,line_height_px=None)
                        if self.tag_style:math_style=self.tag_style('span',math_style,('katex',),self.style)
                        key,width,ascent,descent=self.math_loader(formula.tex,math_style,formula.position)
                        strut=self.style.line_height_px if self.style.line_height_px is not None else self.style.font_size*self.style.line_height
                        self.parts.append(Fragment('\ufffc',math_style,self.shift,False,self.alignment,math_key=key,math_width=width,math_ascent=ascent,math_descent=descent,min_line_height=strut))
                return
            self._text_data(data)

    def _text_data(self,data):
        if self.raw_html and not self.pre:
            # Direct DOM innerHTML uses CSS normal whitespace. Preserve
            # NBSP and preformatted spans; explicit br is emitted separately.
            data=re.sub(r'[ \t\r\n\f]+',' ',data)
        if not self.drop:
            if self.style.direction=='auto':
                strong=next((unicodedata.bidirectional(c) for c in data if unicodedata.bidirectional(c) in {'L','R','AL'}),'L')
                prior=self.style;self.style=replace(self.style,direction='rtl' if strong in {'R','AL'} else 'ltr')
                self.emit(data);self.style=prior
            else:self.emit(data)


def _inline_markdown(text: str, *, literal_html: bool, depth: int = 0, omissions: list[str] | None = None) -> str:
    if depth>128:raise MermaidError("Markdown nesting budget exceeded",code="LABEL_BUDGET")
    output=[];index=0
    while index<len(text):
        if text[index]=='\\' and index+1<len(text) and text[index+1] in r'\`*_{}[]()#+-.!>':
            output.append(html.escape(text[index+1]));index+=2;continue
        if text[index]=='<':
            match=re.match(r'</?[A-Za-z][^>]*>',text[index:])
            if match:
                raw=match[0];output.append(html.escape(raw) if literal_html else raw);index+=len(raw);continue
        if text[index]=='`':
            count=len(text[index:])-len(text[index:].lstrip('`'));marker='`'*count
            end=text.find(marker,index+count)
            if end>=0:
                if literal_html:
                    if omissions is not None:omissions.append('SOURCE_MARKDOWN_TOKEN_OMISSION:codespan')
                else:output.append(html.escape(text[index:end+count]))
                index=end+count;continue
        triple=next((marker for marker in ('***','___') if text.startswith(marker,index)),None)
        if triple:
            end=text.find(triple,index+3)
            if end>index+3:
                output.append('<strong><em>'+_inline_markdown(text[index+3:end],literal_html=literal_html,depth=depth+1,omissions=omissions)+'</em></strong>')
                index=end+3;continue
        marker=next((m for m in ('**','__','*','_') if text.startswith(m,index)),None)
        if marker and not (marker.startswith('_') and index and text[index-1].isalnum()):
            end=text.find(marker,index+len(marker))
            if end>index+len(marker) and not text[index+len(marker)].isspace():
                tag='strong' if len(marker)==2 else 'em'
                output.append(f'<{tag}>'+_inline_markdown(text[index+len(marker):end],literal_html=literal_html,depth=depth+1,omissions=omissions)+f'</{tag}>')
                index=end+len(marker);continue
        # Keep unsupported Markdown token source rather than silently deleting it.
        if text[index]=='[' or text.startswith('![',index):
            match=re.match(r'!?\[[^]\n]*\]\([^\n)]*\)',text[index:])
            if match:
                if literal_html:
                    if omissions is not None:omissions.append('SOURCE_MARKDOWN_TOKEN_OMISSION:'+('image' if match[0].startswith('!') else 'link'))
                else:output.append(html.escape(match[0]))
                index+=len(match[0]);continue
        if text[index]=='&':
            entity=re.match(r'&(?:#\d+|#x[0-9a-f]+|[a-z][a-z0-9]+);',text[index:],re.I)
            if entity:output.append(entity[0]);index+=len(entity[0]);continue
        output.append(html.escape(text[index]));index+=1
    return ''.join(output)


def prepare_label_markup(text: str, label_kind: str, config: FlowConfig):
    """Pure source preprocessing; usable for diagram-wide initial radio state."""
    text,math_tokens=protect_math(text) if config.html_labels else (text,{})
    # createText passes original input, not markdownToHTML, when hasKatex.
    if math_tokens:label_kind='text'
    has_controls=config.html_labels and bool(re.search(r'<(?:input|button|select|textarea|meter|progress|fieldset)\b',text,re.I))
    if has_controls:
        # Preserve the fixed utils.ts encodeEntities preprocessing quirk;
        # source-invalid inline CSS must not acquire different native meaning.
        text=re.sub(r'style.*:\S*#.*;',lambda match:match[0][:-1],text)
    if has_controls and label_kind=='text' and not math_tokens:
        # handle-markdown-text.ts nonMarkdownToHTML runs before innerHTML:
        # even textarea raw text and attributes receive literal <br /> tokens.
        text=re.sub(r'\\n|\n','<br />',text)
    # Equivalent to the source encodeEntities/decodeEntities placeholder pair;
    # HTMLParser then performs one actual HTML entity interpretation pass.
    text=re.sub(r'#(\w+);',lambda match:'&'+('#' if match[1].isdigit() else '')+match[1]+';',text)
    text=text.replace('ﬂ°°','&#').replace('ﬂ°','&').replace('¶ß',';')
    if has_controls:
        # This protection is native transport, after source entity decoding:
        # injected numeric newline entities must not acquire an extra '&'.
        def textarea_raw(match):
            content=match[2].replace('<','&lt;').replace('>','&gt;').replace('\n','&#10;').replace('\\n','&#92;n')
            return match[1]+content+match[3]
        text=re.sub(r'(<textarea\b[^>]*>)(.*?)(</textarea\s*>)',textarea_raw,text,flags=re.I|re.S)
    if config.html_labels:
        text=re.sub(r'\b(fa[bklrs]?):fa-([\w-]+)',lambda m:f'<i class="{m[1]} fa-{m[2]}"></i>',text)
    text=sanitize_markup(text,config)
    return text,label_kind,math_tokens,has_controls


def fragments(text: str, label_kind: str, config: FlowConfig, style: ResolvedStyle,
              *, tag_style=None, diagnostics: list[str] | None = None, asset_loader=None, svg_style=None, math_loader=None,
              _prepared=None, literal: bool = False, raw_html: bool = False) -> tuple[Fragment,...]:
    if literal:
        # Direct SVG .text()/Canvas textContent consumers own their whitespace
        # normalization. Bypass Mermaid rich markup/entity/\\n preprocessing.
        return (Fragment(text,replace(style,white_space='pre'),preserve_space=True),)
    if raw_html:
        # A direct source .html() consumer does not run Mermaid flow-label
        # backslash/entity/math preprocessing. Reuse sanitized native HTML
        # layout while keeping literal data and real HTML whitespace.
        text=_inline_svgs(sanitize_markup(text,config),style,svg_style)
        parser=_HTML(style,interpret=True,tag_style=tag_style,asset_loader=asset_loader,
                     image_only=not re.sub(r'<[^>]*>|\s+','',text),raw_html=True)
        parser.ol_sizes=iter(_ordered_list_sizes(text));parser.feed(text);parser.close()
        if parser.control_capture is not None:parser._finish_control()
        return tuple(parser.parts) or (Fragment('',style),)
    text,label_kind,math_tokens,has_controls=_prepared if _prepared is not None else prepare_label_markup(text,label_kind,config)
    if has_controls and _prepared is None:
        from .controls.semantic import normalize_control_markup
        text=normalize_control_markup(text)
    if config.html_labels:text=_inline_svgs(text,style,svg_style)
    image_only=not re.sub(r'<[^>]*>|\s+','',text)
    # Both source branches recognize malformed-but-common </br> as a break.
    text=re.sub(r'<\/?br\s*\/?>','\n',text,flags=re.I).replace('\\n','\n')
    if label_kind=='markdown':
        if not config.html_labels:
            text=re.sub(r'\n{2,}','\n',textwrap.dedent(text))
        rendered=[];fence=''
        for line in text.split('\n'):
            opening=re.match(r'\s*(`{3,}|~{3,})',line)
            if fence:
                rendered.append(html.escape(line))
                if opening and opening[1].startswith(fence[0]) and len(opening[1])>=len(fence):fence=''
                continue
            if opening:
                fence=opening[1];rendered.append(html.escape(line));continue
            # Source handlers return unknown block tokens as raw source text.
            if re.match(r'\s*(?:#{1,6}\s|>\s|[-+*]\s|\d+\.\s|```|~~~|\|)',line):rendered.append(html.escape(line))
            else:rendered.append(_inline_markdown(line,literal_html=not config.html_labels,omissions=diagnostics))
        text='<br/>'.join(rendered)
        parser=_HTML(style,interpret=True,tag_style=tag_style,svg_text=not config.html_labels,asset_loader=asset_loader,image_only=image_only,math_loader=math_loader,math_tokens=math_tokens)
    elif label_kind=='text':
        if not config.html_labels:
            # nonMarkdownToLines tokenizes tags separately; the SVG tspan
            # writer adds one space before every word after the first.
            text='\n'.join(' '.join(re.findall(r'<[^>]+>|[^\s<>]+',line.strip())) for line in text.split('\n'))
        parser=_HTML(style,interpret=config.html_labels,tag_style=tag_style,svg_text=not config.html_labels,asset_loader=asset_loader,image_only=image_only,math_loader=math_loader,math_tokens=math_tokens)
    else:raise MermaidError(f'Unknown label kind {label_kind!r}',code='INVALID_LABEL')
    parser.ol_sizes=iter(_ordered_list_sizes(text));parser.feed(text);parser.close()
    if parser.control_capture is not None:parser._finish_control()
    parts=parser.parts
    if len(parts)>1 and parts[-1].text in ('','\n') and parts[-2].control and parts[-2].style.display in {'block','table','table-row'}:
        parts.pop()
    # Container-generated paragraph delimiters do not add empty outer rows.
    if parts and parts[-1].text.endswith('\n') and re.search(r'(?:</(?:p|div|section|li|ol|ul|pre|h[1-6]|tr|table)>|<img[^>]*>)\s*$',text,re.I):
        parts[-1]=replace(parts[-1],text=parts[-1].text.rstrip('\n'))
    if not parts:return (Fragment('',style),)
    if label_kind=='markdown' and config.html_labels and not config.markdown_auto_wrap:
        parts=[replace(part,preserve_space=True) for part in parts]
    return tuple(parts)


def _number(metrics: Any,name: str) -> float:
    value=getattr(metrics,name,0)
    if not isinstance(value,(int,float)) or not math.isfinite(value):
        raise MermaidError(f'Invalid Canvas metric {name}',code='INVALID_MEASUREMENT')
    return float(value)


def measure_label(text: str, label_kind: str, config: FlowConfig, style: ResolvedStyle,
                  measure: Callable[[str,ResolvedStyle],Any], *, width: float = math.inf,
                  min_width: float = 0, tag_style=None, diagnostics: list[str] | None = None, asset_loader=None, svg_style=None, math_loader=None,
                  _control_depth: int = 0, _prepared=None, literal: bool = False, raw_html: bool = False) -> tuple[float,float,tuple[MeasuredLine,...],tuple[MeasuredTextRun,...]]:
    """Lay out styled runs using real injected Canvas measurements only."""
    if _control_depth>64:raise MermaidError('Control nesting budget exceeded',code='LABEL_BUDGET')
    pieces=fragments(text,label_kind,config,style,tag_style=tag_style,diagnostics=diagnostics,asset_loader=asset_loader,svg_style=svg_style,math_loader=math_loader,_prepared=_prepared,literal=literal,raw_html=raw_html)
    transformed=[]
    for part in pieces:
        if part.style.hyphens=='auto':raise MermaidError('hyphens:auto requires a language hyphenation dictionary',code='UNSUPPORTED_THEME_CSS')
        text=part.text
        if part.control is not None:
            from .controls.layout import layout_control
            def content_layout(markup,content_style,content_width):
                # Initial state was normalized in the complete outer label
                # (or diagram). Do not regroup radios after stripping a form
                # or fieldset wrapper for nested rich-content measurement.
                prepared=prepare_label_markup(markup,'text',config)
                return measure_label(markup,'text',config,content_style,measure,width=content_width,
                    tag_style=tag_style,diagnostics=diagnostics,asset_loader=asset_loader,svg_style=svg_style,math_loader=math_loader,_control_depth=_control_depth+1,_prepared=prepared)
            control=layout_control(part.control,part.style,measure,content_layout=content_layout,asset_loader=asset_loader,
                containing_width=width if math.isfinite(width) else None)
            part=replace(part,control_layout=control)
        if not part.asset_id and not part.math_key and not part.control:
            if part.style.text_transform=='uppercase':text=text.upper()
            elif part.style.text_transform=='lowercase':text=text.lower()
            elif part.style.text_transform=='capitalize':text=re.sub(r'\b\w',lambda m:m[0].upper(),text)
            if part.style.hyphens=='none':text=text.replace('\u00ad','')
        transformed.append(replace(part,text=text))
    # renderKatexUnsanitized wraps a math-containing source line in a centered
    # nowrap flex row. Keep ordinary lines on the existing wrapping branch.
    math_lines=set();line_index=0
    for part in transformed:
        if part.math_key:math_lines.add(line_index)
        line_index+=part.text.count('\n')
    if math_lines:
        split=[];line_index=0
        for part in transformed:
            chunks=part.text.split('\n')
            for index,chunk in enumerate(chunks):
                current=replace(part,text=chunk)
                if line_index in math_lines:current=replace(current,style=replace(current.style,white_space='nowrap'),alignment='center')
                if chunk:split.append(current)
                if index<len(chunks)-1:
                    split.append(replace(part,text='\n'));line_index+=1
        pieces=tuple(split) if split else tuple(transformed)
    else:pieces=tuple(transformed)
    rows: list[list[Fragment]]=[[]]
    row_width=0.0
    wrap=not(label_kind=='markdown' and not config.markdown_auto_wrap and config.html_labels)

    def metrics_for(fragment,text=None):
        if fragment.control_layout is not None:
            from types import SimpleNamespace
            control=fragment.control_layout
            baseline=control.baseline
            from .controls.layout import parse_control_declarations
            alignment=dict((name,value) for name,value,_ in parse_control_declarations(control.spec.attr('style'))).get('vertical-align','baseline')
            if alignment=='middle':
                reference=measure('x',fragment.control_parent_style or style)
                baseline=control.height/2+max(0,_number(reference,'actualBoundingBoxAscent'))/2
            return SimpleNamespace(width=control.width,actualBoundingBoxLeft=0,actualBoundingBoxRight=control.width,
                actualBoundingBoxAscent=baseline,actualBoundingBoxDescent=control.height-baseline)
        if fragment.math_key:
            from types import SimpleNamespace
            return SimpleNamespace(width=fragment.math_width,actualBoundingBoxLeft=0,actualBoundingBoxRight=fragment.math_width,actualBoundingBoxAscent=fragment.math_ascent,actualBoundingBoxDescent=fragment.math_descent)
        if fragment.asset_id:
            from types import SimpleNamespace
            return SimpleNamespace(width=fragment.asset_width,actualBoundingBoxLeft=0,actualBoundingBoxRight=fragment.asset_width,actualBoundingBoxAscent=fragment.asset_height,actualBoundingBoxDescent=0)
        return measure(fragment.text if text is None else text,fragment.style)

    def append(fragment):
        nonlocal row_width
        if rows[-1] and not fragment.asset_id and not fragment.math_key and not fragment.control and not rows[-1][-1].asset_id and not rows[-1][-1].math_key and not rows[-1][-1].control and rows[-1][-1].style==fragment.style and rows[-1][-1].shift==fragment.shift and rows[-1][-1].preserve_space==fragment.preserve_space and rows[-1][-1].alignment==fragment.alignment:
            prior=rows[-1][-1]
            old=_number(metrics_for(prior),'width')
            rows[-1][-1]=replace(prior,text=prior.text+fragment.text)
            row_width+=_number(metrics_for(rows[-1][-1]),'width')-old
        else:
            rows[-1].append(fragment);row_width+=_number(metrics_for(fragment),'width')

    for part in pieces:
        part_width=min(width,part.width_limit) if part.width_limit is not None else width
        text_part=part.text
        if not part.preserve_space:text_part=re.sub(r'[ \t\r\f]+' if raw_html else r'[^\S\n]+',' ',text_part)
        nowrap=part.style.white_space in {'nowrap','pre'}
        # HTML NBSP is preserved and stays inside an unbreakable word.
        tokens=[text_part] if part.control else re.findall(r'\n|[ \t\r\f]+|[^ \t\r\n\f]+' if raw_html else r'\n|[^\S\n]+|[^\s]+',text_part)
        expanded=[]
        for token in tokens:
            if not part.control and ((part.style.word_break=='break-all' or part.style.overflow_wrap=='anywhere') or (part.style.word_break!='keep-all' and any(unicodedata.east_asian_width(c) in {'W','F'} for c in token))) and token!='\n':expanded.extend(token)
            elif '\u00ad' in token:expanded.extend(value for value in re.split('(\u00ad)',token) if value)
            else:expanded.append(token)
        discretionary=False
        for token in expanded:
            if token=='\u00ad':discretionary=True;continue
            if token=='\n':rows.append([]);row_width=0;continue
            if raw_html and not part.preserve_space and not rows[-1] and re.fullmatch(r'[ \t\r\f]+',token):continue
            if token.isspace() and not part.preserve_space and rows[-1] and rows[-1][-1].text.endswith((' ','\t')):
                continue
            metrics=metrics_for(part,token);advance=_number(metrics,'width')
            if wrap and not nowrap and rows[-1] and row_width+advance>part_width and not token.isspace():
                if discretionary:append(replace(part,text='-'))
                rows.append([]);row_width=0
            discretionary=False
            if wrap and not part.asset_id and not part.math_key and not part.control and (not config.html_labels or part.style.overflow_wrap=='break-word') and advance>part_width and not nowrap:
                for char in token:
                    char_width=_number(measure(char,part.style),'width')
                    if rows[-1] and row_width+char_width>part_width:rows.append([]);row_width=0
                    append(replace(part,text=char))
            else:append(replace(part,text=token))
    if raw_html:
        # CSS normal collapsible spaces do not occupy line edges. A final
        # normal-flow br/block separator ends the last line; it does not
        # introduce an extra empty line after that containing block.
        for row in rows:
            for edge in (0,-1):
                while row:
                    part=row[edge]
                    if part.preserve_space or part.asset_id or part.math_key or part.control:break
                    value=part.text.lstrip(' \t\r\f') if edge==0 else part.text.rstrip(' \t\r\f')
                    if value:row[edge]=replace(part,text=value);break
                    row.pop(edge)
        if len(rows)>1 and not rows[-1] and pieces and not pieces[-1].preserve_space:rows.pop()
    measured=[]
    for row in rows:
        if not row:row=[Fragment('',style)]
        pen=0.;left=0.;right=0.;ascent=descent=0.;data=[]
        for part in row:
            metrics=metrics_for(part)
            advance=max(0,_number(metrics,'width'));ink_left=_number(metrics,'actualBoundingBoxLeft');ink_right=_number(metrics,'actualBoundingBoxRight')
            if part.math_key:a=_number(metrics,'actualBoundingBoxAscent');d=_number(metrics,'actualBoundingBoxDescent')
            else:a=max(0,_number(metrics,'actualBoundingBoxAscent'));d=max(0,_number(metrics,'actualBoundingBoxDescent'))
            if a+d==0:a=max(0,_number(metrics,'fontBoundingBoxAscent'));d=max(0,_number(metrics,'fontBoundingBoxDescent'))
            left=min(left,pen-ink_left);right=max(right,pen+ink_right,pen+advance)
            ascent=max(ascent,a+part.shift);descent=max(descent,d-part.shift)
            data.append((part,pen,advance,a,d,ink_left,ink_right));pen+=advance
        row_height=max(ascent+descent,*(part.min_line_height for part in row),*((part.style.line_height_px if part.style.line_height_px is not None
                                       else part.style.font_size*part.style.line_height) if config.html_labels
                                      else part.style.font_size*1.1 for part in row))
        measured.append((data,left,right,ascent,descent,row_height))
    nonempty=any(part.text for part in pieces)
    label_width=max(min_width if nonempty else 0,*(right-left for _,left,right,_,_,_ in measured))
    # Direct HTML is laid out in its fixed foreignObject containing block.
    # Keep its width so centered headings and left-aligned block code share
    # the source inner box rather than centering a tight content bbox.
    if raw_html and math.isfinite(width):label_width=max(label_width,width)
    runs=[];lines=[];top=0.
    for data,left,right,ascent,descent,row_height in measured:
        row_width=right-left
        align=(data[0][0].alignment or style.text_align) if config.html_labels else {'middle':'center','start':'left','end':'right'}[style.text_anchor]
        offset=(label_width-row_width)/2 if align=='center' else label_width-row_width if align in {'right','end'} else 0
        baseline=top+(row_height-ascent-descent)/2+ascent
        text_line=''
        for part,pen,advance,a,d,ink_left,ink_right in data:
            s=part.style;text_line+=part.text
            run_baseline=baseline-part.shift
            if part.control_layout is not None:
                from .controls.layout import parse_control_declarations
                alignment=dict((name,value) for name,value,_ in parse_control_declarations(part.control.attr('style'))).get('vertical-align','baseline')
                control=part.control_layout
                if alignment=='top':run_baseline=top+control.baseline
                elif alignment=='bottom':run_baseline=top+row_height-control.height+control.baseline
                elif alignment in {'text-top','text-bottom'}:
                    reference=measure('M',part.control_parent_style or style)
                    run_baseline=baseline-_number(reference,'fontBoundingBoxAscent')+control.baseline if alignment=='text-top' else baseline+_number(reference,'fontBoundingBoxDescent')-control.height+control.baseline
                else:run_baseline+=control.baseline-a
            runs.append(MeasuredTextRun(part.text,offset+pen-left,run_baseline,advance,a,d,
                                        s.font_family.rstrip().removesuffix(';').rstrip(),s.font_size,s.font_weight,s.font_style,s.text_color,
                                        s.decoration,s.background if config.html_labels else '',ink_left,ink_right,
                                        opacity=(s.opacity if part.control else s.paint_opacity)*(s.fill_opacity if not config.html_labels else 1),direction=s.direction,kind='control' if part.control else 'math' if part.math_key else part.asset_kind if part.asset_id else 'text',asset_id=part.asset_id,
                                        asset_box=Box(offset+pen-left,baseline-part.shift-a,advance,a+d) if part.asset_id else None,
                                        letter_spacing=s.letter_spacing,word_spacing=s.word_spacing,text_shadows=s.text_shadows,math_key=part.math_key,
                                        blend_mode=s.blend_mode,text_stroke_color=s.text_stroke_color,text_stroke_width=s.text_stroke_width,
                                        brightness=s.brightness,filter_chain=s.filter_chain,
                                        filter_shadow=(s.shadow_dx,s.shadow_dy,s.shadow_blur) if s.filter_chain and s.shadow_opacity else None,
                                        control=part.control_layout))
        lines.append(MeasuredLine(text_line,row_width,ascent,descent));top+=row_height
    return label_width,top,tuple(lines),tuple(runs)
