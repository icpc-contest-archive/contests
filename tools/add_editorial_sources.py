#!/usr/bin/env python3
"""Add `editorial` sources (solution slides, problem analyses) to contests.

    python3 tools/add_editorial_sources.py <candidates.json> --date YYYY-MM-DD [--dry-run]

<candidates.json>: {contest id: [url, ...]}. A url the contest already has gains the role.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import add_source, dump_series, load_series  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("candidates"); ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    cands = json.loads(Path(a.candidates).read_text()); series = load_series(); touched = set(); n = 0
    where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    for cid, urls in sorted(cands.items()):
        if cid not in where: print("not in catalogue:", cid); continue
        ser, c = where[cid]
        for u in urls:
            if add_source(c, u, "editorial")[1]: touched.add(ser); n += 1
    if not a.dry_run:
        for ser in touched: dump_series(ser, series[ser], f"add_editorial_sources.py ({a.date})")
    print(f"{n} editorial sources on {len(cands)} contests, {len(touched)} series" + (" (dry run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
