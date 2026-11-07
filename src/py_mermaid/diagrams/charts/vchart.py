"""Explicit VChart strict JSON and native typed-DSL provider.

Source dispatch: py-vchart/src/py_vchart/core/__init__.py:VChart/RENDERERS.
No Mermaid preprocessor is applied to JSON strings, comments, or data values.
The header must be the first nonblank line; YAML frontmatter and init directives
are not a configuration channel for this extension. Put chart options in spec.
"""
from ...model.scene import Diagram
from ...model.vchart import VChartScene
from ...runtime.common import make_diagram


def parse(document, config):
    from ...vchart_compilation import compile_vchart
    compilation=compile_vchart(document.raw,config=config)
    model=compilation.model
    return make_diagram('vchart',document,config,model,
                        tuple(v.code+': '+v.message for v in model.diagnostics))


async def build(diagram, painter):
    """Return only pure values; encoding is handled by the VChart bridge."""
    from ...model.vchart import VChartModel
    from ...model.flowchart import MermaidError
    if not isinstance(diagram, Diagram) or not isinstance(diagram.model, VChartModel):
        raise MermaidError('VChart provider requires a VChart model', code='INVALID_DIAGRAM')
    from ...vchart_bridge import scene_for
    return scene_for(diagram.model)

