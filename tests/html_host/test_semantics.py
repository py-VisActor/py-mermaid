"""Independent initial-state examples for Mermaid's sanitized HTML handoff.

Handwritten expectations follow HTML state algorithms, not candidate output.
The fixed-source and host-rule index is references/html-host-assertions.json.
No product behavior is invoked during import or unittest discovery.
"""
from html.parser import HTMLParser
import html
import unittest

from py_mermaid.model.flowchart import MermaidError
from py_mermaid.config import resolve_config
from py_mermaid.rendering.labels.sanitize import sanitize_markup
from py_mermaid.rendering.labels.controls.semantic import ControlCapture, normalize_control_markup, normalize_control_labels


# Each literal is a separately meaningful host-state example. Numeric/date
# invalidity is distinct from form constraint validation (min/max/required).
SOURCE_CASES = [
    ('type-text', "<input type='text' value='Hello'>", {'input_type':'text','value':'Hello'}),
    ('text-unicode-value', "<input value='\u4e2d\u6587 \U0001f642'>", {'value':'\u4e2d\u6587 \U0001f642'}),
    ('text-attribute-entity-once', "<input value='&amp;lt;b&amp;gt;'>", {'value':'&lt;b&gt;'}),
    ('type-search', "<input type='search' value='Find'>", {'input_type':'search','value':'Find'}),
    ('type-tel', "<input type='tel' value='+1 555'>", {'input_type':'tel','value':'+1 555'}),
    ('type-url', "<input type='url' value=' https://example.test/ '>", {'input_type':'url','value':'https://example.test/'}),
    ('type-email', "<input type='email' value=' a@example.test '>", {'input_type':'email','value':'a@example.test'}),
    ('type-password', "<input type='password' value='Secret'>", {'input_type':'password','value':'Secret'}),
    ('type-hidden', "<input type='hidden' value='Secret'>", {'input_type':'hidden','value':'Secret','hidden':True}),
    ('type-date', "<input type='date' value='2024-02-29'>", {'input_type':'date','value':'2024-02-29'}),
    ('type-month', "<input type='month' value='2024-02'>", {'input_type':'month','value':'2024-02'}),
    ('type-week', "<input type='week' value='2020-W53'>", {'input_type':'week','value':'2020-W53'}),
    ('type-time', "<input type='time' value='13:45'>", {'input_type':'time','value':'13:45'}),
    ('type-datetime-local', "<input type='datetime-local' value='2024-02-29T13:45'>", {'input_type':'datetime-local','value':'2024-02-29T13:45'}),
    ('type-number', "<input type='number' value='2.5'>", {'input_type':'number','value':'2.5'}),
    ('type-range', "<input type='range' min='0' max='10' step='2' value='7'>", {'input_type':'range','value':'8','fraction':0.8}),
    ('type-color', "<input type='color' value='#FFAA00'>", {'input_type':'color','value':'#ffaa00'}),
    ('type-checkbox', "<input type='checkbox' checked>", {'input_type':'checkbox','value':'on','checked':True}),
    ('type-radio', "<input type='radio'>", {'input_type':'radio','value':'on','checked':False}),
    ('type-file', "<input type='file' value='C:/private.txt'>", {'input_type':'file','value':''}),
    ('type-submit', "<input type='submit'>", {'input_type':'submit','value':''}),
    ('type-image', "<input type='image' alt='Image'>", {'input_type':'image','value':''}),
    ('type-reset', "<input type='reset'>", {'input_type':'reset','value':''}),
    ('type-button', "<input type='button' value='Push'>", {'input_type':'button','value':'Push'}),
    ('missing-type', "<input value='Default'>", {'input_type':'text','value':'Default'}),
    ('unknown-type', "<input type='future-kind' value='Default'>", {'input_type':'text','value':'Default'}),
    ('case-insensitive-type', "<input type='CHECKBOX' checked='false'>", {'input_type':'checkbox','checked':True}),
    ('duplicate-attribute-first-wins', "<input value='First' value='Second'>", {'value':'First'}),
    ('text-removes-newlines', "<input value='A\r\nB\nC'>", {'value':'ABC'}),
    ('tel-retains-edge-spaces', "<input type='tel' value=' 123 '>", {'value':' 123 '}),
    ('email-multiple-trims-each', "<input type='email' multiple value=' a@x.test , b@y.test '>", {'value':'a@x.test,b@y.test','multiple':True}),
    ('password-removes-newlines', "<input type='password' value='A\nB'>", {'value':'AB'}),
    ('disabled-presence-not-string', "<input disabled='false' value='X'>", {'disabled':True,'value':'X'}),
    ('readonly-text', "<input readonly value='X'>", {'readonly':True,'value':'X'}),
    ('readonly-inapplicable-checkbox', "<input type='checkbox' readonly>", {'readonly':False}),
    ('checkbox-explicit-empty-value', "<input type='checkbox' value='' checked>", {'value':'','checked':True}),
    ('submit-explicit-empty', "<input type='submit' value=''>", {'value':''}),
    ('invalid-date-nonleap', "<input type='date' value='2023-02-29'>", {'value':''}),
    ('invalid-date-year-zero', "<input type='date' value='0000-01-01'>", {'value':''}),
    ('invalid-month', "<input type='month' value='2024-13'>", {'value':''}),
    ('invalid-week-53', "<input type='week' value='2021-W53'>", {'value':''}),
    ('invalid-time-hour', "<input type='time' value='24:00'>", {'value':''}),
    ('valid-time-milliseconds', "<input type='time' value='12:30:45.125'>", {'value':'12:30:45.125'}),
    ('datetime-shortest-normalization', "<input type='datetime-local' value='2024-02-29 13:45:00.000'>", {'value':'2024-02-29T13:45'}),
    ('invalid-datetime-zone', "<input type='datetime-local' value='2024-02-29T13:45Z'>", {'value':''}),
    ('number-nan-invalid', "<input type='number' value='NaN'>", {'value':''}),
    ('number-leading-plus-invalid', "<input type='number' value='+2'>", {'value':''}),
    ('number-trailing-dot-invalid', "<input type='number' value='1.'>", {'value':''}),
    ('number-outside-range-retained', "<input type='number' min='0' max='10' value='100'>", {'value':'100'}),
    ('number-exponent-retained', "<input type='number' value='1e2'>", {'value':'1e2'}),
    ('range-default-midpoint', "<input type='range'>", {'value':'50','minimum':0.0,'maximum':100.0,'fraction':0.5}),
    ('range-invalid-value-midpoint', "<input type='range' min='10' max='20' value='bad'>", {'value':'15','fraction':0.5}),
    ('range-clamp-upper', "<input type='range' min='0' max='10' value='99'>", {'value':'10','fraction':1.0}),
    ('range-inverted-bounds', "<input type='range' min='20' max='10'>", {'value':'20','minimum':20.0,'maximum':20.0,'fraction':0.0}),
    ('range-step-any', "<input type='range' min='0' max='10' step='any' value='3.25'>", {'value':'3.25','fraction':0.325}),
    ('range-content-value-step-base', "<input type='range' step='2' value='7'>", {'value':'7'}),
    ('color-default', "<input type='color'>", {'value':'#000000'}),
    ('color-invalid', "<input type='color' value='not-a-color'>", {'value':'#000000'}),
    ('color-named-purple', "<input type='color' value='rebeccapurple'>", {'value':'#663399'}),
    ('color-short-hex-blue', "<input type='color' value='#00f'>", {'value':'#0000ff'}),
    ('color-rgb-percent-half', "<input type='color' value='rgb(0% 50% 100%)'>", {'value':'#0080ff'}),
    ('color-hsl-green', "<input type='color' value='hsl(120 100% 25%)'>", {'value':'#008000'}),
    ('color-hsl-achromatic-half', "<input type='color' value='hsl(0 0% 50%)'>", {'value':'#808080'}),
    ('color-hwb-blue', "<input type='color' value='hwb(240 0% 0%)'>", {'value':'#0000ff'}),
    ('color-hwb-neutral', "<input type='color' value='hwb(240 50% 50%)'>", {'value':'#808080'}),
    ('color-srgb-blue-green', "<input type='color' value='color(srgb 0 0.5 1)'>", {'value':'#0080ff'}),
    ('color-srgb-linear-blue', "<input type='color' value='color(srgb-linear 0 0 1)'>", {'value':'#0000ff'}),
    ('color-display-p3-green', "<input type='color' value='color(display-p3 0 1 0)'>", {'value':'#00ff00'}),
    ('color-host-p3-d50-quantization', "<input type='color' value='color(display-p3 0.2 0.4 0.6)'>", {'value':'#1a689d'}),
    ('color-host-rec2020-transfer', "<input type='color' value='color(rec2020 0.2 0.4 0.6)'>", {'value':'#0078a8'}),
    ('color-lab-neutral', "<input type='color' value='lab(50% 0 0)'>", {'value':'#777777'}),
    ('color-lch-neutral', "<input type='color' value='lch(50% 0 120)'>", {'value':'#777777'}),
    ('color-oklab-neutral', "<input type='color' value='oklab(50% 0 0)'>", {'value':'#636363'}),
    ('color-oklch-black', "<input type='color' value='oklch(0 0 240)'>", {'value':'#000000'}),
    ('button-label-versus-value', "<button value='payload'><b>Save</b></button>", {'text':'Save','value':'payload','inner_markup':'<b>Save</b>'}),
    ('button-disabled', "<button disabled>Save</button>", {'text':'Save','disabled':True}),
    ('textarea-initial-lf', '<textarea>\nFirst\nSecond</textarea>', {'value':'First\nSecond','text':'First\nSecond'}),
    ('textarea-crlf', '<textarea>\r\nFirst\rSecond</textarea>', {'value':'First\nSecond'}),
    ('textarea-rcdata-not-elements', '<textarea><b>literal</b></textarea>', {'value':'<b>literal</b>'}),
    ('textarea-entities-one-pass', '<textarea>&amp;lt;b&amp;gt;</textarea>', {'value':'&lt;b&gt;'}),
    ('textarea-value-attribute-ignored', "<textarea value='ignored'>Body</textarea>", {'value':'Body'}),
    ('textarea-readonly-disabled', '<textarea readonly disabled>Body</textarea>', {'value':'Body','readonly':True,'disabled':True}),
    ('select-default-first-enabled', '<select><option disabled>Skip</option><option>One</option></select>', {'value':'One','selected_indices':(1,)}),
    ('select-last-selected-wins', '<select><option selected>One</option><option selected>Two</option></select>', {'value':'Two','selected_indices':(1,),'options.0.selected':False}),
    ('select-explicit-disabled-selected', '<select><option disabled selected>One</option><option>Two</option></select>', {'value':'One','selected_indices':(0,),'options.0.disabled':True}),
    ('select-multiple-no-default', '<select multiple><option>One</option></select>', {'value':'','multiple':True,'selected_indices':()}),
    ('select-multiple-selected', '<select multiple><option selected>One</option><option selected>Two</option></select>', {'value':'One','selected_indices':(0,1)}),
    ('select-size-two-no-default', "<select size='2'><option>One</option><option>Two</option></select>", {'selected_indices':(),'value':''}),
    ('select-all-disabled', '<select><option disabled>One</option><option disabled>Two</option></select>', {'selected_indices':(),'value':''}),
    ('select-option-label-value', "<select><option label='Shown' value='sent'>Body</option></select>", {'value':'sent','options.0.label':'Shown','options.0.value':'sent'}),
    ('select-option-whitespace', '<select><option>  Alpha\n  Beta  </option></select>', {'value':'Alpha Beta','options.0.label':'Alpha Beta'}),
    ('select-optgroup-disables-options', "<select><optgroup label='Group' disabled><option>One</option></optgroup><option>Two</option></select>", {'value':'Two','selected_indices':(1,),'options.0.group':'Group','options.0.disabled':True}),
    ('select-option-end-omission', '<select><option>One<option selected>Two</select>', {'value':'Two','selected_indices':(1,)}),
    ('progress-indeterminate', '<progress></progress>', {'fraction':None,'maximum':1.0}),
    ('progress-fraction', "<progress max='10' value='6'></progress>", {'fraction':0.6,'value':'6'}),
    ('progress-invalid-value-determinate-zero', "<progress value='bad'></progress>", {'fraction':0.0,'value':'0'}),
    ('progress-max-invalid-default', "<progress max='0' value='2'></progress>", {'maximum':1.0,'fraction':1.0,'value':'1'}),
    ('progress-negative-value', "<progress value='-2'></progress>", {'fraction':0.0,'value':'0'}),
    ('meter-default', '<meter></meter>', {'minimum':0.0,'maximum':1.0,'fraction':0.0}),
    ('meter-nonzero-minimum', "<meter min='10' max='20' value='15'></meter>", {'minimum':10.0,'maximum':20.0,'fraction':0.5,'value':'15'}),
    ('meter-clamp-value', "<meter min='0' max='10' value='99'></meter>", {'value':'10','fraction':1.0}),
    ('meter-invalid-numbers', "<meter min='bad' max='bad' value='bad'></meter>", {'minimum':0.0,'maximum':1.0,'fraction':0.0}),
    ('meter-inverted-bounds', "<meter min='5' max='2' value='3'></meter>", {'minimum':5.0,'maximum':5.0,'value':'5','fraction':0.0}),
    ('fieldset-rich-legend', '<fieldset><legend><b>Legend</b></legend><input></fieldset>', {'legend_text':'Legend','legend_markup':'<legend><b>Legend</b></legend>','inner_markup':'<input>'}),
    ('fieldset-first-direct-legend-only', '<fieldset><div><legend>Nested</legend></div><legend>First</legend><legend>Second</legend></fieldset>', {'legend_text':'First','inner_markup':'<div><legend>Nested</legend></div><legend>Second</legend>'}),
]


class _CaptureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.capture = None
        self.rcdata = False

    def handle_starttag(self, tag, attrs):
        if self.capture is None:
            self.capture = ControlCapture(tag, attrs)
            if tag == 'textarea':
                self.rcdata = True
                self.set_cdata_mode('textarea')
        else:
            self.capture.start(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        self.capture.end(tag)

    def handle_data(self, text):
        # Python 3.13.15 has native RCDATA and has already decoded references.
        # Older HTMLParser versions use the manually selected RAWTEXT mode.
        native_rcdata = 'textarea' in getattr(HTMLParser, 'RCDATA_CONTENT_ELEMENTS', ())
        self.capture.data(html.unescape(text) if self.rcdata and not native_rcdata else text)


def capture(markup):
    parser = _CaptureParser()
    parser.feed(markup)
    parser.close()
    return parser.capture


def field_value(value, path):
    for part in path.split('.'):
        value = value[int(part)] if part.isdigit() else getattr(value, part)
    return value


class InitialControlStateSourceTests(unittest.TestCase):
    pass


def _install_source_cases():
    for id, markup, expected in SOURCE_CASES:
        def method(self, markup=markup, expected=expected):
            cap = capture(markup)
            self.assertTrue(cap.finished)
            spec = cap.build()
            for path, wanted in expected.items():
                with self.subTest(field=path):
                    actual = field_value(spec, path)
                    if isinstance(wanted, float):
                        self.assertAlmostEqual(actual, wanted, places=9)
                    else:
                        self.assertEqual(actual, wanted)
        method.__name__ = 'test_' + id.replace('-', '_')
        method.__doc__ = 'HTML initial state: ' + id
        setattr(InitialControlStateSourceTests, method.__name__, method)


_install_source_cases()


class _Inputs(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.inputs = {}
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            attrs = dict(attrs)
            self.inputs[attrs.get('id', '')] = attrs


class CrossControlHostSourceTests(unittest.TestCase):
    def inputs(self, markup):
        return _Inputs(normalize_control_markup(markup)).inputs

    def test_radio_last_checked_tree_order_wins(self):
        rows = self.inputs("<input id='a' type='radio' name='g' checked><input id='b' type='radio' name='g' checked>")
        self.assertNotIn('checked', rows['a']); self.assertIn('checked', rows['b'])

    def test_radio_disabled_still_participates(self):
        rows = self.inputs("<input id='a' type='radio' name='g' checked><input id='b' type='radio' name='g' checked disabled>")
        self.assertNotIn('checked', rows['a']); self.assertIn('checked', rows['b'])

    def test_radio_names_case_sensitive_and_empty_names_ungrouped(self):
        rows = self.inputs("<input id='a' type='radio' name='G' checked><input id='b' type='radio' name='g' checked><input id='c' type='radio' checked><input id='d' type='radio' checked>")
        self.assertTrue(all('checked' in row for row in rows.values()))

    def test_radio_distinct_form_owners(self):
        rows = self.inputs("<form id='f'><input id='a' type='radio' name='g' checked></form><form id='h'><input id='b' type='radio' name='g' checked></form>")
        self.assertIn('checked', rows['a']); self.assertIn('checked', rows['b'])

    def test_radio_explicit_form_owner_with_custom_allowed_attr(self):
        rows = self.inputs("<form id='f'><input id='a' type='radio' name='g' checked></form><input id='b' type='radio' form='f' name='g' checked>")
        self.assertNotIn('checked', rows['a']); self.assertIn('checked', rows['b'])

    def test_cross_label_radio_last_checked_and_call_isolation(self):
        labels = ("<input id='a' type='radio' name='g' checked>", "<input id='b' type='radio' name='g' checked>")
        first, second = normalize_control_labels(labels)
        self.assertNotIn('checked', _Inputs(first).inputs['a'])
        self.assertIn('checked', _Inputs(second).inputs['b'])
        self.assertEqual(normalize_control_labels((labels[0],)), (labels[0],))

    def test_cross_label_distinct_form_owners_remain_independent(self):
        labels = ("<form id='f'><input id='a' type='radio' name='g' checked></form>",
                  "<form id='h'><input id='b' type='radio' name='g' checked></form>")
        self.assertEqual(normalize_control_labels(labels), labels)

    def test_cross_label_explicit_form_owner_resolves_forward_id(self):
        first, second = normalize_control_labels(("<input id='a' type='radio' form='f' name='g' checked>",
                                                  "<form id='f'><input id='b' type='radio' name='g' checked></form>"))
        self.assertNotIn('checked', _Inputs(first).inputs['a'])
        self.assertIn('checked', _Inputs(second).inputs['b'])

    def test_cross_label_unnamed_radios_stay_checked_without_markup_leak(self):
        labels = ("<input id='a' type='radio' checked>", "<input id='b' type='radio' name='' checked>", '<span>Unchanged</span>')
        self.assertEqual(normalize_control_labels(labels), labels)

    def test_fieldset_first_legend_exception_and_later_legend_disabled(self):
        rows = self.inputs("<fieldset disabled><legend><input id='a'></legend><input id='b'><legend><input id='c'></legend></fieldset>")
        self.assertNotIn('disabled', rows['a']); self.assertIn('disabled', rows['b']); self.assertIn('disabled', rows['c'])

    def test_nested_fieldset_outer_disabled_still_applies(self):
        rows = self.inputs("<fieldset disabled><div><fieldset><legend><input id='a'></legend></fieldset></div></fieldset>")
        self.assertIn('disabled', rows['a'])

    def test_nested_fieldset_itself_has_effective_disabled_state(self):
        normalized = normalize_control_markup("<fieldset disabled><fieldset id='inner'><legend><input id='a'></legend></fieldset></fieldset>")
        self.assertIn('disabled', capture(normalized).build().inner_markup.split('>')[0])

    def test_fieldset_legend_exception_does_not_remove_own_disabled(self):
        rows = self.inputs("<fieldset disabled><legend><input id='a' disabled></legend></fieldset>")
        self.assertIn('disabled', rows['a'])

    def test_no_control_markup_is_byte_preserved(self):
        markup = "<span class='x'>&amp;Text</span>"
        self.assertEqual(normalize_control_markup(markup), markup)

    def test_normalization_without_cross_state_change_preserves_markup(self):
        markup = "<input type='text' value='&amp;'>"
        self.assertEqual(normalize_control_markup(markup), markup)

    def test_normalization_is_request_local(self):
        self.inputs("<input id='a' type='radio' name='g' checked><input id='b' type='radio' name='g' checked>")
        self.assertIn('checked', self.inputs("<input id='a' type='radio' name='g' checked>")['a'])

    def test_textarea_literals_do_not_join_radio_groups(self):
        markup = "<textarea><input type='radio' name='g' checked></textarea><input id='a' type='radio' name='g' checked>"
        self.assertEqual(normalize_control_markup(markup), markup)

    def test_inherited_disabled_capture_flag(self):
        self.assertTrue(ControlCapture('input', [], inherited_disabled=True).build().disabled)

    def test_input_void_root_finished_immediately(self):
        self.assertTrue(ControlCapture('input', []).finished)

    def test_unknown_control_explicit_error(self):
        with self.assertRaises(MermaidError) as caught:
            ControlCapture('video', [])
        self.assertEqual(caught.exception.code, 'INVALID_HTML_CONTROL')

    def test_css_color_validity_distinguishes_black_from_invalid(self):
        from py_mermaid.rendering.labels.controls.color_values import is_valid_css_color
        self.assertTrue(is_valid_css_color('black'))
        self.assertTrue(is_valid_css_color('color(display-p3 0.2 0.4 0.6)'))
        self.assertFalse(is_valid_css_color('not-a-color'))
        self.assertFalse(is_valid_css_color('rgb(1,,2,3)'))

    def test_control_capture_budget_explicit(self):
        cap = ControlCapture('button', [])
        with self.assertRaises(MermaidError) as caught:
            for _ in range(20_001):
                cap.data('x')
        self.assertEqual(caught.exception.code, 'LABEL_BUDGET')


class SanitizedControlAttributeSourceTests(unittest.TestCase):
    def sanitize(self, markup, config=None):
        return sanitize_markup(markup, resolve_config({'securityLevel':'loose', **(config or {})}))

    def test_fixed_boolean_and_dimension_attributes_survive(self):
        markup = self.sanitize("<input checked disabled readonly multiple size='4' maxlength='7' placeholder='Hint'><textarea rows='2' cols='8'></textarea>")
        for name in ('checked', 'disabled', 'readonly', 'multiple', 'size', 'maxlength', 'placeholder', 'rows', 'cols'):
            self.assertIn(' '+name+'=', markup)

    def test_fixed_option_range_and_gauge_attributes_survive(self):
        markup = self.sanitize("<select><optgroup label='Group'><option selected label='One' value='one'>One</option></optgroup></select><meter min='0' max='10' low='2' high='8' optimum='5' value='6'></meter><input type='range' step='0.5'>")
        for name in ('selected', 'label', 'value', 'min', 'max', 'low', 'high', 'optimum', 'step'):
            self.assertIn(' '+name+'=', markup)

    def test_event_handlers_and_javascript_image_are_removed(self):
        markup = self.sanitize("<input type='image' src='javascript:alert(1)' onerror='alert(2)' onclick='alert(3)'>")
        self.assertNotIn('javascript:', markup); self.assertNotIn('onerror', markup); self.assertNotIn('onclick', markup)

    def test_custom_forbid_attribute_wins_over_default_allowlist(self):
        markup = self.sanitize('<input checked disabled>', {'dompurifyConfig':{'FORBID_ATTR':['checked']}})
        self.assertNotIn('checked', markup); self.assertIn('disabled', markup)

    def test_custom_forbid_tag_retains_button_content(self):
        markup = self.sanitize('<button>Save</button>', {'dompurifyConfig':{'FORBID_TAGS':['button']}})
        self.assertNotIn('<button', markup); self.assertIn('Save', markup)

    def test_form_association_attribute_not_default_allowed(self):
        self.assertNotIn(' form=', self.sanitize("<input form='f'>"))
        self.assertIn(' form=', self.sanitize("<input form='f'>", {'dompurifyConfig':{'ADD_ATTR':['form']}}))
