"""Fixed source use-case glyph paths and business circle chord construction."""
import math
STICK='M 0 -12 C 6.627 -12 12 -17.373 12 -24 C 12 -30.627 6.627 -36 0 -36 C -6.627 -36 -12 -30.627 -12 -24 C -12 -17.373 -6.627 -12 0 -12 Z M 0 -12 V 8 M -17 -5 H 17 M 0 8 L -15 28 M 0 8 L 15 28'
HOLLOW='M -22 -10 H 22 V 0 H 6 L 22 17 L 13 28 L 0 13 L -13 28 L -22 17 L -6 0 H -22 Z'
AWESOME='M 0 -34 C 7.18 -34 13 -28.18 13 -21 C 13 -13.82 7.18 -8 0 -8 C -7.18 -8 -13 -13.82 -13 -21 C -13 -28.18 -7.18 -34 0 -34 Z M -24 25 C -24 7 -14 -3 0 -3 C 14 -3 24 7 24 25 C 24 28 21 30 18 30 H -18 C -21 30 -24 28 -24 25 Z'


def child_style(p,classes,parent,*,tag='g',id='',base=None):
    """Resolve an actual source descendant, with ancestor compositing state.

    display/opacity are not CSS inherited values, but a hidden/transparent
    ancestor still constrains its descendants. Reset the child's local values
    before cascading and compose that ancestor constraint exactly once.
    """
    from dataclasses import replace
    seed=replace(parent,display='inline',opacity=1.,important_properties=())
    if base:seed=replace(seed,**base)
    result=p.style(classes,tag=tag,id=id,base=seed,ancestors=parent.paint_context,inherited=parent)
    return replace(result,display='none' if parent.display=='none' else result.display,opacity=parent.opacity*result.opacity)


def actor_styles(p,node,config,definitions,fill,stroke,index):
    from dataclasses import replace
    from ...rendering.styles.flowchart import apply_declarations
    from ._support import palette,number
    tv=config.get('themeVariables') or {};conf=config.get('usecase') or {};meta=dict(node.metadata);variant='icon' if meta.get('icon') else meta.get('type','normal');root='rough-node' if config.get('look')=='handDrawn' else 'node'
    classes=(root,'default','usecase-actor','usecase-actor-'+meta.get('type','normal'),'usecase-actor-variant','usecase-actor-'+variant,*node.classes,*(() if not meta.get('business') else ('usecase-business',)))
    fill,stroke=palette(config,index,fill,stroke)
    outer=p.style(classes,tag='g',id=node.id,base={'fill':fill,'stroke':stroke,'stroke_width':2,'text_color':tv.get('actorTextColor',tv.get('primaryTextColor','#333')),'font_size':number(conf.get('actorFontSize'),14),'font_family':conf.get('actorFontFamily',tv.get('fontFamily','sans-serif')),'font_weight':conf.get('actorFontWeight','normal')},ancestors=(('svg',('usecase',),p.render_id),))
    compiled=[];defs=dict(definitions)
    for name in ('default',*node.classes):compiled.extend(defs.get(name,()))
    compiled.extend(node.styles)
    label_keys={'color','font-size','font-family','font-weight','font-style','text-decoration','text-align','text-transform','line-height','letter-spacing','word-spacing','text-shadow','text-overflow','white-space','word-wrap','word-break','overflow-wrap','hyphens'}
    label_css=';'.join(k+':'+v for k,v in compiled if k in label_keys);node_css=';'.join(k+':'+v for k,v in compiled if k not in label_keys)
    caption=child_style(p,('label','actor-label','usecase-actor-label'),outer,tag='g');caption=apply_declarations(caption,label_css,kind='node-label')
    stereotype=child_style(p,('label','usecase-stereotype'),outer,tag='g');stereotype=apply_declarations(stereotype,label_css,kind='node-label')
    variant_classes={'normal':('usecase-actor-shape','usecase-actor-normal'),'hollow':('usecase-actor-hollow',),'awesome':('usecase-actor-awesome',),'icon':('usecase-actor-icon',)}[variant]
    glyph=child_style(p,('usecase-actor-glyph',*variant_classes),outer);glyph=apply_declarations(glyph,node_css,kind='node')
    # Inline nodeStyles belongs to actorGroup. Re-apply the outer constraint if
    # the inline value overwrote the child's cumulative opacity/display.
    if any(k=='opacity' for k,v in compiled):glyph=replace(glyph,opacity=glyph.opacity*outer.opacity)
    if outer.display=='none':glyph=replace(glyph,display='none')
    return caption,stereotype,glyph


def paint_actor(p,node,box,label,stereotype,style,meta,caption_style=None,stereotype_style=None):
    from dataclasses import replace
    cx=box.x+box.width/2;variant='icon' if meta.get('icon') else meta.get('type','normal');content_height=72+8+label.height+(stereotype.height+2 if stereotype else 0);top=box.y+(box.height-content_height)/2;cy=top+36;transform=(1,0,0,1,cx,cy)
    if variant=='icon':
        frame=child_style(p,('usecase-actor-icon-frame',),style,tag='rect');p.rect(cx-26,cy-28,52,52,radius=4,style=frame,id=node.id,role='actor-icon-frame');icon=meta['icon'];symbol=child_style(p,('usecase-actor-icon-symbol',),style);p.asset(icon if ':' in icon else 'fa:'+icon,cx-21,cy-23,42,42,kind='icon',id=node.id,style=symbol)
    elif variant=='hollow':
        head=child_style(p,('usecase-actor-hollow-head',),style,tag='circle',base={'fill':'none'});body=child_style(p,('usecase-actor-hollow-body',),style,tag='path',base={'fill':'none'});p.ellipse(cx,cy-23,9,9,style=head,id=node.id,role='actor-head');p.path(HOLLOW,transform=transform,style=body,id=node.id,role='actor-body')
    else:
        body=child_style(p,('usecase-actor-awesome-silhouette' if variant=='awesome' else 'usecase-actor-stick',),style,tag='path');p.path(AWESOME if variant=='awesome' else STICK,transform=transform,style=body,id=node.id,role='actor-body')
    if meta.get('business'):
        if variant=='icon':path='M 12 -8 L 26 -26'
        else:
            y,r={'normal':(-24,12),'hollow':(-23,9),'awesome':(-21,13)}[variant];offset=r*.6;half=r*.8;dx=.5;dy=-math.sqrt(3)/2;x=offset*-dy;my=y+offset*dx;path=f'M{x-half*dx} {my-half*dy} L{x+half*dx} {my+half*dy}'
        marker=child_style(p,('usecase-business-marker','usecase-actor-business-marker'),style,tag='path',base={'fill':'none'});p.path(path,transform=transform,style=marker,id=node.id,role='business-actor-mark')
    y=top+80
    if stereotype:p.text(stereotype,cx-stereotype.width/2,y,style=stereotype_style or caption_style or style,id=node.id,role='stereotype');y+=stereotype.height+2
    p.text(label,cx-label.width/2,y,style=caption_style or style,id=node.id)
