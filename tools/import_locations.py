#!/usr/bin/env python3
"""Import per-contest locations into the catalogue.

The catalogue tracked location on only ~49 entries while the authoritative
icpc-history inventory carries it for ~1,900 and the CMS database adds ~150
more - so "do we know where this was held" was only answerable by a join.
This makes location first-class in series/*.yaml:

  location precedence (existing catalogue values are NEVER touched):
    1. inventory master_contests.csv `location` (fallback: `venue`), by slug
    2. CMS icpc-nopii.db site.location, by cms_ids (first site with one)
  Region-only strings (geographic_area) are deliberately NOT imported.

Provenance is written to data/location-import-<date>.json (id -> source),
keeping the YAML clean. Dry-run by default; nothing is written without
--write. Run tools/validate.py afterwards.

Usage: python3 tools/import_locations.py [--write]
       [--inventory PATH] [--db PATH]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import sqlite3
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HEADER = "# Maintained in-repo; last bulk edit: tools/import_locations.py.\n"


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(
    type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null")
)


def ordered(entry: dict, location: str) -> dict:
    """Rebuild the entry with location placed right after date/name for
    readability (yaml.dump keeps insertion order)."""
    out = {}
    placed = False
    for k, v in entry.items():
        out[k] = v
        if not placed and k in ("date", "name"):
            if k == "date" or "date" not in entry:
                out["location"] = location
                placed = True
    if not placed:
        out["location"] = location
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory",
                    default=str(ROOT.parent.parent / "icpc-history" /
                                "contest-inventory" / "master_contests.csv"))
    ap.add_argument("--db",
                    default=str(ROOT.parent.parent / "icpc-data" / "icpc-nopii.db"))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    inv = {}
    with open(args.inventory) as f:
        for r in csv.DictReader(f):
            loc = (r.get("location") or "").strip() or (r.get("venue") or "").strip()
            if loc:
                inv[r["slug"]] = loc

    db = sqlite3.connect(args.db)
    dbsite = {}
    for cid, loc in db.execute(
            "SELECT contest_id, location FROM site "
            "WHERE location IS NOT NULL AND TRIM(location) != ''"):
        dbsite.setdefault(str(cid), str(loc).strip())

    stats = {"kept-existing": 0, "inventory": 0, "cms-site": 0, "no-source": 0}
    provenance = {}
    touched = 0
    for fp in sorted((ROOT / "series").glob("*.yaml")):
        doc = yaml.safe_load(fp.read_text())
        changed = False
        contests = doc.get("contests") or []
        for i, c in enumerate(contests):
            if (c.get("location") or "").strip():
                stats["kept-existing"] += 1
                continue
            loc, src = None, None
            if c["id"] in inv:
                loc, src = inv[c["id"]], "inventory"
            else:
                for cid in (c.get("cms_ids") or []):
                    if str(cid) in dbsite:
                        loc, src = dbsite[str(cid)], "cms-site"
                        break
            if not loc:
                stats["no-source"] += 1
                continue
            contests[i] = ordered(c, loc)
            stats[src] += 1
            provenance[c["id"]] = src
            changed = True
        if changed and args.write:
            body = yaml.dump(doc, Dumper=Dumper, sort_keys=False,
                             allow_unicode=True, width=100)
            fp.write_text(HEADER + body)
            touched += 1
        elif changed:
            touched += 1

    print(f"locations: +{stats['inventory']} from inventory, "
          f"+{stats['cms-site']} from CMS sites; "
          f"{stats['kept-existing']} existing kept untouched; "
          f"{stats['no-source']} entries have no source anywhere")
    print(f"{touched} series file(s) {'written' if args.write else 'WOULD change (dry run)'}")
    if args.write:
        rep = ROOT / "data" / f"location-import-{datetime.date.today().isoformat()}.json"
        rep.write_text(json.dumps(
            {"generated": datetime.date.today().isoformat(),
             "precedence": "existing > inventory(location|venue) > cms site.location",
             "stats": stats, "source_by_contest": provenance},
            indent=1, ensure_ascii=False))
        print(f"provenance -> {rep.relative_to(ROOT)}")
        print("now run: python3 tools/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
