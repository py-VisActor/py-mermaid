"""Compare source configuration/content and diagnostic pixels from existing A/B.

This never renders or mutates raw images. Geometry/algorithm tests are separate
source-owned unit gates; browser and Canvas absolute placements need not match.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
from PIL import ImageColor,Image
from bulk_support import load_cases,write
from pixel_compare import load_png,analyze,heatmap


def css_color(value):
    # CSS rgba alpha is normalized 0..1. Pillow's rgba(...,1) instead returns
    # an alpha byte of 1, so normalize this syntax before its generic parser.
    match=re.fullmatch(r'rgba\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)',value,re.I)
    if match:return tuple(float(v) for v in match.groups()[:3])+(float(match[4])*255,)
    color=ImageColor.getrgb(value)
    return color+(255,) if len(color)==3 else color


def equivalent(a,b):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)) and not isinstance(a,bool) and not isinstance(b,bool):return math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-6)
    if isinstance(a,str) and isinstance(b,str):
        try:return all(abs(x-y)<.51 for x,y in zip(css_color(a),css_color(b)))
        except ValueError:return a==b
    if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    return type(a)==type(b) and a==b


def compare_themes(a,b):
    errors=[]
    for name in ('theme','look','layout'):
        if a.get(name)!=b.get(name):errors.append({'field':name,'official':a.get(name),'native':b.get(name)})
    av,bv=a.get('themeVariables',{}),b.get('themeVariables',{})
    for key in sorted(set(av)|set(bv)):
        if key not in av or key not in bv or not equivalent(av.get(key),bv.get(key)):
            errors.append({'field':'themeVariables.'+key,'official':av.get(key),'native':bv.get(key),
                           'presence':{'official':key in av,'native':key in bv}})
    return errors


def main():
    p=argparse.ArgumentParser();p.add_argument('--fixtures',nargs='+',type=Path,required=True)
    p.add_argument('--oracle',type=Path,required=True);p.add_argument('--native',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--pixels',action='store_true')
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False);cases=load_cases(args.fixtures)
    manifest=json.loads((args.native/'results.json').read_text('utf-8'));known={r['id']:r for r in manifest['cases']};rows=[]
    for case in cases:
        if case['id'] not in known:continue
        id=case['id'];row={'id':id,'kind':case['kind'],'status':'NOT_COMPARED','errors':[]}
        official=args.oracle/(id+'.json');native=args.native/(id+'.scene.json')
        if case['expect']=='excluded_by_static_scope':
            row['status']='EXCLUDED'
        elif known[id]['status'] in ('FAILED','ERROR'):
            row['status']='REVIEW';row['errors'].append('native-checks-failed')
        elif case['expect']=='upstream_defect':
            if case.get('nativeMustRender') and known[id]['status']!='CHECKS_PASSED':row['errors'].append('native-must-render')
            if case.get('officialExpect')=='content_loss':
                from source_defect_checks import content_loss_errors
                row['errors']+=content_loss_errors(case,args.oracle)
            elif case.get('officialExpect')=='degenerate_render':
                svg=args.oracle/(id+'.svg');contract=case.get('sourceGeometry',{})
                attributes=contract.get('nonfiniteAttributes',[])
                text=svg.read_text('utf-8') if svg.is_file() else ''
                matches=re.findall(r'\b(?:'+('|'.join(re.escape(x) for x in attributes) or '(?!)')+r')\s*=\s*"(?:NaN|[+-]?Infinity)"',text)
                if len(matches)<contract.get('minimumMatches',1):row['errors'].append('original-degenerate-geometry-not-confirmed')
                row['sourceInvalidAttributeCount']=len(matches)
            else:
                error=args.oracle/(id+'.error.json')
                source_error=json.loads(error.read_text('utf-8')) if error.is_file() else {}
                if not source_error.get('sourceError'):row['errors'].append('original-runtime-error-not-confirmed')
            row['status']='REVIEW' if row['errors'] else 'UPSTREAM_CONFIRMED'
        elif case['expect'] in ('syntax_error','error'):
            error=args.oracle/(id+'.error.json')
            source_error=json.loads(error.read_text('utf-8')) if error.is_file() else {}
            if not source_error.get('sourceError'):row['errors'].append('original-rejection-not-confirmed')
            row['status']='REVIEW' if row['errors'] else 'SOURCE_CHECKS_PASSED'
        elif official.is_file() and native.is_file() and case['expect']=='render':
            a=json.loads(official.read_text('utf-8'));b=json.loads(native.read_text('utf-8'))
            # Theme parity is checked where the common source pipeline builds
            # these variables; ZenUML uses original core palette instead.
            if case['kind']!='zenuml':row['configurationDifferences']=compare_themes(a['config'],b['effectiveConfig'])
            else:row['configurationDifferences']=[]
            # All source-owned expected visible strings must also be seen by
            # the official implementation; otherwise fixture interpretation
            # needs review and cannot silently lower the native denominator.
            text=re.sub(r'\s+','', ''.join(t['text'] or '' for t in a.get('texts',[])))
            for expected in case.get('expectedText',[]):
                if re.sub(r'\s+','',expected) not in text:row['errors'].append('official-visible-text-disagrees:'+expected)
            if case.get('expectedEmpty'):
                empty=case['expectedEmpty'];im=Image.open(args.oracle/(id+'.png')).convert('RGBA')
                color=ImageColor.getcolor(empty['background'],'RGBA')
                size_mismatch=('width' in empty or 'height' in empty) and im.size!=(empty.get('width'),empty.get('height'))
                if size_mismatch or any(bounds!=(c,c) for bounds,c in zip(im.getextrema(),color)):
                    row['errors'].append('official-does-not-confirm-source-empty-contract')
            row['status']='REVIEW' if row['errors'] or row['configurationDifferences'] else 'SOURCE_CHECKS_PASSED'
            if args.pixels:
                try:
                    ai,am,_=load_png(args.oracle/(id+'.png'),64_000_000);bi,bm,_=load_png(args.native/(id+'.png'),64_000_000)
                    metrics,images=analyze(ai,bi,max_pixels=64_000_000)
                    row['pixels']={'status':'DIAGNOSTIC_ONLY','reference':am,'candidate':bm,'metrics':metrics}
                    heatmap(images['maximum'],tuple(metrics['unionCanvasSize']),images['coverage'],4,0).save(args.out/(id+'.diff.png'))
                except Exception as exc:row['pixels']={'status':'TOOL_ERROR','error':str(exc)};row['status']='REVIEW'
        elif case['expect']=='render':
            row['status']='REVIEW'
            row['errors']=[name for name,path in (('missing-official-evidence',official),('missing-native-evidence',native)) if not path.is_file()]
        rows.append(row);write(args.out/(id+'.comparison.json'),row)
    write(args.out/'comparison.json',{'schema':'py-mermaid-bulk-comparison/v1','source':manifest['source'],'backend':manifest['backend'],'cases':rows,
        'counts':dict(Counter(r['status'] for r in rows)),'pixelFunctionalStatus':'NOT_EVALUATED'})
    print(json.dumps({'counts':dict(Counter(r['status'] for r in rows))}))
    return int(any(r['status']=='REVIEW' for r in rows))


if __name__=='__main__':raise SystemExit(main())
