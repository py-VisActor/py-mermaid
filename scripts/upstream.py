"""Fetch/verify a pinned read-only checkout and index upstream spec inputs.

Run from any directory. Git is required only by this development tool; it is
never imported by the runtime package. Output inventory records source files,
not extracted test cases or evidence of Python rendering compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = ROOT / ".local/upstream-mermaid"
LOCK = ROOT / "references/upstream.lock.json"
INDEX = ROOT / "references/spec-inventory.json"


def git(checkout: Path, *args: str) -> bytes:
    """Return Git stdout bytes; raise on failure; no native graphics ownership."""
    return subprocess.check_output(["git", "-C", str(checkout), *args])


def verify(checkout: Path, lock: dict) -> None:
    """Check commit, clean checkout and pinned source SHA256; raise ValueError.

    Paths are local development data. Hash canonical Git blobs so Windows
    newline conversion cannot change the baseline. Never repairs a mismatch.
    """
    if git(checkout, "rev-parse", "HEAD").decode().strip() != lock["commit"]:
        raise ValueError("Upstream HEAD differs from lock; do not refresh to hide drift")
    if git(checkout, "status", "--porcelain"):
        raise ValueError("Upstream checkout is dirty; keep reference material read-only")
    for name, expected in lock["sha256"].items():
        actual = hashlib.sha256(git(checkout, "show", f"HEAD:{name}")).hexdigest()
        if actual != expected:
            raise ValueError(f"Upstream source hash differs: {name}")
    package = json.loads(git(checkout, "show", "HEAD:packages/mermaid/package.json"))
    if package["version"] != lock["version"]:
        raise ValueError("Upstream package version differs from lock")


def inventory(checkout: Path, lock: dict) -> dict:
    """Return source-derived file/detector inventory; no claims about passed specs.

    Reads the locked Git tree. Detector extraction is intentionally strict:
    unknown source patterns fail instead of silently dropping a diagram.
    """
    verify(checkout, lock)
    files = []
    for line in git(checkout, "ls-tree", "-r", "HEAD").decode().splitlines():
        metadata, path = line.split("\t", 1)
        _, kind, blob = metadata.split()
        if kind != "blob":
            continue
        category = None
        if re.search(r"\.(spec|test)\.[cm]?[jt]sx?$", path):
            category = "test_source"
        elif path.startswith("e2e/") and path.endswith(".mmd"):
            category = "render_fixture"
        elif path.endswith((".jison", ".langium", ".pegjs", ".g4")):
            category = "grammar"
        elif path.startswith("packages/mermaid/src/docs/syntax/") and path.endswith(".md"):
            category = "syntax_doc"
        if category:
            files.append({"path": path, "gitBlob": blob, "category": category})
    registry = "packages/mermaid/src/diagram-api/diagram-orchestration.ts"
    source = git(checkout, "show", f"HEAD:{registry}").decode()
    detectors = []
    for imported in re.findall(r"from ['\"](\.\./diagrams/[^'\"]+)['\"]", source):
        parts = list(PurePosixPath(registry).parent.parts)
        for part in PurePosixPath(imported).parts:
            if part == "..":
                parts.pop()
            else:
                parts.append(part)
        path = str(PurePosixPath(*parts).with_suffix(".ts"))
        if path.endswith("/errorDiagram.ts"):
            continue
        detector_source = git(checkout, "show", f"HEAD:{path}").decode()
        match = re.search(r"const id = ['\"]([^'\"]+)['\"]", detector_source)
        if not match:
            raise ValueError(f"Unrecognized detector: {path}")
        detectors.append({"id": match[1], "source": path, "scope": "core"})
    detectors.append({"id": "zenuml", "scope": "external_plugin",
                      "source": "packages/mermaid-zenuml/src/detector.ts"})
    counts = {category: sum(f["category"] == category for f in files)
              for category in ("test_source", "render_fixture", "grammar", "syntax_doc")}
    return {"schema": "py-mermaid-spec-inventory/v1", "upstreamCommit": lock["commit"],
            "registry": registry, "counts": counts, "detectors": detectors,
            "diagnostics": ["error", "---"], "files": files,
            "limitation": "Source-file inventory only. Individual test cases, assertions and Python parity remain unported."}


def main() -> None:
    """Development CLI: fetch never overwrites; check never regenerates the index."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["fetch", "check", "inventory"])
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    if args.action == "fetch":
        if not CHECKOUT.exists():
            CHECKOUT.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--depth", "1", "--single-branch", "--branch",
                            lock["tag"], lock["repository"], str(CHECKOUT)], check=True)
        verify(CHECKOUT, lock)
    else:
        result = inventory(CHECKOUT, lock)
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.action == "inventory":
            with INDEX.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
        elif json.loads(INDEX.read_text(encoding="utf-8")) != result:
            raise ValueError("Inventory differs; investigate rather than refreshing the baseline")
        print(json.dumps({"counts": result["counts"], "detectors": len(result["detectors"]) }))
    print("UPSTREAM_VERIFIED (source provenance only)")


if __name__ == "__main__":
    main()
