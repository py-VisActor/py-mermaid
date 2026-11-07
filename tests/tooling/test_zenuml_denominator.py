"""Strict Zen selection cannot silently omit regression/source-positive cases."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT/'tools') not in sys.path:sys.path.insert(0,str(ROOT/'tools'))
from check_zenuml_parity import select_zenuml_cases


def corpus():
    return sum((json.loads((ROOT/path).read_text('utf-8'))['cases'] for path in
                ('tests/bulk/cases-C.json','tests/bulk/cases-gap-C.json')),[])


class ZenUMLDenominator(unittest.TestCase):
    def test_all186_positives_include_base148_old28_and_new10(self):
        selected,counts=select_zenuml_cases(corpus())
        self.assertEqual(counts,{'baseVisualDenominator':148,'additionalDenominator':38,'totalDenominator':186})
        self.assertEqual(len(selected),186)
        self.assertEqual(sum(c['id'].startswith('gap-c-zen-') for c in selected),10)
        self.assertIn('C-zenuml-creation',{c['id'] for c in selected})
        self.assertIn('gap-c-zen-typed-assignee',{c['id'] for c in selected})

    def test_each_of148_original_ids_is_mandatory(self):
        rows=corpus()
        base=[c for c in rows if c['kind']=='zenuml' and c['origin']['path']=='e2e/data/compare-cases.js']
        self.assertEqual(len(base),148)
        for case in base:
            with self.subTest(id=case['id']):
                with self.assertRaisesRegex(ValueError,'Locked148'):
                    select_zenuml_cases([c for c in rows if c['id']!=case['id']])

    def test_same_count_replacement_cannot_substitute_a_base_id(self):
        rows=copy.deepcopy(corpus())
        case=next(c for c in rows if c['kind']=='zenuml' and c['origin']['path']=='e2e/data/compare-cases.js')
        case['id']='fabricated-base-replacement'
        with self.assertRaisesRegex(ValueError,'Locked148'):
            select_zenuml_cases(rows)

    def test_changed_base_origin_cannot_hide_identity_drift(self):
        rows=copy.deepcopy(corpus())
        case=next(c for c in rows if c['id']=='C-zenuml-source-creation-rtl')
        case['origin']['path']='some-other-source.ts'
        with self.assertRaisesRegex(ValueError,'Locked148'):
            select_zenuml_cases(rows)

    def test_new_positive_from_any_origin_is_included(self):
        rows=corpus()
        new=copy.deepcopy(next(c for c in rows if c['id']=='gap-c-zen-hidden-await'))
        new['id']='future-positive';new['origin']['path']='new/source/anywhere.ts'
        selected,counts=select_zenuml_cases(rows+[new])
        self.assertIn('future-positive',{c['id'] for c in selected})
        self.assertEqual(counts['additionalDenominator'],39)
        self.assertEqual(counts['totalDenominator'],187)

    def test_positive_source_defect_retains_exact_check_eligibility(self):
        selected,_=select_zenuml_cases(corpus())
        defects=[c for c in selected if c['expect']=='upstream_defect']
        self.assertEqual({c['id'] for c in defects},{'C-zenuml-source-emoji-colon-override','C-zenuml-source-emoji-in-conditions'})

    def test_syntax_error_and_static_excluded_are_not_fake_positives(self):
        rows=corpus();new=copy.deepcopy(next(c for c in rows if c['id']=='gap-c-zen-hidden-await'))
        extras=[]
        for expect in ('syntax_error','error','excluded_by_static_scope'):
            extras.append({**new,'id':'negative-'+expect,'expect':expect})
        selected,counts=select_zenuml_cases(rows+extras)
        self.assertEqual(counts['totalDenominator'],186)
        self.assertFalse(any(c['id'].startswith('negative-') for c in selected))

    def test_duplicate_positive_id_rejected(self):
        rows=corpus();new=copy.deepcopy(next(c for c in rows if c['id']=='gap-c-zen-hidden-await'))
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            select_zenuml_cases(rows+[new])
