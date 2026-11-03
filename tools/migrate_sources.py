#!/usr/bin/env python3
"""One-off migration to the `sources:` model (2026-11-02; DEFINITIONS.md, Resources).

Before, a URL's type was the field it sat in — `web`, `mirrors[]`, `problemset`,
`results.<kind>[]`, `icpc_standings`, `problems.judges.<judge>` — so a page that was
both the results and the problem set was entered twice (689 URLs were). After, a
contest has one `sources:` list, one entry per address, each with its `roles`.

  web / problemset / results.<kind> / icpc_standings  -> source with that role
  problems.judges.<judge>                             -> source with role judge_page, judge: <judge>
  mirrors[]                                           -> `also_at` on the web source, {url, as_of}
                                                         when the mirror had its own as_of (dropped
                                                         when the mirror URL already is a source)
  field: null (confirmed none)                        -> none: [<role>]
  mirrors: []                                         -> dropped (not a role)
  sources: [free text]  (provenance)                  -> provenance: [...]

Entries sharing an address merge: roles union; every `archived` capture kept (list);
first `as_of` kept, others noted; url_state from the most recent url_checked. The run ends with a URL-for-URL
equivalence check: the set of (contest, address, role) before and after is identical.

Usage: python3 tools/migrate_sources.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import yaml  # noqa: E402
from catalogue import RANK, Dumper, dump_series, load_series, normalise_contest, primary_role  # noqa: E402
from resources import norm_key, unwrap  # noqa: E402

RESULT_KINDS = ("scoreboard", "frozen_scoreboard", "standings", "rankings")


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def entry(v, role: str, **extra) -> dict:
    """Old-style value (str or {url, ...}) -> new source dict (wrapper URLs unwrapped)."""
    e = {"url": v} if isinstance(v, str) else dict(v)
    u, ts, via = unwrap(e["url"])
    if via:
        e["url"] = u
        if ts and not e.get("as_of"):
            e["as_of"] = ts
    e["roles"] = [role]
    if "archived" in e:
        e["archived"] = e["archived"] if isinstance(e["archived"], list) else [e["archived"]]
    for k, val in extra.items():
        if val is not None:
            e[k] = val
    return e


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    stats = Counter()
    log: list[str] = []
    before: set[tuple] = set()
    after: set[tuple] = set()

    def convert(c: dict) -> dict:
        if True:
            cid = c["id"]
            raw: list[dict] = []
            none: list[str] = []
            # ---- collect old-style entries ----
            if "web" in c:
                if c["web"] is None:
                    none.append("web")
                for v in as_list(c.pop("web")):
                    raw.append(entry(v, "web"))
            if "problemset" in c:
                if c["problemset"] is None:
                    none.append("problemset")
                for v in as_list(c.pop("problemset")):
                    raw.append(entry(v, "problemset"))
            for kind in RESULT_KINDS:
                for v in (c.get("results") or {}).get(kind) or []:
                    raw.append(entry(v, kind))
            if "results" in c:
                res = c.pop("results")
                for kind in RESULT_KINDS:
                    if kind in (res or {}) and res[kind] is None:
                        none.append(kind)
            if "icpc_standings" in c:
                if c["icpc_standings"] is None:
                    none.append("icpc_standings")
                for v in as_list(c.pop("icpc_standings")):
                    raw.append(entry(v, "icpc_standings"))
            judges = (c.get("problems") or {}).pop("judges", None) if c.get("problems") else None
            for judge, v in (judges or {}).items():
                for x in as_list(v):
                    raw.append(entry(x, "judge_page", judge=judge))
            mirrors = c.pop("mirrors", None)
            if mirrors == []:
                stats["mirrors: [] dropped"] += 1
            if "sources" in c:  # old provenance list
                c["provenance"] = c.pop("sources")
                stats["sources -> provenance"] += 1

            for e in raw:
                before.add((cid, norm_key(e["url"]), e["roles"][0]))

            # ---- merge by address ----
            merged: dict[str, dict] = {}
            order: list[str] = []
            for e in raw:
                k = norm_key(e["url"])
                if k not in merged:
                    merged[k] = e
                    order.append(k)
                    continue
                m = merged[k]
                role = e["roles"][0]
                if role not in m["roles"]:
                    m["roles"].append(role)
                stats["merged duplicate"] += 1
                if e.get("archived"):
                    for a in (e["archived"] if isinstance(e["archived"], list) else [e["archived"]]):
                        if a not in m.setdefault("archived", []):
                            m["archived"].append(a)
                            stats["second capture kept"] += 1
                for f in ("as_of", "fetched"):
                    if e.get(f):
                        if not m.get(f):
                            m[f] = e[f]
                        elif str(e[f]) != str(m[f]):
                            m["note"] = (m.get("note", "") + "; " if m.get("note") else "") + \
                                f"{f} {e[f]} for {role}"
                            stats[f"{f} differs (noted)"] += 1
                            log.append(f"{cid}: {k}: {f} {m[f]} ({primary_role(m)}) vs {e[f]} ({role})")
                if e.get("url_checked") and (not m.get("url_checked") or e["url_checked"] > m["url_checked"]):
                    m["url_checked"] = e["url_checked"]
                    if e.get("url_state"):
                        m["url_state"] = e["url_state"]
                if e.get("judge") and not m.get("judge"):
                    m["judge"] = e["judge"]
                if e.get("note") and e["note"] not in (m.get("note") or ""):
                    m["note"] = (m["note"] + "; " if m.get("note") else "") + e["note"]
            # ---- mirrors -> also_at on the web source ----
            for mir in mirrors or []:
                mu = mir["url"] if isinstance(mir, dict) else mir
                mu, mts, mvia = unwrap(mu)
                if mvia and mts:
                    mir = {**(mir if isinstance(mir, dict) else {"url": mu}), "url": mu, "as_of": mts}
                if norm_key(mu) in merged:
                    stats["mirror already a source (dropped)"] += 1
                    continue
                webs = [merged[k] for k in order if "web" in merged[k]["roles"]]
                if not webs:
                    # a mirror of a site we have no web entry for: it IS our web address
                    e = {"url": mu, "roles": ["web"]}
                    if isinstance(mir, dict) and mir.get("as_of"):
                        e["as_of"] = mir["as_of"]
                    if isinstance(mir, dict) and mir.get("note"):
                        e["note"] = mir["note"]
                    merged[norm_key(mu)] = e
                    order.append(norm_key(mu))
                    stats["mirror promoted to web (no web entry)"] += 1
                    log.append(f"{cid}: mirror {mu} promoted to web")
                    continue
                w = webs[0]
                if isinstance(mir, dict) and mir.get("as_of"):
                    w.setdefault("also_at", []).append({"url": mu, "as_of": mir["as_of"]})
                    stats["mirror -> also_at (with as_of)"] += 1
                else:
                    w.setdefault("also_at", []).append(mu)
                stats["mirror -> also_at"] += 1
            # ---- finalise ----
            srcs = [merged[k] for k in order]
            for s in srcs:
                s["roles"].sort(key=lambda r: RANK[r])
            srcs.sort(key=lambda s: RANK[primary_role(s)])
            if srcs:
                c["sources"] = srcs
            if none:
                c["none"] = sorted(set(none), key=lambda r: RANK[r])
            if c.get("problems") == {}:
                del c["problems"]
            for s in srcs:
                for r in s["roles"]:
                    after.add((cid, norm_key(s["url"]), r))
            stats["contests"] += 1
            stats["sources"] += len(srcs)
            return normalise_contest(c)

    for sid, doc in load_series().items():
        doc["contests"] = [convert(c) for c in doc["contests"]]
        if not args.dry_run:
            dump_series(sid, doc, "migrate_sources.py (sources model, 2026-11-02)")
    reg = ROOT / "registry" / "non-mainline.yaml"
    rdoc = yaml.safe_load(reg.read_text())
    rdoc["non_mainline_contests"] = [convert(c) for c in rdoc["non_mainline_contests"]]
    if not args.dry_run:
        head = "".join(l for l in reg.read_text().splitlines(True)[:2] if l.startswith("#"))
        reg.write_text(head + yaml.dump(rdoc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))

    # ---- equivalence ----
    missing = before - after
    extra = after - before
    print({k: v for k, v in sorted(stats.items())})
    print(f"equivalence: before {len(before)} (contest,address,role) triples, after {len(after)}; "
          f"missing {len(missing)}, extra {len(extra)}")
    for t in sorted(missing)[:10]:
        print("  MISSING", t)
    for t in sorted(extra)[:10]:
        print("  EXTRA  ", t)
    rep = ROOT / "reports" / "migrate-sources-2026-11-02.log"
    if not args.dry_run:
        rep.write_text("\n".join(log) + "\n")
        print(f"log -> {rep.relative_to(ROOT)} ({len(log)} lines)")
    return 1 if missing or extra else 0


if __name__ == "__main__":
    sys.exit(main())
