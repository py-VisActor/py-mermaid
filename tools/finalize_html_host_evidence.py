"""Accept only closed, immutable, same-candidate HTML-host P4 evidence.

No product import, native allocation, test execution or image generation occurs.
Visual review is a mandatory external human receipt; this tool never creates it.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile

from run_support import ROOT, file_identity, verify_run, write_json

PROFILES = ('cpu', 'auto', 'gpu')
FORMATS = ('png', 'jpg', 'webp', 'svg', 'pdf')
KINDS = frozenset('agentflow architecture block c4 classDiagram cynefin er eventmodeling flowchart-elk flowchart-v2 gantt gitGraph info ishikawa journey kanban mindmap packet railroad railroadAbnf railroadEbnf railroadPeg requirement sequence stateDiagram swimlane timeline treeView usecase wardley zenuml'.split())
DEFERRED = ('pie', 'quadrantChart', 'xychart', 'radar', 'treemap', 'sankey', 'venn')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def proof(path):
    path = Path(path).resolve(strict=True)
    try:
        name = path.relative_to(ROOT).as_posix()
    except ValueError:
        name = str(path)
    return {'path': name, **file_identity(path)}


def resolve(name):
    path = Path(name)
    return (path if path.is_absolute() else ROOT / path).resolve(strict=True)


def checked_proof(item):
    path = resolve(item['path'])
    require(file_identity(path)['sha256'] == item['sha256'], 'Evidence fingerprint changed: ' + str(path))
    return path


def unique_rows(rows, expected, label, *, key='id'):
    ids = [row[key] for row in rows]
    require(len(ids) == len(set(ids)) and set(ids) == set(expected), label + ' denominator/ID mismatch')


def same_source(data, source, label):
    require(data.get('sourceUnchanged') is True and data.get('source', {}).get('sourceTreeSha256') == source,
            label + ' is not unchanged same-candidate evidence')


def option(command, name):
    argv = command['argv']
    require(name in argv and argv.index(name) + 1 < len(argv), 'Missing command option ' + name)
    return resolve(argv[argv.index(name) + 1])


def control_keys(cases):
    return {item['tag'] + ':' + item.get('type', 'text' if item['tag'] == 'input' else '')
            for case in cases for item in case.get('controlExpected', [])}


def typed_json(value):
    """Canonical JSON preserves boolean/number and int/float distinctions."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def archived_control_cases(path):
    """Read the entire frozen test input family, never the live working tree."""
    rows = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate test/tool archive member')
        fixtures = sorted(name for name in names if re.fullmatch(r'tests/html_host/cases[^/]*\.json', name))
        require(fixtures, 'Test/tool archive has no HTML-host fixture family')
        for name in fixtures:
            document = json.loads(archive.read(name).decode('utf-8-sig'))
            require(document.get('schema') == 'py-mermaid-bulk-cases/v1', 'Unexpected archived control fixture schema')
            require(isinstance(document.get('cases'), list) and document['cases'], 'Empty archived control fixture')
            for case in document['cases']:
                normalized = {**case, 'group': case.get('group', document['group'])}
                require('controlExpected' in normalized and normalized['group'] == 'shared',
                        'Archived control fixture lacks controlExpected/shared contract')
                rows.append(normalized)
    identifiers = [row['id'].casefold() for row in rows]
    require(len(identifiers) == len(set(identifiers)), 'Duplicate archived control fixture ID')
    return rows


def exports(path, source, selected, *, expected_kinds=None):
    data = read(path)
    same_source(data, source, str(path))
    rows = data['cases']
    expected = {(c, b, f) for c in selected for b in PROFILES for f in FORMATS}
    keys = [(r['fixture'], r['backend'], r['format']) for r in rows]
    require(len(keys) == len(set(keys)) and set(keys) == expected, 'Export Cartesian denominator differs: ' + str(path))
    names = [r['artifact'] for r in rows]
    require(len(names) == len(set(names)), 'Export filenames collide: ' + str(path))
    require(all(r.get('status') == 'CHECKS_PASSED' and not r.get('errors') and r.get('bytes', 0) > 0 for r in rows),
            'An export failed or is empty: ' + str(path))
    if expected_kinds is not None:
        require({r['kind'] for r in rows} == expected_kinds, 'Export detector coverage differs')
    for row in rows:
        artifact = (path.parent / row['artifact']).resolve(strict=True)
        require(artifact.is_relative_to(path.parent.resolve()) and file_identity(artifact) ==
                {'sha256': row.get('sha256'), 'bytes': row['bytes']},
                'Export artifact binding differs')
    return data


def finalize(p4, visual_path, exports_run=None):
    p4 = p4.resolve(strict=True)
    manifest = read(p4 / 'run.json')
    require(manifest.get('scope') == 'BULK-P4' and manifest.get('kind') == 'final', 'Not a whole final BULK-P4 run')
    require(manifest.get('status') == 'SUCCESS' and manifest.get('sourceUnchanged') is True and manifest.get('finishedAtUtc'),
            'P4 must be closed SUCCESS with unchanged source')
    integrity = verify_run(p4)
    require(integrity['integrityStatus'] == 'PASS', 'P4 immutable artifact integrity failed: ' + repr(integrity['errors']))
    commands = manifest['commands']
    require(commands and all(c.get('exitCode') == 0 and c.get('status') == 'SUCCESS' and c.get('finishedAtUtc') for c in commands),
            'P4 has incomplete or failed commands')
    by_name = {c['name']: c for c in commands}
    require(len(by_name) == len(commands), 'Duplicate P4 command names')
    required = {'fixture-freeze', 'unit-html-host', 'original-eleven-themes', 'complete-theme-variable-parity',
                'all-kinds-five-formats', 'html-control-five-formats', 'raw-html-report'}
    required |= {'unit-' + g for g in ('a', 'b', 'c', 'shared')}
    required |= {'regression-' + g for g in ('f011', 'f012', 'f013', 'f014', 'math')}
    required |= {'verification-tools-' + g for g in ('bootstrap', 'tooling', 'pixel_compare')}
    required |= {prefix + b + '-' + g for prefix in ('native-', 'compare-native-') for b in PROFILES for g in ('A', 'B', 'C', 'shared')}
    required |= {'legacy-' + g + '-' + b for g in ('f011', 'f012', 'f013', 'f014') for b in PROFILES}
    required |= {prefix + b for prefix in ('zenuml-source-structure-', 'html-control-state-') for b in PROFILES}
    require(required <= by_name.keys(), 'Missing required commands: ' + repr(sorted(required - by_name.keys())))
    require(bool({'official-source-capture', 'verify-reused-oracle-source'} & by_name.keys()), 'Original source capture/identity verification absent')
    a = p4 / 'artifacts'
    candidate = read(a / 'source-candidate.json')
    source = candidate['sourceTreeSha256']
    require(candidate == manifest['source'], 'Frozen source differs from P4 opening candidate')
    require(hashlib.sha256(json.dumps(candidate['files'], sort_keys=True).encode()).hexdigest() == source,
            'Source tree hash does not describe frozen files')
    with zipfile.ZipFile(a / 'source-candidate.zip') as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())) and set(archive.namelist()) == set(candidate['files']),
                'Source archive file denominator differs')
        require(all(hashlib.sha256(archive.read(name)).hexdigest() == value for name, value in candidate['files'].items()),
                'Source archive content differs')
    cases = read(a / 'fixtures/cases.json')['cases']
    ids = {c['id'] for c in cases}
    require(len(ids) == len(cases) and {c['kind'] for c in cases} == KINDS, 'Frozen case IDs/31-kind denominator differs')
    controls = [c for c in cases if 'controlExpected' in c]
    control_ids = {c['id'] for c in controls}
    require(control_ids and len(ids - control_ids) == 734, 'Frozen controls/734-case legacy split differs')
    archived_controls = archived_control_cases(a / 'test-tool-candidate.zip')
    require({c['id']: typed_json(c) for c in controls} == {c['id']: typed_json(c) for c in archived_controls},
            'Frozen controls differ from complete archived fixture family (missing, extra or changed typed JSON rows)')
    unique_rows(read(a / 'fixtures/html-control-cases.json')['cases'], control_ids, 'Control frozen fixture')
    require(typed_json(read(a / 'fixtures/html-control-cases.json')['cases']) == typed_json(controls),
            'Dedicated control fixture rows/order differ from whole frozen fixture')
    units = {}
    for name, command in by_name.items():
        argv = command['argv']
        if not any(argv[i:i+2] == ['-m', 'unittest'] for i in range(len(argv)-1)):
            continue
        text = (p4 / command['stderr']).read_text('utf-8')
        counts = re.findall(r'^Ran (\d+) tests? in ', text, re.M)
        require(len(counts) == 1 and re.search(r'^OK\s*$', text, re.M), 'No unambiguous successful unittest count: ' + name)
        units[name] = int(counts[0])
    require(all(name in units for name in required if name.startswith(('unit-', 'regression-', 'verification-tools-'))),
            'A required unit group has no actual Ran count')
    oracle = option(by_name['html-control-state-cpu'], '--oracle')
    original = read(oracle / 'manifest.json')
    require(original.get('fixtureSha256') == file_identity(a / 'fixtures/browser-cases.json')['sha256'], 'Oracle fixture fingerprint differs')
    identity = original['identity']
    require(identity.get('package') == 'mermaid@12.2.0' and identity.get('commit') == '1fb7869866dd619168d840291c9c54b4f129758b',
            'Oracle is not fixed canonical Mermaid12.2.0')
    native_profiles = {}; html_proofs = []; zen = {}; legacy = {}
    for backend in PROFILES:
        collected = []
        for group in ('A', 'B', 'C', 'shared'):
            path = a / ('native-' + backend + '-' + group) / 'results.json'
            native = read(path); same_source(native, source, str(path))
            expected = {c['id'] for c in cases if c['group'] == group}
            unique_rows(native['cases'], expected, 'Native ' + backend + '/' + group)
            require(native.get('backend') == backend and native.get('failed') == 0 and
                    all(r['status'] in ('CHECKS_PASSED', 'EXPECTED_ERROR', 'EXCLUDED') for r in native['cases']), 'Failed native group')
            collected += native['cases']
            comparison = read(a / ('comparison-native-' + backend + '-' + group) / 'comparison.json')
            require(comparison['source']['sourceTreeSha256'] == source and comparison['backend'] == backend, 'Comparison candidate differs')
            unique_rows(comparison['cases'], expected, 'Comparison')
            require(all(r['status'] in ('SOURCE_CHECKS_PASSED', 'UPSTREAM_CONFIRMED', 'EXPECTED_ERROR', 'EXCLUDED') for r in comparison['cases']),
                    'Unaccepted comparison status')
        native_profiles[backend] = dict(Counter(r['status'] for r in collected))
        path = a / ('html-control-verification-' + backend) / 'verification.json'
        checked = read(path); same_source(checked, source, str(path))
        require(checked.get('backend') == backend and checked.get('status') == 'PASS', 'Control verification failed')
        unique_rows(checked['cases'], control_ids, 'Control verification')
        require(all(r['status'] == 'PASS' and not r.get('errors') for r in checked['cases']), 'A control verification case failed')
        for name, expected in checked.get('inputs', {}).items():
            require(file_identity(resolve(name)) == expected, 'Control verification input changed')
        control_command = by_name['html-control-state-' + backend]
        expected_inputs = {a / 'fixtures/html-control-cases.json', oracle / 'manifest.json',
                           a / ('native-' + backend + '-shared') / 'results.json'}
        require({resolve(name) for name in checked.get('inputs', {})} == {p.resolve() for p in expected_inputs},
                'Control verification input binding differs')
        require(option(control_command, '--oracle') == oracle and
                option(control_command, '--native') == (a / ('native-' + backend + '-shared')).resolve() and
                option(control_command, '--fixtures') == (a / 'fixtures/html-control-cases.json').resolve(),
                'Control verification command binding differs')
        html_proofs.append(proof(path))
        z = read(a / ('zenuml-parity-' + backend) / 'report.json')
        zen_ids = {c['id'] for c in cases if c['kind'] == 'zenuml' and c['expect'] in ('render', 'upstream_defect')}
        unique_rows(z['cases'], zen_ids, 'Strict Zen')
        require((z.get('baseVisualDenominator'), z.get('additionalDenominator'), z.get('totalDenominator'), z.get('denominator')) == (148, 38, 186, 186),
                'Strict Zen denominator differs')
        require(all(r['status'] == 'PASS' and not r.get('errors') and r.get('controls') and all(v is True for v in r['controls'].values()) for r in z['cases']),
                'Strict Zen check or mutation failed')
        rejected = sum(len(r['controls']) for r in z['cases'])
        require(rejected == 1990, 'Strict Zen mutation denominator differs')
        zen[backend] = {'baseVisual': 148, 'additional': 38, 'total': len(z['cases']), 'rejectedMutationControls': rejected}
        legacy[backend] = {}
        for group, count in (('f011', 12), ('f012', 35), ('f013', 50), ('f014', 200)):
            report = read(a / ('legacy-' + group + '-' + backend) / 'report.json')
            require(report.get('functionalStatus') == 'PASS' and len(report['cases']) == count, 'Legacy positive denominator/failure')
            require(all(r.get('status') == 'PASS' and not r.get('errors') for key in ('cases', 'negativeCases', 'renderErrorCases', 'unsupportedCases') for r in report.get(key, [])),
                    'Legacy semantic/negative regression failed')
            legacy[backend][group] = len(report['cases'])
    theme = read(a / 'theme-parity.json')
    require(theme.get('failed') == 0 and theme.get('cases') and all(not r.get('differences') for r in theme['cases']), 'Theme parity failed')
    source_themes = read(a / 'original-themes.json')
    expected_theme_ids = {c['id'] for c in cases if c['group'] == 'shared' and c.get('config', {}).get('theme')}
    unique_rows(source_themes['cases'], expected_theme_ids, 'Original themes')
    unique_rows(theme['cases'], expected_theme_ids, 'Theme parity')
    require(source_themes.get('package') == 'mermaid@12.2.0' and
            set('base dark default forest neo neo-dark neutral redux redux-color redux-dark redux-dark-color'.split()) <=
            {r['theme'] for r in source_themes['cases']}, 'All eleven canonical themes not covered')
    export_artifacts = a
    export_repair = None
    if exports_run is not None:
        exports_run = exports_run.resolve(strict=True)
        repair = read(exports_run / 'run.json')
        require(repair.get('scope') == 'HTML-HOST-P4-EXPORT' and repair.get('kind') == 'repair' and
                repair.get('status') == 'SUCCESS' and repair.get('sourceUnchanged') is True and
                repair.get('finishedAtUtc') and repair.get('source') == candidate,
                'Export repair is not closed unchanged same-candidate evidence')
        require(verify_run(exports_run)['integrityStatus'] == 'PASS', 'Export repair immutable integrity failed')
        expected_names = {'all-kinds-five-formats', 'html-control-five-formats'}
        repair_commands = repair['commands']
        require(len(repair_commands) == 2 and {c['name'] for c in repair_commands} == expected_names and
                all(c.get('status') == 'SUCCESS' and c.get('exitCode') == 0 and c.get('finishedAtUtc') for c in repair_commands),
                'Export repair required commands differ')
        def without_output(argv):
            argv = list(argv)
            require(argv.count('--out') == 1, 'Export command output option differs')
            index = argv.index('--out')
            del argv[index:index+2]
            return argv
        exporter = exports_run / 'artifacts/bulk_export.py'
        exporter_identity = file_identity(exporter)
        export_artifacts = exports_run / 'artifacts'
        for command in repair_commands:
            require(without_output(command['argv']) == without_output(by_name[command['name']]['argv']),
                    'Export repair changed frozen fixture selection or device matrix')
            folder = 'exports' if command['name'] == 'all-kinds-five-formats' else 'html-control-exports'
            require(option(command, '--out') == (export_artifacts / folder).resolve(), 'Export repair output binding differs')
            tool_files = command.get('toolFiles', {})
            require(any(Path(name).name == 'bulk_export.py' and value == exporter_identity for name, value in tool_files.items()),
                    'Export repair exporter archive does not bind executed tool')
        expected_inputs = {p4 / 'run.json', a / 'fixtures/cases.json', a / 'html-control-export-selection.json'}
        for path in expected_inputs:
            require(repair.get('inputs', {}).get(str(path)) == file_identity(path), 'Export repair frozen input binding differs')
        export_repair = {'manifest': proof(exports_run / 'run.json'), 'exporter': proof(exporter),
                         'reason': 'Original P4 saved exports had filename collisions; both same-candidate matrices were rerun, with unique filenames and saved-byte hashes.',
                         'rejectedOriginalExports': [proof(a / 'exports/exports.json'), proof(a / 'html-control-exports/exports.json')]}
    general_path = export_artifacts / 'exports/exports.json'
    general = read(general_path)
    selected = {r['fixture'] for r in general['cases']}
    require(len(selected) == 31 and selected <= ids, 'General export selection differs')
    exports(general_path, source, selected, expected_kinds=KINDS)
    control_path = export_artifacts / 'html-control-exports/exports.json'
    requested = read(control_path).get('requestedCaseIds', [])
    require(requested and len(requested) == len(set(requested)) and set(requested) <= control_ids, 'Invalid control export selection')
    require(control_keys([c for c in controls if c['id'] in requested]) == control_keys(controls), 'Control export type coverage incomplete')
    selection = read(a / 'html-control-export-selection.json')
    require(selection['caseIds'] == requested, 'Control export recorded selection differs')
    exported = exports(control_path, source, requested)
    visual = read(visual_path)
    require(visual.get('status') == 'PASS' and visual.get('sourceTreeSha256') == source, 'Human visual review candidate/status differs')
    require({c['kind'] for c in visual.get('cases', [])} == KINDS, 'Human visual review must cover all 31 retained kinds')
    required_review_ids = {c['id'] for c in archived_controls if c.get('reviewRequired') is True}
    require(required_review_ids <= {c['id'] for c in visual.get('cases', [])},
            'Human visual review lacks archived reviewRequired control cases')
    by_id = {c['id']: c for c in cases}
    for row in visual['cases']:
        identifier = row['id']
        require(identifier in by_id and row['kind'] == by_id[identifier]['kind'], 'Unknown visual review case')
        require(checked_proof(row['original']) == (oracle / (identifier + '.png')).resolve(), 'Human review original binding differs')
        native_paths = {(a / ('native-' + b + '-' + by_id[identifier]['group']) / (identifier + '.png')).resolve() for b in PROFILES}
        require(checked_proof(row['native']) in native_paths, 'Human review native is not final P4 output')
    return {'schema': 'py-mermaid-gap-branch-acceptance/v1', 'functionalStatus': 'RETAINED_STATIC_LOCAL_ACCEPTED',
            'scopeStatus': 'SCOPED_RETAINED_STATIC_WITH_INITIAL_HTML_CONTROLS', 'sourceTreeSha256': source,
            'fixtureCount': len(cases), 'htmlControlFixtureCount': len(controls), 'legacyFixtureCount': len(cases)-len(controls),
            'retainedDetectors': sorted(KINDS), 'deferredDetectors': list(DEFERRED), 'p4Manifest': proof(p4 / 'run.json'),
            'visualReview': proof(visual_path), 'unitMethods': sum(units.values()), 'unitGroups': units,
            'nativeProfiles': native_profiles, 'zenumlStrict': zen, 'legacy': legacy,
            'htmlControlVerification': html_proofs, 'htmlControlExports': proof(control_path),
            'exports': {'proof': proof(general_path), 'count': len(general['cases'])},
            'exportRepair': export_repair,
            'htmlControlExportCount': len(exported['cases']), 'htmlControlExportSelectedCaseCount': len(requested),
            'requiredControlVisualReviewIds': sorted(required_review_ids),
            'canonicalSource': {'package': identity['package'], 'commit': identity['commit']},
            'installationValidation': {'status': 'NOT_EXECUTED'},
            'limitations': ['video/audio fully excluded', 'interaction and Dagre excluded', 'seven deferred chart detectors remain outside this scope',
                            'bounded static HTML/CSS only; no claim of arbitrary HTML/CSS, browser UI or all platforms', 'local evidence only; no installation validation or publication']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--p4', type=Path, required=True)
    parser.add_argument('--visual-review', type=Path, required=True)
    parser.add_argument('--exports-run', type=Path, help='Closed same-candidate repair of only the two export matrices; original P4 stays immutable')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(not args.out.exists(), 'Output directory must be new')
        for parent in args.out.resolve().parents:
            if (parent / 'run.json').is_file():
                require(read(parent / 'run.json').get('status') == 'RUNNING',
                        'Cannot add output beneath an immutable closed Run')
        result = finalize(args.p4, args.visual_review.resolve(strict=True), args.exports_run)
        args.out.mkdir(parents=True, exist_ok=False)
        write_json(args.out / 'acceptance.json', result, exclusive=True)
        write_json(args.out / 'summary.json', {**result, 'schema': 'py-mermaid-html-host-final-summary/v1'}, exclusive=True)
        print(json.dumps({'status': 'PASS', 'sourceTreeSha256': result['sourceTreeSha256'], 'fixtureCount': result['fixtureCount'],
                          'unitMethods': result['unitMethods'], 'acceptance': str(args.out / 'acceptance.json')}))
        return 0
    except (ValueError, KeyError, OSError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
