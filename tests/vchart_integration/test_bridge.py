"""Consumer contracts from fixed official VChart captures and host API rules.

P2 defines these tests without executing them. Fixtures are local snapshots:
there is no adjacent-checkout import, sys.path fallback, or generated golden.
Natural Canvas font differences are permitted; data/mark identity is retained.
"""
from __future__ import annotations

import asyncio
import base64
import builtins
from collections.abc import Mapping
from contextlib import redirect_stderr
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass
import hashlib
from importlib import metadata
from io import BytesIO, StringIO
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from py_mermaid import (DiagramRenderResult, ExportOptions, FontResource, ImageResource,
    MermaidError, ResourceBundle, arender_vchart, detect_type, parse, render,
    render_vchart, supported_vchart_types)


FIXTURE = Path(__file__).with_name('cases-vchart.json')


def document():
    return json.loads(FIXTURE.read_text('utf-8'))


def case(kind):
    return next(row for row in document()['cases'] if row['type'] == kind)


def kwargs(row):
    return {'maps': row['maps'], 'svgs': row['svgs']}


def source(spec):
    return 'vchart\n' + json.dumps(spec, ensure_ascii=True, allow_nan=False)


def fixture_records(spec):
    """Read the fixture's explicit inline view without changing its shape."""
    view=spec['data']
    if isinstance(view,list):
        if len(view)!=1:raise AssertionError('This assertion requires one inline fixture view')
        view=view[0]
    return view['values']


def pure(value):
    """Reject native handles in an externally returned metadata graph."""
    if value is None or type(value) in (str, bytes, int, float, bool):
        return not isinstance(value, float) or math.isfinite(value)
    if isinstance(value, Mapping):
        return all(pure(k) and pure(v) for k, v in value.items())
    if isinstance(value, (tuple, list)):
        return all(pure(v) for v in value)
    if is_dataclass(value):
        return value.__dataclass_params__.frozen and all(pure(getattr(value, f.name)) for f in fields(value))
    return False


def json_value(value):
    """Serialize returned public pure metadata, never a native renderer."""
    if isinstance(value,Mapping):return {str(k):json_value(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [json_value(v) for v in value]
    if is_dataclass(value):return {f.name:json_value(getattr(value,f.name)) for f in fields(value)}
    return value


def new_json(path, value):
    with path.open('x',encoding='utf-8') as out:
        json.dump(json_value(value),out,indent=2,ensure_ascii=True,allow_nan=False)
        out.write('\n')


class BridgeAssertions(unittest.TestCase):
    def assert_code(self, code, function, *args, **options):
        with self.assertRaises(MermaidError) as caught:
            function(*args, **options)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def assert_png_content(self, result, width, height):
        from PIL import Image
        self.assertEqual(result.mime, 'image/png')
        self.assertTrue(result.data.startswith(b'\x89PNG\r\n\x1a\n'))
        with Image.open(BytesIO(result.data)) as image:
            self.assertEqual(image.size, (width, height))
            pixels = image.convert('RGBA').getdata()
            # A valid encode of a white/no-op surface must fail this gate.
            count = sum(a > 16 and min(r, g, b) < 250 for r, g, b, a in pixels)
            self.assertGreaterEqual(count, 8, 'real chart content is absent')


class FixtureAndParseContracts(BridgeAssertions):
    def test_b01_all_68_local_fixtures_retain_official_capture_identity(self):
        doc = document()
        self.assertEqual(len(doc['cases']), 68)
        self.assertEqual({row['type'] for row in doc['cases']}, set(supported_vchart_types()))
        self.assertEqual(len({row['id'].casefold() for row in doc['cases']}), 68)
        for row in doc['cases']:
            with self.subTest(type=row['type']):
                origin = row['origin']
                original_spec = base64.b64decode(origin['specBytesBase64'], validate=True)
                original_capture = base64.b64decode(origin['captureBytesBase64'], validate=True)
                self.assertEqual(hashlib.sha256(original_spec).hexdigest(), origin['specSha256'])
                self.assertEqual(hashlib.sha256(original_capture).hexdigest(), origin['captureSha256'])
                self.assertEqual(json.loads(original_spec.decode('utf-8-sig')), row['spec'])
                capture = json.loads(original_capture)
                self.assertEqual(capture['inputSha256'], origin['specSha256'])
                self.assertEqual(capture['pngSha256'], origin['pngSha256'])
                self.assertEqual(capture['bundleSha256'], origin['bundleSha256'])
                self.assertEqual(origin['commit'], 'fdb63276cf8b71f5a6cca128c409e009cc94615a')
                scene_bytes=base64.b64decode(origin['sceneBytesBase64'],validate=True)
                self.assertEqual(hashlib.sha256(scene_bytes).hexdigest(),origin['sceneSha256'])
                self.assertEqual(json.loads(scene_bytes),row['sourceScene'])
                for resource in origin['resources']:
                    data=base64.b64decode(resource['bytesBase64'],validate=True)
                    self.assertEqual(hashlib.sha256(data).hexdigest(),resource['sha256'])
                    self.assertEqual(resource['sha256'],resource['captureSha256'])
                    if row['type']=='map':self.assertEqual(json.loads(data),row['maps'][row['spec']['map']])
                    if row['type']=='pictogram':self.assertEqual(data.decode('utf-8'),row['svgs'][row['spec']['svg']])

    def test_b02_dependency_is_the_installed_release_not_adjacent_sources(self):
        import py_vchart
        self.assertEqual(metadata.version('py-visactor-vchart'), document()['providerVersion'])
        self.assertEqual(py_vchart.__version__, document()['providerVersion'])
        self.assertIn('site-packages', Path(py_vchart.__file__).resolve().parts)

    def test_b03_all_68_specs_parse_as_immutable_values_without_render(self):
        from py_mermaid.model.vchart import VChartModel
        for row in document()['cases']:
            with self.subTest(type=row['type']):
                diagram = parse(source(row['spec']))
                self.assertEqual(diagram.kind, 'vchart')
                self.assertIsInstance(diagram.model, VChartModel)
                self.assertEqual(diagram.model.spec(), row['spec'])
                self.assertEqual((diagram.model.width, diagram.model.height),
                                 (row['expected']['width'], row['expected']['height']))
                self.assertTrue(pure(diagram))

    def test_b04_json_directive_strings_remain_exact_data(self):
        spec = case('bar')['spec']
        original = '%%{init: {"theme":"dark"}}%% C4Context\n%% ordinary data'
        fixture_records(spec)[0][spec['xField']] = original
        self.assertEqual(parse(source(spec)).model.spec(), spec)
        self.assertEqual(detect_type(source(spec)), 'vchart')

    def test_b05_explicit_namespace_does_not_capture_existing_sequence_or_timeline(self):
        self.assertEqual(detect_type('timeline\n title Existing\n 2024 : Event'), 'timeline')
        self.assertEqual(detect_type('sequenceDiagram\nA->>B: Hi'), 'sequence')
        for kind in ('sequence', 'timeline'):
            self.assertEqual(parse(source(case(kind)['spec'])).model.spec()['type'], kind)

    def test_b06_malformed_header_does_not_fall_into_c4_detector(self):
        self.assertEqual(detect_type('vchart {"title":"C4Context"}'), 'vchart')
        self.assert_code('INVALID_VCHART_JSON', parse, 'vchart {"type":"bar","title":"C4Context"}')

    def test_b07_strict_json_rejects_duplicate_nonfinite_and_trailing_payload(self):
        for payload in ('{"type":"bar","type":"line"}', '{"type":"bar","n":NaN}',
                        '{"type":"bar","n":Infinity}', '{"type":"bar"} {}', ''):
            with self.subTest(payload=payload):
                self.assert_code('INVALID_VCHART_JSON', parse, 'vchart\n' + payload)

    def test_b08_json_error_span_uses_original_utf16_coordinates(self):
        text = 'vchart\n{"type":"bar", "emoji":"\U0001f600", "broken": }'
        exc = self.assert_code('INVALID_VCHART_JSON', parse, text)
        position = text.index('}')
        self.assertEqual(exc.span.start.index, position)
        self.assertEqual(exc.span.start.line, 2)
        self.assertEqual(exc.span.start.utf16_offset, len(text[:position].encode('utf-16-le')) // 2)

    def test_b09_unconsumed_mermaid_configuration_is_explicit_error(self):
        for config in ({'theme':'dark'}, {'layout':'elk'}, {'look':'neo'}, {'fontSize':30}):
            with self.subTest(config=config):
                self.assert_code('UNSUPPORTED_VCHART_CONFIG', parse, source(case('bar')['spec']), config=config)

    def test_b10_max_text_size_is_a_real_host_budget(self):
        raw = source(case('bar')['spec'])
        self.assert_code('TEXT_LIMIT', parse, raw, config={'maxTextSize':10})
        self.assertEqual(parse(raw, config={'maxTextSize':len(raw)*2}).kind, 'vchart')

    def test_b11_json_snapshot_preserves_empty_objects_arrays_and_caller_ownership(self):
        spec = case('bar')['spec']
        spec['marker'] = {'emptyObject':{}, 'emptyArray':[]}
        diagram = parse(source(spec))
        copy = diagram.model.spec()
        copy['marker']['emptyArray'].append(1)
        self.assertEqual(diagram.model.spec(), spec)
        with self.assertRaises(FrozenInstanceError):
            diagram.model.width = 12

    def test_b42_frontmatter_and_init_are_not_a_hidden_vchart_config_channel(self):
        raw=source(case('bar')['spec'])
        for prefix in ('---\ntitle: Hidden\n---\n','%%{init: {"theme":"dark"}}%%\n'):
            with self.subTest(prefix=prefix):
                with self.assertRaises(MermaidError) as caught:parse(prefix+raw)
                self.assertIn(caught.exception.code,('INVALID_VCHART_JSON','UNSUPPORTED_VCHART_CONFIG'))


class NativeBridgeContracts(BridgeAssertions):
    def test_b12_all_68_real_cpu_frames_and_source_mark_denominators(self):
        output=Path(os.environ['VCHART_ARTIFACTS']) if os.environ.get('VCHART_ARTIFACTS') else None
        if output is not None:output.mkdir(parents=True,exist_ok=True)
        summaries=[]
        for row in document()['cases']:
            with self.subTest(type=row['type']):
                folder=output/row['id'] if output is not None else None
                if folder is not None:folder.mkdir(exist_ok=False)
                evidence={'id':row['id'],'type':row['type'],'status':'FAIL'}
                try:
                    result = render_vchart(row['spec'], backend='cpu', **kwargs(row))
                    evidence.update(width=result.width,height=result.height,backend=dict(result.backend),mime=result.mime)
                    if folder is not None:
                        with (folder/'actual.png').open('xb') as out:out.write(result.data)
                        new_json(folder/'actual.scene.json',result.layout)
                        new_json(folder/'spec.json',row['spec'])
                    self.assertIsInstance(result, DiagramRenderResult)
                    self.assertEqual(result.diagram.kind, 'vchart')
                    self.assertEqual(result.diagram.model.spec(), row['spec'])
                    self.assert_png_content(result, row['expected']['width'], row['expected']['height'])
                    self.assertEqual(dict(result.backend)['renderer'], 'CPU')
                    self.assertTrue(pure(result.layout))
                    for key, expected in row['expected']['geometryCounts'].items():
                        if key.startswith('marks.'):
                            actual = result.layout.get('marks', {}).get(key[6:])
                        else:
                            actual = result.layout.get(key)
                        self.assertIsNotNone(actual, key)
                        self.assertEqual(len(actual), expected, key)
                except Exception as exc:
                    evidence.update(errorType=type(exc).__name__,error=str(exc))
                    raise
                else:
                    evidence['status']='PASS'
                finally:
                    summaries.append(evidence)
                    if folder is not None:new_json(folder/'result.json',evidence)
        if output is not None:
            new_json(output/'result.json',{'cases':summaries,'counts':{
                'total':len(summaries),'PASS':sum(r['status']=='PASS' for r in summaries),
                'FAIL':sum(r['status']!='PASS' for r in summaries)}})

    def test_b13_all_68_text_and_mapping_entrypoints_share_real_encoding(self):
        for row in document()['cases']:
            with self.subTest(type=row['type']):
                direct = render_vchart(row['spec'], backend='cpu', **kwargs(row))
                textual = render(source(row['spec']), backend='cpu', **kwargs(row))
                self.assertEqual(direct.data, textual.data)
                self.assertEqual((direct.width, direct.height, direct.mime),
                                 (textual.width, textual.height, textual.mime))

    def test_b14_production_all_68_reject_python_skia_and_javascript_imports(self):
        # A fresh interpreter catches eager imports as well as lazy render paths.
        script = '''
import builtins,json,sys
from pathlib import Path
original=builtins.__import__
def guard(name,*a,**kw):
    if name.split('.')[0] in {'skia','playwright','quickjs','execjs'}:
        raise AssertionError('production imported forbidden backend '+name)
    return original(name,*a,**kw)
builtins.__import__=guard
from py_mermaid import render_vchart
doc=json.loads(Path(sys.argv[1]).read_text('utf-8'))
for row in doc['cases']:
    r=render_vchart(row['spec'],backend='cpu',maps=row['maps'],svgs=row['svgs'])
    assert r.data.startswith(b'\\x89PNG'),row['id']
    assert dict(r.backend)['renderer']=='CPU',row['id']
print(json.dumps({'rendered':len(doc['cases']),'forbiddenImported':False}))
'''
        result = subprocess.run([sys.executable, '-c', script, str(FIXTURE.resolve())],
                                capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['rendered'], 68)

    def test_b15_all_export_formats_use_real_native_encoders(self):
        from PIL import Image
        row = case('bar')
        for fmt, magic in [('png',b'\x89PNG'),('jpg',b'\xff\xd8'),('jpeg',b'\xff\xd8'),
                           ('webp',b'RIFF'),('pdf',b'%PDF'),('svg',None)]:
            with self.subTest(format=fmt):
                r = render_vchart(row['spec'], format=fmt, backend='cpu')
                self.assertEqual((r.width,r.height),(row['expected']['width'],row['expected']['height']))
                if magic:self.assertTrue(r.data.startswith(magic))
                if fmt in ('png','jpg','jpeg','webp'):
                    with Image.open(BytesIO(r.data)) as im:self.assertEqual(im.size,(r.width,r.height))
                if fmt == 'webp':self.assertEqual(r.data[8:12],b'WEBP')
                if fmt == 'svg':
                    text=r.data.decode('utf-8')
                    self.assertIn('<svg',text)
                    self.assertRegex(text,r'<(?:\w+:)?(?:path|rect|text|use)\b')
                    self.assertNotIn('data:image/png;base64',text)

    def test_b16_raster_density_changes_physical_size_but_vector_size_is_logical(self):
        row = case('bar')
        for fmt in ('png','jpg','webp','svg','pdf'):
            with self.subTest(format=fmt):
                r=render_vchart(row['spec'],format=fmt,backend='cpu',export_options=ExportOptions(density=2))
                multiplier=2 if fmt in ('png','jpg','webp') else 1
                self.assertEqual((r.width,r.height),(row['expected']['width']*multiplier,row['expected']['height']*multiplier))
                if fmt=='png':self.assert_png_content(r,r.width,r.height)

    def test_b17_auto_returns_actual_device_and_explicit_gpu_never_claims_cpu_success(self):
        spec=case('bar')['spec']
        automatic=render_vchart(spec,backend='auto')
        self.assertIn(dict(automatic.backend)['renderer'],('CPU','GPU'))
        try:
            gpu=render_vchart(spec,backend='gpu')
        except MermaidError as exc:
            self.assertEqual(exc.code,'VCHART_RENDER_ERROR')
            self.assertIn('GPU',str(exc).upper())
            self.assertIsNotNone(exc.__cause__)
        else:
            self.assertEqual(dict(gpu.backend)['renderer'],'GPU')

    def test_b18_painter_vchart_returns_real_geometry_and_draws_vector_with_overlay(self):
        from py_mermaid.rendering.skia.scene import Painter
        p=Painter(parse('info'),backend='cpu')
        geometry=p.vchart(case('bar')['spec'],x=13,y=17,id='embedded-chart')
        self.assertIsInstance(geometry,Mapping)
        self.assertEqual(len(geometry['bars']),3)
        p.text('Overlay',20,20,html=False,id='overlay-label')
        scene=p.finish(padding=0,background='white')
        self.assertTrue(pure(scene))
        result=p.encode(scene,format='svg')
        text=result.data.decode('utf-8')
        self.assertIn('<svg',text)
        self.assertNotIn('data:image/png;base64',text)
        self.assertTrue(any(e.kind=='vchart' and e.semantic_id=='embedded-chart' for e in result.trace))
        self.assertTrue(any(e.semantic_id=='overlay-label' for e in result.trace))
        # Probe interiors from the independent browser's three bar rectangles,
        # rather than accepting metadata from a measuring pass while draw_to
        # silently paints nothing on the final host Canvas.
        from PIL import Image
        raster=p.encode(scene,format='png')
        with Image.open(BytesIO(raster.data)) as image:
            rgba=image.convert('RGBA')
            for x1,y1,x2,y2 in case('bar')['sourceScene']['bars']:
                at=(round((x1+x2)/2+13-scene.origin_x),round((y1+y2)/2+17-scene.origin_y))
                red,green,blue,alpha=rgba.getpixel(at)
                self.assertGreater(blue,red)
                self.assertGreater(blue,green)
                self.assertGreater(alpha,200)

    def test_b19_public_geometry_is_not_a_successful_empty_stub(self):
        result=render_vchart(case('bar')['spec'],backend='cpu')
        self.assertEqual(len(result.layout['bars']),3)
        self.assertGreater(len(result.layout['labels']),0)
        self.assert_png_content(result,400,240)
        # Independent white-Canvas negative control exercises the same ink gate.
        from py_skia_canvas import Canvas
        c=Canvas(400,240);c.gpu=False;ctx=c.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,400,240)
        from dataclasses import replace
        with self.assertRaises(AssertionError):
            self.assert_png_content(replace(result,data=bytes(c.toBufferSync('png'))),400,240)


class ErrorAndBudgetContracts(BridgeAssertions):
    def test_b20_unknown_type_and_nonobject_spec_are_precise_errors(self):
        self.assert_code('UNSUPPORTED_VCHART_TYPE',render_vchart,{'type':'Bar'},backend='cpu')
        for value in ([],None,'bar',3):
            with self.subTest(value=value):self.assert_code('INVALID_VCHART_SPEC',render_vchart,value)

    def test_b21_dimensions_reject_bool_fraction_zero_and_oversized_canvas(self):
        for value in (True,1.5,0,-1,8193):
            with self.subTest(width=value):
                self.assert_code('INVALID_VCHART_SIZE',render_vchart,case('bar')['spec']|{'width':value})
        self.assert_code('RENDER_BUDGET',render_vchart,case('bar')['spec']|{'width':8192,'height':8192})

    def test_b22_pixel_scatter_source_fixed_frame_is_300_square(self):
        spec=case('sequenceScatterPixel')['spec']|{'width':500,'height':200}
        result=render_vchart(spec,backend='cpu')
        self.assert_png_content(result,300,300)

    def test_b23_export_budget_and_option_types_are_enforced(self):
        self.assert_code('RENDER_BUDGET',render_vchart,case('bar')['spec'],export_options=ExportOptions(density=100))
        for options in (False,{'density':2},ExportOptions(density=True),ExportOptions(quality=float('nan'))):
            with self.subTest(options=options):
                self.assert_code('INVALID_EXPORT_OPTIONS',render_vchart,case('bar')['spec'],export_options=options)

    def test_b24_format_backend_and_nonchart_resource_arguments_are_rejected(self):
        self.assert_code('UNSUPPORTED_FORMAT',render_vchart,case('bar')['spec'],format='gif')
        self.assert_code('INVALID_BACKEND',render_vchart,case('bar')['spec'],backend='software')
        self.assert_code('INVALID_RESOURCE',render,'info',maps={})

    def test_b25_nonfinite_callable_cycles_and_nonstring_keys_do_not_enter_native(self):
        bad=[{'type':'bar','x':float('inf')},{'type':'bar','x':lambda:None},{'type':'bar',1:'x'}]
        cyclic={'type':'bar'};cyclic['loop']=cyclic;bad.append(cyclic)
        for spec in bad:
            with self.subTest(spec=type(spec)):
                self.assert_code('INVALID_VCHART_SPEC',render_vchart,spec)

    def test_b26_structural_depth_and_spec_bytes_have_finite_budgets(self):
        nested={};current=nested
        for _ in range(140):current['next']={};current=current['next']
        self.assert_code('VCHART_SPEC_BUDGET',render_vchart,{'type':'bar','nested':nested})
        self.assert_code('VCHART_SPEC_BUDGET',render_vchart,{'type':'bar','long':'x'*(8*1024*1024+1)})

    def test_b27_actual_renderer_errors_keep_their_cause_and_never_fallback(self):
        from py_vchart import VChart
        with patch.object(VChart,'render',side_effect=ValueError('source-layout-rejected')) as call:
            exc=self.assert_code('VCHART_SPEC_ERROR',render_vchart,case('bar')['spec'],backend='cpu')
            self.assertEqual(call.call_count,1)
            self.assertIsInstance(exc.__cause__,ValueError)
            self.assertIn('source-layout-rejected',str(exc))
        with patch.object(VChart,'render',side_effect=RuntimeError('native-device-failed')):
            exc=self.assert_code('VCHART_RENDER_ERROR',render_vchart,case('bar')['spec'],backend='cpu')
            self.assertIsInstance(exc.__cause__,RuntimeError)

    def test_b28_unsupported_chart_fields_are_not_silently_removed(self):
        exc=self.assert_code('VCHART_SPEC_ERROR',render_vchart,case('bar')['spec']|{'unsupportedStaticField':True},backend='cpu')
        self.assertIn('unsupportedStaticField',str(exc))


class ResourceContracts(BridgeAssertions):
    def test_b29_map_and_svg_resource_inputs_remain_caller_owned(self):
        for kind in ('map','pictogram'):
            row=case(kind);before=deepcopy(row)
            result=render_vchart(row['spec'],backend='cpu',**kwargs(row))
            self.assert_png_content(result,row['expected']['width'],row['expected']['height'])
            self.assertEqual(row,before)

    def test_b30_named_maps_and_svgs_do_not_leak_between_calls(self):
        for kind in ('map','pictogram'):
            row=case(kind)
            render_vchart(row['spec'],backend='cpu',**kwargs(row))
            self.assert_code('VCHART_SPEC_ERROR',render_vchart,row['spec'],backend='cpu')

    def test_b31_explicit_empty_resources_ignore_legacy_global_registrations(self):
        script='''
import json,sys
from pathlib import Path
from py_vchart import VChart
from py_mermaid import render_vchart,MermaidError
rows=json.loads(Path(sys.argv[1]).read_text('utf-8'))['cases']
for kind in ('map','pictogram'):
    row=next(r for r in rows if r['type']==kind)
    for k,v in row['maps'].items():VChart.register_map(k,v)
    for k,v in row['svgs'].items():VChart.register_svg_source(k,v)
    try:render_vchart(row['spec'],backend='cpu',maps={},svgs={})
    except MermaidError as exc:assert exc.code=='VCHART_SPEC_ERROR',exc
    else:raise AssertionError('global resource leaked into explicit empty instance')
print('isolated')
'''
        result=subprocess.run([sys.executable,'-c',script,str(FIXTURE.resolve())],capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'isolated')

    def test_b32_explicit_image_resource_matches_self_contained_original(self):
        row=case('imageCloud');spec=deepcopy(row['spec'])
        uri=spec['data']['values'][0]['url'];raw=base64.b64decode(uri.split(',',1)[1])
        original=render_vchart(spec,backend='cpu')
        spec['data']['values'][0]['url']='resource:tile'
        bundle=ResourceBundle(images=(ImageResource('tile',raw,'image/png',hashlib.sha256(raw).hexdigest()),))
        actual=render_vchart(spec,backend='cpu',resources=bundle)
        self.assertEqual(actual.data,original.data)

    def test_b33_resource_missing_integrity_and_wrong_bundle_fail_explicitly(self):
        spec=case('imageCloud')['spec'];spec['data']['values'][0]['url']='resource:missing'
        self.assert_code('RESOURCE_NOT_FOUND',render_vchart,spec,backend='cpu')
        bundle=ResourceBundle(images=(ImageResource('missing',b'not-an-image','image/png','0'*64),))
        self.assert_code('RESOURCE_INTEGRITY',render_vchart,spec,resources=bundle,backend='cpu')
        self.assert_code('INVALID_RESOURCE',render_vchart,case('bar')['spec'],resources=False)

    def test_b34_named_svg_external_events_entities_and_animation_are_rejected(self):
        row=case('pictogram');name=row['spec']['svg']
        for svg in ('<svg onload="alert(1)"/>','<svg><image href="https://example.invalid/x.png"/></svg>',
                    '<!DOCTYPE svg [<!ENTITY x "bad">]><svg/>','<svg><animate attributeName="x"/></svg>'):
            with self.subTest(svg=svg):
                self.assert_code('UNSAFE_RESOURCE',render_vchart,row['spec'],svgs={name:svg},backend='cpu')

    def test_b35_inline_svg_data_cannot_bypass_same_security_boundary(self):
        for svg in ('<svg onload="bad()"/>','<svg><image href="file:///secret.png"/></svg>'):
            spec=case('imageCloud')['spec']
            spec['data']['values'][0]['url']='data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()
            self.assert_code('UNSAFE_RESOURCE',render_vchart,spec,backend='cpu')

    def test_b36_svg_resource_validation_applies_inside_nested_spec_data(self):
        spec=case('bar')['spec']
        bad='data:image/svg+xml;base64,'+base64.b64encode(b'<svg><script>bad()</script></svg>').decode()
        fixture_records(spec)[0]['extra']={'deep':[bad]}
        self.assert_code('UNSAFE_RESOURCE',render_vchart,spec,backend='cpu')

    def test_b37_network_image_and_invalid_base64_are_errors_not_blank_success(self):
        for uri,code in [('https://example.invalid/image.png','VCHART_SPEC_ERROR'),
                         ('data:image/png;base64,!!!','INVALID_RESOURCE')]:
            spec=case('imageCloud')['spec'];spec['data']['values'][0]['url']=uri
            self.assert_code(code,render_vchart,spec,backend='cpu')

    def test_b43_font_resources_reuse_explicit_path_and_integrity_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);missing=root/'missing.ttf'
            bundle=ResourceBundle(fonts=(FontResource('Explicit',str(missing)),))
            self.assert_code('RESOURCE_NOT_FOUND',render_vchart,case('bar')['spec'],resources=bundle,backend='cpu')
            present=root/'present.ttf';present.write_bytes(b'untrusted-placeholder-font')
            bundle=ResourceBundle(fonts=(FontResource('Explicit',str(present),'0'*64),))
            self.assert_code('RESOURCE_INTEGRITY',render_vchart,case('bar')['spec'],resources=bundle,backend='cpu')

    def test_b44_declared_image_bytes_are_budgeted_even_when_not_used(self):
        bundle=ResourceBundle(images=(ImageResource('unused',b'x'*(32*1024*1024+1),'image/png'),))
        self.assert_code('RESOURCE_BUDGET',render_vchart,case('bar')['spec'],resources=bundle,backend='cpu')

    def test_b45_unused_font_bundle_never_registers_or_overrides_public_name(self):
        from py_skia_canvas import FontLibrary
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'unused.ttf';path.write_bytes(b'unused-opaque-font-bytes')
            bundle=ResourceBundle(fonts=(FontResource('Arial',str(path)),))
            with patch('py_skia_canvas.FontLibrary') as library:
                register=library.use
                result=render_vchart(case('bar')['spec'],resources=bundle,backend='cpu')
                self.assert_png_content(result,400,240)
                register.assert_not_called()

    def test_b46_custom_font_binding_uses_content_aliases_only_in_render_spec(self):
        from py_skia_canvas import FontLibrary
        from py_vchart import VChart
        spec=case('wordCloud')['spec'];spec['fontFamily']='Demo Face'
        spec['data']['values'][0]['fontFamily']='Demo Face'  # Inert data, not style.
        original=deepcopy(spec);captured=[];constructor=VChart.__init__
        def capture(instance,passed,*args,**options):
            captured.append(deepcopy(passed));constructor(instance,passed,*args,**options)
        with tempfile.TemporaryDirectory() as tmp:
            aliases=[]
            for index,raw in enumerate((b'first-font-content',b'second-font-content')):
                path=Path(tmp)/(str(index)+'.ttf');path.write_bytes(raw)
                bundle=ResourceBundle(fonts=(FontResource('Demo Face',str(path)),))
                with patch('py_skia_canvas.FontLibrary') as library, patch.object(VChart,'__init__',capture), \
                     patch.object(VChart,'render',side_effect=ValueError('binding-observed-before-shaping')):
                    register=library.use
                    self.assert_code('VCHART_SPEC_ERROR',render_vchart,spec,resources=bundle,backend='cpu')
                    expected='__py_mermaid_vchart_'+hashlib.sha256(raw).hexdigest()
                    self.assertEqual(register.call_args.args[0],expected)
                    self.assertNotEqual(register.call_args.args[0],'Demo Face')
                    self.assertEqual(captured[-1]['fontFamily'],expected)
                    self.assertEqual(captured[-1]['data'],original['data'])
                    aliases.append(expected)
            self.assertNotEqual(aliases[0],aliases[1])
        self.assertEqual(spec,original)
        self.assertEqual(parse(source(spec)).model.spec(),original)

    def test_b47_unsupported_custom_font_lists_do_not_silently_override_globals(self):
        from py_skia_canvas import FontLibrary
        spec=case('wordCloud')['spec'];spec['fontFamily']='Demo Face, serif'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'face.ttf';path.write_bytes(b'opaque-font-bytes')
            bundle=ResourceBundle(fonts=(FontResource('Demo Face',str(path)),))
            with patch('py_skia_canvas.FontLibrary') as library:
                register=library.use
                self.assert_code('UNSUPPORTED_VCHART_FONT',render_vchart,spec,resources=bundle,backend='cpu')
                register.assert_not_called()


class CLIContracts(BridgeAssertions):
    def test_b38_cli_offline_map_and_svg_flags_encode_real_content(self):
        from py_mermaid.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for kind in ('map','pictogram'):
                with self.subTest(type=kind):
                    row=case(kind);input_path=root/(kind+'.mmd');output=root/(kind+'.png');meta=root/(kind+'.meta.json')
                    maps=root/(kind+'.maps.json');svgs=root/(kind+'.svgs.json')
                    input_path.write_text(source(row['spec']),encoding='utf-8')
                    maps.write_text(json.dumps(row['maps']),encoding='utf-8');svgs.write_text(json.dumps(row['svgs']),encoding='utf-8')
                    stderr=StringIO()
                    with redirect_stderr(stderr):
                        code=main([str(input_path),'-o',str(output),'--metadata',str(meta),'--backend','cpu',
                                   '--vchart-maps',str(maps),'--vchart-svgs',str(svgs)])
                    self.assertEqual(code,0,stderr.getvalue())
                    values=json.loads(meta.read_text('utf-8'));self.assertEqual(values['backend']['renderer'],'CPU')
                    from PIL import Image
                    with Image.open(output) as image:
                        self.assertEqual(image.size,(row['expected']['width'],row['expected']['height']))
                        self.assertGreater(sum(min(p[:3])<250 for p in image.convert('RGBA').getdata()),8)

    def test_b39_cli_resource_manifest_is_never_overwritten_by_output(self):
        from py_mermaid.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);input_path=root/'chart.mmd';resources=root/'maps.json'
            input_path.write_text(source(case('map')['spec']),encoding='utf-8');resources.write_text(json.dumps(case('map')['maps']),encoding='utf-8')
            before=resources.read_bytes()
            with redirect_stderr(StringIO()):code=main([str(input_path),'-o',str(resources),'--vchart-maps',str(resources)])
            self.assertEqual(code,2);self.assertEqual(resources.read_bytes(),before)


class AsyncContracts(unittest.IsolatedAsyncioTestCase):
    async def test_b40_async_mapping_entrypoint_returns_real_frame(self):
        row=case('bar');result=await arender_vchart(row['spec'],backend='cpu')
        self.assertEqual((result.width,result.height),(400,240))
        self.assertEqual(len(result.layout['bars']),3)
        self.assertEqual(dict(result.backend)['renderer'],'CPU')

    async def test_b41_sync_vchart_api_refuses_nested_event_loop(self):
        with self.assertRaises(MermaidError) as caught:render_vchart(case('bar')['spec'])
        self.assertEqual(caught.exception.code,'ACTIVE_EVENT_LOOP')

