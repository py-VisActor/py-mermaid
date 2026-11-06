"""Evidence requirements: retain failure/timeout streams, detect corruption, never conflate integrity with success."""
from __future__ import annotations

import base64
import hashlib
import contextlib
from functools import partial
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import urllib.request
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from run_support import Run, source_identity, verify_run
from build_f011_html_report import generate


class LoggingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_nonzero_exit_and_unicode_streams_survive(self):
        with Run("test", "failure", runs_dir=self.root, root=self.root) as run:
            result = run.command("negative", [sys.executable, "-c", "import sys;print('中文');print('error-only',file=sys.stderr);sys.exit(7)"])
        self.assertEqual(result["exitCode"], 7)
        self.assertEqual((run.path / result["stdout"]).read_text(encoding="utf-8").strip(), "中文")
        self.assertEqual((run.path / result["stderr"]).read_text(encoding="utf-8").strip(), "error-only")
        integrity = verify_run(run.path)
        self.assertEqual(integrity["integrityStatus"], "PASS")
        self.assertEqual(integrity["executionStatus"], "FAILED")
        self.assertEqual(integrity["functionalStatus"], "NOT_EVALUATED")

    def test_timeout_retains_partial_output_and_does_not_rewrite_stderr(self):
        with Run("test", "timeout", runs_dir=self.root, root=self.root) as run:
            result = run.command("slow", [sys.executable, "-c", "import time;print('started',flush=True);time.sleep(10)"], timeout=.3)
        self.assertEqual(result["exitCode"], 124)
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertIn("started", (run.path / result["stdout"]).read_text())
        self.assertEqual((run.path / result["stderr"]).read_bytes(), b"")
        self.assertEqual(verify_run(run.path)["executionStatus"], "FAILED")

    def test_launch_failure_and_context_exception_are_durable(self):
        with Run("test", "spawn-error", runs_dir=self.root, root=self.root) as first:
            result = first.command("missing", [str(self.root / "missing-executable")])
        self.assertEqual(result["exitCode"], 127)
        with self.assertRaisesRegex(ValueError, "invalid spec"):
            with Run("test", "exception", runs_dir=self.root, root=self.root) as second:
                raise ValueError("invalid spec")
        self.assertEqual(verify_run(second.path)["executionStatus"], "ERROR")
        self.assertIn("invalid spec", (second.path / "error.txt").read_text())

    def test_completed_runs_are_distinct_and_reject_further_writes(self):
        with Run("test", "same", runs_dir=self.root, root=self.root) as first:
            pass
        original = (first.path / "run.json").read_bytes()
        with Run("test", "same", runs_dir=self.root, root=self.root) as second:
            pass
        self.assertNotEqual(first.path, second.path)
        self.assertEqual((first.path / "run.json").read_bytes(), original)
        with self.assertRaises(RuntimeError):
            first.event("late")

    def test_corrupt_missing_and_added_artifacts_are_detected(self):
        with Run("test", "tamper", runs_dir=self.root, root=self.root) as run:
            run.command("echo", [sys.executable, "-c", "print('correct')"])
        stdout = run.path / run.data["commands"][0]["stdout"]
        stdout.write_text("wrong")
        self.assertEqual(verify_run(run.path)["integrityStatus"], "FAIL")
        stdout.unlink()
        self.assertTrue(any("Missing" in e for e in verify_run(run.path)["errors"]))
        (run.path / "surprise.txt").write_text("later")
        self.assertTrue(any("Unrecorded" in e for e in verify_run(run.path)["errors"]))

    def test_source_identity_ignores_generated_egg_info_and_cache(self):
        package = self.root / "src/py_mermaid"
        package.mkdir(parents=True)
        (package / "api.py").write_text("value = 1\n")
        first = source_identity(self.root)
        (self.root / "src/example.egg-info").mkdir()
        (self.root / "src/example.egg-info/PKG-INFO").write_text("generated")
        (package / "__pycache__").mkdir()
        (package / "__pycache__/api.pyc").write_bytes(b"cache")
        self.assertEqual(first, source_identity(self.root))
        (package / "api.py").write_text("value = 2\n")
        self.assertNotEqual(first, source_identity(self.root))

    def test_invalid_run_id_cannot_escape_runs_root(self):
        with self.assertRaises(ValueError):
            Run("../escape", "test", runs_dir=self.root, root=self.root)
        self.assertFalse((self.root.parent / "escape").exists())


class CLITests(unittest.TestCase):
    def test_record_propagates_actual_exit_and_creates_standard_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            completed = subprocess.run([sys.executable, str(ROOT / "tools/workflow.py"), "record", "--runs-dir", folder,
                                        "--scope", "test", "--", sys.executable, "-c", "raise SystemExit(9)"], capture_output=True)
            self.assertEqual(completed.returncode, 9)
            result = json.loads(completed.stdout)
            self.assertEqual(verify_run(Path(result["run"]))["executionStatus"], "FAILED")

    def test_batch_fail_fast_and_keep_going_have_separate_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan = {"schema": "py-mermaid-command-plan/v1", "steps": [
                {"name": "fail", "argv": ["{python}", "-c", "raise SystemExit(5)"]},
                {"name": "after", "argv": ["{python}", "-c", "print('continued')"]}]}
            path = root / "plan.json"
            path.write_text(json.dumps(plan))
            for keep, expected in ((False, 1), (True, 2)):
                args = [sys.executable, str(ROOT / "tools/workflow.py"), "batch", "--runs-dir", folder, "--plan", str(path)]
                if keep:
                    args.append("--keep-going")
                completed = subprocess.run(args, capture_output=True)
                self.assertEqual(completed.returncode, 5)
                run = json.loads((Path(json.loads(completed.stdout)["run"]) / "run.json").read_text())
                self.assertEqual(len(run["commands"]), expected)
                self.assertEqual(run["status"], "FAILED")

    def test_invalid_spec_has_error_log_and_no_html(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            spec = root / "bad.json"
            spec.write_text('{"schema":"wrong"}')
            result = subprocess.run([sys.executable, str(ROOT / "tools/workflow.py"), "report", "--spec", str(spec),
                                     "--runs-dir", str(root / "runs"), "--publish-dir", str(root / "published")], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            run = next((root / "runs").iterdir())
            self.assertEqual(verify_run(run)["executionStatus"], "FAILED")
            self.assertTrue((run / "commands/001-html-report/stderr.log").read_bytes())
            self.assertFalse((root / "published").exists())

    def test_render_dry_run_does_not_render_install_or_create_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(ROOT / "tools/workflow.py"), "render", "--profiles", "cpu",
                                     "--runs-dir", folder, "--dry-run"], capture_output=True)
            self.assertEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertFalse(data["installs"])
            self.assertEqual(len(data["steps"]), 2)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_local_server_serves_report_bytes_and_records_access_event(self):
        import serve_reports
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report = root / 'report.html'
            report.write_text('<!doctype html><title>report</title>', encoding='utf-8')
            capture = io.StringIO()
            with Run('test', 'http', runs_dir=root / 'logs', root=root) as run, contextlib.redirect_stdout(capture):
                serve_reports.ACTIVE_RUN = run
                try:
                    with ThreadingHTTPServer(('127.0.0.1', 0), partial(serve_reports.Handler, directory=str(root))) as server:
                        worker = threading.Thread(target=server.serve_forever)
                        worker.start()
                        try:
                            with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/report.html') as response:
                                self.assertEqual(response.status, 200)
                                self.assertEqual(response.read(), report.read_bytes())
                        finally:
                            server.shutdown()
                            worker.join(timeout=5)
                finally:
                    serve_reports.ACTIVE_RUN = None
            rows = [json.loads(line) for line in (run.path / 'events.ndjson').read_text().splitlines()]
            self.assertTrue(any(row['event'] == 'http_access' for row in rows))
            self.assertEqual(json.loads(capture.getvalue())['schema'], 'py-mermaid-event/v1')
            self.assertEqual(verify_run(run.path)['integrityStatus'], 'PASS')


class ReportContractTests(unittest.TestCase):
    def evidence(self, root):
        """Test-only source of a deliberate FAIL case; no product renderer runs."""
        final, oracle = root / "final", root / "oracle"
        pixels = final / "compare-cpu/example-pixels"
        pixels.mkdir(parents=True)
        oracle.mkdir()
        raw = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aHh0AAAAASUVORK5CYII=")
        sha = hashlib.sha256(raw).hexdigest()
        def write(path, obj): path.write_text(json.dumps(obj), encoding="utf-8")
        write(final / "summary.json", {"scope": "test", "sourceTreeSha256": "source", "tests": None})
        write(final / "source-candidate.json", {"sourceTreeSha256": "source", "files": {}})
        write(oracle / "identity.json", {"commit": "commit", "package": "test"})
        write(oracle / "manifest.json", {"browser": "test", "node": "test"})
        fixture = root / "fixtures.json"
        write(fixture, {"upstreamCommit": "commit", "cases": [{"id": "example", "text": "literal </script>", "nodes": [], "edges": []}]})
        write(oracle / "example.json", {"nodes": [], "edges": []})
        (oracle / "example.png").write_bytes(raw)
        result = {"backend": "cpu", "cases": [{"id": "example", "status": "FAIL", "errors": ["intentional missing content"], "pngSha256": sha}], "negativeCases": []}
        write(final / "compare-cpu/report.json", result)
        write(final / "compare-cpu/example.json", {"width": 1, "height": 1})
        (final / "compare-cpu/example.png").write_bytes(raw)
        metrics = {"inputs": {"reference": {"sha256": sha}, "candidate": {"sha256": sha}}, "artifacts": {}, "createdAtUtc": "2026-01-01T00:00:00Z"}
        for name in ("diff-raw.png", "mask-raw.png"):
            (pixels / name).write_bytes(raw)
            metrics["artifacts"][name] = {"sha256": sha}
        write(pixels / "report.json", metrics)
        return final, oracle, fixture

    def test_single_profile_failed_status_and_script_text_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            final, oracle, fixture = self.evidence(root)
            output = root / "report.html"
            result = generate(final, oracle, output, fixtures=fixture, profiles=["cpu"], scope="test", title="Reusable")
            self.assertEqual(result["profiles"], ["cpu"])
            html = output.read_text(encoding="utf-8")
            self.assertIn('"status":"FAIL"', html)
            self.assertIn('intentional missing content', html)
            self.assertIn('literal \\u003c/script>', html)
            self.assertNotIn('"text":"literal </script>"', html)
            manifest = json.loads(output.with_suffix('.manifest.json').read_text())
            self.assertFalse(manifest['installationVerificationDuringGeneration'])

    def test_mismatched_case_ids_and_png_fingerprints_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            final, oracle, fixture = self.evidence(root)
            (final / "compare-cpu/example.png").write_bytes(b"bad PNG")
            with self.assertRaisesRegex(ValueError, "PNG"):
                generate(final, oracle, root / "report.html", fixtures=fixture, profiles=["cpu"], scope="test")
            self.assertFalse((root / "report.html").exists())

    def test_expected_render_errors_preserve_parse_success_and_denominator(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            final,oracle,fixture=self.evidence(root)
            data=json.loads(fixture.read_text());data['renderErrorCases']=[{'id':'ellipse','text':'A(-x-)','code':'UPSTREAM_SHAPE_MISSING'}]
            fixture.write_text(json.dumps(data))
            report_path=final/'compare-cpu/report.json'
            report=json.loads(report_path.read_text());report['renderErrorCases']=[{'id':'ellipse','status':'PASS','parsed':True,'code':'UPSTREAM_SHAPE_MISSING'}]
            report_path.write_text(json.dumps(report))
            (oracle/'ellipse.render-error.json').write_text(json.dumps({'parsed':True,'renderRejected':True,'message':'upstream registry missing'}))
            output=root/'report.html'
            generate(final,oracle,output,fixtures=fixture,profiles=['cpu'],scope='test')
            manifest=json.loads(output.with_suffix('.manifest.json').read_text())
            self.assertEqual(manifest['renderErrorCases'],1)
            self.assertEqual(manifest['negativeCases'],0)
            self.assertIn('"renderError":true',output.read_text(encoding='utf-8'))
            report['renderErrorCases']=[];report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'denominator'):
                generate(final,oracle,root/'bad.html',fixtures=fixture,profiles=['cpu'],scope='test')

    def test_permanently_excluded_layout_is_preserved_as_policy_not_future_support(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            final, oracle, fixture = self.evidence(root)
            data = json.loads(fixture.read_text())
            data['unsupportedCases'] = [{'id': 'removed-layout', 'text': 'flowchart TD\nA',
                'config': {'layout': 'dagre'}, 'codes': ['UNSUPPORTED_CONFIG'],
                'scopeDisposition': 'excluded_by_user'}]
            fixture.write_text(json.dumps(data))
            report_path = final / 'compare-cpu/report.json'
            report = json.loads(report_path.read_text())
            report['unsupportedCases'] = [{'id': 'removed-layout', 'status': 'PASS', 'code': 'UNSUPPORTED_CONFIG'}]
            report_path.write_text(json.dumps(report))
            (oracle / 'removed-layout.unsupported.json').write_text(json.dumps({'accepted': True}))
            output = root / 'report.html'
            generate(final, oracle, output, fixtures=fixture, profiles=['cpu'], scope='test')
            html = output.read_text(encoding='utf-8')
            self.assertIn('"scopeDisposition":"excluded_by_user"', html)
            self.assertIn('已排除功能 · removed-layout', html)
            manifest = json.loads(output.with_suffix('.manifest.json').read_text())
            self.assertEqual(manifest['unsupportedCases'], 1)

    def test_preexisting_sidecar_never_leaves_partial_html_or_overwrites_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            final, oracle, fixture = self.evidence(root)
            output = root / "report.html"
            sidecar = output.with_suffix('.manifest.json')
            sidecar.write_text('historical evidence')
            with self.assertRaises(FileExistsError):
                generate(final, oracle, output, fixtures=fixture, profiles=["cpu"], scope="test")
            self.assertFalse(output.exists())
            self.assertEqual(sidecar.read_text(), 'historical evidence')

    def test_duplicate_or_traversal_case_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            final, oracle, fixture = self.evidence(root)
            data = json.loads(fixture.read_text())
            data['cases'][0]['id'] = '../escape'
            fixture.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                generate(final, oracle, root / "report.html", fixtures=fixture, profiles=["cpu"], scope="test")


if __name__ == '__main__':
    unittest.main()
