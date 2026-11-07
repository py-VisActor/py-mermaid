"""Independent v1 lowering contracts from RFC sections 2/3/6 and EBNF.

P2 authored without executing parser/compiler. Expected objects are handwritten,
never derived from the implementation or a rendered provider scene. Provider
option support is deliberately separate from lossless syntax lowering.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from py_mermaid.model.flowchart import MermaidError
from py_mermaid.model.vchart_dsl import MAX_BYTES, MAX_DEPTH, MAX_VALUES, Node
from py_mermaid.parsing.vchart_dsl.compiler import lower_dsl
from py_mermaid.parsing.vchart_dsl import compiler


class CompilerContracts(unittest.TestCase):
    def spec(self, body, kind='bar'):
        return json.loads(lower_dsl('vchart '+kind+'\n'+body).spec_json)

    def reject(self, body, code, path=None):
        with self.assertRaises(MermaidError) as caught:
            lower_dsl('vchart bar\n'+body)
        self.assertEqual(caught.exception.code, code)
        if path is not None:
            self.assertEqual(caught.exception.spec_path, path)
        return caught.exception

    def test_B01_local_handwritten_golden_cases(self):
        cases=json.loads(Path(__file__).with_name('cases-compiler.json').read_text('utf8'))['cases']
        for case in cases:
            with self.subTest(case=case['id']):
                value=lower_dsl(case['text'])
                self.assertEqual(json.loads(value.spec_json),case['spec'])
                self.assertEqual(json.loads(value.maps_json),case.get('maps',{}))
                self.assertEqual(dict(value.svgs),case.get('svgs',{}))

    def test_B02_scalar_exact_types(self):
        out=self.spec('data=[false,0,true,1,null,1.5,-2,"0"]')
        self.assertEqual([type(v) for v in out['data']], [bool,int,bool,int,type(None),float,int,str])
        self.assertEqual(out['data'],[False,0,True,1,None,1.5,-2,'0'])

    def test_B03_empty_containers_remain_distinct(self):
        out=self.spec('a={}; b=[]; c=""')
        self.assertIs(type(out['a']),dict)
        self.assertIs(type(out['b']),list)
        self.assertEqual(out['c'],'')

    def test_B04_object_order_not_alphabetized(self):
        out=self.spec('data={z:[1],a:[2],m:[3]}','sequenceScatterLink')
        self.assertEqual(list(out['data']),['z','a','m'])

    def test_B05_numeric_frame_keys_preserved_for_provider_js_order(self):
        out=self.spec('data={"z":[1],"10":[2],"2":[3],"a":[4]}','sequenceScatterLink')
        self.assertEqual(list(out['data']),['z','10','2','a'])
        self.assertEqual(out['data']['2'],[3])

    def test_B06_quoted_path_keys_not_split(self):
        self.assertEqual(self.spec('"a.b"["[0]"][""]=5'),{'type':'bar','a.b':{'[0]':{'':5}}})

    def test_B07_literal_dotted_key_differs_from_nested_path(self):
        self.assertEqual(self.spec('"a.b"=1; a.b=2'),{'type':'bar','a.b':1,'a':{'b':2}})

    def test_B08_direct_index_assignment(self):
        self.assertEqual(self.spec('a[0]=1; a[1]=2'),{'type':'bar','a':[1,2]})

    def test_B09_nested_arrays_direct_whole_elements(self):
        self.assertEqual(self.spec('a[0]=[1]; a[1]=[false,0]'),{'type':'bar','a':[[1],[False,0]]})

    def test_B10_nested_indexed_containers(self):
        self.assertEqual(self.spec('a[0][0].v=1; a[0][1].v=2'),{'type':'bar','a':[[{'v':1},{'v':2}]]})

    def test_B11_index_holes_rejected(self):
        self.reject('a[1]=0','VCHART_DSL_PATH_CONFLICT',('a',1))

    def test_B12_later_index_holes_rejected(self):
        self.reject('a[0]=0; a[2]=2','VCHART_DSL_PATH_CONFLICT',('a',2))

    def test_B13_duplicate_same_scalar_even_identical(self):
        err=self.reject('a=0; a=0','VCHART_DSL_DUPLICATE_WRITE',('a',))
        self.assertTrue(err.related_spans)

    def test_B14_duplicate_object_member(self):
        self.reject('a={x:false,x:0}','VCHART_DSL_DUPLICATE_WRITE',('a','x'))

    def test_B15_atomic_parent_rejects_descendant(self):
        for value in ('{}','[]','0','false','null'):
            with self.subTest(value=value):
                self.reject('a='+value+'; a.b=1','VCHART_DSL_PATH_CONFLICT',('a','b'))

    def test_B16_opened_parent_rejects_whole_replacement(self):
        self.reject('a.b=1; a={b:1}','VCHART_DSL_PATH_CONFLICT',('a',))

    def test_B17_empty_group_is_still_owned_container(self):
        self.reject('a {}; a={}','VCHART_DSL_PATH_CONFLICT',('a',))

    def test_B18_reopen_group_with_disjoint_leaves(self):
        self.assertEqual(self.spec('a {x=1}; a {y=2}'),{'type':'bar','a':{'x':1,'y':2}})

    def test_B19_reopen_group_duplicate_leaf(self):
        self.reject('a {x=1}; a {x=2}','VCHART_DSL_DUPLICATE_WRITE',('a','x'))

    def test_B20_container_type_conflict(self):
        self.reject('a[0].x=1; a.b=2','VCHART_DSL_PATH_CONFLICT')

    def test_B21_root_header_owns_type(self):
        self.reject('type="bar"','VCHART_DSL_DUPLICATE_WRITE',('type',))

    def test_B22_header_does_not_own_nested_type(self):
        self.assertEqual(self.spec('x.type="custom"')['x'],{'type':'custom'})

    def test_B23_size_sets_both_and_preserves_numeric_types(self):
        out=self.spec('size 400 300.5')
        self.assertEqual(out,{'type':'bar','width':400,'height':300.5})
        self.assertIs(type(out['width']),int)

    def test_B24_size_duplicate_in_both_orders(self):
        for body in ('size 400 300; width=400','height=300; size 400 300'):
            with self.subTest(body=body):self.reject(body,'VCHART_DSL_DUPLICATE_WRITE')

    def test_B25_axis_append_order_and_body(self):
        self.assertEqual(self.spec('axis right {max=10}; axis bottom {visible=false}')['axes'],
                         [{'orient':'right','max':10},{'orient':'bottom','visible':False}])

    def test_B26_series_append_order_and_nested_body(self):
        self.assertEqual(self.spec('series line {point {visible=false}}; series bar {xField="x"}')['series'],
                         [{'type':'line','point':{'visible':False}},{'type':'bar','xField':'x'}])

    def test_B27_axis_owned_orient(self):
        self.reject('axis bottom {orient="left"}','VCHART_DSL_DUPLICATE_WRITE',('axes',0,'orient'))

    def test_B28_series_owned_type(self):
        self.reject('series bar {type="line"}','VCHART_DSL_DUPLICATE_WRITE',('series',0,'type'))

    def test_B29_append_and_indexed_arrays_cannot_mix(self):
        for body in ('axis bottom {}; axes[1]={orient:"left"}',
                     'axes[0]={orient:"left"}; axis bottom {}',
                     'series line {}; series[0].xField="x"'):
            with self.subTest(body=body):self.reject(body,'VCHART_DSL_PATH_CONFLICT')

    def test_B30_literal_and_append_arrays_cannot_mix(self):
        for body in ('axes=[]; axis bottom {}','axis bottom {}; axes=[]'):
            with self.subTest(body=body):self.reject(body,'VCHART_DSL_PATH_CONFLICT')

    def test_B31_property_named_keyword_not_rewritten(self):
        self.assertEqual(self.spec('size={x:1}; let=2; resource=3; series=[{type:"custom"}]'),
                         {'type':'bar','size':{'x':1},'let':2,'resource':3,'series':[{'type':'custom'}]})

    def test_B32_table_nested_cells_and_empty_table(self):
        self.assertEqual(self.spec('a=table(k,v){[false,{x:[0,null]}];[1,[]]}; b=table(k){}')['a'],
                         [{'k':False,'v':{'x':[0,None]}},{'k':1,'v':[]}])
        self.assertEqual(self.spec('a=table(k){}')['a'],[])

    def test_B33_table_arity_rejects_short_and_long(self):
        for row in ('[1]','[1,2,3]'):
            with self.subTest(row=row):self.reject('a=table(x,y){'+row+'}','VCHART_DSL_TABLE_ARITY')

    def test_B34_table_duplicate_and_empty_header(self):
        for header in ('x,x','""'):
            with self.subTest(header=header):self.reject('a=table('+header+'){}','VCHART_DSL_TABLE_ARITY')

    def test_B35_let_reference_exact_values(self):
        self.assertEqual(self.spec('let rows=[false,0,{},[]]; a=$rows'),
                         {'type':'bar','a':[False,0,{},[]]})

    def test_B36_reference_object_order(self):
        self.assertEqual(list(self.spec('let frames={z:[],a:[]}; data=$frames')['data']),['z','a'])

    def test_B37_multiple_ref_uses_deep_independent_json_values(self):
        out=self.spec('let x={a:[{n:1}]}; first=$x; second=$x')
        out['first']['a'][0]['n']=9
        self.assertEqual(out['second'],{'a':[{'n':1}]})

    def test_B38_forward_self_and_undefined_references(self):
        for body in ('a=$x; let x=1','let x=$x','a=$missing'):
            with self.subTest(body=body):self.reject(body,'VCHART_DSL_REFERENCE')

    def test_B39_let_rebinding_even_identical_rejected(self):
        self.reject('let x=1; let x=1','VCHART_DSL_REFERENCE')

    def test_B40_unused_let_not_written_to_spec(self):
        self.assertEqual(self.spec('let ignored={type:"custom",data:[]}; x=1'),{'type':'bar','x':1})

    def test_B41_ref_source_map_uses_original_token_and_declaration(self):
        text='vchart bar\nlet v={a:[false]}; data=$v'
        out=lower_dsl(text)
        spans=[s for s in out.source_map if s.path==('data','a',0)]
        self.assertEqual(len(spans),1)
        s=spans[0]
        self.assertEqual(text[s.start:s.end],'$v')
        self.assertEqual(text[s.declaration_start:s.declaration_end],'let v={a:[false]}')

    def test_B42_unicode_source_spans_are_codepoints(self):
        text='vchart bar\n"\U0001f642"=0; data={"\u4e2d":1}'
        out=lower_dsl(text)
        span=next(s for s in out.source_map if s.path==('data','\u4e2d'))
        self.assertEqual(text[span.start:span.end],'1')
        head=next(s for s in out.source_map if s.path==('type',))
        self.assertEqual(text[head.start:head.end],'bar')

    def test_B43_resources_separate_namespaces(self):
        out=lower_dsl('vchart map\nresource map "x"={type:"FeatureCollection",features:[]}; resource svg "x"="<svg/>"; map="x"')
        self.assertEqual(json.loads(out.spec_json),{'type':'map','map':'x'})
        self.assertEqual(json.loads(out.maps_json),{'x':{'type':'FeatureCollection','features':[]}})
        self.assertEqual(out.svgs,(('x','<svg/>'),))

    def test_B44_resource_duplicate_same_kind_rejected(self):
        for kind,value in (('map','{}'),('svg','"<svg/>"')):
            with self.subTest(kind=kind):
                self.reject('resource '+kind+' "x"='+value+'; resource '+kind+' "x"='+value,
                            'VCHART_DSL_RESOURCE_CONFLICT')

    def test_B45_resource_type_not_coerced(self):
        for body in ('resource map "x"=[]','resource svg "x"={}'):
            with self.subTest(body=body):self.reject(body,'INVALID_RESOURCE')

    def test_B46_resource_spans_have_namespace_and_name(self):
        out=lower_dsl('vchart map\nresource map "x"={a:1}; resource svg "x"="<svg/>"')
        self.assertTrue(any(s.namespace=='map' and s.path==('x','a') for s in out.source_map))
        self.assertTrue(any(s.namespace=='svg' and s.path==('x',) for s in out.source_map))

    def test_B47_unknown_fields_and_type_forwarded_without_provider_call(self):
        self.assertEqual(self.spec('unknown={animation:true,nested:[null,{},[]]}','futureType'),
                         {'type':'futureType','unknown':{'animation':True,'nested':[None,{},[]]}})

    def test_B48_public_budget_constants(self):
        self.assertEqual((MAX_DEPTH,MAX_VALUES,MAX_BYTES),(128,1_000_000,8*1024*1024))

    def test_B49_reference_expansion_count_budget(self):
        with patch.object(compiler,'MAX_VALUES',30):
            self.reject('let a=[1,2,3,4,5,6]; data=[$a,$a,$a,$a,$a]', 'VCHART_DSL_BUDGET')

    def test_B50_serialized_expansion_byte_budget(self):
        # Input is below128 bytes, copied output is well above128 bytes.
        body='let a="'+('x'*40)+'"; data=[$a,$a,$a,$a]'
        self.assertLess(len(('vchart bar\n'+body).encode()),128)
        with patch.object(compiler,'MAX_BYTES',128):self.reject(body,'VCHART_DSL_BUDGET')

    def test_B51_ast_supplied_cannot_bypass_expansion_depth(self):
        node=Node('literal',0)
        for _ in range(129):node=Node('array',children=(node,))
        ast=Node('document',children=(Node('header','bar'),Node('assignment',('data',),(node,))))
        with self.assertRaises(MermaidError) as error:lower_dsl('',ast)
        self.assertEqual(error.exception.code,'VCHART_DSL_BUDGET')

    def test_B52_nonfinite_supplied_ast_rejected(self):
        for n in (float('inf'),float('-inf'),float('nan')):
            with self.subTest(n=n):
                ast=Node('document',children=(Node('header','bar'),Node('assignment',('x',),(Node('literal',n),))))
                with self.assertRaises(MermaidError):lower_dsl('',ast)

    def test_B53_source_byte_budget_checks_utf8(self):
        with patch.object(compiler,'MAX_BYTES',16):
            self.reject('x="\u4e2d\u4e2d\u4e2d\u4e2d"','VCHART_DSL_BUDGET')

    def test_B54_error_related_spans_locate_prior_write(self):
        text='vchart bar\na=1; a=2'
        with self.assertRaises(MermaidError) as caught:lower_dsl(text)
        old=caught.exception.related_spans[0]
        self.assertEqual(text[old[0]:old[1]],'a=1')
        self.assertEqual(text[caught.exception.span.start.index:caught.exception.span.end.index],'a=2')

    def test_B55_group_header_does_not_sort_new_member_order(self):
        out=self.spec('a {z=0}; a {b=1}; a.a=2')
        self.assertEqual(list(out['a']),['z','b','a'])


if __name__=='__main__':
    unittest.main()
