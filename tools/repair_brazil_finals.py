#!/usr/bin/env python3
"""Repair the problem sets of the Brazil finals 2005-2018 (ruling of 2026-11-12). Deterministic;
a second run changes nothing.

The Brazil final is a site of the Latin America regional. The Baekjoon import of 2026-11-02 put
two category pages on each final: the regional's ("South/Latin America Regional Contests <year>")
and the one of Brazil's first phase ("A Primeira Fase da Maratona de Programação <year>"), and
`mine_judge_links.py` then joined the two lists letter by letter into one set. This tool takes
the mixed set apart, using the two pages as parsed from the archive's captures (frozen in
data/import/brazil-boj-2026-11-12.json):

  first phase  the first-phase page moves to `brazil-first-phase-<year>` and its problems become
               that contest's set (added to the set when one exists, by letter). The catalogue
               had no first-phase contest for 2005-2007; they are added, without a date.
  regional     `brazil-<year>` joins `latam-<year>` with the letters its own regional page
               gives. Where no `latam` set existed (2005, 2006, 2014) one is made from what the
               other sites have, even when that is nothing: one regional, one set.
  ids          a row keeps its id on the side whose name it carried; ids that end up on the
               other side become aliases there, so old problem pages redirect.

Also moves the first-phase page of 2019 and 2023 (sets repaired earlier by merge_problemsets.py).

  python3 tools/repair_brazil_finals.py [--dry-run] [--trash DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import dump_series, load_series, load_sets, sort_sources  # noqa: E402
from add_contests_2026_11_12 import place  # noqa: E402
from merge_problemsets import Stop, dump_set, letters_of, norm  # noqa: E402

TOOL = "repair_brazil_finals.py"
DAY = "2026-11-12"
PAGES = ROOT / "data" / "import" / "brazil-boj-2026-11-12.json"
SITES = ("caribbean", "central-america", "mexico", "south-america", "south-america-north", "south-america-south")
BOJ = "https://www.acmicpc.net/problem/{}"


def new_pid(set_id: str, letter: str, name: str) -> str:
    return "p-" + hashlib.sha1(f"{set_id}|{letter or ''}|{name}".encode()).hexdigest()[:8]


def is_first_phase(note: str) -> bool:
    return "Primeira Fase" in note or "Maratona de Programação" in note


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--trash", help="move replaced set files here instead of deleting them")
    a = ap.parse_args()
    pages = json.loads(PAGES.read_text())
    sets = load_sets()
    series = load_series()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    write: dict[str, dict] = {}
    remove: list[str] = []
    touched: set[str] = set()
    rep: list[str] = []

    def page_of(cid: str, first_phase: bool) -> dict | None:
        return next((p for p in pages if p["contest"] == cid and is_first_phase(p["note"] or "") == first_phase), None)

    def move_page(cid: str, fp_cid: str) -> bool:
        """The first-phase Baekjoon page: from the final to the first phase."""
        pg = page_of(cid, True)
        src_sid, c = where[cid]
        src = next((s for s in c.get("sources") or [] if pg and s["url"] == pg["url"]), None)
        if src is None:
            return False
        c["sources"].remove(src)
        dst_sid, f = where[fp_cid]
        if not any(s["url"] == src["url"] for s in f.get("sources") or []):
            f.setdefault("sources", []).append(src)
            sort_sources(f)
        touched.update((src_sid, dst_sid))
        return True

    try:
        for year in range(2005, 2019):
            cid, fp_cid, lat_id = f"brazil-{year}", f"brazil-first-phase-{year}", f"latam-{year}"
            if cid not in sets or (where[cid][1].get("problems") or {}).get("set") != cid:
                continue  # repaired on an earlier run
            mixed = sets[cid]
            fp_pg, rg_pg = page_of(cid, True), page_of(cid, False)
            if not fp_pg or not fp_pg["rows"]:
                raise Stop(f"{cid}: no parsed first-phase page")
            rg_rows = (rg_pg or {}).get("rows") or []
            fp_ids, rg_ids = {r["id"] for r in fp_pg["rows"]}, {r["id"] for r in rg_rows}
            fp_names = {norm(r["name"]) for r in fp_pg["rows"]}
            by_letter = {letter: p for p in mixed["problems"] for pid_, letter in letters_of(mixed).items() if pid_ == p["id"]}
            lat = write.get(lat_id) or sets.get(lat_id)
            lat_links = {(j["judge"], j["url"]) for p in (lat or {}).get("problems") or [] for j in p.get("judges") or []}
            lat_boj = {j.get("id") for p in (lat or {}).get("problems") or [] for j in p.get("judges") or [] if j["judge"] == "baekjoon"}
            for p in mixed["problems"]:
                for j in p.get("judges") or []:
                    known = j.get("id") in fp_ids | rg_ids | lat_boj if j["judge"] == "baekjoon" else (j["judge"], j["url"]) in lat_links
                    if not known:
                        raise Stop(f"{cid}: {p['name']!r} has a link that is neither contest's: {j['url']}")
            as_of = {j["id"]: j.get("as_of") for p in mixed["problems"] for j in p.get("judges") or [] if j["judge"] == "baekjoon"}

            def boj_link(bid: str) -> dict:
                link = {"judge": "baekjoon", "url": BOJ.format(bid), "id": bid}
                if as_of.get(bid):
                    link["as_of"] = as_of[bid]
                return link

            # ---- first phase
            if fp_cid not in where:
                fp_sid = "brazil-first-phase"
                c = {"id": fp_cid, "season": year + 1, "name": "South America/Brazil First Phase", "parent": cid,
                     "provenance": [f"added {DAY}: Baekjoon mirrored this contest's problems as “{fp_pg['note']}”; the page had been "
                                    f"filed under {cid} (tools/{TOOL}). No date or site found yet"]}
                if f"brazil-first-phase-{year + 1}" in where or year + 1 in (2006, 2007):
                    c["next"] = f"brazil-first-phase-{year + 1}"
                series[fp_sid]["contests"].append(c)
                series[fp_sid]["contests"].sort(key=lambda x: x["id"])
                where[fp_cid] = (fp_sid, c)
                touched.add(fp_sid)
                rep.append(f"- added contest `{fp_cid}` (no date)")
            fp_doc = write.get(fp_cid) or sets.get(fp_cid)
            moved_ids: dict[str, str] = {}  # mixed row id -> the id it lives on now
            if fp_doc and fp_doc.get("problems"):
                have = {letter: next(p for p in fp_doc["problems"] if p["id"] == pid_) for pid_, letter in letters_of(fp_doc).items()}
                for r in fp_pg["rows"]:
                    row = have.get(r["letter"])
                    if row is None:
                        raise Stop(f"{fp_cid}: its set has no problem {r['letter']}")
                    if not any(j["url"] == BOJ.format(r["id"]) for j in row.get("judges") or []):
                        row.setdefault("judges", []).append(boj_link(r["id"]))
                    if norm(r["name"]) != norm(row["name"]):
                        note = f"titled “{r['name']}” on Baekjoon"
                        if note not in (row.get("notes") or ""):
                            row["notes"] = "; ".join(x for x in (row.get("notes"), note) if x)
                    m = by_letter.get(r["letter"])
                    if m and norm(m["name"]) == norm(r["name"]) and m["id"] != row["id"]:
                        row["aliases"] = sorted(set(row.get("aliases") or []) | {m["id"]})
                        moved_ids[m["id"]] = row["id"]
                line = f"{DAY}: Baekjoon links added from “{fp_pg['note']}”, which had been filed under {cid} (tools/{TOOL})"
                fp_doc["provenance"] = [x for x in fp_doc.get("provenance") or [] if x != line] + [line]
            else:
                rows, letters = [], {}
                for r in fp_pg["rows"]:
                    m = by_letter.get(r["letter"])
                    keep = m["id"] if m and norm(m["name"]) == norm(r["name"]) else new_pid(fp_cid, r["letter"], r["name"])
                    if m and keep == m["id"]:
                        moved_ids[m["id"]] = keep
                    rows.append({"id": keep, "name": r["name"], "judges": [boj_link(r["id"])]})
                    letters[r["letter"]] = keep
                fp_doc = {"id": fp_cid, "complete": False, "contests": [{"contest": fp_cid, "letters": letters}], "problems": rows,
                          "provenance": [f"Baekjoon category “{fp_pg['note']}” ({fp_pg['url']}), from the archived capture",
                                         f"{DAY}: split from the set filed as {cid}, which mixed these problems with the regional's "
                                         f"(tools/{TOOL})"]}
            write[fp_cid] = fp_doc
            fpc = where[fp_cid][1]
            if (fpc.get("problems") or {}).get("set") != fp_cid:
                fpc.setdefault("problems", {})["set"] = fp_cid
                touched.add(where[fp_cid][0])
            move_page(cid, fp_cid)

            # ---- regional
            if lat is None:
                others = [f"{s}-{year}" for s in SITES if f"{s}-{year}" in sets and f"{s}-{year}" in where]
                listed = [o for o in others if sets[o].get("problems")]
                if len(listed) > 1 or any(k in sets[o] for o in others for k in ("count", "repo", "statement", "data", "solutions", "package")):
                    raise Stop(f"{lat_id}: more than one site has a list, or holdings are recorded")
                base = sets[listed[0]] if listed else {}
                lat = {"id": lat_id, "name": f"Latin America regional {year}", "aliases": sorted(others), "complete": False,
                       "contests": sorted(([e for e in base.get("contests") or []] + [{"contest": o} for o in others if o not in listed]),
                                          key=lambda e: e["contest"])}
                if base.get("letters"):
                    lat["letters"] = base["letters"]
                if base.get("problems"):
                    lat["problems"] = base["problems"]
                lat["provenance"] = list(base.get("provenance") or []) + [
                    f"made {DAY} from {', '.join(others)}: one problem set for every site of the Latin America regional (tools/{TOOL})"]
                remove += others
                for o in others:
                    for e in sets[o]["contests"]:
                        osid, oc = where[e["contest"]]
                        oc["problems"]["set"] = lat_id
                        touched.add(osid)
            letters = {}
            by_boj = {j.get("id"): p["id"] for p in lat.get("problems") or [] for j in p.get("judges") or [] if j["judge"] == "baekjoon"}
            lat_let = letters_of(lat)
            for r in rg_rows:
                pid_ = by_boj.get(r["id"])
                if pid_ and r["letter"]:
                    if lat_let.get(pid_, r["letter"]) != r["letter"] or pid_ in letters.values():
                        letters = {}
                        rep.append(f"- `{cid}`: its regional page letters disagree with the set's; no letters recorded for it")
                        break
                    letters[r["letter"]] = pid_
            by_name = {norm(p["name"]): p for p in lat.get("problems") or []}
            n_alias = 0
            for p in mixed["problems"]:
                if p["id"] in moved_ids:
                    continue
                target = by_name.get(norm(p["name"]))
                if target is None:
                    target = next((q for q in lat.get("problems") or [] for j in p.get("judges") or []
                                   if any(x["url"] == j["url"] for x in q.get("judges") or [])), None) if norm(p["name"]) not in fp_names else None
                if target is not None and target["id"] != p["id"]:
                    target["aliases"] = sorted(set(target.get("aliases") or []) | {p["id"]})
                    n_alias += 1
            entry = {"contest": cid, **({"letters": letters} if letters else {})}
            lat["contests"] = sorted([e for e in lat["contests"] if e["contest"] != cid] + [entry], key=lambda e: e["contest"])
            if letters and lat.get("letters") == "unknown":
                del lat["letters"]
            lat["aliases"] = sorted(set(lat.get("aliases") or []) | {cid})
            line = (f"{DAY}: {cid} joins: it is a site of this regional; the set filed under it mixed the regional's problems with "
                    f"those of {fp_cid} (tools/{TOOL})")
            lat["provenance"] = [x for x in lat.get("provenance") or [] if x != line] + [line]
            write[lat_id] = lat
            where[cid][1]["problems"]["set"] = lat_id
            touched.add(where[cid][0])
            remove.append(cid)
            rep.append(f"| {year} | {len(fp_pg['rows'])} problems to `{fp_cid}` | `{cid}` on `{lat_id}`"
                       + (f", letters {''.join(sorted(letters))}" if letters else ", no letters") + f" | {len(moved_ids)} ids kept, {n_alias} aliased |")
        for year in (2019, 2023):
            if move_page(f"brazil-{year}", f"brazil-first-phase-{year}"):
                rep.append(f"- first-phase Baekjoon page of {year} moved from `brazil-{year}` to `brazil-first-phase-{year}`")
    except Stop as e:
        print(f"stopped, nothing written: {e}")
        return 1

    if not write and not touched:
        print("nothing to do")
        return 0
    print(f"{len(remove)} sets retired, {len(write)} sets written, {len(touched)} series files touched")
    if a.dry_run:
        print("\n".join(rep))
        return 0
    pdir = ROOT / "problemsets"
    for sid_, doc in write.items():
        (pdir / f"{sid_}.yaml").write_text(dump_set(doc))
    trash = Path(a.trash) if a.trash else None
    if trash:
        trash.mkdir(parents=True, exist_ok=True)
    for sid_ in dict.fromkeys(remove):
        f = pdir / f"{sid_}.yaml"
        if trash:
            shutil.move(str(f), str(trash / f.name))
        else:
            f.unlink()
    for ssid in sorted(touched):
        if ssid == "brazil-first-phase":  # entries that gained sources / problems: keys back in order
            series[ssid]["contests"] = [place(c) for c in series[ssid]["contests"]]
        dump_series(ssid, series[ssid], TOOL)
    table = [x for x in rep if x.startswith("|")]
    other = [x for x in rep if not x.startswith("|")]
    (ROOT / "reports" / f"brazil-finals-repair-{DAY}.md").write_text("\n".join(
        [f"# Brazil finals 2005-2018 repaired — {DAY}", "",
         f"`tools/{TOOL}`: the sets filed under the Brazil finals mixed the regional's problems with the first phase's "
         "(two Baekjoon pages joined letter by letter). Each is split: the first phase's problems and Baekjoon page go to "
         "`brazil-first-phase-<year>`, and the final uses the regional's set.", "",
         "| year | first phase | final | problem ids |", "| --- | --- | --- | --- |", *table, "", *other, ""]))
    print(f"wrote reports/brazil-finals-repair-{DAY}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
