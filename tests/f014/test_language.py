"""Independent F01.4 language/config assertions from pinned grammar/FlowDB/spec.

No expected values are obtained by running the candidate. Source/contract
provenance, dormant grammar helpers and explicit user exclusions are recorded in
references/f014-language-assertions.json. This module is unexecuted during S3.
"""
from __future__ import annotations
import copy
from dataclasses import FrozenInstanceError
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from py_mermaid.config import resolve_config
from py_mermaid.config.values import thaw_value
from py_mermaid.diagrams.flowchart.syntax import destruct_link
from py_mermaid.model.flowchart import MermaidError
from py_mermaid.parsing import parse_flowchart

FIXTURES = json.loads(Path(__file__).with_name('language-cases.json').read_text(encoding='utf8'))


def plain(value):
    """Decode only the frozen public value contract, not a parser expectation."""
    return thaw_value(value)


class StaticLanguageFixtureTests(unittest.TestCase):
    def assert_case(self, case):
        diagram = parse_flowchart(case['text'], config=copy.deepcopy(case.get('config')))
        self.assertEqual([[n.id, n.label] for n in diagram.nodes], case['nodes'])
        self.assertEqual([[e.source, e.target] for e in diagram.edges], case['edges'])
        self.assertEqual(diagram.direction, case['direction'])
        self.assertEqual([dict(id=g.id, label=g.label, members=list(g.members), parent_id=g.parent_id,
                               direction=g.direction) for g in diagram.groups], case.get('groups', []))
        self.assertEqual([e.label for e in diagram.edges], case.get('edgeLabels', [''] * len(diagram.edges)))
        self.assertEqual([e.label_kind for e in diagram.edges], case.get('edgeLabelKinds', ['text'] * len(diagram.edges)))
        for n in diagram.nodes:
            self.assertEqual(n.shape, case.get('shapes', {}).get(n.id, 'square'))
            self.assertEqual(n.label_kind, case.get('labelKinds', {}).get(n.id, 'text'))
            if n.id in case.get('nodeClasses', {}): self.assertEqual(list(n.classes), case['nodeClasses'][n.id])
            if n.id in case.get('nodeStyles', {}): self.assertEqual(list(n.styles), case['nodeStyles'][n.id])
            if n.id in case.get('metadata', {}): self.assertEqual(plain(n.metadata), case['metadata'][n.id])
            if n.id in case.get('props', {}): self.assertEqual(plain(n.props), case['props'][n.id])
            if n.id in case.get('colorIndices', {}): self.assertEqual(n.color_index, case['colorIndices'][n.id])
        for g in diagram.groups:
            if g.id in case.get('groupClasses', {}): self.assertEqual(list(g.classes), case['groupClasses'][g.id])
            if g.id in case.get('groupMetadata', {}): self.assertEqual(plain(g.metadata), case['groupMetadata'][g.id])
            if g.id in case.get('groupColorIndices', {}): self.assertEqual(g.color_index, case['groupColorIndices'][g.id])
        for name, actual in [('sourceIds', [e.source_id for e in diagram.edges]),
                             ('userIds', [e.is_user_defined_id for e in diagram.edges]),
                             ('edgeCurves', [e.curve for e in diagram.edges]),
                             ('edgeClasses', [list(e.classes) for e in diagram.edges]),
                             ('edgeStyles', [list(e.styles) for e in diagram.edges]),
                             ('edgeAnimations', [dict(animate=e.animate, animation=e.animation) for e in diagram.edges])]:
            if name in case: self.assertEqual(actual, case[name], name)
        if 'edgeSemantics' in case:
            self.assertEqual([dict(type=e.edge_type, stroke=e.stroke, minLength=e.min_length,
                                   startMarker=e.marker_start, endMarker=e.marker_end) for e in diagram.edges], case['edgeSemantics'])
        if 'classDefinitions' in case:
            self.assertEqual([dict(name=c.name, styles=list(c.styles), textStyles=list(c.text_styles)) for c in diagram.class_definitions], case['classDefinitions'])
        if 'defaultEdgeStyles' in case: self.assertEqual(list(diagram.default_edge_styles), case['defaultEdgeStyles'])
        if 'defaultEdgeCurve' in case: self.assertEqual(diagram.default_edge_curve, case['defaultEdgeCurve'])
        for key, value in case.get('expectedConfig', {}).items(): self.assertEqual(getattr(diagram.config, key), value)
        return diagram

    def test_all_handwritten_static_semantic_cases(self):
        for case in FIXTURES['cases']:
            with self.subTest(case=case['id']): self.assert_case(case)

    def test_all_source_metadata_shape_aliases(self):
        for case in FIXTURES['aliasCases']:
            with self.subTest(alias=case['id']): self.assert_case(case)

    def test_independent_fixture_denominator(self):
        self.assertEqual(len(FIXTURES['cases']), 93)
        self.assertEqual(len(FIXTURES['aliasCases']), 147)
        self.assertEqual(len({case['text'] for case in FIXTURES['aliasCases']}), 147)
        self.assertEqual(len({case['shapes']['A'] for case in FIXTURES['aliasCases']}), 59)
        self.assertEqual(len(FIXTURES['negativeCases']), 14)
        self.assertEqual(len(FIXTURES['semanticErrorCases']), 4)

    def test_source_parse_invalid_cases(self):
        for case in FIXTURES['negativeCases']:
            with self.subTest(case=case['id']):
                with self.assertRaises(MermaidError) as caught: parse_flowchart(case['text'])
                self.assertIsNotNone(caught.exception.span)
                self.assertLessEqual(caught.exception.span.end.index, len(case['text']))

    def test_source_metadata_and_index_validation_errors(self):
        for case in FIXTURES['semanticErrorCases']:
            with self.subTest(case=case['id']):
                with self.assertRaises(MermaidError) as caught: parse_flowchart(case['text'])
                self.assertEqual(caught.exception.code, case['code'])

    def test_user_exclusions_are_not_parse_invalid_fixtures(self):
        for case in FIXTURES['excludedCases']:
            with self.subTest(case=case['id']):
                if case['id']=='math-separate':
                    self.assertEqual(parse_flowchart(case['text']).nodes[0].label,'$$x^2$$')
                    continue
                with self.assertRaises(MermaidError) as caught: parse_flowchart(case['text'], config=case.get('config'))
                self.assertIn(caught.exception.code, case['codes'])

    def test_source_anomalies_are_explicit_separate_boundaries(self):
        for case in FIXTURES['sourceAnomalyCases']:
            with self.subTest(case=case['id']):
                if 'nativeCode' in case:
                    with self.assertRaises(MermaidError) as caught: parse_flowchart(case['text'])
                    self.assertEqual(caught.exception.code, case['nativeCode'])
                elif case.get('expectation') == 'positive':
                    self.assertEqual(parse_flowchart(case['text']).direction, case['direction'])
                else:
                    self.assertEqual(parse_flowchart(case['text']).nodes[0].shape, 'ellipse')


class GrammarTokenSourceTests(unittest.TestCase):
    def test_all_classic_vertex_alternatives_remain_reachable(self):
        cases=[('A[Square]','square','Square'),('A(((Double)))','doublecircle','Double'),
               ('A((Circle))','circle','Circle'),('A(-Ellipse-)','ellipse','Ellipse'),
               ('A([Stadium])','stadium','Stadium'),('A[[Sub]]','subroutine','Sub'),
               ('A[|key:value|Props]','square','Props'),('A[(Cylinder)]','cylinder','Cylinder'),
               ('A(Round)','round','Round'),('A{Decision}','diamond','Decision'),
               ('A{{Hex}}','hexagon','Hex'),('A>Odd]','odd','Odd'),
               ('A[/Trap\\]','trapezoid','Trap'),('A[\\Inverse/]','inv_trapezoid','Inverse'),
               ('A[/Right/]','lean_right','Right'),('A[\\Left\\]','lean_left','Left'),('A','square','A')]
        self.assertEqual(len(cases),17)
        for text,shape,label in cases:
            with self.subTest(text=text):
                node=parse_flowchart('flowchart TD\n'+text).nodes[0]
                self.assertEqual((node.shape,node.label),(shape,label))

    def test_each_identifier_token_alternative_has_reachable_input(self):
        # NUM/NODE_STRING/DOWN/MINUS/DEFAULT/COMMA/COLON/AMP/BRKT/MULT/UNICODE_TEXT.
        for identifier in ['123', 'Alpha', 'v', '-', 'default', ',', ':', '&', '#', '*', '\u4e2d']:
            with self.subTest(identifier=identifier):
                diagram = parse_flowchart('flowchart TD\n' + identifier)
                self.assertEqual([(n.id, n.label) for n in diagram.nodes], [(identifier, identifier)])

    def test_all_header_separator_productions(self):
        for separator in [';', '\n', ' \n', '\t \n']:
            with self.subTest(separator=repr(separator)):
                self.assertEqual(parse_flowchart('graph TD' + separator + 'A').nodes[0].id, 'A')

    def test_document_line_and_empty_alternatives(self):
        for source, nodes in [('flowchart TD', []), ('flowchart\n', []), ('graph TD\n;\n\t ;\nA;\n', ['A'])]:
            with self.subTest(source=source): self.assertEqual([n.id for n in parse_flowchart(source).nodes], nodes)

    def test_text_and_quoted_markdown_label_productions(self):
        inputs = [('A[Plain]', 'Plain', 'text'), ('A["Quoted (text)"]', 'Quoted (text)', 'text'),
                  ('A["`**Markdown**`"]', '**Markdown**', 'markdown'), ('A[\u4e2d\u6587]', '\u4e2d\u6587', 'text'),
                  ('A[<b>Tag</b>]', '<b>Tag</b>', 'text')]
        for syntax, label, kind in inputs:
            with self.subTest(syntax=syntax):
                n = parse_flowchart('flowchart TD\n' + syntax).nodes[0]
                self.assertEqual((n.label, n.label_kind), (label, kind))

    def test_unquoted_group_keyword_productions(self):
        for title in ['style', 'linkStyle', 'classDef', 'class', 'click', 'graph', 'subgraph', 'end', 'v', '^']:
            with self.subTest(title=title):
                source = 'flowchart TD\nsubgraph ' + title + ';\nA;\nend'
                g = parse_flowchart(source).groups[0]
                self.assertEqual((g.id, g.label, g.members), (title, title, ('A',)))

    def test_source_unicode_range_boundaries(self):
        for identifier in ['\u00aa', '\u00b5', '\u4e00', '\u9fcc', '\uffda']:
            with self.subTest(identifier=identifier): self.assertEqual(parse_flowchart('graph TD\n' + identifier).nodes[0].id, identifier)
        for identifier in ['\u00ab', '\u9fcd', '\U0001f600']:
            with self.subTest(identifier=identifier):
                with self.assertRaises(MermaidError): parse_flowchart('graph TD\n' + identifier)

    def test_source_keyword_prefix_and_punctuation_boundaries(self):
        for identifier in ['Astyle', 'endUser', 'defaultNode', '123abc', 'A/B', 'A.B', 'A:B', 'A&B', 'styleNode', 'classify', 'value']:
            with self.subTest(identifier=identifier): self.assertEqual(parse_flowchart('graph TD\n' + identifier).nodes[0].id, identifier)
        for source in ['graph TD\nstyle', 'graph TD\nclass', 'graph TD\nA &B']:
            with self.subTest(source=source):
                with self.assertRaises(MermaidError): parse_flowchart(source)

    def test_compiled_word_literal_boundaries_apply_to_old_props(self):
        for key,value in [('key','value'),('styleName','defaultName'),('defaultName','vary')]:
            with self.subTest(key=key,value=value):
                node=parse_flowchart('graph TD\nA[|'+key+':'+value+'|Label]').nodes[0]
                self.assertEqual(dict(node.props),{key:value})

    def test_header_space_semicolon_is_invalid_but_node_space_semicolon_is_valid(self):
        with self.assertRaises(MermaidError) as caught:parse_flowchart('graph TD ;\nA')
        self.assertEqual(caught.exception.code,'INVALID_SYNTAX')
        self.assertEqual(parse_flowchart('graph TD\nA ;\nB ;').nodes[1].id,'B')

    def test_flow_yaml_root_fields_can_start_at_column_zero(self):
        from py_mermaid.parsing.yaml_json import load_yaml_json
        self.assertEqual(load_yaml_json('{\nshape: rect,\nlabel: Alpha\n}'),{'shape':'rect','label':'Alpha'})
        self.assertEqual(load_yaml_json('[\nAlpha,\nBeta\n]'),['Alpha','Beta'])
        self.assertEqual(parse_flowchart('graph TD\nA@{shape: rect}').nodes[0].shape,'square')

    def test_public_and_helper_cold_import_paths_do_not_cycle(self):
        # Fresh interpreters preserve the failing import order; reordering the
        # test module imports would conceal the product topology regression.
        for statement in ['from py_mermaid.diagrams.flowchart.syntax import destruct_link',
                          'from py_mermaid.diagrams.flowchart import parse_flowchart',
                          'from py_mermaid.parsing.yaml_json import load_yaml_json']:
            with self.subTest(statement=statement):
                result=subprocess.run([sys.executable,'-c',statement],cwd=Path(__file__).resolve().parents[2],
                                      env=os.environ.copy(),capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)

    def test_metadata_before_and_after_cartesian_members(self):
        d = parse_flowchart('graph TD\nA@{shape: rounded} & B@{shape: cyl} --> C@{shape: doc} & D')
        self.assertEqual([(n.id,n.shape) for n in d.nodes], [('A','round'),('B','cylinder'),('C','waveEdgedRectangle'),('D','square')])
        self.assertEqual([(e.source,e.target) for e in d.edges], [('A','C'),('A','D'),('B','C'),('B','D')])

    def test_style_components_numbers_units_percent_and_spaces(self):
        source='graph TD\nA\nclassDef paint fill:#abc,stroke-width:12.5px,opacity:50%,font-family:Times New Roman'
        definition=parse_flowchart(source).class_definitions[0]
        self.assertEqual(definition.styles,('fill:#abc','stroke-width:12.5px','opacity:50%','font-family:Times New Roman'))
        # STYLE is explicitly a styleComponent token, even though this CSS value
        # is not a named color. This is a language assertion, not paint success.
        self.assertEqual(parse_flowchart('graph TD\nA\nclassDef paint fill:style').class_definitions[0].styles,('fill:style',))


class EdgeDeclarationSourceTests(unittest.TestCase):
    def test_source_destruct_link_mismatch_branches(self):
        for ending, beginning in [('==>','--'), ('-->','x--'), ('--o','<--')]:
            with self.subTest(ending=ending, beginning=beginning):
                self.assertEqual(destruct_link(ending, beginning), ('INVALID','INVALID',None,'none','point'))

    def test_source_edge_order_class_and_style_selector_use_source_id(self):
        d = parse_flowchart('graph TD\nA edge@--> B\nclass edge red\nstyle edge fill:red\nclassDef red stroke:blue')
        self.assertEqual([n.id for n in d.nodes], ['A','B'])
        self.assertEqual((d.edges[0].id,d.edges[0].source_id,d.edges[0].classes,d.edges[0].styles), ('e0','edge',('red',),()))

    def test_source_user_id_collision_with_generated_id(self):
        d = parse_flowchart('graph TD\nA --> B\nC L_A_B_0@--> D')
        self.assertEqual([(e.source_id,e.is_user_defined_id) for e in d.edges], [('L_A_B_0',False),('L_C_D_0',False)])

    def test_all_thirteen_edge_curve_names(self):
        curves = ['basis','bumpX','bumpY','cardinal','catmullRom','linear','monotoneX','monotoneY','natural','step','stepAfter','stepBefore','rounded']
        for curve in curves:
            with self.subTest(curve=curve):
                d = parse_flowchart('graph TD\nA id@--> B\nid@{curve: '+curve+'}')
                self.assertEqual(d.edges[0].curve,curve)

    def test_animation_metadata_and_classes_are_static_values(self):
        d = parse_flowchart('graph TD\nA e1@--> B\ne1@{animate: true}\nclass e1 animated\nclassDef animated stroke-dasharray:9\\,5,stroke-dashoffset:900,animation:dash 20s linear infinite')
        self.assertIs(d.edges[0].animate, True)
        self.assertEqual(d.edges[0].classes, ('animated',))
        self.assertIn('animation:dash 20s linear infinite',d.class_definitions[0].styles)
        self.assertFalse(hasattr(d,'bindFunctions'))

    def test_cartesian_max_edges_boundary(self):
        source='graph TD\nA & B --> C & D'
        self.assertEqual(len(parse_flowchart(source,config={'maxEdges':4}).edges),4)
        with self.assertRaises(MermaidError) as caught: parse_flowchart(source,config={'maxEdges':3})
        self.assertEqual(caught.exception.code,'MAX_EDGES_EXCEEDED')


class MetadataCollapseSourceTests(unittest.TestCase):
    def test_fourteen_click_productions_have_only_initial_clickable_class(self):
        statements=['call callback()', 'call callback() "tip"', 'call callback(42)', 'call callback(42) "tip"',
                    'href "https://example.invalid"', 'href "https://example.invalid" "tip"',
                    'href "https://example.invalid" _blank', 'href "https://example.invalid" "tip" _blank',
                    'callback', 'callback "tip"', '"https://example.invalid"',
                    '"https://example.invalid" "tip"', '"https://example.invalid" _self',
                    '"https://example.invalid" "tip" _self']
        self.assertEqual(len(statements),14)
        for statement in statements:
            with self.subTest(statement=statement):
                diagram=parse_flowchart('graph TD\nA --> B\nclick A '+statement)
                self.assertEqual([n.id for n in diagram.nodes],['A','B'])
                self.assertEqual(diagram.nodes[0].classes,('clickable',))
                for attribute in ['link','callback','tooltip','bindFunctions']:
                    self.assertFalse(hasattr(diagram.nodes[0],attribute))

    def test_all_group_algorithm_metadata_values_are_preserved_for_layout(self):
        for algorithm in ['elk.layered','elk.box','elk.rectpacking','elk.stress','elk.force','elk.mrtree','elk.radial','elk.sporeOverlap','elk.unknown']:
            with self.subTest(algorithm=algorithm):
                d=parse_flowchart('graph TD\nsubgraph G\nA\nend\nG@{algorithm: '+algorithm+'}')
                self.assertEqual(plain(d.groups[0].metadata),{'algorithm':algorithm})

    def test_removed_group_layout_family_fails_before_any_canvas_entry(self):
        for algorithm in ['dagre','dagre-wrapper','DAGRE','other-engine']:
            inputs=[
                'graph TD\nsubgraph G\nA\nend\nG@{algorithm: '+algorithm+'}',
                'graph TD\nG --> Z\nsubgraph G\nA\nend\nG@{algorithm: '+algorithm+'}',
                'graph TD\nsubgraph O\nsubgraph G\nA\nend\nend\nG@{algorithm: '+algorithm+'}']
            for source in inputs:
                with self.subTest(algorithm=algorithm,source=source):
                    with self.assertRaises(MermaidError) as caught:parse_flowchart(source)
                    self.assertEqual(caught.exception.code,'UNSUPPORTED_CONFIG')

    def test_node_algorithm_is_opaque_unless_it_is_an_actual_group_selection(self):
        node=parse_flowchart('graph TD\nA@{algorithm: dagre}').nodes[0]
        self.assertEqual(plain(node.metadata),{'algorithm':'dagre'})
        # FlowDB does not forward an earlier node's metadata to a later group;
        # no forbidden engine was selected by this declaration order.
        diagram=parse_flowchart('graph TD\nG@{algorithm: dagre}\nsubgraph G\nA\nend')
        self.assertEqual(plain(diagram.groups[0].metadata),{})
        self.assertEqual(diagram.config.layout,'elk')

    def test_all_group_directions_and_inheritance(self):
        for direction in ['TD','TB','LR','RL','BT']:
            with self.subTest(direction=direction):
                d=parse_flowchart('flowchart '+direction+'\nsubgraph O\ndirection LR\nsubgraph I\nA\nend\nend',config={'flowchart':{'inheritDir':True}})
                expected = 'TB' if direction=='TD' else direction # source FlowDB canonical root
                self.assertEqual({g.id:g.direction for g in d.groups},{'I':expected,'O':'LR'})

    def test_group_metadata_before_declaration_is_not_forward_routed(self):
        d=parse_flowchart('graph TD\nG@{view: collapsed}\nsubgraph G[Group]\nA\nend')
        self.assertEqual([n.id for n in d.nodes],['A'])
        self.assertEqual([g.id for g in d.groups],['G'])
        self.assertEqual(plain(d.groups[0].metadata),{})

    def test_edge_metadata_pseudo_member_is_not_a_drawable_node(self):
        d=parse_flowchart('graph TD\nsubgraph G\nA e1@--> B\ne1@{curve: step}\nend')
        self.assertEqual(set(d.groups[0].members),{'A','B'})
        self.assertEqual([n.id for n in d.nodes],['A','B'])

    def test_expanded_restores_group_metadata_without_inventing_interaction(self):
        d=parse_flowchart('graph TD\nsubgraph G\nA\nend\nG@{view: collapsed}\nG@{view: expanded}')
        self.assertEqual([g.id for g in d.groups],['G'])
        self.assertEqual([n.id for n in d.nodes],['A'])

    def test_metadata_truthy_updates_do_not_clear_prior_assets(self):
        d=parse_flowchart('graph TD\nA@{img: logo, w: 40}\nA@{img: "", w: 0}')
        self.assertEqual(d.nodes[0].shape,'imageSquare')
        self.assertEqual(plain(d.nodes[0].metadata)['img'],'logo')
        self.assertEqual(plain(d.nodes[0].metadata)['w'],40)

    def test_metadata_label_preserves_source_db_markup_before_native_sanitization(self):
        node=parse_flowchart('graph TD\nA@{label: "First<br/>second", labelType: text}').nodes[0]
        self.assertEqual((node.label,node.raw_label),('First<br/>second','First<br/>second'))
        node=parse_flowchart('graph TD\nA@{label: "#quot;Quoted#quot;", labelType: text}').nodes[0]
        self.assertEqual((node.label,node.raw_label),('&quot;Quoted&quot;','#quot;Quoted#quot;'))
        node=parse_flowchart('graph TD\nA@{label: "Safe<script>bad</script>", labelType: text}').nodes[0]
        self.assertEqual(node.label,'Safe<script>bad</script>')
        # This is DB semantics, never a claim that unsafe markup is painted.
        # Canvas/provider safety assertions independently check final sanitation.

    def test_request_input_and_result_values_are_isolated(self):
        config={'elk':{'preset':'legacy'},'look':'handDrawn','handDrawnSeed':19}
        original=copy.deepcopy(config)
        first=parse_flowchart('graph TD\nA id@--> B\nid@{animate: true}',config=config)
        with self.assertRaises(MermaidError):parse_flowchart('graph TD\nA@{shape: Unknown}')
        second=parse_flowchart('graph TD\nA --> B')
        self.assertEqual(config,original)
        self.assertEqual(first.edges[0].source_id,'id')
        self.assertEqual(second.config.look,'neo')
        self.assertFalse(second.edges[0].animate)
        self.assertEqual(second.class_definitions,())
        with self.assertRaises(FrozenInstanceError):first.edges[0].stroke='normal'

    def test_original_utf16_spans_through_metadata_and_edge_ids(self):
        source='---\r\ntitle: \U0001f600 Heading\r\n---\r\n%% comment\r\nflowchart RL\r\nA@{shape: doc, label: "\U0001f600 Label"} eid@-->|"\u6761\u4ef6"| B'
        d=parse_flowchart(source)
        self.assertEqual(d.edges[0].source_id,'eid')
        span=d.edges[0].label_span
        self.assertEqual(source[span.start.index:span.end.index],'\u6761\u4ef6')
        self.assertEqual(span.start.utf16_offset,len(source[:span.start.index].encode('utf-16-le'))//2)
        self.assertEqual(span.start.line,6)


class ElkPublicConfigurationTests(unittest.TestCase):
    def test_seven_source_registered_root_names(self):
        for name in ['elk','elk.stress','elk.force','elk.mrtree','elk.sporeOverlap','elk.box','elk.rectpacking']:
            with self.subTest(layout=name):
                self.assertEqual(resolve_config({'layout':name}).layout,name)
                self.assertEqual(parse_flowchart('---\nconfig:\n  flowchart:\n    layout: '+name+'\n---\ngraph TD\nA').config.layout,name)

    def test_unregistered_and_removed_root_layouts_explicitly_fail(self):
        for name in ['dagre','dagre-wrapper','elk.layered','elk.radial','unknown']:
            for config in [{'layout':name},{'flowchart':{'layout':name}}]:
                with self.subTest(config=config):
                    with self.assertRaises(MermaidError) as caught:resolve_config(config)
                    self.assertEqual(caught.exception.code,'UNSUPPORTED_CONFIG')

    def test_nine_defaults_preserve_four_missing_strategy_keys(self):
        values=dict(resolve_config().elk_options)
        self.assertEqual(values,dict(mergeEdges=False,straightenEdges=True,lineHops=True,preset='default',layeringLayerBound=4,forceNodeModelOrder=False,considerModelOrder='NODES_AND_EDGES',keepEntryNodeOnTop=False,orientFeedbackEdges=True))
        for key in ['nodePlacementStrategy','nodePlacementAlignment','layeringStrategy','cycleBreakingStrategy']:
            self.assertNotIn(key,values)

    def test_all_thirteen_public_options_and_no_mutation(self):
        elk=dict(mergeEdges=True,straightenEdges=False,lineHops='gap',preset='modelOrder',layeringLayerBound=6,forceNodeModelOrder=True,considerModelOrder='PREFER_NODES',keepEntryNodeOnTop=True,orientFeedbackEdges=False,nodePlacementStrategy='SIMPLE',nodePlacementAlignment='NONE',layeringStrategy='COFFMAN_GRAHAM',cycleBreakingStrategy='MODEL_ORDER')
        original=copy.deepcopy(elk)
        self.assertEqual(dict(resolve_config({'elk':elk}).elk_options),elk)
        self.assertEqual(elk,original)
        self.assertEqual(len(elk),13)

    def test_null_strategy_keeps_source_undefined_distinct_from_explicit_alignment(self):
        values=dict(resolve_config({'elk':{'nodePlacementStrategy':None,'nodePlacementAlignment':'NONE','preset':None}}).elk_options)
        self.assertNotIn('nodePlacementStrategy',values)
        self.assertEqual(values['nodePlacementAlignment'],'NONE')
        self.assertEqual(values['preset'],'default')

    def test_source_option_enums(self):
        enums={'preset':['default','legacy','modelOrder','depthFirst'],'nodePlacementStrategy':['SIMPLE','NETWORK_SIMPLEX','LINEAR_SEGMENTS','BRANDES_KOEPF'],'nodePlacementAlignment':['NONE','LEFTUP','LEFTDOWN','RIGHTUP','RIGHTDOWN','BALANCED'],'layeringStrategy':['NETWORK_SIMPLEX','LONGEST_PATH','LONGEST_PATH_SOURCE','COFFMAN_GRAHAM','MIN_WIDTH','STRETCH_WIDTH','INTERACTIVE'],'cycleBreakingStrategy':['GREEDY','DEPTH_FIRST','INTERACTIVE','MODEL_ORDER','GREEDY_MODEL_ORDER'],'considerModelOrder':['NONE','NODES_AND_EDGES','PREFER_EDGES','PREFER_NODES'],'lineHops':[True,False,'arc','gap']}
        for key,values in enums.items():
            for value in values:
                with self.subTest(key=key,value=value):self.assertEqual(dict(resolve_config({'elk':{key:value}}).elk_options)[key],value)

    def test_source_schema_layer_bound_has_no_minimum(self):
        for value in [0,-1,1.5]:
            with self.subTest(value=value):self.assertEqual(dict(resolve_config({'elk':{'layeringLayerBound':value}}).elk_options)['layeringLayerBound'],value)

    def test_invalid_public_options_are_config_errors_not_engine_fallback(self):
        for value in [{'unknown':1},{'algorithm':'layered'},{'preset':'missing'},{'mergeEdges':'true'},{'lineHops':'bridge'},{'layeringLayerBound':float('inf')}]:
            with self.subTest(value=value):
                with self.assertRaises(MermaidError) as caught:resolve_config({'elk':value})
                self.assertIn(caught.exception.code,('INVALID_CONFIG','UNSUPPORTED_CONFIG'))

    def test_handdrawn_look_seed_and_deterministic_id_settings(self):
        for seed,expected in [(0,0),(19,19),(-1,-1)]:
            with self.subTest(seed=seed):
                cfg=resolve_config({'look':'handDrawn','handDrawnSeed':seed,'deterministicIds':True,'deterministicIDSeed':'stable'})
                self.assertEqual((cfg.look,cfg.hand_drawn_seed,cfg.deterministic_ids,cfg.deterministic_id_seed),('handDrawn',expected,True,'stable'))
        # Original truthy values are preserved until rough's first Math.imul.
        for seed in [0.5,2**32,3.75]:
            with self.subTest(seed=seed):self.assertEqual(resolve_config({'handDrawnSeed':seed}).hand_drawn_seed,seed)



class SharedShapeThemeClosureTests(unittest.TestCase):
    """Hand-written expectations from pinned theme constructors/updateColors."""
    THEMES = ('base', 'dark', 'default', 'forest', 'neutral', 'neo', 'neo-dark',
              'redux', 'redux-color', 'redux-dark', 'redux-dark-color')

    def variables(self, theme, overrides=None):
        from py_mermaid.config.themes import get_theme_variables
        return get_theme_variables(theme, overrides)

    def test_note_defaults_all_eleven_theme_constructors_and_updates(self):
        table = {
            'default': ('#fff5ad', '#aaaa33', 'black'),
            'forest': ('#fff5ad', '#6eaa49', 'black'),
            'neutral': ('#666', '#999', '#fff'),
            'redux': ('#fff5ad', '#FACC15', '#28253D'),
            'redux-color': ('#fff5ad', '#FACC15', '#28253D'),
            'redux-dark': ('#FEF9C3', '#FACC15', '#28253D'),
            'redux-dark-color': ('#FEF9C3', '#FACC15', '#28253D'),
        }
        for theme, expected in table.items():
            with self.subTest(theme=theme):
                actual = self.variables(theme)
                self.assertEqual(tuple(actual[k] for k in ('noteBkgColor', 'noteBorderColor', 'noteTextColor')), expected)
        for theme in ('base', 'neo', 'neo-dark'):
            with self.subTest(theme=theme):
                actual = self.variables(theme)
                self.assertEqual((actual['noteBkgColor'], actual['noteTextColor']), ('#fff5ad', '#333'))
                # Source mkBorder subtracts 40 saturation and 10 lightness.
                self.assertEqual(actual['noteBorderColor'], 'hsl(52.6829268293, 60%, 73.9215686275%)')
        actual = self.variables('dark')
        # RGB(31,32,32) +16 HSL lightness; Khroma inverts fractional channels.
        self.assertEqual(actual['noteBkgColor'], 'hsl(180, 1.5873015873%, 28.3529411765%)')
        self.assertEqual(actual['noteBorderColor'], 'hsl(180, 0%, 18.3529411765%)')
        self.assertEqual(actual['noteTextColor'], 'rgb(183.8476190475, 181.5523809523, 181.5523809523)')

    def test_state_border_values_and_source_absence_are_preserved(self):
        expected = {'neo': '#000000', 'neutral': '#000', 'redux': '#28253D',
                    'redux-color': '#28253D', 'redux-dark': '#FFFFFF',
                    'redux-dark-color': '#FFFFFF'}
        for theme in self.THEMES:
            with self.subTest(theme=theme):
                actual = self.variables(theme)
                if theme in expected:
                    self.assertEqual(actual['stateBorder'], expected[theme])
                else:
                    self.assertNotIn('stateBorder', actual)

    def test_explicit_overrides_reapplied_after_update_all_themes(self):
        patch = dict(noteBkgColor='#102030', noteBorderColor='#aabbcc',
                     noteTextColor='#fedcba', stateBorder='#123456')
        original = copy.deepcopy(patch)
        for theme in self.THEMES:
            with self.subTest(theme=theme):
                actual = self.variables(theme, patch)
                self.assertEqual({key: actual[key] for key in patch}, patch)
                effective = dict(resolve_config({'theme': theme, 'themeVariables': patch}).theme_variables)
                self.assertEqual({key: effective[key] for key in patch}, patch)
        self.assertEqual(patch, original)

    def test_note_border_derivation_uses_preupdate_override_and_darkmode(self):
        for theme in ('base', 'neo', 'neo-dark'):
            for dark, expected in ((False, 'hsl(0, 60%, 40%)'), (True, 'hsl(0, 60%, 60%)')):
                with self.subTest(theme=theme, dark=dark):
                    actual = self.variables(theme, {'noteBkgColor': '#ff0000', 'darkMode': dark})
                    self.assertEqual(actual['noteBorderColor'], expected)
        for theme in ('redux', 'redux-color', 'redux-dark', 'redux-dark-color'):
            # A constructor-provided yellow border remains truthy despite fill override.
            self.assertEqual(self.variables(theme, {'noteBkgColor': '#ff0000'})['noteBorderColor'], '#FACC15')

    def test_note_dependencies_preserve_constructor_and_update_timing(self):
        for theme in ('default', 'forest'):
            actual = self.variables(theme, {'border2': '#123456', 'actorTextColor': '#654321'})
            self.assertEqual((actual['noteBorderColor'], actual['noteTextColor']), ('#123456', '#654321'))
        actual = self.variables('dark', {'mainBkg': '#ff0000', 'secondaryColor': '#00ff00'})
        self.assertEqual(actual['noteBkgColor'], 'hsl(0, 100%, 66%)')
        # Changing secondaryColor after construction does not recompute secondaryTextColor.
        self.assertEqual(actual['noteTextColor'], 'rgb(183.8476190475, 181.5523809523, 181.5523809523)')
        actual = self.variables('dark', {'secondaryBorderColor': '#123456', 'secondaryTextColor': '#654321'})
        self.assertEqual((actual['noteBorderColor'], actual['noteTextColor']), ('#123456', '#654321'))

    def test_new_shared_shape_theme_values_do_not_leak_between_requests(self):
        first = self.variables('redux-color', {'noteBorderColor': '#123456', 'stateBorder': '#654321'})
        first['noteBorderColor'] = '#000000'
        second = self.variables('redux-color')
        self.assertEqual((second['noteBorderColor'], second['stateBorder']), ('#FACC15', '#28253D'))


if __name__ == '__main__':
    unittest.main()
