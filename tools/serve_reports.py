"""Serve a report directory locally; stdout is UTF-8 NDJSON access/event logs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import os

from run_support import Run

ACTIVE_RUN = None


def event(kind: str, **fields) -> None:
    if ACTIVE_RUN is not None:
        ACTIVE_RUN.event(kind, **fields)
    print(json.dumps({"schema": "py-mermaid-event/v1", "runId": ACTIVE_RUN.id if ACTIVE_RUN else None,
                      "atUtc": datetime.now(timezone.utc).isoformat(), "event": kind, **fields},
                     ensure_ascii=False), flush=True)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        event("http_access", client=self.client_address[0], message=format % args)


def main() -> None:
    global ACTIVE_RUN
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "reports")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--runs-dir", type=Path, help="Standard run logs; defaults to repository test-runs")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if not root.is_dir():
        parser.error("--root must be a report directory")
    with Run("reports", "serve", runs_dir=args.runs_dir) as run:
        ACTIVE_RUN = run
        try:
            with ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(root))) as server:
                run.data["server"] = {"pid": os.getpid(), "root": str(root), "host": args.host,
                                      "port": server.server_port, "url": f"http://{args.host}:{server.server_port}/"}
                run.save()
                event("server_ready", **run.data["server"], run=str(run.path))
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    event("server_stopping")
        finally:
            ACTIVE_RUN = None


if __name__ == "__main__":
    main()
