"""Independent fixed-source regressions for manual P4 blockers.

Sources: c4ShapeAdapter.ts/buildC4Node, c4LabelHelper.ts SECTION_GAP,
c4/styles.js per-type CSS, drawRect.ts center-ray intersection,
block/renderHelpers.ts positionNode and blockArrow.ts natural outline,
classBox.ts styles2String label color, packet/styles.ts and treeView/styles.ts.
No oracle/candidate output is used to generate expected values.
"""
import json
from pathlib import Path
import unittest
from .test_paint_contracts import picture,paths,visible
from py_mermaid.geometry.path_geometry import path_bounds,flatten_path

class ManualVisualSourceRegressions(unittest.IsolatedAsyncioTestCase):
    async def test_c4_horizontal_edges_begin_and_end_at_actual_node_boundary(self):
        r=await picture('C4Context\nSystem(a,"Alpha")\nSystem(b,"Beta")\nRel(a,b,"Uses")')
        a=path_bounds(paths(r,id='a')[0].path);b=path_bounds(paths(r,id='b')[0].path)
        edge=next(e for e in r.trace if e.semantic_id=='c4Rel0' and e.path)
        segments=flatten_path(edge.path);start=segments[0][0];end=segments[-1][-1]
        self.assertAlmostEqual(start.x,a.x+a.width,places=4);self.assertAlmostEqual(end.x,b.x,places=4)
        self.assertGreater(end.x,start.x)
        label=next(e for e in r.trace if e.semantic_id=='c4Rel0' and e.text)
        self.assertGreater(label.box.x,a.x+a.width);self.assertLess(label.box.x+label.box.width,b.x)
        self.assertIn('Uses',visible(r))
    async def test_c4_source_min_width_and_section_font_ratios(self):
        r=await picture('C4Context\nSystem(a,"Alpha","Description")')
        body=path_bounds(paths(r,id='a')[0].path);self.assertGreaterEqual(body.width,216)
        name=next(e for e in r.trace if e.semantic_id=='a' and e.text=='Alpha')
        stereotype=next(e for e in r.trace if e.semantic_id=='a' and e.text and 'Software System' in e.text)
        description=next(e for e in r.trace if e.semantic_id=='a' and e.text=='Description')
        self.assertEqual(name.font_size,14);self.assertEqual(name.font_weight,'bold')
        self.assertAlmostEqual(stereotype.font_size,10.5);self.assertAlmostEqual(description.font_size,11.48)
    async def test_c4_css_percentage_inherits_svg_parent_not_property_default(self):
        r=await picture('C4Context\nSystem(a,"Alpha","Description")',{'theme':'base','themeVariables':{'fontSize':'20px'},'c4':{'systemFontSize':'150%'}})
        name=next(e for e in r.trace if e.text=='Alpha');typ=next(e for e in r.trace if e.text and 'Software' in e.text)
        self.assertEqual(name.font_size,30);self.assertEqual(typ.font_size,22.5)
    async def test_all_fifteen_natural_arrow_outlines_center_on_their_labels(self):
        cases=json.loads(Path(__file__).parents[1].joinpath('cases-A.json').read_text(encoding='utf-8'))['cases']
        case=next(c for c in cases if c['id']=='A-block-all-arrow-factories');r=await picture(case['source'],case['config'])
        for index in range(15):
            with self.subTest(index=index):
                id='a'+str(index);shape=path_bounds(paths(r,id=id)[0].path);label=next(e for e in r.trace if e.semantic_id==id and e.text)
                self.assertAlmostEqual(shape.x+shape.width/2,label.box.x+label.box.width/2,delta=2)
                self.assertGreaterEqual(label.box.x,shape.x-1);self.assertLessEqual(label.box.x+label.box.width,shape.x+shape.width+1)
    async def test_classdef_color_inherits_to_label_without_recoloring_fill(self):
        r=await picture('classDiagram\nclass A:::highlight\nclassDef highlight fill:#ffeeee,color:#990000\nstyle A stroke:#112233')
        label=next(e for e in r.trace if e.semantic_id=='A' and e.text=='A');body=paths(r,id='A')[0]
        self.assertEqual(label.color.lower(),'#990000');self.assertEqual(body.fill.lower(),'#ffeeee');self.assertEqual(body.stroke.lower(),'#112233')
    async def test_modeling_label_color_projection_preserves_node_paint(self):
        for source,id,label in [('erDiagram\nA\nclassDef highlight color:#990000,fill:#ffeeee\nclass A highlight','A','A'),('requirementDiagram\nrequirement A {\ntext: body\n}\nclassDef highlight color:#990000,fill:#ffeeee\nclass A highlight','A','A'),('stateDiagram-v2\nA --> B\nclassDef highlight color:#990000,fill:#ffeeee\nclass A highlight','A','A')]:
            with self.subTest(kind=source.splitlines()[0]):
                r=await picture(source);events=[e for e in r.trace if e.semantic_id==id and e.text==label]
                self.assertTrue(events);self.assertTrue(all(e.color.lower()=='#990000' for e in events));self.assertEqual(paths(r,id=id)[0].fill.lower(),'#ffeeee')
    async def test_packet_physical_units_and_parent_relative_percentage(self):
        for value,expected in [('12pt',16),('150%',30),('2em',40)]:
            with self.subTest(value=value):
                r=await picture('packet\n0-7: "DATA"',{'theme':'base','themeVariables':{'fontSize':'20px','packet':{'labelFontSize':value}}})
                e=next(e for e in r.trace if e.text=='DATA');self.assertAlmostEqual(e.font_size,expected)
    async def test_packet_ex_and_ch_preserve_source_metric_scaling(self):
        for unit in ('ex','ch'):
            sizes=[]
            for factor in (1,2):
                r=await picture('packet\n0-7: "DATA"',{'theme':'base','themeVariables':{'fontSize':'20px','packet':{'labelFontSize':str(factor)+unit}}})
                sizes.append(next(e.font_size for e in r.trace if e.text=='DATA'))
            self.assertGreater(sizes[0],0);self.assertAlmostEqual(sizes[1],2*sizes[0])
    async def test_treeview_label_and_description_use_same_source_css_units(self):
        r=await picture('treeView-beta\n/\n  file.txt ## details',{'theme':'base','themeVariables':{'fontSize':'20px','treeView':{'labelFontSize':'150%'}}})
        labels=[e for e in r.trace if e.text and ('file.txt' in e.text or 'details' in e.text)]
        self.assertTrue(labels);self.assertTrue(all(e.font_size==30 for e in labels))

    def test_mindmap_source_basis_numeric_controls(self):
        from py_mermaid.diagrams.hierarchy.mindmap import _basis_path
        from py_mermaid.model.flowchart import Point
        self.assertEqual(_basis_path((Point(0,0),Point(60,0),Point(60,60),Point(120,60))),'M0,0 L10,0 C20,0 40,0 50,10 C60,20 60,40 70,50 C80,60 100,60 110,60 L120,60')
    async def test_tidy_edges_keep_source_basis_curve_and_all_labels(self):
        r=await picture('mindmap\nroot((Root))\n  a[First]\n  b[Second]\n  c[Third]\n  d[Fourth]',{'layout':'tidy-tree'})
        self.assertTrue(any(e.path.count('C')>=2 for e in r.trace if e.kind=='edge'))
        for label in ('Root','First','Second','Third','Fourth'):self.assertIn(label,visible(r))

    async def test_unified_notes_are_source_rectangles_not_dog_ears(self):
        for source in ('classDiagram\nclass A\nnote for A "Note"','stateDiagram-v2\nA --> B\nnote right of A : Note','usecase-beta\nactor User\nnote for User "Note"'):
            with self.subTest(kind=source.splitlines()[0]):
                r=await picture(source);bodies=[e for e in r.trace if e.kind=='note'];self.assertTrue(bodies)
                for event in bodies:
                    points=flatten_path(event.path)[0]
                    self.assertEqual(len(points),5);self.assertEqual(len({(p.x,p.y) for p in points}),4)
                self.assertIn('Note',visible(r))
    async def test_compound_labels_inherit_color_without_recoloring_shape(self):
        for source in ('erDiagram\nsubgraph G\nA\nend\nclassDef red color:#990000\nclass G red','stateDiagram-v2\nstate G {\nA\n}\nclassDef red color:#990000\nclass G red','usecase-beta\nsystemBoundary G[G]\nactor User\nend\nclassDef red color:#990000\nclass G red'):
            with self.subTest(kind=source.splitlines()[0]):
                r=await picture(source);labels=[e for e in r.trace if e.semantic_id=='G' and e.text=='G']
                self.assertTrue(labels);self.assertTrue(all(e.color.lower()=='#990000' for e in labels))

    async def test_c4_cssom_invalid_font_value_drops_whole_declaration(self):
        r=await picture('C4Context\nSystem(a,"Alpha")',{'theme':'base','themeVariables':{'fontSize':'20px'},'c4':{'systemFontSize':'2em; fill: red'}})
        label=next(e for e in r.trace if e.text=='Alpha')
        self.assertEqual(label.font_size,20);self.assertEqual(label.color.lower(),'#ffffff')

    async def test_kanban_ticket_url_draws_real_static_underline_with_no_url_negative(self):
        # kanbanItem.ts creates a link only with ticket+ticketBaseUrl;
        # styles.ts .kanban-ticket-link text-decoration:underline is unconditional.
        from io import BytesIO
        import math
        from PIL import Image,ImageChops
        source='kanban\nBacklog\n  work[Task]@{ticket: T-0}'
        plain=await picture(source,{'kanban':{'sectionWidth':260}})
        linked=await picture(source,{'kanban':{'sectionWidth':260,'ticketBaseUrl':'https://example.invalid/#TICKET#'}})
        def image(result):
            rgba=Image.open(BytesIO(result.data)).convert('RGBA')
            return Image.alpha_composite(Image.new('RGBA',rgba.size,'white'),rgba).convert('RGB')
        a,b=image(plain),image(linked);self.assertEqual(a.size,b.size)
        pa=next(e for e in plain.trace if e.kind=='ticket' and e.text=='T-0')
        pb=next(e for e in linked.trace if e.kind=='ticket' and e.text=='T-0')
        self.assertEqual(pa.points,pb.points);self.assertEqual((pa.box.x,pa.box.y,pa.box.width),(pb.box.x,pb.box.y,pb.box.width));self.assertGreaterEqual(pb.box.height,pa.box.height)
        baseline=pb.points[0].y;left=math.ceil(pb.box.x+1);right=math.floor(pb.box.x+pb.box.width-1)
        region=(left,math.ceil(baseline+1),right,math.ceil(baseline+.3*pb.font_size+2))
        def ink(crop):
            return sum(min(pixel)<220 for pixel in crop.getdata())
        self.assertEqual(ink(a.crop(region)),0,'No ticket URL must not invent static underline')
        self.assertGreater(ink(b.crop(region)),max(5,(right-left)//2),'Linked ticket must paint visible underline, not merely a run attribute')
        glyph=(left,math.floor(baseline-pb.font_size),right,math.floor(baseline))
        self.assertIsNone(ImageChops.difference(a.crop(glyph),b.crop(glyph)).getbbox(),'Decoration must not duplicate or shift glyph pixels')
        erased=b.copy();erased.paste(a.crop(region),region)
        self.assertEqual(ink(erased.crop(region)),0,'Actual underline removal must be detected')
        self.assertIn('Task',visible(linked));self.assertIn('T-0',visible(linked))

    async def test_kanban_handdrawn_section_keeps_source_width_times_three_height(self):
        r=await picture('kanban\nTodo\n  item[Task]@{priority: High}',{'look':'handDrawn','handDrawnSeed':42,'kanban':{'sectionWidth':200}})
        layout={row[0]:row[1:] for row in r.layout[1]}
        self.assertEqual(layout['Todo'][2:],(200,600))
        self.assertTrue(any(e.kind=='priority' and e.stroke in ('orange','#ffa500') for e in r.trace))
        self.assertFalse(any(e.kind=='kanban-item-hachure' for e in r.trace));self.assertTrue(any(e.kind=='kanban-section-hachure' for e in r.trace))
        self.assertGreaterEqual(r.height,600)
    async def test_kanban_dense_section_background_is_real_painted_pixels(self):
        from io import BytesIO
        from PIL import Image
        r=await picture('kanban\nTodo\n  item[Task]',{'look':'handDrawn','handDrawnSeed':42})
        # The lower half of the source 600px section is still its colored body.
        im=Image.open(BytesIO(r.data)).convert('RGB');crop=im.crop((im.width//4,im.height//2,3*im.width//4,3*im.height//4))
        painted=sum(min(pixel)<245 for pixel in crop.getdata());self.assertGreater(painted,.9*crop.width*crop.height)
    async def test_kanban_explicit_seed_repeats_but_item_look_stays_crisp(self):
        source='kanban\nTodo\n  a[Task]@{priority: High}\nDone\n  b[Completed]'
        config={'look':'handDrawn','handDrawnSeed':42}
        first=await picture(source,config);second=await picture(source,config)
        self.assertEqual(first.data,second.data)
        self.assertEqual(len([e for e in first.trace if e.kind=='priority']),1)
        self.assertEqual(len([e for e in first.trace if e.kind=='kanban-item']),2)
