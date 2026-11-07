"""Explicit offline resources and old resource boundaries on the DSL path."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from py_mermaid import compile_vchart,parse,render,render_vchart,MermaidError,ResourceBundle,FontResource,ImageResource
try:from .support_c import DSL,SPEC,GEO,SVG,resource_dsl,pixels,assert_ink,typed,NoFontLibrary
except ImportError:from support_c import DSL,SPEC,GEO,SVG,resource_dsl,pixels,assert_ink,typed,NoFontLibrary


class DslResourceTests(unittest.TestCase):
    def test_inline_map_and_svg_compile_as_isolated_namespaces_not_spec_fields(self):
        source=resource_dsl('map')+'resource svg "local" = '+json.dumps(SVG)+'\n'
        value=compile_vchart(source)
        self.assertEqual(value.maps(),{'local':GEO});self.assertEqual(value.svg_sources(),{'local':SVG})
        self.assertEqual(value.spec(),{'type':'map','width':180,'height':120,'map':'local'})
        self.assertTrue(any(s.namespace=='map' and s.path[0]=='local' for s in value.source_map))
        self.assertTrue(any(s.namespace=='svg' and s.path[0]=='local' for s in value.source_map))
        value.maps()['local']['features'].clear();value.svg_sources()['local']='changed'
        self.assertEqual(value.maps()['local'],GEO);self.assertEqual(value.svg_sources()['local'],SVG)

    def test_same_kind_same_name_external_conflicts_even_for_identical_bytes(self):
        for kind,resources in [('map',{'maps':{'local':GEO}}),('svg',{'svgs':{'quad':SVG}})]:
            source=resource_dsl(kind)
            for operation in (compile_vchart,render):
                with self.subTest(kind=kind,operation=operation.__name__),self.assertRaises(MermaidError) as caught:
                    operation(source,**resources)
                self.assertEqual(caught.exception.code,'VCHART_DSL_RESOURCE_CONFLICT')
                self.assertEqual((caught.exception.span.start.index,caught.exception.span.end.index),(0,len(source)))

    def test_distinct_resource_names_merge_and_external_mutation_does_not_leak(self):
        external={'second':deepcopy(GEO)}
        value=compile_vchart(resource_dsl('map'),maps=external,svgs={'quad':SVG})
        external['second']['features'].clear()
        self.assertEqual(set(value.maps()),{'local','second'});self.assertTrue(value.maps()['second']['features'])
        self.assertEqual(value.svg_sources(),{'quad':SVG})
        self.assertEqual(compile_vchart(DSL).maps(),{});self.assertEqual(compile_vchart(DSL).svg_sources(),{})

    def test_cross_kind_same_name_is_valid_without_overwriting_either(self):
        value=compile_vchart(resource_dsl('map'),svgs={'local':SVG})
        self.assertEqual(value.maps()['local'],GEO);self.assertEqual(value.svg_sources()['local'],SVG)

    def test_duplicate_inline_resource_diagnostics_retain_source_declaration(self):
        source=resource_dsl('svg')+'resource svg "quad" = '+json.dumps(SVG)+'\n'
        with self.assertRaises(MermaidError) as caught:compile_vchart(source)
        self.assertEqual(caught.exception.code,'VCHART_DSL_RESOURCE_CONFLICT')
        self.assertTrue(caught.exception.related_spans)
        self.assertLess(caught.exception.related_spans[0][0],caught.exception.span.start.index)

    def test_unsafe_svg_never_executes_or_fetches_even_when_unused(self):
        dangerous=['<svg xmlns="http://www.w3.org/2000/svg"><script>evil()</script></svg>',
            '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/x.png"/></svg>',
            '<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///secret">]><svg/>',
            '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><p>host</p></foreignObject></svg>']
        for svg in dangerous:
            with self.subTest(svg=svg),patch('urllib.request.urlopen',side_effect=AssertionError('network')):
                with self.assertRaises(MermaidError) as caught:compile_vchart(DSL,svgs={'unsafe':svg})
                self.assertIsNotNone(caught.exception.span)

    def test_inline_and_external_geojson_use_real_provider_geometry_validation(self):
        bad={'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Polygon','coordinates':[[['bad',0],[1,0],[0,0]]]},'properties':{}}]}
        for source,options in [(DSL,{'maps':{'bad':bad}}),
            ('vchart map\nresource map "bad" = '+json.dumps(bad)+'\n',{})]:
            with self.subTest(source=source),self.assertRaises(MermaidError) as caught:compile_vchart(source,**options)
            self.assertEqual(caught.exception.code,'INVALID_RESOURCE');self.assertIsNotNone(caught.exception.span)

    def test_resource_mapping_types_and_names_are_explicit(self):
        for options in [{'maps':[]},{'svgs':[]},{'maps':{'bad':1}},{'svgs':{'x':b'<svg/>'}},{'svgs':{'':SVG}}]:
            with self.subTest(options=options),self.assertRaises(MermaidError) as caught:compile_vchart(DSL,**options)
            self.assertEqual(caught.exception.code,'INVALID_RESOURCE')

    def test_resource_budget_remains_enforced_before_native_allocation(self):
        from py_skia_canvas import Canvas
        from py_mermaid.resources import MAX_RESOURCE_BYTES
        with patch.object(Canvas,'__init__',side_effect=AssertionError('resource budget allocated Canvas')):
            with self.assertRaises(MermaidError) as caught:compile_vchart(DSL,svgs={'too-large':' '* (MAX_RESOURCE_BYTES+1)})
        self.assertEqual(caught.exception.code,'RESOURCE_BUDGET')

    def test_inline_geojson_real_png_equals_explicit_spec_resources(self):
        source=resource_dsl('map');compiled=compile_vchart(source)
        actual=render(source,backend='cpu');reference=render_vchart(compiled.spec(),maps={'local':GEO},svgs={},backend='cpu')
        self.assertEqual(actual.data,reference.data);assert_ink(self,actual.data)
        self.assertEqual(typed(actual.layout),typed(reference.layout))
        self.assertEqual(len(actual.layout['marks']['area']),1)

    def test_inline_svg_real_png_contains_both_original_colors(self):
        actual=render(resource_dsl('svg'),backend='cpu');image=assert_ink(self,actual.data)
        self.assertGreater(sum(r>b*2 for r,g,b in image.getdata()),100)
        self.assertGreater(sum(b>r*2 for r,g,b in image.getdata()),100)
        # A following request without the resource cannot inherit it globally.
        source='vchart pictogram\nsize 180 120\nsvg = "quad"\ndata = {values: []}\n'
        with self.assertRaises(MermaidError) as caught:render(source,backend='cpu')
        self.assertEqual(caught.exception.code,'VCHART_SPEC_ERROR')

    def test_empty_external_mapping_does_not_inherit_registered_provider_globals(self):
        from py_vchart import VChart
        VChart.register_map('dsl-only-global-map',GEO)
        source='vchart map\nmap = "dsl-only-global-map"\n'
        with self.assertRaises(MermaidError) as caught:render(source,maps={},backend='cpu')
        self.assertEqual(caught.exception.code,'VCHART_SPEC_ERROR')

    def test_existing_explicit_font_alias_boundary_does_not_register_unused_fonts(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unused.ttf';path.write_bytes(b'opaque-unused-font')
            bundle=ResourceBundle(fonts=(FontResource('Arial',str(path)),))
            font_guard=NoFontLibrary()
            with patch('py_skia_canvas.FontLibrary',new=font_guard):
                result=render(DSL,backend='cpu',resources=bundle)
                font_guard.use.assert_not_called();assert_ink(self,result.data)

    def test_existing_explicit_image_resource_is_decoded_only_at_render(self):
        from io import BytesIO
        from PIL import Image
        data=BytesIO();Image.new('RGB',(40,20),'#e02020').save(data,format='PNG')
        source='''vchart imageCloud
size 180 120
data = {values: [{image: "resource:quad"}]}
urlField = "image"
imageSize = 40
layoutConfig = {fillingTimes: 0}
'''
        compiled=compile_vchart(source);self.assertIn('resource:quad',compiled.model.spec_json)
        result=render(source,backend='cpu',resources=ResourceBundle(images=(ImageResource('quad',data.getvalue(),'image/png'),)))
        self.assertGreater(sum(r>g*2 and r>b*2 for r,g,b in pixels(result.data).getdata()),100)
