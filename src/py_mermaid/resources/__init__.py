"""Explicit offline resource values and validation; no decoder or networking."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import re,base64
import xml.etree.ElementTree as ET
from ..model.flowchart import ResourceBundle,ImageResource,IconResource,FontResource,MermaidError

MAX_RESOURCE_BYTES=32*1024*1024
MAX_BUNDLE_BYTES=128*1024*1024
UNKNOWN_ICON='<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80"><rect width="80" height="80" fill="#087ebf"/><text x="21.16" y="64.67" fill="white" font-family="Arial" font-size="67.75">?</text></svg>'

def _error(message,code='INVALID_RESOURCE'):
    raise MermaidError(message,code=code)

def validate_svg(data: bytes)->bytes:
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():_error('SVG entities/DOCTYPE are not allowed','UNSAFE_RESOURCE')
    try:root=ET.fromstring(data)
    except ET.ParseError as exc:raise MermaidError('Invalid SVG resource',code='INVALID_RESOURCE') from exc
    if root.tag.rsplit('}',1)[-1].lower()!='svg':_error('Icon must have an SVG root')
    for element in root.iter():
        tag=element.tag.rsplit('}',1)[-1].lower()
        if tag in {'script','foreignobject','iframe','object','embed','animate','animatetransform','set'}:_error('SVG executable/animated content is not static','UNSAFE_RESOURCE')
        for name,value in element.attrib.items():
            key=name.rsplit('}',1)[-1].lower()
            if key.startswith('on'):_error('SVG event callbacks are forbidden','UNSAFE_RESOURCE')
            if key in {'href','src'} and value and not value.startswith('#'):
                if not re.match(r'^data:image/(?:png|jpeg|webp);base64,',value,re.I):_error('SVG external dependencies must be embedded offline','UNSAFE_RESOURCE')
            if not key.startswith('xmlns') and re.search(r'@import|(?:https?|file|javascript):',value,re.I):_error('External SVG resource reference','UNSAFE_RESOURCE')
            for url in re.findall(r'url\s*\((.*?)\)',value,re.I):
                if not url.strip(' \"\'').startswith('#'):_error('SVG url() must be a local definition','UNSAFE_RESOURCE')
        if tag=='style' and element.text and re.search(r'@import|url\s*\(\s*[\"\']?(?!#)',element.text,re.I):_error('External SVG stylesheet resource','UNSAFE_RESOURCE')
    return data

def inline_image_data(identifier:str):
    if not identifier.startswith('data:'):return None
    match=re.fullmatch(r'data:(image/[\w.+-]+);base64,([A-Za-z0-9+/=\s]+)',identifier,re.S)
    if not match:_error('Only explicit base64 image data URIs are accepted','INVALID_RESOURCE')
    if len(match[2])>MAX_RESOURCE_BYTES*4//3+4096:_error('Inline resource exceeds budget','RESOURCE_BUDGET')
    try:data=base64.b64decode(re.sub(r'\s','',match[2]),validate=True)
    except (ValueError,TypeError) as exc:raise MermaidError('Invalid base64 image',code='INVALID_RESOURCE') from exc
    if not data or len(data)>MAX_RESOURCE_BYTES:_error('Inline resource exceeds budget','RESOURCE_BUDGET')
    if 'svg' in match[1] or data.lstrip(b'\xef\xbb\xbf \t\r\n').startswith(b'<'):validate_svg(data)
    return data

class ResourceStore:
    """Validated pure bytes/path receipts. Native caches belong to CanvasSession."""
    def __init__(self,bundle:ResourceBundle|None=None):
        bundle=bundle or ResourceBundle()
        if not isinstance(bundle,ResourceBundle):_error('resources must be ResourceBundle')
        self.images={};self.icons={};self.fonts=[];total=0
        for item in (*bundle.images,*bundle.icons):
            if not isinstance(item,(ImageResource,IconResource)) or not isinstance(item.id,str) or not item.id:_error('Resource ID must be nonempty')
            if item.id in self.images or item.id in self.icons:_error(f'Duplicate resource ID: {item.id}')
            data=item.data if isinstance(item,ImageResource) else item.svg.encode('utf8')
            if not isinstance(data,bytes) or not data or len(data)>MAX_RESOURCE_BYTES:_error('Invalid resource bytes/budget','RESOURCE_BUDGET')
            digest=sha256(data).hexdigest()
            if item.sha256 and item.sha256.lower()!=digest:_error(f'Resource SHA mismatch: {item.id}','RESOURCE_INTEGRITY')
            if isinstance(item,IconResource) or 'svg' in item.mime.lower() or data.lstrip(b'\xef\xbb\xbf \t\r\n').startswith(b'<'):validate_svg(data)
            (self.icons if isinstance(item,IconResource) else self.images)[item.id]=data;total+=len(data)
        for item in bundle.fonts:
            if not isinstance(item,FontResource) or not item.family:_error('Invalid font resource')
            try:path=Path(item.path).expanduser().resolve(strict=True)
            except (OSError,ValueError) as exc:raise MermaidError('Font path cannot be opened',code='RESOURCE_NOT_FOUND') from exc
            if not path.is_file() or path.stat().st_size>MAX_RESOURCE_BYTES:_error('Invalid font resource size','RESOURCE_BUDGET')
            data=path.read_bytes();digest=sha256(data).hexdigest()
            if item.sha256 and item.sha256.lower()!=digest:_error('Font SHA mismatch','RESOURCE_INTEGRITY')
            self.fonts.append((item.family,str(path),digest));total+=len(data)
        if total>MAX_BUNDLE_BYTES:_error('Resource bundle exceeds budget','RESOURCE_BUDGET')
    def data(self,identifier:str,kind='image')->bytes:
        store=self.icons if kind=='icon' else self.images
        if identifier not in store:
            if kind=='icon':return UNKNOWN_ICON.encode('utf8')
            _error(f'Explicit offline resource not found: {identifier}','RESOURCE_NOT_FOUND')
        return store[identifier]

__all__=['ResourceBundle','ImageResource','IconResource','FontResource','ResourceStore','validate_svg']
