"""Khroma omitted-argument source behavior, observed in the fixed official A.

Source: khroma/src/methods/{lighten,darken,adjust_channel}.ts and
themes/theme-default.js quadrantPointFill, original first-sweep A config.
"""
import unittest
from py_mermaid.config.colors import lighten,darken,truthy
from py_mermaid.config.themes import get_theme_variables,THEMES


class OmittedThemeAmountTests(unittest.TestCase):
    def test_source_undefined_amount_retains_derived_nan_css_value(self):
        self.assertEqual(lighten('#0000ff'),'hsl(240, 100%, NaN%)')
        self.assertEqual(darken('#0000ff'),'hsl(240, 100%, NaN%)')
        self.assertEqual(get_theme_variables('default')['quadrantPointFill'],'hsl(240, 100%, NaN%)')
        self.assertFalse(truthy(float('nan')))

    def test_all_source_theme_constructors_complete_and_keep_regular_paint_colors(self):
        for name in THEMES:
            with self.subTest(theme=name):
                palette=get_theme_variables(name)
                self.assertIsInstance(palette['primaryColor'],str)
                self.assertIsInstance(palette['primaryTextColor'],str)
                self.assertNotIn('NaN',palette['primaryColor'])


if __name__=='__main__':unittest.main()
