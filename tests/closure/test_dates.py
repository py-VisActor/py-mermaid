"""Hand-derived Gregorian/D3/Dayjs closure expectations; no Node dependency.

Literal values come from fixed defaultLocale/locale.js/advancedFormat/isoWeek
and Gregorian2024 transitions. P2 authored without executing product behavior.
"""
from datetime import datetime,timedelta
import os
import time
import unittest
from unittest.mock import patch

from py_mermaid.diagrams.temporal import _dates as dates
from py_mermaid.diagrams.temporal import _civil as civil
from .support_B import NewYork2024,document


class DateClosure(unittest.TestCase):
    def setUp(self):
        self.clock=patch.dict(os.environ,{'TZ':'UTC'});self.clock.start()
    def tearDown(self):self.clock.stop()

    def test_d01_strict_localized_formats_remain_none(self):
        for value,fmt in [('01/02/2024','L'),('January 2, 2024','LL'),
                          ('January 2, 2024 1:04 PM','LLL'),('Tuesday, January 2, 2024 1:04 PM','LLLL')]:
            with self.subTest(fmt=fmt):self.assertIsNone(dates.parse_date(value,fmt))

    def test_d02_public_browser_fallback_is_separate(self):
        for text in ('01/02/2024','January 2, 2024'):
            with self.subTest(text=text):self.assertEqual(dates.fallback_date(text),datetime(2024,1,2))
        self.assertEqual(dates.fallback_date('January 2, 2024 1:04 PM'),datetime(2024,1,2,13,4))

    def test_d03_weekday_parsing_uses_actual_calendar(self):
        self.assertEqual(dates.parse_date('2024-01-01 Monday','YYYY-MM-DD dddd'),datetime(2024,1,1))
        self.assertIsNone(dates.parse_date('2024-01-01 Tuesday','YYYY-MM-DD dddd'))

    def test_d04_dayjs_iso_year_week_and_midnight(self):
        self.assertEqual(dates.format_day(datetime(2021,1,1),'W WW GGGG k kk'),'53 53 2020 24 24')
        self.assertEqual(dates.format_day(datetime(2024,12,30,13),'W WW GGGG k kk'),'1 01 2025 13 13')

    def test_d05_dayjs_capitalized_days_and_literals(self):
        self.assertEqual(dates.format_day(datetime(2021,1,1),'dddd ddd dd d [W WW k]'),'Friday Fri Fr 5 W WW k')

    def test_d06_d3_every_directive_literal_values(self):
        d=datetime(2021,1,1,13,4,5,123000)
        expected={'a':'Fri','A':'Friday','b':'Jan','B':'January','c':'1/1/2021, 1:04:05 PM',
            'd':'01','e':' 1','f':'123000','g':'20','G':'2020','H':'13','I':'01','j':'001',
            'L':'123','m':'01','M':'04','p':'PM','q':'1','Q':'1609506245123','s':'1609506245',
            'S':'05','u':'5','U':'00','V':'53','w':'5','W':'00','x':'1/1/2021','X':'1:04:05 PM',
            'y':'21','Y':'2021','Z':'+0000','%':'%'}
        for directive,value in expected.items():
            with self.subTest(directive=directive):self.assertEqual(dates.axis_format(d,'%'+directive),value)

    def test_d07_padding_and_fraction_are_directive_specific(self):
        d=datetime(2021,1,1,1,4,5,7000)
        for fmt,expected in [('%-d','1'),('%_d',' 1'),('%0d','01'),('%-I','1'),
                            ('%_j','  1'),('%-f','7000'),('%_f','  7000'),('%0f','007000')]:
            with self.subTest(fmt=fmt):self.assertEqual(dates.axis_format(d,fmt),expected)

    def test_d08_percent_escapes_unknown_and_trailing_dispatch(self):
        self.assertEqual(dates.axis_format(datetime(2024,1,1),'%%Q %%L %%s %n %'),' %Q %L %s n '.lstrip())
        self.assertEqual(dates.axis_format(datetime(2024,1,1),'%-'),'')

    def test_d09_gregorian_zero_negative_and_extended_years(self):
        for year,fmt,expected in [(-1,'%Y','-0001'),(0,'%Y','0000'),(10000,'%Y','0000'),
                                  (-1,'%G-W%V','-0002-W53'),(0,'%G-W%V','-0001-W52'),(10000,'%G-W%V','9999-W52')]:
            with self.subTest(year=year,fmt=fmt):self.assertEqual(dates.axis_format(civil.date(year,1,1),fmt),expected)

    def test_d10_iso_week_and_sunday_monday_boundaries(self):
        for value,expected in [(datetime(2023,1,1),'01/00/52/2022'),(datetime(2024,1,1),'00/01/01/2024')]:
            with self.subTest(date=value):self.assertEqual(dates.axis_format(value,'%U/%W/%V/%G'),expected)

    def test_d11_weekday_specific_epoch_every_two(self):
        expected={'monday':[1,15,29],'tuesday':[2,16,30],'wednesday':[3,17,31],
                  'thursday':[4,18,1],'friday':[12,26],'saturday':[13,27],'sunday':[14,28]}
        for name,days in expected.items():
            with self.subTest(day=name):self.assertEqual([d.day for d in dates.time_ticks(datetime(2024,1,1),datetime(2024,2,1),'2week',name)],days)

    def test_d12_automatic_millisecond_tickstep_two_and_twenty(self):
        start=datetime(2024,1,1)
        for maximum,step in [(20,2),(200,20)]:
            with self.subTest(maximum=maximum):
                result=dates.time_ticks(start,start+timedelta(milliseconds=maximum),count=10)
                self.assertEqual([(d-start).total_seconds()*1000 for d in result],list(range(0,maximum+1,step)))

    def test_d13_inclusive_safety_boundary_has_10001_ticks(self):
        start=datetime(2024,1,1)
        ticks=dates.time_ticks(start,start+timedelta(seconds=10),'1millisecond')
        self.assertEqual(len(ticks),10001)
        self.assertEqual((ticks[0],ticks[-1]),(start,start+timedelta(seconds=10)))

    def test_d14_calendar_filters_restart_at_month_and_year(self):
        self.assertEqual([(v.month,v.day) for v in dates.time_ticks(datetime(2024,1,30),datetime(2024,2,5),'2day')],[(1,31),(2,1),(2,3),(2,5)])
        self.assertEqual([(v.year,v.month) for v in dates.time_ticks(datetime(2023,12,1),datetime(2025,1,1),'3month')],[(2024,1),(2024,4),(2024,7),(2024,10),(2025,1)])

    def test_d15_strict_leap_quarter_meridiem_regression(self):
        self.assertIsNone(dates.parse_date('2023-02-29','YYYY-MM-DD'))
        self.assertIsNone(dates.parse_date('2024-Q5-01','YYYY-[Q]Q-DD'))
        self.assertEqual(dates.parse_date('2024-Q2-01','YYYY-[Q]Q-DD'),datetime(2024,4,1))
        self.assertEqual(dates.parse_date('2024-01-01 12:01 AM','YYYY-MM-DD hh:mm A'),datetime(2024,1,1,0,1))

    def test_d16_extended_epoch_roundtrip_avoids_os_mktime(self):
        for year in (-10000,0,10000):
            value=civil.date(year,1,1)
            with self.subTest(year=year):self.assertEqual(civil.timestamp(civil.epoch_seconds(value)),value)

    def test_d17_aware_controlled_DST_not_system_TZ(self):
        zone=NewYork2024()
        for base,hours,next_hour in [(datetime(2024,3,9,12,tzinfo=zone),23,13),(datetime(2024,11,2,12,tzinfo=zone),25,11)]:
            with self.subTest(base=base),patch.object(dates,'calendar_timestamp',side_effect=lambda t:datetime.fromtimestamp(t,zone)):
                day=dates.add(base,1,'d');elapsed=dates.add(base,24,'h')
                self.assertEqual(day.hour,12);self.assertEqual(elapsed.hour,next_hour)
                self.assertEqual((civil.epoch_seconds(day)-civil.epoch_seconds(base))/3600,hours)
                # Negative control: treating a calendar day as fixed24h fails.
                self.assertNotEqual(civil.epoch_seconds(day)-civil.epoch_seconds(base),86400)

    def test_d18_source_missing_plugins_do_not_fabricate_output(self):
        with self.assertRaises(ValueError):dates.format_day(datetime(2021,1,1),'w ww gggg z')

    def test_d19_tracked_pure_denominator_and_initial_90_retained(self):
        doc=document();self.assertEqual(len(doc['pureProbes']),191)
        self.assertEqual(len({v['id'] for v in doc['pureProbes']}),191)
        self.assertEqual(sum(v['id'].startswith('BV-B-P-') for v in doc['pureProbes']),90)

    @unittest.skipUnless(hasattr(time,'tzset'),'Real IANA system TZ needs Linux tzset; aware control is a separate test')
    def test_d20_linux_real_TZ_add_and_zone_formats(self):
        previous=os.environ.get('TZ')
        try:
            os.environ['TZ']='America/New_York';time.tzset()
            self.assertEqual(datetime(2024,1,1).astimezone().utcoffset(),timedelta(hours=-5))
            self.assertEqual(datetime(2024,7,1).astimezone().utcoffset(),timedelta(hours=-4))
            for base,expected in [(datetime(2024,3,9,12),23),(datetime(2024,11,2,12),25)]:
                self.assertEqual((civil.epoch_seconds(dates.add(base,1,'d'))-civil.epoch_seconds(base))/3600,expected)
            self.assertEqual(dates.axis_format(datetime(2024,7,1),'%Z'),'-0400')
        finally:
            if previous is None:os.environ.pop('TZ',None)
            else:os.environ['TZ']=previous
            time.tzset()

    def test_d21_weekday_and_weekend_task_labels_are_not_directives(self):
        from py_mermaid import parse
        from py_mermaid.diagrams.temporal.gantt import compile_tasks
        diagram=parse('gantt\ndateFormat YYYY-MM-DD dddd\nWeekday :a, 2024-01-01 Monday, 1d\nWeekend :b, 2024-01-02 Tuesday, 1d\n')
        self.assertEqual([task.id for task in diagram.model.tasks],['a','b'])
        self.assertEqual((diagram.model.weekday,diagram.model.weekend),('sunday','saturday'))
        tasks,_=compile_tasks(diagram.model,diagram.source)
        self.assertEqual([row[1] for row in tasks],[datetime(2024,1,1),datetime(2024,1,2)])

    def test_d22_case_insensitive_whitespace_day_directives(self):
        from py_mermaid import parse
        diagram=parse('gantt\nweekday\tMONDAY\nweekend\tFRIDAY\ndateFormat YYYY-MM-DD\nA :a, 2024-01-01, 1d\n')
        self.assertEqual((diagram.model.weekday,diagram.model.weekend),('monday','friday'))


class PublicAxisPaintClosure(unittest.IsolatedAsyncioTestCase):
    async def test_d23_escape_survives_public_parse_and_paint(self):
        # gantt.jison axisFormat consumes %% within its directive; D3 %% is a
        # literal percent. cleanupComments removes only whole comment lines.
        from py_mermaid import parse,arender
        from .support_B import case
        row=case('CL-B-AXIS-ESCAPE')
        diagram=parse(row['source'],config=row['config'])
        self.assertEqual(diagram.model.axis_format,'%%Q %%L %%s')
        result=await arender(row['source'],config=row['config'],backend='cpu')
        ticks=[e for e in result.trace if e.semantic_id.startswith('tick-') and e.text]
        self.assertTrue(ticks)
        self.assertEqual({e.text for e in ticks},{'%Q %L %s'})
        from .test_layout import assert_tick_pixels
        assert_tick_pixels(self,result.data,ticks)

    async def test_d24_axis_ink_control_rejects_suppressed_public_draw(self):
        from py_mermaid import arender
        from py_mermaid.rendering.skia.scene import Painter
        from .support_B import case
        from .test_layout import assert_tick_pixels
        row=case('CL-B-AXIS-ESCAPE')
        positive=await arender(row['source'],config=row['config'],backend='cpu')
        ticks=[e for e in positive.trace if e.semantic_id.startswith('tick-') and e.text]
        original=Painter.text
        def without_ticks(owner,*args,**kw):
            if kw.get('id','').startswith('tick-'):return None
            return original(owner,*args,**kw)
        with patch.object(Painter,'text',without_ticks):
            missing=await arender(row['source'],config=row['config'],backend='cpu')
        # Positive original ROIs, rather than missing.trace, stop a suppressed
        # producer from proving its own absent glyphs. Grid center is excluded.
        with self.assertRaises(AssertionError):assert_tick_pixels(self,missing.data,ticks)

if __name__=='__main__':unittest.main()

