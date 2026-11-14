#!/usr/bin/env python3
"""Norway's national championship (NM i programmering) 2000 and 2001: problem lists from the organisers'
pages at heim.ifi.uio.no/~db/nm-i-programmering/, as held by Common Crawl's 2012 crawl (CC-MAIN-2012;
the Wayback Machine has the index pages but not the files). 2000: titles from the jury-comments section
of the index page, statements in nm2000/oppgaver.pdf. 2001: the "Oppgavene" table of the index page.
Read 2026-11-14.

    python3 tools/add_found_lists_2026_11_14e.py [--dry-run]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

TOOL = "tools/add_found_lists_2026_11_14e.py"; B = "http://heim.ifi.uio.no/~db/nm-i-programmering/"
SETS = [("norway-2000", B + "nm2000/oppgaver.pdf", "Traffic planning;A model railroad;Comment removal;R.Ø.L.P.;A fair jury;Radio direction finder;Returning books"),
        ("norway-2001", B + "nm2001/", "Backward numbers;Christmas presents;Tournament ranking;Directed mazes;Connecting islands;A language for constants;Bridge placements;Request for permission")]


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); ser = series["norway"]; con = {c["id"]: c for c in ser["contests"]}
    for sid, url, titles in SETS:
        assert sid not in sets
        probs = []; letters = {}
        for i, t in enumerate(titles.split(";")):
            l = chr(65 + i); p = {"id": pid(None, sid, l, t), "name": t}; probs.append(p); letters[l] = p["id"]
        sets[sid] = {"id": sid, "count": len(probs), "contests": [{"contest": sid, "letters": letters}], "problems": probs,
                     "provenance": [f"letters and titles from the organisers' pages under {B} as held by Common Crawl (CC-MAIN-2012), read 2026-11-14 ({TOOL})"]}
        c = con[sid]; c["problems"] = {"set": sid}
        if not any(x["url"] == url for x in c["sources"]):
            c["sources"].append({"url": url, "roles": ["problemset"], "note": "not live; held by Common Crawl's 2012 crawl together with test data and jury solutions",
                                 "url_state": "dead", "url_checked": "2026-11-14"})
    if not dry:
        for sid, *_ in SETS: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        dump_series("norway", ser, "add_found_lists_2026_11_14e.py (2026-11-14)")
    print("2 sets, 15 problems" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
