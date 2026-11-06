"""Sequence Jison/DB action tables and native static renderer assertions."""
import unittest
from ._support import semantic,assert_png,assert_text_pixels

# Literal lexer spellings: sequenceDiagram.jison:85-118, not product ARROWS.
ARROW_CASES=('->>','-->>','<<->>','<<-->>','->','-->','-x','--x','-)','--)',
             '-|\\','-|/','-\\\\','-//','/|-','\\|-','//-','\\\\-',
             '--|\\','--|/','--\\\\','--//','/|--','\\|--','//--','\\\\--')
ACTOR_KINDS=('participant','actor','boundary','control','entity','database','collections','queue')


class SequenceSemantics(unittest.TestCase):
    def test_actor_menu_keyword_parameter_tables_and_prototype_names(self):
        for name in ('Link','link','LINK','Links','Properties','Details','__proto__','constructor'):
            for explicit in (True,False):
                with self.subTest(name=name,explicit=explicit):
                    src='sequenceDiagram\n'+(f'participant {name} as Alias\n' if explicit else '')+f'A -->> {name} : message\n{name}->>A: reply'
                    m=semantic(src).model
                    self.assertEqual([(e.source,e.target) for e in m.events],[('A',name),(name,'A')])
                    self.assertEqual(next(a for a in m.actors if a.id==name).label,'Alias' if explicit else name)

    def test_autonumber_thousandths_source_negative_boundary(self):
        from py_mermaid import MermaidError
        for declaration in ('autonumber 1.001','autonumber 1 0.001'):
            with self.subTest(declaration=declaration):
                with self.assertRaises(MermaidError) as caught:
                    semantic('sequenceDiagram\n'+declaration+'\nA->>B: msg')
                self.assertEqual(caught.exception.code,'SYNTAX_ERROR')

    def test_implicit_actor_order_then_alias_redeclaration(self):
        m=semantic('sequenceDiagram\nB->>A: first\nparticipant B as Browser\nA-->>C: second').model
        self.assertEqual([a.id for a in m.actors],['B','A','C'])
        self.assertEqual([a.label for a in m.actors],['Browser','A','C'])
        self.assertEqual([(e.source,e.target,e.text) for e in m.events],[('B','A','first'),('A','C','second')])

    def test_nested_activation_stack_and_shorthand_order(self):
        m=semantic('sequenceDiagram\nA->>+B: first\nactivate B\nB-->>-A: second\ndeactivate B').model
        self.assertEqual([e.kind for e in m.events],['message','activate','activate','message','deactivate','deactivate'])
        self.assertEqual([e.source for e in m.events if e.kind in ('activate','deactivate')],['B','B','B','B'])

    def test_note_placements_and_two_actor_over(self):
        m=semantic('sequenceDiagram\nnote left of A: Left\nnote right of B: Right\nnote over A,B: Both\nnote over B: Single').model
        self.assertEqual([(e.placement,e.source,e.target,e.text) for e in m.events],[('left of','A','A','Left'),('right of','B','B','Right'),('over','A','B','Both'),('over','B','B','Single')])
        self.assertEqual([a.id for a in m.actors],['A','B'])

    def test_autonumber_start_step_off_keeps_internal_counter(self):
        m=semantic('sequenceDiagram\nautonumber 2.5 0.25\nA->>B: one\nautonumber off\nA->>B: two\nautonumber\nA->>B: three').model
        self.assertEqual([e.number for e in m.events],[2.5,None,3.0])

    def test_zero_start_and_zero_step_follow_source_or_default(self):
        m=semantic('sequenceDiagram\nautonumber 0 0\nA->>B: one\nA->>B: two').model
        self.assertEqual([e.number for e in m.events],[1,2])

    def test_show_sequence_numbers_config_can_force_visibility(self):
        m=semantic('sequenceDiagram\nautonumber off\nA->>B: one',{'sequence':{'showSequenceNumbers':True}}).model
        self.assertEqual(m.events[0].number,1)

    def test_wrap_overrides_default_and_message_semicolon(self):
        m=semantic('sequenceDiagram;participant A as wrap:Actor A;A->>B: nowrap:First;B-->>A: wrap:Second',{'sequence':{'wrap':True}}).model
        self.assertTrue(m.actors[0].wrap);self.assertEqual(m.actors[0].label,'Actor A')
        self.assertEqual([(e.text,e.wrap) for e in m.events],[('First',False),('Second',True)])

    def test_actor_boxes_members_color_and_declaration_order(self):
        m=semantic('sequenceDiagram\nbox rgb(240,240,255) Services\nparticipant A\nactor B as Client\nend\nparticipant C\nA->>C: call').model
        self.assertEqual(len(m.boxes),1);self.assertEqual(m.boxes[0].actors,('A','B'))
        self.assertEqual(m.boxes[0].title,'Services');self.assertEqual(m.boxes[0].color,'rgb(240,240,255)')
        self.assertEqual([a.box for a in m.actors],[0,0,None])

    def test_create_destroy_attach_to_matching_messages(self):
        m=semantic('sequenceDiagram\nparticipant A\ncreate participant B\nA->>B: create\ndestroy B\nB-->>A: final').model
        self.assertEqual([(a.id,a.created,a.destroyed) for a in m.actors],[('A',None,None),('B',0,1)])
        self.assertEqual([e.text for e in m.events],['create','final'])

    def test_fragment_actions_and_section_order(self):
        src='sequenceDiagram\nalt primary\nloop retry\nA->>B: work\nend\nelse backup\nB-->>A: fallback\nend\npar first\nA->>B: one\nand second\nB->>A: two\nend\ncritical transaction\nA->>B: commit\noption unavailable\nB->>A: abort\nend'
        kinds=[e.kind for e in semantic(src).model.events]
        self.assertEqual(kinds,['alt_start','loop_start','message','loop_end','else','message','alt_end','par_start','message','and','message','par_end','critical_start','message','option','message','critical_end'])

    def test_every_simple_fragment_emits_balanced_actions(self):
        for block in ('loop','opt','break','par_over','rect'):
            with self.subTest(block=block):
                label='rgb(240,240,240)' if block=='rect' else 'Condition'
                events=semantic(f'sequenceDiagram\n{block} {label}\nA->>B: inside\nend').model.events
                self.assertEqual([e.kind for e in events],[block+'_start','message',block+'_end'])
                self.assertEqual(events[0].text,label)

    def test_central_connections_cover_source_target_and_dual(self):
        for spelling,expected in [('A->>()B: target','target'),('A()->>B: source','source'),('A()->>()B: dual','dual')]:
            with self.subTest(spelling=spelling):
                event=semantic('sequenceDiagram\n'+spelling).model.events[0]
                self.assertEqual(event.connection,expected);self.assertEqual((event.source,event.target),('A','B'))

    def test_exact_lifecycle_and_fragment_errors_have_raw_spans(self):
        from py_mermaid import MermaidError
        negatives=[('deactivate A','INACTIVE_PARTICIPANT'),('end','SYNTAX_ERROR'),('else orphan','SYNTAX_ERROR'),('and orphan','SYNTAX_ERROR'),('option orphan','SYNTAX_ERROR'),('loop missing\nA->>B: msg','SYNTAX_ERROR'),('create participant B\nA->>C: wrong','INVALID_CREATE_MESSAGE'),('destroy B\nA->>C: wrong','INVALID_DESTROY_MESSAGE'),('create participant A\nA->>A: ok\ncreate participant A','DUPLICATE_PARTICIPANT')]
        for body,code in negatives:
            with self.subTest(body=body):
                with self.assertRaises(MermaidError) as caught:
                    semantic('sequenceDiagram\n'+body)
                self.assertEqual(caught.exception.code,code);self.assertIsNotNone(caught.exception.span)
                self.assertGreaterEqual(caught.exception.span.start.line,2)

    def test_properties_remain_static_metadata_and_accessibility_not_messages(self):
        m=semantic('sequenceDiagram\nparticipant A\nproperties A: {"class":"customActor"}\nlinks A: {"Docs":"https://example.invalid"}\naccTitle: A title\nA->>B: visible').model
        self.assertEqual([e.text for e in m.events],['visible'])
        self.assertIn('properties',dict(m.actors[0].metadata));self.assertEqual(len(m.actors),2)


def _arrow_method(spelling):
    def method(self):
        m=semantic('sequenceDiagram\nAlice'+spelling+'Bob: Unique message').model
        self.assertEqual([a.id for a in m.actors],['Alice','Bob'])
        self.assertEqual(len(m.events),1);e=m.events[0]
        self.assertEqual((e.kind,e.source,e.target,e.arrow,e.text),('message','Alice','Bob',spelling,'Unique message'))
    return method


def _actor_method(kind):
    def method(self):
        a=semantic('sequenceDiagram\nparticipant A@{ "type":"'+kind+'", "alias":"Alias" }\nA->>B: message').model.actors[0]
        self.assertEqual((a.id,a.kind,a.label),('A',kind,'Alias'))
    return method


for _i,_arrow in enumerate(ARROW_CASES):setattr(SequenceSemantics,f'test_source_arrow_{_i:02d}',_arrow_method(_arrow))
for _kind in ACTOR_KINDS:setattr(SequenceSemantics,'test_source_actor_'+_kind,_actor_method(_kind))


class SequenceNative(unittest.IsolatedAsyncioTestCase):
    async def test_classic_and_neo_actor_database_label_baseline_and_glyph_bands(self):
        from py_mermaid import arender
        source='sequenceDiagram\nparticipant A@{"type":"actor","alias":"Label"}\nparticipant B@{"type":"database","alias":"Label"}\nA->>B: Call'
        for look in ('classic','neo'):
            with self.subTest(look=look):
                result=await arender(source,backend='cpu',config={'look':look,'sequence':{'mirrorActors':False}})
                image=assert_png(self,result);labels=[e for e in result.trace if e.kind=='actor-label' and e.text=='Label']
                self.assertEqual(len(labels),2);self.assertAlmostEqual(labels[0].points[0].y,labels[1].points[0].y,delta=.01)
                for event in labels:assert_text_pixels(self,image,event)
                if look=='neo':
                    glyph=[e for e in result.trace if e.semantic_id=='A' and e.kind=='actor' and e.box]
                    self.assertTrue(glyph)
                    self.assertGreaterEqual(max(e.box.y+e.box.height for e in glyph)-min(e.box.y for e in glyph),44)

    async def test_messages_activations_notes_and_fragment_have_ink_and_order(self):
        from py_mermaid import arender
        src='sequenceDiagram\nparticipant A as Browser\nparticipant B as Server\nA->>+B: Request\nnote over A,B: Shared note\nalt Success\nB-->>-A: Response\nelse Failure\nB--xA: Rejected\nend'
        result=await arender(src,backend='cpu');image=assert_png(self,result)
        events=[e for e in result.trace if e.text]
        for word in ('Browser','Server','Request','Shared note','Response','Rejected'):
            matches=[e for e in events if e.text==word];self.assertTrue(matches,word)
            assert_text_pixels(self,image,matches[0])
        request=next(e for e in events if e.text=='Request');response=next(e for e in events if e.text=='Response')
        self.assertLess(request.box.y,response.box.y)
        self.assertTrue(any(e.kind.startswith('activation') for e in result.trace))

    async def test_parent_text_class_css_applies_real_red_italic_pixels(self):
        from py_mermaid import arender
        result=await arender('sequenceDiagram\nA->>B: Styled',config={'themeCSS':'.messageText { fill:#d02030; font-size:24px; font-style:italic; }'},backend='cpu')
        image=assert_png(self,result);event=next(e for e in result.trace if e.text=='Styled')
        self.assertEqual(event.font_size,24);self.assertEqual(event.font_style,'italic')
        b=event.box;pixels=list(image.crop((int(b.x),int(b.y),int(b.x+b.width+1),int(b.y+b.height+1))).getdata())
        self.assertGreater(sum(r>g*1.6 and r>b*1.5 for r,g,b in pixels),5)
