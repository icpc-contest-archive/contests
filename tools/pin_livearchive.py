#!/usr/bin/env python3
"""Pin the Live Archive's problem links to what the Wayback Machine holds (ruled 2026-11-22).

Reads the listings of archive/tools/cdx_harvest.py for icpcarchive.ecs.baylor.edu (index.php and
external/) and, for every `judge: livearchive` link of a problem:
  - `as_of`: the snapshot of the problem's page. Where the page was only saved under its address with a
    category in it, `url` becomes that address (the same page; it is what the snapshot answers to).
  - `statement_url`: the statement file, external/<nn>/<number>.pdf (else p<number>.pdf, else .html).
The internal page number is taken from the Live Archive's own map (data/livearchive-problems.json) when
it knows the problem, never kept from a link that opens another problem. Edits the files as text.
--write to apply.

--queue writes ../archive/topup-livearchive-statements-<day>.json for capture_urls.py --no-live: the
statement file, at its snapshot, of every such problem whose set's statements we do not all hold and
that has no statement copy yet. (Builds the site into a scratch folder to know what is held.)
"""
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import livearchive  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT.parent / "archive"
HOST = "icpcarchive.ecs.baylor.edu"
PAGE = re.compile(r"^(\s*)url: (https://icpcarchive\.ecs\.baylor\.edu/index\.php\?\S*page=show_problem&problem=(\d+))\s*$")


def listings():
    pages, files = {}, {}
    for u, ts, _st in json.loads((ARCHIVE / "reports" / f"cdx-harvest-{HOST}_index.php.json").read_text()):
        q = urlsplit(u).query
        if "show_problem" not in u or "&amp;" in q:
            continue   # an address saved with its "&amp;" unresolved is another address
        kv = {k.lower(): v for k, v in parse_qsl(q)}
        extra = set(kv) - {"option", "itemid", "page", "problem"}
        if kv.get("page") != "show_problem" or kv.get("option") != "com_onlinejudge" or not kv.get("problem", "").isdigit() or extra - {"category"}:
            continue
        rank = 1 if extra else 0
        if kv["problem"] not in pages or rank < pages[kv["problem"]][0]:
            pages[kv["problem"]] = (rank, ts, u)
    for u, ts, _st in json.loads((ARCHIVE / "reports" / f"cdx-harvest-{HOST}_external.json").read_text()):
        m = re.search(r"/external/\d+/(p?)(\d+)\.(pdf|html)$", u)
        if m:
            rank = (0 if m.group(3) == "pdf" else 2) + (1 if m.group(1) else 0)
            if m.group(2) not in files or rank < files[m.group(2)][0]:
                files[m.group(2)] = (rank, ts, u)
    return pages, files


def main() -> int:
    write, queue = "--write" in sys.argv, "--queue" in sys.argv
    pages, files = listings()
    stats: Counter = Counter()
    if not queue:
        for f in sorted((ROOT / "problemsets").glob("*.yaml")):
            lines = f.read_text().split("\n")
            out, changed = [], False
            i = 0
            while i < len(lines):
                line = lines[i]
                m = PAGE.match(line)
                is_la = m and any(re.match(r"^\s*(- )?judge: livearchive\s*$", lines[k]) for k in (i - 1, i + 1, i + 2) if 0 <= k < len(lines))
                if not is_la:
                    out.append(line)
                    i += 1
                    continue
                ind, internal = m.group(1), m.group(3)
                # the lines of this link that follow its address (id, and anything set on an earlier run)
                rest, k = [], i + 1
                while k < len(lines) and re.match(rf"^{ind}(id|as_of|statement_url|note): ", lines[k]):
                    rest.append(lines[k])
                    k += 1
                num = next((x.split("id:", 1)[1].strip().strip("'\"") for x in rest if x.strip().startswith("id:")), None)
                # the page of the problem itself: the internal number in the address may be another problem's
                # (it was once derived as number - 1999); the Live Archive's own map decides (tools/livearchive.py)
                mapped = livearchive.internal(num) if num else None
                if mapped is not None and str(mapped) != internal:
                    stats["internal number corrected from the map"] += 1
                    internal = str(mapped)
                    m = PAGE.match(f"{ind}url: {livearchive.PAGE_URL.format(internal=internal)}")
                page, fil = pages.get(internal), files.get(num or "")
                url = page[2] if page and page[0] else m.group(2).split("&category=")[0] if not page else m.group(2)
                if page and page[0] == 0:
                    url = f"https://{HOST}/index.php?option=com_onlinejudge&Itemid=8&page=show_problem&problem={internal}"
                if not page and any(x.strip().startswith("as_of:") for x in rest):
                    url = m.group(2)   # keep the address the earlier pin answers to
                new = [f"{ind}url: {url}"] + [x for x in rest if x.strip().startswith(("id:", "note:"))]
                if page:
                    new.append(f"{ind}as_of: '{page[1]}'")
                    stats["page snapshot" + (" (address with its category)" if page[0] else "")] += 1
                else:
                    # a snapshot pinned earlier (found by another CDX query) stays: the listing is not complete
                    kept = [x for x in rest if x.strip().startswith("as_of:")]
                    new += kept
                    stats["no page snapshot in the listing" + (" (earlier pin kept)" if kept else "")] += 1
                if fil:
                    new.append(f"{ind}statement_url: {fil[2]}")
                    stats["statement file: " + ("pdf" if fil[0] < 2 else "html")] += 1
                else:
                    stats["no statement file"] += 1
                changed = changed or new != [line] + rest
                out += new
                i = k
            if changed and write:
                f.write_text("\n".join(out))
        print(dict(stats), "(written)" if write else "(dry run; --write to apply)")
        return 0
    import contextlib, io, tempfile   # noqa: E401
    sys.path.insert(0, str(ROOT / "tools"))
    import build_site as B
    with contextlib.redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory() as tmp:
        B.build(Path(tmp))
    items, seen = [], set()
    for sid, doc in B.SETS.items():
        if B.COV.set_record(sid)["statement"] == "all":
            continue
        members = [m for m in B.set_members(doc) if m in B.CONTESTS]
        if not members:
            continue
        c = B.CONTESTS[members[0]]
        for p in doc.get("problems") or []:
            if p["id"] in B.COV.statements_held(doc):
                stats["has a statement copy already"] += 1
                continue
            j = next((j for j in p.get("judges") or [] if j["judge"] == "livearchive" and j.get("statement_url")), None)
            if not j or j["statement_url"] in seen:
                continue
            seen.add(j["statement_url"])
            ts = next((t for _r, t, u in files.values() if u == j["statement_url"]), None)
            year = int(c["id"].rsplit("-", 1)[1])
            items.append({"contest": c["id"], "kind": "judge-livearchive", "roles": ["problem"], "url": j["statement_url"],
                          "raw_url": j["statement_url"], "pivot": (c.get("date") or f"{year}0101").replace("-", ""),
                          "problem": p["id"], "set": sid, **({"pinned_ts": ts} if ts else {})})
            stats["queued"] += 1
    out = ARCHIVE / f"topup-livearchive-statements-{datetime.date.today().isoformat()}.json"
    out.write_text(json.dumps({"generated": datetime.date.today().isoformat(), "queue": items}, indent=1))
    print(dict(stats), "->", out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
