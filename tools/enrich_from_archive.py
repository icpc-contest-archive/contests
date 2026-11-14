#!/usr/bin/env python3
"""Persist archive references into the catalogue.

For every result-tier capture in data/archive-index.json:
  - if its source URL matches an existing source (any role; scheme/trailing-slash
    insensitive) -> add the capture path to that source's `archived` list (and `as_of`
    from the snapshot if the source has none)
  - else, if the capture has a source URL -> add a new source
    {url, roles: [<role>], archived: [path], note} (artifact scoreboard -> scoreboard;
    external-standings -> standings)
  - ICPC API dumps / icpc.global finder pages -> capture path added to `archived` on the
    icpc_standings source
`archived` is always a list: one address may hold several captures (catalogue.add_archived).
  - captures without a URL are left to render-time handling.
Problemset, judge-page and web-mirror captures are not written back (as before).

Run from the contests repo root; validate afterwards.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import add_archived, add_source, archived, by_role, cms_sources, dump_series, find_source, load_series  # noqa: E402
from resources import unwrap  # noqa: E402
ART_KEY = {"scoreboard": "scoreboard", "frozen_scoreboard": "frozen_scoreboard",
           "standings": "standings", "rankings": "rankings",
           "external-standings": "standings"}


def cap_ts(cap: dict):
    return cap.get("wayback_timestamp") or unwrap(cap.get("wayback_url") or "")[1]


def main() -> int:
    index = json.loads((ROOT / "data" / "archive-index.json").read_text())
    by_contest: dict[str, list[dict]] = {}
    for cap in index["captures"]:
        by_contest.setdefault(cap["contest"], []).append(cap)

    stats = Counter()
    for sid, doc in load_series().items():
        changed = False
        for c in doc["contests"]:
            for cap in by_contest.get(c["id"], []):
                if cap.get("content_caveat"):
                    stats["skipped (content caveat)"] += 1
                    continue
                if cap.get("source") == "icpc-api-archive" or re.match(r"^https?://icpc\.global/regionals/finder/", cap.get("url") or ""):
                    # a copy rendered from the API data belongs to the contest's CMS standings source
                    cur = cms_sources(c)
                    obj = cur[0] if cur else None
                    if obj is None:
                        obj, _ = add_source(c, cap["url"], "standings")
                    if add_archived(obj, cap["path"]):
                        stats["icpc_standings archived added"] += 1
                        changed = True
                    else:
                        stats["icpc_standings already archived"] += 1
                    continue
                role = ART_KEY.get(cap["artifact"])
                if role is None:
                    stats[f"skipped artifact {cap['artifact']}"] += 1
                    continue
                target = None
                if cap.get("url"):
                    target = find_source(c, cap["url"]) or (
                        find_source(c, cap["wayback_url"]) if cap.get("wayback_url") else None)
                if target is not None:
                    if not add_archived(target, cap["path"]):
                        stats["already enriched"] += 1
                        continue
                    if cap_ts(cap) and not target.get("as_of"):
                        target["as_of"] = cap_ts(cap)
                    stats["archived added to existing source"
                          + (" (additional capture)" if len(archived(target)) > 1 else "")] += 1
                    changed = True
                elif cap.get("url"):
                    add_source(c, unwrap(cap["url"])[0], role, as_of=cap_ts(cap), archived=[cap["path"]],
                               note=f"from archived capture ({cap['artifact']})")
                    stats[f"new {role} source from capture"] += 1
                    changed = True
                else:
                    stats["capture without url (render-time only)"] += 1
        if changed:
            dump_series(sid, doc, "enrich_from_archive.py")
            stats["files written"] += 1
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
