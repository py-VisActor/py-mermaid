"""Pure classic flow.jison shape sizing, paths and orthogonal intersections.

Source handlers: rendering-util/rendering-elements/shapes in the fixed Mermaid
checkout. Paths are ordinary immutable SVG path *values*, never DOM or native
objects. Every path is normalized to its outer top-left box.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from ..model.flowchart import Box, FlowConfig, MermaidError, Point, ShapePart
from .shape_registry import canonical_shape, is_valid_shape


CLASSIC_SHAPES = frozenset({"square", "round", "stadium", "subroutine", "cylinder",
                            "circle", "doublecircle", "diamond", "hexagon", "odd",
                            "trapezoid", "inv_trapezoid", "lean_left", "lean_right"})

LABELLESS_SHAPES = frozenset({'stateStart','stateEnd','filledCircle','crossedCircle','choice',
                             'forkJoin','lightningBolt','anchor','hourglass'})


@dataclass(frozen=True)
class ShapeGeometry:
    width: float
    height: float
    label_box: Box
    outline: str
    details: tuple[str, ...] = ()
    parts: tuple[ShapePart, ...] = ()
    paint_outline: bool = True


def _polygon(points: tuple[Point, ...]) -> str:
    return "M " + " L ".join(f"{p.x:.17g} {p.y:.17g}" for p in points) + " Z"


def _rect(width: float, height: float, radius: float = 0) -> str:
    radius = min(radius, width / 2, height / 2)
    if radius <= 0:
        return f"M 0 0 H {width:.17g} V {height:.17g} H 0 Z"
    return (f"M {radius:.17g} 0 H {width-radius:.17g} "
            f"A {radius:.17g} {radius:.17g} 0 0 1 {width:.17g} {radius:.17g} "
            f"V {height-radius:.17g} A {radius:.17g} {radius:.17g} 0 0 1 {width-radius:.17g} {height:.17g} "
            f"H {radius:.17g} A {radius:.17g} {radius:.17g} 0 0 1 0 {height-radius:.17g} "
            f"V {radius:.17g} A {radius:.17g} {radius:.17g} 0 0 1 {radius:.17g} 0 Z")


def _ellipse(cx: float, cy: float, rx: float, ry: float) -> str:
    return (f"M {cx-rx:.17g} {cy:.17g} "
            f"A {rx:.17g} {ry:.17g} 0 1 0 {cx+rx:.17g} {cy:.17g} "
            f"A {rx:.17g} {ry:.17g} 0 1 0 {cx-rx:.17g} {cy:.17g} Z")


def _wave(x0, y0, x1, amplitude, *, cycles=1, direction=1):
    # Fixed util.generateFullSineWavePoints uses exactly fifty intervals.
    return tuple(Point(x0+(x1-x0)*i/50,y0+direction*amplitude*math.sin(i/50*cycles*2*math.pi)) for i in range(51))


def _extended_geometry(kind, lw, lh, config, *, metadata=(), asset_size=None, direction='TD'):
    """Static path/label responsibilities of the fixed source shape handlers.

    Source handler names are retained in shape_registry. Dimensions are logical
    pixels and all paths are normalized to the measured node's top-left box.
    """
    p=config.node_padding or 8;neo=config.look=='neo';px=16 if neo else p;py=12 if neo else p
    parts=[];details=();ox=oy=0.;w=max(1,lw+2*px);h=max(1,lh+2*py)
    label=Box((w-lw)/2,(h-lh)/2,lw,lh)
    if kind in {'icon','iconCircle','iconSquare','iconRounded','imageSquare'}:
        from ..resources.geometry import resource_geometry
        return resource_geometry(kind,lw,lh,config,metadata=metadata,asset_size=asset_size)
    if kind in {'text','note','state','composite'}:
        if kind=='text':w=max(1,lw+p);h=max(1,lh+p)
        elif kind=='composite':w=max(1,lw+p);h=max(1,lh+p)
        outline=_rect(w,h,(3 if neo else 5) if kind=='state' else 0)
    elif kind=='datastore':
        w=max(1,lw+4*p);h=max(1,lh+2*p)
        outline=_rect(w,h)
        label=Box((w-lw)/2,(h-lh)/2,lw,lh)
        # drawRect retains the closed fill, while only the horizontal borders
        # are visible (dash removal in classic/neo; separate lines in rough).
        parts=(ShapePart(outline,fill='node',stroke='none'),ShapePart(f'M 0 0 H {w} M 0 {h} H {w}'))
        return ShapeGeometry(w,h,label,outline,(),parts,False)
    elif kind=='folder':
        w=max(lw+2*p,90);content=lh+2*p;tab=max(8,min(content*.16,14));h=content+tab;tabw=max(.38*w,28)
        outline=_polygon((Point(0,0),Point(tabw,0),Point(tabw,tab),Point(w,tab),Point(w,h),Point(0,h)))
        oy=tab/2
    elif kind=='bucket':
        w=max(lw+2*p,80);ry=max(5,min(w*.08,12));h=lh+2*p+2*ry;inset=w*.14
        outline=f'M 0 {ry} L {inset} {h-ry} A {w*.36} {ry} 0 0 0 {w-inset} {h-ry} L {w} {ry} A {w/2} {ry} 0 0 0 0 {ry} Z'
        parts.append(ShapePart(_ellipse(w/2,ry,w/2,ry)))
        oy=ry/2
    elif kind in {'consoleWindow','browser'}:
        band=20 if kind=='consoleWindow' else 18;w=max(lw+2*p,90);h=lh+2*p+band;outline=_rect(w,h,12);oy=band/2
        if kind=='consoleWindow':
            parts.append(ShapePart('M 12 7 L 17 11 L 12 15 M 21 15 H 29'))
        else:
            parts.append(ShapePart(f'M 0 {band} H {w}'))
            for x in (12,21,30):parts.append(ShapePart(_ellipse(x,9,2.5,2.5),fill='stroke',stroke='none'))
            parts.append(ShapePart(f'M 38 6 H {max(40,w-10)} V 12 H 38 Z'))
    elif kind=='person':
        w=max(lw+2*p,100);r=min(max(w*.23,16),56);overlap=r*.27;body=lh+2*p;h=body+2*r-overlap;top=2*r-overlap
        from .path_geometry import transform_path
        outline=transform_path(_rect(w,body,min(w*.177,body*.45)),dy=top)+' '+_ellipse(w/2,r,r,r)
        oy=top/2
    elif kind in {'stateStart','filledCircle','stateEnd','anchor','choice','forkJoin','lightningBolt','crossedCircle','hourglass'}:
        if kind=='choice':
            w=h=28;outline=_polygon((Point(w/2,0),Point(w,h/2),Point(w/2,h),Point(0,h/2)))
        elif kind=='forkJoin':
            w,h=(10,70) if direction in {'LR','RL'} else (70,10)
            outline=_rect(w,h)
        elif kind=='hourglass':w=h=30;outline=_polygon((Point(0,0),Point(w,0),Point(0,h),Point(w,h)))
        elif kind=='lightningBolt':
            w,h=35,70;gap=7;outline=_polygon((Point(w,0),Point(0,h/2+gap/2),Point(w-2*gap,h/2+gap/2),Point(0,h),Point(w,h/2-gap/2),Point(2*gap,h/2-gap/2)))
        else:
            radius=30 if kind=='crossedCircle' else 1 if kind=='anchor' else 7
            w=h=radius*2;outline=_ellipse(radius,radius,radius,radius)
            if kind=='stateEnd':parts.append(ShapePart(_ellipse(radius,radius,radius*5/14,radius*5/14),fill='node',stroke='node',fill_style='solid'))
            if kind=='crossedCircle':
                d=radius/math.sqrt(2);parts.append(ShapePart(f'M {radius-d} {radius-d} L {radius+d} {radius+d} M {radius-d} {radius+d} L {radius+d} {radius-d}'))
        if kind in LABELLESS_SHAPES:return ShapeGeometry(w,h,Box(w/2,h/2,0,0),outline,details,tuple(parts))
    elif kind=='card':
        w=lw+(56 if neo else p+12);h=lh+(48 if neo else p)
        outline=_polygon((Point(12,0),Point(w,0),Point(w,h),Point(0,h),Point(0,12)))
    elif kind=='shadedProcess':
        frame=8;w=lw+2*px+(frame if neo else 2*frame);h=lh+2*py;outline=_rect(w,h)
        parts.append(ShapePart(f'M {frame} 0 V {h}'));ox=frame/2
    elif kind in {'curlyBraceLeft','curlyBraceRight','curlyBraces'}:
        r=max(5,h*.1);w=lw+2*p+(4*r if kind=='curlyBraces' else 2*r);h=lh+2*p+2*r
        def brace(x,sign):return (f'M {x+sign*r} 0 Q {x} 0 {x} {r} V {h/2-r} Q {x} {h/2} {x-sign*r} {h/2} '
                                  f'Q {x} {h/2} {x} {h/2+r} V {h-r} Q {x} {h} {x+sign*r} {h}')
        outline=brace(r,1) if kind=='curlyBraceLeft' else brace(w-r,-1) if kind=='curlyBraceRight' else brace(r,1)+' '+brace(w-r,-1)
        if kind=='curlyBraceLeft':ox=r
        if kind=='curlyBraceRight':ox=-r
    elif kind in {'waveEdgedRectangle','linedWaveEdgedRect','taggedWaveEdgedRectangle','multiWaveEdgedRectangle','waveRectangle'}:
        # Literal source fifty-sample sine point lists. The measured box uses
        # sampled extrema, not an idealized sine or the pre-wave body height.
        if kind=='multiWaveEdgedRectangle':
            bodyw=lw+2*px;bodyh=lh+3*py;amp=bodyh/(4 if neo else 8);final=bodyh+amp/2
            wave=_wave(0,final+20,bodyw,amp,cycles=.8);last=wave[-1].y
            points=(Point(0,20),Point(0,final+20),*wave,Point(bodyw,last-10),Point(bodyw+10,last-10),
                    Point(bodyw+10,last-20),Point(bodyw+20,last-20),Point(bodyw+20,0),Point(20,0),Point(20,10),Point(10,10),Point(10,20))
            w=bodyw+20;h=max(point.y for point in points);outline=_polygon(points)
            inner=(Point(10,20),Point(bodyw,20),Point(bodyw,last-10),Point(bodyw+10,last-10),Point(bodyw+10,10),Point(10,10))
            parts.append(ShapePart(_polygon(inner),fill='node'))
            label=Box(px,(final-lh)/2+20-amp/2,lw,lh)
        elif kind=='waveRectangle':
            w=lw+2*px;bodyh=lh+(20 if neo else p);amp=bodyh/8;final=bodyh+2*amp
            raw=(Point(0,final/2),*_wave(0,final/2,w,amp),Point(w,-final/2),*_wave(w,-final/2,0,amp,cycles=-1))
            top=min(point.y for point in raw);bottom=max(point.y for point in raw);h=bottom-top
            outline=_polygon(tuple(Point(point.x,point.y-top) for point in raw));label=Box((w-lw)/2,(h-lh)/2,lw,lh)
        else:
            tagged=kind=='taggedWaveEdgedRectangle';lined=kind=='linedWaveEdgedRect'
            basew=lw+2*(p if tagged else px);bodyh=lh+2*(p if tagged else py)
            amp=bodyh/8 if tagged or not neo else bodyh/4;final=bodyh+amp
            w=max(14,basew)*(1.1 if tagged or lined else 1)
            wave=_wave(0,final,w,amp,cycles=.8);points=(Point(0,final),*wave,Point(w,0),Point(0,0))
            h=max(point.y for point in points);outline=_polygon(points)
            label=Box(p+(.075*basew if lined else .05*basew if tagged else 0),p+amp/2 if tagged else p,lw,lh)
            if lined:parts.append(ShapePart(f'M {basew*.05} 0 V {final*1.05}'))
            if tagged:
                tx=-basew*.45;ty=-final/2-bodyh*.08;tagw=basew*.2;tagh=bodyh*.2
                tag=(Point(tx+basew-tagw,(ty+bodyh)*1.3),Point(tx+basew,ty+bodyh-tagh),Point(tx+basew,(ty+bodyh)*.9),
                     *_wave(tx+basew,(ty+bodyh)*1.275,tx+basew-tagw,-bodyh*.02,cycles=.5))
                tag=tuple(Point(point.x+basew*.55,point.y+final/2) for point in tag)
                parts.append(ShapePart(_polygon(tag),fill='node',fill_style='solid'))
        return ShapeGeometry(w,h,label,outline,details,tuple(parts))
    elif kind=='halfRoundedRectangle':
        h=max(lh,15)+2*py;r=h/2;clear=r-math.sqrt(max(0,r*r-(lh/2)**2));w=max(lw,15)+2*px+2*clear
        outline=f'M 0 0 H {w-r} A {r} {r} 0 0 1 {w-r} {h} H 0 Z';ox=-clear/2
    elif kind=='tiltedCylinder':
        h=lh+(12 if neo else p/2);ry=h/2;rx=ry/(2.5+h/50);w=lw+3*rx+(12 if neo else p/2)
        outline=f'M {rx} 0 H {w-rx} A {rx} {ry} 0 0 1 {w-rx} {h} H {rx} A {rx} {ry} 0 0 1 {rx} 0 Z'
        # Source tiltedCylinder.createCylinderPathD completes the right cap.
        parts.append(ShapePart(f'M {w-rx} 0 A {rx} {ry} 0 0 0 {w-rx} {h}'));ox=rx/2
    elif kind=='linedCylinder':
        w=lw+2*px;rx=w/2;ry=rx/(2.5+w/50);body=lh+ry+(48 if neo else 2*p);gap=body*.1;h=body+2*ry+gap
        outline=f'M 0 {ry} A {rx} {ry} 0 0 1 {w} {ry} V {h-ry} A {rx} {ry} 0 0 1 0 {h-ry} Z'
        parts.extend(ShapePart(f'M 0 {y} A {rx} {ry} 0 0 0 {w} {y}') for y in [ry,ry+gap]);oy=ry/2
    elif kind=='curvedTrapezoid':
        h=max(20,lh+2*py);r=h/2;clear=r-math.sqrt(max(0,r*r-(lh/2)**2));side=h/4+clear
        w=max(lw+2*px+2*side,(lw+2*px)*1.25,20)
        outline=f'M {h/4} 0 H {w-r} A {r} {r} 0 0 1 {w-r} {h} H {h/4} L 0 {h/2} Z'
    elif kind=='dividedRectangle':
        w=lw+(16 if neo else p);body=lh+(16 if neo else p);gap=body*.2;h=body+gap;outline=_rect(w,h)
        parts.append(ShapePart(f'M 0 {gap} H {w}'));oy=gap/2
    elif kind in {'triangle','flippedTriangle'}:
        body=lw+(2*p if neo else p);w=h=body+lh
        outline=_polygon((Point(w/2,0),Point(w,h),Point(0,h))) if kind=='triangle' else _polygon((Point(0,0),Point(w,0),Point(w/2,h)))
        oy=(h-lh)/2-p/(2 if config.html_labels else 1) if kind=='triangle' else -(h-lh)/2+p/2
    elif kind=='windowPane':
        extra=10;w=lw+2*px+extra;h=lh+2*py+extra;outline=_rect(w,h)
        parts.append(ShapePart(f'M 0 {extra} H {w} M {extra} 0 V {h}'));ox=oy=extra/2
    elif kind=='trapezoidalPentagon':
        outline=_polygon((Point(w*.1,0),Point(w*.9,0),Point(w,h*.2),Point(w,h),Point(0,h),Point(0,h*.2)))
    elif kind=='slopedRect':
        body=h;h*=1.5;outline=_polygon((Point(0,body*.5),Point(w,0),Point(w,h),Point(0,h)));oy=body*.25
    elif kind=='multiRect':
        gap=10 if neo else 5;bodyw=w;bodyh=h;w+=2*gap;h+=2*gap
        outline=_polygon((Point(gap,0),Point(w,0),Point(w,h-2*gap),Point(w-gap,h-2*gap),Point(w-gap,h-gap),Point(w-2*gap,h-gap),Point(w-2*gap,h),Point(0,h),Point(0,2*gap),Point(gap,2*gap)))
        parts.append(ShapePart(f'M {gap} {gap} H {w-gap} V {h-gap} H {gap} Z M 0 {2*gap} H {bodyw} V {h}'))
        ox=-gap;oy=gap
    elif kind=='bowTieRect':
        h=lh+py;ry=h/2;rx=ry/(2.5+h/50);w=lw+2*px+rx
        outline=f'M 0 0 H {w} A {rx} {ry} 0 0 0 {w} {h} H 0 A {rx} {ry} 0 0 0 0 0 Z'
    elif kind=='taggedRect':
        tag=h*.2;w+=tag;outline=_rect(w,h)
        parts.append(ShapePart(_polygon((Point(w-tag,h),Point(w,h),Point(w,h-tag))),fill='node',fill_style='solid'))
    elif kind in {'cloud','bang'}:
        from .path_geometry import path_bounds,transform_path
        if kind=='cloud':
            bw=lw+p;bh=lh+p;r1=.15*bw;r2=.25*bw;r3=.35*bw;r4=.2*bw
            raw=(f'M 0 0 a {r1} {r1} 0 0 1 {bw*.25} {-bw*.1} a {r3} {r3} 1 0 1 {bw*.4} {-bw*.1} '
                 f'a {r2} {r2} 1 0 1 {bw*.35} {bw*.2} a {r1} {r1} 1 0 1 {bw*.15} {bh*.35} '
                 f'a {r4} {r4} 1 0 1 {-bw*.15} {bh*.65} a {r2} {r1} 1 0 1 {-bw*.25} {bw*.15} '
                 f'a {r3} {r3} 1 0 1 {-bw*.5} 0 a {r1} {r1} 1 0 1 {-bw*.25} {-bw*.15} '
                 f'a {r1} {r1} 1 0 1 {-bw*.1} {-bh*.35} a {r4} {r4} 1 0 1 {bw*.1} {-bh*.65} H 0 V 0 Z')
        else:
            bw=max(lw+5*p,lw+20);bh=max(lh+4*p,lh+20);r=bw*.15
            deltas=[(.25,-.1),(.25,0),(.25,0),(.25,.1),(.15,.33),(0,.34),(-.15,.33),(-.25,.15),(-.25,0),(-.25,0),(-.25,-.15),(-.1,-.33),(0,-.34),(.1,-.33)]
            raw='M 0 0 '+' '.join(f'a {r*(.8 if i in {5,12} else 1)} {r*(.8 if i in {5,12} else 1)} 1 0 0 {dx*bw} {dy*bh}' for i,(dx,dy) in enumerate(deltas))+' H 0 V 0 Z'
        bounds=path_bounds(raw);w=bounds.width;h=bounds.height;outline=transform_path(raw,dx=-bounds.x,dy=-bounds.y)
    elif kind=='collapsedGroup':
        from ..config.values import thaw_value
        meta=thaw_value(metadata) if metadata else {}
        # Both DB projections set padding=8. Container identity survives collapse.
        p=8;radius=10 if meta.get('containerType')=='flow' else 8
        w=max(80,lw+2*p);h=lh+2*p+28;outline=_rect(w,h,radius);oy=-14
        separator=p+lh+8
        parts.append(ShapePart(f'M 8 {separator} H {w-8}',dash=(3,3),css_classes=('collapsed-separator',),tag='line'))
        for x in (w/2-10,w/2,w/2+10):
            parts.append(ShapePart(_ellipse(x,separator+10,2.5,2.5),fill='stroke',stroke='none',css_classes=('collapsed-indicator',),tag='circle'))
    else:
        raise MermaidError(f'No geometry for registered shape {kind!r}',code='UNSUPPORTED_SHAPE')
    label=Box((w-lw)/2+ox,(h-lh)/2+oy,lw,lh)
    return ShapeGeometry(w,h,label,outline,details,tuple(parts))


def _outline_vertices(kind: str, width: float, height: float, *, neo: bool = True) -> tuple[Point, ...]:
    """Normalized polygon outlines; bbox dimensions include protruding corners."""
    w, h = width, height
    if kind == "stadium":
        radius = h/2
        missing = radius*(1-math.cos(math.pi/98))
        return (tuple(Point(radius-missing + radius*math.cos(math.radians(90+i*180/49)),
                            radius + radius*math.sin(math.radians(90+i*180/49))) for i in range(50))
                + tuple(Point(w-radius+missing + radius*math.cos(math.radians(270+i*180/49)),
                              radius + radius*math.sin(math.radians(270+i*180/49))) for i in range(50)))
    if kind == "diamond":
        return (Point(w/2, 0), Point(w, h/2), Point(w/2, h), Point(0, h/2))
    if kind == "hexagon":
        m = h / (3.5 if neo else 4)
        return (Point(m, 0), Point(w-m, 0), Point(w, h/2), Point(w-m, h), Point(m, h), Point(0, h/2))
    if kind == "lean_right":
        return (Point(h/2, 0), Point(w, 0), Point(w-h/2, h), Point(0, h))
    if kind == "lean_left":
        return (Point(0, 0), Point(w-h/2, 0), Point(w, h), Point(h/2, h))
    if kind == "trapezoid":
        return (Point(h/2, 0), Point(w-h/2, 0), Point(w, h), Point(0, h))
    if kind == "inv_trapezoid":
        return (Point(0, 0), Point(w, 0), Point(w-h/2, h), Point(h/2, h))
    if kind == "odd":
        return (Point(0, 0), Point(w, 0), Point(w, h), Point(0, h), Point(h/4, h/2))
    return (Point(0, 0), Point(w, 0), Point(w, h), Point(0, h))


def shape_geometry(kind: str, label_width: float, label_height: float, config: FlowConfig,
                   *, metadata=(), asset_size=None, direction='TD') -> ShapeGeometry:
    """Source-derived classic shape dimensions from an already measured label.

    Circle labels must have been measured without the source minNodeWidth floor.
    Nonempty other labels carry that floor before they reach this function.
    """
    kind = canonical_shape(kind)
    if kind == "ellipse":
        raise MermaidError("Classic ellipse has no renderer in the fixed Mermaid baseline", code="UPSTREAM_SHAPE_MISSING")
    if not all(math.isfinite(value) and value >= 0 for value in (label_width, label_height)):
        raise MermaidError("Shape label dimensions must be finite and nonnegative", code="INVALID_MEASUREMENT")
    if kind not in CLASSIC_SHAPES:
        return _extended_geometry(kind,label_width,label_height,config,metadata=metadata,asset_size=asset_size,direction=direction)
    lw, lh, p = label_width, label_height, config.node_padding or 8
    neo = config.look == "neo"
    details: tuple[str, ...] = ()
    offset_x = offset_y = 0.0
    if kind == "square":
        w, h = (lw + 2*config.padding_x, lh + 2*config.padding_y) if neo else (lw+4*p,lh+2*p)
        outline = _rect(w, h)
    elif kind == "round":
        w, h = lw + 2*p, lh + 2*p
        outline = _rect(w, h, config.round_radius)
    elif kind in {"circle", "doublecircle"}:
        padding = 16 if neo else p if kind=="doublecircle" else p/2
        inner_radius = math.hypot(lw, lh) / 2 + padding
        radius = inner_radius + ((12 if neo else 5) if kind == "doublecircle" else 0)
        w = h = radius*2
        outline = _ellipse(radius, radius, radius, radius)
        if kind == "doublecircle":
            details = (_ellipse(radius, radius, inner_radius, inner_radius),)
    elif kind == "stadium":
        h = lh + (24 if neo else p)
        px = 40 if neo else p
        inscribed = h * math.cos(math.pi / (2*(50-1)))
        cap_clearance = math.sqrt(max(0, inscribed*inscribed - lh*lh))
        w = max(lw + h/4 + px, 1.5*h + h-inscribed, lw + px + h-cap_clearance)
        # The source samples each semicircle at 50 points. Preserve the same
        # outer polygon rather than pretending it was an ordinary round rect.
        radius = h/2
        points = tuple(Point(radius + radius*math.cos(math.radians(90 + i*180/49)),
                             radius + radius*math.sin(math.radians(90 + i*180/49))) for i in range(50))
        points += tuple(Point(w-radius + radius*math.cos(math.radians(270 + i*180/49)),
                              radius + radius*math.sin(math.radians(270 + i*180/49))) for i in range(50))
        # Normalize sampled extrema (the midpoint of an even sample is shy of r).
        left, right = min(point.x for point in points), max(point.x for point in points)
        points = tuple(Point(point.x-left, point.y) for point in points)
        w = right-left
        outline = _polygon(points)
    elif kind == "subroutine":
        w, h = lw + 16 + (28 if neo else p), lh + (12 if neo else p)
        outline = _rect(w, h)
        details = (f"M 8 0 V {h:.17g}", f"M {w-8:.17g} 0 V {h:.17g}")
    elif kind == "cylinder":
        w = lw + (24 if neo else p)
        rx = w/2
        ry = rx/(2.5+w/50)
        body_height = lh + (24 if neo else p) + ry
        h = body_height + 2*ry
        # Source path: complete top ellipse, side walls, lower outer half.
        outline = (f"M 0 {ry:.17g} A {rx:.17g} {ry:.17g} 0 0 1 {w:.17g} {ry:.17g} "
                   f"V {h-ry:.17g} A {rx:.17g} {ry:.17g} 0 0 1 0 {h-ry:.17g} Z")
        details = (f"M 0 {ry:.17g} A {rx:.17g} {ry:.17g} 0 0 0 {w:.17g} {ry:.17g}",)
        offset_y = p/1.5
    elif kind == "diamond":
        w = h = lw + lh + 2*p
        outline = _polygon(_outline_vertices(kind, w, h))
    elif kind == "hexagon":
        h = lh+(70 if neo else p)
        w = lw + 2*h/(3.5 if neo else 4) + (32 if neo else p)
        outline = _polygon(_outline_vertices(kind, w, h,neo=neo))
    elif kind in {"lean_left", "lean_right", "trapezoid", "inv_trapezoid"}:
        h = lh + (2*p if kind == "inv_trapezoid" else p)
        body_width = lw + ((4*p if neo else 2*p) if kind == "inv_trapezoid" else (2*p if neo else p))
        w = body_width + h
        outline = _polygon(_outline_vertices(kind, w, h))
    else:  # odd / rect_left_inv_arrow
        h = lh + (24 if neo else p)
        w = lw + (42 if neo else p) + h/4
        offset_x = h/8
        outline = _polygon(_outline_vertices(kind, w, h))
    label_box = Box((w-lw)/2+offset_x, (h-lh)/2+offset_y, lw, lh)
    return ShapeGeometry(w, h, label_box, outline, details)


def shape_outline_intersection(kind: str, box: Box, port: Point, toward: Point, *, config: FlowConfig | None = None,
                               metadata=(), outline: str = '') -> Point:
    """Clip an orthogonal port axis, or a nonorthogonal center ray, to ink."""
    kind=canonical_shape(kind)
    if kind == "ellipse":
        raise MermaidError("Classic ellipse renderer is missing upstream", code="UPSTREAM_SHAPE_MISSING")
    if not all(math.isfinite(value) for value in (box.x, box.y, box.width, box.height, port.x, port.y, toward.x, toward.y)) or box.width <= 0 or box.height <= 0:
        raise MermaidError("Invalid shape intersection geometry", code="INVALID_LAYOUT")
    w, h = box.width, box.height
    x, y = port.x-box.x, port.y-box.y
    dx, dy = toward.x-port.x, toward.y-port.y
    if kind in {'text','datastore','curlyBraceLeft','curlyBraceRight','curlyBraces'}:
        # These source handlers intersect their virtual rectangle, not the
        # open decorative brace/store strokes. Nonrouting ports start at center.
        if abs(dx)>1e-8 and abs(dy)>1e-8 or 0<x<w and 0<y<h:
            rx,ry=toward.x-box.x-w/2,toward.y-box.y-h/2
            scales=[bound/abs(component) for bound,component in ((w/2,rx),(h/2,ry)) if abs(component)>1e-12]
            if scales:
                scale=min(scales)
                return Point(box.x+w/2+rx*scale,box.y+h/2+ry*scale)
        return port
    if abs(dx)>1e-8 and abs(dy)>1e-8 and outline:
        from .path_geometry import flatten_path
        cx,cy=w/2,h/2
        rx,ry=toward.x-box.x-cx,toward.y-box.y-cy
        hits=[]
        for points in flatten_path(outline):
            for a,b in zip(points,points[1:]):
                sx,sy=b.x-a.x,b.y-a.y
                determinant=rx*sy-ry*sx
                if abs(determinant)<1e-12:continue
                ax,ay=a.x-cx,a.y-cy
                distance=(ax*sy-ay*sx)/determinant
                fraction=(ax*ry-ay*rx)/determinant
                if distance>=-1e-8 and -1e-8<=fraction<=1+1e-8:hits.append(max(0,distance))
        if hits:
            # intersect-polygon.js chooses the intersection nearest the edge
            # endpoint, including concave/self-crossed source outlines.
            distance=min(hits,key=lambda value:abs(1-value))
            return Point(box.x+cx+distance*rx,box.y+cy+distance*ry)
        if kind not in {'text','datastore','curlyBraceLeft','curlyBraceRight','curlyBraces','anchor'}:
            raise MermaidError('Center ray does not intersect the shape outline',code='INVALID_LAYOUT')
    horizontal = abs(dx) >= abs(dy)
    candidates: list[float] = []
    if kind not in CLASSIC_SHAPES:
        from .path_geometry import flatten_path, transform_path
        if not outline:
            if config is None:
                from ..config import resolve_config
                config=resolve_config()
            shape=shape_geometry(kind,max(0,w-2*config.node_padding),max(0,h-2*config.node_padding),config,metadata=metadata)
            outline=transform_path(shape.outline,sx=w/shape.width,sy=h/shape.height)
        for points in flatten_path(outline):
            for first,second in zip(points,points[1:]):
                fixed_a,fixed_b=(first.y,second.y) if horizontal else (first.x,second.x)
                moving_a,moving_b=(first.x,second.x) if horizontal else (first.y,second.y)
                fixed=y if horizontal else x
                if abs(fixed_b-fixed_a)<1e-12:
                    if abs(fixed-fixed_a)<1e-8:candidates.extend((moving_a,moving_b))
                else:
                    t=(fixed-fixed_a)/(fixed_b-fixed_a)
                    if -1e-8<=t<=1+1e-8:candidates.append(moving_a+t*(moving_b-moving_a))
    elif kind in {"circle", "doublecircle"}:
        if horizontal:
            t = 1-((y-h/2)/(h/2))**2
            if t >= -1e-9:
                delta = w/2*math.sqrt(max(0, t)); candidates = [w/2-delta, w/2+delta]
        else:
            t = 1-((x-w/2)/(w/2))**2
            if t >= -1e-9:
                delta = h/2*math.sqrt(max(0, t)); candidates = [h/2-delta, h/2+delta]
    elif kind == "round":
        radius = min(config.round_radius if config is not None else 12.0, w/2, h/2)
        if horizontal:
            if radius <= y <= h-radius:
                candidates = [0, w]
            else:
                cy = radius if y < radius else h-radius
                delta = math.sqrt(max(0, radius*radius-(y-cy)**2))
                candidates = [radius-delta, w-radius+delta]
        else:
            if radius <= x <= w-radius:
                candidates = [0, h]
            else:
                cx = radius if x < radius else w-radius
                delta = math.sqrt(max(0, radius*radius-(x-cx)**2))
                candidates = [radius-delta, h-radius+delta]
    elif kind == "cylinder":
        rx=w/2; ry=rx/(2.5+w/50)
        if horizontal:
            if ry <= y <= h-ry:
                candidates = [0, w]
            else:
                cy = ry if y < ry else h-ry
                delta=rx*math.sqrt(max(0,1-((y-cy)/ry)**2))
                candidates=[rx-delta,rx+delta]
        else:
            delta=ry*math.sqrt(max(0,1-((x-rx)/rx)**2))
            candidates=[ry-delta,h-ry+delta]
    else:
        points = _outline_vertices(kind,w,h,neo=config is None or config.look=="neo")
        for first,second in zip(points,(*points[1:],points[0])):
            fixed_a, fixed_b = (first.y,second.y) if horizontal else (first.x,second.x)
            moving_a, moving_b = (first.x,second.x) if horizontal else (first.y,second.y)
            fixed = y if horizontal else x
            if abs(fixed_b-fixed_a) < 1e-12:
                if abs(fixed-fixed_a)<1e-8:
                    candidates.extend((moving_a,moving_b))
            else:
                t=(fixed-fixed_a)/(fixed_b-fixed_a)
                if -1e-8 <= t <= 1+1e-8:
                    candidates.append(moving_a+t*(moving_b-moving_a))
    if not candidates:
        raise MermaidError("Port axis does not intersect the actual shape outline",code="INVALID_LAYOUT")
    # The nearest boundary on this axis retains the ELK-selected bbox side.
    moving=x if horizontal else y
    chosen=min(candidates,key=lambda value:abs(value-moving))
    return Point(box.x+chosen,port.y) if horizontal else Point(port.x,box.y+chosen)
