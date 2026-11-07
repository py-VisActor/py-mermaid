"""Pure VChart text compilation; rendering and device selection are separate."""
from dataclasses import replace
import math
import re
from .model.flowchart import MermaidError
from .model.vchart import VChartCompilation
from .model.vchart_dsl import DslDiagnostic,SpecSpan,dsl_error

_TYPED_HEADER=re.compile(r'\A\ufeff?[ \t\r\n]*vchart[ \t]+[A-Za-z_][A-Za-z0-9_]*')


def _config(config):
    from .vchart_bridge import raw_document
    raw_document('',config)
    values=dict(config or {})
    unsupported=set(values)-{'maxTextSize'}
    if unsupported:
        raise MermaidError('VChart uses its JSON spec; unsupported Mermaid config: '+
            ', '.join(sorted(map(str,unsupported))),code='UNSUPPORTED_VCHART_CONFIG')
    limit=values.get('maxTextSize',8*1024*1024)
    if type(limit) not in (int,float) or not math.isfinite(limit) or limit<0:
        raise MermaidError('maxTextSize must be finite and nonnegative',code='INVALID_CONFIG')
    return values,limit


def _diagnostics(model):
    spec=model.spec();diagnostics=list(model.diagnostics)
    if spec['type']=='sequenceScatterPixel' and any(spec.get(k,300)!=300 for k in ('width','height')):
        span=next((s for s in model.source_map if s.namespace=='spec' and s.path in (('width',),('height',))),None)
        diagnostics.append(DslDiagnostic('VCHART_FIXED_SIZE',
            'py-visactor-vchart 0.1.1 sequenceScatterPixel always renders 300x300; requested width/height remain in the compiled spec.',
            span.path if span else (),span.start if span else 0,span.end if span else 0))
    return replace(model,diagnostics=tuple(diagnostics))


def compile_model(text,config=None):
    """Keep the legacy strict-JSON path intact; lower only typed headers."""
    from .vchart_bridge import raw_document,source_payload,model_from_json,model_from_spec,_HEADER
    values,limit=_config(config);document=raw_document(text,values)
    if _HEADER.match(text) or not _TYPED_HEADER.match(text):
        # Only an ASCII type token introduces the new language. Other old
        # malformed headers (inline JSON, vchart!, etc.) retain source_payload's
        # original INVALID_VCHART_JSON message and span behavior.
        payload,offset=source_payload(text)
        model=model_from_json(payload,document=document,offset=offset,max_text_size=limit)
        return _diagnostics(replace(model,source_map=(SpecSpan((),offset,len(text)),)))
    if len(text.encode('utf-16-le','surrogatepass'))//2>limit:
        raise dsl_error(text,0,len(text),'VChart payload exceeds maxTextSize',code='TEXT_LIMIT')
    from .parsing.vchart_dsl.compiler import lower_dsl
    lowered=lower_dsl(text)
    import json
    spec=json.loads(lowered.spec_json)
    try:model=model_from_spec(spec)
    except MermaidError as exc:
        path=None;message=str(exc)
        if exc.code=='UNSUPPORTED_VCHART_TYPE':
            from difflib import get_close_matches
            from .vchart_bridge import supported_vchart_types
            names={name.casefold():name for name in supported_vchart_types()}
            guesses=get_close_matches(str(spec.get('type','')).casefold(),names,n=3,cutoff=.25)
            suggestions=[names[g] for g in guesses] or sorted(names.values())[:3]
            message+='; valid case-sensitive type suggestions: '+', '.join(suggestions);path=('type',)
        elif exc.code=='INVALID_VCHART_SIZE':
            invalid=[(key,) for key in ('width','height') if key in spec and
                     (type(spec[key]) is not int or not 1<=spec[key]<=8192)]
            if len(invalid)==1:path=invalid[0]
        # Known type/size failures have exact source paths. Other provider
        # messages retain a reliable whole-document range, never guessed text.
        span=next((v for v in lowered.source_map if v.namespace=='spec' and v.path==path),None) if path else None
        raise dsl_error(text,span.start if span else 0,span.end if span else len(text),
            message,code=exc.code,path=span.path if span else ()) from exc
    model=replace(model,inline_maps_json=lowered.maps_json,inline_svgs=lowered.svgs,
        source_map=lowered.source_map,diagnostics=lowered.diagnostics,syntax='dsl')
    return _diagnostics(model)


def compile_vchart(text,*,config=None,maps=None,svgs=None):
    """Return immutable values, fresh-copy accessors and complete source metadata.

    Public provider construction validates explicit GeoJSON/SVG snapshots only;
    it performs no render/Canvas/font operation. Full option guards remain at
    the provider's render boundary rather than being silently inferred here.
    """
    from .vchart_bridge import scene_for,_provider
    model=compile_model(text,config)
    try:
        scene=scene_for(model,maps=maps,svgs=svgs)
        import json
        _provider()(model.spec(),maps=json.loads(scene.maps_json),svgs=dict(scene.svgs))
    except MermaidError as exc:
        if model.syntax=='dsl' and exc.span is None:
            raise dsl_error(text,0,len(text),str(exc),code=exc.code) from exc
        raise
    except (ValueError,TypeError) as exc:
        if model.syntax=='dsl':
            raise dsl_error(text,0,len(text),str(exc),code='INVALID_RESOURCE') from exc
        raise MermaidError(str(exc),code='INVALID_RESOURCE') from exc
    return VChartCompilation(model,scene.maps_json,scene.svgs,text)
