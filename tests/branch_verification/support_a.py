"""Bindings for handwritten source literals; no product calls at discovery."""
from dataclasses import fields, is_dataclass
from pathlib import Path
import json


def cases():
    return json.loads(Path(__file__).with_name('cases-A.json').read_text(encoding='utf-8'))['cases']


def plain(value):
    if is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def select(value, path):
    for key in path:
        value = value[key]
    return value


def parse_case(case):
    from py_mermaid.runtime.registry import parse_diagram
    return parse_diagram(case['source'], config=case['config'])


async def picture(case):
    from py_mermaid.api import arender
    return await arender(case['source'], config=case['config'], backend='cpu', format='png')


def paint_signature(result):
    # IDs can include per-render host names; source no-op comparison concerns
    # actual geometry, paths, text and paint, not those host identifiers.
    return [plain((e.kind, e.text, e.box, e.path, e.fill, e.stroke, e.opacity)) for e in result.trace]
