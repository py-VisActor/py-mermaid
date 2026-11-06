"""Pure diagram-family and display-list contracts; no native allocations."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .flowchart import SourceDocument, MeasuredTextRun, DrawEvent, Box, Flowchart, FlowLayout, MeasuredNode, MeasuredAnnotations


@dataclass(frozen=True)
class Diagram:
    kind: str
    source: SourceDocument
    config: tuple[tuple[str, object], ...]
    model: object
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class TextBox:
    text: str
    width: float
    height: float
    ascent: float
    descent: float
    runs: tuple[MeasuredTextRun, ...] = ()


@dataclass(frozen=True)
class Paint:
    kind: str
    values: tuple[Any, ...]
    style: tuple[tuple[str, Any], ...] = ()
    semantic_id: str = ''
    role: str = 'shape'
    bounds: Box | None = None


@dataclass(frozen=True)
class Scene:
    commands: tuple[Paint, ...]
    width: float
    height: float
    origin_x: float = 0
    origin_y: float = 0
    background: str = 'white'
    layout: object = None
    measured: tuple = ()
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class FlowchartScene:
    """A source-sanctioned flowchart renderer with a dedicated layout provider."""
    flowchart: Flowchart
    layout: FlowLayout
    measured: tuple[MeasuredNode, ...]
    annotations: MeasuredAnnotations
    group_overrides: tuple[tuple[str, tuple[Paint, ...]], ...] = ()


@dataclass(frozen=True)
class DiagramRenderResult:
    data: bytes
    width: int
    height: int
    mime: str
    diagram: Diagram
    measured: tuple
    layout: object
    backend: tuple[tuple[str, str], ...]
    diagnostics: tuple[str, ...] = ()
    trace: tuple[DrawEvent, ...] = ()
    annotations: object = None
