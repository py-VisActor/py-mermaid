"""Ordered, lazy static-diagram registration from the locked Mermaid detectors.

Registration retains order when replacing an identifier, as in the source
Object-based detector registry. Plugins provide Python parse/build functions;
loading a plugin never executes JavaScript or creates a Canvas object.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from importlib import import_module
import inspect
import re
from threading import RLock

from ..model.flowchart import MermaidError
from ..parsing.preprocess import preprocess_diagram
from .configuration import CONFIG_KEYS, resolve
from .common import error, utf16_length, number


@dataclass(frozen=True)
class Registration:
    id: str
    detector: object
    provider: object


_lock=RLock()
_registrations=OrderedDict()
_ENTRIES=(
    ('flowchart-elk',r'^\s*flowchart-elk',None),
    ('mindmap',r'^\s*mindmap','hierarchy.mindmap'),
    ('architecture',r'^\s*architecture','structures.architecture'),
    ('agentflow',r'^\s*agentflow-beta\b','business.agentflow'),
    ('c4',r'^\s*C4Context|C4Container|C4Component|C4Dynamic|C4Deployment','modeling.c4'),
    ('kanban',r'^\s*kanban','structures.kanban'),
    ('classDiagram',r'^\s*classDiagram','modeling.class_diagram'),
    ('er',r'^\s*erDiagram','modeling.er'),
    ('gantt',r'^\s*gantt','temporal.gantt'),
    ('info',r'^\s*info','info'),
    ('pie',r'^\s*pie','charts.pie'),
    ('requirement',r'^\s*requirement(Diagram)?','modeling.requirement'),
    ('sequence',r'^\s*sequenceDiagram','sequence'),
    ('swimlane',r'^\s*swimlane-beta\b','business.swimlane'),
    ('flowchart-v2',r'^\s*(graph|flowchart)',None),
    ('timeline',r'^\s*timeline','temporal.timeline'),
    ('gitGraph',r'^\s*gitGraph','temporal.gitgraph'),
    ('stateDiagram',r'^\s*stateDiagram','modeling.state_diagram'),
    ('journey',r'^\s*journey','temporal.journey'),
    ('quadrantChart',r'^\s*quadrantChart','charts.quadrant'),
    ('sankey',r'^\s*sankey(-beta)?','flows.sankey'),
    ('packet',r'^\s*packet(-beta)?','structures.packet'),
    ('xychart',r'^\s*xychart(-beta)?','charts.xychart'),
    ('block',r'^\s*block(-beta)?','structures.block'),
    ('eventmodeling',r'^\s*eventmodeling','business.eventmodeling'),
    ('treeView',r'^\s*treeView-beta','hierarchy.tree_view'),
    ('radar',r'^\s*radar-beta','charts.radar'),
    ('ishikawa',r'(?i)^\s*ishikawa(-beta)?\b','business.ishikawa'),
    ('treemap',r'^\s*treemap','hierarchy.treemap'),
    ('railroad',r'(?i)^\s*railroad-beta','railroad'),
    ('railroadEbnf',r'(?i)^\s*railroad-ebnf-beta','railroad'),
    ('railroadAbnf',r'(?i)^\s*railroad-abnf-beta','railroad'),
    ('railroadPeg',r'(?i)^\s*railroad-peg-beta','railroad'),
    ('venn',r'^\s*venn-beta','flows.venn'),
    ('wardley',r'(?i)^\s*wardley-beta','business.wardley'),
    ('cynefin',r'^\s*cynefin-beta(?:[\s:]|$)','business.cynefin'),
    ('usecase',r'^\s*usecase-beta(?:\s|$)','modeling.usecase'),
    ('zenuml',r'^\s*zenuml','zenuml'),
)
for _id,_pattern,_module in _ENTRIES:
    _registrations[_id]=Registration(_id,re.compile(_pattern).search,'py_mermaid.diagrams.'+_module if _module else None)


def register_diagram(identifier,detector,provider):
    """Register a pure Python detector and parse/build provider.

    ``provider`` is an import path or an object exposing callable ``parse`` and
    asynchronous ``build``. Replacing an existing key preserves detector order.
    """
    if not isinstance(identifier,str) or not identifier or not callable(detector):
        raise MermaidError('Diagram registration requires an id and detector',code='INVALID_REGISTRATION')
    if not isinstance(provider,str) and (not callable(getattr(provider,'parse',None)) or inspect.iscoroutinefunction(provider.parse) or not inspect.iscoroutinefunction(getattr(provider,'build',None))):
        raise MermaidError('Provider requires parse and async build',code='INVALID_REGISTRATION')
    with _lock:_registrations[identifier]=Registration(identifier,detector,provider)


def registered_diagrams():
    with _lock:return tuple(_registrations)


def _detect(document):
    text=document.cleaned
    if text.strip().lower()=='error':raise error(document,0,'Explicit Mermaid error diagram',code='ERROR_DIAGRAM')
    if text.lstrip().startswith('---'):raise error(document,0,'Malformed YAML front matter',code='INVALID_FRONTMATTER')
    with _lock:entries=tuple(_registrations.values())
    for entry in entries:
        if entry.detector(text):return entry
    raise error(document,0,'No diagram type detected matching source',code='UNKNOWN_DIAGRAM')


def detect_type(text,*,config=None):
    return _detect(preprocess_diagram(text,config)).id


def provider_for(kind):
    with _lock:registration=_registrations[kind]
    provider=registration.provider
    if provider is None:return None
    result=import_module(provider) if isinstance(provider,str) else provider
    if not callable(getattr(result,'parse',None)) or inspect.iscoroutinefunction(result.parse) or not inspect.iscoroutinefunction(getattr(result,'build',None)):
        raise MermaidError('Diagram provider is missing parse/async build: '+kind,code='INVALID_REGISTRATION')
    return result


def parse_diagram(text,*,config=None):
    document=preprocess_diagram(text,config)
    entry=_detect(document)
    if entry.id in ('flowchart-elk','flowchart-v2') and entry.provider is None:
        from ..diagrams.flowchart.parser import parse_flowchart
        return parse_flowchart(text,config=config)
    key=CONFIG_KEYS.get(entry.id,entry.id)
    document=preprocess_diagram(text,config,diagram_type=key)
    cfg=resolve(document,entry.id,config)
    limit=number(cfg.get('maxTextSize',50000),name='maxTextSize',minimum=0)
    if utf16_length(document.cleaned)>limit:raise error(document,0,'Diagram exceeds maxTextSize',code='TEXT_LIMIT')
    diagram=provider_for(entry.id).parse(document,cfg)
    from ..model.scene import Diagram
    if not isinstance(diagram,Diagram) or diagram.kind!=entry.id:raise MermaidError('Provider returned an invalid diagram kind/model',code='INVALID_DIAGRAM')
    return diagram
