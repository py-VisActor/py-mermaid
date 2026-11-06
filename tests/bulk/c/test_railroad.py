"""Literal assertions transcribed from all four fixed parser source specs."""
import json
import unittest
from pathlib import Path
from ._support import semantic,assert_png,assert_text_pixels

ROWS=json.loads(Path(__file__).with_name('railroad-source-cases.json').read_text('utf-8'))


class RailroadSourceCases(unittest.TestCase):
    def test_missing_semicolon_in_every_dialect(self):
        from py_mermaid import MermaidError
        for header,rule in [('railroad-beta','r=terminal("a")'),('railroad-ebnf-beta','r="a"'),('railroad-abnf-beta','r="a"'),('railroad-peg-beta','r<-"a"')]:
            with self.subTest(header=header):
                with self.assertRaises(MermaidError) as error:
                    semantic(header+'\n'+rule)
                self.assertEqual(error.exception.code,'SYNTAX_ERROR');self.assertIsNotNone(error.exception.span)

    def test_db_rule_order_retains_duplicates_while_lookup_updates(self):
        # railroadDb.addRule: rules.push always, ruleMap.set only overwrites lookup.
        m=semantic('railroad-beta\na=terminal("old"); b=terminal("B"); a=terminal("new");').model
        self.assertEqual([r.name for r in m.rules],['a','b','a'])
        self.assertEqual([r.definition.text for r in m.rules],['old','B','new'])

    def test_abnf_numeric_terminal_retains_source_not_decoded_char(self):
        for raw in ('%x41','%d65','%b1000001','%x30-39','%x41.42'):
            with self.subTest(raw=raw):
                d=semantic('railroad-abnf-beta\nr='+raw+';').model.rules[0].definition
                self.assertEqual((d.kind,d.text),('terminal',raw))

    def test_peg_predicates_are_source_special_literals(self):
        for token in ('&"a"','!"a"','.'):
            with self.subTest(token=token):
                d=semantic('railroad-peg-beta\nr <- '+token+';').model.rules[0].definition
                self.assertEqual(d.kind,'special');self.assertEqual(d.text,token.replace('&','&amp;'))

    def test_ebnf_precedence_and_grouping(self):
        d=semantic('railroad-ebnf-beta\nr = "a" "b" | ("c" "d")?;').model.rules[0].definition
        self.assertEqual(d.kind,'choice');self.assertEqual(len(d.children),2)
        self.assertEqual(d.children[0].kind,'sequence');self.assertEqual([v.text for v in d.children[0].children],['a','b'])
        self.assertEqual(d.children[1].kind,'optional');self.assertEqual(d.children[1].children[0].kind,'sequence')


def _source_method(row):
    def method(self):
        from py_mermaid import MermaidError
        if row['name'].startswith('should throw'):
            with self.assertRaises(MermaidError) as caught:semantic(row['source'])
            self.assertEqual(caught.exception.code,'UNKNOWN_DIAGRAM' if 'keyword' in row['name'] else 'SYNTAX_ERROR')
            self.assertIsNotNone(caught.exception.span);return
        diagram=semantic(row['source']);self.assertEqual(diagram.kind,row['kind']);model=diagram.model
        self.assertGreater(len(row['checks']),0,'Source expectation extraction must not degrade to success-only')
        for check in row['checks']:
            with self.subTest(source=row['sourceFile'],name=row['name'],check=check):
                value=model
                for part in check['path']:value=value[part] if isinstance(part,int) else getattr(value,part)
                self.assertEqual(len(value) if check['op']=='length' else value,check['value'].replace('&','&amp;') if isinstance(check['value'],str) and check['path'][-1]=='text' else check['value'])
    method.__doc__=row['sourceFile']+':'+str(row['line'])+' '+row['name']
    return method


for _row in ROWS:setattr(RailroadSourceCases,'test_'+_row['id'].replace('-','_'),_source_method(_row))


class RailroadNative(unittest.IsolatedAsyncioTestCase):
    async def test_source_leaf_padding_and_recursive_optional_dimensions(self):
        from py_mermaid import arender
        plain=await arender('railroad-beta\nr=terminal("alpha");',backend='cpu',config={'railroad':{'padding':10}})
        padded=await arender('railroad-beta\nr=terminal("alpha");',backend='cpu',config={'railroad':{'padding':30}})
        a=plain.layout[0][1];b=padded.layout[0][1]
        # Source terminal width/height = actual text width/height + 2*padding.
        self.assertAlmostEqual(b.width-a.width,40);self.assertAlmostEqual(b.height-a.height,40)
        self.assertAlmostEqual(a.up,a.height/2);self.assertAlmostEqual(a.down,a.height/2)
        optional=await arender('railroad-beta\nr=optional(terminal("alpha"));',backend='cpu',config={'railroad':{'padding':10,'arcRadius':10}})
        shape=optional.layout[0][1]
        self.assertAlmostEqual(shape.width-a.width,40);self.assertAlmostEqual(shape.height-a.height,20)
        self.assertAlmostEqual(shape.up-a.up,20)
        assert_png(self,plain);assert_png(self,padded);assert_png(self,optional)

    async def test_source_unconsumed_marker_toggle_does_not_invent_a_branch(self):
        from py_mermaid import arender
        source='railroad-beta\nr=terminal("alpha");'
        result=await arender(source,backend='cpu',config={'railroad':{'showMarkers':False,'compactMode':False}})
        assert_png(self,result)
        self.assertEqual(sum(e.kind=='railroad-start' for e in result.trace),1)
        self.assertEqual(sum(e.kind=='railroad-end' for e in result.trace),1)

    async def test_recursive_routes_and_visible_leaf_text_in_all_dialects(self):
        from py_mermaid import arender
        variants=[('railroad-beta','rule=sequence(terminal("Hello"),optional(nonterminal("World")),oneOrMore(special("digit")));'),('railroad-ebnf-beta','rule="Hello" [ World ] { ? digit ? };'),('railroad-abnf-beta','rule="Hello" [ World ] 1*DIGIT;'),('railroad-peg-beta','rule <- "Hello" World? ("0" / "9")+;')]
        for header,rule in variants:
            with self.subTest(header=header):
                result=await arender(header+'\n'+rule,backend='cpu');image=assert_png(self,result)
                text=[e for e in result.trace if e.text]
                joined=' '.join(e.text for e in text)
                self.assertIn('Hello',joined);self.assertIn('World',joined);self.assertIn('rule',joined)
                for event in text:
                    if event.text in ('Hello','World'):assert_text_pixels(self,image,event)
                self.assertGreater(sum(bool(e.path) for e in result.trace),4)
