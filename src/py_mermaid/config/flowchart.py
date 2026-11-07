"""Source-derived F01.3 config layers, sanitation and flowchart appearance."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
import math
import re
import json
from importlib.resources import files
from py_mermaid.model.flowchart import FlowConfig, MermaidError
from .values import assign_with_depth, freeze_value, thaw_value, merge_layers
from .themes import THEMES, get_theme_variables
from .source_keys import CONFIG_KEYS
from .elk import LAYOUTS, CURVES, DEFAULTS as ELK_DEFAULTS, validate_elk

_ROOT_KEYS = frozenset({"fontFamily", "fontSize", "fontWeight", "htmlLabels", "maxTextSize", "maxEdges", "layout", "theme", "look", "flowchart",
    "themeVariables", "themeCSS", "securityLevel", "secure", "dompurifyConfig", "markdownAutoWrap", "wrap", "altFontFamily",
    "darkMode", "logLevel", "startOnLoad", "suppressErrorRendering", "elk", "handDrawnSeed",
    "deterministicIds", "deterministicIDSeed", "arrowMarkerAbsolute"})
# setSiteConfig accepts the declared global config, even when this diagram
# consumes only its own section. Do not reject another kind's valid settings.
_ROOT_KEYS |= frozenset(json.loads(files('py_mermaid').joinpath('data/diagram_defaults.json').read_text('utf-8'))['config'])
_FLOW_KEYS = frozenset({"padding", "diagramPadding", "nodeSpacing", "rankSpacing", "minNodeWidth", "wrappingWidth", "htmlLabels",
    "layout", "theme", "look", "inheritDir", "subGraphTitleMargin", "titleTopMargin", "useWidth", "useMaxWidth", "arrowMarkerAbsolute", "curve"})
SECURE = ("secure", "securityLevel", "startOnLoad", "maxTextSize", "suppressErrorRendering", "maxEdges")
_FONT = '"trebuchet ms", verdana, arial, sans-serif;'


def _mapping(value, name):
    if not isinstance(value, Mapping):
        raise MermaidError(f"{name} must be a mapping", code="INVALID_CONFIG")
    return value


def _keys(data, allowed, name):
    for key in data:
        if key not in allowed:
            raise MermaidError(f"Unsupported flowchart configuration {name}{key}", code="UNSUPPORTED_CONFIG")


def _number(value, name, *, minimum=0, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or value < minimum or (integer and int(value) != value)):
        raise MermaidError(f"{name} must be a finite {'integer' if integer else 'number'} >= {minimum}", code="INVALID_CONFIG")
    return float(value)


def evaluate(value):
    """config.ts:evaluate, including string false/null/0 and true undefined."""
    text = "null" if value is None else "true" if value is True else "false" if value is False else str(value)
    return value is not False and text.strip().lower() not in ("false", "null", "0")


def sanitize_css(text):
    count = 0
    for char in text:
        count += (char == "{") - (char == "}")
        if count < 0:
            return "{ /* ERROR: Unbalanced CSS */ }"
    return text if count == 0 else "{ /* ERROR: Unbalanced CSS */ }"


def sanitize_directive(value, secure=SECURE):
    """Clone then apply sanitizeDirective.ts and config.ts:sanitize in order."""
    def known(item):
        if isinstance(item, list):
            return [known(child) for child in item]
        if not isinstance(item, Mapping):
            return item
        result = {}
        for key, child in item.items():
            if (not isinstance(key, str) or key.startswith("__") or "proto" in key or "constr" in key
                    or key not in CONFIG_KEYS or key == "dompurifyConfig" or child is None):
                continue
            child = known(child)
            if isinstance(child, str) and any(name in key for name in ("themeCSS", "fontFamily", "altFontFamily")):
                child = sanitize_css(child)
            result[key] = child
        if isinstance(result.get("themeVariables"), dict):
            for key, child in result["themeVariables"].items():
                if isinstance(child, str) and not re.fullmatch(r'[\d "#%(),.;A-Za-z]+', child):
                    result["themeVariables"][key] = ""
        return result
    result = known(deepcopy(value))
    if not isinstance(result, dict):
        return {}
    # addDirective's legacy fontFamily bridge is after sanitizeDirective.
    if result.get("fontFamily") and not result.get("themeVariables", {}).get("fontFamily"):
        result.setdefault("themeVariables", {})["fontFamily"] = result["fontFamily"]
    def protected(item):
        if isinstance(item, dict):
            for key in tuple(item):
                child = item[key]
                if (key in ("secure", *secure) or key.startswith("__") or
                        isinstance(child, str) and ("<" in child or ">" in child or "url(data:" in child)):
                    del item[key]
                else:
                    protected(child)
        elif isinstance(item, list):
            for child in item:
                protected(child)
    protected(result)
    return result


def _defaults():
    return {"theme": "default", "look": "classic", "layout": "elk", "fontFamily": _FONT, "fontSize": 16,
        "themeVariables": get_theme_variables("default"), "maxTextSize": 50000, "maxEdges": 500,
        "securityLevel": "strict", "secure": list(SECURE), "markdownAutoWrap": True,
        "elk": deepcopy(ELK_DEFAULTS), "handDrawnSeed": 0, "deterministicIds": False,
        "flowchart": {"theme": "redux-color", "look": "neo", "padding": 15, "diagramPadding": 8,
            "nodeSpacing": 50, "rankSpacing": 50, "wrappingWidth": 120, "minNodeWidth": 120,
            "inheritDir": False, "subGraphTitleMargin": {"top": 0, "bottom": 0}, "titleTopMargin": 25, "curve": "basis"}}


def font_pixels(value, default=16):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _number(value, "themeVariables.fontSize", minimum=0.01)
    if isinstance(value, str):
        match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(px|pt|pc|in|cm|mm|q|em|rem|%)?\s*", value, re.I)
        if match:
            factor = {None: 1, "px": 1, "pt": 96 / 72, "pc": 16, "in": 96, "cm": 96 / 2.54,
                      "mm": 96 / 25.4, "q": 96 / 101.6, "em": default, "rem": 16, "%": default / 100}[match[2].lower() if match[2] else None]
            return _number(float(match[1]) * factor, "themeVariables.fontSize", minimum=0.01)
    raise MermaidError("Unsupported themeVariables.fontSize CSS value", code="INVALID_CONFIG")


def _theme_number(variables, key, fallback):
    value = variables.get(key)
    if isinstance(value, bool):
        raise MermaidError(f"themeVariables.{key} must be numeric", code="INVALID_CONFIG")
    try:
        number = float(fallback if value is None else value)
    except (ValueError, TypeError) as exc:
        raise MermaidError(f"themeVariables.{key} must be numeric", code="INVALID_CONFIG") from exc
    return _number(number, "themeVariables." + key)


def resolve_config(config: Mapping | None = None, *, layers=()) -> FlowConfig:
    root = {} if config is None else deepcopy(dict(_mapping(config, "config")))
    _keys(root, _ROOT_KEYS, "")
    # Source assignWithDepth ignores null and applies array sources in order.
    # Validate the effective merged section below, not the raw site value.
    original = deepcopy(root)
    overrides = deepcopy(dict(_mapping(root.get("themeVariables", {}), "themeVariables")))
    if root.get("fontFamily") and not overrides.get("fontFamily"):
        overrides["fontFamily"] = root["fontFamily"]
    requested = root.get("theme")
    if requested is not None and requested not in (*THEMES, "null"):
        root["theme"] = "default"
        original["theme"] = "default"
    original["themeVariables"] = overrides
    root["themeVariables"] = get_theme_variables(root.get("theme", "default"), overrides)
    defaults = _defaults()
    site = assign_with_depth(deepcopy(defaults), root)
    # config.ts:setSiteConfig replaces the calculated palette when initialize
    # explicitly selects a theme; retaining default-theme-only keys leaks a
    # different palette into base/neutral and other complete theme families.
    if original.get('theme') in THEMES:
        site['themeVariables']=deepcopy(root['themeVariables'])
    secure = site.get("secure", list(SECURE))
    if not isinstance(secure, (list, tuple)):
        raise MermaidError("secure must be an array of config key names", code="INVALID_CONFIG")
    combined = {}
    raw_layers = []
    for name, value in layers:
        decoded = thaw_value(value) if isinstance(value, tuple) else deepcopy(value)
        if name in ("frontmatter", "directive") and isinstance(decoded, dict):
            merge_layers(combined, decoded)
            raw_layers.append((name, freeze_value(decoded)))
    directive = sanitize_directive(combined, secure)
    cfg = assign_with_depth(deepcopy(site), directive)
    for key in ("theme", "look", "layout"):
        found = False
        for layer in (directive, original, defaults):
            scoped = layer.get("flowchart", {})
            values = [(scoped.get(key) if isinstance(scoped, dict) else None), layer.get(key)]
            for value in values:
                usable = value is not None and (key != "theme" or value in (*THEMES, "null")) and (key != "look" or value in ("classic", "neo", "handDrawn"))
                if usable:
                    cfg[key], found = value, True
                    break
            if found:
                break
    from ..runtime.layouts import registered_layouts
    if not isinstance(cfg['layout'], str) or cfg["layout"] not in registered_layouts():
        raise MermaidError("Only ELK or registered native flowchart layouts are supported", code="UNSUPPORTED_CONFIG")
    if directive.get("theme") or cfg["theme"] != site.get("theme"):
        if cfg["theme"] in THEMES:
            variables = assign_with_depth(deepcopy(overrides), directive.get("themeVariables", {}))
            cfg["themeVariables"] = get_theme_variables(cfg["theme"], variables)
    variables = cfg["themeVariables"]
    flow = _mapping(cfg.get("flowchart", {}), "flowchart")
    # Unknown in-document keys are sanitized rather than promoted to support;
    # recognized but deferred options still fail explicitly.
    _keys(flow, _FLOW_KEYS, "flowchart.")
    curve = flow.get("curve", "basis")
    if not isinstance(curve, str) or curve not in CURVES:
        raise MermaidError("Unknown flowchart curve", code="INVALID_CONFIG")
    elk = validate_elk(cfg.get("elk", {}))
    seed = cfg.get("handDrawnSeed", 0)
    if isinstance(seed, bool) or not isinstance(seed, (int, float)) or not math.isfinite(seed):
        raise MermaidError("handDrawnSeed must be finite", code="INVALID_CONFIG")
    # Rough checks the original seed's truthiness before Math.imul coerces it.
    # Preserve numbers such as 0.5/2**32 rather than changing them to false 0.
    deterministic = cfg.get("deterministicIds", False)
    if not isinstance(deterministic, bool):
        raise MermaidError("deterministicIds must be boolean", code="INVALID_CONFIG")
    id_seed = cfg.get("deterministicIDSeed")
    if id_seed is not None and not isinstance(id_seed, str):
        raise MermaidError("deterministicIDSeed must be a string", code="INVALID_CONFIG")
    html = cfg.get("htmlLabels")
    if html is None:
        html = flow.get("htmlLabels")
    html = True if html is None else evaluate(html)
    family = variables.get("fontFamily") or _FONT
    site_family = cfg.get("fontFamily", _FONT)
    for text in (family, site_family):
        if not isinstance(text, str) or not text.strip() or any(char in text for char in "\r\n{}<>"):
            raise MermaidError("fontFamily must be a nonempty CSS family string", code="INVALID_CONFIG")
    security = cfg.get("securityLevel", "strict")
    if security not in ("strict", "loose", "antiscript", "sandbox"):
        raise MermaidError("Invalid securityLevel", code="INVALID_CONFIG")
    dompurify = _mapping(cfg.get("dompurifyConfig", {}), "dompurifyConfig")
    margin = _mapping(flow.get("subGraphTitleMargin", {}), "flowchart.subGraphTitleMargin")
    _keys(margin, frozenset({"top", "bottom"}), "flowchart.subGraphTitleMargin.")
    inherit = flow.get("inheritDir", False)
    if not isinstance(inherit, bool):
        raise MermaidError("flowchart.inheritDir must be boolean", code="INVALID_CONFIG")
    top_margin = _number(flow.get("titleTopMargin", 25), "flowchart.titleTopMargin")
    padding = _number(flow.get("padding", 15), "flowchart.padding")
    shadow = variables.get("dropShadow") or ""
    is_svg_shadow = shadow == "url(#drop-shadow)"
    custom_shadow = re.fullmatch(r"drop-shadow\(\s*([-\d.]+)px\s+([-\d.]+)px\s+([-\d.]+)px\s+rgba?\(([^)]+)\)\s*\)", shadow.strip().rstrip(";").rstrip()) if isinstance(shadow, str) else None
    shadow_x = 4.0 if is_svg_shadow else float(custom_shadow[1]) if custom_shadow else 0.0
    shadow_y = 4.0 if is_svg_shadow else float(custom_shadow[2]) if custom_shadow else 0.0
    shadow_opacity = 0.06 if is_svg_shadow else float(custom_shadow[4].split(",")[-1]) if custom_shadow and len(custom_shadow[4].split(",")) == 4 else 0.0
    if cfg["look"] != "neo":
        shadow_x, shadow_y, shadow_opacity = 0.0, 0.0, 0.0
    palette = variables.get("borderColorArray")
    colour_theme = cfg["theme"] in ("redux-color", "redux-dark-color") and isinstance(palette, list) and bool(palette)
    borders = palette if colour_theme else (variables.get("clusterBorder") or "#000000",)
    fills = variables.get("bkgColorArray") if colour_theme else None
    if not isinstance(fills, list) or not fills:
        fills = (variables.get("clusterBkg") or "#ffffff",)
    layers_value = (("default", freeze_value(defaults)), ("site", freeze_value(config or {})), *raw_layers)
    return FlowConfig(font_family=family, font_size=font_pixels(variables.get("fontSize", "16px")),
        node_padding=padding, diagram_padding=_number(flow.get("diagramPadding", 8), "flowchart.diagramPadding"),
        node_spacing=_number(flow.get("nodeSpacing", 50), "flowchart.nodeSpacing", integer=True),
        rank_spacing=_number(flow.get("rankSpacing", 50), "flowchart.rankSpacing", integer=True),
        fill=variables.get("mainBkg") or "#ffffff", stroke=variables.get("nodeBorder") or "#000000",
        text_color=variables.get("nodeTextColor") or variables.get("textColor") or "#000000",
        edge_color=variables.get("lineColor") or "#000000", background=variables.get("background") or "#ffffff",
        line_height=1.5 if html else 1.1, html_labels=html,
        max_text_size=int(_number(cfg.get("maxTextSize", 50000), "maxTextSize", integer=True)),
        max_edges=int(_number(cfg.get("maxEdges", 500), "maxEdges", integer=True)),
        layout=cfg["layout"], theme=cfg["theme"], look=cfg["look"], padding_x=16 if cfg["look"] == "neo" else padding * 2,
        padding_y=12 if cfg["look"] == "neo" else padding,
        min_node_width=_number(flow.get("minNodeWidth", 120), "flowchart.minNodeWidth"),
        wrapping_width=_number(flow.get("wrappingWidth", 120), "flowchart.wrappingWidth"),
        node_stroke_width=_theme_number(variables, "strokeWidth", 1), edge_stroke_width=_theme_number(variables, "strokeWidth", 1),
        shadow_offset_x=shadow_x, shadow_offset_y=shadow_y, shadow_opacity=shadow_opacity,
        round_radius=_theme_number(variables, "radius", 5), edge_label_background=variables.get("edgeLabelBackground") or "#ffffff",
        site_font_family=site_family, site_font_size=_number(cfg.get("fontSize", 16), "fontSize", minimum=0.01),
        inherit_direction=inherit, group_title_top_margin=_number(margin.get("top", 0), "flowchart.subGraphTitleMargin.top"),
        group_title_bottom_margin=_number(margin.get("bottom", 0), "flowchart.subGraphTitleMargin.bottom"),
        group_borders=tuple(borders), group_fills=tuple(fills),
        security_level=security, markdown_auto_wrap=cfg.get("markdownAutoWrap", True) is not False,
        theme_variables=freeze_value(variables), theme_css=str(cfg.get("themeCSS") or ""), title_top_margin=top_margin,
        config_layers=layers_value, dompurify_config=freeze_value(dompurify),
        dompurify_provided="dompurifyConfig" in cfg and cfg["dompurifyConfig"] is not None,
        curve=curve, elk_options=freeze_value(elk), hand_drawn_seed=seed,
        deterministic_ids=deterministic, deterministic_id_seed=id_seed)
