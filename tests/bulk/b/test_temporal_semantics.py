"""Source: gantt.jison/ganttDb, journey.jison/journeyDb, timeline DB,
gitGraph.langium/gitGraphAst. Literal expectations precede candidate execution.
"""
from .support import SourceCase, model


class GanttSemantics(SourceCase):
    def test_g01_task_fields_and_tag_order(self):
        m = model('gantt\ndateFormat YYYY-MM-DD\nsection Planning\nDesign :crit, active, d, 2024-02-28, 2d\nBuild :b, after d, 3d\n')
        self.assertEqual(m.sections, ('Planning',))
        self.assertEqual([(t.id,t.text,t.previous,t.section) for t in m.tasks], [('d','Design ',None, 'Planning'),('b','Build ','d','Planning')])
        self.assertEqual(m.tasks[0].tags, ('crit','active'))
        self.assertEqual((m.tasks[0].start,m.tasks[0].end), ('2024-02-28','2d'))

    def test_g02_auto_ids_do_not_count_explicit_ids(self):
        m = model('gantt\nA :2024-01-01, 1d\nB :explicit, 2024-01-02, 1d\nC :1d\n')
        self.assertEqual([t.id for t in m.tasks], ['task1','explicit','task2'])
        self.assertEqual(m.tasks[2].previous, 'explicit')

    def test_g03_calendar_directives(self):
        m = model('gantt\ndateFormat YYYY-MM-DD\naxisFormat %d/%m\ntickInterval 2week\nexcludes weekends, 2024-01-01\nincludes 2024-01-06\nweekend friday\nweekday monday\ninclusiveEndDates\ntopAxis\ntodayMarker off\nA :2024-01-01, 1d\n')
        self.assertEqual((m.axis_format,m.tick_interval,m.weekend,m.weekday), ('%d/%m','2week','friday','monday'))
        self.assertTrue(m.inclusive)
        self.assertTrue(m.top_axis)
        self.assertIn('weekends',m.excludes)
        self.assertIn('2024-01-06',m.includes)
        self.assertEqual(m.today_marker,'off')

    def test_g04_milestone_and_vertical_are_distinct(self):
        m=model('gantt\nA :milestone, a, 2024-01-01, 0d\nRelease :vert, v, 2024-01-02, 0d\nB :b, after a, 1d\n')
        self.assertIn('milestone',m.tasks[0].tags)
        self.assertEqual(m.tasks[1].order,-1)
        self.assertEqual(m.tasks[2].order,1)

    def test_g05_section_and_title_keep_punctuation(self):
        m=model('gantt\ntitle Build #1: release\nsection QA #1\nTest :t, 2024-01-01, 1d\n')
        self.assertEqual(m.title,'Build #1: release')
        self.assertEqual(m.sections,('QA #1',))

    def test_g06_missing_task_colon_rejected(self):
        self.reject('gantt\nnot a task\n')


class JourneySemantics(SourceCase):
    def test_j01_actor_sorted_union_and_task_order(self):
        m=model('journey\ntitle Shopping\nsection Travel\nKeys:5:Dad\nCar:3:Dad,Mum,Kid2,Kid1\nsection Shopping\nShop:4:Mum\n')
        self.assertEqual(m.actors,('Dad','Kid1','Kid2','Mum'))
        self.assertEqual([t.score for t in m.tasks],[5,3,4])
        self.assertEqual(m.tasks[1].people,('Dad','Mum','Kid2','Kid1'))
        self.assertEqual(m.sections,('Travel','Shopping'))

    def test_j02_no_actor_and_empty_numeric_coercion(self):
        m=model('journey\nAlone:4\nEmpty: \n')
        self.assertEqual(m.actors,())
        self.assertEqual([t.score for t in m.tasks],[4,0])

    def test_j03_fractional_and_unbounded_finite_scores_are_not_clamped(self):
        m=model('journey\nA:2.5:Alice\nB:8:Bob\nC:-1\n')
        self.assertEqual([t.score for t in m.tasks],[2.5,8,-1])

    def test_j04_non_number_rejected(self):
        # Historical ID retained; fixed source Number() accepts these values.
        import math
        for value in ('oops','Infinity','NaN'):
            with self.subTest(value=value):
                score=model('journey\nTask:'+value+'\n').tasks[0].score
                self.assertTrue(math.isinf(score) if value=='Infinity' else math.isnan(score))

    def test_j05_missing_score_separator_rejected(self):
        self.reject('journey\nJust words\n')
        self.reject('journey\nEmpty:\n')


class TimelineSemantics(SourceCase):
    def test_t01_period_events_and_continuations(self):
        m=model('timeline\ntitle History\nsection Early\n2000 : First : Second\n : Third\n2001 : Fourth\n')
        self.assertEqual(m.title,'History')
        self.assertEqual(m.direction,'LR')
        self.assertEqual(m.periods[0].events,('First','Second','Third'))
        self.assertEqual(m.periods[1].text,'2001')
        self.assertEqual(m.periods[0].section,'Early')

    def test_t02_explicit_directions(self):
        for header,direction in [('timeline LR','LR'),('timeline TD','TD')]:
            with self.subTest(header=header):self.assertEqual(model(header+'\nEra : Event\n').direction,direction)

    def test_t03_event_colon_requires_whitespace(self):
        self.reject('timeline\n12:30 : Lunch\n')

    def test_t04_event_before_period_rejected(self):
        self.reject('timeline\n : Orphan\n','MISSING_TIMELINE_PERIOD')

    def test_t05_repeated_sections_preserve_declarations(self):
        m=model('timeline\nsection One\nA : a\nsection Two\nB : b\nsection One\nC : c\n')
        self.assertEqual(m.sections,('One','Two','One'))
        self.assertEqual([p.section for p in m.periods],['One','Two','One'])


class GitSemantics(SourceCase):
    def test_git01_commit_chain_and_explicit_metadata(self):
        m=model('gitGraph\ncommit id:"A" msg:"First" tag:"v1" tag:"stable" type:HIGHLIGHT\ncommit id:"B" type:REVERSE\n')
        self.assertEqual(m.direction,'LR')
        self.assertEqual([(c.id,c.parents,c.seq,c.branch) for c in m.commits],[('A',(),0,'main'),('B',('A',),1,'main')])
        self.assertEqual(m.commits[0].tags,('v1','stable'))
        self.assertEqual(m.commits[0].message,'First')
        self.assertEqual(m.commits[1].type,'REVERSE')

    def test_git02_branch_implicitly_checks_out(self):
        m=model('gitGraph\ncommit id:"A"\nbranch dev\ncommit id:"B"\ncheckout main\ncommit id:"C"\n')
        self.assertEqual([(c.id,c.branch,c.parents) for c in m.commits],[('A','main',()),('B','dev',('A',)),('C','main',('A',))])
        self.assertEqual(dict(m.heads),{'main':'C','dev':'B'})

    def test_git03_merge_parent_order_and_custom_type(self):
        m=model('gitGraph\ncommit id:"A"\nbranch dev\ncommit id:"B"\nswitch main\ncommit id:"C"\nmerge dev id:"M" type:REVERSE tag:"release"\n')
        c=m.commits[-1]
        self.assertEqual((c.id,c.parents,c.type,c.custom_type,c.tags),('M',('C','B'),'MERGE','REVERSE',('release',)))

    def test_git04_default_branch_and_stable_order(self):
        m=model('gitGraph\nbranch last order:9\nbranch first order:1\n',{'gitGraph':{'mainBranchName':'trunk','mainBranchOrder':5}})
        self.assertEqual(m.branches,(('first',1),('trunk',5),('last',9)))

    def test_git05_cherry_pick_preserves_both_parent_links(self):
        m=model('gitGraph\ncommit id:"A"\nbranch dev\ncommit id:"B"\ncheckout main\ncommit id:"C"\ncherry-pick id:"B"\n')
        c=m.commits[-1]
        self.assertEqual(c.parents,('C','B'))
        self.assertEqual(c.type,'CHERRY_PICK')
        self.assertEqual(c.tags,('cherry-pick:B',))
        self.assertRegex(c.id,r'^3-[0-9a-f]{7}$')

    def test_git06_directions_require_colon(self):
        for direction in ('LR','TB','BT'):
            with self.subTest(direction=direction):self.assertEqual(model('gitGraph '+direction+':\ncommit id:"A"\n').direction,direction)
        self.reject('gitGraph TB\ncommit\n')

    def test_git07_unknown_checkout_exact_error(self):
        self.reject('gitGraph\ncheckout missing\n','UNKNOWN_GIT_BRANCH')

    def test_git08_duplicate_branch_exact_error(self):
        self.reject('gitGraph\nbranch dev\nbranch dev\n','DUPLICATE_GIT_BRANCH')

    def test_git09_self_merge_exact_error(self):
        self.reject('gitGraph\ncommit id:"A"\nmerge main\n','INVALID_GIT_MERGE')

    def test_git10_cherry_pick_current_branch_rejected(self):
        self.reject('gitGraph\ncommit id:"A"\ncherry-pick id:"A"\n','INVALID_CHERRY_PICK')

    def test_git11_semicolon_and_unquoted_id_rejected(self):
        for source in ('gitGraph\ncommit;commit\n','gitGraph\ncommit id:A\n','gitGraph\nbranch dev order:-1\n','gitGraph\ncommit type:MAGIC\n'):
            with self.subTest(source=source):self.reject(source)

    def test_git12_duplicate_ordinary_id_matches_source_map_overwrite(self):
        m=model('gitGraph\ncommit id:"A" msg:"first"\ncommit id:"A" msg:"last"\n')
        self.assertEqual(len(m.commits),1)
        self.assertEqual(m.commits[0].message,'last')
