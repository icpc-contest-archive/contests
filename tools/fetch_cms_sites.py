#!/usr/bin/env python3
"""Fetch every catalogue contest's CMS record (icpc.global public API) for its SITES —
name, locationName, address{city,state,country}, siteDate, homepage — the structured
input for the location tree (DEFINITIONS.md, Locations). Resumable; one JSON per run.

  data/cms-sites.json  {"fetched": date, "contests": {cms_id: {slug, name, endDate, sites: [...]}}}

Usage: python3 tools/fetch_cms_sites.py [--limit N] [--delay 0.3]
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import load_contests  # noqa: E402

API = "https://icpc.global/api/contest/public/"
OUT = ROOT / "data" / "cms-sites.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()
    slugs = {int(k): v for k, v in json.loads((ROOT / "data" / "cms-shortnames.json").read_text()).items()}
    data = json.loads(OUT.read_text()) if OUT.exists() else {"fetched": None, "contests": {}}
    got = data["contests"]
    todo = []
    for c in load_contests().values():
        for i in c.get("cms_ids") or []:
            if str(i) not in got and i in slugs:
                todo.append(i)
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(got)} fetched already, {len(todo)} to go", flush=True)
    n = 0
    for i in todo:
        try:
            with urllib.request.urlopen(API + slugs[i], timeout=30) as r:
                d = json.loads(r.read())
        except urllib.error.HTTPError as e:
            got[str(i)] = {"slug": slugs[i], "error": f"HTTP {e.code}"}
            continue
        except Exception as e:  # noqa: BLE001
            print(f"  {i} {slugs[i]}: {type(e).__name__}", flush=True)
            time.sleep(5)
            continue
        if d.get("id") != i:
            got[str(i)] = {"slug": slugs[i], "error": f"api id {d.get('id')} != {i}"}
            continue
        sites = []
        for s in d.get("sites") or d.get("activeSites") or []:
            a = s.get("address") or {}
            sites.append({"id": s.get("id"), "name": s.get("name"), "location": s.get("locationName"),
                          "city": a.get("city"), "state": a.get("state"), "country": a.get("country"),
                          "date": s.get("siteDate"), "homepage": s.get("homepage"),
                          "type": s.get("siteType"), "delivery": s.get("siteDelivery")})
        got[str(i)] = {"slug": slugs[i], "name": d.get("name"), "endDate": d.get("endDate"),
                       "geographicArea": d.get("geographicArea"), "homepage": d.get("homepage"),
                       "hosts": d.get("hosts"), "sites": sites}
        n += 1
        if n % 50 == 0:
            data["fetched"] = datetime.date.today().isoformat()
            OUT.write_text(json.dumps(data, indent=0, ensure_ascii=False))
            print(f"  {n}/{len(todo)}", flush=True)
        time.sleep(args.delay)
    data["fetched"] = datetime.date.today().isoformat()
    OUT.write_text(json.dumps(data, indent=0, ensure_ascii=False))
    print(f"done: {len(got)} contests in {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    main()
