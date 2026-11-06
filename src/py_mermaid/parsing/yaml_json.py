"""Safe YAML JSON-schema data reader for Mermaid frontmatter/configuration.

Implements block/flow collections, JSON-schema scalars, quoted and block text,
anchors/aliases and explicit JSON tags. No Python object constructors or native
YAML extension are invoked. Duplicate keys and cyclic alias graphs are rejected.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
import re
from py_mermaid.model.flowchart import MermaidError


class YamlError(MermaidError):
    def __init__(self, message, line=1):
        self.line = line
        super().__init__(f"YAML line {line}: {message}", code="INVALID_YAML")


def _comment(text):
    quoted = None
    escaped = False
    for i, char in enumerate(text):
        if quoted:
            if char == quoted and not escaped:
                quoted = None
            escaped = char == "\\" and not escaped if quoted == '"' else False
        elif char in "\"'":
            quoted = char
        elif char == "#" and (i == 0 or text[i - 1].isspace()):
            return text[:i].rstrip()
    return text.rstrip()


def _colon(text):
    quote = None
    level = 0
    escaped = False
    for i, char in enumerate(text):
        if quote:
            if char == quote and not escaped:
                quote = None
            escaped = char == "\\" and not escaped if quote == '"' else False
        elif char in "\"'":
            quote = char
        elif char in "[{":
            level += 1
        elif char in "]}":
            level -= 1
        elif char == ":" and level == 0 and (i + 1 == len(text) or text[i + 1].isspace()):
            return i
    return -1


def _scalar(text):
    if text in ("", "~", "null", "Null", "NULL"):
        return None
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    # Pinned js-yaml 4.3.0 resolves these types with finite JS Numbers.
    # Its integer grammar has lowercase base prefixes and no underscores.
    for pattern, base in ((r"[-+]?0x[0-9a-fA-F]+", 16), (r"[-+]?0o[0-7]+", 8),
                          (r"[-+]?0b[01]+", 2), (r"[-+]?[0-9]+", 10)):
        if re.fullmatch(pattern, text):
            try:
                number = float(int(text, base))
            except (OverflowError, ValueError):
                return text
            return int(number) if math.isfinite(number) else text
    if re.fullmatch(r"(?:[-+]?[0-9]+(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?|\.[0-9]+(?:[eE][-+]?[0-9]+)?)", text):
        number = float(text)
        return number if math.isfinite(number) else text
    if re.fullmatch(r"[-+]?\.(?:inf|Inf|INF)", text):
        return float("-inf" if text.startswith("-") else "inf")
    if re.fullmatch(r"\.(?:nan|NaN|NAN)", text):
        return float("nan")
    return text


class _Flow:
    def __init__(self, text, anchors, line):
        self.text, self.anchors, self.line, self.i = text, anchors, line, 0
        self.level = 0

    def space(self):
        while self.i < len(self.text) and self.text[self.i].isspace():
            self.i += 1

    def fail(self, msg):
        raise YamlError(msg, self.line)

    def value(self, *, key=False):
        self.space()
        if self.i >= len(self.text):
            return None
        char = self.text[self.i]
        if char in "&*!":
            marker = char
            self.i += 1
            start = self.i
            while self.i < len(self.text) and not self.text[self.i].isspace() and self.text[self.i] not in ",]}{[":
                self.i += 1
            name = self.text[start:self.i]
            if marker == "*":
                if name not in self.anchors:
                    self.fail(f"Unknown or cyclic alias {name!r}")
                pending, count = [self.anchors[name]], 0
                while pending:
                    item = pending.pop()
                    count += 1
                    if count > 50000:
                        self.fail("Alias expansion budget exceeded")
                    if isinstance(item, dict):
                        pending.extend(item.values())
                    elif isinstance(item, list):
                        pending.extend(item)
                return deepcopy(self.anchors[name])
            self.space()
            value_start = self.i
            value = self.value(key=key)
            if marker == "&":
                self.anchors[name] = deepcopy(value)
                return value
            tag = name.lstrip("!")
            if tag == "str":
                if value_start < len(self.text) and self.text[value_start] in "\"'":
                    return value
                return self.text[value_start:self.i].strip()
            if tag not in ("map", "seq", "int", "float", "bool", "null"):
                self.fail(f"Unsupported JSON-schema YAML tag !{name}")
            types = {"map": dict, "seq": list, "int": int, "float": (int, float), "bool": bool, "null": type(None)}
            if isinstance(value, str) and tag in ("int", "float", "bool", "null"):
                value = _scalar(value)
            if not isinstance(value, types[tag]):
                self.fail(f"Value does not match tag {tag}")
            return value
        if char == '"':
            start = self.i
            self.i += 1
            escaped = False
            while self.i < len(self.text):
                current = self.text[self.i]
                self.i += 1
                if current == '"' and not escaped:
                    raw = self.text[start:self.i]
                    # YAML double quoted escape additions beyond JSON.
                    for old, new in [(r"\0", r"\u0000"), (r"\a", r"\u0007"), (r"\v", r"\u000b"),
                                     (r"\e", r"\u001b"), (r"\N", r"\u0085"), (r"\_", r"\u00a0"),
                                     (r"\L", r"\u2028"), (r"\P", r"\u2029")]:
                        raw = raw.replace(old, new)
                    raw = re.sub(r"\\x([0-9a-fA-F]{2})", r"\\u00\1", raw)
                    raw = re.sub(r"\\U([0-9a-fA-F]{8})", lambda m: chr(int(m[1], 16)), raw)
                    raw = raw.replace("\\\n", "").replace("\n", " ")
                    raw = raw.replace("\\ ", " ")
                    try:
                        return json.loads(raw)
                    except (ValueError, UnicodeError) as exc:
                        self.fail(f"Invalid quoted scalar: {exc}")
                escaped = current == "\\" and not escaped
            self.fail("Unclosed double quote")
        if char == "'":
            self.i += 1
            out = []
            while self.i < len(self.text):
                if self.text[self.i] == "'":
                    self.i += 1
                    if self.i < len(self.text) and self.text[self.i] == "'":
                        out.append("'"); self.i += 1
                    else:
                        return "".join(out).replace("\n", " ")
                else:
                    out.append(self.text[self.i]); self.i += 1
            self.fail("Unclosed single quote")
        if char in "[{":
            self.level += 1
            if self.level > 100:
                self.fail("Configuration nesting budget exceeded")
            mapping = char == "{"
            closing = "}" if mapping else "]"
            out = {} if mapping else []
            self.i += 1
            self.space()
            if self.i < len(self.text) and self.text[self.i] == closing:
                self.i += 1
                self.level -= 1
                return out
            while self.i < len(self.text):
                item = self.value(key=mapping)
                self.space()
                if mapping:
                    if self.i == len(self.text) or self.text[self.i] != ":":
                        self.fail("Expected : in flow mapping")
                    self.i += 1
                    value = self.value()
                    _put(out, _key(item), value, self.line)
                else:
                    out.append(item)
                self.space()
                if self.i == len(self.text):
                    self.fail(f"Missing {closing}")
                if self.text[self.i] == closing:
                    self.i += 1
                    self.level -= 1
                    return out
                if self.text[self.i] != ",":
                    self.fail("Expected comma in flow collection")
                self.i += 1
                self.space()
                if self.i < len(self.text) and self.text[self.i] == closing:
                    self.i += 1
                    self.level -= 1
                    return out
            self.fail(f"Missing {closing}")
        start = self.i
        while (self.i < len(self.text) and not (self.level and self.text[self.i] in ",]}")
               and not (key and self.text[self.i] == ":")):
            if (self.level and self.text[self.i] == ":" and self.i + 1 < len(self.text)
                    and self.text[self.i + 1].isspace()):
                self.fail("Unexpected colon in flow scalar")
            self.i += 1
        return _scalar(self.text[start:self.i].strip())


def _put(mapping, key, value, line):
    if key in mapping:
        raise YamlError(f"Duplicate mapping key {key!r}", line)
    mapping[key] = value


def _key(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, dict):
        return "[object Object]"
    if isinstance(value, list):
        return ",".join(_key(item) if item is not None else "" for item in value)
    return str(value)


class _Block:
    def __init__(self, text):
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        self.lines = normalized.split("\n")
        if normalized.endswith("\n"):
            # split's final empty sentinel is not another physical blank line.
            self.lines.pop()
        self.i, self.anchors, self.depth = 0, {}, 0

    def clean(self, index):
        raw = self.lines[index]
        prefix = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[:len(raw) - len(raw.lstrip())]:
            raise YamlError("Tab indentation is not allowed", index + 1)
        return prefix, _comment(raw[prefix:])

    def skip(self):
        while self.i < len(self.lines) and not self.clean(self.i)[1]:
            self.i += 1

    def inline(self, text, line):
        parser = _Flow(text, self.anchors, line)
        value = parser.value()
        parser.space()
        if parser.i != len(parser.text):
            raise YamlError("Unexpected trailing flow scalar data", line)
        return value

    def block_text(self, marker, parent_indent):
        style = marker[0]
        chomp = "-" if "-" in marker else "+" if "+" in marker else ""
        number = re.search(r"[1-9]", marker)
        begin = self.i
        end = begin
        while end < len(self.lines):
            raw = self.lines[end]
            indent = len(raw) - len(raw.lstrip(" "))
            if raw.strip() and indent <= parent_indent:
                break
            end += 1
        nonempty = [len(raw) - len(raw.lstrip(" ")) for raw in self.lines[begin:end] if raw.strip()]
        indent = parent_indent + int(number[0]) if number else (min(nonempty) if nonempty else parent_indent + 1)
        items = [line[indent:] if len(line) >= indent else "" for line in self.lines[begin:end]]
        out = ""
        for index, line in enumerate(items):
            out += line
            if index + 1 < len(items):
                following = items[index + 1]
                if style == ">" and line and not line.startswith(" ") and not following.startswith(" "):
                    out += " " if following else ""
                else:
                    out += "\n"
        self.i = end
        out = out.rstrip("\n") if chomp != "+" else out
        return out if chomp == "-" else out + ("\n" if items else "")

    def value_after(self, value, indent, line):
        value = value.strip()
        tag = re.fullmatch(r"!!(str|map|seq|int|float|bool|null)(?:\s+(.*))?", value)
        if tag:
            body = tag[2] or ""
            if tag[1] == "str" and body and body[0] not in "\"'|>":
                return body
            result = self.value_after(body, indent, line)
            if tag[1] == "str":
                return "" if result is None else str(result)
            if isinstance(result, str) and tag[1] in ("int", "float", "bool", "null"):
                result = _scalar(result)
            expected = {"map": dict, "seq": list, "int": int, "float": (int, float), "bool": bool, "null": type(None)}[tag[1]]
            if not isinstance(result, expected):
                raise YamlError(f"Value does not match !!{tag[1]}", line)
            return result
        if re.fullmatch(r"[|>][1-9+-]*", value):
            return self.block_text(value, indent)
        anchor = re.fullmatch(r"&([\w-]+)(?:\s+(.*))?", value)
        if anchor:
            result = self.value_after(anchor[2] or "", indent, line)
            self.anchors[anchor[1]] = deepcopy(result)
            return result
        if not value:
            self.skip()
            if self.i < len(self.lines) and self.clean(self.i)[0] > indent:
                return self.collection(self.clean(self.i)[0])
            return None
        if value[0] not in "\"'*!&[{" and _colon(value) >= 0:
            raise YamlError("Colon followed by whitespace requires quoting in a scalar", line)
        # Continue flow/quoted scalars over source lines when delimiters remain open.
        while True:
            try:
                result = self.inline(value, line)
                if isinstance(result, str) and value[0] not in "\"'*!&[{":
                    while self.i < len(self.lines):
                        probe = self.i
                        while probe < len(self.lines) and not self.clean(probe)[1]:
                            probe += 1
                        if probe == len(self.lines):
                            break
                        next_indent, following = self.clean(probe)
                        if next_indent <= indent or _colon(following) >= 0:
                            break
                        result += ("\n" * (probe - self.i) if probe > self.i else " ") + following
                        self.i = probe + 1
                return result
            except YamlError as exc:
                if ("Unclosed" not in str(exc) and "Missing" not in str(exc)) or self.i >= len(self.lines):
                    raise
                if (value[0] not in "[{\"'" and self.clean(self.i)[0] <= indent and self.lines[self.i].strip()
                        and not self.lines[self.i].lstrip().startswith(("}", "]"))):
                    raise
                value += "\n" + self.lines[self.i].strip()
                self.i += 1

    def collection(self, indent):
        self.depth += 1
        if self.depth > 100:
            raise YamlError("Configuration nesting budget exceeded", self.i + 1)
        sequence = self.clean(self.i)[1].startswith("- ") or self.clean(self.i)[1] == "-"
        out = [] if sequence else {}
        while self.i < len(self.lines):
            self.skip()
            if self.i == len(self.lines):
                break
            current_indent, text = self.clean(self.i)
            if current_indent < indent:
                break
            if current_indent != indent:
                raise YamlError("Unexpected indentation", self.i + 1)
            line = self.i + 1
            self.i += 1
            if sequence:
                if not (text.startswith("- ") or text == "-"):
                    raise YamlError("Cannot mix mapping and sequence entries", line)
                body = text[1:].lstrip()
                colon = _colon(body)
                if colon >= 0:
                    item = {}
                    key = self.inline(body[:colon].strip(), line)
                    _put(item, _key(key), self.value_after(body[colon + 1:], indent + 2, line), line)
                    self.skip()
                    if self.i < len(self.lines) and self.clean(self.i)[0] > indent:
                        more = self.collection(self.clean(self.i)[0])
                        if not isinstance(more, dict):
                            raise YamlError("Expected mapping continuation", self.i + 1)
                        for key, value in more.items():
                            _put(item, key, value, line)
                    out.append(item)
                else:
                    out.append(self.value_after(body, indent, line))
            else:
                if text == "?" or text.startswith("? "):
                    key = self.value_after(text[1:].strip(), indent, line)
                    self.skip()
                    value = None
                    if self.i < len(self.lines):
                        next_indent, following = self.clean(self.i)
                        if next_indent == indent and (following == ":" or following.startswith(": ")):
                            self.i += 1
                            value = self.value_after(following[1:], indent, self.i)
                    _put(out, _key(key), value, line)
                    continue
                colon = _colon(text)
                if colon < 0:
                    if out:
                        raise YamlError("Expected key: value", line)
                    self.depth -= 1
                    return self.value_after(text, indent, line)
                key = self.inline(text[:colon].strip(), line)
                _put(out, _key(key), self.value_after(text[colon + 1:], indent, line), line)
        self.depth -= 1
        return out


def load_yaml_json(text):
    if text.startswith("\ufeff"):
        text = text[1:]
    for index, char in enumerate(text):
        code = ord(char)
        if ((code < 32 and code not in (9, 10, 13)) or 0x7F <= code <= 0x84 or 0x86 <= code <= 0x9F
                or 0xD800 <= code <= 0xDFFF or code in (0xFFFE, 0xFFFF)):
            raise YamlError("Non-printable character in YAML document", text[:index].count("\n") + 1)
    reader = _Block(text)
    reader.skip()
    if reader.i == len(reader.lines):
        return None
    result = reader.collection(reader.clean(reader.i)[0])
    reader.skip()
    if reader.i != len(reader.lines):
        raise YamlError("Unexpected additional YAML document", reader.i + 1)
    return result
