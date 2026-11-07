"""Independent config.ts readAppearance/updateCurrentConfig regression contracts.

Expected values follow the fixed source's layer order and palette rebuild guard,
not the Python resolver. See config.appearance.spec.ts:196-219 and config.ts.
"""
import unittest

from py_mermaid.parsing.preprocess import preprocess_diagram
from py_mermaid.runtime.configuration import resolve


def resolved(site=None, directive=None, kind='classDiagram'):
    import json
    source = ('%%{init: ' + json.dumps(directive) + '}%%\n' if directive else '') + kind
    return resolve(preprocess_diagram(source), kind, site)


class AppearanceGapContracts(unittest.TestCase):
    def test_flowchart_accepts_unused_declared_diagram_sections_in_site_config(self):
        # Mermaid setSiteConfig stores the whole MermaidConfig. Drawing a
        # flowchart must not reject valid settings belonging to another kind.
        from py_mermaid import parse
        for section in ('sequence', 'class', 'gantt', 'packet', 'er'):
            with self.subTest(section=section):
                diagram = parse('flowchart LR\nA --> B', config={section: {'theme': 'dark'}, 'fontWeight': 700})
                self.assertEqual([node.id for node in diagram.nodes], ['A', 'B'])
                self.assertEqual(diagram.config.theme, 'redux-color')

    def test_explicit_elk_parser_retains_detected_diagram_identity(self):
        # Diagram.fromText returns new Diagram(type, ...); the explicit ELK
        # detector has its own id even though both entries share FlowDB.
        from py_mermaid import parse
        self.assertEqual(parse('flowchart-elk TD\nA --> B').diagram_type, 'flowchart-elk')
        self.assertEqual(parse('flowchart TD\nA --> B').diagram_type, 'flowchart-v2')

    def test_invalid_scoped_look_falls_through_to_same_layer_root(self):
        c = resolved({'look': 'classic', 'class': {'look': 'not-a-look'}})
        self.assertEqual(c['look'], 'classic')

    def test_invalid_directive_look_falls_through_to_site(self):
        c = resolved({'look': 'handDrawn'}, {'look': 'not-a-look'})
        self.assertEqual(c['look'], 'handDrawn')

    def test_invalid_root_look_falls_through_to_diagram_default(self):
        self.assertEqual(resolved({'look': 'not-a-look'})['look'], 'neo')
        self.assertEqual(resolved({'look': 'not-a-look'}, kind='info')['look'], 'classic')

    def test_resolved_appearance_keeps_existing_section_in_step(self):
        c = resolved({'look': 'classic', 'theme': 'dark', 'layout': 'elk.force',
                      'class': {'look': 'not-a-look', 'theme': 'not-a-theme', 'layout': 'elk.stress'}})
        for key in ('look', 'theme', 'layout'):
            self.assertEqual(c['class'][key], c[key])
        # resolveAppearance only synchronizes a section key already present.
        self.assertNotIn('layout', resolved({'layout': 'elk.force'})['class'])

    def test_null_directive_theme_keeps_dark_site_palette(self):
        c = resolved({'theme': 'dark'}, {'theme': 'null'})
        self.assertEqual(c['theme'], 'null')
        self.assertEqual(c['themeVariables']['mainBkg'], '#1f2020')

    def test_unknown_root_theme_is_normalized_before_diagram_resolution(self):
        c = resolved({'theme': 'not-a-theme'})
        self.assertEqual(c['theme'], 'default')
        self.assertEqual(c['themeVariables']['mainBkg'], '#ECECFF')

    def test_directive_palette_only_does_not_recalculate_derived_values(self):
        # info has no diagram theme default: cfg.theme equals siteCfg.theme,
        # and sumOfDirectives.theme is absent, so source does not updateColors.
        c = resolved({'theme': 'default'}, {'themeVariables': {'primaryColor': '#112233'}}, kind='info')
        self.assertEqual(c['themeVariables']['primaryColor'], '#112233')
        self.assertEqual(c['themeVariables']['primaryBorderColor'], 'hsl(240, 60%, 86.2745098039%)')
        base = resolved({'theme': 'base'}, {'themeVariables': {'primaryColor': '#112233'}}, kind='info')
        self.assertEqual(base['themeVariables']['mainBkg'], '#fff4dd')
        self.assertEqual(base['themeVariables']['primaryBorderColor'], 'hsl(40.5882352941, 60%, 83.3333333333%)')

    def test_empty_theme_font_family_takes_legacy_root_bridge(self):
        c = resolved({'fontFamily': 'Arial', 'themeVariables': {'fontFamily': ''}})
        self.assertEqual(c['themeVariables']['fontFamily'], 'Arial')


if __name__ == '__main__':
    unittest.main()
