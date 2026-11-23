#!/usr/bin/env python3
"""Hand out the next piece of work of a description run, and say how far the run is.

  python3 tools/describe_next.py --run ../_describe/run1 --claim L03   -> "WRITE b123" | "REVISE b123" | "WAIT" | "DONE"
  python3 tools/describe_next.py --run ../_describe/run1 --status

A batch is written when every contest of it has a result.json, revised when every one has a
revision.json. A piece of work is claimed by an atomic mkdir under <run>/claims/, so several lanes
can ask at once. Revising a written batch comes before writing a new one, and a lane is never
given a batch it wrote itself to revise. A claim that is 25
minutes old and still not done is given out again (its agent died).
"""
import argparse
import json
import os
import time
from pathlib import Path

STALE = 25 * 60


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--claim")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--last", type=int, default=10 ** 6)
    a = ap.parse_args()
    run = Path(a.run).resolve()
    claims = run / "claims"
    claims.mkdir(exist_ok=True)
    batches = []
    for f in sorted((run / "batches").glob("b*.txt")):
        cs = f.read_text().split()
        if cs and a.first <= int(f.stem[1:]) <= a.last:
            batches.append((f.stem, cs))
    state = {}
    for b, cs in batches:
        w = all((run / c / "result.json").exists() for c in cs)
        r = w and all((run / c / "revision.json").exists() for c in cs)
        state[b] = "revised" if r else "written" if w else "new"
    if a.status:
        n = {k: sum(1 for v in state.values() if v == k) for k in ("new", "written", "revised")}
        now = time.time()
        live = sum(1 for d in claims.iterdir() if now - d.stat().st_mtime < STALE and state.get(d.name.split(".")[0]) != "revised"
                   and not (d.name.endswith(".write") and state.get(d.name.split(".")[0]) == "written"))
        srcs = 0
        for b, cs in batches:
            if state[b] == "revised":
                for c in cs:
                    srcs += sum(1 for s in json.loads((run / c / "result.json").read_text())["sources"] if s.get("description"))
        print(json.dumps({"batches": len(batches), **n, "claims in progress": live, "descriptions revised": srcs}))
        return

    def take(b: str, kind: str) -> bool:
        d = claims / f"{b}.{kind}"
        try:
            d.mkdir()
            (d / "by").write_text(a.claim)
            return True
        except FileExistsError:
            if time.time() - d.stat().st_mtime > STALE:
                try:                                    # given out again: whoever touches it first has it
                    os.utime(d, None)
                    (d / "by").write_text(a.claim)
                    return True
                except OSError:
                    return False
            return False

    def wrote(b: str) -> bool:
        """The second reader must not be the first one: a lane does not revise a batch it wrote."""
        by = claims / f"{b}.write" / "by"
        return by.exists() and by.read_text() == a.claim

    def settled(cs: list) -> bool:
        """The first reader checks its result.json after writing it and may still correct it: a batch
        is handed to the second reader only once its results have been left alone for three minutes."""
        return all(time.time() - (run / c / "result.json").stat().st_mtime > 180 for c in cs)

    for b, cs in batches:
        if state[b] == "written" and not wrote(b) and settled(cs) and take(b, "revise"):
            print("REVISE", b)
            return
    for b, _cs in batches:
        if state[b] == "new" and take(b, "write"):
            print("WRITE", b)
            return
    print("DONE" if all(v == "revised" for v in state.values()) else "WAIT")


if __name__ == "__main__":
    main()
