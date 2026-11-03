#!/usr/bin/env python3
"""Apply reviewed URL-hunt candidates into the series files (`sources:` model).

Adds roles, never overwrites existing data. Each candidate is an (artifact, url); the
artifact names the role the address gets:
  web             -> role web if the contest has no web source; when it has one at a
                     DIFFERENT address, the candidate becomes an `also_at` mirror of it
                     (Q11, 2026-09-07: the era URL stays canonical, the mirror still reaches
                     the capture queue)
  icpc_standings  -> role icpc_standings if the contest has none
  scoreboard/frozen_scoreboard/standings/rankings -> added unless the address already
                     carries a result role (an address with any result role is skipped)
  problemset      -> role problemset if the contest has none; with --append-problemset
                     a second address is simply another problemset source
An address already in `sources:` gets the role merged in (catalogue.add_source). A short
provenance note (method) goes into the entry's `note` when the entry is new.

Run from the contests repo root. Validate afterwards:
  python3 tools/apply_url_candidates.py --statuses verified [--methods m1,m2] [--dry-run]
  python3 tools/validate.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import RESULT_ROLES, add_source, also_at, by_role, dump_series, find_source, has_role, load_series  # noqa: E402
from resources import norm_key, unwrap  # noqa: E402

RES_KEYS = {"scoreboard", "frozen_scoreboard", "standings", "rankings"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=str(ROOT / "data" / "url-candidates-2026-09-01.json"))
    ap.add_argument("--statuses", default="verified,wayback")
    ap.add_argument("--methods", default="", help="comma list; empty = all")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--append-problemset", action="store_true",
                    help="add a problemset URL as an additional source when the contest already has a different one")
    args = ap.parse_args()
    statuses = set(args.statuses.split(","))
    methods = set(args.methods.split(",")) if args.methods else None

    doc = json.loads(Path(args.candidates).read_text())
    wanted = defaultdict(list)
    for e in doc["candidates"]:
        if e["status"] in statuses and (methods is None or e["method"] in methods):
            wanted[e["contest"]].append(e)

    stats = Counter()
    for sid, sdoc in load_series().items():
        changed = False
        for c in sdoc["contests"]:
            for e in wanted.get(c["id"], []):
                art, url = e["artifact"], e["url"]
                note = f"added by url-hunt 2026-09-01 ({e['method']})"
                art_stat = art
                # resource model: a wrapper URL is a locator + as_of, never stored as-is
                url, as_of, _via = unwrap(url)
                if art == "icpc_standings":
                    if has_role(c, "icpc_standings"):
                        stats["skipped (icpc_standings present)"] += 1
                        continue
                elif art == "web":
                    webs = by_role(c, "web")
                    if webs:
                        w = webs[0]
                        known = {norm_key(w["url"])} | {norm_key(m["url"]) for m in also_at(w)}
                        if norm_key(url) in known or find_source(c, url) is not None:
                            stats["skipped (web present)"] += 1
                            continue
                        # also_at entries: bare URL, or {url, as_of} when the candidate pins a snapshot
                        w.setdefault("also_at", []).append({"url": url, "as_of": as_of} if as_of else url)
                        stats["applied mirror"] += 1
                        changed = True
                        continue
                elif art == "problemset":
                    s = find_source(c, url)
                    if s is not None and "problemset" in s["roles"]:
                        stats["skipped (problemset url present)"] += 1
                        continue
                    if has_role(c, "problemset"):
                        if not args.append_problemset:
                            stats["skipped (problemset present)"] += 1
                            continue
                        art_stat = "problemset (additional)"
                elif art in RES_KEYS:
                    s = find_source(c, url)
                    if s is not None and any(r in RESULT_ROLES for r in s["roles"]):
                        stats["skipped (url present)"] += 1
                        continue
                else:
                    stats[f"skipped (artifact {art})"] += 1
                    continue
                _s, ch = add_source(c, url, art, as_of=as_of, note=note)
                if not ch:
                    stats["skipped (present)"] += 1
                    continue
                stats[f"applied {art_stat}"] += 1
                changed = True
        if changed and not args.dry_run:
            dump_series(sid, sdoc, "apply_url_candidates.py (url-hunt)")
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
