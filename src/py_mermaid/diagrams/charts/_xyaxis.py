"""XYChart BaseAxis/LinearAxis/BandAxis space allocation and rendering."""
import math
from ._scales import ticks,linear,band

DEFAULTS=dict(showLabel=True,labelFontSize=14,labelPadding=5,showTitle=True,titleFontSize=16,titlePadding=5,showTick=True,tickLength=5,tickWidth=2,showAxisLine=True,axisLineWidth=2,labelRotation=0)

def text_value(v):return f'{v:g}' if isinstance(v,(int,float)) else str(v)

class Axis:
    def __init__(self,kind,domain,title,config,painter,colors,name):
        self.kind=kind;self.domain=domain;self.title=title;self.c={**DEFAULTS,**config};self.p=painter;self.colors=colors;self.name=name
        self.position='left';self.range=(0,10);self.outer=0.;self.show=dict(line=False,label=False,tick=False,title=False);self.box=[0,0,0,0]
        self.rotation=self.c['labelRotation'] if -90<=self.c['labelRotation']<=90 else 0
        self.labels=[painter.measure(text_value(v),size=self.c['labelFontSize']) for v in self.ticks()]
        self.lw=max((b.width for b in self.labels),default=0);self.lh=max((b.height for b in self.labels),default=0)
        self.title_box=painter.measure(title,size=self.c['titleFontSize']) if title else None
    def ticks(self):return self.domain if self.kind=='band' else ticks(*self.domain)
    def calculate(self,w,h,position):
        self.position=position;vertical=position in ('left','right');available=w if vertical else h;self.show=dict(line=False,label=False,tick=False,title=False)
        if self.c['showAxisLine'] and available>self.c['axisLineWidth']:available-=self.c['axisLineWidth'];self.show['line']=True
        if self.c['showLabel']:
            self.outer=min((self.lh if vertical else self.lw)/2,.2*(h if vertical else w))
            required=self.lw if vertical else self.lh
            if position=='bottom' and self.rotation:
                a=math.radians(self.rotation);required=max(required,abs(math.sin(a)*self.lw)+abs(math.cos(a)*self.lh))
            required+=2*self.c['labelPadding']
            if required<=available:available-=required;self.show['label']=True
        if self.c['showTick'] and available>=self.c['tickLength']:available-=self.c['tickLength'];self.show['tick']=True
        if self.c['showTitle'] and self.title_box:
            required=self.title_box.height+2*self.c['titlePadding']
            if required<=available:available-=required;self.show['title']=True
        self.box=[0,0,w-available if vertical else w,h if vertical else h-available]
        return self.box[2],self.box[3]
    def set_range(self,start,end):
        self.range=(start,end)
        self.box[3 if self.position in ('left','right') else 2]=end-start
    def tick_distance(self):return abs(self.range[1]-self.range[0]-2*self.outer)/max(1,len(self.ticks()))
    def pad_bars(self):
        if .7*self.tick_distance()>self.outer*2:self.outer=math.floor(.7*self.tick_distance()/2)
    def scale(self,value):
        a,b=self.range;a+=self.outer;b-=self.outer
        if self.kind=='band':return band(self.domain,a,b,padding_inner=1)[0].get(value,a)
        domain=self.domain[::-1] if self.position=='left' else self.domain
        return linear(float(value),domain,(a,b))
    def draw(self):
        p=self.p;c=self.c;x,y,w,h=self.box;left=self.position=='left';bottom=self.position=='bottom'
        linecolor=self.colors.get('axisLineColor','#333');tickcolor=self.colors.get('tickColor','#333');labelcolor=self.colors.get('labelColor','#333');titlecolor=self.colors.get('titleColor','#333')
        if self.show['line']:
            if left:xx=x+w-c['axisLineWidth']/2;p.line(xx,y,xx,y+h,stroke=linecolor,line_width=c['axisLineWidth'],id=self.name+'-axis')
            else:yy=y+c['axisLineWidth']/2 if bottom else y+h-c['axisLineWidth']/2;p.line(x,yy,x+w,yy,stroke=linecolor,line_width=c['axisLineWidth'],id=self.name+'-axis')
        for i,value in enumerate(self.ticks()):
            loc=self.scale(value);text=self.labels[i] if i<len(self.labels) else p.measure(text_value(value),size=c['labelFontSize'])
            if self.show['tick']:
                if left:
                    xx=x+w-(c['axisLineWidth'] if self.show['line'] else 0);p.line(xx,loc,xx-c['tickLength'],loc,stroke=tickcolor,line_width=c['tickWidth'],id=f'{self.name}-tick-{i}')
                elif bottom:
                    yy=y+(c['axisLineWidth'] if self.show['line'] else 0);p.line(loc,yy,loc,yy+c['tickLength'],stroke=tickcolor,line_width=c['tickWidth'],id=f'{self.name}-tick-{i}')
                else:
                    yy=y+h-(c['axisLineWidth'] if self.show['line'] else 0);p.line(loc,yy,loc,yy-c['tickLength'],stroke=tickcolor,line_width=c['tickWidth'],id=f'{self.name}-tick-{i}')
            if self.show['label']:
                if left:
                    xx=x+w-c['labelPadding']-(c['tickLength'] if self.show['tick'] else 0)-(c['axisLineWidth'] if self.show['line'] else 0)
                    p.text(text,xx,loc-text.height/2,align='right',color=labelcolor,id=f'{self.name}-label-{i}')
                elif bottom:
                    angle=math.radians(self.rotation);xx=loc+math.sin(angle)*self.lh/2;yy=y+c['labelPadding']+(c['tickLength'] if self.show['tick'] else 0)+(c['axisLineWidth'] if self.show['line'] else 0)+abs(math.sin(angle)*self.lw/2)
                    p.text(text,xx,yy,align='center',rotation=self.rotation,color=labelcolor,id=f'{self.name}-label-{i}')
                else:
                    yy=y+(self.title_box.height+2*c['titlePadding'] if self.show['title'] else 0)+c['labelPadding'];p.text(text,loc,yy,align='center',color=labelcolor,id=f'{self.name}-label-{i}')
        if self.show['title']:
            if left:p.text(self.title_box,x+c['titlePadding'],y+h/2,align='center',rotation=270,color=titlecolor,id=self.name+'-title')
            else:p.text(self.title_box,(self.range[0]+self.range[1])/2,y+h-c['titlePadding']-self.title_box.height if bottom else y+c['titlePadding'],align='center',color=titlecolor,id=self.name+'-title')
