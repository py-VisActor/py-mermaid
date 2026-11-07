"""Strict byte-preserving union of closed, source-command-success oracle runs."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def canonical(value):
    # Unlike Python equality, JSON distinguishes true, 1 and 1.0.
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def rows(document):
    result = {}
    for row in document['cases']:
        identifier = row['id']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', identifier) or identifier.endswith('.'):
            raise ValueError('Unsafe case id: ' + identifier)
        if identifier.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}:
            raise ValueError('Reserved case id: ' + identifier)
        if identifier.casefold() in result:
            raise ValueError('Duplicate casefold id: ' + identifier)
        result[identifier.casefold()] = row
    return result


def verified(path, run_root, artifacts):
    path = Path(path).resolve()
    try:
        relative = path.relative_to(run_root).as_posix()
    except ValueError:
        raise ValueError('Evidence outside donor run: ' + str(path)) from None
    expected = artifacts.get(relative)
    if not expected or not path.is_file() or expected.get('sha256') != digest(path) or expected.get('bytes') != path.stat().st_size:
        raise ValueError('Missing or changed closed-run artifact: ' + relative)
    return {'sha256': expected['sha256'], 'bytes': expected['bytes']}


def command_path(value, cwd):
    p = Path(value)
    return (p if p.is_absolute() else Path(cwd)/p).resolve()


def merge(fixtures, donors, out, replace_case_ids=()):
    fixtures, out = Path(fixtures).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError('Output must be a new directory')
    final = rows(load(fixtures))
    requested = rows({'cases': [{'id': identifier} for identifier in replace_case_ids]})
    for key, row in requested.items():
        if key not in final or row['id'] != final[key]['id']:
            raise ValueError('Unknown replacement case id: ' + row['id'])
    union, metadata, copies, provenance, superseded = {}, {}, [], [], {}
    identity = identity_bytes = browser = None
    for run_path, oracle_path, frozen_path in donors:
        run_path, oracle_path, frozen_path = map(lambda p: Path(p).resolve(), (run_path, oracle_path, frozen_path))
        run = load(run_path)
        root = run_path.parent
        if run.get('status') not in ('SUCCESS', 'FAILED', 'ERROR', 'INTERRUPTED') or not run.get('finishedAtUtc'):
            raise ValueError('Donor run is not closed')
        artifacts = run['artifacts']
        for p in (oracle_path/'manifest.json', oracle_path/'identity.json', frozen_path):
            verified(p, root, artifacts)
        manifest, current_identity = load(oracle_path/'manifest.json'), load(oracle_path/'identity.json')
        if canonical(manifest['identity']) != canonical(current_identity):
            raise ValueError('manifest.identity differs from identity.json')
        if identity is None:
            identity, identity_bytes, browser = current_identity, (oracle_path/'identity.json').read_bytes(), manifest['browser']
        if canonical(identity) != canonical(current_identity):
            raise ValueError('Different fixed source identity')
        if manifest['browser'] != browser:
            raise ValueError('Different oracle browser identity')
        if manifest['fixtureSha256'] != digest(frozen_path):
            raise ValueError('Donor fixtureSha256 mismatch')
        successful = []
        for command in run['commands']:
            argv = command.get('argv', [])
            if not any(Path(str(a)).name == 'bulk_capture.cjs' for a in argv):
                continue
            try:
                used_fixture = command_path(argv[argv.index('--fixtures')+1], command['cwd'])
                used_out = command_path(argv[argv.index('--out')+1], command['cwd'])
            except (ValueError, IndexError, KeyError):
                continue
            if used_fixture != frozen_path or used_out != oracle_path:
                continue
            result_path = root/Path(command['stdout']).parent/'result.json'
            verified(result_path, root, artifacts)
            result = load(result_path)
            if command.get('exitCode') == result.get('exitCode') == 0 and command.get('status') == result.get('status') == 'SUCCESS' and command.get('finishedAtUtc') and result.get('finishedAtUtc') and canonical(command['argv']) == canonical(result['argv']):
                successful.append(command)
        if len(successful) != 1:
            raise ValueError('Expected one closed successful bulk_capture command for these inputs/output')
        source_rows, captured_rows = rows(load(frozen_path)), rows(manifest)
        if source_rows.keys() != captured_rows.keys():
            raise ValueError('Donor manifest missing/extra cases')
        for key, row in source_rows.items():
            changed = key in final and canonical(row) != canonical(final[key])
            if key not in final or (changed and key not in requested):
                raise ValueError('Final input differs from donor row: ' + row['id'])
            if row['id'] != final[key]['id']:
                raise ValueError('Replacement case id spelling differs: ' + row['id'])
            if changed and key in superseded:
                raise ValueError('Duplicate superseded donor case: ' + row['id'])
            if not changed and key in union:
                raise ValueError('Duplicate donor case: ' + row['id'])
            record = captured_rows[key]
            status = record['status']
            # bulk_capture deliberately records excluded rows as {id,status}
            # without kind/expect. Their complete input is still bound above.
            excluded = status == 'excluded' and row.get('expect') in ('excluded', 'excluded_by_static_scope')
            if record['id'] != row['id'] or (not excluded and (record.get('kind') != row.get('kind') or record.get('expect') != row.get('expect'))):
                raise ValueError('Manifest case metadata mismatch: ' + row['id'])
            suffixes = {'captured': ('.png', '.svg', '.json'), 'error': ('.error.json',), 'excluded': ()}.get(status)
            if suffixes is None:
                raise ValueError('Unfinished/unknown oracle case status: ' + status)
            expected_names = {row['id']+s for s in suffixes}
            # Dots are legal within IDs (e.g. elk.box). A prefix glob would
            # mistake a different case's files for extra evidence of elk.
            actual_names = {row['id']+s for s in ('.png', '.svg', '.json', '.error.json') if (oracle_path/(row['id']+s)).is_file()}
            if actual_names != expected_names:
                raise ValueError('Missing/extra case evidence: ' + row['id'])
            case_copies = []
            for name in sorted(expected_names):
                path = oracle_path/name
                stamp = verified(path, root, artifacts)
                case_copies.append((path, name, {'donorRun': str(run_path), 'source': str(path), 'destination': name, **stamp}))
            if changed:
                # Old input, manifest row and every old raw artifact have all
                # passed the same closed-run checks as reused evidence. Nothing
                # is silently dropped: retain its full supersession provenance.
                superseded[key] = {'id': row['id'], 'input': row, 'record': record,
                                   'donorRun': str(run_path), 'donorRunSha256': digest(run_path),
                                   'fixtures': str(frozen_path), 'fixtureSha256': digest(frozen_path),
                                   'files': [stamp for _, _, stamp in case_copies]}
            else:
                copies.extend(case_copies)
                union[key], metadata[key] = row, record
        provenance.append({'run': str(run_path), 'runSha256': digest(run_path), 'runStatus': run['status'], 'oracle': str(oracle_path), 'manifestSha256': digest(oracle_path/'manifest.json'), 'identitySha256': digest(oracle_path/'identity.json'), 'fixtures': str(frozen_path), 'fixtureSha256': digest(frozen_path), 'sourceCommand': successful[0], 'reuseScope': 'successful source capture only; overall donor run status is preserved'})
    if requested.keys() != superseded.keys():
        raise ValueError('Unused replacement case id: ' + ', '.join(sorted(set(requested)-set(superseded))))
    for key in requested:
        if key not in union:
            raise ValueError('Missing fresh replacement donor: ' + final[key]['id'])
    if union.keys() != final.keys() or not donors:
        raise ValueError('Final case denominator differs from donor union')
    # All donor and input validation precedes creating the new output.
    out.mkdir(parents=True)
    for path, name, stamp in copies:
        shutil.copyfile(path, out/name)
        if digest(out/name) != stamp['sha256'] or (out/name).stat().st_size != stamp['bytes']:
            raise ValueError('Copied artifact hash mismatch: ' + name)
    (out/'identity.json').write_bytes(identity_bytes)
    merged = {'identity': identity, 'browser': browser, 'fixtureSha256': digest(fixtures), 'cases': [metadata[k] for k in final], 'reuse': {'schema': 'py-mermaid-bulk-oracle-reuse/v1', 'finalFixtures': str(fixtures), 'donors': provenance, 'files': [record for _, _, record in copies], 'supersededInputs': [superseded[k] for k in requested], 'replacementCaseIds': [final[k]['id'] for k in requested], 'imageTransforms': False}}
    (out/'manifest.json').write_text(json.dumps(merged, ensure_ascii=True, indent=2)+'\n', encoding='utf-8')
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', required=True)
    parser.add_argument('--donor', nargs=3, action='append', required=True, metavar=('RUN_JSON', 'ORACLE_DIR', 'BROWSER_FIXTURE_JSON'))
    parser.add_argument('--out', required=True)
    parser.add_argument('--replace-case-id', action='append', default=[], help='Explicit changed case requiring verified old input plus a fresh exact final-row source donor')
    args = parser.parse_args()
    result = merge(args.fixtures, args.donor, args.out, replace_case_ids=args.replace_case_id)
    print(json.dumps({'cases': len(result['cases']), 'donors': len(args.donor), 'out': args.out}))


if __name__ == '__main__':
    main()
