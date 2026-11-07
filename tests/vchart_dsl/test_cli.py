"""CLI compile is complete inspectable JSON, not an image or hidden render."""
from contextlib import redirect_stderr,redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from py_mermaid.cli import main
try:from .support_c import DSL,SPEC,GEO,SVG,resource_dsl,NoFontLibrary
except ImportError:from support_c import DSL,SPEC,GEO,SVG,resource_dsl,NoFontLibrary


class DslCliTests(unittest.TestCase):
    def execute(self,args,stdin=''):
        stdout,stderr=StringIO(),StringIO()
        with patch('sys.stdin',StringIO(stdin)),redirect_stdout(stdout),redirect_stderr(stderr):
            code=main(args)
        return code,stdout.getvalue(),stderr.getvalue()

    def test_stdin_compile_and_alias_are_full_json_without_renderer(self):
        for flag in ('--compile','--compile-only'):
            with self.subTest(flag=flag),patch('py_mermaid.cli.render',side_effect=AssertionError('compile rendered')):
                code,out,err=self.execute(['-',flag],DSL)
            self.assertEqual(code,0,err);value=json.loads(out)
            self.assertEqual(value['spec'],SPEC);self.assertEqual(value['source'],DSL)
            self.assertEqual(value['maps'],{});self.assertEqual(value['svgs'],{});self.assertTrue(value['source_map'])
            self.assertEqual(value['diagnostics'],[]);self.assertEqual(value['syntax'],'dsl')

    def test_file_compile_json_keeps_inline_map_svg_and_source_spans(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.vchart';output=root/'compiled.json'
            text=resource_dsl('map')+'resource svg "quad" = '+json.dumps(SVG)+'\n'
            source.write_text(text,encoding='utf8')
            code,out,err=self.execute([str(source),'--compile','-o',str(output)])
            self.assertEqual(code,0,err);self.assertEqual(out,'');value=json.loads(output.read_text('utf8'))
            self.assertEqual(value['maps'],{'local':GEO});self.assertEqual(value['svgs'],{'quad':SVG})
            self.assertEqual({s['namespace'] for s in value['source_map']},{'spec','map','svg'})
            self.assertEqual(source.read_text('utf8'),text)

    def test_explicit_map_and_svg_flags_are_included_not_discarded(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);maps=root/'maps.json';svgs=root/'svgs.json'
            maps.write_text(json.dumps({'local':GEO}));svgs.write_text(json.dumps({'quad':SVG}))
            code,out,err=self.execute(['-','--compile','--vchart-maps',str(maps),'--vchart-svgs',str(svgs)],DSL)
            self.assertEqual(code,0,err);value=json.loads(out)
            self.assertEqual(value['maps'],{'local':GEO});self.assertEqual(value['svgs'],{'quad':SVG})

    def test_compile_never_allocates_canvas_or_registers_fonts(self):
        from py_skia_canvas import Canvas
        font_guard=NoFontLibrary()
        with (patch.object(Canvas,'__init__',side_effect=AssertionError('CLI allocated Canvas')),
              patch('py_skia_canvas.FontLibrary',new=font_guard)):
            code,out,err=self.execute(['-','--compile','--backend','gpu','--format','pdf','--density','2'],DSL)
        font_guard.use.assert_not_called()
        self.assertEqual(code,0,err);self.assertEqual(json.loads(out)['spec'],SPEC)

    def test_input_and_all_explicit_input_manifests_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.vchart';source.write_text(DSL)
            config=root/'config.json';config.write_text('{}')
            maps=root/'maps.json';maps.write_text('{}')
            svgs=root/'svgs.json';svgs.write_text('{}')
            for destination in (source,config,maps,svgs):
                before=destination.read_bytes()
                code,out,err=self.execute([str(source),'--compile','--config',str(config),
                    '--vchart-maps',str(maps),'--vchart-svgs',str(svgs),'-o',str(destination)])
                self.assertEqual(code,2);self.assertIn('overwrite',json.loads(err)['message'])
                self.assertEqual(destination.read_bytes(),before)

    def test_compile_resourcebundle_and_render_metadata_flags_are_explicit_errors(self):
        for flag in ('--resources','--metadata'):
            with self.subTest(flag=flag):
                code,out,err=self.execute(['-','--compile',flag,'does-not-have-to-exist.json'],DSL)
                self.assertEqual(code,2);self.assertEqual(out,'');self.assertEqual(json.loads(err)['code'],'CLI_INPUT_ERROR')

    def test_error_json_retains_related_codepoint_pairs_and_utf16_span(self):
        source=DSL+'%% 😀\nxField = "duplicate"\n'
        code,out,err=self.execute(['-','--compile'],source)
        self.assertEqual(code,1);self.assertEqual(out,'');value=json.loads(err)
        self.assertEqual(value['code'],'VCHART_DSL_DUPLICATE_WRITE')
        self.assertEqual(value['spec_path'],['xField']);self.assertTrue(value['related_spans'])
        self.assertTrue(all(len(pair)==2 and all(type(i) is int for i in pair) for pair in value['related_spans']))
        start=value['span']['start'];self.assertEqual(start['utf16_offset'],len(source[:start['index']].encode('utf-16-le'))//2)

    def test_cli_fixed_size_compilation_surfaces_diagnostic(self):
        code,out,err=self.execute(['-','--compile'],'vchart sequenceScatterPixel\nsize 100 120\n')
        self.assertEqual(code,0,err);value=json.loads(out)
        self.assertEqual((value['width'],value['height']),(300,300))
        self.assertEqual((value['spec']['width'],value['spec']['height']),(100,120))
        self.assertTrue(any(d['code']=='VCHART_FIXED_SIZE' for d in value['diagnostics']))

    def test_cli_legacy_json_invalid_payload_is_still_structured_json_error(self):
        code,out,err=self.execute(['-','--compile'],'vchart\n{"type":"bar",}')
        self.assertEqual(code,1);self.assertEqual(out,'');value=json.loads(err)
        self.assertEqual(value['code'],'INVALID_VCHART_JSON');self.assertIsNotNone(value['span'])

    def test_cli_render_remains_real_image_with_actual_backend_metadata(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.vchart';image=root/'image.png';meta=root/'meta.json'
            source.write_text(DSL)
            code,out,err=self.execute([str(source),'-o',str(image),'--metadata',str(meta),'--backend','cpu'])
            self.assertEqual(code,0,err);self.assertEqual(out,'')
            with Image.open(image) as actual:self.assertEqual(actual.size,(180,120))
            data=json.loads(meta.read_text('utf8'));self.assertEqual(data['backend']['renderer'],'CPU');self.assertEqual(data['mime'],'image/png')
