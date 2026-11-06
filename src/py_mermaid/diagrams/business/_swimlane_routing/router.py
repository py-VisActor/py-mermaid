"""Fixed-source orthogonal visibility graph router; no native dependencies."""
import math
from functools import cmp_to_key
from .geometry import point,fixed

EPS=1e-6


def choose_side(node,target,fallback='bottom'):
    dx,dy=target['x']-node.get('x',0),target['y']-node.get('y',0)
    if abs(dx)<EPS and abs(dy)<EPS:return fallback
    if abs(dy)>EPS and abs(dy)*3>=abs(dx):return 'bottom' if dy>0 else 'top'
    return 'right' if dx>0 else 'left'


def port(node,side):
    x,y=node.get('x',0),node.get('y',0);w,h=node.get('width',10),node.get('height',10)
    return point(x,y-h/2) if side=='top' else point(x,y+h/2) if side=='bottom' else point(x-w/2,y) if side=='left' else point(x+w/2,y)


class Router:
    def __init__(self,data,direction):
        self.data=data;self.nodes=data.get('nodes',[])
        self.edges=[dict(e,__originalEdge=e) for e in data.get('edges',[]) if not e.get('isLayoutOnly')]
        self.by_id={n['id']:n for n in self.nodes};self.lanes={};self.pipes=[];self.routed=[];self.indices={};self.straights=set()
        def assign(n,lane):
            self.lanes[n['id']]=lane
            for child in self.nodes:
                if child.get('parentId')==n['id']:assign(child,lane)
        for group in self.nodes:
            if group.get('isGroup') and not group.get('parentId'):assign(group,group['id'])
        self.obstacles=[]
        for n in self.nodes:
            if n.get('isGroup') or n.get('isEdgeLabel'):continue
            w,h=n.get('width',10),n.get('height',10);x,y=n.get('x',0),n.get('y',0)
            self.obstacles.append(dict(nodeId=n['id'],minX=x-w/2-8,maxX=x+w/2+8,minY=y-h/2-8,maxY=y+h/2+8,visualXHalfExtent=(h if direction=='LR' else w)/2+8))
        self.side_info={};self.port_groups={};self.offsets={};self.incident={}
        self._assign_ports()

    def pipe(self,orientation,coord,lo,hi):
        p=next((p for p in self.pipes if p['orientation']==orientation and abs(p['coord']-coord)<1),None)
        if p is None:
            p=dict(id=f'pipe-{orientation}-{fixed(coord,0)}',orientation=orientation,coord=coord,spanMin=lo,spanMax=hi,tracks=[]);self.pipes.append(p)
        p['spanMin']=min(p['spanMin'],lo);p['spanMax']=max(p['spanMax'],hi)
        return p

    def blocked(self,a,b,start=None,end=None):
        lo_x,hi_x=min(a['x'],b['x']),max(a['x'],b['x']);lo_y,hi_y=min(a['y'],b['y']),max(a['y'],b['y'])
        for o in self.obstacles:
            if (start and o['nodeId']==start) or (end and o['nodeId']==end):continue
            if abs(a['x']-b['x'])>EPS:
                if o['minY']<a['y']<o['maxY'] and o['maxX']>lo_x and o['minX']<hi_x:return True
            elif o['minX']<a['x']<o['maxX'] and o['maxY']>lo_y and o['minY']<hi_y:return True
        return False

    def crossing_penalty(self,index,a,b):
        h=abs(a['y']-b['y'])<EPS;v=abs(a['x']-b['x'])<EPS
        if not h and not v:return 0
        along='x' if h else 'y';cross='y' if h else 'x';orientation='vertical' if h else 'horizontal'
        lo=min(a[along],b[along])-EPS;hi=max(a[along],b[along])+EPS
        if hi<=lo:return 0
        return 1000*sum(s['edgeIndex']!=index and s['orientation']==orientation and lo<=s['pipe']['coord']<=hi and s['from']-EPS<=a[cross]<=s['to']+EPS for s in self.routed)

    def _assign_ports(self):
        groups={};loads={};incoming={}
        for i,e in enumerate(self.edges):
            start,end=e.get('start'),e.get('end')
            if not start or not end or start==end:continue
            self.incident[start]=self.incident.get(start,0)+1;self.incident[end]=self.incident.get(end,0)+1
            if e.get('points'):continue
            src,dst=self.by_id.get(start),self.by_id.get(end)
            if not src or not dst:continue
            dx,dy=dst.get('x',0)-src.get('x',0),dst.get('y',0)-src.get('y',0)
            ss=choose_side(src,point(dst.get('x',0),dst.get('y',0)));ds=choose_side(dst,point(src.get('x',0),src.get('y',0)))
            info=dict(edgeIdx=i,srcId=start,dstId=end,srcSide=ss,dstSide=ds,absDx=abs(dx),absDy=abs(dy),dxSign=(dx>0)-(dx<0),dySign=(dy>0)-(dy<0));self.side_info[i]=info
            groups.setdefault((start,ss),[]).append(info)
            for key in ((start,ss),(end,ds)):loads[key]=loads.get(key,0)+1
        def strength(info):
            a,b=(info['absDy'],info['absDx']) if info['srcSide'] in ('top','bottom') else (info['absDx'],info['absDy'])
            return a/b if b else math.inf
        def secondary(info):
            if info['srcSide'] in ('top','bottom'):return 'right' if info['dxSign']>=0 else 'left'
            return 'bottom' if info['dySign']>=0 else 'top'
        def compare(a,b):
            sa,sb=strength(a),strength(b)
            return (-1 if sb<sa else 1) if abs(sa-sb)>1e-9 else a['edgeIdx']-b['edgeIdx']
        for group in groups.values():
            if len(group)<2:continue
            group.sort(key=cmp_to_key(compare))
            for info in group[1:]:
                side=secondary(info);primary=(info['srcId'],info['srcSide']);other=(info['srcId'],side)
                if loads.get(other,0)>=loads.get(primary,0):continue
                loads[primary]-=1;loads[other]=loads.get(other,0)+1;info['srcSide']=side
        for info in self.side_info.values():incoming.setdefault(info['dstId'],set()).add(info['dstSide'])
        for info in self.side_info.values():
            node=self.by_id.get(info['srcId']);ins=incoming.get(info['srcId'],set())
            if not node or node.get('shape') not in ('question','diamond') or info['srcSide'] not in ins:continue
            side=secondary(info);key=(info['srcId'],side)
            if side in ins or loads.get(key,0)>0:continue
            old=(info['srcId'],info['srcSide']);loads[old]=max(0,loads.get(old,0)-1);loads[key]=1;info['srcSide']=side
        for info in self.side_info.values():
            src,dst=self.by_id[info['srcId']],self.by_id[info['dstId']]
            for nid,side,role,opposite in ((info['srcId'],info['srcSide'],'src',dst),(info['dstId'],info['dstSide'],'dst',src)):
                coord=opposite.get('x' if side in ('top','bottom') else 'y',0)
                self.port_groups.setdefault((nid,side,role),[]).append(dict(edgeIdx=info['edgeIdx'],oppositeCoord=coord))
        for (nid,side,role),group in self.port_groups.items():
            if len(group)<2:continue
            group.sort(key=lambda p:p['oppositeCoord']);node=self.by_id[nid]
            length=node.get('height' if side in ('left','right') else 'width',10)
            if node.get('shape') in ('question','diamond'):length*=.3
            spacing=min(20,max(8,length/(len(group)+1)));start=-spacing*(len(group)-1)/2
            for j,item in enumerate(group):self.offsets[(item['edgeIdx'],role)]=start+j*spacing

    def ports(self,i,src,dst):
        info=self.side_info.get(i);target=point(dst.get('x',0),dst.get('y',0));opposite=point(src.get('x',0),src.get('y',0))
        ss=info['srcSide'] if info else choose_side(src,target);ds=info['dstSide'] if info else choose_side(dst,opposite)
        sp=port(src,ss if info else choose_side(src,target,'bottom'));dp=port(dst,ds if info else choose_side(dst,opposite,'top'))
        for p,s,role in ((sp,ss,'src'),(dp,ds,'dst')):
            if (i,role) in self.offsets:p['x' if s in ('top','bottom') else 'y']+=self.offsets[(i,role)]
        return sp,dp,ss,ds

    def _anchor_handles(self,p,node,opposite,side,endpoint_ids,source):
        vertical=side in ('top','bottom');axis='y' if vertical else 'x'
        anchor=dict(p);positive=p[axis]>node.get(axis,0);anchor[axis]+=20 if positive else -20
        o=next((o for o in self.obstacles if o['nodeId'] not in endpoint_ids and o['minX']<anchor['x']<o['maxX'] and o['minY']<anchor['y']<o['maxY']),None)
        if o is None:return anchor,[]
        if vertical:
            right=opposite.get('x',0)>=p['x']
            x=o['maxX']+15 if right else o['minX']-15;y=o['maxY']+15 if positive else o['minY']-15
            gap=min(o['minY']-2,p['y']+20) if positive else max(o['maxY']+2,p['y']-20)
            handles=[point(p['x'],gap),point(x,gap),point(x,y)] if source else [point(x,y),point(p['x'],y)]
        else:
            down=opposite.get('y',0)>=p['y']
            x=o['maxX']+15 if positive else o['minX']-15;y=o['maxY']+15 if down else o['minY']-15
            gap=min(o['minX']-2,p['x']+20) if positive else max(o['maxX']+2,p['x']-20)
            handles=[point(gap,p['y']),point(gap,y),point(x,y)] if source else [point(x,y),point(x,p['y'])]
        return point(x,y),handles

    def _fast_path(self,i,e,sp,dp,sa,da,ss,ds,sh,dh):
        if sh or dh:return False
        same_x=abs(sa['x']-da['x'])<15;same_y=abs(sa['y']-da['y'])<15
        if not (same_x or same_y) or (i,'src') in self.offsets or (i,'dst') in self.offsets:return False
        def face_total(n,s):return sum(len(self.port_groups.get((n,s,role),[])) for role in ('src','dst'))
        src_total,dst_total=face_total(e['start'],ss),face_total(e['end'],ds)
        contested=src_total>1 or dst_total>1
        def has_label(n,s):return any(self.edges[item['edgeIdx']].get('labelNodeId') for role in ('src','dst') for item in self.port_groups.get((n,s,role),[]))
        label_contest=(src_total>1 and has_label(e['start'],ss)) or (dst_total>1 and has_label(e['end'],ds))
        allowed=contested and not label_contest and (src_total<=1 or self.incident.get(e['start'],0)<=2) and (dst_total<=1 or self.incident.get(e['end'],0)<=2)
        if contested and not allowed:return False
        if self.blocked(sp,dp,e['start'],e['end']):return False
        e['points']=[dict(sp),dict(sa),dict(da),dict(dp)];self.straights.add(i)
        orientation='horizontal' if same_y else 'vertical';axis='x' if same_y else 'y';coord=sp['y' if same_y else 'x'];lo,hi=min(sp[axis],dp[axis]),max(sp[axis],dp[axis])
        pipe=dict(id=f'fast-path-{orientation}-{fixed(coord,0)}-{i}',orientation=orientation,coord=coord,spanMin=lo,spanMax=hi,tracks=[])
        self.routed.append(dict(edgeIndex=i,segmentIndex=0,orientation=orientation,pipe=pipe,trackIndex=0,**{'from':lo,'to':hi}))
        return True

    def _visibility_path(self,i,e,start,end):
        lo_x,hi_x=min(start['x'],end['x'])-50,max(start['x'],end['x'])+50
        lo_y,hi_y=min(start['y'],end['y'])-50,max(start['y'],end['y'])+50
        for o in self.obstacles:
            if o['minX']<max(start['x'],end['x']) and o['maxX']>min(start['x'],end['x']) and o['minY']<max(start['y'],end['y']) and o['maxY']>min(start['y'],end['y']):
                lo_x=min(lo_x,o['minX']-25);hi_x=max(hi_x,o['maxX']+25);lo_y=min(lo_y,o['minY']-25);hi_y=max(hi_y,o['maxY']+25)
        for o in self.obstacles:
            if o['maxX']<lo_x or o['minX']>hi_x or o['maxY']<lo_y or o['minY']>hi_y:continue
            self.pipe('horizontal',o['minY']-15,lo_x,hi_x);self.pipe('horizontal',o['maxY']+15,lo_x,hi_x)
            self.pipe('vertical',o['minX']-15,lo_y,hi_y);self.pipe('vertical',o['maxX']+15,lo_y,hi_y)
        self.pipe('horizontal',start['y'],lo_x,hi_x);self.pipe('horizontal',end['y'],lo_x,hi_x)
        hp=[p for p in self.pipes if p['orientation']=='horizontal' and lo_y<=p['coord']<=hi_y]
        vp=[p for p in self.pipes if p['orientation']=='vertical' and lo_x<=p['coord']<=hi_x]
        def blocked(a,b):return self.blocked(a,b,e['start'],e['end'])
        hv=point(end['x'],start['y']);vh=point(start['x'],end['y'])
        if not blocked(start,hv) and not blocked(hv,end):
            return [start,end] if abs(start['y']-end['y'])<EPS or abs(start['x']-end['x'])<EPS else [start,hv,end]
        if not blocked(start,vh) and not blocked(vh,end):return [start,end] if abs(start['x']-end['x'])<EPS else [start,vh,end]
        def key(p):return fixed(p['x'],1)+','+fixed(p['y'],1)
        sk,ek=key(start),key(end);g={sk:0};arrival={sk:'n'};came={};opened={sk};queue=[dict(key=sk,f=math.hypot(end['x']-start['x'],end['y']-start['y']),pt=start)]
        while queue:
            queue.sort(key=lambda item:item['f']);current=queue.pop(0);opened.discard(current['key'])
            if current['key']==ek:
                path=[end];ck=ek
                while ck in came:
                    prev=came[ck];path.insert(0,prev);ck=key(prev)
                return path
            cx,cy=current['pt']['x'],current['pt']['y'];vp.sort(key=lambda p:p['coord']);hp.sort(key=lambda p:p['coord'])
            vi=next((j for j,p in enumerate(vp) if abs(p['coord']-cx)<1),-1);hi=next((j for j,p in enumerate(hp) if abs(p['coord']-cy)<1),-1);neighbors=[]
            if vi>0:neighbors.append(point(vp[vi-1]['coord'],cy))
            if 0<=vi<len(vp)-1:neighbors.append(point(vp[vi+1]['coord'],cy))
            if hi>0:neighbors.append(point(cx,hp[hi-1]['coord']))
            if 0<=hi<len(hp)-1:neighbors.append(point(cx,hp[hi+1]['coord']))
            for neighbor in neighbors:
                if blocked(current['pt'],neighbor):continue
                nk=key(neighbor);mx,my=neighbor['x']-cx,neighbor['y']-cy;dx,dy=end['x']-start['x'],end['y']-start['y'];direction_penalty=0
                if (dy>10 and my<-5) or (dy<-10 and my>5):direction_penalty=abs(my)*100
                if (dx>10 and mx<-5) or (dx<-10 and mx>5):direction_penalty+=abs(mx)*50
                old=arrival.get(current['key'],'n');new='h' if abs(mx)>EPS else 'v';bend=50 if old!='n' and old!=new else 0
                tentative=g.get(current['key'],math.inf)+abs(mx)+abs(my)+self.crossing_penalty(i,current['pt'],neighbor)+direction_penalty+bend
                heuristic=abs(end['x']-neighbor['x'])+abs(end['y']-neighbor['y'])
                if tentative<g.get(nk,math.inf):
                    came[nk]=current['pt'];g[nk]=tentative;arrival[nk]=new
                    if nk not in opened:queue.append(dict(key=nk,f=tentative+heuristic,pt=neighbor));opened.add(nk)
                    else:
                        item=next((item for item in queue if item['key']==nk),None)
                        if item is not None:item['f']=tentative+heuristic
        # This explicit source fallback is retained, then subjected to all
        # subsequent source cleanup/validation passes; it is not a substitute router.
        return [start,point(start['x'],end['y']),end]

    def _simplify_visibility(self,path,e,is_lr):
        if len(path)<=4:return path
        start,end=path[0],path[-1];min_x,max_x=min(p['x'] for p in path),max(p['x'] for p in path)
        right=max_x>max(start['x'],end['x']);left=min_x<min(start['x'],end['x'])
        if is_lr:
            if right:
                x=max(start['x'],end['x']);obs=[o for o in self.obstacles if o['minX']<x<o['maxX'] and o['minY']<max(start['y'],end['y']) and o['maxY']>min(start['y'],end['y'])]
                if obs:max_x=max([x,*[(o['minX']+o['maxX'])/2+o['visualXHalfExtent']+15 for o in obs if not math.isnan(o['visualXHalfExtent'])]])
            if left:
                obs=[o for o in self.obstacles if o['minX']<min(start['x'],end['x'])+15 and o['minY']<max(start['y'],end['y']) and o['maxY']>min(start['y'],end['y'])]
                if obs:min_x=min([min(start['x'],end['x']),*[(o['minX']+o['maxX'])/2-o['visualXHalfExtent']-15 for o in obs]])
        if right==left:return path
        detour=max_x if right else min_x
        obs=[o for o in self.obstacles if min(start['x'],end['x'])<o['maxX'] and max(start['x'],end['x'])>o['minX'] and min(start['y'],end['y'])<o['maxY'] and max(start['y'],end['y'])>o['minY']]
        if is_lr:
            at_detour=[o for o in obs if o['minX']<detour<o['maxX']]
            if at_detour:obs=at_detour
        best_y=end['y']
        if obs:
            if end['y']>start['y']:
                candidate=max(o['maxY'] for o in obs)+15
                if candidate<end['y']-EPS:best_y=candidate
            else:
                candidate=min(o['minY'] for o in obs)-15
                if candidate>end['y']+EPS:best_y=candidate
        c1,c2,c3=point(detour,start['y']),point(detour,best_y),point(end['x'],best_y)
        check=[start,c1,c2,c3,end] if best_y!=end['y'] else [start,c1,c2,c3]
        if any(self.blocked(a,b,e['start'],e['end']) for a,b in zip(check,check[1:])):return path
        return [start,c1,c2,end] if abs(best_y-end['y'])<EPS else [start,c1,c2,c3,end]

    def initial(self,direction):
        order=[]
        for i,e in enumerate(self.edges):
            src,dst=self.by_id.get(e.get('start')),self.by_id.get(e.get('end'));sl,dl=self.lanes.get(e.get('start')),self.lanes.get(e.get('end'))
            cross=int(bool(sl and dl and sl!=dl));dist=abs(dst.get('x',0)-src.get('x',0))+abs(dst.get('y',0)-src.get('y',0)) if src and dst else 0
            order.append((i,cross,dist))
        def compare(a,b):
            if a[1]!=b[1]:return b[1]-a[1]
            if abs(a[2]-b[2])>1:return -1 if a[2]<b[2] else 1
            return a[0]-b[0]
        for i,_,__ in sorted(order,key=cmp_to_key(compare)):
            e=self.edges[i];self.indices[i]=[];src,dst=self.by_id.get(e.get('start')),self.by_id.get(e.get('end'))
            if not src or not dst or e.get('points') or e.get('start')==e.get('end'):continue
            sp,dp,ss,ds=self.ports(i,src,dst);endpoints=(e['start'],e['end'])
            sa,sh=self._anchor_handles(sp,src,dst,ss,endpoints,True);da,dh=self._anchor_handles(dp,dst,src,ds,endpoints,False)
            if self._fast_path(i,e,sp,dp,sa,da,ss,ds,sh,dh):continue
            sa['x']=self.pipe('vertical',sa['x'],sa['y'],sa['y'])['coord'];da['x']=self.pipe('vertical',da['x'],da['y'],da['y'])['coord']
            found=self._simplify_visibility(self._visibility_path(i,e,sa,da),e,direction=='LR')
            full=[sp,*sh,*found,*reversed(dh),dp]
            if len(full)>=3:
                a,b,c=full[-3:];axis='x' if abs(a['y']-b['y'])<EPS and abs(b['y']-c['y'])<EPS else 'y' if abs(a['x']-b['x'])<EPS and abs(b['x']-c['x'])<EPS else None
                if axis:
                    ab,ac=b[axis]-a[axis],c[axis]-a[axis]
                    if ab!=0 and ((ab>0)-(ab<0))==((ac>0)-(ac<0)) and abs(ab)>abs(ac):full.pop(-2)
            simplified=[full[0]]
            for k in range(1,len(full)-1):
                cur,nxt=full[k],full[k+1]
                if k==1:simplified.append(cur);continue
                prev=simplified[-1];axis='x' if abs(prev['y']-cur['y'])<EPS and abs(cur['y']-nxt['y'])<EPS else 'y' if abs(prev['x']-cur['x'])<EPS and abs(cur['x']-nxt['x'])<EPS else None
                if axis:
                    if (cur[axis]>prev[axis])!=(nxt[axis]>cur[axis]):simplified.append(cur)
                    continue
                simplified.append(cur)
            simplified.append(full[-1])
            for k,(a,b) in enumerate(zip(simplified,simplified[1:])):
                v=abs(a['x']-b['x'])<EPS;orientation='vertical' if v else 'horizontal';axis='y' if v else 'x';coord=a['x' if v else 'y'];lo,hi=min(a[axis],b[axis]),max(a[axis],b[axis]);pipe=self.pipe(orientation,coord,lo,hi)
                seg=dict(edgeIndex=i,segmentIndex=k,orientation=orientation,pipe=pipe,trackIndex=0,**{'from':lo,'to':hi})
                self.routed.append(seg);self.indices[i].append(len(self.routed)-1)
                if not pipe['tracks']:pipe['tracks'].append(dict(index=0,coord=pipe['coord'],segments=[]))
                pipe['tracks'][0]['segments'].append(dict(edgeIndex=i,segmentIndex=k,**{'from':lo,'to':hi}))

    @staticmethod
    def _overlap(a,b):return a['from']<b['to'] and b['from']<a['to']

    @staticmethod
    def _ref(s):return {k:s[k] for k in ('edgeIndex','segmentIndex','from','to')}

    @staticmethod
    def _different(a,b):return a['edgeIndex']!=b['edgeIndex'] or a['segmentIndex']!=b['segmentIndex']

    def _swap(self,a,b,ta,tb):
        can_a=not any(self._different(r,b) and self._overlap(r,a) for r in tb['segments'])
        can_b=not any(self._different(r,a) and self._overlap(r,b) for r in ta['segments'])
        if not can_a or not can_b:return False
        a['trackIndex'],b['trackIndex']=tb['index'],ta['index']
        ta['segments']=[*[r for r in ta['segments'] if self._different(r,a)],self._ref(b)]
        tb['segments']=[*[r for r in tb['segments'] if self._different(r,b)],self._ref(a)]
        return True

    def _move(self,seg,track_index):
        old=seg['pipe']['tracks'][seg['trackIndex']]
        old['segments']=[r for r in old['segments'] if self._different(r,seg)]
        seg['trackIndex']=track_index;seg['pipe']['tracks'][track_index]['segments'].append(self._ref(seg))

    def _move_chain(self,seg,track_index):
        for index in self.indices[seg['edgeIndex']]:
            s=self.routed[index]
            if s['pipe'] is seg['pipe']:self._move(s,track_index)

    def _adjacent(self,seg):
        indices=self.indices[seg['edgeIndex']];position=next((i for i,idx in enumerate(indices) if self.routed[idx] is seg),-1)
        result=[]
        if position>0:result.append(self.routed[indices[position-1]])
        if position<len(indices)-1:result.append(self.routed[indices[position+1]])
        return result

    @staticmethod
    def _cross(a,b):
        if a['orientation']==b['orientation']:return False
        h,v=(a,b) if a['orientation']=='horizontal' else (b,a)
        return h['from']<v['pipe']['coord']<h['to'] and v['from']<h['pipe']['coord']<v['to']

    def _conflict(self,a,b):
        if a['trackIndex']==b['trackIndex']:return self._overlap(a,b)
        return any(self._cross(x,y) for x in self._adjacent(a) for y in self._adjacent(b))

    def _resolve(self,a,b,move):
        if self._swap(a,b,a['pipe']['tracks'][a['trackIndex']],b['pipe']['tracks'][b['trackIndex']]):return
        available=next((t['index'] for t in a['pipe']['tracks'] if not any(self._different(r,b) and self._overlap(r,b) for r in t['segments'])),-1)
        if available==-1:
            available=len(a['pipe']['tracks']);a['pipe']['tracks'].append(dict(index=available,coord=a['pipe']['coord'],segments=[]))
        move(b,available)

    def _handle_conflicts(self,handles):
        crossings=0
        for i,a in enumerate(handles):
            for b in handles[i+1:]:
                if a['pipe'] is b['pipe'] and self._conflict(a,b):crossings+=1;self._resolve(a,b,self._move_chain)
        return crossings

    def _dest_info(self,index):
        if index in self._dest_cache:return self._dest_cache[index]
        indices=self.indices[index]
        if not indices:info=dict(dest=0,deviation=0,base=0,delta=0)
        else:
            base=self.routed[indices[0]]['pipe']['coord'];dest=base
            for idx in indices[1:]:
                seg=self.routed[idx]
                if seg['orientation']=='horizontal':
                    dest=seg['from'] if abs(seg['from']-base)>abs(seg['to']-base) else seg['to'];break
            info=dict(dest=dest,deviation=abs(dest-base),base=base,delta=dest-base)
        self._dest_cache[index]=info;return info

    def reduce_crossings(self):
        self._dest_cache={}
        def distance(i):
            e=self.edges[i];a,b=self.by_id.get(e.get('start')),self.by_id.get(e.get('end'))
            return abs(b.get('x',0)-a.get('x',0))+abs(b.get('y',0)-a.get('y',0)) if a and b else 0
        def source_cmp(a,b):
            ia,ib=self._dest_info(a),self._dest_info(b)
            for x,y in ((ia['deviation'],ib['deviation']),(ia['dest'],ib['dest']),(-distance(a),-distance(b))):
                if abs(x-y)>1:return -1 if x<y else 1
            la,lb=len(self.indices[a]),len(self.indices[b])
            if la!=lb:return la-lb
            if la==1:
                sa,sb=self.routed[self.indices[a][0]],self.routed[self.indices[b][0]]
                da,db=abs(sa['to']-sa['from']),abs(sb['to']-sb['from'])
                if abs(da-db)>1:return -1 if da<db else 1
            return 0
        def target_cmp(a,b):
            def dist(i):
                indices=self.indices[i]
                if len(indices)<2:return 0
                s=self.routed[indices[-2]];return abs(s['to']-s['from'])
            x,y=dist(a),dist(b)
            return (-1 if x<y else 1) if abs(x-y)>.1 else a-b
        for _ in range(10):
            changed=0
            for field,compare,position in (('start',source_cmp,0),('end',target_cmp,-1)):
                groups={}
                for i,e in enumerate(self.edges):
                    if self.indices[i] and e.get(field):groups.setdefault(e[field],[]).append(i)
                for group in groups.values():
                    group.sort(key=cmp_to_key(compare));handles=[self.routed[self.indices[i][position]] for i in group]
                    changed+=self._handle_conflicts(handles)
            for pipe in self.pipes:
                ss=[]
                for track in pipe['tracks']:
                    for ref in track['segments']:
                        idx=next((idx for idx in self.indices[ref['edgeIndex']] if self.routed[idx]['segmentIndex']==ref['segmentIndex']),None)
                        if idx is not None:ss.append(self.routed[idx])
                ss.sort(key=lambda s:(s['edgeIndex'],s['segmentIndex']))
                for i,a in enumerate(ss):
                    for b in ss[i+1:]:
                        if self._conflict(a,b):changed+=1;self._resolve(a,b,self._move)
            if changed==0:break

    def rebuild(self):
        coords={}
        for pipe in self.pipes:
            ss=[dict(ref,trackIndex=track['index']) for track in pipe['tracks'] for ref in track['segments']]
            ss.sort(key=lambda s:s['from']);clusters=[]
            if ss:
                cluster=[ss[0]];end=ss[0]['to']
                for s in ss[1:]:
                    if s['from']<end:cluster.append(s);end=max(end,s['to'])
                    else:clusters.append(cluster);cluster=[s];end=s['to']
                clusters.append(cluster)
            for cluster in clusters:
                used=list(dict.fromkeys(s['trackIndex'] for s in cluster));scores={}
                for s in cluster:scores[s['trackIndex']]=scores.get(s['trackIndex'],0)+self._dest_info(s['edgeIndex'])['delta']
                left=sorted((t for t in used if scores.get(t,0)<-1),key=lambda t:-scores.get(t,0));right=sorted((t for t in used if scores.get(t,0)>1),key=lambda t:scores.get(t,0));neutral=[t for t in used if abs(scores.get(t,0))<=1]
                def assign(track,coord):
                    for s in cluster:
                        if s['trackIndex']==track:coords[(s['edgeIndex'],s['segmentIndex'])]=pipe['coord'] if s['edgeIndex'] in self.straights else coord
                # Source assigns left coordinates before selecting a neutral
                # track, then overwrites the chosen center, preserving order.
                for count,t in enumerate(left,1):assign(t,pipe['coord']-count*10)
                if not neutral and used:
                    best=min(used,key=lambda t:abs(scores.get(t,0)))
                    if best in left:left.remove(best)
                    if best in right:right.remove(best)
                    neutral.append(best)
                for j,t in enumerate(neutral):assign(t,pipe['coord'] if j==0 else pipe['coord']+(1 if j%2 else -1)*math.ceil(j/2)*5)
                for count,t in enumerate(right,1):assign(t,pipe['coord']+count*10)
        def on_line(line,along):return point(line['coord'],along) if line['orient']=='vertical' else point(along,line['coord'])
        def shared(line,nxt):return line['to'] if abs(line['to']-nxt['from'])<EPS or abs(line['to']-nxt['to'])<EPS else line['from']
        for i,e in enumerate(self.edges):
            indices=self.indices.get(i,[])
            if not indices:continue
            sp,dp,_,__=self.ports(i,self.by_id[e['start']],self.by_id[e['end']])
            lines=[]
            for idx in indices:
                s=self.routed[idx];lines.append(dict(orient=s['orientation'],coord=coords.get((s['edgeIndex'],s['segmentIndex']),s['pipe']['coord']),**{'from':s['from'],'to':s['to']}))
            out=[sp]
            for k,line in enumerate(lines):
                prev=out[-1];v=line['orient']=='vertical';along=prev['y' if v else 'x'];track=prev['x' if v else 'y'];nxt=lines[k+1] if k+1<len(lines) else None
                if abs(track-line['coord'])>EPS:out.append(on_line(line,along))
                if nxt and nxt['orient']==line['orient']:
                    if abs(line['coord']-nxt['coord'])>EPS:
                        junction=(along+nxt['from'])/2 if v else shared(line,nxt);out.extend((on_line(line,junction),on_line(nxt,junction)))
                    elif k==0 or k==len(lines)-2:out.append(on_line(line,shared(line,nxt)))
                elif nxt:out.append(on_line(line,nxt['coord']))
                else:out.append(on_line(line,line['to'] if abs(line['from']-along)<abs(line['to']-along) else line['from']))
            if abs(out[-1]['x']-dp['x'])>EPS or abs(out[-1]['y']-dp['y'])>EPS:out.append(dp)
            filtered=[]
            for p in out:
                if not filtered or abs(p['x']-filtered[-1]['x'])>EPS or abs(p['y']-filtered[-1]['y'])>EPS:filtered.append(p)
            e['points']=filtered
        for e in self.edges:
            if e.get('points') is not None:e['__originalEdge']['points']=e['points']
        self.data['edges']=[e for e in self.data.get('edges',[]) if not e.get('isLayoutOnly')]
        def clamp(p,n):
            x,y=n.get('x',0),n.get('y',0);w,h=n.get('width',0),n.get('height',0)
            if w<=0 or h<=0:return p
            left,right,top,bottom=x-w/2,x+w/2,y-h/2,y+h/2
            if p['x']<left or p['x']>right or p['y']<top or p['y']>bottom:return p
            distances=(p['x']-left,right-p['x'],p['y']-top,bottom-p['y']);minimum=min(distances)
            if minimum==distances[0]:return point(left,p['y'])
            if minimum==distances[1]:return point(right,p['y'])
            if minimum==distances[2]:return point(p['x'],top)
            return point(p['x'],bottom)
        for e in self.data['edges']:
            pts=e.get('points') or []
            if len(pts)<2:continue
            src,dst=self.by_id.get(e.get('start')),self.by_id.get(e.get('end'))
            if src:pts[0]=clamp(pts[0],src)
            if dst:pts[-1]=clamp(pts[-1],dst)


def route_edges_orthogonal(data,direction=None):
    router=Router(data,direction);router.initial(direction);router.reduce_crossings();router.rebuild()
    return data
