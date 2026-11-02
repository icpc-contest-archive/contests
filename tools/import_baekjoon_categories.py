#!/usr/bin/env python3
"""Baekjoon (acmicpc.net) ICPC category pages -> judges.baekjoon locators + problemset fallbacks.

Baekjoon closed on 2026-04-28 (its pages now say 서비스 종료, "service ended"), so every
acmicpc.net link is dead live. data/baekjoon-categories-<date>.json holds the ICPC category
tree as crawled from the Wayback Machine (tools in the hunt notes): detail id -> title,
catalogue contest id(s), and the newest pre-shutdown snapshot timestamp (as_of) when one exists.

For each mapped category page:
  - the contest's judges.baekjoon gets the locator {url, as_of} (an existing bare URL is
    upgraded with as_of; a new page is appended) — 331 pages were already linked
  - contests with NO problemset get the page as a judge-page problemset fallback
Pages with no pre-shutdown snapshot keep a bare URL; the capture tool picks the nearest
snapshot to the contest date itself.
"""
import argparse, datetime, glob, json, re, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from resources import norm_key  # noqa: E402

class Dumper(yaml.SafeDumper): pass
Dumper.add_representer(type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null"))

ap = argparse.ArgumentParser(); ap.add_argument("--date", default="2026-11-02"); args = ap.parse_args()
m = json.loads((ROOT / "data" / f"baekjoon-categories-{args.date}.json").read_text())["map"]
note = f"Baekjoon ICPC category tree via Wayback ({args.date}); site closed 2026-04-28"
by_contest = {}
for did, v in m.items():
    for cid in v["contests"]:
        by_contest.setdefault(cid, []).append((f"https://www.acmicpc.net/category/detail/{did}", v["ts"], v["title"]))
stats = {"as_of added to existing": 0, "page appended": 0, "problemset fallback": 0, "files": 0}
for f in sorted((ROOT / "series").glob("*.yaml")):
    doc = yaml.safe_load(f.read_text()); changed = False
    for c in doc["contests"]:
        pages = by_contest.get(c["id"])
        if not pages: continue
        pb = c.setdefault("problems", {})
        J = pb.setdefault("judges", {})
        cur = J.get("baekjoon"); cur = [] if cur is None else (cur if isinstance(cur, list) else [cur])
        for url, ts, title in pages:
            hit = next((i for i, x in enumerate(cur) if norm_key(x["url"] if isinstance(x, dict) else x) == norm_key(url)), None)
            if hit is not None:
                x = cur[hit]
                if ts and not (isinstance(x, dict) and x.get("as_of")):
                    cur[hit] = {"url": url, "as_of": ts}; stats["as_of added to existing"] += 1; changed = True
            else:
                cur.append({"url": url, "as_of": ts, "note": title} if ts else {"url": url, "note": title}); stats["page appended"] += 1; changed = True
        J["baekjoon"] = cur[0] if len(cur) == 1 else cur
        if not pb.get("source"): pb["source"] = note
        if not c.get("problemset"):
            url, ts, title = pages[0]
            c["problemset"] = {"url": url, **({"as_of": ts} if ts else {}), "note": f"judge page (Baekjoon category, all problems with statements) — fallback, no published set found"}
            c.setdefault("sources", []).append(note); stats["problemset fallback"] += 1; changed = True
        if not pb.get("judges"): del pb["judges"]
        if not pb: del c["problems"]
    if changed:
        f.write_text("# Maintained in-repo; problem-archive data imported by tools/import_problem_archive.py.\n"
                     + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)); stats["files"] += 1
print(stats)
