"""Pinned Mermaid preprocessing with an explicit raw-source boundary map."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import replace
import json
import re
from py_mermaid.model.flowchart import SourceDocument, MermaidError, SourcePosition, SourceSpan
from py_mermaid.config.values import freeze_value, assign_with_depth
from .yaml_json import load_yaml_json, YamlError

_DIRECTIVE = re.compile(r"%%{\s*(?:(\w+)\s*:|(\w+))\s*(?:(\w+)|((?:(?!}%%).|\r?\n)*))?\s*(?:}%%)?", re.I | re.ASCII)


def _white(char):
    return bool(char) and (char.isspace() or char == "\ufeff") and char not in "\x1c\x1d\x1e\x1f"


class _Mapped:
    def __init__(self, text):
        self.text = text
        self.boundaries = list(range(len(text) + 1))

    def substitute(self, pattern, replacement):
        pieces, positions = [], []
        consumed = 0
        for match in pattern.finditer(self.text):
            start, end = match.span()
            pieces.append(self.text[consumed:start])
            positions.extend(self.boundaries[consumed:start])
            value = replacement(match) if callable(replacement) else replacement
            pieces.append(value)
            if value:
                positions.extend(self.boundaries[start + i * (end - start) // len(value)] for i in range(len(value)))
            consumed = end
        pieces.append(self.text[consumed:])
        positions.extend(self.boundaries[consumed:])
        self.text, self.boundaries = "".join(pieces), positions

    def cut_prefix(self, length):
        self.text, self.boundaries = self.text[length:], self.boundaries[length:]


def match_frontmatter(text):
    """Linear scanner port of diagram-api/regexes.ts:matchFrontMatter."""
    cursor = 0
    while cursor < len(text) and _white(text[cursor]) and text[cursor] not in "\r\n":
        cursor += 1
    indent = text[:cursor]
    if not text.startswith("---", cursor):
        return None
    openings = []
    for i in range(cursor + 3, len(text)):
        if not _white(text[i]):
            break
        if text[i] in "\r\n":
            openings.append(i)
    if not openings:
        return None
    fence = indent + "---"
    def closing(index):
        if text[index] not in "\r\n" or not text.startswith(fence, index + 1):
            return -1
        last = -1
        for j in range(index + 1 + len(fence), len(text)):
            if not _white(text[j]):
                break
            if text[j] in "\r\n":
                last = j
        return last
    last_close = -1
    for i in range(openings[0] + 1, len(text)):
        if closing(i) != -1:
            last_close = i
    if last_close == -1:
        return None
    opening = max(i for i in openings if i < last_close)
    for i in range(opening + 1, last_close + 1):
        end = closing(i)
        if end != -1:
            return indent, text[opening + 1:i], end + 1, opening + 1
    return None


def _js_string(value):
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, list):
        return ",".join(_js_string(item) if item is not None else "" for item in value)
    if isinstance(value, Mapping):
        return "[object Object]"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _truthy(value):
    return isinstance(value, (Mapping, list, tuple)) or bool(value)


def preprocess_diagram(text: str, site_config: Mapping | None = None, *, diagram_type: str = 'flowchart') -> SourceDocument:
    if not isinstance(text, str):
        raise MermaidError("Diagram source must be str", code="INVALID_INPUT")
    source = _Mapped(text)
    source.substitute(re.compile(r"\r\n?"), "\n")
    source.substitute(re.compile(r"<(\w+)([^>]*)>"),
                      lambda m: "<" + m[1] + re.sub(r'="([^"]*)"', r"='\1'", m[2]) + ">")
    normalized = source.text
    frontmatter, title, offset, diagnostics = {}, "", 0, []
    matched = match_frontmatter(source.text)
    if matched:
        indent, body, length, body_start = matched
        raw_body = body
        if indent:
            body = "\n".join(line[len(indent):] if line.startswith(indent) else line for line in body.split("\n"))
        try:
            parsed = load_yaml_json(body)
        except YamlError as exc:
            # YAML line offsets describe the header body, not a rewritten diagram.
            relative = sum(len(line) for line in raw_body.splitlines(keepends=True)[:exc.line - 1])
            line_index = source.boundaries[min(body_start + relative + len(indent), len(source.text))]
            prefix = text[:line_index]
            row = prefix.replace("\r\n", "\n").replace("\r", "\n").count("\n") + 1
            column_start = max(prefix.rfind("\n"), prefix.rfind("\r")) + 1
            start = SourcePosition(line_index, len(prefix.encode("utf-16-le", errors="surrogatepass")) // 2,
                                   row, len(prefix[column_start:].encode("utf-16-le", errors="surrogatepass")) // 2)
            raise MermaidError(str(exc), code=exc.code, span=SourceSpan(start, start)) from exc
        if isinstance(parsed, dict):
            if _truthy(parsed.get("title")):
                title = _js_string(parsed["title"])
            if isinstance(parsed.get("config"), Mapping):
                frontmatter = dict(parsed["config"])
            if _truthy(parsed.get("displayMode")):
                frontmatter.setdefault("gantt", {})["displayMode"] = _js_string(parsed["displayMode"])
        offset = source.text[:length].count("\n")
        source.cut_prefix(length)
    directive = {}
    wraps = []
    # detectDirective replaces apostrophes in its input before JSON.parse. Keep
    # parsing indices on the original text; the rewrite is local to arguments.
    malformed = False
    for match in _DIRECTIVE.finditer(source.text):
        kind = match[1] or match[2] or ""
        if "wrap" in kind:
            wraps.append(kind)
        if not re.search(r"(?:init\b)|(?:initialize\b)", kind):
            continue
        payload = match[3] or match[4]
        try:
            value = match[3].strip() if match[3] else json.loads((payload or "null").strip().replace("'", '"'))
        except (ValueError, TypeError, RecursionError) as exc:
            diagnostics.append("Invalid init/initialize directive ignored: " + str(exc))
            malformed = True
            continue
        if isinstance(value, dict):
            # Legacy init.config is scoped to the detected diagram family.
            if "config" in value:
                value[diagram_type] = value.pop("config")
            assign_with_depth(directive, value)
    if malformed:
        directive = {}
    if wraps:
        if len(wraps) > 1:
            directive["wrap"] = any(kind == "wrap" for kind in wraps)
        elif wraps[0] == "wrap":
            directive["wrap"] = True
    source.substitute(_DIRECTIVE, "")
    with_comments = source.text
    source.substitute(re.compile(r"^\s*%%(?!{)[^\n]+\n?", re.M), "")
    trimmed = len(source.text) - len(source.text.lstrip())
    source.cut_prefix(trimmed)
    layers = (("site", freeze_value(site_config or {})), ("frontmatter", freeze_value(frontmatter)),
              ("directive", freeze_value(directive)))
    return SourceDocument(text, normalized, with_comments, source.text, tuple(source.boundaries), offset,
                          title, layers, tuple(diagnostics))
