"""Pure logical-pixel geometry; never allocates a native drawing object."""

from .flowchart import arrow_polygon, edge_points, geometry_bounds
from .shapes import CLASSIC_SHAPES, ShapeGeometry, shape_geometry, shape_outline_intersection

__all__ = ["arrow_polygon", "edge_points", "geometry_bounds", "CLASSIC_SHAPES", "ShapeGeometry",
           "shape_geometry", "shape_outline_intersection"]
