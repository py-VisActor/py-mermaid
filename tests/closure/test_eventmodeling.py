"""Portable source-defined Event measurement and actual nonocclusion regressions."""
import copy,json,math,unittest
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
HERE=Path(__file__).parent
CASES=json.loads((HERE/'cases-event.json').read_text('utf8'))['cases']
ORIGINAL={r['id']:r for r in json.loads((HERE/'event-source-expectations.json').read_text('utf8'))['cases']}
PREFERRED='"trebuchet ms", verdana, arial, sans-serif'

def source_projection(raw,svg):
 from html.parser import HTMLParser
 class Reader(HTMLParser):
  def __init__(self):super().__init__(convert_charrefs=True);self.groups=[];self.cards=[];self.rects=[];self.defs=0
  def active(self):return next((v for v in reversed(self.groups) if v is not None),None)
  def handle_starttag(self,tag,attrs):
   a=dict(attrs)
   if tag=='defs':self.defs+=1
   if tag=='g':
    c={'label':'','index':None} if 'em-box' in (a.get('class') or '').split() else None
    self.groups.append(c)
    if c is not None:self.cards.append(c)
   if tag=='rect' and not self.defs:
    self.rects.append(a);c=self.active()
    if c is not None and c['index'] is None:c['index']=len(self.rects)-1
  def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
  def handle_endtag(self,tag):
   if tag=='g':self.groups.pop()
   if tag=='defs':self.defs-=1
  def handle_data(self,data):
   c=self.active()
   if c is not None:c['label']+=data
 parser=Reader();parser.feed(svg)
 rects=[v for v in raw['shapes'] if v['tag']=='rect']
 if len(rects)!=len(parser.rects):raise ValueError('Source rect denominator differs')
 return {'rectPaintCount':len(rects),'cards':[{'label':v['label'],'box':rects[v['index']]['box']} for v in parser.cards]}

def intersection(a,b):return max(0,min(a['x']+a['width'],b['x']+b['width'])-max(a['x'],b['x']))*max(0,min(a['y']+a['height'],b['y']+b['height'])-max(a['y'],b['y']))
def native_projection(scene,source):
 trace=scene['trace'];shapes=[(i,e) for i,e in enumerate(trace) if e['kind']=='shape' and e.get('box')]
 if len(shapes)!=source['rectPaintCount']:raise ValueError('Actual lane/card paint count differs')
 cards=[]
 for at,e in shapes[-len(source['cards']):]:
  end=next((i for i in range(at+1,len(trace)) if trace[i]['kind']=='shape'),len(trace))
  cards.append({'box':e['box'],'fill':e.get('fill'),'opacity':e.get('opacity',1),'labels':[v for v in trace[at+1:end] if v.get('text') and v['text'].strip() and v.get('box') and v.get('opacity',1)>0]})
 return cards

def relation_errors(source,native,image=None):
 if len(native)!=len(source['cards']):return ['card-denominator']
 errors=[]
 for i,a in enumerate(source['cards']):
  for j,b in enumerate(source['cards'][i+1:],i+1):
   if abs(a['box']['y']-b['box']['y'])<.01 and intersection(a['box'],b['box'])==0 and intersection(native[i]['box'],native[j]['box'])>1:errors.append(f'same-lane-overlap:{i}:{j}')
 for i,card in enumerate(native):
  if not card['labels']:errors.append('missing-card-label:'+str(i))
  for label in card['labels']:
   for j,later in enumerate(native[i+1:],i+1):
    if later['fill'] not in ('none','transparent',None) and later['opacity']>0 and intersection(label['box'],later['box'])>1:errors.append(f'later-card-obscures-earlier-label:{i}:{j}')
   if image is not None:
    b=label['box'];crop=image.convert('RGB').crop((math.floor(b['x']),math.floor(b['y']),math.ceil(b['x']+b['width']),math.ceil(b['y']+b['height'])))
    if sum(max(p)<150 for p in crop.getdata())<2:errors.append('missing-label-ink:'+str(i))
 return sorted(set(errors))

class FakePainter:
 def __init__(self,sans,preferred):self.values={'sans-serif':sans,PREFERRED:preferred};self.calls=[]
 def measure(self,text,**kw):self.calls.append((text,kw));w,h=self.values[kw['family']];return SimpleNamespace(width=w,height=h)
class SourceLiteralMeasurements(unittest.TestCase):
 def test_literal_markup_br_blank_lines_and_js_round(self):
  from py_mermaid.diagrams.business.eventmodeling import _source_text_dimensions
  p=FakePainter((20.4,8.5),(12.4,10.5));text='<b>Place</b><br/><br><code style="text-align: left; display: block;max-width:430px">x</code>'
  self.assertEqual(_source_text_dimensions(p,text),{'width':12,'height':33,'lineHeight':11})
  self.assertEqual([v for v,k in p.calls[:3]],['<b>Place</b>','​','<code style="text-align: left; display: block;max-width:430px">x</code>'])
  for _,k in p.calls:self.assertIs(k['html'],False);self.assertIs(k['literal'],True);self.assertEqual(k['size'],16);self.assertEqual(k['weight'],'700')
 def test_family_selection_all_three_strict_and_nan(self):
  from py_mermaid.diagrams.business.eventmodeling import _source_text_dimensions as f
  self.assertEqual(f(FakePainter((10,20),(10,18)),'x'),{'width':10,'height':18,'lineHeight':18})
  self.assertEqual(f(FakePainter((5.5,7.5),(4.5,6.5)),'x'),{'width':6,'height':8,'lineHeight':8})
  self.assertEqual(f(FakePainter((11,9),(math.nan,8)),'x'),{'width':11,'height':9,'lineHeight':9})
 def test_wrap_equal_boundary_word_space_and_existing_br(self):
  from py_mermaid.diagrams.business import eventmodeling as m
  with patch.object(m,'_source_text_dimensions',side_effect=lambda p,t:{'width':len(t)*10,'height':16,'lineHeight':16}) as measure:
   self.assertEqual(m._source_wrap_label(None,'  aa  b ',30),'aa<br/>b')
   self.assertIn('aa ',[c.args[1] for c in measure.call_args_list]);self.assertIn('',[c.args[1] for c in measure.call_args_list])
  with patch.object(m,'_source_text_dimensions',side_effect=AssertionError('Existing break must not measure')):
   self.assertEqual(m._source_wrap_label(None,' A<br/> B ',30),' A<br/> B ');self.assertEqual(m._source_wrap_label(None,''),'')
 def test_longword_greater_equal_and_last_char_hyphen(self):
  from py_mermaid.diagrams.business import eventmodeling as m
  with patch.object(m,'_source_text_dimensions',side_effect=lambda p,t:{'width':len(t)*10,'height':16,'lineHeight':16}):
   self.assertEqual(m._source_wrap_label(None,'abcdefg',30),'abc-<br/>def-<br/>g');self.assertEqual(m._source_wrap_label(None,'abcdef',30),'abc-<br/>def')
class ActualEventRelations(unittest.IsolatedAsyncioTestCase):
 async def draw(self,c):
  from py_mermaid import arender
  r=await arender(c['source'],config=c.get('config'),backend='cpu');return r,Image.open(BytesIO(r.data)).convert('RGB')
 async def test_three_original_relations_and_actual_glyphs(self):
  for c in CASES:
   with self.subTest(id=c['id']):
    r,im=await self.draw(c);s=ORIGINAL[c['id']];self.assertEqual(relation_errors(s,native_projection(asdict(r),s),im),[])
 async def test_old_html_dimension_fault_reproduces_obscured_card(self):
  from py_mermaid.diagrams.business import eventmodeling as m
  def old(p,text):
   b=p.measure(text,size=16,weight='700',family=PREFERRED,html=True);return {'width':b.width,'height':b.height,'lineHeight':b.height}
  c=next(c for c in CASES if c['id']=='CLOSURE-EVENT-chain-revisit')
  with patch.object(m,'_source_text_dimensions',side_effect=old):r,im=await self.draw(c)
  errs=relation_errors(ORIGINAL[c['id']],native_projection(asdict(r),ORIGINAL[c['id']]),im)
  self.assertTrue(any('overlap' in e or 'obscures' in e for e in errs),'Old HTML width loss was silently accepted')
 async def test_code_style_spaces_reach_literal_measurement(self):
  from py_mermaid.diagrams.business import eventmodeling as m
  seen=[];original=m._source_text_dimensions
  def record(p,text):seen.append(text);return original(p,text)
  with patch.object(m,'_source_text_dimensions',side_effect=record):await self.draw(next(c for c in CASES if c['id']=='CLOSURE-EVENT-data'))
  self.assertTrue(any('<code style="text-align: left; display: block;max-width:430px">' in t for t in seen))
  self.assertFalse(any('<code style="text-align:left;' in t for t in seen))

def raw_data_errors(source,native):
 """Only card containment actually observed in the independent original."""
 errors=[]
 for i,(original,card) in enumerate(zip(source['cards'],native)):
  b=card['box'];caption=original.get('caption')
  if not caption:continue
  caps=[v for v in card['labels'] if v['text'].strip()==caption]
  code=[v for v in card['labels'] if 'monospace' in (v.get('font_family') or '').lower()]
  if len(caps)!=1:errors.append('caption-denominator:'+str(i))
  elif abs(caps[0]['box']['x']+caps[0]['box']['width']/2-(b['x']+b['width']/2))>3:errors.append('caption-not-centered:'+str(i))
  if not code:errors.append('missing-code:'+str(i))
  elif not any(v.get('points') and abs(v['points'][0]['x']-(b['x']+original['codeInset']))<=2 for v in code):errors.append('code-not-left-inset:'+str(i))
  if original.get('sourceTextContained'):
   for v in card['labels']:
    q=v['box']
    if q['x']<b['x']-2 or q['y']<b['y']-2 or q['x']+q['width']>b['x']+b['width']+2 or q['y']+q['height']>b['y']+b['height']+2:errors.append('own-card-label-overflow:'+str(i))
 return sorted(set(errors))

class DirectHTMLAndTransport(unittest.TestCase):
 def test_source_svg_ascii_whitespace_normalization_preserves_nbsp(self):
  from py_mermaid.diagrams.business.eventmodeling import _source_text_dimensions
  p=FakePainter((10,10),(10,10));_source_text_dimensions(p,'  A \t\r\n B  <br/>A\u00a0\u00a0B')
  self.assertEqual([s for s,k in p.calls],['A B','A\u00a0\u00a0B']*2)
 def test_internal_raw_html_is_not_flow_label_preprocessing(self):
  from py_mermaid import parse
  from py_mermaid.rendering.skia.scene import Painter
  p=Painter(parse('eventmodeling\ntf 1 ui Page'),backend='cpu')
  b=p.measure(r'<code>left\nright $$x$$ #amp;</code>',html=True,raw_html=True,width=430)
  text=''.join(r.text for r in b.runs)
  self.assertIn(r'left\nright',text);self.assertIn('$$x$$',text);self.assertIn('#amp;',text)
  self.assertFalse(any(r.kind=='math' for r in b.runs));self.assertGreaterEqual(b.width,430)
  a=p.measure(' A\t B\nC<br/>D\u00a0\u00a0E',html=True,raw_html=True,width=430)
  self.assertEqual(''.join(r.text for r in a.runs),'A B CD\u00a0\u00a0E')
  self.assertEqual(len(set(round(r.baseline,4) for r in a.runs)),2)
 def test_entity_transport_before_source_substring_and_once_html(self):
  from py_mermaid.diagrams.business import eventmodeling as m
  from html import unescape
  encoded=m._source_encode_entities('{#amp;}')
  self.assertEqual(encoded,'{\ufb02\u00b0amp\u00b6\u00df}')
  # JS substring(0,lastIndexOf('}')-1) cuts the placeholder suffix, not raw ';'.
  sliced=encoded[:encoded.rfind('}')-1]
  self.assertEqual(m._source_decode_entities(sliced),'{&amp\u00b6')
  self.assertEqual(unescape(m._source_decode_entities(m._source_encode_entities('&amp; &#65; #amp;'))),'& &A &')

class ActualRawEventRelations(unittest.IsolatedAsyncioTestCase):
 draw=ActualEventRelations.draw
 async def test_public_raw_data_literal_content_and_containment(self):
  for c in CASES:
   if c['id'] not in ('CLOSURE-EVENT-MULTILINE-JSON-AUDIT','CLOSURE-EVENT-LITERAL-DATA-HTML'):continue
   with self.subTest(id=c['id']):
    r,im=await self.draw(c);scene=asdict(r);s=ORIGINAL[c['id']];n=native_projection(scene,s)
    self.assertEqual(relation_errors(s,n,im)+raw_data_errors(s,n),[])
    texts=''.join(t.get('text') or '' for t in scene['trace'])
    if c['id']=='CLOSURE-EVENT-LITERAL-DATA-HTML':
     self.assertIn(r'left\nright',texts);self.assertIn('$$x$$',texts);self.assertIn('&',texts);self.assertNotIn('#amp;',texts)
     self.assertFalse(any(t['kind'].startswith('math-') for t in scene['trace']))
    fault=copy.deepcopy(n);fault[0]['labels'][0]['box']['x']=fault[0]['box']['x']-30
    self.assertTrue(raw_data_errors(s,fault),'Overflow/caption-shift negative control accepted')
 async def test_old_flow_html_consumer_rejected_by_literal_data_contract(self):
  from py_mermaid.rendering.skia.scene import Painter
  original=Painter.measure
  def old(p,text,**kw):kw.pop('raw_html',None);return original(p,text,**kw)
  c=next(c for c in CASES if c['id']=='CLOSURE-EVENT-LITERAL-DATA-HTML')
  with patch.object(Painter,'measure',old):r,im=await self.draw(c)
  scene=asdict(r);texts=''.join(t.get('text') or '' for t in scene['trace']);s=ORIGINAL[c['id']]
  self.assertTrue(r'left\nright' not in texts or '$$x$$' not in texts or raw_data_errors(s,native_projection(scene,s)),'Old flow consumer fault accepted')

if __name__=='__main__':unittest.main()
