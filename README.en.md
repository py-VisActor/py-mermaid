# py-mermaid

The distribution is `py-visactor-mermaid`, the import is `py_mermaid`, and the command is `py-mermaid`. The source version is `0.1.0`; see the [closure record](https://github.com/py-VisActor/py-mermaid/blob/main/docs/CLOSURE_BATCH_PLAN.md) for actual validation and publication status. Chart capabilities and provider limits are managed by py-vchart. This batch completes the remaining grammar, calendar, relationship and static drawing behavior. All outputs are static images.

The native chart DSL v1 uses `vchart <type>`, assignments, tables, immutable value bindings, configuration blocks, axes and series. It reuses the formal provider for all68 registered types. For scope and actual validation status, see the [language specification](https://github.com/py-VisActor/py-mermaid/blob/main/docs/VCHART_DSL_DESIGN.md) and [execution plan](https://github.com/py-VisActor/py-mermaid/blob/main/docs/VCHART_DSL_EXECUTION_PLAN.md).

```python
from pathlib import Path
from py_mermaid import compile_vchart, render

source = """vchart bar
size 640 360
data = { values: table(month, value) {
  ["Jan", 120]
  ["Feb", 180]
} }
xField = "month"
yField = "value"
"""
compiled = compile_vchart(source)
print(compiled.spec())
Path("dsl.svg").write_bytes(render(source, format="svg").data)
```

Use `py-mermaid chart.vchart --compile -o compiled.json` to inspect the complete spec, map/SVG resources, source map and diagnostics. Rendering keeps the ordinary format/backend arguments. Strict `vchart` JSON and the Python spec API remain available.

2026-11-07: `py-visactor-vchart` 0.1.1 is integrated. The dependency resolves `py-visactor-vchart==0.1.1` from PyPI; its wheel and sdist SHA-256 values match the [formal GitHub release](https://github.com/py-VisActor/py-vchart/releases/tag/py-visactor-vchart-v0.1.1). Explicit VChart JSON/Python spec inputs cover its 68 two-dimensional static chart types, including the seven formerly deferred Mermaid chart grammars. See the [integration acceptance](https://github.com/py-VisActor/py-mermaid/blob/main/docs/VCHART_INTEGRATION.md). The 31-entry batch below is historical; repair and validation of the22 non-chart branch gaps are recorded in the latest closure record.

```python
from pathlib import Path
from py_mermaid import render_vchart, supported_vchart_types

print(supported_vchart_types())
result = render_vchart({
    "type": "bar", "width": 400, "height": 240,
    "data": [{"values": [{"name": "A", "value": 8}, {"name": "B", "value": -3}]}],
    "xField": "name", "yField": "value",
}, format="svg", backend="auto")
Path("chart.svg").write_bytes(result.data)
```

Use `render_vchart(spec, format="svg", backend="auto")`, `await arender_vchart(spec, ...)`, or a `vchart` first line followed by strict JSON with the ordinary render/CLI entry. `supported_vchart_types()` reads the dependency's complete registry. Specs are not rewritten by Mermaid directives or rich-label processing; maps/SVGs and image/font resources are explicit and offline. Production uses the released distribution and public Canvas API, without Node, browsers, skia-python, or sibling-source fallbacks. This covers the package's current static 2D types, not 3D, interactions, or every VChart JS advanced option.

CLI flags `--vchart-maps maps.json` and `--vchart-svgs svgs.json` supply explicit name-to-GeoJSON and name-to-SVG-text mappings; `--resources` supplies images/fonts. Venn inherits the provider's three-set limit. Treemap uses VChart binary layout and explicitly rejects unsupported numeric format operators. Custom resource fonts bind a single `fontFamily` through private content-hash aliases; custom fallback lists fail explicitly. These limits are separate from full type-registry support.

[中文](https://github.com/py-VisActor/py-mermaid/blob/main/README.md) | English

[py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid) uses native Python parsing, real py-elk layout and py-skia-canvas measurement, drawing and encoding. Production requires no Node, browser or JavaScript runtime.

**The historical static batch retained 31 detector entries: 29 new entries and two flowchart regression entries.** It covers relationship modeling, sequence/ZenUML, calendars/Git/timelines, mindmap/treeView, block/packet/kanban/architecture, six business diagrams, four railroad grammars and info. See the [exact scope](https://github.com/py-VisActor/py-mermaid/blob/main/references/bulk-scope.json), [batch usage](https://github.com/py-VisActor/py-mermaid/blob/main/docs/BULK_USAGE.md), [execution plan](https://github.com/py-VisActor/py-mermaid/blob/main/docs/BULK_STATIC_EXECUTION.md), and [ledger](https://github.com/py-VisActor/py-mermaid/blob/main/docs/execution-state.json). The seven formerly excluded entries (pie, quadrantChart, xychart, radar, treemap, sankey and venn) are integrated through py-vchart in the new iteration described above; the old 31-entry acceptance remains historical. Entrypoint acceptance does not establish exhaustive grammar/configuration branch coverage; see the [functionality audit plan](https://github.com/py-VisActor/py-mermaid/blob/main/docs/NEXT_ITERATION.md). Initial static appearances of HTML form controls are implemented for input, button, select, textarea, meter/progress and fieldset/legend; see the [iteration scope and acceptance status](https://github.com/py-VisActor/py-mermaid/blob/main/docs/HTML_HOST_ACCEPTANCE.md). This does not claim arbitrary browser HTML/CSS compatibility. The user has entirely excluded video/audio, including decoding, playback, posters/placeholders, controls and initial static appearance. These are neither migration backlog nor acceptance items; existing explicit input rejection remains. Ordinary image/icon resources remain in scope. Implementation, grouped checks and final acceptance remain distinct statuses. The source version is `0.1.0`; publication is recorded separately in the closure record.


Math labels use the published **`py-visactor-katex==0.1.0`** distribution (Python import: `py_katex`). Installing this project resolves it from PyPI; no sibling checkout or PYTHONPATH wiring is required. Node, edge and group labels support native `$$...$$` rendering; `htmlLabels=false` preserves the literal source branch. See [integration verification](https://github.com/py-VisActor/py-mermaid/blob/main/docs/MATH_RELEASE_INTEGRATION.md).

## Local use

Use CPython 3.13 on Windows AMD64 or Linux x86_64. The distribution installs as follows; see the release record for actual publication status. To install a source checkout, use `python -m pip install .`.

```shell
python -m pip install py-visactor-mermaid==0.1.0
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

The static pipeline includes source-specific syntax/models/layouts, labels, themes, hand-drawn branches, explicit resources and PNG/JPEG/WebP/SVG/PDF export. Dagre functionality, options, target dependencies and algorithm fallback are removed; see the [layout policy](https://github.com/py-VisActor/py-mermaid/blob/main/docs/LAYOUT_POLICY.md). General graphs use real ELK; COSE/tidy, architecture fCoSE, swimlane routing, C4, calendars/Git, treeView, railroad and ZenUML retain dedicated algorithms. `parse` returns an immutable `Flowchart | Diagram`; `render`/`arender` return the corresponding result with bytes, geometry, trace and actual backend. Python provider registration extends detectors and layouts. All modules exclude interaction, playback and interactive metadata. The closure batch requires same-candidate regression and isolated Windows/Linux installation gates; actual results and historical platform evidence are recorded separately.

Acceptance checks semantic content, actual painting, relationships, readability and safe export. Browser/Canvas pixels, natural sizes and legitimate routes may differ; pixel reports are diagnostic.

See the [active plan](https://github.com/py-VisActor/py-mermaid/blob/main/docs/CLOSURE_BATCH_PLAN.md), [interfaces](https://github.com/py-VisActor/py-mermaid/blob/main/docs/BULK_STATIC_INTERFACES.md), [ledger](https://github.com/py-VisActor/py-mermaid/blob/main/docs/execution-state.json), [reusable batch tooling](https://github.com/py-VisActor/py-mermaid/blob/main/tools/BULK_REPORTS.md) and [release status](https://github.com/py-VisActor/py-mermaid/blob/main/docs/RELEASE_STATUS.md). The [full migration plan](https://github.com/py-VisActor/py-mermaid/blob/main/docs/FULL_MIGRATION_PLAN.md) retains the original 38-entry inventory; the closure scope includes all38 Mermaid entrypoints and the VChart integration, with chart features managed by the provider; the31/7 split is historical.

The CLI uses the same native API: `python -m py_mermaid input.mmd -o output.svg --backend cpu --metadata output.json`. Resources come from explicit offline bundles/manifests. No implicit network, sibling checkout or browser fallback is used in production.
