"""F01.1 pure value contracts; logical px, top-left coordinates, no native objects."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SourcePosition:
    index: int
    utf16_offset: int
    line: int  # 1-based
    column: int  # 0-based UTF-16 units


@dataclass(frozen=True)
class SourceSpan:
    start: SourcePosition
    end: SourcePosition  # exclusive


class MermaidError(ValueError):
    """Explicit input, configuration, engine or owner error with optional location."""

    def __init__(self, message: str, *, code: str = "MERMAID_ERROR", span: SourceSpan | None = None):
        self.code = code
        self.span = span
        super().__init__(message)


@dataclass(frozen=True)
class FlowConfig:
    # Concrete source-derived defaults are supplied by config.resolve_config.
    font_family: str
    font_size: float
    node_padding: float
    diagram_padding: float
    node_spacing: float
    rank_spacing: float
    fill: str
    stroke: str
    text_color: str
    edge_color: str
    background: str
    line_height: float
    html_labels: bool
    max_text_size: int
    max_edges: int
    layout: str = "elk"
    theme: str = "redux-color"
    look: str = "neo"
    padding_x: float = 16.0
    padding_y: float = 12.0
    min_node_width: float = 120.0
    wrapping_width: float = 120.0
    node_stroke_width: float = 2.0
    edge_stroke_width: float = 2.0
    shadow_offset_x: float = 4.0
    shadow_offset_y: float = 4.0
    shadow_opacity: float = 0.06
    site_font_family: str = '"trebuchet ms", verdana, arial, sans-serif;'
    site_font_size: float = 16.0


@dataclass(frozen=True)
class FlowNode:
    id: str
    label: str
    span: SourceSpan


@dataclass(frozen=True)
class FlowEdge:
    id: str
    source: str
    target: str
    span: SourceSpan


@dataclass(frozen=True)
class Flowchart:
    source: str
    direction: Literal["TD", "LR"]
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]
    config: FlowConfig
    diagram_type: str = "flowchart-v2"


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class MeasuredLine:
    text: str
    width: float
    ascent: float
    descent: float


@dataclass(frozen=True)
class MeasuredNode:
    id: str
    width: float
    height: float
    label_width: float
    label_height: float
    lines: tuple[MeasuredLine, ...]


@dataclass(frozen=True)
class PlacedNode:
    id: str
    box: Box


@dataclass(frozen=True)
class EdgeSection:
    start: Point
    bends: tuple[Point, ...]
    end: Point


@dataclass(frozen=True)
class RoutedEdge:
    id: str
    sections: tuple[EdgeSection, ...]


@dataclass(frozen=True)
class FlowLayout:
    nodes: tuple[PlacedNode, ...]
    edges: tuple[RoutedEdge, ...]
    width: float
    height: float
    engine: str
    engine_version: str


@dataclass(frozen=True)
class DrawEvent:
    kind: str
    semantic_id: str
    box: Box | None = None
    text: str | None = None
    points: tuple[Point, ...] = ()


@dataclass(frozen=True)
class RenderResult:
    data: bytes
    width: int
    height: int
    mime: str
    diagram: Flowchart
    measured: tuple[MeasuredNode, ...]
    layout: FlowLayout
    backend: tuple[tuple[str, str], ...]
    diagnostics: tuple[str, ...] = ()
    trace: tuple[DrawEvent, ...] = ()
