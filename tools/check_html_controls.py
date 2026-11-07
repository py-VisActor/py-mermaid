"""Compare original initial DOM states, immutable native controls and actual ink.

This reads raw evidence; it never renders, alters images or promotes pixel
similarity into acceptance. Dedicated layout/Canvas tests cover each affordance.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from io import BytesIO
import json
import math
from pathlib import Path
import re

from PIL import Image
from bulk_support import load_cases, write
from run_support import file_identity


def _same(a,b):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)) and not isinstance(a,bool) and not isinstance(b,bool):
        return math.isclose(a,b,abs_tol=1e-9,rel_tol=1e-9)
    return type(a)==type(b) and a==b


def _source_value(control,key):
    if key=='fraction':
        if control['tag']=='progress':
            value=control.get('position')
            return None if value is None or value<0 else value
        def number(value,default):
            try:result=float(value)
            except (ValueError,TypeError):return default
            return result if math.isfinite(result) else default
        low=number(control.get('minimum'),0)
        high=number(control.get('maximum'),100 if control.get('type')=='range' else 1)
        value=number(control.get('value'),0)
        return 0 if high<=low else (value-low)/(high-low)
    return control.get(key)


def _native_value(spec,key):
    fields={'type':'input_type','effectiveDisabled':'disabled','selectedIndices':'selected_indices'}
    value=spec.get(fields.get(key,key))
    if key=='value' and spec['tag'] in ('meter','progress'):
        try:return float(value)
        except (ValueError,TypeError):return value
    return value


def native_controls(scene):
    result=[]
    def walk(value):
        if isinstance(value,list):
            for entry in value:walk(entry)
        elif isinstance(value,dict):
            control=value.get('control')
            if isinstance(control,dict) and isinstance(control.get('spec'),dict):
                result.append(control)
                # Caption precedes the body in the native painting order.
                walk(control.get('caption_runs',[]));walk(control.get('content_runs',[]))
            for key,entry in value.items():
                if key!='control':walk(entry)
    walk(scene.get('measured',[]));walk(scene.get('annotations',{}))
    return result


def _inside(a,b):
    return (a and b and a['width']>0 and a['height']>0 and
        a['x']>=b['x']-.6 and a['y']>=b['y']-.6 and
        a['x']+a['width']<=b['x']+b['width']+.6 and
        a['y']+a['height']<=b['y']+b['height']+.6)


def _overlaps(a,b):
    return bool(a and b and min(a['x']+a['width'],b['x']+b['width'])>max(a['x'],b['x']) and
        min(a['y']+a['height'],b['y']+b['height'])>max(a['y'],b['y']))


def _variation(image,box):
    if not box:return False
    if not all(isinstance(box.get(k),(int,float)) and math.isfinite(box[k]) for k in ('x','y','width','height')):return False
    left,top=max(0,math.floor(box['x'])),max(0,math.floor(box['y']))
    right,bottom=min(image.width,math.ceil(box['x']+box['width'])),min(image.height,math.ceil(box['y']+box['height']))
    if right<=left or bottom<=top:return False
    return any(lo!=hi for lo,hi in image.crop((left,top,right,bottom)).getextrema())


def check_control_case(case,official,scene,png):
    errors=[];source=official.get('htmlControls')
    if not isinstance(source,list):return ['missing-original-control-state-evidence']
    expected=case.get('controlExpected')
    if not isinstance(expected,list):return ['missing-source-defined-control-contract']
    if len(expected)!=len(source):errors.append('original-control-denominator-differs')
    for index,item in enumerate(expected):
        if index>=len(source):break
        original=source[index]
        for key,value in item.items():
            if key in ('nativeAbsent','oracleProbe','reason','index'):continue
            if key=='forbiddenAttributes':
                if any(name in original.get('attributes',{}) for name in value):errors.append(f'original-unsafe-attribute:{index}')
                continue
            if key=='options':
                options=original.get('options',[])
                if len(options)!=len(value) or any(any(not _same(option.get(k),v) for k,v in contract.items()) for option,contract in zip(options,value)):
                    errors.append(f'original-contract:{index}:options')
                continue
            actual=original.get('id') if key=='id' else _source_value(original,key)
            if not _same(actual,value):errors.append(f'original-contract:{index}:{key}')
    controls=native_controls(scene);used=set();matched=[]
    for index,original in enumerate(source):
        box=original.get('box',{});style=original.get('style',{})
        absent=style.get('display')=='none' or original.get('type')=='hidden' or box.get('width',0)<=0 or box.get('height',0)<=0
        if index<len(expected) and expected[index].get('nativeAbsent') and not absent:
            errors.append(f'unconfirmed-native-absence:{index}')
        if absent:continue
        identifier=original.get('id','')
        choices=[(i,c) for i,c in enumerate(controls) if i not in used and c['spec']['tag']==original['tag'] and
            (not identifier or dict(c['spec'].get('attributes',[])).get('id')==identifier)]
        if not choices:errors.append(f'missing-native-control:{index}');continue
        number,control=choices[0];used.add(number);spec=control['spec'];matched.append((original,control))
        if index<len(expected) and any(name in dict(spec.get('attributes',[])) for name in expected[index].get('forbiddenAttributes',[])):
            errors.append(f'native-unsafe-attribute:{index}')
        keys=['effectiveDisabled'] if original['tag']=='fieldset' else ['value']
        if original['tag']=='input':keys+=['type','checked','effectiveDisabled','readonly','multiple']
        elif original['tag']=='button':keys+=['effectiveDisabled']
        elif original['tag']=='textarea':keys+=['effectiveDisabled','readonly']
        elif original['tag']=='select':keys+=['effectiveDisabled','multiple','selectedIndices']
        elif original['tag'] in ('meter','progress'):keys+=['fraction']
        for key in keys:
            if not _same(_source_value(original,key),_native_value(spec,key)):
                errors.append(f'native-state:{index}:{key}')
        if original['tag']=='select':
            wanted=[{k:o[k] for k in ('label','value','selected','disabled','group')} for o in original.get('options',[])]
            actual=[{k:o.get(k) for k in ('label','value','selected','disabled','group')} for o in spec.get('options',[])]
            if wanted!=actual:errors.append(f'native-option-state:{index}')
    if len(used)!=len(controls):errors.append('unexpected-native-control-denominator')
    for first,second in case.get('controlDimensionEquivalence',[]):
        original_by={c.get('id'):c for c in source}
        native_by={dict(c['spec'].get('attributes',[])).get('id'):c for c in controls}
        if first not in original_by or second not in original_by or first not in native_by or second not in native_by:
            errors.append('missing-dimension-equivalence-member:'+first+':'+second);continue
        for axis in ('width','height'):
            if not _same(original_by[first]['box'][axis],original_by[second]['box'][axis]):
                errors.append('original-dimension-default-disagrees:'+axis+':'+first)
            if not _same(native_by[first][axis],native_by[second][axis]):
                errors.append('native-dimension-default-disagrees:'+axis+':'+first)
    try:
        image=Image.open(BytesIO(png));image.load();image=image.convert('RGB')
        if image.size!=(scene.get('width'),scene.get('height')):errors.append('encoded-size-differs')
    except Exception:return sorted(set(errors+['invalid-native-image']))
    trace=scene.get('trace',[]);containers=defaultdict(list);identified=defaultdict(list)
    for event in trace:
        if event.get('kind')=='control':
            containers[event.get('resource_id')].append(event)
            if event.get('control_id'):identified[event['control_id']].append(event)
    counts=Counter()
    for index,(original,control) in enumerate(matched):
        spec=control['spec'];key=spec['tag']+':'+spec.get('input_type','')
        identifier=dict(spec.get('attributes',[])).get('id')
        lookup=('id:'+identifier) if identifier and identified.get(identifier) else key
        options=identified[identifier] if lookup.startswith('id:') else containers[key]
        position=counts[lookup];counts[lookup]+=1
        if position>=len(options):errors.append(f'missing-control-paint:{index}');continue
        event=options[position];box=event.get('box')
        style=original.get('style',{})
        if style.get('visibility') in ('hidden','collapse') or original.get('effectiveOpacity',1)==0:continue
        own=lambda e:not identifier or not e.get('control_id') or e['control_id']==identifier
        located=lambda e:(_overlaps(e.get('box'),box) if identifier and e.get('control_id')==identifier else _inside(e.get('box'),box))
        paints=[e for e in trace if own(e) and str(e.get('kind','')).startswith('control-') and e.get('opacity',1)>0 and located(e)]
        if not paints or not _variation(image,box):errors.append(f'unpainted-control:{index}')
        text=[e for e in paints if e.get('kind')=='control-text' and str(e.get('text','')).strip()]
        # Rich button/caption content uses the shared label text path.
        text += [e for e in trace if own(e) and e.get('kind') in ('text','label','node-label','edge-label','group-title','math','math-glyph') and e.get('opacity',1)>0 and str(e.get('text','')).strip() and located(e)]
        if spec['tag']=='select' and original.get('visibleOptionIndices') is not None:
            displayed=re.sub(r'\s+','', ''.join(str(e.get('text','')) for e in text))
            for option_index in original['visibleOptionIndices']:
                label=original['options'][option_index]['label']
                if label and re.sub(r'\s+','',label) not in displayed:errors.append(f'missing-source-visible-option:{index}:{option_index}')
        kind=spec.get('input_type','')
        wants=bool(spec.get('value') or dict(spec.get('attributes',[])).get('placeholder'))
        if spec['tag']=='button':wants=bool(spec.get('text','').strip())
        if spec['tag']=='fieldset':wants=bool(spec.get('legend_text','').strip())
        if spec['tag'] in ('meter','progress') or kind in ('checkbox','radio','range','color','hidden','image'):wants=False
        if kind in ('file','date','month','week','time','datetime-local'):wants=True
        if kind in ('submit','reset'):wants=bool(spec.get('value')) or 'value' not in dict(spec.get('attributes',[]))
        if wants and not text:errors.append(f'missing-control-visible-text:{index}')
        literal_types={'text','search','tel','url','email','number','date','month','week','time','datetime-local'}
        if spec['tag']=='textarea' or spec['tag']=='input' and kind in literal_types:
            wanted=spec.get('value') or dict(spec.get('attributes',[])).get('placeholder','')
            normalized=lambda value:re.sub(r'\s+','',value)
            if wanted and normalized(wanted) not in normalized(''.join(str(e.get('text','')) for e in text)):
                errors.append(f'incorrect-control-visible-text:{index}')
        if spec['tag']=='input' and kind in literal_types|{'password'}:
            # Bind each alleged glyph box to the immutable paint intent and
            # content clip; an existing border is not evidence for value text.
            origin=event.get('points',[{}])[0] if event.get('points') else box or {}
            clip=control.get('clip')
            clip_box=None if clip is None else {'x':origin.get('x',0)+clip[0],'y':origin.get('y',0)+clip[1],'width':clip[2],'height':clip[3]}
            for glyph in text:
                planned=[p for p in control.get('paints',[]) if p.get('kind')=='text' and p.get('text')==glyph.get('text')]
                point=glyph.get('points',[{}])[0] if glyph.get('points') else {}
                bound=any(abs(point.get('x',math.inf)-(origin.get('x',0)+p.get('x',0)))<.6 and abs(point.get('y',math.inf)-(origin.get('y',0)+p.get('y',0)))<.6 for p in planned)
                if not bound or clip_box is not None and not _inside(glyph.get('box'),clip_box):errors.append(f'unbound-control-text-box:{index}')
        if any(not _variation(image,e.get('box')) for e in text):errors.append(f'unpainted-control-text:{index}')
        if kind=='password' and spec.get('value') and any(spec['value'] in str(e.get('text','')) for e in text):
            errors.append(f'unmasked-password:{index}')
        if style.get('appearance')!='none' and kind=='checkbox' and original.get('checked') and not any(e.get('kind')=='control-path' for e in paints):
            errors.append(f'missing-checkbox-mark:{index}')
        if style.get('appearance')!='none' and kind=='radio' and original.get('checked') and sum(e.get('kind')=='control-circle' for e in paints)<2:
            errors.append(f'missing-radio-dot:{index}')
    return sorted(set(errors))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',required=True,type=Path)
    parser.add_argument('--oracle',required=True,type=Path)
    parser.add_argument('--native',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((args.native/'results.json').read_text('utf8'))
    known={row['id']:row for row in manifest['cases']};rows=[]
    for case in load_cases([args.fixtures]):
        if case['expect']!='render':continue
        identifier=case['id'];native=known.get(identifier,{})
        paths=[args.oracle/(identifier+'.json'),args.native/(identifier+'.scene.json'),args.native/(identifier+'.png')]
        if native.get('status')!='CHECKS_PASSED' or not all(p.is_file() for p in paths):errors=['missing-or-failed-render-evidence']
        else:errors=check_control_case(case,json.loads(paths[0].read_text('utf8')),json.loads(paths[1].read_text('utf8')),paths[2].read_bytes())
        rows.append({'id':identifier,'status':'FAIL' if errors else 'PASS','errors':errors})
    result={'schema':'py-mermaid-html-control-verification/v1','source':manifest['source'],'sourceUnchanged':manifest['sourceUnchanged'],
        'backend':manifest['backend'],'cases':rows,'status':'FAIL' if any(r['errors'] for r in rows) or not rows else 'PASS',
        'inputs':{str(p):file_identity(p) for p in (args.fixtures,args.oracle/'manifest.json',args.native/'results.json')},'pixelEqualityRequired':False}
    write(args.out/'verification.json',result)
    print(json.dumps({'status':result['status'],'cases':len(rows),'failed':[r for r in rows if r['errors']]},ensure_ascii=False))
    return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())
