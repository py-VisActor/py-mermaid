"""Pure fixed-Mermaid sequence message geometry, no Canvas/DOM objects.

Source sequenceRenderer.ts activationBounds:896, buildMessageModel:1867,
drawCentralConnection:289 and drawMessage:468-744; svgDraw.js marker paths.
Actor and activation coordinates are supplied by the temporal layout owner.
"""
from dataclasses import dataclass
import math


_HALF={
    '-|\\':'solidTopArrowHead','-|/':'solidBottomArrowHead',
    '-\\\\':'stickTopArrowHead','-//':'stickBottomArrowHead',
    '/|-':'solidBottomArrowHead','\\|-':'solidTopArrowHead',
    '//-':'stickBottomArrowHead','\\\\-':'stickTopArrowHead',
}


@dataclass(frozen=True)
class MessageGeometry:
    startx: float
    stopx: float
    from_bounds: float
    to_bounds: float
    path: str
    painted_start: tuple[float,float]
    painted_end: tuple[float,float]
    start_tangent: tuple[float,float]
    end_tangent: tuple[float,float]
    central_circles: tuple[float,...]
    number_x: float | None
    start_marker: str
    end_marker: str
    dashed: bool
    self_message: bool


def activation_bounds(center,level,width):
    """Union all currently active bars with the source +/-1px lifeline."""
    if not level:return center-1,center+1
    return min(center-1,center-width/2),max(center+1,center+level*width/2)


def message_geometry(arrow,connection,from_center,to_center,source_level,target_level,
                     activation_width,*,y,numbered=False,look='classic',activate=False,
                     self_reference=False,right_angles=False,loop_width=75,
                     start_override=None,end_override=None):
    """Return source model anchors separately from actual numbered shaft ends.

    Number adjustments set x1/x2 attributes on SVG *lines*. They do not alter
    an SVG self path; its separate +10 start rule is retained explicitly.
    """
    base=arrow.replace('--','-');reverse=arrow.startswith(('/','\\'))
    bidirectional=base=='<<->>';half=base in _HALF
    solid_half=half and '|' in base
    left,right=activation_bounds(from_center,source_level,activation_width)
    to_left,to_right=activation_bounds(to_center,target_level,activation_width)
    to_rightward=left<=to_left;sign=1 if to_rightward else -1
    start=right if to_rightward else left;stop=to_left if to_rightward else to_right
    if look=='neo':
        if arrow!='->':stop-=sign*3  # dotted-open is deliberately not exempt
        if bidirectional:start+=sign*3
    if connection in ('source','dual'):
        start+=4
        if bidirectional and not to_rightward:start-=6
    if self_reference:stop=start
    else:
        if activate and abs(to_left-to_right)<=2:stop-=sign*(activation_width/2-1)
        if base!='->' and not (half and (reverse or not solid_half)):stop-=sign*3
        if bidirectional or reverse and solid_half:start+=sign*3
    # Creation/destruction attachment is resolved by the existing actor-shape
    # lifecycle contract; it replaces that model endpoint rather than adding
    # a second generic lifeline/activation offset.
    if start_override is not None:start=start_override
    if end_override is not None:stop=end_override
    from_bounds=min(left,right,to_left,to_right);to_bounds=max(left,right,to_left,to_right)
    self_message=start==stop
    a,b=start,stop
    if self_message:
        a=start+(10 if numbered and (reverse or bidirectional) else 0)
        end_y=y+(25 if right_angles else 20)
        if right_angles:
            ex=start+loop_width
            path=f'M {a} {y} H {ex} V {end_y} H {start}'
            start_tangent=(ex-a,0);end_tangent=(start-ex,0)
        else:
            path=f'M {a} {y} C {a+60} {y-10} {start+60} {y+30} {start} {end_y}'
            start_tangent=(60,-10);end_tangent=(-60,-10)
        painted_start=(a,y);painted_end=(start,end_y)
    else:
        if numbered:
            has_central=bool(connection)
            if bidirectional:
                a=start+12 if start<stop else start-6+(-5 if has_central else 0)+(-7.5 if connection in ('source','dual') else 0)
            elif reverse:
                b=stop-12 if stop>start else stop-6
                if stop<=start and connection in ('source','dual'):a-=7.5
                if has_central:b+=15
            else:a=start+6
        path=f'M {a} {y} L {b} {y}'
        painted_start=(a,y);painted_end=(b,y);start_tangent=end_tangent=(b-a,0)
    circles=[];circle_from,circle_to=from_center,to_center
    circle_sign=1 if from_center<=to_center else -1
    if numbered:
        if connection in ('source','dual') and not reverse:circle_from+=circle_sign*16.5
        if connection in ('target','dual') and reverse:circle_to-=circle_sign*16.5
    if connection in ('source','dual'):circles.append(circle_from)
    if connection in ('target','dual'):circles.append(circle_to)
    number_x=None
    if numbered:
        if self_message:number_x=from_bounds+1
        elif reverse:number_x=to_bounds-1 if start<=stop else from_bounds+1
        else:number_x=from_bounds+1 if start<=stop else to_bounds-1
    start_marker=end_marker=''
    if half:
        if reverse:start_marker=_HALF[base]
        else:end_marker=_HALF[base]
    elif bidirectional:start_marker=end_marker='arrowhead'
    elif base=='->>':end_marker='arrowhead'
    elif base.endswith('x'):end_marker='crosshead'
    elif base.endswith(')'):end_marker='filled-head'
    return MessageGeometry(start,stop,from_bounds,to_bounds,path,painted_start,painted_end,
        start_tangent,end_tangent,tuple(circles),number_x,start_marker,end_marker,'--' in arrow,self_message)


# markerUnits is userSpaceOnUse except the original default strokeWidth for
# filled-head/crosshead. refX/refY are part of the geometry, not ad hoc gaps.
_MARKERS={
    'arrowhead':('M-1 0L10 5L0 10Z',7.9,5,'point','signal','signal',1,False),
    'filled-head':('M18 7L9 13L14 7L9 1Z',15.5,7,'open','text','none',0,True),
    'crosshead':('M1 2L6 7M6 2L1 7',4,4.5,'cross','signal','signal',4/3,True),
    'solidTopArrowHead':('M0 0L10 8L0 8Z',7.9,7.25,'half','text','none',0,False),
    'solidBottomArrowHead':('M0 0L10 0L0 8Z',7.9,.75,'half','text','none',0,False),
    'stickTopArrowHead':('M0 0L7 7',7.5,7,'half','none','black',1.5,False),
    'stickBottomArrowHead':('M0 7L7 0',7.5,0,'half','none','black',1.5,False),
}


def marker_geometry(name,point,tangent,*,at_start=False,line_width=1.5):
    path,refx,refy,kind,fill,stroke,width,relative=_MARKERS[name]
    dx,dy=tangent
    if at_start:dx,dy=-dx,-dy
    length=math.hypot(dx,dy)
    if not length:dx,dy,length=(1,0,1)
    scale=line_width if relative else 1
    a,b=dx/length*scale,dy/length*scale;c,d=-b,a;x,y=point
    transform=(a,b,c,d,x-a*refx-c*refy,y-b*refx-d*refy)
    return path,transform,kind,fill,stroke,width*scale
