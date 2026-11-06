"""Pure port of cynefinBoundaries.ts (fixed Mermaid 12.2.0)."""
def random(seed):
    t=int(seed+0x6d2b79f5)&0xffffffff
    t=((t^(t>>15))*(t|1))&0xffffffff
    t^=(t+(((t^(t>>7))*(t|61))&0xffffffff))&0xffffffff
    return ((t^(t>>14))&0xffffffff)/4294967296

def hash_string(text):
    h=0
    data=text.encode('utf-16-le')
    for i in range(0,len(data),2):h=(31*h+int.from_bytes(data[i:i+2],'little'))&0xffffffff
    return h if h<0x80000000 else h-0x100000000

def boundary(w,h,seed,amplitude=None,horizontal=False):
    a=(h if horizontal else w)*.015 if amplitude is None else amplitude
    points=[]
    for i in range(8):
        jitter=random(seed+i*(23 if horizontal else 17))*a*2-a
        points.append((i*w/7,h/2+jitter) if horizontal else (w/2+jitter,i*h/7))
    d=f'M{points[0][0]},{points[0][1]}'
    for i,(p,q) in enumerate(zip(points,points[1:])):
        offset=a*1.5*(1 if i%2==0 else -1)*random(seed+i*(37 if horizontal else 31)+(11 if horizontal else 7))
        if horizontal:
            m=(p[0]+q[0])/2;c=(m,p[1]+offset,m,q[1]-offset)
        else:
            m=(p[1]+q[1])/2;c=(p[0]+offset,m,q[0]-offset,m)
        d+=f' C{c[0]},{c[1]} {c[2]},{c[3]} {q[0]},{q[1]}'
    return d

def cliff(w,h):
    x=w/2;y=h/2;a=w*.03;dy=h/2
    return f'M{x},{y} C{x+a},{y+dy*.2} {x-a*1.5},{y+dy*.55} {x+a*.5},{y+dy*.75} C{x-a},{y+dy*.85} {x+a*.3},{y+dy*.95} {x},{h}'

def confusion(w,h):
    x=w/2;y=h/2;rx=w*.15;ry=h*.15
    return f'M{x-rx},{y} A{rx},{ry} 0 1,1 {x+rx},{y} A{rx},{ry} 0 1,1 {x-rx},{y} Z'
