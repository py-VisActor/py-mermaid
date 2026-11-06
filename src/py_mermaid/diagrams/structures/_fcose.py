"""Native fCoSE proof pipeline for architecture (cytoscape-fcose 2.2.0).

Owns spectral Nyström initialization, compound spring/repulsion simulation and
alignment/relative constraint projection. No ELK, COSE-Bilkent substitution,
worker host, or runtime JavaScript. All evolving state is request-local.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import random
from ...model.flowchart import Box,Point,MermaidError


class SeededRandom:
    def __init__(self,seed):self.state=int(seed)&0xffffffff;self.unseeded=seed==0
    def __call__(self):
        if self.unseeded:return random.SystemRandom().random()
        self.state=(self.state+0x6d2b79f5)&0xffffffff;t=self.state;t=((t^(t>>15))*(t|1))&0xffffffff;t^=(t+((t^(t>>7))*(t|61)&0xffffffff))&0xffffffff
        return ((t^(t>>14))&0xffffffff)/4294967296


def _eigen_symmetric(matrix):
    """Jacobi diagonalization of the source's symmetric distance submatrix."""
    n=len(matrix);a=[list(row) for row in matrix];v=[[float(i==j) for j in range(n)] for i in range(n)]
    for iteration in range(max(1,100*n*n)):
        candidates=((abs(a[i][j]),i,j) for i in range(n) for j in range(i+1,n));value,p,q=max(candidates,default=(0,0,0))
        if value<1e-10:break
        phi=.5*math.atan2(2*a[p][q],a[q][q]-a[p][p]);c=math.cos(phi);s=math.sin(phi);pp=a[p][p];qq=a[q][q];pq=a[p][q]
        for k in range(n):
            if k not in (p,q):ap=a[k][p];aq=a[k][q];a[k][p]=a[p][k]=c*ap-s*aq;a[k][q]=a[q][k]=s*ap+c*aq
            vp=v[k][p];vq=v[k][q];v[k][p]=c*vp-s*vq;v[k][q]=s*vp+c*vq
        a[p][p]=c*c*pp-2*s*c*pq+s*s*qq;a[q][q]=s*s*pp+2*s*c*pq+c*c*qq;a[p][q]=a[q][p]=0.
    return [a[i][i] for i in range(n)],v


def _spectral(ids,adj,separation,rng):
    n=len(ids)
    if n<=2:return {id:(i*separation,0.) for i,id in enumerate(ids)}
    sample_count=min(n,25);index={id:i for i,id in enumerate(ids)};distances=[];samples=[];minimum=[1e8]*n;sample=int(rng()*n)
    for count in range(sample_count):
        samples.append(sample);dist=[1e8]*n;dist[sample]=0.;queue=[sample]
        for current in queue:
            for other in adj[ids[current]]:
                at=index[other]
                if dist[at]==1e8:dist[at]=dist[current]+1;queue.append(at)
        col=[d*separation for d in dist];distances.append(col)
        for i,d in enumerate(dist):minimum[i]=min(minimum[i],d)
        sample=max(range(n),key=lambda i:minimum[i])
    c=[[distances[j][i]**2 for j in range(sample_count)] for i in range(n)];phi=[[c[samples[j]][i] for j in range(sample_count)] for i in range(sample_count)];eigen,v=_eigen_symmetric(phi);max_s=max(abs(e) for e in eigen)**3
    # Symmetric SVD inverse: sign(lambda) * s/(s² + s_max³/s²).
    inv_weights=[e/(e*e+max_s/(e*e)) if abs(e)>1e-12 else 0. for e in eigen];inv=[[sum(v[i][k]*inv_weights[k]*v[j][k] for k in range(sample_count)) for j in range(sample_count)] for i in range(sample_count)]
    def center(values):mean=sum(values)/len(values);return [x-mean for x in values]
    def normalize(values):norm=math.sqrt(sum(x*x for x in values));return [x/norm for x in values] if norm else values
    def mult(values):
        values=center(values);temp=[sum(-.5*c[i][j]*values[i] for i in range(n)) for j in range(sample_count)];temp=[sum(inv[i][j]*temp[j] for j in range(sample_count)) for i in range(sample_count)];return center([sum(c[i][j]*temp[j] for j in range(sample_count)) for i in range(n)])
    vectors=[];coordinates=[]
    for axis in range(2):
        y=normalize([rng() for i in range(n)]);previous=1e-9;theta=0.
        for iteration in range(10000):
            old=y
            if vectors:
                dot=sum(a*b for a,b in zip(vectors[0],old));old=[a-dot*b for a,b in zip(old,vectors[0])]
            projected=mult(old);theta=sum(a*b for a,b in zip(old,projected));y=normalize(projected);current=sum(a*b for a,b in zip(old,y));ratio=abs(current/previous) if previous else math.inf
            if 1<=ratio<=1+1e-7:break
            previous=current
        else:raise MermaidError('fCoSE spectral power iteration did not converge',code='LAYOUT_CONVERGENCE')
        vectors.append(y);coordinates.append([a*math.sqrt(abs(theta)) for a in y])
    return {id:(coordinates[0][i],coordinates[1][i]) for i,id in enumerate(ids)}


@dataclass
class _Node:
    id:str
    parent:str|None
    width:float
    height:float
    x:float=0.
    y:float=0.
    descendants:tuple=()
    count:int=1


def _clip(node,other):
    dx=other.x-node.x;dy=other.y-node.y;t=min(node.width/2/abs(dx) if dx else math.inf,node.height/2/abs(dy) if dy else math.inf)
    return (node.x+dx*t,node.y+dy*t) if math.isfinite(t) else (node.x,node.y)


def _separation(a,b,buffer):
    # IGeometry.calcSeparationAmount, including contained rectangles.
    dx=b.x-a.x;dy=b.y-a.y;ox=min(a.x+a.width/2,b.x+b.width/2)-max(a.x-a.width/2,b.x-b.width/2);oy=min(a.y+a.height/2,b.y+b.height/2)-max(a.y-a.height/2,b.y-b.height/2)
    ax=a.x-a.width/2;bx=b.x-b.width/2;ay=a.y-a.height/2;by=b.y-b.height/2
    if ax<=bx and ax+a.width>=bx+b.width:ox+=min(bx-ax,ax+a.width-bx-b.width)
    elif bx<=ax and bx+b.width>=ax+a.width:ox+=min(ax-bx,bx+b.width-ax-a.width)
    if ay<=by and ay+a.height>=by+b.height:oy+=min(by-ay,ay+a.height-by-b.height)
    elif by<=ay and by+b.height>=ay+a.height:oy+=min(ay-by,by+b.height-ay-a.height)
    slope=abs(dy/dx) if dx else math.inf
    if not dx and not dy:slope=1.
    sx=oy/slope if slope else math.inf;sy=ox*slope
    if ox<sx:sx=ox
    else:sy=oy
    return math.copysign(sx/2+buffer,dx or 1),math.copysign(sy/2+buffer,dy or 1)


class _Constraints:
    def __init__(self,ids,horizontal,vertical,relative):
        self.ids=tuple(ids);self.axes=[]
        for axis,alignments in ((0,vertical),(1,horizontal)):
            parent={id:id for id in ids}
            def find(id):
                while parent[id]!=id:parent[id]=parent[parent[id]];id=parent[id]
                return id
            for group in alignments:
                for id in group[1:]:parent[find(id)]=find(group[0])
            components={}
            for id in ids:components.setdefault(find(id),[]).append(id)
            edges={id:{} for id in components};indegree={id:0 for id in components}
            for rel in relative:
                if rel[0]!=axis:continue
                a,b,gap=rel[1:];a=find(a);b=find(b)
                if a==b and gap>0:raise MermaidError('Contradictory architecture alignment and relative placement',code='UNSATISFIABLE_LAYOUT')
                if b not in edges[a]:indegree[b]+=1
                edges[a][b]=max(edges[a].get(b,0),gap)
            queue=[id for id in components if indegree[id]==0];order=[]
            for id in queue:
                order.append(id)
                for other in edges[id]:
                    indegree[other]-=1
                    if indegree[other]==0:queue.append(other)
            if len(order)!=len(components):raise MermaidError('Architecture relative-placement constraints contain a cycle',code='UNSATISFIABLE_LAYOUT')
            self.axes.append((axis,components,edges,order))
    def apply(self,nodes):
        for axis,components,edges,order in self.axes:
            values={key:sum((nodes[id].x if axis==0 else nodes[id].y) for id in group)/len(group) for key,group in components.items()};mean=sum(values[k]*len(components[k]) for k in components)/len(self.ids) if self.ids else 0
            # Source DAG longest-path enforcement followed by centroid relocation.
            for a in order:
                for b,gap in edges[a].items():values[b]=max(values[b],values[a]+gap)
            shift=(sum(values[k]*len(components[k]) for k in components)/len(self.ids)-mean) if self.ids else 0
            for k,group in components.items():
                for id in group:
                    if axis==0:nodes[id].x=values[k]-shift
                    else:nodes[id].y=values[k]-shift


def simulate(node_data,group_data,edge_data,*,horizontal=(),vertical=(),relative=(),config=None):
    config=config or {};rng=SeededRandom(config.get('seed',1));nodes={n['id']:_Node(n['id'],n.get('parent'),n['width'],n['height']) for n in node_data};groups={g['id']:_Node(g['id'],g.get('parent'),30.,30.) for g in group_data};all_nodes={**groups,**nodes};children={}
    for n in all_nodes.values():children.setdefault(n.parent,[]).append(n.id)
    def descend(id,path=()):
        if id in path:raise MermaidError('Cyclic architecture groups',code='INVALID_PARENT')
        return tuple(child for c in children.get(id,()) for child in (descend(c,(*path,id)) if c in groups and children.get(c) else (c,)))
    for group in groups.values():group.descendants=descend(group.id);group.count=max(1,len(group.descendants))
    # Empty compound groups are source childless nodes in the force graph.
    leaves={**nodes,**{id:g for id,g in groups.items() if not g.descendants}};ids=tuple(leaves);adj={id:[] for id in ids}
    for edge in edge_data:
        a,b=edge['source'],edge['target']
        if a!=b and a in adj and b in adj:adj[a].append(b);adj[b].append(a)
    def connect_components(members):
        remaining=set(members);components=[]
        while remaining:
            root=next(id for id in members if id in remaining);remaining.remove(root);queue=[root]
            for id in queue:
                for other in adj[id]:
                    if other in remaining:remaining.remove(other);queue.append(other)
            components.append(queue)
        if len(components)>1:
            dummy='__fcose_dummy_'+str(len(adj));adj[dummy]=[]
            for component in components:representative=next((id for id in component if len(adj[id])==min(len(adj[i]) for i in component)),component[0]);adj[dummy].append(representative);adj[representative].append(dummy)
    if config.get('randomize'):
        connect_components(ids)
        for group in groups.values():
            if group.descendants:connect_components(group.descendants)
        initial=_spectral(tuple(adj),adj,float(config.get('nodeSeparation',75)),rng)
    else:
        # Cytoscape initial grid was created before elements were added; each
        # inserted node begins at its zero insertion position, not a new grid.
        initial={id:(0.,0.) for id in ids}
    for id,node in leaves.items():node.x,node.y=initial[id]
    constraints=_Constraints(ids,horizontal,vertical,relative);constraints.apply(leaves)
    padding=float(config.get('padding',40));icon=float(config.get('iconSize',80));ideal=float(config.get('idealEdgeLengthMultiplier',1.5))*icon;elastic=float(config.get('edgeElasticity',.45));links=[];seen=set()
    for edge in edge_data:
        a,b=edge['source'],edge['target'];key=tuple(sorted((a,b)))
        if a==b or key in seen:continue
        seen.add(key);same=all_nodes[a].parent==all_nodes[b].parent;links.append((a,b,ideal if same else .5*icon,elastic if same else .001))
    average=sum(e[2] for e in links)/len(links) if links else 50.;min_repulsion=average/10
    def bounds():
        for group in reversed(tuple(groups.values())):
            direct=[all_nodes[id] for id in children.get(group.id,())]
            if not direct:continue
            left=min(n.x-n.width/2 for n in direct)-padding;right=max(n.x+n.width/2 for n in direct)+padding;top=min(n.y-n.height/2 for n in direct)-padding;bottom=max(n.y+n.height/2 for n in direct)+padding;group.x=(left+right)/2;group.y=(top+bottom)/2;group.width=right-left;group.height=bottom-top
    bounds();max_iter=max(5*len(all_nodes),int(config.get('numIter',2500)));cool=.3;old_displacement=math.inf;cool_cycle=0;last_displacement=math.inf;constraints_exist=any((horizontal,vertical,relative));near=[]
    for iteration in range(1,max_iter+1):
        bounds();force={id:[0.,0.] for id in all_nodes}
        for a,b,length,strength in links:
            na,nb=all_nodes[a],all_nodes[b]
            if abs(nb.x-na.x)<(na.width+nb.width)/2 and abs(nb.y-na.y)<(na.height+nb.height)/2:continue
            ax,ay=_clip(na,nb);bx,by=_clip(nb,na);dx,dy=bx-ax,by-ay;distance=math.hypot(dx,dy)
            if not distance:continue
            scalar=strength*(distance-length)/distance;fx,fy=scalar*dx,scalar*dy;force[a][0]+=fx;force[a][1]+=fy;force[b][0]-=fx;force[b][1]-=fy
        if iteration%10==1:
            near=[]
            for siblings in children.values():
                for i,a in enumerate(siblings):
                    for b in siblings[i+1:]:
                        na,nb=all_nodes[a],all_nodes[b]
                        if abs(na.x-nb.x)-(na.width+nb.width)/2<=2*average and abs(na.y-nb.y)-(na.height+nb.height)/2<=2*average:near.append((a,b))
        for a,b in near:
            na,nb=all_nodes[a],all_nodes[b]
            if abs(nb.x-na.x)<(na.width+nb.width)/2 and abs(nb.y-na.y)<(na.height+nb.height)/2:
                fx,fy=_separation(na,nb,average/2);weight=2*na.count*nb.count/(na.count+nb.count);fx*=weight;fy*=weight
            else:
                ax,ay=_clip(na,nb);bx,by=_clip(nb,na);dx,dy=bx-ax,by-ay;dx=math.copysign(max(abs(dx),min_repulsion),dx) if dx else 0.;dy=math.copysign(max(abs(dy),min_repulsion),dy) if dy else 0.;dist2=dx*dx+dy*dy
                if not dist2:continue
                factor=4500*na.count*nb.count/(dist2*math.sqrt(dist2));fx=dx*factor;fy=dy*factor
            force[a][0]-=fx;force[a][1]-=fy;force[b][0]+=fx;force[b][1]+=fy
        # Disconnected owner graphs receive the source weak gravity; connected
        # components are governed by their springs and explicit constraints.
        for parent,siblings in children.items():
            if len(siblings)<2:continue
            cx=sum(all_nodes[id].x for id in siblings)/len(siblings);cy=sum(all_nodes[id].y for id in siblings)/len(siblings);estimated=sum((all_nodes[id].width+all_nodes[id].height)/2 for id in siblings)/math.sqrt(len(siblings));gravity_range=estimated*(3.8 if parent is None else 1.5)
            for id in siblings:
                n=all_nodes[id];dx=n.x-cx;dy=n.y-cy
                if abs(dx)+n.width/2>gravity_range or abs(dy)+n.height/2>gravity_range:force[id][0]-=.25*dx;force[id][1]-=.25*dy
        displacement={id:[0.,0.] for id in leaves}
        for id,n in all_nodes.items():
            dx=max(-100*cool,min(100*cool,cool*force[id][0]/n.count));dy=max(-100*cool,min(100*cool,cool*force[id][1]/n.count))
            for leaf in n.descendants if n.descendants else (id,):
                if leaf in displacement:displacement[leaf][0]+=dx;displacement[leaf][1]+=dy
        previous={id:(n.x,n.y) for id,n in leaves.items()}
        for id,n in leaves.items():n.x+=displacement[id][0];n.y+=displacement[id][1]
        constraints.apply(leaves);last_displacement=sum(abs(n.x-previous[id][0])+abs(n.y-previous[id][1]) for id,n in leaves.items())
        if iteration%100==0:
            if last_displacement<1.5*len(all_nodes) or (iteration>max_iter/3 and abs(last_displacement-old_displacement)<2):break
            old_displacement=last_displacement;cool_cycle+=1;max_cycle=max_iter/100;exponent=math.log(100*(.3-.04))/math.log(max_cycle) if max_cycle>1 else 1;cool=max(.3-cool_cycle**exponent/100,.04)
    bounds()
    # Without constraints, CoSE tiles isolated childless siblings. Preserve
    # intrinsic dimensions and source ten-pixel tiling gaps.
    if not constraints_exist:
        for parent,siblings in children.items():
            isolated=[id for id in siblings if id in leaves and not adj[id]]
            if len(isolated)>1:
                cols=max(1,math.ceil(math.sqrt(len(isolated))));cw=max(leaves[id].width for id in isolated)+10;ch=max(leaves[id].height for id in isolated)+10
                for i,id in enumerate(isolated):leaves[id].x=(i%cols)*cw;leaves[id].y=(i//cols)*ch
        bounds()
    if not all(math.isfinite(v) for n in all_nodes.values() for v in (n.x,n.y,n.width,n.height)):raise MermaidError('Non-finite architecture fCoSE geometry',code='INVALID_LAYOUT')
    return {id:Box(n.x-n.width/2,n.y-n.height/2,n.width,n.height) for id,n in nodes.items()},{id:Box(n.x-n.width/2,n.y-n.height/2,n.width,n.height) for id,n in groups.items()}
