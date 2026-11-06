"""Source perpendicular port swaps and short terminal stub collapse."""
import math
from .geometry import (point,dedupe,collect_real_node_bounds,collect_node_rect_entries,
    classify_three_segment_route,node_pair_geometry,same_point,same_x,same_y,
    horizontal,vertical,rect_of_node,point_inside_rect,segment_hits_any_rect,
    segment_conflicts_with_any_edge,strictly_cross,fixed)


def port_swap(edges,nodes):
    infos,rects=collect_real_node_bounds(nodes)
    for e in edges:
        if e.get('isLayoutOnly') or len(e.get('points') or [])<4:continue
        route=classify_three_segment_route(dedupe(e['points'],1e-6),1e-6)
        pair=node_pair_geometry(e,infos,1e-6)
        if not route or not pair or pair['collinearX'] or pair['collinearY']:continue
        src,dst=pair['srcInfo'],pair['dstInfo'];r=src['rect'];p3=route['p3'];hvh=route['kind']=='HVH'
        for delta in (0,8,-8,16,-16):
            if hvh:
                x=src['cx']+delta;y=r['bottom'] if dst['cy']>src['cy'] else r['top']
                if not r['left']+1e-6<x<r['right']-1e-6:continue
                a,b,c=point(x,y),point(x,p3['y']),dict(p3)
            else:
                x=r['right'] if dst['cx']>src['cx'] else r['left'];y=src['cy']+delta
                if not r['top']+1e-6<y<r['bottom']-1e-6:continue
                a,b,c=point(x,y),point(p3['x'],y),dict(p3)
            first=same_point(a,b,1e-6);second=same_point(b,c,1e-6)
            if first and second:continue
            if not first and segment_hits_any_rect(a,b,rects,[pair['srcId']],1):continue
            if not second and segment_hits_any_rect(b,c,rects,[pair['dstId']],1):continue
            if not first and segment_conflicts_with_any_edge(a,b,edges,e,epsilon=1e-6,skip_degenerate_other=True):continue
            if not second and segment_conflicts_with_any_edge(b,c,edges,e,epsilon=1e-6,skip_degenerate_other=True):continue
            e['points']=[b,c] if first else [a,b] if second else [a,b,c];break


def collapse_short_stub(edges,nodes):
    real,labels=collect_node_rect_entries(nodes.values())
    for edge in edges:
        if edge.get('isLayoutOnly') or len(edge.get('points') or [])<4:continue
        pts=dedupe(edge['points'])
        if len(pts)<4:continue
        end,penult,prev=pts[-1],pts[-2],pts[-3]
        last_dx,last_dy=end['x']-penult['x'],end['y']-penult['y']
        last_len=math.hypot(last_dx,last_dy)
        if last_len>=10 or last_len<1e-3:continue
        pen_dx,pen_dy=penult['x']-prev['x'],penult['y']-prev['y']
        if math.hypot(pen_dx,pen_dy)<1e-3:continue
        last_h,last_v=horizontal(penult,end),vertical(penult,end)
        pen_h,pen_v=horizontal(prev,penult),vertical(prev,penult)
        if not ((last_h and pen_v) or (last_v and pen_h)):continue
        dst_id,src_id=edge.get('end'),edge.get('start');dst=nodes.get(dst_id)
        r=rect_of_node(dst) if dst else None
        if not r:continue
        cx,cy=dst.get('x',0),dst.get('y',0)
        if pen_v:new_prev=point(cx,prev['y']);new_end=point(cx,r['bottom'] if pen_dy<0 else r['top'])
        else:new_prev=point(prev['x'],cy);new_end=point(r['right'] if pen_dx>0 else r['left'],cy)
        if segment_hits_any_rect(new_prev,new_end,real,[dst_id] if dst_id else [],-2):continue
        if segment_hits_any_rect(new_prev,new_end,labels,[],-2):continue
        src=nodes.get(src_id);sr=rect_of_node(src) if src else None
        if sr and point_inside_rect(new_prev,sr,2):continue
        def key(a,b):return tuple(fixed(p[axis],3) for p in (a,b) for axis in ('x','y'))
        own={key(a,b) for a,b in zip(pts,pts[1:])}
        def crosses(a,b):
            for other in edges:
                if other is edge or other.get('isLayoutOnly'):continue
                op=other.get('points') or []
                for c,d in zip(op,op[1:]):
                    if key(c,d) not in own and strictly_cross(a,b,c,d):return True
            return False
        if crosses(new_prev,new_end):continue
        before=pts[-4]
        if segment_hits_any_rect(before,new_prev,real,[i for i in (src_id,dst_id) if i],-2) or crosses(before,new_prev):continue
        new_pts=[*pts[:-3],new_prev,new_end];edge['points']=new_pts
        label=nodes.get(edge.get('labelNodeId'))
        if not label or label.get('width',0)<=0 or label.get('height',0)<=0:continue
        best_len=-1;best=None
        for a,b in zip(new_pts,new_pts[1:]):
            length=math.hypot(b['x']-a['x'],b['y']-a['y'])
            fits=(same_y(a,b) and length>=label['width']+2) or (same_x(a,b) and length>=label['height']+2)
            if fits and length>best_len:best_len=length;best=point((a['x']+b['x'])/2,(a['y']+b['y'])/2)
        if best:label.update(best)
