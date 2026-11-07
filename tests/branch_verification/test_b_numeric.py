"""Fixed-source literal/relational numerical branches, designed before P3."""
import re
import unittest
from types import SimpleNamespace
from datetime import datetime

from py_mermaid.diagrams.temporal import _dates as dates
from py_mermaid.diagrams.temporal import _civil as civil
from py_mermaid.diagrams.temporal._git_layout import edge_path
from support_b import document,native_probe,get_case


class CalendarBranchContracts(unittest.TestCase):
    def test_b01_custom_parse_positive_and_strict_overflow(self):
        for text,fmt,expected in [('2024-02-29','YYYY-MM-DD',datetime(2024,2,29)),('2024-Q2-01','YYYY-[Q]Q-DD',datetime(2024,4,1)),('2024-01-01 12:01 AM','YYYY-MM-DD hh:mm A',datetime(2024,1,1,0,1)),('2023-02-29','YYYY-MM-DD',None)]:
            with self.subTest(text=text):self.assertEqual(dates.parse_date(text,fmt),expected)

    def test_b02_source_browser_date_fallback_after_localized_format(self):
        from py_mermaid import parse
        from py_mermaid.diagrams.temporal.gantt import compile_tasks
        # customParseFormat expands L while parsing, but without the separate
        # localizedFormat plugin its strict format-roundtrip can reject it.
        # getStartDate then explicitly uses new Date('01/02/2024'). Test that
        # real Gantt fallback branch, not an invented strict-L success.
        c=get_case('DATE-LOCALIZED');d=parse(c['source'],config=c['config'])
        rows,_=compile_tasks(d.model,d.source,now=datetime(2024,1,1))
        self.assertEqual(rows[0][1],datetime(2024,1,2))

    def test_b03_source_weekday_name_custom_format(self):
        self.assertEqual(dates.parse_date('2024-01-01 Monday','YYYY-MM-DD dddd'),datetime(2024,1,1))

    def test_b04_source_iso_week_and_midnight_format(self):
        date=datetime(2021,1,1)
        # ISO year differs from calendar year at this exact boundary.
        self.assertEqual(dates.format_day(date,'W WW GGGG'),'53 53 2020')
        self.assertEqual(dates.format_day(date,'k kk'),'24 24')

    def test_b05_d3_fixed_locale_composites(self):
        date=datetime(2021,1,1,13,4,5)
        for fmt,value in [('%x','1/1/2021'),('%X','1:04:05 PM'),('%c','1/1/2021, 1:04:05 PM')]:
            with self.subTest(fmt=fmt):self.assertEqual(dates.axis_format(date,fmt),value)

    def test_b06_d3_literal_percent_escapes(self):
        self.assertEqual(dates.axis_format(datetime(2024,1,1),'%%Q %%L %%s'),'%Q %L %s')

    def test_b07_d3_iso_week_and_padding_literals(self):
        date=datetime(2021,1,1,13,4,5,123000)
        for fmt,value in [('%g','20'),('%G','2020'),('%V','53'),('%U','00'),('%W','00'),('%u','5'),('%f','123000'),('%_d',' 1'),('%-I','1')]:
            with self.subTest(fmt=fmt):self.assertEqual(dates.axis_format(date,fmt),value)

    def test_b08_d3_far_year_and_iso_week(self):
        self.assertEqual(dates.axis_format(civil.date(10000,1,1),'%Y'),'0000')
        self.assertNotIn('%',dates.axis_format(civil.date(0,1,1),'%G-W%V'))

    def test_b09_two_week_monday_epoch_phase(self):
        # timeMonday.count(0,d) floors epoch to1969-12-29. Jan1 2024
        # lies 2818 weeks later, so every(2) starts Jan1, not Jan8.
        ticks=dates.time_ticks(datetime(2024,1,1),datetime(2024,2,1),'2week','monday')
        self.assertEqual([t.day for t in ticks],[1,15,29])

    def test_b10_day_filter_restarts_at_month_boundary(self):
        ticks=dates.time_ticks(datetime(2024,1,30),datetime(2024,2,5),'2day')
        self.assertEqual([(t.month,t.day) for t in ticks],[(1,31),(2,1),(2,3),(2,5)])

    def test_b11_month_filter_starts_at_january(self):
        ticks=dates.time_ticks(datetime(2023,12,1),datetime(2025,1,1),'3month')
        self.assertEqual([(t.year,t.month) for t in ticks],[(2024,1),(2024,4),(2024,7),(2024,10),(2025,1)])

    def test_b12_custom_tick_limit_falls_back_to_finite_auto_ticks(self):
        ticks=dates.time_ticks(datetime(2024,1,1),datetime(2024,1,3),'1millisecond')
        self.assertGreater(len(ticks),1);self.assertLess(len(ticks),100)
        self.assertTrue(all(a<b for a,b in zip(ticks,ticks[1:])))

    def test_b13_zero_domain_retains_the_single_timestamp(self):
        value=datetime(2024,1,1)
        self.assertEqual(dates.time_ticks(value,value),(value,))


class GitNumericBranchContracts(unittest.TestCase):
    def test_b14_lane_reservation_retry_and_depth_guard(self):
        rows=[r for r in document()['pureProbes'] if r['kind']=='gitLane']
        for row,expected in zip(rows,(50,40,13.1072)):
            with self.subTest(row=row['id']):
                actual=native_probe(row)
                self.assertIsNone(actual['error']);self.assertAlmostEqual(actual['value'],expected,places=6)

    def test_b15_nonrerouted_parent_order_changes_bend_placement(self):
        for start,end in [(0,100),(100,0)]:
            for merge in (False,True):
                with self.subTest(start=start,merge=merge):
                    a=SimpleNamespace(id='P',seq=0,branch='main',type='NORMAL',parents=())
                    b=SimpleNamespace(id='C',seq=1,branch='dev',type='MERGE' if merge else 'NORMAL',parents=('other','P') if merge else ('P',))
                    path,_,_=edge_path(a,b,{'P':(0,start),'C':(100,end)},[a,b],'LR',[])
                    first=re.search(r'L([+\-.\d]+),([+\-.\d]+)',path)
                    actual=tuple(float(x) for x in first.groups())
                    expected=(80,start) if merge else (0,end-20 if start<end else end+20)
                    self.assertEqual(actual,expected)
                    self.assertIn('A20,20',path)
