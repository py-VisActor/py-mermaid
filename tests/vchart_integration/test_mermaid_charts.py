"""Source-first seven-DSL tests, deferred until the joint P3 candidate run.

Literal model expectations are handwritten from fixed Mermaid grammar/DB.
Geometry constants are elementary consequences of the source scales, sectors,
equal weighted partitions and flow conservation, never candidate snapshots.
"""
from dataclasses import fields, is_dataclass
from pathlib import Path
import importlib
import json
import math
import unittest
from unittest.mock import patch


FIXTURE = Path(__file__).with_name('cases-mermaid-charts.json')
DATA = json.loads(FIXTURE.read_text(encoding='utf-8'))
CASES = {case['id']: case for case in DATA['cases']}
BASIC = {'pie': 'pie-basic', 'quadrantChart': 'quadrant-basic', 'xychart': 'xy-line',
         'radar': 'radar-basic', 'treemap': 'treemap-basic', 'sankey': 'sankey-basic', 'venn': 'venn-basic'}


def plain(value):
    if is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def select(value, keys):
    for key in keys:
        value = value[key]
    return value


def parse_case(case):
    from py_mermaid.runtime.registry import parse_diagram
    return parse_diagram(case['source'], config=case['config'])


async def picture(case, format='png'):
    from py_mermaid.api import arender
    return await arender(case['source'], config=case['config'], format=format, backend='cpu')


def visible(result):
    return ''.join(e.text or '' for e in result.trace if e.opacity > 0)


class MermaidSourceSemantics(unittest.TestCase):
    def test_quadrant_spaced_zero_is_a_valid_source_control(self):
        # Fixed original diagnostic VC-Q-DIAG-repeated-spaced captured both
        # points. A rule rejecting all bare zero coordinates would be wrong.
        from py_mermaid.runtime.registry import parse_diagram
        model = parse_diagram('quadrantChart\nPoint: [0, 0]\nPoint: [1, 1]').model
        self.assertEqual([(p[0], p[2], p[3]) for p in model.points],
                         [('Point', 1.0, 1.0), ('Point', 0.0, 0.0)])


def install_source_cases():
    for case in DATA['cases']:
        def check(self, case=case):
            from py_mermaid.model.flowchart import MermaidError
            if case['expect'] == 'syntax_error':
                with self.assertRaises(MermaidError) as caught:
                    parse_case(case)
                self.assertIn(caught.exception.code, case['expectedErrorCodes'])
                self.assertIsNotNone(caught.exception.span)
                return
            diagram = parse_case(case)
            self.assertEqual(diagram.kind, case['kind'])
            model = plain(diagram.model)
            self.assertTrue(case['modelExpected'], 'Positive case requires semantic field assertions')
            for expected in case['modelExpected']:
                with self.subTest(path=expected['path']):
                    self.assertEqual(select(model, expected['path']), expected['equals'])
        name = 'test_source_' + case['id'][5:].replace('-', '_')
        check.__name__ = name
        check.__doc__ = case['origin']['path'] + ': ' + case['origin']['symbol']
        setattr(MermaidSourceSemantics, name, check)


install_source_cases()


class PublicVChartGeometry(unittest.TestCase):
    def test_pie_one_to_three_preserves_order_and_area_angles(self):
        from py_vchart.layouts import pie
        arcs = pie([1, 3], radius=40, inner_radius=.25)
        self.assertEqual(len(arcs), 2)
        self.assertAlmostEqual(arcs[0][0], -math.pi / 2)
        self.assertAlmostEqual(arcs[0][1], 0)
        self.assertAlmostEqual(arcs[1][1], math.pi * 1.5)
        self.assertEqual(arcs[0][2:], (10, 40))

    def test_numeric_scatter_uses_domain_corners_and_y_inversion(self):
        from py_vchart.layouts import scatter
        actual = scatter([(0, 0), (.5, .5), (1, 1)], 200, 100)
        self.assertEqual(actual, ((0, 100), (100, 50), (200, 0)))

    def test_line_has_missing_value_segment_boundary(self):
        from py_vchart.layouts import cartesian
        geometry = cartesian('line', [('A', 1), ('B', None), ('C', 3)], 200, 100,
                             ['A', 'B', 'C'], [0, 4])
        self.assertEqual([len(s) for s in geometry['segments']], [1, 1])
        self.assertLess(geometry['segments'][0][0][0], geometry['segments'][1][0][0])
        self.assertAlmostEqual(geometry['segments'][0][0][1], 75)
        self.assertAlmostEqual(geometry['segments'][1][0][1], 25)

    def test_continuous_x_bar_keeps_nonuniform_distances(self):
        from py_vchart.layouts import cartesian
        result = cartesian('bar', [(0, 1), (10, 2), (100, 3)], 200, 100, [0, 100], [0, 4], x_kind='linear')
        centers = [(r[0] + r[2]) / 2 for r in result['bars']]
        self.assertEqual(centers, [0, 20, 200])
        self.assertAlmostEqual((centers[2] - centers[1]) / (centers[1] - centers[0]), 9)
        self.assertTrue(all(r[3] == 100 for r in result['bars']))

    def test_radar_cardinal_axes_use_one_common_domain(self):
        from py_vchart.layouts import radar
        actual = radar([1, 1, 1, 1], 0, 1, center=(50, 50), radius=40)
        for point, expected in zip(actual, [(50, 10), (90, 50), (50, 90), (10, 50)]):
            self.assertAlmostEqual(point[0], expected[0])
            self.assertAlmostEqual(point[1], expected[1])

    def test_sankey_two_node_flow_conserves_full_height(self):
        from py_vchart.layouts import sankey
        nodes, edges = sankey(['A', 'B'], [('A', 'B', 10)], 200, 100, node_width=10, node_gap=0)
        self.assertEqual([n['id'] for n in nodes], ['A', 'B'])
        self.assertEqual((nodes[0]['x0'], nodes[0]['x1']), (0, 10))
        self.assertEqual((nodes[1]['x0'], nodes[1]['x1']), (190, 200))
        self.assertEqual([n['value'] for n in nodes], [10, 10])
        self.assertEqual((edges[0]['width'], edges[0]['y0'], edges[0]['y1']), (100, 50, 50))

    def test_binary_treemap_equal_leaf_area_and_identity(self):
        from py_vchart.layouts import treemap
        boxes = treemap([{'id': 'A', 'value': 1}, {'id': 'B', 'value': 1}], 200, 100)
        self.assertEqual([b['id'] for b in boxes], ['A', 'B'])
        self.assertEqual(boxes[0]['box'], (0, 0, 100, 100))
        self.assertEqual(boxes[1]['box'], (100, 0, 200, 100))
        self.assertTrue(all(not b['section'] for b in boxes))

    def test_single_venn_circle_uses_limiting_plot_dimension(self):
        from py_vchart.layouts import venn
        actual = venn([(('A',), math.pi)], 200, 100, padding=0)
        self.assertEqual(len(actual['circles']), 1)
        key, x, y, radius = actual['circles'][0]
        self.assertEqual(key, 'A')
        self.assertAlmostEqual(x, 100)
        self.assertAlmostEqual(y, 50)
        self.assertAlmostEqual(radius, 50)
        self.assertTrue(actual['regions'][0]['path'].endswith('Z'))

    def test_layout_helpers_never_allocate_a_canvas(self):
        from py_vchart import layouts
        import py_skia_canvas
        with patch.object(py_skia_canvas, 'Canvas', side_effect=AssertionError('Pure layout allocated Canvas')):
            self.assertEqual(len(layouts.pie([1, 1])), 2)
            self.assertEqual(len(layouts.scatter([(0, 0)], 100, 100)), 1)
            self.assertEqual(len(layouts.radar([1, 2, 3], 0, 3)), 3)
            self.assertEqual(len(layouts.treemap([{'id': 'A', 'value': 1}], 100, 100)), 1)

    def test_runtime_layouts_comes_from_installed_dependency(self):
        from py_vchart import layouts
        adjacent = Path(__file__).resolve().parents[2].parent / 'py-vchart' / 'src'
        self.assertFalse(Path(layouts.__file__).resolve().is_relative_to(adjacent),
                         'Integration must consume the installed wheel, not an adjacent source path')


class MermaidVChartRendering(unittest.IsolatedAsyncioTestCase):
    async def test_treemap_missing_parent_fill_uses_readable_default_label_ink(self):
        # Original source's ordinal root slot is transparent. Its first label
        # is white (verified original PNG/DOM), an upstream readability defect.
        # Host correction is only the default text paint; explicit green in
        # treemap-class is independently asserted by the existing pixel test.
        from io import BytesIO
        from PIL import Image
        for suffix,label,value in [('basic','Alpha','1'),('class','Beta','20'),('numbers','Revenue',None)]:
            with self.subTest(case=suffix):
                result=await picture(CASES['VC-M-treemap-'+suffix])
                image=Image.open(BytesIO(result.data)).convert('RGB')
                labels=[e for e in result.trace if e.text==label]
                self.assertEqual(len(labels),1)
                values=[e for e in result.trace if e.text==value and e.semantic_id==labels[0].semantic_id.replace('-label','-value')] if value else []
                if value:self.assertEqual(len(values),1)
                for event in labels+values:
                    self.assertEqual(event.color.lower(),'#333333')
                    box=event.box
                    crop=image.crop((max(0,math.floor(box.x)),max(0,math.floor(box.y)),min(image.width,math.ceil(box.x+box.width)),min(image.height,math.ceil(box.y+box.height))))
                    self.assertGreater(sum(max(pixel)<140 for pixel in crop.getdata()),5,'Actual label/value region must contain visible dark ink')

    async def test_pie_svg_title_baseline_keeps_glyphs_above_outer_arc(self):
        # pieRenderer.ts title baseline is height/2-(height-50)/2 = 25,
        # while the outer circle starts at 225-186 = 39.
        result=await picture(CASES['VC-M-pie-basic'])
        title=next(e for e in result.trace if e.kind=='title' and e.text)
        circle=next(e for e in result.trace if e.semantic_id=='pie-outer')
        # Trace currently includes a conservative miter stroke budget around
        # the ellipse; the actual top arc is center-radius, not that budget.
        self.assertLess(title.box.y+title.box.height,39)

    async def test_quadrant_invalid_source_color_inherits_visible_svg_fill(self):
        # Original SVG has fill=hsl(...NaN%); rejected presentation attr
        # inherits computed root fill rgb(51,51,51), not Canvas white.
        from io import BytesIO
        from PIL import Image
        result=await picture(CASES['VC-M-quadrant-basic'])
        pixels=Image.open(BytesIO(result.data)).convert('RGB')
        points=[e for e in result.trace if e.semantic_id.startswith('point-') and not e.text]
        self.assertEqual(len(points),2)
        for point in points:
            x=round(point.box.x+point.box.width/2);y=round(point.box.y+point.box.height/2)
            self.assertLess(max(pixels.getpixel((x,y))),100,'Default marker must create dark visible ink')
            background=pixels.getpixel((x+10,y))
            self.assertGreater(min(background)-max(pixels.getpixel((x,y))),100)

    async def test_xy_numeric_bars_remain_inside_axis_plot(self):
        # barPlot.ts uses min(2*axis.outerPadding,tickDistance)*.95,
        # rather than continuous neighbor spacing as the full bar width.
        result=await picture(CASES['VC-M-xy-default-bar'])
        background=next(e for e in result.trace if e.semantic_id=='background')
        bars=[e for e in result.trace if e.semantic_id.startswith('bar-')]
        self.assertEqual(len(bars),3)
        for bar in bars:
            self.assertGreaterEqual(bar.box.x,background.box.x)
            self.assertLessEqual(bar.box.x+bar.box.width,background.box.x+700)
        self.assertLessEqual(result.width,702)

    async def test_treemap_leaf_source_opacity_has_real_translucent_ink(self):
        # renderer.ts leaf fill-opacity=.3, including inline class red fill.
        from io import BytesIO
        from PIL import Image
        result=await picture(CASES['VC-M-treemap-class'])
        leaf=next(e for e in result.trace if e.semantic_id=='treemap-0' and e.path)
        pixels=Image.open(BytesIO(result.data)).convert('RGB')
        color=pixels.getpixel((round(leaf.box.x+leaf.box.width*.2),round(leaf.box.y+leaf.box.height*.2)))
        self.assertGreater(color[0],240)
        self.assertTrue(165<color[1]<195 and 165<color[2]<195,'30% red on white must be pink, never opaque red')

    async def test_each_chart_really_consumes_vchart_geometry_and_keeps_text(self):
        from py_vchart import layouts
        providers = {'pie': 'pie', 'quadrantChart': 'scatter', 'xychart': 'cartesian', 'radar': 'radar',
                     'treemap': 'treemap', 'sankey': 'sankey', 'venn': 'venn'}
        data_ids = {'pie': 'slice-0', 'quadrantChart': 'point-0', 'xychart': 'line-0',
                    'radar': 'curve-plan', 'treemap': 'treemap-0', 'sankey': 'node-Alpha', 'venn': 'venn-area-0'}
        for kind, suffix in BASIC.items():
            case = CASES['VC-M-' + suffix]
            name = providers[kind]
            with self.subTest(kind=kind), patch.object(layouts, name, wraps=getattr(layouts, name)) as provider:
                result = await picture(case)
                provider.assert_called()
                self.assertTrue(any(e.semantic_id == data_ids[kind] and e.path and e.opacity > 0 for e in result.trace))
                text = ''.join(visible(result).split())
                for expected in case['expectedText']:
                    self.assertIn(''.join(expected.split()), text)

    async def test_quadrant_class_style_reaches_actual_point(self):
        result = await picture(CASES['VC-M-quadrant-style'])
        point = next(e for e in result.trace if e.semantic_id == 'point-0' and e.path)
        self.assertEqual(point.fill.lower(), '#ff0000')
        self.assertEqual(point.stroke.lower(), '#000000')

    async def test_treemap_class_style_reaches_actual_leaf(self):
        result = await picture(CASES['VC-M-treemap-class'])
        point = next(e for e in result.trace if e.semantic_id == 'treemap-0' and e.path)
        self.assertEqual(point.fill.lower(), '#ff0000')
        self.assertIn('Alpha', visible(result))
        label = next(e for e in result.trace if e.semantic_id == 'treemap-0-label' and e.text)
        self.assertEqual(label.color.lower(), '#00ff00')
        from io import BytesIO
        from PIL import Image
        pixels = Image.open(BytesIO(result.data)).convert('RGB').getdata()
        self.assertTrue(any(g > 120 and g > r * 1.5 and g > b * 1.5 for r, g, b in pixels),
                        'Explicit green source label must produce real green ink')

    async def test_venn_style_reaches_intersection_and_label(self):
        result = await picture(CASES['VC-M-venn-style'])
        region = next(e for e in result.trace if e.semantic_id == 'venn-area-2' and e.path)
        self.assertEqual(region.fill.lower(), '#ffff00')
        label = next(e for e in result.trace if e.semantic_id == 'venn-label-2' and e.text)
        self.assertEqual(label.color.lower(), '#000000')

    async def test_sankey_gradient_and_prefix_remain_vector_semantics(self):
        result = await picture(CASES['VC-M-sankey-colors'], 'svg')
        self.assertIn('$', visible(result))
        self.assertIn('units', visible(result))
        self.assertIn(b'linearGradient', result.data)
        self.assertNotIn(b'data:image/png', result.data)

    async def test_sankey_show_values_false_keeps_names_without_value_labels(self):
        result = await picture(CASES['VC-M-sankey-no-values'])
        labels = [e.text for e in result.trace if e.semantic_id in ('label-Alpha', 'label-Beta')]
        self.assertEqual(labels, ['Alpha', 'Beta'])

    async def test_venn_union_and_indented_text_all_remain_visible(self):
        result = await picture(CASES['VC-M-venn-text'])
        text = visible(result)
        for label in ('Alpha', 'Beta', 'One', 'Two', 'Shared note'):
            self.assertIn(label, text)
        self.assertTrue(any(e.semantic_id == 'common' and e.text for e in result.trace))

    async def test_advanced_provider_limits_are_explicit_diagnostics(self):
        from py_mermaid.model.flowchart import MermaidError
        for case in DATA['unsupportedCases']:
            with self.subTest(id=case['id']), self.assertRaises(MermaidError) as caught:
                await picture(case)
            self.assertEqual(caught.exception.code, 'UNSUPPORTED_VCHART_OPTION')
            self.assertTrue(str(caught.exception))


class MermaidChartExports(unittest.IsolatedAsyncioTestCase):
    pass


def install_export_cases():
    for kind, suffix in BASIC.items():
        for format, signature in [('png', b'\x89PNG\r\n\x1a\n'), ('jpeg', b'\xff\xd8'),
                                  ('webp', b'RIFF'), ('pdf', b'%PDF'), ('svg', None)]:
            async def check(self, suffix=suffix, format=format, signature=signature):
                result = await picture(CASES['VC-M-' + suffix], format)
                self.assertGreater(result.width, 0)
                self.assertGreater(result.height, 0)
                self.assertTrue(any(e.path and e.opacity > 0 for e in result.trace))
                if signature is not None:
                    self.assertTrue(result.data.startswith(signature))
                    if format == 'pdf':
                        self.assertNotIn(b'/Subtype /Image', result.data)
                else:
                    self.assertIn(b'<svg', result.data)
                    self.assertTrue(b'<path' in result.data or b'<text' in result.data)
                    self.assertNotIn(b'data:image/png', result.data)
            name = 'test_export_' + kind.replace('-', '_') + '_' + format
            check.__name__ = name
            setattr(MermaidChartExports, name, check)


install_export_cases()
