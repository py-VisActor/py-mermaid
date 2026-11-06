"""F014 source-derived Canvas/resource/export assertions, no candidate goldens.

Handwritten SVG and test-only placements isolate native painting. Pixel controls
verify actual assets, parts, fonts and markers; semantic trace alone cannot pass.
Only unittest execution creates images/native objects; import is collection-safe.
"""
from __future__ import annotations
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace,fields,is_dataclass
from hashlib import sha256
from io import BytesIO
import json,math,re,unittest,zlib
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image,ImageColor
from py_skia_canvas import Canvas,FontLibrary,Path2D
from py_mermaid.api import parse,render
from py_mermaid.config import resolve_config
from py_mermaid.config.values import freeze_value
from py_mermaid.geometry.rough import rough_path,Random
from py_mermaid.model.flowchart import (Box,Flowchart,FlowNode,FlowEdge,FlowLayout,PlacedNode,
    Point,EdgeSection,RoutedEdge,ImageResource,IconResource,FontResource,ResourceBundle,
    ExportOptions,MermaidError,SourcePosition,SourceSpan)
from py_mermaid.rendering.skia import CanvasSession

SPAN=SourceSpan(SourcePosition(0,0,1,0),SourcePosition(1,1,1,1))
# Written geometric assets, not copied or rendered candidate output.
QUAD_SVG='<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20" viewBox="0 0 40 20"><path fill="red" d="M0 0H20V10H0Z"/><path fill="lime" d="M20 0H40V10H20Z"/><path fill="blue" d="M0 10H20V20H0Z"/><path fill="yellow" d="M20 10H40V20H20Z"/></svg>'
ICON_SVG='<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="currentColor" d="M0 0H24V8H8V24H0Z"/></svg>'
DATA_URI='data:image/svg+xml;base64,'+base64.b64encode(QUAD_SVG.encode()).decode()
FONT=Path('C:/Windows/Fonts/arial.ttf')

def bundle():return ResourceBundle(images=(ImageResource('quad',QUAD_SVG.encode(),'image/svg+xml'),),icons=(IconResource('test:angle',ICON_SVG),IconResource('fa:check',ICON_SVG)))

def diagram(label='Asset',*,shape='square',metadata=None,config=None):
    return Flowchart('test-only source fixture','TD',(FlowNode('A',label,SPAN,shape=shape,raw_label=label,metadata=freeze_value(metadata or {})),),(),resolve_config(config))

def draw(d,*,resources=None,backend='cpu',format='png',options=None,extra_width=0,session=None):
    session=session or CanvasSession(backend,resources=resources);measured=session.measure(d);ann=session.measure_annotations(d)
    placed=tuple(PlacedNode(n.id,Box(30+i*320,40,n.width+extra_width,n.height+extra_width)) for i,n in enumerate(measured))
    edges=tuple(RoutedEdge(e.id,(EdgeSection(Point(30+measured[0].width,65),(),Point(350,65)),),
        (Point(30+measured[0].width,65),Point(350,65)),'linear',f'M {30+measured[0].width:g} 65 L 350 65',Box(30+measured[0].width,65,320-measured[0].width,0)) for e in d.edges)
    layout=FlowLayout(placed,edges,700 if d.edges else 300,250,'test-only','source fixture')
    return session.render(d,measured,layout,annotations=ann,format=format,export_options=options)

def img(result):
    i=Image.open(BytesIO(result.data));i.load();return i.convert('RGB')

def pixels(image,box):
    return tuple(image.crop((max(0,math.floor(box.x)),max(0,math.floor(box.y)),min(image.width,math.ceil(box.x+box.width)),min(image.height,math.ceil(box.y+box.height)))).getdata())

def dark(p):return max(p)<145

def colored(p):return max(p)-min(p)>120

def verify_quad(result,kind='node-asset',semantic_id=None):
    event=next(e for e in result.trace if e.kind==kind and (semantic_id is None or e.semantic_id==semantic_id));box=event.box;i=img(result)
    # Literal SVG quadrants at internal quarter points, independent source colors.
    expected=((.25,.25,(255,0,0)),(.75,.25,(0,255,0)),(.25,.75,(0,0,255)),(.75,.75,(255,255,0)))
    for x,y,color in expected:
        actual=i.getpixel((int(box.x+x*box.width),int(box.y+y*box.height)))
        assert max(abs(a-b) for a,b in zip(actual,color))<8,(actual,color,box)
    return event

class ResourceCanvasTests(unittest.TestCase):
    def test_typed_image_real_decode_and_source_constraint_dimensions(self):
        for constraint,height in (('off',20),('on',60)):
            with self.subTest(constraint=constraint):
                d=diagram('Photo',shape='imageSquare',metadata={'img':'quad','constraint':constraint})
                r=draw(d,resources=bundle());event=verify_quad(r)
                self.assertAlmostEqual(event.box.width,120);self.assertAlmostEqual(event.box.height,height)
                self.assertEqual(r.measured[0].assets[0].resource_id,'quad')
                self.assertEqual(r.diagram.nodes[0].label,'Photo')

    def test_source_image_natural_and_explicit_asset_dimensions(self):
        r=draw(diagram('',shape='imageSquare',metadata={'img':'quad','w':80,'h':30}),resources=bundle())
        event=verify_quad(r);self.assertEqual((event.box.width,event.box.height),(80,30))
        # Empty source span has no label bbox or phantom text line allocation.
        self.assertEqual(r.measured[0].label_height,0)
        self.assertEqual(r.measured[0].height,30)

    def test_source_top_bottom_label_gap_and_real_mask(self):
        for pos in ('t','b'):
            r=draw(diagram('Photo',shape='imageSquare',metadata={'img':'quad','pos':pos}),resources=bundle())
            asset=verify_quad(r);text=next(e for e in r.trace if e.kind=='text' and e.text=='Photo')
            background=next(e for e in r.trace if e.kind=='resource-label-background')
            # Fixed source Khroma retains negative hue; Pillow's CSS parser
            # rejects it. Check the exact source intent and actual gray pixels.
            self.assertEqual(background.fill,'hsl(-120, 0%, 80%)')
            corner=img(r).getpixel((int(background.box.x+1),int(background.box.y+1)))
            self.assertEqual(corner,(204,204,204))
            if pos=='t':self.assertLess(text.box.y+text.box.height,asset.box.y)
            else:self.assertGreater(text.box.y,asset.box.y+asset.box.height)
            self.assertGreater(sum(dark(p) for p in pixels(img(r),text.box)),2)

    def test_icon_real_currentcolor_and_default_frame_size(self):
        for shape,size in (('icon',48),('iconSquare',63),('iconRounded',63),('iconCircle',48*math.sqrt(2)+40)):
            with self.subTest(shape=shape):
                r=draw(diagram('Icon',shape=shape,metadata={'icon':'test:angle'}),resources=bundle())
                event=next(e for e in r.trace if e.kind=='node-asset')
                self.assertEqual((event.box.width,event.box.height),(48,48))
                self.assertGreater(sum(dark(p) for p in pixels(img(r),event.box)),30)
                self.assertAlmostEqual(r.measured[0].height-r.measured[0].label_height-8,size,places=5)
                if shape!='icon':self.assertTrue(any(e.kind=='node-part' for e in r.trace))

    def test_unknown_icon_source_question_fallback_visible(self):
        r=draw(diagram('Unknown',shape='icon',metadata={'icon':'missing:entry'}))
        event=next(e for e in r.trace if e.kind=='node-asset');p=pixels(img(r),event.box)
        self.assertGreater(sum(c[2]>120 and c[0]<70 for c in p),30)
        self.assertGreater(sum(min(c)>230 for c in p),3)

    def test_inline_explicit_data_uri_and_direct_svg_are_real_images(self):
        r=draw(diagram(f'<img src="{DATA_URI}">'));e=verify_quad(r,'inline-asset')
        self.assertEqual((e.box.width,e.box.height),(80,40)) # img-only site16*5
        direct=draw(diagram(QUAD_SVG));e=next(e for e in direct.trace if e.kind=='inline-asset')
        self.assertEqual((e.box.width,e.box.height),(40,20)) # SVG native intrinsic box
        self.assertGreater(sum(dark(p) for p in pixels(img(direct),e.box)),20)
        self.assertEqual(img(direct).getpixel((int(e.box.x+10),int(e.box.y+5))),(255,255,255))
        self.assertTrue(any(run.kind=='svg' for run in direct.measured[0].runs))

    def test_mixed_text_image_and_fontawesome_explicit_icon(self):
        r=draw(diagram('Before<img src="quad">After fa:fa-check'),resources=bundle())
        self.assertEqual(''.join(e.text or '' for e in r.trace if e.kind=='text'),'BeforeAfter ')
        events=[e for e in r.trace if e.kind=='inline-asset'];self.assertEqual(len(events),2)
        self.assertEqual(events[0].box.width,120);verify_quad(r,'inline-asset')
        self.assertGreater(sum(dark(p) for p in pixels(img(r),events[1].box)),3)

    def test_inline_svg_gradient_and_local_clip_survive_sanitizer(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20" viewBox="0 0 40 20"><defs><linearGradient id="g"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient></defs><rect width="40" height="20" style="fill:url(#g)"/></svg>'
        r=draw(diagram(svg));e=next(e for e in r.trace if e.kind=='inline-asset');i=img(r)
        left=i.getpixel((int(e.box.x+e.box.width*.1),int(e.box.y+e.box.height*.5)))
        right=i.getpixel((int(e.box.x+e.box.width*.9),int(e.box.y+e.box.height*.5)))
        self.assertGreater(left[0],left[2]+130);self.assertGreater(right[2],right[0]+130)

    def test_direct_svg_host_paint_and_data_uri_isolation_through_real_api(self):
        direct_svg=QUAD_SVG.replace('"',"'")
        text=f'flowchart TD\nD["{direct_svg}"] --> I["<img src=\'{DATA_URI}\'>"]'
        r=render(text,backend='cpu');i=img(r)
        direct=next(e for e in r.trace if e.kind=='inline-asset' and e.semantic_id=='D')
        self.assertEqual((direct.box.width,direct.box.height),(40,20))
        def verify_host(image):
            for x,y in ((.25,.25),(.75,.25),(.25,.75),(.75,.75)):
                color=image.getpixel((int(direct.box.x+x*direct.box.width),int(direct.box.y+y*direct.box.height)))
                assert color==(255,255,255),('host .node path CSS fill must override presentation attrs',color)
            assert sum(dark(p) for p in pixels(image,direct.box))>20,'grid stroke missing'
        verify_host(i);verify_quad(r,'inline-asset','I')
        # Old implementation's colored direct SVG cannot pass the same oracle.
        wrong=i.copy()
        from PIL import ImageDraw
        painter=ImageDraw.Draw(wrong)
        for x,y,color in ((0,0,'red'),(1,0,'lime'),(0,1,'blue'),(1,1,'yellow')):
            left=int(direct.box.x+x*20);top=int(direct.box.y+y*10)
            painter.rectangle((left,top,left+19,top+9),fill=color)
        with self.assertRaises(AssertionError):verify_host(wrong)
        with self.assertRaises(AssertionError):verify_host(Image.new('RGB',i.size,'white'))

    def test_missing_image_is_explicit_and_no_network_fallback(self):
        for value in ('quad','https://example.invalid/a.png','file:///C:/secret.png'):
            with self.subTest(value=value),self.assertRaises(MermaidError) as caught:
                CanvasSession('cpu').measure(diagram(f'<img src="{value}">'))
            self.assertEqual(caught.exception.code,'RESOURCE_NOT_FOUND')

    def test_svg_external_event_script_and_entity_resources_rejected(self):
        payloads=('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg" onload="x()"/>',
            '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/x.png"/></svg>',
            '<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///C:/x">]><svg xmlns="http://www.w3.org/2000/svg"/>')
        for payload in payloads:
            with self.subTest(payload=payload),self.assertRaises(MermaidError) as caught:
                CanvasSession('cpu',resources=ResourceBundle(icons=(IconResource('bad',payload),)))
            self.assertEqual(caught.exception.code,'UNSAFE_RESOURCE')

    def test_sha_duplicates_decode_and_budget_fail_explicitly(self):
        cases=[(ResourceBundle(images=(ImageResource('bad',b'notpng',sha256='0'*64),)),'RESOURCE_INTEGRITY'),
            (ResourceBundle(images=(ImageResource('same',b'x'),ImageResource('same',b'y'))),'INVALID_RESOURCE'),
            (ResourceBundle(images=(ImageResource('huge',b'x'*(32*1024*1024+1)),)),'RESOURCE_BUDGET')]
        for resources,code in cases:
            with self.subTest(code=code),self.assertRaises(MermaidError) as caught:CanvasSession('cpu',resources)
            self.assertEqual(caught.exception.code,code)
        with self.assertRaises(MermaidError) as caught:draw(diagram('',shape='imageSquare',metadata={'img':'bad'}),resources=ResourceBundle(images=(ImageResource('bad',b'notpng'),)))
        self.assertEqual(caught.exception.code,'RESOURCE_DECODE')

    def test_explicit_font_path_hash_real_owner_registration_and_metrics(self):
        self.assertTrue(FONT.is_file(),'source fixture requires the recorded existing Arial font')
        font=FontResource('F014ExplicitFace',str(FONT),sha256(FONT.read_bytes()).hexdigest())
        resources=ResourceBundle(fonts=(font,));r=draw(diagram('Font WWW',config={'fontFamily':'F014ExplicitFace'}),resources=resources)
        self.assertTrue(FontLibrary.has('F014ExplicitFace'))
        e=next(e for e in r.trace if e.kind=='text');self.assertGreater(sum(dark(p) for p in pixels(img(r),e.box)),3)
        c=Canvas(1,1);c.gpu=False;x=c.getContext('2d');x.font='normal 400 14px F014ExplicitFace';x.textAlign='left'
        self.assertAlmostEqual(r.measured[0].runs[0].width,x.measureText('Font WWW').width,places=4)
        with ThreadPoolExecutor(1) as pool:self.assertFalse(pool.submit(FontLibrary.has,'F014ExplicitFace').result())
        with self.assertRaises(MermaidError) as caught:CanvasSession('cpu',ResourceBundle(fonts=(replace(font,sha256='0'*64),)))
        self.assertEqual(caught.exception.code,'RESOURCE_INTEGRITY')

    def test_resource_cache_owner_and_returned_values_are_pure(self):
        session=CanvasSession('cpu',bundle());d=diagram('Photo',shape='imageSquare',metadata={'img':'quad'})
        a=draw(d,session=session);b=draw(d,session=session);self.assertEqual(a.data,b.data)
        with ThreadPoolExecutor(1) as pool:
            with self.assertRaises(MermaidError) as caught:pool.submit(session.measure,d).result()
        self.assertEqual(caught.exception.code,'THREAD_OWNERSHIP')
        def pure(value):
            if is_dataclass(value):return all(pure(getattr(value,f.name)) for f in fields(value))
            if isinstance(value,(tuple,list)):return all(pure(x) for x in value)
            return isinstance(value,(str,bytes,int,float,bool,type(None)))
        self.assertTrue(pure(a))

    def test_resource_pixel_white_and_missing_asset_negative_controls(self):
        r=draw(diagram('Photo',shape='imageSquare',metadata={'img':'quad'}),resources=bundle());verify_quad(r)
        blank=Image.new('RGB',(r.width,r.height),'white');out=BytesIO();blank.save(out,format='PNG')
        with self.assertRaises(AssertionError):verify_quad(replace(r,data=out.getvalue()))
        with self.assertRaises(StopIteration):verify_quad(replace(r,trace=tuple(e for e in r.trace if e.kind!='node-asset')))

class RoughAndPaintTests(unittest.TestCase):
    def test_seeded_rng_matches_fixed_roughjs_imul_stream(self):
        r=Random(1)
        # Literal results of source ((Math.imul(48271,seed))&0x7fffffff)/2**31.
        self.assertEqual([r.next() for _ in range(3)],[48271/2147483648,(48271**2%2147483648)/2147483648,(48271**3%2147483648)/2147483648])

    def test_source_truthy_seed_before_imul_fractional_boundary(self):
        # JS Random constructor preserves the numeric seed. Truthiness precedes
        # Math.imul's ToInt32: these truthy numbers produce first sample zero,
        # then seed=0 selects the source Math.random branch on subsequent calls.
        for seed in (.5,2**32):
            with self.subTest(seed=seed):
                self.assertEqual(Random(seed).next(),0)

    def test_nonzero_seed_geometry_and_png_deterministic_and_seed_change_visible(self):
        config={'look':'handDrawn','handDrawnSeed':123}
        a=draw(diagram('Sketch',config=config));b=draw(diagram('Sketch',config=config));c=draw(diagram('Sketch',config={**config,'handDrawnSeed':124}))
        self.assertEqual(a.data,b.data);self.assertNotEqual(a.data,c.data)
        self.assertGreater(len(set(img(a).getdata())),10)
        self.assertTrue(any(e.kind=='text' and e.text=='Sketch' for e in a.trace))
        p=rough_path('M0 0H100V50H0Z',seed=123);self.assertIn('C',p.stroke_path);self.assertTrue(p.fill_path)

    def test_seed_zero_retains_random_semantics_and_real_hachure(self):
        a=draw(diagram('Sketch',config={'look':'handDrawn','handDrawnSeed':0}));b=draw(diagram('Sketch',config={'look':'handDrawn','handDrawnSeed':0}))
        self.assertNotEqual(a.data,b.data)
        node=next(e for e in a.trace if e.kind=='node');inside=Box(node.box.x+5,node.box.y+4,node.box.width-10,node.box.height-8)
        self.assertGreater(len(set(pixels(img(a),inside))),5)

    def test_parts_have_actual_ink_and_whiteout_negative_control(self):
        r=draw(diagram('Document',shape='doc'))
        self.assertTrue(r.measured[0].parts or r.measured[0].outline)
        node=next(e for e in r.trace if e.kind=='node');i=img(r)
        bottom=Box(node.box.x,node.box.y+node.box.height-12,node.box.width,13)
        self.assertGreater(sum(dark(p) for p in pixels(i,bottom)),10)
        white=Image.new('RGB',i.size,'white');self.assertEqual(sum(dark(p) for p in pixels(white,bottom)),0)
        # Cylinder top inner arc is an independently specified visible component.
        cyl=draw(diagram('Cylinder',shape='cylinder'));box=next(e.box for e in cyl.trace if e.kind=='node')
        self.assertGreater(sum(dark(p) for p in pixels(img(cyl),Box(box.x+3,box.y+8,box.width-6,12))),4)

    def test_datastore_fill_and_horizontal_only_border_are_real_pixels(self):
        # datastore.ts keeps drawRect's closed fill, then removes vertical
        # stroke via width/height dash pattern. It is not two unfilled lines.
        d=diagram('Data',shape='datastore')
        d=replace(d,nodes=(replace(d.nodes[0],styles=('fill:#fee2e2','stroke:black')),))
        r=draw(d);self.assertFalse(r.measured[0].paint_outline)
        node=next(e for e in r.trace if e.kind=='node');i=img(r);box=node.box
        def verify(image):
            fill=image.getpixel((int(box.x+box.width*.8),int(box.y+box.height*.5)))
            assert fill==(254,226,226),('closed datastore fill absent',fill)
            for x in (box.x,box.x+box.width):
                strip=Box(x-1,box.y+box.height*.3,2,box.height*.4)
                assert sum(dark(p) for p in pixels(image,strip))==0,'datastore must have no vertical border'
            top=Box(box.x+box.width*.3,box.y-1,box.width*.4,3)
            assert sum(dark(p) for p in pixels(image,top))>box.width*.2,'horizontal border missing'
        verify(i)
        with self.assertRaises(AssertionError):verify(Image.new('RGB',i.size,'white'))
        with self.assertRaises(AssertionError):verify(Image.new('RGB',i.size,(254,226,226)))

    def test_browser_source_inner_parts_are_really_painted(self):
        r=draw(diagram('Browser',shape='browser'));node=next(e for e in r.trace if e.kind=='node');i=img(r)
        self.assertGreaterEqual(sum(e.kind=='node-part' for e in r.trace),5)
        # browser.ts chrome bar18; centers12+9*i,y9,r2.5, independently
        # specified source positions. A correct outer rectangle cannot fake it.
        for x in (12,21,30):
            self.assertTrue(dark(i.getpixel((round(node.box.x+x),round(node.box.y+9)))))
        divider=Box(node.box.x+5,node.box.y+17,node.box.width-10,3)
        self.assertGreater(sum(dark(p) for p in pixels(i,divider)),node.box.width/2)
        blank=Image.new('RGB',i.size,'white')
        self.assertEqual(sum(dark(p) for p in pixels(blank,divider)),0)

    def test_hachure_source_fill_is_stripes_not_solid_or_absent(self):
        d=diagram('Sketch',config={'look':'handDrawn','handDrawnSeed':42})
        d=replace(d,nodes=(replace(d.nodes[0],styles=('fill:red',)),))
        r=draw(d);node=next(e for e in r.trace if e.kind=='node')
        band=Box(node.box.x+8,node.box.y+5,node.box.width-16,5)
        p=pixels(img(r),band)
        self.assertGreater(sum(c[0]>170 and c[1]<120 and c[2]<120 for c in p),4)
        # Independent RoughJS public-generator paths captured before candidate
        # acceptance; replay at the same raster origin. Original pure-white-gap
        # assertion was disproved by source: both source and candidate had zero.
        receipt=json.loads((Path(__file__).parents[2]/'references/f014-canvas-assertions.json').read_text(encoding='utf8'))
        fixture=receipt['roughSourceFixture'];self.assertEqual((node.box.width,node.box.height),(180,51))
        c=Canvas(r.width,r.height);c.gpu=False;ctx=c.getContext('2d')
        ctx.fillStyle='white';ctx.fillRect(0,0,r.width,r.height);ctx.translate(node.box.x,node.box.y)
        for path in fixture['paths']:
            ctx.strokeStyle=path['stroke'];ctx.lineWidth=path['strokeWidth'];ctx.stroke(Path2D(path['d']))
        reference=Image.open(BytesIO(c.toBufferSync('png'))).convert('RGB')
        expected=pixels(reference,band)
        close=lambda a,b:max(abs(x-y) for x,y in zip(a,b))<=4
        self.assertGreaterEqual(sum(close(a,b) for a,b in zip(p,expected,strict=True)),len(p)*.97)
        self.assertGreater(len(set(expected)),5)
        # Solid red and white controls must both fail this actual hatch pattern.
        for color in ((255,0,0),(255,255,255)):
            self.assertLess(sum(close(color,b) for b in expected),len(expected)*.97)

    def test_handdrawn_source_solid_fill_handlers_remain_solid(self):
        # filledCircle.ts explicitly userNodeOverrides(fillStyle:'solid'),
        # independent of the general handDrawn hachure default.
        r=draw(diagram('',shape='filledCircle',config={'look':'handDrawn','handDrawnSeed':42}))
        node=next(e for e in r.trace if e.kind=='node')
        center=Box(node.box.x+node.box.width/2-3,node.box.y+node.box.height/2-3,6,6)
        self.assertGreaterEqual(sum(dark(p) for p in pixels(img(r),center)),32)
        # Source tag component metadata must preserve the semantic distinction;
        # actual component pixel evidence is covered by the source parts tests.
        tagged=draw(diagram('Tag',shape='taggedRect',config={'look':'handDrawn','handDrawnSeed':42}))
        self.assertTrue(any(part.fill_style=='solid' for part in tagged.measured[0].parts))

    def test_marker_circle_fill_stays_theme_color_custom_stroke(self):
        d=diagram('Start');other=FlowNode('B','End',SPAN)
        edge=FlowEdge('e','A','B',SPAN,marker_end='circle',styles=('stroke:red',))
        r=draw(replace(d,nodes=(*d.nodes,other),edges=(edge,)))
        marker=next(e for e in r.trace if e.kind=='arrow');self.assertEqual(marker.marker,'circle')
        p=pixels(img(r),marker.box)
        self.assertGreater(sum(dark(c) for c in p),4)
        self.assertGreater(sum(c[0]>180 and c[1]<100 and c[2]<100 for c in p),2)

    def test_none_cross_invisible_and_source_marker_color_pixels(self):
        for kind in ('none','point','circle','cross'):
            d=diagram('Start');edge=FlowEdge('e','A','B',SPAN,marker_end=kind)
            r=draw(replace(d,nodes=(*d.nodes,FlowNode('B','End',SPAN)),edges=(edge,)))
            markers=[e for e in r.trace if e.kind=='arrow']
            self.assertEqual(len(markers),0 if kind=='none' else 1)
            if markers:self.assertGreater(sum(dark(p) for p in pixels(img(r),markers[0].box)),2)
        d=replace(d,edges=(replace(edge,stroke='invisible'),))
        r=draw(d);self.assertFalse(any(e.kind in {'edge','arrow'} for e in r.trace))

    def test_engine_expansion_centers_original_shape_without_rescaling(self):
        d=diagram('Fixed',shape='diamond');a=draw(d);b=draw(d,extra_width=80)
        node_a=next(e for e in a.trace if e.kind=='node');node_b=next(e for e in b.trace if e.kind=='node')
        self.assertEqual((node_a.box.width,node_a.box.height),(node_b.box.width,node_b.box.height))
        self.assertEqual(a.measured,b.measured)
        e=next(e for e in b.trace if e.kind=='text');self.assertGreater(sum(dark(p) for p in pixels(img(b),e.box)),2)

    def test_spacing_transform_uses_real_native_measure_and_paint(self):
        cfg={'dompurifyConfig':{}}
        normal=draw(diagram('ab cd',config=cfg))
        styled=draw(diagram('<span style="letter-spacing:2px;word-spacing:5px;text-transform:uppercase">ab cd</span>',config=cfg))
        run=styled.measured[0].runs[0];self.assertEqual(run.text,'AB CD');self.assertEqual(float(run.letter_spacing.removesuffix('px')),2);self.assertEqual(float(run.word_spacing.removesuffix('px')),5)
        c=Canvas(1,1);c.gpu=False;ctx=c.getContext('2d');ctx.font='normal 400 14px "Recursive Variable", arial, sans-serif';ctx.textAlign='left';ctx.letterSpacing='2px';ctx.wordSpacing='5px'
        self.assertAlmostEqual(run.width,ctx.measureText('AB CD').width,places=4)
        self.assertGreater(run.width,normal.measured[0].runs[0].width+12)
        e=next(e for e in styled.trace if e.kind=='text');self.assertGreater(sum(dark(p) for p in pixels(img(styled),e.box)),4)

    def test_text_shadow_real_color_bounds_and_auto_hyphen_diagnostic(self):
        d=diagram('<span style="color:black;text-shadow:8px 4px 0 red">Shadow</span>',config={'dompurifyConfig':{}})
        r=draw(d);e=next(e for e in r.trace if e.kind=='text');p=pixels(img(r),e.box)
        self.assertGreater(sum(c[0]>170 and c[1]<100 and c[2]<100 for c in p),3)
        self.assertGreater(sum(dark(c) for c in p),3)
        self.assertGreaterEqual(e.box.x,0);self.assertLessEqual(e.box.x+e.box.width,r.width)
        with self.assertRaises(MermaidError) as caught:draw(diagram('<span style="hyphens:auto">hyphenation</span>',config={'dompurifyConfig':{}}))
        self.assertEqual(caught.exception.code,'UNSUPPORTED_THEME_CSS')

    def test_text_shadow_is_real_glyph_silhouette_not_a_rectangle(self):
        text='flowchart TD\nA["<span style=\'color:black;text-shadow:4px 2px 0 red;letter-spacing:2px;word-spacing:5px;text-transform:uppercase\'>ab cd</span>"]'
        r=render(text,backend='cpu',config={'fontFamily':'Arial','dompurifyConfig':{}})
        event=next(e for e in r.trace if e.kind=='text');self.assertEqual(event.text,'AB CD')
        x,baseline=event.points[0].x,event.points[0].y
        references=[]
        for faulty in (False,True):
            c=Canvas(r.width,r.height);c.gpu=False;ctx=c.getContext('2d')
            ctx.fillStyle='white';ctx.fillRect(0,0,r.width,r.height)
            # Literal source CSS operation, independent of product shadow helper.
            ctx.font='normal 400 14px Arial';ctx.textAlign='left';ctx.textBaseline='alphabetic';ctx.letterSpacing='2px';ctx.wordSpacing='5px'
            ctx.fillStyle='red'
            if faulty:
                m=ctx.measureText('AB CD');ctx.fillRect(x+4-m.actualBoundingBoxLeft,baseline+2-m.actualBoundingBoxAscent,m.actualBoundingBoxLeft+m.actualBoundingBoxRight,m.actualBoundingBoxAscent+m.actualBoundingBoxDescent)
            else:ctx.fillText('AB CD',x+4,baseline+2)
            ctx.fillStyle='black';ctx.fillText('AB CD',x,baseline)
            references.append(Image.open(BytesIO(c.toBufferSync('png'))).convert('RGB'))
        expected=pixels(references[0],event.box);observed=pixels(img(r),event.box)
        match=lambda a,b:sum(max(abs(x-y) for x,y in zip(p,q))<=4 for p,q in zip(a,b,strict=True))/len(a)
        self.assertGreaterEqual(match(observed,expected),.97,'shadow must retain glyph holes/whitespace')
        self.assertLess(match(pixels(references[1],event.box),expected),.97,'rectangle negative control must fail')
        self.assertGreater(sum(c[0]>180 and c[1]<100 and c[2]<100 for c in observed),5)

    def test_wrap_break_all_keep_all_and_manual_soft_hyphen(self):
        broken=draw(diagram('<span style="word-break:break-all">ABCDEFGHIJKLMNOPQRSTUVWXYZ</span>',config={'dompurifyConfig':{}}))
        self.assertGreater(len(broken.measured[0].lines),1)
        joined=''.join(e.text or '' for e in broken.trace if e.kind=='text');self.assertEqual(joined,'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        keep=draw(diagram('<span style="word-break:keep-all">中文中文中文中文中文中文中文中文中文中文</span>',config={'dompurifyConfig':{}}))
        self.assertEqual(len(keep.measured[0].lines),1)

    def test_math_and_media_controls_have_static_boundary_diagnostics(self):
        mathematical=CanvasSession('cpu').measure(diagram('$$x^2$$'))[0]
        self.assertTrue(any(run.kind=='math' and run.math_key for run in mathematical.runs))
        for text,code in (('<video src="clip.mp4"></video>','UNSUPPORTED_LABEL_RESOURCE'),('<audio src="clip.mp3"></audio>','UNSUPPORTED_LABEL_RESOURCE')):
            with self.subTest(text=text),self.assertRaises(MermaidError) as caught:CanvasSession('cpu').measure(diagram(text))
            self.assertEqual(caught.exception.code,code)

class LabellessPublicApiTests(unittest.TestCase):
    # Literal fixed handler dimensions, not generated by shape_geometry.
    # Source handlers set node.label='' (including choice/hourglass); fork
    # orientation is deliberately checked through a real LR ELK graph.
    CASES=(('sm-circ','stateStart',14,14,'TD'),('fr-circ','stateEnd',14,14,'TD'),
           ('f-circ','filledCircle',14,14,'TD'),('cross-circ','crossedCircle',60,60,'TD'),
           ('choice','choice',28,28,'TD'),('fork','forkJoin',10,70,'LR'),
           ('bolt','lightningBolt',35,70,'TD'),('anchor','anchor',2,2,'TD'),
           ('hourglass','hourglass',30,30,'TD'))

    def test_nine_source_labelless_shapes_through_public_api_and_real_elk(self):
        for name,canonical,width,height,direction in self.CASES:
            with self.subTest(shape=name):
                r=render(f'flowchart {direction}\nA@{{shape: {name}, label: "Ignored"}}',backend='cpu')
                self.assertTrue(r.layout.engine.startswith('pyelk/'))
                measured=r.measured[0];self.assertEqual((measured.width,measured.height),(width,height))
                self.assertEqual((measured.label_width,measured.label_height),(0,0))
                self.assertEqual(measured.lines,());self.assertEqual(measured.runs,())
                self.assertEqual(r.diagram.nodes[0].shape,canonical)
                self.assertFalse(any(e.kind=='text' and e.semantic_id=='A' for e in r.trace))
                node=next(e for e in r.trace if e.kind=='node' and e.semantic_id=='A')
                region=Box(node.box.x-2,node.box.y-2,node.box.width+4,node.box.height+4)
                self.assertGreater(sum(dark(p) for p in pixels(img(r),region)),0,'shape must still have actual native ink')

    def test_real_state_hollow_ring_and_filled_marker_pixels_with_dark_negative_control(self):
        # Source RoughSVG.draw paints fillSketch before the final ellipse path;
        # .node path CSS changes that later path's fill from presentation none
        # to opaque mainBkg. This is a visible content distinction, not trace.
        text='flowchart LR\nA@{shape:sm-circ,label:"Ignored"}\nB@{shape:fr-circ,label:"Ignored"}\nC@{shape:f-circ,label:"Ignored"}'
        r=render(text,backend='cpu',config={'look':'handDrawn','handDrawnSeed':42,'themeVariables':{'background':'#ffcccc'}})
        image=img(r);self.assertEqual(image.getpixel((0,0)),(255,204,204))
        nodes={e.semantic_id:e for e in r.trace if e.kind=='node'}
        def center_pixels(image,event):
            cx=math.floor(event.box.x+event.box.width/2);cy=math.floor(event.box.y+event.box.height/2)
            return pixels(image,Box(cx-2,cy-2,5,5)),image.getpixel((cx,cy))
        def hollow(image,event,ring=False):
            sample,center=center_pixels(image,event)
            assert min(center)>220,('hollow marker center lost',event.semantic_id,center)
            if ring:assert sum(dark(p) for p in sample)>4,'stateEnd inner ring missing'
            else:assert sum(min(p)>220 for p in sample)>=20,'stateStart center became a filled or hatched disk'
            border=pixels(image,Box(event.box.x-1,event.box.y-1,event.box.width+2,event.box.height+2))
            assert sum(dark(p) for p in border)>5,'hollow circle outline absent'
        hollow(image,nodes['A']);hollow(image,nodes['B'],True)
        sample,_=center_pixels(image,nodes['C']);self.assertGreaterEqual(sum(dark(p) for p in sample),20)
        self.assertEqual(nodes['A'].fill,'#ffffff');self.assertEqual(nodes['B'].fill,'#ffffff')
        # Reproduce the old QA failure visually: dark disks cannot satisfy the
        # same acceptance even if shape IDs/trace fonts/relations are correct.
        wrong=Image.new('RGB',image.size,'#28253d')
        for key,ring in (('A',False),('B',True)):
            with self.assertRaises(AssertionError):hollow(wrong,nodes[key],ring)

    def test_seeded_labelless_gallery_uses_real_elk_without_phantom_label_boxes(self):
        definitions=[f'N{i}@{{shape: {name}, label: "Ignored{i}"}}' for i,(name,*_) in enumerate(self.CASES)]
        connections=[f'N{i} --> N{i+1}' for i in range(len(self.CASES)-1)]
        text='flowchart TD\n'+'\n'.join(definitions+connections)
        config={'look':'handDrawn','handDrawnSeed':123}
        a=render(text,backend='cpu',config=config);b=render(text,backend='cpu',config=config)
        self.assertTrue(a.layout.engine.startswith('pyelk/'));self.assertEqual(a.data,b.data)
        self.assertEqual(len(a.measured),9);self.assertEqual(len(a.layout.edges),8)
        self.assertTrue(all(m.label_width==m.label_height==0 and m.lines==m.runs==() for m in a.measured))
        self.assertFalse(any(e.kind=='text' for e in a.trace))
        self.assertEqual(sum(e.kind=='node' for e in a.trace),9)
        self.assertGreater(sum(dark(p) for p in img(a).getdata()),40)

class ExportTests(unittest.TestCase):
    def test_empty_graph_is_source_padding_only_sixteen_by_sixteen(self):
        d=Flowchart('flowchart TD','TD',(),(),resolve_config())
        session=CanvasSession('cpu');m=session.measure(d);ann=session.measure_annotations(d)
        r=session.render(d,m,FlowLayout((),(),0,0,'test-only','empty'),annotations=ann)
        self.assertEqual((r.width,r.height),(16,16));self.assertEqual(img(r).size,(16,16))
        self.assertEqual(tuple(e.kind for e in r.trace),('viewport',))

    def test_encoded_raster_formats_density_dimensions_and_real_pixels(self):
        for format,magic,pillow in (('png',b'\x89PNG','PNG'),('jpg',b'\xff\xd8','JPEG'),('jpeg',b'\xff\xd8','JPEG'),('webp',b'RIFF','WEBP')):
            with self.subTest(format=format):
                r=draw(diagram('Encoded'),format=format,options=ExportOptions(density=2,quality=.85))
                self.assertTrue(r.data.startswith(magic));i=Image.open(BytesIO(r.data));i.load();self.assertEqual(i.format,pillow);self.assertEqual(i.size,(r.width,r.height))
                self.assertGreater(len(set(i.convert('RGB').getdata())),5)
                e=next(e for e in r.trace if e.kind=='text')
                scaled=Box(e.box.x*2,e.box.y*2,e.box.width*2,e.box.height*2)
                self.assertGreater(sum(dark(p) for p in pixels(i.convert('RGB'),scaled)),5,'encoded format must contain actual glyph ink')
                self.assertEqual(r.width%2,0);self.assertEqual(r.height%2,0)
                self.assertEqual(r.mime,{'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp'}[format])

    def test_svg_actual_vector_content_page_dimensions_and_outlined_text(self):
        plain=draw(diagram('VectorWord'),format='svg');outlined=draw(diagram('VectorWord'),format='svg',options=ExportOptions(outline=True))
        for r in (plain,outlined):
            root=ET.fromstring(r.data);self.assertTrue(root.tag.endswith('svg'))
            self.assertAlmostEqual(float(re.match(r'[\d.]+',root.attrib['width'])[0]),r.width)
            self.assertAlmostEqual(float(re.match(r'[\d.]+',root.attrib['height'])[0]),r.height)
            self.assertGreater(sum(e.tag.endswith('path') for e in root.iter()),0)
        self.assertIn(b'VectorWord',plain.data)
        self.assertNotIn(b'>VectorWord<',outlined.data)
        self.assertGreater(outlined.data.count(b'<path'),plain.data.count(b'<path'))

    def test_pdf_actual_page_signature_dimensions_and_paint_streams(self):
        r=draw(diagram('PdfWord'),format='pdf');self.assertTrue(r.data.startswith(b'%PDF-'));self.assertIn(b'%%EOF',r.data[-100:])
        box=re.search(rb'/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)',r.data);self.assertIsNotNone(box)
        self.assertAlmostEqual(float(box[1]),r.width,delta=.1);self.assertAlmostEqual(float(box[2]),r.height,delta=.1)
        streams=[]
        for stream in re.findall(rb'stream\r?\n(.*?)\r?\nendstream',r.data,re.S):
            try:streams.append(zlib.decompress(stream))
            except zlib.error:streams.append(stream)
        self.assertTrue(any(b'BT' in stream and (b'Tj' in stream or b'TJ' in stream) for stream in streams),'PDF must contain actual text operators, not only a blank page or outer shapes')

    def test_export_invalid_options_formats_and_matte(self):
        for option in (ExportOptions(quality=2),ExportOptions(density=0),ExportOptions(density=True),ExportOptions(outline='yes')):
            with self.subTest(option=option),self.assertRaises(MermaidError) as caught:draw(diagram(),options=option)
            self.assertEqual(caught.exception.code,'INVALID_EXPORT_OPTIONS')
        with self.assertRaises(MermaidError) as caught:draw(diagram(),format='raw')
        self.assertEqual(caught.exception.code,'UNSUPPORTED_FORMAT')
        d=diagram('Matte');d=replace(d,config=replace(d.config,background='transparent'))
        r=draw(d,format='jpg',options=ExportOptions(matte='#ff0000'));self.assertTrue(r.data.startswith(b'\xff\xd8'))
        color=img(r).getpixel((0,0));self.assertGreater(color[0],225);self.assertLess(max(color[1:]),30)

    def test_native_backend_profiles_no_gpu_fallback(self):
        for backend in ('cpu','auto','gpu'):
            with self.subTest(backend=backend):
                try:r=draw(diagram('Backend'),backend=backend)
                except MermaidError as exc:
                    if backend=='gpu':self.assertEqual(exc.code,'GPU_UNAVAILABLE');continue
                    raise
                renderer=dict(r.backend)['renderer'];self.assertEqual(renderer,'CPU' if backend=='cpu' else 'GPU' if backend=='gpu' else renderer)
                e=next(e for e in r.trace if e.kind=='text');self.assertGreater(sum(dark(p) for p in pixels(img(r),e.box)),2)

if __name__=='__main__':unittest.main()
