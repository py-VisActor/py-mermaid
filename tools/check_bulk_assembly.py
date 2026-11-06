"""P1 mechanical assembly only: no diagram parsing/layout/native rendering."""
from __future__ import annotations
import ast
import compileall
import importlib
import inspect
import json
from pathlib import Path
import re
import sys
import zipfile
from run_support import ROOT, Run, write_json, source_identity


def mechanical_probe(output):
    sys.path.insert(0,str(ROOT/'src'))
    from py_mermaid.runtime.registry import provider_for
    from py_mermaid.runtime.layouts import registered_layouts,layout_definition,load_layout
    from py_mermaid.rendering.skia.scene import Painter
    scope=json.loads((ROOT/'references/bulk-scope.json').read_text('utf-8'))
    excluded=re.compile(r'[/\\]diagrams[/\\](?:charts|flows)[/\\]|[/\\]hierarchy[/\\]treemap\.py$')
    if not compileall.compile_dir(ROOT/'src/py_mermaid',quiet=1,rx=excluded):raise RuntimeError('Product compilation failed')
    providers=[];paths=[]
    for kind in scope['retainedDetectors']:
        module=provider_for(kind)
        if module is None:
            from py_mermaid.diagrams.flowchart.parser import parse_flowchart
            inspect.signature(parse_flowchart).bind('',config={})
            providers.append({'kind':kind,'provider':'legacy flowchart pipe','parserSignature':str(inspect.signature(parse_flowchart))})
            paths.append(Path(inspect.getsourcefile(parse_flowchart)).parent)
        else:
            inspect.signature(module.parse).bind(None,{})
            inspect.signature(module.build).bind(None,None)
            if not inspect.iscoroutinefunction(module.build):raise TypeError('build must be async: '+kind)
            providers.append({'kind':kind,'provider':module.__name__,'parserSignature':str(inspect.signature(module.parse)),'buildSignature':str(inspect.signature(module.build))})
            paths.append(Path(module.__file__).parent if Path(module.__file__).name=='__init__.py' else Path(module.__file__))
    layouts=[]
    for name in registered_layouts():
        definition=layout_definition(name)
        if definition.provider is not None:
            provider=load_layout(definition)
            inspect.signature(provider).bind((),(),direction='TB',parents=(),options=None,node_spacing=50,rank_spacing=50,config={},algorithm=definition.algorithm)
            layouts.append({'name':name,'provider':str(definition.provider),'signature':str(inspect.signature(provider))})
        else:layouts.append({'name':name,'provider':'published pyelk','algorithm':definition.algorithm})
    python_paths=set()
    for path in paths:
        python_paths.update(path.rglob('*.py') if path.is_dir() else (path,))
    calls=[];forwarded=[]
    for path in sorted(python_paths):
        tree=ast.parse(path.read_text('utf-8-sig'),filename=str(path))
        parents={child:parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):continue
            receiver=ast.unparse(node.func.value);method=node.func.attr
            if receiver not in ('p','painter','self.p','self.painter') or not callable(getattr(Painter,method,None)):continue
            location={'path':path.relative_to(ROOT).as_posix(),'line':node.lineno,'method':method}
            function=parents.get(node)
            while function is not None and not isinstance(function,(ast.FunctionDef,ast.AsyncFunctionDef)):function=parents.get(function)
            delegated=False
            if function is not None:
                for assignment in ast.walk(function):
                    if isinstance(assignment,ast.Assign) and any(isinstance(target,ast.Name) and target.id==receiver for target in assignment.targets) and isinstance(assignment.value,ast.Call) and isinstance(assignment.value.func,ast.Name) and assignment.value.func.id in ('TemporalPainter','Presentation'):
                        delegated=True;break
            if delegated:
                forwarded.append({**location,'reason':'source-specific presentation proxy; inspect its forwarding implementation separately'});continue
            if any(isinstance(arg,ast.Starred) for arg in node.args) or any(key.arg is None for key in node.keywords):forwarded.append(location);continue
            try:inspect.signature(getattr(Painter,method)).bind(None,*[None for arg in node.args],**{key.arg:None for key in node.keywords})
            except TypeError as exc:raise TypeError(str(path)+':'+str(node.lineno)+' Painter.'+method+': '+str(exc)) from exc
            calls.append(location)
    native_modules=[name for name in sys.modules if name=='py_skia_canvas' or name.startswith('py_skia_canvas.')]
    if native_modules:raise RuntimeError('Assembly imports unexpectedly loaded native Canvas modules: '+str(native_modules))
    write_json(output,{'schema':'py-mermaid-p1-assembly/v1','status':'mechanical_pass_only','scope':scope,
        'providers':providers,'layouts':layouts,'boundPainterCalls':calls,'dynamicForwardingCalls':forwarded,
        'parseBuildLayoutCalls':0,'nativeObjectsCreated':False,'behavioralStatus':'NOT_EVALUATED'})


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--probe':
        mechanical_probe(Path(sys.argv[2]));return 0
    with Run('BULK','P1-assembly') as run:
        run.input(ROOT/'references/bulk-scope.json')
        result=run.command('retained-provider-assembly',[sys.executable,str(Path(__file__).resolve()),'--probe',str(run.path/'artifacts/assembly.json')])
        if result['exitCode']!=0:
            print(json.dumps({'runId':run.id,'status':'FAILED','behaviorExecuted':False}));return result['exitCode']
        identity=source_identity();write_json(run.path/'artifacts/source-identity.json',identity)
        with zipfile.ZipFile(run.path/'artifacts/P1-source-candidate.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for relative in identity['files']:archive.write(ROOT/relative,relative)
        run.event('mechanical_assembly_complete',retainedDetectors=31,behaviorExecuted=False,sourceSHA256=identity['sourceTreeSha256'])
        print(json.dumps({'runId':run.id,'status':'mechanical_pass_only','sourceSHA256':identity['sourceTreeSha256'],'behaviorExecuted':False}))
    return 0


if __name__=='__main__':raise SystemExit(main())
