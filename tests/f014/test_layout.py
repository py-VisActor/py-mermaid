"""F014 independent source contracts, real ELK primary, synthetic paint controls.

Source expectations are literal option tables, analytic geometry and semantic
relations. No candidate private helper or candidate-generated coordinate golden
is used. All public production operations occur inside test methods only.
"""
from __future__ import annotations
import copy
from dataclasses import asdict,replace
import json
import math
import re
import sys
import types
import unittest
from unittest.mock import patch
from py_mermaid.config import resolve_config
from py_mermaid.layout.elk import layout_flowchart
from py_mermaid.geometry.edges import edge_markers,marker_offsets,rounded_path,line_hop_paths,finish_edges,align_degenerate_boxes
from py_mermaid.geometry.shapes import shape_geometry
from py_mermaid.model.flowchart import (Box,Point,Flowchart,FlowNode,FlowGroup,FlowEdge,FlowLayout,
    PlacedNode,PlacedEdgeLabel,RoutedEdge,EdgeSection,MeasuredNode,SourcePosition,SourceSpan,MermaidError)
from py_mermaid.rendering.skia import CanvasSession
ROOTS=('elk','elk.stress','elk.force','elk.mrtree','elk.sporeOverlap','elk.box','elk.rectpacking')
GROUP_ALGORITHMS=('elk.layered','elk.box','elk.rectpacking','elk.stress','elk.force','elk.mrtree','elk.radial','elk.sporeOverlap')
DIRECTIONS={'TD':'DOWN','TB':'DOWN','BT':'UP','LR':'RIGHT','RL':'LEFT'}
PRESETS={'default':('NETWORK_SIMPLEX','BRANDES_KOEPF','BRANDES_KOEPF','BALANCED','DEPTH_FIRST'),
 'legacy':('NETWORK_SIMPLEX','BRANDES_KOEPF','BRANDES_KOEPF','NONE','GREEDY'),
 'modelOrder':('NETWORK_SIMPLEX','NETWORK_SIMPLEX','BRANDES_KOEPF','NONE','GREEDY_MODEL_ORDER'),
 'depthFirst':('NETWORK_SIMPLEX','NETWORK_SIMPLEX','BRANDES_KOEPF','NONE','DEPTH_FIRST')}


def span():
    p=SourcePosition(0,0,1,0);return SourceSpan(p,p)


def diagram(*,layout='elk',direction='TD',elk=None,group_algorithm=None,cross=False,label=''):
    p=span();cfg=resolve_config({'layout':layout,'look':'classic','theme':'base','elk':elk or {},'flowchart':{'minNodeWidth':0}})
    nodes=(FlowNode('A','Alpha',p,parent_id='G' if group_algorithm else None),FlowNode('B','Long Beta',p,parent_id='G' if group_algorithm else None),FlowNode('C','Gamma',p))
    groups=(FlowGroup('G','Group',p,('A','B'),metadata=(('algorithm',group_algorithm),)),) if group_algorithm else ()
    edges=(FlowEdge('AB','A','B',p,label,p,marker_end='none'),)+( (FlowEdge('BC','B','C',p,marker_end='none'),) if cross or not group_algorithm else () )
    return Flowchart('independent test semantic input',direction,nodes,edges,cfg,groups=groups)


def contains(a,b,tol=1e-5):
    return b.x>=a.x-tol and b.y>=a.y-tol and b.x+b.width<=a.x+a.width+tol and b.y+b.height<=a.y+a.height+tol


def overlap(a,b):
    return min(a.x+a.width,b.x+b.width)-max(a.x,b.x)>1e-5 and min(a.y+a.height,b.y+b.height)-max(a.y,b.y)>1e-5


def all_raw_edges(graph):
    result=list(graph.get('edges',[]))
    for child in graph.get('children',[]):result.extend(all_raw_edges(child))
    return result


class ActualELKTests(unittest.IsolatedAsyncioTestCase):
    async def actual(self,chart):
        from pyelk import ELK
        original=ELK.layout;inputs=[];outputs=[]
        async def observe(engine,graph,args=None):
            inputs.append(copy.deepcopy(graph));result=await original(engine,graph,args);outputs.append(copy.deepcopy(result));return result
        session=CanvasSession('cpu');measured=session.measure(chart);ann=session.measure_annotations(chart)
        before=copy.deepcopy((chart,measured,ann))
        with patch.object(ELK,'layout',observe):
            result=await layout_flowchart(chart,measured,measured_groups=ann.groups,measured_edge_labels=ann.edge_labels,
                measured_title=ann.title,title_suppressed=ann.title_suppressed)
        self.assertEqual(before,(chart,measured,ann))
        self.assertEqual(tuple(n.id for n in result.nodes),tuple(n.id for n in chart.nodes))
        self.assertEqual(tuple(g.id for g in result.groups),tuple(g.id for g in chart.groups))
        self.assertEqual(tuple(e.id for e in result.edges),tuple(e.id for e in chart.edges))
        self.assertEqual(result.engine_version,'0.1.0');self.assertEqual(len(inputs),1)
        self.assertTrue(math.isfinite(result.width) and result.width>0)
        self.assertTrue(math.isfinite(result.height) and result.height>0)
        for node in result.nodes:
            self.assertTrue(all(math.isfinite(v) for v in (node.box.x,node.box.y,node.box.width,node.box.height)))
            self.assertGreater(node.box.width,0);self.assertGreater(node.box.height,0)
        for source,route in zip(chart.edges,result.edges):
            self.assertTrue(route.paint_points)
            self.assertEqual(route.effective_curve,'rounded' if route.sections else 'linear')
            for point in route.paint_points:self.assertTrue(math.isfinite(point.x) and math.isfinite(point.y))
            if len(route.paint_points)>1 and source.stroke!='invisible':self.assertTrue(route.path)
            if source.stroke=='invisible':self.assertEqual(route.path,'')
        json.dumps(asdict(result))
        return result,measured,ann,inputs[0],outputs[0]

    async def test_l01_all_seven_root_algorithms_use_actual_native_provider(self):
        for name in ROOTS:
            with self.subTest(layout=name):
                result,_,_,raw,_=await self.actual(diagram(layout=name))
                expected='elk.layered' if name=='elk' else name
                self.assertEqual(raw['layoutOptions']['elk.algorithm'],expected)
                self.assertEqual(result.engine,'pyelk/'+expected)
                if name in ('elk.box','elk.rectpacking'):
                    self.assertTrue(all(not edge.sections for edge in result.edges))
                    self.assertTrue(all(edge.effective_curve=='linear' for edge in result.edges))

    async def test_l02_all_eight_group_algorithms_run_in_separate_container(self):
        for name in GROUP_ALGORITHMS:
            with self.subTest(algorithm=name):
                result,_,_,raw,engine_output=await self.actual(diagram(group_algorithm=name))
                group=next(child for child in raw['children'] if child.get('children'))
                self.assertEqual(group['layoutOptions']['elk.algorithm'],name)
                self.assertEqual(group['layoutOptions']['elk.hierarchyHandling'],'SEPARATE_CHILDREN')
                self.assertEqual(result.engine,'pyelk/elk.layered')
                if name=='elk.radial':
                    # Fixed upstream and the real native output both size this
                    # container too small. Preserve original source frame and
                    # visible defect explicitly; never expand a frame to pass.
                    engine_group=next(node for node in engine_output['children'] if node.get('children'))
                    actual=result.groups[0].box
                    self.assertEqual((actual.x,actual.y,actual.width,actual.height),
                        (engine_group['x'],engine_group['y'],engine_group['width'],engine_group['height']))
                    self.assertTrue(any(not contains(actual,node.box) for node in result.nodes[:2]))
                else:
                    for node in result.nodes[:2]:self.assertTrue(contains(result.groups[0].box,node.box))

    async def test_l03_all_five_root_directions_and_nonoverlap(self):
        for direction,expected in DIRECTIONS.items():
            with self.subTest(direction=direction):
                result,_,_,raw,_=await self.actual(diagram(direction=direction))
                self.assertEqual(raw['layoutOptions']['elk.direction'],expected)
                boxes={node.id:node.box for node in result.nodes}
                for a,b in zip(result.nodes,result.nodes[1:]):
                    self.assertFalse(overlap(a.box,b.box))
                    if expected=='DOWN':self.assertLessEqual(a.box.y+a.box.height,b.box.y+1e-5)
                    elif expected=='UP':self.assertLessEqual(b.box.y+b.box.height,a.box.y+1e-5)
                    elif expected=='RIGHT':self.assertLessEqual(a.box.x+a.box.width,b.box.x+1e-5)
                    else:self.assertLessEqual(b.box.x+b.box.width,a.box.x+1e-5)

    async def test_l04_four_presets_preserve_root_and_container_distinction(self):
        for preset,(layering,root,child,alignment,breaking) in PRESETS.items():
            with self.subTest(preset=preset):
                _,_,_,raw,_=await self.actual(diagram(elk={'preset':preset},group_algorithm='elk.layered'))
                root_opts=raw['layoutOptions'];group_opts=next(n for n in raw['children'] if n.get('children'))['layoutOptions']
                self.assertEqual(root_opts['elk.layered.layering.strategy'],layering)
                self.assertEqual(root_opts['elk.layered.nodePlacement.strategy'],root)
                self.assertEqual(group_opts['elk.layered.nodePlacement.strategy'],child)
                for options in (root_opts,group_opts):
                    self.assertEqual(options['elk.layered.nodePlacement.bk.fixedAlignment'],alignment)
                    self.assertEqual(options['elk.layered.cycleBreaking.strategy'],breaking)

    async def test_l05_explicit_public_option_mapping_and_preset_override(self):
        cases=(('mergeEdges',True,'elk.layered.mergeEdges'),('nodePlacementStrategy','SIMPLE','elk.layered.nodePlacement.strategy'),
          ('nodePlacementAlignment','RIGHTDOWN','elk.layered.nodePlacement.bk.fixedAlignment'),('layeringStrategy','LONGEST_PATH','elk.layered.layering.strategy'),
          ('layeringLayerBound',2,'elk.layered.layering.coffmanGraham.layerBound'),('cycleBreakingStrategy','MODEL_ORDER','elk.layered.cycleBreaking.strategy'),
          ('forceNodeModelOrder',True,'elk.layered.crossingMinimization.forceNodeModelOrder'),('considerModelOrder','PREFER_EDGES','elk.layered.considerModelOrder.strategy'))
        for key,value,elk_key in cases:
            with self.subTest(key=key):
                _,_,_,raw,_=await self.actual(diagram(elk={'preset':'legacy',key:value}))
                self.assertEqual(raw['layoutOptions'][elk_key],value)
                self.assertEqual(raw['layoutOptions']['spacing.baseValue'],40)
        # Remaining public keys: preset L04, keepEntry L06, orientFeedback L07,
        # straightenEdges + lineHops public postprocessing controls P04-P07.

    async def test_l06_keep_entry_uses_greedy_edge_order_not_first_declared_node(self):
        chart=diagram(elk={'keepEntryNodeOnTop':True})
        p=span();chart=replace(chart,nodes=(FlowNode('B','B',p),FlowNode('A','Alpha',p)),
          edges=(FlowEdge('AB','A','B',p,marker_end='none'),FlowEdge('BA','B','A',p,marker_end='none')))
        _,_,_,raw,_=await self.actual(chart)
        self.assertEqual(raw['children'][1]['layoutOptions']['elk.layered.layering.layerConstraint'],'FIRST')
        self.assertNotEqual(raw['children'][0].get('layoutOptions',{}).get('elk.layered.layering.layerConstraint'),'FIRST')

    async def test_l07_feedback_option_changes_only_source_preorientation(self):
        chart=diagram(group_algorithm='elk.layered',cross=True)
        chart=replace(chart,edges=chart.edges+(FlowEdge('CA','C','A',span(),marker_end='none'),))
        on,_,_,raw_on,_=await self.actual(replace(chart,config=resolve_config({'elk':{'orientFeedbackEdges':True}})))
        off,_,_,raw_off,_=await self.actual(replace(chart,config=resolve_config({'elk':{'orientFeedbackEdges':False}})))
        semantic_pairs=[(e.source,e.target) for e in chart.edges]
        on_pairs=[(e['sources'],e['targets']) for e in raw_on['edges']]
        off_pairs=[(e['sources'],e['targets']) for e in raw_off['edges']]
        self.assertNotEqual(on_pairs,off_pairs)
        self.assertEqual(len(on.edges),len(semantic_pairs));self.assertEqual(len(off.edges),len(semantic_pairs))
        self.assertTrue(all(route.paint_points for route in (*on.edges,*off.edges)))

    async def test_l08_cross_boundary_clears_only_custom_algorithm_scope(self):
        _,_,_,raw,_=await self.actual(diagram(group_algorithm='elk.rectpacking',cross=True))
        group=next(child for child in raw['children'] if child.get('children'));options=group['layoutOptions']
        self.assertNotIn('elk.algorithm',options)
        self.assertNotIn('elk.rectpacking.trybox',options)
        self.assertNotIn('elk.aspectRatio',options)
        self.assertEqual(options['elk.hierarchyHandling'],'INCLUDE_CHILDREN')
        self.assertEqual(options['spacing.baseValue'],24)
        self.assertEqual(options['spacing.nodeNode'],50)

    async def test_l09_min_length_and_declared_curve_do_not_invent_elk_options(self):
        chart=diagram();base,_,_,raw_base,_=await self.actual(chart)
        changed=replace(chart,edges=tuple(replace(edge,min_length=10,curve='natural') for edge in chart.edges))
        routed,_,_,raw_changed,_=await self.actual(changed)
        self.assertEqual(raw_base,raw_changed)
        self.assertEqual(tuple(edge.sections for edge in base.edges),tuple(edge.sections for edge in routed.edges))
        self.assertTrue(all(edge.effective_curve=='rounded' for edge in routed.edges))
        for key in json.dumps(raw_changed).split('"'):
            self.assertNotIn('minLength',key)

    async def test_l10_box_and_rectpacking_physical_frame_and_cached_ink(self):
        for algo in ('elk.box','elk.rectpacking'):
            with self.subTest(algorithm=algo):
                chart=diagram(group_algorithm=algo)
                chart=replace(chart,nodes=(replace(chart.nodes[0],label='Small'),replace(chart.nodes[1],label='A long wide label WWWWWWWWWWWWW'),chart.nodes[2]))
                result,measured,_,raw,_=await self.actual(chart)
                for placed,size in zip(result.nodes,measured):
                    self.assertGreaterEqual(placed.box.width+1e-5,size.width)
                    self.assertGreaterEqual(placed.box.height+1e-5,size.height)
                    ink=Box(placed.box.x+(placed.box.width-size.width)/2,placed.box.y+(placed.box.height-size.height)/2,size.width,size.height)
                    self.assertTrue(contains(placed.box,ink))
                self.assertTrue(any(n['layoutOptions'].get('elk.expandNodes')=='true' for n in raw['children'] if n.get('children')))

    async def test_l11_raw_sections_preserved_before_shape_and_marker_paint(self):
        chart=diagram();chart=replace(chart,nodes=tuple(replace(n,shape='diamond') for n in chart.nodes),edges=tuple(replace(e,marker_start='circle',marker_end='point') for e in chart.edges))
        result,_,_,raw_input,raw=await self.actual(chart)
        by_id={edge['id']:edge for edge in all_raw_edges(raw)}
        for index,route in enumerate(result.edges):
            # No containers here: public engine sections are root-local=absolute.
            original=by_id[raw_input['edges'][index]['id']]['sections']
            self.assertEqual(len(route.sections),len(original))
            for value,expected in zip(route.sections,original):
                self.assertEqual(value.start,Point(**expected['startPoint']))
                self.assertEqual(value.end,Point(**expected['endPoint']))
            self.assertTrue(route.paint_points)
            self.assertTrue(route.path)

    async def test_l12_nonrouting_nonaxis_endpoint_stays_on_real_diamond(self):
        chart=diagram(layout='elk.box');chart=replace(chart,nodes=tuple(replace(n,shape='diamond') for n in chart.nodes))
        result,measured,_,_,_=await self.actual(chart)
        nodes={n.id:n.box for n in result.nodes};sizes={n.id:n for n in measured}
        for edge,route in zip(chart.edges,result.edges):
            for identifier,point in ((edge.source,route.paint_points[0]),(edge.target,route.paint_points[-1])):
                box=nodes[identifier];size=sizes[identifier];cx,cy=box.x+box.width/2,box.y+box.height/2
                self.assertAlmostEqual(abs(point.x-cx)/(size.width/2)+abs(point.y-cy)/(size.height/2),1,delta=.005)

    async def test_l13_nonrouting_selfloop_keeps_id_without_fabricated_loop(self):
        for algo in ('elk.box','elk.rectpacking'):
            chart=diagram(layout=algo);chart=replace(chart,edges=(FlowEdge('loop','A','A',span()),))
            with self.subTest(algorithm=algo):
                result,_,_,_,_=await self.actual(chart)
                edge=result.edges[0]
                self.assertEqual(edge.id,'loop');self.assertEqual(edge.sections,())
                self.assertEqual(len(edge.paint_points),1);self.assertEqual(edge.path,'')

    async def test_l14_invisible_and_source_invalid_keep_layout_semantic_edges(self):
        chart=diagram();chart=replace(chart,edges=(replace(chart.edges[0],stroke='invisible',marker_start='none',marker_end='none'),
          replace(chart.edges[1],stroke='INVALID',edge_type='INVALID',min_length=None)))
        result,_,_,_,_=await self.actual(chart)
        self.assertEqual(result.edges[0].path,'')
        self.assertTrue(result.edges[0].paint_points)
        self.assertTrue(result.edges[1].path)

    async def test_l15_engine_failure_is_single_call_and_never_success_fallback(self):
        from pyelk import ELK
        chart=diagram();session=CanvasSession('cpu');nodes=session.measure(chart);calls=[]
        async def fail(engine,graph,args=None):calls.append(copy.deepcopy(graph));raise RuntimeError('independent engine fault')
        with patch.object(ELK,'layout',fail),self.assertRaises(MermaidError) as error:
            await layout_flowchart(chart,nodes)
        self.assertEqual(error.exception.code,'ELK_LAYOUT_FAILED')
        self.assertEqual(len(calls),1)
        self.assertIn('independent engine fault',str(error.exception))

    async def test_l16_wrong_engine_version_and_unavailable_are_explicit(self):
        chart=diagram();session=CanvasSession('cpu');nodes=session.measure(chart)
        module=types.ModuleType('pyelk');module.__version__='wrong'
        class Forbidden:
            def __init__(self):raise AssertionError('Wrong-version engine must never initialize')
        module.ELK=Forbidden
        with patch.dict(sys.modules,{'pyelk':module}),self.assertRaises(MermaidError) as error:
            await layout_flowchart(chart,nodes)
        self.assertEqual(error.exception.code,'ELK_VERSION_MISMATCH')
        with patch.dict(sys.modules,{'pyelk':None}),self.assertRaises(MermaidError) as error:
            await layout_flowchart(chart,nodes)
        self.assertEqual(error.exception.code,'ELK_UNAVAILABLE')

    async def test_l17_all_public_enum_values_reach_native_options(self):
        enums={
          'nodePlacementStrategy':(('SIMPLE','NETWORK_SIMPLEX','LINEAR_SEGMENTS','BRANDES_KOEPF'),'elk.layered.nodePlacement.strategy'),
          'nodePlacementAlignment':(('NONE','LEFTUP','LEFTDOWN','RIGHTUP','RIGHTDOWN','BALANCED'),'elk.layered.nodePlacement.bk.fixedAlignment'),
          'layeringStrategy':(('NETWORK_SIMPLEX','LONGEST_PATH','LONGEST_PATH_SOURCE','COFFMAN_GRAHAM','MIN_WIDTH','STRETCH_WIDTH','INTERACTIVE'),'elk.layered.layering.strategy'),
          'cycleBreakingStrategy':(('GREEDY','DEPTH_FIRST','INTERACTIVE','MODEL_ORDER','GREEDY_MODEL_ORDER'),'elk.layered.cycleBreaking.strategy'),
          'considerModelOrder':(('NONE','NODES_AND_EDGES','PREFER_EDGES','PREFER_NODES'),'elk.layered.considerModelOrder.strategy')}
        for key,(values,target) in enums.items():
            for value in values:
                with self.subTest(key=key,value=value):
                    _,_,_,raw,_=await self.actual(diagram(elk={key:value}))
                    self.assertEqual(raw['layoutOptions'][target],value)

    async def test_l18_keep_entry_does_not_pin_acyclic_natural_source(self):
        _,_,_,raw,_=await self.actual(diagram(elk={'keepEntryNodeOnTop':True}))
        self.assertTrue(all('elk.layered.layering.layerConstraint' not in node.get('layoutOptions',{}) for node in raw['children']))

    async def test_l19_group_direction_branch_and_cross_boundary_retention(self):
        for direction,expected in DIRECTIONS.items():
            with self.subTest(direction=direction):
                chart=diagram(group_algorithm='elk.layered',cross=True)
                chart=replace(chart,groups=(replace(chart.groups[0],metadata=(),direction=direction),))
                _,_,_,raw,_=await self.actual(chart)
                group=next(node for node in raw['children'] if node.get('children'))
                self.assertEqual(group['layoutOptions']['elk.direction'],expected)
                self.assertEqual(group['layoutOptions']['elk.algorithm'],'elk.layered')
                self.assertEqual(group['layoutOptions']['elk.hierarchyHandling'],'INCLUDE_CHILDREN')

    async def test_l20_nested_group_and_ancestor_endpoints_no_lost_route(self):
        chart=diagram();p=span()
        chart=replace(chart,nodes=(FlowNode('A','Alpha',p,parent_id='Inner'),FlowNode('B','Beta',p,parent_id='Inner'),FlowNode('C','Gamma',p,parent_id='Outer'),FlowNode('D','Delta',p)),
          groups=(FlowGroup('Inner','Inner',p,('A','B'),'Outer'),FlowGroup('Outer','Outer',p,('Inner','C'))),
          edges=tuple(FlowEdge(str(i),a,b,p,marker_start='circle',marker_end='cross') for i,(a,b) in enumerate((('A','C'),('A','Outer'),('Outer','D'),('Inner','D')))))
        result,_,_,_,_=await self.actual(chart)
        groups={g.id:g for g in result.groups}
        self.assertTrue(contains(groups['Outer'].box,groups['Inner'].box))
        self.assertEqual(len(result.edges),4)
        self.assertTrue(all(len(e.paint_points)>=2 and e.path for e in result.edges))

    async def test_l21_empty_graph_calls_real_elk_and_preserves_its_empty_box(self):
        from pyelk import ELK
        chart=diagram();chart=replace(chart,nodes=(),edges=(),groups=())
        original=ELK.layout;inputs=[];outputs=[]
        async def observe(engine,graph,args=None):
            inputs.append(copy.deepcopy(graph));result=await original(engine,graph,args);outputs.append(copy.deepcopy(result));return result
        with patch.object(ELK,'layout',observe):
            result=await layout_flowchart(chart,())
        self.assertEqual(len(inputs),1)
        self.assertEqual(inputs[0]['children'],[]);self.assertEqual(inputs[0]['edges'],[])
        self.assertEqual((result.width,result.height),(outputs[0]['width'],outputs[0]['height']))
        self.assertGreaterEqual(result.width,0);self.assertGreaterEqual(result.height,0)
        self.assertEqual((result.nodes,result.edges,result.groups),((),(),()))
        self.assertEqual(result.engine,'pyelk/elk.layered')

    async def test_l22_real_labelless_gallery_aligns_paint_boxes_without_mutating_raw_frames(self):
        from py_mermaid import parse
        names=('sm-circ','fr-circ','f-circ','cross-circ','choice','fork','bolt','anchor','hourglass')
        text='flowchart TD\n'+'\n'.join([f'N{i}@{{shape: {name}, label: "Ignored{i}"}}' for i,name in enumerate(names)]+[f'N{i} --> N{i+1}' for i in range(8)])
        chart=parse(text,config={'look':'handDrawn','handDrawnSeed':123})
        result,measured,_,raw_input,raw_output=await self.actual(chart)
        self.assertEqual(len(result.nodes),9);self.assertEqual(len(result.edges),8)
        self.assertTrue(all(m.label_width==m.label_height==0 and m.lines==m.runs==() for m in measured))
        raw_nodes={n['id']:n for n in raw_output['children']}
        semantics={n['id']:chart.nodes[i].id for i,n in enumerate(raw_input['children'])}
        placed={n.id:n for n in result.nodes};first={}
        for raw_id,identifier in semantics.items():
            n=raw_nodes[raw_id]
            self.assertEqual(placed[identifier].box,Box(n['x'],n['y'],n['width'],n['height']))
        # Independent fixed-source rule, applied to raw engine anchors; never
        # call the candidate aligner to generate the expected paint position.
        for edge in raw_output['edges']:
            section=edge['sections'][0]
            for raw_id,anchor in ((edge['sources'][0],section['startPoint']),(edge['targets'][0],section['endPoint'])):
                identifier=semantics[raw_id];box=placed[identifier].box
                along_width=abs(anchor['y']-box.y)<=.5 or abs(anchor['y']-box.y-box.height)<=.5
                if (box.width if along_width else box.height)>=24 or identifier in first:continue
                first[identifier]=(anchor,along_width)
        for identifier,(anchor,along_width) in first.items():
            raw=placed[identifier].box;paint=placed[identifier].paint_box or raw
            self.assertEqual((paint.width,paint.height),(raw.width,raw.height))
            if along_width:
                self.assertAlmostEqual(paint.x+paint.width/2,anchor['x'])
                self.assertEqual(paint.y,raw.y)
            else:
                self.assertAlmostEqual(paint.y+paint.height/2,anchor['y'])
                self.assertEqual(paint.x,raw.x)
        self.assertIsNotNone(placed['N7'].paint_box,'2px anchor must follow real clamped ELK port')
        self.assertNotEqual(placed['N7'].paint_box,placed['N7'].box)
        for semantic,route in zip(chart.edges,result.edges):
            for identifier,point in ((semantic.source,route.paint_points[0]),(semantic.target,route.paint_points[-1])):
                if identifier not in first:continue
                anchor,along_width=first[identifier]
                if along_width:self.assertAlmostEqual(point.x,anchor['x'])
                else:self.assertAlmostEqual(point.y,anchor['y'])


class CorruptResultTests(unittest.IsolatedAsyncioTestCase):
    async def test_c01_layered_result_corruption_never_becomes_nonrouting_success(self):
        chart=diagram();session=CanvasSession('cpu');nodes=session.measure(chart)
        for fault in ('missing-sections','changed-fixed-width','unknown-id','nan-point','unknown-container'):
            calls=[];module=types.ModuleType('pyelk');module.__version__='0.1.0'
            class ControlledEngine:
                def __enter__(self):calls.append('enter');return self
                def __exit__(self,*args):calls.append('close')
                async def layout(self,graph):
                    result=copy.deepcopy(graph);result.update(width=700,height=200)
                    positions={node['id']:i for i,node in enumerate(result['children'])}
                    for node in result['children']:node.update(x=positions[node['id']]*200,y=50)
                    for edge in result['edges']:
                        source=next(n for n in result['children'] if n['id']==edge['sources'][0])
                        target=next(n for n in result['children'] if n['id']==edge['targets'][0])
                        edge['sections']=[{'startPoint':{'x':source['x']+source['width'],'y':70},'endPoint':{'x':target['x'],'y':70}}]
                    if fault=='missing-sections':result['edges'][0]['sections']=[]
                    elif fault=='changed-fixed-width':result['children'][0]['width']+=1
                    elif fault=='unknown-id':result['children'][0]['id']='not-an-input-id'
                    elif fault=='nan-point':result['edges'][0]['sections'][0]['startPoint']['x']=math.nan
                    elif fault=='unknown-container':result['edges'][0]['container']='not-a-container'
                    return result
            module.ELK=ControlledEngine
            with self.subTest(fault=fault),patch.dict(sys.modules,{'pyelk':module}),self.assertRaises(MermaidError) as error:
                await layout_flowchart(chart,nodes)
            self.assertEqual(error.exception.code,'INVALID_ELK_RESULT')
            self.assertEqual(calls[-1],'close')

    async def test_c02_bad_edge_contracts_reject_before_engine(self):
        chart=diagram();session=CanvasSession('cpu');nodes=session.measure(chart)
        from pyelk import ELK
        for changes in ({'marker_start':'triangle'},{'marker_end':'bad'},{'stroke':'unknown'},{'min_length':-1},{'min_length':True},{'min_length':math.inf}):
            with self.subTest(changes=changes),patch.object(ELK,'layout') as forbidden:
                with self.assertRaises(MermaidError) as error:
                    await layout_flowchart(replace(chart,edges=(replace(chart.edges[0],**changes),chart.edges[1])),nodes)
                self.assertEqual(error.exception.code,'INVALID_LAYOUT_INPUT')
                forbidden.assert_not_called()


def synthetic(routes,*,elk=None,markers=None,labels=()):
    """Independent raw-coordinate fixture, never an expected layout golden."""
    p=span();nodes=[];placed=[];edges=[];routed=[]
    for index,points in enumerate(routes):
        a,b='a'+str(index),'b'+str(index);start,end=points[0],points[-1]
        nodes.extend((FlowNode(a,a,p),FlowNode(b,b,p)))
        placed.extend((PlacedNode(a,Box(start.x-80,start.y-20,80,40)),PlacedNode(b,Box(end.x,end.y-20,80,40))))
        first,last=markers[index] if markers else ('none','none')
        text = 'Label' if any(label.id=='e'+str(index) for label in labels) else ''
        edges.append(FlowEdge('e'+str(index),a,b,p,label=text,marker_start=first,marker_end=last))
        section=EdgeSection(points[0],tuple(points[1:-1]),points[-1])
        routed.append(RoutedEdge('e'+str(index),(section,),tuple(points),'rounded'))
    cfg=resolve_config({'elk':elk or {'straightenEdges':False,'lineHops':False}})
    chart=Flowchart('independent synthetic path input','LR',tuple(nodes),tuple(edges),cfg)
    layout=FlowLayout(tuple(placed),tuple(routed),500,500,'synthetic-control','not-engine',edge_labels=tuple(labels))
    return chart,layout


class PaintGeometryTests(unittest.TestCase):
    def test_p01_point_marker_offsets_viewbox_and_independent_coordinates(self):
        points=(Point(0,0),Point(100,0))
        self.assertEqual(marker_offsets(points,'point','point'),(Point(4,0),Point(96,0)))
        values=edge_markers(points,'point','point');self.assertEqual(len(values),2)
        self.assertTrue(all(m.filled and m.stroke_width==.8 for m in values))
        for value,expected in zip(asdict(values[0].bounds).values(),(0,-4.4,8.8,8.8)):
            self.assertAlmostEqual(value,expected,places=8)
        self.assertAlmostEqual(values[1].bounds.x,91.6)
        self.assertAlmostEqual(values[1].bounds.x+values[1].bounds.width,100.4)

    def test_p02_circle_cross_use_no_path_pullback_and_native_marker_extents(self):
        points=(Point(0,0),Point(100,0))
        self.assertEqual(marker_offsets(points,'circle','cross'),points)
        circle=edge_markers(points,'none','circle')[0]
        self.assertTrue(circle.filled);self.assertAlmostEqual(circle.stroke_width,1.1)
        self.assertAlmostEqual(circle.bounds.x,87.35,places=5)
        self.assertAlmostEqual(circle.bounds.width,12.1,places=5)
        cross=edge_markers(points,'none','cross')[0]
        self.assertFalse(cross.filled);self.assertEqual(cross.stroke_width,2)
        self.assertEqual(cross.bounds,Box(88,-5.2,11,11))

    def test_p03_markers_all_terminal_directions_rotation_and_none(self):
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1)):
            with self.subTest(direction=(dx,dy)):
                length=math.hypot(dx,dy);points=(Point(20,30),Point(20+100*dx/length,30+100*dy/length))
                self.assertEqual(edge_markers(points,'none','none'),())
                for kind in ('point','circle','cross'):
                    markers=edge_markers(points,kind,kind)
                    self.assertEqual(len(markers),2)
                    self.assertTrue(markers[0].at_start);self.assertFalse(markers[1].at_start)
                    self.assertTrue(all(math.isfinite(v) for m in markers for v in (m.bounds.x,m.bounds.y,m.bounds.width,m.bounds.height)))
                    self.assertTrue(all(m.path for m in markers))

    def test_p04_rounded_corner_uses_radius5_angle_cut_and_no_input_mutation(self):
        points=(Point(0,0),Point(100,0),Point(100,100));before=copy.deepcopy(points)
        path=rounded_path(points);cut=5/math.sin(math.pi/4)
        values=[float(n) for n in re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?',path)]
        expected=(0,0,100-cut,0,100,0,100,cut,100,100)
        self.assertEqual(len(values),len(expected))
        for actual,value in zip(values,expected):self.assertAlmostEqual(actual,value,places=8)
        self.assertEqual(points,before)
        self.assertNotIn('Q',rounded_path((Point(0,0),Point(10,0),Point(20,0))))

    def test_p05_terminal_straightening_preserves_ports_and_moves_label_with_run(self):
        points=(Point(0,0),Point(10,0),Point(10,4),Point(60,4),Point(60,50),Point(100,50))
        chart,layout=synthetic((points,),elk={'straightenEdges':True,'lineHops':False},labels=(PlacedEdgeLabel('e0',Box(24,2,12,4)),))
        before=copy.deepcopy(layout);result=finish_edges(chart,layout,())
        self.assertEqual(result.edges[0].paint_points,(Point(0,0),Point(60,0),Point(60,50),Point(100,50)))
        self.assertEqual(result.edge_labels[0].box,Box(24,-2,12,4))
        self.assertEqual(result.edges[0].sections,layout.edges[0].sections)
        self.assertEqual(layout,before)
        off=finish_edges(replace(chart,config=resolve_config({'elk':{'straightenEdges':False,'lineHops':False}})),layout,())
        self.assertEqual(off.edges[0].paint_points,points)

    def test_p06_straightening_rejects_new_crossing_and_far_port_drag(self):
        points=(Point(0,0),Point(10,0),Point(10,4),Point(60,4),Point(60,50),Point(100,50))
        other=(Point(40,-2),Point(40,2))
        chart,layout=synthetic((points,other),elk={'straightenEdges':True,'lineHops':False})
        result=finish_edges(chart,layout,())
        self.assertEqual(result.edges[0].paint_points,points)
        short=(Point(0,0),Point(10,0),Point(10,4),Point(100,4))
        chart,layout=synthetic((short,),elk={'straightenEdges':True,'lineHops':False})
        self.assertEqual(finish_edges(chart,layout,()).edges[0].paint_points,short)

    def test_p07_hop_orientation_radius6_gap_and_disabled(self):
        horizontal=(Point(0,0),Point(100,0));vertical=(Point(50,-50),Point(50,50))
        routes=((horizontal,'linear'),(vertical,'linear'));markers=(('none','none'),('none','none'))
        arc=line_hop_paths(routes,markers,True)
        self.assertIn('L44,0',arc[0]);self.assertIn('A6,6 0 0 1 56,0',arc[0]);self.assertNotIn('A',arc[1])
        gap=line_hop_paths(routes,markers,'gap');self.assertNotIn('A',gap[0]);self.assertIn('M56,0',gap[0])
        disabled=line_hop_paths(routes,markers,False);self.assertFalse(any('A' in path for path in disabled))

    def test_p08_hops_exclude_shared_endpoints_corners_and_unreadable_close_pair(self):
        horizontal=(Point(0,0),Point(100,0));near=(Point(0,-20),Point(0,20))
        markers=(('none','none'),)*2
        self.assertFalse(any('A' in path for path in line_hop_paths(((horizontal,'linear'),(near,'linear')),markers,True)))
        close=((horizontal,'linear'),((Point(50,-20),Point(50,20)),'linear'),((Point(55,-20),Point(55,20)),'linear'))
        self.assertNotIn('A',line_hop_paths(close,(('none','none'),)*3,True)[0])
        corner=((Point(0,0),Point(50,0),Point(50,50)))
        crossing=(Point(48,-20),Point(48,20))
        self.assertFalse(any('A' in path for path in line_hop_paths(((corner,'rounded'),(crossing,'linear')),markers,True)))

    def test_p09_short_marker_stubs_removed_without_overwriting_raw_sections(self):
        points=(Point(0,0),Point(0,2),Point(40,2),Point(40,40),Point(100,40))
        chart,layout=synthetic((points,),markers=(('point','none'),))
        before=copy.deepcopy(layout.edges[0].sections)
        result=finish_edges(chart,layout,())
        self.assertNotIn(Point(0,2),result.edges[0].paint_points)
        self.assertEqual(result.edges[0].paint_points[0],Point(0,0))
        self.assertEqual(result.edges[0].sections,before)

    def test_p10_paint_bounds_cover_true_native_arc_and_marker_ink(self):
        from py_skia_canvas import Path2D
        first=(Point(0,0),Point(100,0));second=(Point(50,-50),Point(50,50))
        chart,layout=synthetic((first,second),elk={'lineHops':True,'straightenEdges':False},markers=(('circle','point'),('none','cross')))
        result=finish_edges(chart,layout,())
        self.assertLessEqual(result.edges[0].paint_bounds.y,-6)
        for semantic,edge in zip(chart.edges,result.edges):
            native=Path2D(edge.path).bounds
            self.assertTrue(contains(edge.paint_bounds,Box(native['left'],native['top'],native['width'],native['height']),.02))
            for marker in edge_markers(edge.paint_points,semantic.marker_start,semantic.marker_end):self.assertTrue(contains(edge.paint_bounds,marker.bounds,.02))

    def test_p11_source_curve_override_and_nonrouting_linear_are_explicit(self):
        points=(Point(0,0),Point(40,0),Point(40,40),Point(100,40));chart,layout=synthetic((points,))
        for declaration in ('basis','natural','step','cardinal','catmullRom','monotoneX','linear'):
            with self.subTest(curve=declaration):
                changed=replace(chart,edges=(replace(chart.edges[0],curve=declaration),))
                routed=finish_edges(changed,layout,()).edges[0]
                self.assertEqual(routed.effective_curve,'rounded');self.assertIn('Q',routed.path)
        linear=replace(layout,edges=(replace(layout.edges[0],sections=(),effective_curve='linear'),))
        self.assertNotIn('Q',finish_edges(chart,linear,()).edges[0].path)

    def test_p12_public_line_hops_config_gap_false_and_default(self):
        routes=((Point(0,0),Point(100,0)),(Point(50,-50),Point(50,50)))
        for setting,expected in (('gap','M56,0'),(True,'A6,6'),(False,None)):
            chart,layout=synthetic(routes,elk={'straightenEdges':False,'lineHops':setting})
            path=finish_edges(chart,layout,()).edges[0].path
            if expected:self.assertIn(expected,path)
            else:self.assertNotIn('A',path)

    def test_p13_degenerate_alignment_source_numbers_and_exact_twentyfour_threshold(self):
        p=span();cfg=resolve_config()
        chart=Flowchart('source prepass control','TD',(FlowNode('A','',p),FlowNode('B','',p)),(FlowEdge('e','A','B',p),),cfg)
        boxes={'A':Box(37,502,2,2),'B':Box(0,600,40,40)}
        route=RoutedEdge('e',(EdgeSection(Point(47,504),(),Point(47,600)),))
        original=copy.deepcopy((boxes,route))
        changed=align_degenerate_boxes(chart,(route,),boxes,('e',))
        self.assertEqual(changed,{'A':Box(46,502,2,2)})
        self.assertEqual((boxes,route),original)
        # Exactly24 is excluded, even when the port is far off-centre. A
        # left/right anchor spreads along height, not the width of that side.
        boxes={'A':Box(10,20,24,2),'B':Box(0,600,40,40)}
        self.assertEqual(align_degenerate_boxes(chart,(replace(route,sections=(EdgeSection(Point(100,20),(),Point(20,600)),)),),boxes,('e',)),{})
        left=replace(route,sections=(EdgeSection(Point(10,30),(),Point(20,600)),))
        self.assertEqual(align_degenerate_boxes(chart,(left,),boxes,('e',)),{'A':Box(10,29,24,2)})

    def test_p14_first_qualifying_anchor_wins_including_noop_and_group_has_no_skip(self):
        p=span();cfg=resolve_config()
        chart=Flowchart('first anchor control','TD',(FlowNode('A','',p),FlowNode('B','',p)),
          (FlowEdge('first','A','B',p),FlowEdge('second','A','B',p)),cfg)
        boxes={'A':Box(10,20,2,2),'B':Box(0,600,40,40)}
        first=RoutedEdge('first',(EdgeSection(Point(11,22),(),Point(20,600)),))
        second=RoutedEdge('second',(EdgeSection(Point(12,20),(),Point(20,600)),))
        self.assertEqual(align_degenerate_boxes(chart,(first,second),boxes,('first','second')),{})
        self.assertEqual(align_degenerate_boxes(chart,(first,second),boxes,('second','first')),{'A':Box(11,20,2,2)})
        child=Box(80,80,10,10)
        grouped=replace(chart,nodes=(chart.nodes[1],FlowNode('child','',p,parent_id='A')),groups=(FlowGroup('A','',p,('child',)),))
        self.assertEqual(align_degenerate_boxes(grouped,(first,second),dict(boxes,child=child),('second','first')),{'A':Box(11,20,2,2)})
        excluded=replace(chart,nodes=(replace(chart.nodes[0],shape='rect33'),chart.nodes[1]))
        self.assertEqual(align_degenerate_boxes(excluded,(first,second),boxes,('second','first')),{})

    def test_p15_geometry_bounds_uses_source_paint_box_not_unpainted_raw_position(self):
        from py_mermaid.geometry import geometry_bounds
        node=PlacedNode('A',Box(0,0,2,2),paint_box=Box(9,0,2,2))
        layout=FlowLayout((node,),(),30,30,'test','test')
        self.assertEqual(geometry_bounds(layout,include_engine=False),Box(9,0,2,2))


if __name__=='__main__':unittest.main()
