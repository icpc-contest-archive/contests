#!/usr/bin/env python3
"""Draw the independent check's sample from a description run: about --rate of the descriptions
of the given batches, spread over the kinds of document, in files of ten for a checker each.

  python3 tools/describe_check_sample.py --run ../_describe/run1 --batches 1-40 --name c01 [--rate 0.03]

Writes <run>/check/<name>-sample-<i>.json. A checker (tools/describe_check_agent.md) writes
<name>-found-<i>.json beside it; tools/describe_fix_agent.md applies the findings.
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--batches", required=True, help="a range of batch numbers, e.g. 1-40")
    ap.add_argument("--name", required=True)
    ap.add_argument("--rate", type=float, default=0.03)
    a = ap.parse_args()
    run = Path(a.run).resolve()
    lo, hi = (int(x) for x in a.batches.split("-"))
    pool = defaultdict(list)
    for b in range(lo, hi + 1):
        f = run / "batches" / f"b{b:03d}.txt"
        for cid in (f.read_text().split() if f.exists() else []):
            rp = run / cid / "result.json"
            if not rp.exists():
                continue
            res, pack = json.loads(rp.read_text()), json.loads((run / cid / "pack.json").read_text())
            for s, q in zip(res["sources"], pack["sources"]):
                if s.get("description"):
                    pool[(s.get("roles") or ["none"])[0]].append(
                        {"contest": cid, "n": q["n"], "url": q["url"], "roles": s.get("roles"), "copy_file": q["copy"]["file"],
                         "digest": f"{cid}/{q['copy']['digest']}", "document": s.get("document"), "description": s["description"]})
    total = sum(len(v) for v in pool.values())
    want = max(10, round(total * a.rate / 10) * 10)
    rnd = random.Random(a.name)
    for v in pool.values():
        rnd.shuffle(v)
    pick, kinds = [], sorted(pool, key=lambda k: -len(pool[k]))
    while len(pick) < want and any(pool.values()):
        for k in kinds:                       # round robin over the kinds, so rare kinds are in every sample
            if pool[k] and len(pick) < want:
                pick.append(pool[k].pop())
    rnd.shuffle(pick)
    (run / "check").mkdir(exist_ok=True)
    files = max(1, len(pick) // 10)
    for i in range(files):
        (run / "check" / f"{a.name}-sample-{i + 1}.json").write_text(json.dumps(pick[i::files], ensure_ascii=False, indent=1))
    print(f"{total} descriptions in batches {a.batches}; {len(pick)} drawn into {files} files: {a.name}-sample-1..{files}.json")


if __name__ == "__main__":
    main()
