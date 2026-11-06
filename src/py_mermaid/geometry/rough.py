"""Pure seeded rough stroke and scanline hachure geometry.

Random/_line/_bezierTo translated from roughjs4.6.6 MIT math.js/renderer.js.
SVG arcs use the standard endpoint-to-center conversion; hachure is an even-odd
scanline fill in rotated coordinates. No native canvas or image postprocessing.
"""
from __future__ import annotations
from dataclasses import dataclass
import math,random,re
from ..model.flowchart import Box,MermaidError

@dataclass(frozen=True)
class RoughGeometry:
    stroke_path:str
    fill_path:str
    bounds:Box
    fill_width:float=1.5
    fill_style:str="hachure"

class Random:
    def __init__(self,seed=0):self.seed=seed
    def next(self):
        # Source truthiness is evaluated before Math.imul applies ToInt32.
        if self.seed and not (isinstance(self.seed,float) and math.isnan(self.seed)):
            integer=math.trunc(float(self.seed)) if math.isfinite(self.seed) else 0
            self.seed=(48271*(integer&0xffffffff))&0xffffffff
            return (self.seed&0x7fffffff)/2147483648
        return random.random()

_ARITY={'M':2,'L':2,'H':1,'V':1,'C':6,'S':4,'Q':4,'T':2,'A':7,'Z':0}
def _segments(path):
    tokens=re.findall(r'[a-zA-Z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',path)
    i=0;command=None;current=(0.,0.);start=current;control=None;prior=''
    while i<len(tokens):
        if tokens[i].isalpha():command=tokens[i];i+=1
        if command is None or command.upper() not in _ARITY:raise MermaidError('Invalid rough SVG path',code='INVALID_GEOMETRY')
        op=command.upper();relative=command.islower();n=_ARITY[op]
        if op=='Z':yield ('L',current,*start);current=start;command=None;prior='Z';continue
        if i+n>len(tokens):raise MermaidError('Truncated rough path',code='INVALID_GEOMETRY')
        values=list(map(float,tokens[i:i+n]));i+=n
        x,y=current
        if op=='H':end=(values[0]+(x if relative else 0),y);yield('L',current,*end)
        elif op=='V':end=(x,values[0]+(y if relative else 0));yield('L',current,*end)
        elif op in {'M','L','T'}:
            end=(values[0]+(x if relative else 0),values[1]+(y if relative else 0))
            if op=='M':yield('M',current,*end);start=end;command='l' if relative else 'L'
            elif op=='L':yield('L',current,*end)
            else:
                q=(2*x-control[0],2*y-control[1]) if prior in {'Q','T'} and control else current
                yield('C',current,x+2*(q[0]-x)/3,y+2*(q[1]-y)/3,end[0]+2*(q[0]-end[0])/3,end[1]+2*(q[1]-end[1])/3,*end);control=q
        elif op in {'C','S','Q'}:
            if relative:values=[v+(x if j%2==0 else y) for j,v in enumerate(values)]
            if op=='C':a,b,end=tuple(values[:2]),tuple(values[2:4]),tuple(values[4:]);control=b
            elif op=='S':a=(2*x-control[0],2*y-control[1]) if prior in {'C','S'} and control else current;b=tuple(values[:2]);end=tuple(values[2:]);control=b
            else:
                q=tuple(values[:2]);end=tuple(values[2:]);a=(x+2*(q[0]-x)/3,y+2*(q[1]-y)/3);b=(end[0]+2*(q[0]-end[0])/3,end[1]+2*(q[1]-end[1])/3);control=q
            yield('C',current,*a,*b,*end)
        else:
            rx,ry,rotation,large,sweep,ex,ey=values;end=(ex+(x if relative else 0),ey+(y if relative else 0))
            if not rx or not ry or end==current:yield('L',current,*end)
            else:
                rx,ry=abs(rx),abs(ry);phi=math.radians(rotation);co,si=math.cos(phi),math.sin(phi)
                dx,dy=(x-end[0])/2,(y-end[1])/2;xp=co*dx+si*dy;yp=-si*dx+co*dy
                scale=max(1,math.sqrt(xp*xp/(rx*rx)+yp*yp/(ry*ry)));rx*=scale;ry*=scale
                factor=math.sqrt(max(0,(rx*rx*ry*ry-rx*rx*yp*yp-ry*ry*xp*xp)/(rx*rx*yp*yp+ry*ry*xp*xp)))
                if bool(large)==bool(sweep):factor=-factor
                cxp=factor*rx*yp/ry;cyp=-factor*ry*xp/rx
                cx=co*cxp-si*cyp+(x+end[0])/2;cy=si*cxp+co*cyp+(y+end[1])/2
                a0=math.atan2((yp-cyp)/ry,(xp-cxp)/rx);a1=math.atan2((-yp-cyp)/ry,(-xp-cxp)/rx);delta=(a1-a0)%(2*math.pi)
                if not sweep and delta>0:delta-=2*math.pi
                count=max(1,math.ceil(abs(delta)/(math.pi/2)));step=delta/count;previous=current
                def point(a):return(cx+rx*co*math.cos(a)-ry*si*math.sin(a),cy+rx*si*math.cos(a)+ry*co*math.sin(a))
                def tangent(a):return(-rx*co*math.sin(a)-ry*si*math.cos(a),-rx*si*math.sin(a)+ry*co*math.cos(a))
                for k in range(count):
                    a=a0+k*step;b=a+step;alpha=4/3*math.tan(step/4);p=point(a);q=point(b);u=tangent(a);v=tangent(b)
                    yield('C',previous,p[0]+alpha*u[0],p[1]+alpha*u[1],q[0]-alpha*v[0],q[1]-alpha*v[1],*q);previous=q
        current=end;prior=op

def rough_path(path:str,*,seed:int|float=0,roughness:float=.7,fill:bool=True,fill_weight:float=1.5,hachure_gap:float=1.5,hachure_angle:float=-41,fill_style:str="hachure")->RoughGeometry:
    rng=Random(seed);stroke=[];hatch=[];points=[];polygons=[];polygon=[]
    def offset(value,gain=1):return roughness*gain*(rng.next()*2-1)*value
    def emit(output,op,values):
        output.append(op+' '+' '.join(f'{v:.17g}' for v in values));points.extend(zip(values[::2],values[1::2]))
    def line(a,b,output):
        x,y=a;ex,ey=b;length=math.hypot(ex-x,ey-y);gain=1 if length<200 else .4 if length>500 else -.0016668*length+1.233334
        rand=min(2,length/10);half=rand/2
        for overlay in (False,True):
            diverge=.2+rng.next()*.2;mx=offset((ey-y)/100,gain);my=offset((x-ex)/100,gain);amount=half if overlay else rand
            jitter=lambda:offset(amount,gain)
            emit(output,'M',(x+jitter(),y+jitter()))
            emit(output,'C',(mx+x+(ex-x)*diverge+jitter(),my+y+(ey-y)*diverge+jitter(),mx+x+2*(ex-x)*diverge+jitter(),my+y+2*(ey-y)*diverge+jitter(),ex+jitter(),ey+jitter()))
    for segment in _segments(path):
        kind,current,*v=segment
        if kind=='M':
            if polygon:polygons.append(polygon)
            polygon=[tuple(v)];continue
        if not polygon:polygon=[current]
        if kind=='L':line(current,tuple(v),stroke);polygon.append(tuple(v))
        else:
            for iteration in (0,1):
                ro=2+.3*iteration
                emit(stroke,'M',current if not iteration else (current[0]+offset(2),current[1]+offset(2)))
                # Source _bezierTo consumes endpoint randomness before controls.
                end=(v[4]+offset(ro),v[5]+offset(ro))
                emit(stroke,'C',(v[0]+offset(ro),v[1]+offset(ro),v[2]+offset(ro),v[3]+offset(ro),*end))
            for k in range(1,17):
                t=k/16;u=1-t;polygon.append((u**3*current[0]+3*u*u*t*v[0]+3*u*t*t*v[2]+t**3*v[4],u**3*current[1]+3*u*u*t*v[1]+3*u*t*t*v[3]+t**3*v[5]))
    if polygon:polygons.append(polygon)
    if fill and fill_style=='solid':
        for p in polygons:
            if len(p)>2:
                emit(hatch,'M',(p[0][0]+offset(2),p[0][1]+offset(2)))
                for x,y in p[1:]:emit(hatch,'L',(x+offset(2),y+offset(2)))
                hatch.append('Z')
    elif fill and polygons:
        angle=math.radians(hachure_angle+90);co,si=math.cos(angle),math.sin(angle)
        rotated=[[(x*co-y*si,x*si+y*co) for x,y in p] for p in polygons if len(p)>2]
        if rotated:
            gap=max(1,math.floor(max(hachure_gap,.1)+.5))
            # hachure-fill straightHachureLines: start at exact ymin, advance
            # active edges every unit, emit every gap, and Math.round x values.
            edges=[]
            for p in rotated:
                for a,b in zip(p,p[1:]+p[:1]):
                    if a[1]!=b[1]:
                        low,high=(a,b) if a[1]<b[1] else (b,a)
                        edges.append({'ymin':low[1],'ymax':high[1],'x':low[0],'slope':(b[0]-a[0])/(b[1]-a[1])})
            edges.sort(key=lambda e:(e['ymin'],e['x'],e['ymax']))
            if edges:
                y=edges[0]['ymin'];active=[];iteration=0
                while active or edges:
                    if iteration>100000:raise MermaidError('Hachure budget exceeded',code='RENDER_BUDGET')
                    while edges and edges[0]['ymin']<=y:active.append(edges.pop(0))
                    active=[e for e in active if e['ymax']>y];active.sort(key=lambda e:e['x'])
                    if iteration%gap==0:
                        for a,b in zip(active[::2],active[1::2]):
                            left=math.floor(a['x']+.5);right=math.floor(b['x']+.5)
                            line((left*co+y*si,-left*si+y*co),(right*co+y*si,-right*si+y*co),hatch)
                    y+=1;iteration+=1
                    for edge in active:edge['x']+=edge['slope']
    if not points:return RoughGeometry('','',Box(0,0,0,0),fill_weight,fill_style)
    xs,ys=zip(*points);return RoughGeometry(' '.join(stroke),' '.join(hatch),Box(min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)),fill_weight,fill_style)
