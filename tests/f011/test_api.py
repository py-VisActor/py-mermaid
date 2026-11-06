"""Public F01.1 contract tests, independent of implementation internals.

Source: docs/F01_1_EXECUTION_PLAN.md and docs/F01_1_INTERFACES.md;
runtime restrictions supplement the fixed Mermaid language source tests.
"""
import asyncio
from dataclasses import FrozenInstanceError
import subprocess
import sys
import unittest

from py_mermaid import MermaidError, arender, parse, render


class PublicAPI(unittest.TestCase):
    def test_parse_returns_immutable_values(self):
        diagram = parse('graph LR\nA[Hello] --> B[World]')
        self.assertEqual(diagram.direction, 'LR')
        with self.assertRaises(FrozenInstanceError):
            diagram.direction = 'TD'

    def test_import_allocates_no_native(self):
        code = "import sys, py_mermaid; assert 'py_skia_canvas' not in sys.modules; assert 'pyelk' not in sys.modules"
        completed = subprocess.run([sys.executable, '-c', code], capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_render_in_event_loop_has_actionable_error(self):
        async def inside():
            with self.assertRaises(MermaidError) as error:
                render('flowchart TD\nA')
            self.assertEqual(error.exception.code, 'ACTIVE_EVENT_LOOP')
        asyncio.run(inside())

    def test_reject_unsupported_export_and_backend(self):
        for kwargs, code in [({'format':'tiff'}, 'UNSUPPORTED_FORMAT'),
                             ({'backend':'silent-fallback'}, 'INVALID_BACKEND')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(MermaidError) as error:
                render('flowchart TD\nA', **kwargs)
            self.assertEqual(error.exception.code, code)

    def test_async_real_render(self):
        result = asyncio.run(arender('flowchart TD\nA[Async] --> B[Done]', backend='cpu'))
        self.assertEqual(result.mime, 'image/png')
        self.assertGreater(result.width, 1)
        self.assertEqual(len(result.diagram.edges), 1)
        self.assertTrue(result.data.startswith(b'\x89PNG\r\n\x1a\n'))


if __name__ == '__main__':
    unittest.main()
