#!/usr/bin/env python3
"""Problem lists read on the regional platforms on 2026-11-14 (data/platform-lists-2026-11-14/lists.json):
CodeChef (Amritapuri and Chennai 2024, the on-site rounds ICPCAMROS24 and ICPCCHNOS24), CodeMarshal via the
Wayback Machine (Dhaka 2019 and 2020, Kanpur 2020 main rounds; the site is down), BAPS OJ (Dhaka 2023; the
public list has A-F and H-K, no G) and the Ministry of Education NCPC past-problems archive at
ncpc.ntnu.edu.tw (Group A finals of 2012 and 2013). CodeChef prefixes its titles with the letter ("A - ...");
the prefix is dropped. 2012 H prints as "Gap Verication" in the PDF text (a lost fi ligature) and is
recorded as "Gap Verification".

    python3 tools/import_platform_lists.py [--dry-run]
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

TOOL = "tools/import_platform_lists.py"; D = ROOT / "data" / "platform-lists-2026-11-14"
FIX = {"Gap Verication": "Gap Verification"}


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    touched = set(); changed = []; made = 0
    for r in json.loads((D / "lists.json").read_text()):
        cid = r["contest_id"]; ser, c = where[cid]
        if (c.get("problems") or {}).get("set") or cid in sets: print("has a set, skipped:", cid); continue
        probs = []; letters = {}; cc = "codechef.com" in r["contest_url"]
        for p0 in r["problems"]:
            l = p0["letter"]; t = FIX.get(p0["title"], re.sub(rf"^{l} - ", "", p0["title"]))
            p = {"id": pid(None, cid, l, t), "name": t}
            if cc: p["judges"] = [{"judge": "codechef", "url": p0["problem_url"], "id": p0["code"]}]
            probs.append(p); letters[l] = p["id"]; made += 1
        s = {"id": cid, "count": len(probs), "contests": [{"contest": cid, "letters": letters}], "problems": probs,
             "provenance": [f"letters and titles from {r['platform']}, {r['contest_url']}, read 2026-11-14 ({TOOL})"]}
        if cid == "dhaka-2023": s["complete"] = False; s["count"] = 11; s["provenance"].append("the platform lists A-F and H-K; G is not shown")
        sets[cid] = s; c["problems"] = {"set": cid}
        if not any(x["url"].rstrip("/") == r["contest_url"].rstrip("/") for x in c.setdefault("sources", [])):
            x = {"url": r["contest_url"], "roles": ["problemset"]}
            if cc: x["judge"] = "codechef"
            dead = "codemarshal" in r["contest_url"]
            if dead: x["note"] = "site down; read from the Wayback Machine"
            x["url_state"] = "dead" if dead else "live"; x["url_checked"] = "2026-11-14"; c["sources"].append(x)
        touched.add(ser); changed.append(cid)
    if not dry:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], "import_platform_lists.py (2026-11-14)")
        (D / "changed.json").write_text(json.dumps({"sets": changed, "series": sorted(touched)}))
    print(f"{len(changed)} sets, {made} problems" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
