"""Independent pinned-source shape registration, analytical geometry and ink tests.

Expectations below are literals/formulas from Mermaid shape handlers, not
candidate geometry output. Native Path2D is an independent public geometry
consumer; no candidate flatten_path/intersection helper supplies expected data.
"""
from __future__ import annotations
from dataclasses import asdict, replace
import copy
import json
import math
import os
from pathlib import Path
import re
import unittest
from py_mermaid.config import resolve_config
from py_mermaid.geometry.shapes import shape_geometry, shape_outline_intersection
from py_mermaid.geometry.shape_registry import canonical_shape, is_valid_shape, METADATA_SHAPES
from py_mermaid.model.flowchart import Box, Point, MermaidError

# Exact shapesDefs records and alias arrays from fixed upstream shapes.ts.
SOURCE_DEFINITIONS = (('rect', 'squareRect', ('proc', 'process', 'rectangle', 'squareRect')),
 ('rounded', 'roundedRect', ('event', 'roundedRect')),
 ('stadium', 'stadium', ('terminal', 'pill')),
 ('fr-rect', 'subroutine', ('subprocess', 'subproc', 'framed-rectangle', 'subroutine')),
 ('cyl', 'cylinder', ('db', 'database', 'cylinder')),
 ('datastore', 'datastore', ('data-store',)),
 ('folder', 'folder', ('directory',)),
 ('bucket', 'bucket', ()),
 ('console', 'consoleWindow', ()),
 ('browser', 'browser', ()),
 ('person', 'person', ()),
 ('circle', 'circle', ('circ',)),
 ('bang', 'bang', ('bang',)),
 ('cloud', 'cloud', ('cloud',)),
 ('diam', 'question', ('decision', 'diamond', 'question')),
 ('hex', 'hexagon', ('hexagon', 'prepare')),
 ('lean-r', 'lean_right', ('lean-right', 'in-out', 'lean_right')),
 ('lean-l', 'lean_left', ('lean-left', 'out-in', 'lean_left')),
 ('trap-b', 'trapezoid', ('priority', 'trapezoid-bottom', 'trapezoid')),
 ('trap-t', 'inv_trapezoid', ('manual', 'trapezoid-top', 'inv-trapezoid', 'inv_trapezoid')),
 ('dbl-circ', 'doublecircle', ('double-circle', 'doublecircle')),
 ('text', 'text', ()),
 ('notch-rect', 'card', ('card', 'notched-rectangle')),
 ('lin-rect', 'shadedProcess', ('lined-rectangle', 'lined-process', 'lin-proc', 'shaded-process')),
 ('sm-circ', 'stateStart', ('start', 'small-circle', 'stateStart')),
 ('fr-circ', 'stateEnd', ('stop', 'framed-circle', 'stateEnd')),
 ('fork', 'forkJoin', ('join', 'forkJoin')),
 ('hourglass', 'hourglass', ('hourglass', 'collate')),
 ('brace', 'curlyBraceLeft', ('comment', 'brace-l')),
 ('brace-r', 'curlyBraceRight', ()),
 ('braces', 'curlyBraces', ()),
 ('bolt', 'lightningBolt', ('com-link', 'lightning-bolt')),
 ('doc', 'waveEdgedRectangle', ('doc', 'document')),
 ('delay', 'halfRoundedRectangle', ('half-rounded-rectangle',)),
 ('h-cyl', 'tiltedCylinder', ('das', 'horizontal-cylinder')),
 ('lin-cyl', 'linedCylinder', ('disk', 'lined-cylinder')),
 ('curv-trap', 'curvedTrapezoid', ('curved-trapezoid', 'display')),
 ('div-rect', 'dividedRectangle', ('div-proc', 'divided-rectangle', 'divided-process')),
 ('tri', 'triangle', ('extract', 'triangle')),
 ('win-pane', 'windowPane', ('internal-storage', 'window-pane')),
 ('f-circ', 'filledCircle', ('junction', 'filled-circle')),
 ('notch-pent', 'trapezoidalPentagon', ('loop-limit', 'notched-pentagon')),
 ('flip-tri', 'flippedTriangle', ('manual-file', 'flipped-triangle')),
 ('sl-rect', 'slopedRect', ('manual-input', 'sloped-rectangle')),
 ('docs', 'multiWaveEdgedRectangle', ('documents', 'st-doc', 'stacked-document')),
 ('st-rect', 'multiRect', ('procs', 'processes', 'stacked-rectangle')),
 ('bow-rect', 'bowTieRect', ('stored-data', 'bow-tie-rectangle')),
 ('cross-circ', 'crossedCircle', ('summary', 'crossed-circle')),
 ('tag-doc', 'taggedWaveEdgedRectangle', ('tag-doc', 'tagged-document')),
 ('tag-rect', 'taggedRect', ('tagged-rectangle', 'tag-proc', 'tagged-process')),
 ('flag', 'waveRectangle', ('paper-tape',)),
 ('odd', 'rect_left_inv_arrow', ('rect_left_inv_arrow',)),
 ('lin-doc', 'linedWaveEdgedRect', ('lined-document',)))
REACHABLE_INTERNAL = ("state","choice","note","composite","icon","anchor")
SOURCE_CANONICAL = {"squareRect":"square","roundedRect":"round","question":"diamond","rect_left_inv_arrow":"odd"}
LABELLESS = frozenset(("stateStart","stateEnd","filledCircle","crossedCircle","choice","forkJoin","lightningBolt","anchor","hourglass"))
VIRTUAL = frozenset(("text","datastore","curlyBraceLeft","curlyBraceRight","curlyBraces"))


def config(look="neo"):
    return resolve_config({"theme":"base","look":look,"flowchart":{"padding":8,"minNodeWidth":0}})


def native(path):
    from py_skia_canvas import Path2D
    return Path2D(path)


def box_contains(outer,inner,tol=1e-4):
    return outer.x-tol<=inner.x and outer.y-tol<=inner.y and inner.x+inner.width<=outer.x+outer.width+tol and inner.y+inner.height<=outer.y+outer.height+tol


def native_bounds(path):
    bounds=native(path).bounds
    return Box(bounds['left'],bounds['top'],bounds['width'],bounds['height'])


def cap_image_probes(result):
    """Independent source cap locations, tested against actual PNG pixels.

    Source factory appends its inner arc at the RIGHT outer chord. After bbox
    normalization the inner tangent is W-2*rx; the counterfactual left tangent
    is2*rx. Large minNodeWidth keeps short real text away from both probes.
    """
    from io import BytesIO
    from PIL import Image
    measured=result.measured[0]
    event=next(event for event in result.trace if event.kind=='node' and event.semantic_id=='A')
    h=measured.height;rx=(h/2)/(2.5+h/50)
    image=Image.open(BytesIO(result.data)).convert('RGBA')
    background=Image.new('RGBA',image.size,'white');background.alpha_composite(image)
    rgb=background.convert('RGB')
    def dark_at(local_x):
        x=event.box.x+local_x;y=event.box.y+h/2
        crop=rgb.crop((math.floor(x-2),math.floor(y-2),math.ceil(x+2),math.ceil(y+2)))
        return sum(1 for red,green,blue in crop.getdata() if min(red,green,blue)<110)
    return dark_at(measured.width-2*rx),dark_at(2*rx)


def cap_render(look):
    from py_mermaid import render
    return render('flowchart LR\nA@{shape: h-cyl, label: "Cap"}',backend='cpu',config={
      'look':look,'theme':'base','handDrawnSeed':123,'flowchart':{'padding':8,'minNodeWidth':160},
      'themeVariables':{'mainBkg':'#ffffff','nodeBorder':'#000000','lineColor':'#000000',
                        'textColor':'#000000','background':'#ffffff','useGradient':False,'dropShadow':'none'}})


def save_cap_image(result,filename):
    folder=os.environ.get('PY_MERMAID_CAP_QA_DIR')
    if folder:
        directory=Path(folder);directory.mkdir(parents=True,exist_ok=True)
        (directory/filename).write_bytes(result.data)


class SourceShapeTests(unittest.TestCase):
    def test_s01_exact_53_definitions_and_alias_equivalence(self):
        self.assertEqual(len(SOURCE_DEFINITIONS),53)
        for short,handler,aliases in SOURCE_DEFINITIONS:
            expected=SOURCE_CANONICAL.get(handler,handler)
            for alias in (short,*aliases):
                with self.subTest(shape=short,alias=alias):
                    self.assertTrue(is_valid_shape(alias))
                    self.assertEqual(canonical_shape(alias),expected)

    def test_s02_metadata_reachable_denominator_and_internal_case_barrier(self):
        expected=set(REACHABLE_INTERNAL)
        for short,handler,aliases in SOURCE_DEFINITIONS:
            expected.update(alias for alias in (short,*aliases) if alias==alias.lower() and '_' not in alias)
        self.assertEqual(set(METADATA_SHAPES),expected)
        for name in REACHABLE_INTERNAL:self.assertTrue(is_valid_shape(name))
        for short,handler,aliases in SOURCE_DEFINITIONS:
            for alias in (short,*aliases):
                self.assertEqual(canonical_shape(canonical_shape(alias)),canonical_shape(alias),alias)
        for internal in ('imageSquare','iconCircle','iconSquare','iconRounded','collapsedGroup'):
            self.assertTrue(is_valid_shape(internal))
            self.assertNotIn(internal,METADATA_SHAPES)

    def test_s03_ellipse_upstream_missing_and_unknown_shape_explicit(self):
        with self.assertRaises(MermaidError) as error:shape_geometry('ellipse',40,20,config())
        self.assertEqual(error.exception.code,'UPSTREAM_SHAPE_MISSING')
        with self.assertRaises(MermaidError):shape_geometry('invented-shape',40,20,config())
        for width,height in ((-1,20),(40,-1),(math.nan,20),(40,math.inf)):
            with self.subTest(width=width,height=height),self.assertRaises(MermaidError):shape_geometry('rect',width,height,config())

    def test_s04_all_reachable_handlers_finite_pure_and_nonempty_silhouette(self):
        for look in ('classic','neo'):
            cfg=config(look);before=copy.deepcopy(cfg)
            for name in tuple(row[0] for row in SOURCE_DEFINITIONS)+REACHABLE_INTERNAL+('collapsedGroup','imageSquare','iconCircle','iconSquare','iconRounded'):
                with self.subTest(look=look,shape=name):
                    shape=shape_geometry(name,40,20,cfg,asset_size=(48,32),metadata=(("w",48),("h",32),("icon","test:icon")))
                    self.assertTrue(all(math.isfinite(v) and v>0 for v in (shape.width,shape.height)))
                    self.assertTrue(box_contains(Box(0,0,shape.width,shape.height),shape.label_box))
                    self.assertEqual(cfg,before)
                    json.dumps(asdict(shape))
                    for path in (shape.outline,*shape.details,*(part.path for part in shape.parts)):
                        bounds=native_bounds(path)
                        self.assertTrue(all(math.isfinite(v) for v in (bounds.x,bounds.y,bounds.width,bounds.height)))
                    if canonical_shape(name) not in VIRTUAL:
                        self.assertTrue(shape.outline,name)
                        bounds=native_bounds(shape.outline)
                        self.assertGreater(bounds.width*bounds.height,0)

    def test_s05_source_fixed_label_suppression_sizes_and_fork_direction(self):
        expected={'choice':(28,28),'sm-circ':(14,14),'f-circ':(14,14),'fr-circ':(14,14),'anchor':(2,2),'cross-circ':(60,60),'hourglass':(30,30),'bolt':(35,70)}
        for name,size in expected.items():
            with self.subTest(shape=name):
                shape=shape_geometry(name,500,300,config())
                self.assertEqual((shape.width,shape.height),size)
                self.assertEqual((shape.label_box.width,shape.label_box.height),(0,0))
        for direction in ('TD','TB','LR','RL','BT'):
            shape=shape_geometry('fork',500,300,config(),direction=direction)
            self.assertEqual((shape.width,shape.height),(10,70) if direction in ('LR','RL') else (70,10))

    def test_s06_circle_diagonal_and_double_ring_padding(self):
        for look,padding,gap in (('neo',16,12),('classic',8,5)):
            cfg=config(look)
            circle=shape_geometry('circle',30,40,cfg)
            self.assertAlmostEqual(circle.width,50+(32 if look=='neo' else 8))
            self.assertAlmostEqual(circle.height,circle.width)
            double=shape_geometry('dbl-circ',30,40,cfg)
            self.assertAlmostEqual(double.width,50+2*padding+2*gap)
            inner=[native_bounds(path) for path in (*double.details,*(part.path for part in double.parts))]
            self.assertTrue(any(abs(box.width-(50+2*padding))<.01 for box in inner))

    def test_s07_card_text_and_note_numeric_padding_from_handlers(self):
        for look,expected in (('classic',(60,28)),('neo',(96,68))):
            card=shape_geometry('notch-rect',40,20,config(look))
            self.assertEqual((card.width,card.height),expected)
            path=native(card.outline)
            self.assertFalse(path.contains(1,1))
            self.assertTrue(path.contains(14,1))
        text=shape_geometry('text',40,20,config('classic'))
        self.assertEqual((text.width,text.height),(48,28))
        note=shape_geometry('note',40,20,config('classic'))
        self.assertEqual((note.width,note.height),(56,36))

    def test_s08_triangles_and_pentagon_have_source_silhouette(self):
        for name,up in (('tri',True),('flip-tri',False)):
            with self.subTest(shape=name):
                shape=shape_geometry(name,40,20,config());path=native(shape.outline);w,h=shape.width,shape.height
                self.assertFalse(path.contains(w*.05,h*(.05 if up else .95)))
                self.assertTrue(path.contains(w*.5,h*.5))
                self.assertTrue(path.contains(w*.1,h*(.95 if up else .05)))
        shape=shape_geometry('notch-pent',40,20,config());path=native(shape.outline)
        self.assertGreater(shape.width,40)
        self.assertGreater(shape.height,20)
        self.assertTrue(path.contains(shape.width/2,shape.height/2))

    def test_s09_odd_and_hourglass_are_not_rectangle_substitutes(self):
        shape=shape_geometry('odd',40,20,config());path=native(shape.outline)
        self.assertFalse(path.contains(shape.height/16,shape.height/2))
        self.assertTrue(path.contains(shape.width*.75,shape.height/2))
        hourglass=shape_geometry('hourglass',40,20,config());path=native(hourglass.outline)
        self.assertFalse(path.contains(2,15))
        self.assertTrue(path.contains(15,2))

    def test_s10_curved_shapes_and_lined_shapes_have_distinct_components(self):
        for name in ('cloud','bang','delay','h-cyl','curv-trap','lin-cyl'):
            with self.subTest(shape=name):
                shape=shape_geometry(name,40,20,config())
                self.assertRegex(shape.outline,'' + r'[CQAcqa]')
        for name in ('fr-rect','lin-rect','div-rect','win-pane','cross-circ','fr-circ','tag-rect','tag-doc','lin-doc','lin-cyl','console','browser','docs','st-rect'):
            with self.subTest(shape=name):
                shape=shape_geometry(name,40,20,config())
                self.assertTrue(shape.details or shape.parts,'Missing source inner/stack/decoration path: '+name)
        # Wave handlers use generateFullSineWavePoints + createPathFromPoints,
        # so their source outline is sampled L segments, not C/Q/A commands.
        # Their complete 50-step phase/extent is independently checked in S15.

    def test_s11_label_corners_fit_painted_source_container(self):
        exempt=VIRTUAL|LABELLESS|{'icon','iconCircle','iconSquare','iconRounded','imageSquare'}
        for short,handler,aliases in SOURCE_DEFINITIONS:
            if SOURCE_CANONICAL.get(handler,handler) in exempt:continue
            with self.subTest(shape=short):
                shape=shape_geometry(short,40,20,config());path=native(shape.outline);b=shape.label_box
                self.assertAlmostEqual(b.width,40)
                self.assertAlmostEqual(b.height,20)
                for x in (b.x+.01,b.x+b.width-.01):
                    for y in (b.y+.01,b.y+b.height-.01):
                        self.assertTrue(path.contains(x,y),(short,x,y,'label clipped by source silhouette'))

    def test_s12_all_outline_approaches_axis_and_nonaxis_match_native_ink(self):
        names=tuple(row[0] for row in SOURCE_DEFINITIONS)+('state','choice','note','composite','anchor')
        for name in names:
            shape=shape_geometry(name,40,20,config());kind=canonical_shape(name)
            if kind in VIRTUAL:continue
            path=native(shape.outline);w,h=shape.width,shape.height;box=Box(13,17,w,h)
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(-1,-1),(1,-1)):
                with self.subTest(shape=name,approach=(dx,dy)):
                    length=math.hypot(dx,dy);ux,uy=dx/length,dy/length
                    scale=min(w/2/abs(ux) if ux else math.inf,h/2/abs(uy) if uy else math.inf)
                    port=Point(box.x+w/2+ux*scale,box.y+h/2+uy*scale)
                    toward=Point(port.x+ux*max(w,h),port.y+uy*max(w,h))
                    hit=shape_outline_intersection(kind,box,port,toward,config=config(),outline=shape.outline)
                    self.assertTrue(math.isfinite(hit.x) and math.isfinite(hit.y))
                    x,y=hit.x-box.x,hit.y-box.y
                    # At a true silhouette, arbitrarily close native samples
                    # cannot all agree as inside or all agree as outside.
                    probes=[path.contains(x+math.cos(a)*.15,y+math.sin(a)*.15) for a in (0,math.pi/2,math.pi,3*math.pi/2)]
                    self.assertTrue(any(probes),(name,hit,'not near painted contour'))
                    self.assertFalse(all(probes),(name,hit,'intersection inside solid fill'))
                    if dx==0:self.assertAlmostEqual(hit.x,port.x,places=5)
                    if dy==0:self.assertAlmostEqual(hit.y,port.y,places=5)
                    if dx and dy:
                        self.assertAlmostEqual((hit.x-box.x-w/2)*dy,(hit.y-box.y-h/2)*dx,places=4)

    def test_s13_analytical_diamond_circle_and_round_intersections(self):
        cfg=config()
        for name in ('diamond','circle','round'):
            shape=shape_geometry(name,40,20,cfg);w,h=shape.width,shape.height;box=Box(10,30,w,h)
            for dx,dy in ((1,1),(-1,1),(1,-1),(-1,-1)):
                center=Point(box.x+w/2,box.y+h/2);toward=Point(center.x+dx*1000,center.y+dy*1000)
                hit=shape_outline_intersection(name,box,center,toward,config=cfg,outline=shape.outline)
                if name=='diamond':self.assertAlmostEqual(abs(hit.x-center.x)/(w/2)+abs(hit.y-center.y)/(h/2),1,places=4)
                elif name=='circle':self.assertAlmostEqual(math.hypot(hit.x-center.x,hit.y-center.y),w/2,delta=.02)
                else:self.assertTrue(box_contains(box,Box(hit.x,hit.y,0,0)))

    def test_s14_resources_and_decorations_keep_pure_label_ownership(self):
        for name in ('icon','iconCircle','iconSquare','iconRounded','imageSquare'):
            with self.subTest(shape=name):
                metadata=(("w",80),("h",40),("pos","b"),("icon","demo:shape"),("img","offline-key"))
                before=copy.deepcopy(metadata)
                shape=shape_geometry(name,30,12,config(),metadata=metadata,asset_size=(80,40))
                self.assertEqual(metadata,before)
                self.assertTrue(box_contains(Box(0,0,shape.width,shape.height),shape.label_box))
                self.assertEqual((shape.label_box.width,shape.label_box.height),(30,12))
                self.assertGreaterEqual(shape.width,80)
                self.assertGreaterEqual(shape.height,40)
                json.dumps(asdict(shape))

    def test_s15_source_fifty_step_wave_phase_height_and_stacked_outer_boundary(self):
        # Literal source inputs: label40x20, neo16/12, node.padding8. The
        # references construct source points before translating the bbox;
        # no candidate helper or candidate result generates expectations.
        cfg=config();p=8;lw,lh=40,20
        def sine(x1,y1,x2,y2,amplitude,cycles):
            return [(x1+(x2-x1)*i/50,(y1+y2)/2+amplitude*math.sin(2*math.pi*cycles*i/50)) for i in range(51)]
        references={}
        for name in ('doc','lin-doc','tag-doc'):
            w,h=(lw+2*p,lh+2*p) if name=='tag-doc' else (lw+32,lh+24)
            amplitude=h/8 if name=='tag-doc' else h/4
            final=h+amplitude;left=-w/2*(1.1 if name!='doc' else 1);right=-left
            wave=sine(left,final/2,right,final/2,amplitude,.8)
            points=[(left,final/2),*wave,(right,-final/2),(left,-final/2)]
            references[name]=(points,[(x,y-amplitude/2) for x,y in points],
                (p if name=='doc' else p+.075*w if name=='lin-doc' else p+.05*w,
                 p+amplitude/2 if name=='tag-doc' else p))
        w,h=lw+32,lh+20;amplitude=h/8;final=h+2*amplitude
        bottom=sine(-w/2,final/2,w/2,final/2,amplitude,1)
        top=sine(w/2,-final/2,-w/2,-final/2,amplitude,-1)
        points=[(-w/2,final/2),*bottom,(w/2,-final/2),*top]
        minimum=min(y for x,y in points)
        references['flag']=(points,points,((w-lw)/2,-lh/2-minimum))
        w,h=lw+32,lh+36;amplitude=h/4;final=h+amplitude/2;x,y=-w/2,-final/2;offset=10
        wave=sine(x-offset,y+final+offset,x+w-offset,y+final+offset,amplitude,.8)
        last_y=wave[-1][1]
        points=[(x-offset,y+offset),(x-offset,y+final+offset),*wave,
          (x+w-offset,last_y-offset),(x+w,last_y-offset),(x+w,last_y-2*offset),
          (x+w+offset,last_y-2*offset),(x+w+offset,y-offset),(x+offset,y-offset),
          (x+offset,y),(x,y),(x,y+offset)]
        # Source shape transform -A/2 acts on shape only, not sibling label.
        references['docs']=(points,[(a,b-amplitude/2) for a,b in points],
          (-lw/2-offset-min(a for a,b in points),-lh/2+offset-amplitude-min(b-amplitude/2 for a,b in points)))
        for name,(original,transformed,label_origin) in references.items():
            with self.subTest(shape=name):
                left=min(x for x,y in transformed);top=min(y for x,y in transformed)
                width=max(x for x,y in transformed)-left;height=max(y for x,y in transformed)-top
                shape=shape_geometry(name,lw,lh,cfg);path=native(shape.outline)
                self.assertAlmostEqual(shape.width,width,delta=.01)
                self.assertAlmostEqual(shape.height,height,delta=.01)
                self.assertAlmostEqual(shape.label_box.x,label_origin[0],delta=.01)
                self.assertAlmostEqual(shape.label_box.y,label_origin[1],delta=.01)
                # Source 51 wave sample vertices must survive, including phase
                # at .8 cycles. Checks geometry, not merely command spelling.
                actual=[(float(a),float(b)) for a,b in re.findall(r'[ML]\s*([+-]?[\d.eE-]+)[ ,]+([+-]?[\d.eE-]+)',shape.outline)]
                for a,b in transformed:
                    expected=(a-left,b-top)
                    self.assertTrue(any(math.hypot(px-expected[0],py-expected[1])<.01 for px,py in actual),(name,expected,'source sample/outer step missing'))
                self.assertGreaterEqual(len(actual),51)
                if name=='docs':
                    # Distinct upper front-card area lies outside the old
                    # back-document-only outline and must be part of ink.
                    self.assertTrue(path.contains(width-2,2))

    def test_s16_horizontal_cylinder_right_chord_from_source_factory_all_looks(self):
        # tiltedCylinder.ts createCylinderPathD appends M(width,-height),
        # then sweep0 down the RIGHT chord. In handDrawn the inner path is
        # separately placed at width/2; only the outer receives -width/2.
        # Both yield the same normalized right-cap tangent, not a left cap.
        for look,padding in (('classic',4),('neo',12),('handDrawn',4)):
            with self.subTest(look=look):
                shape=shape_geometry('h-cyl',80,24,config(look))
                h=24+padding;ry=h/2;rx=ry/(2.5+h/50)
                body_width=80+rx+padding;expected_width=body_width+2*rx
                self.assertAlmostEqual(shape.height,h)
                self.assertAlmostEqual(shape.width,expected_width)
                components=[native_bounds(path) for path in (*shape.details,*(part.path for part in shape.parts))]
                self.assertTrue(components)
                # Source inner arc fills the right half of the body-ending
                # ellipse. These bounds come from source factory coordinate
                # transforms and an independent native path consumer.
                expected=Box(body_width,0,rx,h)
                self.assertTrue(any(abs(b.x-expected.x)<.01 and abs(b.y)<.01 and abs(b.width-rx)<.01 and abs(b.height-h)<.01 for b in components))
                self.assertFalse(any(b.x<expected_width/2 for b in components),'Unexpected mirrored left inner cap')

    def test_s17_horizontal_cylinder_actual_api_right_ink_left_blank_all_looks(self):
        for look in ('classic','neo','handDrawn'):
            with self.subTest(look=look):
                result=cap_render(look)
                right,left=cap_image_probes(result)
                save_cap_image(result,'right-cap-'+look+'.png')
                self.assertGreater(right,0,'Source right inner arc must have actual PNG ink')
                self.assertEqual(left,0,'Source has no mirrored inner arc on the left')
                self.assertEqual(result.diagram.nodes[0].shape,'tiltedCylinder')
                self.assertTrue(result.layout.engine.startswith('pyelk/'))

    def test_s18_cap_png_guard_detects_explicit_left_cap_fault_through_real_api(self):
        # Deliberately inject the original directional fault at the measured
        # pure geometry boundary, then use the REAL public API/ELK/Canvas. The
        # pixel guard must detect it; a trace or path metadata-only assertion
        # cannot satisfy this negative control.
        from unittest.mock import patch
        from py_mermaid.model.flowchart import ShapePart
        import py_mermaid.rendering.skia.session as adapter
        original=adapter.shape_geometry
        def wrong_left_cap(kind,lw,lh,cfg,**kwargs):
            value=original(kind,lw,lh,cfg,**kwargs)
            if canonical_shape(kind)=='tiltedCylinder':
                h=value.height;rx=(h/2)/(2.5+h/50)
                fault=ShapePart(f'M {rx} 0 A {rx} {h/2} 0 0 1 {rx} {h}')
                return replace(value,parts=(fault,))
            return value
        for look in ('classic','neo','handDrawn'):
            with self.subTest(look=look),patch.object(adapter,'shape_geometry',wrong_left_cap):
                result=cap_render(look)
                right,left=cap_image_probes(result)
                save_cap_image(result,'injected-left-cap-'+look+'.png')
                self.assertGreater(left,0,'Negative control must actually paint erroneous left inner arc')
                self.assertEqual(right,0,'Guard must reject missing source right inner arc')


if __name__=='__main__':unittest.main()
