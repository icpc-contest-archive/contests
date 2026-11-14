#!/usr/bin/env python3
"""Import the "ICPC Problem Archive progress" sheet into the catalogue.

One-shot import (re-runnable): reads the frozen CSV exports in data/import/
  icpc-problem-archive-progress-<date>-contests.csv   (one row per contest)
  icpc-problem-archive-progress-<date>-problems.csv   (one row per problem, 30 contests)
and writes

  problemsets/<set-id>.yaml   the contest's problem set (DEFINITIONS.md, Problems): the
                              holdings (repo, count, what is held, counts, notes) and the
                              per-problem rows (name, what is held, judge links) with the
                              contest's letter map; the sheet is recorded under the set's
                              `provenance:`. A contest with no set yet gets one named after
                              it (`problems: {set: <contest-id>}` on the contest); a contest
                              that already links to a shared set updates that set. Keys this
                              tool does not know about are kept (uuid, short_name, judge
                              links other tools added, `complete`, `letters: unknown`);
                              problem ids are permanent — an existing row (matched by letter
                              via the letter map, else by name) keeps its id, and rows the
                              sheet does not list are kept and reported.
  series/<series>.yaml        `problems: {set: ...}` where the contest had no set; the
                              sheet's judge links become `sources:` entries with role
                              judge_page and `judge: <id>` (catalogue.add_source: an address
                              already catalogued only gains the role, its as_of/note are kept)
  registry/non-mainline.yaml  the same for non-mainline contests the sheet tracks
  series/*.yaml sources:      role problemset from the sheet's "Web" column where the
                              contest has none and the URL is not just the contest website
                              (a bare site root becomes a web source instead); the sheet
                              is recorded under `provenance:`
  reports/problem-archive-import-<date>.md   everything the sheet disagrees with

What is deliberately NOT imported: "#P est." (a guess), "Contact email" and
"Assigned to" (personal data / internal workflow — also stripped from the CSV), and the
"Contest names" existence grid (superseded by the catalogue itself).

Model (DEFINITIONS.md, "Problems"): the sheet's yes/partial/no flags become
full/partial/none; exact per-kind counts are kept only where the flag is partial
(`counts:`), since full and none are implied by `count`. Judge links are sources
(wrapper URLs unwrapped into url + as_of, as everywhere else); a problem's judge link is
`{judge, url, id}` with `id` the judge's own problem id (the Kattis short name).

Re-runnable: a second run on the same data changes nothing.

Usage (from the repo root):
  python3 tools/import_problem_archive.py [--date 2026-11-01] [--dry-run]
  python3 tools/validate.py
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import Dumper, add_source, by_role, dump_series, has_role, load_series  # noqa: E402
from resources import norm_key, unwrap  # noqa: E402

# ---- problem sets (same conventions as tools/migrate_problemsets.py, which created them) ----
SET_DIR = ROOT / "problemsets"
SET_HEADER = "# Problem set (DEFINITIONS.md, Problems): holdings, member contests with letter maps, problems.\n"
HELD_KINDS = ("statement", "data", "solutions", "package")
SET_KEYS = ("id", "name", "repo", "count", "complete", "letters", *HELD_KINDS, "counts",
            "contests", "problems", "provenance", "notes")
PROB_KEYS = ("id", "uuid", "aliases", "name", "short_name", "have", "status", "judges", "notes")
JUDGE_ID = {
    "kattis": re.compile(r"open\.kattis\.com/problems/([^/?#]+)"),
    "livearchive": re.compile(r"problem=(\d+)"),
    "baekjoon": re.compile(r"acmicpc\.net/problem/(\d+)"),
    "codeforces": re.compile(r"codeforces\.com/gym/(\d+(?:/problem/[A-Z0-9]+)?)"),
}


def pid(uuid: str | None, set_id: str, letter: str | None, name: str) -> str:
    """Permanent internal problem id (verbatim from migrate_problemsets.py)."""
    if uuid:  # hash, not prefix: Kattis-issued uuids share long prefixes (8ee7605a-...)
        return "p-" + hashlib.sha1(uuid.lower().encode()).hexdigest()[:8]
    h = hashlib.sha1(f"{set_id}|{letter or ''}|{name}".encode()).hexdigest()
    return "p-" + h[:8]


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", t.lower())


def judge_link(judge: str, u: str) -> dict:
    """A sheet URL as a problem judge link {judge, url, id?, as_of?}."""
    url, ts, _via = unwrap(u)
    link = {"judge": judge, "url": url}
    m = JUDGE_ID.get(judge)
    if m and (mm := m.search(url)):
        link["id"] = mm.group(1)
    if ts:
        link["as_of"] = ts
    return link


def add_judge_link(p: dict, link: dict) -> bool:
    """Add a judge link to a problem unless the same address (or the same judge id) is there."""
    for j in p.get("judges") or []:
        if j["judge"] == link["judge"] and (norm_key(j["url"]) == norm_key(link["url"])
                                            or (link.get("id") and j.get("id") == link["id"])):
            return False
    p.setdefault("judges", []).append(link)
    return True


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
    """The set's `contests` entry for a member, created when missing."""
    e = next((e for e in s["contests"] if e["contest"] == cid), None)
    if e is None:
        e = {"contest": cid}
        s["contests"].append(e)
    return e


ORG = "icpc-problem-archive"
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]*-\d{4}")
KINDS = (("has state.", "count state.", "statement"), ("has data", "count data", "data"),
         ("has sol.", "count sol.", "solutions"), ("has package", "count package", "package"))
JUDGE_COLS = (("Kattis", "kattis"), ("OJ", "livearchive"), ("BJ", "baekjoon"), ("CF", "codeforces"))
# the problems sheet names a few contests by their repo rather than their contest id
PROBLEM_SHEET_RENAMES = {"benelux-": "bapc-", "german-": "germany-"}
# sheet rows ruled to be errors (2026-11-01): wf-1974 — there was no 1974 finals
IGNORE_ROWS = {"wf-1974": "sheet error — no such contest"}
# sheet-only dates verified 2026-11-01. Held back: syria-2017 "2017-17-23" is not a date;
# nwerc-2005 "2006-11-17" and neerc-2001 "2002-11-27" fall AFTER the World Finals they feed
# (wf-2006 2006-04-13, wf-2002 2002-03-24), so they cannot be right as given.
APPLY_DATES = {"erc-1988", "nena-north-2008", "alberta-2023"}
# Ruling 2026-11-01: where the Problems sheet's rows contradict the Contests sheet, the
# Contests sheet is right — the rows are rewritten to match. For the partial cases the
# sheet does not say WHICH problems; the letters below are inferred (noted on the problem).
CONTEST_SHEET_WINS = {"nwerc-2010", "nwerc-2002", "nwerc-2001", "nwerc-2000", "bapc-2020", "germany-2020", "ukiepc-2020"}
# Holdings checked against the repo itself: these win over the sheet's flags.
# nzpc-2019 (2026-11-13): the statement-only PDF holds problems A-H only.
CHECKED_HOLDINGS = {
    "nzpc-2019": {"statement": "partial", "counts": {"statement": 8}},
}
PARTIAL_LETTERS = {  # (contest, kind) -> letters that HAVE it
    ("nwerc-2010", "data"): set("ABCDFGH"),       # the seven with packages
    ("nwerc-2010", "solutions"): set("ABCDFGH"),
    ("bapc-2020", "package"): set("ABCEFGHIJK"),  # all but D, the one problem not shared with ukiepc-2020
}


def org_repos() -> set[str]:
    """Repo names in the org, from the newest frozen `gh repo list` export
    (data/import/problem-archive-repos-<date>.json); empty when there is none:
      gh repo list icpc-problem-archive --limit 1000 --json name,isPrivate,isEmpty,isArchived,pushedAt
    """
    files = sorted((ROOT / "data" / "import").glob("problem-archive-repos-*.json"))
    return {r["name"] for r in json.loads(files[-1].read_text())} if files else set()


def dump(doc, header: str) -> str:
    return header + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def split_urls(v: str) -> list[str]:
    return [u.strip().rstrip(",") for u in re.split(r"[;\s]+", v or "") if u.strip().rstrip(",")]


def parts(u: str) -> tuple[str, str | None]:
    """A sheet URL as (url, as_of) for a `sources:` entry."""
    url, ts, _via = unwrap(u)
    return url, ts


def site_keys(c: dict) -> set[str]:
    """Addresses that ARE the contest website: its web sources."""
    return {norm_key(w["url"]) for w in by_role(c, "web")}


def add_provenance(c: dict, line: str) -> bool:
    if line in (c.get("provenance") or []):
        return False
    c.setdefault("provenance", []).append(line)
    return True


def merge_problem_rows(s: dict, cid: str, rows: list[dict], report: dict, stats: Counter) -> None:
    """The sheet's rows for `cid` (letter, name, short_name?, have, judges?, notes?) become
    problem rows of the set `s` plus the contest's letter map. An existing row — found by
    letter through the letter map, else by name — keeps its id and everything the sheet
    does not produce (uuid, other judge links, …); the sheet's name/have/notes win, judge
    links are added. Rows of the set the sheet does not list are kept (ids are permanent)."""
    probs = s.setdefault("problems", [])
    entry = set_entry(s, cid)
    letters: dict[str, str] = dict(entry.get("letters") or {})
    by_id = {p["id"]: p for p in probs}
    by_name: dict[str, dict] = {}
    for p in probs:
        by_name.setdefault(norm_title(p["name"]), p)
    seen = set()
    for r in rows:
        letter = r.pop("letter")
        p = by_id.get(letters.get(letter)) if letter else None
        if p is None:
            p = by_name.get(norm_title(r["name"]))
        if p is None:
            p = {"id": pid(None, s["id"], letter, r["name"])}
            if p["id"] in by_id:
                report["problem id collision inside a set (row skipped)"].append(f"{s['id']}: {letter} {r['name']!r} -> {p['id']}")
                continue
            probs.append(p)
            by_id[p["id"]] = p
            stats["problem rows added to sets"] += 1
        seen.add(p["id"])
        for k in ("name", "short_name", "have", "notes"):
            if k in r:
                p[k] = r[k]
        for link in r.get("judges") or []:
            if add_judge_link(p, link):
                stats["judge links added to problems"] += 1
        if letter:
            if letters.get(letter) not in (None, p["id"]):
                report["letter map: letter re-pointed by the sheet"].append(f"{s['id']} {cid}: {letter} {letters[letter]} -> {p['id']}")
            letters[letter] = p["id"]
    if letters:
        entry["letters"] = letters
        if s.get("letters") == "unknown":  # a letter map is known now
            del s["letters"]
    extra = [p for p in probs if p["id"] not in seen]
    if extra:
        report["problems in the set the sheet does not list (kept)"].append(
            f"{s['id']} ({cid}): " + ", ".join(f"{p['id']} {p['name']!r}" for p in extra))
    if s.get("complete") is False and s.get("count") == len(probs):
        del s["complete"]  # the sheet lists every problem now


JUDGE_HOSTS = (("kattis.com", "kattis"), ("acmicpc.net", "baekjoon"), ("codeforces.com", "codeforces"),
               ("onlinejudge.org", "livearchive"), ("icpcarchive.ecs.baylor.edu", "livearchive"))


def judge_of(u: str) -> str | None:
    host = urlparse(u).netloc.lower()
    return next((k for h, k in JUDGE_HOSTS if host == h or host.endswith("." + h)), None)


def is_site_root(u: str) -> bool:
    p = urlparse(u)
    return bool(re.fullmatch(r"/?(index\.(php|html?))?", p.path)) and not p.query and not p.fragment


def read_contests(path: Path) -> dict[str, dict]:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    out, section = {}, None
    for r in rows:
        short = (r["Short name"] or "").strip()
        if not short and (r["Full name"] or "").strip():
            section = r["Full name"].strip()  # a heading row of the sheet
        if ID_RE.fullmatch(short):
            r["_section"] = section
            out[short] = r
    return out


def read_problems(path: Path) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for r in csv.DictReader(path.open(newline="", encoding="utf-8")):
        cid = (r["Contest"] or "").strip()
        if not cid:
            continue
        for old, new in PROBLEM_SHEET_RENAMES.items():
            if cid.startswith(old):
                cid = new + cid[len(old):]
        out[cid].append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-11-01", help="date suffix of the CSV exports")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    stem = ROOT / "data" / "import" / f"icpc-problem-archive-progress-{args.date}"
    sheet = read_contests(Path(f"{stem}-contests.csv"))
    psheet = read_problems(Path(f"{stem}-problems.csv"))
    source = f"ICPC Problem Archive progress sheet ({args.date})"

    # ---- catalogue ----
    series_docs: dict[str, dict] = load_series()
    contests: dict[str, dict] = {c["id"]: c for doc in series_docs.values() for c in doc["contests"]}
    nm_path = ROOT / "registry" / "non-mainline.yaml"
    nm_doc = yaml.safe_load(nm_path.read_text())
    non_mainline = {c["id"]: c for c in nm_doc["non_mainline_contests"]}
    triage = {e["cms_id"]: e for e in yaml.safe_load((ROOT / "registry" / "cms-triage.yaml").read_text())["excluded"]}
    cms_owner = {}
    for cid, c in contests.items():
        for i in c.get("cms_ids") or []:
            cms_owner[i] = cid
    series_of_id = {c["id"]: sid for sid, doc in series_docs.items() for c in doc["contests"]}

    def mark_dirty(cid):
        if cid in series_of_id:
            series_docs[series_of_id[cid]]["_dirty"] = True

    alias_series = {}
    for sid, doc in series_docs.items():
        for a in doc["series"].get("aliases") or []:
            alias_series[a] = sid

    # ---- sheet id -> catalogue id (direct, CMS id, series rename learnt from CMS matches, aliases) ----
    mapping: dict[str, str] = {}
    rename: dict[str, str] = dict(alias_series)
    for sid, r in sheet.items():
        if sid in contests or sid in non_mainline:
            mapping[sid] = sid
        elif (cms := num(r["CMS"])) in cms_owner:
            mapping[sid] = cms_owner[cms]
            a, b = sid.rsplit("-", 1)[0], cms_owner[cms].rsplit("-", 1)[0]
            if a != b:
                rename[a] = b
    unmapped = []
    for sid, r in sheet.items():
        if sid in mapping:
            continue
        ser, yr = sid.rsplit("-", 1)
        cand = f"{rename.get(ser, ser)}-{yr}"
        if cand in contests:
            mapping[sid] = cand
        else:
            unmapped.append(sid)
    rev = defaultdict(list)
    for a, b in mapping.items():
        rev[b].append(a)
    collisions = {b: a for b, a in rev.items() if len(a) > 1}

    report: dict[str, list[str]] = defaultdict(list)
    stats: Counter = Counter()
    repos = org_repos()
    today = datetime.date.today()

    # ---- build the problems block per mapped contest ----
    blocks: dict[str, dict] = {}
    judge_pages: dict[str, list[tuple[str, str]]] = defaultdict(list)  # cid -> [(judge, sheet url)]
    for sid, r in sheet.items():
        cid = mapping.get(sid)
        if not cid:
            continue
        c = contests.get(cid) or non_mainline[cid]
        blk: dict = {}
        repo = (r["Repo"] or "").strip()
        if repo:
            repo = re.sub(r"^https?://github\.com/", "", repo).strip("/")
            repo = repo if "/" in repo else f"{ORG}/{repo}"
            name = repo.split("/", 1)[1]
            if repos and repo.startswith(f"{ORG}/") and name not in repos:
                if cid in repos:  # renamed to the contest id since the sheet was written
                    report["repo renamed since the sheet (org name used)"].append(f"{cid}: sheet `{name}`")
                    repo, name = f"{ORG}/{cid}", cid
                else:
                    report["sheet names a repo the org does not have (kept)"].append(f"{cid}: `{repo}`")
            blk["repo"] = repo
            if name not in ("statement-only", cid):
                report["repo named differently from the contest id"].append(
                    f"{cid}: repo `{repo}`" + (f" (sheet row `{sid}`)" if sid != cid else ""))
        elif cid in repos:
            blk["repo"] = f"{ORG}/{cid}"
            report["repo exists in the org, sheet has none (repo recorded)"].append(cid)
        count = num(r["#P"])
        if count is not None:
            blk["count"] = count
        counts = {}
        for flag_col, cnt_col, kind in KINDS:
            flag = (r[flag_col] or "").strip().lower()
            if not flag:
                continue
            blk[kind] = {"yes": "full", "no": "none", "partial": "partial"}[flag]
            n = num(r[cnt_col])
            if n is not None and count is not None:
                implied = "full" if n == count else ("none" if n == 0 else "partial")
                if implied != blk[kind]:
                    report["sheet flag disagrees with its own count"].append(
                        f"{sid}: {kind} flagged {flag} but {n} of {count}")
                if blk[kind] == "partial":
                    counts[kind] = n
        if counts:
            blk["counts"] = counts
        if cid in CHECKED_HOLDINGS:
            blk.update(CHECKED_HOLDINGS[cid])
            report["holdings checked against the repo (sheet overridden)"].append(f"{cid}: {CHECKED_HOLDINGS[cid]}")
        judges = [(key, u) for col, key in JUDGE_COLS for u in split_urls(r[col])]
        if judges:
            judge_pages[cid].extend(judges)
            blk["_judges"] = True  # the row carries data even when nothing else is set
        if (r["Comment"] or "").strip():
            blk["notes"] = r["Comment"].strip()
        if blk:
            blk.pop("_judges", None)
            blk["source"] = source
            blocks[cid] = blk
            if c.get("status") == "upcoming":
                report["problem data on an upcoming contest (not imported)"].append(
                    f"{cid}: {blk}" + (f" judges {judge_pages[cid]}" if judge_pages.get(cid) else ""))
                del blocks[cid]
                judge_pages.pop(cid, None)

        # ---- disagreements with the catalogue (report only, nothing changed) ----
        if cid in non_mainline:
            continue
        sd, cd = (r["Date"] or "").strip(), c.get("date")
        if sd and cd and sd != cd and not cd.startswith(sd[:len(cd)]):
            report["dates differ (catalogue kept)"].append(f"{cid}: sheet {sd}, catalogue {cd}")
        elif sd and not cd:
            if cid in APPLY_DATES:
                c["date"] = sd
                add_provenance(c, source)
                mark_dirty(cid)
                report["sheet dates applied by ruling"].append(f"{cid}: {sd}")
            else:
                report["sheet has a date the catalogue lacks (not applied — verify first)"].append(f"{cid}: {sd}")
        scms, ccms = num(r["CMS"]), c.get("cms_ids")
        if scms is not None and ccms and scms not in ccms:
            report["CMS ids differ (catalogue kept)"].append(f"{cid}: sheet {scms}, catalogue {ccms}")
        sn, cn = (r["Full name"] or "").strip(), (c.get("name") or "").strip()
        if sn and cn and sn != cn:
            report["names differ (catalogue kept)"].append(f"{cid}: sheet {sn!r}, catalogue {cn!r}")

        # ---- problemset from the sheet's "Web" column ----
        webs = split_urls(r["Web"])
        # judge pages filed under Web belong with the judge links
        for u in list(webs):
            key = judge_of(unwrap(u)[0])
            if key:
                webs.remove(u)
                if cid in blocks:
                    judge_pages[cid].append((key, u))
                    stats["Web column judge link moved to judges"] += 1
        if len(webs) > 1:
            report["Web column has several URLs (first used as problemset)"].append(f"{cid}: {webs}")
            webs = webs[:1]
        if webs:
            cand = [parts(u) for u in webs if norm_key(unwrap(u)[0]) not in site_keys(c)]
            roots = [p for p in cand if is_site_root(p[0])]
            for url, ts in roots:  # a bare site root is a website, not a problem set: an extra web source (ruling 2026-11-01)
                _s, ch = add_source(c, url, "web", as_of=ts)
                if ch:
                    add_provenance(c, source)
                    stats["extra web source added from the Web column"] += 1
                    mark_dirty(cid)
            cand = [p for p in cand if p not in roots]
            if not cand:
                stats["Web column = contest website, nothing to add"] += 1
            else:
                had = has_role(c, "problemset")
                added = 0
                for url, ts in cand:
                    _s, ch = add_source(c, url, "problemset", as_of=ts)
                    if ch:
                        added += 1
                        add_provenance(c, source)
                        mark_dirty(cid)
                if not added:
                    stats["problemset already present"] += 1
                elif had:  # several places publish the set: keep both (ruling 2026-11-01)
                    stats["problemset: second URL added"] += added
                else:
                    stats["problemset filled from sheet"] += 1

    # ---- per-problem rows ----
    problem_rows: dict[str, list[dict]] = {}
    for pcid, rows in psheet.items():
        cid = mapping.get(pcid, pcid)
        if cid not in contests and cid not in non_mainline:
            report["problems sheet: contest not in the catalogue (skipped)"].append(f"{pcid} ({len(rows)} problems)")
            continue
        probs = []
        for r in rows:
            p = {"letter": r["Lbl"].strip(), "name": r["Name"].strip()}
            if (r["Short name"] or "").strip():
                p["short_name"] = r["Short name"].strip()
            have = [k for col, k in (("Stm.", "statement"), ("Data", "data"), ("IV", "input_validator"),
                                     ("OV", "output_validator"), ("Sol.", "solutions"), ("Packaged", "package"))
                    if (r[col] or "").strip().lower() == "yes"]
            p["have"] = have
            if (r["Kattis"] or "").strip():
                p["judges"] = [judge_link("kattis", r["Kattis"].strip())]
            if (r["Comment"] or "").strip():
                p["notes"] = r["Comment"].strip()
            probs.append(p)
        letters = [p["letter"] for p in probs]
        if len(set(letters)) != len(letters):
            report["problems sheet: duplicate letters"].append(f"{pcid}: {letters}")
        blk = blocks.setdefault(cid, {"source": source})
        if cid in CONTEST_SHEET_WINS:
            for kind, key in (("statement", "statement"), ("data", "data"), ("solutions", "solutions"), ("package", "package")):
                st = blk.get(kind)
                if not st:
                    continue
                n_rows = sum(1 for p in probs if key in p["have"])
                want = {"full": {p["letter"] for p in probs}, "none": set(),
                        "partial": PARTIAL_LETTERS.get((cid, kind))}[st]
                if want is None:
                    report["ruling needs the letters: partial kind with no PARTIAL_LETTERS entry"].append(f"{cid}: {kind}")
                    continue
                if n_rows == len(probs) and st == "full" or n_rows == 0 and st == "none" or {p["letter"] for p in probs if key in p["have"]} == want:
                    continue
                for p in probs:
                    has = p["letter"] in want
                    if has and key not in p["have"]:
                        p["have"].append(key)
                    elif not has and key in p["have"]:
                        p["have"].remove(key)
                    if st == "partial":
                        p["notes"] = (p.get("notes", "") + ("; " if p.get("notes") else "")
                                      + f"{kind}: {'held' if has else 'not held'} — inferred, the sheet only gives the count ({len(want)}/{len(probs)})")
                report["problems sheet rows rewritten to match the Contests sheet (ruling 2026-11-01)"].append(
                    f"{cid}: {kind} rows said {n_rows}/{len(probs)}, contest says {st}" + (f" ({len(want)})" if st == "partial" else ""))
                order = ["statement", "data", "input_validator", "output_validator", "solutions", "package"]
                for p in probs:
                    p["have"] = [k for k in order if k in p["have"]]
        if blk.get("count") is not None and blk["count"] != len(probs):
            report["problems sheet: row count differs from the contest's #P"].append(
                f"{cid}: {len(probs)} problem rows, #P {blk['count']}")
        blk.setdefault("count", len(probs))
        for kind, key in (("statement", "statement"), ("data", "data"), ("solutions", "solutions"), ("package", "package")):
            n = sum(1 for p in probs if key in p["have"])
            implied = "full" if n == len(probs) else ("none" if n == 0 else "partial")
            if blk.get(kind) and blk[kind] != implied:
                report["problems sheet: per-problem rows disagree with the contest flag"].append(
                    f"{cid}: {kind} flagged {blk[kind]}, rows say {implied} ({n}/{len(probs)})")
            blk[kind] = implied
            blk.setdefault("counts", {})
            if implied == "partial":
                blk["counts"][kind] = n
            else:
                blk["counts"].pop(kind, None)
        if not blk["counts"]:
            del blk["counts"]
        problem_rows[cid] = probs

    # ---- merge blocks into the contests' problem sets ----
    sets: dict[str, dict] = {}       # set id -> document (loaded, or new)
    set_text: dict[str, str] = {}    # set id -> file text as loaded ("" when new)
    holdings_by: dict[str, str] = {}  # set id -> first contest that wrote holdings this run

    def get_set(cid: str) -> dict:
        """The set the contest links to, loaded once; a contest without a set gets one named
        after it (DEFINITIONS.md: the set id defaults to the contest id)."""
        c = contests.get(cid) or non_mainline[cid]
        set_id = (c.get("problems") or {}).get("set")
        if not set_id:
            set_id = cid
            c["problems"] = {"set": set_id}
            if cid not in non_mainline:
                mark_dirty(cid)
            stats["contests linked to a new set"] += 1
        if set_id not in sets:
            s = load_set(set_id)
            if s is None:
                s = {"id": set_id, "contests": []}
                set_text[set_id] = ""
            else:
                set_text[set_id] = (SET_DIR / f"{set_id}.yaml").read_text()
            sets[set_id] = s
        set_entry(sets[set_id], cid)
        return sets[set_id]

    for cid in sorted(blocks):
        blk = dict(blocks[cid])
        s = get_set(cid)
        src = blk.pop("source")
        first = holdings_by.setdefault(s["id"], cid)
        if first != cid:  # a shared set: the holdings are the set's, the first member's row wins
            diffs = {k: (s.get(k), v) for k, v in blk.items() if s.get(k) != v}
            if diffs:
                report["shared set: a member's sheet row disagrees with the set's holdings (first member kept)"].append(
                    f"{s['id']} <- {cid}: {diffs}")
        else:
            s.pop("counts", None)  # derived here; a stale copy must not survive a re-run
            s.update(blk)
            if s.get("complete") is False and s.get("problems") and s.get("count") == len(s["problems"]):
                del s["complete"]  # the list has as many problems as the sheet says there are
        if src not in (s.get("provenance") or []):
            s.setdefault("provenance", []).append(src)
        stats["contests with holdings on their set"] += 1
        if cid in non_mainline:
            stats["  of which non-mainline"] += 1

    # ---- per-problem rows -> set problems + letter maps ----
    for cid in sorted(problem_rows):
        s = get_set(cid)
        merge_problem_rows(s, cid, problem_rows[cid], report, stats)
        if source not in (s.get("provenance") or []):
            s.setdefault("provenance", []).append(source)
    changed_sets = sorted(sid for sid, s in sets.items() if dump_set(s) != set_text[sid])

    # ---- judge pages -> sources (role judge_page, judge: <id>) ----
    for cid, pages in judge_pages.items():
        c = contests.get(cid) or non_mainline[cid]
        for judge, u in pages:
            url, ts = parts(u)
            _s, ch = add_source(c, url, "problemset", judge=judge, as_of=ts)
            if ch:
                stats["judge pages added to sources"] += 1
                if cid not in non_mainline:
                    mark_dirty(cid)

    # ---- report ----
    triaged = Counter()
    for sid in unmapped:
        r = sheet[sid]
        cms = num(r["CMS"])
        if sid in IGNORE_ROWS:
            report["sheet rows ignored by ruling"].append(f"{sid}: {IGNORE_ROWS[sid]}")
        elif cms in triage:
            if not num(r["#P"]) and not r["Repo"]:  # a ghost CMS id the sheet still carries — nothing to reconcile
                triaged[triage[cms]["reason"]] += 1
            else:
                report[f"sheet has problem data for a contest the catalogue triaged as `{triage[cms]['reason']}`"].append(
                    f"{sid} (CMS {cms}, {r['Full name'] or 'no name'})")
        else:
            report["sheet contest with no match in the catalogue (CMS id unknown or absent)"].append(
                f"{sid}: #P {r['#P'] or '—'}, repo {r['Repo'] or '—'}, date {r['Date'] or '—'}, section “{r['_section']}”")
    for b, a in collisions.items():
        report["several sheet rows map to one contest"].append(f"{b} <- {a}")
    renamed = sorted((s, m) for s, m in mapping.items() if s != m)
    not_in_sheet = sorted(set(contests) - set(mapping.values()))

    lines = [f"# Problem-archive progress sheet import — {args.date}", "",
             f"Generated by `tools/import_problem_archive.py` from `data/import/icpc-problem-archive-progress-{args.date}-*.csv`.",
             "", "## Summary", "",
             f"- {len(sheet)} contest rows in the sheet; {len(mapping)} matched a catalogue entry "
             f"({len(renamed)} under an older id, mapped via CMS id or series rename), {len(unmapped)} unmatched.",
             f"- {stats['contests with holdings on their set']} contests have holdings from the sheet on their problem set "
             f"({stats['  of which non-mainline']} in `registry/non-mainline.yaml`); "
             f"{len(problem_rows)} have per-problem rows from the sheet; {len(sets)} sets touched, "
             f"{len(changed_sets)} changed.",
             f"- `problemset:` filled from the sheet's Web column for {stats['problemset filled from sheet']} contests "
             f"({stats['Web column = contest website, nothing to add']} rows pointed at the contest website itself, "
             f"{stats['problemset already present']} already had the same problemset).",
             f"- {len(not_in_sheet)} catalogue contests are not in the sheet at all (the catalogue has grown since; nothing to reconcile).",
             "- Not imported: `#P est.` (estimates), `Contact email`, `Assigned to`, the `Contest names` grid.",
             "- " + ", ".join(f"{n} sheet rows carry a CMS id the catalogue triaged as `{k}`" for k, n in sorted(triaged.items()))
             + " (no problem data on any of them; triage stands).",
             "- The sheet carries no problem UUIDs; `uuid:` stays empty until a sync from the package repos fills it.",
             ""]
    order = ["dates differ (catalogue kept)", "sheet has a date the catalogue lacks (not applied — verify first)", "sheet dates applied by ruling",
             "CMS ids differ (catalogue kept)", "names differ (catalogue kept)",
             "problemset: sheet URL differs from the catalogue's (catalogue kept)",
             "sheet contest with no match in the catalogue (CMS id unknown or absent)"]
    keys = [k for k in order if k in report] + sorted(k for k in report if k not in order)
    for k in keys:
        lines += [f"## {k} ({len(report[k])})", ""] + [f"- {x}" for x in report[k]] + [""]
    lines += ["## Older ids mapped to catalogue ids (%d)" % len(renamed), ""]
    lines += [f"- {s} → {m}" for s, m in renamed] + [""]
    rep_path = ROOT / "reports" / f"problem-archive-import-{args.date}.md"

    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print(f"report sections: {len(keys)}; unmapped {len(unmapped)}; collisions {len(collisions)}")
    nm_header = "".join(l for l in nm_path.read_text().splitlines(keepends=True) if l.startswith("#"))
    nm_text = dump(nm_doc, nm_header)
    nm_changed = nm_text != nm_path.read_text()
    if args.dry_run:
        dirty = sorted(sid for sid, doc in series_docs.items() if doc.get("_dirty"))
        print(f"(dry run — nothing written; {len(dirty)} series files would change: {', '.join(dirty)}; "
              f"non-mainline registry would change: {nm_changed}; "
              f"{len(changed_sets)} of {len(sets)} problemsets files would change: {', '.join(changed_sets)})")
        return 0

    # ---- write ----
    for sid, doc in series_docs.items():
        if doc.pop("_dirty", False):
            dump_series(sid, doc, "import_problem_archive.py")
            stats["series files written"] += 1
    if nm_changed:
        nm_path.write_text(nm_text)
    SET_DIR.mkdir(exist_ok=True)
    for sid in changed_sets:
        (SET_DIR / f"{sid}.yaml").write_text(dump_set(sets[sid]))
        stats["problemsets files written"] += 1
    rep_path.write_text("\n".join(lines))
    print(f"series files written: {stats['series files written']}; problemsets files written: "
          f"{stats['problemsets files written']} of {len(sets)} touched; report: {rep_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
