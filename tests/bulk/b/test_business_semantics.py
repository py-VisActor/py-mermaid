"""Fixed Langium/Jison productions, source DB reductions and conformance facts."""
from .support import SourceCase, model


class CynefinSemantics(SourceCase):
    def test_c01_five_domains_and_quoted_items(self):
        m=model('cynefin-beta:\ncomplex\n "Explore"\ncomplicated\n "Analyse"\nclear\n "Repeat"\nchaotic\n "Act"\nconfusion\n "Decide"\n')
        self.assertEqual(dict(m.domains),{'complex':('Explore',),'complicated':('Analyse',),'clear':('Repeat',),'chaotic':('Act',),'confusion':('Decide',)})

    def test_c02_transition_order_and_optional_label(self):
        m=model('cynefin-beta\ncomplex --> complicated : "Learning"\ncomplicated --> clear\n')
        self.assertEqual(m.transitions,(('complex','complicated','Learning'),('complicated','clear','')))

    def test_c03_repeated_domain_last_block_wins(self):
        self.assertEqual(dict(model('cynefin-beta\nclear\n "Old"\nclear\n "New"\n').domains),{'clear':('New',)})

    def test_c04_self_transition_warns_and_is_not_drawn(self):
        from py_mermaid import parse
        d=parse('cynefin-beta\nclear --> clear : "Loop"\n')
        self.assertEqual(d.model.transitions,())
        self.assertTrue(any('self-loop' in str(x) for x in d.diagnostics))

    def test_c05_unquoted_item_rejected(self):
        self.reject('cynefin-beta\nclear\n Unquoted\n')

    def test_c06_unknown_domain_and_missing_eol_rejected(self):
        for s in ('cynefin-beta\nunknown\n "x"\n','cynefin-beta\nclear --> complex complex --> clear\n'):
            with self.subTest(source=s):self.reject(s)


class EventSemantics(SourceCase):
    def test_e01_aliases_qualified_names_and_reset(self):
        for alias in ('rmo','readmodel','ui','cmd','command','evt','event','pcr','processor'):
            with self.subTest(alias=alias):
                m=model('eventmodeling\nrf 001 '+alias+' store.Order\n')
                f=m.frames[0]
                self.assertEqual((f.id,f.type,f.entity,f.reset),('001',alias,'store.Order',True))

    def test_e02_explicit_multiple_sources(self):
        m=model('eventmodeling\ntf 1 cmd Place\ntf 2 cmd Pay\ntf 3 evt Ordered ->> 1 ->> 2\n')
        self.assertEqual(m.frames[-1].sources,('1','2'))

    def test_e03_data_reference_and_raw_block(self):
        m=model('eventmodeling\ndata payload {\n "value": 3\n}\ntf 1 ui Page [[payload]]\n')
        self.assertEqual(m.frames[0].data_reference,'payload')
        self.assertEqual(m.data[0][0],'payload')
        self.assertIn('"value": 3',m.data[0][1])

    def test_e04_inline_data_formats(self):
        for typ in ('json','jsobj','figma','salt','uri','md','html','text'):
            with self.subTest(format=typ):
                f=model('eventmodeling\ntf 1 ui Page `'+typ+'` {hello}\n').frames[0]
                self.assertEqual(f.data_inline,'{hello}')

    def test_e05_reset_without_source_has_no_inferred_reference(self):
        m=model('eventmodeling\ntf 1 ui Page\nrf 2 cmd Submit\n')
        self.assertTrue(m.frames[-1].reset)
        self.assertEqual(m.frames[-1].sources,())

    def test_e06_duplicate_frame_including_reset_rejected(self):
        self.reject('eventmodeling\ntf 1 ui Page\nrf 1 cmd Again\n')

    def test_e07_frame_identifier_limit_and_unknown_data_format(self):
        for s in ('eventmodeling\ntf 1000 ui Page\n','eventmodeling\ntf 1 ui Page `yaml` {a}\n'):
            with self.subTest(source=s):self.reject(s)

    def test_e08_invalid_source_type_rejected(self):
        self.reject('eventmodeling\ntf 1 evt Arrived\ntf 2 cmd Submit ->> 1\n')


class IshikawaSemantics(SourceCase):
    def test_i01_indent_relative_to_first_cause(self):
        m=model('ishikawa-beta\nEffect\n     People\n       Training\n     Process\n       Review\n')
        self.assertEqual(m.text,'Effect')
        self.assertEqual([c.text for c in m.children],['People','Process'])
        self.assertEqual(m.children[0].children[0].text,'Training')

    def test_i02_effect_indentation_does_not_own_cause_depth(self):
        m=model('ishikawa\n     Effect\n  Cause\n    Detail\n')
        self.assertEqual(m.children[0].children[0].text,'Detail')

    def test_i03_sibling_dedent_closes_only_deeper_causes(self):
        m=model('ishikawa\nEffect\n A\n   B\n     C\n   D\n E\n')
        self.assertEqual([c.text for c in m.children],['A','E'])
        self.assertEqual([c.text for c in m.children[0].children],['B','D'])

    def test_i04_missing_effect_rejected(self):
        self.reject('ishikawa\n')


class WardleySemantics(SourceCase):
    def test_w01_coordinate_swap_fraction_and_percent(self):
        m=model('wardley-beta\ncomponent A [0.8, 0.2]\ncomponent B [80.0, 20.0]\n')
        self.assertEqual([(n.x,n.y) for n in m.nodes],[(20,80),(20,80)])

    def test_w02_anchor_offset_strategy_and_inertia(self):
        m=model('wardley-beta\nanchor User [0.9, 0.5]\ncomponent API [0.7, 0.3] label [-4, 8] (buy) inertia\n')
        self.assertEqual(m.nodes[0].kind,'anchor')
        n=m.nodes[1]
        self.assertEqual((n.offset_x,n.offset_y,n.strategy,n.inertia),(-4,8,'buy',True))

    def test_w03_pipeline_children_share_parent_visibility(self):
        m=model('wardley-beta\ncomponent Compute [0.4, 0.5]\npipeline Compute {\n component Custom [0.2]\n component Utility [0.8]\n}\n')
        self.assertEqual(dict(m.pipelines),{'Compute':('Compute_Custom','Compute_Utility')})
        self.assertEqual([(n.id,n.x,n.y,n.in_pipeline) for n in m.nodes[1:]],[('Compute_Custom',20,40,True),('Compute_Utility',80,40,True)])

    def test_w04_latest_evolve_and_unknown_ignored(self):
        m=model('wardley-beta\ncomponent A [0.4, 0.2]\nevolve A 0.5\nevolve A 0.8\nevolve Missing 0.9\n')
        self.assertEqual(m.trends,(('A',80,40),))

    def test_w05_size_and_custom_stages(self):
        m=model('wardley-beta\nsize [800, 500]\nevolution Genesis -> Custom -> Product -> Utility\ncomponent A [0.4, 0.2]\n')
        self.assertEqual(m.size,(800,500))
        self.assertEqual(m.stages,('Genesis','Custom','Product','Utility'))

    def test_w06_link_endpoints_and_dash(self):
        m=model('wardley-beta\ncomponent A [0.8, 0.2]\ncomponent B [0.4, 0.7]\nA -.-> B\n')
        self.assertEqual(m.links[0][:3],('A','B',True))

    def test_w07_invalid_coordinate_rejected(self):
        self.reject('wardley-beta\ncomponent A [101.0, 0.2]\n')

    def test_w08_integer_coordinate_is_not_decimal_terminal(self):
        self.reject('wardley-beta\ncomponent A [1, 0]\n')

    def test_w09_pipeline_requires_declared_parent(self):
        self.reject('wardley-beta\npipeline Missing {\n component Child [0.2]\n}\n')


class AgentSemantics(SourceCase):
    def test_a01_source_kinds_and_shapes(self):
        source='agentflow-beta TB\n'+''.join(f'n{i}[Label{i}]\nn{i}@{{ shape: {kind} }}\n' for i,kind in enumerate(('task','tool','input','decision','refdoc','action')))
        m=model(source)
        self.assertEqual(dict(m.kinds),dict((f'n{i}',kind) for i,kind in enumerate(('task','tool','input','decision','refdoc','action'))))
        self.assertEqual([n.shape for n in m.graph.nodes],['roundedRect','subroutine','lean-right','diamond','lin-doc','hexagon'])

    def test_a02_flow_membership_and_connector(self):
        m=model('agentflow-beta TB\nconnector external[API]\nflow team[Team]\n A[Work]\n A --> external\nend\n')
        self.assertEqual(m.connectors,('external',))
        self.assertEqual(next(n for n in m.graph.nodes if n.id=='A').parent_id,'team')
        # agentflowDb.addSubGraph exempts globalNodes, not connectors.
        self.assertEqual(next(n for n in m.graph.nodes if n.id=='external').parent_id,'team')

    def test_a03_global_nodes_not_claimed_by_flow(self):
        m=model('agentflow-beta TB\nglobal\n X[Shared]\nend\nflow F[Flow]\n A --> X\nend\n')
        self.assertIsNone(next(n for n in m.graph.nodes if n.id=='X').parent_id)
        self.assertEqual(next(n for n in m.graph.nodes if n.id=='A').parent_id,'F')

    def test_a04_metadata_does_not_create_reserved_semantic_diagnostics(self):
        from py_mermaid import parse
        d=parse('agentflow-beta TB\nA[Work]\nA@{ shape: tool, arbitrary: retained, retry: 2 }\n')
        self.assertFalse(any('FLOW_NO_INPUT' in str(x) or 'UNKNOWN_METADATA' in str(x) for x in d.diagnostics))
        self.assertEqual(dict(d.model.graph.nodes[0].metadata)['arbitrary'],'retained')

    def test_a05_edges_preserve_reference_and_failure_markers(self):
        m=model('agentflow-beta TB\nA --> B\nB -.- C\nB --x D\n')
        self.assertEqual([(e.source,e.target) for e in m.graph.edges],[('A','B'),('B','C'),('B','D')])
        self.assertEqual(m.graph.edges[-1].marker_end,'cross')

    def test_a06_unterminated_flow_has_structured_error(self):
        from py_mermaid.model.flowchart import MermaidError
        from py_mermaid import parse
        with self.assertRaises(MermaidError) as c:parse('agentflow-beta TB\nflow F\n A[Work]\n')
        self.assertIn(c.exception.code,('SYNTAX_ERROR','INVALID_SYNTAX'))
        self.assertIsNotNone(c.exception.span)


class SwimlaneSemantics(SourceCase):
    def test_s01_full_flow_shape_and_edge_grammar(self):
        m=model('swimlane-beta LR\nsubgraph L[Lane]\n A{Decision} -->|Yes| B([Done])\nend\n')
        self.assertEqual(m.direction,'LR')
        self.assertEqual([(n.id,n.parent_id) for n in m.nodes],[('A','L'),('B','L')])
        self.assertEqual(m.nodes[0].shape,'diamond')
        self.assertEqual(m.edges[0].label,'Yes')

    def test_s02_nested_membership(self):
        m=model('swimlane-beta TB\nsubgraph Outer\n subgraph Inner\n A[Work]\n end\n B[Other]\nend\n')
        self.assertEqual(next(g for g in m.groups if g.id=='Inner').parent_id,'Outer')
        self.assertEqual(next(n for n in m.nodes if n.id=='A').parent_id,'Inner')
        self.assertEqual(next(n for n in m.nodes if n.id=='B').parent_id,'Outer')

    def test_s03_all_flow_directions_preserved(self):
        for direction in ('TD','TB','LR','RL','BT'):
            with self.subTest(direction=direction):self.assertEqual(model('swimlane-beta '+direction+'\nA --> B\n').direction,direction)

    def test_s04_source_spans_refer_to_original_input(self):
        from py_mermaid import parse
        source='---\ntitle: Lanes\n---\nswimlane-beta LR\nA[Work] --> B[Done]\n'
        d=parse(source)
        n=d.model.nodes[0]
        self.assertEqual(source[n.span.start.index:n.span.start.index+1],'A')
        self.assertEqual(n.span.start.line,5)
