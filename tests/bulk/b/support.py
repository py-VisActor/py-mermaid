"""Test bindings only; expectations live in source-backed test cases."""
import unittest
from py_mermaid import parse
from py_mermaid.model.flowchart import MermaidError


def model(source, config=None):
    return parse(source, config=config).model


class SourceCase(unittest.TestCase):
    def reject(self, source, code='SYNTAX_ERROR', config=None):
        with self.assertRaises(MermaidError) as caught:
            parse(source, config=config)
        self.assertEqual(caught.exception.code, code)
        self.assertTrue(str(caught.exception))
        self.assertIsNotNone(caught.exception.span)
        self.assertGreaterEqual(caught.exception.span.start.line,1)
        self.assertGreaterEqual(caught.exception.span.start.index,0)
        self.assertLessEqual(caught.exception.span.start.index,len(source))
        return caught.exception


async def scene(source, config=None):
    from py_mermaid.runtime.registry import provider_for
    from py_mermaid.rendering.skia.scene import Painter
    diagram = parse(source, config=config)
    painter = Painter(diagram, backend='cpu')
    return await provider_for(diagram.kind).build(diagram, painter)


def command(scene_, identifier):
    matches = [c for c in scene_.commands if c.semantic_id == identifier]
    if len(matches) != 1:
        raise AssertionError(f'{identifier}: expected one paint command, got {len(matches)}')
    return matches[0]


def texts(scene_):
    return tuple(c.values[0].text for c in scene_.commands if c.kind == 'text')


def shape_box(command_):
    """Decode a recorded path; no candidate layout helper supplies expectations."""
    from py_mermaid.geometry.path_geometry import path_bounds
    return path_bounds(command_.values[0])
