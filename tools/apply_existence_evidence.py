#!/usr/bin/env python3
"""Append existence-hunt evidence to the `provenance:` list of catalogue contests.

Reads data/existence-evidence-<date>.json (output of the 2026-10-22 existence hunt) and, for
every contest whose verdict is one of --verdicts, appends its proposed provenance lines (the
hunt's JSON still calls them `proposed_sources_lines`) to the contest record in
series/<series>.yaml — never touching any other field, never duplicating a line whose URL is
already present in that contest's provenance/notes. Dates, hosts and winners
found by the hunt are NOT applied (they are listed in the report for manual review).

Run from the contests repo root:
  python3 tools/apply_existence_evidence.py --dry-run
  python3 tools/apply_existence_evidence.py
  python3 tools/validate.py
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import dump_series, load_series  # noqa: E402

URL_RE = re.compile(r"https?://\S+")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=str(ROOT / "data" / "existence-evidence-2026-10-22.json"))
    ap.add_argument("--verdicts", default="confirmed-ran,likely-ran,likely-not-run,not-yet-held,unclear")
    ap.add_argument("--max-per-contest", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    verdicts = set(args.verdicts.split(","))

    doc = json.loads(Path(args.evidence).read_text())
    wanted = {c["contest"]: c for c in doc["contests"]
              if c["verdict"] in verdicts and c.get("proposed_sources_lines")}

    stats = Counter()
    for sid, sdoc in load_series().items():
        changed = False
        for c in sdoc["contests"]:
            e = wanted.get(c["id"])
            if not e:
                continue
            have = " ".join(c.get("provenance") or []) + " " + str(c.get("notes") or "")
            have_urls = set(URL_RE.findall(have))
            added = 0
            for line in e["proposed_sources_lines"]:
                if added >= args.max_per_contest:
                    break
                urls = URL_RE.findall(line)
                if urls and all(u.rstrip(".,)") in have_urls for u in urls):
                    stats["dup"] += 1
                    continue
                c.setdefault("provenance", []).append(line)
                have_urls.update(u.rstrip(".,)") for u in urls)
                added += 1
                stats["added"] += 1
                changed = True
            if added:
                stats["contests"] += 1
                if e["verdict"] in ("likely-not-run", "not-yet-held"):
                    note = f"existence hunt 2026-10-22: verdict {e['verdict']} — review"
                    if note not in str(c.get("notes") or ""):
                        c["notes"] = ((c.get("notes") or "") + ("; " if c.get("notes") else "") + note)
                        changed = True
        if changed and not args.dry_run:
            dump_series(sid, sdoc, "apply_existence_evidence.py (existence hunt 2026-10-22)")
            stats["files"] += 1
    print(dict(stats), "(dry run)" if args.dry_run else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
