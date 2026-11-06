"""Fixed renderer/style assertions; native calls only inside deferred P3 tests."""
from pathlib import Path
import unittest
from py_mermaid.api import arender
from py_mermaid.model.flowchart import ResourceBundle,IconResource
from py_mermaid.geometry.path_geometry import path_bounds,flatten_path

SVG=Path(__file__).with_name('resources').joinpath('user.svg').read_text(encoding='utf-8-sig')
RESOURCES=ResourceBundle(icons=(IconResource('test:user',SVG),))


async def picture(source,config=None,resources=None):
    return await arender(source,config=config,resources=resources,backend='cpu',format='png')


def visible(result,id=None):
    return ''.join(e.text or '' for e in result.trace if e.opacity>0 and (id is None or e.semantic_id==id))


def paths(result,role=None,id=None):
    return [e for e in result.trace if e.path and (role is None or e.kind==role) and (id is None or e.semantic_id==id)]


class PacketRendererSourceTests(unittest.IsolatedAsyncioTestCase):
    # packet/renderer.spec.ts literal register positions and source styles defaults.
    async def test_eight_bit_field_ascending_x_and_width(self):
        r=await picture('packet\n0-7: "DATA"');b=path_bounds(paths(r,'shape','packet-0')[0].path)
        self.assertAlmostEqual(b.x,next(e.box.x for e in r.trace if e.kind=='bit-number' and e.text=='0'));self.assertAlmostEqual(b.width,251);self.assertEqual(len([e for e in r.trace if e.kind=='bit-number']),2);self.assertIn('DATA',visible(r))
    async def test_eight_bit_field_descending_mirrors_row(self):
        r=await picture('packet\n0-7: "DATA"',{'packet':{'bitOrder':'descending'}});b=path_bounds(paths(r,'shape','packet-0')[0].path)
        self.assertAlmostEqual(b.x,769);self.assertAlmostEqual(b.width,251);bits=[e for e in r.trace if e.kind=='bit-number'];self.assertEqual([e.text for e in sorted(bits,key=lambda e:e.box.x)],['7','0'])
    async def test_show_bits_false_preserves_fields_and_omits_numbers(self):
        for order in ('ascending','descending'):
            with self.subTest(bitOrder=order):
                r=await picture('packet\n0-7: "DATA"',{'packet':{'showBits':False,'bitOrder':order}});self.assertEqual([e for e in r.trace if e.kind=='bit-number'],[]);self.assertIn('DATA',visible(r));self.assertEqual(len(paths(r,id='packet-0')),1)
    async def test_packet_theme_variables_are_renderer_specific(self):
        r=await picture('packet\n0-7: "DATA"',{'themeVariables':{'packet':{'labelColor':'#123456','blockFillColor':'#abcdef','blockStrokeWidth':'3'}}});block=paths(r,id='packet-0')[0];self.assertEqual(block.fill,'#abcdef');self.assertEqual(block.stroke_width,3);self.assertTrue(any(e.text=='DATA' and e.color=='#123456' for e in r.trace))


class ModelingPaintSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_class_empty_member_compartments_follow_source_config(self):
        a=await picture('classDiagram\nclass A',{'class':{'hideEmptyMembersBox':False}});b=await picture('classDiagram\nclass A',{'class':{'hideEmptyMembersBox':True}})
        self.assertEqual(len(paths(a,'compartment-divider','A')),2);self.assertEqual(len(paths(b,'compartment-divider','A')),0);self.assertIn('A',visible(a));self.assertIn('A',visible(b))
    async def test_class_member_classifiers_are_visible_format(self):
        r=await picture('classDiagram\nclass A {\n+staticCount$\n+abstractOp()*\n}')
        self.assertTrue(any(e.kind=='static-member-underline' for e in r.trace));self.assertTrue(any(e.font_style=='italic' and e.text and 'abstractOp' in e.text for e in r.trace))
    async def test_state_special_shapes_have_actual_distinct_geometry(self):
        r=await picture('stateDiagram-v2\nstate C <<choice>>\n[*] --> C\nC --> [*]')
        choice=paths(r,id='C');self.assertTrue(choice);self.assertTrue(any(any(len(contour)==5 for contour in flatten_path(e.path)) for e in choice));self.assertTrue(paths(r,id='root_start'));self.assertTrue(paths(r,id='root_end'))
    async def test_requirement_contains_has_circle_plus_and_compartment_fields(self):
        r=await picture('requirementDiagram\nrequirement R {\nid: 7\ntext: Required\n}\nelement E {\ntype: Artifact\n}\nR - contains -> E')
        self.assertTrue(any(e.kind=='containment-marker' for e in r.trace));self.assertIn('Required',visible(r));self.assertIn('Artifact',visible(r));self.assertEqual(len([e for e in r.trace if e.kind=='compartment-divider']),2)
    async def test_er_keys_comments_cardinalities_survive_table_paint(self):
        r=await picture('erDiagram\nA {\nint id PK "Primary"\nstring name\n}\nA ||--o{ B : owns')
        for text in ('id','PK','Primary','name','owns'):self.assertIn(text,visible(r))
        self.assertTrue(any(e.kind=='cardinality' or e.kind=='marker' for e in r.trace));self.assertTrue(any(e.kind=='attribute-column' for e in r.trace))
    async def test_c4_dynamic_numbers_source_relationships(self):
        r=await picture('C4Dynamic\nPerson(a,"Alice")\nSystem(b,"Billing")\nRel(a,b,"Uses")\nRel(b,a,"Replies")')
        self.assertIn('1: Uses',visible(r));self.assertIn('2: Replies',visible(r));self.assertTrue(paths(r,id='a'));self.assertTrue(paths(r,id='b'))
    async def test_usecase_actor_variants_have_source_paths(self):
        for variant in ('normal','hollow','awesome'):
            with self.subTest(variant=variant):
                r=await picture('usecase-beta\nactor User@{type: '+variant+'}\nUser --> Login');self.assertIn('User',visible(r));self.assertTrue(paths(r,id='User'))
                if variant=='hollow':self.assertTrue(any(e.fill in ('none','transparent',None) for e in paths(r,'actor-body','User')))
                if variant=='awesome':self.assertTrue(any(e.path.count('C')>=8 for e in paths(r,'actor-body','User')))
    async def test_actor_classdef_hides_glyph_but_keeps_caption_sibling(self):
        r=await picture('usecase-beta\nclassDef hidden display:none\nactor User@{icon: "test:user"}:::hidden\nUser --> Login',resources=RESOURCES)
        self.assertIn('User',visible(r,'User'));self.assertFalse(any(e.resource_id=='test:user' for e in r.trace));self.assertFalse(paths(r,'actor-icon-frame','User'))
    async def test_actor_outer_css_hides_glyph_and_caption(self):
        r=await picture('usecase-beta\nactor User@{icon: "test:user"}\nUser --> Login',{'themeCSS':'.usecase-actor {display:none !important;}'},RESOURCES)
        self.assertNotIn('User',visible(r));self.assertFalse(any(e.resource_id=='test:user' and e.opacity>0 for e in r.trace))
    async def test_actor_classdef_zero_opacity_leaves_caption_visible(self):
        r=await picture('usecase-beta\nclassDef transparent opacity:0\nactor User@{icon: "test:user"}:::transparent\nUser --> Login',resources=RESOURCES)
        self.assertIn('User',visible(r,'User'));self.assertFalse(any(e.resource_id=='test:user' and e.opacity>0 for e in r.trace))
    async def test_actor_explicit_icon_is_real_resource(self):
        r=await picture('usecase-beta\nactor User@{icon: "test:user"}\nUser --> Login',resources=RESOURCES)
        self.assertTrue(any(e.resource_id=='test:user' and e.opacity>0 for e in r.trace));self.assertIn('User',visible(r));self.assertIn('Login',visible(r))


class HierarchyPaintSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_tree_view_preorder_rows_and_description_column(self):
        r=await picture('treeView-beta\nroot/\n  A ## First\n  B ## Second');a=[e for e in r.trace if e.text=='A'][0];b=[e for e in r.trace if e.text=='B'][0];one=[e for e in r.trace if e.text=='First'][0];two=[e for e in r.trace if e.text=='Second'][0]
        self.assertLess(a.box.y,b.box.y);self.assertAlmostEqual(one.box.x,two.box.x);self.assertGreater(one.box.x,a.box.x+a.box.width);self.assertTrue(any(e.kind=='tree-trunk' for e in r.trace))
    async def test_tree_explicit_builtin_icon_works_when_showicons_false(self):
        r=await picture('treeView-beta\nroot/ icon(folder)\n  file icon()',{'treeView':{'showIcons':False}})
        self.assertTrue(any(e.kind=='asset' for e in r.trace));self.assertIn('file',visible(r))
    async def test_mindmap_source_icon_metadata_does_not_invent_glyph(self):
        r=await picture('mindmap\nroot\n  child\n  ::icon(fa:book)')
        self.assertIn('child',visible(r));self.assertFalse(any(e.resource_id=='fa:book' for e in r.trace))
    async def test_mindmap_circle_is_actual_containing_circle(self):
        r=await picture('mindmap\nroot((Root))\n  child[Leaf]');g=r.layout.nodes['0'];self.assertAlmostEqual(g.width,g.height);self.assertIn('Root',visible(r));self.assertIn('Leaf',visible(r));self.assertTrue(paths(r,id='0'))

    async def test_mindmap_explicit_tidy_uses_actual_two_sided_tree(self):
        r=await picture('mindmap\nRoot\n  First\n  Second',{'layout':'tidy-tree'});root=r.layout.nodes['0'];left=r.layout.nodes['1'];right=r.layout.nodes['2']
        self.assertLess(left.x+left.width/2,root.x+root.width/2);self.assertGreater(right.x+right.width/2,root.x+root.width/2);self.assertIn('First',visible(r));self.assertIn('Second',visible(r))
    async def test_mindmap_scoped_layout_does_not_replace_source_root_default(self):
        r=await picture('mindmap\nRoot\n  Child',{'mindmap':{'layout':'elk'}})
        self.assertEqual(r.layout.engine,'native-cose-bilkent');self.assertIn('Root',visible(r));self.assertIn('Child',visible(r))


class StructuresPaintSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_kanban_tickets_assignees_and_priority_are_visible(self):
        r=await picture('kanban\nTodo\n  item[Implement]@{ticket: T-1, assigned: Alice, priority: High}')
        for text in ('Todo','Implement','T-1','Alice'):self.assertIn(text,visible(r))
        self.assertTrue(any(e.kind=='priority' and e.stroke in ('orange','#ffa500') for e in r.trace))
    async def test_kanban_handdrawn_does_not_draw_priority_line_source_branch(self):
        r=await picture('kanban\nTodo\n  item[Implement]@{priority: High}',{'look':'handDrawn'})
        # Historical method name retained: source getData omits item.look;
        # only section inherits look. The original omission expectation was wrong.
        self.assertTrue(any(e.kind=='priority' for e in r.trace));self.assertFalse(any(e.kind=='kanban-item-hachure' for e in r.trace));self.assertIn('Implement',visible(r))
    async def test_block_spans_and_nested_grid_draw_all_labels(self):
        r=await picture('block\ncolumns 3\nA["Wide"]:2\nB["Narrow"]\nblock:Nested\n columns 2\n C["Child one"] D["Child two"]\nend')
        for text in ('Wide','Narrow','Child one','Child two'):self.assertIn(text,visible(r))
        layout=dict(r.layout[1]);self.assertGreater(layout['A'].width,layout['B'].width);self.assertLessEqual(layout['Nested'].x,layout['C'].x);self.assertGreaterEqual(layout['Nested'].x+layout['Nested'].width,layout['D'].x+layout['D'].width)
    async def test_architecture_internal_icon_and_text_are_static_content(self):
        r=await picture('architecture-beta\nservice api(server)[API]\nservice db(database)[Database]\napi:R -- L:db')
        self.assertIn('API',visible(r));self.assertIn('Database',visible(r));self.assertTrue(any(e.kind=='asset' for e in r.trace));self.assertTrue(paths(r,'edge','architecture-edge-0'))
    async def test_architecture_service_container_hides_icon_and_caption(self):
        r=await picture('architecture-beta\nservice api(test:user)[API]',{'themeCSS':'.architecture-service {opacity:0;}'},RESOURCES)
        self.assertNotIn('API',visible(r));self.assertFalse(any(e.semantic_id=='api' and e.opacity>0 for e in r.trace))
    async def test_architecture_node_bkg_hides_only_frame_not_group_title_icon(self):
        r=await picture('architecture-beta\ngroup g(cloud)[Cloud]\nservice api(server)[API] in g',{'themeCSS':'.node-bkg {display:none;}'})
        self.assertIn('Cloud',visible(r));self.assertIn('API',visible(r));self.assertFalse(paths(r,'architecture-group','g'));self.assertTrue(any(e.kind=='asset' and e.semantic_id in ('api','g') for e in r.trace))
    async def test_architecture_icon_text_uses_real_clip_and_ellipsis(self):
        r=await picture('architecture-beta\nservice api "One two three four five six seven eight nine ten eleven twelve thirteen fourteen"[API]')
        self.assertTrue(any(e.clip is not None for e in r.trace if e.semantic_id=='api'));self.assertNotIn('fourteen',visible(r));self.assertTrue(all(e.box.width<=80 for e in r.trace if e.kind=='icon-text'));self.assertIn('API',visible(r))


class ExplicitSwimlaneSourceTests(unittest.IsolatedAsyncioTestCase):
    SOURCE='classDiagram\nnamespace Outer {\n class A\n namespace Inner {\n class B\n }\n}\nclass Loose\nA --> Loose'
    async def test_generic_layout_draws_source_lane_and_default_lane(self):
        r=await picture(self.SOURCE,{'layout':'swimlane','class':{'hierarchicalNamespaces':True}});lanes={e.semantic_id for e in r.trace if e.kind=='swimlane-body'}
        self.assertEqual(lanes,{'Outer','__swimlane_default__'});self.assertTrue(paths(r,'namespace','Outer.Inner'));self.assertFalse(paths(r,'namespace','Outer'));self.assertIn('Loose',visible(r));self.assertIn('A',visible(r));self.assertIn('B',visible(r))
    async def test_er_swimlane_duplicate_terminal_points_keep_cardinality_markers(self):
        for direction in ('TB','LR'):
            with self.subTest(direction=direction):
                r=await picture('erDiagram\ndirection '+direction+'\nsubgraph Lane\nA\nB\nend\nA ||--o{ Outside : relation',{'layout':'swimlane'})
                self.assertIn('relation',visible(r));self.assertIn('Outside',visible(r))
                self.assertGreaterEqual(len(paths(r,id='erEdge0')),5)

    async def test_lr_source_lane_title_is_really_rotated(self):
        r=await picture('classDiagram\ndirection LR\nnamespace Lane {\nclass A\n}\nclass B\nA --> B',{'layout':'swimlane'})
        titles=[c for c in r.annotations.commands if c.role=='swimlane-label' and c.semantic_id=='Lane-label'];self.assertEqual(len(titles),1);self.assertEqual(titles[0].values[3],-90);self.assertTrue(paths(r,'swimlane-title','Lane'))
