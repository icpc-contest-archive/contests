#!/usr/bin/env python3
"""One-off migration: problem sets become objects (2026-11-02; DEFINITIONS.md, Problems).

Before: holdings lived in a `problems:` block on each contest (repo, count, held states,
counts) and per-problem rows in problems/<contest-id>.yaml. One set used by several
contests (NCPC + UKIEPC 2013/2014) existed twice with the same uuids.

After: problemsets/<set-id>.yaml holds everything about one set — holdings, the contests
that used it with their letter maps, and the problems (each with a permanent internal id
`p-xxxxxxxx`); the contest keeps only `problems: {set: <set-id>}`.

  set id        = the contest id; shared sets get a combined id (SHARED below)
  problem id    = p- + 8 hex of sha1(uuid) when known (so a reused problem gets the
                  same id everywhere), else p- + 8 hex of sha1(set|letter|name)
  judges        = {kattis: url} -> [{judge: kattis, url, id: <short name>}]
  sources       -> provenance

Usage: python3 tools/migrate_problemsets.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import Dumper, dump_series, load_series, normalise_contest  # noqa: E402

# contests whose per-problem files describe the same set (uuid-identical) -> one set
SHARED = {
    "nordic-ukiepc-2013": ["nordic-2013", "ukiepc-2013"],
    "nordic-ukiepc-2014": ["nordic-2014", "ukiepc-2014"],
}
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
    if uuid:  # hash, not prefix: Kattis-issued uuids share long prefixes (8ee7605a-...)
        return "p-" + hashlib.sha1(uuid.lower().encode()).hexdigest()[:8]
    h = hashlib.sha1(f"{set_id}|{letter or ''}|{name}".encode()).hexdigest()
    return "p-" + h[:8]


def convert_problem(p: dict, set_id: str) -> dict:
    q = {"id": pid(p.get("uuid"), set_id, p.get("letter"), p["name"])}
    for k in ("uuid", "name", "short_name", "have", "status", "notes"):
        if k in p:
            q[k] = p[k]
    if p.get("judges"):
        links = []
        for judge, v in p["judges"].items():
            for u in (v if isinstance(v, list) else [v]):
                url = u["url"] if isinstance(u, dict) else u
                link = {"judge": judge, "url": url}
                m = JUDGE_ID.get(judge)
                if m and (mm := m.search(url)):
                    link["id"] = mm.group(1)
                if isinstance(u, dict) and u.get("as_of"):
                    link["as_of"] = u["as_of"]
                links.append(link)
        q["judges"] = links
    return {k: q[k] for k in PROB_KEYS if k in q}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    stats = Counter()
    log: list[str] = []

    series = load_series()
    contests = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    reg_path = ROOT / "registry" / "non-mainline.yaml"
    reg = yaml.safe_load(reg_path.read_text())
    for c in reg["non_mainline_contests"]:
        contests[c["id"]] = ("non-mainline", c)

    pfiles = {f.stem: yaml.safe_load(f.read_text()) for f in sorted((ROOT / "problems").glob("*.yaml"))}
    set_of = {cid: sid for sid, members in SHARED.items() for cid in members}
    sets: dict[str, dict] = {}

    # ---- every contest with a problems block gets a set ----
    for cid, (_, c) in contests.items():
        pb = c.get("problems")
        if not pb and cid not in pfiles:
            continue
        pb = pb or {}
        set_id = set_of.get(cid, cid)
        s = sets.get(set_id)
        if s is None:
            s = sets[set_id] = {"id": set_id, "contests": [], "problems": [], "provenance": []}
        s["contests"].append({"contest": cid})
        for k in ("repo", "count", *HELD_KINDS, "counts", "notes"):
            if k in pb:
                if k in s and s[k] != pb[k]:
                    log.append(f"{set_id}: {k} differs between member contests: {s[k]!r} vs {pb[k]!r} ({cid}) — kept first")
                    stats["holdings differ in shared set"] += 1
                else:
                    s[k] = pb[k]
        if pb.get("source"):
            s["provenance"].append(pb["source"])
        c["problems"] = {"set": set_id}
        stats["contests with a set"] += 1

    # ---- per-problem files -> problems + letter maps ----
    for cid, doc in pfiles.items():
        set_id = set_of.get(cid, cid)
        s = sets[set_id]
        letters: dict[str, str] = {}
        for p in doc.get("problems") or []:
            q = convert_problem(p, set_id)
            existing = next((x for x in s["problems"] if x["id"] == q["id"]), None)
            if existing is None:
                s["problems"].append(q)
            else:
                for k, v in q.items():  # shared set: second file may add judges/have
                    existing.setdefault(k, v)
                stats["problem merged (shared set)"] += 1
            if p.get("letter"):
                letters[p["letter"]] = q["id"]
        entry = next(e for e in s["contests"] if e["contest"] == cid)
        if letters:
            entry["letters"] = letters
        if doc.get("letters") == "unknown":
            s["letters"] = "unknown"
        if doc.get("complete") is False:
            s["complete"] = False
        for src in doc.get("sources") or []:
            if src not in s["provenance"]:
                s["provenance"].append(src)
        if doc.get("notes"):
            s["notes"] = (s.get("notes", "") + "; " if s.get("notes") else "") + doc["notes"]
        stats["problem files converted"] += 1

    # ---- id uniqueness across all sets (a uuid shared across sets is fine: same id) ----
    owner = defaultdict(set)
    for s in sets.values():
        for p in s["problems"]:
            owner[p["id"]].add((p.get("uuid"), p["name"]))
    for i, names in owner.items():
        if len({u for u, _ in names}) > 1:
            log.append(f"id collision {i}: {names}")
            stats["ID COLLISION"] += 1

    # ---- write ----
    out = ROOT / "problemsets"
    if not args.dry_run:
        out.mkdir(exist_ok=True)
        for set_id, s in sorted(sets.items()):
            if not s["provenance"]:
                del s["provenance"]
            if not s["problems"]:
                del s["problems"]
                s["complete"] = False
            doc = {k: s[k] for k in SET_KEYS if k in s}
            (out / f"{set_id}.yaml").write_text(
                "# Problem set (DEFINITIONS.md, Problems): holdings, member contests with letter maps, problems.\n"
                + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
        for sid, doc in series.items():
            doc["contests"] = [normalise_contest(c) for c in doc["contests"]]
            dump_series(sid, doc, "migrate_problemsets.py (problem sets as objects, 2026-11-02)")
        head = "".join(l for l in reg_path.read_text().splitlines(True)[:2] if l.startswith("#"))
        reg["non_mainline_contests"] = [normalise_contest(c) for c in reg["non_mainline_contests"]]
        reg_path.write_text(head + yaml.dump(reg, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
        (ROOT / "reports" / "migrate-problemsets-2026-11-02.log").write_text("\n".join(log) + "\n")
    stats["sets"] = len(sets)
    stats["problems"] = sum(len(s.get("problems") or []) for s in sets.values())
    print(dict(sorted(stats.items())))
    for l in log[:20]:
        print("  ", l)
    return 1 if stats["ID COLLISION"] else 0


if __name__ == "__main__":
    sys.exit(main())
