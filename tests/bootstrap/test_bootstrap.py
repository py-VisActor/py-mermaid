"""Source integrity regression tests, including independent negative controls."""
import contextlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import upstream
from validate_bootstrap import check, local_file


@contextlib.contextmanager
def altered_document(relative, transform):
    """Yield a temporary source view with one corrupt JSON file; never edit repo."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in ("src", "scripts", "examples", "tests", "docs", "references", "tools"):
            shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
        for path in ROOT.glob("*"):
            if path.is_file():
                shutil.copy2(path, root / path.name)
        target = root / relative
        document = json.loads(target.read_text(encoding="utf-8"))
        transform(document)
        target.write_text(json.dumps(document), encoding="utf-8")
        yield root


class BootstrapTests(unittest.TestCase):
    def test_current_source(self):
        self.assertEqual(check()["errors"], [])

    def test_newer_and_external_diagrams_are_in_denominator(self):
        source = json.loads((ROOT / "references/spec-inventory.json").read_text(encoding="utf-8"))
        ids = {item["id"] for item in source["detectors"]}
        self.assertTrue({"agentflow", "swimlane", "railroadEbnf", "railroadAbnf", "railroadPeg", "zenuml", "flowchart-elk"} <= ids)

    def test_cannot_drop_diagram(self):
        with altered_document("docs/compatibility.json", lambda doc: doc["diagrams"].pop()) as root:
            self.assertIn("Diagram coverage denominator differs from source detectors", check(root)["errors"])

    def test_cannot_change_canvas_pin(self):
        with altered_document("references/upstream.lock.json", lambda doc: doc["canvas"].update(version="0.0.0")) as root:
            self.assertIn("Canvas dependency differs from lock", check(root)["errors"])

    def test_cannot_claim_rendering_without_evidence(self):
        with altered_document("docs/compatibility.json", lambda doc: doc["diagrams"][0].update(canvas="canvas_verified")) as root:
            self.assertTrue(any("Verified stage requires real evidence" in e for e in check(root)["errors"]))

    def test_fixture_cannot_escape_directory(self):
        self.assertFalse(local_file(ROOT / "tests/fixtures", "../../README.md"))
        with altered_document("tests/fixtures/cases.json", lambda doc: doc["cases"][0].update(input="../../README.md")) as root:
            self.assertTrue(any("Invalid fixture" in e for e in check(root)["errors"]))

    def test_cannot_attach_nonexistent_evidence(self):
        def corrupt(doc):
            doc["diagrams"][0].update(canvas="canvas_verified", evidence=[{"path": "missing.json", "sha256": "0" * 64}])
        with altered_document("docs/compatibility.json", corrupt) as root:
            self.assertTrue(any("Invalid evidence file" in e for e in check(root)["errors"]))

    def test_image_hash_corruption_detected(self):
        with altered_document("docs/assets/manifest.json", lambda doc: doc.update(sha256="0" * 64)) as root:
            self.assertIn("Example image hash differs", check(root)["errors"])

    def test_missing_doc_link_detected(self):
        with altered_document("docs/compatibility.json", lambda doc: None) as root:
            with (root / "README.md").open("a", encoding="utf-8") as stream:
                stream.write("\n[broken](does-not-exist.md)\n")
            self.assertTrue(any("Missing documentation link" in e for e in check(root)["errors"]))

    def test_upstream_wrong_commit_rejected(self):
        with patch.object(upstream, "git", return_value=b"wrong-commit\n"):
            with self.assertRaisesRegex(ValueError, "HEAD differs"):
                upstream.verify(Path("unused"), {"commit": "expected"})

    def test_upstream_dirty_tree_rejected(self):
        with patch.object(upstream, "git", side_effect=[b"expected\n", b" M source.ts\n"]):
            with self.assertRaisesRegex(ValueError, "dirty"):
                upstream.verify(Path("unused"), {"commit": "expected"})

    def test_upstream_wrong_hash_rejected(self):
        lock = {"commit": "expected", "sha256": {"source.ts": "0" * 64}}
        with patch.object(upstream, "git", side_effect=[b"expected\n", b"", b"changed source"]):
            with self.assertRaisesRegex(ValueError, "hash differs"):
                upstream.verify(Path("unused"), lock)


if __name__ == "__main__":
    unittest.main()
