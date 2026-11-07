"""Collect current B observations or compare separate fixed-source evidence.

No test expectation is generated from native output. Nonzero exits preserve all
observed mismatches. Windows controlled aware DST is explicitly distinguished
from Linux real-TZ/public-render evidence.
"""
from __future__ import annotations
import argparse
import asyncio
from collections.abc import Mapping
from dataclasses import fields,is_dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('closure_support_B',ROOT/'tests/closure/support_B.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)

def load(path):return json.loads(Path(path).read_text(encoding='utf8'))
def pure(value):
    """Transport immutable observations; preserve scalar types and order.

    Mapping precedes dataclass because FrozenLookup is both. Unknown host or
    native objects are errors, never silently stringified as successful data.
    """
    if isinstance(value,Mapping):
        if any(type(key) is not str for key in value):raise TypeError('JSON observation keys must be strings')
        return {key:pure(item) for key,item in value.items()}
    if is_dataclass(value) and not isinstance(value,type):
        return {field.name:pure(getattr(value,field.name)) for field in fields(value)}
    if isinstance(value,(tuple,list)):return [pure(item) for item in value]
    if value is None or type(value) in (str,bool,int):return value
    if type(value) is float and math.isfinite(value):return value
    raise TypeError('Observation contains unsupported/nonfinite value: '+type(value).__name__)

def save(path,value):
    with Path(path).open('x',encoding='utf8') as stream:json.dump(pure(value),stream,ensure_ascii=True,allow_nan=False,indent=2);stream.write('\n')
def close(a,b):
    if type(a) is bool or type(b) is bool:return type(a) is type(b) and a==b
    if isinstance(a,(float,int)) and isinstance(b,(float,int)):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-5)
    if type(a) is not type(b):return False
    if isinstance(a,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    if isinstance(a,dict):return a.keys()==b.keys() and all(close(a[k],b[k]) for k in a)
    return a==b


async def collect_public_paint(row,out):
    from py_mermaid import arender
    result=await arender(row['source'],config=row['config'],backend='cpu',format='png')
    image=out/(row['id']+'.png');image.write_bytes(result.data)
    trace=pure(result.trace)
    return {'trace':trace,'image':{'name':image.name,'sha256':hashlib.sha256(result.data).hexdigest(),'bytes':len(result.data)},
            'width':result.width,'height':result.height,
            'nodes':pure(result.diagram.model.graph.nodes) if row['kind']=='agentflow' else []}

def color(value):
    from py_mermaid.config.colors import channels
    try:return tuple(round(v*255) for v in channels(value)[:3])
    except Exception:return None

def public_paint_checks(row,a,b,native_dir):
    if 'publicPaint' not in a or 'publicPaint' not in b:
        return [{'kind':'fresh-public-paint-observer-required','pass':False,'reason':'Old capture cannot prove new paint obligations; recapture and refreeze original JSON.'}]
    source=a['publicPaint'];current=b['publicPaint'];trace=current['trace'];checks=[]
    from PIL import Image
    path=native_dir/current['image']['name'];data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=current['image']['sha256']:raise ValueError('Native raw paint image SHA drift')
    image=Image.open(path).convert('RGB')
    def pixels(box,predicate,exclude_center=False):
        x,y,w,h=(box[k] for k in ('x','y','width','height'));cx=x+w/2
        return sum(predicate(image.getpixel((px,py))) for py in range(max(0,math.ceil(y)),min(image.height,math.floor(y+h)))
            for px in range(max(0,math.ceil(x)),min(image.width,math.floor(x+w))) if not exclude_center or abs(px-cx)>3)
    if row['kind']=='gantt':
        ticks=[e for e in trace if e['semantic_id'].startswith('tick-') and e['text'] is not None]
        actual=[e['text'] for e in ticks];expected=[v['text'] for v in source['ticks']]
        checks.append({'kind':'public-axis-labels-from-original-SVG','pass':actual==expected,'source':expected,'native':actual})
        for e in ticks:checks.append({'kind':'actual-tick-glyph-ROI','id':e['semantic_id'],'pass':bool(e['box']) and pixels(e['box'],lambda p:min(p)<200,True)>5})
    if row['kind']=='gitGraph':
        shells=[e for e in source['cherries'] if e['tag']=='circle' and float(e['numeric'].get('r',0))>=7]
        fruits=[e for e in trace if '-cherry-' in e['semantic_id'] and '-stem-' not in e['semantic_id']]
        stems=[e for e in trace if '-cherry-stem-' in e['semantic_id']]
        ids={e['semantic_id'].split('-cherry-')[0] for e in fruits}
        native_shells=[e for e in trace if e['semantic_id'] in ids and e['kind']=='commit']
        checks.append({'kind':'cherry-component-denominator','pass':len(native_shells)==len(shells) and len(fruits)==len(shells)*2 and len(stems)==len(shells)*2})
        # Match role multisets rather than random source auto-commit IDs.
        checks.append({'kind':'cherry-shell-parent-inheritance','pass':sorted(color(e['fill']) for e in native_shells)==sorted(color(e['fill']) for e in shells)})
        source_fruits=[e for e in source['cherries'] if e['tag']=='circle' and float(e['numeric'].get('r',0))<7]
        source_stems=[e for e in source['cherries'] if e['tag']=='line']
        checks.append({'kind':'cherry-fruit-explicit-fill','pass':sorted(color(e['fill']) for e in fruits)==sorted(color(e['fill']) for e in source_fruits)})
        checks.append({'kind':'cherry-stem-explicit-stroke','pass':sorted((color(e['stroke']),e['stroke_width']) for e in stems)==sorted((color(e['stroke']),float(e['strokeWidth'].removesuffix('px'))) for e in source_stems)})
        for shell in native_shells:
            box=shell['box'];cx=box['x']+box['width']/2;cy=box['y']+box['height']/2
            expected=color(shell['fill']);ring=white=0
            for py in range(max(0,math.ceil(cy-10)),min(image.height,math.floor(cy+10))):
                for px in range(max(0,math.ceil(cx-10)),min(image.width,math.floor(cx+10))):
                    d=math.hypot(px+.5-cx,py+.5-cy);p=image.getpixel((px,py))
                    if 7<d<9 and expected and max(abs(p[i]-expected[i]) for i in range(3))<25:ring+=1
                    if d<6.7 and min(p)>230:white+=1
            checks.append({'kind':'actual-cherry-shell-and-white-fruit-ROI','id':shell['semantic_id'],'pass':ring>30 and white>8,'ringPixels':ring,'fruitPixels':white})
    if row['kind']=='agentflow':
        collapsed=[e for e in source['collapsed'] if 'flow-collapsed' in e['classes'].split()]
        source_ids={n['id'] for n in a['snapshot']['nodes'] if n.get('shape')=='collapsedGroup'}
        native_ids={n['id'] for n in current['nodes'] if n.get('shape')=='collapsedGroup'}
        checks.append({'kind':'collapsed-model-identity','pass':source_ids==native_ids})
        nodes=[e for e in trace if e['kind']=='node' and e['semantic_id'] in source_ids]
        for original in collapsed:
            # Ordinary X/Y do not make the collapsed Outer ambiguous. This
            # frozen source observer has no owner ID per primitive, so retain
            # explicit failure for multiple collapsed paint owners.
            if len(collapsed)!=1 or len(source_ids)!=1 or len(nodes)!=1:
                checks.append({'kind':'collapsed-paint-unambiguous-match','pass':False});continue
            node=nodes[0]
            checks.append({'kind':'collapsed-source-palette','pass':color(node['fill'])==color(original['fill']) and color(node['stroke'])==color(original['stroke']),'source':original,'native':node})
        # Metadata is a public immutable model obligation, independently of
        # whether a temporary style happened to paint the expected color.
        for node in current['nodes']:
            if node.get('shape')=='collapsedGroup':checks.append({'kind':'collapsed-containerType-flow','pass':dict(node.get('metadata',())).get('containerType')=='flow'})
    return checks

async def collect(args,doc):
    out=args.collect_native;out.mkdir(parents=True,exist_ok=False)
    environment=support.set_timezone(args.timezone)
    pure=[]
    for row in doc['pureProbes']:
        try:value,error=support.native_value(row),None
        except Exception as exc:value,error=None,{'name':type(exc).__name__,'message':str(exc)}
        pure.append({'id':row['id'],'kind':row['kind'],'input':row['input'],'value':value,'error':error})
    extras=[]
    for row in doc['sourceProbes']:
        try:value,error=support.native_extra(row),None
        except Exception as exc:value,error=None,{'name':type(exc).__name__,'message':str(exc)}
        extras.append({'id':row['id'],'kind':row['kind'],'input':row['input'],'value':value,'error':error,
                       'timezone':row['timezone'],'observationMode':'aware-input-controlled-host-conversion' if row['kind']=='dayAdd' else 'actual-host'})
    save(out/'native-values.json',{'fixtureSha256':args.fixture_hash,'environment':environment,'rows':pure})
    save(out/'native-extra.json',{'fixtureSha256':args.fixture_hash,'rows':extras})
    cases=[]
    if args.cases:
        for row in doc['cases']:
            zone=row.get('closure',{}).get('timezone',args.timezone)
            if row.get('closure',{}).get('nativeRequiresRealTZ') and not hasattr(time,'tzset'):
                actual={'id':row['id'],'status':'NOT_VERIFIED','reason':'Windows has no tzset; Linux real-TZ public rendering is separately required. Aware DST arithmetic is not presented as a system timezone switch.'}
            else:
                actual_timezone=support.set_timezone(zone)
                try:
                    actual=await support.layout_observation(row)
                    actual['timezoneEnvironment']=actual_timezone
                    actual['publicPaint']=await collect_public_paint(row,out)
                except Exception as exc:actual={'id':row['id'],'status':'NATIVE_ERROR','error':{'name':type(exc).__name__,'message':str(exc)}}
                finally:support.set_timezone(args.timezone)
            save(out/(row['id']+'.json'),actual);cases.append({'id':row['id'],'status':actual['status']})
    save(out/'manifest.json',{'schema':'py-mermaid-closure-B-native/v1','fixtureSha256':args.fixture_hash,'platform':platform.platform(),'environment':environment,'cases':cases})
    print(json.dumps({'pure':len(pure),'extras':len(extras),'cases':len(cases),'nativeErrors':sum(r['status']=='NATIVE_ERROR' for r in cases)}))

def unique(rows):
    result={r['id']:r for r in rows}
    if len(result)!=len(rows):raise ValueError('Duplicate observation IDs')
    return result

def compare(args,doc):
    source=load(args.oracle/'values/oracle-b.json');native=load(args.native/'native-values.json')
    extras=load(args.oracle/'source-extra.json');native_extra=load(args.native/'native-extra.json')
    if any(x['fixtureSha256']!=args.fixture_hash for x in (source,native,extras,native_extra)):raise ValueError('Input fixture identity drift')
    rows=[]
    for expected,original,current in ((doc['pureProbes'],source['rows'],native['rows']),(doc['sourceProbes'],extras['rows'],native_extra['rows'])):
        a,b=unique(original),unique(current)
        if set(a)!=set(b) or set(a)!={r['id'] for r in expected}:raise ValueError('Source/native row denominator differs')
        for row in expected:
            left,right=a[row['id']],b[row['id']]
            if left['input']!=row['input'] or right['input']!=row['input']:raise ValueError('Input mutation')
            if left['error']:
                verdict='SOURCE_EXCEPTION' if row['input'].get('sourceMayThrow') else 'SOURCE_ERROR_REQUIRES_REVIEW'
            else:verdict='PASS' if not right['error'] and close(left['value'],right['value']) else 'FAIL'
            if row.get('expected') and verdict=='PASS':
                if any(left['value'].get(k)!=v for k,v in row['expected'].items()):verdict='SOURCE_CONTRADICTS_LITERAL_EXPECTATION'
            rows.append({'id':row['id'],'branch':row.get('branch',row['kind']),'status':verdict,'sourceExpected':row.get('expected','Fixed original values; independent from native'),'sourceActual':left,'nativeActual':right})
    case_rows=[]
    if args.cases:
        for row in doc['cases']:
            a,b=load(args.oracle/(row['id']+'.json')),load(args.native/(row['id']+'.json'))
            checks=[]
            if b['status']=='NOT_VERIFIED':
                status='FAIL' if args.require_real_tz else 'NOT_VERIFIED'
            elif a['status']!='CAPTURED' or b['status']!='OBSERVED':status='FAIL'
            else:
                if row['kind']=='gantt':
                    # This validates the actual public browser-Date fallback
                    # and task compiler, separately from strict Dayjs helpers.
                    x=unique(a['snapshot']['tasks']);y=unique(b['taskDates'])
                    checks.append({'kind':'public-task-denominator','pass':set(x)==set(y)})
                    for key in x.keys() & y.keys():
                        checks.append({'kind':'public-start-end-date-and-epoch','id':key,
                                       'pass':close(x[key],y[key]),'source':x[key],'native':y[key]})
                if row['kind']=='agentflow':
                    source_pairs=sorted((e['start'],e['end']) for e in a['snapshot']['edges'])
                    native_pairs=sorted((e['source'],e['target']) for e in b['edges'])
                    checks.append({'kind':'actual-edge-topology','pass':source_pairs==native_pairs,'source':source_pairs,'native':native_pairs})
                    checks.append({'kind':'no-unrouted-ids','pass':{e['id'] for e in b['edges']}==set(b['routedEdges'])})
                    condition=row.get('closure',{})
                    if condition.get('groupAlgorithm'):
                        def group(raw):
                            children=[c for c in raw['children'] if 'children' in c]
                            if len(children)!=1:raise ValueError('Expected exactly one actual group input')
                            return children[0].get('layoutOptions',{})
                        if len(a['elkInputs'])!=1 or len(b['rawInputs'])!=1:raise ValueError('Original/native did not invoke exactly one real ELK layout')
                        x,y=group(a['elkInputs'][0]),group(b['rawInputs'][0])
                        if condition['cross']:
                            for key in ('elk.algorithm','elk.aspectRatio','elk.contentAlignment','elk.expandNodes',
                                        'elk.rectpacking.trybox','elk.rectpacking.widthApproximation.strategy'):
                                checks.append({'kind':'cross-clear-'+key,'pass':key not in x and key not in y,'source':x.get(key),'native':y.get(key)})
                            for key,expected in [('elk.hierarchyHandling','INCLUDE_CHILDREN'),('spacing.baseValue',24),('spacing.nodeNode',50)]:
                                checks.append({'kind':'restored-'+key,'pass':x.get(key)==y.get(key)==expected,'source':x.get(key),'native':y.get(key)})
                        else:
                            checks.append({'kind':'actual-group-algorithm','pass':x.get('elk.algorithm')==y.get('elk.algorithm')==condition['groupAlgorithm'],'source':x.get('elk.algorithm'),'native':y.get('elk.algorithm')})
                if row['kind']=='gitGraph':
                    vertical='gitGraph LR' not in row['source'];rotate=row['config']['gitGraph']['rotateCommitLabel']
                    source_labels=[v for v in a['labels'] if re.search(r'\bbranch-label\d+\b',v.get('classes') or '')]
                    labels={v['id']:v['values'] for v in b['labels'] if v['kind']=='text'}
                    positions=dict(b['layout']['branches'])
                    checks.append({'kind':'source-branch-label-count','pass':len(source_labels)==len(positions)})
                    original_positions=[]
                    for source_label in source_labels:
                        name=source_label['text'];key='branch-label-'+name
                        checks.append({'kind':'source-label-visible-'+name,'pass':key in labels and labels[key]['text']==name})
                        match=re.search(r'translate\(\s*([+\-.\deE]+)[ ,]+([+\-.\deE]+)\s*\)',source_label.get('transform') or '')
                        if match:
                            x,y=map(float,match.groups());box=source_label['box']
                            # Source drawBranches(default theme) placement is
                            # inverted from its actual SVG transform, not from
                            # any Python positions or candidate measurement.
                            cross=x+box['width']/2+5 if vertical else y+box['height']/2+4
                            original_positions.append((name,cross,box['width']))
                        else:checks.append({'kind':'source-original-transform-present','pass':False})
                    for previous,current in zip(original_positions,original_positions[1:]):
                        expected=50+(40 if rotate else 0)+(previous[2]/2 if vertical else 0)
                        checks.append({'kind':'original-source-lane-step','pass':abs(current[1]-previous[1]-expected)<.1,
                                       'sourceDelta':current[1]-previous[1],'sourceExpected':expected})
                    names=list(positions)
                    for previous,name in zip(names,names[1:]):
                        expected=50+(40 if rotate else 0)+(labels['branch-label-'+previous]['width']/2 if vertical else 0)
                        checks.append({'kind':'native-lane-step','pass':close(positions[name]-positions[previous],expected)})
                    source_text=[v['text'] for v in a['texts']]
                    for tag in ('last','long-release','first'):
                        checks.append({'kind':'source-tag-'+tag,'pass':tag in source_text and any(v.get('text')==tag for v in labels.values())})
                    for value in (v for k,v in labels.items() if '-tag-' in k):
                        checks.append({'kind':'source-tag-angle','pass':value['rotation']==(45 if vertical else 0)})
                checks.extend(public_paint_checks(row,a,b,args.native))
                status='PASS' if all(c['pass'] for c in checks) else 'FAIL'
            case_rows.append({'id':row['id'],'status':status,'checks':checks,'sourceFile':str(args.oracle/(row['id']+'.json')),'nativeFile':str(args.native/(row['id']+'.json'))})
    result={'schema':'py-mermaid-closure-B-comparison/v1','fixtureSha256':args.fixture_hash,'sourceIdentity':source['identity'],
            'status':'FAIL' if any(r['status'] not in ('PASS','SOURCE_EXCEPTION','NOT_VERIFIED') for r in rows+case_rows) else 'PASS_WITH_EXPLICIT_UNVERIFIED' if any(r['status']=='NOT_VERIFIED' for r in case_rows) else 'PASS',
            'rows':rows,'cases':case_rows,'counts':{status:sum(r['status']==status for r in rows+case_rows) for status in sorted({r['status'] for r in rows+case_rows})}}
    save(args.out,result);print(json.dumps(result['counts']));return int(result['status']=='FAIL')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,default=ROOT/'tests/closure/cases-B.json')
    parser.add_argument('--collect-native',type=Path);parser.add_argument('--timezone',default='UTC')
    parser.add_argument('--cases',action='store_true');parser.add_argument('--require-real-tz',action='store_true')
    parser.add_argument('--oracle',type=Path);parser.add_argument('--native',type=Path);parser.add_argument('--out',type=Path)
    args=parser.parse_args();args.fixture_hash=hashlib.sha256(args.fixtures.read_bytes()).hexdigest();doc=load(args.fixtures)
    if args.collect_native:asyncio.run(collect(args,doc));return 0
    if not(args.oracle and args.native and args.out):parser.error('Supply --collect-native NEWDIR or --oracle DIR --native DIR --out NEWJSON')
    return compare(args,doc)

if __name__=='__main__':raise SystemExit(main())
