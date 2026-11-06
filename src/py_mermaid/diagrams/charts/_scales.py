"""D3-array ticks, continuous/band scales, arcs and cubic chart curves.

Pure calculations, transcribed from fixed d3-array/d3-scale/d3-shape behavior;
no JS runtime or geometry selected from examples.
"""
import math

def tick_increment(start,stop,count):
    step=(stop-start)/max(0,count);power=math.floor(math.log10(step)) if step>0 else 0
    error=step/10**power;factor=10 if error>=math.sqrt(50) else 5 if error>=math.sqrt(10) else 2 if error>=math.sqrt(2) else 1
    return factor*10**power if power>=0 else -10**(-power)/factor

def ticks(start,stop,count=10):
    if count<=0 or not math.isfinite(start+stop):return ()
    if start==stop:return (start,)
    reverse=stop<start
    if reverse:start,stop=stop,start
    inc=tick_increment(start,stop,count)
    if inc>0:values=tuple(i*inc for i in range(math.ceil(start/inc),math.floor(stop/inc)+1))
    else:
        inc=-inc;values=tuple(i/inc for i in range(math.ceil(start*inc),math.floor(stop*inc)+1))
    return values[::-1] if reverse else values

def nice(start,stop,count=10):
    reverse=stop<start
    if reverse:start,stop=stop,start
    previous=None
    for _ in range(10):
        step=tick_increment(start,stop,count)
        if step==previous or not step:break
        if step>0:start=math.floor(start/step)*step;stop=math.ceil(stop/step)*step
        else:start=math.ceil(start*step)/step;stop=math.floor(stop*step)/step
        previous=step
    return (stop,start) if reverse else (start,stop)

def linear(value,domain,range_,clamp=False):
    a,b=domain;c,d=range_;t=(value-a)/(b-a) if a!=b else .5
    if clamp:t=min(1,max(0,t))
    return c+(d-c)*t

def band(domain,start,stop,padding_inner=0,padding_outer=0,align=.5):
    domain=tuple(dict.fromkeys(domain));reverse=stop<start
    if reverse:start,stop=stop,start
    n=len(domain);step=(stop-start)/max(1,n-padding_inner+2*padding_outer)
    first=start+(stop-start-step*(n-padding_inner))*align;width=step*(1-padding_inner)
    values=[first+step*i for i in range(n)]
    if reverse:values.reverse()
    return dict(zip(domain,values)),width,step

def arc(cx,cy,r,start,end,inner=0):
    """D3 arc convention: angle zero is 12 o'clock, positive clockwise."""
    tau=2*math.pi
    if r<=0 or not all(math.isfinite(x) for x in (r,start,end,inner)):return ''
    inner=max(0,min(inner,r));delta=end-start;clock=1 if delta>=0 else 0
    def point(radius,a):return cx+radius*math.sin(a),cy-radius*math.cos(a)
    if abs(delta)>=tau-1e-12:
        x,y=point(r,start);xx,yy=point(r,start+math.pi)
        d=f'M{x:g},{y:g}A{r:g},{r:g} 0 1,{clock} {xx:g},{yy:g}A{r:g},{r:g} 0 1,{clock} {x:g},{y:g}'
        if inner:
            x,y=point(inner,start);xx,yy=point(inner,start+math.pi)
            d+=f'M{x:g},{y:g}A{inner:g},{inner:g} 0 1,{1-clock} {xx:g},{yy:g}A{inner:g},{inner:g} 0 1,{1-clock} {x:g},{y:g}'
        return d+'Z'
    x,y=point(r,start);xx,yy=point(r,end);large=int(abs(delta)>math.pi)
    d=f'M{x:g},{y:g}A{r:g},{r:g} 0 {large},{clock} {xx:g},{yy:g}'
    if inner:
        x,y=point(inner,end);xx,yy=point(inner,start)
        d+=f'L{x:g},{y:g}A{inner:g},{inner:g} 0 {large},{1-clock} {xx:g},{yy:g}'
    else:d+=f'L{cx:g},{cy:g}'
    return d+'Z'

def closed_round(points,tension):
    if not points:return ''
    parts=[f'M{points[0][0]:g},{points[0][1]:g}'];n=len(points)
    for i in range(n):
        p0,p1,p2,p3=(points[j%n] for j in (i-1,i,i+1,i+2))
        a=(p1[0]+(p2[0]-p0[0])*tension,p1[1]+(p2[1]-p0[1])*tension)
        b=(p2[0]-(p3[0]-p1[0])*tension,p2[1]-(p3[1]-p1[1])*tension)
        parts.append(f'C{a[0]:g},{a[1]:g} {b[0]:g},{b[1]:g} {p2[0]:g},{p2[1]:g}')
    return ' '.join(parts)+'Z'
