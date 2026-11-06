"""Quadrant chart's dedicated grammar, style validation and normalized axes."""
from dataclasses import dataclass
import re
from ...runtime.common import make_diagram,config_dict,error
from ._syntax import statements,common_statement,words,split,scalar,theme,number

@dataclass(frozen=True)
class Quadrant:
    title:str
    axes:tuple[tuple[str,str],...]
    quadrants:tuple[str,...]
    points:tuple[tuple[str,str,float,float,tuple],...]
    classes:tuple[tuple[str,tuple],...]
    accessibility:tuple=()

def _styles(document,seq):
    out={}
    for part in split(seq):
        colon=next((i for i,t in enumerate(part) if t.value==':'),-1)
        if colon<1:raise error(document,part[0].offset if part else 0,'Expected quadrant style key:value')
        key=words(part[:colon]);value=words(part[colon+1:])
        if key=='radius':valid=re.fullmatch(r'\d+',value);converted=int(value) if valid else None
        elif key in ('color','stroke-color'):valid=re.fullmatch(r'#?(?:[\dA-Fa-f]{6}|[\dA-Fa-f]{3})',value);converted=value
        elif key=='stroke-width':valid=re.fullmatch(r'\d+px',value);converted=value
        else:raise error(document,part[0].offset,f'style named {key} is not supported.','INVALID_STYLE')
        if not valid:raise error(document,part[0].offset,f'value for {key} {value} is invalid','INVALID_STYLE')
        out[key]=converted
    return tuple(out.items())

def parse(document,config):
    rows=statements(document);meta={'title':document.title};axes={'x-left':'','x-right':'','y-bottom':'','y-top':''};quadrants=['']*4;points=[];classes={}
    if not rows or rows[0][0].value.lower()!='quadrantchart':raise error(document,0,'Expected quadrantChart')
    header=rows.pop(0)[1:]
    if header:rows.insert(0,header)
    for row in rows:
        if common_statement(row,meta):continue
        name=row[0].value.lower()
        if name in ('x-axis','y-axis'):
            delimiter=next((i for i,t in enumerate(row) if t.value=='-->'),-1)
            first=words(row[1:delimiter if delimiter>=0 else len(row)]).strip();second=words(row[delimiter+1:]).strip() if delimiter>=0 else ''
            if delimiter>=0 and not second:first+=' \u27f6 '
            keys=('x-left','x-right') if name=='x-axis' else ('y-bottom','y-top')
            axes[keys[0]]=first;axes[keys[1]]=second
        elif re.fullmatch(r'quadrant-[1-4]',name):quadrants[int(name[-1])-1]=words(row[1:]).strip()
        elif name=='classdef':
            if len(row)<3:raise error(document,row[0].offset,'Expected quadrant classDef name styles')
            classes[row[1].value]=_styles(document,row[2:])
        else:
            opening=next((i for i,t in enumerate(row[:-1]) if t.value==':' and row[i+1].value=='['),-1)
            if opening<1:raise error(document,row[0].offset,'Expected quadrant point : [x,y]')
            closing=next((i for i in range(opening+2,len(row)) if row[i].value==']'),-1)
            if closing<0 or closing-opening!=5 or row[opening+3].value!=',':raise error(document,row[opening].offset,'Expected quadrant [x,y]')
            x=scalar(document,row[opening+2]);y=scalar(document,row[opening+4])
            if not 0<=x<=1 or not 0<=y<=1:raise error(document,row[opening].offset,'Quadrant coordinates must be in [0,1]')
            prefix=row[:opening];class_name='';classpos=next((i for i,t in enumerate(prefix) if t.value==':::'),-1)
            if classpos>=0:
                if len(prefix)-classpos!=2:raise error(document,prefix[classpos].offset,'Expected quadrant class name')
                class_name=prefix[classpos+1].value;prefix=prefix[:classpos]
            label=words(prefix).strip();styles=_styles(document,row[closing+1:]) if closing+1<len(row) else ()
            points.insert(0,(label,class_name,x,y,styles)) # source addPoints prepends.
    return make_diagram('quadrantChart',document,config,Quadrant(meta.get('title',''),tuple(axes.items()),tuple(quadrants),tuple(points),tuple(classes.items()),tuple((k,v) for k,v in meta.items() if k!='title')))

async def build(diagram,p):
    m=diagram.model;c=config_dict(diagram);cfg=c.get('quadrantChart',{});axes=dict(m.axes);classes=dict(m.classes)
    defaults={'chartWidth':500,'chartHeight':500,'titlePadding':10,'titleFontSize':20,'quadrantPadding':5,'xAxisLabelPadding':5,'yAxisLabelPadding':5,'xAxisLabelFontSize':16,'yAxisLabelFontSize':16,'quadrantLabelFontSize':16,'quadrantTextTopPadding':5,'pointTextPadding':5,'pointLabelFontSize':12,'pointRadius':5,'xAxisPosition':'top','yAxisPosition':'left','quadrantInternalBorderStrokeWidth':1,'quadrantExternalBorderStrokeWidth':2,'showXAxis':True,'showYAxis':True,'showTitle':True}
    q={**defaults,**cfg};sx=q['showXAxis'] and bool(axes['x-left'] or axes['x-right']);sy=q['showYAxis'] and bool(axes['y-bottom'] or axes['y-top']);st=q['showTitle'] and bool(m.title)
    xp='bottom' if m.points else q['xAxisPosition'];yp=q['yAxisPosition'];xspace=2*q['xAxisLabelPadding']+q['xAxisLabelFontSize'] if sx else 0;yspace=2*q['yAxisLabelPadding']+q['yAxisLabelFontSize'] if sy else 0;tspace=q['titleFontSize']+2*q['titlePadding'] if st else 0
    left=q['quadrantPadding']+(yspace if yp=='left' else 0);top=q['quadrantPadding']+(xspace if xp=='top' else 0)+tspace;w=q['chartWidth']-2*q['quadrantPadding']-yspace;h=q['chartHeight']-2*q['quadrantPadding']-xspace-tspace
    for i,(column,row) in enumerate(((1,0),(0,0),(0,1),(1,1))):
        x=left+column*w/2;y=top+row*h/2
        p.rect(x,y,w/2,h/2,fill=theme(c,f'quadrant{i+1}Fill',('#ececff','#ffffde','#ffdfdf','#e2f0d9')[i]),stroke='none',id=f'quadrant-{i+1}')
        label=m.quadrants[i]
        if label:
            text=p.measure(label,size=q['quadrantLabelFontSize']);yy=y+q['quadrantTextTopPadding'] if m.points else y+h/4-text.height/2
            p.text(text,x+w/4,yy,align='center',color=theme(c,f'quadrant{i+1}TextFill','#333'),id=f'quadrant-label-{i+1}')
    ew=q['quadrantExternalBorderStrokeWidth'];iw=q['quadrantInternalBorderStrokeWidth'];external=theme(c,'quadrantExternalBorderStrokeFill','#333');internal=theme(c,'quadrantInternalBorderStrokeFill','#333')
    for i,(a,b) in enumerate((((left-ew/2,top),(left+w+ew/2,top)),((left+w,top+ew/2),(left+w,top+h-ew/2)),((left-ew/2,top+h),(left+w+ew/2,top+h)),((left,top+ew/2),(left,top+h-ew/2)))):p.line(*a,*b,stroke=external,line_width=ew,id=f'outer-{i}')
    p.line(left+w/2,top+ew/2,left+w/2,top+h-ew/2,stroke=internal,line_width=iw,id='middle-x');p.line(left+ew/2,top+h/2,left+w-ew/2,top+h/2,stroke=internal,line_width=iw,id='middle-y')
    if st:p.text(m.title,q['chartWidth']/2,q['titlePadding'],align='center',size=q['titleFontSize'],color=theme(c,'quadrantTitleFill','#333'),role='title')
    if sx:
        middle=bool(axes['x-right']);y=q['xAxisLabelPadding']+tspace if xp=='top' else q['xAxisLabelPadding']+top+h+q['quadrantPadding']
        for i,key in enumerate(('x-left','x-right')):
            if axes[key]:p.text(axes[key],left+i*w/2+(w/4 if middle else 0),y,align='center' if middle else 'left',size=q['xAxisLabelFontSize'],color=theme(c,'quadrantXAxisTextFill','#333'),id=key)
    if sy:
        middle=bool(axes['y-top']);x=q['yAxisLabelPadding'] if yp=='left' else q['yAxisLabelPadding']+left+w+q['quadrantPadding']
        for i,key in enumerate(('y-bottom','y-top')):
            if axes[key]:p.text(axes[key],x,top+h-i*h/2-(h/4 if middle else 0),align='center' if middle else 'left',rotation=-90,size=q['yAxisLabelFontSize'],color=theme(c,'quadrantYAxisTextFill','#333'),id=key)
    positions=[]
    for i,(label,class_name,x,y,styles) in enumerate(m.points):
        style={**dict(classes.get(class_name,())),**dict(styles)};px=left+x*w;py=top+(1-y)*h;r=style.get('radius',q['pointRadius']);fill=style.get('color',theme(c,'quadrantPointFill','#333'))
        p.ellipse(px,py,r,r,fill=fill,stroke=style.get('stroke-color',theme(c,'quadrantPointFill','#333')),line_width=number(style.get('stroke-width','0px'),0),id=f'point-{i}')
        p.text(label,px,py+q['pointTextPadding'],align='center',size=q['pointLabelFontSize'],color=theme(c,'quadrantPointTextFill','#333'),id=f'point-label-{i}');positions.append((label,px,py))
    return p.finish(width=q['chartWidth'],height=q['chartHeight'],padding=0,layout={'kind':'quadrant','frame':(left,top,w,h),'points':tuple(positions)})
