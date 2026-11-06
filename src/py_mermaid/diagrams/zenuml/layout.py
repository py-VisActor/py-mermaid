"""Dedicated ZenUML positioning/geometry and source native SVG paint projection."""
from importlib.resources import files
import base64,re,math,html
from dataclasses import dataclass
from py_mermaid.model.flowchart import Box
from .geometry import optimal_positions,vertical_layout
from .emoji import resolve,EMOJIS,CSS_TEXT_VALUES


FAMILY='Helvetica, Verdana, serif'


@dataclass(frozen=True)
class ZenLayout:
    participants: tuple
    statements: tuple
    occurrences: tuple
    groups: tuple
    width: float
    height: float
    paint_ir: tuple = ()


def _style_comment(raw):
    lines=raw.strip().split('\n');last=lines[-1] if lines else '';comment=[];message=[];common=[];end=0
    for m in re.finditer(r'<([^>]*)>|\(([^)]*)\)|\[([^\]]*)\]|([^<>()[\]\s]+)',last):
        if m[4]:break
        end=m.end();values=[v.strip() for v in (m[1] or m[2] or m[3]).split(',') if v.strip()]
        if m[1]:comment+=values
        elif m[2]:message+=values
        else:common+=values
    text='\n'.join(lines[:-1]+[last[end:]]).strip()
    # Comment.ts resolves emojis only from common square-bracket styles.
    emoji_values=[v for v in common if re.fullmatch(r':.+:',v) or v not in CSS_TEXT_VALUES and v in EMOJIS]
    common_styles=[v for v in common if v not in emoji_values]
    def attributes(values):
        result={};classes=[]
        for value in dict.fromkeys(values):
            if value in {'italic','oblique'}:result['font_style']=value
            elif value in {'bold','bolder','lighter'}:result['font_weight']=value
            elif value in {'underline','overline','line-through'}:result['decoration']=value
            elif value in CSS_TEXT_VALUES:result['text_color']=value
            else:classes.append(value)
        return result,tuple(classes)
    common_emojis=''.join(EMOJIS.get(v.strip(':'),v.strip(':')) for v in emoji_values)
    return (common_emojis+' '+text).strip(),attributes(common_styles+comment),attributes(common_styles+message)



def _comment_markup(value):
    """Static projection of renderComment collectLines' consumed Marked tokens.

    Inline code has no code font in source; fenced/indented blocks do. Links,
    headings, lists and raw HTML are source-unconsumed literals, never hosts.
    """
    def inline(text,depth=0):
        if depth>128:raise ValueError('Comment nesting budget exceeded')
        output=[];i=0
        while i<len(text):
            # collectLines leaves link/image tokens as their authored raw text.
            link=re.match(r'!?\[[^\]]*\](?:\([^)]*\)|\[[^\]]*\])',text[i:])
            if link:output.append(html.escape(link[0]));i+=len(link[0]);continue
            if text[i]==chr(96):
                marker=re.match(chr(96)+'+',text[i:])[0];end=text.find(marker,i+len(marker))
                if end>=0:
                    content=text[i+len(marker):end].replace('\n',' ')
                    if content.startswith(' ') and content.endswith(' ') and content.strip():content=content[1:-1]
                    output.append(html.escape(content));i=end+len(marker);continue
            found=False
            for marker,opening,closing in [('***','<strong><em>','</em></strong>'),('___','<strong><em>','</em></strong>'),('**','<strong>','</strong>'),('__','<strong>','</strong>'),('*','<em>','</em>'),('_','<em>','</em>')]:
                if text.startswith(marker,i):
                    if marker.startswith('_') and i and text[i-1].isalnum():continue
                    end=text.find(marker,i+len(marker))
                    if end>i+len(marker):output.append(opening+inline(text[i+len(marker):end],depth+1)+closing);i=end+len(marker);found=True;break
            if found:continue
            output.append(html.escape(text[i]));i+=1
        return ''.join(output)
    result=[];lines=value.split('\n');i=0
    while i<len(lines):
        fence=re.match(r'^ {0,3}(`{3,}|~{3,})[^`]*$',lines[i])
        if fence:
            marker=fence[1];body=[];i+=1
            while i<len(lines) and not re.match(r'^ {0,3}'+re.escape(marker[0])+'{'+str(len(marker))+r',}\s*$',lines[i]):body.append(lines[i]);i+=1
            result.append('<span style="font-family:monospace">'+'<br>'.join(html.escape(line) for line in body)+'</span>')
        elif re.match(r'^ {0,3}(?:#{1,6}(?:\s|$)|>|[-+*]\s|\d+[.)]\s)',lines[i]):result.append(html.escape(lines[i]))
        elif lines[i].startswith('    '):result.append('<span style="font-family:monospace">'+html.escape(lines[i][4:])+'</span>')
        else:result.append(inline(lines[i]))
        i+=1
    # Zen's Marked SVG comment entry has no Mermaid KaTeX/icon transport.
    # Keep those authored characters literal while reusing native HTML runs.
    markup='<br>'.join(result).replace('$','&#36;').replace('\\n','&#92;n')
    return re.sub(r'\b(fa[bklrs]?):fa-',r'\1&#58;fa-',markup)


async def build(diagram,p):
    model=diagram.model;participants=model.participants;indices={a.id:i for i,a in enumerate(participants)}
    def measure(text,size=14,weight='normal',italic=False,label_kind='text'):
        return p.measure(resolve(text),size=size,family=FAMILY,weight=weight,italic=italic,html=False,label_kind=label_kind)
    def style(classes,tag='text',base=None,identity=''):
        return p.style(classes,tag=tag,id=identity,base={'font_family':FAMILY,'font_size':14,'text_color':'#222','line_height':1.0,**(base or {})},ancestors=(('g',('zenuml',),''),))
    def text(label,x,y,*,classes='message-label',size=14,color='#222',weight='normal',italic=False,identity='',center=False,end=False,baseline=False,label_kind='text',resolved=None):
        st=resolved or style(classes,base={'font_size':size,'text_color':color,'font_weight':weight,'font_style':'italic' if italic else 'normal'},identity=identity)
        tb=p.measure(resolve(label),size=st.font_size,family=st.font_family,weight=st.font_weight,italic=st.font_style!='normal',html=False,label_kind=label_kind,style=st)
        p.text(tb,x-tb.width/2 if center else x-tb.width if end else x,y-tb.ascent if baseline else y,color=st.text_color,id=identity,role=classes,style=st)
        return tb
    def rect(x,y,w,h,*,classes,fill='none',stroke='#666',line_width=1,radius=0,identity='',dash=(),opacity=1):
        st=style(classes,'rect',{'fill':fill,'stroke':stroke,'stroke_width':line_width,'opacity':opacity,'dash':dash},identity)
        p.rect(x,y,w,h,fill=st.fill,stroke=st.stroke,line_width=st.stroke_width,radius=radius,dash=st.dash,opacity=st.opacity,id=identity,role=classes,style=st)
    def lines(node):
        yield node
        if node.sections:
            for _,section in node.sections:
                for n in section:yield from lines(n)
        else:
            for n in node.children:yield from lines(n)
    statements=tuple(n for node in model.statements for n in lines(node))
    measured={a.id:measure(a.label or a.id,16) for a in participants}
    physical={a.id:min(250,max(80,measured[a.id].width+16+(28 if a.type else 0)+(20 if a.emoji else 0),measure('\u00ab'+a.stereotype+'\u00bb',16).width+8 if a.stereotype else 0)) for a in participants}
    # Source coordinates' virtual participant widths include20px margin and
    # use16px text measurements for every source TextType (upstream cache rule).
    virtual={a.id:max(measured[a.id].width+(40 if a.type else 0)+(24 if a.emoji else 0),80)+20 for a in participants}
    n=len(participants);matrix=[[0.]*n for _ in range(n)]
    for i in range(n-1):matrix[i][i+1]=(virtual[participants[i].id]+virtual[participants[i+1].id])/2
    for node in statements:
        if node.source not in indices or node.target not in indices:continue
        i,j=sorted((indices[node.source],indices[node.target]));required=round(measure(node.label,16).width)+25
        if node.kind=='creation':required+=virtual[node.target]/2
        matrix[i][j]=max(matrix[i][j],required)
    positions=optimal_positions(matrix);left_gap=virtual[participants[0].id]/2 if participants else 0
    xs={a.id:left_gap+positions[i] for i,a in enumerate(participants)}
    nested_fragments=max([0]+[sum(1 for _ in node.children) for node in statements if node.kind in {'alt','tcf','loop','par','opt','critical','section'}])
    # Fragment side lanes depend on nesting depth, not the total node count.
    def depth(nodes,level=0):
        values=[level]
        for node in nodes:
            inc=1 if node.kind in {'alt','tcf','loop','par','opt','critical','section','ref'} else 0
            if node.sections:
                for _,section in node.sections:values.append(depth(section,level+inc))
            else:values.append(depth(node.children,level+inc))
        return max(values)
    fragment_depth=depth(model.statements);border=fragment_depth*10;origin_x=11+border;origin_y=34
    xs={k:v+origin_x for k,v in xs.items()}
    def comment_height(raw):return len(raw.strip().split('\n'))*20 if _style_comment(raw)[0] else 0
    placed,creations,diagram_height=vertical_layout(model.statements,origin=model.starter,comment_measurer=comment_height)
    lifeline_end=diagram_height+12;boxes={a.id:Box(xs[a.id]-physical[a.id]/2,max(28,creations.get(a.id,28))+origin_y,physical[a.id],40) for a in participants}
    width=max([100]+[xs[a.id]+virtual[a.id]/2 for a in participants])+10+border+1
    for node in statements:
        if node.source==node.target and node.target in xs:width=max(width,xs[node.target]+measure(node.label,16).width+40)
    height=diagram_height+47
    # Frame and title are the source SVG frame, not Mermaid sequence headers.
    rect(0,0,width,height,classes='frame-border-outer',fill='#666',stroke='none',radius=4)
    rect(1,1,max(0,width-2),max(0,height-2),classes='frame-border-inner',fill='white',stroke='none',radius=3)
    p.line(1,33.5,width-1,33.5,stroke='#666',id='zen-frame-header',role='frame-header-line')
    if model.title:text(model.title,5,9,classes='frame-title',size=16,weight='600',identity='diagram-title')
    groups=[]
    for group in dict.fromkeys(a.group for a in participants if a.group):
        members=[a for a in participants if a.group==group];left=min(boxes[a.id].x for a in members)-2;right=max(boxes[a.id].x+boxes[a.id].width for a in members)+2
        gy=min(boxes[a.id].y for a in members)-18.5;gb=Box(left,gy,right-left,height-gy-3)
        rect(gb.x-.5,gb.y-2,gb.width+1,gb.height+1.5,classes='group-outline',dash=(4,3),identity=group)
        rect(gb.x+.5,gb.y-1.5,gb.width-1,19.5,classes='group-title-bg',fill='white',stroke='none',identity=group)
        text(group,(left+right)/2,gy+2,classes='group-title-text',size=13,center=True,identity=group);groups.append((group,gb))
    for a in participants:p.line(xs[a.id],boxes[a.id].y+40,xs[a.id],origin_y+lifeline_end,stroke='#666',dash=(4,4),id=a.id,role='lifeline')
    def asset(name,x,y,size,identity):
        resource=files(__package__).joinpath('assets',name+'.svg')
        if not resource.is_file():return False
        raw=resource.read_bytes()
        if name=='try-catch-fragment':
            # Fixed MIT core icon has a W3C external DTD declaration only.
            # Canvas receives its self-contained geometry; never resolve a DTD.
            raw=raw.replace(b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">',b'')
        uri='data:image/svg+xml;base64,'+base64.b64encode(raw).decode('ascii')
        vendor=name in {'ec2','lambda','iam','sns','sqs','azurefunction'}
        p.asset(uri,x,y,size,size,kind='image' if vendor else 'icon',color=None if vendor else '#222',id=identity);return True
    def participant(a,b,footer=False):
        rect(b.x+1,b.y+1,max(0,b.width-2),38,classes='participant-box',fill=a.color or 'white',stroke='#666',line_width=2,radius=3,identity=a.id)
        if a.id=='_STARTER_':asset('actor',b.x+(b.width-24)/2,b.y+8,24,a.id);return
        t=measured[a.id];cy=b.y+20-.25+(8 if a.stereotype else 0);tx=xs[a.id]-t.width/2
        has_icon=files(__package__).joinpath('assets',a.type.lower()+'.svg').is_file() if a.type else False
        emoji=EMOJIS.get(a.emoji.strip(':'),a.emoji.strip(':')) if a.emoji else ''
        if has_icon:
            groupw=24+4+16+t.width+(20 if emoji else 0);gx=xs[a.id]-groupw/2
            asset(a.type.lower(),gx+4,b.y+8+(2.75 if a.type.lower()=='boundary' else 0),24,a.id)
            tx=gx+36
            if emoji:text(emoji,gx+32,cy-8,classes='participant-emoji',size=16,identity=a.id);tx=gx+56
        elif emoji:
            tx=xs[a.id]-(20+8+t.width)/2+24;text(emoji,tx-24,cy-8,classes='participant-emoji',size=16,identity=a.id)
        text(a.label or a.id,tx,cy-8,classes='participant-label',size=16,identity=a.id)
        if a.stereotype:text('\u00ab'+a.stereotype+'\u00bb',tx+t.width/2 if has_icon else xs[a.id],b.y+4,classes='stereotype-label',size=16,center=True,identity=a.id)
    for a in participants:
        if a.id not in creations:participant(a,boxes[a.id])
    # Source LocalParticipants collects declared/call targets plus lexical origin;
    # returns do not introduce their target as a participant of the fragment.
    def local_participants(node):
        result=set(node.participants)
        if node.source in xs:result.add(node.source)
        for item in lines(node):
            if item.kind in {'sync','async','creation'} or item.kind=='return' and item.return_explicit:
                result.update(v for v in (item.source,item.target) if v in xs)
        return result or set(xs)
    def immediate_frames(nodes):
        result=[]
        for n in nodes:
            if n.kind in {'alt','tcf','loop','par','opt','critical','section','ref'}:result.append(n)
            else:result.extend(immediate_frames(n.children))
        return result
    def frame(node):
        names=local_participants(node);ordered=[a.id for a in participants if a.id in names]
        left,right=ordered[0],ordered[-1]
        descendants=[]
        for _,body in node.sections:descendants.extend(immediate_frames(body))
        if not node.sections:descendants.extend(immediate_frames(node.children))
        frames=[frame(n) for n in descendants]
        lp=10+max([0]+[f[2] for f in frames if f[0]==left]);rp=10+max([0]+[f[3] for f in frames if f[1]==right])
        return left,right,lp,rp
    frame_boxes={}
    for item in placed:
        n=item.node
        if n.kind not in {'alt','tcf','loop','par','opt','critical','section','ref'}:continue
        left,right,lp,rp=frame(n)
        extra=max([0]+[round(measure(v.label,16).width)-(xs[right]-xs.get(v.source,xs[right]))-virtual[right]/2 for v in lines(n) if v.kind in {'sync','async'} and v.source==v.target])
        fw=max(100,xs[right]-xs[left]+virtual[left]/2+virtual[right]/2)+lp+rp+extra
        frame_boxes[n.offset]=(xs[left]-virtual[left]/2,fw,lp,rp,left,right)
    # buildGeometry's final padding/nesting pass is distinct from a fragment's
    # own FrameBorder. It is a position-only shift, then near-full extension.
    roots=immediate_frames(model.statements)
    global_left,global_right=(frame(roots[0])[2:4] if roots else (0,0))
    for offset,(left,fw,lp,rp,first,last) in tuple(frame_boxes.items()):frame_boxes[offset]=(left-global_left,fw,lp,rp,first,last)
    for item in placed:
        if item.node.offset not in frame_boxes:continue
        left,fw,lp,rp,first,last=frame_boxes[item.node.offset];nd=0
        for other in placed:
            if other.node.offset==item.node.offset or other.node.offset not in frame_boxes:continue
            ol,ow,*_=frame_boxes[other.node.offset]
            if ol<=left and other.top<=item.top and ol+ow>=left+fw and other.top+other.height>=item.top+item.height:nd+=1
        left+=nd*10
        logical_right=max(200,max(xs[a.id]+virtual[a.id]/2-origin_x for a in participants))+origin_x+global_right-nd*10
        if logical_right-20<=left+fw<logical_right:fw=logical_right-left
        frame_boxes[item.node.offset]=(left,fw,lp,rp,first,last)
    occurrences=[];paint_ir=[]
    for item in placed:
        node=item.node;yy=origin_y+item.top;sy=yy+item.comment_height
        if node.kind in {'sync','creation'} and node.target in xs:
            mh=40 if node.kind=='creation' else 30 if node.source==node.target else 16
            oy=boxes[node.target].y+38 if node.kind=='creation' else sy+mh-2
            h=max(24,yy+item.height-oy)
            b=Box(xs[node.target]-7+item.target_depth*7,oy,15,h)
            rect(b.x+1,b.y+1,b.width-2,max(0,b.height-2),classes='occurrence',fill='#dedede',line_width=2,identity=f'zen-{node.offset}')
            occurrences.append((node.target,b))
    for a in participants:
        if a.id in creations:participant(a,boxes[a.id])
    def bracketed(inner,x,y,role,identity):
        inner=resolve(inner)
        text('[',x,y,classes=role,baseline=True,color='#000',identity=identity)
        st=style(role,base={'opacity':.65,'text_color':'#000'},identity=identity)
        tb=text(inner,x+7.89,y,classes=role,baseline=True,identity=identity,resolved=st)
        text(']',x+7.89+tb.width+4,y,classes=role,baseline=True,color='#000',identity=identity)
    def section_text(value,x,y,identity):
        if value.startswith('[') and value.endswith(']') and value!='[else]':
            bracketed(value[1:-1].strip(),x,y,'fragment-section-label',identity);return
        if value=='[else]':text(value,x+4,y,classes='fragment-section-label',baseline=True,color='#000',identity=identity);return
        st=style('fragment-section-label',base={'opacity':.65,'text_color':'#222'},identity=identity)
        tb=p.measure(value,size=14,family=FAMILY,html=False,style=st)
        rect(x,y-15,tb.width+8,20,classes='fragment-section-background',fill='white',stroke='none',opacity=.65,identity=identity)
        if value.startswith('catch '):
            keyword,detail=value.split(' ',1);kw=text(keyword,x+4,y,classes='fragment-section-label',baseline=True,identity=identity,resolved=st)
            text(detail,x+4+kw.width+8,y,classes='fragment-section-label',baseline=True,identity=identity,resolved=st)
        else:text(value,x+4,y,classes='fragment-section-label',baseline=True,identity=identity,resolved=st)
    def number(value,x,y,identity,central=False):
        text(value,x,y,classes='seq-number',size=12,color='#6b7280',weight='100',baseline=not central,end=True,identity=identity)
    def return_draw(label,number_value,from_id,to_id,sx,tx,yy,identity,self_return=False):
        liney=math.floor(yy)
        if self_return:
            p.path('M256 0C114.84 0 0 114.84 0 256s114.84 256 256 256 256-114.84 256-256S397.16 0 256 0Zm0 469.33c-117.63 0-213.33-95.7-213.33-213.33S138.37 42.67 256 42.67 469.33 138.37 469.33 256 373.63 469.33 256 469.33Z',fill='#222',stroke='none',line_width=0,transform=(12/512,0,0,12/512,sx+4,liney-12),id=identity,role='return-icon')
            p.path('M288 192h-87.16l27.58-27.58a21.33 21.33 0 1 0-30.17-30.17l-64 64a21.33 21.33 0 0 0 0 30.17l64 64a21.33 21.33 0 0 0 30.17-30.17l-27.58-27.58H288a53.33 53.33 0 0 1 0 106.67h-32a21.33 21.33 0 0 0 0 42.66h32a96 96 0 0 0 0-192Z',fill='#222',stroke='none',line_width=0,transform=(12/512,0,0,12/512,sx+4,liney-12),id=identity,role='return-icon')
            text(label,sx+20,liney-1,classes='return-label',baseline=True,identity=identity)
        else:
            p.line(sx,liney,tx,liney,stroke='#000',line_width=2,dash=(6,4),id=identity,role='return-line')
            p.marker(tx,liney,1 if tx>sx else -1,0,kind='open',size=6,line_width=2,color='#000',id=identity)
            text(label,(sx+tx)/2+(-3.5 if tx<sx else 3.5),liney-3,classes='return-label',center=True,baseline=True,identity=identity)
            number(number_value,min(sx,tx)-4,liney-3,identity)
        paint_ir.append(dict(kind='return',semantic_id=identity,label=label,number=number_value if not self_return else '',source=from_id,target=to_id,is_self=self_return))
    for item in placed:
        node=item.node;identity=f'zen-{node.offset}';yy=origin_y+item.top;sy=yy+item.comment_height
        comment,(comment_base,comment_classes),(message_base,message_classes)=_style_comment(node.comment)
        if comment:
            cx=xs.get(node.source,origin_x)
            if node.kind in {'alt','tcf','loop','par','opt','critical','section','ref'}:cx=frame_boxes[node.offset][0]
            elif node.kind=='creation' and xs.get(node.source,0)>xs.get(node.target,0):cx=xs[node.target]
            else:cx+=7 if item.sender_depth else 0
            if comment.lstrip().startswith(chr(96)):cx+=2
            st=style(('comment-text',)+comment_classes,base={'text_color':'#333','opacity':.5,**comment_base},identity=identity)
            tb=p.measure(_comment_markup(resolve(comment)),size=st.font_size,family=st.font_family,weight=st.font_weight,italic=st.font_style!='normal',html=True,label_kind='text',style=st)
            p.text(tb,cx+1,yy,color=st.text_color,id=identity,role='comment-text',style=st)
        st=style(('message-label',)+message_classes,base=message_base,identity=identity)
        label=resolve(node.source_text if node.kind=='ref' else node.label)
        if node.kind in {'sync','async','return','creation'}:
            raw_sx=xs.get(node.source,origin_x);raw_tx=xs.get(node.target,origin_x);direction=1 if raw_tx>=raw_sx else -1
            sx=raw_sx;tx=raw_tx;selfcall=node.source==node.target
            if node.kind=='return':
                if direction<0:sx=raw_sx if not item.sender_depth else raw_sx+7*max(item.sender_depth-1,0)-7;tx=raw_tx+7*item.target_depth+1
                else:sx=raw_sx+7*item.sender_depth+1;tx=raw_tx if not item.target_depth else raw_tx+7*max(item.target_depth-1,0)-7
                return_draw(label,item.number,node.source,node.target,sx,tx,sy+15.5,identity,selfcall);continue
            if selfcall and item.sender_depth:sx+=7*item.sender_depth
            elif item.sender_depth:sx+=item.sender_depth*7 if direction>0 else (item.sender_depth-2)*7
            if node.kind=='sync' and not selfcall:tx+=(-7 if direction>0 else 7)+item.target_depth*7
            elif node.kind=='async' and item.target_depth and not selfcall:tx+=-direction*item.target_depth*7
            if node.kind=='creation':
                if item.sender_depth:sx=raw_sx+direction*item.sender_depth*7
                tx=boxes[node.target].x if direction>0 else boxes[node.target].x+boxes[node.target].width
                liney=boxes[node.target].y+20
                p.line(sx+(1 if direction>0 else 0),liney,tx,liney,stroke='#000',line_width=2,dash=(6,4),id=identity,role='creation-line')
                p.marker(tx,liney,direction,0,kind='open',size=6,line_width=2,color='#000',id=identity)
                # Parameter-bearing source guillemets add two explicit 4px gaps.
                if label.startswith('?') and label.endswith('?') and label!='?create?':label='? '+label[1:-1]+' ?'
                text(label,(sx+(1 if direction>0 else 0)+tx)/2+(-3 if direction>0 else 3.5),liney-3,center=True,baseline=True,identity=identity,resolved=st)
                number(item.number,min(sx+(1 if direction>0 else 0),tx)-4,liney-3,identity)
            elif selfcall:
                ax=sx+1;ay=sy+(20 if node.kind=='async' else 14);endx=ax+(1 if node.kind=='async' else 14)
                p.path(f'M {ax} {ay+2} H {ax+26} Q {ax+28} {ay+2} {ax+28} {ay+4} V {ay+13} Q {ax+28} {ay+15} {ax+26} {ay+15} H {endx}',stroke='#000',line_width=2,id=identity,role='message-line')
                p.marker(endx,ay+15,-1,0,kind='open' if node.kind=='async' else 'point',size=6,line_width=2,color='#000',id=identity)
                text(label,sx+6,sy+(15 if node.kind=='async' else 12),baseline=True,identity=identity,resolved=st)
                number(item.number,sx-3,sy+12,identity)
            else:
                liney=sy+15
                p.line(sx+(1 if direction>0 else 0),liney,tx+(1 if direction<0 else 0),liney,stroke='#000',line_width=2,id=identity,role='message-line')
                p.marker(tx-direction*.85,liney,direction,0,kind='open' if node.kind=='async' else 'point',size=6,line_width=2,color='#000',id=identity)
                text(label,(sx+tx)/2-direction*3.5+.5,liney-3,center=True,baseline=True,identity=identity,resolved=st)
                number(item.number,min(sx+(1 if direction>0 else 0),tx+(1 if direction<0 else 0))-4,liney-3,identity)
            paint_ir.append(dict(kind=node.kind,semantic_id=identity,label=node.label,number=item.number,source=node.source,target=node.target,is_self=selfcall))
            if node.assignment and not selfcall:
                children_count=len(node.children);ret_number=item.number+'.'+str(children_count+1)
                ry=yy+item.height-2
                if node.kind=='creation':
                    ret_sx=raw_tx+(-6 if direction>0 else 8);ret_tx=raw_sx+7*max(item.sender_depth-1,0)+(9 if direction>0 else -7) if item.sender_depth else raw_sx
                else:
                    ret_sx=raw_tx+(-6 if direction>0 else 8)+item.target_depth*7
                    ret_tx=sx+(2 if direction>0 else 0) if item.sender_depth else sx+(2 if direction>0 else 1)
                return_draw(node.assignee or node.assignment,ret_number,node.target,node.source,ret_sx,ret_tx,ry,identity+'-assignment-return')
            continue
        if node.kind=='divider':
            label=re.sub(r'^=+\s*|\s*=+$','',label).strip();liney=yy+20;t=measure(label,14);bw=t.width+18;bx=(width-bw)/2
            p.line(origin_x,liney,bx,liney,stroke='#aaaa33',id=identity,role='divider-line');p.line(bx+bw,liney,width-10,liney,stroke='#aaaa33',id=identity,role='divider-line')
            rect(bx+.5,liney-13.5,bw-1,27,classes='divider-bg',fill='#fff5ad',stroke='#aaaa33',radius=2,identity=identity)
            text(label,width/2,liney-7,classes='divider-label',color='#333',center=True,identity=identity);paint_ir.append(dict(kind='divider',semantic_id=identity,label=label,number=item.number));continue
        left,fw,lp,rp,left_id,right_id=frame_boxes[node.offset];right=left+fw;hy=sy+1
        rect(left+.5,yy+.5,fw-1,max(1,item.height-1),classes='fragment-border',radius=4,identity=identity)
        rect(left+1,hy,fw-2,25,classes='fragment-header',fill='#dedede',stroke='none',opacity=.498,identity=identity)
        icon={'alt':'alt-fragment','loop':'loop-fragment','par':'par-fragment','opt':'opt-fragment','critical':'critical-fragment','tcf':'try-catch-fragment','section':'section-fragment','ref':'ref-fragment'}.get(node.kind)
        if icon:asset(icon,left+5,hy,20,identity)
        text({'tcf':'Try'}.get(node.kind,node.kind.title()),left+27,hy+5,classes='fragment-label',weight='600',color='#000',identity=identity)
        if label:bracketed(label,left+1,hy+40,'fragment-condition',identity)
        section_labels=[]
        for j,(section_label,section_y) in enumerate(item.sections):
            if not j:continue
            syy=origin_y+section_y-37;p.line(left+1,syy+.5,right-1,syy+.5,stroke='#e5e7eb',id=identity,role='fragment-separator')
            section_labels.append(section_label)
            section_text(section_label,left+1,syy+16,identity+'-section-'+str(j))
        if node.kind=='par':
            for child in node.children[1:]:
                child_item=next(v for v in placed if v.node.offset==child.offset);liney=origin_y+child_item.top-.5
                p.line(left+1+lp+virtual[left_id]/2,liney,right-1,liney,stroke='#e5e7eb',id=identity,role='fragment-separator')
                section_labels.append('')
        number(item.number,left-3,hy+3.5,identity,True)
        paint_ir.append(dict(kind='fragment',semantic_id=identity,fragment_kind=node.kind,label=node.source_text if node.kind=='ref' else node.label,number=item.number,sections=tuple(section_labels),participants=tuple(a.id for a in participants if a.id in local_participants(node))))
    layout=ZenLayout(tuple(boxes.items()),placed,tuple(occurrences),tuple(groups),width,height,tuple(paint_ir))
    return p.finish(width=width,height=height,padding=0,layout=layout,measured=tuple(measured.items()))
