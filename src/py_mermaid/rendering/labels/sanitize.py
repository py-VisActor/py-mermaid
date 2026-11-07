"""Pure inert-markup sanitizer for the fixed common.ts label boundary.

This returns serialized safe markup, not visible text. Resource acquisition,
callback execution and browser/DOM objects never belong to this module.
"""
from __future__ import annotations

from html.parser import HTMLParser
import html
import re

from ...model.flowchart import FlowConfig, MermaidError
from ...config.values import thaw_value


_HTML_TAGS=frozenset('a abbr acronym address area article aside audio b bdi bdo big blockquote br button caption center cite code col colgroup data datalist dd del details dfn dialog dir div dl dt em fieldset figcaption figure font footer form h1 h2 h3 h4 h5 h6 header hgroup hr i img input ins kbd label legend li main map mark menu meter nav nobr ol optgroup option output p picture pre progress q rp rt ruby s samp section select small source span strike strong sub summary sup table tbody td template textarea tfoot th thead time tr track tt u ul var video wbr'.split())
_SVG_TAGS=frozenset('svg g path rect circle ellipse line polyline polygon text tspan defs lineargradient radialgradient stop clippath mask pattern marker symbol use foreignobject image filter fedropshadow fegaussianblur feoffset femerge femergenode'.split())
_MATH_TAGS=frozenset('math maction maligngroup malignmark menclose merror mfenced mfrac mglyph mi mlabeledtr mlongdiv mmultiscripts mn mo mover mpadded mphantom mroot mrow ms mscarries mscarry msgroup msline mspace msqrt msrow mstack mstyle msub msubsup msup mtable mtd mtext mtr munder munderover mprescripts none semantics annotation annotation-xml'.split())
_ATTRS=frozenset('id class style title lang dir hidden align bgcolor border cellpadding cellspacing colspan rowspan color face size href target rel name alt src srcset width height role aria-label aria-hidden viewbox gradientunits gradienttransform preserveaspectratio clippathunits patternunits patterntransform d x y x1 y1 x2 y2 cx cy r rx ry points transform fill stroke stroke-width fill-rule opacity fill-opacity stroke-opacity xmlns xmlns:xlink xlink:href type start reversed value datetime open controls preload poster'.split())
# Fixed bundle DOMPurify 3.4.12/src/attrs.ts HTML allowlist.
# Keep static form state (checked/selected/disabled/readonly/ranges/sizes);
# URL policy and explicit FORBID_ATTR still apply below.
_ATTRS=_ATTRS|frozenset('accept action align alt autocapitalize autocomplete autopictureinpicture autoplay background bgcolor border capture cellpadding cellspacing checked cite class clear color cols colspan command commandfor controls controlslist coords crossorigin datetime decoding default dir disabled disablepictureinpicture disableremoteplayback download draggable enctype enterkeyhint exportparts face for headers height hidden high href hreflang id inert inputmode integrity ismap kind label lang list loading loop low max maxlength media method min minlength multiple muted name nonce noshade novalidate nowrap open optimum part pattern placeholder playsinline popover popovertarget popovertargetaction poster preload pubdate radiogroup readonly rel required rev reversed role rows rowspan spellcheck scope selected shape size sizes slot span srclang start src srcset step style summary tabindex title translate type usemap valign value width wrap xmlns'.split())
_SVG_TAGS=_SVG_TAGS|frozenset(('svg', 'a', 'altglyph', 'altglyphdef', 'altglyphitem', 'animatecolor', 'animatemotion', 'animatetransform', 'circle', 'clippath', 'defs', 'desc', 'ellipse', 'enterkeyhint', 'exportparts', 'filter', 'font', 'g', 'glyph', 'glyphref', 'hkern', 'image', 'inputmode', 'line', 'lineargradient', 'marker', 'mask', 'metadata', 'mpath', 'part', 'path', 'pattern', 'polygon', 'polyline', 'radialgradient', 'rect', 'stop', 'style', 'switch', 'symbol', 'text', 'textpath', 'title', 'tref', 'tspan', 'view', 'vkern'))
_ATTRS=_ATTRS|frozenset(('accent-height', 'accumulate', 'additive', 'alignment-baseline', 'amplitude', 'ascent', 'attributename', 'attributetype', 'azimuth', 'basefrequency', 'baseline-shift', 'begin', 'bias', 'by', 'class', 'clip', 'clippathunits', 'clip-path', 'clip-rule', 'color', 'color-interpolation', 'color-interpolation-filters', 'color-profile', 'color-rendering', 'cx', 'cy', 'd', 'dx', 'dy', 'diffuseconstant', 'direction', 'display', 'divisor', 'dominant-baseline', 'dur', 'edgemode', 'elevation', 'end', 'exponent', 'fill', 'fill-opacity', 'fill-rule', 'filter', 'filterunits', 'flood-color', 'flood-opacity', 'font-family', 'font-size', 'font-size-adjust', 'font-stretch', 'font-style', 'font-variant', 'font-weight', 'fx', 'fy', 'g1', 'g2', 'glyph-name', 'glyphref', 'gradientunits', 'gradienttransform', 'height', 'href', 'id', 'image-rendering', 'in', 'in2', 'intercept', 'k', 'k1', 'k2', 'k3', 'k4', 'kerning', 'keypoints', 'keysplines', 'keytimes', 'lang', 'lengthadjust', 'letter-spacing', 'kernelmatrix', 'kernelunitlength', 'lighting-color', 'local', 'marker-end', 'marker-mid', 'marker-start', 'markerheight', 'markerunits', 'markerwidth', 'maskcontentunits', 'maskunits', 'max', 'mask', 'mask-type', 'media', 'method', 'mode', 'min', 'name', 'numoctaves', 'offset', 'operator', 'opacity', 'order', 'orient', 'orientation', 'origin', 'overflow', 'paint-order', 'path', 'pathlength', 'patterncontentunits', 'patterntransform', 'patternunits', 'pointer-events', 'points', 'preservealpha', 'preserveaspectratio', 'primitiveunits', 'r', 'rx', 'ry', 'radius', 'refx', 'refy', 'repeatcount', 'repeatdur', 'restart', 'result', 'rotate', 'scale', 'seed', 'shape-rendering', 'slope', 'specularconstant', 'specularexponent', 'spreadmethod', 'startoffset', 'stddeviation', 'stitchtiles', 'stop-color', 'stop-opacity', 'stroke-dasharray', 'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-opacity', 'stroke', 'stroke-width', 'style', 'surfacescale', 'systemlanguage', 'tabindex', 'tablevalues', 'targetx', 'targety', 'transform', 'transform-origin', 'text-anchor', 'text-decoration', 'text-orientation', 'text-rendering', 'textlength', 'type', 'u1', 'u2', 'unicode', 'values', 'vector-effect', 'viewbox', 'visibility', 'version', 'vert-adv-y', 'vert-origin-x', 'vert-origin-y', 'width', 'word-spacing', 'wrap', 'writing-mode', 'xchannelselector', 'ychannelselector', 'x', 'x1', 'x2', 'xmlns', 'y', 'y1', 'y2', 'z', 'zoomandpan'))
_SVG_CASE={'lineargradient':'linearGradient','radialgradient':'radialGradient','clippath':'clipPath','foreignobject':'foreignObject','fedropshadow':'feDropShadow','fegaussianblur':'feGaussianBlur','feoffset':'feOffset','femerge':'feMerge','femergenode':'feMergeNode','textpath':'textPath','feblend':'feBlend','fecolormatrix':'feColorMatrix','fecomponenttransfer':'feComponentTransfer','fecomposite':'feComposite','feconvolvematrix':'feConvolveMatrix','fediffuselighting':'feDiffuseLighting','fedisplacementmap':'feDisplacementMap','feflood':'feFlood','fefunca':'feFuncA','fefuncb':'feFuncB','fefuncg':'feFuncG','fefuncr':'feFuncR','feimage':'feImage','femorphology':'feMorphology','fepointlight':'fePointLight','fespecularlighting':'feSpecularLighting','fespotlight':'feSpotLight','fetile':'feTile','feturbulence':'feTurbulence'}
_VOID=frozenset('area br col hr img input source track wbr'.split())
_DANGER=frozenset({'script','style','iframe','object','embed','template','noscript'})
_OPTIONS=frozenset({'ALLOWED_TAGS','ALLOWED_ATTR','ADD_TAGS','ADD_ATTR','FORBID_TAGS','FORBID_ATTR',
    'FORBID_CONTENTS','ADD_FORBID_CONTENTS','KEEP_CONTENT','ALLOW_DATA_ATTR','ALLOW_ARIA_ATTR',
    'ALLOW_UNKNOWN_PROTOCOLS','SAFE_FOR_TEMPLATES','SANITIZE_DOM','SANITIZE_NAMED_PROPS',
    'USE_PROFILES','ADD_URI_SAFE_ATTR','ADD_DATA_URI_TAGS','RETURN_TRUSTED_TYPE'})


def _set(options,key,default=()):
    value=options.get(key,default)
    if isinstance(value,str) or not isinstance(value,(list,tuple,set,frozenset,dict)):
        raise MermaidError(f'Sanitizer {key} must be a string sequence',code='INVALID_SANITIZER_CONFIG')
    if not all(isinstance(item,str) for item in value):raise MermaidError(f'Sanitizer {key} requires strings',code='INVALID_SANITIZER_CONFIG')
    return {item.lower() for item in value}


def _safe_uri(value,tag,options):
    compact=re.sub(r'[\x00-\x20\x7f-\x9f]','',html.unescape(value)).lower()
    if compact.startswith(('javascript:','vbscript:')):return False
    if compact.startswith('data:'):
        return tag in ({'img','audio','video','source','image'}|_set(options,'ADD_DATA_URI_TAGS')) and bool(re.match(r'data:(?:image|audio|video)/',compact))
    if options.get('ALLOW_UNKNOWN_PROTOCOLS',False):return True
    match=re.match(r'^([a-z][a-z0-9+.-]*):',compact)
    return match is None or match[1] in {'http','https','ftp','ftps','mailto','tel','callto','sms','cid','xmpp'}


class _Sanitizer(HTMLParser):
    def __init__(self,options,custom: bool):
        super().__init__(convert_charrefs=False)
        self.options=options;self.output=[];self.stack=[];self.dropping=[]
        tags=set(_HTML_TAGS|_SVG_TAGS|_MATH_TAGS)
        profiles=options.get('USE_PROFILES')
        if profiles is not None:
            if not isinstance(profiles,dict):raise MermaidError('Sanitizer USE_PROFILES must be an object',code='INVALID_SANITIZER_CONFIG')
            tags=set()
            if profiles.get('html'):tags.update(_HTML_TAGS)
            if profiles.get('svg') or profiles.get('svgFilters'):tags.update(_SVG_TAGS)
            if profiles.get('mathMl'):tags.update(_MATH_TAGS)
        self.allowed=_set(options,'ALLOWED_TAGS',tags)|_set(options,'ADD_TAGS')
        self.forbidden=_set(options,'FORBID_TAGS',() if custom else ('style',))
        self.allowed_attrs=_set(options,'ALLOWED_ATTR',_ATTRS)|_set(options,'ADD_ATTR')
        self.forbidden_attrs=_set(options,'FORBID_ATTR')
        self.forbidden_content=_set(options,'FORBID_CONTENTS',_DANGER)|_set(options,'ADD_FORBID_CONTENTS')

    def handle_starttag(self,tag,attrs):
        if self.dropping:
            if tag not in _VOID:self.dropping.append(tag)
            return
        allowed=tag in self.allowed and tag not in self.forbidden and tag not in {'script','iframe','object','embed'}
        if not allowed:
            if tag in self.forbidden_content or not self.options.get('KEEP_CONTENT',True):
                if tag not in _VOID:self.dropping.append(tag)
            return
        # common.ts hooks transport target through a temporary data attribute;
        # after sanitizing, target and rel are restored/forced by the hook.
        target=next((value or '' for name,value in attrs if name.lower()=='target'),None) if tag=='a' else None
        if target is not None:
            attrs=[(name,value) for name,value in attrs if name.lower()!='data-temp-href-target']+[('data-temp-href-target',target)]
        safe=[]
        for name,value in attrs:
            name=name.lower();value=value or ''
            if name in self.forbidden_attrs:continue
            if name.startswith('on'):continue
            if name not in self.allowed_attrs:
                if name.startswith('data-') and self.options.get('ALLOW_DATA_ATTR',True):pass
                elif name.startswith('aria-') and self.options.get('ALLOW_ARIA_ATTR',True):pass
                else:continue
            if name in {'href','src','poster','xlink:href','action','formaction','background'} and name not in _set(self.options,'ADD_URI_SAFE_ATTR'):
                if not _safe_uri(value,tag,self.options):continue
            if self.options.get('SANITIZE_NAMED_PROPS') and name in {'id','name'}:value='user-content-'+value
            if self.options.get('SANITIZE_DOM',True) and name in {'id','name'} and value.lower() in {'__proto__','constructor','prototype','attributes','children','innerhtml','outerhtml'}:continue
            svg_attr={'viewbox':'viewBox','gradientunits':'gradientUnits','gradienttransform':'gradientTransform','preserveaspectratio':'preserveAspectRatio','clippathunits':'clipPathUnits','patternunits':'patternUnits','patterntransform':'patternTransform','markerwidth':'markerWidth','markerheight':'markerHeight','markerunits':'markerUnits','refx':'refX','refy':'refY','textlength':'textLength','lengthadjust':'lengthAdjust','startoffset':'startOffset','pathlength':'pathLength','filterunits':'filterUnits','primitiveunits':'primitiveUnits','stddeviation':'stdDeviation','basefrequency':'baseFrequency','kernelmatrix':'kernelMatrix','kernelunitlength':'kernelUnitLength','numoctaves':'numOctaves','surfacescale':'surfaceScale','specularconstant':'specularConstant','specularexponent':'specularExponent','diffuseconstant':'diffuseConstant','limitingconeangle':'limitingConeAngle'}.get(name,name)
            safe.append(f' {svg_attr}="{html.escape(value,quote=True)}"')
        temporary=next((item for item in safe if item.startswith(' data-temp-href-target=')),None)
        if tag=='a' and temporary is not None:
            safe=[item for item in safe if not item.startswith((' data-temp-href-target=',' target='))]
            safe.append(f' target="{html.escape(target or "",quote=True)}"')
            if target=='_blank':
                safe=[item for item in safe if not item.startswith(' rel=')]
                safe.append(' rel="noopener"')
        self.output.append('<'+_SVG_CASE.get(tag,tag)+''.join(safe)+'>')
        if tag not in _VOID:self.stack.append(tag)

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in _VOID:self.handle_endtag(tag)

    def handle_endtag(self,tag):
        if self.dropping:
            if tag in self.dropping:
                index=len(self.dropping)-1-self.dropping[::-1].index(tag)
                del self.dropping[index:]
            return
        if tag=='br':self.output.append('<br>');return
        if tag in self.stack:
            index=len(self.stack)-1-self.stack[::-1].index(tag)
            for entry in reversed(self.stack[index:]):self.output.append('</'+_SVG_CASE.get(entry,entry)+'>')
            del self.stack[index:]

    def handle_data(self,data):
        if self.dropping:return
        if self.options.get('SAFE_FOR_TEMPLATES'):data=re.sub(r'\{\{.*?\}\}|\$\{.*?\}|<%.*?%>',' ',data,flags=re.S)
        self.output.append(html.escape(data,quote=False))

    def handle_entityref(self,name):
        if not self.dropping:self.output.append('&'+name+';')

    def handle_charref(self,name):
        if not self.dropping:self.output.append('&#'+name+';')

    def finish(self):
        for tag in reversed(self.stack):self.output.append('</'+_SVG_CASE.get(tag,tag)+'>')
        return ''.join(self.output)


def sanitize_markup(text: str, config: FlowConfig) -> str:
    """Return safe serialized label markup using only effective config policy.

    Browser-only return-object/hooks/custom callbacks have no Python label value
    equivalent and fail explicitly rather than being accepted and ignored.
    """
    options=thaw_value(config.dompurify_config) if config.dompurify_config else {}
    if not isinstance(options,dict):raise MermaidError('dompurifyConfig must be an object',code='INVALID_SANITIZER_CONFIG')
    unknown=set(options)-_OPTIONS
    if unknown:raise MermaidError('Unsupported native sanitizer options: '+', '.join(sorted(unknown)),code='UNSUPPORTED_SANITIZER_CONFIG')
    for key in {'KEEP_CONTENT','ALLOW_DATA_ATTR','ALLOW_ARIA_ATTR','ALLOW_UNKNOWN_PROTOCOLS','SAFE_FOR_TEMPLATES','SANITIZE_DOM','SANITIZE_NAMED_PROPS','RETURN_TRUSTED_TYPE'}:
        if key in options and not isinstance(options[key],bool):raise MermaidError(f'Sanitizer {key} must be boolean',code='INVALID_SANITIZER_CONFIG')
    parser=_Sanitizer(options,config.dompurify_provided);parser.feed(text);parser.close()
    return parser.finish()
