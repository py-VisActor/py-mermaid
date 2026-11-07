"""Pure source-position-preserving static flowchart parser.

Locked flow.jison productions and FlowDB actions define classic shapes, plain
edge labels, rich label bodies and subgraph reduction. Preprocessing keeps an
explicit boundary map to the original source. No browser or native objects are
used. See references/f014-parser-sources.json for the source correspondence.
"""
from __future__ import annotations

from collections.abc import Mapping
from bisect import bisect_right
from dataclasses import dataclass, field, replace
import re
import math

from py_mermaid.config import resolve_config
from py_mermaid.model.flowchart import (
    Flowchart, FlowConfig, FlowEdge, FlowGroup, FlowNode, MermaidError,
    SourcePosition, SourceSpan, SourceDocument, ClassDefinition,
)
from py_mermaid.config.values import freeze_value, thaw_value
from py_mermaid.config.elk import CURVES
from py_mermaid.geometry.shape_registry import canonical_shape, METADATA_SHAPES
from .syntax import match_direct, destruct_link, ParsedLink, DIRECT, START
from .lexical import identifier_character, identifier_token, source_space, NODE_STRING, BLOCKED, NUM, ID_LITERAL

_HEADER = re.compile(r"(flowchart-elk|flowchart|graph|swimlane-beta)(?=[\s;]|$)")
_RESERVED = frozenset({"subgraph", "end", "style", "classDef", "class", "linkStyle"})
_SHAPES = (("(((", ")))", "doublecircle"), ("[[", "]]", "subroutine"),
           ("([", "])", "stadium"), ("[(", ")]", "cylinder"),
           ("((", "))", "circle"), ("(-", "-)", "ellipse"),
           ("{{", "}}", "hexagon"), ("[", "]", "square"),
           ("(", ")", "round"), ("{", "}", "diamond"), (">", "]", "odd"))


def _truthy(value):
    return (isinstance(value, (Mapping, list, tuple)) or bool(value)) and not (
        isinstance(value, float) and math.isnan(value))


@dataclass
class _Block:
    start: int
    identifier: str | None
    label: str
    members: list[str] = field(default_factory=list)
    direction: str | None = None
    label_kind: str = "text"
    raw_label: str | None = None
    label_span: SourceSpan | None = None


class _Parser:
    def __init__(self, text: str, config: FlowConfig, document: SourceDocument | None = None):
        self.text, self.config, self.cursor = text, config, 0
        self.document = document
        self.raw = document.raw if document is not None else text
        self.source_map = document.processed_to_raw if document is not None else tuple(range(len(text) + 1))
        self.last_kind, self.last_raw, self.last_span = "text", None, None
        self.acc_title, self.acc_description = "", ""
        self.nodes: dict[str, FlowNode] = {}
        self.edges: list[FlowEdge] = []
        self.groups: dict[str, FlowGroup] = {}
        self.blocks: list[_Block] = []
        self.group_count = 0
        self.classes: dict[str, ClassDefinition] = {}
        self.default_edge_styles: tuple[str, ...] = ()
        self.default_edge_curve: str | None = None
        self.direction = "TD"
        self.diagram_type = "flowchart-v2"
        self.utf16 = [0]
        self.lines = [0]
        for index, char in enumerate(self.raw):
            self.utf16.append(self.utf16[-1] + (2 if ord(char) > 0xFFFF else 1))
            if char == "\n" or (char == "\r" and self.raw[index:index + 2] != "\r\n"):
                self.lines.append(index + 1)

    def position(self, index: int) -> SourcePosition:
        index = self.source_map[index]
        row = bisect_right(self.lines, index) - 1
        return SourcePosition(index, self.utf16[index], row + 1,
                              self.utf16[index] - self.utf16[self.lines[row]])

    def span(self, start: int, end: int) -> SourceSpan:
        return SourceSpan(self.position(start), self.position(end))

    def error(self, message: str, code: str = "INVALID_SYNTAX", *, start: int | None = None,
              end: int | None = None) -> None:
        start = self.cursor if start is None else start
        end = min(len(self.text), start + 1) if end is None else end
        raise MermaidError(message, code=code, span=self.span(start, end))

    def horizontal(self) -> None:
        while self.cursor < len(self.text) and source_space(self.text[self.cursor], horizontal=True):
            self.cursor += 1

    def keyword(self, word: str) -> bool:
        end = self.cursor + len(word)
        return (self.text.startswith(word, self.cursor)
                and (end == len(self.text) or self.text[end].isspace() or self.text[end] == ";"))

    def comment(self) -> bool:
        if not self.text.startswith("%%", self.cursor):
            return False
        line_start = max(self.text.rfind("\n", 0, self.cursor),
                         self.text.rfind("\r", 0, self.cursor)) + 1
        if self.text[line_start:self.cursor].strip():
            self.error("%% comments must occupy a separate line")
        if self.text.startswith("%%{", self.cursor):
            self.error("Configuration directives are outside this slice; pass config explicitly",
                       "UNSUPPORTED_SYNTAX")
        while self.cursor < len(self.text) and self.text[self.cursor] not in "\r\n":
            self.cursor += 1
        return True

    def separators(self) -> None:
        while self.cursor < len(self.text):
            if source_space(self.text[self.cursor]) or self.text[self.cursor] == ";":
                self.cursor += 1
            elif not self.comment():
                break

    def statement_end(self) -> None:
        self.horizontal()
        self.comment()
        if self.cursor < len(self.text) and self.text[self.cursor] not in ";\r\n":
            self.error("Unexpected trailing syntax outside the supported flowchart slice",
                       "UNSUPPORTED_SYNTAX")
        self.separators()

    def link_whitespace(self) -> None:
        # Jison's LINK lexeme consumes surrounding whitespace; whole-line
        # comments have already disappeared in upstream preprocessing.
        while self.cursor < len(self.text):
            if source_space(self.text[self.cursor]):
                self.cursor += 1
            elif not self.comment():
                break

    def plain(self, content: str, start: int, end: int) -> str:
        from py_mermaid.rendering.labels.math import protect_math
        content,formulas=protect_math(content)
        content = re.sub(r"#(\w+);", lambda match: "&#" + match[1] + ";" if match[1].isdigit()
                         else "&" + match[1] + ";", content)
        content = content.strip().replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n")
        content="\n".join(re.sub(r"[ \t\v\f]+", " ", line).strip()
                           for line in content.split("\n"))
        for token,formula in formulas.items():content=content.replace(token,'$$'+formula.tex+'$$')
        return content

    def label(self, content, start, end, *, quoted=False):
        if quoted and content.startswith("`") and (len(content) < 2 or not content.endswith("`")):
            self.error("Expected closing backtick for Markdown label", start=start, end=end)
        kind = "markdown" if quoted and content.startswith("`") and content.endswith("`") else "text"
        raw = content[1:-1] if kind == "markdown" else content
        body_start, body_end = (start + 1, end - 1) if kind == "markdown" else (start, end)
        self.last_kind, self.last_raw, self.last_span = kind, raw, self.span(body_start, body_end)
        from py_mermaid.rendering.labels.sanitize import sanitize_markup
        from py_mermaid.rendering.labels.math import protect_math
        protected,formulas=protect_math(raw.strip())
        sanitized = sanitize_markup(protected, self.config)
        if kind == "markdown":
            for token,formula in formulas.items():sanitized=sanitized.replace(token,'$$'+formula.tex+'$$')
            return sanitized, self.last_span
        content=self.plain(sanitized, start, end)
        for token,formula in formulas.items():content=content.replace(token,'$$'+formula.tex+'$$')
        return content,self.last_span

    def quoted(self) -> tuple[str, SourceSpan]:
        quote = self.cursor
        self.cursor += 1
        start = self.cursor
        while self.cursor < len(self.text) and self.text[self.cursor] != '"':
            self.cursor += 1
        if self.cursor == len(self.text):
            self.error("Unterminated quoted label", start=quote)
        end = self.cursor
        self.cursor += 1
        return self.label(self.text[start:end], start, end, quoted=True)

    def delimited_text(self, closing: str, *, unquoted_empty: bool = False) -> tuple[str, SourceSpan]:
        start = self.cursor
        if self.cursor < len(self.text) and self.text[self.cursor] == '"':
            label, span = self.quoted()
            self.horizontal()
        else:
            while self.cursor < len(self.text) and not self.text.startswith(closing, self.cursor):
                if self.text[self.cursor] in '[](){}"|':
                    self.error("Delimiter in an ordinary label must be quoted")
                self.cursor += 1
            end = self.cursor
            content = self.text[start:end]
            if not content.strip() and not unquoted_empty:
                self.error("Expected nonempty ordinary label", start=start, end=end)
            label, span = self.label(content, start, end)
        if not self.text.startswith(closing, self.cursor):
            self.error(f"Expected closing {closing!r} for label")
        self.cursor += len(closing)
        return label, span

    def identifier(self) -> str:
        start = self.cursor
        while self.cursor < len(self.text):
            char = self.text[self.cursor]
            if self.text.startswith(':::', self.cursor) or match_direct(self.text, self.cursor):
                break
            if any(pattern.match(self.text, self.cursor) for pattern in START):
                break
            length = identifier_token(self.text, self.cursor)
            if not length:
                break
            self.cursor += length
        if self.cursor == start:
            self.error("Expected a node identifier")
        identifier = self.text[start:self.cursor]
        if identifier in _RESERVED:
            self.error(f"Unexpected reserved statement {identifier!r}", "UNSUPPORTED_SYNTAX", start=start)
        return identifier

    def node(self) -> str:
        self.horizontal()
        start = self.cursor
        identifier = self.identifier()
        identifier_end = self.cursor
        self.horizontal()
        explicit = False
        props = {}
        label, shape = identifier, "square"
        if self.text.startswith('[|', self.cursor):
            explicit, shape = True, 'square'
            self.cursor += 2
            property_start = self.cursor
            closing = self.text.find('|', self.cursor)
            if closing < 0:
                self.error('Expected property delimiter |', start=property_start)
            value = self.text[self.cursor:closing]
            if ':' not in value:
                self.error('Expected field:value for vertex property', start=property_start)
            key, value = value.split(':', 1)
            if any(not NODE_STRING.fullmatch(item) or NUM.match(item) or BLOCKED.match(item)
                   or ID_LITERAL.match(item) or item.startswith(('#', '*', '&', '"')) for item in (key, value)):
                self.error('Expected nonempty vertex property', start=property_start)
            props[key] = value
            self.cursor = closing + 1
            label, _ = self.delimited_text(']')
        elif self.text.startswith(("[/", "[\\"), self.cursor):
            explicit = True
            opening = self.text[self.cursor:self.cursor + 2]
            self.cursor += 2
            content_start = self.cursor
            if self.cursor < len(self.text) and self.text[self.cursor] == '"':
                label, _ = self.quoted()
                self.horizontal()
            else:
                while self.cursor < len(self.text) and not self.text.startswith(("/]", "\\]"), self.cursor):
                    if self.text[self.cursor] in '[](){}"':
                        self.error("Delimiter in slanted node label must be quoted")
                    self.cursor += 1
                if not self.text[content_start:self.cursor].strip():
                    self.error("Expected nonempty ordinary label", start=content_start)
                label, _ = self.label(self.text[content_start:self.cursor], content_start, self.cursor)
            closing = self.text[self.cursor:self.cursor + 2]
            if closing not in ("/]", "\\]"):
                self.error("Expected /] or \\] to close slanted node")
            shape = {("[/", "\\]"): "trapezoid", ("[\\", "/]"): "inv_trapezoid",
                     ("[/", "/]"): "lean_right", ("[\\", "\\]"): "lean_left"}[(opening, closing)]
            self.cursor += 2
        else:
            for opening, closing, candidate in _SHAPES:
                if self.text.startswith(opening, self.cursor):
                    explicit, shape = True, candidate
                    self.cursor += len(opening)
                    label, _ = self.delimited_text(closing)
                    break
        old = self.nodes.get(identifier)
        existing_edge = next((edge for edge in self.edges if edge.source_id == identifier), None)
        if existing_edge is None and (old is None or explicit):
            previous_metadata = thaw_value(old.metadata) if old and old.metadata else {}
            if _truthy(previous_metadata.get('img')):
                shape = 'imageSquare'
            elif _truthy(previous_metadata.get('icon')):
                shape = {'circle': 'iconCircle', 'square': 'iconSquare', 'rounded': 'iconRounded'}.get(previous_metadata.get('form'), 'icon')
            self.nodes[identifier] = FlowNode(identifier, label, self.span(start, self.cursor), shape,
                label_kind=self.last_kind if explicit else "text", raw_label=self.last_raw if explicit else None,
                label_span=self.last_span if explicit else self.span(start, identifier_end),
                classes=old.classes if old else (), styles=old.styles if old else (),
                metadata=old.metadata if old else (),
                props=freeze_value({**(thaw_value(old.props) if old and old.props else {}), **props}))
        if self.text.startswith(':::', self.cursor):
            self.cursor += 3
            self.set_class(identifier, self.identifier())
        self.horizontal()
        while self.text.startswith('@{', self.cursor):
            self.metadata(identifier)
            self.horizontal()
        return identifier

    def node_list(self) -> list[str]:
        nodes = [self.node()]
        while (self.cursor < len(self.text) and self.text[self.cursor] == '&'
               and self.cursor > 0 and self.text[self.cursor - 1].isspace()
               and self.cursor + 1 < len(self.text) and self.text[self.cursor + 1].isspace()):
            self.cursor += 1
            self.horizontal()
            nodes.append(self.node())
        return nodes

    def link(self) -> ParsedLink | None:
        original = self.cursor
        self.link_whitespace()
        start = self.cursor
        user_id = None
        edge_id = re.match(r'[^\s"{}]+@(?=[^{"])', self.text[self.cursor:])
        if edge_id:
            user_id = edge_id[0].replace('@', '', 1)
            self.cursor += edge_id.end()
        match = match_direct(self.text, self.cursor)
        label, span, kind, raw = '', None, 'text', None
        beginning = None
        if match:
            ending = match[0]
            self.cursor = match.end()
        else:
            candidates = [pattern.match(self.text, self.cursor) for pattern in START]
            opening = max((item for item in candidates if item), key=lambda item: item.end(), default=None)
            if opening is None:
                if user_id is not None:
                    self.error('Expected edge after edge ID', start=start)
                self.cursor = original
                return None
            beginning = opening[0]
            self.cursor = opening.end()
            self.horizontal()
            if self.cursor < len(self.text) and self.text[self.cursor] == '"':
                label, span = self.quoted()
                self.horizontal()
                match = match_direct(self.text, self.cursor)
            else:
                label_start = self.cursor
                while self.cursor < len(self.text):
                    match = match_direct(self.text, self.cursor)
                    if match:
                        break
                    if self.text[self.cursor] == '"':
                        self.error('Unexpected quote in edge label')
                    self.cursor += 1
                if self.cursor == len(self.text):
                    self.error('Expected ending link after edge label')
                content = self.text[label_start:self.cursor]
                if not content.strip():
                    self.error('Expected nonempty inline edge label', start=label_start)
                label, span = self.label(content, label_start, self.cursor)
            if not match:
                self.error('Expected ending link after quoted edge label')
            ending = match[0]
            self.cursor = match.end()
            kind, raw = self.last_kind, self.last_raw
        edge_type, stroke, length, marker_start, marker_end = destruct_link(ending, beginning)
        after = self.cursor
        self.link_whitespace()
        if self.text.startswith('|', self.cursor):
            self.cursor += 1
            label, span = self.delimited_text('|')
            kind, raw = self.last_kind, self.last_raw
        else:
            self.cursor = after
        return ParsedLink(start, label, span, kind, raw, user_id, edge_type, stroke, length,
                          marker_start, marker_end)

    def add_links(self, sources, targets, token):
        for source in sources:
            for target in targets:
                if len(self.edges) >= self.config.max_edges:
                    self.error(f'Edge count exceeds maxEdges={self.config.max_edges}',
                               'MAX_EDGES_EXCEEDED', start=token.start)
                requested = token.user_id if source == sources[-1] and target == targets[0] else None
                user_defined = bool(requested) and not any(e.source_id == requested for e in self.edges)
                same_pair = sum(e.source == source and e.target == target for e in self.edges)
                source_id = requested if user_defined else f'L_{source}_{target}_{same_pair + 1 if same_pair else 0}'
                self.edges.append(FlowEdge(f'e{len(self.edges)}', source, target,
                    self.span(token.start, self.cursor), token.label, token.label_span, token.label_kind,
                    token.raw_label, source_id=source_id, is_user_defined_id=user_defined,
                    marker_start=token.marker_start, marker_end=token.marker_end, stroke=token.stroke,
                    min_length=token.length, curve=self.default_edge_curve, edge_type=token.edge_type))

    def metadata(self, identifier):
        # Keep parsing package initialization independent of this module's
        # cold import path (flowchart -> parser -> parsing -> parser).
        from py_mermaid.parsing.yaml_json import load_yaml_json, YamlError
        from py_mermaid.parsing.preprocess import _js_string
        start = self.cursor
        self.cursor += 2
        body_start = self.cursor
        quoted = False
        chunks, piece = [], self.cursor
        while self.cursor < len(self.text):
            char = self.text[self.cursor]
            if char == '"':
                if quoted:
                    chunks.append(re.sub(r'\n\s*', '<br/>', self.text[piece:self.cursor]))
                    chunks.append('"')
                    piece = self.cursor + 1
                else:
                    chunks.append(self.text[piece:self.cursor + 1])
                    piece = self.cursor + 1
                quoted = not quoted
            elif char == '}' and not quoted:
                chunks.append(self.text[piece:self.cursor])
                break
            elif char == '^' and not quoted:
                self.error('Unexpected caret outside a quoted metadata scalar')
            self.cursor += 1
        if self.cursor == len(self.text):
            self.error('Unterminated @{ metadata block', start=start)
        self.cursor += 1
        content = ''.join(chunks)
        yaml = content + '\n' if '\n' in content else '{\n' + content + '\n}'
        try:
            doc = load_yaml_json(yaml)
        except YamlError as exc:
            self.error(str(exc), 'INVALID_YAML', start=body_start, end=self.cursor - 1)
        if not isinstance(doc, Mapping):
            self.error('Shape metadata must be a mapping', 'INVALID_METADATA', start=start)
        if identifier in self.groups:
            if 'algorithm' in doc:
                algorithm = doc['algorithm']
                if not isinstance(algorithm, str) or not (algorithm == 'elk' or algorithm.startswith('elk.')):
                    self.error('Only the ELK group layout family is supported', 'UNSUPPORTED_CONFIG', start=start)
            group = self.groups[identifier]
            self.groups[identifier] = replace(group, metadata=freeze_value({**dict(thaw_value(group.metadata)), **doc}))
            return
        for index, edge in enumerate(self.edges):
            if edge.source_id == identifier:
                values = dict(thaw_value(edge.metadata)) if edge.metadata else {}
                values.update(doc)
                curve = doc.get('curve', edge.curve)
                if curve is not None and (not isinstance(curve, str) or curve not in CURVES):
                    self.error('Unknown per-edge curve', 'INVALID_METADATA', start=start)
                self.edges[index] = replace(edge, curve=curve, animate=doc.get('animate', edge.animate),
                    animation=doc.get('animation', edge.animation), metadata=freeze_value(values))
                return
        node = self.nodes[identifier]
        values = dict(thaw_value(node.metadata)) if node.metadata else {}
        for key, value in doc.items():
            # FlowDB's resource/shape fields update only on JS truthy values.
            # Keep effective values for their consumers, while SourceDocument
            # and the metadata source span retain the original declaration.
            if key not in {'shape', 'label', 'icon', 'form', 'pos', 'img', 'constraint', 'w', 'h'} or _truthy(value):
                values[key] = value
        shape = node.shape
        if _truthy(doc.get('shape')):
            value = doc['shape']
            if not isinstance(value, str) or value not in METADATA_SHAPES:
                self.error(f'No such metadata shape: {value!r}; expected a lowercase source alias',
                           'UNSUPPORTED_SHAPE', start=start)
            shape = canonical_shape(value)
        if _truthy(values.get('img')):
            shape = 'imageSquare'
        elif _truthy(values.get('icon')):
            shape = {'circle': 'iconCircle', 'square': 'iconSquare', 'rounded': 'iconRounded'}.get(values.get('form'), 'icon')
        label, kind, raw, label_span = node.label, node.label_kind, node.raw_label, node.label_span
        if _truthy(doc.get('label')):
            raw = _js_string(doc['label'])
            kind = 'text' if doc.get('labelType') in ('text', 'string') else 'markdown'
            # Unlike classic textObj, FlowDB assigns doc.label directly. Keep
            # its semantic markup serialization; the native label provider
            # sanitizes raw_label before measurement/paint. Only restore the
            # Mermaid entity transport spelling for canonical DB comparisons.
            label = re.sub(r'#(\w+);', lambda match: '&#' + match[1] + ';' if match[1].isdigit()
                           else '&' + match[1] + ';', raw)
            label_span = self.span(body_start, self.cursor - 1)
        elif (_truthy(doc.get('icon')) or _truthy(doc.get('img'))) and node.label == identifier:
            label, raw = '', ''
        self.nodes[identifier] = replace(node, shape=shape, label=label, label_kind=kind, raw_label=raw,
            label_span=label_span, metadata=freeze_value(values))

    def set_class(self, identifiers, classes):
        for identifier in identifiers.split(','):
            if identifier in self.nodes:
                node = self.nodes[identifier]
                self.nodes[identifier] = replace(node, classes=node.classes + (classes,))
            if identifier in self.groups:
                group = self.groups[identifier]
                self.groups[identifier] = replace(group, classes=group.classes + (classes,))
            for index, edge in enumerate(self.edges):
                if edge.source_id == identifier:
                    self.edges[index] = replace(edge, classes=edge.classes + (classes,))
                    break

    def statement_value(self):
        start = self.cursor
        quote = False
        while self.cursor < len(self.text):
            char = self.text[self.cursor]
            if char == '"':
                quote = not quote
            elif char in ';\r\n' and not quote:
                break
            self.cursor += 1
        if quote:
            self.error('Unterminated quoted statement', start=start)
        return self.text[start:self.cursor].strip()

    def style_statement(self, keyword):
        self.cursor += len(keyword)
        self.horizontal()
        selector_start = self.cursor
        selector = self.identifier()
        selector_end = self.cursor
        self.horizontal()
        value = self.statement_value()
        if not value:
            self.error('Expected styles or class names')
        styles = tuple(value.split(','))
        if keyword == 'class':
            if any(not identifier_character(char) for char in value) or ':::' in value:
                self.error('Expected one class identifier')
            self.set_class(selector, value)
        elif keyword == 'classDef':
            normalized = value.replace('\\,', '\u00a7\u00a7\u00a7').replace(',', ';').replace('\u00a7\u00a7\u00a7', ',').split(';')
            for name in selector.split(','):
                old = self.classes.get(name, ClassDefinition(name))
                self.classes[name] = replace(old, styles=old.styles + tuple(normalized),
                    text_styles=old.text_styles + tuple(style.replace('fill', 'bgFill', 1) for style in normalized if 'color' in style))
        else:
            if not any(edge.source_id == selector for edge in self.edges):
                if selector not in self.nodes:
                    self.nodes[selector] = FlowNode(selector, selector, self.span(selector_start, selector_end))
                node = self.nodes[selector]
                self.nodes[selector] = replace(node, styles=node.styles + styles)
        self.statement_end()

    def link_style(self):
        self.cursor += len('linkStyle')
        self.horizontal()
        selector_start = self.cursor
        while self.cursor < len(self.text) and not self.text[self.cursor].isspace():
            self.cursor += 1
        selector = self.text[selector_start:self.cursor]
        if selector != 'default' and not re.fullmatch(r'\d+(?:,\d+)*', selector):
            self.error('Invalid linkStyle edge index', start=selector_start)
        indices = [] if selector == 'default' else [int(item) for item in selector.split(',')]
        self.horizontal()
        interpolate = None
        if self.keyword('interpolate'):
            self.cursor += len('interpolate')
            self.horizontal()
            interpolate = self.identifier()
            self.horizontal()
            if interpolate not in CURVES:
                self.error('Unknown link interpolation', 'INVALID_CONFIG')
        value = self.statement_value()
        if not value and interpolate is None:
            self.error('Expected linkStyle declarations')
        styles = tuple(value.split(',')) if value else ()
        for index in indices:
            if index >= len(self.edges):
                self.error(f'linkStyle index {index} is out of bounds', 'INVALID_EDGE_INDEX', start=selector_start)
        if selector == 'default':
            if styles:
                self.default_edge_styles = styles
            if interpolate is not None:
                self.default_edge_curve = interpolate
        else:
            for index in indices:
                edge = self.edges[index]
                assigned = styles + (('fill:none',) if styles and not any(s.startswith('fill') for s in styles) else ())
                self.edges[index] = replace(edge, styles=assigned if styles else edge.styles,
                    curve=interpolate if interpolate is not None else edge.curve)
        self.statement_end()

    def ignored_click(self):
        self.cursor += len('click')
        self.horizontal()
        start = self.cursor
        while self.cursor < len(self.text) and not self.text[self.cursor].isspace():
            self.cursor += 1
        identifier = self.text[start:self.cursor]
        self.horizontal()
        statement_start = self.cursor
        if self.keyword('call'):
            self.cursor += len('call')
            self.horizontal()
            left = self.text.find('(', self.cursor)
            if left < 0 or not self.text[self.cursor:left].strip():
                self.error('Expected callback name and arguments')
            right = self.text.find(')', left + 1)
            if right < 0:
                self.error('Unterminated ignored callback arguments')
            self.cursor = right + 1
            self.horizontal()
            tail = self.statement_value()
            valid = not tail or bool(re.fullmatch(r'"[^"]*"', tail))
        else:
            tail = self.statement_value()
            quoted = r'"[^"]*"'
            target = r'(?:_self|_blank|_parent|_top)'
            valid = bool(re.fullmatch(r'(?:href\s+)?' + quoted + r'(?:\s+' + quoted + r')?(?:\s+' + target + r')?', tail)
                         or re.fullmatch(r'[^\s"()]+(?:\s+' + quoted + r')?', tail))
        if not identifier or not valid:
            self.error('Invalid ignored click declaration', start=statement_start)
        self.set_class(identifier, 'clickable')
        self.statement_end()

    def start_group(self) -> None:
        start = self.cursor
        self.cursor += len("subgraph")
        self.horizontal()
        identifier = None
        label = ""
        self.last_kind, self.last_raw, self.last_span = "text", "", self.span(self.cursor, self.cursor)
        if self.cursor < len(self.text) and self.text[self.cursor] not in ";\r\n":
            if self.text[self.cursor] == '"':
                label, _ = self.quoted()
                if label and not re.search(r"\s", label):
                    identifier = label
            else:
                title_start = self.cursor
                while self.cursor < len(self.text) and self.text[self.cursor] not in "[;\r\n":
                    self.cursor += 1
                head = self.text[title_start:self.cursor].strip()
                if self.cursor < len(self.text) and self.text[self.cursor] == "[":
                    if not head or re.search(r"\s", head):
                        self.error("Explicit subgraph ID must be a single identifier", start=title_start)
                    identifier = head
                    self.cursor += 1
                    label, _ = self.delimited_text("]")
                else:
                    label, _ = self.label(head, title_start, self.cursor)
                    if head and not re.search(r"\s", head):
                        identifier = head
        self.blocks.append(_Block(start, identifier, label, label_kind=self.last_kind,
                                  raw_label=self.last_raw, label_span=self.last_span))
        self.statement_end()

    def end_group(self) -> None:
        start = self.cursor
        self.cursor += len("end")
        if not self.blocks:
            self.error("end without matching subgraph", start=start)
        block = self.blocks.pop()
        identifier = block.identifier if block.identifier is not None else f"subGraph{self.group_count}"
        self.group_count += 1
        claimed = {member for group in self.groups.values() for member in group.members}
        members = tuple(dict.fromkeys(member for member in block.members
                                     if member != identifier and member not in claimed))
        old = self.groups.get(identifier)
        if old is not None:
            self.groups[identifier] = replace(old, members=old.members + members)
        else:
            direction = block.direction
            if direction is None and self.config.inherit_direction:
                direction = 'TB' if self.direction == 'TD' else self.direction
            self.groups[identifier] = FlowGroup(identifier, block.label, self.span(block.start, self.cursor),
                members=members, direction=direction, label_kind=block.label_kind,
                raw_label=block.raw_label, label_span=block.label_span)
        if self.blocks:
            self.blocks[-1].members.append(identifier)
        self.statement_end()

    def group_direction(self) -> None:
        start = self.cursor
        self.cursor += len("direction")
        self.horizontal()
        value_start = self.cursor
        while self.cursor < len(self.text) and self.text[self.cursor].isalpha():
            self.cursor += 1
        direction = self.text[value_start:self.cursor]
        if direction not in ("TD", "TB", "LR", "RL", "BT"):
            self.error("Unsupported subgraph direction", "UNSUPPORTED_DIRECTION", start=value_start)
        if self.blocks:
            self.blocks[-1].direction = direction
        self.statement_end()

    def lexical_direction(self):
        # These INITIAL-state flow.jison rules deliberately consume the whole
        # matched line. Preserve their source precedence, including trailing text.
        for value in ('TB', 'BT', 'RL', 'LR', 'TD'):
            match = re.match(r'.*direction\s+' + value + r'[^\n]*', self.text[self.cursor:])
            if match:
                self.cursor += match.end()
                if self.blocks:
                    self.blocks[-1].direction = value
                self.statement_end()
                return True
        return False

    def finish(self) -> Flowchart:
        parents: dict[str, str] = {}
        for group in reversed(tuple(self.groups.values())):
            for member in group.members:
                parents[member] = group.id
        for identifier, group in self.groups.items():
            seen = {identifier}
            parent = parents.get(identifier)
            while parent is not None:
                if parent in seen:
                    raise MermaidError("Cyclic subgraph membership", code="INVALID_GROUP_HIERARCHY", span=group.span)
                seen.add(parent)
                parent = parents.get(parent)
        colour = {group.id: index for index, group in enumerate(
            sorted(self.groups.values(), key=lambda item: item.span.start.index))}
        effective_groups = {}
        for group in self.groups.values():
            placeholder = self.nodes.get(group.id)
            effective_groups[group.id] = replace(group, parent_id=parents.get(group.id), color_index=colour[group.id],
                classes=placeholder.classes if placeholder is not None else group.classes,
                styles=placeholder.styles if placeholder is not None else group.styles)
        def outermost_collapsed(identifier):
            result = None
            while identifier in effective_groups:
                group = effective_groups[identifier]
                if dict(thaw_value(group.metadata)).get('view') == 'collapsed':
                    result = identifier
                identifier = parents.get(identifier)
            return result
        hidden, redirects = set(), {}
        for group in effective_groups.values():
            ancestor = outermost_collapsed(group.id)
            if ancestor is not None:
                for member in (group.id, *group.members):
                    if member != ancestor:
                        hidden.add(member)
                        redirects[member] = ancestor
        object_ids = set(self.nodes) | set(self.groups)
        groups = tuple(replace(group, members=tuple(member for member in group.members if member not in hidden and member in object_ids))
                       for group in effective_groups.values() if group.id not in hidden
                       and dict(thaw_value(group.metadata)).get('view') != 'collapsed')
        nodes = []
        for group in reversed(tuple(effective_groups.values())):
            if group.id not in hidden and dict(thaw_value(group.metadata)).get('view') == 'collapsed':
                nodes.append(FlowNode(group.id, group.label, group.span, 'collapsedGroup', group.parent_id,
                    group.label_kind, group.raw_label, group.label_span, classes=group.classes,
                    styles=group.styles, metadata=group.metadata, color_index=group.color_index))
        nodes.extend(replace(node, parent_id=parents.get(node.id)) for node in self.nodes.values()
                     if node.id not in self.groups and node.id not in hidden)
        edges = []
        for edge in self.edges:
            source, target = redirects.get(edge.source, edge.source), redirects.get(edge.target, edge.target)
            if self._drop_collapsed_selfloop(edge, source, target, redirects):
                continue
            edges.append(replace(edge, source=source, target=target,
                curve=edge.curve or self.default_edge_curve or self.config.curve))
        from py_mermaid.rendering.labels.sanitize import sanitize_markup
        return Flowchart(self.raw, self.direction, tuple(nodes), tuple(edges), self.config, groups=groups,
            diagram_type=self.diagram_type,
            title=sanitize_markup(self.document.title, self.config) if self.document else "",
            acc_title=sanitize_markup(self.acc_title, self.config),
            acc_description=sanitize_markup(self.acc_description, self.config), source_document=self.document,
            class_definitions=tuple(self.classes.values()), default_edge_styles=self.default_edge_styles,
            default_edge_curve=self.default_edge_curve)

    def _drop_collapsed_selfloop(self, edge, source, target, redirects):
        """Keep the flowchart collapse policy; derived grammars own their policy."""
        return source == target and (edge.source in redirects or edge.target in redirects)

    def accessibility(self):
        title = re.match(r"accTitle\s*:\s*", self.text[self.cursor:])
        description = re.match(r"accDescr\s*:\s*", self.text[self.cursor:])
        block = re.match(r"accDescr\s*{\s*", self.text[self.cursor:])
        match = title or description or block
        if match is None:
            return False
        self.cursor += match.end()
        start = self.cursor
        if block:
            while self.cursor < len(self.text) and self.text[self.cursor] != "}":
                self.cursor += 1
            if self.cursor == len(self.text):
                self.error("Unterminated accessibility description", start=start)
            value = self.text[start:self.cursor].strip()
            self.cursor += 1
        else:
            while self.cursor < len(self.text) and self.text[self.cursor] not in "\r\n":
                self.cursor += 1
            value = self.text[start:self.cursor].strip()
        if title:
            self.acc_title = value
        else:
            self.acc_description = re.sub(r"\n\s+", "\n", value)
        self.statement_end()
        return True

    def parse(self) -> Flowchart:
        self.separators()
        if self.text.startswith("---", self.cursor):
            self.error("YAML frontmatter is outside this slice; pass config explicitly", "UNSUPPORTED_SYNTAX")
        header = _HEADER.match(self.text, self.cursor)
        if header is None:
            self.error("Expected flowchart or graph header", "UNKNOWN_DIAGRAM")
        self.cursor = header.end()
        if header[1]=='flowchart-elk':self.diagram_type='flowchart-elk'
        self.horizontal()
        direction_start = self.cursor
        if self.cursor == len(self.text) or self.text[self.cursor] in '\r\n':
            self.direction = 'TB'
        else:
            while self.cursor < len(self.text) and not self.text[self.cursor].isspace() and self.text[self.cursor] != ';':
                self.cursor += 1
            value = self.text[direction_start:self.cursor]
            self.direction = {'<': 'RL', '>': 'LR', '^': 'BT', 'v': 'TB', 'BR': 'TB'}.get(value, value)
        if self.direction not in ("TD", "TB", "LR", "RL", "BT"):
            self.error("Unsupported flowchart direction", "UNSUPPORTED_DIRECTION",
                       start=direction_start, end=self.cursor)
        direction_end = self.cursor
        self.horizontal()
        if self.cursor > direction_end and self.text.startswith(';', self.cursor):
            self.error('A header space separator must end with a newline')
        self.statement_end()
        while self.cursor < len(self.text):
            if self.lexical_direction():
                continue
            elif self.accessibility():
                continue
            elif self.keyword("subgraph"):
                self.start_group()
            elif self.keyword("end"):
                self.end_group()
            elif self.keyword("direction"):
                self.group_direction()
            elif self.keyword('style'):
                self.style_statement('style')
            elif self.keyword('classDef'):
                self.style_statement('classDef')
            elif self.keyword('class'):
                self.style_statement('class')
            elif self.keyword('linkStyle'):
                self.link_style()
            elif self.text.startswith('click', self.cursor) and self.cursor + 5 < len(self.text) and self.text[self.cursor + 5].isspace():
                self.ignored_click()
            else:
                current = self.node_list()
                chain = list(current)
                while (link := self.link()) is not None:
                    self.link_whitespace()
                    target = self.node_list()
                    self.add_links(current, target, link)
                    current = target
                    chain = list(target) + chain
                if self.blocks:
                    self.blocks[-1].members.extend(chain)
                self.statement_end()
        if self.blocks:
            self.error("Unterminated subgraph; expected end", start=self.blocks[-1].start,
                       end=len(self.text))
        return self.finish()


def parse_flowchart(text: str, *, config: Mapping | None = None) -> Flowchart:
    """Parse scoped flowchart syntax with raw character/UTF-16 half-open spans."""
    if not isinstance(text, str):
        raise MermaidError("Diagram source must be str", code="INVALID_INPUT")
    from py_mermaid.parsing.preprocess import preprocess_diagram
    document = preprocess_diagram(text, config)
    resolved = resolve_config(config, layers=document.config_layers)
    document = replace(document, config_layers=resolved.config_layers)
    parser = _Parser(document.cleaned, resolved, document)
    if len(document.cleaned.encode("utf-16-le", errors="surrogatepass")) // 2 > resolved.max_text_size:
        parser.error(f"Source exceeds maxTextSize={resolved.max_text_size}",
                     "MAX_TEXT_SIZE_EXCEEDED", start=0, end=len(document.cleaned))
    return parser.parse()
