import unittest
from ._support import semantic,assert_png,assert_text_pixels


class InfoSemantics(unittest.TestCase):
    def test_show_info_flag_and_source_title(self):
        self.assertFalse(semantic('info').model.show_info)
        d=semantic('info showInfo\ntitle Source title')
        self.assertTrue(d.model.show_info);self.assertEqual(d.model.title,'Source title')

    def test_unknown_body_rejected_with_exact_family_error(self):
        from py_mermaid import MermaidError
        with self.assertRaises(MermaidError) as caught:semantic('info\nthis is not info syntax')
        self.assertEqual(caught.exception.code,'SYNTAX_ERROR');self.assertIsNotNone(caught.exception.span)


class InfoNative(unittest.IsolatedAsyncioTestCase):
    async def test_source_version_at_source_viewport_and_real_ink(self):
        from py_mermaid import arender
        result=await arender('info showInfo',backend='cpu');image=assert_png(self,result)
        self.assertEqual((result.width,result.height),(400,100))
        event=next(e for e in result.trace if e.text=='v12.2.0')
        self.assertEqual(event.font_size,32);assert_text_pixels(self,image,event)
        self.assertAlmostEqual(event.box.x+event.box.width/2,100,delta=8)
