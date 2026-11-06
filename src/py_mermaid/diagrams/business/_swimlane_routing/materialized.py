"""Source materialized-render orthogonal route refinements."""
import math
import itertools
from functools import cmp_to_key
from .geometry import (EPS,point,same_point,same_x,same_y,horizontal,vertical,
    dedupe,segments,rect_of_node,collect_node_rect_entries,segment_hits_any_rect,
    same_axis_overlap,strictly_cross,count_bends,build_port_path,
    build_same_side_track_path,overlap_length,port_for_side,simplify,fixed)


def _aligned(a,b):return same_x(a,b) or same_y(a,b)


def _rect_intersect(node,p):
    x,y=node.get('x',0),node.get('y',0);dx,dy=p['x']-x,p['y']-y;w,h=node.get('width',0)/2,node.get('height',0)/2
    if abs(dy)*w>abs(dx)*h:
        if dy<0:h=-h
        return point(x+(h*dx/dy if dy else 0),y+h)
    if dx<0:w=-w
    return point(x+w,y+(w*dy/dx if dx else 0))


def _terminal_lane(edge,start,nodes):
    pts=dedupe(edge.get('points') or [])
    if len(pts)<2:return None
    nid=edge.get('start' if start else 'end');node=nodes.get(nid);r=rect_of_node(node) if node else None
    if not node or not nid or not r:return None
    endpoint,adjacent=(pts[0],pts[1]) if start else (pts[-1],pts[-2]);boundary=_rect_intersect(node,endpoint)
    rail=adjacent if _aligned(adjacent,boundary) else endpoint
    if same_x(boundary,rail):orientation='V';coord=boundary['x'];axis='y'
    elif same_y(boundary,rail):orientation='H';coord=boundary['y'];axis='x'
    else:return None
    return dict(edge=edge,edgeId=str(edge.get('id','')),nodeId=nid,atStart=start,orientation=orientation,coord=coord,min=min(boundary[axis],rail[axis]),max=max(boundary[axis],rail[axis]),boundary=boundary,railEnd=rail,rect=r)


def _same_terminal_face(a,b):
    if a['nodeId']!=b['nodeId'] or a['orientation']!=b['orientation']:return False
    p,r=a['boundary'],a['rect']
    if a['orientation']=='H':return (abs(p['x']-r['left'])<1 or abs(p['x']-r['right'])<1) and same_x(p,b['boundary'],1)
    return (abs(p['y']-r['top'])<1 or abs(p['y']-r['bottom'])<1) and same_y(p,b['boundary'],1)


def _exact_lane_conflict(a,b):
    return a['nodeId']==b['nodeId'] and a['orientation']==b['orientation'] and min(a['max'],b['max'])-max(a['min'],b['min'])>=8 and abs(a['coord']-b['coord'])<.5


def _near_lane_conflict(a,b):
    if a['nodeId']!=b['nodeId'] or a['orientation']!=b['orientation'] or a['orientation']!='H' or a['atStart']==b['atStart']:return False
    shared=max(0,min(a['max'],b['max'])-max(a['min'],b['min']));span=a['rect']['bottom']-a['rect']['top']
    return shared>=8 and span<=shared<=2*span and _same_terminal_face(a,b) and abs(a['coord']-b['coord'])<16


def separate_terminal_lanes(edges,nodes):
    def shifted(lane,shift):
        pts=dedupe(lane['edge'].get('points') or [])
        if len(pts)<2:return None
        b,r=lane['boundary'],lane['rect'];axis='x' if lane['orientation']=='V' else 'y';sb=dict(b);sr=dict(lane['railEnd']);sb[axis]+=shift;sr[axis]+=shift
        if abs(b['y']-r['top'])<1 or abs(b['y']-r['bottom'])<1:
            on_face=same_y(sb,b) and r['left']+1<=sb['x']<=r['right']-1
        elif abs(b['x']-r['left'])<1 or abs(b['x']-r['right'])<1:
            on_face=same_x(sb,b) and r['top']+1<=sb['y']<=r['bottom']-1
        else:on_face=False
        if not on_face:return None
        if lane['atStart']:
            adjacent=same_point(pts[1],lane['railEnd']);rest=pts[2 if adjacent else 1:]
            if rest and not _aligned(rest[0],sr):return None
            return [sb,sr,*rest]
        adjacent=same_point(pts[-2],lane['railEnd']);before=pts[:-2 if adjacent else -1]
        if before and not _aligned(before[-1],sr):return None
        return [*before,sr,sb]
    def straight(lane):
        e=lane['edge'];pts=dedupe(e.get('points') or []);a,b=nodes.get(e.get('start')),nodes.get(e.get('end'))
        if len(pts)!=2 or not a or not b:return False
        dx,dy=abs(a.get('x',0)-b.get('x',0)),abs(a.get('y',0)-b.get('y',0))
        return (same_y(*pts) and dy<1 and dx>1) or (same_x(*pts) and dx<1 and dy>1)
    for _ in range(8):
        lanes=[lane for e in edges if not e.get('isLayoutOnly') for start in (True,False) if (lane:=_terminal_lane(e,start,nodes))]
        fixed=False
        for i,first in enumerate(lanes):
            if fixed:break
            for second in lanes[i+1:]:
                if first['edge'] is second['edge'] or not (_exact_lane_conflict(first,second) or _near_lane_conflict(first,second)):continue
                near=not _exact_lane_conflict(first,second)
                candidates=sorted((first,second),key=lambda lane:(straight(lane),lane['atStart']))
                for lane in candidates:
                    for shift in (-7,7,-14,14,-21,21):
                        candidate=shifted(lane,shift)
                        if not candidate:continue
                        next_lane=_terminal_lane(dict(lane['edge'],points=candidate),lane['atStart'],nodes)
                        if not next_lane or any(o['edge'] is not lane['edge'] and (_exact_lane_conflict(next_lane,o) or (near and _near_lane_conflict(next_lane,o))) for o in lanes):continue
                        lane['edge']['points']=candidate;fixed=True;break
                    if fixed:break
                if fixed:break
        if not fixed:return


def _visible(edges):return [e for e in edges if not e.get('isLayoutOnly')]


def _points(edge,replacements=()):
    for original,points in replacements:
        if edge is original:return dedupe(points)
    return dedupe(edge.get('points') or [])


def _strict_count(edges,replacements=()):
    count=0
    for i,e in enumerate(edges):
        for other in edges[i+1:]:
            for a in segments(_points(e,replacements)):
                for b in segments(_points(other,replacements)):
                    if strictly_cross(a['a'],a['b'],b['a'],b['b']):count+=1
    return count


def lift_hugging_rails(edges,nodes):
    real,labels=collect_node_rect_entries(nodes.values());visible=_visible(edges)
    def safe(edge,candidate,current):
        ss=segments(candidate);endpoint_ids=[i for i in (edge.get('start'),edge.get('end')) if i]
        if len(ss)!=len(candidate)-1:return False
        for s in ss:
            if segment_hits_any_rect(s['a'],s['b'],real,endpoint_ids,-2) or segment_hits_any_rect(s['a'],s['b'],labels,[],-2):return False
        for other in visible:
            if other is edge:continue
            if any(same_axis_overlap(a,b,.5)>=8 for a in ss for b in segments(_points(other))):return False
        return _strict_count(visible,[(edge,candidate)])<=current
    for _ in range(8):
        current=_strict_count(visible);fixed=False
        for edge in visible:
            pts=_points(edge);ss=segments(pts)
            if len(ss)!=3 or ss[0]['horizontal']==ss[1]['horizontal'] or ss[2]['horizontal']==ss[1]['horizontal']:continue
            rail=ss[1];endpoint_ids=(edge.get('start'),edge.get('end'));blockers=[]
            for entry in real:
                if entry['id'] in endpoint_ids:continue
                r=entry['rect']
                if rail['horizontal']:
                    blocked=overlap_length(rail['a']['x'],rail['b']['x'],r['left'],r['right'])>=8 and r['top']-2<=rail['a']['y']<=r['bottom']+2
                else:blocked=overlap_length(rail['a']['y'],rail['b']['y'],r['top'],r['bottom'])>=8 and r['left']-2<=rail['a']['x']<=r['right']+2
                if blocked:blockers.append(entry)
            if not blockers:continue
            low,high=('top','bottom') if rail['horizontal'] else ('left','right');axis='y' if rail['horizontal'] else 'x'
            coords=(min(b['rect'][low] for b in blockers)-20,max(b['rect'][high] for b in blockers)+20)
            for coord in coords:
                candidate=[dict(p) for p in pts];candidate[rail['index']][axis]=coord;candidate[rail['index']+1][axis]=coord;candidate=simplify(dedupe(candidate))
                if len(segments(candidate))!=len(candidate)-1 or not safe(edge,candidate,current):continue
                edge['points']=candidate;fixed=True;break
            if fixed:break
        if not fixed:return


def _valid_title(node):
    r=node.get('groupTitleRect')
    if not r or any(not isinstance(r.get(k),(int,float)) or not math.isfinite(r[k]) for k in ('left','right','top','bottom')):return None
    if r['right']<=r['left'] or r['bottom']<=r['top']:return None
    return dict(r)


def _title_intersects(s,r,horizontal_axis):
    if horizontal_axis:
        return s['horizontal'] and r['top']-EPS<=s['a']['y']<=r['bottom']+EPS and overlap_length(s['a']['x'],s['b']['x'],r['left'],r['right'])>=8
    return s['vertical'] and r['left']-EPS<=s['a']['x']<=r['right']+EPS and overlap_length(s['a']['y'],s['b']['y'],r['top'],r['bottom'])>=8


def lift_top_titles(edges,nodes,direction=None):
    lanes=[]
    for n in nodes.values():
        nd=n.get('direction') if n.get('direction') is not None else direction;nd=nd.upper() if isinstance(nd,str) else ''
        if not n.get('isGroup') or n.get('parentId') or nd in ('LR','RL','BT'):continue
        r=_valid_title(n);y,h=n.get('y'),n.get('height')
        if not r or not isinstance(y,(int,float)) or not isinstance(h,(int,float)) or not math.isfinite(y) or not math.isfinite(h) or h<=0:continue
        if r['right']-r['left']<r['bottom']-r['top']:continue
        lanes.append((n,r))
    delta=0
    for edge in _visible(edges):
        for s in segments(_points(edge)):
            for _,r in lanes:
                if _title_intersects(s,r,True):delta=max(delta,r['bottom']-s['a']['y']+4)
    if delta<=EPS:return
    for n,r in lanes:n.update(y=n['y']-delta/2,height=n['height']+delta,groupTitleRect=dict(r,top=r['top']-delta,bottom=r['bottom']-delta))


def shift_left_titles(edges,nodes,direction=None):
    lanes=[]
    for n in nodes.values():
        nd=n.get('direction') if n.get('direction') is not None else direction;nd=nd.upper() if isinstance(nd,str) else ''
        if not n.get('isGroup') or n.get('parentId') or nd!='LR':continue
        r=_valid_title(n);x,w=n.get('x'),n.get('width')
        if not r or not isinstance(x,(int,float)) or not isinstance(w,(int,float)) or not math.isfinite(x) or not math.isfinite(w) or w<=0:continue
        if r['bottom']-r['top']<r['right']-r['left']:continue
        lanes.append((n,r))
    delta=0
    for edge in _visible(edges):
        for s in segments(_points(edge)):
            for _,r in lanes:
                if _title_intersects(s,r,False):delta=max(delta,r['right']-s['a']['x']+4)
                elif _title_intersects(s,r,True):delta=max(delta,r['right']-min(s['a']['x'],s['b']['x'])+4)
    if delta<=EPS:return
    for n,r in lanes:n.update(x=n['x']-delta/2,width=n['width']+delta,groupTitleRect=dict(r,left=r['left']-delta,right=r['right']-delta))


def _total_bends(edges,replacements=()):return sum(count_bends(_points(e,replacements)) for e in edges)


def _path_length(points):return sum(math.hypot(s['b']['x']-s['a']['x'],s['b']['y']-s['a']['y']) for s in segments(points))


def shortcut_jogs(edges,nodes):
    real,labels=collect_node_rect_entries(nodes.values());visible=_visible(edges)
    def candidates_at(pts,i):
        if i+3>=len(pts):return []
        a,b,c,d=pts[i:i+4]
        hvh=horizontal(a,b) and vertical(b,c) and horizontal(c,d)
        vhv=vertical(a,b) and horizontal(b,c) and vertical(c,d)
        if not hvh and not vhv:return []
        axis='x' if hvh else 'y'
        sign=lambda x:(x>0)-(x<0)
        if sign(b[axis]-a[axis])==sign(d[axis]-c[axis]):return []
        corners=[] if same_x(a,d) or same_y(a,d) else [point(a['x'],d['y']),point(d['x'],a['y'])]
        raw=[[ *pts[:i+1],*pts[i+3:]]] if not corners else [[*pts[:i+1],corner,*pts[i+3:]] for corner in corners]
        seen=set();result=[]
        for candidate in raw:
            candidate=simplify(dedupe(candidate))
            if len(segments(candidate))!=len(candidate)-1 or not any(same_point(p,d) for p in candidate):continue
            key=tuple((fixed(p['x'],3),fixed(p['y'],3)) for p in candidate)
            if key not in seen:seen.add(key);result.append(candidate)
        return result
    def along_border(s,r):
        if s['horizontal']:return (abs(s['a']['y']-r['top'])<1 or abs(s['a']['y']-r['bottom'])<1) and overlap_length(s['a']['x'],s['b']['x'],r['left'],r['right'])>=8
        if s['vertical']:return (abs(s['a']['x']-r['left'])<1 or abs(s['a']['x']-r['right'])<1) and overlap_length(s['a']['y'],s['b']['y'],r['top'],r['bottom'])>=8
        return False
    def safe(edge,candidate,current):
        endpoint_ids=[i for i in (edge.get('start'),edge.get('end')) if i];endpoint_rects=[r for i in endpoint_ids if i in nodes if (r:=rect_of_node(nodes[i]))]
        for s in segments(candidate):
            if segment_hits_any_rect(s['a'],s['b'],real,endpoint_ids,-2) or segment_hits_any_rect(s['a'],s['b'],labels,[],-2) or any(along_border(s,r) for r in endpoint_rects):return False
        return not _path_shared_track(edge,candidate,visible) and _strict_count(visible,[(edge,candidate)])<=current
    for _ in range(8):
        current=_strict_count(visible);best_edge=None;best_path=None;best_cross=current;best_bends=math.inf;best_length=math.inf
        for edge in visible:
            pts=_points(edge);old_bends=count_bends(pts);old_len=_path_length(pts)
            for i in range(len(pts)-3):
                for candidate in candidates_at(pts,i):
                    bends,length=count_bends(candidate),_path_length(candidate)
                    improves=bends<old_bends or (bends==old_bends and length<old_len-EPS)
                    if not improves or not safe(edge,candidate,current):continue
                    cross=_strict_count(visible,[(edge,candidate)])
                    if cross>best_cross or (cross==best_cross and (bends>best_bends or (bends==best_bends and length>=best_length))):continue
                    best_edge,best_path,best_cross,best_bends,best_length=edge,candidate,cross,bends,length
        if best_edge is None or best_path is None:return
        best_edge['points']=best_path


def resolve_crossings(edges,nodes):
    """Single-edge and transactional paired source crossing cleanup."""
    real_nodes=[]
    for n in nodes.values():
        if n.get('isGroup') or n.get('isEdgeLabel'):continue
        r=rect_of_node(n)
        if r:real_nodes.append(dict(id=str(n.get('id','')),cx=n.get('x',0),cy=n.get('y',0),rect=r))
    if not real_nodes:return
    infos={n['id']:n for n in real_nodes};rects=[dict(id=n['id'],rect=n['rect']) for n in real_nodes]
    sides=('top','bottom','left','right');visible=_visible(edges)
    outside={s:(min(n['rect'][s] for n in real_nodes)-20 if s in ('top','left') else max(n['rect'][s] for n in real_nodes)+20) for s in sides}
    def outward(side):return [outside[side]+(-1 if side in ('left','top') else 1)*20*channel for channel in range(3)]
    def push(candidates,pts):
        candidate=simplify(dedupe(pts))
        if len(segments(candidate))==len(candidate)-1:candidates.append(candidate)
    def candidate_key(pts):return tuple((fixed(p['x'],3),fixed(p['y'],3)) for p in pts)
    def for_sides(src,ss,dst,ds):
        candidates=[];base=build_port_path(src,ss,dst,ds,20)
        if base:push(candidates,base)
        if ss==ds:
            axis='x' if ss in ('left','right') else 'y';local=min(src[axis],dst[axis])-20 if ss in ('left','top') else max(src[axis],dst[axis])+20
            for seed in (local,outside[ss]):
                for channel in range(3):push(candidates,build_same_side_track_path(src,ss,dst,seed+(-1 if ss in ('left','top') else 1)*20*channel))
        sh,dh=ss in ('left','right'),ds in ('left','right')
        if sh and not dh:
            for x in outward(ss):
                for y in outward(ds):push(candidates,[src,point(x,src['y']),point(x,y),point(dst['x'],y),dst])
        elif not sh and dh:
            for y in outward(ss):
                for x in outward(ds):push(candidates,[src,point(src['x'],y),point(x,y),point(x,dst['y']),dst])
        elif sh:
            for st in outward(ss):
                for dt in outward(ds):
                    for y in [*outward('top'),*outward('bottom')]:push(candidates,[src,point(st,src['y']),point(st,y),point(dt,y),point(dt,dst['y']),dst])
        else:
            for st in outward(ss):
                for dt in outward(ds):
                    for x in [*outward('left'),*outward('right')]:push(candidates,[src,point(src['x'],st),point(x,st),point(x,dt),point(dst['x'],dt),dst])
        result=[];seen=set()
        for c in candidates:
            c=dedupe(c);key=candidate_key(c)
            if key not in seen and len(c)>=2:seen.add(key);result.append(c)
        return result
    def preserving(edge):
        src_id,dst_id=edge.get('start'),edge.get('end');dst_node=infos.get(dst_id)
        if not src_id or not dst_node:return []
        pts=_points(edge)
        if len(pts)<4:return []
        first,departure=pts[:2];candidates=[]
        xs=[*outward('left'),*outward('right')];ys=[*outward('top'),*outward('bottom')]
        if vertical(first,departure):
            for side in sides:
                dst=port_for_side(dst_node,side);target_ys=outward(side) if side in ('top','bottom') else ys
                for x in xs:
                    push(candidates,[first,departure,point(x,departure['y']),point(x,dst['y']),dst])
                    for y in target_ys:push(candidates,[first,departure,point(x,departure['y']),point(x,y),point(dst['x'],y),dst])
        elif horizontal(first,departure):
            for side in sides:
                dst=port_for_side(dst_node,side);target_xs=outward(side) if side in ('left','right') else xs
                for y in ys:
                    push(candidates,[first,departure,point(departure['x'],y),point(dst['x'],y),dst])
                    for x in target_xs:push(candidates,[first,departure,point(departure['x'],y),point(x,y),point(x,dst['y']),dst])
        return candidates
    def candidates_for(edge):
        src,dst=infos.get(edge.get('start')),infos.get(edge.get('end'))
        if not src or not dst:return []
        candidates=[]
        for ss in sides:
            sp=port_for_side(src,ss)
            for ds in sides:candidates.extend(for_sides(sp,ss,port_for_side(dst,ds),ds))
        candidates.extend(preserving(edge));return candidates
    def crossing_between(a,b):return sum(strictly_cross(x['a'],x['b'],y['a'],y['b']) for x in a for y in b)
    def snapshot():
        pairs=[];edge_set=set();count=0
        for i,e in enumerate(visible):
            for j in range(i+1,len(visible)):
                c=crossing_between(segments(_points(e)),segments(_points(visible[j])))
                if c:count+=c;pairs.append((i,j,c));edge_set.update((i,j))
        return dict(count=count,pairs=pairs,edgeSet=edge_set,edges=sorted(edge_set))
    def length(pts):return sum(abs(b['x']-a['x'])+abs(b['y']-a['y']) for a,b in zip(pts,pts[1:]))
    def paired(current):
        base_segments={i:segments(_points(e)) for i,e in enumerate(visible)}
        base_bends={i:count_bends(_points(e)) for i,e in enumerate(visible)};base_length={i:length(_points(e)) for i,e in enumerate(visible)}
        total_bends,total_length=sum(base_bends.values()),sum(base_length.values());by_edge={};neighbors={}
        for a,b,c in current['pairs']:
            by_edge[a]=by_edge.get(a,0)+c;by_edge[b]=by_edge.get(b,0)+c
            neighbors.setdefault(a,[])
            if b not in neighbors[a]:neighbors[a].append(b)
            neighbors.setdefault(b,[])
            if a not in neighbors[b]:neighbors[b].append(a)
        groups=[];seen=set()
        for start in current['edges']:
            if start in seen:continue
            queue=[start];component=[];seen.add(start)
            while queue:
                index=queue.pop();component.append(index)
                for nxt in neighbors.get(index,[]):
                    if nxt not in seen:seen.add(nxt);queue.append(nxt)
            component.sort()
            if len(component)<=1:continue
            endpoint_ids={key for i in component for key in (visible[i].get('start'),visible[i].get('end')) if key}
            group=list(component)
            for i,e in enumerate(visible):
                if i not in component and any(key in endpoint_ids for key in (e.get('start'),e.get('end')) if key):group.append(i)
            groups.append(sorted(group))
        options={}
        for group in groups:
            for i in group:
                if i in options:continue
                edge=visible[i];seen_paths=set();candidates=[]
                for candidate in candidates_for(edge):
                    candidate=simplify(dedupe(candidate))
                    if _path_node_hit(edge,candidate,rects):continue
                    key=candidate_key(candidate)
                    if key in seen_paths or len(candidate)<2:continue
                    seen_paths.add(key);ss=segments(candidate)
                    affected=sum(crossing_between(ss,base_segments[j]) for j in range(len(visible)) if j!=i)
                    crossings=current['count']-by_edge.get(i,0)+affected
                    if crossings>current['count']:continue
                    candidates.append(dict(path=candidate,segments=ss,crossings=crossings,bends=count_bends(candidate),totalBends=count_bends(candidate),length=length(candidate)))
                candidates.sort(key=lambda c:(c['crossings'],c['bends'],c['length']))
                for c in candidates[:48]:c['sharedTrackConflicts']={j for j in range(len(visible)) if j!=i and any(same_axis_overlap(a,b,.5)>=8 for a in c['segments'] for b in base_segments[j])}
                if candidates:options[i]=candidates[:48]
        best_score=(current['count'],total_bends,total_length);best=None
        for group in groups:
            opts=[i for i in group if i in options]
            for pos,i in enumerate(opts):
                for j in opts[pos+1:]:
                    if i not in current['edgeSet'] and j not in current['edgeSet']:continue
                    for a in options[i]:
                        if a['sharedTrackConflicts']-{j}:continue
                        for b in options[j]:
                            if b['sharedTrackConflicts']-{i} or any(same_axis_overlap(x,y,.5)>=8 for x in a['segments'] for y in b['segments']):continue
                            affected=sum(c for first,second,c in current['pairs'] if first in (i,j) or second in (i,j))
                            replacement=crossing_between(a['segments'],b['segments'])
                            replacement+=sum(crossing_between(a['segments'],base_segments[k])+crossing_between(b['segments'],base_segments[k]) for k in range(len(visible)) if k not in (i,j))
                            cross=current['count']-affected+replacement
                            if cross>=current['count']:continue
                            score=(cross,total_bends-base_bends[i]-base_bends[j]+a['totalBends']+b['totalBends'],total_length-base_length[i]-base_length[j]+a['length']+b['length'])
                            if score<best_score:best_score=score;best=[(visible[i],a['path']),(visible[j],b['path'])]
        return best
    for _ in range(4):
        current=snapshot()
        if current['count']==0:return
        best_edge=None;best_path=None;best_cross=current['count'];best_bends=math.inf
        for i in current['edges']:
            edge=visible[i];old_bends=count_bends(_points(edge))
            for candidate in candidates_for(edge):
                hits=_path_node_hit(edge,candidate,rects);conflict=not hits and _path_shared_track(edge,candidate,visible)
                cross=_strict_count(visible,[(edge,candidate)]);bends=count_bends(candidate)
                if hits or conflict:continue
                if not (cross<current['count'] or (cross==current['count'] and bends<old_bends)):continue
                if cross>best_cross or (cross==best_cross and bends>=best_bends):continue
                best_edge,best_path,best_cross,best_bends=edge,candidate,cross,bends
        if best_edge is not None and best_path is not None:best_edge['points']=best_path;continue
        replacements=paired(current)
        if not replacements:return
        for edge,pts in replacements:edge['points']=pts


def _path_node_hit(edge,path,rects):
    endpoints=[i for i in (edge.get('start'),edge.get('end')) if i]
    return any(segment_hits_any_rect(s['a'],s['b'],rects,endpoints,-2) for s in segments(path))


def _path_shared_track(edge,path,edges,replacements=()):
    return any(same_axis_overlap(a,b,.5)>=8 for other in edges if other is not edge for a in segments(path) for b in segments(_points(other,replacements)))


def swap_destination_tails(edges,nodes):
    real,_=collect_node_rect_entries(nodes.values());visible=_visible(edges)
    def tail(edge):
        pts=_points(edge)
        if len(pts)<4 or not (horizontal(pts[-2],pts[-1]) or vertical(pts[-2],pts[-1])):return None
        return pts[-2],pts[-1]
    def with_tail(edge,t):
        pts=_points(edge)
        if len(pts)<3:return None
        start,turn=pts[:2];tail_start,terminal=t
        if horizontal(start,turn):connector=point(turn['x'],tail_start['y'])
        elif vertical(start,turn):connector=point(tail_start['x'],turn['y'])
        else:return None
        candidate=simplify(dedupe([start,turn,connector,tail_start,terminal]))
        return candidate if len(segments(candidate))==len(candidate)-1 else None
    for _ in range(4):
        current=_strict_count(visible)
        if current==0:return
        best=None;best_cross=current;best_bends=_total_bends(visible);groups={}
        for edge in visible:
            dst=edge.get('end')
            if dst and dst in nodes and len(_points(edge))>=4:groups.setdefault(dst,[]).append(edge)
        for group in groups.values():
            for i,a in enumerate(group):
                for b in group[i+1:]:
                    ta,tb=tail(a),tail(b)
                    if not ta or not tb:continue
                    ca,cb=with_tail(a,tb),with_tail(b,ta)
                    if not ca or not cb:continue
                    replacements=[(a,ca),(b,cb)]
                    if any(_path_node_hit(e,p,real) or _path_shared_track(e,p,visible,replacements) for e,p in replacements):continue
                    cross=_strict_count(visible,replacements);bends=_total_bends(visible,replacements)
                    if cross>=current or cross>best_cross or (cross==best_cross and bends>=best_bends):continue
                    best,best_cross,best_bends=replacements,cross,bends
        if not best:return
        for edge,pts in best:edge['points']=pts


def reassign_external_channels(edges,nodes):
    real,labels=collect_node_rect_entries(nodes.values());visible=_visible(edges)
    def rails():
        result=[]
        for edge in visible:
            pts=_points(edge);src,dst=nodes.get(edge.get('start')),nodes.get(edge.get('end'));sr,dr=rect_of_node(src) if src else None,rect_of_node(dst) if dst else None
            if not sr or not dr:continue
            for s in segments(pts):
                if s['index']<=0 or s['index']+1>=len(pts)-1:continue
                if s['vertical']:
                    coord=s['a']['x'];side='left' if coord<min(sr['left'],dr['left'])-EPS else 'right' if coord>max(sr['right'],dr['right'])+EPS else None;axis='vertical';along='y'
                else:
                    coord=s['a']['y'];side='top' if coord<min(sr['top'],dr['top'])-EPS else 'bottom' if coord>max(sr['bottom'],dr['bottom'])+EPS else None;axis='horizontal';along='x'
                if side:result.append(dict(edge=edge,points=pts,segmentIndex=s['index'],axis=axis,side=side,coord=coord,min=min(s['a'][along],s['b'][along]),max=max(s['a'][along],s['b'][along])))
        return result
    def interact(a,b):return a['edge'] is not b['edge'] and a['axis']==b['axis'] and a['side']==b['side'] and overlap_length(a['min'],a['max'],b['min'],b['max'])>=8
    def components(rails):
        seen=set();result=[]
        for i,rail in enumerate(rails):
            if i in seen:continue
            queue=[i];component=[];seen.add(i)
            while queue:
                current=queue.pop();component.append(rails[current])
                for j,nxt in enumerate(rails):
                    if j not in seen and interact(rails[current],nxt):seen.add(j);queue.append(j)
            if len(component)>1:result.append(component)
        return result
    def assignments(component):
        current=[r['coord'] for r in component];coords=[]
        for r in component:
            if not any(abs(c-r['coord'])<EPS for c in coords):coords.append(r['coord'])
        while len(coords)<len(component):
            gap=12*(len(component)-len(coords));coords.append(min(coords)-gap if component[0]['side'] in ('left','top') else max(coords)+gap)
        if len(component)<=6:
            for values in itertools.permutations(coords,len(component)):
                if any(abs(c-current[i])>=EPS for i,c in enumerate(values)):yield values
        else:
            for i in range(len(current)):
                for j in range(i+1,len(current)):
                    values=list(current);values[i],values[j]=values[j],values[i];yield values
    def replacements_for(component,assignment):
        draft=[]
        for rail,coord in zip(component,assignment):
            edge=rail['edge'];entry=next((entry for entry in draft if entry[0] is edge),None)
            if entry is None:entry=(edge,[dict(p) for p in rail['points']]);draft.append(entry)
            axis='x' if rail['axis']=='vertical' else 'y';idx=rail['segmentIndex'];entry[1][idx][axis]=coord;entry[1][idx+1][axis]=coord
        result=[]
        for edge,pts in draft:
            pts=simplify(dedupe(pts))
            if len(segments(pts))!=len(pts)-1:return None
            result.append((edge,pts))
        return result
    def safe(replacements):
        for edge,pts in replacements:
            if _path_node_hit(edge,pts,real):return False
            if any(segment_hits_any_rect(s['a'],s['b'],labels,[],-2) for s in segments(pts)):return False
        for i,first in enumerate(visible):
            changed=any(e is first for e,_ in replacements)
            for second in visible[i+1:]:
                if not changed and not any(e is second for e,_ in replacements):continue
                if any(same_axis_overlap(a,b,.5)>=8 for a in segments(_points(first,replacements)) for b in segments(_points(second,replacements))):return False
        return True
    for _ in range(4):
        current=_strict_count(visible)
        if current==0:return
        best=None;best_cross=current;best_bends=_total_bends(visible);best_displacement=math.inf
        for component in components(rails()):
            for assignment in assignments(component):
                replacements=replacements_for(component,assignment)
                if not replacements or not safe(replacements):continue
                cross=_strict_count(visible,replacements)
                if cross>=current:continue
                bends=_total_bends(visible,replacements);displacement=sum(abs(coord-r['coord']) for r,coord in zip(component,assignment))
                if cross>best_cross or (cross==best_cross and (bends>best_bends or (bends==best_bends and displacement>=best_displacement))):continue
                best,best_cross,best_bends,best_displacement=replacements,cross,bends,displacement
        if not best:return
        for edge,pts in best:edge['points']=pts


def collapse_doglegs(edges,nodes):
    real,labels=collect_node_rect_entries(nodes.values())
    def safe(edge,candidate):
        ss=segments(candidate)
        if len(ss)!=len(candidate)-1:return False
        endpoint_ids=[i for i in (edge.get('start'),edge.get('end')) if i]
        for s in ss:
            if segment_hits_any_rect(s['a'],s['b'],real,endpoint_ids,-2) or segment_hits_any_rect(s['a'],s['b'],labels,[],-2):return False
        for other in edges:
            if other is edge or other.get('isLayoutOnly'):continue
            for a in ss:
                for b in segments(dedupe(other.get('points') or [])):
                    if same_axis_overlap(a,b,.5)>=8 or strictly_cross(a['a'],a['b'],b['a'],b['b']):return False
        return True
    def without(pts,i):
        if i+4>=len(pts):return None
        a,b,c,d,e=pts[i:i+5]
        tv=horizontal(a,b) and vertical(b,c) and horizontal(c,d) and vertical(d,e) and same_x(a,d) and same_x(a,e) and same_x(b,c) and (b['x']-a['x'])*(d['x']-c['x'])<0
        th=vertical(a,b) and horizontal(b,c) and vertical(c,d) and horizontal(d,e) and same_y(a,d) and same_y(a,e) and same_y(b,c) and (b['y']-a['y'])*(d['y']-c['y'])<0
        if tv or th:return dedupe([*pts[:i+1],e,*pts[i+5:]])
        if i+5>=len(pts):return None
        f=pts[i+5]
        v=vertical(a,b) and horizontal(b,c) and vertical(c,d) and horizontal(d,e) and vertical(e,f) and same_x(a,e) and same_x(a,f) and same_x(c,d) and (c['x']-b['x'])*(e['x']-d['x'])<0
        h=horizontal(a,b) and vertical(b,c) and horizontal(c,d) and vertical(d,e) and horizontal(e,f) and same_y(a,e) and same_y(a,f) and same_y(c,d) and (c['y']-b['y'])*(e['y']-d['y'])<0
        return dedupe([*pts[:i+1],f,*pts[i+6:]]) if v or h else None
    for _ in range(8):
        fixed=False
        for edge in edges:
            if edge.get('isLayoutOnly'):continue
            pts=dedupe(edge.get('points') or [])
            for i in range(len(pts)-4):
                candidate=without(pts,i)
                if candidate and safe(edge,candidate):edge['points']=candidate;fixed=True;break
            if fixed:break
        if not fixed:return
