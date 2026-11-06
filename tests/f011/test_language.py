"""Independent F01.1 assertions from pinned Mermaid grammar/spec and slice contract.

Provenance and source hashes: references/f011-language-assertions.json.
No snapshots or expected values are generated from candidate output.
"""
from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import math
import unittest

from py_mermaid.config import resolve_config
from py_mermaid.model.flowchart import MermaidError
from py_mermaid.parsing import parse_flowchart


def semantic(diagram):
    return ([(node.id, node.label) for node in diagram.nodes],
            [(edge.source, edge.target) for edge in diagram.edges])


class LanguageTests(unittest.TestCase):
    def test_header_keywords_and_directions(self):
        for keyword in ("flowchart", "graph"):
            for direction in ("TD", "LR"):
                with self.subTest(keyword=keyword, direction=direction):
                    diagram = parse_flowchart(f"{keyword} {direction}\nA[Alpha]")
                    self.assertEqual(diagram.direction, direction)
                    self.assertEqual(semantic(diagram), ([("A", "Alpha")], []))

    def test_single_bare_node(self):
        self.assertEqual(semantic(parse_flowchart("graph TD;A;")), ([("A", "A")], []))

    def test_single_rectangle(self):
        self.assertEqual(semantic(parse_flowchart("graph TD;a[A];")), ([("a", "A")], []))

    def test_chain(self):
        self.assertEqual(semantic(parse_flowchart("graph TD\nA-->B-->C;")),
                         ([("A", "A"), ("B", "B"), ("C", "C")], [("A", "B"), ("B", "C")]))

    def test_branch_and_merge(self):
        diagram = parse_flowchart("flowchart LR\nA[Start]-->B[Left];A-->C[Right]\nB-->D[End];C-->D")
        self.assertEqual(semantic(diagram),
                         ([("A", "Start"), ("B", "Left"), ("C", "Right"), ("D", "End")],
                          [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]))
        self.assertEqual(len({edge.id for edge in diagram.edges}), 4)

    def test_disconnected_nodes_keep_insertion_order(self):
        self.assertEqual(semantic(parse_flowchart("graph TD;Z;A;M")),
                         ([("Z", "Z"), ("A", "A"), ("M", "M")], []))

    def test_bare_reference_preserves_label(self):
        self.assertEqual(semantic(parse_flowchart("graph TD;A[First];A-->B;A")),
                         ([("A", "First"), ("B", "B")], [("A", "B")]))

    def test_last_explicit_label_wins_without_reordering(self):
        self.assertEqual(semantic(parse_flowchart("graph TD;A[First];B;A[Last];A-->B")),
                         ([("A", "Last"), ("B", "B")], [("A", "B")]))

    def test_duplicate_edges_retained(self):
        diagram = parse_flowchart("graph TD;A-->B;A-->B")
        self.assertEqual(semantic(diagram), ([("A", "A"), ("B", "B")], [("A", "B"), ("A", "B")]))
        self.assertEqual(len({edge.id for edge in diagram.edges}), 2)

    def test_self_loop_retained(self):
        self.assertEqual(semantic(parse_flowchart("graph TD;A-->A")), ([("A", "A")], [("A", "A")]))

    def test_comments_at_beginning_middle_and_eof(self):
        source = "%% leading comment\ngraph TD;\n%% middle comment\nA-->B\n%% final comment"
        self.assertEqual(semantic(parse_flowchart(source)), ([("A", "A"), ("B", "B")], [("A", "B")]))

    def test_inline_comments_are_not_grammar_whitespace(self):
        # cleanupComments is line-anchored and flow.jison defines no inline
        # comment token; official getDiagramFromText rejects the edge variant.
        sources = ["graph TD %% header\nA", "graph TD;A %% node", "graph TD;A; %% after separator",
                   "graph TD\nA-->B %% after edge", "graph TD\nA-->B %% after edge\nC"]
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaises(MermaidError) as caught:
                    parse_flowchart(source)
                self.assertEqual(caught.exception.span.start.index, source.index("%%"))

    def test_indented_whole_line_comments_with_crlf_and_no_final_newline(self):
        source = "  %% first\r\ngraph TD\r\n\t%% middle\r\nA-->B\r\n \t%% final"
        self.assertEqual(semantic(parse_flowchart(source)),
                         ([("A", "A"), ("B", "B")], [("A", "B")]))

    def test_semicolons_and_horizontal_spaces(self):
        self.assertEqual(semantic(parse_flowchart("  graph TD; A [ Alpha ] --> B [ Beta ] ;\n")),
                         ([("A", "Alpha"), ("B", "Beta")], [("A", "B")]))

    def test_quoted_punctuation(self):
        self.assertEqual(parse_flowchart('graph TD;A["Check (x), [y] and {z}!"]').nodes[0].label,
                         "Check (x), [y] and {z}!")

    def test_plain_hash_is_not_an_entity(self):
        self.assertEqual(parse_flowchart('graph TD;A["Issue #1"]').nodes[0].label, "Issue #1")

    def test_literal_and_actual_line_breaks(self):
        for label in ("First\\nSecond", "First\nSecond", "First\r\nSecond"):
            with self.subTest(label=label):
                self.assertEqual(parse_flowchart(f'graph TD;A["{label}"]').nodes[0].label, "First\nSecond")

    def test_plain_whitespace_rendering_semantics(self):
        for html in (True, False):
            with self.subTest(html=html):
                result = parse_flowchart('graph TD;A["  Alpha   Beta\tGamma  "]', config={"htmlLabels": html})
                self.assertEqual(result.nodes[0].label, "Alpha Beta Gamma")

    def test_unicode_and_crlf_source_positions(self):
        source = 'flowchart TD\r\nA["😀"] --> B[完成]'
        result = parse_flowchart(source)
        self.assertEqual(result.source, source)
        self.assertEqual(semantic(result), ([("A", "😀"), ("B", "完成")], [("A", "B")]))
        node = result.nodes[1]
        index = source.index("B[")
        self.assertEqual(node.span.start.index, index)
        self.assertEqual(node.span.start.utf16_offset, index + 1)
        self.assertEqual((node.span.start.line, node.span.start.column), (2, 12))
        self.assertEqual(node.span.end.index, len(source))
        self.assertEqual(node.span.end.utf16_offset, len(source) + 1)

    def test_incomplete_source_reports_raw_eof_position(self):
        source = 'graph TD\r\nA["😀"]-->'
        with self.assertRaises(MermaidError) as caught:
            parse_flowchart(source)
        span = caught.exception.span
        self.assertIsNotNone(span)
        self.assertEqual(span.start.index, len(source))
        self.assertEqual(span.start.utf16_offset, len(source) + 1)
        self.assertEqual((span.start.line, span.start.column), (2, 10))

    def test_invalid_sources_explicitly_fail_with_location(self):
        sources = ["", "flowchart TD A", "graph TD;A-->",
                   "graph TD;A[unfinished", 'graph TD;A["unfinished]', "graph TD;A[]",
                   'graph TD;A["text" extra]', "graph TD;A B", "sequenceDiagram\nA-->B"]
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaises(MermaidError) as caught:
                    parse_flowchart(source)
                self.assertTrue(caught.exception.code)
                self.assertIsNotNone(caught.exception.span)
                self.assertGreaterEqual(caught.exception.span.start.index, 0)
                self.assertLessEqual(caught.exception.span.end.index, len(source))

    def test_f014_promoted_static_syntax_and_remaining_math_boundary(self):
        for direction in ('TB', 'RL', 'BT'):
            with self.subTest(direction=direction): self.assertEqual(parse_flowchart('graph '+direction+';A').direction,direction)
        self.assertEqual(parse_flowchart('flowchart-elk TD;A').nodes[0].id,'A')
        for token, stroke, marker in [('---','normal','none'),('-.->','dotted','point'),('==>','thick','point')]:
            with self.subTest(token=token):
                edge=parse_flowchart('graph TD;A'+token+'B').edges[0]
                self.assertEqual((edge.stroke,edge.marker_end),(stroke,marker))
        self.assertEqual([(e.source,e.target) for e in parse_flowchart('graph TD;A & B-->C').edges],[('A','C'),('B','C')])
        self.assertEqual(parse_flowchart('graph TD;A:::red').nodes[0].classes,('red',))
        self.assertEqual(parse_flowchart('graph TD;A;style A fill:red').nodes[0].styles,('fill:red',))
        self.assertEqual(parse_flowchart('graph TD;A;click A callback').nodes[0].classes,('clickable',))
        self.assertEqual(parse_flowchart('graph TD;A["fa:fa-home"]').nodes[0].label,'fa:fa-home')
        for source in ('graph TD','flowchart'):
            with self.subTest(source=source): self.assertEqual(parse_flowchart(source).nodes,())
        self.assertEqual(parse_flowchart('graph TD;A["$$x^2$$"]').nodes[0].label,'$$x^2$$')

    def test_f013_promoted_labels_frontmatter_directives_and_accessibility(self):
        # Explicit source-backed migration of former F01.1 scope rejections.
        for text, label, kind in [('graph TD;A["<b>Bold</b>"]', '<b>Bold</b>', 'text'),
                                  ('graph TD;A["`Markdown`"]', 'Markdown', 'markdown'),
                                  ('graph TD;A["#quot;"]', '&quot;', 'text'),
                                  ('graph TD;A["&amp;"]', '&amp;', 'text')]:
            with self.subTest(text=text):
                node = parse_flowchart(text).nodes[0]
                self.assertEqual((node.label, node.label_kind), (label, kind))
        self.assertEqual(parse_flowchart('graph TD;accTitle: Title\nA').acc_title, 'Title')
        self.assertEqual(parse_flowchart('%%{init: {"theme":"dark"}}%%\ngraph TD;A').config.theme, 'dark')
        self.assertEqual(parse_flowchart('---\ntitle: Title\n---\ngraph TD;A').title, 'Title')

    def test_f012_promoted_features_have_positive_semantics(self):
        # Explicit scope migration of the five former F01.1 exclusions above;
        # each gains a concrete assertion rather than a skip or silent removal.
        for source, shape, label in [("graph TD;A(Round)", "round", "Round"),
                                     ("graph TD;A{Decision}", "diamond", "Decision"),
                                     ("graph TD;A((Circle))", "circle", "Circle")]:
            with self.subTest(source=source):
                node = parse_flowchart(source).nodes[0]
                self.assertEqual((node.id, node.shape, node.label), ("A", shape, label))
        edge = parse_flowchart("graph TD;A-->|text|B").edges[0]
        self.assertEqual((edge.source, edge.target, edge.label), ("A", "B", "text"))
        diagram = parse_flowchart("graph TD;subgraph Group\nA\nend")
        self.assertEqual((diagram.groups[0].id, diagram.groups[0].members), ("Group", ("A",)))
        self.assertEqual(diagram.nodes[0].parent_id, "Group")

    def test_text_budget_counts_utf16_and_does_not_truncate(self):
        source = 'graph TD;A["😀"]'
        units = len(source) + 1
        self.assertEqual(parse_flowchart(source, config={"maxTextSize": units}).source, source)
        with self.assertRaises(MermaidError) as caught:
            parse_flowchart(source, config={"maxTextSize": units - 1})
        self.assertEqual(caught.exception.code, "MAX_TEXT_SIZE_EXCEEDED")

    def test_edge_budget_boundary(self):
        self.assertEqual(len(parse_flowchart("graph TD;A-->B", config={"maxEdges": 1}).edges), 1)
        with self.assertRaises(MermaidError) as caught:
            parse_flowchart("graph TD;A-->B-->C", config={"maxEdges": 1})
        self.assertEqual(caught.exception.code, "MAX_EDGES_EXCEEDED")
        self.assertEqual(len(parse_flowchart("graph TD;A", config={"maxEdges": 0}).edges), 0)

    def test_invalid_input_type(self):
        for value in (None, b"graph TD;A", 42):
            with self.subTest(value=value):
                with self.assertRaises(MermaidError):
                    parse_flowchart(value)

    def test_request_isolation_after_success_and_failure(self):
        first = parse_flowchart("graph LR;X[Original]-->Y", config={"fontSize": 24})
        with self.assertRaises(MermaidError):
            parse_flowchart("graph TD;X[Broken")
        second = parse_flowchart("graph TD;A[New]")
        self.assertEqual(semantic(first), ([("X", "Original"), ("Y", "Y")], [("X", "Y")]))
        self.assertEqual(semantic(second), ([("A", "New")], []))
        self.assertEqual(second.config.font_size, 14)
        self.assertEqual(second.config.site_font_size, 16)
        self.assertEqual(second.direction, "TD")

    def test_model_is_immutable(self):
        diagram = parse_flowchart("graph TD;A")
        with self.assertRaises(FrozenInstanceError):
            diagram.nodes[0].label = "Changed"


class ConfigurationTests(unittest.TestCase):
    def test_source_defaults(self):
        config = resolve_config()
        self.assertEqual((config.layout, config.theme, config.look), ("elk", "redux-color", "neo"))
        self.assertEqual(config.font_family, '"Recursive Variable", arial, sans-serif')
        self.assertEqual(config.site_font_family, '"trebuchet ms", verdana, arial, sans-serif;')
        self.assertEqual((config.font_size, config.site_font_size), (14, 16))
        self.assertEqual((config.node_padding, config.diagram_padding), (15, 8))
        self.assertEqual((config.node_spacing, config.rank_spacing), (50, 50))
        self.assertEqual((config.fill, config.stroke, config.text_color, config.edge_color, config.background),
                         ("#ffffff", "#28253D", "#28253D", "#000000", "#ffffff"))
        self.assertEqual((config.padding_x, config.padding_y, config.min_node_width, config.wrapping_width),
                         (16, 12, 120, 120))
        self.assertEqual((config.node_stroke_width, config.edge_stroke_width), (2, 2))
        self.assertEqual((config.shadow_offset_x, config.shadow_offset_y, config.shadow_opacity), (4, 4, 0.06))
        self.assertEqual((config.html_labels, config.line_height), (True, 1.5))
        self.assertEqual((config.max_text_size, config.max_edges), (50000, 500))

    def test_supported_overrides_and_input_unchanged(self):
        supplied = {"fontFamily": "Arial", "fontSize": 20, "maxTextSize": 1234, "maxEdges": 12,
                    "flowchart": {"padding": 3.5, "diagramPadding": 10, "nodeSpacing": 25, "rankSpacing": 30}}
        original = copy.deepcopy(supplied)
        config = resolve_config(supplied)
        self.assertEqual((config.font_family, config.font_size), ("Arial", 14))
        self.assertEqual((config.site_font_family, config.site_font_size), ("Arial", 20))
        self.assertEqual((config.node_padding, config.diagram_padding, config.node_spacing, config.rank_spacing),
                         (3.5, 10, 25, 30))
        self.assertEqual((config.max_text_size, config.max_edges), (1234, 12))
        self.assertEqual(supplied, original)
        self.assertEqual(resolve_config().node_padding, 15)

    def test_html_labels_precedence_and_nullish_fallback(self):
        cases = [({}, True), ({"htmlLabels": False}, False), ({"flowchart": {"htmlLabels": False}}, False),
                 ({"htmlLabels": True, "flowchart": {"htmlLabels": False}}, True),
                 ({"htmlLabels": False, "flowchart": {"htmlLabels": True}}, False),
                 ({"htmlLabels": None, "flowchart": {"htmlLabels": False}}, False),
                 ({"flowchart": {"htmlLabels": None}}, True)]
        for supplied, expected in cases:
            with self.subTest(supplied=supplied):
                config = resolve_config(supplied)
                self.assertIs(config.html_labels, expected)
                self.assertEqual(config.line_height, 1.5 if expected else 1.1)

    def test_diagram_appearance_and_site_font_are_distinct(self):
        config = resolve_config({"fontSize": 30, "flowchart": {"theme": "redux-color", "look": "neo"}})
        self.assertEqual((config.theme, config.look), ("redux-color", "neo"))
        self.assertEqual(config.font_size, 14)
        self.assertEqual(config.site_font_size, 30)
        self.assertEqual(config.font_family, '"Recursive Variable", arial, sans-serif')

    def test_minimum_label_width_and_wrapping_configuration(self):
        config = resolve_config({"flowchart": {"minNodeWidth": 90, "wrappingWidth": 180, "padding": 2}})
        self.assertEqual((config.min_node_width, config.wrapping_width), (90, 180))
        self.assertEqual(config.node_padding, 2)
        # Neo rectangle padding is look-specific, not the legacy padding option.
        self.assertEqual((config.padding_x, config.padding_y), (16, 12))

    def test_unknown_and_unsupported_options_rejected(self):
        cases = [{"layout": "dagre"}, {"unknown": 1}, {"flowchart": {"layout": "dagre"}}]
        for supplied in cases:
            with self.subTest(supplied=supplied):
                with self.assertRaises(MermaidError) as caught:
                    resolve_config(supplied)
                self.assertEqual(caught.exception.code, "UNSUPPORTED_CONFIG")

    def test_f013_promoted_configuration_has_positive_semantics(self):
        for theme in ('dark', 'default'):
            with self.subTest(theme=theme): self.assertEqual(resolve_config({'theme': theme}).theme, theme)
        self.assertEqual(resolve_config({'look': 'classic'}).look, 'classic')
        self.assertEqual(resolve_config({'securityLevel': 'loose'}).security_level, 'loose')
        self.assertEqual(resolve_config({'theme': 'base', 'themeVariables': {'primaryColor': 'red'}}).fill, 'red')
        self.assertIs(resolve_config({'htmlLabels': 'false'}).html_labels, False)
        # assignWithDepth ignores null rather than erasing a default number.
        self.assertEqual(resolve_config({'flowchart': {'padding': None}}).node_padding, 15)
        for value in (None, []):
            with self.subTest(flowchart=value): self.assertEqual(resolve_config({'flowchart': value}).wrapping_width, 120)

    def test_f014_promoted_static_configuration(self):
        cfg=resolve_config({'look':'handDrawn','handDrawnSeed':19,'flowchart':{'curve':'step'}})
        self.assertEqual((cfg.look,cfg.hand_drawn_seed,cfg.curve),('handDrawn',19,'step'))

    def test_invalid_numeric_values_rejected(self):
        cases = [{"fontSize": 0}, {"fontSize": -1}, {"fontSize": True}, {"fontSize": "20"},
                 {"fontSize": math.nan}, {"fontSize": math.inf}, {"maxTextSize": -1}, {"maxEdges": 1.5},
                 {"flowchart": {"nodeSpacing": -1}}, {"flowchart": {"rankSpacing": 1.5}},
                 {"flowchart": {"diagramPadding": math.inf}},
                 {"flowchart": {"minNodeWidth": -1}}, {"flowchart": {"wrappingWidth": math.nan}}]
        for supplied in cases:
            with self.subTest(supplied=supplied):
                with self.assertRaises(MermaidError) as caught:
                    resolve_config(supplied)
                self.assertEqual(caught.exception.code, "INVALID_CONFIG")

    def test_zero_spacing_and_padding_allowed(self):
        config = resolve_config({"flowchart": {"nodeSpacing": 0, "rankSpacing": 0,
                                              "padding": 0, "diagramPadding": 0}})
        self.assertEqual((config.node_spacing, config.rank_spacing, config.node_padding, config.diagram_padding),
                         (0, 0, 0, 0))

    def test_wrong_configuration_shapes_rejected(self):
        cases = [[], "elk", 1,
                 {"fontFamily": ""}, {"fontFamily": "Arial\nInjected"}]
        for supplied in cases:
            with self.subTest(supplied=supplied):
                with self.assertRaises(MermaidError):
                    resolve_config(supplied)


if __name__ == "__main__":
    unittest.main()
