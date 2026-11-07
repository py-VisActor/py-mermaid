"""Locked Treemap Langium semantics with VChart native hierarchy geometry."""
from dataclasses import dataclass, replace
import re
import math
from ...runtime.common import make_diagram, config_dict, error
from ..modeling._support import styles, node_style, label_style as inherit_label_style
from ..charts._vchart_bridge import geometry


@dataclass(frozen=True)
class TreemapNode:
    id: str
    name: str
    value: float | None
    parent: str | None
    children: tuple[str, ...] = ()
    class_selector: str = ''
    styles: tuple = ()


@dataclass(frozen=True)
class Treemap:
    nodes: tuple[TreemapNode, ...]
    classes: tuple = ()
    title: str = ''
    acc_title: str = ''
    acc_description: str = ''


def _records(text):
    """STRING2 can span line breaks; indentation counts source code units."""
    position = 0
    for match in re.finditer(r'[^\n]*(?:\n|$)', text):
        if not match[0]:
            continue
        yield match.start(), match[0].rstrip('\r\n')


def parse(document, config):
    meta = {}
    records = list(_records(document.cleaned))
    first = next((i for i, (_, s) in enumerate(records) if s.strip() and not s.lstrip().startswith('%%')), None)
    if first is None or records[first][1].strip() not in ('treemap', 'treemap-beta'):
        raise error(document, 0, 'Expected treemap or treemap-beta')
    definitions = {}
    raw = []
    i = first + 1
    while i < len(records):
        offset, line = records[i]
        i += 1
        if not line.strip() or line.lstrip().startswith('%%'):
            continue
        level = len(line) - len(line.lstrip(' \t'))
        content = line[level:]
        metadata = re.match(r'^(title(?:[\t ]|$)|accTitle[\t ]*:|accDescr[\t ]*[:{])', content)
        if metadata:
            if content.startswith('accDescr') and '{' in content:
                raw = content.split('{', 1)[1]
                while '}' not in raw:
                    if i == len(records):
                        raise error(document, offset, 'Unterminated accessible description')
                    raw += '\n' + records[i][1]
                    i += 1
                value = raw.split('}', 1)[0]
                value = '\n'.join(re.sub(r'[\t ]{2,}', ' ', s.strip()) for s in value.splitlines())
                meta['accdescr'] = re.sub(r'[\r\n]{2,}', '\n', value)
            else:
                key = 'title' if content.startswith('title') else 'acctitle' if content.startswith('accTitle') else 'accdescr'
                value = content[5:] if key == 'title' else content.split(':', 1)[1]
                meta[key] = re.sub(r'[\t ]{2,}', ' ', value.split('%%', 1)[0].strip())
            continue
        if content.startswith('classDef'):
            match = re.fullmatch(r'classDef\s+([A-Za-z_]\w+)(?:\s+([^;\r\n]*))?;?\s*(?:%%.*)?', content)
            if not match:
                raise error(document, offset, 'Invalid treemap classDef')
            definitions.setdefault(match[1], [])
            definitions[match[1]].extend(styles(match[2] or ''))
            continue
        if not content.startswith(('"', "'")):
            raise error(document, offset + level, 'Treemap names must be quoted')
        quote = content[0]
        end = content.find(quote, 1)
        while end < 0:
            if i == len(records):
                raise error(document, offset + level, 'Unterminated treemap name')
            content += '\n' + records[i][1]
            i += 1
            end = content.find(quote, 1)
        name = content[1:end]
        tail = content[end + 1:].split('%%', 1)[0].strip()
        selector = ''
        selected = re.search(r':::\s*([A-Za-z_]\w*)\s*$', tail)
        if selected:
            selector = selected[1]
            tail = tail[:selected.start()].strip()
        value = None
        if tail:
            match = re.fullmatch(r'[:,]\s*([0-9_.,]+)', tail)
            if not match:
                raise error(document, offset + level + end + 1, 'Expected treemap : numeric value')
            # The source NUMBER2 converter is parseFloat(input.replace(/,/g,'')),
            # not Python float accepting arbitrary underscore separators.
            numeric = re.match(r'(?:\d+\.?\d*|\.\d+)', match[1].replace(',', ''))
            value = float(numeric[0]) if numeric else float('nan')
        raw.append((level, name, value, selector))
    nodes = []
    stack = []
    for level, name, value, selector in raw:
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1] if stack else None
        id = 'treemap-' + str(len(nodes))
        nodes.append(TreemapNode(id, name, value, parent, (), selector,
                                 tuple(definitions.get(selector, ()))))
        if value is None:
            stack.append((level, id))
    children = {}
    for node in nodes:
        children.setdefault(node.parent, []).append(node.id)
    nodes = [replace(node, children=tuple(children.get(node.id, ()))) for node in nodes]
    return make_diagram('treemap', document, config, Treemap(tuple(nodes),
                        tuple((k, tuple(v)) for k, v in definitions.items()),
                        meta.get('title', document.title or ''), meta.get('acctitle', ''), meta.get('accdescr', '')))


async def build(diagram, painter):
    cfg = config_dict(diagram)
    conf = cfg.get('treemap') or {}
    model = diagram.model
    width = conf.get('nodeWidth', 0) * 10 or 960
    height = conf.get('nodeHeight', 0) * 10 or 500
    title_height = 30 if model.title else 0
    by_id = {n.id: n for n in model.nodes}
    def record(node):
        return {'id': node.id, 'value': node.value or 0,
                'children': [record(by_id[id]) for id in node.children]}
    rows = [record(n) for n in model.nodes if n.parent is None]
    boxes = geometry('treemap', diagram.source, rows, width, height - title_height,
                     padding=conf.get('padding', 10), header=25)
    value_format = conf.get('valueFormat') or ','
    def value_text(value):
        if not value:
            return ''
        if value_format == ',':
            return format(int(value), ',') if float(value).is_integer() else format(value, ',g')
        if not re.fullmatch(r'[ +\-]?(?:\d{1,3})?,?(?:\.\d{1,2})?[fge%]', value_format):
            raise error(diagram.source, 0, 'VChart embedding does not implement this D3 valueFormat: ' + value_format,
                        'UNSUPPORTED_VCHART_OPTION')
        return format(value, value_format)
    # Reject unsupported format before emitting any node, even on empty data.
    value_text(1)
    theme = cfg.get('themeVariables') or {}
    palette = [theme.get('cScale' + str(i), '#ECECFF') for i in range(12)]
    text_colors = [theme.get('cScaleLabel' + str(i), theme.get('textColor', '#333')) for i in range(12)]
    peers = [theme.get('cScalePeer' + str(i), '#9370DB') for i in range(12)]
    # d3 ordinal scales are populated by descendants() (breadth first), with
    # the synthetic root consuming the first transparent background entry.
    weights={entry['id']:entry['value'] for entry in boxes}
    queue=sorted((n for n in model.nodes if n.parent is None),key=lambda n:-weights[n.id])
    ordered=[]
    while queue:
        node=queue.pop(0);ordered.append(node)
        queue.extend(sorted((by_id[id] for id in node.children),key=lambda n:-weights[n.id]))
    section_names=list(dict.fromkeys(n.name for n in ordered if n.children))
    section_index={name:i%12 for i,name in enumerate(section_names)}
    label_names=list(dict.fromkeys(section_names+[n.name for n in ordered if not n.children]))
    color_index={name:i%12 for i,name in enumerate(label_names)}
    if model.title:
        painter.text(model.title, width / 2, 5, align='center', role='title',
                     color=theme.get('titleColor', '#333'), html=False)
    for entry in boxes:
        node = by_id[entry['id']]
        x0, y0, x1, y1 = entry['box']
        y0 += title_height
        y1 += title_height
        index = color_index[node.name]
        paint_name=node.name if entry['section'] else by_id[node.parent].name if node.parent else None
        paint_index=section_index.get(paint_name)
        fill=palette[paint_index] if paint_index is not None else 'transparent'
        border=peers[paint_index] if entry['section'] and paint_index is not None else fill
        # The pinned source assigns a transparent synthetic-root palette slot
        # but still assigns its first leaf white text (for colored tiles).
        # Preserve transparent paint; use readable host text only for this
        # absent-parent-fill default. Explicit class/inline color still wins.
        default_text=theme.get('textColor','#333') if not entry['section'] and paint_index is None else text_colors[index]
        style = node_style(painter, cfg, ('treemapSection' if entry['section'] else 'treemapNode',),
                           node.id, inline=node.styles, fill=fill, stroke=border,
                           color=default_text, base_extra={'stroke_width': 2 if entry['section'] else 3,
                           'fill_opacity': .6 if entry['section'] else .3,
                           'stroke_opacity': .4 if entry['section'] else 1})
        painter.rect(x0, y0, x1 - x0, y1 - y0, style=style, id=node.id,
                     role='treemap-section' if entry['section'] else 'treemap-leaf')
        text_style = inherit_label_style(style)
        label = node.name
        if entry['section'] and conf.get('showValues', True):
            painter.text(value_text(entry['value']), x1 - 6, y0 + 6, align='right', size=10,
                         color=text_style.text_color, italic=True, html=False, id=node.id + '-value',
                         clip=(x0, y0, max(0, x1 - x0), min(25, y1 - y0)))
        leaf_count = sum(not b['section'] for b in boxes)
        font_size = 12 if entry['section'] else 16 if leaf_count > 20 else 38
        if not entry['section']:
            aw, ah = max(0, x1 - x0 - 8), max(0, y1 - y0 - 8)
            value = value_text(node.value or 0) if conf.get('showValues', True) else ''
            minimum = 4 if leaf_count > 20 else 8
            while font_size > minimum and (painter.measure(label, size=font_size, html=False).width > aw
                                            or font_size * (2 if value else 1) + 2 > ah):
                font_size -= 1
            while label and painter.measure(label, size=font_size, html=False).width > aw:
                label = label[:-1]
            if not label or ah < font_size:
                label = ''
            elif value and ah >= font_size * 2 + 2:
                label += '\n' + value
        label_style = painter.style((), tag='text', id=node.id + '-label',
                                    base={'text_color': text_style.text_color,
                                          'font_size': font_size,
                                          'font_weight': 'bold' if entry['section'] else 'normal'})
        # Leaf labels are centered independently from their smaller values.
        if not entry['section']:
            label=node.name if label else ''
            label_box=painter.measure(label,style=label_style,html=False)
            if label:
                painter.text(label_box,(x0+x1)/2,(y0+y1)/2-label_box.height/2,align='center',style=label_style,id=node.id+'-label',html=False,clip=(x0,y0,x1-x0,y1-y0))
                value=value_text(node.value or 0) if conf.get('showValues',True) else ''
                if value:
                    value_size=max(4 if leaf_count>20 else 6,min(14 if leaf_count>20 else 28,int(font_size*.6+.5)))
                    painter.text(value,(x0+x1)/2,(y0+y1)/2+font_size/2+2,align='center',size=value_size,color=text_style.text_color,id=node.id+'-value',html=False,clip=(x0,y0,x1-x0,y1-y0))
            continue
        painter.text(label, x0 + 6, y0 + 6, style=label_style, id=node.id + '-label', html=False,
                     clip=(x0, y0, max(0, x1 - x0), min(25, y1 - y0) if entry['section'] else max(0, y1 - y0)))
    return painter.finish(width=width, height=height, padding=0,
                          layout={'kind': 'treemap', 'provider': 'py_vchart.layouts.treemap', 'nodes': boxes})
