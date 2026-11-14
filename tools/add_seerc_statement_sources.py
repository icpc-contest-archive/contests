#!/usr/bin/env python3
"""SEERC 1999-2015: the files each year's problems page links to become sources.

The organisers' problems pages (seerc.icpc.global/<year>/problems.htm, a `problemset`
source) are link lists. From the pages as fetched 2026-11-14
(data/import/seerc-problem-page-links-2026-11-14.json):
  - a per-problem statement PDF  -> role `problem`, note "problem <letter>"
  - an archive of all statements -> role `problemset`
  - test-data archives (2000, 2002) and the 2013 time-limits sheet -> role `problemset`
    (bare test data is a problem set source, ruling 2026-11-14)
The page itself stays a `problemset` source (ruling 2026-11-14: both).
Re-runnable: an address already catalogued only gains the role.

Usage (from the repo root): python3 tools/add_seerc_statement_sources.py && python3 tools/validate.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import add_source, dump_series, load_series  # noqa: E402


def classify(url: str) -> tuple[str, str] | None:
    name = url.rsplit("/", 1)[1]
    m = re.fullmatch(r"([A-Za-z])\.pdf", name, re.I)
    if m:
        return "problem", f"problem {m.group(1).upper()}"
    if "/Test_Data/" in url:
        m = re.fullmatch(r"([a-z])\.zip", name)
        return "problemset", f"test data, problem {m.group(1).upper()}" if m else "test data (archive)"
    if "data_files" in name:
        return "problemset", "test data (archive)"
    if name.lower().endswith((".zip", ".tar.gz")):
        return "problemset", "all statements (archive)"
    if name.startswith("Time"):
        return "problemset", "time limits"
    return None


def main() -> int:
    links = json.loads((ROOT / "data" / "import" / "seerc-problem-page-links-2026-11-14.json").read_text())
    docs = load_series()
    doc = docs["seerc"]
    contests = {c["id"]: c for c in doc["contests"]}
    added = skipped = 0
    for page, urls in links.items():
        year = re.search(r"/(\d{4})/", page).group(1)
        c = contests[f"seerc-{year}"]
        for u in urls:
            k = classify(u)
            if k is None:
                skipped += 1
                print("not classified:", u)
                continue
            _, changed = add_source(c, u, k[0], note=k[1])
            added += changed
    if added:
        dump_series("seerc", doc, "tools/add_seerc_statement_sources.py")
    print(f"sources added or given a role: {added}; not classified: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
