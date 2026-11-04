"""Basic flowchart geometry, using top-left boxes and immutable value objects.

Source responsibilities: Mermaid rendering-elements/intersect and
layout-algorithms/elk/geometry.ts. Arrow construction is a Canvas-native
expression of the ordinary point marker, with its tip on the routed endpoint.
"""
from __future__ import annotations

import math
from collections.abc import Iterable

from py_mermaid.model.flowchart import Box, EdgeSection, FlowLayout, Point


def edge_points(section: EdgeSection) -> tuple[Point, ...]:
    """Return the complete ordered route, including both endpoint positions."""
    return (section.start, *section.bends, section.end)


def arrow_polygon(
    points: Iterable[Point], *, length: float = 10.0, width: float = 7.0
) -> tuple[Point, ...]:
    """Build a triangular end marker along the last nonzero route segment.

    The tip is the last route point; duplicate endpoint bends are permitted.
    A degenerate path has no direction and cannot produce an arrow.
    """
    if not all(math.isfinite(v) and v > 0 for v in (length, width)):
        raise ValueError("Arrow length and width must be positive finite values")
    route = tuple(points)
    if len(route) < 2:
        raise ValueError("An arrow needs at least two route points")
    tip = route[-1]
    for previous in reversed(route[:-1]):
        dx, dy = tip.x - previous.x, tip.y - previous.y
        distance = math.hypot(dx, dy)
        if distance > 0:
            ux, uy = dx / distance, dy / distance
            base_x, base_y = tip.x - length * ux, tip.y - length * uy
            half = width / 2
            return (
                tip,
                Point(base_x - half * uy, base_y + half * ux),
                Point(base_x + half * uy, base_y - half * ux),
            )
    raise ValueError("An arrow needs a nonzero terminal segment")


def geometry_bounds(layout: FlowLayout, *, margin: float = 0.0) -> Box:
    """Bounds of every node and route, including an optional stroke margin.

    The engine's graph box is included so its own spacing is preserved.
    Callers may union additional arrow/text extents before choosing a viewport.
    """
    if not math.isfinite(margin) or margin < 0:
        raise ValueError("Bounds margin must be finite and nonnegative")
    xs = [0.0, layout.width]
    ys = [0.0, layout.height]
    for node in layout.nodes:
        box = node.box
        xs.extend((box.x, box.x + box.width))
        ys.extend((box.y, box.y + box.height))
    for edge in layout.edges:
        for section in edge.sections:
            for point in edge_points(section):
                xs.append(point.x)
                ys.append(point.y)
    left, top = min(xs) - margin, min(ys) - margin
    return Box(left, top, max(xs) + margin - left, max(ys) + margin - top)
