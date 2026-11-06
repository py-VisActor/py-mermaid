"""Independent controls for the rich-label evidence comparator."""
from pathlib import Path
import sys
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from rich_scene_checks import _foreground, _text_matches, color, same_color


class RichEvidenceControls(unittest.TestCase):
    def test_source_negative_hues_and_fractional_rgb_are_real_css_colors(self):
        self.assertEqual(color('hsl(-120, 0%, 80%)'),(204,204,204,255))
        self.assertTrue(same_color('hsl(-79.4117647059, 60%, 83.3333333333%)','rgb(222, 187, 238)'))
        self.assertFalse(same_color('hsl(40.5882352941, 60%, 83.3333333333%)','rgb(222, 187, 238)'))
        self.assertEqual(color('hsla(-120, 100%, 50%, .5)'),(0,0,255,128))
        self.assertIsNone(color('hsl(NaN, 100%, 50%)'))

    def test_thin_antialiased_stroke_has_color_but_white_and_wrong_hue_do_not(self):
        box = dict(x=0, y=0, width=3, height=3)
        for rgb, expected in [((204, 204, 204), True), ((255, 255, 255), False),
                              ((255, 180, 180), False)]:
            with self.subTest(rgb=rgb):
                image = Image.new('RGB', (4, 4), 'white')
                image.putpixel((1, 1), rgb)
                self.assertEqual(_foreground(image, box, '#000', '#fff'), expected)

    def test_fractional_theme_outline_is_not_required_to_have_opaque_core(self):
        image = Image.new('RGB', (4, 4), (240, 244, 248))
        image.putpixel((1, 1), (204, 210, 218))
        self.assertTrue(_foreground(image, dict(x=0, y=0, width=3, height=3),
                                    '#384756', '#f0f4f8'))

    def test_rows_allow_explicit_and_soft_breaks_but_preserve_missing_text(self):
        def run(text, y):
            return dict(text=text, font_size=14, points=[dict(x=0, y=y)])
        self.assertTrue(_text_matches([run('First', 10), run('Second', 31)], 'First Second'))
        self.assertTrue(_text_matches([run('中文', 10), run('换行', 31)], '中文换行'))
        self.assertFalse(_text_matches([run('First', 10), run('Second', 31)], 'First Lost Second'))
        self.assertFalse(_text_matches([run('First', 10)], 'First Second'))

    def test_adjacent_style_runs_do_not_invent_word_spaces(self):
        runs = [dict(text=t, font_size=14, points=[dict(x=i*10, y=10)])
                for i, t in enumerate(('He', 'llo'))]
        self.assertTrue(_text_matches(runs, 'Hello'))
        self.assertFalse(_text_matches(runs, 'He llo'))


if __name__ == '__main__':
    unittest.main()
