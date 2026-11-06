"""Deferred test helpers. Expected values live in handwritten source tables."""
from dataclasses import is_dataclass,fields
from pathlib import Path
import json
import unittest
from py_mermaid.runtime.registry import parse_diagram
from py_mermaid.model.flowchart import MermaidError


def plain(value):
    if is_dataclass(value):return {f.name:plain(getattr(value,f.name)) for f in fields(value)}
    if isinstance(value,(tuple,list)):return [plain(v) for v in value]
    if isinstance(value,dict):return {k:plain(v) for k,v in value.items()}
    return value


def select(value,path):
    parts=path.split('.');i=0
    while i<len(parts):
        part=parts[i]
        if isinstance(value,(tuple,list)):
            if part.isdigit():value=value[int(part)];i+=1;continue
            found=[]
            for end in range(len(parts),i,-1):
                name='.'.join(parts[i:end]);found=[v for v in value if str(getattr(v,'id',None))==name or str(getattr(v,'name',None))==name]
                if len(found)==1:value=found[0];i=end;break
            else:raise KeyError(path)
        elif isinstance(value,dict):value=value[part];i+=1
        else:value=getattr(value,part);i+=1
    return value



class SourceCase(unittest.TestCase):
    def check_case(self,case):
        if 'errors' in case:
            with self.assertRaises(MermaidError) as caught:parse_diagram(case['source'],config=case.get('config'))
            self.assertIn(caught.exception.code,case['errors'])
            if 'position' in case:self.assertEqual(caught.exception.span.start.utf16_offset,case['position'])
            return
        diagram=parse_diagram(case['source'],config=case.get('config'))
        self.assertEqual(diagram.kind,case['kind'])
        for path,expected in case.get('checks',{}).items():
            with self.subTest(field=path):self.assertEqual(plain(select(diagram.model,path)),expected)
        for path,expected in case.get('lengths',{}).items():
            with self.subTest(length=path):self.assertEqual(len(select(diagram.model,path)),expected)
        for path in case.get('absent',[]):
            with self.subTest(absent=path),self.assertRaises((KeyError,AttributeError)):select(diagram.model,path)


def install_cases(namespace,kinds):
    data=json.loads(Path(__file__).with_name('language_cases.json').read_text(encoding='utf-8'))
    for case in data['cases']:
        if case['kind'] not in kinds:continue
        def body(self,case=case):self.check_case(case)
        body.__doc__=case['origin']['symbol']+' ['+case['origin']['path']+']'
        body.__name__='test_'+case['id'].replace('-','_').replace('.','_')
        namespace[body.__name__]=body
