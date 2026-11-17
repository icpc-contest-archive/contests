#!/usr/bin/env python3
"""Give per-problem sources their problem as data: `problem: <letter>` (2026-11-16).

  python3 tools/migrate_problem_letters.py [--write]

A `problem` source is one problem's document (a statement PDF, a page). Which problem it is was
written in the free-text `note` ("problem A"). It is a fact the site links on — the source's page
names the contest, the problem set and the problem — so it becomes a field of its own, and the
note, which said nothing else, goes. Without --write nothing is changed.
"""
import argparse, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import dump_series, load_series, sources  # noqa: E402

NOTE = re.compile(r"^problem ([A-Z0-9]{1,3})$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    n = files = 0
    for sid, doc in load_series().items():
        hit = 0
        for c in doc["contests"]:
            for s in sources(c):
                m = NOTE.match((s.get("note") or "").strip())
                if m and "problem" in s["roles"] and "problem" not in s:
                    kept = {k: v for k, v in s.items() if k != "note"}
                    s.clear()   # `problem` goes right after `roles`; every other key keeps its place
                    for k, v in kept.items():
                        s[k] = v
                        if k == "roles":
                            s["problem"] = m.group(1)
                    hit += 1
        if hit:
            n += hit
            files += 1
            if a.write:
                dump_series(sid, doc, "migrate_problem_letters.py")
    print(f"{n} problem sources in {files} series files" + ("" if a.write else " (dry run; --write to apply)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
