"""Strict JSON scene encoding, preserving JS/YAML non-finite scalar intent."""
from __future__ import annotations

import math


def json_ready(value):
    if isinstance(value,float) and not math.isfinite(value):
        return {'$jsNumber':'NaN' if math.isnan(value) else 'Infinity' if value>0 else '-Infinity'}
    if isinstance(value,dict):return {key:json_ready(item) for key,item in value.items()}
    if isinstance(value,(tuple,list)):return [json_ready(item) for item in value]
    return value
