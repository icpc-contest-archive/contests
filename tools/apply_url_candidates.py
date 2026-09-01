#!/usr/bin/env python3
"""Apply reviewed URL-hunt candidates into the series files.

Fills EMPTY slots only, never overwrites existing data:
  icpc_standings  -> set if absent
  web             -> set if absent
  scoreboard/frozen_scoreboard/standings/rankings -> append {url} if the URL
                     isn't already anywhere in the contest's results
A short provenance note (method) goes into the entry's `note`.

Run from the contests repo root. Validate afterwards:
  python3 tools/apply_url_candidates.py --statuses verified [--methods m1,m2] [--dry-run]
  python3 tools/validate.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RES_KEYS = {"scoreboard", "frozen_scoreboard", "standings", "rankings"}


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(
    type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null")
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=str(ROOT / "data" / "url-candidates-2026-09-01.json"))
    ap.add_argument("--statuses", default="verified,wayback")
    ap.add_argument("--methods", default="", help="comma list; empty = all")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    statuses = set(args.statuses.split(","))
    methods = set(args.methods.split(",")) if args.methods else None

    doc = json.loads(Path(args.candidates).read_text())
    wanted = defaultdict(list)
    for e in doc["candidates"]:
        if e["status"] in statuses and (methods is None or e["method"] in methods):
            wanted[e["contest"]].append(e)

    stats = Counter()
    for f in sorted((ROOT / "series").glob("*.yaml")):
        sdoc = yaml.safe_load(f.read_text())
        changed = False
        for c in sdoc["contests"]:
            for e in wanted.get(c["id"], []):
                art, url = e["artifact"], e["url"]
                note = f"added by url-hunt 2026-09-01 ({e['method']})"
                if art == "icpc_standings":
                    if c.get("icpc_standings"):
                        stats["skipped (icpc_standings present)"] += 1
                        continue
                    c["icpc_standings"] = url
                elif art == "web":
                    if c.get("web"):
                        stats["skipped (web present)"] += 1
                        continue
                    c["web"] = url
                elif art in RES_KEYS:
                    res = c.setdefault("results", {})
                    existing = {x["url"] for lst in res.values() for x in lst}
                    if url in existing:
                        stats["skipped (url present)"] += 1
                        continue
                    res.setdefault(art, []).append({"url": url, "note": note})
                else:
                    stats[f"skipped (artifact {art})"] += 1
                    continue
                stats[f"applied {art}"] += 1
                changed = True
        if changed and not args.dry_run:
            header = ("# Maintained in-repo; last bulk edit: tools/apply_url_candidates.py "
                      "(url-hunt 2026-09-01).\n")
            body = yaml.dump(sdoc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)
            f.write_text(header + body)
            stats["files written"] += 1
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    if args.dry_run:
        print("(dry run — nothing written)")
    else:
        print("now run: python3 tools/validate.py && python3 tools/build_site.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
