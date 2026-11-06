"""Flowchart grammar with the source swimlane Sugiyama/router pipeline."""
from dataclasses import replace
import math
from ...runtime.common import make_diagram,config_dict,error,immutable_value
from ...model.flowchart import (Box,Point,FlowGroup,PlacedNode,PlacedGroup,PlacedEdgeLabel,EdgeSection,RoutedEdge,FlowLayout)
from ...runtime.graph import GraphLayout,FrozenLookup
from ...geometry.edges.paths import line_hop_paths
from ...geometry.path_geometry import path_bounds
from ...geometry.flowchart import geometry_bounds
from ...rendering.styles.flowchart import resolve_style
from ..flowchart.parser import _Parser
from ._flow_config import flow_config
from ._swimlane_prepare import prepare,create_label_nodes,sugiyama,DEFAULT_LANE

def parse(document,config):
    resolved=flow_config(config,measurement_only=True)
    if len(document.cleaned.encode('utf-16-le'))//2>resolved.max_text_size:raise error(document,0,'Source exceeds maxTextSize','MAX_TEXT_SIZE_EXCEEDED')
    graph=_Parser(document.cleaned,resolved,document).parse()
    return make_diagram('swimlane',document,config,graph)

def _run(data):
    from ._swimlane_routing import route_and_postprocess
    prepare(data);create_label_nodes(data);direction=sugiyama(data)
    route_and_postprocess(data,direction)
    for e in data['edges']:
        if not e.get('curve') or e['curve']=='basis':e['curve']='rounded'
    return data

def _box(n):return Box(n['x']-n.get('width',0)/2,n['y']-n.get('height',0)/2,n.get('width',0),n.get('height',0))

async def layout_provider(nodes,edges,*,direction='TB',parents=(),options=None,node_spacing=40,rank_spacing=100,config=None,algorithm=None):
    """Public registry hook; pure values only, no engine fallback."""
    cfg={**(config or {})};cfg['flowchart']={**cfg.get('flowchart',{}),'nodeSpacing':node_spacing,'rankSpacing':rank_spacing}
    input_nodes=[{**n,'parentId':n.get('parent'),'isGroup':False} for n in nodes]
    input_groups=[{**g,'parentId':g.get('parent'),'label':g.get('label',g.get('title','')),'isGroup':True,'width':g.get('width',g.get('title_width',0)),'height':g.get('height',g.get('title_height',0)),'padding':g.get('padding',20)} for g in parents]
    input_edges=[{**e,'start':e['source'],'end':e['target']} for e in edges]
    data=_run({'nodes':list(reversed(input_groups))+input_nodes,'edges':input_edges,'config':cfg,'direction':'TB' if direction=='TD' else direction})
    byid={n['id']:n for n in data['nodes']};actualnodes=tuple((n['id'],_box(byid[n['id']])) for n in nodes);actualgroups=tuple((n['id'],_box(byid[n['id']])) for n in parents);routes=[];labels=[]
    for e in data['edges']:
        if e.get('isLayoutOnly'):continue
        routes.append((e['id'],tuple(Point(v['x'],v['y']) for v in e.get('points',()))))
        if e.get('labelNodeId'):labels.append((e['id'],_box(byid[e['labelNodeId']])))
    group_data=tuple(immutable_value(n) for n in data['nodes'] if n.get('isGroup'))
    boxes=[_box(n) for n in data['nodes']];width=max((b.x+b.width for b in boxes),default=0);height=max((b.y+b.height for b in boxes),default=0)
    return GraphLayout(FrozenLookup(actualnodes),FrozenLookup(tuple(routes)),FrozenLookup(actualgroups),FrozenLookup(tuple(labels)),max(0,width),max(0,height),engine='mermaid-swimlane',version='12.2.0',group_data=group_data)

def _with_default_lane(graph):
    loose=tuple(n.id for n in graph.nodes if not n.parent_id)
    if not loose:return graph
    if any(g.id==DEFAULT_LANE for g in graph.groups):return graph
    if any(n.id==DEFAULT_LANE for n in graph.nodes):raise error(graph.source_document,0,'Reserved default lane identity collides with a content node','INVALID_GROUP_HIERARCHY')
    span=graph.nodes[0].span;slot=max((g.color_index for g in graph.groups),default=-1)+1
    group=FlowGroup(DEFAULT_LANE,'',span,members=loose,color_index=slot)
    return replace(graph,nodes=tuple(replace(n,parent_id=DEFAULT_LANE) if n.id in loose else n for n in graph.nodes),groups=(*graph.groups,group))

def _source_data(graph,measured,annotations,config):
    bymeasure={n.id:n for n in measured};groupmeasure={n.id:n for n in annotations.groups};edge_labels={n.id:n for n in annotations.edge_labels}
    nodes=[]
    for g in reversed(graph.groups):
        title=groupmeasure[g.id]
        nodes.append({'id':g.id,'label':g.label,'parentId':g.parent_id,'isGroup':True,'shape':'swimlane' if not g.parent_id else 'rect','padding':20 if g.id==DEFAULT_LANE else graph.config.group_padding,'width':title.label_width,'height':title.label_height,'colorIndex':g.color_index,'direction':graph.direction,'dir':g.direction})
    for n in graph.nodes:
        m=bymeasure[n.id];nodes.append({'id':n.id,'label':n.label,'parentId':n.parent_id,'isGroup':False,'shape':n.shape,'width':m.width,'height':m.height,'dir':graph.direction})
    edges=[]
    for e in graph.edges:
        label=edge_labels.get(e.id);edges.append({'id':e.id,'start':e.source,'end':e.target,'label':e.label,'label_width':label.width if label else 0,'label_height':label.height if label else 0,'curve':e.curve,'arrowTypeStart':e.marker_start,'arrowTypeEnd':e.marker_end})
    return {'nodes':nodes,'edges':edges,'config':config,'direction':'TB' if graph.direction=='TD' else graph.direction}

def _layout(graph,data,annotations,measured):
    from ._swimlane_intersect import paint_points
    bymeasure={n.id:n for n in measured};nodebyid={n.id:n for n in graph.nodes}
    byid={n['id']:n for n in data['nodes']};labels={l.id:l for l in annotations.edge_labels};groupmeasure={g.id:g for g in annotations.groups};nodes=tuple(PlacedNode(n.id,_box(byid[n.id])) for n in graph.nodes);groups=[]
    for g in graph.groups:
        n=byid[g.id];b=_box(n);label=groupmeasure[g.id];title=n.get('groupTitleRect');tb=Box(title['left'],title['top'],max(label.label_width,title['right']-title['left']),max(label.label_height,title['bottom']-title['top'])) if title else Box(b.x+(b.width-label.label_width)/2,b.y,label.label_width,label.label_height)
        groups.append(PlacedGroup(g.id,b,g.parent_id,Point(n['x'],n['y']),tb))
    edges=[];placedlabels=[];routes=[];markers=[];rawroutes=[];edgebyid={e['id']:e for e in data['edges'] if not e.get('isLayoutOnly')}
    for e in graph.edges:
        raw=edgebyid[e.id];points=tuple(Point(pt['x'],pt['y']) for pt in raw.get('points',()))
        curve=raw.get('curve') or 'rounded';curve='rounded' if curve=='basis' else curve
        # Preserve the source routing output, then apply the separate renderer
        # center-ray handoff in edges.js's swimlane-only branch.
        source=nodebyid.get(e.source);target=nodebyid.get(e.target)
        painted=paint_points(points,_box(byid[e.source]),_box(byid[e.target]),source.shape if source else 'square',target.shape if target else 'square',bymeasure.get(e.source),bymeasure.get(e.target))
        routes.append((painted,curve));markers.append((e.marker_start,e.marker_end));rawroutes.append(points)
        lid=raw.get('labelNodeId')
        if e.id in labels:
            if not lid or lid not in byid:raise error(graph.source_document,e.span.start.index,'Missing swimlane label placement','INVALID_LAYOUT')
            placedlabels.append(PlacedEdgeLabel(e.id,_box(byid[lid])))
    paths=line_hop_paths(routes,markers,data['config'].get('swimlane',{}).get('lineHops',True))
    for e,points,(painted,curve),path in zip(graph.edges,rawroutes,routes,paths):
        sections=(EdgeSection(points[0],points[1:-1],points[-1]),) if len(points)>1 else ()
        if not sections and len(points)!=1:raise error(graph.source_document,e.span.start.index,'Swimlane router omitted edge','INVALID_LAYOUT')
        edges.append(RoutedEdge(e.id,sections,painted,curve,path,path_bounds(path) if path else None))
    boxes=[n.box for n in nodes]+[g.box for g in groups];width=max((b.x+b.width for b in boxes),default=0);height=max((b.y+b.height for b in boxes),default=0)
    result=FlowLayout(nodes,tuple(edges),max(0,width),max(0,height),'mermaid-swimlane','12.2.0',tuple(groups),tuple(placedlabels))
    if annotations.title is not None:
        title=annotations.title;content=geometry_bounds(result,include_engine=False);center=content.x+content.width/2;x=center-title.width/2 if title.text_anchor=='middle' else center if title.text_anchor=='start' else center-title.width
        result=replace(result,title_box=Box(x,-graph.config.title_top_margin-title.ascent,title.width,title.height))
    return result

def _lane_paints(graph,data,p):
    byid={n['id']:n for n in data['nodes']};overrides=[]
    p.rough_enabled=graph.config.look=='handDrawn'
    for group in graph.groups:
        if group.parent_id:continue
        n=byid[group.id];style=resolve_style(graph,'group',group.id);labelstyle=resolve_style(graph,'group-title',group.id);b=_box(n)
        # Swimlane source uses createText for every label kind, with the same
        # source rich-label provider shared by the flowchart measurement.
        text=p.measure(group.raw_label if group.raw_label is not None else group.label,label_kind=group.label_kind,style=labelstyle,width=b.width)
        width=max(b.width,text.width+n.get('padding',0));left=n['x']-width/2;top=b.y
        if data['direction']=='LR':
            band=text.height+8;title=Box(left,top,band,b.height);body=Box(left+band,top,max(0,width-band),b.height);cx=left+band/2;cy=n['y'];angle=-90
        else:
            content=n.get('swimlaneContentTop',top+b.height/3);band=min(text.height,max(0,content-top));title=Box(left,top,width,band);body=Box(left,top+band,width,max(0,b.height-band));cx=n['x'];cy=top+band/2;angle=0
        # The lane overrides shared neo drop-shadow (source swimlanes/styles).
        style=replace(style,shadow_opacity=0)
        for box,fill,role in ((body,'none','swimlane-body'),(title,style.fill,'swimlane-title')):
            st=replace(style,fill=fill)
            p.path(f'M{box.x},{box.y} h{box.width} v{box.height} h{-box.width} Z',id=group.id,role=role,style=st,rough_options={'roughness':.7,'fillWeight':3} if angle==0 and fill!='none' else {'roughness':.7})
        if angle==-90:p.text(text,cx-text.height/2,cy+text.width/2,align='left',rotation=-90,id=group.id+'-label',style=labelstyle)
        else:p.text(text,cx,cy-text.height/2,align='center',id=group.id+'-label',style=labelstyle)
        overrides.append((group.id,p.take_commands()))
    return tuple(overrides)

async def build(diagram,p):
    from ...runtime.layouts import uses_builtin_elk,uses_builtin_swimlane
    c=config_dict(diagram);selected=c.get('layout','swimlane');graph=diagram.model
    if not uses_builtin_swimlane(selected):
        graph=replace(graph,config=replace(graph.config,layout=selected,theme_css='[data-look="neo"].cluster rect {filter:none;}\n'+graph.config.theme_css))
        measured,annotations=p.measure_flowchart(graph)
        if uses_builtin_elk(selected):
            from ...layout.elk.flowchart import layout_flowchart
            result=await layout_flowchart(graph,measured,measured_groups=annotations.groups,measured_edge_labels=annotations.edge_labels,measured_title=annotations.title,title_suppressed=annotations.title_suppressed)
        else:
            from ...runtime.flow_variants import layout_registered_flowchart
            result=await layout_registered_flowchart(graph,measured,annotations)
        return p.flowchart_scene(graph,result,measured=measured,annotations=annotations)
    graph=_with_default_lane(graph)
    graph=replace(graph,config=replace(graph.config,theme_css='[data-look="neo"].cluster rect {filter:none;}\n'+graph.config.theme_css))
    measured,annotations=p.measure_flowchart(graph);data=_run(_source_data(graph,measured,annotations,c));layout=_layout(graph,data,annotations,measured);overrides=_lane_paints(graph,data,p)
    return p.flowchart_scene(graph,layout,measured=measured,annotations=annotations,group_overrides=overrides)
