"""Independent fixed-source branch assertions. Execute only in coordinated P3.

The JSON contains literal source expectations, never candidate-generated data.
Original-only anomalies/active-consumer probes are handled by probe_a.py and
remain unresolved rather than becoming native acceptance-only unit tests.
"""
import unittest
from .support_a import cases, plain, select, parse_case, picture, paint_signature


class ASourceLiteralTests(unittest.TestCase):
    def test_cynefin_unterminated_string_is_rejected(self):
        from py_mermaid.model.flowchart import MermaidError
        case = next(c for c in cases() if c['id'] == 'BV-A-cynefin-unclosed')
        with self.assertRaises(MermaidError) as caught:
            parse_case(case)
        self.assertEqual(caught.exception.code, 'SYNTAX_ERROR')


def install_literals():
    for case in cases():
        checks = case['branchExpected']['nativeChecks']
        migrated_rejection = case.get('sourceExpectationMigration') and case['expect'] == 'syntax_error'
        if not checks and not migrated_rejection:
            continue
        def test(self, case=case, checks=checks):
            if case.get('sourceExpectationMigration') and case['expect'] == 'syntax_error':
                from py_mermaid.model.flowchart import MermaidError
                with self.assertRaises(MermaidError) as caught:
                    parse_case(case)
                self.assertIn(caught.exception.code,case['expectedErrorCodes'])
                return
            model = plain(parse_case(case).model)
            for check in checks:
                with self.subTest(path=check['path']):
                    self.assertEqual(select(model, check['path']), check['equals'])
        name = 'test_' + case['id'][5:].replace('-', '_')
        test.__name__ = name
        test.__doc__ = case['origin']['path'] + ': ' + case['branchExpected']['description']
        setattr(ASourceLiteralTests, name, test)


install_literals()


class ASourcePaintTests(unittest.IsolatedAsyncioTestCase):
    async def test_state_no_action_productions_do_not_change_paint(self):
        lookup = {c['id']: c for c in cases()}
        base = await picture(lookup['BV-A-state-base'])
        decorated = await picture(lookup['BV-A-state-noops'])
        self.assertEqual(paint_signature(decorated), paint_signature(base))
        self.assertEqual((decorated.width, decorated.height), (base.width, base.height))

    async def test_c4_rows_config_is_not_db_update_command(self):
        lookup = {c['id']: c for c in cases()}
        base = await picture(lookup['BV-A-c4-rows-base'])
        ignored = await picture(lookup['BV-A-c4-rows-config'])
        command = await picture(lookup['BV-A-c4-rows-command'])
        self.assertEqual(paint_signature(ignored), paint_signature(base))
        self.assertNotEqual(paint_signature(command), paint_signature(base))

    async def test_c4_legend_fields_do_not_invent_legend_text(self):
        case = next(c for c in cases() if c['id'] == 'BV-A-c4-shadow-legend')
        result = await picture(case)
        text = ''.join(e.text or '' for e in result.trace if e.opacity > 0)
        self.assertIn('Alpha', text)
        self.assertNotIn('LEGEND', text)

    async def test_class_box_displays_first_annotation(self):
        case = next(c for c in cases() if c['id'] == 'BV-A-class-first-annotation')
        result = await picture(case)
        text = ''.join(e.text or '' for e in result.trace if e.opacity > 0)
        self.assertIn('interface', text)
        self.assertNotIn('service', text)

    async def test_mindmap_layout_selection_and_tree_constraints(self):
        # mindmapDb.getData only tests presence of user root layout. A scoped
        # layout value alone does not change the actual default algorithm.
        expected = {'default': 'native-cose-bilkent', 'scoped-layout': 'native-cose-bilkent',
                    'explicit-tidy': 'native-tidy-tree'}
        for suffix, engine in expected.items():
            case = next(c for c in cases() if c['id'] == 'BV-A-mindmap-' + suffix)
            with self.subTest(layout=suffix):
                result = await picture(case)
                self.assertEqual(result.layout.engine, engine)
                boxes = list(result.layout.nodes.values())
                self.assertEqual(len(boxes), 4)
                for i, a in enumerate(boxes):
                    self.assertGreater(a.width, 0)
                    self.assertGreater(a.height, 0)
                    for b in boxes[i + 1:]:
                        self.assertTrue(a.x + a.width <= b.x + .5 or b.x + b.width <= a.x + .5
                                        or a.y + a.height <= b.y + .5 or b.y + b.height <= a.y + .5)
                self.assertEqual(len(result.layout.edges), 3)


class ASourceShapeTests(unittest.TestCase):
    def test_c4_shape_keyword_priority_and_fallback(self):
        from py_mermaid.diagrams.modeling.c4 import _shape
        expected = {'shape-priority': 'cylinder', 'sprite-fallback': 'person',
                    'tags-first-known': 'h-cyl', 'type-fallback': 'round'}
        for suffix, shape in expected.items():
            case = next(c for c in cases() if c['id'] == 'BV-A-c4-' + suffix)
            with self.subTest(branch=suffix):
                model = parse_case(case).model
                self.assertEqual(model.elements[0].id, 'a')
                self.assertEqual(model.elements[0].label, 'Alpha')
                self.assertEqual(_shape(model.elements[0]), shape)
