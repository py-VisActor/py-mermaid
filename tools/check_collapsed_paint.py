from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/closure'))
from support_collapsed import *
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixtures',required=True,type=Path);p.add_argument('--oracle',required=True,type=Path);p.add_argument('--native',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():raise ValueError('Output must be new')
 rows=[]
 for case in read(a.fixtures)['cases']:
  row={'id':case['id'],'status':'TOOL_ERROR'}
  try:
   id=case['id'];op=a.oracle/(id+'.json');sp=a.oracle/(id+'.svg');np=a.native/(id+'.scene.json');png=a.native/(id+'.png')
   original=source_projection(read(op),sp.read_text('utf8'));native=native_projection(read(np),case['collapsedProbe']['nodeId'])
   with Image.open(png) as image:
    image=image.convert('RGB');differences=errors(original,native,image,case['collapsedProbe']['radius'])
    blank=Image.new('RGB',image.size,'white');no_dots=image.copy();draw=ImageDraw.Draw(no_dots)
    for dot in native['dots']:
     b=dot['box'];draw.rectangle((math.floor(b['x'])-1,math.floor(b['y'])-1,math.ceil(b['x']+b['width'])+1,math.ceil(b['y']+b['height'])+1),fill=rgb(original['body']['fill']) or 'white')
    wrong=copy.deepcopy(native);wrong['dots'][0]['opacity']=0
    controls={'whiteNoopRejected':bool(errors(original,native,blank,case['collapsedProbe']['radius'])),'lostDotsRejected':bool(errors(original,native,no_dots,case['collapsedProbe']['radius'])),'wrongDotAlphaRejected':bool(errors(original,wrong,image,case['collapsedProbe']['radius']))}
   row.update(sourceActual=original,nativeActual=native,errors=differences,negativeControls=controls,status='PASS' if not differences and all(controls.values()) else 'FAIL',evidence=[identity(f) for f in (op,sp,np,png)])
  except Exception as exc:row['error']=type(exc).__name__+': '+str(exc)
  rows.append(row)
 result={'schema':'py-mermaid-collapsed-paint-verification/v1','status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL','sourceIndependent':True,'fixture':identity(a.fixtures),'nativeSource':read(a.native/'results.json').get('source'),'cases':rows}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':result['status'],'cases':len(rows)}));return int(result['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
