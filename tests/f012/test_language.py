"""Independent F01.2 language/config expectations from pinned upstream sources.

The fixtures are handwritten, never generated from candidate parser output.
Official-invalid negatives and slice exclusions are deliberately separate.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import unittest

from py_mermaid.config import resolve_config
from py_mermaid.model.flowchart import MermaidError
from py_mermaid.parsing import parse_flowchart


FIXTURES = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf8"))


class EnhancedLanguageTests(unittest.TestCase):
    def test_handwritten_positive_semantics(self):
        for case in FIXTURES["cases"]:
            with self.subTest(case=case["id"]):
                diagram = parse_flowchart(case["text"], config=case.get("config"))
                self.assertEqual([[n.id, n.label] for n in diagram.nodes], case["nodes"])
                self.assertEqual([[e.source, e.target] for e in diagram.edges], case["edges"])
                self.assertEqual(diagram.direction, case["direction"])
                self.assertEqual([edge.label for edge in diagram.edges],
                                 case.get("edgeLabels", [""] * len(case["edges"])))
                for node in diagram.nodes:
                    self.assertEqual(node.shape, case.get("shapes", {}).get(node.id, "square"))
                self.assertEqual([
                    {"id": g.id, "label": g.label, "members": list(g.members),
                     "parent_id": g.parent_id, "direction": g.direction}
                    for g in diagram.groups], case.get("groups", []))

    def test_shape_fixture_denominator_is_complete(self):
        expected = {"square", "round", "stadium", "subroutine", "cylinder", "circle", "doublecircle",
                    "diamond", "hexagon", "odd", "trapezoid", "inv_trapezoid", "lean_right", "lean_left"}
        self.assertEqual({case["shapes"]["A"] for case in FIXTURES["cases"]
                          if case["id"].startswith("shape-")}, expected)
        self.assertEqual(len(expected), 14)

    def test_shape_redeclaration_updates_but_bare_reference_preserves(self):
        diagram = parse_flowchart("flowchart TD\nA[First]\nA((Second))\nA --> B[End]\nA")
        self.assertEqual([(n.id, n.shape, n.label) for n in diagram.nodes],
                         [("A", "circle", "Second"), ("B", "square", "End")])

    def test_quoted_plain_labels_across_classic_delimiters(self):
        sources = [('A("Round (text)")', "round", "Round (text)"),
                   ('A{{"Hexagon {text}"}}', "hexagon", "Hexagon {text}"),
                   ('A[\\"Lean [text]"\\]', "lean_left", "Lean [text]")]
        for syntax, kind, text in sources:
            with self.subTest(kind=kind):
                node = parse_flowchart("flowchart TD\n" + syntax).nodes[0]
                self.assertEqual((node.shape, node.label), (kind, text))

    def test_ellipse_preserves_upstream_parse_semantics(self):
        case = FIXTURES["renderErrorCases"][0]
        node = parse_flowchart(case["text"]).nodes[0]
        self.assertEqual((node.id, node.shape, node.label), ("A", "ellipse", "Ellipse"))
        self.assertEqual(case["code"], "UPSTREAM_SHAPE_MISSING")

    def test_both_edge_label_syntaxes_agree(self):
        first = parse_flowchart("flowchart TD\nA -->|Some text| B")
        second = parse_flowchart("flowchart TD\nA -- Some text --> B")
        self.assertEqual([(e.source, e.target, e.label) for e in first.edges], [("A", "B", "Some text")])
        self.assertEqual([(e.source, e.target, e.label) for e in second.edges], [("A", "B", "Some text")])

    def test_quoted_inline_edge_label(self):
        edge = parse_flowchart('flowchart LR\nA -- "Quoted (plain)" --> B').edges[0]
        self.assertEqual(edge.label, "Quoted (plain)")

    def test_multiline_edge_labels_and_link_whitespace(self):
        for source in ['flowchart TD\nA -->|"First\nSecond"| B',
                       'flowchart TD\nA -- "First\\nSecond" --> B',
                       'flowchart TD\nA -- First\nSecond --> B']:
            with self.subTest(source=source):
                self.assertEqual(parse_flowchart(source).edges[0].label, "First\nSecond")
        self.assertEqual([(e.source, e.target) for e in
                          parse_flowchart("flowchart TD\nA\n-->\nB").edges], [("A", "B")])

    def test_label_spans_use_raw_text_and_utf16_units(self):
        for syntax in ['A -->|"😀 条件"| B', 'A -- "😀 条件" --> B', 'A -->|😀 条件| B']:
            with self.subTest(syntax=syntax):
                source = "flowchart TD\r\n" + syntax
                edge = parse_flowchart(source).edges[0]
                start = source.index("😀")
                span = edge.label_span
                self.assertIsNotNone(span)
                self.assertEqual(source[span.start.index:span.end.index], "😀 条件")
                self.assertEqual(span.start.index, start)
                self.assertEqual(span.start.utf16_offset, len(source[:start].encode("utf-16-le")) // 2)
                self.assertEqual(span.end.utf16_offset - span.start.utf16_offset, 5)
                self.assertEqual(span.start.line, 2)

    def test_unlabelled_edges_have_no_label_span(self):
        edge = parse_flowchart("flowchart TD\nA --> B").edges[0]
        self.assertEqual(edge.label, "")
        self.assertIsNone(edge.label_span)

    def test_group_chain_member_order_is_source_db_order(self):
        diagram = parse_flowchart("flowchart TD\nsubgraph S\nx --> y --> z\nend")
        self.assertEqual([n.id for n in diagram.nodes], ["x", "y", "z"])
        self.assertEqual(diagram.groups[0].members, ("z", "y", "x"))

    def test_group_close_order_differs_from_colour_preorder(self):
        diagram = parse_flowchart("flowchart TD\nsubgraph O\nsubgraph I\nA\nend\nend\nsubgraph S\nB\nend")
        self.assertEqual([g.id for g in diagram.groups], ["I", "O", "S"])
        self.assertEqual({g.id: g.color_index for g in diagram.groups}, {"O": 0, "I": 1, "S": 2})
        self.assertEqual({g.id: g.parent_id for g in diagram.groups}, {"I": "O", "O": None, "S": None})

    def test_group_source_span_covers_original_block(self):
        source = 'flowchart TD\r\nsubgraph S["😀 Group"]\r\nA\r\nend'
        group = parse_flowchart(source).groups[0]
        self.assertEqual(source[group.span.start.index:group.span.end.index],
                         'subgraph S["😀 Group"]\r\nA\r\nend')
        self.assertEqual(group.span.start.line, 2)
        self.assertEqual(group.span.end.utf16_offset, len(source) + 1)

    def test_membership_and_parent_references_agree(self):
        for case in FIXTURES["cases"]:
            with self.subTest(case=case["id"]):
                diagram = parse_flowchart(case["text"], config=case.get("config"))
                objects = {item.id: item for item in (*diagram.nodes, *diagram.groups)}
                group_ids = {group.id for group in diagram.groups}
                self.assertEqual(len(objects), len(diagram.nodes) + len(diagram.groups))
                for group in diagram.groups:
                    self.assertNotIn(group.id, group.members)
                    for member in group.members:
                        self.assertIn(member, objects)
                        self.assertEqual(objects[member].parent_id, group.id)
                for obj in objects.values():
                    if obj.parent_id is not None:
                        self.assertIn(obj.parent_id, group_ids)

    def test_subgraph_direction_denominator(self):
        for direction in ("TD", "TB", "LR", "RL", "BT"):
            with self.subTest(direction=direction):
                diagram = parse_flowchart(f"flowchart TD\nsubgraph S\ndirection {direction}\nA\nend")
                self.assertEqual(diagram.direction, "TD")
                self.assertEqual(diagram.groups[0].direction, direction)

    def test_last_subgraph_direction_wins(self):
        diagram = parse_flowchart("flowchart TD\nsubgraph S\ndirection LR\nA\ndirection BT\nend")
        self.assertEqual(diagram.groups[0].direction, "BT")

    def test_absent_direction_is_none_by_default(self):
        diagram = parse_flowchart("flowchart LR\nsubgraph S\nA\nend")
        self.assertIsNone(diagram.groups[0].direction)

    def test_inherit_direction_uses_root_not_parent_override(self):
        source = "flowchart LR\nsubgraph O\ndirection TB\nsubgraph I\nA\nend\nend"
        diagram = parse_flowchart(source, config={"flowchart": {"inheritDir": True}})
        self.assertEqual({g.id: g.direction for g in diagram.groups}, {"I": "LR", "O": "TB"})

    def test_automatic_counter_includes_explicit_declarations(self):
        diagram = parse_flowchart('flowchart TD\nsubgraph Explicit\nA\nend\nsubgraph "Automatic Title"\nB\nend')
        self.assertEqual([g.id for g in diagram.groups], ["Explicit", "subGraph1"])

    def test_forward_group_reference_does_not_create_duplicate_node(self):
        source = "flowchart TD\nG --> Z\nsubgraph G[Later]\nA\nend"
        diagram = parse_flowchart(source)
        self.assertEqual([n.id for n in diagram.nodes], ["Z", "A"])
        self.assertEqual([g.id for g in diagram.groups], ["G"])
        self.assertEqual((diagram.edges[0].source, diagram.edges[0].target), ("G", "Z"))

    def test_repeated_group_keeps_first_title_and_direction(self):
        source = "flowchart TD\nsubgraph S[First]\ndirection LR\nx\nend\nsubgraph S[Second]\ndirection BT\ny\nend"
        group = parse_flowchart(source).groups[0]
        self.assertEqual((group.label, group.direction, group.members), ("First", "LR", ("x", "y")))

    def test_group_and_label_state_isolated_after_failure(self):
        first = parse_flowchart("flowchart TD\nsubgraph S\nA -->|Original| B\nend")
        with self.assertRaises(MermaidError):
            parse_flowchart("flowchart TD\nsubgraph Broken\nA")
        second = parse_flowchart("flowchart TD\nA --> B")
        self.assertEqual(first.groups[0].id, "S")
        self.assertEqual(first.edges[0].label, "Original")
        self.assertFalse(second.groups)
        self.assertEqual(second.edges[0].label, "")
        self.assertIsNone(second.nodes[0].parent_id)
        with self.assertRaises(FrozenInstanceError):
            first.groups[0].label = "Changed"

    def test_official_invalid_sources_rejected_with_spans(self):
        for case in FIXTURES["negativeCases"]:
            with self.subTest(case=case["id"]):
                with self.assertRaises(MermaidError) as caught:
                    parse_flowchart(case["text"])
                self.assertIsNotNone(caught.exception.span)
                self.assertLessEqual(caught.exception.span.end.index, len(case["text"]))

    def test_f014_remaining_scope_items_promoted_with_source_semantics(self):
        node=parse_flowchart('flowchart TD\nA@{ shape: hourglass }').nodes[0]
        self.assertEqual((node.id,node.shape,node.label),('A','hourglass','A'))
        node=parse_flowchart('flowchart TD\nA[|key:value|Text]').nodes[0]
        self.assertEqual((node.label,dict(node.props)),('Text',{'key':'value'}))
        self.assertEqual(parse_flowchart('flowchart TD\nA; style A fill:red').nodes[0].styles,('fill:red',))
        diagram=parse_flowchart('flowchart TD\nA & B --> C')
        self.assertEqual([(e.source,e.target) for e in diagram.edges],[('A','C'),('B','C')])

    def test_f013_rich_labels_promoted_with_concrete_semantics(self):
        edge = parse_flowchart('flowchart TD\nA -->|"<b>Rich</b>"| B').edges[0]
        self.assertEqual((edge.label, edge.label_kind), ('<b>Rich</b>', 'text'))
        node = parse_flowchart('flowchart TD\nA["`Markdown`"]', config={'htmlLabels': False}).nodes[0]
        self.assertEqual((node.label, node.label_kind), ('Markdown', 'markdown'))



class EnhancedConfigurationTests(unittest.TestCase):
    def test_new_defaults_and_title_margin_values(self):
        defaults = resolve_config()
        self.assertIs(defaults.inherit_direction, False)
        self.assertEqual((defaults.group_title_top_margin, defaults.group_title_bottom_margin), (0, 0))
        source_config = {"flowchart": {"inheritDir": True, "subGraphTitleMargin": {"top": 3, "bottom": 7}}}
        resolved = resolve_config(source_config)
        self.assertIs(resolved.inherit_direction, True)
        self.assertEqual((resolved.group_title_top_margin, resolved.group_title_bottom_margin), (3, 7))
        self.assertEqual(source_config["flowchart"]["subGraphTitleMargin"], {"top": 3, "bottom": 7})

    def test_partial_title_margin_preserves_default(self):
        config = resolve_config({"flowchart": {"subGraphTitleMargin": {"top": 4}}})
        self.assertEqual((config.group_title_top_margin, config.group_title_bottom_margin), (4, 0))

    def test_f013_null_margin_preserves_default_via_assign_with_depth(self):
        cfg = resolve_config({'flowchart': {'subGraphTitleMargin': None}})
        self.assertEqual((cfg.group_title_top_margin, cfg.group_title_bottom_margin), (0, 0))

    def test_invalid_group_configuration_rejected(self):
        configs = [{"inheritDir": "true"}, {"inheritDir": 1},
                   {"subGraphTitleMargin": {"left": 5}}, {"subGraphTitleMargin": {"top": -1}},
                   {"subGraphTitleMargin": {"bottom": float("inf")}}]
        for config in configs:
            with self.subTest(config=config):
                with self.assertRaises(MermaidError):
                    resolve_config({"flowchart": config})


if __name__ == "__main__":
    unittest.main()
