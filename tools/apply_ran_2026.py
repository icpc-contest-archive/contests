#!/usr/bin/env python3
"""Autumn 2026: contests that ran stop being `upcoming` (ruling of 2026-11-12). Deterministic;
a second run changes nothing.

Rule: a contest stops being upcoming when its date has passed and a result source or a judge page
shows it ran.

Input, frozen in data/import/autumn-2026-probe-2026-11-12.json (read on 2026-11-12):
  api   for every upcoming contest with a CMS id: whether the ICPC CMS holds ranked standings, and
        the contest record's start and end date and links;
  hits  last year's addresses of each contest with the year moved on (naq25 -> naq26, /2025/ ->
        /2026/), kept when they answered and are not last year's page again.

What is added: the ICPC standings page where the CMS has ranked standings; the hits that pass
`accept`; a few addresses checked by hand (EXTRA); the CMS record's own results link where it is
a results page (CMS_RESULTS). What is set: `date`, when the entry has none, from the contest's
CMS site date or the CMS record's last day (DATE where the two disagree or the CMS has none).

  python3 tools/apply_ran_2026.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from add_contests_2026_11_12 import place  # noqa: E402
from catalogue import RESULT_ROLES, add_source, dump_series, load_series  # noqa: E402

TOOL = "apply_ran_2026.py"
DAY = "2026-11-12"
DATA = ROOT / "data" / "import" / "autumn-2026-probe-2026-11-12.json"
LATAM = "https://scorelatam.naquadah.com.br/latam-2026/"
CENTRAL = "https://nacentral26.kattis.com/contests/nacentral26d{}/standings"
GC = "ICPC Grand Central 2026 (Rocky/Mid-Central): one contest for the Rocky Mountain and Mid-Central regionals"
# contest: [(url, role, note)] — fetched and read on 2026-11-12
EXTRA = {
    "mcpc-2026": [(CENTRAL.format(1), "scoreboard", GC), (CENTRAL.format(2), "scoreboard", GC)],
    "rmc-2026": [(CENTRAL.format(2), "scoreboard", GC)],
    "caribbean-2026": [(LATAM, "scoreboard", None)],
    "central-america-2026": [(LATAM, "scoreboard", None)],
    "south-america-south-2026": [(LATAM, "scoreboard", None)],
}
MOVED = {"https://scorelatam.naquadah.com.br/subbr-2026/": "brazil-first-phase-2026"}  # the first phase's scoreboard, not the final's
CMS_RESULTS = {"south-pacific-2026": "scoreboard", "south-pacific-division-2026": "scoreboard", "south-russia-2026": "standings"}
DATE = {  # the CMS site date and the CMS record's last day disagree
    "brazil-2026": ("2026-11-07", "the regional's contest day (CMS site date; the CMS record runs to 8 Nov)"),
    "mexico-2026": ("2026-11-07", "the regional's contest day (the CMS record's last day; the site date is 6 Nov)"),
    "ctuo-2026": ("2026-10-24", "second day of the event, as for earlier CTU Opens (the CMS site date is 23 Oct)"),
    "caribbean-2026": ("2026-11-07", "the Latin America regional's contest day: one contest for every site (no date in the CMS)"),
    "central-america-2026": ("2026-11-07", "the Latin America regional's contest day: one contest for every site (no date in the CMS)"),
    "south-america-south-2026": ("2026-11-07", "the Latin America regional's contest day: one contest for every site (no date in the CMS)"),
}
EVIDENCE = set(RESULT_ROLES) | {"judge_page"}


def accept(h: dict) -> bool:
    title = h.get("title") or ""
    if h["same_as_last_year"] or ("2025" in title and "2026" not in title):
        return False
    if h.get("final") and h["final"].rstrip("/").endswith("/contests"):
        return False  # redirected to a contest list
    if re.search(r"kattis\.com/contests/[^/]+/standings/\d+$", h["url"]):
        return False  # a filter id of last year's contest
    in_url = "2026" in h["url"] or bool(re.search(r"(?<![0-9])26(?![0-9])", h["url"]))
    return in_url if h["pdf"] else bool(h["year_in_title"] or (in_url and h["mentions_year"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    data = json.loads(DATA.read_text())
    api, hits = data["api"], data["hits"]
    series = load_series()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    touched: set[str] = set()
    flipped, waiting, leads = [], [], []

    def add(cid: str, url: str, role: str, note: str | None = None) -> bool:
        sid, c = where[cid]
        judge = "kattis" if role == "judge_page" and "kattis.com" in url else None
        if role == "judge_page" and not judge:
            raise SystemExit(f"{cid}: judge page on an unknown judge: {url}")
        if add_source(c, url, role, note=note, judge=judge)[1]:
            touched.add(sid)
            return True
        return False

    for h in hits:
        if h["url"] in MOVED and accept(h):
            for role in h["roles"]:
                add(MOVED[h["url"]], h["url"], role)
    for cid in sorted(where):
        sid, c = where[cid]
        if c.get("status") != "upcoming":
            for url, role, note in EXTRA.get(cid, []):
                add(cid, url, role, note)
            continue
        rec = api.get(cid) or {}
        added: list[str] = []
        if rec.get("ranked") and rec.get("short"):
            if add(cid, f"https://icpc.global/regionals/finder/{rec['short']}/standings", "icpc_standings"):
                added.append("ICPC standings")
        for h in hits:
            if h["contest"] == cid and h["url"] not in MOVED and accept(h):
                if any([add(cid, h["url"], role) for role in h["roles"]]):
                    added.append(h["roles"][0])
        for url, role, note in EXTRA.get(cid, []):
            if add(cid, url, role, note):
                added.append(role)
        if cid in CMS_RESULTS and rec.get("resultsUrl"):
            if add(cid, rec["resultsUrl"], CMS_RESULTS[cid], "results link in the contest's ICPC CMS record"):
                added.append(CMS_RESULTS[cid])
        elif rec.get("resultsUrl") and not any(s["url"].rstrip("/") == rec["resultsUrl"].rstrip("/") for s in c.get("sources") or []):
            leads.append((cid, rec["resultsUrl"]))
        site_dates = sorted({s["date"] for s in c.get("sites") or [] if s.get("date")})
        date, date_from = c.get("date"), "the catalogue"
        if not date:
            if cid in DATE:
                date, date_from = DATE[cid]
            elif len(site_dates) == 1:
                date, date_from = site_dates[0], "CMS site date"
            elif rec.get("endDate"):
                date = rec["endDate"]
                date_from = ("CMS contest record" if rec.get("startDate") == rec["endDate"]
                             else f"last day of the CMS contest record ({rec.get('startDate')} to {rec['endDate']})")
        evidence = sorted({r for s in c.get("sources") or [] for r in s["roles"] if r in EVIDENCE})
        if date and date < DAY and evidence:
            del c["status"]
            if not c.get("date"):
                c["date"] = date
            line = (f"ran {date}: shown by its {', '.join(e.replace('_', ' ') for e in evidence)} source(s); date from {date_from} "
                    f"(ruling {DAY}: upcoming ends when the date has passed and a result source or judge page shows the contest ran)")
            c.setdefault("provenance", []).append(line)
            series[sid]["contests"][series[sid]["contests"].index(c)] = place(c)
            where[cid] = (sid, series[sid]["contests"][[x["id"] for x in series[sid]["contests"]].index(cid)])
            touched.add(sid)
            flipped.append((cid, date, evidence, added))
        elif date and date < DAY:
            waiting.append((cid, date, added))
        elif added:
            series[sid]["contests"][series[sid]["contests"].index(c)] = place(c)
    # a contest that is one region's view of a larger one (subset_of) ran when the larger one did
    for cid, date, added in list(waiting):
        sid, c = where[cid]
        sup = where.get(c.get("subset_of") or "", (None, {}))[1]
        if sup and sup.get("status") != "upcoming" and sup.get("date"):
            del c["status"]
            if not c.get("date"):
                c["date"] = date
            c.setdefault("provenance", []).append(
                f"ran {date}: it is the {sup['id']} contest seen for one region (subset_of), and that contest ran; date from the "
                f"CMS record (ruling {DAY})")
            series[sid]["contests"][series[sid]["contests"].index(c)] = place(c)
            touched.add(sid)
            waiting.remove((cid, date, added))
            flipped.append((cid, date, [f"{sup['id']} ran"], added))
    print(f"{len(flipped)} contests no longer upcoming; {len(waiting)} with a past date and nothing that shows they ran; "
          f"{len(touched)} series files")
    if a.dry_run or not touched:
        for cid, date, ev, added in flipped:
            print(f"  {cid} {date} {'/'.join(ev)} +{len(added)}")
        print("  waiting:", ", ".join(f"{c} ({d})" for c, d, _a in waiting))
        return 0
    for sid in sorted(touched):
        dump_series(sid, series[sid], TOOL)
    rep = [f"# Autumn 2026: which contests ran — {DAY}", "",
           f"`tools/{TOOL}`, from `data/import/autumn-2026-probe-{DAY}.json`. Rule: a contest stops being upcoming when its date "
           "has passed and a result source or judge page shows it ran.", "",
           "Searched: the ICPC CMS (ranked standings and the contest record, for every upcoming contest), and last year's "
           "addresses of each past-dated contest with the year moved on (Kattis, DOMjudge archives, scorelatam, contest sites, "
           "Kattis problem-source pages). QOJ was read earlier today. Codeforces refused both the script and the fetch tool, "
           "so its gym list was not read.", "",
           f"## No longer upcoming ({len(flipped)})", "", "| contest | date | shown by | sources added |", "| --- | --- | --- | --- |"]
    rep += [f"| {cid} | {date} | {', '.join(e.replace('_', ' ') for e in ev)} | {', '.join(added) or '—'} |" for cid, date, ev, added in flipped]
    rep += ["", f"## Date passed, nothing found that shows it ran ({len(waiting)})", "",
            *[f"- {cid} ({date})" + (f" — added: {', '.join(added)}" if added else "") for cid, date, added in waiting], "",
            "## Results links in the CMS record that were not added", "",
            "A home page or a qualifier's leaderboard rather than this contest's results:", "",
            *[f"- {cid}: {url}" for cid, url in leads], ""]
    (ROOT / "reports" / f"autumn-2026-{DAY}.md").write_text("\n".join(rep))
    print(f"wrote reports/autumn-2026-{DAY}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
