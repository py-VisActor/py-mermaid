"""Topology/real-engine/numerical failure contracts from fixed source.

Only public installed packages and adjacent tracked inputs are needed. Raw
original ELK requests and Git SVG transforms are independently captured by the
separate source oracle, never generated as candidate-coordinate goldens.
"""
import copy
from dataclasses import replace
import math
import os
import time
import unittest
from unittest.mock import patch

from py_mermaid import parse,MermaidError
from .support_B import case,document,graph_scene,layout_observation,raw_nodes


class CompoundClosure(unittest.IsolatedAsyncioTestCase):
    def test_l01_authored_hidden_selfloop_survives(self):
        row=case('CL-B-AGENT-GENUINE-SOURCE-VALID');g=parse(row['source'],config=row['config']).model.graph
        self.assertEqual([n.id for n in g.nodes],['Outer'])
        self.assertEqual([(e.source,e.target) for e in g.edges],[('Outer','Outer')])

    def test_l02_nested_outermost_collapse_keeps_genuine_loop(self):
        row=case('CL-B-AGENT-NESTED-GENUINE');g=parse(row['source'],config=row['config']).model.graph
        self.assertEqual([n.id for n in g.nodes],['Outer'])
        self.assertEqual([(e.source,e.target) for e in g.edges],[('Outer','Outer')])

    def test_l03_synthetic_collapse_loop_still_removed(self):
        row=case('CL-B-AGENT-INTERNAL-SOURCE-VALID');g=parse(row['source'],config=row['config']).model.graph
        self.assertEqual([n.id for n in g.nodes],['Outer']);self.assertEqual(g.edges,())

    async def test_l04_real_engine_routes_authored_loop(self):
        diagram,scene=await graph_scene(case('CL-B-AGENT-GENUINE-SOURCE-VALID'))
        self.assertEqual(len(scene.layout.edges),1)
        edge=scene.layout.edges[0]
        self.assertEqual((diagram.model.graph.edges[0].source,diagram.model.graph.edges[0].target),('Outer','Outer'))
        self.assertTrue(edge.sections)
        self.assertGreater(len(edge.paint_points),1)

    async def test_l05_visible_collapsed_group_own_selfloop(self):
        diagram,scene=await graph_scene(case('CL-B-AGENT-VISIBLE-GROUP-SELF'))
        self.assertEqual(len(diagram.model.graph.edges),1);self.assertEqual(len(scene.layout.edges),1)

    async def test_l06_ancestor_route_ids_are_not_dropped(self):
        diagram,scene=await graph_scene(case('CL-B-AGENT-ANCESTOR-SOURCE-VALID'))
        self.assertEqual(len(scene.layout.edges),3)
        self.assertEqual({e.id for e in scene.layout.edges},{e.id for e in diagram.model.graph.edges})

    async def test_l07_all_eight_isolated_group_algorithms_reach_real_engine(self):
        rows=[r for r in document()['cases'] if r['id'].startswith('CL-B-GROUP-') and not r['closure']['cross']]
        self.assertEqual(len(rows),8)
        for row in rows:
            with self.subTest(case=row['id']):
                observed=await layout_observation(row)
                self.assertEqual(len(observed['rawInputs']),1);self.assertEqual(len(observed['rawOutputs']),1)
                nodes=list(raw_nodes(observed['rawInputs'][0]))
                self.assertTrue(any(n.get('layoutOptions',{}).get('elk.algorithm')==row['closure']['groupAlgorithm'] for n in nodes))
                self.assertEqual(len(observed['edges']),len(observed['routedEdges']))

    async def test_l08_cross_hierarchy_clears_all_algorithm_overrides(self):
        rows=[r for r in document()['cases'] if r['id'].startswith('CL-B-GROUP-') and r['closure']['cross']]
        self.assertEqual(len(rows),8)
        for row in rows:
            with self.subTest(case=row['id']):
                observed=await layout_observation(row)
                group=next(n for n in observed['rawInputs'][0]['children'] if 'children' in n)
                options=group['layoutOptions']
                self.assertEqual(options['elk.hierarchyHandling'],'INCLUDE_CHILDREN')
                for name in ('elk.algorithm','elk.aspectRatio','elk.contentAlignment','elk.expandNodes',
                             'elk.rectpacking.trybox','elk.rectpacking.packing.compaction.iterations',
                             'elk.rectpacking.whiteSpaceElimination.strategy','elk.rectpacking.widthApproximation.strategy'):
                    self.assertNotIn(name,options)
                self.assertEqual(options['spacing.baseValue'],24);self.assertEqual(options['spacing.nodeNode'],50)
                self.assertEqual(len(observed['edges']),3);self.assertEqual(len(observed['routedEdges']),3)

    async def test_l09_engine_exception_never_falls_back(self):
        from pyelk import ELK
        calls=[]
        async def fail(engine,graph,args=None):calls.append(copy.deepcopy(graph));raise RuntimeError('closure-sentinel-engine-failure')
        with patch.object(ELK,'layout',fail),self.assertRaises(MermaidError) as caught:
            await graph_scene(case('CL-B-AGENT-ANCESTOR-SOURCE-VALID'))
        self.assertEqual(caught.exception.code,'ELK_LAYOUT_FAILED');self.assertIn('closure-sentinel',str(caught.exception))
        self.assertEqual(len(calls),1)

    async def test_l10_nonfinite_and_boolean_engine_dimensions_rejected(self):
        from pyelk import ELK
        original=ELK.layout
        for value in (float('nan'),float('inf'),float('-inf'),True):
            calls=[]
            async def corrupt(engine,graph,args=None):
                calls.append(1);result=await original(engine,graph,args);result['width']=value;return result
            with self.subTest(value=value),patch.object(ELK,'layout',corrupt),self.assertRaises(MermaidError) as caught:
                await graph_scene(case('CL-B-AGENT-ANCESTOR-SOURCE-VALID'))
            self.assertEqual(caught.exception.code,'INVALID_ELK_RESULT');self.assertEqual(len(calls),1)

    async def test_l11_bad_route_point_rejected_not_zeroed(self):
        from pyelk import ELK
        original=ELK.layout;corrupted=[]
        async def corrupt(engine,graph,args=None):
            result=await original(engine,graph,args)
            for node in raw_nodes(result):
                for edge in node.get('edges',[]):
                    if edge.get('sections'):
                        edge['sections'][0]['startPoint']['x']=float('nan');corrupted.append(edge['id']);return result
            raise AssertionError('No real routed section available for this negative control')
        with patch.object(ELK,'layout',corrupt),self.assertRaises(MermaidError) as caught:
            await graph_scene(case('CL-B-AGENT-ANCESTOR-SOURCE-VALID'))
        self.assertEqual(caught.exception.code,'INVALID_ELK_RESULT');self.assertEqual(len(corrupted),1)

    async def test_l12_duplicate_engine_identity_rejected(self):
        from pyelk import ELK
        original=ELK.layout
        async def corrupt(engine,graph,args=None):
            result=await original(engine,graph,args);result['children'].append(copy.deepcopy(result['children'][0]));return result
        with patch.object(ELK,'layout',corrupt),self.assertRaises(MermaidError) as caught:
            await graph_scene(case('CL-B-AGENT-ANCESTOR-SOURCE-VALID'))
        self.assertEqual(caught.exception.code,'INVALID_ELK_RESULT')


class GitClosure(unittest.IsolatedAsyncioTestCase):
    async def test_l13_all_directions_rotations_preserve_dense_edges(self):
        rows=[r for r in document()['cases'] if r['kind']=='gitGraph']
        self.assertEqual(len(rows),6)
        for row in rows:
            with self.subTest(case=row['id']):
                diagram,scene=await graph_scene(row)
                expected=sum(len(c.parents) for c in diagram.model.commits)
                self.assertEqual(expected,9)
                self.assertEqual(sum(p.role=='edge' for p in scene.commands),9)
                self.assertTrue(all(math.isfinite(v) for _,x,y in scene.layout['commits'] for v in (x,y)))

    async def test_l14_branch_labels_use_source_lane_spacing(self):
        for row in [r for r in document()['cases'] if r['kind']=='gitGraph']:
            with self.subTest(case=row['id']):
                diagram,scene=await graph_scene(row);positions=dict(scene.layout['branches'])
                labels={p.semantic_id:p.values[0] for p in scene.commands if p.kind=='text'}
                names=list(positions);vertical=diagram.model.direction!='LR';rotate=row['config']['gitGraph']['rotateCommitLabel']
                self.assertEqual(names,['main','dev'])
                expected=50+(40 if rotate else 0)+(labels['branch-label-main'].width/2 if vertical else 0)
                self.assertAlmostEqual(positions['dev']-positions['main'],expected)
                self.assertEqual(labels['branch-label-main'].text,'main');self.assertEqual(labels['branch-label-dev'].text,'dev')

    async def test_l15_reverse_tag_stack_and_source_rotation(self):
        for row in [r for r in document()['cases'] if r['kind']=='gitGraph']:
            with self.subTest(case=row['id']):
                diagram,scene=await graph_scene(row)
                tags={p.semantic_id:p for p in scene.commands if p.kind=='text' and p.semantic_id.startswith('A-tag-')}
                self.assertEqual([tags['A-tag-'+str(i)].values[0].text for i in range(3)],['last','long-release','first'])
                self.assertEqual({p.values[3] for p in tags.values()},{0 if diagram.model.direction=='LR' else 45})

    @unittest.skipUnless(hasattr(time,'tzset'),'Public Gantt DST geometry needs Linux actual IANA TZ')
    async def test_l16_linux_public_gantt_calendar_vs_elapsed_bar_width(self):
        previous=os.environ.get('TZ')
        try:
            os.environ['TZ']='America/New_York';time.tzset()
            # Original controls finish at midnight BEFORE the 02:00 transition;
            # fixed-source task endpoints and SVG bars prove equal duration.
            for season in ('SPRING','FALL'):
                _,scene=await graph_scene(case('CL-B-DST-PUBLIC-'+season))
                widths={row[0]:row[3] for row in scene.layout['tasks']}
                self.assertEqual(widths['a'],widths['b'])
            # Keep the original inputs. New IDs begin on the transition date,
            # so calendar +1d actually spans23/25 elapsed hours against24h.
            for season,larger in [('SPRING','b'),('FALL','a')]:
                _,scene=await graph_scene(case('CL-B-DST-CROSS-'+season))
                widths={row[0]:row[3] for row in scene.layout['tasks']}
                self.assertGreater(widths[larger],widths['a' if larger=='b' else 'b'])
        finally:
            if previous is None:os.environ.pop('TZ',None)
            else:os.environ['TZ']=previous
            time.tzset()


def assert_tick_pixels(test,png,events):
    from PIL import Image
    from io import BytesIO
    image=Image.open(BytesIO(png)).convert('RGBA')
    test.assertTrue(events)
    for event in events:
        b=event.box;test.assertIsNotNone(b)
        cx=b.x+b.width/2
        points=[image.getpixel((x,y)) for y in range(max(0,math.ceil(b.y)),min(image.height,math.floor(b.y+b.height)))
                for x in range(max(0,math.ceil(b.x)),min(image.width,math.floor(b.x+b.width))) if abs(x-cx)>3]
        test.assertGreater(sum(p[3]>20 and min(p[:3])<200 for p in points),5,'tick glyph ink absent '+str(event.text))


def assert_cherry_pixels(test,png,event):
    # Fixed default source parent nodeBorder #333; white fruit/stems are
    # independently visible inside it. A blue branch disk cannot pass.
    from PIL import Image
    from io import BytesIO
    image=Image.open(BytesIO(png)).convert('RGB');b=event.box
    test.assertIsNotNone(b);cx=b.x+b.width/2;cy=b.y+b.height/2
    ring=[];core=[]
    for y in range(max(0,math.ceil(cy-10)),min(image.height,math.floor(cy+10))):
        for x in range(max(0,math.ceil(cx-10)),min(image.width,math.floor(cx+10))):
            distance=math.hypot(x+.5-cx,y+.5-cy);pixel=image.getpixel((x,y))
            if 7<distance<9:ring.append(pixel)
            if distance<6.7:core.append(pixel)
    test.assertGreater(sum(max(abs(v-51) for v in p)<25 for p in ring),30,'missing source dark cherry shell')
    test.assertGreater(sum(min(p)>230 for p in core),8,'missing white cherry fruit/stems')


class PublicMarkerPresentationClosure(unittest.IsolatedAsyncioTestCase):
    async def git_result(self,config=None):
        from py_mermaid import arender
        row=case('CL-B-GIT-TB-ROTATE')
        return await arender(row['source'],config=config or row['config'],backend='cpu')

    async def test_l17_cherry_source_primitives_and_real_ink(self):
        result=await self.git_result()
        commits=[c for c in result.diagram.model.commits if c.type=='CHERRY_PICK']
        self.assertEqual(len(commits),2)
        for commit in commits:
            outer=next(e for e in result.trace if e.semantic_id==commit.id and e.kind=='commit')
            self.assertIn(outer.fill,('#333','#333333','rgb(51,51,51)'))
            fruits=[e for e in result.trace if e.semantic_id.startswith(commit.id+'-cherry-') and '-stem-' not in e.semantic_id]
            stems=[e for e in result.trace if e.semantic_id.startswith(commit.id+'-cherry-stem-')]
            self.assertEqual(len(fruits),2);self.assertEqual(len(stems),2)
            self.assertTrue(all(e.fill in ('#fff','#ffffff','white') for e in fruits))
            self.assertTrue(all(e.stroke in ('#fff','#ffffff','white') and e.stroke_width==1 for e in stems))
            assert_cherry_pixels(self,result.data,outer)

    async def test_l18_cherry_class_css_is_consumed_not_just_recorded(self):
        from py_mermaid.rendering.skia.scene import Painter
        row=case('CL-B-GIT-TB-ROTATE');cfg=copy.deepcopy(row['config'])
        cfg['themeCSS']='.commit-cherry-pick { fill: #13579b !important; stroke: #13579b !important; }'
        positive=await self.git_result(cfg)
        ids={c.id for c in positive.diagram.model.commits if c.type=='CHERRY_PICK'}
        def authored(result):
            values=[e for e in result.trace if e.semantic_id in ids and e.kind=='commit']
            self.assertEqual(len(values),2);self.assertTrue(all(e.fill=='#13579b' for e in values))
        authored(positive)
        original=Painter.style
        def missing_class(owner,classes=(),**kw):
            return original(owner,tuple(c for c in classes if c!='commit-cherry-pick'),**kw)
        with patch.object(Painter,'style',missing_class):negative=await self.git_result(cfg)
        with self.assertRaises(AssertionError):authored(negative)

    async def test_l19_cherry_fruit_paint_control_is_pixel_detectable(self):
        from py_mermaid.rendering.skia.scene import Painter
        original=Painter.style
        def no_fruit(owner,classes=(),**kw):
            resolved=original(owner,classes,**kw)
            if 'commit-cherry-pick' in classes and kw.get('tag')=='circle' and resolved.fill in ('#fff','#ffffff','white'):
                return replace(resolved,fill='#333')
            if 'commit-cherry-pick' in classes and kw.get('tag')=='line':return replace(resolved,stroke='#333')
            return resolved
        with patch.object(Painter,'style',no_fruit):negative=await self.git_result()
        ids={c.id for c in negative.diagram.model.commits if c.type=='CHERRY_PICK'}
        for outer in [e for e in negative.trace if e.semantic_id in ids and e.kind=='commit']:
            with self.assertRaises(AssertionError):assert_cherry_pixels(self,negative.data,outer)

    async def test_l20_collapsed_container_metadata_and_slot7_paint(self):
        from py_mermaid import arender
        for ident in ('CL-B-AGENT-GENUINE-SOURCE-VALID','CL-B-AGENT-NESTED-GENUINE'):
            row=case(ident);diagram=parse(row['source'],config=row['config'])
            collapsed=[n for n in diagram.model.graph.nodes if n.shape=='collapsedGroup']
            self.assertTrue(collapsed)
            for node in collapsed:self.assertEqual(dict(node.metadata)['containerType'],'flow')
            result=await arender(row['source'],config=row['config'],backend='cpu')
            outer=[e for e in result.trace if e.kind=='node' and e.semantic_id in {n.id for n in collapsed}]
            self.assertTrue(outer)
            for event in outer:
                self.assertEqual(event.fill.lower(),'#fefce8');self.assertEqual(event.stroke.lower(),'#facc15')
            self.assertTrue(any(e.kind=='edge' for e in result.trace))

    async def test_l21_agent_effective_appearance_and_palette_survive_flow_bridge(self):
        # Agentflow reads its own appearance; flowchart defaults cannot replace
        # its effective theme/look or leave palette values from another theme.
        from py_mermaid import arender
        from py_mermaid.config.values import thaw_value
        row=case('CL-B-AGENT-GENUINE-SOURCE-VALID')
        for look in ('classic','neo','handDrawn'):
            config={'theme':'base','look':look,'themeVariables':{
                'mainBkg':'#edf1f5','nodeBorder':'#713579','textColor':'#123456'}}
            diagram=parse(row['source'],config=config)
            graph=diagram.model.graph
            self.assertEqual((graph.config.theme,graph.config.look),('base',look))
            variables=thaw_value(graph.config.theme_variables)
            self.assertEqual(variables['mainBkg'],'#edf1f5')
            self.assertEqual(variables['nodeBorder'],'#713579')
            self.assertEqual(graph.config.fill,'#edf1f5')
            self.assertEqual(graph.config.stroke,'#713579')
            result=await arender(row['source'],config=config,backend='cpu')
            self.assertEqual((result.annotations.flowchart.config.theme,
                              result.annotations.flowchart.config.look),('base',look))
            self.assertTrue(any(e.kind=='edge' for e in result.trace))

if __name__=='__main__':unittest.main()

