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
from resources import is_wrapper  # noqa: E402

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
            for w in refs(c.get("web")):
                check_locator(f"{c['id']}.web", w)
            for w in refs(c.get("problemset")):
                check_locator(f"{c['id']}.problemset", w)
            for m in c.get("mirrors") or []:
                check_locator(f"{c['id']}.mirrors", m)
            for kind, lst in (c.get("results") or {}).items():
                for e in lst:
                    check_locator(f"{c['id']}.results.{kind}", e)

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

    # ---- problems: contest blocks + problems/<id>.yaml (DEFINITIONS.md, Problems) ----
    pschema = json.loads((ROOT / "schema" / "problems.schema.json").read_text())
    pvalidator = Draft202012Validator(pschema)
    pblock_schema = {"$ref": "#/$defs/problemsBlock", "$defs": schema["$defs"]}
    pblock_validator = Draft202012Validator(pblock_schema)
    all_known = {**{c["id"]: c for c in non_mainline["non_mainline_contests"]}, **contests}
    for cid, c in all_known.items():
        pb = c.get("problems")
        if pb is None:
            continue
        if cid not in contests:  # series files are schema-checked above; the registry is not
            for e in pblock_validator.iter_errors(pb):
                err(f"non-mainline {cid}: problems: {'/'.join(map(str, e.path))}: {e.message[:140]}")
        for key in ("judges",):
            for v in (pb.get(key) or {}).values():
                for loc in (v if isinstance(v, list) else [v]):
                    check_locator(f"{cid}.problems.judges", loc)
        if pb.get("counts"):
            for k, n in pb["counts"].items():
                if pb.get(k) != "partial":
                    err(f"{cid}: problems.counts.{k} given but {k} is {pb.get(k)!r} (counts are for partial kinds only)")
                if pb.get("count") is not None and not 0 < n < pb["count"]:
                    err(f"{cid}: problems.counts.{k}={n} is not strictly between 0 and count={pb['count']}")
        # problem data must never be published before the contest has run
        d = parse_date(c.get("date"))
        if c.get("status") == "upcoming" or (d and d > TODAY):
            if pb.get("count") or any(pb.get(k) not in (None, "none") for k in ("statement", "data", "solutions", "package")) or pb.get("repo"):
                err(f"{cid}: problem data on a contest that has not run yet (upcoming / dated {c.get('date')}) — not publishable")
    uuid_owner: dict[str, list[str]] = defaultdict(list)
    pdir = ROOT / "problems"
    for f in sorted(pdir.glob("*.yaml")) if pdir.exists() else []:
        doc = yaml.safe_load(f.read_text())
        for e in pvalidator.iter_errors(doc):
            err(f"problems/{f.name}: schema: {'/'.join(map(str, e.path))}: {e.message[:140]}")
        cid = doc.get("contest")
        if cid != f.stem:
            err(f"problems/{f.name}: contest {cid!r} != filename")
        c = all_known.get(cid)
        if c is None:
            err(f"problems/{f.name}: contest {cid!r} is not in the catalogue or the non-mainline registry")
            continue
        if c.get("status") == "upcoming" or ((d := parse_date(c.get("date"))) and d > TODAY):
            err(f"problems/{f.name}: per-problem data for a contest that has not run yet — not publishable")
        probs = doc.get("problems") or []
        letters = [p.get("letter") for p in probs if p.get("letter")]
        if len(set(letters)) != len(letters):
            err(f"problems/{f.name}: duplicate letters {sorted(l for l in letters if letters.count(l) > 1)}")
        if len(letters) < len(probs) and doc.get("letters") != "unknown":
            err(f"problems/{f.name}: {len(probs) - len(letters)} problem(s) without a letter — set letters: unknown or add them")
        pb = c.get("problems") or {}
        if doc.get("complete") is False:
            if pb.get("count") is not None and len(probs) > pb["count"]:
                err(f"problems/{f.name}: {len(probs)} problems listed but {cid} says count {pb['count']}")
            elif pb.get("count") is not None and len(probs) == pb["count"] and all(p.get("letter") for p in probs):
                warn(f"problems/{f.name}: marked incomplete but lists all {pb['count']} problems with letters — drop complete: false")
        elif pb.get("count") is None:
            err(f"problems/{f.name}: contest {cid} has no problems.count (set it to {len(probs)}, or mark the file complete: false)")
        elif pb["count"] != len(probs):
            err(f"problems/{f.name}: {len(probs)} problems listed but {cid} says count {pb['count']}")
        for kind, key in (("statement", "statement"), ("data", "data"), ("solutions", "solutions"), ("package", "package")):
            if pb.get(kind) is None or not all("have" in p for p in probs):
                continue  # holdings per problem not recorded (judge-derived list): nothing to compare
            n = sum(1 for p in probs if key in (p.get("have") or []))
            implied = "full" if n == len(probs) else ("none" if n == 0 else "partial")
            if implied != pb[kind]:
                err(f"problems/{f.name}: {kind} is {pb[kind]} on the contest but the problem rows say {implied} ({n}/{len(probs)})")
        for p in probs:
            if p.get("uuid"):
                uuid_owner[p["uuid"]].append(f"{cid}/{p.get('letter')}")
            for v in (p.get("judges") or {}).values():
                for loc in (v if isinstance(v, list) else [v]):
                    check_locator(f"problems/{f.name} {p.get('letter')}.judges", loc)
    # a uuid may legitimately recur (the same problem reused in another contest) but never twice in one contest
    for u, owners in uuid_owner.items():
        by_contest = defaultdict(list)
        for o in owners:
            by_contest[o.split("/")[0]].append(o)
        for cid, os_ in by_contest.items():
            if len(os_) > 1:
                err(f"uuid {u} appears twice in {cid}: {os_}")

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
