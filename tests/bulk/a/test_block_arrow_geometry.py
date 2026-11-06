"""Complete source blockArrow.ts nonempty direction-factory parameter family."""
import math
import unittest
from py_mermaid.diagrams.structures._block_arrows import points

FACTORIES=(('right',9),('left',7),('up',7),('down',7),('right|left',10),('up|down',10),('right|up',3),('right|down',3),('left|up',3),('left|down',3),('right|left|up',6),('right|left|down',4),('right|up|down',4),('left|up|down',4),('right|left|up|down',16))
class BlockArrowSourceTests(unittest.TestCase):
    def test_source_x_y_aliases_and_duplicate_directions(self):
        self.assertEqual(points(('x',),100,20,8),points(('right','left'),100,20,8));self.assertEqual(points(('y',),100,20,8),points(('up','down'),100,20,8));self.assertEqual(points(('right','right'),100,20,8),points(('right',),100,20,8))
    def test_source_right_factory_numeric_tip_and_body(self):
        vertices,w,h=points(('right',),100,20,8);self.assertEqual((w,h),(126,36));self.assertEqual(vertices[4],(126,18));self.assertEqual(vertices[0],(0,32))
    def test_source_all_directions_numeric_outer_extents(self):
        vertices,w,h=points(('right','left','up','down'),100,20,8);self.assertEqual((w,h),(160,52));self.assertEqual(len(vertices),16);self.assertEqual(min(x for x,y in vertices),0);self.assertEqual(min(y for x,y in vertices),0)

def _case(direction,count):
    def test(self):
        vertices,w,h=points(tuple(direction.split('|')),100,20,8)
        self.assertEqual(len(vertices),count);self.assertGreater(w,0);self.assertGreater(h,0);self.assertTrue(all(math.isfinite(n) for xy in vertices for n in xy));self.assertTrue(all(0<=x<=w and 0<=y<=h for x,y in vertices))
    return test
for _directions,_count in FACTORIES:setattr(BlockArrowSourceTests,'test_factory_'+_directions.replace('|','_'),_case(_directions,_count))
