#!/usr/bin/env python3
"""Local browser: rebuilds the site with local replay links and serves it.

Usage: python3 tools/serve.py [--port 8123]
Serves site/ at /, and — when sibling checkouts exist — ../replay at /replay/
and ../archive at /archive/. /health answers 200 with CORS for the public
site's lights-up probe.
"""
from __future__ import annotations

import argparse
import functools
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    mounts: dict[str, Path] = {}

    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0].split("#", 1)[0]
        for prefix, base in self.mounts.items():
            if clean.startswith(prefix):
                rel = clean[len(prefix):].lstrip("/")
                return str(base / rel)
        return str(self.mounts[""] / clean.lstrip("/"))

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            body = b"ok"
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--no-rebuild", action="store_true")
    args = ap.parse_args()

    if not args.no_rebuild:
        os.environ["REPLAY_BASE"] = "/replay"
        sys.path.insert(0, str(ROOT / "tools"))
        import build_site  # noqa: E402

        build_site.build(ROOT / "site")

    Handler.mounts = {"": ROOT / "site"}
    for name in ("replay", "archive"):
        sibling = ROOT.parent / name
        if sibling.is_dir():
            Handler.mounts[f"/{name}/"] = sibling
            print(f"mounted ../{name} at /{name}/")
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"browsing at http://127.0.0.1:{args.port}/")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
