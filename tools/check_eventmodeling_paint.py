"""Compare only fixed-source-observed Event nonocclusion, without rendering."""
import argparse,copy,hashlib,json,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from closure.test_eventmodeling import source_projection,native_projection,relation_errors,intersection,raw_data_errors

def read(p):return json.loads(p.read_text('utf8'))
def identity(p):return {'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--oracle',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise ValueError('Output must be new')
 rows=[]
 for c in read(a.fixtures)['cases']:
  row={'id':c['id'],'status':'TOOL_ERROR'}
  try:
   id=c['id'];op=a.oracle/(id+'.json');sp=a.oracle/(id+'.svg');np=a.native/(id+'.scene.json');bp=a.native/(id+'.png')
   source=source_projection(read(op),sp.read_text('utf8'));native=native_projection(read(np),source)
   with Image.open(bp) as im:
    errs=relation_errors(source,native,im)+raw_data_errors(source,native);fault=copy.deepcopy(native)
    pairs=[(i,j) for i,x in enumerate(source['cards']) for j,y in enumerate(source['cards'][i+1:],i+1) if abs(x['box']['y']-y['box']['y'])<.01 and intersection(x['box'],y['box'])==0]
    if pairs:
     i,j=pairs[0];fault[j]['box']={**fault[i]['box'],'x':fault[i]['box']['x']+5}
    controls={'whiteGlyphLossRejected':bool(relation_errors(source,native,Image.new('RGB',im.size,'white'))),'observedPairOverlapRejected':not pairs or bool(relation_errors(source,fault,im))}
   row.update(status='PASS' if not errs and all(controls.values()) else 'FAIL',sourceActual=source,nativeActual=native,errors=errs,negativeControls=controls,sourceObservedPairs=pairs,evidence=[identity(p) for p in [op,sp,np,bp]])
  except Exception as e:row['error']=type(e).__name__+': '+str(e)
  rows.append(row)
 out={'schema':'py-mermaid-event-paint-verification/v1','status':'PASS' if all(c['status']=='PASS' for c in rows) else 'FAIL','cases':rows,'fixture':identity(a.fixtures),'nativeSource':read(a.native/'results.json').get('source')};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':out['status'],'cases':len(rows)}));return int(out['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
