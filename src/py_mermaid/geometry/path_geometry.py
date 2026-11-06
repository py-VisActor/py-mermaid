"""Pure SVG path-value geometry; never creates an SVG document or native path."""
from __future__ import annotations

import math
import re

from ..model.flowchart import Box, MermaidError, Point

_TOKEN = re.compile(r'[MmLlHhVvQqTtCcSsAaZz]|[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?')
_ARITY = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'Q': 4, 'T': 2, 'C': 6, 'S': 4, 'A': 7}


def _arc(start, values, relative, steps):
    rx, ry, rotation, large, sweep, ex, ey = values
    if relative: ex += start.x; ey += start.y
    end = Point(ex, ey); rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0 or start == end: return (end,)
    phi = math.radians(rotation % 360); c, s = math.cos(phi), math.sin(phi)
    dx, dy = (start.x-ex)/2, (start.y-ey)/2
    xp, yp = c*dx+s*dy, -s*dx+c*dy
    scale = xp*xp/(rx*rx)+yp*yp/(ry*ry)
    if scale > 1: rx *= math.sqrt(scale); ry *= math.sqrt(scale)
    numerator = max(0, rx*rx*ry*ry-rx*rx*yp*yp-ry*ry*xp*xp)
    denominator = rx*rx*yp*yp+ry*ry*xp*xp
    factor = math.sqrt(numerator/denominator) if denominator else 0
    if bool(large) == bool(sweep): factor = -factor
    cxp, cyp = factor*rx*yp/ry, -factor*ry*xp/rx
    cx, cy = c*cxp-s*cyp+(start.x+ex)/2, s*cxp+c*cyp+(start.y+ey)/2
    ux, uy = (xp-cxp)/rx, (yp-cyp)/ry
    vx, vy = (-xp-cxp)/rx, (-yp-cyp)/ry
    begin = math.atan2(uy, ux)
    angle = math.atan2(ux*vy-uy*vx, ux*vx+uy*vy)
    if not sweep and angle > 0: angle -= 2*math.pi
    if sweep and angle < 0: angle += 2*math.pi
    count = max(2, math.ceil(abs(angle)/(2*math.pi)*steps))
    return tuple(Point(cx+c*rx*math.cos(begin+angle*i/count)-s*ry*math.sin(begin+angle*i/count),
                       cy+s*rx*math.cos(begin+angle*i/count)+c*ry*math.sin(begin+angle*i/count))
                 if i<count else end for i in range(1,count+1))


def flatten_path(path: str, *, steps: int = 128) -> tuple[tuple[Point, ...], ...]:
    """Sample pure path curves into subpaths for clipping/intersections.

    The actual renderer retains the original curves. This polyline is used only
    for pure geometry queries, never as a raster or browser-layout substitute.
    """
    if not isinstance(path, str): raise MermaidError('Path must be text', code='INVALID_PATH')
    tokens = _TOKEN.findall(path)
    if _TOKEN.sub('', path).strip(' ,\r\n\t'): raise MermaidError('Invalid path token', code='INVALID_PATH')
    subpaths=[]; points=[]; position=Point(0,0); origin=position; index=0; command=None; control=None; prior=None
    while index<len(tokens):
        if tokens[index].isalpha():
            command=tokens[index]; index+=1
            if command.upper()=='Z':
                if points and points[-1]!=origin: points.append(origin)
                position=origin; control=None; prior='Z'; command=None
                continue
        if command is None or command.upper() not in _ARITY: raise MermaidError('Missing path command',code='INVALID_PATH')
        upper=command.upper(); relative=command.islower(); count=_ARITY[upper]
        if index+count>len(tokens) or any(x.isalpha() for x in tokens[index:index+count]):
            raise MermaidError('Incomplete path segment',code='INVALID_PATH')
        values=tuple(float(x) for x in tokens[index:index+count]); index+=count
        if not all(math.isfinite(x) for x in values): raise MermaidError('Nonfinite path coordinate',code='INVALID_PATH')
        def point(x,y):return Point(x+position.x if relative else x,y+position.y if relative else y)
        start=position
        if upper=='M':
            if points:subpaths.append(tuple(points))
            position=point(*values);origin=position;points=[position];command='l' if relative else 'L';control=None
        elif upper=='L':position=point(*values);points.append(position);control=None
        elif upper=='H':position=Point(values[0]+position.x if relative else values[0],position.y);points.append(position);control=None
        elif upper=='V':position=Point(position.x,values[0]+position.y if relative else values[0]);points.append(position);control=None
        elif upper in {'Q','T'}:
            if upper=='Q': middle=point(*values[:2]);end=point(*values[2:])
            else:
                middle=Point(2*position.x-control.x,2*position.y-control.y) if prior in {'Q','T'} and control else position
                end=point(*values)
            points.extend(Point((1-t)**2*start.x+2*(1-t)*t*middle.x+t*t*end.x,
                                (1-t)**2*start.y+2*(1-t)*t*middle.y+t*t*end.y)
                          for t in (i/steps for i in range(1,steps+1)))
            position=end;control=middle
        elif upper in {'C','S'}:
            if upper=='C':first=point(*values[:2]);second=point(*values[2:4]);end=point(*values[4:])
            else:
                first=Point(2*position.x-control.x,2*position.y-control.y) if prior in {'C','S'} and control else position
                second=point(*values[:2]);end=point(*values[2:])
            points.extend(Point((1-t)**3*start.x+3*(1-t)**2*t*first.x+3*(1-t)*t*t*second.x+t**3*end.x,
                                (1-t)**3*start.y+3*(1-t)**2*t*first.y+3*(1-t)*t*t*second.y+t**3*end.y)
                          for t in (i/steps for i in range(1,steps+1)))
            position=end;control=second
        elif upper=='A':
            arc=_arc(position,values,relative,steps);points.extend(arc);position=arc[-1];control=None
        prior=upper
    if points:subpaths.append(tuple(points))
    return tuple(subpaths)


def path_bounds(path: str) -> Box:
    points=[p for contour in flatten_path(path) for p in contour]
    if not points:return Box(0,0,0,0)
    left=min(p.x for p in points);top=min(p.y for p in points)
    return Box(left,top,max(p.x for p in points)-left,max(p.y for p in points)-top)


def transform_path(path: str, *, dx: float = 0, dy: float = 0,
                   sx: float = 1, sy: float = 1) -> str:
    """Return an affine translate/axis-scale of path values as absolute commands."""
    tokens=_TOKEN.findall(path);index=0;command=None;position=Point(0,0);origin=position;out=[]
    while index<len(tokens):
        if tokens[index].isalpha():
            command=tokens[index];index+=1
            if command.upper()=='Z':out.append('Z');position=origin;command=None;continue
        if command is None or command.upper() not in _ARITY:raise MermaidError('Invalid path command',code='INVALID_PATH')
        upper=command.upper();count=_ARITY[upper];relative=command.islower()
        if index+count>len(tokens):raise MermaidError('Incomplete path',code='INVALID_PATH')
        values=[float(x) for x in tokens[index:index+count]];index+=count
        if upper in {'H','V'}:
            end=Point(values[0]+position.x if relative else values[0],position.y) if upper=='H' else Point(position.x,values[0]+position.y if relative else values[0])
            out.append(f'L {end.x*sx+dx:.17g} {end.y*sy+dy:.17g}');position=end;continue
        if upper=='A':
            ex=values[5]+position.x if relative else values[5];ey=values[6]+position.y if relative else values[6]
            values=[abs(values[0]*sx),abs(values[1]*sy),values[2],values[3],values[4],ex*sx+dx,ey*sy+dy]
            position=Point(ex,ey)
        else:
            points=[Point(values[i]+position.x if relative else values[i],values[i+1]+position.y if relative else values[i+1]) for i in range(0,count,2)]
            position=points[-1];values=[v for point in points for v in (point.x*sx+dx,point.y*sy+dy)]
            if upper=='M':origin=position;command='l' if relative else 'L'
        out.append(upper+' '+' '.join(f'{v:.17g}' for v in values))
    return ' '.join(out)
