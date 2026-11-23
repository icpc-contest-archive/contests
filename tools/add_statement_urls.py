#!/usr/bin/env python3
"""Record where a problem's statement is when it is not the problem's page on the judge.

`statement_url` on a problem's judge link names the file that holds the statement:
  - QOJ: the page is a frame around /download.php?type=statement&id=<n>
  - Codeforces gyms whose problem pages lead to the gym's attachments: the problem set's PDF there
Read from the queues the statement files were fetched with (archive/topup-qoj-statements-*.json,
archive/topup-cf-gym-statements-*.json). Edits the files as text. --write to apply.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT.parent / "archive"


def main() -> int:
    write = "--write" in sys.argv
    stats = Counter()
    by_set: dict = {}
    for q in sorted(ARCHIVE.glob("topup-qoj-statements-*.json")):
        for it in json.loads(q.read_text())["queue"]:
            by_set.setdefault(it["set"], {})[it["page"]] = it["raw_url"]
    gym_pdf = {}
    for q in sorted(ARCHIVE.glob("topup-cf-gym-statements-*.json")):
        for it in json.loads(q.read_text())["queue"]:
            gym_pdf[it["gym"]] = it["raw_url"]
    for f in sorted((ROOT / "problemsets").glob("*.yaml")):
        lines = f.read_text().split("\n")
        qoj = by_set.get(f.stem, {})
        out, changed = [], False
        for i, line in enumerate(lines):
            out.append(line)
            m = re.match(r"^(\s*)url: (\S+)\s*$", line)
            if not m:
                continue
            url = m.group(2)
            g = re.match(r"https://codeforces\.com/gym/(\d+)/problem/", url)
            target = qoj.get(url) or (gym_pdf.get(g.group(1)) if g else None)
            if not target:
                continue
            nxt = "\n".join(lines[i + 1:i + 4])
            if "statement_url:" in nxt:
                continue
            out.append(f"{m.group(1)}statement_url: {target}")
            stats["qoj" if url in qoj else "codeforces gym"] += 1
            changed = True
        if changed and write:
            f.write_text("\n".join(out))
    print(dict(stats), "(written)" if write else "(dry run; --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
