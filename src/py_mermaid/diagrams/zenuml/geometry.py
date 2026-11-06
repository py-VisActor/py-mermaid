"""Source DavidEisenstat dual-number spacing and recursive vertical VM."""
from dataclasses import dataclass
import math


def optimal_positions(matrix):
    """Direct pure port of positioning/david/DavidEisenstat.find_optimal."""
    n=len(matrix)
    if not n:return []
    graph=[[(i,(matrix[i][j],0.)) for i in range(j) if matrix[i][j]>0] for j in range(n)]
    gaps=[[0.,1.] for _ in range(n-1)];epsilon=math.sqrt(2.220446049250313e-16)
    def plus(a,b):return (a[0]+b[0],a[1]+b[1])
    for _ in range(100000):
        delta=math.inf;table=[];maximum=(0.,0.)
        def less(x,y):
            nonlocal delta
            difference=x[0]-y[0];result=difference<-epsilon or abs(difference)<=epsilon and x[1]<y[1]
            if result:x,y=y,x
            if x[1]<y[1]:delta=min(delta,(x[0]-y[0])/(y[1]-x[1]))
            return result
        for j in range(n):
            argument=None
            if j:maximum=plus(maximum,gaps[j-1])
            for i,length in graph[j]:
                candidate=plus(table[i][1],length)
                if less(maximum,candidate):argument=i;maximum=candidate
            table.append((argument,maximum))
        if delta==math.inf:return [entry[1][0] for entry in table]
        if table[-1][1][1]>0:
            j=n-1
            while j>0:
                argument=table[j][0]
                if argument is not None:j=argument
                else:j-=1;gaps[j][1]=0
        else:
            for gap in gaps:gap[0]+=gap[1]*delta
    raise ValueError('ZenUML horizontal numerical budget exceeded')


@dataclass(frozen=True)
class PlacedStatement:
    node: object
    top: float
    height: float
    number: str
    depth: int
    sender_depth: int = 0
    target_depth: int = 0
    sections: tuple = ()
    comment_height: float = 0


def vertical_layout(nodes,*,top=56.,origin='_STARTER_',comment_measurer=None):
    """Port BlockVM, message/creation/fragment VMs and visual return debt.

    Source coordinates stay in the content group. A zero-height final return
    inside an occurrence receives visual space without clipping its glyphs.
    """
    placed=[];creations={};max_return=[0.]
    def comment_height(node):
        if comment_measurer is not None:return comment_measurer(node.comment)
        return len(node.comment.strip().split('\n'))*20 if node.comment.strip() else 0.
    def block(items,start,origin,parent='',prefix='',depth=0,active=None,index_offset=0):
        if depth>128:raise ValueError('ZenUML vertical nesting budget exceeded')
        if not items:return start
        cursor=start+16;active=active or {}
        for ordinal,node in enumerate(items,1+index_offset):
            if parent=='par' and ordinal>1:cursor+=1
            number=prefix+'.'+str(ordinal) if prefix else str(ordinal);position=cursor;ch=comment_height(node);sections=[]
            sd=active.get(node.source,0);td=active.get(node.target,0)
            if node.kind in {'sync','creation'}:
                message_height=40 if node.kind=='creation' else 30 if node.source==node.target else 16
                if node.kind=='creation':creations[node.target]=position+ch
                cursor=position+ch+message_height
                if node.children:
                    inner=dict(active);inner[node.target]=td+1
                    cursor=block(node.children,cursor,node.target,node.kind,number,depth+1,inner)+2
                else:cursor+=22
                if node.assignment:cursor+=16 if node.children else 12
            elif node.kind=='async':cursor=position+ch+(44 if node.source==node.target else 16)
            elif node.kind=='return':
                # Source return debt restores the16px actual return after the
                # engine's zero-height occurrence-last return calculation.
                cursor=position+ch+(20 if node.source==node.target else 16);max_return[0]=max(max_return[0],cursor+47)
            elif node.kind=='divider':cursor=position+40
            elif node.kind=='ref':cursor=position+ch+25+10
            else:
                cursor=position+1+25+ch
                if node.sections:
                    section_offset=0
                    for section_index,(label,children) in enumerate(node.sections):
                        if node.kind=='alt' or section_index:cursor+=20+(9 if section_index else 0)
                        sections.append((label,cursor))
                        cursor=block(children,cursor,origin,node.kind,number,depth+1,active,section_offset)
                        section_offset+=len(children)
                else:
                    if node.label:cursor+=20
                    cursor=block(node.children,cursor,origin,node.kind,number,depth+1,active)
                cursor+=11
            placed.append(PlacedStatement(node,position,cursor-position,number,depth,sd,td,tuple(sections),ch))
            cursor+=16
        return cursor
    height=block(nodes,top,origin)
    return tuple(sorted(placed,key=lambda item:(item.top,item.depth))),creations,max(height+28,max_return[0])
