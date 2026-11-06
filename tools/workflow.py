"""Reusable evidence commands: record, batch, report, render and verify. Never installs dependencies."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from run_support import ROOT, Run, file_identity, source_identity, verify_run, write_json


def resolve(path: Path) -> Path:
    return (ROOT / path).resolve()


def load_plan(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema") != "py-mermaid-command-plan/v1" or not isinstance(plan.get("steps"), list) or not plan["steps"]:
        raise ValueError("Unsupported or empty command plan")
    return plan


def expand(value: str, run: Run, python: str) -> str:
    for name, replacement in (("{repo}", str(ROOT)), ("{run}", str(run.path)), ("{python}", python)):
        value = value.replace(name, replacement)
    return value


def publish(run: Run, directory: Path | None) -> Path:
    source = run.path / "report/index.html"
    if directory is None:
        return source
    target = resolve(directory) / run.id
    target.mkdir(parents=True, exist_ok=False)
    for name in ("index.html", "index.manifest.json"):
        shutil.copyfile(run.path / "report" / name, target / name)
    run.data["publishedReport"] = str(target / "index.html")
    run.data["publishedArtifacts"] = {str(target / name): file_identity(target / name)
                                      for name in ("index.html", "index.manifest.json")}
    run.event("report_published", path=str(target / "index.html"))
    return target / "index.html"


def report_command(run: Run, spec: Path, python: str, publish_dir: Path | None) -> int:
    spec = resolve(spec)
    run.input(spec)
    shutil.copyfile(spec, run.path / "artifacts/report-spec.json")
    result = run.command("html-report", [python, str(ROOT / "tools/build_f011_html_report.py"),
                                        "--spec", str(spec), "--out", str(run.path / "report/index.html")])
    if result["exitCode"] == 0:
        target = publish(run, publish_dir)
        run.data["result"] = {"report": str(target), "reportManifest": str(run.path / "report/index.manifest.json")}
        run.event("report_generated", **run.data["result"])
    return result["exitCode"]


def render_plan(args) -> list[dict]:
    profiles = args.profiles
    if not profiles or len(set(profiles)) != len(profiles):
        raise ValueError("Profiles must be nonempty and unique")
    for profile in profiles:
        if profile not in ("cpu", "auto", "gpu"):
            raise ValueError(f"Unsupported product backend: {profile}")
    steps = [{"name": "official", "argv": [args.node, "{repo}/tools/oracle/f011_capture.cjs",
              "--fixtures", "{run}/artifacts/cases.json", "--out", "{run}/artifacts/oracle"]}]
    for profile in profiles:
        steps.append({"name": f"compare-{profile}", "argv": ["{python}", "{repo}/tools/f011_validate.py",
                      "--fixtures", "{run}/artifacts/cases.json", "--oracle", "{run}/artifacts/oracle",
                      "--out", f"{{run}}/artifacts/compare-{profile}", "--backend", profile],
                      "env": {"PYTHONPATH": "{repo}/src"}})
    if args.scope=='F01.4':
        steps.append({'name':'static-format-samples','argv':['{python}','{repo}/tools/export_static_samples.py',
            '--out','{run}/artifacts/static-exports','--backend','cpu'],'env':{'PYTHONPATH':'{repo}/src'}})
    return steps


def execute_steps(run: Run, steps: list[dict], python: str, *, keep_going: bool = False) -> int:
    first_failure = 0
    for step in steps:
        if not isinstance(step.get("argv"), list) or not all(isinstance(v, str) for v in step["argv"]):
            raise ValueError("Every step requires an argv string array")
        env = {k: expand(v, run, python) for k, v in step.get("env", {}).items()}
        result = run.command(step["name"], [expand(v, run, python) for v in step["argv"]],
                             cwd=Path(expand(step.get("cwd", "{repo}"), run, python)), env=env,
                             timeout=step.get("timeoutSeconds"))
        if result["exitCode"] != 0:
            first_failure = first_failure or result["exitCode"]
            if not keep_going:
                break
    return first_failure


def render_command(run: Run, args) -> int:
    fixture_path = resolve(args.fixtures)
    run.input(fixture_path)
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    shutil.copyfile(fixture_path, run.path / "artifacts/cases.json")
    write_json(run.path / "artifacts/source-candidate.json", run.data["source"], exclusive=True)
    plan = render_plan(args)
    write_json(run.path / "artifacts/plan.json", {"steps": plan}, exclusive=True)
    code = execute_steps(run, plan, args.python)
    if code:
        return code
    if source_identity() != run.data["source"]:
        raise ValueError("Product source changed during rendering; do not combine different candidates")
    profiles = {}
    functional = "PASS"
    for profile in args.profiles:
        path = run.path / f"artifacts/compare-{profile}/report.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        profiles[profile] = {"positiveCases": len(result["cases"]), "negativeCases": len(result["negativeCases"]),
                             "renderErrorCases":len(result.get("renderErrorCases",[])),
                             "unsupportedCases":len(result.get("unsupportedCases",[]))}
        if result["functionalStatus"] != "PASS":
            functional = "FAIL"
    summary = {"scope": args.scope, "sourceTreeSha256": run.data["source"]["sourceTreeSha256"],
               "wheelSha256": None, "tests": None, "profiles": profiles,
               "functionalStatus": functional, "installationValidation": {"status": "NOT_EXECUTED"},
               "note": "Source-render run; unit tests and package installation were not executed"}
    write_json(run.path / "artifacts/summary.json", summary, exclusive=True)
    spec = {"schema": "py-mermaid-render-report-spec/v1", "scope": args.scope, "title": args.title,
            "final": str(run.path / "artifacts"), "oracle": str(run.path / "artifacts/oracle"),
            "fixtures": str(run.path / "artifacts/cases.json"), "profiles": args.profiles}
    if args.default_case is not None:
        spec['defaultCase']=args.default_case
    if args.scope=='F01.4':spec['exportSamples']=str(run.path/'artifacts/static-exports')
    spec_path = run.path / "artifacts/generated-report-spec.json"
    write_json(spec_path, spec, exclusive=True)
    run.data["functionalStatus"] = functional
    return report_command(run, spec_path, args.python, args.publish_dir)


def parser() -> argparse.ArgumentParser:
    main = argparse.ArgumentParser(description=__doc__)
    commands = main.add_subparsers(dest="action", required=True)

    def common(command):
        command.add_argument("--scope")
        command.add_argument("--runs-dir", type=Path, default=ROOT / "test-runs")
        command.add_argument("--python", default=sys.executable)

    record = commands.add_parser("record", help="Record one argv command, retaining failures and separate raw streams")
    common(record)
    record.add_argument("--name", default="command")
    record.add_argument("--cwd", type=Path, default=ROOT)
    record.add_argument("--timeout", type=float)
    record.add_argument("--input", type=Path, action="append", default=[])
    record.add_argument("argv", nargs=argparse.REMAINDER)
    batch = commands.add_parser("batch", help="Execute a versioned plan; no shell expansion")
    common(batch)
    batch.add_argument("--plan", type=Path, required=True)
    batch.add_argument("--keep-going", action="store_true")
    batch.add_argument("--dry-run", action="store_true")
    report = commands.add_parser("report", help="Read existing evidence and generate/publish a new HTML report only")
    common(report)
    report.add_argument("--spec", type=Path, default=ROOT / "tools/report_specs/f011-baseline.json")
    report.add_argument("--publish-dir", type=Path, default=ROOT / "reports")
    render = commands.add_parser("render", help="Explicitly recapture A, render/compare B and build HTML; never installs")
    common(render)
    render.add_argument("--fixtures", type=Path, default=ROOT / "tests/f011/cases.json")
    render.add_argument("--profiles", nargs="+", default=["cpu", "auto", "gpu"])
    render.add_argument("--node", default="node")
    render.add_argument("--title", default="基础流程图 · 渲染效果对比")
    render.add_argument("--default-case", help="Initially selected positive fixture ID in the generated report")
    render.add_argument("--publish-dir", type=Path, default=ROOT / "reports")
    render.add_argument("--dry-run", action="store_true")
    verify = commands.add_parser("verify", help="Verify stored run artifact hashes; does not rerun commands")
    verify.add_argument("--run", type=Path, required=True)
    return main


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    run = None
    try:
        if args.action == "verify":
            result = verify_run(args.run)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["integrityStatus"] == "PASS" else 1
        if args.scope is None:
            args.scope = "F01.1" if args.action == "render" else "adhoc"
            path = args.spec if args.action == "report" else args.plan if args.action == "batch" else None
            if path is not None:
                try:
                    args.scope = json.loads(resolve(path).read_text(encoding="utf-8")).get("scope", args.scope)
                except (ValueError, OSError):
                    pass  # The actual operation records the invalid input in its run.
        if args.action == "render" and args.dry_run:
            print(json.dumps({"status": "DRY_RUN", "steps": render_plan(args), "installs": False}, ensure_ascii=False, indent=2))
            return 0
        plan = None
        if args.action == "batch" and args.dry_run:
            plan = load_plan(resolve(args.plan))
            print(json.dumps({"status": "DRY_RUN", "steps": plan["steps"]}, ensure_ascii=False, indent=2))
            return 0
        run = Run(args.scope, args.action, runs_dir=resolve(args.runs_dir))
        with run:
            if args.action == "record":
                for path in args.input:
                    run.input(resolve(path))
                command = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
                code = run.command(args.name, command, cwd=resolve(args.cwd), timeout=args.timeout)["exitCode"]
            elif args.action == "batch":
                run.input(resolve(args.plan))
                plan = load_plan(resolve(args.plan))
                shutil.copyfile(resolve(args.plan), run.path / "artifacts/plan.json")
                for path in plan.get("inputs", []):
                    run.input(Path(expand(path, run, args.python)))
                code = execute_steps(run, plan["steps"], args.python, keep_going=args.keep_going)
            elif args.action == "report":
                code = report_command(run, args.spec, args.python, args.publish_dir)
            else:
                code = render_command(run, args)
        print(json.dumps({"runId": run.id, "status": run.data["status"], "run": str(run.path),
                          "manifest": str(run.path / "run.json"), **run.data.get("result", {})}, ensure_ascii=False, indent=2))
        return code if 0 <= code <= 255 else 1
    except KeyboardInterrupt:
        print(json.dumps({"status": "INTERRUPTED", "run": str(run.path) if run else None}), file=sys.stderr)
        return 130
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc), "run": str(run.path) if run else None}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
