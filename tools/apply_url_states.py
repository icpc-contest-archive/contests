#!/usr/bin/env python3
"""Apply the capture run's url-state verdicts to the catalogue.

Reads the newest archive/reports/url-states-*.json and, per matching source (the
verdict's contest + catalogue_url, matched by address whatever roles it serves):
  - normalizes wayback-link entries: url -> raw origin URL, the snapshot
    timestamp moves into `as_of` (kept if already set)
  - records the snapshot used (`as_of`) when the source had none
  - sets url_state (live|changed|replaced|dead|unknown) + url_checked

Verdicts for also_at mirror addresses (kind web-mirror) have no source entry of their
own and are left alone, as before.

Run from the contests repo root; validate afterwards.
"""
from __future__ import annotations

VERDICTS = {"live", "changed", "replaced", "dead", "unknown"}
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import RANK, dump_series, find_source, load_series  # noqa: E402
from resources import unwrap  # noqa: E402


def main() -> int:
    reports = sorted((ROOT.parent / "archive" / "reports").glob("url-states-*.json"))
    if not reports:
        print("no url-states report found")
        return 1
    # the newest day's merged report (reconcile_states.py) beats that day's single-lane file
    day = re.search(r"url-states-(\d{4}-\d{2}-\d{2})", reports[-1].name).group(1)
    merged = reports[-1].with_name(f"url-states-{day}-merged.json")
    if merged.exists():
        reports[-1] = merged
    states = json.loads(reports[-1].read_text())
    # one address may have been checked under several kinds (pre-sources-model queues, or a
    # source serving several roles): the most recent verdict per source wins, ties going to
    # the verdict made for the highest-ranked role (RANK: scoreboard before problemset ...)
    def rank(kind: str) -> int:
        return RANK.get("judge_page" if kind.startswith("judge-") else kind, len(RANK))

    def better(a: dict, b: dict) -> bool:
        return ((a.get("checked") or ""), -rank(a["kind"])) > ((b.get("checked") or ""), -rank(b["kind"]))

    by_contest: dict[str, list[dict]] = {}
    for s in states:
        by_contest.setdefault(s["contest"], []).append(s)
    print(f"applying {len(states)} verdicts from {reports[-1].name}")

    stats = Counter()
    for sid, doc in load_series().items():
        changed = False
        for c in doc["contests"]:
            applied: dict[int, dict] = {}   # id(source) -> verdict applied
            for s in by_contest.get(c["id"], []):
                e = find_source(c, s["catalogue_url"]) or find_source(c, s["raw_url"])
                if e is None:
                    stats[f"no source for verdict kind {s['kind']}"] += 1
                    continue
                prev = applied.get(id(e))
                if prev and not better(s, prev):
                    continue
                applied[id(e)] = s
                if s["catalogue_url"] != s["raw_url"] and unwrap(e["url"])[2]:
                    # wayback-link entry: url becomes the raw origin URL
                    _, ts, _ = unwrap(e["url"])
                    if ts and not e.get("as_of"):
                        e["as_of"] = ts
                    e["url"] = s["raw_url"]
                    stats["normalized wayback-link entry"] += 1
                    changed = True
                ts = s.get("wayback_timestamp") or unwrap(s.get("wayback_url") or "")[1]
                if ts and not e.get("as_of"):
                    e["as_of"] = ts
                    stats["wayback snapshot recorded (as_of)"] += 1
                    changed = True
                if s["state"] not in VERDICTS:
                    # reconcile_states' provisional "captured-unverdicted" rows (manifest but no
                    # verdict): the capture is already in the index; the as_of above is all we take
                    stats[f"provisional row skipped ({s['state']})"] += 1
                    continue
                if s["state"] == "unknown" and e.get("url_state") in VERDICTS - {"unknown"}:
                    # an IA-only lane (or a live lane that skipped the address) has no opinion
                    # on the origin: never let "no live capture to judge" erase a real verdict
                    stats[f"unknown kept as {e['url_state']}"] += 1
                    continue
                if e.get("url_state") != s["state"]:
                    stats[f"state -> {s['state']}"] += 1
                if (e.get("url_state"), e.get("url_checked")) != (s["state"], s["checked"]):
                    changed = True
                e["url_state"], e["url_checked"] = s["state"], s["checked"]
                stats["verdicts applied"] += 1
        if changed:
            dump_series(sid, doc, "apply_url_states.py")
            stats["files written"] += 1
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print("now run: python3 tools/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
