#!/usr/bin/env python3
"""Fill problem lists from Codeforces gym problem names as mirrored by vjudge.net (OJ "Gym").

A contest that has a codeforces.com/gym/<id> source and whose set lists no problems gets the gym's
problems (letters from the gym, judge link per problem). Held back: gyms shared by several
contests, gyms whose list is larger than the set's count, gyms whose vjudge name says it is a
merged/extended/training set, contests with several gyms that disagree.

usage: import_vjudge_gym.py <harvest.json> --date YYYY-MM-DD [--dry-run]
"""
from __future__ import annotations
import argparse, collections, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import dump_set, norm_title, pid  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("harvest"); ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    gyms = collections.defaultdict(dict); names = {}
    for k, (title, src) in json.loads(Path(a.harvest).read_text())["Gym"].items():
        m = re.match(r"(\d{6})([A-Z]\d?|\d+)$", k)
        if m: gyms[m.group(1)][m.group(2)] = title.strip(); names[m.group(1)] = src
    series = load_series(); sets = load_sets()
    use = collections.defaultdict(list)
    for ser, doc in series.items():
        for c in doc["contests"]:
            for s in c.get("sources") or []:
                m = re.search(r"codeforces\.com/gym/(\d+)", s["url"])
                if m and all(x["id"] != c["id"] for _, x in use[m.group(1)]): use[m.group(1)].append((ser, c))
    per = collections.defaultdict(list)
    for g, cs in use.items():
        for ser, c in cs:
            if g not in per[c["id"]]: per[c["id"]].append(g)
    rep = collections.defaultdict(list); changed = set(); touched = set(); n = 0; done = set()
    for g, cs in sorted(use.items()):
        for ser, c in cs:
            cid = c["id"]
            if cid in done or c.get("status") == "upcoming": continue
            sid = (c.get("problems") or {}).get("set"); s = sets.get(sid) if sid else None
            if s and s.get("problems"): continue
            line = f"{cid} <- gym {g} '{names.get(g, '?')}'"
            if g not in gyms: rep["gym not on vjudge"].append(line); continue
            probs = gyms[g]; line += f": {len(probs)} problems"
            if len(cs) > 1: rep["held back: gym is a source of several contests"].append(line + " (" + ", ".join(x["id"] for _, x in cs) + ")"); continue
            others = [x for x in per[cid] if x != g and x in gyms]
            if any({norm_title(t) for t in gyms[x].values()} != {norm_title(t) for t in probs.values()} for x in others):
                rep["held back: contest has several gyms with different lists"].append(line + " vs " + ", ".join(others)); continue
            if re.search(r"extended|merged|\+|training|selected|div\.? ?2|deprecated", names.get(g, ""), re.I):
                rep["held back: gym name says extended/merged/division"].append(line); continue
            if s and s.get("count") and len(probs) > s["count"]:
                rep["held back: gym lists more problems than the set's count"].append(line + f" (count {s['count']})"); continue
            if len(probs) < 3: rep["held back: fewer than 3 problems"].append(line); continue
            if not s:
                if cid in sets: rep["set id taken (skipped)"].append(line); continue
                sid = cid; s = sets[sid] = {"id": sid, "contests": [{"contest": cid}], "provenance": []}
                c["problems"] = {"set": sid}; touched.add(ser)
            if s.get("count") and len(probs) < s["count"]: s["complete"] = False
            elif not s.get("count"): s["count"] = len(probs)
            rows = []; letters = {}
            for L, t in sorted(probs.items(), key=lambda x: (len(x[0]), x[0])):
                i = pid(None, sid, L, t)
                rows.append({"id": i, "name": t, "judges": [{"judge": "codeforces", "url": f"https://codeforces.com/gym/{g}/problem/{L}", "id": f"{g}/{L}"}]})
                letters[L] = i
            if len({r["id"] for r in rows}) != len(rows): rep["id clash (skipped)"].append(line); continue
            e = next((e for e in s["contests"] if e["contest"] == cid), None)
            if e is None: e = {"contest": cid}; s["contests"].append(e)
            e["letters"] = letters; s["problems"] = rows; s.pop("letters", None) if s.get("letters") == "unknown" else None
            s.setdefault("provenance", []).append(
                f"problem list from Codeforces gym {g} ('{names.get(g, '')}') as mirrored by vjudge.net, read {a.date} "
                f"(tools/import_vjudge_gym.py)")
            changed.add(sid); done.add(cid); n += len(rows); rep["problems created"].append(line)
    if not a.dry_run:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump_set(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], f"import_vjudge_gym.py ({a.date})")
        lines = [f"# Codeforces gym problem lists via vjudge — {a.date}", "", f"- problems created: {n}", ""]
        for k in sorted(rep): lines += [f"## {k} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
        (ROOT / "reports" / f"vjudge-gym-{a.date}.md").write_text("\n".join(lines))
    print({k: len(v) for k, v in rep.items()}, "new", n)
    return 0

if __name__ == "__main__":
    sys.exit(main())
