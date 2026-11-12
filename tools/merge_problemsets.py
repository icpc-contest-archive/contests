#!/usr/bin/env python3
"""Merge problem sets that are one set (ruling of 2026-11-12). Deterministic; a second run changes nothing.

A problem set is its own object so that several contests can share one (DEFINITIONS.md, Problems).
The imports of 2026-11-01/02 nevertheless made one set per contest, so the Latin America regional,
which every site sits with the same problems, appeared as up to six sets a year. This tool merges
the sets in PLAN below into shared sets:

  LATAM   one `latam-<year>` per year for the sites of the Latin America regional whose lists are
          the same list (identical, or one contained in the other with the same letters);
  JOINED  sites of that regional with no list of their own join the year's set, on the rule that
          the regional has one problem set (no letters are claimed for them);
  PAIRS   two North America contests that sat the same set;
  REFILED a set that was filed under the wrong contest: the Brazil final (a site of the regional)
          carried the list of Brazil's first phase. Its rows go to the first-phase set, the final
          joins the year's `latam` set.

What a merge keeps:
  - one row per problem (matched by normalised name). The id kept is the one with a uuid, else the
    id of the first member in alphabetical order; every other id becomes an `aliases` entry, so old
    problem pages redirect. Judge links, `have`, short names and notes are united.
  - each contest keeps its own letter map, rewritten to the kept ids.
  - the merged set's `aliases` are the ids of the sets it replaces, so old set pages redirect.
  - holdings (`count`, `statement`, ...) must agree between members that state them, else the
    tool stops.
Every merge is checked against the data before anything is written; a plan entry that no longer
matches (lists differ, letters disagree) stops the run.

  python3 tools/merge_problemsets.py [--dry-run] [--trash DIR]

--trash DIR moves the replaced files there instead of deleting them (for mounts that refuse unlink).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import Dumper, dump_series, load_series, load_sets  # noqa: E402

TOOL = "merge_problemsets.py"
DAY = "2026-11-12"
SET_HEADER = "# Problem set (DEFINITIONS.md, Problems): holdings, member contests with letter maps, problems.\n"
HELD_KINDS = ("statement", "data", "solutions", "package")
SET_KEYS = ("id", "name", "aliases", "repo", "count", "complete", "letters", *HELD_KINDS, "counts",
            "contests", "problems", "provenance", "notes")
PROB_KEYS = ("id", "uuid", "aliases", "name", "short_name", "have", "status", "judges", "notes")
HAVE = ("statement", "data", "input_validator", "output_validator", "solutions", "package")

C, CA, MX, SN, SS, BR = "caribbean", "central-america", "mexico", "south-america-north", "south-america-south", "brazil"
# year: (sets with a list, sets without one that join)
LATAM = {
    2007: (["central-america", "south-america"], []),
    2008: ([CA, SN, SS], []),
    2009: ([C, CA, SN, SS], []),
    2010: ([C, CA, SN, SS], []),
    2011: ([C, CA, SN, SS], []),
    2012: ([C, CA, SN, SS], []),
    2013: ([C, CA, SN, SS], []),
    2015: ([C, CA, SN, SS], []),
    2016: ([C, CA, SN, SS], []),
    2017: ([C, CA, SN, SS], []),
    2018: ([C, CA, SN, SS], []),
    2019: ([C, CA, MX, SN, SS], []),
    2020: ([BR, C, CA, MX, SN, SS], []),
    2021: ([BR, C, CA, MX, SN, SS], []),
    2022: ([BR, C, CA, MX, SN, SS], []),
    2023: ([C, CA, MX], [SN, SS]),
    2024: ([C, CA, MX], [BR, SN, SS]),
    2025: ([BR, C, CA, MX, SN, SS], []),
}
PAIRS = {  # new id: (name, members)
    "east-na-ecna-2025": ("North America East Division and East Central regional 2025", ["east-na-2025", "ecna-2025"]),
    "scusa-seusa-2020": ("North America South Central and Southeast regionals 2020", ["scusa-2020", "seusa-2020"]),
}
REFILED = {  # misfiled set: (the set it really is, the set its contest really used)
    "brazil-2019": ("brazil-first-phase-2019", "latam-2019"),
    "brazil-2023": ("brazil-first-phase-2023", "latam-2023"),
}


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").casefold()
    return "".join(ch for ch in t if ch.isalnum() and unicodedata.category(ch) != "Mn")


def dump_set(s: dict) -> str:
    doc = {k: s[k] for k in SET_KEYS if k in s}
    doc.update({k: v for k, v in s.items() if k not in doc})
    if "problems" in doc:
        doc["problems"] = [{**{k: p[k] for k in PROB_KEYS if k in p}, **{k: v for k, v in p.items() if k not in PROB_KEYS}}
                           for p in doc["problems"]]
    return SET_HEADER + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)


class Stop(Exception):
    pass


def letters_of(doc: dict) -> dict[str, str]:
    """{problem id: letter} over every contest of a set; a problem with two letters stops the run."""
    out: dict[str, str] = {}
    for e in doc["contests"]:
        for letter, pid in (e.get("letters") or {}).items():
            if out.setdefault(pid, letter) != letter:
                raise Stop(f"{doc['id']}: {pid} has letters {out[pid]} and {letter}")
    return out


def unite_rows(cands: list[dict], drop_links: set = frozenset()) -> dict:
    """One row from the rows of the same problem (first = the member that comes first)."""
    uuids = {p["uuid"] for p in cands if p.get("uuid")}
    if len(uuids) > 1:
        raise Stop(f"{cands[0]['name']!r}: two uuids {sorted(uuids)}")
    keep = next((p for p in cands if p.get("uuid")), cands[0])
    row: dict = {"id": keep["id"]}
    if uuids:
        row["uuid"] = uuids.pop()
    aliases = ({p["id"] for p in cands} | {a for p in cands for a in p.get("aliases") or []}) - {keep["id"]}
    if aliases:
        row["aliases"] = sorted(aliases)
    row["name"] = keep["name"]
    shorts = {p["short_name"] for p in cands if p.get("short_name")}
    if len(shorts) > 1:
        raise Stop(f"{keep['name']!r}: two short names {sorted(shorts)}")
    if shorts:
        row["short_name"] = shorts.pop()
    have = {h for p in cands for h in p.get("have") or []}
    if have:
        row["have"] = [h for h in HAVE if h in have]
    if any(p.get("status") for p in cands):
        row["status"] = next(p["status"] for p in cands if p.get("status"))
    judges: list[dict] = []
    for p in cands:
        for j in p.get("judges") or []:
            if (j["judge"], j["url"]) in drop_links:
                continue
            old = next((x for x in judges if (x["judge"], x["url"]) == (j["judge"], j["url"])), None)
            if old is None:
                judges.append(dict(j))
            else:
                old.update({k: v for k, v in j.items() if k not in old})
    if judges:
        first = list(dict.fromkeys(j["judge"] for j in judges))
        row["judges"] = sorted(judges, key=lambda j: first.index(j["judge"]))  # stable: a judge's links stay together
    notes = []
    for p in cands:
        if p.get("notes") and p["notes"] not in notes:
            notes.append(p["notes"])
    if notes:
        row["notes"] = "; ".join(notes)
    return row


def merge(target: str, name: str, members: list[str], joined: list[str], sets: dict, why: str) -> tuple[dict, dict, list[str]]:
    """The merged document, {(member, old problem id): kept id}, and remarks for the report."""
    docs = {m: sets[m] for m in members}
    remarks: list[str] = []
    for m in joined:
        d = sets[m]
        if d.get("problems") or any(k in d for k in ("count", "repo", "counts", *HELD_KINDS)):
            raise Stop(f"{m}: expected an empty placeholder")
    names = {m: [norm(p["name"]) for p in d.get("problems") or []] for m, d in docs.items()}
    for m, ns in names.items():
        if not ns or len(ns) != len(set(ns)):
            raise Stop(f"{m}: no list, or two problems with one name")
    big = max(members, key=lambda m: (len(names[m]), [-ord(ch) for ch in m]))  # longest; ties: first in the alphabet
    for m in members:
        if not set(names[m]) <= set(names[big]):
            raise Stop(f"{m}: its list is not contained in {big}'s")
    lets = {m: letters_of(d) for m, d in docs.items()}
    rows, idmap = [], {}
    for key in names[big]:
        cands = [(m, p) for m in members for p in docs[m]["problems"] if norm(p["name"]) == key]
        seen = {lets[m][p["id"]] for m, p in cands if p["id"] in lets[m]}
        if len(seen) > 1:
            raise Stop(f"{target}: {cands[0][1]['name']!r} has letters {sorted(seen)} across members")
        per_judge: dict[str, set] = {}
        for m, p in cands:
            for j in p.get("judges") or []:
                per_judge.setdefault(j["judge"], set()).add((m, j["url"]))
        for judge, pairs in per_judge.items():
            by_member: dict[str, set] = {}
            for m, url in pairs:
                by_member.setdefault(m, set()).add(url)
            if len({frozenset(v) for v in by_member.values()}) > 1:
                remarks.append(judge)
        row = unite_rows([p for _m, p in cands])
        rows.append(row)
        for m, p in cands:
            idmap[(m, p["id"])] = row["id"]
    out: dict = {"id": target, "name": name, "aliases": sorted(members + joined)}
    for k in ("repo", "count", "counts", *HELD_KINDS):
        vals = {json.dumps(d[k], sort_keys=True) for d in docs.values() if k in d}
        if len(vals) > 1:
            raise Stop(f"{target}: members disagree on {k}: {sorted(vals)}")
        if vals:
            out[k] = json.loads(vals.pop())
    if "count" in out and out["count"] != len(rows):
        raise Stop(f"{target}: count {out['count']} but {len(rows)} problems after the merge")
    if "count" not in out:
        if any(d.get("complete") is not False for d in docs.values()):
            raise Stop(f"{target}: a member has neither a count nor complete: false")
        out["complete"] = False
    entries = []
    for m in members:
        for e in docs[m]["contests"]:
            n = {"contest": e["contest"]}
            if e.get("letters"):
                n["letters"] = {letter: idmap[(m, pid)] for letter, pid in e["letters"].items()}
            entries.append(n)
    for m in joined:
        entries += [{"contest": e["contest"]} for e in sets[m]["contests"]]
    out["contests"] = sorted(entries, key=lambda e: e["contest"])
    if not any(e.get("letters") for e in out["contests"]):
        out["letters"] = "unknown"
    out["problems"] = rows
    prov: list[str] = []
    for m in members:
        prov += [x for x in docs[m].get("provenance") or [] if x not in prov]
    line = f"merged {DAY} from {', '.join(members)}: {why} (tools/{TOOL})"
    if joined:
        line += f"; {', '.join(joined)} had no list and joined on the rule that the regional has one problem set"
    out["provenance"] = prov + [line]
    notes = []
    for m in members + joined:
        if sets[m].get("notes") and sets[m]["notes"] not in notes:
            notes.append(sets[m]["notes"])
    if notes:
        out["notes"] = "; ".join(notes)
    return out, idmap, remarks


def refile(wrong: dict, real: dict, regional_links: set) -> list[str]:
    """Move the rows of a misfiled set into the set they belong to (in place). Links that the
    regional's own rows carry were paired to these rows by letter and are dropped."""
    wn = {norm(p["name"]): p for p in wrong["problems"]}
    rn = [norm(p["name"]) for p in real["problems"]]
    if sorted(wn) != sorted(rn):
        raise Stop(f"{wrong['id']} and {real['id']} do not list the same problems")
    wl, rl = letters_of(wrong), letters_of(real)
    dropped = 0
    for i, p in enumerate(real["problems"]):
        w = wn[norm(p["name"])]
        if wl.get(w["id"]) and rl.get(p["id"]) and wl[w["id"]] != rl[p["id"]]:
            raise Stop(f"{real['id']}: {p['name']!r} is {rl[p['id']]} here and {wl[w['id']]} in {wrong['id']}")
        dropped += sum(1 for j in w.get("judges") or [] if (j["judge"], j["url"]) in regional_links)
        real["problems"][i] = unite_rows([p, w], drop_links=regional_links)
    line = (f"{DAY}: rows, ids and judge links taken over from the set filed as {wrong['id']}, which was this list, "
            f"not the regional's (tools/{TOOL})")
    real["provenance"] = [x for x in real.get("provenance") or [] if x != line] + [line]
    return [f"{dropped} judge links that belong to the regional's problems (paired to these rows by letter) dropped"] if dropped else []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--trash", help="move replaced set files here instead of deleting them")
    a = ap.parse_args()
    sets = load_sets()
    series = load_series()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    pdir = ROOT / "problemsets"
    write: dict[str, dict] = {}
    remove: list[str] = []
    relink: dict[str, str] = {}  # contest id -> set id
    report: list[str] = []
    n_alias = 0

    plan: list[tuple[str, str, list[str], list[str], str]] = []
    for year, (with_list, without) in LATAM.items():
        plan.append((f"latam-{year}", f"Latin America regional {year}", [f"{s}-{year}" for s in with_list],
                     [f"{s}-{year}" for s in without], "one problem set for every site of the Latin America regional"))
    for target, (name, members) in PAIRS.items():
        plan.append((target, name, members, [], "the two contests sat the same problem set"))

    try:
        for target, name, members, joined, why in plan:
            gone = [m for m in members + joined if m not in sets]
            if target in sets and len(gone) == len(members + joined):
                continue  # done on an earlier run
            if gone or target in sets:
                raise Stop(f"{target}: half merged (missing {gone}, target exists: {target in sets})")
            doc, _idmap, remarks = merge(target, name, sorted(members), sorted(joined), sets, why)
            write[target] = doc
            remove += members + joined
            for e in doc["contests"]:
                relink[e["contest"]] = target
            n_alias += sum(len(p.get("aliases") or []) for p in doc["problems"])
            remark = "; ".join(f"{remarks.count(j)} problems have different {j} links per member, all kept"
                               for j in dict.fromkeys(remarks))
            report.append(f"| `{target}` | {len(doc['problems'])} | {', '.join(e['contest'] for e in doc['contests'])} | {remark} |")
        refiled_report: list[str] = []
        for wrong_id, (real_id, used_id) in REFILED.items():
            if wrong_id not in sets:
                continue
            used = write.get(used_id) or sets.get(used_id)
            real = sets.get(real_id)
            if used is None or real is None:
                raise Stop(f"{wrong_id}: {real_id} or {used_id} is missing")
            regional_links = {(j["judge"], j["url"]) for p in used["problems"] for j in p.get("judges") or []}
            remarks = refile(sets[wrong_id], real, regional_links)
            write[real_id] = real
            cid = sets[wrong_id]["contests"][0]["contest"]
            if [e["contest"] for e in sets[wrong_id]["contests"]] != [cid]:
                raise Stop(f"{wrong_id}: more than one contest")
            used["contests"] = sorted(used["contests"] + [{"contest": cid}], key=lambda e: e["contest"])
            used["aliases"] = sorted(set(used.get("aliases") or []) | {wrong_id})
            line = (f"{DAY}: {cid} joins: it is a site of this regional; the set filed under it was the list of "
                    f"{real_id} (tools/{TOOL})")
            used["provenance"] = [x for x in used.get("provenance") or [] if x != line] + [line]
            write[used_id] = used
            relink[cid] = used_id
            remove.append(wrong_id)
            n_alias += len(real["problems"])
            refiled_report.append(f"- `{wrong_id}` held the list of `{real_id}`; its rows moved there, and {cid} now uses "
                                  f"`{used_id}`" + (f" ({'; '.join(remarks)})" if remarks else ""))
    except Stop as e:
        print(f"stopped, nothing written: {e}")
        return 1

    if not write:
        print("nothing to do")
        return 0
    touched: set[str] = set()
    for cid, sid_ in relink.items():
        ssid, c = where[cid]
        if (c.get("problems") or {}).get("set") != sid_:
            c.setdefault("problems", {})["set"] = sid_
            touched.add(ssid)
    n_new = sum(1 for t in write if t not in sets)
    print(f"{len(remove)} sets replaced by {n_new} shared sets ({len(write) - n_new} existing sets updated); "
          f"{len(relink)} contests relinked in {len(touched)} series files; {n_alias} problem ids became aliases")
    if a.dry_run:
        return 0
    for sid_, doc in write.items():
        (pdir / f"{sid_}.yaml").write_text(dump_set(doc))
    trash = Path(a.trash) if a.trash else None
    if trash:
        trash.mkdir(parents=True, exist_ok=True)
    for sid_ in remove:
        f = pdir / f"{sid_}.yaml"
        if trash:
            shutil.move(str(f), str(trash / f.name))
        else:
            f.unlink()
    for ssid in sorted(touched):
        dump_series(ssid, series[ssid], TOOL)
    rep = [f"# Problem sets merged — {DAY}", "",
           f"`tools/{TOOL}`: {len(remove)} sets replaced by {n_new} shared sets; {len(relink)} contests relinked; "
           f"{n_alias} problem ids kept as aliases, so old problem and set pages redirect.", "",
           "## Shared sets", "", "| set | problems | used by | remarks |", "| --- | --- | --- | --- |", *report, "",
           "## Refiled", "", *refiled_report, ""]
    (ROOT / "reports" / f"problemset-merge-{DAY}.md").write_text("\n".join(rep))
    print(f"wrote {len(write)} set files, removed {len(remove)}, reports/problemset-merge-{DAY}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
