"""Validate functional-group audit references; never infer branch coverage."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from run_support import ROOT, file_identity, source_identity


STATUSES = {'implemented_with_evidence', 'implemented_unverified', 'confirmed_gap',
            'excluded', 'upstream_defect', 'unresolved'}


def validate(paths):
    scope = json.loads((ROOT / 'references/bulk-scope.json').read_text('utf-8'))
    documents = [json.loads(path.read_text('utf-8')) for path in paths]
    entries = [entry for doc in documents for entry in doc['entries']]
    identifiers = [entry['id'] for entry in entries]
    if Counter(identifiers) != Counter(scope['retainedDetectors']):
        raise ValueError('Audit entry denominator differs from the 31 retained entries')
    candidate = source_identity()
    baseline = {doc['baselineSourceSha256'] for doc in documents}
    if len(baseline) != 1:
        raise ValueError('Audit documents do not share one baseline')
    statuses = Counter()
    references = {}
    gaps = []
    shared = [entry for doc in documents for entry in doc.get('sharedCapabilities', [])]
    if len(shared) != 13 or len({item['id'] for item in shared}) != 13:
        raise ValueError('Expected 13 distinct shared capability groups')
    for doc in documents:
        if doc['upstreamCommit'] != scope['upstreamCommit']:
            raise ValueError('Upstream identity differs from fixed baseline')
        if not doc.get('unresolvedScope') or not doc.get('actualReviewDepth'):
            raise ValueError('Missing review depth or residual denominator')
        for entry in doc['entries'] + doc.get('sharedCapabilities', []):
            if not entry['features']:
                raise ValueError('Empty functional group inventory: ' + entry['id'])
            for feature in entry['features']:
                status = feature['status']
                if status not in STATUSES or not feature.get('reason'):
                    raise ValueError('Invalid classification/reason: ' + feature['id'])
                if not feature.get('source'):
                    raise ValueError('Missing fixed source: ' + feature['id'])
                if status in {'confirmed_gap', 'implemented_with_evidence'} and not feature.get('tests'):
                    raise ValueError('Missing regression/evidence reference: ' + feature['id'])
                statuses[status] += 1
                if status == 'confirmed_gap':
                    gaps.append({'entry': entry['id'], 'id': feature['id'], 'title': feature['title'],
                                 'reason': feature['reason'], 'audit': str(paths[documents.index(doc)])})
                for role in ('source', 'python', 'tests'):
                    for ref in feature.get(role, []):
                        relative = Path(ref['path'])
                        if relative.is_absolute() or '..' in relative.parts:
                            raise ValueError('Unsafe audit reference: ' + str(relative))
                        roots = [ROOT / '.local/upstream-mermaid', ROOT / '.local/bulk-sources/zenuml/source'] if role == 'source' else [ROOT]
                        existing = [(base / relative).resolve() for base in roots if (base / relative).is_file()]
                        if len(existing) != 1 or not ref.get('symbol'):
                            raise ValueError('Missing/ambiguous source or symbol: ' + str(relative))
                        path = existing[0]
                        lines = path.read_text(encoding='utf-8-sig').splitlines()
                        if not isinstance(ref.get('line'), int) or not 1 <= ref['line'] <= len(lines):
                            raise ValueError('Invalid reference line: ' + str(relative))
                        references[path.relative_to(ROOT).as_posix()] = file_identity(path)
    return {'schema': 'py-mermaid-functional-audit-check/v1', 'status': 'PASS',
            'retainedEntries': len(entries), 'deferredEntries': len(scope['deferredDetectors']),
            'sharedCapabilities': len(shared), 'functionalGroupRecords': sum(statuses.values()),
            'classifications': dict(statuses), 'confirmedGapRecords': gaps,
            'auditBaselineSourceSha256': next(iter(baseline)),
            'currentSourceTreeSha256': candidate['sourceTreeSha256'],
            'sourceChangedSinceAudit': candidate['sourceTreeSha256'] not in baseline,
            'branchCoverageEstablished': False, 'newBehaviorVerified': False,
            'inputs': {str(path): file_identity(path) for path in paths},
            'references': references,
            'unresolvedScope': {doc['group']: doc['unresolvedScope'] for doc in documents},
            'meaning': 'Complete entry/group correspondence and reference integrity only; statuses retain baseline audit findings. Not functional acceptance or exhaustive branch coverage.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audits', type=Path, nargs='+', default=[ROOT / 'references' / f'gap-audit-{g}.json' for g in ('A', 'B', 'C', 'root')])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.audits)
    except (ValueError, KeyError, OSError) as exc:
        result = {'schema': 'py-mermaid-functional-audit-check/v1', 'status': 'FAIL', 'error': str(exc)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key not in {'inputs', 'references', 'unresolvedScope', 'confirmedGapRecords'}}, ensure_ascii=False))
    return int(result['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
