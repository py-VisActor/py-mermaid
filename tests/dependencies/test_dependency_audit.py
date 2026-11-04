"""Targeted controls for the read-only pinned dependency inventory."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import audit_dependencies as audit


class DependencyAuditTests(unittest.TestCase):
    def test_snapshot_scalar_does_not_become_dependency(self):
        # pnpm adds metadata beside dependency blocks. It must close a block,
        # rather than invent an edge to a package called "optional".
        snapshot = "    dependencies:\n      'cose-base': 2.2.0\n    optional: true\n"
        groups = audit.blocks(snapshot, 4)
        self.assertEqual(audit.mapping_values(groups['dependencies'], 6),
                         {'cose-base': '2.2.0'})

    def test_context_and_patch_keys_are_not_flattened(self):
        text = "  'plugin@1.0.0(host@2.0.0)': {}\n  'plugin@1.0.0(host@3.0.0)': {}\n  'rough@1.0.0(patch_hash=abc)': {}\n"
        self.assertEqual(set(audit.blocks(text, 2)), {
            'plugin@1.0.0(host@2.0.0)', 'plugin@1.0.0(host@3.0.0)',
            'rough@1.0.0(patch_hash=abc)'})

    def test_duplicate_blocks_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            audit.blocks('  duplicate: {}\n  duplicate: {}\n', 2)

    def test_nested_dependency_value_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            audit.mapping_values('      nested:\n        value: unexpected', 6)

    def test_wrong_checkout_commit_is_rejected(self):
        with patch.object(audit.subprocess, 'check_output', return_value=b'wrong\n'):
            with self.assertRaisesRegex(ValueError, 'commit differs'):
                audit.build()

    def test_dirty_checkout_is_rejected(self):
        import json
        commit = json.loads((audit.ROOT / 'references/upstream.lock.json').read_bytes())['commit']
        with patch.object(audit.subprocess, 'check_output',
                          side_effect=[commit.encode(), b' M package.json\n']):
            with self.assertRaisesRegex(ValueError, 'dirty'):
                audit.build()


if __name__ == '__main__':
    unittest.main()
