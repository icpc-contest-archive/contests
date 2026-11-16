#!/usr/bin/env python3
"""Clear `complete: false` on problem sets whose list is in fact complete.

  python3 tools/clear_stale_incomplete.py [--write]

A set says `complete: false` while its problem list is partial. Lists were filled in later (from
judge pages, statements, the problem archive) without the flag being cleared, so some sets carry
it although they list exactly as many problems as their `count`. Those lists are complete
(ruling of 2026-11-15): the flag goes. A set with no count, or with fewer problems listed than its
count, keeps it. Without --write nothing is changed.
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, load_sets  # noqa: E402
from mine_judge_links import dump_set  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    sets = load_sets()
    stale = [sid for sid, d in sets.items() if d.get("complete") is False and d.get("count") and len(d.get("problems") or []) == d["count"]]
    left = []
    for sid in stale:
        f = ROOT / "problemsets" / f"{sid}.yaml"
        text = f.read_text()
        if dump_set(sets[sid]) == text:
            del sets[sid]["complete"]
            new = dump_set(sets[sid])
        else:   # the file is not in the writer's form: take out the one line, leave the rest as it is
            new, k = re.subn(r"(?m)^complete: false\n", "", text)
            if k != 1:
                left.append(sid)
                continue
        if a.write:
            f.write_text(new)
    print(f"{len(stale)} sets say complete: false but list as many problems as their count")
    print(f"{len(stale) - len(left)} " + ("cleared" if a.write else "would be cleared (--write)"))
    if left:
        print(f"{len(left)} left alone, the flag is not on a line of its own: " + ", ".join(left))
    return 0


if __name__ == "__main__":
    sys.exit(main())
