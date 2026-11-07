# py-mermaid

[中文](https://github.com/py-VisActor/py-mermaid/blob/main/README.md) | English

Render Mermaid text as static images in Python. Draw flowcharts, sequence diagrams, relationship models and business diagrams, or use VChart specs and the chart DSL for statistical charts. No Node.js, browser or JavaScript runtime is required.

## Install

Requires CPython 3.13 on Windows AMD64 or Linux x86_64 with glibc 2.28+. Install `py-visactor-mermaid`; import `py_mermaid`.

```shell
python -m pip install py-visactor-mermaid==0.1.1
```

## Draw a flowchart

Save this as a Python file and run it:

```python
from pathlib import Path
from py_mermaid import render

if __name__ == "__main__":
    result = render("flowchart LR\nA[Start] --> B[End]", format="svg")
    Path("flowchart.svg").write_bytes(result.data)
```

Keep the main guard because layout uses process workers. Inside an existing event loop, use `await arender(...)`.

The command line reads a Mermaid file and infers the format from the output extension:

```shell
py-mermaid diagram.mmd -o diagram.svg
```

## Features and scope

- PNG, JPEG, WebP, SVG and PDF output; themes, static rich text and math labels; explicitly supplied images, icons and fonts.
- `render_vchart(spec)` and `vchart <type>` text support py-vchart's 68 static 2D chart types. Available options follow the provider's supported scope.
- `backend="auto"` selects a device; `cpu` and `gpu` are explicit alternatives. Fonts and devices affect text metrics and appearance.
- SVG/PDF output is static. Interaction, animation, Dagre, audio/video, arbitrary browser HTML/CSS extensions and 3D are outside scope.

## Documentation

- [User documentation](https://github.com/py-VisActor/py-mermaid/blob/main/docs/README.en.md): installation, Python API, CLI and resources.
- [VChart guide](https://github.com/py-VisActor/py-mermaid/blob/main/docs/user/VCHART.md) (Chinese): specs, DSL and offline maps.
- [Examples](https://github.com/py-VisActor/py-mermaid/tree/main/examples) · [Releases](https://github.com/py-VisActor/py-mermaid/releases) · [Issues](https://github.com/py-VisActor/py-mermaid/issues).

For repository maintenance and AI coding agents, start with the [developer documentation](https://github.com/py-VisActor/py-mermaid/blob/main/docs/development/README.md).

## License

Original code is [MIT licensed](https://github.com/py-VisActor/py-mermaid/blob/main/LICENSE). See [third-party notices](https://github.com/py-VisActor/py-mermaid/blob/main/THIRD_PARTY_NOTICES.md) for ported code, fonts and resources.
