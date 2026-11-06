"""@upsetjs/venn.js2.0.0 greedy/MDS/simplex layout and text-margin solver."""
from dataclasses import replace
import itertools,math,random
from ._circles import Circle,distance,intersections,overlap,intersection_area
from ._optimize import bisect,nelder_mead,conjugate_gradient

def distance_for_area(r1,r2,area):
    if math.pi*min(r1,r2)**2<=area+1e-10:return abs(r1-r2)
    return bisect(lambda d:overlap(r1,r2,d)-area,0,r1+r2)

def loss(circles,areas):
    result=0.
    for sets,size in areas:
        if len(sets)<2:continue
        cs=[circles[s] for s in sets]
        actual=overlap(cs[0].radius,cs[1].radius,distance(*cs)) if len(cs)==2 else intersection_area(cs)
        result+=(actual-size)**2
    return result

def missing_pairs(areas):
    ids=sorted(s[0] for s,v in areas if len(s)==1);present={tuple(sorted(s)) for s,v in areas if len(s)==2}
    return list(areas)+[(pair,0.) for pair in itertools.combinations(ids,2) if pair not in present]

def greedy(areas):
    circles={s[0]:Circle(1e10,1e10,math.sqrt(v/math.pi),s[0]) for s,v in areas if len(s)==1};sizes={s[0]:v for s,v in areas if len(s)==1};overlaps={s:[] for s in circles};pairs=[(s,v) for s,v in areas if len(s)==2]
    for (a,b),value in pairs:
        weight=0 if value+1e-10>=min(sizes[a],sizes[b]) else 1
        overlaps[a].append((b,value,weight));overlaps[b].append((a,value,weight))
    ordered=sorted(circles,key=lambda s:sum(v*w for b,v,w in overlaps[s]),reverse=True)
    if not ordered:return circles
    circles[ordered[0]].x=circles[ordered[0]].y=0.;placed={ordered[0]}
    for id in ordered[1:]:
        candidates=[];touches=sorted((p for p in overlaps[id] if p[0] in placed),key=lambda p:p[1],reverse=True);circle=circles[id]
        if not touches:raise ValueError('Missing Venn pairwise overlap information')
        for j,(other,size,weight) in enumerate(touches):
            a=circles[other];d1=distance_for_area(circle.radius,a.radius,size)
            candidates.extend(((a.x+d1,a.y),(a.x-d1,a.y),(a.x,a.y+d1),(a.x,a.y-d1)))
            for other2,size2,weight2 in touches[j+1:]:
                b=circles[other2];d2=distance_for_area(circle.radius,b.radius,size2);candidates.extend(intersections(Circle(a.x,a.y,d1),Circle(b.x,b.y,d2)))
        best=candidates[0];bestloss=1e50
        for x,y in candidates:
            circle.x=x;circle.y=y;candidate=loss(circles,pairs)
            if candidate<bestloss:bestloss=candidate;best=(x,y)
        circle.x,circle.y=best;placed.add(id)
    return circles

def constrained_mds(areas):
    sets=[(s[0],v) for s,v in areas if len(s)==1];indices={id:i for i,(id,size) in enumerate(sets)};n=len(sets);distances=[[0.]*n for _ in range(n)];constraints=[[0]*n for _ in range(n)]
    for s,area in areas:
        if len(s)!=2:continue
        i,j=(indices[id] for id in s);r1=math.sqrt(sets[i][1]/math.pi);r2=math.sqrt(sets[j][1]/math.pi);distances[i][j]=distances[j][i]=distance_for_area(r1,r2,area);constraint=1 if area+1e-10>=min(sets[i][1],sets[j][1]) else -1 if area<=1e-10 else 0;constraints[i][j]=constraints[j][i]=constraint
    norm=math.sqrt(sum(d*d for row in distances for d in row))/n if n else 0
    if not norm:return {id:Circle(0,0,math.sqrt(size/math.pi),id) for id,size in sets}
    distances=[[d/norm for d in row] for row in distances]
    def objective(x,gradient):
        gradient[:]=[0.]*len(x);result=0.
        for i in range(n):
            for j in range(i+1,n):
                dx=x[2*i]-x[2*j];dy=x[2*i+1]-x[2*j+1];squared=dx*dx+dy*dy;dist=math.sqrt(squared);d=distances[i][j];constraint=constraints[i][j]
                if constraint>0 and dist<=d or constraint<0 and dist>=d:continue
                delta=squared-d*d;result+=2*delta*delta
                gradient[2*i]+=4*delta*dx;gradient[2*i+1]+=4*delta*dy;gradient[2*j]-=4*delta*dx;gradient[2*j+1]-=4*delta*dy
        return result
    rng=random.Random();best=None
    for _ in range(10):
        solution,value=conjugate_gradient(objective,[rng.random() for _ in range(2*n)])
        if best is None or value<best[1]:best=(solution,value)
    return {id:Circle(best[0][2*i]*norm,best[0][2*i+1]*norm,math.sqrt(size/math.pi),id) for i,(id,size) in enumerate(sets)}

def optimize(areas):
    areas=missing_pairs(areas);circles=greedy(areas)
    if len(areas)>=8:
        alternative=constrained_mds(areas)
        if loss(alternative,areas)+1e-8<loss(circles,areas):circles=alternative
    ids=list(circles)
    def objective(values):return loss({id:replace(circles[id],x=values[2*i],y=values[2*i+1]) for i,id in enumerate(ids)},areas)
    solution,_=nelder_mead(objective,[v for id in ids for v in (circles[id].x,circles[id].y)],iterations=500)
    return {id:replace(circles[id],x=solution[2*i],y=solution[2*i+1]) for i,id in enumerate(ids)}

def bounds(circles):return min(c.x-c.radius for c in circles),min(c.y-c.radius for c in circles),max(c.x+c.radius for c in circles),max(c.y+c.radius for c in circles)

def orient(circles,orientation=math.pi/2):
    circles.sort(key=lambda c:c.radius,reverse=True)
    if not circles:return
    x=circles[0].x;y=circles[0].y
    for c in circles:c.x-=x;c.y-=y
    if len(circles)==2 and distance(*circles)<abs(circles[0].radius-circles[1].radius):circles[1].x=circles[0].radius-circles[1].radius-1e-10;circles[1].y=0
    if len(circles)>1:
        angle=math.atan2(circles[1].x,circles[1].y)-orientation;co=math.cos(angle);si=math.sin(angle)
        for c in circles:c.x,c.y=co*c.x-si*c.y,si*c.x+co*c.y
    if len(circles)>2 and (math.atan2(circles[2].x,circles[2].y)-orientation)%math.tau>math.pi:
        slope=circles[1].y/(1e-10+circles[1].x)
        for c in circles:d=(c.x+slope*c.y)/(1+slope*slope);c.x=2*d-c.x;c.y=2*d*slope-c.y

def normalize(solution):
    circles=[replace(c) for c in solution.values()]
    if not circles:return {}
    parents=list(range(len(circles)))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for i,a in enumerate(circles):
        for j in range(i+1,len(circles)):
            if distance(a,circles[j])+1e-10<a.radius+circles[j].radius:parents[find(j)]=find(i)
    groups={}
    for i,c in enumerate(circles):groups.setdefault(find(i),[]).append(c)
    clusters=[]
    for group in groups.values():
        orient(group);b=bounds(group);clusters.append((group,b,(b[2]-b[0])*(b[3]-b[1])))
    clusters.sort(key=lambda v:v[2],reverse=True);result=list(clusters[0][0]);box=clusters[0][1];spacing=(box[2]-box[0])/50
    for start in range(1,len(clusters),3):
        for index,right,bottom in ((start,True,False),(start+1,False,True),(start+2,True,True)):
            if index>=len(clusters):continue
            group,b,size=clusters[index];dx=box[2]-b[0]+spacing if right else box[2]-b[2]+min(0,(b[2]-b[0])/2-(box[2]-box[0])/2);dy=box[3]-b[1]+spacing if bottom else box[3]-b[3]+min(0,(b[3]-b[1])/2-(box[3]-box[1])/2)
            for circle in group:circle.x+=dx;circle.y+=dy;result.append(circle)
        box=bounds(result)
    return {c.setid:c for c in result}

def scale(solution,width,height,padding):
    if not solution:return {}
    x0,y0,x1,y1=bounds(list(solution.values()));w=width-2*padding;h=height-2*padding
    if x0==x1 or y0==y1:return solution
    factor=min(w/(x1-x0),h/(y1-y0));dx=(w-(x1-x0)*factor)/2;dy=(h-(y1-y0)*factor)/2
    return {id:Circle(padding+dx+(c.x-x0)*factor,padding+dy+(c.y-y0)*factor,c.radius*factor,id) for id,c in solution.items()}

def text_center(interior,exterior):
    def margin(point):
        x,y=point
        return min([c.radius-math.hypot(x-c.x,y-c.y) for c in interior]+[math.hypot(x-c.x,y-c.y)-c.radius for c in exterior])
    points=[(c.x+dx*c.radius,c.y+dy*c.radius) for c in interior for dx,dy in ((0,0),(.5,0),(-.5,0),(0,.5),(0,-.5))]
    best=points[0];bestmargin=margin(best)
    for point in points[1:]:
        value=margin(point)
        if value>=bestmargin:best=point;bestmargin=value
    solution,_=nelder_mead(lambda p:-margin(p),best,iterations=500,error_delta=1e-10,tolerance=1e-10)
    if all(math.hypot(solution[0]-c.x,solution[1]-c.y)<=c.radius for c in interior) and all(math.hypot(solution[0]-c.x,solution[1]-c.y)>=c.radius for c in exterior):return (*solution,False)
    if len(interior)==1:return interior[0].x,interior[0].y,False
    area,arcs=intersection_area(interior,True)
    if not arcs:return 0.,-1000.,True
    if len(arcs)==1:return arcs[0][0].x,arcs[0][0].y,False
    if exterior:return text_center(interior,[])
    return sum(a[2][0] for a in arcs)/len(arcs),sum(a[2][1] for a in arcs)/len(arcs),False

def layout(areas,width,height,padding=15):
    if any(size<0 for sets,size in areas):raise ValueError('Negative Venn set size produces a non-finite radius')
    solution=scale(normalize(optimize(areas)),width,height,padding);overlapped={id:[] for id in solution};ids=list(solution)
    for i,a in enumerate(ids):
        for b in ids[i+1:]:
            ca=solution[a];cb=solution[b];d=distance(ca,cb)
            if d+cb.radius<=ca.radius+1e-10:overlapped[b].append(a)
            elif d+ca.radius<=cb.radius+1e-10:overlapped[a].append(b)
    centers={}
    for sets,size in areas:
        exclude={id for setid in sets for id in overlapped[setid]};interior=[c for id,c in solution.items() if id in sets];exterior=[c for id,c in solution.items() if id not in sets and id not in exclude]
        centers[tuple(sets)]=text_center(interior,exterior)
    return solution,centers
