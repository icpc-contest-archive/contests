#!/usr/bin/env python3
"""Make a problem's page on an online judge a source of its contest when we hold a copy of it.

Ruled 2026-11-23: a page we have saved is a source. For every problem of every set, each of its
judge links whose address we hold a good copy of (the file `statement_url` names where the judge
keeps the statement apart from the page, else the page) becomes a `problem` source of every contest
that used the set:  roles [problem], judge, problem: <the letter it had there, when the set records
it>, contains [statement], and `as_of` when our copy comes from the Wayback Machine.

Only held copies (option 1 of the ruling). A judge link we hold no copy of stays a link - whether
every judge link should be a source is an open question (reports/open-questions.md in the project).
Safe to run again: it adds what is missing and changes nothing else.

Builds the site into a scratch folder to know what is held (about a minute). --write to apply.
"""
import contextlib
import io
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_site as B  # noqa: E402
from catalogue import add_source, dump_series, find_source, load_series, set_letters  # noqa: E402


def good_copy(url: str):
    """(held, as_of): do we hold a good copy of the address, and the snapshot time when every good copy is from Wayback."""
    L = B.RES.locs.get(B.lid(url))
    good = [(R.get("via") or c.get("source") or "live", ts) for ts, R in ((L or {}).get("resources") or {}).items()
            for c in R.get("captures") or [] if c.get("sha256") and not c.get("caveat")]
    if not good:
        return False, None
    if all(via == "wayback" for via, _ts in good):
        return True, sorted(ts for _via, ts in good if ts and ts != "unknown")[0] if any(ts and ts != "unknown" for _v, ts in good) else None
    return True, None


def main() -> int:
    write = "--write" in sys.argv
    with contextlib.redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory() as tmp:
        B.build(Path(tmp))
    series = load_series()
    where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    stats, touched = Counter(), set()
    for sid, doc in B.SETS.items():
        members = [m["contest"] for m in doc.get("contests") or [] if m["contest"] in where]
        letter_of = {cid: {pid: L for L, pid in set_letters(doc, cid).items()} for cid in members}
        for p in doc.get("problems") or []:
            for j in p.get("judges") or []:
                addr = j.get("statement_url") or j.get("url")
                if not addr:
                    continue
                held, as_of = good_copy(addr)
                if not held:
                    continue
                stats["held copies of a problem's statement"] += 1
                for cid in members:
                    # the letter the problem had in this contest, when the set records it (the address
                    # ties the source to its problem either way: it is one of the problem's judge links)
                    letter = letter_of[cid].get(p["id"])
                    if letter and not re.fullmatch(r"[A-Z0-9]{1,3}", str(letter)):
                        letter = None   # a division label ("A/C"), not a letter: `problem:` takes a letter
                    ser, c = where[cid]
                    if find_source(c, addr) is not None and "problem" in find_source(c, addr)["roles"]:
                        stats["already a source"] += 1
                        continue
                    add_source(c, addr, "problem", judge=j["judge"], problem=str(letter) if letter else None, contains=["statement"], as_of=as_of)
                    stats[f"source added: {j['judge']}"] += 1
                    if not letter:
                        stats["added without a letter (the contest's lettering is not recorded)"] += 1
                    touched.add(ser)
    if write:
        for ser in sorted(touched):
            dump_series(ser, series[ser], "problem_sources_from_judge_copies.py")
    total = sum(n for k, n in stats.items() if k.startswith("source added"))
    print(f"{total} sources in {len(touched)} series" + (" (written)" if write else " (dry run; --write to apply)"))
    for k, n in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
