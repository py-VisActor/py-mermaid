"""Freeze all retained source-defined fixtures without executing product behavior."""
import argparse
from collections import Counter
from pathlib import Path
from bulk_support import load_cases,browser_resources,write
from run_support import ROOT,file_identity,source_identity


def main():
    p=argparse.ArgumentParser();p.add_argument('--fixtures',type=Path,nargs='+',default=[*sorted((ROOT/'tests/bulk').glob('cases-*.json')),*sorted((ROOT/'tests/html_host').glob('cases*.json'))])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--allow-subset',action='store_true',help='Explicit targeted regression; does not claim all retained kinds')
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);cases=load_cases(args.fixtures,require_all=not args.allow_subset)
    write(args.out/'cases.json',{'schema':'py-mermaid-bulk-cases/v1','group':'combined','cases':cases})
    # Preserve original group on each case; native load_cases uses this field.
    write(args.out/'browser-cases.json',{'schema':'py-mermaid-bulk-cases/v1','group':'combined',
        'cases':[{**c,'browserResources':browser_resources(c)} for c in cases]})
    write(args.out/'fixture-identity.json',{'source':source_identity(),'inputs':{str(f):file_identity(f) for f in args.fixtures},
        'counts':dict(Counter(c['kind'] for c in cases)),'expectations':dict(Counter(c['expect'] for c in cases)),
        'groupCounts':dict(Counter(c['group'] for c in cases)),'productBehaviorExecuted':False,
        'allRetainedKindsRequired':not args.allow_subset})
    print({'cases':len(cases),'kinds':len(set(c['kind'] for c in cases))})


if __name__=='__main__':main()
