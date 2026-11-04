"""F01.1 source-derived geometry/layout assertions, authored before first run.

Sources: Mermaid elk/render.ts:createRootElkGraph/default preset,
defaultConfig.ts:config.elk, elk/geometry.ts:onBorder; pyelk 0.1.0
API_COMPATIBILITY.md (fixed dimensions, async lifecycle, preserved input).
No Python candidate output is used as a golden. Controlled coordinates below
are explicitly test-only geometry / corrupt-engine fixtures.
"""
from __future__ import annotations

import asyncio
import copy
from dataclasses import replace
import math
import sys
import types
import unittest
from unittest.mock import patch

from py_mermaid.geometry import arrow_polygon, edge_points, geometry_bounds
from py_mermaid.layout.elk import layout_flowchart
from py_mermaid.model.flowchart import (
    Box, EdgeSection, FlowConfig, FlowEdge, Flowchart, FlowLayout, FlowNode,
    MeasuredNode, MermaidError, PlacedNode, Point, RoutedEdge,
    SourcePosition, SourceSpan,
)


def specimen(ids=("a", "b"), connections=(("a", "b"),), direction="TD"):
    """Independent pure-value input, not parser output or recorded layout."""
    position = SourcePosition(0, 0, 1, 0)
    span = SourceSpan(position, position)
    config = FlowConfig(
        font_family="sans-serif", font_size=16, node_padding=15,
        diagram_padding=8, node_spacing=50, rank_spacing=50,
        fill="#ECECFF", stroke="#9370DB", text_color="#333",
        edge_color="#333333", background="white", line_height=1.5,
        html_labels=True, max_text_size=50000, max_edges=500,
    )
    chart = Flowchart(
        "test-only semantic fixture", direction,
        tuple(FlowNode(identifier, identifier, span) for identifier in ids),
        tuple(FlowEdge(f"edge-{i}", source, target, span) for i, (source, target) in enumerate(connections)),
        config,
    )
    measured = tuple(MeasuredNode(identifier, 80.0, 40.0, 30.0, 16.0, ()) for identifier in ids)
    return chart, measured


class GeometryTests(unittest.TestCase):
    def test_g01_section_order_and_bends_are_lossless(self):
        section = EdgeSection(Point(1, 2), (Point(1, 8), Point(9, 8)), Point(9, 10))
        self.assertEqual(edge_points(section), (Point(1, 2), Point(1, 8), Point(9, 8), Point(9, 10)))

    def test_g02_arrow_tip_base_width_and_orientation(self):
        for start, tip in ((Point(0, 0), Point(30, 0)), (Point(0, 30), Point(0, 0)), (Point(0, 0), Point(30, 40))):
            with self.subTest(tip=tip):
                arrow = arrow_polygon((start, tip, tip), length=10, width=8)
                self.assertEqual(arrow[0], tip)
                left, right = arrow[1:]
                base = Point((left.x + right.x) / 2, (left.y + right.y) / 2)
                self.assertAlmostEqual(math.hypot(tip.x - base.x, tip.y - base.y), 10)
                self.assertAlmostEqual(math.hypot(left.x - right.x, left.y - right.y), 8)
                dx, dy = tip.x - start.x, tip.y - start.y
                self.assertGreater((tip.x - base.x) * dx + (tip.y - base.y) * dy, 0)
                self.assertAlmostEqual((left.x - right.x) * dx + (left.y - right.y) * dy, 0)

    def test_g03_arrow_rejects_degenerate_paths_and_sizes(self):
        for points in ((), (Point(0, 0),), (Point(0, 0), Point(0, 0))):
            with self.subTest(points=points), self.assertRaises(ValueError):
                arrow_polygon(points)
        for length, width in ((0, 7), (-1, 7), (10, 0), (math.inf, 7), (10, math.nan)):
            with self.subTest(length=length, width=width), self.assertRaises(ValueError):
                arrow_polygon((Point(0, 0), Point(20, 0)), length=length, width=width)

    def test_g04_bounds_include_route_nodes_graph_and_margin(self):
        layout = FlowLayout(
            (PlacedNode("a", Box(-10, -5, 20, 20)),),
            (RoutedEdge("e", (EdgeSection(Point(10, 10), (Point(140, 90),), Point(20, 20)),)),),
            100, 70, "test-only", "fixture",
        )
        self.assertEqual(geometry_bounds(layout, margin=2), Box(-12, -7, 154, 99))
        for margin in (-1, math.inf, math.nan):
            with self.subTest(margin=margin), self.assertRaises(ValueError):
                geometry_bounds(layout, margin=margin)


class RealElkTests(unittest.IsolatedAsyncioTestCase):
    """Real engine relations; never assert cross-version coordinate identity."""

    def assert_border(self, point, box):
        tolerance = 1e-5
        inside_x = box.x - tolerance <= point.x <= box.x + box.width + tolerance
        inside_y = box.y - tolerance <= point.y <= box.y + box.height + tolerance
        border_x = min(abs(point.x - box.x), abs(point.x - box.x - box.width)) <= tolerance
        border_y = min(abs(point.y - box.y), abs(point.y - box.y - box.height)) <= tolerance
        self.assertTrue(inside_x and inside_y and (border_x or border_y), (point, box))

    def assert_quality(self, chart, measured, result, *, forward=True):
        self.assertEqual(tuple(n.id for n in result.nodes), tuple(n.id for n in chart.nodes))
        self.assertEqual(tuple(e.id for e in result.edges), tuple(e.id for e in chart.edges))
        self.assertEqual(result.engine_version, "0.1.0")
        self.assertIn("pyelk", result.engine)
        self.assertTrue(math.isfinite(result.width) and result.width > 0)
        self.assertTrue(math.isfinite(result.height) and result.height > 0)
        boxes = {node.id: node.box for node in result.nodes}
        for node, size in zip(result.nodes, measured):
            self.assertAlmostEqual(node.box.width, size.width)
            self.assertAlmostEqual(node.box.height, size.height)
            self.assertGreaterEqual(node.box.x, -1e-5)
            self.assertGreaterEqual(node.box.y, -1e-5)
            self.assertLessEqual(node.box.x + node.box.width, result.width + 1e-5)
            self.assertLessEqual(node.box.y + node.box.height, result.height + 1e-5)
        for i, left in enumerate(result.nodes):
            for right in result.nodes[i + 1:]:
                a, b = left.box, right.box
                overlap_x = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
                overlap_y = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
                self.assertFalse(overlap_x > 1e-5 and overlap_y > 1e-5, (left, right))
        for source, route in zip(chart.edges, result.edges):
            self.assertTrue(route.sections)
            self.assert_border(route.sections[0].start, boxes[source.source])
            self.assert_border(route.sections[-1].end, boxes[source.target])
            total_length = 0
            for section in route.sections:
                points = edge_points(section)
                for point in points:
                    self.assertTrue(math.isfinite(point.x) and math.isfinite(point.y))
                    self.assertGreaterEqual(point.x, -1e-5)
                    self.assertGreaterEqual(point.y, -1e-5)
                    self.assertLessEqual(point.x, result.width + 1e-5)
                    self.assertLessEqual(point.y, result.height + 1e-5)
                for start, end in zip(points, points[1:]):
                    dx, dy = end.x - start.x, end.y - start.y
                    self.assertTrue(abs(dx) <= 1e-5 or abs(dy) <= 1e-5, "ORTHOGONAL route")
                    total_length += math.hypot(dx, dy)
            self.assertGreater(total_length, 0)
            if forward and source.source != source.target:
                a, b = boxes[source.source], boxes[source.target]
                if chart.direction == "TD":
                    self.assertLessEqual(a.y + a.height, b.y + 1e-5)
                else:
                    self.assertLessEqual(a.x + a.width, b.x + 1e-5)

    async def check(self, ids, connections, direction="TD", *, forward=True):
        chart, measured = specimen(ids, connections, direction)
        result = await layout_flowchart(chart, measured)
        self.assert_quality(chart, measured, result, forward=forward)
        return result

    async def test_l01_real_single_node(self):
        await self.check(("alone",), ())

    async def test_l02_real_td_chain(self):
        await self.check(("a", "b", "c"), (("a", "b"), ("b", "c")))

    async def test_l03_real_lr_chain(self):
        await self.check(("a", "b", "c"), (("a", "b"), ("b", "c")), "LR")

    async def test_l04_real_td_branch_merge(self):
        await self.check(("a", "b", "c", "d"), (("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")))

    async def test_l05_real_lr_branch_merge(self):
        await self.check(("a", "b", "c", "d"), (("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")), "LR")

    async def test_l06_real_multiedge_preserves_both_routes(self):
        result = await self.check(("a", "b"), (("a", "b"), ("a", "b")))
        # mergeEdges=false keeps separate graph edges and endpoint attachments.
        self.assertNotEqual(result.edges[0].sections, result.edges[1].sections)

    async def test_l07_real_self_loop(self):
        await self.check(("a",), (("a", "a"),))

    async def test_l08_reserved_looking_user_ids_and_independent_calls(self):
        await self.check(("root", "n0", "e0"), (("root", "n0"), ("n0", "e0")))
        result = await self.check(("fresh",), ())
        self.assertEqual(len(result.edges), 0)

    async def test_l09_measured_dimensions_and_input_immutability(self):
        chart, measured = specimen()
        measured = (replace(measured[0], width=140, height=70), replace(measured[1], width=100, height=55))
        before = copy.deepcopy((chart, measured))
        result = await layout_flowchart(chart, measured)
        self.assert_quality(chart, measured, result)
        self.assertEqual((chart, measured), before)


class AdapterControlTests(unittest.IsolatedAsyncioTestCase):
    """Fault injection into the public engine boundary, never production data."""

    def fake_module(self, transform=None, failure=None, version="0.1.0"):
        module = types.ModuleType("pyelk")
        module.__version__ = version
        events = []

        class Engine:
            def __enter__(self):
                events.append("enter")
                return self

            def __exit__(self, *args):
                events.append("close")

            async def layout(self, graph):
                events.append(copy.deepcopy(graph))
                if failure is not None:
                    raise failure
                # Explicit test-only response: arbitrary legal rectangles, not
                # copied from the implementation or an actual layout result.
                nodes = [dict(node, x=i * 160, y=0) for i, node in enumerate(graph["children"])]
                edges = [dict(edge, sections=[{"startPoint": {"x": 80, "y": 20}, "bendPoints": [], "endPoint": {"x": 160, "y": 20}}]) for edge in graph["edges"]]
                response = {"id": "root", "width": 300, "height": 100, "children": nodes, "edges": edges}
                return transform(response) if transform else response

        module.ELK = Engine
        return module, events

    async def test_c01_source_root_defaults_direction_and_ignored_spacing(self):
        chart, measured = specimen(direction="LR")
        chart = replace(chart, config=replace(chart.config, node_spacing=999, rank_spacing=888))
        module, events = self.fake_module()
        with patch.dict(sys.modules, {"pyelk": module}):
            await layout_flowchart(chart, measured)
        graph = events[1]
        options = graph["layoutOptions"]
        self.assertEqual(options["elk.direction"], "RIGHT")
        self.assertEqual(options["elk.algorithm"], "elk.layered")
        self.assertEqual(options["spacing.baseValue"], 40)
        self.assertEqual(options["elk.layered.nodePlacement.strategy"], "BRANDES_KOEPF")
        self.assertEqual(options["elk.layered.nodePlacement.bk.fixedAlignment"], "BALANCED")
        self.assertEqual(options["elk.layered.cycleBreaking.strategy"], "DEPTH_FIRST")
        self.assertEqual(options["elk.layered.layering.strategy"], "NETWORK_SIMPLEX")
        self.assertIs(options["elk.layered.mergeEdges"], False)
        self.assertNotIn("elk.spacing.nodeNode", options)
        self.assertNotIn("elk.layered.spacing.nodeNodeBetweenLayers", options)
        self.assertEqual(events[-1], "close")

    async def test_c02_input_faults_fail_before_engine_creation(self):
        chart, measured = specimen()
        variants = [
            (replace(chart, nodes=()), ()),
            (replace(chart, nodes=(chart.nodes[0], chart.nodes[0])), measured),
            (replace(chart, edges=(chart.edges[0], chart.edges[0])), measured),
            (chart, measured[:1]), (chart, measured + measured[:1]),
            (chart, (replace(measured[0], id="unknown"), measured[1])),
            (chart, (replace(measured[0], width=0), measured[1])),
            (chart, (replace(measured[0], height=math.inf), measured[1])),
            (chart, (replace(measured[0], width=True), measured[1])),
            (chart, (replace(measured[0], label_width=90), measured[1])),
            (chart, (replace(measured[0], label_height=-1), measured[1])),
            (replace(chart, edges=(replace(chart.edges[0], target="unknown"),)), measured),
            (replace(chart, config=replace(chart.config, node_spacing=math.nan)), measured),
        ]
        for bad_chart, bad_measured in variants:
            module, events = self.fake_module()
            with self.subTest(chart=bad_chart, measured=bad_measured), patch.dict(sys.modules, {"pyelk": module}):
                with self.assertRaises(MermaidError) as raised:
                    await layout_flowchart(bad_chart, bad_measured)
                self.assertEqual(raised.exception.code, "INVALID_LAYOUT_INPUT")
                self.assertEqual(events, [])

    async def test_c03_wrong_direction_or_engine_is_explicit(self):
        chart, measured = specimen()
        for invalid in (replace(chart, direction="RL"), replace(chart, config=replace(chart.config, layout="dagre"))):
            with self.subTest(invalid=invalid), self.assertRaises(MermaidError) as raised:
                await layout_flowchart(invalid, measured)
            self.assertEqual(raised.exception.code, "UNSUPPORTED_LAYOUT")

    async def test_c04_corrupt_output_is_rejected_and_worker_closed(self):
        chart, measured = specimen()
        def modify(path, value):
            def transform(response):
                target = response
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = value
                return response
            return transform
        variants = [
            lambda r: None,
            modify(("width",), 0), modify(("height",), math.nan),
            modify(("children",), []), modify(("children", 1, "id"), "n0"),
            modify(("children", 1, "id"), "unknown"),
            modify(("children", 0, "width"), 99), modify(("children", 0, "x"), math.inf),
            modify(("edges",), []), modify(("edges", 0, "targets"), ["wrong"]),
            modify(("edges", 0, "sections"), []),
            modify(("edges", 0, "sections", 0, "startPoint"), None),
            modify(("edges", 0, "sections", 0, "bendPoints"), "invalid"),
            modify(("edges", 0, "sections", 0, "endPoint", "x"), True),
        ]
        for index, transform in enumerate(variants):
            module, events = self.fake_module(transform=transform)
            with self.subTest(fault=index), patch.dict(sys.modules, {"pyelk": module}):
                with self.assertRaises(MermaidError) as raised:
                    await layout_flowchart(chart, measured)
                self.assertEqual(raised.exception.code, "INVALID_ELK_RESULT")
                self.assertEqual(events[-1], "close")

    async def test_c05_multiple_sections_and_bends_are_not_dropped(self):
        chart, measured = specimen()
        sections = [
            {"startPoint": {"x": 80, "y": 20}, "bendPoints": [{"x": 100, "y": 20}], "endPoint": {"x": 100, "y": 50}},
            {"startPoint": {"x": 100, "y": 50}, "bendPoints": [{"x": 160, "y": 50}], "endPoint": {"x": 160, "y": 20}},
        ]
        def response_transform(response):
            response["edges"][0]["sections"] = sections
            return response
        module, events = self.fake_module(transform=response_transform)
        with patch.dict(sys.modules, {"pyelk": module}):
            result = await layout_flowchart(chart, measured)
        self.assertEqual(len(result.edges[0].sections), 2)
        for actual, expected in zip(result.edges[0].sections, sections):
            expected_points = (expected["startPoint"], *expected["bendPoints"], expected["endPoint"])
            self.assertEqual(edge_points(actual), tuple(Point(p["x"], p["y"]) for p in expected_points))
        self.assertEqual(events[-1], "close")

    async def test_c06_engine_failure_retains_cause_and_closes(self):
        chart, measured = specimen()
        failure = RuntimeError("test-only worker failure")
        module, events = self.fake_module(failure=failure)
        with patch.dict(sys.modules, {"pyelk": module}), self.assertRaises(MermaidError) as raised:
            await layout_flowchart(chart, measured)
        self.assertEqual(raised.exception.code, "ELK_LAYOUT_FAILED")
        self.assertIs(raised.exception.__cause__, failure)
        self.assertEqual(events[-1], "close")

    async def test_c07_cancellation_propagates_and_closes(self):
        chart, measured = specimen()
        module, events = self.fake_module(failure=asyncio.CancelledError())
        with patch.dict(sys.modules, {"pyelk": module}), self.assertRaises(asyncio.CancelledError):
            await layout_flowchart(chart, measured)
        self.assertEqual(events[-1], "close")

    async def test_c08_wrong_engine_version_is_rejected_before_layout(self):
        chart, measured = specimen()
        module, events = self.fake_module(version="0.0.0")
        with patch.dict(sys.modules, {"pyelk": module}), self.assertRaises(MermaidError) as raised:
            await layout_flowchart(chart, measured)
        self.assertEqual(raised.exception.code, "ELK_VERSION_MISMATCH")
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
