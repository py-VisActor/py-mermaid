"""Venn Jison/DB semantics and VChart circle/intersection layout embedding."""
from dataclasses import dataclass
import itertools
import math
import re
from ...runtime.common import make_diagram, config_dict, error
from ..charts._vchart_bridge import geometry
from ..modeling._support import number
from ...config.colors import darken, lighten, isDark


@dataclass(frozen=True)
class VennArea:
    sets: tuple[str, ...]
    size: float
    label: str | None = None


@dataclass(frozen=True)
class VennText:
    sets: tuple[str, ...]
    id: str
    label: str | None = None


@dataclass(frozen=True)
class Venn:
    areas: tuple[VennArea, ...]
    texts: tuple[VennText, ...]
    styles: tuple
    title: str = ''


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    offset: int
    indent: int = 0


def _tokens(document):
    text = document.cleaned
    pattern = re.compile(r'(?i:title)\s[^#\n;]+|%%[^\n]*|[\r\n]+|[ \t]+|\["[^"]*"\]|\[[^\]"]+\]|"[^"]*"|'
                         r'rgba?\(\s*[0-9.]+\s*(?:,\s*[0-9.]+\s*){2,3}\)|'
                         r'\#[0-9a-fA-F]{3,8}|[+-]?(?:\d+(?:\.\d+)?|\.\d+)|'
                         r'[A-Za-z_][A-Za-z0-9_-]*|[:,]')
    position = 0
    bol = True
    indent = 0
    tokens = []
    for match in pattern.finditer(text):
        if match.start() != position:
            raise error(document, position, 'Invalid Venn token')
        position = match.end()
        raw = match[0]
        if raw.startswith('%%'):
            continue
        if raw.isspace():
            if '\n' in raw or '\r' in raw:
                tokens.append(_Token('newline', raw, match.start()))
                bol = True
                indent = 0
            elif bol:
                indent += len(raw)
            continue
        kind = 'id'
        value = raw
        if re.match(r'(?i:title)\s',raw):
            kind = 'title'
        elif raw.startswith('['):
            kind = 'label'
            value = raw[2:-2] if raw.startswith('["') else raw[1:-1].strip()
        elif raw.startswith('"'):
            kind = 'string'
            value = raw[1:-1]
        elif re.fullmatch(r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)', raw):
            kind = 'number'
        elif raw in (':', ','):
            kind = raw
        elif raw.lower() in ('venn-beta', 'set', 'union', 'text', 'style'):
            kind = raw.lower()
        elif raw.startswith('#') or raw.lower().startswith(('rgb(', 'rgba(')):
            kind = 'color'
        tokens.append(_Token(kind, value, match.start(), indent if bol else 0))
        bol = False
    if position != len(text):
        raise error(document, position, 'Invalid Venn token')
    return tokens


def parse(document, config):
    tokens = _tokens(document)
    index = 0
    while index < len(tokens) and tokens[index].kind == 'newline':
        index += 1
    if index == len(tokens) or tokens[index].kind != 'venn-beta':
        raise error(document, 0, 'Expected venn-beta')
    index += 1
    areas, texts, styles = [], [], []
    known = set()
    current = None
    indent_mode = False
    title = document.title or ''
    def take(kind=None):
        nonlocal index
        if index >= len(tokens):
            raise error(document, len(document.cleaned), 'Unexpected end of Venn input')
        token = tokens[index]
        if kind is not None and token.kind != kind:
            raise error(document, token.offset, 'Expected ' + kind)
        index += 1
        return token
    def identifiers():
        values = []
        while True:
            token = take()
            if token.kind not in ('id', 'string'):
                raise error(document, token.offset, 'Expected Venn identifier')
            values.append(token.value.strip() if token.kind == 'id' else token.value)
            if index >= len(tokens) or tokens[index].kind != ',':
                return values
            index_plus = index + 1
            if index_plus >= len(tokens) or tokens[index_plus].kind not in ('id', 'string'):
                return values
            take(',')
    while index < len(tokens):
        token = take()
        if token.kind == 'newline':
            continue
        if token.kind == 'title':
            indent_mode = False
            end = document.cleaned.find('\n', token.offset)
            if end < 0:
                end = len(document.cleaned)
            title = document.cleaned[token.offset + 6:end].split(';', 1)[0].split('#', 1)[0]
            while index < len(tokens) and tokens[index].offset < end:
                index += 1
            continue
        if token.kind in ('set', 'union'):
            ids = identifiers()
            if token.kind == 'set' and len(ids) != 1:
                raise error(document, token.offset, 'set requires one identifier')
            if token.kind == 'union':
                if len(ids) < 2:
                    raise error(document, token.offset, 'union requires multiple identifiers')
                unknown = [id for id in ids if id not in known]
                if unknown:
                    raise error(document, token.offset, 'unknown set identifier: ' + ', '.join(unknown))
            label = take('label').value if index < len(tokens) and tokens[index].kind == 'label' else None
            size = 10 / len(ids) ** 2
            if index < len(tokens) and tokens[index].kind == ':':
                take(':')
                size = float(take('number').value)
            current = tuple(sorted(ids))
            areas.append(VennArea(current, size, label))
            if len(ids) == 1:
                known.add(ids[0])
            indent_mode = True
        elif token.kind == 'text':
            if token.indent and indent_mode:
                ids = current
            else:
                ids = tuple(sorted(identifiers()))
                indent_mode = False
            if ids is None:
                raise error(document, token.offset, 'text requires set')
            item = take()
            if item.kind not in ('id', 'string', 'number'):
                raise error(document, item.offset, 'Expected Venn text identifier')
            label = take('label').value if index < len(tokens) and tokens[index].kind == 'label' else None
            texts.append(VennText(tuple(ids), item.value, label))
        elif token.kind == 'style':
            ids = tuple(sorted(identifiers()))
            entries = []
            while index < len(tokens) and tokens[index].kind == 'id':
                key = take('id').value
                take(':')
                value = []
                while index < len(tokens) and tokens[index].kind in ('id', 'number', 'color', 'string'):
                    value.append(take().value)
                if not value:
                    raise error(document, token.offset, 'Expected Venn style value')
                entries.append((key, ' '.join(value)))
                if index < len(tokens) and tokens[index].kind == ',':
                    take(',')
                else:
                    break
            if not entries:
                raise error(document, token.offset, 'Expected Venn styles')
            styles.append((ids, tuple(entries)))
            indent_mode = False
        else:
            raise error(document, token.offset, 'Expected Venn set, union, text or style')
    return make_diagram('venn', document, config, Venn(tuple(areas), tuple(texts), tuple(styles), title))


async def build(diagram, painter):
    cfg = config_dict(diagram)
    conf = cfg.get('venn') or {}
    theme = cfg.get('themeVariables') or {}
    model = diagram.model
    width, height = conf.get('width', 800), conf.get('height', 450)
    scale = width / 1600
    title_height = 48 * scale if model.title else 0
    areas = [(a.sets, a.size) for a in model.areas]
    # Source ensurePairwiseSubsets adds geometry-only pairs for N-way regions.
    present = {a.sets for a in model.areas}
    sizes = {a.sets[0]: a.size for a in model.areas if len(a.sets) == 1}
    for area in model.areas:
        if len(area.sets) >= 3:
            for pair in itertools.combinations(area.sets, 2):
                if pair not in present:
                    areas.append((pair, min(sizes.get(pair[0], 10), sizes.get(pair[1], 10)) / 4))
                    present.add(pair)
    if len(sizes) > 3:
        raise error(diagram.source, 0, 'VChart Venn currently supports at most three singleton sets', 'UNSUPPORTED_VCHART_OPTION')
    if not areas:
        return painter.finish(width=width, height=height, padding=0, layout={'kind': 'venn', 'regions': ()})
    result = geometry('venn', diagram.source, areas, width, height - title_height, padding=conf.get('padding', 15))
    regions = {r['sets']: r for r in result['regions']}
    style_map = {}
    for targets, entries in model.styles:
        style_map.setdefault(targets, {}).update(entries)
    colors = [theme['venn' + str(i)] for i in range(1, 9) if theme.get('venn' + str(i))]
    fallback = theme.get('primaryColor', '#ECECFF')
    dark_theme = isDark(theme.get('background') or '#f4f4f4')
    painter.rough_enabled = cfg.get('look') == 'handDrawn'
    if model.title:
        painter.text(model.title, width / 2, 32 * scale, align='center', size=32 * scale,
                     color=theme.get('vennTitleTextColor', theme.get('titleColor', '#333')), role='title', html=False)
    for i, area in enumerate(model.areas):
        region = regions[area.sets]
        style = style_map.get(area.sets, {})
        singleton = len(area.sets) == 1
        fill = style.get('fill', colors[i % len(colors)] if colors else fallback) if singleton else style.get('fill', 'none')
        resolved = painter.style(('venn-circle' if singleton else 'venn-intersection',), tag='path',
                                 id='venn-area-' + str(i), base={'fill': fill,
                                 'fill_opacity': number(style.get('fill-opacity'), .1 if singleton else 1),
                                 'stroke': style.get('stroke', fill) if singleton else 'none',
                                 'stroke_width': number(style.get('stroke-width'), 5 * scale) if singleton else 0})
        if singleton:
            x, y, radius = region['circles'][0]
            painter.ellipse(x, y + title_height, radius, radius, style=resolved, id='venn-area-' + str(i),
                            rough_options={'roughness': .7, 'fillStyle': 'hachure', 'fillWeight': 2,
                                           'hachureGap': 8, 'hachureAngle': -41 + i * 60})
        elif region['path']:
            painter.path(region['path'], transform=(1, 0, 0, 1, 0, title_height),
                         style=resolved, id='venn-area-' + str(i),
                         rough_options={'roughness': .7, 'fillStyle': 'cross-hatch',
                                        'fillWeight': 2, 'hachureGap': 6, 'hachureAngle': 60})
        label = area.label if area.label is not None else area.sets[0] if singleton else ''
        if label:
            x, y = region['center']
            text_color = (lighten(fill, 30) if dark_theme else darken(fill, 30)) if singleton else theme.get('vennSetTextColor', theme.get('primaryTextColor', '#333'))
            painter.text(label, x, y + title_height, align='center', size=48 * scale,
                         color=style.get('color', text_color),
                         id='venn-label-' + str(i), html=False)
    grouped = {}
    for node in model.texts:
        grouped.setdefault(node.sets, []).append(node)
    for sets, nodes in grouped.items():
        region = regions.get(sets)
        if region is None:
            continue  # Original renderTextNodes skips areas not present in layout.
        x, y = region['center']
        minimum = min((r for _, _, r in region['circles']), default=0)
        inner = min((r - math.hypot(x - cx, y - cy) for cx, cy, r in region['circles']), default=0)
        inner = max(0, inner) or minimum * .6
        iw, ih = max(80 * scale, inner * 1.9), max(60 * scale, inner * 1.9)
        original = next((a for a in model.areas if a.sets == sets), None)
        offset = (min(32 * scale, inner * .25) if original and original.label else 0) + (30 * scale if len(nodes) <= 2 else 0)
        cols = max(1, math.ceil(math.sqrt(len(nodes))))
        rows = math.ceil(len(nodes) / cols)
        cw, ch = iw / cols, ih / rows
        if conf.get('useDebugLayout'):
            painter.ellipse(x, y + title_height, inner, inner, fill='none', stroke='purple', line_width=1.5 * scale)
        for i, node in enumerate(nodes):
            xx = x - iw / 2 + cw * (i % cols + .5)
            yy = y - ih / 2 + ch * (i // cols + .5) + offset + title_height
            if conf.get('useDebugLayout'):
                painter.rect(xx - cw / 2, yy - ch / 2, cw, ch, fill='none', stroke='teal',
                             line_width=scale, dash=(4 * scale, 3 * scale))
            text = re.sub(r'\s+', ' ', node.label if node.label is not None else node.id)
            style = style_map.get((node.id,), {})
            label = painter.measure(text, size=40 * scale, width=cw * .9, html=False)
            painter.text(label, xx, yy - label.height / 2, align='center',
                         color=style.get('color', theme.get('primaryTextColor', '#333')), id=node.id)
    return painter.finish(width=width, height=height, padding=0,
                          layout={'kind': 'venn', 'provider': 'py_vchart.layouts.venn', **result})
