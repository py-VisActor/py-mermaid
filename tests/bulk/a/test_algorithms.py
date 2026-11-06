"""Source algorithm geometry, arithmetic and safety contracts; deferred until P3."""
from __future__ import annotations
import unittest
import math
from py_mermaid.diagrams.hierarchy._cose_tree import layout as cose_layout
from py_mermaid.diagrams.hierarchy._tidy import layout as tidy_layout
from py_mermaid.diagrams.structures._fcose import simulate,SeededRandom
from py_mermaid.model.flowchart import MermaidError


def center(box):return box.x+box.width/2,box.y+box.height/2

def disjoint(a,b,tolerance=.5):
    return min(a.x+a.width,b.x+b.width)-max(a.x,b.x)<=tolerance or min(a.y+a.height,b.y+b.height)-max(a.y,b.y)<=tolerance


class CoSESourceTests(unittest.IsolatedAsyncioTestCase):
    # cose-bilkent/layout.test.ts validation + flat forest's actual FD geometry.
    async def test_single_node_preserves_measured_dimensions(self):
        result=await cose_layout([{'id':'root','width':83,'height':29}],[],config={'_diagramConfigKey':'mindmap'})
        self.assertEqual(result.nodes['root'].width,83);self.assertEqual(result.nodes['root'].height,29);self.assertEqual(set(result.nodes),{'root'});self.assertEqual(len(result.edges),0)
    async def test_root_context_required_not_generic_force_fallback(self):
        with self.assertRaises(MermaidError) as caught:await cose_layout([{'id':'A','width':40,'height':20}],[],config={'_diagramConfigKey':'class'})
        self.assertEqual(caught.exception.code,'INVALID_LAYOUT_DATA')
    async def test_tree_has_no_overlapping_real_leaf_boxes(self):
        nodes=[{'id':str(i),'width':80+i*8,'height':30+i*3} for i in range(6)];edges=[{'id':'e'+str(i),'source':'0','target':str(i)} for i in range(1,6)]
        result=await cose_layout(nodes,edges,config={'_diagramConfigKey':'mindmap'})
        self.assertEqual(set(result.nodes),set(str(i) for i in range(6)));self.assertEqual(set(result.edges),set('e'+str(i) for i in range(1,6)))
        for i,a in enumerate(nodes):
            box=result.nodes[a['id']];self.assertEqual((box.width,box.height),(a['width'],a['height']))
            for b in nodes[i+1:]:self.assertTrue(disjoint(box,result.nodes[b['id']]),(a['id'],b['id']))
        for route in result.edges.values():
            self.assertGreaterEqual(len(route),2);self.assertTrue(all(math.isfinite(v) for p in route for v in (p.x,p.y)))
    async def test_forest_components_keep_all_nodes(self):
        nodes=[{'id':id,'width':60,'height':30} for id in ('A','B','C','D')];edges=[{'id':'AB','source':'A','target':'B'},{'id':'CD','source':'C','target':'D'}]
        result=await cose_layout(nodes,edges,config={'_diagramConfigKey':'mindmap'})
        self.assertEqual(len(result.nodes),4);self.assertTrue(disjoint(result.nodes['A'],result.nodes['C']));self.assertEqual(len(result.edges),2)
    async def test_source_radial_tree_is_repeatable_without_global_state(self):
        nodes=[{'id':id,'width':70,'height':25} for id in ('A','B','C')];edges=[{'id':'AB','source':'A','target':'B'},{'id':'BC','source':'B','target':'C'}]
        a=await cose_layout(nodes,edges,config={'_diagramConfigKey':'mindmap'});b=await cose_layout(nodes,edges,config={'_diagramConfigKey':'mindmap'})
        self.assertEqual(tuple(a.nodes.items()),tuple(b.nodes.items()));self.assertEqual(tuple(a.edges.items()),tuple(b.edges.items()))
    async def test_cycle_is_explicit_error_not_infinite_radial_recursion(self):
        nodes=[{'id':id,'width':40,'height':20} for id in ('A','B','C')];edges=[{'id':a+b,'source':a,'target':b} for a,b in (('A','B'),('B','C'),('C','A'))]
        with self.assertRaises(MermaidError) as caught:await cose_layout(nodes,edges,config={'_diagramConfigKey':'mindmap'})
        self.assertEqual(caught.exception.code,'INVALID_LAYOUT_DATA')


class TidySourceTests(unittest.IsolatedAsyncioTestCase):
    # Original package layout.test.ts first/third children left, second/fourth right.
    async def test_alternating_root_children_are_on_source_sides(self):
        nodes=[{'id':id,'width':100,'height':50} for id in ('root','one','two','three','four')];edges=[{'id':id,'source':'root','target':id} for id in ('one','two','three','four')];r=await tidy_layout(nodes,edges);rx,ry=center(r.nodes['root'])
        for id in ('one','three'):self.assertLess(center(r.nodes[id])[0],rx-100)
        for id in ('two','four'):self.assertGreater(center(r.nodes[id])[0],rx+100)
        self.assertEqual(r.nodes['root'].width,100);self.assertEqual(r.nodes['root'].height,50)
    async def test_tall_siblings_preserve_clearance(self):
        nodes=[{'id':'root','width':90,'height':40},{'id':'A','width':100,'height':180},{'id':'B','width':90,'height':45},{'id':'C','width':100,'height':210}];edges=[{'id':id,'source':'root','target':id} for id in ('A','B','C')];r=await tidy_layout(nodes,edges)
        self.assertTrue(disjoint(r.nodes['A'],r.nodes['C']));self.assertGreaterEqual(r.nodes['C'].y-r.nodes['A'].y-r.nodes['A'].height,19.9)
    async def test_descendants_follow_their_parent_side(self):
        nodes=[{'id':id,'width':80,'height':35} for id in ('R','A','B','AA','BB')];edges=[{'id':a+b,'source':a,'target':b} for a,b in (('R','A'),('R','B'),('A','AA'),('B','BB'))];r=await tidy_layout(nodes,edges)
        self.assertLess(center(r.nodes['AA'])[0],center(r.nodes['A'])[0]);self.assertGreater(center(r.nodes['BB'])[0],center(r.nodes['B'])[0]);self.assertEqual(len(r.edges),4)
    async def test_tidy_edges_use_boundary_points_not_node_centers(self):
        r=await tidy_layout([{'id':'R','width':100,'height':60},{'id':'A','width':80,'height':40}],[{'id':'edge','source':'R','target':'A'}]);path=r.edges['edge']
        self.assertGreaterEqual(len(path),3)
        for at,id in ((path[0],'R'),(path[-1],'A')):
            b=r.nodes[id];self.assertTrue(abs(at.x-b.x)<1e-6 or abs(at.x-b.x-b.width)<1e-6 or abs(at.y-b.y)<1e-6 or abs(at.y-b.y-b.height)<1e-6)
    async def test_empty_source_adapter_rejects(self):
        with self.assertRaises(MermaidError) as caught:await tidy_layout([],[])
        self.assertEqual(caught.exception.code,'INVALID_LAYOUT_DATA')


class ArchitectureFcoseSourceTests(unittest.TestCase):
    # Fixed architectureSeed.ts mulberry32 independent published seed=1 vectors.
    def test_mulberry_seed_one_arithmetic(self):
        rng=SeededRandom(1);actual=[rng() for _ in range(5)]
        self.assertEqual(actual,[0.6270739405881613,0.002735721180215478,0.5274470399599522,0.9810509674716741,0.9683778982143849])
    def test_seed_state_is_request_local(self):
        a,b=SeededRandom(9),SeededRandom(9);self.assertEqual(a(),b());a();c=SeededRandom(9);self.assertEqual(b(),(c(),c())[1])
    def test_horizontal_relative_constraint_and_alignment(self):
        nodes=[{'id':id,'width':80,'height':80} for id in ('A','B','C')];edges=[{'source':'A','target':'B'},{'source':'B','target':'C'}];r,_=simulate(nodes,[],edges,horizontal=(('A','B','C'),),relative=((0,'A','B',120),(0,'B','C',120)),config={'seed':1,'numIter':2500})
        ax,ay=center(r['A']);bx,by=center(r['B']);cx,cy=center(r['C']);self.assertAlmostEqual(ay,by);self.assertAlmostEqual(by,cy);self.assertGreaterEqual(bx-ax,120-1e-6);self.assertGreaterEqual(cx-bx,120-1e-6)
        self.assertTrue(disjoint(r['A'],r['B']));self.assertTrue(disjoint(r['B'],r['C']))
    def test_vertical_relative_constraint_and_alignment(self):
        nodes=[{'id':id,'width':80,'height':80} for id in ('A','B')];r,_=simulate(nodes,[],[{'source':'A','target':'B'}],vertical=(('A','B'),),relative=((1,'A','B',120),),config={'seed':3})
        ax,ay=center(r['A']);bx,by=center(r['B']);self.assertAlmostEqual(ax,bx);self.assertGreaterEqual(by-ay,120-1e-6)
    def test_nested_compounds_contain_actual_children(self):
        nodes=[{'id':'A','parent':'inner','width':80,'height':80},{'id':'B','parent':'outer','width':80,'height':80}];r,g=simulate(nodes,[{'id':'outer'},{'id':'inner','parent':'outer'}],[{'source':'A','target':'B'}],config={'seed':1,'padding':40})
        for parent,child in ((g['inner'],r['A']),(g['outer'],g['inner']),(g['outer'],r['B'])):
            self.assertLessEqual(parent.x+39.9,child.x);self.assertLessEqual(parent.y+39.9,child.y);self.assertGreaterEqual(parent.x+parent.width-39.9,child.x+child.width);self.assertGreaterEqual(parent.y+parent.height-39.9,child.y+child.height)
    def test_same_seed_spectral_input_is_repeatable(self):
        nodes=[{'id':id,'width':80,'height':80} for id in ('A','B','C','D')];edges=[{'source':a,'target':b} for a,b in (('A','B'),('B','C'),('C','D'),('D','A'))];cfg={'randomize':True,'seed':7,'nodeSeparation':75};a,_=simulate(nodes,[],edges,config=cfg);b,_=simulate(nodes,[],edges,config=cfg)
        self.assertEqual(a,b)
        for i,id in enumerate(a):
            for other in tuple(a)[i+1:]:self.assertTrue(disjoint(a[id],a[other]),(id,other))
    def test_conflicting_relative_cycle_reports_layout_error(self):
        nodes=[{'id':id,'width':80,'height':80} for id in ('A','B')]
        with self.assertRaises(MermaidError) as caught:simulate(nodes,[],[],relative=((0,'A','B',120),(0,'B','A',120)),config={'seed':1})
        self.assertEqual(caught.exception.code,'UNSATISFIABLE_LAYOUT')
    def test_alignment_cannot_share_positive_relative_axis(self):
        nodes=[{'id':id,'width':80,'height':80} for id in ('A','B')]
        with self.assertRaises(MermaidError) as caught:simulate(nodes,[],[],vertical=(('A','B'),),relative=((0,'A','B',120),),config={'seed':1})
        self.assertEqual(caught.exception.code,'UNSATISFIABLE_LAYOUT')
    def test_isolated_source_nodes_are_tiled_without_loss_or_overlap(self):
        nodes=[{'id':str(i),'width':80,'height':80} for i in range(5)];r,_=simulate(nodes,[],[],config={'seed':1})
        self.assertEqual(set(r),set(str(i) for i in range(5)))
        for i,a in enumerate(r):
            for b in tuple(r)[i+1:]:self.assertTrue(disjoint(r[a],r[b]))
