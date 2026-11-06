"""Value scanning and relationship painting shared by modeling grammars.

This is not a grammar: consumers decide which structural tokens and statements
are legal. No native resource is created until their build entry is called.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import re


@dataclass(frozen=True)
class Statement:
    text: str
    offset: int


def statements(text, *, semicolon=True, braces=True):
    """Scan quoted/multiline strings, bracket labels, comments and structures."""
    out=[];start=0;i=0;quote='';depth=0
    def emit(end):
        value=text[start:end]
        if value.strip():out.append(Statement(value.strip(),start+len(value)-len(value.lstrip())))
    while i<len(text):
        c=text[i]
        if quote:
            if c==quote:quote=''
            i+=1;continue
        if c in ('"','`'):
            quote=c;i+=1;continue
        if text.startswith('%%',i):
            emit(i);j=text.find('\n',i);i=len(text) if j<0 else j;start=i;continue
        if c=='[':depth+=1
        elif c==']':depth=max(0,depth-1)
        structure=braces and c in '{}' and not (c=='{' and i and text[i-1] in '|o' or c=='}' and i+1<len(text) and text[i+1] in '|o')
        if not depth and (c=='\n' or semicolon and c==';' or structure):
            emit(i)
            if structure:out.append(Statement(c,i))
            start=i+1
        i+=1
    emit(len(text))
    return tuple(out)


def unquote(value):
    value=value.strip()
    return value[1:-1] if len(value)>1 and value[0] in ('"','`') and value[-1]==value[0] else value


def split_top(value,separator=','):
    result=[];start=0;quote='';level=0
    for i,c in enumerate(value):
        if quote:
            if c==quote:quote=''
        elif c in ('"',"'",'`'):quote=c
        elif c in '([{':level+=1
        elif c in ')]}':level-=1
        elif c==separator and level==0 and (i==0 or value[i-1]!='\\'):result.append(value[start:i].strip());start=i+1
    result.append(value[start:].strip());return tuple(result)


def styles(value):
    result=[]
    for item in split_top(value):
        if ':' in item:
            key,val=item.split(':',1);result.append((key.strip(),val.strip().replace('\\,',',')))
    return tuple(result)


def css(style,default=None):
    result=dict(default or {})
    for key,value in style:result[key]=value
    return result


def number(value,default):
    try:result=float(str(value).removesuffix('px'))
    except (TypeError,ValueError):return default
    return result if math.isfinite(result) else default


def theme(config):
    values=config.get('themeVariables') or {}
    return {'fill':values.get('mainBkg',values.get('primaryColor','#ffffff')),
            'stroke':values.get('nodeBorder',values.get('primaryBorderColor','#28253d')),
            'text':values.get('nodeTextColor',values.get('primaryTextColor','#28253d')),
            'edge':values.get('lineColor','#333333'),
            'note':values.get('noteBkgColor','#fff5ad'),
            'noteStroke':values.get('noteBorderColor','#aaaa33'),
            'group':values.get('clusterBkg','#f4f4f4'),
            'groupStroke':values.get('clusterBorder','#888888')}


def palette(config,index,fill,stroke):
    """common/colorThemeGate: independent border/background palette lengths."""
    values=config.get('themeVariables') or {};borders=values.get('borderColorArray');backgrounds=values.get('bkgColorArray')
    if index is not None and config.get('theme') in ('redux-color','redux-dark-color') and isinstance(borders,(tuple,list)) and borders:
        stroke=borders[index%len(borders)]
        if isinstance(backgrounds,(tuple,list)) and backgrounds:fill=backgrounds[index%len(backgrounds)]
    return fill,stroke


def node_style(painter,config,classes,id,definitions=(),inline=(),*,fill=None,stroke=None,color=None,index=None,tag='rect',ancestors=(),effects=True,base_extra=None):
    from ...rendering.styles.flowchart import apply_declarations
    values=theme(config);fill,stroke=palette(config,index,values['fill'] if fill is None else fill,values['stroke'] if stroke is None else stroke)
    variables=config.get('themeVariables') or {};base={'fill':fill,'stroke':stroke,'text_color':values['text'] if color is None else color,'stroke_width':number(variables.get('strokeWidth'),2 if config.get('look')=='neo' else 1)}
    if effects and config.get('look')=='neo' and variables.get('useGradient'):
        start,stop=variables.get('gradientStart'),variables.get('gradientStop')
        if isinstance(start,str) and isinstance(stop,str):base['stroke_gradient']=((0.,start),(1.,stop))
        borders=variables.get('borderColorArray')
        if index is not None and config.get('theme') in ('redux-color','redux-dark-color') and isinstance(borders,(list,tuple)) and borders:base['stroke_gradient']=()
    if base_extra:base.update(base_extra)
    base_style=painter.style((),tag=tag,id=id,base=base)
    if effects and config.get('look')=='neo' and variables.get('dropShadow'):
        base_style=apply_declarations(base_style,'filter:'+str(variables['dropShadow']),kind='node')
    if not ancestors:
        kind=painter.diagram.kind;alias={'er':'erDiagram','requirement':'requirementDiagram','c4':'c4','stateDiagram':'statediagram'}.get(kind,kind);ancestors=(('svg',(kind,alias),''),)
    style=painter.style(classes,tag=tag,id=id,base=base_style,ancestors=ancestors)
    defs=dict(definitions)
    for name in classes:
        if name in defs:style=apply_declarations(style,';'.join(k+':'+v for k,v in defs[name]),kind='node',svg_text=False)
    return apply_declarations(style,';'.join(k+':'+v for k,v in inline),kind='node',svg_text=False)


def clip_endpoint(box,toward,kind='rect'):
    from ...model.flowchart import Point
    cx=box.x+box.width/2;cy=box.y+box.height/2;dx=toward.x-cx;dy=toward.y-cy
    if not dx and not dy:return Point(cx,cy)
    if kind in ('ellipse','circle'):
        scale=1/math.sqrt((dx/(box.width/2))**2+(dy/(box.height/2))**2)
    elif kind=='diamond':scale=1/(abs(dx)/(box.width/2)+abs(dy)/(box.height/2))
    else:scale=min(box.width/2/abs(dx) if dx else math.inf,box.height/2/abs(dy) if dy else math.inf)
    return Point(cx+dx*scale,cy+dy*scale)


def label_style(style):
    """Source label subtree inherits node color; fill remains node paint."""
    from dataclasses import replace
    return replace(style,text_color=style.current_color or style.text_color)


def paint_edges(painter,layout,edges,palette,shapes=None):
    from ...rendering.styles.flowchart import apply_declarations
    from dataclasses import replace
    from ...runtime.graph import FrozenLookup,finish_graph
    edges=tuple(edges)
    if shapes:
        routes=[]
        for edge in edges:
            points=list(layout.edges.get(edge.id,()))
            if len(points)>1:
                for at,other,id in ((0,1,edge.source),(-1,-2,edge.target)):
                    if id in shapes and id in layout.nodes:points[at]=clip_endpoint(layout.nodes[id],points[other],shapes[id])
            routes.append((edge.id,tuple(points)))
        layout=replace(layout,edges=FrozenLookup(tuple(routes)),edge_paths=FrozenLookup(()))
        if layout.engine=='py-visactor-elk':layout=finish_graph(layout,[{'id':e.id,'source':e.source,'target':e.target} for e in edges],config=painter.config)
    for edge in edges:
        points=list(layout.edges.get(edge.id,()))
        if len(points)<2:continue
        style=painter.style(('edge','relation',*getattr(edge,'classes',())),tag='path',id=edge.id,base={'fill':'none','stroke':palette['edge'],'dash':(4.,3.) if edge.dashed else ()})
        style=apply_declarations(style,';'.join(k+':'+v for k,v in edge.styles),kind='edge');color=style.stroke
        path=(getattr(layout,'edge_paths',None) or {}).get(edge.id)
        if path:painter.path(path,style=style,id=edge.id)
        else:painter.polyline(points,style=style,id=edge.id)
        for at,marker,other in ((points[0],edge.start_marker,points[1]),(points[-1],edge.end_marker,points[-2])):
            if marker and marker!='none':painter.marker(at.x,at.y,at.x-other.x,at.y-other.y,kind=marker,color=color,fill=palette['fill'],id=edge.id)
        label=getattr(edge,'label','')
        if label:
            box=layout.labels.get(edge.id)
            label_style=painter.style(('edgeLabel','label'),tag='text',id=edge.id,base={'text_color':style.current_color or style.text_color},ancestors=(('g',('edgeLabel',),edge.id),))
            if box is not None:painter.text(label,box.x,box.y,style=label_style,label_kind=getattr(edge,'label_kind','text'),id=edge.id,role='edge-label')
            else:
                mid=points[len(points)//2];m=painter.measure(label)
                painter.rect(mid.x-m.width/2-2,mid.y-m.height/2-1,m.width+4,m.height+2,fill='white',stroke='none',id=edge.id,role='edge-label-background')
                painter.text(m,mid.x-m.width/2,mid.y-m.height/2,style=label_style,id=edge.id,role='edge-label')
        for text,at,other in ((getattr(edge,'source_label',''),points[0],points[1]),(getattr(edge,'target_label',''),points[-1],points[-2])):
            if text and text!='none':
                m=painter.measure(text);dx=other.x-at.x;dy=other.y-at.y;length=math.hypot(dx,dy) or 1
                painter.text(m,at.x+dx/length*14-dy/length*10-m.width/2,at.y+dy/length*14+dx/length*10-m.height/2,color=palette['text'],id=edge.id,role='cardinality')

    return layout


def draw_note(p,x,y,w,h,label,palette,id):
    # Unified note.ts is a rectangle. A dog-ear belongs to other shape handlers.
    variables=p.config.get('themeVariables') or {}
    s=p.style(('note','node'),id=id,base={'fill':palette['note'],'stroke':palette['noteStroke'],'text_color':variables.get('noteTextColor',palette['text'])})
    p.rect(x,y,w,h,style=s,id=id,role='note')
    box=p.measure(label,style=label_style(s),width=max(0,w-16))
    p.text(box,x+(w-box.width)/2,y+(h-box.height)/2,style=label_style(s),id=id)


def paint_title(diagram,painter,layout,css_class,margin=25):
    text=diagram.source.title
    if not text:return
    style=painter.style((css_class,),tag='text',base={'font_size':18.})
    box=painter.measure(text,html=False,style=style)
    painter.text(box,layout.width/2-box.width/2,-margin-box.ascent,style=style,id='diagram-title',role='title')
