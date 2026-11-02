# py-mermaid

[中文](README.md) | English

Project repository: [py-VisActor/py-mermaid](https://github.com/py-VisActor/py-mermaid).

A Python port targeting the full Mermaid JS syntax, configuration, layout and spec rendering behavior, with [py-skia-canvas](https://github.com/xuanhun/py-skia-canvas) as its sole production rendering engine. The intended runtime needs no Node, browser or JavaScript engine.

**Bootstrap stage: repository structure, upstream lock, spec-file inventory and development instructions exist. Mermaid parsing, layout and rendering APIs are not implemented; no usable Mermaid rendering package has been released.** `examples/canvas_smoke.py` checks the actual Canvas dependency only.

## Baseline and scope

The first baseline is **mermaid@12.2.0**, commit `1fb7869866dd619168d840291c9c54b4f129758b`. The [lock](references/upstream.lock.json) records versions, critical source SHA256 hashes and parser/layout extension package versions. The [pinned source](https://github.com/mermaid-js/mermaid/tree/1fb7869866dd619168d840291c9c54b4f129758b) governs compatibility; live documentation is navigation only.

The [source inventory](references/spec-inventory.json) lists **37 core detectors plus the external ZenUML plugin**, 368 test source files, 2,366 rendering `.mmd` fixtures, 38 grammar files and 34 syntax documents. These are file counts, not individual test counts or pass rates. All diagram parsing, layout and rendering remain unimplemented; see [compatibility.json](docs/compatibility.json).

The target includes every diagram family, invalid inputs, frontmatter/directives, configuration/themes, labels/fonts, layout/routing, shapes/markers, resources/security, accessibility metadata and exports. DOM interactions, HTML/CSS, math and external plugins require explicit Python mappings and acceptance; they remain in the scope ledger. See the [compatibility rules](docs/API_COMPATIBILITY.md), currently in Chinese.

Canvas is pinned to `py-skia-canvas==0.1.0a18`. Initial targets are **CPython 3.13 / Windows AMD64 / Linux glibc 2.28+ x86_64**. Preserve its GPU/CPU policy and thread ownership. macOS and other ABIs are unverified. This project ports diagram layout; Canvas provides text shaping, drawing and encoding.

## Start development

Run at the repository root, using a separate CPython 3.13 environment. A short Windows environment path such as `C:\venvs\pymmd` is recommended.

```shell
python -m venv .venv
```

Activate the environment before installing the local scaffold and pinned dependencies:

```shell
python -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
python -m pip install -e ".[dev]"
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python scripts/upstream.py fetch
python scripts/upstream.py check
python examples/canvas_smoke.py --out test-runs/my-canvas-auto
python examples/canvas_smoke.py --backend cpu --out test-runs/my-canvas-cpu
```

Source checks need no Canvas installation. `upstream.py` needs Git and network access for the initial fetch. The production package will exclude `.local` and development oracles. Use `--backend gpu` for a separate GPU dependency check; it fails if the actual engine is not GPU. Existing output directories are never overwritten.

## Structure and entry points

| Path | Purpose |
| --- | --- |
| [AGENTS.md](AGENTS.md), [NEW_SESSION](docs/NEW_SESSION.md) | Startup order and a copyable next-session task |
| [Plan](docs/IMPLEMENTATION_PLAN.md), [tasks](docs/TASKS.md) | Architecture, milestones and next-batch acceptance |
| [Compatibility](docs/API_COMPATIBILITY.md), [testing](docs/TEST_AND_RELEASE.md) | Spec scope, oracle protocol, backend/font/export gates |
| [src/py_mermaid](src/py_mermaid) | parsing / model / layout / diagrams / config / rendering/skia boundaries |
| [references](references/README.md) | Upstream lock, read-only source and spec-file index |
| [tests](tests/README.md), [tools/oracle](tools/oracle/README.md) | Bootstrap assertions, inputs and planned official JS oracle |
| [examples](examples/README.md) | Runnable Canvas dependency check |
| [Release status](docs/RELEASE_STATUS.md) | Actual bootstrap evidence and unverified work |

The [M0–M8 implementation plan](docs/IMPLEMENTATION_PLAN.md) and [task breakdown](docs/TASKS.md), currently in Chinese, now cover all diagrams, shared behavior, layout algorithms, the official oracle and release gates. The pinned source defaults to ELK, so the first flowchart slice must verify that default path. This planning update adds no rendering capability.

The detailed startup/development records are currently in Chinese. The project uses MIT licensing, preserves the [upstream copyright](references/licenses/mermaid-LICENSE) and records [third-party notices](THIRD_PARTY_NOTICES.md). Use only public Canvas Python APIs. Canvas gaps are separate fixes in that repository, with their own validation; do not copy its Rust/Skia core here.
