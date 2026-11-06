# py-mermaid

[中文](README.md) | English

[py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid) uses native Python parsing, real py-elk layout and py-skia-canvas measurement, drawing and encoding. Production requires no Node, browser or JavaScript runtime.

**The active static batch retains 31 detector entries: 29 new entries and two flowchart regression entries.** It covers relationship modeling, sequence/ZenUML, calendars/Git/timelines, mindmap/treeView, block/packet/kanban/architecture, six business diagrams, four railroad grammars and info. See the [exact scope](references/bulk-scope.json), [batch usage](docs/BULK_USAGE.md), [execution plan](docs/BULK_STATIC_EXECUTION.md), and [ledger](docs/execution-state.json). The seven deferred entries are pie, quadrantChart, xychart, radar, treemap, sankey and venn. Implementation, grouped checks and final acceptance remain distinct statuses. Version `0.0.1a0` is local development code and has not been published to PyPI.


Math labels use the published **`py-visactor-katex==0.1.0`** distribution (Python import: `py_katex`). Installing this project resolves it from PyPI; no sibling checkout or PYTHONPATH wiring is required. Node, edge and group labels support native `$$...$$` rendering; `htmlLabels=false` preserves the literal source branch. See [integration verification](docs/MATH_RELEASE_INTEGRATION.md).

## Local use

Use CPython 3.13 and install this source tree:

```shell
python -m pip install .
```

```python
from pathlib import Path
from py_mermaid import render

if __name__ == "__main__":
    result = render("flowchart TD\nA[Start] --> B[End]")
    Path("flowchart.png").write_bytes(result.data)
    print(result.width, result.height, result.mime)
```

Guard the entry point because py-elk uses process workers. Use `await arender(...)` inside an event loop, and `parse(...)` for an immutable model without native allocation. Canvas stays on the calling thread. Backend `auto` preserves policy; `cpu` uses the public GPU setter; `gpu` requires an actual GPU renderer and fails otherwise.

Run the branch/merge example:

```shell
python examples/basic_flowchart.py --out test-runs/my-flowchart.png
python examples/enhanced_flowchart.py --out test-runs/my-enhanced-flowchart.png
python examples/rich_flowchart.py --out test-runs/my-rich-flowchart.png
```

## Scope and evidence

Pinned: Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`, `py-skia-canvas==0.1.0a18`, `py-visactor-elk==0.1.0`. Appearance follows diagram-scoped `redux-color/neo` defaults: white rectangles, dark borders/text, black arrows, shadows and measured wrapping. System fallback fonts are not bundled.

Classic shapes: square, round, stadium, subroutine, cylinder, circle, doublecircle, diamond, hexagon, odd, trapezoid, inv_trapezoid, lean_right and lean_left. Classic `A(-Ellipse-)` parses, but the pinned upstream lacks its renderer; rendering reports `UPSTREAM_SHAPE_MISSING`. Subgraphs support TD/TB/LR/RL/BT locally and retain the source inheritance policy.

Preprocessing preserves raw character/UTF-16 positions. Configuration retains site/frontmatter/directive precedence, all 11 pinned themes and the `null` sentinel. Rich labels become immutable measured text runs and native Canvas paint, with no DOM runtime. The HTML-off path follows upstream SVG text semantics rather than stripping tags. Markdown follows upstream's supported branches rather than claiming complete CommonMark. Applicable theme CSS becomes native paint/font intent.

The static pipeline includes source-specific syntax/models/layouts, labels, themes, hand-drawn branches, explicit resources and PNG/JPEG/WebP/SVG/PDF export. Dagre functionality, options, target dependencies and algorithm fallback are removed; see the [layout policy](docs/LAYOUT_POLICY.md). General graphs use real ELK; COSE/tidy, architecture fCoSE, swimlane routing, C4, calendars/Git, treeView, railroad and ZenUML retain dedicated algorithms. `parse` returns an immutable `Flowchart | Diagram`; `render`/`arender` return the corresponding result with bytes, geometry, trace and actual backend. Python provider registration extends detectors and layouts. All modules exclude interaction, playback and interactive metadata. The current batch does not run installation verification or publish py-mermaid; historical math installation and platform evidence keep their original scope.

Acceptance checks semantic content, actual painting, relationships, readability and safe export. Browser/Canvas pixels, natural sizes and legitimate routes may differ; pixel reports are diagnostic.

See the [active plan](docs/BULK_STATIC_EXECUTION.md), [interfaces](docs/BULK_STATIC_INTERFACES.md), [ledger](docs/execution-state.json), [reusable batch tooling](tools/BULK_REPORTS.md) and [release status](docs/RELEASE_STATUS.md). The [full migration plan](docs/FULL_MIGRATION_PLAN.md) retains the original 38-entry inventory; the current 31/7 scope decision governs this batch.

The CLI uses the same native API: `python -m py_mermaid input.mmd -o output.svg --backend cpu --metadata output.json`. Resources come from explicit offline bundles/manifests. No implicit network, sibling checkout or browser fallback is used in production.
