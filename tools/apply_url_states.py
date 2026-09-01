#!/usr/bin/env python3
"""Apply the capture run's url-state verdicts to the catalogue.

Reads the newest archive/reports/url-states-*.json and, per matching result entry:
  - normalizes wayback-link entries: url -> raw origin URL, the snapshot link
    moves into `wayback` (kept if already set)
  - records the snapshot used (`wayback`) when the entry had none
  - sets url_state (live|changed|replaced|dead|unknown) + url_checked

Run from the contests repo root; validate afterwards.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(
    type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null")
)


def main() -> int:
    reports = sorted((ROOT.parent / "archive" / "reports").glob("url-states-*.json"))
    if not reports:
        print("no url-states report found")
        return 1
    states = json.loads(reports[-1].read_text())
    by_key = {(s["contest"], s["kind"], s["catalogue_url"]): s for s in states}
    print(f"applying {len(by_key)} verdicts from {reports[-1].name}")

    stats = Counter()
    for f in sorted((ROOT / "series").glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        changed = False
        for c in doc["contests"]:
            for kind, lst in c.get("results", {}).items():
                for e in lst:
                    s = by_key.get((c["id"], kind, e["url"]))
                    if not s:
                        continue
                    if s["catalogue_url"] != s["raw_url"]:
                        # wayback-link entry: url becomes the raw origin URL
                        if not e.get("wayback"):
                            e["wayback"] = s["catalogue_url"]
                        e["url"] = s["raw_url"]
                        stats["normalized wayback-link entry"] += 1
                    if s.get("wayback_url") and not e.get("wayback"):
                        e["wayback"] = s["wayback_url"]
                        stats["wayback snapshot recorded"] += 1
                    if e.get("url_state") != s["state"]:
                        stats[f"state -> {s['state']}"] += 1
                    e["url_state"], e["url_checked"] = s["state"], s["checked"]
                    changed = True
        if changed:
            header = ("# Maintained in-repo; url states applied by "
                      "tools/apply_url_states.py.\n")
            f.write_text(header + yaml.dump(doc, Dumper=Dumper, sort_keys=False,
                                            allow_unicode=True, width=100))
            stats["files written"] += 1
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print("now run: python3 tools/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
