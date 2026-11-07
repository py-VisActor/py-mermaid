"""G01-C source-derived regressions; authored before baseline first execution.

No candidate helper supplies expectations. Sources are identified in
references/gap-audit-C.json and cases-gap-C.json. Import/discovery is inert.
"""
import unittest

from ._support import semantic, assert_png, assert_text_pixels


RAILWAYS = (
    ('railroad', 'railroad-beta\nr=terminal("Visible");'),
    ('railroadEbnf', 'railroad-ebnf-beta\nr="Visible";'),
    ('railroadAbnf', 'railroad-abnf-beta\nr="Visible";'),
    ('railroadPeg', 'railroad-peg-beta\nr<-"Visible";'),
)


class ZenSourceHiddenChannels(unittest.TestCase):
    def test_await_never_becomes_a_participant(self):
        # sequenceLexer.g4 AWAIT -> MODIFIER_CHANNEL, not parser participant.
        model = semantic('zenuml\nawait A.work()').model
        self.assertEqual([p.id for p in model.participants], ['_STARTER_', 'A'])
        self.assertEqual([(s.source, s.target, s.label) for s in model.statements],
                         [('_STARTER_', 'A', 'work()')])

    def test_assignment_modifiers_are_hidden_before_participant_collection(self):
        for prefix in ('const', 'readonly', 'static', 'const readonly static',
                       'const readonly static await'):
            with self.subTest(prefix=prefix):
                model = semantic('zenuml\n' + prefix + ' answer = A.work()').model
                self.assertEqual([p.id for p in model.participants], ['_STARTER_', 'A'])
                self.assertEqual(len(model.statements), 1)
                self.assertEqual(model.statements[0].assignment, 'answer')
                self.assertEqual(model.statements[0].assignee, 'answer')

    def test_entire_arbitrary_length_assignee_list_is_preserved(self):
        # assignee: ((ID|DIGIT_LEADING_NAME) (COMMA ...)*), no length ceiling.
        for count in (1, 2, 3, 4, 8, 17):
            names = ','.join('v' + str(i) for i in range(count))
            with self.subTest(count=count):
                model = semantic('zenuml\n' + names + ' = A.work()').model
                self.assertEqual(len(model.statements), 1)
                call = model.statements[0]
                self.assertEqual((call.kind, call.target, call.label), ('sync', 'A', 'work()'))
                self.assertEqual(call.assignment, names)
                self.assertEqual(call.assignee, names)
                self.assertEqual([p.id for p in model.participants], ['_STARTER_', 'A'])

    def test_typed_assignee_list_preserves_type_separately(self):
        for count in (1, 2, 3, 8):
            names = ','.join('v' + str(i) for i in range(count))
            with self.subTest(count=count):
                model = semantic('zenuml\nResult ' + names + ' = A.work()').model
                call = model.statements[0]
                # Source prog/head priority collects Result before block.
                # Original gap-c-zen-typed-assignee geometry explicitly contains
                # _STARTER_,Result,A. The earlier type-at-head expectation was
                # wrong, despite type? being valid inside a block assignment.
                self.assertEqual([p.id for p in model.participants], ['_STARTER_', 'Result', 'A'])
                self.assertEqual(call.assignment, names)
                self.assertEqual(call.assignee, names)

    def test_body_typed_assignment_keeps_quoted_and_multiline_type(self):
        for typename, spelling in (('Result', 'Result'), ('Result Type', '"Result Type"')):
            for separator in (' ', '\n'):
                with self.subTest(typename=typename, separator=separator):
                    model = semantic('zenuml\nA.outer() { ' + spelling + separator + 'a,b,c = B.work() }').model
                    call = model.statements[0].children[0]
                    self.assertEqual([p.id for p in model.participants], ['_STARTER_', 'A', 'B'])
                    self.assertEqual(call.assignment, 'a,b,c:' + typename)
                    self.assertEqual(call.assignee, 'a,b,c')

    def test_explicit_quoted_creation_participant_precedes_later_assignment(self):
        # Literal fixed e2e/data/compare-cases.js CASES.creation-rtl.
        model = semantic('zenuml\n"b:B"\na1 = A.method() {\n// abcde\nb = new B()\n}').model
        self.assertEqual([p.id for p in model.participants], ['_STARTER_', 'b:B', 'A'])
        self.assertEqual(model.statements[0].assignment, 'a1')
        self.assertEqual(model.statements[0].children[0].target, 'b:B')

    def test_digit_leading_unicode_names_are_one_source_token(self):
        for name in ('1\u670d\u52a1', '2\u03b1', '3\u03b1\u03b2_4'):
            with self.subTest(name=name):
                model = semantic('zenuml\n' + name + ' -> B: work').model
                self.assertEqual([p.id for p in model.participants], [name, 'B'])
                call = model.statements[0]
                self.assertEqual((call.source, call.target, call.label), (name, 'B', 'work'))

    def test_hidden_cr_between_qualified_call_tokens_is_whitespace(self):
        for body in ('A.\nwork()', 'A.\r\nwork()', 'A\n.work()'):
            with self.subTest(body=body):
                model = semantic('zenuml\n' + body).model
                self.assertEqual([p.id for p in model.participants], ['_STARTER_', 'A'])
                self.assertEqual([(s.kind, s.target, s.label) for s in model.statements],
                                 [('sync', 'A', 'work()')])


class GapNativeSourcePaint(unittest.IsolatedAsyncioTestCase):
    async def test_multi_assignee_actual_return_text_and_glyph_ink(self):
        from py_mermaid import arender
        for names in ('a,b', 'a,b,c,d,e'):
            with self.subTest(names=names):
                result = await arender('zenuml\n' + names + ' = A.work()', backend='cpu')
                image = assert_png(self, result)
                return_text = [e for e in result.trace if e.kind == 'return-label' and e.text == names]
                self.assertEqual(len(return_text), 1)
                assert_text_pixels(self, image, return_text[0])

    async def _railway(self, source, config):
        from py_mermaid import arender
        result = await arender(source, backend='cpu', config=config)
        image = assert_png(self, result)
        shape = next(e for e in result.trace if e.kind == 'railroad-terminal')
        label = next(e for e in result.trace if e.text == 'Visible')
        assert_text_pixels(self, image, label)
        return image, shape, label

    def _fill_ink(self, image, event, rgb):
        b = event.box
        crop = image.crop((int(b.x + 2), int(b.y + 2), int(b.x + b.width - 2),
                           int(b.y + b.height - 2)))
        # Independent literal color; white/no-op or default-yellow substitute fails.
        self.assertGreater(sum(all(abs(c - want) <= 2 for c, want in zip(pixel, rgb))
                               for pixel in crop.getdata()), 12)

    async def test_invalid_terminal_fill_uses_theme_derived_color_in_all_dialects(self):
        for kind, source in RAILWAYS:
            for invalid in (False, 42, 'url(bad)', '#12'):
                with self.subTest(kind=kind, invalid=invalid):
                    image, shape, _ = await self._railway(source, {
                        'themeVariables': {'secondBkg': '#112233'},
                        'railroad': {'terminalFill': invalid},
                    })
                    self.assertEqual(shape.fill, '#112233')
                    self._fill_ink(image, shape, (17, 34, 51))

    async def test_valid_override_wins_theme_in_all_dialects(self):
        for kind, source in RAILWAYS:
            with self.subTest(kind=kind):
                image, shape, _ = await self._railway(source, {
                    'themeVariables': {'secondBkg': '#112233'},
                    'railroad': {'terminalFill': '#aabbcc', 'padding': 0},
                })
                self.assertEqual(shape.fill, '#aabbcc')
                self._fill_ink(image, shape, (170, 187, 204))

    async def test_invalid_font_size_uses_derived_size_not_literal_default(self):
        for kind, source in RAILWAYS:
            for invalid in (-1, 'invalid', False):
                with self.subTest(kind=kind, invalid=invalid):
                    _, _, label = await self._railway(source, {
                        'themeVariables': {'fontSize': '24px'},
                        'railroad': {'fontSize': invalid},
                    })
                    self.assertEqual(label.font_size, 24)

    async def test_zero_numeric_override_is_valid_source_boundary(self):
        for kind, source in RAILWAYS:
            with self.subTest(kind=kind):
                _, shape, _ = await self._railway(source, {
                    'themeVariables': {'secondBkg': '#112233'},
                    'railroad': {'padding': 0, 'strokeWidth': 0, 'markerRadius': 0},
                })
                self.assertEqual(shape.stroke_width, 0)

    async def test_invalid_font_family_uses_theme_family(self):
        for kind, source in RAILWAYS:
            with self.subTest(kind=kind):
                _, _, label = await self._railway(source, {
                    'themeVariables': {'fontFamily': 'Arial'},
                    'railroad': {'fontFamily': 'bad;family'},
                })
                self.assertEqual(label.font_family, 'Arial')

    async def test_root_generic_sequence_font_size_and_weight_reach_all_roles(self):
        from py_mermaid import arender
        result = await arender('sequenceDiagram\nparticipant A\nNote over A: NoteInk\nA->>B: MessageInk',
                               backend='cpu', config={'fontSize': 32, 'fontWeight': 700})
        image = assert_png(self, result)
        for label in ('A', 'NoteInk', 'MessageInk'):
            with self.subTest(label=label):
                events = [e for e in result.trace if e.text == label]
                self.assertTrue(events)
                for event in events:
                    self.assertEqual(event.font_size, 32)
                    self.assertIn(str(event.font_weight), ('700', 'bold'))
                    assert_text_pixels(self, image, event)

    async def test_sequence_number_font_length_source_branches(self):
        from py_mermaid import arender
        for number, size in ((1, 12), (123, 12), (1234, 9), (12345, 9), (123456, 7)):
            with self.subTest(number=number):
                result = await arender('sequenceDiagram\nautonumber ' + str(number) + '\nA->>B: Message', backend='cpu')
                image = assert_png(self, result)
                event = next(e for e in result.trace if e.kind == 'sequence-number')
                self.assertEqual(event.text, str(number))
                self.assertEqual(event.font_size, size)
                assert_text_pixels(self, image, event)

    async def test_destroy_receiver_arrow_stops_before_visible_footer(self):
        from py_mermaid import arender
        from py_skia_canvas import Path2D
        result = await arender('sequenceDiagram\nparticipant A\nparticipant B\ndestroy B\nA->>B: Goodbye',
                               backend='cpu', config={'sequence': {'mirrorActors': True}})
        image = assert_png(self, result)
        footer = next(e for e in result.trace if e.kind == 'actor-footer' and e.semantic_id == 'B')
        line = next(e for e in result.trace if e.kind == 'message' and e.path)
        # DrawEvent.box is conservative paint/miter/shadow allocation, not a
        # geometric endpoint. Decode the actual paths sent to native Canvas.
        endpoint = Path2D(line.path).bounds['right']
        footer_left = Path2D(footer.path).bounds['left']
        self.assertAlmostEqual(footer_left - endpoint, 3, delta=.01)
        crop = image.crop((int(endpoint) - 2, int(Path2D(line.path).bounds['top']) - 2,
                           int(endpoint) + 2, int(Path2D(line.path).bounds['top']) + 3))
        self.assertGreater(sum(min(pixel) < 180 for pixel in crop.getdata()), 1)
        assert_text_pixels(self, image, next(e for e in result.trace if e.text == 'Goodbye'))
