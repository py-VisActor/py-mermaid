"""Pure swimlane geometry, ported from direction/geometry.ts (fixed Mermaid)."""
from decimal import Decimal,ROUND_HALF_UP,localcontext
EPS = 1e-3


def fixed(value,digits):
    """ECMAScript toFixed key rounding on the actual binary floating value."""
    value=float(value)
    if value==0:value=0.0
    with localcontext() as ctx:
        ctx.prec=400
        return format(Decimal.from_float(value).quantize(Decimal(1).scaleb(-digits),rounding=ROUND_HALF_UP),f'.{digits}f')


def same_point(a, b, epsilon=EPS):
    return abs(a['x']-b['x']) < epsilon and abs(a['y']-b['y']) < epsilon


def same_x(a, b, epsilon=EPS): return abs(a['x']-b['x']) < epsilon
def same_y(a, b, epsilon=EPS): return abs(a['y']-b['y']) < epsilon
def horizontal(a,b,epsilon=EPS): return same_y(a,b,epsilon) and abs(a['x']-b['x']) > epsilon
def vertical(a,b,epsilon=EPS): return same_x(a,b,epsilon) and abs(a['y']-b['y']) > epsilon
def point(x,y): return {'x':x,'y':y}


def overlap_length(a1,a2,b1,b2):
    return max(0,min(max(a1,a2),max(b1,b2))-max(min(a1,a2),min(b1,b2)))


def segments(points,epsilon=EPS):
    result=[]
    for i,(a,b) in enumerate(zip(points,points[1:])):
        h,v=horizontal(a,b,epsilon),vertical(a,b,epsilon)
        if h or v: result.append(dict(index=i,a=a,b=b,horizontal=h,vertical=v))
    return result


def same_axis_overlap(a,b,epsilon=EPS):
    if a['horizontal'] and b['horizontal'] and same_y(a['a'],b['a'],epsilon):
        return overlap_length(a['a']['x'],a['b']['x'],b['a']['x'],b['b']['x'])
    if a['vertical'] and b['vertical'] and same_x(a['a'],b['a'],epsilon):
        return overlap_length(a['a']['y'],a['b']['y'],b['a']['y'],b['b']['y'])
    return 0


def count_bends(points,epsilon=EPS):
    ss=segments(points,epsilon)
    return sum(a['horizontal']!=b['horizontal'] for a,b in zip(ss,ss[1:]))


def dedupe(points,epsilon=EPS):
    out=[]
    for p in points:
        if not out or not same_point(out[-1],p,epsilon):out.append(point(p['x'],p['y']))
    return out


def classify_three_segment_route(points,epsilon=EPS):
    if not points or len(points)!=4:return None
    p0,p1,p2,p3=points
    if horizontal(p0,p1,epsilon) and vertical(p1,p2,epsilon) and horizontal(p2,p3,epsilon):kind='HVH'
    elif vertical(p0,p1,epsilon) and horizontal(p1,p2,epsilon) and vertical(p2,p3,epsilon):kind='VHV'
    else:return None
    return dict(kind=kind,p0=p0,p1=p1,p2=p2,p3=p3)


def segment_bounds_overlap_rect(a,b,r,buffer=0):
    return max(a['x'],b['x'])>r['left']-buffer and min(a['x'],b['x'])<r['right']+buffer and max(a['y'],b['y'])>r['top']-buffer and min(a['y'],b['y'])<r['bottom']+buffer


def point_inside_rect(p,r,buffer=0):
    return r['left']+buffer<p['x']<r['right']-buffer and r['top']+buffer<p['y']<r['bottom']-buffer


def rect_contains_rect(a,b):
    return a['left']<=b['left'] and a['right']>=b['right'] and a['top']<=b['top'] and a['bottom']>=b['bottom']


def rects_overlap(a,b):
    return a['left']<b['right'] and a['right']>b['left'] and a['top']<b['bottom'] and a['bottom']>b['top']


def inflate_rect(r,margin):
    return dict(left=r['left']-margin,right=r['right']+margin,top=r['top']-margin,bottom=r['bottom']+margin)


def rect_from_center_size(cx,cy,width,height):
    return dict(left=cx-width/2,right=cx+width/2,top=cy-height/2,bottom=cy+height/2)


def rect_of_node(node):
    w,h=node.get('width',0),node.get('height',0)
    return rect_from_center_size(node.get('x',0),node.get('y',0),w,h) if w>0 and h>0 else None


def node_info(node):
    if node.get('isGroup'):return None
    rect=rect_of_node(node)
    return dict(id=str(node.get('id','')),cx=node.get('x',0),cy=node.get('y',0),rect=rect) if rect else None


def port_for_side(node,side):
    r=node['rect'];cx,cy=node['cx'],node['cy']
    return point(cx,r[side]) if side in ('top','bottom') else point(r[side],cy)


def build_port_path(src,src_side,dst,dst_side,anchor,epsilon=EPS):
    sh=src_side in ('left','right');dh=dst_side in ('left','right')
    sx,sy,dx,dy=src['x'],src['y'],dst['x'],dst['y']
    if sh and dh:
        opposing=(src_side=='right' and dst_side=='left' and sx<dx) or (src_side=='left' and dst_side=='right' and sx>dx)
        if opposing:
            if same_y(src,dst,epsilon):return [src,dst]
            mid=(sx+dx)/2
            return [src,point(mid,sy),point(mid,dy),dst]
        if src_side==dst_side:
            if same_y(src,dst,epsilon):return None
            x=min(sx,dx)-anchor if src_side=='left' else max(sx,dx)+anchor
            return [src,point(x,sy),point(x,dy),dst]
        return None
    if not sh and not dh:
        if src_side==dst_side:
            if same_x(src,dst,epsilon):return None
            y=min(sy,dy)-anchor if src_side=='top' else max(sy,dy)+anchor
            return [src,point(sx,y),point(dx,y),dst]
        forward=(src_side=='bottom' and dst_side=='top' and sy<dy) or (src_side=='top' and dst_side=='bottom' and sy>dy)
        if not forward:return None
        if same_x(src,dst,epsilon):return [src,dst]
        mid=(sy+dy)/2
        return [src,point(sx,mid),point(dx,mid),dst]
    if sh:
        forward=(src_side=='right' and dx>sx) or (src_side=='left' and dx<sx)
        dst_forward=(dst_side=='top' and sy<dy) or (dst_side=='bottom' and sy>dy)
        return [src,point(dx,sy),dst] if forward and dst_forward else None
    forward=(src_side=='bottom' and dy>sy) or (src_side=='top' and dy<sy)
    dst_forward=(dst_side=='left' and sx<dx) or (dst_side=='right' and sx>dx)
    return [src,point(sx,dy),dst] if forward and dst_forward else None


def build_same_side_track_path(src,side,dst,track):
    return [src,point(track,src['y']),point(track,dst['y']),dst] if side in ('left','right') else [src,point(src['x'],track),point(dst['x'],track),dst]


def collect_real_node_bounds(nodes):
    infos={};rects=[]
    for n in nodes:
        if n.get('isEdgeLabel'):continue
        info=node_info(n)
        if info:infos[info['id']]=info;rects.append(dict(id=info['id'],rect=info['rect']))
    return infos,rects


def collect_node_rect_entries(nodes):
    real=[];labels=[]
    for n in nodes:
        info=node_info(n)
        if info:(labels if n.get('isEdgeLabel') else real).append(dict(id=info['id'],rect=info['rect']))
    return real,labels


def collect_layout_node_rects(nodes,include_edge_labels=True):
    return [dict(nodeId=n.get('id'),**rect_from_center_size(n.get('x',0),n.get('y',0),n.get('width',0),n.get('height',0))) for n in nodes if not n.get('isGroup') and (include_edge_labels or not n.get('isEdgeLabel'))]


def node_pair_geometry(edge,infos,epsilon=EPS):
    src,dst=edge.get('start'),edge.get('end')
    if not src or not dst or src not in infos or dst not in infos:return None
    a,b=infos[src],infos[dst]
    return dict(srcId=src,dstId=dst,srcInfo=a,dstInfo=b,collinearX=abs(a['cx']-b['cx'])<epsilon,collinearY=abs(a['cy']-b['cy'])<epsilon)


def segment_hits_any_rect(a,b,rects,exclude_ids=(),shrink=0):
    return any(e['id'] not in exclude_ids and segment_bounds_overlap_rect(a,b,e['rect'],-shrink) for e in rects)


def orthogonal_segments_cross(a,b,c,d,epsilon=EPS,endpoint_tolerance=1e-6):
    ah,av,bh,bv=same_y(a,b,epsilon),same_x(a,b,epsilon),same_y(c,d,epsilon),same_x(c,d,epsilon)
    if (ah and bh) or (av and bv) or not (ah or av) or not (bh or bv):return False
    ha,hb=(a,b) if ah else (c,d);va,vb=(a,b) if av else (c,d)
    x,y=va['x'],ha['y']
    if not min(ha['x'],hb['x'])<=x<=max(ha['x'],hb['x']) or not min(va['y'],vb['y'])<=y<=max(va['y'],vb['y']):return False
    p=point(x,y)
    return not (any(same_point(p,e,endpoint_tolerance) for e in (ha,hb)) and any(same_point(p,e,endpoint_tolerance) for e in (va,vb)))


def same_axis_segments_overlap(a,b,c,d,epsilon=EPS):
    if same_x(a,b,epsilon) and same_x(c,d,epsilon) and same_x(a,c,epsilon):return overlap_length(a['y'],b['y'],c['y'],d['y'])>epsilon
    if same_y(a,b,epsilon) and same_y(c,d,epsilon) and same_y(a,c,epsilon):return overlap_length(a['x'],b['x'],c['x'],d['x'])>epsilon
    return False


def segment_conflicts_with_any_edge(a,b,edges,exclude_edge=None,epsilon=EPS,skip_degenerate_other=False):
    for other in edges:
        if other is exclude_edge or other.get('isLayoutOnly'):continue
        pts=other.get('points') or []
        for c,d in zip(pts,pts[1:]):
            if skip_degenerate_other and same_point(c,d,epsilon):continue
            if orthogonal_segments_cross(a,b,c,d,epsilon) or same_axis_segments_overlap(a,b,c,d,epsilon):return True
    return False


def strictly_cross(a,b,c,d,epsilon=EPS):
    ah,av,bh,bv=same_y(a,b,epsilon),same_x(a,b,epsilon),same_y(c,d,epsilon),same_x(c,d,epsilon)
    if not ((ah and bv) or (av and bh)):return False
    ha,hb=(a,b) if ah else (c,d);va,vb=(c,d) if ah else (a,b)
    return min(ha['x'],hb['x'])+epsilon<va['x']<max(ha['x'],hb['x'])-epsilon and min(va['y'],vb['y'])+epsilon<ha['y']<max(va['y'],vb['y'])-epsilon


def orthogonalize(points):
    if not points:return []
    cleaned=[points[0]]
    for cur in points[1:]:
        prev=cleaned[-1]
        if not same_x(prev,cur) and not same_y(prev,cur):
            incoming_vertical=len(cleaned)>=2 and same_x(cleaned[-2],prev)
            cleaned.append(point(prev['x'],cur['y']) if incoming_vertical else point(cur['x'],prev['y']))
        cleaned.append(cur)
    return dedupe(cleaned)


def simplify(points):
    if len(points)<3:return points
    work=list(points)
    for _ in range(32):
        out=[];changed=False;i=0
        while i<len(work):
            cur=work[i];prev=out[-1] if out else None;nxt=work[i+1] if i+1<len(work) else None
            if prev is not None and nxt is not None:
                if same_point(prev,nxt):i+=2;changed=True;continue
                axis='y' if same_x(prev,cur) and same_x(cur,nxt) else 'x' if same_y(prev,cur) and same_y(cur,nxt) else None
                if axis and min(prev[axis],nxt[axis])+EPS<cur[axis]<max(prev[axis],nxt[axis])-EPS:
                    i+=1;changed=True;continue
            out.append(cur);i+=1
        work=out
        if not changed:break
    return work
