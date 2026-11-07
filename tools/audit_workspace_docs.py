"""Audit documentation audiences and links in sibling py-VisActor repositories.

Standard library only. No network, imports of product code, build or install.
Use --write-inventory to refresh explicit per-document audience catalogues.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import tomllib
from urllib.parse import unquote, urlsplit


PROJECTS = ('py-skia-canvas', 'py-elk', 'py-katex', 'py-vchart', 'py-mermaid')
LINK = re.compile(r'!?\[[^\]\n]*\]\(([^\n]*?)\)')
FORBIDDEN_PUBLIC = re.compile(
    r'(?:AGENTS\.md|NEW_SESSION|EXECUTION_HANDOFF|_ACCEPTANCE|_EXECUTION|'
    r'CLOSURE_BATCH_PLAN|PORTING_WORKFLOW|docs/ai/README)', re.I)


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root).decode('utf-8')


def files_in(root):
    names = git(root, 'ls-files', '-co', '--exclude-standard', '-z').split('\0')
    return sorted({n for n in names if n and (root / n).is_file()
                   and Path(n).suffix.lower() in {'.md', '.rst'}})


def audience(name):
    lower = name.lower()
    if any(x in lower for x in ('license', 'third_party_notices', 'third-party')):
        return 'legal'
    if any(x in lower for x in ('/archive/', '/history/', '.history-', '/retrospectives/')):
        return 'archive'
    if lower.startswith(('references/upstream/', 'references/next-native-evidence/', 'tests/fixtures/',
                         'references/closure-source-')):
        return 'evidence'
    if lower.startswith('docs/releases/') and 'rejected' in lower:
        return 'archive'
    if lower.startswith(('docs/user/', 'docs/ai/usage/')) or lower in {
        'readme.md', 'readme.en.md', 'changelog.md', 'examples/readme.md',
        'docs/readme.md', 'docs/readme.en.md', 'docs/user_guide.md', 'docs/api.md',
        'docs/usage.md', 'docs/chart_types.md', 'docs/pypi_description.md',
        'docs/ai/install.md', 'docs/ai/install.en.md', 'docs/releases/0.1.0.md',
        'docs/releases/0.1.1.md'}:
        return 'user'
    if lower.startswith(('docs/releases/evidence/',)) or any(x in lower for x in (
            '_acceptance', '_validation', '_report', 'completion_report')):
        return 'evidence'
    if re.search(r'(?:^|/)(?:f01_[1-4]_usage|bulk_usage|next_iteration|'
                 r'implementation_plan|full_migration_plan|tasks|'
                 r'.*_execution_plan|.*_static_execution)\.md$', lower):
        return 'archive'
    return 'developer'


def without_fences(text):
    return re.sub(r'^(`{3,}|~{3,}).*?^\1\s*$', '', text, flags=re.M | re.S)


def destinations(text):
    for match in LINK.finditer(without_fences(text)):
        value = match[1].strip()
        yield value[1:value.index('>')] if value.startswith('<') and '>' in value else value.split(' ', 1)[0]


def local_target(workspace, root, source, url):
    parsed = urlsplit(url)
    if parsed.scheme in {'https', 'http'}:
        bits = unquote(parsed.path).strip('/').split('/')
        if parsed.netloc.lower() == 'github.com' and len(bits) >= 5 and bits[0].lower() == 'py-visactor' \
                and bits[1] in PROJECTS and bits[2] in {'blob', 'tree'} and bits[3] in {'main', 'master'}:
            return workspace / bits[1] / '/'.join(bits[4:])
        return None
    if parsed.scheme or not parsed.path:
        return None
    return (root / source).parent / unquote(parsed.path)


def python_blocks(text):
    return re.findall(r'^```python\s*\n(.*?)^```\s*$', text, re.M | re.S)


def check_project(workspace, name, write_inventory=False):
    root = workspace / name
    project = tomllib.loads((root / 'pyproject.toml').read_text('utf-8'))['project']
    names = files_in(root)
    rows = [{'path':n, 'audience':audience(n)} for n in names]
    errors, legacy_links = [], []
    required = ('README.md', 'AGENTS.md', 'docs/README.md', 'docs/development/README.md')
    for path in required:
        if path not in names:
            errors.append({'path':path, 'error':'missing audience entry'})
    expected = f'https://github.com/py-VisActor/{name}/blob/main/docs/README.md'
    if project.get('urls', {}).get('Documentation') != expected:
        errors.append({'path':'pyproject.toml', 'error':'Documentation must point to the user index'})
    agent = (root / 'AGENTS.md').read_text('utf-8')
    if re.findall(r'^## ([1-6])\.', agent, re.M) != list('123456'):
        errors.append({'path':'AGENTS.md', 'error':'expected six ordered AI instruction sections'})
    if not 40 <= len(agent.splitlines()) <= 100 or re.search(r'^>\s*20\d\d-', agent, re.M):
        errors.append({'path':'AGENTS.md', 'error':'agent entry contains a timeline or exceeds its concise scope'})
    readme = project['readme']
    pypi_file = readme if isinstance(readme, str) else readme['file']
    public = {'README.md', 'README.en.md', pypi_file}
    links = blocks = 0
    for row in rows:
        path, role = row['path'], row['audience']
        text = (root / path).read_text('utf-8')
        # Frozen source/evidence and archived text retain their original context.
        if role in {'archive', 'evidence', 'legal'}:
            continue
        for url in destinations(text):
            links += 1
            if path in public and FORBIDDEN_PUBLIC.search(url):
                errors.append({'path':path, 'link':url, 'error':'public entry points directly to session/implementation evidence'})
            if path == pypi_file and not urlsplit(url).scheme and not url.startswith('#'):
                errors.append({'path':path, 'link':url, 'error':'PyPI description needs absolute links'})
            target = local_target(workspace, root, path, url)
            if target is not None and not target.exists():
                issue = {'path':path, 'link':url, 'error':'missing local/current-branch target'}
                active = path in public or path in required or role == 'user' or path.startswith('docs/development/')
                (errors if active else legacy_links).append(issue)
        for block in python_blocks(text):
            blocks += 1
            try:
                ast.parse(block)
            except SyntaxError as exc:
                errors.append({'path':path, 'error':'Python example syntax: '+str(exc)})
    baseline = tomllib.loads(git(root, 'show', 'HEAD:pyproject.toml'))
    current = tomllib.loads((root / 'pyproject.toml').read_text('utf-8'))
    baseline['project'].pop('urls', None)
    current['project'].pop('urls', None)
    if baseline != current:
        errors.append({'path':'pyproject.toml', 'error':'non-URL metadata changed during documentation task'})
    changed = git(root, 'diff', '--name-only').splitlines()
    changed += [n for n in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0') if n]
    runtime = [n for n in changed if n.startswith(('src/', 'python/', 'crates/'))]
    if runtime:
        errors.append({'error':'runtime changed during documentation task', 'paths':runtime})
    inventory = {'schema':'py-visactor-documentation-inventory/v1', 'project':name,
                 'userEntry':'docs/README.md', 'developerEntry':'docs/development/README.md',
                 'agentEntry':'AGENTS.md', 'roles':{
                     'user':'Installation, API, examples and supported behavior',
                     'developer':'Repository maintenance, tools, architecture and agent rules',
                     'archive':'Historical plans or original archived text; not current instructions',
                     'evidence':'Frozen verification and source records; not current user guidance',
                     'legal':'License and attribution notices'},
                 'counts':dict(Counter(r['audience'] for r in rows)), 'documents':rows}
    if write_inventory:
        destination = root / 'docs/development/documentation-inventory.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(inventory, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    return {'project':name, 'status':'PASS' if not errors else 'FAIL', 'documents':len(rows),
            'counts':inventory['counts'], 'checkedLinks':links, 'pythonBlocks':blocks,
            'pypiDescription':pypi_file, 'documentationUrl':expected,
            'runtimeChanges':runtime, 'errors':errors, 'legacyLinkWarnings':legacy_links}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out', type=Path, required=True, help='New evidence directory')
    parser.add_argument('--write-inventory', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    rows = [check_project(args.workspace.resolve(), name, args.write_inventory) for name in PROJECTS]
    result = {'schema':'py-visactor-documentation-audit/v1',
              'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',
              'scope':'Owned Markdown routing, links, Python syntax, agent structure and metadata. '
                      'No runtime/visual/install verification; frozen evidence is not rewritten.',
              'projects':rows}
    (args.out / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(result['status'] != 'PASS')


if __name__ == '__main__':
    main()
