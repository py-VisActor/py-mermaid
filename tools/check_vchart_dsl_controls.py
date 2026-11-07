"""Independent negative controls for corpus comparison, with no product calls."""
import json

from vchart_dsl_corpus import format_spec, typed_equal


def main():
    expected = {'type': 'sequenceScatterPixel', 'data': dict([
        ('z-last-alphabetically', [{'x': 1, 'y': 2, 'flag': False}]),
        ('a-first-alphabetically', [{'x': 8, 'y': 9, 'flag': True}])])}
    assert typed_equal(expected, expected, root=True)
    assert not typed_equal({'v': False}, {'v': 0}, root=True)
    assert not typed_equal({'v': 1}, {'v': 1.0}, root=True)
    assert not typed_equal({'v': []}, {'v': {}}, root=True)
    assert not typed_equal({'v': [1, 2]}, {'v': [2, 1]}, root=True)
    changed = dict(expected)
    changed['data'] = dict(reversed(list(expected['data'].items())))
    assert not typed_equal(changed, expected, root=True)
    assert not typed_equal({'type': expected['type']}, expected, root=True)
    assert not typed_equal({'v': 'changed'}, {'v': 'original'}, root=True)
    source = format_spec(expected, sugar=True)
    assert source.index('z-last-alphabetically') < source.index('a-first-alphabetically')
    assert 'false' in source and 'true' in source and '$' in source
    print(json.dumps({'status': 'PASS', 'controls': 9, 'productExecuted': False}))


if __name__ == '__main__':
    main()
