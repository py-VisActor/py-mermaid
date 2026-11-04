"""Mermaid Python port, currently scoped to F01.1 basic flowcharts.

Target: mermaid@12.2.0. Importing performs no I/O or native allocation.
"""

from .api import arender, parse, render
from .model.flowchart import Flowchart, MermaidError, RenderResult

__version__ = "0.0.1a0"
__all__ = ["__version__", "parse", "render", "arender", "Flowchart", "RenderResult", "MermaidError"]
