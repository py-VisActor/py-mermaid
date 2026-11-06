"""Original sequence svgDraw drawLoop/static filter contracts."""
import unittest
from ._support import assert_png,assert_text_pixels

class SequenceSourcePaint(unittest.IsolatedAsyncioTestCase):
    async def test_control_brackets_center_and_inline_section_dash(self):
        from py_mermaid import arender
        result=await arender('sequenceDiagram\ncritical Transaction\nA->>B: Commit\noption Unavailable\nB-->>A: Abort\nend',backend='cpu');image=assert_png(self,result)
        labels=[e for e in result.trace if e.kind in ('fragment-title','fragment-section') and e.text]
        self.assertEqual([e.text for e in labels],['[Transaction]','[Unavailable]'])
        for e in labels:assert_text_pixels(self,image,e)
        self.assertTrue(all(e.dash==(3.,3.) for e in result.trace if e.kind=='fragment-divider'))
        section=next(e for e in labels if e.text=='[Unavailable]');border=next(e for e in result.trace if e.kind=='fragment')
        self.assertAlmostEqual(section.box.x+section.box.width/2,border.box.x+border.box.width/2,delta=2)
        for css,expected in (('.loopLine{stroke-dasharray:1,1}',(3.,3.)),('.loopLine{stroke-dasharray:1,1!important}',(1.,1.))):
            styled=await arender('sequenceDiagram\nalt First\nA->>B: One\nelse Second\nB->>A: Two\nend',backend='cpu',config={'themeCSS':css})
            self.assertTrue(all(e.dash==expected for e in styled.trace if e.kind=='fragment-divider'))
    async def test_source_dangling_css_shadow_not_invented_for_note(self):
        from py_mermaid import arender
        result=await arender('sequenceDiagram\nparticipant A\nNote over A: Visible note',backend='cpu');image=assert_png(self,result)
        # svgDraw.js assigns presentation stroke-width=.5px, but styles.js
        # `.actor-man circle, line {stroke-width:2px}` targets every line.
        # The stylesheet therefore wins for lifelines as well as actor limbs.
        lifelines=[e for e in result.trace if e.kind=='lifeline']
        self.assertTrue(lifelines)
        self.assertTrue(all(e.stroke_width==2 for e in lifelines))
        # CSS note url(#drop-shadow) has no matching definition; actor inline
        # prefixed filter is independent and remains supported.
        note=next(e for e in result.trace if e.kind=='note')
        self.assertFalse(any(e.kind=='shadow' and e.semantic_id==note.semantic_id for e in result.trace))
        event=next(e for e in result.trace if e.text=='Visible note');assert_text_pixels(self,image,event)
