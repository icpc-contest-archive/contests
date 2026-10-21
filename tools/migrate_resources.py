#!/usr/bin/env python3
"""One-off migration to the resource model (DEFINITIONS.md, "Resources").

For every locator field in the catalogue (`results.*[].url`, `web`, `mirrors[].url`,
`problemset`):
  - an archive-wrapper URL (web.archive.org/web/<ts>/<url>) becomes the bare `url`
    plus `as_of: <ts>`; a `web` string becomes `{url, as_of}`
  - the old `wayback` field (a full snapshot URL) becomes `as_of` when its inner URL
    is the entry's own URL; otherwise its timestamp is still kept as `as_of` and the
    mismatch is noted (it was the snapshot we verified content at)
  - a calendar link (`/web/*/`) is dropped: it carries no time
  - cross-check: when the entry has `archived` and the archive index knows the
    capture's snapshot timestamp, prefer that (it is the timestamp Wayback actually
    served, not the one we asked for)

Usage: python3 tools/migrate_resources.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from resources import norm_key, unwrap  # noqa: E402


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(
    type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null")
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cap_ts = {}  # archived path -> wayback_timestamp
    idx = ROOT / "data" / "archive-index.json"
    if idx.exists():
        for cap in json.loads(idx.read_text())["captures"]:
            if cap.get("wayback_timestamp"):
                cap_ts[cap["path"]] = cap["wayback_timestamp"]

    stats = Counter()
    log = []

    def fix_entry(cid: str, where: str, e: dict) -> None:
        """Entry with `url` (+ maybe `wayback`, `archived`)."""
        url, ts, via = unwrap(e["url"])
        if via:
            e["url"] = url
            if ts:
                e["as_of"] = ts
                stats["url unwrapped -> as_of"] += 1
            else:
                stats["url unwrapped (calendar link, no time)"] += 1
            log.append(f"{cid} {where}: unwrapped {via} link -> {url} as_of={ts}")
        wb = e.pop("wayback", None)
        if wb:
            wurl, wts, wvia = unwrap(wb)
            if wts:
                if norm_key(wurl) != norm_key(e["url"]):
                    e.setdefault("note", "")
                    e["note"] = (e["note"] + "; " if e["note"] else "") + \
                        f"snapshot verified at a different locator: {wurl}"
                    stats["wayback field: inner url differs (noted)"] += 1
                if not e.get("as_of"):
                    e["as_of"] = wts
                    stats["wayback field -> as_of"] += 1
                elif e["as_of"] != wts:
                    stats["wayback field ts differs from url ts (url ts kept)"] += 1
            else:
                stats["wayback field was a calendar link (dropped)"] += 1
        if e.get("archived") and cap_ts.get(e["archived"]):
            real = cap_ts[e["archived"]]
            if e.get("as_of") and e["as_of"] != real and not real.startswith(e["as_of"]):
                stats["as_of corrected to capture's served snapshot"] += 1
                log.append(f"{cid} {where}: as_of {e['as_of']} -> {real} (served snapshot)")
                e["as_of"] = real
            elif not e.get("as_of"):
                e["as_of"] = real
                stats["as_of from capture snapshot"] += 1
    def reorder(e: dict) -> dict:
        if "as_of" not in e:
            return e
        out = {"url": e["url"], "as_of": e["as_of"]}
        out.update({k: v for k, v in e.items() if k not in out})
        return out

    for f in sorted((ROOT / "series").glob("*.yaml")):
        text = f.read_text()
        doc = yaml.safe_load(text)
        before = json.dumps(doc, sort_keys=True, ensure_ascii=False)
        for c in doc["contests"]:
            cid = c["id"]
            # results
            for kind, lst in (c.get("results") or {}).items():
                for i, e in enumerate(lst):
                    keep = dict(e)
                    fix_entry(cid, f"results.{kind}", keep)
                    lst[i] = reorder(keep)
            # web
            if c.get("web") is not None:
                ws = c["web"] if isinstance(c["web"], list) else [c["web"]]
                out = []
                for w in ws:
                    if isinstance(w, dict):
                        keep = dict(w)
                        fix_entry(cid, "web", keep)
                        out.append(reorder(keep))
                        continue
                    url, ts, via = unwrap(w)
                    if via:
                        stats["web unwrapped"] += 1
                        log.append(f"{cid} web: {w[:80]} -> {url} as_of={ts}")
                        out.append({"url": url, "as_of": ts} if ts else url)
                    else:
                        out.append(w)
                c["web"] = out[0] if len(out) == 1 else out
            # mirrors
            for m in c.get("mirrors") or []:
                url, ts, via = unwrap(m["url"])
                if via:
                    m["url"] = url
                    if ts:
                        m["as_of"] = ts
                    stats["mirror unwrapped"] += 1
            # problemset
            if isinstance(c.get("problemset"), str):
                url, ts, via = unwrap(c["problemset"])
                if via:
                    c["problemset"] = {"url": url, "as_of": ts} if ts else url
                    stats["problemset unwrapped"] += 1
        after = json.dumps(doc, sort_keys=True, ensure_ascii=False)
        if after != before:
            stats["files changed"] += 1
            if not args.dry_run:
                header = "# Maintained in-repo; resource model migration (tools/migrate_resources.py)."
                f.write_text(header + "\n" + yaml.dump(doc, Dumper=Dumper, sort_keys=False,
                                                       allow_unicode=True, width=100))
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    (ROOT / "reports" / "migrate-resources.log").write_text("\n".join(log) + "\n")
    print(f"{len(log)} log lines -> reports/migrate-resources.log")
    print("dry run, nothing written" if args.dry_run else "now run: python3 tools/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
