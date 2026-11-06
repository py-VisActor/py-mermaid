"""Source label candidate ranking, lane containment and clearance guards."""
from .geometry import (EPS,dedupe,inflate_rect,rect_of_node,rects_overlap,
    rect_contains_rect,rect_from_center_size,segment_bounds_overlap_rect)


def _marker_rect(points,start):
    tip,inner=(points[0],points[1]) if start else (points[-1],points[-2])
    dx,dy=inner['x']-tip['x'],inner['y']-tip['y']
    if abs(dx)+abs(dy)<EPS:return None
    if abs(dy)<=EPS:
        x2=tip['x']+(10 if dx>0 else -10 if dx<0 else 0)
        return dict(left=min(tip['x'],x2),right=max(tip['x'],x2),top=tip['y']-7,bottom=tip['y']+7)
    if abs(dx)<=EPS:
        y2=tip['y']+(10 if dy>0 else -10 if dy<0 else 0)
        return dict(left=tip['x']-7,right=tip['x']+7,top=min(tip['y'],y2),bottom=max(tip['y'],y2))
    return dict(left=min(tip['x'],inner['x']),right=max(tip['x'],inner['x']),top=min(tip['y'],inner['y']),bottom=max(tip['y'],inner['y']))


def _own_marker_overlap(rect,points):
    pts=dedupe(points)
    if len(pts)<2:return False
    return any(r and rects_overlap(rect,r) for r in (_marker_rect(pts,True),_marker_rect(pts,False)))


def anchor_labels(edges,nodes):
    all_segments=[(e.get('id'),a,b) for e in edges if not e.get('isLayoutOnly') for a,b in zip(e.get('points') or [],(e.get('points') or [])[1:])]
    foreign=[];lanes=[];placed=[]
    for n in nodes.values():
        r=rect_of_node(n)
        if n.get('isGroup') and not n.get('parentId'):
            if r:lanes.append((n['id'],r))
        elif not n.get('isGroup') and not n.get('isEdgeLabel') and r:foreign.append((n['id'],r))
    def foreign_node_overlap(label_id,r):
        buffered=inflate_rect(r,3)
        return any(i!=label_id and rects_overlap(buffered,nr) for i,nr in foreign)
    def foreign_edge_overlap(edge_id,r):
        buffered=inflate_rect(r,3)
        return any(i!=edge_id and segment_bounds_overlap_rect(a,b,buffered) for i,a,b in all_segments)
    def placed_overlap(label_id,r):return any(i!=label_id and rects_overlap(r,pr) for i,pr in placed)
    def inclusive(anchor,r):return r['left']-EPS<=anchor[0]<=r['right']+EPS and r['top']-EPS<=anchor[1]<=r['bottom']+EPS
    for edge in edges:
        if edge.get('isLayoutOnly'):continue
        label_id=edge.get('labelNodeId');label=nodes.get(label_id);pts=edge.get('points') or []
        if not label or len(pts)<2:continue
        lw,lh=label.get('width',0),label.get('height',0)
        if lw<=0 or lh<=0:continue
        ss=[]
        for i,(a,b) in enumerate(zip(pts,pts[1:])):
            dx,dy=abs(a['x']-b['x']),abs(a['y']-b['y'])
            if (dx<EPS and dy<EPS) or (dx>=EPS and dy>=EPS):continue
            ss.append(dict(idx=i,length=dx+dy,h=dx>=EPS,mid=((a['x']+b['x'])/2,(a['y']+b['y'])/2)))
        if not ss:continue
        middle=[s for s in ss if 0<s['idx']<len(ss)-1] if len(ss)>=3 else ss
        pool=middle or ss;long_h=lw>=lh
        def rank(pool):return sorted(pool,key=lambda s:(s['h']!=long_h,s['length']<(lw if s['h'] else lh)+2,-s['length']))
        def placement(anchor):
            centered=rect_from_center_size(*anchor,lw,lh)
            for lid,r in lanes:
                if rect_contains_rect(r,centered):return lid,anchor,centered
            containing=next(((i,r) for i,r in lanes if inclusive(anchor,r)),None)
            if not containing:return None
            lid,r=containing;min_x,max_x=r['left']+lw/2+1,r['right']-lw/2-1;min_y,max_y=r['top']+lh/2+1,r['bottom']-lh/2-1
            if min_x>max_x or min_y>max_y:return None
            clamped=(min(max_x,max(min_x,anchor[0])),min(max_y,max(min_y,anchor[1])))
            rect=rect_from_center_size(*clamped,lw,lh)
            return (lid,clamped,rect) if inclusive(anchor,rect) else None
        def clears(s,anchor):
            required=(lw if s['h'] else lh)/2+12;axis=0 if s['h'] else 1;key='x' if s['h'] else 'y'
            if s is ss[0] and abs(anchor[axis]-pts[s['idx']][key])+EPS<required:return False
            if s is ss[-1] and abs(anchor[axis]-pts[s['idx']+1][key])+EPS<required:return False
            return True
        def try_pool(pool):
            for s in rank(pool):
                a,b=pts[s['idx']],pts[s['idx']+1]
                for t in (.5,.25,.75,.05,.95,.15,.85,.1,.9):
                    anchor=(a['x']+(b['x']-a['x'])*t,a['y']+(b['y']-a['y'])*t)
                    if not clears(s,anchor):continue
                    p=placement(anchor)
                    if not p:continue
                    lid,anchor,r=p
                    if _own_marker_overlap(r,pts) or placed_overlap(label_id,r):continue
                    if not foreign_node_overlap(label_id,r) and not foreign_edge_overlap(edge.get('id'),r):return lid,anchor
            return None
        def fallback(require_clearance,allow_edge_overlap=False):
            for s in rank(ss):
                anchor=s['mid']
                if require_clearance and not clears(s,anchor):continue
                p=placement(anchor)
                if not p:continue
                lid,anchor,r=p
                if _own_marker_overlap(r,pts) or placed_overlap(label_id,r) or foreign_node_overlap(label_id,r):continue
                if allow_edge_overlap or not foreign_edge_overlap(edge.get('id'),r):return lid,anchor
            return None
        chosen=try_pool(pool) or (try_pool(ss) if len(pool)<len(ss) else None) or fallback(True) or fallback(False) or fallback(False,True)
        if chosen:
            lid,(x,y)=chosen;label.update(x=x,y=y,parentId=lid)
            rect=rect_from_center_size(x,y,lw,lh)
            prior=next((i for i,p in enumerate(placed) if p[0]==label_id),None)
            if prior is not None:placed[prior]=(label_id,rect)
            else:placed.append((label_id,rect))
