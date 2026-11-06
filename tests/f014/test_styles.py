"""Fixed FlowDB.compileStyles/styles2String and styles.ts static contracts.

All expected values below are literal source rules or CSS arithmetic. No
candidate scene/golden is used to manufacture expectations. First run is S4.
"""
from dataclasses import replace
import unittest
from py_mermaid import parse
from py_mermaid.model.flowchart import ResolvedStyle, MermaidError
from py_mermaid.rendering.styles import resolve_style, apply_declarations, parse_css, resolve_inline_svg_style


def graph(body, **config):
    return parse("flowchart TD\n"+body, config=config)


class StaticStyleContracts(unittest.TestCase):
    def test_inline_svg_host_css_overrides_presentation_but_not_own_inline(self):
        # diagrams/flowchart/styles.ts:162-169, styles.ts:129-132.
        base=ResolvedStyle(fill='red',stroke='none',stroke_width=0)
        diagram=graph('A[Alpha]\nstyle A fill:blue',look='classic')
        child=resolve_inline_svg_style(diagram,'node-label','A',tag='path',base=base)
        self.assertEqual((child.fill,child.stroke,child.stroke_width),(diagram.config.fill,diagram.config.stroke,diagram.config.node_stroke_width))
        self.assertEqual(apply_declarations(child,'fill:green',kind='node').fill,'green')
        rough=graph('A[Alpha]',look='handDrawn')
        self.assertEqual(resolve_inline_svg_style(rough,'node-label','A',tag='path',base=base).fill,'red')
        css=graph('A[Alpha]',look='classic',themeCSS='.node path{fill:purple!important}')
        child=resolve_inline_svg_style(css,'node-label','A',tag='path',base=base)
        self.assertEqual(apply_declarations(child,'fill:green',kind='node').fill,'purple')

    def test_class_default_node_explicit_and_local_order(self):
        diagram=graph("A[Alpha]:::hot\nclassDef default fill:#111111,color:#121212\nclassDef node fill:#222222,font-size:18px\nclassDef hot fill:#333333,color:#343434\nstyle A fill:#444444,stroke:#454545")
        shape=resolve_style(diagram,'node','A');label=resolve_style(diagram,'node-label','A')
        self.assertEqual((shape.fill,shape.stroke),('#444444','#454545'))
        self.assertEqual((label.text_color,label.font_size),('#343434',18))

    def test_local_styles_win_theme_css_important(self):
        diagram=graph('A[Alpha]\nstyle A fill:#135724', themeCSS='#A rect {fill:red!important}')
        self.assertEqual(resolve_style(diagram,'node','A').fill,'#135724')

    def test_class_declaration_append_and_local_last(self):
        diagram=graph('A:::hot\nclassDef hot fill:red\nclassDef hot fill:blue,stroke:green\nstyle A stroke:black\nstyle A stroke:#123456')
        style=resolve_style(diagram,'node','A')
        self.assertEqual((style.fill,style.stroke),('blue','#123456'))

    def test_class_paint_does_not_color_label_as_fill(self):
        diagram=graph('A[Alpha]:::hot\nclassDef hot fill:red,stroke:blue,color:green')
        self.assertEqual(resolve_style(diagram,'node','A').fill,'red')
        self.assertEqual(resolve_style(diagram,'node-label','A').text_color,'green')

    def test_svg_text_local_color_becomes_fill(self):
        diagram=graph('A[Alpha]\nstyle A color:#123456', htmlLabels=False)
        self.assertEqual(resolve_style(diagram,'node-label','A').text_color,'#123456')

    def test_default_and_per_edge_styles_and_label_color(self):
        diagram=graph('A -->|one| B -->|two| C\nlinkStyle default stroke:blue,color:green\nlinkStyle 1 stroke:red,stroke-width:5px')
        first,second=diagram.edges
        self.assertEqual(resolve_style(diagram,'edge',first.id).stroke,'blue')
        style=resolve_style(diagram,'edge',second.id)
        self.assertEqual((style.stroke,style.stroke_width),('red',5))
        self.assertEqual(resolve_style(diagram,'edge-label',first.id).text_color,'green')

    def test_named_edge_class_and_direct_metadata_animation_snapshot(self):
        diagram=graph('A e1@--> B\ne1@{animate: true}\nclassDef hot stroke:#123456,animation:slow\nclass e1 hot')
        style=resolve_style(diagram,'edge',diagram.edges[0].id)
        self.assertEqual((style.stroke,style.dash,style.dash_offset,style.line_cap),('#123456',(9,5),900,'round'))

    def test_animated_explicit_dash_and_cap_override(self):
        diagram=graph('A e1@--> B\ne1@{animate: true}\nclassDef hot stroke-dasharray:2 4,stroke-linecap:square,stroke-dashoffset:3\nclass e1 hot')
        style=resolve_style(diagram,'edge',diagram.edges[0].id)
        self.assertEqual((style.dash,style.line_cap,style.dash_offset),((2,4),'square',3))

    def test_class_animation_only_disables_neo_gap_not_metadata_dash_class(self):
        # edges.js uses class animation presence for animatedEdge (marker gap),
        # but edge-animation-fast/slow comes only from the edge metadata.
        diagram=graph('A e1@--> B\nclassDef hot animation:slow\nclass e1 hot')
        style=resolve_style(diagram,'edge',diagram.edges[0].id)
        self.assertEqual((style.dash,style.dash_offset,style.line_cap),((),0,'butt'))

    def test_stroke_source_defaults(self):
        for token,width,dash in [('==>',3.5,()),('-.->',2,(2,)),('~~~',0,())]:
            with self.subTest(token=token):
                diagram=graph('A '+token+' B')
                style=resolve_style(diagram,'edge',diagram.edges[0].id)
                self.assertEqual((style.stroke_width,style.dash),(width,dash))

    def test_static_clickable_class_css_and_hover_ignored(self):
        diagram=graph('A[Alpha]\nclick A href "https://example.com"',themeCSS='.node.clickable rect{fill:red!important}.node:hover rect{fill:blue!important}')
        self.assertEqual(resolve_style(diagram,'node','A').fill,'red')
        self.assertEqual(parse_css('.node:hover rect{fill:blue}'),())

    def test_text_shape_has_no_default_frame(self):
        diagram=graph('A@{shape: text, label: Alpha}')
        style=resolve_style(diagram,'node','A')
        self.assertEqual((style.fill,style.stroke_width,style.shadow_opacity),('none',0,0))

    def test_special_shapes_actual_static_css_and_handdrawn_pattern(self):
        # Fifteen fixed-source computed-paint cases are retained in
        # F01.4-s4-source-paint-diagnostic-20261105T092448Z-a6b4e487.
        for look in ['neo','classic','handDrawn']:
            for name in ['sm-circ','fork','anchor','note']:
                with self.subTest(name=name,look=look):
                    diagram=graph('A@{shape: '+name+'}',look=look)
                    style=resolve_style(diagram,'node','A')
                    if name=='anchor':
                        self.assertEqual(style.fill,diagram.config.edge_color)
                        self.assertEqual(style.stroke,diagram.config.stroke if look=='neo' else diagram.config.edge_color)
                        self.assertEqual(style.stroke_width,diagram.config.node_stroke_width if look=='neo' else 0)
                    elif name=='fork' and look=='handDrawn':
                        self.assertEqual((style.fill,style.stroke),(diagram.config.edge_color,diagram.config.edge_color))
                    elif name=='note' and look=='handDrawn':
                        self.assertEqual((style.fill.lower(),style.stroke.lower()),('#fff5ad','#facc15'))
                    else:
                        self.assertEqual((style.fill,style.stroke),(diagram.config.fill,diagram.config.stroke))
                        if name=='sm-circ' and look=='handDrawn':self.assertEqual(style.hachure_color,diagram.config.stroke)

    def test_collapsed_group_keeps_palette_slot_and_override(self):
        diagram=graph('subgraph G[Group]\nA\nend\nG@{view: collapsed}\nstyle G fill:#123456')
        self.assertFalse(diagram.groups)
        self.assertEqual(resolve_style(diagram,'node','G').fill,'#123456')

    def test_spacing_units_and_signed_offsets(self):
        style=apply_declarations(ResolvedStyle(font_size=20),'letter-spacing:-.1em;word-spacing:3px;stroke-dashoffset:-4px;stroke-linejoin:bevel')
        self.assertEqual((float(style.letter_spacing[:-2]),float(style.word_spacing[:-2]),style.dash_offset,style.line_join),(-2,3,-4,'bevel'))

    def test_text_transform_wrap_hyphen_and_shadow_intents(self):
        style=apply_declarations(ResolvedStyle(),'text-transform:uppercase;word-wrap:anywhere;word-break:break-all;hyphens:none;text-shadow:2px 3px 4px red,-1px 0 blue')
        self.assertEqual((style.text_transform,style.overflow_wrap,style.word_break,style.hyphens),('uppercase','anywhere','break-all','none'))
        self.assertEqual(style.text_shadows,((2,3,4,'red'),(-1,0,0,'blue')))

    def test_new_text_properties_inherit_and_initial(self):
        parent=apply_declarations(ResolvedStyle(),'letter-spacing:2px;text-transform:uppercase;text-shadow:1px 2px red')
        child=apply_declarations(ResolvedStyle(),'letter-spacing:inherit;text-transform:inherit;text-shadow:inherit',inherited=parent)
        self.assertEqual((child.letter_spacing,child.text_transform,child.text_shadows),(parent.letter_spacing,parent.text_transform,parent.text_shadows))
        fresh=apply_declarations(parent,'letter-spacing:initial;text-transform:initial;text-shadow:initial')
        self.assertEqual((float(fresh.letter_spacing[:-2]),fresh.text_transform,fresh.text_shadows),(0,'none',()))

    def test_invalid_static_css_is_explicit_and_input_immutable(self):
        initial=ResolvedStyle()
        for declarations in ['stroke-linecap:triangle','word-break:garbage','text-shadow:1px red','hyphens:auto']:
            with self.subTest(declarations=declarations),self.assertRaises(MermaidError):apply_declarations(initial,declarations)
        self.assertEqual(initial,ResolvedStyle())

if __name__=='__main__':unittest.main()
