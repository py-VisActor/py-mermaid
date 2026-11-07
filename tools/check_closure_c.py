"""Compare closed source/native Sequence closure artifacts; never renders.
CLI --fixtures --oracle --native --out NEWFILE. Source predicate failures stay
SOURCE_EXPECTATION_MISMATCH and cannot be promoted to a native functional gap.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'/'closure'))
from support_C import errors,source_projection,native_projection

def read(p):return json.loads(p.read_text('utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--fixtures',type=Path,default=ROOT/'tests/closure/cases-C.json')
 parser.add_argument('--oracle',type=Path,required=True);parser.add_argument('--native',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
 a=parser.parse_args()
 if a.out.exists():raise ValueError('Output must be new; closed evidence is immutable')
 fixtures=read(a.fixtures)['cases'];manifest=read(a.native/'results.json');available={c['id']:c for c in manifest['cases']}
 expected_source='dab675b768488413fd60bb07b656d28ef8e2e6c4f34af45056eec9763c98f0f4'
 # P3 may contain an authorized later repair; bind its explicit manifest SHA,
 # never assert that the initial P1 identity is a post-repair acceptance.
 rows=[]
 for case in fixtures:
  row={'id':case['id'],'expected':case['closureProbe'],'status':'TOOL_ERROR'}
  try:
   if case['id'] not in available:raise ValueError('Native fixture missing')
   op=a.oracle/(case['id']+'.json');sp=a.oracle/(case['id']+'.svg');ap=a.oracle/(case['id']+'.png');np=a.native/(case['id']+'.scene.json');bp=a.native/(case['id']+'.png')
   original=read(op);scene=read(np)
   if original.get('status') in ('ERROR','FAIL'):raise ValueError('Original failed to render')
   source=source_projection(sp.read_text('utf8'),original);native=native_projection(scene)
   with Image.open(ap) as im:source_errors=errors(case['closureProbe'],source,im.convert('RGB'))
   with Image.open(bp) as im:native_errors=errors(case['closureProbe'],native,im.convert('RGB'))
   row.update(sourceActual={k:v for k,v in source.items() if k!='trace'},nativeActual={k:v for k,v in native.items() if k!='trace'},sourceErrors=source_errors,nativeErrors=native_errors,
              evidence=[{'path':str(p.resolve()),'sha256':digest(p),'bytes':p.stat().st_size} for p in (op,sp,ap,np,bp)],
              status='SOURCE_EXPECTATION_MISMATCH' if source_errors else 'NATIVE_PREDICATE_DIFFERENCE' if native_errors else 'VERIFIED')
  except Exception as exc:row['error']=type(exc).__name__+': '+str(exc)
  rows.append(row)
 out={'schema':'py-mermaid-closure-C-verification/v1','status':'PASS' if all(r['status']=='VERIFIED' for r in rows) else 'FAIL','baselineSourceTreeSha256':expected_source,
      'nativeSource':manifest.get('source'),'nativeSourceUnchanged':manifest.get('sourceUnchanged'),'fixtureCount':len(fixtures),'fixtures':{'path':str(a.fixtures.resolve()),'sha256':digest(a.fixtures)},'cases':rows,
      'limits':['Coordinates are source-specific predicates; visible/manual classification remains distinct from numerical difference.','Arbitrary CSS/HTML extensions and unclosed activation adaptation are not asserted as new source-equivalent features.']}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,ensure_ascii=True,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'status':out['status'],'cases':len(rows),'out':str(a.out)}))
 return 0 if out['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
