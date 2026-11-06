"""Synthetic independent controls for the static scene evidence checker."""
import copy
import io
from pathlib import Path
import sys
import unittest
from PIL import Image, ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from static_flowchart_checks import check_scene,controls


class StaticEvidenceControls(unittest.TestCase):
    def fixture(self):
        node={'id':'A','label':'','shape':'filledCircle'}
        box={'x':4,'y':4,'width':12,'height':12}
        scene={'width':20,'height':20,'diagram':{'nodes':[node],'edges':[],'groups':[],'direction':'TD','title':'','config':{'background':'white','fill':'black','stroke':'black','text_color':'black'}},
               'measured':[{'id':'A','assets':[],'runs':[]}],
               'layout':{'nodes':[{'id':'A','box':box}],'groups':[],'edges':[]},
               'trace':[{'kind':'node','semantic_id':'A','box':box.copy(),'fill':'black','stroke':'black','stroke_width':1,'opacity':1}]}
        expected={'nodes':[['A','']],'edges':[],'groups':[],'direction':'TD'}
        image=Image.new('RGB',(20,20),'white');ImageDraw.Draw(image).ellipse((4,4,16,16),fill='black')
        output=io.BytesIO();image.save(output,format='PNG')
        return scene,output.getvalue(),expected

    def test_actual_paint_and_independent_fault_controls(self):
        scene,png,expected=self.fixture()
        self.assertEqual(check_scene(scene,png,expected),[])
        outcomes=controls(scene,png,expected)
        self.assertTrue(outcomes)
        self.assertTrue(all(outcomes.values()),outcomes)

    def test_trace_cannot_stand_in_for_pixels(self):
        scene,_,expected=self.fixture();output=io.BytesIO()
        Image.new('RGB',(20,20),'white').save(output,format='PNG')
        self.assertTrue(check_scene(scene,output.getvalue(),expected))

    def test_missing_asset_trace_fails_even_when_other_ink_exists(self):
        scene,png,expected=self.fixture()
        scene['measured'][0]['assets']=[{'resource_id':'expected-image'}]
        self.assertIn('L2 asset denominator A',check_scene(scene,png,expected))

    def test_local_fill_probe_rejects_dark_interior_despite_background_white(self):
        scene,png,expected=self.fixture()
        expected['fillProbes']=[{'node':'A','x':.5,'y':.5,'color':'white'}]
        self.assertIn('L2 missing node fill region A',check_scene(scene,png,expected))
        image=Image.open(io.BytesIO(png)).convert('RGB')
        ImageDraw.Draw(image).ellipse((8,8,12,12),fill='white')
        output=io.BytesIO();image.save(output,format='PNG')
        self.assertNotIn('L2 missing node fill region A',check_scene(scene,output.getvalue(),expected))

if __name__=='__main__':unittest.main()
