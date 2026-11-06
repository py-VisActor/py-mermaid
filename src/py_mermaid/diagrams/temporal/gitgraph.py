"""GitGraph Langium semantics, immutable commit DAG and dedicated lanes."""
from dataclasses import dataclass
import math,re,secrets
from ...runtime.common import make_diagram,config_dict,error
from ..charts._syntax import statements,common_statement,theme,number,palette,tokens
from ._syntax import plain_label,langium_metadata
from ._git_layout import positions,edge_path

@dataclass(frozen=True)
class Commit:
    id:str
    message:str
    seq:int
    type:str
    tags:tuple[str,...]
    parents:tuple[str,...]
    branch:str
    custom_type:str|None=None
    custom_id:bool=False

@dataclass(frozen=True)
class GitGraph:
    direction:str
    title:str
    commits:tuple[Commit,...]
    branches:tuple[tuple[str,int|float],...]
    heads:tuple[tuple[str,str|None],...]
    accessibility:tuple=()

def parse(document,config):
    masked,common=langium_metadata(document);rows=statements(masked);meta={'title':document.title,**common};cfg=config.get('gitGraph',{});main=cfg.get('mainBranchName','main');branches={main:cfg.get('mainBranchOrder',0)};heads={main:None};current=main;head=None;commits={};sequence=0;direction='LR'
    if any(document.cleaned[token.offset:token.offset+1]==';' for token in tokens(masked) if not token.quoted):raise error(document,0,'GitGraph statements require newline separators')
    if not rows or rows[0][0].value!='gitGraph':raise error(document,0,'Expected gitGraph')
    rest=rows.pop(0)[1:]
    if rest and rest[0].value in ('LR','TB','BT'):
        direction=rest[0].value;rest=rest[1:]
        if not rest or rest[0].value!=':':raise error(document,0,'GitGraph direction requires a colon')
    if rest and rest[0].value==':':rest=rest[1:]
    if rest:rows.insert(0,rest)
    def generated():return str(sequence)+'-'+''.join(secrets.choice('0123456789abcdef') for _ in range(7))
    for row in rows:
        if common_statement(row,meta):continue
        cmd=row[0].value;rest=row[1:];attrs={};tags=[];branch=None
        if cmd in ('branch','merge','checkout','switch'):
            if not rest:raise error(document,row[0].offset,'Git command requires a branch')
            # REFERENCE includes slash/dot, unlike the shared chart ID token.
            stop=next((i for i,t in enumerate(rest) if i+1<len(rest) and rest[i+1].value==':' and t.value in ('order','id','tag','type')),len(rest))
            nameparts=rest[:stop]
            if not nameparts:raise error(document,row[0].offset,'Expected Git branch name')
            branch=''.join(t.value for t in nameparts)
            if len(nameparts)>1 and any(t.quoted for t in nameparts):raise error(document,nameparts[0].offset,'Malformed quoted Git branch')
            if not nameparts[0].quoted and not re.fullmatch(r'\w(?:[-./\w]*[-\w])?',branch):raise error(document,nameparts[0].offset,'Invalid Git branch reference')
            rest=rest[stop:]
        i=0
        while i<len(rest):
            t=rest[i]
            if t.quoted and cmd=='commit':attrs['msg']=t.value;i+=1;continue
            if i+2>=len(rest) or rest[i+1].value!=':':raise error(document,t.offset,'Expected Git option key:value')
            key=t.value;value=rest[i+2];i+=3
            allowed={'branch':('order',),'merge':('id','tag','type'),'commit':('id','msg','tag','type'),'cherry-pick':('id','tag','parent')}.get(cmd,())
            if key not in allowed:raise error(document,t.offset,'Unknown option for Git '+cmd)
            if key in ('id','msg','tag','parent') and not value.quoted:raise error(document,value.offset,'Git textual options must be quoted')
            if key=='type' and value.value not in ('NORMAL','REVERSE','HIGHLIGHT'):raise error(document,value.offset,'Unknown Git commit type')
            if key=='order' and not re.fullmatch(r'\d+',value.value):raise error(document,value.offset,'Git branch order must be nonnegative integer')
            if key=='tag':tags.append(value.value)
            else:attrs[key]=int(value.value) if key=='order' else value.value
        if cmd in ('checkout','switch'):
            if branch not in heads:raise error(document,row[0].offset,'Trying to checkout branch which is not yet created','UNKNOWN_GIT_BRANCH')
            current=branch;head=heads[current];continue
        if cmd=='branch':
            if branch in heads:raise error(document,row[0].offset,'Trying to create an existing branch','DUPLICATE_GIT_BRANCH')
            branches[branch]=attrs.get('order',0);heads[branch]=head;current=branch;continue
        if cmd=='commit':
            id=attrs.get('id') or generated();commit=Commit(id,attrs.get('msg',''),sequence,attrs.get('type','NORMAL'),tuple(tags),(head,) if head is not None else (),current,custom_id=bool(attrs.get('id')))
        elif cmd=='merge':
            if branch==current:raise error(document,row[0].offset,'Cannot merge a branch to itself','INVALID_GIT_MERGE')
            if not head:raise error(document,row[0].offset,'Current branch has no commits','INVALID_GIT_MERGE')
            if branch not in heads or not heads[branch]:raise error(document,row[0].offset,'Branch to be merged does not exist or has no commits','INVALID_GIT_MERGE')
            if head==heads[branch] or commits[head].branch==branch:raise error(document,row[0].offset,'Both branches have same head or merge targets same source branch','INVALID_GIT_MERGE')
            id=attrs.get('id') or generated()
            if attrs.get('id') and id in commits:raise error(document,row[0].offset,'Merge commit id already exists','DUPLICATE_GIT_COMMIT')
            commit=Commit(id,f'merged branch {branch} into {current}',sequence,'MERGE',tuple(tags),(head,heads[branch]),current,attrs.get('type'),bool(attrs.get('id')))
        elif cmd=='cherry-pick':
            source=commits.get(attrs.get('id'));parent=attrs.get('parent')
            if source is None:raise error(document,row[0].offset,'Cherry-pick source commit must exist','INVALID_CHERRY_PICK')
            if parent and parent not in source.parents:raise error(document,row[0].offset,'Specified parent is not an immediate source parent','INVALID_CHERRY_PICK')
            if source.type=='MERGE' and not parent:raise error(document,row[0].offset,'Cherry-picking a merge requires an immediate parent','INVALID_CHERRY_PICK')
            if source.branch==current or not head:raise error(document,row[0].offset,'Cherry-pick source is on current branch or current branch has no commits','INVALID_CHERRY_PICK')
            id=generated();auto='cherry-pick:'+source.id+('|parent:'+parent if source.type=='MERGE' else '')
            commit=Commit(id,f'cherry-picked {source.message} into {current}',sequence,'CHERRY_PICK',tuple(t for t in tags if t) if tags else (auto,),(head,source.id),current)
        else:raise error(document,row[0].offset,'Unexpected GitGraph command')
        commits[commit.id]=commit;head=commit.id;heads[current]=head;sequence+=1
    ordered=tuple(sorted(branches.items(),key=lambda kv:kv[1]))
    return make_diagram('gitGraph',document,config,GitGraph(direction,meta.get('title',''),tuple(commits.values()),ordered,tuple(heads.items()),tuple((k,v) for k,v in meta.items() if k!='title')))

def _rotate(point,origin,angle):
    c=math.cos(math.radians(angle));s=math.sin(math.radians(angle));x=point[0]-origin[0];y=point[1]-origin[1]
    return origin[0]+c*x-s*y,origin[1]+s*x+c*y

async def build(diagram,p):
    from ._source_styles import git as source_styles
    cfg_all=config_dict(diagram);tv=cfg_all['themeVariables']
    if tv.get('useGradient') and tv.get('gradientStart') and tv.get('gradientStop'):p.register_gradient(p.render_id+'-gradient',((0,tv['gradientStart']),(1,tv['gradientStop'])),direction=(0,0,1,0))
    p.add_styles(source_styles(tv,cfg_all.get('theme','default'),p.render_id))
    from ._paint import TemporalPainter
    p=TemporalPainter(p,'gitGraph');p.text_classes=('commit-label',)
    m=diagram.model;c=config_dict(diagram);cfg=c.get('gitGraph',{});themename=c.get('theme','');redux=themename in ('redux','redux-dark','redux-color','redux-dark-color');color_theme=themename in ('redux-color','redux-dark-color');neo=themename in ('neo','neo-dark');dark=themename in ('dark','redux-dark','redux-dark-color','neo-dark');rotate=cfg.get('rotateCommitLabel',True);branchpositions={};labels={};position=0.;indices={name:i for i,(name,order) in enumerate(m.branches)};colors=palette(c,'git',8);slots=c.get('themeVariables',{}).get('borderColorArray',())
    for name,order in m.branches:
        label=p.measure(plain_label(name),html=False);labels[name]=label;branchpositions[name]=position;position+=50+(40 if rotate else 0)+(label.width/2 if m.direction in ('TB','BT') else 0)
    pos,chronology,maximum=positions(m.commits,branchpositions,m.direction,cfg.get('parallelCommits',False),redux);lanes=[];byid={commit.id:commit for commit in m.commits}
    def branch_color(name):
        i=indices[name];idx=((i-1)%7+1) if color_theme and i else i%8
        if color_theme:return theme(c,'nodeBorder','#333') if idx==0 else slots[idx%len(slots)] if slots else theme(c,'nodeBorder','#333')
        if redux or neo and idx==0:return theme(c,'nodeBorder','#333')
        return colors[idx]
    if cfg.get('showBranches',True):
        for name,order in m.branches:
            index=indices[name]
            p.extra['branch-'+name]=('branch',)
            p.extra['branch-label-bg-'+name]=('label'+str(index),)
            p.extra['branch-label-'+name]=('branch-label','branch-label'+str(index))
            cross=branchpositions[name];spine=cross if m.direction!='LR' else cross+(7 if redux else -2);lanes.append(spine);label=labels[name];fill=branch_color(name) if color_theme or not(redux or neo) else theme(c,'mainBkg','#fff');stroke=branch_color(name)
            if m.direction=='LR':
                p.line(0,spine,maximum,spine,stroke=theme(c,'commitLineColor',theme(c,'lineColor','#333')),line_width=number(theme(c,'strokeWidth',1),1),dash=(4,2) if redux or neo else (2,2),id='branch-'+name)
                bx=-label.width-4-(30 if rotate else 0)-19;by=spine-12-(6 if redux else 0)-label.height/2+10;bw=label.width+18+(16 if redux else 0);bh=label.height+4+(12 if redux else 0);tx=-label.width-14-(30 if rotate else 0)+(8 if redux else 0);ty=spine-label.height/2-2
            else:
                bottom=maximum if m.direction=='BT' else 0
                p.line(cross,maximum if m.direction=='BT' else 30,cross,30 if m.direction=='BT' else maximum,stroke=theme(c,'commitLineColor',theme(c,'lineColor','#333')),line_width=number(theme(c,'strokeWidth',1),1),dash=(4,2) if redux or neo else (2,2),id='branch-'+name)
                bx=cross-label.width/2-10-(11 if redux else 0);by=bottom+(-22 if redux and m.direction=='TB' else 22 if redux else 0);bw=label.width+18+(16 if redux else 0);bh=label.height+4+(12 if redux else 0);tx=cross-label.width/2-5;ty=bottom+(-17 if redux and m.direction=='TB' else 28 if redux else 0)
            p.rect(bx,by,bw,bh,fill=fill,stroke=stroke,line_width=number(theme(c,'strokeWidth',1),1),radius=0 if redux else 4,id='branch-label-bg-'+name);p.text(label,tx,ty,html=False,color=theme(c,'nodeBorder','#333') if redux or neo else theme(c,'gitBranchLabel'+str(indices[name]%8),'#fff'),id='branch-label-'+name)
    for commit in m.commits:
        for parent in commit.parents:
            if parent not in byid:raise error(diagram.source,0,'GitGraph parent commit is missing','INVALID_GIT_GRAPH')
            path,matrix,name=edge_path(byid[parent],commit,pos,m.commits,m.direction,lanes);ident='edge-'+parent+'-'+commit.id;p.extra[ident]=('arrow','arrow'+str(indices[name]));p.path(path,fill='none',stroke=branch_color(name),line_width=number(theme(c,'strokeWidth',2),2) if redux else 8,transform=matrix,id=ident,role='edge')
    for commit in sorted(m.commits,key=lambda v:v.seq,reverse=m.direction=='BT'):
        x,y=pos[commit.id];color=branch_color(commit.branch);kind=commit.custom_type or commit.type;inner=theme(c,'mainBkg','#fff') if redux or neo else theme(c,'primaryColor','#ececff');r=7 if redux else 10
        slot=indices[commit.branch];p.extra[commit.id]=('commit','commit'+str(slot)) if kind!='HIGHLIGHT' else ('commit-highlight','commit-highlight'+str(slot),'commit-highlight-outer')
        p.extra[commit.id+'-inner']=('commit-highlight-inner',);p.extra[commit.id+'-merge']=('commit-merge',);p.extra[commit.id+'-reverse']=('commit-reverse',);p.extra[commit.id+'-label-bg']=('commit-label-bkg',)
        if kind=='HIGHLIGHT':
            p.rect(x-r,y-r,2*r,2*r,fill=color,stroke=color,id=commit.id);rr=4 if redux else 6;p.rect(x-rr,y-rr,rr*2,rr*2,fill=inner,stroke=inner,id=commit.id+'-inner')
        else:
            p.ellipse(x,y,r,r,fill=color,stroke=color,line_width=2,id=commit.id,role='commit')
            if kind=='MERGE':p.ellipse(x,y,5 if redux else 6,5 if redux else 6,fill=inner,stroke=inner,id=commit.id+'-merge')
            elif kind=='REVERSE':
                rr=4 if redux else 5;p.path(f'M{x-rr:g},{y-rr:g}L{x+rr:g},{y+rr:g}M{x-rr:g},{y+rr:g}L{x+rr:g},{y-rr:g}',stroke=inner,line_width=number(theme(c,'strokeWidth',1),1) if redux or neo else 3,id=commit.id+'-reverse')
            elif kind=='CHERRY_PICK':
                for side in (-1,1):p.ellipse(x+side*3,y+2,2.5 if redux else 2.75,2.5 if redux else 2.75,fill='#000' if dark else '#fff',stroke='none',id=commit.id+'-cherry-'+str(side));p.line(x+side*3,y+1,x,y-5,stroke='#000' if dark else '#fff',id=commit.id+'-cherry-stem-'+str(side))
        if commit.type!='CHERRY_PICK' and (commit.type!='MERGE' or commit.custom_id) and cfg.get('showCommitLabel',True):
            label=p.measure(commit.id,size=number(theme(c,'commitLabelFontSize',10),10),html=False);vertical=m.direction in ('TB','BT');bx=x-label.width-21 if vertical else x-label.width/2-2;by=y-12 if vertical else y+13.5;tx=x-label.width-16 if vertical else x-label.width/2;ty=y+label.height-12-label.ascent if vertical else y+25-label.ascent
            if not(redux or neo):
                d=f'M{bx:g},{by:g}h{label.width+4:g}v{label.height+4:g}h{-label.width-4:g}Z'
                if rotate:
                    a=math.radians(-45);origin=(x,y) if vertical else (chronology[commit.id],y);ex,ey=(0,0) if vertical else (-7.5-((label.width+10)/25)*9.5,10+(label.width/25)*8.5);matrix=(math.cos(a),math.sin(a),-math.sin(a),math.cos(a),origin[0]-math.cos(a)*origin[0]+math.sin(a)*origin[1]+ex,origin[1]-math.sin(a)*origin[0]-math.cos(a)*origin[1]+ey)
                    p.path(d,fill=theme(c,'commitLabelBackground','#fff'),stroke='none',opacity=.5,transform=matrix,id=commit.id+'-label-bg')
                    tx,ty=_rotate((tx,ty),origin,-45);tx+=ex;ty+=ey
                else:p.path(d,fill=theme(c,'commitLabelBackground','#fff'),stroke='none',opacity=.5,id=commit.id+'-label-bg')
            elif rotate:
                origin=(x,y) if vertical else (chronology[commit.id],y);tx,ty=_rotate((tx,ty),origin,-45)
                if not vertical:tx+=-7.5-((label.width+10)/25)*9.5;ty+=10+(label.width/25)*8.5
            p.text(label,tx,ty,rotation=-45 if rotate else 0,color=theme(c,'nodeBorder','#333') if redux or neo else theme(c,'commitLabelColor','#333'),html=False,id=commit.id+'-label')
        tagboxes=[p.measure(t,size=number(theme(c,'tagLabelFontSize',10),10),html=False) for t in reversed(commit.tags)];tw=max((t.width for t in tagboxes),default=0);th=max((t.height for t in tagboxes),default=0)
        for i,label in enumerate(tagboxes):
            offset=i*20;ly=y-19.2-offset;pp=chronology[commit.id]
            if m.direction=='LR':
                points=((pp-tw/2-2,ly+2),(pp-tw/2-2,ly-2),(x-tw/2-4,ly-th/2-2),(x+tw/2+4,ly-th/2-2),(x+tw/2+4,ly+th/2+2),(x-tw/2-4,ly+th/2+2));hole=(pp-tw/2+2,ly);tx=x-label.width/2;ty=y-16-offset-label.ascent;angle=0
            else:
                origin=(x,pp);basey=pp+offset;points=tuple((a+12,b+12) for a,b in (_rotate(v,origin,45) for v in ((x,basey+2),(x,basey-2),(x+10,basey-th/2-2),(x+10+tw+4,basey-th/2-2),(x+10+tw+4,basey+th/2+2),(x+10,basey+th/2+2))));a,b=_rotate((x+2,basey),origin,45);hole=(a+12,b+12);a,b=_rotate((x+5,basey+3-label.ascent),origin,45);tx=a+14;ty=b+14;angle=45
            p.polygon(points,fill=theme(c,'mainBkg','#fff') if redux or neo else theme(c,'tagLabelBackground','#fff'),stroke=theme(c,'nodeBorder','#333') if redux or neo else theme(c,'tagLabelBorder','#333'),id=commit.id+'-tag-bg-'+str(i));p.ellipse(*hole,1.5,1.5,fill=theme(c,'textColor','#333'),stroke='none',id=commit.id+'-tag-hole-'+str(i));p.text(label,tx,ty,rotation=angle,color=theme(c,'tagLabelColor','#333'),html=False,id=commit.id+'-tag-'+str(i))
    if m.title:
        minx=min((x for x,y in pos.values()),default=0);maxx=max((x for x,y in pos.values()),default=0);p.text(m.title,(minx+maxx)/2,-cfg.get('titleTopMargin',25)-20,align='center',html=False,role='title')
    return p.finish(padding=cfg.get('diagramPadding',8),layout={'kind':'gitGraph','commits':tuple((id,*point) for id,point in pos.items()),'branches':tuple(branchpositions.items()),'parallel':cfg.get('parallelCommits',False)})
