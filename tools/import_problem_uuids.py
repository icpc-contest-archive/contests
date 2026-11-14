#!/usr/bin/env python3
"""Attach problem UUIDs from a Kattis problem export to the catalogue's problem lists.

Input (--raw): a JSON list of {title, source, problem_uuid} as exported from Kattis. The
`source` is free text ("Nordic Collegiate Programming Contest (NCPC) 2014"); this tool maps
it to catalogue contest ids by (1) the contest's own Kattis judge page (a `sources:` entry
with role judge_page, judge: kattis, pointing at open.kattis.com/problem-sources/...),
(2) a table of source patterns per series. Only problems whose source maps to a catalogued
contest that has run are kept; the kept rows are frozen in
data/import/problem-uuids-<date>.json (the raw export is not stored — most of it is not
ICPC material) and the tool can be re-run from that file without --raw.

Applying (DEFINITIONS.md, Problems — the contest's set, problemsets/<set-id>.yaml):
  the set lists problems      -> the uuid goes on the problem whose name matches the title
                                 (normalized; else the letter, through the contest's letter
                                 map); the row keeps its permanent id. Titles with no match
                                 are reported, or appended (id from the uuid) when the set
                                 is marked incomplete or its letters unknown
  no set, or holdings only    -> the set is created (named after the contest, linked from it
                                 with `problems: {set: ...}`) or populated from the export:
                                 name + uuid, a letter map only when the titles are
                                 alphabetical A, B, C… (the convention most European contests
                                 follow), else `letters: unknown` is left for the repo sync;
                                 `complete: false` when the set's count says more problems
                                 exist, or no count is known
  a row with a Kattis short name (export field problem_id/short_name) also gets
  `short_name` and a judge link {judge: kattis, url, id}.
A source that names several contests attaches to each; when they share one set, the set
is updated once. Sources naming a shared set whose members are not known (the North
America "Regional Contests" sets 2019–2023) are reported, not guessed.

Usage (repo root):
  python3 tools/import_problem_uuids.py --raw /path/to/problems.json [--date 2026-11-01]
  python3 tools/import_problem_uuids.py            # re-apply the frozen file
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import Dumper, by_role, dump_series, judge_sources, load_series  # noqa: E402

# ---- problem sets (same conventions as tools/migrate_problemsets.py, which created them) ----
SET_DIR = ROOT / "problemsets"
SET_HEADER = "# Problem set (DEFINITIONS.md, Problems): holdings, member contests with letter maps, problems.\n"
HELD_KINDS = ("statement", "data", "solutions", "package")
SET_KEYS = ("id", "name", "repo", "count", "complete", "letters", *HELD_KINDS, "counts",
            "contests", "problems", "provenance", "notes")
PROB_KEYS = ("id", "uuid", "aliases", "name", "short_name", "have", "status", "judges", "notes")
KATTIS_PROBLEM = "https://open.kattis.com/problems/{}"


def pid(uuid: str | None, set_id: str, letter: str | None, name: str) -> str:
    """Permanent internal problem id (verbatim from migrate_problemsets.py)."""
    if uuid:  # hash, not prefix: Kattis-issued uuids share long prefixes (8ee7605a-...)
        return "p-" + hashlib.sha1(uuid.lower().encode()).hexdigest()[:8]
    h = hashlib.sha1(f"{set_id}|{letter or ''}|{name}".encode()).hexdigest()
    return "p-" + h[:8]


def order_problem(p: dict) -> dict:
    out = {k: p[k] for k in PROB_KEYS if k in p}
    out.update({k: v for k, v in p.items() if k not in out})
    return out


def load_set(set_id: str) -> dict | None:
    f = SET_DIR / f"{set_id}.yaml"
    return yaml.safe_load(f.read_text()) if f.exists() else None


def dump_set(s: dict) -> str:
    doc = {k: s[k] for k in SET_KEYS if k in s}
    doc.update({k: v for k, v in s.items() if k not in doc and not k.startswith("_")})
    if "problems" in doc:
        doc["problems"] = [order_problem(p) for p in doc["problems"]]
    return SET_HEADER + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)


def set_entry(s: dict, cid: str) -> dict:
    e = next((e for e in s["contests"] if e["contest"] == cid), None)
    if e is None:
        e = {"contest": cid}
        s["contests"].append(e)
    return e


def attach_kattis(p: dict, row: dict) -> bool:
    """short_name + Kattis judge link from a row that carries the short name."""
    sn = row.get("short_name")
    if not sn:
        return False
    changed = False
    if not p.get("short_name"):
        p["short_name"] = sn
        changed = True
    if not any(j["judge"] == "kattis" for j in p.get("judges") or []):
        p.setdefault("judges", []).append({"judge": "kattis", "url": KATTIS_PROBLEM.format(sn), "id": sn})
        changed = True
    return changed

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
                               and re.search(r"same as|shared with", set_notes(c), re.I)]
        dropped = [c for c in linked if c not in keep]
        return keep, ("kattis link + rule" if not dropped else f"kattis link (rule said {by_rule}; dropped {dropped})")
    if len(by_rule) == 1 and len(linked) == 1 and ALL.get(linked[0], {}).get("subset_of") == by_rule[0]:
        return by_rule, f"kattis link (rule said {by_rule}: the merged contest, used instead of its regional view {linked})"
    return linked, f"kattis link (rule said {by_rule})"


ALL: dict = {}  # contest id -> entry, set by main()
NOT_ICPC = re.compile(r"\bHSC\b|High School|^KTH Challenge$", re.I)  # sheet links that are not the contest


def set_notes(cid: str) -> str:
    """The notes of the contest's problem set ("Same as ncpc-2013"), "" when it has none."""
    sid = ((ALL.get(cid) or {}).get("problems") or {}).get("set")
    s = load_set(sid) if sid else None
    return (s or {}).get("notes") or ""


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
    series_docs, contests, series_of = load_series(), {}, {}
    for sid, doc in series_docs.items():
        for c in doc["contests"]:
            contests[c["id"]] = c
            series_of[c["id"]] = sid
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
        for s in judge_sources(c):
            if s.get("judge") != "kattis":
                continue
            m = re.search(r"open\.kattis\.com/problem-sources/([^/?#]+)", s["url"])
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
                row = {"title": r["title"], "source": src, "uuid": r["problem_uuid"],
                       "contests": live, "letter": (re.match(r"^Problem ([A-Z]) of ", src) or [None, None])[1]}
                sn = r.get("short_name") or r.get("problem_id") or r.get("shortname")
                if sn:
                    row["short_name"] = str(sn).strip()
                kept.append(row)
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
    sets: dict[str, dict] = {}      # set id -> document, loaded once (shared sets are updated once)
    set_text: dict[str, str] = {}   # set id -> text as loaded ("" when new)
    dirty_series, nm_dirty = set(), False
    for cid, rs in sorted(by_contest.items()):
        c = all_known[cid]
        set_id = (c.get("problems") or {}).get("set")
        s = None
        if set_id:
            if set_id not in sets:
                s = load_set(set_id)
                if s is None:
                    report["contest links to a set that has no file (skipped)"].append(f"{cid}: {set_id}")
                    continue
                sets[set_id], set_text[set_id] = s, (SET_DIR / f"{set_id}.yaml").read_text()
            s = sets[set_id]
        if s is not None and s.get("problems"):
            # ---- the set lists problems: attach to the matching rows ----
            probs = s["problems"]
            entry = set_entry(s, cid)
            letters: dict[str, str] = entry.get("letters") or {}
            by_id = {p["id"]: p for p in probs}
            by_name: dict[str, dict] = {}
            for p in probs:
                by_name.setdefault(norm_title(p["name"]), p)
            if len(by_name) != len(probs):
                report["set has duplicate normalized names"].append(set_id)
            for p in probs:  # "essentially same as <name> in <contest>": the judge may use that name
                m = re.search(r"same as (.+?) in [a-z0-9-]+-\d{4}", p.get("notes") or "")
                if m:
                    by_name.setdefault(norm_title(m.group(1)), p)
            by_uuid = {p["uuid"].lower(): p for p in probs if p.get("uuid")}
            for r in rs:
                p = by_uuid.get(r["uuid"].lower())  # already attached (re-run) — nothing to match by name
                if p is None:
                    p = by_name.get(norm_title(r["title"]))
                if p is None and r.get("letter"):
                    p = by_id.get(letters.get(r["letter"]))
                if p is None:
                    if s.get("letters") == "unknown" or s.get("complete") is False:
                        p = {"id": pid(r["uuid"], set_id, None, r["title"]), "uuid": r["uuid"], "name": r["title"]}
                        if p["id"] in by_id:
                            report["uuid already in the set under another name (not added)"].append(
                                f"{set_id}: {r['title']!r} ({r['uuid']}) is {by_id[p['id']]['name']!r}")
                            continue
                        attach_kattis(p, r)
                        probs.append(p)
                        by_id[p["id"]] = by_uuid[r["uuid"].lower()] = p
                        by_name.setdefault(norm_title(p["name"]), p)
                        if r.get("letter") and s.get("letters") != "unknown" and r["letter"] not in letters:
                            letters[r["letter"]] = p["id"]
                            entry["letters"] = letters
                        stats["problem appended to an incomplete set"] += 1
                    else:
                        report["title not found in the contest's problem set (not added)"].append(
                            f"{cid} ({set_id}): {r['title']!r} ({r['uuid']})")
                    continue
                if p.get("uuid") and p["uuid"] != r["uuid"]:
                    letter = next((l for l, i in letters.items() if i == p["id"]), p["id"])
                    report["uuid conflict (existing kept)"].append(f"{cid} {letter}: have {p['uuid']}, export {r['uuid']}")
                elif not p.get("uuid"):
                    p["uuid"] = r["uuid"]  # the id stays: ids are permanent
                    stats["uuid attached"] += 1
                if attach_kattis(p, r):
                    stats["kattis short name / judge link attached"] += 1
        else:
            # ---- no set, or holdings only: build the problem list from the export ----
            if c.get("status") == "upcoming" or not has_run(cid):
                continue
            new_id = set_id or cid
            titles = sorted(rs, key=lambda r: norm_title(r["title"]))
            letters_l = [r.get("letter") or first_letter(r["title"]) for r in titles]
            alphabetical = all(letters_l) and letters_l == [chr(ord("A") + i) for i in range(len(letters_l))]
            probs, lmap = [], {}
            for i, r in enumerate(titles):
                p = {"id": pid(r["uuid"], new_id, None, r["title"]), "uuid": r["uuid"], "name": r["title"]}
                attach_kattis(p, r)
                probs.append(p)
                if r.get("letter"):
                    lmap[r["letter"]] = p["id"]
                elif alphabetical:
                    lmap[letters_l[i]] = p["id"]
            if any(r.get("letter") for r in rs) and not all(r.get("letter") for r in rs):
                report["mixed letter knowledge in one contest"].append(cid)
            count = (s or {}).get("count")
            if count and len(probs) > count:
                report["judge lists MORE problems than the set's count (set not filled — rule on the count)"].append(
                    f"{cid} ({new_id}): {len(probs)} on Kattis, count {count}: " + ", ".join(p["name"] for p in probs))
                continue
            if s is None:
                s = sets[new_id] = {"id": new_id, "contests": []}
                set_text[new_id] = ""
                c["problems"] = {"set": new_id}
                if cid in non_mainline:
                    nm_dirty = True
                else:
                    dirty_series.add(series_of[cid])
                stats["set created"] += 1
            else:
                stats["holdings-only set filled"] += 1
            entry = set_entry(s, cid)
            if len(lmap) == len(probs):
                entry["letters"] = lmap
                s.pop("letters", None)
            else:
                s["letters"] = "unknown"
            if count and count != len(probs):
                s["complete"] = False
                stats["set filled (incomplete: fewer problems than count)"] += 1
            elif not count:
                s["complete"] = False  # nothing says how many problems the set had
                stats["set filled (count unknown)"] += 1
            else:
                s.pop("complete", None)
                stats["set filled (complete)"] += 1
            s["problems"] = probs
            stats["problems with uuid in filled sets"] += len(probs)

    changed_sets = sorted(sid for sid, s in sets.items() if dump_set(s) != set_text[sid])
    for sid in changed_sets:  # provenance: the export, once
        s = sets[sid]
        if source_note not in (s.get("provenance") or []):
            s.setdefault("provenance", []).append(source_note)
    touched_files = len(changed_sets)
    if not args.dry_run:
        SET_DIR.mkdir(exist_ok=True)
        for sid in changed_sets:
            (SET_DIR / f"{sid}.yaml").write_text(dump_set(sets[sid]))
        for sid in sorted(dirty_series):
            dump_series(sid, series_docs[sid], "import_problem_uuids.py")
        if nm_dirty:
            head = "".join(l for l in nm_path.read_text().splitlines(keepends=True) if l.startswith("#"))
            nm_path.write_text(head + yaml.dump(nm_doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
    stats["series files written"] = len(dirty_series) if not args.dry_run else 0
    stats["problemsets files written"] = touched_files if not args.dry_run else 0
    if args.dry_run and (dirty_series or nm_dirty or changed_sets):
        print(f"(dry run) series files that would change: {', '.join(sorted(dirty_series))}; "
              f"non-mainline registry: {nm_dirty}; problemsets files that would change ({len(changed_sets)}): "
              f"{', '.join(changed_sets)}")

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
    print(f"problemsets files {'that would change' if args.dry_run else 'touched'}: {touched_files} of {len(sets)}; "
          f"report sections: {len(report)} -> {rep.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
