"""Renderer-side center-ray intersections, separate from ELK port clipping.

Source: rendering-elements/intersect/{rect,circle,polygon}.js and each
reachable shape handler's node.intersect. Rectangular virtual attachments do
not suddenly acquire the painted decorative boundary of clouds/brace/text.
"""
import math
from ...model.flowchart import Point
from ...geometry.path_geometry import flatten_path
from ...geometry.shape_registry import canonical_shape

RECT=frozenset(('square','round','bang','browser','consoleWindow','cloud','collapsedGroup','curlyBraceLeft','curlyBraceRight','curlyBraces','datastore','dividedRectangle','forkJoin','note','shadedProcess','state','text','taggedRect','iconCircle'))
CIRCLE=frozenset(('anchor','circle','doublecircle','crossedCircle','filledCircle','stateStart','stateEnd'))

def rect(box,point):
    cx=box.x+box.width/2;cy=box.y+box.height/2;dx=point.x-cx;dy=point.y-cy;w=box.width/2;h=box.height/2
    if abs(dy)*w>abs(dx)*h:
        h=-h if dy<0 else h;sx=h*dx/dy if dy else 0;sy=h
    else:
        w=-w if dx<0 else w;sx=w;sy=w*dy/dx if dx else 0
    return Point(cx+sx,cy+sy)

def intersect(kind,box,point,measured=None):
    kind=canonical_shape(kind);cx=box.x+box.width/2;cy=box.y+box.height/2
    if kind in RECT:return rect(box,point)
    dx=point.x-cx;dy=point.y-cy
    if kind in CIRCLE:
        length=math.hypot(dx,dy)
        # Fixed intersect-ellipse guards a query at the center by returning it.
        if length==0:return Point(cx,cy)
        radius=box.width/2;return Point(cx+radius*dx/length,cy+radius*dy/length)
    if kind in ('cylinder','linedCylinder','tiltedCylinder'):
        pos=rect(box,point)
        if kind=='tiltedCylinder':
            ry=box.height/2;rx=ry/(2.5+box.height/50);y=pos.y-cy
            if ry and (abs(y)<box.height/2 or abs(y)==box.height/2 and abs(pos.x-cx)>box.width/2-rx):
                x=rx*rx*(1-y*y/(ry*ry));x=math.sqrt(abs(x)) if x else x;x=rx-x
                if dx>0:x=-x
                return Point(pos.x+x,pos.y)
        else:
            rx=box.width/2;ry=rx/(2.5+box.width/50);x=pos.x-cx
            if rx and (abs(x)<box.width/2 or abs(x)==box.width/2 and abs(pos.y-cy)>box.height/2-ry):
                y=ry*ry*(1-x*x/(rx*rx));y=math.sqrt(y) if y>0 else y;y=ry-y
                if dy>0:y=-y
                return Point(pos.x,pos.y+y)
        return pos
    if dx==0 and dy==0:return Point(cx,cy)
    outline=measured.outline if measured is not None else ''
    hits=[]
    for points in flatten_path(outline):
        for a,b in zip(points,(*points[1:],points[:1][0])) if points else ():
            ax=box.x+a.x;ay=box.y+a.y;sx=b.x-a.x;sy=b.y-a.y;det=dx*sy-dy*sx
            if abs(det)<1e-12:continue
            t=((ax-cx)*sy-(ay-cy)*sx)/det;u=((ax-cx)*dy-(ay-cy)*dx)/det
            if -1e-8<=u<=1+1e-8:hits.append(Point(cx+t*dx,cy+t*dy))
    # The source polygon helper explicitly returns the node center when its
    # query line has no boundary intersections; keep that degenerate policy.
    return min(hits,key=lambda p:(p.x-point.x)**2+(p.y-point.y)**2) if hits else Point(cx,cy)

def paint_points(points,source_box,target_box,source_kind,target_kind,source_measure=None,target_measure=None):
    if len(points)<2:return points
    clip_source=lambda pt:intersect(source_kind,source_box,pt,source_measure)
    clip_target=lambda pt:intersect(target_kind,target_box,pt,target_measure)
    if len(points)==2:return (clip_source(points[0]),clip_target(points[1]))
    inner=points[1:-1];first,last=inner[0],inner[-1]
    close=lambda a,b:abs(a.x-b.x)<.5 and abs(a.y-b.y)<.5
    first_clip=clip_source(first);last_clip=last if close(points[-1],last) else clip_target(last)
    return (() if close(first_clip,first) else (first_clip,))+inner+(() if close(last_clip,last) else (last_clip,))
