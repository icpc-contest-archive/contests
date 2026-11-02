#!/usr/bin/env python3
"""Import the "ICPC Problem Archive progress" sheet into the catalogue.

One-shot import (re-runnable): reads the frozen CSV exports in data/import/
  icpc-problem-archive-progress-<date>-contests.csv   (one row per contest)
  icpc-problem-archive-progress-<date>-problems.csv   (one row per problem, 30 contests)
and writes

  series/<series>.yaml        a `problems:` block per contest (repo, count, what is held,
                              judge links, notes) — merged into the existing block, keys
                              this tool does not know about are kept
  registry/non-mainline.yaml  the same block for non-mainline contests the sheet tracks
  problems/<contest>.yaml     per-problem lists (letter, name, what is held, judge links)
  series/*.yaml problemset:   filled from the sheet's "Web" column where the catalogue
                              has none and the URL is not just the contest website
  reports/problem-archive-import-<date>.md   everything the sheet disagrees with

What is deliberately NOT imported: "#P est." (a guess), "Contact email" and
"Assigned to" (personal data / internal workflow — also stripped from the CSV), and the
"Contest names" existence grid (superseded by the catalogue itself).

Model (DEFINITIONS.md, "Problems"): the sheet's yes/partial/no flags become
full/partial/none; exact per-kind counts are kept only where the flag is partial
(`counts:`), since full and none are implied by `count`. Judge links are locators
(wrapper URLs unwrapped into url + as_of, as everywhere else).

Usage (from the repo root):
  python3 tools/import_problem_archive.py [--date 2026-11-01] [--dry-run]
  python3 tools/validate.py
"""
from __future__ import annotations

import argparse
import csv
import datetime
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from resources import norm_key, unwrap  # noqa: E402

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
PARTIAL_LETTERS = {  # (contest, kind) -> letters that HAVE it
    ("nwerc-2010", "data"): set("ABCDFGH"),       # the seven with packages
    ("nwerc-2010", "solutions"): set("ABCDFGH"),
    ("bapc-2020", "package"): set("ABCEFGHIJK"),  # all but D, the one problem not shared with ukiepc-2020
}


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null"))


def dump(doc, header: str) -> str:
    return header + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def split_urls(v: str) -> list[str]:
    return [u.strip().rstrip(",") for u in re.split(r"[;\s]+", v or "") if u.strip().rstrip(",")]


def locator(u: str):
    """A sheet URL as a catalogue locator: bare URL, or {url, as_of} for a wrapper."""
    url, ts, _via = unwrap(u)
    return {"url": url, "as_of": ts} if ts else url


def loc_url(v) -> str:
    return v["url"] if isinstance(v, dict) else v


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
    series_docs: dict[str, dict] = {}
    contests: dict[str, dict] = {}
    for f in sorted((ROOT / "series").glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        series_docs[f.stem] = doc
        for c in doc["contests"]:
            contests[c["id"]] = c
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
    today = datetime.date.today()

    # ---- build the problems block per mapped contest ----
    blocks: dict[str, dict] = {}
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
            blk["repo"] = repo
            name = repo.split("/", 1)[1]
            if name not in ("statement-only", cid):
                report["repo named differently from the contest id"].append(
                    f"{cid}: repo `{repo}`" + (f" (sheet row `{sid}`)" if sid != cid else ""))
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
        judges = {}
        for col, key in JUDGE_COLS:
            urls = split_urls(r[col])
            if urls:
                locs = [locator(u) for u in urls]
                judges[key] = locs[0] if len(locs) == 1 else locs
        if judges:
            blk["judges"] = judges
        if (r["Comment"] or "").strip():
            blk["notes"] = r["Comment"].strip()
        if blk:
            blk["source"] = source
            blocks[cid] = blk
            if c.get("status") == "upcoming":
                report["problem data on an upcoming contest (not imported)"].append(f"{cid}: {blk}")
                del blocks[cid]

        # ---- disagreements with the catalogue (report only, nothing changed) ----
        if cid in non_mainline:
            continue
        sd, cd = (r["Date"] or "").strip(), c.get("date")
        if sd and cd and sd != cd and not cd.startswith(sd[:len(cd)]):
            report["dates differ (catalogue kept)"].append(f"{cid}: sheet {sd}, catalogue {cd}")
        elif sd and not cd:
            if cid in APPLY_DATES:
                c["date"] = sd
                if source not in (c.get("sources") or []):
                    c.setdefault("sources", []).append(source)
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
                blk = blocks.get(cid)
                if blk is not None:
                    cur = blk.setdefault("judges", {}).get(key)
                    cur = [] if cur is None else (cur if isinstance(cur, list) else [cur])
                    if norm_key(unwrap(u)[0]) not in {norm_key(loc_url(x)) for x in cur}:
                        cur.append(locator(u))
                    blk["judges"][key] = cur[0] if len(cur) == 1 else cur
                    stats["Web column judge link moved to judges"] += 1
        if len(webs) > 1:
            report["Web column has several URLs (first used as problemset)"].append(f"{cid}: {webs}")
            webs = webs[:1]
        if webs:
            site_keys = {norm_key(loc_url(w)) for w in (c.get("web") if isinstance(c.get("web"), list) else [c.get("web")]) if w}
            cand = [locator(u) for u in webs if norm_key(unwrap(u)[0]) not in site_keys]
            roots = [p for p in cand if is_site_root(loc_url(p))]
            if roots:  # a bare site root is a website, not a problem set: an extra web locator (ruling 2026-11-01)
                cur = [w for w in (c.get("web") if isinstance(c.get("web"), list) else [c.get("web")]) if w]
                c["web"] = cur + roots if len(cur + roots) > 1 else (cur + roots)[0]
                c.setdefault("sources", []).append(source) if source not in (c.get("sources") or []) else None
                stats["extra web locator added from the Web column"] += len(roots)
                mark_dirty(cid)
                cand = [p for p in cand if p not in roots]
            if not cand:
                stats["Web column = contest website, nothing to add"] += 1
            elif c.get("problemset"):
                have = {norm_key(loc_url(p)) for p in (c["problemset"] if isinstance(c["problemset"], list) else [c["problemset"]])}
                new = [p for p in cand if norm_key(loc_url(p)) not in have]
                if new:  # several places publish the set: keep both (ruling 2026-11-01)
                    cur = c["problemset"] if isinstance(c["problemset"], list) else [c["problemset"]]
                    c["problemset"] = cur + new
                    if source not in (c.get("sources") or []):
                        c.setdefault("sources", []).append(source)
                    stats["problemset: second URL added"] += len(new)
                    mark_dirty(cid)
                else:
                    stats["problemset already present"] += 1
            else:
                c["problemset"] = cand[0] if len(cand) == 1 else cand
                if source not in (c.get("sources") or []):
                    c.setdefault("sources", []).append(source)
                stats["problemset filled from sheet"] += 1
                mark_dirty(cid)

    # ---- per-problem files ----
    problem_files: dict[str, dict] = {}
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
                p["judges"] = {"kattis": locator(r["Kattis"].strip())}
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
        problem_files[cid] = {"contest": cid, "source": source, "problems": probs}

    # ---- merge blocks into the catalogue ----
    for cid, blk in blocks.items():
        c = contests.get(cid) or non_mainline[cid]
        old = c.get("problems") if isinstance(c.get("problems"), dict) else {}
        old.pop("counts", None)  # derived here; a stale copy must not survive a re-run
        c["problems"] = {**old, **blk}
        stats["contests with a problems block"] += 1
        if cid in non_mainline:
            stats["  of which non-mainline"] += 1
        else:
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
             f"- {stats['contests with a problems block']} contests received a `problems:` block "
             f"({stats['  of which non-mainline']} in `registry/non-mainline.yaml`); "
             f"{len(problem_files)} got a per-problem file under `problems/`.",
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
    if args.dry_run:
        print("(dry run — nothing written)")
        return 0

    # ---- write ----
    header = "# Maintained in-repo; problem-archive data imported by tools/import_problem_archive.py.\n"
    for sid, doc in series_docs.items():
        if doc.pop("_dirty", False):
            (ROOT / "series" / f"{sid}.yaml").write_text(dump(doc, header))
            stats["series files written"] += 1
    nm_header = "".join(l for l in nm_path.read_text().splitlines(keepends=True) if l.startswith("#"))
    nm_path.write_text(dump(nm_doc, nm_header))
    pdir = ROOT / "problems"
    pdir.mkdir(exist_ok=True)
    for cid, doc in problem_files.items():
        (pdir / f"{cid}.yaml").write_text(dump(doc, "# Per-problem data; letter/name/have from the progress sheet, "
                                                   "uuid and judge links maintained here.\n"))
    rep_path.write_text("\n".join(lines))
    print(f"series files written: {stats['series files written']}; problem files: {len(problem_files)}; report: {rep_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
