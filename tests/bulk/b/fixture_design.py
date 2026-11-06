"""Source-derived input catalogue. Running this file only writes P2 metadata.

No product module is imported, no parse/build/layout/native/oracle is invoked.
All synthetic inputs identify the source production rather than a verbatim spec.
"""
from pathlib import Path
import ast
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[3]
UP=ROOT/'.local/upstream-mermaid'
CASES=[]
SOURCE={
 'gantt':'packages/mermaid/src/diagrams/gantt/parser/gantt.jison',
 'journey':'packages/mermaid/src/diagrams/user-journey/parser/journey.jison',
 'timeline':'packages/mermaid/src/diagrams/timeline/parser/timeline.jison',
 'gitGraph':'packages/parser/src/language/gitGraph/gitGraph.langium',
 'swimlane':'packages/mermaid/src/diagrams/swimlanes/swimlanesDiagram.ts',
 'agentflow':'packages/mermaid/src/diagrams/agentflow/parser/agentflow.jison',
 'eventmodeling':'packages/parser/src/language/eventmodeling/event-modeling.langium',
 'ishikawa':'packages/mermaid/src/diagrams/ishikawa/parser/ishikawa.jison',
 'wardley':'packages/parser/src/language/wardley/wardley.langium',
 'cynefin':'packages/parser/src/language/cynefin/cynefin.langium',
}


def case(kind,id,source,labels=(),features=(),config=None,expect='render',errors=(),symbol=None):
    path=SOURCE[kind]
    CASES.append({'id':'B-'+kind+'-'+id,'kind':kind,'source':source,'config':config or {},
        'origin':{'path':path,'sha256':hashlib.sha256((UP/path).read_bytes()).hexdigest(),
                  'symbol':symbol or 'synthetic production/renderer boundary: '+','.join(features),'line':1},
        'expect':expect,'features':list(features),'expectedText':list(labels),'expectedErrorCodes':list(errors)})


def design():
    case('gantt','calendar-tags','gantt\ntitle Project\ndateFormat YYYY-MM-DD\naxisFormat %d/%m\ntodayMarker off\nsection Build\nDraft :done, a, 2024-02-28, 2d\nWork :active, crit, b, after a, 2d\nRelease :milestone, c, after b, 0d\nCut :vert, v, 2024-03-02, 0d\n',('Project','Build','Draft','Work','Release','Cut'),('tags','milestone','vertical','dependency','dateFormat','axisFormat'))
    case('gantt','excludes-includes','gantt\ndateFormat YYYY-MM-DD\nexcludes weekends, 2024-01-08\nincludes 2024-01-06\nweekend friday\nweekday monday\ntickInterval 1week\ntopAxis\ntodayMarker off\nsection S\nTask :a, 2024-01-05, 5d\n',('Task','S'),('exclusion','inclusion','weekendFriday','tickWeek','topAxis'))
    case('gantt','inclusive-until','gantt\ndateFormat YYYY-MM-DD\ninclusiveEndDates\ntodayMarker off\nA :a, 2024-01-01, 2024-01-03\nB :b, 2023-12-30, until a\n',('A','B'),('inclusiveEndDates','until'))
    case('gantt','compact','gantt\ndateFormat YYYY-MM-DD\ntodayMarker off\nsection S\nA :a, 2024-01-01, 2d\nB :b, 2024-01-03, 2d\nC :c, 2024-01-02, 2d\n',('A','B','C'),('compact','overlap','laneReuse'),{'gantt':{'displayMode':'compact','useWidth':700}})
    for fmt,start,end in [('YYYY-MM-DD HH:mm','2024-03-10 01:30','2h'),('x','1704067200000','1d'),('X','1704067200000','1d')]:
        case('gantt','format-'+('datetime' if 'HH' in fmt else fmt),'gantt\ndateFormat '+fmt+'\ntodayMarker off\nA :a, '+start+', '+end+'\n',('A',),('dateFormat','timestampStartQuirk','subdayDuration'))
    for name,start in [('year-zero','0000-01-01'),('far-positive','+010000-01-01'),('far-negative','-010000-01-01')]:
        case('gantt',name,'gantt\ntodayMarker off\nCalendar :a, '+start+', 2d\n',('Calendar',),('extendedYear','nativeDateFallback'))
    case('gantt','click-visible-class','gantt\ndateFormat YYYY-MM-DD\ntodayMarker off\nLinked :a, 2024-01-01, 1d\nclick a href "https://example.invalid"\n',('Linked',),('clickableVisibleCSS','interactionExcluded'))
    case('gantt','bad-task','gantt\nNo colon\n',features=('syntaxError',),expect='syntax_error',errors=('SYNTAX_ERROR',))
    case('gantt','cyclic','gantt\ndateFormat YYYY-MM-DD\nA :a, after b, 1d\nB :b, after a, 1d\n',features=('cycleError',),expect='error',errors=('CYCLIC_GANTT_DEPENDENCY',))
    case('gantt','missing-previous','gantt\nA :1d\n',features=('missingPrevious',),expect='error',errors=('MISSING_PREVIOUS_TASK',))
    case('gantt','bad-date','gantt\ndateFormat YYYY-MM-DD\nA :a, impossible, 1d\n',features=('dateError',),expect='error',errors=('INVALID_DATE',))
    case('journey','actors-emotions','journey\ntitle Shopping\nsection Travel\nKeys:5:Dad\nDrive:3:Dad,Mum,Kid\nsection Return\nTraffic:1:Mum\n',('Shopping','Travel','Return','Keys','Drive','Traffic','Dad','Mum','Kid'),('actorsSorted','scores135','sections','faces'))
    case('journey','fractional-empty','journey\nAlone:2.5\nEmpty:\nHigh:8:Alice\nLow:-1:Bob\n',('Alone','Empty','High','Low'),('fractionScore','emptyScore','unclampedFiniteScore'))
    case('journey','wrapped','journey\nsection This is a longer journey section\nA journey task with several words:4:Person with a long name\n',('A journey task with several words',),('wrap','actorLegend','customSizing'),{'journey':{'width':120,'taskMargin':30,'maxLabelWidth':100}})
    case('journey','bad-score','journey\nTask:not-number\n',features=('scoreError',),expect='syntax_error',errors=('SYNTAX_ERROR',))
    for direction in ('LR','TD'):
        case('timeline','direction-'+direction,'timeline '+direction+'\ntitle Releases\nsection Early\n2000 : One : Two\n : Continuation\nsection Late\n2001 : Three\n',('Releases','Early','Late','2000','2001','One','Two','Continuation','Three'),('direction'+direction,'continuation','multiEvent','section'))
    case('timeline','no-section','timeline\nA : Event one\nB : Event two\n',('A','B','Event one','Event two'),('multicolorWithoutSections',))
    case('timeline','wrapped','timeline TD\nA long period label with many words : A long event description that wraps over multiple lines\n',('A long period label with many words','A long event description that wraps over multiple lines'),('longLabels','TDMeasuredHeight'))
    case('timeline','orphan','timeline\n : Orphan\n',features=('eventBeforePeriod',),expect='syntax_error',errors=('MISSING_TIMELINE_PERIOD',))
    gitbody='commit id:"A" msg:"Start" tag:"v1"\nbranch dev order:2\ncommit id:"B" type:HIGHLIGHT\ncheckout main\ncommit id:"C" type:REVERSE\nmerge dev id:"M" tag:"release"\n'
    for direction in ('LR','TB','BT'):
        for parallel in (False,True):
            case('gitGraph',direction+('-parallel' if parallel else '-serial'),'gitGraph '+direction+':\n'+gitbody,('A','B','C','M','main','dev','v1','release'),('direction'+direction,'parallel' if parallel else 'serial','merge','highlight','reverse','tags'),{'gitGraph':{'parallelCommits':parallel,'rotateCommitLabel':False}})
    case('gitGraph','cherry','gitGraph\ncommit id:"A"\nbranch dev\ncommit id:"B"\ncheckout main\ncommit id:"C"\ncherry-pick id:"B" tag:"Picked"\n',('A','B','C','Picked'),('cherryPick','branchCheckout'))
    case('gitGraph','branch-hidden','gitGraph\ncommit id:"A" tag:"v1"\ncommit id:"B"\n',('v1',),('showBranchesFalse','showCommitLabelFalse'),{'gitGraph':{'showBranches':False,'showCommitLabel':False}})
    case('gitGraph','unknown-branch','gitGraph\ncheckout unknown\n',features=('unknownBranch',),expect='syntax_error',errors=('UNKNOWN_GIT_BRANCH',))
    case('gitGraph','self-merge','gitGraph\ncommit id:"A"\nmerge main\n',features=('invalidMerge',),expect='syntax_error',errors=('INVALID_GIT_MERGE',))
    case('gitGraph','semicolon','gitGraph\ncommit;commit\n',features=('newlinesRequired',),expect='syntax_error',errors=('SYNTAX_ERROR',))
    for direction in ('TB','TD','LR','RL','BT'):
        case('swimlane','direction-'+direction,'swimlane-beta '+direction+'\nsubgraph L[Left lane]\n A[Start]\n C{Choice}\n A --> C\nend\nsubgraph R[Right lane]\n B([Done])\nend\nC -->|Handoff| B\n',('Left lane','Right lane','Start','Choice','Done','Handoff'),('direction'+direction,'crossLane','edgeLabel','nonRectangle'))
    case('swimlane','nested-cycle','swimlane-beta TB\nsubgraph L[Outer]\n subgraph N[Nested]\n A[One]\n B[Two]\n end\n C[Three]\nend\nA --> B\nB --> C\nC --> A\n',('Outer','Nested','One','Two','Three'),('nested','cycleReversal','allEdgesRetained'))
    case('swimlane','default-lane','swimlane-beta LR\nA[Loose] -->|Next| B[Other]\n',('Loose','Other','Next'),('syntheticDefaultLane','labelNode'))
    for hops in (False,'gap',True):
        case('swimlane','hops-'+str(hops).lower(),'swimlane-beta TB\nsubgraph L[Left]\n A --> B\nend\nsubgraph R[Right]\n C --> D\nend\nA --> D\nC --> B\n',('Left','Right','A','B','C','D'),('lineHops','crossing'),{'swimlane':{'lineHops':hops}})
    case('swimlane','explicit-elk','swimlane-beta TB\nsubgraph L[Lane]\n A --> B\nend\n',('Lane','A','B'),('explicitLayoutELK',),{'layout':'elk'})
    case('swimlane','no-ignore','swimlane-beta TB\nsubgraph L[Left]\n A --> B\nend\nsubgraph R[Right]\n C --> D\nend\nB --> C\n',('Left','Right','A','B','C','D'),('ignoreCrossLaneEdgesFalse','optimizeCrossings'),{'swimlane':{'ignoreCrossLaneEdges':False,'optimizeCrossings':True}})
    case('agentflow','all-kinds','agentflow-beta TB\nconnector API[API]\nflow F[Team]\n i@{ shape: input, label: Input }\n t@{ shape: task, label: Task }\n tool@{ shape: tool, label: Tool }\n d@{ shape: decision, label: Decide }\n r@{ shape: refdoc, label: Guide }\n a@{ shape: action, label: Act }\n i --> t --> tool --> d --> a\n tool -.- r\n a --x API\nend\n',('API','Team','Input','Task','Tool','Decide','Guide','Act'),('sevenKinds','flow','connector','sequence','reference','failure'))
    case('agentflow','global-nested','agentflow-beta LR\nglobal\n G[Shared]\nend\nflow Outer[Outer]\n flow Inner[Inner]\n  A[Work] --> G\n end\nend\n',('Shared','Outer','Inner','Work'),('global','nestedFlow','crossContainer'))
    case('agentflow','swimlane','agentflow-beta TB\nflow A[Agent A]\n X[Work]\nend\nflow B[Agent B]\n Y[Result]\nend\nX -->|Send| Y\n',('Agent A','Agent B','Work','Result','Send'),('explicitSwimlane','flowBridge'),{'layout':'swimlane'})
    case('agentflow','metadata','agentflow-beta TB\nA[Work]\nA@{ shape: tool, custom: value, retry: 2, model: m }\n',('Work',),('opaqueMetadata','reservedChecksUnconsumed'))
    case('eventmodeling','all-types','eventmodeling\ntitle Order\ntf 1 ui Page\ntf 2 cmd Place\ntf 3 evt Placed\ntf 4 rmo Orders\ntf 5 pcr React\n',('Page','Place','Placed','Orders','React'),('fiveTypes','inferredRelations','lanes','titleSourceUnconsumed'))
    case('eventmodeling','data','eventmodeling\ndata payload {\n "count": 2\n}\ntf 1 ui Page [[payload]]\ntf 2 cmd Submit `json` {"id":1}\n',('Page','Submit'),('dataBlock','dataReference','dataInline'))
    case('eventmodeling','reset-multi','eventmodeling\ntf 1 cmd Place\ntf 2 cmd Pay\nrf 3 evt Placed ->> 1 ->> 2\nrf 4 ui Empty\n',('Place','Pay','Placed','Empty'),('multipleSources','reset','noResetInference'))
    case('eventmodeling','namespace-source-defect','eventmodeling\ntf 1 ui shop.Page\ntf 2 ui shop.Other\n',('Page','Other'),('namespaceLaneRepetition','sourceInheritedNamespaceLookupDefect'))
    case('eventmodeling','duplicate-id','eventmodeling\ntf 1 ui Page\nrf 1 cmd Submit\n',features=('duplicateID',),expect='syntax_error',errors=('SYNTAX_ERROR',))
    case('ishikawa','deep','ishikawa\nLate delivery\n People\n  Training\n   Practice\n  Staffing\n Process\n  Review\n Machines\n  Maintenance\n',('Late delivery','People','Training','Practice','Staffing','Process','Review','Machines','Maintenance'),('alternatingBones','deepTree','flattenParity'))
    case('ishikawa','long-label','ishikawa-beta\nAn effect label with enough words to wrap\n First top level cause\n  A detailed secondary cause with many words\n Second cause\n',('First top level cause','Second cause'),('headWrap','descendantWrap'))
    case('wardley','full','wardley-beta\ntitle Strategy\nsize [900, 600]\nanchor User [0.9, 0.5]\ncomponent API [0.7, 0.3] label [8, -8] (build) inertia\ncomponent Data [0.4, 0.8] (buy)\nUser -> API\nAPI -.-> Data\nevolve API 0.7\nnote "Risk" [0.6, 0.6]\n',('Strategy','User','API','Data','Risk'),('projection','anchor','link','dash','evolve','inertia','strategy','note'))
    case('wardley','pipeline','wardley-beta\ncomponent Compute [0.4, 0.5]\npipeline Compute {\n component Custom [0.2]\n component Utility [0.8]\n}\n',('Compute','Custom','Utility'),('pipeline','childCoordinates'))
    case('wardley','stages-decorators','wardley-beta\nevolution Genesis -> Custom -> Product -> Utility\ncomponent A [0.8, 0.2] (market)\ncomponent B [0.4, 0.6] (outsource)\naccelerator "Faster" [0.6, 0.4]\ndeaccelerator "Slower" [0.3, 0.7]\n',('Genesis','Custom','Product','Utility','A','B','Faster','Slower'),('customStages','market','outsource','accelerators'))
    case('wardley','bad-coordinate','wardley-beta\ncomponent A [101.0, 0.5]\n',features=('coordinateBounds',),expect='syntax_error',errors=('SYNTAX_ERROR',))
    case('cynefin','full','cynefin-beta\ntitle Sense making\ncomplex\n "Probe"\ncomplicated\n "Analyse"\nclear\n "Repeat"\nchaotic\n "Act"\nconfusion\n "One"\n "Two"\n "Three"\n "Hidden"\ncomplex --> complicated : "Learn"\ncomplicated --> clear\n',('Sense making','Probe','Analyse','Repeat','Act','One','Two','Three','+1 more','Learn'),('allDomains','transitions','overflow','seed'),{'cynefin':{'seed':17}})
    case('cynefin','no-description','cynefin-beta:\nclear\n "Repeat"\n',('Clear','Repeat'),('descriptionFalse','amplitudeZero'),{'cynefin':{'showDomainDescriptions':False,'boundaryAmplitude':0,'seed':5}})
    case('cynefin','host-seed','cynefin-beta\ncomplex\n "Probe"\n',('Probe',),('renderIDHostAdaptation','seedZero'),{'renderId':'native-host-id','cynefin':{'seed':0}})
    case('cynefin','bad-domain','cynefin-beta\nunknown\n "x"\n',features=('unknownDomain',),expect='syntax_error',errors=('SYNTAX_ERROR',))
    case('wardley','annotations','wardley-beta\ncomponent A [0.8, 0.2]\ncomponent B [0.2, 0.8]\nA -> B ;dependency\nannotations [0.6, 0.4]\nannotation 1, [0.4, 0.6] "Risk"\n',('A','B','Risk'),('annotation','annotationBox','linkLabel','sourceSemicolonPreserved'))
    case('eventmodeling','notes-gwt','eventmodeling\nentity Order\ntf 1 ui Page\nnote 1 {\nNote text\n}\ngwt 1 given ui Order when cmd Order then evt Order\n',('Page',),('entity','note','gwt','sourceUnconsumedMetadata'))
    case('eventmodeling','future-source','eventmodeling\ntf 1 evt Placed ->> 2\ntf 2 cmd Place\n',('Placed','Place'),('forwardReference','sourceOnlyAlreadyPlacedRelations'))
    case('timeline','multicolor-disabled','timeline\nA : First\nB : Second\n',('A','B','First','Second'),('disableMulticolor',),{'timeline':{'disableMulticolor':True}})
    for unit,span in [('M','1M'),('y','1y'),('w','1w'),('h','12h'),('m','30m'),('s','90s'),('ms','500ms')]:
        case('gantt','duration-'+unit,'gantt\ndateFormat YYYY-MM-DD HH:mm:ss\ntodayMarker off\nCalendar:a, 2024-01-31 10:00:00, '+span+'\n',('Calendar',),('duration'+unit,'calendarVsEpoch'))
    for name in ('complete-example-agentflow','smoke-valid-agentflow','pattern-reference-doc-agentflow','pattern-parallel-agentflow','pattern-connector-dotted-form-agentflow','warning-shape-unsupported-agentflow','error-shape-removed-agentflow','parse-error-unterminated-container-agentflow'):
        relative='packages/mermaid/src/diagrams/agentflow/conformance/fixtures/'+name+'.mmd'
        raw=(UP/relative).read_text(encoding='utf-8')
        case('agentflow','conformance-'+name.removesuffix('-agentflow'),raw,(),('upstreamVerbatimConformance',name),expect='syntax_error' if name.startswith('parse-error') else 'render',errors=('INVALID_SYNTAX',) if name.startswith('parse-error') else ())
        CASES[-1]['origin']={'path':relative,'sha256':hashlib.sha256((UP/relative).read_bytes()).hexdigest(),'symbol':'verbatim source conformance fixture; .expected.json is fixed source semantic receipt','line':1}
    # Source theme branches are family specific. Shared 11-theme provider
    # verification is root-owned; Timeline/Git each branch needs native paints.
    for theme in ('default','dark','forest','neutral','base','neo','neo-dark','redux','redux-dark','redux-color','redux-dark-color'):
        case('timeline','theme-'+theme,'timeline\nsection Releases\n2024 : Launch\n',('Releases','2024','Launch'),('theme'+theme,'gradient','shadow','eventBrightness'),{'theme':theme})
        case('gitGraph','theme-'+theme,'gitGraph\ncommit id:"A" tag:"v1"\nbranch dev\ncommit id:"B" type:HIGHLIGHT\n',('A','B','main','dev','v1'),('theme'+theme,'gradient','shadow','commitShapes'),{'theme':theme,'gitGraph':{'rotateCommitLabel':False}})
    for kind,source,labels in [('ishikawa','ishikawa\nEffect\n Cause\n  Detail\n',('Effect','Cause','Detail')),('agentflow','agentflow-beta TB\nflow Team[Team]\n A[Work] --> B[Done]\nend\n',('Team','Work','Done')),('swimlane','swimlane-beta LR\nsubgraph L[Lane]\n A[Work] --> B[Done]\nend\n',('Lane','Work','Done'))]:
        case(kind,'handdrawn',source,labels,('handDrawn','sourceRoughOptions'),{'look':'handDrawn','handDrawnSeed':11})
    # P3 source-backed corrections; original source strings remain intact.
    original_gantt=next(c for c in CASES if c['id']=='B-gantt-excludes-includes')
    original_gantt['expect']='upstream_defect'
    original_gantt['features'].append('sourceJisonTopAxisMissingMethod')
    original_gantt['notes']='Fixed gantt.jison:141 calls yy.TopAxis(); ganttDb exports enableTopAxis/topAxisEnabled. Official first-run TypeError preserved.'
    cyclic=next(c for c in CASES if c['id']=='B-gantt-cyclic')
    cyclic.update(expect='upstream_defect',officialExpect='degenerate_render',
                  sourceGeometry={'nonfiniteAttributes':['x','width','x1','x2'],'minimumMatches':4})
    cyclic['sourceBehavior']={
        'processed':False,'startAndEndDatesAbsent':True,'maximumRetryPasses':10,
        'officialRenderRejected':False,'nativeExpectedErrorCode':'CYCLIC_GANTT_DEPENDENCY',
        'evidence':'references/bulk-B-gantt-cycle-evidence.json',
        'svg':'test-runs/BULK-P3-official-refresh-20261106T050328Z-0274d04e/artifacts/oracle/B-gantt-cyclic.svg',
        'png':'test-runs/BULK-P3-official-refresh-20261106T050328Z-0274d04e/artifacts/oracle/B-gantt-cyclic.png'}
    cyclic['features'].append('sourceNonfiniteScheduleDegenerateRender')
    cyclic['notes']='Source returns SVG with processed=false tasks, missing start/end dates and NaN task/label/today coordinates. Exact native cycle diagnostic remains required; do not classify source as renderRejected.'
    good=original_gantt['source'].replace('topAxis\n','')
    case('gantt','excludes-includes-valid',good,('Task','S'),('exclusion','inclusion','weekendFriday','tickWeek'))
    case('gantt','top-axis-config',good,('Task','S'),('topAxisConfig','topAxisRendererBranch'),{'gantt':{'topAxis':True}})
    original_journey=next(c for c in CASES if c['id']=='B-journey-fractional-empty')
    original_journey['expect']='syntax_error';original_journey['expectedText']=[];original_journey['expectedErrorCodes']=['SYNTAX_ERROR']
    original_journey['notes']='Original retained negative: bare Empty: violates taskData :[^#\\n;]+. A space after colon is legal Number whitespace => zero.'
    case('journey','fractional-space-valid',original_journey['source'].replace('Empty:\n','Empty: \n'),('Alone','Empty','High','Low'),('fractionScore','whitespaceZero','unclampedFiniteScore'))
    badscore=next(c for c in CASES if c['id']=='B-journey-bad-score')
    badscore.update(expect='render',expectedText=['Task'],expectedErrorCodes=[])
    badscore['features']=['sourceNumberNaN','visibleTaskWithoutInvalidFace']
    badscore['notes']='Official first-run DB score={$jsNumber:NaN}; source task card/label/axis paint while SVG face NaN coordinates do not. Native retains score and explicit diagnostic.'
    original_event=next(c for c in CASES if c['id']=='B-eventmodeling-all-types')
    original_event['expect']='upstream_defect'
    original_event['features'].append('declaredTitlePublishedLexerMismatch')
    original_event['notes']='event-modeling.langium declares title=EM_TITLE; published source lexer rejects title at EOF. Official repaired-oracle error retained in 044453Z-0f6c21dc.'
    eventbody=original_event['source'].replace('title Order\n','')
    case('eventmodeling','all-types-valid',eventbody,('Page','Place','Placed','Orders','React'),('fiveTypes','inferredRelations','lanes'))
    case('eventmodeling','frontmatter-title','---\ntitle: Order\n---\n'+eventbody,('Page','Place','Placed','Orders','React'),('frontmatterTitle','sourceUnconsumedTitle','fiveTypes'))
    # Root's P4 portable-evidence identity repair. Preserve source/config and
    # provenance; Windows filenames must not differ only by letter case.
    aliases={'B-gantt-format-x':'B-gantt-format-unix-ms','B-gantt-format-X':'B-gantt-format-unix-seconds',
             'B-gantt-duration-M':'B-gantt-duration-months','B-gantt-duration-m':'B-gantt-duration-minutes'}
    for c in CASES:
        if c['id'] in aliases:c['previousEvidenceId']=c['id'];c['id']=aliases[c['id']]


def write():
    design()
    data={'schema':'py-mermaid-bulk-cases/v1','group':'B','cases':CASES}
    (ROOT/'tests/bulk/cases-B.json').write_text(json.dumps(data,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    # Inventory fixed-source spec titles/parameter-table locations separately
    # from actual encoded assertions. No file count is labelled coverage.
    paths=set(SOURCE.values())
    for name in ('temporal','business'):
        for d in json.loads((ROOT/f'references/bulk-B-{name}-sources.json').read_text(encoding='utf-8'))['diagrams']:
            paths.update(d['sourceFiles'])
    dirs=['gantt','user-journey','timeline','git','agentflow','swimlanes','eventmodeling','ishikawa','wardley','cynefin']
    for dirname in dirs:
        for p in (UP/'packages/mermaid/src/diagrams'/dirname).rglob('*'):
            if p.is_file() and p.suffix in ('.ts','.js','.jison','.mmd','.json'):paths.add(p.relative_to(UP).as_posix())
    for dirname in ('gitGraph','eventmodeling','wardley','cynefin'):
        for p in (UP/'packages/parser/src/language'/dirname).rglob('*'):
            if p.is_file() and p.suffix in ('.ts','.langium'):paths.add(p.relative_to(UP).as_posix())
    for p in (UP/'packages/mermaid/src/rendering-util/layout-algorithms/swimlanes').rglob('*.ts'):
        paths.add(p.relative_to(UP).as_posix())
    inventory=[]
    for path in sorted(paths):
        p=UP/path
        if not p.is_file():continue
        raw=p.read_bytes();s=raw.decode('utf-8');titles=[];tables=[]
        for lineno,line in enumerate(s.splitlines(),1):
            m=re.search(r'\b(?:it|test|describe)\s*\(\s*([\'\"])(.*?)\1',line)
            if m:titles.append({'line':lineno,'title':m[2]})
            if re.search(r'\b(?:it|test|describe)\.each\s*\(',line):tables.append(lineno)
        inventory.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'literalSpecTitles':titles,'parameterTableLines':tables})
    source_by_kind={}
    for name in ('temporal','business'):
        for d in json.loads((ROOT/f'references/bulk-B-{name}-sources.json').read_text(encoding='utf-8'))['diagrams']:
            source_by_kind[d['detector']]=d['sourceFiles']
    source_by_kind['cynefin'].append('packages/mermaid/src/diagrams/cynefin/cynefinBoundaries.ts')
    source_by_kind['swimlane']+=sorted(p for p in paths if '/layout-algorithms/swimlanes/' in p)
    assertions=[]
    for file in sorted((ROOT/'tests/bulk/b').glob('test_*.py')):
        tree=ast.parse(file.read_text(encoding='utf-8'))
        for cls in tree.body:
            if isinstance(cls,ast.ClassDef):
                for fn in cls.body:
                    if isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)) and fn.name.startswith('test_'):
                        family=next((k for needle,k in [('Gantt','gantt'),('Calendar','gantt'),('Journey','journey'),('Timeline','timeline'),('Git','gitGraph'),('Cynefin','cynefin'),('Event','eventmodeling'),('Ishikawa','ishikawa'),('Wardley','wardley'),('Agent','agentflow'),('Swimlane','swimlane')] if needle in cls.name),None)
                        assertions.append({'id':cls.name+'.'+fn.name,'path':file.relative_to(ROOT).as_posix(),'line':fn.lineno,'async':isinstance(fn,ast.AsyncFunctionDef),'sourceRefs':list(dict.fromkeys(source_by_kind[family])) if family else list(SOURCE.values()),'expectationOrigin':'fixed source productions/DB/formulas; see module docstring and source inventory; candidate not executed'})
    result={'schema':'bulk-source-assertions/v1','phase':'P2','status':'designed_not_executed','group':'B','frozenProductSHA256':'97b353ebf7e176a750a736a714c85638e0a497b722e451dc77570579a2d36cbb','upstreamCommit':'1fb7869866dd619168d840291c9c54b4f129758b','detectors':list(SOURCE),'methodCount':len(assertions),'fixtureCount':len(CASES),'fixturesByKind':{kind:sum(c['kind']==kind for c in CASES) for kind in SOURCE},'assertions':assertions,'fixedSourceInventory':inventory,'unexecuted':['product parse/build/layout/render','formal unittest behavior','native Canvas','official oracle','images'],'sourceSpecialCases':['Gantt invalid end -> zero duration + warning; unknown after/until -> source today warning','Git ordinary duplicate commit ID overwrites source Map entry','EventModeling same namespace creates another lane because source never stores namespace','EventModeling entity/note/gwt/title metadata are source-unconsumed paints','Agentflow reserved semantic diagnostics are not emitted by the source parser','Cynefin seed=0 uses explicit host renderId; Python deterministic host ID is native adaptation'],'conditionalHostCoverage':['DST test substitutes only host timestamp conversion and requires already available IANA America/New_York rules; absence is explicit skip, not coverage PASS'],'P3Risks':['All source independently selected semantics remain unverified; do not edit frozen src before first whole-group run','Agentflow collapsed genuine selfloop and source lower-case shape aliases need official comparison','Swimlane nested group frames/5 directions and label routes require real integration, not numeric-only success']}
    result.update(phase='P3',status='source_backed_targeted_validation',unexecuted=[],
        conditionalHostCoverage=['DST uses fixed 2024 New York transition instants and an isolated host conversion seam; spring/fall literal 23/25-hour assertions executed without host tzdata installation.'],
        pendingFinalValidation=['Updated official/native image fixtures and complete same-candidate P4 remain root-owned.'])
    result['sourceSpecialCases'] += [
        'Gantt cycle: source getTasks returns unprocessed records after10 retries, SVG bars/labels have NaN coordinates; explicit native CYCLIC_GANTT_DEPENDENCY required, not source render rejection',
        'Gantt topAxis keyword: declared Jison yy.TopAxis() missing DB export, official TypeError; preserved upstream_defect plus valid config topAxis render fixture',
        'EventModeling title: declared EM_TITLE versus published lexer EOF mismatch, official error preserved upstream_defect plus no-title/frontmatter render fixtures',
        'Journey bare empty colon is a syntax error; whitespace score Number=>0; nonnumeric Number=>NaN keeps task content while source invalid face does not paint',
        'AgentFlow raw DB keeps roundedRect/lean-right/hex/subprocess; only global nodes are membership-exempt, connectors alone are not']
    (ROOT/'references/bulk-B-assertions.json').write_text(json.dumps(result,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    print(json.dumps({'methods':len(assertions),'fixtures':len(CASES),'byKind':result['fixturesByKind'],'sourceFilesInventoried':len(inventory)}))


if __name__=='__main__':write()
