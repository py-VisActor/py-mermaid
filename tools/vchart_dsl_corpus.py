"""Independent source-spec formatter and immutable DSL corpus acquisition.

This developer formatter imports no product parser/compiler. Original JSON,
capture hashes and browser images remain the independent expected inputs.
"""
import argparse
import json
from pathlib import Path
import shutil

from run_support import ROOT, file_identity, write_json


def literal(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':'))


def table_value(value):
    if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
        columns = list(value[0])
        if columns and all(list(row) == columns and all(columns) for row in value):
            return 'table(' + ','.join(literal(c) for c in columns) + ') {\n' + '\n'.join(
                '[' + ','.join(table_value(row[c]) for c in columns) + ']' for row in value) + '\n}'
    if isinstance(value, dict):
        return '{' + ','.join(literal(k) + ':' + table_value(v) for k, v in value.items()) + '}'
    return literal(value)


def format_spec(spec, maps=None, svgs=None, *, sugar=False):
    lines = ['vchart ' + spec['type']]
    if sugar and 'data' in spec:
        lines.append('let _dataset = ' + table_value(spec['data']))
    for key, value in spec.items():
        if key == 'type':
            continue
        lines.append(literal(key) + ' = ' + ('$' + '_dataset' if sugar and key == 'data' else literal(value)))
    for name, value in (maps or {}).items():
        lines.append('resource map ' + literal(name) + ' = ' + literal(value))
    for name, value in (svgs or {}).items():
        lines.append('resource svg ' + literal(name) + ' = ' + literal(value))
    return '\n'.join(lines) + '\n'


def typed_equal(actual, expected, *, root=False):
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        if set(actual) != set(expected) or not root and list(actual) != list(expected):
            return False
        return all(typed_equal(actual[k], expected[k]) for k in expected)
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(typed_equal(a, e) for a, e in zip(actual, expected))
    return actual == expected


def freeze(out, supplier):
    out.mkdir(parents=True, exist_ok=False)
    cases = []
    source_files = sorted((supplier / 'tests/cases').glob('*/*/spec.json'))
    assert len(source_files) == 225
    def add(group, name, spec, maps, svgs, source, origin=None):
        folder = out / group / name
        folder.mkdir(parents=True)
        write_json(folder / 'expected.spec.json', spec, exclusive=True)
        write_json(folder / 'resources.json', {'maps': maps, 'svgs': svgs}, exclusive=True)
        (folder / 'source.vchart').write_text(source, 'utf-8')
        if origin:
            for filename in ('spec.json', 'capture.json', 'expected.scene.json', 'expected.png', 'geo.json', 'source.svg'):
                if (origin / filename).is_file():
                    shutil.copyfile(origin / filename, folder / ('upstream.png' if filename == 'expected.png' else 'origin-' + filename))
        cases.append({'id': name, 'type': spec['type'], 'group': group,
                      'folder': folder.relative_to(out).as_posix(),
                      'expected': file_identity(folder / 'expected.spec.json'),
                      'source': file_identity(folder / 'source.vchart')})
    for path in source_files:
        original = path.parent
        capture = json.loads((original / 'capture.json').read_text('utf-8'))
        assert file_identity(path)['sha256'] == capture['inputSha256']
        assert file_identity(original / 'expected.png')['sha256'] == capture['pngSha256']
        spec = json.loads(path.read_text('utf-8-sig'))
        maps, svgs = {}, {}
        if spec['type'] == 'map':
            assert file_identity(original / 'geo.json')['sha256'] == capture['geojsonSha256']
            maps[spec['map']] = json.loads((original / 'geo.json').read_text('utf-8'))
        if spec['type'] == 'pictogram':
            assert file_identity(original / 'source.svg')['sha256'] == capture['svgSha256']
            svgs[spec['svg']] = (original / 'source.svg').read_bytes().decode('utf-8')
        name = original.relative_to(supplier / 'tests/cases').as_posix()
        add('supplier', name, spec, maps, svgs, format_spec(spec, maps, svgs), original)
    representatives = json.loads((ROOT / 'tests/vchart_integration/cases-vchart.json').read_text('utf-8'))['cases']
    assert len(representatives) == 68
    for row in representatives:
        add('representative', row['id'], row['spec'], row['maps'], row['svgs'],
            format_spec(row['spec'], row['maps'], row['svgs'], sugar=True))
    example_root = ROOT / 'docs/proposals/vchart-v1/examples'
    examples = json.loads((example_root / 'manifest.json').read_text('utf-8'))['examples']
    assert len(examples) == 8
    for row in examples:
        spec = json.loads((example_root / row['expectedSpec']).read_text('utf-8'))
        resources = json.loads((example_root / row['resources']).read_text('utf-8'))
        add('example', row['id'], spec, resources['maps'], resources['svgs'],
            (example_root / row['source']).read_text('utf-8'))
    assert len(cases) == 301 and len({c['type'] for c in cases}) == 68
    result = {'schema': 'py-mermaid-vchart-dsl-corpus/v1', 'cases': cases,
              'groups': {'supplier': 225, 'representative': 68, 'example': 8},
              'note': '225 original specs and68 representatives overlap; this is not301 independent chart types.'}
    write_json(out / 'cases.json', result, exclusive=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--supplier', type=Path, default=ROOT.parent / 'py-vchart')
    args = parser.parse_args()
    result = freeze(args.out, args.supplier)
    print(json.dumps({'cases': len(result['cases']), 'groups': result['groups']}))
