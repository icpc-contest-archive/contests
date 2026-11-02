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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh-days", type=int, default=0,
                    help="leave out result entries that already have an archived copy AND were live-checked "
                         "within this many days (0 = include everything; the capture tool still dedupes)")
    args = ap.parse_args()
    cutoff = (datetime.date.today() - datetime.timedelta(days=args.fresh_days)).isoformat() if args.fresh_days else None
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
                    if cutoff and e.get("archived") and (e.get("url_checked") or "") >= cutoff:
                        stats[f"left out: archived + checked within {args.fresh_days}d"] += 1
                        continue
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
            for p in (ps if isinstance(ps, list) else [ps]) if ps else []:  # a list since 2026-11-01
                extra.append(("problemset", p["url"], p.get("as_of")) if isinstance(p, dict)
                             else ("problemset", p, None))
            for m in c.get("mirrors") or []:
                if m.get("url"):
                    extra.append(("web-mirror", m["url"], m.get("as_of")))
            # 2026-11-02: online-judge category pages (Baekjoon closed 2026-04-28, Live Archive
            # long dead) are captured too, as judge-<name> artifacts
            for jname, jv in ((c.get("problems") or {}).get("judges") or {}).items():
                for loc in (jv if isinstance(jv, list) else [jv]):
                    extra.append((f"judge-{jname}", loc["url"] if isinstance(loc, dict) else loc,
                                  loc.get("as_of") if isinstance(loc, dict) else None))
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
