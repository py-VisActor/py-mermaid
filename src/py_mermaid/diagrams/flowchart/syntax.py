"""Pure lexical edge values from flow.jison and FlowDB.destructLink."""
from dataclasses import dataclass
import re

DIRECT = (
    re.compile(r'[xo<]?--+[-xo>]'),
    re.compile(r'[xo<]?==+[=xo>]'),
    re.compile(r'[xo<]?-?\.+-[xo>]?'),
    re.compile(r'~~~+'),
)
START = (re.compile(r'[xo<]?--'), re.compile(r'[xo<]?=='), re.compile(r'[xo<]?-\.'))


def match_direct(text, index):
    matches = [pattern.match(text, index) for pattern in DIRECT]
    return max((match for match in matches if match), key=lambda match: match.end(), default=None)


def destruct_link(ending, beginning=None):
    """Keep the source's seven edge types rather than invent mixed markers."""
    ending = ending.strip()
    line = ending[:-1]
    edge_type = {'x': 'arrow_cross', '>': 'arrow_point', 'o': 'arrow_circle'}.get(ending[-1], 'arrow_open')
    opposite = {'x': 'x', '>': '<', 'o': 'o'}.get(ending[-1])
    if opposite and ending.startswith(opposite):
        edge_type = 'double_' + edge_type
        line = line[1:]
    stroke = 'thick' if line.startswith('=') else 'invisible' if line.startswith('~') else 'normal'
    length = len(line) - 1
    if '.' in line:
        stroke, length = 'dotted', line.count('.')
    if beginning:
        beginning = beginning.strip()
        start_type = {'<': 'arrow_point', 'x': 'arrow_cross', 'o': 'arrow_circle'}.get(beginning[0], 'arrow_open')
        start_stroke = 'dotted' if '.' in beginning else 'thick' if '=' in beginning else 'normal'
        if start_stroke != stroke or start_type != 'arrow_open' and start_type != edge_type:
            return 'INVALID', 'INVALID', None, 'none', 'point'
        edge_type = edge_type if start_type == 'arrow_open' else 'double_' + start_type
    marker = edge_type.removeprefix('double_').removeprefix('arrow_')
    marker = 'none' if marker == 'open' or stroke == 'invisible' else marker
    return edge_type, stroke, min(length, 10), marker if edge_type.startswith('double_') else 'none', marker


@dataclass(frozen=True)
class ParsedLink:
    start: int
    label: str = ''
    label_span: object = None
    label_kind: str = 'text'
    raw_label: str | None = None
    user_id: str | None = None
    edge_type: str = 'arrow_point'
    stroke: str = 'normal'
    length: int | None = 1
    marker_start: str = 'none'
    marker_end: str = 'point'
