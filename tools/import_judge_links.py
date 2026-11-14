#!/usr/bin/env python3
"""Add online-judge links to problems from a matched list.

    python3 tools/import_judge_links.py <judge> <file> --date YYYY-MM-DD [--dry-run]

<file> has one line per problem set:  <set-id>|<key>=<start of the pid, without p->,...
(HackerRank lines: <set-id>|<HackerRank contest>|<challenge>=...) where <key> is the problem's id on the judge, or <shown id>:<url id> when the judge's
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
       "pintia": "https://pintia.cn/problem-sets/91827364500/exam/problems/type/7?problemSetProblemId={id}",
       "bailian": "http://bailian.openjudge.cn/practice/{id}", "poj": "http://poj.org/problem?id={id}",
       "luogu": "https://www.luogu.com.cn/problem/{id}", "loj": "https://loj.ac/p/{id}",
       "vnoj": "https://oj.vnoi.info/problem/{id}", "tlx": "https://tlx.toki.id/problems/{id}",
       "hackerrank": "https://www.hackerrank.com/contests/{id}"}


def expand(judge: str, sid: str, key: str, extra: str) -> tuple[str, str]:
    """(id shown, id in the address) for a key of the list file."""
    shown, _, uid = key.partition(":")
    if judge == "tlx":          # key is the letter; the problem set is icpc-jakarta-<year>
        return f"icpc-{sid}-{key}", f"icpc-{sid}/{key}"
    if judge == "vnoj" and len(key) <= 2:   # key is the letter; icpc<yy>_regional_<x> / icpc<yy>_national_<x>
        code = f"icpc{sid[-2:]}_{'national' if 'national' in sid else 'regional'}_{key}"
        return code, code
    if judge == "hackerrank":   # the line names the HackerRank contest; key is the challenge
        return key, f"{extra}/challenges/{key}"
    return shown, uid or shown


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
        sid, *extra, rest = line.split("|")
        probs = (sets.get(sid) or {}).get("problems") or []
        for kv in rest.split(","):
            key, pid = kv.rsplit("=", 1); hit = [p for p in probs if p["id"].startswith("p-" + pid)]
            if len(hit) != 1:
                bad.append(f"{sid} {kv}"); continue
            p = hit[0]
            if any(j["judge"] == a.judge for j in p.get("judges") or []):
                continue
            shown, uid = expand(a.judge, sid, key, extra[0] if extra else "")
            p.setdefault("judges", []).append({"judge": a.judge, "url": URL[a.judge].format(id=uid), "id": shown})
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
