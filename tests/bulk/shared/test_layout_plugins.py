"""Native extensibility and lifecycle adapters; source registry order is preserved."""
import asyncio
from dataclasses import replace
import unittest
from py_mermaid import MermaidError
from py_mermaid.model.flowchart import Box,Point
from py_mermaid.runtime.graph import GraphLayout,FrozenLookup,layout_graph
from py_mermaid.runtime import layouts


class LayoutAdapterContracts(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):self.saved=layouts._providers.copy()
    async def asyncTearDown(self):layouts._providers.clear();layouts._providers.update(self.saved)

    async def test_custom_provider_receives_exact_measured_values_and_no_shadow_layout(self):
        seen={}
        nodes=({'id':'a','width':17,'height':23},);edges=()
        expected=GraphLayout(FrozenLookup((('a',Box(3,5,17,23)),)),FrozenLookup(()),FrozenLookup(()),FrozenLookup(()),23,31,'fixture-native','1')
        async def provider(n,e,**kw):seen.update(nodes=n,edges=e,kwargs=kw);return expected
        layouts.register_layout('fixture-native',provider,algorithm='fixture-native.algorithm')
        result=await layout_graph(nodes,edges,direction='LR',node_spacing=11,rank_spacing=29,config={'layout':'fixture-native'})
        self.assertIs(result,expected);self.assertEqual(seen['nodes'],nodes)
        self.assertEqual(seen['kwargs']['direction'],'LR');self.assertEqual(seen['kwargs']['node_spacing'],11)
        self.assertEqual(seen['kwargs']['rank_spacing'],29);self.assertEqual(seen['kwargs']['algorithm'],'fixture-native.algorithm')

    async def test_provider_failure_and_invalid_result_are_not_elk_fallback(self):
        async def failure(*a,**kw):raise RuntimeError('intentional-provider-failure')
        layouts.register_layout('fixture-error',failure)
        with self.assertRaisesRegex(RuntimeError,'intentional-provider-failure'):
            await layout_graph((),(),algorithm='fixture-error')
        async def wrong(*a,**kw):return {'success':True}
        layouts.register_layout('fixture-invalid',wrong)
        with self.assertRaises(MermaidError) as caught:await layout_graph((),(),algorithm='fixture-invalid')
        self.assertEqual(caught.exception.code,'INVALID_LAYOUT')

    async def test_cancellation_propagates_to_active_provider_finally(self):
        started=asyncio.Event();released=[]
        async def provider(*a,**kw):
            started.set()
            try:await asyncio.Future()
            finally:released.append(True)
        layouts.register_layout('fixture-cancel',provider)
        task=asyncio.create_task(layout_graph((),(),algorithm='fixture-cancel'))
        await started.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(released,[True])

    async def test_builtin_elk_graph_hierarchy_edge_identity_and_finite_routes(self):
        import math
        nodes=({'id':'__py_mermaid_root__','width':80,'height':35,'parent':'group'},
               {'id':'other','width':55,'height':28})
        edges=({'id':'edge','source':'__py_mermaid_root__','target':'other','label_width':30,'label_height':15},)
        graph=await layout_graph(nodes,edges,parents=({'id':'group','padding':12,'title_height':20},),direction='LR')
        self.assertEqual(set(graph.nodes),{'__py_mermaid_root__','other'})
        self.assertEqual(set(graph.groups),{'group'});self.assertEqual(set(graph.edges),{'edge'})
        b=graph.nodes['__py_mermaid_root__'];g=graph.groups['group']
        self.assertGreaterEqual(b.x,g.x);self.assertGreaterEqual(b.y,g.y)
        self.assertLessEqual(b.x+b.width,g.x+g.width);self.assertLessEqual(b.y+b.height,g.y+g.height)
        self.assertGreater(len(graph.edges['edge']),1)
        self.assertTrue(all(math.isfinite(v) for pt in graph.edges['edge'] for v in (pt.x,pt.y)))
        self.assertIn('edge',graph.edge_paths)


if __name__=='__main__':unittest.main()
