"""Fixed defaults and native static configuration precedence across diagram kinds."""
from copy import deepcopy
from importlib.resources import files
import json
from collections.abc import Mapping
from ..config.values import thaw_value, assign_with_depth, merge_layers
from ..config.flowchart import sanitize_directive, SECURE
from ..config.themes import get_theme_variables, THEMES
from ..model.flowchart import MermaidError

CONFIG_KEYS={'classDiagram':'class','stateDiagram':'state','xychart':'xyChart',
             'railroadEbnf':'railroad','railroadAbnf':'railroad','railroadPeg':'railroad'}


def defaults():
    return json.loads(files('py_mermaid').joinpath('data/diagram_defaults.json').read_text('utf-8'))['config']


def resolve(document, kind, site=None):
    if site is not None and not isinstance(site,Mapping):raise MermaidError('config must be a mapping',code='INVALID_CONFIG')
    base=defaults();key=CONFIG_KEYS.get(kind,kind);original=deepcopy(dict(site or {}))
    cfg=assign_with_depth(deepcopy(base),original)
    secure=cfg.get('secure',list(SECURE))
    if not isinstance(secure,(tuple,list)):raise MermaidError('secure must be an array',code='INVALID_CONFIG')
    combined={}
    for name,value in document.config_layers:
        if name in ('frontmatter','directive'):merge_layers(combined,thaw_value(value))
    directive=sanitize_directive(combined,secure)
    cfg=assign_with_depth(cfg,directive)
    for prop in ('theme','look','layout'):
        for layer in (directive,original,base):
            scoped=layer.get(key,{})
            candidates=(scoped.get(prop) if isinstance(scoped,Mapping) else None,layer.get(prop))
            usable=next((value for value in candidates if value is not None and
                         (prop!='theme' or isinstance(value,str) and value in (*THEMES,'null'))),None)
            if usable is not None:
                cfg[prop]=usable;break
    if cfg.get('theme') not in (*THEMES,'null'):cfg['theme']='default'
    if cfg.get('look') not in ('classic','neo','handDrawn'):raise MermaidError('Unsupported look',code='INVALID_CONFIG')
    layout=cfg.get('layout','elk')
    from .layouts import registered_layouts
    if layout not in (*registered_layouts(),'cose-bilkent','tidy-tree','swimlane'):
        raise MermaidError('Unregistered native layout',code='UNSUPPORTED_CONFIG')
    overrides=deepcopy(original.get('themeVariables') or {})
    assign_with_depth(overrides,directive.get('themeVariables') or {})
    if original.get('fontFamily') and 'fontFamily' not in overrides:overrides['fontFamily']=original['fontFamily']
    cfg['themeVariables']=get_theme_variables(cfg['theme'],overrides)
    cfg.setdefault(key,{})
    cfg['_diagramKind']=kind;cfg['_diagramConfigKey']=key
    cfg['_explicitLayout']=any('layout' in layer or isinstance(layer.get(key),Mapping) and 'layout' in layer[key] for layer in (original,directive))
    cfg['_explicitRootLayout']=any('layout' in layer for layer in (original,directive))
    return cfg


def font_descriptor(config, section, role):
    values=config.get(section,{})
    return {'fontFamily':values.get(role+'FontFamily',config.get('fontFamily','sans-serif')),
            'fontSize':values.get(role+'FontSize',config.get('fontSize',16)),
            'fontWeight':values.get(role+'FontWeight','normal')}
