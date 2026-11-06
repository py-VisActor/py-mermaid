"""Source class/presentation-attribute bridge for temporal SVG renderers.

Geometry remains in each dedicated renderer. This adapter applies the source
CSS classes before measurement/paint so user CSS can override presentation
attributes without bypassing the common native style/security provider.
"""
import re

class TemporalPainter:
    def __init__(self,painter,kind):self.painter=painter;self.kind=kind;self.section=0;self.text_classes=();self.extra={}
    def __getattr__(self,key):return getattr(self.painter,key)
    def classes(self,method,kw):
        ident=kw.get('id','');role=kw.get('role','');kind=self.kind
        if ident in self.extra:return self.extra[ident]
        if role=='title':return ('titleText',) if kind=='gantt' else ('gitTitleText',) if kind=='gitGraph' else ()
        if kind=='journey':
            if ident.startswith('actor-label'):return ('legend',)
            if ident.startswith('actor-'):return (ident,)
            if ident.startswith('face-'):return ('face',)
            if ident.startswith('mouth-'):return ('mouth',)
            if ident.startswith('task-stem-'):return ('task-line',)
            if ident.startswith('task-actor-'):
                return self.extra.get(ident,())
            if ident.startswith('task-label-') or ident.startswith('task-'):return ('task','task-type-'+str(self.section))
            if ident.startswith('section-'):return ('journey-section','section-type-'+str(self.section))
        if kind=='timeline':
            if ident=='timeline-axis':return ('lineWrapper',)
            classes=('section-'+str(self.section-1),)
            if re.match(r'^event-\d',ident):classes+=('eventWrapper',)
            return classes
        if kind=='gantt':
            if role in ('task','milestone','vertical-marker'):return self.extra.get(ident,('task',))
            if ident.endswith('-label'):return self.extra.get(ident,('taskText',))
            if ident.startswith('category-'):return ('sectionTitle',)
            if ident.startswith('section-'):return ('section','section'+str(self.section%4))
            if ident=='today-marker':return ('today',)
            if ident.startswith(('exclude-','excluded-')):return ('exclude-range',)
            if ident.startswith(('tick','grid')):return ('grid',)
        if kind=='gitGraph':
            if '-tag-bg-' in ident:return ('tag-label-bkg',)
            if '-tag-hole-' in ident:return ('tag-hole',)
            if '-tag-' in ident:return ('tag-label',)
            if ident.endswith('-label'):return ('commit-label',)
            if ident.startswith('branch-'):return ('branch',)
            if method in ('path','line','polyline'):return ('arrow',)
            if method=='ellipse':return ('commit',)
        return ()
    def _style(self,method,kw):
        tag={'ellipse':'circle','line':'line','polyline':'path','polygon':'polygon','rect':'rect','path':'path','text':'text','measure':'text'}[method];base={}
        aliases={'line_width':'stroke_width','color':'text_color','size':'font_size','family':'font_family','weight':'font_weight'}
        for key in ('fill','stroke','line_width','dash','opacity','color','size','family','weight','italic'):
            if key not in kw:continue
            value=kw.pop(key)
            if value is None:continue
            if key=='italic':base['font_style']='italic' if value else 'normal'
            else:base[aliases.get(key,key)]=value
        classes=self.classes(method,kw) or self.text_classes if method in ('text','measure') else self.classes(method,kw)
        ancestors=(('g',classes,''),) if self.kind=='timeline' else ()
        return self.painter.style(classes,tag=tag,id=kw.get('id',''),base=base,ancestors=ancestors)
    def measure(self,*args,**kw):
        style=kw.pop('style',None) or self._style('measure',kw)
        return self.painter.measure(*args,style=style,**kw)
    def text(self,*args,**kw):
        style=kw.pop('style',None) or self._style('text',kw)
        return self.painter.text(*args,style=style,**kw)
    def _primitive(self,method,args,kw):
        style=kw.pop('style',None) or self._style(method,kw)
        return getattr(self.painter,method)(*args,style=style,**kw)
    def rect(self,*args,**kw):return self._primitive('rect',args,kw)
    def ellipse(self,*args,**kw):return self._primitive('ellipse',args,kw)
    def line(self,*args,**kw):return self._primitive('line',args,kw)
    def path(self,*args,**kw):return self._primitive('path',args,kw)
    def polyline(self,*args,**kw):return self._primitive('polyline',args,kw)
    def polygon(self,*args,**kw):return self._primitive('polygon',args,kw)
