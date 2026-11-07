"""Portable source-recorded collapsed container paint, geometry and pixel gates.
No source workspace, tools, browser or images are needed at test runtime.
"""
from io import BytesIO
import copy,json,math,unittest
from pathlib import Path
from PIL import Image,ImageDraw
from .support_collapsed import actual_projection,errors,rgb,separator_pixels,corner_pixels
HERE=Path(__file__).parent
CASES=json.loads((HERE/'cases-shared.json').read_text('utf8'))['cases']
ORIGINAL={r['id']:r for r in json.loads((HERE/'collapsed-source-expectations.json').read_text('utf8'))['cases']}

class CollapsedPaintTests(unittest.IsolatedAsyncioTestCase):
 async def draw(self,case):
  from py_mermaid import arender
  r=await arender(case['source'],config=case['config'],backend='cpu')
  return r,Image.open(BytesIO(r.data)).convert('RGB'),actual_projection(r,case['collapsedProbe']['nodeId'])
 async def test_six_source_recorded_primitive_roles_and_actual_alpha(self):
  for c in CASES:
   with self.subTest(id=c['id']):
    r,im,n=await self.draw(c);a=ORIGINAL[c['id']]
    self.assertEqual(errors(a['expected'],n,im,a['radius']),[])
    self.assertEqual(im.size,(r.width,r.height));self.assertEqual(len(n['dots']),3)
 async def test_actual_separator_has_three_on_three_off_source_gaps(self):
  for c in CASES:
   with self.subTest(id=c['id']):
    _,im,n=await self.draw(c);a=ORIGINAL[c['id']]
    self.assertTrue(separator_pixels(a['expected'],n,im))
 async def test_actual_corner_matches_public_arc_reference_not_square(self):
  for c in CASES:
   if c['config']['look']=='handDrawn':continue
   with self.subTest(id=c['id']):
    _,im,n=await self.draw(c);a=ORIGINAL[c['id']]
    # Fixed theme-base.js:15 background is #f4f4f4. Canvas encodes that
    # explicit background whereas the original transparent SVG has a white
    # browser host. Derive neither reference color nor shape from native pixels.
    background='#f4f4f4' if c['config']['theme']=='base' else 'white'
    self.assertTrue(corner_pixels(a['expected'],n,im,a['radius'],background))
    square=im.copy();b=n['bodyBox'];ImageDraw.Draw(square).rectangle((math.floor(b['x']),math.floor(b['y']),math.floor(b['x'])+a['radius'],math.floor(b['y'])+a['radius']),fill=rgb(a['expected']['body']['fill']) or 'white')
    self.assertFalse(corner_pixels(a['expected'],n,square,a['radius'],background))
 async def test_lost_dots_body_tint_and_full_alpha_faults_rejected_by_pixels(self):
  c=next(c for c in CASES if c['id']=='COLLAPSED-SOURCE-agentflow-palette-neo')
  _,im,n=await self.draw(c);a=ORIGINAL[c['id']];background=rgb(a['expected']['body']['fill']) or 'white'
  for fault in ('lost','body','alpha1'):
   changed=im.copy();draw=ImageDraw.Draw(changed)
   for dot in n['dots']:
    b=dot['box'];color=background if fault in ('lost','body') else rgb(a['expected']['dots'][0]['fill'])
    draw.ellipse((b['x'],b['y'],b['x']+b['width'],b['y']+b['height']),fill=color)
   self.assertIn('dot-visible-alpha-color',errors(a['expected'],n,changed,a['radius']))
 async def test_removed_separator_rejected_even_with_body_and_label_present(self):
  c=next(c for c in CASES if c['id']=='COLLAPSED-SOURCE-agentflow-palette-neo')
  _,im,n=await self.draw(c);a=ORIGINAL[c['id']];self.assertTrue(separator_pixels(a['expected'],n,im))
  changed=im.copy();b=n['separator']['box'];ImageDraw.Draw(changed).rectangle((b['x'],b['y']-2,b['x']+b['width'],b['y']+2),fill=rgb(a['expected']['body']['fill']) or 'white')
  self.assertFalse(separator_pixels(a['expected'],n,changed))
 async def test_stylesheet_important_changes_real_independent_child_paint(self):
  c=copy.deepcopy(next(c for c in CASES if c['id']=='COLLAPSED-SOURCE-agentflow-palette-neo'))
  c['config']['themeCSS']='.collapsed-indicator { fill:rgb(208,32,48)!important; stroke:none!important; stroke-width:0!important; opacity:.25!important; }'
  _,im,n=await self.draw(c);a=copy.deepcopy(ORIGINAL[c['id']])
  for d in a['expected']['dots']:d.update(fill='rgb(208,32,48)',stroke='none',width=0,opacity=.25)
  self.assertEqual(errors(a['expected'],n,im,a['radius']),[])
 async def test_outer_local_fill_does_not_recolor_sibling_indicators(self):
  # FlowDB style applies its fill to the real rect; circles are siblings with
  # their own .collapsed-indicator declaration, not descendants of that rect.
  c=copy.deepcopy(next(c for c in CASES if c['id']=='COLLAPSED-SOURCE-flowchart-palette-neo'))
  # Flowchart's style list splits unescaped commas; use the identical RGB
  # color in a source-legal literal instead of changing the parser contract.
  c['source']+='\nstyle G fill:#c8dcf0\n'
  _,im,n=await self.draw(c);a=copy.deepcopy(ORIGINAL[c['id']]);a['expected']['body']['fill']='rgb(200,220,240)'
  self.assertEqual(errors(a['expected'],n,im,a['radius']),[])
if __name__=='__main__':unittest.main()
