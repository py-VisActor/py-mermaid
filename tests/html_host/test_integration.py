"""Diagram-level static host contracts beyond isolated widget layout."""
import unittest

from py_mermaid import parse
from py_mermaid.rendering.skia.session import CanvasSession


def measured(markup):
    diagram=parse('flowchart LR\nA["'+markup+'"]',config={'securityLevel':'loose'})
    return CanvasSession('cpu').measure(diagram)[0]


def controls(nodes):
    return {dict(run.control.spec.attributes).get('id'):run.control.spec
        for node in nodes for run in node.runs if run.control is not None}


class DiagramHostIntegration(unittest.TestCase):
    def test_parent_explicit_line_height_keeps_its_strut_around_small_control(self):
        label=measured("<span style='line-height:100px'><input value='Small'></span>")
        self.assertGreaterEqual(label.label_height,100)

    def test_explicit_block_control_places_following_text_on_next_line(self):
        label=measured("Before<input value='Block' style='display:block;width:100px;height:20px'>After")
        before=next(r for r in label.runs if 'Before' in r.text)
        after=next(r for r in label.runs if 'After' in r.text)
        widget=next(r for r in label.runs if r.control)
        self.assertLess(before.baseline,widget.baseline)
        self.assertLess(widget.baseline,after.baseline)

    def test_inline_control_ua_display_does_not_inherit_block_parent(self):
        # Keep the pair below the label wrapping width so this probes display
        # inheritance rather than the independent atomic inline-wrap rule.
        label=measured("<div><input size='1' value='One'><input size='1' value='Two'></div>")
        widgets=[r for r in label.runs if r.control]
        self.assertEqual(len(widgets),2)
        self.assertAlmostEqual(widgets[0].baseline,widgets[1].baseline)

    def test_cross_node_radio_group_is_initially_exclusive(self):
        diagram=parse('flowchart LR\nA["<input id=\'a\' type=\'radio\' name=\'group\' checked>"] --> B["<input id=\'b\' type=\'radio\' name=\'group\' checked>"]',config={'securityLevel':'loose'})
        state=controls(CanvasSession('cpu').measure(diagram))
        self.assertFalse(state['a'].checked);self.assertTrue(state['b'].checked)

    def test_cross_node_forms_remain_independent(self):
        diagram=parse('flowchart LR\nA["<form id=\'fa\'><input id=\'a\' type=\'radio\' name=\'group\' checked></form>"] --> B["<form id=\'fb\'><input id=\'b\' type=\'radio\' name=\'group\' checked></form>"]',config={'securityLevel':'loose'})
        state=controls(CanvasSession('cpu').measure(diagram))
        self.assertTrue(state['a'].checked);self.assertTrue(state['b'].checked)

    def test_radio_state_does_not_leak_to_next_request_in_same_session(self):
        session=CanvasSession('cpu')
        first=parse('flowchart LR\nA["<input id=\'a\' type=\'radio\' name=\'group\' checked>"] --> B["<input id=\'b\' type=\'radio\' name=\'group\' checked>"]',config={'securityLevel':'loose'})
        session.measure(first)
        second=parse('flowchart LR\nC["<input id=\'c\' type=\'radio\' name=\'group\' checked>"]',config={'securityLevel':'loose'})
        state=controls(session.measure(second));self.assertEqual(set(state),{'c'});self.assertTrue(state['c'].checked)
