"""Prevent separate source cases overwriting each other's raw evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from bulk_support import load_cases


class PortableFixtureIdentity(unittest.TestCase):
    def document(self,ids):
        root=Path(__file__).resolve().parents[2]
        template=next(c for c in json.loads((root/'tests/bulk/cases-C.json').read_text('utf-8'))['cases'] if c['id']=='C-info-show')
        cases=[]
        for id in ids:
            row=copy.deepcopy(template);row['id']=id;cases.append(row)
        return {'schema':'py-mermaid-bulk-cases/v1','group':'C','cases':cases}

    def load(self,ids):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'cases.json';p.write_text(json.dumps(self.document(ids)),encoding='utf-8')
            return load_cases([p])

    def test_case_sensitive_language_tokens_need_distinct_portable_case_ids(self):
        for ids in [('format-x','format-X'),('duration-M','duration-m'),('same','same')]:
            with self.subTest(ids=ids),self.assertRaisesRegex(ValueError,'case-insensitive'):self.load(ids)

    def test_device_names_and_trailing_dots_are_rejected_before_writing_artifacts(self):
        for id in ('NUL','con.test','LPT1','COM9','case.'):
            with self.subTest(id=id),self.assertRaisesRegex(ValueError,'portable'):self.load([id])

    def test_explicit_token_names_preserve_both_cases_without_overwrite(self):
        ids=['format-unix-seconds','format-unix-ms','duration-months','duration-minutes']
        self.assertEqual([c['id'] for c in self.load(ids)],ids)


if __name__=='__main__':unittest.main()
