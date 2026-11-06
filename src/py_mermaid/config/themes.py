"""Eleven pinned Mermaid theme families and the documented null sentinel."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from .theme_rules_full import THEME_RULES

THEMES = tuple(THEME_RULES)


def get_theme_variables(name, overrides=None):
    """Run the complete statically translated constructor/update rules.

    Mermaid re-applies explicit overrides after derived values have been computed.
    The null sentinel retains a name with no palette gate but does not create a
    twelfth palette: initialize builds the default variables for that name.
    """
    selected=name if name in THEME_RULES else 'default'
    construct, update = THEME_RULES[selected]
    values = {}
    construct(values)
    # Only theme-default.calculate clears these placeholders. Other families
    # inspect the literal sentinel in updateColors (notably secondBkg in dark
    # themes), and dark.labelColor is deliberately retained by the source.
    if selected=='default':values = {key: value for key, value in values.items() if value != "calculated"}
    patch = deepcopy(dict(overrides)) if isinstance(overrides, Mapping) else {}
    values.update(patch)
    update(values)
    # JavaScript array reads outside a short user palette produce undefined,
    # which JSON/object configuration projection omits. Explicit null overrides
    # are re-applied below and remain distinct user values.
    def projected(value):
        if isinstance(value,dict):return {key:projected(item) for key,item in value.items() if item is not None}
        if isinstance(value,list):return [projected(item) for item in value]
        return value
    values=projected(values)
    for key, value in patch.items():
        if isinstance(value, Mapping) and isinstance(values.get(key), Mapping):
            values[key] = {**values[key], **value}
        else:
            values[key] = value
    if name == "base" and "nodeBorder" in patch and "useGradient" not in patch:
        values["useGradient"] = False
    return values
