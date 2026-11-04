"""Render the supported F01.1 branch/merge example with real ELK and Canvas."""
from __future__ import annotations

import argparse
from pathlib import Path

from py_mermaid import render


SOURCE = """flowchart TD
    A[Start] --> B[Left]
    A --> C[Right]
    B --> D[End]
    C --> D
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--backend", choices=("auto", "cpu", "gpu"), default="auto")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output already exists; choose a new path")
    result = render(SOURCE, backend=args.backend)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("xb") as stream:
        stream.write(result.data)
    print(f"{result.mime} {result.width}x{result.height}: {args.out}")


if __name__ == "__main__":
    main()
