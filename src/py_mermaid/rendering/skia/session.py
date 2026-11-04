"""F01.1 owner-thread Canvas measurement, drawing and PNG encoding.

Only this adapter imports py_skia_canvas. Coordinates are logical px and all
metrics, rectangles, route sections and text remain Python-owned value data.
"""
from __future__ import annotations

import math
import threading
from ...geometry import arrow_polygon
from ...model.flowchart import Box, DrawEvent, Flowchart, FlowLayout, MeasuredNode, MermaidError, Point, RenderResult
from ..labels import measure_node


class CanvasSession:
    """One calling thread owns all Canvas/Context instances in this session.

    auto retains the Canvas default; cpu uses its public GPU setter; gpu verifies
    that the actual selected renderer is GPU and never accepts a CPU fallback.
    No native handles are returned or put into render results/trace.
    """

    def __init__(self, backend: str = "auto"):
        if backend not in {"auto", "cpu", "gpu"}:
            raise MermaidError("backend must be auto, cpu or gpu", code="INVALID_BACKEND")
        from py_skia_canvas import Canvas, __version__
        if __version__ != "0.1.0a18":
            raise MermaidError(f"Expected py-skia-canvas 0.1.0a18, found {__version__}", code="DEPENDENCY_VERSION")
        self._owner = threading.get_ident()
        self._backend = backend
        self._canvas_factory = Canvas
        self._measure_canvas = self._new_canvas(1, 1)
        self._context = self._measure_canvas.getContext("2d")
        self.trace: tuple[DrawEvent, ...] = ()

    def _check_owner(self) -> None:
        if threading.get_ident() != self._owner:
            raise MermaidError("CanvasSession must be used on its creating thread", code="THREAD_OWNERSHIP")

    def _new_canvas(self, width: int, height: int):
        self._check_owner()
        canvas = self._canvas_factory(width, height)
        if self._backend == "cpu":
            canvas.gpu = False
        if self._backend == "gpu" and canvas.engine.get("renderer") != "GPU":
            raise MermaidError("GPU required but Canvas selected a CPU renderer", code="GPU_UNAVAILABLE")
        return canvas

    @staticmethod
    def _text_state(context, diagram: Flowchart) -> None:
        config = diagram.config
        # Mermaid's CSS declaration default includes a trailing semicolon;
        # Canvas.font accepts the font value rather than a CSS declaration.
        family = config.font_family.rstrip().removesuffix(";").rstrip()
        context.font = f"{config.font_size:g}px {family}"
        context.textAlign = "center"
        context.textBaseline = "alphabetic"
        context.direction = "ltr"
        context.textWrap = False

    def measure(self, diagram: Flowchart) -> tuple[MeasuredNode, ...]:
        self._check_owner()
        self._text_state(self._context, diagram)
        return tuple(measure_node(node, diagram.config, self._context.measureText) for node in diagram.nodes)

    @staticmethod
    def _arrow(points: tuple[Point, ...]) -> tuple[Point, Point, Point]:
        try:
            return arrow_polygon(points, length=10, width=10)
        except ValueError as error:
            raise MermaidError("Edge has no nonzero terminal route segment", code="INVALID_LAYOUT") from error

    def render(self, diagram: Flowchart, measured: tuple[MeasuredNode, ...], layout: FlowLayout) -> RenderResult:
        self._check_owner()
        self.trace = ()
        node_ids = tuple(node.id for node in diagram.nodes)
        edge_ids = tuple(edge.id for edge in diagram.edges)
        if not node_ids:
            raise MermaidError("F01.1 requires at least one node", code="EMPTY_DIAGRAM")
        if (len(set(node_ids)) != len(node_ids)
                or len(measured) != len(node_ids) or {node.id for node in measured} != set(node_ids)
                or len(layout.nodes) != len(node_ids) or {node.id for node in layout.nodes} != set(node_ids)
                or len(layout.edges) != len(edge_ids) or {edge.id for edge in layout.edges} != set(edge_ids)):
            raise MermaidError("Layout/measurement identities do not match the diagram", code="INVALID_LAYOUT")
        sizes = {node.id: node for node in measured}
        boxes = {node.id: node.box for node in layout.nodes}
        routes = {edge.id: edge.sections for edge in layout.edges}
        coordinates = []
        arrows = {}
        for node in layout.nodes:
            box = node.box
            size = sizes[node.id]
            if (box.width < size.width - 1e-5 or box.height < size.height - 1e-5):
                raise MermaidError("Placed node is smaller than its measured content", code="INVALID_LAYOUT")
            half_stroke = diagram.config.node_stroke_width / 2
            coordinates.extend(((box.x - half_stroke, box.y - half_stroke),
                                (box.x + box.width + half_stroke, box.y + box.height + half_stroke)))
            if diagram.config.shadow_opacity:
                sx, sy = diagram.config.shadow_offset_x, diagram.config.shadow_offset_y
                coordinates.extend(((box.x + sx - half_stroke, box.y + sy - half_stroke),
                                    (box.x + box.width + sx + half_stroke,
                                     box.y + box.height + sy + half_stroke)))
        for edge in diagram.edges:
            sections = routes[edge.id]
            if not sections:
                raise MermaidError("Edge route is missing", code="INVALID_LAYOUT", span=edge.span)
            for section in sections:
                coordinates.extend((point.x, point.y) for point in (section.start, *section.bends, section.end))
            last = sections[-1]
            arrow = self._arrow((last.start, *last.bends, last.end))
            arrows[edge.id] = arrow
            coordinates.extend((point.x, point.y) for point in arrow)
        if any(not math.isfinite(value) for pair in coordinates for value in pair):
            raise MermaidError("Layout contains non-finite geometry", code="INVALID_LAYOUT")
        padding = diagram.config.diagram_padding
        route_margin = diagram.config.edge_stroke_width / 2
        left = min(x for x, _ in coordinates) - route_margin
        top = min(y for _, y in coordinates) - route_margin
        right = max(x for x, _ in coordinates) + route_margin
        bottom = max(y for _, y in coordinates) + route_margin
        width = max(1, math.ceil(right - left + 2 * padding))
        height = max(1, math.ceil(bottom - top + 2 * padding))
        if width > 32768 or height > 32768 or width * height > 64_000_000:
            raise MermaidError("PNG dimensions exceed the F01.1 render budget", code="RENDER_BUDGET")
        tx, ty = padding - left, padding - top
        canvas = self._new_canvas(width, height)
        context = canvas.getContext("2d")
        self._text_state(context, diagram)
        context.fillStyle = diagram.config.background
        context.fillRect(0, 0, width, height)
        context.translate(tx, ty)
        trace = [DrawEvent("viewport", "", Box(0, 0, width, height))]
        context.strokeStyle = diagram.config.edge_color
        context.fillStyle = diagram.config.edge_color
        context.lineWidth = diagram.config.edge_stroke_width
        context.lineJoin = "round"
        for edge in diagram.edges:
            for section in routes[edge.id]:
                points = (section.start, *section.bends, section.end)
                context.beginPath()
                context.moveTo(points[0].x, points[0].y)
                for point in points[1:]:
                    context.lineTo(point.x, point.y)
                context.stroke()
                trace.append(DrawEvent("edge", edge.id,
                                       points=tuple(Point(point.x + tx, point.y + ty) for point in points)))
            arrow = arrows[edge.id]
            context.beginPath()
            context.moveTo(arrow[0].x, arrow[0].y)
            context.lineTo(arrow[1].x, arrow[1].y)
            context.lineTo(arrow[2].x, arrow[2].y)
            context.closePath()
            context.fill()
            trace.append(DrawEvent("arrow", edge.id,
                                   points=tuple(Point(point.x + tx, point.y + ty) for point in arrow)))
        for node in diagram.nodes:
            box, size = boxes[node.id], sizes[node.id]
            if diagram.config.shadow_opacity:
                half_stroke = diagram.config.node_stroke_width / 2
                shadow_box = Box(box.x + diagram.config.shadow_offset_x - half_stroke,
                                 box.y + diagram.config.shadow_offset_y - half_stroke,
                                 box.width + 2 * half_stroke, box.height + 2 * half_stroke)
                # SVG feDropShadow(stdDeviation=0) filters the combined opaque
                # fill+stroke silhouette. A translated outer rectangle expresses
                # that silhouette once, avoiding doubled alpha at the border.
                context.fillStyle = f"rgba(0, 0, 0, {diagram.config.shadow_opacity:g})"
                context.fillRect(shadow_box.x, shadow_box.y, shadow_box.width, shadow_box.height)
                trace.append(DrawEvent("shadow", node.id,
                                       Box(shadow_box.x + tx, shadow_box.y + ty,
                                           shadow_box.width, shadow_box.height)))
            context.fillStyle = diagram.config.fill
            context.strokeStyle = diagram.config.stroke
            context.lineWidth = diagram.config.node_stroke_width
            context.fillRect(box.x, box.y, box.width, box.height)
            context.strokeRect(box.x, box.y, box.width, box.height)
            trace.append(DrawEvent("node", node.id, Box(box.x + tx, box.y + ty, box.width, box.height)))
            row_height = size.label_height / len(size.lines)
            label_top = box.y + (box.height - size.label_height) / 2
            context.fillStyle = diagram.config.text_color
            for index, line in enumerate(size.lines):
                x = box.x + box.width / 2
                baseline = label_top + (index + .5) * row_height + (line.ascent - line.descent) / 2
                context.fillText(line.text, x, baseline)
                trace.append(DrawEvent("text", node.id,
                                       Box(x + tx - line.width / 2, baseline + ty - line.ascent,
                                           line.width, line.ascent + line.descent), line.text,
                                       (Point(x + tx, baseline + ty),)))
        data = bytes(canvas.toBufferSync("png"))
        backend = tuple((str(key), str(value)) for key, value in sorted(canvas.engine.items()))
        self.trace = tuple(trace)
        return RenderResult(data, width, height, "image/png", diagram, measured, layout, backend, trace=self.trace)
