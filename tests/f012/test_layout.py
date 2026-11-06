"""Source-derived F01.2 layout assertions; no implementation-coordinate goldens.

Primary acceptance uses real Canvas measurement and real pyelk. Synthetic raw
outputs are explicitly test-only controls for JSON container coordinate frames.
Expected relations come from fixed Mermaid group/label/shape geometry and the
public ELK JSON contract, not candidate private helpers.
"""
from __future__ import annotations

import copy
from dataclasses import replace
import math
import sys
import types
import unittest
from unittest.mock import patch

from py_mermaid.config import resolve_config
from py_mermaid.geometry import geometry_bounds
from py_mermaid.layout.elk import layout_flowchart
from py_mermaid.model.flowchart import (
    Box, Flowchart, FlowEdge, FlowGroup, FlowNode, MeasuredEdgeLabel,
    MeasuredGroup, MeasuredNode, MermaidError, Point, SourcePosition, SourceSpan,
)
from py_mermaid.rendering.skia import CanvasSession

SHAPES = ("square", "round", "stadium", "subroutine", "cylinder", "circle",
          "doublecircle", "diamond", "hexagon", "odd", "trapezoid",
          "inv_trapezoid", "lean_right", "lean_left")


def chart(nodes=(), edges=(), groups=(), direction="TD"):
    """Public semantic fixtures isolate layout from parser source coverage."""
    p = SourcePosition(0, 0, 1, 0)
    span = SourceSpan(p, p)
    return Flowchart(
        "test-only semantic fixture", direction,
        tuple(FlowNode(identifier, "节点 " + identifier, span, shape, parent) for identifier, shape, parent in nodes),
        tuple(FlowEdge(f"edge-{index}", source, target, span, text, span) for index, (source, target, text) in enumerate(edges)),
        resolve_config(), groups=tuple(FlowGroup(identifier, "组 " + identifier, span, members, parent, local_direction, index)
                                       for index, (identifier, members, parent, local_direction) in enumerate(groups)),
    )


def points(section):
    return (section.start, *section.bends, section.end)


def overlaps(a, b, epsilon=1e-5):
    return min(a.x+a.width, b.x+b.width)-max(a.x, b.x) > epsilon and min(a.y+a.height, b.y+b.height)-max(a.y, b.y) > epsilon


def segment_distance(p, a, b):
    dx, dy = b.x-a.x, b.y-a.y
    denominator = dx*dx+dy*dy
    t = 0 if denominator == 0 else max(0, min(1, ((p.x-a.x)*dx+(p.y-a.y)*dy)/denominator))
    return math.hypot(p.x-a.x-t*dx, p.y-a.y-t*dy)


def outline_distance(kind, box, point):
    """Independent analytical outline, translated from upstream shape handlers.

    Stadium's source uses a 50-point sampled semicircle; ideal-arc distance is
    accepted within 0.25px, above its bounded polygon sampling deviation.
    """
    x, y, w, h = point.x-box.x, point.y-box.y, box.width, box.height
    if kind in ("circle", "doublecircle"):
        return abs(math.hypot(x-w/2, y-h/2)-w/2)
    if kind == "round":
        radius = min(12, w/2, h/2)
        cx, cy = min(max(x, radius), w-radius), min(max(y, radius), h-radius)
        return abs(math.hypot(x-cx, y-cy)-radius)
    if kind == "stadium":
        radius = h/2
        cx = min(max(x, radius), w-radius)
        return abs(math.hypot(x-cx, y-radius)-radius)
    if kind == "cylinder":
        rx, ry = w/2, (w/2)/(2.5+w/50)
        if ry <= y <= h-ry:
            return min(abs(x), abs(x-w))
        cy = ry if y < ry else h-ry
        # Residual scaled to logical px; zero describes the outer ellipse.
        return abs(((x-rx)/rx)**2+((y-cy)/ry)**2-1)*max(rx, ry)
    vertices = {
        "square": ((0, 0), (w, 0), (w, h), (0, h)),
        "subroutine": ((0, 0), (w, 0), (w, h), (0, h)),
        "diamond": ((w/2, 0), (w, h/2), (w/2, h), (0, h/2)),
        "hexagon": ((h/3.5, 0), (w-h/3.5, 0), (w, h/2), (w-h/3.5, h), (h/3.5, h), (0, h/2)),
        "odd": ((0, 0), (w, 0), (w, h), (0, h), (h/4, h/2)),
        "trapezoid": ((h/2, 0), (w-h/2, 0), (w, h), (0, h)),
        "inv_trapezoid": ((0, 0), (w, 0), (w-h/2, h), (h/2, h)),
        "lean_right": ((h/2, 0), (w, 0), (w-h/2, h), (0, h)),
        "lean_left": ((0, 0), (w-h/2, 0), (w, h), (h/2, h)),
    }[kind]
    vertices = tuple(Point(a, b) for a, b in vertices)
    return min(segment_distance(Point(x, y), a, b) for a, b in zip(vertices, (*vertices[1:], vertices[0])))


class LayoutRelations(unittest.TestCase):
    def assert_contains(self, outer, inner, message=""):
        tolerance = 1e-5
        self.assertGreaterEqual(inner.x, outer.x-tolerance, message)
        self.assertGreaterEqual(inner.y, outer.y-tolerance, message)
        self.assertLessEqual(inner.x+inner.width, outer.x+outer.width+tolerance, message)
        self.assertLessEqual(inner.y+inner.height, outer.y+outer.height+tolerance, message)

    def assert_quality(self, diagram, measured, annotations, layout):
        self.assertEqual(tuple(n.id for n in layout.nodes), tuple(n.id for n in diagram.nodes))
        self.assertEqual(tuple(g.id for g in layout.groups), tuple(g.id for g in diagram.groups))
        self.assertEqual(tuple(e.id for e in layout.edges), tuple(e.id for e in diagram.edges))
        self.assertEqual(tuple(e.id for e in layout.edge_labels), tuple(e.id for e in diagram.edges if e.label))
        self.assertEqual(layout.engine_version, "0.1.0")
        viewport = Box(0, 0, layout.width, layout.height)
        boxes = {node.id: node.box for node in layout.nodes}
        group_boxes = {group.id: group.box for group in layout.groups}
        all_boxes = {**boxes, **group_boxes}
        sizes = {node.id: node for node in measured}
        for node in diagram.nodes:
            self.assert_contains(viewport, boxes[node.id], node.id)
            self.assertAlmostEqual(boxes[node.id].width, sizes[node.id].width)
            self.assertAlmostEqual(boxes[node.id].height, sizes[node.id].height)
            if node.parent_id:
                self.assert_contains(group_boxes[node.parent_id], boxes[node.id], node.id)
        for source, placed in zip(diagram.groups, layout.groups):
            self.assertEqual(placed.parent_id, source.parent_id)
            self.assertIsNotNone(placed.engine_origin)
            self.assertIsNotNone(placed.title_box)
            self.assert_contains(viewport, placed.box, source.id)
            self.assert_contains(placed.box, placed.title_box, source.id+" title")
            if source.parent_id:
                self.assert_contains(group_boxes[source.parent_id], placed.box, source.id)
            for node in diagram.nodes:
                if node.parent_id == source.id:
                    self.assertFalse(overlaps(placed.title_box, boxes[node.id]), (source.id, node.id, "title covers child"))
        for i, a in enumerate(diagram.nodes):
            for b in diagram.nodes[i+1:]:
                self.assertFalse(overlaps(boxes[a.id], boxes[b.id]), (a.id, b.id, "leaf overlap"))
        for i, a in enumerate(diagram.groups):
            for b in diagram.groups[i+1:]:
                if a.parent_id == b.parent_id:
                    self.assertFalse(overlaps(group_boxes[a.id], group_boxes[b.id]), (a.id, b.id, "sibling group overlap"))
        for label, expected in zip(layout.edge_labels, annotations.edge_labels):
            self.assertAlmostEqual(label.box.width, expected.width)
            self.assertAlmostEqual(label.box.height, expected.height)
            self.assert_contains(viewport, label.box, label.id)
            for node_id, box in boxes.items():
                self.assertFalse(overlaps(label.box, box), (label.id, node_id, "edge label covers node"))
            for group in layout.groups:
                self.assertFalse(overlaps(label.box, group.title_box), (label.id, group.id, "edge label covers title"))
        for i, a in enumerate(layout.edge_labels):
            for b in layout.edge_labels[i+1:]:
                self.assertFalse(overlaps(a.box, b.box), (a.id, b.id, "edge labels overlap"))
        shape_by_id = {node.id: node.shape for node in diagram.nodes}
        for semantic, routed in zip(diagram.edges, layout.edges):
            self.assertTrue(routed.sections, semantic.id)
            length = 0
            for section in routed.sections:
                for point in points(section):
                    self.assertTrue(math.isfinite(point.x) and math.isfinite(point.y))
                    self.assert_contains(viewport, Box(point.x, point.y, 0, 0), semantic.id)
                for a, b in zip(points(section), points(section)[1:]):
                    self.assertTrue(abs(a.x-b.x) < 1e-5 or abs(a.y-b.y) < 1e-5, (semantic.id, "diagonal introduced"))
                    length += math.hypot(a.x-b.x, a.y-b.y)
            self.assertGreater(length, 0)
            # F014 retains raw engine sections. Visible terminals belong to
            # the separate outline-clipped paint route, preserving this same
            # independent shape-boundary acceptance requirement.
            self.assertTrue(routed.paint_points, semantic.id)
            for identifier, point in ((semantic.source, routed.paint_points[0]), (semantic.target, routed.paint_points[-1])):
                kind = shape_by_id.get(identifier, "square")
                self.assertLessEqual(outline_distance(kind, all_boxes[identifier], point), 0.25, (identifier, point, "endpoint off outline"))
        bounds = geometry_bounds(layout)
        for box in all_boxes.values():
            self.assert_contains(bounds, box)
        for label in layout.edge_labels:
            self.assert_contains(bounds, label.box)


class RealCompoundTests(unittest.IsolatedAsyncioTestCase, LayoutRelations):
    async def layout(self, diagram):
        before = copy.deepcopy(diagram)
        session = CanvasSession("cpu")
        measured = session.measure(diagram)
        annotations = session.measure_annotations(diagram)
        before_measurements = copy.deepcopy((measured, annotations))
        result = await layout_flowchart(diagram, measured, measured_groups=annotations.groups,
                                        measured_edge_labels=annotations.edge_labels)
        self.assertEqual(diagram, before)
        self.assertEqual((measured, annotations), before_measurements)
        self.assert_quality(diagram, measured, annotations, result)
        return result

    async def test_l01_real_unicode_multiline_edge_label(self):
        for direction in ("TD", "LR"):
            with self.subTest(direction=direction):
                diagram = chart((("a", "square", None), ("b", "square", None)), (("a", "b", "条件\n继续 ✓"),), direction=direction)
                result = await self.layout(diagram)
                self.assertEqual(len(result.edge_labels), 1)

    async def test_l02_real_all_classic_shape_endpoints(self):
        # A two-in/two-out graph places ports away from a common center ray.
        for shape in SHAPES:
            for direction in ("TD", "LR"):
                with self.subTest(shape=shape, direction=direction):
                    nodes = (("a", "square", None), ("b", "square", None), ("c", shape, None), ("d", "square", None), ("e", "square", None))
                    edges = (("a", "c", ""), ("b", "c", ""), ("c", "d", ""), ("c", "e", ""))
                    await self.layout(chart(nodes, edges, direction=direction))

    async def test_l03_real_empty_group_and_only_groups(self):
        await self.layout(chart(groups=(("empty", (), None, None),)))
        await self.layout(chart(groups=(("inner", (), "outer", None), ("outer", ("inner",), None, None))))

    async def test_l04_real_nested_parent_local_coordinates(self):
        nodes = (("a", "square", "inner"), ("b", "circle", "inner"), ("c", "square", "outer"))
        groups = (("inner", ("a", "b"), "outer", None), ("outer", ("inner", "c"), None, None))
        await self.layout(chart(nodes, (("a", "b", "inner"), ("b", "c", "cross nesting")), groups))

    async def test_l05_real_group_local_directions(self):
        for direction in ("TD", "TB", "LR", "RL", "BT"):
            with self.subTest(group_direction=direction):
                nodes = (("a", "square", "g"), ("b", "square", "g"))
                groups = (("g", ("a", "b"), None, direction),)
                result = await self.layout(chart(nodes, (("a", "b", ""),), groups))
                a, b = (item.box for item in result.nodes)
                if direction in ("TD", "TB"):
                    self.assertLessEqual(a.y+a.height, b.y+1e-5)
                elif direction == "BT":
                    self.assertLessEqual(b.y+b.height, a.y+1e-5)
                elif direction == "LR":
                    self.assertLessEqual(a.x+a.width, b.x+1e-5)
                else:
                    self.assertLessEqual(b.x+b.width, a.x+1e-5)

    async def test_l06_real_sibling_cross_group_labels(self):
        nodes = (("a", "diamond", "left"), ("b", "square", "left"), ("c", "round", "right"), ("d", "square", "right"))
        groups = (("left", ("a", "b"), None, "TD"), ("right", ("c", "d"), None, "LR"))
        edges = (("a", "b", "内部"), ("c", "d", ""), ("b", "c", "跨组"))
        await self.layout(chart(nodes, edges, groups, "LR"))

    async def test_l07_real_group_inside_outside_connections(self):
        nodes = (("a", "square", "g"), ("b", "hexagon", "g"), ("outside", "square", None))
        groups = (("g", ("a", "b"), None, "LR"),)
        await self.layout(chart(nodes, (("a", "b", ""), ("b", "outside", "出"), ("outside", "a", "入")), groups))

    async def test_l08_real_group_node_and_group_group_endpoints(self):
        nodes = (("a", "square", "left"), ("b", "square", "right"), ("outside", "square", None))
        groups = (("left", ("a",), None, None), ("right", ("b",), None, None))
        await self.layout(chart(nodes, (("outside", "left", "to frame"), ("left", "right", "frames"), ("right", "outside", "from frame")), groups))

    async def test_l09_real_ancestor_group_endpoints(self):
        nodes = (("a", "square", "inner"),)
        groups = (("inner", ("a",), "outer", None), ("outer", ("inner",), None, None))
        for source, target in (("outer", "a"), ("a", "outer"), ("outer", "inner"), ("inner", "outer")):
            with self.subTest(source=source, target=target):
                await self.layout(chart(nodes, ((source, target, "ancestor"),), groups))

    async def test_l10_real_collapsed_subgraph_feedback_restores_semantics(self):
        nodes = (("a", "square", "g"), ("b", "square", "g"), ("c", "square", "g"), ("x", "square", None))
        groups = (("g", ("a", "b", "c"), None, None),)
        await self.layout(chart(nodes, (("a", "b", ""), ("b", "x", "out"), ("x", "c", "return")), groups))

    async def test_l11_real_labeled_multiedges_self_loop_and_repeat_isolation(self):
        nodes = (("a", "circle", "g"), ("b", "square", "g"))
        groups = (("g", ("a", "b"), None, None),)
        diagram = chart(nodes, (("a", "b", "first"), ("a", "b", "second"), ("b", "b", "loop")), groups)
        await self.layout(diagram)
        fresh = await self.layout(chart(groups=(("fresh", (), None, None),)))
        self.assertEqual(tuple(g.id for g in fresh.groups), ("fresh",))
        self.assertEqual(fresh.edges, ())
        self.assertEqual(fresh.edge_labels, ())

    async def test_l12_real_empty_group_edges_and_group_self_loop(self):
        groups = (("left", (), None, None), ("right", (), None, None))
        await self.layout(chart(edges=(("left", "right", "empty frames"),), groups=groups))
        await self.layout(chart(edges=(("left", "left", "frame loop"),), groups=(("left", (), None, None),)))

    async def test_l13_real_title_width_floor_and_internal_long_label(self):
        diagram = chart((("a", "circle", "g"), ("b", "circle", "g")),
                        (("a", "b", "实际测量的长边标签 with wrapping into multiple lines and Unicode 内容"),),
                        (("g", ("a", "b"), None, None),))
        title = "A group title wider than a small circle child 组标题"
        diagram = replace(diagram, groups=(replace(diagram.groups[0], label=title),))
        await self.layout(diagram)

    async def test_l14_long_title_floor_five_separate_group_directions(self):
        for direction in ("TD", "TB", "LR", "RL", "BT"):
            with self.subTest(group_direction=direction):
                diagram = chart((("a", "circle", "g"), ("b", "circle", "g")),
                                (("a", "b", ""),), (("g", ("a", "b"), None, direction),))
                diagram = replace(diagram, groups=(replace(diagram.groups[0], label="Wide isolated direction title "*3),))
                await self.layout(diagram)

    async def test_l15_long_title_floor_five_cross_boundary_group_directions(self):
        for direction in ("TD", "TB", "LR", "RL", "BT"):
            with self.subTest(group_direction=direction):
                diagram = chart((("a", "circle", "g"), ("b", "circle", "g"), ("outside", "square", None)),
                                (("a", "b", ""), ("b", "outside", "cross")),
                                (("g", ("a", "b"), None, direction),))
                diagram = replace(diagram, groups=(replace(diagram.groups[0], label="Wide compound direction title "*3),))
                await self.layout(diagram)

    async def test_l16_nested_long_title_with_inherited_and_separate_directions(self):
        for root_direction in ("TD", "LR"):
            for outer_direction in (None, "TD", "LR", "RL", "BT"):
                with self.subTest(root_direction=root_direction, outer_direction=outer_direction):
                    diagram = chart((("a", "circle", "inner"), ("b", "circle", "inner")),
                                    (("a", "b", ""),),
                                    (("inner", ("a", "b"), "outer", None), ("outer", ("inner",), None, outer_direction)),
                                    root_direction)
                    diagram = replace(diagram, groups=(replace(diagram.groups[0], label="Nested measured title "*3), diagram.groups[1]))
                    await self.layout(diagram)


class CompoundBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def fixture(self):
        diagram = chart((("a", "square", "g"), ("b", "square", "g")), (("a", "b", "label"),), (("g", ("a", "b"), None, None),))
        measured = tuple(MeasuredNode(identifier, 80, 40, 30, 16, ()) for identifier in ("a", "b"))
        groups = (MeasuredGroup("g", 40, 12, ()),)
        labels = (MeasuredEdgeLabel("edge-0", 20, 10, ()),)
        return diagram, measured, groups, labels

    def module(self, mutate=None):
        module = types.ModuleType("pyelk")
        module.__version__ = "0.1.0"
        calls = []
        class Engine:
            def __enter__(self):
                calls.append("enter")
                return self
            def __exit__(self, *args):
                calls.append("close")
            async def layout(self, graph):
                calls.append(copy.deepcopy(graph))
                # Test-only independent public JSON contract specimen. Its
                # container origin differs from the tightened paint frame.
                result = {"id": "root", "width": 400, "height": 300,
                          "children": [{"id": "g0", "x": 20, "y": 30, "width": 300, "height": 200,
                                        "children": [{"id": "n0", "x": 50, "y": 60, "width": 80, "height": 40},
                                                     {"id": "n1", "x": 160, "y": 60, "width": 80, "height": 40}]}],
                          "edges": [{"id": "e0", "sources": ["n0"], "targets": ["n1"], "container": "g0",
                                     "sections": [{"startPoint": {"x": 130, "y": 80}, "endPoint": {"x": 160, "y": 80}}],
                                     "labels": [{"id": "label-e0", "x": 135, "y": 75, "width": 20, "height": 10}]}]}
                return mutate(result) if mutate else result
        module.ELK = Engine
        return module, calls

    async def test_c01_container_translation_keeps_engine_origin_after_frame_shrink(self):
        diagram, nodes, groups, labels = self.fixture()
        module, calls = self.module()
        with patch.dict(sys.modules, {"pyelk": module}):
            result = await layout_flowchart(diagram, nodes, measured_groups=groups, measured_edge_labels=labels)
        self.assertEqual(result.nodes[0].box, Box(70, 90, 80, 40))
        self.assertEqual(result.nodes[1].box, Box(180, 90, 80, 40))
        self.assertEqual(result.groups[0].engine_origin, Point(20, 30))
        self.assertGreater(result.groups[0].box.x, 20, "controlled fixture tightens frame while engine origin stays fixed")
        self.assertEqual(result.edges[0].sections[0].start, Point(150, 110))
        self.assertEqual(result.edges[0].sections[0].end, Point(180, 110))
        self.assertEqual(result.edge_labels[0].box, Box(155, 105, 20, 10))
        self.assertEqual(calls[-1], "close")

    async def test_c02_measurement_parent_and_endpoint_faults_before_engine(self):
        diagram, nodes, groups, labels = self.fixture()
        variants = [
            (diagram, nodes, (), labels), (diagram, nodes, groups*2, labels),
            (diagram, nodes, groups, ()), (diagram, nodes, groups, labels*2),
            (diagram, nodes, (replace(groups[0], id="wrong"),), labels),
            (diagram, nodes, (replace(groups[0], label_width=math.nan),), labels),
            # F01.3 rich labels can legitimately measure zero width after
            # sanitation or for <br>. Negative width remains invalid.
            (diagram, nodes, groups, (replace(labels[0], width=-1),)),
            (diagram, nodes, groups, (replace(labels[0], height=math.inf),)),
            (replace(diagram, nodes=(replace(diagram.nodes[0], parent_id="missing"), diagram.nodes[1])), nodes, groups, labels),
            (replace(diagram, groups=(replace(diagram.groups[0], parent_id="g"),)), nodes, groups, labels),
            (replace(diagram, groups=(replace(diagram.groups[0], members=("missing",)),)), nodes, groups, labels),
            (replace(diagram, edges=(replace(diagram.edges[0], target="missing"),)), nodes, groups, labels),
            (replace(diagram, groups=(replace(diagram.groups[0], id="a"),)), nodes, groups, labels),
        ]
        for index, (bad, measured, group_sizes, label_sizes) in enumerate(variants):
            module, calls = self.module()
            with self.subTest(fault=index), patch.dict(sys.modules, {"pyelk": module}):
                with self.assertRaises(MermaidError) as raised:
                    await layout_flowchart(bad, measured, measured_groups=group_sizes, measured_edge_labels=label_sizes)
                self.assertEqual(raised.exception.code, "INVALID_LAYOUT_INPUT")
                self.assertEqual(calls, [])

    async def test_c03_bad_container_parent_and_label_outputs_fail(self):
        diagram, nodes, groups, labels = self.fixture()
        def edit(path, value):
            def mutate(result):
                target = result
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                return result
            return mutate
        variants = [edit(("id",), "wrong-root"), edit(("edges", 0, "container"), "missing"),
                    edit(("edges", 0, "labels"), []), edit(("edges", 0, "labels", 0, "width"), 21),
                    edit(("edges", 0, "labels", 0, "x"), math.nan), edit(("children", 0, "children", 1, "id"), "n0"),
                    edit(("children", 0, "children"), []), edit(("children", 0, "width"), 0),
                    edit(("children", 0, "width"), 39)]
        def changed_parent(result):
            node = result["children"][0]["children"].pop(0)
            result["children"].append(node)
            return result
        variants.append(changed_parent)
        for index, mutate in enumerate(variants):
            module, calls = self.module(mutate)
            with self.subTest(fault=index), patch.dict(sys.modules, {"pyelk": module}):
                with self.assertRaises(MermaidError) as raised:
                    await layout_flowchart(diagram, nodes, measured_groups=groups, measured_edge_labels=labels)
                self.assertEqual(raised.exception.code, "INVALID_ELK_RESULT")
                self.assertEqual(calls[-1], "close")


if __name__ == "__main__":
    unittest.main()
