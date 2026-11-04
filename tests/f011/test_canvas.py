"""Independent F01.1 Canvas boundary, content and lifecycle assertions.

Sources and assertion ownership: references/f011-canvas-assertions.json.
Synthetic placements below are test-only fixtures for isolating the Canvas
adapter; production layout is exercised separately through the real API.
No Python renderer output is used as a saved expected image.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
import math
import unittest

from PIL import Image
from py_skia_canvas import Canvas

from py_mermaid.api import parse, render
from py_mermaid.config import resolve_config
from py_mermaid.model.flowchart import (
    Box, EdgeSection, Flowchart, FlowEdge, FlowLayout, FlowNode, MermaidError,
    PlacedNode, Point, RoutedEdge, SourcePosition, SourceSpan,
)
from py_mermaid.rendering.skia import CanvasSession


_SPAN = SourceSpan(SourcePosition(0, 0, 1, 0), SourcePosition(1, 1, 1, 1))


def diagram_for_labels(*labels: str, font_size: float | None = None, html_labels: bool = True) -> Flowchart:
    """Test-only pure semantic fixture, independently supplied text/config."""
    nodes = tuple(FlowNode(chr(65 + index), label, _SPAN) for index, label in enumerate(labels))
    config = resolve_config({"htmlLabels": html_labels})
    if font_size is not None:
        # Test-only effective font injection isolates Canvas measurement. The
        # source legacy root fontSize does not override themeVariables.fontSize.
        config = replace(config, font_size=font_size)
    return Flowchart("test-only semantic fixture", "TD", nodes, (), config)


def isolated_layout(measured) -> FlowLayout:
    """Test-only disconnected placements isolate measuring/drawing from ELK."""
    nodes = tuple(PlacedNode(node.id, Box(40 + index * 260, 30, node.width, node.height))
                  for index, node in enumerate(measured))
    return FlowLayout(nodes, (), max(box.box.x + box.box.width for box in nodes) + 40,
                      max(box.box.height for box in nodes) + 60, "test-only", "fixture")


def image_for(result) -> Image.Image:
    image = Image.open(BytesIO(result.data))
    image.load()
    return image.convert("RGB")


def dark_pixels(image: Image.Image, box: Box) -> int:
    left, top = max(0, math.floor(box.x)), max(0, math.floor(box.y))
    right, bottom = min(image.width, math.ceil(box.x + box.width)), min(image.height, math.ceil(box.y + box.height))
    return sum(max(pixel) < 130 for pixel in image.crop((left, top, right, bottom)).getdata())


class CanvasMeasurementTests(unittest.TestCase):
    def test_source_padding_and_public_text_metrics(self):
        """Default neo: max(label,120)+32 horizontally and row-height+24."""
        diagram = diagram_for_labels("Mermaid", "Wide WWW and narrow iii")
        measured = CanvasSession("cpu").measure(diagram)
        canvas = Canvas(1, 1)
        canvas.gpu = False
        context = canvas.getContext("2d")
        context.font = '14px "Recursive Variable", arial, sans-serif'
        context.textAlign = "center"
        context.textBaseline = "alphabetic"
        context.direction = "ltr"
        for node, size in zip(diagram.nodes, measured, strict=True):
            with self.subTest(node=node.id):
                public_metrics = [context.measureText(line.text) for line in size.lines]
                expected_width = max(120, *(max(metric.width,
                                                metric.actualBoundingBoxLeft + metric.actualBoundingBoxRight)
                                            for metric in public_metrics))
                self.assertAlmostEqual(size.label_width, expected_width, places=4)
                self.assertAlmostEqual(size.width - size.label_width, 32)
                self.assertAlmostEqual(size.height - size.label_height, 24)
                self.assertGreaterEqual(size.label_height, 21)
                self.assertEqual("".join(line.text for line in size.lines), node.label)

    def test_font_size_changes_real_metrics(self):
        small = CanvasSession("cpu").measure(diagram_for_labels("WWWiii", font_size=12))[0]
        large = CanvasSession("cpu").measure(diagram_for_labels("WWWiii", font_size=32))[0]
        self.assertGreater(large.lines[0].width, small.lines[0].width * 2)
        self.assertGreater(large.label_height, small.label_height * 2)

    def test_multiline_plain_text_and_lineheight(self):
        for html_labels, factor in ((True, 1.5), (False, 1.1)):
            diagram = diagram_for_labels("First\nSecond\n第三行", html_labels=html_labels)
            measured = CanvasSession("cpu").measure(diagram)[0]
            self.assertEqual(tuple(line.text for line in measured.lines), ("First", "Second", "第三行"))
            self.assertGreaterEqual(measured.label_height, 3 * 14 * factor)
            self.assertGreater(measured.label_width, 0)
            self.assertGreaterEqual(measured.height, measured.label_height + 24)

    def test_long_label_preserved_without_truncation(self):
        label = "Content " * 80
        diagram = diagram_for_labels(label)
        measured = CanvasSession("cpu").measure(diagram)[0]
        self.assertEqual("".join(line.text for line in measured.lines), label)
        self.assertGreater(len(measured.lines), 20)
        self.assertGreater(measured.label_height, 400)
        self.assertGreaterEqual(measured.label_width, 120)
        self.assertGreater(measured.width, measured.label_width)

    def test_fallback_font_declaration_separator(self):
        base = diagram_for_labels("Font family must retain explicit size")
        config = replace(base.config, font_family=base.config.font_family + ";")
        plain = CanvasSession("cpu").measure(base)[0]
        semicolon = CanvasSession("cpu").measure(replace(base, config=config))[0]
        self.assertEqual(plain, semicolon)

    def test_source_effective_minimum_and_empty_label_exception(self):
        session = CanvasSession("cpu")
        short = session.measure(diagram_for_labels("Hello"))[0]
        empty = session.measure(diagram_for_labels(""))[0]
        self.assertEqual(short.label_width, 120)
        self.assertEqual(short.width, 152)
        self.assertEqual(short.height, 45)
        self.assertEqual(empty.label_width, 0)
        self.assertEqual(empty.width, 32)

    def test_long_unbreakable_word_preserved_and_contained(self):
        label = "W" * 80
        diagram = diagram_for_labels(label)
        measured = CanvasSession("cpu").measure(diagram)[0]
        self.assertEqual("".join(line.text for line in measured.lines), label)
        self.assertGreater(measured.label_width, 120)
        self.assertGreaterEqual(measured.width, measured.lines[0].width + 32)

    def test_site_root_fontsize_does_not_change_effective_theme_font(self):
        first = resolve_config({"fontSize": 12})
        second = resolve_config({"fontSize": 32})
        self.assertEqual(first.font_size, 14)
        self.assertEqual(second.font_size, 14)
        self.assertNotEqual(first.site_font_size, second.site_font_size)

    def test_rich_content_rejected_instead_of_stripped(self):
        for text in ("<b>secret</b>", "`markdown`", "$$x$$"):
            with self.subTest(text=text), self.assertRaises(MermaidError) as caught:
                CanvasSession("cpu").measure(diagram_for_labels(text))
            self.assertEqual(caught.exception.code, "UNSUPPORTED_SYNTAX")


class CanvasContentTests(unittest.TestCase):
    def test_png_dimensions_background_and_visible_content(self):
        diagram = diagram_for_labels("Readable label")
        session = CanvasSession("cpu")
        measured = session.measure(diagram)
        result = session.render(diagram, measured, isolated_layout(measured))
        self.assertTrue(result.data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(result.mime, "image/png")
        image = image_for(result)
        self.assertEqual(image.size, (result.width, result.height))
        for position in ((0, 0), (image.width - 1, 0), (0, image.height - 1), (image.width - 1, image.height - 1)):
            self.assertEqual(image.getpixel(position), (255, 255, 255))
        self.assertGreater(len(set(image.getdata())), 8, "a background-only/no-op image is invalid")
        self.assertEqual(dict(result.backend)["renderer"], "CPU")

    def test_every_label_has_pixels_inside_its_node(self):
        diagram = diagram_for_labels("Visible alpha", "Visible beta", "中文标签", "Line one\nLine two")
        session = CanvasSession("cpu")
        measured = session.measure(diagram)
        result = session.render(diagram, measured, isolated_layout(measured))
        image = image_for(result)
        nodes = {event.semantic_id: event.box for event in result.trace if event.kind == "node"}
        text_events = [event for event in result.trace if event.kind == "text"]
        self.assertEqual(len(nodes), 4)
        self.assertEqual([event.text for event in text_events],
                         ["Visible alpha", "Visible beta", "中文标签", "Line one", "Line two"])
        for event in text_events:
            with self.subTest(text=event.text):
                label, node = event.box, nodes[event.semantic_id]
                self.assertGreaterEqual(label.x, node.x)
                self.assertGreaterEqual(label.y, node.y)
                self.assertLessEqual(label.x + label.width, node.x + node.width)
                self.assertLessEqual(label.y + label.height, node.y + node.height)
                self.assertGreater(dark_pixels(image, label), 5, "label trace without visible glyph pixels")

    def test_plain_rect_fill_and_stroke_are_present(self):
        diagram = diagram_for_labels("Centre")
        session = CanvasSession("cpu")
        measured = session.measure(diagram)
        result = session.render(diagram, measured, isolated_layout(measured))
        image = image_for(result)
        box = next(event.box for event in result.trace if event.kind == "node")
        self.assertEqual(image.getpixel((math.floor(box.x + 5), math.floor(box.y + 5))), (255, 255, 255))
        border_colors = [image.getpixel((math.floor(box.x + offset), math.floor(box.y + 10))) for offset in (-1, 0, 1)]
        self.assertIn((40, 37, 61), border_colors)

    def test_neo_shadow_is_visible_and_included_in_bounds(self):
        diagram = diagram_for_labels("Shadow")
        session = CanvasSession("cpu")
        measured = session.measure(diagram)
        result = session.render(diagram, measured, isolated_layout(measured))
        image = image_for(result)
        node = next(event.box for event in result.trace if event.kind == "node")
        shadow = next(event.box for event in result.trace if event.kind == "shadow")
        self.assertEqual(shadow.x - node.x, 3)  # offset4 minus stroke2/2
        self.assertEqual(shadow.y - node.y, 3)
        self.assertEqual(shadow.width - node.width, 2)
        pixel = image.getpixel((math.floor(node.x + node.width + 3), math.floor(node.y + node.height / 2)))
        self.assertTrue(all(238 <= channel <= 241 for channel in pixel), pixel)
        self.assertLess(shadow.x + shadow.width, result.width - 7)
        self.assertLess(shadow.y + shadow.height, result.height - 7)

    def test_multiple_sections_and_arrow_have_real_pixels(self):
        diagram = diagram_for_labels("Start", "End")
        diagram = replace(diagram, edges=(FlowEdge("e0", "A", "B", _SPAN),))
        session = CanvasSession("cpu")
        measured = session.measure(diagram)
        first, second = measured
        # Independent test-only route: vertical, horizontal, vertical sections.
        box_a = Box(20, 20, first.width, first.height)
        box_b = Box(220, 220, second.width, second.height)
        start = Point(box_a.x + box_a.width / 2, box_a.y + box_a.height)
        middle = Point(start.x, 150)
        bend = Point(box_b.x + box_b.width / 2, 150)
        end = Point(bend.x, box_b.y)
        sections = (EdgeSection(start, (), middle), EdgeSection(middle, (bend,), end))
        layout = FlowLayout((PlacedNode("A", box_a), PlacedNode("B", box_b)),
                            (RoutedEdge("e0", sections),), 500, 350, "test-only", "fixture")
        result = session.render(diagram, measured, layout)
        events = [event for event in result.trace if event.kind == "edge"]
        self.assertEqual(len(events), 2)
        self.assertEqual(tuple(len(event.points) for event in events), (2, 3))
        image = image_for(result)
        for event in events:
            a, b = event.points[0], event.points[1]
            center = Point((a.x + b.x) / 2, (a.y + b.y) / 2)
            self.assertGreater(dark_pixels(image, Box(center.x - 2, center.y - 2, 4, 4)), 2)
        arrow = next(event for event in result.trace if event.kind == "arrow")
        self.assertEqual(arrow.semantic_id, "e0")
        self.assertEqual(arrow.points[0], events[-1].points[-1])
        centroid = Point(sum(point.x for point in arrow.points) / 3, sum(point.y for point in arrow.points) / 3)
        self.assertGreater(dark_pixels(image, Box(centroid.x - 2, centroid.y - 2, 4, 4)), 2)
        for point in arrow.points:
            self.assertGreaterEqual(point.x, 0)
            self.assertGreaterEqual(point.y, 0)
            self.assertLess(point.x, result.width)
            self.assertLess(point.y, result.height)

    def test_padding_contains_all_drawn_geometry(self):
        diagram = diagram_for_labels("An entirely visible label")
        session = CanvasSession("cpu")
        measured = session.measure(diagram)
        result = session.render(diagram, measured, isolated_layout(measured))
        padding = 8  # config.schema.yaml: flowchart.diagramPadding
        for event in result.trace:
            if event.kind in {"node", "text"}:
                box = event.box
                self.assertGreaterEqual(box.x, padding)
                self.assertGreaterEqual(box.y, padding)
                self.assertLessEqual(box.x + box.width, result.width - padding)
                self.assertLessEqual(box.y + box.height, result.height - padding)

    def test_real_elk_branch_semantic_connections_and_content(self):
        result = render('flowchart TD\nA[Start] --> B[Left]\nA --> C[Right]\nB --> D[Finish]\nC --> D', backend="cpu")
        image = image_for(result)
        nodes = {event.semantic_id: event.box for event in result.trace if event.kind == "node"}
        edge_events = {event.semantic_id: event for event in result.trace if event.kind == "edge"}
        self.assertEqual(set(nodes), {"A", "B", "C", "D"})
        self.assertEqual(len(edge_events), 4)
        self.assertEqual(len([event for event in result.trace if event.kind == "arrow"]), 4)
        self.assertEqual([event.text for event in result.trace if event.kind == "text"], ["Start", "Left", "Right", "Finish"])
        for edge in result.diagram.edges:
            points = edge_events[edge.id].points
            for point, node_id in ((points[0], edge.source), (points[-1], edge.target)):
                box = nodes[node_id]
                inside = box.x - 1e-4 <= point.x <= box.x + box.width + 1e-4 and box.y - 1e-4 <= point.y <= box.y + box.height + 1e-4
                boundary = min(abs(point.x - box.x), abs(point.x - box.x - box.width),
                               abs(point.y - box.y), abs(point.y - box.y - box.height)) < 1e-4
                self.assertTrue(inside and boundary, "edge endpoint must meet its semantic node boundary")
            self.assertLessEqual(points[0].y, points[-1].y)
        for event in result.trace:
            if event.kind == "text":
                self.assertGreater(dark_pixels(image, event.box), 5)


class CanvasLifecycleTests(unittest.TestCase):
    def test_owner_thread_rejects_measure_and_render(self):
        diagram = diagram_for_labels("Owner")
        session = CanvasSession("cpu")
        measured = session.measure(diagram)
        layout = isolated_layout(measured)
        with ThreadPoolExecutor(max_workers=1) as pool:
            for method, args in ((session.measure, (diagram,)), (session.render, (diagram, measured, layout))):
                future = pool.submit(method, *args)
                with self.assertRaises(MermaidError) as caught:
                    future.result()
                self.assertEqual(caught.exception.code, "THREAD_OWNERSHIP")

    def test_repeated_session_has_no_old_trace_or_style(self):
        session = CanvasSession("cpu")
        for label, font_size in (("First", 12), ("Second", 32), ("Third", 16)):
            diagram = diagram_for_labels(label, font_size=font_size)
            measured = session.measure(diagram)
            result = session.render(diagram, measured, isolated_layout(measured))
            self.assertEqual([event.text for event in result.trace if event.kind == "text"], [label])
            self.assertEqual(result.trace, session.trace)
            self.assertEqual(len([event for event in result.trace if event.kind == "node"]), 1)
            self.assertGreater(dark_pixels(image_for(result), next(event.box for event in result.trace if event.kind == "text")), 5)

    def test_worker_can_create_own_session(self):
        def on_worker():
            session = CanvasSession("cpu")
            diagram = diagram_for_labels("Worker")
            measured = session.measure(diagram)
            return session.render(diagram, measured, isolated_layout(measured))
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(on_worker).result()
        self.assertTrue(result.data.startswith(b"\x89PNG"))
        self.assertEqual(dict(result.backend)["renderer"], "CPU")

    def test_auto_preserves_actual_canvas_default(self):
        default_canvas = Canvas(1, 1)
        diagram = diagram_for_labels("Auto")
        session = CanvasSession("auto")
        measured = session.measure(diagram)
        result = session.render(diagram, measured, isolated_layout(measured))
        self.assertEqual(dict(result.backend)["renderer"], default_canvas.engine["renderer"])

    def test_gpu_required_returns_gpu(self):
        # Required device group: unavailable hardware is a recorded failure,
        # never a skip or a successful fallback to CPU.
        diagram = diagram_for_labels("GPU required")
        session = CanvasSession("gpu")
        measured = session.measure(diagram)
        result = session.render(diagram, measured, isolated_layout(measured))
        self.assertEqual(dict(result.backend)["renderer"], "GPU")
        self.assertGreater(dark_pixels(image_for(result), next(event.box for event in result.trace if event.kind == "text")), 5)

    def test_unknown_backend_rejected(self):
        with self.assertRaises(MermaidError) as caught:
            CanvasSession("fallback")
        self.assertEqual(caught.exception.code, "INVALID_BACKEND")

    def test_explicit_missing_route_rejected(self):
        diagram = diagram_for_labels("Start", "End")
        diagram = replace(diagram, edges=(FlowEdge("e0", "A", "B", _SPAN),))
        session = CanvasSession("cpu")
        measured = session.measure(diagram)
        layout = replace(isolated_layout(measured), edges=(RoutedEdge("e0", ()),))
        with self.assertRaises(MermaidError) as caught:
            session.render(diagram, measured, layout)
        self.assertEqual(caught.exception.code, "INVALID_LAYOUT")


if __name__ == "__main__":
    unittest.main()
