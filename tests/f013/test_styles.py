"""Independent native CSS intent assertions for fixed Mermaid source styles.

Expected values are CSS declaration/cascade arithmetic and explicit source
theme rules, never candidate private helpers or generated Python goldens.
"""
from __future__ import annotations

import copy
from dataclasses import replace
import re
import unittest

from py_mermaid.config import resolve_config
from py_mermaid.model.flowchart import Flowchart, FlowGroup, FlowNode, MermaidError, ResolvedStyle, SourcePosition, SourceSpan
from py_mermaid.rendering.styles import apply_declarations, css_size, resolve_style

THEMES = ("base", "dark", "default", "forest", "neutral", "neo", "neo-dark",
          "redux", "redux-dark", "redux-color", "redux-dark-color", "null")


def specimen(config=None):
    p = SourcePosition(0, 0, 1, 0)
    span = SourceSpan(p, p)
    return Flowchart("test-only style semantic fixture", "TD",
                     (FlowNode("A", "Alpha", span),), (), resolve_config(config),
                     groups=(FlowGroup("G", "Group", span, color_index=3),))


def rgb(value):
    """Only normalize independent literal colors used by these assertions."""
    text = value.lower().strip().replace(" ", "")
    names = {"red": (255, 0, 0), "blue": (0, 0, 255), "green": (0, 128, 0),
             "black": (0, 0, 0), "white": (255, 255, 255)}
    if text in names:
        return names[text]
    if re.fullmatch(r"#[0-9a-f]{3}", text):
        return tuple(int(c*2, 16) for c in text[1:])
    if re.fullmatch(r"#[0-9a-f]{6}", text):
        return tuple(int(text[i:i+2], 16) for i in (1, 3, 5))
    match = re.fullmatch(r"rgba?\((\d+),(\d+),(\d+)(?:,[\d.]+)?\)", text)
    if match:
        return tuple(int(c) for c in match.groups())
    raise AssertionError("Unexpected literal color representation: " + value)


class NativeStyleTests(unittest.TestCase):
    def test_s01_font_shorthand_order_priority_and_resets(self):
        parent = ResolvedStyle(font_size=14, font_weight="bold", font_style="italic", line_height=2)
        result = apply_declarations(parent, "font-size:10px;font:20px Arial")
        self.assertEqual(result.font_size, 20)
        self.assertEqual(result.font_family, "Arial")
        self.assertEqual(result.font_weight, "normal")
        self.assertEqual(result.font_style, "normal")
        self.assertIsNone(result.line_height_px)
        self.assertEqual(apply_declarations(parent, "font:20px Arial;font-size:10px").font_size, 10)
        self.assertEqual(apply_declarations(parent, "font-size:10px!important;font:20px Arial").font_size, 10)
        self.assertEqual(apply_declarations(parent, "font-size:10px;font:20px Arial!important").font_size, 20)

    def test_s02_inline_important_and_equal_priority_last_wins(self):
        base = ResolvedStyle()
        red = apply_declarations(base, "color:red!important;color:blue")
        blue = apply_declarations(base, "color:red!important;color:blue!important")
        self.assertEqual(rgb(red.text_color), (255, 0, 0))
        self.assertEqual(rgb(blue.text_color), (0, 0, 255))

    def test_s03_relative_font_uses_true_parent_not_ua_scaled_tag(self):
        for tag, factor in (("small", .8), ("h1", 2), ("sup", .75)):
            for value, expected in (("2em", 40), ("150%", 30), ("inherit", 20)):
                with self.subTest(tag=tag, value=value):
                    diagram = specimen({"themeCSS": f".nodeLabel {tag} {{font-size:{value}}}"})
                    parent = ResolvedStyle(font_size=20)
                    ua = replace(parent, font_size=20*factor)
                    child = resolve_style(diagram, "node-label", "A", tag=tag, base=ua, inherited_base=parent)
                    self.assertEqual(child.font_size, expected)

    def test_s04_custom_variables_inherit_and_nested_fallback_resolves(self):
        diagram = specimen({"themeCSS": ".nodeLabel {--ink:#123456} .nodeLabel em {color:var(--ink)}"})
        parent = resolve_style(diagram, "node-label", "A")
        child = resolve_style(diagram, "node-label", "A", tag="em", base=parent, inherited_base=parent)
        self.assertEqual(rgb(child.text_color), (18, 52, 86))
        fallback = apply_declarations(ResolvedStyle(), "color:var(--absent,var(--also-absent,#654321))")
        self.assertEqual(rgb(fallback.text_color), (101, 67, 33))
        with self.assertRaises(MermaidError):
            apply_declarations(ResolvedStyle(), "--a:var(--b);--b:var(--a);color:var(--a)")

    def test_s05_absolute_font_keywords_and_relative_units(self):
        # Chromium's ordinary 16px medium profile; absolute keywords ignore
        # the parent's size. Relative em/% and larger use the actual parent.
        for base in (12, 32):
            for keyword, expected in (("small", 13), ("medium", 16), ("large", 18), ("x-large", 24)):
                with self.subTest(base=base, keyword=keyword):
                    self.assertEqual(css_size(keyword, base), expected)
            self.assertEqual(css_size("2em", base), 2*base)
            self.assertEqual(css_size("150%", base), 1.5*base)
            self.assertEqual(css_size("1rem", base), 16)
            self.assertEqual(css_size("12pt", base), 16)

    def test_s06_title_default18_and_anchor_is_not_text_align(self):
        diagram = specimen({"themeVariables": {"fontSize": "32px"}})
        self.assertEqual(resolve_style(diagram, "title").font_size, 18)
        diagram = specimen({"themeCSS": ".flowchartTitleText {font-size:24px;text-align:right;text-anchor:start}"})
        title = resolve_style(diagram, "title")
        self.assertEqual(title.font_size, 24)
        self.assertEqual(title.text_anchor, "start")
        self.assertEqual(title.text_align, "right")

    def test_s07_current_color_independent_of_declaration_order(self):
        for declarations in ("stroke:currentColor;color:#123456", "color:#123456;stroke:currentColor"):
            with self.subTest(declarations=declarations):
                style = apply_declarations(ResolvedStyle(), declarations, kind="node")
                self.assertEqual(rgb(style.stroke), (18, 52, 86))
        svg = apply_declarations(ResolvedStyle(), "fill:currentColor;color:#123456", kind="title", svg_text=True)
        self.assertEqual(rgb(svg.text_color), (18, 52, 86))

    def test_s08_absolute_and_unitless_line_height_inheritance(self):
        parent = apply_declarations(ResolvedStyle(font_size=14), "line-height:20px")
        child = apply_declarations(parent, "font-size:28px", inherited=parent)
        self.assertEqual(child.line_height_px, 20)
        self.assertAlmostEqual(child.font_size*child.line_height, 20)
        multiplier = apply_declarations(ResolvedStyle(font_size=14), "line-height:2")
        enlarged = apply_declarations(multiplier, "font-size:28px", inherited=multiplier)
        self.assertIsNone(enlarged.line_height_px)
        self.assertEqual(enlarged.font_size*enlarged.line_height, 56)

    def test_s09_palette_theme_border_gate_and_nodes_do_not_cycle(self):
        variables = {"borderColorArray": ["#111111", "#222222"], "bkgColorArray": ["#333333", "#444444"],
                     "clusterBkg": "#aaaaaa", "clusterBorder": "#bbbbbb", "mainBkg": "#555555"}
        for theme in THEMES:
            with self.subTest(theme=theme):
                diagram = specimen({"theme": theme, "themeVariables": variables})
                group = resolve_style(diagram, "group", "G")
                expected = ((68, 68, 68), (34, 34, 34)) if theme in ("redux-color", "redux-dark-color") else ((170, 170, 170), (187, 187, 187))
                self.assertEqual((rgb(group.fill), rgb(group.stroke)), expected)
                self.assertEqual(rgb(resolve_style(diagram, "node", "A").fill), (85, 85, 85))
        diagram = specimen({"theme": "redux-color", "themeVariables": dict(variables, borderColorArray=[])})
        group = resolve_style(diagram, "group", "G")
        self.assertEqual(rgb(group.fill), (170, 170, 170))
        self.assertEqual(rgb(group.stroke), (187, 187, 187))

    def test_s10_specificity_source_order_and_important(self):
        css = ".nodeLabel{color:red} #A.nodeLabel{color:blue} .nodeLabel{color:green}"
        self.assertEqual(rgb(resolve_style(specimen({"themeCSS": css}), "node-label", "A").text_color), (0, 0, 255))
        css += ".nodeLabel{color:red!important}"
        self.assertEqual(rgb(resolve_style(specimen({"themeCSS": css}), "node-label", "A").text_color), (255, 0, 0))
        equal = ".nodeLabel{color:red}.nodeLabel{color:blue}"
        self.assertEqual(rgb(resolve_style(specimen({"themeCSS": equal}), "node-label", "A").text_color), (0, 0, 255))

    def test_s11_parent_important_is_not_inherited_as_child_priority(self):
        diagram = specimen({"themeCSS": ".nodeLabel{font-size:20px!important}.nodeLabel em{font-size:30px}"})
        parent = resolve_style(diagram, "node-label", "A")
        child = resolve_style(diagram, "node-label", "A", tag="em", base=parent, inherited_base=parent)
        self.assertEqual(parent.font_size, 20)
        self.assertEqual(child.font_size, 30)

    def test_s12_gradient_native_stops_and_explicit_stroke_override(self):
        variables = {"useGradient": True, "gradientStart": "#123456", "gradientStop": "#654321"}
        diagram = specimen({"theme": "base", "look": "neo", "themeVariables": variables})
        style = resolve_style(diagram, "node", "A")
        self.assertEqual(tuple((offset, rgb(color)) for offset, color in style.stroke_gradient), ((0, (18, 52, 86)), (1, (101, 67, 33))))
        override = specimen({"theme": "base", "look": "neo", "themeVariables": variables,
                             "themeCSS": '.node[data-look="neo"] rect {stroke:#abcdef!important}'})
        style = resolve_style(override, "node", "A")
        self.assertEqual(style.stroke_gradient, ())
        self.assertEqual(rgb(style.stroke), (171, 205, 239))
        classic = specimen({"theme": "base", "look": "classic", "themeVariables": variables})
        self.assertEqual(resolve_style(classic, "node", "A").stroke_gradient, ())

    def test_s13_source_shadow_neo_and_custom_native_filter(self):
        # Official computed style accepts pinned source's terminated filter as
        # drop-shadow(rgba(0,0,0,.25) 0px 1px 2px); prior contrary test preserved.
        neo = resolve_style(specimen({"theme": "neo", "look": "neo"}), "node", "A")
        self.assertEqual((neo.shadow_opacity, neo.shadow_dx, neo.shadow_dy, neo.shadow_blur), (1, 0, 1, 2))
        self.assertEqual(rgb(neo.shadow_color), (0, 0, 0))
        self.assertRegex(neo.shadow_color.replace(" ", ""), r"^rgba\(0,0,0,(?:0?\.25)\)$")
        css = '.node rect {filter:drop-shadow(-3px 4px 2px rgba(1,2,3,0.5))!important}'
        style = resolve_style(specimen({"themeCSS": css}), "node", "A")
        self.assertEqual((style.shadow_dx, style.shadow_dy, style.shadow_blur), (-3, 4, 2))
        self.assertEqual(rgb(style.shadow_color), (1, 2, 3))
        no_filter = resolve_style(specimen({"themeCSS": '.node rect{filter:none!important}'}), "node", "A")
        self.assertEqual(no_filter.shadow_opacity, 0)

    def test_s14_global_keywords_distinguish_inherited_and_unset(self):
        parent = ResolvedStyle(font_size=24, opacity=.25, display="block", background="red")
        inherited = apply_declarations(ResolvedStyle(), "font-size:inherit;opacity:inherit", inherited=parent)
        self.assertEqual(inherited.font_size, 24)
        self.assertEqual(inherited.opacity, .25)
        unset = apply_declarations(parent, "font-size:unset;opacity:unset;display:unset;background:unset", inherited=parent)
        self.assertEqual(unset.font_size, 24)
        self.assertEqual(unset.opacity, 1)
        self.assertEqual(unset.display, "inline")
        self.assertEqual(unset.background, "transparent")

    def test_s15_supported_layout_css_is_executable_or_explicitly_rejected(self):
        style = apply_declarations(ResolvedStyle(), "white-space:pre-wrap;display:block;text-align:right;text-anchor:end")
        self.assertEqual((style.white_space, style.display, style.text_align, style.text_anchor), ("pre-wrap", "block", "right", "end"))
        with self.assertRaises(MermaidError):
            apply_declarations(ResolvedStyle(), "dominant-baseline:central")

    def test_s16_config_and_base_style_are_not_mutated_or_leaked(self):
        configuration = {"theme": "redux-color", "themeVariables": {"borderColorArray": ["red", "blue"]},
                         "themeCSS": ".nodeLabel{font-size:24px;color:red}"}
        before = copy.deepcopy(configuration)
        first = specimen(configuration)
        style = resolve_style(first, "node-label", "A")
        original = copy.deepcopy(style)
        apply_declarations(style, "font-size:32px;color:blue")
        self.assertEqual(configuration, before)
        self.assertEqual(style, original)
        fresh = resolve_style(specimen(), "node-label", "A")
        self.assertNotEqual(fresh.font_size, 24)


if __name__ == "__main__":
    unittest.main()
