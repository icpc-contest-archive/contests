#!/usr/bin/env python3
"""By-catch of the no-sources hunt of 2026-11-16: sources the search agents came across for
contests other than the one they were searching for. Every address below was opened and read
again on 2026-11-16 before it was listed (the Pakistan files by the agent that found them).
Deterministic; a second run changes nothing.

  python3 tools/apply_no_sources_bycatch.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from add_contests_2026_11_12 import place  # noqa: E402
from catalogue import add_source, dump_series, load_series  # noqa: E402

TOOL = "apply_no_sources_bycatch.py"
NOTE = "by-catch of the no-sources hunt 2026-11-16"
GIKI = "https://giki.edu.pk/wp-content/uploads/"
GG = "https://groups.google.com/g/comp.org.acm/c/"
CURSOR = "https://www.cursor.tue.nl/fileadmin/user_upload/magazine/jaargangen/31/nl/"
# contest: [(url, roles, extra fields, what the document is)]
FOUND = {
    "pakistan-2025": [
        (GIKI + "2026/02/Scoreboard-ICPC-Onsite-2025-DOMjudge.pdf", ["scoreboard"], {},
         "DOMjudge final scoreboard, 12 problems; about 29 ranked rows where the event report counts 87 teams"),
        (GIKI + "2026/07/Event-Report_Regionals-2025.pdf", ["rankings", "report"], {},
         "the organisers' event report: 1 Feb 2026 at three sites, 87 teams, medal winners"),
        (GIKI + "2026/02/1-ICPC_Feb12026_Compiled_Final.pdf", ["problemset"], {"contains": ["statement"]},
         "the 12 problems of the onsite contest of 1 Feb 2026"),
    ],
    "pakistan-2024": [
        (GIKI + "2025/02/ICPC-2024-Final-OnSite.pdf", ["problemset"], {"contains": ["statement"]},
         "the 9 problems of the onsite contest"),
        (GIKI + "2025/02/ICPC-2024-Onsite-Event-Report.pdf", ["rankings", "report"], {},
         "the organisers' event report: 1-2 Feb 2025 at three sites"),
        (GIKI + "2024/11/Invitation-to-The-2024-ICPC-Asia-Topi-Regional-Onsite-Contest.pdf", ["web"], {},
         "the organisers' invitation letter to the onsite contest"),
    ],
    "erc-1988": [
        (CURSOR + "13.pdf", ["rankings"], {},
         "TU/e weekly Cursor: Ecole des Mines (Paris) first, Leiden second, the TUE teams' places"),
        (CURSOR + "12.pdf", ["report"], {},
         "TU/e weekly Cursor: the final held at the TUE, 25 teams, organised under the ACM"),
    ],
    "erc-1989": [
        ("http://resolver.kb.nl/resolve?urn=ddd:010559226:mpeg21:a0076:ocr", ["rankings", "report"], {},
         "ANP newspaper item: TU Eindhoven first, Leiden second, Utrecht third; 25 teams from nine countries"),
        ("http://resolver.kb.nl/resolve?urn=ABCDDD:010827203:mpeg21:a0058:ocr", ["rankings", "report"], {},
         "newspaper item: TU Eindhoven first, Leiden second; nine problems in six hours"),
    ],
    "rmc-1991": [
        (GG + "Fxpay4MAoak", ["report"], {},
         "the head judge's report of 11 Nov 1991: sites, the eight problems, how many of 34 teams solved how many"),
    ],
    "rmc-1993": [
        ("https://archive.org/details/dailyuniverse4768prov", ["rankings", "report"], {"scope": "one team's place"},
         "BYU Daily Universe, 3 Dec 1993: a BYU team second; 29 teams at three locations, early November"),
    ],
    "kuwait-2025": [
        ("https://www.aljarida.com/article/113099", ["rankings", "report"], {"scope": "top 3"},
         "Al-Jarida, 27 Oct 2025: 16 and 18 Oct at AUK, 44 teams, the first three teams"),
    ],
    "scusa-1991": [
        (GG + "WqBIPKSnTUE", ["standings"], {},
         "the 16th South Central regional's results posted 19 Nov 1991: 71 teams with problems solved and time"),
    ],
    "wf-1992": [
        (GG + "Crbpn3ZgPyw", ["scoreboard"], {},
         "the finals scoreboard posted by the ACM on 19 Mar 1992: 30 teams, times for problems A-G"),
    ],
    "ecna-1992": [
        (GG + "P3ys4igw6Mk", ["rankings"], {"scope": "top 10"},
         "the top ten as posted by a participant on 25 Nov 1992, before the official results"),
    ],
    "tajikistan-2025": [
        ("https://nerc.itmo.ru/archive/2025/tajikistan/standings.xml", ["scoreboard", "problemset"],
         {"contains": ["names"]}, "the NERC archive's standings data, with the problems' names"),
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    series = load_series()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    touched: set[str] = set()
    n = 0
    for cid, items in FOUND.items():
        sid, c = where[cid]
        hit = False
        for url, roles, extra, what in items:
            for role in roles:
                if add_source(c, url, role, note=f"{NOTE}: {what}", **extra)[1]:
                    print(f"{cid}: {role} {url}")
                    hit = True
                    n += 1
        if hit:
            doc = series[sid]
            doc["contests"][[x["id"] for x in doc["contests"]].index(cid)] = place(c)
            touched.add(sid)
    print(f"{n} additions, {len(touched)} series files{' (dry run)' if a.dry_run else ''}")
    if not a.dry_run:
        for sid in sorted(touched):
            dump_series(sid, series[sid], TOOL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
