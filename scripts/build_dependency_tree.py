"""Build complete pinned pnpm graphs, reference trees and a bottom-up work index.

Offline and standard-library only. Preserves optional edges, peer contexts,
workspace links, cycles and every lock snapshot; does not execute upstream code.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import posixpath
import re

import audit_dependencies as audit

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ROOT / 'references/dependency-porting-policy.json'


def identity(snapshot):
    base = snapshot.split('(', 1)[0]
    return base.rsplit('@', 1)


def resolve(name, version, owner, nodes):
    if version.startswith('link:'):
        target = 'workspace:' + posixpath.normpath(posixpath.join(owner, version[5:]))
    else:
        target = name + '@' + version
        if target not in nodes and version in nodes:
            target = version  # npm alias
    if target not in nodes:
        raise ValueError(f'Unresolved edge {owner}: {name} -> {version}')
    return target


def closure(roots, nodes, groups):
    reached = set()
    queue = deque(roots)
    while queue:
        key = queue.popleft()
        if key in reached:
            continue
        reached.add(key)
        queue.extend(edge['target'] for edge in nodes[key]['edges'] if edge['group'] in groups)
    return reached


def bottom_up(nodes, selected, groups):
    """Condense strongly connected components before computing sink-first layers."""
    graph = {key: sorted({e['target'] for e in nodes[key]['edges']
                          if e['group'] in groups and e['target'] in selected})
             for key in sorted(selected)}
    index = {}
    low = {}
    stack = []
    active = set()
    components = []

    def visit(node):
        index[node] = low[node] = len(index)
        stack.append(node)
        active.add(node)
        for child in graph[node]:
            if child not in index:
                visit(child)
                low[node] = min(low[node], low[child])
            elif child in active:
                low[node] = min(low[node], index[child])
        if low[node] == index[node]:
            members = []
            while True:
                member = stack.pop()
                active.remove(member)
                members.append(member)
                if member == node:
                    break
            components.append(sorted(members))

    for node in graph:
        if node not in index:
            visit(node)
    components.sort(key=lambda members: members[0])
    owner = {node: i for i, members in enumerate(components) for node in members}
    dependencies = {i: {owner[c] for n in members for c in graph[n] if owner[c] != i}
                    for i, members in enumerate(components)}
    remaining = {i: len(deps) for i, deps in dependencies.items()}
    parents = defaultdict(set)
    for i, deps in dependencies.items():
        for child in deps:
            parents[child].add(i)
    levels = {i: 0 for i, count in remaining.items() if count == 0}
    queue = deque(sorted(levels))
    while queue:
        child = queue.popleft()
        for parent in sorted(parents[child]):
            remaining[parent] -= 1
            if remaining[parent] == 0:
                levels[parent] = 1 + max(levels[c] for c in dependencies[parent])
                queue.append(parent)
    if len(levels) != len(components):
        raise ValueError('SCC condensation did not produce an acyclic graph')
    return [{'id': f'C{i:04d}', 'layer': levels[i], 'members': members,
             'cyclic': len(members) > 1 or any(n in graph[n] for n in members),
             'dependsOn': [f'C{c:04d}' for c in sorted(dependencies[i])]}
            for i, members in sorted(enumerate(components), key=lambda item: (levels[item[0]], item[1][0]))]


def reference_tree(nodes, roots, selected, groups, title):
    """Expand each node once globally; every repeated/cyclic edge gets a reference."""
    refs = {key: f'N{i:04d}' for i, key in enumerate(sorted(nodes))}
    seen = set()
    lines = [title, 'Every node expands once. -> [Nxxxx] is a shared/cyclic reference.',
             'Versions include peer/patch contexts. Optional edges are retained.', '']

    def visit(key, prefix, edge_label):
        label = f'{edge_label}{key} [{refs[key]}]'
        if key in seen:
            lines.append(prefix + label + f' -> [{refs[key]}]')
            return
        seen.add(key)
        lines.append(prefix + label)
        children = [e for e in nodes[key]['edges'] if e['group'] in groups and e['target'] in selected]
        for edge in sorted(children, key=lambda e: (e['group'], e['name'], e['target'])):
            visit(edge['target'], prefix + '  ', f"{edge['group']} {edge['name']}: ")

    for root in roots:
        visit(root, '', '')
    # Full-lock views retain even snapshots not reachable from workspace roots.
    for key in sorted(selected - seen):
        lines.append('\nLOCK-ONLY ROOT (not reachable from preceding roots):')
        visit(key, '', '')
    if seen != selected:
        raise ValueError('Tree omitted nodes')
    return '\n'.join(lines) + '\n'


def plan_for(name, effective, policy):
    if name in policy['exact']:
        return policy['exact'][name]
    for rule in policy['prefixes']:
        if name.startswith(rule['prefix']):
            return {k: v for k, v in rule.items() if k != 'prefix'}
    return policy['productFallback' if effective else 'toolingFallback']


def build():
    inventory = audit.build()  # verify pinned identity/hashes and source candidates
    if json.loads(audit.OUT.read_text('utf-8')) != inventory:
        raise ValueError('Run the upstream dependency audit first; saved inventory differs')
    policy = json.loads(POLICIES.read_text('utf-8'))
    sections = audit.blocks(audit.git_bytes('pnpm-lock.yaml').decode(), 0)
    importers = audit.blocks(sections['importers'], 2)
    snapshots = audit.blocks(sections['snapshots'], 2)
    metadata = audit.blocks(sections['packages'], 2)
    nodes = {}
    for key, body in sorted(snapshots.items()):
        name, version = identity(key)
        record = metadata.get(name + '@' + version, '')
        integrity = re.search(r'\bintegrity:\s*([^,}\s]+)', record)
        fields = audit.blocks(record, 4)
        nodes[key] = {'kind': 'registry', 'name': name, 'version': version,
                      'contextKey': key, 'integrity': integrity[1] if integrity else None,
                      'peerDeclarations': audit.mapping_values(fields.get('peerDependencies', ''), 6),
                      'platformConstraints': [line.strip() for line in record.splitlines()
                                              if re.match(r'    (?:os|cpu|libc):', line)],
                      'optionalSnapshot': bool(re.search(r'(?m)^    optional: true$', body)),
                      'edges': []}
    for path in sorted(importers):
        manifest_path = 'package.json' if path == '.' else path + '/package.json'
        manifest = json.loads(audit.git_bytes(manifest_path))
        nodes['workspace:' + path] = {'kind': 'workspace', 'name': manifest.get('name', path),
                                     'version': manifest.get('version'),
                                     'manifestSha256': hashlib.sha256(audit.git_bytes(manifest_path)).hexdigest(),
                                     'peerDeclarations': manifest.get('peerDependencies', {}), 'edges': []}
    for owner, body in [(key, body) for key, body in snapshots.items()]:
        for group, fields in audit.blocks(body, 4).items():
            if group not in ('dependencies', 'optionalDependencies'):
                continue
            for name, version in audit.mapping_values(fields, 6).items():
                nodes[owner]['edges'].append({'group': group, 'name': name, 'resolved': version,
                                              'target': resolve(name, version, '', nodes)})
    for owner, body in importers.items():
        for group, fields in audit.blocks(body, 4).items():
            if group not in ('dependencies', 'devDependencies', 'optionalDependencies'):
                continue
            for name, raw in audit.blocks(fields, 6).items():
                values = audit.mapping_values(raw, 8)
                nodes['workspace:' + owner]['edges'].append({
                    'group': group, 'name': name, 'declared': values['specifier'],
                    'resolved': values['version'],
                    'target': resolve(name, values['version'], owner, nodes)})
    for node in nodes.values():
        node['edges'].sort(key=lambda e: (e['group'], e['name'], e['target']))
    product_groups = {'dependencies', 'optionalDependencies'}
    all_groups = product_groups | {'devDependencies'}
    product_roots = ['workspace:' + p for p in audit.PACKAGES]
    declared = closure(product_roots, nodes, product_groups)
    dispositions = []
    source_roots = []
    for extra in inventory['additionalSourceImports']:
        name = extra['name']
        decision = policy['sourceImports'].get(name)
        if decision is None:
            raise ValueError('Unclassified additional source import: ' + name)
        row = {'name': name, **decision, 'references': extra['references']}
        if decision['disposition'] == 'include-value-root':
            matches = {e['target'] for n in nodes.values() if n['kind'] == 'workspace'
                       for e in n['edges'] if e['name'] == name}
            if len(matches) != 1:
                raise ValueError(f'Expected one source resolution for {name}: {matches}')
            row['target'] = next(iter(matches))
            source_roots.append(row['target'])
        dispositions.append(row)
    effective = declared | closure(source_roots, nodes, product_groups)
    generation_roots = [e['target'] for e in nodes['workspace:.']['edges']
                        if e['name'] in ('jison', 'langium-cli')]
    if len(generation_roots) != 2:
        raise ValueError('Expected both locked parser generation tools')
    generation = closure(generation_roots, nodes, product_groups)
    workspace_roots = sorted(k for k in nodes if k.startswith('workspace:'))
    workspace_reachable = closure(workspace_roots, nodes, all_groups)
    components = bottom_up(nodes, effective, product_groups)
    layers = {n: c['layer'] for c in components for n in c['members']}
    # Trace every product descendant back to its direct or supplemental root.
    feature_roots = {e['target'] for r in product_roots for e in nodes[r]['edges']
                     if e['group'] in product_groups} | set(source_roots)
    owners = defaultdict(set)
    for seed in sorted(feature_roots):
        for child in closure([seed], nodes, product_groups):
            owners[child].add(nodes[seed]['name'])
    for key, node in nodes.items():
        node['scopes'] = [name for name, selected in [
            ('declared-product', declared), ('source-inclusive-product', effective),
            ('parser-generation', generation), ('workspace-toolchain', workspace_reachable)] if key in selected]
        node['plan'] = {'state': 'proposal-not-implemented',
                        **plan_for(node['name'], key in effective, policy)}
        if key in effective:
            node['bottomUpLayer'] = layers[key]
            node['featureOwners'] = sorted(owners[key])
    data = {'schema': 'py-mermaid-complete-dependency-graph/v1',
            'upstreamCommit': inventory['upstreamCommit'],
            'pnpmLockSha256': inventory['canonicalInputsSha256']['pnpm-lock.yaml'],
            'inventorySha256': hashlib.sha256(audit.OUT.read_bytes()).hexdigest(),
            'policySha256': hashlib.sha256(POLICIES.read_bytes()).hexdigest(),
            'pythonMigrationArchitecture': policy.get('architecture'),
            'scope': 'All pinned lock snapshots and all 13 workspace importers; declared edges, not bundle reachability.',
            'counts': {'registrySnapshots': len(snapshots), 'workspaceImporters': len(importers),
                       'totalNodes': len(nodes), 'totalEdges': sum(len(n['edges']) for n in nodes.values()),
                       'declaredProductRegistrySnapshots': sum(nodes[n]['kind'] == 'registry' for n in declared),
                       'sourceInclusiveRegistrySnapshots': sum(nodes[n]['kind'] == 'registry' for n in effective),
                       'sourceInclusiveUniqueRegistryNames': len({nodes[n]['name'] for n in effective if nodes[n]['kind'] == 'registry'}),
                       'sourceInclusiveComponents': len(components),
                       'sourceInclusiveCyclicComponents': sum(c['cyclic'] for c in components),
                       'lockOnlySnapshots': len(set(nodes) - workspace_reachable),
                       'unresolvedEdges': 0},
            'roots': {'declaredProduct': product_roots, 'additionalSourceValues': sorted(source_roots),
                      'parserGeneration': sorted(generation_roots), 'allWorkspaces': workspace_roots},
            'additionalSourceDispositions': dispositions, 'nodes': dict(sorted(nodes.items())),
            'bottomUpComponents': components,
            'limitations': ['Complete for pinned pnpm mapping edges, not every bundled internal algorithm or resource.',
                            'Peer ranges are metadata; resolved snapshot edges/context keys are retained without inventing missing peer providers.',
                            'Source additions are static import candidates with explicit type/test exclusions, not proven bundle execution.',
                            'Porting decisions are proposals; Python candidate metadata is not an accepted runtime lock or equivalence proof.',
                            'Platform-optional packages remain visible; no third-party tarball license or native dependency closure claim.']}
    product_text = reference_tree(nodes, product_roots + sorted(source_roots), effective, product_groups,
                                  'MERMAID PRODUCT + SOURCE VALUE DEPENDENCY TREE (PINNED)')
    full_text = reference_tree(nodes, workspace_roots, set(nodes), all_groups,
                               'ALL WORKSPACES / BUILD / TEST / DOCS / LOCK-ONLY SNAPSHOTS (PINNED)')
    md = ['# 从底层向上的依赖工作索引（自动生成）', '',
          '来源和选型说明见 [迁移方案](../docs/DEPENDENCY_MIGRATION.md)。包管理叶节点不等于算法简单。',
          '目标采用 [Canvas 原生架构](../docs/CANVAS_NATIVE_ARCHITECTURE.md)；discard-browser-layer 表示淘汰该运行机制，相关图形功能由 Python 数据与 Canvas 承接。',
          '层号按依赖边的 SCC 缩图计算，依赖先于使用者；同一 SCC 内部一起处理。每项计划均未实现/未验证等价。', '',
          '| 层 | SCC | 精确节点 | 处理策略 | Python 候选/实现 | 工作包 |',
          '| --- | --- | --- | --- | --- | --- |']
    for component in components:
        for key in component['members']:
            plan = nodes[key]['plan']
            label = key.replace('|', '&#124;')
            implementation = '不进入目标运行时（用户排除）' if plan['action'] == 'excluded-by-user' else ', '.join(plan.get('candidates', [])) or 'Python 重写/追踪调用面'
            md.append(f"| {component['layer']} | {component['id']}{' ↻' if component['cyclic'] else ''} | `{label}` | {plan['action']} | {implementation} | {plan['workPackage']} |")
    return data, product_text, full_text, '\n'.join(md) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--build', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data, product, full, bottom = build()
    outputs = {'references/dependency-tree.json': json.dumps(data, ensure_ascii=False, indent=2) + '\n',
               'references/dependency-tree.txt': product,
               'references/dependency-toolchain-tree.txt': full,
               'references/dependency-bottom-up.md': bottom}
    for name, payload in outputs.items():
        path = ROOT / name
        if args.build:
            path.write_text(payload, encoding='utf-8', newline='\n')
        elif not path.exists() or path.read_text('utf-8') != payload:
            raise ValueError('Generated dependency view differs: ' + name)
    print(json.dumps(data['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
