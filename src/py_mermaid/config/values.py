"""Pure configuration values and Mermaid's bounded merge semantics."""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from py_mermaid.model.flowchart import MermaidError


class FrozenMap(tuple):
    """An immutable key/value tuple that also distinguishes an empty object."""
    __slots__ = ()


class FrozenArray(tuple):
    """An immutable value tuple that preserves empty-array identity."""
    __slots__ = ()


def freeze_value(value, _seen=None, _budget=None):
    _seen = set() if _seen is None else _seen
    _budget = [50000] if _budget is None else _budget
    _budget[0] -= 1
    if _budget[0] < 0:
        raise MermaidError("Configuration value budget exceeded", code="CONFIG_BUDGET_EXCEEDED")
    if isinstance(value, (Mapping, list, tuple)):
        if id(value) in _seen:
            raise MermaidError("Cyclic configuration values are not supported", code="INVALID_CONFIG")
        _seen.add(id(value))
    if isinstance(value, (Mapping, FrozenMap)):
        pairs = value if isinstance(value, FrozenMap) else value.items()
        result = FrozenMap((str(key), freeze_value(item, _seen, _budget)) for key, item in pairs)
        _seen.remove(id(value))
        return result
    if isinstance(value, (list, tuple)):
        result = FrozenArray(freeze_value(item, _seen, _budget) for item in value)
        _seen.remove(id(value))
        return result
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"Unsupported configuration value type: {type(value).__name__}")


def thaw_value(value):
    if isinstance(value, FrozenArray):
        return [thaw_value(item) for item in value]
    if isinstance(value, FrozenMap):
        return {key: thaw_value(item) for key, item in value}
    if isinstance(value, tuple):
        if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value):
            return {key: thaw_value(item) for key, item in value}
        return [thaw_value(item) for item in value]
    return value


def assign_with_depth(destination, source, depth=2):
    """Port assignWithDepth.ts: array union, bounded object merge, null skip."""
    if isinstance(source, list):
        if isinstance(destination, list):
            for item in source:
                def same(other):
                    if isinstance(item, (Mapping, list)):
                        return item is other
                    if isinstance(item, bool) or isinstance(other, bool):
                        return type(item) is type(other) and item == other
                    if isinstance(item, float) and isinstance(other, float) and item != item and other != other:
                        return True
                    return item == other
                if not any(same(other) for other in destination):
                    destination.append(item)
        else:
            for item in source:
                assign_with_depth(destination, item, depth)
        return destination
    if destination is None or depth <= 0:
        if isinstance(destination, dict) and isinstance(source, Mapping):
            destination.update(deepcopy(source))
            return destination
        return deepcopy(source)
    if isinstance(destination, dict) and isinstance(source, Mapping):
        for key, value in source.items():
            if value is None:
                continue
            if isinstance(value, (Mapping, list)):
                if key not in destination:
                    destination[key] = [] if isinstance(value, list) else {}
                if isinstance(destination[key], (dict, list)):
                    destination[key] = assign_with_depth(destination[key], value, depth - 1)
            elif not isinstance(destination.get(key), (dict, list)):
                destination[key] = deepcopy(value)
    return destination


def merge_layers(destination, source):
    """lodash merge used for frontmatter+init: object recursion, array indices."""
    for key, value in source.items():
        if isinstance(value, Mapping):
            old = destination.get(key)
            destination[key] = merge_layers(old if isinstance(old, dict) else {}, value)
        elif isinstance(value, list) and isinstance(destination.get(key), list):
            old = destination[key]
            for index, item in enumerate(value):
                if index == len(old):
                    old.append(deepcopy(item))
                elif isinstance(item, Mapping):
                    old[index] = merge_layers(old[index] if isinstance(old[index], dict) else {}, item)
                else:
                    old[index] = deepcopy(item)
        else:
            destination[key] = deepcopy(value)
    return destination
