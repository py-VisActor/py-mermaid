"""The flat-forest CoSE-Bilkent 4.1.0 / cose-base 1.0.3 execution path.

Mindmap's adapter supplies an undirected flat tree: compound tiling, graph
coarsening and pruned cyclic-graph regrowth are not reachable for that input.
The radial initialization, rectangle-clipped springs, FR-grid repulsion,
cooling/convergence and movement below follow the pinned source path.
"""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass
class Node:
    id:str
    width:float
    height:float
    x:float=0.
    y:float=0.


def _clip(a,b):
    dx=b.x-a.x;dy=b.y-a.y
    def endpoint(n,dx,dy):
        factor=min(n.width/(2*abs(dx)) if dx else math.inf,n.height/(2*abs(dy)) if dy else math.inf)
        return (n.x+dx*factor,n.y+dy*factor) if math.isfinite(factor) else (n.x,n.y)
    return endpoint(a,dx,dy),endpoint(b,-dx,-dy)


def _overlap(a,b):return abs(a.x-b.x)<=(a.width+b.width)/2 and abs(a.y-b.y)<=(a.height+b.height)/2


def _separation(a,b,buffer=25.):
    ax=a.x-a.width/2;ay=a.y-a.height/2;bx=b.x-b.width/2;by=b.y-b.height/2
    ox=min(ax+a.width,bx+b.width)-max(ax,bx);oy=min(ay+a.height,by+b.height)-max(ay,by)
    if ax<=bx and ax+a.width>=bx+b.width:ox+=min(bx-ax,ax+a.width-bx-b.width)
    elif bx<=ax and bx+b.width>=ax+a.width:ox+=min(ax-bx,bx+b.width-ax-a.width)
    if ay<=by and ay+a.height>=by+b.height:oy+=min(by-ay,ay+a.height-by-b.height)
    elif by<=ay and by+b.height>=ay+a.height:oy+=min(ay-by,by+b.height-ay-a.height)
    dx=b.x-a.x;dy=b.y-a.y;slope=abs(dy/dx) if dx else math.inf
    if dx==0 and dy==0:slope=1.
    my=slope*ox;mx=oy/slope if slope else math.inf
    if ox<mx:mx=ox
    else:my=oy
    return ((mx/2+buffer)*(1 if a.x<b.x else -1),(my/2+buffer)*(1 if a.y<b.y else -1))


def _source_center(component):
    # Preserve this release's Layout.findCenterOfTree iteration semantics:
    # it mutates its working list while iterating that same list.
    values=list(component)
    while len(values)>2:
        i=0
        while i<len(values):values.pop(i);i+=1
    return values[0]


def _radial(nodes,adjacency,component):
    center=_source_center(component);separation=max(50.,max(math.hypot(nodes[id].width,nodes[id].height) for id in component))
    def branch(id,parent,start,end,distance):
        half=(end-start+1)/2
        if half<0:half+=180
        angle=math.radians((half+start)%360);node=nodes[id];node.x=distance*math.cos(angle);node.y=distance*math.sin(angle)
        neighbors=adjacency[id];count=len(neighbors)-(parent is not None)
        if not count:return
        first=(neighbors.index(parent)+1)%len(neighbors) if parent is not None else 0;ordered=[neighbors[(first+i)%len(neighbors)] for i in range(len(neighbors)) if neighbors[(first+i)%len(neighbors)]!=parent];step=abs(end-start)/count
        for i,child in enumerate(ordered):
            child_start=(start+i*step)%360;branch(child,id,child_start,(child_start+step)%360,distance+separation)
    branch(center,None,0.,359.,0.)


def _surrounding(nodes,range_=100.):
    ids=list(nodes);left=min(n.x-n.width/2 for n in nodes.values());top=min(n.y-n.height/2 for n in nodes.values());grid={};cells={}
    for id,node in nodes.items():
        x0=math.floor((node.x-node.width/2-left)/range_);x1=math.floor((node.x+node.width/2-left)/range_);y0=math.floor((node.y-node.height/2-top)/range_);y1=math.floor((node.y+node.height/2-top)/range_);cells[id]=(x0,x1,y0,y1)
        for x in range(x0,x1+1):
            for y in range(y0,y1+1):grid.setdefault((x,y),[]).append(id)
    pairs=[];processed=set()
    for id in ids:
        a=nodes[id];x0,x1,y0,y1=cells[id];seen=set()
        for x in range(x0-1,x1+2):
            for y in range(y0-1,y1+2):
                for other in grid.get((x,y),()):
                    if other==id or other in processed or other in seen:continue
                    b=nodes[other]
                    if abs(a.x-b.x)-(a.width+b.width)/2<=range_ and abs(a.y-b.y)-(a.height+b.height)/2<=range_:seen.add(other);pairs.append((id,other))
        processed.add(id)
    return pairs


async def layout(nodes,edges,*,direction='TB',parents=(),options=None,node_spacing=50,rank_spacing=50,config=None,algorithm=None):
    from ...model.flowchart import Box,Point,MermaidError
    from ...runtime.graph import GraphLayout,FrozenLookup
    if not config or config.get('_diagramConfigKey')!='mindmap':raise MermaidError('Root node is required for the source CoSE-Bilkent mindmap adapter',code='INVALID_LAYOUT_DATA')
    inputs=tuple(nodes);edges=tuple(edges)
    if parents:raise MermaidError('The source mindmap CoSE adapter requires a flat root tree',code='INVALID_LAYOUT_DATA')
    values={n['id']:Node(n['id'],float(n['width']),float(n['height'])) for n in inputs}
    if len(values)!=len(inputs):raise MermaidError('Duplicate CoSE node',code='DUPLICATE_ID')
    if not values:return GraphLayout(FrozenLookup(()),FrozenLookup(()),FrozenLookup(()),FrozenLookup(()),0,0,'native-cose-bilkent','4.1.0/cose-base-1.0.3')
    adjacency={id:[] for id in values}
    for edge in edges:
        a,b=edge['source'],edge['target']
        if a not in values or b not in values or a==b or b in adjacency[a]:raise MermaidError('Invalid mindmap tree edge',code='INVALID_LAYOUT_DATA')
        adjacency[a].append(b);adjacency[b].append(a)
    components=[];seen=set()
    for id in values:
        if id in seen:continue
        todo=[id];component=[]
        while todo:
            current=todo.pop(0)
            if current in seen:continue
            seen.add(current);component.append(current);todo.extend(x for x in adjacency[current] if x not in seen)
        if sum(len(adjacency[x]) for x in component)!=2*(len(component)-1):raise MermaidError('CoSE mindmap input must be a forest',code='INVALID_LAYOUT_DATA')
        components.append(component)
    # The actual mindmap input has one tree. Retain the dependency's forest
    # initial packing too, without inventing a graph-layout replacement.
    columns=math.ceil(math.sqrt(len(components)));x=0.;y=0.;row_height=0.
    for i,component in enumerate(components):
        _radial(values,adjacency,component)
        if i%columns==0:x=0.;y+=row_height+(60 if i else 0);row_height=0.
        left=min(values[id].x-values[id].width/2 for id in component);top=min(values[id].y-values[id].height/2 for id in component);right=max(values[id].x+values[id].width/2 for id in component);bottom=max(values[id].y+values[id].height/2 for id in component)
        for id in component:values[id].x+=x-left;values[id].y+=y-top
        x+=right-left+60;row_height=max(row_height,bottom-top)
    count=len(values);iterations=max(2500,count*5);initial=max(.33,1-(count-1000)/4000*.67) if count>1000 else 1.;cooling=initial;max_cycle=iterations/100;final_temperature=100/iterations;cycle=0;old=0.;total=0.;surrounding=[]
    for iteration in range(1,iterations+1):
        if iteration==iterations:break
        if iteration%100==0:
            if total<1.5*count or iteration>iterations/3 and abs(total-old)<2:break
            old=total;cycle+=1;exponent=math.log(100*(initial-final_temperature))/math.log(max_cycle);cooling=max(initial-cycle**exponent/100,final_temperature)
        if iteration%10==1:surrounding=_surrounding(values)
        forces={id:[0.,0.] for id in values}
        for edge in edges:
            a=values[edge['source']];b=values[edge['target']]
            if _overlap(a,b):continue
            (ax,ay),(bx,by)=_clip(a,b);dx=bx-ax;dy=by-ay;length=math.hypot(dx,dy)
            if not length:continue
            force=.45*(length-50);fx=force*dx/length;fy=force*dy/length;forces[a.id][0]+=fx;forces[a.id][1]+=fy;forces[b.id][0]-=fx;forces[b.id][1]-=fy
        for a_id,b_id in surrounding:
            a=values[a_id];b=values[b_id]
            if _overlap(a,b):fx,fy=_separation(a,b)
            else:
                (ax,ay),(bx,by)=_clip(a,b);dx=bx-ax;dy=by-ay
                if abs(dx)<5:dx=5*(1 if dx>=0 else -1)
                if abs(dy)<5:dy=5*(1 if dy>=0 else -1)
                squared=dx*dx+dy*dy;distance=math.sqrt(squared);force=4500/squared;fx=force*dx/distance;fy=force*dy/distance
            forces[a_id][0]-=fx;forces[a_id][1]-=fy;forces[b_id][0]+=fx;forces[b_id][1]+=fy
        # Connected owner graphs do not enter CoSE's gravity list.
        if len(components)>1:
            left=min(n.x-n.width/2 for n in values.values());right=max(n.x+n.width/2 for n in values.values());top=min(n.y-n.height/2 for n in values.values());bottom=max(n.y+n.height/2 for n in values.values());cx=(left+right)/2;cy=(top+bottom)/2;estimated=sum((n.width+n.height)/2 for n in values.values())/math.sqrt(count)*3.8
            for id,n in values.items():
                if abs(n.x-cx)+n.width/2>estimated or abs(n.y-cy)+n.height/2>estimated:forces[id][0]-=.25*(n.x-cx);forces[id][1]-=.25*(n.y-cy)
        total=0.
        for id,n in values.items():
            fx,fy=forces[id];dx=max(-cooling*300,min(cooling*300,cooling*fx));dy=max(-cooling*300,min(cooling*300,cooling*fy));n.x+=dx;n.y+=dy;total+=abs(dx)+abs(dy)
    left=min(n.x-n.width/2 for n in values.values());top=min(n.y-n.height/2 for n in values.values());boxes=tuple((id,Box(n.x-n.width/2-left,n.y-n.height/2-top,n.width,n.height)) for id,n in values.items());routes=[]
    for edge in edges:
        a,b=_clip(values[edge['source']],values[edge['target']]);routes.append((edge['id'],(Point(a[0]-left,a[1]-top),Point(b[0]-left,b[1]-top))))
    return GraphLayout(FrozenLookup(boxes),FrozenLookup(tuple(routes)),FrozenLookup(()),FrozenLookup(()),max(b.x+b.width for _,b in boxes),max(b.y+b.height for _,b in boxes),'native-cose-bilkent','4.1.0/cose-base-1.0.3')
