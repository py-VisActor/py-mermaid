"""Independent static-host contracts, not browser pixel-coordinate goldens.

The synthetic font has 5px advance per scalar at 10px, an 8px/2px font
cell, and a measured 4px x-height. It isolates CSS box arithmetic from real
font/platform differences; C owns public-Canvas/pixel correspondence tests.
Expected behavior comes from HTML initial-state/CSS box semantics and the
frozen pure provider contract. No candidate private helper computes expected
values, and no candidate-generated snapshot is used.
"""
from dataclasses import replace
import math
import unittest

from py_mermaid.model.controls import ControlSpec, ControlOption
from py_mermaid.model.flowchart import ResolvedStyle, MeasuredTextRun, MermaidError
from py_mermaid.rendering.labels.controls.layout import (
    layout_control, control_ua_style, split_control_style, parse_control_declarations,
)


def measure(text, style):
    scale = style.font_size/10
    width = len(text)*5*scale
    return {'width': width, 'actualBoundingBoxLeft': 0, 'actualBoundingBoxRight': width,
            'actualBoundingBoxAscent': (4 if text=='x' else 8)*scale,
            'actualBoundingBoxDescent': (0 if text=='x' else 2)*scale,
            'fontBoundingBoxAscent': 8*scale, 'fontBoundingBoxDescent': 2*scale}


STYLE = ResolvedStyle(font_family='Synthetic contract font',font_size=10,line_height=1.2,
                      font_weight='normal',font_style='normal',text_align='left',
                      text_color='#000000',background='transparent',shadow_opacity=0)


def spec(tag='input', type_='text', css='', **kwargs):
    attrs = dict(kwargs.pop('attrs', {}))
    if css:attrs['style']=css
    return ControlSpec(tag,input_type=type_ if tag=='input' else '',attributes=tuple(attrs.items()),**kwargs)


def texts(layout):
    return [p for p in layout.paints if p.kind=='text']


class StaticControlLayout(unittest.TestCase):
    def layout(self, control, style=STYLE, **kwargs):
        return layout_control(control,style,measure,**kwargs)

    def reject(self, control, code='UNSUPPORTED_CONTROL_CSS', **kwargs):
        with self.assertRaises(MermaidError) as caught:self.layout(control,**kwargs)
        self.assertEqual(caught.exception.code,code)

    def test_l01_all_retained_input_types_have_finite_initial_boxes(self):
        types='text search tel url email password date month week time datetime-local number range color checkbox radio file submit image reset button'.split()
        for kind in types:
            with self.subTest(kind=kind):
                c=spec(type_=kind,value='#112233' if kind=='color' else '',fraction=.5)
                before=repr(c);box=self.layout(c)
                self.assertTrue(all(math.isfinite(v) and v>=0 for v in (box.width,box.height)))
                self.assertGreater(box.width,0)
                self.assertGreater(box.height,0)
                self.assertEqual(repr(c),before)

    def test_l02_hidden_and_display_none_never_measure_or_paint(self):
        def forbidden(*args):raise AssertionError('hidden control invoked measurement')
        for c,s in [(spec(type_='hidden'),STYLE),(spec(hidden=True),STYLE),(spec(),replace(STYLE,display='none'))]:
            result=layout_control(c,s,forbidden)
            self.assertEqual((result.width,result.height,result.baseline),(0,0,0))
            self.assertEqual(result.paints,())

    def test_l03_relative_meter_font_and_form_ua_are_separate_bases(self):
        parent=replace(STYLE,font_size=30,font_family='Parent family',font_weight='bold')
        self.assertEqual(control_ua_style('meter',parent).font_size,30)
        self.assertEqual(control_ua_style('progress',parent).font_family,'Parent family')
        for tag in ('input','button','select','textarea'):
            base=control_ua_style(tag,parent)
            self.assertEqual(base.font_weight,'normal')
            self.assertEqual(base.background,'transparent')
        self.assertIn('mono',control_ua_style('textarea',parent).font_family)

    def test_l04_text_size_attribute_adds_real_zero_advances(self):
        a=self.layout(spec(attrs={'size':'4'}));b=self.layout(spec(attrs={'size':'9'}))
        self.assertAlmostEqual(b.width-a.width,25)
        self.assertEqual(a.height,b.height)

    def test_l05_password_masks_value_but_preserves_placeholder(self):
        password=self.layout(spec(type_='password',value='secret'))
        self.assertNotIn('secret',''.join(p.text for p in texts(password)))
        self.assertEqual(len(texts(password)[0].text),6)
        empty=self.layout(spec(type_='password',attrs={'placeholder':'Password'}))
        self.assertEqual(texts(empty)[0].text,'Password')

    def test_l06_value_wins_over_placeholder(self):
        c=self.layout(spec(value='Actual',attrs={'placeholder':'Hint'}))
        self.assertEqual([p.text for p in texts(c)],['Actual'])

    def test_l07_missing_action_caption_differs_from_explicit_empty(self):
        for kind,caption in [('submit','Submit'),('reset','Reset')]:
            with self.subTest(kind=kind):
                self.assertEqual([p.text for p in texts(self.layout(spec(type_=kind)))],[caption])
                self.assertEqual(texts(self.layout(spec(type_=kind,attrs={'value':''}))),[])

    def test_l08_readonly_keeps_content_and_geometry(self):
        a=self.layout(spec(value='Read'));b=self.layout(spec(value='Read',readonly=True))
        self.assertEqual((a.width,a.height),(b.width,b.height))
        self.assertEqual([p.text for p in texts(a)],[p.text for p in texts(b)])
        self.assertEqual(texts(a)[0].fill,texts(b)[0].fill)

    def test_l09_content_box_dimensions_add_padding_and_border(self):
        c=self.layout(spec(css='width:100px;height:20px;padding:3px;border:2px solid black'))
        self.assertEqual((c.width,c.height),(110,30))
        self.assertEqual(c.clip,(5,5,100,20))

    def test_l10_border_box_dimensions_include_padding_and_border(self):
        c=self.layout(spec(css='box-sizing:border-box;width:100px;height:30px;padding:3px;border:2px solid black'))
        self.assertEqual((c.width,c.height),(100,30))
        self.assertEqual(c.clip,(5,5,90,20))

    def test_l11_minimum_wins_over_smaller_maximum(self):
        c=self.layout(spec(css='width:200px;min-width:80px;max-width:60px;padding:0;border:0'))
        self.assertEqual(c.width,80)

    def test_l12_asymmetric_padding_border_and_content_origin(self):
        c=self.layout(spec(css='width:100px;height:20px;padding:1px 2px 3px 4px;border:2px solid black;border-left-width:5px'))
        self.assertEqual(c.width,113)
        self.assertEqual(c.height,28)
        self.assertEqual(c.clip,(9,3,100,20))

    def test_l13_margins_shift_once_and_are_in_total_size(self):
        a=self.layout(spec(value='X',css='padding:0;border:0;width:40px;height:20px'))
        b=self.layout(spec(value='X',css='padding:0;border:0;width:40px;height:20px;margin:2px 3px 4px 5px'))
        self.assertEqual((b.width,b.height),(48,26))
        self.assertEqual((texts(b)[0].x-texts(a)[0].x,texts(b)[0].y-texts(a)[0].y),(5,2))
        self.assertEqual(b.baseline-a.baseline,2)

    def test_l14_finite_percentage_has_containing_block_reference(self):
        c=self.layout(spec(css='width:50%;height:25%;padding:0;border:0'),containing_width=200,containing_height=80)
        self.assertEqual((c.width,c.height),(100,20))

    def test_l15_indefinite_percentage_is_auto(self):
        a=self.layout(spec());b=self.layout(spec(css='width:50%;height:25%'))
        self.assertEqual((a.width,a.height),(b.width,b.height))

    def test_l16_physical_css_units_use_96dpi(self):
        c=self.layout(spec(css='width:1in;height:2.54cm;padding:0;border:0'))
        self.assertAlmostEqual(c.width,96);self.assertAlmostEqual(c.height,96)

    def test_l17_ex_and_ch_use_injected_metrics(self):
        c=self.layout(spec(css='width:4ch;height:2ex;padding:0;border:0'))
        self.assertEqual((c.width,c.height),(20,8))

    def test_l18_textarea_row_height_uses_resolved_line_height(self):
        c=self.layout(spec('textarea',attrs={'rows':'3'},css='padding:0;border:0'),replace(STYLE,line_height=2))
        self.assertEqual(c.height,60)

    def test_l19_important_shorthand_blocks_later_normal_longhand(self):
        c=self.layout(spec(css='width:100px;border:0;padding:2px !important;padding-left:7px'))
        self.assertEqual(c.width,104);self.assertEqual(c.clip[0],2)

    def test_l20_later_border_shorthand_resets_prior_width(self):
        a=self.layout(spec(css='width:100px;padding:0;border-width:5px;border:1px solid black'))
        b=self.layout(spec(css='width:100px;padding:0;border:1px solid black;border-width:5px'))
        self.assertEqual((a.width,b.width),(102,110))

    def test_l21_radius_is_bounded_by_the_box(self):
        c=self.layout(spec(css='width:20px;height:10px;padding:0;border:0;border-radius:999px'))
        self.assertTrue(any(p.radius>0 for p in c.paints))
        self.assertTrue(all(p.radius<=5 for p in c.paints))

    def test_l22_unsupported_css_is_explicit(self):
        for css in ('width:calc(100% - 1px)','background:linear-gradient(red,blue)','border-radius:2px / 4px'):
            with self.subTest(css=css):self.reject(spec(css=css))

    def test_l23_nonfinite_public_metric_is_rejected(self):
        def bad(*args):return {'width':math.nan,'actualBoundingBoxAscent':math.nan}
        with self.assertRaises(MermaidError) as c:layout_control(spec(),STYLE,bad)
        self.assertEqual(c.exception.code,'INVALID_MEASUREMENT')

    def test_l24_image_single_dimension_preserves_ratio(self):
        calls=[]
        def resource(*args):calls.append(args);return (60,30)
        c=self.layout(spec(type_='image',attrs={'src':'resource:sample'},css='width:120px'),asset_loader=resource)
        image=next(p for p in c.paints if p.kind=='image')
        self.assertEqual((image.width,image.height),(120,60))
        self.assertEqual(image.resource_id,'resource:sample')
        self.assertEqual(calls[0][1],'control-image')

    def test_l25_image_both_dimensions_are_explicit(self):
        c=self.layout(spec(type_='image',attrs={'src':'resource:sample'},css='width:120px;height:40px'),asset_loader=lambda *args:(60,30))
        image=next(p for p in c.paints if p.kind=='image')
        self.assertEqual((image.width,image.height),(120,40))

    def test_l26_image_cannot_silently_skip_missing_loader(self):
        self.reject(spec(type_='image',attrs={'src':'resource:sample'}),'RESOURCE_NOT_FOUND')

    def test_l27_image_without_source_has_measured_alt(self):
        c=self.layout(spec(type_='image',attrs={'alt':'Send'}))
        self.assertEqual([p.text for p in texts(c)],['Send'])

    def test_l28_checked_checkbox_and_radio_have_additional_visible_marks(self):
        for kind in ('checkbox','radio'):
            a=self.layout(spec(type_=kind));b=self.layout(spec(type_=kind,checked=True))
            with self.subTest(kind=kind):
                self.assertEqual((a.width,a.height),(b.width,b.height))
                self.assertGreater(len(b.paints),len(a.paints))

    def test_l29_range_fraction_moves_thumb_and_rtl_reverses(self):
        def center(c):
            p=next(p for p in c.paints if p.kind=='circle')
            return p.x+p.width/2
        a=self.layout(spec(type_='range',fraction=.25));b=self.layout(spec(type_='range',fraction=.75))
        rtl=self.layout(spec(type_='range',fraction=.25),replace(STYLE,direction='rtl'))
        self.assertLess(center(a),center(b))
        self.assertAlmostEqual(center(a)+center(rtl),a.width)

    def test_l30_meter_quality_bands_are_not_a_single_generic_fill(self):
        fills=[]
        for f in (.2,.5,.9):
            c=self.layout(spec('meter',fraction=f,minimum=0,maximum=100,attrs={'low':'30','high':'70','optimum':'0'}))
            fills.append(c.paints[-1].fill)
        self.assertEqual(len(set(fills)),3)

    def test_l31_meter_optimum_middle_reverses_quality_at_outer_bands(self):
        a=self.layout(spec('meter',fraction=.5,minimum=0,maximum=100,attrs={'low':'30','high':'70','optimum':'50'}))
        b=self.layout(spec('meter',fraction=.1,minimum=0,maximum=100,attrs={'low':'30','high':'70','optimum':'50'}))
        self.assertNotEqual(a.paints[-1].fill,b.paints[-1].fill)

    def test_l32_indeterminate_progress_is_visible_but_not_zero_value(self):
        a=self.layout(spec('progress',fraction=None));b=self.layout(spec('progress',fraction=0))
        self.assertGreater(a.paints[-1].width,0)
        self.assertEqual(b.paints[-1].width,0)
        self.assertEqual((a.width,a.height),(b.width,b.height))

    def test_l33_disabled_range_removes_active_accent(self):
        c=self.layout(spec(type_='range',disabled=True,fraction=.5,css='accent-color:#ff00ff'))
        self.assertNotIn('#ff00ff',[p.fill for p in c.paints])

    def test_l34_single_select_uses_selected_index_not_first_option(self):
        c=self.layout(spec('select',options=(ControlOption('First'),ControlOption('Chosen')),selected_indices=(1,)))
        self.assertEqual([p.text for p in texts(c)],['Chosen'])

    def test_l35_multiple_list_highlights_stay_within_visible_content(self):
        options=tuple(ControlOption(str(i)) for i in range(8))
        c=self.layout(spec('select',multiple=True,options=options,selected_indices=(6,7),attrs={'size':'3'}))
        x,y,w,h=c.clip
        for p in c.paints:
            if p.kind=='rect' and p.fill not in ('#ffffff','transparent'):
                self.assertGreaterEqual(p.y,y);self.assertLessEqual(p.y+p.height,y+h)

    def test_l36_optgroup_heading_and_disabled_option_are_distinct(self):
        c=self.layout(spec('select',multiple=True,options=(ControlOption('Enabled',group='Group'),ControlOption('Disabled',disabled=True,group='Group')),attrs={'size':'4'}))
        bytext={p.text:p for p in texts(c)}
        self.assertEqual(bytext['Group'].font_weight,'bold')
        self.assertNotEqual(bytext['Enabled'].fill,bytext['Disabled'].fill)

    def test_l37_select_size_adds_rows_without_changing_option_identity(self):
        opts=(ControlOption('A'),ControlOption('B'))
        a=self.layout(spec('select',options=opts,attrs={'size':'2'}));b=self.layout(spec('select',options=opts,attrs={'size':'4'}))
        self.assertAlmostEqual(b.height-a.height,24)

    def test_l38_rtl_value_and_text_decoration_survive_to_paints(self):
        c=self.layout(spec(value='RTL'),replace(STYLE,direction='rtl',decoration='underline'))
        p=texts(c)[0]
        self.assertEqual((p.direction,p.decoration),('rtl','underline'))
        self.assertGreater(p.x,c.clip[0])

    def test_l39_textarea_cols_and_rows_are_measured(self):
        a=self.layout(spec('textarea',attrs={'cols':'4','rows':'2'}));b=self.layout(spec('textarea',attrs={'cols':'7','rows':'4'}))
        self.assertEqual(b.width-a.width,15);self.assertEqual(b.height-a.height,24)

    def test_l40_textarea_explicit_linebreaks_have_ordered_baselines(self):
        c=self.layout(spec('textarea',value='One\nTwo'))
        p=texts(c);self.assertEqual([v.text for v in p],['One','Two'])
        self.assertEqual(p[1].y-p[0].y,12)

    def test_l41_textarea_wrap_prefers_word_boundaries(self):
        c=self.layout(spec('textarea',value='hello world',css='width:40px;padding:0;border:0'))
        self.assertEqual([v.text.rstrip() for v in texts(c)],['hello','world'])

    def test_l42_textarea_wrap_off_keeps_unbroken_content_with_clip(self):
        c=self.layout(spec('textarea',value='hello world',attrs={'wrap':'off'},css='width:20px'))
        self.assertEqual([v.text for v in texts(c)],['hello world'])
        self.assertIsNotNone(c.clip)

    def test_l43_empty_textarea_placeholder_is_not_value(self):
        c=self.layout(spec('textarea',attrs={'placeholder':'Hint'}));v=self.layout(spec('textarea',value='Real',attrs={'placeholder':'Hint'}))
        self.assertEqual([p.text for p in texts(c)],['Hint'])
        self.assertEqual([p.text for p in texts(v)],['Real'])
        self.assertEqual((c.width,c.height),(v.width,v.height))

    def test_l44_long_value_clips_instead_of_expanding_explicit_box(self):
        c=self.layout(spec(value='A'*100,css='width:20px;height:12px;padding:0;border:0'))
        self.assertEqual((c.width,c.height),(20,12));self.assertEqual(c.clip,(0,0,20,12))
        self.assertEqual(texts(c)[0].text,'A'*100)

    def test_l45_visible_overflow_has_no_content_clip(self):
        c=self.layout(spec(value='Overflow',css='width:10px;overflow:visible'))
        self.assertIsNone(c.clip)

    def test_l46_numeric_vertical_align_changes_baseline_not_box_dimensions(self):
        a=self.layout(spec());b=self.layout(spec(css='vertical-align:3px'))
        self.assertEqual((a.width,a.height),(b.width,b.height))
        self.assertEqual(b.baseline-a.baseline,3)

    def test_l47_appearance_none_removes_checkbox_mark_but_keeps_author_border(self):
        c=self.layout(spec(type_='checkbox',checked=True,css='appearance:none;width:20px;height:20px;border:1px solid red'))
        self.assertFalse(any(p.kind=='path' for p in c.paints))
        self.assertTrue(any(p.stroke=='red' for p in c.paints))

    def test_l48_margin_does_not_translate_path_coordinates_twice(self):
        a=self.layout(spec(type_='checkbox',checked=True));b=self.layout(spec(type_='checkbox',checked=True,css='margin:3px 0 0 5px'))
        p=next(p for p in a.paints if p.kind=='path');q=next(p for p in b.paints if p.kind=='path')
        self.assertEqual(p.path,q.path)
        self.assertEqual((q.x-p.x,q.y-p.y),(5,3))

    def test_l49_disabled_author_color_can_override_ua_gray(self):
        ua=control_ua_style('input',STYLE,disabled=True)
        red=replace(ua,text_color='#ff0000',current_color='#ff0000')
        c=self.layout(spec(disabled=True,value='Red'),red)
        self.assertEqual(texts(c)[0].fill,'#ff0000')

    def test_l50_css_split_does_not_lose_generic_declarations_or_important(self):
        generic,control=split_control_style('color:red;width:50px !important;font-weight:bold;border:1px solid blue')
        self.assertIn('color:red',generic);self.assertIn('font-weight:bold',generic)
        self.assertNotIn('width',generic);self.assertIn('width:50px !important',control)
        self.assertIn(('width','50px',True),parse_control_declarations(control))

    def test_l58_source_ua_box_sizing_defaults_are_type_specific(self):
        css='width:100px;height:40px;padding:4px;border:2px solid black'
        for tag,kind in [('button',''),('select',''),('meter',''),('progress',''),('input','search'),('input','checkbox'),('input','color'),('input','submit')]:
            with self.subTest(tag=tag,kind=kind):
                c=self.layout(spec(tag,type_=kind,css=css))
                self.assertEqual((c.width,c.height),(100,40))
        for kind in ('text','number','date','range'):
            with self.subTest(kind=kind):
                c=self.layout(spec(type_=kind,css=css))
                self.assertEqual((c.width,c.height),(112,52))

    def test_l59_ua_display_does_not_inherit_parent_block(self):
        parent=replace(STYLE,display='block')
        for tag in ('input','button','select','textarea','meter','progress'):
            self.assertEqual(control_ua_style(tag,parent).display,'inline-block')
        self.assertEqual(control_ua_style('fieldset',replace(STYLE,display='inline')).display,'block')

    def test_l60_date_time_ua_font_is_monospace(self):
        for kind in ('date','month','week','time','datetime-local'):
            self.assertIn('mono',control_ua_style('input',STYLE,input_type=kind).font_family)
        self.assertNotIn('mono',control_ua_style('input',STYLE,input_type='text').font_family)

    def test_l61_radio_checked_center_uses_accent_inside_white_circle(self):
        c=self.layout(spec(type_='radio',checked=True,css='accent-color:#1144cc'))
        circles=[p for p in c.paints if p.kind=='circle']
        self.assertEqual(len(circles),2)
        self.assertEqual(circles[0].fill,'#ffffff')
        self.assertEqual(circles[1].fill,'#1144cc')
        self.assertLess(circles[1].width,circles[0].width)

    def test_l62_author_text_paint_axes_are_forwarded(self):
        st=replace(STYLE,letter_spacing='3px',word_spacing='5px',
                   text_shadows=((2,3,1,'red'),),text_stroke_color='blue',text_stroke_width=2)
        p=texts(self.layout(spec(value='A B'),st))[0]
        self.assertEqual((p.letter_spacing,p.word_spacing),('3px','5px'))
        self.assertEqual(p.text_shadows,((2,3,1,'red'),))
        self.assertEqual((p.text_stroke_color,p.text_stroke_width),('blue',2))

    def test_l63_source_invalid_accent_declaration_uses_ua_default(self):
        # Fixed utils.encodeEntities removes the CSS hex's middle separator;
        # the source host ignores the resulting invalid accent declaration.
        default=self.layout(spec(type_='checkbox',checked=True))
        for invalid in ('#2468acmargin:0','#2468acdirection:rtl','not-a-color'):
            with self.subTest(invalid=invalid):
                c=self.layout(spec(type_='checkbox',checked=True,css='accent-color:'+invalid))
                self.assertEqual([p.fill for p in c.paints],[p.fill for p in default.paints])

    def test_l64_valid_rgb_accent_is_not_replaced_by_default(self):
        rgb='rgb(36,104,172)'
        c=self.layout(spec(type_='checkbox',checked=True,css='accent-color:'+rgb))
        self.assertIn(rgb,[p.fill for p in c.paints])

    def test_l65_absolute_modern_css_color_is_not_called_invalid(self):
        for color in ('hwb(210 10% 20%)','oklch(60% 0.1 210)','color(display-p3 0.2 0.4 0.7)'):
            with self.subTest(color=color):
                c=self.layout(spec(type_='checkbox',checked=True,css='accent-color:'+color))
                self.assertIn(color,[p.fill for p in c.paints])

    def test_l66_single_select_far_selected_item_sets_initial_visible_rows(self):
        # Fixed-source post-first-paint PNG shows Four/Five, not One/Two.
        # The earlier pre-paint DOM query had not yet applied UA scrolling.
        options=tuple(ControlOption(label) for label in ('One','Two','Three','Four','Five'))
        c=self.layout(spec('select',options=options,selected_indices=(4,),attrs={'size':'2'}))
        _,top,_,height=c.clip
        visible=[p.text for p in texts(c) if p.y-8>=top and p.y+2<=top+height]
        self.assertEqual(visible,['Four','Five'])
        self.assertEqual(c.spec.selected_indices,(4,))

    def test_l67_multiple_select_keeps_first_selected_item_in_initial_view(self):
        # Source post-paint PNG shows One/Two with Two selected; Five remains
        # selected in state but is outside the initial two-row viewport.
        options=tuple(ControlOption(label) for label in ('One','Two','Three','Four','Five'))
        c=self.layout(spec('select',multiple=True,options=options,selected_indices=(1,4),attrs={'size':'2'}))
        _,top,_,height=c.clip
        visible=[p.text for p in texts(c) if p.y-8>=top and p.y+2<=top+height]
        self.assertEqual(visible,['One','Two'])
        self.assertEqual(c.spec.selected_indices,(1,4))

    def test_l68_zero_input_size_uses_default_and_keeps_value_visible(self):
        default=self.layout(spec(value='Size'))
        zero=self.layout(spec(value='Size',attrs={'size':'0'}))
        self.assertEqual((zero.width,zero.height,zero.clip),(default.width,default.height,default.clip))
        x,y,w,h=zero.clip
        visible=[p.text for p in texts(zero)
                 if p.x>=x and p.x+len(p.text)*5<=x+w and p.y-8>=y and p.y+2<=y+h]
        self.assertEqual(visible,['Size'])

    def test_l69_zero_textarea_rows_and_cols_use_default_dimensions(self):
        default=self.layout(spec('textarea',value='One\nTwo'))
        zero=self.layout(spec('textarea',value='One\nTwo',attrs={'cols':'0','rows':'0'}))
        self.assertEqual((zero.width,zero.height,zero.clip),(default.width,default.height,default.clip))
        x,y,w,h=zero.clip
        visible=[p.text for p in texts(zero)
                 if p.x>=x and p.x+len(p.text)*5<=x+w and p.y-8>=y and p.y+2<=y+h]
        self.assertEqual(visible,['One','Two'])

    def test_l70_zero_multiple_select_size_uses_default_four_visible_rows(self):
        options=tuple(ControlOption(label) for label in ('One','Two','Three','Four'))
        default=self.layout(spec('select',multiple=True,options=options))
        zero=self.layout(spec('select',multiple=True,options=options,attrs={'size':'0'}))
        self.assertEqual((zero.width,zero.height,zero.clip),(default.width,default.height,default.clip))
        _,top,_,height=zero.clip
        visible=[p.text for p in texts(zero) if p.y-8>=top and p.y+2<=top+height]
        self.assertEqual(visible,['One','Two','Three','Four'])


class RichControlLayout(unittest.TestCase):
    def provider(self,calls):
        def build(markup,style,width):
            calls.append((markup,style,width))
            caption='legend' in markup
            label='Caption' if caption else 'Body'
            w,h=(35,12) if caption else (30,18)
            run=MeasuredTextRun(label,0,8,w,8,2,style.font_family,style.font_size,color=style.text_color)
            return w,h,(),(run,)
        return build

    def test_l51_rich_button_content_is_centered_in_inner_box(self):
        calls=[];c=layout_control(spec('button',inner_markup='<b>Body</b>',css='box-sizing:content-box;width:100px;height:50px;padding:5px;border:2px solid black'),STYLE,measure,content_layout=self.provider(calls))
        self.assertEqual(c.content_runs[0].text,'Body')
        self.assertAlmostEqual(c.content_offset[0]+15,c.width/2)
        self.assertAlmostEqual(c.content_offset[1]+9,c.height/2)
        self.assertEqual(calls[-1][2],100)

    def test_l52_rich_child_base_does_not_duplicate_parent_compositing(self):
        calls=[];style=replace(STYLE,opacity=.4,brightness=1.5,filter_chain=('brightness(1.5)',),background='yellow')
        layout_control(spec('button',inner_markup='<span>Body</span>'),style,measure,content_layout=self.provider(calls))
        for _,child,_ in calls:
            self.assertEqual(child.opacity,1);self.assertEqual(child.brightness,1)
            self.assertEqual(child.filter_chain,());self.assertEqual(child.background,'transparent')
        self.assertEqual(style.opacity,.4)

    def test_l53_fieldset_has_separate_body_and_rich_caption(self):
        calls=[];c=layout_control(spec('fieldset',inner_markup='<input value="Body">',legend_text='Caption',legend_markup='<legend><b>Caption</b></legend>'),STYLE,measure,content_layout=self.provider(calls))
        self.assertEqual(c.content_runs[0].text,'Body');self.assertEqual(c.caption_runs[0].text,'Caption')
        self.assertLess(c.caption_offset[1],c.clip[1])
        self.assertTrue(any('<input' in text for text,_,_ in calls))

    def test_l54_plain_fieldset_caption_is_not_in_clipped_body(self):
        c=layout_control(spec('fieldset',legend_text='Plain'),STYLE,measure)
        self.assertEqual(c.caption_runs[0].text,'Plain')
        self.assertEqual(c.caption_offset[1],0)
        self.assertLess(c.caption_offset[1],c.clip[1])

    def test_l55_fieldset_top_frame_has_a_real_caption_gap(self):
        c=layout_control(spec('fieldset',legend_text='Caption'),STYLE,measure)
        x=c.caption_offset[0];right=x+c.caption_runs[0].width
        top=[p for p in c.paints if p.kind=='line' and p.height==0 and p.y<c.clip[1]]
        self.assertTrue(top)
        self.assertTrue(all(p.x+p.width<=x or p.x>=right for p in top))

    def test_l56_hidden_visibility_keeps_geometry_and_restorable_children(self):
        calls=[];c=layout_control(spec('button',inner_markup='<span style="visibility:visible">Body</span>'),replace(STYLE,visibility='hidden'),measure,content_layout=self.provider(calls))
        self.assertGreater(c.width,0);self.assertEqual(c.paints,())
        self.assertTrue(c.content_runs)
        self.assertTrue(all(child.visibility=='hidden' for _,child,_ in calls))

    def test_l57_rich_markup_requires_explicit_provider(self):
        with self.assertRaises(MermaidError) as caught:
            layout_control(spec('button',inner_markup='<b>Body</b>'),STYLE,measure)
        self.assertEqual(caught.exception.code,'INVALID_HTML_CONTROL')
