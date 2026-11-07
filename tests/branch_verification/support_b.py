"""B branch inputs and native observation adapters; no imports execute product."""
from pathlib import Path
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[2]
REPO=ROOT
FIXTURES=Path(__file__).with_name('cases-B.json')
BASELINE='b605642cc285e95735f18d32f13ff8f98908bcae8e3fefb46120891edf42e268'


def build_fixture_document():
    """Mechanical P2 input construction only; never calls parse/layout."""
    cases=[];probes=[]
    def case(id,kind,text,config,path,symbol,features,labels):
        path='packages/mermaid/src/'+path;source=REPO/'.local/upstream-mermaid'/path
        content=source.read_bytes();lines=content.decode().splitlines()
        cases.append(dict(id='BV-B-'+id,kind=kind,source=text,config=config,
            origin=dict(path=path,symbol=symbol,line=next(i+1 for i,v in enumerate(lines) if symbol in v),sha256=hashlib.sha256(content).hexdigest(),synthesized=True),
            expect='render',features=features,expectedText=labels,expectedErrorCodes=[]))
    gantt=[('DATE-LOCALIZED','L','01/02/2024','%Y-%m-%d','Localized'),
           ('DATE-WEEKDAY','YYYY-MM-DD dddd','2024-01-01 Monday','%Y-%m-%d','Weekday'),
           ('DATE-ISOWEEK','YYYY-MM-DD [W]WW','2021-01-01 W53','%G-W%V','ISOWeek'),
           ('AXIS-LOCALE','YYYY-MM-DD','2021-01-01','%c | %x | %X','LocaleAxis'),
           ('AXIS-ESCAPE','YYYY-MM-DD','2024-01-01','%%Q %%L %%s','LiteralPercent'),
           ('TICKS-MONDAY','YYYY-MM-DD','2024-01-01','%Y-%m-%d','MondayPhase'),
           ('TICKS-CAP','YYYY-MM-DD','2024-01-01','%Y-%m-%d','BoundedTicks'),
           ('AXIS-FAR','YYYY-MM-DD','+010000-01-01','%Y | %G-W%V','FarYear')]
    for id,fmt,start,axis,label in gantt:
        interval='tickInterval 2week\nweekday monday\n' if id=='TICKS-MONDAY' else 'tickInterval 1millisecond\n' if id=='TICKS-CAP' else ''
        duration='31d' if id=='TICKS-MONDAY' else '2d'
        case(id,'gantt',f'gantt\ndateFormat {fmt}\naxisFormat {axis}\n{interval}todayMarker off\n{label} :a, {start}, {duration}\n',{'gantt':{'width':1200}},'diagrams/gantt/ganttRenderer.js','function makeGrid',['date-format','time-axis'],[label])
    git='commit id:"A" tag:"first" tag:"long-release" tag:"last"\nbranch dev\ncommit id:"B"\ncommit id:"C"\ncheckout main\ncommit id:"D"\ncherry-pick id:"B"\ncheckout dev\ncherry-pick id:"A"\ncheckout main\nmerge dev id:"M"\n'
    for direction in ('LR','TB','BT'):
        for rotate in (False,True):
            case('GIT-'+direction+('-ROTATE' if rotate else '-FLAT'),'gitGraph','gitGraph '+direction+':\n'+git,{'gitGraph':{'rotateCommitLabel':rotate,'parallelCommits':direction=='BT'}},'diagrams/git/gitGraphRenderer.ts','const drawArrow',['dense-routing','cherry-pick','tag-stack','rotation','direction'],['A','B','C','D','M','main','dev','first','long-release','last'])
    agents=[('AGENT-GENUINE','agentflow-beta TB\nflow Outer\n A --> A\nend\nOuter@{view:collapsed}\n',['Outer']),
        ('AGENT-INTERNAL','agentflow-beta TB\nflow Outer\n A --> B\nend\nOuter@{view:collapsed}\n',['Outer']),
        ('AGENT-NESTED','agentflow-beta LR\nflow Outer\n flow Inner\n  A --> B\n end\nend\nOuter@{view:collapsed}\nInner@{view:collapsed}\nX --> A\nB --> Y\n',['Outer','X','Y']),
        ('AGENT-ANCESTOR','agentflow-beta TB\nflow Outer\n flow Inner\n  A --> B\n end\nend\nOuter --> A\nB --> Inner\n',['Outer','Inner','A','B']),
        ('AGENT-GROUP-ALGO','agentflow-beta TB\nflow Outer@{algorithm:elk.box}\n A --> B\nend\n',['Outer','A','B']),
        ('AGENT-CROSS-ALGO','agentflow-beta LR\nflow Outer@{algorithm:elk.box}\n A --> B\nend\nX --> A\nB --> Y\n',['Outer','A','B','X','Y'])]
    for id,text,labels in agents:
        case(id,'agentflow',text,{},'diagrams/agentflow/agentflowDb.ts','public getData()',['compound-routing','collapsed-identity'],labels)
    for algorithm,body in [('force','A --> B\nB --> C\nC --> A\n'),('stress','A --> B\nC\n'),('box','A --> B\nC\n'),('rectpacking','A --> B\nC\n'),('force','A --> A\n'),('stress','A --> A\n')]:
        case('ENGINE-'+algorithm.upper()+('-COINCIDENT' if 'A --> A' in body else '-GRAPH'),'flowchart-v2','flowchart LR\n'+body,{'layout':'elk.'+algorithm},'rendering-util/layout-algorithms/elk/render.ts','async function runElkLayout',['actual-engine','no-fallback','nonrouting'],['A'] if 'A --> A' in body else ['A','B','C'])
    case('WARDLEY-ANNOTATION-PUSH','wardley','wardley-beta\ncomponent A [0.5, 0.5]\nannotations [0.7, 0.2]\nannotation 1, [0.2, 0.3] "First"\nannotation 1, [0.8, 0.7] "Second"\n',{},'diagrams/wardley/wardleyParser.ts','// Add individual annotations',['repeated-number-push','one-coordinate-per-grammar-record'],['A','First','Second'])
    def probe(id,kind,branch,**input):probes.append(dict(id='BV-B-P-'+id,kind=kind,branch=branch,input=input))
    for id,value,fmt in [('ISO','2024-02-29','YYYY-MM-DD'),('QUARTER','2024-Q2-01','YYYY-[Q]Q-DD'),('LOCAL-L','01/02/2024','L'),('LOCAL-LL','January 2, 2024','LL'),('LOCAL-LLL','January 2, 2024 1:04 PM','LLL'),('WEEKDAY','2024-01-01 Monday','YYYY-MM-DD dddd'),('ORDINAL','January 2nd 2024','MMMM Do YYYY'),('INVALID','2023-02-29','YYYY-MM-DD'),('MERIDIEM','2024-01-01 12:01 AM','YYYY-MM-DD hh:mm A')]:
        probe('PARSE-'+id,'parse','DATE-PARSE',value=value,format=fmt)
    for d in 'a A b B c d e f g G H I j L m M p q Q s S u U V w W x X y Y Z %'.split():
        probe('AXIS-'+('PERCENT' if d=='%' else 'LOWER-'+d if d.islower() else 'UPPER-'+d),'axis','AXIS-FORMAT',date=[2021,1,1,13,4,5,123],format='%'+d)
    for i,fmt in enumerate(['%-d','%_d','%0d','%-I','%%Q','%%L','%%s','%n']):
        probe('PAD-'+str(i),'axis','AXIS-PADDING',date=[2021,1,1,13,4,5,123],format=fmt)
    for y in (-1,0,10000):
        for fmt in ('%Y','%G-W%V','%U/%W'):
            probe('FAR-'+str(y).replace('-','NEG')+'-'+str(len(probes)),'axis','AXIS-FAR',date=[y,1,1,0,0,0,0],format=fmt)
    for fmt in ('Q','Do','dddd','ddd','W WW GGGG','k kk','w ww gggg z'):
        probe('DAYFORMAT-'+str(len(probes)),'dayFormat','DAYJS-ADVANCED',date=[2021,1,1,0,4,5,123],format=fmt,sourceMayThrow=fmt=='w ww gggg z')
    for weekday in ('monday','tuesday','wednesday','thursday','friday','saturday','sunday'):
        probe('WEEK-'+weekday.upper(),'ticks','TICK-WEEKDAY',start=[2024,1,1],end=[2024,2,1],interval='2week',weekday=weekday,count=10)
    for unit,step,start,end in [('millisecond',5,[2024,1,1,0,0,0,0],[2024,1,1,0,0,0,20]),('second',5,[2024,1,1],[2024,1,1,0,0,20]),('minute',5,[2024,1,1],[2024,1,1,0,20]),('hour',3,[2024,1,1],[2024,1,2]),('day',2,[2024,1,30],[2024,2,5]),('month',3,[2023,12,1],[2025,1,1])]:
        probe('UNIT-'+unit.upper(),'ticks','TICK-EXPLICIT',start=start,end=end,interval=str(step)+unit,weekday='sunday',count=10)
    for id,start,end,interval in [('SHORT',[2024,1,1],[2024,1,1,0,0,0,40],None),('YEARS',[1800,1,1],[2200,1,1],None),('CAP',[2024,1,1],[2024,1,3],'1millisecond'),('REVERSE',[2024,1,3],[2024,1,1],'1day'),('ZERO',[2024,1,1],[2024,1,1],None)]:
        probe('AUTO-'+id,'ticks','TICK-AUTO',start=start,end=end,interval=interval,weekday='sunday',count=10)
    for id,lanes in [('EMPTY',[]),('ONE',[50]),('DEPTH',[50,40,32,25.6,20.48,16.384])]:probe('LANE-'+id,'gitLane','GIT-LANES',a=0,b=100,lanes=lanes)
    for seed in (0,-1,2**32-1,1.25):probe('RANDOM-'+str(len(probes)),'random','NUMERIC-PRNG',seed=seed)
    return dict(schema='py-mermaid-bulk-cases/v1',group='B',cases=cases,pureProbes=probes,
                pureProbeContract='Separate exact-source helper observations; pure rows are never counted as rendered diagram fixtures.')


def document():return json.loads(FIXTURES.read_text(encoding='utf-8'))


def native_probe(probe):
    """Preserve actual return values/exceptions; never replace a failed call."""
    from py_mermaid.diagrams.temporal import _dates,_civil
    from py_mermaid.diagrams.business import _cynefin_geometry
    x=probe['input'];kind=probe['kind']
    def date(parts):
        if len(parts)==7:return _civil.date(*parts[:6],microsecond=parts[6]*1000)
        return _civil.date(*parts)
    def value(v):
        if v is None:return None
        # Evidence serialization is explicitly UTC, matching the follow-up
        # original-helper TZ=UTC. Do not call Windows CRT local timestamp():
        # IANA TZ strings may be interpreted as unrelated POSIX DST rules,
        # and pre-1970 timestamps can fail after the product already returned.
        year=v.year-(v.month<=2);era=year//400;yoe=year-era*400
        month=v.month+(-3 if v.month>2 else 9)
        doy=(153*month+2)//5+v.day-1
        days=era*146097+yoe*365+yoe//4-yoe//100+doy-719468
        epoch=((days*24+v.hour)*60+v.minute)*60000+v.second*1000+v.microsecond//1000
        return {'local':[v.year,v.month,v.day,v.hour,v.minute,v.second,v.microsecond//1000],'epochMs':epoch}
    try:
        if kind=='parse':result=value(_dates.parse_date(x['value'],x['format']))
        elif kind=='axis':result=_dates.axis_format(date(x['date']),x['format'])
        elif kind=='dayFormat':result=_dates.format_day(date(x['date']),x['format'])
        elif kind=='ticks':result=[value(v) for v in _dates.time_ticks(date(x['start']),date(x['end']),x['interval'],x['weekday'],x['count'])]
        elif kind=='random':result=_cynefin_geometry.random(x['seed'])
        elif kind=='gitLane':
            import re
            from types import SimpleNamespace
            from py_mermaid.diagrams.temporal._git_layout import edge_path
            a=SimpleNamespace(id='A',seq=0,branch='main',type='NORMAL',parents=())
            b=SimpleNamespace(id='B',seq=10,branch='dev',type='NORMAL',parents=('A',))
            middle=SimpleNamespace(id='I',seq=5,branch='dev',type='NORMAL',parents=('A',))
            path,_,_=edge_path(a,b,{'A':(0,x['a']),'B':(1000,x['b'])},[a,middle,b],'LR',list(x['lanes']))
            result=float(re.search(r'L0,([+\-.\deE]+)',path)[1])+10
        else:raise ValueError('Unknown pure probe '+kind)
        return dict(id=probe['id'],kind=kind,input=x,value=result,error=None)
    except Exception as exc:
        return dict(id=probe['id'],kind=kind,input=x,value=None,error={'name':type(exc).__name__,'message':str(exc)})


async def scene(case):
    from py_mermaid import parse
    from py_mermaid.runtime.registry import provider_for
    from py_mermaid.rendering.skia.scene import Painter
    diagram=parse(case['source'],config=case['config'])
    return diagram,await provider_for(diagram.kind).build(diagram,Painter(diagram,backend='cpu'))


def get_case(suffix):return next(c for c in document()['cases'] if c['id']=='BV-B-'+suffix)
