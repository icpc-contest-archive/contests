#!/usr/bin/env python3
"""Give one problem id to problems that several sets share (ruling of 2026-11-26). A second run changes nothing.

Two rows in different sets are the same problem when they point at the same page of an online judge
(same judge and judge id) or carry the same uuid. The sets stay separate, each with its own letters
and its own title for the problem; only the problem id becomes one, so that the problem's page shows
every contest that used it.

  kept id   the row with a uuid, else the row of the earliest contest, else the first set in the alphabet
  aliases   every id replaced, on every row of the problem (old problem pages redirect)
  judges    every row gets the union of the links, so the rows agree
  titles    each row keeps its set's title and lists the others under `other_names`
  uuid, short_name   copied to the rows that lack them when the problem has exactly one

Not unified, and listed in the report instead:
  - rows whose titles differ and that agree on one judge only (one wrong link would join two problems);
  - a group that would join two problems of one set, or two uuids;
  - rows of one season with the same title and no judge in common.

  python3 tools/unify_shared_problems.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import merge_problemsets as M  # noqa: E402
from catalogue import load_series, load_sets  # noqa: E402

REPORT = ROOT / "data" / "shared-problems-2026-11-26.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sets = load_sets()
    contests = {c["id"]: c for d in load_series().values() for c in d["contests"]}

    def first_date(sid: str) -> str:
        ds = [str(contests[e["contest"]].get("date") or "") for e in sets[sid]["contests"] if e["contest"] in contests]
        return min([d for d in ds if d] or ["9999"])

    def seasons(sid: str) -> set:
        return {contests[e["contest"]].get("season") for e in sets[sid]["contests"] if e["contest"] in contests} - {None}

    rows = [(sid, p) for sid, d in sorted(sets.items()) for p in d.get("problems") or []]
    idx = {(sid, p["id"]): n for n, (sid, p) in enumerate(rows)}
    assert len(idx) == len(rows)
    # pairwise evidence between rows of different sets
    by_key: dict[tuple, list[int]] = defaultdict(list)
    for n, (sid, p) in enumerate(rows):
        if p.get("uuid"):
            by_key[("uuid", p["uuid"].lower())].append(n)
        for j in p.get("judges") or []:
            by_key[(j["judge"], str(j.get("id") or j["url"]))].append(n)
    ev: dict[tuple[int, int], set] = defaultdict(set)
    for key, ns in by_key.items():
        for i in range(len(ns)):
            for k in range(i + 1, len(ns)):
                x, y = ns[i], ns[k]
                if rows[x][0] != rows[y][0]:
                    ev[(x, y)].add(key[0])
    parent = list(range(len(rows)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    weak = []
    for (x, y), judges in sorted(ev.items()):
        same_name = M.norm(rows[x][1]["name"]) == M.norm(rows[y][1]["name"])
        same_id = rows[x][1]["id"] == rows[y][1]["id"]
        if same_name or same_id or "uuid" in judges or len(judges) >= 2:
            parent[find(x)] = find(y)
        else:
            weak.append({"a": [rows[x][0], rows[x][1]["id"], rows[x][1]["name"]], "b": [rows[y][0], rows[y][1]["id"], rows[y][1]["name"]],
                         "judge": sorted(judges)})
    comps: dict[int, list[int]] = defaultdict(list)
    for n in range(len(rows)):
        comps[find(n)].append(n)
    # rows that already share an id belong together whatever their links say
    by_id: dict[str, list[int]] = defaultdict(list)
    for n, (_s, p) in enumerate(rows):
        by_id[p["id"]].append(n)
    for ns in by_id.values():
        for n in ns[1:]:
            parent[find(n)] = find(ns[0])
    comps = defaultdict(list)
    for n in range(len(rows)):
        comps[find(n)].append(n)

    unified, refused, changed_sets = [], [], set()
    for ns in comps.values():
        if len(ns) < 2:
            continue
        members = [rows[n] for n in ns]
        per_set = defaultdict(set)
        for sid, p in members:
            per_set[sid].add(p["id"])
        uuids = {p["uuid"].lower() for _s, p in members if p.get("uuid")}
        brief = [[sid, p["id"], p["name"]] for sid, p in members]
        if any(len(v) > 1 for v in per_set.values()):
            refused.append({"why": "two problems of one set", "rows": brief})
            continue
        if len(uuids) > 1:
            refused.append({"why": "two uuids", "rows": brief})
            continue
        keep = min(members, key=lambda m: (0 if m[1].get("uuid") else 1, first_date(m[0]), m[0]))[1]["id"]
        ids = {p["id"] for _s, p in members}
        aliases = sorted((ids | {x for _s, p in members for x in p.get("aliases") or []}) - {keep})
        names = list(dict.fromkeys(p["name"] for _s, p in members))
        others_all = set(names) | {o for _s, p in members for o in p.get("other_names") or []}
        judges: list[dict] = []
        for _s, p in sorted(members, key=lambda m: (first_date(m[0]), m[0])):
            for j in p.get("judges") or []:
                old = next((x for x in judges if (x["judge"], x["url"]) == (j["judge"], j["url"])), None)
                if old is None:
                    judges.append(dict(j))
                else:
                    old.update({k: v for k, v in j.items() if k not in old})
        order = list(dict.fromkeys(j["judge"] for j in judges))
        judges.sort(key=lambda j: order.index(j["judge"]))
        shorts = {p["short_name"] for _s, p in members if p.get("short_name")}
        was = len(ids) > 1
        for sid, p in members:
            new = dict(p)
            new["id"] = keep
            if uuids:
                new["uuid"] = next(q["uuid"] for _s, q in members if q.get("uuid"))
            if aliases:
                new["aliases"] = aliases
            others = sorted(others_all - {p["name"]})
            if others:
                new["other_names"] = others
            if len(shorts) == 1:
                new["short_name"] = next(iter(shorts))
            if judges:
                new["judges"] = [dict(j) for j in judges]
            if new != p:
                old_id = p["id"]
                p.clear()
                p.update(new)
                changed_sets.add(sid)
        if was:
            unified.append({"id": keep, "replaced": aliases, "titles": names, "sets": sorted(per_set)})
    # letter maps (a contest's own, and each division's) follow the ids
    for sid, d in sets.items():
        now = {x: p["id"] for p in d.get("problems") or [] for x in p.get("aliases") or []}
        live = {p["id"] for p in d.get("problems") or []}
        for e in d["contests"]:
            for lm in [e.get("letters")] + list((e.get("divisions") or {}).values()):
                if isinstance(lm, dict):
                    for L, v in lm.items():
                        if v not in live and v in now:
                            lm[L] = now[v]
                            changed_sets.add(sid)
    # same title, same season, nothing in common
    final = {(sid, p["id"]) for sid, d in sets.items() for p in d.get("problems") or []}
    by_name: dict[str, list] = defaultdict(list)
    for sid, d in sets.items():
        for p in d.get("problems") or []:
            if len(M.norm(p["name"])) >= 6:
                by_name[M.norm(p["name"])].append((sid, p))
    name_only = []
    for key, lst in sorted(by_name.items()):
        for i in range(len(lst)):
            for k in range(i + 1, len(lst)):
                (s1, p1), (s2, p2) = lst[i], lst[k]
                if s1 != s2 and p1["id"] != p2["id"] and seasons(s1) & seasons(s2):
                    name_only.append([p1["name"], s1, p1["id"], s2, p2["id"]])
    report = {"generated": "2026-11-26", "about": "Decision 37: one problem id for problems that several sets share (tools/unify_shared_problems.py).",
              "unified": sorted(unified, key=lambda u: u["id"]), "not_unified_one_judge_and_titles_differ": weak,
              "not_unified_conflict": refused, "same_title_same_season_no_judge_in_common": name_only}
    print(f"{len(unified)} problems unified ({sum(len(u['replaced']) for u in unified)} ids replaced) in {len(changed_sets)} sets; "
          f"{sum(1 for u in unified if len(u['titles']) > 1)} with more than one title; {len(weak)} pairs on one judge with different titles, "
          f"{len(refused)} conflicts, {len(name_only)} same-title pairs left alone")
    if a.dry_run:
        json.dump(report, open("/tmp/shared-problems-dry.json", "w"), indent=1, ensure_ascii=False)
        return 0
    if changed_sets:
        for sid in sorted(changed_sets):
            (ROOT / "problemsets" / f"{sid}.yaml").write_text(M.dump_set(sets[sid]), encoding="utf-8")
        if unified:
            json.dump(report, open(REPORT, "w"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
