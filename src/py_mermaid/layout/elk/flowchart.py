"""F01.1 flat rectangular flowcharts on the real py-visactor-elk engine.

Only pure JSON enters ELK; only immutable geometry leaves this adapter.
The worker is closed on success, error and cancellation. No event-loop bridge,
fallback engine, font measurement or Canvas object belongs here.
"""
from __future__ import annotations

import math
from dataclasses import replace
from collections.abc import Mapping
from typing import Any

from py_mermaid.model.flowchart import (
    Box, EdgeSection, Flowchart, FlowLayout, MeasuredNode, MermaidError,
    MeasuredGroup, MeasuredEdgeLabel, MeasuredTitle, PlacedNode, Point, RoutedEdge,
)


def _fail(message: str) -> MermaidError:
    return MermaidError(message, code="INVALID_ELK_RESULT")


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _fail(f"ELK {name} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        raise _fail(f"ELK {name} must be {'positive and ' if positive else ''}finite")
    return number


def _point(value: Any, name: str) -> Point:
    if not isinstance(value, Mapping):
        raise _fail(f"ELK {name} must contain x and y")
    return Point(_number(value.get("x"), f"{name}.x"), _number(value.get("y"), f"{name}.y"))


def _index(items: Any, expected: set[str], kind: str) -> dict[str, Mapping]:
    if not isinstance(items, list):
        raise _fail(f"ELK {kind} must be a list")
    result: dict[str, Mapping] = {}
    for item in items:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            raise _fail(f"ELK {kind} entry has no string id")
        identifier = item["id"]
        if identifier not in expected or identifier in result:
            raise _fail(f"ELK {kind} has unknown or duplicate id {identifier!r}")
        result[identifier] = item
    if set(result) != expected:
        raise _fail(f"ELK {kind} omitted ids: {sorted(expected - set(result))}")
    return result


def _build_graph(diagram: Flowchart, measured: tuple[MeasuredNode, ...]) -> tuple[dict, dict, dict]:
    if diagram.direction not in ("TD", "LR") or diagram.config.layout != "elk":
        raise MermaidError("F01.1 supports only TD/LR on ELK", code="UNSUPPORTED_LAYOUT")
    node_ids = [node.id for node in diagram.nodes]
    edge_ids = [edge.id for edge in diagram.edges]
    if len(set(node_ids)) != len(node_ids) or len(set(edge_ids)) != len(edge_ids):
        raise MermaidError("Flowchart requires unique node and edge ids", code="INVALID_LAYOUT_INPUT")
    by_measure: dict[str, MeasuredNode] = {}
    for item in measured:
        if item.id in by_measure:
            raise MermaidError(f"Duplicate measured node {item.id!r}", code="INVALID_LAYOUT_INPUT")
        by_measure[item.id] = item
        for name in ("width", "height", "label_width", "label_height"):
            value = getattr(item, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise MermaidError(f"Node {item.id!r} has invalid {name}", code="INVALID_LAYOUT_INPUT")
            if value < 0 or (name in ("width", "height") and value == 0):
                raise MermaidError(f"Node {item.id!r} has invalid {name}", code="INVALID_LAYOUT_INPUT")
        if item.width < item.label_width or item.height < item.label_height:
            raise MermaidError(f"Node {item.id!r} cannot contain its measured label", code="INVALID_LAYOUT_INPUT")
    if set(by_measure) != set(node_ids):
        raise MermaidError("Measured node ids must match the complete diagram", code="INVALID_LAYOUT_INPUT")
    for name in ("node_spacing", "rank_spacing"):
        value = getattr(diagram.config, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise MermaidError(f"Invalid layout {name}", code="INVALID_LAYOUT_INPUT")
    # Engine ids are private so user ids such as 'root' cannot collide with the
    # root graph or another element kind. Declaration order stays unchanged.
    engine_nodes = {identifier: f"n{index}" for index, identifier in enumerate(node_ids)}
    engine_edges = {identifier: f"e{index}" for index, identifier in enumerate(edge_ids)}
    children = [
        {"id": engine_nodes[node.id], "width": by_measure[node.id].width, "height": by_measure[node.id].height}
        for node in diagram.nodes
    ]
    edges = []
    for edge in diagram.edges:
        if edge.source not in engine_nodes or edge.target not in engine_nodes:
            raise MermaidError(f"Edge {edge.id!r} references an unknown node", code="INVALID_LAYOUT_INPUT", span=edge.span)
        edges.append({"id": engine_edges[edge.id], "sources": [engine_nodes[edge.source]], "targets": [engine_nodes[edge.target]]})
    return {"id": "root", "layoutOptions": _root_options(diagram.direction), "children": children, "edges": edges}, engine_nodes, engine_edges


def _root_options(direction: str, config=None) -> dict:
    """Actual fixed Mermaid defaultConfig/default-preset root options."""
    options = {
            "elk.algorithm": "elk.layered",
            "elk.direction": "DOWN" if direction == "TD" else "RIGHT",
            "elk.hierarchyHandling": "INCLUDE_CHILDREN",
            "elk.edgeRouting": "ORTHOGONAL",
            "spacing.baseValue": 40,
            "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
            "elk.layered.nodePlacement.bk.fixedAlignment": "BALANCED",
            "elk.layered.layering.strategy": "NETWORK_SIMPLEX",
            "elk.layered.layering.coffmanGraham.layerBound": 4,
            "elk.layered.cycleBreaking.strategy": "DEPTH_FIRST",
            "elk.layered.mergeEdges": False,
            "elk.layered.crossingMinimization.forceNodeModelOrder": False,
            "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
            "elk.layered.wrapping.multiEdge.improveCuts": True,
            "elk.layered.wrapping.multiEdge.improveWrappedEdges": True,
            "elk.layered.unnecessaryBendpoints": True,
            "elk.layered.edgeRouting.selfLoopDistribution": "EQUALLY",
            "elk.layered.mergeHierarchyEdges": True,
            "elk.spacing.portsSurrounding": "[top=12,left=12,bottom=12,right=12]",
    }
    if config is not None:
        from .options import DIRECTIONS, RECTPACKING, algorithm, strategies
        options.update(strategies(config))
        options.pop('elk.edgeRouting', None)  # no public source mapping
        options['elk.algorithm'] = algorithm(config)
        options['elk.direction'] = DIRECTIONS[direction]
        if options['elk.algorithm'] == 'elk.rectpacking':
            options.update(RECTPACKING)
            options.update({'elk.contentAlignment':'H_CENTER V_TOP','elk.padding':'[top=15,left=15,bottom=15,right=15]'})
    return options


def _read_result(result: Any, diagram: Flowchart, measured: tuple[MeasuredNode, ...], node_ids: dict, edge_ids: dict, version: str) -> FlowLayout:
    if not isinstance(result, Mapping):
        raise _fail("ELK did not return a graph mapping")
    width = _number(result.get("width"), "graph.width", positive=bool(diagram.nodes))
    height = _number(result.get("height"), "graph.height", positive=bool(diagram.nodes))
    if width < 0 or height < 0:
        raise _fail("ELK graph dimensions must be nonnegative")
    nodes = _index(result.get("children"), set(node_ids.values()), "nodes")
    edges = _index(result.get("edges", []), set(edge_ids.values()), "edges")
    sizes = {item.id: item for item in measured}
    placed = []
    for source in diagram.nodes:
        node = nodes[node_ids[source.id]]
        box = Box(
            _number(node.get("x"), "node.x"), _number(node.get("y"), "node.y"),
            _number(node.get("width"), "node.width", positive=True),
            _number(node.get("height"), "node.height", positive=True),
        )
        original = sizes[source.id]
        if not math.isclose(box.width, original.width, rel_tol=1e-9, abs_tol=1e-7) or not math.isclose(box.height, original.height, rel_tol=1e-9, abs_tol=1e-7):
            raise _fail(f"ELK changed fixed dimensions for node {source.id!r}")
        placed.append(PlacedNode(source.id, box))
    routed = []
    for source in diagram.edges:
        edge = edges[edge_ids[source.id]]
        if edge.get("sources") != [node_ids[source.source]] or edge.get("targets") != [node_ids[source.target]]:
            raise _fail(f"ELK changed endpoints for edge {source.id!r}")
        sections = edge.get("sections")
        if not isinstance(sections, list) or not sections:
            raise _fail(f"ELK returned no route sections for edge {source.id!r}")
        converted = []
        for section in sections:
            if not isinstance(section, Mapping):
                raise _fail(f"ELK section for edge {source.id!r} is invalid")
            bends = section.get("bendPoints", [])
            if not isinstance(bends, list):
                raise _fail("ELK section bendPoints must be a list")
            converted.append(EdgeSection(
                _point(section.get("startPoint"), "section.startPoint"),
                tuple(_point(point, "section.bendPoint") for point in bends),
                _point(section.get("endPoint"), "section.endPoint"),
            ))
        routed.append(RoutedEdge(source.id, tuple(converted)))
    from py_mermaid.geometry.edges.alignment import align_degenerate_boxes
    semantic_edge_ids = {engine:semantic for semantic,engine in edge_ids.items()}
    order = [semantic_edge_ids[edge['id']] for edge in result.get('edges',[])]
    painted = align_degenerate_boxes(diagram,routed,{node.id:node.box for node in placed},order)
    return FlowLayout(tuple(replace(node,paint_box=painted.get(node.id)) for node in placed),
                      tuple(routed), width, height, "pyelk/elk.layered", version)


async def layout_flowchart(
    diagram: Flowchart, measured: tuple[MeasuredNode, ...], *,
    measured_groups: tuple[MeasuredGroup, ...] = (),
    measured_edge_labels: tuple[MeasuredEdgeLabel, ...] = (),
    measured_title: MeasuredTitle | None = None,
    title_suppressed: bool = False,
) -> FlowLayout:
    """Real async ELK; preserve the original no-group square-node path."""
    _validate_title(diagram, measured_title, title_suppressed)
    _validate_edges(diagram)
    enhanced = bool(diagram.groups or measured_groups or measured_edge_labels or
                    any(edge.label for edge in diagram.edges) or
                    any(node.shape != "square" for node in diagram.nodes) or
                    diagram.direction not in ('TD','LR') or diagram.config.layout != 'elk' or
                    bool(diagram.config.elk_options))
    if enhanced:
        from .compound import prepare_compound, read_compound
        graph, state = prepare_compound(diagram, measured, measured_groups, measured_edge_labels)
    else:
        graph, node_ids, edge_ids = _build_graph(diagram, measured)
    try:
        from pyelk import ELK, __version__
    except ImportError as exc:
        raise MermaidError("py-visactor-elk==0.1.0 is required for flowchart layout", code="ELK_UNAVAILABLE") from exc
    if __version__ != "0.1.0":
        raise MermaidError(f"Expected py-visactor-elk 0.1.0, got {__version__}", code="ELK_VERSION_MISMATCH")
    try:
        with ELK() as engine:
            result = await engine.layout(graph)
    except Exception as exc:
        raise MermaidError(f"ELK layout failed: {exc}", code="ELK_LAYOUT_FAILED") from exc
    if enhanced:
        layout = read_compound(result, diagram, measured, measured_groups, measured_edge_labels, state, __version__)
    else:
        layout = _read_result(result, diagram, measured, node_ids, edge_ids, __version__)
    from py_mermaid.geometry.edges import finish_edges
    layout = finish_edges(diagram, layout, measured)
    return _place_title(diagram, layout, measured_title, measured)


def _validate_edges(diagram):
    for edge in diagram.edges:
        if edge.marker_start not in ('none','point','circle','cross') or edge.marker_end not in ('none','point','circle','cross'):
            raise MermaidError('Unknown edge marker',code='INVALID_LAYOUT_INPUT')
        if edge.stroke not in ('normal','thick','dotted','invisible','INVALID'):
            raise MermaidError('Unknown edge stroke',code='INVALID_LAYOUT_INPUT')
        if edge.min_length is not None and (isinstance(edge.min_length,bool) or not isinstance(edge.min_length,int) or edge.min_length < 1 or edge.min_length > 10):
            raise MermaidError('Edge length must be an integer from 1 to 10',code='INVALID_LAYOUT_INPUT')


def _validate_title(diagram: Flowchart, title: MeasuredTitle | None, suppressed: bool = False) -> None:
    """Reject an incomplete measurement contract before allocating a worker."""
    if not isinstance(diagram.title, str):
        raise MermaidError("Diagram title must be text", code="INVALID_LAYOUT_INPUT")
    if not isinstance(suppressed, bool):
        raise MermaidError("Title suppression must be boolean", code="INVALID_LAYOUT_INPUT")
    if suppressed:
        if title is not None:
            raise MermaidError("Suppressed title cannot have measured ink", code="INVALID_LAYOUT_INPUT")
        return
    if not diagram.title:
        if title is not None:
            raise MermaidError("Unexpected title measurement for an untitled diagram", code="INVALID_LAYOUT_INPUT")
        return
    if title is None:
        raise MermaidError("Diagram title requires an actual measured title box", code="INVALID_LAYOUT_INPUT")
    for name in ("width", "height", "ascent", "descent"):
        value = getattr(title, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise MermaidError(f"Invalid measured title {name}", code="INVALID_LAYOUT_INPUT")
    if title.height + 1e-7 < title.ascent + title.descent:
        raise MermaidError("Measured title height does not contain its actual ink", code="INVALID_LAYOUT_INPUT")
    if title.text_anchor not in ("start", "middle", "end"):
        raise MermaidError("Measured title anchor must be start, middle or end", code="INVALID_LAYOUT_INPUT")
    margin = diagram.config.title_top_margin
    if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not math.isfinite(margin) or margin < 0:
        raise MermaidError("Title top margin must be finite and nonnegative", code="INVALID_LAYOUT_INPUT")


def _place_title(diagram: Flowchart, layout: FlowLayout, title: MeasuredTitle | None, measured=()) -> FlowLayout:
    """Source insertTitle: anchor at content center, baseline at -margin.

    Actual measured title geometry is added after real layout. It neither
    becomes a graph node nor changes the engine's node/edge/group coordinates.
    Export viewport code can union the resulting negative-y ink with content.
    """
    if title is None:
        return layout
    from py_mermaid.geometry.flowchart import geometry_bounds
    sizes = {item.id:item for item in measured}
    # Source ordinary-node paint repositions the cached measurement; it does
    # not stretch that ink when a packing algorithm expands its physical box.
    ink_nodes = []
    for node in layout.nodes:
        physical = node.paint_box or node.box
        if node.id in sizes:
            size = sizes[node.id]
            ink = Box(physical.x+(physical.width-size.width)/2,
                      physical.y+(physical.height-size.height)/2,size.width,size.height)
            ink_nodes.append(replace(node,box=ink,paint_box=None))
        else:ink_nodes.append(node)
    content = geometry_bounds(replace(layout,nodes=tuple(ink_nodes)), include_engine=False)
    center = content.x + content.width / 2
    # The source presentation attribute is middle, but applicable theme CSS
    # text-anchor overrides it. text-align is a distinct label-box property.
    left = center if title.text_anchor == "start" else center - title.width if title.text_anchor == "end" else center - title.width / 2
    box = Box(left,
              -diagram.config.title_top_margin - title.ascent,
              title.width, title.height)
    return replace(layout, title_box=box)
