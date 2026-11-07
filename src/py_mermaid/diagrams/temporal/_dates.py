"""Gantt calendar parsing/arithmetic and D3 calendar interval calculations."""
from datetime import datetime,timedelta
import calendar,math,re,bisect
from ._civil import (date as calendar_date,timestamp as calendar_timestamp,CivilDate,
                     days_from_civil,civil_from_days,epoch_seconds,_local_offset)

MONTHS=('January','February','March','April','May','June','July','August','September','October','November','December')
DAYS=('monday','tuesday','wednesday','thursday','friday','saturday','sunday')
DATE_TOKENS=('YYYY','GGGG','MMMM','dddd','MMM','ddd','SSS','YY','WW','MM','DD','Do','dd','HH','hh','mm','ss','ZZ','SS','W','M','D','d','H','h','m','s','S','A','a','Z','X','x','Q')

def _iso_week(value):
    """ISO Thursday/week arithmetic, valid for every retained Gregorian year."""
    day=days_from_civil(value.year,value.month,value.day)
    thursday=day+3-value.weekday();year,_,_=civil_from_days(thursday)
    return year,(thursday-days_from_civil(year,1,1))//7+1

def _normalize(year,month,day,hour=0,minute=0,second=0,microsecond=0):
    year,month0=divmod(year*12+month-1,12)
    return calendar_date(year,month0+1,1)+timedelta(days=day-1,hours=hour,minutes=minute,seconds=second,microseconds=microsecond)

def parse_date(value,format_,start=False):
    value=value.strip();format_=format_.strip()
    if format_ in ('x','X'):
        # Fixed source getStartDate treats both integer timestamp formats as
        # milliseconds. getEndDate uses Dayjs X seconds. Preserve that branch.
        if start and re.fullmatch(r'\d+',value):return calendar_timestamp(int(value)/1000)
        try:return calendar_timestamp(float(value)/(1000 if format_=='x' else 1))
        except (ValueError,OverflowError,OSError):return None
    if not format_:
        extended=re.fullmatch(r'([+-]\d{6}|\d{4,5})(?:-(\d\d)(?:-(\d\d))?)?(?:[T ](\d\d):(\d\d)(?::(\d\d)(?:\.(\d{1,6}))?)?(Z|[+-]\d\d:\d\d)?)?',value)
        if extended:
            year=int(extended[1]);month=int(extended[2] or 1);day=int(extended[3] or 1)
            if not -10000<=year<=10000:return None
            try:
                hour,minute,second=int(extended[4] or 0),int(extended[5] or 0),int(extended[6] or 0)
                micro=int((extended[7] or '').ljust(6,'0') or 0)
                if not (1<=month<=12 and 1<=day<=31 and 0<=hour<=24 and 0<=minute<60 and 0<=second<60):return None
                if hour==24 and (minute or second or micro):return None
                result=_normalize(year,month,day,hour,minute,second,micro)
                zone=extended[8]
                if zone or extended[4] is None:
                    # ECMA date-only ISO strings are UTC; ISO date-times
                    # without a zone are local. Strict Dayjs is not this path.
                    offset=0 if zone in (None,'Z') else (1 if zone[0]=='+' else -1)*(int(zone[1:3])*3600+int(zone[4:])*60)
                    if zone is None:offset=0
                    elif zone!='Z' and (int(zone[1:3])>23 or int(zone[4:])>59):return None
                    result=calendar_timestamp(epoch_seconds(result)+_local_offset(result)-offset)
                return result
            except ValueError:return None
        return None
    parts=[];groups=[];i=0
    patterns={'YYYY':r'\d{4}','YY':r'\d{2}','M':r'\d{1,2}','MM':r'\d{2}','MMM':'|'.join(m[:3] for m in MONTHS),'MMMM':'|'.join(MONTHS),'D':r'\d{1,2}','DD':r'\d{2}','Do':r'\d{1,2}(?:st|nd|rd|th)','H':r'\d{1,2}','HH':r'\d{2}','h':r'\d{1,2}','hh':r'\d{2}','m':r'\d{1,2}','mm':r'\d{2}','s':r'\d{1,2}','ss':r'\d{2}','S':r'\d','SS':r'\d{2}','SSS':r'\d{3}','A':r'AM|PM','a':r'am|pm','Z':r'Z|[-+]\d\d:?\d\d','ZZ':r'Z|[-+]\d{4}'}
    # Dayjs customParseFormat consumes one digit for Q. Its strict
    # advancedFormat roundtrip rejects out-of-range quarters below.
    patterns['Q']=r'[0-9]'
    patterns.update({'dddd':'|'.join(day.title() for day in DAYS),
                     'ddd':'|'.join(day[:3].title() for day in DAYS),
                     'dd':'|'.join(day[:2].title() for day in DAYS),
                     'd':r'[0-6]','W':r'\d{1,2}','WW':r'\d{2}','GGGG':r'\d{4}'})
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
    now=datetime.now();has_year=any(t in groups for t in ('YYYY','YY'));has_month=any(t in groups for t in ('M','MM','MMM','MMMM','Q'))
    year=now.year;month=1 if has_year else now.month;day=1 if has_year or has_month else now.day
    hour=minute=second=micro=0;meridiem=None;zone=None;quarters=[]
    for token,item in zip(groups,match.groups()):
        if token=='YYYY':year=int(item)
        elif token=='YY':year=int(item)+(1900 if int(item)>68 else 2000)
        elif token in ('M','MM'):month=int(item)
        elif token=='Q':month=3*(int(item)-1)+1;quarters.append(int(item))
        elif token in ('MMM','MMMM'):month=next(i+1 for i,m in enumerate(MONTHS) if m==item or m[:3]==item)
        elif token in ('D','DD','Do'):day=int(re.match(r'\d+',item)[0])
        elif token in ('H','HH','h','hh'):hour=int(item)
        elif token in ('m','mm'):minute=int(item)
        elif token in ('s','ss'):second=int(item)
        elif token in ('S','SS','SSS'):micro=int(item)*10**(6-len(item))
        elif token in ('A','a'):meridiem=item.lower()
        elif token in ('Z','ZZ'):zone=item
    if any(q not in (1,2,3,4) or q!=(month-1)//3+1 for q in quarters):return None
    if meridiem:hour=hour%12+(12 if meridiem=='pm' else 0)
    try:
        result=calendar_date(year,month,day,hour,minute,second,micro)
        if zone:
            offset=0 if zone=='Z' else (1 if zone[0]=='+' else -1)*(int(zone[1:3])*60+int(zone[-2:]))
            result=calendar_timestamp(epoch_seconds(result)+_local_offset(result)-offset*60)
        # customParseFormat's strict mode validates by the unexpanded original
        # format string after parsing. In particular L/LL are not made valid by
        # silently installing localizedFormat; Gantt's browser-Date fallback
        # below is a separate source branch.
        return result if format_day(result,format_)==value else None
    except ValueError:return None

def fallback_date(value):
    """Fixed browser-Date string families used by Gantt's explicit fallback.

    Keep this independent of strict Dayjs token parsing. Slash numeric dates
    use the source browser's month/day/year interpretation, not OS locale.
    """
    parsed=parse_date(value,'')
    if parsed is not None:return parsed if -10000<=parsed.year<=10000 else None
    text=value.strip()
    match=re.fullmatch(r'(\d{1,2})[/-](\d{1,2})[/-](\d{1,6})(?:[ ,]+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*(AM|PM))?)?',text,re.I)
    if match:
        month,day,year=map(int,match.group(1,2,3));hour=int(match[4] or 0)
        if year<100:year+=1900 if year>=50 else 2000
        if match[7]:
            if not 1<=hour<=12:return None
            hour=hour%12+(12 if match[7].upper()=='PM' else 0)
        if year<=10000 and 1<=month<=12 and 1<=day<=31 and 0<=hour<24 and int(match[5] or 0)<60 and int(match[6] or 0)<60:
            return _normalize(year,month,day,hour,int(match[5] or 0),int(match[6] or 0))
        return None
    # English named months with optional ordinal-free comma, as accepted by
    # new Date and used when strict localized Dayjs forms fail their roundtrip.
    names='|'.join(MONTHS)+'|'+'|'.join(m[:3] for m in MONTHS)
    match=re.fullmatch(r'('+names+r')\s+(\d{1,2}),?\s+(\d{1,6})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?)?',text,re.I)
    if match:
        month=next(i+1 for i,m in enumerate(MONTHS) if match[1].lower() in (m.lower(),m[:3].lower()))
        year=int(match[3]);year=year+(1900 if year>=50 else 2000) if year<100 else year
        hour=int(match[4] or 0)
        if match[7]:
            if not 1<=hour<=12:return None
            hour=hour%12+(12 if match[7].upper()=='PM' else 0)
        if year<=10000 and 1<=int(match[2])<=31 and hour<24 and int(match[5] or 0)<60 and int(match[6] or 0)<60:
            return _normalize(year,month,int(match[2]),hour,int(match[5] or 0),int(match[6] or 0))
        return None
    from email.utils import parsedate_to_datetime
    try:
        parsed=parsedate_to_datetime(value)
        return calendar_timestamp(epoch_seconds(parsed)) if parsed.utcoffset() is not None else parsed
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
    return calendar_timestamp(epoch_seconds(value)+seconds)

def format_day(value,pattern):
    ordinal=lambda n:str(n)+('th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th'))
    iso_year,iso_week=_iso_week(value);offset=math.trunc(_local_offset(value)/60)
    zone=('+' if offset>=0 else '-')+f'{abs(offset)//60:02}:{abs(offset)%60:02}'
    table={'YYYY':str(value.year).rjust(4,'0'),'YY':str(value.year)[-2:],'MMMM':MONTHS[value.month-1],'MMM':MONTHS[value.month-1][:3],'MM':f'{value.month:02}','M':str(value.month),'DD':f'{value.day:02}','D':str(value.day),'Do':ordinal(value.day),'dddd':DAYS[value.weekday()].title(),'ddd':DAYS[value.weekday()][:3].title(),'dd':DAYS[value.weekday()][:2].title(),'d':str((value.weekday()+1)%7),'HH':f'{value.hour:02}','H':str(value.hour),'hh':f'{value.hour%12 or 12:02}','h':str(value.hour%12 or 12),'mm':f'{value.minute:02}','m':str(value.minute),'ss':f'{value.second:02}','s':str(value.second),'SSS':f'{value.microsecond//1000:03}','A':'PM' if value.hour>=12 else 'AM','a':'pm' if value.hour>=12 else 'am','x':str(math.floor(epoch_seconds(value)*1000)),'X':str(math.floor(epoch_seconds(value))),'Q':str((value.month-1)//3+1),'W':str(iso_week),'WW':f'{iso_week:02}','GGGG':str(iso_year),'k':str(value.hour or 24),'kk':f'{value.hour or 24:02}','Z':zone,'ZZ':zone.replace(':','')}
    unavailable=('gggg','zzz','wo','ww','w','z')
    tokens=sorted((*table,*unavailable),key=len,reverse=True);out=[];i=0
    while i<len(pattern):
        if pattern[i]=='[':
            end=pattern.find(']',i+1)
            if end>=0:out.append(pattern[i+1:end]);i=end+1;continue
        token=next((t for t in tokens if pattern.startswith(t,i)),None)
        if token:
            if token in unavailable:
                # Fixed bundle installs advancedFormat+isoWeek, but not
                # weekOfYear/weekYear/timezone. Do not fabricate a value for
                # source plugin methods which throw when actually requested.
                raise ValueError('Dayjs format requires an unavailable source plugin: '+token)
            out.append(table[token]);i+=len(token)
        else:out.append(pattern[i]);i+=1
    return ''.join(out)

def invalid(value,dateformat,excludes,includes,weekend='saturday'):
    formatted=format_day(value,dateformat);iso=value.strftime('%Y-%m-%d')
    if formatted in includes or iso in includes:return False
    start=4 if weekend=='friday' else 5
    return ('weekends' in excludes and value.weekday() in (start,start+1)) or DAYS[value.weekday()] in excludes or formatted in excludes or iso in excludes

def time_ticks(start,end,interval=None,weekday='sunday',count=10):
    """D3 time intervals; calendar boundary filtering, bounded at10k ticks."""
    start_epoch,end_epoch=epoch_seconds(start),epoch_seconds(end)
    # Gantt rejects explicit intervals for a reversed domain (its estimate is
    # Infinity), then D3's automatic ticker handles reversal.
    if end_epoch<start_epoch:return time_ticks(end,start,None,weekday,count)[::-1]
    if start_epoch==end_epoch:return (start,)
    if not isinstance(count,(int,float)) or not math.isfinite(count) or count<=0:return ()
    options=[('millisecond',1,.001),('millisecond',5,.005),('millisecond',10,.01),('millisecond',50,.05),('millisecond',100,.1),('millisecond',500,.5),('second',1,1),('second',5,5),('second',15,15),('second',30,30),('minute',1,60),('minute',5,300),('minute',15,900),('minute',30,1800),('hour',1,3600),('hour',3,10800),('hour',6,21600),('hour',12,43200),('day',1,86400),('day',2,172800),('week',1,604800),('month',1,2592000),('month',3,7776000),('year',1,31536000)]
    match=re.fullmatch(r'([1-9]\d*)(millisecond|second|minute|hour|day|week|month)',interval or '')
    if match:
        step=int(match[1]);unit=match[2];seconds=next(s for u,n,s in options if u==unit and n==1)
        # Dayjs.duration uses 365days/12 for a month in the source safety
        # estimate, while D3's automatic interval heuristic uses30days.
        estimate=2628000 if unit=='month' else seconds
        if (end_epoch-start_epoch)/estimate/step>10000:match=None
    if not match:
        from ..charts._scales import tick_increment
        def tick_step(a,b):
            inc=tick_increment(a,b,count)
            return inc if inc>0 else 1/-inc
        intervals=[item for item in options if item[0]!='millisecond']
        target=(end_epoch-start_epoch)/count;i=bisect.bisect_right([s for u,n,s in intervals],target)
        if i==0:
            unit,step,seconds='millisecond',max(1,math.floor(tick_step(start_epoch*1000,end_epoch*1000))),.001
        elif i==len(intervals):
            unit,step,seconds='year',max(1,math.floor(tick_step(start_epoch/31536000,end_epoch/31536000))),31536000
        else:
            unit,step,seconds=intervals[i-1 if target/intervals[i-1][2]<intervals[i][2]/target else i]
    if unit=='millisecond':
        begin=math.ceil(epoch_seconds(start)*1000/step)*step;finish=epoch_seconds(end)*1000
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
    week_origin=0
    if unit=='week':
        epoch_local=calendar_timestamp(0)
        epoch_day=days_from_civil(epoch_local.year,epoch_local.month,epoch_local.day)
        week_origin=epoch_day-(epoch_local.weekday()-DAYS.index(weekday))%7
    result=[]
    while epoch_seconds(value)<=end_epoch:
        # interval.every(k) for weekdays counts from floor(Date(0)) using
        # that same weekday, not one shared Monday epoch for all weekdays.
        field=value.second if unit=='second' else value.minute if unit=='minute' else value.hour if unit=='hour' else value.day-1 if unit=='day' else value.month-1 if unit=='month' else value.year if unit=='year' else (days_from_civil(value.year,value.month,value.day)-week_origin)//7
        if epoch_seconds(value)>=start_epoch and field%step==0:result.append(value)
        value=add(value,1,unit)
    return tuple(result)

def axis_format(value,pattern):
    """D3-time-format 4.1 defaultLocale/newFormat, independent of OS strftime.

    Percent dispatch is scanned once: escaped %%Q never becomes a timestamp,
    padding modifiers are per-directive, unknown directives emit their letter.
    Calendar/ISO arithmetic works for year0 and negative/extended years.
    """
    def pad(number,fill,width):
        sign='-' if number<0 else '';digits=str(abs(number))
        return sign+fill*max(0,width-len(digits))+digits
    def remainder(number,divisor):return number-math.trunc(number/divisor)*divisor
    iso_year,iso_week=_iso_week(value);weekday=(value.weekday()+1)%7
    doy=days_from_civil(value.year,value.month,value.day)-days_from_civil(value.year,1,1)+1
    numeric={'d':(value.day,2),'e':(value.day,2),'f':((value.microsecond//1000)*1000,6),
        'g':(remainder(iso_year,100),2),'G':(remainder(iso_year,10000),4),
        'H':(value.hour,2),'I':(value.hour%12 or 12,2),'j':(doy,3),'L':(value.microsecond//1000,3),
        'm':(value.month,2),'M':(value.minute,2),'S':(value.second,2),
        'U':((doy+6-weekday)//7,2),'W':((doy+6-value.weekday())//7,2),'V':(iso_week,2),
        'y':(remainder(value.year,100),2),'Y':(remainder(value.year,10000),4)}
    zone=math.trunc(_local_offset(value)/60)
    text={'a':DAYS[value.weekday()][:3].title(),'A':DAYS[value.weekday()].title(),
        'b':MONTHS[value.month-1][:3],'B':MONTHS[value.month-1],'p':'PM' if value.hour>=12 else 'AM',
        'q':str((value.month-1)//3+1),'Q':str(math.floor(epoch_seconds(value)*1000)),
        's':str(math.floor(epoch_seconds(value))),'u':str(value.weekday()+1),'w':str(weekday),
        'Z':('+' if zone>=0 else '-')+f'{abs(zone)//60:02}{abs(zone)%60:02}','%':'%'}
    composites={'c':'%x, %X','x':'%-m/%-d/%Y','X':'%-I:%M:%S %p'}
    out=[];i=0
    while i<len(pattern):
        if pattern[i]!='%':out.append(pattern[i]);i+=1;continue
        i+=1
        if i==len(pattern):break
        directive=pattern[i];fill=' ' if directive=='e' else '0'
        if directive in '-_0':
            fill={'-':'','_':' ','0':'0'}[directive];i+=1
            if i==len(pattern):break
            directive=pattern[i]
        if directive in numeric:
            number,width=numeric[directive]
            # D3 %f pads milliseconds to3 then appends exactly000.
            result=pad(value.microsecond//1000,fill,3)+'000' if directive=='f' else pad(number,fill,width)
        elif directive in composites:result=axis_format(value,composites[directive])
        else:result=text.get(directive,directive)
        out.append(result);i+=1
    return ''.join(out)
