"""Build a self-contained HTML viewer from existing F01.1 evidence only.

No render, install, browser capture, image processing or product tests run here.
PNG bytes and diagnostic reports must match the recorded SHA256 identities.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import struct

from run_support import safe_id

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "tools/report_specs/f011-baseline.json"


def load_spec(path: Path) -> dict:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("schema") != "py-mermaid-render-report-spec/v1":
        raise ValueError("Unsupported report spec schema")
    for name in ("scope", "title", "final", "oracle", "fixtures", "profiles"):
        if name not in spec:
            raise ValueError(f"Report spec is missing {name}")
    safe_id(spec["scope"])
    for name in ("final", "oracle", "fixtures", "template", "exportSamples"):
        if name in spec:
            spec[name] = (ROOT / spec[name]).resolve()
    return spec


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate(final: Path, oracle: Path, output: Path, *, fixtures: Path | None = None,
             profiles: list[str] | None = None, scope: str = "F01.1", title: str = "渲染效果对比",
             case_titles: dict | None = None, default_case: str | None = None,
             template: Path | None = None, export_samples: Path | None = None) -> dict:
    """Read and verify evidence, embed original bytes, then create a new file."""
    sources: dict[str, dict] = {}
    if output.exists() or output.with_suffix(".manifest.json").exists():
        raise FileExistsError(f"Report or manifest already exists: {output}")
    profiles = profiles if profiles is not None else ["cpu", "auto", "gpu"]
    if not profiles or len(profiles) != len(set(profiles)):
        raise ValueError("Profiles must be nonempty and unique")
    for profile in profiles:
        safe_id(profile)
    case_titles = case_titles or {}

    def read(path: Path) -> bytes:
        raw = path.read_bytes()
        try:
            label = path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            label = path.resolve().as_posix()
        sources[label] = {"sha256": digest(raw), "bytes": len(raw)}
        return raw

    def doc(path: Path) -> dict:
        return json.loads(read(path))

    def png(path: Path, expected: str | None = None) -> dict:
        raw = read(path)
        if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Not a PNG: {path}")
        if expected is not None and digest(raw) != expected:
            raise ValueError(f"PNG does not match recorded evidence: {path}")
        width, height = struct.unpack(">II", raw[16:24])
        return {"url": "data:image/png;base64," + base64.b64encode(raw).decode("ascii"),
                "width": width, "height": height, "sha256": digest(raw), "bytes": len(raw)}

    summary = doc(final / "summary.json")
    candidate = doc(final / "source-candidate.json")
    identity = doc(oracle / "identity.json")
    official_manifest = doc(oracle / "manifest.json")
    fixture = doc(fixtures or ROOT / "tests/f011/cases.json")
    identifiers = [case["id"] for case in fixture["cases"] + fixture.get("negativeCases", []) + fixture.get("renderErrorCases", []) + fixture.get('unsupportedCases',[])]
    if not fixture["cases"] or len(identifiers) != len(set(identifiers)):
        raise ValueError("Cases must be nonempty with unique positive/negative IDs")
    for identifier in identifiers:
        safe_id(identifier)
    if fixture.get("upstreamCommit") != identity.get("commit"):
        raise ValueError("Fixture and oracle upstream commits differ")
    if summary.get("scope", scope) != scope:
        raise ValueError("Summary and report spec scopes differ")
    if default_case is not None and default_case not in [c["id"] for c in fixture["cases"]]:
        raise ValueError("Default case is not in the positive case list")
    reports = {profile: doc(final / f"compare-{profile}/report.json") for profile in profiles}
    for profile, report in reports.items():
        for key, expected in (("cases", fixture["cases"]), ("negativeCases", fixture.get("negativeCases", [])), ("renderErrorCases",fixture.get("renderErrorCases",[])), ('unsupportedCases',fixture.get('unsupportedCases',[]))):
            actual_ids = [row["id"] for row in report.get(key, [])]
            if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != {row["id"] for row in expected}:
                raise ValueError(f"Case denominator mismatch: {profile}/{key}")
    data = {"generatedAt": datetime.now(timezone(timedelta(hours=8), "Asia/Shanghai")).isoformat(timespec="seconds"),
            "summary": summary, "identity": identity,
            "browser": official_manifest["browser"], "node": official_manifest["node"],
            "scope": scope, "title": title, "defaultCase": default_case or fixture["cases"][0]["id"],
            "cases": [], "negatives": [], "profiles": list(profiles),
            "evidenceTime": None, "renderedDuringReportGeneration": False,
            "installationVerificationDuringReportGeneration": False}
    if summary["sourceTreeSha256"] != candidate["sourceTreeSha256"]:
        raise ValueError("Source identity mismatch between final summary and candidate")
    data["sourceFilesStillMatch"] = all((ROOT / name).is_file() and digest((ROOT / name).read_bytes()) == sha
                                        for name, sha in candidate["files"].items())
    for case in fixture["cases"]:
        identifier = case["id"]
        item = {**case, "title": case.get("title", case_titles.get(identifier, identifier)),
                "official": doc(oracle / f"{identifier}.json"), "profiles": {}}
        official_png = png(oracle / f"{identifier}.png")
        item["officialImage"] = official_png
        for profile in profiles:
            directory = final / f"compare-{profile}"
            result = next(row for row in reports[profile]["cases"] if row["id"] == identifier)
            scene = doc(directory / f"{identifier}.json")
            pixels = directory / f"{identifier}-pixels"
            metrics = doc(pixels / "report.json")
            if metrics["inputs"]["reference"]["sha256"] != official_png["sha256"]:
                raise ValueError(f"Official PNG differs from pixel-report reference: {identifier}/{profile}")
            image = png(directory / f"{identifier}.png", result["pngSha256"])
            if metrics["inputs"]["candidate"]["sha256"] != image["sha256"]:
                raise ValueError(f"Candidate PNG differs from pixel-report input: {identifier}/{profile}")
            if [image["width"], image["height"]] != [scene["width"], scene["height"]]:
                raise ValueError(f"Encoded dimensions differ from scene: {identifier}/{profile}")
            diagnostics = {name: png(pixels / name, metrics["artifacts"][name]["sha256"])
                           for name in ("diff-raw.png", "mask-raw.png")}
            item["profiles"][profile] = {"result": result, "scene": scene, "image": image,
                                           "metrics": metrics, "diagnostics": diagnostics}
            if data["evidenceTime"] is None:
                data["evidenceTime"] = metrics["createdAtUtc"]
        data["cases"].append(item)
    for case in fixture.get("negativeCases", []):
        identifier = case["id"]
        data["negatives"].append({**case, "title": case.get("title", case_titles.get(identifier, identifier)),
                                  "official": doc(oracle / f"{identifier}.negative.json"),
                                  "profiles": {profile: next(row for row in reports[profile]["negativeCases"]
                                                              if row["id"] == identifier) for profile in profiles}})
    for case in fixture.get("renderErrorCases", []):
        identifier=case['id']
        data['negatives'].append({**case,'renderError':True,'title':case.get('title','上游渲染缺陷 · '+identifier),
                                 'official':doc(oracle/f'{identifier}.render-error.json'),
                                 'profiles':{profile:next(row for row in reports[profile]['renderErrorCases'] if row['id']==identifier) for profile in profiles}})
    for case in fixture.get('unsupportedCases',[]):
        identifier=case['id']
        label='已排除功能' if case.get('scopeDisposition')=='excluded_by_user' else '后续范围'
        data['negatives'].append({**case,'outsideScope':True,'title':case.get('title',label+' · '+identifier),
                                 'official':doc(oracle/f'{identifier}.unsupported.json'),
                                 'profiles':{profile:next(row for row in reports[profile]['unsupportedCases'] if row['id']==identifier) for profile in profiles}})
    data['exports']=[]
    if export_samples is not None:
        for sample in doc(export_samples/'manifest.json')['samples']:
            name=sample['file']
            if Path(name).name!=name:raise ValueError('Unsafe static export filename')
            raw=read(export_samples/name)
            if digest(raw)!=sample['sha256'] or len(raw)!=sample['bytes']:raise ValueError('Static export fingerprint mismatch')
            data['exports'].append({**sample,'url':'data:'+sample['mime']+';base64,'+base64.b64encode(raw).decode('ascii')})
    data["inputFilesVerified"] = len(sources)
    template_path = template or ROOT / "tools/templates/f011_comparison.html"
    template = template_path.read_text(encoding="utf-8")
    if template.count("__REPORT_DATA__") != 1:
        raise ValueError("Expected a single data placeholder in report template")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    html = template.replace("__REPORT_DATA__", payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(html)
    manifest = {"schema": "py-mermaid-render-report/v1", "generatedAt": data["generatedAt"],
                "report": output.as_posix(), "sha256": digest(output.read_bytes()),
                "positiveCases": len(data["cases"]), "negativeCases": len(fixture.get('negativeCases',[])),
                "renderErrorCases":len(fixture.get('renderErrorCases',[])),
                "unsupportedCases":len(fixture.get('unsupportedCases',[])),
                "scope": scope, "title": title, "profiles": list(profiles), "sourceCandidateSha256": summary["sourceTreeSha256"],
                "wheelSha256": summary.get("wheelSha256"), "inputs": sources,
                "generatorSha256": digest(Path(__file__).read_bytes()),
                "templateSha256": digest(template_path.read_bytes()),
                "renderedDuringGeneration": False, "installationVerificationDuringGeneration": False}
    with output.with_suffix(".manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {key: manifest[key] for key in ("report", "sha256", "positiveCases", "negativeCases", "profiles")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--final", type=Path)
    parser.add_argument("--oracle", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--profiles", nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    spec = load_spec(args.spec)
    print(json.dumps(generate(args.final or spec["final"], args.oracle or spec["oracle"], args.out,
                              fixtures=args.fixtures or spec["fixtures"], profiles=args.profiles or spec["profiles"],
                              scope=spec["scope"], title=spec["title"], case_titles=spec.get("caseTitles"),
                              default_case=spec.get("defaultCase"), template=spec.get("template"),
                              export_samples=spec.get('exportSamples')),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
