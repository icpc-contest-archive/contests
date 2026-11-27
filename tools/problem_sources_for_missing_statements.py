#!/usr/bin/env python3
"""Make one judge address a source for every problem we hold no statement of (ruling of 2026-11-27).

The rule of 2026-11-23 stands: a judge link is a `problem` source when we hold a copy of it
(tools/problem_sources_from_judge_copies.py). This adds the gap that matters: a problem whose
statement we do not hold, in the archive or in any source of its contests, and that has no source of
its own yet, gets ONE of its judge links as a `problem` source of every contest that sat it. The
source shows as not captured until a top-up run fetches it (tools/make_topup_queues.py queues every
source without a copy). The problem's other judge links stay links.

Which link: the judges a plain fetch works on first, then closed judges whose link names a snapshot,
then judges that need a browser, then any other; the Live Archive is left to tools/pin_livearchive.py.
The address is the judge's statement file where the link names one (`statement_url`), else the page.

Builds the site into a scratch folder to know what is held (about a minute). --write to apply.
Safe to run again: a problem that has a source of its own is skipped.
"""
import contextlib
import io
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_site as B  # noqa: E402
from catalogue import add_source, dump_series, find_source, load_series, set_letters  # noqa: E402
from make_topup_queues import JUDGE_BROWSER, JUDGE_PLAIN, JUDGE_SKIP  # noqa: E402

NOTE = "the problem has no held statement: one judge address made a source, to be captured (ruling of 2026-11-27)"
NOTE_SET = "problems of the set have no held statement: the judge's statement file for the whole set made a source, to be captured (ruling of 2026-11-27)"
OUT = ROOT / "data" / "problem-sources-for-missing-statements-2026-11-27.json"


def main() -> int:
    write = "--write" in sys.argv
    with contextlib.redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory() as tmp:
        B.build(Path(tmp))
    registry = yaml.safe_load((ROOT / "judges.yaml").read_text())
    registry = registry["judges"] if isinstance(registry, dict) else registry
    closed = {j["id"] for j in registry if j.get("status") == "closed"} - set(JUDGE_SKIP)
    order = list(JUDGE_PLAIN) + sorted(closed) + list(JUDGE_BROWSER)
    rank = {j: i for i, j in enumerate(order)}
    series = load_series()
    where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    stats, touched, rows = Counter(), set(), []
    for sid, doc in B.SETS.items():
        members = [m for m in B.set_members(doc) if m in where and B.did_run(where[m][1]) and where[m][1].get("status") != "upcoming"]
        if not members:
            continue
        letter_of = {cid: {pid: L for L, pid in set_letters(doc, cid).items()} for cid in members}
        picks = []
        for p in doc.get("problems") or []:
            stats["problems"] += 1
            if B.problem_have(p, doc)["statement"] is True:
                stats["statement held"] += 1
                continue
            if B.material_sources(doc, p["id"]):
                stats["no statement, but the problem has a source of its own (not captured yet)"] += 1
                continue
            links = [j for j in p.get("judges") or [] if j.get("url")]
            if not links:
                stats["no statement and no judge link"] += 1
                continue
            usable = [j for j in links if j["judge"] not in JUDGE_SKIP and (j["judge"] not in closed or j.get("as_of"))]
            if not usable:
                stats["no statement, Live Archive link only"] += 1
                continue
            j = min(usable, key=lambda j: rank.get(j["judge"], len(order)))
            addr = j.get("statement_url") or j["url"]
            picks.append((p, j, addr))
        # a statement file that several problems of the set share is the set's file, not one problem's
        shared = {a for a, n in Counter(addr for _p, _j, addr in picks).items() if n > 1}
        for p, j, addr in picks:
            whole = addr in shared
            stats[f"source: {j['judge']}" + (" (a file of the whole set)" if whole else "")] += 1
            rows.append({"problem": p["id"], "name": p["name"], "set": sid, "judge": j["judge"], "url": addr,
                         "role": "problemset" if whole else "problem", "contests": members})
            for cid in members:
                letter = letter_of[cid].get(p["id"])
                if whole or (letter and not re.fullmatch(r"[A-Z0-9]{1,3}", str(letter))):
                    letter = None
                ser, c = where[cid]
                old = find_source(c, addr)
                if whole and old is not None:   # the set's file, filed as one problem's source: it is the set's
                    if "problem" in old["roles"] or "problemset" not in old["roles"]:
                        old["roles"] = ["problemset"] + [r for r in old["roles"] if r not in ("problem", "problemset")]
                        old.pop("problem", None)
                        stats["whole-set files refiled as the set's"] += 1
                        touched.add(ser)
                    continue
                _s, changed = add_source(c, addr, "problemset" if whole else "problem", judge=j["judge"],
                                         problem=str(letter) if letter else None,
                                         as_of=j.get("as_of") if j["judge"] in closed else None, note=NOTE_SET if whole else NOTE)
                if changed:
                    stats["sources added"] += 1
                    touched.add(ser)
    if write:
        for ser in sorted(touched):
            dump_series(ser, series[ser], "problem_sources_for_missing_statements.py")
        if rows and not OUT.exists():   # the record of the first run is kept
            json.dump({"generated": "2026-11-27", "about": __doc__.split("\n\n")[0], "rows": rows}, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"{len(rows)} problems, {stats['sources added']} sources in {len(touched)} series" + (" (written)" if write else " (dry run; --write to apply)"))
    for k, n in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"  {n:6d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
