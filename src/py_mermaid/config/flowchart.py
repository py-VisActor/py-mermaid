"""F01.1 configuration; see references/f011-parser-sources.json for provenance.

This is deliberately an explicit slice, not a replacement for the full Mermaid
schema. Unknown options fail rather than being accepted and silently ignored.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

from py_mermaid.model.flowchart import FlowConfig, MermaidError

_ROOT_KEYS = frozenset({"fontFamily", "fontSize", "htmlLabels", "maxTextSize", "maxEdges",
                        "layout", "theme", "look", "flowchart"})
_FLOW_KEYS = frozenset({"padding", "diagramPadding", "nodeSpacing", "rankSpacing",
                        "minNodeWidth", "wrappingWidth", "htmlLabels", "layout", "theme", "look"})


def _mapping(value: object, name: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise MermaidError(f"{name} must be a mapping", code="INVALID_CONFIG")
    return value


def _keys(data: Mapping, allowed: frozenset[str], name: str) -> None:
    for key in data:
        if key not in allowed:
            raise MermaidError(f"F01.1 does not support configuration {name}{key}",
                               code="UNSUPPORTED_CONFIG")


def _number(value: object, name: str, *, minimum: float = 0, integer: bool = False) -> float:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < minimum
            or (integer and int(value) != value)):
        raise MermaidError(f"{name} must be a finite {'integer' if integer else 'number'} >= {minimum}",
                           code="INVALID_CONFIG")
    return float(value)


def resolve_config(config: Mapping | None = None) -> FlowConfig:
    """Resolve the supported site configuration without mutation or global state.

    Effective defaults follow config.ts's diagram scope: the flowchart schema's
    redux-color/neo overrides global default/classic and rebuilds theme variables.
    mermaidAPI.initialize bridges an explicit site fontFamily into theme variables;
    it does not bridge fontSize. Both original site values are retained separately.
    Global htmlLabels takes precedence; absence/null uses deprecated per-diagram
    htmlLabels and ultimately true, as config.ts:getEffectiveHtmlLabels specifies.
    """
    root = {} if config is None else _mapping(config, "config")
    _keys(root, _ROOT_KEYS, "")
    flow = _mapping(root.get("flowchart", {}), "flowchart")
    _keys(flow, _FLOW_KEYS, "flowchart.")
    for key, supported in (("theme", "redux-color"), ("look", "neo"), ("layout", "elk")):
        for layer in (root, flow):
            if key in layer and layer[key] != supported:
                raise MermaidError(f"F01.1 supports only {key}={supported!r}",
                                   code="UNSUPPORTED_CONFIG")
    html = root.get("htmlLabels")
    if html is None:
        html = flow.get("htmlLabels")
    if html is None:
        html = True
    if not isinstance(html, bool):
        raise MermaidError("htmlLabels must be boolean or null", code="INVALID_CONFIG")
    family = root.get("fontFamily", '"trebuchet ms", verdana, arial, sans-serif;')
    if not isinstance(family, str) or not family.strip() or any(c in family for c in "\r\n{}<>"):
        raise MermaidError("fontFamily must be a nonempty font-family string", code="INVALID_CONFIG")
    site_font_size = _number(root.get("fontSize", 16), "fontSize", minimum=0.01)
    effective_family = family if "fontFamily" in root else '"Recursive Variable", arial, sans-serif'
    return FlowConfig(
        font_family=effective_family, font_size=14.0,
        node_padding=_number(flow.get("padding", 15), "flowchart.padding"),
        diagram_padding=_number(flow.get("diagramPadding", 8), "flowchart.diagramPadding"),
        node_spacing=_number(flow.get("nodeSpacing", 50), "flowchart.nodeSpacing", integer=True),
        rank_spacing=_number(flow.get("rankSpacing", 50), "flowchart.rankSpacing", integer=True),
        fill="#ffffff", stroke="#28253D", text_color="#28253D", edge_color="#000000",
        background="#ffffff", line_height=1.5 if html else 1.1, html_labels=html,
        max_text_size=int(_number(root.get("maxTextSize", 50000), "maxTextSize", integer=True)),
        max_edges=int(_number(root.get("maxEdges", 500), "maxEdges", integer=True)),
        theme="redux-color", look="neo", padding_x=16.0, padding_y=12.0,
        min_node_width=_number(flow.get("minNodeWidth", 120), "flowchart.minNodeWidth"),
        wrapping_width=_number(flow.get("wrappingWidth", 120), "flowchart.wrappingWidth"),
        node_stroke_width=2.0, edge_stroke_width=2.0,
        shadow_offset_x=4.0, shadow_offset_y=4.0, shadow_opacity=0.06,
        site_font_family=family, site_font_size=site_font_size,
    )
