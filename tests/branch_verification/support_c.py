"""Read-only branch inputs and independent elementary geometry; inert import."""
from pathlib import Path
import json
import math
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def cases():
    return json.loads((Path(__file__).with_name('cases-C.json')).read_text('utf-8'))['cases']


def center(box):
    if not isinstance(box, dict):
        return box.x + box.width/2, box.y + box.height/2
    return box['x'] + box['width']/2, box['y'] + box['height']/2


def path_endpoints(path):
    # These probes cover source M/L/H/V/C self/straight message paths only.
    # Reject other path families rather than guessing coordinates.
    tokens = re.findall(r'[MLHVCmlhvc]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', path)
    require = lambda c: c if c else (_ for _ in ()).throw(ValueError('Unsupported message path'))
    position = [0., 0.]; first = None; i = 0
    sizes = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6}
    while i < len(tokens):
        command = tokens[i]; i += 1
        require(command.upper() in sizes)
        size = sizes[command.upper()]
        values = [float(v) for v in tokens[i:i+size]]; i += size
        require(len(values) == size and all(math.isfinite(v) for v in values))
        relative = command.islower(); upper = command.upper()
        if upper == 'H':position[0] = values[0] + (position[0] if relative else 0)
        elif upper == 'V':position[1] = values[0] + (position[1] if relative else 0)
        else:
            position = [values[-2] + (position[0] if relative else 0), values[-1] + (position[1] if relative else 0)]
        if first is None:first = tuple(position)
    require(first is not None)
    return first, tuple(position)


def svg_projection(text):
    root = ET.fromstring(text); actors = {}; messages = []; circles = []; numbers = []; comments = []
    def walk(element, in_defs=False):
        tag = element.tag.rsplit('}', 1)[-1]; in_defs = in_defs or tag == 'defs'
        attrs = element.attrib; classes = attrs.get('class', '').split()
        if not in_defs:
            if 'actor-line' in classes:actors[attrs.get('name', attrs.get('data-id', ''))] = float(attrs['x1'])
            if attrs.get('data-et') == 'message':
                if tag == 'line':start, end = (float(attrs['x1']), float(attrs['y1'])), (float(attrs['x2']), float(attrs['y2']))
                else:start, end = path_endpoints(attrs['d'])
                messages.append({'start':start,'end':end,'markerStart':attrs.get('marker-start',''),'markerEnd':attrs.get('marker-end',''), 'class':attrs.get('class','')})
            if tag == 'circle' and float(attrs.get('r', 0)) == 5:circles.append((float(attrs['cx']), float(attrs['cy'])))
            if tag == 'text' and 'sequenceNumber' in classes:numbers.append((float(attrs['x']), ''.join(element.itertext())))
            if tag == 'text' and 'comment-text' in classes:
                comments.append({'text': ''.join(element.itertext()), 'spans': [dict(e.attrib, text=''.join(e.itertext())) for e in element.iter() if e is not element]})
        for child in element:walk(child, in_defs)
    walk(root)
    return {'actors':actors,'messages':messages,'circles':circles,'numbers':numbers,'comments':comments}


def native_projection(scene):
    trace = scene['trace']
    layout = scene.get('layout', {})
    actors = {name: center(box)[0] for name, box in (layout.get('actors', []) if isinstance(layout, dict) else [])}
    return {'actors':actors,
            'messages':[{'start':path_endpoints(e['path'])[0],'end':path_endpoints(e['path'])[1], 'dash':e.get('dash',[])} for e in trace if e['kind']=='message'],
            'circles':[center(e['box']) for e in trace if e['kind']=='central-connection'],
            'numbers':[(center(e['box'])[0], None) for e in trace if e['kind']=='sequence-number-box'],
            'comments':[{'text':e.get('text',''),'font_weight':e.get('font_weight'),'font_style':e.get('font_style'),'font_family':e.get('font_family'),'baseline':e.get('points',[])} for e in trace if e['kind']=='comment-text'],
            'arrowComponents':{e['semantic_id']:[{'kind':c['kind'],'marker':c.get('marker'),'path':c.get('path','')} for c in trace if c['semantic_id']==e['semantic_id'] and c['kind'] in ('marker','message-arrow')] for e in trace if e['kind']=='message'}}


def logical_arrow_components(components):
    """A cross is two real coincident-center opposite diagonals, not two marks.

    Missing, repeated, parallel or disconnected strokes remain explicit faults.
    No other marker family is deduplicated, and physical paths are retained.
    """
    result=[c for c in components if c.get('marker')!='cross'];cross=[c for c in components if c.get('marker')=='cross']
    if not cross:return result,[]
    # svgDraw.js crosshead is one path with two M/L subpaths. The older
    # generic marker emitted the exact same geometry as two real Paints.
    # Normalize only these two physical encodings, not incomplete crosses.
    if len(cross)==1:
        combined=cross[0].get('path','')
        pieces=re.findall(r'[Mm][^Mm]*',combined)
        if len(pieces)!=2:return result,['cross-requires-two-diagonal-paints']
        cross=[dict(cross[0],path=piece) for piece in pieces]
    if len(cross)!=2:return result,['cross-requires-two-diagonal-paints']
    segments=[]
    try:
        for c in cross:
            if len(re.findall(r'[MLHVCmlhvc]',c.get('path','')))!=2 or not re.fullmatch(r'\s*M[^A-Za-z]*L[^A-Za-z]*\s*',c['path']):
                raise ValueError('Cross must contain one straight segment per paint')
            a,b=path_endpoints(c['path']);dx=b[0]-a[0];dy=b[1]-a[1]
            if abs(dx)<1e-6 or abs(abs(dx)-abs(dy))>1e-6:raise ValueError('Cross stroke is not a diagonal')
            segments.append(((a[0]+b[0])/2,(a[1]+b[1])/2,dx*dy))
        a,b=segments
        if abs(a[0]-b[0])>1e-6 or abs(a[1]-b[1])>1e-6 or a[2]*b[2]>=0:raise ValueError('Cross diagonal centers/slopes differ')
    except (ValueError,KeyError,TypeError):return result,['cross-diagonals-not-a-complete-logical-marker']
    result.append(dict(kind='marker',marker='cross',paths=[c['path'] for c in cross]))
    return result,[]


ABNF_PROBES = (
    ('bare-terminator', 'railroad-abnf-beta\nword = "a";', ['word']),
    ('trailing-comment', 'railroad-abnf-beta\nword = "a"; trailing comment\n', ['word']),
    ('comment-line', 'railroad-abnf-beta\n; comment only\nword = "a";', ['word']),
    ('quoted-semicolon', 'railroad-abnf-beta\nword = "a;b";', ['word']),
    ('two-rules', 'railroad-abnf-beta\nfirst = "a";\nsecond = "b";', ['first','second']),
)
