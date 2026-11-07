"""Owner-thread display list for native static diagram families.

This adapter shares the flowchart label, resource and formula implementation.
All exported scene values are immutable; Canvas/Path2D/Image never leave it.
"""
from __future__ import annotations

import base64
import math
import re
from dataclasses import fields, replace

from .session import CanvasSession
from ...model.flowchart import Box, Point, DrawEvent, ResolvedStyle, MermaidError, ExportOptions
from ...model.scene import TextBox, Paint, Scene, FlowchartScene, DiagramRenderResult
from ...runtime.common import config_dict, number, label_config, immutable_value, utf16_length
from ..labels import measure_label
from ..styles.flowchart import parse_css, apply_declarations


def _union(boxes):
    boxes=tuple(boxes)
    if not boxes:return Box(0,0,0,0)
    left=min(b.x for b in boxes);top=min(b.y for b in boxes)
    return Box(left,top,max(b.x+b.width for b in boxes)-left,max(b.y+b.height for b in boxes)-top)


def _stroke_box(path,width,cap='butt',join='miter',dash=()):
    """Bound actual centered stroke using public Path2D.edges only.

    Curves use positive-weight rational Bezier convex hulls and their tangent
    direction cone. Subdivision tightens those *conservative* offset intervals;
    sampled offsets are only pruning witnesses, never the returned boundary.
    Real segment joins alone receive miter tips (Canvas default miterLimit 10).
    Depth/work limits retain the last conservative interval, not a clipped
    sampled approximation. Native paths/handles remain on their owner thread.
    """
    r=width/2;boxes=[];contours=[];segments=[];start=current=None
    fallback=False;work=0

    def point(h):return h[0]/h[2],h[1]/h[2]
    def unit(v):
        length=math.hypot(*v)
        return (v[0]/length,v[1]/length) if length>1e-12 else None
    def add_points(points):
        xs,ys=zip(*points);boxes.append(Box(min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)))
    def disk(p,radius=r):boxes.append(Box(p[0]-radius,p[1]-radius,2*radius,2*radius))
    def flush(closed=False):
        nonlocal segments
        if segments:contours.append((segments,closed));segments=[]
    def tangent(control,end=False):
        pts=[point(h) for h in control];origin=pts[-1] if end else pts[0]
        for p in (reversed(pts[:-1]) if end else pts[1:]):
            direction=unit((origin[0]-p[0],origin[1]-p[1]) if end else (p[0]-origin[0],p[1]-origin[1]))
            if direction:return direction
        return None
    def split(control):
        rows=[control]
        while len(rows[-1])>1:
            row=rows[-1];rows.append([tuple((a+b)/2 for a,b in zip(p,q)) for p,q in zip(row,row[1:])])
        return [row[0] for row in rows],[row[-1] for row in reversed(rows)]
    def samples(control):
        pts=[point(h) for h in control]
        mid=split(control)[0][-1];p=point(mid)
        left,right=split(control)
        samples=((pts[0],tangent(control)),(p,tangent(left,True) or tangent(right)),(pts[-1],tangent(control,True)))
        result=[]
        for (x,y),t in samples:
            if t:result.extend(((x-r*t[1],y+r*t[0]),(x+r*t[1],y-r*t[0])))
            else:result.extend(((x-r,y-r),(x+r,y+r)))
        return result
    def interval(control):
        pts=[point(h) for h in control]
        directions=[unit((q[0]-p[0],q[1]-p[1])) for p,q in zip(pts,pts[1:])]
        angles=[math.atan2(v[1],v[0]) for v in directions if v]
        nx=ny=1
        if angles:
            base=angles[0];angles=[base+math.atan2(math.sin(a-base),math.cos(a-base)) for a in angles]
            lo,hi=min(angles),max(angles)
            if hi-lo<math.pi-1e-10:
                critical=[lo,hi]+[k*math.pi/2 for k in range(math.ceil(lo/(math.pi/2)),math.floor(hi/(math.pi/2))+1)]
                nx=max(abs(math.sin(a)) for a in critical);ny=max(abs(math.cos(a)) for a in critical)
        xs,ys=zip(*pts)
        return min(xs)-r*nx,min(ys)-r*ny,max(xs)+r*nx,max(ys)+r*ny
    def curve(control):
        nonlocal work,fallback
        # Positive homogeneous weights keep every subcurve in its control hull.
        if any(h[2]<=0 for h in control):
            fallback=True
            b=path.bounds;boxes.append(Box(b['left']-r,b['top']-r,b['width']+2*r,b['height']+2*r));return
        witness=samples(control)
        xmin=min(p[0] for p in witness);xmax=max(p[0] for p in witness)
        ymin=min(p[1] for p in witness);ymax=max(p[1] for p in witness)
        stack=[(control,0)]
        while stack:
            c,depth=stack.pop();work+=1
            samples_=samples(c)
            xmin=min(xmin,*(p[0] for p in samples_));xmax=max(xmax,*(p[0] for p in samples_))
            ymin=min(ymin,*(p[1] for p in samples_));ymax=max(ymax,*(p[1] for p in samples_))
            left,top,right,bottom=interval(c)
            accurate=left>=xmin-.125 and right<=xmax+.125 and top>=ymin-.125 and bottom<=ymax+.125
            if accurate or depth>=16 or work>=8192:
                boxes.append(Box(left,top,right-left,bottom-top))
                if not accurate:fallback=True
            else:
                a,b=split(c);stack.extend(((a,depth+1),(b,depth+1)))
    for edge in path.edges:
        command=edge[0];values=edge[1:]
        if command=='moveTo':
            flush();current=start=(values[0],values[1])
        elif command=='closePath':
            if current is not None and start is not None and current!=start:
                segments.append([(current[0],current[1],1),(start[0],start[1],1)])
            flush(True);current=start
        elif current is not None:
            control=[(*current,1)]
            if command=='lineTo':control.append((values[0],values[1],1))
            elif command=='quadraticCurveTo':control.extend(((values[0],values[1],1),(values[2],values[3],1)))
            elif command=='bezierCurveTo':control.extend(tuple((*values[i:i+2],1)) for i in (0,2,4))
            elif command=='conicCurveTo':
                w=values[4];control.extend(((values[0]*w,values[1]*w,w),(values[2],values[3],1)))
            else:
                fallback=True;continue
            segments.append(control);current=point(control[-1])
    flush()
    for contour,closed in contours:
        for control in contour:curve(control)
        joins=list(zip(contour,contour[1:]))+([(contour[-1],contour[0])] if closed else [])
        for incoming,outgoing in joins:
            p=point(incoming[-1]);u=tangent(incoming,True);v=tangent(outgoing)
            if not u or not v:continue
            if join=='round':disk(p)
            elif join=='miter':
                denom=1+u[0]*v[0]+u[1]*v[1]
                if denom>1e-12:
                    dx=r*(-u[1]-v[1])/denom;dy=r*(u[0]+v[0])/denom
                    if math.hypot(dx,dy)<=10*r+1e-9:add_points(((p[0]+dx,p[1]+dy),(p[0]-dx,p[1]-dy)))
        if not closed:
            for control,end in ((contour[0],False),(contour[-1],True)):
                p=point(control[-1] if end else control[0]);t=tangent(control,end)
                if cap=='round':disk(p)
                elif cap=='square':
                    if not t:disk(p,r*math.sqrt(2));continue
                    sign=1 if end else -1
                    add_points(((p[0]+sign*r*t[0]-r*t[1],p[1]+sign*r*t[1]+r*t[0]),
                                (p[0]+sign*r*t[0]+r*t[1],p[1]+sign*r*t[1]-r*t[0])))
    if dash and cap in ('round','square'):
        # Internal dash endpoints can occur anywhere on the curve. Their cap
        # disks/squares are a subset of this centerline Minkowski envelope.
        b=path.bounds;extra=r*(math.sqrt(2) if cap=='square' else 1)
        boxes.append(Box(b['left']-extra,b['top']-extra,b['width']+2*extra,b['height']+2*extra))
    if not boxes:
        b=path.bounds;boxes.append(Box(b['left'],b['top'],b['width'],b['height']))
    return _union(boxes),fallback


def _paint_path_box(path,fill,stroke,width,dash=(),style=None):
    b=path.bounds;box=Box(b['left'],b['top'],b['width'],b['height']);fallback=False
    if stroke not in (None,'none','transparent','') and width>0:
        box,fallback=_stroke_box(path,width,style.line_cap if style else 'butt',style.line_join if style else 'miter',dash)
        if fill not in (None,'none','transparent',''):box=_union((box,Box(b['left'],b['top'],b['width'],b['height'])))
    return box,fallback


def _mapped(box,matrix):
    a,b,c,d,e,f=matrix
    pts=tuple(Point(a*x+c*y+e,b*x+d*y+f) for x,y in ((box.x,box.y),(box.x+box.width,box.y),(box.x,box.y+box.height),(box.x+box.width,box.y+box.height)))
    return Box(min(p.x for p in pts),min(p.y for p in pts),max(p.x for p in pts)-min(p.x for p in pts),max(p.y for p in pts)-min(p.y for p in pts))


def _intersection(box,clip):
    left=max(box.x,clip.x);top=max(box.y,clip.y)
    right=min(box.x+box.width,clip.x+clip.width);bottom=min(box.y+box.height,clip.y+clip.height)
    if right<=left or bottom<=top:return Box(clip.x,clip.y,0,0)
    return Box(left,top,right-left,bottom-top)


def _classes(value):
    return tuple(value.split()) if isinstance(value,str) else tuple(value)


_ATTRIBUTE=re.compile(r'''\[\s*(data-look|data-theme|id|class)\s*(?:([~|^$*]?=)\s*["']?([\w .-]+?)["']?)?\s*\]''')


def _simple(selector,element,config):
    tag,classes,identifier=element
    for negation in re.findall(r':not\(([^()]+)\)',selector):
        if any(_simple(part.strip(),element,config) for part in negation.split(',')):return False
    selector=re.sub(r':not\([^()]+\)','',selector)
    for match in _ATTRIBUTE.finditer(selector):
        name,operator,value=match.groups()
        actual={'data-look':config.get('look'),'data-theme':config.get('theme'),'id':identifier,'class':' '.join(_classes(classes))}[name]
        if operator is None:
            if actual in (None,''):return False
        elif operator=='=':
            if actual!=value:return False
        elif operator=='~=':
            if value not in str(actual or '').split():return False
        elif operator=='^=':
            if not str(actual or '').startswith(value):return False
        elif operator=='$=':
            if not str(actual or '').endswith(value):return False
        elif operator=='*=':
            if value not in str(actual or ''):return False
        elif operator=='|=':
            if actual!=value and not str(actual or '').startswith(value+'-'):return False
    selector=_ATTRIBUTE.sub('',selector)
    parts=re.findall(r'[#.]?[\w-]+|\*',selector)
    if ''.join(parts)!=selector:return False
    return all((token[1:]==identifier if token.startswith('#') else token[1:] in _classes(classes) if token.startswith('.') else token in ('*',tag)) for token in parts)


def _selector(selector,element,ancestors,config):
    # Source diagram sheets use compound selectors and child/descendant chains.
    tokens=re.findall(r'''(?:\[[^\]]+\]|[^\s>\[])+|>''',selector.strip())
    if not tokens or not _simple(tokens[-1],element,config):return False
    tokens=tokens[:-1];chain=list(ancestors)
    while tokens:
        child=tokens[-1]=='>'
        if child:tokens.pop()
        if not tokens or not chain:return False
        needle=tokens.pop()
        if child:
            if not _simple(needle,chain.pop(),config):return False
        else:
            while chain and not _simple(needle,chain[-1],config):chain.pop()
            if not chain:return False
            chain.pop()
    return True


class Painter:
    """One native session and semantic display list for one diagram."""

    def __init__(self,diagram,*,backend='auto',resources=None):
        self.diagram=diagram
        self.config=config_dict(diagram)
        self.session=CanvasSession(backend=backend,resources=resources)
        self._vchart_backend=backend
        self._vchart_resources=resources
        self.commands=[]
        self._gradients={}
        self._diagnostics=[]
        # Each family enables this only where its fixed renderer uses roughjs.
        self.rough_enabled=False
        # Reuse the audited rich-label configuration without sending unrelated
        # family sections into the flowchart-specific validator.
        self._label_config=label_config(self.config)
        self._css=self._stylesheet(self.config.get('themeCSS') or '')
        self.viewport_width=number(self.config.get('viewportWidth',1200),name='viewportWidth',minimum=1)
        self.render_id=self.config.get('renderId',diagram.kind)
        if not isinstance(self.render_id,str) or not self.render_id:raise MermaidError('renderId must be a nonempty string',code='INVALID_CONFIG')

    def _check(self):self.session._check_owner()

    @staticmethod
    def _stylesheet(css):
        rules=parse_css(css)
        for selector,declarations in rules:
            plain=re.sub(r':not\([^()]+\)','',selector)
            if re.search(r'[^\w\s.#*>-]',_ATTRIBUTE.sub('',plain)):raise MermaidError('Unsupported static CSS selector: '+selector,code='UNSUPPORTED_THEME_CSS')
        return rules

    def add_styles(self,css,*,prepend=True):
        """Add family source styles before the user stylesheet by default."""
        self._check()
        rules=self._stylesheet(css)
        self._css=rules+self._css if prepend else self._css+rules

    def register_gradient(self,id,stops,*,direction=(0,0,1,0)):
        self._check()
        if not isinstance(id,str) or not id or any(c in id for c in '<>\"\'() \r\n'):raise MermaidError('Invalid gradient identifier',code='INVALID_RESOURCE')
        stops=tuple((number(offset,minimum=0,maximum=1),color) for offset,color in stops)
        if not stops or any(not isinstance(color,str) for offset,color in stops):raise MermaidError('Gradient needs color stops',code='INVALID_RESOURCE')
        direction=tuple(number(value) for value in direction)
        if len(direction)!=4:raise MermaidError('Gradient direction needs four numbers',code='INVALID_GEOMETRY')
        self._gradients[id]=(stops,direction)

    def measure_flowchart(self,flowchart):
        """Source layout variants reuse all fixed flowchart measuring branches."""
        self._check()
        return self.session.measure(flowchart),self.session.measure_annotations(flowchart)

    def take_commands(self):
        self._check()
        commands=tuple(self.commands);self.commands.clear()
        return commands

    def flowchart_scene(self,flowchart,layout,*,measured,annotations,group_overrides=()):
        self._check()
        return FlowchartScene(flowchart,layout,tuple(measured),annotations,tuple(group_overrides))

    def _base_style(self):
        cfg=self._label_config
        return ResolvedStyle(fill=cfg.fill,stroke=cfg.stroke,text_color=cfg.text_color,
            font_family=cfg.font_family,font_size=cfg.font_size,line_height=cfg.line_height,
            shadow_opacity=0,text_align='left',text_anchor='start')

    def style(self,classes,*,tag='rect',id='',base=None,ancestors=(),inherited=None):
        self._check()
        style=base if isinstance(base,ResolvedStyle) else replace(self._base_style(),**(base or {}))
        if inherited is not None:style=replace(style,important_properties=())
        element=(tag,_classes(classes),id)
        matched=[]
        for order,(selector,declarations) in enumerate(self._css):
            if _selector(selector,element,ancestors,self.config):
                specificity=(selector.count('#'),selector.count('.')+len(_ATTRIBUTE.findall(selector)),len(re.findall(r'(?:^|[ >])\w+',selector)))
                matched.append((specificity,order,declarations))
        for _,__,declarations in sorted(matched,key=lambda item:item[:2]):
            style=apply_declarations(style,declarations,kind='node-label' if tag in ('text','tspan','span','label') else 'node',svg_text=tag in ('text','tspan'),inherited=inherited,paint_resources=self._gradients)
        return replace(style,paint_context=tuple(ancestors)+(element,))

    def measure(self,text,*,size=None,family=None,weight='normal',italic=False,html=None,width=None,align=None,label_kind='text',style=None,literal=False,raw_html=False):
        self._check()
        if not isinstance(text,str):raise MermaidError('Label must be text',code='INVALID_LABEL')
        if label_kind not in ('text','markdown'):raise MermaidError('Unknown label kind',code='INVALID_LABEL')
        if not isinstance(literal,bool) or (literal and label_kind!='text'):raise MermaidError('literal measurement requires plain text',code='INVALID_LABEL')
        if not isinstance(raw_html,bool) or (raw_html and (literal or label_kind!='text')):raise MermaidError('raw_html requires a direct HTML text consumer',code='INVALID_LABEL')
        if utf16_length(text)>self._label_config.max_text_size:raise MermaidError('Label exceeds maxTextSize',code='TEXT_LIMIT')
        style=style or self._base_style()
        style=replace(style,font_size=number(size if size is not None else style.font_size,name='fontSize',minimum=.01),
            font_family=family or style.font_family,font_weight=str(weight) if weight!='normal' else style.font_weight,font_style='italic' if italic else style.font_style)
        if align is not None:style=replace(style,text_align=align,text_anchor={'left':'start','center':'middle','right':'end'}.get(align,'start'))
        cfg=replace(self._label_config,html_labels=self._label_config.html_labels if html is None else bool(html))
        if raw_html and not cfg.html_labels:raise MermaidError('raw_html requires HTML measurement',code='INVALID_LABEL')
        def asset_loader(identifier,kind,attrs,run_style,image_only):
            natural_w,natural_h=self.session._asset_size(identifier,kind)
            if kind=='icon':return run_style.font_size,run_style.font_size
            if kind=='svg':return natural_w,natural_h
            target=cfg.site_font_size*5 if image_only else width if width is not None else cfg.wrapping_width
            return target,target*natural_h/natural_w
        def tag_style(tag,base,classes=(),parent=None):
            return self.style(classes,tag=tag,base=base,inherited=parent,ancestors=parent.paint_context if parent else ())
        def svg_style(tag,base,classes=(),parent=None):
            return self.style(classes,tag=tag,base=base,inherited=parent,ancestors=parent.paint_context if parent else ())
        w,h,lines,runs=measure_label(text,label_kind,cfg,style,self.session._measure_span,
            width=number(width,name='label width',minimum=0) if width is not None else math.inf,
            diagnostics=self._diagnostics,asset_loader=asset_loader,math_loader=self.session._math_atom,
            tag_style=tag_style,svg_style=svg_style,literal=literal,raw_html=raw_html)
        return TextBox(text,w,h,max((line.ascent for line in lines),default=0),max((line.descent for line in lines),default=0),runs)

    def font_size(self,value,*,base=None,family=None,weight='normal',italic=False):
        """Resolve source CSS font units using the actual owner-thread font.

        Relative sizes inherit the caller's parent size, not the option's
        default. ex uses the ink of x; ch uses the advance of U+0030. No native
        measurement object escapes this call.
        """
        self._check()
        from ...config.flowchart import font_pixels
        from ..styles.flowchart import css_size
        base=number(self._label_config.font_size if base is None else base,name='parent fontSize',minimum=.01)
        if isinstance(value,str):
            match=re.fullmatch(r'\s*([+]?(?:\d+(?:\.\d*)?|\.\d+))\s*(ex|ch)\s*',value,re.I)
            if match:
                unit=match[2].lower()
                box=self.measure('x' if unit=='ex' else '0',size=base,family=family,weight=weight,italic=italic,html=False)
                metric=max((run.ascent+run.descent for run in box.runs),default=0) if unit=='ex' else box.width
                return number(float(match[1])*metric,name='fontSize',minimum=.01)
            if value.strip().lower() in {'xx-small','x-small','small','medium','large','x-large','xx-large','smaller','larger'}:
                return css_size(value.strip(),base)
            dimension=re.fullmatch(r'\s*([+]?(?:\d+(?:\.\d*)?|\.\d+))\s*(px|pt|pc|in|cm|mm|q|em|rem|%)?\s*',value,re.I)
            if dimension:
                value=str(float(dimension[1]))+(dimension[2] or '')
        return font_pixels(value,default=base)

    def text(self,text_or_box,x,y,*,size=None,family=None,weight='normal',italic=False,color=None,align=None,html=None,width=None,id='',role='label',rotation=0,label_kind='text',style=None,clip=None):
        self._check()
        text=text_or_box if isinstance(text_or_box,TextBox) else self.measure(text_or_box,size=size,family=family,weight=weight,italic=italic,html=html,width=width,align=align,label_kind=label_kind,style=style)
        x=number(x);y=number(y);rotation=number(rotation)
        x-=text.width*(.5 if align=='center' else 1 if align=='right' else 0)
        # A measured box already contains the full nested CSS cascade. Replacing
        # its per-run opacity/decorations here would erase rich child styles.
        if color is not None:text=replace(text,runs=tuple(replace(run,color=color) for run in text.runs))
        box=Box(x,y,text.width,text.height)
        ink=_union((box,*(self.session._ink_box(run,box) for run in text.runs)))
        angle=math.radians(rotation);co,si=math.cos(angle),math.sin(angle)
        matrix=(co,si,-si,co,x-co*x+si*y,y-si*x-co*y)
        bounds=_mapped(ink,matrix)
        if clip is not None:
            values=(clip.x,clip.y,clip.width,clip.height) if isinstance(clip,Box) else tuple(clip)
            if len(values)!=4:raise MermaidError('Text clip needs x/y/width/height',code='INVALID_GEOMETRY')
            clip=Box(number(values[0]),number(values[1]),number(values[2],minimum=0),number(values[3],minimum=0))
            bounds=_intersection(bounds,clip)
        self.commands.append(Paint('text',(text,x,y,rotation,clip),semantic_id=id,role=role,bounds=bounds))
        return text

    def shape_geometry(self,kind,label_width,label_height,*,padding=None,metadata=(),direction='TD'):
        self._check()
        from ...geometry.shapes import shape_geometry
        cfg=self._label_config if padding is None else replace(self._label_config,node_padding=number(padding,minimum=0))
        return shape_geometry(kind,label_width,label_height,cfg,metadata=metadata,asset_size=self.session._asset_size,direction=direction)

    def path(self,d,*,fill=None,stroke=None,line_width=None,dash=None,id='',role='path',opacity=None,transform=(1,0,0,1,0,0),style=None,rough_options=None):
        self._check()
        if style is not None and style.display=='none':return
        if not isinstance(d,str):raise MermaidError('Path must be SVG path data',code='INVALID_GEOMETRY')
        if not d.strip():return
        transform=tuple(number(n) for n in transform)
        if len(transform)!=6:raise MermaidError('Affine transform needs six numbers',code='INVALID_GEOMETRY')
        if style is not None:
            fill=style.fill if fill is None else fill;stroke=style.stroke if stroke is None else stroke
            line_width=style.stroke_width if line_width is None else line_width
            opacity=(style.opacity if opacity is None else opacity) if style.visibility=='visible' else 0
            dash=style.dash if dash is None else dash
        line_width=number(1 if line_width is None else line_width,minimum=0);opacity=number(1 if opacity is None else opacity,minimum=0,maximum=1)
        dash=tuple(number(n,minimum=0) for n in (dash or ()))
        if self.rough_enabled and self.config.get('look')=='handDrawn':
            from ...geometry.rough import rough_path
            opts={};aliases={'fillWeight':'fill_weight','hachureGap':'hachure_gap','hachureAngle':'hachure_angle','fillStyle':'fill_style'}
            for key,value in (rough_options or {}).items():
                key=aliases.get(key,key)
                if key not in ('seed','roughness','fill_weight','hachure_gap','hachure_angle','fill_style'):raise MermaidError('Unsupported rough option '+key,code='INVALID_CONFIG')
                opts[key]=value
            opts.setdefault('seed',self.config.get('handDrawnSeed',0))
            rough=rough_path(d,fill=fill not in (None,'none','transparent',''),**opts)
            if rough.fill_path:self._record_path(rough.fill_path,transform,fill=fill if rough.fill_style=='solid' else None,stroke=None if rough.fill_style=='solid' else fill,line_width=rough.fill_width,dash=(),id=id,role=role+'-hachure',opacity=opacity,style=style)
            if opts.get('fill_style')=='cross-hatch' and fill not in (None,'none','transparent',''):
                other=rough_path(d,fill=True,**{**opts,'fill_style':'hachure','hachure_angle':opts.get('hachure_angle',-41)+90})
                if other.fill_path:self._record_path(other.fill_path,transform,fill=None,stroke=fill,line_width=other.fill_width,dash=(),id=id,role=role+'-cross-hachure',opacity=opacity,style=style)
            self._record_path(rough.stroke_path,transform,fill=None,stroke=stroke,line_width=line_width,dash=dash,id=id,role=role,opacity=opacity,style=style)
        else:self._record_path(d,transform,fill=fill,stroke=stroke,line_width=line_width,dash=dash,id=id,role=role,opacity=opacity,style=style)

    def _record_path(self,d,transform,*,fill,stroke,line_width,dash,id,role,opacity,style):
        path=self.session._path_factory(d).transform(*transform)
        box,fallback=_paint_path_box(path,fill,stroke,line_width,dash,style)
        if fallback:self._diagnostics.append('stroke_bounds_conservative_fallback')
        if style is not None and style.shadow_opacity>0:
            blur=style.shadow_blur*3
            box=_union((box,Box(box.x+style.shadow_dx-blur,box.y+style.shadow_dy-blur,box.width+2*blur,box.height+2*blur)))
        self.commands.append(Paint('path',(d,transform),tuple(dict(fill=fill,stroke=stroke,line_width=line_width,dash=dash,opacity=opacity,resolved=style).items()),id,role,box))

    def rect(self,x,y,w,h,*,fill=None,stroke=None,line_width=None,radius=0,dash=None,id='',role='shape',opacity=None,style=None):
        x,y,w,h=number(x),number(y),number(w,minimum=0),number(h,minimum=0)
        r=min(number(radius,minimum=0),w/2,h/2)
        d=f'M{x+r},{y}H{x+w-r}Q{x+w},{y} {x+w},{y+r}V{y+h-r}Q{x+w},{y+h} {x+w-r},{y+h}H{x+r}Q{x},{y+h} {x},{y+h-r}V{y+r}Q{x},{y} {x+r},{y}Z' if r else f'M{x},{y}h{w}v{h}h{-w}Z'
        self.path(d,fill=fill,stroke=stroke,line_width=line_width,dash=dash,id=id,role=role,opacity=opacity,style=style)

    def ellipse(self,cx,cy,rx,ry,*,fill=None,stroke=None,line_width=None,id='',role='shape',opacity=None,style=None,rough_options=None):
        cx,cy,rx,ry=number(cx),number(cy),number(rx,minimum=0),number(ry,minimum=0)
        self.path(f'M{cx-rx},{cy}a{rx},{ry} 0 1,0 {2*rx},0a{rx},{ry} 0 1,0 {-2*rx},0Z',fill=fill,stroke=stroke,line_width=line_width,id=id,role=role,opacity=opacity,style=style,rough_options=rough_options)

    def line(self,x1,y1,x2,y2,*,stroke=None,line_width=None,dash=None,id='',role='line',opacity=None,style=None):
        self.path(f'M{number(x1)},{number(y1)}L{number(x2)},{number(y2)}',fill='none',stroke=stroke,line_width=line_width,dash=dash,id=id,role=role,opacity=opacity,style=style)

    def polyline(self,points,*,stroke=None,line_width=None,dash=None,id='',role='edge',opacity=None,style=None):
        pts=tuple((number(p.x),number(p.y)) if isinstance(p,Point) else (number(p[0]),number(p[1])) for p in points)
        if not pts:return
        self.path('M'+'L'.join(f'{x},{y}' for x,y in pts),fill='none',stroke=stroke,line_width=line_width,dash=dash,id=id,role=role,opacity=opacity,style=style)

    def polygon(self,points,*,fill=None,stroke=None,line_width=None,id='',role='shape',opacity=None,style=None):
        pts=tuple((number(p.x),number(p.y)) if isinstance(p,Point) else (number(p[0]),number(p[1])) for p in points)
        if not pts:return
        self.path('M'+'L'.join(f'{x},{y}' for x,y in pts)+'Z',fill=fill,stroke=stroke,line_width=line_width,id=id,role=role,opacity=opacity,style=style)

    def marker_path(self,d,*,kind='point',**options):
        """Paint explicit source marker geometry and retain its semantic kind.

        Diagram-specific marker anchors and outlines belong to the caller;
        ordinary path validation, styles, bounds and drawing stay here.
        """
        self._check()
        if not isinstance(kind,str) or not kind:
            raise MermaidError('Marker path requires a semantic kind',code='INVALID_GEOMETRY')
        start=len(self.commands)
        options.setdefault('role','marker')
        self.path(d,**options)
        for index in range(start,len(self.commands)):
            command=self.commands[index]
            self.commands[index]=replace(command,style=tuple({**dict(command.style),'marker':kind}.items()))

    def marker(self,x,y,dx,dy,*,kind='point',size=8,color=None,fill=None,id='',line_width=1):
        x,y,dx,dy,size=number(x),number(y),number(dx),number(dy),number(size,minimum=0)
        length=math.hypot(dx,dy)
        if not length:raise MermaidError('Marker needs a nonzero direction',code='INVALID_GEOMETRY')
        ux,uy=dx/length,dy/length;vx,vy=-uy,ux
        def pt(a,b=0):return (x+ux*a+vx*b,y+uy*a+vy*b)
        color=color or self.config.get('themeVariables',{}).get('lineColor') or '#333'
        background=fill or self.config.get('themeVariables',{}).get('background') or 'white'
        start=len(self.commands)
        if kind in ('point','extension','open','dependency'):
            points=(pt(-size,-size/2),pt(0),pt(-size,size/2))
            if kind in ('open','dependency'):self.polyline(points,stroke=color,line_width=line_width,id=id,role='marker')
            else:self.polygon(points,fill=color if kind=='point' else background,stroke=color,line_width=line_width,id=id,role='marker')
        elif kind in ('aggregation','composition'):
            self.polygon((pt(0),pt(-size,size/2),pt(-2*size),pt(-size,-size/2)),fill=color if kind=='composition' else background,stroke=color,line_width=line_width,id=id,role='marker')
        elif kind in ('circle','zero','lollipop'):
            cx,cy=pt(-size/2);self.ellipse(cx,cy,size/2,size/2,fill=background,stroke=color,line_width=line_width,id=id,role='marker')
        elif kind in ('bar','one'):
            a,b=pt(0,-size/2),pt(0,size/2);self.line(*a,*b,stroke=color,line_width=line_width,id=id,role='marker')
        elif kind=='cross':
            for a,b in ((pt(-size/2,-size/2),pt(size/2,size/2)),(pt(-size/2,size/2),pt(size/2,-size/2))):self.line(*a,*b,stroke=color,line_width=line_width,id=id,role='marker')
        elif kind=='crow':
            for offset in (-size/2,0,size/2):self.line(*pt(-size),*pt(0,offset),stroke=color,line_width=line_width,id=id,role='marker')
        else:raise MermaidError(f'Unknown marker {kind}',code='INVALID_GEOMETRY')
        for index in range(start,len(self.commands)):
            command=self.commands[index]
            self.commands[index]=replace(command,style=(*command.style,('marker',kind)))

    def asset(self,resource_id,x,y,w,h,*,kind='image',id='',color=None,style=None):
        self._check()
        if style is not None and style.display=='none':return
        self.session._asset(resource_id,kind,color or self._label_config.text_color)
        box=Box(number(x),number(y),number(w,minimum=0),number(h,minimum=0))
        bounds=box
        if style is not None and style.filter_chain and style.shadow_opacity:
            dx,dy,blur=style.shadow_dx,style.shadow_dy,style.shadow_blur
            bounds=_union((box,Box(box.x+dx-3*blur,box.y+dy-3*blur,box.width+6*blur,box.height+6*blur)))
        self.commands.append(Paint('asset',(resource_id,kind,color,box),style=(('resolved',style),),semantic_id=id,role='asset',bounds=bounds))

    def svg(self,svg,x,y,w,h,*,id='',color=None,style=None):
        if not isinstance(svg,str):raise MermaidError('SVG must be text',code='INVALID_RESOURCE')
        resource='data:image/svg+xml;base64,'+base64.b64encode(svg.encode('utf-8')).decode('ascii')
        self.asset(resource,x,y,w,h,kind='icon',id=id,color=color,style=style)

    def vchart(self,spec,x=0,y=0,*,maps=None,svgs=None,id=''):
        """Draw the real VChart renderer, returning immutable layout metadata.

        The measuring pass supplies actual chart marks to family overlays. The
        command pass draws on the final owner Canvas, keeping vector exports;
        no PNG embedding or reference to a temporary Canvas enters the Scene.
        Source: py_vchart.core.VChart.render/draw_to/public scene metadata.
        """
        self._check()
        from ...vchart_bridge import model_from_spec, scene_for, measure_vchart
        model=model_from_spec(spec)
        scene=scene_for(model,maps=maps,svgs=svgs)
        x,y=number(x),number(y)
        metadata=measure_vchart(scene,backend=self._vchart_backend,resources=self._vchart_resources)
        command=Paint('vchart',(scene,x,y),semantic_id=id,role='chart',
                      bounds=Box(x,y,model.width,model.height))
        self.commands.append(command)
        return metadata

    def finish(self,*,width=None,height=None,padding=None,background=None,layout=None,measured=(),diagnostics=()):
        self._check()
        if getattr(layout,'engine',None)=='mermaid-swimlane' and getattr(layout,'group_data',()):
            from .graph_groups import overlay_swimlane_groups
            self.commands=list(overlay_swimlane_groups(self,layout,tuple(self.commands)))
        bounds=[command.bounds for command in self.commands if command.bounds is not None]
        if width is not None or height is not None:bounds.append(Box(0,0,number(width or 0,minimum=0),number(height or 0,minimum=0)))
        ink=_union(bounds)
        key=self.config.get('_diagramConfigKey',self.diagram.kind)
        section=self.config.get(key,{})
        pad=number(padding if padding is not None else section.get('diagramPadding',self.config.get('diagramPadding',8)),minimum=0)
        width=max(1,math.ceil(ink.width+pad*2));height=max(1,math.ceil(ink.height+pad*2))
        if width>32768 or height>32768 or width*height>64_000_000:raise MermaidError('Scene exceeds canvas budget',code='RENDER_BUDGET')
        return Scene(tuple(self.commands),width,height,ink.x-pad,ink.y-pad,
            background if background is not None else self.config.get('themeVariables',{}).get('background') or 'white',
            immutable_value(layout),immutable_value(measured),tuple(dict.fromkeys((*self.diagram.diagnostics,*self._diagnostics,*self.session._diagnostics,*diagnostics))))

    def _paint_path(self,ctx,path,style,resolved,opacity):
        def paint(value,stops,direction):
            if not stops:return value
            bounds=path.bounds;gx1,gy1,gx2,gy2=direction or resolved.gradient_direction
            gradient=ctx.createLinearGradient(bounds['left']+gx1*bounds['width'],bounds['top']+gy1*bounds['height'],bounds['left']+gx2*bounds['width'],bounds['top']+gy2*bounds['height'])
            for offset,color in stops:gradient.addColorStop(number(offset,minimum=0,maximum=1),color)
            return gradient
        if style['fill'] not in (None,'none','transparent',''):
            ctx.globalAlpha=opacity*(resolved.fill_opacity if resolved else 1)
            ctx.fillStyle=paint(style['fill'],resolved.fill_gradient if resolved else (),resolved.fill_gradient_direction if resolved else None);ctx.fill(path)
        if style['stroke'] not in (None,'none','transparent','') and style['line_width']>0:
            ctx.globalAlpha=opacity*(resolved.stroke_opacity if resolved else 1)
            ctx.strokeStyle=paint(style['stroke'],resolved.stroke_gradient if resolved else (),resolved.stroke_gradient_direction if resolved else None);ctx.stroke(path)

    def _path_shadow(self,ctx,path,style,resolved):
        # Compose the source alpha before recoloring it. A transparent fill or
        # a partially opaque stroke must cast exactly its own silhouette.
        bounds,_=_paint_path_box(path,style['fill'],style['stroke'],style['line_width'],style['dash'],resolved)
        left,top=math.floor(bounds.x)-1,math.floor(bounds.y)-1
        width=max(1,math.ceil(bounds.x+bounds.width)-left+1);height=max(1,math.ceil(bounds.y+bounds.height)-top+1)
        if max(width,height)>32768 or width*height>64_000_000:raise MermaidError('Shadow exceeds canvas budget',code='RENDER_BUDGET')
        surface=self.session._new_canvas(width,height);mask=surface.getContext('2d')
        mask.translate(-left,-top);mask.lineWidth=style['line_width'];mask.setLineDash(list(style['dash']))
        mask.lineCap=resolved.line_cap;mask.lineJoin=resolved.line_join;mask.lineDashOffset=resolved.dash_offset
        self._paint_path(mask,path,style,resolved,1)
        mask.globalAlpha=1;mask.globalCompositeOperation='source-in';mask.fillStyle=resolved.shadow_color
        mask.fillRect(left,top,width,height)
        silhouette=self.session._image_factory(bytes(surface.toBufferSync('png')))
        ctx.save()
        try:
            ctx.globalAlpha=style['opacity']*resolved.shadow_opacity
            ctx.filter=f'blur({resolved.shadow_blur:g}px)' if resolved.shadow_blur else 'none'
            ctx.drawImage(silhouette,left+resolved.shadow_dx,top+resolved.shadow_dy)
        finally:ctx.restore()

    def _draw_commands(self,ctx,commands,tx,ty):
        self._check();trace=[]
        for command in commands:
            ctx.save()
            try:
                if command.kind=='vchart':
                    from ...vchart_bridge import draw_vchart
                    scene,x,y=command.values
                    draw_vchart(scene,ctx.canvas,backend=self._vchart_backend,
                                x=x,y=y,resources=self._vchart_resources)
                    trace.append(DrawEvent('vchart',command.semantic_id,
                        Box(command.bounds.x+tx,command.bounds.y+ty,command.bounds.width,command.bounds.height),
                        resource_id=scene.model.spec()['type']))
                elif command.kind=='path':
                    d,matrix=command.values;style=dict(command.style)
                    path=self.session._path_factory(d).transform(*matrix)
                    ctx.globalAlpha=style['opacity'];ctx.lineWidth=style['line_width'];ctx.setLineDash(list(style['dash']))
                    resolved=style.get('resolved')
                    if resolved is not None:
                        ctx.globalCompositeOperation=resolved.blend_mode
                        ctx.lineCap=resolved.line_cap;ctx.lineJoin=resolved.line_join;ctx.lineDashOffset=resolved.dash_offset
                        if resolved.shadow_opacity>0 and not resolved.filter_chain:
                            self._path_shadow(ctx,path,style,resolved)
                        ctx.filter=self.session._filter_css(resolved)
                    self._paint_path(ctx,path,style,resolved,style['opacity'])
                    trace.append(DrawEvent(command.role,command.semantic_id,Box(command.bounds.x+tx,command.bounds.y+ty,command.bounds.width,command.bounds.height),path=path.transform(1,0,0,1,tx,ty).d,fill=style['fill'],stroke=style['stroke'],stroke_width=style['line_width'],opacity=style['opacity'],brightness=resolved.brightness if resolved else 1,filter_chain=resolved.filter_chain if resolved else (),blend_mode=resolved.blend_mode if resolved else 'source-over',dash=tuple(style['dash']),marker=style.get('marker')))
                elif command.kind=='asset':
                    resource,kind,color=command.values[:3];box=command.values[3] if len(command.values)>3 else command.bounds
                    resolved=dict(command.style).get('resolved')
                    if resolved is not None:
                        ctx.globalAlpha=resolved.paint_opacity;ctx.filter=self.session._filter_css(resolved);ctx.globalCompositeOperation=resolved.blend_mode
                    ctx.drawImage(self.session._asset(resource,kind,color or self._label_config.text_color),box.x,box.y,box.width,box.height)
                    trace.append(DrawEvent(command.role,command.semantic_id,Box(command.bounds.x+tx,command.bounds.y+ty,command.bounds.width,command.bounds.height),resource_id=resource,opacity=resolved.paint_opacity if resolved else 1,brightness=resolved.brightness if resolved else 1,filter_chain=resolved.filter_chain if resolved else (),blend_mode=resolved.blend_mode if resolved else 'source-over'))
                elif command.kind=='text':
                    text,x,y,rotation,clip=command.values
                    if clip is not None:ctx.clip(self.session._path_factory(f'M{clip.x},{clip.y} h{clip.width} v{clip.height} h{-clip.width}Z'))
                    ctx.translate(x,y);ctx.rotate(math.radians(rotation))
                    events=self.session._draw_runs(ctx,text.runs,Box(0,0,text.width,text.height),command.role,command.semantic_id,0,0)
                    angle=math.radians(rotation);co,si=math.cos(angle),math.sin(angle);matrix=(co,si,-si,co,x+tx,y+ty)
                    for event in events:
                        points=tuple(Point(co*p.x-si*p.y+x+tx,si*p.x+co*p.y+y+ty) if index==0 or event.kind not in ('math-glyph','math-path') else p for index,p in enumerate(event.points))
                        box=_mapped(event.box,matrix) if event.box else None
                        screen_clip=Box(clip.x+tx,clip.y+ty,clip.width,clip.height) if clip is not None else None
                        if box is not None and screen_clip is not None:
                            box=_intersection(box,screen_clip)
                            if box.width==0 or box.height==0:continue
                        trace.append(replace(event,box=box,points=points,clip=screen_clip))
                else:raise MermaidError(f'Unknown display-list command {command.kind}',code='INVALID_SCENE')
            finally:ctx.restore()
        return trace

    def encode(self,scene,*,format='png',export_options=None):
        self._check()
        if isinstance(scene,FlowchartScene):
            result=self.session.render(scene.flowchart,scene.measured,scene.layout,
                annotations=scene.annotations,format=format,export_options=export_options,
                group_overrides=scene.group_overrides,draw_group_override=self._draw_commands)
            return DiagramRenderResult(result.data,result.width,result.height,result.mime,self.diagram,
                result.measured,result.layout,result.backend,
                tuple(dict.fromkeys((*self.diagram.diagnostics,*result.diagnostics))),result.trace,scene)
        format='jpg' if format=='jpeg' else format
        if format not in ('png','jpg','webp','svg','pdf'):raise MermaidError('Unsupported static export format',code='UNSUPPORTED_FORMAT')
        options=export_options or ExportOptions()
        if not isinstance(options,ExportOptions) or isinstance(options.density,bool) or not isinstance(options.density,int) or options.density<1 or isinstance(options.quality,bool) or not isinstance(options.quality,(int,float)) or not math.isfinite(options.quality) or not 0<=options.quality<=1 or not isinstance(options.outline,bool) or not isinstance(options.downsample,bool) or (options.matte is not None and not isinstance(options.matte,str)):
            raise MermaidError('Invalid export options',code='INVALID_EXPORT_OPTIONS')
        width,height=math.ceil(scene.width),math.ceil(scene.height)
        if max(width,height)>32768 or width*height*(options.density**2 if format in ('png','jpg','webp') else 1)>64_000_000:raise MermaidError('Export exceeds canvas budget',code='RENDER_BUDGET')
        canvas=self.session._new_canvas(width,height);ctx=canvas.getContext('2d');trace=[]
        if scene.background not in ('none','transparent','',None):ctx.fillStyle=scene.background;ctx.fillRect(0,0,width,height)
        tx,ty=-scene.origin_x,-scene.origin_y
        ctx.translate(tx,ty)
        trace.extend(self._draw_commands(ctx,scene.commands,tx,ty))
        encoded={field.name:getattr(options,field.name) for field in fields(options) if getattr(options,field.name) is not None}
        try:data=bytes(canvas.toBufferSync(format,encoded))
        except Exception as exc:raise MermaidError(f'Canvas {format} export failed: {exc}',code='EXPORT_ERROR') from exc
        density=options.density if format in ('png','jpg','webp') else 1
        return DiagramRenderResult(data,width*density,height*density,{'png':'image/png','jpg':'image/jpeg','webp':'image/webp','svg':'image/svg+xml','pdf':'application/pdf'}[format],
            self.diagram,scene.measured,scene.layout,tuple((str(k),str(v)) for k,v in sorted(canvas.engine.items())),scene.diagnostics,tuple(trace),scene)
