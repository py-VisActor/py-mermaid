"""Actual seven-DSL native rendering with source literals and explicit limits.

Writes raw PNG/scene per successful input and truthful diagnostic_error records
for declared native restrictions. Uses the shared real ink/negative-control
checker, but does not apply the historical 31-detector exclusion catalogue.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import sys
import traceback

from bulk_validate import check_output, controls
from bulk_support import write, value_json
from run_support import ROOT, source_identity, environment_identity


def get(value, keys):
    for key in keys:
        value = value[key]
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixtures', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--backend', choices=('cpu', 'auto', 'gpu'), required=True)
    ap.add_argument('--export-formats', nargs='*', choices=('svg', 'pdf', 'jpg', 'webp'), default=[])
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    fixture = json.loads(args.fixtures.read_text(encoding='utf-8'))
    if fixture.get('schema') != 'py-mermaid-bulk-cases/v1':
        raise ValueError('Unexpected fixture schema')
    base = (ROOT / '.local/upstream-mermaid').resolve()
    all_cases = fixture['cases'] + fixture.get('unsupportedCases', [])
    seen = set()
    for c in all_cases:
        if c['id'] in seen:
            raise ValueError('Duplicate fixture id')
        seen.add(c['id'])
        origin = (base / c['origin']['path']).resolve(strict=True)
        origin.relative_to(base)
        if hashlib.sha256(origin.read_bytes()).hexdigest() != c['origin']['sha256']:
            raise ValueError('Fixed origin identity changed: ' + c['id'])
    from py_mermaid import render, MermaidError
    import py_vchart.layouts
    layout_path = Path(py_vchart.layouts.__file__).resolve()
    identity = source_identity()
    package = {'distribution': 'py-visactor-vchart', 'version': importlib.metadata.version('py-visactor-vchart'),
               'layouts': {'path': str(layout_path), 'sha256': hashlib.sha256(layout_path.read_bytes()).hexdigest()}}
    write(args.out / 'identity.json', {'source': identity, 'environment': environment_identity(),
                                     'backend': args.backend, 'provider': package})
    rows = []
    exported_kinds = set()
    for case in all_cases:
        restricted = bool(case.get('nativeExpectedErrorCodes'))
        row = {'id': case['id'], 'kind': case['kind'], 'group': 'A', 'expect': case['expect'],
               'status': 'ERROR', 'checks': [], 'nativeRestrictionOnly': restricted}
        try:
            result = render(case['source'], config=case.get('config'), backend=args.backend)
            (args.out / (case['id'] + '.png')).write_bytes(result.data)
            model = value_json(result.diagram.model)
            from py_mermaid.runtime.common import config_dict
            write(args.out / (case['id'] + '.scene.json'), {'width': result.width, 'height': result.height,
                  'diagram': result.diagram, 'layout': result.layout, 'trace': result.trace,
                  'measured': result.measured, 'annotations': result.annotations,
                  'backend': result.backend, 'diagnostics': result.diagnostics,
                  'effectiveConfig': config_dict(result.diagram)})
            if restricted or case['expect'] == 'syntax_error':
                row.update(status='FAILED', checks=['declared-error-was-accepted'])
            else:
                errors = check_output(result, case)
                faults = controls(result, case)
                if not all(faults.values()):
                    errors.append('checker-negative-controls-failed')
                semantic = []
                for expected in case.get('modelExpected', []):
                    actual = get(model, expected['path'])
                    semantic.append({**expected, 'actual': actual, 'matches': actual == expected['equals']})
                if any(not a['matches'] for a in semantic):
                    errors.append('source-model-field-mismatch')
                row.update(status='FAILED' if errors else 'CHECKS_PASSED', checks=errors,
                           controls=faults, semanticAssertions=semantic, width=result.width,
                           height=result.height, backend=value_json(result.backend))
                if args.export_formats and case['kind'] not in exported_kinds:
                    exported_kinds.add(case['kind'])
                    row['exports'] = []
                    for format in args.export_formats:
                        exported = render(case['source'], config=case.get('config'), backend=args.backend,
                                          format=format)
                        path = args.out / (case['id'] + '.' + format)
                        path.write_bytes(exported.data)
                        row['exports'].append({'format': format, 'path': str(path),
                            'sha256': hashlib.sha256(exported.data).hexdigest(),
                            'bytes': len(exported.data), 'width': exported.width, 'height': exported.height})
        except MermaidError as exc:
            codes = case.get('nativeExpectedErrorCodes') if restricted else case.get('expectedErrorCodes', [])
            accepted = (restricted or case['expect'] == 'syntax_error') and exc.code in codes
            row.update(status='DIAGNOSTIC_ERROR' if accepted and restricted else 'EXPECTED_ERROR' if accepted else 'FAILED',
                       errorCode=exc.code, message=str(exc), span=value_json(exc.span))
            if restricted:
                write(args.out / (case['id'] + '.diagnostic.json'), row)
        except Exception as exc:
            row.update(status='TOOL_OR_PRODUCT_ERROR', exception=type(exc).__name__, message=str(exc),
                       traceback=traceback.format_exc())
        rows.append(row)
        print(json.dumps({'id': case['id'], 'status': row['status']}, ensure_ascii=True), flush=True)
    unchanged = source_identity()['sourceTreeSha256'] == identity['sourceTreeSha256']
    failed = sum(r['status'] not in ('CHECKS_PASSED', 'EXPECTED_ERROR', 'DIAGNOSTIC_ERROR') for r in rows)
    summary = {'schema': 'py-mermaid-bulk-results/v1', 'source': identity, 'sourceUnchanged': unchanged,
               'backend': args.backend, 'provider': package, 'cases': rows, 'failed': failed,
               'normalRendered': sum(r['status'] == 'CHECKS_PASSED' for r in rows),
               'restrictionDiagnostics': sum(r['status'] == 'DIAGNOSTIC_ERROR' for r in rows),
               'exportFormats': args.export_formats, 'exportedKinds': sorted(exported_kinds),
               'functionalStatus': 'SOURCE_COMPARISON_AND_VISUAL_REVIEW_REQUIRED',
               'note': 'Explicit native restrictions are diagnostic records, never accepted rendered charts or source parse errors.'}
    write(args.out / 'results.json', summary)
    return int(bool(failed) or not unchanged)


if __name__ == '__main__':
    raise SystemExit(main())
