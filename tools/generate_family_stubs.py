#!/usr/bin/env python3
"""Generate catalogue entries + CMS-ledger entries from the 2026-09-04 family ruling.

Scope = the ADOPTED part of the ruling ("adopt, but flag exceptions"): the six
contested calls (ukraine, brazil-first-phase, vietnam-national, kazakhstan-octafinal,
caribbean CFQ-era, afghanistan) are NOT touched here.

Sources:
  ~/Claude/icpc-history/contest-inventory/master_contests.csv  (Fredrik's own
      per-edition reconstruction: names, dates, parents, team counts)
  contests/data/triage-families.json                            (cms_id per row,
      for the ledger side)

Outputs (dry-run by default; --write to apply):
  A) series/<id>.yaml stubs for the adopted MAINLINE families
  B) registry/cms-triage.yaml additions for adopted part-of-parent / registry /
     locals / specials rows (reasons: preliminary | non-mainline | minor | special)

Run in the VM (needs pyyaml):  python3 tools/generate_family_stubs.py [--write]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import yaml

CONTESTS = Path(__file__).resolve().parent.parent
INVENTORY = CONTESTS.parent.parent / "icpc-history" / "contest-inventory" / "master_contests.csv"

# Adopted mainline families: series id -> (series name, regex on the CSV `series`
# column, optional year filter). Held families are absent by design.
MAINLINE = {
    "colombia-maraton": ("Colombia Maratón Nacional de Programación (ACIS/REDIS)",
                         r"Maraton Nacional de Programacion ACIS", None),
    "tap": ("Torneo Argentino de Programación",
            r"Torneo Argentino", None),
    "gran-premio-mexico": ("ICPC Gran Premio de México",
                           r"Gran Premio de M", None),
    "gran-premio-centroamerica": ("ICPC Gran Premio de Centroamérica",
                                  r"Gran Premio de Centroam", None),
    "bolivia-national": ("Competencia Boliviana de Programación",
                         r"Bolivia.*(Preliminar|Competencia)|Competencia.*Bolivia", None),
    "torneo-chileno": ("Torneo Chileno de Programación",
                       r"Torneo Chileno", None),
    "caribbean-national": ("ICPC Caribbean National Contests",
                           r"Caribbean National", (2010, 2019)),
    "thailand-national": ("ICPC Thailand National On-site Programming Contest",
                          r"Thailand National", None),
    "mongolia-national": ("ICPC Mongolia National Programming Contest",
                          r"Mongolia National", None),
    "myanmar-mcpc": ("Myanmar Collegiate Programming Contest",
                     r"Myanmar", None),
    "taiwan-ncpc": ("Taiwan National Collegiate Programming Contest (MOE NCPC)",
                    r"Kaohsiung.*Taiwan National|Taiwan National.*(Group|NCPU|NCTU|Programming)", None),
    "oman-capital": ("ICPC Oman Capital Sub-region Collegiate Programming Contest",
                     r"Oman Capital Sub-region", None),
    "oman-coastline": ("ICPC Oman Coastline Sub-region Collegiate Programming Contest",
                       r"Oman Coastline Sub-region", None),
    "oman-midland": ("ICPC Oman Midland Sub-region Collegiate Programming Contest",
                     r"Oman Midland Sub-region", None),
    "oman-southern": ("ICPC Oman Southern Sub-region Collegiate Programming Contest",
                      r"Oman Southern Sub-region", None),
    "oman-oriental": ("ICPC Oman Oriental Sub-region Collegiate Programming Contest",
                      r"Oman Oriental Sub-region", None),
}

# Ledger side: adopted triage families -> cms-triage reason.
LEDGER_REASON = {
    # part-of-parent (identity-less rounds of catalogued parents)
    "tehran-online": "preliminary", "japan-first-round": "preliminary",
    "jakarta-indonesia-national": "preliminary", "moscow-open": "preliminary",
    "slovenia-rounds": "preliminary", "india-area-rounds": "preliminary",
    "dhaka-prelim": "preliminary", "south-pacific-legacy": "preliminary",
    # per-country cuts of the joint regional
    "venezuela-finals": "preliminary", "ecuador": "preliminary",
    # registry (real but off the WF path)
    "china-provincial": "non-mainline", "china-metropolitan": "non-mainline",
    # locals
    "arab-uni-locals": "minor", "mexico-locals": "minor", "mexico-states": "minor",
    "angola-local": "minor", "caribbean-local": "minor",
    # specials (no WF path by design)
    "girls-special": "special", "seniors-masters": "special",
    "kickoff-individual": "special",
}
# Families whose rows become MAINLINE editions get no ledger entry (their cms_ids
# land in the series files). Held families are skipped entirely.
HELD = {"ukraine-oblasts", "brazil-first-phase", "vietnam-national",
        "kazakhstan-octafinal", "afghanistan", "asia-nationals-misc",
        "taiwan-rounds", "thailand-rounds", "caribbean", "future-shells",
        "handled-elsewhere", "unmatched", "tajikistan-dupe", "dhaka-secondary",
        "kharagpur-2012"}
# (taiwan-rounds/thailand-rounds/caribbean worklist rows mix mainline+prelim
#  sub-cases; their mainline halves come from master_contests below, and the
#  remainder is settled with the six held calls — so their LEDGER rows wait.)

HEADER = "# Maintained in-repo; last bulk edit: tools/generate_family_stubs.py (family ruling 2026-09-04).\n"


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null"))


def existing_ids():
    ids = set()
    for f in (CONTESTS / "series").glob("*.yaml"):
        doc = yaml.safe_load(f.read_text()) or {}
        for c in doc.get("contests") or []:
            ids.add(c["id"])
    return ids


def build_stubs():
    rows = list(csv.DictReader(open(INVENTORY, encoding="utf-8")))
    out = {}
    for sid, (sname, pat, yrs) in MAINLINE.items():
        rx = re.compile(pat, re.I)
        eds = []
        for r in rows:
            if not rx.search(r.get("series") or ""):
                continue
            try:
                y = int((r.get("year") or "0")[:4])
            except ValueError:
                continue
            if not y or (yrs and not (yrs[0] <= y <= yrs[1])):
                continue
            eds.append((y, r))
        eds.sort(key=lambda t: t[0])
        entries = []
        for y, r in eds:
            e = {"id": f"{sid}-{y}", "season": y + 1}
            nm = (r.get("full_name") or r.get("name_best_guess") or f"{y} {sname}").strip()
            e["name"] = re.sub(r"^The\s+", "", nm)
            dt = (r.get("date") or "").strip()
            if re.match(r"^\d{4}-\d{2}-\d{2}$", dt):
                e["date"] = dt
            cid = (r.get("contest_id") or "").strip()
            e["cms_ids"] = [int(cid)] if cid.isdigit() else []
            par = (r.get("parent") or "").strip()
            if par and par not in ("n/a", "none", "lac", "nac", "wf"):
                e["parent"] = par
            teams = ""
            m = re.search(r"(\d+) teams", r.get("comments") or "")
            if m:
                teams = f"{m.group(1)} teams; "
            e["notes"] = (f"{teams}from icpc-history master_contests "
                          f"(family ruling 2026-09-04; src: {(r.get('source') or '')[:60]})")
            entries.append(e)
        # chain next links
        for a, b in zip(entries, entries[1:]):
            a["next"] = b["id"]
        out[sid] = (sname, entries)
    return out


def build_ledger():
    fam = json.loads((CONTESTS / "data" / "triage-families.json").read_text())["families"]
    adds = []
    for fname, fdata in fam.items():
        reason = LEDGER_REASON.get(fname)
        if not reason or fname in HELD:
            continue
        for r in fdata["rows"]:
            cid = r.get("cms_id")
            if not cid or not str(cid).isdigit():
                continue
            a = {"cms_id": int(cid), "reason": reason,
                 "name": (r.get("name") or "")[:110],
                 "family": fname}
            if r.get("date"):
                a["date"] = r["date"]
            adds.append(a)
    return adds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    have = existing_ids()
    stubs = build_stubs()
    total = 0
    for sid, (sname, entries) in sorted(stubs.items()):
        fresh = [e for e in entries if e["id"] not in have]
        dupe = len(entries) - len(fresh)
        print(f"{sid:28} {len(fresh):3} new editions"
              + (f" ({dupe} already in catalogue - skipped)" if dupe else "")
              + (f"  [{entries[0]['id']} .. {entries[-1]['id']}]" if entries else "  [EMPTY - check regex]"))
        total += len(fresh)
        if args.write and fresh:
            f = CONTESTS / "series" / f"{sid}.yaml"
            if f.exists():
                doc = yaml.safe_load(f.read_text())
            else:
                doc = {"series": {"id": sid, "name": sname}, "contests": []}
            doc.setdefault("contests", []).extend(fresh)
            f.write_text(HEADER + yaml.dump(doc, Dumper=Dumper, sort_keys=False,
                                            allow_unicode=True, width=100))
    print(f"= {total} new mainline editions across {len(stubs)} series")

    adds = build_ledger()
    trg = CONTESTS / "registry" / "cms-triage.yaml"
    doc = yaml.safe_load(trg.read_text())
    known = {e["cms_id"] for e in doc.get("excluded") or []}
    fresh = [a for a in adds if a["cms_id"] not in known]
    from collections import Counter
    print(f"ledger: {len(fresh)} new cms-triage rows "
          f"({len(adds)-len(fresh)} already present) "
          f"by reason: {dict(Counter(a['reason'] for a in fresh))}")
    if args.write and fresh:
        doc["excluded"] = (doc.get("excluded") or []) + fresh
        trg.write_text(yaml.dump(doc, Dumper=Dumper, sort_keys=False,
                                 allow_unicode=True, width=110))
    if not args.write:
        print("(dry run - nothing written; add --write)")
    else:
        print("written; now: python3 tools/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
