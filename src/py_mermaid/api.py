"""F01.1 public orchestration; all native work stays on the calling thread."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from .model.flowchart import Flowchart, MermaidError, RenderResult


def parse(text: str, *, config: Mapping[str, Any] | None = None) -> Flowchart:
    """Parse a supported basic flowchart without allocating Canvas or ELK."""
    from .parsing import parse_flowchart

    return parse_flowchart(text, config=config)


async def arender(
    text: str,
    *,
    config: Mapping[str, Any] | None = None,
    format: str = "png",
    backend: str = "auto",
) -> RenderResult:
    """Measure, lay out with pyelk and draw PNG on the caller's owner thread.

    No objects are moved to executor threads. Cancellation propagates through
    the layout engine, whose worker lifecycle is owned by its adapter.
    """
    if format != "png":
        raise MermaidError("F01.1 supports PNG output only", code="UNSUPPORTED_FORMAT")
    if backend not in ("auto", "cpu", "gpu"):
        raise MermaidError("backend must be auto, cpu or gpu", code="INVALID_BACKEND")
    diagram = parse(text, config=config)
    from .layout.elk import layout_flowchart
    from .rendering.skia import CanvasSession

    session = CanvasSession(backend=backend)
    measured = session.measure(diagram)
    layout = await layout_flowchart(diagram, measured)
    return session.render(diagram, measured, layout)


def render(
    text: str,
    *,
    config: Mapping[str, Any] | None = None,
    format: str = "png",
    backend: str = "auto",
) -> RenderResult:
    """Synchronous PNG renderer; in an event loop use ``await arender(...)``.

    Applications using Windows multiprocessing must call this from a guarded
    ``if __name__ == '__main__'`` entry, as required by pyelk's spawn workers.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(arender(text, config=config, format=format, backend=backend))
    raise MermaidError("Use await arender(...) inside an active event loop", code="ACTIVE_EVENT_LOOP")
