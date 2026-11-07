"""Render proposed examples' separate expected JSON, never execute new DSL."""
import argparse
import json
from pathlib import Path
import shutil

from py_mermaid import render_vchart
from run_support import ROOT, Run, file_identity, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples', type=Path,
                        default=ROOT / 'docs/proposals/vchart-v1/examples/manifest.json')
    args = parser.parse_args()
    manifest = args.examples.resolve(strict=True)
    definitions = json.loads(manifest.read_text('utf-8'))
    assert definitions['status'] == 'DESIGN_ONLY_NOT_IMPLEMENTED'
    with Run('VCHART-DSL-DESIGN', 'expected-json-preview') as run:
        run.input(manifest)
        rows = []
        for example in definitions['examples']:
            directory = run.path / 'artifacts' / example['id']
            directory.mkdir()
            for key in ('source', 'expectedSpec', 'resources'):
                original = (manifest.parent / example[key]).resolve(strict=True)
                assert original.is_relative_to(manifest.parent)
                run.input(original)
                shutil.copyfile(original, directory / original.name)
            spec = json.loads((manifest.parent / example['expectedSpec']).read_text('utf-8'))
            resources = json.loads((manifest.parent / example['resources']).read_text('utf-8'))
            assert spec['type'] == example['type']
            rendered = render_vchart(spec, backend='cpu', maps=resources['maps'], svgs=resources['svgs'])
            assert rendered.data.startswith(b'\x89PNG\r\n\x1a\n')
            assert dict(rendered.backend)['renderer'] == 'CPU'
            image = directory / 'expected-json.png'
            image.write_bytes(rendered.data)
            rows.append({'id': example['id'], 'type': spec['type'],
                         'status': 'EXPECTED_JSON_RENDERED_ONLY', 'dslExecuted': False,
                         'width': rendered.width, 'height': rendered.height,
                         'image': file_identity(image)})
        write_json(run.path / 'artifacts/result.json', {
            'status': 'EXISTING_JSON_API_PREVIEW_COMPLETE', 'dslExecuted': False,
            'scope': 'Independent expected specs only; proposed DSL parser/lowering is not implemented or verified.',
            'cases': rows}, exclusive=True)
        run.data['functionalStatus'] = 'DESIGN_PREVIEW_ONLY_NOT_NEW_DSL_ACCEPTANCE'
        run.data['result'] = {'examples': len(rows), 'dslExecuted': False}
        run.save()
    print(json.dumps({'run': str(run.path), 'status': run.data['status'], **run.data['result']}))


if __name__ == '__main__':
    main()
