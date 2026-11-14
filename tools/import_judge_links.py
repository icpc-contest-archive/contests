#!/usr/bin/env python3
"""Add online-judge links to problems from a matched list.

    python3 tools/import_judge_links.py <judge> <file> --date YYYY-MM-DD [--dry-run]

<file> has one line per problem set:  <set-id>|<key>=<pid without p->,...
where <key> is the problem's id on the judge, or <shown id>:<url id> when the judge's
address uses another id than the one it shows (PTA's ZOJ problem set). The lists in
data/judge-links-2026-11-14/ were matched by title against a judge's own problem list,
keeping only runs of neighbouring judge ids that cover most of one problem set.
A link a problem already has on that judge is left alone.
"""
import argparse, collections, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, load_sets  # noqa: E402
from mine_judge_links import SET_HEADER, Dumper, order_problem  # noqa: E402

URL = {"beecrowd": "https://judge.beecrowd.com/en/problems/view/{id}",
       "pintia": "https://pintia.cn/problem-sets/91827364500/exam/problems/type/7?problemSetProblemId={id}"}


def dump(doc: dict) -> str:
    doc = dict(doc)
    if "problems" in doc:
        doc["problems"] = [order_problem(p) for p in doc["problems"]]
    return SET_HEADER + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("judge"); ap.add_argument("file"); ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    sets = load_sets(); added = collections.Counter(); bad = []
    for line in Path(a.file).read_text().split():
        sid, rest = line.split("|")
        probs = {p["id"]: p for p in (sets.get(sid) or {}).get("problems") or []}
        for kv in rest.split(","):
            key, pid = kv.split("="); shown, _, uid = key.partition(":"); p = probs.get("p-" + pid)
            if p is None:
                bad.append(f"{sid} {kv}"); continue
            if any(j["judge"] == a.judge for j in p.get("judges") or []):
                continue
            p.setdefault("judges", []).append({"judge": a.judge, "url": URL[a.judge].format(id=uid or shown), "id": shown})
            added[sid] += 1
    if bad:
        print("unknown problems:", *bad, sep="\n  "); return 1
    if not a.dry_run:
        for sid in added:
            (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
    print(f"{a.judge}: {sum(added.values())} links in {len(added)} problem sets" + (" (dry run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
