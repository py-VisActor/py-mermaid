"""Acceptance fault controls bind source state, actual paints and PNG content.

Public rendering happens only during test execution. P2 collection performs no
native work. Handwritten original-DOM states are independent HTML expectations.
"""
from __future__ import annotations

import copy
from dataclasses import fields,is_dataclass
from io import BytesIO
from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT/'tools') not in sys.path:sys.path.insert(0,str(ROOT/'tools'))


def pure(value):
    if is_dataclass(value):return {field.name:pure(getattr(value,field.name)) for field in fields(value)}
    if isinstance(value,dict):return {key:pure(item) for key,item in value.items()}
    if isinstance(value,(tuple,list)):return [pure(item) for item in value]
    return value


def evidence(result):
    return {'width':result.width,'height':result.height,'measured':pure(result.measured),
            'annotations':pure(result.annotations),'trace':pure(result.trace)}


def png(image):
    buffer=BytesIO();image.save(buffer,'PNG');return buffer.getvalue()


def reference():
    # HTML input initial state; source browser exposes these IDL values.
    state={'id':'value','tag':'input','type':'text','value':'RealValue','checked':False,
           'effectiveDisabled':False,'readonly':False,'multiple':False,
           'box':{'x':0,'y':0,'width':180,'height':40},
           'style':{'display':'inline-block','visibility':'visible','appearance':'auto'},
           'effectiveOpacity':1}
    expected={key:state[key] for key in ('id','tag','type','value','checked','effectiveDisabled','readonly','multiple')}
    return {'id':'checker-control','controlExpected':[expected]}, {'htmlControls':[state]}


class StaticControlCheckerFaults(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from py_mermaid import arender
        self.result=await arender('flowchart TD\nA["<input id=\'value\' value=\'RealValue\' style=\'width:180px;height:40px\'>"]',backend='cpu')
        self.scene=evidence(self.result);self.case,self.original=reference()

    def check(self,*,case=None,original=None,scene=None,data=None):
        from check_html_controls import check_control_case
        return check_control_case(case if case is not None else self.case,
                                  original if original is not None else self.original,
                                  scene if scene is not None else self.scene,
                                  data if data is not None else self.result.data)

    def test_real_value_pixels_and_initial_state_pass_jointly(self):
        self.assertEqual(self.check(),[])

    def test_wrong_native_state_rejected(self):
        from check_html_controls import native_controls
        scene=copy.deepcopy(self.scene);native_controls(scene)[0]['spec']['value']='Counterfeit'
        self.assertTrue(self.check(scene=scene))

    def test_source_expected_cannot_be_forged_to_fit_native(self):
        case=copy.deepcopy(self.case);case['controlExpected'][0]['value']='Counterfeit'
        self.assertTrue(self.check(case=case))

    def test_missing_original_state_evidence_rejected(self):
        self.assertTrue(self.check(original={}))

    def test_missing_measured_control_rejected(self):
        scene=copy.deepcopy(self.scene);scene['measured']=[]
        self.assertTrue(self.check(scene=scene))

    def test_missing_actual_control_container_rejected(self):
        scene=copy.deepcopy(self.scene);scene['trace']=[e for e in scene['trace'] if e['kind']!='control']
        self.assertTrue(self.check(scene=scene))

    def test_missing_text_trace_cannot_pass_with_outer_frame_ink(self):
        scene=copy.deepcopy(self.scene)
        scene['trace']=[e for e in scene['trace'] if e['kind']!='control-text']
        self.assertTrue(any(e['kind']=='control-roundrect' for e in scene['trace']))
        self.assertTrue(self.check(scene=scene))

    def test_pure_white_image_rejected_with_unchanged_truthful_trace(self):
        image=Image.new('RGB',(self.result.width,self.result.height),'white')
        self.assertTrue(self.check(data=png(image)))

    def test_value_glyphs_erased_frame_preserved_is_rejected(self):
        scene=copy.deepcopy(self.scene)
        image=Image.open(BytesIO(self.result.data)).convert('RGB')
        for event in scene['trace']:
            if event['kind']=='control-text':
                b=event['box'];image.paste('white',(int(b['x']),int(b['y']),int(b['x']+b['width']+1),int(b['y']+b['height']+1)))
        self.assertTrue(self.check(scene=scene,data=png(image)))

    def test_outer_border_cannot_substitute_for_fabricated_value_glyph_box(self):
        scene=copy.deepcopy(self.scene);image=Image.open(BytesIO(self.result.data)).convert('RGB')
        box=next(e['box'] for e in scene['trace'] if e['kind']=='control')
        image.paste('white',(int(box['x']+3),int(box['y']+3),int(box['x']+box['width']-3),int(box['y']+box['height']-3)))
        for event in scene['trace']:
            if event['kind']=='control-text':
                # An adversarial declared text box is moved onto an existing
                # varying border strip. Glyphs remain absent from the interior.
                event['box']={'x':box['x']+.2,'y':box['y']+2,'width':8,'height':12}
        self.assertTrue(self.check(scene=scene,data=png(image)))

    def test_incorrect_text_content_metadata_rejected(self):
        scene=copy.deepcopy(self.scene)
        for event in scene['trace']:
            if event['kind']=='control-text':event['text']='Counterfeit'
        self.assertTrue(self.check(scene=scene))

    async def test_input_password_source_value_must_not_appear_as_plain_glyphs(self):
        from py_mermaid import arender
        result=await arender('flowchart TD\nA["<input id=\'value\' type=\'password\' value=\'RealValue\' style=\'width:180px;height:40px\'>"]',backend='cpu')
        scene=evidence(result);case,original=reference()
        case['controlExpected'][0]['type']='password';original['htmlControls'][0]['type']='password'
        for event in scene['trace']:
            if event['kind']=='control-text':event['text']='RealValue'
        self.assertTrue(self.check(case=case,original=original,scene=scene,data=result.data))

    async def test_checked_checkbox_chrome_without_mark_rejected(self):
        from py_mermaid import arender
        result=await arender('flowchart TD\nA["<input id=\'value\' type=\'checkbox\' checked>"]',backend='cpu')
        scene=evidence(result);case,original=reference()
        for state in (case['controlExpected'][0],original['htmlControls'][0]):state.update(type='checkbox',checked=True,value='on')
        scene['trace']=[event for event in scene['trace'] if event['kind']!='control-path']
        self.assertTrue(self.check(case=case,original=original,scene=scene,data=result.data))

    def test_encoded_size_and_missing_control_contract_rejected(self):
        self.assertTrue(self.check(data=png(Image.new('RGB',(2,2),'black'))))
        self.assertTrue(self.check(case={'controlExpected':[]}))
