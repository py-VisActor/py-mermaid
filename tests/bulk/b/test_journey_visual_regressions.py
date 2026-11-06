"""P4 manual rejection regressions, independently from journey svgDraw/render.

The source branches are svgDraw.js:285/307/346 and journeyRenderer.ts:166-191,
338-349. Public Canvas is an external font/ink reference, never a candidate
layout helper. Existing fixtures remain unchanged.
"""
from dataclasses import replace
from io import BytesIO
import math
import unittest
from PIL import Image
from py_skia_canvas import Canvas
from py_mermaid import parse
from py_mermaid.rendering.skia.scene import Painter
from py_mermaid.diagrams.temporal.journey import build
from .support import scene,command,shape_box


class JourneySourceVisualRegressions(unittest.IsolatedAsyncioTestCase):
    async def test_jv12_source_note_rect_default_border_is_preserved(self):
        # svgDrawCommon.getNoteRect stroke '#666'; Journey overrides fill,
        # dimensions and radii, but never clears this source default border.
        s=await scene('journey\nsection Work\nTask:5\n')
        for id in ('section-0','task-0'):
            style=dict(command(s,id).style)
            self.assertEqual(style['stroke'],'#666')
            self.assertEqual(style['line_width'],1)

    async def test_jv10_nonfinite_source_attributes_default_independently(self):
        for token in ('NaN','Infinity','-Infinity'):
            with self.subTest(token=token):
                s=await scene('journey\nTask:'+token+'\n')
                face=shape_box(command(s,'face-0'))
                self.assertAlmostEqual(face.y,-15)
                for side in (-1,1):
                    eye=shape_box(command(s,'eye-0-'+str(side)))
                    self.assertAlmostEqual(eye.y+eye.height/2,0)
                mouth=shape_box(command(s,'mouth-0'))
                if token=='NaN':
                    self.assertAlmostEqual(mouth.y,0)
                    self.assertAlmostEqual(mouth.width,10)
                    self.assertAlmostEqual(mouth.x+mouth.width/2,face.x+15)
                else:
                    self.assertAlmostEqual(mouth.x,0,delta=.001)
                    self.assertAlmostEqual(mouth.width,7.5,delta=.001)
                    self.assertAlmostEqual(mouth.y,0 if token=='Infinity' else -7.5,delta=.001)
                for c in s.commands:
                    if c.bounds:self.assertTrue(all(math.isfinite(v) for v in (c.bounds.x,c.bounds.y,c.bounds.width,c.bounds.height)))

    async def test_jv11_invalid_face_real_pixels_match_public_circle_not_white(self):
        d=parse('journey\nTask:NaN\n');p=Painter(d,backend='cpu');s=await build(d,p)
        face=command(s,'face-0');box=shape_box(face)
        result=p.encode(replace(s,commands=(face,)),format='png')
        actual=Image.open(BytesIO(result.data)).convert('RGB')
        canvas=Canvas(result.width,result.height);canvas.gpu=False;ctx=canvas.getContext('2d')
        ctx.fillStyle='white';ctx.fillRect(0,0,result.width,result.height)
        cx=box.x+15-s.origin_x;cy=-s.origin_y
        ctx.beginPath();ctx.arc(cx,cy,15,0,2*math.pi)
        ctx.fillStyle='#FFF8DC';ctx.fill();ctx.strokeStyle='#999';ctx.lineWidth=2;ctx.stroke()
        reference=Image.open(BytesIO(canvas.toBufferSync('png'))).convert('RGB')
        point=(round(cx),round(cy))
        self.assertEqual(actual.getpixel(point),reference.getpixel(point))
        self.assertNotEqual(actual.getpixel(point),(255,255,255))
        missing=p.encode(replace(s,commands=()),format='png')
        self.assertNotEqual(Image.open(BytesIO(missing.data)).convert('RGB').getpixel(point),reference.getpixel(point))

    async def test_jv01_default_title_ex_uses_public_glyph_metric(self):
        config={'fontFamily':'Arial','themeVariables':{'fontSize':'20px'},'journey':{'titleFontFamily':'Arial','titleFontSize':'4ex'}}
        s=await scene('journey\ntitle Visible title\nWork:5\n',config)
        title=next(c for c in s.commands if c.role=='title')
        canvas=Canvas(1,1);canvas.gpu=False;ctx=canvas.getContext('2d')
        ctx.font='normal 400 20px Arial';metric=ctx.measureText('x')
        # ex is measured from the parent baseline to the x-height. Native
        # metrics may put the glyph's bottom above the baseline (negative
        # descent); that must not subtract from the baseline-relative height.
        expected=4*(max(0,metric.actualBoundingBoxAscent)+max(0,metric.actualBoundingBoxDescent))
        self.assertAlmostEqual(title.values[0].runs[0].font_size,expected,delta=.05)
        self.assertGreater(expected,20) # rejects the old 4px interpretation
        self.assertGreater(title.values[0].height,20)

    async def test_jv02_absolute_title_px_and_baseline(self):
        s=await scene('journey\ntitle Title\nWork:5\n',{'journey':{'titleFontSize':'24px'}})
        title=next(c for c in s.commands if c.role=='title')
        label,x,y,angle,clip=title.values
        self.assertAlmostEqual(label.runs[0].font_size,24)
        self.assertAlmostEqual(y+label.runs[0].baseline,25)
        self.assertIsNone(clip)

    async def test_jv03_FO_wraps_text_inside_explicit_foreign_object(self):
        s=await scene('journey\nsection This section has several words\nA task with several words:5\n',{'journey':{'width':120,'height':60,'taskFontSize':30}})
        for text_id,rect_id in [('task-label-0','task-0'),('section-label-0','section-0')]:
            with self.subTest(id=text_id):
                c=command(s,text_id);label,x,y,angle,clip=c.values;rect=shape_box(command(s,rect_id))
                self.assertEqual(clip,rect)
                self.assertGreater(len({r.baseline for r in label.runs}),1)
                self.assertLessEqual(label.width,rect.width+.01)
                self.assertNotEqual(label.runs[0].font_size,30) # source FO inherits label CSS
                baselines=sorted({r.baseline for r in label.runs})
                self.assertAlmostEqual(baselines[1]-baselines[0],label.runs[0].font_size*1.2,delta=.01)

    async def test_jv04_old_is_unwrapped_root_font_and_source_baseline(self):
        s=await scene('journey\nA task with several words:5\n',{'journey':{'width':100,'height':50,'textPlacement':'old','taskFontSize':30}})
        label,x,y,angle,clip=command(s,'task-label-0').values
        self.assertIsNone(clip)
        self.assertEqual(len({r.baseline for r in label.runs}),1)
        self.assertGreater(label.width,100)
        self.assertNotEqual(label.runs[0].font_size,30)
        self.assertAlmostEqual(y+label.runs[0].baseline,110+25+5)

    async def test_jv05_tspan_breaks_only_explicit_br_and_uses_task_font(self):
        s=await scene('journey\nFirst long line<br/>Second:5\n',{'journey':{'width':80,'textPlacement':'svg','taskFontSize':18,'taskFontFamily':'Arial'}})
        a=command(s,'task-label-0');b=command(s,'task-label-0-line-1')
        self.assertEqual(a.values[0].text,'First long line')
        self.assertEqual(b.values[0].text,'Second')
        self.assertEqual(a.values[0].runs[0].font_size,18)
        self.assertGreater(a.values[0].width,80)
        self.assertIsNone(a.values[4])
        self.assertAlmostEqual(b.values[2]-a.values[2],18,delta=2)

    async def test_jv06_single_task_activity_source_bounds_176_pixels(self):
        s=await scene('journey\nOnly task:5:Person with a long name\n',{'journey':{'width':120,'taskMargin':30,'diagramMarginX':50,'maxLabelWidth':100}})
        b=shape_box(command(s,'activity'))
        self.assertAlmostEqual(b.width,176)
        self.assertAlmostEqual(b.height,0)
        self.assertTrue(command(s,'activity').values[0])

    async def test_jv07_many_task_activity_includes_last_source_bound(self):
        s=await scene('journey\nA:5\nB:3\nC:1\n',{'journey':{'width':120,'taskMargin':30,'diagramMarginX':50}})
        b=shape_box(command(s,'activity'))
        # Three source x positions 0,150,300 plus mx+gap+2mx-4=176.
        self.assertAlmostEqual(b.width,476)

    async def test_jv08_fo_actual_ink_clips_and_negative_controls_detect_regression(self):
        d=parse('journey\nA task with a very long line of words:5\n',config={'journey':{'width':90,'height':40}})
        p=Painter(d,backend='cpu');s=await build(d,p);target=command(s,'task-label-0')
        rect=shape_box(command(s,'task-0'))
        def pixels(scene_):
            r=p.encode(scene_,format='png')
            return Image.open(BytesIO(r.data)).convert('RGB'),r
        isolated=replace(s,commands=(target,))
        im,_=pixels(isolated)
        # The source FO viewport is explicit clipping; inspect actual ink, not
        # merely descriptor presence. Removed clipping must be observable.
        from PIL import ImageChops
        ink=ImageChops.difference(im,Image.new('RGB',im.size,'white')).getbbox()
        self.assertIsNotNone(ink)
        left=rect.x-s.origin_x;top=rect.y-s.origin_y
        self.assertGreaterEqual(ink[0],math.floor(left)-1)
        self.assertLessEqual(ink[2],math.ceil(left+rect.width)+1)
        self.assertLessEqual(ink[3],math.ceil(top+rect.height)+1)
        values=list(target.values);values[4]=None
        broken=replace(target,values=tuple(values))
        unbounded,_=pixels(replace(s,commands=(broken,)))
        self.assertNotEqual(im.tobytes(),unbounded.tobytes())

    async def test_jv09_activity_visible_ink_rejects_zero_length_negative(self):
        d=parse('journey\nOnly:5\n',config={'journey':{'width':120,'taskMargin':30,'diagramMarginX':50}})
        p=Painter(d,backend='cpu');s=await build(d,p);axis=command(s,'activity')
        from PIL import ImageChops
        def footprint(c):
            result=p.encode(replace(s,commands=(c,)),format='png')
            im=Image.open(BytesIO(result.data)).convert('RGB')
            return ImageChops.difference(im,Image.new('RGB',im.size,'white')).getbbox()
        bbox=footprint(axis)
        self.assertIsNotNone(bbox)
        self.assertGreater(bbox[2]-bbox[0],170)
        box=shape_box(axis)
        broken=replace(axis,values=(f'M{box.x},{box.y}L{box.x},{box.y}',axis.values[1]))
        empty=footprint(broken)
        self.assertTrue(empty is None or empty[2]-empty[0]<10)
