#!/usr/bin/env python3
"""Materialize finder-only standings from the icpc.global API archive.

286 catalogue contests have ONLY the JS finder link as a result while their full
standings sit on disk (icpc_all_standings.json + icpc_new_standings_from_db.json,
fetched from the open /api/contest/public/ endpoints; team-level fields only).
This renders each as a self-contained HTML table + raw JSON in the archive and
appends a `standings` result entry (finder URL + archived path) to the catalogue.

Run in the VM from the contests repo:  python3 tools/bake_api_standings.py
[--limit N] [--write]. Idempotent: contests already holding an api-* archived
standings entry are skipped.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
from pathlib import Path

import yaml

CONTESTS = Path(__file__).resolve().parent.parent
ROOT = CONTESTS.parent                      # ~/Claude/icpc-contests
ARCHIVE = ROOT / "archive"
TOOL = "bake_api_standings.py/1.0"
STAMP = "api-" + datetime.date.today().strftime("%Y%m%d")
FETCHED = "2026-04-26"                      # api_fetch_log high-water mark

COLS = [("rank", "Rank"), ("teamName", "Team"), ("institution", "Institution"),
        ("problemsSolved", "Solved"), ("totalTime", "Time"),
        ("medalCitation", "Medal"), ("citation", "Citation"),
        ("siteCitation", "Site citation"), ("honorableMentionCitation", "HM")]


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null"))


def render(entry: dict, cid: str, cms: int) -> str:
    rows = sorted(entry["standings"], key=lambda r: (r.get("rank") is None, r.get("rank")))
    used = [(k, h) for k, h in COLS if any(r.get(k) not in (None, "", 0) or k in
            ("rank", "teamName", "problemsSolved", "totalTime") for r in rows)]
    out = ["<!DOCTYPE html><html><head><meta charset='utf-8'>",
           f"<title>{html.escape(entry.get('name') or cid)} — standings</title>",
           "<style>body{font:14px/1.4 system-ui;margin:1.5em}table{border-collapse:collapse}"
           "td,th{border:1px solid #ccc;padding:2px 8px;text-align:left}"
           "th{background:#eee}td:first-child,td:nth-child(4),td:nth-child(5)"
           "{text-align:right}</style></head><body>",
           f"<h1>{html.escape(entry.get('name') or cid)}</h1>",
           f"<p>{html.escape(entry.get('abbr') or '')} — ICPC year {entry.get('year')} — "
           f"{len(rows)} teams — rendered {datetime.date.today()} from the icpc.global "
           f"public API archive (contest id {cms}, DB fetch {FETCHED}).</p>",
           "<table><tr>" + "".join(f"<th>{h}</th>" for _, h in used) + "</tr>"]
    for r in rows:
        out.append("<tr>" + "".join(
            f"<td>{html.escape(str(r.get(k))) if r.get(k) is not None else ''}</td>"
            for k, _ in used) + "</tr>")
    out.append(f"</table><p>Source data preserved alongside as standings.json ({TOOL}).</p></body></html>")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    cov = json.loads((CONTESTS / "reports" / "finder-standings-coverage.json").read_text())
    data = json.loads((ROOT / "icpc_all_standings.json").read_text())
    data.update(json.loads((ROOT / "icpc_new_standings_from_db.json").read_text()))

    series_docs = {}
    where = {}
    for f in sorted((CONTESTS / "series").glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        series_docs[f] = doc
        for c in doc.get("contests") or []:
            where[c["id"]] = (f, doc, c)

    done = skipped = missing = 0
    touched = set()
    items = sorted(cov["covered"].items())
    if args.limit:
        items = items[: args.limit]
    for cid, cms_ids in items:
        if cid not in where:
            continue
        f, doc, c = where[cid]
        res = c.setdefault("results", {}) if args.write else (c.get("results") or {})
        st = res.get("standings") or []
        if any("api-" in (e.get("archived") or "") for e in st):
            skipped += 1
            continue
        best = None
        for x in cms_ids:
            e = data.get(str(x))
            if e and e.get("standings") and (best is None or
                    len(e["standings"]) > len(data[str(best)]["standings"])):
                best = x
        if best is None:
            missing += 1
            continue
        entry = data[str(best)]
        sid = doc["series"]["id"]
        rel = f"{sid}/{cid}/standings/{STAMP}"
        if args.write:
            dest = ARCHIVE / rel
            dest.mkdir(parents=True, exist_ok=True)
            page = render(entry, cid, best)
            (dest / "standings.html").write_text(page, encoding="utf-8")
            (dest / "standings.json").write_text(json.dumps(
                {"cms_id": best, "fetched": FETCHED, "name": entry.get("name"),
                 "abbr": entry.get("abbr"), "year": entry.get("year"),
                 "standings": entry["standings"]}, indent=1, ensure_ascii=False))
            man = {"schema_version": 1, "contest": cid, "artifact": "standings",
                   "cms_id": best, "url": c.get("icpc_standings"),
                   "source": "icpc-api-archive", "fetched": FETCHED,
                   "baked": datetime.date.today().isoformat(),
                   "content_file": "standings.html",
                   "content_type": "text/html; charset=utf-8",
                   "size": len(page.encode()),
                   "sha256": hashlib.sha256(page.encode()).hexdigest(),
                   "teams": len(entry["standings"]), "tool": TOOL}
            tmp = dest / "manifest.json.tmp"
            tmp.write_text(json.dumps(man, indent=1, ensure_ascii=False))
            tmp.replace(dest / "manifest.json")
            res.setdefault("standings", []).append({
                "url": c.get("icpc_standings"),
                "archived": rel + "/standings.html",
                "note": f"rendered from the icpc.global API standings archive "
                        f"(cms {best}, {len(entry['standings'])} teams, DB fetch {FETCHED})"})
            touched.add(f)
        done += 1
    print(f"baked: {done} | already had api- entry: {skipped} | no rows found: {missing}"
          + ("" if args.write else "  (dry run)"))
    if args.write:
        H = "# Maintained in-repo; last bulk edit: tools/bake_api_standings.py (finder unlock 2026-09-04).\n"
        for f in sorted(touched):
            f.write_text(H + yaml.dump(series_docs[f], Dumper=Dumper, sort_keys=False,
                                       allow_unicode=True, width=100))
        print(f"{len(touched)} series files updated; now: python3 tools/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
