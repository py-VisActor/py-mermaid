"""Source CSS targets for sequence primitives and measured text."""
from py_mermaid.config.values import thaw_value
import html,re
_SHAPE={'actor':'actor','actor-footer':'actor actor-bottom','actor-detail':'actor','lifeline':'actor-line','activation':'activation0','message':'messageLine0','note':'note','fragment':'loopLine','fragment-label-box':'labelBox','fragment-divider':'loopLine'}
_TEXT={'actor-label':'actor','message-text':'messageText','note-text':'noteText','fragment-title':'loopText','fragment-section':'loopText','fragment-kind':'labelText','box-title':'boxText','sequence-number':'sequenceNumber','diagram-title':'titleText'}

def _label_text(text):
    """SVG source text is literal except br and the dedicated KaTeX branch."""
    text=re.sub(r'#(\w+);',lambda m:html.unescape('&'+('#' if m[1].isdigit() else '')+m[1]+';'),text)
    pieces=re.split(r'(\$\$.+?\$\$)',text)
    for i,value in enumerate(pieces):
        if value.startswith('$$') and value.endswith('$$'):continue
        value=re.sub(r'<\/?br\s*\/?>','\n',value.replace('\n',' '),flags=re.I)
        # Generic flow label parsing has extra \n/icon syntax that source
        # sequence SVG text does not; HTML entities preserve literal glyphs
        # until that parser's actual text-data stage.
        value=html.escape(value,quote=False).replace('\\n','&#92;n')
        value=re.sub(r'\b(fa[bklrs]?):fa-',r'\1&#58;fa-',value)
        pieces[i]=value
    return ''.join(pieces)

class Presentation:
    def __init__(self,painter,actors=()):
        self.p=painter;self.actor_classes={a.id:thaw_value(a.metadata).get('properties',{}).get('class','') for a in actors}
        self.actor_types={a.id:a.kind for a in actors}
        self.message_stroke_width=1.5
    def __getattr__(self,name):return getattr(self.p,name)
    def measure_role(self,text,role,**kwargs):
        classes={'actor':'actor','message':'messageText','note':'noteText'}[role]
        base={'font_size':kwargs.get('size',14),'font_family':kwargs.get('family','sans-serif'),'font_weight':str(kwargs.get('weight','400')),'line_height':1.0}
        parent=self.p.style(classes,tag='text',base=base,ancestors=(('svg',('sequenceDiagram',),''),))
        st=self.p.style('',tag='tspan',base=parent,inherited=parent,ancestors=parent.paint_context)
        kwargs.update(size=st.font_size,family=st.font_family,weight=st.font_weight,italic=st.font_style!='normal')
        return self.p.measure(_label_text(text),**kwargs,style=st)
    def text(self,text,x,y,**kwargs):
        role=kwargs.get('role','label');classes=_TEXT.get(role,'');base={}
        if kwargs.get('color') is not None:base['text_color']=kwargs['color']
        if kwargs.get('size') is not None:base['font_size']=kwargs['size']
        identity=kwargs.get('id','')
        parent=self.p.style(classes,tag='text',id=identity,base=base,ancestors=(('svg',('sequenceDiagram',),''),))
        st=self.p.style('',tag='tspan',base=parent,inherited=parent,ancestors=parent.paint_context)
        kwargs['style']=st;kwargs['color']=st.text_color
        if 'size' in kwargs:kwargs['size']=st.font_size
        return self.p.text(_label_text(text) if isinstance(text,str) else text,x,y,**kwargs)
    def _shape(self,method,*args,**kwargs):
        role=kwargs.get('role','shape');identity=kwargs.get('id','');classes=_SHAPE.get(role,'')
        if role in {'actor','actor-footer'} and self.actor_classes.get(identity):classes=self.actor_classes[identity]
        if role=='message' and kwargs.get('dash'):classes='messageLine1'
        if role in {'activation0','activation1','activation2'}:classes=role
        if not classes and role!='central-connection':return getattr(self.p,method)(*args,**kwargs)
        base={target:kwargs[key] for key,target in [('fill','fill'),('stroke','stroke'),('line_width','stroke_width'),('dash','dash'),('opacity','opacity')] if key in kwargs}
        neo=self.p.config.get('look','neo')=='neo'
        # Source CSS uses an unresolved #drop-shadow for note/labelBox; only
        # actor primitives carry the actual diagram-prefixed filter reference.
        shadow=role in {'actor','actor-footer'} and self.actor_types.get(identity)!='actor'
        if neo and shadow:
            theme=self.p.config.get('sequence',{}).get('theme',self.p.config.get('theme','redux-color'))
            base.update(shadow_dx=4,shadow_dy=4,shadow_blur=0,shadow_opacity=.06,shadow_color='#000000' if theme in {'redux','redux-color'} else '#FFFFFF')
        if method=='line' and role!='message':base['stroke_width']=2  # source .actor-man circle, line
        ancestors=(('svg',('sequenceDiagram',),''),)
        if role=='central-connection':ancestors+=(('g',(),''),)
        st=self.p.style(classes,tag={'line':'line','polyline':'polyline','ellipse':'circle','polygon':'polygon','path':'path'}.get(method,'rect'),id='' if role=='central-connection' else identity,base=base,ancestors=ancestors)
        if role=='message':
            # drawMessage applies inline fill:none even to open self curves.
            # CSS !important may still override this exact element as in SVG.
            from py_mermaid.rendering.styles import apply_declarations
            st=apply_declarations(st,'fill:none'+(';stroke-dasharray:3,3' if kwargs.get('dash') else ''),kind='node')
            self.message_stroke_width=st.stroke_width
        elif role=='fragment-divider':
            # svgDraw.drawLoop sets this as an inline style. Ordinary themeCSS
            # cannot override it, but a stylesheet !important still can.
            from py_mermaid.rendering.styles import apply_declarations
            st=apply_declarations(st,'stroke-dasharray:3,3',kind='node')
        for target,value in [('stroke',st.stroke),('line_width',st.stroke_width),('opacity',st.opacity)]:kwargs[target]=value
        if method not in {'line','polyline'}:kwargs['fill']=st.fill
        if method not in {'polygon','ellipse'}:kwargs['dash']=st.dash
        kwargs['style']=st
        return getattr(self.p,method)(*args,**kwargs)
    def rect(self,*a,**kw):return self._shape('rect',*a,**kw)
    def ellipse(self,*a,**kw):return self._shape('ellipse',*a,**kw)
    def path(self,*a,**kw):return self._shape('path',*a,**kw)
    def line(self,*a,**kw):return self._shape('line',*a,**kw)
    def polyline(self,*a,**kw):return self._shape('polyline',*a,**kw)
    def polygon(self,*a,**kw):return self._shape('polygon',*a,**kw)
