"""Swimlane preparation, label-node transform and group writeback helpers."""
import math
from ._swimlane_sugiyama import (remove_cycles,lane_map,layering,proper,order_layers,coordinates,optimize_lane_order)

DEFAULT_LANE='__swimlane_default__'

def prepare(layout):
    nodes=layout['nodes'];direction=layout.get('direction');byid={n['id']:n for n in nodes}
    for n in nodes:
        if n.get('isGroup') and not n.get('parentId'):n['shape']='swimlane';n['direction']=direction
    loose=[n for n in nodes if not n.get('isGroup') and not n.get('parentId')]
    if loose:
        default=byid.get(DEFAULT_LANE)
        if default is None:
            default={'id':DEFAULT_LANE,'label':'','isGroup':True,'shape':'swimlane','padding':20,'look':layout['config'].get('look'),'colorIndex':max((n.get('colorIndex',-1) for n in nodes),default=-1)+1,'direction':direction};nodes.append(default)
        elif default.get('isGroup'):default['shape']='swimlane';default['direction']=direction
        for n in loose:n['parentId']=DEFAULT_LANE

def create_label_nodes(layout):
    byid={n['id']:n for n in layout['nodes']};added=[];virtual=[]
    for e in layout['edges']:
        if not e.get('label') or e.get('isLayoutOnly') or e.get('labelNodeId'):continue
        source=byid.get(e.get('start'));target=byid.get(e.get('end'))
        if source is None or target is None:continue
        ident=f"edge-label-{e['start']}-{e['end']}-{e['id']}";parent=target.get('parentId') if source.get('parentId')!=target.get('parentId') else source.get('parentId')
        # Public provider's measured label dimensions arrive in the edge.
        added.append({'id':ident,'label':e['label'],'edgeStart':e['start'],'edgeEnd':e['end'],'shape':'labelRect','width':e.get('label_width',0),'height':e.get('label_height',0),'isEdgeLabel':True,'isDummy':True,'parentId':parent,'isGroup':False,'labelStyle':e.get('labelStyle',''),'dir':source.get('dir')})
        e['labelNodeId']=ident;e['label']=None;e.pop('text',None)
        virtual.extend(({'id':e['id']+'-to-label','start':e['start'],'end':ident,'type':'normal','isLayoutOnly':True},{'id':e['id']+'-from-label','start':ident,'end':e['end'],'type':'normal','isLayoutOnly':True}))
    layout['nodes'].extend(added);layout['edges'].extend(virtual)

def assign_title_rect(lane):
    x,y,w,h,content=(lane.get(k) for k in ('x','y','width','height','swimlaneContentTop'))
    if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in (x,y,w,h,content)) or w<=0 or h<=0:lane.pop('groupTitleRect',None);return
    top=y-h/2;bottom=top+min(21,max(0,min(content,y+h/2)-top))
    if bottom<=top:lane.pop('groupTitleRect',None);return
    lane['groupTitleRect']={'left':x-w/2,'right':x+w/2,'top':top,'bottom':bottom}

def writeback(layout,graph_nodes,layers,coords,node_gap,layer_gap):
    for rank,layer in enumerate(layers):
        for order,ident in enumerate(layer):
            if ident in graph_nodes:
                n=graph_nodes[ident];n['layer']=rank;n['order']=order;n['x'],n['y']=coords.get(ident,(order*node_gap,rank*layer_gap))
    allnodes=layout['nodes'];bounds={};top=[]
    for group in allnodes:
        if not group.get('isGroup'):continue
        if not group.get('parentId'):top.append(group)
        children=[n for n in allnodes if n.get('parentId')==group['id']];rect=[]
        for child in children:
            cx=child.get('x',coords.get(child['id'],(None,None))[0]);cy=child.get('y',coords.get(child['id'],(None,None))[1])
            if cx is not None and cy is not None:rect.append((cx-child.get('width',0)/2,cy-child.get('height',0)/2,cx+child.get('width',0)/2,cy+child.get('height',0)/2))
        if not rect:
            for key in ('x','y','width','height'):group.setdefault(key,0)
            continue
        minx=min(r[0] for r in rect);miny=min(r[1] for r in rect);maxx=max(r[2] for r in rect);maxy=max(r[3] for r in rect);padding=group.get('padding',20);horizontal=padding if group.get('parentId') else 2*max(padding,20)
        group.update(x=(minx+maxx)/2,y=(miny+maxy)/2,width=max(0,maxx-minx)+horizontal,height=max(0,maxy-miny)+padding);bounds[group['id']]=(minx,miny,maxx,maxy)
    if not top or not bounds:return
    eligible=[n for n in top if n['id'] in bounds]
    if not eligible:return
    miny=min(bounds[n['id']][1] for n in eligible);maxy=max(bounds[n['id']][3] for n in eligible);maxpad=max(n.get('padding',20) for n in top);margin=max(maxpad,36)
    for lane in top:lane['y']=(miny+maxy)/2;lane['height']=max(0,maxy-miny)+2*margin;lane['swimlaneContentTop']=miny
    eligible=sorted(eligible,key=lambda n:n.get('x',0));centers=[];widths=[]
    for lane in eligible:
        minx,_,maxx,_=bounds[lane['id']];centers.append((minx+maxx)/2);widths.append(max(0,maxx-minx)+2*max(lane.get('padding',20),20))
    if len(eligible)==1:eligible[0]['width']=widths[0]
    else:
        u=[0]
        for a,b in zip(centers,centers[1:]):u.append(2*(b-a)-u[-1])
        lower=max([0]+[widths[i]-u[i] for i in range(0,len(u),2)]);upper=min((u[i]-widths[i] for i in range(1,len(u),2)),default=math.inf);x=(lower+upper)/2 if lower<=upper else lower
        for i,lane in enumerate(eligible):lane['width']=max(widths[i],u[i]+(x if i%2==0 else -x))
    for lane in top:assign_title_rect(lane)

def sugiyama(layout):
    cfg=layout['config'];fc=cfg.get('flowchart',{});sc=cfg.get('swimlane',{});direction=layout.get('direction','TB');nodegap=fc.get('nodeSpacing',40);layergap=fc.get('rankSpacing',100)
    nodes={n['id']:n for n in layout['nodes']};rawedges=[];seen=set()
    for e in layout['edges']:
        source=e.get('start');target=e.get('end');key=(e['id'],source,target)
        if source not in nodes or target not in nodes or e.get('labelNodeId') or key in seen:continue
        seen.add(key);rawedges.append({'id':e['id'],'src':source,'dst':target,'ref':e['id'],'original_source':source,'original_target':target,'isLayoutOnly':e.get('isLayoutOnly',False)})
    lanes=lane_map(nodes);sourceorder=list(reversed([n['id'] for n in layout['nodes'] if n.get('isGroup') and not n.get('parentId')]))
    weighted_edges=[{'id':e['id'],'src':e['start'],'dst':e['end']} for e in layout['edges'] if not e.get('isLayoutOnly') and e.get('start') in nodes and e.get('end') in nodes]
    laneorder=optimize_lane_order(nodes,weighted_edges,lanes,sourceorder) if sc.get('automaticLaneOrdering',False) else sourceorder
    acyclic=remove_cycles(nodes,rawedges);rank,layers=layering(nodes,acyclic,lanes,direction,sc.get('ignoreCrossLaneEdges',True),sc.get('optimizeRanksByCrossings',True));expanded,edges,layers=proper(nodes,acyclic,rank,layers);lanes=lane_map(expanded)
    layers=order_layers(layers,edges,lanes,laneorder);coords=coordinates(expanded,edges,layers,lanes,laneorder,nodegap,layergap,direction);writeback(layout,nodes,layers,coords,nodegap,layergap)
    for e in layout['edges']:e.pop('points',None)
    return direction
