"""Flowchart pure value contracts; logical px, top-left coordinates, no native objects."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from .controls import ControlLayout


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
class SourceDocument:
    """Preprocessed value data; cleaned boundaries map to raw Python indices."""
    raw: str
    normalized: str = ""
    with_comments: str = ""
    cleaned: str = ""
    processed_to_raw: tuple[int, ...] = ()  # len(cleaned)+1, half-open boundaries
    frontmatter_line_offset: int = 0
    title: str = ""
    config_layers: tuple[tuple[str, object], ...] = ()  # recursively frozen tuples/scalars
    diagnostics: tuple[str, ...] = ()


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
    inherit_direction: bool = False
    round_radius: float = 12.0
    edge_label_background: str = "#cccccc"
    edge_label_wrapping_width: float = 200.0
    group_padding: float = 8.0
    group_title_top_margin: float = 0.0
    group_title_bottom_margin: float = 0.0
    group_stroke_width: float = 1.0
    group_borders: tuple[str, ...] = ("#E879F9", "#2DD4BF", "#FB923C", "#22D3EE", "#4ADE80", "#A78BFA", "#F87171", "#FACC15", "#818CF8", "#A3E635", "#38BDF8", "#FB7185")
    group_fills: tuple[str, ...] = ("#FDF4FF", "#F0FDFA", "#FFF7ED", "#ECFEFF", "#F0FDF4", "#F5F3FF", "#FEF2F2", "#FEFCE8", "#EEF2FF", "#F7FEE7", "#F0F9FF", "#FFF1F2")
    security_level: str = "strict"
    markdown_auto_wrap: bool = True
    theme_variables: tuple[tuple[str, object], ...] = ()
    theme_css: str = ""
    title_top_margin: float = 25.0
    config_layers: tuple[tuple[str, object], ...] = ()
    dompurify_config: tuple[tuple[str, object], ...] = ()
    dompurify_provided: bool = False
    curve: str = "basis"
    elk_options: tuple[tuple[str, object], ...] = ()
    hand_drawn_seed: int | float = 0
    deterministic_ids: bool = False
    deterministic_id_seed: str | None = None


@dataclass(frozen=True)
class FlowNode:
    id: str
    label: str
    span: SourceSpan
    shape: str = "square"
    parent_id: str | None = None
    label_kind: str = "text"
    raw_label: str | None = None
    label_span: SourceSpan | None = None
    classes: tuple[str, ...] = ()
    styles: tuple[str, ...] = ()
    metadata: tuple[tuple[str, object], ...] = ()
    props: tuple[tuple[str, object], ...] = ()
    color_index: int | None = None


@dataclass(frozen=True)
class FlowEdge:
    id: str
    source: str
    target: str
    span: SourceSpan
    label: str = ""
    label_span: SourceSpan | None = None
    label_kind: str = "text"
    raw_label: str | None = None
    source_id: str | None = None
    is_user_defined_id: bool = False
    marker_start: str = "none"
    marker_end: str = "point"
    stroke: str = "normal"
    min_length: int | None = 1
    curve: str | None = None
    classes: tuple[str, ...] = ()
    styles: tuple[str, ...] = ()
    animate: bool = False
    animation: str | None = None
    metadata: tuple[tuple[str, object], ...] = ()
    edge_type: str = "arrow_point"


@dataclass(frozen=True)
class FlowGroup:
    id: str
    label: str
    span: SourceSpan
    members: tuple[str, ...] = ()
    parent_id: str | None = None
    direction: Literal["TD", "TB", "LR", "RL", "BT"] | None = None
    color_index: int = 0
    label_kind: str = "text"
    raw_label: str | None = None
    label_span: SourceSpan | None = None
    classes: tuple[str, ...] = ()
    styles: tuple[str, ...] = ()
    metadata: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True)
class ClassDefinition:
    name: str
    styles: tuple[str, ...] = ()
    text_styles: tuple[str, ...] = ()


FlowClassDefinition = ClassDefinition


@dataclass(frozen=True)
class Flowchart:
    source: str
    direction: Literal["TD", "TB", "LR", "RL", "BT"]
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]
    config: FlowConfig
    diagram_type: str = "flowchart-v2"
    groups: tuple[FlowGroup, ...] = ()
    title: str = ""
    acc_title: str = ""
    acc_description: str = ""
    source_document: SourceDocument | None = None
    class_definitions: tuple[ClassDefinition, ...] = ()
    default_edge_styles: tuple[str, ...] = ()
    default_edge_curve: str | None = None


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
class ResolvedStyle:
    """Canvas-applicable paint and text intent, with no CSS/native objects."""
    fill: str = "#ffffff"
    stroke: str = "#28253D"
    text_color: str = "#28253D"
    stroke_width: float = 2.0
    font_family: str = '"Recursive Variable", arial, sans-serif'
    font_size: float = 14.0
    line_height: float = 1.5
    font_weight: str = "normal"
    font_style: str = "normal"
    decoration: str = ""
    background: str = "transparent"
    text_align: str = "center"
    white_space: str = "normal"
    display: str = "inline"
    text_anchor: str = "middle"
    line_height_px: float | None = None
    custom_properties: tuple[tuple[str, str], ...] = ()
    current_color: str | None = None
    direction: str = "ltr"
    stroke_gradient: tuple[tuple[float, str], ...] = ()
    shadow_dx: float = 4.0
    shadow_dy: float = 4.0
    shadow_blur: float = 0.0
    shadow_color: str = "#000000"
    important_properties: tuple[str, ...] = ()
    opacity: float = 1.0
    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0
    dash: tuple[float, ...] = ()
    shadow_opacity: float = 0.06
    line_cap: str = "butt"
    line_join: str = "miter"
    dash_offset: float = 0.0
    letter_spacing: str = '0px'
    word_spacing: str = '0px'
    text_transform: str = 'none'
    overflow_wrap: str = 'normal'
    word_break: str = 'normal'
    hyphens: str = 'manual'
    text_shadows: tuple[tuple[float, float, float, str], ...] = ()
    hachure_color: str | None = None  # Actual fill-stroke when source CSS overrides a rough hatch.
    fill_gradient: tuple[tuple[float, str], ...] = ()
    gradient_direction: tuple[float, float, float, float] = (0, 0, 1, 0)
    blend_mode: str = 'source-over'
    text_stroke_color: str = ''
    text_stroke_width: float = 0
    paint_context: tuple[tuple[str, tuple[str, ...], str], ...] = ()
    fill_gradient_direction: tuple[float, float, float, float] | None = None
    stroke_gradient_direction: tuple[float, float, float, float] | None = None
    brightness: float = 1.0
    filter_chain: tuple[str, ...] = ()  # Ordered explicit static CSS filter winner.
    max_width: float | None = None
    visibility: str = 'visible'

    @property
    def paint_opacity(self) -> float:
        # visibility inherits and can be restored by a descendant; opacity is
        # ancestor compositing and cannot. Keep both values through the cascade.
        return self.opacity if self.visibility == 'visible' else 0.0


@dataclass(frozen=True)
class MeasuredTextRun:
    """Label-local left-aligned draw origin/advance, baseline and visible ink."""
    text: str
    x: float
    baseline: float
    width: float  # Canvas advance; ink can overhang it
    ascent: float
    descent: float
    font_family: str
    font_size: float
    font_weight: str = "normal"
    font_style: str = "normal"
    color: str = ""
    decoration: str = ""
    background: str = ""
    ink_left: float = 0.0
    ink_right: float = 0.0
    opacity: float = 1.0
    direction: str = "ltr"
    kind: str = "text"
    asset_id: str = ""
    asset_box: Box | None = None
    letter_spacing: str = '0px'
    word_spacing: str = '0px'
    text_shadows: tuple[tuple[float, float, float, str], ...] = ()
    math_key: str = ""  # Session cache key for an immutable py-katex MathBox.
    blend_mode: str = 'source-over'
    text_stroke_color: str = ''
    text_stroke_width: float = 0
    brightness: float = 1.0
    filter_chain: tuple[str, ...] = ()
    filter_shadow: tuple[float, float, float] | None = None  # Bounds footprint dx/dy/blur.
    control: ControlLayout | None = None  # Immutable measured static HTML control.


@dataclass(frozen=True)
class ShapePart:
    path: str
    fill: str = "none"  # none/node/stroke/white or a literal paint value
    stroke: str = "node"  # none/node/fill or literal; fill uses node fill color
    opacity: float = 1.0
    fill_style: str = 'hachure'  # RoughJS handler override; solid keeps a filled tag/disk.
    dash: tuple[float, ...] | None = None  # None inherits node stroke; explicit tuples override.
    css_classes: tuple[str, ...] = ()  # Actual source child-element classes, not node classes.
    tag: str = 'path'  # Source primitive for direct-child CSS; geometry remains a pure path.
    stroke_width: float | None = None  # None inherits legacy part width.


@dataclass(frozen=True)
class MeasuredAsset:
    resource_id: str
    box: Box  # node-local, immutable logical coordinates
    kind: str = "image"
    fit: str = "contain"
    opacity: float = 1.0


@dataclass(frozen=True)
class MeasuredNode:
    id: str
    width: float
    height: float
    label_width: float
    label_height: float
    lines: tuple[MeasuredLine, ...]
    label_box: Box | None = None  # node-local box; supports asymmetric shapes
    outline: str = ""  # pure SVG path value; only Canvas adapter creates Path2D
    details: tuple[str, ...] = ()
    runs: tuple[MeasuredTextRun, ...] = ()
    parts: tuple[ShapePart, ...] = ()
    assets: tuple[MeasuredAsset, ...] = ()
    paint_outline: bool = True  # False for a virtual attachment box painted via parts.


@dataclass(frozen=True)
class MeasuredGroup:
    id: str
    label_width: float
    label_height: float
    lines: tuple[MeasuredLine, ...]
    runs: tuple[MeasuredTextRun, ...] = ()


@dataclass(frozen=True)
class MeasuredEdgeLabel:
    id: str  # semantic edge ID, separate from node/group ID namespaces
    width: float
    height: float
    lines: tuple[MeasuredLine, ...]
    runs: tuple[MeasuredTextRun, ...] = ()


@dataclass(frozen=True)
class MeasuredTitle:
    width: float
    height: float
    ascent: float
    descent: float
    lines: tuple[MeasuredLine, ...] = ()
    runs: tuple[MeasuredTextRun, ...] = ()
    text_anchor: str = "middle"


@dataclass(frozen=True)
class MeasuredAnnotations:
    groups: tuple[MeasuredGroup, ...] = ()
    edge_labels: tuple[MeasuredEdgeLabel, ...] = ()
    title: MeasuredTitle | None = None
    title_suppressed: bool = False


@dataclass(frozen=True)
class PlacedNode:
    id: str
    box: Box
    paint_box: Box | None = None  # Fixed-source small-node anchor alignment; raw engine box stays intact.


@dataclass(frozen=True)
class EdgeSection:
    start: Point
    bends: tuple[Point, ...]
    end: Point


@dataclass(frozen=True)
class RoutedEdge:
    id: str
    sections: tuple[EdgeSection, ...]
    paint_points: tuple[Point, ...] = ()
    effective_curve: str = "rounded"
    path: str = ""
    paint_bounds: Box | None = None


@dataclass(frozen=True)
class PlacedGroup:
    id: str
    box: Box
    parent_id: str | None = None
    engine_origin: Point | None = None
    title_box: Box | None = None
    paint_box: Box | None = None  # Same source anchor alignment; engine_origin remains raw.


@dataclass(frozen=True)
class PlacedEdgeLabel:
    id: str
    box: Box


@dataclass(frozen=True)
class FlowLayout:
    nodes: tuple[PlacedNode, ...]
    edges: tuple[RoutedEdge, ...]
    width: float
    height: float
    engine: str
    engine_version: str
    groups: tuple[PlacedGroup, ...] = ()
    edge_labels: tuple[PlacedEdgeLabel, ...] = ()
    title_box: Box | None = None


@dataclass(frozen=True)
class DrawEvent:
    kind: str
    semantic_id: str
    box: Box | None = None
    text: str | None = None
    points: tuple[Point, ...] = ()
    font_family: str | None = None
    font_size: float | None = None
    font_weight: str | None = None
    font_style: str | None = None
    color: str | None = None
    fill: str | None = None
    stroke: str | None = None
    stroke_width: float | None = None
    opacity: float = 1.0
    path: str = ""
    curve: str | None = None
    marker: str | None = None
    resource_id: str | None = None
    clip: Box | None = None
    brightness: float = 1.0
    filter_chain: tuple[str, ...] = ()
    blend_mode: str = 'source-over'
    dash: tuple[float, ...] = ()
    control_id: str | None = None  # Static markup identity for real control paints.


@dataclass(frozen=True)
class ImageResource:
    id: str
    data: bytes
    mime: str = ""
    sha256: str = ""


@dataclass(frozen=True)
class IconResource:
    id: str
    svg: str
    sha256: str = ""


@dataclass(frozen=True)
class FontResource:
    family: str
    path: str
    sha256: str = ""


@dataclass(frozen=True)
class ResourceBundle:
    images: tuple[ImageResource, ...] = ()
    icons: tuple[IconResource, ...] = ()
    fonts: tuple[FontResource, ...] = ()


@dataclass(frozen=True)
class ExportOptions:
    quality: float = 0.92
    density: int = 1
    matte: str | None = None
    outline: bool = False
    downsample: bool = False


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
    annotations: MeasuredAnnotations = MeasuredAnnotations()
