"""Native Python static Mermaid diagram families.

Target: mermaid@12.2.0. Importing performs no I/O or native allocation.
"""

from .api import arender, parse, render
from .model.flowchart import (ExportOptions, Flowchart, FontResource, IconResource,
                             ImageResource, MermaidError, RenderResult, ResourceBundle)
from .model.scene import Diagram, DiagramRenderResult, Scene
from .runtime.registry import detect_type, register_diagram, registered_diagrams
from .runtime.layouts import register_layout, registered_layouts

__version__ = "0.0.1a0"
__all__ = ["__version__", "parse", "render", "arender", "Flowchart", "RenderResult", "MermaidError",
           "ResourceBundle", "ImageResource", "IconResource", "FontResource", "ExportOptions",
           "Diagram", "DiagramRenderResult", "Scene", "detect_type", "register_diagram", "registered_diagrams",
           "register_layout", "registered_layouts"]
