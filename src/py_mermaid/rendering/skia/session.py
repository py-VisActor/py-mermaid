"""Classic flowchart owner-thread Canvas measurement, drawing and PNG encoding.

Only this adapter imports py_skia_canvas. Coordinates are logical px and all
metrics, rectangles, route sections and text remain Python-owned value data.
"""
from __future__ import annotations

import math
import re
import threading
from dataclasses import replace
from ...geometry import arrow_polygon
from ...geometry.shapes import shape_geometry
from ...geometry.rough import rough_path
from ...model.flowchart import (Box, DrawEvent, Flowchart, FlowLayout, MeasuredNode,
                               MeasuredAnnotations, MeasuredGroup, MeasuredEdgeLabel,
                               MeasuredLine, MeasuredTextRun, MeasuredTitle, ResolvedStyle,
                               MermaidError, Point, RenderResult, MeasuredAsset, ExportOptions, ResourceBundle)
from ..labels import measure_label
from ..styles import resolve_style,resolve_inline_svg_style
from ..styles.flowchart import resolve_shape_part_style


class CanvasSession:
    """One calling thread owns all Canvas/Context instances in this session.

    auto retains the Canvas default; cpu uses its public GPU setter; gpu verifies
    that the actual selected renderer is GPU and never accepts a CPU fallback.
    No native handles are returned or put into render results/trace.
    """

    def __init__(self, backend: str = "auto", resources: ResourceBundle | None = None):
        if backend not in {"auto", "cpu", "gpu"}:
            raise MermaidError("backend must be auto, cpu or gpu", code="INVALID_BACKEND")
        from py_skia_canvas import Canvas, Path2D, Image, FontLibrary, __version__
        from ...resources import ResourceStore
        if __version__ != "0.1.0a18":
            raise MermaidError(f"Expected py-skia-canvas 0.1.0a18, found {__version__}", code="DEPENDENCY_VERSION")
        self._owner = threading.get_ident()
        self._backend = backend
        self._resources=ResourceStore(resources)
        self._image_factory=Image;self._images={}
        for family,path,digest in self._resources.fonts:FontLibrary.use(family,path)
        self._canvas_factory = Canvas
        self._path_factory = Path2D
        self._measure_canvas = self._new_canvas(1, 1)
        self._context = self._measure_canvas.getContext("2d")
        self.trace: tuple[DrawEvent, ...] = ()
        self._diagnostics: list[str] = []
        self._math_boxes = {}
        self._math_sources = {}
        self._math_ink = {}
        self._request_diagram: Flowchart | None = None
        self._control_diagram = None
        self._control_labels = {}

    def _prepare_control_labels(self,diagram):
        if self._control_diagram is diagram:return
        self._control_diagram=diagram;self._control_labels={}
        if not diagram.config.html_labels:return
        from ...geometry.shapes import LABELLESS_SHAPES
        from ...geometry.shape_registry import canonical_shape
        labels=[('node-label',n.id,n.raw_label if n.raw_label is not None else n.label,n.label_kind)
            for n in diagram.nodes if canonical_shape(n.shape) not in LABELLESS_SHAPES]
        labels += [('group-title',g.id,g.raw_label if g.raw_label is not None else g.label,g.label_kind) for g in diagram.groups]
        labels += [('edge-label',e.id,e.raw_label if e.raw_label is not None else e.label,e.label_kind) for e in diagram.edges if e.label]
        if sum(bool(re.search(r'<input\b',text,re.I) and re.search(r'\bradio\b',text,re.I)) for _,_,text,_ in labels)<2:return
        from ..labels.rich import prepare_label_markup
        from ..labels.controls.semantic import normalize_control_labels
        prepared=[prepare_label_markup(text,label_kind,diagram.config) for _,_,text,label_kind in labels]
        normalized=normalize_control_labels([entry[0] for entry in prepared])
        self._control_labels={(kind,identifier):(markup,*entry[1:]) for (kind,identifier,_,_),markup,entry in zip(labels,normalized,prepared)}

    @staticmethod
    def _filter_css(paint,extra=''):
        chain=tuple(paint.filter_chain)
        if not chain and paint.brightness!=1:chain=(f'brightness({paint.brightness:g})',)
        return ' '.join((*((extra,) if extra else ()),*chain)) or 'none'

    @staticmethod
    def _filter_ink(box,run):
        if run.filter_shadow is None:return box
        dx,dy,blur=run.filter_shadow;left=min(box.x,box.x+dx-3*blur);top=min(box.y,box.y+dy-3*blur)
        right=max(box.x+box.width,box.x+box.width+dx+3*blur);bottom=max(box.y+box.height,box.y+box.height+dy+3*blur)
        return Box(left,top,right-left,bottom-top)

    def _math_atom(self, tex, style, position=0):
        self._check_owner()
        from ..labels.math import cache_key, typeset_formula
        key=cache_key(tex,style)
        if key not in self._math_boxes:
            from py_katex.model import ResourceBundle as MathResources,FontResource as MathFont
            from py_katex.resources import image_resource
            from pathlib import Path as ResourcePath
            images=tuple(image_resource(identifier,data) for identifier,data in self._resources.images.items())
            fonts=tuple(MathFont(family,ResourcePath(path).read_bytes()) for family,path,digest in self._resources.fonts)
            self._math_boxes[key]=typeset_formula(tex,style,position,resources=MathResources(images),fallback_fonts=fonts)
            self._math_sources[key]=tex
        box=self._math_boxes[key]
        self._diagnostics.extend('MATH_'+item.code+': '+item.message for item in box.diagnostics)
        return key,box.width,box.height,box.depth

    def _draw_math(self, context, run, box, kind, semantic_id, tx, ty):
        from py_katex.canvas import draw, glyph_font_alias
        from py_katex.model import Glyph,Rule,Path,ImageCommand,CommandGroup
        if run.math_key not in self._math_boxes:
            raise MermaidError('Mathematical measurement belongs to another session',code='MATH_CACHE_MISSING')
        if run.filter_chain or run.brightness!=1:
            # An inner KaTeX CommandGroup may own a blur/filter. Compose the
            # whole mathematical element first so its local filter cannot
            # replace the source host CSS filter on the outer element.
            plain=replace(run,brightness=1,filter_chain=(),filter_shadow=None)
            ink=self._ink_box(plain,box)
            left=min(ink.x,box.x+run.x)-1;top=min(ink.y,box.y+run.baseline-run.ascent)-1
            right=max(ink.x+ink.width,box.x+run.x+run.width)+1
            bottom=max(ink.y+ink.height,box.y+run.baseline+run.descent)+1
            width=max(1,math.ceil(right-left));height=max(1,math.ceil(bottom-top))
            if max(width,height)>32768 or width*height>64_000_000:raise MermaidError('Filtered math exceeds canvas budget',code='RENDER_BUDGET')
            surface=self._new_canvas(width,height);target=surface.getContext('2d');target.translate(-left,-top)
            events=self._draw_math(target,plain,box,kind,semantic_id,tx,ty)
            context.save()
            try:
                context.globalAlpha=1;context.filter=self._filter_css(run)
                context.drawCanvas(surface,left,top)
            finally:context.restore()
            return events
        formula=self._math_boxes[run.math_key]
        x=box.x+run.x;baseline=box.y+run.baseline
        context.save()
        try:
            context.globalAlpha=run.opacity
            if run.background not in {'','none','transparent'}:
                context.fillStyle=run.background
                context.fillRect(x,baseline-run.ascent,run.width,run.ascent+run.descent)
            for dx,dy,blur,color in reversed(run.text_shadows):
                from ..labels.math import recolor_math
                shadow=recolor_math(formula,color)
                context.save()
                try:
                    context.filter=self._filter_css(run,f'blur({blur:g}px)' if blur else '')
                    draw(context,shadow,x+dx,baseline+dy)
                finally:context.restore()
            draw(context,formula,x,baseline)
        finally:context.restore()
        events=[DrawEvent('math',semantic_id,Box(x+tx,baseline+ty-run.ascent,run.width,run.ascent+run.descent),
            self._math_sources[run.math_key],(Point(x+tx,baseline+ty),),font_size=run.font_size,color=run.color,
            resource_id=run.math_key,opacity=run.opacity)]
        def trace_commands(commands,matrix=(1,0,0,1,x+tx,baseline+ty),opacity=run.opacity):
            def point(xx,yy):
                a,b,c,d,e,f=matrix;return Point(a*xx+c*yy+e,b*xx+d*yy+f)
            def bounds(xx,yy,width,height):
                pts=(point(xx,yy),point(xx+width,yy),point(xx,yy+height),point(xx+width,yy+height))
                return Box(min(p.x for p in pts),min(p.y for p in pts),max(p.x for p in pts)-min(p.x for p in pts),max(p.y for p in pts)-min(p.y for p in pts))
            for command in commands:
                if isinstance(command,Glyph):
                    events.append(DrawEvent('math-glyph',semantic_id,text=command.text,
                        points=(point(command.x,command.y),Point(command.scale_x,1)),
                        font_family=glyph_font_alias(command),font_size=command.size,color=command.color,opacity=opacity,
                        font_style=command.font_style or (command.font_resource.style if command.font_resource else command.font.split('|')[1] if command.font.startswith('system:') and '|' in command.font else 'italic' if 'Italic' in command.font else 'normal'),
                        font_weight=command.font_weight or (command.font_resource.weight if command.font_resource else command.font.split('|')[2] if command.font.startswith('system:') and command.font.count('|')>=2 else '700' if 'Bold' in command.font else '400')))
                elif isinstance(command,Rule):
                    events.append(DrawEvent('math-rule',semantic_id,bounds(command.x,command.y,command.width,command.height),fill=command.color,opacity=opacity))
                elif isinstance(command,Path):
                    events.append(DrawEvent('math-path',semantic_id,text=command.d,
                        points=(point(command.x,command.y),Point(command.scale_x,command.scale_y)),
                        fill=command.color if not command.stroke_width else None,stroke=command.color if command.stroke_width else None,
                        stroke_width=command.stroke_width,opacity=opacity))
                elif isinstance(command,ImageCommand):
                    events.append(DrawEvent('math-image',semantic_id,bounds(command.x,command.y,command.width,command.height),resource_id=command.resource.key,opacity=opacity*command.opacity))
                elif isinstance(command,CommandGroup):
                    a,b,c,d,e,f=matrix;g,h,i,j,k,l=command.matrix
                    g*=command.scale_x;i*=command.scale_x;k=command.x+k*command.scale_x
                    h*=command.scale_y;j*=command.scale_y;l=command.y+l*command.scale_y
                    child=(a*g+c*h,b*g+d*h,a*i+c*j,b*i+d*j,a*k+c*l+e,b*k+d*l+f)
                    events.append(DrawEvent('math-group',semantic_id,opacity=opacity*command.opacity))
                    trace_commands(command.commands,child,opacity*command.opacity)
        trace_commands(formula.commands)
        events.extend(DrawEvent('math-diagnostic',semantic_id,text=item.code+': '+item.message) for item in formula.diagnostics)
        return events

    def _check_owner(self) -> None:
        if threading.get_ident() != self._owner:
            raise MermaidError("CanvasSession must be used on its creating thread", code="THREAD_OWNERSHIP")

    def _new_canvas(self, width: int, height: int):
        self._check_owner()
        canvas = self._canvas_factory(width, height)
        if self._backend == "cpu":
            canvas.gpu = False
        if self._backend == "gpu" and canvas.engine.get("renderer") != "GPU":
            raise MermaidError("GPU required but Canvas selected a CPU renderer", code="GPU_UNAVAILABLE")
        return canvas

    @staticmethod
    def _text_state(context, diagram: Flowchart) -> None:
        config = diagram.config
        # Mermaid's CSS declaration default includes a trailing semicolon;
        # Canvas.font accepts the font value rather than a CSS declaration.
        family = config.font_family.rstrip().removesuffix(";").rstrip()
        context.font = f"{config.font_size:g}px {family}"
        context.textAlign = "center"
        context.textBaseline = "alphabetic"
        context.direction = "ltr"
        context.textWrap = False

    def measure(self, diagram: Flowchart) -> tuple[MeasuredNode, ...]:
        self._check_owner()
        self._diagnostics=[]
        self._request_diagram=diagram
        self._prepare_control_labels(diagram)
        measured=[]
        for node in diagram.nodes:
            style=resolve_style(diagram,'node-label',node.id)
            from ...geometry.shapes import LABELLESS_SHAPES
            from ...geometry.shape_registry import canonical_shape
            labelless=canonical_shape(node.shape) in LABELLESS_SHAPES
            label='' if labelless else (node.raw_label if node.raw_label is not None else node.label)
            try:
                from ...config.values import thaw_value
                metadata=thaw_value(node.metadata) if node.metadata else {}
                asset_id=metadata.get('img') or metadata.get('icon')
                asset_kind='image' if metadata.get('img') else 'icon'
                natural=self._asset_size(str(asset_id),asset_kind) if asset_id else None
                minimum=0 if node.shape in {'circle','doublecircle'} else diagram.config.min_node_width
                wrap_width=diagram.config.wrapping_width
                if asset_id and label:
                    from ...resources.geometry import asset_layout
                    *_,asset_box=asset_layout(node.shape,1,1,diagram.config,metadata,natural)
                    minimum=max(diagram.config.wrapping_width,asset_box.width)-4
                    wrap_width=max(1,wrap_width-4)
                width,height,lines,runs=measure_label(label,node.label_kind,diagram.config,style,
                    self._measure_span,width=wrap_width,min_width=minimum,
                    tag_style=self._tag_style(diagram,'node-label',node.id),diagnostics=self._diagnostics,asset_loader=self._inline_asset(diagram),svg_style=self._svg_style(diagram,'node-label',node.id),math_loader=self._math_atom,_prepared=self._control_labels.get(('node-label',node.id)))
                if labelless or (asset_id and not label):
                    width=height=0.;lines=();runs=()
                if asset_id and label:
                    width+=4;height+=4
                    runs=tuple(replace(run,x=run.x+2,baseline=run.baseline+2,asset_box=Box(run.asset_box.x+2,run.asset_box.y+2,run.asset_box.width,run.asset_box.height) if run.asset_box else None) for run in runs)
                shape=shape_geometry(node.shape,width,height,diagram.config,metadata=node.metadata,asset_size=natural,direction=self._node_direction(diagram,node))
            except MermaidError as error:
                if error.span is None:error.span=node.label_span or node.span
                raise
            measured.append(MeasuredNode(node.id,shape.width,shape.height,width,height,lines,
                                          shape.label_box,shape.outline,shape.details,runs,
                                          getattr(shape,'parts',()),self._node_assets(metadata,natural,shape,asset_id,asset_kind,diagram.config,node.shape),shape.paint_outline))
        return tuple(measured)

    @staticmethod
    def _edge_dash(diagram,edge,route,style):
        compiled=list(diagram.default_edge_styles)+list(edge.styles)
        for definition in diagram.class_definitions:
            if definition.name in edge.classes or definition.name=='default':compiled.extend(definition.styles)
        animated=edge.animate is True or bool(edge.animation) or any('animation' in declaration for declaration in compiled)
        explicit=any('stroke-dasharray' in declaration for declaration in compiled) or 'stroke-dasharray' in diagram.config.theme_css
        if diagram.config.look!='neo' or animated or explicit or not route.path:return style.dash
        from ...geometry.path_geometry import flatten_path
        length=sum(math.hypot(b.x-a.x,b.y-a.y) for contour in flatten_path(route.path) for a,b in zip(contour,contour[1:]))
        offsets={'none':0,'point':4,'circle':12.5,'cross':12.5}
        start,end=offsets[edge.marker_start],offsets[edge.marker_end]
        if edge.stroke=='dotted':return (0,start,*((2,2)*max(0,math.floor((length-start-end)/4))),end)
        # A negative source SVG dash declaration is invalid and falls back to
        # the already-computed pattern; do not invent a negative Canvas length.
        return style.dash if length<start+end else (0,start,length-start-end,end)

    @staticmethod
    def _node_direction(diagram,node):
        groups={group.id:group for group in diagram.groups};parent=node.parent_id;seen=set()
        while parent in groups and parent not in seen:
            seen.add(parent);group=groups[parent]
            if group.direction:return group.direction
            parent=group.parent_id
        return diagram.direction

    def _asset(self,identifier:str,kind='image',color=None):
        self._check_owner()
        key=(kind,identifier,color)
        if key not in self._images:
            from ...resources import inline_image_data
            data=inline_image_data(identifier) if identifier.startswith('data:') else self._resources.data(identifier,kind)
            if kind=='icon' and color:
                # Iconify SVG currentColor resolves against the enclosing node/text.
                from ...config.colors import channels, rgba
                from ...resources import validate_svg
                red,green,blue,alpha=channels(color)
                tint=rgba(red*255,green*255,blue*255,alpha).encode('ascii')
                data=re.sub(rb'\bcurrentcolor\b',lambda match:tint,data,flags=re.I)
                validate_svg(data) # Verify the exact bytes passed to the decoder.
            try:self._images[key]=self._image_factory(data)
            except MermaidError:raise
            except Exception as exc:raise MermaidError(f'Cannot decode resource: {identifier}',code='RESOURCE_DECODE') from exc
            img=self._images[key]
            if img.width<=0 or img.height<=0 or img.width*img.height>64_000_000:
                raise MermaidError('Decoded image exceeds budget',code='RESOURCE_BUDGET')
        return self._images[key]

    def _asset_size(self,identifier,kind):
        img=self._asset(identifier,kind);return(float(img.width),float(img.height))

    def _inline_asset(self,diagram):
        def load(identifier,kind,attrs,style,image_only):
            width,height=self._asset_size(identifier,'image' if kind=='control-image' else kind)
            if kind=='control-image':return(width,height)
            if kind=='icon':return(style.font_size,style.font_size)
            if kind=='svg':return(width,height)
            target=diagram.config.site_font_size*5 if image_only else diagram.config.wrapping_width
            # configureLabelImages defines inline image width on the label container.
            return(target,target*height/width)
        return load

    @staticmethod
    def _node_assets(metadata,natural,shape,identifier,kind,config,shape_kind):
        if not identifier or not natural:return ()
        from ...resources.geometry import asset_layout
        _,_,_,_,rect=asset_layout(shape_kind,shape.label_box.width,shape.label_box.height,config,metadata,natural)
        return(MeasuredAsset(str(identifier),rect,kind,fit='fill'),)

    @staticmethod
    def _svg_style(diagram,kind,identifier):
        return lambda tag,base,classes=(),parent=None:resolve_inline_svg_style(diagram,kind,identifier,
            tag=tag,base=base,css_classes=classes,inherited_base=parent)

    @staticmethod
    def _tag_style(diagram: Flowchart,kind: str,identifier: str):
        return lambda tag,base,classes=(),parent=None:resolve_style(diagram,kind,identifier,
            tag=tag if diagram.config.html_labels else 'tspan',base=base,css_classes=classes,inherited_base=parent)

    @staticmethod
    def _run_font(context,style) -> None:
        family=style.font_family.rstrip().removesuffix(';').rstrip()
        # a18 treats a later ambiguous `normal` token as font-style reset.
        # Numeric CSS weights preserve an earlier italic/oblique request.
        weight={'normal':'400','bold':'700'}.get(style.font_weight,style.font_weight)
        context.font=f'{style.font_style} {weight} {style.font_size:g}px {family}'
        context.textAlign='left';context.textBaseline='alphabetic';context.direction=style.direction;context.textWrap=False
        context.textDecoration='none'
        context.letterSpacing=style.letter_spacing;context.wordSpacing=style.word_spacing

    def _measure_span(self,text: str,style: ResolvedStyle):
        self._check_owner()
        self._run_font(self._context,style)
        return self._context.measureText(text)

    def measure_annotations(self, diagram: Flowchart) -> MeasuredAnnotations:
        self._check_owner()
        self._prepare_control_labels(diagram)
        if self._request_diagram is not diagram:
            self._diagnostics=[];self._request_diagram=diagram
        groups = []
        edge_labels = []
        for group in diagram.groups:
            style=resolve_style(diagram,'group-title',group.id)
            width,height,lines,runs=measure_label(group.raw_label if group.raw_label is not None else group.label,group.label_kind,diagram.config,style,
                self._measure_span,width=math.inf,tag_style=self._tag_style(diagram,'group-title',group.id),diagnostics=self._diagnostics,asset_loader=self._inline_asset(diagram),svg_style=self._svg_style(diagram,'group-title',group.id),math_loader=self._math_atom,_prepared=self._control_labels.get(('group-title',group.id)))
            groups.append(MeasuredGroup(group.id,width,height,lines,runs))
        for edge in diagram.edges:
            if edge.label:
                style=resolve_style(diagram,'edge-label',edge.id)
                width,height,lines,runs=measure_label(edge.raw_label if edge.raw_label is not None else edge.label,edge.label_kind,diagram.config,style,
                    self._measure_span,width=diagram.config.edge_label_wrapping_width,
                    tag_style=self._tag_style(diagram,'edge-label',edge.id),diagnostics=self._diagnostics,asset_loader=self._inline_asset(diagram),svg_style=self._svg_style(diagram,'edge-label',edge.id),math_loader=self._math_atom,_prepared=self._control_labels.get(('edge-label',edge.id)))
                edge_labels.append(MeasuredEdgeLabel(edge.id,width,height,lines,runs))
        title=None
        if diagram.title:
            style=resolve_style(diagram,'title')
            if style.display=='none':return MeasuredAnnotations(tuple(groups),tuple(edge_labels),None,title_suppressed=True)
            # insertTitle uses SVG .text(), not HTML, with one alphabetic baseline.
            text=re.sub(r'\s+',' ',diagram.title)
            if style.text_transform=='uppercase':text=text.upper()
            elif style.text_transform=='lowercase':text=text.lower()
            elif style.text_transform=='capitalize':text=re.sub(r'\b\w',lambda m:m[0].upper(),text)
            metrics=self._measure_span(text,style)
            ascent=max(0,float(metrics.actualBoundingBoxAscent));descent=max(0,float(metrics.actualBoundingBoxDescent))
            ink_left=float(metrics.actualBoundingBoxLeft);ink_right=float(metrics.actualBoundingBoxRight)
            advance=float(metrics.width);left=min(0,-ink_left);width=max(advance,ink_right)-left
            height=ascent+descent
            run=MeasuredTextRun(text,-left,ascent,advance,ascent,descent,style.font_family.rstrip().removesuffix(';').rstrip(),style.font_size,
                                style.font_weight,style.font_style,style.text_color,style.decoration,style.background,
                                ink_left,ink_right,style.paint_opacity*style.fill_opacity,style.direction,
                                letter_spacing=style.letter_spacing,word_spacing=style.word_spacing,text_shadows=style.text_shadows,
                                brightness=style.brightness,filter_chain=style.filter_chain,
                                filter_shadow=(style.shadow_dx,style.shadow_dy,style.shadow_blur) if style.filter_chain and style.shadow_opacity else None)
            title=MeasuredTitle(width,height,ascent,descent,(MeasuredLine(text,width,ascent,descent),),(run,),style.text_anchor)
        return MeasuredAnnotations(tuple(groups), tuple(edge_labels),title)

    @staticmethod
    def _arrow(points: tuple[Point, ...]) -> tuple[Point, Point, Point]:
        try:
            return arrow_polygon(points, length=10, width=10)
        except ValueError as error:
            raise MermaidError("Edge has no nonzero terminal route segment", code="INVALID_LAYOUT") from error

    @staticmethod
    def _shadow_for_shape(shape: str) -> bool:
        # Fixed styles.ts applies drop-shadow to circles too. The nearby
        # filter:none rule applies only to .neo-line path, not to circle.
        return True

    def _draw_shadow(self, context, box: Box, diagram: Flowchart, *, outline: str = "",
                     stroke_width: float | None = None, paint: ResolvedStyle | None = None) -> Box:
        config = diagram.config
        stroke_width = config.node_stroke_width if stroke_width is None else stroke_width
        opacity=(paint.shadow_opacity*paint.paint_opacity) if paint is not None else config.shadow_opacity
        dx=paint.shadow_dx if paint is not None else config.shadow_offset_x
        dy=paint.shadow_dy if paint is not None else config.shadow_offset_y
        blur=paint.shadow_blur if paint is not None else 0
        color=paint.shadow_color if paint is not None else '#000000'
        half = stroke_width/2
        shadow_box = Box(box.x+dx-half-3*blur, box.y+dy-half-3*blur,
                         box.width+stroke_width+6*blur, box.height+stroke_width+6*blur)
        simple_opaque=(paint is None or (paint.fill_opacity==paint.stroke_opacity==1
                      and (paint.fill=='white' or re.fullmatch(r'#[0-9a-fA-F]{6}',paint.fill))))
        if not outline and simple_opaque and not blur:
            context.save();context.globalAlpha=opacity;context.fillStyle=color
            context.fillRect(shadow_box.x, shadow_box.y, shadow_box.width, shadow_box.height)
            context.restore()
        else:
            # Public owner-thread Canvas snapshot composes fill+stroke into a
            # single opaque silhouette, then applies shadow alpha exactly once.
            # This handles concave paths/rings without a bbox-shaped fake shadow.
            margin = half+1
            surface = self._new_canvas(math.ceil(box.width+2*margin), math.ceil(box.height+2*margin))
            mask = surface.getContext("2d")
            mask.translate(margin, margin)
            path = self._path_factory(outline or f'M 0 0 H {box.width:g} V {box.height:g} H 0 Z')
            bounds = path.bounds
            shadow_box = Box(box.x+dx+bounds["left"]-half-3*blur,
                             box.y+dy+bounds["top"]-half-3*blur,
                             bounds["width"]+stroke_width+6*blur,bounds["height"]+stroke_width+6*blur)
            mask.fillStyle = paint.fill if paint is not None and paint.fill not in {'none',''} else 'transparent'
            mask.strokeStyle = self._stroke_paint(mask,paint,Box(0,0,box.width,box.height)) if paint is not None else 'black'
            if paint is None:mask.fillStyle=mask.strokeStyle='black'
            mask.lineWidth = stroke_width
            mask.globalAlpha=paint.fill_opacity if paint is not None else 1
            mask.fill(path)
            mask.globalAlpha=paint.stroke_opacity if paint is not None else 1
            if stroke_width:mask.stroke(path)
            mask.globalAlpha=1
            mask.globalCompositeOperation='source-in'
            mask.fillStyle=color
            mask.fillRect(-margin,-margin,surface.width,surface.height)
            context.save()
            context.globalAlpha = opacity
            context.filter=f'blur({blur:g}px)' if blur else 'none'
            # drawCanvas replays picture blend commands into the destination.
            # Resolve source-in alpha on the owner surface first, so it cannot
            # use the opaque main canvas as its destination mask.
            silhouette=self._image_factory(bytes(surface.toBufferSync('png')))
            context.drawImage(silhouette, box.x+dx-margin,box.y+dy-margin)
            context.restore()
        return shadow_box

    def _paint_rough(self,context,geometry,style,box,*,outline_fill=None):
        context.save();context.translate(box.x,box.y)
        context.lineCap=style.line_cap;context.lineJoin=style.line_join;context.lineDashOffset=style.dash_offset
        if geometry.fill_path and style.fill not in {'none','transparent',''}:
            context.globalAlpha=style.paint_opacity*style.fill_opacity
            if geometry.fill_style=='solid':
                context.fillStyle=style.fill;context.fill(self._path_factory(geometry.fill_path))
            else:
                context.strokeStyle=style.hachure_color or style.fill;context.lineWidth=geometry.fill_width
                context.stroke(self._path_factory(geometry.fill_path))
        if outline_fill and style.fill not in {'none','transparent',''}:
            # These source .node ellipse paths acquire CSS fill even though
            # RoughJS set presentation fill=none. Its final continuous ellipse
            # closes implicitly and covers prior hachure. Our generic arc
            # stroke is segmented, so fill the same pure closed shape outline.
            context.globalAlpha=style.paint_opacity*style.fill_opacity;context.fillStyle=style.fill
            context.fill(self._path_factory(outline_fill))
        context.strokeStyle=self._stroke_paint(context,style,Box(0,0,box.width,box.height))
        context.lineWidth=style.stroke_width;context.globalAlpha=style.paint_opacity*style.stroke_opacity
        context.setLineDash(list(style.dash))
        if geometry.stroke_path and style.stroke_width:context.stroke(self._path_factory(geometry.stroke_path))
        context.restore()

    @staticmethod
    def _stroke_paint(context,style: ResolvedStyle,box: Box):
        if style.stroke_gradient:
            gradient=context.createLinearGradient(box.x,box.y,box.x+box.width,box.y)
            for offset,color in style.stroke_gradient:gradient.addColorStop(offset,color)
            return gradient
        return style.stroke if style.stroke not in {'none',''} else 'transparent'

    @staticmethod
    def _trace_stroke(style: ResolvedStyle) -> str:
        if style.stroke_gradient:
            return 'linear-gradient('+','.join(f'{offset:g}:{color}' for offset,color in style.stroke_gradient)+')'
        return style.stroke

    def _ink_box(self, run: MeasuredTextRun, box: Box) -> Box:
        if run.control is not None:
            return self._filter_ink(Box(box.x+run.x,box.y+run.baseline-run.control.baseline,run.control.width,run.control.height),run)
        if run.asset_box is not None:return self._filter_ink(Box(box.x+run.asset_box.x,box.y+run.asset_box.y,run.asset_box.width,run.asset_box.height),run)
        top=run.baseline-run.ascent;bottom=run.baseline+run.descent
        if 'underline' in run.decoration:bottom=max(bottom,run.baseline+.22*run.font_size)
        if 'overline' in run.decoration:top=min(top,run.baseline-run.font_size)
        left=box.x+run.x-run.ink_left;right=left+max(0,run.ink_left+run.ink_right)
        top+=box.y;bottom+=box.y
        if run.kind=='math':
            if run.math_key not in self._math_boxes:raise MermaidError('Mathematical measurement belongs to another session',code='MATH_CACHE_MISSING')
            if run.math_key not in self._math_ink:
                from py_katex.canvas import ink_bounds
                self._math_ink[run.math_key]=ink_bounds(self._math_boxes[run.math_key],self._context)
            ink=self._math_ink[run.math_key]
            if ink is not None:
                origin_x=box.x+run.x;baseline=box.y+run.baseline
                left=min(left,origin_x+ink[0]);top=min(top,baseline+ink[1]);right=max(right,origin_x+ink[2]);bottom=max(bottom,baseline+ink[3])
        base=(left,top,right,bottom)
        if run.text_stroke_width and run.text_stroke_color:
            margin=run.text_stroke_width/2
            left-=margin;right+=margin;top-=margin;bottom+=margin
        for dx,dy,blur,color in run.text_shadows:
            left=min(left,base[0]+dx-3*blur);top=min(top,base[1]+dy-3*blur)
            right=max(right,base[2]+dx+3*blur);bottom=max(bottom,base[3]+dy+3*blur)
        return self._filter_ink(Box(left,top,max(0,right-left),max(0,bottom-top)),run)

    @staticmethod
    def _fill_decorated_text(context,run,x,baseline,*,color=None):
        """Adapt CSS decoration lines to the public Canvas shorthand.

        Canvas requires an explicit decoration color and consumes one line per
        descriptor. Additional transparent-glyph passes paint only the other
        decoration lines; glyph opacity is applied exactly once.
        """
        color=color or run.color or '#000000'
        lines=tuple(dict.fromkeys(part for part in run.decoration.split() if part in ('underline','overline','line-through')))
        context.fillStyle=color
        paint=str(context.fillStyle)
        context.textDecoration=f'{lines[0]} {paint}' if lines else 'none'
        context.fillText(run.text,x,baseline)
        if len(lines)>1:
            context.save()
            try:
                context.fillStyle='transparent'
                for line in lines[1:]:
                    context.textDecoration=f'{line} {paint}'
                    context.fillText(run.text,x,baseline)
            finally:context.restore()

    def _text_shadows(self,context,run,x,baseline):
        if not run.text_shadows or not run.text:return
        ink=self._ink_box(replace(run,x=0,baseline=0,text_shadows=()),Box(0,0,0,0))
        pad=2;w=max(1,math.ceil(ink.width+2*pad));h=max(1,math.ceil(ink.height+2*pad))
        if w*h>64_000_000:raise MermaidError('Text shadow exceeds budget',code='RENDER_BUDGET')
        for dx,dy,blur,color in reversed(run.text_shadows):
            surface=self._new_canvas(w,h);mask=surface.getContext('2d');self._run_font(mask,run)
            self._fill_decorated_text(mask,run,pad-ink.x,pad-ink.y,color=color)
            context.save();context.globalAlpha=run.opacity;context.filter=self._filter_css(run,f'blur({blur:g}px)' if blur else '')
            context.drawCanvas(surface,x+ink.x-pad+dx,baseline+ink.y-pad+dy);context.restore()

    def _draw_runs(self, context, runs: tuple[MeasuredTextRun,...], box: Box, kind: str,
                   semantic_id: str, tx: float, ty: float) -> list[DrawEvent]:
        events=[]
        for run in runs:
            if run.control is not None:
                from .controls import paint_control
                x=box.x+run.x;y=box.y+run.baseline-run.control.baseline
                context.save()
                try:
                    context.globalAlpha=run.opacity
                    context.globalCompositeOperation=run.blend_mode
                    context.filter=self._filter_css(run)
                    def paint_runs(children,cx,cy):
                        nested=tuple(replace(child,opacity=child.opacity*run.opacity,
                            filter_chain=run.filter_chain+child.filter_chain,
                            brightness=run.brightness*child.brightness) for child in children)
                        return self._draw_runs(context,nested,Box(cx,cy,0,0),kind,semantic_id,0,0)
                    def paint_image(identifier,ix,iy,iw,ih):
                        context.drawImage(self._asset(identifier,'image',run.color),ix,iy,iw,ih)
                    drawn=paint_control(context,run.control,x,y,paint_runs=paint_runs,paint_image=paint_image)
                    def moved(rect):
                        return None if rect is None else Box(rect.x+tx,rect.y+ty,rect.width,rect.height)
                    for event in drawn:
                        nested=bool(event.semantic_id)
                        events.append(replace(event,semantic_id=semantic_id,box=moved(event.box),clip=moved(event.clip),
                            control_id=event.control_id or run.control.spec.attr('id') or None,
                            points=tuple(Point(point.x+tx,point.y+ty) for point in event.points),
                            opacity=event.opacity,
                            brightness=run.brightness if not nested else event.brightness,
                            filter_chain=run.filter_chain if not nested else event.filter_chain,
                            blend_mode=run.blend_mode if not nested else event.blend_mode))
                    ink=self._ink_box(run,box)
                    events.append(DrawEvent('control',semantic_id,moved(ink),points=(Point(x+tx,y+ty),),resource_id=run.control.spec.tag+':'+run.control.spec.input_type,
                        control_id=run.control.spec.attr('id') or None,
                        opacity=run.opacity,brightness=run.brightness,filter_chain=run.filter_chain,blend_mode=run.blend_mode))
                finally:context.restore()
                continue
            if run.kind=='math':
                context.save()
                try:
                    context.globalCompositeOperation=run.blend_mode
                    context.filter=self._filter_css(run)
                    events.extend(replace(event,brightness=run.brightness,filter_chain=run.filter_chain,blend_mode=run.blend_mode) for event in self._draw_math(context,run,box,kind,semantic_id,tx,ty))
                finally:context.restore()
                continue
            if run.asset_id and run.asset_box is not None:
                local=run.asset_box;rect=Box(box.x+local.x,box.y+local.y,local.width,local.height)
                context.save();context.globalAlpha=run.opacity
                context.globalCompositeOperation=run.blend_mode
                context.filter=self._filter_css(run)
                context.drawImage(self._asset(run.asset_id,run.kind,run.color),rect.x,rect.y,rect.width,rect.height);context.restore()
                ink=self._ink_box(run,box)
                events.append(DrawEvent('inline-asset',semantic_id,Box(ink.x+tx,ink.y+ty,ink.width,ink.height),resource_id=run.asset_id,opacity=run.opacity,brightness=run.brightness,filter_chain=run.filter_chain,blend_mode=run.blend_mode))
                continue
            context.save()
            self._run_font(context,run)
            context.globalAlpha=run.opacity
            context.globalCompositeOperation=run.blend_mode
            context.filter=self._filter_css(run)
            x=box.x+run.x;baseline=box.y+run.baseline
            if run.background not in {'','none','transparent'}:
                context.fillStyle=run.background
                context.fillRect(x,baseline-run.ascent,run.width,run.ascent+run.descent)
                events.append(DrawEvent(kind+'-background',semantic_id,
                    Box(x+tx,baseline+ty-run.ascent,run.width,run.ascent+run.descent),
                    fill=run.background,opacity=run.opacity))
            self._text_shadows(context,run,x,baseline)
            context.fillStyle=run.color or '#000000'
            context.textDecoration='none'
            if run.text_stroke_color and run.text_stroke_width>0:
                context.strokeStyle=run.text_stroke_color;context.lineWidth=run.text_stroke_width
                context.strokeText(run.text,x,baseline)
                events.append(DrawEvent(kind+'-stroke',semantic_id,text=run.text,points=(Point(x+tx,baseline+ty),),
                    font_family=run.font_family,font_size=run.font_size,stroke=run.text_stroke_color,stroke_width=run.text_stroke_width,opacity=run.opacity))
            self._fill_decorated_text(context,run,x,baseline)
            ink=self._ink_box(run,box)
            events.append(DrawEvent(kind,semantic_id,Box(ink.x+tx,ink.y+ty,ink.width,ink.height),
                run.text,(Point(x+tx,baseline+ty),),font_family=run.font_family,font_size=run.font_size,
                font_weight=run.font_weight,font_style=run.font_style,color=str(context.fillStyle),opacity=run.opacity,
                brightness=run.brightness,filter_chain=run.filter_chain,blend_mode=run.blend_mode))
            context.restore()
        return events

    @staticmethod
    def _draw_text(context, lines: tuple[MeasuredLine, ...], box: Box, kind: str,
                   semantic_id: str, tx: float, ty: float) -> list[DrawEvent]:
        if not lines:
            return []
        row_height = box.height/len(lines)
        events = []
        for index, line in enumerate(lines):
            x = box.x+box.width/2
            baseline = box.y+(index+.5)*row_height+(line.ascent-line.descent)/2
            context.fillText(line.text, x, baseline)
            events.append(DrawEvent(kind, semantic_id,
                                   Box(x+tx-line.width/2, baseline+ty-line.ascent,
                                       line.width, line.ascent+line.descent), line.text,
                                   (Point(x+tx, baseline+ty),)))
        return events

    def render(self, diagram: Flowchart, measured: tuple[MeasuredNode, ...], layout: FlowLayout,
               *, annotations: MeasuredAnnotations | None = None, format: str = 'png', export_options: ExportOptions | None = None,
               group_overrides=(), draw_group_override=None) -> RenderResult:
        self._check_owner()
        self.trace = ()
        format='jpg' if format=='jpeg' else format
        if format not in {'png','jpg','webp','svg','pdf'}:raise MermaidError('Unsupported export format',code='UNSUPPORTED_FORMAT')
        options=export_options or ExportOptions()
        if not isinstance(options,ExportOptions) or not isinstance(options.density,int) or isinstance(options.density,bool) or options.density<1 or isinstance(options.quality,bool) or not isinstance(options.quality,(int,float)) or not math.isfinite(options.quality) or not 0<=options.quality<=1 or not isinstance(options.outline,bool) or not isinstance(options.downsample,bool) or (options.matte is not None and not isinstance(options.matte,str)):
            raise MermaidError('Invalid export options',code='INVALID_EXPORT_OPTIONS')
        node_ids = tuple(node.id for node in diagram.nodes)
        edge_ids = tuple(edge.id for edge in diagram.edges)
        group_ids = tuple(group.id for group in diagram.groups)
        group_overrides=dict(group_overrides)
        if set(group_overrides)-set(group_ids) or group_overrides and not callable(draw_group_override):
            raise MermaidError('Invalid group paint override',code='INVALID_SCENE')
        labelled_edge_ids = {edge.id for edge in diagram.edges if edge.label}
        annotations = annotations if annotations is not None else MeasuredAnnotations()
        if (len(set(node_ids)) != len(node_ids)
                or len(measured) != len(node_ids) or {node.id for node in measured} != set(node_ids)
                or len(layout.nodes) != len(node_ids) or {node.id for node in layout.nodes} != set(node_ids)
                or len(layout.edges) != len(edge_ids) or {edge.id for edge in layout.edges} != set(edge_ids)
                or len(set(group_ids)) != len(group_ids) or set(group_ids) & set(node_ids)
                or len(layout.groups) != len(group_ids) or {group.id for group in layout.groups} != set(group_ids)
                or len(annotations.groups) != len(group_ids) or {group.id for group in annotations.groups} != set(group_ids)
                or len(annotations.edge_labels) != len(labelled_edge_ids)
                or {label.id for label in annotations.edge_labels} != labelled_edge_ids
                or len(layout.edge_labels) != len(labelled_edge_ids)
                or {label.id for label in layout.edge_labels} != labelled_edge_ids):
            raise MermaidError("Layout/measurement identities do not match the diagram", code="INVALID_LAYOUT")
        sizes = {node.id: node for node in measured}
        engine_boxes = {node.id: node.box for node in layout.nodes}
        boxes = {}
        for node in layout.nodes:
            paint=node.paint_box or node.box
            boxes[node.id]=Box(paint.x+(paint.width-sizes[node.id].width)/2,
                               paint.y+(paint.height-sizes[node.id].height)/2,
                               sizes[node.id].width,sizes[node.id].height)
        shapes = {node.id: node.shape for node in diagram.nodes}
        routes = {edge.id: edge.sections for edge in layout.edges}
        group_layouts = {group.id: group for group in layout.groups}
        group_sizes = {group.id: group for group in annotations.groups}
        label_layouts = {label.id: label.box for label in layout.edge_labels}
        label_sizes = {label.id: label for label in annotations.edge_labels}
        node_styles={node.id:resolve_style(diagram,'node',node.id) for node in diagram.nodes}
        group_styles={group.id:resolve_style(diagram,'group',group.id) for group in diagram.groups}
        edge_styles={edge.id:resolve_style(diagram,'edge',edge.id) for edge in diagram.edges}
        edge_label_styles={edge.id:resolve_style(diagram,'edge-label',edge.id) for edge in diagram.edges if edge.label}
        canvas_style=resolve_style(diagram,'canvas')
        visible_title=bool(diagram.title) and resolve_style(diagram,'title').display!='none'
        if annotations.title_suppressed != (bool(diagram.title) and not visible_title):
            raise MermaidError('Title suppression does not match resolved display',code='INVALID_LAYOUT')
        if visible_title!=(annotations.title is not None and layout.title_box is not None):
            raise MermaidError('Diagram title measurement/placement is missing or unexpected',code='INVALID_LAYOUT')
        coordinates = []
        arrows = {}
        rough_nodes={};rough_groups={};rough_edges={};rough_components={};rough_details={}
        if diagram.config.look=='handDrawn':
            for node in diagram.nodes:
                size=sizes[node.id]
                path=size.outline or f'M 0 0 H {size.width:g} V {size.height:g} H 0 Z'
                if size.paint_outline:rough_nodes[node.id]=rough_path(path,seed=diagram.config.hand_drawn_seed,roughness=.2 if node.shape=='doublecircle' else .7,fill_style='solid' if node.shape in {'filledCircle','anchor','collapsedGroup'} else 'hachure',hachure_angle=120 if node.shape=='stateStart' else -41)
                for index,part in enumerate(size.parts):
                    # Source collapsed indicators and separator remain plain even
                    # when only the outer container is drawn with RoughJS.
                    if not part.css_classes:rough_components[(node.id,index)]=rough_path(part.path,seed=diagram.config.hand_drawn_seed,fill=part.fill!='none',fill_style=part.fill_style)
                for index,detail in enumerate(size.details):rough_details[(node.id,index)]=rough_path(detail,seed=diagram.config.hand_drawn_seed,roughness=.2 if node.shape=='doublecircle' else .7,fill=node.shape=='doublecircle')
            for group in layout.groups:
                box=group.paint_box or group.box
                rough_groups[group.id]=rough_path(f'M 0 0 H {box.width:g} V {box.height:g} H 0 Z',seed=diagram.config.hand_drawn_seed)


        def include_box(box: Box, margin: float = 0, *, shadow: ResolvedStyle | None = None):
            if not all(math.isfinite(value) for value in (box.x, box.y, box.width, box.height)) or box.width < 0 or box.height < 0:
                raise MermaidError("Layout contains invalid boxes", code="INVALID_LAYOUT")
            coordinates.extend(((box.x-margin,box.y-margin),(box.x+box.width+margin,box.y+box.height+margin)))
            if shadow is not None:
                blur_margin=3*shadow.shadow_blur
                coordinates.extend(((box.x+shadow.shadow_dx-margin-blur_margin,
                                     box.y+shadow.shadow_dy-margin-blur_margin),
                                    (box.x+box.width+shadow.shadow_dx+margin+blur_margin,
                                     box.y+box.height+shadow.shadow_dy+margin+blur_margin)))

        for group in layout.groups:
            style=group_styles[group.id]
            if group.id in group_overrides:
                include_box(group.paint_box or group.box)
                for command in group_overrides[group.id]:
                    if command.bounds is not None:include_box(command.bounds)
                continue
            include_box(group.paint_box or group.box,style.stroke_width/2,shadow=style if style.shadow_opacity>0 else None)
            title=group_sizes[group.id]
            if group.title_box is None:
                raise MermaidError("Group is missing its measured title placement",code="INVALID_LAYOUT")
            if group.title_box.width < title.label_width-1e-5 or group.title_box.height < title.label_height-1e-5:
                raise MermaidError("Group title placement is smaller than its measured text",code="INVALID_LAYOUT")
            include_box(group.title_box)
            for run in title.runs:include_box(self._ink_box(run,group.title_box))
        for label_id,box in label_layouts.items():
            title=label_sizes[label_id]
            if box.width < title.width-1e-5 or box.height < title.height-1e-5:
                raise MermaidError("Edge label placement is smaller than its measured text",code="INVALID_LAYOUT")
            include_box(box)
            for run in title.runs:include_box(self._ink_box(run,box))
        if annotations.title is not None and layout.title_box is not None:
            include_box(layout.title_box)
            for run in annotations.title.runs:include_box(self._ink_box(run,layout.title_box))
        for node in layout.nodes:
            box = boxes[node.id]
            size = sizes[node.id]
            if (engine_boxes[node.id].width < size.width - 1e-5 or engine_boxes[node.id].height < size.height - 1e-5):
                raise MermaidError("Placed node is smaller than its measured content", code="INVALID_LAYOUT")
            style=node_styles[node.id]
            for asset in size.assets:include_box(Box(box.x+asset.box.x,box.y+asset.box.y,asset.box.width,asset.box.height))
            if node.id in rough_nodes:
                rough=rough_nodes[node.id].bounds;include_box(Box(box.x+rough.x,box.y+rough.y,rough.width,rough.height),max(style.stroke_width,3)/2)
            for table in (rough_components,rough_details):
                for (identifier,index),item in table.items():
                    if identifier==node.id:include_box(Box(box.x+item.bounds.x,box.y+item.bounds.y,item.bounds.width,item.bounds.height),max(style.stroke_width,3)/2)
            for part in size.parts:
                paint=resolve_shape_part_style(diagram,node.id,part,style)
                if paint.display=='none' or not paint.paint_opacity:continue
                b=self._path_factory(part.path).bounds
                include_box(Box(box.x+b['left'],box.y+b['top'],b['width'],b['height']),
                            paint.stroke_width/2 if paint.stroke not in {'none',''} else 0,
                            shadow=paint if paint.shadow_opacity>0 else None)
            half_stroke = style.stroke_width / 2
            include_box(box,half_stroke,shadow=style if not size.assets and style.shadow_opacity>0 and self._shadow_for_shape(shapes[node.id]) else None)
            if size.label_box:
                local=size.label_box
                include_box(Box(box.x+local.x,box.y+local.y,local.width,local.height))
                for run in size.runs:include_box(self._ink_box(run,Box(box.x+local.x,box.y+local.y,local.width,local.height)))
        for group in layout.groups:
            if group.id in rough_groups:
                b=rough_groups[group.id].bounds;paint=group.paint_box or group.box;include_box(Box(paint.x+b.x,paint.y+b.y,b.width,b.height),max(group_styles[group.id].stroke_width,1.5)/2)
        for edge in diagram.edges:
            sections = routes[edge.id]
            route=next(item for item in layout.edges if item.id==edge.id)
            if not sections and not route.path and len(route.paint_points)!=1:
                raise MermaidError("Edge route is missing", code="INVALID_LAYOUT", span=edge.span)
            for section in sections:
                coordinates.extend((point.x, point.y) for point in (section.start, *section.bends, section.end))
            route=next(item for item in layout.edges if item.id==edge.id)
            points=route.paint_points or tuple(p for section in sections for p in (section.start,*section.bends,section.end))
            from ...geometry.edges import edge_markers
            markers=() if edge.stroke=='invisible' else edge_markers(points,edge.marker_start,edge.marker_end)
            arrows[edge.id]=markers
            for marker in markers:include_box(marker.bounds)
            if route.paint_bounds is not None:include_box(route.paint_bounds,edge_styles[edge.id].stroke_width/2)
            if route.path:
                b=self._path_factory(route.path).bounds;include_box(Box(b['left'],b['top'],b['width'],b['height']),edge_styles[edge.id].stroke_width/2)
                if diagram.config.look=='handDrawn' and edge.stroke!='invisible':
                    rough_edges[edge.id]=rough_path(route.path,seed=diagram.config.hand_drawn_seed,fill=False)
                    include_box(rough_edges[edge.id].bounds,edge_styles[edge.id].stroke_width/2)
        if any(not math.isfinite(value) for pair in coordinates for value in pair):
            raise MermaidError("Layout contains non-finite geometry", code="INVALID_LAYOUT")
        padding = diagram.config.diagram_padding
        if not coordinates:coordinates=[(0.,0.)]
        route_margin = 0 if not diagram.nodes and not diagram.edges and not diagram.groups and annotations.title is None else max((style.stroke_width/2 for style in edge_styles.values()),default=diagram.config.edge_stroke_width/2)
        left = min(x for x, _ in coordinates) - route_margin
        top = min(y for _, y in coordinates) - route_margin
        right = max(x for x, _ in coordinates) + route_margin
        bottom = max(y for _, y in coordinates) + route_margin
        width = max(1, math.ceil(right - left + 2 * padding))
        height = max(1, math.ceil(bottom - top + 2 * padding))
        if width > 32768 or height > 32768 or width * height > 64_000_000:
            raise MermaidError("PNG dimensions exceed the F01.1 render budget", code="RENDER_BUDGET")
        tx, ty = padding - left, padding - top
        canvas = self._new_canvas(width, height)
        context = canvas.getContext("2d")
        self._text_state(context, diagram)
        context.fillStyle = canvas_style.fill if canvas_style.fill not in {'none',''} else 'transparent'
        context.globalAlpha=canvas_style.paint_opacity*canvas_style.fill_opacity
        context.filter=self._filter_css(canvas_style)
        context.fillRect(0, 0, width, height)
        context.globalAlpha=1;context.filter='none'
        context.translate(tx, ty)
        trace = [DrawEvent("viewport", "", Box(0, 0, width, height))]

        def group_depth(group):
            depth=0
            parent=group.parent_id
            seen={group.id}
            while parent is not None:
                if parent in seen or parent not in group_layouts:
                    raise MermaidError("Group parent hierarchy is invalid",code="INVALID_LAYOUT")
                seen.add(parent)
                depth+=1
                parent=group_layouts[parent].parent_id
            return depth

        for group in sorted(diagram.groups,key=group_depth):
            placed=group_layouts[group.id]
            box=placed.paint_box or placed.box
            style=group_styles[group.id]
            if style.display=='none':continue
            if group.id in group_overrides:
                trace.extend(draw_group_override(context,group_overrides[group.id],tx,ty))
                continue
            context.filter='none'
            context.lineCap=style.line_cap;context.lineJoin=style.line_join;context.lineDashOffset=style.dash_offset
            if style.shadow_opacity and not style.filter_chain:
                shadow=self._draw_shadow(context,box,diagram,stroke_width=style.stroke_width,paint=style)
                trace.append(DrawEvent("group-shadow",group.id,Box(shadow.x+tx,shadow.y+ty,shadow.width,shadow.height)))
            context.fillStyle=style.fill if style.fill not in {'none',''} else 'transparent'
            context.filter=self._filter_css(style)
            context.strokeStyle=self._stroke_paint(context,style,box)
            context.lineWidth=style.stroke_width;context.setLineDash(list(style.dash))
            context.globalAlpha=style.paint_opacity*style.fill_opacity
            if group.id in rough_groups:self._paint_rough(context,rough_groups[group.id],style,box)
            else:
                context.fillRect(box.x,box.y,box.width,box.height)
                context.globalAlpha=style.paint_opacity*style.stroke_opacity
                if style.stroke_width:context.strokeRect(box.x,box.y,box.width,box.height)
            context.globalAlpha=1;context.filter='none'
            trace.append(DrawEvent("group",group.id,Box(box.x+tx,box.y+ty,box.width,box.height),
                                   fill=style.fill,stroke=self._trace_stroke(style),stroke_width=style.stroke_width,opacity=style.paint_opacity))
            context.fillStyle=resolve_style(diagram,'group-title',group.id).text_color
            title=group_sizes[group.id]
            trace.extend(self._draw_runs(context,title.runs,placed.title_box,'group-title',group.id,tx,ty)
                         if title.runs else self._draw_text(context,title.lines,placed.title_box,'group-title',group.id,tx,ty))
        context.strokeStyle = diagram.config.edge_color
        context.fillStyle = diagram.config.edge_color
        context.lineWidth = diagram.config.edge_stroke_width
        context.lineJoin = "round"
        for edge in diagram.edges:
            if edge.stroke=='invisible' or edge_styles[edge.id].display=='none':continue
            style=edge_styles[edge.id];route=next(item for item in layout.edges if item.id==edge.id)
            if len(route.paint_points)==1 and not route.path:continue
            context.filter=self._filter_css(style)
            context.strokeStyle=style.stroke if style.stroke not in {'none',''} else 'transparent'
            context.fillStyle=context.strokeStyle;context.lineWidth=style.stroke_width
            context.lineCap=style.line_cap;context.lineJoin=style.line_join;context.lineDashOffset=style.dash_offset
            context.setLineDash(list(self._edge_dash(diagram,edge,route,style)));context.globalAlpha=style.paint_opacity*style.stroke_opacity
            if edge.id in rough_edges:
                context.stroke(self._path_factory(rough_edges[edge.id].stroke_path))
            elif route.path:
                if style.stroke_width:context.stroke(self._path_factory(route.path))
            else:
                for section in routes[edge.id]:
                    points=(section.start,*section.bends,section.end);context.beginPath();context.moveTo(points[0].x,points[0].y)
                    for point in points[1:]:context.lineTo(point.x,point.y)
                    if style.stroke_width:context.stroke()
                    trace.append(DrawEvent('edge',edge.id,points=tuple(Point(p.x+tx,p.y+ty) for p in points),curve=route.effective_curve,stroke=style.stroke,stroke_width=style.stroke_width,opacity=style.paint_opacity))
            if route.path or edge.id in rough_edges:
                trace.append(DrawEvent('edge',edge.id,points=tuple(Point(p.x+tx,p.y+ty) for p in route.paint_points),path=rough_edges[edge.id].stroke_path if edge.id in rough_edges else route.path,curve=route.effective_curve,stroke=style.stroke,stroke_width=style.stroke_width,opacity=style.paint_opacity))
            for marker in arrows[edge.id]:
                context.save();context.setLineDash([]);context.lineWidth=marker.stroke_width
                context.fillStyle=diagram.config.edge_color if marker.kind=='circle' else style.stroke
                path=self._path_factory(marker.path)
                if marker.filled:context.fill(path)
                context.stroke(path)
                b=marker.bounds;marker_points=()
                if marker.kind=='point':
                    from ...geometry.path_geometry import flatten_path
                    vertices=list(dict.fromkeys(flatten_path(marker.path,steps=1)[0]))
                    if not marker.at_start:vertices=vertices[1:]+vertices[:1]
                    marker_points=tuple(Point(p.x+tx,p.y+ty) for p in vertices)
                trace.append(DrawEvent('arrow',edge.id,Box(b.x+tx,b.y+ty,b.width,b.height),points=marker_points,path=marker.path,marker=marker.kind,fill=str(context.fillStyle) if marker.filled else 'none',stroke=style.stroke,stroke_width=marker.stroke_width,opacity=style.paint_opacity))
                context.restore()
        context.globalAlpha=1;context.setLineDash([]);context.filter='none'
        for node in diagram.nodes:
            box, size = boxes[node.id], sizes[node.id]
            style=node_styles[node.id]
            if style.display=='none':continue
            context.filter='none'
            context.lineCap=style.line_cap;context.lineJoin=style.line_join;context.lineDashOffset=style.dash_offset
            if not size.assets and style.shadow_opacity and not style.filter_chain and self._shadow_for_shape(node.shape):
                shadow_box=self._draw_shadow(context,box,diagram,outline="" if node.shape=="square" else size.outline,
                                             stroke_width=style.stroke_width,paint=style)
                trace.append(DrawEvent("shadow", node.id,
                                       Box(shadow_box.x + tx, shadow_box.y + ty,
                                           shadow_box.width, shadow_box.height)))
            context.fillStyle = style.fill if style.fill not in {'none',''} else 'transparent'
            context.filter=self._filter_css(style)
            context.strokeStyle = self._stroke_paint(context,style,box)
            context.lineWidth = style.stroke_width;context.setLineDash(list(style.dash))
            if size.assets or not size.paint_outline:pass  # Virtual bbox: only source parts/assets paint.
            elif node.id in rough_nodes:
                self._paint_rough(context,rough_nodes[node.id],replace(style,stroke_width=2.5) if node.shape=='doublecircle' else style,box,
                                  outline_fill=size.outline if node.shape in {'stateStart','stateEnd'} else None)
                for index,detail in enumerate(size.details):self._paint_rough(context,rough_details[(node.id,index)],replace(style,stroke_width=1.5) if node.shape=='doublecircle' else style,box)
            elif node.shape=="square":
                context.globalAlpha=style.paint_opacity*style.fill_opacity
                context.fillRect(box.x, box.y, box.width, box.height)
                context.globalAlpha=style.paint_opacity*style.stroke_opacity
                if style.stroke_width:context.strokeRect(box.x, box.y, box.width, box.height)
            else:
                if not size.outline:
                    raise MermaidError("Nonrectangular node is missing its true outline",code="INVALID_MEASUREMENT")
                context.save()
                context.translate(box.x,box.y)
                context.strokeStyle=self._stroke_paint(context,style,Box(0,0,box.width,box.height))
                path=self._path_factory(size.outline)
                context.globalAlpha=style.paint_opacity*style.fill_opacity;context.fill(path)
                context.globalAlpha=style.paint_opacity*style.stroke_opacity
                if style.stroke_width:context.stroke(path)
                for detail in size.details:
                    detail_path=self._path_factory(detail)
                    if node.shape=="doublecircle":
                        # Each source <circle> is independently filled, filtered
                        # and stroked. Inner-ring shadow belongs on the outer
                        # ring's white fill, before painting the inner disk.
                        if style.shadow_opacity and not style.filter_chain:
                            inner_shadow=self._draw_shadow(context,Box(0,0,box.width,box.height),diagram,outline=detail,
                                                           stroke_width=style.stroke_width,paint=style)
                            trace.append(DrawEvent("node-detail-shadow",node.id,
                                                   Box(box.x+tx+inner_shadow.x,box.y+ty+inner_shadow.y,
                                                       inner_shadow.width,inner_shadow.height)))
                        context.fillStyle=style.fill if style.fill not in {'none',''} else 'transparent'
                        context.globalAlpha=style.paint_opacity*style.fill_opacity
                        context.fill(detail_path)
                    context.globalAlpha=style.paint_opacity*style.stroke_opacity
                    if style.stroke_width:context.stroke(detail_path)
                context.restore()
            context.globalAlpha=1;context.setLineDash([])
            if size.parts or size.assets:
                context.save();context.translate(box.x,box.y)
                for index,part in enumerate(size.parts):
                    paint=resolve_shape_part_style(diagram,node.id,part,style)
                    if paint.display=='none':continue
                    context.save();context.filter='none'
                    context.setLineDash(list(paint.dash));context.lineWidth=paint.stroke_width
                    context.lineCap=paint.line_cap;context.lineJoin=paint.line_join;context.lineDashOffset=paint.dash_offset
                    path=self._path_factory(part.path)
                    if part.css_classes and paint.shadow_opacity and not paint.filter_chain:
                        self._draw_shadow(context,Box(0,0,box.width,box.height),diagram,outline=part.path,stroke_width=paint.stroke_width,paint=paint)
                    context.filter=self._filter_css(paint)
                    context.fillStyle=paint.fill if paint.fill not in {'none',''} else 'transparent'
                    context.strokeStyle=self._stroke_paint(context,paint,Box(0,0,box.width,box.height))
                    if (node.id,index) in rough_components:
                        self._paint_rough(context,rough_components[(node.id,index)],paint,Box(0,0,box.width,box.height))
                    else:
                        if paint.fill not in {'none',''}:
                            context.globalAlpha=paint.paint_opacity*paint.fill_opacity;context.fill(path)
                        if paint.stroke not in {'none',''} and paint.stroke_width:
                            context.globalAlpha=paint.paint_opacity*paint.stroke_opacity;context.stroke(path)
                    b=path.bounds
                    trace.append(DrawEvent('node-part',node.id,Box(box.x+tx+b['left'],box.y+ty+b['top'],b['width'],b['height']),
                        path=part.path,fill=paint.fill,stroke=paint.stroke,stroke_width=paint.stroke_width,
                        opacity=paint.paint_opacity,dash=paint.dash,resource_id=' '.join(part.css_classes) or None))
                    context.restore()
                for asset in size.assets:
                    rect=asset.box;context.globalAlpha=asset.opacity*style.paint_opacity
                    context.drawImage(self._asset(asset.resource_id,asset.kind,style.stroke),rect.x,rect.y,rect.width,rect.height)
                    trace.append(DrawEvent('node-asset',node.id,Box(box.x+rect.x+tx,box.y+rect.y+ty,rect.width,rect.height),resource_id=asset.resource_id,opacity=asset.opacity*style.paint_opacity))
                context.restore()
            actual_fill=(style.hachure_color or style.fill) if node.id in rough_nodes and node.shape not in {'stateStart','stateEnd'} and rough_nodes[node.id].fill_style=='hachure' and rough_nodes[node.id].fill_path else style.fill
            context.filter='none'
            trace.append(DrawEvent("node", node.id, Box(box.x + tx, box.y + ty, box.width, box.height),
                                   fill=actual_fill,stroke=self._trace_stroke(style),stroke_width=style.stroke_width,opacity=style.paint_opacity))
            local=size.label_box or Box((box.width-size.label_width)/2,(box.height-size.label_height)/2,
                                        size.label_width,size.label_height)
            context.fillStyle = resolve_style(diagram,'node-label',node.id).text_color
            label_box=Box(box.x+local.x,box.y+local.y,local.width,local.height)
            if size.assets and size.label_width>0 and any(run.text for run in size.runs):
                context.save();context.globalAlpha=style.paint_opacity*(1 if diagram.config.html_labels else .5)
                context.fillStyle=diagram.config.edge_label_background
                context.fillRect(label_box.x,label_box.y,label_box.width,label_box.height);context.restore()
                trace.append(DrawEvent('resource-label-background',node.id,Box(label_box.x+tx,label_box.y+ty,label_box.width,label_box.height),fill=diagram.config.edge_label_background,opacity=style.paint_opacity*(1 if diagram.config.html_labels else .5)))
            trace.extend(self._draw_runs(context,size.runs,label_box,'text',node.id,tx,ty)
                         if size.runs else self._draw_text(context,size.lines,label_box,'text',node.id,tx,ty))
        for edge in diagram.edges:
            if not edge.label:
                continue
            box=label_layouts[edge.id]
            style=edge_label_styles[edge.id]
            if style.display=='none':continue
            context.fillStyle=style.background if style.background not in {'none',''} else 'transparent'
            context.globalAlpha=style.paint_opacity*(1 if diagram.config.html_labels else .5)
            context.fillRect(box.x,box.y,box.width,box.height)
            context.globalAlpha=1
            trace.append(DrawEvent("edge-label-background",edge.id,Box(box.x+tx,box.y+ty,box.width,box.height),
                                   fill=style.background,opacity=style.paint_opacity))
            context.fillStyle=style.text_color
            label=label_sizes[edge.id]
            trace.extend(self._draw_runs(context,label.runs,box,'edge-label',edge.id,tx,ty)
                         if label.runs else self._draw_text(context,label.lines,box,'edge-label',edge.id,tx,ty))
        if annotations.title is not None and layout.title_box is not None:
            context.fillStyle=resolve_style(diagram,'title').text_color
            trace.extend(self._draw_runs(context,annotations.title.runs,layout.title_box,'diagram-title','',tx,ty))
        encoded={'quality':options.quality,'density':options.density,'outline':options.outline,'downsample':options.downsample}
        if options.matte is not None:encoded['matte']=options.matte
        if width*height*options.density**2>64_000_000 and format in {'png','jpg','webp'}:raise MermaidError('Export density exceeds image budget',code='RENDER_BUDGET')
        try:data = bytes(canvas.toBufferSync(format,encoded))
        except Exception as exc:raise MermaidError(f'Canvas {format} export failed: {exc}',code='EXPORT_ERROR') from exc
        output_width=width*options.density if format in {'png','jpg','webp'} else width
        output_height=height*options.density if format in {'png','jpg','webp'} else height
        mime={'png':'image/png','jpg':'image/jpeg','webp':'image/webp','svg':'image/svg+xml','pdf':'application/pdf'}[format]
        backend = tuple((str(key), str(value)) for key, value in sorted(canvas.engine.items()))
        self.trace = tuple(trace)
        return RenderResult(data, output_width, output_height, mime, diagram, measured, layout, backend,
                            diagnostics=tuple(dict.fromkeys(self._diagnostics)),trace=self.trace,annotations=annotations)
