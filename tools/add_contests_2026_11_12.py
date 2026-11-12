#!/usr/bin/env python3
"""Rulings of 2026-11-12 on the open items of the QOJ import. Deterministic; a second run changes nothing.

  A. Five contests of autumn 2026 were still `upcoming` although QOJ mirrors their problem sets.
     They ran: the status goes, the date is set from the organiser's own pages, and the public
     Kattis scoreboards that exist are recorded as sources.
  B. Four contests the catalogue lacked are added:
       yinchuan-2020       the 2020 Yinchuan regional, held 15-16 May 2021 (delayed season);
       ctuo-1995, -1996    the first two CTU Opens, held in May like the 1997 one;
       tehran-online-2022  the 19th Iran Internet Programming Contest, 16 March 2023, the online
                           round before the delayed 2022 Tehran regional (27-28 April 2023).
                           QOJ files it under 2023, the year it was held; by the naming rule a
                           delayed edition keeps its season's year. New series `tehran-online`.

  Run tools/import_qoj_tree.py afterwards: it adds the QOJ judge pages it had held back. Then run
  this tool once more: it only puts the keys of the entries it touched back in order.

  python3 tools/add_contests_2026_11_12.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import add_source, dump_series, load_series, normalise_contest  # noqa: E402

TOOL = "add_contests_2026_11_12.py"
RULING = "ruling 2026-11-12"

# id: (date, provenance line, [(url, role, note)])
RAN = {
    "chengdu-2026": ("2026-10-25",
                     "ran 2026-10-25: icpc.global finder Chengdu-2027 gives the contest as 24-25 Oct 2026; the Codeforces "
                     "gym replay (106799) started 2026-10-25; QOJ mirrors the set", []),
    "xian-2026": ("2026-10-18",
                  "ran 2026-10-18: CMS site date; icpc.global finder Xian-2027 gives the contest as 16-18 Oct 2026; "
                  "QOJ mirrors the set", []),
    "naq-2026": ("2026-10-03",
                 "ran 2026-10-03: CMS site dates; naq26.kattis.com (start 2026-10-03 20:00 CEST); QOJ mirrors the set",
                 [("https://naq26.kattis.com/contests/naq26/standings", "scoreboard", None)]),
    "rmc-2026": ("2026-10-31",
                 "ran 2026-10-31: rm.na.icpc.global; held as ICPC Grand Central 2026 (Rocky/Mid-Central) on "
                 "nacentral26.kattis.com; QOJ mirrors the set",
                 [("https://nacentral26.kattis.com/contests/nacentral26d1/standings", "scoreboard",
                   "ICPC Grand Central 2026 (Rocky/Mid-Central), Division 1: one contest for the Rocky Mountain and "
                   "Mid-Central regionals")]),
    "ukiepc-2026": ("2026-10-17",
                    "ran 2026-10-17: CMS site dates; ukiepc26.kattis.com (start 2026-10-17 12:00 CEST); QOJ mirrors the set",
                    [("https://ukiepc26.kattis.com/contests/ukiepc26/standings", "scoreboard", None)]),
}

CTU = "https://contest.felk.cvut.cz/"
NEW = {  # series id: [contest, ...]
    "yinchuan": [{
        "id": "yinchuan-2020", "season": 2021, "name": "2020 ICPC Asia Yinchuan Regional Contest", "date": "2021-05-16",
        "sites": [{"location": "cn-yinchuan"}], "parent": "wf-2021",
        "provenance": [
            "added 2026-11-12: QOJ mirrors the set (https://qoj.ac/contest/1322). Held 15-16 May 2021, delayed from the "
            "2020 season: the Asia council's notice on the Yinchuan site (https://icpcasia.wp.txstate.edu/?p=14) gives the "
            "onsite as May 15-16; Codeforces blog 114930 gives the contest day as 16 May 2021",
            "site: the Yinchuan site as in 2019; host Ningxia Institute of Science and Technology; no CMS entry found",
        ]}],
    "ctuo": [{
        "id": "ctuo-1995", "season": 1996, "date": "1995-05-13", "cms_ids": [], "parent": "cerc-1995", "next": "ctuo-1996",
        "sources": [{"url": CTU + "95prg/", "roles": ["web"]},
                    {"url": CTU + "95prg/results.html", "roles": ["standings"]},
                    {"url": CTU + "95prg/problems_1995_converted.pdf", "roles": ["problemset"]}],
        "provenance": [
            "added 2026-11-12: QOJ mirrors the set (https://qoj.ac/contest/3662). The first CTU Open: " + CTU + "95prg/ "
            "says May 12th and 13th, 1995, at CTU Prague FEE; the CTU Open 2014 problem set's introduction gives the "
            "contest day as May 13, 1995",
        ]}, {
        "id": "ctuo-1996", "season": 1997, "date": "1996-05-04", "cms_ids": [], "parent": "cerc-1996", "next": "ctuo-1997",
        "sources": [{"url": CTU + "96prg/", "roles": ["web"]},
                    {"url": CTU + "96prg/praha.html", "roles": ["standings"]},
                    {"url": CTU + "96prg/ulohy2.html", "roles": ["problemset"]}],
        "provenance": [
            "added 2026-11-12: QOJ mirrors the set (https://qoj.ac/contest/3663). " + CTU + "96prg/ lists a faculty "
            "round (26-27 April 1996) and a Prague round (3-4 May 1996); the Prague round is taken as the CTU Open, "
            "and its second day as the contest day, as in 1995 and 1997",
        ]}],
    "tehran-online": [{
        "id": "tehran-online-2022", "season": 2023, "name": "19th Iran Internet Programming Contest", "date": "2023-03-16",
        "sites": [{"type": "online"}], "parent": "tehran-2022",
        "sources": [{"url": "https://icpc.sharif.edu/2022", "roles": ["web"],
                     "note": "the Tehran regional's site; it lists the 19th Iran Internet Programming Contest, 16 March 2023"}],
        "provenance": [
            "added 2026-11-12: QOJ mirrors the set (https://qoj.ac/contest/1166) as the Tehran online contest of 2023. "
            "https://icpc.sharif.edu/2022 lists one online contest that year, the 19th Iran Internet Programming Contest "
            "on 16 March 2023, ahead of the regional of 27-28 April 2023 (tehran-2022); the QOJ page itself needs a "
            "login and was not read",
        ]}],
}
NEW_SERIES = {
    "tehran-online": {"id": "tehran-online", "name": "Iran Internet Programming Contest", "tier": "subregional",
                      "region": "Asia West", "naming": "season-start"},
}
NEXT = {"yinchuan-2019": "yinchuan-2020"}  # predecessors that gain a `next`


def place(c: dict) -> dict:
    """Key order for an entry this tool touched, without disturbing the rest of the file: `date`
    after `name`, and sources / problems / provenance / notes last, in that order."""
    tail = ("sources", "none", "problems", "provenance", "notes")
    keys = [k for k in c if k != "date" and k not in tail]
    at = keys.index("name") + 1 if "name" in keys else len(keys)
    keys[at:at] = ["date"] if "date" in c else []
    return {k: c[k] for k in keys + [k for k in tail if k in c]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    series = load_series()
    touched: set[str] = set()
    log: list[str] = []

    # ---- A. ran
    for sid, doc in series.items():
        for c in doc["contests"]:
            if c["id"] not in RAN:
                continue
            date, why, srcs = RAN[c["id"]]
            changed = False
            if c.get("status") == "upcoming":
                del c["status"]
                changed = True
            if c.get("date") != date:
                c["date"] = date
                changed = True
            line = f"{why} ({RULING})"
            prov = c.setdefault("provenance", [])
            if line not in prov:
                prov.append(line)
                changed = True
            for url, role, note in srcs:
                changed |= add_source(c, url, role, note=note)[1]
            if changed:
                touched.add(sid)
                log.append(f"ran: {c['id']} {date}" + (f" (+{len(srcs)} source)" if srcs else ""))
            if list(place(c)) != list(c):
                doc["contests"][doc["contests"].index(c)] = place(c)
                touched.add(sid)

    # ---- B. new contests
    for sid, new in NEW.items():
        if sid not in series:
            series[sid] = {"series": NEW_SERIES[sid], "contests": []}
            touched.add(sid)
            log.append(f"new series: {sid}")
        doc = series[sid]
        have = {c["id"] for c in doc["contests"]}
        for c in new:
            if c["id"] in have:
                continue
            doc["contests"].append(normalise_contest(c))
            touched.add(sid)
            log.append(f"added: {c['id']} {c['date']}")
        for c in doc["contests"]:
            if NEXT.get(c["id"]) and c.get("next") != NEXT[c["id"]]:
                c["next"] = NEXT[c["id"]]
                touched.add(sid)
        doc["contests"].sort(key=lambda c: c["id"])

    print("\n".join(log) if log else "nothing to do")
    if not a.dry_run:
        for sid in sorted(touched):
            dump_series(sid, series[sid], TOOL)
    print(f"{len(touched)} series file(s) {'would change' if a.dry_run else 'written'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
