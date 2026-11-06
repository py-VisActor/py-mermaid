"""Independent integrity boundaries for immutable oracle reuse."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from reuse_oracle import validate_reuse


class OracleReuseIntegrity(unittest.TestCase):
    def fixture(self):return {'cases':[{'id':'A','text':'flowchart TD\nA','config':{'look':'neo'}}]}

    def test_equal_inputs_and_changed_assertion_metadata_are_reusable(self):
        old=self.fixture();new=copy.deepcopy(old);new['cases'][0]['title']='Updated explanation'
        validate_reuse(old,new,set())

    def test_changed_executed_input_requires_refresh(self):
        old=self.fixture();new=copy.deepcopy(old);new['cases'][0]['text']='flowchart TD\nB'
        with self.assertRaises(ValueError):validate_reuse(old,new,set())
        validate_reuse(old,new,{'A'})

    def test_denominator_or_unknown_refresh_cannot_borrow_evidence(self):
        with self.assertRaises(ValueError):validate_reuse(self.fixture(),{'cases':[]},set())
        with self.assertRaises(ValueError):validate_reuse(self.fixture(),self.fixture(),{'unknown'})

    def test_added_case_requires_its_own_fresh_capture(self):
        old=self.fixture();new=copy.deepcopy(old);new['cases'].append({'id':'B','text':'flowchart TD\nB'})
        with self.assertRaises(ValueError):validate_reuse(old,new,set())
        validate_reuse(old,new,{'B'})

if __name__=='__main__':unittest.main()
