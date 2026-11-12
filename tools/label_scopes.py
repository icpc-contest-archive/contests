#!/usr/bin/env python3
"""Mark sources that cover one division of a contest: `scope: Division 1`. Deterministic; a second
run changes nothing.

A contest run in divisions has a scoreboard, a problem set and a judge page per division. The
catalogue listed them as two sources of the same role with nothing to tell them apart. The
division is taken, in this order, from
  - data/import/source-scopes-<date>.json: what the archived capture says (the Kattis filter
    heading "Site: Division 1", the page title or heading), read on the machine that has the archive;
  - the address (…/div1/…, acpc20d2.kattis.com, index_D1.html);
  - the source's note ("…; Div. 1").
Two readings that disagree are reported and left alone.

  python3 tools/label_scopes.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import dump_series, load_series, normalise_source  # noqa: E402

TOOL = "label_scopes.py"
URL_DIV = re.compile(r"(?i)(?:[/_.=-]|^)div(?:ision)?[-_]?([12])(?=[/_.?&-]|$)|[a-z]{3,}[0-9]{2}-?d([12])(?=[/.]|$)|[/_-]d([12])(?=[/_.-]|$)")
NOTE_DIV = re.compile(r"\bDiv(?:ision)?\.? ?([12])\b")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    read = {}
    for f in sorted((ROOT / "data" / "import").glob("source-scopes-*.json")):
        for e in json.loads(f.read_text())["sources"]:
            read[(e["contest"], e["url"])] = e["scope"]
    series = load_series()
    touched, n, clash = set(), 0, []
    for sid, doc in series.items():
        for c in doc["contests"]:
            for i, s in enumerate(c.get("sources") or []):
                m, k = URL_DIV.search(s["url"].split("?")[0]), NOTE_DIV.search(s.get("note") or "")
                got = {x for x in (read.get((c["id"], s["url"])),
                                   m and "Division " + next(g for g in m.groups() if g),
                                   k and "Division " + k.group(1)) if x}
                if len(got) > 1:
                    clash.append((c["id"], s["url"], sorted(got)))
                elif got and s.get("scope") != (scope := got.pop()):
                    s["scope"] = scope
                    c["sources"][i] = normalise_source(s)
                    touched.add(sid)
                    n += 1
    print(f"{n} sources marked with a division in {len(touched)} series files" + (f"; {len(clash)} left alone (readings disagree)" if clash else ""))
    for x in clash:
        print("  ", *x)
    if not a.dry_run:
        for sid in sorted(touched):
            dump_series(sid, series[sid], TOOL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
