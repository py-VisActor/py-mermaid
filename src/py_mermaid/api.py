"""Static diagram orchestration; native work stays on the calling thread."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from collections.abc import Mapping
from typing import Any

from .model.flowchart import ExportOptions, Flowchart, MermaidError, RenderResult, ResourceBundle
from .model.scene import Diagram, DiagramRenderResult


def parse(text: str, *, config: Mapping[str, Any] | None = None) -> Flowchart | Diagram:
    """Preprocess, detect and parse without allocating Canvas or ELK."""
    from .runtime.registry import parse_diagram
    return parse_diagram(text,config=config)


def compile_vchart(text: str, *, config: Mapping[str,Any] | None = None,
                   maps: Mapping[str,Any] | None = None,svgs: Mapping[str,str] | None = None):
    """Pure strict-JSON/typed-DSL compilation, with explicit resource snapshots.

    Inspection proves syntax/lowering/basic type-size/safety only. Statistical
    rendering, fonts, devices and full provider option guards are not invoked.
    """
    from .vchart_compilation import compile_vchart as compile_text
    return compile_text(text,config=config,maps=maps,svgs=svgs)


async def arender(
    text: str,
    *,
    config: Mapping[str, Any] | None = None,
    format: str = "png",
    backend: str = "auto",
    resources: ResourceBundle | None = None,
    export_options: ExportOptions | None = None,
    maps: Mapping[str, Any] | None = None,
    svgs: Mapping[str, str] | None = None,
) -> RenderResult | DiagramRenderResult:
    """Measure, lay out with pyelk and export on the caller's owner thread.

    No objects are moved to executor threads. Cancellation propagates through
    the layout engine, whose worker lifecycle is owned by its adapter.
    """
    if format not in {"png", "jpg", "jpeg", "webp", "svg", "pdf"}:
        raise MermaidError("Unsupported static export format", code="UNSUPPORTED_FORMAT")
    if backend not in ("auto", "cpu", "gpu"):
        raise MermaidError("backend must be auto, cpu or gpu", code="INVALID_BACKEND")
    diagram = parse(text, config=config)
    if isinstance(diagram,Diagram):
        from .runtime.registry import provider_for
        from .model.vchart import VChartModel
        if isinstance(diagram.model,VChartModel):
            from .vchart_bridge import encode_vchart, scene_for, _provider_error
            try:scene=scene_for(diagram.model,maps=maps,svgs=svgs)
            except MermaidError as exc:
                if diagram.model.syntax=='dsl' and exc.span is None:
                    raise _provider_error(diagram,exc,exc.code) from exc
                raise
            except (ValueError,TypeError) as exc:
                if diagram.model.syntax=='dsl':
                    raise _provider_error(diagram,exc,'INVALID_RESOURCE') from exc
                raise
            return encode_vchart(diagram,scene,format=format,backend=backend,
                                 resources=resources,export_options=export_options)
        if maps is not None or svgs is not None:
            raise MermaidError('maps/svgs belong to explicit VChart inputs',code='INVALID_RESOURCE')
        from .rendering.skia.scene import Painter
        painter=Painter(diagram,backend=backend,resources=resources)
        scene=await provider_for(diagram.kind).build(diagram,painter)
        return painter.encode(scene,format=format,export_options=export_options)
    if maps is not None or svgs is not None:
        raise MermaidError('maps/svgs belong to explicit VChart inputs',code='INVALID_RESOURCE')
    from .runtime.layouts import uses_builtin_swimlane
    if uses_builtin_swimlane(diagram.config.layout):
        from .runtime.configuration import resolve
        from .runtime.common import make_diagram
        from .diagrams.business.swimlane import build
        from .rendering.skia.scene import Painter
        values=resolve(diagram.source_document,'flowchart',config);values['layout']='swimlane'
        wrapped=make_diagram(diagram.diagram_type,diagram.source_document,values,diagram)
        painter=Painter(wrapped,backend=backend,resources=resources)
        scene=await build(wrapped,painter)
        result=painter.session.render(scene.flowchart,scene.measured,scene.layout,
            annotations=scene.annotations,format=format,export_options=export_options,
            group_overrides=scene.group_overrides,draw_group_override=painter._draw_commands)
        return replace(result,diagram=diagram,annotations=scene)
    from .layout.elk import layout_flowchart
    from .rendering.skia import CanvasSession

    session = CanvasSession(backend=backend, resources=resources)
    measured = session.measure(diagram)
    annotations = session.measure_annotations(diagram)
    from .runtime.layouts import uses_builtin_elk
    if uses_builtin_elk(diagram.config.layout):
        layout = await layout_flowchart(diagram, measured, measured_groups=annotations.groups,
                                        measured_edge_labels=annotations.edge_labels,
                                        measured_title=annotations.title,
                                        title_suppressed=annotations.title_suppressed)
    else:
        from .runtime.flow_variants import layout_registered_flowchart
        layout=await layout_registered_flowchart(diagram,measured,annotations)
    return session.render(diagram, measured, layout, annotations=annotations,
                          format=format, export_options=export_options)


def render(
    text: str,
    *,
    config: Mapping[str, Any] | None = None,
    format: str = "png",
    backend: str = "auto",
    resources: ResourceBundle | None = None,
    export_options: ExportOptions | None = None,
    maps: Mapping[str, Any] | None = None,
    svgs: Mapping[str, str] | None = None,
) -> RenderResult | DiagramRenderResult:
    """Synchronous static renderer; in an event loop use ``await arender(...)``.

    Applications using Windows multiprocessing must call this from a guarded
    ``if __name__ == '__main__'`` entry, as required by pyelk's spawn workers.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(arender(text, config=config, format=format, backend=backend,
                                   resources=resources, export_options=export_options,
                                   maps=maps, svgs=svgs))
    raise MermaidError("Use await arender(...) inside an active event loop", code="ACTIVE_EVENT_LOOP")


async def arender_vchart(
    spec: Mapping[str, Any], *, format: str = 'png', backend: str = 'auto',
    resources: ResourceBundle | None = None, export_options: ExportOptions | None = None,
    maps: Mapping[str, Any] | None = None, svgs: Mapping[str, str] | None = None,
) -> DiagramRenderResult:
    """Render any supported VChart JSON spec directly on the calling thread.

    No Mermaid directives, grammar, theme or rich-label sanitizer modify spec.
    Images use explicit resource:ID references or self-contained data URIs;
    named maps and SVGs are isolated snapshots for this one render.
    """
    if format not in {'png','jpg','jpeg','webp','svg','pdf'}:
        raise MermaidError('Unsupported static export format',code='UNSUPPORTED_FORMAT')
    if backend not in ('auto','cpu','gpu'):
        raise MermaidError('backend must be auto, cpu or gpu',code='INVALID_BACKEND')
    from .vchart_bridge import make_vchart_diagram, scene_for, encode_vchart
    diagram=make_vchart_diagram(spec)
    scene=scene_for(diagram.model,maps=maps,svgs=svgs)
    return encode_vchart(diagram,scene,format=format,backend=backend,
                         resources=resources,export_options=export_options)


def render_vchart(
    spec: Mapping[str, Any], *, format: str = 'png', backend: str = 'auto',
    resources: ResourceBundle | None = None, export_options: ExportOptions | None = None,
    maps: Mapping[str, Any] | None = None, svgs: Mapping[str, str] | None = None,
) -> DiagramRenderResult:
    """Synchronous VChart JSON renderer; inside a loop use arender_vchart."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(arender_vchart(spec,format=format,backend=backend,
            resources=resources,export_options=export_options,maps=maps,svgs=svgs))
    raise MermaidError('Use await arender_vchart(...) inside an active event loop',code='ACTIVE_EVENT_LOOP')
