"""Analytic circle areas/intersections and exact SVG intersection arcs."""
from dataclasses import dataclass
import math

SMALL=1e-10

@dataclass
class Circle:
    x:float
    y:float
    radius:float
    setid:str=''

def distance(a,b):return math.hypot(a.x-b.x,a.y-b.y)

def circle_area(radius,width):
    if not radius:return 0.
    width=max(0,min(2*radius,width))
    return radius*radius*math.acos(max(-1,min(1,1-width/radius)))-(radius-width)*math.sqrt(max(0,width*(2*radius-width)))

def overlap(r1,r2,d):
    if d>=r1+r2:return 0.
    if d<=abs(r1-r2):return math.pi*min(r1,r2)**2
    return circle_area(r1,r1-(d*d-r2*r2+r1*r1)/(2*d))+circle_area(r2,r2-(d*d-r1*r1+r2*r2)/(2*d))

def intersections(a,b):
    d=distance(a,b);r1=a.radius;r2=b.radius
    if d>=r1+r2 or d<=abs(r1-r2):return ()
    t=(r1*r1-r2*r2+d*d)/(2*d);h=math.sqrt(max(0,r1*r1-t*t));x=a.x+t*(b.x-a.x)/d;y=a.y+t*(b.y-a.y)/d;rx=-(b.y-a.y)*h/d;ry=-(b.x-a.x)*h/d
    return ((x+rx,y-ry),(x-rx,y+ry))

def intersection_area(circles,with_arcs=False):
    if not circles:return (0.,()) if with_arcs else 0.
    points=[]
    for i,a in enumerate(circles):
        for j in range(i+1,len(circles)):
            points.extend((x,y,(i,j)) for x,y in intersections(a,circles[j]))
    inner=[point for point in points if all(math.hypot(point[0]-c.x,point[1]-c.y)<c.radius+SMALL for c in circles)];arcs=[];arc_area=polygon=0.
    if len(inner)>1:
        cx=sum(p[0] for p in inner)/len(inner);cy=sum(p[1] for p in inner)/len(inner);inner.sort(key=lambda p:math.atan2(p[0]-cx,p[1]-cy),reverse=True);p2=inner[-1]
        for p1 in inner:
            polygon+=(p2[0]+p1[0])*(p1[1]-p2[1]);mid=((p1[0]+p2[0])/2,(p1[1]+p2[1])/2);best=None
            for index in p1[2]:
                if index not in p2[2]:continue
                c=circles[index];a1=math.atan2(p1[0]-c.x,p1[1]-c.y);a2=math.atan2(p2[0]-c.x,p2[1]-c.y);delta=(a2-a1)%math.tau;a=a2-delta/2
                width=min(c.radius*2,math.hypot(mid[0]-c.x-c.radius*math.sin(a),mid[1]-c.y-c.radius*math.cos(a)))
                if best is None or width<best[1]:best=(c,width,p1[:2],p2[:2])
            if best is not None:arcs.append(best);arc_area+=circle_area(best[0].radius,best[1]);p2=p1
    else:
        smallest=min(circles,key=lambda c:c.radius)
        if all(distance(c,smallest)<=abs(smallest.radius-c.radius) for c in circles):arc_area=math.pi*smallest.radius**2;arcs=[(smallest,2*smallest.radius,(smallest.x,smallest.y+smallest.radius),(smallest.x-SMALL,smallest.y+smallest.radius))]
    area=arc_area+polygon/2
    return (area,tuple(arcs)) if with_arcs else area

def area_path(circles,round_=None):
    _,arcs=intersection_area(circles,True)
    if not arcs:return 'M0,0'
    def fmt(v):
        if round_ is not None:v=math.floor(v*10**round_+.5)/10**round_
        return f'{v:g}'
    if len(arcs)==1:
        c=arcs[0][0];x=fmt(c.x);y=fmt(c.y);r=fmt(c.radius);d=fmt(c.radius*2)
        return f'M{x},{y}m-{r},0a{r},{r} 0 1,0 {d},0a{r},{r} 0 1,0 -{d},0'
    parts=['M'+fmt(arcs[0][3][0])+','+fmt(arcs[0][3][1])]
    for c,width,p1,p2 in arcs:parts.append('A'+fmt(c.radius)+','+fmt(c.radius)+' 0 '+str(int(width>c.radius))+',1 '+fmt(p1[0])+','+fmt(p1[1]))
    return ' '.join(parts)
