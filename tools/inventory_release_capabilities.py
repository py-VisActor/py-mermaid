"""Record current public wiring and release prerequisites; not branch coverage."""
import argparse
import ast
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import sys
import tomllib
import urllib.error
import urllib.request

from run_support import ROOT, file_identity, source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT / 'src'))
    from py_mermaid import registered_diagrams, supported_vchart_types, registered_layouts
    from py_mermaid.runtime.registry import provider_for

    source = source_identity()
    declared = json.loads((ROOT / 'references/bulk-scope.json').read_text('utf-8'))['upstreamInventory']
    entries = registered_diagrams()
    if len(entries) != 39 or set(entries) != set(declared) | {'vchart'}:
        raise ValueError('Current registry lost or added an unexpected entry')
    providers = []
    for name in entries:
        provider = provider_for(name)
        if provider is None:
            if name not in ('flowchart-elk', 'flowchart-v2'):
                raise ValueError('Missing registered provider: ' + name)
            file = ROOT / 'src/py_mermaid/diagrams/flowchart/parser.py'
            providers.append({'id': name, 'path': file.relative_to(ROOT).as_posix(),
                              **file_identity(file), 'route': 'Dedicated flowchart parse/layout/Canvas path'})
        else:
            file = Path(provider.__file__).resolve(strict=True)
            if not file.is_relative_to(ROOT / 'src'):
                raise ValueError('Provider is not current workspace source: ' + name)
            providers.append({'id': name, 'path': file.relative_to(ROOT).as_posix(),
                              **file_identity(file), 'parseSignature': str(inspect.signature(provider.parse)),
                              'buildSignature': str(inspect.signature(provider.build)),
                              'asyncBuild': inspect.iscoroutinefunction(provider.build)})
    types = supported_vchart_types()
    if len(types) != len(set(types)) or len(types) != 68:
        raise ValueError('Formal VChart type denominator mismatch')

    imports, guards, empty, unimplemented = set(), [], [], []
    files = sorted((ROOT / 'src/py_mermaid').rglob('*.py'))
    for file in files:
        tree = ast.parse(file.read_text('utf-8-sig'))
        name = file.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports.add(node.module.split('.')[0])
            elif isinstance(node, ast.Raise):
                statement = ast.unparse(node)
                if 'NotImplemented' in statement:
                    unimplemented.append({'path': name, 'line': node.lineno, 'statement': statement})
                if any(word in statement.lower() for word in ('unsupported', 'not supported', 'outside', 'requires')):
                    guards.append({'path': name, 'line': node.lineno, 'statement': statement})
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body[1:] if ast.get_docstring(node) else node.body
                if not body or all(isinstance(n, ast.Pass) or isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and n.value.value is Ellipsis for n in body):
                    empty.append({'path': name, 'line': node.lineno, 'symbol': node.name})
    external = sorted(imports - sys.stdlib_module_names - {'__future__', 'py_mermaid'})
    expected = {'py_skia_canvas', 'pyelk', 'py_katex', 'py_vchart'}
    if set(external) != expected:
        raise ValueError('Unexpected absolute production import roots: ' + repr(external))
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text('utf-8'))['project']
    workflows = []
    for file in sorted((ROOT / '.github/workflows').glob('*')):
        workflows.append({'path': file.relative_to(ROOT).as_posix(), **file_identity(file)})
    pyproject = {key: project.get(key) for key in ('name', 'version', 'requires-python', 'dependencies', 'classifiers')}
    url = 'https://pypi.org/pypi/' + project['name'] + '/json'
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read()
            (args.out / 'pypi-project.json').write_bytes(raw)
            info = json.loads(raw)
            pypi = {'url': url, 'httpStatus': response.status, 'projectPresent': True,
                    'version': info['info']['version'], 'response': file_identity(args.out / 'pypi-project.json')}
    except urllib.error.HTTPError as error:
        (args.out / 'pypi-response.txt').write_bytes(error.read())
        pypi = {'url': url, 'httpStatus': error.code, 'projectPresent': False if error.code == 404 else None,
                'meaning': '404 does not prove name availability, similarity approval, ownership or Trusted Publisher configuration',
                'response': file_identity(args.out / 'pypi-response.txt')}
    result = {'schema': 'py-mermaid-final-capability-inventory/v1', 'status': 'INVENTORY_COMPLETE_NOT_FUNCTIONAL_ACCEPTANCE',
              'source': source, 'sourceUnchanged': source_identity() == source,
              'registry': {'count': len(entries), 'originalMermaid': len(declared), 'providers': providers},
              'vchart': {'types': list(types), 'count': len(types), 'providerVersion': importlib.metadata.version('py-visactor-vchart')},
              'layouts': list(registered_layouts()), 'sourceFileCount': len(files), 'externalImportRoots': external,
              'unimplementedRaises': unimplemented, 'emptyFunctionBodies': empty, 'explicitGuardSites': guards,
              'guardMeaning': 'Source-reading candidates only. Invalid-input/security/static exclusions and helper-only paths must not be counted as missing functionality.',
              'packaging': pyproject, 'workflows': workflows, 'pypi': pypi,
              'releaseReadiness': 'Not established: alpha version/classifier, no consumer release workflow, no same-candidate Linux install proof. Known retained gaps are audited separately.',
              'coverageMeaning': '39 registered names and68 supplier types have real public wiring. This is not evidence of all fields/branches, visible output or platform release acceptance.'}
    (args.out / 'inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps({'registry': len(entries), 'vchart': len(types), 'files': len(files), 'guardSites': len(guards),
                      'emptyBodies': len(empty), 'unimplementedRaises': len(unimplemented), 'externalImports': external,
                      'pypi': pypi, 'sourceUnchanged': result['sourceUnchanged']}))


if __name__ == '__main__':
    main()
