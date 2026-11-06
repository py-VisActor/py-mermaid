"""Independent fixed-source numeric tables and routing quality constraints.

Expected geometry is literal source-spec data or elementary rectangle/segment
math below. No production helper computes an expected route or intersection.
"""
import copy
import math
import unittest


def p(x,y):return dict(x=x,y=y)
def node(id,x,y,width=100,height=80,**kwargs):return dict(id=id,x=x,y=y,width=width,height=height,isGroup=False,**kwargs)
def edge(id,start,end,points=None,**kwargs):return dict(id=id,start=start,end=end,**({'points':points} if points is not None else {}),**kwargs)


def on_border(point,n,tolerance=1e-6):
    x,y,w,h=n['x'],n['y'],n['width']/2,n['height']/2
    return ((abs(point['x']-(x-w))<tolerance or abs(point['x']-(x+w))<tolerance) and y-h-tolerance<=point['y']<=y+h+tolerance) or ((abs(point['y']-(y-h))<tolerance or abs(point['y']-(y+h))<tolerance) and x-w-tolerance<=point['x']<=x+w+tolerance)


def crosses_interior(a,b,c,d):
    # Independent determinant intersection with strict interior parameters.
    ux,uy=b['x']-a['x'],b['y']-a['y'];vx,vy=d['x']-c['x'],d['y']-c['y'];det=ux*vy-uy*vx
    if abs(det)<1e-9:return False
    dx,dy=c['x']-a['x'],c['y']-a['y'];t=(dx*vy-dy*vx)/det;u=(dx*uy-dy*ux)/det
    return 1e-6<t<1-1e-6 and 1e-6<u<1-1e-6


def count_crossings(edges):
    return sum(crosses_interior(a,b,c,d) for i,e in enumerate(edges) for other in edges[i+1:] for a,b in zip(e.get('points',[]),e.get('points',[])[1:]) for c,d in zip(other.get('points',[]),other.get('points',[])[1:]))


class GeometrySourceCases(unittest.TestCase):
    def test_crossing_source_spec_strict_t_shared_collinear_and_diagonal(self):
        from py_mermaid.diagrams.business._swimlane_routing.geometry import orthogonal_segments_cross,strictly_cross
        cases=[((-10,0),(10,0),(0,-10),(0,10),True,True),((-10,0),(10,0),(0,0),(0,10),True,False),((-10,0),(0,0),(0,0),(0,10),False,False),((-10,0),(10,0),(-5,0),(5,0),False,False),((-10,0),(10,10),(0,-10),(0,10),False,False),((-10,0),(10,0),(9.9995,-10),(9.9995,10),True,False)]
        for a,b,c,d,loose,strict in cases:
            with self.subTest(points=(a,b,c,d)):
                self.assertEqual(orthogonal_segments_cross(p(*a),p(*b),p(*c),p(*d)),loose)
                self.assertEqual(strictly_cross(p(*a),p(*b),p(*c),p(*d)),strict)

    def test_caller_epsilon_is_not_ignored(self):
        from py_mermaid.diagrams.business._swimlane_routing.geometry import orthogonal_segments_cross
        self.assertFalse(orthogonal_segments_cross(p(-10,0),p(10,.00001),p(0,-10),p(0,10),1e-6))

    def test_real_bounds_exclude_group_label_and_zero_width(self):
        from py_mermaid.diagrams.business._swimlane_routing.geometry import collect_real_node_bounds
        nodes=[node('A',10,20,40,20),dict(node('g',10,20,40,20),isGroup=True),node('label',10,20,40,20,isEdgeLabel=True),node('empty',10,20,0,20)]
        infos,rects=collect_real_node_bounds(nodes)
        self.assertEqual(list(infos),['A']);self.assertEqual(rects,[{'id':'A','rect':{'left':-10,'right':30,'top':10,'bottom':30}}])

    def test_segment_rect_exclusions_and_shrink_source_spec(self):
        from py_mermaid.diagrams.business._swimlane_routing.geometry import segment_hits_any_rect
        rects=[dict(id='A',rect=dict(left=0,right=10,top=0,bottom=10))]
        self.assertTrue(segment_hits_any_rect(p(-5,5),p(15,5),rects))
        self.assertFalse(segment_hits_any_rect(p(-5,5),p(15,5),rects,['A']))
        self.assertFalse(segment_hits_any_rect(p(-5,.5),p(15,.5),rects,[],1))

    def test_hvh_vhv_and_diagonal_rejection(self):
        from py_mermaid.diagrams.business._swimlane_routing.geometry import classify_three_segment_route
        for points,kind in [([p(0,0),p(10,0),p(10,20),p(30,20)],'HVH'),([p(0,0),p(0,10),p(20,10),p(20,30)],'VHV')]:self.assertEqual(classify_three_segment_route(points)['kind'],kind)
        self.assertIsNone(classify_three_segment_route([p(0,0),p(10,10),p(20,10),p(20,30)]))

    def test_overlap_touch_and_parallel_gap(self):
        from py_mermaid.diagrams.business._swimlane_routing.geometry import same_axis_segments_overlap
        self.assertTrue(same_axis_segments_overlap(p(0,0),p(10,0),p(5,0),p(15,0)))
        self.assertFalse(same_axis_segments_overlap(p(0,0),p(10,0),p(10,0),p(15,0)))
        self.assertFalse(same_axis_segments_overlap(p(0,0),p(10,0),p(5,1),p(15,1)))

    def test_simplification_removes_backtrack_and_collinear_only(self):
        from py_mermaid.diagrams.business._swimlane_routing.geometry import simplify,orthogonalize
        self.assertEqual(simplify([p(0,0),p(5,0),p(10,0),p(10,10)]),[p(0,0),p(10,0),p(10,10)])
        self.assertEqual(simplify([p(0,0),p(10,0),p(0,0),p(0,10)]),[p(0,0),p(0,10)])
        self.assertEqual(orthogonalize([p(0,0),p(10,20)]),[p(0,0),p(10,0),p(10,20)])

    def test_port_path_source_side_matrix_and_rejected_reverse(self):
        from py_mermaid.diagrams.business._swimlane_routing.geometry import build_port_path
        self.assertEqual(build_port_path(p(0,0),'right',p(100,40),'left',20),[p(0,0),p(50,0),p(50,40),p(100,40)])
        self.assertEqual(build_port_path(p(0,0),'left',p(100,40),'left',20),[p(0,0),p(-20,0),p(-20,40),p(100,40)])
        self.assertEqual(build_port_path(p(0,0),'bottom',p(100,100),'top',20),[p(0,0),p(0,50),p(100,50),p(100,100)])
        self.assertIsNone(build_port_path(p(0,0),'left',p(100,40),'right',20))


class DirectionAndEndpointCases(unittest.TestCase):
    def test_bt_mirrors_centers_points_and_title_rect(self):
        from py_mermaid.diagrams.business._swimlane_routing.direction import apply_bt
        a,b=node('A',150,100),node('B',150,300);g=dict(node('G',150,200,200,400),isGroup=True,groupTitleRect=dict(left=50,right=250,top=0,bottom=36))
        data={'nodes':[a,b,g],'edges':[edge('e','A','B',[p(150,140),p(150,260)])]}
        self.assertTrue(apply_bt(data));self.assertEqual((a['y'],b['y']),(300,100));self.assertEqual(data['edges'][0]['points'],[p(150,260),p(150,140)])
        self.assertEqual(g['groupTitleRect'],dict(left=50,right=250,top=364,bottom=400))

    def test_lr_and_rl_scale_progression_but_preserve_node_dimensions(self):
        from py_mermaid.diagrams.business._swimlane_routing.direction import apply_lr
        for direction,expected in [('LR',(36,286)),('RL',(286,36))]:
            with self.subTest(direction=direction):
                a,b=node('A',150,100),node('B',150,300);data=dict(nodes=[a,b],edges=[])
                self.assertTrue(apply_lr(data,direction));self.assertEqual((a['x'],b['x']),expected);self.assertEqual((a['y'],b['y']),(0,0))
                self.assertEqual((a['width'],a['height'],b['width'],b['height']),(100,80,100,80))

    def test_lr_lane_header_is_vertical_and_contains_children(self):
        from py_mermaid.diagrams.business._swimlane_routing.direction import apply_lr
        g=dict(node('Lane',150,200,200,400),isGroup=True,padding=20);a=node('A',150,100,parentId='Lane');b=node('B',150,300,parentId='Lane')
        self.assertTrue(apply_lr(dict(nodes=[g,a,b],edges=[]),'LR'))
        r=g['groupTitleRect'];self.assertEqual(r['right']-r['left'],36)
        self.assertGreater(r['bottom']-r['top'],36)
        self.assertLessEqual(g['x']-g['width']/2,a['x']-a['width']/2)
        self.assertGreaterEqual(g['x']+g['width']/2,b['x']+b['width']/2)

    def test_clip_inside_runs_to_actual_rect_boundaries(self):
        from py_mermaid.diagrams.business._swimlane_routing.endpoint_clip import clip_endpoints
        nodes={'A':node('A',0,0,40,40),'B':node('B',100,0,40,40)};e=edge('e','A','B',[p(0,0),p(10,0),p(50,0),p(90,0),p(100,0)])
        clip_endpoints([e],nodes);self.assertEqual(e['points'],[p(20,0),p(80,0)])

    def test_renderer_handoff_duplicates_only_nonstraight_terminals_idempotently(self):
        from py_mermaid.diagrams.business._swimlane_routing.endpoint_clip import prepare_endpoints
        e=edge('e','A','B',[p(20,0),p(60,0),p(60,100),p(80,100)]);nodes={'A':node('A',0,0,40,40),'B':node('B',100,100,40,40)}
        prepare_endpoints([e],nodes);expected=[p(20,0),p(20,0),p(60,0),p(60,100),p(80,100),p(80,100)]
        self.assertEqual(e['points'],expected);prepare_endpoints([e],nodes);self.assertEqual(e['points'],expected)

    def test_short_straight_corners_shift_inside_four_pixel_clearance(self):
        from py_mermaid.diagrams.business._swimlane_routing.endpoint_clip import prepare_endpoints
        e=edge('e','A','B',[p(20,19),p(80,19)]);nodes={'A':node('A',0,0,40,40),'B':node('B',100,0,40,40)}
        prepare_endpoints([e],nodes);self.assertEqual(e['points'],[p(20,16),p(80,16)])

    def test_label_anchors_to_middle_segment_and_reparents_into_lane(self):
        from py_mermaid.diagrams.business._swimlane_routing.label_anchoring import anchor_labels
        nodes={'L':dict(node('L',150,100,400,300),isGroup=True),'A':node('A',0,100,20,20),'B':node('B',300,200,20,20),'label':node('label',999,999,40,20,isEdgeLabel=True,parentId='wrong')}
        e=edge('e','A','B',[p(10,100),p(100,100),p(100,200),p(290,200)],labelNodeId='label')
        anchor_labels([e],nodes);self.assertEqual((nodes['label']['x'],nodes['label']['y'],nodes['label']['parentId']),(100,150,'L'))


class PostprocessSourceCases(unittest.TestCase):
    def test_source_shared_terminal_face_exact_and_near_sixteen_spacing(self):
        from py_mermaid.diagrams.business._swimlane_routing.materialized import separate_terminal_lanes
        nodes={'A':node('A',-40,-30,10,10),'B':node('B',0,0,10,80)}
        edges=[edge('one','A','B',[p(-30,0),p(-5,0)]),edge('two','A','B',[p(-30,0),p(-5,0)])]
        separate_terminal_lanes(edges,nodes);ys=sorted(e['points'][-1]['y'] for e in edges)
        self.assertNotEqual(ys[0],ys[1]);self.assertIn(0,ys)
        nodes={'A':node('A',-40,-30,10,10),'B':node('B',0,0,10,60),'C':node('C',-40,30,10,10)}
        edges=[edge('ab','A','B',[p(-90,-4),p(-5,-4)]),edge('bc','B','C',[p(-5,4),p(-90,4)])]
        separate_terminal_lanes(edges,nodes)
        self.assertGreaterEqual(abs(edges[0]['points'][-1]['y']-edges[1]['points'][0]['y']),16)

    def test_source_obstacle_hugging_rail_exact_twenty_clearance(self):
        from py_mermaid.diagrams.business._swimlane_routing.materialized import lift_hugging_rails
        nodes={'26':node('26',-166,54,232,66),'27':node('27',830,54,232,66),'28':node('28',166,54,232,108)}
        e=edge('e','26','27',[p(-166,21),p(-166,1),p(830,1),p(830,21)])
        lift_hugging_rails([e],nodes)
        self.assertEqual(e['points'],[p(-166,21),p(-166,-20),p(830,-20),p(830,21)])

    def test_source_destination_pair_transaction_removes_crossing(self):
        from py_mermaid.diagrams.business._swimlane_routing.materialized import swap_destination_tails
        top=p(297.553125,1171.1287841796875);right=p(318.890625,1196.6287841796875)
        nodes={'C':node('C',292.21875,287.5,150.05624389648438,91),'D':node('D',292.21875,570.5,94.11250305175781,91),'exit':node('exit',292.21875,1196.6287841796875,53.34375,51)}
        edges=[edge('c','C','exit',[p(367.2468719482422,287.5),p(387.2468719482422,287.5),p(387.2468719482422,1151.1287841796875),p(297.553125,1151.1287841796875),top]),edge('d','D','exit',[p(339.2750015258789,570.5),p(359.2750015258789,570.5),p(359.2750015258789,1196.6287841796875),right])]
        self.assertEqual(count_crossings(edges),1);swap_destination_tails(edges,nodes)
        self.assertEqual(count_crossings(edges),0);self.assertEqual(edges[0]['points'][-1],right);self.assertEqual(edges[1]['points'][-1],top)

    def test_source_external_channel_transaction_reassigns_tracks(self):
        from py_mermaid.diagrams.business._swimlane_routing.materialized import reassign_external_channels
        nodes={'26':node('26',-22,664,116,64),'27':node('27',-22,1602,116,116),'28':node('28',-22,1050,116,80)}
        edges=[edge('a','26','27',[p(-80,664),p(-100,664),p(-100,1660),p(-80,1660)]),edge('b','27','28',[p(36,1544),p(65,1544),p(65,1467),p(-126.4,1467),p(-126.4,1132),p(36,1132),p(36,1050)])]
        self.assertEqual(count_crossings(edges),2);reassign_external_channels(edges,nodes)
        self.assertEqual(count_crossings(edges),0);self.assertEqual(edges[0]['points'][1]['x'],-126.4);self.assertEqual(edges[1]['points'][3]['x'],-100)

    def test_redundant_rectangular_terminal_dogleg_collapses(self):
        from py_mermaid.diagrams.business._swimlane_routing.materialized import collapse_doglegs
        e=edge('e','A','B',[p(0,0),p(10,0),p(10,20),p(0,20),p(0,30)])
        collapse_doglegs([e],{});self.assertEqual(e['points'],[p(0,0),p(0,30)])

    def test_redundant_jog_shortcut_preserves_destination_and_reduces_bends(self):
        from py_mermaid.diagrams.business._swimlane_routing.materialized import shortcut_jogs
        e=edge('e','A','B',[p(0,0),p(100,0),p(100,50),p(20,50)])
        shortcut_jogs([e],{});self.assertEqual(e['points'],[p(0,0),p(0,50),p(20,50)])

    def test_shared_interior_nudge_uses_seven_pixel_gap_without_new_crossings(self):
        from py_mermaid.diagrams.business._swimlane_routing.shared_tracks import nudge_shared_interiors
        a=edge('a','A','B',[p(0,0),p(20,0),p(20,100),p(40,100)]);b=edge('b','C','D',[p(0,20),p(20,20),p(20,120),p(40,120)])
        before=count_crossings([a,b]);nudge_shared_interiors([a,b],{})
        self.assertGreaterEqual(abs(a['points'][1]['x']-b['points'][1]['x']),7)
        self.assertLessEqual(count_crossings([a,b]),before)

    def test_top_title_band_lifts_four_pixels_clear_of_final_rail(self):
        from py_mermaid.diagrams.business._swimlane_routing.materialized import lift_top_titles
        g=dict(node('L',100,100,200,200),isGroup=True,groupTitleRect=dict(left=0,right=200,top=0,bottom=36));e=edge('e','A','B',[p(0,20),p(200,20)])
        lift_top_titles([e],{'L':g},'TB')
        self.assertEqual(g['groupTitleRect'],dict(left=0,right=200,top=-20,bottom=16));self.assertEqual((g['y'],g['height']),(90,220))

    def test_left_title_band_moves_for_horizontal_and_vertical_rail(self):
        from py_mermaid.diagrams.business._swimlane_routing.materialized import shift_left_titles
        g=dict(node('L',100,100,200,200),isGroup=True,groupTitleRect=dict(left=0,right=36,top=0,bottom=200));e=edge('e','A','B',[p(20,0),p(20,200)])
        shift_left_titles([e],{'L':g},'LR')
        self.assertEqual(g['groupTitleRect'],dict(left=-20,right=16,top=0,bottom=200));self.assertEqual((g['x'],g['width']),(90,220))

    def test_validation_reports_exact_foreign_node_overlap_and_cross_pair(self):
        from py_mermaid.diagrams.business._swimlane_routing.validation import validate
        nodes=[node('A',0,0,10,10),node('B',100,0,10,10),node('X',50,0,20,20),node('C',50,-50,10,10),node('D',50,50,10,10)]
        edges=[edge('ab','A','B',[p(5,0),p(95,0)]),edge('cd','C','D',[p(50,-45),p(50,45)])]
        issues=validate(dict(nodes=nodes,edges=edges))
        self.assertEqual(sum(i['type']=='edge-node-overlap' for i in issues),2)
        self.assertEqual(sum(i['type']=='edge-edge-crossing' for i in issues),1)
        self.assertEqual(next(i for i in issues if i['type']=='edge-edge-crossing')['targetId'],'cd')


class FullOrthogonalRouter(unittest.TestCase):
    def test_source_collinear_chain_short_edge_centered_long_edge_detours(self):
        from py_mermaid.diagrams.business._swimlane_routing.router import route_edges_orthogonal
        data=dict(nodes=[node('D',50,22.5,42.1171875,45),node('E',50,117.5,41.34375,45),node('H',50,212.5,42.1171875,45)],edges=[edge('de','D','E'),edge('dh','D','H')],config={})
        route_edges_orthogonal(data,'TB');self.assert_route(data)
        self.assertTrue(all(abs(pt['x']-50)<1e-6 for pt in data['edges'][0]['points']))
        self.assertTrue(any(abs(pt['x']-50)>1 for pt in data['edges'][1]['points']))
        self.assertEqual(count_crossings(data['edges']),0)

    def assert_route(self,data):
        by_id={n['id']:n for n in data['nodes']}
        for e in data['edges']:
            pts=e.get('points') or [];self.assertGreaterEqual(len(pts),2,e['id'])
            self.assertTrue(on_border(pts[0],by_id[e['start']]),(e['id'],pts[0]))
            self.assertTrue(on_border(pts[-1],by_id[e['end']]),(e['id'],pts[-1]))
            for a,b in zip(pts,pts[1:]):
                self.assertTrue(abs(a['x']-b['x'])<1e-6 or abs(a['y']-b['y'])<1e-6,(a,b))
                self.assertTrue(all(math.isfinite(v) for v in (*a.values(),*b.values())))

    def test_source_four_cardinal_port_cases(self):
        from py_mermaid.diagrams.business._swimlane_routing.router import route_edges_orthogonal
        for target,expected_start,expected_end in [((300,150),(150,150),(250,150)),((-100,150),(50,150),(-50,150)),((100,350),(100,190),(100,310)),((100,-50),(100,110),(100,-10))]:
            with self.subTest(target=target):
                data=dict(nodes=[node('A',100,150),node('B',*target)],edges=[edge('e','A','B')],config={})
                route_edges_orthogonal(data,'TB');self.assert_route(data)
                self.assertEqual(data['edges'][0]['points'][0],p(*expected_start));self.assertEqual(data['edges'][0]['points'][-1],p(*expected_end))

    def test_astar_routes_around_blocker_without_crossing_its_open_interior(self):
        from py_mermaid.diagrams.business._swimlane_routing import route_and_postprocess
        obstacle=node('X',100,300,100,100);data=dict(nodes=[node('A',100,100),node('B',100,500),obstacle],edges=[edge('e','A','B')],config={})
        route_and_postprocess(data,'TB');self.assert_route(data)
        pts=data['edges'][0]['points'];self.assertTrue(any(q['x']<50 or q['x']>150 for q in pts))
        for a,b in zip(pts,pts[1:]):
            if abs(a['x']-b['x'])<1e-6:self.assertFalse(50<a['x']<150 and max(a['y'],b['y'])>250 and min(a['y'],b['y'])<350)
            else:self.assertFalse(250<a['y']<350 and max(a['x'],b['x'])>50 and min(a['x'],b['x'])<150)

    def test_all_direction_pipeline_and_layout_only_removal(self):
        from py_mermaid.diagrams.business._swimlane_routing import route_and_postprocess
        for direction in ('TB','BT','LR','RL'):
            with self.subTest(direction=direction):
                data=dict(nodes=[node('A',100,100),node('B',100,300)],edges=[edge('e','A','B',sentinel={'keep':1}),edge('virtual','A','B',isLayoutOnly=True)],config={})
                route_and_postprocess(data,direction);self.assert_route(data)
                self.assertEqual([e['id'] for e in data['edges']],['e']);self.assertEqual(data['edges'][0]['sentinel'],{'keep':1})
                a,b=data['nodes'];axis='x' if direction in ('LR','RL') else 'y'
                self.assertEqual(a[axis]<b[axis],direction in ('TB','LR'))

    def test_fanout_distributes_ports_and_preserves_opaque_source_values(self):
        from py_mermaid.diagrams.business._swimlane_routing.router import route_edges_orthogonal
        data=dict(nodes=[node('A',100,0),node('B',0,300),node('C',100,300),node('D',200,300)],edges=[edge('ab','A','B',curve='rounded'),edge('ac','A','C'),edge('ad','A','D')],config={})
        route_edges_orthogonal(data,'TB');self.assert_route(data)
        ports=[(e['points'][0]['x'],e['points'][0]['y']) for e in data['edges']]
        self.assertEqual(len(set(ports)),3);self.assertEqual(data['edges'][0]['curve'],'rounded')
