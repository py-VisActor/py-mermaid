"""Independent F013 native Canvas checks. No saved renderer-generated goldens.

Synthetic placements isolate drawing from ELK. Expectations are literal source
branches/CSS rules and public Canvas metrics, never rich.py/styles.py helpers.
PNG assertions run with semantic/trace assertions; fault controls prove that a
white PNG, missing glyph or wrong visible paint cannot pass on trace alone.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
import math
import unittest
from PIL import Image
from py_skia_canvas import Canvas
from py_mermaid.api import parse
from py_mermaid.config import resolve_config
from py_mermaid.model.flowchart import (Box, EdgeSection, Flowchart, FlowEdge, FlowGroup,
    FlowLayout, FlowNode, MermaidError, PlacedEdgeLabel, PlacedGroup, PlacedNode,
    Point, RoutedEdge, SourcePosition, SourceSpan)
from py_mermaid.rendering.skia import CanvasSession
from py_mermaid.rendering.labels.sanitize import sanitize_markup

SPAN=SourceSpan(SourcePosition(0,0,1,0),SourcePosition(1,1,1,1))
THEMES=('base','default','dark','forest','neutral','neo','neo-dark','redux','redux-dark','redux-color','redux-dark-color','null')

def fixture(text, *, kind='text', config=None, title='', annotations=False):
    cfg=resolve_config(config)
    node=FlowNode('A',text,SPAN,label_kind=kind,raw_label=text)
    if not annotations:return Flowchart('test-only semantic fixture','TD',(node,),(),cfg,title=title)
    other=FlowNode('B','End',SPAN)
    edge=FlowEdge('e','A','B',SPAN,'**Edge** 中文',SPAN,'markdown','**Edge** 中文')
    group=FlowGroup('G','<b>Group</b>',SPAN,('A','B'),raw_label='<b>Group</b>')
    return Flowchart('test-only annotation fixture','TD',(node,other),(edge,),cfg,groups=(group,),title=title)

def draw(diagram, session=None):
    session=session or CanvasSession('cpu')
    measured=session.measure(diagram);ann=session.measure_annotations(diagram)
    placed=tuple(PlacedNode(n.id,Box(40+i*320,70,n.width,n.height)) for i,n in enumerate(measured))
    groups=tuple(PlacedGroup(g.id,Box(15,15,650,230),title_box=Box(25,25,g.label_width,g.label_height)) for g in ann.groups)
    edges=tuple(RoutedEdge(e.id,(EdgeSection(Point(40+measured[0].width,100),(),Point(360,100)),)) for e in diagram.edges)
    labels=tuple(PlacedEdgeLabel(e.id,Box(220,100,e.width,e.height)) for e in ann.edge_labels)
    title_box=Box(30,-50,ann.title.width,ann.title.height) if ann.title else None
    layout=FlowLayout(placed,edges,max(700,max((p.box.x+p.box.width+20 for p in placed),default=0)),280,'test-only','fixture',groups,labels,title_box)
    return session.render(diagram,measured,layout,annotations=ann)

def image(result):
    img=Image.open(BytesIO(result.data));img.load();return img.convert('RGB')

def region(img,box):
    return tuple(img.crop((max(0,math.floor(box.x)),max(0,math.floor(box.y)),min(img.width,math.ceil(box.x+box.width)),min(img.height,math.ceil(box.y+box.height)))).getdata())

def dark(p):return max(p)<155

def red(p):return p[0]>140 and p[1]<100 and p[2]<100

def blue(p):return p[2]>130 and p[0]<100 and p[1]<130

def verify_visible(result,expected,kind='text',predicate=dark):
    events=[e for e in result.trace if e.kind==kind]
    actual=''.join(e.text or '' for e in events)
    assert actual==expected,(actual,expected)
    img=image(result)
    for event in events:
        if event.text and event.text.strip():
            assert event.box and sum(predicate(p) for p in region(img,event.box))>1,('glyph pixels absent',event.text,event.box)
    return events

class RichCanvasTests(unittest.TestCase):
    def test_plain_public_metrics_and_source_padding(self):
        d=fixture('Italic f 中文');s=CanvasSession('cpu');m=s.measure(d)[0]
        c=Canvas(1,1);c.gpu=False;ctx=c.getContext('2d')
        ctx.font='normal normal 14px "Recursive Variable", arial, sans-serif';ctx.textAlign='left';ctx.textBaseline='alphabetic';ctx.direction='ltr'
        metrics=ctx.measureText('Italic f 中文')
        self.assertAlmostEqual(m.runs[0].width,metrics.width,places=4)
        self.assertEqual(m.width-m.label_width,32);self.assertEqual(m.height-m.label_height,24)
        self.assertGreaterEqual(m.label_width,120);self.assertGreaterEqual(m.label_height,21)
        verify_visible(draw(d),'Italic f 中文')

    def test_html_bold_italic_nested_real_fonts_and_pixels(self):
        result=draw(fixture('<b>Bold <i>Italic中文</i></b>'))
        events=verify_visible(result,'Bold Italic中文')
        italic=next(e for e in events if 'Italic' in e.text)
        self.assertEqual(italic.font_weight,'bold');self.assertEqual(italic.font_style,'italic')
        c=Canvas(1,1);c.gpu=False;ctx=c.getContext('2d');ctx.font='italic bold 14px '+italic.font_family.rstrip(';');ctx.textAlign='left'
        run=next(r for r in result.measured[0].runs if 'Italic' in r.text)
        self.assertAlmostEqual(run.width,ctx.measureText(run.text).width,places=4)

    def test_html_false_tags_literal_not_bold(self):
        result=draw(fixture('<b>literal</b>',config={'htmlLabels':False}))
        events=verify_visible(result,'<b> literal </b>')
        self.assertTrue(all(e.font_weight=='normal' for e in events))

    def test_markdown_html_true_and_false_strong_em(self):
        for mode in (True,False):
            with self.subTest(mode=mode):
                r=draw(fixture('**Bold** and *Italic*',kind='markdown',config={'htmlLabels':mode}))
                events=verify_visible(r,'Bold and Italic')
                self.assertTrue(any(e.font_weight=='bold' and 'Bold' in e.text for e in events))
                self.assertTrue(any(e.font_style=='italic' and 'Italic' in e.text for e in events))

    def test_markdown_nested_source_svg_inner_style_override(self):
        for mode in (True,False):
            r=draw(fixture('**Bold *Inner* End**',kind='markdown',config={'htmlLabels':mode}))
            events=verify_visible(r,'Bold Inner End')
            inner=next(e for e in events if e.text=='Inner')
            self.assertEqual(inner.font_style,'italic');self.assertEqual(inner.font_weight,'bold' if mode else 'normal')

    def test_breaks_multiline_cjk_no_content_loss(self):
        r=draw(fixture('First<br>第二行</br>Third'))
        events=verify_visible(r,'First第二行Third')
        self.assertEqual(len({round(e.points[0].y,3) for e in events}),3)
        self.assertGreaterEqual(r.measured[0].label_height,63)

    def test_entity_once_and_mermaid_numeric_named_entities(self):
        r=draw(fixture('#quot; #9829; &amp;lt;'))
        verify_visible(r,'" ♥ &lt;')
        self.assertNotIn('<',''.join(run.text for run in r.measured[0].runs).replace('&lt;',''))

    def test_dom_purify_missing_versus_explicit_empty_style_policy(self):
        markup='<span style="color:red">Red</span>'
        default=draw(fixture(markup));provided=draw(fixture(markup,config={'dompurifyConfig':{}}))
        # common.ts FORBID_TAGS:['style'] forbids elements, not style attrs.
        a=verify_visible(default,'Red',predicate=red);b=verify_visible(provided,'Red',predicate=red)
        self.assertFalse(default.diagram.config.dompurify_provided)
        self.assertTrue(provided.diagram.config.dompurify_provided)
        self.assertTrue(any('red' in (e.color or '') or 'ff0000' in (e.color or '') for e in b))

    def test_sanitizer_script_event_uri_and_allowlist(self):
        d=fixture('<script>SECRET</script><a href="javascript:alert(1)" onclick="alert(2)">Safe</a>')
        safe=sanitize_markup(d.nodes[0].raw_label,d.config)
        for forbidden in ('SECRET','javascript','onclick','script'):self.assertNotIn(forbidden,safe)
        verify_visible(draw(d),'Safe')
        custom=fixture('<b>Keep</b><i>text</i>',config={'dompurifyConfig':{'ALLOWED_TAGS':['b'],'ALLOWED_ATTR':[]}})
        self.assertEqual(sanitize_markup(custom.nodes[0].raw_label,custom.config),'<b>Keep</b>text')
        verify_visible(draw(custom),'Keeptext')

    def test_font_presentation_before_inline_and_parent_relative_inheritance(self):
        r=draw(fixture('<font color="red" style="color:blue"><small style="font-size:2em">Size</small></font>',config={'dompurifyConfig':{}}))
        events=verify_visible(r,'Size',predicate=blue)
        self.assertEqual(events[0].font_size,28)
        self.assertGreater(r.measured[0].label_height,30)

    def test_nested_opacity_rgba_and_actual_alpha(self):
        r=draw(fixture('<span style="opacity:.5"><span style="opacity:.5;color:black">MMMM</span></span>',config={'dompurifyConfig':{}}))
        events=verify_visible(r,'MMMM',predicate=lambda p:150<min(p)<245)
        self.assertAlmostEqual(events[0].opacity,.25)
        self.assertGreaterEqual(min(min(p) for p in region(image(r),events[0].box)),180)
        rgba=draw(fixture('<span style="color:rgba(255,0,0,.5)">MMMM</span>',config={'dompurifyConfig':{}}))
        verify_visible(rgba,'MMMM',predicate=lambda p:p[0]>240 and 100<p[1]<220 and abs(p[1]-p[2])<10)

    def test_run_background_decoration_visible(self):
        r=draw(fixture('<span style="background-color:yellow;color:red;text-decoration:underline">MMMM</span>',config={'dompurifyConfig':{}}))
        events=verify_visible(r,'MMMM',predicate=red)
        self.assertTrue(any(e.kind=='text-background' for e in r.trace))
        self.assertGreater(sum(p[0]>220 and p[1]>220 and p[2]<100 for p in region(image(r),events[0].box)),5)
        # Underline must add red pixels below the alphabetic baseline, not just trace.
        e=events[0];baseline=e.points[0].y
        self.assertGreater(sum(red(p) for p in region(image(r),Box(e.box.x,baseline+.5,e.box.width,4))),2)

    def test_pre_whitespace_and_nowrap(self):
        d=fixture('<span style="white-space:pre">A   B\nC</span>',config={'dompurifyConfig':{}})
        r=draw(d);verify_visible(r,'A   BC');self.assertEqual(len(r.measured[0].lines),2)
        nowrap=draw(fixture('<span style="white-space:nowrap">one two three four five six seven eight</span>',config={'dompurifyConfig':{}}))
        self.assertEqual(len(nowrap.measured[0].lines),1)
        self.assertGreater(nowrap.measured[0].label_width,120)
        verify_visible(nowrap,'one two three four five six seven eight')

    def test_hidden_inline_no_pixels_or_model_run(self):
        r=draw(fixture('Visible<span style="display:none">SECRET</span>',config={'dompurifyConfig':{}}))
        verify_visible(r,'Visible');self.assertNotIn('SECRET',''.join(x.text for x in r.measured[0].runs))

    def test_direction_and_italic_ink_bounds(self):
        r=draw(fixture('<span dir="rtl" style="font-style:italic;font-size:30px">مرحبا f</span>',config={'dompurifyConfig':{}}))
        verify_visible(r,'مرحبا f')
        n=r.measured[0]
        self.assertTrue(all(run.direction=='rtl' for run in n.runs))
        for run in n.runs:
            self.assertGreaterEqual(run.x-run.ink_left,-.001)
            self.assertLessEqual(run.x+run.ink_right,n.label_width+.001)
        for e in r.trace:
            if e.box:
                self.assertGreaterEqual(e.box.x,-.001);self.assertLessEqual(e.box.x+e.box.width,r.width+.001)

    def test_group_edge_labels_rich_and_title_plain(self):
        r=draw(fixture('Node',annotations=True,title='<b>Literal & title</b>'))
        verify_visible(r,'Group','group-title');verify_visible(r,'Edge 中文','edge-label')
        title=verify_visible(r,'<b>Literal & title</b>','diagram-title')
        self.assertEqual(title[0].font_size,18);self.assertEqual(title[0].font_weight,'normal')
        self.assertTrue(any(e.kind=='edge-label-background' for e in r.trace))
        self.assertTrue(any(e.font_weight=='bold' for e in r.trace if e.kind=='group-title'))

    def test_all_theme_names_real_png_and_source_representative_fill(self):
        # Each theme is explicitly selected at the effective flowchart layer.
        for theme in THEMES:
            with self.subTest(theme=theme):
                r=draw(fixture('Theme',config={'flowchart':{'theme':theme}}));img=image(r)
                self.assertEqual(img.size,(r.width,r.height));self.assertGreater(len(set(img.getdata())),3)
                self.assertTrue(any(e.kind=='text' and e.text=='Theme' for e in r.trace))
                self.assertTrue(any(e.kind=='node' for e in r.trace))
                # Visible ink differs from the independent node interior sample.
                node=next(e for e in r.trace if e.kind=='node');sample=img.getpixel((int(node.box.x+8),int(node.box.y+8)))
                verify_visible(r,'Theme',predicate=lambda p,s=sample:max(abs(a-b) for a,b in zip(p,s))>40)
                if theme in {'redux-color','redux','neo'}:self.assertEqual(sample,(255,255,255))

    def test_neo_gradient_has_blue_and_red_border_pixels(self):
        r=draw(fixture('Gradient',config={'flowchart':{'theme':'neo'}}));img=image(r)
        node=next(e for e in r.trace if e.kind=='node');self.assertIn('linear-gradient',node.stroke)
        left=region(img,Box(node.box.x-2,node.box.y+5,4,node.box.height-10))
        right=region(img,Box(node.box.x+node.box.width-2,node.box.y+5,4,node.box.height-10))
        self.assertGreater(sum(blue(p) for p in left),4);self.assertGreater(sum(red(p) for p in right),4)

    def test_neo_blur_shadow_and_full_bounds(self):
        r=draw(fixture('Shadow',config={'flowchart':{'theme':'neo'}}));img=image(r)
        node=next(e for e in r.trace if e.kind=='node');shadow=next(e for e in r.trace if e.kind=='shadow')
        self.assertLess(shadow.box.y,node.box.y);self.assertGreater(shadow.box.width,node.box.width)
        self.assertGreater(sum(max(p)-min(p)<12 and 180<min(p)<253 for p in region(img,Box(node.box.x+15,node.box.y+node.box.height+1,node.box.width-30,6))),2)
        for e in r.trace:
            if e.box:self.assertTrue(e.box.x>=0 and e.box.y>=0 and e.box.x+e.box.width<=r.width+.01 and e.box.y+e.box.height<=r.height+.01)

    def test_classic_and_neo_round_radius_outline_and_label_containment(self):
        for look in ('classic','neo'):
            d=fixture('Round',config={'flowchart':{'look':look,'theme':'neo'}})
            d=replace(d,nodes=(replace(d.nodes[0],shape='round'),));r=draw(d)
            verify_visible(r,'Round');self.assertTrue(r.measured[0].outline)
            self.assertGreater(r.measured[0].width,r.measured[0].label_width)

    def test_svg_false_markdown_omission_is_source_diagnostic(self):
        r=draw(fixture('Before `code` and [link](https://example.com) After',kind='markdown',config={'htmlLabels':False}))
        verify_visible(r,'Before and After')
        self.assertIn('SOURCE_MARKDOWN_TOKEN_OMISSION:codespan',r.diagnostics)
        self.assertIn('SOURCE_MARKDOWN_TOKEN_OMISSION:link',r.diagnostics)

    def test_controls_resources_and_browser_only_policy_explicit_errors(self):
        mathematical=CanvasSession('cpu').measure(fixture('$$x$$'))[0]
        self.assertTrue(any(run.kind=='math' and run.math_key for run in mathematical.runs))
        # Static controls are now implemented; retain the independent resource
        # and host-policy rejection checks rather than expecting old deferral.
        for text,value in (('<input value="hidden">','hidden'),('<button>Click</button>','Click')):
            measured=CanvasSession('cpu').measure(fixture(text))[0]
            widgets=[run.control for run in measured.runs if run.control is not None]
            self.assertEqual(len(widgets),1)
            self.assertEqual(widgets[0].spec.value or widgets[0].spec.text,value)
            self.assertGreater(widgets[0].width,0)
        cases=[('<img src="https://example.com/a.png">',{},'RESOURCE_NOT_FOUND'),('<style>b{color:red}</style>Text',{'dompurifyConfig':{'ADD_TAGS':['style']}},'UNSUPPORTED_LABEL_STYLE_ELEMENT'),('Text',{'dompurifyConfig':{'WHOLE_DOCUMENT':True}},'UNSUPPORTED_SANITIZER_CONFIG')]
        for text,config,code in cases:
            with self.subTest(text=text),self.assertRaises(MermaidError) as caught:CanvasSession('cpu').measure(fixture(text,config=config))
            self.assertEqual(caught.exception.code,code)

    def test_owner_thread_and_repeated_request_state(self):
        session=CanvasSession('cpu');d=fixture('First')
        with ThreadPoolExecutor(1) as pool:
            future=pool.submit(session.measure,d)
            with self.assertRaises(MermaidError) as caught:future.result()
        self.assertEqual(caught.exception.code,'THREAD_OWNERSHIP')
        draw(fixture('`code`',kind='markdown',config={'htmlLabels':False}),session)
        clean=draw(fixture('Second'),session);verify_visible(clean,'Second');self.assertEqual(clean.diagnostics,())
        self.assertTrue(all(e.text!='First' for e in session.trace))

    def test_png_fault_controls_white_missing_and_wrong_color(self):
        r=draw(fixture('<b>Red</b>',config={'themeCSS':'.nodeLabel {color:red !important;}'}))
        verify_visible(r,'Red',predicate=red)
        white=Image.new('RGB',(r.width,r.height),'white');buf=BytesIO();white.save(buf,format='PNG')
        with self.assertRaises(AssertionError):verify_visible(replace(r,data=buf.getvalue()),'Red',predicate=red)
        with self.assertRaises(AssertionError):verify_visible(replace(r,trace=tuple(e for e in r.trace if e.kind!='text')),'Red',predicate=red)
        black=draw(fixture('Red'))
        with self.assertRaises(AssertionError):verify_visible(black,'Red',predicate=red)

    def test_lists_tables_and_block_text_all_visible(self):
        r=draw(fixture('<ol start="3"><li>Three</li><li>Four</li></ol><table><tr><th>Head</th><td>Cell</td></tr></table>'))
        text=''.join(e.text or '' for e in r.trace if e.kind=='text')
        for value in ('3. Three','4. Four','Head','Cell'):self.assertIn(value,text)
        verify_visible(r,text)
        self.assertGreaterEqual(len(r.measured[0].lines),3)

    def test_author_css_important_and_inline_cascade_pixels(self):
        r=draw(fixture('<span style="color:blue">Paint</span>',config={'dompurifyConfig':{},'themeCSS':'.nodeLabel span { color:red !important; }'}))
        verify_visible(r,'Paint',predicate=red)
        override=draw(fixture('<span style="color:blue !important">Paint</span>',config={'dompurifyConfig':{},'themeCSS':'.nodeLabel span { color:red !important; }'}))
        verify_visible(override,'Paint',predicate=blue)

    def test_svg_lineheight_and_html_absolute_lineheight(self):
        cfg={'dompurifyConfig':{},'themeCSS':'.nodeLabel {line-height:40px !important;}'}
        html_result=draw(fixture('Top<br>Bottom',config=cfg))
        svg_result=draw(fixture('Top<br>Bottom',config={**cfg,'htmlLabels':False}))
        verify_visible(html_result,'TopBottom');verify_visible(svg_result,'TopBottom')
        self.assertAlmostEqual(html_result.measured[0].label_height,80)
        self.assertAlmostEqual(svg_result.measured[0].label_height,30.8)

    def test_auto_and_gpu_keep_native_backend_contract(self):
        for backend in ('auto','gpu'):
            try:result=draw(fixture('<b>Native</b>'),CanvasSession(backend))
            except MermaidError as exc:
                if backend=='gpu':self.assertEqual(exc.code,'GPU_UNAVAILABLE');continue
                raise
            verify_visible(result,'Native')
            self.assertIn(dict(result.backend)['renderer'],('GPU','CPU'))
            if backend=='gpu':self.assertEqual(dict(result.backend)['renderer'],'GPU')

    def test_bold_and_size_changes_actual_glyph_pixels(self):
        plain=draw(fixture('MMMM',config={'fontFamily':'Arial'}))
        bold=draw(fixture('<b>MMMM</b>',config={'fontFamily':'Arial'}))
        a=verify_visible(plain,'MMMM')[0];b=verify_visible(bold,'MMMM')[0]
        normal_ink=sum(dark(p) for p in region(image(plain),a.box))
        bold_ink=sum(dark(p) for p in region(image(bold),b.box))
        self.assertGreater(bold_ink,normal_ink*1.1)
        large=draw(fixture('<span style="font-size:32px">MMMM</span>',config={'fontFamily':'Arial','dompurifyConfig':{}}))
        e=verify_visible(large,'MMMM')[0]
        self.assertGreater(e.box.height,a.box.height*1.8)
        self.assertGreater(sum(dark(p) for p in region(image(large),e.box)),normal_ink*2)

    def test_sanitizer_target_blank_source_noopener_hook(self):
        cfg=resolve_config()
        safe=sanitize_markup('<a href="https://example.com" target="_blank" rel="opener">Link</a>',cfg)
        self.assertIn('target="_blank"',safe);self.assertIn('rel="noopener"',safe);self.assertNotIn('rel="opener"',safe)
        restricted=resolve_config({'dompurifyConfig':{'ALLOWED_ATTR':['href']}})
        hooked=sanitize_markup('<a href="https://example.com" target="_blank">Link</a>',restricted)
        self.assertIn('target="_blank"',hooked);self.assertIn('rel="noopener"',hooked);self.assertNotIn('data-temp-href-target',hooked)
        verify_visible(draw(fixture('<a href="https://example.com" target="_blank">Link</a>')),'Link',predicate=blue)

    def test_hidden_title_explicit_pure_suppression(self):
        d=fixture('Visible',title='Hidden',config={'themeCSS':'.flowchartTitleText {display:none !important;}'})
        result=draw(d);verify_visible(result,'Visible')
        self.assertTrue(result.annotations.title_suppressed)
        self.assertIsNone(result.annotations.title);self.assertIsNone(result.layout.title_box)
        self.assertFalse(any(e.kind=='diagram-title' for e in result.trace))

    def test_real_italic_pixels_against_unambiguous_public_font_and_normal_control(self):
        d=fixture('<i style="color:black">Approved</i>',config={'fontFamily':'Arial','dompurifyConfig':{}},annotations=True)
        d=replace(d,edges=(replace(d.edges[0],label='<i style="color:black">Validate</i>',raw_label='<i style="color:black">Validate</i>',label_kind='text'),),
                    groups=(replace(d.groups[0],label='<i style="color:black">Group</i>',raw_label='<i style="color:black">Group</i>'),))
        result=draw(d);actual=image(result)
        # Independent literal native font syntax, deliberately not _run_font or
        # a string assembled from the same product run fields. The old product
        # "italic normal" parsed back to upright on a18 despite italic trace.
        for kind,word in (('text','Approved'),('edge-label','Validate'),('group-title','Group')):
            with self.subTest(kind=kind):
                event=next(e for e in result.trace if e.kind==kind and e.text==word)
                self.assertEqual(event.font_style,'italic');self.assertEqual(event.font_weight,'normal')
                box=Box(event.box.x-3,event.box.y-3,event.box.width+6,event.box.height+6)
                observed=tuple(dark(p) for p in region(actual,box))
                masks=[]
                for font in ('italic 400 14px Arial','normal 400 14px Arial'):
                    c=Canvas(result.width,result.height);c.gpu=False;ctx=c.getContext('2d')
                    # Source default edge-label mask is #ccc, so raster edge
                    # antialias must composite over gray rather than white.
                    ctx.fillStyle='#cccccc' if kind=='edge-label' else 'white';ctx.fillRect(0,0,result.width,result.height)
                    ctx.font=font;ctx.textAlign='left';ctx.textBaseline='alphabetic';ctx.direction='ltr';ctx.fillStyle='black'
                    ctx.fillText(word,event.points[0].x,event.points[0].y)
                    decoded=Image.open(BytesIO(c.toBufferSync('png'))).convert('RGB')
                    masks.append(tuple(dark(p) for p in region(decoded,box)))
                difference=lambda a,b:sum(x!=y for x,y in zip(a,b,strict=True))
                self.assertLessEqual(difference(observed,masks[0]),max(2,sum(masks[0])*.03),'real italic glyphs must match independent public API')
                self.assertGreater(difference(observed,masks[1]),max(5,sum(masks[0])*.1),'upright glyph negative control must fail')

    def test_real_bold_and_bolditalic_numeric_weight_preserved(self):
        for markup,font in (('<b style="color:black">Approved</b>','normal 700 14px Arial'),('<b style="color:black"><i>Approved</i></b>','italic 700 14px Arial')):
            with self.subTest(font=font):
                result=draw(fixture(markup,config={'fontFamily':'Arial','dompurifyConfig':{}}))
                event=verify_visible(result,'Approved')[0]
                c=Canvas(result.width,result.height);c.gpu=False;ctx=c.getContext('2d')
                ctx.fillStyle='white';ctx.fillRect(0,0,result.width,result.height)
                ctx.font=font;ctx.textAlign='left';ctx.textBaseline='alphabetic';ctx.direction='ltr';ctx.fillStyle='black'
                ctx.fillText('Approved',event.points[0].x,event.points[0].y)
                ref=Image.open(BytesIO(c.toBufferSync('png'))).convert('RGB')
                box=Box(event.box.x-2,event.box.y-2,event.box.width+4,event.box.height+4)
                a=tuple(dark(p) for p in region(image(result),box));b=tuple(dark(p) for p in region(ref,box))
                self.assertLessEqual(sum(x!=y for x,y in zip(a,b,strict=True)),max(2,sum(b)*.03))
                self.assertEqual(event.font_weight,'bold')

if __name__=='__main__':unittest.main()
