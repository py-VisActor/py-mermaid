"""Non-mutating final source quality diagnostics, not a success fallback."""
import logging
from .geometry import collect_layout_node_rects, segment_bounds_overlap_rect


def _intersects(a,b,c,d):
    ux,uy=b['x']-a['x'],b['y']-a['y'];vx,vy=d['x']-c['x'],d['y']-c['y']
    cross=ux*vy-uy*vx
    if abs(cross)<1e-10:return False
    dx,dy=c['x']-a['x'],c['y']-a['y']
    t=(dx*vy-dy*vx)/cross;u=(dx*uy-dy*ux)/cross
    return .01<t<.99 and .01<u<.99


def validate(layout):
    nodes=layout.get('nodes',[]);edges=layout.get('edges',[]);issues=[]
    if not nodes or not edges:return issues
    rects=collect_layout_node_rects(nodes);all_segments=[]
    for e in edges:
        if e.get('isLayoutOnly'):continue
        pts=e.get('points') or []
        if len(pts)<2:continue
        start,end=e.get('start'),e.get('end');own_label=e.get('labelNodeId');eid=e.get('id',f'{start}->{end}')
        for r in rects:
            if r['nodeId'] in (start,end) or own_label and r['nodeId']==own_label:continue
            for i,(a,b) in enumerate(zip(pts,pts[1:])):
                if segment_bounds_overlap_rect(a,b,r,-1):
                    issues.append(dict(type='edge-node-overlap',edgeId=eid,targetId=r['nodeId'],detail=f'segment {i} passes through node "{r["nodeId"]}"'));break
        all_segments.extend(dict(edgeId=eid,start=start,end=end,p1=a,p2=b) for a,b in zip(pts,pts[1:]))
    pairs=set()
    for i,a in enumerate(all_segments):
        for b in all_segments[i+1:]:
            if a['edgeId']==b['edgeId'] or a['start'] in (b['start'],b['end']) or a['end'] in (b['start'],b['end']):continue
            if _intersects(a['p1'],a['p2'],b['p1'],b['p2']):
                key=tuple(sorted((str(a['edgeId']),str(b['edgeId']))))
                if key not in pairs:
                    pairs.add(key);issues.append(dict(type='edge-edge-crossing',edgeId=a['edgeId'],targetId=b['edgeId'],detail=f'edges "{a["edgeId"]}" and "{b["edgeId"]}" cross'))
    for issue in issues:logging.getLogger(__name__).warning('[SWIMLANE_VALIDATE] %s: %s',issue['type'],issue['detail'])
    return issues
