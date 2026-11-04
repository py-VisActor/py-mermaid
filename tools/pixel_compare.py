"""Compare static <=8-bit PNGs; diagnose cross-renderer pixels, never semantics.

Pillow is a development-only decoder/artifact writer. No Mermaid/native renderer
is imported. Inputs are never resized, aligned, cropped to hide content or edited.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import reduce
import hashlib
import html
import io
import json
import math
from pathlib import Path
import platform
import sys
import warnings

try:
    import PIL
    from PIL import Image, ImageChops, ImageDraw
except ImportError as error:
    print(json.dumps({'result': 'ERROR', 'message': 'Install development dependencies: python -m pip install -r tools/pixel_compare_requirements.txt',
                      'dependencyError': str(error)}))
    raise SystemExit(2)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_png(path: Path, max_pixels: int):
    raw = path.read_bytes()
    if raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR':
        raise ValueError('Only PNG inputs are supported: ' + str(path))
    if len(raw) < 29 or raw[24] not in (1, 2, 4, 8):
        raise ValueError('PNG bit depth must be <=8; 16-bit conversion would lose precision')
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > max_pixels:
                raise ValueError('Input exceeds --max-pixels')
            if getattr(image, 'n_frames', 1) != 1:
                raise ValueError('Animated PNG inputs are not supported')
            image.load()
            metadata = {'path': str(path.resolve()), 'sha256': sha256(raw),
                        'bytes': len(raw), 'size': list(image.size), 'mode': image.mode,
                        'bitDepth': raw[24],
                        'color': {'iccSha256': sha256(image.info['icc_profile']) if image.info.get('icc_profile') else None,
                                  'gamma': image.info.get('gamma'), 'srgb': image.info.get('srgb')},
                        'dpi': image.info.get('dpi')}
            return image.convert('RGBA'), metadata, raw


def metrics(a: Image.Image, b: Image.Image, threshold: int = 0):
    """All-channel pixel differences in the actual common region, no padding."""
    if a.size != b.size or a.mode != b.mode:
        raise ValueError('Metrics require matching sizes and modes')
    delta = ImageChops.difference(a, b)
    maximum = reduce(ImageChops.lighter, delta.split())
    histogram = maximum.histogram()
    mask = maximum.point([0] + [255] * 255)
    count = a.width * a.height
    channels = len(a.getbands())
    channel_histogram = delta.histogram()
    summed = [sum(channel_histogram[i * 256 + value] for i in range(channels)) for value in range(256)]
    mae = sum(value * n for value, n in enumerate(summed)) / (count * channels)
    mse = sum(value * value * n for value, n in enumerate(summed)) / (count * channels)
    different = count - histogram[0]
    return {'pixels': count, 'channels': channels, 'differentPixels': different,
            'differentRatio': different / count, 'mae': mae, 'rmse': math.sqrt(mse),
            'maxChannelDelta': max(i for i, n in enumerate(histogram) if n),
            'differenceBBox': list(mask.getbbox()) if mask.getbbox() else None,
            'threshold': threshold, 'aboveThresholdPixels': count - sum(histogram[:threshold + 1])}, maximum, mask


def composite(image: Image.Image, color: str):
    return Image.alpha_composite(Image.new('RGBA', image.size, color), image).convert('RGB')


def analyze(a: Image.Image, b: Image.Image, threshold=0, tile_size=64, max_pixels=16_000_000):
    if not 0 <= threshold <= 255 or tile_size < 1:
        raise ValueError('Invalid threshold or tile size')
    w, h = min(a.width, b.width), min(a.height, b.height)
    width, height = max(a.width, b.width), max(a.height, b.height)
    if width * height > max_pixels:
        raise ValueError('Union canvas exceeds --max-pixels')
    box = (0, 0, w, h)
    raw, max_delta, overlap_mask = metrics(a.crop(box), b.crop(box), threshold)
    coverage_a, coverage_b = Image.new('L', (width, height)), Image.new('L', (width, height))
    ImageDraw.Draw(coverage_a).rectangle((0, 0, a.width - 1, a.height - 1), fill=255)
    ImageDraw.Draw(coverage_b).rectangle((0, 0, b.width - 1, b.height - 1), fill=255)
    coverage = ImageChops.difference(coverage_a, coverage_b)
    coverage_count = coverage.histogram()[255]
    union_area = a.width * a.height + b.width * b.height - w * h
    mask = Image.new('L', (width, height))
    mask.paste(overlap_mask, (0, 0))
    mask = ImageChops.lighter(mask, coverage)
    above = max_delta.point([255 if i > threshold else 0 for i in range(256)])
    threshold_mask = Image.new('L', (width, height))
    threshold_mask.paste(above, (0, 0))
    threshold_mask = ImageChops.lighter(threshold_mask, coverage)
    changed_tiles = []
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            tile = (x, y, min(x + tile_size, width), min(y + tile_size, height))
            n = mask.crop(tile).histogram()[255]
            if n:
                changed_tiles.append({'bbox': list(tile), 'differentPixels': n,
                                      'coverageMismatchPixels': coverage.crop(tile).histogram()[255]})
    visible = {}
    visible_deltas = {}
    for background in ('white', 'black'):
        stats, delta, _ = metrics(composite(a.crop(box), background), composite(b.crop(box), background), threshold)
        visible[background] = stats
        visible_deltas[background] = delta
    result = {'alignment': 'top-left-only-no-resampling', 'sameDimensions': a.size == b.size,
              'overlapSize': [w, h], 'unionCanvasSize': [width, height],
              'overlapRawRGBA': raw, 'overlapCompositedRGB': visible,
              'coverageMismatchPixels': coverage_count, 'unionAreaPixels': union_area,
              'unionDifferentPixels': raw['differentPixels'] + coverage_count,
              'unionDifferentRatio': (raw['differentPixels'] + coverage_count) / union_area,
              'unionDifferenceBBox': list(mask.getbbox()) if mask.getbbox() else None,
              'tiles': {'tileSize': tile_size, 'changed': changed_tiles},
              'exactPixelMatch': a.size == b.size and raw['differentPixels'] == 0}
    return result, {'maximum': max_delta, 'mask': mask, 'thresholdMask': threshold_mask,
                    'coverage': coverage, 'visible': visible_deltas}


def heatmap(delta, size, coverage, gain, threshold):
    lookup = [0 if v <= threshold else min(v * gain, 255) for v in range(256)]
    signal = Image.new('L', size)
    signal.paste(delta.point(lookup), (0, 0))
    result = Image.merge('RGB', (signal, signal.point(lambda v: v // 4), Image.new('L', size)))
    result.paste((40, 120, 255), (0, 0), coverage)
    return result


def report_html(report):
    stats = report['comparison']
    title = html.escape(report['result'])
    summary = html.escape(json.dumps({'mode': report['mode'], 'comparison': stats,
                                      'warnings': report['warnings']}, ensure_ascii=False, indent=2))
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Pixel comparison — {title}</title><style>
body{{font:15px system-ui;margin:24px;background:#f6f8fb;color:#172033}}section{{background:white;padding:16px;margin:16px 0;border-radius:8px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}}img{{max-width:100%;height:auto;image-rendering:auto}}
.scroll{{overflow:auto;background:repeating-conic-gradient(#ddd 0% 25%,white 0% 50%) 0/16px 16px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}
.overlay{{position:relative;width:{stats['unionCanvasSize'][0]}px;height:{stats['unionCanvasSize'][1]}px}}.overlay img{{position:absolute;left:0;top:0;max-width:none}}
</style><h1>{title}</h1><p>Pixel diagnostics do not establish functional parity. Original PNGs are preserved. No resize, crop, alignment optimization or color-profile conversion was applied.</p>
<section class="grid"><div><h2>Reference</h2><img src="reference.png"></div><div><h2>Candidate</h2><img src="candidate.png"></div><div><h2>RGBA heatmap</h2><img src="diff-raw.png"></div></section>
<section><h2>Overlay (view only)</h2><label>Candidate opacity <input type="range" min="0" max="100" value="50" oninput="document.getElementById('candidate').style.opacity=this.value/100"></label>
<div class="scroll"><div class="overlay"><img src="reference.png"><img id="candidate" src="candidate.png" style="opacity:.5"></div></div></section>
<section class="grid"><div><h2>Visible on white</h2><img src="diff-white.png"></div><div><h2>Visible on black</h2><img src="diff-black.png"></div><div><h2>Raw change mask</h2><img src="mask-raw.png"></div></section>
<p>Heatmap: black = no displayed signal, red/yellow = channel difference, blue = missing image coverage. Gain and display threshold affect visualization only; raw metrics remain unchanged. Thumbnails may be CSS-scaled; saved PNGs are not resampled.</p>
<section><h2>Metrics (0–255 channel units)</h2><pre>{summary}</pre><a href="report.json">Complete report and SHA256 manifest</a></section></html>'''


def run(args):
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    try:
        if args.mode == 'exact' and args.channel_threshold:
            raise ValueError('Exact mode requires --channel-threshold 0')
        a, am, ar = load_png(args.reference, args.max_pixels)
        b, bm, br = load_png(args.candidate, args.max_pixels)
        comparison, images = analyze(a, b, args.channel_threshold, args.tile_size, args.max_pixels)
        color_equal = am['color'] == bm['color']
        warn = []
        if not comparison['sameDimensions']:
            warn.append('Dimensions differ: overlap metrics and uncovered frame area are reported separately.')
        if not color_equal:
            warn.append('Color metadata differs; no ICC/gamma conversion performed. Color appearance requires context review.')
        if comparison['overlapRawRGBA']['differentPixels'] and not any(
                s['differentPixels'] for s in comparison['overlapCompositedRGB'].values()):
            warn.append('Raw RGBA differs but composites match: hidden transparent RGB values may differ.')
        matched = comparison['exactPixelMatch'] and color_equal
        result = 'DIAGNOSTIC_ONLY' if args.mode == 'diagnostic' else ('PIXEL_MATCH' if matched else 'PIXEL_MISMATCH_OR_COLOR_METADATA_DIFFERENCE')
        report = {'schema': 'py-mermaid-pixel-comparison/v1', 'createdAtUtc': datetime.now(timezone.utc).isoformat(),
                  'mode': args.mode, 'result': result, 'functionalStatus': 'NOT_EVALUATED',
                  'environmentIdentityVerified': False,
                  'inputs': {'reference': am, 'candidate': bm}, 'comparison': comparison,
                  'colorMetadataEqual': color_equal, 'warnings': warn,
                  'metricDefinition': 'Decoded <=8-bit unpremultiplied RGBA; overlap MAE/RMSE over all channels. White/black alpha composites in encoded channel space. No ICC/gamma conversion, SSIM or semantic comparison.',
                  'visualization': {'gain': args.gain, 'channelThreshold': args.channel_threshold},
                  'tool': {'python': platform.python_version(), 'pillow': PIL.__version__,
                           'platform': platform.platform(), 'command': sys.argv,
                           'maxPixels': args.max_pixels,
                           'scriptSha256': sha256(Path(__file__).read_bytes())}}
        (out / 'reference.png').write_bytes(ar)
        (out / 'candidate.png').write_bytes(br)
        size = tuple(comparison['unionCanvasSize'])
        heatmap(images['maximum'], size, images['coverage'], args.gain, args.channel_threshold).save(out / 'diff-raw.png')
        for color in ('white', 'black'):
            heatmap(images['visible'][color], size, images['coverage'], args.gain, args.channel_threshold).save(out / f'diff-{color}.png')
        images['mask'].save(out / 'mask-raw.png')
        images['thresholdMask'].save(out / 'mask-threshold.png')
        (out / 'report.html').write_text(report_html(report), encoding='utf-8', newline='\n')
        report['artifacts'] = {p.name: {'sha256': sha256(p.read_bytes()), 'bytes': p.stat().st_size}
                               for p in sorted(out.iterdir()) if p.is_file()}
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps({'result': result, 'functionalStatus': 'NOT_EVALUATED',
                          'report': str(out / 'report.json'), 'html': str(out / 'report.html'),
                          'unionDifferentPixels': comparison['unionDifferentPixels']}))
        return 0 if args.mode == 'diagnostic' or matched else 1
    except Exception as error:
        payload = {'schema': 'py-mermaid-pixel-comparison/v1', 'result': 'ERROR',
                   'errorType': type(error).__name__, 'message': str(error), 'functionalStatus': 'NOT_EVALUATED'}
        (out / 'error.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps(payload))
        return 2


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('Must be positive')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='New output directory; never overwritten')
    parser.add_argument('--mode', choices=['diagnostic', 'exact'], default='diagnostic')
    parser.add_argument('--channel-threshold', type=int, choices=range(256), default=0, metavar='0..255')
    parser.add_argument('--gain', type=positive, default=4)
    parser.add_argument('--tile-size', type=positive, default=64)
    parser.add_argument('--max-pixels', type=positive, default=16_000_000)
    args = parser.parse_args()
    try:
        return run(args)
    except OSError as error:
        print(json.dumps({'result': 'ERROR', 'message': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
