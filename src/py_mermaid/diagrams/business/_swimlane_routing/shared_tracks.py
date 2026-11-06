"""Shared interior track nudging and collinear sibling rescue, source ports."""
from .geometry import (point,segments,dedupe,overlap_length,strictly_cross,
    collect_node_rect_entries,collect_real_node_bounds,segment_hits_any_rect,
    rect_of_node,classify_three_segment_route,node_pair_geometry,
    segment_conflicts_with_any_edge)


def straighten_siblings(edges,nodes):
    infos,rects=collect_real_node_bounds(nodes)
    label_dims={n['id']:(n.get('width',0),n.get('height',0)) for n in nodes if not n.get('isGroup') and n.get('isEdgeLabel')}
    for edge in edges:
        if edge.get('isLayoutOnly') or not classify_three_segment_route(edge.get('points'),1e-6):continue
        pair=node_pair_geometry(edge,infos,1e-6)
        if not pair or pair['collinearX']==pair['collinearY']:continue
        src,dst=pair['srcInfo'],pair['dstInfo'];cx=pair['collinearX']
        a,b=src['rect'],dst['rect']
        if cx:
            below=dst['cy']>src['cy'];p=point(src['cx'],a['bottom'] if below else a['top']);q=point(dst['cx'],b['top'] if below else b['bottom'])
        else:
            right=dst['cx']>src['cx'];p=point(a['right'] if right else a['left'],src['cy']);q=point(b['left'] if right else b['right'],dst['cy'])
        exclude=(pair['srcId'],pair['dstId'])
        if segment_hits_any_rect(p,q,rects,exclude,1):continue
        target=tuple(sorted(exclude));axis='x' if cx else 'y';half=0
        for other in edges:
            if other is not edge and (other.get('isLayoutOnly') or not other.get('start') or not other.get('end') or tuple(sorted((other['start'],other['end'])))!=target):continue
            dim=label_dims.get(other.get('labelNodeId'))
            if dim:half=max(half,dim[0 if cx else 1]/2)
        shift=max(4,half+3 if half>0 else 0)
        lo,hi=('left','right') if cx else ('top','bottom')
        for delta in (0,shift,-shift):
            sp=dict(p);sq=dict(q);sp[axis]+=delta;sq[axis]+=delta
            if not a[lo]<sp[axis]<a[hi] or not b[lo]<sq[axis]<b[hi]:continue
            if segment_hits_any_rect(sp,sq,rects,exclude,1):continue
            if segment_conflicts_with_any_edge(sp,sq,edges,edge,epsilon=1e-6):continue
            edge['points']=[sp,sq];break


def nudge_shared_interiors(edges,nodes):
    real,labels=collect_node_rect_entries(nodes.values())

    def edge_segments(edge,pts):
        return [dict(s,edge=edge,interior=1<=s['index']<=len(pts)-3) for s in segments(pts)]

    def crowded(a,b):
        if a['horizontal'] and b['horizontal']:
            return overlap_length(a['a']['x'],a['b']['x'],b['a']['x'],b['b']['x'])>=8 and abs(a['a']['y']-b['a']['y'])<7
        if a['vertical'] and b['vertical']:
            return overlap_length(a['a']['y'],a['b']['y'],b['a']['y'],b['b']['y'])>=8 and abs(a['a']['x']-b['a']['x'])<7
        return False

    def safe(edge,candidate):
        ss=edge_segments(edge,candidate)
        if len(ss)!=len(candidate)-1:return False
        endpoints=[i for i in (edge.get('start'),edge.get('end')) if i]
        own=[edge['labelNodeId']] if edge.get('labelNodeId') else []
        for s in ss:
            if segment_hits_any_rect(s['a'],s['b'],real,endpoints,-2) or segment_hits_any_rect(s['a'],s['b'],labels,own,-2):return False
        for other in edges:
            if other is edge or other.get('isLayoutOnly'):continue
            os=edge_segments(other,dedupe(other.get('points') or []))
            for a in ss:
                for b in os:
                    if crowded(a,b) or strictly_cross(a['a'],a['b'],b['a'],b['b']):return False
        return True

    def shifted(s,shift):
        pts=dedupe(s['edge'].get('points') or []);i=s['index']
        if len(pts)<4 or i>=len(pts)-1:return None
        out=[dict(p) for p in pts];axis='y' if s['horizontal'] else 'x'
        out[i][axis]+=shift;out[i+1][axis]+=shift
        return out if len(edge_segments(s['edge'],out))==len(out)-1 else None

    def source_detour(s,shift):
        e=s['edge'];pts=dedupe(e.get('points') or [])
        if len(pts)!=4 or s['index']!=1:return None
        src=nodes.get(e.get('start'));dst=nodes.get(e.get('end'))
        sr=rect_of_node(src) if src else None;dr=rect_of_node(dst) if dst else None
        if not sr or not dr:return None
        sc=point(src.get('x',(sr['left']+sr['right'])/2),src.get('y',(sr['top']+sr['bottom'])/2))
        dc=point(dst.get('x',(dr['left']+dr['right'])/2),dst.get('y',(dr['top']+dr['bottom'])/2));tail=pts[3:]
        if s['vertical']:
            below=dc['y']>=sc['y'];port=sr['bottom'] if below else sr['top'];stub=port+(20 if below else -20)
            if (below and s['b']['y']<=stub+1e-3) or (not below and s['b']['y']>=stub-1e-3):return None
            rail=s['a']['x']+shift
            return dedupe([point(sc['x'],port),point(sc['x'],stub),point(rail,stub),point(rail,s['b']['y']),*tail])
        right=dc['x']>=sc['x'];port=sr['right'] if right else sr['left'];stub=port+(20 if right else -20)
        if (right and s['b']['x']<=stub+1e-3) or (not right and s['b']['x']>=stub-1e-3):return None
        rail=s['a']['y']+shift
        return dedupe([point(port,sc['y']),point(stub,sc['y']),point(stub,rail),point(s['b']['x'],rail),*tail])

    for _ in range(12):
        ss=[s for e in edges if not e.get('isLayoutOnly') for s in edge_segments(e,dedupe(e.get('points') or []))]
        fixed=False
        for i,first in enumerate(ss):
            if fixed:break
            for second in ss[i+1:]:
                if first['edge'] is second['edge'] or not crowded(first,second):continue
                for s in (first,second):
                    if not s['interior']:continue
                    for shift in (-7,7,-14,14,-21,21):
                        direct=shifted(s,shift)
                        if direct and safe(s['edge'],direct):s['edge']['points']=direct;fixed=True;break
                        detour=source_detour(s,shift)
                        if detour and safe(s['edge'],detour):s['edge']['points']=detour;fixed=True;break
                    if fixed:break
                if fixed:break
        if not fixed:return
