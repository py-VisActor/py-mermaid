"""Streaming, budgeted JSON-value lexer; newlines remain syntax tokens."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re

from ...model.vchart_dsl import MAX_BYTES, MAX_VALUES, dsl_error

IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
MAX_TOKENS = MAX_VALUES * 4 + 32


@dataclass(frozen=True)
class Token:
    kind: str
    value: object
    start: int
    end: int


def iter_tokens(text):
    """Yield source tokens without materializing a second full token tree."""
    if not isinstance(text, str):
        from ...model.flowchart import MermaidError
        raise MermaidError('VChart DSL source must be a string', code='INVALID_INPUT')
    if len(text) > MAX_BYTES or len(text.encode('utf-8', 'surrogatepass')) > MAX_BYTES:
        raise dsl_error(text, 0, len(text), 'VChart DSL document exceeds 8 MiB', 'VCHART_DSL_BUDGET')
    i = 1 if text.startswith('\ufeff') else 0
    count = 0
    while i < len(text):
        char = text[i]
        if char in ' \t':
            i += 1
            continue
        if text.startswith('%%', i):
            if text.startswith('%%{', i):
                raise dsl_error(text, i, i + 3, 'Mermaid init directives are not part of VChart DSL', 'VCHART_DSL_DIRECTIVE')
            while i < len(text) and text[i] not in '\r\n':
                i += 1
            continue
        start = i
        if char in '\r\n':
            i += 2 if text.startswith('\r\n', i) else 1
            token = Token('NL', '\n', start, i)
        elif char == '"':
            i += 1
            while i < len(text):
                if text[i] == '\\':
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                elif ord(text[i]) < 32:
                    raise dsl_error(text, i, i + 1, 'JSON string contains an unescaped control character')
                else:
                    i += 1
            else:
                raise dsl_error(text, start, len(text), 'Unterminated JSON string')
            if i > len(text) or text[i - 1] != '"':
                raise dsl_error(text, start, len(text), 'Unterminated JSON string')
            try:
                value = json.loads(text[start:i])
            except json.JSONDecodeError as exc:
                raise dsl_error(text, start + exc.pos, min(i, start + exc.pos + 1), 'Invalid JSON string escape: ' + exc.msg) from None
            token = Token('STRING', value, start, i)
        elif char.isascii() and (char.isdigit() or char == '-'):
            match = NUMBER.match(text, i)
            if match is None:
                raise dsl_error(text, i, i + 1, 'Expected a finite JSON number')
            i = match.end()
            # A number cannot be split into 01, 1e, 1_000 or 1.2.3 tokens.
            if i < len(text) and (text[i].isascii() and (text[i].isalnum() or text[i] in '_.+-')):
                raise dsl_error(text, start, i + 1, 'Invalid JSON number')
            try:
                value = json.loads(match[0])
            except (ValueError, OverflowError):
                raise dsl_error(text, start, i, 'JSON numeric literal exceeds the integer budget', 'VCHART_DSL_BUDGET') from None
            if isinstance(value, float) and not math.isfinite(value):
                raise dsl_error(text, start, i, 'VChart DSL numbers must be finite')
            token = Token('NUMBER', value, start, i)
        elif char.isascii() and (char.isalpha() or char == '_'):
            match = IDENTIFIER.match(text, i)
            i = match.end()
            token = Token('IDENT', match[0], start, i)
        elif char in '{}[]():,;=.$':
            i += 1
            token = Token(char, char, start, i)
        else:
            raise dsl_error(text, i, i + 1, 'Unexpected VChart DSL character ' + repr(char))
        count += 1
        if count > MAX_TOKENS:
            raise dsl_error(text, start, i, 'VChart DSL token budget exceeded', 'VCHART_DSL_BUDGET')
        yield token
    yield Token('EOF', None, len(text), len(text))


def tokenize(text):
    """Return immutable tokens for source inspection; parser itself streams."""
    return tuple(iter_tokens(text))
