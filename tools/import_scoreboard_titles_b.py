#!/usr/bin/env python3
"""Problem lists read off scoreboards already in the archive whose header prints the titles
(data/scoreboard-titles-2026-11-14b/titles.json; second pass, 2026-11-14).

A contest whose titles are those of an existing set of the same season (every title found there) joins
that set with its own letter map: the NERC subregionals of 2021 and 2022 that sat another
subregional's problems, a Kattis division scoreboard, a Codeforces gym already used. Otherwise a new
set is made from the header. Nothing is guessed: titles are the header's, letters the columns'.

    python3 tools/import_scoreboard_titles_b.py [--dry-run]
"""
import json, re, sys, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

TOOL = "tools/import_scoreboard_titles_b.py"
# five NERC subregionals of 2021 print one and the same header: a set of its own, not Armenia's
SHARED = {"armenia-2021": ("nerc-shared-2021", "NERC 2021: the set shared by the Armenia, Azerbaijan, Kazakhstan, Taurida and Ural subregionals")}
# header prints one title twice (B and I): held
SKIP = {"azerbaijan-2022", "georgia-2022"}


def norm(s): return re.sub(r"[^\w]+", "", unicodedata.normalize("NFKC", s).casefold())


def main() -> int:
    dry = "--dry-run" in sys.argv
    rows = json.loads((ROOT / "data" / "scoreboard-titles-2026-11-14b" / "titles.json").read_text())
    series = load_series(); sets = load_sets(); where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    touched = set(); changed = set(); made = joined = new = 0
    for r in rows:
        cid = r["contest_id"]; ser, c = where[cid]; titles = r["titles"]; year = cid.rsplit("-", 1)[1]
        if cid in SKIP: print("held:", cid); continue
        if (c.get("problems") or {}).get("set"): print("has a set, skipped:", cid); continue
        if r["count"] != len(titles): print("count differs, skipped:", cid); continue
        want = {norm(t) for t in titles.values()}; target = None
        for s in sets.values():
            if not s["id"].endswith(year) or not s.get("problems"): continue
            have = {norm(p["name"]): p["id"] for p in s["problems"]}
            if want <= set(have): target = (s, have); break
        src = r["source_url"]
        if target:
            s, have = target
            s["contests"].append({"contest": cid, "letters": {l: have[norm(t)] for l, t in sorted(titles.items())}})
            if s.get("letters") == "unknown": del s["letters"]
            s.setdefault("provenance", []).append(f"{cid} sat this set: its scoreboard header ({src}) prints these titles ({TOOL}, 2026-11-14)")
            c["problems"] = {"set": s["id"]}; joined += 1; print(f"{cid} -> {s['id']}")
        else:
            probs = []; letters = {}
            for l, t in sorted(titles.items()):
                p = {"id": pid(None, cid, l, t), "name": t}; probs.append(p); letters[l] = p["id"]; made += 1
            sid, name = SHARED.get(cid, (cid, None))
            for p in probs: p["id"] = pid(None, sid, next(l for l, q in letters.items() if q == p["id"]), p["name"]) if sid != cid else p["id"]
            letters = {l: p["id"] for (l, _), p in zip(sorted(titles.items()), probs)}
            s = sets[sid] = {"id": sid, **({"name": name} if name else {}), "count": len(probs), "contests": [{"contest": cid, "letters": letters}], "problems": probs,
                             "provenance": [f"letters and titles from the scoreboard header, {src} (archive capture), read 2026-11-14 ({TOOL})"]}
            c["problems"] = {"set": sid}; new += 1; print(f"{cid}: new set, {len(probs)} problems")
        changed.add(s["id"]); touched.add(ser)
    if not dry:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], "import_scoreboard_titles_b.py (2026-11-14)")
        (ROOT / "data" / "scoreboard-titles-2026-11-14b" / "changed.json").write_text(json.dumps({"sets": sorted(changed), "series": sorted(touched)}))
    print(f"{joined} joined, {new} new sets, {made} problems created" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
