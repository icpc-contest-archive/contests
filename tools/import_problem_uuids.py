#!/usr/bin/env python3
"""Attach problem UUIDs from a Kattis problem export to the catalogue's problem lists.

Input (--raw): a JSON list of {title, source, problem_uuid} as exported from Kattis. The
`source` is free text ("Nordic Collegiate Programming Contest (NCPC) 2014"); this tool maps
it to catalogue contest ids by (1) the contest's own `judges.kattis` problem-sources link,
(2) a table of source patterns per series. Only problems whose source maps to a catalogued
contest that has run are kept; the kept rows are frozen in
data/import/problem-uuids-<date>.json (the raw export is not stored — most of it is not
ICPC material) and the tool can be re-run from that file without --raw.

Applying:
  problems/<contest>.yaml exists  -> the uuid goes on the problem whose name matches the
                                    title (normalized); titles with no match are reported,
                                    or appended when the list is marked incomplete
  no per-problem file             -> one is created from the export: name + uuid, letters
                                    only when the titles are alphabetical A, B, C… (the
                                    convention most European contests follow), else no
                                    letter — `letters: unknown` is left for the repo sync
A source that names several contests (a shared problem set) attaches to each of them.
Sources naming a shared set whose members are not known (the North America "Regional
Contests" sets 2019–2023) are reported, not guessed.

Usage (repo root):
  python3 tools/import_problem_uuids.py --raw /path/to/problems.json [--date 2026-11-01]
  python3 tools/import_problem_uuids.py            # re-apply the frozen file
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parent.parent


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null"))

# ---- source -> contest id(s). Patterns are tried in order; {y} = the 4-digit year ----
Y = r"(?P<y>(?:19|20)\d{2})"
RULES: list[tuple[str, str | list[str] | None]] = [
    # skipped kinds first (practice, dress rehearsal, challenges, adaptations)
    (r"practice|dress rehearsal|challenge|adapted from|and KTH training|puzzle", None),
    (r"(?:ICPC|ACM-ICPC|ACM/ICPC|International Collegiate Programming Contest \(ACM-ICPC\)) World Finals " + Y, "wf"),
    (r"^" + Y + r" ACM Scholastic Programming Contest Finals", "wf"),
    (r"ACM National Scholastic Programming Contest " + Y, "wf"),
    (r"ICPC World Finals " + Y + r" and (?P<y2>20\d{2})", ["wf", "wf:y2"]),
    (r"NWERC|Northwestern? Europe|North Western Europe", "nwerc"),
    (r"NCPC|Nordic Collegiate", "nordic"),
    (r"Swedish Championships " + Y, "sweden"),
    (r"BAPC\) preliminaries|Benelux.*(?:preliminar|Qualifier)", "bapc-prelims"),
    (r"BAPC|Benelux Algorithm", "bapc"),
    (r"GCPC|German Collegiate", "germany"),
    (r"UKIEPC|United Kingdom and Ireland", "ukiepc"),
    (r"SWERC|Southwestern? Europe", "swerc"),
    (r"Mid-Central European", "mcerc"),
    (r"CERC|Central Europe(?:an)? Regional", "cerc"),
    (r"South Central, South East and Mid Atlantic", "south-na"),
    (r"North Central North America and Southern California", ["ncna", "socal"]),
    (r"Mid-Central and Rocky Mountain", ["mcpc", "rmc"]),
    (r"Mid[- ]Central", "mcpc"),
    (r"Mid[- ]Atlantic", "mausa"),
    (r"East[- ]Central", "ecna"),
    (r"Greater New York", "gny"),
    (r"South ?East(?:ern)? USA|South East Regionals|Southeast USA", "seusa"),
    (r"South Central(?:,| USA| Regional)", "scusa"),
    (r"North Central|NCNA", "ncna"),
    (r"Rocky Mountain", "rmc"),
    (r"Pacific Northwest", "pacnw"),
    (r"Southern California", "socal"),
    (r"North Americ(?:a|an) Qualifier", "naq"),
    (r"North America Division Championships", "nadc"),
    (r"North America East Division", "east-na"),
    (r"North America Championship", "nac"),
    (r"Northeast North America", "nena"),
    (r"Atlantic Canadian", "nena-atlantic"),
    (r"Alberta Collegiate", "alberta"),
    (r"Hong Kong Regional Contest", "hong-kong"),
    (r"Singapore Regional", "singapore"),
    (r"Vietnam National", "vietnam-national"),
    (r"Asia (?:Nha Trang|Ho Chi Minh City|Hanoi|Danang|Can Tho) Regional", "vietnam"),
    (r"Asia Nanjing Regional", "nanjing"),
    (r"Asia Qingdao Regional", "qingdao"),
    (r"South American Regional", "south-america"),
    (r"South Pacific Regionals", "south-pacific"),
    (r"Southeastern European Regionals", "seerc"),
    (r"North Eastern European Regionals", "neerc"),
    (r"NAIPC", "naipc"),
]
# the shared North-America regional sets: members not recorded anywhere we trust
UNRESOLVED_SHARED = re.compile(r"ICPC North America Regional (?:Programming )?Contests|North America Regionals \(|"
                               r"ICPC North America Regional Contests 20")


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", t.lower())


def first_letter(t: str) -> str | None:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    m = re.search(r"[A-Za-z0-9]", t)
    return m.group(0).upper() if m else None


def year_of(source: str) -> str | None:
    ys = re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", source)
    if not ys:
        return None
    # "2020-2021 …", "2021/2022 …", "ICPC NCNA Regionals 2025 2026": the season's first year
    return ys[0]


def map_source(source: str, kattis_sources: dict[str, str], known: set[str]) -> tuple[list[str], str]:
    """-> (contest ids, how)"""
    s = source.strip()
    if NOT_ICPC.search(s):
        return [], "skipped kind"
    if UNRESOLVED_SHARED.search(s):
        return [], "shared NA regional set — members unknown"
    linked = kattis_sources.get(s) or []
    by_rule, how = _map_by_rule(s, known)
    if not linked:
        return by_rule, how
    if not by_rule or set(by_rule) == set(linked):
        return linked, "kattis link"
    if len(by_rule) > 1 and set(linked) <= set(by_rule):
        return by_rule, "kattis link + shared-set rule"
    if len(by_rule) == 1 and by_rule[0] in linked:
        # the sheet links this source from other contests too: deliberate when that
        # contest's notes say it shares the set ("Same as ncpc-2013"), a slip otherwise
        keep = [by_rule[0]] + [c for c in linked if c != by_rule[0]
                               and re.search(r"same as|shared with", (ALL.get(c, {}).get("problems") or {}).get("notes") or "", re.I)]
        dropped = [c for c in linked if c not in keep]
        return keep, ("kattis link + rule" if not dropped else f"kattis link (rule said {by_rule}; dropped {dropped})")
    if len(by_rule) == 1 and len(linked) == 1 and ALL.get(linked[0], {}).get("subset_of") == by_rule[0]:
        return by_rule, f"kattis link (rule said {by_rule}: the merged contest, used instead of its regional view {linked})"
    return linked, f"kattis link (rule said {by_rule})"


ALL: dict = {}  # contest id -> entry, set by main()
NOT_ICPC = re.compile(r"\bHSC\b|High School|^KTH Challenge$", re.I)  # sheet links that are not the contest


def _map_by_rule(s: str, known: set[str]) -> tuple[list[str], str]:
    m = re.search(r"^Problem ([A-Z]) of ", s)
    if m:
        s2 = s[m.end():]
    else:
        s2 = s
    for pat, series in RULES:
        mm = re.search(pat, s2, re.I)
        if not mm:
            continue
        if series is None:
            return [], "skipped kind"
        y = year_of(s2)
        if not y:
            return [], "no year"
        out = []
        for ser in (series if isinstance(series, list) else [series]):
            yy = y
            if ser.endswith(":y2"):
                ser, yy = ser[:-3], mm.group("y2")
            cid = f"{ser}-{yy}"
            if cid in known:
                out.append(cid)
            else:
                return [], f"{cid} not in the catalogue"
        return out, "pattern"
    return [], "no rule"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", help="Kattis export (JSON list of title/source/problem_uuid)")
    ap.add_argument("--date", default="2026-11-01")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    frozen = ROOT / "data" / "import" / f"problem-uuids-{args.date}.json"
    today = datetime.date.today()

    # ---- catalogue ----
    series_docs, contests, series_of = {}, {}, {}
    for f in sorted((ROOT / "series").glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        series_docs[f.stem] = doc
        for c in doc["contests"]:
            contests[c["id"]] = c
            series_of[c["id"]] = f.stem
    nm_path = ROOT / "registry" / "non-mainline.yaml"
    nm_doc = yaml.safe_load(nm_path.read_text())
    non_mainline = {c["id"]: c for c in nm_doc["non_mainline_contests"]}
    all_known = {**non_mainline, **contests}
    ALL.update(all_known)

    def has_run(cid):
        c = all_known[cid]
        if c.get("status") == "upcoming":
            return False
        try:
            return datetime.date.fromisoformat(c.get("date", "")) <= today
        except ValueError:
            return True

    kattis_sources: dict[str, list[str]] = defaultdict(list)  # a shared set is linked from several contests
    for cid, c in all_known.items():
        j = ((c.get("problems") or {}).get("judges") or {}).get("kattis")
        for loc in (j if isinstance(j, list) else [j]) if j else []:
            u = loc["url"] if isinstance(loc, dict) else loc
            m = re.search(r"open\.kattis\.com/problem-sources/([^/?#]+)", u)
            if m:
                kattis_sources[unquote(m.group(1)).replace("+", " ")].append(cid)

    report: dict[str, list[str]] = defaultdict(list)
    stats = Counter()

    # ---- map ----
    if args.raw:
        raw = json.loads(Path(args.raw).read_text())
        by_source = defaultdict(list)
        for r in raw:
            by_source[(r.get("source") or "").strip()].append(r)
        kept = []
        how_count = Counter()
        for src, rows in sorted(by_source.items()):
            cids, how = map_source(src, kattis_sources, set(all_known))
            how_count[how.split(" (")[0] if cids else how] += len(rows)
            if cids and how.startswith("kattis link (rule said"):
                report["sheet's Kattis link and the source pattern disagree (link used)"].append(f"{src} -> {cids}; {how}")
            if not cids:
                if how not in ("skipped kind", "no rule", "no year"):
                    report[f"source not applied: {how}"].append(f"{src} ({len(rows)} problems)")
                elif re.search(r"ICPC|ACM|Regional|Collegiate|NWERC|NCPC|BAPC|SWERC|CERC|GCPC|UKIEPC|World Finals", src, re.I) and how != "skipped kind":
                    report["ICPC-looking source with no rule (not applied)"].append(f"{src} ({len(rows)} problems)")
                continue
            live = [c for c in cids if has_run(c)]
            for c in cids:
                if c not in live:
                    report["contest has not run — problem data not publishable (held back)"].append(f"{c} <- {src} ({len(rows)} problems)")
            if not live:
                continue
            for r in rows:
                if not r.get("title"):
                    report["row without a title (skipped)"].append(f"{src}: {r['problem_uuid']}")
                    continue
                kept.append({"title": r["title"], "source": src, "uuid": r["problem_uuid"],
                             "contests": live, "letter": (re.match(r"^Problem ([A-Z]) of ", src) or [None, None])[1]})
        kept.sort(key=lambda r: (r["contests"][0], r["title"]))
        frozen.write_text(json.dumps({"exported": args.date, "from": "Kattis problem export (title, source, uuid)",
                                      "rows": kept}, indent=1, ensure_ascii=False) + "\n")
        print(f"raw rows {len(raw)}: kept {len(kept)} -> {frozen.relative_to(ROOT)}")
        print("  by outcome:", dict(how_count))
    rows = json.loads(frozen.read_text())["rows"]
    source_note = f"Kattis problem export ({args.date})"

    # ---- apply ----
    by_contest = defaultdict(list)
    for r in rows:
        for cid in r["contests"]:
            by_contest[cid].append(r)
    pdir = ROOT / "problems"
    pdir.mkdir(exist_ok=True)
    dirty_series, touched_files = set(), 0
    for cid, rs in sorted(by_contest.items()):
        c = all_known[cid]
        pfile = pdir / f"{cid}.yaml"
        if pfile.exists():
            doc = yaml.safe_load(pfile.read_text())
            by_name = {norm_title(p["name"]): p for p in doc["problems"]}
            if len(by_name) != len(doc["problems"]):
                report["per-problem file has duplicate normalized names"].append(cid)
            for p in doc["problems"]:  # "essentially same as <name> in <contest>": the judge may use that name
                m = re.search(r"same as (.+?) in [a-z0-9-]+-\d{4}", p.get("notes") or "")
                if m:
                    by_name.setdefault(norm_title(m.group(1)), p)
            changed = False
            for r in rs:
                p = by_name.get(norm_title(r["title"]))
                if p is None and r.get("letter"):
                    p = next((x for x in doc["problems"] if x.get("letter") == r["letter"]), None)
                if p is None:
                    if doc.get("letters") == "unknown" or doc.get("complete") is False:
                        doc["problems"].append({"name": r["title"], "uuid": r["uuid"]})
                        stats["problem appended to an incomplete list"] += 1
                        changed = True
                    else:
                        report["title not found in the contest's problem list (not added)"].append(
                            f"{cid}: {r['title']!r} ({r['uuid']})")
                    continue
                if p.get("uuid") and p["uuid"] != r["uuid"]:
                    report["uuid conflict (existing kept)"].append(f"{cid} {p.get('letter')}: have {p['uuid']}, export {r['uuid']}")
                elif not p.get("uuid"):
                    # keep key order: letter, name, short_name, uuid, …
                    items = list(p.items())
                    pos = next((i + 1 for i, (k, _v) in enumerate(items) if k in ("short_name", "name")), len(items))
                    pos = max(pos, next((i + 1 for i, (k, _v) in enumerate(items) if k == "short_name"), 0))
                    items.insert(pos, ("uuid", r["uuid"]))
                    p.clear()
                    p.update(items)
                    stats["uuid attached"] += 1
                    changed = True
            if changed:
                doc["sources"] = sorted(set((doc.get("sources") or []) + [source_note]))
                if not args.dry_run:
                    pfile.write_text(dump(doc, cid))
                touched_files += 1
        else:
            if c.get("status") == "upcoming" or not has_run(cid):
                continue
            titles = sorted(rs, key=lambda r: norm_title(r["title"]))
            letters = [r.get("letter") or first_letter(r["title"]) for r in titles]
            alphabetical = all(letters) and letters == [chr(ord("A") + i) for i in range(len(letters))]
            probs = []
            for i, r in enumerate(titles):
                p = {}
                if r.get("letter"):
                    p["letter"] = r["letter"]
                elif alphabetical:
                    p["letter"] = letters[i]
                p["name"] = r["title"]
                p["uuid"] = r["uuid"]
                probs.append(p)
            if any(r.get("letter") for r in rs) and not all(r.get("letter") for r in rs):
                report["mixed letter knowledge in one contest"].append(cid)
            doc = {"contest": cid, "sources": [source_note]}
            pb = c.get("problems") or {}
            if pb.get("count") and len(probs) > pb["count"]:
                report["judge lists MORE problems than the contest's count (file not created — rule on the count)"].append(
                    f"{cid}: {len(probs)} on Kattis, count {pb['count']}: " + ", ".join(p["name"] for p in probs))
                continue
            if not alphabetical and not all(p.get("letter") for p in probs):
                doc["letters"] = "unknown"
            if pb.get("count") and pb["count"] != len(probs):
                doc["complete"] = False
                stats["file created (incomplete: fewer problems than count)"] += 1
            elif not pb.get("count"):
                doc["complete"] = False  # nothing says how many problems the contest had
                stats["file created (count unknown)"] += 1
            else:
                stats["file created (complete)"] += 1
            doc["problems"] = probs
            if not args.dry_run:
                pfile.write_text(dump(doc, cid))
            touched_files += 1
            if not c.get("problems"):
                c["problems"] = {"source": source_note}
                if cid in non_mainline:
                    pass
                else:
                    dirty_series.add(series_of[cid])
            stats["problems with uuid in new files"] += len(probs)

    for sid in dirty_series:
        if not args.dry_run:
            (ROOT / "series" / f"{sid}.yaml").write_text(
                "# Maintained in-repo; problem-archive data imported by tools/import_problem_archive.py.\n"
                + yaml.dump(series_docs[sid], Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))

    # ---- report ----
    rep = ROOT / "reports" / f"problem-uuids-import-{args.date}.md"
    lines = [f"# Problem UUID import — {args.date}", "",
             f"Generated by `tools/import_problem_uuids.py` from `data/import/problem-uuids-{args.date}.json` "
             f"({len(rows)} rows for {len(by_contest)} contests).", "",
             "## Summary", ""] + [f"- {k}: {v}" for k, v in sorted(stats.items())] + [""]
    for k in sorted(report):
        lines += [f"## {k} ({len(report[k])})", ""] + [f"- {x}" for x in report[k]] + [""]
    if not args.dry_run:
        rep.write_text("\n".join(lines))
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print(f"files touched: {touched_files}; report sections: {len(report)} -> {rep.relative_to(ROOT)}")
    return 0


def dump(doc: dict, cid: str) -> str:
    return ("# Per-problem data; letter/name/have from the progress sheet, uuid and judge links maintained here.\n"
            + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))


if __name__ == "__main__":
    sys.exit(main())
