"""P2 compilation/discovery only. This deliberately has no unittest runner."""
from pathlib import Path
import compileall
import hashlib
import json
import sys
import unittest


def main():
    root=Path(__file__).resolve().parents[3]
    sys.path.insert(0,str(root/'src'))
    assert compileall.compile_dir(str(root/'tests/bulk/b'),quiet=1)
    data=json.loads((root/'tests/bulk/cases-B.json').read_text(encoding='utf-8'))
    ids=[c['id'] for c in data['cases']]
    assert len(ids)==len(set(ids))
    for case in data['cases']:
        assert case['source'] and case['features']
        assert case['expect'] in ('render','syntax_error','error','upstream_defect','excluded_by_static_scope')
        origin=case['origin'];path=root/'.local/upstream-mermaid'/origin['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==origin['sha256']
    loader=unittest.TestLoader()
    suite=loader.discover(str(root/'tests/bulk/b'),pattern='test_*.py',top_level_dir=str(root/'tests/bulk'))
    assert not loader.errors,loader.errors
    def flatten(s):
        for t in s:
            if isinstance(t,unittest.TestSuite):yield from flatten(t)
            else:yield t.id()
    methods=list(flatten(suite))
    assert not any('_FailedTest' in m for m in methods),methods
    assertions=json.loads((root/'references/bulk-B-assertions.json').read_text(encoding='utf-8'))
    assert len(methods)==assertions['methodCount'],(len(methods),assertions['methodCount'])
    result={'status':'MECHANICAL_SUCCESS_NOT_BEHAVIOR','methodsCollected':len(methods),'fixtures':len(ids),
            'fixturesByKind':assertions['fixturesByKind'],'sourceFilesInventoried':len(assertions['fixedSourceInventory']),
            'behaviorExecuted':False,'parseBuildLayoutRenderCalled':False,'oracleOrNativeCalled':False,
            'testIDs':methods}
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
