#!/usr/bin/env python3
"""Persist archive references into the catalogue.

For every capture in data/archive-index.json:
  - if its source URL matches an existing result entry (scheme/trailing-slash
    insensitive) -> set that entry's `archived` (and `wayback` if known)
  - else, if the capture has a source URL -> append a new result entry
    {url, archived, note} (artifact scoreboard -> scoreboard;
    external-standings -> standings)
  - captures without a URL are left to render-time handling.

Run from the contests repo root; validate afterwards.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ART_KEY = {"scoreboard": "scoreboard", "frozen_scoreboard": "frozen_scoreboard",
           "standings": "standings", "rankings": "rankings",
           "external-standings": "standings"}


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(
    type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null")
)


def norm(u: str) -> str:
    return re.sub(r"^https?://", "", (u or "").strip()).rstrip("/")


def keyset(*urls) -> set:
    """Match keys for a set of URLs: each normalized, plus the raw origin URL
    embedded in any wayback link among them."""
    out = set()
    for u in urls:
        if not u:
            continue
        out.add(norm(u))
        m = re.match(r"^https?://web\.archive\.org/web/\d{4,14}[a-z_]{0,3}/(.*)$", u)
        if m:
            out.add(norm(m.group(1)))
    return out


def main() -> int:
    index = json.loads((ROOT / "data" / "archive-index.json").read_text())
    by_contest: dict[str, list[dict]] = {}
    for cap in index["captures"]:
        by_contest.setdefault(cap["contest"], []).append(cap)

    stats = Counter()
    for f in sorted((ROOT / "series").glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        changed = False
        for c in doc["contests"]:
            for cap in by_contest.get(c["id"], []):
                if cap.get("content_caveat"):
                    stats["skipped (content caveat)"] += 1
                    continue
                key = ART_KEY.get(cap["artifact"])
                if key is None:
                    stats[f"skipped artifact {cap['artifact']}"] += 1
                    continue
                res = c.setdefault("results", {})
                target = None
                if cap.get("url"):
                    want = keyset(cap["url"], cap.get("wayback_url"))
                    for lst in res.values():
                        for e in lst:
                            if keyset(e["url"], e.get("wayback")) & want:
                                target = e
                                break
                        if target:
                            break
                if target is not None:
                    if target.get("archived"):
                        stats["already enriched"] += 1
                        continue
                    target["archived"] = cap["path"]
                    if cap.get("wayback_url") and not target.get("wayback"):
                        target["wayback"] = cap["wayback_url"]
                    stats["archived added to existing entry"] += 1
                    changed = True
                elif cap.get("url"):
                    entry = {"url": cap["url"], "archived": cap["path"],
                             "note": f"from archived capture ({cap['artifact']})"}
                    if cap.get("wayback_url"):
                        entry["wayback"] = cap["wayback_url"]
                    res.setdefault(key, []).append(entry)
                    stats[f"new {key} entry from capture"] += 1
                    changed = True
                else:
                    stats["capture without url (render-time only)"] += 1
        if changed:
            header = ("# Maintained in-repo; archive references added by "
                      "tools/enrich_from_archive.py.\n")
            f.write_text(header + yaml.dump(doc, Dumper=Dumper, sort_keys=False,
                                            allow_unicode=True, width=100))
            stats["files written"] += 1
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
