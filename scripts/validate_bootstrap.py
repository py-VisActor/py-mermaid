"""Validate local bootstrap structure, docs and inventories without Canvas/Git.

This checks metadata and consistency only; it never certifies Mermaid spec
compatibility. Run upstream.py check separately to compare the real source.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import tomllib
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def local_file(root: Path, relative: str) -> bool:
    """Return whether a relative source/evidence file exists inside root."""
    path = (root / relative).resolve()
    return not Path(relative).is_absolute() and path.is_relative_to(root.resolve()) and path.is_file()


def check(root: Path = ROOT) -> dict:
    """Return structural errors/counts; reads files only, owns no native objects."""
    errors = []
    required = ["AGENTS.md", "README.md", "README.en.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
                "docs/NEW_SESSION.md", "docs/IMPLEMENTATION_PLAN.md", "docs/API_COMPATIBILITY.md",
                "docs/TASKS.md", "docs/TEST_AND_RELEASE.md", "docs/RELEASE_STATUS.md",
                "references/licenses/mermaid-LICENSE", "examples/canvas_smoke.py",
                "src/py_mermaid/py.typed", "tools/oracle/README.md"]
    for name in required:
        if not local_file(root, name):
            errors.append(f"Missing required file: {name}")
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    lock = json.loads((root / "references/upstream.lock.json").read_text(encoding="utf-8"))
    index = json.loads((root / "references/spec-inventory.json").read_text(encoding="utf-8"))
    ledger = json.loads((root / "docs/compatibility.json").read_text(encoding="utf-8"))
    cases = json.loads((root / "tests/fixtures/cases.json").read_text(encoding="utf-8"))["cases"]
    if lock.get("schema") != "py-mermaid-upstream-lock/v1" or not re.fullmatch(r"[0-9a-f]{40}", lock.get("commit", "")):
        errors.append("Invalid upstream lock schema/commit")
    if lock.get("tag") != "mermaid@" + lock.get("version", "") or not lock.get("sha256"):
        errors.append("Invalid upstream tag/source hashes")
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in lock["sha256"].values()):
        errors.append("Invalid source SHA256")
    if index.get("schema") != "py-mermaid-spec-inventory/v1" or ledger.get("schema") != "py-mermaid-compatibility/v1":
        errors.append("Invalid inventory/ledger schema")
    if lock["commit"] != index.get("upstreamCommit") or lock["commit"] != ledger.get("upstreamCommit"):
        errors.append("Source commit differs between lock, inventory and compatibility")
    paths = [item["path"] for item in index["files"]]
    if len(paths) != len(set(paths)) or not paths:
        errors.append("Empty/duplicate source inventory")
    counts = dict(Counter(item["category"] for item in index["files"]))
    if counts != index["counts"]:
        errors.append("Inventory category counts differ")
    for item in index["files"]:
        if item["path"].startswith(("/", "../")) or ".." in item["path"].split("/") or not re.fullmatch(r"[0-9a-f]{40}", item["gitBlob"]):
            errors.append(f"Invalid upstream path/blob: {item['path']}")
    expected = {item["id"]: item for item in index["detectors"]}
    actual = {item["id"]: item for item in ledger["diagrams"]}
    if len(expected) != len(index["detectors"]) or len(actual) != len(ledger["diagrams"]) or expected.keys() != actual.keys():
        errors.append("Diagram coverage denominator differs from source detectors")
    for key in expected.keys() & actual.keys():
        if any(expected[key][field] != actual[key].get(field) for field in ("source", "scope")):
            errors.append(f"Diagram source/scope differs: {key}")
    stages = ledger["stages"]
    for item in [*ledger["diagrams"], *ledger["crossCutting"]]:
        for field in ("status", "parser", "layout", "canvas"):
            if field in item and item[field] not in stages:
                errors.append(f"Unknown stage: {item['id']}.{field}")
        advanced = any(item.get(f, "planned") not in ("planned", "inventoried")
                       for f in ("status", "parser", "layout", "canvas"))
        if advanced and not item.get("evidence"):
            errors.append(f"Verified stage requires real evidence: {item['id']}")
        for evidence in item.get("evidence", []):
            if not isinstance(evidence, dict) or not local_file(root, evidence.get("path", "")):
                errors.append(f"Invalid evidence file: {item['id']}")
            elif hashlib.sha256((root / evidence['path']).read_bytes()).hexdigest() != evidence.get("sha256"):
                errors.append(f"Evidence hash differs: {item['id']}")
    expected_dependencies = [f"py-skia-canvas=={lock['canvas']['version']}", "py-visactor-elk==0.1.0"]
    if expected_dependencies[0] not in project["dependencies"]:
        errors.append("Canvas dependency differs from lock")
    elif project["dependencies"] != expected_dependencies:
        errors.append("Runtime dependencies differ from pinned Canvas/ELK requirements")
    if project["requires-python"] != lock["canvas"]["requiresPython"]:
        errors.append("Python support differs from locked Canvas ABI scope")
    tree = ast.parse((root / "src/py_mermaid/__init__.py").read_text(encoding="utf-8"))
    versions = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__version__" for t in n.targets)]
    if versions != [project["version"]]:
        errors.append("Python and project versions differ")
    if len({item["id"] for item in cases}) != len(cases):
        errors.append("Duplicate fixture IDs")
    for item in cases:
        if item["diagram"] not in expected or not local_file(root / "tests/fixtures", item["input"]):
            errors.append(f"Invalid fixture input/diagram: {item['id']}")
    markdown = [*root.glob("*.md")]
    for directory in ("docs", "references", "tests", "tools", "examples"):
        markdown.extend((root / directory).rglob("*.md"))
    for path in markdown:
        inside = False
        language = ""
        block = []
        for line in path.read_text(encoding="utf-8").splitlines():
            fence = re.fullmatch(r"```(\w*)\s*", line)
            if fence:
                if inside and language == "python":
                    try:
                        ast.parse("\n".join(block))
                    except SyntaxError:
                        errors.append(f"Invalid Python example: {path.relative_to(root)}")
                if not inside:
                    language = fence[1]
                    block = []
                inside = not inside
                continue
            if inside:
                block.append(line)
                continue
            for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", line):
                if urlsplit(target).scheme or target.startswith("#"):
                    continue
                filename = unquote(target.split("#", 1)[0])
                if filename and not (path.parent / filename).exists():
                    errors.append(f"Missing documentation link: {path.relative_to(root)} -> {target}")
        if inside:
            errors.append(f"Unclosed code fence: {path.relative_to(root)}")
    zh = (root / "README.md").read_text(encoding="utf-8")
    en = (root / "README.en.md").read_text(encoding="utf-8")
    if "中文 | [English](README.en.md)" not in zh or "[中文](README.md) | English" not in en:
        errors.append("Missing reciprocal README language links")
    command_blocks = lambda text: re.findall(r"```(?:shell|python|powershell|bash)\n(.*?)\n```", text, re.S)
    if command_blocks(zh) != command_blocks(en):
        errors.append("README executable examples differ between languages")
    asset = json.loads((root / "docs/assets/manifest.json").read_text(encoding="utf-8"))
    image_path = root / "docs/assets" / asset["image"]
    if not local_file(root / "docs/assets", asset["image"]):
        errors.append("Missing/invalid example image")
    else:
        data = image_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != asset["sha256"]:
            errors.append("Example image hash differs")
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or list(struct.unpack(">II", data[16:24])) != asset["pixels"]:
            errors.append("Example PNG signature/dimensions differ")
    if not local_file(root, asset["script"]) or hashlib.sha256((root / asset["script"]).read_bytes()).hexdigest() != asset["scriptSha256"]:
        errors.append("Example source differs from image provenance")
    for directory in ("src", "scripts", "examples", "tests/bootstrap"):
        for path in (root / directory).rglob("*.py"):
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                errors.append(f"Invalid Python source: {path.relative_to(root)}")
    return {"status": "BOOTSTRAP_VALIDATED" if not errors else "INCOMPLETE",
            "errors": errors, "detectors": len(expected), "inventoryFiles": len(paths),
            "markdownFiles": len(markdown), "mermaidSpecsPassed": 0,
            "limitation": "Metadata/source consistency only; no Mermaid parsing, layout, rendering or release acceptance."}


def main() -> None:
    """Print JSON and optionally save to a new report path; nonzero on errors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = check()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(payload)
    print(payload, end="")
    raise SystemExit(bool(result["errors"]))


if __name__ == "__main__":
    main()
