"""Save reviewable static format samples through the public Python API.

Use workflow.py record/batch for the enclosing immutable execution manifest.
No dependency installation, browser, JS runtime or alternate renderer is used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from py_mermaid import ExportOptions, render

TEXT='''---
title: Static workflow
---
flowchart LR
A@{shape: doc, label: Input} -->|validate| B{Ready?}
B --> C@{shape: cyl, label: Storage}
B -.-> D@{shape: cloud, label: Review}
classDef selected fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e
class A selected
style D fill:#fef3c7,stroke:#92400e
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--backend',choices=('cpu','auto','gpu'),default='cpu')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'workflow.mmd').write_text(TEXT,encoding='utf-8');samples=[]
    for format in ('png','jpg','webp','svg','pdf'):
        result=render(TEXT,format=format,backend=args.backend,export_options=ExportOptions())
        path=args.out/('workflow.'+format);path.write_bytes(result.data)
        samples.append({'file':path.name,'mime':result.mime,'width':result.width,'height':result.height,
                        'bytes':len(result.data),'sha256':hashlib.sha256(result.data).hexdigest(),'backend':dict(result.backend)})
    (args.out/'manifest.json').write_text(json.dumps({'schema':'py-mermaid-static-exports/v1','samples':samples},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'out':str(args.out),'samples':samples},ensure_ascii=False))


if __name__=='__main__':main()
