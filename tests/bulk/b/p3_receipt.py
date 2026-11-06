"""Write source identities/repair receipt from existing evidence, no behavior."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parents[3]
    parser=argparse.ArgumentParser();parser.add_argument('--native-run',default='BULK-batch-20261106T044926Z-babecf94')
    args=parser.parse_args()
    def read(path):return json.loads((root/path).read_text(encoding='utf-8'))
    def write(path,value):(root/path).write_text(json.dumps(value,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    def sha(path):return hashlib.sha256((root/path).read_bytes()).hexdigest()
    repairs={
      'temporal':[
        {'file':'src/py_mermaid/diagrams/temporal/journey.py','cause':'Source taskData requires one character; raw whitespace Number coercion differs from bare empty colon. Source Number may NaN/Infinity; source invalid face invisible but task/actor/axis content valid.','source':['packages/mermaid/src/diagrams/user-journey/parser/journey.jison:29','packages/mermaid/src/diagrams/user-journey/journeyDb.js:addTask','packages/mermaid/src/diagrams/user-journey/svgDraw.js:drawTask'],'repair':'Retain raw task-data characters and source Number results; only invalid face geometry omitted with explicit diagnostic, all real valid task paints retained.'},
        {'file':'src/py_mermaid/diagrams/temporal/_source_styles.py','cause':'Fixed Journey source SCSS nests rect inside .edgeLabel; shared static CSS accepts flat declarations. HTML tooltip styles are interaction-only.','source':['packages/mermaid/src/diagrams/user-journey/styles.js:getStyles'],'repair':'Expand exact source child selector .edgeLabel rect; exclude div.mermaidTooltip block only, retaining all static task/actor/face rules.'}],
      'business':[
        {'file':'src/py_mermaid/diagrams/business/wardley.py','cause':'Line splitting lost source multiline accDescr terminal.','source':['packages/parser/src/language/common/common.langium:TitleAndAccessibilities'],'repair':'Reuse offset-preserving common Langium metadata masking before dedicated Wardley statement records.'},
        {'file':'src/py_mermaid/diagrams/business/ishikawa.py','cause':'Source parsed numeric font size was passed as theme CSS string in native presentation base.','source':['packages/mermaid/src/diagrams/ishikawa/ishikawaRenderer.ts:parseFontSize'],'repair':'Pass parsed source numeric size to native pure style base; source CSS remains authoritative cascade.'},
        {'file':'src/py_mermaid/diagrams/business/_flow_config.py','cause':'Old measurement compatibility override rewrote explicit swimlane to elk even for real AgentFlow graph.','source':['packages/mermaid/src/diagrams/agentflow/renderer.ts','packages/mermaid/src/rendering-util/render.ts'],'repair':'Only measurement_only bridge temporarily selects elk; retain actual source layout selection for real build/provider dispatch.'}]}
    aggregates={}
    for family in ('temporal','business'):
        path=f'references/bulk-B-{family}-sources.json';d=read(path)
        before=d['nativeAggregateSHA256']
        native={p:sha(p) for p in d['nativeSHA256']}
        aggregate=hashlib.sha256(json.dumps(native,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if before!=aggregate:
            d.setdefault('freezeHistory',[]).append({'nativeAggregateSHA256':before,'reasonReopened':'P3 complete first sweep closed before source-backed batch repairs; P1 source state preserved in closed runs and prior receipt.'})
        d.update(phase='P3_TARGETED',status='targeted_unit_pass_final_visual_pending',nativeSHA256=native,nativeAggregateSHA256=aggregate,
                 aggregateAlgorithm='SHA256 canonical JSON(sorted nativeSHA256 keys, separators comma/colon)',p3Repairs=repairs[family],
                 p3UnitRun='test-runs/BULK-record-20261106T044818Z-5294681e')
        write(path,d);aggregates[family]=aggregate
    assertion=read('references/bulk-B-assertions.json')
    fixtures=read('tests/bulk/cases-B.json')['cases']
    native=read(f'test-runs/{args.native_run}/artifacts/native-cpu-B/results.json')
    files=sorted((root/'tests/bulk/b').glob('*.py'))+[root/'tests/bulk/cases-B.json',root/'references/bulk-B-assertions.json']
    receipt={'schemaVersion':1,'scope':'BULK_STATIC_31_ENTRIES','owner':'B','phase':'P3','status':'targeted_unit_pass_final_visual_pending',
      'firstSweep':'test-runs/BULK-P3-first-20261106T042952Z-978737eb','firstSweepSourceUnchanged':True,
      'repairs':repairs,'productStoppedWriting':True,'nativeAggregateSHA256':aggregates,
      'testCorrections':[
        {'method':'test_d12_epoch_start_X_source_milliseconds_quirk','before':'end.timestamp()-start.timestamp()','after':'(end-start).total_seconds()','reason':'Windows mktime epoch edge failure occurs in test roundtrip after parsing; fixed source still requires 999-second difference.'},
        {'methods':['test_a01_source_kinds_and_shapes','test_bt12_agent_aliases_and_default_kind'],'reason':'Source shapes.ts keeps roundedRect/lean-right/hex/subprocess aliases; F014 paint canonicalisation is later, not DB expectation.'},
        {'method':'test_a02_flow_membership_and_connector','reason':'agentflowDb.ts addSubGraph filters globalNodes only; connector alone is not membership-exempt.'},
        {'method':'test_bt13_agent_unknown_registered_shape_warning_vs_invalid_name','reason':'Native public structured category UNSUPPORTED_SHAPE maps source positioned no-such-shape error.'},
        {'methods':['test_j02_no_actor_and_empty_numeric_coercion','test_j04_non_number_rejected','test_j05_missing_score_separator_rejected'],'reason':'Source lexer requires a taskData character, DB Number coercion permits whitespace zero and NaN/Infinity. Historical j04 ID retained with corrected source semantics.'}],
      'newRegression':'test_v23_journey_nonfinite_score_keeps_real_content checks real task/actor/axis plus explicit diagnosis and finite command bounds; no false replacement face.',
      'DST':{'method':'test_d17_DST_calendar_day_vs_elapsed_hours_controlled_host','hostSeam':'_dates.calendar_timestamp only; supplied literal 2024 New York clock, not a substituted date/layout algorithm','literalUTCTransitions':['2024-03-10T07:00Z','2024-11-03T06:00Z'],'assertions':['calendar add day preserves 12:00 wall time','elapsed 24h yields 13:00 spring / 11:00 fall','calendar elapsed seconds are 23h spring / 25h fall'],'ianaEnvironmentDependency':False,'installationPerformed':False,'status':'PASS'},
      'targetedUnit':{'run':'test-runs/BULK-record-20261106T044818Z-5294681e','methods':140,'skipped':0,'status':'SUCCESS','exitCode':0},
      'nativeCPU':{'run':'test-runs/'+args.native_run,'caseCount':len(native['cases']),'failed':native['failed'],'sourceUnchanged':native['sourceUnchanged'],'status':'PASS' if not native['failed'] else 'FOLLOWUP_REQUIRED','failures':[row for row in native['cases'] if row['status'] in ('ERROR','FAILED')]},
      'fixtureCount':len(fixtures),'fixtureClassification':{key:sum(c['expect']==key for c in fixtures) for key in ('render','syntax_error','error','upstream_defect')},
      'fixtureChanges':[
        {'id':'B-gantt-cyclic','change':'Original input/ID retained; source degenerate SVG is upstream_defect with officialExpect=degenerate_render and mandatory NaN attribute evidence. Exact native CYCLIC_GANTT_DEPENDENCY still required; source did not throw.','evidence':'references/bulk-B-gantt-cycle-evidence.json'},
        {'id':'B-gantt-excludes-includes','change':'Original source retained; upstream_defect: yy.TopAxis() missing exported method','evidence':'first sweep artifacts/oracle/B-gantt-excludes-includes.error.json','added':['B-gantt-excludes-includes-valid','B-gantt-top-axis-config']},
        {'id':'B-journey-fractional-empty','change':'Original bare-empty input retained as syntax_error; source lexer taskData +','added':['B-journey-fractional-space-valid']},
        {'id':'B-journey-bad-score','change':'Original input retained as render; Task remains visible; source DB Number NaN retained','evidence':'first sweep artifacts/oracle/B-journey-bad-score.json'},
        {'id':'B-eventmodeling-all-types','change':'Original title input retained as upstream_defect: declared EM_TITLE vs published lexer EOF mismatch; native metadata retained, source renderer does not draw title','evidence':'test-runs/BULK-P3-shared-and-oracle-repair-20261106T044453Z-0f6c21dc/artifacts/oracle/B-eventmodeling-all-types.error.json','added':['B-eventmodeling-all-types-valid','B-eventmodeling-frontmatter-title']}],
      'files':{p.relative_to(root).as_posix():sha(p.relative_to(root)) for p in files},
      'preservedFailedRuns':['BULK-record-20261106T044357Z-0c8c0f24 (missing PYTHONPATH, no product behavior)','BULK-record-20261106T044411Z-495683f3 (first real theme-ready B unit)','BULK-record-20261106T044745Z-e7cd4984 (remaining static tooltip CSS)','BULK-batch-20261106T044906Z-4c9d8a5c (plan schema omission, no product behavior)','BULK-batch-20261106T044926Z-babecf94 (115 CPU, one shared max-width error)'],
      'remaining':['Final same-candidate P4 / official capture / three-backend matrix / actual manual visual review are root-owned and not claimed by this targeted receipt.','Charts/flows and C private Swimlane routing files unchanged by B.','Old P2 receipts and first-run artifacts unchanged.']}
    lookup={c['id']:c for c in fixtures}
    changes=[{'id':row['id'],'expectAtNativeRun':row['expect'],'currentExpect':lookup[row['id']]['expect'],'actualNativeErrorCode':row.get('errorCode')} for row in native['cases'] if row['expect']!=lookup[row['id']]['expect']]
    if changes:receipt['postValidationMetadataMigrations']={'changes':changes,'productOrInputChanged':False,'finalRootP4Required':True,'reason':'Official source-degenerate-render evidence classification corrected after prior targeted native run; original exact native error remains required.'}
    write('docs/changes/bulk-B-P3.json',receipt)
    print(json.dumps({'unitMethods':140,'fixtures':len(fixtures),'nativeFailures':native['failed'],'fixtureSHA256':sha('tests/bulk/cases-B.json'),'aggregates':aggregates}))


if __name__=='__main__':main()
