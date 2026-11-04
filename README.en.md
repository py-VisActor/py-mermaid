# py-mermaid

[中文](README.md) | English

[py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid) uses native Python parsing, real py-elk layout and py-skia-canvas measurement, drawing and encoding. Production requires no Node, browser or JavaScript runtime.

**Current scope: F01.1 basic flowcharts.** Supports `flowchart` / `graph`, TD / LR, rectangles, plain labels, `-->`, individual nodes, chains, branching and merging. Version `0.0.1a0` is local development code and has not been published to PyPI.

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
```

## Scope and evidence

Pinned: Mermaid 12.2.0 / `1fb7869866dd619168d840291c9c54b4f129758b`, `py-skia-canvas==0.1.0a18`, `py-visactor-elk==0.1.0`. Appearance follows diagram-scoped `redux-color/neo` defaults: white rectangles, dark borders/text, black arrows, shadows and measured wrapping. System fallback fonts are not bundled.

Edge labels, subgraphs, other shapes, rich/math labels, other themes/looks, Dagre, plugins and non-PNG exports are outside this slice and explicitly rejected. This does not establish complete flowchart or Mermaid compatibility. Windows local evidence and unverified Linux/no-loader environments are reported separately.

Acceptance checks semantic content, actual painting, relationships, readability and safe export. Browser/Canvas pixels, natural sizes and legitimate routes may differ; pixel reports are diagnostic.

See the [active plan](docs/F01_1_EXECUTION_PLAN.md), [usage](docs/F01_1_USAGE.md), [ledger](docs/execution-state.json), [tools](tools/oracle/README.md) and [release status](docs/RELEASE_STATUS.md). The [full migration plan](docs/FULL_MIGRATION_PLAN.md) remains future scope.
