"""P2 mechanical collection only. Never invokes a unittest method or renderer."""
from __future__ import annotations
import ast
import compileall
import json
from pathlib import Path
import sys
import unittest
from run_support import ROOT,write_json,source_identity


def main():
    output=Path(sys.argv[1]);sys.path.insert(0,str(ROOT/'src'))
    before=source_identity()
    if not compileall.compile_dir(ROOT/'tests/bulk',quiet=1):raise RuntimeError('Bulk test compilation failed')
    suites={};ids=[]
    def flatten(suite):
        for test in suite:
            if isinstance(test,unittest.TestSuite):yield from flatten(test)
            else:yield test
    for group in ('shared','a','b','c'):
        directory=ROOT/'tests/bulk'/group
        if not directory.is_dir():continue
        suite=unittest.TestLoader().discover(str(directory),top_level_dir=str(ROOT/'tests'))
        tests=list(flatten(suite))
        failed=[t.id() for t in tests if isinstance(t,unittest.loader._FailedTest)]
        if failed:raise RuntimeError('Collection failed: '+str(failed))
        group_ids=[t.id() for t in tests];suites[group]=len(group_ids);ids+=group_ids
    assertion_calls=0
    for path in (ROOT/'tests/bulk').rglob('test_*.py'):
        tree=ast.parse(path.read_text('utf-8-sig'))
        assertion_calls+=sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr.startswith('assert') for n in ast.walk(tree))
    if before!=source_identity():raise RuntimeError('P1 product changed during P2')
    write_json(output,{'phase':'P2','productBehaviorExecuted':False,'testMethodsExecuted':0,'collectionCounts':suites,
        'testIds':ids,'staticAssertionCallsites':assertion_calls,'callsiteNote':'Not a parameterized assertion count or coverage percentage',
        'sourceTreeSha256':before['sourceTreeSha256']})
    print(json.dumps({'collection':suites,'total':len(ids),'behaviorExecuted':False}))


if __name__=='__main__':main()
