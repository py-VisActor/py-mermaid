"""Mermaid source math branch/native pixels, independent of its private helpers.

Expected scale/escaping/branching comes from fixed createText/common.ts and
KaTeX SCSS/metrics. Actual API uses real ELK. Fault controls alter decoded pixels
or native math draw, never the expected source formula.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
import json,math,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from py_mermaid.api import parse,render
from py_mermaid.rendering.skia import CanvasSession
from py_mermaid.model.flowchart import MermaidError
from py_katex.model import Glyph,Rule


def src(label):return 'flowchart TD\nA["'+label+'"]'

def image(result):
    im=Image.open(BytesIO(result.data));im.load();return im.convert('RGB')

def pixels(im,box):
    return tuple(im.crop((max(0,math.floor(box.x)),max(0,math.floor(box.y)),min(im.width,math.ceil(box.x+box.width)),min(im.height,math.ceil(box.y+box.height)))).getdata())

def assert_math_visible(result,expected=None,im=None):
    im=im or image(result);events=[event for event in result.trace if event.kind=='math']
    assert events,'no mathematical draw event'
    if expected is not None:assert {event.text for event in events}==set(expected)
    for event in events:
        colors=pixels(im,event.box)
        assert sum(max(abs(channel-255) for channel in p)>90 for p in colors)>2,(event.semantic_id,'missing formula ink')
    return events

class MathIntegrationTests(unittest.TestCase):
    def test_node_mixed_label_real_pixels_and_source_scale(self):
        r=render(src('Before $$x^2$$ after'),backend='cpu');events=assert_math_visible(r,{'x^2'})
        node=r.measured[0];mathrun=next(run for run in node.runs if run.kind=='math')
        self.assertAlmostEqual(mathrun.font_size,14*1.21)
        self.assertTrue(any(run.text.strip()=='Before' for run in node.runs));self.assertTrue(any(run.text.strip()=='after' for run in node.runs))
        self.assertEqual(events[0].semantic_id,'A');self.assertTrue(any(e.kind=='math-glyph' and e.text=='2' for e in r.trace))
        self.assertGreater(node.label_height,mathrun.ascent+mathrun.descent-1e-6)

    def test_formula_geometry_uses_fixed_bundled_metric_not_plain_text(self):
        r=render(src('$$x$$'),backend='cpu');run=next(x for x in r.measured[0].runs if x.kind=='math')
        # KaTeX fontMetricsData Math-Italic x = depth0,height.43056,
        # italic0,skew.02778,width.57153 (source metrics, not a layout helper).
        self.assertAlmostEqual(run.width,.57153*14*1.21,places=5)
        self.assertAlmostEqual(run.ascent,.43056*14*1.21,places=5)
        self.assertAlmostEqual(run.descent,0,places=5);assert_math_visible(r,{'x'})

    def test_node_edge_group_math_via_real_public_api(self):
        text='flowchart TD\nsubgraph G["Group $$g_1$$"]\nA["Node $$x^2$$"] -->|"Edge $$y_2$$"| B["End"]\nend'
        r=render(text,backend='cpu');events=assert_math_visible(r,{'g_1','x^2','y_2'})
        self.assertEqual(len(events),3)
        self.assertTrue(any(run.kind=='math' for run in r.annotations.groups[0].runs))
        self.assertTrue(any(run.kind=='math' for run in r.annotations.edge_labels[0].runs))
        self.assertTrue(all(event.box.width>0 and event.box.height>0 for event in events))

    def test_metadata_math_uses_same_safe_formula_pipeline(self):
        # YAML double-quoted scalar: two actual slashes encode one literal.
        text='flowchart TD\n'+r'A@{ shape: rect, label: "$$\\nu<y$$", labelType: text }'
        r=render(text,backend='cpu');assert_math_visible(r,{r'\nu<y'})
        glyphs=[event.text for event in r.trace if event.kind=='math-glyph']
        self.assertIn('\u03bd',glyphs);self.assertIn('<',glyphs)
        self.assertTrue(r.diagram.nodes[0].raw_label)

    def test_source_linebreaks_preserve_math_and_plain_rows(self):
        r=render(src('Top $$x$$<br/>Plain<br/>Bottom $$y$$'),backend='cpu');events=assert_math_visible(r,{'x','y'})
        positions={event.text:event.box.y for event in events};self.assertLess(positions['x'],positions['y'])
        self.assertEqual(len(r.measured[0].lines),3)
        self.assertTrue(any('Plain' in run.text for run in r.measured[0].runs))

    def test_htmlfalse_keeps_formula_literal_and_no_math_draw(self):
        r=render(src('Before $$x^2$$ after'),config={'htmlLabels':False},backend='cpu')
        self.assertFalse(any(run.kind=='math' for run in r.measured[0].runs))
        self.assertFalse(any(e.kind.startswith('math') for e in r.trace))
        visible=''.join(run.text for run in r.measured[0].runs)
        self.assertIn('$$x^2$$',visible)
        text=[e for e in r.trace if e.kind=='text' and '$$x^2$$' in (e.text or '')]
        self.assertTrue(text);self.assertGreater(sum(max(p)<150 for p in pixels(image(r),text[0].box)),2)

    def test_math_branch_markdown_surroundings_remain_source_literal(self):
        # createText computes markdownHTML then deliberately chooses original
        # inputForKatex whenever hasKatex(text), so ** is visible punctuation.
        r=render('flowchart TD\nA["`**Before** $$x$$ after`"]',backend='cpu')
        assert_math_visible(r,{'x'});plain=''.join(run.text for run in r.measured[0].runs if run.kind=='text')
        self.assertIn('**Before**',plain)
        self.assertFalse(any(run.font_weight in ('bold','700') for run in r.measured[0].runs))

    def test_math_lines_source_nowrap_despite_small_wrapping_width(self):
        label='LongPrefix $$x^2$$ LongSuffix'
        r=render(src(label),config={'flowchart':{'wrappingWidth':25,'minNodeWidth':0}},backend='cpu')
        self.assertEqual(len(r.measured[0].lines),1);assert_math_visible(r,{'x^2'})
        self.assertGreater(r.measured[0].label_width,25)

    def test_tex_less_than_ampersand_and_commands_protected_from_html(self):
        r=render(src(r'$$\begin{matrix}x<y&\nu\\\\1&\neq\end{matrix}$$'),backend='cpu')
        events=assert_math_visible(r)
        self.assertIn('<y',events[0].text);self.assertIn('&',events[0].text)
        glyphs=[e.text for e in r.trace if e.kind=='math-glyph']
        self.assertIn('\u03bd',glyphs);self.assertIn('1',glyphs)
        # \nu must not be transformed by plain-label literal \n normalization.
        self.assertFalse(any(e.kind=='text' and 'u'==(e.text or '').strip() for e in r.trace))

    def test_mermaid_actual_double_slash_collapses_once_matrix_two_rows(self):
        tex=r'\begin{matrix}1&2\\\\3&4\end{matrix}'
        r=render(src('$$'+tex+'$$'),backend='cpu');assert_math_visible(r,{tex})
        glyphs=[e for e in r.trace if e.kind=='math-glyph' and e.text in '1234']
        self.assertEqual(len(glyphs),4)
        pos={e.text:e.points[0] for e in glyphs}
        self.assertLess(pos['1'].y,pos['3'].y);self.assertLess(pos['1'].x,pos['2'].x)

    def test_non_dotall_regex_does_not_join_formula_across_real_newline(self):
        d=parse(src('$$x\ny$$'));s=CanvasSession('cpu');m=s.measure(d)
        self.assertFalse(any(run.kind=='math' for run in m[0].runs))
        self.assertIn('$$',''.join(run.text for run in m[0].runs))

    def test_invalid_formula_returns_explicit_diagnostic_not_text_or_white_success(self):
        for tex in (r'\definitelyUnknownControl',r'\frac{1}{',r'\begin{matrix}1&2'):
            with self.subTest(tex=tex),self.assertRaises(MermaidError) as caught:render(src('$$'+tex+'$$'),backend='cpu')
            self.assertTrue(caught.exception.code.startswith('MATH_'))
            self.assertIn('offset',str(caught.exception))

    def test_source_math_font_size_follows_actual_label_css(self):
        r=render(src('$$x$$'),config={'themeCSS':'.nodeLabel {font-size:20px;color:#d02030;}'},backend='cpu')
        run=next(run for run in r.measured[0].runs if run.kind=='math');self.assertAlmostEqual(run.font_size,24.2)
        event=assert_math_visible(r,{'x'})[0];colors=pixels(image(r),event.box)
        self.assertGreater(sum(p[0]>100 and p[0]>p[1]*1.7 and p[0]>p[2]*1.4 for p in colors),2)

    def test_pixel_oracle_rejects_blank_image_even_with_correct_trace(self):
        r=render(src(r'$$\frac{x}{2}$$'),backend='cpu');assert_math_visible(r)
        with self.assertRaises(AssertionError):assert_math_visible(r,im=Image.new('RGB',(r.width,r.height),'white'))

    def test_noop_native_math_draw_is_detected_by_actual_pixels(self):
        with patch('py_katex.canvas.draw',return_value=None):r=render(src('$$x$$'),backend='cpu')
        self.assertTrue(any(e.kind=='math' for e in r.trace))
        with self.assertRaises(AssertionError):assert_math_visible(r)

    def test_repeat_session_cache_keeps_formula_and_style_separate(self):
        s=CanvasSession('cpu')
        first=s.measure(parse(src('$$x$$')))[0];other=s.measure(parse(src('$$y$$')))[0];again=s.measure(parse(src('$$x$$')))[0]
        a=next(x for x in first.runs if x.kind=='math');b=next(x for x in other.runs if x.kind=='math');c=next(x for x in again.runs if x.kind=='math')
        self.assertEqual(a,c);self.assertNotEqual(a.math_key,b.math_key)
        red=s.measure(parse(src('$$x$$'),config={'themeCSS':'.nodeLabel{color:red}'}))[0]
        self.assertNotEqual(a.math_key,next(x for x in red.runs if x.kind=='math').math_key)

    def test_session_owner_thread_guard_including_math_measure(self):
        s=CanvasSession('cpu');d=parse(src('$$x$$'))
        def attempt():
            try:s.measure(d);return None
            except MermaidError as exc:return exc.code
        with ThreadPoolExecutor(max_workers=1) as pool:code=pool.submit(attempt).result()
        self.assertEqual(code,'THREAD_OWNERSHIP')

if __name__=='__main__':unittest.main()
