"""Swimlane Sugiyama numeric phases; fixed source pipeline, not ELK."""
from collections import defaultdict,deque
from statistics import median
import math
from ._cynefin_geometry import random as mulberry

def lane_map(nodes):
    cache={}
    def lane(ident):
        if ident in cache:return cache[ident]
        parent=nodes.get(ident,{}).get('parentId')
        cache[ident]=None
        if parent:cache[ident]=lane(parent) or parent
        return cache[ident]
    for ident in nodes:lane(ident)
    return cache

def adjacency(nodes,edges):
    pred={n:[] for n in nodes};succ={n:[] for n in nodes}
    for e in edges:pred[e['dst']].append(e['src']);succ[e['src']].append(e['dst'])
    return pred,succ

def topological(nodes,edges,generation=False):
    pred,succ=adjacency(nodes,edges);indegree={n:len(pred[n]) for n in nodes};queue=sorted(n for n in nodes if not indegree[n]);linked={x for e in edges for x in (e['src'],e['dst'])}
    unconnected=iter(n for n in nodes if not indegree[n] and n not in linked and not nodes[n].get('isGroup'))
    queue=[next(unconnected) if n not in linked and not nodes[n].get('isGroup') else n for n in queue];order=[]
    while queue:
        current=queue if generation else [queue.pop(0)]
        if generation:queue=[]
        next_generation=[]
        for u in current:
            order.append(u)
            for v in sorted(succ[u]):
                indegree[v]-=1
                if not indegree[v]:
                    if generation:next_generation.append(v)
                    else:
                        i=0
                        while i<len(queue) and queue[i]<v:i+=1
                        queue.insert(i,v)
        if generation:queue=sorted(next_generation)
    return order if len(order)==len(nodes) else None

def remove_cycles(nodes,edges):
    pred,succ=adjacency(nodes,edges);adj={n:[] for n in nodes};color=dict.fromkeys(nodes,0);reversed_ids=set()
    for index,e in enumerate(edges):adj[e['src']].append((e['dst'],e['id'],index))
    def visit(u):
        color[u]=1
        for v,_,index in sorted(adj[u]):
            if not color[v]:visit(v)
            elif color[v]==1:reversed_ids.add(index)
        color[u]=2
    for n in [n for n in nodes if not pred[n]]+[n for n in nodes if pred[n]]:
        if not color[n]:visit(n)
    return [{**e,'src':e['dst'],'dst':e['src']} if i in reversed_ids else dict(e) for i,e in enumerate(edges)]

def layers_from(nodes,order,rank,skip_groups=False):
    layers=[[] for _ in range(max((rank.get(n,0) for n in nodes if not skip_groups or not nodes[n].get('isGroup')),default=0)+1)]
    for n in order:
        if not skip_groups or not nodes[n].get('isGroup'):layers[max(0,rank.get(n,0))].append(n)
    return layers

def multitree_order(nodes,edges,rank,lanes):
    pred,_=adjacency(nodes,edges);order=topological(nodes,edges) or sorted(nodes);index={n:i for i,n in enumerate(order)};parent={};children={n:[] for n in nodes}
    for n in order:
        candidates=[p for p in sorted(pred[n]) if p in parent]
        if candidates:
            chosen=min(candidates,key=lambda p:(not(lanes[p] is not None and lanes[p]==lanes[n]),-rank.get(p,0),index[p],p));parent[n]=chosen;children[chosen].append(n)
        else:parent[n]=None
    roots=sorted((n for n in nodes if parent[n] is None),key=lambda n:(index[n],n));own={n:defaultdict(int) for n in nodes}
    def ancestors(n):
        chain=[]
        while n is not None:chain.append(n);n=parent[n]
        return chain
    for e in edges:
        a,b=e['src'],e['dst'];ra,rb=rank.get(a),rank.get(b)
        if ra is None or rb is None or ra==rb:continue
        aset=set(ancestors(a));lca=next((n for n in ancestors(b) if n in aset),None)
        if lca is not None:
            for r in range(min(ra,rb),max(ra,rb)):own[lca][r]+=1
    cross={n:{} for n in nodes};minimum={}
    def aggregate(n):
        acc=own[n].copy();minimum[n]=rank.get(n,0)
        for child in children[n]:
            values=aggregate(child);r=rank.get(n,0);cross[n][child]=values.get(r,0)+int(rank.get(child,0)>r)
            minimum[n]=min(minimum[n],minimum[child])
            for r,value in values.items():acc[r]+=value
        return acc
    for root in roots:aggregate(root)
    layers=layers_from(nodes,[],rank);emitted=set()
    def emit(n):
        if n in emitted:return
        emitted.add(n);layers[rank.get(n,0)].append(n);current=rank.get(n,0)
        future=sorted((ch for ch in children[n] if minimum[ch]>current),key=lambda ch:(minimum[ch],ch));present=sorted((ch for ch in children[n] if minimum[ch]<=current),key=lambda ch:(cross[n].get(ch,0),minimum[ch],ch))
        for child in future+present:emit(child)
    for root in sorted(roots,key=lambda n:(rank.get(n,0),n)):emit(root)
    for n in nodes:
        if n not in emitted:layers[rank.get(n,0)].append(n)
    return layers

def crossing_score(layers,edges,rank=None):
    count=0
    for upper,lower in zip(layers,layers[1:]):
        ui={n:i for i,n in enumerate(upper)};li={n:i for i,n in enumerate(lower)}
        if rank is None:
            pairs=sorted((ui[e['src']],li[e['dst']]) for e in edges if e['src'] in ui and e['dst'] in li);vs=[p[1] for p in pairs]
        else:
            # crossOptimization's source preserves incoming edge order here.
            vs=[li[e['dst']] for e in edges if e['src'] in ui and e['dst'] in li]
        count+=sum(vs[i]>vs[j] for i in range(len(vs)) for j in range(i+1,len(vs)))
    return count

def layering(nodes,edges,lanes,direction,ignore=True,optimize=True):
    order=topological(nodes,edges,generation=direction=='LR' and ignore) or sorted(nodes);pred,succ=adjacency(nodes,edges);rank={}
    if ignore:
        next_free={}
        for n in order:
            if nodes[n].get('isGroup'):continue
            lane=lanes[n] or n;base=max((rank.get(p,0)+int((lanes[p] or p)==lane) for p in pred[n]),default=0);r=max(base,next_free.get(lane,0));rank[n]=r;next_free[lane]=r+1
        return rank,layers_from(nodes,order,rank,True)
    for n in order:
        inc=pred[n]
        if len(inc)==1 and lanes[inc[0]]!=lanes[n]:rank[n]=rank.get(inc[0],0)
        else:rank[n]=max((rank.get(p,0)+1 for p in inc),default=0)
    if optimize:
        best=crossing_score(multitree_order(nodes,edges,rank,lanes),edges,rank)
        for _ in range(4):
            changed=False
            for n in sorted(nodes,key=lambda n:-rank.get(n,0)):
                old=rank.get(n,0);lower=max((rank.get(p,0)+1 for p in pred[n]),default=0)
                if old==0 or lower>=old:continue
                rank[n]=lower;score=crossing_score(multitree_order(nodes,edges,rank,lanes),edges,rank)
                if score<best:best=score;changed=True
                else:rank[n]=old
            if not changed:break
    # Source gravity relaxation enforces full edge precedence after the
    # compact initial assignment, with eight bidirectional rounds.
    for _ in range(8):
        changed=False
        for traversal in (order,list(reversed(order))):
            for n in traversal:
                ps=pred[n];ss=succ[n]
                if not ps and not ss:continue
                pa=sum(rank[p]+1 for p in ps)/len(ps) if ps else rank[n];sa=sum(rank[s]-1 for s in ss)/len(ss) if ss else rank[n];desired=math.floor((pa+sa)/2+.5)
                low=max((rank[p]+1 for p in ps),default=0);up=min((rank[s]-1 for s in ss),default=max(low,desired));value=min(max(desired,low),up)
                if value!=rank[n]:rank[n]=value;changed=True
        if not changed:break
    for n in order:rank[n]=max(rank[n],max((rank[p]+1 for p in pred[n]),default=0))
    for n in reversed(order):
        if succ[n]:rank[n]=min(rank[n],min(rank[s]-1 for s in succ[n]))
    return rank,layers_from(nodes,order,rank)

def proper(nodes,edges,rank,layers):
    nodes=dict(nodes);layers=[list(l) for l in layers];result=[];seq=0
    for e in sorted(edges,key=lambda e:(e['id'],e['src'],e['dst'])):
        ru=rank.get(e['src'],0);rv=rank.get(e['dst'],0)
        if rv-ru<=1:result.append(e);continue
        previous=e['src']
        for k,r in enumerate(range(ru+1,rv)):
            ident='placeholder-'+str(seq);seq+=1;nodes[ident]={'id':ident,'isDummy':True,'width':0,'height':0};rank[ident]=r
            while len(layers)<=r:layers.append([])
            layers[r].append(ident);result.append({**e,'id':e['id']+'#'+str(k),'src':previous,'dst':ident});previous=ident
        result.append({**e,'id':e['id']+'#'+str(max(rv-ru-1,0)),'src':previous})
    return nodes,result,layers

def optimize_lane_order(nodes,edges,lanes,source):
    if len(source)<2:return source
    index={n:i for i,n in enumerate(source)};weights={}
    for e in edges:
        a,b=lanes[e['src']],lanes[e['dst']]
        if a not in index or b not in index or a==b or e.get('isLayoutOnly'):continue
        if index[a]>index[b]:a,b=b,a
        weights[a,b]=weights.get((a,b),0)+1
    if not weights:return source
    def cost(order):
        pos={n:i for i,n in enumerate(order)};return sum(weight*abs(pos[a]-pos[b]) for (a,b),weight in weights.items())
    def candidate(start):
        order=list(start);score=cost(order)
        for _ in range(max(1,len(order))):
            changed=False
            for i in range(len(order)-1):
                order[i],order[i+1]=order[i+1],order[i];trial=cost(order)
                if trial<score:score=trial;changed=True
                else:order[i],order[i+1]=order[i+1],order[i]
            if not changed:break
        return score,sum(abs(i-index[n]) for i,n in enumerate(order)),order
    best=candidate(source);signature='|'.join(f'{a}:{b}:{weight}' for (a,b),weight in sorted(weights.items()))
    for restart in range(8):
        text='|'.join(source)+'#'+signature+'#'+str(restart);seed=2166136261
        encoded=text.encode('utf-16-le')
        for i in range(0,len(encoded),2):seed=((seed^int.from_bytes(encoded[i:i+2],'little'))*16777619)&0xffffffff
        order=list(source);state=seed
        for i in range(len(order)-1,0,-1):
            # mulberry helper accepts the pre-increment state.
            j=math.floor(mulberry(state)*(i+1));state=(state+0x6d2b79f5)&0xffffffff;order[i],order[j]=order[j],order[i]
        trial=candidate(order)
        if trial[:2]<best[:2]:best=trial
    return best[2]

def order_layers(layers,edges,lanes,lane_order):
    layers=[list(layer) for layer in layers]
    def reorder(fixed,target,down):
        positions={n:i for i,n in enumerate(fixed)};current={n:i for i,n in enumerate(target)};neighbors={n:[] for n in target}
        for e in edges:
            a,b=(e['src'],e['dst']) if down else (e['dst'],e['src'])
            if a in positions and b in neighbors:neighbors[b].append(positions[a])
        def key(n):return (median(neighbors[n]) if neighbors[n] else math.inf,current[n],n)
        if not lane_order:return sorted(target,key=key)
        groups=defaultdict(list)
        for n in target:groups[lanes[n]].append(n)
        result=[n for lane in lane_order for n in sorted(groups[lane],key=key)]
        for n in sorted(groups[None],key=key):
            bc=sum(neighbors[n])/len(neighbors[n]) if neighbors[n] else math.inf;at=len(result)
            if math.isfinite(bc):
                at=next((i for i,r in enumerate(result) if bc<(sum(neighbors[r])/len(neighbors[r]) if neighbors[r] else math.inf)),len(result))
            result.insert(at,n)
        return result
    def transpose(upper,current,next_layer):
        best=list(current)
        def score(layer):return crossing_score([upper,layer]+([next_layer] if next_layer is not None else []),edges)
        previous=score(best);changed=True
        while changed:
            changed=False
            for i in range(len(best)-1):
                if lanes[best[i]]!=lanes[best[i+1]]:continue
                best[i],best[i+1]=best[i+1],best[i];trial=score(best)
                if trial<previous:previous=trial;changed=True
                else:best[i],best[i+1]=best[i+1],best[i]
        return best
    for _ in range(3):
        for i in range(1,len(layers)):layers[i]=transpose(layers[i-1],reorder(layers[i-1],layers[i],True),layers[i+1] if i+1<len(layers) else None)
        for i in range(len(layers)-2,-1,-1):layers[i]=transpose(layers[i+1],reorder(layers[i+1],layers[i],False),layers[i-1] if i else None)
    return layers

def coordinates(nodes,edges,layers,lanes,lane_order,node_gap=40,layer_gap=100,direction='TB'):
    heights=[max((nodes[n].get('height',0) for n in layer),default=0) for layer in layers];used={lanes[n] for layer in layers for n in layer};columns=([None] if None in used else [])+[n for n in lane_order if n in used];widths=dict.fromkeys(columns,0)
    for layer in layers:
        for lane in columns:
            ids=[n for n in layer if lanes[n]==lane];widths[lane]=max(widths[lane],sum(nodes[n].get('width',0) for n in ids)+node_gap*max(0,len(ids)-1))
    total=sum(widths.values())+node_gap*2*max(0,len(columns)-1);cursor=-total/2;centers={}
    for lane in columns:centers[lane]=cursor+widths[lane]/2;cursor+=widths[lane]+node_gap*2
    positions={};y=0
    for i,layer in enumerate(layers):
        for lane in columns:
            ids=[n for n in layer if lanes[n]==lane];total=sum(nodes[n].get('width',0) for n in ids)+node_gap*max(0,len(ids)-1);cursor=centers[lane]-total/2
            for n in ids:
                width=nodes[n].get('width',0);positions[n]=(cursor+width/2,y+heights[i]/2);cursor+=width+node_gap
        extra=0
        if direction in ('LR','RL') and i+1<len(layers):
            a=max((nodes[n].get('width',0) for n in layer),default=0);b=max((nodes[n].get('width',0) for n in layers[i+1]),default=0);extra=max(0,(a+b-heights[i]-heights[i+1])/2-layer_gap)
        y+=heights[i]+layer_gap+extra
    byref=defaultdict(list)
    for e in edges:byref[e.get('ref',e['id'])].append(e)
    for chain in byref.values():
        source=chain[0].get('original_source',chain[0]['src']);target=chain[0].get('original_target',chain[-1]['dst']);mid=math.floor((positions.get(source,(0,0))[0]+positions.get(target,(0,0))[0])/2+.5)
        for e in chain:
            for n in (e['src'],e['dst']):
                if n not in (source,target) and nodes[n].get('isDummy'):positions[n]=(mid,positions[n][1])
    return positions
