#!/usr/bin/env python3
"""Index the archive repo's `website` captures into data/website-index.json.

The private archive repo holds one crawl per contest website under
  <series>/<contest>/website/<capture-id>/site-manifest.json
(see archive/tools/capture_site.py). archive/index.json only lists result
captures, so the site builder needs this separate, small index to know which
contests have an archived website and which snapshot it came from.

Usage: python3 tools/index_websites.py [--archive ../archive]
Writes data/website-index.json (committed; CI builds the site without the
archive checkout). One entry per capture; `primary` marks the capture the
catalogue's "local" link points at (most pages, then latest).
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from resources import unwrap  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default=str(ROOT.parent / "archive"))
    args = ap.parse_args()
    archive = Path(args.archive)
    if not archive.is_dir():
        print(f"no archive checkout at {archive}")
        return 1

    by_contest: dict[str, list] = defaultdict(list)
    for mf in sorted(archive.glob("*/*/website/*/site-manifest.json")):
        m = json.loads(mf.read_text())
        pages = m.get("pages") or {}
        seed = (m.get("seeds") or [None])[0]
        seed_page = pages.get(seed) if seed else None
        if seed_page is None and pages:
            seed = next(iter(pages))
            seed_page = pages[seed]
        html_pages = sum(1 for p in pages.values()
                         if str(p.get("ctype", "")).startswith("text/html"))
        entry = {
            "contest": m["contest"],
            "dir": str(mf.parent.relative_to(archive)),
            "mode": m.get("mode"),
            "seed": seed,
            "pivot": m.get("pivot"),
            "fetched": m.get("fetched"),
            "pages": len(pages),
            "html_pages": html_pages,
            "bytes": (m.get("stats") or {}).get("bytes"),
        }
        if seed_page and seed_page.get("wayback_timestamp"):
            entry["wayback_timestamp"] = seed_page["wayback_timestamp"]
            entry["wayback_url"] = seed_page.get("wayback_url")
        # a crawl seeded with a Wayback wrapper URL (pre-resource-model catalogue) is a
        # snapshot crawl whatever the manifest's mode says: unwrap -> (url, ts)
        raw, ts, via = unwrap(seed or "")
        if via:
            entry["seed_raw"] = raw
            if ts and not entry.get("wayback_timestamp"):
                entry["wayback_timestamp"] = ts
                entry["wayback_url"] = f"https://web.archive.org/web/{ts}/{raw}"
            entry["mode"] = "wayback"
        by_contest[m["contest"]].append(entry)

    sites = []
    for cid, entries in sorted(by_contest.items()):
        # primary = a real-url capture over a wrapper-seeded one (pre-resource-model
        # crawls hold Wayback's toolbar-wrapped pages), then most html pages, then latest
        best = max(entries, key=lambda e: (not e.get("seed_raw"), e["html_pages"],
                                           e["pages"], e["fetched"] or ""))
        for e in entries:
            e["primary"] = e is best
            sites.append(e)

    out = ROOT / "data" / "website-index.json"
    out.write_text(json.dumps({"generated": __import__("datetime").datetime.utcnow()
                               .strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "tool": "index_websites.py/1.0",
                               "sites": sites}, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(sites)} website captures for {len(by_contest)} contests -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
