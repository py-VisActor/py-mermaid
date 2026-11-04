"""Dependency completeness and ordering controls; no product/JS execution."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import audit_dependencies as audit
import build_dependency_tree as tree


def node(*children):
    return {'edges': [{'name': name, 'group': 'dependencies', 'target': name}
                      for name in children]}


class TreeAlgorithmTests(unittest.TestCase):
    def test_cycles_are_atomic_and_dependencies_come_first(self):
        graph = {'root': node('a'), 'a': node('b'), 'b': node('a', 'leaf'), 'leaf': node()}
        components = tree.bottom_up(graph, set(graph), {'dependencies'})
        levels = {n: c['layer'] for c in components for n in c['members']}
        self.assertEqual(levels, {'leaf': 0, 'a': 1, 'b': 1, 'root': 2})
        self.assertEqual([c['members'] for c in components if c['cyclic']], [['a', 'b']])

    def test_shared_and_cyclic_tree_paths_keep_all_edges(self):
        graph = {'root': node('left', 'right'), 'left': node('shared'),
                 'right': node('shared'), 'shared': node('root')}
        text = tree.reference_tree(graph, ['root'], set(graph), {'dependencies'}, 'test')
        for edge in ['dependencies left:', 'dependencies right:']:
            self.assertEqual(text.count(edge), 1)
        self.assertEqual(text.count('dependencies shared:'), 2)
        self.assertEqual(text.count('dependencies root:'), 1)
        self.assertEqual(len(re.findall(r' -> \[N\d+\]', text)), 2)

    def test_optional_edges_are_preserved(self):
        graph = {'root': {'edges': [{'name': 'platform', 'group': 'optionalDependencies', 'target': 'platform'}]},
                 'platform': node()}
        self.assertEqual(tree.closure(['root'], graph, {'dependencies'}), {'root'})
        self.assertEqual(tree.closure(['root'], graph, {'dependencies', 'optionalDependencies'}), set(graph))

    def test_workspace_and_alias_resolution(self):
        graph = {'workspace:packages/parser': {}, 'actual@1.0.0': {}}
        self.assertEqual(tree.resolve('parser', 'link:../parser', 'packages/mermaid', graph),
                         'workspace:packages/parser')
        self.assertEqual(tree.resolve('alias', 'actual@1.0.0', '', graph), 'actual@1.0.0')
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            tree.resolve('missing', '1.0.0', '', graph)


class PinnedTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'references/dependency-tree.json').read_text('utf-8'))

    def test_every_raw_snapshot_header_is_present(self):
        # Independent line scan of the pinned snapshots section, rather than
        # reusing the graph builder's block parser to compute its denominator.
        raw = audit.git_bytes('pnpm-lock.yaml').decode().split('\nsnapshots:\n', 1)[1]
        keys = set()
        for line in raw.splitlines():
            if line.startswith('  ') and not line.startswith('   ') and line.strip():
                match = re.fullmatch(r"  (?:'([^']+)'|([^' ].*?)):(?: \{\})?", line)
                self.assertIsNotNone(match, line)
                keys.add(match[1] or match[2])
        actual = {k for k, n in self.data['nodes'].items() if n['kind'] == 'registry'}
        self.assertEqual(keys, actual)

    def test_all_targets_and_plan_owners_exist(self):
        policy = json.loads(tree.POLICIES.read_text('utf-8'))
        nodes = self.data['nodes']
        for key, n in nodes.items():
            self.assertIn(n['plan']['workPackage'], policy['workPackages'], key)
            for edge in n['edges']:
                self.assertIn(edge['target'], nodes, (key, edge))

    def test_old_closure_and_supplemental_value_roots_are_retained(self):
        old = json.loads(audit.OUT.read_text('utf-8'))
        declared = {k for k, n in self.data['nodes'].items()
                    if n['kind'] == 'registry' and 'declared-product' in n['scopes']}
        self.assertEqual(declared, set(old['declaredProductionClosure']['nodes']))
        roots = self.data['roots']['additionalSourceValues']
        self.assertEqual({self.data['nodes'][k]['name'] for k in roots},
                         {'js-yaml', 'langium', 'fastdom', 'non-layered-tidy-tree-layout'})
        self.assertTrue(all('source-inclusive-product' in self.data['nodes'][r]['scopes'] for r in roots))
        self.assertFalse(any(k.startswith('vitest@') for k, n in self.data['nodes'].items()
                             if 'source-inclusive-product' in n['scopes']))

    def test_layering_has_no_backwards_dependency_across_components(self):
        components = self.data['bottomUpComponents']
        lookup = {n: c for c in components for n in c['members']}
        nodes = self.data['nodes']
        effective = {k for k, n in nodes.items() if 'source-inclusive-product' in n['scopes']}
        self.assertEqual(set(lookup), effective)
        for key in effective:
            for edge in nodes[key]['edges']:
                if edge['group'] not in {'dependencies', 'optionalDependencies'}:
                    continue
                child = edge['target']
                if lookup[key]['id'] != lookup[child]['id']:
                    self.assertLess(lookup[child]['layer'], lookup[key]['layer'], (key, child))


if __name__ == '__main__':
    unittest.main()
