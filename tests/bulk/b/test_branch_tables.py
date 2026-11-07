"""Production/DB parameter tables, meaningful negative controls and source CSS.

Tables are literal deductions from fixed upstream, not candidate-generated cases.
"""
import unittest
from py_mermaid import parse
from py_mermaid.model.flowchart import MermaidError
from .support import SourceCase,model,scene,command,shape_box


class SourceParameterTables(SourceCase):
    def test_bt01_gantt_weekday_and_weekend_terminals(self):
        for day in ('monday','tuesday','wednesday','thursday','friday','saturday','sunday'):
            with self.subTest(day=day):self.assertEqual(model('gantt\nweekday '+day+'\nA:2024-01-01, 1d\n').weekday,day)
        for day in ('friday','saturday'):
            with self.subTest(weekend=day):self.assertEqual(model('gantt\nweekend '+day+'\nA:2024-01-01, 1d\n').weekend,day)
        self.reject('gantt\nweekend sunday\nA:2024-01-01, 1d\n')

    def test_bt02_gantt_tag_combinations_remain_independent(self):
        for tags in ('done','active','crit','done,crit','active,crit','milestone','vert'):
            with self.subTest(tags=tags):
                t=model('gantt\nA:'+tags+', a, 2024-01-01, 1d\n').tasks[0]
                self.assertEqual(set(t.tags),set(tags.split(',')))

    def test_bt03_git_all_merge_preconditions(self):
        rows=[('gitGraph\nbranch dev\nmerge main\n','INVALID_GIT_MERGE'),('gitGraph\ncommit id:"A"\nmerge absent\n','INVALID_GIT_MERGE'),('gitGraph\ncommit id:"A"\nbranch dev\ncheckout main\nmerge dev\n','INVALID_GIT_MERGE'),('gitGraph\ncommit id:"A"\nbranch dev\ncommit id:"B"\ncheckout main\ncommit id:"C"\nmerge dev id:"A"\n','DUPLICATE_GIT_COMMIT')]
        for source,code in rows:
            with self.subTest(source=source):self.reject(source,code)

    def test_bt04_git_cherry_pick_merge_requires_immediate_parent(self):
        base='gitGraph\ncommit id:"A"\nbranch dev\ncommit id:"B"\ncheckout main\ncommit id:"C"\nmerge dev id:"M"\nbranch other\ncommit id:"D"\n'
        for suffix in ('cherry-pick id:"M"','cherry-pick id:"M" parent:"A"'):
            with self.subTest(suffix=suffix):self.reject(base+suffix+'\n','INVALID_CHERRY_PICK')
        m=model(base+'cherry-pick id:"M" parent:"C"\n')
        self.assertEqual(m.commits[-1].parents,('D','M'))
        self.assertEqual(m.commits[-1].tags,('cherry-pick:M|parent:C',))

    def test_bt05_event_model_source_type_table(self):
        valid={'ui':'rmo','processor':'readmodel','rmo':'event','command':'ui','event':'cmd'}
        for target,source in valid.items():
            with self.subTest(target=target,source=source):
                m=model('eventmodeling\ntf 1 '+source+' From\ntf 2 '+target+' To ->> 1\n')
                self.assertEqual(m.frames[1].sources,('1',))
        for source in ('eventmodeling\ntf 1 ui Page ->> 999\n','eventmodeling\ntf 1 ui Page [[missing]]\n'):
            with self.subTest(source=source):self.reject(source)

    def test_bt06_event_notes_and_gwt_are_preserved_not_silently_dropped(self):
        m=model('eventmodeling\nentity Order\ntf 1 ui Page\nnote 1 {\nNote text\n}\ngwt 1 given ui Order when cmd Order then evt Order\n')
        self.assertEqual(m.entities,('Order',))
        self.assertEqual(m.notes[0][0],'1')
        self.assertEqual(m.assertions[0][0],'1')
        self.assertEqual([phase for phase,_ in m.assertions[0][1]],['given','when','then'])

    def test_bt07_wardley_decorator_table(self):
        for kind in ('build','buy','outsource','market'):
            with self.subTest(strategy=kind):self.assertEqual(model('wardley-beta\ncomponent A [0.5, 0.5] ('+kind+')\n').nodes[0].strategy,kind)

    def test_bt08_wardley_annotations_and_first_box_wins(self):
        m=model('wardley-beta\nannotations [20, 30]\nannotations [40, 50]\nannotation 1, [25, 75] "Risk"\n')
        self.assertEqual(m.annotations_box,(30,20))
        self.assertEqual(m.annotations,((1,75,25,'Risk'),))

    def test_bt09_wardley_duplicate_preserves_unspecified_offset(self):
        m=model('wardley-beta\ncomponent A [0.2, 0.3] label [4, -8]\ncomponent A [0.4, 0.5]\n')
        self.assertEqual(len(m.nodes),1)
        self.assertEqual((m.nodes[0].x,m.nodes[0].y,m.nodes[0].offset_x,m.nodes[0].offset_y),(50,40,4,-8))

    def test_bt10_wardley_link_label_includes_source_semicolon(self):
        m=model('wardley-beta\ncomponent A [0.2, 0.3]\ncomponent B [0.4, 0.5]\nA -> B ;dependency\n')
        self.assertEqual(m.links[0][3],';dependency')

    def test_bt11_agent_removed_shape_table_has_visible_recovery_and_diagnostic(self):
        removed=('doc','stadium','terminal','circle','trapezoid','inv-trapezoid','double-circle','procs','lean-left','in-out','cylinder','ellipse','odd','tag-rect','delay','lin-rect','win-pane','curv-trap')
        for shape in removed:
            with self.subTest(shape=shape):
                d=parse('agentflow-beta TB\nA[Visible]\nA@{ shape: "'+shape+'" }\n')
                self.assertEqual(d.model.graph.nodes[0].label,'Visible')
                self.assertTrue(any('SHAPE_REMOVED' in str(v) for v in d.diagnostics))

    def test_bt12_agent_aliases_and_default_kind(self):
        m=model('agentflow-beta TB\nA[Default]\nB@{ shape: round }\nC@{ shape: hex }\nD@{ shape: subprocess }\n')
        self.assertEqual(dict(m.kinds)['A'],'task')
        self.assertEqual(m.graph.nodes[0].shape,m.graph.nodes[1].shape)
        # Source ALLOWED_SHAPES keeps these aliases; paint canonicalisation is
        # a later shared shape-provider concern, not a DB rewrite.
        self.assertEqual(next(n for n in m.graph.nodes if n.id=='C').shape,'hex')
        self.assertEqual(next(n for n in m.graph.nodes if n.id=='D').shape,'subprocess')

    def test_bt13_agent_unknown_registered_shape_warning_vs_invalid_name(self):
        d=parse('agentflow-beta TB\nx[Visible]\nx@{ shape: cloud }\n')
        self.assertTrue(any('SHAPE_UNSUPPORTED' in str(v) for v in d.diagnostics))
        self.assertEqual(d.model.graph.nodes[0].label,'Visible')
        with self.assertRaises(MermaidError) as c:parse('agentflow-beta TB\nx@{ shape: not_a_shape }\n')
        self.assertEqual(c.exception.code,'UNSUPPORTED_SHAPE')

    def test_bt14_accessibility_is_preserved_as_pure_metadata(self):
        for header,body in [('gantt','A:2024-01-01, 1d'),('journey','A:5'),('timeline','A : Event'),('gitGraph','commit id:"A"'),('cynefin-beta','clear\n "Item"'),('wardley-beta','component A [0.5, 0.5]'),('eventmodeling','tf 1 ui Page')]:
            with self.subTest(header=header):
                source=header+'\naccTitle: Accessible\naccDescr {Description\ncontinued}\n'+body+'\n'
                if header=='eventmodeling':
                    # Fixed Langium EM_ID precedes EM_ACC_* terminals. This
                    # exact bare line is rejected (not metadata) by original
                    #12.2.0; raw exception preserved in source Run
                    #CLOSURE-P3-B-EXPECTATION-source-20261107T083759Z-f31238d5.
                    with self.assertRaises(MermaidError) as caught:model(source)
                    self.assertEqual(caught.exception.code,'SYNTAX_ERROR')
                    continue
                m=model(source)
                values=dict(m.accessibility)
                self.assertEqual(values['acctitle'],'Accessible')
                self.assertIn('continued',values['accdescr'])


class StyleAndGeometryBranches(unittest.IsolatedAsyncioTestCase):
    async def test_bs01_timeline_event_brightness_is_real_style(self):
        s=await scene('timeline\nA : Event\n')
        e=command(s,'event-0-0-0')
        style=dict(e.style).get('resolved')
        self.assertIsNotNone(style)
        self.assertAlmostEqual(style.brightness,1.2)

    async def test_bs02_user_css_wins_source_defaults(self):
        s=await scene('journey\nA:5:Alice\n',{'themeCSS':'.task {stroke:#123456 !important; fill:#abcdef !important;} .task text {fill:#987654 !important;}'})
        style=dict(command(s,'task-0').style)['resolved']
        self.assertEqual(style.stroke,'#123456')
        self.assertEqual(style.fill,'#abcdef')

    async def test_bs03_swimlane_group_overlay_text_is_centered_after_rotation(self):
        s=await scene('swimlane-beta LR\nsubgraph L[Long lane title]\nA[Work] --> B[Done]\nend\n')
        paints=dict(s.group_overrides)['L']
        label=next(c for c in paints if c.kind=='text')
        box,x,y,angle,_=label.values
        self.assertEqual(angle,-90)
        lane=next(g.box for g in s.layout.groups if g.id=='L')
        self.assertAlmostEqual(y-box.width/2,lane.y+lane.height/2,delta=1)
        self.assertGreaterEqual(x,lane.x-1)
        self.assertLessEqual(x+box.height,lane.x+lane.width+1)

    async def test_bs04_gantt_milestone_source_rotated_scale(self):
        s=await scene('gantt\ndateFormat YYYY-MM-DD\ntodayMarker off\nM:milestone, m, 2024-01-02, 0d\nA:a, 2024-01-01, 2d\n',{'gantt':{'barHeight':20,'useWidth':600}})
        c=command(s,'m');b=shape_box(c)
        self.assertAlmostEqual(b.width,16*2**.5,delta=.01)
        self.assertAlmostEqual(b.height,16*2**.5,delta=.01)

    async def test_bs05_event_namespace_source_inherited_repeated_lane(self):
        s=await scene('eventmodeling\ntf 1 ui shop.Page\ntf 2 ui shop.Other\n')
        # Source lane.namespace is never assigned, so the same namespace gets
        # another lane. Do not silently correct this to a reused single lane.
        labels=[c for c in s.commands if c.kind=='text' and 'shop' in c.values[0].text]
        self.assertEqual(len(labels),2)
        self.assertNotEqual(labels[0].values[2],labels[1].values[2])
