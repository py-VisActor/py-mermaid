"""Independent numeric and CLI controls for the generic PNG utility only."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import pixel_compare as pixel


class PixelMetricsTests(unittest.TestCase):
    def test_rgb_change_with_unchanged_alpha_has_correct_bbox_and_metrics(self):
        a = Image.new('RGBA', (2, 2), (0, 0, 0, 255))
        b = a.copy()
        b.putpixel((1, 0), (16, 0, 0, 255))
        stats, _, _ = pixel.metrics(a, b)
        self.assertEqual(stats['differentPixels'], 1)
        self.assertEqual(stats['differenceBBox'], [1, 0, 2, 1])
        self.assertEqual(stats['mae'], 1)
        self.assertEqual(stats['rmse'], 4)
        self.assertEqual(stats['maxChannelDelta'], 16)

    def test_hidden_transparent_rgb_is_reported_separately(self):
        a = Image.new('RGBA', (1, 1), (255, 0, 0, 0))
        b = Image.new('RGBA', (1, 1), (0, 255, 0, 0))
        stats, _ = pixel.analyze(a, b)
        self.assertEqual(stats['overlapRawRGBA']['differentPixels'], 1)
        for background in ('white', 'black'):
            self.assertEqual(stats['overlapCompositedRGB'][background]['differentPixels'], 0)

    def test_alpha_only_change_visible_on_white(self):
        a = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        b = Image.new('RGBA', (1, 1), (0, 0, 0, 255))
        stats, _ = pixel.analyze(a, b)
        self.assertEqual(stats['overlapRawRGBA']['differentPixels'], 1)
        self.assertEqual(stats['overlapCompositedRGB']['white']['differentPixels'], 1)
        self.assertEqual(stats['overlapCompositedRGB']['black']['differentPixels'], 0)

    def test_crossed_dimensions_do_not_count_neither_frame_corner(self):
        a = Image.new('RGBA', (2, 2))
        b = Image.new('RGBA', (3, 1))
        stats, _ = pixel.analyze(a, b)
        self.assertEqual(stats['overlapSize'], [2, 1])
        self.assertEqual(stats['unionAreaPixels'], 5)
        self.assertEqual(stats['coverageMismatchPixels'], 3)
        self.assertEqual(stats['unionDifferentRatio'], 3 / 5)
        self.assertFalse(stats['exactPixelMatch'])

    def test_display_threshold_never_changes_raw_metrics(self):
        a = Image.new('RGBA', (1, 1), (0, 0, 0, 255))
        b = Image.new('RGBA', (1, 1), (1, 0, 0, 255))
        stats, _ = pixel.analyze(a, b, threshold=4)
        self.assertEqual(stats['overlapRawRGBA']['differentPixels'], 1)
        self.assertEqual(stats['overlapRawRGBA']['aboveThresholdPixels'], 0)
        self.assertFalse(stats['exactPixelMatch'])

    def test_tile_report_localizes_small_change_despite_large_background(self):
        a = Image.new('RGBA', (128, 64), 'white')
        b = a.copy()
        b.putpixel((66, 4), (0, 0, 0, 255))
        stats, _ = pixel.analyze(a, b, tile_size=64)
        self.assertEqual(stats['tiles']['changed'], [
            {'bbox': [64, 0, 128, 64], 'differentPixels': 1, 'coverageMismatchPixels': 0}])

    def test_union_budget_is_enforced(self):
        with self.assertRaisesRegex(ValueError, 'Union canvas'):
            pixel.analyze(Image.new('RGBA', (10, 1)), Image.new('RGBA', (1, 10)), max_pixels=20)


class PixelCLITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.a = self.root / 'a.png'
        self.b = self.root / 'b.png'
        Image.new('RGBA', (3, 2), 'white').save(self.a)
        Image.new('RGBA', (3, 2), 'black').save(self.b)

    def cli(self, name, mode='diagnostic', *extra):
        out = self.root / name
        result = subprocess.run([sys.executable, str(ROOT / 'tools/pixel_compare.py'),
                                 '--reference', str(self.a), '--candidate', str(self.b),
                                 '--out', str(out), '--mode', mode, *extra],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return result, out

    def test_diagnostic_reports_difference_but_no_functional_pass(self):
        original = self.a.read_bytes()
        p, out = self.cli('diagnostic')
        self.assertEqual(p.returncode, 0, p.stdout)
        report = json.loads((out / 'report.json').read_text('utf-8'))
        self.assertEqual(report['result'], 'DIAGNOSTIC_ONLY')
        self.assertEqual(report['functionalStatus'], 'NOT_EVALUATED')
        self.assertEqual(report['comparison']['unionDifferentPixels'], 6)
        self.assertEqual((out / 'reference.png').read_bytes(), original)
        self.assertEqual(self.a.read_bytes(), original)
        for name, artifact in report['artifacts'].items():
            self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), artifact['sha256'])

    def test_exact_mismatch_returns_one_and_match_returns_zero(self):
        p, _ = self.cli('different', 'exact')
        self.assertEqual(p.returncode, 1, p.stdout)
        self.b.write_bytes(self.a.read_bytes())
        p, out = self.cli('equal', 'exact')
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(json.loads((out / 'report.json').read_text('utf-8'))['result'], 'PIXEL_MATCH')

    def test_exact_rejects_tolerance(self):
        p, out = self.cli('invalid-threshold', 'exact', '--channel-threshold', '2')
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertEqual(json.loads((out / 'error.json').read_text('utf-8'))['result'], 'ERROR')

    def test_existing_output_is_never_overwritten(self):
        out = self.root / 'existing'
        out.mkdir()
        sentinel = out / 'sentinel'
        sentinel.write_text('keep', encoding='utf-8')
        p, _ = self.cli('existing')
        self.assertEqual(p.returncode, 2)
        self.assertEqual(sentinel.read_text('utf-8'), 'keep')
        self.assertEqual(set(p.name for p in out.iterdir()), {'sentinel'})

    def test_different_color_metadata_prevents_false_exact_match(self):
        info = PngImagePlugin.PngInfo()
        info.add(b'gAMA', struct.pack('>I', 45455))
        Image.new('RGBA', (3, 2), 'white').save(self.b, pnginfo=info)
        p, out = self.cli('gamma', 'exact')
        self.assertEqual(p.returncode, 1, p.stdout)
        report = json.loads((out / 'report.json').read_text('utf-8'))
        self.assertTrue(report['comparison']['exactPixelMatch'])
        self.assertFalse(report['colorMetadataEqual'])

    def test_jpeg_rejected_with_error_receipt(self):
        Image.new('RGB', (1, 1)).save(self.b, format='JPEG')
        p, out = self.cli('jpeg')
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn('Only PNG', json.loads((out / 'error.json').read_text('utf-8'))['message'])

    def test_16_bit_precision_loss_is_rejected(self):
        Image.new('I;16', (1, 1)).save(self.b)
        p, _ = self.cli('sixteen-bit')
        self.assertEqual(p.returncode, 2, p.stdout)

    def test_animated_png_rejected(self):
        Image.new('RGBA', (1, 1), 'red').save(self.b, save_all=True,
                                            append_images=[Image.new('RGBA', (1, 1), 'blue')])
        p, out = self.cli('animated')
        self.assertEqual(p.returncode, 2, p.stdout)
        self.assertIn('Animated', json.loads((out / 'error.json').read_text('utf-8'))['message'])

    def test_palette_png_decodes_without_false_difference(self):
        palette = Image.new('P', (3, 2))
        palette.putpalette([255, 255, 255] + [0, 0, 0] * 255)
        palette.save(self.b)
        p, out = self.cli('palette', 'exact')
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertTrue(json.loads((out / 'report.json').read_text('utf-8'))['comparison']['exactPixelMatch'])

    def test_missing_pillow_is_tool_error_not_pixel_mismatch(self):
        script = str(ROOT / 'tools/pixel_compare.py')
        code = ("import builtins,runpy\noriginal=builtins.__import__\n"
                "def blocked(name,*a,**k):\n"
                " if name=='PIL' or name.startswith('PIL.'):raise ImportError('synthetic missing Pillow')\n"
                " return original(name,*a,**k)\n"
                "builtins.__import__=blocked\n"
                f"runpy.run_path({script!r},run_name='__main__')\n")
        result = subprocess.run([sys.executable, '-c', code], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(json.loads(result.stdout)['result'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
