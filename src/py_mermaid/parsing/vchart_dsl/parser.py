"""Recursive descent for VChart DSL v1; only immutable syntax is produced."""
from __future__ import annotations

from collections import deque

from ...model.vchart_dsl import Node, MAX_DEPTH, MAX_VALUES, dsl_error
from .lexer import iter_tokens


class Parser:
    def __init__(self, text):
        self.text = text
        self.tokens = iter(iter_tokens(text))
        self.pending = deque()
        self.nodes = 0

    def peek(self, ahead=0):
        while len(self.pending) <= ahead:
            self.pending.append(next(self.tokens))
        return self.pending[ahead]

    def take(self, kind=None):
        token = self.peek()
        if kind is not None and token.kind != kind:
            self.fail(token, 'Expected ' + kind + ', got ' + token.kind)
        self.pending.popleft()
        return token

    def fail(self, token, message, code='VCHART_DSL_SYNTAX', path=()):
        raise dsl_error(self.text, token.start, token.end, message, code, path=path)

    def node(self, kind, value, children, start, end):
        self.nodes += 1
        if self.nodes > MAX_VALUES:
            raise dsl_error(self.text, start, end, 'VChart DSL AST value budget exceeded', 'VCHART_DSL_BUDGET')
        return Node(kind, value, tuple(children), start, end)

    def depth(self, depth):
        if depth > MAX_DEPTH:
            self.fail(self.peek(), 'VChart DSL nesting exceeds 128', 'VCHART_DSL_BUDGET')

    def newlines(self):
        while self.peek().kind == 'NL':
            self.take()

    def separators(self):
        while self.peek().kind in ('NL', ';'):
            self.take()

    def end_statement(self):
        token = self.peek()
        if token.kind not in ('NL', ';', '}', 'EOF'):
            self.fail(token, 'Expected newline or semicolon after statement')
        if token.kind in ('NL', ';'):
            self.take()

    def document(self):
        # RFC3.1: only BOM / leading whitespace may precede the header.
        # The value lexer intentionally ignores comments, so check the raw
        # boundary before letting it scan forward past a leading comment.
        start = 1 if isinstance(self.text, str) and self.text.startswith('\ufeff') else 0
        if isinstance(self.text, str):
            while start < len(self.text) and self.text[start] in ' \t\r\n':
                start += 1
            if self.text.startswith('%%', start):
                raise dsl_error(self.text, start, min(len(self.text), start + 2),
                                'VChart DSL header may only follow BOM and whitespace')
        self.newlines()
        head = self.take('IDENT')
        if head.value != 'vchart':
            self.fail(head, 'Expected vchart <type> header')
        chart_type = self.take('IDENT')
        header = self.node('header', chart_type.value, (), chart_type.start, chart_type.end)
        if self.peek().kind not in ('NL', 'EOF'):
            self.fail(self.peek(), 'VChart DSL header must end with newline or EOF')
        self.newlines()
        children = [header]
        self.separators()
        while self.peek().kind != 'EOF':
            children.append(self.statement(0, root=True))
            self.separators()
        return self.node('document', None, children, 0, len(self.text))

    def property_path(self):
        token = self.peek()
        if token.kind not in ('IDENT', 'STRING'):
            self.fail(token, 'Expected property path')
        self.take()
        start = token.start
        path = [token.value]
        while self.peek().kind in ('.', '['):
            punct = self.take()
            if punct.kind == '.':
                path.append(self.take('IDENT').value)
            else:
                key = self.take()
                if key.kind == 'STRING':
                    path.append(key.value)
                elif key.kind == 'NUMBER' and type(key.value) is int and key.value >= 0 and self.text[key.start:key.end].isdigit():
                    path.append(key.value)
                else:
                    self.fail(key, 'Array path index must be an unsigned JSON integer or string key')
                self.take(']')
            if len(path) > MAX_DEPTH:
                self.fail(self.peek(), 'VChart DSL path depth exceeds 128', 'VCHART_DSL_BUDGET', tuple(path[:MAX_DEPTH]))
        return tuple(path), start

    def block(self, depth):
        self.depth(depth)
        self.take('{')
        self.separators()
        children = []
        while self.peek().kind != '}':
            if self.peek().kind == 'EOF':
                self.fail(self.peek(), 'Unterminated configuration block')
            children.append(self.statement(depth, root=False))
            self.separators()
        end = self.take('}').end
        return children, end

    def statement(self, depth, root):
        self.depth(depth)
        token = self.peek()
        # Root words are special only in their sugar shape; assignments or
        # ordinary blocks named size/axis/series/let/resource stay properties.
        if root and token.kind == 'IDENT' and self.peek(1).kind not in ('=', '.', '[', '{'):
            word = token.value
            if word == 'size':
                self.take()
                values = []
                for _ in range(2):
                    number = self.take('NUMBER')
                    values.append(self.node('literal', number.value, (), number.start, number.end))
                self.end_statement()
                return self.node('size', None, values, token.start, values[-1].end)
            if word == 'let':
                self.take()
                name = self.take('IDENT')
                self.take('=')
                value = self.value(depth + 1)
                self.end_statement()
                return self.node('let', name.value, (value,), token.start, value.end)
            if word in ('axis', 'series'):
                self.take()
                name = self.take('IDENT')
                children, end = self.block(depth + 1)
                return self.node(word, name.value, children, token.start, end)
            if word == 'resource':
                self.take()
                namespace = self.take('IDENT')
                if namespace.value not in ('map', 'svg'):
                    self.fail(namespace, 'Resource namespace must be map or svg')
                name = self.take('STRING')
                self.take('=')
                value = self.value(depth + 1)
                self.end_statement()
                return self.node('resource', (namespace.value, name.value), (value,), token.start, value.end)
        path, start = self.property_path()
        if self.peek().kind == '{':
            children, end = self.block(depth + 1)
            return self.node('group', path, children, start, end)
        self.take('=')
        value = self.value(depth + 1)
        self.end_statement()
        return self.node('assignment', path, (value,), start, value.end)

    def value(self, depth):
        self.depth(depth)
        self.newlines()
        token = self.take()
        if token.kind in ('STRING', 'NUMBER'):
            return self.node('literal', token.value, (), token.start, token.end)
        if token.kind == 'IDENT':
            if token.value in ('true', 'false', 'null'):
                return self.node('literal', {'true': True, 'false': False, 'null': None}[token.value], (), token.start, token.end)
            if token.value == 'table':
                return self.table(token, depth)
            self.fail(token, 'Bare words are not values; use a double-quoted JSON string')
        if token.kind == '$':
            self.newlines()
            name = self.take('IDENT')
            return self.node('reference', name.value, (), token.start, name.end)
        if token.kind not in ('[', '{'):
            self.fail(token, 'Expected a JSON value, table or $reference')
        is_object = token.kind == '{'
        close = '}' if is_object else ']'
        self.newlines()
        children = []
        while self.peek().kind != close:
            if is_object:
                key = self.take()
                if key.kind not in ('STRING', 'IDENT'):
                    self.fail(key, 'Object member key must be an identifier or JSON string')
                self.newlines()
                self.take(':')
                value = self.value(depth + 1)
                children.append(self.node('member', key.value, (value,), key.start, value.end))
            else:
                children.append(self.value(depth + 1))
            self.newlines()
            if self.peek().kind == close:
                break
            self.take(',')
            self.newlines()
            if self.peek().kind == close:
                break
        end = self.take(close).end
        return self.node('object' if is_object else 'array', None, children, token.start, end)

    def table(self, token, depth):
        self.newlines()
        self.take('(')
        self.newlines()
        columns = []
        names = set()
        while True:
            column = self.take()
            if column.kind not in ('IDENT', 'STRING'):
                self.fail(column, 'Table requires a nonempty list of column names')
            if column.value in names:
                self.fail(column, 'Table column names must be unique', 'VCHART_DSL_TABLE_ARITY')
            columns.append(column.value)
            names.add(column.value)
            self.newlines()
            if self.peek().kind == ')':
                break
            self.take(',')
            self.newlines()
        self.take(')')
        self.newlines()
        self.take('{')
        self.separators()
        rows = []
        while self.peek().kind != '}':
            if self.peek().kind != '[':
                self.fail(self.peek(), 'Table row must be an array')
            row = self.value(depth + 1)
            if len(row.children) != len(columns):
                raise dsl_error(self.text, row.start, row.end, 'Table row length differs from its header', 'VCHART_DSL_TABLE_ARITY')
            rows.append(row)
            if self.peek().kind not in ('NL', ';', '}'):
                self.fail(self.peek(), 'Expected newline or semicolon after table row')
            self.separators()
        end = self.take('}').end
        return self.node('table', tuple(columns), rows, token.start, end)


def parse_dsl(text):
    """Parse one source document; no lowering, native objects or resource I/O."""
    return Parser(text).document()
