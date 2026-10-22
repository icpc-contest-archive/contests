#!/usr/bin/env python3
"""One-off: ICPC finder pages filed as `standings` move to the `icpc_standings` tier.

The API-dump bake (tools/bake_api_standings.py) and enrich_from_archive filed the
icpc.global finder page as a `standings` result entry, so the lowest tier (the CMS's own
data) counted as "standings" in coverage and on the marks. Ruling (resource consistency
review 2026-10-22): the finder page is the ICPC-standings tier, nothing else. This moves
every results entry whose url is a finder page into `icpc_standings` (now a locator
object carrying the capture pointer), and drops the duplicate from the results tiers.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FINDER = re.compile(r"^https?://icpc\.global/regionals/finder/")


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null"))


def main() -> int:
    dry = "--dry-run" in sys.argv
    stats = Counter()
    for f in sorted((ROOT / "series").glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        changed = False
        for c in doc["contests"]:
            res = c.get("results") or {}
            moved = None
            for kind in list(res):
                keep = []
                for e in res[kind]:
                    if FINDER.match(e["url"]):
                        stats[f"moved from {kind}"] += 1
                        if moved is None or (e.get("archived") and not moved.get("archived")):
                            moved = e
                        changed = True
                    else:
                        keep.append(e)
                if keep:
                    res[kind] = keep
                else:
                    del res[kind]
            if not res and "results" in c:
                del c["results"]
            if moved:
                cur = c.get("icpc_standings")
                cur_url = cur["url"] if isinstance(cur, dict) else cur
                obj = {"url": cur_url or moved["url"]}
                if cur_url and cur_url.rstrip("/") != moved["url"].rstrip("/"):
                    stats["finder url differs from icpc_standings (kept field's url, noted)"] += 1
                    obj["note"] = f"API-dump capture was filed under {moved['url']}"
                for k in ("as_of", "archived", "url_state", "url_checked"):
                    if moved.get(k):
                        obj[k] = moved[k]
                if moved.get("note"):
                    obj["note"] = (obj.get("note", "") + "; " if obj.get("note") else "") + moved["note"]
                if isinstance(cur, dict):
                    obj = {**cur, **{k: v for k, v in obj.items() if k != "url"}}
                c["icpc_standings"] = obj
                stats["icpc_standings now an object"] += 1
        if changed and not dry:
            f.write_text("# Maintained in-repo; finder pages moved to the icpc_standings tier (tools/migrate_finder_tier.py).\n"
                         + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
            stats["files written"] += 1
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print("dry run" if dry else "now run: python3 tools/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
