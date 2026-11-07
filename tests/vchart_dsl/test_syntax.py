"""Handwritten DSL syntax assertions from RFC sections 3/7 and frozen EBNF.

No expected tree is produced by a candidate compiler/parser. Compiler-only
ownership, references and resource/type validation belong to the B suite.
P2 authoring does not execute this module's tests.
"""
from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from py_mermaid.model.flowchart import MermaidError
from py_mermaid.model.vchart_dsl import Node, SpecSpan, DslDiagnostic, LoweredVChart, dsl_error
from py_mermaid.parsing.vchart_dsl import parse_dsl
from py_mermaid.parsing.vchart_dsl.lexer import tokenize, iter_tokens


def shape(node):
    return (node.kind, node.value, tuple(shape(child) for child in node.children))


def literal(value):
    return ('literal', value, ())


class SyntaxAssertions(unittest.TestCase):
    def failure(self, text, code='VCHART_DSL_SYNTAX'):
        with self.assertRaises(MermaidError) as caught:
            parse_dsl(text)
        self.assertEqual(caught.exception.code, code)
        self.assertIsNotNone(caught.exception.span)
        return caught.exception

    def body(self, text):
        return parse_dsl('vchart bar\n' + text).children[1:]


class DslLexicalContract(SyntaxAssertions):
    def test_lexer_preserves_crlf_as_one_newline_with_raw_span(self):
        tokens=tokenize('vchart bar\r\nx = 1\r\n')
        self.assertEqual([(t.kind,t.value,t.start,t.end) for t in tokens],
                         [('IDENT','vchart',0,6),('IDENT','bar',7,10),('NL','\n',10,12),
                          ('IDENT','x',12,13),('=','=',14,15),('NUMBER',1,16,17),
                          ('NL','\n',17,19),('EOF',None,19,19)])

    def test_json_escapes_and_literal_percent_directive_text(self):
        node=self.body(r'x = "A\n\t\b\f\r\"\\\/\u4e2d\ud83d\ude00 %%{literal}%%"')[0].children[0]
        self.assertEqual(node.value,'A\n\t\b\f\r"\\/中😀 %%{literal}%%')
        self.assertIs(type(node.value),str)

    def test_comment_skips_content_but_keeps_statement_newline(self):
        nodes=self.body('x = 1 %% "not a string" }\ny = "https://a/%%b"')
        self.assertEqual([n.value for n in nodes],[('x',),('y',)])
        self.assertEqual([n.children[0].value for n in nodes],[1,'https://a/%%b'])

    def test_directive_is_explicitly_rejected_outside_strings(self):
        self.failure('vchart bar\n%%{init: {}}%%','VCHART_DSL_DIRECTIVE')

    def test_unterminated_or_illegally_escaped_strings_reject(self):
        for value in ['"abc','"abc\\','"bad\\q"','"bad\\uXYZ1"','"bad\nline"','"bad\tline"']:
            with self.subTest(value=value):self.failure('vchart bar\nx = '+value)

    def test_single_quotes_backticks_and_nonascii_identifiers_reject(self):
        for source in ["x = 'a'",'x = `a`','中文 = 1','x = α']:
            with self.subTest(source=source):self.failure('vchart bar\n'+source)

    def test_json_numbers_preserve_integer_float_boolean_and_null_types(self):
        value=self.body('x = [0,-2,1.25,1e2,-0.0,true,false,null]')[0].children[0]
        self.assertEqual([n.value for n in value.children],[0,-2,1.25,100.0,-0.0,True,False,None])
        self.assertEqual([type(n.value) for n in value.children],[int,int,float,float,float,bool,bool,type(None)])

    def test_non_json_numbers_and_nonfinite_literals_reject(self):
        for value in ['NaN','Infinity','-Infinity','+1','01','-01','.2','1.','1e','1e+','1_000','0x10','1.2.3','1e309']:
            with self.subTest(value=value):self.failure('vchart bar\nx = '+value)

    def test_long_numeric_literal_rejects_with_explicit_budget_not_python_error(self):
        self.failure('vchart bar\nx = '+'9'*5000,'VCHART_DSL_BUDGET')

    def test_comment_at_eof_and_lone_cr_newline(self):
        node=parse_dsl('vchart bar\rx=1 %% final comment')
        self.assertEqual(node.children[1].children[0].value,1)
        self.assertEqual(node.end,31)


class DslSyntaxTrees(SyntaxAssertions):
    def test_header_only_eof_and_full_document_span(self):
        root=parse_dsl('vchart bar')
        self.assertEqual(shape(root),('document',None,(('header','bar',()),)))
        self.assertEqual((root.start,root.end),(0,10))
        self.assertEqual((root.children[0].start,root.children[0].end),(7,10))

    def test_bom_and_leading_blank_whitespace_preserve_original_offsets(self):
        text='\ufeff \r\n\tvchart bar\r\nx=0'
        root=parse_dsl(text)
        self.assertEqual(root.start,0);self.assertEqual(root.end,len(text))
        self.assertEqual((root.children[0].start,root.children[0].end),(12,15))

    def test_header_rejects_comment_or_yaml_preamble(self):
        # RFC3.1 allows BOM and whitespace, not a scan-forward detector.
        for text in ['%% preamble\nvchart bar','---\ntitle: X\n---\nvchart bar']:
            with self.subTest(text=text):self.failure(text)

    def test_header_requires_type_and_complete_line(self):
        for text in ['', 'vchart','bar','VChart bar','vchart\nbar','vchart bar; x=1','vchart bar extra','vchart bar {}']:
            with self.subTest(text=text):self.failure(text)

    def test_header_does_not_validate_provider_registered_type(self):
        self.assertEqual(parse_dsl('vchart UnknownProviderType').children[0].value,'UnknownProviderType')

    def test_assignment_group_paths_and_nested_statements(self):
        root=self.body('bar { style { fill = "red"; visible = true } }')[0]
        self.assertEqual(shape(root),('group',('bar',),(
            ('group',('style',),(
                ('assignment',('fill',),(literal('red'),)),
                ('assignment',('visible',),(literal(True),)))),)))

    def test_quoted_path_is_one_key_and_bracket_key_index_is_structural(self):
        nodes=self.body('"a.b" = 1\na.b[0]["中文.key"] = 2')
        self.assertEqual([n.value for n in nodes],[('a.b',),('a','b',0,'中文.key')])

    def test_path_only_accepts_unsigned_json_integer_or_string(self):
        for path in ['a[-1]','a[1.0]','a[1e0]','a[01]','a[true]','a[]','a.0','a.[0]']:
            with self.subTest(path=path):self.failure('vchart bar\n'+path+' = 1')

    def test_index_holes_and_duplicate_object_keys_are_syntax_not_lowering(self):
        nodes=self.body('axes[2].orient = "left"\nx = {a:1,a:2}')
        self.assertEqual(nodes[0].value,('axes',2,'orient'))
        self.assertEqual([m.value for m in nodes[1].children[0].children],['a','a'])

    def test_object_keys_are_not_paths_and_complete_json_empty_containers(self):
        value=self.body('x = {"a.b":[],nested:{},"":null, true: false,}')[0].children[0]
        self.assertEqual(shape(value),('object',None,(
            ('member','a.b',(('array',None,()),)),('member','nested',(('object',None,()),)),
            ('member','',(literal(None),)),('member','true',(literal(False),)))))

    def test_values_allow_nested_newlines_and_one_trailing_comma(self):
        value=self.body('x = [\n{\na\n:\n[1,2,],\n},\n]')[0].children[0]
        self.assertEqual(shape(value),('array',None,(('object',None,(
            ('member','a',(('array',None,(literal(1),literal(2))),)),)),)))

    def test_missing_commas_double_commas_and_missing_values_reject(self):
        for value in ['[1 2]','[1,,2]','[,1]','{a:1 b:2}','{,a:1}','{a:}','{a=1}','[1','{a:1']:
            with self.subTest(value=value):self.failure('vchart bar\nx = '+value)

    def test_statements_require_newline_or_semicolon(self):
        self.failure('vchart bar\nx=1 y=2')
        nodes=self.body('x=1;y=2\nz=3')
        self.assertEqual([n.value for n in nodes],[('x',),('y',),('z',)])

    def test_close_block_or_eof_terminates_last_assignment(self):
        group=self.body('a {x=1}')[0]
        self.assertEqual(group.children[0].children[0].value,1)
        self.assertEqual(self.body('x=1')[0].children[0].value,1)

    def test_unterminated_and_unexpected_blocks_reject(self):
        for source in ['a {x=1','a {','}','x = (1)','{x=1}','x = 1 + 2']:
            with self.subTest(source=source):self.failure('vchart bar\n'+source)

    def test_size_let_axis_series_and_resource_sugar_shapes(self):
        nodes=self.body('size 800 420\nlet rows = []\naxis bottom {type="band"}\nseries bar {xField="x"}\nresource svg "icon" = "<svg/>"')
        self.assertEqual([shape(n) for n in nodes],[
            ('size',None,(literal(800),literal(420))),('let','rows',(('array',None,()),)),
            ('axis','bottom',(('assignment',('type',),(literal('band'),)),)),
            ('series','bar',(('assignment',('xField',),(literal('x'),)),)),
            ('resource',('svg','icon'),(literal('<svg/>'),))])

    def test_resource_map_value_and_reference(self):
        nodes=self.body('resource map "local" = {type:"FeatureCollection",features:[]}\nlet data = $prior')
        self.assertEqual(nodes[0].value,('map','local'))
        self.assertEqual(shape(nodes[1].children[0]),('reference','prior',()))

    def test_keywords_are_ordinary_root_or_nested_property_names(self):
        nodes=self.body('size=1;let=2;axis={};series=[];resource="x"\naxis { let=3;size=4;series=5 }')
        self.assertEqual([n.value for n in nodes],[('size',),('let',),('axis',),('series',),('resource',),('axis',)])
        self.assertEqual([n.value for n in nodes[-1].children],[('let',),('size',),('series',)])

    def test_root_sugars_are_not_allowed_inside_configuration_blocks(self):
        for source in ['a {size 1 2}','a {let x=1}','a {axis left {}}','a {resource svg "x"="x"}']:
            with self.subTest(source=source):self.failure('vchart bar\n'+source)

    def test_malformed_sugars_and_reference_reject(self):
        for source in ['size 1','size "1" 2','let x 1','let "x" = 1','axis "left" {}',
                       'series bar []','resource image "x" = 1','resource svg local = "x"','x=$','x=$1']:
            with self.subTest(source=source):self.failure('vchart bar\n'+source)


class DslTableContract(SyntaxAssertions):
    def test_table_headers_and_rows_are_handwritten_tree(self):
        table=self.body('x = table(month,"收入") { ["Jan",1]\n["Feb",null] }')[0].children[0]
        self.assertEqual(shape(table),('table',('month','收入'),(
            ('array',None,(literal('Jan'),literal(1))),('array',None,(literal('Feb'),literal(None))))))

    def test_empty_table_is_valid_but_header_list_cannot_be_empty(self):
        self.assertEqual(shape(self.body('x=table(a) {}')[0].children[0]),('table',('a',),()))
        self.failure('vchart bar\nx=table(){}')

    def test_empty_column_name_remains_for_compiler_semantic_validation(self):
        table=self.body('x=table(""){[1]}')[0].children[0]
        self.assertEqual(table.value,('',))

    def test_table_columns_duplicate_and_rows_wrong_arity_reject(self):
        for text in ['table(a,a){[1,2]}','table(a,b){[1]}','table(a){[1,2]}']:
            with self.subTest(text=text):self.failure('vchart bar\nx='+text,'VCHART_DSL_TABLE_ARITY')

    def test_table_nested_cells_keep_types_and_reference(self):
        table=self.body('x=table(a,b){[{nested:[true,0]},$prior]}')[0].children[0]
        cells=table.children[0].children
        self.assertEqual(cells[0].kind,'object')
        self.assertEqual(shape(cells[1]),('reference','prior',()))

    def test_table_rows_semicolon_newline_or_close_not_commas(self):
        table=self.body('x=table(a){[1];[2]\n[3]}')[0].children[0]
        self.assertEqual([row.children[0].value for row in table.children],[1,2,3])
        for text in ['table(a){[1],[2]}','table(a){[1][2]}','table(a){1}','table(a,){[1]}','table(a){[1]']:
            with self.subTest(text=text):self.failure('vchart bar\nx='+text)


class DslSpansAndBudgets(SyntaxAssertions):
    def test_nonbmp_literal_and_reference_source_spans_are_raw_codepoints(self):
        text='vchart bar\r\nx = "😀"\r\ny = $rows'
        nodes=parse_dsl(text).children
        self.assertEqual((nodes[1].start,nodes[1].end),(12,19))
        self.assertEqual((nodes[1].children[0].start,nodes[1].children[0].end),(16,19))
        self.assertEqual((nodes[2].children[0].start,nodes[2].children[0].end),(25,30))

    def test_syntax_error_after_astral_uses_original_utf16_offset(self):
        text='vchart bar\r\nx = "😀"\r\ny = @'
        error=self.failure(text)
        self.assertEqual((error.span.start.index,error.span.start.utf16_offset),(25,26))
        self.assertEqual((error.span.start.line,error.span.start.column),(3,4))
        self.assertEqual((error.span.end.index,error.span.end.utf16_offset),(26,27))

    def test_error_helper_preserves_path_related_and_crlf_columns(self):
        text='😀\r\nab'
        related=(SpecSpan(('data',),0,1),)
        error=dsl_error(text,4,5,'bad','VCHART_DSL_REFERENCE',path=('axes',0),related=related)
        self.assertEqual(error.spec_path,('axes',0));self.assertEqual(error.related_spans,related)
        self.assertEqual((error.span.start.index,error.span.start.utf16_offset,error.span.start.line,error.span.start.column),(4,5,2,1))

    def test_document_utf8_byte_budget_counts_nonascii_bytes(self):
        with patch('py_mermaid.parsing.vchart_dsl.lexer.MAX_BYTES',20):
            self.failure('vchart bar\nx="😀😀"','VCHART_DSL_BUDGET')

    def test_streaming_token_budget_does_not_yield_beyond_limit(self):
        with patch('py_mermaid.parsing.vchart_dsl.lexer.MAX_TOKENS',4):
            tokens=iter_tokens('vchart bar\nx=1')
            yielded=[]
            with self.assertRaises(MermaidError) as caught:
                for token in tokens:yielded.append(token)
            self.assertEqual(caught.exception.code,'VCHART_DSL_BUDGET')
            self.assertLessEqual(len(yielded),4)

    def test_ast_budget_stops_before_allocating_excess_node(self):
        from py_mermaid.model.vchart_dsl import Node as RealNode
        with patch('py_mermaid.parsing.vchart_dsl.parser.MAX_VALUES',4), patch('py_mermaid.parsing.vchart_dsl.parser.Node',wraps=RealNode) as allocation:
            self.failure('vchart bar\nx=[1,2]','VCHART_DSL_BUDGET')
            self.assertEqual(allocation.call_count,4)

    def test_nested_values_and_groups_enforce_bounded_depth(self):
        for body in ['x='+'['*129+'0'+']'*129,'a {'*129+'x=0'+'}'*129]:
            with self.subTest(body=body[:15]):self.failure('vchart bar\n'+body,'VCHART_DSL_BUDGET')
        self.assertEqual(self.body('x='+'['*32+'0'+']'*32)[0].value,('x',))

    def test_nested_path_budget_is_independent_of_value_depth(self):
        self.failure('vchart bar\n'+'.'.join(['a']*129)+'=0','VCHART_DSL_BUDGET')

    def test_repeated_documents_have_no_parser_state_leak(self):
        first=parse_dsl('vchart bar\nx=1');second=parse_dsl('vchart line\nx=2')
        self.assertEqual(first.children[0].value,'bar');self.assertEqual(second.children[0].value,'line')
        self.assertEqual(first.children[1].children[0].value,1)

    def test_contracts_are_frozen_and_only_pure_values(self):
        node=Node('literal',1,(),0,1)
        with self.assertRaises(FrozenInstanceError):node.value=2
        result=LoweredVChart('{}','{}',(),(SpecSpan(('x',),0,1),),(DslDiagnostic('code','message'),))
        with self.assertRaises(FrozenInstanceError):result.spec_json='[]'

    def test_non_string_input_has_explicit_error(self):
        for text in [None,b'vchart bar',1]:
            with self.subTest(text=text):
                with self.assertRaises(MermaidError) as caught:parse_dsl(text)
                self.assertEqual(caught.exception.code,'INVALID_INPUT')
