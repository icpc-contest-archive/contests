#!/usr/bin/env python3
"""Apply the rulings of 2026-11-26 on problem sets whose member contests held different documents.

The rulings were made while sorting the problem archive's repos (project report
reports/problem-repo-rulings-2026-11-26.md). Comparing the statements problem by problem, not by
title, showed two kinds of mistakes in the sets:

  OWN SET    central-america-2008 was merged into latam-2008 on the rule that the Latin America
             regional has one set. Its own statement is a different set of seven problems, held two
             weeks earlier. It gets its own set and leaves latam-2008.
  LIGHT SET  the Northern Subregional of 2007 and of 2017 had a lighter version with the same
             titles: 7 of 11 problems differ in 2007, 5 of 12 in 2017. The contests that sat the
             lighter version get a set of their own, `north-russia-light-<year>`. Problems whose
             statements are the same keep one id in both sets; the others get new ids.
             Contests placed on the full set by a standings header alone get a note: a header shows
             titles only, so it cannot tell the two sets apart.
The third finding of that day, that mausa-2022's own set is the Division 1 list of south-na-2022 (the
contest ran on the south conference's contest), is not applied here: four of its problem ids are also
ids in another set, so it needs the shared-problems tool, not a plain merge.

Deterministic; a second run changes nothing.

  python3 tools/apply_problem_repo_rulings_2026_11_26.py [--dry-run]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import merge_problemsets as M  # noqa: E402
from catalogue import dump_series, load_series  # noqa: E402

TOOL = "apply_problem_repo_rulings_2026_11_26.py"
DAY = "2026-11-26"
SETS = ROOT / "problemsets"
HEADER_NOTE = ("its place on this set rests on a standings header, which shows only the problem titles; the "
               "lighter set of the same day has the same titles, so which of the two it sat is not confirmed")


def pid(setid: str, letter: str, name: str) -> str:
    return "p-" + hashlib.sha1(f"{setid}|{letter}|{name}".encode()).hexdigest()[:8]


def load(setid: str) -> dict | None:
    f = SETS / f"{setid}.yaml"
    return yaml.safe_load(f.read_text()) if f.exists() else None


def point(series: dict, changed: set, contest: str, setid: str) -> None:
    for sid, doc in series.items():
        for c in doc.get("contests") or []:
            if c.get("id") == contest:
                if (c.get("problems") or {}).get("set") != setid:
                    c.setdefault("problems", {})["set"] = setid
                    changed.add(sid)
                return
    raise SystemExit(f"{contest}: not in any series")


def own_set(out: dict, series: dict, changed: set) -> None:
    big = load("latam-2008")
    if not any(e["contest"] == "central-america-2008" for e in big["contests"]):
        return
    big["contests"] = [e for e in big["contests"] if e["contest"] != "central-america-2008"]
    big["aliases"] = [a for a in big.get("aliases") or [] if a != "central-america-2008"]
    big["provenance"].append(
        f"{DAY}: central-america-2008 leaves: its own statement (https://academicos.azc.uam.mx/franz/acm/problems2008.pdf) "
        "is a different set of seven problems, and the contest was held on 1-2 November 2008, two weeks before the "
        "South American contests of this set, whose cover lists Argentina, Bolivia, Brazil, Chile, Colombia, Peru and "
        f"Venezuela (ruling {DAY}, tools/{TOOL})")
    out["latam-2008"] = big
    names = ["Trip to Mars", "Binary Clock", "Chinese Checkers", "Cycles and more cycles", "Minimal Multiple",
             "Can I take it?", "Egyptian Multiplication"]
    rows = [{"id": pid("central-america-2008", str(i), n), "name": n} for i, n in enumerate(names, 1)]
    out["central-america-2008"] = {
        "id": "central-america-2008", "count": 7,
        "contests": [{"contest": "central-america-2008", "letters": {str(i): r["id"] for i, r in enumerate(rows, 1)}}],
        "problems": rows,
        "provenance": [
            "problem names and numbers read from our copy of https://academicos.azc.uam.mx/franz/acm/problems2008.pdf, "
            f"headed '13th México and Central America ACM International Collegiate Programming Contest 2008' ({DAY}, tools/{TOOL})",
            f"split from latam-2008, where the merge of 2026-11-12 had placed the contest (ruling {DAY})"]}
    point(series, changed, "central-america-2008", "central-america-2008")


def light_set(out: dict, series: dict, changed: set, year: int, name: str, movers: list[str], differ: str, url: str,
              doubtful: list[str], what: str) -> None:
    full_id, light_id = f"north-russia-{year}", f"north-russia-light-{year}"
    full = load(full_id)
    if load(light_id) or light_id in out:
        return
    letters = next(e["letters"] for e in full["contests"] if e["contest"] == full_id)
    rows_by_id = {p["id"]: p for p in full["problems"]}
    rows, lmap = [], {}
    for letter, old in letters.items():
        row = copy.deepcopy(rows_by_id[old])
        if letter in differ:
            row = {"id": pid(light_id, letter, row["name"]), "name": row["name"]}
        rows.append(row)
        lmap[letter] = row["id"]
    full["contests"] = [e for e in full["contests"] if e["contest"] not in movers]
    for e in full["contests"]:
        if e["contest"] in doubtful:
            e["note"] = HEADER_NOTE
    same = "".join(x for x in letters if x not in differ)
    full["provenance"] = [x for x in full["provenance"] if not any(x.startswith(f"{m} sat this set") for m in movers)]
    full["provenance"].append(
        f"{DAY}: {', '.join(movers)} leave{'s' if len(movers) == 1 else ''} for {light_id}: the statement they sat ({url}) "
        f"has the same titles but different problems for {', '.join(differ)} (ruling {DAY}, tools/{TOOL})")
    full["notes"] = "; ".join(x for x in [full.get("notes"),
                              f"a lighter set with the same titles exists for the same day: {light_id}"] if x)
    out[full_id] = full
    out[light_id] = {
        "id": light_id, "name": name, "count": len(rows),
        "contests": [{"contest": m, "letters": dict(lmap)} for m in sorted(movers)],
        "problems": rows,
        "provenance": [
            f"problem list read from our copy of {url}, {what} ({DAY}, tools/{TOOL})",
            f"compared statement by statement with {full_id}: {', '.join(same)} are word for word the same and keep that "
            f"set's problem ids; {', '.join(differ)} are different problems under the same titles and have ids of their own "
            f"(ruling {DAY})"],
        "notes": f"the lighter version of {full_id}: same titles, {len(differ)} of {len(rows)} problems differ"}
    for m in movers:
        point(series, changed, m, light_id)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    out: dict[str, dict] = {}
    series = load_series()
    changed: set[str] = set()
    trash: list[Path] = []
    own_set(out, series, changed)
    light_set(out, series, changed, 2007, "Northern Subregional 2007, light set", ["georgia-2007", "uzbekistan-2007"],
              "ACEFGHK", "https://nerc.itmo.ru/archive/2007/light/problems.pdf", ["kazakhstan-2007"],
              "headed 'Georgiya and Uzbekistan Subregional Contests, Batumi, Tashkent, October 28, 2007'")
    light_set(out, series, changed, 2017, "Northern Subregional 2017, light set", ["kazakhstan-2017"],
              "DEFHJ", "https://nerc.itmo.ru/archive/2017/kazakhstan/northern-lite-2017-statement.pdf",
              ["armenia-2017", "azerbaijan-2017", "georgia-2017", "taurida-2017", "urals-2017"],
              "which carries the full set's heading; only its file name says it is the lite one")
    for sid, doc in sorted(out.items()):
        print("set", sid, len(doc["problems"]), "problems,", [e["contest"] for e in doc["contests"]])
        if not a.dry_run:
            (SETS / f"{sid}.yaml").write_text(M.dump_set(doc))
    for sid in sorted(changed):
        print("series", sid)
        if not a.dry_run:
            dump_series(sid, series[sid], TOOL)
    for f in trash:
        print("remove", f.name)
        if not a.dry_run:
            f.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
