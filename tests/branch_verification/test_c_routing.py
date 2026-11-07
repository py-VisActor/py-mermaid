"""Finite private-router predicates; literal source constants, no native."""
import unittest


def node(identifier,x,y,width=100,height=80,**extra):
    return dict(id=identifier,x=x,y=y,width=width,height=height,**extra)


def edge(identifier,start,end,**extra):return dict(id=identifier,start=start,end=end,**extra)
def point(x,y):return dict(x=x,y=y)


class SwimlanePrivateBranches(unittest.TestCase):
    def router(self,nodes=(),edges=(),direction='TB'):
        from py_mermaid.diagrams.business._swimlane_routing.router import Router
        return Router(dict(nodes=list(nodes),edges=list(edges),config={}),direction)

    def test_vertical_bias_inclusive_three_threshold_and_coincident_fallback(self):
        from py_mermaid.diagrams.business._swimlane_routing.router import choose_side
        a=node('A',0,0)
        for target,expected in [(point(30,10),'bottom'),(point(30.0001,10),'right'),(point(-30,-10),'top'),(point(-30.0001,-10),'left')]:
            with self.subTest(target=target):self.assertEqual(choose_side(a,target),expected)
        self.assertEqual(choose_side(a,point(0,0),'left'),'left')

    def test_obstacle_padding_excludes_groups_labels_and_lr_uses_visual_height(self):
        r=self.router([node('A',100,100,40,20),node('G',0,0,isGroup=True),node('L',0,0,isEdgeLabel=True)],direction='LR')
        self.assertEqual(r.obstacles,[dict(nodeId='A',minX=72,minY=82,maxX=128,maxY=118,visualXHalfExtent=18)])

    def test_source_destination_port_spacing_minimum_middle_maximum_and_diamond_fraction(self):
        for width,shape,expected in [(120,'rect',[-20,0,20]),(48,'rect',[-12,0,12]),(60,'diamond',[-8,0,8])]:
            with self.subTest(width=width,shape=shape):
                nodes=[node('S'+str(i),x,0) for i,x in enumerate((-30,0,30))]+[node('D',0,300,width,80,shape=shape)]
                r=self.router(nodes,[edge('e'+str(i),'S'+str(i),'D') for i in range(3)])
                self.assertEqual([r.offsets[(i,'dst')] for i in range(3)],expected)

    def test_sibling_side_split_moves_weaker_primary_only_when_secondary_less_loaded(self):
        r=self.router([node('A',0,0),node('B',0,300),node('C',60,300)],[edge('ab','A','B'),edge('ac','A','C')])
        self.assertEqual([r.side_info[i]['srcSide'] for i in range(2)],['bottom','right'])

    def test_diamond_incoming_outgoing_same_face_decollides_to_free_secondary(self):
        r=self.router([node('X',0,-300),node('D',0,0,shape='diamond'),node('B',60,-300)],[edge('xd','X','D'),edge('db','D','B')])
        self.assertEqual(r.side_info[0]['dstSide'],'top')
        self.assertEqual(r.side_info[1]['srcSide'],'right')

    def test_preexisting_route_and_layout_only_edges_do_not_reassign_ports(self):
        given=[point(0,0),point(1,0)]
        r=self.router([node('A',0,0),node('B',0,300)],[edge('ab','A','B',points=given),edge('layout','A','B',isLayoutOnly=True)])
        self.assertEqual(r.side_info,{})
        self.assertEqual(len(r.edges),1);self.assertEqual(r.edges[0]['points'],given)

    def test_crossing_penalty_counts_other_axis_other_edge_only(self):
        r=self.router()
        r.routed=[dict(edgeIndex=1,orientation='vertical',pipe=dict(coord=5),**{'from':0,'to':10})]
        self.assertEqual(r.crossing_penalty(0,point(0,5),point(10,5)),1000)
        self.assertEqual(r.crossing_penalty(1,point(0,5),point(10,5)),0)
        self.assertEqual(r.crossing_penalty(0,point(0,20),point(10,20)),0)
        self.assertEqual(r.crossing_penalty(0,point(0,0),point(10,10)),0)

    def test_pipe_reuse_strict_one_pixel_threshold_and_union_span(self):
        r=self.router();a=r.pipe('horizontal',10,0,10);b=r.pipe('horizontal',10.999,-5,5)
        self.assertIs(a,b);self.assertEqual((a['spanMin'],a['spanMax']),(-5,10))
        self.assertIsNot(a,r.pipe('horizontal',11,0,10))

    def test_feedback_upward_ports_point_outward_and_path_remains_orthogonal(self):
        from py_mermaid.diagrams.business._swimlane_routing import route_and_postprocess
        data=dict(nodes=[node('A',0,300),node('B',0,0)],edges=[edge('back','A','B')],config={})
        route_and_postprocess(data,'TB');points=data['edges'][0]['points']
        self.assertEqual(points[0],point(0,260));self.assertEqual(points[-1],point(0,40))
        self.assertTrue(all(a['x']==b['x'] or a['y']==b['y'] for a,b in zip(points,points[1:])))
