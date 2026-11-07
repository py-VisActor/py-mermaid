"""Locked ZenUML geometry/SVG versus actual native paint parity.

No absolute A/B coordinates, candidate parser/layout helpers or generated
candidate goldens create expectations. Both directions of semantic multisets
are compared. Mutation controls operate on in-memory evidence copies only.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import copy
import hashlib
import html
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from PIL import Image,ImageColor
from bulk_support import load_cases,write

ROOT=Path(__file__).resolve().parents[1]
KIND_LABEL={'alt':'Alt','loop':'Loop','opt':'Opt','par':'Par','critical':'Critical','section':'Section','tcf':'Try','ref':'Ref'}
EMOJI={r['name']:r['unicode'] for r in json.loads((ROOT/'tests/bulk/c/zen-emoji-source.json').read_text('utf-8'))}
CSS_VALUES={'red','italic','oblique','bold','bolder','lighter','underline','overline','line-through'}


def norm(value):
    # Source browser decoding and source StringUtil whitespace normalization.
    return re.sub(r'\s+','',html.unescape(str(value or ''))).replace('\u200b','')


def resolved(text):
    def replace(match):
        names=[]
        for v in match[1].split(','):
            v=v.strip();explicit=re.fullmatch(r':(.+):',v)
            if explicit:names.append(EMOJI.get(explicit[1],explicit[1]))
            elif v not in CSS_VALUES and v in EMOJI:names.append(EMOJI[v])
        return ''.join(names) if names else match[0]
    return re.sub(r'\[([^\]]+)\]',replace,text or '')


def classes(e):return set(e.attrib.get('class','').split())
def tag(e):return e.tag.rsplit('}',1)[-1]
def text_of(e):return ''.join(e.itertext())


def source_projection(document,svg):
    g=document['snapshot']['zenumlCore']['geometry']
    if not isinstance(g,dict):raise ValueError('Missing original geometry')
    participants=g['participants'];occ=g['occurrences']
    def who(x):
        scores=[]
        for p in participants:
            candidates=[p['x']]
            for o in occ:
                if o['participantName']==p['name']:candidates += [o['x'],o['x']+o['width'],o['x']+7,o['x']+8]
            scores.append((min(abs(x-c) for c in candidates),p['name']))
        scores.sort()
        if not scores or scores[0][0]>35:raise ValueError('Unresolved original endpoint '+str(x))
        if len(scores)>1 and abs(scores[0][0]-scores[1][0])<1e-7:raise ValueError('Ambiguous original endpoint '+str(x))
        return scores[0][1]
    calls=[];endpoints=[]
    centers={p['name']:p['x'] for p in participants}
    for m in g['messages']:
        calls.append(('async' if m['arrowStyle']=='open' else 'sync',norm(resolved(m['label'])),m.get('number') or '',who(m['fromX']),who(m['toX']),False,m['arrowStyle']))
        src,dst=who(m['fromX']),who(m['toX']);ltr=m['fromX']<m['toX']
        endpoints.append(('async' if m['arrowStyle']=='open' else 'sync',norm(resolved(m['label'])),m.get('number') or '',src,dst,m['fromX']+(1 if ltr else 0)-centers[src],m['toX']+(0 if ltr else 1)-centers[dst]))
    for m in g['selfCalls']:
        name=who(m['x']);calls.append(('async' if m['arrowStyle']=='open' else 'sync',norm(resolved(m['label'])),m.get('number') or '',name,name,True,m['arrowStyle']))
    for c in g['creations']:
        m=c['message'];calls.append(('creation',norm(m['label']),m.get('number') or '',who(m['fromX']),who(m['toX']),False,'open'))
        src,dst=who(m['fromX']),who(m['toX']);ltr=m['fromX']<m['toX']
        endpoints.append(('creation',norm(m['label']),m.get('number') or '',src,dst,m['fromX']+(1 if ltr else 0)-centers[src],'left-edge' if ltr else 'right-edge'))
    for r in g['returns']:
        calls.append(('return',norm(resolved(r['label'])),'' if r['isSelf'] else r.get('number') or '',who(r['fromX']),who(r['toX']),r['isSelf'],'none' if r['isSelf'] else 'open'))
        if not r['isSelf']:
            src,dst=who(r['fromX']),who(r['toX']);endpoints.append(('return',norm(resolved(r['label'])),r.get('number') or '',src,dst,r['fromX']-centers[src],r['toX']-centers[dst]))
    fragments=[(f['kind'],norm(resolved(f['label'])),f.get('number') or '',tuple(norm(resolved(s['label'])) for s in f['sections'][1:]),len(f['sections'][1:])) for f in g['fragments']]
    tree=ET.fromstring(svg)
    drawn_participants=[];participant_content=[];comments=[];dividers=[];source_numbers=[]
    for e in tree.iter():
        cls=classes(e)
        if tag(e)=='g' and 'participant' in cls:
            name=e.attrib.get('data-participant','');drawn_participants.append(name)
            def texts(cls):return norm(''.join(text_of(v) for v in e.iter() if tag(v)=='text' and cls in classes(v)))
            participant_content.append((name,texts('participant-label'),texts('participant-emoji'),texts('stereotype-label'),sum(tag(v)=='g' and 'participant-icon' in classes(v) for v in e.iter())))
        if tag(e)=='text' and 'comment-text' in cls:comments.append(norm(text_of(e)))
        if tag(e)=='g' and 'divider' in cls:dividers.append(norm(''.join(text_of(v) for v in e.iter() if tag(v)=='text')))
        if tag(e)=='text' and 'seq-number' in cls:source_numbers.append(norm(text_of(e)))
    # Crosscheck the reference geometry against what the original actually paints.
    expected_calls=len(g['messages'])+len(g['selfCalls'])
    actual_calls=sum(tag(e)=='g' and 'message' in classes(e) for e in tree.iter())
    if actual_calls!=expected_calls:raise ValueError('Original geometry/SVG call count mismatch')
    if Counter(drawn_participants)!=Counter(p['name'] for p in participants):raise ValueError('Original participant geometry/SVG mismatch')
    return {'calls':calls,'endpoints':endpoints,'fragments':fragments,'participants':drawn_participants,'participantContent':participant_content,'groupMembers':[(v.get('name',''),tuple(p['name'] for p in sorted(participants,key=lambda p:p['x']) if v['x']<=p['x']<=v['x']+v['width'])) for v in g['groups']],'fragmentMembers':[(f['kind'],f.get('number') or '',tuple(p['name'] for p in sorted(participants,key=lambda p:p['x']) if f['x']<=p['x']<=f['x']+f['width'])) for f in g['fragments']],'participantOrder':[p['name'] for p in sorted(participants,key=lambda p:p['x'])],'comments':comments,'dividers':dividers,'groups':[v['name'] if 'name' in v else v.get('title','') for v in g['groups']],'numbers':source_numbers}


def plain(value):
    if isinstance(value,dict):
        if set(value)=={'entries'}:return {k:plain(v) for k,v in value['entries']}
        return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    return value


def native_projection(scene):
    scene=plain(scene)
    ir=scene['layout'].get('paint_ir')
    if ir is None:raise ValueError('Missing native actual-paint binding IR')
    events=defaultdict(list)
    for e in scene['trace']:
        if e.get('opacity',1)>0:events[e['semantic_id']].append(e)
    calls=[];fragments=[];errors=[];numbers=[];endpoints=[]
    participant_bounds={}
    for event in scene['trace']:
        if event['kind']=='participant-box':
            nums=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',event.get('path') or '')))
            if len(nums)>=4:
                xx=nums[::2];participant_bounds[event['semantic_id']]=(min(xx)-1,max(xx)+1)
    centers={id:(x1+x2)/2 for id,(x1,x2) in participant_bounds.items()}
    for record in ir:
        id=record['semantic_id'];paint=events[id];kind=record['kind']
        def labels(role):return ''.join(e['text'] or '' for e in paint if e['kind']==role)
        num=norm(labels('seq-number'));numbers.extend(e['text'] for e in paint if e['kind']=='seq-number')
        if kind!='divider' and num!=norm(record.get('number')):errors.append('metadata-without-number-paint:'+id)
        if kind in ('sync','async','creation','return'):
            role='return-label' if kind=='return' else 'message-label';label=norm(labels(role))
            if label!=norm(resolved(record['label'])):errors.append('metadata-without-label-paint:'+id)
            line_role='return-icon' if kind=='return' and record['is_self'] else 'return-line' if kind=='return' else 'creation-line' if kind=='creation' else 'message-line'
            line=[e for e in paint if e['kind']==line_role and e.get('path')]
            if not line:errors.append('missing-actual-line:'+id)
            markers=[e for e in paint if e.get('marker')]
            marker='none' if not markers else 'open' if all(e['marker']=='open' for e in markers) else 'solid' if all(e['marker']=='point' for e in markers) else 'invalid'
            expected='none' if kind=='return' and record['is_self'] else 'open' if kind in ('async','creation','return') else 'solid'
            if markers and any(e.get('stroke_width')!=2 for e in markers):errors.append('marker-stroke-width:'+id)
            if record['is_self'] and line and markers:
                values=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',line[0]['path'])))
                for me in markers:
                    mv=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',me.get('path') or '')))
                    if not mv or abs(min(mv[::2])-values[-2])>1.1:errors.append('self-marker-disconnected:'+id)
            if marker!=expected:errors.append('marker-paint:'+id+':'+marker+'!='+expected)
            if kind=='creation' or kind=='return' and not record['is_self']:
                if not line or any(tuple(e.get('dash',()))!=(6.,4.) for e in line):errors.append('missing-dashed-line:'+id)
            if not record['is_self'] and line:
                nums=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',line[0]['path'])))
                if len(nums)!=4:errors.append('nonstraight-native-call:'+id)
                else:
                    src,dst=record['source'],record['target'];start,endx=nums[0],nums[2]
                    if kind=='creation':
                        edge=participant_bounds[dst][0 if endx>start else 1]
                        if abs(endx-edge)>1:errors.append('creation-tip-not-at-frame:'+id)
                        target='left-edge' if endx>start else 'right-edge'
                    else:target=endx-centers[dst]
                    endpoints.append((kind,label,num,src,dst,start-centers[src],target))
                    for marker_event in markers:
                        values=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',marker_event.get('path') or '')))
                        if len(values)<4:errors.append('empty-marker-path:'+id);continue
                        tip=(max if endx>start else min)(values[::2])
                        if abs(tip-endx)>1.1:errors.append('marker-disconnected-from-line:'+id)
            calls.append((kind,label,num,record['source'],record['target'],record['is_self'],marker))
            if record['is_self'] and kind!='return':
                lbl=[e for e in paint if e['kind']==role and e.get('box')];seq=[e for e in paint if e['kind']=='seq-number' and e.get('box')]
                if lbl and seq and max(e['box']['x']+e['box']['width'] for e in seq)>min(e['box']['x'] for e in lbl)-1:errors.append('number-overlaps-self-label:'+id)
        elif kind=='fragment':
            condition=labels('fragment-condition')
            if norm(condition)!=norm('['+resolved(record['label'])+']' if record['label'] else ''):errors.append('missing-fragment-condition-paint:'+id)
            visible=labels('fragment-label')
            if norm(visible)!=KIND_LABEL.get(record['fragment_kind'],record['fragment_kind']):errors.append('fragment-visible-kind:'+id)
            sections=[]
            for j in range(1,len(record['sections'])+1):
                section_events=events[id+'-section-'+str(j)]
                sections.append(norm(''.join(e.get('text') or '' for e in section_events if e['kind']=='fragment-section-label')))
            actual_separators=sum(e['kind']=='fragment-separator' for e in paint)
            if actual_separators!=len(record['sections']):errors.append('fragment-separators:'+id)
            fragments.append((record['fragment_kind'],norm(resolved(record['label'])),num,tuple(sections),actual_separators))
        elif kind!='divider':raise ValueError('Unknown native IR kind '+kind)
    participants=[e['semantic_id'] for e in scene['trace'] if e['kind']=='participant-box' and e.get('opacity',1)>0]
    comments=[norm(''.join(e.get('text') or '' for e in paint if e['kind']=='comment-text')) for paint in events.values() if any(e['kind']=='comment-text' for e in paint)]
    dividers=[norm(''.join(e.get('text') or '' for e in paint if e['kind']=='divider-label')) for paint in events.values() if any(e['kind']=='divider-label' for e in paint)]
    participant_content=[]
    for name in participants:
        paint=events[name]
        def txt(role):return norm(''.join(e.get('text') or '' for e in paint if e['kind']==role))
        participant_content.append((name,txt('participant-label'),txt('participant-emoji'),txt('stereotype-label'),sum(e['kind']=='asset' for e in paint)))
    group_members=[];fragment_members=[]
    for id,paint in events.items():
        outlines=[e for e in paint if e['kind'] in ('group-outline','fragment-border') and e.get('path')]
        for outline in outlines:
            values=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',outline['path'])));left=min(values[::2]);right=max(values[::2])
            members=tuple(n for n in sorted(centers,key=centers.get) if left<=centers[n]<=right)
            if outline['kind']=='group-outline':group_members.append((id,members))
            else:
                binding=next(r for r in ir if r['semantic_id']==id);fragment_members.append((binding['fragment_kind'],binding['number'],members))
    groups=[group[0] for group in scene['layout']['groups']]
    return dict(calls=calls,endpoints=endpoints,fragments=fragments,participants=participants,participantContent=participant_content,groupMembers=group_members,fragmentMembers=fragment_members,participantOrder=sorted(centers,key=centers.get),comments=comments,dividers=dividers,groups=groups,numbers=numbers),errors


def multiset_difference(a,b):
    left=Counter(map(repr,a));right=Counter(map(repr,b))
    return {'missing':list((left-right).elements()),'extra':list((right-left).elements())}


def check(case,official,svg,scene,png):
    reference=source_projection(official,svg);actual,errors=native_projection(scene)
    if case.get('officialExpect')=='content_loss':
        # Exactly the two reviewed fixed-source recovery cases, no broad skip.
        contracts={
          'C-zenuml-source-emoji-colon-override':(['notify()'],[],[],['_STARTER_']),
          'C-zenuml-source-emoji-in-conditions':(['wait()','deny()'],['proceed()','limited'],['proceed()','limited'],['_STARTER_','A'])}
        if case['id'] not in contracts:raise ValueError('Unreviewed content-loss exception')
        missing,present,source_labels,source_participants=contracts[case['id']]
        declared=case['sourceContent']
        if declared!={'missingText':missing,'presentText':present}:raise ValueError('Content-loss contract drift')
        if sorted(v[1] for v in reference['calls'])!=sorted(map(norm,source_labels)) or reference['participants']!=source_participants:errors.append('source-content-loss-transcript-drift')
        intended={
          'C-zenuml-source-emoji-colon-override':(['Alert','Normal'],[('sync','notify()','1','Alert','Normal',False,'solid')],0),
          'C-zenuml-source-emoji-in-conditions':(['_STARTER_','A'],[('sync','proceed()','1.1','_STARTER_','A',False,'solid'),('sync','wait()','1.2','_STARTER_','A',False,'solid'),('sync','deny()','1.3','_STARTER_','A',False,'solid')],1)}
        intended_participants,intended_calls,intended_fragments=intended[case['id']]
        if Counter(actual['participants'])!=Counter(intended_participants) or actual['participantOrder']!=intended_participants:errors.append('native-content-loss-participant-contract')
        # Both reviewed author-intent examples contain independent bare LTR sync
        # calls: +1 lifeline stroke on sender, -7px target occurrence wall.
        for endpoint in actual['endpoints']:
            if abs(endpoint[5]-1)>.01 or abs(endpoint[6]+7)>.01:errors.append('native-content-loss-wall-contract')
        if Counter(actual['calls'])!=Counter(intended_calls) or len(actual['fragments'])!=intended_fragments:errors.append('native-content-loss-call-contract')
        intended_sections=[] if case['id'].endswith('colon-override') else [
            ('alt',norm('\u2705 authorized'),'1',
             (norm('[\u26a0\ufe0f rate limited]'),norm('[else]')),2)]
        if Counter(actual['fragments'])!=Counter(intended_sections):errors.append('native-content-loss-section-contract')
        text=''.join(v[1] for v in actual['calls'])
        for v in case['expectedText']:
            if norm(v) not in text:errors.append('native-enhancement-content-missing:'+v)
    else:
        for field in ('calls','fragments','participants','participantContent','groupMembers','fragmentMembers','comments','dividers','groups','numbers'):
            diff=multiset_difference(reference[field],actual[field])
            if diff['missing'] or diff['extra']:errors.append({'field':field,**diff})
    if case.get('officialExpect')!='content_loss':
        if reference['participantOrder']!=actual['participantOrder']:errors.append('participant-left-right-order')
        def key(row):return tuple(row[:5])
        observed={key(row):row for row in actual['endpoints']}
        for row in reference['endpoints']:
            b=observed.get(key(row))
            if b is None:errors.append('missing-endpoint-contract:'+repr(key(row)));continue
            for av,bv in zip(row[5:],b[5:]):
                if isinstance(av,(int,float)) and isinstance(bv,(int,float)):
                    if abs(av-bv)>1.01:errors.append('endpoint-wall-offset:'+repr((key(row),av,bv)))
                elif av!=bv:errors.append('endpoint-side:'+repr((key(row),av,bv)))
    image=(png.copy() if isinstance(png,Image.Image) else Image.open(png)).convert('RGB');ink_checks=0
    if all(channel==(255,255) for channel in image.getextrema()):errors.append('white-noop-png')
    for e in scene['trace']:
        if not e.get('text') or not e.get('box') or e.get('opacity',1)<=0:continue
        b=e['box'];x1=max(0,math.floor(b['x']));y1=max(0,math.floor(b['y']));x2=min(image.width,math.ceil(b['x']+b['width']));y2=min(image.height,math.ceil(b['y']+b['height']))
        if x2<=x1 or y2<=y1:continue
        crop=image.crop((x1,y1,x2,y2));ink_checks+=1
        if all(lo==hi for lo,hi in crop.getextrema()):errors.append('missing-png-text-ink:'+e['semantic_id'])
    for e in scene['trace']:
        if e.get('opacity',1)<=0:continue
        if e['kind']=='asset':
            b=e['box'];roi=(math.floor(b['x']),math.floor(b['y']),math.ceil(b['x']+b['width']),math.ceil(b['y']+b['height']))
        elif e.get('marker'):
            values=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',e.get('path') or '')))
            if not values:continue
            roi=(math.floor(min(values[::2]))-1,math.floor(min(values[1::2]))-1,math.ceil(max(values[::2]))+1,math.ceil(max(values[1::2]))+1)
        else:continue
        crop=image.crop(roi)
        if crop.width and crop.height and all(lo==hi for lo,hi in crop.getextrema()):errors.append('missing-asset-marker-pixels:'+e['semantic_id'])
    if not ink_checks and actual['calls']:errors.append('no-text-pixel-checks')
    for e in scene['trace']:
        if e['kind'] not in ('message-line','creation-line','return-line') or e.get('opacity',1)<=0:continue
        coords=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',e.get('path') or '')))
        if len(coords)!=4 or abs(coords[1]-coords[3])>.01:continue
        x1,x2=sorted((coords[0],coords[2]));y=coords[1]
        if x2-x1<30:continue
        samples=[]
        for x in range(max(0,math.ceil(x1)+8),min(image.width,math.floor(x2)-8)):
            samples.append(any(sum(image.getpixel((x,yy)))<500 for yy in range(max(0,math.floor(y)-1),min(image.height,math.ceil(y)+2))))
        if samples and sum(samples)/len(samples)<.2:errors.append('missing-png-line-ink:'+e['semantic_id'])
    return errors,reference,actual


def mutations(case,official,svg,scene,png,artifact_dir=None):
    base_errors,_,_=check(case,official,svg,scene,png)
    if base_errors:return {'status':'BLOCKED_BY_POSITIVE'}
    rows={}
    if artifact_dir:artifact_dir.mkdir(parents=True,exist_ok=False)
    def probe(name,mutator):
        value=copy.deepcopy(scene);mutator(value)
        rows[name]=bool(check(case,official,svg,value,png)[0])
        if artifact_dir:write(artifact_dir/(name+'.json'),{'rejected':rows[name],'mutation':name,'nativeEvidence':value})
    if any(e['kind']=='seq-number' for e in scene['trace']):probe('wrong-number',lambda s:next(e for e in s['trace'] if e['kind']=='seq-number').update(text='999.999'))
    if any(e.get('marker') for e in scene['trace']):probe('wrong-arrow',lambda s:next(e for e in s['trace'] if e.get('marker')).update(marker='invalid'))
    if any(e['kind'] in ('message-line','creation-line','return-line') for e in scene['trace']):probe('missing-line',lambda s:s.update(trace=[e for e in s['trace'] if e['kind'] not in ('message-line','creation-line','return-line')]))
    if any(e['kind']=='fragment-condition' for e in scene['trace']):probe('missing-fragment-condition',lambda s:s.update(trace=[e for e in s['trace'] if e['kind']!='fragment-condition']))
    if any(e['kind']=='fragment-section-label' for e in scene['trace']):probe('missing-section-label',lambda s:s.update(trace=[e for e in s['trace'] if e['kind']!='fragment-section-label']))
    bindings=plain(scene)['layout']['paint_ir']
    self_call=next((v for v in bindings if v.get('is_self') and v['kind'] in ('sync','async')),None)
    if self_call:
        def overlap_number(s):
            number=next(e for e in s['trace'] if e['semantic_id']==self_call['semantic_id'] and e['kind']=='seq-number')
            label=next(e for e in s['trace'] if e['semantic_id']==self_call['semantic_id'] and e['kind']=='message-label')
            number['box']['x']=label['box']['x']
        probe('number-overlaps-glyph',overlap_number)
    if any(e['kind']=='fragment-separator' for e in scene['trace']):probe('missing-separator',lambda s:s.update(trace=[e for e in s['trace'] if e['kind']!='fragment-separator']))
    line=next((e for e in scene['trace'] if e['kind'] in ('message-line','creation-line','return-line') and len(re.findall(r'[-+]?(?:\d*\.\d+|\d+)',e.get('path') or ''))==4),None)
    if line:
        def wrong_wall(s):
            e=next(e for e in s['trace'] if e['semantic_id']==line['semantic_id'] and e['kind']==line['kind']);e['path']=re.sub(r'(?<=M)[-+]?(?:\d*\.\d+|\d+)',lambda m:str(float(m[0])+7),e['path'],count=1)
        probe('wrong-occurrence-wall',wrong_wall)
    if any(e['kind']=='creation-line' for e in scene['trace']):probe('solid-creation',lambda s:next(e for e in s['trace'] if e['kind']=='creation-line').update(dash=[]))
    if any(e['kind']=='message-label' and e.get('text') for e in scene['trace']):probe('missing-glyph-event',lambda s:s['trace'].remove(next(e for e in s['trace'] if e['kind']=='message-label' and e.get('text'))))
    if any(e.get('marker') for e in scene['trace']):probe('disconnected-marker',lambda s:next(e for e in s['trace'] if e.get('marker')).update(path='M100000 0L100010 5L100000 10Z'))
    if any(e['kind']=='participant-box' for e in scene['trace']):probe('extra-footer',lambda s:s['trace'].append(copy.deepcopy(next(e for e in s['trace'] if e['kind']=='participant-box'))))
    image=(png.copy() if isinstance(png,Image.Image) else Image.open(png)).convert('RGB')
    white=Image.new('RGB',image.size,'white')
    if artifact_dir:white.save(artifact_dir/'white-png.png')
    rows['white-png']=bool(check(case,official,svg,scene,white)[0])
    text_event=next((e for e in scene['trace'] if e.get('text') and e.get('box') and e['kind']=='message-label'),None)
    if text_event:
        erased=image.copy();b=text_event['box'];erased.paste('white',(max(0,math.floor(b['x'])),max(0,math.floor(b['y'])),min(image.width,math.ceil(b['x']+b['width'])),min(image.height,math.ceil(b['y']+b['height']))));rows['erased-glyph-png']=bool(check(case,official,svg,scene,erased)[0])
    marker=next((e for e in scene['trace'] if e.get('marker') and e.get('path')),None)
    if marker:
        values=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',marker['path'])))
        erased_marker=image.copy();erased_marker.paste('white',(max(0,math.floor(min(values[::2]))-1),max(0,math.floor(min(values[1::2]))-1),min(image.width,math.ceil(max(values[::2]))+1),min(image.height,math.ceil(max(values[1::2]))+1)))
        rows['erased-arrow-png']=bool(check(case,official,svg,scene,erased_marker)[0])
        if artifact_dir:erased_marker.save(artifact_dir/'erased-arrow-png.png')
    if artifact_dir:
        if text_event:erased.save(artifact_dir/'erased-glyph-png.png')
        write(artifact_dir/'results.json',rows)
    return rows


def select_zenuml_cases(cases):
    """All static Zen positives, with exact preservation of the locked148.

    Origin identifies the base corpus, never eligibility for the strict check.
    New/regression inputs from any source path receive identical checks.
    """
    base_path=ROOT/'tests/bulk/c/zen-visual-source-cases.json'
    raw=base_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!='0b7b430524b8aacd48a0982e4dd9fc8401b9a397308b3f73b24ade70516bdeb1':
        raise ValueError('Locked148 visual identity reference changed')
    expected={row['id'] for row in json.loads(raw)}
    if len(expected)!=148:raise ValueError('Locked visual identity set must contain148IDs')
    selected=[c for c in cases if c['kind']=='zenuml' and c['expect'] in ('render','upstream_defect')]
    ids=[c['id'] for c in selected]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate Zen positive ID')
    base={c['id'] for c in selected if c['origin']['path']=='e2e/data/compare-cases.js'}
    if base!=expected:
        raise ValueError('Locked148 visual IDs missing/substituted: '+repr({'missing':sorted(expected-base),'extra':sorted(base-expected)}))
    if not expected.issubset(ids):raise ValueError('Locked148 visual input missing')
    return selected,dict(baseVisualDenominator=148,additionalDenominator=len(selected)-148,totalDenominator=len(selected))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fixtures',required=True,type=Path);parser.add_argument('--oracle',required=True,type=Path);parser.add_argument('--native',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    cases,denominators=select_zenuml_cases(load_cases([args.fixtures]))
    rows=[]
    for case in cases:
        id=case['id'];row={'id':id,'status':'TOOL_ERROR'}
        try:
            a=args.oracle/(id+'.json');svg=args.oracle/(id+'.svg');b=args.native/(id+'.scene.json');png=args.native/(id+'.png')
            original=json.loads(a.read_text('utf-8'));scene=json.loads(b.read_text('utf-8'));text=svg.read_text('utf-8')
            errors,reference,actual=check(case,original,text,scene,png)
            controls=mutations(case,original,text,scene,png,args.out/(id+'.controls'))
            if not errors and not all(controls.values()):errors.append('mutation-control-survived')
            row.update(status='FAIL' if errors else 'PASS',errors=errors,controls=controls,sourceProjection=reference,nativeProjection=actual,evidence={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a,svg,b,png)})
        except Exception as exc:row.update(error=type(exc).__name__+': '+str(exc))
        rows.append(row);write(args.out/(id+'.parity.json'),row)
    counts=Counter(r['status'] for r in rows);write(args.out/'report.json',{'schema':'py-mermaid-zenuml-parity/v1','counts':counts,'cases':rows,'denominator':len(cases),**denominators,'coordinatePolicy':'relative relationships only; no A/B exact pixel placement requirement'})
    print(json.dumps(dict(counts)));return int(counts['FAIL']>0 or counts['TOOL_ERROR']>0)

if __name__=='__main__':raise SystemExit(main())
