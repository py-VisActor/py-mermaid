"""P4 independent locked source contracts omitted by text-only corpus checks."""
import unittest
from ._support import semantic,assert_png,assert_text_pixels


class ZenSourceTokenBranches(unittest.TestCase):
    def test_source_lexer_loop_and_section_aliases(self):
        for word,kind in [('while','loop'),('for','loop'),('foreach','loop'),('forEach','loop'),('loop','loop'),('section','section'),('frame','section')]:
            with self.subTest(word=word):
                node=semantic('zenuml\n'+word+'(condition) { A.run() }').model.statements[0]
                self.assertEqual(node.kind,kind);self.assertEqual(node.children[0].label,'run()')
    def test_event_and_title_lexer_modes_preserve_arbitrary_unicode_line(self):
        m=semantic('zenuml\ntitle Unicode \U0001f680 <plain>\nA->B: \U0001f600 payload ! \u2014 <x> [other] = value').model
        self.assertEqual(m.title,'Unicode \U0001f680 <plain>')
        self.assertEqual(m.statements[0].label,'\U0001f600 payload ! \u2014 <x> [other] = value')
    def test_source_return_annotations_are_all_accepted(self):
        for alias in ('@Return','@return','@Reply','@reply'):
            with self.subTest(alias=alias):
                node=semantic('zenuml\nA->B.call() {\n'+alias+' B->A: result\n}').model.statements[0].children[0]
                self.assertEqual((node.kind,node.source,node.target,node.label),('return','B','A','result'))
    def test_creation_parameters_keep_source_expression_quotes(self):
        node=semantic('zenuml\nobj = new Service(name="John",note="x y")').model.statements[0]
        self.assertEqual(node.label,'\u00abname=John,note=x y\u00bb')
    def test_comment_source_unconsumed_tokens_keep_authored_punctuation(self):
        from py_mermaid.diagrams.zenuml.layout import _comment_markup
        self.assertEqual(_comment_markup('[**label**](https://example.invalid)'), '[**label**](https://example.invalid)')
        self.assertEqual(_comment_markup('# **heading**'), '# **heading**')
        self.assertEqual(_comment_markup('word_with_underscores'), 'word_with_underscores')
        self.assertEqual(_comment_markup(chr(96)+'code'+chr(96)+' **bold**'), 'code <strong>bold</strong>')

    def test_source_divider_discards_all_outer_equals(self):
        self.assertEqual(semantic('zenuml\n=====phase=====').model.statements[0].label,'phase')


class ZenSourceGeometryAndPixels(unittest.IsolatedAsyncioTestCase):
    async def test_original_spec_cumulative_alt_tcf_numbers(self):
        # Exact original svg/buildGeometry.spec.ts:66-96 literals, not a
        # recursive recomputation through the candidate numbering helper.
        from py_mermaid import arender
        source='zenuml\nif(cond) {\nA -> B: msg1\ntry {\nB -> C: tryMsg\n} catch(e) {\nC -> B: catchMsg\n} finally {\nB -> A: finallyMsg\n}\n} else if(cond2) {\nA -> B: elseIfMsg\n} else {\nA -> B: elseMsg\n}'
        result=await arender(source,backend='cpu');image=assert_png(self,result)
        expected={'msg1':'1.1','tryMsg':'1.2.1','catchMsg':'1.2.2','finallyMsg':'1.2.3','elseIfMsg':'1.3','elseMsg':'1.4'}
        actual={item['label']:item['number'] for item in result.layout.paint_ir if item['kind']=='async'}
        self.assertEqual(actual,expected)
        for label,number in expected.items():
            call=next(v for v in result.layout.paint_ir if v['label']==label)
            events=[e for e in result.trace if e.semantic_id==call['semantic_id']]
            self.assertEqual(''.join(e.text or '' for e in events if e.kind=='seq-number'),number)
            assert_text_pixels(self,image,next(e for e in events if e.text==label))
    async def test_self_number_is_left_of_label_and_has_actual_ink(self):
        from py_mermaid import arender
        result=await arender('zenuml\nA.outer() { A.selfCall() }',backend='cpu');image=assert_png(self,result)
        label=next(e for e in result.trace if e.text=='selfCall()')
        number=next(e for e in result.trace if e.kind=='seq-number' and e.semantic_id==label.semantic_id)
        self.assertEqual(number.text,'1.1')
        self.assertLessEqual(number.box.x+number.box.width,label.box.x-1)
        assert_text_pixels(self,image,label);assert_text_pixels(self,image,number)
    async def test_creation_uses_two_pixel_open_tip_and_dashed_line(self):
        from py_mermaid import arender
        result=await arender('zenuml\nA.run() { x = new Service() }',backend='cpu');image=assert_png(self,result)
        call=next(v for v in result.layout.paint_ir if v['kind']=='creation');events=[e for e in result.trace if e.semantic_id==call['semantic_id']]
        self.assertEqual([e.dash for e in events if e.kind=='creation-line'],[(6.,4.)])
        markers=[e for e in events if e.marker];self.assertTrue(markers)
        self.assertEqual({e.marker for e in markers},{'open'});self.assertTrue(all(e.stroke_width==2 for e in markers))
        ret=next(v for v in result.layout.paint_ir if v['kind']=='return');self.assertEqual(ret['number'],'1.1.1')
        event=next(e for e in result.trace if e.semantic_id==ret['semantic_id'] and e.text=='x');assert_text_pixels(self,image,event)
    async def test_ref_consumes_source_full_signature_and_bracket_opacity(self):
        from py_mermaid import arender
        result=await arender('zenuml\nA B\nref("External",A,B);',backend='cpu');image=assert_png(self,result)
        text=''.join(e.text or '' for e in result.trace if e.kind=='fragment-condition')
        self.assertEqual(text,'[ref("External",A,B);]')
        inner=next(e for e in result.trace if e.kind=='fragment-condition' and e.text and e.text.startswith('ref('))
        self.assertEqual(inner.opacity,.65);assert_text_pixels(self,image,inner)

    async def test_source_return_near_wall_offsets_are_seven_and_eight_pixels(self):
        import re
        from py_mermaid import arender
        result=await arender('zenuml\nA.run() { B.call() { return result } }',backend='cpu')
        centers={}
        for e in result.trace:
            if e.kind=='participant-box':
                values=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)',e.path)))
                centers[e.semantic_id]=(min(values[::2])+max(values[::2]))/2
        line=next(e for e in result.trace if e.kind=='return-line')
        values=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)',line.path)))
        self.assertAlmostEqual(values[0],centers['B']-7,delta=.001)
        self.assertAlmostEqual(values[2],centers['A']+8,delta=.001)
        self.assertEqual(line.dash,(6.,4.))

    async def test_source_svg_has_one_header_no_footer_and_keeps_long_label(self):
        from py_mermaid import arender
        name='AHasAVeryLongNameLongNameLongNameLongName'
        result=await arender('zenuml\n'+name+'\nB\n'+name+'->B.run()',backend='cpu');image=assert_png(self,result)
        boxes=[e for e in result.trace if e.kind=='participant-box'];self.assertEqual(len(boxes),2)
        target=next(e for e in boxes if e.semantic_id==name)
        self.assertAlmostEqual(dict(result.layout.participants)[name].width,250)
        label=next(e for e in result.trace if e.kind=='participant-label' and e.semantic_id==name)
        self.assertGreater(label.box.width,250);assert_text_pixels(self,image,label)
    async def test_par_separators_and_source_visible_kind_labels(self):
        from py_mermaid import arender
        result=await arender('zenuml\npar { A.one() B.two() C.three() }\ntry { A.ok() } catch(e) { B.fail() }',backend='cpu');image=assert_png(self,result)
        par=next(v for v in result.layout.paint_ir if v.get('fragment_kind')=='par')
        self.assertEqual(sum(e.kind=='fragment-separator' and e.semantic_id==par['semantic_id'] for e in result.trace),2)
        self.assertIn('Par',[e.text for e in result.trace]);self.assertIn('Try',[e.text for e in result.trace])
        for word in ('Par','Try'):assert_text_pixels(self,image,next(e for e in result.trace if e.text==word))


class ZenParityNegativeControls(unittest.IsolatedAsyncioTestCase):
    async def test_fixed_original_geometry_and_real_png_reject_mutations(self):
        import json,sys
        from pathlib import Path
        from io import BytesIO
        from dataclasses import asdict
        from PIL import Image
        from ._support import ROOT
        from py_mermaid import arender
        if str(ROOT/'tools') not in sys.path:sys.path.insert(0,str(ROOT/'tools'))
        from check_zenuml_parity import check,mutations
        reference=json.loads(Path(__file__).with_name('zen-parity-source-reference.json').read_text('utf-8'))
        case=reference['case'];result=await arender(case['source'],backend='cpu')
        scene={'trace':[asdict(e) for e in result.trace],'layout':asdict(result.layout)}
        image=Image.open(BytesIO(result.data)).convert('RGB')
        errors,_,_=check(case,reference['official'],reference['svg'],scene,image)
        self.assertEqual(errors,[])
        controls=mutations(case,reference['official'],reference['svg'],scene,image)
        for name in ('wrong-number','wrong-arrow','missing-line','extra-footer','disconnected-marker','missing-glyph-event','white-png','erased-glyph-png','erased-arrow-png','wrong-occurrence-wall'):
            self.assertIn(name,controls);self.assertIs(controls[name],True,name)
