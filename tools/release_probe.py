"""Run outside the workspace with -I, using installed packages and frozen data."""
from __future__ import annotations

import argparse
import builtins
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
import hashlib
import html
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import struct
import sys
import unittest


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def plain(value):
    if is_dataclass(value):
        return {field.name: plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def exact(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(exact(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
    return a == b


def normalized(text):
    return re.sub(r'\s+', '', html.unescape(str(text)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixtures', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--workspace', required=True, type=Path)
    p.add_argument('--expected-version', required=True)
    p.add_argument('--expected-project', default='py-visactor-mermaid')
    p.add_argument('--pip-report', type=Path)
    p.add_argument('--suite', type=Path)
    args = p.parse_args()
    assert sys.flags.isolated == 1, 'Installed verification requires -I'
    workspace, prefix = args.workspace.resolve(), Path(sys.prefix).resolve()
    assert not Path.cwd().resolve().is_relative_to(workspace), 'Verification cwd belongs to workspace'
    args.out.mkdir(parents=True, exist_ok=False)
    original = builtins.__import__
    def guarded(name, *values, **kwargs):
        if name.split('.')[0] in {'skia', 'playwright', 'quickjs', 'execjs', 'selenium'}:
            raise AssertionError('Forbidden production import: ' + name)
        return original(name, *values, **kwargs)
    builtins.__import__ = guarded
    import py_mermaid, py_vchart, py_katex, pyelk, py_skia_canvas
    from py_mermaid import parse, render, render_vchart, compile_vchart, MermaidError
    from py_skia_canvas import Canvas, Image
    modules = (py_mermaid, py_vchart, py_katex, pyelk, py_skia_canvas)
    def installed_modules():
        paths = {}
        for name, module in tuple(sys.modules.items()):
            if name.split('.')[0] not in {'py_mermaid', 'py_vchart', 'py_katex', 'pyelk', 'py_skia_canvas'}:
                continue
            file = getattr(module, '__file__', None)
            if file:
                path = Path(file).resolve()
                assert path.is_relative_to(prefix) and not path.is_relative_to(workspace), str(path)
                paths[name] = str(path)
        return paths
    installed_modules()
    assert py_mermaid.__version__ == metadata.version(args.expected_project) == args.expected_version
    doc = json.loads(args.fixtures.read_text('utf-8'))
    if args.suite:
        # Every test is copied outside the checkout, without any product source.
        assert not args.suite.resolve().is_relative_to(workspace)
        suite = unittest.defaultTestLoader.discover(str(args.suite / 'closure'), top_level_dir=str(args.suite))
        with (args.out / 'unittest.log').open('w', encoding='utf-8') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        report = {'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'methodInvocations': result.testsRun,
            'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
            'isolated': True, 'prefix': str(prefix), 'modulePaths': installed_modules()}
        (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', 'utf-8')
        assert result.wasSuccessful(), 'Installed closure contracts failed: ' + str(args.out / 'unittest.log')
        assert result.testsRun > 0
        print(json.dumps({'status': report['status'], 'methodInvocations': result.testsRun}))
        return

    lock = doc['supplierLock']
    assert metadata.version('py-visactor-vchart') == lock['version']
    assert metadata.distribution('py-visactor-vchart').read_text('direct_url.json') is None
    report = json.loads(args.pip_report.read_text('utf-8'))
    supplier = [row for row in report['install'] if row['metadata']['name'].lower().replace('_', '-') == 'py-visactor-vchart']
    assert len(supplier) == 1
    download = supplier[0]['download_info']
    assert download['url'] == lock['asset']['url'] and download['archive_info']['hashes']['sha256'] == lock['asset']['sha256']

    def rgba(data, dimensions):
        surface = Canvas(*dimensions)
        surface.gpu = False
        ctx = surface.getContext('2d')
        ctx.drawImage(Image(data), 0, 0)
        return bytes(ctx.getImageData(0, 0, *dimensions).data)

    def image_result(result, name, expected=()):
        assert result.mime == 'image/png' and result.data[:8] == b'\x89PNG\r\n\x1a\n'
        size = struct.unpack('>II', result.data[16:24])
        assert size == (result.width, result.height) and min(size) > 0
        assert dict(result.backend)['renderer'] == 'CPU'
        visible = normalized(''.join(e.text or '' for e in getattr(result, 'trace', ()) if e.opacity > 0))
        for text in expected:
            assert normalized(text) in visible, (name, 'missing expected text', text, visible)
        pixels = rgba(result.data, size)
        ink = sum(pixels[i + 3] > 0 and min(pixels[i:i + 3]) < 245 for i in range(0, len(pixels), 4))
        assert ink >= 8, (name, 'empty paint')
        (args.out / (name + '.png')).write_bytes(result.data)
        return {'id': name, 'status': 'PASS', 'width': size[0], 'height': size[1], 'renderer': 'CPU',
                'inkPixels': ink, **identity(result.data)}

    assert len(doc['diagrams']) == 38
    diagram_rows = []
    for case in doc['diagrams']:
        result = render(case['source'], config=case.get('config', {}), backend='cpu')
        row = image_result(result, case['id'], case.get('expectedText', []))
        row['kind'] = case['kind']
        diagram_rows.append(row)
    assert {r['kind'] for r in diagram_rows} == set(py_mermaid.registered_diagrams()) - {'vchart'}

    assert len(doc['vchart']) == 68
    chart_rows = []
    for row in doc['vchart']:
        result = render_vchart(row['spec'], maps=row['maps'], svgs=row['svgs'], backend='cpu')
        image_result(result, row['id'])
        compiled = compile_vchart(row['dslSource'])
        # Root type moves to the header; nested object insertion order must stay.
        expected = {'type': row['spec']['type'], **row['spec']}
        assert exact(compiled.spec(), expected), row['id']
        assert exact(compiled.maps(), row['maps']) and exact(compiled.svg_sources(), row['svgs']), row['id']
        actual = render(row['dslSource'], backend='cpu')
        size = (result.width, result.height)
        assert size == (actual.width, actual.height) and rgba(result.data, size) == rgba(actual.data, size), row['id']
        image_result(actual, row['id'] + '-dsl')
        chart_rows.append({'id': row['id'], 'type': row['type'], 'status': 'PASS', 'decodedPixelsEqual': True})
    assert {r['type'] for r in chart_rows} == set(py_mermaid.supported_vchart_types())

    closure_rows = []
    for row in doc['closure']:
        expected_error = row.get('expect') in ('syntax_error', 'error')
        try:
            parsed = parse(row['source'], config=row.get('config', {}))
            assert not expected_error, row['id']
            model = plain(getattr(parsed, 'model', parsed))
            for check in row.get('nativeChecks', []):
                value = model
                for part in check['path']:
                    value = value[part]
                assert value == check['equals'], (row['id'], check, value)
            if row.get('expect') == 'render' and not row.get('parserOnly'):
                result = render(row['source'], config=row.get('config', {}), backend='cpu')
                image_result(result, row['id'], row.get('expectedText', []))
            closure_rows.append({'id': row['id'], 'status': 'PASS', 'parserOnly': bool(row.get('parserOnly'))})
        except MermaidError as error:
            assert expected_error and error.code in row.get('expectedErrorCodes', []), (row['id'], error.code, str(error))
            closure_rows.append({'id': row['id'], 'status': 'EXPECTED_ERROR', 'errorCode': error.code})

    math_source = 'flowchart LR\n A["$$\\frac{1}{2}$$"] --> B[Beta]\n'
    mathematical = render(math_source, backend='cpu')
    image_result(mathematical, 'math-and-elk')
    assert any(e.kind == 'math-glyph' for e in mathematical.trace), 'No actual formula glyph draw'
    assert mathematical.layout.engine == 'pyelk/elk.layered' and len(mathematical.layout.edges) == 1
    exports = []
    for fmt, extension in [('svg', 'svg'), ('pdf', 'pdf'), ('jpg', 'jpg'), ('webp', 'webp')]:
        output = render('flowchart LR\n A[Alpha] --> B[Beta]', backend='cpu', format=fmt)
        raw = output.data
        assert raw and (b'<svg' in raw[:1500] if fmt == 'svg' else raw.startswith(b'%PDF-') if fmt == 'pdf' else len(raw) > 100)
        if fmt == 'svg':
            assert b'data:image/png;base64' not in raw, 'Vector is a full PNG screenshot'
        (args.out / ('representative.' + extension)).write_bytes(raw)
        exports.append({'format': fmt, **identity(raw)})
    result = {'schema': 'py-mermaid-installed-release/v1', 'status': 'PASS', 'isolated': True,
        'project': args.expected_project, 'version': args.expected_version, 'prefix': str(prefix),
        'workspace': str(workspace), 'modulePaths': installed_modules(), 'diagrams': diagram_rows,
        'vchart': chart_rows, 'closure': closure_rows, 'actualMathGlyphs': True, 'realELK': True,
        'exports': exports, 'resolvedSupplier': download, 'fixture': identity(args.fixtures.read_bytes()),
        'forbiddenProductionFallbacks': False}
    (args.out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps({'status': 'PASS', 'diagrams': len(diagram_rows), 'chartTypes': len(chart_rows), 'closureCases': len(closure_rows)}))


if __name__ == '__main__':
    main()
