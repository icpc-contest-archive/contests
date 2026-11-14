#!/usr/bin/env python3
"""Problem lists from the Shanghai University mirror of the ICPC regionals archive (acm.shu.edu.cn,
Wayback Machine), read 2026-11-14 while checking where the early UVa volumes came from.

  dhaka-1997    .../ProblemSet/ICPCRegionals/asia/dhaka/1997/index.html (capture 2001-04-30): A-F
  taiwan-1996   .../asia/taipei/1996/index.html (2001-05-01): A-H. E reads "Compute the Value of p" on
                the page; the "p" is probably a pi lost in encoding (problem.pdf, capture 2003-06-13).
  taiwan-1997   .../asia/taipei/1997/index.html (2001-05-01): A-H; the mirror marks F "(Problem lost)"
                and G "(Picture lost)".

    python3 tools/add_found_lists_2026_11_14d.py [--dry-run]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

TOOL = "tools/add_found_lists_2026_11_14d.py"
B = "http://acm.shu.edu.cn/ProblemSet/ICPCRegionals/asia/"
SETS = [
    ("dhaka-1997", B + "dhaka/1997/index.html", "20010430012401", None,
     "The Perfect Candidate;Unlucky Volunteer;Amazement;Fast Food?;Lucas Numbers;Premium Plus"),
    ("taiwan-1996", B + "taipei/1996/index.html", "20010501051304", {"E": "title as on the mirror; the 'p' is probably a pi lost in encoding"},
     "Special Sequence Generation;Activity Selection Problem;The Shortest Path Problem;Reflected Gray Codes;Compute the Value of p;Hill Cipher;Permutation Enumeration;Evaluate a Boolean Function"),
    ("taiwan-1997", B + "taipei/1997/index.html", "20010501050812", {"F": "the mirror marks the statement '(Problem lost)'", "G": "the mirror marks it '(Picture lost)'"},
     "Jugs Puzzle;Filling Water Pot;Component Labeling;Reordering Cars on a T-shape Railway;Negative-base Numbers;Verify a Conjecture;Basketball Team Assignment;Sum of Consecutive Positive Integers"),
]


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    touched = set(); made = 0
    for sid, url, ts, notes, titles in SETS:
        ser, c = where[sid]
        if sid not in sets:
            probs = []; letters = {}
            for i, t in enumerate(titles.split(";")):
                l = chr(65 + i); p = {"id": pid(None, sid, l, t), "name": t}
                if notes and l in notes: p["notes"] = notes[l]
                probs.append(p); letters[l] = p["id"]; made += 1
            sets[sid] = {"id": sid, "count": len(probs), "contests": [{"contest": sid, "letters": letters}], "problems": probs,
                         "provenance": [f"letters and titles from {url} (Wayback capture {ts}), read 2026-11-14 ({TOOL})"]}
        c["problems"] = {"set": sid}
        if not any(x["url"] == url for x in c.setdefault("sources", [])):
            c["sources"].append({"url": url, "roles": ["problemset"], "as_of": ts, "note": "Shanghai University mirror of the regionals problem archive",
                                 "url_state": "dead", "url_checked": "2026-11-14"})
        touched.add(ser)
    if not dry:
        for sid, *_ in SETS: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], "add_found_lists_2026_11_14d.py (2026-11-14)")
    print(f"{len(SETS)} sets, {made} problems, series: {sorted(touched)}" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
