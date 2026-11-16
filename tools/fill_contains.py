#!/usr/bin/env python3
"""Set `contains:` on problemset and problem sources from the content check's reading of our copies.

  python3 tools/fill_contains.py --name run-2026-11-15 [--write]

The content check (tools/content_check_rubric.md) recorded, for every problem set source it could
read, the `material` the document holds: statements, names-only, data, solutions, package. That is
the source's `contains:` (DEFINITIONS.md, Coverage). A verdict that could not tell, or that found
the document to be another contest's, says nothing about this source and is skipped; so is a source
that is no longer a problem set. An existing `contains:` is left alone unless --force.
Without --write nothing is changed; the counts are printed either way.
"""
import argparse, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue as cat  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORD = {"statements": "statement", "statement": "statement", "names-only": "names", "names": "names",
        "data": "data", "solutions": "solutions", "package": "package"}
SKIP = {"cannot-tell", "wrong-contest", "no-copy", "not-the-document"}


def norm(material) -> list[str] | None:
    """The check's `material` as a `contains:` list, in CONTAINS order; None when a word is not understood."""
    if isinstance(material, str):
        material = [x.strip() for x in material.replace(";", ",").split(",") if x.strip()]
    out = set()
    for x in material or []:
        if x not in WORD:
            return None
        out.add(WORD[x])
    if out - {"names"}:
        out.discard("names")   # names-only means nothing but the names: any material makes it moot
    return [k for k in cat.CONTAINS if k in out]


def put(s: dict, got: list[str]) -> None:
    """Set `contains` on a source in place, after `scope` (or `roles`), leaving every other key where it is."""
    items = [(k, v) for k, v in s.items() if k != "contains"]
    at = max(i for i, (k, _v) in enumerate(items) if k in ("roles", "scope")) + 1
    items.insert(at, ("contains", got))
    s.clear()
    s.update(items)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    verdicts = {}
    for f in sorted((ROOT / "data" / "content-check" / a.name).glob("w*.json")):
        verdicts.update(json.loads(f.read_text()))
    series = cat.load_series()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    count, touched = Counter(), set()
    for cid, d in verdicts.items():
        if cid not in where:
            continue
        sid, c = where[cid]
        for v in d.get("sources") or []:
            m = (v.get("facts") or {}).get("material")
            if m is None:
                continue
            s = cat.find_source(c, v["url"])
            if s is None:
                count["source gone"] += 1
            elif not ({"problemset", "problem"} & set(s["roles"])):
                count["no longer a problem set"] += 1
            elif v.get("verdict") in SKIP:
                count["verdict says nothing"] += 1
            elif "contains" in s and not a.force:
                count["already set"] += 1
            elif (got := norm(m)) is None:
                count["material not understood"] += 1
            else:
                put(s, got)
                touched.add(sid)
                count["set"] += 1
                count["  " + ("on a judge: " if s.get("judge") else "") + (", ".join(got) or "none of these")] += 1
    for k, n in sorted(count.items(), key=lambda x: (x[0].startswith("  "), -x[1])):
        print(f"{n:6}  {k}")
    if a.write:
        for sid in sorted(touched):
            cat.dump_series(sid, series[sid], "fill_contains.py")
        print(f"wrote {len(touched)} series files")
    else:
        print(f"dry run: {len(touched)} series files would change (--write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
