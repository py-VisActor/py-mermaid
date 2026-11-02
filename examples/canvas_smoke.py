"""Check the real Canvas dependency; this is NOT a Mermaid renderer.

Writes a fresh output directory with a PNG and environment/metric/hash report.
Canvas and Context stay on this process's calling thread; only bytes are saved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import struct
import sys


def main() -> None:
    """Draw measured text and a rectangle; assert interior RGBA, PNG dimensions.

    --out is a new directory. --backend auto preserves upstream policy, cpu
    uses the public setter, gpu requires engine.renderer == GPU. Failures
    propagate; no fonts, Node process, or external resources are downloaded.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--backend", choices=["auto", "cpu", "gpu"], default="auto")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    import py_skia_canvas as skia

    if skia.__version__ != "0.1.0a18":
        raise RuntimeError("Expected pinned py-skia-canvas==0.1.0a18")
    canvas = skia.Canvas(360, 140)
    if args.backend == "cpu":
        canvas.gpu = False
    ctx = canvas.getContext("2d")
    ctx.fillStyle = "white"
    ctx.fillRect(0, 0, 360, 140)
    ctx.fillStyle = "#2878d9"
    ctx.fillRect(20, 20, 320, 50)
    ctx.fillStyle = "#16243a"
    ctx.font = "20px sans-serif"
    metrics = ctx.measureText("py-mermaid / Canvas backend")
    ctx.fillText("py-mermaid / Canvas backend", 20, 110)
    assert metrics.width > 0
    assert list(ctx.getImageData(25, 25, 1, 1).data) == [40, 120, 217, 255]
    assert list(ctx.getImageData(0, 0, 1, 1).data) == [255, 255, 255, 255]
    if args.backend in ("cpu", "gpu") and canvas.engine["renderer"] != args.backend.upper():
        raise RuntimeError(f"Requested {args.backend}; actual engine: {canvas.engine}")
    png = canvas.toBufferSync("png")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == (360, 140)
    (args.out / "canvas.png").write_bytes(png)
    report = {"status": "CANVAS_DEPENDENCY_SMOKE_PASSED", "mermaidSpecsPassed": 0,
              "canvasVersion": skia.__version__, "canvasModule": skia.__file__,
              "python": sys.version, "platform": platform.platform(),
              "requestedBackend": args.backend, "engine": canvas.engine,
              "textWidth": metrics.width, "pixels": [360, 140],
              "pngSha256": hashlib.sha256(png).hexdigest(),
              "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (args.out / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
