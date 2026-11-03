#!/usr/bin/env python3
"""Baekjoon (acmicpc.net) ICPC category pages -> judge_page sources + problemset fallbacks.

Baekjoon closed on 2026-04-28 (its pages now say 서비스 종료, "service ended"), so every
acmicpc.net link is dead live. data/baekjoon-categories-<date>.json holds the ICPC category
tree as crawled from the Wayback Machine (tools in the hunt notes): detail id -> title,
catalogue contest id(s), and the newest pre-shutdown snapshot timestamp (as_of) when one exists.

For each mapped category page (sources model, DEFINITIONS.md Resources):
  - the contest gets a source {url, roles: [judge_page], judge: baekjoon, as_of} (an existing
    source of the same address gets the role and, when missing, as_of) — 331 pages were
    already linked
  - contests with NO problemset source get the first page the role problemset too (a
    judge-page fallback), with the Baekjoon crawl noted under `provenance:`
Pages with no pre-shutdown snapshot keep a bare URL; the capture tool picks the nearest
snapshot to the contest date itself.

Re-runnable: a second run on the same data changes nothing.
  python3 tools/import_baekjoon_categories.py [--date 2026-11-02] [--dry-run]
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import add_source, dump_series, find_source, has_role, load_series  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--date", default="2026-11-02"); ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()
m = json.loads((ROOT / "data" / f"baekjoon-categories-{args.date}.json").read_text())["map"]
note = f"Baekjoon ICPC category tree via Wayback ({args.date}); site closed 2026-04-28"
by_contest = {}
for did, v in m.items():
    for cid in v["contests"]:
        by_contest.setdefault(cid, []).append((f"https://www.acmicpc.net/category/detail/{did}", v["ts"], v["title"]))
stats = {"as_of added to existing": 0, "page appended": 0, "problemset fallback": 0, "files": 0}
for sid, doc in load_series().items():
    changed = False
    for c in doc["contests"]:
        pages = by_contest.get(c["id"])
        if not pages: continue
        for url, ts, title in pages:
            existed = find_source(c, url) is not None
            had_as_of = existed and bool(find_source(c, url).get("as_of"))
            s, ch = add_source(c, url, "judge_page", judge="baekjoon", as_of=ts, **({} if existed else {"note": title}))
            if ch:
                changed = True
                if not existed: stats["page appended"] += 1
                elif ts and not had_as_of: stats["as_of added to existing"] += 1
        pb = c.setdefault("problems", {})
        if not pb.get("source"): pb["source"] = note; changed = True
        if not has_role(c, "problemset"):
            url, ts, title = pages[0]
            _s, ch = add_source(c, url, "problemset", as_of=ts,
                                note="judge page (Baekjoon category, all problems with statements) — fallback, no published set found")
            if note not in (c.get("provenance") or []): c.setdefault("provenance", []).append(note)
            stats["problemset fallback"] += 1; changed = True
        if not pb: del c["problems"]
    if changed and not args.dry_run:
        dump_series(sid, doc, "import_baekjoon_categories.py"); stats["files"] += 1
print(stats, "(dry run)" if args.dry_run else "")
