#!/usr/bin/env python3
"""One-off data cleanup of 2026-11-12 (site review). Deterministic; a second run changes nothing.

  A. World Finals dates 1979-1998: the 16 editions without a date get one, with the source on
     `provenance`. Fifteen come from this project's own captures of the ICPC headquarters
     pages (icpc.baylor.edu/past/EarlyYears.html and the 1998 standings); 1985 is the one year
     that page leaves undated and rests on a secondary listing.
  B. World Finals 1977-1998 are placed in the location tree (`sites: [{location: <city>}]`
     ahead of the CMS's administrative placeholder); two typos in the free-text location
     are fixed (Detroid, Cincinatti).
  C. locations.yaml: the five host cities the tree lacked (Detroit, Indianapolis, New Orleans,
     Phoenix, Nashville; GeoNames ids from the geonamescache gazetteer).
  D. locations.yaml: six "institutions" that are CMS staff/guest groups, not places (NAC Guests,
     NAPC Guests, NAC Technology, NAC Media, NAC Operations, RCD) are removed; their sites move
     to the city, keeping the group's name as the site label.
  E. `season` for the 70 contests that had none (alberta, lethbridge, naq, nzpc, caribbean-2009):
     it was only filled where a parent chain existed; the series' `naming` rule gives it
     (season-start: id year + 1).
  F. Notes about the *contest* that the problem-archive sheet import left on the problem *set*
     (no date / no teams in the CMS, 2 divisions, strange date?, also CMS id N, online & offline)
     move to the contest's `notes`; notes about the set (missing problems, shared, packaging)
     stay. A "no date" remark is dropped when the catalogue has a date by now.
  G. `cms_status: pre-cms` is dropped (133 contests): the CMS is being backfilled, so "pre-CMS"
     is no longer a category; `cms_ids: []` already says "no CMS entry".
  H. The World Finals series gets `region: International`.
  I. World Finals 1999-2026: the host city becomes the first site. The CMS clones each finals
     from the previous one, so its staff/guest/sponsor groups kept pointing at earlier hosts
     (every finals since 2019 said Beijing; 2004 said Dumai). The host comes from the reviewed
     free-text location; a group pointing outside the host city loses its stale location and is
     marked administrative. Adds the United Arab Emirates and Dubai to the tree (2026).

  python3 tools/cleanup_2026_11_12.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import Dumper, dump_series, load_series, load_sets  # noqa: E402

TOOL = "cleanup_2026_11_12.py"
EARLY = ("icpc.baylor.edu/past/EarlyYears.html (Wayback 2011-01-02; archive wf-1979/rankings/20110102-wayback-ada91083)")
WF_DATES = {  # year: (date, the page's own line)
    1979: ("1979-02-21", "1979 ACM Contest Finals, February 21, 1979, Dayton, Ohio"),
    1980: ("1980-02-13", "1980 ACM Contest Finals, February 13, 1980, Kansas City, Missouri"),
    1981: ("1981-02-25", "1981 ACM Contest Finals, February 25, 1981, St. Louis, Missouri"),
    1982: ("1982-02-10", "1982 ACM Contest Finals, February 10, 1982, Indianapolis, Indiana"),
    1983: ("1983-02-16", "1983 ACM Contest Finals, February 16, 1983, Melbourne, Florida"),
    1984: ("1984-02-15", "1984 ACM Contest Finals, February 15, 1984, Philadelphia, Pennsylvania"),
    1986: ("1986-02-05", "1986 ACM Contest Finals, February 5, 1986, Cinncinnati, Ohio"),
    1987: ("1987-02-18", "1987 ACM Contest Finals, February 18, 1987, St. Louis, Missouri"),
    1989: ("1989-02-22", "1989 ACM Contest Finals, February 22, 1989, Louisville, Kentucky"),
    1990: ("1990-02-21", "1990 ACM Contest Finals, February 21, 1990, Washington, D.C."),
    1992: ("1992-03-04", "1992 ACM Contest Finals, March 4, 1992, Kansas City, Missouri"),
    1995: ("1995-03-01", "1995 ACM Contest Finals, March 1, 1995, Nashville, Tennessee"),
    1996: ("1996-02-17", "1996 ACM Contest Finals, February 17, 1996, Philadelphia, Pennsylvania"),
    1997: ("1997-03-02", "1997 ACM Contest Finals, March 2, 1997, San Jose, California"),
}
WF_OTHER = {
    1998: ("1998-02-28", "date: icpc.baylor.edu/past/icpc98/Finals/Report/Standings.htm (archive wf-1998/standings): "
                         "'1998 World Finals February 28, 1998 Atlanta, Georgia, USA'"),
    1985: ("1985-03-13", "date: NOT from a primary source — EarlyYears.html gives no day for 1985 ('1985 ACM Contest Finals, New Orleans, "
                         "Louisiana'). CLIST's listing of icpc.global results gives March 13, 1985; that is the Wednesday of the ACM Computer "
                         "Science Conference week in New Orleans (SIGCSE symposium March 14-15, 1985), and every finals 1977-1995 with a known "
                         "date fell on a Wednesday. Replace when a primary source turns up."),
}
WF_CITY = {1977: "us-atlanta", 1978: "us-detroit", 1979: "us-dayton", 1980: "us-kansas-city", 1981: "us-st-louis",
           1982: "us-indianapolis", 1983: "us-melbourne", 1984: "us-philadelphia", 1985: "us-new-orleans",
           1986: "us-cincinnati", 1987: "us-st-louis", 1988: "us-atlanta", 1989: "us-louisville", 1990: "us-washington",
           1991: "us-san-antonio", 1992: "us-kansas-city", 1993: "us-indianapolis", 1994: "us-phoenix",
           1995: "us-nashville", 1996: "us-philadelphia", 1997: "us-san-jose", 1998: "us-atlanta"}
TYPOS = {"Detroid, MI, USA": "Detroit, MI, USA", "Cincinatti, OH, USA": "Cincinnati, OH, USA"}
NEW_CITIES = [("us-detroit", "Detroit", "us-mi", 4990729), ("us-indianapolis", "Indianapolis", "us-in", 4259418),
              ("us-new-orleans", "New Orleans", "us-la", 4335045), ("us-phoenix", "Phoenix", "us-az", 5308655),
              ("us-nashville", "Nashville", "us-tn", 4644585)]
WF_HOST = {1999: "nl-eindhoven", 2000: "us-orlando", 2001: "ca-vancouver", 2002: "us-honolulu", 2003: "us-beverly-hills",
           2004: "cz-prague", 2005: "cn-shanghai", 2006: "us-san-antonio", 2007: "jp-tokyo", 2008: "ca-banff",
           2009: "se-stockholm", 2010: "cn-harbin", 2011: "us-orlando", 2012: "pl-warsaw", 2013: "ru-saint-petersburg",
           2014: "ru-yekaterinburg", 2015: "ma-marrakesh", 2016: "th-phuket", 2017: "us-rapid-city", 2018: "cn-beijing",
           2019: "pt-porto", 2020: "ru-moscow", 2021: "bd-dhaka", 2022: "eg-luxor", 2023: "eg-luxor", 2024: "kz-astana",
           2025: "az-baku", 2026: "ae-dubai",
           2027: None}  # host not on record yet: its cloned groups still said Beijing
JUNK_NODES = ("us-orlando-nac-guests", "us-orlando-napc-guests", "us-atlanta-nac", "us-atlanta-nac-media",
              "us-atlanta-nac-operations", "us-atlanta-rcd")
SHEET = "problem archive sheet"

# F. exact set note -> (what stays on the set | None, contest fragments). A fragment starting
# with "date:" is only written when the catalogue still has no date for the contest.
NOTE_MAP = {
    "No date, no teams": (None, ["date:the CMS has no date", "the CMS lists no teams"]),
    "No date, no teams in CMS": (None, ["date:the CMS has no date", "the CMS lists no teams"]),
    "No date, no teams. Did this run?": (None, ["date:the CMS has no date", "the CMS lists no teams — did this run?"]),
    "No date": (None, ["date:the CMS has no date"]),
    "No date.": (None, ["date:the CMS has no date"]),
    "No date in CMS": (None, ["date:the CMS has no date"]),
    "2 divisions": (None, ["2 divisions"]),
    "No date in CMS. 2 divisions": (None, ["date:the CMS has no date", "2 divisions"]),
    "Strange date?": (None, ["strange date?"]),
    "No date in CMS. Shared?": ("Shared?", ["date:the CMS has no date"]),
    "Online & offline. No date": (None, ["online & offline", "date:the CMS has no date"]),
    "Missing some, strange date?": ("Missing some", ["strange date?"]),
    "No date. 2 days, 12+13 problems. Are both the actual contest?":
        ("2 days, 12+13 problems. Are both the actual contest?", ["date:the CMS has no date"]),
}
ALSO_CMS = re.compile(r"^Also CMS:(\d+)( \?)?$")


def insert_after(d: dict, after: tuple[str, ...], key: str, value) -> dict:
    """A copy of mapping `d` with `key` placed right after the last present key of `after`."""
    anchor = next((k for k in reversed(after) if k in d), None)
    out, done = {}, False
    if anchor is None:
        out[key] = value
        done = True
    for k, v in d.items():
        if k == key:
            continue
        out[k] = v
        if k == anchor and not done:
            out[key] = value
            done = True
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    stats: Counter = Counter()
    series = load_series()
    touched: set[str] = set()
    where = {c["id"]: sid for sid, doc in series.items() for c in doc["contests"]}

    def replace(sid: str, cid: str, new: dict) -> None:
        lst = series[sid]["contests"]
        lst[next(i for i, c in enumerate(lst) if c["id"] == cid)] = new
        touched.add(sid)

    def contest(cid: str) -> dict:
        return next(c for c in series[where[cid]]["contests"] if c["id"] == cid)

    # ---- C + D. locations.yaml ----
    loc_path = ROOT / "locations.yaml"
    loc_text = loc_path.read_text()
    loc_doc = yaml.safe_load(loc_text)
    nodes = loc_doc["locations"]
    ids = {n["id"] for n in nodes}
    for nid, name, parent, gid in NEW_CITIES:
        if nid in ids:
            continue
        start = next(i for i, n in enumerate(nodes) if n["id"] == parent) + 1
        end = next((i for i in range(start, len(nodes)) if nodes[i]["type"] in ("country", "region")), len(nodes))
        at = next((i for i in range(start, end) if nodes[i]["type"] == "city" and nodes[i]["name"].lower() > name.lower()), end)
        nodes.insert(at, {"id": nid, "name": name, "type": "city", "parent": parent, "geonameid": gid})
        ids.add(nid)
        stats["C. city nodes added"] += 1
    if "ae" not in ids:  # a country node goes in id order among the countries; its city right after it
        at = next((i for i, n in enumerate(nodes) if n["type"] == "country" and n["id"] > "ae"), len(nodes))
        nodes[at:at] = [{"id": "ae", "name": "United Arab Emirates", "type": "country", "iso": "AE"},
                        {"id": "ae-dubai", "name": "Dubai", "type": "city", "parent": "ae", "geonameid": 292223}]
        ids.update(("ae", "ae-dubai"))
        stats["C. city nodes added"] += 1
        stats["I. country nodes added"] += 1
    junk = {n["id"]: n for n in nodes if n["id"] in JUNK_NODES}
    if junk:
        assert not any(n.get("parent") in junk for n in nodes), "a junk node has children"
        for sid, doc in series.items():
            for c in doc["contests"]:
                for s in c.get("sites") or []:
                    if s.get("location") in junk:
                        j = junk[s["location"]]
                        s["location"] = j["parent"]
                        s.setdefault("name", j["name"])
                        # keep the canonical key order location, name, date, type
                        order = {k: s[k] for k in ("location", "name", "date", "type") if k in s}
                        s.clear()
                        s.update(order)
                        touched.add(sid)
                        stats["D. sites moved from a staff/guest pseudo-institution to its city"] += 1
        loc_doc["locations"] = nodes = [n for n in nodes if n["id"] not in junk]
        stats["D. pseudo-institution nodes removed"] += len(junk)

    # ---- A + B. World Finals ----
    for c in list(series["wf"]["contests"]):
        y = int(c["id"][-4:])
        new = c
        if y in WF_DATES or y in WF_OTHER:
            if not c.get("date"):
                if y in WF_DATES:
                    date, line = WF_DATES[y]
                    prov = f"date: {EARLY}: '{line}'"
                else:
                    date, prov = WF_OTHER[y]
                new = insert_after(new, ("id", "status", "season", "name"), "date", date)
                new["provenance"] = list(new.get("provenance") or []) + [prov]
                stats["A. World Finals dates set"] += 1
        if new.get("location") in TYPOS:
            new["location"] = TYPOS[new["location"]]
            stats["B. location typos fixed"] += 1
        city = WF_CITY.get(y)
        if city and not any(s.get("location") == city for s in new.get("sites") or []):
            assert city in ids, city
            sites = [{"location": city}] + list(new.get("sites") or [])
            new = insert_after(new, ("id", "status", "season", "name", "date", "location", "venue", "cms_ids", "cms_status"), "sites", sites) \
                if "sites" not in new else {**new, "sites": sites}
            stats["B. World Finals placed in the location tree"] += 1
        if new is not c:
            replace("wf", c["id"], new)

    # ---- I. World Finals 1999-2026: the host city first, stale cloned locations dropped ----
    by_id = {n["id"]: n for n in nodes}

    def inside(nid: str, host: str) -> bool:
        seen = set()
        while nid and nid in by_id and nid not in seen:
            if nid == host:
                return True
            seen.add(nid)
            nid = by_id[nid].get("parent")
        return False
    for c in list(series["wf"]["contests"]):
        y = int(c["id"][-4:])
        if y not in WF_HOST:
            continue
        host = WF_HOST[y]
        assert host is None or host in by_id, host
        new_sites, seen_keys = ([{"location": host}], {(None, host, None)}) if host else ([], set())
        for s in c.get("sites") or []:
            s = dict(s)
            loc = s.get("location")
            if loc and (host is None or not inside(loc, host)):
                del s["location"]
                s["type"] = "administrative"
                stats["I. stale cloned site locations dropped"] += 1
            s = {k: s[k] for k in ("location", "name", "date", "type") if k in s}
            key = (s.get("type"), s.get("location"), s.get("name"))  # validate.py's notion of one site
            if key in seen_keys:
                continue
            seen_keys.add(key)
            new_sites.append(s)
        if new_sites != c.get("sites"):
            new = insert_after(c, ("id", "status", "season", "name", "date", "location", "venue", "cms_ids"), "sites", new_sites) \
                if "sites" not in c else {**c, "sites": new_sites}
            replace("wf", c["id"], new)
            stats["I. World Finals with the host city set as first site"] += 1

    # ---- H. WF region ----
    if series["wf"]["series"].get("region") != "International":
        series["wf"]["series"] = insert_after(series["wf"]["series"], ("id", "name", "tier"), "region", "International")
        touched.add("wf")
        stats["H. wf region set"] += 1

    # ---- E. seasons from the naming rule ----
    for sid, doc in series.items():
        naming = doc["series"].get("naming")
        for c in list(doc["contests"]):
            if c.get("season") or not naming:
                continue
            y = int(c["id"].rsplit("-", 1)[1])
            replace(sid, c["id"], insert_after(c, ("id", "status"), "season", y + 1 if naming == "season-start" else y))
            stats["E. seasons filled from the naming rule"] += 1

    # ---- G. cms_status ----
    for sid, doc in series.items():
        for c in doc["contests"]:
            if "cms_status" in c:
                del c["cms_status"]
                touched.add(sid)
                stats["G. cms_status dropped"] += 1

    # ---- F. set notes -> contest notes ----
    sets = load_sets()
    set_changes: dict[str, dict] = {}
    log = []
    for set_id, doc in sets.items():
        note = doc.get("notes")
        if not note:
            continue
        m = ALSO_CMS.match(note)
        if m:
            keep, frags = None, [f"also CMS id {m.group(1)}{'?' if m.group(2) else ''}"]
        elif note in NOTE_MAP:
            keep, frags = NOTE_MAP[note]
        else:
            continue
        members = [x["contest"] for x in doc.get("contests") or [] if x["contest"] in where]
        if not members:
            continue
        for cid in members:
            c = contest(cid)
            parts = []
            for f in frags:
                if f.startswith("date:"):
                    if c.get("date"):
                        stats["F. 'no date' remarks dropped (the catalogue has a date now)"] += 1
                        continue
                    f = f[5:]
                parts.append(f)
            if parts:
                text = (parts[0][0].upper() + parts[0][1:] + ("; " + "; ".join(parts[1:]) if parts[1:] else "") + f" ({SHEET})")
                old = c.get("notes")
                if not old or text not in old:
                    c["notes"] = f"{old}; {text}" if old else text
                    touched.add(where[cid])
                    stats["F. contest notes written"] += 1
            log.append(f"{set_id}: {note!r} -> contest {cid}: {parts or 'dropped'}; set keeps {keep!r}")
        new_doc = dict(doc)
        if keep:
            new_doc["notes"] = keep
        else:
            del new_doc["notes"]
        set_changes[set_id] = new_doc
        stats["F. set notes moved off the set"] += 1

    for k in sorted(stats):
        print(f"  {k}: {stats[k]}")
    if a.dry_run:
        loc = "would change" if stats["C. city nodes added"] or stats["D. pseudo-institution nodes removed"] else "unchanged"
        print(f"dry run: {len(touched)} series files, {len(set_changes)} set files; locations.yaml {loc}")
        return 0
    for sid in sorted(touched):
        dump_series(sid, series[sid], TOOL)
    for set_id, doc in set_changes.items():
        p = ROOT / "problemsets" / f"{set_id}.yaml"
        first = p.read_text().split("\n", 1)[0] + "\n"
        p.write_text(first + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
    if stats["C. city nodes added"] or stats["D. pseudo-institution nodes removed"]:
        hdr = "".join(ln + "\n" for ln in loc_text.split("\n")[:2])
        loc_path.write_text(hdr + yaml.dump(loc_doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
    if log:
        (ROOT / "reports" / "set-notes-moved-2026-11-12.md").write_text(
            "# Problem-set notes moved to their contests (2026-11-12)\n\nBy `tools/cleanup_2026_11_12.py`, step F.\n\n"
            + "\n".join(f"- {x}" for x in log) + "\n")
    print(f"wrote {len(touched)} series files, {len(set_changes)} set files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
