"""Archive the immutable candidate and focused branch inputs before execution."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
import shutil
import zipfile

from bulk_support import load_cases, browser_resources
from run_support import ROOT, file_identity, source_identity, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, nargs='+', required=True)
    parser.add_argument('--ledgers', type=Path, nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    cases = load_cases(args.fixtures, require_all=False)
    for role, paths in (('fixtures', args.fixtures), ('ledgers', args.ledgers)):
        target = args.out / 'raw-inputs' / role
        target.mkdir(parents=True)
        names = set()
        for path in paths:
            if path.name.casefold() in names:
                raise ValueError('Colliding frozen raw input names: ' + path.name)
            names.add(path.name.casefold())
            shutil.copy2(path, target / path.name)
    source = source_identity()
    write_json(args.out / 'source-candidate.json', source, exclusive=True)
    with zipfile.ZipFile(args.out / 'source-candidate.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in source['files']:
            archive.write(ROOT / name, name)
    inputs = sorted(set([*args.fixtures, *args.ledgers, *[p for base in ('tests/branch_verification', 'tools', 'scripts', 'docs', 'references')
                                                      for p in (ROOT / base).rglob('*')
                                                      if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']]), key=str)
    with zipfile.ZipFile(args.out / 'verification-inputs.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        seen = set()
        for path in inputs:
            path = path.resolve(strict=True)
            name = path.relative_to(ROOT).as_posix()
            if name not in seen:
                archive.write(path, name)
                seen.add(name)
    write_json(args.out / 'cases.json', {'schema': 'py-mermaid-bulk-cases/v1', 'group': 'combined', 'cases': cases}, exclusive=True)
    write_json(args.out / 'browser-cases.json', {'schema': 'py-mermaid-bulk-cases/v1', 'group': 'combined',
               'cases': [{**case, 'browserResources': browser_resources(case)} for case in cases]}, exclusive=True)
    for group in sorted({c['group'] for c in cases}):
        write_json(args.out / ('cases-' + group + '.json'), {'schema': 'py-mermaid-bulk-cases/v1', 'group': group,
                   'cases': [c for c in cases if c['group'] == group]}, exclusive=True)
    for ledger in args.ledgers:
        shutil.copy2(ledger, args.out / ledger.name)
    write_json(args.out / 'freeze.json', {'schema': 'py-mermaid-branch-freeze/v1', 'source': source,
               'inputs': {str(p.resolve()): file_identity(p) for p in inputs},
               'fixtureCount': len(cases), 'groupCounts': dict(Counter(c['group'] for c in cases)),
               'scope': 'Focused retained-branch verification; not whole-project branch coverage',
               'productBehaviorExecuted': False}, exclusive=True)
    print({'fixtureCount': len(cases), 'groupCounts': dict(Counter(c['group'] for c in cases)), 'productBehaviorExecuted': False})


if __name__ == '__main__':
    main()
