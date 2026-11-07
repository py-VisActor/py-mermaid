"""Five real static formats across every retained detector and requested devices."""
import argparse
from collections import Counter
from io import BytesIO
import json
from pathlib import Path
import re
import traceback
import xml.etree.ElementTree as ET
import zlib
from PIL import Image
from bulk_support import load_cases,resources,write
from run_support import source_identity,file_identity


def main():
    p=argparse.ArgumentParser();p.add_argument('--fixtures',type=Path,nargs='+',required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--profiles',nargs='+',choices=('cpu','auto','gpu'),default=['cpu','auto','gpu'])
    p.add_argument('--case-ids',nargs='+',help='Explicit representative fixtures; keeps the default full 31-kind matrix separate')
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    selected={}
    cases=load_cases(args.fixtures,require_all=not bool(args.case_ids))
    if args.case_ids:
        by_id={c['id']:c for c in cases}
        if len(set(args.case_ids))!=len(args.case_ids) or any(identifier not in by_id or by_id[identifier]['expect']!='render' for identifier in args.case_ids):
            raise ValueError('Explicit export cases must be unique known render inputs')
        selected={identifier:by_id[identifier] for identifier in args.case_ids}
    else:
        for c in cases:
            if c['expect']=='render' and c.get('expectedText') and c['kind'] not in selected:selected[c['kind']]=c
    from py_mermaid import render
    source=source_identity();rows=[]
    for fixture_key,c in selected.items():
        kind=c['kind']
        for backend in args.profiles:
            for fmt in ('png','jpg','webp','svg','pdf'):
                row={'kind':kind,'fixture':c['id'],'backend':backend,'format':fmt,'status':'ERROR'}
                try:
                    r=render(c['source'],config=c.get('config'),resources=resources(c),backend=backend,format=fmt)
                    name=fixture_key+'-'+backend+'.'+fmt
                    artifact=args.out/name
                    with artifact.open('xb') as stream:stream.write(r.data)
                    errors=[]
                    renderer=dict(r.backend)['renderer']
                    if backend!='auto' and renderer!=backend.upper():errors.append('device-mismatch')
                    if fmt in ('png','jpg','webp'):
                        im=Image.open(BytesIO(r.data));im.load()
                        if im.size!=(r.width,r.height):errors.append('raster-dimensions')
                        if len(set(im.convert('RGB').getdata()))<3:errors.append('raster-no-content')
                    elif fmt=='svg':
                        svg=ET.fromstring(r.data)
                        if not svg.tag.endswith('svg'):errors.append('svg-root')
                        if not any(e.tag.endswith(('path','text','image')) for e in svg.iter()):errors.append('svg-no-content')
                        if 'controlExpected' in c and any(e.tag.rsplit('}',1)[-1] in ('input','button','select','textarea','meter','progress','fieldset','foreignObject','script') for e in svg.iter()):
                            errors.append('svg-contains-live-html-host')
                        for dimension,expected in (('width',r.width),('height',r.height)):
                            if abs(float(re.match(r'[\d.]+',svg.attrib[dimension])[0])-expected)>.1:errors.append('svg-'+dimension)
                    else:
                        if not r.data.startswith(b'%PDF-') or b'%%EOF' not in r.data[-100:]:errors.append('pdf-transport')
                        box=re.search(rb'/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)',r.data)
                        if not box or abs(float(box[1])-r.width)>.1 or abs(float(box[2])-r.height)>.1:errors.append('pdf-page-size')
                        streams=[]
                        for data in re.findall(rb'stream\r?\n(.*?)\r?\nendstream',r.data,re.S):
                            try:streams.append(zlib.decompress(data))
                            except zlib.error:streams.append(data)
                        if not any(b'BT' in s or re.search(rb'\b(?:m|l|f|S)\b',s) for s in streams):errors.append('pdf-empty-paint-streams')
                    row.update(status='FAILED' if errors else 'CHECKS_PASSED',errors=errors,actualBackend=dict(r.backend),
                               width=r.width,height=r.height,mime=r.mime,bytes=len(r.data),artifact=name,sha256=file_identity(artifact)['sha256'])
                except Exception as exc:row.update(message=str(exc),exception=type(exc).__name__,traceback=traceback.format_exc())
                rows.append(row);print(json.dumps({k:row[k] for k in ('kind','backend','format','status')}),flush=True)
                write(args.out/'exports.partial.json',{'cases':rows})
    artifact_names=[r['artifact'] for r in rows if r.get('artifact')]
    if len(artifact_names)!=len(set(artifact_names)):raise ValueError('Export artifact filenames collide')
    for row in rows:
        if row['status']=='CHECKS_PASSED' and file_identity(args.out/row['artifact'])!={'sha256':row['sha256'],'bytes':row['bytes']}:
            row.update(status='FAILED',errors=[*row['errors'],'saved-artifact-binding'])
    unchanged=source==source_identity();counts=Counter(r['status'] for r in rows)
    write(args.out/'exports.json',{'schema':'py-mermaid-bulk-exports/v1','source':source,'sourceUnchanged':unchanged,'detectors':len({c['kind'] for c in selected.values()}),
        'requestedCaseIds':args.case_ids,'cases':rows,'counts':dict(counts)})
    return int(not unchanged or any(r['status']!='CHECKS_PASSED' for r in rows) or len(selected)!=(len(args.case_ids) if args.case_ids else 31))


if __name__=='__main__':raise SystemExit(main())
