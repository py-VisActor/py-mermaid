"""Independent direct-schema defaults, plus source configuration consumers."""
from pathlib import Path
import json
import unittest
from py_mermaid.runtime.registry import parse_diagram
from py_mermaid.runtime.common import config_dict

DATA=json.loads(Path(__file__).with_name('config_cases.json').read_text(encoding='utf-8'))
class SourceConfigurationTests(unittest.TestCase):
    pass

def _method(case):
    def test(self):
        diagram=parse_diagram(case['source']);actual=config_dict(diagram)
        self.assertIn(case['section'],actual)
        if case.get('runtimeAbsent'):
            self.assertNotIn(case['property'],actual[case['section']]);return
        self.assertIn(case['property'],actual[case['section']]);self.assertEqual(actual[case['section']][case['property']],case['expected'])
    test.__doc__=case['origin']['symbol']
    return test
for _case in DATA['rows']:setattr(SourceConfigurationTests,'test_default_'+_case['id'].replace('-','_'),_method(_case))
