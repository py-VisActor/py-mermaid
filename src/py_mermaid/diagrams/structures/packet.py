"""PacketGrammar and contiguous word population, with source bit-order geometry."""
from __future__ import annotations
from dataclasses import dataclass
import re
from ...runtime.common import make_diagram,error,config_dict
from ..modeling._support import number


@dataclass(frozen=True)
class PacketField:
    start:int
    end:int
    label:str


@dataclass(frozen=True)
class PacketModel:
    words:tuple[tuple[PacketField,...],...]
    title:str=''
    acc_title:str=''
    acc_description:str=''


def _string(token):
    # Langium ValueConverter.STRING strips quotes and handles JS string escapes.
    result=[];i=1;end=len(token)-1
    while i<end:
        if token[i]=='\\' and i+1<end:
            i+=1;c=token[i];result.append({'n':'\n','r':'\r','t':'\t','b':'\b','f':'\f','v':'\v','0':'\0'}.get(c,c))
        else:result.append(token[i])
        i+=1
    return ''.join(result)


def parse(document,config):
    text=document.cleaned;header=re.match(r'\s*packet(?:-beta)?\b',text)
    if not header:raise error(document,0,'Expected packet header')
    pos=header.end();last=-1;words=[];word=[];row=1;conf=config.get('packet') or {};bits_per_row=conf.get('bitsPerRow',32);title=document.title or '';acc_title='';acc_description=''
    if isinstance(bits_per_row,bool) or not isinstance(bits_per_row,int) or bits_per_row<=0:raise error(document,0,'bitsPerRow must be a positive integer','INVALID_CONFIG')
    while pos<len(text):
        gap=re.match(r'[\t \r\n]+|%%[^\n\r]*',text[pos:])
        if gap:pos+=gap.end();continue
        common=re.match(r'(title(?:[\t ]+([^\r\n]*))?|accTitle[\t ]*:[\t ]*([^\r\n]*)|accDescr[\t ]*:[\t ]*([^\r\n]*)|accDescr\s*\{([^}]*)\})[\t ]*(?:\r?\n|$)',text[pos:])
        if common:
            if common[1].startswith('title'):
                # CommonGrammar.TITLE stops before %% and runCommonConverter
                # collapses horizontal whitespace after trimming the token.
                title=re.sub(r'[\t ]{2,}',' ',(common[2] or '').split('%%',1)[0].strip())
            elif common[3] is not None:acc_title=common[3].strip()
            else:acc_description=(common[4] if common[4] is not None else common[5] or '').strip()
            pos+=common.end();continue
        match=re.match(r'(?:(0|[1-9][0-9]*)(?:[\t ]*-[\t ]*(0|[1-9][0-9]*))?|\+[\t ]*(0|[1-9][0-9]*))[\t ]*:[\t ]*("(?:[^"\\]|\\.)*"|\x27(?:[^\x27\\]|\\.)*\x27)[\t ]*(?:%%[^\r\n]*)?(?:\r?\n|$)',text[pos:])
        if not match:raise error(document,pos,'Invalid packet block')
        start=int(match[1]) if match[1] is not None else last+1;end=int(match[2]) if match[2] is not None else None;bits=int(match[3]) if match[3] is not None else None
        if start!=last+1:raise error(document,pos,'Packet block is not contiguous','INVALID_PACKET_RANGE')
        if bits==0:raise error(document,pos,'Cannot have a zero bit field','INVALID_PACKET_RANGE')
        if end is None:end=start+(bits or 1)-1
        if end<start:raise error(document,pos,'Packet end must be greater than start','INVALID_PACKET_RANGE')
        last=end;label=_string(match[4])
        while start<=end and len(words)<10000:
            finish=min(end,row*bits_per_row-1);word.append(PacketField(start,finish,label));start=finish+1
            if finish+1==row*bits_per_row:words.append(tuple(word));word=[];row+=1
        pos+=match.end()
    if word:words.append(tuple(word))
    return make_diagram('packet',document,config,PacketModel(tuple(words),title,acc_title,acc_description))


async def build(diagram,painter):
    config=config_dict(diagram);conf=config.get('packet') or {};styles=(config.get('themeVariables') or {}).get('packet') or {};model=diagram.model
    row_h=number(conf.get('rowHeight'),32);py=number(conf.get('paddingY'),5)+(10 if conf.get('showBits',True) else 0);px=number(conf.get('paddingX'),5);bw=number(conf.get('bitWidth'),32);count=conf.get('bitsPerRow',32);width=bw*count+2;height=(row_h+py)*(len(model.words)+1)-(0 if model.title else row_h);descending=conf.get('bitOrder')=='descending'
    def text_style(classes,size,color):return painter.style(classes,tag='text',base={'font_size':painter.font_size(size),'text_color':color})
    for row,word in enumerate(model.words):
        y=row*(row_h+py)+py
        for field in word:
            bits=field.end-field.start+1;col=field.start%count;col=count-col-bits if descending else col;x=col*bw+1;w=bits*bw-px;id='packet-'+str(field.start)
            s=painter.style(('packetBlock',),id=id,base={'fill':styles.get('blockFillColor','#efefef'),'stroke':styles.get('blockStrokeColor','black'),'stroke_width':number(styles.get('blockStrokeWidth'),1)})
            painter.rect(x,y,w,row_h,style=s,id=id)
            s=text_style(('packetLabel',),styles.get('labelFontSize','12px'),styles.get('labelColor','black'));box=painter.measure(field.label,html=False,style=s);painter.text(box,x+(w-box.width)/2,y+(row_h-box.height)/2,style=s,id=id)
            if conf.get('showBits',True):
                first,last=(field.end,field.start) if descending else (field.start,field.end)
                for value,at,anchor,color in ((first,x+w/2 if bits==1 else x,'middle' if bits==1 else 'start',styles.get('startByteColor','black')),*(() if bits==1 else ((last,x+w,'end',styles.get('endByteColor','black')),))):
                    s=text_style(('packetByte','start' if value==first else 'end'),styles.get('byteFontSize','10px'),color);b=painter.measure(str(value),html=False,style=s);painter.text(b,at-(b.width/2 if anchor=='middle' else b.width if anchor=='end' else 0),y-2-b.ascent,style=s,id=id,role='bit-number')
    if model.title:
        s=text_style(('packetTitle',),styles.get('titleFontSize','14px'),styles.get('titleColor','black'));b=painter.measure(model.title,html=False,style=s);painter.text(b,(width-b.width)/2,height-(row_h+py)/2-b.height/2,style=s,id='diagram-title',role='title')
    return painter.finish(width=width,height=max(0,height),padding=0,layout=('packet-bit-rows',model.words))
