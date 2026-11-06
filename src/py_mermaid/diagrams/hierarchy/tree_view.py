"""Langium TreeView values, box-drawing preprocessing and source preorder rows."""
from dataclasses import dataclass
import math
import re
from ..modeling._support import number


@dataclass(frozen=True)
class TreeNode:
    id:int
    name:str
    level:int
    parent:int|None
    directory:bool=False
    css_class:str=''
    icon:str|None=None
    description:str=''


@dataclass(frozen=True)
class TreeViewModel:
    nodes:tuple[TreeNode,...]
    title:str=''
    acc_title:str=''
    acc_description:str=''


_FOLDER='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M10.59 4.59A2 2 0 0 0 9.17 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.17z"/></svg>'
_FILE='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" fill-rule="evenodd" d="M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8.83a2 2 0 0 0-.59-1.42l-4.82-4.82A2 2 0 0 0 13.17 2H6Zm7.5 1.9l4.6 4.6h-3.6a1 1 0 0 1-1-1V3.9Z" clip-rule="evenodd"/></svg>'
_BOX=re.compile('[─━│┃└┗├┣]');_BRANCH=re.compile('[└┗├┣]');_META=re.compile(r'^\s*(title(?:[\t ]|$)|accTitle[\t ]*:|accDescr[\t ]*[:{])')


def _records(document):
    from ...runtime.common import error
    records=[];offset=0
    for line in document.cleaned.splitlines(keepends=True):records.append((line.rstrip('\r\n'),offset));offset+=len(line)
    key=next((i for i,(line,_) in enumerate(records) if line.strip()=='treeView-beta'),None)
    if key is None:raise error(document,0,'Expected treeView-beta')
    content=[line.replace('\t','    ') for line,_ in records[key+1:] if line.strip() and not line.lstrip().startswith('%%') and not _META.match(line) and not re.fullmatch(r'[\s│┃]+',line)]
    if not any(_BOX.search(line) for line in content):return records[key+1:]
    segment=next((m.start() for line in content if (m:=_BRANCH.search(line)) and m.start()>0),4);result=[]
    for line,offset in records[key+1:]:
        if not line.strip() or line.lstrip().startswith('%%') or _META.match(line):result.append((line,offset));continue
        if re.fullmatch(r'[\s│┃]+',line):continue
        normal=line.replace('\t','    ');branch=_BRANCH.search(normal)
        if branch:
            depth=math.floor(branch.start()/segment+.5)+1;pos=branch.start()+1
            while pos<len(normal) and normal[pos] in '─━':pos+=1
            while pos<len(normal) and normal[pos]==' ':pos+=1
            text=normal[pos:].rstrip()
            if not text:raise error(document,offset,'Empty tree node after box-drawing prefix')
            result.append(('    '*depth+text,offset));continue
        if re.fullmatch(r'[\s─━│┃└┗├┣]+',normal):continue
        if _BOX.search(normal):result.append((line,offset));continue
        if normal[:1].isspace():raise error(document,offset,'Mixed indentation in a box-drawing tree')
        result.append((line,offset))
    return result


def parse(document,config):
    from ...runtime.common import make_diagram,error,sanitize_text
    records=_records(document);nodes=[TreeNode(0,'/',-1,None,True)];stack=[nodes[0]];title='';acc_title='';acc_description='';started=False;i=0
    while i<len(records):
        line,offset=records[i];i+=1
        if not line.strip() or line.lstrip().startswith('%%'):continue
        if _META.match(line):
            if started:raise error(document,offset,'Tree metadata must precede the nodes')
            stripped=line.strip()
            if stripped.startswith('title'):title=stripped[5:].strip().split('%%',1)[0].rstrip()
            elif stripped.startswith('accTitle'):acc_title=stripped.split(':',1)[1].split('%%',1)[0].strip()
            elif '{' in stripped:
                parts=[stripped.split('{',1)[1]]
                while '}' not in parts[-1]:
                    if i==len(records):raise error(document,offset,'Unterminated accessibility description')
                    parts.append(records[i][0]);i+=1
                acc_description='\n'.join(parts).split('}',1)[0].strip()
            else:acc_description=stripped.split(':',1)[1].split('%%',1)[0].strip()
            continue
        started=True;level=len(line)-len(line.lstrip(' \t'));text=line[level:];name='';rest=''
        if text.startswith(('"',"'")):
            quote=text[0];end=text.find(quote,1)
            while end<0:
                if i==len(records):raise error(document,offset,'Unterminated tree node name')
                text+='\n'+records[i][0];i+=1;end=text.find(quote,1)
            name=text[1:end];rest=text[end+1:]
        else:
            annotation=re.search(r'[ \t]+(?::::[ \t]*[A-Za-z_]|icon\(|##)',text)
            name=text[:annotation.start()].rstrip(' \t') if annotation else text.rstrip(' \t');rest=text[annotation.start():] if annotation else ''
            if not name or name.startswith((':::','icon(','##')):raise error(document,offset+level,'Expected tree filename or directory')
        css_class='';icon=None;description=''
        while rest.strip():
            match=re.match(r'[ \t]+:::[ \t]*([A-Za-z_][\w-]*)',rest)
            if match:css_class=match[1];rest=rest[match.end():];continue
            match=re.match(r'[ \t]+icon\(([\w-]*(?::[\w-]+)?)\)',rest)
            if match:icon=match[1] or 'none';rest=rest[match.end():];continue
            match=re.match(r'[ \t]+##(.*)',rest,re.S)
            if match:description=sanitize_text(match[1].strip(),config);rest='';continue
            raise error(document,offset+level+len(text)-len(rest),'Invalid tree node annotation')
        while stack and level<=stack[-1].level:stack.pop()
        if not stack:raise error(document,offset,'Tree indentation has no parent')
        directory=name.endswith('/');node=TreeNode(len(nodes),name[:-1] if directory else name,level,stack[-1].id,directory,css_class,icon,description);nodes.append(node);stack.append(node)
    return make_diagram('treeView',document,config,TreeViewModel(tuple(nodes),title,acc_title,acc_description))


def _icon(node,config):
    def qualify(name):return name if ':' in name else ('mermaid-treeview:' if name in ('file','folder') or not config.get('defaultIconPack') else config['defaultIconPack']+':')+name
    if node.icon=='none':return None
    if node.icon:return qualify(node.icon)
    if not config.get('showIcons',False):return None
    if not node.directory:
        chosen=(config.get('filenameIcons') or {}).get(node.name)
        dot=node.name.rfind('.')
        if not chosen and dot>0:
            ext=node.name[dot:].lower();mapping=config.get('extensionIcons') or {};chosen=mapping.get(ext,mapping.get(ext[1:]))
        if chosen=='none':return None
        if chosen:return qualify(chosen)
    return 'mermaid-treeview:'+('folder' if node.directory else 'file')


async def build(diagram,painter):
    from ...runtime.common import config_dict
    from ...model.flowchart import Box
    model=diagram.model;config=config_dict(diagram);conf=config.get('treeView') or {};tv=(config.get('themeVariables') or {}).get('treeView') or {};px=number(conf.get('paddingX'),5);py=number(conf.get('paddingY'),5);indent=number(conf.get('rowIndent'),20);thickness=number(conf.get('lineThickness'),1);rows=[];boxes={};total_height=0.;total_width=0.;children={}
    for node in model.nodes:
        if node.parent is not None:children.setdefault(node.parent,[]).append(node.id)
    depths={0:0}
    for node in model.nodes:
        depth=0 if node.parent is None else depths[node.parent]+1;depths[node.id]=depth;x=depth*(indent+px);icon=_icon(node,conf);classes=('treeView-node-label',*(('treeView-node-dir',) if node.directory else ()),*node.css_class.split());s=painter.style(classes,tag='text',id=str(node.id),base={'font_size':painter.font_size(tv.get('labelFontSize','16px')),'text_color':tv.get('labelColor','black'),'font_weight':'bold' if node.directory else 'normal','white_space':'pre'});label=painter.measure(node.name,html=False,style=s);height=label.height+py*2;width=label.width+px*2+(18 if icon else 0);box=Box(x,total_height,width,height);boxes[node.id]=box;rows.append((node,box,label,s,icon,x+px+(18 if icon else 0),total_height+height/2));total_width=max(total_width,x+width);total_height+=height
    max_label_right=max((x+label.width for _,_,label,_,_,x,_ in rows),default=0);desc_x=max_label_right+16;descriptions={}
    for node,_,_,_,_,_,_ in rows:
        if node.description:
            s=painter.style(('treeView-node-description',),tag='text',id=str(node.id),base={'font_size':painter.font_size(tv.get('labelFontSize','16px')),'text_color':tv.get('descriptionColor','#6a9955'),'font_style':'italic','white_space':'pre'});label=painter.measure(node.description,html=False,style=s);descriptions[node.id]=(label,s);total_width=max(total_width,desc_x+label.width+px)
    # Source's third pass sizes each highlight against the current accumulated
    # width. Keep source order, including its small cumulative growth.
    highlight_widths={}
    for node,box,*_ in rows:
        if 'highlight' in node.css_class.split():highlight_widths[node.id]=total_width-box.x+8;total_width=max(total_width,box.x+highlight_widths[node.id]+2)
    line_style=painter.style(('treeView-node-line',),tag='line',base={'stroke':tv.get('lineColor','black'),'stroke_width':thickness,'fill':'none'})
    for node,box,label,s,icon,label_x,cy in rows:
        if node.id in highlight_widths:
            hs=painter.style(('treeView-highlight-bg',),id=str(node.id),base={'fill':tv.get('highlightBg','rgba(255, 193, 7, 0.15)'),'stroke':tv.get('highlightStroke','#ffc107'),'stroke_width':1.});painter.rect(box.x,box.y+1,highlight_widths[node.id],max(0,box.height-2),radius=3,style=hs,id=str(node.id),role='highlight')
        painter.line(box.x-indent,cy,box.x,cy,style=line_style,id=str(node.id),role='tree-branch')
        if children.get(node.id):
            end=boxes[children[node.id][-1]];painter.line(box.x+px,box.y+box.height,box.x+px,end.y+end.height/2+thickness/2,style=line_style,id=str(node.id),role='tree-trunk')
        if icon:
            color=tv.get('iconColor','#546e7a');x=box.x+px;y=box.y+py
            if icon in ('mermaid-treeview:file','mermaid-treeview:folder'):painter.svg(_FOLDER if icon.endswith(':folder') else _FILE,x,y,14,14,id=str(node.id),color=color)
            else:painter.asset(icon,x,y,14,14,kind='icon',id=str(node.id),color=color)
        painter.text(label,label_x,cy-label.height/2,style=s,id=str(node.id))
        if node.id in descriptions:
            desc,ds=descriptions[node.id];painter.text(desc,desc_x,cy-desc.height/2,style=ds,id=str(node.id),role='description')
    return painter.finish(width=total_width,height=total_height,padding=0,layout=('treeView-source-preorder',tuple(boxes.items())))
