"""d3-sankey0.12.3 link breadth/depth/layer relaxation, six iterations.

Source copyright Mike Bostock, BSD-3-Clause; this is a pure Python numerical
port, not a runtime adapter or a replacement graph-layout algorithm.
"""
from dataclasses import dataclass,field
import math

@dataclass(eq=False)
class Node:
    id:str
    index:int
    source_links:list=field(default_factory=list)
    target_links:list=field(default_factory=list)
    value:float=0
    depth:int=0
    height:int=0
    layer:int=0
    x0:float=0
    x1:float=0
    y0:float=0
    y1:float=0

@dataclass(eq=False)
class Link:
    source:Node
    target:Node
    value:float
    index:int
    width:float=0
    y0:float=0
    y1:float=0

def sankey(node_ids,link_data,width,height,node_width=10,padding=12,alignment='justify',iterations=6):
    nodes=[Node(id,i) for i,id in enumerate(node_ids)];lookup={n.id:n for n in nodes};links=[]
    for i,(source,target,value) in enumerate(link_data):
        if source not in lookup or target not in lookup:raise ValueError('missing: '+(source if source not in lookup else target))
        link=Link(lookup[source],lookup[target],value,i);links.append(link);link.source.source_links.append(link);link.target.target_links.append(link)
    for n in nodes:n.value=max(sum(l.value for l in n.source_links if math.isfinite(l.value)),sum(l.value for l in n.target_links if math.isfinite(l.value)))
    for attr,edge_attr,neighbor in (('depth','source_links','target'),('height','target_links','source')):
        current=nodes[:];level=0
        while current:
            next_={}
            for n in current:
                setattr(n,attr,level)
                for link in getattr(n,edge_attr):next_[getattr(link,neighbor)]=None
            level+=1
            if level>len(nodes):raise ValueError('circular link')
            current=list(next_)
    if not nodes:raise ValueError('Sankey requires nodes')
    count=max(n.depth for n in nodes)+1
    if count<2:raise ValueError('Sankey does not have a finite multi-column extent')
    columns=[[] for _ in range(count)];kx=(width-node_width)/(count-1)
    for n in nodes:
        if alignment=='left':layer=n.depth
        elif alignment=='right':layer=count-1-n.height
        elif alignment=='justify':layer=n.depth if n.source_links else count-1
        elif alignment=='center':layer=n.depth if n.target_links else min((l.target.depth for l in n.source_links),default=1)-1 if n.source_links else 0
        else:raise ValueError('Unknown Sankey node alignment')
        n.layer=max(0,min(count-1,math.floor(layer)));n.x0=n.layer*kx;n.x1=n.x0+node_width;columns[n.layer].append(n)
    # Every layer is populated for a DAG's longest path.
    py=min(padding,height/(max(len(c) for c in columns)-1)) if max(len(c) for c in columns)>1 else padding
    scales=[(height-(len(c)-1)*py)/sum(n.value for n in c) for c in columns if c and sum(n.value for n in c)!=0]
    if not scales:raise ValueError('Sankey has no finite nonzero flow scale')
    ky=min(scales)
    def sort_links(n):
        n.source_links.sort(key=lambda l:(l.target.y0,l.index));n.target_links.sort(key=lambda l:(l.source.y0,l.index))
    def reorder(n):
        for link in n.target_links:link.source.source_links.sort(key=lambda l:(l.target.y0,l.index))
        for link in n.source_links:link.target.target_links.sort(key=lambda l:(l.source.y0,l.index))
    for column in columns:
        y=0
        for n in column:
            n.y0=y;n.y1=y+n.value*ky;y=n.y1+py
            for link in n.source_links:link.width=link.value*ky
        y=(height-y+py)/(len(column)+1)
        for i,n in enumerate(column):n.y0+=y*(i+1);n.y1+=y*(i+1)
        for n in column:sort_links(n)
    def top_to_bottom(column,y,index,alpha):
        for n in column[index:]:
            dy=(y-n.y0)*alpha
            if dy>1e-6:n.y0+=dy;n.y1+=dy
            y=n.y1+py
    def bottom_to_top(column,y,index,alpha):
        for n in column[:index+1][::-1]:
            dy=(n.y1-y)*alpha
            if dy>1e-6:n.y0-=dy;n.y1-=dy
            y=n.y0-py
    def collisions(column,alpha):
        if not column:return
        mid=len(column)//2;subject=column[mid]
        bottom_to_top(column,subject.y0-py,mid-1,alpha);top_to_bottom(column,subject.y1+py,mid+1,alpha)
        bottom_to_top(column,height,len(column)-1,alpha);top_to_bottom(column,0,0,alpha)
    def target_top(source,target):
        y=source.y0-(len(source.source_links)-1)*py/2
        for link in source.source_links:
            if link.target is target:break
            y+=link.width+py
        for link in target.target_links:
            if link.source is source:break
            y-=link.width
        return y
    def source_top(source,target):
        y=target.y0-(len(target.target_links)-1)*py/2
        for link in target.target_links:
            if link.source is source:break
            y+=link.width+py
        for link in source.source_links:
            if link.target is target:break
            y-=link.width
        return y
    for i in range(iterations):
        alpha=.99**i;beta=max(1-alpha,(i+1)/iterations)
        for column in columns[-2::-1]:
            for source in column:
                values=[(link,link.value*(link.target.layer-source.layer)) for link in source.source_links];weight=sum(v for link,v in values)
                if weight>0:
                    dy=(sum(source_top(source,link.target)*v for link,v in values)/weight-source.y0)*alpha;source.y0+=dy;source.y1+=dy;reorder(source)
            column.sort(key=lambda n:n.y0);collisions(column,beta)
        for column in columns[1:]:
            for target in column:
                values=[(link,link.value*(target.layer-link.source.layer)) for link in target.target_links];weight=sum(v for link,v in values)
                if weight>0:
                    dy=(sum(target_top(link.source,target)*v for link,v in values)/weight-target.y0)*alpha;target.y0+=dy;target.y1+=dy;reorder(target)
            column.sort(key=lambda n:n.y0);collisions(column,beta)
    for n in nodes:
        y0=n.y0;y1=n.y0
        for link in n.source_links:link.y0=y0+link.width/2;y0+=link.width
        for link in n.target_links:link.y1=y1+link.width/2;y1+=link.width
    if not all(math.isfinite(v) for n in nodes for v in (n.x0,n.x1,n.y0,n.y1)) or not all(math.isfinite(v) for l in links for v in (l.width,l.y0,l.y1)):raise ValueError('Non-finite Sankey geometry')
    return nodes,links
