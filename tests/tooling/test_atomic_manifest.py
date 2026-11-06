"""Atomic evidence updates tolerate temporary Windows sharing locks only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from run_support import write_json


class AtomicManifestTests(unittest.TestCase):
    def test_transient_lock_preserves_old_file_until_atomic_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'run.json'
            target.write_text('{"old":true}', encoding='utf-8')
            original = Path.replace
            lock = PermissionError('sharing violation'); lock.winerror = 32
            calls = []

            def replace(path, destination):
                calls.append(path)
                if len(calls) == 1:
                    self.assertEqual(json.loads(target.read_text(encoding='utf-8')), {'old': True})
                    raise lock
                return original(path, destination)

            with patch.object(Path, 'replace', replace), patch('run_support.time.sleep'):
                write_json(target, {'new': True})
            self.assertEqual(len(calls), 2)
            self.assertEqual(json.loads(target.read_text(encoding='utf-8')), {'new': True})
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])

    def test_persistent_or_unrelated_denials_propagate_and_leave_old_evidence(self):
        for winerror, expected_attempts in [(5, 6), (999, 1), (None, 1)]:
            with self.subTest(winerror=winerror), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / 'run.json'
                target.write_text('{"old":true}', encoding='utf-8')
                error = PermissionError('denied')
                if winerror is not None: error.winerror = winerror
                with patch.object(Path, 'replace', side_effect=error) as replace, patch('run_support.time.sleep'):
                    with self.assertRaises(PermissionError): write_json(target, {'new': True})
                self.assertEqual(replace.call_count, expected_attempts)
                self.assertEqual(json.loads(target.read_text(encoding='utf-8')), {'old': True})
                self.assertEqual(list(Path(directory).glob('*.tmp')), [])


if __name__ == '__main__': unittest.main()
