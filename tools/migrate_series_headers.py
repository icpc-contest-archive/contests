#!/usr/bin/env python3
"""One-off: give every series header `region`, `tier` and `naming` (2026-11-02 redesign).

  region  one of the ICPC super-regions (REGIONS); was a table in build_site.py. Championship
          series take the region they are the championship of; the World Finals has none.
  tier    world-finals | championship | regional | subregional
          derived: wf -> world-finals; header already says championship -> keep; otherwise from
          where the series' contests advance to (latest contest with a parent): WF or a
          championship -> regional; a regional -> subregional. No parent anywhere -> left
          unset (validator warns) unless the series is a known regional view (subset_of).
  naming  season-start | season-end: which half of the season the id's year names
          (derived from id year vs season; mixed series are reported, not written).

Usage: python3 tools/migrate_series_headers.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import dump_series, load_series  # noqa: E402

REGIONS = ("North America", "Latin America", "Europe", "Northern Eurasia", "Africa & Arab",
           "Asia West", "Asia Pacific", "Asia East")
TABLE = {
    "North America": ["nac", "nadc", "socal", "naq", "nena", "nena-atlantic", "nena-central", "nena-east",
                      "nena-north", "nena-west", "ecna", "scusa", "rmc", "lethbridge", "gny", "mcpc", "seusa",
                      "mausa", "pacnw", "east-na", "south-na", "alberta", "ncna"],
    "Latin America": ["lac", "brazil", "mexico", "caribbean", "central-america", "south-america",
                      "south-america-north", "south-america-south", "cuba"],
    "Europe": ["euc", "poland", "hungary", "slovenia", "turkey", "ukraine", "cerc", "swerc", "nwerc", "bapc",
               "bapc-prelims", "germany", "croatia", "romania", "bulgaria", "greece", "cyprus", "nordic", "sweden",
               "norway", "ukiepc", "ctuo", "erc", "werc", "mcerc", "seerc"],
    "Northern Eurasia": ["neerc", "nerc", "south-russia", "central-russia", "north-russia", "west-siberia",
                         "east-siberia", "far-east-russia", "urals", "moscow", "taurida", "west-neerc", "armenia",
                         "azerbaijan", "georgia", "kazakhstan", "kyrgyzstan", "uzbekistan"],
    "Africa & Arab": ["acpc", "egypt", "jordan", "syria", "lebanon", "kuwait", "bahrain", "oman", "qatar",
                      "saudi-arabia", "palestine", "morocco", "tunisia", "algeria", "sudan", "south-africa", "angola",
                      "benin", "burkina-faso", "ethiopia", "ivory-coast", "nigeria", "senegal", "togo"],
    "Asia West": ["awc", "tehran", "pakistan", "kabul", "dhaka", "kanpur", "amritapuri", "kharagpur", "kolkata",
                  "gwalior", "chennai", "coimbatore", "bombay", "mathura", "india", "gwalior-kanpur", "kolkata-kanpur",
                  "kolkata-roorkee", "gwalior-pune"],
    "Asia Pacific": ["apc", "mongolia-national", "philippines-national", "japan", "korea", "taiwan", "singapore",
                     "manila", "jakarta", "kuala-lumpur", "thailand", "vietnam", "yangon", "south-pacific",
                     "south-pacific-west", "south-pacific-central", "south-pacific-east", "south-pacific-division",
                     "nzpc", "australia"],
    "Asia East": ["aec", "hong-kong", "macau", "pyongyang", "beijing", "shanghai", "chengdu", "hangzhou", "xian",
                  "harbin", "wuhan", "fuzhou", "hefei", "nanjing", "dalian", "changchun", "changsha", "jinan", "jinhua",
                  "jiaozuo", "kunming", "mudanjiang", "nanchang", "nanning", "ningbo", "qingdao", "shenyang",
                  "tianjin", "urumqi", "xuzhou", "yinchuan", "anshan", "guangzhou"],
}
SERIES_REGION = {s: r for r, ss in TABLE.items() for s in ss}
HEADER_ORDER = ("id", "name", "tier", "region", "naming", "rotating_host", "aliases", "lineage", "notes")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    series = load_series()
    contests = {c["id"]: c for d in series.values() for c in d["contests"]}
    stats = Counter()
    tier: dict[str, str] = {}
    for sid in ("alberta", "lethbridge", "naq", "mongolia-national", "philippines-national"):
        tier[sid] = "subregional"  # feeders whose parent links are not recorded yet
    for sid, d in series.items():
        if sid == "wf":
            tier[sid] = "world-finals"
        elif d["series"].get("tier") == "championship":
            tier[sid] = "championship"
    # regions: table, then inherit along parent chains (feeders follow their regional)
    region = dict(SERIES_REGION)
    for _ in range(6):
        for sid, d in series.items():
            if sid in region or sid == "wf":
                continue
            for c in reversed(d["contests"]):
                ps = c.get("parent") if isinstance(c.get("parent"), list) else [c.get("parent")]
                for p in ps:
                    if p and p in contests and p.rsplit("-", 1)[0] in region:
                        region[sid] = region[p.rsplit("-", 1)[0]]
                        break
                if sid in region:
                    break
    # tiers from where contests advance to
    for _ in range(6):
        for sid, d in series.items():
            if sid in tier:
                continue
            for c in reversed(d["contests"]):
                ps = c.get("parent") if isinstance(c.get("parent"), list) else [c.get("parent")]
                pt = {tier.get(p.rsplit("-", 1)[0]) for p in ps if p}
                pt.discard(None)
                if pt:
                    tier[sid] = "regional" if pt & {"world-finals", "championship"} else "subregional"
                    break
            if sid not in tier and any(c.get("subset_of") for c in d["contests"]):
                tier[sid] = "regional"  # a regional-level view of a division contest
    for sid, d in series.items():
        h = d["series"]
        pat = Counter()
        for c in d["contests"]:
            y, s = int(c["id"].rsplit("-", 1)[1]), c.get("season")
            if s:
                pat["season-end" if y == s else "season-start" if y == s - 1 else "other"] += 1
        if sid in tier:
            h["tier"] = tier[sid]
        else:
            stats["tier unknown"] += 1
            print(f"  tier unknown: {sid}")
        if sid in region:
            h["region"] = region[sid]
        elif sid != "wf":
            stats["region unknown"] += 1
            print(f"  region unknown: {sid}")
        if len(pat) == 1:
            h["naming"] = next(iter(pat))
        elif pat:
            stats["naming mixed"] += 1
            print(f"  naming mixed: {sid} {dict(pat)}")
        else:
            h["naming"] = "season-start"  # no seasons recorded yet; the regional default
            stats["naming defaulted (no seasons)"] += 1
        d["series"] = {k: h[k] for k in HEADER_ORDER if k in h} | {k: v for k, v in h.items() if k not in HEADER_ORDER}
        stats[f"tier {tier.get(sid)}"] += 1
        if not args.dry_run:
            dump_series(sid, d, "migrate_series_headers.py (region/tier/naming, 2026-11-02)")
    print(dict(sorted(stats.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
