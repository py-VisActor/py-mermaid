"""F01.3 frontmatter, directive, theme and rich-label Canvas example."""
from __future__ import annotations

import argparse
from pathlib import Path

from py_mermaid import render

SOURCE = '''---
title: Configuration and rich labels
config:
  theme: forest
  htmlLabels: true
  flowchart:
    wrappingWidth: 180
---
%%{init: {"themeVariables": {"fontFamily": "Arial, sans-serif"}}}%%
flowchart LR
subgraph INPUT[Input]
  A["`**Start** with *Markdown*`"] -->|"`*Approved*`"| B["<b>HTML label</b><br/><span style='color:#146c43'>第二行</span>"]
end
B --> C[(Storage)]
'''


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--backend',choices=('auto','cpu','gpu'),default='auto')
    args=parser.parse_args()
    if args.out.exists():parser.error('output already exists; choose a new path')
    result=render(SOURCE,backend=args.backend)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('xb') as stream:stream.write(result.data)
    print(f'{result.mime} {result.width}x{result.height}: {args.out}')


if __name__=='__main__':
    main()
