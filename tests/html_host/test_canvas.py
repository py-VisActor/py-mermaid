"""Source/HTML initial-state and public Canvas pixel contracts, no goldens.

Only test execution allocates native objects. P2 import/collection is inert.
Explicit author sizes/colors isolate required state/content from platform UA
styling differences; comparisons never require browser and Canvas zero pixels.
"""
from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
import math
import re
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops


SVG = ("<svg xmlns='http://www.w3.org/2000/svg' width='40' height='20' viewBox='0 0 40 20'>"
       "<rect width='20' height='20' fill='#e02020'/><rect x='20' width='20' height='20' fill='#2040e0'/></svg>")
DATA_URI = 'data:image/svg+xml;base64,' + base64.b64encode(SVG.encode()).decode()


def graph(markup):
    return 'flowchart TD\nA["' + markup + '"]'


async def render_markup(markup, **kwargs):
    from py_mermaid import arender
    return await arender(graph(markup), backend=kwargs.pop('backend', 'cpu'), **kwargs)


def decode(test, result):
    test.assertTrue(result.data.startswith(b'\x89PNG\r\n\x1a\n'))
    image=Image.open(BytesIO(result.data)).convert('RGB')
    test.assertEqual(image.size,(result.width,result.height))
    return image


def controls(result):
    return [event for event in result.trace if event.kind=='control']


def control(result, tag='input', type_=''):
    # ControlSpec.input_type is empty for non-input tags; the actual container
    # key preserves that semantic field rather than layout's effective kind.
    return next(event for event in controls(result) if event.resource_id==tag+':'+type_)


def crop_box(image, box, inset=0):
    return image.crop((math.ceil(box.x+inset),math.ceil(box.y+inset),
                       math.floor(box.x+box.width-inset),math.floor(box.y+box.height-inset)))


def text_ink(test, result, image, value, predicate=None):
    events=[event for event in result.trace if event.text and value in event.text]
    test.assertTrue(events,'missing actual glyph event '+value)
    predicate=predicate or (lambda pixel:sum(pixel)<420)
    crops=[crop_box(image,event.box) for event in events if event.box and event.box.width>0 and event.box.height>0]
    test.assertTrue(any(any(hi-lo>15 for lo,hi in crop.getextrema()) for crop in crops),
                    'uniform background cannot replace glyphs '+value)
    test.assertGreater(sum(sum(predicate(pixel) for pixel in crop.getdata()) for crop in crops),2,
                       'missing actual glyph pixels '+value)
    return events


def blue(pixel):
    r,g,b=pixel
    return b>r*1.3 and b>g*1.05 and b-r>30


def green(pixel):
    r,g,b=pixel
    return g>r*1.35 and g>b*1.2 and g-r>25


def xs_with_color(image, box, predicate):
    crop=crop_box(image,box)
    return [x for x in range(crop.width) if any(predicate(crop.getpixel((x,y))) for y in range(crop.height))]


def assert_checked_checkbox(test, result, image):
    summary=control(result,'input','checkbox')
    inner=crop_box(image,summary.box,3)
    test.assertGreater(sum(blue(p) for p in inner.getdata()),5,'missing checked accent fill')
    # Outer border/nonwhite fill cannot stand in for the white checkmark.
    marks=[e for e in result.trace if e.kind=='control-path' and e.stroke in ('#ffffff','#FFFFFF','white')]
    test.assertTrue(marks,'missing executed checkmark path')
    test.assertGreater(sum(all(c>235 for c in p) for e in marks for p in crop_box(image,e.box).getdata()),3,
                       'accent frame exists but checkmark glyph is missing')


def layout_values(result):
    def runs(values):
        for run in values:
            layout=getattr(run,'control',None)
            if layout is not None:
                yield layout
                yield from runs(layout.content_runs)
                yield from runs(layout.caption_runs)
    for node in result.measured:yield from runs(node.runs)


class StaticControlPixels(unittest.IsolatedAsyncioTestCase):
    async def test_checkbox_checked_has_real_mark_unchecked_does_not(self):
        css="style='width:28px;height:28px;accent-color:rgb(36,104,172);margin:0'"
        checked=await render_markup('<input type=\'checkbox\' checked '+css+'>')
        plain=await render_markup('<input type=\'checkbox\' '+css+'>')
        a,b=decode(self,checked),decode(self,plain)
        assert_checked_checkbox(self,checked,a)
        self.assertFalse(any(e.kind=='control-path' for e in plain.trace))
        self.assertGreater(len(xs_with_color(a,control(checked,'input','checkbox').box,blue)),8)
        self.assertEqual(xs_with_color(b,control(plain,'input','checkbox').box,blue),[])

    async def test_radio_selected_has_center_dot_and_unselected_not_accented(self):
        css="style='width:28px;height:28px;accent-color:rgb(36,104,172);margin:0'"
        selected=await render_markup('<input type=\'radio\' checked '+css+'>')
        plain=await render_markup('<input type=\'radio\' '+css+'>')
        image=decode(self,selected);box=control(selected,'input','radio').box
        self.assertGreater(len(xs_with_color(image,box,blue)),10)
        center=image.getpixel((round(box.x+box.width/2),round(box.y+box.height/2)))
        # Original Chromium control has a blue center and a white interior
        # ring, not a white dot on a solid blue disk.
        self.assertTrue(blue(center),'selected blue center indicator was lost')
        self.assertGreater(sum(all(v>235 for v in p) for p in crop_box(image,box,3).getdata()),10)
        self.assertEqual(xs_with_color(decode(self,plain),control(plain,'input','radio').box,blue),[])

    async def test_checkbox_mark_loss_mutation_fails_even_with_outer_chrome(self):
        from py_mermaid.rendering.skia import controls as executor
        original=executor.paint_control
        def missing_mark(context,layout,*args,**kwargs):
            layout=replace(layout,paints=tuple(p for p in layout.paints if not (p.kind=='path' and p.stroke=='#ffffff')))
            return original(context,layout,*args,**kwargs)
        with patch.object(executor,'paint_control',missing_mark):
            result=await render_markup("<input type='checkbox' checked style='width:28px;height:28px;accent-color:rgb(36,104,172)'>")
        with self.assertRaises(AssertionError):assert_checked_checkbox(self,result,decode(self,result))

    async def test_meter_fraction_has_proportional_real_green_fill(self):
        spans=[]
        for value in (25,75):
            result=await render_markup(f"<meter min='0' max='100' value='{value}' low='0' high='100' optimum='50' style='width:120px;height:20px'></meter>")
            image=decode(self,result);spans.append(len(xs_with_color(image,control(result,'meter').box,green)))
            self.assertAlmostEqual(next(layout_values(result)).spec.fraction,value/100)
        self.assertGreater(spans[0],15);self.assertGreater(spans[1],spans[0]*2.4)
        self.assertAlmostEqual(spans[0]/spans[1],1/3,delta=.08)

    async def test_progress_determinate_fill_ratios_and_empty_endpoint(self):
        spans=[]
        for value in (0,25,75):
            result=await render_markup(f"<progress max='100' value='{value}' style='width:120px;height:20px;accent-color:rgb(36,104,172)'></progress>")
            spans.append(len(xs_with_color(decode(self,result),control(result,'progress').box,blue)))
        self.assertEqual(spans[0],0);self.assertGreater(spans[1],15)
        self.assertAlmostEqual(spans[1]/spans[2],1/3,delta=.08)

    async def test_progress_indeterminate_has_static_initial_indicator(self):
        result=await render_markup("<progress style='width:120px;height:20px;accent-color:rgb(36,104,172)'></progress>")
        self.assertIsNone(next(layout_values(result)).spec.fraction)
        span=len(xs_with_color(decode(self,result),control(result,'progress').box,blue))
        self.assertGreater(span,10);self.assertLess(span,110)

    async def test_range_thumb_moves_with_value_and_reverses_in_rtl(self):
        positions=[]
        for direction,value in (('ltr',25),('ltr',75),('rtl',25)):
            result=await render_markup(f"<input type='range' min='0' max='100' value='{value}' style='width:140px;height:24px;accent-color:rgb(36,104,172);direction:{direction}'>")
            box=control(result,'input','range').box
            circles=[e for e in result.trace if e.kind=='control-circle']
            self.assertEqual(len(circles),1)
            self.assertGreater(len(xs_with_color(decode(self,result),circles[0].box,blue)),5)
            positions.append((circles[0].box.x+circles[0].box.width/2)-box.x)
        self.assertGreater(positions[1]-positions[0],40)
        self.assertAlmostEqual(positions[2],positions[1],delta=2)

    async def test_button_unicode_bold_italic_and_underline_are_actual_content(self):
        result=await render_markup("<button style='width:180px;height:45px'><strong><em><u>Launch \u542f\u52a8</u></em></strong></button>")
        image=decode(self,result);events=text_ink(self,result,image,'Launch')
        self.assertTrue(any(str(e.font_weight) in ('bold','700') for e in events))
        self.assertTrue(any(e.font_style=='italic' for e in events))
        text_ink(self,result,image,'\u542f\u52a8')

    async def test_button_frame_without_value_or_rich_glyphs_is_rejected(self):
        from py_mermaid.rendering.skia import controls as executor
        original=executor.paint_control
        def missing_text(context,layout,*args,**kwargs):
            return original(context,replace(layout,paints=tuple(p for p in layout.paints if p.kind!='text'),content_runs=()),*args,**kwargs)
        with patch.object(executor,'paint_control',missing_text):result=await render_markup('<button>Important</button>')
        self.assertTrue(any(e.kind=='control-roundrect' for e in result.trace))
        with self.assertRaises(AssertionError):text_ink(self,result,decode(self,result),'Important')

    async def test_textarea_newlines_and_unicode_remain_separate_visible_rows(self):
        result=await render_markup("<textarea rows='3' cols='14'>First&#10;\u7b2c\u4e8c\u884c&#10;Third</textarea>")
        image=decode(self,result)
        rows=[text_ink(self,result,image,value)[0] for value in ('First','\u7b2c\u4e8c\u884c','Third')]
        self.assertLess(rows[0].box.y,rows[1].box.y);self.assertLess(rows[1].box.y,rows[2].box.y)

    async def test_collapsed_select_paints_selected_unicode_and_arrow(self):
        result=await render_markup("<select><option>Unchosen</option><option selected>\u5df2\u9009\u9879</option></select>")
        image=decode(self,result);text_ink(self,result,image,'\u5df2\u9009\u9879')
        self.assertFalse(any(e.text=='Unchosen' for e in result.trace))
        self.assertTrue(any(e.kind=='control-path' for e in result.trace))
        self.assertEqual(next(layout_values(result)).spec.selected_indices,(1,))

    async def test_multiple_select_keeps_group_titles_and_all_visible_rows(self):
        result=await render_markup("<select multiple size='4'><optgroup label='Group'><option selected>One</option><option>Two</option></optgroup><option selected>Three</option></select>")
        image=decode(self,result)
        for value in ('Group','One','Two','Three'):text_ink(self,result,image,value,lambda p:sum(p)<650)
        self.assertEqual(next(layout_values(result)).spec.selected_indices,(0,2))

    async def test_author_color_overrides_disabled_ua_text_and_readonly_keeps_value(self):
        for attr in ('disabled','readonly'):
            result=await render_markup(f"<input value='Authored' {attr} style='color:#d02030'>")
            text_ink(self,result,decode(self,result),'Authored',lambda p:p[0]>p[1]*1.6 and p[0]>p[2]*1.4)
            spec=next(layout_values(result)).spec
            self.assertTrue(getattr(spec,attr))

    async def test_nested_opacity_composes_once_per_element(self):
        result=await render_markup("<span style='opacity:.5'><button style='opacity:.5;background:rgb(208,32,48);width:80px;height:40px;border:0'></button></span>")
        image=decode(self,result);b=control(result,'button').box
        pixel=image.getpixel((round(b.x+b.width*.7),round(b.y+b.height*.7)))
        for actual,color in zip(pixel,(208,32,48)):
            self.assertAlmostEqual(actual,255*.75+color*.25,delta=3)

    async def test_visibility_hidden_parent_can_restore_visible_child_text(self):
        result=await render_markup("<button style='visibility:hidden'><span style='visibility:visible;color:#d02030'>Restored</span></button>")
        text_ink(self,result,decode(self,result),'Restored',lambda p:p[0]>p[1]*1.6 and p[0]>p[2]*1.4)
        self.assertFalse(any(e.kind in ('control-rect','control-roundrect') for e in result.trace))

    async def test_fieldset_legend_and_nested_checkbox_are_visible(self):
        result=await render_markup("<fieldset style='width:220px'><legend>Legend \u6807\u9898</legend>Body <input type='checkbox' checked style='width:24px;height:24px;accent-color:rgb(36,104,172)'></fieldset>")
        image=decode(self,result);legend=text_ink(self,result,image,'Legend')[0]
        text_ink(self,result,image,'Body');assert_checked_checkbox(self,result,image)
        self.assertIsNone(legend.clip,'legend must not receive fieldset body clipping')
        self.assertTrue(any(layout.spec.tag=='fieldset' and layout.caption_runs for layout in layout_values(result)))

    async def test_input_image_uses_explicit_offline_pixels_and_source_ratio(self):
        from py_mermaid import ResourceBundle,ImageResource
        resources=ResourceBundle(images=(ImageResource('quad',SVG.encode(),'image/svg+xml'),))
        result=await render_markup("<input type='image' src='quad' width='80' height='40' alt='Submit'>",resources=resources)
        image=decode(self,result);event=next(e for e in result.trace if e.kind=='control-image')
        self.assertAlmostEqual(event.box.width/event.box.height,2,delta=.01)
        left=image.getpixel((round(event.box.x+event.box.width*.25),round(event.box.y+event.box.height*.5)))
        right=image.getpixel((round(event.box.x+event.box.width*.75),round(event.box.y+event.box.height*.5)))
        self.assertGreater(left[0],left[2]*2);self.assertGreater(right[2],right[0]*2)

    async def test_input_image_data_uri_is_offline_and_missing_resource_is_explicit(self):
        from py_mermaid import MermaidError
        markup="<input type='image' src='"+DATA_URI+"' width='80' height='40'>"
        # DOMPurify's default data-URI tag set excludes input. Explicitly
        # authorize this tag when asserting the actual offline image branch.
        default=await render_markup(markup)
        self.assertFalse(any(e.kind=='control-image' for e in default.trace))
        result=await render_markup(markup,config={'securityLevel':'loose',
            'dompurifyConfig':{'ADD_DATA_URI_TAGS':['input']}})
        self.assertTrue(any(e.kind=='control-image' for e in result.trace));decode(self,result)
        with self.assertRaises(MermaidError):await render_markup("<input type='image' src='https://example.invalid/never-fetch.png'>")

    async def test_input_image_without_dimensions_keeps_resource_natural_size(self):
        from py_mermaid import ResourceBundle,ImageResource
        resources=ResourceBundle(images=(ImageResource('natural',SVG.encode(),'image/svg+xml'),))
        result=await render_markup("<input type='image' src='natural' alt='Submit'>",resources=resources)
        layout=next(layout_values(result));self.assertEqual((layout.width,layout.height),(40,20))
        event=next(e for e in result.trace if e.kind=='control-image')
        self.assertEqual((event.box.width,event.box.height),(40,20));decode(self,result)

    async def test_input_image_css_width_preserves_natural_aspect_ratio(self):
        from py_mermaid import ResourceBundle,ImageResource
        resources=ResourceBundle(images=(ImageResource('natural',SVG.encode(),'image/svg+xml'),))
        result=await render_markup("<input type='image' src='natural' style='width:80px'>",resources=resources)
        layout=next(layout_values(result));self.assertEqual((layout.width,layout.height),(80,40))
        event=next(e for e in result.trace if e.kind=='control-image')
        self.assertEqual((event.box.width,event.box.height),(80,40));decode(self,result)

    async def test_control_value_author_letter_and_word_spacing_change_actual_glyph_span(self):
        for value,property_,amount,minimum in (('IIII','letter-spacing',3,8),('I I I','word-spacing',8,12)):
            spans=[]
            for spacing in (0,amount):
                result=await render_markup(f"<input value='{value}' style='width:200px;height:40px;font-size:24px;{property_}:{spacing}px'>")
                image=decode(self,result);event=text_ink(self,result,image,value)[0]
                pixels=crop_box(image,event.box)
                xs=[x for x in range(pixels.width) if any(sum(pixels.getpixel((x,y)))<300 for y in range(pixels.height))]
                self.assertTrue(xs);spans.append(max(xs)-min(xs))
            self.assertGreaterEqual(spans[1]-spans[0],minimum)

    async def test_control_value_author_text_shadow_has_actual_offset_red_glyphs(self):
        result=await render_markup("<input value='Shadow' style='width:180px;height:40px;font-size:24px;color:black;text-shadow:6px 0 0 #d02030'>")
        image=decode(self,result);text_ink(self,result,image,'Shadow')
        pixels=crop_box(image,control(result,'input','text').box)
        self.assertGreater(sum(r>g*1.6 and r>b*1.4 for r,g,b in pixels.getdata()),5)

    async def test_control_value_author_text_stroke_is_not_silently_lost(self):
        result=await render_markup("<input value='Stroke' style='width:180px;height:40px;font-size:24px;color:white;-webkit-text-stroke:2px #2040e0'>")
        image=decode(self,result);pixels=crop_box(image,control(result,'input','text').box)
        self.assertGreater(sum(blue(pixel) for pixel in pixels.getdata()),5)

    async def test_five_exports_contain_static_output_not_live_form_protocol(self):
        for fmt in ('png','jpg','webp','svg','pdf'):
            with self.subTest(format=fmt):
                result=await render_markup("<button>Exported</button><input type='checkbox' checked>",format=fmt)
                self.assertTrue(any(e.text=='Exported' for e in result.trace))
                if fmt in ('png','jpg','webp'):
                    image=Image.open(BytesIO(result.data));self.assertEqual(image.size,(result.width,result.height))
                    self.assertEqual(image.format,{'png':'PNG','jpg':'JPEG','webp':'WEBP'}[fmt])
                    self.assertGreater(len(set(image.convert('RGB').getdata())),2)
                elif fmt=='svg':
                    root=ET.fromstring(result.data);self.assertEqual(root.tag.rsplit('}',1)[-1],'svg')
                    self.assertFalse(any(e.tag.rsplit('}',1)[-1] in ('input','button','foreignObject') for e in root.iter()))
                    self.assertGreater(len(list(root.iter())),2)
                else:
                    self.assertTrue(result.data.startswith(b'%PDF-'));self.assertIn(b'/MediaBox',result.data)
                    self.assertIn(b'%%EOF',result.data);self.assertGreater(len(result.data),700)

    async def test_literal_html_labels_false_has_text_without_control_paint(self):
        result=await render_markup("<input type='checkbox' checked>",config={'htmlLabels':False})
        self.assertFalse(any(e.kind.startswith('control') for e in result.trace))
        text_ink(self,result,decode(self,result),'input')

    async def test_unknown_input_type_uses_text_fallback_without_losing_value(self):
        result=await render_markup("<input type='future-type' value='Fallback'>")
        text_ink(self,result,decode(self,result),'Fallback')
        self.assertEqual(next(layout_values(result)).spec.input_type,'text')

    async def test_hidden_input_has_no_visible_control_or_value(self):
        result=await render_markup("Visible<input type='hidden' value='SECRET'>")
        text_ink(self,result,decode(self,result),'Visible')
        self.assertFalse(any(e.text and 'SECRET' in e.text for e in result.trace))
        self.assertFalse(controls(result))

    async def test_video_audio_remain_excluded_even_with_poster_and_controls(self):
        from py_mermaid import MermaidError
        for markup in ("<video controls poster='"+DATA_URI+"'></video>",'<audio controls></audio>'):
            with self.subTest(markup=markup):
                with self.assertRaises(MermaidError) as caught:await render_markup(markup)
                self.assertEqual(caught.exception.code,'UNSUPPORTED_LABEL_RESOURCE')

    async def test_cpu_auto_gpu_controls_use_explicit_backend_policy(self):
        for backend in ('cpu','auto','gpu'):
            with self.subTest(backend=backend):
                result=await render_markup("<button>Backend</button>",backend=backend)
                text_ink(self,result,decode(self,result),'Backend')
                metadata=dict(result.backend)
                self.assertEqual(metadata['renderer'],'CPU' if backend=='cpu' else 'GPU' if backend=='gpu' else metadata['renderer'])


class ControlExecutorPublicCanvas(unittest.TestCase):
    def text_painter(self,ctx):
        # Exercise the same shared glyph executor used by production controls;
        # pixel expectations below remain independent geometric assertions.
        from py_mermaid.model.flowchart import Box
        from py_mermaid.rendering.skia.session import CanvasSession
        session=CanvasSession(backend='cpu')
        return lambda runs,x,y:session._draw_runs(ctx,runs,Box(x,y,0,0),'control-text','',0,0)

    def surface(self):
        from py_skia_canvas import Canvas
        canvas=Canvas(120,70);canvas.gpu=False;context=canvas.getContext('2d')
        context.fillStyle='white';context.fillRect(0,0,120,70)
        return canvas,context

    def image(self,canvas):
        return Image.open(BytesIO(canvas.toBufferSync('png'))).convert('RGB')

    def test_content_clip_does_not_clip_frame_or_replace_current_path(self):
        from py_mermaid.model.controls import ControlSpec,ControlPaint,ControlLayout
        from py_mermaid.rendering.skia.controls import paint_control
        canvas,ctx=self.surface();ctx.beginPath();ctx.rect(85,10,10,10)
        layout=ControlLayout(ControlSpec('input','text'),50,30,20,(
            ControlPaint('rect',width=50,height=30,fill='white',stroke='#00a000'),
            ControlPaint('text',x=2,y=20,text='MMMMMMMM',font_size=18,fill='black'),),clip=(2,2,25,22))
        events=paint_control(ctx,layout,10,10,paint_runs=self.text_painter(ctx))
        ctx.fillStyle='#e02020';ctx.fill()
        image=self.image(canvas)
        self.assertGreater(sum(sum(p)<400 for p in image.crop((12,12,37,34)).getdata()),5)
        self.assertEqual(sum(sum(p)<400 for p in image.crop((40,13,55,33)).getdata()),0)
        self.assertGreater(image.getpixel((59,25))[1],image.getpixel((59,25))[0])
        self.assertGreater(image.getpixel((90,15))[0],image.getpixel((90,15))[1]*2)
        event=next(e for e in events if e.kind=='control-text')
        self.assertLessEqual(event.box.x+event.box.width,37)

    def test_callback_fault_restores_native_state(self):
        from py_mermaid.model.controls import ControlSpec,ControlPaint,ControlLayout
        from py_mermaid.rendering.skia.controls import paint_control
        _,ctx=self.surface();ctx.fillStyle='#204060';ctx.lineWidth=7;ctx.globalAlpha=.4
        before=(str(ctx.fillStyle),ctx.lineWidth,ctx.globalAlpha,ctx.font)
        layout=ControlLayout(ControlSpec('input','image'),20,20,20,(ControlPaint('image',resource_id='asset',width=20,height=20),))
        def fault(*_):raise RuntimeError('injected image failure')
        with self.assertRaisesRegex(RuntimeError,'injected'):
            paint_control(ctx,layout,0,0,paint_runs=lambda *_:(),paint_image=fault)
        self.assertEqual((str(ctx.fillStyle),ctx.lineWidth,ctx.globalAlpha,ctx.font),before)

    def test_owner_thread_rejected_without_native_transfer(self):
        from py_mermaid.model.controls import ControlSpec,ControlPaint,ControlLayout
        from py_mermaid.rendering.skia.controls import paint_control
        canvas,ctx=self.surface()
        layout=ControlLayout(ControlSpec('button'),20,20,15,(ControlPaint('rect',width=20,height=20,fill='red'),))
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(RuntimeError):pool.submit(paint_control,ctx,layout,0,0,paint_runs=lambda *_:()).result()
        self.assertIsNotNone(canvas)

    def test_invalid_geometry_and_command_budgets_reject_before_ink(self):
        from py_mermaid import MermaidError
        from py_mermaid.model.controls import ControlSpec,ControlPaint,ControlLayout
        from py_mermaid.rendering.skia.controls import paint_control
        canvas,ctx=self.surface();before=self.image(canvas).tobytes()
        layouts=[ControlLayout(ControlSpec('input'),20,20,15,(ControlPaint('rect',width=math.inf,height=5,fill='red'),)),
                 ControlLayout(ControlSpec('input'),20,20,15,(ControlPaint('unknown',width=5,height=5),)),
                 ControlLayout(ControlSpec('input'),20,20,15,(ControlPaint('rect',width=1,height=1),)*4097)]
        for layout in layouts:
            with self.subTest(layout=layout.spec.tag):
                with self.assertRaises(MermaidError):paint_control(ctx,layout,0,0,paint_runs=lambda *_:())
                self.assertEqual(self.image(canvas).tobytes(),before)

    def test_multiple_decoration_lines_add_pixels_beyond_plain_glyphs(self):
        from py_mermaid.model.controls import ControlSpec,ControlPaint,ControlLayout
        from py_mermaid.rendering.skia.controls import paint_control
        images=[]
        for decoration in ('','underline overline'):
            canvas,ctx=self.surface()
            layout=ControlLayout(ControlSpec('input','text'),100,50,30,(
                ControlPaint('text',x=5,y=30,text='Decor',font_size=20,fill='black',decoration=decoration),))
            paint_control(ctx,layout,0,0,paint_runs=self.text_painter(ctx));images.append(self.image(canvas))
        diff=ImageChops.difference(*images)
        self.assertIsNotNone(diff.getbbox())
        self.assertGreater(sum(sum(p)>30 for p in diff.crop((0,30,90,42)).getdata()),5)
        self.assertGreater(sum(sum(p)>30 for p in diff.crop((0,3,90,15)).getdata()),5)
