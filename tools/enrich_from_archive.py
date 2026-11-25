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
  - a capture whose address another contest already cites, or whose path a source already
    lists, never makes a new source: it was filed under this contest's folder before the
    source was moved or removed (content check, data scan), and re-adding it would undo that.
  - a capture of an address that data/removed-sources.json lists for the contest never makes a source.
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
from resources import norm_key, unwrap  # noqa: E402
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
    series = load_series()
    cited: dict[str, set[str]] = {}     # address key -> contests that cite it
    listed: set[str] = set()           # capture paths some source already lists
    for doc in series.values():
        for c in doc["contests"]:
            for s in c.get("sources") or []:
                cited.setdefault(norm_key(s["url"]), set()).add(c["id"])
                listed.update(archived(s))
    # sources taken off a contest by a ruling (data/removed-sources.json): a capture filed under the
    # contest must not bring one back
    rp = ROOT / "data" / "removed-sources.json"
    removed = {cid: {norm_key(u) for u in urls} for cid, urls in (json.loads(rp.read_text()) if rp.exists() else {}).items()
               if not cid.startswith("_")}
    for sid, doc in series.items():
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
                elif cap.get("url") and norm_key(unwrap(cap["url"])[0]) in removed.get(c["id"], ()):
                    stats["skipped: source removed from this contest by a ruling"] += 1
                elif cap.get("url") and (cap["path"] in listed
                                         or cited.get(norm_key(unwrap(cap["url"])[0]), set()) - {c["id"]}):
                    stats["skipped: address cited by another contest (moved or removed here)"] += 1
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
