#!/usr/bin/env python3
"""Put the Live Archive's problem links back on the Live Archive (ruled 2026-11-22).

The catalogue had every Live Archive link on onlinejudge.org, with the Live Archive's internal problem
number. onlinejudge.org is the UVa Online Judge: the same numbers are other problems there. The Live
Archive itself (icpcarchive.ecs.baylor.edu) is gone for good, so its links point at its old address and
are opened from the Wayback Machine. They are not mapped to UVa: where UVa has a problem it is not
exactly the same.

A link is a real UVa link (and becomes `judge: uva`) when the pair (internal number, problem number) is
on a UVa contest page we hold (the Dhaka regionals); every other link is the Live Archive's and gets its
host put right. The contest pages on onlinejudge.org that were tagged livearchive become `judge: uva`.

Edits the files as text (no reformatting). Run once from the contests repository root; --write to apply.
"""
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT.parent / "archive"
OLD = "https://onlinejudge.org/index.php?option=com_onlinejudge&Itemid=8&page=show_problem&problem="
NEW = "https://icpcarchive.ecs.baylor.edu/index.php?option=com_onlinejudge&Itemid=8&page=show_problem&problem="


def uva_pairs() -> dict:
    pairs = {}
    for x in json.loads((ARCHIVE / "index.json").read_text())["captures"]:
        if x["artifact"] in ("judge-livearchive", "judge-uva") and "onlinejudge.org" in x["url"]:
            body = (ARCHIVE / x["path"]).read_text(encoding="utf-8", errors="replace")
            for n, t in re.findall(r'page=show_problem&(?:amp;)?problem=(\d+)">([^<]+)</a>', body):
                pairs[n] = html.unescape(t).replace("\xa0", " ").split(" - ")[0].strip()
    return pairs


def main() -> int:
    write = "--write" in sys.argv
    uva, stats = uva_pairs(), Counter()
    for f in sorted((ROOT / "problemsets").glob("*.yaml")):
        lines = f.read_text().split("\n")
        changed = False
        for i, line in enumerate(lines):
            m = re.match(r"^(\s*)url: " + re.escape(OLD) + r"(\d+)\s*$", line)
            if not m:
                continue
            judge_at = next((k for k in (i - 1, i + 1, i + 2) if 0 <= k < len(lines) and re.match(r"^\s*(- )?judge: livearchive\s*$", lines[k])), None)
            id_at = next((k for k in (i + 1, i - 1, i + 2) if 0 <= k < len(lines) and re.match(r"^\s*(- )?id: ", lines[k])), None)
            if judge_at is None or id_at is None:
                stats["not understood"] += 1
                continue
            num = lines[id_at].split("id:", 1)[1].strip().strip("'\"")
            if uva.get(m.group(2)) == num:
                lines[judge_at] = lines[judge_at].replace("judge: livearchive", "judge: uva")
                stats["UVa link: judge set to uva"] += 1
            else:
                lines[i] = f"{m.group(1)}url: {NEW}{m.group(2)}"
                stats["Live Archive link: host put right"] += 1
            changed = True
        if changed and write:
            f.write_text("\n".join(lines))
    for f in sorted((ROOT / "series").glob("*.yaml")):
        lines = f.read_text().split("\n")
        changed, on_uva = False, False
        for i, line in enumerate(lines):
            if re.match(r"^\s*- url: ", line):
                on_uva = "onlinejudge.org" in line
            elif on_uva and re.match(r"^\s*judge: livearchive\s*$", line):
                lines[i] = line.replace("judge: livearchive", "judge: uva")
                stats["contest page on onlinejudge.org: judge set to uva"] += 1
                changed = True
        if changed and write:
            f.write_text("\n".join(lines))
    print(dict(stats), "(written)" if write else "(dry run; --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
