"""Source: config.spec.ts, diagramAPI.spec.ts, preprocess.ts and native API contract.

Inputs/expected values come from the locked upstream and public static policy;
module import only defines tests. No candidate snapshots are expected values.
"""
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import unittest

from py_mermaid import parse, MermaidError
from py_mermaid.parsing.preprocess import preprocess_diagram
from py_mermaid.runtime.configuration import resolve, defaults
from py_mermaid.runtime.common import config_dict, error, make_diagram, utf16_length
from py_mermaid.runtime import registry, layouts


class ConfigurationContracts(unittest.TestCase):
    def test_source_default_swimlane_layering_and_preset_elision(self):
        c=defaults()
        self.assertTrue(c['swimlane']['ignoreCrossLaneEdges'])
        self.assertTrue(c['swimlane']['optimizeRanksByCrossings'])
        self.assertFalse(c['swimlane']['automaticLaneOrdering'])
        self.assertNotIn('nodePlacementStrategy', c['elk'])
        self.assertNotIn('nodePlacementAlignment', c['elk'])
        self.assertNotIn('padding', c['class'])

    def test_secure_keys_from_site_resist_directive_overrides(self):
        d=preprocess_diagram('%%{init: {"fontFamily":"baf","fontSize":54321,"securityLevel":"loose"}}%%\ninfo')
        c=resolve(d,'info',{'fontFamily':'foo-font','fontSize':12345,'securityLevel':'strict',
                            'secure':['securityLevel','fontSize']})
        self.assertEqual(c['fontFamily'],'baf')
        self.assertEqual(c['fontSize'],12345)
        self.assertEqual(c['securityLevel'],'strict')

    def test_railroad_aliases_retain_directive_font_configuration(self):
        d=preprocess_diagram('%%{init: {"railroad":{"fontSize":18,"fontFamily":"Courier New"}}}%%\nrailroad-ebnf-beta')
        for kind in ('railroad','railroadEbnf','railroadAbnf','railroadPeg'):
            with self.subTest(kind=kind):
                c=resolve(d,kind)
                self.assertEqual(c['_diagramConfigKey'],'railroad')
                self.assertEqual(c['railroad']['fontSize'],18)
                self.assertEqual(c['railroad']['fontFamily'],'Courier New')

    def test_scoped_source_theme_look_layout_precedence(self):
        d=preprocess_diagram('%%{init: {"theme":"forest","class":{"theme":"neutral","layout":"elk.force","look":"classic"}}}%%\nclassDiagram')
        c=resolve(d,'classDiagram',{'theme':'dark','class':{'theme':'base','layout':'elk.stress','look':'neo'}})
        self.assertEqual((c['theme'],c['layout'],c['look']),('neutral','elk.force','classic'))
        self.assertTrue(c['_explicitLayout']);self.assertFalse(c['_explicitRootLayout'])
        self.assertEqual(c['_diagramConfigKey'],'class')

    def test_root_layout_explicitness_is_separate_from_family_scope(self):
        d=preprocess_diagram('mindmap\n  root')
        a=resolve(d,'mindmap',{'mindmap':{'layout':'tidy-tree'}})
        b=resolve(d,'mindmap',{'layout':'tidy-tree'})
        self.assertTrue(a['_explicitLayout']);self.assertFalse(a['_explicitRootLayout'])
        self.assertTrue(b['_explicitRootLayout'])

    def test_unusable_scoped_theme_falls_through_to_sibling_root(self):
        # config.ts readAppearance/isUsableAppearance skips unrenderable scoped
        # names rather than allowing them to win then choosing a new palette.
        d=preprocess_diagram('classDiagram')
        for bogus in ('unknown','constructor','__proto__'):
            with self.subTest(theme=bogus):
                c=resolve(d,'classDiagram',{'theme':'forest','class':{'theme':bogus}})
                self.assertEqual(c['theme'],'forest')

    def test_source_diagram_default_wins_global_default_but_not_user_root(self):
        d=preprocess_diagram('classDiagram')
        base=defaults()
        c=resolve(d,'classDiagram')
        self.assertEqual(c['theme'],base['class']['theme'])
        self.assertEqual(c['look'],base['class']['look'])
        explicit=resolve(d,'classDiagram',{'theme':'dark','look':'classic'})
        self.assertEqual(explicit['theme'],'dark');self.assertEqual(explicit['look'],'classic')

    def test_config_mutation_does_not_leak_between_diagrams(self):
        d=preprocess_diagram('info')
        a=resolve(d,'info');a['swimlane']['ignoreCrossLaneEdges']=False
        a['themeVariables']['primaryColor']='red'
        b=resolve(d,'info')
        self.assertTrue(b['swimlane']['ignoreCrossLaneEdges'])
        self.assertNotEqual(b['themeVariables']['primaryColor'],'red')

    def test_all_eleven_themes_compute_full_family_variables(self):
        from py_mermaid.config.themes import THEMES, get_theme_variables
        self.assertEqual(set(THEMES),{'base','dark','default','forest','neutral','neo','neo-dark','redux','redux-dark','redux-color','redux-dark-color'})
        for theme in THEMES:
            with self.subTest(theme=theme):
                c=get_theme_variables(theme,{'fontFamily':'Fixture Font'})
                self.assertEqual(c['fontFamily'],'Fixture Font')
                for key in ('primaryColor','primaryTextColor','lineColor','actorBkg','taskBkgColor','git0'):
                    self.assertIn(key,c)
                self.assertNotEqual(c['primaryColor'],c['primaryTextColor'])

    def test_input_limits_use_utf16_not_python_scalar_length(self):
        s='info 😀'
        self.assertEqual(utf16_length('😀'),2)
        with self.assertRaises(MermaidError) as caught:parse(s,config={'maxTextSize':6})
        self.assertEqual(caught.exception.code,'TEXT_LIMIT')
        for value in (True,float('nan'),float('inf'),-1):
            with self.subTest(value=value),self.assertRaises(MermaidError) as caught:
                parse('info',config={'maxTextSize':value})
            self.assertEqual(caught.exception.code,'INVALID_NUMBER')

    def test_raw_source_error_maps_crlf_directive_and_surrogate_columns(self):
        raw='---\r\ntitle: Offset\r\n---\r\n%% comment\r\ninfo\r\n😀bad'
        doc=preprocess_diagram(raw)
        offset=doc.cleaned.index('bad')
        err=error(doc,offset,'fixture')
        self.assertEqual(err.span.start.index,raw.index('bad'))
        self.assertEqual(err.span.start.line,6)
        self.assertEqual(err.span.start.column,2)
        self.assertEqual(err.span.start.utf16_offset,len(raw[:raw.index('bad')].encode('utf-16-le'))//2)

    def test_explicit_error_unknown_and_excluded_dagre_are_precise_errors(self):
        for source,config,code in (('error',None,'ERROR_DIAGRAM'),('not-a-diagram',None,'UNKNOWN_DIAGRAM'),
                ('info',{'layout':'dagre'},'UNSUPPORTED_CONFIG'),('info',{'look':'unknown'},'INVALID_CONFIG')):
            with self.subTest(source=source,config=config),self.assertRaises(MermaidError) as caught:parse(source,config=config)
            self.assertEqual(caught.exception.code,code)

    def test_provider_registration_order_replacement_and_actual_model(self):
        saved=registry._registrations.copy()
        try:
            async def build(diagram,painter):raise AssertionError('not called during parse')
            def create(doc,cfg):return make_diagram('fixture-plugin',doc,cfg,('retained',42))
            provider=SimpleNamespace(parse=create,build=build)
            registry.register_diagram('fixture-plugin',lambda text:text.startswith('fixture-plugin'),provider)
            order=registry.registered_diagrams()
            registry.register_diagram('fixture-plugin',lambda text:text.startswith('fixture-plugin'),provider)
            self.assertEqual(registry.registered_diagrams(),order)
            result=parse('fixture-plugin')
            self.assertEqual(result.model,('retained',42))
            self.assertEqual(result.kind,'fixture-plugin')
            with self.assertRaises(FrozenInstanceError):result.kind='changed'
        finally:registry._registrations.clear();registry._registrations.update(saved)

    def test_layout_registration_replacement_owns_builtin_name_without_fallback(self):
        saved=layouts._providers.copy()
        try:
            async def provider(*args,**kwargs):raise RuntimeError('source provider failure')
            for name in ('elk','swimlane'):
                order=layouts.registered_layouts()
                layouts.register_layout(name,provider)
                self.assertEqual(layouts.registered_layouts(),order)
                self.assertFalse(layouts.uses_builtin_elk(name))
                self.assertFalse(layouts.uses_builtin_swimlane(name))
                self.assertIs(layouts.load_layout(layouts.layout_definition(name)),provider)
            for name in ('dagre','dagre-wrapper',''):
                with self.subTest(name=name),self.assertRaises(MermaidError) as caught:layouts.register_layout(name,provider)
                self.assertEqual(caught.exception.code,'INVALID_REGISTRATION')
        finally:layouts._providers.clear();layouts._providers.update(saved)


if __name__=='__main__':unittest.main()
