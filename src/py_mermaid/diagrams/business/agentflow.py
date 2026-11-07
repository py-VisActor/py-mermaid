"""Agentflow source-specific containers, shape semantics and measured graph."""
from dataclasses import dataclass
from ...runtime.common import make_diagram,config_dict,error
from ._flow_config import flow_config
from ._agent_parser import AgentParser

@dataclass(frozen=True)
class AgentFlow:
    graph:object
    kinds:tuple
    connectors:tuple

def parse(document,config):
    # Appearance was resolved for agentflow already. Unrelated flowchart
    # defaults must not select another theme/look and recalculate its palette.
    projected=dict(config)
    projected['flowchart']={**config.get('flowchart',{}),
                            'theme':config['theme'],'look':config['look']}
    resolved=flow_config(projected)
    if len(document.cleaned.encode('utf-16-le',errors='surrogatepass'))//2>resolved.max_text_size:raise error(document,0,'Source exceeds maxTextSize','MAX_TEXT_SIZE_EXCEEDED')
    parser=AgentParser(document.cleaned,resolved,document);graph=parser.parse()
    return make_diagram('agentflow',document,config,AgentFlow(graph,tuple(parser.kinds.items()),tuple(parser.connectors)),tuple(parser.diagnostics))

def presentation(graph,c,kinds):
    from dataclasses import replace
    t=c['themeVariables'];cfg=c.get('agentflow',{});rules=[]
    borders=t.get('borderColorArray',());fills=t.get('bkgColorArray',());palette=c.get('theme') in ('redux-color','redux-dark-color') and bool(borders)
    slots={'tool':0,'task':1,'decision':2,'input':3,'refdoc':4,'connector':5,'action':6}
    if palette:
        for kind,slot in slots.items():
            fill='fill:'+fills[slot%len(fills)]+';' if fills else ''
            rules.append('[data-look="'+c.get('look','classic')+'"].node.af-kind-'+kind+' path,[data-look="'+c.get('look','classic')+'"].node.af-kind-'+kind+' rect {stroke:'+borders[slot%len(borders)]+';'+fill+'}')
    rules.append('.cluster.af-flow rect {fill:none;stroke-width:.75px;}')
    css='\n'.join(rules)+'\n'+graph.config.theme_css
    conf=replace(graph.config,theme_css=css,node_spacing=cfg.get('nodeSpacing') or 50,rank_spacing=cfg.get('rankSpacing') or 50,diagram_padding=cfg.get('diagramPadding',8),title_top_margin=cfg.get('titleTopMargin',0),min_node_width=cfg.get('minNodeWidth',graph.config.min_node_width),wrapping_width=cfg.get('wrappingWidth',graph.config.wrapping_width))
    groups=tuple(replace(group,classes=(*group.classes,'af-flow'),color_index=(7+group.color_index%max(1,len(borders)-7))%len(borders) if palette else group.color_index) for group in graph.groups)
    nodes=tuple(replace(node,classes=node.classes if node.shape=='collapsedGroup' else (*node.classes,'af-kind-'+kinds.get(node.id,'task')),color_index=(7+(node.color_index or 0)%max(1,len(borders)-7))%len(borders) if palette and node.shape=='collapsedGroup' else node.color_index) for node in graph.nodes)
    return replace(graph,config=conf,groups=groups,nodes=nodes)

async def build(diagram,p):
    # Reuse the real F014 measurement/shape/resource/marker renderer rather
    # than duplicating its 59-shape and rich-text pipelines in this family.
    from ...layout.elk.flowchart import layout_flowchart
    from ...runtime.layouts import uses_builtin_elk,uses_builtin_swimlane
    c=config_dict(diagram);graph=presentation(diagram.model.graph,c,dict(diagram.model.kinds))
    if uses_builtin_swimlane(graph.config.layout):
        from dataclasses import replace
        from .swimlane import build as build_swimlane
        return await build_swimlane(replace(diagram,model=graph),p)
    measured,annotations=p.measure_flowchart(graph)
    if uses_builtin_elk(graph.config.layout):
        layout=await layout_flowchart(graph,measured,measured_groups=annotations.groups,measured_edge_labels=annotations.edge_labels,measured_title=annotations.title,title_suppressed=annotations.title_suppressed)
    else:
        from ...runtime.flow_variants import layout_registered_flowchart
        layout=await layout_registered_flowchart(graph,measured,annotations)
    return p.flowchart_scene(graph,layout,measured=measured,annotations=annotations)
