"""Independent literal/calendar/graph invariants from fixed source algorithms.

Private numeric ports are subjects, never expectation generators. Source
paths and exact hashes are catalogued in bulk-B-assertions.json.
"""
import copy
import re
import unittest
from datetime import datetime, timedelta,tzinfo
from unittest.mock import patch
from py_mermaid import parse
from py_mermaid.model.flowchart import MermaidError
from py_mermaid.diagrams.temporal import _dates as dates
from py_mermaid.diagrams.temporal import _civil as civil
from py_mermaid.diagrams.temporal.gantt import compile_tasks
from py_mermaid.diagrams.temporal._git_layout import positions
from py_mermaid.diagrams.business import _cynefin_geometry as cy
from py_mermaid.diagrams.business import _swimlane_sugiyama as su
from py_mermaid.diagrams.business import _swimlane_prepare as prep


class CalendarAlgorithms(unittest.TestCase):
    def compile(self, body):
        d=parse('gantt\ndateFormat YYYY-MM-DD\n'+body)
        return compile_tasks(d.model,d.source,now=datetime(2024,1,15))

    def test_d01_leap_day_duration(self):
        rows,_=self.compile('A :a, 2024-02-28, 2d\n')
        self.assertEqual(rows[0][1:3],(datetime(2024,2,28),datetime(2024,3,1)))

    def test_d02_calendar_month_and_year_clamp(self):
        for start,n,unit,expected in [(datetime(2024,1,31),1,'M',datetime(2024,2,29)),(datetime(2024,2,29),1,'y',datetime(2025,2,28)),(datetime(2023,1,31),1,'M',datetime(2023,2,28))]:
            with self.subTest(start=start):self.assertEqual(dates.add(start,n,unit),expected)

    def test_d03_day_and_week_rounding(self):
        base=datetime(2024,1,1)
        self.assertEqual(dates.add(base,.5,'d'),datetime(2024,1,2))
        self.assertEqual(dates.add(base,1.5,'w'),datetime(2024,1,12))

    def test_d04_after_uses_latest_end_until_earliest_start(self):
        rows,_=self.compile('A :a, 2024-01-01, 2d\nB :b, 2024-01-02, 4d\nC :c, after a b, 1d\nD :d, 2023-12-01, until a b\n')
        self.assertEqual(rows[2][1],datetime(2024,1,6))
        self.assertEqual(rows[3][2],datetime(2024,1,1))

    def test_d05_inclusive_end_applies_date_not_duration(self):
        rows,_=self.compile('inclusiveEndDates\nA :a, 2024-01-01, 2024-01-02\nB :b, 2024-01-01, 2d\n')
        self.assertEqual(rows[0][2],datetime(2024,1,3))
        self.assertEqual(rows[1][2],datetime(2024,1,3))

    def test_d06_include_overrides_weekend(self):
        sat=datetime(2024,1,6)
        self.assertTrue(dates.invalid(sat,'YYYY-MM-DD',('weekends',),(),'saturday'))
        self.assertFalse(dates.invalid(sat,'YYYY-MM-DD',('weekends',),('2024-01-06',),'saturday'))

    def test_d07_duration_extends_weekend_manual_end_does_not(self):
        rows,_=self.compile('excludes weekends\nA :a, 2024-01-05, 1d\nB :b, 2024-01-05, 2024-01-06\n')
        self.assertEqual(rows[0][2],datetime(2024,1,8))
        self.assertEqual(rows[1][2],datetime(2024,1,6))

    def test_d08_unknown_dependency_retains_warning_and_source_today(self):
        rows,warnings=self.compile('A :a, after missing, 1d\n')
        self.assertEqual(rows[0][1],datetime(2024,1,15))
        self.assertTrue(any('missing' in x for x in warnings))

    def test_d09_invalid_end_is_explicit_zero_duration_warning(self):
        rows,warnings=self.compile('A :a, 2024-01-01, nonsense\n')
        self.assertEqual(rows[0][1],rows[0][2])
        self.assertTrue(any('zero duration' in x for x in warnings))

    def test_d10_dependency_cycle_is_not_successful_stub(self):
        with self.assertRaises(MermaidError) as c:self.compile('A :a, after b, 1d\nB :b, after a, 1d\n')
        self.assertEqual(c.exception.code,'CYCLIC_GANTT_DEPENDENCY')

    def test_d11_duration_only_first_task_rejected(self):
        with self.assertRaises(MermaidError) as c:self.compile('A :1d\n')
        self.assertEqual(c.exception.code,'MISSING_PREVIOUS_TASK')

    def test_d12_epoch_start_X_source_milliseconds_quirk(self):
        start=dates.parse_date('1000','X',start=True)
        end=dates.parse_date('1000','X',start=False)
        # Date values are the subject. Windows mktime cannot reliably roundtrip
        # the local epoch edge; subtracting the two parsed local values retains
        # the source X-start-ms / X-end-seconds relationship without mktime.
        self.assertAlmostEqual((end-start).total_seconds(),999)

    def test_d13_strict_date_rejects_calendar_overflow(self):
        for s in ('2023-02-29','2024-13-01','2024-04-31'):
            with self.subTest(date=s):self.assertIsNone(dates.parse_date(s,'YYYY-MM-DD'))

    def test_d14_extended_gregorian_400_year_cycle(self):
        for year in (-10000,-400,0,9600):
            with self.subTest(year=year):
                a=civil.date(year,3,1);b=civil.date(year+400,3,1)
                self.assertEqual((b-a).days,146097)
                self.assertEqual(a.weekday(),b.weekday())

    def test_d15_year_zero_and_negative_leap_day(self):
        for year in (0,-400,10000):
            with self.subTest(year=year):
                value=civil.date(year,2,28)+timedelta(days=2)
                self.assertEqual((value.year,value.month,value.day),(year,3,1))
        with self.assertRaises(ValueError):civil.date(-100,2,29)

    def test_d16_extended_year_fallback_and_limits(self):
        for text,year in [('0000-01-01',0),('+010000-01-01',10000),('-010000-01-01',-10000)]:
            with self.subTest(text=text):self.assertEqual(dates.fallback_date(text).year,year)
        self.assertIsNone(dates.fallback_date('+010001-01-01'))

    def test_d17_DST_calendar_day_vs_elapsed_hours_controlled_host(self):
        # Source Dayjs add(day) preserves wall time; add(hour) uses epoch.
        # Substitute only the host-local timestamp conversion seam. Literal
        # 2024 New York transitions (Mar10 07UTC / Nov3 06UTC) make this
        # independent of host tzdata availability; no product algorithm is
        # substituted and neither expected 23/25 elapsed hours is computed by
        # the subject. Source ganttDb explicitly requires these DST branches.
        class NewYork2024(tzinfo):
            def utcoffset(self,d):
                wall=d.replace(tzinfo=None)
                return timedelta(hours=-4 if datetime(2024,3,10,2)<=wall<datetime(2024,11,3,2) else -5)
            def dst(self,d):return self.utcoffset(d)-timedelta(hours=-5)
            def fromutc(self,d):
                utc=d.replace(tzinfo=None)
                offset=-4 if datetime(2024,3,10,7)<=utc<datetime(2024,11,3,6) else -5
                return (utc+timedelta(hours=offset)).replace(tzinfo=self)
        ny=NewYork2024()
        for base,expected_hour,elapsed in [(datetime(2024,3,9,12,tzinfo=ny),13,23),(datetime(2024,11,2,12,tzinfo=ny),11,25)]:
            with self.subTest(base=base),patch.object(dates,'calendar_timestamp',side_effect=lambda t:datetime.fromtimestamp(t,ny)):
                day=dates.add(base,1,'d');hours=dates.add(base,24,'h')
                self.assertEqual(day.hour,12)
                self.assertEqual(hours.hour,expected_hour)
                self.assertEqual((day.timestamp()-base.timestamp())/3600,elapsed)

    def test_d18_duration_units_and_case(self):
        for v,expected in [('1.5M',(1.5,'M')),('2ms',(2,'ms')),('3m',(3,'m')),('0d',(0,'d'))]:
            with self.subTest(v=v):self.assertEqual(dates.duration(v),expected)
        for v in ('-1d','1D','1month','junk'):
            with self.subTest(v=v):self.assertIsNone(dates.duration(v))


class GitCoordinates(unittest.TestCase):
    def commits(self, extra=''):
        return parse('gitGraph\ncommit id:"A"\ncommit id:"B"\ncommit id:"C"\n'+extra).model.commits

    def test_gitc01_source_LR_50px_step(self):
        p,_,_=positions(self.commits(),{'main':0},'LR',False)
        self.assertEqual(p,{'A':(10,-2),'B':(60,-2),'C':(110,-2)})

    def test_gitc02_source_TB_and_BT_reverse(self):
        for direction,expected in [('TB',[40,90,140]),('BT',[140,90,40])]:
            with self.subTest(direction=direction):
                p,_,_=positions(self.commits(),{'main':0},direction,False)
                self.assertEqual([p[id][1] for id in ('A','B','C')],expected)

    def test_gitc03_parallel_siblings_share_chronological_axis(self):
        m=parse('gitGraph\ncommit id:"A"\nbranch dev\ncommit id:"B"\ncheckout main\ncommit id:"C"\nmerge dev id:"M"\n').model
        p,_,_=positions(m.commits,{'main':0,'dev':90},'LR',True)
        self.assertEqual([p[id][0] for id in ('A','B','C','M')],[10,60,60,110])
        self.assertEqual(p['B'][1]-p['C'][1],90)

    def test_gitc04_redux_lane_offset(self):
        p,_,_=positions(self.commits(),{'main':0},'LR',False,True)
        self.assertEqual(p['A'],(10,7))


class CynefinCoordinates(unittest.TestCase):
    def test_cyc01_literal_mulberry32_seed_zero(self):
        self.assertAlmostEqual(cy.random(0),0.26642920868471265,places=15)
        self.assertGreaterEqual(cy.random(-1),0)
        self.assertLess(cy.random(-1),1)

    def test_cyc02_UTF16_hash_literal_values(self):
        self.assertEqual(cy.hash_string(''),0)
        self.assertEqual(cy.hash_string('A'),65)
        self.assertEqual(cy.hash_string('abc'),96354)
        self.assertEqual(cy.hash_string('\U0001f600'),1772899)

    def test_cyc03_zero_amplitude_fold_is_exact_centerline(self):
        for horizontal in (False,True):
            with self.subTest(horizontal=horizontal):
                path=cy.boundary(700,420,5,0,horizontal)
                self.assertEqual(path.count('C'),7)
                values=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',path)]
                fixed=values[1::2] if horizontal else values[0::2]
                self.assertTrue(all(v==(210 if horizontal else 350) for v in fixed))

    def test_cyc04_cliff_literal_control_points(self):
        numbers=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',cy.cliff(1000,600))]
        self.assertEqual(numbers,[500,300,530,360,455,465,515,525,470,555,509,585,500,600])

    def test_cyc05_confusion_ellipse_dimensions(self):
        path=cy.confusion(800,600)
        self.assertTrue(path.startswith('M280.0,300.0'))
        self.assertEqual(path.count('A120.0,90.0'),2)
        self.assertIn('520.0,300.0',path)


class SwimlaneNumeric(unittest.TestCase):
    def test_sn01_nested_lane_map_uses_topmost_container(self):
        nodes={'L':{'isGroup':True},'G':{'isGroup':True,'parentId':'L'},'A':{'parentId':'G'},'B':{}}
        self.assertEqual(su.lane_map(nodes),{'L':None,'G':'L','A':'L','B':None})

    def test_sn02_cycle_reversal_preserves_ids_and_yields_DAG(self):
        nodes={id:{} for id in 'ABC'}
        edges=[{'id':'ab','src':'A','dst':'B'},{'id':'bc','src':'B','dst':'C'},{'id':'ca','src':'C','dst':'A'}]
        before=copy.deepcopy(edges);actual=su.remove_cycles(nodes,edges)
        self.assertEqual(edges,before)
        self.assertEqual([(e['id'],e['src'],e['dst']) for e in actual],[('ab','A','B'),('bc','B','C'),('ca','A','C')])
        self.assertEqual(su.topological(nodes,actual),['A','B','C'])

    def test_sn03_proper_graph_inserts_each_intermediate_rank(self):
        nodes={'A':{'width':40,'height':20},'B':{'width':40,'height':20}}
        n,e,l=su.proper(nodes,[{'id':'long','src':'A','dst':'B','ref':'original'}],{'A':0,'B':3},[['A'],[],[],['B']])
        dummy=[id for id in n if id not in nodes]
        self.assertEqual(len(dummy),2)
        self.assertEqual([len(x) for x in l],[1,1,1,1])
        self.assertTrue(all(n[id]['width']==0 and n[id]['height']==0 for id in dummy))
        self.assertEqual(len(e),3)
        self.assertTrue(all(x['ref']=='original' for x in e))

    def test_sn04_label_node_cross_lane_belongs_to_target(self):
        data={'nodes':[{'id':'A','parentId':'L'},{'id':'B','parentId':'R'}],'edges':[{'id':'e','start':'A','end':'B','label':'Handoff','label_width':70,'label_height':18}]}
        prep.create_label_nodes(data)
        label=data['nodes'][-1]
        self.assertEqual((label['parentId'],label['width'],label['height']),('R',70,18))
        self.assertEqual(len(data['edges']),3)
        self.assertTrue(all(e['isLayoutOnly'] for e in data['edges'][1:]))
        self.assertEqual(data['edges'][0]['labelNodeId'],label['id'])

    def test_sn05_default_lane_is_real_group_and_idempotent(self):
        data={'direction':'TB','config':{},'nodes':[{'id':'A','width':40,'height':20}],'edges':[]}
        prep.prepare(data);prep.prepare(data)
        groups=[n for n in data['nodes'] if n.get('isGroup')]
        self.assertEqual(len(groups),1)
        self.assertEqual((groups[0]['id'],groups[0]['label'],groups[0]['padding']),('__swimlane_default__','',20))
        self.assertEqual(data['nodes'][0]['parentId'],'__swimlane_default__')

    def test_sn06_title_rect_fixed_21_and_content_floor(self):
        lane={'x':100,'y':100,'width':80,'height':100,'swimlaneContentTop':80}
        prep.assign_title_rect(lane)
        self.assertEqual(lane['groupTitleRect'],{'left':60,'right':140,'top':50,'bottom':71})
        lane['swimlaneContentTop']=60;prep.assign_title_rect(lane)
        self.assertEqual(lane['groupTitleRect']['bottom'],60)
