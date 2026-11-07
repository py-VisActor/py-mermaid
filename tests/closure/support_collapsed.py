"""Read-only independent collapsed source/native paint and pixel verification.
Uses fixed-source computed JSON plus raw SVG, never candidate-generated goldens.
"""
import argparse,colorsys,copy,hashlib,json,math,re
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image,ImageColor,ImageDraw

def read(path):return json.loads(Path(path).read_text('utf-8-sig'))
def identity(path):return {'path':str(Path(path).resolve()),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'bytes':Path(path).stat().st_size}
def rgb(value):
 if value in ('none','transparent',''):return None
 if value.startswith('url('):raise ValueError('Gradient source requires a dedicated sampled-color contract')
 # CSS hue is cyclic, including the negative hues preserved by Khroma.
 # Pillow rejects negative hue and rounds exact-half theme channels downward
 # after decimal serialization. Keep this verifier independent of the product
 # parser and use CSS half-up 8-bit quantization, tolerating only 1e-9 of
 # serialization error at a mathematical half-channel boundary.
 hsl=re.fullmatch(r'hsl\(\s*([-+\d.eE]+)(?:deg)?\s*,\s*([-+\d.eE]+)%\s*,\s*([-+\d.eE]+)%\s*\)',value,re.I)
 if hsl:
  hue,saturation,lightness=map(float,hsl.groups())
  if not all(math.isfinite(v) for v in (hue,saturation,lightness)):raise ValueError('Nonfinite source color')
  channels=colorsys.hls_to_rgb((hue%360)/360,max(0,min(1,lightness/100)),max(0,min(1,saturation/100)))
  return tuple(max(0,min(255,math.floor(c*255+.5+1e-9))) for c in channels)
 return ImageColor.getrgb(value)[:3]
def number(value):return float(str(value).removesuffix('px'))
def center(box):return box['x']+box['width']/2,box['y']+box['height']/2
def source_projection(raw,svg):
 xml=ET.fromstring(svg);parents={child:p for p in xml.iter() for child in p};paths=[];radius=None
 for e in xml.iter():
  cls=e.attrib.get('class','')
  if 'collapsed-group' in cls or 'flow-collapsed' in cls:
   if 'rx' in e.attrib:radius=number(e.attrib['rx'])
   paths.extend(x.attrib['d'] for x in e.iter() if x.tag.rsplit('}',1)[-1]=='path' and 'd' in x.attrib)
 shapes=raw['shapes'];bodies=[s for s in shapes if any(c in (s.get('classes') or '').split() for c in ('collapsed-group','flow-collapsed'))]
 if not bodies:bodies=[s for s in shapes if s.get('d') in paths]
 if not bodies:raise ValueError('No actual source collapsed outer paint')
 dots=[s for s in shapes if 'collapsed-indicator' in (s.get('classes') or '').split()]
 separators=[s for s in shapes if 'collapsed-separator' in (s.get('classes') or '').split()]
 if len(dots)!=3 or len(separators)!=1:raise ValueError('Source marker denominator changed')
 body=bodies[-1]
 return {'body':{'fill':body['fill'],'stroke':body['stroke'],'width':number(body['strokeWidth']),'opacity':number(body['opacity'])},'bodyBox':body['box'],'radius':radius,
         'dots':[{'box':d['box'],'fill':d['fill'],'stroke':d['stroke'],'width':number(d['strokeWidth']),'opacity':number(d['opacity'])} for d in dots],
         'separator':{'box':separators[0]['box'],'stroke':separators[0]['stroke'],'width':number(separators[0]['strokeWidth']),'dash':list(map(float,re.findall(r'[\d.]+',separators[0]['strokeDasharray'])))}}
def native_projection(scene,node_id):
 body=next(e for e in scene['trace'] if e['kind']=='node' and e['semantic_id']==node_id)
 parts=[e for e in scene['trace'] if e['kind']=='node-part' and e['semantic_id']==node_id]
 measured=next(e for e in scene['measured'] if e['id']==node_id)
 arcs=re.findall(r'[Aa]\s*([\d.]+)[ ,]+([\d.]+)',measured['outline'])
 if not arcs:raise ValueError('Rounded source container has no actual measured arc')
 def paint(e):return {'fill':e.get('fill','none'),'stroke':e.get('stroke','none'),'width':e.get('stroke_width',0),'opacity':e.get('opacity',1),'box':e['box']}
 dots=[paint(e) for e in parts if 'collapsed-indicator' in (e.get('resource_id') or '').split()]
 sep=[e for e in parts if 'collapsed-separator' in (e.get('resource_id') or '').split()]
 if len(dots)!=3 or len(sep)!=1:raise ValueError('Native marker denominator changed')
 return {'body':paint(body),'bodyBox':body['box'],'radius':float(arcs[0][0]),'dots':dots,'separator':{**paint(sep[0]),'dash':list(sep[0].get('dash',[]))}}
def errors(source,native,image,expected_radius):
 errors=[]
 def close(a,b,t=.05):return abs(a-b)<=t
 def color(a,b):return rgb(a)==rgb(b)
 for prop in ('fill','stroke'):
  if not color(source['body'][prop],native['body'][prop]):errors.append('body-'+prop)
 if not close(source['body']['width'],native['body']['width']):errors.append('body-stroke-width')
 if not close(native['radius'],source['radius'] if source['radius'] is not None else expected_radius):errors.append('body-radius')
 # Normalize only absolute location/label-dependent size. Marker geometry stays
 # in each node's own frame and must satisfy exact fixed-source local distances.
 ns=native['separator'];sb=ns['box'];bb=native['bodyBox']
 if not close(sb['x']-bb['x'],8) or not close(bb['x']+bb['width']-sb['x']-sb['width'],8):errors.append('separator-inset')
 if not close(source['separator']['width'],ns['width']) or not color(source['separator']['stroke'],ns['stroke']):errors.append('separator-paint')
 if ns['dash']!=source['separator']['dash']:errors.append('separator-dash')
 sd=sorted(source['dots'],key=lambda d:d['box']['x']);nd=sorted(native['dots'],key=lambda d:d['box']['x'])
 centers=[center(d['box']) for d in nd]
 if any(not close(centers[i+1][0]-centers[i][0],10) for i in (0,1)):errors.append('dot-spacing')
 if not close(centers[1][0],bb['x']+bb['width']/2):errors.append('dot-center')
 if any(not close(d['box']['width'],5) or not close(d['box']['height'],5) for d in nd):errors.append('dot-radius')
 for a,b in zip(sd,nd):
  if any(not color(a[prop],b[prop]) for prop in ('fill','stroke')) or not close(a['width'],b['width']) or not close(a['opacity'],b['opacity']):errors.append('dot-paint')
 # Real pixels must match body/alpha colors at independently chosen clear areas.
 im=image.convert('RGB');background=rgb(source['body']['fill']) or (255,255,255)
 p=(round(bb['x']+.8*bb['width']),round(bb['y']+.5*bb['height']))
 if max(abs(a-b) for a,b in zip(im.getpixel(p),background))>18:errors.append('body-visible-fill')
 for a,b in zip(sd,nd):
  foreground=rgb(a['fill']);expected=tuple(round(c*a['opacity']+bg*(1-a['opacity'])) for c,bg in zip(foreground,background))
  x,y=center(b['box']);actual=im.getpixel((round(x),round(y)))
  # Derive discrimination from original paint, not from candidate pixels.
  # A pale source marker can differ from its body by only17 levels, so the
  # old fixed18 tolerance incorrectly accepted removing that marker entirely.
  contrast=max(abs(c-bg) for c,bg in zip(expected,background))
  tolerance=min(18,max(2,contrast/3))
  if max(abs(x-y) for x,y in zip(actual,expected))>tolerance:errors.append('dot-visible-alpha-color')
 return sorted(set(errors))


def actual_projection(result,node_id):
    from dataclasses import asdict
    return native_projection(asdict(result),node_id)

def separator_pixels(source,native,image):
    """Test independent source3-on/3-off dash centers, away from borders."""
    im=image.convert('RGB');b=native['separator']['box'];background=rgb(source['body']['fill']) or (255,255,255)
    def contrast(x):
        return max(max(abs(a-b) for a,b in zip(im.getpixel((round(x),yy)),background))
                   for yy in (math.floor(b['y']),math.ceil(b['y'])))
    active=[];gaps=[]
    for i in range(max(0,int((b['width']-6)//6))):
        active.append(contrast(b['x']+1.5+6*i));gaps.append(contrast(b['x']+4.5+6*i))
    return bool(active) and sum(v>12 for v in active)>=len(active)*.7 and sum(v<12 for v in gaps)>=len(gaps)*.7

def corner_pixels(source,native,image,radius,canvas_background='white'):
    """Independent public Canvas circular arcTo reference, no shape helper.

    Only the upper-left corner is compared. The source4px positive shadow does
    not project into its exterior, and label/markers are outside this corner.
    """
    from py_skia_canvas import Canvas
    b=native['bodyBox'];extent=math.ceil(radius+2);pad=4
    reference=Canvas(extent+8,extent+8);reference.gpu=False;ctx=reference.getContext('2d')
    ctx.fillStyle=canvas_background;ctx.fillRect(0,0,reference.width,reference.height)
    fx=b['x']-math.floor(b['x']);fy=b['y']-math.floor(b['y']);ctx.translate(pad+fx,pad+fy)
    ctx.beginPath();ctx.moveTo(radius,0);ctx.lineTo(b['width']-radius,0)
    ctx.arcTo(b['width'],0,b['width'],radius,radius);ctx.lineTo(b['width'],b['height']-radius)
    ctx.arcTo(b['width'],b['height'],b['width']-radius,b['height'],radius);ctx.lineTo(radius,b['height'])
    ctx.arcTo(0,b['height'],0,b['height']-radius,radius);ctx.lineTo(0,radius)
    ctx.arcTo(0,0,radius,0,radius);ctx.closePath()
    ctx.fillStyle=source['body']['fill'] if rgb(source['body']['fill']) else 'transparent';ctx.fill()
    ctx.strokeStyle=source['body']['stroke'];ctx.lineWidth=source['body']['width'];ctx.stroke()
    data=bytes(ctx.getImageData(0,0,reference.width,reference.height).data);im=image.convert('RGB');mismatch=0
    stride=int(reference.width)  # Public Canvas dimensions may be float-valued.
    for yy in range(extent):
        for xx in range(extent):
            i=((pad+yy)*stride+pad+xx)*4;expected=tuple(data[i:i+3])
            actual=im.getpixel((math.floor(b['x'])+xx,math.floor(b['y'])+yy))
            mismatch+=max(abs(a-b) for a,b in zip(actual,expected))>40
    if mismatch>3:return False
    # Preserve the broad contour check above for antialiasing, but independently
    # inspect definite exterior pixels. A pale square must not pass merely
    # because its fill-to-white contrast is below the old40-level cutoff.
    background=rgb(canvas_background)
    body=rgb(source['body']['fill']) or background
    contrast=max(abs(c-bg) for c,bg in zip(body,background))
    tolerance=max(2,min(8,contrast/3))
    clear=[]
    half=source['body']['width']/2
    for yy in range(math.ceil(radius)):
        for xx in range(math.ceil(radius)):
            x=xx+.5-fx;y=yy+.5-fy
            # More than1px beyond the outer stroke removes AA-edge ambiguity;
            # positive source shadow offset4 cannot reach this upper-left area.
            if math.hypot(x-radius,y-radius)>radius+half+1:
                actual=im.getpixel((math.floor(b['x'])+xx,math.floor(b['y'])+yy))
                clear.append(max(abs(c-bg) for c,bg in zip(actual,background))<=tolerance)
    return bool(clear) and all(clear)
