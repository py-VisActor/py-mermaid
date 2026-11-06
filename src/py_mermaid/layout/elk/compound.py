"""Measured flowchart groups, center labels and shape attachment on real ELK.

Source: fixed Mermaid elk/render.ts group policy / label construction / frame
tightening, subgraphFeedbackEdges.ts, and pyelk 0.1.0 container-local export.
Every returned coordinate is absolute logical px. Frame tightening never moves
the engine origin used to translate routes. No font or layout is fabricated.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any
from collections.abc import Mapping

from py_mermaid.model.flowchart import (
    Box, EdgeSection, Flowchart, FlowLayout, MeasuredEdgeLabel, MeasuredGroup,
    MeasuredNode, MermaidError, PlacedEdgeLabel, PlacedGroup, PlacedNode, Point,
    RoutedEdge,
)
from .flowchart import _fail, _index, _number, _point, _root_options
from .options import (DIRECTIONS, CONTAINER_OVERRIDES, RECTPACKING, algorithm,
                      container_algorithm, cyclic_entries, settings, strategies)

_DIRECTION = DIRECTIONS
_SUBGRAPH_PADDING = 24.0


@dataclass(frozen=True)
class _State:
    element_ids: dict[str, str]
    edge_ids: dict[str, str]
    parents: dict[str, str | None]
    reversed_edges: frozenset[str]
    algorithms: dict[str, str]
    expanding_containers: frozenset[str]


def _input(message: str) -> MermaidError:
    return MermaidError(message, code="INVALID_LAYOUT_INPUT")


def _measurements(items, expected, fields):
    result = {}
    for item in items:
        if item.id in result or item.id not in expected:
            raise _input(f"Unknown or duplicate measured annotation {item.id!r}")
        for field in fields:
            value = getattr(item, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise _input(f"Invalid measured {field} for {item.id!r}")
        result[item.id] = item
    if set(result) != set(expected):
        raise _input(f"Measurements do not match required ids: {sorted(set(expected) ^ set(result))}")
    return result


def _lca(source: str, target: str, parents: dict[str, str | None]) -> str | None:
    if source == target:
        return parents[source]
    ancestors = set()
    current = source
    while current is not None:
        ancestors.add(current)
        current = parents[current]
    current = target
    while current is not None:
        if current in ancestors:
            return current
        current = parents[current]
    return None


def _feedback_edges(diagram: Flowchart, parents: dict[str, str | None]) -> frozenset[str]:
    """Source DFS in declaration order on collapsed lowest-common-group graphs."""
    levels: dict[str | None, list] = {}
    for edge in diagram.edges:
        if edge.source == edge.target:
            continue
        ancestor = _lca(edge.source, edge.target, parents)
        if ancestor in (edge.source, edge.target):
            continue
        def child_on_path(identifier):
            while parents[identifier] != ancestor:
                identifier = parents[identifier]
            return identifier
        source, target = child_on_path(edge.source), child_on_path(edge.target)
        levels.setdefault(ancestor, []).append((edge.id, source, target, source != edge.source or target != edge.target))
    reversed_ids = set()
    for edges in levels.values():
        outgoing, incoming = {}, {}
        for edge in edges:
            _, source, target, _ = edge
            for identifier in (source, target):
                outgoing.setdefault(identifier, [])
                incoming.setdefault(identifier, 0)
            outgoing[source].append(edge)
            incoming[target] += 1
        seen = {}
        roots = [identifier for identifier in outgoing if incoming[identifier] == 0] + list(outgoing)
        for root in roots:
            if root in seen:
                continue
            seen[root] = 1
            stack = [(root, 0)]
            while stack:
                identifier, index = stack[-1]
                if index == len(outgoing[identifier]):
                    seen[identifier] = 2
                    stack.pop()
                    continue
                stack[-1] = (identifier, index + 1)
                edge_id, _, target, collapsed = outgoing[identifier][index]
                if seen.get(target) == 1 and collapsed:
                    reversed_ids.add(edge_id)
                elif target not in seen:
                    seen[target] = 1
                    stack.append((target, 0))
    return frozenset(reversed_ids)


def _group_options(group, measurement, config) -> dict:
    options = {
        "nodeSize.constraints": "[MINIMUM_SIZE, NODE_LABELS]",
        "nodeSize.minimum": f"({measurement.label_width + config.group_padding}, 0)",
        "spacing.baseValue": 24,
        "elk.layered.spacing.edgeNodeBetweenLayers": 30,
        "elk.spacing.edgeEdge": 20,
        "spacing.nodeNode": 50,
        "elk.padding": "[top=24,left=24,bottom=24,right=24]",
        "nodeLabels.placement": "[H_CENTER V_TOP, INSIDE]",
        "elk.layered.mergeEdges": False,
        "elk.layered.nodePlacement.bk.fixedAlignment": "BALANCED",
        "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
        "elk.layered.cycleBreaking.strategy": "DEPTH_FIRST",
        "elk.layered.nodePlacement.networkSimplex.nodeFlexibility": "PORT_POSITION",
        "elk.spacing.portsSurrounding": "[top=12,left=12,bottom=12,right=12]",
    }
    options.update(strategies(config, container=True))
    custom = container_algorithm(group, warn=True)
    if custom:
        padding = 10 if custom == 'elk.rectpacking' else 15
        top = measurement.label_height + padding
        options.update({'nodeSize.minimum':f'({measurement.label_width + 2*config.group_padding}, {top+padding})',
                        'elk.algorithm':custom,'elk.hierarchyHandling':'SEPARATE_CHILDREN',
                        'elk.aspectRatio':'2.0','elk.contentAlignment':'H_CENTER V_TOP','elk.expandNodes':'true',
                        'elk.padding':f'[top={top},left={padding},bottom={padding},right={padding}]'})
        if custom == 'elk.rectpacking':
            options.update(RECTPACKING)
            options['elk.padding'] = f'[top={top},left={padding},bottom={padding},right={padding}]'
    elif group.direction is not None:
        if group.direction not in _DIRECTION:
            raise _input(f"Unknown group direction {group.direction!r}")
        options.update({"elk.algorithm": algorithm(config), "elk.direction": _DIRECTION[group.direction],
                        "elk.hierarchyHandling": "SEPARATE_CHILDREN"})
    return options


def _adapt_title_minima(diagram, raw_nodes, parents, group_sizes):
    """Express measured title width in pyelk 0.1.0's compound minimum frame.

    INCLUDE_CHILDREN's vertical run transposes the containing native node's
    minimum before nested graph sizing, whereas a SEPARATE_CHILDREN run accepts
    physical x/y. The pinned engine's public JSON therefore needs the title
    width in the y component for populated groups in a vertical compound run.
    This is an input-constraint conversion, never a post-layout frame growth.
    See the preserved Unicode raw-input/output direction probes in the F01.2
    change receipt. Empty groups have no nested native graph and are not swapped.
    """
    policies = {}
    root_direction = _DIRECTION[diagram.direction]
    def policy(identifier):
        if identifier in policies:
            return policies[identifier]
        parent = parents[identifier]
        inherited_mode, inherited_direction = policy(parent) if parent is not None else ("INCLUDE_CHILDREN", root_direction)
        options = raw_nodes[identifier]["layoutOptions"]
        mode = options.get("elk.hierarchyHandling", inherited_mode)
        direction = options.get("elk.direction", inherited_direction) if mode == "SEPARATE_CHILDREN" else inherited_direction
        policies[identifier] = (mode, direction)
        return mode, direction
    for group in diagram.groups:
        raw = raw_nodes[group.id]
        mode, direction = policy(group.id)
        if algorithm(diagram.config) == 'elk.layered' and raw["children"] and mode == "INCLUDE_CHILDREN" and direction in ("DOWN", "UP"):
            width = group_sizes[group.id].label_width + diagram.config.group_padding
            raw["layoutOptions"]["nodeSize.minimum"] = f"(0, {width})"


def prepare_compound(diagram, measured, measured_groups, measured_edge_labels):
    if diagram.direction not in _DIRECTION:
        raise MermaidError("Unknown flowchart direction", code="UNSUPPORTED_LAYOUT")
    algorithm(diagram.config)
    # flowDb.getData emits groups in reverse reduction order, then ordinary
    # vertices in insertion order; addVertices preserves that sibling order.
    elements = (*reversed(diagram.groups), *diagram.nodes)
    ids = [element.id for element in elements]
    if any(not isinstance(identifier, str) for identifier in ids) or len(set(ids)) != len(ids):
        raise _input("Nodes and groups require unique string ids in one namespace")
    edge_ids = [edge.id for edge in diagram.edges]
    if any(not isinstance(identifier, str) for identifier in edge_ids) or len(set(edge_ids)) != len(edge_ids):
        raise _input("Edges require unique string ids")
    group_ids = {group.id for group in diagram.groups}
    parents = {element.id: element.parent_id for element in elements}
    for element in elements:
        if element.parent_id is not None and element.parent_id not in group_ids:
            raise _input(f"Unknown parent group of {element.id!r}")
        seen = {element.id}
        ancestor = element.parent_id
        while ancestor is not None:
            if ancestor in seen:
                raise _input(f"Cyclic group membership at {element.id!r}")
            seen.add(ancestor)
            ancestor = parents[ancestor]
    for group in diagram.groups:
        if any(member not in parents for member in group.members):
            raise _input(f"Group {group.id!r} has an unknown member")
    for edge in diagram.edges:
        if edge.source not in parents or edge.target not in parents:
            raise _input(f"Unknown endpoint of edge {edge.id!r}")
    for field in ("group_padding", "group_title_top_margin", "group_title_bottom_margin", "node_spacing", "rank_spacing"):
        value = getattr(diagram.config, field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise _input(f"Invalid layout configuration {field}")
    from py_mermaid.geometry.shape_registry import is_valid_shape
    for node in diagram.nodes:
        if node.shape == "ellipse":
            raise MermaidError("Classic ellipse renderer is missing upstream", code="UPSTREAM_SHAPE_MISSING", span=node.span)
        if not is_valid_shape(node.shape):
            raise MermaidError(f"Unknown flowchart shape {node.shape!r}", code="UNSUPPORTED_SHAPE", span=node.span)
    sizes = _measurements(measured, {node.id for node in diagram.nodes}, ("width", "height", "label_width", "label_height"))
    for size in sizes.values():
        if size.width <= 0 or size.height <= 0 or size.width < size.label_width or size.height < size.label_height:
            raise _input(f"Invalid measured dimensions of {size.id!r}")
    group_sizes = _measurements(measured_groups, group_ids, ("label_width", "label_height"))
    edge_sizes = _measurements(measured_edge_labels, {edge.id for edge in diagram.edges if edge.label}, ("width", "height"))
    for size in edge_sizes.values():
        # Source addEdgesToElkGraph accepts a zero-width label. Sanitized empty
        # rich text or a line-break-only label still has a real line height.
        if size.height <= 0:
            raise _input(f"Edge label {size.id!r} needs a positive measured height")
    engine_ids = {node.id: f"n{i}" for i, node in enumerate(diagram.nodes)}
    engine_ids.update({group.id: f"g{i}" for i, group in enumerate(diagram.groups)})
    engine_edges = {edge.id: f"e{i}" for i, edge in enumerate(diagram.edges)}
    raw_nodes = {node.id: {"id": engine_ids[node.id], "width": sizes[node.id].width, "height": sizes[node.id].height}
                 for node in diagram.nodes}
    for group in diagram.groups:
        size = group_sizes[group.id]
        raw_nodes[group.id] = {
            "id": engine_ids[group.id], "children": [], "isGroup": True,
            "labels": [{"id": f"title-{engine_ids[group.id]}", "text": group.label,
                        "width": size.label_width, "height": size.label_height}],
            "layoutOptions": _group_options(group, size, diagram.config),
        }
    root = {"id": "root", "layoutOptions": _root_options(diagram.direction, diagram.config), "children": [], "edges": []}
    for parent_id in (None, *(group.id for group in diagram.groups)):
        children = [element.id for element in elements if parents[element.id] == parent_id]
        container = root if parent_id is None else raw_nodes[parent_id]
        container["children"] = [raw_nodes[identifier] for identifier in children]
        if parent_id is not None and not children:
            # Empty groups are actual measured title boxes with source inner
            # padding; only dimensions are specified, never positions.
            title = group_sizes[parent_id]
            container["width"] = max(title.label_width + 2 * _SUBGRAPH_PADDING, 2 * _SUBGRAPH_PADDING)
            container["height"] = max(title.label_height + 2 * _SUBGRAPH_PADDING, 2 * _SUBGRAPH_PADDING)
    if settings(diagram.config)['keepEntryNodeOnTop']:
        for identifier in cyclic_entries(elements, diagram.edges):
            raw_nodes[identifier].setdefault('layoutOptions', {})['elk.layered.layering.layerConstraint'] = 'FIRST'
    reversed_edges = _feedback_edges(diagram, parents) if settings(diagram.config)['orientFeedbackEdges'] else frozenset()
    for edge in diagram.edges:
        source, target = edge.source, edge.target
        if edge.id in reversed_edges:
            source, target = target, source
        raw = {"id": engine_edges[edge.id], "sources": [engine_ids[source]], "targets": [engine_ids[target]]}
        if edge.label:
            size = edge_sizes[edge.id]
            raw["labels"] = [{"id": f"label-{engine_edges[edge.id]}", "text": edge.label,
                              "width": size.width, "height": size.height,
                              "layoutOptions": {"edgeLabels.inline": "true", "edgeLabels.placement": "CENTER"}}]
        root["edges"].append(raw)
        # Source cross-boundary policy changes only hierarchy handling, retaining
        # explicit direction metadata. The real engine resolves its own policy.
        if parents[edge.source] != parents[edge.target]:
            ancestor = _lca(edge.source, edge.target, parents)
            for endpoint in (edge.source, edge.target):
                current = endpoint
                while current is not None:
                    options = raw_nodes[current].setdefault("layoutOptions", {})
                    group = next((group for group in diagram.groups if group.id == current),None)
                    if group is not None and container_algorithm(group) and options.get('elk.hierarchyHandling') == 'SEPARATE_CHILDREN':
                        for key in CONTAINER_OVERRIDES:options.pop(key,None)
                        options.update({'spacing.baseValue':24,'spacing.nodeNode':50,
                                        'elk.padding':'[top=24,left=24,bottom=24,right=24]',
                                        'nodeSize.constraints':'[MINIMUM_SIZE, NODE_LABELS]',
                                        'nodeSize.minimum':f'({group_sizes[current].label_width+diagram.config.group_padding}, 0)'})
                    options["elk.hierarchyHandling"] = "INCLUDE_CHILDREN"
                    if current == ancestor:
                        break
                    current = parents[current]
    _adapt_title_minima(diagram, raw_nodes, parents, group_sizes)
    algorithms = {'root': algorithm(diagram.config)}
    def resolve_algorithm(identifier):
        engine_id = engine_ids[identifier]
        if engine_id not in algorithms:
            inherited = resolve_algorithm(parents[identifier]) if parents[identifier] is not None else algorithms['root']
            algorithms[engine_id] = raw_nodes[identifier].get('layoutOptions',{}).get('elk.algorithm',inherited)
        return algorithms[engine_id]
    for identifier in parents:resolve_algorithm(identifier)
    expanding = {engine_ids[identifier] for identifier,raw in raw_nodes.items()
                 if raw.get('layoutOptions',{}).get('elk.expandNodes') in (True,'true')}
    if root['layoutOptions'].get('elk.expandNodes') in (True,'true'):expanding.add('root')
    return root, _State(engine_ids, engine_edges, parents, reversed_edges, algorithms, frozenset(expanding))


def _box(raw, name, *, allow_zero_width=False):
    width = _number(raw.get("width"), f"{name}.width", positive=not allow_zero_width)
    if width < 0:
        raise _fail(f"ELK {name}.width must be nonnegative")
    return Box(_number(raw.get("x"), f"{name}.x"), _number(raw.get("y"), f"{name}.y"),
               width,
               _number(raw.get("height"), f"{name}.height", positive=True))


def _on_border(point, box, tolerance=0.5):
    return ((abs(point.x - box.x) <= tolerance or abs(point.x - box.x - box.width) <= tolerance)
            and box.y - tolerance <= point.y <= box.y + box.height + tolerance) or (
            (abs(point.y - box.y) <= tolerance or abs(point.y - box.y - box.height) <= tolerance)
            and box.x - tolerance <= point.x <= box.x + box.width + tolerance)


def _rectangle_attach(box, port, toward):
    """Clip along the endpoint's own orthogonal segment, not a center ray."""
    dx, dy = toward.x - port.x, toward.y - port.y
    if abs(dx) <= 1e-9 and abs(dy) <= 1e-9:
        return port
    if abs(dy) <= 1e-6:
        return Point(box.x if dx < 0 else box.x + box.width, port.y)
    if abs(dx) <= 1e-6:
        return Point(port.x, box.y if dy < 0 else box.y + box.height)
    if _on_border(port, box):
        return port
    candidates = []
    for x in (box.x,box.x+box.width):
        t=(x-port.x)/dx
        y=port.y+t*dy
        if -1e-7<=t<=1+1e-7 and box.y-1e-7<=y<=box.y+box.height+1e-7:
            candidates.append((t,Point(x,y)))
    for y in (box.y,box.y+box.height):
        t=(y-port.y)/dy
        x=port.x+t*dx
        if -1e-7<=t<=1+1e-7 and box.x-1e-7<=x<=box.x+box.width+1e-7:
            candidates.append((t,Point(x,y)))
    if candidates:return min(candidates,key=lambda item:item[0])[1]
    raise _fail("ELK group endpoint does not cross its painted frame")


def _outline_routes(diagram, routes, boxes, group_boxes, measured):
    shapes = {node.id: node.shape for node in diagram.nodes}
    result = []
    measurements = {item.id:item for item in measured}
    nodes = {node.id:node for node in diagram.nodes}
    for source, edge in zip(diagram.edges, routes):
        # Fixed source paints the first routed section; preserve every raw
        # section for inspection, without overwriting it with paint clipping.
        if edge.sections:
            section = edge.sections[0]
            points = list((section.start,*section.bends,section.end))
        else:
            points = [Point(boxes[identifier].x+boxes[identifier].width/2,
                            boxes[identifier].y+boxes[identifier].height/2)
                      for identifier in (source.source,source.target)]
            if points[0] == points[1]:
                # Source non-routing centre-to-centre self-loop degenerates;
                # retain the semantic edge without fabricating visible routing.
                result.append(replace(edge,paint_points=(points[0],)))
                continue
        for at_start, identifier in ((True, source.source), (False, source.target)):
            ordered = points if at_start else list(reversed(points))
            port = ordered[0]
            toward = next((point for point in ordered[1:] if point != port), None)
            if toward is None:
                raise _fail(f"Edge {edge.id!r} has no terminal direction")
            if identifier in group_boxes:
                box = group_boxes[identifier]
                if edge.sections:
                    attachment = port if _on_border(port, box) else _rectangle_attach(box, port, toward)
                else:
                    cx,cy=box.x+box.width/2,box.y+box.height/2
                    dx,dy=toward.x-cx,toward.y-cy
                    scale=min(box.width/2/abs(dx) if dx else math.inf,box.height/2/abs(dy) if dy else math.inf)
                    attachment=Point(cx+dx*scale,cy+dy*scale)
            else:
                from py_mermaid.geometry.shapes import shape_outline_intersection
                size = measurements[identifier]
                physical = boxes[identifier]
                ink_box = Box(physical.x+(physical.width-size.width)/2,
                              physical.y+(physical.height-size.height)/2,
                              size.width,size.height)
                attachment = shape_outline_intersection(
                    shapes[identifier], ink_box, port, toward, config=diagram.config,
                    metadata=nodes[identifier].metadata, outline=measurements[identifier].outline,
                )
                if not isinstance(attachment, Point) or not math.isfinite(attachment.x) or not math.isfinite(attachment.y):
                    raise _fail(f"No finite shape attachment for node {identifier!r}")
            points[0 if at_start else -1] = attachment
        result.append(replace(edge, paint_points=tuple(points)))
    return tuple(result)


def read_compound(result: Any, diagram: Flowchart, measured, measured_groups, measured_edge_labels, state: _State, version: str) -> FlowLayout:
    if not isinstance(result, Mapping):
        raise _fail("ELK did not return a compound graph")
    if result.get("id") != "root":
        raise _fail("ELK changed the root graph identity")
    width = _number(result.get("width"), "graph.width", positive=bool(state.element_ids))
    height = _number(result.get("height"), "graph.height", positive=bool(state.element_ids))
    if width < 0 or height < 0:
        raise _fail("ELK graph dimensions must be nonnegative")
    raw_elements, raw_edges, boxes = {}, {}, {}
    origins = {"root": Point(0.0, 0.0)}
    edge_owners = {}
    element_parents = {}

    def visit(container, origin):
        children = container.get("children", [])
        if not isinstance(children, list):
            raise _fail("ELK children must be a list")
        for raw in children:
            if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str) or raw["id"] in raw_elements:
                raise _fail("ELK returned invalid or duplicate compound element")
            identifier = raw["id"]
            local = _box(raw, "element")
            absolute = replace(local, x=local.x + origin.x, y=local.y + origin.y)
            raw_elements[identifier], boxes[identifier] = raw, absolute
            element_parents[identifier] = container["id"]
            origins[identifier] = Point(absolute.x, absolute.y)
            visit(raw, origins[identifier])
        contained = container.get("edges", [])
        if not isinstance(contained, list):
            raise _fail("ELK edges must be a list")
        for edge in contained:
            if not isinstance(edge, Mapping) or not isinstance(edge.get("id"), str) or edge["id"] in raw_edges:
                raise _fail("ELK returned invalid or duplicate compound edge")
            raw_edges[edge["id"]] = edge
            edge_owners[edge["id"]] = container["id"]

    visit(result, origins["root"])
    _index(list(raw_elements.values()), set(state.element_ids.values()), "elements")
    _index(list(raw_edges.values()), set(state.edge_ids.values()), "edges")
    for identifier, parent in state.parents.items():
        expected_parent = state.element_ids[parent] if parent is not None else "root"
        if element_parents[state.element_ids[identifier]] != expected_parent:
            raise _fail(f"ELK changed the parent group of element {identifier!r}")
    sizes = {item.id: item for item in measured}
    placed = []
    for node in diagram.nodes:
        box = boxes[state.element_ids[node.id]]
        size = sizes[node.id]
        owner = element_parents[state.element_ids[node.id]]
        expanded = owner in state.expanding_containers and state.algorithms[owner] in ('elk.box','elk.rectpacking')
        valid_size = (box.width+1e-7>=size.width and box.height+1e-7>=size.height) if expanded else (math.isclose(box.width,size.width,rel_tol=1e-9,abs_tol=1e-7) and math.isclose(box.height,size.height,rel_tol=1e-9,abs_tol=1e-7))
        if not valid_size:
            raise _fail(f"ELK changed fixed dimensions for node {node.id!r}")
        placed.append(PlacedNode(node.id, box))
    routes, placed_labels = [], []
    for edge in diagram.edges:
        identifier = state.edge_ids[edge.id]
        raw = raw_edges[identifier]
        source, target = edge.source, edge.target
        reversed_edge = edge.id in state.reversed_edges
        if reversed_edge:
            source, target = target, source
        if raw.get("sources") != [state.element_ids[source]] or raw.get("targets") != [state.element_ids[target]]:
            raise _fail(f"ELK changed endpoints of edge {edge.id!r}")
        owner = raw.get("container", edge_owners[identifier])
        if owner not in origins:
            raise _fail(f"ELK edge {edge.id!r} has an unknown coordinate container")
        offset = origins[owner]
        def translate(value, name):
            point = _point(value, name)
            return Point(point.x + offset.x, point.y + offset.y)
        sections = raw.get("sections")
        if sections is None and state.algorithms.get(owner) != 'elk.layered':
            sections = []
        if not isinstance(sections, list) or (not sections and state.algorithms.get(owner) == 'elk.layered'):
            raise _fail(f"ELK returned no route sections for edge {edge.id!r}")
        converted = []
        for section in sections:
            if not isinstance(section, Mapping) or not isinstance(section.get("bendPoints", []), list):
                raise _fail(f"ELK returned an invalid section for edge {edge.id!r}")
            converted.append(EdgeSection(translate(section.get("startPoint"), "section.startPoint"),
                                        tuple(translate(point, "section.bendPoint") for point in section.get("bendPoints", [])),
                                        translate(section.get("endPoint"), "section.endPoint")))
        if reversed_edge:
            converted = [EdgeSection(section.end, tuple(reversed(section.bends)), section.start) for section in reversed(converted)]
        routes.append(RoutedEdge(edge.id, tuple(converted), effective_curve='rounded' if converted else 'linear'))
        if edge.label:
            expected_id = f"label-{identifier}"
            labels = _index(raw.get("labels"), {expected_id}, "edge labels")
            raw_label = labels[expected_id]
            if not converted:
                raw_label = dict(raw_label, x=raw_label.get('x',0), y=raw_label.get('y',0))
            local = _box(raw_label, "edge label", allow_zero_width=True)
            expected = next(item for item in measured_edge_labels if item.id == edge.id)
            if not math.isclose(local.width, expected.width, abs_tol=1e-7) or not math.isclose(local.height, expected.height, abs_tol=1e-7):
                raise _fail(f"ELK changed measured label dimensions of edge {edge.id!r}")
            placed_labels.append(PlacedEdgeLabel(edge.id, replace(local, x=local.x + offset.x, y=local.y + offset.y)))
    semantic_boxes = {identifier: boxes[engine_id] for identifier, engine_id in state.element_ids.items()}
    frames = {group.id: semantic_boxes[group.id] for group in diagram.groups}
    group_sizes = {item.id: item for item in measured_groups}
    for group in diagram.groups:
        if frames[group.id].width + 1e-7 < group_sizes[group.id].label_width + diagram.config.group_padding:
            raise _fail(f"ELK did not honor the measured title width constraint for group {group.id!r}")
    def descendant(identifier, group):
        current = state.parents[identifier]
        while current is not None:
            if current == group:
                return True
            current = state.parents[current]
        return False
    def depth(identifier):
        count = 0
        while state.parents[identifier] is not None:
            count += 1
            identifier = state.parents[identifier]
        return count
    # Source evenGroupFrames is a deepest-first paint-frame pass; route offsets
    # remain tied to the original immutable origins above.
    for group in sorted(diagram.groups, key=lambda g: depth(g.id), reverse=True):
        child_boxes = [frames.get(identifier, semantic_boxes[identifier]) for identifier, parent in state.parents.items() if parent == group.id]
        if not child_boxes:
            continue
        points = []
        for source, route in zip(diagram.edges, routes):
            internal = descendant(source.source, group.id) and descendant(source.target, group.id)
            for section in route.sections:
                if internal:
                    points.extend((section.start, *section.bends, section.end))
                else:
                    if source.source == group.id:
                        points.append(section.start)
                    if source.target == group.id:
                        points.append(section.end)
        xs = [value for box in child_boxes for value in (box.x, box.x + box.width)] + [point.x for point in points]
        ys = [value for box in child_boxes for value in (box.y, box.y + box.height)] + [point.y for point in points]
        original = frames[group.id]
        left = max(original.x, min(xs) - _SUBGRAPH_PADDING)
        right = min(original.x + original.width, max(xs) + _SUBGRAPH_PADDING)
        bottom = min(original.y + original.height, max(ys) + _SUBGRAPH_PADDING)
        title_floor = group_sizes[group.id].label_width + diagram.config.group_padding
        frame_width = right - left
        if frame_width < title_floor:
            left = max(original.x, min(left - (title_floor - frame_width) / 2, original.x + original.width - title_floor))
            frame_width = min(title_floor, original.width)
        if frame_width > 0 and bottom > original.y:
            frames[group.id] = Box(left, original.y, frame_width, bottom - original.y)
    placed_groups = []
    from py_mermaid.geometry.edges.alignment import align_degenerate_boxes
    semantic_edge_ids = {engine:semantic for semantic,engine in state.edge_ids.items()}
    # Fixed applyElkEdgeLayout aligns before any edge paint clipping, in the
    # native graph.edges order. A first anchor must affect every later route.
    native_edge_order = [semantic_edge_ids[edge['id']] for edge in result.get('edges',[])]
    paint_boxes = align_degenerate_boxes(diagram,routes,{**semantic_boxes,**frames},native_edge_order)
    placed = [replace(node,paint_box=paint_boxes.get(node.id)) for node in placed]
    paint_groups = {identifier:paint_boxes.get(identifier,frame) for identifier,frame in frames.items()}
    for group in diagram.groups:
        frame = frames[group.id]
        paint_frame = paint_groups[group.id]
        size = group_sizes[group.id]
        title = Box(paint_frame.x + (paint_frame.width - size.label_width) / 2,
                    paint_frame.y + diagram.config.group_title_top_margin,
                    size.label_width, size.label_height)
        placed_groups.append(PlacedGroup(group.id, frame, group.parent_id, origins[state.element_ids[group.id]], title,
                                        paint_box=paint_boxes.get(group.id)))
    routes = _outline_routes(diagram, routes, {**semantic_boxes,**paint_boxes}, paint_groups, measured)
    route_by_id = {route.id:route for route in routes}
    for index,label in enumerate(placed_labels):
        route = route_by_id[label.id]
        if not route.sections:
            a,b=route.paint_points[0],route.paint_points[-1]
            placed_labels[index]=replace(label,box=replace(label.box,x=(a.x+b.x-label.box.width)/2,y=(a.y+b.y-label.box.height)/2))
    return FlowLayout(tuple(placed), routes, width, height, 'pyelk/'+algorithm(diagram.config), version,
                      tuple(placed_groups), tuple(placed_labels))
