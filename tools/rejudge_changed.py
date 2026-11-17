#!/usr/bin/env python3
"""Second look at addresses judged `changed`: is it the page's content, or only its dressing? (2026-11-16)

  python3 tools/rejudge_changed.py [--write]

The live check compares the whole page with the snapshot taken near the contest. A results page
whose table is exactly what it was, on a site that has since changed its header, menus and
scripts, scores low on that comparison and is recorded as `changed` (rmc-2021's Kattis scoreboard:
whole-page similarity 0.53, tables 0.98). Where we hold both a copy fetched from the address and
a copy from the Wayback Machine, this compares what matters — the text of the tables — and
records the address as `live` when the tables are the same (similarity 0.90 or more, on tables
of 30 words or more). Anything else stays as it is. The archive must be checked out beside this
repository. Without --write nothing is changed.
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, dump_series, load_series, sources  # noqa: E402
from site_resources import lid  # noqa: E402

ARCHIVE = ROOT.parent / "archive"
SAME = 0.90


def table_words(p: Path) -> collections.Counter:
    b = p.read_bytes()
    s = next((b.decode(e) for e in ("utf-8", "cp1251") if _ok(b, e)), b.decode("latin-1"))
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", s)
    tabs = re.findall(r"(?is)<table\b.*?</table>", s)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", " ".join(tabs)))
    return collections.Counter(re.findall(r"\w+", t.lower()))


def _ok(b: bytes, enc: str) -> bool:
    try:
        b.decode(enc)
        return True
    except UnicodeDecodeError:
        return False


def similarity(a: collections.Counter, b: collections.Counter) -> float:
    union = sum((a | b).values())
    return sum((a & b).values()) / union if union else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if not ARCHIVE.exists():
        sys.exit("the archive repository is not checked out beside this one")
    locs = json.loads((ROOT / "data" / "resources.json").read_text())["locators"]
    series = load_series()
    n = collections.Counter()
    fixed = []
    for sid, doc in series.items():
        hit = False
        for c in doc["contests"]:
            for s in sources(c):
                if s.get("url_state") != "changed":
                    continue
                n["changed"] += 1
                caps = [x for R in ((locs.get(lid(s["url"])) or {}).get("resources") or {}).values() for x in R.get("captures") or []
                        if not x.get("caveat") and "html" in (x.get("content_type") or "") and x.get("contest") == c["id"]]
                live = sorted((x for x in caps if x.get("source") == "live"), key=lambda x: str(x.get("fetched")))
                wb = [x for x in caps if x.get("source") == "wayback"]
                if not live or not wb:
                    n["no pair of copies to compare"] += 1
                    continue
                lw = table_words(ARCHIVE / live[-1]["path"])
                best = max((similarity(lw, table_words(ARCHIVE / x["path"])) for x in wb), default=0.0)
                if sum(lw.values()) < 30:
                    n["no table to compare"] += 1
                elif best >= SAME:
                    n["tables the same: live"] += 1
                    fixed.append(f"{c['id']}: {s['url']} (tables {best:.2f})")
                    s["url_state"] = "live"
                    hit = True
                else:
                    n["tables differ: stays changed"] += 1
        if hit and a.write:
            dump_series(sid, doc, "rejudge_changed.py")
    for k, v in n.items():
        print(f"{v:5} {k}")
    print("\n".join(fixed[:400]))
    if not a.write:
        print("(dry run; --write to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
