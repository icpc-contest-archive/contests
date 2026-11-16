#!/usr/bin/env python3
"""No-sources hunt of 2026-11-16: add the sources the search agents found for contests that had
none, and end `upcoming` for the autumn-2026 contests whose result source shows they ran.
Deterministic; a second run changes nothing.

Input, frozen in data/import/no-sources-hunt-2026-11-16.json: one record per contest with the
addresses an agent opened and read (role, what the page holds, verified, confidence).

What is added: a source that the agent opened (`verified`), rated `high`, with a catalogue role.
What is not: existence records (the agents' role `other`: CMS records, season tables, schedules);
anything rated lower; pages of another event (SKIP_URL: preliminary and qualification rounds, the
India selection pool, hub and series front pages); a whole contest whose match or identity is a
question for a ruling (HOLD); more than MAX_WEB pages of one website per contest.

`upcoming` ends (RAN) by the rule of 2026-11-12: the date has passed and a result source or the
organisers' published problem set shows the contest ran. `date` is set only where RAN gives one.

  python3 tools/apply_no_sources_hunt.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from add_contests_2026_11_12 import place  # noqa: E402
from catalogue import ROLES, add_source, dump_series, load_series  # noqa: E402

TOOL = "apply_no_sources_hunt.py"
DAY = "2026-11-16"
DATA = ROOT / "data" / "import" / "no-sources-hunt-2026-11-16.json"
NOTE = f"added by the no-sources hunt {DAY}"
MAX_WEB = 2

# matched by series continuity only, filed under the wrong series, or possibly another year's set
HOLD = {"turkey-2021", "turkey-2023", "rmc-1989", "taiwan-1994"}
SKIP_URL = (
    "indiaicpc.in/selection_pool_2026",      # the common India preliminary, not a regional
    "://indiaicpc.in/",                      # season hub
    "iubat.ac.bd/icpc/registration/preliminary-teams",
    "icpc.jp/2026/domestic/results",         # the domestic qualifier
    "icpcapac.solved.ac",                    # unofficial tracker
    "giki.edu.pk/wp-content/uploads/2026/10",  # the online preliminary's files
    "icpc.global/regionals/finder/",         # CMS pages are added by slug below, never as `web`
    "apac.icpc.global/championship/latest",
    "icpc.global/api/",                      # the API behind a CMS page: the page is the source (CMS)
    "im.cycu.edu.tw/",                       # rules of the other contest merged into taiwan-ncpc-2016 (CMS 3076)
)
SKIP_EXACT = {"https://nerc.itmo.ru/", "https://nerc.icpc.global/", "https://cpfed.kz/",
              "https://icpc.jp/2026/", "https://acmicpcph.blogspot.com/", "https://olymp.nstu.ru/"}
# CMS standings the agents read through the public API: contest -> slug
CMS = {
    "malaysia-national-2014": "al-Khawarizmi-2015",
    "vietnam-national-2013": "Vietnam-National-First-Round-2014",
    "vietnam-national-2015": "Vietnam-National-2016",
    "vietnam-national-2026": "Vietnam-National-2027",
    "tap-2020": "TAP-2021",
}
# contest -> (date or None, how the date was read)
RAN = {
    "armenia-2026": ("2026-11-14", "the NERC archive scoreboard"),
    "georgia-2026": ("2026-11-14", "the NERC archive scoreboard and subregion page"),
    "kazakhstan-2026": ("2026-11-14", "the NERC archive scoreboard and subregion page"),
    "north-russia-2026": ("2026-11-14", "the statements' title page"),
    "tajikistan-2026": ("2026-11-14", "the NERC archive scoreboard"),
    "turkmenistan-2026": ("2026-11-14", "the NERC archive scoreboard"),
    "urals-2026": ("2026-11-14", "the NERC archive scoreboard and the host's timetable"),
    "taurida-2026": ("2026-11-14", "the NERC archive scoreboard"),
    "west-neerc-2026": ("2026-11-15", "the host's standings page"),
    "nanjing-2026": ("2026-11-08", "the board's config and the host's news report"),
    "shenyang-2026": ("2026-11-15", "the board's config"),
    "korea-2026": ("2026-11-14", "the organisers' rules notice and results post"),
    "qatar-2026": ("2026-10-10", "CMS site date; press reports of 14-16 Oct 2026"),
    "turkey-2026": ("2026-10-11", "the organisers' report (final round)"),
    "romania-2026": (None, "held 7-8 Nov 2026 per the organisers' site; contest day not stated"),
    "kuwait-2026": (None, "held 22 and 24 Oct 2026 per the host's press release; contest day not stated"),
}
# a date for a contest that had none, where the source states the contest day
DATE = {
    "vietnam-national-2026": "2026-11-08",
    "gny-1994": "1994-11-12",
    "erc-1985": "1985-11-02",
    "nena-north-2016": "2016-10-22",
}
EVIDENCE = {"scoreboard", "standings", "rankings", "problemset"}


def wanted(cid: str, s: dict) -> list[str]:
    url = s.get("url") or ""
    if s.get("verified") is not True or s.get("confidence") != "high":
        return []
    if url in SKIP_EXACT or any(x in url for x in SKIP_URL):
        return []
    return [r for r in s.get("roles") or [] if r in ROLES]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    data = json.loads(DATA.read_text())
    series = load_series()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    touched: set[str] = set()
    log: list[str] = []
    for cid in sorted(data):
        rec = data[cid]
        if cid not in where:
            log.append(f"?? {cid}: not in the catalogue")
            continue
        sid, c = where[cid]
        added: list[str] = []
        if cid not in HOLD:
            web_per_host: dict[str, int] = {}
            for s in rec.get("sources") or []:
                roles = wanted(cid, s)
                if not roles:
                    continue
                url = s["url"]
                if roles == ["web"]:
                    host = urlsplit(url).netloc
                    web_per_host[host] = web_per_host.get(host, 0) + 1
                    if web_per_host[host] > MAX_WEB:
                        continue
                for role in roles:
                    names = ["names"] if role == "problemset" and url.endswith("standings.xml") else None
                    if add_source(c, url, role, note=NOTE, contains=names)[1]:
                        added.append(f"{role} {url}")
            if cid in CMS:
                url = f"https://icpc.global/regionals/finder/{CMS[cid]}/standings"
                if add_source(c, url, "standings", note=NOTE)[1]:
                    added.append(f"standings {url}")
        if cid in DATE and not c.get("date") and added:
            c["date"] = DATE[cid]
            c.setdefault("provenance", []).append(f"date {DATE[cid]} as stated by its sources (no-sources hunt {DAY})")
            added.append(f"-- date {DATE[cid]}")
        if cid in RAN and c.get("status") == "upcoming":
            date, how = RAN[cid]
            roles = sorted({r for s in c.get("sources") or [] for r in s["roles"] if r in EVIDENCE})
            if roles:
                del c["status"]
                if date and not c.get("date"):
                    c["date"] = date
                when = f"ran {date}" if date else "ran"
                c.setdefault("provenance", []).append(
                    f"{when}: shown by its {', '.join(roles)} source(s); {how} (no-sources hunt {DAY})")
                added.append(f"-- no longer upcoming{' ' + date if date else ''}")
        if added:
            doc = series[sid]
            i = [x["id"] for x in doc["contests"]].index(cid)
            doc["contests"][i] = place(c)
            touched.add(sid)
            log.append(f"{cid}:")
            log += [f"    {x}" for x in added]
    print("\n".join(log))
    print(f"{sum(1 for x in log if x.endswith(':'))} contests, {len(touched)} series files"
          f"{' (dry run)' if a.dry_run else ''}")
    if not a.dry_run:
        for sid in sorted(touched):
            dump_series(sid, series[sid], TOOL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
