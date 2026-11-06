"""Recursive descent of all four fixed Langium railroad grammars."""
import re
from dataclasses import dataclass
from .model import Expression as E,Rule,Railroad
from py_mermaid.runtime.common import make_diagram,error,sanitize_text


HEADERS={'railroad-beta':'railroad','railroad-ebnf-beta':'railroadEbnf','railroad-abnf-beta':'railroadAbnf','railroad-peg-beta':'railroadPeg'}


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    offset: int


def _unquote(value):
    value=value[1:-1]
    return re.sub(r'\\(.)',lambda m:{'n':'\n','r':'\r','t':'\t'}.get(m[1],m[1]),value,flags=re.S)


class Grammar:
    def __init__(self,document,config):
        self.doc=document;self.config=config;self.tokens=[];self.index=0;self.title=document.title;self.depth=0
    def fail(self,message,token=None):
        t=token or self.peek();raise error(self.doc,t.offset,message)
    def scan(self):
        text=self.doc.cleaned;head=re.match(r'\s*(railroad(?:-ebnf|-abnf|-peg)?-beta)\b',text)
        if not head:self.fail('Expected railroad-beta/railroad-ebnf-beta/railroad-abnf-beta/railroad-peg-beta',Token('','',0))
        self.kind=HEADERS[head[1]];i=head.end();n=len(text)
        while i<n:
            if text[i].isspace():i+=1;continue
            if text.startswith('%%',i) or self.kind=='railroadPeg' and text[i]=='#':
                end=text.find('\n',i);i=n if end<0 else end+1;continue
            if text.startswith('/*',i) or self.kind=='railroadEbnf' and text.startswith('(*',i):
                closing='*/' if text.startswith('/*',i) else '*)';end=text.find(closing,i+2)
                if end<0:self.fail('Unclosed grammar comment',Token('','',i))
                i=end+2;continue
            if (i==0 or not text[text.rfind('\n',0,i)+1:i].strip()):
                common=re.match(r'(title(?:[ \t]+|$)|accTitle\s*:|accDescr\s*(?::|\{))([^\n]*)',text[i:])
                if common:
                    if common[1].startswith('title'):self.title=_unquote(common[2].strip()) if common[2].strip().startswith(('"',"'")) else common[2].strip()
                    if common[1].endswith('{'):
                        end=text.find('}',i+common.start(2));i=n if end<0 else end+1
                    else:i+=common.end()
                    continue
            if text[i] in '\"\'':
                quote=text[i];j=i+1
                while j<n:
                    if text[j]=='\\' and self.kind!='railroadAbnf':j+=2;continue
                    if text[j]==quote:break
                    j+=1
                if j==n:self.fail('Unclosed terminal string',Token('','',i))
                if self.kind=='railroadAbnf' and quote!="\"":self.fail('ABNF uses double quoted terminals',Token('','',i))
                value=text[i+1:j] if self.kind=='railroadAbnf' else _unquote(text[i:j+1])
                self.tokens.append(Token('string',value,i));i=j+1;continue
            if self.kind=='railroadEbnf' and text[i]=='?':
                special=re.match(r'\?(?=[^?;]*[^?\s;][^?;]*\?)[^?;]*\?',text[i:])
                if special:self.tokens.append(Token('special',special[0][1:-1].strip(),i));i+=special.end();continue
            patterns=[]
            if self.kind=='railroadAbnf':patterns=[('numval',r'%[xXdDbB][0-9A-Fa-f]+(?:-[0-9A-Fa-f]+|\.[0-9A-Fa-f]+)*'),('repeat',r'[0-9]*\*[0-9]*|[0-9]+')]
            patterns += [('id',r'[A-Za-z_][\w-]*'),('symbol',r'::=|<-|[=;,|/()\[\]{}?*+&!.-]')]
            for kind,pattern in patterns:
                match=re.match(pattern,text[i:])
                if match:
                    self.tokens.append(Token(kind,match[0],i));i+=match.end();break
            else:self.fail('Invalid grammar token',Token('','',i))
        self.tokens.append(Token('eof','',n))
    def peek(self):return self.tokens[self.index]
    def accept(self,value):
        if self.peek().kind!='string' and self.peek().value==value:self.index+=1;return True
        return False
    def take(self,value=None,kind=None):
        t=self.peek()
        if value is not None and t.value!=value or kind is not None and t.kind!=kind:self.fail('Expected '+str(value or kind),t)
        self.index+=1;return t
    def combined(self,kind,elements):return elements[0] if len(elements)==1 else E(kind,children=tuple(elements))
    def expression(self):
        self.depth+=1
        if self.depth>128:self.fail('Grammar nesting budget exceeded')
        try:
            if self.kind=='railroad':return self.functional()
            sep='|' if self.kind=='railroadEbnf' else '/';alternatives=[self.sequence()]
            while self.accept(sep):alternatives.append(self.sequence())
            return self.combined('choice',alternatives)
        finally:self.depth-=1
    def sequence(self):
        result=[];stops={';',')',']','}','|','/',''}
        while self.peek().kind=='string' or self.peek().value not in stops:
            if result and self.kind=='railroadEbnf':self.accept(',')
            if self.peek().kind!='string' and self.peek().value in stops:self.fail('Expected expression after comma')
            result.append(self.term())
        if not result:self.fail('Empty grammar sequence')
        return self.combined('sequence',result)
    def term(self):
        prefix=None;repeat=None
        if self.kind=='railroadPeg' and self.peek().value in {'&','!'}:prefix=self.take().value
        if self.kind=='railroadAbnf' and self.peek().kind=='repeat':repeat=self.take().value
        inner=self.primary()
        if self.kind in {'railroadEbnf','railroadPeg'}:
            while self.peek().kind!='string' and (self.peek().value in {'?','*','+'} or self.kind=='railroadEbnf' and self.peek().value=='-'):
                op=self.take().value
                if op=='-':inner=E('sequence',children=(inner,E('terminal','-'),self.primary()))
                else:inner=E('optional',children=(inner,)) if op=='?' else E('repetition',children=(inner,),minimum=1 if op=='+' else 0)
                if self.kind=='railroadPeg':break
        if repeat:
            if '*' in repeat:
                lo,hi=repeat.split('*');minimum=int(lo) if lo else 0;maximum=int(hi) if hi else None
            else:minimum=maximum=int(repeat)
            inner=E('optional',children=(inner,)) if minimum==0 and maximum==1 else E('repetition',children=(inner,),minimum=minimum,maximum=maximum)
        if prefix:
            label='"'+inner.text+'"' if inner.kind=='terminal' else inner.text if inner.kind in {'nonterminal','special'} else '(...)'
            inner=E('special',prefix+label)
        return inner
    def primary(self):
        t=self.peek()
        if t.kind=='string':self.take();return E('terminal',t.value)
        if t.kind=='numval':self.take();return E('terminal',t.value)
        if t.kind=='special':self.take();return E('special',t.value)
        if t.kind=='id':self.take();return E('nonterminal',t.value)
        if self.accept('.'):
            if self.kind!='railroadPeg':self.fail('Any-character only belongs to PEG')
            return E('special','.')
        for opening,closing,kind in [('(',')',None),('[',']','optional'),('{','}','repetition')]:
            if self.accept(opening):
                if opening=='{' and self.kind!='railroadEbnf' or opening=='[' and self.kind=='railroadPeg':self.fail('Invalid dialect grouping')
                element=self.expression();self.take(closing);return E(kind,children=(element,)) if kind else element
        self.fail('Expected grammar primary')
    def functional(self):
        name=self.take(kind='id').value;self.take('(')
        if name in {'terminal','nonterminal','special'}:
            value=self.take(kind='string').value;self.take(')');return E(name,value)
        if name in {'sequence','choice'}:
            nodes=[self.expression()]
            while self.accept(','):nodes.append(self.expression())
            self.take(')');return self.combined(name,nodes)
        if name in {'optional','oneOrMore','zeroOrMore'}:
            node=self.expression();self.take(')');return E('optional',children=(node,)) if name=='optional' else E('repetition',children=(node,),minimum=1 if name=='oneOrMore' else 0)
        self.fail('Unknown railroad constructor '+name)
    def parse(self):
        self.scan();rules=[]
        while self.peek().kind!='eof':
            name=self.take(kind='id').value
            if self.kind=='railroadPeg':self.take('<-')
            elif self.kind=='railroadEbnf' and self.accept('::='):pass
            else:self.take('=')
            definition=self.expression();self.take(';');rules.append(Rule(sanitize_text(name,self.config),definition))
        def sanitize(node):
            return E(node.kind,sanitize_text(node.text,self.config),tuple(sanitize(ch) for ch in node.children),node.minimum,node.maximum)
        rules=[Rule(rule.name,sanitize(rule.definition)) for rule in rules]
        self.title=sanitize_text(self.title,self.config)
        return make_diagram(self.kind,self.doc,self.config,Railroad(tuple(rules),self.title,self.kind))


def parse(document,config):return Grammar(document,config).parse()

