#!/usr/bin/env python3
"""Build the capture queue for archive/tools/capture_urls.py (v2 semantics).

One item per capturable SOURCE address (ALL of them — the capture tool itself skips
work already done): {contest, kind, roles, url (catalogue source url), raw_url,
pinned_ts?, pivot}.
- kind: the source's primary capturable role — scoreboard/frozen_scoreboard/standings/
  rankings/problemset, or judge-<judge> for judge pages — which names the archive
  layout <contest>/<kind>/...; `roles` lists every role the address serves.
  Sources serving only web/icpc_standings/teams are not single-page capture targets
  (websites go through make_site_queue.py) and are left out.
- also_at addresses of a web source are queued as kind `web-mirror` (the old mirrors[]);
  an entry of the form {url, as_of} pins that snapshot, a bare URL gets a CDX pick.
- raw_url: the origin URL (wayback links unwrapped)
- pinned_ts: when the catalogue names a snapshot (`as_of`), use it
- pivot: YYYYMMDD to anchor CDX snapshot selection — contest date when known,
  else July 1 of the name-year for fall contests (season == year+1), Jan 1 otherwise.

Needs pyyaml. Writes ../archive/capture-queue-<today>.json.
"""
from __future__ import annotations

import datetime
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import RANK, RESULT_ROLES, also_at, archived, load_contests, sources  # noqa: E402
from resources import unwrap  # noqa: E402

# roles captured as single pages, in archive-layout priority order
CAPTURE_ROLES = ("scoreboard", "frozen_scoreboard", "standings", "rankings", "problemset", "judge_page")


def capture_kind(s: dict, skip: set[str] = frozenset()) -> str | None:
    """Archive artifact kind for a source: its highest-ranked capturable role
    (judge_page -> judge-<judge>), or None when nothing on it is captured this way.
    Roles in `skip` are not considered."""
    roles = [r for r in s["roles"] if r in CAPTURE_ROLES and r not in skip]
    if not roles:
        return None
    r = min(roles, key=lambda r: RANK[r])
    return f"judge-{s.get('judge') or 'unknown'}" if r == "judge_page" else r


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh-days", type=int, default=0,
                    help="leave out sources that already have an archived copy AND were live-checked "
                         "within this many days (0 = include everything; the capture tool still dedupes)")
    args = ap.parse_args()
    cutoff = (datetime.date.today() - datetime.timedelta(days=args.fresh_days)).isoformat() if args.fresh_days else None
    queue, stats = [], Counter()
    for c in load_contests().values():
        if c.get("status") == "upcoming":
            continue
        year = int(c["id"].rsplit("-", 1)[1])
        if c.get("date"):
            pivot = c["date"].replace("-", "")
        elif c.get("season") == year + 1:
            pivot = f"{year}0701"
        else:
            pivot = f"{year}0101"

        def add(kind: str, roles: list[str], url: str, as_of):
            item = {"contest": c["id"], "kind": kind, "roles": roles, "url": url, "pivot": pivot}
            raw, ts, via = unwrap(url)
            item["raw_url"] = raw
            ts = as_of or ts
            if ts:
                item["pinned_ts"] = ts
                stats["pinned via as_of"] += 1
            else:
                stats["cdx pick needed"] += 1
            if via:
                stats["wrapper url still in catalogue (run migrate_resources)"] += 1
            stats[f"{kind} item"] += 1
            queue.append(item)

        for s in sources(c):
            # --fresh-days: `archived` tracks the result-tier capture of the address, so a
            # fresh source drops its result roles from consideration; the address stays
            # queued when it also serves a problemset / judge page (as before the sources model)
            fresh = bool(cutoff and archived(s) and (s.get("url_checked") or "") >= cutoff)
            kind = capture_kind(s, set(RESULT_ROLES) if fresh else frozenset())
            if kind is not None:
                add(kind, list(s["roles"]), s["url"], s.get("as_of"))
            elif fresh and capture_kind(s) is not None:
                stats[f"left out: archived + checked within {args.fresh_days}d"] += 1
            if "web" in s["roles"]:
                # Q11 (2026-09-07): mirrors are first-class capture targets. A mirror's own
                # as_of (when the entry is {url, as_of}) pins the snapshot; otherwise CDX pick
                # around the pivot (the web source's as_of names a snapshot of *its* host, not
                # the mirror's)
                for m in also_at(s):
                    add("web-mirror", ["web"], m["url"], m.get("as_of"))
    out = ROOT.parent / "archive" / f"capture-queue-{datetime.date.today().isoformat()}.json"
    out.write_text(json.dumps({"generated": datetime.date.today().isoformat(),
                               "queue": queue}, indent=1))
    print(dict(stats), "| total:", len(queue), "->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
