"""Pure edge paths from fixed edges.js / lineJump.ts / markers.js.

Coordinates are absolute logical pixels. Native path construction is downstream.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from py_mermaid.model.flowchart import Box, Point

def f(number):
    return format(number, ".12g")

def xy(point):
    return f(point.x)+","+f(point.y)

def dedupe(points):
    out=[]
    for point in points:
        if not out or abs(point.x-out[-1].x)>1e-6 or abs(point.y-out[-1].y)>1e-6:out.append(point)
    return tuple(out)

def distance(a,b):return math.hypot(a.x-b.x,a.y-b.y)

def between(a,b,t):return Point(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t)

def corner(a,b,c,radius=5):
    first,second=distance(a,b),distance(b,c)
    if min(first,second)<1e-5:return None
    x,y=(b.x-a.x)/first,(b.y-a.y)/first
    u,v=(c.x-b.x)/second,(c.y-b.y)/second
    angle=math.acos(max(-1,min(1,x*u+y*v)))
    if angle<1e-5 or abs(math.pi-angle)<1e-5:return None
    cut=min(radius/math.sin(angle/2),first/2,second/2)
    return Point(b.x-x*cut,b.y-y*cut),Point(b.x+u*cut,b.y+v*cut),cut

def rounded_path(points, radius=5):
    if len(points)<2:return ""
    path=["M"+xy(points[0])]
    for i,b in enumerate(points[1:],1):
        bend=corner(points[i-1],b,points[i+1],radius) if radius > 0 and i+1<len(points) else None
        path.extend(("L"+xy(bend[0]),"Q"+xy(b)+" "+xy(bend[1])) if bend else ("L"+xy(b),))
    return " ".join(path)

def marker_offsets(points,start="none",end="point"):
    result=list(points)
    if len(result)<2:return tuple(result)
    # Actual path pullback uses markerOffsets, not markerOffsets2. The latter
    # table supplies the neo dash gap and short-stub clearance only.
    offsets={"none":0,"point":4,"circle":0,"cross":0}
    for index,neighbor,kind in ((0,1,start),(-1,-2,end)):
        a,b=result[index],points[neighbor];length=distance(a,b)
        if length and offsets[kind]:result[index]=between(a,b,offsets[kind]/length)
    return tuple(result)

@dataclass(frozen=True)
class MarkerGeometry:
    path: str
    bounds: Box
    filled: bool
    kind: str
    at_start: bool
    stroke_width: float = 1.0

def edge_markers(points,start="none",end="point"):
    """SVG userSpaceOnUse markers transformed at the OFFSET path endpoint.

    Source point viewBox10/width8, circle viewBox10/width11 and cross11.
    Caller supplies un-offset paint points; same pull-back as edge path.
    """
    shifted=marker_offsets(points,start,end);result=[]
    if len(shifted)<2:return ()
    from py_mermaid.geometry.path_geometry import path_bounds
    for at_start,kind in ((True,start),(False,end)):
        if kind=="none":continue
        anchor=shifted[0] if at_start else shifted[-1]
        a,b=(points[0],points[1]) if at_start else (points[-2],points[-1])
        length=distance(a,b)
        if length<1e-9:continue
        ux,uy=(b.x-a.x)/length,(b.y-a.y)/length
        if kind=="point":scale=.8;ref=4.5 if at_start else 5;refy=5
        elif kind=="circle":scale=1.1;ref=-1 if at_start else 11;refy=5
        else:scale=1;ref=-1 if at_start else 12;refy=5.2
        def transform(x,y):
            x,y=(x-ref)*scale,(y-refy)*scale
            return Point(anchor.x+x*ux-y*uy,anchor.y+x*uy+y*ux)
        if kind=="point":
            vertices=((0,5),(10,10),(10,0)) if at_start else ((0,0),(10,5),(0,10))
            path="M"+xy(transform(*vertices[0]))+" "+" ".join("L"+xy(transform(*v)) for v in vertices[1:])+" Z"
        elif kind=="circle":
            c=transform(5,5);r=5.5
            path=f"M{f(c.x-r)},{f(c.y)} A{f(r)},{f(r)} 0 1 0 {f(c.x+r)},{f(c.y)} A{f(r)},{f(r)} 0 1 0 {f(c.x-r)},{f(c.y)} Z"
        else:path="M"+xy(transform(1,1))+" L"+xy(transform(10,10))+" M"+xy(transform(10,1))+" L"+xy(transform(1,10))
        bounds=path_bounds(path)
        half=.4 if kind=='point' else .55 if kind=='circle' else 1
        bounds=Box(bounds.x-half,bounds.y-half,bounds.width+2*half,bounds.height+2*half)
        result.append(MarkerGeometry(path,bounds,kind in ('point','circle'),kind,at_start,2*half))
    return tuple(result)

def intersect_segments(a,b,c,d):
    rx,ry=b.x-a.x,b.y-a.y;sx,sy=d.x-c.x,d.y-c.y
    denominator=rx*sy-ry*sx
    if denominator==0:return None
    qx,qy=c.x-a.x,c.y-a.y
    t=(qx*sy-qy*sx)/denominator;u=(qx*ry-qy*rx)/denominator
    return (t,u,between(a,b,t)) if 1e-6<t<1-1e-6 and 1e-6<u<1-1e-6 else None

def _rounded_hit(points,index,t):
    length=distance(points[index],points[index+1]);where=t*length
    incoming=corner(points[index-1],points[index],points[index+1]) if index else None
    outgoing=corner(points[index],points[index+1],points[index+2]) if index+2<len(points) else None
    return bool((incoming and where<incoming[2]) or (outgoing and length-where<outgoing[2]))

def line_hop_paths(routes,markers,style=True):
    """Source crossing orientation, radius6, corner clearance2 and .6 floor.

    Routes are (points,effective_curve). Return paths without native objects.
    """
    jumps={i:{} for i in range(len(routes))}
    supported={"linear","rounded","step","stepBefore","stepAfter"}
    if style is not False:
        for i,(a,curve_a) in enumerate(routes):
            for j in range(i+1,len(routes)):
                b,curve_b=routes[j]
                if curve_a not in supported or curve_b not in supported:continue
                for ai,(a0,a1) in enumerate(zip(a,a[1:])):
                    for bi,(b0,b1) in enumerate(zip(b,b[1:])):
                        hit=intersect_segments(a0,a1,b0,b1)
                        if not hit:continue
                        ta,tb,point=hit
                        if (curve_a=="rounded" and _rounded_hit(a,ai,ta)) or (curve_b=="rounded" and _rounded_hit(b,bi,tb)):continue
                        ah=abs(a1.x-a0.x)>=abs(a1.y-a0.y);bh=abs(b1.x-b0.x)>=abs(b1.y-b0.y)
                        target,index,t=(i,ai,ta) if ah!=bh and ah else (j,bi,tb)
                        jumps[target].setdefault(index,[]).append((t,point))
    paths=[]
    for index,(raw,curve) in enumerate(routes):
        start,end=markers[index];points=marker_offsets(raw,start,end)
        if not jumps[index]:paths.append(rounded_path(points) if curve=="rounded" else rounded_path(points,0));continue
        parts=["M"+xy(points[0])]
        for k,(a,b) in enumerate(zip(points,points[1:])):
            length=distance(a,b)
            if length<1e-9:continue
            ux,uy=(b.x-a.x)/length,(b.y-a.y)/length
            previous=corner(points[k-1],a,b) if curve=="rounded" and k else None
            following=corner(a,b,points[k+2]) if curve=="rounded" and k+2<len(points) else None
            lower=previous[2] if previous else 0;upper=length-(following[2] if following else 0)
            available=[]
            for t,point in sorted(jumps[index].get(k,[]),key=lambda item:item[0]):
                d=t*length;r=min(6,d-lower-2,upper-d-2)
                if r>=3.6:available.append([d,r,point])
            for first,second in zip(available,available[1:]):
                half=(second[0]-first[0])/2
                if first[1]+second[1]>2*half:first[1]=min(first[1],half);second[1]=min(second[1],half)
            for d,r,point in available:
                if r<3.6:continue
                before=Point(point.x-ux*r,point.y-uy*r);after=Point(point.x+ux*r,point.y+uy*r)
                parts.append("L"+xy(before))
                if style=="gap":parts.append("M"+xy(after))
                else:
                    sweep=int((b.x-a.x)>=0) if abs(ux)>=abs(uy) else int((b.y-a.y)>=0)
                    parts.append(f"A{f(r)},{f(r)} 0 0 {sweep} "+xy(after))
            if following:parts.extend(("L"+xy(following[0]),"Q"+xy(b)+" "+xy(following[1])))
            else:parts.append("L"+xy(b))
        paths.append(" ".join(parts))
    return tuple(paths)
