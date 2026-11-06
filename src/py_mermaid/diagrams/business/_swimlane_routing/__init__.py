"""Pure fixed-source swimlane routing and renderer-facing postprocessing.

Input node coordinates are canonical TB centers. The supplied local layout is
mutated exactly at the routing boundary; no native objects or resources enter.
"""
from .router import route_edges_orthogonal
from .direction import apply_lr,apply_bt
from .geometry import simplify,orthogonalize
from .detours import simplify_detours
from .shared_tracks import straighten_siblings,nudge_shared_interiors
from .terminal_routes import port_swap,collapse_short_stub
from .endpoint_clip import clip_endpoints,prepare_endpoints
from .label_anchoring import anchor_labels
from .materialized import (separate_terminal_lanes,collapse_doglegs,
    lift_hugging_rails,swap_destination_tails,resolve_crossings,
    reassign_external_channels,shortcut_jogs,lift_top_titles,shift_left_titles)
from .validation import validate as validate_swimlanes_layout


def post_process(layout:dict,direction:str)->None:
    """Source postProcessSwimlaneLayout, preserving its ordered bounded passes."""
    nodes=layout.get('nodes',[]);edges=layout.get('edges',[])
    content=[n for n in nodes if not n.get('isGroup')]
    if direction in ('LR','RL') and content and not apply_lr(layout,direction):return
    if direction=='BT' and content and not apply_bt(layout):return
    for edge in edges:
        if edge.get('isLayoutOnly'):continue
        pts=edge.get('points') or []
        if len(pts)>=2:edge['points']=simplify(orthogonalize(pts))
    simplify_detours(edges,nodes)
    straighten_siblings(edges,nodes)
    port_swap(edges,nodes)
    by_id={str(n['id']):n for n in nodes}
    anchor_labels(edges,by_id)
    clip_endpoints(edges,by_id)
    collapse_short_stub(edges,by_id)
    nudge_shared_interiors(edges,by_id)
    separate_terminal_lanes(edges,by_id)
    collapse_doglegs(edges,by_id)
    lift_hugging_rails(edges,by_id)
    swap_destination_tails(edges,by_id)

    def finalize():
        resolve_crossings(edges,by_id)
        separate_terminal_lanes(edges,by_id)
        reassign_external_channels(edges,by_id)
        shortcut_jogs(edges,by_id)
        anchor_labels(edges,by_id)
        prepare_endpoints(edges,by_id)
        lift_hugging_rails(edges,by_id)
        anchor_labels(edges,by_id)
        prepare_endpoints(edges,by_id)

    finalize()
    nudge_shared_interiors(edges,by_id)
    finalize()
    lift_top_titles(edges,by_id,direction)
    shift_left_titles(edges,by_id,direction)
    lift_top_titles(edges,by_id,direction)
    shift_left_titles(edges,by_id,direction)


def route_and_postprocess(layout:dict,direction:str)->None:
    """Route, orient, postprocess and diagnose the supplied pure local layout."""
    route_edges_orthogonal(layout,direction)
    post_process(layout,direction)
    validate_swimlanes_layout(layout)


__all__=['route_and_postprocess','validate_swimlanes_layout']
