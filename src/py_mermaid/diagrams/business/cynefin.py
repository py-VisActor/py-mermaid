"""Cynefin grammar, DB reduction and dedicated source geometry."""
from dataclasses import dataclass
import math
import re
from ...runtime.common import make_diagram,config_dict,error
from ._cynefin_geometry import boundary,cliff,confusion,hash_string

NAMES=('complex','complicated','clear','chaotic','confusion')
META={'complex':('Probe \u2192 Sense \u2192 Respond','Emergent Practices'),'complicated':('Sense \u2192 Analyse \u2192 Respond','Good Practices'),'clear':('Sense \u2192 Categorise \u2192 Respond','Best Practices'),'chaotic':('Act \u2192 Sense \u2192 Respond','Novel Practices'),'confusion':('','Disorder')}


def _svg_display_text(text):
    # cynefinRenderer writes plain SVG text with default normal whitespace.
    # Normalize only XML ASCII whitespace for display/measurement; the model
    # retains source values, including LF/TAB and non-ASCII whitespace.
    return re.sub(r'[ \t\r\n]+', ' ', text).strip(' ')


def _metadata(text,meta):
    # common.langium terminals stop single-line values at %% before the
    # CommonValueConverter trims/collapses them; multiline values retain %%.
    match=re.fullmatch(r'title(?:[\t ](.*)|)|(accTitle)[\t ]*:(.*)|accDescr(?:[\t ]*:(.*)|\s*\{([^}]*)\})',text,re.S)
    if not match:return False
    if text.startswith('title'):key='title';value=match[1] or ''
    elif match[2]:key='acctitle';value=match[3]
    else:key='accdescr';value=match[4] if match[4] is not None else match[5]
    if match[5] is not None:
        value=re.sub(r'^\s*','',value,flags=re.M)
        value=re.sub(r'\s+$','',value,flags=re.M)
        value=re.sub(r'[\t ]{2,}',' ',value)
        value=re.sub(r'[\n\r]{2,}','\n',value)
    else:value=re.sub(r'[\t ]{2,}',' ',value.split('%%',1)[0].strip())
    meta[key]=value
    return True

@dataclass(frozen=True)
class Cynefin:
    domains:tuple
    transitions:tuple
    title:str=''
    accessibility:tuple=()

def parse(document,config):
    # Langium STRING terminals and domain blocks retain quoted newlines and
    # punctuation; domain names within a string never terminate a block.
    s=document.cleaned;pos=0;tokens=[]
    pattern=re.compile(r'accDescr\s*\{[^}]*\}|(?:title(?:[ \t]+|(?=\r?\n|$))|accTitle\s*:|accDescr\s*:)[^\r\n]*|\s+|%%[^\n]*|"(?:\\.|[^"\\])*"|\'(?:(?:\\.)|[^\'\\])*\'|-->|[^\s:"\']+|:')
    for m in pattern.finditer(s):
        if m.start()!=pos:raise error(document,pos,'Invalid Cynefin token')
        pos=m.end();v=m[0]
        if v.isspace() or v.startswith('%%'):continue
        tokens.append((v,m.start()))
    if pos!=len(s):raise error(document,pos,'Invalid Cynefin token')
    if not tokens or tokens[0][0] not in ('cynefin-beta','cynefin-beta:'):raise error(document,0,'Expected cynefin-beta')
    i=1
    if i<len(tokens) and tokens[i][0]==':':i+=1
    blocks={};trans=[];diagnostics=[];meta={'title':document.title or ''}
    def string(v,at):
        if len(v)<2 or v[0] not in '\"\'':raise error(document,at,'Expected quoted label')
        # Langium convertString is a one-character escape converter, not JSON:
        # \u0041 becomes u0041, unknown escapes drop only the backslash, and
        # both quote styles permit literal newlines in their terminal.
        escapes={'b':'\b','f':'\f','n':'\n','r':'\r','t':'\t','v':'\v','0':'\0'}
        return re.sub(r'\\(.)',lambda m:escapes.get(m[1],m[1]),v[1:-1],flags=re.S)
    while i<len(tokens):
        v,at=tokens[i]
        if _metadata(v,meta):i+=1;continue
        if v in ('title','accTitle','accDescr'):
            end=s.find('\n',at)
            if end<0:end=len(s)
            raw=s[at:end]
            if not _metadata(raw,meta):raise error(document,at,'Invalid metadata')
            i+=1
            while i<len(tokens) and tokens[i][1]<end:i+=1
            continue
        if v not in NAMES:raise error(document,at,'Expected Cynefin domain')
        i+=1
        if i<len(tokens) and tokens[i][0]=='-->':
            i+=1
            if i>=len(tokens) or tokens[i][0] not in NAMES:raise error(document,at,'Expected transition domain')
            target=tokens[i][0];i+=1;label=''
            if i<len(tokens) and tokens[i][0]==':':
                i+=1
                if i>=len(tokens):raise error(document,at,'Missing transition label')
                label=string(*tokens[i]);i+=1
            if target==v:diagnostics.append(f'Cynefin: self-loop transition on domain "{v}" skipped')
            else:trans.append((v,target,label))
            end=tokens[i-1][1]+len(tokens[i-1][0]);next_at=tokens[i][1] if i<len(tokens) else len(s)
            if i<len(tokens) and '\n' not in s[end:next_at]:raise error(document,end,'Transition must end at a newline')
        else:
            items=[]
            while i<len(tokens) and tokens[i][0][0] in '\"\'':items.append(string(*tokens[i]));i+=1
            blocks[v]=tuple(items)
    return make_diagram('cynefin',document,config,Cynefin(tuple(blocks.items()),tuple(trans),meta['title'],tuple(meta.items())),tuple(diagnostics))

async def build(diagram,p):
    c=config_dict(diagram);cfg=c['cynefin'];t=c['themeVariables']['cynefin'];m=diagram.model
    from ._source_styles import styles
    p.add_styles(styles('cynefin',t))
    w=float(cfg['width']);h=float(cfg['height']);pad=float(cfg['padding']);show=cfg['showDomainDescriptions']
    configured_seed=cfg.get('seed',0)
    # resolveSeed accepts only nonzero finite JS numbers. In particular bool
    # is not numeric here, despite Python bool being an int subclass.
    seed=configured_seed if type(configured_seed) in (int,float) and math.isfinite(configured_seed) and configured_seed!=0 else hash_string(p.render_id)
    # The browser source hashes its host element id when seed=0. Native has no
    # DOM element id; Painter.render_id is the native host's explicit identity.
    layouts={'complex':(0,0,w/4,h/4),'complicated':(w/2,0,w*.75,h/4),'chaotic':(0,h/2,w/4,h*.75),'clear':(w/2,h/2,w*.75,h*.75),'confusion':(w*.35,h*.35,w/2,h/2)}
    def style(cls,tag='path',**base):return p.style(cls,tag=tag,base=base)
    def label(text,x,y,cls,size,color,weight='normal',italic=False,baseline=False):
        st=style(cls,'text',font_size=size,text_color=color,font_weight=weight,font_style='italic' if italic else 'normal')
        text=_svg_display_text(text)
        box=p.measure(text,html=False,style=st,literal=True)
        p.text(box,x+pad,y+pad-(box.ascent if baseline else box.height/2),align='center',style=st)
    for name in ('complex','complicated','chaotic','clear'):
        x,y,_,_=layouts[name];p.rect(x+pad,y+pad,w/2,h/2,style=style('cynefinDomain','rect',fill=t[name+'Bg'],fill_opacity=.4,stroke='none'))
    transform=(1,0,0,1,pad,pad)
    for d,cls,color,width,dash in ((boundary(w,h,seed,cfg.get('boundaryAmplitude')),'cynefinBoundary',t['boundaryColor'],t['boundaryWidth'],(6,3)),(boundary(w,h,seed+100,cfg.get('boundaryAmplitude'),True),'cynefinBoundary',t['boundaryColor'],t['boundaryWidth'],(6,3)),(cliff(w,h),'cynefinCliff',t['cliffColor'],t['cliffWidth'],())):
        p.path(d,transform=transform,style=style(cls,fill='none',stroke=color,stroke_width=width,dash=dash))
    p.path(confusion(w,h),transform=transform,style=style('cynefinConfusion',fill=t['confusionBg'],fill_opacity=.5,stroke=t['boundaryColor'],stroke_width=1.5,dash=(4,2)))
    for name,(_,_,x,y) in layouts.items():
        center=name=='confusion'
        label(name.title(),x,y-((10 if center else 30) if show else 0),'cynefinDomainLabel',t['domainFontSize'],t['labelColor'],'bold')
        if show:
            if not center:label(META[name][0],x,y-10,'cynefinSubtitle',t['itemFontSize']-1,t['textColor'],italic=True)
            label(META[name][1],x,y+(8 if center else 5),'cynefinSubtitle',t['itemFontSize']-1,t['textColor'],italic=True)
    for name,items in m.domains:
        _,_,x,y=layouts[name];center=name=='confusion';shown=items[:3] if center else items
        labels=list(shown)
        if center and len(items)>3:labels.append(f'+{len(items)-3} more')
        start=y+((22 if show else 14) if center else (25 if show else 15))
        for index,text in enumerate(labels):
            st=style('cynefinItemText','text',font_size=t['itemFontSize'],text_color=t['textColor'])
            text=_svg_display_text(text)
            box=p.measure(text,html=False,style=st,literal=True);bw=box.width+20;by=start+index*30;overflow=index>=len(shown)
            p.rect(x-bw/2+pad,by+pad,bw,26,radius=4,style=style('cynefinItemOverflow' if overflow else 'cynefinItem','rect',fill=t[name+'Bg'],fill_opacity=.6 if overflow else .95,stroke=t['boundaryColor'],stroke_width=1,dash=(3,2) if overflow else ()))
            p.text(box,x+pad,by+pad+13-box.height/2,align='center',style=st)
    for a,b,text in m.transitions:
        x,y=layouts[a][2:];u,v=layouts[b][2:];dx=u-x;dy=v-y;cx=(x+u)/2-dy*.15;cy=(y+v)/2+dx*.15
        st=style('cynefinArrowLine',fill='none',stroke=t['arrowColor'],stroke_width=t['arrowWidth'])
        p.path(f'M{x+pad},{y+pad} Q{cx+pad},{cy+pad} {u+pad},{v+pad}',style=st)
        p.marker(u+pad,v+pad,u-cx,v-cy,color=st.stroke,size=6)
        if text:label(text,cx,cy-6,'cynefinArrowLabel',t['itemFontSize']-1,t['textColor'],baseline=True)
    if m.title:label(m.title,w/2,-pad/2,'cynefinTitle',t['domainFontSize']+2,t['labelColor'],'bold')
    return p.finish(width=w+2*pad,height=h+2*pad,padding=0,diagnostics=diagram.diagnostics)
