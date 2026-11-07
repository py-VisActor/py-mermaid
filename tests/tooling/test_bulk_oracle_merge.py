"""Synthetic independent evidence controls for strict oracle byte reuse."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('bulk_oracle_merge', Path(__file__).resolve().parents[2]/'tools/merge_bulk_oracles.py')
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class OracleMergeEvidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.row = {'id': 'case-a', 'kind': 'journey', 'source': 'journey\nA: 4: Me',
                    'config': {'htmlLabels': True}, 'resources': [], 'browserResources': [],
                    'group': 'B', 'origin': {'path': 'source', 'line': 7}, 'expect': 'render'}

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def seal(self, donor):
        runpath, _, _ = donor
        run = tool.load(runpath)
        run['artifacts'] = {p.relative_to(runpath.parent).as_posix():
                            {'sha256': tool.digest(p), 'bytes': p.stat().st_size}
                            for p in runpath.parent.rglob('*') if p.is_file() and p != runpath}
        self.write(runpath, run)

    def donor(self, name='donor', rows=None, status='FAILED', identity=None):
        root = self.root/name
        oracle, frozen = root/'artifacts/oracle', root/'artifacts/fixtures/browser-cases.json'
        rows = rows or [copy.deepcopy(self.row)]
        self.write(frozen, {'cases': rows})
        identity = identity or {'commit': 'fixed', 'package': 'mermaid@12.2.0', 'bundleSha256': 'bundle'}
        self.write(oracle/'identity.json', identity)
        captured = []
        for row in rows:
            state = 'excluded' if row['expect'] in ('excluded','excluded_by_static_scope') else 'error' if row['expect']=='syntax_error' else 'captured'
            captured.append({'id': row['id'], 'status': state} if state=='excluded' else {'id': row['id'], 'kind': row['kind'], 'expect': row['expect'], 'status': state})
            suffixes = ('.png', '.svg', '.json') if state=='captured' else ('.error.json',) if state=='error' else ()
            for suffix in suffixes:
                (oracle/(row['id']+suffix)).write_bytes((row['id']+suffix+' original bytes').encode())
        self.write(oracle/'manifest.json', {'identity': identity, 'browser': 'fixed-browser', 'fixtureSha256': tool.digest(frozen), 'cases': captured})
        command = {'argv': ['node', 'tools/oracle/bulk_capture.cjs', '--fixtures', str(frozen), '--out', str(oracle)],
                   'cwd': str(root), 'status': 'SUCCESS', 'exitCode': 0, 'finishedAtUtc': 'closed',
                   'stdout': 'commands/001-source/stdout.log'}
        self.write(root/'commands/001-source/result.json', command)
        self.write(root/'run.json', {'status': status, 'finishedAtUtc': 'closed', 'commands': [command], 'artifacts': {}})
        donor = (root/'run.json', oracle, frozen)
        self.seal(donor)
        return donor

    def final(self, rows=None):
        path = self.root/'final.json'
        self.write(path, {'cases': rows if rows is not None else [self.row]})
        return path

    def test_failed_run_successful_source_command_preserves_bytes(self):
        donor = self.donor()
        result = tool.merge(self.final(), [donor], self.root/'out')
        self.assertEqual(result['reuse']['donors'][0]['runStatus'], 'FAILED')
        self.assertEqual(result['fixtureSha256'], tool.digest(self.root/'final.json'))
        for suffix in ('.png', '.svg', '.json'):
            self.assertEqual((self.root/'out'/('case-a'+suffix)).read_bytes(), (donor[1]/('case-a'+suffix)).read_bytes())

    def test_changed_png_bytes_rejected_before_output(self):
        for suffix in ('.png', '.svg', '.json'):
            with self.subTest(suffix=suffix):
                donor = self.donor('donor'+suffix); (donor[1]/('case-a'+suffix)).write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'changed closed-run artifact'):
                    tool.merge(self.final(), [donor], self.root/'out')
                self.assertFalse((self.root/'out').exists())

    def test_every_input_field_is_bound_including_types(self):
        donor = self.donor()
        for key, value in [('source', 'changed'), ('origin', {}), ('resources', ['changed']), ('browserResources', ['changed']), ('group', 'C'), ('expect', 'syntax_error'), ('config', {'htmlLabels': 1})]:
            with self.subTest(key=key):
                row = copy.deepcopy(self.row); row[key] = value
                with self.assertRaisesRegex(ValueError, 'input differs'):
                    tool.merge(self.final([row]), [donor], self.root/'out')

    def test_missing_or_extra_final_case_rejected(self):
        donor = self.donor()
        with self.assertRaises(ValueError): tool.merge(self.final([]), [donor], self.root/'out')
        extra = dict(self.row, id='case-b')
        with self.assertRaisesRegex(ValueError, 'denominator'):
            tool.merge(self.final([self.row, extra]), [donor], self.root/'out')

    def test_two_donor_identity_difference_rejected(self):
        a = self.donor('a'); row = dict(self.row, id='case-b')
        b = self.donor('b', [row], identity={'commit': 'different'})
        with self.assertRaisesRegex(ValueError, 'Different fixed source identity'):
            tool.merge(self.final([self.row, row]), [a, b], self.root/'out')

    def test_manifest_identity_must_equal_identity_json(self):
        donor = self.donor(); m = tool.load(donor[1]/'manifest.json');m['identity']={'commit':'other'}
        self.write(donor[1]/'manifest.json',m);self.seal(donor)
        with self.assertRaisesRegex(ValueError, 'manifest.identity'):
            tool.merge(self.final(), [donor], self.root/'out')

    def test_fixture_hash_mismatch_even_with_resealed_artifact(self):
        donor = self.donor(); self.write(donor[2], {'cases': [dict(self.row, source='other')]});self.seal(donor)
        with self.assertRaisesRegex(ValueError, 'fixtureSha256'):
            tool.merge(self.final(), [donor], self.root/'out')

    def test_source_command_failure_rejected(self):
        donor = self.donor();run=tool.load(donor[0]);run['commands'][0].update(status='FAILED',exitCode=1)
        self.write(donor[0],run);self.write(donor[0].parent/'commands/001-source/result.json',run['commands'][0]);self.seal(donor)
        with self.assertRaisesRegex(ValueError, 'successful bulk_capture'):
            tool.merge(self.final(), [donor], self.root/'out')

    def test_running_run_rejected(self):
        donor=self.donor(status='RUNNING')
        with self.assertRaisesRegex(ValueError, 'not closed'):
            tool.merge(self.final(),[donor],self.root/'out')

    def test_unfinished_source_result_rejected(self):
        donor=self.donor();result_path=donor[0].parent/'commands/001-source/result.json'
        result=tool.load(result_path);result['finishedAtUtc']=None
        self.write(result_path,result);self.seal(donor)
        with self.assertRaisesRegex(ValueError,'successful bulk_capture'):
            tool.merge(self.final(),[donor],self.root/'out')

    def test_casefold_collision_and_duplicate_donor_rejected(self):
        donor=self.donor()
        with self.assertRaisesRegex(ValueError,'casefold'):
            tool.merge(self.final([self.row,dict(self.row,id='CASE-A')]),[donor],self.root/'out')
        with self.assertRaisesRegex(ValueError,'Duplicate donor'):
            tool.merge(self.final(),[donor,donor],self.root/'out')

    def test_error_and_excluded_cases_keep_denominator(self):
        error=dict(self.row,id='negative',expect='syntax_error');excluded=dict(self.row,id='excluded',expect='excluded_by_static_scope')
        donor=self.donor(rows=[error,excluded]);m=tool.merge(self.final([error,excluded]),[donor],self.root/'out')
        self.assertEqual([c['status'] for c in m['cases']],['error','excluded'])
        self.assertTrue((self.root/'out/negative.error.json').is_file())

    def test_existing_output_is_never_overwritten(self):
        donor=self.donor();out=self.root/'out';out.mkdir()
        with self.assertRaisesRegex(ValueError,'new directory'):
            tool.merge(self.final(),[donor],out)

    def test_dotted_id_does_not_collide_with_prefix_case(self):
        dotted=dict(self.row,id='case-a.box')
        donor=self.donor(rows=[self.row,dotted])
        m=tool.merge(self.final([self.row,dotted]),[donor],self.root/'out')
        self.assertEqual(len(m['cases']),2)
        self.assertTrue((self.root/'out/case-a.box.png').exists())


    def replacement_pair(self):
        unchanged=dict(self.row,id='case-b')
        old=self.donor('old',[self.row,unchanged])
        revised=dict(self.row,expect='syntax_error',expectedErrorCodes=['SYNTAX_ERROR'])
        fresh=self.donor('fresh',[revised])
        final=self.final([revised,unchanged])
        return old,fresh,final

    def test_explicit_replacement_verifies_old_and_reuses_only_fresh_bytes(self):
        old,fresh,final=self.replacement_pair()
        merged=tool.merge(final,[old,fresh],self.root/'out',replace_case_ids=['case-a'])
        self.assertEqual(len(merged['cases']),2)
        self.assertEqual(merged['cases'][0]['status'],'error')
        self.assertEqual((self.root/'out/case-a.error.json').read_bytes(),(fresh[1]/'case-a.error.json').read_bytes())
        self.assertFalse((self.root/'out/case-a.png').exists())
        self.assertEqual((self.root/'out/case-b.png').read_bytes(),(old[1]/'case-b.png').read_bytes())
        previous=merged['reuse']['supersededInputs'][0]
        self.assertEqual(previous['input'],self.row)
        self.assertEqual(previous['record']['status'],'captured')
        self.assertEqual(len(previous['files']),3)
        for item in previous['files']:
            self.assertEqual(item['sha256'],tool.digest(item['source']))

    def test_explicit_replacement_allows_fresh_donor_before_old(self):
        old,fresh,final=self.replacement_pair()
        result=tool.merge(final,[fresh,old],self.root/'out',replace_case_ids=['case-a'])
        self.assertEqual(len(result['cases']),2)
        self.assertEqual(result['reuse']['replacementCaseIds'],['case-a'])

    def test_replacement_missing_fresh_donor_rejected_before_output(self):
        old,fresh,final=self.replacement_pair()
        with self.assertRaisesRegex(ValueError,'Missing fresh replacement'):
            tool.merge(final,[old],self.root/'out',replace_case_ids=['case-a'])
        self.assertFalse((self.root/'out').exists())

    def test_changed_input_without_explicit_replacement_rejected(self):
        old,fresh,final=self.replacement_pair()
        with self.assertRaisesRegex(ValueError,'input differs'):
            tool.merge(final,[old,fresh],self.root/'out')
        self.assertFalse((self.root/'out').exists())

    def test_unknown_or_unused_replacement_id_rejected(self):
        old,fresh,final=self.replacement_pair()
        with self.assertRaisesRegex(ValueError,'Unknown replacement'):
            tool.merge(final,[old,fresh],self.root/'out',replace_case_ids=['typo'])
        with self.assertRaisesRegex(ValueError,'Unused replacement'):
            tool.merge(self.final(),[self.donor('same')],self.root/'out',replace_case_ids=['case-a'])
        self.assertFalse((self.root/'out').exists())

    def test_replacement_does_not_skip_corrupted_old_evidence(self):
        old,fresh,final=self.replacement_pair()
        (old[1]/'case-a.png').write_bytes(b'corrupted old png')
        with self.assertRaisesRegex(ValueError,'changed closed-run artifact'):
            tool.merge(final,[old,fresh],self.root/'out',replace_case_ids=['case-a'])
        self.assertFalse((self.root/'out').exists())

    def test_replacement_does_not_skip_bad_old_manifest_metadata(self):
        old,fresh,final=self.replacement_pair()
        manifest=tool.load(old[1]/'manifest.json');manifest['cases'][0]['expect']='unrelated'
        self.write(old[1]/'manifest.json',manifest);self.seal(old)
        with self.assertRaisesRegex(ValueError,'metadata mismatch'):
            tool.merge(final,[old,fresh],self.root/'out',replace_case_ids=['case-a'])

    def test_fresh_replacement_full_row_mismatch_not_accepted(self):
        old,fresh,final=self.replacement_pair()
        wrong=dict(self.row,expect='syntax_error',expectedErrorCodes=['OTHER'])
        other=self.donor('other',[wrong])
        with self.assertRaisesRegex(ValueError,'Duplicate superseded'):
            tool.merge(final,[old,other],self.root/'out',replace_case_ids=['case-a'])
        self.assertFalse((self.root/'out').exists())

    def test_replacement_duplicate_requested_id_rejected(self):
        old,fresh,final=self.replacement_pair()
        with self.assertRaisesRegex(ValueError,'casefold'):
            tool.merge(final,[old,fresh],self.root/'out',replace_case_ids=['case-a','CASE-A'])
