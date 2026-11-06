"""Assemble independently authored F01.4 fixtures, without rendering anything."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def assemble(root=ROOT):
    cases=[];parser_only=[];negative=[];unsupported=[];render_errors=[];aliases=0
    for name in ('shape','style','language','layout','resource','virtual'):
        fragment=f'tests/f014/{name}-cases.json'
        data=json.loads((root/fragment).read_text(encoding='utf-8'))
        for original in data['cases']:
            item=dict(original)
            if item.get('parserOnly'):
                parser_only.append({'id':item['id'],'fragment':fragment,'reason':'Pure parser contract; rendering covered by explicit resource fixtures'})
                continue
            item['sourceFragment']=fragment
            if 'visibleNodes' in item:item['visibleLabels']=dict(item['visibleNodes'])
            if item.get('edgeLabelKinds'):
                item['visibleEdgeLabels']=[label.strip('`').replace('**','').replace('*','') for label in item['edgeLabels']]
            if not item.get('nodes') and not item.get('groups'):
                item['expectedEmptyRendering']=True;item['expectedEmptySize']=[16,16]
            cases.append(item)
        if name=='language':
            aliases=len(data.get('aliasCases',[]))
            negative=[dict(item,sourceFragment=fragment) for item in data['negativeCases']+data['semanticErrorCases']]
            unsupported=[dict(item,scopeDisposition='deferred_by_user_separate_module' if item['id']=='math-separate' else 'excluded_by_user') for item in data['excludedCases']]
            for item in data['sourceAnomalyCases']:
                if item.get('expectation')=='positive':cases.append(dict(item,sourceFragment=fragment))
                else:render_errors.append(dict(item,code=item.get('code',item.get('nativeCode')),
                    allowNativeParseRejection=item['id']=='constructor-source-bug',
                    expectedSourceBlank=item['id']=='constructor-source-bug'))
    ids=[item['id'] for item in cases+negative+unsupported+render_errors]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate fixture ID across source fragments')
    return {'schema':'py-mermaid-f014-cases/v1','scope':'F01.4','upstreamCommit':'1fb7869866dd619168d840291c9c54b4f129758b',
            'origin':'Independent source-derived fragments. Parser aliases remain a separate unit denominator; no candidate rendering manufactures expectations.',
            'cases':cases,'negativeCases':negative,'unsupportedCases':unsupported,'renderErrorCases':render_errors,
            'parserOnlyCases':parser_only,'aliasParserDenominator':aliases,
            'scopeExclusions':{'math':'separate module explicitly deferred by user','dagre':'removed by user','interaction':'all modules static rendering only','installation':'deferred by user'}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'tests/f014/cases.json')
    args=parser.parse_args();data=assemble()
    args.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:len(data[key]) for key in ('cases','negativeCases','renderErrorCases','unsupportedCases','parserOnlyCases')},ensure_ascii=False))


if __name__=='__main__':main()
