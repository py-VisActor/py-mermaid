"""F01.3 independent source assertions; no expected data comes from the candidate.

Pinned source groups and SHA identities are in f013-language-assertions.json.
Fixtures use canonical HTML entity transport, without decoding escaped markup.
"""
from __future__ import annotations
import copy
from dataclasses import FrozenInstanceError
import json
import math
from pathlib import Path
import unittest

from py_mermaid.config import resolve_config
from py_mermaid.config.colors import channels
from py_mermaid.config.themes import get_theme_variables
from py_mermaid.config.values import thaw_value, assign_with_depth, merge_layers
from py_mermaid.model.flowchart import MermaidError
from py_mermaid.parsing import parse_flowchart, preprocess_diagram
from py_mermaid.parsing.yaml_json import load_yaml_json

FIXTURES = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf8"))
BASE = "flowchart TD\nA[Alpha] --> B[Beta]"


class RichFixtureLanguageTests(unittest.TestCase):
    def test_handwritten_semantic_cases(self):
        for case in FIXTURES["cases"]:
            with self.subTest(case=case["id"]):
                diagram = parse_flowchart(case["text"], config=copy.deepcopy(case.get("config")))
                self.assertEqual([[n.id, n.label] for n in diagram.nodes], case["nodes"])
                self.assertEqual([[e.source, e.target] for e in diagram.edges], case["edges"])
                self.assertEqual(diagram.direction, case["direction"])
                self.assertEqual([e.label for e in diagram.edges], case.get("edgeLabels", [""] * len(case["edges"])))
                self.assertEqual([n.shape for n in diagram.nodes], [case.get("shapes", {}).get(n.id, "square") for n in diagram.nodes])
                self.assertEqual([dict(id=g.id, label=g.label, members=list(g.members), parent_id=g.parent_id, direction=g.direction) for g in diagram.groups], case.get("groups", []))
                self.assertEqual(diagram.title, case.get("diagramTitle", ""))
                self.assertEqual(diagram.acc_title, case.get("accTitle", ""))
                self.assertEqual(diagram.acc_description, case.get("accDescription", ""))
                for n in diagram.nodes:
                    self.assertEqual(n.label_kind, case.get("labelKinds", {}).get(n.id, "text"))
                self.assertEqual([e.label_kind for e in diagram.edges], case.get("edgeLabelKinds", ["text"] * len(diagram.edges)))
                for g in diagram.groups:
                    self.assertEqual(g.label_kind, case.get("groupLabelKinds", {}).get(g.id, "text"))
                for key, value in case.get("expectedConfig", {}).items():
                    self.assertEqual(getattr(diagram.config, key), value, key)

    def test_fixture_denominator_and_theme_registry(self):
        self.assertEqual(len(FIXTURES["cases"]), 50)
        self.assertEqual({c["id"][6:] for c in FIXTURES["cases"] if c["id"].startswith("theme-") and c["id"] not in ("theme-css-native-paint", "theme-vars-native-paint")},
                         {"base", "dark", "default", "forest", "neutral", "neo", "neo-dark", "redux", "redux-dark", "redux-color", "redux-dark-color", "null"})
        self.assertEqual(len(FIXTURES["negativeCases"]), 8)
        self.assertEqual(len(FIXTURES["unsupportedCases"]), 2)
        self.assertEqual(len({c["id"] for c in FIXTURES["cases"]}), 50)

    def test_official_parse_invalid_cases(self):
        for case in FIXTURES["negativeCases"]:
            with self.subTest(case=case["id"]):
                with self.assertRaises(MermaidError):
                    parse_flowchart(case["text"])

    def test_f014_promotions_and_remaining_explicit_exclusions(self):
        # Historical fixture JSON is coordinated separately. Reclassify using
        # explicit source semantics; none of these are skips or silent deletion.
        for case in FIXTURES['unsupportedCases']:
            if case['id']=='math':
                self.assertEqual(parse_flowchart(case['text']).nodes[0].label,'$$x^2$$')
            elif case['id']=='dagre-layout':
                with self.subTest(case=case['id']):
                    with self.assertRaises(MermaidError) as caught: parse_flowchart(case['text'],config=case.get('config'))
                    self.assertIn(caught.exception.code,case['codes'])
        self.assertEqual(parse_flowchart('flowchart TD\nA["fa:fa-home"]').nodes[0].label,'fa:fa-home')
        self.assertEqual(parse_flowchart('flowchart TD\nA@{ shape: hourglass }').nodes[0].shape,'hourglass')
        self.assertEqual(parse_flowchart('flowchart TD\nA;style A fill:red').nodes[0].styles,('fill:red',))
        self.assertEqual(resolve_config({'look':'handDrawn'}).look,'handDrawn')

    def test_raw_label_preserves_markup_entities_and_markdown_body(self):
        pairs = [('A["<b>Safe</b>"]', "text", "<b>Safe</b>"),
                 ('A["#quot;Hi#quot;"]', "text", "#quot;Hi#quot;"),
                 ('A["`**Bold**`"]', "markdown", "**Bold**")]
        for syntax, kind, raw in pairs:
            with self.subTest(syntax=syntax):
                n = parse_flowchart("flowchart TD\n" + syntax).nodes[0]
                self.assertEqual((n.raw_label, n.label_kind), (raw, kind))

    def test_unclosed_markdown_in_node_edge_and_group_is_parse_error(self):
        for source in ['flowchart TD\nA["`Missing close"]',
                       'flowchart TD\nA -->|"`Missing close"| B',
                       'flowchart TD\nsubgraph G["`Missing close"]\nA\nend']:
            with self.subTest(source=source):
                with self.assertRaises(MermaidError) as caught:
                    parse_flowchart(source)
                self.assertEqual(caught.exception.code, 'INVALID_SYNTAX')

    def test_rich_labels_do_not_leak_across_redeclaration_or_requests(self):
        d = parse_flowchart('flowchart TD\nA["`**First**`"]\nA[Plain]\nA --> B')
        self.assertEqual((d.nodes[0].label, d.nodes[0].label_kind), ("Plain", "text"))
        self.assertEqual(parse_flowchart('flowchart TD\nA').nodes[0].label_kind, "text")


class YamlJsonSchemaTests(unittest.TestCase):
    def test_null_and_boolean_three_case_forms(self):
        for source, expected in [("null", None), ("Null", None), ("NULL", None), ("~", None),
                                 ("true", True), ("True", True), ("TRUE", True),
                                 ("false", False), ("False", False), ("FALSE", False)]:
            with self.subTest(source=source): self.assertIs(load_yaml_json(source), expected)

    def test_non_json_booleans_timestamps_and_underscores_stay_strings(self):
        # Pinned js-yaml 4.3.0 integer/float regexes reject underscores.
        for text in ["yes", "no", "on", "off", "2026-11-05", "1_000", "0xF_F", "1_0.5", "trUE"]:
            with self.subTest(text=text): self.assertEqual(load_yaml_json(text), text)

    def test_json_schema_numeric_bases_signs_and_float_forms(self):
        for source, expected in [("0", 0), ("001", 1), ("+12", 12), ("-12", -12),
                                 ("0b101", 5), ("0o17", 15), ("0xFF", 255),
                                 ("1.25", 1.25), ("2e3", 2000), (".25", .25), ("1.", 1)]:
            with self.subTest(source=source): self.assertEqual(load_yaml_json(source), expected)
        self.assertEqual(load_yaml_json("-.Inf"), -math.inf)
        self.assertTrue(math.isnan(load_yaml_json(".NaN")))

    def test_pinned_numeric_case_and_float_grammar_boundaries(self):
        for text in ['0XFF', '0O17', '0B101', '.iNf', '.nAn', '-.25', '+.25', '1e999', '0x' + 'F' * 300]:
            with self.subTest(text=text):
                self.assertEqual(load_yaml_json(text), text)
        for text, expected in [('-0b101', -5), ('+0o17', 15), ('-0xFF', -255), ('.25e2', 25), ('.INF', math.inf)]:
            with self.subTest(text=text):
                self.assertEqual(load_yaml_json(text), expected)

    def test_yaml_integers_use_js_number_rounding(self):
        self.assertEqual(load_yaml_json('9007199254740993'), 9007199254740992)
        self.assertEqual(load_yaml_json('0x20000000000001'), 9007199254740992)
        self.assertEqual(load_yaml_json('-9007199254740993'), -9007199254740992)

    def test_quoted_strings_and_escapes(self):
        self.assertEqual(load_yaml_json("'it''s YAML'"), "it's YAML")
        self.assertEqual(load_yaml_json(r'"Line\nTab\t\u4e2d\U0001F600"'), "Line\nTab\t中😀")
        self.assertEqual(load_yaml_json(r'"\x41\N\_\L\P"'), "A\x85\xa0\u2028\u2029")
        self.assertEqual(load_yaml_json('"true"'), "true")

    def test_flow_and_block_collections(self):
        self.assertEqual(load_yaml_json("{a: [1, true, null], b: {c: two}}"), {"a": [1, True, None], "b": {"c": "two"}})
        self.assertEqual(load_yaml_json("items:\n  - name: one\n    value: 1\n  - name: two\n    value: 2"), {"items": [{"name": "one", "value": 1}, {"name": "two", "value": 2}]})
        self.assertEqual(load_yaml_json("a:\n b:\n  - x\n  - y"), {"a": {"b": ["x", "y"]}})

    def test_comments_and_plain_string_hash(self):
        self.assertEqual(load_yaml_json("a: issue#1\nb: value # comment\nc: '# literal'"), {"a": "issue#1", "b": "value", "c": "# literal"})

    def test_block_literal_chomp_and_fold(self):
        for header, expected in [("|", "one\ntwo\n"), ("|-", "one\ntwo"), (">", "one two\n"), (">-", "one two")]:
            with self.subTest(header=header): self.assertEqual(load_yaml_json("value: " + header + "\n  one\n  two\n"), {"value": expected})
        self.assertEqual(load_yaml_json("value: |+\n  one\n\n"), {"value": "one\n\n"})
        self.assertEqual(load_yaml_json("value: |2-\n  one\n  two"), {"value": "one\ntwo"})

    def test_keep_chomp_counts_real_trailing_linebreaks(self):
        for ending, expected in [('', 'one\n'), ('\n', 'one\n'), ('\n\n', 'one\n\n'), ('\n\n\n', 'one\n\n\n')]:
            with self.subTest(ending=repr(ending)):
                self.assertEqual(load_yaml_json('value: |+\n  one' + ending), {'value': expected})

    def test_multiline_plain_and_quoted_folding(self):
        self.assertEqual(load_yaml_json("value: first\n  second"), {"value": "first second"})
        self.assertEqual(load_yaml_json('value: "first\n  second"'), {"value": "first second"})
        self.assertEqual(load_yaml_json("value: 'first\n  second'"), {"value": "first second"})

    def test_aliases_and_json_schema_merge_key(self):
        self.assertEqual(load_yaml_json("a: &item {x: 1}\nb: *item"), {"a": {"x": 1}, "b": {"x": 1}})
        self.assertEqual(load_yaml_json("a: &items [1, 2]\nb: *items"), {"a": [1, 2], "b": [1, 2]})
        # JSON_SCHEMA has no merge type; << is an ordinary mapping key.
        self.assertEqual(load_yaml_json("a: &item {x: 1}\nb: {<<: *item, y: 2}"), {"a": {"x": 1}, "b": {"<<": {"x": 1}, "y": 2}})

    def test_explicit_json_tags(self):
        for text, expected in [("!!str 001", "001"), ("!!int 0x10", 16), ("!!bool TRUE", True),
                               ("!!float 2", 2.0), ("!!null null", None), ("!!seq [1, 2]", [1, 2]),
                               ("!!map {a: 1}", {"a": 1})]:
            with self.subTest(text=text): self.assertEqual(load_yaml_json(text), expected)

    def test_explicit_and_coerced_mapping_keys(self):
        self.assertEqual(load_yaml_json("? name\n: value\ntrue: yes\n12: number"), {"name": "value", "true": "yes", "12": "number"})

    def test_yaml_invalid_structures_and_unknown_tags(self):
        for source in ["a: 1\na: 2", "{a: [1, 2}", "a: *missing", "!!python/object x", "a: \"bad\\q\"", "a:\n\tb: 1", "a: value: nested"]:
            with self.subTest(source=source):
                with self.assertRaises(MermaidError): load_yaml_json(source)


class PreprocessPositionTests(unittest.TestCase):
    def test_frontmatter_empty_scalar_array_and_unknown_metadata(self):
        for body in ["", "1", "null", "[1, 2]", "unknown: ignored"]:
            with self.subTest(body=body):
                d = parse_flowchart("---\n" + body + "\n---\n" + BASE)
                self.assertEqual(d.title, "")
                self.assertEqual([n.label for n in d.nodes], ["Alpha", "Beta"])

    def test_frontmatter_false_zero_and_array_title_js_coercion(self):
        for yaml, expected in [("false", ""), ("0", ""), ("[]", ""), ("[one, two]", "one,two"), ("{}", "[object Object]")]:
            with self.subTest(yaml=yaml):
                self.assertEqual(preprocess_diagram("---\ntitle: " + yaml + "\n---\n" + BASE).title, expected)

    def test_frontmatter_only_at_start_and_exact_indent(self):
        for source in [BASE + "\n---\ntitle: late\n---", "---\ntitle: bad\n  ---\n" + BASE, "---\ntitle: open\n" + BASE]:
            with self.subTest(source=source): self.assertEqual(preprocess_diagram(source).title, "")

    def test_cleanup_stages_and_html_attribute_quotes(self):
        source = '---\r\ntitle: Title\r\n---\r\n%%{init: {"theme":"dark"}}%%\r\n%% keep comment\r\nflowchart TD\r\nA["<b title="hint">Text</b>"]'
        doc = preprocess_diagram(source)
        self.assertEqual(doc.raw, source)
        self.assertNotIn("\r", doc.normalized)
        self.assertIn("<b title='hint'>", doc.normalized)
        self.assertIn("%% keep comment", doc.with_comments)
        self.assertNotIn("%%{init", doc.with_comments)
        self.assertEqual(doc.cleaned, 'flowchart TD\nA["<b title=\'hint\'>Text</b>"]')
        self.assertEqual(doc.frontmatter_line_offset, 3)

    def test_processed_boundary_map_is_monotonic_and_original(self):
        source = '  ---\r\n  title: 😀 Heading\r\n  ---\r\n%% note\r\nflowchart TD\r\nA["😀 Label"] --> B'
        doc = preprocess_diagram(source)
        mapping = doc.processed_to_raw
        self.assertEqual(len(mapping), len(doc.cleaned) + 1)
        self.assertEqual(list(mapping), sorted(mapping))
        self.assertEqual(mapping[doc.cleaned.index('A[')], source.index('A['))
        self.assertEqual(mapping[doc.cleaned.index('😀')], source.index('😀 Label'))
        self.assertEqual(mapping[-1], len(source))

    def test_node_edge_group_label_spans_reference_original_utf16(self):
        source = '---\r\ntitle: Title 😀\r\n---\r\n%%{init: {"theme":"forest"}}%%\r\n%% comment\r\nflowchart TD\r\nsubgraph G["`**Group 😀**`"]\r\nA["<b>Node 😀</b>"] -->|"`*Edge 😀*`"| B\r\nend'
        d = parse_flowchart(source)
        for span, text in [(d.nodes[0].label_span, '<b>Node 😀</b>'), (d.edges[0].label_span, '*Edge 😀*'), (d.groups[0].label_span, '**Group 😀**')]:
            with self.subTest(text=text):
                self.assertIsNotNone(span)
                self.assertEqual(source[span.start.index:span.end.index], text)
                self.assertEqual(span.start.utf16_offset, len(source[:span.start.index].encode('utf-16-le')) // 2)
                self.assertEqual(span.end.utf16_offset, len(source[:span.end.index].encode('utf-16-le')) // 2)
                self.assertEqual(span.start.line, source[:span.start.index].count('\n') + 1)
        self.assertEqual(d.source, source)
        self.assertEqual(d.source_document.raw, source)

    def test_markdown_node_span_excludes_quote_and_tick_delimiters(self):
        source = '---\r\ntitle: Header\r\n---\r\nflowchart TD\r\nA["`**\U0001f600 Node**`"]'
        node = parse_flowchart(source).nodes[0]
        self.assertEqual(node.raw_label, '**\U0001f600 Node**')
        span = node.label_span
        self.assertEqual(source[span.start.index:span.end.index], node.raw_label)
        self.assertEqual(span.end.utf16_offset - span.start.utf16_offset, 11)

    def test_parse_error_after_frontmatter_comments_crlf_and_unicode(self):
        source = '---\r\ntitle: 😀\r\n---\r\n%% comment\r\nflowchart TD\r\nA["😀"] -->'
        with self.assertRaises(MermaidError) as caught: parse_flowchart(source)
        span = caught.exception.span
        self.assertIsNotNone(span)
        self.assertEqual(span.start.index, len(source))
        self.assertEqual(span.start.utf16_offset, len(source.encode('utf-16-le')) // 2)
        self.assertEqual(span.start.line, 6)

    def test_yaml_error_span_is_in_original_frontmatter(self):
        source = '  ---\r\n  title: 😀\r\n  config: {theme: dark\r\n  ---\r\nflowchart TD\r\nA'
        with self.assertRaises(MermaidError) as caught: parse_flowchart(source)
        self.assertEqual(caught.exception.code, "INVALID_YAML")
        span = caught.exception.span
        self.assertIsNotNone(span)
        self.assertLess(span.start.index, source.index('flowchart'))
        self.assertEqual(span.start.utf16_offset, len(source[:span.start.index].encode('utf-16-le')) // 2)

    def test_empty_comment_marker_is_not_removed_by_cleanup_regex(self):
        self.assertEqual(preprocess_diagram('%%\n' + BASE).cleaned, '%%\n' + BASE)
        self.assertEqual(preprocess_diagram('%% heading\n' + BASE).cleaned, BASE)

    def test_wrap_nowrap_directives_preserve_source_precedence(self):
        for prefix, expected in [('%%{wrap}%%', True), ('%%{nowrap}%%', None), ('%%{nowrap}%%\n%%{wrap}%%', True)]:
            with self.subTest(prefix=prefix):
                doc = preprocess_diagram(prefix + '\n' + BASE)
                layers = dict(doc.config_layers)
                directive = thaw_value(layers.get('directive', ()))
                self.assertEqual(directive.get('wrap'), expected)
                self.assertEqual(doc.cleaned, BASE)

    def test_malformed_init_is_removed_without_poisoning_next_request(self):
        bad = preprocess_diagram('%%{init: {not json}}%%\n' + BASE)
        good = parse_flowchart(BASE)
        self.assertEqual(bad.cleaned, BASE)
        self.assertEqual(good.config.theme, 'redux-color')


class ConfigurationLayerSourceTests(unittest.TestCase):
    def test_null_and_array_flowchart_sections_follow_merge_before_validation(self):
        for value in (None, []):
            with self.subTest(value=value):
                self.assertEqual(resolve_config({'flowchart': value}).wrapping_width, 120)
        value = [{'wrappingWidth': 140}, {'titleTopMargin': 35}]
        original = copy.deepcopy(value)
        config = resolve_config({'flowchart': value})
        self.assertEqual((config.wrapping_width, config.title_top_margin), (140, 35))
        self.assertEqual(value, original)

    def test_neo_shadow_keeps_source_string_and_parses_declaration_semicolon(self):
        config = resolve_config({'theme': 'neo'})
        self.assertEqual(dict(config.theme_variables)['dropShadow'],
                         'drop-shadow( 0px 1px 2px rgba(0, 0, 0, 0.25));')
        self.assertEqual((config.shadow_offset_x, config.shadow_offset_y, config.shadow_opacity), (0, 1, .25))

    def test_config_layer_order_and_original_values_are_frozen(self):
        cfg = {'fontSize': 22, 'flowchart': {'wrappingWidth': 140}}
        snapshot = copy.deepcopy(cfg)
        source = '---\nconfig: {theme: forest}\n---\n%%{init: {"flowchart":{"wrappingWidth":180}}}%%\n' + BASE
        diagram = parse_flowchart(source, config=cfg)
        self.assertEqual([name for name, _ in diagram.config.config_layers], ['default', 'site', 'frontmatter', 'directive'])
        self.assertEqual(dict(diagram.config.config_layers)['site'], diagram.source_document.config_layers[1][1])
        self.assertEqual(thaw_value(dict(diagram.config.config_layers)['site']), snapshot)
        cfg['flowchart']['wrappingWidth'] = 999
        self.assertEqual(diagram.config.wrapping_width, 180)
        with self.assertRaises(FrozenInstanceError): diagram.config.font_size = 1

    def test_theme_precedence_scoped_over_top_within_each_layer(self):
        source = '---\nconfig:\n  theme: dark\n  flowchart: {theme: forest}\n---\n' + BASE
        self.assertEqual(parse_flowchart(source, config={'theme':'neutral'}).config.theme, 'forest')
        self.assertEqual(resolve_config({'theme':'dark','flowchart':{'theme':'neutral'}}).theme, 'neutral')

    def test_null_theme_keeps_site_variables_and_default_look(self):
        d = parse_flowchart('%%{init: {"theme":"null"}}%%\n' + BASE, config={'theme':'dark'})
        self.assertEqual(d.config.theme, 'null')
        self.assertEqual(d.config.fill, '#1f2020')
        self.assertEqual(d.config.look, 'neo')

    def test_root_font_family_bridges_but_root_size_is_site_only(self):
        cfg = resolve_config({'fontFamily':'Arial','fontSize':28})
        self.assertEqual((cfg.font_family,cfg.font_size,cfg.site_font_size), ('Arial',14,28))
        explicit = resolve_config({'fontFamily':'Arial','themeVariables':{'fontFamily':'Verdana','fontSize':'20px'}})
        self.assertEqual((explicit.font_family,explicit.font_size), ('Verdana',20))

    def test_theme_variables_font_size_css_units(self):
        for css, pixels in [('12pt',16),('1pc',16),('0.5in',48),('2.54cm',96),('25.4mm',96),('101.6q',96),('1.5em',24),('2rem',32),('125%',20)]:
            with self.subTest(css=css): self.assertAlmostEqual(resolve_config({'themeVariables':{'fontSize':css}}).font_size,pixels)

    def test_root_and_diagram_html_evaluate_truth_table(self):
        for value, expected in [(False,False),('false',False),(' NULL ',False),('0',False),(0,False),(True,True),('true',True),('',True)]:
            with self.subTest(value=value): self.assertIs(resolve_config({'htmlLabels':value}).html_labels,expected)
        self.assertIs(resolve_config({'htmlLabels':None,'flowchart':{'htmlLabels':False}}).html_labels,False)
        self.assertIs(resolve_config({'htmlLabels':True,'flowchart':{'htmlLabels':False}}).html_labels,True)

    def test_markdown_auto_wrap_only_boolean_false_disables(self):
        for value, expected in [(False,False),('false',True),(0,True),(None,True),('',True),(True,True)]:
            with self.subTest(value=value): self.assertIs(resolve_config({'markdownAutoWrap':value}).markdown_auto_wrap,expected)

    def test_secure_keys_protected_recursively(self):
        source = '%%{init: {"maxEdges":1,"maxTextSize":1,"securityLevel":"loose","secure":[],"flowchart":{"maxEdges":1}}}%%\n' + BASE
        d = parse_flowchart(source,config={'maxEdges':3,'maxTextSize':2000})
        self.assertEqual((d.config.max_edges,d.config.max_text_size,d.config.security_level),(3,2000,'strict'))
        directive = thaw_value(dict(d.config.config_layers)['directive'])
        self.assertEqual(directive['securityLevel'], 'loose') # provenance is raw, effective is protected

    def test_user_secure_extension_protects_theme(self):
        cfg = parse_flowchart('%%{init: {"theme":"dark"}}%%\n' + BASE,config={'secure':['theme']}).config
        self.assertEqual(cfg.theme,'redux-color')

    def test_prototype_schema_metadata_unknown_and_null_directive_keys_are_removed(self):
        source = '%%{init: {"properties":1,"tsType":1,"FlowchartDiagramConfig":1,"unknown":3,"__proto__":{},"constructor":{},"theme":null}}%%\n' + BASE
        self.assertEqual(parse_flowchart(source).config.theme,'redux-color')

    def test_in_document_dompurify_is_not_a_known_default_config_key(self):
        source = '%%{init: {"dompurifyConfig":{"ALLOWED_TAGS":[]}}}%%\nflowchart TD\nA["<b>Bold</b>"]'
        d = parse_flowchart(source)
        self.assertEqual(d.nodes[0].label,'<b>Bold</b>')
        self.assertFalse(d.config.dompurify_provided)

    def test_dompurify_missing_empty_and_null_are_distinct(self):
        self.assertFalse(resolve_config().dompurify_provided)
        self.assertTrue(resolve_config({'dompurifyConfig':{}}).dompurify_provided)
        self.assertFalse(resolve_config({'dompurifyConfig':None}).dompurify_provided)

    def test_in_document_css_balance_and_unsafe_strings(self):
        for css, expected in [('.node { fill: red; }','.node { fill: red; }'),('.node {','{ /* ERROR: Unbalanced CSS */ }'),('} {','{ /* ERROR: Unbalanced CSS */ }')]:
            with self.subTest(css=css):
                text='%%{init: '+json.dumps({'themeCSS':css})+'}%%\n'+BASE
                self.assertEqual(parse_flowchart(text).config.theme_css,expected)
        unsafe='%%{init: {"themeCSS":"x {background:url(data:image/svg+xml,foo)}"}}%%\n'+BASE
        self.assertEqual(parse_flowchart(unsafe).config.theme_css,'')

    def test_theme_variable_directive_value_filter_is_source_restrictive(self):
        d=parse_flowchart('%%{init: {"themeVariables":{"fontFamily":"my-font","mainBkg":"#ffeedd"}}}%%\n'+BASE)
        self.assertNotEqual(d.config.font_family,'my-font')
        self.assertEqual(d.config.fill,'#ffeedd')

    def test_request_state_isolation_after_yaml_and_config_failure(self):
        supplied={'theme':'forest','themeVariables':{'mainBkg':'#ffeedd'}}
        original=copy.deepcopy(supplied)
        first=parse_flowchart(BASE,config=supplied)
        for source in ['---\n!!!\n---\n'+BASE, 'flowchart TD\nA["Unclosed]']:
            with self.assertRaises(MermaidError): parse_flowchart(source)
        second=parse_flowchart(BASE)
        self.assertEqual(supplied,original)
        self.assertEqual(first.config.fill,'#ffeedd')
        self.assertEqual((second.config.theme,second.config.fill),('redux-color','#ffffff'))

    def test_cleaned_text_budget_counts_utf16_at_boundary(self):
        cleaned='flowchart TD\nA["😀"]'
        source='---\ntitle: Long title before graph\n---\n%% comments removed\n'+cleaned
        units=len(cleaned.encode('utf-16-le'))//2
        self.assertEqual(parse_flowchart(source,config={'maxTextSize':units}).nodes[0].label,'😀')
        with self.assertRaises(MermaidError) as caught: parse_flowchart(source,config={'maxTextSize':units-1})
        self.assertEqual(caught.exception.code,'MAX_TEXT_SIZE_EXCEEDED')

    def test_secure_edge_budget_boundary_and_no_truncation(self):
        self.assertEqual(len(parse_flowchart(BASE,config={'maxEdges':1}).edges),1)
        with self.assertRaises(MermaidError) as caught: parse_flowchart(BASE+'\nB --> C',config={'maxEdges':1})
        self.assertEqual(caught.exception.code,'MAX_EDGES_EXCEEDED')


class PureMergeSourceTests(unittest.TestCase):
    def test_depth_two_and_null_skip_follow_assign_with_depth(self):
        destination = {'a': {'b': {'x': 1, 'keep': 2}}, 'n': 3}
        result = assign_with_depth(copy.deepcopy(destination), {'a': {'b': {'x': 9}}, 'n': None})
        self.assertEqual(result, {'a': {'b': {'x': 9, 'keep': 2}}, 'n': 3})
        self.assertEqual(destination, {'a': {'b': {'x': 1, 'keep': 2}}, 'n': 3})

    def test_object_scalar_mismatches_do_not_clobber(self):
        self.assertEqual(assign_with_depth({'a': {'x': 1}, 'b': 2}, {'a': 5, 'b': {'x': 3}}), {'a': {'x': 1}, 'b': 2})

    def test_array_union_has_js_identity_and_boolean_numeric_distinction(self):
        first, second = {'x': 1}, {'x': 1}
        destination = [1, first, float('nan')]
        result = assign_with_depth(destination, [1, True, first, second, float('nan')])
        self.assertEqual(len(result), 5)
        self.assertIs(result[1], first)
        self.assertIs(result[3], True)
        self.assertIs(result[4], second)
        self.assertTrue(math.isnan(result[2]))

    def test_array_of_sources_merges_in_order_into_object(self):
        self.assertEqual(assign_with_depth({}, [{'a': 1}, {'b': 2}, {'a': 3}]), {'a': 3, 'b': 2})

    def test_frontmatter_directive_lodash_array_index_merge_is_distinct(self):
        self.assertEqual(merge_layers({'items': [{'a': 1}, 2, 3]}, {'items': [{'b': 4}, 5]}),
                         {'items': [{'a': 1, 'b': 4}, 5, 3]})
        self.assertEqual(merge_layers({'a': {'x': 1}}, {'a': None}), {'a': None})


class ThemeColorSourceTests(unittest.TestCase):
    def test_css_color_forms_have_independently_known_channels(self):
        for color, expected in [('red',(1,0,0,1)),('#f00',(1,0,0,1)),('#ff000080',(1,0,0,128/255)),
                                ('rgb(100%,0%,0%)',(1,0,0,1)),('rgba(255,0,0,0.5)',(1,0,0,.5)),
                                ('hsl(120,100%,50%)',(0,1,0,1)),('hsl(0.5turn,100%,50%)',(0,1,1,1)),
                                ('transparent',(0,0,0,0)),('navy',(0,0,128/255,1))]:
            with self.subTest(color=color):
                for actual,wanted in zip(channels(color),expected): self.assertAlmostEqual(actual,wanted,places=9)

    def test_base_primary_border_derivation_preserves_source_hsl(self):
        # theme-helpers.mkBorder decreases saturation40 and lightness10.
        variables=get_theme_variables('base',{'primaryColor':'#ff0000'})
        self.assertEqual(variables['mainBkg'],'#ff0000')
        for actual,wanted in zip(channels(variables['nodeBorder']),(.64,.16,.16,1)):
            self.assertAlmostEqual(actual,wanted,places=8)

    def test_explicit_node_border_disables_base_gradient_unless_explicit(self):
        self.assertFalse(get_theme_variables('base',{'nodeBorder':'#123456'})['useGradient'])
        self.assertTrue(get_theme_variables('base',{'nodeBorder':'#123456','useGradient':True})['useGradient'])

    def test_theme_effective_variables_are_request_local(self):
        first=get_theme_variables('redux-color',{'mainBkg':'#ffeedd'})
        second=get_theme_variables('redux-color')
        first['mainBkg']='#000000'
        self.assertEqual(second['mainBkg'],'#ffffff')


class RemovedLayoutPolicyTests(unittest.TestCase):
    def test_removed_layout_requests_fail_before_canvas_without_fallback(self):
        from unittest.mock import patch
        from py_mermaid import render

        requests = [
            (BASE, {'layout': 'dagre'}),
            (BASE, {'flowchart': {'layout': 'dagre'}}),
            (BASE, {'layout': 'dagre-wrapper'}),
            (BASE, {'layout': 'dagre-d3'}),
            ('---\nconfig:\n  layout: dagre\n---\n' + BASE, None),
            ('---\nconfig:\n  flowchart:\n    layout: dagre\n---\n' + BASE, None),
            ('%%{init: {"layout":"dagre"}}%%\n' + BASE, None),
            ('%%{initialize: {"flowchart":{"layout":"dagre"}}}%%\n' + BASE, None),
        ]
        for text, config in requests:
            with self.subTest(text=text, config=config), patch('py_mermaid.rendering.skia.CanvasSession') as canvas:
                before = copy.deepcopy(config)
                with self.assertRaises(MermaidError) as caught:
                    render(text, config=config, backend='cpu')
                self.assertEqual(caught.exception.code, 'UNSUPPORTED_CONFIG')
                self.assertIn('ELK', str(caught.exception))
                self.assertNotIn('deferred', str(caught.exception))
                canvas.assert_not_called()
                self.assertEqual(config, before)
                self.assertEqual(parse_flowchart(BASE).config.layout, 'elk')


if __name__ == '__main__':
    unittest.main()
