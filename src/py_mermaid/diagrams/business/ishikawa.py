"""Dedicated alternating-bone Ishikawa layout from ishikawaRenderer.ts."""
from dataclasses import dataclass
import math
import re
from ...runtime.common import make_diagram,config_dict,error,sanitize_text,utf16_length

@dataclass(frozen=True)
class Cause:
    text:str
    children:tuple=()

def parse(document,config):
    records=[];offset=0
    for raw in document.cleaned.splitlines(keepends=True):
        if raw.strip() and not raw.lstrip().startswith('%%'):records.append((offset,raw.rstrip('\r\n')))
        offset+=len(raw)
    if not records or not re.fullmatch(r'\s*ishikawa(?:-beta)?\s*',records[0][1],re.I):raise error(document,0,'Expected ishikawa')
    if len(records)<2:raise error(document,len(document.cleaned),'Expected effect label')
    root=None;stack=[];base=None
    for at,line in records[1:]:
        level=len(line)-len(line.lstrip());node=[sanitize_text(line.strip(),config),[]]
        if root is None:root=node;stack=[(0,node)];continue
        if base is None:base=level
        level=max(1,level-base+1)
        while len(stack)>1 and stack[-1][0]>=level:stack.pop()
        stack[-1][1][1].append(node);stack.append((level,node))
    def freeze(node):return Cause(node[0],tuple(freeze(x) for x in node[1]))
    return make_diagram('ishikawa',document,config,freeze(root))

def wrap(text,n):
    # Renderer wrapText uses JavaScript String.length before font layout.
    if utf16_length(text)<=n:return text
    lines=[]
    for word in text.split():
        if lines and utf16_length(lines[-1])+1+utf16_length(word)<=n:lines[-1]+=' '+word
        else:lines.append(word)
    return '\n'.join(lines)

def flatten(children,direction):
    entries=[];order=[]
    def walk(nodes,parent,depth):
        for child in (nodes[::-1] if direction==-1 else nodes):
            i=len(entries);entries.append((wrap(child.text,15),depth,parent,len(child.children)))
            if depth%2==0:order.append(i)
            if child.children:walk(child.children,i,depth+1)
            if depth%2:order.append(i)
    walk(children,-1,2)
    return entries,order

async def build(diagram,p):
    c=config_dict(diagram);t=c['themeVariables'];root=diagram.model
    from ._source_styles import styles
    p.add_styles(styles('ishikawa',t))
    size=float(re.match(r'[\d.]+',str(c.get('fontSize',14)))[0]);causes=root.children
    rough=c.get('look')=='handDrawn';p.rough_enabled=rough
    opts={'roughness':1.5,'fillStyle':'hachure','fillWeight':2.5,'hachureGap':5}
    ancestors=(('g',('ishikawa',),''),)
    def sty(cls,tag='path',**base):return p.style(cls,tag=tag,base=base,ancestors=ancestors)
    def line(x,y,u,v,cls):
        st=sty(cls,fill='none',stroke=t['lineColor'],stroke_width=2 if rough or cls!='ishikawa-sub-branch' else 1)
        p.path(f'M{x},{y} L{u},{v}',style=st,rough_options={'roughness':1.5})
        if cls!='ishikawa-spine' and (x!=u or y!=v):
            # Source start marker points toward the parent attachment.
            dx=x-u;dy=y-v;n=math.hypot(dx,dy);ux=dx/n;uy=dy/n
            length=12 if rough else 6;width=6 if rough else 3
            path=f'M{x},{y} L{x-ux*length-uy*width},{y-uy*length+ux*width} L{x-ux*length+uy*width},{y-uy*length-ux*width} Z'
            p.path(path,style=sty('ishikawa-arrow',fill=t['lineColor'],stroke=t['lineColor'] if rough else 'none',stroke_width=1),rough_options={'roughness':1,'fillStyle':'solid'})
    def text(value,x,y,cls,anchor='end',middle=False,hanging=False,head=False):
        value=re.sub(r'<br\s*/?>','\n',value)
        st=sty(cls,'text',text_color=t['textColor'],font_family=t['fontFamily'],font_size=14 if head else size,font_weight='600' if head else 'normal',line_height=1.05)
        box=p.measure(value,html=False,style=st)
        # SVG tspan first baseline is centered around the supplied y.
        count=len(value.split('\n'));first=y-(count-1)*size*1.05/2
        top=first-(box.height/count/2 if middle else 0 if hanging else box.ascent)
        align={'end':'right','middle':'center','start':'left'}[anchor]
        p.text(box,x,top,align=align,style=st)
        left=x-(box.width if anchor=='end' else box.width/2 if anchor=='middle' else 0)
        return left,top,box
    def count(node):return sum(1+count(ch) for ch in node.children)
    up=[count(x) for x in causes[::2]];down=[count(x) for x in causes[1::2]];total=sum(up+down)
    ul=max(75,500*sum(up)/total) if total else 250;dl=max(75,500*sum(down)/total) if total else 250
    ul=max(ul,max(up,default=0)*size*2);dl=max(dl,max(down,default=0)*size*2);spine_y=max(ul,250)
    # Head dimensions are measured from the actual source head label.
    label=wrap(root.text,max(6,math.floor(110/(size*.6))))
    hs=sty('ishikawa-head-label','text',font_size=14,font_weight='600',text_color=t['textColor'],font_family=t['fontFamily'],line_height=1.05)
    hb=p.measure(label,html=False,style=hs);hw=max(60,hb.width+6);hh=max(40,hb.height*2+40)
    p.path(f'M0,{spine_y-hh/2} L0,{spine_y+hh/2} Q{hw*2.4},{spine_y} 0,{spine_y-hh/2} Z',style=sty('ishikawa-head',fill=t['mainBkg'],stroke=t['lineColor'],stroke_width=2),rough_options=opts)
    p.text(hb,(hw-hb.width)/2+3,spine_y-hb.height/2,style=hs)
    spine_x=-20;co=math.cos(math.radians(82));si=math.sin(math.radians(82))
    for pair in range(math.ceil(len(causes)/2)):
        lefts=[]
        for index,direction,length in ((pair*2,-1,ul),(pair*2+1,1,dl)):
            if index>=len(causes):continue
            cause=causes[index];length*=1 if cause.children else .2
            dx=-co*length;dy=si*length*direction;ex=spine_x+dx;ey=spine_y+dy
            line(spine_x,spine_y,ex,ey,'ishikawa-branch')
            # Cause box is inserted behind text in source; measure before paint.
            st=sty('ishikawa-label cause','text',font_size=size,font_family=t['fontFamily'],text_color=t['textColor'],line_height=1.05)
            cb=p.measure(cause.text,html=False,style=st);ty=ey+11*direction-cb.height/2
            p.path(f'M{ex-cb.width/2-20},{ty-2} h{cb.width+40} v{cb.height+4} h{-cb.width-40} Z',style=sty('ishikawa-label-box',fill=t['mainBkg'],stroke=t['lineColor'],stroke_width=2),rough_options=opts)
            p.text(cb,ex,ty,align='center',style=st);lefts.append(ex-cb.width/2)
            entries,order=flatten(cause.children,direction);ys={i:spine_y+dy*(slot+1)/(len(entries)+1) for slot,i in enumerate(order)}
            bones={-1:[spine_x,spine_y,ex,ey,len(cause.children),0]}
            for i,(value,depth,parent,nchildren) in enumerate(entries):
                y=ys[i];par=bones[parent]
                if depth%2==0:
                    fraction=(y-par[1])/(par[3]-par[1]) if par[3]!=par[1] else .5
                    x0=par[0]+(par[2]-par[0])*fraction;y0=y;x1=x0-(60+nchildren*5 if nchildren else 30)
                    cls='ishikawa-label align'
                else:
                    k=par[5];par[5]+=1;x0=par[0]+(par[2]-par[0])*(par[4]-k)/(par[4]+1);y0=par[1];x1=x0-co*(y-y0)/(si*direction)
                    cls='ishikawa-label up' if direction<0 else 'ishikawa-label down'
                line(x0,y0,x1,y,'ishikawa-sub-branch')
                tx,_,_=text(value,x1,y,cls,middle=depth%2==0,hanging=depth%2==1 and direction>0);lefts.append(tx)
                if nchildren:bones[i]=[x0,y0,x1,y,nchildren,0]
        spine_x=min(lefts)
    line(spine_x if causes else 0,spine_y,0,spine_y,'ishikawa-spine')
    return p.finish(padding=c.get('ishikawa',{}).get('diagramPadding',20))
