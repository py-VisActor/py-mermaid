# Quick start

[User documentation](../README.en.md) · [中文](QUICKSTART.md)

Install on CPython 3.13, Windows AMD64 or Linux x86_64 with glibc 2.28+:

```shell
python -m pip install py-visactor-mermaid==0.1.1
```

Dependencies are installed from PyPI. No sibling checkout or Node.js installation is needed.

Save this as `draw.py`, then run `python draw.py`:

```python
from pathlib import Path
from py_mermaid import render

if __name__ == "__main__":
    result = render("flowchart LR\nA[Input] --> B[Output]", format="svg")
    Path("diagram.svg").write_bytes(result.data)
    print(result.width, result.height, result.mime)
```

The main guard is required by process-based layout workers. Supported formats are `png` (default), `jpg`/`jpeg`, `webp`, `svg` and `pdf`. Backend `auto` uses the default device policy; `cpu` and `gpu` select explicitly. Requiring an unavailable GPU raises an error. Text appearance depends on installed fonts and the rendering backend.

For command-line use, create a UTF-8 file `diagram.mmd`:

```text
flowchart LR
    A[Input] --> B[Output]
```

```shell
py-mermaid diagram.mmd -o diagram.svg
py-mermaid diagram.mmd --backend cpu -o diagram.png --metadata diagram.json
python -m py_mermaid diagram.mmd -o diagram.pdf
```

Inside a running event loop, use the async API:

```python
from py_mermaid import arender

async def draw(source):
    result = await arender(source, format="png")
    return result.data
```

Keep native Canvas objects on their creating thread; pass output bytes between threads. See the [API reference](API.md), [VChart guide](VCHART.md) and [resources guide](RESOURCES.md) for further details (Chinese).
