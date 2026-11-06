"""Strict report transport must not emit bare NaN/Infinity into JSON.parse."""
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from scene_codec import json_ready


class SceneCodecTests(unittest.TestCase):
    def test_nested_nonfinite_js_scalars_are_explicit_and_valid_json(self):
        source={'variables':(('limit',math.inf),('other',-math.inf),('nan',math.nan)), 'finite':1.5}
        encoded=json.dumps(json_ready(source),allow_nan=False)
        decoded=json.loads(encoded)
        self.assertEqual(decoded['variables'],[['limit',{'$jsNumber':'Infinity'}],['other',{'$jsNumber':'-Infinity'}],['nan',{'$jsNumber':'NaN'}]])
        self.assertEqual(decoded['finite'],1.5)
        self.assertTrue(math.isinf(source['variables'][0][1]))

    def test_markup_and_literal_tag_objects_are_not_reinterpreted(self):
        source={'text':'</script><b>原文</b>','object':{'$jsNumber':'literal'}}
        self.assertEqual(json_ready(source),source)


if __name__=='__main__':unittest.main()
