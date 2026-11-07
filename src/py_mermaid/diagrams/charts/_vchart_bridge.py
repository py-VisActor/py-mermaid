"""Seven Mermaid chart syntaxes consume the installed VChart pure layouts.

No fallback to the former Mermaid numerical implementations is allowed.
Presentation remains in the host Painter so native vector exports and semantic
labels remain available alongside the chart geometry.
"""
from ...runtime.common import error


def geometry(name, document, *args, **kwargs):
    try:
        from py_vchart import layouts
    except ImportError as exc:
        raise error(document, 0, 'Chart syntax requires py-visactor-vchart with public layouts support',
                    'VCHART_DEPENDENCY_MISSING') from exc
    provider = getattr(layouts, name, None)
    if provider is None:
        raise error(document, 0, 'Installed VChart does not expose layout ' + name,
                    'VCHART_DEPENDENCY_MISSING')
    try:
        return provider(*args, **kwargs)
    except (ValueError, KeyError, ZeroDivisionError, OverflowError) as exc:
        raise error(document, 0, 'VChart ' + name + ': ' + str(exc), 'UNSUPPORTED_VCHART_OPTION') from exc
