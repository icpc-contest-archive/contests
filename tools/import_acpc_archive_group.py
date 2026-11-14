#!/usr/bin/env python3
"""Problem lists from the Codeforces group "ACPC Scientific Committee Archive"
(https://codeforces.com/group/Rilx5irOux), read 2026-11-14 with a logged-in account that joined as a
spectator (the group is private; joining was granted at once).

The group holds the ACPC committee's copies of the Arab and African nationals and of ACPC itself, 116
contests in all; data/acpc-archive-group-2026-11-14/lists-*.txt has the ones matched to a catalogue
contest without a list: `contest id|group contest id|name in the group|A~title ; B~title ; ...`.
Matching is by the contest's name and year in the group, checked against the catalogue date where
the group shows a date (mirrors run a few days after the contest). Not imported: qualification days,
kickoffs, girls' and teens' contests, single-university contests, and three whose acronym does not say
which country they are (AOCPC 2023, AOCPC 2024, AlCPC 2023).

    python3 tools/import_acpc_archive_group.py [--dry-run]
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

TOOL = "tools/import_acpc_archive_group.py"; G = "https://codeforces.com/group/Rilx5irOux/contest/"
D = ROOT / "data" / "acpc-archive-group-2026-11-14"


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    touched = set(); changed = []; made = 0
    for f in sorted(D.glob("lists-*.txt")):
        for line in f.read_text().splitlines():
            cid, gid, gname, lst = line.split("|", 3); ser, c = where[cid]
            if (c.get("problems") or {}).get("set") or cid in sets: print("has a set, skipped:", cid); continue
            probs = []; letters = {}
            for row in lst.split(" ; "):
                l, t = row.split("~", 1)
                p = {"id": pid(None, cid, l, t), "name": t, "judges": [{"judge": "codeforces", "url": f"{G}{gid}/problem/{l}", "id": f"{gid}{l}"}]}
                probs.append(p); letters[l] = p["id"]; made += 1
            sets[cid] = {"id": cid, "count": len(probs), "contests": [{"contest": cid, "letters": letters}], "problems": probs,
                         "provenance": [f"letters and titles from '{gname}' in the Codeforces group ACPC Scientific Committee Archive ({G}{gid}), read 2026-11-14 ({TOOL})"]}
            c["problems"] = {"set": cid}
            c.setdefault("sources", []).append({"url": f"{G}{gid}", "roles": ["problemset"], "judge": "codeforces",
                                                "note": f"'{gname}' in the private group ACPC Scientific Committee Archive (login and group membership needed)",
                                                "url_state": "live", "url_checked": "2026-11-14"})
            touched.add(ser); changed.append(cid)
    if not dry:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], "import_acpc_archive_group.py (2026-11-14)")
        (D / "changed.json").write_text(json.dumps({"sets": changed, "series": sorted(touched)}))
    print(f"{len(changed)} sets, {made} problems, {len(touched)} series" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
