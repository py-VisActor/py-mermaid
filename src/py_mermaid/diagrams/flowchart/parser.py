"""Scanner/parser for the explicitly scoped flow.jison rectangular subset.

Parsing operates on the original source: comments and CRLF are skipped rather
than removed, preserving character and UTF-16 coordinates in all diagnostics.
Each invocation owns its node/edge tables. No browser, JS or native dependency.
"""
from __future__ import annotations

from collections.abc import Mapping
from bisect import bisect_right
import re

from py_mermaid.config import resolve_config
from py_mermaid.model.flowchart import (
    Flowchart, FlowConfig, FlowEdge, FlowNode, MermaidError, SourcePosition, SourceSpan,
)

_HEADER = re.compile(r"(flowchart|graph)(?=[\s;]|$)")
_RESERVED = frozenset({"subgraph", "end", "style", "classDef", "class", "linkStyle",
                       "click", "direction", "accTitle", "accDescr"})


class _Parser:
    def __init__(self, text: str, config: FlowConfig):
        self.text = text
        self.config = config
        self.cursor = 0
        self.nodes: dict[str, FlowNode] = {}
        self.edges: list[FlowEdge] = []
        self.utf16 = [0]
        self.lines = [0]
        for index, char in enumerate(text):
            self.utf16.append(self.utf16[-1] + (2 if ord(char) > 0xFFFF else 1))
            if char == "\n" or (char == "\r" and text[index:index + 2] != "\r\n"):
                self.lines.append(index + 1)

    def position(self, index: int) -> SourcePosition:
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
        while self.cursor < len(self.text) and self.text[self.cursor] in " \t\v\f":
            self.cursor += 1

    def comment(self) -> bool:
        if not self.text.startswith("%%", self.cursor):
            return False
        # comments.ts:cleanupComments is anchored at the line start. The more
        # permissive stripAnyComments belongs only to detector preprocessing;
        # treating it as parser whitespace would wrongly accept inline %%.
        line_start = max(self.text.rfind("\n", 0, self.cursor),
                         self.text.rfind("\r", 0, self.cursor)) + 1
        if self.text[line_start:self.cursor].strip():
            self.error("%% comments must occupy a separate line", "INVALID_SYNTAX")
        if self.text.startswith("%%{", self.cursor):
            self.error("Configuration directives are outside F01.1; pass config explicitly",
                       "UNSUPPORTED_SYNTAX")
        while self.cursor < len(self.text) and self.text[self.cursor] not in "\r\n":
            self.cursor += 1
        return True

    def separators(self) -> None:
        while self.cursor < len(self.text):
            if self.text[self.cursor].isspace() or self.text[self.cursor] == ";":
                self.cursor += 1
            elif not self.comment():
                break

    def node(self) -> str:
        self.horizontal()
        start = self.cursor
        while self.cursor < len(self.text):
            char = self.text[self.cursor]
            if char.isalnum() or char in "_":
                self.cursor += 1
            elif (char == "-" and self.cursor + 1 < len(self.text)
                  and (self.text[self.cursor + 1].isalnum() or self.text[self.cursor + 1] == "_")):
                self.cursor += 1
            else:
                break
        if self.cursor == start:
            self.error("Expected a node identifier")
        identifier = self.text[start:self.cursor]
        if identifier in _RESERVED:
            self.error(f"{identifier!r} is outside F01.1 rectangular flowcharts",
                       "UNSUPPORTED_SYNTAX", start=start)
        self.horizontal()
        explicit = self.cursor < len(self.text) and self.text[self.cursor] == "["
        label = identifier
        if explicit:
            self.cursor += 1
            label_start = self.cursor
            if self.cursor < len(self.text) and self.text[self.cursor] == '"':
                self.cursor += 1
                content_start = self.cursor
                while self.cursor < len(self.text) and self.text[self.cursor] != '"':
                    self.cursor += 1
                if self.cursor == len(self.text):
                    self.error("Unterminated quoted label", start=label_start)
                label = self.text[content_start:self.cursor].strip()
                self.cursor += 1
                self.horizontal()
            else:
                content_start = self.cursor
                while self.cursor < len(self.text) and self.text[self.cursor] != "]":
                    if self.text[self.cursor] in '[(\"{})<>|':
                        self.error("Use a quoted plain-text label, or a supported rectangle",
                                   "UNSUPPORTED_SYNTAX")
                    self.cursor += 1
                label = self.text[content_start:self.cursor].strip()
                if not label:
                    self.error("Empty unquoted rectangle label", start=content_start)
            if self.cursor == len(self.text) or self.text[self.cursor] != "]":
                self.error("Expected closing ] for rectangle label")
            self.cursor += 1
            if (any(marker in label for marker in ("<", ">", "`", "$$"))
                    or re.search(r"(?:#(?:[A-Za-z]+|[0-9]+);|&(?:#\w+|[A-Za-z]+);)", label)
                    or re.search(r"fa[bklrs]?:fa-[\w-]+", label)):
                self.error("HTML, Markdown, math and entity escapes are outside F01.1",
                           "UNSUPPORTED_SYNTAX", start=label_start, end=self.cursor - 1)
            label = label.replace("\r\n", "\n").replace("\r", "\n")
            # handle-markdown-text.ts:nonMarkdownToHTML/nonMarkdownToLines
            # both interpret a literal backslash+n as a line break. Plain runs
            # collapse horizontal whitespace in HTML and structured SVG labels.
            label = label.replace("\\n", "\n")
            label = "\n".join(re.sub(r"[ \t\v\f]+", " ", line).strip()
                              for line in label.split("\n"))
        node_span = self.span(start, self.cursor)
        if identifier not in self.nodes:
            self.nodes[identifier] = FlowNode(identifier, label, node_span)
        elif explicit:
            # flowDb.addVertex updates explicit text, but a bare reference retains it.
            self.nodes[identifier] = FlowNode(identifier, label, node_span)
        return identifier

    def parse(self) -> Flowchart:
        self.separators()
        if self.text.startswith("---", self.cursor):
            self.error("YAML frontmatter is outside F01.1; pass config explicitly", "UNSUPPORTED_SYNTAX")
        header = _HEADER.match(self.text, self.cursor)
        if header is None:
            self.error("Expected flowchart or graph header", "UNKNOWN_DIAGRAM")
        self.cursor = header.end()
        self.horizontal()
        direction_start = self.cursor
        while self.cursor < len(self.text) and self.text[self.cursor].isalpha():
            self.cursor += 1
        direction = self.text[direction_start:self.cursor]
        if direction not in ("TD", "LR"):
            self.error("F01.1 requires direction TD or LR", "UNSUPPORTED_DIRECTION",
                       start=direction_start, end=self.cursor)
        self.horizontal()
        self.comment()
        if self.cursor < len(self.text) and self.text[self.cursor] not in ";\r\n":
            self.error("Expected newline or ; after flowchart direction")
        self.separators()
        while self.cursor < len(self.text):
            current = self.node()
            while True:
                self.horizontal()
                if not self.text.startswith("-->", self.cursor):
                    break
                edge_start = self.cursor
                self.cursor += 3
                target = self.node()
                if len(self.edges) >= self.config.max_edges:
                    self.error(f"Edge count exceeds maxEdges={self.config.max_edges}",
                               "MAX_EDGES_EXCEEDED", start=edge_start)
                self.edges.append(FlowEdge(f"e{len(self.edges)}", current, target,
                                           self.span(edge_start, self.cursor)))
                current = target
            self.horizontal()
            self.comment()
            if self.cursor < len(self.text) and self.text[self.cursor] not in ";\r\n":
                self.error("F01.1 supports only rectangles and --> edges; unexpected trailing syntax",
                           "UNSUPPORTED_SYNTAX")
            self.separators()
        if not self.nodes:
            self.error("F01.1 requires at least one node", "EMPTY_DIAGRAM")
        return Flowchart(self.text, direction, tuple(self.nodes.values()), tuple(self.edges), self.config)


def parse_flowchart(text: str, *, config: Mapping | None = None) -> Flowchart:
    """Parse F01.1 source into immutable values with raw-source positions.

    Source size is measured in UTF-16 code units, matching JS String.length.
    Unsupported syntax fails explicitly; source is never truncated or sanitized
    into a different accepted diagram.
    """
    if not isinstance(text, str):
        raise MermaidError("Diagram source must be str", code="INVALID_INPUT")
    resolved = resolve_config(config)
    parser = _Parser(text, resolved)
    if parser.utf16[-1] > resolved.max_text_size:
        parser.error(f"Source exceeds maxTextSize={resolved.max_text_size}",
                     "MAX_TEXT_SIZE_EXCEEDED", start=0, end=len(text))
    return parser.parse()
