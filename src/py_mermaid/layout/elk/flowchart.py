"""F01.1 flat rectangular flowcharts on the real py-visactor-elk engine.

Only pure JSON enters ELK; only immutable geometry leaves this adapter.
The worker is closed on success, error and cancellation. No event-loop bridge,
fallback engine, font measurement or Canvas object belongs here.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from py_mermaid.model.flowchart import (
    Box, EdgeSection, Flowchart, FlowLayout, MeasuredNode, MermaidError,
    PlacedNode, Point, RoutedEdge,
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
    if not node_ids or len(set(node_ids)) != len(node_ids) or len(set(edge_ids)) != len(edge_ids):
        raise MermaidError("Flowchart requires nonempty unique node and edge ids", code="INVALID_LAYOUT_INPUT")
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
    graph = {
        "id": "root",
        "layoutOptions": {
            "elk.algorithm": "elk.layered",
            "elk.direction": "DOWN" if diagram.direction == "TD" else "RIGHT",
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
        },
        "children": children,
        "edges": edges,
    }
    return graph, engine_nodes, engine_edges


def _read_result(result: Any, diagram: Flowchart, measured: tuple[MeasuredNode, ...], node_ids: dict, edge_ids: dict, version: str) -> FlowLayout:
    if not isinstance(result, Mapping):
        raise _fail("ELK did not return a graph mapping")
    width = _number(result.get("width"), "graph.width", positive=True)
    height = _number(result.get("height"), "graph.height", positive=True)
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
    return FlowLayout(tuple(placed), tuple(routed), width, height, "pyelk/elk.layered", version)


async def layout_flowchart(diagram: Flowchart, measured: tuple[MeasuredNode, ...]) -> FlowLayout:
    """Lay out the full flat diagram using pyelk's asynchronous native engine."""
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
    return _read_result(result, diagram, measured, node_ids, edge_ids, __version__)
