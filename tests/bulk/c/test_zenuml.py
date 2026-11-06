"""Locked @zenuml/core grammar, dedicated positioning and resource semantics."""
import hashlib
import json
import math
import unittest
from pathlib import Path
from ._support import semantic,walk_statements,assert_png,assert_text_pixels,ROOT

SIGNATURE_CASES=[('A.m','m',''),('A.m()','m()',''),('A.m(1)','m(1)',''),('A.m(1,2)','m(1,2)',''),('ret = A.m','m','ret'),('new = A.m','m','new'),('const ret = A.m','m','ret'),('readonly ret = A.m','m','ret'),('static ret = A.m','m','ret'),('const ret = await A.m','m','ret'),('B.method(getCount(1))','method(getCount(1))','')]
ICON_TYPES=('actor','boundary','control','database','entity','ec2','lambda','iam','sns','sqs','azurefunction')


class ZenSemantics(unittest.TestCase):
    def test_explicit_participant_width_alias_stereotype_and_type(self):
        m=semantic('zenuml\n@actor <<Repo>> A 100 as "Long name"\nB\nA->B.method()').model
        a=next(a for a in m.participants if a.id=='A')
        self.assertEqual((a.type,a.stereotype,a.width,a.label,a.explicit),('actor','Repo',100,'Long name',True))
        self.assertEqual((m.statements[0].source,m.statements[0].target,m.statements[0].label),('A','B','method()'))

    def test_quoted_async_endpoints(self):
        m=semantic('zenuml\n"A B"->"C D":m').model;s=m.statements[0]
        self.assertEqual((s.kind,s.source,s.target,s.label),('async','A B','C D','m'))
        self.assertIn('A B',[p.id for p in m.participants]);self.assertIn('C D',[p.id for p in m.participants])

    def test_group_members_and_order(self):
        m=semantic('zenuml\nA\ngroup Services {B\nC}\nA->B.call()').model
        self.assertEqual([p.id for p in m.participants if not p.starter],['A','B','C'])
        self.assertEqual([(p.id,p.group) for p in m.participants if p.group],[('B','Services'),('C','Services')])

    def test_origin_and_starter_are_not_invented_message_nodes(self):
        m=semantic('zenuml\n@Starter(M)\nA->B.method() { return result }').model
        self.assertEqual(m.starter,'M');call=m.statements[0];ret=call.children[0]
        self.assertEqual((call.source,call.target,ret.source,ret.target,ret.label),('A','B','B','A','result'))

    def test_nested_sync_scope_and_self_call(self):
        m=semantic('zenuml\nA->B.outer() { B.inner() { C.deep() } }').model
        first=m.statements[0];second=first.children[0];third=second.children[0]
        self.assertEqual((first.source,first.target),('A','B'))
        self.assertEqual((second.source,second.target),('B','B'))
        self.assertEqual((third.source,third.target),('B','C'))

    def test_if_else_if_else_branch_order(self):
        m=semantic('zenuml\nif(condition) { return y1 } else if(condition1) { return y2 } else { return y3 }').model
        alt=m.statements[0];self.assertEqual(alt.kind,'alt');self.assertEqual(len(alt.sections),3)
        self.assertEqual([body[0].label for _,body in alt.sections],['y1','y2','y3'])
        self.assertEqual([label for label,_ in alt.sections],['[condition]','[condition1]','[else]'])

    def test_try_catch_finally_keeps_section_return_values(self):
        s=semantic('zenuml\ntry { A.run() } catch(e) { A.fail() } finally { A.close() }').model.statements[0]
        self.assertEqual(s.kind,'tcf');self.assertEqual([label for label,_ in s.sections],['try','catch e','finally'])
        self.assertEqual([body[0].label for _,body in s.sections],['run()','fail()','close()'])

    def test_control_conditions_preserve_text_and_nested_calls(self):
        for keyword,kind in [('while','loop'),('for','loop'),('foreach','loop'),('loop','loop'),('par','par'),('opt','opt'),('critical','critical'),('section','section')]:
            with self.subTest(keyword=keyword):
                s=semantic(f'zenuml\n{keyword}(condition) {{ B.method() }}').model.statements[0]
                self.assertEqual(s.kind,kind);self.assertEqual(s.label,'condition');self.assertEqual(s.children[0].label,'method()')

    def test_creation_assignment_and_constructor_participant(self):
        s=semantic('zenuml\nA->B.run() { obj = new Service() { C.init() } }').model.statements[0].children[0]
        self.assertEqual(s.kind,'creation');self.assertEqual(s.assignment,'obj')
        self.assertEqual((s.source,s.target),('B','obj:Service'));self.assertEqual(s.children[0].source,'obj:Service')

    def test_ref_and_divider_static_shapes(self):
        m=semantic('zenuml\nA B\nref("External",A,B)\n== Phase Two ==\nA->B: message').model
        self.assertEqual([s.kind for s in m.statements],['ref','divider','async'])
        self.assertEqual(m.statements[0].participants,('A','B'));self.assertEqual(m.statements[0].label,'External')
        self.assertEqual(m.statements[1].label,'Phase Two')

    def test_comment_belongs_to_following_message(self):
        s=semantic('zenuml\nA B\n// <red> Important comment\nA->B.call()').model.statements[0]
        self.assertIn('Important comment',s.comment);self.assertEqual(s.label,'call()')

    def test_dedicated_parser_rejects_unclosed_delimiters_with_raw_location(self):
        from py_mermaid import MermaidError
        for body in ('A.call(1','A.call() { B.run()','if(x) { A.m()','A -> : broken'):
            with self.subTest(body=body):
                with self.assertRaises(MermaidError) as caught:
                    semantic('zenuml\n'+body)
                self.assertEqual(caught.exception.code,'SYNTAX_ERROR');self.assertIsNotNone(caught.exception.span)
                self.assertGreaterEqual(caught.exception.span.start.line,2)

    def test_all_builtin_types_are_semantic_participant_annotations(self):
        for kind in ICON_TYPES:
            with self.subTest(kind=kind):
                p=next(p for p in semantic(f'zenuml\n@{kind} Service\nService.run()').model.participants if p.id=='Service')
                self.assertEqual(p.type,kind);self.assertTrue(p.explicit)


def _signature_method(row):
    source,signature,assignment=row
    def method(self):
        node=semantic('zenuml\n'+source).model.statements[0]
        self.assertEqual(node.kind,'sync');self.assertEqual(node.target,source.split('=')[-1].strip().split('.')[0].split()[-1])
        self.assertEqual(node.label,signature);self.assertEqual(node.assignment,assignment)
    return method


for _i,_row in enumerate(SIGNATURE_CASES):setattr(ZenSemantics,f'test_source_signature_{_i:02d}',_signature_method(_row))


def _source_visual_semantics(row):
    def method(self):
        from dataclasses import is_dataclass
        diagram=semantic(row['source']);self.assertEqual(diagram.kind,'zenuml');m=diagram.model
        self.assertTrue(is_dataclass(m));self.assertTrue(m.__dataclass_params__.frozen)
        self.assertEqual(len({p.id for p in m.participants}),len(m.participants))
        statements=list(walk_statements(m.statements));labels=' '.join(s.label for s in statements)
        for text in row['expectedText']:self.assertIn(text,labels)
        for statement in statements:
            self.assertGreaterEqual(statement.offset,0);self.assertLessEqual(statement.offset,len(row['source']))
        if row['source'].split('\n',1)[1].strip():self.assertTrue(m.participants or m.statements or m.title)
    method.__doc__=row['origin']['path']+':'+str(row['origin']['line'])+' '+row['origin']['symbol']
    return method


class ZenOfficialVisualCorpusSemantics(unittest.TestCase):pass
for _row in json.loads(Path(__file__).with_name('zen-visual-source-cases.json').read_text('utf-8')):
    setattr(ZenOfficialVisualCorpusSemantics,'test_'+_row['id'].replace('-','_'),_source_visual_semantics(_row))


class ZenPurePositioning(unittest.TestCase):
    def test_source_recovery_content_loss_is_explicit_and_native_content_not_reduced(self):
        cases=json.loads(Path(__file__).with_name('zen-visual-source-cases.json').read_text('utf-8'))
        cases={row['id']:row for row in cases}
        expectations={
            'C-zenuml-source-emoji-colon-override':(['notify()'],[]),
            'C-zenuml-source-emoji-in-conditions':(['wait()','deny()'],['proceed()','limited']),
        }
        for id,(missing,present) in expectations.items():
            with self.subTest(id=id):
                row=cases[id]
                self.assertEqual(row['expect'],'upstream_defect');self.assertEqual(row['officialExpect'],'content_loss')
                self.assertTrue(row['nativeMustRender']);self.assertEqual(row['expectedErrorCodes'],[])
                self.assertEqual(row['sourceContent'],{'missingText':missing,'presentText':present})
                labels=[s.label for s in walk_statements(semantic(row['source']).model.statements)]
                for label in row['expectedText']:self.assertIn(label,labels)
                for label in missing:self.assertIn(label,row['expectedText']);self.assertIn(label,labels)

    def test_comment_css_first_and_common_only_emoji_source_priority(self):
        from py_mermaid.diagrams.zenuml.layout import _style_comment
        text, (comment, _), (message, _) = _style_comment('[red] Important')
        self.assertEqual(text, 'Important')
        self.assertEqual(comment['text_color'], 'red');self.assertEqual(message['text_color'], 'red')
        text, (comment, _), (message, _) = _style_comment('[rocket] <blue> (red) Important')
        self.assertEqual(text, '🚀 Important')
        self.assertEqual(comment['text_color'], 'blue');self.assertEqual(message['text_color'], 'red')
        self.assertEqual(_style_comment('<rocket> Important')[0], 'Important')

    def test_all_source_builtin_shortcodes_and_css_first_collision(self):
        from py_mermaid.diagrams.zenuml.emoji import resolve
        rows=json.loads(Path(__file__).with_name('zen-emoji-source.json').read_text('utf-8'))
        self.assertEqual(len(rows),93)
        for row in rows:
            with self.subTest(name=row['name'],sourceLine=row['sourceLine']):
                self.assertEqual(resolve('[:'+row['name']+':]'),row['unicode'])
                self.assertEqual(resolve('['+row['name']+']'),'[red]' if row['name']=='red' else row['unicode'])
        self.assertEqual(resolve('[unknown_xyz] message'),'[unknown_xyz] message')
        self.assertEqual(resolve('plain message'),'plain message')

    def test_two_participant_constraint_has_exact_minimal_span(self):
        from py_mermaid.diagrams.zenuml.geometry import optimal_positions
        self.assertEqual(optimal_positions([[0,100],[0,0]]),[0,100])

    def test_chain_and_spanning_constraints_minimum_total_width(self):
        from py_mermaid.diagrams.zenuml.geometry import optimal_positions
        matrices=[([[0,100,0],[0,0,200],[0,0,0]],300),([[0,100,100,800],[0,0,100,0],[0,0,0,100],[0,0,0,0]],800),([[0,100,0,100],[0,0,300,800],[0,0,0,0],[0,0,0,0]],900)]
        for matrix,minimum in matrices:
            with self.subTest(matrix=matrix):
                positions=optimal_positions(matrix);self.assertAlmostEqual(positions[0],0);self.assertAlmostEqual(positions[-1],minimum)
                for i,row in enumerate(matrix):
                    for j,d in enumerate(row):
                        if d>0:self.assertGreaterEqual(positions[j]-positions[i]+1e-6,d)


class ZenNative(unittest.IsolatedAsyncioTestCase):
    async def test_nested_calls_returns_fragments_actual_content_and_geometry(self):
        from py_mermaid import arender
        source='zenuml\nA as Client\nB as Server\nA->B.request() { if(ok) { C.work() } else { B.retry() } return result }'
        result=await arender(source,backend='cpu');image=assert_png(self,result)
        text=' '.join(e.text for e in result.trace if e.text)
        for word in ('Client','Server','request()','work()','retry()','result'):self.assertIn(word,text)
        for label in ('request()','result'):
            event=next(e for e in result.trace if e.text and label in e.text);assert_text_pixels(self,image,event)
        self.assertGreaterEqual(sum(e.kind=='message-line' for e in result.trace),3)
        self.assertTrue(any(e.kind=='return-line' for e in result.trace))
        self.assertGreater(len(result.layout.occurrences),0)

    async def test_explicit_participant_emoji_is_unicode_not_shortcode_ink(self):
        from py_mermaid import arender
        result=await arender('zenuml\n[:red:] Alert\n[rocket] Normal\nAlert->Normal.notify()',backend='cpu')
        image=assert_png(self,result)
        red=next(e for e in result.trace if e.text=='\U0001f534')
        self.assertFalse(any(e.text and ':red:' in e.text for e in result.trace))
        crop=image.crop((int(red.box.x),int(red.box.y),int(red.box.x+red.box.width+1),int(red.box.y+red.box.height+1))).convert('RGB')
        self.assertGreater(sum(r>120 and r>g*1.4 and r>b*1.4 for r,g,b in crop.getdata()),10)

    async def test_source_tcf_builtin_is_offline_and_visible(self):
        from py_mermaid import arender
        result=await arender('zenuml\ntry { A.run() } catch(e) { A.fail() } finally { A.close() }',backend='cpu')
        image=assert_png(self,result)
        self.assertTrue(any(e.kind=='asset' for e in result.trace))
        for label in ('run()', 'fail()', 'close()'):
            event=next(e for e in result.trace if e.text and label in e.text)
            assert_text_pixels(self,image,event)

    async def test_vendor_icons_keep_original_bytes_colors_and_square_ratio(self):
        from py_mermaid import arender
        rows=json.loads(Path(__file__).with_name('zen-assets.json').read_text('utf-8'))
        for row in rows:
            raw=(ROOT/row['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sourceSha256'])
        source='zenuml\n'+'\n'.join('@'+name+' '+name for name in ('ec2','lambda','iam','sns','sqs','azurefunction'))+'\nec2->lambda.call()'
        result=await arender(source,backend='cpu');image=assert_png(self,result)
        assets=[e for e in result.trace if e.kind=='asset'];self.assertEqual(len(assets),6)  # Actual renderToSvg never consumes the bottom helper.
        self.assertTrue(all(abs(e.box.width-e.box.height)<1e-6 for e in assets))
        self.assertGreater(sum(max(p)-min(p)>60 for p in image.getdata()),30)
