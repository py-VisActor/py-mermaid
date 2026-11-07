"""Immutable initial-state controls and native painting intent; no host objects."""
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .flowchart import MeasuredTextRun


@dataclass(frozen=True)
class ControlOption:
    label: str
    value: str = ''
    selected: bool = False
    disabled: bool = False
    group: str = ''


@dataclass(frozen=True)
class ControlSpec:
    tag: str
    input_type: str = ''
    attributes: tuple[tuple[str, str], ...] = ()
    text: str = ''
    inner_markup: str = ''
    options: tuple[ControlOption, ...] = ()
    disabled: bool = False
    readonly: bool = False
    checked: bool = False
    multiple: bool = False
    selected_indices: tuple[int, ...] = ()
    value: str = ''
    minimum: float = 0
    maximum: float = 1
    fraction: float | None = None
    hidden: bool = False
    legend_text: str = ''
    legend_markup: str = ''

    def attr(self, name: str, default: str = '') -> str:
        return dict(self.attributes).get(name, default)


@dataclass(frozen=True)
class ControlPaint:
    """Control-local public Canvas primitive; lengths are CSS pixels."""
    kind: str
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    fill: str = ''
    stroke: str = ''
    line_width: float = 1
    radius: float = 0
    path: str = ''
    text: str = ''
    font_family: str = 'Arial, sans-serif'
    font_size: float = 13.333333333333334
    font_weight: str = 'normal'
    font_style: str = 'normal'
    resource_id: str = ''
    direction: str = 'ltr'
    decoration: str = ''
    letter_spacing: str = '0px'
    word_spacing: str = '0px'
    text_shadows: tuple[tuple[float, float, float, str], ...] = ()
    text_stroke_color: str = ''
    text_stroke_width: float = 0


@dataclass(frozen=True)
class ControlLayout:
    spec: ControlSpec
    width: float
    height: float
    baseline: float
    paints: tuple[ControlPaint, ...] = ()
    content_runs: tuple[MeasuredTextRun, ...] = ()
    content_offset: tuple[float, float] = (0, 0)
    clip: tuple[float, float, float, float] | None = None
    caption_runs: tuple[MeasuredTextRun, ...] = ()
    caption_offset: tuple[float, float] = (0, 0)
