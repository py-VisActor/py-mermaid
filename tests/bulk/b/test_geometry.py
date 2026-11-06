"""Real native measurements and dedicated layout relationships (P3 execution).

Geometry literals come from fixed renderer algorithms; no image/coordinate
goldens are recorded from the Python candidate. C tests router phase internals.
"""
import math
import unittest
from .support import scene,command,texts,shape_box


class TemporalGeometry(unittest.IsolatedAsyncioTestCase):
    async def test_v23_journey_nonfinite_score_keeps_real_content(self):
        s=await scene('journey\nTask:not-number:Alice\nValid:5:Bob\n')
        visible=' '.join(texts(s))
        for label in ('Task','Valid','Alice','Bob'):self.assertIn(label,visible)
        self.assertTrue(command(s,'task-0').values[0])
        self.assertTrue(command(s,'activity').values[0])
        # Actual source SVG invalid cy defaults to 0. P3's earlier assumption
        # that this face vanished was disproved by the original A PNG.
        self.assertTrue(any(c.semantic_id=='face-0' for c in s.commands))
        badface=shape_box(command(s,'face-0'))
        self.assertAlmostEqual(badface.y+badface.height/2,0)
        self.assertTrue(any(c.semantic_id=='face-1' for c in s.commands))
        self.assertTrue(any('non-finite' in str(d) for d in s.diagnostics))
        for c in s.commands:
            if c.bounds:self.assertTrue(all(math.isfinite(v) for v in (c.bounds.x,c.bounds.y,c.bounds.width,c.bounds.height)))

    async def test_v01_journey_score_face_positions_and_radius(self):
        s=await scene('journey\nsection Work\nGood:5:Alice\nNeutral:3:Bob\nBad:1:Alice\n')
        for i,cy in enumerate((300,360,420)):
            with self.subTest(score=i):
                b=shape_box(command(s,'face-'+str(i)))
                self.assertAlmostEqual(b.y+b.height/2,cy)
                self.assertAlmostEqual(b.width,30)
        positions=s.layout['tasks']
        self.assertEqual(positions[1][1]-positions[0][1],200)
        self.assertEqual(positions[2][1]-positions[1][1],200)

    async def test_v02_journey_custom_width_gap(self):
        s=await scene('journey\nA:5\nB:3\n',{'journey':{'width':120,'taskMargin':30}})
        self.assertEqual(s.layout['tasks'][1][1]-s.layout['tasks'][0][1],150)

    async def test_v03_timeline_LR_200px_columns(self):
        s=await scene('timeline LR\nsection S\nA : One\nB : Two\n')
        boxes={r[0]:r[1:] for r in s.layout['boxes']}
        self.assertEqual(boxes['period-0-1'][0]-boxes['period-0-0'][0],200)
        self.assertEqual(boxes['period-0-0'][2],190)
        self.assertEqual(boxes['period-0-0'][0],boxes['event-0-0-0'][0])

    async def test_v04_timeline_TD_event_and_period_columns(self):
        s=await scene('timeline TD\nsection S\nA : One : Two\nB : Three\n')
        boxes={r[0]:r[1:] for r in s.layout['boxes']}
        p=boxes['period-0-0'];e=boxes['event-0-0-0'];e2=boxes['event-0-0-1']
        self.assertEqual(p[2],210)
        self.assertEqual(e[2],310)
        self.assertEqual(e[0]-p[0],280)
        self.assertGreaterEqual(e2[1]-e[1],e[3]+10)

    async def test_v05_timeline_theme_shapes_keep_content(self):
        for theme in ('default','dark','forest','neutral','base','neo','neo-dark','redux','redux-dark','redux-color','redux-dark-color'):
            with self.subTest(theme=theme):
                s=await scene('timeline\nsection Releases\n2024 : Launch\n',{'theme':theme})
                visible=' '.join(texts(s))
                for label in ('Releases','2024','Launch'):self.assertIn(label,visible)
                self.assertEqual(len(s.layout['boxes']),3)

    async def test_v06_gantt_time_scaling_and_constant_row_gap(self):
        s=await scene('gantt\ndateFormat YYYY-MM-DD\ntodayMarker off\nA :a, 2024-01-01, 1d\nB :b, 2024-01-02, 1d\n',{'gantt':{'useWidth':600,'leftPadding':50,'rightPadding':50,'barHeight':20,'barGap':4}})
        a=shape_box(command(s,'a'));b=shape_box(command(s,'b'))
        self.assertAlmostEqual(b.x-a.x,250,delta=2)
        self.assertAlmostEqual(b.y-a.y,24,delta=1)
        self.assertAlmostEqual(a.width,b.width,delta=1)

    async def test_v07_gantt_compact_reuses_disjoint_lane(self):
        source='gantt\ndateFormat YYYY-MM-DD\ntodayMarker off\nsection S\nA :a, 2024-01-01, 2d\nB :b, 2024-01-03, 2d\nC :c, 2024-01-02, 2d\n'
        s=await scene(source,{'gantt':{'displayMode':'compact','useWidth':800}})
        a,b,c=(shape_box(command(s,id)) for id in 'abc')
        self.assertAlmostEqual(a.y,b.y)
        self.assertGreater(c.y,a.y)

    async def test_v08_gitgraph_all_direction_and_parallel_layout(self):
        source='commit id:"A"\nbranch dev\ncommit id:"B"\ncheckout main\ncommit id:"C"\nmerge dev id:"M"\n'
        for direction in ('LR','TB','BT'):
            for parallel in (False,True):
                with self.subTest(direction=direction,parallel=parallel):
                    s=await scene('gitGraph '+direction+':\n'+source,{'gitGraph':{'parallelCommits':parallel,'rotateCommitLabel':False}})
                    pos={r[0]:r[1:] for r in s.layout['commits']}
                    self.assertEqual(set(pos),set('ABCM'))
                    axis=0 if direction=='LR' else 1
                    sign=-1 if direction=='BT' else 1
                    self.assertGreater(sign*(pos['M'][axis]-pos['A'][axis]),0)
                    self.assertTrue(command(s,'edge-C-M').values[0])
                    self.assertTrue(command(s,'edge-B-M').values[0])

    async def test_v09_gitgraph_commit_types_and_tag_visible(self):
        s=await scene('gitGraph\ncommit id:"A" type:HIGHLIGHT tag:"v1"\ncommit id:"B" type:REVERSE\n')
        self.assertIn('v1',texts(s))
        self.assertAlmostEqual(shape_box(command(s,'A')).width,20)
        self.assertEqual(command(s,'B-reverse').kind,'path')


class BusinessGeometry(unittest.IsolatedAsyncioTestCase):
    async def test_v21_swimlane_public_provider_retains_source_group_metadata(self):
        import copy
        from py_mermaid.diagrams.business.swimlane import layout_provider
        nodes=[{'id':'A','width':60,'height':30,'parent':'L','label':'Work'},{'id':'B','width':80,'height':40,'parent':'L','label':'Done'}]
        parents=[{'id':'L','title':'Lane','padding':20,'classes':('lane-class',)}]
        edges=[{'id':'e','source':'A','target':'B','label':'Next','label_width':40,'label_height':18}]
        before=copy.deepcopy((nodes,parents,edges))
        result=await layout_provider(nodes,edges,parents=parents,direction='LR')
        self.assertEqual((nodes,parents,edges),before)
        self.assertEqual(result.engine,'mermaid-swimlane')
        self.assertEqual(set(result.nodes),{'A','B'})
        self.assertEqual(set(result.groups),{'L'})
        self.assertEqual(set(result.labels),{'e'})
        group=next(g for g in result.group_data if g['id']=='L')
        self.assertEqual(group['direction'],'LR')
        self.assertEqual(group['classes'],('lane-class',))
        self.assertEqual(group['label'],'Lane')
        self.assertGreater(group['width'],0)
        self.assertGreater(group['height'],0)

    async def test_v22_swimlane_public_provider_exposes_synthetic_group_data(self):
        from py_mermaid.diagrams.business.swimlane import layout_provider
        result=await layout_provider([{'id':'A','width':60,'height':30}],[],direction='TB')
        group=next(g for g in result.group_data if g['id']=='__swimlane_default__')
        self.assertEqual(group['label'],'')
        self.assertEqual(group['shape'],'swimlane')
        self.assertGreater(group['width'],60)
        self.assertGreater(group['height'],30)
        self.assertEqual(set(result.nodes),{'A'})

    async def test_v10_wardley_percentage_projection(self):
        s=await scene('wardley-beta\nsize [900, 600]\ncomponent A [0.8, 0.2]\ncomponent B [0.2, 0.8]\n')
        # Source plot inner rectangle [48,48]..[852,552]. Need the actual
        # node paths, not arbitrary text locations, to verify coordinate axes.
        circles=[c for c in s.commands if c.kind=='path' and 'a6.0,6.0' in c.values[0]]
        boxes=[shape_box(c) for c in circles]
        centers=[(b.x+b.width/2,b.y+b.height/2) for b in boxes]
        for expected in ((208.8,148.8),(691.2,451.2)):
            self.assertTrue(any(math.dist(p,expected)<.01 for p in centers),(expected,centers))

    async def test_v11_cynefin_transition_uses_domain_centers(self):
        s=await scene('cynefin-beta\ncomplex --> complicated : "Learning"\n',{'cynefin':{'width':800,'height':600,'padding':20,'seed':1}})
        paths=[str(c.values[0]) for c in s.commands if c.kind=='path']
        self.assertTrue(any('M220.0,170.0 Q420.0,230.0 620.0,170.0' in p for p in paths))
        self.assertIn('Learning',texts(s))

    async def test_v12_cynefin_confusion_caps_three_and_overflow(self):
        s=await scene('cynefin-beta\nconfusion\n "One"\n "Two"\n "Three"\n "Four"\n "Five"\n')
        visible=texts(s)
        for label in ('One','Two','Three','+2 more'):self.assertIn(label,visible)
        for hidden in ('Four','Five'):self.assertNotIn(hidden,visible)

    async def test_v13_cynefin_seed_is_reproducible_and_render_id_host_input(self):
        src='cynefin-beta\nclear\n "Repeat"\n'
        a=await scene(src,{'renderId':'host-a','cynefin':{'seed':17}})
        b=await scene(src,{'renderId':'host-b','cynefin':{'seed':17}})
        self.assertEqual([c.values[0] for c in a.commands if c.kind=='path'],[c.values[0] for c in b.commands if c.kind=='path'])
        c=await scene(src,{'renderId':'host-a','cynefin':{'seed':0}})
        d=await scene(src,{'renderId':'host-b','cynefin':{'seed':0}})
        self.assertNotEqual([x.values[0] for x in c.commands if x.kind=='path'],[x.values[0] for x in d.commands if x.kind=='path'])

    async def test_v14_event_frames_have_min100_and_no_missing_text(self):
        s=await scene('eventmodeling\ntf 1 ui Page\ntf 2 cmd Submit\ntf 3 evt Submitted\n')
        visible=' '.join(texts(s))
        for label in ('Page','Submit','Submitted'):self.assertIn(label,visible)
        boxes=[shape_box(c) for c in s.commands if c.kind=='path' and 'Q' in c.values[0]]
        boxes=[b for b in boxes if 99<=b.width<=471 and b.height>=99]
        self.assertGreaterEqual(len(boxes),3)

    async def test_v15_ishikawa_spine_and_leaf_bone_source_scale(self):
        s=await scene('ishikawa\nEffect\n People\n Process\n')
        self.assertIn('Effect',' '.join(texts(s)))
        for label in ('People','Process'):self.assertIn(label,' '.join(texts(s)))
        # A simple leaf cause has length .2*250=50, angle 82 degrees.
        paths=[shape_box(c) for c in s.commands if c.kind=='path' and c.bounds]
        self.assertTrue(any(abs(b.height-50*math.sin(math.radians(82)))<.1 for b in paths))

    async def test_v16_all_generic_business_scene_ink_is_inside_viewport(self):
        for src in ('cynefin-beta\nclear\n "Repeat"\n','wardley-beta\ncomponent A [0.5, 0.5]\n','ishikawa\nEffect\n Cause\n','eventmodeling\ntf 1 ui Page\n'):
            with self.subTest(source=src):
                s=await scene(src)
                for c in s.commands:
                    if c.bounds:
                        b=c.bounds
                        self.assertGreaterEqual(b.x,s.origin_x-1e-6)
                        self.assertGreaterEqual(b.y,s.origin_y-1e-6)
                        self.assertLessEqual(b.x+b.width,s.origin_x+s.width+1e-6)
                        self.assertLessEqual(b.y+b.height,s.origin_y+s.height+1e-6)

    async def test_v17_swimlane_all_directions_complete_ids_and_label(self):
        for direction in ('TB','TD','LR','RL','BT'):
            with self.subTest(direction=direction):
                s=await scene('swimlane-beta '+direction+'\nsubgraph L[Left]\nA[Start]\nend\nsubgraph R[Right]\nB[Done]\nend\nA -->|Handoff| B\n')
                self.assertEqual(s.layout.engine,'mermaid-swimlane')
                self.assertEqual({n.id for n in s.layout.nodes},{'A','B'})
                self.assertEqual({g.id for g in s.layout.groups},{'L','R'})
                self.assertEqual(len(s.layout.edges),1)
                self.assertEqual(len(s.layout.edge_labels),1)
                self.assertTrue(s.layout.edges[0].path)
                self.assertEqual({x[0] for x in s.group_overrides},{'L','R'})

    async def test_v18_swimlane_nested_containment_and_title_rotation(self):
        s=await scene('swimlane-beta LR\nsubgraph L[Lane]\n subgraph N[Nested]\n A[Work]\n end\n B[Other]\nend\nA --> B\n')
        groups={g.id:g.box for g in s.layout.groups}
        for n in s.layout.nodes:
            outer=groups['L'];b=n.box
            self.assertGreaterEqual(b.x,outer.x-1e-6)
            self.assertGreaterEqual(b.y,outer.y-1e-6)
            self.assertLessEqual(b.x+b.width,outer.x+outer.width+1e-6)
            self.assertLessEqual(b.y+b.height,outer.y+outer.height+1e-6)
        commands=dict(s.group_overrides)['L']
        label=next(c for c in commands if c.kind=='text' and c.values[0].text=='Lane')
        box,x,y,angle,_=label.values
        self.assertEqual(angle,-90)
        # Rotation is around text top-left. Final center=(x+h/2,y-w/2).
        self.assertAlmostEqual(y-box.width/2,groups['L'].y+groups['L'].height/2,delta=1)

    async def test_v19_swimlane_loose_nodes_real_default_lane_and_cycle(self):
        s=await scene('swimlane-beta TB\nA --> B\nB --> C\nC --> A\n')
        self.assertEqual({n.id for n in s.layout.nodes},{'A','B','C'})
        self.assertIn('__swimlane_default__',{g.id for g in s.layout.groups})
        self.assertEqual(len(s.layout.edges),3)
        boxes=[n.box for n in s.layout.nodes]
        for i,a in enumerate(boxes):
            for b in boxes[i+1:]:
                self.assertTrue(a.x+a.width<=b.x or b.x+b.width<=a.x or a.y+a.height<=b.y or b.y+b.height<=a.y)

    async def test_v20_agentflow_real_ELK_and_explicit_swimlane(self):
        src='agentflow-beta TB\nflow F[Team]\n A@{ shape: input, label: Input }\n B@{ shape: tool, label: Tool }\n A -->|Call| B\nend\n'
        for algorithm,engine in [('elk','pyelk'),('swimlane','mermaid-swimlane')]:
            with self.subTest(algorithm=algorithm):
                s=await scene(src,{'layout':algorithm})
                self.assertIn(engine,s.layout.engine)
                self.assertEqual({n.id for n in s.layout.nodes},{'A','B'})
                self.assertEqual(len(s.layout.edges),1)
                self.assertEqual(len(s.layout.edge_labels),1)
