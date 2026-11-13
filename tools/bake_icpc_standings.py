#!/usr/bin/env python3
"""File the ICPC standings we already have on disk as copies of their `icpc_standings` sources.

An `icpc_standings` source is a page of the ICPC CMS (icpc.global/regionals/finder/<slug>/standings):
a JavaScript app, so fetching the page stores an empty shell. The data behind it comes from the
open API, and two dumps of it sit next to this repo:
    ../icpc_all_standings.json            (2,278 contests, DB fetch 2026-04-26)
    ../icpc_new_standings_from_db.json    (154 more, extracted 2026-08-31)
Team-level fields only (team, institution, rank, solved, time, citations) — no people.

The first pass (tools/legacy/bake_api_standings.py, 2026-09-04) rendered only the 286 contests
whose ICPC standings were their *only* result. This does the rest: every contest that has an
`icpc_standings` source without a copy and whose CMS id has rows in a dump gets
    ../archive/<series>/<contest>/standings/api-<date>/{standings.html, standings.json, manifest.json}
an entry in ../archive/index.json (source icpc-api-archive, fetched = the dump date) and the
capture path under the source's `archived:`. A third dump, ../icpc_standings_topup.json
(tools/topup_icpc_standings.py), holds the contests the first two lack; the ids it asked that
have no rows at all are written to data/icpc-standings-empty.json — their standings page is empty.

Usage: python3 tools/bake_icpc_standings.py [--write] [--limit N]
Idempotent: a source that already names an api-* capture is skipped. Afterwards:
    python3 tools/build_resources.py && python3 tools/validate.py
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import add_archived, archived, by_role, dump_series, load_series, normalise_source  # noqa: E402

BASE = ROOT.parent
ARCHIVE = BASE / "archive"
TOOL = "bake_icpc_standings.py/1.0"
TODAY = datetime.date.today()
STAMP = "api-" + TODAY.strftime("%Y%m%d")
DUMPS = (("icpc_all_standings.json", "2026-04-26"), ("icpc_new_standings_from_db.json", "2026-04-26"),
         ("icpc_standings_topup.json", None))   # tools/topup_icpc_standings.py: each entry carries its own fetch date
COLS = [("rank", "Rank"), ("teamName", "Team"), ("institution", "Institution"), ("problemsSolved", "Solved"),
        ("totalTime", "Time"), ("medalCitation", "Medal"), ("citation", "Citation"),
        ("siteCitation", "Site citation"), ("honorableMentionCitation", "HM")]


def render(entry: dict, cid: str, cms: str, fetched: str) -> str:
    rows = sorted(entry["standings"], key=lambda r: (r.get("rank") is None, r.get("rank") or 0))
    used = [(k, h) for k, h in COLS if k in ("rank", "teamName", "problemsSolved", "totalTime")
            or any(r.get(k) not in (None, "", 0) for r in rows)]
    name = html.escape(entry.get("name") or cid)
    out = ["<!DOCTYPE html><html><head><meta charset='utf-8'>", f"<title>{name} — standings</title>",
           "<style>body{font:14px/1.4 system-ui;margin:1.5em}table{border-collapse:collapse}"
           "td,th{border:1px solid #ccc;padding:2px 8px;text-align:left}th{background:#eee}"
           "td:first-child,td:nth-child(4),td:nth-child(5){text-align:right}</style></head><body>",
           f"<h1>{name}</h1>",
           f"<p>{html.escape(entry.get('abbr') or '')} — ICPC year {entry.get('year')} — {len(rows)} teams — rendered {TODAY} "
           f"from the icpc.global public API archive (contest id {cms}, DB fetch {fetched}).</p>",
           "<table><tr>" + "".join(f"<th>{h}</th>" for _, h in used) + "</tr>"]
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{html.escape(str(r.get(k))) if r.get(k) is not None else ''}</td>" for k, _ in used) + "</tr>")
    out.append(f"</table><p>Source data preserved alongside as standings.json ({TOOL}).</p></body></html>")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    data, when, empty = {}, {}, {}
    for name, fetched in DUMPS:
        p = BASE / name
        if not p.exists():
            if fetched is None:
                continue
            print(f"missing dump: {p}")
            return 1
        asked = {}
        for k, v in json.loads(p.read_text()).items():
            if v.get("standings"):
                data[k], when[k] = v, fetched or v.get("fetched")
            elif fetched is None:
                asked[k] = v
        if fetched is None:   # the ids the open API answered with no rows: the CMS holds no standings for them
            empty[name] = asked
    idx_p = ARCHIVE / "index.json"
    idx = json.loads(idx_p.read_text())
    have = {c["path"] for c in idx["captures"]}
    done = skipped = no_rows = no_id = 0
    none_in_cms: dict = {}
    touched = {}
    series = load_series()
    for sid, doc in series.items():
        for i, c in enumerate(doc["contests"]):
            srcs = by_role(c, "icpc_standings")
            if not srcs:
                continue
            s = next((x for x in srcs if "icpc.global" in x["url"]), srcs[0])
            if any("/api-" in p for x in srcs for p in archived(x)):
                skipped += 1
                continue
            ids = [str(x) for x in c.get("cms_ids") or []]
            if not ids:
                no_id += 1
                continue
            best = max((x for x in ids if x in data), key=lambda x: len(data[x]["standings"]), default=None)
            if best is None:
                no_rows += 1
                asked = [v for e in empty.values() for k, v in e.items() if k in ids]
                if len(asked) == len(ids):   # every id was asked and none has rows
                    none_in_cms[c["id"]] = {"cms_ids": [int(x) for x in ids], "asked": max(v.get("fetched") or "" for v in asked), "url": s["url"]}
                continue
            if args.limit and done >= args.limit:
                break
            entry, fetched, cid = data[best], when[best], c["id"]
            rel = f"{sid}/{cid}/standings/{STAMP}"
            page = render(entry, cid, best, fetched)
            sha = hashlib.sha256(page.encode()).hexdigest()
            if args.write:
                dest = ARCHIVE / rel
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "standings.html").write_text(page, encoding="utf-8")
                (dest / "standings.json").write_text(json.dumps(
                    {"cms_id": int(best), "fetched": fetched, "name": entry.get("name"), "abbr": entry.get("abbr"),
                     "year": entry.get("year"), "standings": entry["standings"]}, indent=1, ensure_ascii=False))
                (dest / "manifest.json").write_text(json.dumps(
                    {"schema_version": 1, "contest": cid, "artifact": "standings", "cms_id": int(best), "url": s["url"],
                     "source": "icpc-api-archive", "fetched": fetched, "baked": TODAY.isoformat(), "content_file": "standings.html",
                     "content_type": "text/html; charset=utf-8", "size": len(page.encode()), "sha256": sha,
                     "teams": len(entry["standings"]), "tool": TOOL}, indent=1, ensure_ascii=False))
                path = rel + "/standings.html"
                if path not in have:
                    idx["captures"].append({"contest": cid, "artifact": "standings", "path": path, "url": s["url"],
                                            "source": "icpc-api-archive", "fetched": fetched, "sha256": sha,
                                            "size": len(page.encode()), "content_type": "text/html; charset=utf-8"})
                    have.add(path)
                add_archived(s, path)
                s.setdefault("note", f"rendered from the icpc.global API standings archive (cms {best}, {len(entry['standings'])} teams, DB fetch {fetched})")
                c["sources"] = [normalise_source(x) if x is s else x for x in c["sources"]]   # key order of this one source only
                touched[sid] = doc
            done += 1
    print(f"baked: {done} | already held: {skipped} | CMS id without rows in the dumps: {no_rows} | no CMS id: {no_id}"
          + ("" if args.write else "  (dry run)"))
    if args.write and none_in_cms:
        (ROOT / "data" / "icpc-standings-empty.json").write_text(json.dumps(
            {"what": "contests whose ICPC standings page holds nothing: the open API returned no rows for every CMS id of the contest",
             "tool": TOOL, "contests": dict(sorted(none_in_cms.items()))}, indent=1) + "\n")
        print(f"{len(none_in_cms)} contests have an icpc_standings source and no standings in the CMS -> data/icpc-standings-empty.json")
    if args.write and done:
        idx_p.write_text(json.dumps(idx, indent=1, ensure_ascii=False))
        for sid, doc in touched.items():
            dump_series(sid, doc, "bake_icpc_standings.py")
        print(f"{len(touched)} series files updated; archive/index.json has {len(idx['captures'])} captures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
