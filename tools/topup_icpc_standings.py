#!/usr/bin/env python3
"""Fetch ICPC standings for contests whose CMS id has no rows in the dumps on disk.

The dumps next to this repo (icpc_all_standings.json, icpc_new_standings_from_db.json) were
taken year by year from the open API, which lists contests from ICPC year 2005 on; older
contests, and a few newer ones, are missing although the CMS holds their standings. This
asks the same open endpoint for each such contest id (../fetch_icpc_api_json.py does the
talking: /api/contest/public/search/contest/<id>, team-level fields only, one request at a
time with its own pacing) and writes ../icpc_standings_topup.json in the dumps' shape. An id
that answers with no rows is remembered as empty so it is not asked again.

Usage: python3 tools/topup_icpc_standings.py [--time-budget 150] [--limit N]
Resumable: run it again until it says nothing is left; then tools/bake_icpc_standings.py --write.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(BASE))
from catalogue import archived, by_role, load_series  # noqa: E402
import fetch_icpc_api_json as api  # noqa: E402

OUT = BASE / "icpc_standings_topup.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-budget", type=float, default=150)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    have = set()
    for name in ("icpc_all_standings.json", "icpc_new_standings_from_db.json"):
        have |= {k for k, v in json.loads((BASE / name).read_text()).items() if v.get("standings")}
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = []
    for doc in load_series().values():
        for c in doc["contests"]:
            srcs = by_role(c, "icpc_standings")
            if not srcs or any("/api-" in p for s in srcs for p in archived(s)):
                continue
            m = re.search(r"/finder/(.+)-(\d{4})/standings", srcs[0]["url"])
            for i in c.get("cms_ids") or []:
                if str(i) not in have and str(i) not in out:
                    todo.append((str(i), c, m))
    print(f"{len(todo)} contest ids to ask; {len(out)} already asked ({sum(1 for v in out.values() if v.get('standings'))} with rows)")
    t0, n, got = time.time(), 0, 0
    for i, c, m in todo:
        if time.time() - t0 > args.time_budget or (args.limit and n >= args.limit):
            break
        rows = api.fetch_contest_standings(int(i))
        n += 1
        if rows is None:
            print(f"  {i} ({c['id']}): no answer — will be asked again")
            continue
        out[i] = {"name": c.get("name"), "abbr": m.group(1) if m else "", "year": int(m.group(2)) if m else c.get("season"),
                  "extStandings": "", "standings": rows, "fetched": datetime.date.today().isoformat(), "contest": c["id"]}
        got += bool(rows)
        if n % 10 == 0:
            OUT.write_text(json.dumps(out, ensure_ascii=False))
    OUT.write_text(json.dumps(out, ensure_ascii=False))
    print(f"asked {n}: {got} with standings, {n - got} without; {len(todo) - n} left -> {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
