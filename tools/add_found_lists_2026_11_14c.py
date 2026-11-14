#!/usr/bin/env python3
"""Problem lists read from the organisers' own published files on 2026-11-14 (third batch).

  kanpur-2022, mathura-2022  one contest on 2023-04-09: the set's cover reads "Mathura - Kanpur Contest
        Problems (11 Problems) 09th April, 2023" (kanpur.indiaicpc.in/docs/problems_2022.pdf); shared set.
  kanpur-2023   kanpur.indiaicpc.in/docs/problem-set-2023.pdf (PDF created 2023-12-22; A-I).
  kanpur-2024   kanpur.indiaicpc.in/docs/Problem_Set2024.pdf, "2024 ICPC Kanpur Regional Problem Set" (A-L).
  awc-2024      wc.indiaicpc.in/problem_set_2024_25.pdf, "2025 ICPC Asia West Finals Problemset": the
        2024-25 season's final, held 2025-03-08 (the file was already linked in September 2025, before
        the 2026 final).
  sweden-1997..1999  the Lund pages of the Swedish championship, fileadmin.cs.lth.se/contest/c97, c98,
        c99: "Uppgift A - ..." lists with the result table (A-G each). c96 has the 1996 result table
        (columns A-G) but no titles: the page is added as a source only.

    python3 tools/add_found_lists_2026_11_14c.py [--dry-run]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

TOOL = "tools/add_found_lists_2026_11_14c.py"
K = "https://kanpur.indiaicpc.in/docs/"; L = "https://fileadmin.cs.lth.se/contest/"
# set id, name or None, members, source url, roles, titles in letter order
SETS = [
    ("kanpur-mathura-2022", "Kanpur and Mathura-Kanpur 2022 (one contest, 2023-04-09)", ["kanpur-2022", "mathura-2022"], K + "problems_2022.pdf", ["problemset"],
     "Binary Digit Escaping;Little Seherish and Tree;Magic vs Geometry;K-th Number;Diameter Division;Robot and the Doors;Marriage vs Gym;Factorization Game;Boring Mode;Road Trip;Gotta Catch 'Em All"),
    ("kanpur-2023", None, ["kanpur-2023"], K + "problem-set-2023.pdf", ["problemset"],
     "End of Evolution;Generalized Collatz Conjecture;Lost Luggage;Mod Messages;Pairwise Perfect;Palindromic Polygon;Protracted Parenthesization;Slothful Secretary;Swirly Sort"),
    ("kanpur-2024", None, ["kanpur-2024"], K + "Problem_Set2024.pdf", ["problemset"],
     "AB to C;Bob Learns to Read;Check Good;Hard Counting Problem;Largest K;Lexicographic Raffle;Majority Voters;P to Q;Prime Difference Graph;Score Sum;Stalin Sort;Yet Another MST Problem"),
    ("awc-2024", None, ["awc-2024"], "https://wc.indiaicpc.in/problem_set_2024_25.pdf", ["problemset"],
     "Construct uwu;Counting Distance Arrays;Counting is Fun;Deletable Subarrays;Greedy Prices;Jagged Operations;LCM on Range;Majority Graph;Suffix Array;Tri-Knight;Unique Subsequences Counting"),
    ("sweden-1997", None, ["sweden-1997"], L + "c97/", ["web", "scoreboard", "problemset"], "Kanon;Dna;FFT;Press;Sabotage;Frim;Fnutt"),
    ("sweden-1998", None, ["sweden-1998"], L + "c98/", ["web", "scoreboard", "problemset"], "Souvenir;Ekvation;MEME;Valuta;Simuleringsproblematik;Rektor;Exotica"),
    ("sweden-1999", None, ["sweden-1999"], L + "c99/", ["web", "scoreboard", "problemset"], "Volleyboll;Virus;Jaktstart;Matrix;Play Ball;Korsord;Stitching"),
]
EXTRA = {"sweden-1996": (L + "c96/", ["web", "scoreboard"], "result table with columns A-G (seven problems); no titles on the page")}


def add_source(c, url, roles, note=None):
    have = {x["url"].rstrip("/") for x in c.setdefault("sources", [])}
    if url.rstrip("/") in have: return 0
    x = {"url": url, "roles": roles}
    if note: x["note"] = note
    x["url_state"] = "live"; x["url_checked"] = "2026-11-14"; c["sources"].append(x); return 1


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    touched = set(); made = 0
    for sid, name, members, url, roles, titles in SETS:
        assert sid not in sets, sid
        probs = []; letters = {}
        for i, t in enumerate(titles.split(";")):
            l = chr(65 + i); p = {"id": pid(None, sid, l, t), "name": t}; probs.append(p); letters[l] = p["id"]; made += 1
        s = {"id": sid}
        if name: s["name"] = name
        s.update({"count": len(probs), "contests": [], "problems": probs,
                  "provenance": [f"letters and titles from {url}, read 2026-11-14 ({TOOL})"]})
        for cid in members:
            ser, c = where[cid]; assert not (c.get("problems") or {}).get("set"), cid
            s["contests"].append({"contest": cid, "letters": dict(letters)}); c["problems"] = {"set": sid}
            add_source(c, url, roles); touched.add(ser)
        sets[sid] = s
    for cid, (url, roles, note) in EXTRA.items():
        ser, c = where[cid]; add_source(c, url, roles, note); touched.add(ser)
    if not dry:
        for sid, *_ in SETS: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], "add_found_lists_2026_11_14c.py (2026-11-14)")
    print(f"{len(SETS)} sets, {made} problems, series touched: {sorted(touched)}" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
