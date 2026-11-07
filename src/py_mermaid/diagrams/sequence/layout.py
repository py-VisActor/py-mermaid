"""Sequence-specific column constraints, temporal bands and native primitives.

Actor bands follow actorBands.ts; this is a temporal layout, never a graph
layout substitution. Every message/fragment keeps source chronological order.
"""
from dataclasses import dataclass
import math,re
from py_mermaid.model.flowchart import Box
from py_mermaid.config.values import thaw_value
from py_mermaid.runtime.common import config_dict
from .presentation import Presentation
from .message_geometry import message_geometry,marker_geometry


@dataclass(frozen=True)
class SequenceLayout:
    actors: tuple[tuple[str,Box], ...]
    events: tuple[tuple[int,Box], ...]
    activations: tuple[tuple[str,Box], ...]
    fragments: tuple[tuple[str,Box], ...]
    width: float
    height: float


DEFAULTS=dict(activationWidth=10,diagramMarginX=50,diagramMarginY=10,actorMargin=50,width=150,height=65,
    boxMargin=10,boxTextMargin=5,noteMargin=10,messageMargin=35,messageAlign='center',mirrorActors=True,
    bottomMarginAdj=1,rightAngles=False,showSequenceNumbers=False,actorFontSize=14,actorFontFamily='"Open Sans", sans-serif',
    actorFontWeight=400,noteFontSize=14,noteFontFamily='"trebuchet ms", verdana, arial, sans-serif',noteFontWeight=400,
    noteAlign='center',messageFontSize=16,messageFontFamily='"trebuchet ms", verdana, arial, sans-serif',
    messageFontWeight=400,wrap=False,wrapPadding=10,labelBoxWidth=50,labelBoxHeight=20,hideUnusedParticipants=False)
COLOR_THEMES={'redux-color','redux-dark-color'}


def _number(value,default=0):
    match=re.match(r'^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))',str(value))
    return float(match[1]) if match else default


async def build(diagram,p):
    model=diagram.model;p=Presentation(p,model.actors);cfg=config_dict(diagram);c={**DEFAULTS,**cfg.get('sequence',{})};tv=cfg.get('themeVariables',{}) or {}
    # Source draw sets conf=sequence, then bounds.init calls setConf(root).
    # Generic truthy root font aliases overwrite all three specific role keys.
    for key in ('fontFamily','fontSize','fontWeight'):
        if cfg.get(key):
            for role in ('actor','note','message'):c[role+key[0].upper()+key[1:]]=cfg[key]
    from .parser import KINDS
    from py_mermaid.model.flowchart import MermaidError
    unsupported=[a.kind for a in model.actors if a.kind not in KINDS]
    if unsupported:raise MermaidError('Fixed sequence renderer has no actor handler for '+unsupported[0],code='SOURCE_RENDER_ERROR')
    look=c.get('look',cfg.get('look','neo'));theme=c.get('theme',cfg.get('theme','redux-color'))
    def color(name,default):return tv.get(name,default)
    stroke=color('actorBorder','#28253D');fill=color('actorBkg','#FFFFFF');textcolor=color('actorTextColor','#28253D')
    signalcolor=color('signalColor','#28253D');signaltext=color('signalTextColor','#28253D')
    fills=tv.get('bkgColorArray',());borders=tv.get('borderColorArray',())
    pad=_number(c['wrapPadding']);margin=_number(c['diagramMarginX']);top=_number(c['diagramMarginY']);gap=_number(c['actorMargin'])
    boxmargin=_number(c['boxMargin']);note_pad=_number(c['noteMargin']);message_gap=_number(c['messageMargin'])
    activity_width=_number(c['activationWidth']);width=_number(c['width']);height=_number(c['height'])
    used={e.source for e in model.events}|{e.target for e in model.events}
    actors=[a for a in model.actors if not c['hideUnusedParticipants'] or a.id in used]
    indices={a.id:i for i,a in enumerate(actors)}
    def measure(text,role,wrap=False,wrap_width=None):
        prefix='actor' if role=='actor' else 'note' if role=='note' else 'message'
        return p.measure_role(text,prefix,size=_number(c[prefix+'FontSize'],14),family=c[prefix+'FontFamily'],weight=str(c[prefix+'FontWeight']),
                         html=True,width=wrap_width if wrap else None,align=c.get(prefix+'Align','center'))
    actor_text={a.id:measure(a.label,'actor',a.wrap,width-2*pad) for a in actors}
    box_shapes={'participant','collections','queue'}
    row_height=max([height]+[56+t.height if look=='neo' else max(height,t.height) if a.wrap else height for a in actors for t in [actor_text[a.id]]])
    actor_width={a.id:width if a.wrap else max(width,actor_text[a.id].width+2*pad) for a in actors}
    label_height=max([0]+[measure(b.title,'actor',b.wrap,width).height for b in model.boxes if b.title])
    title_box=p.measure(model.title,size=18,html=False) if model.title else None
    title_height=title_box.height+10 if title_box else 0
    row_top=top+title_height+(label_height+2*boxmargin if model.boxes else 0)
    events=model.events;texts={};note_widths={}
    centers=[];cursor=margin+boxmargin
    for a in actors:centers.append(cursor+actor_width[a.id]/2);cursor+=actor_width[a.id]+gap
    for i,e in enumerate(events):
        if e.kind=='message':texts[i]=measure(e.text,'message',e.wrap,width-2*pad)
        elif e.kind=='note':texts[i]=measure(e.text,'note',e.wrap,width-2*note_pad);note_widths[i]=max(width,texts[i].width+2*note_pad)
        elif e.text and e.kind!='rect_start':texts[i]=measure('['+e.text+']','message',e.wrap,max(width,len(actors)*width/2))
    # Source actor margins account for all message and over-note labels. Solve
    # monotone pair distances; no fixed fixture coordinates or graph fallback.
    for i,e in enumerate(events):
        if e.source not in indices or e.target not in indices:continue
        a,b=sorted((indices[e.source],indices[e.target]))
        if a==b:continue
        required=texts[i].width+2*pad if e.kind=='message' else note_widths.get(i,0) if e.placement=='over' else 0
        current=centers[b]-centers[a]
        if required>current:
            extra=(required-current)/(b-a)
            centers=[v+extra*max(0,min(k-a,b-a)) for k,v in enumerate(centers)]
    left_extra=max([0]+[note_widths[i]+note_pad-actor_width[e.source]/2 for i,e in enumerate(events) if e.kind=='note' and e.source in indices and indices[e.source]==0 and e.placement=='left of'])
    centers=[v+left_extra for v in centers];xs=dict(zip((a.id for a in actors),centers))
    extent_left=min([margin]+[xs[a.id]-actor_width[a.id]/2-boxmargin for a in actors])
    extent_right=max([margin+width]+[xs[a.id]+actor_width[a.id]/2+boxmargin for a in actors])
    y=row_top+row_height+message_gap;placed={};frames=[];frame_stack=[];active={a.id:[] for a in actors};activation_boxes=[]
    event_depth={};birth={};death={};sections=[];activation_levels={}
    for i,e in enumerate(events):
        if e.kind.endswith('_start'):
            kind=e.kind[:-6];header=0 if kind=='rect' else max(_number(c['labelBoxHeight']),texts.get(i,p.measure('',size=14)).height+10)
            extras=[]
            if kind=='par_over':
                nesting=0
                for j in range(i+1,len(events)):
                    other=events[j]
                    if other.kind.endswith('_start'):nesting+=1
                    elif other.kind.endswith('_end'):
                        if not nesting:break
                        nesting-=1
                    elif not nesting and other.kind=='and':extras.append((j,max(20,texts[j].height+10)))
            full_header=header+sum(h for _,h in extras)
            frame_stack.append(dict(kind=kind,start=i,y=y-8,header=header,sections=[],max_y=y,base=y+full_header,depth=len(frame_stack),parallel_labels=extras))
            placed[i]=Box(extent_left,y-8,extent_right-extent_left,header);y+=full_header+boxmargin;continue
        if e.kind in {'else','and','option'}:
            frame=frame_stack[-1];frame['max_y']=max(frame['max_y'],y)
            if frame['kind']=='par_over':
                sy=frame['y']+frame['header']+sum(h for j,h in frame['parallel_labels'] if j<i)
                h=next(h for j,h in frame['parallel_labels'] if j==i)
                sections.append((i,sy,e,frame['start']));placed[i]=Box(extent_left,sy,extent_right-extent_left,h)
                y=frame['base']+boxmargin
            else:
                h=max(20,texts[i].height+10);sections.append((i,y,e,frame['start']));placed[i]=Box(extent_left,y,extent_right-extent_left,h);y+=h+boxmargin
            continue
        if e.kind.endswith('_end'):
            frame=frame_stack.pop();y=max(y,frame['max_y'])+boxmargin;frame['bottom']=y;frames.append(frame);placed[i]=Box(extent_left,y,extent_right-extent_left,0);y+=boxmargin;continue
        if e.kind=='activate':
            if e.source in active:
                # Inline '+' is a separate DB activation immediately after its
                # message; it begins at the message line +2, not the next row.
                previous=events[i-1] if i else None
                inline=previous is not None and previous.kind=='message' and previous.offset==e.offset
                start=placed[i-1].y+texts[i-1].height+12 if inline else y-4
                active[e.source].append((start,len(active[e.source])))
            placed[i]=Box(xs.get(e.source,margin),y,activity_width,0);continue
        if e.kind=='deactivate':
            if e.source in active and active[e.source]:
                start,level=active[e.source].pop();previous=events[i-1] if i else None
                inline=previous is not None and previous.kind=='message' and previous.offset==e.offset
                end=placed[i-1].y+texts[i-1].height+10+(30 if previous.source==previous.target else 0) if inline else y
                if start+18>end:start=end-6;end+=12  # source activeEnd minimum visible bar
                ab=Box(xs[e.source]+(level-1)*activity_width/2,start,activity_width,end-start);activation_boxes.append((e.source,ab));activation_levels[(e.source,ab)]=level
            placed[i]=Box(xs.get(e.source,margin),y,activity_width,0);continue
        t=texts.get(i)
        if e.kind=='note':
            w=note_widths[i];h=t.height+2*note_pad
            x=xs[e.source]-w-note_pad if e.placement=='left of' else xs[e.source]+note_pad if e.placement=='right of' else (xs[e.source]+xs[e.target]-w)/2
            if e.source!=e.target and e.placement=='over':w=max(w,abs(xs[e.source]-xs[e.target])+width/2);x=min(xs[e.source],xs[e.target])-width/4
            placed[i]=Box(x,y,w,h);extent_left=min(extent_left,x-boxmargin);extent_right=max(extent_right,x+w+boxmargin);y+=h+message_gap;continue
        if e.kind=='message':
            level_s=len(active.get(e.source,()));level_t=len(active.get(e.target,()))
            event_depth[i]=(level_s,level_t)
            h=t.height+10+(25 if e.source==e.target else 0)
            if e.source==e.target:
                extent_right=max(extent_right,xs[e.source]+max(width/2,t.width/2)+pad)
                extent_left=min(extent_left,xs[e.source]-t.width/2-pad)
            placed[i]=Box(min(xs[e.source],xs[e.target]),y,abs(xs[e.source]-xs[e.target]),h)
            lifecycle=False
            for a in actors:
                if a.created is not None and i>=a.created and a.id not in birth:birth[a.id]=y+t.height+10-row_height/2;lifecycle=True
                if a.destroyed is not None and i>=a.destroyed and a.id not in death:death[a.id]=y+t.height+10;lifecycle=True
            if lifecycle:h+=row_height/2
            y+=max(message_gap,h+message_gap/2)
    if frames:
        required=max([extent_right-extent_left]+[_number(c['labelBoxWidth'])+texts[f['start']].width+2*boxmargin+8 for f in frames if f['kind']!='rect' and f['start'] in texts])
        expansion=max(0,required-(extent_right-extent_left))/2+max(f['depth'] for f in frames)*boxmargin
        extent_left-=expansion;extent_right+=expansion
    for frame in frames:
        # Nested frames receive inset horizontal lanes while retaining all
        # actors needed by the temporal block.
        inset=frame['depth']*boxmargin
        frame['box']=Box(extent_left-boxmargin+inset,frame['y'],extent_right-extent_left+2*boxmargin-2*inset,frame['bottom']-frame['y'])
    bottom=y+_number(c['bottomMarginAdj']);actor_boxes={a.id:Box(xs[a.id]-actor_width[a.id]/2,birth.get(a.id,row_top),actor_width[a.id],row_height) for a in actors}
    for name,stack in active.items():
        for start,level in stack:
            ab=Box(xs[name]+(level-1)*activity_width/2,start,activity_width,max(2,bottom-start));activation_boxes.append((name,ab));activation_levels[(name,ab)]=level
    total_height=bottom+(row_height if c['mirrorActors'] else 0)+top
    # Backdrops first. Source rect sections are true colors, not opaque labels.
    for bi,b in enumerate(model.boxes):
        members=[a for a in actors if a.id in b.actors]
        if not members:continue
        left=min(actor_boxes[a.id].x for a in members)-boxmargin;right=max(actor_boxes[a.id].x+actor_boxes[a.id].width for a in members)+boxmargin
        p.rect(left,top+title_height,right-left,total_height-top-title_height,fill=b.color,stroke='none',id=f'box-{bi}',role='participant-box')
        if b.title:
            t=measure(b.title,'actor',b.wrap,right-left-2*boxmargin);p.text(t,left+(right-left-t.width)/2,top+title_height+boxmargin,color=textcolor,id=f'box-{bi}',role='box-title')
    for frame in sorted(frames,key=lambda f:f['depth']):
        if frame['kind']=='rect':
            b=frame['box'];e=events[frame['start']];p.rect(b.x,b.y,b.width,b.height,fill=e.text or color('rectBkgColor',color('actorBkg','rgba(128,128,128,0.5)')),stroke='none',id=f'fragment-{frame["start"]}',role='rect-section')
    # Lifelines terminate at their actual creation/destruction intervals.
    for a in actors:
        b=actor_boxes[a.id]
        legacy={'actor':80,'boundary':80,'control':75,'entity':75,'database':b.height+2*_number(c['boxTextMargin'])}
        start=b.y+(b.height if look=='neo' else legacy.get(a.kind,b.height));end=death[a.id]-row_height/2 if a.id in death and c['mirrorActors'] else death.get(a.id,bottom)
        p.line(xs[a.id],start,xs[a.id],max(start,end),stroke=color('actorLineColor','#28253D'),line_width=.5,id=a.id,role='lifeline')
    for name,b in activation_boxes:
        ai=indices[name];af=fills[ai%len(fills)] if fills and theme in COLOR_THEMES else color('mainBkg',fill) if theme in COLOR_THEMES else color('activationBkgColor','#F4F4F4')
        ab=borders[ai%len(borders)] if borders and theme in COLOR_THEMES else color('activationBorderColor',stroke)
        p.rect(b.x,b.y,b.width,b.height,fill=af,stroke=ab,id=name,role='activation'+str(activation_levels[(name,b)]%3))
    for frame in sorted(frames,key=lambda f:f['depth']):
        if frame['kind']=='rect':continue
        b=frame['box'];identity=f'fragment-{frame["start"]}';kind=frame['kind'];kind='par' if kind=='par_over' else kind
        border=color('labelBoxBorderColor',stroke)
        p.rect(b.x,b.y,b.width,b.height,fill='none',stroke=border,line_width=2,dash=(2,2),id=identity,role='fragment')
        tabwidth=max(_number(c['labelBoxWidth']),p.measure(kind,size=14).width+12);tabheight=_number(c['labelBoxHeight'])+(15 if look=='neo' else 0)
        p.polygon(((b.x,b.y),(b.x+tabwidth,b.y),(b.x+tabwidth,b.y+tabheight-7),(b.x+tabwidth-8.4,b.y+tabheight),(b.x,b.y+tabheight)),fill=color('labelBoxBkgColor',fill),stroke=border,id=identity,role='fragment-label-box')
        p.text(kind,b.x+5,b.y+2,size=14,color=color('labelTextColor',textcolor),id=identity,role='fragment-kind')
        t=texts.get(frame['start'])
        if t:p.text(t,b.x+tabwidth/2+b.width/2-t.width/2,b.y+_number(c['boxMargin'])+_number(c['boxTextMargin']),color=color('loopTextColor',textcolor),id=identity,role='fragment-title')
    for i,sy,e,start in sections:
        frame=next(f for f in frames if f['start']==start);b=frame['box'];p.line(b.x,sy,b.x+b.width,sy,stroke=color('labelBoxBorderColor',stroke),dash=(3,3),id=f'section-{i}',role='fragment-divider')
        p.text(texts[i],b.x+(b.width-texts[i].width)/2,sy+_number(c['boxMargin'])+_number(c['boxTextMargin']),color=color('loopTextColor',textcolor),id=f'section-{i}',role='fragment-section')
    def actor_paint(a,b,footer=False):
        i=indices[a.id];afill=fills[i%len(fills)] if fills and theme in COLOR_THEMES else fill;astroke=borders[i%len(borders)] if borders and theme in COLOR_THEMES else stroke
        cx=b.x+b.width/2;t=actor_text[a.id];kind=a.kind if a.kind in {'actor','boundary','collections','control','database','entity','queue'} else 'participant'
        role='actor-footer' if footer else 'actor';radius=6 if look=='neo' else 3
        if kind in box_shapes:
            if kind=='collections':p.rect(b.x-5,b.y-5,b.width,b.height,fill=afill,stroke=astroke,id=a.id,role=role,radius=radius)
            p.rect(b.x,b.y,b.width,b.height,fill=afill,stroke=astroke,line_width=_number(tv.get('strokeWidth',1)),radius=radius,id=a.id,role=role)
            if kind=='queue':
                p.ellipse(b.x+10,b.y+b.height/2,10,b.height/2,fill=afill,stroke=astroke,id=a.id,role='actor-detail')
                p.path(f'M {b.x+b.width-10} {b.y} A 10 {b.height/2} 0 0 1 {b.x+b.width-10} {b.y+b.height}',stroke=astroke,id=a.id,role='actor-detail')
            ty=b.y+(b.height-t.height)/2
        else:
            # neo actorBands: shared datum,44px glyph band,6px gaps.
            gy=b.y+6 if footer else b.y+b.height-6-t.height-6-44
            cy=gy+22;ty=gy+44+6 if footer else b.y+b.height-6-t.height
            if look!='neo':
                cy=b.y+({'control':32,'entity':10 if footer else 25,'boundary':12}.get(kind,22))
                shift=21 if kind in {'entity','boundary'} else 0
                cy+=shift;gy=cy-22
                label_offset={'actor':35,'database':35,'control':27 if footer else 34,'entity':15 if footer else 30,'boundary':15}.get(kind,0)
                ty=b.y+label_offset+b.height/2-t.height/2+shift
            if kind=='actor':
                scale=44/65 if look=='neo' else 1
                anchor=gy+44-60*scale if look=='neo' else b.y
                gx=lambda offset:cx+offset*scale
                yy=lambda offset:anchor+offset*scale
                p.ellipse(cx,yy(10),15*scale,15*scale,fill=afill,stroke=astroke,line_width=2,id=a.id,role=role)
                for x1,y1,x2,y2 in ((cx,yy(25),cx,yy(45)),(gx(-18),yy(33),gx(18),yy(33)),(gx(-18),yy(60),cx,yy(45)),(cx,yy(45),gx(16),yy(60))):p.line(x1,y1,x2,y2,stroke=astroke,line_width=2,id=a.id,role=role)
            elif kind=='database':
                ww=b.width/3;rx=ww/2;ry=rx/(2.5+ww/50);hh=44 if look=='neo' else ww
                cylinder_y=gy+44-hh-ry if look=='neo' else b.y
                xx=b.x+ww;yy0=cylinder_y+2*ry
                p.path(f'M {xx} {yy0} a {rx} {ry} 0 0 0 {ww} 0 a {rx} {ry} 0 0 0 {-ww} 0 l 0 {hh-2*ry} a {rx} {ry} 0 0 0 {ww} 0 l 0 {-hh+2*ry}',fill=afill,stroke=astroke,id=a.id,role=role)
            else:
                p.ellipse(cx,cy,22,22,fill=afill,stroke=astroke,line_width=2,id=a.id,role=role)
                if kind=='boundary':p.line(cx-55,cy,cx-15,cy,stroke=astroke,id=a.id,role='actor-detail');p.line(cx-55,cy-10,cx-55,cy+10,stroke=astroke,id=a.id,role='actor-detail')
                if kind=='control':p.polyline(((cx-4,gy-4),(cx+5,gy),(cx-4,gy+5)),stroke=astroke,id=a.id,role='actor-detail')
                if kind=='entity':p.line(cx-22,gy+44,cx+22,gy+44,stroke=astroke,line_width=2,id=a.id,role='actor-detail')
        p.text(t,cx-t.width/2,ty,color=textcolor,id=a.id,role='actor-label')
        metadata=thaw_value(a.metadata)
        icon=metadata.get('properties',{}).get('icon') if isinstance(metadata,dict) else None
        if icon:p.asset(str(icon).removeprefix('@'),b.x+b.width-20,b.y+10,16,16,kind='image',id=a.id)
    for a in actors:
        actor_paint(a,actor_boxes[a.id])
        if c['mirrorActors']:actor_paint(a,Box(actor_boxes[a.id].x,death[a.id]-row_height/2 if a.id in death else bottom,actor_boxes[a.id].width,row_height),True)
    for i,e in enumerate(events):
        if e.kind not in {'message','note'}:continue
        b=placed[i];t=texts[i];identity=f'message-{i}'
        if e.kind=='note':
            p.rect(b.x,b.y,b.width,b.height,fill=color('noteBkgColor','#FFF5AD'),stroke=color('noteBorderColor','#AAAA33'),id=identity,role='note')
            align=c['noteAlign'];tx=b.x+note_pad if align=='left' else b.x+b.width-note_pad-t.width if align=='right' else b.x+(b.width-t.width)/2
            p.text(t,tx,b.y+note_pad,color=color('noteTextColor',textcolor),id=identity,role='note-text');continue
        sx=xs[e.source];tx=xs[e.target];sy=b.y+t.height+10;ls,lt=event_depth[i];direction=1 if tx>=sx else -1
        start_override=end_override=None
        glyph_types={'actor','control','entity','database'}
        def lifecycle_half(name):
            # Source ACTOR_TYPE_WIDTH=18*2 for these glyph participants; other
            # handlers attach to the actual participant rectangle boundary.
            return 18 if actors[indices[name]].kind in glyph_types else actor_width[name]/2
        if e.target in birth and birth[e.target]==sy-row_height/2:
            end_override=tx-direction*(lifecycle_half(e.target)+3)
        elif c['mirrorActors'] and e.source in death and death[e.source]==sy:
            start_override=sx+direction*lifecycle_half(e.source)
        elif c['mirrorActors'] and e.target in death and death[e.target]==sy:
            end_override=tx-direction*(lifecycle_half(e.target)+3)
        following=events[i+1] if i+1<len(events) else None
        first_activate=following is not None and following.kind=='activate' and following.source==e.target and following.offset==e.offset
        geom=message_geometry(e.arrow,e.connection,sx,tx,ls,lt,activity_width,
            y=sy,numbered=e.number is not None,look=look,activate=first_activate,
            self_reference=e.source==e.target,right_angles=c['rightAngles'],loop_width=max(width/2,t.width/2),
            start_override=start_override,end_override=end_override)
        dash=(3,3) if geom.dashed else ()
        if geom.self_message:p.path(geom.path,fill='none',stroke=signalcolor,line_width=1.5,dash=dash,id=identity,role='message')
        else:p.line(*geom.painted_start,*geom.painted_end,stroke=signalcolor,line_width=1.5,dash=dash,id=identity,role='message')
        sx,tx=geom.startx,geom.stopx
        lx=min(sx,tx)+(abs(tx-sx)-t.width)/2
        align=c['messageAlign']
        if align=='left':lx=min(sx,tx)+pad
        elif align=='right':lx=max(sx,tx)-t.width-pad
        p.text(t,lx,b.y,color=signaltext,id=identity,role='message-text')
        for at_start,name,point,tangent in ((True,geom.start_marker,geom.painted_start,geom.start_tangent),
                                           (False,geom.end_marker,geom.painted_end,geom.end_tangent)):
            if not name:continue
            shape,matrix,kind,marker_fill,marker_stroke,marker_width=marker_geometry(name,point,tangent,at_start=at_start,line_width=p.message_stroke_width)
            colors={'signal':signalcolor,'text':color('textColor',signalcolor),'black':'black','none':'none'}
            marker_id=p.render_id+'-'+name
            marker_style=p.style('',tag='path',base={'fill':colors[marker_fill],'stroke':colors[marker_stroke],'stroke_width':marker_width},
                ancestors=(('svg',('sequenceDiagram',),''),('defs',(),''),('marker',(),marker_id)))
            p.marker_path(shape,kind=kind,transform=matrix,style=marker_style,id=identity)
        for cx in geom.central_circles:
            p.ellipse(cx,sy,5,5,fill=color('textColor',signalcolor),stroke='none',line_width=0,id=identity,role='central-connection')
        if geom.number_x is not None:
            nx=geom.number_x
            # Source markerUnits=strokeWidth; its zero-length line's inherited
            # `.actor-man circle, line` rule supplies the default 2px scale.
            number_line=p.style('',tag='line',base={'stroke_width':2},ancestors=(('svg',('sequenceDiagram',),''),))
            radius=6*number_line.stroke_width
            number_style=p.style('',tag='circle',base={'fill':signalcolor,'stroke':'none','stroke_width':0},
                ancestors=(('svg',('sequenceDiagram',),''),('defs',(),''),('marker',(),p.render_id+'-sequencenumber')))
            p.ellipse(nx,sy,radius,radius,style=number_style,id=identity,role='sequence-number-box')
            number_text=f'{e.number:g}';number_size=7 if len(number_text)>5 else 9 if len(number_text)>3 else 12
            nt=p.measure(number_text,size=number_size,family='sans-serif',html=False)
            p.text(nt,nx-nt.width/2,sy+4-nt.ascent,color=color('sequenceNumberColor','#FFFFFF'),id=identity,role='sequence-number')
    if title_box:p.text(title_box,(extent_left+extent_right-title_box.width)/2,top,color=textcolor,id='diagram-title',role='diagram-title')
    layout=SequenceLayout(tuple(actor_boxes.items()),tuple(placed.items()),tuple(activation_boxes),tuple((f['kind'],f['box']) for f in frames),extent_right+margin,total_height)
    return p.finish(width=extent_right+margin,height=total_height,padding=0,layout=layout,measured=tuple(actor_text.items()))
