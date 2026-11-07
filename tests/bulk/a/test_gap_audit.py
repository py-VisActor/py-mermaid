"""G01 source-derived regressions, designed without invoking the candidate.

Source anchors and hashes: references/gap-audit-A.json. These tests deliberately
compose previously separate features; old acceptance is not their expectation.
"""
import unittest

from py_mermaid.runtime.registry import parse_diagram
from py_mermaid.model.flowchart import MermaidError
from .test_paint_contracts import picture, paths, visible


class GapLanguageSourceTests(unittest.TestCase):
    def test_packet_title_stops_at_common_inline_comment(self):
        diagram = parse_diagram('packet\ntitle Register %% hidden\n0: "X"')
        self.assertEqual(diagram.model.title, 'Register')
        self.assertEqual(diagram.model.words[0][0].label, 'X')

    def test_packet_title_converter_collapses_horizontal_whitespace(self):
        diagram = parse_diagram('packet\ntitle Register   Map\n0: "X"')
        self.assertEqual(diagram.model.title, 'Register Map')

    def test_packet_title_quoted_field_percent_is_not_comment(self):
        diagram = parse_diagram('packet\ntitle Register %% hidden\n0: "%% data"')
        self.assertEqual(diagram.model.title, 'Register')
        self.assertEqual(diagram.model.words[0][0].label, '%% data')

    def test_class_cssclass_normalizes_generic_target(self):
        diagram = parse_diagram('classDiagram\nclass A~T~\ncssClass "A~T~" red\nclassDef red fill:#ff0000')
        a = next(node for node in diagram.model.classes if node.id == 'A')
        self.assertEqual(a.generic_type, 'T')
        self.assertIn('red', a.classes)

    def test_class_cssclass_normalizes_each_comma_separated_target(self):
        diagram = parse_diagram('classDiagram\nclass A~T~\nclass B~U~\ncssClass "A~T~,B~U~" red')
        self.assertEqual({node.id for node in diagram.model.classes}, {'A', 'B'})
        for node in diagram.model.classes:
            self.assertIn('red', node.classes)

    def reject_syntax(self, source):
        with self.assertRaises(MermaidError) as caught:
            parse_diagram(source)
        self.assertEqual(caught.exception.code, 'SYNTAX_ERROR')

    def test_block_empty_quoted_label_has_no_str_token(self):
        self.reject_syntax('block\nA[""]')

    def test_block_empty_composite_has_no_document(self):
        self.reject_syntax('block\nblock:X\nend')

    def test_kanban_empty_quoted_label_has_no_node_descr(self):
        self.reject_syntax('kanban\nTodo\n  item[""]')

    def test_block_nonempty_quoted_label_control(self):
        diagram = parse_diagram('block\nA["Alpha"]')
        self.assertEqual(next(n for n in diagram.model.nodes if n.id == 'A').label, 'Alpha')

    def test_block_nonempty_composite_control(self):
        diagram = parse_diagram('block\nblock:X\nA["Alpha"]\nend')
        nodes = {n.id: n for n in diagram.model.nodes}
        self.assertEqual(nodes['A'].parent, 'X')
        self.assertIn('A', nodes['X'].children)

    def test_kanban_nonempty_quoted_label_control(self):
        diagram = parse_diagram('kanban\nTodo\n  item["Alpha"]')
        node = next(n for n in diagram.model.nodes if n.id == 'item')
        self.assertEqual(node.label, 'Alpha')
        self.assertEqual(node.parent, 'Todo')


class GapPaintSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_packet_comment_never_becomes_visible_title(self):
        result = await picture('packet\ntitle Register   Map %% hidden\n0: "X"')
        title = [e.text for e in result.trace if e.kind == 'title' and e.opacity > 0]
        self.assertEqual(title, ['Register Map'])
        self.assertNotIn('hidden', visible(result))

    async def test_generic_cssclass_reaches_real_node_fill(self):
        result = await picture('classDiagram\nclass A~T~\ncssClass "A~T~" red\nclassDef red fill:#ff0000')
        body = paths(result, id='A')[0]
        self.assertEqual(body.fill.lower(), '#ff0000')
        self.assertIn('A', visible(result))
