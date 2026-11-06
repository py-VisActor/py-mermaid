"""Source: createText.ts and squareRect.ts/drawRect.ts; no native ownership."""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import replace
from collections.abc import Callable
from typing import Any

from ...model.flowchart import FlowConfig, FlowNode, MeasuredLine, MeasuredNode, MermaidError
from ...geometry.shapes import shape_geometry


def _metric(metrics: Any, name: str, default: float = 0.0) -> float:
    value = getattr(metrics, name, default)
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise MermaidError(f"Canvas returned invalid text metric {name}", code="INVALID_MEASUREMENT")
    return float(value)


def _wrapped_lines(text: str, config: FlowConfig, measure_text: Callable[[str], Any]) -> list[str]:
    """Preserve text while wrapping at spaces and CJK opportunities.

    The source HTML branch uses break-spaces at wrappingWidth; a Latin word
    without a break opportunity may overflow that nominal width. We keep that
    word intact and include its actual ink in the measured box. The non-HTML
    splitText.ts branch also splits long words by Unicode code point.
    """
    output = []
    for explicit_line in text.split("\n"):
        tokens = []
        current = ""
        for character in explicit_line:
            if unicodedata.east_asian_width(character) in {"W", "F"}:
                if current:
                    tokens.append(current)
                    current = ""
                tokens.append(character)
            else:
                current += character
                if character.isspace():
                    tokens.append(current)
                    current = ""
        if current:
            tokens.append(current)
        line = ""
        for token in tokens:
            if line and _metric(measure_text(line + token), "width") > config.wrapping_width:
                output.append(line)
                line = ""
            if not config.html_labels and _metric(measure_text(token), "width") > config.wrapping_width:
                for character in token:
                    if line and _metric(measure_text(line + character), "width") > config.wrapping_width:
                        output.append(line)
                        line = ""
                    line += character
            else:
                line += token
        output.append(line)
    return output


def measure_plain_label(text: str, config: FlowConfig, measure_text: Callable[[str], Any], *,
                        wrapping_width: float | None = None, min_width: float = 0) -> tuple[float, float, tuple[MeasuredLine, ...]]:
    """Measure plain node/edge/group content with explicit width policy."""
    if re.search(r"<[^>]*>|`|\$\$", text):
        raise MermaidError("Rich labels are outside F01.2", code="UNSUPPORTED_SYNTAX")
    if wrapping_width is not None:
        config = replace(config, wrapping_width=wrapping_width)
    lines = []
    for line_text in _wrapped_lines(text, config, measure_text):
        metrics = measure_text(line_text)
        advance = _metric(metrics, "width")
        ink = _metric(metrics, "actualBoundingBoxLeft") + _metric(metrics, "actualBoundingBoxRight")
        ascent = max(0.0, _metric(metrics, "actualBoundingBoxAscent"))
        descent = max(0.0, _metric(metrics, "actualBoundingBoxDescent"))
        if ascent + descent == 0:
            ascent = max(0.0, _metric(metrics, "fontBoundingBoxAscent"))
            descent = max(0.0, _metric(metrics, "fontBoundingBoxDescent"))
        lines.append(MeasuredLine(line_text, max(0.0, advance, ink), ascent, descent))
    label_width = max(max(line.width for line in lines), min_width if text else 0)
    row_height = max(config.font_size * config.line_height, *(line.ascent + line.descent for line in lines))
    label_height = row_height * len(lines)
    return label_width, label_height, tuple(lines)


def measure_node(node: FlowNode, config: FlowConfig, measure_text: Callable[[str], Any]) -> MeasuredNode:
    """Retain source shape-specific sizing; circles do not get minNodeWidth."""
    try:
        lw, lh, lines = measure_plain_label(node.label, config, measure_text,
                                           min_width=0 if node.shape in {"circle", "doublecircle"} else config.min_node_width)
        geometry = shape_geometry(node.shape, lw, lh, config)
    except MermaidError as error:
        if error.span is None:
            error.span = node.span
        raise
    return MeasuredNode(node.id, geometry.width, geometry.height, lw, lh, lines,
                        geometry.label_box, geometry.outline, geometry.details)
