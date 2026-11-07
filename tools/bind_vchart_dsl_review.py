"""Reuse an actual visual review only for byte-identical closed candidate images."""
import argparse
import copy
import json
from pathlib import Path

from collect_vchart_report_inputs import evidence
from run_support import ROOT, file_identity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review', required=True, type=Path)
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    original = json.loads(args.review.read_text('utf-8'))
    run = args.run.resolve(strict=True)
    manifest = json.loads((run / 'run.json').read_text('utf-8'))
    if manifest['status'] != 'SUCCESS' or not manifest['sourceUnchanged']:
        raise ValueError('Final review binding requires a successful closed candidate')
    rows = original['entries']
    expected = {(r['group'], r['id']) for r in json.loads((run / 'artifacts/matrix-cpu/result.json').read_text('utf-8'))['cases']
                if r['group'] in ('representative', 'example')}
    if len(rows) != 76 or {(r['group'], r['id']) for r in rows} != expected:
        raise ValueError('Actual review does not cover the 68+8 final case IDs')
    result = copy.deepcopy(original)
    result.pop('cases', None)
    result['candidateRun'] = run.relative_to(ROOT).as_posix()
    result['baselineRun'] = result['candidateRun']
    result['sourceTreeSha256'] = manifest['source']['sourceTreeSha256']
    result['originalReviewStatus'] = original.get('status') or original['verdict']
    result['status'] = 'PASS'  # Status of byte-identical binding; original verdict remains above.
    result['actualReviewOrigin'] = {'path': args.review.resolve().relative_to(ROOT).as_posix(),
                                    **file_identity(args.review), 'candidateRun': original['candidateRun']}
    result['actualViewedImages'] = 0
    result['reusedActuallyViewedImages'] = 76
    result['method'] = 'No new image viewing claimed. All 152 final API/DSL files are byte-identical to the 76 actually viewed DSL images and their 76 original API hash bindings. Original observations and provider characteristics are preserved.'
    for row in result['entries']:
        for side, filename in (('api', 'api.png'), ('actual', 'actual.png')):
            old = row['images'][side]
            original_path = (ROOT / old['rawPath']).resolve(strict=True)
            proof = evidence(original_path)
            if any(old[k] != proof[k] for k in ('sha256', 'bytes')):
                raise ValueError('Original actual-review bytes changed')
            final = run / 'artifacts/matrix-cpu' / row['group'] / row['id'] / filename
            final_proof = evidence(final)
            if file_identity(final) != file_identity(original_path):
                raise ValueError('Image changed; actual visual review is required: ' + str(final))
            old['originalReviewImage'] = old['rawPath']
            old['originalReviewMethod'] = old['reviewMethod']
            old['rawPath'] = old['path'] = final.relative_to(ROOT).as_posix()
            old['reviewMethod'] = 'SAME_SHA_REUSE_OF_ACTUAL_REVIEW'
            old['closedRunArtifact'] = final_proof['path']
            old['finalClosedRunProof'] = final_proof
            old['originalClosedRunProof'] = proof
    result['cases'] = result['entries']
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({'boundPairs': len(rows), 'newViewsClaimed': 0, 'status': result['status']}))


if __name__ == '__main__':
    main()
