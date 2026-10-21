#!/usr/bin/env python3
"""Build the website-capture queue for archive/tools/capture_site.py.

One item per contest that has a `web` URL: {contest, seeds, pivot, scope}.
Scope is auto-derived per seed: a year-bearing host (2018.nwerc.eu) scopes to the
host; a year-bearing path (acmgnyr.org/year2018/) scopes to that path prefix;
otherwise the whole host (flagged, since undated hosts get repurposed).

Needs pyyaml. Writes ../archive/site-queue-<today>.json.
"""
from __future__ import annotations

import datetime
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent


def scope_for(url: str, year: int):
    p = urlsplit(url)
    yy = str(year)[2:]
    if re.search(rf"(?<!\d)({year}|{year + 1})(?!\d)", p.netloc):
        return {"host": p.netloc, "path": "/", "rule": "year-host"}
    m = re.search(rf"^(.*?/[^/]*(?:{year}|{year + 1}|{yy})[^/]*/)", p.path + "/")
    if m:
        return {"host": p.netloc, "path": m.group(1), "rule": "year-path"}
    return {"host": p.netloc, "path": "/", "rule": "whole-host (undated — repurposing risk)"}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot-only", action="store_true",
                    help="only contests whose web entry carries as_of (dead sites)")
    args = ap.parse_args()
    queue, stats = [], Counter()
    for f in sorted((ROOT / "series").glob("*.yaml")):
        for c in yaml.safe_load(f.read_text())["contests"]:
            if c.get("status") == "upcoming" or not c.get("web"):
                continue
            year = int(c["id"].rsplit("-", 1)[1])
            pivot = (c.get("date") or "").replace("-", "") or (
                f"{year}0701" if c.get("season") == year + 1 else f"{year}0101")
            seeds, snapshot = [], None
            for w in (c["web"] if isinstance(c["web"], list) else [c["web"]]):
                # resource model: {url, as_of} = "the site as it was at as_of" ->
                # capture_site snapshot mode (raw id_ fetches within that snapshot,
                # pages keyed by real url); a bare url is crawled live
                if isinstance(w, dict):
                    seeds.append(w["url"])
                    snapshot = snapshot or w.get("as_of")
                elif isinstance(w, str) and w.startswith("http"):
                    seeds.append(w)
            if not seeds:
                continue
            item = {"contest": c["id"], "seeds": seeds, "pivot": pivot,
                    "scopes": [scope_for(s, year) for s in seeds]}
            if snapshot:
                item["snapshot"] = snapshot
                stats["snapshot"] += 1
            if args.snapshot_only and not snapshot:
                continue
            queue.append(item)
            for s in item["scopes"]:
                stats[s["rule"].split(" ")[0]] += 1
    out = ROOT.parent / "archive" / f"site-queue-{datetime.date.today().isoformat()}.json"
    out.write_text(json.dumps({"generated": datetime.date.today().isoformat(),
                               "queue": queue}, indent=1))
    print(dict(stats), "| contests with sites:", len(queue), "->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
