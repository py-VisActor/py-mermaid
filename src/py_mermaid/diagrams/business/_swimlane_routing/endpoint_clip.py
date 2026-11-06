"""Source endpoint clipping, corner clearance and renderer handoff."""
from .geometry import EPS,point,same_x,same_y,same_point,point_inside_rect,rect_of_node,dedupe,simplify,orthogonalize


def _context(edge,nodes):
    pts=edge.get('points')
    if edge.get('isLayoutOnly') or not pts or len(pts)<2:return None
    src=nodes.get(edge.get('start'));dst=nodes.get(edge.get('end'))
    return pts,rect_of_node(src) if src else None,rect_of_node(dst) if dst else None


def _enter(outside,inside,r):
    if same_y(outside,inside):return point(r['left'] if outside['x']<r['left'] else r['right'],outside['y'])
    if same_x(outside,inside):return point(outside['x'],r['top'] if outside['y']<r['top'] else r['bottom'])
    return point(min(r['right'],max(r['left'],outside['x'])),min(r['bottom'],max(r['top'],outside['y'])))


def _clip(points,r,start):
    step=1 if start else -1;i=0 if start else len(points)-1
    while 0<=i<len(points) and point_inside_rect(points[i],r,.5):i+=step
    if not 0<=i<len(points) or not 0<=i-step<len(points):return points
    entry=_enter(points[i],points[i-step],r)
    return [entry,*points[i:]] if start else [*points[:i+1],entry]


def terminal_side(endpoint,adjacent,r):
    y_within=r['top']-EPS<=endpoint['y']<=r['bottom']+EPS
    x_within=r['left']-EPS<=endpoint['x']<=r['right']+EPS
    if same_y(endpoint,adjacent) and y_within:
        if abs(endpoint['x']-r['left'])<EPS:return 'left'
        if abs(endpoint['x']-r['right'])<EPS:return 'right'
    if same_x(endpoint,adjacent) and x_within:
        if abs(endpoint['y']-r['top'])<EPS:return 'top'
        if abs(endpoint['y']-r['bottom'])<EPS:return 'bottom'
    return None


def clearance_range(lo,hi):
    return (lo+4,hi-4) if lo+4<=hi-4 else ((lo+hi)/2,(lo+hi)/2)


def _clear_straight(points,src,dst):
    if len(points)!=2:return points
    a,b=points;h=same_y(a,b)
    if not h and not same_x(a,b):return points
    ranges=[]
    for r,e,adj in ((src,a,b),(dst,b,a)):
        side=terminal_side(e,adj,r) if r else None
        if side and (side in ('left','right'))==h:
            ranges.append(clearance_range(r['top'],r['bottom']) if h else clearance_range(r['left'],r['right']))
    if not ranges:return points
    lo=max(r[0] for r in ranges);hi=min(r[1] for r in ranges)
    if lo>hi:return points
    axis='y' if h else 'x';current=a[axis];new=min(hi,max(lo,current))
    if abs(new-current)<EPS:return points
    return [dict(a,**{axis:new}),dict(b,**{axis:new})]


def clip_endpoints(edges,nodes):
    for e in edges:
        c=_context(e,nodes)
        if not c:continue
        pts,src,dst=c;out=list(pts)
        if src:out=_clip(out,src,True)
        if dst:out=_clip(out,dst,False)
        out=simplify(orthogonalize(out))
        e['points']=simplify(orthogonalize(_clear_straight(out,src,dst)))


def _adjacent(points,index,step):
    i=index+step
    while 0<=i<len(points):
        if not same_point(points[i],points[index]):return points[i]
        i+=step
    return points[index+step] if 0<=index+step<len(points) else None


def _snap(inner,endpoint,r,approach=False):
    if same_y(inner,endpoint):
        if endpoint['y']<r['top']-EPS or endpoint['y']>r['bottom']+EPS:return endpoint
        if approach:
            if inner['x']<r['left']-EPS:return point(r['left'],inner['y'])
            if inner['x']>r['right']+EPS:return point(r['right'],inner['y'])
        return point(r['left'] if abs(endpoint['x']-r['left'])<=abs(endpoint['x']-r['right']) else r['right'],inner['y'])
    if same_x(inner,endpoint):
        if endpoint['x']<r['left']-EPS or endpoint['x']>r['right']+EPS:return endpoint
        if approach:
            if inner['y']<r['top']-EPS:return point(inner['x'],r['top'])
            if inner['y']>r['bottom']+EPS:return point(inner['x'],r['bottom'])
        return point(inner['x'],r['top'] if abs(endpoint['y']-r['top'])<=abs(endpoint['y']-r['bottom']) else r['bottom'])
    return endpoint


def _border_side(a,b,r):
    x_within=min(a['x'],b['x'])>=r['left']-EPS and max(a['x'],b['x'])<=r['right']+EPS
    y_within=min(a['y'],b['y'])>=r['top']-EPS and max(a['y'],b['y'])<=r['bottom']+EPS
    for side in ('top','bottom'):
        if abs(a['y']-r[side])<EPS and abs(b['y']-r[side])<EPS and x_within:return side
    for side in ('left','right'):
        if abs(a['x']-r[side])<EPS and abs(b['x']-r[side])<EPS and y_within:return side
    return None


def _outward(side,a,b,r):
    if side=='top':return same_x(a,b) and b['y']<r['top']-EPS
    if side=='bottom':return same_x(a,b) and b['y']>r['bottom']+EPS
    if side=='left':return same_y(a,b) and b['x']<r['left']-EPS
    return same_y(a,b) and b['x']>r['right']+EPS


def _collapse_border(points,r,start):
    if len(points)<3:return points
    a,b,c=points[:3] if start else (points[-1],points[-2],points[-3])
    side=_border_side(a,b,r)
    if side and _outward(side,b,c,r):return points[1:] if start else points[:-1]
    return points


def _clear_corner(points,r,start):
    if len(points)<2:return points
    index=0 if start else len(points)-1;step=1 if start else -1;endpoint=points[index]
    adj=_adjacent(points,index,step)
    side=terminal_side(endpoint,adj,r) if adj else None
    if not side:return points
    h=side in ('left','right');axis='y' if h else 'x'
    lo,hi=clearance_range(r['top'],r['bottom']) if h else clearance_range(r['left'],r['right'])
    value=min(hi,max(lo,endpoint[axis]));adjusted=dict(endpoint,**{axis:value})
    if same_point(endpoint,adjusted):return points
    out=[dict(p) for p in points];i=index
    while 0<=i<len(points):
        if not (same_y(points[i],endpoint) if h else same_x(points[i],endpoint)):break
        out[i][axis]=value;i+=step
    return out


def _snap_collapse(points,src,dst):
    out=points
    if src:
        adjacent=_adjacent(out,0,1)
        if adjacent:out=[_snap(adjacent,out[0],src),*out[1:]]
        out=_collapse_border(out,src,True)
    if dst:
        adjacent=_adjacent(out,len(out)-1,-1)
        if adjacent:out=[*out[:-1],_snap(adjacent,out[-1],dst,True)]
        out=_collapse_border(out,dst,False)
    cleared=_clear_straight(out,src,dst)
    if cleared is not out or len(out)==2:return cleared
    if src:out=_clear_corner(out,src,True)
    if dst:out=_clear_corner(out,dst,False)
    return out


def prepare_endpoints(edges,nodes):
    for e in edges:
        c=_context(e,nodes)
        if not c:continue
        pts,src,dst=c;out=_snap_collapse(dedupe(pts),src,dst)
        e['points']=out if len(out)<3 else [out[0],dict(out[0]),*out[1:-1],out[-1],dict(out[-1])]
