"""Static host paint projection onto explicit inline SVG (not isolated img SVG)."""
from dataclasses import replace
import xml.etree.ElementTree as ET
from ..rendering.styles import apply_declarations,parse_declarations
from . import validate_svg

NS='http://www.w3.org/2000/svg'
PAINT={'fill','stroke','stroke-width','color','fill-opacity','stroke-opacity','opacity',
       'stroke-linecap','stroke-linejoin','stroke-dasharray','stroke-dashoffset',
       'display','visibility'}

def _apply(style,declarations,parent):
    # Local SVG paint servers are safe validated references, not CSS colors.
    normal=[]
    for name,value,important in declarations:
        if name in {'fill','stroke'} and value.strip().startswith('url('):
            if name not in style.important_properties or important:
                style=replace(style,**{name:value},stroke_gradient=() if name=='stroke' else style.stroke_gradient)
                if important:style=replace(style,important_properties=tuple(dict.fromkeys((*style.important_properties,name))))
        else:normal.append((name,value,important))
    return apply_declarations(style,tuple(normal),kind='node',inherited=parent)

def project_inline_svg(svg:str,label_style,resolver)->bytes:
    """Resolve source host CSS after presentation attrs, before own inline style.

    This is a pure element walk over explicit SVG values. Raster image/data URI
    documents never enter this function; native SVG decoding/drawing stays owner.
    """
    validate_svg(svg.encode('utf8'))
    root=ET.fromstring(svg);ET.register_namespace('',NS);ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
    initial=replace(label_style,fill=label_style.text_color,stroke='none',stroke_width=1,
        opacity=1,fill_opacity=1,stroke_opacity=1,stroke_gradient=(),shadow_opacity=0,important_properties=())
    gradients=[];used={e.get('id') for e in root.iter() if e.get('id')}
    def visit(element,parent):
        tag=element.tag.rsplit('}',1)[-1]
        base=replace(parent,opacity=1,important_properties=())
        presentation=tuple((name,value,False) for name,value in element.attrib.items() if name in PAINT)
        base=_apply(base,presentation,parent)
        style=resolver(tag,base,tuple(element.get('class','').split()),parent)
        inline=parse_declarations(element.get('style',''))
        style=_apply(style,tuple(d for d in inline if d[0] in PAINT),parent)
        stroke=style.stroke
        if style.stroke_gradient:
            index=len(gradients);identifier='py-mermaid-host-gradient-'+str(index)
            while identifier in used:index+=1;identifier='py-mermaid-host-gradient-'+str(index)
            used.add(identifier)
            gradient=ET.Element('{'+NS+'}linearGradient',{'id':identifier,'x1':'0%','y1':'0%','x2':'100%','y2':'0%'})
            for offset,color in style.stroke_gradient:ET.SubElement(gradient,'{'+NS+'}stop',{'offset':str(offset),'stop-color':color})
            gradients.append(gradient);stroke='url(#'+identifier+')'
        final={'fill':style.fill,'stroke':stroke,'stroke-width':f'{style.stroke_width:g}',
               'fill-opacity':f'{style.fill_opacity:g}','stroke-opacity':f'{style.stroke_opacity:g}',
               'opacity':f'{style.opacity:g}','color':style.text_color,
               'stroke-linecap':style.line_cap,'stroke-linejoin':style.line_join,
               'stroke-dasharray':' '.join(f'{value:g}' for value in style.dash) if style.dash else 'none',
               'stroke-dashoffset':f'{style.dash_offset:g}','display':style.display}
        # Remove original inline paint values after cascading; otherwise native
        # SVG would give them a second priority pass over source !important.
        other=[name+':'+value+(' !important' if important else '') for name,value,important in inline if name not in PAINT]
        for name,value in final.items():element.set(name,value)
        if other:element.set('style',';'.join(other))
        else:element.attrib.pop('style',None)
        for child in tuple(element):visit(child,style)
    visit(root,initial)
    if gradients:
        defs=next((e for e in root if e.tag.rsplit('}',1)[-1]=='defs'),None)
        if defs is None:defs=ET.Element('{'+NS+'}defs');root.insert(0,defs)
        defs.extend(gradients)
    return validate_svg(ET.tostring(root,encoding='utf-8',xml_declaration=False))
