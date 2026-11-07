"""Independent source SVG/actual native-paint checks for Sequence closure.
No product helpers or native allocations at import. Coordinates stay in each
engine's own actor-relative frame; font and participant widths may differ.
"""
from dataclasses import asdict,is_dataclass
from io import BytesIO
import json,math,re
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image

FIXTURES=Path(__file__).with_name('cases-C.json')
def cases():return json.loads(FIXTURES.read_text('utf8'))['cases']
def center(b):return (b['x']+b['width']/2,b['y']+b['height']/2)
def endpoints(path):
 tokens=re.findall(r'[MLHVCmlhvc]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',path)
 pos=[0.,0.];first=None;i=0
 while i<len(tokens):
  cmd=tokens[i];i+=1
  n={'M':2,'L':2,'H':1,'V':1,'C':6}.get(cmd.upper())
  if n is None:raise ValueError('Unsupported message path command '+cmd)
  v=list(map(float,tokens[i:i+n]));i+=n
  if len(v)!=n:raise ValueError('Truncated message path')
  rel=cmd.islower();c=cmd.upper()
  if c=='H':pos[0]=v[0]+(pos[0] if rel else 0)
  elif c=='V':pos[1]=v[0]+(pos[1] if rel else 0)
  else:pos=[v[-2]+(pos[0] if rel else 0),v[-1]+(pos[1] if rel else 0)]
  if first is None:first=tuple(pos)
 return first,tuple(pos)
def native_projection(value):
 if is_dataclass(value):value=asdict(value)
 trace=value['trace'];actors={};messages=[];circles=[];numbers=[];markers=[]
 for e in trace:
  k=e['kind'];b=e.get('box')
  if k=='lifeline':actors[e['semantic_id']]=endpoints(e['path'])[0][0]
  elif k=='message':
   a,z=endpoints(e['path']);messages.append(dict(start=a,end=z,fill=e.get('fill'),dash=e.get('dash',()),id=e['semantic_id'],path=e['path']))
  elif k=='central-connection':circles.append(dict(center=center(b),radius=b['width']/2,fill=e.get('fill')))
  elif k=='sequence-number-box':numbers.append(dict(center=center(b),radius=b['width']/2))
  elif k=='marker':markers.append(dict(kind=e.get('marker'),path=e.get('path'),id=e['semantic_id'],box=b))
 return dict(actors=actors,messages=messages,circles=circles,numbers=numbers,markers=markers,trace=trace,
             activations=[e for e in trace if e['kind'].startswith('activation')],source=False)
def source_projection(svg,computed=None):
 root=ET.fromstring(svg);actors={};messages=[];circles=[];numbers=[];markers=[];activations=[]
 vb=list(map(float,root.attrib.get('viewBox','0 0 1 1').split()))
 def walk(el,defs=False):
  tag=el.tag.rsplit('}',1)[-1];a=el.attrib;defs=defs or tag=='defs';cls=a.get('class','').split()
  if not defs:
   if 'actor-line' in cls:actors[a.get('name',a.get('data-id',''))]=float(a['x1'])
   if a.get('data-et')=='message':
    if tag=='line':p=(float(a['x1']),float(a['y1']));q=(float(a['x2']),float(a['y2']))
    else:p,q=endpoints(a['d'])
    style={k.strip():v.strip() for k,v in (s.split(':',1) for s in a.get('style','').split(';') if ':' in s)}
    start=a.get('marker-start','');end=a.get('marker-end','')
    messages.append(dict(start=p,end=q,fill=style.get('fill',a.get('fill')),dash=style.get('stroke-dasharray',''),markerStart=start,markerEnd=end,path=a.get('d','')))
    for side,ref in [('start',start),('end',end)]:
     if ref:markers.append(dict(side=side,name=ref.split('-')[-1].rstrip(')')))
   if tag=='circle' and float(a.get('r',0))==5:circles.append(dict(center=(float(a['cx']),float(a['cy'])),radius=5))
   if tag=='text' and 'sequenceNumber' in cls:numbers.append(dict(center=(float(a['x']),float(a['y'])-4),text=''.join(el.itertext())))
   if tag=='rect' and any(c.startswith('activation') for c in cls):activations.append(dict(a))
  for child in el:walk(child,defs)
 walk(root)
 # Raw SVG inline declarations are not the final winner under !important.
 # Use independently captured getComputedStyle on the same exact message d.
 if computed is not None:
  shapes=[s for s in computed.get('shapes',[]) if 'messageLine0' in (s.get('classes') or '').split() or 'messageLine1' in (s.get('classes') or '').split()]
  if len(shapes)!=len(messages):raise ValueError('Computed message denominator differs')
  for message,shape in zip(messages,shapes):
   if message['path'] and shape.get('d')!=message['path']:raise ValueError('Computed message path identity differs')
   message['dash']=shape['strokeDasharray'];message['fill']=shape['fill']
 return dict(actors=actors,messages=messages,circles=circles,numbers=numbers,markers=markers,activations=activations,source=True,viewBox=vb)
def dark_fraction(image,x,y,r=2):
 rgb=image.convert('RGB');pts=[(px,py) for py in range(math.floor(y-r),math.ceil(y+r)+1) for px in range(math.floor(x-r),math.ceil(x+r)+1) if (px+.5-x)**2+(py+.5-y)**2<=r*r and 0<=px<rgb.width and 0<=py<rgb.height]
 return sum(max(rgb.getpixel(p))<150 for p in pts)/max(1,len(pts))
def errors(probe,p,image=None):
 e=[];kind=probe['type'];actors=p['actors'];msgs=p['messages'];source=p.get('source',False)
 if kind in ('endpoint','activation'):
  if len(msgs)!=1:return ['message-count']
  for side,who,want in [('start',probe['sender'],probe['startOffset']),('end',probe['receiver'],probe['endOffset'])]:
   if abs(msgs[0][side][0]-actors[who]-want)>.06:e.append(side+'-actor-offset')
 elif kind=='central':
  want=sorted(actors[c['actor']]+c['offset'] for c in probe['circles']);got=sorted(c['center'][0] for c in p['circles'])
  if len(got)!=len(want) or any(abs(a-b)>.06 for a,b in zip(got,want)):e.append('central-actor-anchor')
  if any(abs(c['radius']-5)>.06 for c in p['circles']):e.append('central-radius')
  if image is not None:
   for c in p['circles']:
    x,y=c['center']
    if source:
     vx,vy,vw,vh=p['viewBox'];x=(x-vx)*image.width/vw;y=(y-vy)*image.height/vh
    if dark_fraction(image,x,y)<.8:e.append('central-solid-core')
 elif kind=='number':
  if len(p['numbers'])!=1 or abs(p['numbers'][0]['center'][0]-actors[probe['anchor']])>.06:e.append('number-anchor')
 elif kind=='self':
  if len(msgs)!=1:return ['self-count']
  m=msgs[0];cx=actors[probe['sender']]
  if abs(m['start'][0]-cx-probe['startOffset'])>.06:e.append('self-start')
  if abs(m['end'][0]-cx-1)>.06:e.append('self-end')
  if abs(m['end'][1]-m['start'][1]-(25 if probe['angular'] else 20))>.06:e.append('self-height')
  if m['fill']!='none':e.append('self-fill-none')
  if image is not None:
   x,y=m['start'];x+=20;y+=10
   if source:
    vx,vy,vw,vh=p['viewBox'];x=(x-vx)*image.width/vw;y=(y-vy)*image.height/vh
   if min(image.convert('RGB').getpixel((round(x),round(y))))<250:e.append('self-invented-interior-fill')
 elif kind=='arrows':
  wanted=probe['expected']
  if len(msgs)!=len(wanted):return ['gallery-message-count']
  if source:
   for i,(m,w) in enumerate(zip(msgs,wanted)):
    if any(float(v)>0 for v in re.findall(r'[\d.]+',m['dash']))!=w['dashed']:e.append(f'gallery-{i}-dash')
    for key,side in [('markerStart','start'),('markerEnd','end')]:
     actual=re.search(r'(filled-head|arrowhead|crosshead|solidTopArrowHead|solidBottomArrowHead|stickTopArrowHead|stickBottomArrowHead)\)$',m[key]);actual=actual[1] if actual else ''
     if actual!=w[side]:e.append(f'gallery-{i}-{side}')
  else:
   from collections import Counter
   for i,w in enumerate(wanted):
    if bool(msgs[i]['dash'])!=w['dashed']:e.append(f'gallery-{i}-dash')
    expect=Counter({'arrowhead':'point','crosshead':'cross','filled-head':'open'}.get(s,'half') for s in (w['start'],w['end']) if s)
    actual=Counter(m['kind'] for m in p['markers'] if m['id']==msgs[i]['id'])
    if actual!=expect:e.append(f'gallery-{i}-markers')
 elif kind=='lifecycle':
  if len(p['activations'])!=probe['activationCount']:e.append('activation-count')
  if len(msgs)!=probe['messageCount']:e.append('lifecycle-message-count')
 elif kind=='paint':
  if len(msgs)!=1:return ['message-count']
  if msgs[0]['fill']!=probe['fill']:e.append('inline-fill')
  dash=msgs[0]['dash'];dash=list(map(float,re.findall(r'[\d.]+',dash))) if isinstance(dash,str) else list(dash)
  if dash!=probe['dash']:e.append('important-dash')
 else:raise ValueError('Unknown closure predicate '+kind)
 return sorted(set(e))
