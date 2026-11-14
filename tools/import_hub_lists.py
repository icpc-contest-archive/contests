#!/usr/bin/env python3
"""Problem lists found through hub and history pages on 2026-11-14 (data/hub-lists-2026-11-14/lists.json):
the Northeast North America archive at RIT (cs.rit.edu/~icpc/prob.html: the preliminary sites' booklets,
one set per site), the BOSPRE home page, the Calgary ACPC pages, the KRSU judge, acm.ro's 2013 page, and
statement files that were already in the archive captures (Pakistan 2023, Tehran 2025, South Pacific 2021,
AMPPZ 2009's statistics page). Only entries read with high confidence, with a title for every problem and
one set per contest, are imported; letters are the booklet's own (several sites number their problems).
The BOSPRE booklets name problems by their short file names (equity, turtledraw, ...).

    python3 tools/import_hub_lists.py [--dry-run]
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

TOOL = "tools/import_hub_lists.py"; D = ROOT / "data" / "hub-lists-2026-11-14"


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    touched = set(); changed = []; made = 0
    for r in json.loads((D / "lists.json").read_text()):
        cid = r["contest_id"]; ser, c = where[cid]
        if (c.get("problems") or {}).get("set") or cid in sets: continue
        ps = r["problems"]
        if any(not p.get("letter") for p in ps) or len({p["letter"] for p in ps}) != len(ps): print("no letters, held:", cid); continue
        probs = []; letters = {}
        for p0 in ps:
            p = {"id": pid(None, cid, p0["letter"], p0["title"]), "name": p0["title"]}; probs.append(p); letters[p0["letter"]] = p["id"]; made += 1
        url = r["evidence_url"]; ts = r.get("wayback_timestamp")
        sets[cid] = {"id": cid, "count": len(probs), "contests": [{"contest": cid, "letters": letters}], "problems": probs,
                     "provenance": [f"letters and titles from {url}" + (f" (Wayback capture {ts})" if ts else "") + f", found via {r.get('hub_url') or 'the archive capture'}, read 2026-11-14 ({TOOL})"]}
        c["problems"] = {"set": cid}
        if not any(x["url"].rstrip("/") == url.rstrip("/") for x in c.setdefault("sources", [])):
            x = {"url": url, "roles": ["problemset"]}
            if ts: x["as_of"] = str(ts)
            x["url_state"] = "unknown"; x["url_checked"] = "2026-11-14"; c["sources"].append(x)
        touched.add(ser); changed.append(cid)
    if not dry:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], "import_hub_lists.py (2026-11-14)")
        (D / "changed.json").write_text(json.dumps({"sets": changed, "series": sorted(touched)}))
    print(f"{len(changed)} sets, {made} problems: {' '.join(changed)}" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
