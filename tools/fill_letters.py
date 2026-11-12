#!/usr/bin/env python3
"""Give a problem its letter when only one letter is left for it. Deterministic; a second run
changes nothing.

A contest's letter map can miss a problem that the judge page did not show (hidden, renamed).
When the set is complete, every other problem has its letter, the letters run A, B, C… without
a second gap, and exactly one problem is left, the missing letter is that problem's. Nothing else
is inferred; maps with more than one gap are listed, not touched.

  python3 tools/fill_letters.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import load_sets  # noqa: E402
from merge_problemsets import dump_set  # noqa: E402

TOOL = "fill_letters.py"
DAY = "2026-11-12"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    done, open_ = [], 0
    for sid, doc in load_sets().items():
        probs = doc.get("problems") or []
        n = len(probs)
        changed = False
        for e in doc["contests"]:
            letters = e.get("letters") or {}
            if not letters or len(letters) == n:
                continue
            left = [p for p in probs if p["id"] not in letters.values()]
            want = [chr(65 + i) for i in range(n)]
            gap = [x for x in want if x not in letters]
            whole = doc.get("complete") is not False and doc.get("count") in (None, n)
            if whole and len(left) == 1 and len(gap) == 1 and set(letters) <= set(want):
                e["letters"] = dict(sorted({**letters, gap[0]: left[0]["id"]}.items()))
                line = f"{DAY}: {e['contest']} letter {gap[0]} = {left[0]['name']}: the one letter and the one problem left (tools/{TOOL})"
                doc["provenance"] = (doc.get("provenance") or []) + [line]
                done.append((sid, e["contest"], gap[0], left[0]["name"]))
                changed = True
            else:
                open_ += 1
        if changed and not a.dry_run:
            (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump_set(doc))
    for x in done:
        print("  %s: %s gets %s = %s" % x)
    print(f"{len(done)} letters filled; {open_} letter maps still miss problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
