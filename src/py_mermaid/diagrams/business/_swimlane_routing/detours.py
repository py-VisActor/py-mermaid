"""Source bounded bend minimization preserving face claims and crossings."""
import math
from .geometry import (collect_real_node_bounds,build_port_path,build_same_side_track_path,
    count_bends,segments,orthogonal_segments_cross,same_axis_overlap,
    segment_hits_any_rect,port_for_side)


def simplify_detours(edges,nodes):
    infos,rects=collect_real_node_bounds(nodes);sides=('top','bottom','left','right')
    outside={s:(min((e['rect'][s] for e in rects),default=math.inf)-20 if s in ('top','left') else max((e['rect'][s] for e in rects),default=-math.inf)+20) for s in sides}
    def candidates(a,side_a,b,side_b):
        result=[];base=build_port_path(a,side_a,b,side_b,20)
        if base:result.append(base)
        if side_a==side_b:result.append(build_same_side_track_path(a,side_a,b,outside[side_a]))
        return result
    def conflicts(path,edge,include_incident=False):
        result=0;ss=segments(path)
        for other in edges:
            if other is edge or other.get('isLayoutOnly'):continue
            if not include_incident and edge.get('start') and edge.get('end') and (other.get('start') in (edge['start'],edge['end']) or other.get('end') in (edge['start'],edge['end'])):continue
            for a in ss:
                for b in segments(other.get('points') or []):
                    if orthogonal_segments_cross(a['a'],a['b'],b['a'],b['b'],endpoint_tolerance=1e-3):result+=1
                    elif same_axis_overlap(a,b)>=8:result+=1
        return result
    def nearest(p,info):
        r=info['rect']
        return min(sides,key=lambda s:abs(p['y' if s in ('top','bottom') else 'x']-r[s]))
    claims={}
    def claim(n,s,eid):claims.setdefault(n,[]).append((s,eid))
    for e in edges:
        pts=e.get('points') or []
        if e.get('isLayoutOnly') or not pts:continue
        for nid,p in ((e.get('start'),pts[0]),(e.get('end'),pts[-1])):
            if nid in infos:claim(nid,nearest(p,infos[nid]),e.get('id',''))
    for edge in edges:
        pts=edge.get('points') or []
        if edge.get('isLayoutOnly') or len(pts)<2:continue
        bends=count_bends(pts)
        if bends<4:continue
        src_id,dst_id=edge.get('start'),edge.get('end')
        if src_id not in infos or dst_id not in infos:continue
        src,dst=infos[src_id],infos[dst_id];eid=edge.get('id','')
        current_cross=conflicts(pts,edge,True);non_incident=conflicts(pts,edge)
        best=None;best_cross=current_cross;best_bends=bends
        for ss in sides:
            if any(s==ss and i!=eid for s,i in claims.get(src_id,[])):continue
            a=port_for_side(src,ss)
            for ds in sides:
                if any(s==ds and i!=eid for s,i in claims.get(dst_id,[])):continue
                b=port_for_side(dst,ds)
                for path in candidates(a,ss,b,ds):
                    if any(segment_hits_any_rect(p,q,rects,[src_id,dst_id],1) for p,q in zip(path,path[1:])):continue
                    pb=count_bends(path)
                    if current_cross>0:
                        pc=conflicts(path,edge,True)
                        if pc>best_cross or (pc==best_cross and pb>=best_bends):continue
                        best_cross,best_bends,best=pc,pb,path
                    else:
                        if conflicts(path,edge)>non_incident:continue
                        if pb<best_bends:best_bends,best=pb,path
        if best:
            edge['points']=best
            for nid in (src_id,dst_id):claims[nid]=[(s,i) for s,i in claims.get(nid,[]) if i!=eid]
            claim(src_id,nearest(best[0],src),eid);claim(dst_id,nearest(best[-1],dst),eid)
