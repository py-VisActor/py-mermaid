"""Shared locked-fixture and pure evidence codecs for retained-batch tooling."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timedelta
import base64
import hashlib
import json
import math
from pathlib import Path
import re
from run_support import ROOT, file_identity


def value_json(value):
    if is_dataclass(value):return {f.name:value_json(getattr(value,f.name)) for f in fields(value)}
    if isinstance(value,Mapping):return {str(k):value_json(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [value_json(v) for v in value]
    if isinstance(value,(datetime,date)):return {'$date':value.isoformat()}
    if isinstance(value,timedelta):return {'$timedeltaSeconds':value.total_seconds()}
    if isinstance(value,bytes):return {'$bytesSha256':hashlib.sha256(value).hexdigest(),'length':len(value)}
    if isinstance(value,float) and not math.isfinite(value):return {'$number':str(value)}
    if value is None or isinstance(value,(str,bool,int,float)):return value
    raise TypeError('Unserializable evidence value '+type(value).__name__)


def write(path,value):
    Path(path).write_text(json.dumps(value_json(value),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def origin_path(origin):
    roots={'mermaid':ROOT/'.local/upstream-mermaid','zenuml-core':ROOT/'.local/bulk-sources/zenuml/source'}
    repository=origin.get('repository','mermaid')
    base=roots.get(repository)
    if base is None:
        # Additional fixed dependency roots must be declared explicitly, never fetched.
        base=(ROOT/origin['repositoryRoot']).resolve(strict=True)
        base.relative_to(ROOT/'.local')
    path=(base/origin['path']).resolve(strict=True)
    path.relative_to(base.resolve())
    return path


def load_cases(paths,*,require_all=False):
    scope=json.loads((ROOT/'references/bulk-scope.json').read_text('utf-8'))
    result=[];seen=set()
    for path in paths:
        document=json.loads(Path(path).read_text('utf-8-sig'))
        if document['schema']!='py-mermaid-bulk-cases/v1':raise ValueError('Unexpected fixture schema')
        for case in document['cases']:
            id=case['id']
            portable=id.casefold()
            reserved={'con','prn','aux','nul',*(f'com{i}' for i in range(1,10)),*(f'lpt{i}' for i in range(1,10))}
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,179}',id) or id.endswith('.') or portable.split('.')[0] in reserved:
                raise ValueError('Invalid portable case ID '+id)
            if portable in seen:raise ValueError('Case ID collision on case-insensitive filesystems: '+id)
            seen.add(portable)
            if case['kind'] not in scope['retainedDetectors']:raise ValueError('Case outside retained scope '+id)
            if case['expect'] not in ('render','syntax_error','error','upstream_defect','excluded_by_static_scope'):raise ValueError('Unexpected expectation '+id)
            if not isinstance(case['source'],str) or not isinstance(case.get('config',{}),dict):raise ValueError('Invalid case input '+id)
            origin=case['origin'];canonical=origin_path(origin)
            if file_identity(canonical)['sha256']!=origin['sha256']:raise ValueError('Source origin SHA drift '+id)
            if not origin.get('symbol'):raise ValueError('Missing source branch/case identity '+id)
            result.append({**case,'group':case.get('group',document['group'])})
    missing=set(scope['retainedDetectors'])-{c['kind'] for c in result if c['expect']=='render'}
    if require_all and missing:raise ValueError('Missing retained positive fixture kinds: '+str(sorted(missing)))
    return result


def resources(case):
    """Strict explicit repository-relative file reads; no network or directory search."""
    from py_mermaid import ResourceBundle, ImageResource, IconResource, FontResource
    source=case.get('resources') or {}
    def path(item):
        target=(ROOT/item['path']).resolve(strict=True);target.relative_to(ROOT)
        if item.get('sha256') and file_identity(target)['sha256']!=item['sha256']:raise ValueError('Resource fixture SHA mismatch')
        return target
    return ResourceBundle(
        images=tuple(ImageResource(id,path(item).read_bytes(),item.get('mime',''),item.get('sha256','')) for id,item in source.get('images',{}).items()),
        icons=tuple(IconResource(id,path(item).read_text('utf-8'),item.get('sha256','')) for id,item in source.get('icons',{}).items()),
        fonts=tuple(FontResource(item['family'],str(path(item)),item.get('sha256','')) for item in source.get('fonts',[])))


def browser_resources(case):
    result={'images':[],'icons':[],'fonts':[]}
    for kind in ('images','icons'):
        for id,item in (case.get('resources') or {}).get(kind,{}).items():
            path=(ROOT/item['path']).resolve(strict=True);path.relative_to(ROOT)
            data=path.read_bytes()
            if item.get('sha256') and hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Fixture SHA mismatch')
            result[kind].append({'id':id,'dataBase64':base64.b64encode(data).decode(),'mime':item.get('mime',''),
                                 **({'svg':data.decode('utf-8-sig')} if kind=='icons' else {})})
    result['fonts']=(case.get('resources') or {}).get('fonts',[])
    return result
