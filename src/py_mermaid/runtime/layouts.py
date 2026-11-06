"""Native layout provider registration; no unavailable-algorithm fallback."""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from importlib import import_module
import inspect
from threading import RLock
from ..config.elk import LAYOUTS
from ..model.flowchart import MermaidError


@dataclass(frozen=True)
class LayoutRegistration:
    name: str
    provider: object
    algorithm: str | None = None


_lock=RLock()
_providers=OrderedDict((name,LayoutRegistration(name,None,'elk.layered' if name=='elk' else name)) for name in sorted(LAYOUTS))
_providers['cose-bilkent']=LayoutRegistration('cose-bilkent','py_mermaid.diagrams.hierarchy._cose_tree:layout')
_providers['tidy-tree']=LayoutRegistration('tidy-tree','py_mermaid.diagrams.hierarchy._tidy:layout')
_providers['swimlane']=LayoutRegistration('swimlane','py_mermaid.diagrams.business.swimlane:layout_provider')


def register_layout(name,provider,*,algorithm=None):
    """Register an async Python measured-graph provider or ``module:symbol``.

    A provider accepts the same pure measured graph arguments as layout_graph
    and returns GraphLayout. Custom providers own their cancellation lifecycle.
    Registration never loads the provider or creates native/worker objects.
    """
    if not isinstance(name,str) or not name or 'dagre' in name.lower():
        raise MermaidError('Invalid or excluded layout name',code='INVALID_REGISTRATION')
    if not isinstance(provider,str) and not inspect.iscoroutinefunction(provider):
        raise MermaidError('Layout provider must be async or a module:symbol path',code='INVALID_REGISTRATION')
    if isinstance(provider,str) and ':' not in provider:
        raise MermaidError('Layout import path requires module:symbol',code='INVALID_REGISTRATION')
    with _lock:_providers[name]=LayoutRegistration(name,provider,algorithm)


def registered_layouts():
    with _lock:return tuple(_providers)


def layout_definition(name):
    with _lock:entry=_providers.get(name)
    if entry is None:raise MermaidError('Unknown native layout: '+str(name),code='UNSUPPORTED_LAYOUT')
    return entry


def uses_builtin_elk(name):
    return name in LAYOUTS and layout_definition(name).provider is None


def uses_builtin_swimlane(name):
    return name=='swimlane' and layout_definition(name).provider=='py_mermaid.diagrams.business.swimlane:layout_provider'


def load_layout(entry):
    provider=entry.provider
    if isinstance(provider,str):
        module,symbol=provider.split(':',1);provider=getattr(import_module(module),symbol)
    if not inspect.iscoroutinefunction(provider):raise MermaidError('Layout provider must be async',code='INVALID_REGISTRATION')
    return provider
