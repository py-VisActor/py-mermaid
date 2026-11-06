"""Fixed-version informational diagram, source's dedicated400x100 viewport."""
from dataclasses import dataclass
import re
from py_mermaid.runtime.common import make_diagram,error


@dataclass(frozen=True)
class Info:
    show_info: bool = False
    title: str = ''


def parse(document,config):
    text=document.cleaned
    match=re.fullmatch(r'\s*info\s*(showInfo\s*)?(?:(?:title[^\n]*|accTitle\s*:[^\n]*|accDescr\s*:[^\n]*|accDescr\s*\{[^}]*\})\s*)*',text,re.S)
    if not match:raise error(document,0,'Invalid info diagram')
    title=re.search(r'(?:^|\n)[ \t]*title[ \t]+([^\n]*)',text)
    return make_diagram('info',document,config,Info(bool(match[1]),title[1].strip() if title else document.title))


async def build(diagram,painter):
    # Source infoRenderer receives the pinned Mermaid version, independent of
    # showInfo/title/accessibility metadata, and paints one version string.
    st=painter.style('version',tag='text',base={'font_size':32})
    label=painter.measure('v12.2.0',size=st.font_size,family=st.font_family,weight=st.font_weight,italic=st.font_style!='normal',html=False,style=st)
    painter.text(label,100-label.width/2,40-label.ascent,color=st.text_color,id='version',role='version',style=st)
    return painter.finish(width=400,height=100,padding=0,layout=())


__all__=['parse','build']
