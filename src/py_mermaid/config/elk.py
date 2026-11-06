"""Public Mermaid ELK configuration, preserving unspecified strategy keys."""
from collections.abc import Mapping
import math
from py_mermaid.model.flowchart import MermaidError

LAYOUTS = frozenset(('elk', 'elk.stress', 'elk.force', 'elk.mrtree',
                     'elk.sporeOverlap', 'elk.box', 'elk.rectpacking'))
CURVES = frozenset(('basis', 'bumpX', 'bumpY', 'cardinal', 'catmullRom', 'linear',
                    'monotoneX', 'monotoneY', 'natural', 'step', 'stepAfter', 'stepBefore', 'rounded'))
DEFAULTS = dict(mergeEdges=False, straightenEdges=True, lineHops=True, preset='default',
                layeringLayerBound=4, forceNodeModelOrder=False, considerModelOrder='NODES_AND_EDGES',
                keepEntryNodeOnTop=False, orientFeedbackEdges=True)
ENUMS = {
    'nodePlacementStrategy': ('SIMPLE', 'NETWORK_SIMPLEX', 'LINEAR_SEGMENTS', 'BRANDES_KOEPF'),
    'nodePlacementAlignment': ('NONE', 'LEFTUP', 'LEFTDOWN', 'RIGHTUP', 'RIGHTDOWN', 'BALANCED'),
    'preset': ('default', 'legacy', 'modelOrder', 'depthFirst'),
    'layeringStrategy': ('NETWORK_SIMPLEX', 'LONGEST_PATH', 'LONGEST_PATH_SOURCE', 'COFFMAN_GRAHAM',
                         'MIN_WIDTH', 'STRETCH_WIDTH', 'INTERACTIVE'),
    'cycleBreakingStrategy': ('GREEDY', 'DEPTH_FIRST', 'INTERACTIVE', 'MODEL_ORDER', 'GREEDY_MODEL_ORDER'),
    'considerModelOrder': ('NONE', 'NODES_AND_EDGES', 'PREFER_EDGES', 'PREFER_NODES'),
}


def validate_elk(value):
    if not isinstance(value, Mapping):
        raise MermaidError('elk must be a mapping', code='INVALID_CONFIG')
    for key, item in value.items():
        if key not in DEFAULTS and key not in ENUMS:
            raise MermaidError(f'Unsupported public ELK configuration elk.{key}', code='UNSUPPORTED_CONFIG')
        if key in ENUMS:
            valid = item in ENUMS[key]
        elif key == 'lineHops':
            valid = isinstance(item, bool) or item in ('arc', 'gap')
        elif key == 'layeringLayerBound':
            valid = not isinstance(item, bool) and isinstance(item, (float, int)) and math.isfinite(item)
        else:
            valid = isinstance(item, bool)
        if not valid:
            raise MermaidError(f'Invalid public ELK configuration elk.{key}', code='INVALID_CONFIG')
    return dict(value)
