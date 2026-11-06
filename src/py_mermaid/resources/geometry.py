"""Pure image/icon source dimensions and placement, no native decoding."""
from __future__ import annotations
import math
from ..model.flowchart import Box,ShapePart,MermaidError
from ..config.values import thaw_value

def dimension(value,default):
    if value is None:return default
    try:
        if isinstance(value,str) and not value.strip():return 0.
        return float(value)
    except (TypeError,ValueError) as exc:raise MermaidError('Resource dimension must be numeric',code='INVALID_RESOURCE') from exc

def asset_layout(kind,lw,lh,cfg,metadata,asset_size):
    meta=thaw_value(metadata) if isinstance(metadata,tuple) else dict(metadata or {})
    if asset_size is None:raise MermaidError('Resource has no natural dimensions',code='RESOURCE_NOT_FOUND')
    nw,nh=asset_size
    if nw<=0 or nh<=0:raise MermaidError('Invalid natural resource dimensions',code='INVALID_RESOURCE')
    icon=kind!='imageSquare' and kind!='image'
    gap=8 if lh>0 and lw>0 else 0
    if icon:
        aw=ah=max(dimension(meta.get('h'),48),dimension(meta.get('w'),48))
        if kind=='iconCircle':frame_w=frame_h=aw*math.sqrt(2)+40
        elif kind in {'iconSquare','iconRounded'}:frame_w=frame_h=aw+(cfg.node_padding or 0)
        else:frame_w=frame_h=aw
    else:
        raw=max(cfg.wrapping_width if lw>0 else 0,dimension(meta.get('w'),nw))
        if meta.get('constraint')=='on':
            aw=dimension(meta['h'],nh)*nw/nh if meta.get('h') is not None else raw;ah=aw*nh/nw
        else:aw=raw;ah=dimension(meta.get('h'),nh)
        frame_w,frame_h=aw,ah
    if min(aw,ah)<=0 or not all(math.isfinite(v) for v in (aw,ah)) or max(aw,ah)>32768:raise MermaidError('Invalid asset dimensions',code='RESOURCE_BUDGET')
    width=max(frame_w,lw);height=frame_h+lh+gap;top=meta.get('pos')=='t'
    label=Box((width-lw)/2,0 if top else frame_h+gap,lw,lh)
    frame=Box((width-frame_w)/2,lh+gap if top else 0,frame_w,frame_h)
    asset=Box((width-aw)/2,frame.y+(frame_h-ah)/2,aw,ah)
    return width,height,label,frame,asset

def resource_geometry(kind,lw,lh,cfg,metadata=(),asset_size=None):
    from ..geometry.shapes import ShapeGeometry
    width,height,label,frame,asset=asset_layout(kind,lw,lh,cfg,metadata,asset_size)
    outline=f'M 0 0 H {width:.17g} V {height:.17g} H 0 Z'
    x,y,w,h=frame.x,frame.y,frame.width,frame.height
    if kind=='iconCircle':
        r=w/2;cx=x+r;cy=y+r
        path=f'M {cx+r:g} {cy:g} A {r:g} {r:g} 0 1 0 {cx-r:g} {cy:g} A {r:g} {r:g} 0 1 0 {cx+r:g} {cy:g} Z'
    elif kind in {'iconSquare','iconRounded'}:
        r=5 if kind=='iconRounded' else .1
        path=f'M {x+r:g} {y:g} H {x+w-r:g} Q {x+w:g} {y:g} {x+w:g} {y+r:g} V {y+h-r:g} Q {x+w:g} {y+h:g} {x+w-r:g} {y+h:g} H {x+r:g} Q {x:g} {y+h:g} {x:g} {y+h-r:g} V {y+r:g} Q {x:g} {y:g} {x+r:g} {y:g} Z'
    else:path=f'M {x:g} {y:g} H {x+w:g} V {y+h:g} H {x:g} Z'
    # Icon standalone is intentionally paint-free; framed variants paint their
    # frame using fill as stroke, while SVG icon itself uses nodeBorder currentColor.
    parts=() if kind=='icon' else (ShapePart(path,'node','fill' if kind.startswith('icon') else 'node'),)
    return ShapeGeometry(width,height,label,outline,(),parts)
