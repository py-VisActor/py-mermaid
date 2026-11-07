"""Explicit local-file CLI for the public static renderer."""
from __future__ import annotations
import argparse
from dataclasses import asdict,is_dataclass
import json
from pathlib import Path
import sys
from .api import render,compile_vchart
from .model.flowchart import MermaidError, ExportOptions, ResourceBundle, ImageResource, IconResource, FontResource


def _json_object(path):
    value=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value,dict):raise ValueError(str(path)+' must contain a JSON object')
    return value


def _resource_bundle(manifest):
    if manifest is None:return None
    from .resources import MAX_RESOURCE_BYTES, MAX_BUNDLE_BYTES
    values=_json_object(manifest);base=manifest.resolve().parent;total=0
    if set(values)-{'images','icons','fonts'}:raise ValueError('Unknown resource manifest fields')
    def local_path(value):
        if not isinstance(value,str) or not value:raise ValueError('Resource path must be a nonempty string')
        path=(base/value).resolve(strict=True)
        if not path.is_file() or path.stat().st_size>MAX_RESOURCE_BYTES:raise ValueError('Invalid resource file size: '+value)
        return path
    def data(value):
        nonlocal total
        path=local_path(value);total+=path.stat().st_size
        if total>MAX_BUNDLE_BYTES:raise ValueError('Resource manifest exceeds bundle budget')
        return path.read_bytes()
    images=[];icons=[];fonts=[]
    for key,target in (('images',images),('icons',icons)):
        entries=values.get(key,{})
        if not isinstance(entries,dict):raise ValueError(key+' must map IDs to explicit paths or path/SHA objects')
        for identifier,item in entries.items():
            item={'path':item} if isinstance(item,str) else item
            if not isinstance(item,dict) or set(item)-{'path','sha256','mime'}:raise ValueError('Invalid resource manifest entry')
            content=data(item.get('path'));sha=item.get('sha256','')
            target.append(ImageResource(identifier,content,item.get('mime',''),sha) if key=='images' else IconResource(identifier,content.decode('utf-8'),sha))
    entries=values.get('fonts',[])
    if not isinstance(entries,list):raise ValueError('fonts must be an array')
    for item in entries:
        if not isinstance(item,dict) or set(item)-{'family','path','sha256'}:raise ValueError('Invalid font manifest entry')
        path=local_path(item.get('path'));total+=path.stat().st_size
        if total>MAX_BUNDLE_BYTES:raise ValueError('Resource manifest exceeds bundle budget')
        fonts.append(FontResource(item.get('family',''),str(path),item.get('sha256','')))
    return ResourceBundle(tuple(images),tuple(icons),tuple(fonts))


def main(argv=None):
    parser=argparse.ArgumentParser(prog='py-mermaid',description='Render a Mermaid diagram to a static image using native Canvas.')
    parser.add_argument('input',nargs='?',default='-',help='UTF-8 Mermaid file, or - for stdin')
    parser.add_argument('-o','--output',type=Path,help='Output file; default writes bytes to stdout')
    parser.add_argument('-f','--format',choices=('png','jpg','jpeg','webp','svg','pdf'),help='Default inferred from output suffix, otherwise png')
    parser.add_argument('--backend',choices=('auto','cpu','gpu'),default='auto')
    parser.add_argument('--config',type=Path,help='Explicit local JSON configuration file')
    parser.add_argument('--resources',type=Path,help='Offline JSON resource manifest with explicit image/icon/font paths')
    parser.add_argument('--vchart-maps',type=Path,help='Offline JSON object mapping VChart map names to GeoJSON objects')
    parser.add_argument('--vchart-svgs',type=Path,help='Offline JSON object mapping VChart SVG names to SVG source text')
    parser.add_argument('--metadata',type=Path,help='Write output size, MIME, actual backend and diagnostics as JSON')
    parser.add_argument('--compile','--compile-only',dest='compile_only',action='store_true',
        help='Compile explicit VChart text to inspectable JSON (spec, maps/SVGs, source spans and diagnostics), without rendering')
    parser.add_argument('--quality',type=float,default=.92)
    parser.add_argument('--density',type=int,default=1)
    parser.add_argument('--matte')
    parser.add_argument('--outline',action='store_true')
    parser.add_argument('--downsample',action='store_true')
    args=parser.parse_args(argv)
    try:
        text=sys.stdin.read() if args.input=='-' else Path(args.input).read_text(encoding='utf-8-sig')
        fmt=args.format or (args.output.suffix.lstrip('.').lower() if args.output and args.output.suffix else 'png')
        if args.output and args.metadata and args.output.resolve()==args.metadata.resolve():raise ValueError('Image and metadata paths must differ')
        protected=[Path(args.input)] if args.input!='-' else []
        protected.extend(p for p in (args.config,args.resources,args.vchart_maps,args.vchart_svgs) if p)
        for output in (args.output,args.metadata):
            if output and any(output.resolve()==source.resolve() for source in protected):raise ValueError('Output cannot overwrite an input file')
        from .resources import MAX_BUNDLE_BYTES
        for source in (args.vchart_maps,args.vchart_svgs):
            if source and source.stat().st_size>MAX_BUNDLE_BYTES:raise ValueError('VChart resource JSON exceeds bundle budget')
        config=_json_object(args.config) if args.config else None
        maps=_json_object(args.vchart_maps) if args.vchart_maps else None
        svgs=_json_object(args.vchart_svgs) if args.vchart_svgs else None
        if args.compile_only:
            if args.resources:raise ValueError('--resources is a rendering bundle; compile-only accepts --vchart-maps and --vchart-svgs')
            if args.metadata:raise ValueError('--metadata is for rendered outputs; compilation JSON already includes all source/resource metadata')
            compilation=compile_vchart(text,config=config,maps=maps,svgs=svgs)
            encoded=json.dumps(compilation.as_dict(),ensure_ascii=True,allow_nan=False,indent=2)+'\n'
            if args.output:args.output.write_text(encoded,encoding='utf-8')
            else:sys.stdout.write(encoded)
            return 0
        result=render(text,config=config,format=fmt,backend=args.backend,
            resources=_resource_bundle(args.resources),export_options=ExportOptions(args.quality,args.density,args.matte,args.outline,args.downsample),
            maps=maps,svgs=svgs)
        if args.output:args.output.write_bytes(result.data)
        else:sys.stdout.buffer.write(result.data)
        if args.metadata:
            metadata={'width':result.width,'height':result.height,'mime':result.mime,'backend':dict(result.backend),'diagnostics':result.diagnostics}
            args.metadata.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return 0
    except MermaidError as exc:
        payload={'code':exc.code,'message':str(exc),'span':asdict(exc.span) if exc.span else None}
        if hasattr(exc,'spec_path'):payload['spec_path']=list(exc.spec_path)
        if hasattr(exc,'related_spans'):
            payload['related_spans']=[asdict(v) if is_dataclass(v) else v for v in exc.related_spans]
        print(json.dumps(payload,ensure_ascii=True),file=sys.stderr);return 1
    except (OSError,ValueError) as exc:
        print(json.dumps({'code':'CLI_INPUT_ERROR','message':str(exc)},ensure_ascii=True),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
