#!/usr/bin/env python3
"""Drop the `icpc_standings` role (ruling 2026-11-14): a role says what a document holds, not
where it is, and a standings page of the ICPC CMS holds standings, rankings or a team list.

Every source with the role gets the role of its content instead:
  rows with problems solved        -> standings
  rows with ranks only             -> rankings
  rows with neither                -> teams
  no rows at all                   -> the page holds nothing, so it is not a source: the role
                                      goes, and a source left with no role is removed and
                                      recorded in data/icpc-standings-empty.json
The content is read from the fetch of every standings page (../archive/icpc-global-standings,
2026-11-13) and, where that has no rows or no entry, from the copy rendered from the API dumps
(standings.json beside the archived standings.html). A source with the role that is not a CMS
finder page and has no copy cannot be read here: it becomes `rankings` (the least a results
page says) and is listed in the report for a look.

That a source is a page of the CMS is now read off its address (catalogue.is_cms).

  python3 tools/drop_icpc_standings.py [--write]
Rerunnable: a second run finds nothing. Report: reports/icpc-standings-mapped-2026-11-14.md
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import RANK, ROOT, archived, dump_series, is_cms, load_series, sort_sources  # noqa: E402

ARCHIVE = ROOT.parent / "archive"
FETCH = ARCHIVE / "icpc-global-standings"
OLD = "icpc_standings"


def kind_of(rows: list) -> str | None:
    if not rows:
        return None
    if any(r.get("problemsSolved") for r in rows):
        return "standings"
    return "rankings" if any(r.get("rank") for r in rows) else "teams"


class Reader:
    def __init__(self):
        self.idx = {r["url"].lower(): r for r in csv.DictReader((FETCH / "index.csv").open())}

    def rows(self, s: dict) -> tuple[list | None, str]:
        """(rows or None when nothing could be read, where they were read)."""
        got = None
        r = self.idx.get(s["url"].lower())
        if r:
            got = json.loads((FETCH / "standings" / r["file"]).read_text())["rows"], f"page fetch {r['fetched'][:10]}"
            if got[0]:
                return got
        for p in archived(s):
            j = ARCHIVE / Path(p).with_name("standings.json")
            if p.endswith("standings.html") and j.exists():
                rows = json.loads(j.read_text()).get("standings") or []
                if rows:
                    return rows, f"copy {p.split('/')[-2]}"
        return got if got else (None, "")


def convert(doc: dict, rd: Reader, log: dict) -> bool:
    changed = False
    for c in doc["contests"]:
        keep = []
        for s in c.get("sources") or []:
            if OLD not in s["roles"]:
                keep.append(s)
                continue
            changed = True
            rows, where = rd.rows(s)
            if rows is None:
                new = "rankings"
                log["unread"].append((c["id"], s["url"]))
            else:
                new = kind_of(rows)
                if new is None:
                    log["empty"].append((c["id"], s["url"], where, c.get("cms_ids") or []))
                elif new != "standings" or not any(r.get("rank") for r in rows):
                    log["odd"].append((c["id"], new, len(rows), "no ranks" if new == "standings" else ""))
            roles = [r for r in s["roles"] if r != OLD]
            if new and new not in roles:
                roles.append(new)
            log["to " + (new or "nothing")].append(c["id"])
            if not roles:
                continue  # an empty page with no other role: not a source
            s["roles"] = sorted(roles, key=lambda r: RANK[r])
            keep.append(s)
        if changed and "sources" in c:
            if keep:
                c["sources"] = keep
                sort_sources(c)
            else:
                del c["sources"]
        if OLD in (c.get("none") or []):
            c["none"] = [r for r in c["none"] if r != OLD]
            if not c["none"]:
                del c["none"]
            changed = True
    return changed


def main() -> int:
    write = "--write" in sys.argv
    rd, log, n = Reader(), defaultdict(list), 0
    for sid, doc in load_series().items():
        if convert(doc, rd, log):
            n += 1
            if write:
                dump_series(sid, doc, "drop_icpc_standings.py")
    for k in sorted(log):
        print(f"{k}: {len(log[k])}")
    print(f"{n} series files" + ("" if write else " (dry run)"))
    if write and n:
        p = ROOT / "data" / "icpc-standings-empty.json"
        d = json.loads(p.read_text())
        d["what"] = ("contests whose ICPC standings page holds nothing (no rows from the open API). An empty page is not a source: "
                     "since 2026-11-14 these are not in the contests' sources; this file is the record of the pages and when they were asked")
        for cid, url, where, ids in log["empty"]:
            d["contests"].setdefault(cid, {"cms_ids": ids, "asked": where[-10:], "url": url})
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
        L = ["# ICPC standings mapped by content, 2026-11-14", "",
             "The `icpc_standings` role is gone. Each source that had it now says what its page holds; "
             "`tools/drop_icpc_standings.py` did it from the fetch of every standings page (2026-11-13) and the copies rendered from the API dumps.", "",
             "| became | sources |", "| --- | --- |"]
        L += [f"| {k[3:]} | {len(log[k])} |" for k in sorted(log) if k.startswith("to ")]
        L += ["", "`nothing`: the page has no rows. The role is gone; a source with no other role is removed and recorded in "
              "`data/icpc-standings-empty.json`.", "", "## Not plain standings", ""]
        L += [f"- {cid}: {new}, {rows} rows" + (f" ({what})" if what else "") for cid, new, rows, what in log["odd"]]
        L += ["", "## Not read: filed as rankings, to be looked at", "",
              "Not CMS finder pages, and we hold no copy, so the content was not read.", ""]
        L += [f"- {cid}: {url}" for cid, url in log["unread"]]
        (ROOT / "reports" / "icpc-standings-mapped-2026-11-14.md").write_text("\n".join(L) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
