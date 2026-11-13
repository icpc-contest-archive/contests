#!/usr/bin/env python3
"""Fill problem lists from QOJ problem names as mirrored by vjudge.net (OJ "QOJ").

vjudge gives each QOJ problem its source: the names of the QOJ contests it belongs to, run together.
A contest that has a qoj.ac/contest/<id> source and whose set lists no problems gets the QOJ problems
whose source contains the contest's catalogue name (warm-up/online/division variants excluded),
when 5-16 problems match and their QOJ numbers lie within a span of 40. No letters (vjudge does not
give the contest's letters). Everything else is reported.

usage: import_vjudge_qoj.py <harvest.json> --date YYYY-MM-DD [--dry-run]
"""
from __future__ import annotations
import argparse, collections, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import dump_set, pid  # noqa: E402

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("ACM-ICPC", "ICPC").replace("ACM ICPC", "ICPC")).strip().lower()

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("harvest"); ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    q = [(int(k), t.strip(), norm(s)) for k, (t, s) in json.loads(Path(a.harvest).read_text())["QOJ"].items() if k.isdigit()]
    series = load_series(); sets = load_sets()
    rep = collections.defaultdict(list); changed = set(); touched = set(); n = 0
    for ser, doc in sorted(series.items()):
        for c in doc["contests"]:
            sid = (c.get("problems") or {}).get("set"); s = sets.get(sid) if sid else None
            url = next((x["url"] for x in c.get("sources") or [] if "qoj.ac/contest/" in x["url"]), None)
            if not url or (s and s.get("problems")) or c.get("status") == "upcoming" or not c.get("name"): continue
            key = norm(c["name"]); line = f"{c['id']} ({c['name']}) {url}"
            hits = sorted((k, t) for k, t, src in q
                          if key in src and not re.match(r"\s*(,|-|\()?\s*(warm|online|div|practice|\(div)", src[src.index(key) + len(key):]))
            if not (5 <= len(hits) <= 16) or hits[-1][0] - hits[0][0] > 40:
                rep["no clean match (not applied)"].append(line + f": {len(hits)} problems matched"); continue
            if s and s.get("count") and len(hits) > s["count"]:
                rep["held back: more problems than the set's count"].append(line + f": {len(hits)} vs count {s['count']}"); continue
            if not s:
                if c["id"] in sets: rep["set id taken (skipped)"].append(line); continue
                sid = c["id"]; s = sets[sid] = {"id": sid, "contests": [{"contest": sid}], "provenance": []}
                c["problems"] = {"set": sid}; touched.add(ser)
            if len(s["contests"]) > 1:
                rep["held back: shared set"].append(line); continue
            if s.get("count") and len(hits) < s["count"]: s["complete"] = False
            elif not s.get("count"): s["count"] = len(hits)
            s["problems"] = [{"id": pid(None, sid, None, t), "name": t,
                              "judges": [{"judge": "qoj", "url": f"https://qoj.ac/problem/{k}", "id": str(k)}]} for k, t in hits]
            if len({p["id"] for p in s["problems"]}) != len(hits):
                del s["problems"]; rep["id clash (skipped)"].append(line); continue
            if not any(e.get("letters") for e in s["contests"]): s["letters"] = "unknown"
            s.setdefault("provenance", []).append(
                f"problem list from QOJ (problems {hits[0][0]}–{hits[-1][0]}, source '{c['name']}') as mirrored by vjudge.net, "
                f"read {a.date}; letters not known (tools/import_vjudge_qoj.py)")
            changed.add(sid); n += len(hits); rep["problems created"].append(line + f": {len(hits)}")
    if not a.dry_run:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump_set(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], f"import_vjudge_qoj.py ({a.date})")
        lines = [f"# QOJ problem lists via vjudge — {a.date}", "", f"- problems created: {n}", ""]
        for k in sorted(rep): lines += [f"## {k} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
        (ROOT / "reports" / f"vjudge-qoj-{a.date}.md").write_text("\n".join(lines))
    print({k: len(v) for k, v in rep.items()}, "new", n)
    return 0

if __name__ == "__main__":
    sys.exit(main())
