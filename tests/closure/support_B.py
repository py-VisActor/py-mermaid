"""Portable closure observations; imports alone never execute products.

Tests use installed py_mermaid and this tracked JSON only. Source-only Node
and bundled-browser observations belong to the separate P3 oracle command.
"""
from datetime import datetime,timedelta,tzinfo
from pathlib import Path
from unittest.mock import patch
import copy
import json
import os
import time

FIXTURE=Path(__file__).with_name('cases-B.json')

def document():return json.loads(FIXTURE.read_text(encoding='utf8'))

def case(identifier):return next(c for c in document()['cases'] if c['id']==identifier)

def serialize(value):
    if value is None:return None
    from py_mermaid.diagrams.temporal._civil import epoch_seconds
    return {'local':[value.year,value.month,value.day,value.hour,value.minute,value.second,value.microsecond//1000],
            'epochMs':round(epoch_seconds(value)*1000)}

def date(parts):
    from py_mermaid.diagrams.temporal._civil import date as civil
    return civil(*parts[:6],microsecond=parts[6]*1000) if len(parts)==7 else civil(*parts)

def native_value(row):
    from py_mermaid.diagrams.temporal import _dates
    x=row['input'];kind=row['kind']
    if kind=='parse':return serialize(_dates.parse_date(x['value'],x['format']))
    if kind=='axis':return _dates.axis_format(date(x['date']),x['format'])
    if kind=='dayFormat':return _dates.format_day(date(x['date']),x['format'])
    if kind=='ticks':return [serialize(v) for v in _dates.time_ticks(date(x['start']),date(x['end']),x['interval'],x['weekday'],x['count'])]
    if kind=='random':
        from py_mermaid.diagrams.business._cynefin_geometry import random
        return random(x['seed'])
    if kind=='gitLane':
        from types import SimpleNamespace
        import re
        from py_mermaid.diagrams.temporal._git_layout import edge_path
        a=SimpleNamespace(id='A',seq=0,branch='main',type='NORMAL',parents=())
        b=SimpleNamespace(id='B',seq=10,branch='dev',type='NORMAL',parents=('A',))
        middle=SimpleNamespace(id='I',seq=5,branch='dev',type='NORMAL',parents=('A',))
        route,_,_=edge_path(a,b,{'A':(0,x['a']),'B':(1000,x['b'])},[a,middle,b],'LR',list(x['lanes']))
        return float(re.search(r'L0,([+\-.\deE]+)',route)[1])+10
    raise ValueError('Unknown numerical observation '+kind)

class NewYork2024(tzinfo):
    """Literal source-independent2024 transition instants, not an IANA shim.

    Used only as an explicit aware input and inverse host-conversion seam for
    a pure arithmetic test. Linux public Gantt uses real TZ rules separately.
    """
    def utcoffset(self,value):
        wall=value.replace(tzinfo=None)
        return timedelta(hours=-4 if datetime(2024,3,10,2)<=wall<datetime(2024,11,3,2) else -5)
    def dst(self,value):return self.utcoffset(value)-timedelta(hours=-5)
    def fromutc(self,value):
        utc=value.replace(tzinfo=None)
        offset=-4 if datetime(2024,3,10,7)<=utc<datetime(2024,11,3,6) else -5
        return (utc+timedelta(hours=offset)).replace(tzinfo=self)

def native_extra(row):
    from py_mermaid.diagrams.temporal import _dates
    if row['kind']=='browserFallback':return serialize(_dates.fallback_date(row['input']['value']))
    if row['kind']=='dayAdd':
        zone=NewYork2024();base=datetime(*row['input']['date'],tzinfo=zone)
        with patch.object(_dates,'calendar_timestamp',side_effect=lambda t:datetime.fromtimestamp(t,zone)):
            calendar=_dates.add(base,1,'day');elapsed=_dates.add(base,24,'hour')
        return {'base':serialize(base),'calendar':serialize(calendar),'elapsed':serialize(elapsed),
                'calendarHours':(calendar.timestamp()-base.timestamp())/3600,
                'calendarLocalHour':calendar.hour,'elapsedLocalHour':elapsed.hour}
    raise ValueError('Unknown extra observation '+row['kind'])

async def graph_scene(row):
    from py_mermaid import parse
    from py_mermaid.runtime.registry import provider_for
    from py_mermaid.rendering.skia.scene import Painter
    d=parse(row['source'],config=row.get('config',{}))
    return d,await provider_for(d.kind).build(d,Painter(d,backend='cpu'))

async def layout_observation(row):
    """Observe raw real-engine requests/results, never synthesize geometry."""
    from pyelk import ELK
    inputs=[];outputs=[];original=ELK.layout
    async def capture(engine,graph,args=None):
        inputs.append(copy.deepcopy(graph));result=await original(engine,graph,args)
        outputs.append(copy.deepcopy(result));return result
    with patch.object(ELK,'layout',capture):diagram,scene=await graph_scene(row)
    result={'id':row['id'],'source':row['source'],'config':row.get('config',{}),
            'rawInputs':inputs,'rawOutputs':outputs,'status':'OBSERVED','error':None}
    if diagram.kind=='agentflow':
        graph=diagram.model.graph
        result['nodes']=[n.id for n in graph.nodes];result['groups']=[g.id for g in graph.groups]
        result['edges']=[{'id':e.id,'source':e.source,'target':e.target} for e in graph.edges]
        result['engine']=scene.layout.engine;result['routedEdges']=[e.id for e in scene.layout.edges]
    else:
        result['layout']=scene.layout
        if diagram.kind=='gantt':
            from py_mermaid.diagrams.temporal.gantt import compile_tasks
            tasks,_=compile_tasks(diagram.model,diagram.source)
            result['taskDates']=[{'id':task.id,'start':serialize(start),'end':serialize(end)} for task,start,end,_ in tasks]
        result['labels']=[{'id':p.semantic_id,'kind':p.kind,'values':
            {'text':p.values[0].text,'width':p.values[0].width,'height':p.values[0].height,
             'x':p.values[1],'y':p.values[2],'rotation':p.values[3]} if p.kind=='text' else None}
            for p in scene.commands if p.kind=='text' or 'branch-label-bg-' in p.semantic_id]
        result['commands']=[{'id':p.semantic_id,'kind':p.kind,'role':p.role,
                            'values':list(p.values),'bounds':[p.bounds.x,p.bounds.y,p.bounds.width,p.bounds.height] if p.bounds else None}
                            for p in scene.commands if p.kind=='path']
    return result

def raw_nodes(raw):
    yield raw
    for child in raw.get('children',[]):yield from raw_nodes(child)

def set_timezone(value):
    os.environ['TZ']=value
    if hasattr(time,'tzset'):time.tzset()
    return {'requested':value,'realTzset':hasattr(time,'tzset'),
            'utcPortable':value.upper() in ('UTC','ETC/UTC','UTC0','GMT'),
            'hostOffsetSeconds':datetime.now().astimezone().utcoffset().total_seconds()}
