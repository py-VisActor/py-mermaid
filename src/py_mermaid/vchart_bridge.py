"""Native VChart host boundary, derived from the public py_vchart.VChart API.

This module adds no renderer or inferred chart defaults. All chart types and
actual drawing remain owned by py-visactor-vchart. Native objects stay on the
calling thread, and only JSON/bytes/immutable metadata leave this boundary.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import fields
import json
import math
import re

from .model.flowchart import ExportOptions, MermaidError, SourceDocument
from .model.scene import Diagram, DiagramRenderResult
from .model.vchart import VChartModel, VChartScene
from .runtime.common import error, immutable_value, make_diagram

MAX_SPEC_BYTES = 8 * 1024 * 1024
MAX_JSON_DEPTH = 128
MAX_JSON_VALUES = 1_000_000
MAX_PIXELS = 64_000_000
_HEADER = re.compile(r'\A\ufeff?[ \t\r\n]*vchart[ \t]*(?:\r?\n|\Z)')
_NAMESPACE = re.compile(r'\A\ufeff?[ \t\r\n]*vchart\b')


def is_vchart_source(text):
    # Reserve malformed explicit headers too: JSON/title text must never be
    # accidentally detected as another Mermaid family. The provider below
    # still requires a real header line; YAML frontmatter is not supported.
    return isinstance(text, str) and _NAMESPACE.match(text) is not None


def raw_document(text, config=None):
    """Identity source map: JSON may contain literal Mermaid directive syntax."""
    if not isinstance(text, str):
        raise MermaidError('Diagram source must be str', code='INVALID_INPUT')
    if config is not None and not isinstance(config, Mapping):
        raise MermaidError('config must be a mapping', code='INVALID_CONFIG')
    # Config remains host metadata. Chart theme/layout/data come only from spec.
    # Empty processed_to_raw already means the identity map in common.error;
    # avoid allocating millions of redundant integer offsets for large data.
    return SourceDocument(text, text, text, text)


def source_payload(text):
    match = _HEADER.match(text)
    if match is None:
        raise MermaidError('VChart requires a vchart header followed by JSON', code='INVALID_VCHART_JSON')
    return text[match.end():], match.end()


def _provider():
    try:
        from py_vchart import VChart
    except ImportError as exc:
        raise MermaidError('py-visactor-vchart is required for VChart rendering',
                           code='VCHART_UNAVAILABLE') from exc
    if not callable(getattr(VChart, 'supported_types', None)):
        raise MermaidError('VChart dependency lacks the public native-host API',
                           code='VCHART_VERSION_MISMATCH')
    return VChart


def supported_vchart_types():
    """Return the dependency's complete current registry without a copied list."""
    return tuple(_provider().supported_types())


def _json_value(value, *, depth=0, seen=None, budget=None):
    seen = set() if seen is None else seen
    budget = [MAX_JSON_VALUES] if budget is None else budget
    budget[0] -= 1
    if depth > MAX_JSON_DEPTH or budget[0] < 0:
        raise MermaidError('VChart JSON exceeds structural budget', code='VCHART_SPEC_BUDGET')
    if value is None or type(value) in (bool, str, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise MermaidError('VChart JSON numbers must be finite', code='INVALID_VCHART_SPEC')
        return value
    if isinstance(value, Mapping) or type(value) in (list, tuple):
        identity = id(value)
        if identity in seen:
            raise MermaidError('Cyclic VChart JSON is forbidden', code='INVALID_VCHART_SPEC')
        seen.add(identity)
        try:
            if isinstance(value, Mapping):
                if any(type(key) is not str for key in value):
                    raise MermaidError('VChart JSON object keys must be strings', code='INVALID_VCHART_SPEC')
                return {key: _json_value(item, depth=depth+1, seen=seen, budget=budget)
                        for key, item in value.items()}
            return [_json_value(item, depth=depth+1, seen=seen, budget=budget) for item in value]
        finally:
            seen.remove(identity)
    raise MermaidError('VChart spec accepts only JSON-compatible values', code='INVALID_VCHART_SPEC')


def _dump(value, limit=MAX_SPEC_BYTES):
    try:
        text = json.dumps(_json_value(value), ensure_ascii=True, allow_nan=False,
                          separators=(',', ':'))
    except (ValueError, OverflowError, RecursionError) as exc:
        if isinstance(exc, MermaidError):
            raise
        raise MermaidError('Invalid or oversized VChart JSON', code='INVALID_VCHART_SPEC') from exc
    if len(text.encode('utf-8')) > limit:
        raise MermaidError('VChart JSON exceeds byte budget', code='VCHART_SPEC_BUDGET')
    return text


def model_from_spec(spec):
    if not isinstance(spec, Mapping):
        raise MermaidError('VChart spec must be a JSON object', code='INVALID_VCHART_SPEC')
    encoded = _dump(spec)
    spec = json.loads(encoded)
    provider = _provider()
    if not isinstance(spec.get('type'), str) or spec['type'] not in provider.supported_types():
        raise MermaidError('Unsupported VChart spec.type', code='UNSUPPORTED_VCHART_TYPE')
    try:
        width, height = provider.spec_size(spec)
    except ValueError as exc:
        raise MermaidError(str(exc), code='INVALID_VCHART_SIZE') from exc
    if width * height > MAX_PIXELS:
        raise MermaidError('VChart dimensions exceed canvas budget', code='RENDER_BUDGET')
    return VChartModel(encoded, width, height)


def model_from_json(payload, *, document, offset, max_text_size=MAX_SPEC_BYTES):
    if type(max_text_size) not in (int, float) or not math.isfinite(max_text_size) or max_text_size < 0:
        raise MermaidError('maxTextSize must be finite and nonnegative', code='INVALID_CONFIG')
    if len(payload.encode('utf-16-le', errors='surrogatepass')) // 2 > max_text_size:
        raise error(document, offset, 'VChart payload exceeds maxTextSize', code='TEXT_LIMIT')
    if len(payload.encode('utf-8', errors='surrogatepass')) > MAX_SPEC_BYTES:
        raise error(document, offset, 'VChart JSON exceeds byte budget', code='VCHART_SPEC_BUDGET')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate VChart JSON key: ' + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Nonfinite JSON literal: ' + value)
    try:
        value = json.loads(payload, object_pairs_hook=pairs, parse_constant=constant)
    except json.JSONDecodeError as exc:
        raise error(document, offset + exc.pos, str(exc), code='INVALID_VCHART_JSON') from exc
    except (ValueError, RecursionError) as exc:
        raise error(document, offset, str(exc), code='INVALID_VCHART_JSON') from exc
    return model_from_spec(value)


def make_vchart_diagram(spec):
    model = model_from_spec(spec)
    document = raw_document('vchart\n' + model.spec_json)
    return make_diagram('vchart', document, {}, model)


def _resources(maps=None, svgs=None):
    from .resources import MAX_BUNDLE_BYTES, MAX_RESOURCE_BYTES, validate_svg
    if maps is not None and not isinstance(maps, Mapping):
        raise MermaidError('VChart maps must be a name/GeoJSON mapping', code='INVALID_RESOURCE')
    if svgs is not None and not isinstance(svgs, Mapping):
        raise MermaidError('VChart svgs must be a name/SVG mapping', code='INVALID_RESOURCE')
    maps = _json_value(maps or {})
    total = 0
    for name, value in maps.items():
        if not name or not isinstance(value, dict):
            raise MermaidError('VChart map resources require nonempty names and GeoJSON objects', code='INVALID_RESOURCE')
        size = len(_dump(value, MAX_RESOURCE_BYTES).encode('utf-8'))
        total += size
    serialized = _dump(maps, MAX_BUNDLE_BYTES)
    sources = []
    for name, value in (svgs or {}).items():
        if not isinstance(name, str) or not name or not isinstance(value, str):
            raise MermaidError('VChart SVG resources require nonempty names and SVG text', code='INVALID_RESOURCE')
        data = value.encode('utf-8')
        if len(data) > MAX_RESOURCE_BYTES:
            raise MermaidError('VChart SVG exceeds resource budget', code='RESOURCE_BUDGET')
        validate_svg(data)
        sources.append((name, value))
        total += len(data)
    if total > MAX_BUNDLE_BYTES:
        raise MermaidError('VChart resources exceed bundle budget', code='RESOURCE_BUDGET')
    return serialized, tuple(sources)


def scene_for(model, *, maps=None, svgs=None):
    if not isinstance(model, VChartModel):
        raise MermaidError('Expected a VChart model', code='INVALID_DIAGRAM')
    if maps is not None and not isinstance(maps,Mapping) or svgs is not None and not isinstance(svgs,Mapping):
        # Preserve the existing explicit resource argument diagnostics.
        _resources(maps,svgs)
    inline_maps=json.loads(model.inline_maps_json)
    inline_svgs=dict(model.inline_svgs)
    if len(inline_svgs)!=len(model.inline_svgs):
        raise MermaidError('Duplicate inline VChart SVG resource',code='VCHART_DSL_RESOURCE_CONFLICT')
    for kind,inline,external in (('map',inline_maps,maps),('svg',inline_svgs,svgs)):
        collision=set(inline).intersection(external or {})
        if collision:
            raise MermaidError('Inline VChart '+kind+' resource conflicts with external resource: '+str(sorted(collision)[0]),
                               code='VCHART_DSL_RESOURCE_CONFLICT')
    map_json, sources = _resources({**inline_maps,**(maps or {})},{**inline_svgs,**(svgs or {})})
    return VChartScene(model, map_json, sources)


def _provider_error(diagram,exc,code):
    """Provider strings do not encode an exact spec path. Report the full DSL
    document, never invent a precise field/line from arbitrary error wording.
    Legacy JSON/Python-spec error messages and span behavior remain intact.
    """
    if isinstance(diagram.model,VChartModel) and diagram.model.syntax=='dsl':
        from .model.vchart_dsl import dsl_error
        return dsl_error(diagram.source.raw,0,len(diagram.source.raw),str(exc),code=code)
    return MermaidError(str(exc),code=code)


def _chart(scene, *, backend, resources=None):
    from .resources import ResourceStore, MAX_BUNDLE_BYTES, inline_image_data
    from .model.flowchart import ResourceBundle
    if backend not in ('auto', 'cpu', 'gpu'):
        raise MermaidError('backend must be auto, cpu or gpu', code='INVALID_BACKEND')
    if resources is not None and not isinstance(resources,ResourceBundle):
        raise MermaidError('resources must be ResourceBundle',code='INVALID_RESOURCE')
    store = ResourceStore(resources)
    from pathlib import Path
    resource_size=(sum(len(v) for v in store.images.values())+
                   sum(len(v) for v in store.icons.values())+
                   sum(Path(path).stat().st_size for family,path,digest in store.fonts)+
                   len(scene.maps_json.encode('utf-8'))+
                   sum(len(value.encode('utf-8')) for name,value in scene.svgs))
    if resource_size > MAX_BUNDLE_BYTES:
        raise MermaidError('Combined VChart resources exceed bundle budget',code='RESOURCE_BUDGET')
    inline_images=set()
    # FontLibrary is process-global. Never register an author's public name:
    # isolate each font's bytes, and bind only explicit spec fontFamily values.
    font_aliases={family:('__py_mermaid_vchart_'+digest,path) for family,path,digest in store.fonts}
    used_fonts=set()
    def bind_fonts(value):
        if isinstance(value,dict):
            result={}
            for key,item in value.items():
                if key=='data':result[key]=item  # Data labels are not CSS declarations.
                elif key=='fontFamily' and isinstance(item,str):
                    if item in font_aliases:
                        alias,path=font_aliases[item];used_fonts.add(item);result[key]=alias
                    elif any(token.strip().strip('\"\'') in font_aliases for token in item.split(',')):
                        raise MermaidError('Custom VChart fonts require a single explicit fontFamily name',code='UNSUPPORTED_VCHART_FONT')
                    else:result[key]=item
                else:result[key]=bind_fonts(item)
            return result
        if isinstance(value,list):return [bind_fonts(item) for item in value]
        return value
    # Reserve an explicit local protocol: ordinary labels/data strings are not
    # looked up as resources merely because they equal a registered identifier.
    def replace_assets(value):
        nonlocal resource_size
        # Self-contained image URIs reach VChart's decoder directly. Apply the
        # same Mermaid byte/SVG safety boundary first, including nested specs
        # and otherwise opaque data records. No event/external SVG may bypass
        # validation merely by being base64-encoded rather than named in svgs.
        if isinstance(value,str) and value.lower().startswith('data:image/'):
            if value not in inline_images:
                data=inline_image_data(value)
                if data is None:
                    raise MermaidError('Invalid embedded VChart image URI',code='INVALID_RESOURCE')
                resource_size+=len(data)
                if resource_size>MAX_BUNDLE_BYTES:
                    raise MermaidError('Combined VChart resources exceed bundle budget',code='RESOURCE_BUDGET')
                inline_images.add(value)
            return value
        if isinstance(value, str) and value.startswith('resource:'):
            key = value[len('resource:'):]
            data = store.data(key, 'image')
            mime = next((v.mime for v in resources.images if v.id == key), '') if resources else ''
            if not mime.startswith('image/'):
                mime = 'image/svg+xml' if data.lstrip().startswith(b'<') else 'image/png'
            return 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')
        if isinstance(value, dict):
            return {k: replace_assets(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace_assets(v) for v in value]
        return value
    spec=bind_fonts(replace_assets(scene.model.spec()))
    if used_fonts:
        from py_skia_canvas import FontLibrary
        for family in sorted(used_fonts):
            alias,path=font_aliases[family]
            FontLibrary.use(alias,path)
    return _provider()(spec, backend=backend,
                       text_engine='canvas', maps=json.loads(scene.maps_json), svgs=dict(scene.svgs))


def _options(format, options, width, height):
    format = 'jpg' if format == 'jpeg' else format
    if format not in ('png', 'jpg', 'webp', 'svg', 'pdf'):
        raise MermaidError('Unsupported static export format', code='UNSUPPORTED_FORMAT')
    options = ExportOptions() if options is None else options
    if (not isinstance(options, ExportOptions) or type(options.density) is not int or options.density < 1
            or type(options.quality) not in (int, float) or not math.isfinite(options.quality)
            or not 0 <= options.quality <= 1 or type(options.outline) is not bool
            or type(options.downsample) is not bool or options.matte is not None and not isinstance(options.matte, str)):
        raise MermaidError('Invalid export options', code='INVALID_EXPORT_OPTIONS')
    density = options.density if format in ('png', 'jpg', 'webp') else 1
    if max(width,height)*density > 32768 or width * height * density ** 2 > MAX_PIXELS:
        raise MermaidError('VChart export exceeds canvas budget', code='RENDER_BUDGET')
    return format, {f.name: getattr(options, f.name) for f in fields(options)
                    if getattr(options, f.name) is not None}, density


def draw_vchart(scene, canvas, *, backend, x=0, y=0, resources=None):
    """Draw on the actual owner Canvas; no raster embedding or temporary file."""
    try:
        chart = _chart(scene, backend=backend, resources=resources)
        chart.draw_to(canvas, x=x, y=y)
        return immutable_value(chart.scene)
    except MermaidError:
        raise
    except ValueError as exc:
        raise MermaidError(str(exc), code='VCHART_SPEC_ERROR') from exc
    except Exception as exc:
        raise MermaidError('VChart draw failed: ' + str(exc), code='VCHART_RENDER_ERROR') from exc


def measure_vchart(scene, *, backend, resources=None):
    """Run the real engine for pure layout metadata used by Mermaid overlays."""
    try:
        chart = _chart(scene, backend=backend, resources=resources).render()
        return immutable_value(chart.scene)
    except MermaidError:
        raise
    except ValueError as exc:
        raise MermaidError(str(exc), code='VCHART_SPEC_ERROR') from exc
    except Exception as exc:
        raise MermaidError('VChart layout failed: ' + str(exc), code='VCHART_RENDER_ERROR') from exc


def encode_vchart(diagram, scene, *, format='png', backend='auto', resources=None, export_options=None):
    format, options, density = _options(format, export_options, scene.model.width, scene.model.height)
    try:
        chart = _chart(scene, backend=backend, resources=resources).render()
        data = bytes(chart.to_buffer(format, options=options))
        # Public width/height are logical pixels; raster density affects only
        # encoded dimensions. Never report requested backend as actual engine.
        width, height = chart.export_size(format, options=options)
        engine = tuple(sorted((str(k), str(v)) for k, v in chart.engine.items()))
        geometry = immutable_value(chart.scene)
    except MermaidError as exc:
        if scene.model.syntax=='dsl' and exc.span is None:
            raise _provider_error(diagram,exc,exc.code) from exc
        raise
    except ValueError as exc:
        raise _provider_error(diagram,exc,'VCHART_SPEC_ERROR') from exc
    except Exception as exc:
        raise _provider_error(diagram,'VChart rendering/export failed: '+str(exc),'VCHART_RENDER_ERROR') from exc
    return DiagramRenderResult(data, width, height,
        {'png':'image/png', 'jpg':'image/jpeg', 'webp':'image/webp', 'svg':'image/svg+xml', 'pdf':'application/pdf'}[format],
        diagram, (), geometry, engine, diagram.diagnostics, (), scene)
