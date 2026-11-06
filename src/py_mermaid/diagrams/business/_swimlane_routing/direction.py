"""Canonical TB to BT/LR/RL materialization (source lrTransform.ts)."""
import math


def _parent_groups(node, by_id):
    parent=node.get('parentId')
    while parent:
        group=by_id.get(parent)
        if not group or not group.get('isGroup'):break
        yield group
        parent=group.get('parentId')


def _bounds(children):
    children=[n for n in children if isinstance(n.get('x'),(int,float)) and isinstance(n.get('y'),(int,float))]
    if not children:return None
    return dict(minX=min(n['x']-n.get('width',0)/2 for n in children),maxX=max(n['x']+n.get('width',0)/2 for n in children),minY=min(n['y']-n.get('height',0)/2 for n in children),maxY=max(n['y']+n.get('height',0)/2 for n in children))


def _recompute_nested(nodes):
    by_id={n['id']:n for n in nodes}
    groups=sorted((n for n in nodes if n.get('isGroup') and n.get('parentId')),key=lambda n:len(list(_parent_groups(n,by_id))),reverse=True)
    for group in groups:
        b=_bounds([n for n in nodes if n.get('parentId')==group['id']])
        if b:
            pad=group.get('padding',20)
            group.update(x=(b['minX']+b['maxX'])/2,y=(b['minY']+b['maxY'])/2,width=max(0,b['maxX']-b['minX'])+pad,height=max(0,b['maxY']-b['minY'])+pad)


def mirror_axis(layout,axis):
    values=[n[axis] for n in layout.get('nodes',[]) if not n.get('isGroup') and isinstance(n.get(axis),(int,float))]
    if not values or not math.isfinite(min(values)) or not math.isfinite(max(values)):return False
    total=min(values)+max(values)
    for n in layout.get('nodes',[]):
        if isinstance(n.get(axis),(int,float)):n[axis]=total-n[axis]
        r=n.get('groupTitleRect')
        if r:
            r=dict(r)
            if axis=='x':r['left'],r['right']=total-r['right'],total-r['left']
            else:r['top'],r['bottom']=total-r['bottom'],total-r['top']
            n['groupTitleRect']=r
    for e in layout.get('edges',[]):
        for p in e.get('points') or []:p[axis]=total-p[axis]
    return True


def apply_bt(layout):
    return mirror_axis(layout,'y') if any(not n.get('isGroup') for n in layout.get('nodes',[])) else True


def apply_lr(layout,direction='LR'):
    nodes=layout.get('nodes',[]);edges=layout.get('edges',[])
    content=[n for n in nodes if not n.get('isGroup')]
    if not content:return False
    min_x=min(n.get('x',0) for n in content);min_y=min(n.get('y',0) for n in content)
    if not math.isfinite(min_x) or not math.isfinite(min_y):return False
    title_band=36
    avg_w=sum(n.get('width',0) for n in content)/len(content)
    avg_h=sum(n.get('height',0) for n in content)/len(content)
    scale=max(1,avg_w/avg_h) if avg_h>0 else 1
    for n in content:n['x'],n['y']=(n.get('y',0)-min_y)*scale+title_band,n.get('x',0)-min_x
    for e in edges:
        for p in e.get('points') or []:p['x'],p['y']=(p['y']-min_y)*scale+title_band,p['x']-min_x
    _recompute_nested(nodes)
    lanes=[n for n in nodes if n.get('isGroup') and not n.get('parentId')]
    if not lanes:
        if direction=='RL':mirror_axis(layout,'x')
        return True
    by_id={n['id']:n for n in nodes};children={}
    for n in nodes:
        if n.get('isGroup'):continue
        parents=list(_parent_groups(n,by_id))
        if parents:children.setdefault(parents[-1]['id'],[]).append(n)
    max_pad=max(n.get('padding',0) for n in lanes)
    lane_bounds=[]
    for lane in lanes:
        b=_bounds(children.get(lane['id'],[]))
        if b:lane_bounds.append(dict(lane=lane,contentTop=b['minY'],contentBottom=b['maxY'],centerY=(b['minY']+b['maxY'])/2,minX=b['minX'],maxX=b['maxX']))
    if not lane_bounds:return True
    min_child=min(b['minX'] for b in lane_bounds);max_child=max(b['maxX'] for b in lane_bounds)
    body_width=max(0,max_child-min_child)+2*max(max_pad,10)
    lane_width=title_band+body_width
    lane_left=(min_child+max_child)/2-body_width/2-title_band
    center_x=lane_left+lane_width/2;vertical_margin=max(max_pad,title_band)
    lane_bounds.sort(key=lambda b:b['centerY'])
    for i,curr in enumerate(lane_bounds):
        top=curr['contentTop']-vertical_margin if i==0 else (lane_bounds[i-1]['contentBottom']+curr['contentTop'])/2
        bottom=curr['contentBottom']+vertical_margin if i==len(lane_bounds)-1 else (curr['contentBottom']+lane_bounds[i+1]['contentTop'])/2
        curr['lane'].update(x=center_x,y=(top+bottom)/2,width=lane_width,height=max(0,bottom-top),swimlaneContentTop=curr['contentTop'],groupTitleRect=dict(left=lane_left,right=lane_left+title_band,top=top,bottom=bottom))
    if direction=='RL':mirror_axis(layout,'x')
    return True
