#!/usr/bin/env python3
"""Build data/resources.json: the resource graph (DEFINITIONS.md, "Resources").

Joins everything the project knows about each locator into one record:
  catalogue references  (series/*.yaml: results.*[], web, mirrors[], problemset)
  captures              (../archive/index.json when checked out, else data/archive-index.json)
  website crawls        (data/website-index.json + the crawl manifests when available)
  live-check verdicts   (../archive/reports/url-states-*-merged.json, newest per locator)
  published replay pages (data/replay-index.json)

Identifiers
  locator id  = first 12 hex of sha256(norm_key(url)) — stable across http/https, www,
                default ports, case and trailing-slash drift (tools/resources.py)
  resource id = <locator id>@<ts>, ts = Wayback-style timestamp at the precision known:
                the served snapshot for wayback-sourced captures, our fetch time for live
                ones, the dump time for API dumps, the catalogue's as_of when nothing is held.

Usage: python3 tools/build_resources.py            (also refreshes data/archive-index.json
                                                    from ../archive/index.json when present)
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT.parent / "archive"
sys.path.insert(0, str(ROOT / "tools"))
from resources import canon_url, norm_key, ts_from, unwrap  # noqa: E402

TIERS = ("scoreboard", "frozen_scoreboard", "standings", "rankings")


def lid(url: str) -> str:
    return hashlib.sha256(norm_key(url).encode()).hexdigest()[:12]


def main() -> int:
    # ---- captures: prefer the live archive index, mirror it into data/ ----
    live_idx = ARCHIVE / "index.json"
    if live_idx.exists():
        (ROOT / "data" / "archive-index.json").write_text(live_idx.read_text())
        print("data/archive-index.json refreshed from ../archive/index.json")
    captures = json.loads((ROOT / "data" / "archive-index.json").read_text())["captures"]
    replay = {}
    p = ROOT / "data" / "replay-index.json"
    if p.exists():
        for e in json.loads(p.read_text())["pages"]:
            replay[e["path"].removeprefix("a/")] = e["path"]
    websites = []
    p = ROOT / "data" / "website-index.json"
    if p.exists():
        websites = json.loads(p.read_text())["sites"]
    states: dict[str, dict] = {}
    reports = (sorted((ARCHIVE / "reports").glob("url-states-*-merged.json"))
               + sorted((ARCHIVE / "reports").glob("url-health-*.json"))) if ARCHIVE.exists() else []
    # lane files (url-health-<date>-Lkk.json) sort after the date; all are read, newest wins
    for rp in sorted(reports, key=lambda p: re.search(r"(\d{4}-\d{2}-\d{2})", p.name).group(1)):
        for s in json.loads(rp.read_text()):
            if s.get("state") in ("live", "changed", "replaced", "dead", "unknown"):
                k = lid(s["raw_url"])
                cur = states.get(k)
                if not cur or (s.get("checked") or "") >= (cur.get("checked") or ""):
                    states[k] = s

    locs: dict[str, dict] = {}

    def loc(url: str) -> dict:
        url = canon_url(unwrap(url)[0])
        k = lid(url)
        L = locs.setdefault(k, {"id": k, "url": url, "key": norm_key(url), "refs": [], "resources": {}})
        return L

    def res(L: dict, ts: str | None, via: str | None) -> dict:
        ts = ts or "unknown"
        R = L["resources"].setdefault(ts, {"ts": ts, "via": via, "captures": [], "refs": [],
                                           "website": None, "held": False})
        if via and not R.get("via"):
            R["via"] = via
        return R

    # ---- catalogue references ----
    for f in sorted((ROOT / "series").glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        for c in doc["contests"]:
            cid = c["id"]

            def ref(url, field, e=None, as_of=None):
                L = loc(url)
                r = {"contest": cid, "field": field}
                if as_of:
                    r["as_of"] = as_of
                for k in ("url_state", "url_checked", "note", "archived"):
                    if e and e.get(k):
                        r[k] = e[k]
                L["refs"].append(r)
                if as_of:
                    res(L, as_of, None)["refs"].append({"contest": cid, "field": field})

            for kind, lst in (c.get("results") or {}).items():
                for e in lst:
                    ref(e["url"], kind, e, e.get("as_of"))
            w = c.get("web")
            for x in (w if isinstance(w, list) else [w]) if w else []:
                if isinstance(x, dict):
                    ref(x["url"], "web", x, x.get("as_of"))
                else:
                    ref(x, "web")
            for m in c.get("mirrors") or []:
                ref(m["url"], "mirror", m, m.get("as_of"))
            ps = c.get("problemset")
            if isinstance(ps, dict):
                ref(ps["url"], "problemset", ps, ps.get("as_of"))
            elif ps:
                ref(ps, "problemset")
            if c.get("icpc_standings"):
                ref(c["icpc_standings"], "icpc_standings")

    # ---- captures ----
    for cap in captures:
        url = cap.get("url")
        if not url:
            continue
        raw, inner_ts, via_wrap = unwrap(url)
        src = cap.get("source") or "live"
        ts = cap.get("wayback_timestamp") or unwrap(cap.get("wayback_url") or "")[1] or inner_ts
        if src == "wayback" or via_wrap:
            via = "wayback"
        elif src == "icpc-api-archive":
            via = "api-dump"
            ts = ts or ts_from(cap.get("fetched"))
        else:
            via = "live" if src == "live" else src
            ts = ts or ts_from(cap.get("fetched"))
        L = loc(raw)
        R = res(L, ts, via)
        R["held"] = True
        R["captures"].append({
            "path": cap["path"], "contest": cap["contest"], "artifact": cap["artifact"],
            "sha256": cap.get("sha256"), "size": cap.get("size"),
            "content_type": cap.get("content_type"), "fetched": cap.get("fetched"),
            "source": src, "fetch_url": cap.get("final_url") or url,
            "wrapper_fetched": bool(via_wrap and src != "wayback"),
            "caveat": cap.get("content_caveat"),
            "replay": replay.get(cap["path"]),
        })

    # ---- website crawls ----
    for w in websites:
        seed = w.get("seed_raw") or w.get("seed")
        if not seed:
            continue
        ts = w.get("wayback_timestamp") or ts_from(w.get("fetched"))
        via = "wayback" if w.get("mode") == "wayback" else "live"
        L = loc(seed)
        R = res(L, ts, via)
        R["held"] = True
        site = {"contest": w["contest"], "dir": w["dir"], "mode": w.get("mode"),
                "pages": w.get("pages"), "html_pages": w.get("html_pages"), "bytes": w.get("bytes"),
                "fetched": w.get("fetched"), "pivot": w.get("pivot"), "primary": w.get("primary"),
                "legacy_wrapper": bool(w.get("seed_raw")), "page_list": None}
        mf = ARCHIVE / w["dir"] / "site-manifest.json"
        if mf.exists():
            m = json.loads(mf.read_text())
            site["scopes"] = m.get("scopes")
            site["tool"] = m.get("tool")
            pl = []
            for u, pg in m.get("pages", {}).items():
                ru = unwrap(u)[0]
                pl.append([ru, pg.get("status"), pg.get("size"), pg.get("wayback_timestamp"),
                           pg.get("ctype", "").split(";")[0] if pg.get("ctype") else None])
            site["page_list"] = pl
            site["unfetched"] = len(m.get("unfetched_in_scope") or {})
            site["offsite"] = len(m.get("offsite_links") or [])
        if R["website"] is None or site["primary"]:
            R["website"] = site

    # ---- verdicts ----
    for k, L in locs.items():
        s = states.get(k)
        if s:
            L["health"] = {"state": s["state"], "checked": s.get("checked"),
                           "evidence": s.get("evidence"), "note": s.get("note")}
        else:
            for r in L["refs"]:
                if r.get("url_state"):
                    L["health"] = {"state": r["url_state"], "checked": r.get("url_checked")}
                    break
        L["resources"] = dict(sorted(L["resources"].items()))

    out = {"generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "tool": "build_resources.py/1.0",
           "locators": dict(sorted(locs.items(), key=lambda kv: kv[1]["key"]))}
    (ROOT / "data" / "resources.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    n_res = sum(len(L["resources"]) for L in locs.values())
    n_held = sum(1 for L in locs.values() for R in L["resources"].values() if R["held"])
    print(f"{len(locs)} locators, {n_res} resources ({n_held} held) -> data/resources.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
