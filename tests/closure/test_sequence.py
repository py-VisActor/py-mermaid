"""Portable fixed-source Sequence closure contracts (no oracle at discovery).
Numerical literals below derive from sequenceRenderer.ts / svgDraw.js, never
from the production message_geometry helper. Actual public API PNG checks are
paired with destructive in-memory controls; original evidence is unmodified.
"""
from dataclasses import asdict
from io import BytesIO
import copy,math,unittest
from PIL import Image
from .support_C import cases,native_projection,errors,dark_fraction


def render(case):
 from py_mermaid import render
 return render(case['source'],backend='cpu',config=case.get('config'))
def png(result):return Image.open(BytesIO(result.data)).convert('RGB')

class SourceGeometry(unittest.TestCase):
 def test_activation_union_literal_depths(self):
  from py_mermaid.diagrams.sequence.message_geometry import activation_bounds
  for level,expected in [(0,(99,101)),(1,(95,105)),(2,(95,110)),(3,(95,115))]:
   with self.subTest(depth=level):self.assertEqual(activation_bounds(100,level,10),expected)
 def test_filled_plain_endpoints_both_directions(self):
  from py_mermaid.diagrams.sequence.message_geometry import message_geometry
  for a,b,expected in [(100,300,(101,296)),(300,100,(299,104))]:
   g=message_geometry('->>','',a,b,0,0,10,y=80)
   self.assertEqual((g.startx,g.stopx),expected)
 def test_inline_activation_first_excludes_full_half_bar(self):
  from py_mermaid.diagrams.sequence.message_geometry import message_geometry
  g=message_geometry('->>','',100,300,0,0,10,y=80,activate=True)
  self.assertEqual((g.startx,g.stopx),(101,292))
 def test_number_normal_and_reverse_literal_actor_anchors(self):
  from py_mermaid.diagrams.sequence.message_geometry import message_geometry
  for arrow,a,b,anchor in [('->>',100,300,100),('->>',300,100,300),('/|-',100,300,300),('/|-',300,100,100),('<<->>',300,100,300)]:
   with self.subTest(arrow=arrow,a=a):self.assertEqual(message_geometry(arrow,'',a,b,0,0,10,y=80,numbered=True).number_x,anchor)
 def test_central_plain_does_not_use_shortened_shaft_anchor(self):
  from py_mermaid.diagrams.sequence.message_geometry import message_geometry
  g=message_geometry('->>','dual',100,300,0,0,10,y=80)
  self.assertEqual(g.central_circles,(100,300));self.assertEqual((g.startx,g.stopx),(105,296))
 def test_source_numbered_central_circle_adjusts_only_source(self):
  from py_mermaid.diagrams.sequence.message_geometry import message_geometry
  g=message_geometry('->>','dual',100,300,0,0,10,y=80,numbered=True)
  self.assertEqual(g.central_circles,(116.5,300))
 def test_reverse_numbered_central_circle_adjusts_only_target(self):
  from py_mermaid.diagrams.sequence.message_geometry import message_geometry
  g=message_geometry('/|-','dual',300,100,0,0,10,y=80,numbered=True)
  self.assertEqual(g.central_circles,(300,116.5))
 def test_self_curve_and_rightangle_source_end_baselines(self):
  from py_mermaid.diagrams.sequence.message_geometry import message_geometry
  for angular,endpoint in [(False,(101,100)),(True,(101,105))]:
   g=message_geometry('//-','',100,100,0,0,10,y=80,self_reference=True,numbered=True,right_angles=angular)
   self.assertEqual(g.painted_start,(111,80));self.assertEqual(g.painted_end,endpoint)
 def test_half_markers_reverse_orientation_names_literal(self):
  from py_mermaid.diagrams.sequence.message_geometry import message_geometry
  for arrow,side,wanted in [('-|\\','end','solidTopArrowHead'),('-|/','end','solidBottomArrowHead'),('/|-','start','solidBottomArrowHead'),('\\|-','start','solidTopArrowHead'),('//-','start','stickBottomArrowHead')]:
   g=message_geometry(arrow,'',100,300,0,0,10,y=80)
   self.assertEqual(getattr(g,side+'_marker'),wanted)

class ActualSequencePNG(unittest.TestCase):
 def check_cases(self,types):
  selected=[c for c in cases() if c['closureProbe']['type'] in types]
  self.assertTrue(selected)
  for case in selected:
   with self.subTest(case=case['id']):
    result=render(case);im=png(result);p=native_projection(result)
    self.assertEqual(errors(case['closureProbe'],p,im),[])
    self.assertEqual(im.size,(result.width,result.height))
    self.assertGreater(sum(max(px)-min(px)>20 or min(px)<180 for px in im.getdata()),30)
    for ev in result.trace:
     if ev.box:self.assertTrue(all(math.isfinite(v) for v in (ev.box.x,ev.box.y,ev.box.width,ev.box.height)))
 def test_actual_central_solid_cores_actor_relative_both_sides(self):self.check_cases({'central'})
 def test_actual_number_forward_reverse_bidir_actor_ownership(self):self.check_cases({'number'})
 def test_actual_self_open_curves_dashed_rightangle_and_handdrawn(self):self.check_cases({'self'})
 def test_actual_all_26_marker_paints_one_logical_cross(self):self.check_cases({'arrows'})
 def test_actual_activation_boundaries_and_inline_nested_lifetimes(self):self.check_cases({'activation','lifecycle'})
 def test_actual_plain_and_neo_endpoints(self):self.check_cases({'endpoint'})
 def test_important_dash_overrides_source_inline_not_fill(self):self.check_cases({'paint'})
 def test_circle_core_negative_white_noop_and_hollow_ring_rejected(self):
  case=next(c for c in cases() if c['id']=='CLOSURE-C-central-dual-plain')
  result=render(case);p=native_projection(result);im=png(result)
  self.assertEqual(errors(case['closureProbe'],p,im),[])
  white=Image.new('RGB',im.size,'white')
  self.assertIn('central-solid-core',errors(case['closureProbe'],p,white))
  hollow=im.copy()
  from PIL import ImageDraw
  draw=ImageDraw.Draw(hollow)
  for c in p['circles']:
   x,y=c['center'];draw.ellipse((x-3,y-3,x+3,y+3),fill='white')
  self.assertIn('central-solid-core',errors(case['closureProbe'],p,hollow))
 def test_self_interior_rejects_invented_filled_wedge(self):
  case=next(c for c in cases() if c['id']=='CLOSURE-C-self-curved-normal')
  result=render(case);p=native_projection(result);im=png(result);m=p['messages'][0]
  # Source cubic M(x,y) C(x+60,y-10)(x+60,y+30)(x,y+20):
  # (x+20,y+10) is strictly inside its closed area but away from stroke.
  x,y=m['start'];self.assertGreater(min(im.getpixel((round(x+20),round(y+10)))),220)
  changed=copy.deepcopy(p);changed['messages'][0]['fill']='#ECECFF'
  self.assertIn('self-fill-none',errors(case['closureProbe'],changed,im))
  from PIL import ImageDraw
  wedge=im.copy();ImageDraw.Draw(wedge).rectangle((round(x+17),round(y+7),round(x+23),round(y+13)),fill='#ECECFF')
  self.assertIn('self-invented-interior-fill',errors(case['closureProbe'],p,wedge))
 def test_number_text_has_real_white_glyph_not_only_dark_circle(self):
  result=render(next(c for c in cases() if c['id']=='CLOSURE-C-number-reverse-ltr'));im=png(result)
  event=next(e for e in result.trace if e.kind=='sequence-number');b=event.box
  crop=im.crop((math.floor(b.x),math.floor(b.y),math.ceil(b.x+b.width),math.ceil(b.y+b.height)))
  self.assertGreater(sum(min(px)>220 for px in crop.getdata()),1)
  self.assertGreater(sum(max(px)<150 for px in crop.getdata()),1)

class PainterMarkerPath(unittest.TestCase):
 def test_real_transformed_triangle_bounds_semantics_and_pixels(self):
  from py_mermaid.model.scene import Diagram
  from py_mermaid.model.flowchart import SourceDocument
  from py_mermaid.rendering.skia.scene import Painter
  p=Painter(Diagram('info',SourceDocument('info'),(),None),backend='cpu')
  p.marker_path('M0 0L12 6L0 12Z',kind='point',transform=(1,0,0,1,20,20),fill='#d02030',stroke='none',line_width=0,id='independent-marker')
  result=p.encode(p.finish(width=60,height=60,padding=0));im=png(result)
  ev=next(e for e in result.trace if e.semantic_id=='independent-marker')
  self.assertEqual(ev.marker,'point');self.assertEqual(ev.kind,'marker')
  self.assertAlmostEqual(ev.box.x,20);self.assertAlmostEqual(ev.box.width,12)
  r,g,b=im.getpixel((24,26));self.assertGreater(r,150);self.assertLess(g,80);self.assertLess(b,100)
  self.assertEqual(im.getpixel((35,26)),(255,255,255))
 def test_marker_missing_component_fault_is_rejected(self):
  p={'source':False,'actors':{},'messages':[{'id':'m','dash':()}],'markers':[{'id':'m','kind':'point'}]}
  probe={'type':'arrows','expected':[{'start':'arrowhead','end':'arrowhead','dashed':False}]}
  self.assertIn('gallery-0-markers',errors(probe,p))
 def test_wrong_number_owner_fault_is_rejected(self):
  p={'source':False,'actors':{'A':100,'B':300},'messages':[],'numbers':[{'center':(100,80)}]}
  self.assertIn('number-anchor',errors({'type':'number','anchor':'B'},p))

if __name__=='__main__':unittest.main()
