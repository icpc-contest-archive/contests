#!/usr/bin/env python3
"""Build the capture queue for archive/tools/capture_urls.py (v2 semantics).

One item per result entry (ALL of them — the capture tool itself skips work already
done): {contest, kind, url (catalogue entry url), raw_url, pinned_ts?, pivot}.
- raw_url: the origin URL (wayback links unwrapped)
- pinned_ts: when the catalogue names a snapshot (`as_of`), use it
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
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from resources import unwrap  # noqa: E402
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
                    raw, ts, via = unwrap(url)
                    item["raw_url"] = raw
                    ts = e.get("as_of") or ts
                    if ts:
                        item["pinned_ts"] = ts
                        stats["pinned via as_of"] += 1
                    else:
                        stats["cdx pick needed"] += 1
                    if via:
                        stats["wrapper url still in catalogue (run migrate_resources)"] += 1
                    queue.append(item)
            # Q11 (2026-09-07): problemset + mirrors are first-class capture
            # targets - single-page URL captures like the result tiers.
            extra = []
            ps = c.get("problemset")
            if ps:
                extra.append(("problemset", ps["url"], ps.get("as_of")) if isinstance(ps, dict)
                             else ("problemset", ps, None))
            for m in c.get("mirrors") or []:
                if m.get("url"):
                    extra.append(("web-mirror", m["url"], m.get("as_of")))
            for kind, url, as_of in extra:
                item = {"contest": c["id"], "kind": kind, "url": url, "pivot": pivot}
                raw, ts, via = unwrap(url)
                item["raw_url"] = raw
                ts = as_of or ts
                if ts:
                    item["pinned_ts"] = ts
                    stats["pinned via as_of"] += 1
                else:
                    stats["cdx pick needed"] += 1
                stats[f"{kind} item"] += 1
                queue.append(item)
    out = ROOT.parent / "archive" / f"capture-queue-{datetime.date.today().isoformat()}.json"
    out.write_text(json.dumps({"generated": datetime.date.today().isoformat(),
                               "queue": queue}, indent=1))
    print(dict(stats), "| total:", len(queue), "->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
