#!/usr/bin/env python3
"""Build the capture queue for archive/tools/capture_urls.py (v2 semantics).

One item per result entry (ALL of them — the capture tool itself skips work already
done): {contest, kind, url (catalogue entry url), raw_url, pinned_ts?, pivot}.
- raw_url: the origin URL (wayback links unwrapped)
- pinned_ts: when the catalogue already names a specific snapshot, use it
- pivot: YYYYMMDD to anchor CDX snapshot selection — contest date when known,
  else July 1 of the name-year for fall contests (season == year+1), Jan 1 otherwise.

Needs pyyaml. Writes ../archive/capture-queue-<today>.json.
"""
from __future__ import annotations

import datetime
import json
import re
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TIERS = ["scoreboard", "frozen_scoreboard", "standings", "rankings"]
WB = re.compile(r"^https?://web\.archive\.org/web/(\d{4,14})[a-z_]{0,3}/(.*)$")


def main() -> int:
    queue, stats = [], Counter()
    for f in sorted((ROOT / "series").glob("*.yaml")):
        for c in yaml.safe_load(f.read_text())["contests"]:
            if c.get("status") == "upcoming":
                continue
            year = int(c["id"].rsplit("-", 1)[1])
            if c.get("date"):
                pivot = c["date"].replace("-", "")
            elif c.get("season") == year + 1:
                pivot = f"{year}0701"
            else:
                pivot = f"{year}0101"
            for kind in TIERS:
                for e in c.get("results", {}).get(kind, []):
                    url = e["url"]
                    item = {"contest": c["id"], "kind": kind, "url": url, "pivot": pivot}
                    m = WB.match(url)
                    if m:
                        raw, ts = m.group(2), m.group(1)
                        while (mm := WB.match(raw)):  # unwrap wayback-of-wayback
                            raw, ts = mm.group(2), mm.group(1)
                            stats["double-wrapped wayback unwrapped"] += 1
                        item["raw_url"], item["pinned_ts"] = raw, ts
                        stats["wayback-link entry"] += 1
                    else:
                        item["raw_url"] = url
                        wb = e.get("wayback") or ""
                        mm = WB.match(wb)
                        if mm and mm.group(2).rstrip("/") == url.rstrip("/"):
                            item["pinned_ts"] = mm.group(1)
                            stats["pinned via wayback field"] += 1
                        else:
                            stats["cdx pick needed"] += 1
                    queue.append(item)
    out = ROOT.parent / "archive" / f"capture-queue-{datetime.date.today().isoformat()}.json"
    out.write_text(json.dumps({"generated": datetime.date.today().isoformat(),
                               "queue": queue}, indent=1))
    print(dict(stats), "| total:", len(queue), "->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
