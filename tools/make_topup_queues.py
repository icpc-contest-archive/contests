#!/usr/bin/env python3
"""Queue the sources we hold no copy of but could fetch with the tools we have.

A source qualifies when our archive has no copy of it and either its address answers (live or
changed) or the Wayback Machine has a snapshot. Left out, each counted in the summary:
- contests still to come (their pages are captured once the contest has run);
- hosts a plain fetch does not get (NEEDS_BROWSER);
- a bad copy whose address answers and that has no snapshot: the same fetch gives the same copy;
- a website address that is already a page of a crawl we hold.

Two files in ../archive, named so that the default queue lookup of the capture tools never picks them:
  topup-pages-<today>.json   for capture_urls.py: single pages, the snapshot pinned when one is known
  topup-sites-<today>.json   for capture_site.py: a contest with no crawl gets its normal item; a
                             contest that has one gets an item for the missing address alone,
                             with a budget of 25 pages, once however many contests cite it
                             (capture_site.py never revisits a site it has crawled, so an address
                             added later is otherwise never fetched)

Builds the site into a scratch folder to judge every source exactly as the site does (about a minute).
Needs pyyaml and the archive checkout.
"""
from __future__ import annotations

import contextlib
import datetime
import io
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT.parent / "archive"
sys.path.insert(0, str(ROOT / "tools"))
import build_site as B  # noqa: E402
from catalogue import load_contests, sources  # noqa: E402
from make_capture_queue import capture_kind  # noqa: E402
from make_site_queue import scope_for  # noqa: E402
from resources import norm_key, unwrap  # noqa: E402

# a plain fetch gets a bot wall, a login page or an empty app shell from these
NEEDS_BROWSER = {"qoj.ac", "codeforces.com", "drive.google.com", "docs.google.com", "www.facebook.com",
                 "github.com", "board.xcpcio.com", "onlinejudge.u-aizu.ac.jp", "groups.google.com", "dmoj.ca",
                 "usenetarchives.com", "www.instagram.com", "omegaup.com", "tlx.toki.id", "www.mediafire.com"}


TOPUP_PAGES = 25   # page budget of an item for one missing address (capture_site.py >= 1.17)


def needs_browser(url: str) -> bool:
    host = urlsplit(url).netloc.lower()
    return host in NEEDS_BROWSER or host.endswith("icpc.global")


def crawled(cid: str) -> tuple[bool, set[str]]:
    """Has the contest a website crawl, and the addresses it holds a file for."""
    held, any_crawl = set(), False
    for mf in (ARCHIVE / cid.rsplit("-", 1)[0] / cid / "website").glob("*/site-manifest.json"):
        any_crawl = True
        for u, pg in (json.loads(mf.read_text()).get("pages") or {}).items():
            if pg.get("file"):
                held.add(norm_key(unwrap(u)[0]))
    return any_crawl, held


def main() -> int:
    with contextlib.redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory() as tmp:
        B.build(Path(tmp))
    today = datetime.date.today().isoformat()
    pages, sites, stats, seen = [], [], Counter(), set()
    crawls: dict = {}
    for c in load_contests().values():
        cid = c["id"]
        year = int(cid.rsplit("-", 1)[1])
        pivot = (c.get("date") or "").replace("-", "") or (f"{year}0701" if c.get("season") == year + 1 else f"{year}0101")
        new_seeds = []
        for s in sources(c):
            url = s["url"]
            if not url.startswith("http"):
                continue
            a = B.avail(url, cid)
            if a["ours"]["word"] == "held":
                continue
            answers = a["live"]["word"] in ("live", "changed")
            snap = a["wb"].get("ts") if a["wb"]["word"] == "snapshot" else None
            if not answers and not snap:
                continue
            if c.get("status") == "upcoming":
                stats["left out: contest still to come"] += 1
                continue
            if needs_browser(url):
                stats["left out: needs a browser"] += 1
                continue
            kind = capture_kind(s)
            if kind is not None:
                if a["ours"]["word"] == "bad copy" and not snap:
                    stats["left out: bad copy, the same fetch gives the same"] += 1
                    continue
                raw, ts, _via = unwrap(url)
                if (cid, kind, raw) in seen:
                    continue
                seen.add((cid, kind, raw))
                item = {"contest": cid, "kind": kind, "roles": list(s["roles"]), "url": url, "pivot": pivot, "raw_url": raw}
                ts = s.get("as_of") or ts or snap
                if ts:
                    item["pinned_ts"] = ts
                pages.append(item)
                stats[f"page: {'address answers' if answers else 'snapshot'}"] += 1
            elif "web" in s["roles"]:
                if cid not in crawls:
                    crawls[cid] = crawled(cid)
                any_crawl, held = crawls[cid]
                if norm_key(unwrap(url)[0]) in held:
                    stats["left out: website address already a page of a crawl we hold"] += 1
                    continue
                if a["ours"]["word"] == "bad copy" and not snap:
                    stats["left out: bad copy, the same fetch gives the same"] += 1
                    continue
                if not any_crawl:
                    new_seeds.append((url, s.get("as_of")))
                    continue
                raw = unwrap(url)[0]
                when = None if answers else (s.get("as_of") or snap)
                if (norm_key(raw), when) in seen:   # cited by several contests: one fetch
                    stats["site: the same address and time already queued for another contest"] += 1
                    continue
                seen.add((norm_key(raw), when))
                p = urlsplit(raw)
                item = {"contest": cid, "seeds": [raw], "pivot": pivot, "max_pages": TOPUP_PAGES,
                        "scopes": [{"host": p.netloc, "path": p.path or "/", "rule": "missing address of a crawled site"}]}
                if when:
                    item["snapshot"] = when
                sites.append(item)
                stats[f"site, address missing from its crawl: {'address answers' if answers else 'snapshot'}"] += 1
        if new_seeds:   # no crawl yet: the item make_site_queue.py would write
            item = {"contest": cid, "seeds": [u for u, _ in new_seeds], "pivot": pivot,
                    "scopes": [scope_for(u, year) for u, _ in new_seeds]}
            snapshot = next((t for _, t in new_seeds if t), None)
            if snapshot:
                item["snapshot"] = snapshot
            sites.append(item)
            stats["site, never crawled"] += 1
    for name, queue in (("pages", pages), ("sites", sites)):
        out = ARCHIVE / f"topup-{name}-{today}.json"
        out.write_text(json.dumps({"generated": today, "queue": queue}, indent=1))
        print(f"{len(queue)} -> {out}")
    for k, n in sorted(stats.items()):
        print(f"  {n:4d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
