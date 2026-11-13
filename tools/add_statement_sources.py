#!/usr/bin/env python3
"""Record the statement a problem set's names were read from as a source of its contest.

tools/apply_statement_titles.py writes where the names came from into the set's provenance
("problem names read from the published statement <address> ..."). A provenance note is free
text. Only a source of the contest gets a source page, shows on the contest's page, is found
by the search box, is health-checked and is archived by the capture rounds. So every such
statement is also made a source (DEFINITIONS.md, Provenance):

  - a problem list on an online judge of judges.yaml (its contest_url)   -> judge_page, judge: <id>
  - anything else: a PDF, an archive, a page, a folder of statements     -> problemset

Addresses are written the catalogue's way: a Wayback address becomes the original address
plus `as_of`; raw.githubusercontent.com becomes the file's page on github.com; HEAD in a
GitHub address becomes the repository's default branch when BRANCH knows it.

apply_statement_titles.py calls statement_source() for everything it applies. Run on its own,
this tool backfills the sets filled before that (2026-11-13: 30 contests) from their
provenance notes. It adds nothing that is already there, so it is safe to run again.

usage: add_statement_sources.py [--date YYYY-MM-DD] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, add_source, dump_series, find_source, load_judges, load_series, load_sets  # noqa: E402
from resources import norm_key  # noqa: E402

NOTE = re.compile(r"problem names read from the published statement (\S+) \(capture ")

# Default branch of the GitHub repositories whose statements were cited with HEAD (looked up 2026-11-13).
# HEAD follows whatever the repository holds later; a branch name is at least what the owner calls the main line.
BRANCH = {
    "alielgamal9/ecpc2022": "main",
    "mohannad-elsayed/ecpc-past-contest": "master",
    "kitihounel/competitive-programming-africa": "master",
    "mukerem/icpc-journey": "master",
}
# Statements read from a local Wayback capture of a dead address: the snapshot time, so the address keeps its meaning.
AS_OF = {
    "http://acm.fci-cu.edu.eg/archive/ENC08.pdf": "20091025030029",  # inside the egypt-2009 website capture
}


def canonical(url: str) -> tuple[str, str | None]:
    """(address as the catalogue writes it, as_of or None)."""
    as_of = None
    m = re.match(r"https?://web\.archive\.org/web/(\d{14})[a-z_]*/(.+)$", url)
    if m:
        as_of, url = m.group(1), re.sub(r"^(https?://[^/:]+):80(?=/|$)", r"\1", m.group(2))
    m = re.match(r"https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$", url)
    if m:
        url = "https://github.com/{}/{}/blob/{}/{}".format(*m.groups())
    m = re.match(r"(https://github\.com/([^/]+/[^/]+)/(?:blob|tree)/)HEAD(/.+)$", url)
    if m and m.group(2).lower() in BRANCH:
        url = m.group(1) + BRANCH[m.group(2).lower()] + m.group(3)
    return url, as_of or AS_OF.get(url)


def judge_of(url: str, judges: dict) -> str | None:
    """The judge whose contest pages start like this address, if any."""
    k = norm_key(url)
    for jid, j in judges.items():
        pat = j.get("contest_url") or ""
        if "{id}" in pat and k.startswith(norm_key(pat.split("{id}")[0])) and len(norm_key(pat.split("{id}")[0])) > 12:
            return jid
    return None


def statement_source(c: dict, url: str, judges: dict) -> tuple[dict, bool, str]:
    """Make the statement at `url` a source of contest `c`. Returns (source, changed, role)."""
    url, as_of = canonical(url)
    jid = judge_of(url, judges)
    had = find_source(c, url)
    if had is not None and ("problemset" in had["roles"] or "judge_page" in had["roles"]):
        return had, False, "judge_page" if "judge_page" in had["roles"] else "problemset"
    if jid:
        s, changed = add_source(c, url, "judge_page", judge=jid, as_of=as_of)
        return s, changed, "judge_page"
    s, changed = add_source(c, url, "problemset", as_of=as_of)
    return s, changed, "problemset"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    series, sets, judges = load_series(), load_sets(), load_judges()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    added, there, skipped, touched = [], 0, [], set()
    for sid, s in sorted(sets.items()):
        for note in s.get("provenance") or []:
            m = NOTE.search(str(note))
            if not m:
                continue
            members = [e["contest"] for e in s.get("contests") or [] if e["contest"] in where]
            if len(members) > 1 and any(find_source(where[x][1], canonical(m.group(1))[0]) for x in members):
                there += 1  # a shared set: the statement is already a source of the contest it was read for
                continue
            if len(members) != 1:
                skipped.append(f"{sid}: the set is used by {len(members)} contests ({', '.join(members) or 'none'}); say which one {m.group(1)} belongs to")
                continue
            ser, c = where[members[0]]
            src, changed, role = statement_source(c, m.group(1), judges)
            if not changed:
                there += 1
                continue
            touched.add(ser)
            added.append((members[0], role, src["url"], src.get("as_of"), m.group(1)))
    if not a.dry_run and added:
        for ser in sorted(touched):
            dump_series(ser, series[ser], f"add_statement_sources.py ({a.date})")
        lines = [f"# Statements recorded as sources — {a.date}", "",
                 "Generated by `tools/add_statement_sources.py`. Each address below was named only in the provenance note of a problem",
                 "set, as the statement its problem names were read from. It is now a source of the contest as well, so it has a source",
                 "page, is found by the search box and is archived by the next capture round.", "",
                 f"- sources added: {len(added)} ({sum(1 for x in added if x[1] == 'problemset')} problem sets, "
                 f"{sum(1 for x in added if x[1] == 'judge_page')} judge pages)",
                 f"- statements that were a source already: {there}", f"- skipped: {len(skipped)}", "",
                 "## added", ""]
        for cid, role, url, as_of, was in added:
            lines.append(f"- {cid}: {role.replace('_', ' ').replace('problemset', 'problem set')} {url}" + (f" (as of {as_of})" if as_of else "")
                         + (f"  — cited as {was}" if was != url else ""))
        if skipped:
            lines += ["", "## skipped", ""] + [f"- {x}" for x in skipped]
        (ROOT / "reports" / f"statement-sources-{a.date}.md").write_text("\n".join(lines) + "\n")
    print(f"sources added: {len(added)} ({sum(1 for x in added if x[1] == 'judge_page')} judge pages), already there: {there}, "
          f"skipped: {len(skipped)}, series files: {len(touched)}" + (" (dry run)" if a.dry_run else ""))
    for x in skipped:
        print("  skipped:", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
