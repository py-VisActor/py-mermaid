"""Measured flowchart bridge for registered native layout providers."""
from __future__ import annotations
from dataclasses import replace
import math
from ..model.flowchart import (Box, Point, EdgeSection, RoutedEdge, FlowLayout,
    PlacedNode, PlacedGroup, PlacedEdgeLabel, MermaidError)
from ..config.values import thaw_value
from .graph import layout_graph


async def layout_registered_flowchart(diagram,measured,annotations):
    """Reuse every flowchart measurement/paint branch with a pure layout hook.

    Dedicated providers must return every semantic identity and label placement;
    missing output is an error, never a request to run an alternative algorithm.
    """
    from .configuration import resolve
    from ..layout.elk.compound import _outline_routes
    from ..layout.elk.flowchart import _place_title
    from ..geometry.edges.paths import rounded_path
    source=diagram.source_document
    if source is None:raise MermaidError('Registered layout needs the original source document',code='INVALID_LAYOUT_DATA')
    site=next((thaw_value(value) for name,value in diagram.config.config_layers if name=='site'),{})
    config=resolve(source,'flowchart',site);config['layout']=diagram.config.layout
    sizes={node.id:node for node in measured};labels={label.id:label for label in annotations.edge_labels}
    groups={group.id:group for group in annotations.groups}
    nodes=[{'id':node.id,'width':sizes[node.id].width,'height':sizes[node.id].height,'parent':node.parent_id,
            'shape':node.shape,'metadata':node.metadata} for node in diagram.nodes]
    parents=[{'id':group.id,'parent':group.parent_id,'padding':diagram.config.group_padding,
              'title_height':groups[group.id].label_height+diagram.config.group_title_top_margin+diagram.config.group_title_bottom_margin,
              'title_width':groups[group.id].label_width,'direction':group.direction} for group in diagram.groups]
    edges=[{'id':edge.id,'source':edge.source,'target':edge.target,'label':edge.label,
            'label_width':labels[edge.id].width if edge.id in labels else 0,'label_height':labels[edge.id].height if edge.id in labels else 0} for edge in diagram.edges]
    result=await layout_graph(nodes,edges,direction=diagram.direction,parents=parents,config=config,
        node_spacing=diagram.config.node_spacing,rank_spacing=diagram.config.rank_spacing)
    expected_nodes={node.id for node in diagram.nodes};expected_groups={group.id for group in diagram.groups}
    if set(result.nodes)!=expected_nodes or set(result.groups)!=expected_groups or set(result.edges)!={edge.id for edge in diagram.edges} or set(result.labels)!=set(labels):
        raise MermaidError('Registered layout omitted semantic identities/label placements',code='INVALID_LAYOUT')
    boxes={**dict(result.nodes.items()),**dict(result.groups.items())}
    for node in diagram.nodes:
        box=boxes[node.id];size=sizes[node.id]
        if box.width+1e-7<size.width or box.height+1e-7<size.height:raise MermaidError('Registered layout shrank measured content',code='INVALID_LAYOUT')
    routes=[]
    for edge in diagram.edges:
        points=tuple(result.edges[edge.id])
        if len(points)<2:raise MermaidError('Registered layout returned no route',code='INVALID_LAYOUT')
        routes.append(RoutedEdge(edge.id,(EdgeSection(points[0],points[1:-1],points[-1]),),effective_curve='linear'))
    routes=_outline_routes(diagram,tuple(routes),boxes,dict(result.groups.items()),measured)
    for route in routes:
        if result.edge_paths and result.edge_paths.get(route.id):
            raw=tuple(result.edges[route.id])
            if any(not math.isclose(a.x,b.x,abs_tol=1e-6) or not math.isclose(a.y,b.y,abs_tol=1e-6) for a,b in ((raw[0],route.paint_points[0]),(raw[-1],route.paint_points[-1]))):
                raise MermaidError('Registered paint paths must already meet measured shape attachments',code='INVALID_LAYOUT')
    # Layout plugins can provide their own exact curves. When absent, the
    # protocol specifies a direct polyline through their returned waypoints.
    routes=tuple(replace(route,path=result.edge_paths.get(route.id) if result.edge_paths and route.id in result.edge_paths else rounded_path(route.paint_points,0)) for route in routes)
    placed_groups=[]
    for group in diagram.groups:
        box=result.groups[group.id];title=groups[group.id]
        title_box=Box(box.x+(box.width-title.label_width)/2,box.y+diagram.config.group_padding+diagram.config.group_title_top_margin,title.label_width,title.label_height)
        placed_groups.append(PlacedGroup(group.id,box,group.parent_id,Point(box.x,box.y),title_box))
    layout=FlowLayout(tuple(PlacedNode(node.id,result.nodes[node.id]) for node in diagram.nodes),routes,
        result.width,result.height,result.engine,result.version,tuple(placed_groups),
        tuple(PlacedEdgeLabel(edge.id,result.labels[edge.id]) for edge in diagram.edges if edge.id in labels))
    return _place_title(diagram,layout,annotations.title,measured)
