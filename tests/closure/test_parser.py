"""Closure source assertions: pinned Langium, ABNF, Zen Marked and C4.

Expected literals/geometry increments are independently handwritten from source
and existing actual original rejection evidence. P2 must not execute tests.
"""
import unittest
from html.parser import HTMLParser
from .helper_A import CASES,parse_case,plain,select


class ParserSourceContract(unittest.TestCase):
    pass


def install():
    for case in CASES:
        if not case['nativeChecks'] and case['expect']!='syntax_error':continue
        def test(self,case=case):
            from py_mermaid.model.flowchart import MermaidError
            if case['expect']=='syntax_error':
                with self.assertRaises(MermaidError) as caught:parse_case(case)
                self.assertIn(caught.exception.code,case['expectedErrorCodes'])
                self.assertIsNotNone(caught.exception.span)
                if case.get('errorPosition'):
                    expected=case['errorPosition'];cp=case['source'].index(expected['token'])
                    self.assertEqual(caught.exception.span.start.index,cp)
                    self.assertEqual(caught.exception.span.start.utf16_offset,len(case['source'][:cp].encode('utf-16-le'))//2)
                    self.assertEqual(caught.exception.span.start.line,expected['line'])
                    self.assertEqual(caught.exception.span.start.column,expected['column'])
                return
            model=plain(parse_case(case).model)
            for expected in case['nativeChecks']:
                with self.subTest(path=expected['path']):self.assertEqual(select(model,expected['path']),expected['equals'])
        name='test_'+case['id'].removeprefix('CLOSURE-A-').replace('-','_')
        test.__name__=name;test.__doc__=case['origin']['path']+': '+case['origin']['symbol']
        setattr(ParserSourceContract,name,test)


install()


class ZenLiteralAndFormatting(unittest.TestCase):
    def test_literal_escapes_and_real_italic_use_distinct_consumed_tokens(self):
        from py_mermaid.diagrams.zenuml.layout import _comment_markup
        class Projection(HTMLParser):
            def __init__(self):super().__init__(convert_charrefs=True);self.text=[];self.italic=False
            def handle_data(self,text):self.text.append(text)
            def handle_starttag(self,tag,attrs):self.italic|=tag in ('em','i')
        for case in CASES:
            if not case.get('commentExpected'):continue
            expected=case['commentExpected']
            with self.subTest(case=case['id']):
                actual=Projection();actual.feed(_comment_markup(expected['source']))
                self.assertEqual(''.join(actual.text),expected['visible'])
                self.assertEqual(actual.italic,expected['italic'])


class C4NativeGeometryControl(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_sprite_reservation_against_same_input_without_sprite(self):
        from py_mermaid.api import arender
        chosen={case['id']:case for case in CASES if case.get('geometryControl')}
        records=[]
        for id in ['CLOSURE-A-c4-boundary-base','CLOSURE-A-c4-boundary-unknown-sprite']:
            case=chosen[id];result=await arender(case['source'],config=case['config'],backend='cpu')
            rect=next(event for event in result.trace if event.semantic_id=='boundary' and event.kind=='c4-boundary')
            label=next(event for event in result.trace if event.semantic_id=='boundary' and event.text=='Shell')
            records.append((rect.box,label.box.y-rect.box.y))
            self.assertFalse(any(event.resource_id for event in result.trace),'Source has no sprite image paint consumer')
        self.assertAlmostEqual(records[1][1]-records[0][1],48,delta=.05)
        self.assertAlmostEqual(records[1][0].width,records[0][0].width,delta=.05)
        self.assertAlmostEqual(records[1][0].height,records[0][0].height,delta=.05)


class CynefinSvgWhitespaceDisplay(unittest.IsolatedAsyncioTestCase):
    """Original SVG .text() normal whitespace, not parser string rewriting.

    Fixed cynefinRenderer.ts:274,418,432 and styles.ts:29-93. Actual original
    XML-whitespace captures have one A B row (bbox18.03125x14), not A/B rows.
    Width/height checks use same-host controls, not hard-coded font metrics.
    """
    @staticmethod
    def _quoted(value):
        import json
        return json.dumps(value,ensure_ascii=False)

    async def _render(self, source, expected):
        from py_mermaid import arender
        result=await arender(source,config={'theme':'default','cynefin':{'seed':123}},backend='cpu')
        matches=[event for event in result.trace if event.text==expected]
        self.assertEqual(len(matches),1,'Expected exactly one actual public text draw, not separate A/B rows')
        self.assertFalse(any(event.text in ('A','B') for event in result.trace),'SVG normal whitespace must not create extra rows')
        self.assertGreater(len(result.data),0)
        return matches[0]

    async def test_item_four_ascii_whitespace_preserves_model_and_single_row_geometry(self):
        from py_mermaid import parse
        control=await self._render('cynefin-beta\nclear\n "A B"\n','A B')
        tight=await self._render('cynefin-beta\nclear\n "AB"\n','AB')
        self.assertLess(tight.box.width,control.box.width,'AB is a real negative control for lost separator')
        for raw in ('A\nB','A\rB','A\tB',' A   B '):
            with self.subTest(raw=repr(raw)):
                source='cynefin-beta\nclear\n '+self._quoted(raw)+'\n'
                self.assertEqual(dict(parse(source).model.domains)['clear'][0],raw)
                event=await self._render(source,'A B')
                self.assertAlmostEqual(event.box.width,control.box.width,delta=.01)
                self.assertAlmostEqual(event.box.height,control.box.height,delta=.01)
                self.assertAlmostEqual(event.box.y,control.box.y,delta=.01)

    async def test_transition_ascii_whitespace_preserves_model_and_single_row_geometry(self):
        from py_mermaid import parse
        def source(value):return 'cynefin-beta\nclear --> complex: '+self._quoted(value)+'\n'
        control=await self._render(source('A B'),'A B')
        for raw in ('A\nB','A\rB','A\tB',' A   B '):
            with self.subTest(raw=repr(raw)):
                text=source(raw)
                self.assertEqual(parse(text).model.transitions[0][2],raw)
                event=await self._render(text,'A B')
                self.assertAlmostEqual(event.box.width,control.box.width,delta=.01)
                self.assertAlmostEqual(event.box.height,control.box.height,delta=.01)
                self.assertAlmostEqual(event.box.y,control.box.y,delta=.01)

    async def test_title_svg_text_ascii_tab_collapses_without_model_mutation(self):
        from py_mermaid import parse
        source='cynefin-beta\ntitle A\tB\nclear\n "Item"\n'
        self.assertEqual(parse(source).model.title,'A\tB')
        event=await self._render(source,'A B')
        control=await self._render('cynefin-beta\ntitle A B\nclear\n "Item"\n','A B')
        self.assertAlmostEqual(event.box.width,control.box.width,delta=.01)
        self.assertAlmostEqual(event.box.height,control.box.height,delta=.01)

    async def test_non_ascii_whitespace_is_not_collapsed_by_svg_ascii_rule(self):
        from py_mermaid import parse
        for raw in ('A\u00a0B','A\u2003B'):
            with self.subTest(raw=repr(raw)):
                source='cynefin-beta\nclear\n '+self._quoted(raw)+'\n'
                self.assertEqual(dict(parse(source).model.domains)['clear'][0],raw)
                event=await self._render(source,raw)
                self.assertEqual(event.text,raw)


    async def test_plain_svg_markup_entities_and_backslashes_remain_literal(self):
        # Original raw SVG/DOM controls captured in
        # CLOSURE-REPAIR-A-literal-svg-source-20261107T095021Z-652b940c.
        # Original .text() emits these as visible characters, not HTML or entities.
        from py_mermaid import parse
        control=await self._render('cynefin-beta\nclear\n "A B"\n','A B')
        for raw in ('A<br>B', 'A&nbsp;B', 'A\\nB'):
            with self.subTest(raw=raw):
                source='cynefin-beta\nclear\n '+self._quoted(raw)+'\n'
                self.assertEqual(dict(parse(source).model.domains)['clear'][0],raw)
                event=await self._render(source,raw)
                # DrawEvent.box measures glyph ink, not CSS line height.
                # Different glyphs (e.g. p descenders) legitimately change it.
                self.assertEqual(event.font_size,control.font_size)
                self.assertEqual(len(event.points),1,'One actual fillText baseline, not markup-generated rows')
                self.assertGreater(event.box.width,control.box.width)
