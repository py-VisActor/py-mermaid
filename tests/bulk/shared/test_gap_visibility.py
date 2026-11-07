"""Static createText.ts HTML/SVG visibility cascade, independent of opacity.

The original label is attached to the browser with its authored CSS. A hidden
parent's child can select visibility:visible; opacity:0 cannot be undone there.
Both still reserve their normal layout space. Original capture accompanies this
contract; these assertions inspect actual native measured runs/paint.
"""
import unittest

from py_mermaid import parse
from py_mermaid.rendering.skia.session import CanvasSession


def measured(markup):
    diagram = parse('flowchart LR\nA["' + markup + '"]', config={'securityLevel': 'loose'})
    session = CanvasSession(backend='cpu')
    return session, session.measure(diagram)[0]


class VisibilityGapContracts(unittest.TestCase):
    def test_visible_child_can_override_hidden_ancestor(self):
        session, label = measured("<span style='visibility:hidden'>Hidden<span style='visibility:visible'>Visible</span></span>")
        self.assertEqual(''.join(r.text for r in label.runs if r.opacity > 0), 'Visible')
        self.assertTrue(any('Hidden' in r.text and r.opacity == 0 for r in label.runs))

    def test_hidden_state_is_inherited_without_explicit_child_override(self):
        session, label = measured("<span style='visibility:hidden'>Hidden<span>AlsoHidden</span></span>Shown")
        self.assertEqual(''.join(r.text for r in label.runs if r.opacity > 0), 'Shown')

    def test_visibility_does_not_reset_real_ancestor_opacity(self):
        session, label = measured("<span style='opacity:0;visibility:hidden'><span style='visibility:visible'>Hidden</span></span>Shown")
        self.assertEqual(''.join(r.text for r in label.runs if r.opacity > 0), 'Shown')

    def test_hidden_label_keeps_layout_advance(self):
        session, label = measured("<span style='visibility:hidden'>Hidden</span>")
        self.assertGreater(label.width, 0)
        self.assertTrue(all(r.opacity == 0 for r in label.runs))


if __name__ == '__main__':
    unittest.main()
