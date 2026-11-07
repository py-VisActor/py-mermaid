"""Independent Canvas stroke contracts; no diagram-specific canvas clamping."""
from dataclasses import replace
from io import BytesIO
import math
import unittest
from unittest.mock import patch

from PIL import Image
from py_skia_canvas import Canvas,Path2D
from py_mermaid.model.scene import Diagram
from py_mermaid.model.flowchart import SourceDocument,ResolvedStyle
from py_mermaid.rendering.skia.scene import Painter


def painter():return Painter(Diagram('info',SourceDocument('info'),(),None),backend='cpu')


class PathStrokeBoundsTests(unittest.TestCase):
    def record(self,d,width,*,cap='butt',join='miter',matrix=(1,0,0,1,0,0),dash=()):
        p=painter();style=ResolvedStyle(fill='none',stroke='black',stroke_width=width,
                                      line_cap=cap,line_join=join,shadow_opacity=0)
        p.path(d,style=style,transform=matrix,dash=dash)
        return p,p.commands[-1].bounds

    def assert_pixels_contained(self,d,width,box,*,cap='butt',join='miter'):
        # Independent public API draws on a generous fixed surface; every
        # actual nonzero alpha pixel must fit the computed world-space bounds.
        canvas=Canvas(500,500);canvas.gpu=False;ctx=canvas.getContext('2d')
        ctx.translate(100,100);ctx.lineWidth=width;ctx.lineCap=cap;ctx.lineJoin=join
        ctx.strokeStyle='black';ctx.stroke(Path2D(d))
        data=bytes(ctx.getImageData(0,0,500,500).data)
        points=[(i%500-100+.5,i//500-100+.5) for i,a in enumerate(data[3::4]) if a>0]
        self.assertGreater(len(points),10)
        for x,y in points:
            self.assertGreaterEqual(x,box.x-1);self.assertLessEqual(x,box.x+box.width+1)
            self.assertGreaterEqual(y,box.y-1);self.assertLessEqual(y,box.y+box.height+1)

    def test_axis_butt_ends_do_not_extend_canvas_by_ten_stroke_widths(self):
        p,b=self.record('M0 0H700',1)
        self.assertAlmostEqual(b.x,0);self.assertAlmostEqual(b.width,700)
        self.assertAlmostEqual(b.y,-.5);self.assertAlmostEqual(b.height,1)
        _,b=self.record('M0 0V400',1)
        self.assertAlmostEqual(b.y,0);self.assertAlmostEqual(b.height,400)

    def test_sankey_smooth_thick_cubic_keeps_physical_600_by_400(self):
        p,b=self.record('M0 200C200 200 400 200 600 200',360)
        self.assertAlmostEqual(b.x,0);self.assertAlmostEqual(b.width,600)
        self.assertAlmostEqual(b.y,20);self.assertAlmostEqual(b.height,360)
        scene=p.finish(width=600,height=400,padding=0)
        self.assertEqual((scene.width,scene.height),(600,400))

    def test_curved_cubic_bounds_contain_real_stroke_without_giant_margin(self):
        d='M40 180C40 40 260 40 260 180';p,b=self.record(d,60)
        self.assert_pixels_contained(d,60,b)
        self.assertLess(b.width,285);self.assertLess(b.height,190)
        scene=p.finish(padding=2,background='transparent');result=p.encode(scene)
        image=Image.open(BytesIO(result.data)).convert('RGBA')
        independent=Canvas(scene.width,scene.height);independent.gpu=False
        ctx=independent.getContext('2d');ctx.translate(-scene.origin_x,-scene.origin_y)
        ctx.strokeStyle='black';ctx.lineWidth=60;ctx.stroke(Path2D(d))
        expected=Image.open(BytesIO(independent.toBufferSync('png'))).convert('RGBA')
        self.assertEqual(image.tobytes(),expected.tobytes())

    def test_actual_acute_miter_tip_is_retained(self):
        d='M80 180L120 40L160 180';_,b=self.record(d,20)
        self.assertLess(b.y,10);self.assertGreater(b.y,0)
        self.assert_pixels_contained(d,20,b)

    def test_miter_limit_falls_back_to_bevel_for_too_sharp_corner(self):
        d='M100 180L120 40L121 180';_,b=self.record(d,20)
        self.assertGreater(b.y,25)
        self.assert_pixels_contained(d,20,b)

    def test_round_square_and_diagonal_caps_match_canvas_geometry(self):
        for cap,left,right in [('butt',40,140),('round',30,150),('square',30,150)]:
            with self.subTest(cap=cap):
                _,b=self.record('M40 50H140',20,cap=cap)
                self.assertAlmostEqual(b.x,left);self.assertAlmostEqual(b.x+b.width,right)
                self.assert_pixels_contained('M40 50H140',20,b,cap=cap)
        _,b=self.record('M40 40L140 140',20,cap='square')
        self.assertAlmostEqual(b.x,40-10*math.sqrt(2),places=5)
        self.assert_pixels_contained('M40 40L140 140',20,b,cap='square')

    def test_affine_transforms_path_but_not_actual_context_stroke_width(self):
        _,b=self.record('M0 0H100',10,matrix=(2,0,0,3,7,9))
        self.assertAlmostEqual(b.x,7);self.assertAlmostEqual(b.width,200)
        self.assertAlmostEqual(b.y,4);self.assertAlmostEqual(b.height,10)

    def test_closed_conic_outline_and_degenerate_cubic_are_bounded(self):
        for d in ['M40 100A60 60 0 1 0 160 100A60 60 0 1 0 40 100Z',
                  'M40 100C40 100 40 100 160 100']:
            with self.subTest(path=d):
                _,b=self.record(d,20)
                self.assert_pixels_contained(d,20,b)
                self.assertLess(b.width,145);self.assertLess(b.height,145)

    def test_round_dashed_curves_keep_actual_cap_ink(self):
        d='M40 180C40 40 260 40 260 180';_,b=self.record(d,20,cap='round',dash=(4,10))
        # Full solid stroke is a conservative reference for round dash caps.
        self.assert_pixels_contained(d,20,b,cap='round')

    def test_shadow_mask_uses_same_visible_stroke_bounds_and_restores_paint(self):
        p=painter();style=ResolvedStyle(fill='none',stroke='#2468ac',stroke_width=100,
            shadow_color='#e02020',shadow_opacity=1,shadow_dx=20,shadow_dy=20,shadow_blur=0)
        p.path('M40 100C140 100 260 100 360 100',style=style)
        allocations=[];create=p.session._new_canvas
        def tracked(w,h):allocations.append((w,h));return create(w,h)
        with patch.object(p.session,'_new_canvas',side_effect=tracked):
            result=p.encode(p.finish(padding=2))
        self.assertTrue(allocations);self.assertTrue(all(w<=350 and h<=130 for w,h in allocations),allocations)
        pixels=list(Image.open(BytesIO(result.data)).convert('RGB').getdata())
        self.assertGreater(sum(r>g*2 and r>b*2 for r,g,b in pixels),100)
        self.assertGreater(sum(b>r*2 and b>g for r,g,b in pixels),100)


if __name__=='__main__':unittest.main()
