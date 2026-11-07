"""Collect native numerical observations or compare exact-source/native rows.

P2 defines these commands without executing them. Expected-source contracts,
original observations and native observations remain separate report fields.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from support_b import BASELINE,FIXTURES,native_probe


def close(a,b):
    if isinstance(a,bool) or isinstance(b,bool):return type(a) is type(b) and a==b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-6)
    if type(a) is not type(b):return False
    if isinstance(a,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    if isinstance(a,dict):return a.keys()==b.keys() and all(close(a[k],b[k]) for k in a)
    return a==b


def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=True,indent=2);f.write('\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixtures',type=Path,default=FIXTURES)
    p.add_argument('--collect-native',type=Path)
    p.add_argument('--oracle',type=Path);p.add_argument('--native',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args();doc=json.loads(a.fixtures.read_text(encoding='utf-8'))
    fixture_hash=hashlib.sha256(a.fixtures.read_bytes()).hexdigest()
    if a.collect_native:
        if a.collect_native.exists():p.error('Native observation directory must be new')
        rows=[native_probe(r) for r in doc['pureProbes']]
        write_new(a.collect_native/'native-b.json',{'schema':'py-mermaid-branch-native-observations/v1','baselineSourceTreeSha256':BASELINE,'fixtureSha256':fixture_hash,'python':sys.version,'rows':rows})
        print(json.dumps({'rows':len(rows),'exceptions':sum(r['error'] is not None for r in rows)}));return 0
    if not(a.oracle and a.native and a.out):p.error('Supply --oracle DIR --native DIR --out NEWFILE')
    original=json.loads((a.oracle/'oracle-b.json').read_text(encoding='utf-8'));native=json.loads((a.native/'native-b.json').read_text(encoding='utf-8'))
    if original['fixtureSha256']!=fixture_hash or native['fixtureSha256']!=fixture_hash:raise ValueError('Observation input identity differs')
    expected={r['id']:r for r in doc['pureProbes']};source_rows={r['id']:r for r in original['rows']};native_rows={r['id']:r for r in native['rows']}
    if expected.keys()!=source_rows.keys() or expected.keys()!=native_rows.keys():raise ValueError('Pure probe denominator differs')
    rows=[]
    for id,spec in expected.items():
        source,candidate=source_rows[id],native_rows[id]
        if source['input']!=spec['input'] or candidate['input']!=spec['input']:raise ValueError('Actual input differs for '+id)
        if source['error']:
            classification='UPSTREAM_EXCEPTION' if spec['input'].get('sourceMayThrow') else 'ORACLE_EXCEPTION_REQUIRES_REVIEW'
        elif candidate['error']:classification='CONFIRMED_NUMERICAL_GAP'
        elif close(source['value'],candidate['value']):classification='VERIFIED_OBSERVED_EQUAL'
        elif id.endswith('AUTO-REVERSE'):classification='SOURCE_INTERNAL_DOMAIN_DIFFERENCE'
        else:classification='OBSERVED_DIFFERENCE_REQUIRES_REVIEW'
        rows.append({'id':id,'branch':spec['branch'],'sourceExpected':{'operation':spec['kind'],'fixedOriginalModule':'See oracle identity.modules; no native-generated golden','input':spec['input']},'sourceActual':source,'nativeActual':candidate,'classification':classification})
    report={'schema':'py-mermaid-branch-comparison/v1','group':'B','fixtureSha256':fixture_hash,'sourceIdentity':original['identity'],'rows':rows,'counts':{s:sum(r['classification']==s for r in rows) for s in sorted({r['classification'] for r in rows})}}
    write_new(a.out,report);print(json.dumps(report['counts']))
    return int(any(r['classification'] in ('CONFIRMED_NUMERICAL_GAP','OBSERVED_DIFFERENCE_REQUIRES_REVIEW','ORACLE_EXCEPTION_REQUIRES_REVIEW') for r in rows))


if __name__=='__main__':raise SystemExit(main())
