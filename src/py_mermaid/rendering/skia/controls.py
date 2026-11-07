"""Execute immutable initial-state form-control paint on an owner Canvas.

No layout, resource lookup, font creation, offscreen surface, or host UI lives
here. Text coordinates are alphabetic baselines; circle coordinates describe
its bounding rectangle; line width/height are signed endpoint increments.
"""
from __future__ import annotations

from dataclasses import replace
import math
import re

from ...model.controls import ControlLayout
from ...model.flowchart import Box, DrawEvent, MeasuredTextRun, MermaidError, Point


_MAX_PAINTS = 4096
_MAX_RUNS = 16384
_MAX_TEXT = 1_000_000
_MAX_PATH = 1_000_000
_MAX_COORD = 10_000_000
_KINDS = frozenset(('rect', 'roundrect', 'circle', 'path', 'text', 'line', 'image'))


def _number(value, name, *, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MermaidError('Control '+name+' must be numeric', code='INVALID_GEOMETRY')
    try:
        result = float(value)
    except (ValueError, OverflowError):
        result = math.nan
    if not math.isfinite(result) or abs(result) > _MAX_COORD or nonnegative and result < 0:
        raise MermaidError('Invalid control '+name, code='INVALID_GEOMETRY')
    return result


def _intersection(box, clip):
    if clip is None or box is None:
        return box
    left=max(box.x, clip.x);top=max(box.y, clip.y)
    right=min(box.x+box.width, clip.x+clip.width)
    bottom=min(box.y+box.height, clip.y+clip.height)
    return Box(left,top,max(0,right-left),max(0,bottom-top))


def _font(paint):
    family=paint.font_family.rstrip().removesuffix(';').rstrip()
    if not family or any(c in family for c in ('\n','\r','\0')):
        raise MermaidError('Invalid control font family',code='INVALID_GEOMETRY')
    weight={'normal':'400','bold':'700'}.get(str(paint.font_weight),str(paint.font_weight))
    return f'{paint.font_style} {weight} {paint.font_size:g}px {family}'


def _validate(layout, x, y, paint_runs, paint_image):
    if not isinstance(layout,ControlLayout):
        raise MermaidError('Expected immutable ControlLayout',code='INVALID_GEOMETRY')
    _number(x,'origin x');_number(y,'origin y')
    _number(layout.width,'width',nonnegative=True);_number(layout.height,'height',nonnegative=True)
    _number(layout.baseline,'baseline')
    caption_runs=getattr(layout,'caption_runs',())
    if len(layout.paints)>_MAX_PAINTS or len(layout.content_runs)+len(caption_runs)>_MAX_RUNS:
        raise MermaidError('Control paint count exceeds budget',code='RENDER_BUDGET')
    if len(layout.content_offset)!=2:
        raise MermaidError('Control content offset requires2coordinates',code='INVALID_GEOMETRY')
    for value in layout.content_offset:_number(value,'content offset')
    caption_offset=getattr(layout,'caption_offset',(0,0))
    if len(caption_offset)!=2:
        raise MermaidError('Control caption offset requires2coordinates',code='INVALID_GEOMETRY')
    for value in caption_offset:_number(value,'caption offset')
    if layout.clip is not None:
        if len(layout.clip)!=4:raise MermaidError('Control clip requires4coordinates',code='INVALID_GEOMETRY')
        for i,value in enumerate(layout.clip):_number(value,'clip',nonnegative=i>1)
    if (layout.content_runs or caption_runs) and not callable(paint_runs):
        raise MermaidError('Control text painter is unavailable',code='INVALID_GEOMETRY')
    text_size=sum(len(run.text) for run in (*layout.content_runs,*caption_runs));path_size=0
    for paint in layout.paints:
        if paint.kind not in _KINDS:
            raise MermaidError('Unknown control paint '+str(paint.kind),code='INVALID_GEOMETRY')
        for name in ('x','y','width','height','line_width','radius'):
            _number(getattr(paint,name),name,nonnegative=name in ('line_width','radius') or name in ('width','height') and paint.kind!='line')
        if not all(isinstance(value,str) for value in (paint.fill,paint.stroke,paint.path,paint.text,paint.resource_id)):
            raise MermaidError('Control paint strings must be pure text',code='INVALID_GEOMETRY')
        text_size+=len(paint.text);path_size+=len(paint.path)
        if paint.kind=='path':
            if not paint.path.strip():
                raise MermaidError('Control path must not be empty',code='INVALID_GEOMETRY')
            for value in re.findall(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?',paint.path):
                _number(float(value),'path coordinate')
        if paint.kind=='image' and (not paint.resource_id or not callable(paint_image)):
            raise MermaidError('Control image resource painter is unavailable',code='RESOURCE_NOT_FOUND')
        if paint.kind=='text':
            if not callable(paint_runs):
                raise MermaidError('Control text painter is unavailable',code='INVALID_GEOMETRY')
            if not isinstance(paint.font_family,str) or paint.font_style not in ('normal','italic','oblique'):
                raise MermaidError('Invalid control text font',code='INVALID_GEOMETRY')
            if _number(paint.font_size,'font size',nonnegative=True)==0:
                raise MermaidError('Control font size must be positive',code='INVALID_GEOMETRY')
            if getattr(paint,'direction','ltr') not in ('ltr','rtl'):
                raise MermaidError('Invalid control text direction',code='INVALID_GEOMETRY')
            weight=str(paint.font_weight)
            if weight not in ('normal','bold','bolder','lighter') and not (
                re.fullmatch(r'\d+(?:\.\d+)?',weight) and 0<float(weight)<=1000):
                raise MermaidError('Invalid control text weight',code='INVALID_GEOMETRY')
            if not isinstance(getattr(paint,'decoration',''),str):
                raise MermaidError('Invalid control text decoration',code='INVALID_GEOMETRY')
            if not all(isinstance(v,str) for v in (paint.letter_spacing,paint.word_spacing,paint.text_stroke_color)):
                raise MermaidError('Invalid control text effects',code='INVALID_GEOMETRY')
            _number(paint.text_stroke_width,'text stroke width',nonnegative=True)
            if len(paint.text_shadows)>_MAX_PAINTS:
                raise MermaidError('Control shadow count exceeds budget',code='RENDER_BUDGET')
            for shadow in paint.text_shadows:
                if len(shadow)!=4 or not isinstance(shadow[3],str):
                    raise MermaidError('Invalid control text shadow',code='INVALID_GEOMETRY')
                for i,value in enumerate(shadow[:3]):_number(value,'text shadow',nonnegative=i==2)
            _font(paint)
    if text_size>_MAX_TEXT or path_size>_MAX_PATH:
        raise MermaidError('Control text/path exceeds budget',code='RENDER_BUDGET')


def _set_clip(context, clip):
    if clip is not None:
        # Current path is not part of Canvas save/restore state. An explicit
        # clip Path2D preserves a caller's in-progress current path as well.
        from py_skia_canvas import Path2D
        path=Path2D();path.rect(clip.x,clip.y,clip.width,clip.height);context.clip(path)


def paint_control(context, layout, x, y, *, paint_runs, paint_image=None):
    """Paint on the supplied owner context and return real primitive events.

    Callbacks draw on that same context. ``paint_runs(runs,x,y)`` returns its
    DrawEvents; ``paint_image(id,x,y,w,h)`` performs explicit resource painting.
    Only text/images/content receive layout.clip. External alpha/filter/blend
    are inherited untouched; the session combines parent/child run styles.
    Native thread-affinity errors propagate, and save/restore is exception-safe.
    """
    _validate(layout,x,y,paint_runs,paint_image)
    if layout.spec.hidden:return ()
    from py_skia_canvas import Path2D
    x=float(x);y=float(y);events=[]
    clip=Box(x+layout.clip[0],y+layout.clip[1],layout.clip[2],layout.clip[3]) if layout.clip is not None else None
    context.save()
    try:
        for paint in layout.paints:
            px=x+paint.x;py=y+paint.y
            context.save()
            try:
                alpha=float(context.globalAlpha)
                context.setLineDash([])
                context.lineWidth=paint.line_width
                context.lineJoin='round';context.lineCap='butt'
                if paint.kind in ('text','image'):_set_clip(context,clip)
                if paint.kind=='text':
                    context.font=_font(paint);context.textAlign='left';context.textBaseline='alphabetic'
                    context.direction=getattr(paint,'direction','ltr')
                    context.letterSpacing=paint.letter_spacing;context.wordSpacing=paint.word_spacing
                    metrics=context.measureText(paint.text)
                    left=_number(metrics.actualBoundingBoxLeft,'text ink left')
                    right=_number(metrics.actualBoundingBoxRight,'text ink right')
                    ascent=_number(metrics.actualBoundingBoxAscent,'text ascent')
                    descent=_number(metrics.actualBoundingBoxDescent,'text descent')
                    # The shared run painter owns glyphs, decorations, shadows,
                    # stroke and filters. Its callback composes outer opacity
                    # once; this local run must therefore keep opacity=1.
                    run=MeasuredTextRun(paint.text,0,0,_number(metrics.width,'text width'),ascent,descent,
                        paint.font_family.rstrip().removesuffix(';').rstrip(),paint.font_size,
                        font_weight=str(paint.font_weight),font_style=paint.font_style,color=paint.fill or '#000000',
                        decoration=paint.decoration,ink_left=left,ink_right=right,direction=paint.direction,
                        letter_spacing=paint.letter_spacing,word_spacing=paint.word_spacing,
                        text_shadows=paint.text_shadows,text_stroke_color=paint.text_stroke_color,
                        text_stroke_width=paint.text_stroke_width,blend_mode=str(context.globalCompositeOperation))
                    for event in paint_runs((run,),px,py):
                        if not isinstance(event,DrawEvent):
                            raise MermaidError('Control callback must return DrawEvent values',code='INVALID_GEOMETRY')
                        kind='control-text-stroke' if event.kind.endswith('-stroke') else 'control-text'
                        events.append(replace(event,kind=kind,clip=clip if clip is not None else event.clip,
                                              box=_intersection(event.box,clip)))
                    continue
                if paint.kind=='image':
                    paint_image(paint.resource_id,px,py,paint.width,paint.height)
                    events.append(DrawEvent('control-image','',_intersection(Box(px,py,paint.width,paint.height),clip),resource_id=paint.resource_id,clip=clip,opacity=alpha))
                    continue
                path=Path2D()
                if paint.kind=='rect':path.rect(px,py,paint.width,paint.height)
                elif paint.kind=='roundrect':path.roundRect(px,py,paint.width,paint.height,paint.radius)
                elif paint.kind=='circle':path.ellipse(px+paint.width/2,py+paint.height/2,paint.width/2,paint.height/2,0,0,math.tau)
                elif paint.kind=='line':path.moveTo(px,py);path.lineTo(px+paint.width,py+paint.height)
                else:
                    # Path bytes stay pure until the existing native owner draws.
                    path=Path2D(paint.path).transform(1,0,0,1,px,py)
                fill=paint.fill not in ('','none','transparent') and paint.kind!='line'
                stroke=paint.stroke not in ('','none','transparent') and paint.line_width>0
                if fill:context.fillStyle=paint.fill;context.fill(path)
                if stroke:context.strokeStyle=paint.stroke;context.stroke(path)
                if not fill and not stroke:continue
                bounds=path.bounds
                for key in ('left','top','width','height'):_number(bounds[key],'path '+key,nonnegative=key in ('width','height'))
                margin=paint.line_width/2 if stroke else 0
                box=Box(bounds['left']-margin,bounds['top']-margin,bounds['width']+2*margin,bounds['height']+2*margin)
                events.append(DrawEvent('control-'+paint.kind,'',box,path=path.d,
                    points=(Point(px,py),Point(px+paint.width,py+paint.height)) if paint.kind=='line' else (),
                    fill=paint.fill if fill else 'none',stroke=paint.stroke if stroke else 'none',stroke_width=paint.line_width if stroke else 0,opacity=alpha))
            finally:
                context.restore()
        if layout.content_runs:
            context.save()
            try:
                _set_clip(context,clip)
                child_events=paint_runs(layout.content_runs,x+layout.content_offset[0],y+layout.content_offset[1])
                for event in child_events:
                    if not isinstance(event,DrawEvent):raise MermaidError('Control callback must return DrawEvent values',code='INVALID_GEOMETRY')
                    events.append(replace(event,clip=clip if clip is not None else event.clip,box=_intersection(event.box,clip)))
            finally:
                context.restore()
        caption_runs=getattr(layout,'caption_runs',())
        if caption_runs:
            context.save()
            try:
                # A fieldset legend sits on its border; body clipping must not
                # remove its caption. Child runs retain their own clips.
                offset=getattr(layout,'caption_offset',(0,0))
                for event in paint_runs(caption_runs,x+offset[0],y+offset[1]):
                    if not isinstance(event,DrawEvent):raise MermaidError('Control caption callback must return DrawEvent values',code='INVALID_GEOMETRY')
                    events.append(event)
            finally:
                context.restore()
    finally:
        context.restore()
    return tuple(events)


__all__=['paint_control']
