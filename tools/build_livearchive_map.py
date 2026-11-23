#!/usr/bin/env python3
"""Build data/livearchive-problems.json: the Live Archive's own map from problem number to its internal
page number, read off Wayback copies of its category pages.

The Live Archive (icpcarchive.ecs.baylor.edu, gone; ruled 2026-11-22: link its Wayback snapshots) has two
numbers per problem: the problem number everyone cites (e.g. 6689) and the internal number in its page
address (`page=show_problem&problem=4701`). The two are NOT a fixed offset apart: "number - 1999" is right
for about two thirds of the problems and opens another problem for the rest. Each category page lists
`<a href="...page=show_problem&problem=<internal>"><number> - <title></a>`, so the map is read from them.

    python3 tools/build_livearchive_map.py DIR [PAGES.json ...]

DIR holds the category pages as <category>.html, each with <category>.html.ts holding the Wayback
timestamp it was fetched at (the data scan of 2026-11-23 fetched all 804 that Wayback holds; 767 list
problems). PAGES.json files add problems no category page lists, read one by one off the snapshot of the
problem's own page ({"pages": [{number, internal, title, url, as_of}]}, e.g.
data/livearchive-problem-pages-2026-11-23.json).
"""
from __future__ import annotations

import datetime
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r'page=show_problem&(?:amp;)?problem=(\d+)">(\d+)(?:&nbsp;|\s)-(?:&nbsp;|\s)([^<]*)<')
CATEGORY = "https://icpcarchive.ecs.baylor.edu/index.php?option=com_onlinejudge&Itemid=8&category={c}"


def main() -> int:
    src = Path(sys.argv[1])
    problems: dict[str, dict] = {}
    pages = 0
    for f in sorted(src.glob("*.html"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0):
        if not f.stem.isdigit():
            continue
        cat = int(f.stem)
        ts_file = f.with_name(f.name + ".ts")
        ts = ts_file.read_text().strip() if ts_file.exists() else None
        body = f.read_text(encoding="utf-8", errors="replace")
        found = LINK.findall(body)
        if found:
            pages += 1
        for internal, number, title in found:
            e = problems.setdefault(number, {"internal": [], "titles": [], "seen_on": []})
            if int(internal) not in e["internal"]:
                e["internal"].append(int(internal))
            t = html.unescape(title).replace("\xa0", " ").strip()
            if t and t not in e["titles"]:
                e["titles"].append(t)
            if len(e["seen_on"]) < 3:
                e["seen_on"].append({"url": CATEGORY.format(c=cat), "as_of": ts})
    for extra in sys.argv[2:]:
        for p in json.loads(Path(extra).read_text())["pages"]:
            e = problems.setdefault(str(p["number"]), {"internal": [], "titles": [], "seen_on": []})
            if p["internal"] not in e["internal"]:
                e["internal"].append(p["internal"])
            if p["title"] not in e["titles"]:
                e["titles"].append(p["title"])
            if len(e["seen_on"]) < 3:
                e["seen_on"].append({"url": p["url"], "as_of": p["as_of"]})
    out = {
        "about": "Live Archive problem number -> internal page number (page=show_problem&problem=N), "
                 "read off Wayback copies of its category pages; tools/build_livearchive_map.py",
        "built": datetime.date.today().isoformat(),
        "category_pages": pages,
        "problems": dict(sorted(problems.items(), key=lambda kv: int(kv[0]))),
    }
    (ROOT / "data" / "livearchive-problems.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    multi = sum(1 for e in problems.values() if len(e["internal"]) > 1)
    print(f"{len(problems)} problem numbers from {pages} category pages; {multi} with more than one internal number")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
