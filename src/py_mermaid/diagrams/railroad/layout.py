"""Pure recursive railroad dimensions and source arc/bypass/repetition geometry."""
from dataclasses import dataclass
import math,re
from py_mermaid.runtime.common import config_dict


DEFAULTS=dict(compactMode=True,padding=10,verticalSeparation=8,horizontalSeparation=10,arcRadius=10,
 fontSize=14,fontFamily='monospace',terminalFill='#FFFFC0',terminalStroke='#000000',terminalTextColor='#000000',
 nonTerminalFill='#FFFFFF',nonTerminalStroke='#000000',nonTerminalTextColor='#000000',lineColor='#000000',strokeWidth=2,
 markerFill='#000000',commentFill='#E8E8E8',commentStroke='#888888',commentTextColor='#666666',
 specialFill='#F0E0FF',specialStroke='#8800CC',ruleNameColor='#000066',showMarkers=True,markerRadius=5)


@dataclass(frozen=True)
class Geometry:
    expression: object
    width: float
    height: float
    up: float
    down: float
    children: tuple = ()
    label: object = None


def _style(config):
    tv=config.get('themeVariables',{}) or {};result=dict(DEFAULTS)
    mapping={'terminalFill':('secondBkg','secondaryColor'),'terminalStroke':('secondaryBorderColor','lineColor'),
     'terminalTextColor':('secondaryTextColor','textColor'),'nonTerminalFill':('mainBkg','background'),
     'nonTerminalStroke':('primaryBorderColor','lineColor'),'nonTerminalTextColor':('primaryTextColor','textColor'),
     'lineColor':('lineColor',),'markerFill':('lineColor',),'commentFill':('labelBackground','tertiaryColor'),
     'commentStroke':('tertiaryBorderColor','lineColor'),'commentTextColor':('tertiaryTextColor','textColor'),
     'specialFill':('tertiaryColor','secondaryColor'),'specialStroke':('tertiaryBorderColor','secondaryBorderColor'),
     'ruleNameColor':('titleColor','textColor'),'fontFamily':('fontFamily',),'fontSize':('fontSize',)}
    for key,keys in mapping.items():
        for source in keys:
            if tv.get(source) is not None:result[key]=tv[source];break
    result.update(config.get('railroad',{}) or {})
    color_pattern=r'^#(?:[\da-f]{3,4}|[\da-f]{6}|[\da-f]{8})$|^(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch)\([\d\s%+,./-]+\)$|^[a-z]+$'
    for key,value in tuple(result.items()):
        if key.endswith(('Fill','Stroke','Color')) and (not isinstance(value,str) or not re.fullmatch(color_pattern,value.strip(),re.I)):result[key]=DEFAULTS[key]
        elif key in {'padding','verticalSeparation','horizontalSeparation','arcRadius','fontSize','strokeWidth','markerRadius'}:
            m=re.match(r'^[ \t]*([-+]?(?:\d+(?:\.\d*)?|\.\d+))',str(value))
            number=float(m[1]) if m else math.nan;result[key]=number if math.isfinite(number) and number>=0 else DEFAULTS[key]
    if not isinstance(result['fontFamily'],str) or not re.fullmatch(r'[\w "\',.-]+',result['fontFamily']):result['fontFamily']=DEFAULTS['fontFamily']
    return result


async def build(diagram,p):
    c=_style(config_dict(diagram));radius=c['arcRadius'];pad=c['padding'];horizontal=c['horizontalSeparation'];vertical=c['verticalSeparation']
    def text_style(kind,tag='text'):
        prefix='terminal' if kind=='terminal' else 'nonTerminal'
        return p.style('railroad-'+kind,tag=tag,base={'fill':c.get(prefix+'Fill',c['specialFill']),'stroke':c.get(prefix+'Stroke',c['specialStroke']),
            'text_color':c[prefix+'TextColor'],'font_size':c['fontSize'],'font_family':c['fontFamily'],'stroke_width':c['strokeWidth'],'line_height':1.0},ancestors=(('g',('railroad-'+kind,),''),))
    def measure(expression,depth=0):
        if depth>128:raise ValueError('Railroad expression depth exceeds budget')
        kind=expression.kind
        if kind in {'terminal','nonterminal','special'}:
            label='? '+expression.text+' ?' if kind=='special' else expression.text
            st=text_style(kind)
            t=p.measure(label,size=st.font_size,family=st.font_family,weight=st.font_weight,italic=st.font_style!='normal',html=False,style=st)
            w=t.width+2*pad;h=t.height+2*pad;return Geometry(expression,w,h,h/2,h/2,label=t)
        children=tuple(measure(ch,depth+1) for ch in expression.children)
        if kind=='sequence':
            up=max(ch.up for ch in children);down=max(ch.down for ch in children);x=0;places=[]
            for ch in children:places.append((x,up-ch.up,ch));x+=ch.width+horizontal
            return Geometry(expression,x-horizontal,up+down,up,down,tuple(places))
        if kind=='choice':
            w=max(ch.width for ch in children)+4*radius;h=sum(ch.height for ch in children)+vertical*(len(children)-1);y=0;places=[]
            for ch in children:places.append((2*radius+(w-4*radius-ch.width)/2,y,ch));y+=ch.height+vertical
            return Geometry(expression,w,h,h/2,h/2,tuple(places))
        ch=children[0];bypass=kind=='optional' or expression.minimum==0
        offset=2*radius if bypass else 0;h=ch.height+2*radius+(2*radius if kind=='repetition' and bypass else 0)
        up=offset+ch.up;return Geometry(expression,ch.width+4*radius,h,up,h-up,((2*radius,offset,ch),))
    def path(d,identity):
        st=p.style('railroad-line',tag='path',id=identity,base={'stroke':c['lineColor'],'stroke_width':c['strokeWidth'],'fill':'none'})
        p.path(d,stroke=st.stroke,fill=st.fill,line_width=st.stroke_width,dash=st.dash,opacity=st.opacity,id=identity,role='railroad-line',style=st)
    def draw(geo,x,y,identity):
        kind=geo.expression.kind;w=geo.width;h=geo.height;cy=y+geo.up;r=radius
        if kind in {'terminal','nonterminal','special'}:
            prefix='terminal' if kind=='terminal' else 'nonTerminal'
            base={'fill':c['specialFill'] if kind=='special' else c[prefix+'Fill'],'stroke':c['specialStroke'] if kind=='special' else c[prefix+'Stroke'],'stroke_width':c['strokeWidth']}
            st=p.style('',tag='rect',id=identity,base=base,ancestors=(('g',('railroad-'+kind,),identity),))
            p.rect(x,y,w,h,fill=st.fill,stroke=st.stroke,line_width=st.stroke_width,radius=10 if kind=='terminal' else 0,dash=(5,3) if kind=='special' else st.dash,opacity=st.opacity,id=identity,role='railroad-'+kind,style=st)
            t=geo.label;st=text_style(kind);p.text(t,x+(w-t.width)/2,y+(h-t.height)/2,color=st.text_color,id=identity,role='railroad-label',style=st);return
        for i,(dx,dy,ch) in enumerate(geo.children):draw(ch,x+dx,y+dy,identity+f'-{i}')
        if kind=='sequence':
            for dx,dy,ch in geo.children[:-1]:path(f'M {x+dx+ch.width} {cy} H {x+dx+ch.width+horizontal}',identity)
            return
        if kind=='choice':
            for dx,dy,ch in geo.children:
                yy=y+dy+ch.up;below=yy>cy;sign=1 if below else -1
                if yy==cy:path(f'M {x} {cy} H {x+dx}',identity);path(f'M {x+dx+ch.width} {cy} H {x+w}',identity)
                else:
                    path(f'M {x} {cy} A {r} {r} 0 0 {int(below)} {x+r} {cy+sign*r} V {yy-sign*r} A {r} {r} 0 0 {int(not below)} {x+2*r} {yy} H {x+dx}',identity)
                    path(f'M {x+dx+ch.width} {yy} H {x+w-2*r} A {r} {r} 0 0 {int(not below)} {x+w-r} {yy-sign*r} V {cy+sign*r} A {r} {r} 0 0 {int(below)} {x+w} {cy}',identity)
            return
        dx,dy,ch=geo.children[0]
        path(f'M {x} {cy} H {x+dx}',identity);path(f'M {x+dx+ch.width} {cy} H {x+w}',identity)
        bypass=kind=='optional' or geo.expression.minimum==0
        if bypass:path(f'M {x} {cy} A {r} {r} 0 0 0 {x+r} {cy-r} V {y+r} A {r} {r} 0 0 1 {x+2*r} {y} H {x+w-2*r} A {r} {r} 0 0 1 {x+w-r} {y+r} V {cy-r} A {r} {r} 0 0 0 {x+w} {cy}',identity)
        if kind=='repetition':
            ly=y+dy+ch.height+r;ex=x+dx+ch.width
            path(f'M {ex} {cy} A {r} {r} 0 0 1 {ex+r} {cy+r} V {ly} A {r} {r} 0 0 1 {ex} {ly+r} H {x+2*r} A {r} {r} 0 0 1 {x+r} {ly} V {cy+r} A {r} {r} 0 0 1 {x+2*r} {cy}',identity)
    if not diagram.model.rules:return p.finish(width=200,height=100,padding=0,layout=())
    y=pad;max_width=0;layout=[]
    for index,rule in enumerate(diagram.model.rules):
        geo=measure(rule.definition);name=rule.name+' ='
        nt=p.measure(name,size=c['fontSize'],family=c['fontFamily'],html=False);name_width=nt.width+20;definition_x=name_width+20
        baseline=max(20,geo.up);definition_y=baseline-geo.up;identity='rule-'+str(index)
        draw(geo,definition_x,y+definition_y,identity)
        st=p.style('railroad-rule-name',tag='text',id=rule.name,base={'font_family':c['fontFamily'],'font_size':c['fontSize'],'font_weight':'bold','text_color':c['ruleNameColor']})
        namebox=p.measure(name,size=st.font_size,family=st.font_family,weight=st.font_weight,italic=st.font_style!='normal',html=False,style=st)
        p.text(namebox,0,y+baseline-namebox.ascent,color=st.text_color,id=identity,role='railroad-rule-name',style=st)
        # Fixed renderer currently paints these regardless of showMarkers;
        # retain that actual source branch rather than invent configuration.
        mr=c['markerRadius'];end=definition_x+geo.width+10
        p.ellipse(name_width,y+baseline,mr,mr,fill=c['markerFill'],stroke='none',id=identity,role='railroad-start')
        p.ellipse(end,y+baseline,mr,mr,fill=c['markerFill'],stroke='none',id=identity,role='railroad-end')
        path(f'M {name_width+mr} {y+baseline} H {definition_x}',identity);path(f'M {definition_x+geo.width} {y+baseline} H {end-mr}',identity)
        rh=max(40,definition_y+geo.height+2*pad);rw=end+mr;layout.append((rule.name,geo,y,rw,rh));y+=rh+vertical;max_width=max(max_width,rw)
    return p.finish(width=max_width+2*pad,height=y+pad,padding=0,layout=tuple(layout))
