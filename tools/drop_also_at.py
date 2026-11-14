#!/usr/bin/env python3
"""Drop `also_at` (ruling 2026-11-14): another address that shows a contest's website is a
`web` source of its own, not an entry under the first one. That two sources are the same
document is read off the copies (same checksum), not stored.

Each also_at entry becomes {url, roles: [web], as_of?, note?} on the same contest, except:
  - the address is already a source of the contest           -> nothing added
  - a CMS finder page (icpc.global/regionals/finder/...)     -> not a source (ruling 8), dropped
  - not an address (a wildcard)                              -> dropped
Dropped entries are listed in reports/also-at-dropped-2026-11-14.md.

  python3 tools/drop_also_at.py [--write]
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, dump_series, find_source, load_series, normalise_source, sort_sources  # noqa: E402

FINDER = re.compile(r"^https?://icpc\.global/regionals/finder/", re.I)


def convert(doc: dict, log: dict) -> bool:
    changed = False
    for c in doc["contests"]:
        new = []
        for s in c.get("sources") or []:
            for m in s.pop("also_at", None) or []:
                changed = True
                m = m if isinstance(m, dict) else {"url": m}
                url = m["url"]
                if "*" in url or not url.startswith("http"):
                    log["dropped: not an address"].append((c["id"], url, s["url"]))
                elif FINDER.match(url):
                    log["dropped: CMS finder page"].append((c["id"], url, s["url"]))
                elif find_source(c, url) is not None or any(x["url"] == url for x in new):
                    log["already a source"].append((c["id"], url, s["url"]))
                else:
                    e = {"url": url, "roles": ["web"]}
                    for k in ("as_of", "note"):
                        if m.get(k):
                            e[k] = m[k]
                    new.append(normalise_source(e))
                    log["now a web source"].append((c["id"], url, s["url"]))
        if new:
            c["sources"].extend(new)
            sort_sources(c)
    return changed


def main() -> int:
    write = "--write" in sys.argv
    log, n = defaultdict(list), 0
    for sid, doc in load_series().items():
        if convert(doc, log):
            n += 1
            if write:
                dump_series(sid, doc, "drop_also_at.py")
    for k in sorted(log):
        print(f"{k}: {len(log[k])}")
    print(f"{n} series files" + ("" if write else " (dry run)"))
    if write and n:
        L = ["# also_at dropped, 2026-11-14", "", "Every other address of a contest's website is now a `web` source of its own "
             "(`tools/drop_also_at.py`).", "", "| what happened | entries |", "| --- | --- |"]
        L += [f"| {k} | {len(v)} |" for k, v in sorted(log.items())]
        for k in sorted(log):
            if k != "now a web source":
                L += ["", f"## {k[0].upper() + k[1:]}", ""] + [f"- {cid}: {url} (was under {of})" for cid, url, of in log[k]]
        (ROOT / "reports" / "also-at-dropped-2026-11-14.md").write_text("\n".join(L) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
