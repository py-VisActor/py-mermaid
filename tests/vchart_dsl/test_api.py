"""Public text/spec integration contracts from DSL RFC and Canvas public API.

P2: test definitions only. Expected spec/geometry are hand written, and native
positives require actual PNG/encoding evidence, not successful compilation.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError,fields,is_dataclass
import json
import unittest
from unittest.mock import patch
from pathlib import Path

from py_mermaid import (compile_vchart,parse,render,arender,render_vchart,
    VChartModel,VChartCompilation,Diagram,MermaidError,ExportOptions)
try:from .support_c import SPEC,DSL,source_json,typed,jsonable,assert_ink,NoFontLibrary
except ImportError:from support_c import SPEC,DSL,source_json,typed,jsonable,assert_ink,NoFontLibrary


class CompilationApiTests(unittest.TestCase):
    def test_public_immutable_compilation_preserves_model_and_full_inspection(self):
        compiled=compile_vchart(DSL)
        self.assertIsInstance(compiled,VChartCompilation);self.assertIsInstance(compiled.model,VChartModel)
        self.assertEqual(typed(compiled.spec()),typed(SPEC));self.assertEqual(compiled.syntax,'dsl')
        info=compiled.as_dict();self.assertEqual(info['spec'],SPEC);self.assertEqual(info['maps'],{});self.assertEqual(info['svgs'],{})
        self.assertEqual(info['source'],DSL);self.assertTrue(info['source_map']);self.assertIn('provider',info['validation'])
        with self.assertRaises(FrozenInstanceError):compiled.model.width=1
        with self.assertRaises(FrozenInstanceError):compiled.source_text='changed'

    def test_fresh_copies_cannot_mutate_model_or_later_inspection(self):
        compiled=compile_vchart(DSL);spec=compiled.spec();spec['data']['values'][0]['v']=999
        view=compiled.as_dict();view['spec']['data']['values'].clear();view['source_map'].clear()
        self.assertEqual(compiled.spec(),SPEC);self.assertTrue(compiled.source_map)
        self.assertEqual(compile_vchart(DSL).spec(),SPEC)

    def test_compile_is_pure_without_canvas_fonts_render_file_or_network_access(self):
        from py_skia_canvas import Canvas
        from py_vchart import VChart
        import py_mermaid.parsing.vchart_dsl.compiler
        import py_mermaid.vchart_compilation
        from contextlib import ExitStack
        font_guard=NoFontLibrary()
        with ExitStack() as stack:
            stack.enter_context(patch('py_skia_canvas.FontLibrary',new=font_guard))
            for target,name in [(Canvas,'__init__'),(VChart,'render'),(VChart,'draw_to'),
                                (Path,'read_text'),(Path,'read_bytes')]:
                stack.enter_context(patch.object(target,name,side_effect=AssertionError('Forbidden compile side effect '+name)))
            stack.enter_context(patch('urllib.request.urlopen',side_effect=AssertionError('compile network')))
            value=compile_vchart(DSL)
        font_guard.use.assert_not_called()
        self.assertEqual(value.spec(),SPEC)
        def pure(v):
            if is_dataclass(v):return v.__dataclass_params__.frozen and all(pure(getattr(v,f.name)) for f in fields(v))
            if isinstance(v,tuple):return all(pure(x) for x in v)
            return type(v) in (str,int,float,bool,type(None))
        self.assertTrue(pure(value))

    def test_parse_returns_same_vchart_model_identity_and_no_mermaid_sanitizing(self):
        source=DSL+'custom = {text: "%%{init: x}%% <b>& \\n $literal"}\n'
        diagram=parse(source);self.assertIsInstance(diagram,Diagram);self.assertIsInstance(diagram.model,VChartModel)
        self.assertEqual(diagram.kind,'vchart');self.assertIn('%%{init: x}%%',diagram.model.spec()['custom']['text'])

    def test_python_spec_api_never_calls_text_compiler_or_parser(self):
        with (patch('py_mermaid.api.parse',side_effect=AssertionError('spec API text parse')),
              patch('py_mermaid.vchart_compilation.compile_vchart',side_effect=AssertionError('spec API text compile'))):
            result=render_vchart(SPEC,backend='cpu')
        self.assertEqual((result.width,result.height),(180,120));assert_ink(self,result.data)

    def test_legacy_strict_json_values_and_literal_directives_remain_unchanged(self):
        spec={**SPEC,'literal':{'array':[],'object':{},'nil':None,'bool':False,'integer':0,'fraction':0.0,
                              'text':'%%{init: {"theme":"dark"}}%% <svg> 😀'}}
        value=compile_vchart(source_json(spec));self.assertEqual(value.syntax,'json')
        self.assertEqual(typed(value.spec()),typed(spec));self.assertIsInstance(parse(source_json(spec)).model,VChartModel)

    def test_legacy_json_rejects_non_json_comments_duplicates_and_constants(self):
        for payload in ['{"type":"bar",}','{"type":"bar",%% comment\n"width":100}',
                        '{"type":"bar","type":"pie"}','{"type":"bar","x":NaN}',
                        '{"type":"bar","x":Infinity}','[1]','null']:
            with self.subTest(payload=payload),self.assertRaises(MermaidError) as caught:
                compile_vchart('vchart\n'+payload)
            self.assertIn(caught.exception.code,('INVALID_VCHART_JSON','INVALID_VCHART_SPEC'))

    def test_reserved_bad_typed_header_never_falls_through_other_diagrams(self):
        for source in ['vchart bar extra\n','vchart bar\ndata = notAString\n']:
            with self.subTest(source=source),self.assertRaises(MermaidError) as caught:parse(source)
            self.assertEqual(caught.exception.code,'VCHART_DSL_SYNTAX')
            self.assertIsNotNone(caught.exception.span)
        # This is not a typed ASCII-identifier header. The old JSON entry
        # already reserved its namespace and reported this exact error class.
        with self.assertRaises(MermaidError) as caught:parse('vchart!\nflowchart TD\nA-->B')
        self.assertEqual(caught.exception.code,'INVALID_VCHART_JSON')
        self.assertIsNone(caught.exception.span)

    def test_legacy_json_error_offsets_still_use_original_utf16_source(self):
        source='vchart\n{"type":"bar","text":"😀","bad": }'
        with self.assertRaises(MermaidError) as caught:compile_vchart(source)
        position=caught.exception.span.start;index=source.rindex('}')
        self.assertEqual(caught.exception.code,'INVALID_VCHART_JSON')
        self.assertEqual(position.index,index)
        self.assertEqual(position.utf16_offset,len(source[:index].encode('utf-16-le'))//2)

    def test_unknown_case_sensitive_type_suggestion_points_to_actual_header(self):
        source='\ufeff\n vchart BAR\n'
        with self.assertRaises(MermaidError) as caught:compile_vchart(source)
        error=caught.exception;self.assertEqual(error.code,'UNSUPPORTED_VCHART_TYPE')
        self.assertIn('bar',str(error));self.assertEqual(error.spec_path,('type',))
        self.assertEqual((error.span.start.index,error.span.end.index),(source.index('BAR'),source.index('BAR')+3))

    def test_invalid_size_after_non_bmp_data_uses_original_utf16_span(self):
        source='vchart bar\nname = "😀"\nwidth = 0\n'
        with self.assertRaises(MermaidError) as caught:compile_vchart(source)
        error=caught.exception;index=source.index('0')
        self.assertEqual(error.code,'INVALID_VCHART_SIZE');self.assertEqual(error.spec_path,('width',))
        self.assertEqual(error.span.start.index,index)
        self.assertEqual(error.span.start.utf16_offset,len(source[:index].encode('utf-16-le'))//2)

    def test_fixed_pixel_size_is_diagnostic_not_silently_rewritten_spec(self):
        source='vchart sequenceScatterPixel\nsize 640 480\n'
        value=compile_vchart(source)
        self.assertEqual((value.width,value.height),(300,300))
        self.assertEqual(value.spec(),{'type':'sequenceScatterPixel','width':640,'height':480})
        self.assertTrue(any(v.code=='VCHART_FIXED_SIZE' and '300' in v.message for v in value.diagnostics))

    def test_compile_success_does_not_claim_provider_disabled_options_supported(self):
        source='vchart sankey\nlabel.visible = true\n'
        self.assertEqual(compile_vchart(source).spec()['label'],{'visible':True})
        with self.assertRaises(MermaidError) as caught:render(source,backend='cpu')
        error=caught.exception;self.assertEqual(error.code,'VCHART_SPEC_ERROR');self.assertIn('visible=false',str(error))
        self.assertEqual((error.span.start.index,error.span.end.index),(0,len(source)))
        self.assertEqual(error.spec_path,())

    def test_json_source_map_is_reliable_whole_payload_not_invented_fields(self):
        source='\n vchart\n'+json.dumps(SPEC)
        value=compile_vchart(source);self.assertEqual(len(value.source_map),1)
        span=value.source_map[0];self.assertEqual(span.path,())
        self.assertEqual(source[span.start:span.end],json.dumps(SPEC))

    def test_config_and_text_budget_are_explicit_not_execution_options(self):
        for config in [{'backend':'gpu'},{'maxTextSize':True},{'maxTextSize':float('inf')},{'maxTextSize':-1}]:
            with self.subTest(config=config),self.assertRaises(MermaidError):compile_vchart(DSL,config=config)
        with self.assertRaises(MermaidError) as caught:compile_vchart(DSL,config={'maxTextSize':3})
        self.assertEqual(caught.exception.code,'TEXT_LIMIT')


class NativeDslIntegrationTests(unittest.TestCase):
    def test_dsl_json_and_python_spec_same_cpu_content_and_scene(self):
        results=[render(DSL,backend='cpu'),render(source_json(SPEC),backend='cpu'),render_vchart(SPEC,backend='cpu')]
        for result in results:
            self.assertEqual((result.width,result.height),(180,120));self.assertEqual(dict(result.backend)['renderer'],'CPU')
            assert_ink(self,result.data)
        self.assertEqual(results[0].data,results[1].data);self.assertEqual(results[0].data,results[2].data)
        self.assertEqual(typed(results[0].layout),typed(results[2].layout))

    def test_async_api_and_compile_inside_active_loop(self):
        async def execute():
            self.assertEqual(compile_vchart(DSL).spec(),SPEC)
            result=await arender(DSL,backend='cpu');assert_ink(self,result.data)
            with self.assertRaises(MermaidError) as caught:render(DSL,backend='cpu')
            self.assertEqual(caught.exception.code,'ACTIVE_EVENT_LOOP')
        asyncio.run(execute())

    def test_pure_compilation_can_cross_threads_each_render_owns_native_context(self):
        compiled=compile_vchart(DSL)
        def draw(_):
            self.assertEqual(compiled.spec(),SPEC)
            result=render(DSL,backend='cpu');return result.data,dict(result.backend)['renderer']
        with ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(draw,range(2)))
        self.assertEqual(values[0],values[1]);self.assertEqual(values[0][1],'CPU')

    def test_actual_five_formats_and_density_on_dsl_path(self):
        from xml.etree import ElementTree
        from io import BytesIO
        from PIL import Image
        for format in ('png','jpg','webp','svg','pdf'):
            with self.subTest(format=format):
                result=render(DSL,format=format,backend='cpu',export_options=ExportOptions(density=2))
                if format in ('png','jpg','webp'):
                    image=Image.open(BytesIO(result.data));self.assertEqual(image.size,(360,240));assert_ink(self,result.data)
                elif format=='svg':
                    self.assertTrue(ElementTree.fromstring(result.data).tag.endswith('svg'))
                    self.assertNotIn(b'data:image/png;base64',result.data)
                else:self.assertTrue(result.data.startswith(b'%PDF'));self.assertIn(b'%%EOF',result.data[-2048:])

    def test_backend_and_format_stay_host_arguments_not_dsl_configuration(self):
        for kwargs,code in [({'backend':'software'},'INVALID_BACKEND'),({'format':'gif'},'UNSUPPORTED_FORMAT')]:
            with self.subTest(kwargs=kwargs),self.assertRaises(MermaidError) as caught:render(DSL,**kwargs)
            self.assertEqual(caught.exception.code,code)
