#!/usr/bin/env python3
"""
fetch_icpc_global_standings.py — local copies of every icpc.global standings page

    https://icpc.global/regionals/finder/<contest>/standings

That page is a JS shell; its table is filled from the public API
    /api/contest/public/search/contest/{contestId}?q=&page=N&size=S
The page defaults to size=10. This script asks for size=1000 ("Rows per page"
= 1000) and keeps fetching further pages while a page comes back full, so
contests with more than 1000 rows are complete too. Rows are stored exactly
as the API returns them.

Contests are enumerated from /api/contest/public/regionalresults/{year} for
every year the API serves (1977 onward), and EVERY node is fetched, including
those whose metadata claims 0 results.

Output (default ../archive/icpc-global-standings/, in the archive repo next to this one):
  trees/<year>.json        raw regionalresults tree per ICPC year
  standings/<slug>.json    one file per contest; <slug> is the <contest> part
                           of the URL (abbreviation-icpcYear)
  index.csv                one line per contest: id, slug, rows, pages, status

Usage:
  python3 tools/fetch_icpc_global_standings.py              # fetch what is missing
  python3 tools/fetch_icpc_global_standings.py --force      # refetch everything
  python3 tools/fetch_icpc_global_standings.py --refresh-trees
  python3 tools/fetch_icpc_global_standings.py --only World-Finals-2026
"""
from __future__ import annotations

import argparse, csv, json, os, re, sys, threading, time
import urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

API = "https://icpc.global/api/contest/public"
UA = "icpc-data-tools/0.1 (research; github.com/niemela/icpc-data)"
FIRST_YEAR = 1977
HERE = os.path.dirname(os.path.abspath(__file__))
_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, file=sys.stderr, flush=True)


def get(url, retries=5):
    """Return (parsed_json, None) or (None, error_string)."""
    err = "?"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
            return (json.loads(body.decode("utf-8")) if body.strip() else None), None
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
            if e.code in (400, 404):
                return None, err
            time.sleep(min(60, 3 * 2 ** attempt))
        except Exception as e:  # network, timeout, bad JSON
            err = f"{type(e).__name__}: {e}"
            time.sleep(min(60, 3 * 2 ** attempt))
    return None, err


def write_json(path, obj):
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def load_trees(out, refresh, last_year):
    tdir = os.path.join(out, "trees")
    os.makedirs(tdir, exist_ok=True)
    contests = {}

    def walk(node, parent):
        cid = node.get("contestId")
        if cid is None:
            return
        contests[cid] = {k: v for k, v in node.items() if k != "subcontests"}
        contests[cid]["parentId"] = parent
        for ch in node.get("subcontests") or []:
            walk(ch, cid)

    for year in range(FIRST_YEAR, last_year + 1):
        path = os.path.join(tdir, f"{year}.json")
        if refresh or not os.path.exists(path):
            data, err = get(f"{API}/regionalresults/{year}")
            if err:
                log(f"tree {year}: {err}")
                continue
            if data is None:
                continue
            write_json(path, data)
            time.sleep(0.2)
        walk(json.load(open(path, encoding="utf-8")), None)
    return contests


def assign_slugs(contests):
    """<abbreviation>-<icpcYear>, as in the URL; disambiguated by id on clash."""
    seen = {}
    for cid in sorted(contests):
        c = contests[cid]
        abbr, yr = c.get("abbreviation") or "", c.get("icpcYear")
        slug = f"{abbr}-{yr}" if abbr and yr is not None else f"id-{cid}"
        c["urlSlug"] = slug if abbr and yr is not None else ""
        fname = re.sub(r"[^A-Za-z0-9._-]", "_", slug)
        if fname.lower() in seen:
            fname = f"{fname}--{cid}"
        seen[fname.lower()] = cid
        c["file"] = fname


def fetch_one(c, sdir, size, force, delay):
    path = os.path.join(sdir, c["file"] + ".json")
    if not force and os.path.exists(path):
        return "cached"
    rows, page = [], 1
    while True:
        data, err = get(f"{API}/search/contest/{c['contestId']}?q=&page={page}&size={size}")
        time.sleep(delay)
        if err:
            log(f"FAIL {c['file']} (id {c['contestId']}) page {page}: {err}")
            return "error: " + err
        if not isinstance(data, list):
            data = []
        rows.extend(data)
        if len(data) < size:
            break
        page += 1
    write_json(path, {
        "contestId": c["contestId"],
        "url": f"https://icpc.global/regionals/finder/{c['urlSlug']}/standings" if c["urlSlug"] else "",
        "api": f"{API}/search/contest/{c['contestId']}?q=&page=1..{page}&size={size}",
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pageSize": size,
        "pages": page,
        "contest": {k: v for k, v in c.items() if k not in ("file", "urlSlug")},
        "rowCount": len(rows),
        "rows": rows,
    })
    return "fetched"


def write_index(contests, out):
    sdir = os.path.join(out, "standings")
    cols = ["id", "file", "url", "name", "icpc_year", "parent_id", "results_meta", "rows", "pages", "fetched", "status"]
    with open(os.path.join(out, "index.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for cid in sorted(contests, key=lambda i: (contests[i].get("icpcYear") or 0, i)):
            c = contests[cid]
            p = os.path.join(sdir, c["file"] + ".json")
            rows = pages = fetched = ""
            status = "missing"
            if os.path.exists(p):
                d = json.load(open(p, encoding="utf-8"))
                rows, pages, fetched, status = d["rowCount"], d["pages"], d["fetched"], "ok"
            w.writerow([cid, c["file"] + ".json",
                        f"https://icpc.global/regionals/finder/{c['urlSlug']}/standings" if c["urlSlug"] else "",
                        c.get("contestName") or "", c.get("icpcYear"), c.get("parentId") or "",
                        c.get("results") if c.get("results") is not None else "", rows, pages, fetched, status])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(HERE)), "archive", "icpc-global-standings"))
    ap.add_argument("--size", type=int, default=1000, help="rows per page (default 1000)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--delay", type=float, default=0.25, help="pause after each request, per worker")
    ap.add_argument("--last-year", type=int, default=datetime.now().year + 1)
    ap.add_argument("--refresh-trees", action="store_true")
    ap.add_argument("--force", action="store_true", help="refetch standings that already exist")
    ap.add_argument("--only", help="comma-separated slugs or contest ids")
    ap.add_argument("--index-only", action="store_true")
    a = ap.parse_args()

    sdir = os.path.join(a.out, "standings")
    os.makedirs(sdir, exist_ok=True)
    contests = load_trees(a.out, a.refresh_trees, a.last_year)
    assign_slugs(contests)
    todo = list(contests.values())
    if a.only:
        want = set(a.only.split(","))
        todo = [c for c in todo if c["file"] in want or c["urlSlug"] in want or str(c["contestId"]) in want]
    log(f"{len(contests)} contests in trees; {len(todo)} selected")

    counts, n = {}, [0]
    if not a.index_only:
        def job(c):
            try:
                res = fetch_one(c, sdir, a.size, a.force, a.delay)
            except Exception as e:
                res = f"error: {type(e).__name__}: {e}"
                log(f"FAIL {c['file']}: {res}")
            with _print_lock:
                k = res.split(":")[0]
                counts[k] = counts.get(k, 0) + 1
                n[0] += 1
                if n[0] % 100 == 0:
                    print(f"  {n[0]}/{len(todo)} {counts}", file=sys.stderr, flush=True)
        with ThreadPoolExecutor(a.workers) as ex:
            list(ex.map(job, todo))
    write_index(contests, a.out)
    log(f"done: {counts}; index at {os.path.join(a.out, 'index.csv')}")
    return 1 if counts.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
