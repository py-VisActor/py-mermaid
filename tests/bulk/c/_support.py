"""Independent assertion helpers; no product invocation at import/discovery."""
import io
import math
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]


def semantic(source,config=None):
    from py_mermaid import parse
    return parse(source,config=config)


def walk_statements(statements):
    for s in statements:
        yield s
        yield from walk_statements(s.children)
        for _,children in s.sections:yield from walk_statements(children)


def assert_png(test,result):
    test.assertTrue(result.data.startswith(b'\x89PNG\r\n\x1a\n'))
    image=Image.open(io.BytesIO(result.data)).convert('RGB')
    test.assertEqual(image.size,(result.width,result.height))
    pixels=list(image.getdata())
    test.assertGreater(sum(max(p)-min(p)>25 or min(p)<180 for p in pixels),12)
    test.assertTrue(all(math.isfinite(v) for event in result.trace if event.box for v in (event.box.x,event.box.y,event.box.width,event.box.height)))
    return image


def assert_text_pixels(test,image,event):
    """Text's actual expected ROI must contain ink; blank/no-op is rejected."""
    test.assertIsNotNone(event.box)
    b=event.box;l=max(0,math.floor(b.x));t=max(0,math.floor(b.y));r=min(image.width,math.ceil(b.x+b.width));bottom=min(image.height,math.ceil(b.y+b.height))
    test.assertGreater(r-l,0);test.assertGreater(bottom-t,0)
    pixels=list(image.crop((l,t,r,bottom)).getdata())
    test.assertGreater(sum(min(p)<180 for p in pixels),1)
