"""F01.3 source-derived title/rich-measurement layout relations.

Real Canvas measurement and real pyelk are the primary path. Coordinates used
by the synthetic title-control fixture below are independent test-only JSON,
not candidate output, layout goldens or production data.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, replace
from io import BytesIO
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
import types
import unittest
from unittest.mock import patch

from py_mermaid.config import resolve_config
from py_mermaid.geometry import geometry_bounds
from py_mermaid.layout.elk import layout_flowchart
from py_mermaid.model.flowchart import (
    Box, Flowchart, FlowEdge, FlowGroup, FlowNode, MeasuredNode, MeasuredTitle,
    MermaidError, SourcePosition, SourceSpan,
)
from py_mermaid.rendering.skia import CanvasSession

THEMES = ("base", "dark", "default", "forest", "neutral", "neo", "neo-dark",
          "redux", "redux-dark", "redux-color", "redux-dark-color", "null")


def specimen(*, title="Diagram title", config=None, rich=False, groups=False, label="Condition"):
    p = SourcePosition(0, 0, 1, 0)
    span = SourceSpan(p, p)
    first = "**Alpha** and *italic*" if rich else "Alpha WWWW"
    node_a = FlowNode("A", first, span, "round", "G" if groups else None,
                      "markdown" if rich else "text", first, span)
    node_b = FlowNode("B", "<b>Beta</b> &amp; 内容" if rich else "Beta WWWW", span,
                      "square", None, "text", "<b>Beta</b> &amp; 内容" if rich else "Beta WWWW", span)
    edge = FlowEdge("AB", "A", "B", span, label, span, "text", label)
    group_tuple = (FlowGroup("G", "**Group** title" if rich else "Group title", span, ("A",),
                             label_kind="markdown" if rich else "text", raw_label="**Group** title" if rich else "Group title"),) if groups else ()
    return Flowchart("test-only title/rich semantic fixture", "TD", (node_a, node_b),
                     (edge,), resolve_config(config), groups=group_tuple, title=title)


def content_union(layout):
    """Independent source getBBox union, excluding unpainted engine padding."""
    boxes = [node.box for node in layout.nodes]
    boxes += [group.box for group in layout.groups]
    boxes += [group.title_box for group in layout.groups if group.title_box is not None]
    boxes += [label.box for label in layout.edge_labels]
    xs = [value for box in boxes for value in (box.x, box.x+box.width)]
    ys = [value for box in boxes for value in (box.y, box.y+box.height)]
    for edge in layout.edges:
        if edge.path:
            # Independent native consumer of final source paint geometry;
            # raw ELK sections now deliberately retain pre-clipping coordinates.
            # These title fixtures' point markers stay within the node union.
            from py_skia_canvas import Path2D
            bounds = Path2D(edge.path).bounds
            xs.extend((bounds['left'],bounds['left']+bounds['width']))
            ys.extend((bounds['top'],bounds['top']+bounds['height']))
            continue
        for section in edge.sections:
            for point in (section.start, *section.bends, section.end):
                xs.append(point.x)
                ys.append(point.y)
    if not xs:
        return Box(0, 0, 0, 0)
    return Box(min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))


def contains(outer, inner, tolerance=1e-5):
    return (inner.x >= outer.x-tolerance and inner.y >= outer.y-tolerance
            and inner.x+inner.width <= outer.x+outer.width+tolerance
            and inner.y+inner.height <= outer.y+outer.height+tolerance)


class RealRichLayoutTests(unittest.IsolatedAsyncioTestCase):
    async def execute(self, diagram, *, draw=False):
        original = copy.deepcopy(diagram)
        session = CanvasSession("cpu")
        nodes = session.measure(diagram)
        annotations = session.measure_annotations(diagram)
        before = copy.deepcopy((nodes, annotations))
        layout = await layout_flowchart(diagram, nodes, measured_groups=annotations.groups,
                                        measured_edge_labels=annotations.edge_labels, measured_title=annotations.title,
                                        title_suppressed=annotations.title_suppressed)
        self.assertEqual(diagram, original)
        self.assertEqual((nodes, annotations), before)
        self.assertEqual(tuple(n.id for n in layout.nodes), tuple(n.id for n in diagram.nodes))
        self.assertEqual(tuple(e.id for e in layout.edges), tuple(e.id for e in diagram.edges))
        self.assertEqual(tuple(g.id for g in layout.groups), tuple(g.id for g in diagram.groups))
        for measured, placed in zip(nodes, layout.nodes):
            self.assertAlmostEqual(measured.width, placed.box.width)
            self.assertAlmostEqual(measured.height, placed.box.height)
            self.assertGreaterEqual(measured.width, measured.label_width)
            self.assertGreaterEqual(measured.height, measured.label_height)
        for label, placed in zip(annotations.edge_labels, layout.edge_labels):
            self.assertEqual(label.id, placed.id)
            self.assertAlmostEqual(label.width, placed.box.width)
            self.assertAlmostEqual(label.height, placed.box.height)
        if annotations.title is not None:
            title, box = annotations.title, layout.title_box
            self.assertIsNotNone(box)
            center = content_union(layout).x+content_union(layout).width/2
            anchor_x = box.x if title.text_anchor == "start" else box.x+box.width if title.text_anchor == "end" else box.x+box.width/2
            self.assertAlmostEqual(anchor_x, center)
            self.assertAlmostEqual(box.y+title.ascent, -diagram.config.title_top_margin)
            self.assertGreaterEqual(box.height+1e-7, title.ascent+title.descent)
            self.assertTrue(contains(geometry_bounds(layout), box))
        result = session.render(diagram, nodes, layout, annotations=annotations) if draw else None
        return nodes, annotations, layout, result

    async def test_l01_title_font18_ascent_and_plain_text(self):
        title = "Literal <b>title</b> & 内容"
        nodes, annotations, layout, _ = await self.execute(specimen(title=title, config={"themeVariables": {"fontSize": "32px"}}))
        self.assertTrue(annotations.title.runs)
        self.assertEqual("".join(run.text for run in annotations.title.runs), title)
        self.assertTrue(all(run.font_size == 18 for run in annotations.title.runs))
        self.assertAlmostEqual(layout.title_box.y, -25-annotations.title.ascent)

    async def test_l02_all_title_anchors_and_explicit_margin(self):
        for anchor in ("middle", "start", "end"):
            with self.subTest(anchor=anchor):
                css = f".flowchartTitleText{{text-anchor:{anchor};font-size:26px}}"
                _, annotations, _, _ = await self.execute(specimen(config={"themeCSS": css, "flowchart": {"titleTopMargin": 37}}))
                self.assertEqual(annotations.title.text_anchor, anchor)
                self.assertTrue(all(run.font_size == 26 for run in annotations.title.runs))

    async def test_l03_title_does_not_enter_or_compress_elk(self):
        from pyelk import ELK
        original_layout = ELK.layout
        inputs = []
        async def observe(engine, graph, args=None):
            inputs.append(copy.deepcopy(graph))
            return await original_layout(engine, graph, args)
        base = specimen(title="", groups=True, rich=True)
        with patch.object(ELK, "layout", observe):
            _, _, uncaptioned, _ = await self.execute(base)
            _, _, captioned, _ = await self.execute(replace(base, title="A very long title "*10))
        self.assertEqual(inputs[0], inputs[1], "Title measurement must not change actual ELK input")
        self.assertIsNone(uncaptioned.title_box)
        self.assertIsNotNone(captioned.title_box)
        self.assertEqual((uncaptioned.width, uncaptioned.height), (captioned.width, captioned.height))

    async def test_l04_rich_groups_crossing_labels_keep_measured_boxes_and_edges(self):
        label = "<b>Cross</b><br/><i>label 内容</i>"
        nodes, annotations, layout, _ = await self.execute(specimen(groups=True, rich=True, label=label))
        self.assertTrue(nodes[0].runs)
        self.assertTrue(annotations.groups[0].runs)
        group = layout.groups[0]
        self.assertTrue(contains(group.box, layout.nodes[0].box))
        self.assertTrue(contains(group.title_box, Box(group.title_box.x, group.title_box.y,
                                                   annotations.groups[0].label_width, annotations.groups[0].label_height)))
        self.assertEqual(tuple(e.id for e in layout.edge_labels), ("AB",))
        self.assertTrue(layout.edges[0].sections)

    async def test_l05_sanitized_empty_and_break_only_edge_labels_are_legal_zero_width(self):
        for label in ("<br/>", "<span></span>", "<script>blocked()</script>"):
            with self.subTest(label=label):
                _, annotations, layout, _ = await self.execute(specimen(title="", label=label, config={"securityLevel": "strict"}))
                self.assertEqual(len(annotations.edge_labels), 1)
                self.assertEqual(annotations.edge_labels[0].width, 0)
                self.assertGreater(annotations.edge_labels[0].height, 0)
                self.assertEqual(layout.edge_labels[0].box.width, 0)
                self.assertEqual(tuple(edge.id for edge in layout.edges), ("AB",))

    async def test_l06_font_size_changes_actual_dimensions_not_semantic_ids(self):
        small_config = {"themeVariables": {"fontSize": "12px"}, "flowchart": {"wrappingWidth": 2000, "minNodeWidth": 0}}
        large_config = {"themeVariables": {"fontSize": "32px"}, "flowchart": {"wrappingWidth": 2000, "minNodeWidth": 0}}
        small, _, small_layout, _ = await self.execute(specimen(title="", config=small_config))
        large, _, large_layout, _ = await self.execute(specimen(title="", config=large_config))
        for a, b in zip(small, large):
            self.assertGreater(b.label_width, a.label_width)
            self.assertGreater(b.label_height, a.label_height)
            self.assertGreater(b.width, a.width)
            self.assertGreater(b.height, a.height)
        self.assertEqual(tuple(n.id for n in small_layout.nodes), tuple(n.id for n in large_layout.nodes))

    async def test_l07_all_source_themes_keep_label_and_title_geometry(self):
        for theme in THEMES:
            with self.subTest(theme=theme):
                await self.execute(specimen(groups=True, rich=True, config={"theme": theme}))

    async def test_l08_actual_png_title_ink_inside_viewport(self):
        from PIL import Image
        for anchor in ("middle", "start", "end"):
            with self.subTest(anchor=anchor):
                diagram = specimen(title="Wide italic title WWWW 内容 "+"overflow "*12,
                                   config={"theme": "base", "themeVariables": {"background": "#ffffff"},
                                           "themeCSS": f".flowchartTitleText{{font-size:28px;font-style:italic;fill:#000000;text-anchor:{anchor}}}"})
                _, _, _, result = await self.execute(diagram, draw=True)
                self.assertEqual(result.mime, "image/png")
                self.assertEqual(result.data[:8], b"\x89PNG\r\n\x1a\n")
                title_events = [event for event in result.trace if event.kind == "diagram-title" and event.box]
                self.assertTrue(title_events)
                image = Image.open(BytesIO(result.data)).convert("RGBA")
                self.assertEqual(image.size, (result.width, result.height))
                viewport = Box(0, 0, result.width, result.height)
                for event in title_events:
                    self.assertTrue(contains(viewport, event.box))
                    crop = image.crop((max(0, math.floor(event.box.x)-1), max(0, math.floor(event.box.y)-1),
                                       min(result.width, math.ceil(event.box.x+event.box.width)+1),
                                       min(result.height, math.ceil(event.box.y+event.box.height)+1)))
                    self.assertGreater(sum(1 for r,g,b,a in crop.getdata() if a and min(r,g,b) < 200), 0,
                                       "A title trace alone does not prove actual ink")

    async def test_l09_measurements_pure_immutable_and_canvas_owner_thread(self):
        diagram = specimen(groups=True, rich=True)
        session = CanvasSession("cpu")
        nodes = session.measure(diagram)
        annotations = session.measure_annotations(diagram)
        before = copy.deepcopy((nodes, annotations))
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(session.measure, diagram)
            with self.assertRaises(MermaidError) as raised:
                future.result(timeout=10)
        self.assertEqual(raised.exception.code, "THREAD_OWNERSHIP")
        layout = await layout_flowchart(diagram, nodes, measured_groups=annotations.groups,
                                        measured_edge_labels=annotations.edge_labels, measured_title=annotations.title,
                                        title_suppressed=annotations.title_suppressed)
        json.dumps(asdict(layout))
        self.assertEqual((nodes, annotations), before)

    async def test_l10_display_none_title_has_no_layout_or_ink(self):
        # A valid CSS display:none title contributes neither getBBox nor paint.
        _, annotations, layout, result = await self.execute(specimen(config={"themeCSS": ".flowchartTitleText{display:none}"}), draw=True)
        self.assertIsNone(annotations.title)
        self.assertTrue(annotations.title_suppressed)
        self.assertIsNone(layout.title_box)
        self.assertFalse(any(event.kind == "diagram-title" for event in result.trace))

    async def test_l11_empty_rich_group_title_keeps_container_and_crossing_edge(self):
        diagram = specimen(title="", groups=True, rich=True)
        group = replace(diagram.groups[0], label="<br/>", raw_label="<br/>", label_kind="text")
        _, annotations, layout, _ = await self.execute(replace(diagram, groups=(group,)))
        self.assertEqual(annotations.groups[0].label_width, 0)
        self.assertGreater(annotations.groups[0].label_height, 0)
        self.assertEqual(layout.groups[0].title_box.width, 0)
        self.assertTrue(contains(layout.groups[0].box, layout.nodes[0].box))
        self.assertEqual(tuple(edge.id for edge in layout.edges), ("AB",))


class TitleBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def fixture(self):
        p = SourcePosition(0, 0, 1, 0)
        span = SourceSpan(p, p)
        diagram = Flowchart("test-only synthetic title fixture", "TD", (FlowNode("A", "A", span),), (),
                            resolve_config(), title="Title")
        nodes = (MeasuredNode("A", 80, 40, 30, 16, ()),)
        title = MeasuredTitle(60, 12, 10, 2)
        return diagram, nodes, title

    def module(self):
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
                return {"id": "root", "width": 1000, "height": 800,
                        "children": [{"id": "n0", "x": 30, "y": 40, "width": 80, "height": 40}], "edges": []}
        module.ELK = Engine
        return module, calls

    async def test_c01_content_center_ignores_engine_padding_all_anchors(self):
        diagram, nodes, title = self.fixture()
        for anchor, expected_left in (("middle", 40), ("start", 70), ("end", 10)):
            module, calls = self.module()
            with self.subTest(anchor=anchor), patch.dict(sys.modules, {"pyelk": module}):
                result = await layout_flowchart(diagram, nodes, measured_title=replace(title, text_anchor=anchor))
            self.assertEqual(result.title_box, Box(expected_left, -35, 60, 12))
            self.assertEqual(result.nodes[0].box, Box(30, 40, 80, 40))
            self.assertEqual((result.width, result.height), (1000, 800))
            self.assertEqual(geometry_bounds(replace(result, title_box=None), include_engine=False), Box(30, 40, 80, 40))
            self.assertEqual(calls[-1], "close")

    async def test_c02_invalid_title_metrics_missing_and_unexpected_are_early_errors(self):
        diagram, nodes, title = self.fixture()
        variants = [(diagram, None), (replace(diagram, title=""), title),
                    (diagram, replace(title, width=-1)), (diagram, replace(title, width=math.nan)),
                    (diagram, replace(title, height=math.inf)), (diagram, replace(title, ascent=True)),
                    (diagram, replace(title, descent=-1)), (diagram, replace(title, height=5)),
                    (diagram, replace(title, text_anchor="invalid")),
                    (replace(diagram, config=replace(diagram.config, title_top_margin=-1)), title)]
        for index, (bad, measurement) in enumerate(variants):
            module, calls = self.module()
            with self.subTest(fault=index), patch.dict(sys.modules, {"pyelk": module}):
                with self.assertRaises(MermaidError) as raised:
                    await layout_flowchart(bad, nodes, measured_title=measurement)
                self.assertEqual(raised.exception.code, "INVALID_LAYOUT_INPUT")
                self.assertEqual(calls, [])

    async def test_c03_suppressed_title_rejects_measured_ink_and_invalid_flag(self):
        diagram, nodes, title = self.fixture()
        for measurement, flag in ((title, True), (None, "hidden"), (None, 1)):
            module, calls = self.module()
            with self.subTest(flag=flag), patch.dict(sys.modules, {"pyelk": module}):
                with self.assertRaises(MermaidError) as raised:
                    await layout_flowchart(diagram, nodes, measured_title=measurement, title_suppressed=flag)
                self.assertEqual(raised.exception.code, "INVALID_LAYOUT_INPUT")
                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
