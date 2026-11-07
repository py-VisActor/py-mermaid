"""G01-B source-derived gaps; designed before the unified baseline first run.

No candidate output supplies golden coordinates. Sources and exact locations
are recorded in references/gap-audit-B.json. UTF-16 examples use escapes to
preserve their bytes across Windows shells.
"""
import math
import unittest
from datetime import datetime

from py_mermaid import parse
from py_mermaid.diagrams.temporal import _dates
from py_mermaid.diagrams.temporal.gantt import compile_tasks
from py_mermaid.diagrams.business.ishikawa import wrap
from .support import scene, command


class QuarterDateSource(unittest.TestCase):
    # ganttDb installs customParseFormat + advancedFormat. The Dayjs Q parser
    # assigns month=3*(Q-1)+1, and strict formatting round-trips the quarter.
    def test_gap_b01_quarter_start_and_end_months(self):
        for quarter, month in ((1, 1), (2, 4), (3, 7), (4, 10)):
            with self.subTest(quarter=quarter):
                d = parse('gantt\ndateFormat YYYY-[Q]Q-DD\ntodayMarker off\n'
                          f'A :a, 2024-Q{quarter}-01, 1d\n')
                rows, _ = compile_tasks(d.model, d.source, now=datetime(2024, 1, 1))
                self.assertEqual(rows[0][1:3],
                                 (datetime(2024, month, 1), datetime(2024, month, 2)))

    def test_gap_b02_invalid_quarter_fails_strict_roundtrip(self):
        for value in ('2024-Q0-01', '2024-Q5-01', '2024-Q02-01'):
            with self.subTest(value=value):
                self.assertIsNone(_dates.parse_date(value, 'YYYY-[Q]Q-DD'))

    def test_gap_b03_quarter_literal_and_ordinary_month_remain_distinct(self):
        self.assertEqual(_dates.parse_date('2024-Q2-04-01', 'YYYY-[Q2]-MM-DD'),
                         datetime(2024, 4, 1))
        self.assertEqual(_dates.parse_date('2024-02-01', 'YYYY-MM-DD'),
                         datetime(2024, 2, 1))


class IshikawaCharacterCount(unittest.TestCase):
    # ishikawaRenderer.wrapText uses String.length, before font measurement.
    def test_gap_b04_supplementary_characters_use_utf16_threshold(self):
        face = '\U0001f600'
        self.assertEqual(wrap(' '.join([face] * 8), 15),
                         ' '.join([face] * 5) + '\n' + ' '.join([face] * 3))

    def test_gap_b05_ascii_threshold_and_indivisible_word(self):
        self.assertEqual(wrap('1234567 1234567', 15), '1234567 1234567')
        self.assertEqual(wrap('12345678 1234567', 15), '12345678\n1234567')
        self.assertEqual(wrap('\U0001f600' * 9, 15), '\U0001f600' * 9)

    def test_gap_b06_bmp_characters_are_single_units(self):
        word = '\u539f\u56e0'
        self.assertEqual(wrap(' '.join([word] * 6), 15),
                         ' '.join([word] * 5) + '\n' + word)


class RendererApplicability(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def rows(box):
        # Decode actual painted runs, rather than raw TextBox input metadata.
        rows = {}
        for run in box.runs:
            rows.setdefault(round(run.baseline, 6), []).append(run.text)
        return [''.join(value) for _, value in sorted(rows.items())]

    async def test_gap_b07_git_config_literal_backslash_n_is_two_rows(self):
        name = r'alpha\nbeta'
        s = await scene('gitGraph\ncommit id:"A"\n',
                        {'gitGraph': {'mainBranchName': name}})
        label = command(s, 'branch-label-' + name).values[0]
        self.assertEqual(self.rows(label), ['alpha', 'beta'])

    async def test_gap_b08_git_newline_br_and_row_trim(self):
        # drawText splits all three separators and calls row.trim().
        for name in ('alpha\nbeta', 'alpha<br/>beta', r'  alpha\n beta  '):
            with self.subTest(name=name):
                s = await scene('gitGraph\ncommit id:"A"\n',
                                {'gitGraph': {'mainBranchName': name}})
                self.assertEqual(self.rows(command(s, 'branch-label-' + name).values[0]),
                                 ['alpha', 'beta'])

    async def test_gap_b09_event_own_html_ignores_global_label_mode(self):
        # renderD3Box unconditionally .html(box.text), including its <b> label.
        for enabled in (False, True):
            with self.subTest(htmlLabels=enabled):
                s = await scene('eventmodeling\ntf 1 ui Page\n',
                                {'htmlLabels': enabled})
                runs = [r for c in s.commands if c.kind == 'text'
                        for r in c.values[0].runs]
                visible = ''.join(r.text for r in runs)
                self.assertIn('Page', visible)
                self.assertNotIn('<b>', visible)
                self.assertNotIn('</b>', visible)
                page = [r for r in runs if 'Page' in r.text]
                self.assertTrue(page)
                self.assertTrue(all(r.font_weight in ('700', 'bold') for r in page))

    @staticmethod
    async def paths(seed):
        s = await scene('cynefin-beta\nclear\n "Repeat"\n',
                        {'renderId': 'abc', 'cynefin': {'seed': seed}})
        return tuple(c.values[0] for c in s.commands if c.kind == 'path')

    async def test_gap_b10_cynefin_nonfinite_seed_hashes_host(self):
        # Independent hashString literal: ((97*31)+98)*31+99 = 96354.
        expected = await self.paths(96354)
        self.assertTrue(expected)
        for seed in (math.nan, math.inf, -math.inf):
            with self.subTest(seed=seed):
                self.assertEqual(await self.paths(seed), expected)

    async def test_gap_b11_cynefin_non_number_seed_hashes_host(self):
        expected = await self.paths(96354)
        for seed in (True, False, '17', ''):
            with self.subTest(seed=seed):
                self.assertEqual(await self.paths(seed), expected)

    async def test_gap_b12_cynefin_zero_and_nonzero_priority(self):
        hashed = await self.paths(96354)
        self.assertEqual(await self.paths(0), hashed)
        self.assertEqual(await self.paths(-0.0), hashed)
        # Positive control prevents a repair that simply ignores every seed.
        self.assertNotEqual(await self.paths(17), hashed)
        self.assertNotEqual(await self.paths(-17), hashed)
