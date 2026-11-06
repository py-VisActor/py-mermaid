"""Non-layered tidy tree 2.0.2 and Mermaid's dual-horizontal-tree adapter.

Numeric port of algorithm.js/helpers.js, MIT. Browser/webpack hosts are absent.
"""
from dataclasses import dataclass
import math


class Tree:
    def __init__(self,id,w,h,y,children):
        self.id=id;self.w=w;self.h=h;self.y=y;self.c=children;self.cs=len(children);self.x=0.;self.prelim=0.;self.mod=0.;self.shift=0.;self.change=0.;self.tl=None;self.tr=None;self.el=None;self.er=None;self.msel=0.;self.mser=0.


@dataclass
class IYL:
    low_y:float
    index:int
    next:object=None


def _bottom(t):return t.y+t.h
def _left(t):return t.tl if not t.cs else t.c[0]
def _right(t):return t.tr if not t.cs else t.c[-1]


def _extremes(t):
    if not t.cs:t.el=t.er=t;t.msel=t.mser=0.
    else:t.el=t.c[0].el;t.msel=t.c[0].msel;t.er=t.c[-1].er;t.mser=t.c[-1].mser


def _iyl(y,index,head):
    while head is not None and y>=head.low_y:head=head.next
    return IYL(y,index,head)


def _move(t,i,si,distance):
    child=t.c[i];child.mod+=distance;child.msel+=distance;child.mser+=distance
    if si!=i-1:
        count=i-si;t.c[si+1].shift+=distance/count;t.c[i].shift-=distance/count;t.c[i].change-=distance-distance/count


def _left_thread(t,i,cl,modsum):
    li=t.c[0].el;li.tl=cl;diff=(modsum-cl.mod)-t.c[0].msel;li.mod+=diff;li.prelim-=diff;t.c[0].el=t.c[i].el;t.c[0].msel=t.c[i].msel


def _right_thread(t,i,sr,modsum):
    ri=t.c[i].er;ri.tr=sr;diff=(modsum-sr.mod)-t.c[i].mser;ri.mod+=diff;ri.prelim-=diff;t.c[i].er=t.c[i-1].er;t.c[i].mser=t.c[i-1].mser


def _separate(t,i,head):
    sr=t.c[i-1];mssr=sr.mod;cl=t.c[i];mscl=cl.mod
    while sr is not None and cl is not None:
        if _bottom(sr)>head.low_y:head=head.next
        distance=mssr+sr.prelim+sr.w-(mscl+cl.prelim)
        if distance>0:mscl+=distance;_move(t,i,head.index,distance)
        sy=_bottom(sr);cy=_bottom(cl)
        if sy<=cy:
            sr=_right(sr)
            if sr is not None:mssr+=sr.mod
        if sy>=cy:
            cl=_left(cl)
            if cl is not None:mscl+=cl.mod
    if sr is None and cl is not None:_left_thread(t,i,cl,mscl)
    elif sr is not None and cl is None:_right_thread(t,i,sr,mssr)


def _first(t):
    if not t.cs:_extremes(t);return
    _first(t.c[0]);head=_iyl(_bottom(t.c[0].el),0,None)
    for i in range(1,t.cs):
        _first(t.c[i]);low=_bottom(t.c[i].er);_separate(t,i,head);head=_iyl(low,i,head)
    t.prelim=(t.c[0].prelim+t.c[0].mod+t.c[-1].mod+t.c[-1].prelim+t.c[-1].w)/2-t.w/2;_extremes(t)


def _second(t,modsum):
    modsum+=t.mod;t.x=t.prelim+modsum;d=0.;delta=0.
    for child in t.c:d+=child.shift;delta+=d+child.change;child.mod+=delta
    for child in t.c:_second(child,modsum)


def _convert(id,lookup,children,y=0,path=()):
    from ...model.flowchart import MermaidError
    if id in path:raise MermaidError('Cyclic tidy-tree input',code='INVALID_LAYOUT_DATA')
    node=lookup[id];w=node['height']+20;h=node['width']+40
    return Tree(id,w,h,y,[_convert(child,lookup,children,y+h,(*path,id)) for child in children.get(id,())])


def _tree(roots,lookup,children):
    # A transposed one-by-one virtual root participates in both walks.
    t=Tree(None,21.,41.,0.,[_convert(id,lookup,children,41.) for id in roots]);_first(t);_second(t,0.);return t


def _rectangle_intersection(node,outside,inside):
    x,y,w,h=node['x'],node['y'],node['width']/2,node['height']/2;ox,oy=outside;ix,iy=inside;dx=abs(x-ix);r=w-dx if ix<ox else w+dx;q=abs(oy-iy);rr=abs(ox-ix)
    if abs(y-oy)*w>abs(x-ox)*h:
        cut=oy-h-y if iy<oy else y-h-oy;r=rr*cut/q if q else 0.;rx=ix+r if ix<ox else ix-rr+r;ry=iy+q-cut if iy<oy else iy-q+cut
        if r==0:rx,ry=ox,oy
        if rr==0:rx=ox
        if q==0:ry=oy
        return rx,ry
    r=ox-w-x if ix<ox else x-w-ox;cut=q*r/rr if rr else 0.;rx=ix+rr-r if ix<ox else ix-rr+r;ry=iy+cut if iy<oy else iy-cut
    if r==0:rx,ry=ox,oy
    if rr==0:rx=ox
    if q==0:ry=oy
    return rx,ry


def _intersect(node,outside,inside):
    if node.get('shape') in ('circle','cloud','bang'):
        dx=inside[0]-outside[0];dy=inside[1]-outside[1];length=math.hypot(dx,dy)
        if not length:return outside
        radius=min(node['width'],node['height'])/2;return node['x']-dx/length*radius,node['y']-dy/length*radius
    return _rectangle_intersection(node,outside,inside)


async def layout(nodes,edges,*,direction='TB',parents=(),options=None,node_spacing=50,rank_spacing=50,config=None,algorithm=None):
    from ...runtime.graph import GraphLayout,FrozenLookup
    from ...model.flowchart import Box,Point,MermaidError
    lookup={n['id']:dict(n) for n in nodes};edges=tuple(edges);children={};parent={}
    if not lookup:raise MermaidError('No nodes found in tidy-tree input',code='INVALID_LAYOUT_DATA')
    if parents:raise MermaidError('Tidy-tree source adapter does not consume compound graph groups',code='INVALID_LAYOUT_DATA')
    for edge in edges:
        a,b=edge['source'],edge['target']
        if a not in lookup or b not in lookup:raise MermaidError('Unknown tidy-tree endpoint',code='UNKNOWN_REFERENCE')
        children.setdefault(a,[]).append(b);parent[b]=a
    root=next((id for id in lookup if id not in parent),next(iter(lookup)));root_node=lookup[root];root_children=children.get(root,());positions={root:{**root_node,'x':0.,'y':20.,'section':'root'}};spacing=root_node['width']/2+30
    for section,roots,sign in (('left',root_children[::2],-1),('right',root_children[1::2],1)):
        if not roots:continue
        tree=_tree(roots,lookup,children);side=[]
        def position(t):
            node=lookup[t.id];side.append({**node,'x':sign*(spacing+t.y),'y':t.x+10,'section':section})
            for child in t.c:position(child)
        for child in tree.c:position(child)
        first_x=max(n['x'] for n in side) if sign<0 else min(n['x'] for n in side);first=[n for n in side if n['x']==first_x];center=(min(n['y']-n['height']/2 for n in first)+max(n['y']+n['height']/2 for n in first))/2
        for n in side:n['x']+=sign*n['width']/2;n['y']+=-center+n['height']/2;positions[n['id']]=n
    # The source leaves nodes outside the root component at their insertion
    # origin. Retain them as real nodes instead of dropping their content.
    for id,node in lookup.items():positions.setdefault(id,{**node,'x':0.,'y':0.,'section':None})
    left=min(n['x']-n['width']/2 for n in positions.values());top=min(n['y']-n['height']/2 for n in positions.values());boxes=tuple((id,Box(n['x']-n['width']/2-left,n['y']-n['height']/2-top,n['width'],n['height'])) for id,n in positions.items());routes=[]
    for edge in edges:
        a=positions[edge['source']];b=positions[edge['target']];ac=(a['x'],a['y']);bc=(b['x'],b['y']);points=[_intersect(a,ac,bc)]
        side=a['section'] if a['section'] in ('left','right') else b['section']
        if side in ('left','right'):points.append((a['x']+(-1 if side=='left' else 1)*(a['width']/2+30),a['y']))
        side=b['section'] if b['section'] in ('left','right') else a['section']
        if side in ('left','right'):points.append((b['x']+(1 if side=='left' else -1)*(b['width']/2+30),b['y']))
        points.append(_intersect(b,bc,ac));points[0]=_intersect(a,points[1],ac);points[-1]=_intersect(b,points[-2],bc);routes.append((edge['id'],tuple(Point(x-left,y-top) for x,y in points)))
    return GraphLayout(FrozenLookup(boxes),FrozenLookup(tuple(routes)),FrozenLookup(()),FrozenLookup(()),max(b.x+b.width for _,b in boxes),max(b.y+b.height for _,b in boxes),'native-tidy-tree','2.0.2')
