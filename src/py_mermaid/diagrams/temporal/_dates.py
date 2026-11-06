"""Gantt calendar parsing/arithmetic and D3 calendar interval calculations."""
from datetime import datetime,timedelta
import calendar,math,re,bisect
from ._civil import date as calendar_date,timestamp as calendar_timestamp,CivilDate

MONTHS=('January','February','March','April','May','June','July','August','September','October','November','December')
DAYS=('monday','tuesday','wednesday','thursday','friday','saturday','sunday')
DATE_TOKENS=('YYYY','MMMM','MMM','SSS','YY','MM','DD','Do','HH','hh','mm','ss','ZZ','SS','M','D','H','h','m','s','S','A','a','Z','X','x')

def parse_date(value,format_,start=False):
    value=value.strip();format_=format_.strip()
    if format_ in ('x','X'):
        # Fixed source getStartDate treats both integer timestamp formats as
        # milliseconds. getEndDate uses Dayjs X seconds. Preserve that branch.
        if start and re.fullmatch(r'\d+',value):return calendar_timestamp(int(value)/1000)
        try:return calendar_timestamp(float(value)/(1000 if format_=='x' else 1))
        except (ValueError,OverflowError,OSError):return None
    if not format_:
        extended=re.fullmatch(r'([+-]\d{6}|0000|10000)(?:-(\d\d)(?:-(\d\d))?)?(?:T(\d\d):(\d\d)(?::(\d\d)(?:\.(\d{1,6}))?)?(Z|[+-]\d\d:\d\d)?)?',value)
        if extended:
            year=int(extended[1]);month=int(extended[2] or 1);day=int(extended[3] or 1)
            if not -10000<=year<=10000:return None
            try:
                result=calendar_date(year,month,day,int(extended[4] or 0),int(extended[5] or 0),int(extended[6] or 0),int((extended[7] or '').ljust(6,'0') or 0))
                zone=extended[8]
                if zone:
                    from ._civil import _local_offset
                    offset=0 if zone=='Z' else (1 if zone[0]=='+' else -1)*(int(zone[1:3])*3600+int(zone[4:])*60)
                    result+=timedelta(seconds=_local_offset()-offset)
                return result
            except ValueError:return None
        try:return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone().replace(tzinfo=None) if value.endswith('Z') or re.search(r'[+-]\d\d:\d\d$',value) else datetime.fromisoformat(value)
        except ValueError:return None
    parts=[];groups=[];i=0
    patterns={'YYYY':r'\d{4}','YY':r'\d{2}','M':r'\d{1,2}','MM':r'\d{2}','MMM':'|'.join(m[:3] for m in MONTHS),'MMMM':'|'.join(MONTHS),'D':r'\d{1,2}','DD':r'\d{2}','Do':r'\d{1,2}(?:st|nd|rd|th)','H':r'\d{1,2}','HH':r'\d{2}','h':r'\d{1,2}','hh':r'\d{2}','m':r'\d{1,2}','mm':r'\d{2}','s':r'\d{1,2}','ss':r'\d{2}','S':r'\d','SS':r'\d{2}','SSS':r'\d{3}','A':r'AM|PM','a':r'am|pm','Z':r'Z|[-+]\d\d:?\d\d','ZZ':r'Z|[-+]\d{4}'}
    while i<len(format_):
        if format_[i]=='[':
            end=format_.find(']',i+1)
            if end<0:return None
            parts.append(re.escape(format_[i+1:end]));i=end+1;continue
        token=next((t for t in DATE_TOKENS if format_.startswith(t,i)),None)
        if token and token in patterns:parts.append('('+patterns[token]+')');groups.append(token);i+=len(token)
        else:parts.append(re.escape(format_[i]));i+=1
    match=re.fullmatch(''.join(parts),value)
    if not match:return None
    now=datetime.now();year=now.year;month=1;day=1;hour=minute=second=micro=0;meridiem=None;zone=None
    for token,item in zip(groups,match.groups()):
        if token=='YYYY':year=int(item)
        elif token=='YY':year=int(item)+(1900 if int(item)>68 else 2000)
        elif token in ('M','MM'):month=int(item)
        elif token in ('MMM','MMMM'):month=next(i+1 for i,m in enumerate(MONTHS) if m==item or m[:3]==item)
        elif token in ('D','DD','Do'):day=int(re.match(r'\d+',item)[0])
        elif token in ('H','HH','h','hh'):hour=int(item)
        elif token in ('m','mm'):minute=int(item)
        elif token in ('s','ss'):second=int(item)
        elif token in ('S','SS','SSS'):micro=int(item)*10**(6-len(item))
        elif token in ('A','a'):meridiem=item.lower()
        elif token in ('Z','ZZ'):zone=item
    if meridiem:hour=hour%12+(12 if meridiem=='pm' else 0)
    try:
        result=calendar_date(year,month,day,hour,minute,second,micro)
        if zone:
            from datetime import timezone
            offset=0 if zone=='Z' else (1 if zone[0]=='+' else -1)*(int(zone[1:3])*60+int(zone[-2:]))
            if isinstance(result,CivilDate):
                from ._civil import _local_offset
                result+=timedelta(seconds=_local_offset()-offset*60)
            else:result=result.replace(tzinfo=timezone(timedelta(minutes=offset))).astimezone().replace(tzinfo=None)
        return result
    except ValueError:return None

def fallback_date(value):
    """ISO/RFC formats accepted by the source's explicit new Date fallback."""
    parsed=parse_date(value,'')
    if parsed is not None:return parsed
    from email.utils import parsedate_to_datetime
    try:return parsedate_to_datetime(value).astimezone().replace(tzinfo=None)
    except (ValueError,TypeError):return None

def duration(value):
    match=re.fullmatch(r'(\d+(?:\.\d+)?)([Mdhmswy]|ms)',value.strip())
    return (float(match[1]),match[2]) if match else None

def add(value,amount,unit):
    if unit in ('M','month','y','year'):
        months=math.trunc(amount*(12 if unit in ('y','year') else 1));total=value.year*12+value.month-1+months;year,month=divmod(total,12);month+=1
        return value.replace(year=year,month=month,day=min(value.day,calendar.monthrange(year,month)[1]))
    if unit in ('d','day','w','week'):
        days=math.floor(amount*(7 if unit in ('w','week') else 1)+.5)
        return value+timedelta(days=days)
    seconds={'h':3600,'hour':3600,'m':60,'minute':60,'s':1,'second':1,'ms':.001,'millisecond':.001}[unit]*amount
    return calendar_timestamp(value.timestamp()+seconds)

def format_day(value,pattern):
    ordinal=lambda n:str(n)+('th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th'))
    table={'YYYY':f'{value.year:04}','YY':f'{value.year%100:02}','MMMM':MONTHS[value.month-1],'MMM':MONTHS[value.month-1][:3],'MM':f'{value.month:02}','M':str(value.month),'DD':f'{value.day:02}','D':str(value.day),'Do':ordinal(value.day),'dddd':DAYS[value.weekday()],'ddd':DAYS[value.weekday()][:3],'HH':f'{value.hour:02}','H':str(value.hour),'hh':f'{value.hour%12 or 12:02}','h':str(value.hour%12 or 12),'mm':f'{value.minute:02}','m':str(value.minute),'ss':f'{value.second:02}','s':str(value.second),'SSS':f'{value.microsecond//1000:03}','A':'PM' if value.hour>=12 else 'AM','a':'pm' if value.hour>=12 else 'am','x':str(math.floor(value.timestamp()*1000)),'X':str(math.floor(value.timestamp())),'Q':str((value.month-1)//3+1)}
    tokens=sorted(table,key=len,reverse=True);out=[];i=0
    while i<len(pattern):
        if pattern[i]=='[':
            end=pattern.find(']',i+1)
            if end>=0:out.append(pattern[i+1:end]);i=end+1;continue
        token=next((t for t in tokens if pattern.startswith(t,i)),None)
        if token:out.append(table[token]);i+=len(token)
        else:out.append(pattern[i]);i+=1
    return ''.join(out)

def invalid(value,dateformat,excludes,includes,weekend='saturday'):
    formatted=format_day(value,dateformat);iso=value.strftime('%Y-%m-%d')
    if formatted in includes or iso in includes:return False
    start=4 if weekend=='friday' else 5
    return ('weekends' in excludes and value.weekday() in (start,start+1)) or DAYS[value.weekday()] in excludes or formatted in excludes or iso in excludes

def time_ticks(start,end,interval=None,weekday='sunday',count=10):
    """D3 time intervals; calendar boundary filtering, bounded at10k ticks."""
    if end<start:return time_ticks(end,start,interval,weekday,count)[::-1]
    if start==end:return (start,)
    options=[('millisecond',1,.001),('millisecond',5,.005),('millisecond',10,.01),('millisecond',50,.05),('millisecond',100,.1),('millisecond',500,.5),('second',1,1),('second',5,5),('second',15,15),('second',30,30),('minute',1,60),('minute',5,300),('minute',15,900),('minute',30,1800),('hour',1,3600),('hour',3,10800),('hour',6,21600),('hour',12,43200),('day',1,86400),('day',2,172800),('week',1,604800),('month',1,2592000),('month',3,7776000),('year',1,31536000)]
    match=re.fullmatch(r'([1-9]\d*)(millisecond|second|minute|hour|day|week|month)',interval or '')
    if match:
        step=int(match[1]);unit=match[2];seconds=next(s for u,n,s in options if u==unit and n==1)
        if (end-start).total_seconds()/seconds/step>10000:match=None
    if not match:
        target=(end-start).total_seconds()/count;i=bisect.bisect_right([s for u,n,s in options],target)
        selected=options[min(i,len(options)-1)]
        if 0<i<len(options) and target/options[i-1][2]<options[i][2]/target:selected=options[i-1]
        unit,step,seconds=selected
        if unit=='year' and target>seconds:
            from ..charts._scales import ticks
            years=ticks(start.year,end.year,count)
            return tuple(calendar_date(int(y),1,1) for y in years if start<=calendar_date(int(y),1,1)<=end)
    if unit=='millisecond':
        begin=math.ceil(start.timestamp()*1000/step)*step;finish=end.timestamp()*1000
        return tuple(calendar_timestamp(v/1000) for v in range(int(begin),int(finish)+1,step))
    if unit in ('second','minute','hour'):
        value=start.replace(microsecond=0)
        if unit in ('minute','hour'):value=value.replace(second=0)
        if unit=='hour':value=value.replace(minute=0)
    else:
        value=start.replace(hour=0,minute=0,second=0,microsecond=0)
        if unit=='week':value-=timedelta(days=(value.weekday()-DAYS.index(weekday))%7)
        elif unit=='month':value=value.replace(day=1)
        elif unit=='year':value=value.replace(month=1,day=1)
    result=[]
    while value<=end and len(result)<=10000:
        field=value.second if unit=='second' else value.minute if unit=='minute' else value.hour if unit=='hour' else value.day-1 if unit=='day' else value.month-1 if unit=='month' else value.year if unit=='year' else math.floor((value-calendar_date(1970,1,5)).days/7)
        if value>=start and field%step==0:result.append(value)
        value=add(value,1,unit)
    if len(result)>10000:raise ValueError('Time tick count exceeds10000')
    return tuple(result)

def axis_format(value,pattern):
    # D3-time-format differs from Dayjs: source axisFormat is strftime-like.
    replacements={'%L':f'{value.microsecond//1000:03}','%q':str((value.month-1)//3+1),'%Q':str(math.floor(value.timestamp()*1000)),'%s':str(math.floor(value.timestamp())),'%e':f'{value.day:2}','%-d':str(value.day),'%-m':str(value.month),'%-H':str(value.hour)}
    for key,text in replacements.items():pattern=pattern.replace(key,text)
    return value.strftime(pattern)
