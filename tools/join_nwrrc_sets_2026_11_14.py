#!/usr/bin/env python3
"""Subregionals that sat the North-Western Russia (NWRRC) set on the same day join that year's set.

  west-neerc-2022            2022-10-29, the NWRRC 2022 date: the acm.bsu.by standings (contest 198) have 14
                             problems with the solve profile of the NWRRC set
  tajikistan-2025, turkmenistan-2025   2025-11-15, the NWRRC 2025 date: 12 problems, same solved letters
Evidence is the identical date, the problem count and the solve profile in the NERC archive standings; no
page states it outright (unlike the members already in these sets). Read 2026-11-14.

    python3 tools/join_nwrrc_sets_2026_11_14.py [--dry-run]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from import_judge_links import dump  # noqa: E402

PLAN = {"north-russia-2022": ["west-neerc-2022"], "north-russia-2025": ["tajikistan-2025", "turkmenistan-2025"]}


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    touched = set()
    for sid, cids in PLAN.items():
        s = sets[sid]; own = next(e for e in s["contests"] if e["contest"] == sid)
        for cid in cids:
            ser, c = where[cid]; assert not (c.get("problems") or {}).get("set"), cid
            e = {"contest": cid}
            if isinstance(own.get("letters"), dict): e["letters"] = dict(own["letters"])
            s["contests"].append(e); c["problems"] = {"set": sid}; touched.add(ser)
            s.setdefault("provenance", []).append(f"{cid} sat this set: same date, same problem count and solve profile in its standings; not stated on a page (tools/join_nwrrc_sets_2026_11_14.py)")
            print(cid, "->", sid)
    if not dry:
        for sid in PLAN: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], "join_nwrrc_sets_2026_11_14.py (2026-11-14)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
