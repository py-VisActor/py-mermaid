"""Pure fixed Khroma 2.1.0 channel operations for Mermaid themes.

HSL input retains its authored hue/saturation even at white, black or zero
saturation. Public channels() remains normalized RGBA for Canvas consumers.
"""
from __future__ import annotations
import math
import re
from py_mermaid.model.flowchart import MermaidError
from .color_names import COLOR_NAMES


def _clamp(number, lo=0.0, hi=1.0):
    number=float(number)
    return hi if number >= hi else lo if number < lo else number


def _parse(color):
    if not isinstance(color,str):
        raise MermaidError("Theme colors must be strings",code="INVALID_COLOR")
    value=color.strip().lower()
    value=COLOR_NAMES.get(value,value)
    if value=='transparent':return dict(r=0.,g=0.,b=0.,a=0.)
    if re.fullmatch(r"#[0-9a-f]{3,4}",value):value='#'+''.join(c*2 for c in value[1:])
    if re.fullmatch(r"#[0-9a-f]{6}(?:[0-9a-f]{2})?",value):
        nums=[int(value[i:i+2],16) for i in range(1,len(value),2)]
        return dict(zip(('r','g','b','a'),nums[:3]+[nums[3]/255 if len(nums)==4 else 1.]))
    match=re.fullmatch(r"(rgba?|hsla?)\((.*)\)",value)
    if match:
        parts=[p for p in re.split(r"[,\s/]+",match[2].strip()) if p]
        if len(parts) not in (3,4):raise MermaidError(f"Invalid CSS color {color!r}",code="INVALID_COLOR")
        try:
            alpha=_clamp(float(parts[3][:-1])/100 if parts[3].endswith('%') else float(parts[3])) if len(parts)==4 else 1.
            if match[1].startswith('rgb'):
                rgb=[_clamp(float(p[:-1])*2.55 if p.endswith('%') else float(p),0,255) for p in parts[:3]]
                return dict(zip(('r','g','b','a'),rgb+[alpha]))
            hue=parts[0];factor=1.
            for suffix,multiplier in (('turn',360),('grad',.9),('rad',180/math.pi),('deg',1)):
                if hue.endswith(suffix):hue,factor=hue[:-len(suffix)],multiplier;break
            return dict(h=math.fmod(float(hue)*factor,360),s=_clamp(float(parts[1].rstrip('%')),0,100),l=_clamp(float(parts[2].rstrip('%')),0,100),a=alpha)
        except (ValueError,OverflowError) as exc:
            raise MermaidError(f"Invalid CSS color {color!r}",code="INVALID_COLOR") from exc
    raise MermaidError(f"Unsupported CSS color {color!r}",code="INVALID_COLOR")


def _rgb(data):
    if 'r' in data:return data['r'],data['g'],data['b']
    h,s,l=data['h'],data['s'],data['l']
    if not s:return (l*2.55,)*3
    h/=360;s/=100;l/=100
    q=l*(1+s) if l<.5 else (l+s)-(l*s);p=2*l-q
    def hue(t):
        if t<0:t+=1
        if t>1:t-=1
        if t<1/6:return p+(q-p)*6*t
        if t<1/2:return q
        if t<2/3:return p+(q-p)*(2/3-t)*6
        return p
    return tuple(hue(t)*255 for t in (h+1/3,h,h-1/3))


def _hsl(data):
    if 'h' in data:return data['h'],data['s'],data['l']
    r,g,b=(v/255 for v in _rgb(data));high=max(r,g,b);low=min(r,g,b);l=(high+low)/2
    if high==low:return 0.,0.,l*100
    d=high-low;s=d/(2-high-low) if l>.5 else d/(high+low)
    h=((g-b)/d+(6 if g<b else 0)) if high==r else ((b-r)/d+2) if high==g else ((r-g)/d+4)
    return h*60,s*100,l*100


def channels(color):
    data=_parse(color)
    return *tuple(v/255 for v in _rgb(data)),data['a']


def _number(value):
    value=float(value)
    if math.isnan(value):return 'NaN'
    if math.isinf(value):return 'Infinity' if value>0 else '-Infinity'
    value=math.floor(value*10000000000+.5)/10000000000
    return f'{value:.10f}'.rstrip('0').rstrip('.') or '0'


def _raw_number(value):
    return str(int(value)) if float(value).is_integer() else str(value)


def _unchanged(color):
    # Keyword.parse delegates to Hex.parse and thus remembers canonical hex.
    value=color.lower()
    return '#00000000' if value=='transparent' else COLOR_NAMES.get(value,color)


def _stringify(data,space):
    alpha=data['a']
    if space=='hsl':
        h,s,l=_hsl(data)
        return f"hsla({_number(h)}, {_number(s)}%, {_number(l)}%, {_raw_number(alpha)})" if alpha<1 else f"hsl({_number(h)}, {_number(s)}%, {_number(l)}%)"
    rgb=_rgb(data)
    if alpha<1:return 'rgba('+', '.join(_number(v) for v in (*rgb,alpha))+')'
    if not all(float(v).is_integer() for v in rgb):return 'rgb('+', '.join(_number(v) for v in rgb)+')'
    return '#'+''.join(f'{int(v):02x}' for v in rgb)


def rgba(red,green,blue=0,alpha=1):
    if not isinstance(red,(int,float)):
        data=_parse(red);data['a']=_clamp(green)
        return _stringify(data,'hsl' if 'h' in data else 'rgb')
    return _stringify(dict(r=_clamp(red,0,255),g=_clamp(green,0,255),b=_clamp(blue,0,255),a=_clamp(alpha)),'rgb')


def adjust(color,changes):
    data=_parse(color);active={key:delta for key,delta in changes.items() if truthy(delta)}
    if not active:return _unchanged(color)
    rgb=any(c in active for c in 'rgb');hsl=any(c in active for c in 'hsl')
    if rgb and hsl:raise MermaidError('Cannot change both RGB and HSL channels at the same time',code='INVALID_COLOR')
    space='hsl' if hsl or not rgb and 'h' in data else 'rgb'
    axes=dict(zip('hsl',_hsl(data))) if space=='hsl' else dict(zip('rgb',_rgb(data)))
    axes['a']=data['a']
    for key,delta in active.items():
        if key not in axes:raise MermaidError('Unsupported color channel '+str(key),code='INVALID_COLOR')
        axes[key]=math.fmod(axes[key]+delta,360) if key=='h' else _clamp(axes[key]+delta,0,1 if key=='a' else 255 if key in 'rgb' else 100)
    return _stringify(axes,space)


_OMITTED=object()

def lighten(color,amount=_OMITTED):
    data=_parse(color);h,s,l=_hsl(data);next_l=float('nan') if amount is _OMITTED else _clamp(l+amount,0,100)
    if l==next_l:return _unchanged(color)
    return _stringify(dict(h=h,s=s,l=next_l,a=data['a']),'hsl')


def darken(color,amount=_OMITTED):
    return lighten(color) if amount is _OMITTED else lighten(color,-amount)


def invert(color):
    data=_parse(color)
    return _stringify(dict(zip('rgba',[255-v for v in _rgb(data)]+[data['a']])),'rgb')


def isDark(color):
    data=_parse(color)
    def linear(c):
        n=c/255
        return ((n+.055)/1.055)**2.4 if c>.03928 else n/12.92
    luminance=sum(coefficient*linear(c) for coefficient,c in zip((.2126,.7152,.0722),_rgb(data)))
    return math.floor(luminance*10000000000+.5)/10000000000<.5


def mkBorder(color,dark_mode=False):
    return adjust(color,{'s':-40,'l':10 if dark_mode else -10})


def truthy(value):
    if isinstance(value,float) and math.isnan(value):return False
    return isinstance(value,(dict,list,tuple,set,frozenset)) or bool(value)
