"""Measured generic graphs on the published ELK provider; no layout fallback."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, replace
import math
from ..model.flowchart import Box, Point, MermaidError


@dataclass(frozen=True)
class FrozenLookup(Mapping):
    entries: tuple
    def __getitem__(self,key):
        for name,value in self.entries:
            if name==key:return value
        raise KeyError(key)
    def __iter__(self):return (name for name,value in self.entries)
    def __len__(self):return len(self.entries)


@dataclass(frozen=True)
class GraphLayout:
    nodes: Mapping
    edges: Mapping
    groups: Mapping
    labels: Mapping
    width: float
    height: float
    engine: str = 'py-visactor-elk'
    version: str = '0.1.0'
    edge_paths: Mapping | None = None
    raw_edges: Mapping | None = None
    group_data: tuple = ()


def finish_graph(layout,edge_data=(),*,config=None):
    """Shared fixed ELK terminal-jog straightening, label projection and jumps.

    Shape owners may call this again after clipping endpoints. Raw engine
    routes remain in raw_edges; only paint routes/labels/paths are replaced.
    """
    from ..geometry.edges.pipeline import _front, _project, _hits, _crossings
    from ..geometry.edges.paths import dedupe, line_hop_paths
    from ..config.elk import DEFAULTS
    settings={**DEFAULTS,**((config or {}).get('elk') or {})}
    edge_data={edge['id']:edge for edge in edge_data}
    ids=tuple(layout.edges);routes=[dedupe(layout.edges[identifier]) for identifier in ids]
    labels=dict(layout.labels.items())
    if settings['straightenEdges']:
        for index,route in enumerate(routes):
            candidate,front=_front(route);candidate,back=_front(tuple(reversed(candidate)))
            candidate=tuple(reversed(candidate));runs=front+back
            if not runs:continue
            identifier=ids[index];box=labels.get(identifier);moved=box
            if box is not None:
                center=_project(Point(box.x+box.width/2,box.y+box.height/2),runs)
                moved=replace(box,x=center.x-box.width/2,y=center.y-box.height/2)
            before=after=covered_before=covered_after=0
            for other,path in enumerate(routes):
                if other==index:continue
                before+=_crossings(route,path);after+=_crossings(candidate,path)
                other_box=labels.get(ids[other])
                covered_before+=int(_hits(path,box))+int(_hits(route,other_box))
                covered_after+=int(_hits(path,moved))+int(_hits(candidate,other_box))
            if after>before or covered_after>covered_before:continue
            routes[index]=candidate
            if moved is not None:labels[identifier]=moved
    curves=tuple(edge_data.get(identifier,{}).get('curve','rounded') for identifier in ids)
    # Families paint their own marker variants, so this stage does not apply
    # the flowchart-only marker pullback table to class/ER/use-case markers.
    paths=line_hop_paths(tuple(zip(routes,curves)),[('none','none') for _ in ids],settings['lineHops'])
    return replace(layout,edges=FrozenLookup(tuple(zip(ids,routes))),labels=FrozenLookup(tuple(labels.items())),
        edge_paths=FrozenLookup(tuple(zip(ids,paths))),raw_edges=layout.raw_edges or layout.edges)


def _numeric(value,name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise MermaidError('Invalid ELK '+name,code='INVALID_ELK_RESULT')
    return float(value)


async def layout_graph(nodes,edges,*,direction='TB',parents=(),options=None,node_spacing=50,rank_spacing=50,config=None,algorithm=None):
    from .layouts import layout_definition, load_layout
    from ..config.elk import validate_elk
    selected=algorithm or (config or {}).get('layout','elk')
    entry=layout_definition(selected)
    if entry.provider is not None:
        result=await load_layout(entry)(nodes,edges,direction=direction,parents=parents,options=options,
            node_spacing=node_spacing,rank_spacing=rank_spacing,config=config,algorithm=entry.algorithm)
        if not isinstance(result,GraphLayout):raise MermaidError('Layout provider must return GraphLayout',code='INVALID_LAYOUT')
        return result
    from pyelk import ELK
    direction_map={'TB':'DOWN','TD':'DOWN','BT':'UP','LR':'RIGHT','RL':'LEFT'}
    if direction not in direction_map:raise MermaidError('Invalid graph direction',code='INVALID_DIRECTION')
    nodes=tuple(dict(n) for n in nodes);edges=tuple(dict(e) for e in edges);parents=tuple(dict(p) for p in parents)
    ids=[n['id'] for n in (*nodes,*parents)]
    if len(set(ids))!=len(ids):raise MermaidError('Duplicate graph node/group identity',code='DUPLICATE_ID')
    if len(set(e['id'] for e in edges))!=len(edges):raise MermaidError('Duplicate graph edge identity',code='DUPLICATE_ID')
    from ..layout.elk.flowchart import _root_options
    from types import SimpleNamespace
    settings=SimpleNamespace(layout=selected,elk_options=tuple(validate_elk((config or {}).get('elk',{})).items()))
    root_options=_root_options(direction,settings)
    root_options.update({'elk.spacing.nodeNode':str(node_spacing),'elk.layered.spacing.nodeNodeBetweenLayers':str(rank_spacing)})
    root_id='__py_mermaid_root__'
    while root_id in ids:root_id+='_' # private engine identity cannot collide with source IDs
    root={'id':root_id,'layoutOptions':root_options,
        'children':[],'edges':[]}
    if options:
        for key,value in dict(options).items():
            name=key if key.startswith(('elk.','org.eclipse.elk.')) else 'elk.'+key
            root['layoutOptions'][name]=str(value).lower() if isinstance(value,bool) else str(value)
    containers={root['id']:root};parent_of={};input_nodes={}
    for item in parents:
        pad=item.get('padding',12);title=item.get('title_height',0)
        options={'elk.padding':f'[top={pad+title},left={pad},bottom={pad},right={pad}]'}
        if item.get('direction'):
            if item['direction'] not in direction_map:raise MermaidError('Invalid group direction',code='INVALID_DIRECTION')
            options['elk.direction']=direction_map[item['direction']]
        containers[item['id']]={'id':item['id'],'children':[],'edges':[],'layoutOptions':options}
    for item in parents:
        parent=item.get('parent') or root['id']
        if parent not in containers:raise MermaidError('Unknown graph parent',code='UNKNOWN_PARENT')
        cursor=parent;seen={item['id']}
        while cursor!=root['id']:
            if cursor in seen:raise MermaidError('Cyclic graph parent',code='INVALID_PARENT')
            seen.add(cursor);cursor=next((p.get('parent') or root['id'] for p in parents if p['id']==cursor),root['id'])
        containers[parent]['children'].append(containers[item['id']]);parent_of[item['id']]=parent
    for item in nodes:
        parent=item.get('parent') or root['id']
        if parent not in containers:raise MermaidError('Unknown graph parent',code='UNKNOWN_PARENT')
        width=_numeric(item['width'],'node width');height=_numeric(item['height'],'node height')
        if width<0 or height<0:raise MermaidError('Negative measured node size',code='INVALID_GRAPH')
        value={'id':item['id'],'width':width,'height':height}
        for field in ('ports','labels','layoutOptions'):
            if field in item:value[field]=item[field]
        if item.get('spreadPorts'):
            # createElkNode: implicit ports are spread by CENTER alignment;
            # explicit port spacing is deliberately not the source mechanism.
            value['layoutOptions']={**value.get('layoutOptions',{}),'elk.portAlignment.default':'CENTER'}
        containers[parent]['children'].append(value);parent_of[item['id']]=parent;input_nodes[item['id']]=item
    def ancestors(name):
        result=[name]
        while name in parent_of:name=parent_of[name];result.append(name)
        return result
    edge_owners={}
    for item in edges:
        if item['source'] not in ids or item['target'] not in ids:raise MermaidError('Unknown relationship endpoint',code='UNKNOWN_NODE')
        left=ancestors(item['source']);right=set(ancestors(item['target']))
        owner=next(name for name in left[1:] if name in right) if any(name in right for name in left[1:]) else root['id']
        value={'id':item['id'],'sources':[item.get('source_port') or item['source']],
               'targets':[item.get('target_port') or item['target']]}
        if item.get('label'):
            value['labels']=[{'id':item['id']+'__label','text':item['label'],
                              'width':item.get('label_width',0),'height':item.get('label_height',0)}]
        containers[owner]['edges'].append(value);edge_owners[item['id']]=owner
    with ELK() as engine:result=await engine.layout(root)
    placed={};groups={};routed={};labels={};offsets={}
    def visit(node,x=0,y=0):
        px=x+_numeric(node.get('x',0),'x');py=y+_numeric(node.get('y',0),'y');offsets[node['id']]=(px,py)
        if node['id'] in input_nodes:placed[node['id']]=Box(px,py,_numeric(node.get('width',0),'width'),_numeric(node.get('height',0),'height'))
        elif node['id'] in containers and node['id']!=root['id']:groups[node['id']]=Box(px,py,_numeric(node.get('width',0),'width'),_numeric(node.get('height',0),'height'))
        for child in node.get('children',[]):visit(child,px,py)
        for edge in node.get('edges',[]):
            points=[]
            for section in edge.get('sections',[]):
                for point in [section['startPoint'],*section.get('bendPoints',[]),section['endPoint']]:
                    value=Point(px+_numeric(point['x'],'edge x'),py+_numeric(point['y'],'edge y'))
                    if not points or points[-1]!=value:points.append(value)
            routed[edge['id']]=tuple(points)
            for label in edge.get('labels',[]):labels[edge['id']]=Box(px+label.get('x',0),py+label.get('y',0),label.get('width',0),label.get('height',0))
    visit(result)
    if set(placed)!=set(input_nodes) or set(routed)!={e['id'] for e in edges}:
        raise MermaidError('ELK omitted graph identities',code='INVALID_ELK_RESULT')
    # Source applyElkEdgeLayout draws centre rays for non-routing algorithms.
    # This is their paint contract, not a request to run a fallback layout.
    all_boxes={**placed,**groups}
    for item in edges:
        if not routed[item['id']]:
            start=all_boxes[item['source']];end=all_boxes[item['target']]
            first=Point(start.x+start.width/2,start.y+start.height/2)
            last=Point(end.x+end.width/2,end.y+end.height/2)
            routed[item['id']]=(first,) if first==last else (first,last)
    layout=GraphLayout(*(FrozenLookup(tuple(mapping.items())) for mapping in [placed,routed,groups,labels]),
                       _numeric(result.get('width',0),'graph width'),_numeric(result.get('height',0),'graph height'))
    return finish_graph(layout,edges,config=config)
