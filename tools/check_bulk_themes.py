"""Whole original theme-variable parity; no product rendering or Canvas."""
import argparse
import json
from pathlib import Path
from bulk_compare import equivalent
from bulk_support import write


def main():
    p=argparse.ArgumentParser();p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--oracle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    from py_mermaid.config.themes import get_theme_variables
    cases=json.loads(a.fixtures.read_text('utf-8'))['cases'];by_id={c['id']:c for c in cases}
    original=json.loads(a.oracle.read_text('utf-8'));rows=[]
    for c in original['cases']:
        fixture=by_id[c['id']];cfg=fixture['config'];native=get_theme_variables(cfg['theme'],cfg.get('themeVariables'))
        actual=c['themeVariables'];diff=[]
        for key in sorted(set(native)|set(actual)):
            if key not in actual or key not in native or not equivalent(actual.get(key),native.get(key)):
                diff.append({'key':key,'original':actual.get(key),'native':native.get(key),'presence':{'original':key in actual,'native':key in native}})
        rows.append({'id':c['id'],'differences':diff,'variables':len(actual)})
    write(a.out,{'cases':rows,'failed':sum(bool(c['differences']) for c in rows)})
    print(json.dumps({'cases':len(rows),'failed':sum(bool(c['differences']) for c in rows)}))
    return int(any(c['differences'] for c in rows))


if __name__=='__main__':raise SystemExit(main())
