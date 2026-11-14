#!/usr/bin/env python3
"""Collect the content-check verdicts of a run into the repo, one file per 20 batches.

  python3 tools/content_check_collect.py --run ../_content-check/run1 --name run-2026-11-15

Writes data/content-check/<name>/w<NN>.json ({contest: verdict}) and prints the state of the run.
A verdict that is not valid JSON, or does not have one entry per source of its pack, is reported
and left out (delete the file and its batch is done again).
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--name", required=True)
    args = ap.parse_args()
    run, out = Path(args.run).resolve(), ROOT / "data" / "content-check" / args.name
    out.mkdir(parents=True, exist_ok=True)
    batches = sorted((run / "batches").glob("b*.txt"))
    V, bad, todo, nsrc = Counter(), [], [], 0
    for w in range(0, len(batches), 20):
        coll = {}
        for b in batches[w:w + 20]:
            miss = 0
            for cid in b.read_text().split():
                p = run / cid / "verdict.json"
                if not p.exists():
                    miss += 1
                    continue
                try:
                    v = json.loads(p.read_text())
                    pack = json.loads((run / cid / "pack.json").read_text())
                    assert [s["n"] for s in v["sources"]] == [s["n"] for s in pack["sources"]], "sources do not match the pack"
                    for s, q in zip(v["sources"], pack["sources"]):
                        s["url"], s["was"] = q["url"], q["roles"]
                        if q.get("copy") and q["copy"].get("sha256"):
                            s["copy"] = q["copy"]["sha256"]
                        V[s["verdict"]] += 1
                        nsrc += 1
                    coll[cid] = v
                except Exception as e:  # noqa: BLE001
                    bad.append(f"{b.stem} {cid}: {type(e).__name__}: {e}")
                    miss += 1
            if miss:
                todo.append(f"{b.stem}({miss})")
        f = out / f"w{w // 20 + 1:02d}.json"
        text = json.dumps(coll, indent=0, ensure_ascii=False, sort_keys=True) + "\n"
        if coll and (not f.exists() or f.read_text() != text):
            f.write_text(text)
    print(f"{nsrc} sources read in verdicts: {dict(V)}")
    print(f"batches not finished: {len(todo)} of {len(batches)}" + (": " + " ".join(todo[:60]) if todo else ""))
    for x in bad[:20]:
        print("BAD", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
