"""Fixed-source numeric branch expectations; native execution only in tests."""
import io
import json
import os
from pathlib import Path
import unittest
from PIL import Image, ImageColor
from support_c import ABNF_PROBES, cases, center, path_endpoints


class SequenceGeometryBranches(unittest.IsolatedAsyncioTestCase):
    async def render(self, case):
        from py_mermaid import arender
        result = await arender(case['source'],config=case['config'],backend='cpu')
        image = Image.open(io.BytesIO(result.data)).convert('RGB')
        self.assertEqual(image.size,(result.width,result.height))
        self.assertGreater(len(set(image.getdata())),3)
        return result

    async def test_source_endpoint_classes_and_neo_offsets(self):
        for case in cases():
            p=case['branchProbe']
            if p['type'] not in ('endpoint','activation'):continue
            with self.subTest(id=case['id']):
                r=await self.render(case);actors=dict(r.layout.actors)
                start,end=path_endpoints(next(e.path for e in r.trace if e.kind=='message'))
                self.assertAlmostEqual(start[0]-center(actors[p['sender']])[0],p['startOffset'])
                self.assertAlmostEqual(end[0]-center(actors[p['receiver']])[0],p['endOffset'])
                # Mid-shaft ROI cannot be satisfied by actor frames/lifelines
                # or the message caption above the shaft.
                image=Image.open(io.BytesIO(r.data)).convert('RGB')
                mid=(start[0]+end[0])/2;yy=start[1]
                strip=image.crop((int(mid-5),int(yy-2),int(mid+6),int(yy+3)))
                self.assertGreater(sum(min(pixel)<180 for pixel in strip.getdata()),3)

    async def test_source_central_circles_follow_actor_centers_and_autonumber_arm(self):
        for case in cases():
            p=case['branchProbe']
            if p['type']!='central':continue
            with self.subTest(id=case['id']):
                r=await self.render(case);actors=dict(r.layout.actors)
                actual=sorted(center(e.box)[0] for e in r.trace if e.kind=='central-connection')
                expected=sorted(center(actors[c['actor']])[0]+c['offset'] for c in p['circles'])
                self.assertEqual(len(actual),len(expected))
                for a,b in zip(actual,expected):self.assertAlmostEqual(a,b)

    async def test_source_number_anchor_tracks_sender_or_reverse_receiver(self):
        for case in cases():
            p=case['branchProbe']
            if p['type']!='number':continue
            with self.subTest(id=case['id']):
                r=await self.render(case);actors=dict(r.layout.actors)
                e=next(e for e in r.trace if e.kind=='sequence-number-box')
                self.assertAlmostEqual(center(e.box)[0],center(actors[p['anchor']])[0])
                self.assertTrue(any(e.text=='1' and e.kind=='sequence-number' for e in r.trace))

    async def test_source_self_path_start_offset_with_reverse_and_bidirectional_numbering(self):
        for case in cases():
            p=case['branchProbe']
            if p['type']!='self':continue
            with self.subTest(id=case['id']):
                r=await self.render(case);actor=dict(r.layout.actors)['A']
                path=next(e.path for e in r.trace if e.kind=='message');start,end=path_endpoints(path)
                self.assertAlmostEqual(start[0]-center(actor)[0],p['startOffset'])
                self.assertAlmostEqual(end[0]-center(actor)[0],1)
                self.assertAlmostEqual(end[1]-start[1],25 if p['angular'] else 20)
                self.assertEqual('C' in path,not p['angular'])

    async def test_nested_frames_retain_content_and_section_geometry(self):
        for case in cases():
            p=case['branchProbe']
            if p['type']!='frame':continue
            with self.subTest(id=case['id']):
                r=await self.render(case)
                self.assertEqual(len(r.layout.fragments),p['requiredFrames'])
                for _,frame in r.layout.fragments:
                    self.assertGreater(frame.width,0);self.assertGreater(frame.height,0)
                # Source inset sections span the parent, no hardcoded engine size.
                for divider in (e for e in r.trace if e.kind=='fragment-divider'):
                    self.assertEqual(tuple(divider.dash),(3.,3.))
                for e in r.trace:
                    if e.kind in ('message-text','note-text') and e.box:
                        self.assertTrue(any(b.x<=e.box.x+2 and b.y<=e.box.y+2 and b.x+b.width>=e.box.x+e.box.width-2 and b.y+b.height>=e.box.y+e.box.height-2 for _,b in r.layout.fragments))

    async def test_all_26_painted_arrow_components_and_dash_in_both_directions(self):
        from probe_c import errors_for
        from support_c import native_projection
        from dataclasses import asdict
        for case in cases():
            if case['branchProbe']['type']!='arrows':continue
            with self.subTest(id=case['id']):
                r=await self.render(case)
                projection=native_projection({'layout':asdict(r.layout),'trace':[asdict(e) for e in r.trace]})
                self.assertEqual(errors_for(case['branchProbe'],projection),[])


class InfoRoleBranches(unittest.IsolatedAsyncioTestCase):
    async def test_all_eleven_theme_version_roles_and_existing_css_override(self):
        from py_mermaid import arender
        for case in cases():
            p=case['branchProbe']
            if p['type']!='info':continue
            with self.subTest(id=case['id']):
                r=await arender(case['source'],config=case['config'],backend='cpu')
                self.assertEqual((r.width,r.height),(400,100))
                e=next(e for e in r.trace if e.text==p['version'])
                self.assertEqual(e.font_size,p['fontSize'])
                self.assertEqual(ImageColor.getrgb(e.color),ImageColor.getrgb(p['color']))
                image=Image.open(io.BytesIO(r.data)).convert('RGB');b=e.box
                roi=image.crop((int(b.x),int(b.y),int(b.x+b.width+1),int(b.y+b.height+1)))
                self.assertGreater(len(set(roi.getdata())),3,'trace alone cannot prove version ink')


class AbnfSourcePriority(unittest.TestCase):
    def test_fixed_original_keyword_vs_hidden_comment_priority(self):
        from py_mermaid import parse, MermaidError
        # An independent original-parser receipt is mandatory; missing evidence
        # is an ERROR, never a skip or guessed successful diagram fixture.
        source=Path(os.environ['BRANCH_C_ORACLE'])/'abnf.json'
        rows=json.loads(source.read_text('utf8'))['cases'];actual={c['id']:c for c in rows}
        self.assertEqual(set(actual),{p[0] for p in ABNF_PROBES})
        for identifier,tex,_ in ABNF_PROBES:
            with self.subTest(id=identifier):
                a=actual[identifier]
                self.assertEqual(a['source'],tex)
                try:result=parse(tex);accepted=True
                except MermaidError:accepted=False
                self.assertEqual(accepted,a['accepted'],'fixed original lexer/parser priority differs')
                if accepted:self.assertEqual([r.name for r in result.model.rules],a['rules'])


class ZenMarkedBranches(unittest.TestCase):
    def test_delimiter_and_escape_predicates_against_consumed_source_tokens(self):
        from html.parser import HTMLParser
        from py_mermaid.diagrams.zenuml.layout import _comment_markup
        class Projection(HTMLParser):
            def __init__(self):super().__init__(convert_charrefs=True);self.text=[];self.bold=False;self.italic=False
            def handle_data(self,value):self.text.append(value)
            def handle_starttag(self,tag,attrs):self.bold|=tag in ('strong','b');self.italic|=tag in ('em','i')
        for case in cases():
            p=case['branchProbe']
            if p['type']!='comment':continue
            with self.subTest(id=case['id']):
                parsed=Projection();parsed.feed(_comment_markup(p['comment']))
                self.assertEqual(''.join(''.join(parsed.text).split()),''.join(p['visible'].split()))
                self.assertEqual(parsed.bold,p['bold']);self.assertEqual(parsed.italic,p['italic'])

    def test_comment_height_uses_raw_trimmed_line_count_even_fence_and_paragraph(self):
        from py_mermaid import parse
        from py_mermaid.diagrams.zenuml.geometry import vertical_layout
        for case in cases():
            p=case['branchProbe']
            if p['type']!='comment':continue
            with self.subTest(id=case['id']):
                model=parse(case['source']).model
                placed,_,_=vertical_layout(model.statements,origin=model.starter)
                self.assertEqual(placed[0].comment_height,p['rawLineCount']*20)
