#!/usr/bin/env python3
"""Apply (or check) data-scan fix operations to the catalogue.

    python3 tools/apply_scan_ops.py --check OPS.json [OPS.json ...]   # resolve every op, write nothing
    python3 tools/apply_scan_ops.py OPS.json [OPS.json ...]           # apply, then dump touched files

An ops file is a JSON list (or {"ops": [...]}) of operations. Each operation:

    {"file": "series/nordic.yaml",                 # or problemsets/<id>.yaml, locations.yaml, judges.yaml
     "path": ["contests", {"id": "nordic-2004"}, "date"],
     "op": "set",                                   # set | unset | append | remove | insert_contest | create_file
     "value": "2004-10-02",                         # for set / append / insert_contest / create_file
     "old": "2004-10-03",                           # optional guard: the value the step expects to find
     "reason": "...", "evidence": "..."}            # both required

Path steps: a string is a mapping key, a dict selects the ONE list element whose keys equal it
(e.g. {"url": "http://..."} or {"url": "...", "as_of": "2004..."}), an int is a list index.

- set      the last step is a key of a mapping: sets it (creates it if missing). With "old", the
           current value must equal it ("old": null means the key must be absent or null).
- unset    removes the key (guarded by "old" when given).
- append   the path names a list (created if missing); appends value. An element equal to the value
           already present is "already present", not an error. With "unique_keys": [...] an element
           that agrees on those keys counts as present too.
- remove   the last step selects a list element; removes it. With "old", the element must equal it.
- insert_contest  path ["contests"] in a series file: inserts the contest entry so ids stay sorted;
           refuses an id that exists anywhere in the catalogue.
- create_file     writes a new problemsets/<id>.yaml (value = the set document); refuses to overwrite.

Touched contests are normalised (catalogue.normalise_contest). Every applied op is logged as one line
of JSON to --log (default: the ops file's folder, applied.jsonl).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue as cat  # noqa: E402
from merge_problemsets import dump_set  # noqa: E402

ROOT = cat.ROOT
TOOL = "apply_scan_ops.py"


class OpError(Exception):
    pass


def load(rel: str, cache: dict) -> dict:
    if rel not in cache:
        p = ROOT / rel
        if not p.exists():
            raise OpError(f"no such file {rel}")
        cache[rel] = yaml.safe_load(p.read_text())
    return cache[rel]


def step(node, s, rel, so_far):
    if isinstance(s, str):
        if not isinstance(node, dict):
            raise OpError(f"{rel} {so_far}: expected a mapping before key {s!r}")
        if s not in node:
            raise OpError(f"{rel} {so_far}: no key {s!r}")
        return node[s]
    if isinstance(s, int):
        if not isinstance(node, list) or not -len(node) <= s < len(node):
            raise OpError(f"{rel} {so_far}: bad index {s}")
        return node[s]
    if isinstance(s, dict):
        if not isinstance(node, list):
            raise OpError(f"{rel} {so_far}: expected a list before selector {s}")
        hits = [e for e in node if isinstance(e, dict) and all(e.get(k) == v for k, v in s.items())]
        if len(hits) != 1:
            raise OpError(f"{rel} {so_far}: selector {s} matches {len(hits)} elements")
        return hits[0]
    raise OpError(f"{rel}: bad path step {s!r}")


def resolve(doc, path, rel):
    node = doc
    for i, s in enumerate(path):
        node = step(node, s, rel, path[:i])
    return node


def contest_ids(cache: dict) -> set[str]:
    ids = set()
    for f in sorted((ROOT / "series").glob("*.yaml")):
        doc = load(f"series/{f.name}", cache)
        ids.update(c["id"] for c in doc.get("contests") or [])
    return ids


def apply_one(op: dict, cache: dict, touched: dict, created: dict) -> str:
    for k in ("file", "op", "reason", "evidence"):
        if not op.get(k):
            raise OpError(f"missing {k!r}")
    rel, kind, path = op["file"], op["op"], op.get("path") or []
    if kind == "create_file":
        if not rel.startswith("problemsets/") or not rel.endswith(".yaml"):
            raise OpError("create_file only makes problemsets/<id>.yaml")
        if (ROOT / rel).exists() or rel in created:
            raise OpError(f"{rel} exists")
        v = op["value"]
        if not isinstance(v, dict) or v.get("id") != Path(rel).stem:
            raise OpError("value must be a set document whose id is the file name")
        created[rel] = v
        return "created"
    doc = load(rel, cache)
    if kind == "insert_contest":
        if not rel.startswith("series/") or path != ["contests"]:
            raise OpError("insert_contest needs a series file and path ['contests']")
        v = op["value"]
        if not isinstance(v, dict) or not v.get("id"):
            raise OpError("value must be a contest entry with an id")
        if v["id"] in contest_ids(cache):
            raise OpError(f"contest {v['id']} exists already")
        lst = doc["contests"]
        pos = len(lst)
        for i, c in enumerate(lst):
            if c["id"] > v["id"]:
                pos = i
                break
        lst.insert(pos, cat.normalise_contest(v))
        touched.setdefault(rel, set()).add(v["id"])
        return "inserted"
    if not path:
        raise OpError("empty path")
    if kind in ("set", "unset"):
        parent = resolve(doc, path[:-1], rel)
        key = path[-1]
        if not isinstance(parent, dict) or not isinstance(key, str):
            raise OpError(f"{kind} needs a mapping key as the last step")
        if "old" in op and parent.get(key) != op["old"]:
            raise OpError(f"guard: found {parent.get(key)!r}, expected {op['old']!r}")
        if kind == "set":
            if parent.get(key) == op.get("value") and key in parent:
                result = "unchanged"
            else:
                parent[key] = op["value"]
                result = "set"
        else:
            if key not in parent:
                raise OpError(f"no key {key!r} to unset")
            del parent[key]
            result = "unset"
    elif kind == "append":
        parent = resolve(doc, path[:-1], rel)
        key = path[-1]
        if isinstance(key, str) and isinstance(parent, dict) and key not in parent:
            parent[key] = []
        lst = step(parent, key, rel, path[:-1])
        if not isinstance(lst, list):
            raise OpError("append target is not a list")
        v = op["value"]
        uk = op.get("unique_keys")
        if v in lst or (uk and isinstance(v, dict) and any(
                isinstance(e, dict) and all(e.get(k) == v.get(k) for k in uk) for e in lst)):
            result = "already present"
        else:
            lst.append(v)
            result = "appended"
    elif kind == "remove":
        lst = resolve(doc, path[:-1], rel)
        el = step(lst, path[-1], rel, path[:-1])
        if "old" in op and el != op["old"]:
            raise OpError("guard: element differs from 'old'")
        lst.remove(el)
        result = "removed"
    else:
        raise OpError(f"unknown op {kind!r}")
    if rel.startswith("series/") and len(path) >= 2 and path[0] == "contests" and isinstance(path[1], dict):
        c = step(doc["contests"], path[1], rel, ["contests"]) if not (kind == "remove" and len(path) == 2) else None
        if c is not None:
            touched.setdefault(rel, set()).add(c["id"])
        else:
            touched.setdefault(rel, set())
    else:
        touched.setdefault(rel, set())
    return result


def dump(rel: str, doc: dict, ids: set[str]) -> None:
    p = ROOT / rel
    if rel.startswith("series/"):
        doc["contests"] = [cat.normalise_contest(c) if c["id"] in ids else c for c in doc["contests"]]
        for c in doc["contests"]:
            if c["id"] in ids:
                cat.sort_sources(c)
        cat.dump_series(p.stem, doc, TOOL)
    elif rel.startswith("problemsets/"):
        p.write_text(dump_set(doc))
    else:
        head = "".join(l for l in p.read_text().splitlines(keepends=True)[:5] if l.startswith("#"))
        p.write_text(head + yaml.dump(doc, Dumper=cat.Dumper, sort_keys=False, allow_unicode=True, width=100))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ops", nargs="+")
    ap.add_argument("--check", action="store_true", help="resolve only; write nothing")
    ap.add_argument("--log", help="JSONL log of applied ops")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--partial", action="store_true",
                    help="apply the ops that resolve, skip (and list) the rest — for replaying ops onto a newer state")
    ap.add_argument("--failed", help="with --partial: write the skipped ops here (JSON list, with the reason)")
    a = ap.parse_args()
    cache: dict = {}
    touched: dict = {}
    created: dict = {}
    n_ok = n_bad = 0
    log = []
    failed = []
    for f in a.ops:
        data = json.loads(Path(f).read_text())
        ops = data.get("ops") if isinstance(data, dict) else data
        for i, op in enumerate(ops):
            try:
                r = apply_one(op, cache, touched, created)
                n_ok += 1
                log.append({**op, "_result": r, "_from": f})
                if not a.quiet:
                    print(f"ok   {f}#{i} {op.get('op')} {op.get('file')} {json.dumps(op.get('path'), ensure_ascii=False)[:120]} -> {r}")
            except OpError as e:
                n_bad += 1
                failed.append({**op, "_error": str(e), "_from": f})
                print(f"FAIL {f}#{i} {op.get('op')} {op.get('file')} {json.dumps(op.get('path'), ensure_ascii=False)[:120]}: {e}")
            except Exception as e:  # a malformed op must not stop the rest
                n_bad += 1
                failed.append({**op, "_error": f"{type(e).__name__}: {e}", "_from": f})
                print(f"FAIL {f}#{i}: {type(e).__name__}: {e}")
    print(f"{n_ok} ok, {n_bad} failed{' (check only, nothing written)' if a.check else ''}")
    if a.check:
        return 1 if n_bad else 0
    if n_bad and not a.partial:
        print("not writing: fix or drop the failed ops first")
        return 1
    if failed and a.failed:
        Path(a.failed).write_text(json.dumps(failed, ensure_ascii=False, indent=1))
    for rel, ids in touched.items():
        dump(rel, cache[rel], ids)
    for rel, doc in created.items():
        (ROOT / rel).write_text(dump_set(doc))
    lp = Path(a.log) if a.log else Path(a.ops[0]).resolve().parent / "applied.jsonl"
    with lp.open("a") as fh:
        for row in log:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(touched)} files, created {len(created)}; log {lp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
