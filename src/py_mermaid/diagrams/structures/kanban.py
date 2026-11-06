"""Kanban Jison metadata, sections and its dedicated measured column layout."""
from __future__ import annotations
from dataclasses import dataclass,replace
import re
from ...runtime.common import make_diagram,error,config_dict,sanitize_text
from ...parsing.yaml_json import load_yaml_json
from ..hierarchy.mindmap import _records
from ..modeling._support import number


@dataclass(frozen=True)
class KanbanNode:
    id:str
    label:str
    level:int
    parent:str|None
    ticket:str=''
    assigned:str=''
    priority:str=''
    icon:str=''
    classes:tuple[str,...]=()


@dataclass(frozen=True)
class KanbanModel:
    nodes:tuple[KanbanNode,...]
    sections:tuple[str,...]


def _rows(text):
    # shapeData can contain block YAML; its quotes consume literal newlines.
    pending='';start=0;offset=0;level=0;quote=None
    for line in text.splitlines(keepends=True):
        if not pending:start=offset
        pending+=line;offset+=len(line);i=0;quote=None;level=0
        while i<len(pending):
            c=pending[i]
            if quote:
                if c==quote:quote=None
            elif c in ('"',"'"):quote=c
            elif pending.startswith('@{',i):level+=1;i+=1
            elif c=='}' and level:level-=1
            i+=1
        if not quote and not level:yield start,pending.rstrip('\r\n');pending=''
    if pending:yield start,pending


def parse(document,config):
    nodes=[];sections=[];header=False;cnt=0;section_level=None
    for offset,line in _rows(document.cleaned):
        if not line.strip() or line.lstrip().startswith('%%'):continue
        if not header:
            m=re.match(r'\s*kanban\b',line,re.I)
            if not m:raise error(document,offset,'Expected kanban header')
            header=True;offset+=m.end();line=line[m.end():]
            if not line.strip():continue
        level=len(line)-len(line.lstrip());body=line[level:]
        if body.startswith(':::') or body.startswith('::icon('):
            if not nodes:raise error(document,offset,'Decoration has no Kanban node','UNKNOWN_REFERENCE')
            if body.startswith(':::'):nodes[-1]=replace(nodes[-1],classes=(sanitize_text(body[3:],config),))
            else:
                m=re.fullmatch(r'::icon\(([^)]+)\)\s*',body)
                if not m:raise error(document,offset,'Invalid icon decoration')
                nodes[-1]=replace(nodes[-1],icon=sanitize_text(m[1],config))
            continue
        metadata={};at=body.find('@{')
        if at>=0:
            raw=body[at+2:]
            if not raw.endswith('}'):raise error(document,offset+at,'Unterminated Kanban metadata')
            raw=raw[:-1];raw=re.sub(r'"[^"]*"',lambda m:re.sub(r'\n\s*','<br/>',m[0]),raw)
            metadata=load_yaml_json('{\n'+raw+'\n}' if '\n' not in raw else raw+'\n');body=body[:at]
            if not isinstance(metadata,dict):raise error(document,offset+at,'Kanban metadata must be a mapping','INVALID_METADATA')
            shape=metadata.get('shape')
            if shape and (not isinstance(shape,str) or shape!=shape.lower() or '_' in shape):raise error(document,offset+at,'Shape names should be lowercase','INVALID_SHAPE')
        node_id=label=body;start=re.search(r'-\)|\(-|\)\)|\(\(|\{\{|[\[(\)]',body)
        if start:
            node_id=body[:start.start()];tail=body[start.end():]
            if tail.startswith('"`'):
                end=tail.find('`"',2);label=tail[2:end];closing=tail[end+2:] if end>=0 else ''
            elif tail.startswith('"'):
                end=tail.find('"',1);label=tail[1:end];closing=tail[end+1:] if end>=0 else ''
            else:
                m=re.fullmatch(r'([\s\S]+?)(\)\)|\}\}|\(-|-\)|\(\(|[\])\(])\s*',tail)
                if not m:raise error(document,offset,'Unterminated Kanban node')
                label=m[1];closing=m[2]
            if not re.fullmatch(r'(?:\)\)|\}\}|\(-|-\)|\(\(|[\])\(])\s*',closing):raise error(document,offset,'Invalid Kanban closing delimiter')
            if not node_id:node_id=label
        elif any(c in body for c in '{}]@'):raise error(document,offset,'Invalid Kanban node')
        if section_level is None:section_level=level
        # getSection scans existing DB nodes before adding the current one.
        # A first outdented item is retained; the next add exposes that anomaly.
        if any(node.level<section_level for node in nodes):raise error(document,offset,'Items without section detected','INVALID_SECTION')
        parent=None if level==section_level else sections[-1]
        node_id=sanitize_text(node_id,config)
        if not node_id:node_id='kbn'+str(cnt);cnt+=1
        node=KanbanNode(node_id,metadata.get('label') or sanitize_text(label,config),level,parent,str(metadata.get('ticket') or ''),str(metadata.get('assigned') or ''),str(metadata.get('priority') or ''),str(metadata.get('icon') or ''))
        nodes.append(node)
        if parent is None:sections.append(node_id)
    if not header or not nodes:raise error(document,len(document.cleaned),'Kanban requires a section')
    return make_diagram('kanban',document,config,KanbanModel(tuple(nodes),tuple(sections)))


async def build(diagram,painter):
    from ...config.colors import lighten,darken
    config=config_dict(diagram);tv=config.get('themeVariables') or {};conf=config.get('kanban') or {};width=number(conf.get('sectionWidth'),200) or 200;padding=10.;sections=[n for n in diagram.model.nodes if n.parent is None];labels={};max_label_height=25.;painter.rough_enabled=True
    for section in sections:
        s=painter.style(('cluster-label','label'),tag='text',base={'text_color':tv.get('textColor','#333')});label=painter.measure(section.label,label_kind='markdown',html=False,width=width-20,style=s);labels[section.id]=(s,label);max_label_height=max(max_label_height,label.height)
    layout=[]
    for index,section in enumerate(sections,1):
        cx=width*index+(index-1)*padding/2;x=cx-width/2;top=-width*3/2+max_label_height;y=top;items=[]
        for node in diagram.model.nodes:
            if node.parent!=section.id:continue
            s=painter.style(('node','kanbanItem'),id=node.id,base={'fill':tv.get('background','#fff'),'stroke':tv.get('nodeBorder','#333'),'stroke_width':1,'text_color':tv.get('textColor','#333')})
            iw=width-15;label=painter.measure(node.label,html=False,label_kind='markdown',width=iw-10,style=s);ticket=painter.measure(node.ticket,html=False,width=iw-10,style=replace(s,decoration='underline') if conf.get('ticketBaseUrl') and node.ticket else s);assigned=painter.measure(node.assigned,html=False,width=iw-10,style=s);adj=max(ticket.height,assigned.height)/2;h=label.height+20+adj;items.append((node,s,label,ticket,assigned,x+7.5,y,iw,h,adj));y+=h+padding/2
        height=width*3 if config.get('look')=='handDrawn' else max(y-top+3*padding,50)+(max_label_height-25);i=index+1;color=tv.get('cScale'+str(i),'#ececff');color=(darken if tv.get('darkMode') else lighten)(color,10)
        hand_drawn=config.get('look')=='handDrawn'
        group=painter.style(('cluster','section-'+str(index)),tag='g',id=section.id,base={'fill':color,'stroke':color,'text_color':tv.get('cScaleLabel'+str(i),'#333'),'stroke_width':1.3 if hand_drawn else 1})
        s=painter.style((),tag='path' if hand_drawn else 'rect',base=group,inherited=group,ancestors=group.paint_context);sy=-width*3/2
        painter.rough_enabled=hand_drawn
        if hand_drawn:
            # clusters.js creates a path at WIDTH*3; later select('rect') height
            # updates cannot resize it. Its dense, weight-4 hachure is recolored
            # by .section-N path background/border CSS, not default thin hachure.
            r=5;d=f'M{x+r},{sy}H{x+width-r}Q{x+width},{sy} {x+width},{sy+r}V{sy+height-r}Q{x+width},{sy+height} {x+width-r},{sy+height}H{x+r}Q{x},{sy+height} {x},{sy+height-r}V{sy+r}Q{x},{sy} {x+r},{sy}Z'
            painter.path(d,style=s,id=section.id,role='kanban-section',rough_options={'roughness':.7,'fillWeight':4,'hachureGap':1.5,'fillStyle':'hachure','seed':config.get('handDrawnSeed',0)})
        else:painter.rect(x,sy,width,height,style=s,radius=5,id=section.id,role='kanban-section')
        ls,label=labels[section.id];painter.text(label,cx-label.width/2,sy+5,style=ls,id=section.id)
        layout.append((section.id,x,sy,width,height))
        for node,s,label,ticket,assigned,ix,iy,iw,h,adj in items:
            # getData supplies look to sections only. Item nodes have no look,
            # so kanbanItem.ts takes its crisp branch even on a handDrawn diagram.
            painter.rough_enabled=False
            painter.rect(ix,iy,iw,h,style=s,radius=5,id=node.id,role='kanban-item');painter.text(label,ix+10,iy+h/2-adj-label.height/2,style=s,id=node.id)
            ly=iy+h/2-adj+label.height/2;painter.text(ticket,ix+10,ly,style=s,id=node.id,role='ticket');painter.text(assigned,ix+iw-assigned.width-10,ly,style=s,id=node.id,role='assigned')
            color={'Very High':'red','High':'orange','Low':'blue','Very Low':'lightblue'}.get(node.priority)
            if node.priority and color:painter.line(ix+2,iy,ix+2,iy+h,stroke=color,line_width=4,id=node.id,role='priority')
            layout.append((node.id,ix,iy,iw,h))
    return painter.finish(layout=('kanban-measured-columns',tuple(layout)),padding=number((config.get('mindmap') or {}).get('padding'),number(conf.get('padding'),10)))
