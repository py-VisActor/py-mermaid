"""Read completed evidence only; never run parse/build/render in this comparator.

--oracle is bulk_capture's directory; --getters is oracle_a.cjs output.
Source/native expectation failures remain separate. Unasserted visual questions
are EVIDENCE_INSUFFICIENT, never a rendering-success compatibility claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
from support_a import select


def read(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def check(data, assertions):
    result = []
    for assertion in assertions:
        try:
            actual = select(data, assertion['path'])
            result.append({**assertion, 'actual': actual, 'matches': actual == assertion['equals']})
        except (KeyError, IndexError, TypeError) as exc:
            result.append({**assertion, 'error': str(exc), 'matches': False})
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--oracle', type=Path, required=True)
    ap.add_argument('--native', type=Path, required=True)
    ap.add_argument('--getters', type=Path, required=True)
    ap.add_argument('--fixtures', type=Path, default=Path(__file__).with_name('cases-A.json'))
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError('New output required: ' + str(args.out))
    rows = []
    native_manifest = read(args.native / 'results.json') or {}
    native_rows = {r['id']: r for r in native_manifest.get('cases', native_manifest.get('results', []))}
    for case in read(args.fixtures)['cases']:
        id = case['id']
        original = read(args.oracle / (id + '.json'))
        source_error = read(args.oracle / (id + '.error.json'))
        getter = read(args.getters / (id + '.json'))
        native = read(args.native / (id + '.scene.json'))
        expected = case['branchExpected']
        row = {'id': id, 'expected': expected, 'classification': 'EVIDENCE_INSUFFICIENT',
               'sourceActual': {'rendered': original is not None, 'error': source_error,
                                'getters': getter}, 'nativeActual': {'rendered': native is not None}}
        source_checks = check((getter or {}).get('snapshot', {}), expected['sourceChecks'])
        native_checks = check((native or {}).get('diagram', {}).get('model', {}), expected['nativeChecks'])
        row.update(sourceAssertions=source_checks, nativeAssertions=native_checks)
        row['sourceExpectedMismatch'] = any(not a['matches'] for a in source_checks)
        row['nativeExpectedMismatch'] = any(not a['matches'] for a in native_checks)
        if getter is None or (original is None and source_error is None):
            row['classification'] = 'TOOL_ERROR'
        elif case['expect'] == 'syntax_error':
            native_row = native_rows.get(id, {})
            row['nativeActual']['result'] = native_row
            source_rejected = getter.get('status') == 'SOURCE_PARSE_ERROR' and source_error is not None
            native_rejected = native_row.get('errorCode') in case['expectedErrorCodes']
            row['classification'] = ('MATCHED_DECLARED_SOURCE_REJECTION' if source_rejected and native_rejected
                                     else 'SOURCE_EXPECTATION_MISMATCH' if not source_rejected
                                     else 'CONFIRMED_GAP')
        elif row['sourceExpectedMismatch']:
            row['classification'] = 'SOURCE_EXPECTATION_MISMATCH'
        elif source_error is not None:
            row['classification'] = 'SOURCE_RENDER_ERROR_REQUIRES_REVIEW'
        elif native is None:
            row['classification'] = 'NATIVE_RENDER_ERROR'
        elif row['nativeExpectedMismatch']:
            row['classification'] = 'CONFIRMED_GAP' if source_checks else 'NATIVE_ASSERTION_FAILURE_SOURCE_REVIEW_REQUIRED'
        elif source_checks and native_checks:
            row['classification'] = 'MATCHED_DECLARED_SOURCE_FIELDS'
        else:
            row['reason'] = 'Visual/geometry/active-consumer original comparison still required; acceptance alone cannot close this branch.'
        for side, directory in [('original', args.oracle), ('native', args.native)]:
            png = directory / (id + '.png')
            row[side + 'Png'] = None if not png.exists() else {
                'path': str(png.resolve()), 'sha256': hashlib.sha256(png.read_bytes()).hexdigest()}
        rows.append(row)
    fixture = args.fixtures
    manifest = read(args.getters / 'manifest.json')
    identity_valid = manifest is not None and manifest.get('fixtureSha256') == hashlib.sha256(fixture.read_bytes()).hexdigest()
    report = {'schema': 'branch-A-evidence-comparison/v1', 'fixtureIdentityMatches': identity_valid,
              'identity': (manifest or {}).get('identity'), 'branches': rows,
              'note': 'Declared literal field match only; EVIDENCE_INSUFFICIENT cases are not accepted or excluded.'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    failures = {'TOOL_ERROR', 'SOURCE_EXPECTATION_MISMATCH', 'NATIVE_RENDER_ERROR', 'CONFIRMED_GAP',
                'NATIVE_ASSERTION_FAILURE_SOURCE_REVIEW_REQUIRED'}
    return int(not identity_valid or any(r['classification'] in failures for r in rows))


if __name__ == '__main__':
    raise SystemExit(main())
