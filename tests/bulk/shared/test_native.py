"""Source CSS/SVG/label primitives translated to public Canvas owner-thread contracts.

Literal test paths and colors are authored independently; images are only made
inside test methods during P3/P4, never during collection.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import math
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from PIL import Image
from py_mermaid import MermaidError, ResourceBundle, ImageResource, IconResource, FontResource, ExportOptions, arender
from py_mermaid.model.flowchart import Box
from py_mermaid.parsing.preprocess import preprocess_diagram
from py_mermaid.runtime.common import make_diagram
from py_mermaid.runtime.configuration import resolve
from py_mermaid.rendering.skia.scene import Painter

SVG='<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20"><path fill="currentColor" d="M0 0H20V20H0Z"/></svg>'


def painter(config=None,resources=None,backend='cpu'):
    doc=preprocess_diagram('info')
    d=make_diagram('info',doc,resolve(doc,'info',config),())
    return Painter(d,resources=resources,backend=backend)


def image(r):
    im=Image.open(BytesIO(r.data));im.load();return im.convert('RGB')


def region(im,b):
    return im.crop((max(0,math.floor(b.x)),max(0,math.floor(b.y)),
                   min(im.width,math.ceil(b.x+b.width)),min(im.height,math.ceil(b.y+b.height))))


class NativePainterContracts(unittest.TestCase):
    def test_css_font_units_use_parent_and_public_canvas_glyph_metrics(self):
        from py_skia_canvas import Canvas
        p=painter(backend='cpu');canvas=Canvas(1,1);canvas.gpu=False
        context=canvas.getContext('2d');context.font='normal 700 20px Arial'
        metrics=context.measureText('x');zero=context.measureText('0')
        x_height=max(0,metrics.actualBoundingBoxAscent)+max(0,metrics.actualBoundingBoxDescent)
        self.assertAlmostEqual(p.font_size('4ex',base=20,family='Arial',weight='bold'),4*x_height,places=4)
        self.assertAlmostEqual(p.font_size('3ch',base=20,family='Arial',weight='bold'),3*zero.width,places=4)
        for value,expected in [('2em',40),('.5em',10),('+12pt',16),('2.em',40),('150%',30),('2rem',32),('12pt',16),('1in',96),('24px',24)]:
            with self.subTest(value=value):self.assertAlmostEqual(p.font_size(value,base=20),expected)
        self.assertNotEqual(p.font_size('4ex',base=20,family='Arial',weight='bold'),4)
        size=p.font_size('4ex',base=20,family='Arial',weight='bold')
        p.text('Metric',5,5,size=size,family='Arial',weight='bold',html=False,id='metric')
        r=p.encode(p.finish());events=[e for e in r.trace if e.semantic_id=='metric' and e.text]
        self.assertTrue(events);self.assertTrue(all(e.font_size==size for e in events))
        self.assertGreater(len(set(region(image(r),events[0].box).getdata())),5)

    def test_invalid_css_font_units_and_off_thread_metrics_fail_precisely(self):
        p=painter(backend='cpu')
        for value in ('-4ex','auto','4unknown',True,0):
            with self.subTest(value=value),self.assertRaises(MermaidError):p.font_size(value)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(MermaidError):pool.submit(p.font_size,'4ex').result()

    def test_path_dash_and_marker_trace_are_actual_paint_and_pixels(self):
        p=painter(backend='cpu');p.line(10,20,110,20,stroke='black',line_width=2,dash=(6,4),id='dashed')
        p.marker(110,20,1,0,kind='open',size=10,color='black',line_width=2,id='head')
        r=p.encode(p.finish());line=next(e for e in r.trace if e.semantic_id=='dashed')
        marker=next(e for e in r.trace if e.semantic_id=='head')
        self.assertEqual(line.dash,(6.,4.));self.assertEqual(marker.marker,'open');self.assertEqual(marker.stroke_width,2)
        self.assertEqual(marker.fill,'none')
        im=image(r);box=line.box;row=[min(im.getpixel((x,round(box.y+box.height/2)))) for x in range(round(box.x+12),round(box.x+72))]
        self.assertTrue(any(v<50 for v in row));self.assertTrue(any(v>240 for v in row))

    def test_nested_css_decorations_paint_all_lines_and_reject_erased_lines(self):
        from py_skia_canvas import Canvas
        from PIL import ImageDraw
        p=painter(backend='cpu')
        style=p.style((),tag='text',base={'font_size':32,'font_family':'Arial','text_color':'#000000','decoration':'overline'})
        p.text('<u><s>HH HH</s></u>',5,5,html=True,style=style,id='decorated')
        r=p.encode(p.finish());im=image(r);event=next(e for e in r.trace if e.semantic_id=='decorated' and e.text)
        c=Canvas(1,1);c.gpu=False;context=c.getContext('2d');context.font='normal 400 32px Arial'
        width=context.measureText('HH HH').width;ascent=context.measureText('H').actualBoundingBoxAscent
        x,y=event.points[0].x,event.points[0].y
        boxes={'underline':(x,y+1,x+width,y+8),
               'overline':(x,y-33,x+width,y-ascent-1),
               'line-through':(x+context.measureText('HH').width+1,y-ascent*.7,
                               x+context.measureText('HH ').width-1,y-ascent*.1)}
        def check(image,box):
            left,top,right,bottom=box;left=max(0,math.ceil(left));right=min(image.width,math.floor(right))
            return right>left and any(sum(min(image.getpixel((xx,yy)))<100 for xx in range(left,right))>.8*(right-left)
                for yy in range(max(0,math.floor(top)),min(image.height,math.ceil(bottom))))
        for name,box in boxes.items():
            with self.subTest(decoration=name):
                self.assertTrue(check(im,box))
                erased=im.copy();left,top,right,bottom=box
                ImageDraw.Draw(erased).rectangle((math.floor(left),math.floor(top),math.ceil(right),math.ceil(bottom)),fill='white')
                self.assertFalse(check(erased,box))
                self.assertGreater(sum(min(v)<100 for v in erased.getdata()),100)

    def test_compound_child_attribute_negation_and_specificity(self):
        p=painter({'look':'classic','themeCSS':'.outer rect.hot {fill:blue;} .outer > rect.hot[data-look="classic"]:not(.muted) {fill:red;} #target {stroke:green;} rect {stroke:black;}'})
        s=p.style(('hot',),tag='rect',id='target',ancestors=(('g',('outer',),'group'),))
        self.assertEqual(s.fill,'red');self.assertEqual(s.stroke,'green')
        muted=p.style(('hot','muted'),tag='rect',ancestors=(('g',('outer',),'group'),))
        self.assertEqual(muted.fill,'blue')
        distant=p.style(('hot',),tag='rect',ancestors=(('g',('outer',),'group'),('g',(),'intermediate')))
        self.assertEqual(distant.fill,'blue')

    def test_family_sheet_precedes_user_css_and_important_cascade(self):
        p=painter({'themeCSS':'.cell {fill:red;} .cell {stroke:blue!important;} #cell {stroke:green;}'})
        p.add_styles('.cell {fill:yellow;stroke:black;}')
        s=p.style('cell',id='cell')
        self.assertEqual(s.fill,'red');self.assertEqual(s.stroke,'blue')

    def test_nested_svg_tspan_own_declaration_beats_inherited_important(self):
        p=painter({'htmlLabels':False,'themeCSS':'text {fill:red!important;} tspan.inner {fill:blue;}'})
        parent=p.style((),tag='text')
        child=p.style(('inner',),tag='tspan',base=parent,inherited=parent,ancestors=parent.paint_context)
        self.assertEqual(parent.text_color,'red');self.assertEqual(child.text_color,'blue')

    def test_registered_horizontal_gradient_is_real_native_color(self):
        p=painter({'themeCSS':'.cell {fill:url(#fixture-gradient);stroke:none;}'})
        p.register_gradient('fixture-gradient',((0,'#ff0000'),(1,'#0000ff')))
        style=p.style('cell')
        p.rect(0,0,120,40,style=style,id='gradient')
        r=p.encode(p.finish(padding=8));im=image(r)
        left,right=im.getpixel((18,28)),im.getpixel((118,28))
        self.assertGreater(left[0],left[2]+100);self.assertGreater(right[2],right[0]+100)
        self.assertAlmostEqual(im.getpixel((68,15))[0],im.getpixel((68,40))[0],delta=3)

    def test_css_none_removes_gradient_in_later_rule(self):
        p=painter({'themeCSS':'.cell{fill:url(#g)} #target{fill:none}'})
        p.register_gradient('g',((0,'red'),(1,'blue')))
        s=p.style('cell',id='target')
        self.assertEqual(s.fill,'none');self.assertFalse(s.fill_gradient)

    def test_hidden_asset_does_not_load_and_opacity_paints_real_composite(self):
        p=painter()
        hidden=replace(p._base_style(),display='none')
        p.asset('unprovided-and-not-read',0,0,30,30,style=hidden)
        self.assertFalse(p.commands)
        p.svg(SVG,0,0,20,20,color='red',style=replace(p._base_style(),opacity=.5))
        r=p.encode(p.finish(padding=8));pixel=image(r).getpixel((18,18))
        self.assertGreater(pixel[0],250);self.assertAlmostEqual(pixel[1],128,delta=3)

    def test_affine_path_and_negative_origin_ink_are_retained(self):
        p=painter();p.path('M0,0H40V20H0Z',fill='red',transform=(0,1,-1,0,-30,-20),id='affine')
        scene=p.finish(padding=8);self.assertLess(scene.origin_x,0);self.assertLess(scene.origin_y,0)
        r=p.encode(scene);event=next(e for e in r.trace if e.semantic_id=='affine')
        self.assertGreaterEqual(event.box.x,0);self.assertGreaterEqual(event.box.y,0)
        self.assertEqual(image(r).getpixel((int(event.box.x+10),int(event.box.y+20))),(255,0,0))
        self.assertGreater(event.box.height,event.box.width)

    def test_clip_before_rotated_text_is_global_and_really_applied(self):
        p=painter();p.text('Clipped visible long label',0,0,size=30,id='clip',rotation=30,clip=Box(0,0,35,18))
        r=p.encode(p.finish(padding=8));im=image(r)
        self.assertGreater(sum(max(c)<200 for c in im.getdata()),5)
        event=next(e for e in r.trace if e.semantic_id=='clip' and e.clip is not None)
        self.assertIsNotNone(event.clip)
        # Outside the source global clip every pixel remains white.
        self.assertTrue(all(c==(255,255,255) for c in im.crop((44,0,im.width,im.height)).getdata()))

    def test_dashes_inherit_and_explicit_empty_dash_clears(self):
        p=painter();s=replace(p._base_style(),fill='none',stroke='black',dash=(4,3))
        p.line(0,0,100,0,style=s,id='inherited')
        p.line(0,20,100,20,style=s,id='cleared',dash=())
        values={c.semantic_id:dict(c.style)['dash'] for c in p.commands}
        self.assertEqual(values,{'inherited':(4,3),'cleared':()})

    def test_html_default_false_and_explicit_override_remain_distinct(self):
        p=painter({'htmlLabels':False})
        literal=p.measure('<b>Bold</b>')
        rich=p.measure('<b>Bold</b>',html=True)
        self.assertIn('<b>',''.join(r.text for r in literal.runs))
        self.assertEqual(''.join(r.text for r in rich.runs),'Bold')
        self.assertTrue(any(r.font_weight in ('bold','700') for r in rich.runs))

    def test_html_rich_text_math_uses_formal_dependency_real_glyphs(self):
        import importlib.metadata
        self.assertEqual(importlib.metadata.version('py-visactor-katex'),'0.1.0')
        p=painter({'htmlLabels':True});box=p.measure('Before $$\\frac{1}{2}$$ after')
        self.assertTrue(any(r.kind=='math' for r in box.runs))
        p.text(box,0,0,id='math');r=p.encode(p.finish())
        self.assertTrue(any(e.kind=='math-glyph' for e in r.trace))
        self.assertTrue(any(e.kind=='math-rule' for e in r.trace))
        self.assertGreater(sum(max(c)<180 for c in image(r).getdata()),30)

    def test_explicit_offline_font_controls_actual_generic_measure_and_draw(self):
        font=Path('C:/Windows/Fonts/arial.ttf')
        if not font.is_file():self.skipTest('Explicit fixture font unavailable; font environment not verified')
        bundle=ResourceBundle(fonts=(FontResource('FixtureArial',str(font),sha256(font.read_bytes()).hexdigest()),))
        p=painter({'fontFamily':'FixtureArial'},resources=bundle)
        small=p.measure('MMMM iii',size=12);large=p.measure('MMMM iii',size=36)
        self.assertGreater(large.width,small.width*2.8);self.assertLess(large.width,small.width*3.2)
        self.assertTrue(all('FixtureArial' in run.font_family for run in large.runs))
        p.text(large,0,0,id='font');r=p.encode(p.finish())
        self.assertGreater(sum(max(c)<180 for c in image(r).getdata()),30)

    def test_source_code_block_max_width_wraps_content_and_restores_outer_scope(self):
        p=painter({'htmlLabels':True})
        words='alpha beta gamma delta epsilon '*12
        unbounded=p.measure('<code style="display:block">'+words+'</code>',size=16)
        limited=p.measure('<code style="display:block;max-width:120px">'+words+'</code>',size=16)
        self.assertLess(limited.width,130)
        self.assertGreater(limited.height,unbounded.height*2)
        self.assertEqual(''.join(r.text for r in limited.runs).replace(' ',''),words.replace(' ',''))
        combined=p.measure('<code style="display:block;max-width:120px">'+words+'</code><div>wide wide wide wide wide wide wide</div>',size=16)
        self.assertGreater(combined.width,limited.width)
        inline=p.measure('<span style="max-width:20px">'+words+'</span>',size=16)
        self.assertGreater(inline.width,200,'CSS max-width does not constrain ordinary inline boxes')
        p.text(limited,0,0,id='code');result=p.encode(p.finish())
        self.assertGreater(sum(max(c)<180 for c in image(result).getdata()),40)

    def test_generic_static_label_sanitization_preserves_visible_anchor_caption(self):
        p=painter({'htmlLabels':True,'securityLevel':'strict'})
        text=p.measure('<script>BAD_SCRIPT</script><a href="javascript:evil()" onclick="evil()">SafeCaption</a>')
        visible=''.join(run.text for run in text.runs)
        self.assertIn('SafeCaption',visible);self.assertNotIn('BAD_SCRIPT',visible)
        p.text(text,0,0,id='safe');r=p.encode(p.finish())
        self.assertFalse(any('javascript:' in (e.text or '') or 'onclick' in (e.text or '') for e in r.trace))
        self.assertGreater(sum(max(c)<180 for c in image(r).getdata()),5)

    def test_brightness_and_shadow_filters_paint_without_rectangular_glyph_fill(self):
        p=painter({'htmlLabels':False,'themeCSS':'.word {fill:#808080;filter:brightness(120%);}'})
        style=p.style('word',tag='text')
        p.text('OO',0,0,size=32,id='filter',style=style)
        r=p.encode(p.finish());im=image(r)
        grays=[c[0] for c in im.getdata() if max(c)-min(c)<2 and 100<c[0]<230]
        self.assertTrue(grays);self.assertGreaterEqual(min(grays),150)
        self.assertTrue(any(c==(255,255,255) for c in im.getdata()))

    def test_seeded_handdrawn_geometry_repeats_but_differs_by_seed(self):
        def commands(seed):
            p=painter({'look':'handDrawn','handDrawnSeed':seed});p.rough_enabled=True
            p.rect(0,0,100,60,fill='red',stroke='black',id='rough')
            return tuple(c.values[0] for c in p.commands)
        self.assertEqual(commands(42),commands(42))
        self.assertNotEqual(commands(42),commands(43))
        self.assertGreater(len(commands(42)),1)

    def test_source_marker_topologies_not_placeholder_rectangles(self):
        for kind,minimum in (('point',1),('extension',1),('dependency',1),('aggregation',1),('composition',1),
                ('circle',1),('bar',1),('cross',2),('crow',3)):
            with self.subTest(kind=kind):
                p=painter();p.marker(30,30,1,0,kind=kind,size=10)
                self.assertEqual(len(p.commands),minimum)
                r=p.encode(p.finish());self.assertGreater(sum(max(c)<200 for c in image(r).getdata()),3)

    def test_native_owner_thread_rejects_foreign_use_and_bytes_cross_thread(self):
        p=painter();p.rect(0,0,20,20,fill='red')
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(MermaidError) as caught:pool.submit(p.measure,'forbidden').result()
        self.assertEqual(caught.exception.code,'THREAD_OWNERSHIP')
        data=p.encode(p.finish()).data
        with ThreadPoolExecutor(max_workers=1) as pool:
            self.assertEqual(pool.submit(lambda b:Image.open(BytesIO(b)).size,data).result(),(36,36))

    def test_resource_hash_and_svg_active_external_content_rejected(self):
        for svg in ('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
                    '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/x.png"/></svg>',
                    '<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>'):
            with self.subTest(svg=svg),self.assertRaises(MermaidError) as caught:
                painter(resources=ResourceBundle(icons=(IconResource('fixture:bad',svg),))).asset('fixture:bad',0,0,20,20,kind='icon')
            self.assertEqual(caught.exception.code,'UNSAFE_RESOURCE')
        with self.assertRaises(MermaidError) as caught:
            painter(resources=ResourceBundle(icons=(IconResource('fixture:hash',SVG,'0'*64),)))
        self.assertEqual(caught.exception.code,'RESOURCE_INTEGRITY')

    def test_tint_cannot_inject_markup_or_external_resource(self):
        p=painter()
        with self.assertRaises(MermaidError) as caught:
            p.svg(SVG,0,0,20,20,color='red"/><image href="https://example.com/a"/><path fill="red')
        self.assertIn(caught.exception.code,('INVALID_STYLE','INVALID_COLOR','INVALID_RESOURCE','UNSAFE_RESOURCE'))

    def test_generic_scene_native_exports_contain_shape_and_text(self):
        for fmt in ('png','jpg','webp','svg','pdf'):
            with self.subTest(format=fmt):
                p=painter();p.rect(0,0,140,70,fill='#00ff00');p.text('ExportWord',4,4,id='word')
                r=p.encode(p.finish(),format=fmt)
                self.assertGreater(len(r.data),200)
                self.assertTrue(any(e.semantic_id=='word' for e in r.trace))
                if fmt in ('png','jpg','webp'):
                    im=image(r);self.assertEqual(im.size,(r.width,r.height));self.assertGreater(len(set(im.getdata())),5)
                elif fmt=='svg':
                    svg=ET.fromstring(r.data);self.assertTrue(svg.tag.endswith('svg'));self.assertIn(b'ExportWord',r.data)
                    self.assertTrue(any(e.tag.endswith('path') for e in svg.iter()))
                else:
                    self.assertTrue(r.data.startswith(b'%PDF-'));self.assertIn(b'%%EOF',r.data[-100:])


class PublicAsyncContracts(unittest.IsolatedAsyncioTestCase):
    async def test_generic_info_device_profiles_actual_output(self):
        for backend in ('cpu','auto','gpu'):
            with self.subTest(backend=backend):
                r=await arender('info',backend=backend)
                renderer=dict(r.backend)['renderer']
                if backend!='auto':self.assertEqual(renderer,backend.upper())
                self.assertTrue(r.data.startswith(b'\x89PNG'));self.assertGreater(len(set(image(r).getdata())),5)

    async def test_sync_render_inside_active_loop_and_invalid_api_options(self):
        from py_mermaid import render
        with self.assertRaises(MermaidError) as caught:render('info')
        self.assertEqual(caught.exception.code,'ACTIVE_EVENT_LOOP')
        for kwargs,code in (({'format':'raw'},'UNSUPPORTED_FORMAT'),({'backend':'silent-fallback'},'INVALID_BACKEND')):
            with self.subTest(kwargs=kwargs),self.assertRaises(MermaidError) as caught:await arender('info',**kwargs)
            self.assertEqual(caught.exception.code,code)


if __name__=='__main__':unittest.main()
