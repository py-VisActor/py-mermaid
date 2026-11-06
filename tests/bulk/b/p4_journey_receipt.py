"""Read completed runs, bind source/PNG hashes, write B repair records only."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[3]
    ap=argparse.ArgumentParser();ap.add_argument('--native-run',required=True);args=ap.parse_args()
    def read(p):return json.loads((root/p).read_text(encoding='utf-8'))
    def sha(p):return hashlib.sha256((root/p).read_bytes()).hexdigest()
    def write(p,v):(root/p).write_text(json.dumps(v,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    references=['packages/mermaid/src/diagrams/user-journey/journeyRenderer.ts','packages/mermaid/src/diagrams/user-journey/svgDraw.js','packages/mermaid/src/diagrams/common/svgDrawCommon.ts']
    index=read('references/bulk-B-assertions.json');previous={x['id']:x for x in index['assertions']};rows=[]
    for p in sorted((root/'tests/bulk/b').glob('test_*.py')):
        for cls in ast.parse(p.read_text(encoding='utf-8')).body:
            if not isinstance(cls,ast.ClassDef):continue
            for fn in cls.body:
                if not isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)) or not fn.name.startswith('test_'):continue
                id=cls.name+'.'+fn.name
                rows.append({**previous.get(id,{'id':id,'sourceRefs':references,'expectationOrigin':'Source svgDraw three text branches / CSS unit baseline / task bounds literals; direct public Canvas metric and pixel negative controls, never candidate coordinate goldens'}),
                    'path':p.relative_to(root).as_posix(),'line':fn.lineno,'async':isinstance(fn,ast.AsyncFunctionDef)})
    index.update(phase='P4_REPAIR',status='targeted_tests_pass_final_joint_candidate_pending',methodCount=len(rows),assertions=rows)
    index['manualRejectionRepairs']={'Journey':'CSS ex parent metrics; source FO/old/tspan and explicit clip; real bounds.stopx activity; source SVG NaN/Infinity per-attribute defaults; common note rect stroke'}
    index['sourceSpecialCases']=[s.replace('nonnumeric Number=>NaN keeps task content while source invalid face does not paint','nonnumeric Number=>NaN keeps task content; actual original SVG invalid numeric attributes default0 and invalid Infinity translate is identity') for s in index.get('sourceSpecialCases',[])]
    write('references/bulk-B-assertions.json',index)
    mapping=read('references/bulk-B-temporal-sources.json');before=mapping['nativeAggregateSHA256']
    native={p:sha(p) for p in mapping['nativeSHA256']}
    aggregate=hashlib.sha256(json.dumps(native,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if before!=aggregate:mapping.setdefault('freezeHistory',[]).append({'nativeAggregateSHA256':before,'reasonReopened':'First P4 automated candidate rejected by real manual QA; Journey source-unit/FO/activity repairs plus corrected original SVG nonfinite defaults.'})
    mapping.update(phase='P4_REPAIR',status='targeted_tests_pass_final_joint_candidate_pending',nativeSHA256=native,nativeAggregateSHA256=aggregate)
    mapping['p4Repairs']={
        'journey.py':['NativePainter.font_size retains CSS units against actual parent size/family/weight','FO plain DOM text in a normal-line-height table cell, fixed viewport clip and actual width wrapping','old single SVG baseline y+h/2+5 with inherited root font','tspan only <br> split, source task font and symmetric dy','source bounds.stopx uses task.x+diagramMarginX+taskMargin; activity endpoint stopx+2mx-4','actor legend source maxWidth threshold and20px line slots','source nonfinite cy attributes default independently0; NaN neutral line; +/-Infinity ignored translate leaves origin mouth clipped at root x0','getNoteRect default #666 border retained'],
        'supersedesEarlierIncorrectInterpretation':'P3 said NaN/Infinity face invisible; original source A SVG/PNG proves default0 face and invalid transform identity. Original P3 receipts and approvals are preserved unchanged.',
        'sourceOracleProbe':'test-runs/BULK-batch-20261106T061304Z-7b9bba54/artifacts/oracle/B-journey-nonfinite-source-probe.svg'}
    write('references/bulk-B-temporal-sources.json',mapping)
    evidence=[]
    official='test-runs/BULK-P3-official-refresh-20261106T050328Z-0274d04e/artifacts/oracle'
    for id in ('B-journey-actors-emotions','B-journey-wrapped','B-journey-bad-score','B-journey-fractional-space-valid'):
        a=f'{official}/{id}.png';b=f'test-runs/{args.native_run}/artifacts/native-cpu-B/{id}.png'
        evidence.append({'id':id,'official':a,'officialSHA256':sha(a),'native':b,'nativeSHA256':sha(b),'actualViewImage':True})
    probe='B-journey-nonfinite-source-probe'
    a=f'test-runs/BULK-batch-20261106T061304Z-7b9bba54/artifacts/oracle/{probe}.png'
    b=f'test-runs/{args.native_run}/artifacts/nonfinite-probe-native/{probe}.png'
    evidence.append({'id':probe,'official':a,'officialSHA256':sha(a),'native':b,'nativeSHA256':sha(b),'actualViewImage':True})
    fresh_gantt=[]
    for id in ('B-gantt-format-unix-ms','B-gantt-format-unix-seconds','B-gantt-duration-months','B-gantt-duration-minutes'):
        p=f'test-runs/{args.native_run}/artifacts/native-cpu-B/{id}.png'
        fresh_gantt.append({'id':id,'native':p,'nativeSHA256':sha(p),'actualViewImage':True,'originalCollisionEvidenceReused':False,'freshOfficialComparison':'Root new complete oracle capture pending; old case-fold-colliding images rejected.'})
    n=read(f'test-runs/{args.native_run}/artifacts/native-cpu-B/results.json')
    report={'schemaVersion':1,'owner':'B','phase':'P4_MANUAL_REPAIR','status':'TARGETED_PASS_PENDING_FINAL_P4',
      'rejectedCandidateRun':'test-runs/BULK-P4-final-20261106T053339Z-476daa06',
      'sourceFiles':{p:sha(p) for p in native},'nativeTemporalAggregateSHA256':aggregate,
      'fixedSource':{p:sha('.local/upstream-mermaid/'+p) for p in references},
      'sharedDependency':'NativePainter.font_size CSS px resolver, root owner; no B shared modifications',
      'sourceRepairDetails':mapping['p4Repairs'],'newMethods':12,'totalBMethods':len(rows),
      'unitRun':{'run':'test-runs/BULK-record-20261106T061635Z-5b17cfb5','methods':152,'skipped':0,'exitCode':0},
      'nativeRun':{'run':'test-runs/'+args.native_run,'cases':len(n['cases']),'failures':n['failed'],'sourceUnchanged':n['sourceUnchanged']},
      'existing115FixtureSourceConfigUnchangedByB':True,'currentFixtureSHA256':sha('tests/bulk/cases-B.json'),
      'independentProbe':'One diagnostic-only source NaN/+Inf/-Inf probe under tests/bulk/b, not added to canonical115',
      'portableIdRepairNativeReview':fresh_gantt,
      'negativeControls':['external public Canvas x metric rejects4px unit stripping','pixel clip removal changes real ink','zero-length activity drops >170px ink footprint','missing-face mutation rejected against public Canvas circle pixel reference'],
      'visualReview':{'status':'PASS_FOR_REPAIRED_JOURNEY','pairs':evidence,'conclusions':['Title is readable at parent-derived4ex size; no4px regression','FO labels wrap inside card; last line bottom clip matches original explicit fixed-height foreignObject, source inherited not accidental canvas crop','Single task activity shows complete176px source line and arrow','NaN face/eyes/neutral mouth visible at0; +/-Infinity origin-mouth right halves retained as in sourceSVG','Finite scores preserve actor circles/card/emotion and full timeline; export viewport may include more source-clipped out-of-range face ink']},
      'preservedAttempts':['BULK-record-20261106T060812Z-ee85a064: direct reference negative-descent interpretation corrected using baseline-relative x-height','BULK-record-20261106T060854Z-5a1caced: public parent font probe','BULK-record-20261106T060919Z-d261b790:149unitPASS','BULK-batch-20261106T060943Z-032c69e9: FO inherited wrong1.5 lineheight caused last line missing; corrected to CSSnormal before usercascade','BULK-record-20261106T061048Z-9a3ea354:149unitPASS','BULK-batch-20261106T061052Z-5145c39d:115CPU PASS before sourceNaN face correction','BULK-record-20261106T061457Z-5f2a7022:151unitPASS','BULK-batch-20261106T061527Z-ad9b4db3:115CPU+probePASS','BULK-batch-20261106T061640Z-b3d2c7b3:115CPU+probePASS before root evidence-id collision repair'],
      'evidenceCollisionWarning':'Old x/X and M/m fixture evidence filename collisions were discovered by root strict raw-byte QA; old four PNGs cannot be accepted as independent evidence. Root alone renames IDs and requires fresh source/native capture, keeping original source/config/expect.',
      'limitations':['These are targeted B checks, not final same-candidate P4 acceptance. Root owns complete new matrix and manual gate.','Source CSS normal line-height uses established native convention1.2; font engine ink metrics may differ from original browser, not a pixel-equivalence claim.','All initial manual rejection/earlier mistaken NaN interpretation and failed tool/source runs remain preserved.'],
      'productTestsStoppedWriting':True}
    write('docs/changes/bulk-B-P4-repair.json',report)
    print(json.dumps({'methods':len(rows),'aggregate':aggregate,'journeySHA256':sha('src/py_mermaid/diagrams/temporal/journey.py'),'fixtureSHA256':report['currentFixtureSHA256'],'nativeFailures':n['failed']}))


if __name__=='__main__':main()
