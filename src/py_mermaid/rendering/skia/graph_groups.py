"""Shared source swimlane-cluster display overlay for generic measured graphs.

The layout provider owns placement. This module consumes its final centers and
replaces only top-level group frame/title commands, never nodes or edge routes.
Source: clusters/swimlane.js and swimlanes/helpers.ts (Mermaid 12.2.0, MIT).
"""
from __future__ import annotations
from dataclasses import replace
from collections.abc import Mapping
import math
from ...model.flowchart import Box,ResolvedStyle,MermaidError
from ...model.scene import Paint,TextBox


_FRAME_ROLES=frozenset({'group','cluster','namespace','composite-state','concurrency-region','composite-body','system-boundary','package-tab','group-frame','group-background','group-title-background','swimlane-body','swimlane-title'})
_TITLE_ROLES=frozenset({'label','title','group-title','cluster-label','namespace-label','boundary-title','swimlane-label','swimlane-title-label'})


def _style(command):
    value=dict(command.style).get('resolved')
    return value if isinstance(value,ResolvedStyle) else None


def _frame(command,id):
    if command.semantic_id!=id or command.kind!='path':return False
    if command.role in _FRAME_ROLES or any(command.role.startswith(role+'-') for role in _FRAME_ROLES):return True
    style=_style(command)
    # A family may retain the primitive's default role; only its actual cluster
    # context makes that a group frame. Do not remove same-ID edge paths.
    return command.role in ('shape','path') and style is not None and any(set(classes)&{'cluster','namespace','system-boundary','statediagram-cluster'} for tag,classes,name in style.paint_context)


def _title(command,id):
    return command.kind=='text' and command.semantic_id in (id,id+'-label') and command.role in _TITLE_ROLES


def _number(value,name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise MermaidError('Invalid swimlane group '+name,code='INVALID_LAYOUT')
    return float(value)


def _classes(group):
    value=group.get('cssClasses',group.get('classes',())) or ()
    return tuple(value.split()) if isinstance(value,str) else tuple(value)


def _declarations(group):
    result=[]
    for key in ('cssCompiledStyles','cssStyles','styles'):
        values=group.get(key,()) or ()
        if isinstance(values,str):result.append(values)
        elif isinstance(values,Mapping):result.extend(str(k)+':'+str(v) for k,v in values.items())
        else:
            for value in values:
                if isinstance(value,str):result.append(value)
                elif isinstance(value,(list,tuple)) and len(value)>=2:result.append(str(value[0])+':'+str(value[1]))
    return ';'.join(result)


def _child_style(painter,classes,parent,*,tag='rect',base=None):
    seed=replace(parent,opacity=1.,display='inline',important_properties=())
    if base is not None:seed=base
    result=painter.style(classes,tag=tag,base=seed,ancestors=parent.paint_context,inherited=parent)
    return replace(result,opacity=parent.opacity*result.opacity,display='none' if parent.display=='none' else result.display)


def overlay_swimlane_groups(painter,layout,commands)->tuple[Paint,...]:
    """Paint actual source lanes in front-to-back source cluster order.

    ``group_data`` includes synthetic DefaultLane already decided by the source
    prepare pass. Its frame is emitted even when its label is the empty string.
    Nested groups and every unrelated command are returned unchanged.
    """
    from ...config.flowchart import evaluate
    from ..styles.flowchart import apply_declarations
    commands=tuple(commands)
    if getattr(layout,'engine',None)!='mermaid-swimlane':return commands
    groups=tuple(group for group in getattr(layout,'group_data',()) if group.get('isGroup') and not group.get('parentId',group.get('parent')))
    if not groups:return commands
    tv=painter.config.get('themeVariables') or {};html=painter._label_config.html_labels
    remove=set();prepared=[]
    for group in groups:
        id=group.get('id')
        if not isinstance(id,str):raise MermaidError('Swimlane group requires a string identity',code='INVALID_LAYOUT')
        frames=[(i,c) for i,c in enumerate(commands) if _frame(c,id)];titles=[(i,c) for i,c in enumerate(commands) if _title(c,id)]
        remove.update(i for i,c in (*frames,*titles));base=next((s for i,c in frames if (s:=_style(c)) is not None),None)
        if base is None:
            fill=tv.get('clusterBkg','#ffffde');stroke=tv.get('clusterBorder','#aaaa33');borders=tv.get('borderColorArray');backgrounds=tv.get('bkgColorArray');index=group.get('colorIndex')
            if painter.config.get('theme') in ('redux-color','redux-dark-color') and isinstance(index,int) and isinstance(borders,(tuple,list)) and borders:
                stroke=borders[index%len(borders)]
                if isinstance(backgrounds,(tuple,list)) and backgrounds:fill=backgrounds[index%len(backgrounds)]
            base=replace(painter._base_style(),fill=fill,stroke=stroke,text_color=tv.get('titleColor',tv.get('textColor','#333')),
                stroke_width=painter._label_config.group_stroke_width,shadow_opacity=0)
        classes=('cluster','swimlane',*_classes(group));style=painter.style(classes,tag='g',id=id,base=replace(base,shadow_opacity=0),ancestors=(('svg',(painter.diagram.kind,),painter.render_id),));node_css=_declarations(group)
        if node_css:style=apply_declarations(style,node_css,kind='node')
        label=next((c.values[0] for i,c in titles if c.values and isinstance(c.values[0],TextBox)),None)
        # Already measured labels carry all rich runs and their source palette;
        # never flatten them back into a literal string and lose formatting.
        label_style=replace(style,fill=style.fill,shadow_opacity=0)
        if label is not None and label.runs:
            run=label.runs[0];label_style=replace(label_style,font_family=run.font_family,font_size=run.font_size,font_weight=run.font_weight,font_style=run.font_style,text_color=run.color)
        original_label_opacity=label_style.opacity
        label_style=_child_style(painter,('cluster-label','swimlane-label'),style,tag='g',base=replace(label_style,opacity=1.,display='inline',important_properties=()))
        x=_number(group.get('x'),'center x');y=_number(group.get('y'),'center y');w=_number(group.get('width',0),'width');h=_number(group.get('height',0),'height');padding=_number(group.get('padding',0),'padding')
        if min(w,h,padding)<0:raise MermaidError('Negative swimlane group geometry',code='INVALID_LAYOUT')
        reused=label is not None
        if label is None:label=painter.measure(str(group.get('label') or ''),label_kind=group.get('labelType','text') if group.get('labelType') in ('text','markdown') else 'text',html=html,width=w,style=label_style)
        if reused:
            factor=label_style.opacity/original_label_opacity if original_label_opacity else 0.
            label=replace(label,runs=tuple(replace(run,opacity=0. if label_style.display=='none' else run.opacity*factor) for run in label.runs))
        width=max(w,label.width+padding);left=x-width/2;top=y-h/2;is_lr=group.get('direction')=='LR'
        if is_lr:
            band=label.height+8;title=Box(left,top,band,h);body=Box(left+band,top,max(0,width-band),h);cx=left+band/2;cy=y
        else:
            content=_number(group.get('swimlaneContentTop',top+h/3),'content top');band=min(label.height,max(0,content-top));title=Box(left,top,width,band);body=Box(left,top+band,width,max(0,h-band));cx=x;cy=top+band/2
        prepared.append((id,group,style,label_style,label,body,title,cx,cy,is_lr,node_css))
    # Painter records exact path/font ink and rough extents. Isolate only this
    # temporary command buffer; restore caller state even if geometry fails.
    saved_commands=painter.commands;saved_rough=painter.rough_enabled;painter.commands=[]
    try:
        for id,group,style,label_style,label,body,title,cx,cy,is_lr,node_css in prepared:
            painter.rough_enabled=group.get('look',painter.config.get('look'))=='handDrawn'
            for box,fill,role in ((body,'none','swimlane-body'),(title,style.fill,'swimlane-title')):
                child=replace(style,fill=fill,shadow_opacity=0)
                child=_child_style(painter,(role,),style,tag='rect',base=replace(child,opacity=1.,display='inline',important_properties=()))
                if node_css:child=apply_declarations(child,node_css,kind='node')
                if style.display=='none':child=replace(child,display='none')
                painter.path(f'M{box.x},{box.y} h{box.width} v{box.height} h{-box.width} Z',style=child,id=id,role=role,rough_options={'roughness':.7,'fillWeight':3} if not is_lr and role=='swimlane-title' else {'roughness':.7})
            if is_lr:painter.text(label,cx-label.height/2,cy+label.width/2,align='left',rotation=-90,style=label_style,id=id+'-label',role='swimlane-label')
            else:painter.text(label,cx,cy-label.height/2,align='center',style=label_style,id=id+'-label',role='swimlane-label')
        generated=tuple(painter.commands)
    finally:painter.commands=saved_commands;painter.rough_enabled=saved_rough
    return generated+tuple(command for i,command in enumerate(commands) if i not in remove)
