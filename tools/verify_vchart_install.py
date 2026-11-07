"""Verify resolver-led external wheel/sdist installs using the locked release.

Every subprocess is retained by run_support.Run. The fresh environment contains
no preinstalled VChart, editable checkout, extra index, or neighbouring source.
The isolated probe uses only installed public APIs and a copied data fixture.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

from run_support import ROOT, Run, file_identity, write_json


PROBE = r'''
import builtins
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import struct
import sys


def main():
    fixture,lockfile,outdir,workspace,reportfile=map(Path,sys.argv[1:6])
    dsl_mode=sys.argv[6:]==['--dsl']
    output=outdir.resolve();output.mkdir(parents=True,exist_ok=False)
    workspace=workspace.resolve();prefix=Path(sys.prefix).resolve()
    assert sys.flags.isolated==1,'probe must run with -I'
    assert not Path.cwd().resolve().is_relative_to(workspace),'cwd must be outside workspace'
    original_import=builtins.__import__
    def guarded(name,*args,**kwargs):
        if name.split('.')[0] in {'skia','playwright','quickjs','execjs'}:
            raise AssertionError('forbidden production import: '+name)
        return original_import(name,*args,**kwargs)
    builtins.__import__=guarded
    import py_mermaid,py_vchart,py_katex,pyelk
    from py_mermaid import render_vchart,render
    from py_skia_canvas import Canvas,Image
    for module in (py_mermaid,py_vchart,py_katex,pyelk):
        path=Path(module.__file__).resolve()
        assert path.is_relative_to(prefix) and not path.is_relative_to(workspace),str(path)
    lock=json.loads(lockfile.read_text('utf-8'))
    assert metadata.version('py-visactor-vchart')==lock['version']
    raw_direct=metadata.distribution('py-visactor-vchart').read_text('direct_url.json')
    direct=json.loads(raw_direct) if raw_direct else None
    download_info=next(p['download_info'] for p in json.loads(reportfile.read_text('utf-8'))['install']
                  if p['metadata']['name'].lower().replace('_','-')=='py-visactor-vchart')
    assert download_info['url']==lock['asset']['url'],download_info
    assert download_info['archive_info']['hashes']['sha256']==lock['asset']['sha256'],download_info
    if lock['delivery']=='pypi':
        assert direct is None,'Index installs must not be replaced by direct URLs'
    else:
        assert direct['url']==lock['asset']['url'],direct
        assert direct['archive_info']['hashes']['sha256']==lock['asset']['sha256'],direct
    distributions=metadata.packages_distributions().get('py_mermaid',[])
    assert len(distributions)==1,distributions
    mermaid_distribution=distributions[0]
    requirements=metadata.requires(mermaid_distribution)
    assert any(value.replace(' ','')==lock['requirement'].replace(' ','') for value in requirements),requirements
    doc=json.loads(fixture.read_text('utf-8'));rows=doc['cases']
    assert len(rows)==68 and {r['type'] for r in rows}==set(py_mermaid.supported_vchart_types())
    results=[];dsl_results=[]
    for row in rows:
        result=render_vchart(row['spec'],backend='cpu',maps=row['maps'],svgs=row['svgs'])
        assert result.data[:8]==b'\x89PNG\r\n\x1a\n',row['id']
        dimensions=struct.unpack('>II',result.data[16:24])
        assert dimensions==(row['expected']['width'],row['expected']['height']),row['id']
        assert dimensions==(result.width,result.height),row['id']
        assert dict(result.backend)['renderer']=='CPU',row['id']
        canvas=Canvas(*dimensions);canvas.gpu=False;ctx=canvas.getContext('2d')
        ctx.drawImage(Image(result.data),0,0)
        pixels=bytes(ctx.getImageData(0,0,*dimensions).data)
        visible=sum(pixels[i+3]>16 and min(pixels[i:i+3])<250 for i in range(0,len(pixels),4))
        assert visible>=8,(row['id'],'white or invisible frame')
        for key,expected in row['expected']['geometryCounts'].items():
            actual=result.layout.get('marks',{}).get(key[6:]) if key.startswith('marks.') else result.layout.get(key)
            assert actual is not None and len(actual)==expected,(row['id'],key)
        path=output/(row['id']+'.png');path.write_bytes(result.data)
        results.append({'id':row['id'],'type':row['type'],'width':result.width,'height':result.height,
                        'renderer':dict(result.backend)['renderer'],'nonwhitePixels':visible,
                        'sha256':hashlib.sha256(result.data).hexdigest(),'status':'PASS'})
        if dsl_mode:
            # The copied fixture contains independent source-spec properties,
            # not a neighboring checkout or compiler-generated expected spec.
            from py_mermaid import compile_vchart
            compiled=compile_vchart(row['dslSource'])
            canonical=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':'))
            assert canonical(compiled.spec())==canonical(row['spec']),row['id']
            assert canonical(compiled.maps())==canonical(row['maps']),row['id']
            assert canonical(compiled.svg_sources())==canonical(row['svgs']),row['id']
            text_result=render(row['dslSource'],backend='cpu')
            assert text_result.data==result.data,(row['id'],'DSL and direct spec PNG differ')
            assert (text_result.width,text_result.height)==dimensions,row['id']
            assert dict(text_result.backend)['renderer']=='CPU',row['id']
            (output/(row['id']+'.vchart')).write_text(row['dslSource'],encoding='utf8')
            (output/(row['id']+'.dsl.png')).write_bytes(text_result.data)
            inspection=json.dumps(compiled.as_dict(),indent=2,ensure_ascii=True)+'\n'
            (output/(row['id']+'.compiled.json')).write_text(inspection,encoding='utf8')
            dsl_results.append({'id':row['id'],'type':row['type'],'status':'PASS',
                'pngSha256':hashlib.sha256(text_result.data).hexdigest(),
                'specEquivalent':True,'actualPixelsEqual':True,
                'inlineMapCount':len(compiled.maps()),'inlineSvgCount':len(compiled.svg_sources()),
                'sourceMapEntries':len(compiled.source_map)})
    bar=next(r for r in rows if r['type']=='bar')
    for fmt,magic in [('svg',None),('pdf',b'%PDF')]:
        result=render_vchart(bar['spec'],format=fmt,backend='cpu')
        if magic:assert result.data.startswith(magic)
        else:
            assert '<svg' in result.data.decode('utf-8')
            assert 'data:image/png;base64' not in result.data.decode('utf-8')
        (output/('representative.'+fmt)).write_bytes(result.data)
    # A real pyelk worker and a real installed KaTeX layout in the same public
    # Mermaid request. The main guard is required by Windows spawn.
    flow=render('flowchart TD\nA["Before $$x^2$$ after"] --> B[Result]\nB --> C[Done]',backend='cpu')
    assert flow.layout.engine=='pyelk/elk.layered',flow.layout.engine
    assert flow.layout.engine_version=='0.1.0'
    assert len(flow.layout.nodes)==3 and len(flow.layout.edges)==2
    assert any(event.kind=='math-glyph' and event.text=='2' for event in flow.trace),'missing real math glyph'
    assert any(event.kind=='math' for event in flow.trace),'missing real math box'
    (output/'math-and-elk.png').write_bytes(flow.data)
    module_paths={}
    for name,module in list(sys.modules.items()):
        path=getattr(module,'__file__',None)
        if path:
            resolved=Path(path).resolve()
            assert not resolved.is_relative_to(workspace),(name,str(resolved))
            if name.startswith(('py_mermaid','py_vchart','py_katex','pyelk')):module_paths[name]=str(resolved)
    summary={'status':'PASS','isolated':True,'cwd':str(Path.cwd()),'prefix':str(prefix),
             'versions':{name:metadata.version(name) for name in (mermaid_distribution,'py-visactor-vchart','py-visactor-elk','py-visactor-katex','py-skia-canvas')},
             'vchartDirectUrl':direct,'vchartResolvedDownload':download_info,'delivery':lock['delivery'],
             'mermaidRequiresDist':requirements,'renderedTypes':len(results),
             'cases':results,'vectorExports':['svg','pdf'],'mathGlyphVerified':True,
             'realELK':{'engine':flow.layout.engine,'version':flow.layout.engine_version,'nodes':3,'edges':2},
             'modulePaths':module_paths,'forbiddenProductionImports':False}
    if dsl_mode:
        assert len(dsl_results)==68 and {r['type'] for r in dsl_results}==set(py_mermaid.supported_vchart_types())
        assert any(r['inlineMapCount'] for r in dsl_results),'No real inline map verification'
        assert any(r['inlineSvgCount'] for r in dsl_results),'No real inline SVG verification'
        summary['dsl']={'status':'PASS','renderedTypes':68,'cases':dsl_results,
                        'fixtureSha256':hashlib.sha256(fixture.read_bytes()).hexdigest()}
    (output/'result.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','renderedTypes':len(results),'prefix':str(prefix),'direct_url':direct}))


if __name__=='__main__':
    main()
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=('wheel','sdist'),required=True)
    parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--dsl',action='store_true',help='Additionally compile and render all 68 copied source specs through the new DSL, including inline maps/SVGs')
    args=parser.parse_args()
    fixture=ROOT/'tests/vchart_integration/cases-vchart.json'
    lockfile=ROOT/'references/vchart-release-lock.json'
    temp_root=Path('C:/t');temp_root.mkdir(exist_ok=True)
    external=Path(tempfile.mkdtemp(prefix='vci-',dir=temp_root)).resolve()
    assert not external.is_relative_to(ROOT.parent.resolve())
    tmp=external/'tmp';tmp.mkdir()
    env={'TMP':str(tmp),'TEMP':str(tmp),'PYTHONPATH':'','PYTHONNOUSERSITE':'1',
         'PYTHONIOENCODING':'utf-8','PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_CONFIG_FILE':'NUL'}
    run=Run('VCHART-INSTALL',args.kind)
    code=1
    try:
        with run:
            for path in (Path(__file__),ROOT/'pyproject.toml',lockfile,fixture):run.input(path)
            if args.dsl:run.input(ROOT/'tools/vchart_dsl_corpus.py')
            artifacts=run.path/'artifacts';dist=artifacts/'dist';dist.mkdir()
            shutil.copyfile(lockfile,artifacts/'release-lock.json')
            shutil.copyfile(ROOT/'pyproject.toml',artifacts/'pyproject.toml')
            def command(name,argv,*,cwd=external,timeout=600):
                result=run.command(name,list(map(str,argv)),cwd=cwd,env=env,timeout=timeout)
                if result['exitCode']!=0:raise RuntimeError(name+' failed with exit '+str(result['exitCode']))
                return result
            # Build from the actual consumer tree; never manufacture metadata or
            # install VChart in advance. Both distributions are preserved.
            command('build-consumer',[args.python,'-m','build','--wheel','--sdist','--outdir',dist,ROOT],timeout=900)
            wheels=list(dist.glob('*.whl'));sdists=list(dist.glob('*.tar.gz'))
            if len(wheels)!=1 or len(sdists)!=1:raise RuntimeError('Expected one consumer wheel and one sdist')
            selected=(wheels if args.kind=='wheel' else sdists)[0]
            environment=external/'v'
            command('fresh-venv',[args.python,'-m','venv',environment])
            python=environment/'Scripts/python.exe'
            before=command('before-install',[python,'-I','-m','pip','--isolated','list','--format=json'])
            initial=json.loads((run.path/before['stdout']).read_text('utf-8'))
            if any(p['name'].lower().replace('_','-')=='py-visactor-vchart' for p in initial):
                raise RuntimeError('Fresh environment already contained VChart')
            report=artifacts/'pip-install-report.json'
            command('resolver-install',[python,'-I','-m','pip','--isolated','install','--no-input','--no-cache-dir',
                '--index-url','https://pypi.org/simple','--report',report,selected],timeout=1200)
            lock=json.loads(lockfile.read_text('utf-8'));installed=json.loads(report.read_text('utf-8'))
            entry=next(p for p in installed['install'] if p['metadata']['name'].lower().replace('_','-')=='py-visactor-vchart')
            info=entry['download_info']
            if info['url'].split('#',1)[0]!=lock['asset']['url'] or info['archive_info']['hashes']['sha256']!=lock['asset']['sha256']:
                raise RuntimeError('Resolver did not fetch the exact approved release wheel/hash')
            command('pip-check',[python,'-I','-m','pip','--isolated','check'])
            command('pip-freeze',[python,'-I','-m','pip','--isolated','freeze','--all'])
            copied_fixture=external/'cases.json'
            if args.dsl:
                from vchart_dsl_corpus import format_spec
                document=json.loads(fixture.read_text('utf8'))
                for row in document['cases']:
                    # Host-only stdlib formatter, never shipped into or imported
                    # from the isolated installed-package probe.
                    row['dslSource']=format_spec(row['spec'],row['maps'],row['svgs'])
                write_json(artifacts/'dsl-fixtures.json',document,exclusive=True)
                shutil.copyfile(artifacts/'dsl-fixtures.json',copied_fixture)
            else:shutil.copyfile(fixture,copied_fixture)
            copied_lock=external/'lock.json';shutil.copyfile(lockfile,copied_lock)
            copied_report=external/'pip-report.json';shutil.copyfile(report,copied_report)
            probe=external/'probe.py';probe.write_text(PROBE,encoding='utf-8')
            (artifacts/'installed-probe.py').write_text(PROBE,encoding='utf-8')
            if file_identity(copied_fixture)!=file_identity(artifacts/'dsl-fixtures.json' if args.dsl else fixture):raise RuntimeError('Fixture copy drift')
            command('isolated-installed-render',[python,'-I',probe,copied_fixture,copied_lock,artifacts/'installed',ROOT.parent,copied_report]+(['--dsl'] if args.dsl else []),timeout=900)
            write_json(artifacts/'delivery.json',{'status':'PASS','artifactKind':args.kind,'consumerArtifact':
                {'path':selected.relative_to(run.path).as_posix(),**file_identity(selected)},
                'delivery':lock['delivery'],'requirement':lock['requirement'],'sourceCommit':lock['sourceCommit'],
                'pypi':lock['pypi'],'externalEnvironment':str(environment),'freshEnvironmentHadVChart':False,
                'resolvedDownload':info,'fixture':file_identity(copied_fixture)},exclusive=True)
            run.data['functionalStatus']='PASS';run.data['result']={'artifactKind':args.kind,'externalEnvironment':str(environment),
                'delivery':lock['delivery'],'pypiStatus':lock['pypi']['status'],'consumerArtifactSha256':file_identity(selected)['sha256']}
            code=0
    except Exception as exc:
        print(str(exc),file=sys.stderr)
    print(json.dumps({'runId':run.id,'status':run.data['status'],'run':str(run.path),'kind':args.kind}))
    return code


if __name__=='__main__':
    raise SystemExit(main())
