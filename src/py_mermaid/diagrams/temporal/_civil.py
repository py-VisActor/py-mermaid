"""Proleptic Gregorian value dates for the source Gantt [-10000,10000] range.

Python's datetime stops at year 1/9999; JavaScript Date does not. Ordinary
dates stay datetime values (and retain host DST arithmetic); only extended
years use these integer calendar values. No alternate layout algorithm.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta
from functools import total_ordering
import calendar,math

def days_from_civil(year,month,day):
    year-=month<=2;era=year//400;yoe=year-era*400;mp=month+(-3 if month>2 else 9);doy=(153*mp+2)//5+day-1;doe=yoe*365+yoe//4-yoe//100+doy
    return era*146097+doe-719468

def civil_from_days(days):
    days+=719468;era=days//146097;doe=days-era*146097;yoe=(doe-doe//1460+doe//36524-doe//146096)//365;year=yoe+era*400;doy=doe-(365*yoe+yoe//4-yoe//100);mp=(5*doy+2)//153;day=doy-(153*mp+2)//5+1;month=mp+(3 if mp<10 else -9);year+=month<=2
    return year,month,day

def _local_offset():return datetime.now().astimezone().utcoffset().total_seconds()

def _microseconds(value):
    return (days_from_civil(value.year,value.month,value.day)*86400+value.hour*3600+value.minute*60+value.second)*1000000+value.microsecond

@total_ordering
@dataclass(frozen=True,eq=False)
class CivilDate:
    year:int
    month:int=1
    day:int=1
    hour:int=0
    minute:int=0
    second:int=0
    microsecond:int=0
    def __post_init__(self):
        if not 1<=self.month<=12 or not 1<=self.day<=calendar.monthrange(self.year,self.month)[1] or not 0<=self.hour<24 or not 0<=self.minute<60 or not 0<=self.second<60 or not 0<=self.microsecond<1000000:raise ValueError('Invalid calendar date')
    def __eq__(self,other):return _microseconds(self)==_microseconds(other) if isinstance(other,(CivilDate,datetime)) else NotImplemented
    def __lt__(self,other):return _microseconds(self)<_microseconds(other) if isinstance(other,(CivilDate,datetime)) else NotImplemented
    def __hash__(self):return hash(_microseconds(self))
    def __add__(self,delta):
        if not isinstance(delta,timedelta):return NotImplemented
        return from_microseconds(_microseconds(self)+round(delta.total_seconds()*1000000))
    __radd__=__add__
    def __sub__(self,other):
        if isinstance(other,timedelta):return self+-other
        if isinstance(other,(CivilDate,datetime)):return timedelta(microseconds=_microseconds(self)-_microseconds(other))
        return NotImplemented
    def __rsub__(self,other):
        if isinstance(other,datetime):return timedelta(microseconds=_microseconds(other)-_microseconds(self))
        return NotImplemented
    def replace(self,**values):return date(**{key:values.get(key,getattr(self,key)) for key in ('year','month','day','hour','minute','second','microsecond')})
    def timestamp(self):return _microseconds(self)/1000000-_local_offset()
    def weekday(self):return (days_from_civil(self.year,self.month,self.day)+3)%7
    def isoformat(self):return f'{self.year:04}-{self.month:02}-{self.day:02}T{self.hour:02}:{self.minute:02}:{self.second:02}'+(f'.{self.microsecond:06}' if self.microsecond else '')
    def strftime(self,pattern):
        months=('January','February','March','April','May','June','July','August','September','October','November','December');days=('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday');year=self.year
        table={'Y':f'{year:04}','y':f'{year%100:02}','m':f'{self.month:02}','d':f'{self.day:02}','H':f'{self.hour:02}','I':f'{self.hour%12 or 12:02}','M':f'{self.minute:02}','S':f'{self.second:02}','f':f'{self.microsecond:06}','p':'PM' if self.hour>=12 else 'AM','B':months[self.month-1],'b':months[self.month-1][:3],'A':days[self.weekday()],'a':days[self.weekday()][:3],'w':str((self.weekday()+1)%7),'u':str(self.weekday()+1),'j':f'{days_from_civil(year,self.month,self.day)-days_from_civil(year,1,1)+1:03}','%':'%'}
        out=[];i=0
        while i<len(pattern):
            if pattern[i]=='%' and i+1<len(pattern):out.append(table.get(pattern[i+1],'%'+pattern[i+1]));i+=2
            else:out.append(pattern[i]);i+=1
        return ''.join(out)

def date(year,month=1,day=1,hour=0,minute=0,second=0,microsecond=0):
    constructor=datetime if 1<=year<=9999 else CivilDate
    return constructor(year,month,day,hour,minute,second,microsecond)

def from_microseconds(value):
    days,within=divmod(value,86400*1000000);year,month,day=civil_from_days(days);hour,within=divmod(within,3600*1000000);minute,within=divmod(within,60*1000000);second,micro=divmod(within,1000000)
    return date(year,month,day,hour,minute,second,micro)

def timestamp(seconds):
    try:return datetime.fromtimestamp(seconds)
    except (ValueError,OverflowError,OSError):return from_microseconds(round((seconds+_local_offset())*1000000))
