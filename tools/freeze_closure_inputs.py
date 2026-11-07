"""Freeze all source inputs while separating parse-only and real-render cases."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

from bulk_support import load_cases, browser_resources
from run_support import ROOT, file_identity, write_json, source_identity


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    files = sorted((ROOT / 'tests/closure').glob('cases-*.json'))
    cases = load_cases(files)
    rendered = [row for row in cases if not row.get('parserOnly')]
    write_json(args.out / 'all-cases.json', {'schema': 'py-mermaid-bulk-cases/v1', 'group': 'combined', 'cases': cases}, exclusive=True)
    write_json(args.out / 'cases.json', {'schema': 'py-mermaid-bulk-cases/v1', 'group': 'combined', 'cases': rendered}, exclusive=True)
    write_json(args.out / 'browser-cases.json', {'schema': 'py-mermaid-bulk-cases/v1', 'group': 'combined',
        'cases': [{**row, 'browserResources': browser_resources(row)} for row in rendered]}, exclusive=True)
    for file in files:
        shutil.copyfile(file, args.out / file.name)
    write_json(args.out / 'identity.json', {'source': source_identity(), 'inputs': {file.relative_to(ROOT).as_posix(): file_identity(file) for file in files},
        'counts': {'all': len(cases), 'renderOrError': len(rendered), 'parserOnly': len(cases) - len(rendered)},
        'groups': dict(Counter(row['group'] for row in rendered)), 'productBehaviorExecuted': False,
        'parserOnlyMeaning': 'Control-character/grammar-only source literals are tested by getters and parser units, never claimed as serializable SVG draws.'}, exclusive=True)
    print(json.dumps({'all': len(cases), 'renderOrError': len(rendered), 'parserOnly': len(cases) - len(rendered)}))


if __name__ == '__main__':
    main()
