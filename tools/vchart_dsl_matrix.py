"""Execute a frozen301-case DSL/spec-API matrix on one real Canvas backend."""
import argparse
from collections import Counter
from collections.abc import Mapping
import importlib.metadata
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys
import traceback

from PIL import Image, ImageChops
from run_support import ROOT, file_identity, source_identity, write_json
from vchart_dsl_corpus import typed_equal


def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def texts(value):
    if isinstance(value, dict):
        return sum((texts(v) for v in value.values()), Counter())
    if isinstance(value, list):
        return sum((texts(v) for v in value), Counter())
    return Counter([value]) if isinstance(value, str) else Counter()


def structure(value):
    if isinstance(value, dict):
        return {k: structure(v) for k, v in value.items()}
    if isinstance(value, list):
        return [structure(v) for v in value]
    if value is None:
        return None
    return 'text' if isinstance(value, str) else 'number' if isinstance(value, (bool, int, float)) else type(value).__name__


def encoding(data, fmt, width, height):
    if fmt in ('png', 'jpg', 'webp'):
        with Image.open(BytesIO(data)) as im:
            assert im.size == (width, height), 'Encoded dimensions differ'
            assert im.format.lower() == {'png': 'png', 'jpg': 'jpeg', 'webp': 'webp'}[fmt]
    elif fmt == 'svg':
        from xml.etree import ElementTree
        tree = ElementTree.fromstring(data)
        assert tree.tag.rsplit('}', 1)[-1] == 'svg' and len(list(tree.iter())) > 1
    elif fmt == 'pdf':
        assert data.startswith(b'%PDF-') and b'%%EOF' in data[-2048:]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--backend', choices=('cpu', 'auto', 'gpu'), required=True)
    p.add_argument('--exports', action='store_true')
    args = p.parse_args()
    from py_mermaid import compile_vchart, render, render_vchart, supported_vchart_types
    import py_vchart
    assert not Path(py_vchart.__file__).resolve().is_relative_to((ROOT.parent / 'py-vchart/src').resolve())
    assert importlib.metadata.version('py-visactor-vchart') == '0.1.1'
    source = source_identity()
    corpus = json.loads((args.corpus / 'cases.json').read_text('utf-8'))
    assert len(corpus['cases']) == 301 and {c['type'] for c in corpus['cases']} == set(supported_vchart_types())
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    for item in corpus['cases']:
        folder = args.corpus / item['folder']
        target = args.out / item['folder']
        target.mkdir(parents=True)
        row = {**item, 'status': 'FAIL', 'errors': [], 'exports': []}
        try:
            assert file_identity(folder / 'source.vchart') == item['source']
            assert file_identity(folder / 'expected.spec.json') == item['expected']
            for file in folder.iterdir():
                if file.is_file():
                    shutil.copyfile(file, target / file.name)
            spec = json.loads((folder / 'expected.spec.json').read_text('utf-8'))
            resources = json.loads((folder / 'resources.json').read_text('utf-8'))
            text = (folder / 'source.vchart').read_text('utf-8')
            compilation = compile_vchart(text)
            compiled = compilation.spec()
            assert typed_equal(compiled, spec, root=True), 'Compiled JSON type/value/order differs from original'
            assert typed_equal(compilation.maps(), resources['maps']) and typed_equal(compilation.svg_sources(), resources['svgs']), 'Resource snapshot differs'
            assert compilation.syntax == 'dsl' and compilation.source_map
            assert all(0 <= s.start <= s.end <= len(text) for s in compilation.source_map)
            assert all(any(s.namespace == 'spec' and s.path == (k,) for s in compilation.source_map) for k in spec), 'A top-level source map path is missing'
            write_json(target / 'compiled.json', compilation.as_dict(), exclusive=True)
            api = render_vchart(spec, backend=args.backend, **resources)
            actual = render(text, backend=args.backend)
            assert (actual.width, actual.height) == (api.width, api.height)
            engine = dict(actual.backend)
            assert engine['renderer'] == ('CPU' if args.backend == 'cpu' else 'GPU') if args.backend != 'auto' else engine['renderer'] in ('CPU', 'GPU')
            assert engine['renderer'] == dict(api.backend)['renderer']
            row.update(width=actual.width, height=actual.height, engine=engine)
            (target / 'api.png').write_bytes(api.data)
            (target / 'actual.png').write_bytes(actual.data)
            api_scene, dsl_scene = plain(api.layout), plain(actual.layout)
            write_json(target / 'api.scene.json', api_scene, exclusive=True)
            write_json(target / 'dsl.scene.json', dsl_scene, exclusive=True)
            assert typed_equal(dsl_scene, api_scene), 'DSL scene differs from spec API'
            a = Image.open(BytesIO(api.data)).convert('RGBA')
            b = Image.open(BytesIO(actual.data)).convert('RGBA')
            assert a.size == b.size
            difference = ImageChops.difference(a, b)
            difference.save(target / 'diff.png')
            row['exactPixels'] = a.tobytes() == b.tobytes()
            assert row['exactPixels'], 'Same-backend DSL pixels differ from identical spec API'
            if item['group'] == 'supplier':
                expected_scene = json.loads((folder / 'origin-expected.scene.json').read_text('utf-8'))
                with Image.open(folder / 'upstream.png') as upstream:
                    if len(upstream.convert('RGBA').getcolors(upstream.width * upstream.height) or ()) > 1:
                        assert len(b.getcolors(b.width * b.height) or ()) > 1, 'Visible original became a blank output'
                row['upstreamTextEqual'] = texts(dsl_scene) == texts(expected_scene)
                row['upstreamStructureEqual'] = structure(dsl_scene) == structure(expected_scene)
                if item['id'] in ('wordCloud/default-filling', 'wordCloud/filled-mask'):
                    policy_file = ROOT.parent / 'py-vchart/tools/native_wordcloud_policy.py'
                    definition = importlib.util.spec_from_file_location('dsl_native_font_policy', policy_file)
                    policy = importlib.util.module_from_spec(definition)
                    definition.loader.exec_module(policy)
                    result = policy.check(item['id'], (folder / 'origin-spec.json').read_bytes(), dsl_scene, actual.data, expected_scene)
                    write_json(target / 'native-font-policy.json', result, exclusive=True)
                    row['nativeFontPolicy'] = result
                    assert result['status'] == 'PASS', 'Existing independent word-cloud glyph/mask policy failed'
                else:
                    assert row['upstreamTextEqual'] and row['upstreamStructureEqual'], 'Original content/mark structure differs'
            if args.exports and item['group'] == 'representative':
                for fmt in ('svg', 'pdf', 'jpg', 'webp'):
                    exported = render(text, backend=args.backend, format=fmt)
                    encoding(exported.data, fmt, exported.width, exported.height)
                    if fmt == 'svg' and item['type'] == 'bar':
                        assert b'data:image/png;base64' not in exported.data, 'Vector output replaced by a screenshot'
                    file = target / ('actual.' + fmt)
                    file.write_bytes(exported.data)
                    row['exports'].append({'format': fmt, 'path': file.name, **file_identity(file)})
            row['status'] = 'PASS'
        except Exception as exc:
            row['errors'].append(type(exc).__name__ + ': ' + str(exc))
            (target / 'error.txt').write_text(traceback.format_exc(), 'utf-8')
        write_json(target / 'result.json', row, exclusive=True)
        rows.append(row)
        print(json.dumps({'group': item['group'], 'id': item['id'], 'status': row['status']}), flush=True)
    result = {'schema': 'py-mermaid-vchart-dsl-matrix/v1', 'backend': args.backend, 'source': source,
              'sourceUnchanged': source_identity() == source, 'cases': rows,
              'counts': {g: {'cases': sum(r['group'] == g for r in rows), 'passed': sum(r['group'] == g and r['status'] == 'PASS' for r in rows)} for g in corpus['groups']},
              'types': sorted({r['type'] for r in rows}), 'failed': sum(r['status'] != 'PASS' for r in rows),
              'providerVersion': importlib.metadata.version('py-visactor-vchart'),
              'providerModule': str(Path(py_vchart.__file__).resolve()), 'exports': args.exports}
    write_json(args.out / 'result.json', result, exclusive=True)
    return int(result['failed'] != 0 or not result['sourceUnchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
