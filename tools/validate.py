#!/usr/bin/env python3
"""Validate the catalogue: JSON Schema + cross-file invariants.

Errors fail the build (exit 1). Warnings are written to reports/open-warnings.md
and printed; they represent known judgment calls and unresearched gaps.
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resources import is_wrapper, norm_key  # noqa: E402

try:
    from jsonschema import Draft202012Validator
except ImportError:  # older jsonschema (e.g. distro packages)
    from jsonschema import Draft7Validator as Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
TODAY = datetime.date.today()

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def refs(value) -> list[str]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def parse_date(s):
    try:
        return datetime.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def main() -> int:
    schema = json.loads((ROOT / "schema" / "catalogue.schema.json").read_text())
    validator = Draft202012Validator(schema)

    series_docs: dict[str, dict] = {}
    for f in sorted((ROOT / "series").glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        for e in validator.iter_errors(doc):
            err(f"{f.name}: schema: {'/'.join(map(str, e.path))}: {e.message[:140]}")
        series_docs[f.stem] = doc

    non_mainline = yaml.safe_load((ROOT / "registry" / "non-mainline.yaml").read_text())
    triage = yaml.safe_load((ROOT / "registry" / "cms-triage.yaml").read_text())

    # ---- locators are bare URLs, never archive wrappers (DEFINITIONS.md, Resources) ----
    def check_locator(where: str, v):
        if isinstance(v, dict):
            v = v.get("url")
        if isinstance(v, str) and is_wrapper(v):
            err(f"{where}: archive wrapper URL used as locator — unwrap into url + as_of "
                f"(tools/migrate_resources.py): {v[:100]}")

    for sid, doc in series_docs.items():
        for c in doc["contests"]:
            seen_addr: dict[str, str] = {}
            for s in c.get("sources") or []:
                check_locator(f"{c['id']}.sources", s)
                for a in s.get("also_at") or []:
                    check_locator(f"{c['id']}.sources.also_at", a)
                k = norm_key(s["url"])
                if k in seen_addr:
                    err(f"{c['id']}: address listed twice in sources ({s['url']}); merge the roles")
                seen_addr[k] = s["url"]
                if s.get("judge") and not ({"problemset", "problem"} & set(s["roles"])):
                    err(f"{c['id']}: source {s['url'][:80]}: `judge:` belongs on a problemset or problem source")
                if s.get("url_checked") and not s.get("url_state"):
                    err(f"{c['id']}: source {s['url'][:80]}: url_checked without url_state")
            for r in c.get("none") or []:
                if any(r in s["roles"] for s in c.get("sources") or []):
                    err(f"{c['id']}: role {r} is both in none: and on a source")
            if "mirrors" in c or "web" in c or "results" in c or "problemset" in c or "icpc_standings" in c:
                err(f"{c['id']}: pre-2026-11 field present (web/results/problemset/mirrors/icpc_standings) — run tools/migrate_sources.py")

    # ---- index all mainline contests ----
    contests: dict[str, dict] = {}
    series_of: dict[str, str] = {}
    for sid, doc in series_docs.items():
        if doc["series"]["id"] != sid:
            err(f"{sid}.yaml: series.id {doc['series']['id']!r} != filename")
        for c in doc["contests"]:
            cid = c["id"]
            if cid in contests:
                err(f"duplicate contest id {cid}")
            if not cid.startswith(sid + "-") or not re.fullmatch(re.escape(sid) + r"-\d{4}", cid):
                err(f"{sid}.yaml: contest {cid} does not belong to series {sid}")
            contests[cid] = c
            series_of[cid] = sid

    # ---- reference resolution + date ordering + season consistency ----
    champ = {sid for sid, d in series_docs.items() if d["series"].get("tier") == "championship"}
    for cid, c in contests.items():
        d = parse_date(c.get("date"))
        for kind in ("parent", "next"):
            for ref in refs(c.get(kind)):
                if ref not in contests:
                    err(f"{cid}: {kind} {ref!r} does not resolve")
                    continue
                t = contests[ref]
                td = parse_date(t.get("date"))
                if d and td and td < d:
                    warn(f"{cid} ({c.get('date')}): {kind} {ref} is dated earlier ({t.get('date')})")
        sub = c.get("subset_of")
        if sub:
            if sub not in contests:
                err(f"{cid}: subset_of {sub!r} does not resolve")
            else:
                a, b = set(c.get("cms_ids", [])), set(contests[sub].get("cms_ids", []))
                if not (a and a < b):
                    err(f"{cid}: subset_of {sub} but cms_ids {sorted(a)} not a proper subset of {sorted(b)}")
                if (c.get("status") == "upcoming") != (contests[sub].get("status") == "upcoming"):
                    warn(f"{cid} and its superset {sub} disagree on upcoming status")
        parents = refs(c.get("parent"))
        if parents and c.get("season"):
            for p in parents:
                ps = contests.get(p, {}).get("season")
                if ps and ps != c["season"]:
                    warn(f"{cid}: season {c['season']} != parent {p} season {ps}")
        if c.get("status") == "upcoming" and d and d < TODAY:
            warn(f"{cid}: marked upcoming but dated {c['date']} (past) — confirm it ran")
        if c.get("status") != "upcoming" and d and d > TODAY:
            warn(f"{cid}: not marked upcoming but dated {c['date']} (future)")
        if d and (m := re.search(r"-(\d{4})$", cid)):
            diff = d.year - int(m.group(1))
            if diff < 0 or diff > 2:
                warn(f"{cid}: date {c['date']} vs name year (diff {diff:+d})")
        # id year follows the series' naming pattern (DEFINITIONS.md, Naming)
        naming = series_docs[series_of[cid]]["series"].get("naming")
        if naming and c.get("season") and (m := re.search(r"-(\d{4})$", cid)):
            expected = c["season"] if naming == "season-end" else c["season"] - 1
            if int(m.group(1)) != expected:
                err(f"{cid}: id year {m.group(1)} but season {c['season']} and series naming is {naming} "
                    f"(expected {series_of[cid]}-{expected})")

    for sid, doc in series_docs.items():
        h = doc["series"]
        for k in ("tier", "naming", "region"):
            if not h.get(k):
                warn(f"{sid}: series header has no {k}")

    # ---- wf reachability ----
    def reaches_wf(cid, seen=None):
        seen = seen or set()
        if cid in seen:
            err(f"parent cycle involving {cid}")
            return False
        seen.add(cid)
        if cid.startswith("wf-"):
            return True
        parents = refs(contests[cid].get("parent"))
        return any(reaches_wf(p, seen) for p in parents if p in contests)

    dangling = [cid for cid, c in contests.items()
                if c.get("status") != "upcoming" and not reaches_wf(cid)]
    if dangling:
        warn(f"{len(dangling)} contests do not reach a WF via parents (parent unknown): "
             + ", ".join(sorted(dangling)[:8]) + (" …" if len(dangling) > 8 else ""))

    # ---- CMS id uniqueness across catalogue + triage ----
    owner: dict[int, list[str]] = defaultdict(list)
    for cid, c in contests.items():
        for n in c.get("cms_ids", []):
            owner[n].append(cid)
    for n, owners in sorted(owner.items()):
        if len(owners) > 1:
            covered = all(
                contests[a].get("subset_of") in owners or contests[b].get("subset_of") in owners
                for a in owners for b in owners if a != b
            )
            if not covered:
                err(f"cms id {n} on {owners} without a subset_of relation")
    triage_ids = {e["cms_id"] for e in triage["excluded"]}
    both = triage_ids & set(owner)
    for n in sorted(both):
        err(f"cms id {n} present in both catalogue ({owner[n]}) and triage")
    for e in triage["excluded"]:
        if e["reason"] not in {"cancelled", "camp", "challenge", "junk", "minor", "structural",
                                "preliminary", "non-mainline", "special"}:
            err(f"triage {e['cms_id']}: unknown reason {e['reason']!r}")

    # ---- non-mainline sanity ----
    for c in non_mainline["non_mainline_contests"]:
        if c["id"] in contests:
            err(f"{c['id']} present in both series/ and non-mainline registry")

    # ---- problem sets: problemsets/<set-id>.yaml + contest links (DEFINITIONS.md, Problems) ----
    judges_doc = yaml.safe_load((ROOT / "judges.yaml").read_text())
    judge_ids = {j["id"] for j in judges_doc["judges"]}
    for cid, c in contests.items():
        for s in c.get("sources") or []:
            if s.get("judge") and s["judge"] not in judge_ids:
                err(f"{cid}: unknown judge {s['judge']!r} (add it to judges.yaml)")
    pschema = json.loads((ROOT / "schema" / "problemsets.schema.json").read_text())
    pvalidator = Draft202012Validator(pschema)
    all_known = {**{c["id"]: c for c in non_mainline["non_mainline_contests"]}, **contests}
    sets: dict[str, dict] = {}
    pdir = ROOT / "problemsets"
    for f in sorted(pdir.glob("*.yaml")) if pdir.exists() else []:
        doc = yaml.safe_load(f.read_text())
        for e in pvalidator.iter_errors(doc):
            err(f"problemsets/{f.name}: schema: {'/'.join(map(str, e.path))}: {e.message[:140]}")
        if doc.get("id") != f.stem:
            err(f"problemsets/{f.name}: id {doc.get('id')!r} != filename")
        sets[f.stem] = doc
    set_users: dict[str, list[str]] = defaultdict(list)
    for cid, c in all_known.items():
        pb = c.get("problems")
        if not pb:
            continue
        if cid not in contests:
            for e in Draft202012Validator({"$ref": "#/$defs/problemsBlock", "$defs": schema["$defs"]}).iter_errors(pb):
                err(f"non-mainline {cid}: problems: {e.message[:140]}")
        sid_ = pb.get("set")
        if sid_ not in sets:
            err(f"{cid}: problems.set {sid_!r} has no problemsets/{sid_}.yaml")
            continue
        set_users[sid_].append(cid)
        if cid not in {e["contest"] for e in sets[sid_]["contests"]}:
            err(f"{cid}: links to set {sid_} but the set does not list it under contests")
    pid_owner: dict[str, set] = defaultdict(set)
    uuid_owner: dict[str, set] = defaultdict(set)
    for sid_, doc in sets.items():
        probs = doc.get("problems") or []
        ids = [p["id"] for p in probs]
        if len(set(ids)) != len(ids):
            err(f"problemsets/{sid_}.yaml: duplicate problem id")
        for p in probs:
            pid_owner[p["id"]].add((p.get("uuid"), p["name"]))
            if p.get("uuid"):
                uuid_owner[p["uuid"]].add(p["id"])
            for j in p.get("judges") or []:
                if j["judge"] not in judge_ids:
                    err(f"problemsets/{sid_}.yaml {p['id']}: unknown judge {j['judge']!r}")
                check_locator(f"problemsets/{sid_}.yaml {p['id']}.judges", j["url"])
        members = [e["contest"] for e in doc["contests"]]
        for e in doc["contests"]:
            m = e["contest"]
            c = all_known.get(m)
            if c is None:
                err(f"problemsets/{sid_}.yaml: contest {m!r} is not in the catalogue or the non-mainline registry")
                continue
            if (c.get("problems") or {}).get("set") != sid_:
                err(f"problemsets/{sid_}.yaml lists {m} but {m} links to set {(c.get('problems') or {}).get('set')!r}")
            # nothing about a set is publishable before every contest that uses it has run
            d = parse_date(c.get("date"))
            if c.get("status") == "upcoming" or (d and d > TODAY):
                if probs or doc.get("repo") or any(doc.get(k) not in (None, "none") for k in ("statement", "data", "solutions", "package")):
                    err(f"problemsets/{sid_}.yaml: problem data on a contest that has not run yet ({m}, {c.get('date')}) — not publishable")
            letters = e.get("letters") or {}
            for letter, pid_ in letters.items():
                if pid_ not in ids:
                    err(f"problemsets/{sid_}.yaml: {m} letter {letter} -> {pid_} is not a problem of the set")
            if len(set(letters.values())) != len(letters):
                err(f"problemsets/{sid_}.yaml: {m} maps two letters to one problem")
        if len(members) != len(set(members)):
            err(f"problemsets/{sid_}.yaml: a contest is listed twice")
        n, cnt = len(probs), doc.get("count")
        if doc.get("complete") is False:
            if cnt is not None and n > cnt:
                err(f"problemsets/{sid_}.yaml: {n} problems listed but count {cnt}")
        elif probs:
            if cnt is None:
                err(f"problemsets/{sid_}.yaml: {n} problems but no count (set count: {n}, or complete: false)")
            elif cnt != n:
                err(f"problemsets/{sid_}.yaml: {n} problems listed but count {cnt} (mark complete: false if the list is partial)")
        if probs and doc.get("letters") != "unknown" and not any(e.get("letters") for e in doc["contests"]):
            err(f"problemsets/{sid_}.yaml: problems listed but no contest has a letter map — add one or set letters: unknown")
        if doc.get("counts"):
            for k, v in doc["counts"].items():
                if doc.get(k) != "partial":
                    err(f"problemsets/{sid_}.yaml: counts.{k} given but {k} is {doc.get(k)!r}")
                if cnt is not None and not 0 < v < cnt:
                    err(f"problemsets/{sid_}.yaml: counts.{k}={v} not strictly between 0 and count={cnt}")
        for kind in ("statement", "data", "solutions", "package"):
            if doc.get(kind) is None or not probs or not all("have" in p for p in probs) or doc.get("complete") is False:
                continue
            k = sum(1 for p in probs if kind in (p.get("have") or []))
            implied = "full" if k == n else ("none" if k == 0 else "partial")
            if implied != doc[kind]:
                err(f"problemsets/{sid_}.yaml: {kind} is {doc[kind]} but the problem rows say {implied} ({k}/{n})")
    for sid_ in sets:
        if sid_ not in set_users:
            warn(f"problemsets/{sid_}.yaml is used by no contest")
    # merged ids (set `aliases`, problem `aliases`): never a live id, never claimed twice — old pages redirect by them
    set_alias: dict[str, str] = {}
    prob_alias: dict[str, str] = {}
    live_pids = {p["id"] for d in sets.values() for p in d.get("problems") or []}
    for sid_, doc in sets.items():
        for old in doc.get("aliases") or []:
            if old in sets:
                err(f"problemsets/{sid_}.yaml: alias {old!r} is also a set — an id merged away is not reused")
            if set_alias.setdefault(old, sid_) != sid_:
                err(f"problemsets/{sid_}.yaml: alias {old!r} is also claimed by {set_alias[old]}")
        for pr in doc.get("problems") or []:
            for old in pr.get("aliases") or []:
                if old in live_pids:
                    err(f"problemsets/{sid_}.yaml {pr['id']}: alias {old} is also a problem id")
                if prob_alias.setdefault(old, pr["id"]) != pr["id"]:
                    err(f"problemsets/{sid_}.yaml {pr['id']}: alias {old} is also claimed by {prob_alias[old]}")
    for i, names in pid_owner.items():
        if len({u for u, _ in names if u}) > 1:
            err(f"problem id {i} carries two different uuids: {sorted(names)}")
    for u, ids_ in uuid_owner.items():
        if len(ids_) > 1:
            err(f"uuid {u} appears under two problem ids {sorted(ids_)} — merge them (aliases)")

    # ---- locations: locations.yaml tree + contest sites (DEFINITIONS.md, Locations) ----
    loc_path = ROOT / "locations.yaml"
    nodes: dict[str, dict] = {}
    if loc_path.exists():
        lschema = json.loads((ROOT / "schema" / "locations.schema.json").read_text())
        ldoc = yaml.safe_load(loc_path.read_text()) or {}
        for e in Draft202012Validator(lschema).iter_errors(ldoc):
            err(f"locations.yaml: schema: {'/'.join(map(str, e.path))}: {e.message[:140]}")
        for n in ldoc.get("locations") or []:
            if n["id"] in nodes:
                err(f"locations.yaml: duplicate id {n['id']}")
            nodes[n["id"]] = n
        allowed_parent = {"region": {"country"}, "city": {"region", "country"}, "institution": {"city"}}
        alias_owner: dict[str, str] = {}
        name_owner: dict[tuple, str] = {}
        for nid, n in nodes.items():
            t = n["type"]
            if t == "country":
                if n.get("parent"):
                    err(f"locations.yaml: country {nid} has a parent")
                if nid != n.get("iso", "").lower():
                    err(f"locations.yaml: country id {nid} is not its ISO code in lowercase ({n.get('iso')})")
            else:
                p = n.get("parent")
                if p not in nodes:
                    err(f"locations.yaml: {nid}: parent {p!r} does not resolve")
                else:
                    pt = nodes[p]["type"]
                    if pt not in allowed_parent[t]:
                        err(f"locations.yaml: {nid} ({t}) hangs under {p} ({pt}); allowed: {sorted(allowed_parent[t])}")
                    # id carries the country, and the parent's id for institutions
                    anc, seen = n, set()
                    while anc.get("parent") and anc["parent"] in nodes and anc["id"] not in seen:
                        seen.add(anc["id"])
                        anc = nodes[anc["parent"]]
                    if anc["type"] != "country":
                        err(f"locations.yaml: {nid}: parent chain does not end at a country")
                    elif not nid.startswith(anc["id"] + "-"):
                        err(f"locations.yaml: {nid}: id does not start with its country's id {anc['id']}-")
                    if t == "institution" and not nid.startswith(p + "-"):
                        err(f"locations.yaml: institution {nid}: id does not start with its city's id {p}-")
                    if t in ("region", "city") and (nid.startswith(p + "-") is False) and nodes[p]["type"] == "region":
                        pass  # cities under a region keep <country>-<city> ids (regions are optional)
            key = (t, n.get("parent"), n["name"].casefold())
            if key in name_owner:
                err(f"locations.yaml: {nid} and {name_owner[key]} are two {t} nodes named {n['name']!r} under the same parent — merge (aliases)")
            name_owner[key] = nid
            for a in n.get("aliases") or []:
                k = a.casefold()
                if k == n["name"].casefold():
                    err(f"locations.yaml: {nid}: alias {a!r} repeats the node's name")
                # aliases are unique across nodes; an acronym (UCI, ASU) may recur in another country only
                acronym = len(a) <= 6 and " " not in a
                owner_id = alias_owner.get(k)
                if owner_id and owner_id != nid and (not acronym or owner_id.split("-")[0] == nid.split("-")[0]):
                    err(f"locations.yaml: alias {a!r} on both {owner_id} and {nid} — aliases must be unique across nodes")
                alias_owner[k] = nid
        if not nodes:
            warn("locations.yaml holds no nodes")
    else:
        warn("locations.yaml missing — contest sites cannot be resolved (tools/migrate_locations.py)")
    n_sites = n_located_contests = 0
    for cid, c in contests.items():
        sites = c.get("sites")
        if sites is None:
            continue
        seen_sites = set()
        located = False
        for i, st in enumerate(sites):
            n_sites += 1
            loc = st.get("location")
            if loc is not None:
                if loc not in nodes:
                    err(f"{cid}: sites[{i}].location {loc!r} does not resolve (locations.yaml)")
                else:
                    located = True
            if not (loc or st.get("name") or st.get("type")):
                err(f"{cid}: sites[{i}] is empty")
            k = (st.get("type"), loc, st.get("name"))
            if k in seen_sites:
                err(f"{cid}: sites[{i}] duplicates an earlier site entry {k}")
            seen_sites.add(k)
        if located:
            n_located_contests += 1

    # ---- lineage symmetry ----
    for sid, doc in series_docs.items():
        for ev in doc["series"].get("lineage", []):
            other = series_docs.get(ev["series"])
            if other is None:
                err(f"{sid}: lineage references unknown series {ev['series']}")
                continue
            mirror = "continues-from" if ev["type"] == "continues-as" else "continues-as"
            if not any(e["type"] == mirror and e["series"] == sid and e["year"] == ev["year"]
                       for e in other["series"].get("lineage", [])):
                warn(f"lineage not mirrored: {sid} {ev['type']} {ev['series']} ({ev['year']})")

    # ---- report ----
    rep = ROOT / "reports" / "open-warnings.md"
    rep.parent.mkdir(exist_ok=True)
    lines = [
        "# Open warnings",
        "",
        f"Generated by tools/validate.py on {TODAY.isoformat()}. "
        f"{len(warnings)} warnings, {len(errors)} errors.",
        "",
    ] + [f"- {w}" for w in warnings]
    rep.write_text("\n".join(lines) + "\n")

    stats = {
        "series": len(series_docs),
        "contests": len(contests),
        "upcoming": sum(1 for c in contests.values() if c.get("status") == "upcoming"),
        "non_mainline": len(non_mainline["non_mainline_contests"]),
        "triage_ids": len(triage_ids),
        "cms_ids_in_catalogue": len(owner),
        "location_nodes": len(nodes),
        "sites": n_sites,
        "contests_with_located_site": n_located_contests,
    }
    print("stats:", json.dumps(stats))
    print(f"warnings: {len(warnings)} (reports/open-warnings.md)")
    for w in warnings[:12]:
        print("  warn:", w)
    if len(warnings) > 12:
        print(f"  … {len(warnings) - 12} more in report")
    if errors:
        print(f"ERRORS: {len(errors)}")
        for e in errors[:40]:
            print("  ERROR:", e)
        return 1
    print("errors: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
