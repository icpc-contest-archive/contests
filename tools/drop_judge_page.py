#!/usr/bin/env python3
"""Drop the `judge_page` role (ruling 2026-11-14).

A role says what a source is: a judge's page with a contest's problems is a `problemset`
(one problem's page would be a `problem`). That it is on an online judge is said by
`judge: <id>`, which stays. Every judge_page source in the catalogue was a contest-level
page, so each becomes a problemset; a source that carried both roles keeps the one.

Edits series/*.yaml and registry/non-mainline.yaml in place, line by line, so nothing else
in the files moves. Rerunnable (a second run finds nothing).

  python3 tools/drop_judge_page.py [--dry-run]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEM = re.compile(r"^(\s*)- (\w+)\s*$")


def convert(text: str) -> tuple[str, int, int]:
    lines, out, i, renamed, merged = text.split("\n"), [], 0, 0, 0
    while i < len(lines):
        out.append(lines[i])
        if re.match(r"^\s*(- )?roles:\s*$", lines[i]):
            j = i + 1
            while j < len(lines) and ITEM.match(lines[j]):
                j += 1
            block = lines[i + 1:j]
            names = [ITEM.match(x).group(2) for x in block]
            if "judge_page" in names:
                if "problemset" in names or "problem" in names:
                    block = [x for x in block if ITEM.match(x).group(2) != "judge_page"]
                    merged += 1
                else:
                    block = [x.replace("judge_page", "problemset") if ITEM.match(x).group(2) == "judge_page" else x for x in block]
                    renamed += 1
            out.extend(block)
            i = j
            continue
        i += 1
    return "\n".join(out), renamed, merged


def main() -> int:
    dry = "--dry-run" in sys.argv
    files = sorted((ROOT / "series").glob("*.yaml")) + [ROOT / "registry" / "non-mainline.yaml"]
    tr = tm = tf = 0
    for f in files:
        old = f.read_text()
        new, r, m = convert(old)
        if new != old:
            tf += 1
            tr += r
            tm += m
            if not dry:
                f.write_text(new)
    print(f"{tf} files: {tr} judge_page -> problemset, {tm} judge_page dropped beside problemset/problem" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
