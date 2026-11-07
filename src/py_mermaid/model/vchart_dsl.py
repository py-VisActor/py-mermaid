"""Immutable VChart DSL syntax and lowering contracts (code-point spans)."""
from __future__ import annotations

from dataclasses import dataclass
from .flowchart import MermaidError, SourcePosition, SourceSpan

MAX_BYTES = 8 * 1024 * 1024
MAX_DEPTH = 128
MAX_VALUES = 1_000_000


@dataclass(frozen=True)
class Node:
    kind: str
    value: object = None
    children: tuple[Node, ...] = ()
    start: int = 0
    end: int = 0


@dataclass(frozen=True)
class SpecSpan:
    path: tuple[str | int, ...]
    start: int
    end: int
    namespace: str = 'spec'
    declaration_start: int | None = None
    declaration_end: int | None = None


@dataclass(frozen=True)
class DslDiagnostic:
    code: str
    message: str
    path: tuple[str | int, ...] = ()
    start: int = 0
    end: int = 0


@dataclass(frozen=True)
class LoweredVChart:
    spec_json: str
    maps_json: str
    svgs: tuple[tuple[str, str], ...]
    source_map: tuple[SpecSpan, ...]
    diagnostics: tuple[DslDiagnostic, ...]


def dsl_error(text, start, end, message, code='VCHART_DSL_SYNTAX', path=(), related=()):
    """Build an error in original CP / UTF-16 coordinates, never generated JSON."""
    def position(index):
        index = max(0, min(len(text), index))
        prefix = text[:index]
        line_start = max(prefix.rfind('\r'), prefix.rfind('\n')) + 1
        return SourcePosition(index, len(prefix.encode('utf-16-le', 'surrogatepass')) // 2,
                              prefix.replace('\r\n', '\n').replace('\r', '\n').count('\n') + 1,
                              len(prefix[line_start:].encode('utf-16-le', 'surrogatepass')) // 2)
    error = MermaidError(message, code=code, span=SourceSpan(position(start), position(end)))
    error.spec_path = tuple(path)
    error.related_spans = tuple(related)
    return error
