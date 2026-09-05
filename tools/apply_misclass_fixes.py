#!/usr/bin/env python3
"""Apply ratified misclassification fixes from data/misclass-fix-candidates.json.

Nothing applies by default — selection is explicit, so Fredrik can ratify item
by item (see reports/misclassification-audit-2026-09-02.md for the evidence):

  python3 tools/apply_misclass_fixes.py                          # menu
  python3 tools/apply_misclass_fixes.py --edits all --dry-run    # preview
  python3 tools/apply_misclass_fixes.py --edits all --adds all --write
  python3 tools/apply_misclass_fixes.py --edits kuwait-2010,kuwait-2011 --write

Safety: every edit checks the CURRENT value equals the recorded 'from' before
changing it; a mismatch refuses that one edit (the file moved under us) and the
rest proceed. Adds create catalogue-shaped stubs (new series files if needed);
candidate URLs from the audit go into the entry note, not web/results — the URL
waves own those. --shells adds the 2027-season upcoming shells. Run
tools/validate.py afterwards. Nothing is written without --write.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(
    type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null")
)

# Editorial enrichment for the 'adds' (names follow existing series style).
ADD_META = {
    "wuhan-2025": {"name": "2025 ICPC Asia Wuhan Regional Contest",
                   "series_name": "ICPC Asia Wuhan Regional Contest",
                   "pred": "wuhan-2009"},
    "peradeniya-2025": {"name": "2025 ICPC Asia Peradeniya Regional Contest",
                        "series_name": "ICPC Asia Peradeniya Regional Contest"},
    "tajikistan-2023": {"name": "2023 ICPC Tajikistan Regional Contest",
                        "series_name": "ICPC Tajikistan Regional Contest"},
    "tajikistan-2024": {"name": "2024 ICPC Tajikistan Regional Contest",
                        "series_name": "ICPC Tajikistan Regional Contest",
                        "pred": "tajikistan-2023"},
    "tajikistan-2025": {"name": "2025 ICPC Tajikistan Regional Contest",
                        "series_name": "ICPC Tajikistan Regional Contest",
                        "pred": "tajikistan-2024"},
    "turkmenistan-2025": {"name": "2025 ICPC Turkmenistan Regional Contest",
                          "series_name": "ICPC Turkmenistan Regional Contest"},
}
SHELL_META = {  # id -> (season, parent)
    "wuhan-2026": (2027, "wf-2027"), "nanchang-2026": (2027, "wf-2027"),
    "hefei-2026": (2027, "wf-2027"), "jinan-2026": (2027, "wf-2027"),
    "kunming-2026": (2027, "wf-2027"), "peradeniya-2026": (2027, "awc-2026"),
    "tajikistan-2026": (2027, "nerc-2026"), "turkmenistan-2026": (2027, "nerc-2026"),
}
HEADER = "# Maintained in-repo; last bulk edit: tools/apply_misclass_fixes.py (audit 2026-09-02).\n"


def load_series():
    """-> (files: {path: sdoc}, index: {contest_id: (path, entry)})"""
    files, index = {}, {}
    for f in sorted((ROOT / "series").glob("*.yaml")):
        sdoc = yaml.safe_load(f.read_text())
        files[f] = sdoc
        for c in sdoc.get("contests") or []:
            index[c["id"]] = (f, c)
    return files, index


def pick(arg: str, universe: list[str]) -> list[str]:
    if not arg:
        return []
    if arg == "all":
        return universe
    sel = [s.strip() for s in arg.split(",") if s.strip()]
    unknown = [s for s in sel if s not in universe]
    if unknown:
        raise SystemExit(f"unknown ids {unknown}; available: {universe}")
    return sel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixes", default=str(ROOT / "data" / "misclass-fix-candidates.json"))
    ap.add_argument("--edits", default="", help="'all' or comma list of edit ids")
    ap.add_argument("--adds", default="", help="'all' or comma list of add ids")
    ap.add_argument("--shells", default="", help="'all' or comma list of 2027 shell ids")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(Path(args.fixes).read_text())
    edits = {e["id"]: e for e in doc["edits"]}
    adds = {a["id"]: a for a in doc["adds"]}
    shells = {s["id"]: s for s in doc.get("upcoming_2027_shells", [])}

    if not (args.edits or args.adds or args.shells):
        print("Available (nothing selected — pick with --edits/--adds/--shells):\n")
        for e in doc["edits"]:
            print(f"  edit {e['id']:24} {e['field']}: {e['from']} -> {e['to']}"
                  f"   [{e.get('confidence', '?')}]")
        for a in doc["adds"]:
            print(f"  add  {a['id']:24} season {a['season']}, {a['date']}, parent {a['parent']}, "
                  f"cms {a['cms_ids']}, {a.get('teams', '?')} teams")
        for s in shells:
            print(f"  shell {s}")
        for t in doc.get("triage_new_rows", []):
            print(f"  (fyi, no action) cms {t['cms_id']}: {t['name']} -> {t['suggest']}")
        return 0

    sel_edits = pick(args.edits, list(edits))
    sel_adds = pick(args.adds, list(adds))
    sel_shells = pick(args.shells, list(shells))

    files, index = load_series()
    touched: set[Path] = set()
    log, refused = [], []

    for eid in sel_edits:
        e = edits[eid]
        if eid not in index:
            refused.append(f"{eid}: not in catalogue")
            continue
        f, c = index[eid]
        field, frm, to = e["field"], e["from"], e["to"]
        cur = c.get(field)
        if cur != frm and not (frm is None and cur is None):
            refused.append(f"{eid}: {field} is {cur!r}, expected {frm!r} — skipped")
            continue
        c[field] = to
        note = f"{eid}: {field} {frm!r} -> {to!r}"
        for afield, spec in (e.get("also") or {}).items():
            acur = c.get(afield)
            if acur != spec["from"]:
                refused.append(f"{eid}: also.{afield} is {acur!r}, expected {spec['from']!r}")
                continue
            c[afield] = spec["to"]
            note += f"; {afield} -> {spec['to']}"
        touched.add(f)
        log.append(note)

    for aid in sel_adds + sel_shells:
        if aid in index:
            refused.append(f"{aid}: already in catalogue — skipped")
            continue
        sid = aid.rsplit("-", 1)[0]
        sf = ROOT / "series" / f"{sid}.yaml"
        if sf in files:
            sdoc = files[sf]
        else:
            meta = ADD_META.get(aid, {})
            sdoc = {"series": {"id": sid, "name": meta.get(
                "series_name", f"ICPC {sid.title()} Regional Contest")}, "contests": []}
            files[sf] = sdoc
        if aid in adds:
            a = adds[aid]
            # meta may live in ADD_META (the 2026-09-02 audit set) or inline in the
            # fixes file itself (later packs pass name/series_name per entry).
            meta = ADD_META.get(aid) or {"name": a.get("name"),
                                         "series_name": a.get("series_name")}
            if not meta.get("name"):
                raise SystemExit(f"{aid}: no name in ADD_META or fixes file")
            entry = {"id": aid, "season": a["season"], "name": meta["name"],
                     "cms_ids": a.get("cms_ids") or [], "parent": a["parent"]}
            if a.get("date"):
                entry["date"] = a["date"]
            if a.get("finder"):
                entry["icpc_standings"] = (
                    f"https://icpc.global/regionals/finder/{a['finder']}/standings")
            if a.get("pred"):
                ADD_META.setdefault(aid, {})["pred"] = a["pred"]
            bits = [f"added from misclass audit 2026-09-02 ({a.get('teams')} teams, "
                    f"{a.get('results')} results in CMS)"]
            for k in ("scoreboard_candidate", "standings_candidate"):
                if a.get(k):
                    bits.append(f"{k}: {a[k]}")
            for u in a.get("web_candidates", []):
                bits.append(f"web candidate: {u}")
            if a.get("note"):
                bits.append(a["note"])
            entry["notes"] = "; ".join(bits)
        else:
            season, parent = SHELL_META[aid]
            year = aid.rsplit("-", 1)[1]
            sname = sdoc["series"]["name"].removeprefix("ICPC ")
            entry = {"id": aid, "season": season, "name": f"{year} {sname}",
                     "cms_ids": shells[aid]["cms_ids"], "parent": parent,
                     "status": "upcoming",
                     "notes": "upcoming shell from misclass audit 2026-09-02"}
        sdoc.setdefault("contests", []).append(entry)
        index[aid] = (sf, entry)
        touched.add(sf)
        log.append(f"{aid}: added to {sf.name} (season {entry['season']}, "
                   f"parent {entry['parent']})")
        pred = ADD_META.get(aid, {}).get("pred")
        if pred and pred in index:
            pf, pc = index[pred]
            if pc.get("next") != aid:
                pc["next"] = aid
                touched.add(pf)
                log.append(f"{pred}: next -> {aid}")

    for line in log:
        print("apply:", line)
    for line in refused:
        print("REFUSED:", line)
    if not args.write or args.dry_run:
        print(f"\n(dry run — {len(touched)} file(s) WOULD change; nothing written)")
        return 0
    for f in sorted(touched):
        body = yaml.dump(files[f], Dumper=Dumper, sort_keys=False,
                         allow_unicode=True, width=100)
        f.write_text(HEADER + body)
    print(f"\nwrote {len(touched)} file(s); now: python3 tools/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
