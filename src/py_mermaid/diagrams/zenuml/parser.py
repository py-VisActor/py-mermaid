"""Native token/recursive-scope parser of locked ZenUML core3.49.2 grammar.

Ported from generated ANTLR sequenceParser rule branches and semantic Owner,
Origin, ToCollector, SignatureText, RetContext helpers. No parser subprocess.
"""
from dataclasses import dataclass,replace
import re
from .model import Participant,Statement,ZenUML
from py_mermaid.runtime.common import error,make_diagram


@dataclass(frozen=True)
class Token:
    value: str
    offset: int
    kind: str = 'symbol'


_TOKEN=re.compile(r'(?P<space>[ \t\r]+)|(?P<newline>\n)|(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)|(?P<string>"(?:[^"\n]|"")*(?:"|(?=\n|$))|\x27[^\x27\n]*\x27)|(?P<annotation>@[\w-]+)|(?P<color>\#[\da-fA-F]{3,8}\b)|(?P<money>[$\u00a3\u00a5\u20ac]\d+(?:\.\d+)?)|(?P<number>\d+(?:\.\d+)?(?:[A-Za-z]+)?)|(?P<word>[^\W\d][\w$]*)|(?P<symbol>-->|->|<<|>>|>=|<=|==|!=|&&|\|\||[{}()\[\].,:;=+*/%^!<>-])',re.U)


def _name(token):
    value=token.value
    if token.kind=='string':return value[1:-1].replace('""','"') if len(value)>1 and value[-1]==value[0] else value[1:]
    return value


def _formatted(tokens):
    # StringUtil.formatText collapses source whitespace and removes it only
    # around comma/semicolon/dot/parentheses; operators keep authored spacing.
    out=''
    for i,t in enumerate(tokens):
        if i and t.offset>tokens[i-1].offset+len(tokens[i-1].value):out+=' '
        out+=t.value
    out=re.sub(r'\s+',' ',out)
    out=re.sub(r'\s*([,;.])\s*',r'\1',out)
    return re.sub(r'\s*(\()\s*|\s*(\))',lambda m:m[1] or m[2],out).strip()


class Parser:
    def __init__(self,document,config):
        self.doc=document;self.config=config;self.tokens=[];self.i=0;self.participants={};self.comments=[];self.title=document.title;self.starter='_STARTER_';self.depth=0
    def fail(self,message,token=None):raise error(self.doc,(token or self.peek()).offset,message)
    def peek(self,n=0):return self.tokens[min(self.i+n,len(self.tokens)-1)]
    def take(self,value=None):
        t=self.peek()
        if value is not None and t.value!=value:self.fail('Expected '+value,t)
        self.i+=1;return t
    def accept(self,value):
        if self.peek().value==value:self.i+=1;return True
        return False
    def skip(self):
        while self.peek().kind in {'newline','comment'} or self.peek().value==';':
            t=self.take()
            if t.kind=='comment':self.comments.append(t.value[2:-2] if t.value.startswith('/*') else t.value[2:])
    def lex(self):
        text=self.doc.cleaned;head=re.match(r'\s*zenuml\b',text)
        if not head:self.fail('Expected zenuml',Token('',0))
        i=head.end();line_start=i;brackets=0;parens=0;seen=False
        while i<len(text):
            if not text[line_start:i].strip() and text.startswith('==',i):
                end=text.find('\n',i);end=len(text) if end<0 else end;self.tokens.append(Token(text[i:end].strip(),i,'divider'));i=end;continue
            # Source TITLE/EVENT lexer modes accept the complete Unicode line.
            if not seen and re.match(r'title\b(?![ \t]*[.(=])',text[i:]):
                end=text.find('\n',i);end=len(text) if end<0 else end
                self.tokens.extend((Token('title',i,'word'),Token(text[i+5:end].strip(),i+5,'payload')));i=end;seen=True;continue
            if text[i]==':' and not brackets and not parens:
                end=text.find('\n',i);end=len(text) if end<0 else end
                self.tokens.extend((Token(':',i),Token(text[i+1:end],i+1,'payload')));i=end;continue
            m=_TOKEN.match(text,i)
            if not m:self.fail('Invalid ZenUML token',Token(text[i],i))
            kind=m.lastgroup;value=m[0]
            if kind not in {'space','newline','comment'}:seen=True
            if value=='[':brackets+=1
            elif value==']':brackets=max(0,brackets-1)
            elif value=='(':parens+=1
            elif value==')':parens=max(0,parens-1)
            if kind=='annotation' and value.lower() in {'@return','@reply'}:value='@return'
            if kind=='word' and value=='forEach':value='foreach'
            if kind=='word' and value=='frame':value='section'
            if kind!='space':self.tokens.append(Token(value,i,kind))
            if kind=='newline':line_start=m.end()
            i=m.end()
        self.tokens.append(Token('',len(text),'eof'))
    def name(self):
        t=self.take()
        if t.kind not in {'word','string','number'}:self.fail('Expected ZenUML name',t)
        return _name(t)
    def emoji(self):
        if self.accept('['):
            explicit=self.accept(':');name=self.name()
            if explicit:self.take(':')
            self.take(']');return ':'+name+':' if explicit else name
        if self.peek().value==':' and self.peek(2).value==':':
            self.take();name=self.name();self.take(':');return ':'+name+':'
        return ''
    def endpoint(self,register=True):
        emoji=self.emoji()
        name=self.name()
        self.endpoint_emoji=emoji
        if emoji and register:self.participant(name,emoji=emoji)
        return name
    def participant(self,name,**values):
        if not name:return
        old=self.participants.get(name)
        if old:
            # Source Participants.mergeOptions uses first truthy values.
            values={k:v for k,v in values.items() if v and not getattr(old,k)}
            self.participants[name]=replace(old,**values)
        else:self.participants[name]=Participant(name,**values)
    def parens(self,mode='invocation'):
        self.take('(');tokens=[];depth=1
        while depth:
            t=self.take()
            if t.kind=='eof':self.fail('Unclosed invocation',t)
            if t.value=='(':depth+=1
            if t.value==')':depth-=1
            if depth:tokens.append(t)
        # Do not execute argument expressions, attributes or strings.
        if any(tokens[i].value=='==' and i+1<len(tokens) and tokens[i+1].value=='=' for i in range(len(tokens))):self.fail('Strict equality is not a ZenUML operator')
        tokens=[t for t in tokens if t.kind not in {'comment','newline'}]
        if mode=='parameters':
            pieces=[];start=0;balance=0
            for i,t in enumerate(tokens):
                if t.value in {'(','['}:balance+=1
                elif t.value in {')',']'}:balance-=1
                elif t.value==',' and not balance:pieces.append(tokens[start:i]);start=i+1
            if tokens[start:]:pieces.append(tokens[start:])
            result=[]
            for part in pieces:
                if len(part)>=2 and part[0].kind=='word' and part[1].value=='=':
                    expr=_formatted(part[2:]);expr=expr[1:-1] if expr.startswith(chr(34)) and expr.endswith(chr(34)) else expr;result.append(part[0].value+'='+expr)
                else:
                    expr=_formatted(part);result.append(expr[1:-1] if expr.startswith(chr(34)) and expr.endswith(chr(34)) else expr)
            return ','.join(result)
        result=_formatted(tokens)
        return result[1:-1] if mode=='expression' and result.startswith('"') and result.endswith('"') else result
    def declarations(self,group=''):
        while True:
            self.skip();t=self.peek()
            if t.kind=='eof' or t.value=='}':return
            if t.value=='title' or t.value=='title:':
                self.take();self.accept(':');parts=[]
                while self.peek().kind not in {'newline','eof'}:parts.append(self.take().value)
                self.title=' '.join(parts);continue
            if t.value=='group':
                self.take();name=self.name() if self.peek().kind in {'word','string','number'} else ''
                if self.accept('{'):self.declarations(name);self.take('}')
                continue
            if t.value.lower()=='@starter':
                self.take()
                if self.accept('('):
                    self.starter=self.name() if self.peek().value!=')' else '_STARTER_';self.accept(')')
                if self.starter!='_STARTER_':self.participant(self.starter,starter=True)
                continue
            # A statement starts at control keywords or a qualified call/arrow;
            # declaration annotations/stereotypes may be spread over lines.
            if t.value in {'if','while','for','foreach','loop','par','opt','critical','section','try','ref','return','new','{'} or t.value.lower()=='@return' or t.kind=='divider':return
            declaration_start=self.i
            annotation='';stereotype='';emoji=''
            if t.kind=='annotation':annotation=self.take().value[1:];self.skip()
            if self.accept('<<'):
                stereotype=self.name();self.accept('>>');self.accept('>')
            emoji=self.emoji()
            if self.peek().kind not in {'word','string','number'}:
                if annotation or stereotype:continue
                return
            if self.peek(1).value in {'.','->','-->','-','=', '('}:
                self.i=declaration_start
                return
            name=self.name();label='';w=None;color=''
            if self.peek().kind=='number':
                value=self.take().value
                if value.isdigit():w=float(value)
            if self.accept('as'):label=self.name() if self.peek().kind in {'word','string','number'} else ''
            if self.peek().kind=='color':color=self.take().value
            self.comments=[]
            self.participant(name,label=label,type=annotation,stereotype=stereotype,emoji=emoji,color=color,group=group,width=w,explicit=True)
    def block(self,origin=None,caller=None,braced=False):
        self.depth+=1
        if self.depth>128:self.fail('ZenUML nesting budget exceeded')
        if braced:self.take('{')
        result=[]
        while True:
            self.skip();t=self.peek()
            if t.kind=='eof' or t.value=='}':break
            comment='\n'.join(self.comments);self.comments=[]
            node=self.statement(origin or self.starter,caller or self.starter)
            if node:result.append(replace(node,comment=comment))
        if braced:self.take('}')
        self.depth-=1;return tuple(result)
    def optional_body(self,origin,caller):
        self.skip()
        return self.block(origin,caller,True) if self.peek().value=='{' else ()
    def statement(self,origin,caller):
        start=self.peek();value=start.value
        if start.kind=='divider':self.take();return Statement('divider',re.sub(r'^=+\s*|\s*=+$','',value),offset=start.offset)
        if value=='{':return Statement('section',children=self.block(origin,caller,True),offset=start.offset)
        if value in {'if','while','for','foreach','loop','par','opt','critical','section','try','ref'}:
            self.take()
            if value=='ref':
                args=self.parens();parts=[v.strip().strip('\"\'') for v in args.split(',')];targets=tuple(parts[1:]);[self.participant(v) for v in targets]
                ending=';' if self.accept(';') else ''
                return Statement('ref',parts[0] if parts else '',source=origin,participants=targets,offset=start.offset,source_text='ref('+args+')'+ending)
            label=self.parens(mode='expression') if self.peek().value=='(' else ''
            children=self.optional_body(origin,caller)
            if value=='if':
                sections=[('['+label+']',children)]
                while True:
                    self.skip()
                    if not self.accept('else'):break
                    if self.accept('if'):condition=self.parens(mode='expression') if self.peek().value=='(' else '';sections.append(('['+condition+']',self.optional_body(origin,caller)))
                    else:sections.append(('[else]',self.optional_body(origin,caller)));break
                return Statement('alt',label,source=origin,children=children,sections=tuple(sections),offset=start.offset)
            if value=='try':
                sections=[('try',children)]
                while True:
                    self.skip()
                    if self.accept('catch'):
                        param=self.parens() if self.peek().value=='(' else '';sections.append(('catch '+param,self.optional_body(origin,caller)))
                    elif self.accept('finally'):sections.append(('finally',self.optional_body(origin,caller)));break
                    else:break
                return Statement('tcf','',source=origin,children=children,sections=tuple(sections),offset=start.offset)
            return Statement('loop' if value in {'while','for','foreach','loop'} else value,label,source=origin,children=children,offset=start.offset)
        returning=value in {'return','@return'}
        if returning:
            self.take()
            if value=='@return':self.skip()
        elif value in {'const','readonly','static','await'}:
            while self.peek().value in {'const','readonly','static','await'}:self.take()
        if returning and self.peek(1).value not in {'->','-->',':'}:
            tokens=[];balance=0
            while self.peek().kind!='eof':
                t=self.peek()
                if not balance and (t.kind=='newline' or t.value in {';','}'}):break
                self.take();tokens.append(t)
                if t.value in {'(','['}:balance+=1
                if t.value in {')',']'}:balance-=1
                if balance<0:self.fail('Unmatched return expression delimiter',t)
            if balance:self.fail('Unclosed return expression')
            result=_formatted(tokens)
            if len(result)>=2 and result.startswith(chr(34)) and result.endswith(chr(34)):result=result[1:-1]
            return Statement('return',result,origin,caller,offset=start.offset)
        # Assignment is recognized at token level, separately from named
        # parameters, comparisons, return expressions and creation constructors.
        mark=self.i;assignment='';assignee=''
        for k in range(self.i,min(self.i+4,len(self.tokens))):
            if self.tokens[k].value=='=':
                lhs=self.tokens[self.i:k]
                assignee=_name(lhs[-1]) if lhs else ''
                assignment=(assignee+':'+_name(lhs[0])) if len(lhs)==2 and all(t.kind in {'word','string'} for t in lhs) else _formatted(lhs)
                self.i=k+1;break
            if self.tokens[k].value in {'.','->','-->','(',':','\n',';','{','}'}:break
        while self.peek().value=='await':self.take()
        if self.accept('new'):
            constructor=self.name() if self.peek().kind in {'word','string'} else 'Missing Constructor';parameters=self.parens(mode='parameters') if self.peek().value=='(' else ''
            target=(assignee+':' if assignment else '')+constructor;self.participant(target)
            children=self.optional_body(target,origin)
            return Statement('creation','\u00ab'+(parameters or 'create')+'\u00bb',origin,target,children,assignment=assignment,offset=start.offset,assignee=assignee)
        if returning and self.peek().kind in {'newline','eof'} or returning and self.peek().value in {';','}'}:
            return Statement('return','',origin,caller,offset=start.offset)
        if self.peek().kind not in {'word','number','string'} and self.peek().value not in {'[',':'}:self.fail('Expected message, return expression or control fragment')
        first=self.endpoint(False);first_emoji=self.endpoint_emoji;src=origin;dst=origin;signature='';kind='return' if returning else 'sync'
        if self.peek().value in {'->','-->','-'}:
            if first_emoji:self.participant(first,emoji=first_emoji)
            arrow=self.take().value;src=first;self.participant(src,emoji=first_emoji);dst=self.endpoint() if self.peek().kind in {'word','string','number'} or self.peek().value in {'[',':'} else caller
            if self.peek().value==':' and dst==caller and self.tokens[self.i-1].value in {'->','-->'}:self.fail('Expected async target before colon')
            self.participant(src);self.participant(dst)
            if self.accept(':'):
                parts=[]
                while self.peek().kind not in {'newline','eof'} and self.peek().value not in {';','}'}:parts.append(self.take())
                signature=(parts[0].value.strip() if len(parts)==1 and parts[0].kind=='payload' else _formatted(parts));kind='return' if returning or arrow=='-->' else 'async'
            elif self.accept('.'):
                signature=self.function()
                kind='return' if returning or arrow=='-->' else 'sync'
            else:signature='';kind='return' if returning or arrow=='-->' else 'async'
        elif self.accept('.'):
            dst=first;self.participant(dst,emoji=first_emoji);signature=self.function()
        elif self.accept(':'):
            # Source supports the colon asynchronous form with an implied owner.
            dst=first;self.participant(dst);parts=[]
            while self.peek().kind not in {'newline','eof'} and self.peek().value not in {';','}'}:parts.append(self.take())
            signature=(parts[0].value.strip() if len(parts)==1 and parts[0].kind=='payload' else _formatted(parts));kind='return' if returning else 'async'
        else:
            signature=('['+first_emoji+']' if first_emoji else '')+first+(('('+self.parens()+')') if self.peek().value=='(' else '')
            if returning:
                tokens=[]
                while self.peek().kind not in {'newline','eof'} and self.peek().value not in {';','}'}:tokens.append(self.take())
                signature+=_formatted(tokens);dst=caller
            elif src==self.starter:dst=self.starter
        if returning:kind='return';dst=dst if dst!=origin else caller
        if not returning:self.participant(dst)
        children=self.optional_body(dst,src) if kind=='sync' else ()
        return Statement(kind,signature,src,dst,children,assignment=assignment,offset=start.offset,assignee=assignee,return_explicit=kind=='return')
    def function(self):
        parts=[]
        while True:
            emoji=self.emoji();name=self.name();name=('['+emoji+']' if emoji else '')+name;params='('+self.parens()+')' if self.peek().value=='(' else '';parts.append(name+params)
            if not self.accept('.'):break
        return '.'.join(parts)
    def parse(self):
        self.lex();self.declarations();body=self.block(self.starter,self.starter)
        if self.peek().kind!='eof':self.fail('Unexpected closing brace')
        def statements(nodes):
            for node in nodes:
                yield node
                for _,section in node.sections:yield from statements(section)
                if not node.sections:yield from statements(node.children)
        items=tuple(statements(body));need_starter=not self.participants or any(s.kind in {'sync','async','return','creation'} and (s.source==self.starter or s.target==self.starter) for s in items)
        participants=list(self.participants.values())
        if self.starter=='_STARTER_' and need_starter and self.starter not in self.participants:participants.insert(0,Participant('_STARTER_',starter=True))
        elif self.starter not in self.participants and need_starter:participants.insert(0,Participant(self.starter,starter=True))
        return make_diagram('zenuml',self.doc,self.config,ZenUML(tuple(participants),body,self.title,self.starter))


def parse(document,config):return Parser(document,config).parse()

