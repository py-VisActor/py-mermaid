"""ELK post-layout paint geometry, preserving all raw engine sections."""
from __future__ import annotations
from dataclasses import replace
from py_mermaid.model.flowchart import Box, Point
from .paths import (between, corner, dedupe, distance, edge_markers, intersect_segments, line_hop_paths)

def _axis(a,b):
    dx,dy=abs(b.x-a.x),abs(b.y-a.y)
    return "h" if dx>.01 and dy<=.01 else "v" if dy>.01 and dx<=.01 else None

def _front(points):
    if len(points)<5:return points,[]
    p0,p1,p2,p3=points[:4];axis=_axis(p0,p1)
    if not axis or _axis(p2,p3)!=axis or _axis(p1,p2)!=("v" if axis=="h" else "h"):return points,[]
    jog=abs(p2.y-p1.y) if axis=="h" else abs(p2.x-p1.x)
    if distance(p0,p1)>30 or jog<.01 or jog>16:return points,[]
    if ((p1.x-p0.x)*(p3.x-p2.x) if axis=="h" else (p1.y-p0.y)*(p3.y-p2.y))<=0:return points,[]
    last=3
    while last+1<len(points) and _axis(points[last],points[last+1])==axis:last+=1
    if last==len(points)-1:return points,[]
    moved=list(points)
    for i in range(2,last+1):moved[i]=Point(points[i].x,p0.y) if axis=="h" else Point(p0.x,points[i].y)
    run=(points[2],points[last],moved[2],moved[last]);del moved[1:3]
    return tuple(moved),[run]

def _project(center,runs):
    best=None
    for a,b,c,d in runs:
        dx,dy=b.x-a.x,b.y-a.y;length=dx*dx+dy*dy
        t=max(0,min(1,((center.x-a.x)*dx+(center.y-a.y)*dy)/length)) if length else 0
        original=between(a,b,t);squared=(original.x-center.x)**2+(original.y-center.y)**2
        if best is None or squared<best[0]:best=(squared,between(c,d,t))
    return best[1] if best else center

def _crossings(a,b):
    def strict(p,q,r,s):
        def side(o,a,b):return (a.x-o.x)*(b.y-o.y)-(a.y-o.y)*(b.x-o.x)
        first,second=side(r,s,p),side(r,s,q)
        third,fourth=side(p,q,r),side(p,q,s)
        return first*second<0 and third*fourth<0
    return sum(strict(p,q,r,s) for p,q in zip(a,a[1:]) for r,s in zip(b,b[1:]))

def _hits(route,box):
    if box is None:return False
    for a,b in zip(route,route[1:]):
        t0,t1=0.,1.;dx,dy=b.x-a.x,b.y-a.y;valid=True
        for p,q in ((-dx,a.x-box.x),(dx,box.x+box.width-a.x),(-dy,a.y-box.y),(dy,box.y+box.height-a.y)):
            if p==0:
                if q<0:valid=False;break
            elif p<0:t0=max(t0,q/p)
            else:t1=min(t1,q/p)
        if valid and t0<t1:return True
    return False

def _border(point,box,tolerance=1):
    return ((abs(point.x-box.x)<=tolerance or abs(point.x-box.x-box.width)<=tolerance) and box.y-tolerance<=point.y<=box.y+box.height+tolerance) or ((abs(point.y-box.y)<=tolerance or abs(point.y-box.y-box.height)<=tolerance) and box.x-tolerance<=point.x<=box.x+box.width+tolerance)

def _short_markers(points,source,boxes):
    points=list(points);offsets={"none":0,"point":4,"circle":12.5,"cross":12.5}
    for start,kind,identifier in ((False,source.marker_end,source.target),(True,source.marker_start,source.source)):
        offset=offsets[kind]
        if offset<=0 or len(points)<3:continue
        end,entry=(0,1) if start else (-1,-2)
        if distance(points[end],points[entry])<max(8,offset*2) and _border(points[entry],boxes[identifier]):del points[entry]
    return dedupe(points)

def finish_edges(diagram,layout,measured):
    """Compute source rounded/linear paths, safeguarded terminal jogs and hops.

    This stage never re-runs ELK and never writes to raw sections or model input.
    """
    from py_mermaid.layout.elk.options import settings
    from py_mermaid.geometry.path_geometry import path_bounds
    config=settings(diagram.config);boxes={n.id:n.paint_box or n.box for n in (*layout.nodes,*layout.groups)}
    routes=[]
    for source,route in zip(diagram.edges,layout.edges):
        points=route.paint_points
        if not points and route.sections:
            first=route.sections[0];points=(first.start,*first.bends,first.end)
        points=_short_markers(dedupe(points),source,boxes)
        routes.append(points)
    labels=list(layout.edge_labels);label_index={label.id:i for i,label in enumerate(labels)}
    label_boxes={label.id:label.box for label in labels}
    if config["straightenEdges"]:
        for index,route in enumerate(routes):
            candidate,front=_front(route);candidate,back=_front(tuple(reversed(candidate)));candidate=tuple(reversed(candidate));runs=front+back
            if not runs:continue
            identifier=layout.edges[index].id;box=label_boxes.get(identifier);moved=box
            if box is not None:
                center=_project(Point(box.x+box.width/2,box.y+box.height/2),runs)
                moved=replace(box,x=center.x-box.width/2,y=center.y-box.height/2)
            before=after=covered_before=covered_after=0
            for other,path in enumerate(routes):
                if other==index:continue
                before+=_crossings(route,path);after+=_crossings(candidate,path)
                other_box=label_boxes.get(layout.edges[other].id)
                covered_before+=int(_hits(path,box))+int(_hits(route,other_box))
                covered_after+=int(_hits(path,moved))+int(_hits(candidate,other_box))
            if after>before or covered_after>covered_before:continue
            routes[index]=candidate
            if moved is not None:
                label_boxes[identifier]=moved;i=label_index[identifier];labels[i]=replace(labels[i],box=moved)
    marker_kinds=[(edge.marker_start,edge.marker_end) if edge.stroke!="invisible" else ("none","none") for edge in diagram.edges]
    paths=line_hop_paths(tuple((points,edge.effective_curve) for points,edge in zip(routes,layout.edges)),marker_kinds,config["lineHops"])
    output=[]
    for source,route,points,path,kinds in zip(diagram.edges,layout.edges,routes,paths,marker_kinds):
        if source.stroke=="invisible":path="";bounds=None
        else:
            boxes_for_path=[path_bounds(path)] if path else []
            boxes_for_path.extend(marker.bounds for marker in edge_markers(points,*kinds))
            if boxes_for_path:
                left=min(b.x for b in boxes_for_path);top=min(b.y for b in boxes_for_path)
                bounds=Box(left,top,max(b.x+b.width for b in boxes_for_path)-left,max(b.y+b.height for b in boxes_for_path)-top)
            else:bounds=None
        output.append(replace(route,paint_points=tuple(points),path=path,paint_bounds=bounds))
    return replace(layout,edges=tuple(output),edge_labels=tuple(labels))
