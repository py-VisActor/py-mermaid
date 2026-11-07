"""Actual engine/topology branches; P2 defines but does not execute them."""
import copy
import math
import unittest
from unittest.mock import patch

from py_mermaid import parse,arender
from support_b import get_case,document,scene


class CompoundBranchContracts(unittest.IsolatedAsyncioTestCase):
    def test_b16_hidden_authored_selfloop_survives_agent_collapse(self):
        d=parse(get_case('AGENT-GENUINE')['source']).model.graph
        self.assertEqual([n.id for n in d.nodes],['Outer'])
        self.assertEqual([(e.source,e.target) for e in d.edges],[('Outer','Outer')])

    def test_b17_distinct_internal_endpoints_collapse_to_no_edge(self):
        d=parse(get_case('AGENT-INTERNAL')['source']).model.graph
        self.assertEqual([n.id for n in d.nodes],['Outer']);self.assertEqual(d.edges,())

    def test_b18_nested_collapse_redirects_to_outermost_visible_node(self):
        d=parse(get_case('AGENT-NESTED')['source']).model.graph
        self.assertEqual({n.id for n in d.nodes},{'Outer','X','Y'})
        self.assertEqual([(e.source,e.target) for e in d.edges],[('X','Outer'),('Outer','Y')])

    async def test_b19_ancestor_edges_keep_all_route_identities(self):
        d,s=await scene(get_case('AGENT-ANCESTOR'));g=d.model.graph
        self.assertEqual({e.id for e in s.layout.edges},{e.id for e in g.edges})
        self.assertEqual(len(s.layout.edges),3)
        self.assertEqual({p.id for p in s.layout.groups},{'Outer','Inner'})

    async def test_b20_cross_hierarchy_clears_only_isolated_algorithm(self):
        from pyelk import ELK
        original=ELK.layout;inputs=[]
        async def capture(engine,graph,args=None):
            inputs.append(copy.deepcopy(graph));return await original(engine,graph,args)
        with patch.object(ELK,'layout',capture):
            d,s=await scene(get_case('AGENT-CROSS-ALGO'))
        self.assertEqual(len(inputs),1)
        def groups(node):
            for child in node.get('children',[]):
                if child.get('children'):yield child
                yield from groups(child)
        custom=list(groups(inputs[0]));self.assertTrue(custom)
        self.assertTrue(all(c['layoutOptions'].get('elk.algorithm')!='elk.box' for c in custom))
        self.assertEqual({e.id for e in s.layout.edges},{e.id for e in d.model.graph.edges})

    async def test_b21_isolated_group_algorithm_stays_requested(self):
        from pyelk import ELK
        original=ELK.layout;inputs=[]
        async def capture(engine,graph,args=None):
            inputs.append(copy.deepcopy(graph));return await original(engine,graph,args)
        with patch.object(ELK,'layout',capture):await scene(get_case('AGENT-GROUP-ALGO'))
        def collect(node):
            yield node
            for child in node.get('children',[]):yield from collect(child)
        self.assertTrue(any(n.get('layoutOptions',{}).get('elk.algorithm')=='elk.box' for n in collect(inputs[0])))


class DedicatedNumericLayouts(unittest.IsolatedAsyncioTestCase):
    async def test_b22_dense_git_routes_and_direction_across_rotation(self):
        for c in document()['cases']:
            if not c['id'].startswith('BV-B-GIT-'):continue
            with self.subTest(case=c['id']):
                d,s=await scene(c);model=d.model
                expected=sum(len(commit.parents) for commit in model.commits)
                routes=[p for p in s.commands if p.role=='edge']
                self.assertEqual(expected,9);self.assertEqual(len(routes),expected)
                positions={id:(x,y) for id,x,y in s.layout['commits']}
                axis=0 if model.direction=='LR' else 1;sign=-1 if model.direction=='BT' else 1
                for commit in model.commits:
                    for parent in commit.parents:self.assertGreater(sign*(positions[commit.id][axis]-positions[parent][axis]),0)
                self.assertTrue(all(math.isfinite(v) for xy in positions.values() for v in xy))

    async def test_b23_multiple_tags_preserve_reverse_display_stack(self):
        _,s=await scene(get_case('GIT-LR-FLAT'))
        labels={p.semantic_id:p.values[0].text for p in s.commands if p.kind=='text'}
        self.assertEqual([labels['A-tag-'+str(i)] for i in range(3)],['last','long-release','first'])
        self.assertTrue(all('A-tag-bg-'+str(i) in {p.semantic_id for p in s.commands} for i in range(3)))

    async def test_b24_nonlayered_algorithms_use_real_requested_engine_once(self):
        from pyelk import ELK
        original=ELK.layout
        for c in document()['cases']:
            if not c['id'].startswith('BV-B-ENGINE-'):continue
            inputs=[]
            async def capture(engine,graph,args=None):
                inputs.append(copy.deepcopy(graph));return await original(engine,graph,args)
            with self.subTest(case=c['id']):
                with patch.object(ELK,'layout',capture):r=await arender(c['source'],config=c['config'],backend='cpu')
                requested=c['config']['layout']
                self.assertEqual(len(inputs),1);self.assertEqual(inputs[0]['layoutOptions']['elk.algorithm'],requested)
                self.assertEqual(r.layout.engine,'pyelk/'+requested)
                self.assertEqual(r.layout.engine_version,'0.1.0')
                self.assertEqual({p.id for p in r.layout.nodes},{n.id for n in r.diagram.nodes})
                self.assertEqual({e.id for e in r.layout.edges},{e.id for e in r.diagram.edges})
                self.assertTrue(all(math.isfinite(v) for n in r.layout.nodes for v in (n.box.x,n.box.y,n.box.width,n.box.height)))

    def test_b25_repeated_wardley_annotation_number_is_not_merged(self):
        d=parse(get_case('WARDLEY-ANNOTATION-PUSH')['source']).model
        self.assertEqual(d.annotations,((1,30,20,'First'),(1,70,80,'Second')))
