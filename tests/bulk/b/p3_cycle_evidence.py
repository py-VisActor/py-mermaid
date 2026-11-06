"""Record existing official cyclic-Gantt evidence; never runs the product."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET


def main():
    root=Path(__file__).resolve().parents[3]
    run='test-runs/BULK-P3-official-refresh-20261106T050328Z-0274d04e'
    base=root/run/'artifacts/oracle'
    paths=[base/('B-gantt-cyclic.'+suffix) for suffix in ('json','svg','png')]
    data=json.loads(paths[0].read_text(encoding='utf-8'))
    svg=ET.fromstring(paths[1].read_text(encoding='utf-8'))
    invalid=[{'tag':n.tag.rsplit('}',1)[-1],'attributes':n.attrib} for n in svg.iter() if any('NaN' in value or 'Infinity' in value for value in n.attrib.values())]
    tasks=data['snapshot']['getTasks']
    source=root/'.local/upstream-mermaid/packages/mermaid/src/diagrams/gantt/ganttDb.js'
    receipt={'schemaVersion':1,'owner':'B','case':'B-gantt-cyclic','classification':'SOURCE_DEGENERATE_RENDER_NATIVE_EXPLICIT_DIAGNOSTIC',
      'officialRun':run,'sourceVersion':'mermaid@12.2.0','sourceCommit':'1fb7869866dd619168d840291c9c54b4f129758b',
      'source':{'path':source.relative_to(root/'.local/upstream-mermaid').as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'symbols':['getTasks lines169-180: compile once plus at most10 retries, then return rawTasks even if not processed','getStartDate lines320-344: existing after dependency chosen although endTime not available','compileTasks/compileTask lines658-710: absent startTime never assigns finite endTime or processed=true']},
      'officialRenderedSvg':True,'officialRenderRejected':False,'viewBox':svg.attrib['viewBox'],
      'taskState':[{'id':t['id'],'processed':t.get('processed'),'hasStartTime':'startTime' in t,'hasEndTime':'endTime' in t} for t in tasks],
      'invalidPaintElements':invalid,
      'actualViewImage':{'path':paths[2].relative_to(root).as_posix(),'reviewed':True,'conclusion':'1600x148 image shows pale section background bands and an empty axis; both task bars and labels are absent because their source x/width are NaN. No meaningful finite cyclic schedule exists.'},
      'artifacts':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
      'nativePolicy':{'expectedErrorCode':'CYCLIC_GANTT_DEPENDENCY','expectedSuccessfulEmptyImage':False,'reason':'Unresolvable dependency cycle cannot provide source-defined finite schedule. Preserve exact explicit error instead of returning an apparently successful task-less scene.'},
      'originalInputRetained':True,'negativeControlRetained':'CalendarAlgorithms.test_d10_dependency_cycle_is_not_successful_stub','newProductBehaviorExecuted':False,'productModified':False,
      'warning':'Official SVG return is not successful task scheduling and must not be described as source render rejection.'}
    text=json.dumps(receipt,indent=2,ensure_ascii=True)+'\n'
    (root/'references/bulk-B-gantt-cycle-evidence.json').write_text(text,encoding='utf-8')
    (root/'docs/changes/bulk-B-gantt-cycle.json').write_text(text,encoding='utf-8')
    print(json.dumps({'case':receipt['case'],'viewBox':receipt['viewBox'],'invalidElements':len(invalid),'taskState':receipt['taskState'],'classification':receipt['classification']}))


if __name__=='__main__':main()
