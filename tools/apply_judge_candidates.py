#!/usr/bin/env python3
"""Apply the online-judge hunt (2026-11-03) to the catalogue: judges.yaml, judge_page
sources, and problem lists for tools/mine_judge_links.py.

Input: the hunt output files (format: judgehunt INSTRUCTIONS.md — {brief, judges,
candidates, unmatched, veins}), in the order given on the command line.

What it does, deterministically (a second run changes 0 files):
  1. judges.yaml: adds every judge id that gets a candidate, plus the blocked-but-relevant
     judges (qoj, pintia, beecrowd, vjudge, ucup), with status/notes from the hunt files.
     Existing entries are kept intact. The hunt's `codeforces-gym` and `codeforces` are
     one registry id, `codeforces` (the URL says gym or regular round). A judge described
     in several hunt files takes the entry of the file that recorded candidates for it
     (first file otherwise).
     URL patterns with exactly one placeholder are normalised to `{id}`.
  2. Sources (series/*.yaml and registry/non-mainline.yaml): every candidate with
     confidence high gets a judge_page source via catalogue.add_source, note
     "<judge_name> (judge hunt 2026-11-03: <evidence>)". A medium candidate is applied
     only when it is a shared Latin America set attached to a sibling contest (the
     evidence says so, or the judge names the Latin America regional) or when the hunt
     verified at least half of the catalogue's problem titles (N/M titles match); the rest
     of medium and all low go to the report "for ruling". A candidate whose URL is already
     a source of the contest under another role is skipped (reported); a URL already
     present as a judge_page source of the same judge counts as applied (rerun). Contests
     not in the catalogue or the registry are reported.
  3. Problem lists: applied candidates that carry `problems` are injected into the miner's
     frozen state (data/import/judge-pages-<date>.json) as pages keyed
     "<contest>|<judge>|<url>" with capture "hunt:<brief>", captures [] (no archive
     capture), source "hunt"; each problem {id, letter, name, url} (url from the candidate,
     else the judge's problem_url pattern). A page that a real capture already fills is
     left alone. Run the miner afterwards to apply them with its matching rules.
  4. Report reports/judge-hunt-<date>.md: per judge applied / for ruling / skipped, the
     hunts' unmatched lists verbatim, veins, blockers and catalogue gaps.

Usage (repo root):
  python3 tools/apply_judge_candidates.py [--dry-run] out/cf-qoj.json out/east-asia.json out/rest-of-world.json
  python3 tools/mine_judge_links.py --archive /path/to/judgecaps
  python3 tools/apply_judge_candidates.py out/*.json      # again: copies the miner's per-judge numbers into the report
  python3 tools/validate.py
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import Dumper, add_source, dump_series, load_judges, load_series, sources  # noqa: E402
from resources import norm_key  # noqa: E402

HUNT_DATE = "2026-11-03"
JUDGE_ALIASES = {"codeforces-gym": "codeforces"}
BLOCKED_RELEVANT = ("qoj", "pintia", "beecrowd", "vjudge", "ucup")
JUDGE_KEYS = ("id", "name", "url", "problem_url", "contest_url", "status", "closed", "statements", "submissions", "notes")
LETTER = re.compile(r"^[A-Z][0-9]?$|^[0-9]{1,2}$")  # schema/problemsets.schema.json
TITLES = re.compile(r"(\d+)\s*/\s*(\d+)\s+(?:catalogue\s+)?(?:problem\s+)?titles?\s+match")
LATAM = re.compile(r"latin[o]?\s*-?\s*americ", re.I)
TOOL_TAG = "apply_judge_candidates.py (judge hunt 2026-11-03)"

# the blockers and catalogue gaps the hunts noticed (from the hunt files' judge notes and
# unmatched lists; listed here so the report carries them in one place)
BLOCKERS = [
    "QOJ (qoj.ac, alias jiang.ly): Cloudflare JS challenge (403) on every page; category 21 'Asia East Continent' "
    "(5 EC online qualifications, 20 regional subcategories, all 11 EC-Finals 2015-2025) and category 458 "
    "'The 2024 ICPC Asia East Regionals' need a browser-side pass to harvest contest ids.",
    "PTA 拼题A (Pīntí A, pintia.cn): problem-set listing and metadata APIs answer 401 USER_NOT_LOGGED_IN; only the "
    "textbook sets and the public XCPC scoreboards are reachable; needs a browser (logged-in) pass.",
    "beecrowd (ex URI Online Judge): Cloudflare 'Just a moment' challenge (403) on every page; hosts the Maratona "
    "de Programação sets (problems 1xxx-3xxx, source 'Maratona'); needs a browser.",
    "Virtual Judge (vjudge.net): Cloudflare challenge (403) on /, /contest and the /contest/data API; needs a browser.",
    "Eolymp: contest problem lists and statements need a sign-in (API /contests/{id}/problems unauthenticated); "
    "candidates matched by contest name and date only.",
    "omegaUp: /api/contest/list/ gives anonymous callers only current contests, /api/contest/problems/ needs a "
    "login; only ICPCMX2021 (public problems tagged problemTagICPC) could be confirmed.",
    "Jutge.org: SWERC 2017-2023 sets live in contests that need a sign-in; the public problem list has no SWERC set.",
    "POJ (poj.org): 502 Bad Gateway / connection reset on 2026-11-03; the Source-field search "
    "(/searchproblem?field=source&key=...) could not be used.",
    "Codeforces gyms: problem lists need a login (contest.standings refuses gyms), so gym candidates carry no "
    "problem lists; codeforces.com HTML is behind Cloudflare from this network (the API is not).",
    "CodeChef: the 2020-2024 ICPC India rounds are not in the public past-contest API (codes unknown).",
    "Toph: no ICPC Dhaka regional or preliminary is publicly listed (invite-only/unlisted if run there).",
    "HDU: the 'Online' preliminaries are private (login); the server resets connections intermittently.",
]
CATALOGUE_GAPS = [
    "China regionals missing from the catalogue (judge pages exist): hangzhou-2025, jinan-2024, jinan-2025, "
    "kunming-2025, hefei-2024, hefei-2025, hong-kong-2020, hong-kong-2021.",
    "AOJ lists no 2025 Yokohama regional yet (as of 2026-11-03); japan-2025 has no AOJ candidate.",
    "ICPC India online preliminaries / first rounds 2010-2016 (CodeChef) have no catalogue series.",
    "Ukrainian UCPC Stage I (1/8 final) and Stage III (1/2 final) on eolymp are separate rounds; the catalogue has "
    "one ukraine-YYYY entry (Stage II).",
    "Taiwan Online Programming Contest (TOPC) rounds have no catalogue entries.",
]


# ---------------------------------------------------------------- judges.yaml
def norm_pattern(p):
    """A URL pattern with exactly one placeholder becomes `...{id}...`; otherwise verbatim."""
    if not p or not isinstance(p, str):
        return None
    holes = re.findall(r"\{[^}]*\}", p)
    if len(holes) == 1:
        return p.replace(holes[0], "{id}")
    return p


def build_judge(jid: str, recs: list[tuple[str, dict, int]]) -> dict:
    """One judges.yaml entry from the hunt records [(brief, record, n_candidates)] of a judge."""
    recs = sorted(recs, key=lambda r: (-r[2], 0))  # most candidates first; stable on argument order
    primary = recs[0][1]
    e = {"id": jid, "name": primary.get("name") or jid, "url": primary.get("url")}
    pu, cu = norm_pattern(primary.get("problem_url")), norm_pattern(primary.get("contest_url"))
    if pu:
        e["problem_url"] = pu
    if cu:
        e["contest_url"] = cu
    e["status"] = primary.get("status") or "active"
    e["statements"] = bool(primary.get("statements"))
    e["submissions"] = bool(primary.get("submissions"))
    notes = (primary.get("notes") or "").strip()
    if notes:
        e["notes"] = notes
    return {k: e[k] for k in JUDGE_KEYS if k in e}


def write_judges(existing_text: str, entries: list[dict]) -> str:
    head = existing_text.split("judges:", 1)[0]
    return head + yaml.dump({"judges": entries}, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)


# ---------------------------------------------------------------- verdicts
def title_ratio(evidence: str):
    m = TITLES.search(evidence or "")
    if not m or int(m.group(2)) == 0:
        return None
    return int(m.group(1)) / int(m.group(2))


def verdict(cand: dict) -> tuple[str, str]:
    """-> ("apply" | "ruling", reason)."""
    conf = cand.get("confidence")
    ev = cand.get("evidence") or ""
    if conf == "high":
        return "apply", "high"
    if conf == "medium":
        if ("shared" in ev.lower() and LATAM.search(ev)) or LATAM.search(cand.get("judge_name") or ""):
            return "apply", "medium: shared Latin America set attached to a sibling contest"
        r = title_ratio(ev)
        if r is not None and r >= 0.5:
            return "apply", f"medium: {int(round(r * 100))}% of the catalogue's problem titles verified"
        return "ruling", "medium: not a shared set, titles not verified (or under 50%)"
    return "ruling", f"{conf}: confidence below medium"


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+", help="hunt output files (judgehunt out/*.json), in order")
    ap.add_argument("--date", default="2026-11-02", help="date of the miner's frozen state file")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    today = datetime.date.today()

    hunts = []
    for f in args.files:
        d = json.loads(Path(f).read_text())
        d["_file"] = f
        hunts.append(d)

    # ---- catalogue ----
    series = load_series()
    contests: dict[str, tuple[str, dict]] = {}
    for sid, doc in series.items():
        for c in doc["contests"]:
            contests[c["id"]] = (sid, c)
    nm_path = ROOT / "registry" / "non-mainline.yaml"
    nm_text = nm_path.read_text()
    nm_doc = yaml.safe_load(nm_text)
    for c in nm_doc.get("non_mainline_contests") or []:
        contests.setdefault(c["id"], ("non-mainline", c))

    # ---- 1. judges.yaml ----
    judges_path = ROOT / "judges.yaml"
    judges_text = judges_path.read_text()
    existing = load_judges()
    hunt_judges: dict[str, list[tuple[str, dict, int]]] = defaultdict(list)
    cand_count: Counter = Counter()
    for h in hunts:
        for x in h["candidates"]:
            cand_count[(h["brief"], JUDGE_ALIASES.get(x["judge"], x["judge"]))] += 1
    for h in hunts:
        for j in h.get("judges") or []:
            jid = JUDGE_ALIASES.get(j["id"], j["id"])
            hunt_judges[jid].append((h["brief"], j, cand_count[(h["brief"], jid)]))
    wanted = {jid for (_, jid) in cand_count} | set(BLOCKED_RELEVANT)
    new_entries = []
    for jid in sorted(wanted):
        if jid in existing:
            continue
        if jid not in hunt_judges:
            print(f"warning: judge {jid} has candidates but no judge record in the hunt files", file=sys.stderr)
            continue
        new_entries.append(build_judge(jid, hunt_judges[jid]))
    judges_out = write_judges(judges_text, list(existing.values()) + new_entries)
    judge_ids = set(existing) | {e["id"] for e in new_entries}
    judge_names = {**{k: v["name"] for k, v in existing.items()}, **{e["id"]: e["name"] for e in new_entries}}
    surveyed_only = sorted(j for j in hunt_judges if j not in judge_ids)

    # ---- 2. candidates -> sources ----
    stats: Counter = Counter()
    applied: dict[str, list[str]] = defaultdict(list)      # judge -> lines
    ruling: dict[str, list[str]] = defaultdict(list)
    skipped: dict[str, list[str]] = defaultdict(list)
    flagged: list[str] = []                                # applied, but the catalogue says upcoming
    changed_series: set[str] = set()
    nm_changed = False
    to_inject: list[tuple[str, str, str, str, dict]] = []  # (brief, cid, jid, url, cand)
    seen_keys: set[tuple[str, str, str]] = set()

    for h in hunts:
        brief = h["brief"]
        for x in h["candidates"]:
            jid = JUDGE_ALIASES.get(x["judge"], x["judge"])
            cid, url = x["contest"], x["url"].strip()
            line = f"{cid} <- {url} — {x.get('judge_name', '')!s} [{x.get('confidence')}] {x.get('evidence', '')}"
            if (cid, jid, url) in seen_keys:
                skipped[jid].append(f"{line} (duplicate candidate in the hunt files)")
                stats["skipped: duplicate"] += 1
                continue
            seen_keys.add((cid, jid, url))
            if cid not in contests:
                skipped[jid].append(f"{line} (contest not in the catalogue or the registry)")
                stats["skipped: contest unknown"] += 1
                continue
            sid, c = contests[cid]
            if jid not in judge_ids:
                skipped[jid].append(f"{line} (judge not in judges.yaml)")
                stats["skipped: judge unknown"] += 1
                continue
            k = norm_key(url)
            present = next((s for s in sources(c) if norm_key(s["url"]) == k), None)
            if present is not None and present.get("judge") == jid:
                # same page, same judge: the source exists (a rerun, or an earlier import); nothing to add
                mine = f"(judge hunt {HUNT_DATE}:" in (present.get("note") or "")
                why = verdict(x)[1] if mine else "already a judge_page source from an earlier import"
                stats["sources already present"] += 1
            elif present is not None:
                skipped[jid].append(f"{line} (URL already a source of the contest, roles {present['roles']})")
                stats["skipped: already a source (other role)"] += 1
                continue
            else:
                v, why = verdict(x)
                if v == "ruling":
                    ruling[jid].append(f"{line} ({why})")
                    stats["for ruling"] += 1
                    continue
                note = f"{x.get('judge_name') or judge_names[jid]} (judge hunt {HUNT_DATE}: {x.get('evidence', '')})"
                add_source(c, url, "problemset", judge=jid, note=note)
                stats["sources added"] += 1
                stats[f"{jid}: sources added"] += 1
                if sid == "non-mainline":
                    nm_changed = True
                else:
                    changed_series.add(sid)
            applied[jid].append(f"{line} ({why}"
                                f"{'; ' + str(len(x['problems'])) + ' problems injected' if x.get('problems') else ''})")
            d = c.get("date")
            try:
                dd = datetime.date.fromisoformat(d) if d else None
            except ValueError:
                dd = None
            if c.get("status") == "upcoming" or (dd and dd > today):
                flagged.append(f"{cid} (status {c.get('status')}, date {d}): {url} — {x.get('judge_name', '')}")
            if x.get("problems"):
                to_inject.append((brief, cid, jid, url, x))

    # ---- 3. frozen pages for the miner ----
    frozen_path = ROOT / "data" / "import" / f"judge-pages-{args.date}.json"
    frozen = json.loads(frozen_path.read_text()) if frozen_path.exists() else {}
    frozen_text = json.dumps(frozen, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    pages = frozen.setdefault("pages", {})
    frozen.setdefault("archive_layout", "<series>/<contest>/judge-<judge>/<capture>/page.html")
    injected: dict[str, list[str]] = defaultdict(list)
    patterns = {**{k: v.get("problem_url") for k, v in existing.items()}, **{e["id"]: e.get("problem_url") for e in new_entries}}
    for brief, cid, jid, url, x in sorted(to_inject, key=lambda t: (t[1], t[2], t[3])):
        key = f"{cid}|{jid}|{url}"
        old = pages.get(key)
        if old and old.get("captures"):
            skipped[jid].append(f"{cid} <- {url}: problem list not injected, a real capture fills this page ({old['capture']})")
            stats["problem lists not injected (real capture exists)"] += 1
            continue
        probs = []
        seen_ids: set[str] = set()
        for p in x["problems"]:
            pid_ = str(p.get("id") or "").strip()
            name = (p.get("name") or "").strip()
            if not pid_ or not name or pid_ in seen_ids:
                continue
            seen_ids.add(pid_)
            letter = (p.get("letter") or "").strip() or None
            if letter and not LETTER.match(letter):
                letter = None
            purl = (p.get("url") or "").strip()
            if not purl and patterns.get(jid) and "{id}" in patterns[jid]:
                purl = patterns[jid].replace("{id}", pid_)
            probs.append({"id": pid_, "letter": letter, "name": name, "url": purl or None})
        pages[key] = {"as_of": None, "capture": f"hunt:{brief}", "captures": [], "contest": cid, "judge": jid,
                      "problems": probs, "skipped": [], "source": "hunt", "tried": [], "url": url}
        injected[jid].append(f"{cid}: {url} ({len(probs)} problems)")
        stats["problem lists injected"] += 1
        stats[f"{jid}: problem lists injected"] += 1
    frozen_out = json.dumps(frozen, indent=1, ensure_ascii=False, sort_keys=True) + "\n"

    # ---- 4. write ----
    written = []
    if not args.dry_run:
        if judges_out != judges_text:
            judges_path.write_text(judges_out)
            written.append("judges.yaml")
        for sid in sorted(changed_series):
            dump_series(sid, series[sid], TOOL_TAG)
            written.append(f"series/{sid}.yaml")
        if nm_changed:
            head = nm_text.split("non_mainline_contests:", 1)[0]
            nm_path.write_text(head + yaml.dump(nm_doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
            written.append("registry/non-mainline.yaml")
        if frozen_out != frozen_text:
            frozen_path.write_text(frozen_out)
            written.append(str(frozen_path.relative_to(ROOT)))

    # ---- 5. report ----
    lines = [f"# Online-judge hunt applied — {HUNT_DATE}", "",
             f"Generated by `tools/apply_judge_candidates.py` from {', '.join(Path(f).name for f in args.files)} "
             f"(hunt briefs: {', '.join(h['brief'] for h in hunts)}). Problem lists carried by the candidates were "
             f"injected into `data/import/judge-pages-{args.date}.json` and applied by `tools/mine_judge_links.py` "
             f"(its own report: `reports/judge-links-{args.date}.md`).", "",
             "## Rules applied", "",
             "- confidence high: judge_page source added (note = the judge's contest name + the hunt's evidence).",
             "- confidence medium: applied only for a shared Latin America set attached to a sibling contest "
             "(Codeforces gym / omegaUp / eolymp pages named for the whole Latin America regional) or when the hunt "
             "verified at least half of the catalogue's problem titles; everything else medium, and all low, is listed "
             "under *for ruling*.",
             "- a candidate whose URL is already a source of the contest under another role (mostly Codeforces gyms "
             "recorded as `problemset`) is skipped and listed; giving those addresses the judge_page role too is a "
             "ruling (they are the same page).",
             "- `codeforces-gym` and `codeforces` from the hunt are one judge id, `codeforces` (gym vs regular round "
             "is in the URL).",
             "- problem lists: injected as frozen pages (capture `hunt:<brief>`, no archive capture) and applied by the "
             "miner with its usual matching (title, then letter; rows created for holdings-only sets unless the page "
             "lists more than `count`; translated titles not created).", "",
             "## Totals", ""]
    n_app = sum(len(v) for v in applied.values())
    lines += [f"- candidates applied (judge_page sources): {n_app}",
              f"- candidates for ruling: {sum(len(v) for v in ruling.values())}",
              f"- candidates skipped: {sum(len(v) for v in skipped.values())}",
              f"- problem lists injected for the miner: {sum(len(v) for v in injected.values())}"]
    lines += ["", f"- judges registered in judges.yaml for the hunt (added when missing): {', '.join(sorted(wanted))}",
              f"- judges surveyed by the hunts but not registered (no candidates, not blocked-relevant): "
              f"{', '.join(surveyed_only) or 'none'}", ""]
    lines += ["## Per judge", ""]
    for jid in sorted(judge_ids | set(applied) | set(ruling) | set(skipped)):
        if not (applied.get(jid) or ruling.get(jid) or skipped.get(jid)):
            continue
        lines += [f"### {jid} — {judge_names.get(jid, jid)}", "",
                  f"- applied: {len(applied.get(jid, []))} (problem lists injected: {len(injected.get(jid, []))})",
                  f"- for ruling: {len(ruling.get(jid, []))}", f"- skipped: {len(skipped.get(jid, []))}", ""]
        for title, lst in (("Applied", applied.get(jid)), ("For ruling", ruling.get(jid)), ("Skipped", skipped.get(jid))):
            if lst:
                lines += [f"#### {title} ({len(lst)})", ""] + [f"- {x}" for x in lst] + [""]
    # the miner's per-judge summary (links added, rows created) for the hunt's judges, copied from its report
    # when it exists: run this tool once more after the miner so the numbers land here
    miner_rep = ROOT / "reports" / f"judge-links-{args.date}.md"
    lines += [f"## What the miner made of the injected pages (from `reports/judge-links-{args.date}.md`)", ""]
    if miner_rep.exists():
        blocks = re.split(r"\n(?=### )", miner_rep.read_text().split("## Per judge", 1)[-1].split("## Totals", 1)[0])
        hunt_judges_seen = {j for j in injected} | {j for j in applied}
        for b in blocks:
            m = re.match(r"### (\S+)\n", b)
            if m and m.group(1) in hunt_judges_seen:
                vals = dict(re.findall(r"- ([^:]+): (\d+)", b))
                lines.append(f"- {m.group(1)}: pages parsed {vals.get('pages parsed', '?')}, links added "
                             f"{vals.get('links added', '?')}, rows created {vals.get('rows created', '?')}, titles "
                             f"unmatched {vals.get('titles unmatched', '?')}, pages held back (count) "
                             f"{vals.get('pages held back (count)', '?')}, matched by letter {vals.get('matched by letter (title differs)', '?')}")
        tot = re.search(r"- problem rows now: (\d+) \(before: (\d+)\)", miner_rep.read_text())
        if tot:
            lines.append(f"- problem rows: {tot.group(2)} -> {tot.group(1)} (the miner's run after this tool)")
    else:
        lines.append("- miner report not found; run tools/mine_judge_links.py, then this tool again")
    no_set = sorted({cid for _, cid, _, _, _ in to_inject if not (contests[cid][1].get("problems") or {}).get("set")})
    lines += ["", f"## Injected pages whose contest has no problem set ({len(no_set)} contests; the miner cannot apply "
              "them until a set exists — DEFINITIONS.md, Problems)", ""]
    lines += [f"- {cid}: " + ", ".join(sorted({jid for _, c2, jid, _, _ in to_inject if c2 == cid})) for cid in no_set] or ["- none"]
    lines += ["", "## Applied to contests the catalogue still lists as upcoming (they have evidently run; update status/date)", ""]
    lines += [f"- {x}" for x in flagged] or ["- none"]
    lines += ["", "## Problem lists injected for the miner", ""]
    for jid in sorted(injected):
        lines += [f"### {jid} ({len(injected[jid])})", ""] + [f"- {x}" for x in injected[jid]] + [""]
    lines += ["## Unmatched (verbatim from the hunts: ICPC-looking judge pages with no catalogue contest)", ""]
    for h in hunts:
        groups: dict[str, list[dict]] = defaultdict(list)
        for u in h.get("unmatched") or []:
            groups[JUDGE_ALIASES.get(u.get("judge") or "?", u.get("judge") or "?")].append(u)
        lines += [f"### {h['brief']} ({sum(len(v) for v in groups.values())})", ""]
        for jid in sorted(groups):
            lines += [f"#### {jid} ({len(groups[jid])})", ""]
            for u in groups[jid]:
                lines.append(f"- {u.get('judge_name', '')} — {u.get('url', '')}" + (f" — {u['note']}" if u.get("note") else ""))
            lines.append("")
    lines += ["## Veins (listing/API URLs that cover many contests)", ""]
    for h in hunts:
        lines += [f"### {h['brief']}", ""] + [f"- {v}" for v in h.get("veins") or []] + [""]
    lines += ["## Blockers", ""] + [f"- {b}" for b in BLOCKERS] + [""]
    lines += ["## Catalogue gaps the hunts noticed", ""] + [f"- {g}" for g in CATALOGUE_GAPS] + [""]
    rep = ROOT / "reports" / f"judge-hunt-{HUNT_DATE}.md"
    rep_text = "\n".join(lines)
    if not args.dry_run and (not rep.exists() or rep.read_text() != rep_text):
        rep.write_text(rep_text)
        written.append(str(rep.relative_to(ROOT)))

    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print(f"judges added: {len(new_entries)}; series changed: {len(changed_series)}; registry changed: {nm_changed}; "
          f"frozen pages injected: {stats.get('problem lists injected', 0)}; "
          f"{'would write' if args.dry_run else 'written'}: {len(written) if not args.dry_run else '-'}"
          + ("" if args.dry_run else f" ({', '.join(written) if written else 'nothing'})"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
