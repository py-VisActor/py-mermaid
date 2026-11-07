"""Pure initial HTML form state; no events, DOM, resource loading or painting.

Mermaid delegates these states to the HTML host after DOMPurify. The native
boundary therefore follows HTML's value-sanitization and initial-selectedness
algorithms rather than treating content attributes as already-computed state.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from html.parser import HTMLParser
import html
import math
import re

from ....model.controls import ControlOption, ControlSpec
from ....model.flowchart import MermaidError


CONTROL_TAGS = frozenset({'input', 'button', 'select', 'textarea', 'meter', 'progress', 'fieldset'})
INPUT_TYPES = frozenset(('hidden text search tel url email password date month week '
                         'time datetime-local number range color checkbox radio file '
                         'submit image reset button').split())
_READONLY_TYPES = frozenset(('text search tel url email password date month week '
                            'time datetime-local number').split())
_VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
_ASCII_SPACE = '\t\n\f\r '
_VALID_FLOAT = re.compile(r'-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')
_PARSE_FLOAT = re.compile(r'[\t\n\f\r ]*([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)')
_SPACE = re.compile(r'[\t\n\f\r ]+')


def _attributes(attrs):
    """HTML duplicate attributes are first-wins; booleans use presence."""
    result = {}
    for name, value in (attrs.items() if hasattr(attrs, 'items') else attrs):
        name = str(name).lower()
        if name not in result:
            result[name] = '' if value is None else str(value).replace('\0', '\ufffd')
    return result


def _finite(value, default=0., *, strict=False):
    if not isinstance(value, str):
        return default
    match = _VALID_FLOAT.fullmatch(value) if strict else _PARSE_FLOAT.match(value)
    if not match:
        return default
    try:
        number = float(value if strict else match[1])
    except (ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def _serialize_number(value):
    if value == 0:
        return '0'
    if value == int(value):
        return str(int(value))
    return format(value, '.15g')


def _fraction(value, minimum, maximum):
    if maximum <= minimum:
        return 0.
    delta = maximum-minimum
    return ((value-minimum)/delta if math.isfinite(delta)
            else (value/2-minimum/2)/(maximum/2-minimum/2))


def _leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _date(value):
    match = re.fullmatch(r'([0-9]{4,})-([0-9]{2})-([0-9]{2})', value)
    if not match:
        return False
    year, month, day = map(int, match.groups())
    if year <= 0 or not 1 <= month <= 12:
        return False
    return 1 <= day <= (31, 29 if _leap(year) else 28, 31, 30, 31, 30,
                        31, 31, 30, 31, 30, 31)[month - 1]


def _time(value):
    # A valid time permits milliseconds with one, two or three digits.
    match = re.fullmatch(r'([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\.([0-9]{1,3}))?)?', value)
    return bool(match and int(match[1]) < 24 and int(match[2]) < 60
                and (match[3] is None or int(match[3]) < 60))


def _date_value(kind, value):
    if kind == 'date':
        return value if _date(value) else ''
    if kind == 'month':
        m = re.fullmatch(r'([0-9]{4,})-([0-9]{2})', value)
        return value if m and int(m[1]) > 0 and 1 <= int(m[2]) <= 12 else ''
    if kind == 'week':
        m = re.fullmatch(r'([0-9]{4,})-W([0-9]{2})', value)
        if not m or int(m[1]) <= 0:
            return ''
        y = int(m[1]); previous = y - 1
        # Gregorian Jan 1, Monday=0, without datetime's year 9999 limit.
        weekday = (previous + previous // 4 - previous // 100 + previous // 400) % 7
        weeks = 53 if weekday == 3 or (weekday == 2 and _leap(y)) else 52
        return value if 1 <= int(m[2]) <= weeks else ''
    if kind == 'time':
        return value if _time(value) else ''
    match = re.fullmatch(r'(.+?)[T ](.+)', value)
    if not match or not _date(match[1]) or not _time(match[2]):
        return ''
    time = match[2]
    if '.' in time:
        time = time.rstrip('0').rstrip('.')
    if time.endswith(':00') and len(time) == 8:
        time = time[:-3]
    return match[1] + 'T' + time


def _range(attrs):
    minimum = _finite(attrs.get('min'), 0.)
    maximum = max(minimum, _finite(attrs.get('max'), 100.))
    value = _finite(attrs.get('value'), minimum / 2 + maximum / 2, strict=True)
    value = max(minimum, min(maximum, value))
    if attrs.get('step', '').lower() != 'any':
        step = _finite(attrs.get('step'), 1.)
        if step <= 0:
            step = 1.
        # The step base is valid min, else valid content value, else zero.
        base = _finite(attrs.get('min'), None)
        if base is None:
            base = _finite(attrs.get('value'), 0., strict=True)
        try:
            dvalue, dbase, dstep = map(lambda n: Decimal(str(n)), (value, base, step))
            lower = ((dvalue - dbase) / dstep).to_integral_value(rounding=ROUND_FLOOR)
            candidates = [dbase + lower * dstep, dbase + (lower + 1) * dstep]
            candidates = [n for n in candidates if Decimal(str(minimum)) <= n <= Decimal(str(maximum))]
            if candidates:
                # Equal-distance ties round toward positive infinity.
                value = float(min(candidates, key=lambda n: (abs(n - dvalue), -n)))
        except (InvalidOperation, OverflowError, ValueError):
            pass
    return minimum, maximum, value


def _input_value(kind, attrs):
    value = attrs.get('value', '')
    if kind in {'checkbox', 'radio'}:
        return attrs.get('value', 'on')
    if kind == 'file':
        # Content attributes cannot populate a selected file list.
        return ''
    if kind in {'text', 'search', 'tel', 'url', 'email', 'password'}:
        value = value.replace('\r', '').replace('\n', '')
        if kind in {'url', 'email'}:
            value = value.strip(_ASCII_SPACE)
        if kind == 'email' and 'multiple' in attrs:
            value = ','.join(part.strip(_ASCII_SPACE) for part in value.split(','))
        return value
    if kind in {'date', 'month', 'week', 'time', 'datetime-local'}:
        return _date_value(kind, value)
    if kind == 'number':
        return value if _finite(value, None, strict=True) is not None else ''
    if kind == 'range':
        return _serialize_number(_range(attrs)[2])
    if kind == 'color':
        from .color_values import normalize_color_value
        return normalize_color_value(value)
    return value


def _display_size(attrs):
    m = re.match(r'[\t\n\f\r ]*\+?([0-9]+)', attrs.get('size', ''))
    value = int(m[1]) if m else 0
    return value if value > 0 else 4 if 'multiple' in attrs else 1


class ControlCapture:
    """Collect descendants of one root; the root start is not fed again.

    ``data`` receives decoded character data, just like HTMLParser with
    convert_charrefs=True. ``inner_markup`` re-escapes text exactly once for the
    existing label parser. Input is a void root and is finished immediately.
    """
    def __init__(self, tag, attrs, *, inherited_disabled=False):
        self.tag = tag.lower()
        if self.tag not in CONTROL_TAGS:
            raise MermaidError('Unknown static control ' + tag, code='INVALID_HTML_CONTROL')
        self.attrs = _attributes(attrs)
        self.finished = self.tag == 'input'
        self.inherited_disabled = inherited_disabled
        self._stack = []
        self._text = []
        self._markup = []
        self._options = []
        self._option = None
        self._groups = []
        self._count = 0
        self._legend_seen = False
        self._legend_active = False
        self._legend_markup = []
        self._legend_text = []

    def _budget(self):
        self._count += 1
        if self._count > 20_000 or len(self._stack) > 256:
            raise MermaidError('Static control nesting/content budget exceeded', code='LABEL_BUDGET')

    def _finish_option(self):
        if self._option is None:
            return
        attrs, text, group, group_disabled = self._option
        content = _SPACE.sub(' ', ''.join(text)).strip(_ASCII_SPACE)
        label = attrs.get('label') or content
        self._options.append(ControlOption(label, attrs.get('value', content),
                                          'selected' in attrs, 'disabled' in attrs or group_disabled, group))
        self._option = None

    def start(self, tag, attrs):
        if self.finished:
            return
        self._budget(); tag = tag.lower(); attrs = _attributes(attrs)
        markup = '<' + tag + ''.join(' ' + k + '="' + html.escape(v, quote=True) + '"' for k, v in attrs.items()) + '>'
        if self.tag == 'fieldset' and tag == 'legend' and not self._stack and not self._legend_seen:
            self._legend_seen = self._legend_active = True
            self._legend_markup.append(markup)
            self._stack.append('legend')
            return
        (self._legend_markup if self._legend_active else self._markup).append(markup)
        if self.tag == 'textarea':
            self._text.append(markup)
            return
        if self.tag == 'select':
            if tag == 'option':
                self._finish_option()
                group, disabled = self._groups[-1] if self._groups else ('', False)
                self._option = (attrs, [], group, disabled)
            elif tag == 'optgroup':
                self._finish_option()
                self._groups = [(attrs.get('label', ''), 'disabled' in attrs)]
        if tag == 'br':
            (self._legend_text if self._legend_active else self._text).append('\n')
        if tag not in _VOID:
            self._stack.append(tag)

    def end(self, tag):
        if self.finished:
            return
        self._budget(); tag = tag.lower()
        if tag == self.tag and tag not in self._stack:
            self._finish_option(); self.finished = True
            return
        if self._legend_active and tag == 'legend' and self._stack == ['legend']:
            self._legend_markup.append('</legend>')
            self._legend_active = False; self._stack.pop()
            return
        (self._legend_markup if self._legend_active else self._markup).append('</' + tag + '>')
        if self.tag == 'textarea':
            self._text.append('</' + tag + '>')
            return
        if tag == 'option':
            self._finish_option()
        if tag == 'optgroup':
            self._finish_option(); self._groups = []
        if tag in self._stack:
            index = len(self._stack) - 1 - self._stack[::-1].index(tag)
            del self._stack[index:]

    def data(self, text):
        if self.finished:
            return
        self._budget(); text = text.replace('\0', '\ufffd')
        (self._legend_text if self._legend_active else self._text).append(text)
        (self._legend_markup if self._legend_active else self._markup).append(html.escape(text, quote=False))
        if self._option is not None:
            self._option[1].append(text)

    def build(self):
        self._finish_option()
        a = self.attrs; tag = self.tag
        attributes = tuple(a.items()); text = ''.join(self._text)
        kind = a.get('type', 'text').lower() if tag == 'input' else ''
        if tag == 'input' and kind not in INPUT_TYPES:
            kind = 'text'
        state = dict(tag=tag, input_type=kind, attributes=attributes, text=text,
                     inner_markup=''.join(self._markup), hidden='hidden' in a or kind == 'hidden')
        if tag in {'input', 'button', 'select', 'textarea', 'fieldset'}:
            state['disabled'] = 'disabled' in a or bool(self.inherited_disabled)
        if tag == 'input':
            state.update(value=_input_value(kind, a), checked=kind in {'checkbox', 'radio'} and 'checked' in a,
                         readonly=kind in _READONLY_TYPES and 'readonly' in a,
                         multiple=kind in {'email', 'file'} and 'multiple' in a)
            if kind == 'range':
                low, high, value = _range(a)
                state.update(minimum=low, maximum=high, fraction=_fraction(value,low,high))
        elif tag == 'textarea':
            value = text.replace('\r\n', '\n').replace('\r', '\n')
            if value.startswith('\n'):
                value = value[1:]
            state.update(value=value, text=value, readonly='readonly' in a)
        elif tag == 'button':
            state['value'] = a.get('value', '')
        elif tag == 'fieldset':
            state.update(legend_text=''.join(self._legend_text), legend_markup=''.join(self._legend_markup))
        elif tag == 'select':
            options = self._options
            selected = [i for i, option in enumerate(options) if option.selected]
            multiple = 'multiple' in a
            if not multiple:
                selected = selected[-1:]
                if not selected and _display_size(a) == 1:
                    selected = next(([i] for i, option in enumerate(options) if not option.disabled), [])
            options = tuple(replace(option, selected=i in selected) for i, option in enumerate(options))
            state.update(options=options, selected_indices=tuple(selected), multiple=multiple,
                         value=options[selected[0]].value if selected else '')
        elif tag == 'progress':
            maximum = _finite(a.get('max'), 1.)
            if maximum <= 0:
                maximum = 1.
            value = max(0., min(maximum, _finite(a.get('value'), 0.)))
            state.update(minimum=0., maximum=maximum, value=_serialize_number(value),
                         fraction=value/maximum if 'value' in a else None)
        elif tag == 'meter':
            minimum = _finite(a.get('min'), 0.)
            maximum = max(minimum, _finite(a.get('max'), 1.))
            value = max(minimum, min(maximum, _finite(a.get('value'), 0.)))
            state.update(minimum=minimum, maximum=maximum, value=_serialize_number(value),
                         fraction=_fraction(value,minimum,maximum))
        return ControlSpec(**state)


@dataclass(eq=False)
class _Element:
    tag: str
    attrs: dict = field(default_factory=dict)
    raw: str = ''
    spelling: str = ''
    children: list = field(default_factory=list)
    parent: _Element | None = None
    changed: bool = False


class _Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = _Element(''); self.stack = [self.root]; self.nodes = []

    def handle_starttag(self, tag, attrs):
        if len(self.nodes) >= 20_000 or len(self.stack) > 256:
            raise MermaidError('Control normalization budget exceeded', code='LABEL_BUDGET')
        if tag in {'option', 'optgroup'}:
            while self.stack[-1].tag == 'option' or (tag == 'optgroup' and self.stack[-1].tag == 'optgroup'):
                self.stack.pop()
        raw = self.get_starttag_text(); m = re.match(r'<([^\s/>]+)', raw)
        node = _Element(tag, _attributes(attrs), raw, m[1] if m else tag, parent=self.stack[-1])
        self.stack[-1].children.append(node); self.nodes.append(node)
        if tag not in _VOID:
            self.stack.append(node)
        if tag == 'textarea':
            # Textarea is RCDATA: apparent input/fieldset tags inside it are
            # text, never participants in radio/disabled normalization.
            self.set_cdata_mode('textarea')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, text):
        self.stack[-1].children.append(text)

    def handle_entityref(self, name):
        self.handle_data('&' + name + ';')

    def handle_charref(self, name):
        self.handle_data('&#' + name + ';')

    def handle_comment(self, text):
        self.handle_data('<!--' + text + '-->')


def _fieldset_disabled(node):
    child = node; parent = node.parent
    while parent is not None:
        if parent.tag == 'fieldset' and 'disabled' in parent.attrs:
            first_legend = next((c for c in parent.children if isinstance(c, _Element) and c.tag == 'legend'), None)
            if child is not first_legend:
                return True
        child, parent = parent, parent.parent
    return False


def normalize_control_labels(labels: Sequence[str]) -> tuple[str, ...]:
    """Resolve one diagram's safe labels in caller-supplied host tree order.

    Each label has its own synthetic boundary: an unclosed form or fieldset
    cannot escape into another label. Boundaries are never serialized and do
    not create form owners. IDs and unowned radio groups share the diagram's
    scope. All state is local to this call, never a global or session cache.
    """
    if isinstance(labels, (str, bytes)) or not isinstance(labels, Sequence) or not all(isinstance(label, str) for label in labels):
        raise MermaidError('Control labels must be a sequence of strings', code='INVALID_HTML_CONTROL')
    labels = tuple(labels)
    if not any(re.search(r'<(?:input|button|select|textarea|meter|progress|fieldset)\b', label, re.I) for label in labels):
        return labels
    parsers = []
    nodes = []
    for text in labels:
        parser = _Markup(); parser.feed(text); parser.close()
        parsers.append(parser); nodes.extend(parser.nodes)
        if len(nodes) > 20_000:
            raise MermaidError('Diagram control normalization budget exceeded', code='LABEL_BUDGET')
    ids = {}
    for node in nodes:
        if 'id' in node.attrs:
            ids.setdefault(node.attrs['id'], node)
    checked = {}
    for node in nodes:
        if node.tag in {'input', 'button', 'select', 'textarea', 'fieldset'} and _fieldset_disabled(node):
            node.attrs['disabled'] = ''; node.changed = True
        if node.tag != 'input' or node.attrs.get('type', '').lower() != 'radio' or not node.attrs.get('name'):
            continue
        if 'form' in node.attrs:
            owner = ids.get(node.attrs['form'])
            if owner is not None and owner.tag != 'form':
                owner = None
        else:
            owner = node.parent
            while owner is not None and owner.tag != 'form':
                owner = owner.parent
        if 'checked' in node.attrs:
            key = (owner, node.attrs['name'])
            previous = checked.get(key)
            if previous is not None:
                del previous.attrs['checked']; previous.changed = True
            checked[key] = node

    def serialize(node):
        if isinstance(node, str):
            return node
        start = node.raw if not node.changed else '<' + node.spelling + ''.join(
            ' ' + k + '="' + html.escape(v, quote=True) + '"' for k, v in node.attrs.items()) + '>'
        if node.tag in _VOID:
            return start
        return start + ''.join(serialize(c) for c in node.children) + ('</' + node.spelling + '>' if node.tag else '')
    return tuple(''.join(serialize(node) for node in parser.root.children)
                 if any(node.changed for node in parser.nodes) else original
                 for parser, original in zip(parsers, labels))


def normalize_control_markup(text):
    """Resolve one already-sanitized label using the diagram-scoped algorithm.

    For cross-label radio/form ownership the caller must use
    normalize_control_labels before independently measuring the labels.
    """
    return normalize_control_labels((text,))[0]
