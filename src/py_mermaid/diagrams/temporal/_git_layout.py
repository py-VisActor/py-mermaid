"""GitGraph commit positioning and rounded, collision-rerouted branch edges."""

def positions(commits,branches,direction,parallel,redux=False):
    result={};chronology={};default=30 if direction!='LR' else 0
    ordered=sorted(commits,key=lambda c:c.seq)
    if direction=='BT' and parallel:
        cur=30;maximum=30;roots=[]
        for commit in ordered:
            if commit.parents:
                cur=max(result[p][1] for p in commit.parents)+40;maximum=max(cur,maximum)
            else:roots.append(commit)
            result[commit.id]=(branches[commit.branch],cur+10)
        for commit in roots:result[commit.id]=(branches[commit.branch],maximum+30)
        for commit in ordered:
            if commit.parents:result[commit.id]=(branches[commit.branch],min(result[p][1] for p in commit.parents)-50)
    traversal=ordered[::-1] if direction=='BT' else ordered;pos=default;maxpos=0
    for commit in traversal:
        if parallel:
            if direction=='BT':pos=result[commit.id][1]-40
            elif commit.parents:pos=max(result[p][1 if direction=='TB' else 0] for p in commit.parents)+40
            else:pos=30 if direction=='TB' else 0
        offset=pos if direction=='BT' and parallel else pos+10
        if direction=='LR':result[commit.id]=(offset,branches[commit.branch]+(7 if redux else -2))
        else:result[commit.id]=(branches[commit.branch],offset)
        chronology[commit.id]=pos;pos+=40 if direction=='BT' and parallel else 50;maxpos=max(maxpos,pos)
    return result,chronology,maxpos

def edge_path(parent,commit,positions,all_commits,direction,lanes):
    p1=positions[parent.id];p2=positions[commit.id]
    farther=p1[0]<p2[0] if direction!='LR' else p1[1]<p2[1]
    branch=commit.branch if farther else parent.branch
    reroute=any(c.branch==branch and parent.seq<c.seq<commit.seq for c in all_commits)
    def lane(a,b,depth=0):
        candidate=a+abs(a-b)/2
        if depth>5:return candidate
        if all(abs(v-candidate)>=10 for v in lanes):lanes.append(candidate);return candidate
        return lane(a,b-abs(a-b)/5,depth+1)
    line_y=line_x=None
    if reroute:
        line_y=lane(min(p1[1],p2[1]),max(p1[1],p2[1]));line_x=lane(min(p1[0],p2[0]),max(p1[0],p2[0]))
    # The source LR/TB/BT branch cases are rotations/reflections of this
    # chronological/branch frame. SVG path transforms preserve arc winding.
    if direction=='LR':a,b=p1,p2;matrix=(1,0,0,1,0,0);middle=line_y
    elif direction=='TB':a=(p1[1],p1[0]);b=(p2[1],p2[0]);matrix=(0,1,1,0,0,0);middle=line_x
    else:a=(-p1[1],p1[0]);b=(-p2[1],p2[0]);matrix=(0,-1,1,0,0,0);middle=line_x
    x1,y1=a;x2,y2=b;merge=commit.type=='MERGE' and parent.id!=commit.parents[0]
    if y1==y2:return f'M{x1:g},{y1:g}L{x2:g},{y2:g}',matrix,parent.branch if merge else commit.branch
    sign=1 if y1<y2 else -1;r=10 if reroute else 20;sweep=0 if sign>0 else 1
    if reroute:
        d=f'M{x1:g},{y1:g}L{x1:g},{middle-sign*r:g}A{r},{r} 0 0,{sweep} {x1+r:g},{middle:g}L{x2-r:g},{middle:g}A{r},{r} 0 0,{1-sweep} {x2:g},{middle+sign*r:g}L{x2:g},{y2:g}'
        color_branch=commit.branch if sign>0 else parent.branch
    elif merge:
        d=f'M{x1:g},{y1:g}L{x2-r:g},{y1:g}A{r},{r} 0 0,{1-sweep} {x2:g},{y1+sign*r:g}L{x2:g},{y2:g}'
        color_branch=parent.branch
    else:
        d=f'M{x1:g},{y1:g}L{x1:g},{y2-sign*r:g}A{r},{r} 0 0,{sweep} {x1+r:g},{y2:g}L{x2:g},{y2:g}'
        color_branch=commit.branch
    return d,matrix,color_branch
