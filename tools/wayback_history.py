#!/usr/bin/env python3
"""Ask the Wayback Machine what an address held around a contest (rulings 16 and 17).

  python3 tools/wayback_history.py --name run-2026-11-15 [--budget 150]     # resumable; run until "done"
  python3 tools/wayback_history.py --name run-2026-11-15 --decide [--write]

Reads data/content-check/<run>/lists/year-reused.json (an address whose copy shows another
edition) and not-document.json (a copy that is not the document). For each address it lists the
Wayback captures, fetches a few promising ones and looks for the contest's year in them.

year-reused, the window being from 200 days before the contest to 60 days before the next edition:
  keep      a capture in the window names the year: the source stays, as_of names that capture
  lost      the address (or its host) was known to Wayback by then, but no capture in the window
            names the year: the source stays without as_of and without a copy
  remove    Wayback first saw the host more than a year after the window: nothing shows the
            address ever served this edition
  review    the copy is about another series and no capture names this contest: left alone
not-document:
  snapshot  another capture names the year and is not the bad copy: queue it
  browser   only a live copy exists or every capture is a shell: needs a browser capture
  none      nothing better found
--decide writes lists/year-reused-resolved.json and lists/recapture.json; with --write it also
edits the catalogue and writes ../archive/capture-queue-<day>.json and
../archive/reports/content-check-<day>.json (the copies to mark as not the document).
"""
import argparse, datetime, hashlib, json, re, sys, threading, time, urllib.parse, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import catalogue as cat
from resources import unwrap
from make_capture_queue import capture_kind

ROOT = Path(__file__).resolve().parent.parent
UA = "icpc-contests-archive/1.0 (wayback history; contact via icpc.global)"
LOCK = threading.Lock()
# hosts whose pages are built in the browser or sit behind a login: a Wayback copy is a shell too
BROWSER_ONLY = {"www.facebook.com", "qoj.ac", "board.xcpcio.com", "ac.nowcoder.com", "github.com", "drive.google.com"}


def get(url, timeout=20):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(3_000_000), r.headers.get("Content-Type", "")
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            if "404" in err:
                break
            time.sleep(1)
    return None, err


def cdx(raw, **extra):
    q = {"url": raw, "output": "json", "fl": "timestamp,statuscode,digest,length", "limit": "4000", **extra}
    body, info = get("https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(q))
    if body is None:
        return None
    try:
        rows = json.loads(body or b"[]")
    except ValueError:
        return None
    return rows[1:] if rows else []


def text_of(body, ctype):
    if b"%PDF" in body[:1024]:
        return body.decode("latin-1", "replace")
    t = body.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def window(c, contests):
    d = str(c.get("date") or "")
    year = int(c["id"].rsplit("-", 1)[-1])
    try:
        day = datetime.date.fromisoformat(d)
    except ValueError:
        day = datetime.date(year, 11, 1)
    nx = c.get("next")
    nxt = contests.get((nx[0] if isinstance(nx, list) and nx else nx) or "")
    try:
        end = datetime.date.fromisoformat(str(nxt.get("date"))) - datetime.timedelta(days=60)
    except Exception:
        end = day + datetime.timedelta(days=300)
    if end <= day:
        end = day + datetime.timedelta(days=120)
    f = lambda x: x.strftime("%Y%m%d")
    return f(day - datetime.timedelta(days=200)), f(day), f(end), str(day.year)


def good(hit) -> bool:
    """A fetched capture that names the contest's year and is not the copy already judged bad."""
    return bool(hit.get("names_year")) and not hit.get("same_as_bad") and hit.get("text", 0) > 80


def study(job, contests, packs):
    cid, url, kind = job["contest"], job["url"], job["list"]
    c = contests[cid]
    raw = unwrap(url)[0]
    start, day, end, year = window(c, contests)
    out = {"contest": cid, "url": url, "list": kind, "window": [start, end], "year": year}
    if kind == "not-document" and urllib.parse.urlsplit(raw).netloc in BROWSER_ONLY:
        return dict(out, captures=0, first=None, tried=[], skipped="host needs a browser")
    rows = cdx(raw)
    if rows is None:
        return None  # try again on a later run
    ok = [r for r in rows if r[1] == "200"]
    out["captures"] = len(rows)
    out["first"] = rows[0][0] if rows else None
    bad_sha = ((packs(cid).get(url) or {}).get("copy") or {}).get("sha256") or "-"
    if kind == "year-reused":
        inw = [r for r in ok if start <= r[0][:8] <= end]
        cands = sorted([r for r in inw if r[0][:8] >= day], key=lambda r: r[0]) + \
            sorted([r for r in inw if r[0][:8] < day], key=lambda r: r[0], reverse=True)
        out["in_window"] = len(inw)
    else:
        cands = sorted(ok, key=lambda r: (r[0][:8] < day, abs(int(r[0][:8]) - int(day))))
    seen, tried = set(), []
    for ts, _st, dig, _ln in cands:
        if dig in seen:
            continue
        seen.add(dig)
        if len(tried) >= 3:
            break
        body, ctype = get(f"https://web.archive.org/web/{ts}id_/{raw}")
        if body is None:
            tried.append({"ts": ts, "error": ctype[:80]})
            continue
        txt = text_of(body, ctype)
        sha = hashlib.sha256(body).hexdigest()
        hit = {"ts": ts, "size": len(body), "text": len(txt), "names_year": bool(re.search(rf"(?<!\d){year}(?!\d)", txt)),
               "same_as_bad": sha.startswith(bad_sha), "title": (re.search(r"(?is)<title[^>]*>(.*?)</title>", body.decode("utf-8", "replace")) or [None, ""])[1].strip()[:90]}
        tried.append(hit)
        if good(hit):
            out["pick"] = ts
            break
    out["tried"] = tried
    if kind == "year-reused" and "pick" not in out and (out["first"] or "9")[:8] > end:
        host = urllib.parse.urlsplit(raw).netloc
        h = cdx(host + "/", limit="1")
        out["host_first"] = h[0][0] if h else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--packs", default="../_content-check/run1")
    ap.add_argument("--budget", type=int, default=150, help="seconds to work before stopping")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--accept-errors", action="store_true", help="keep results even when a fetch failed")
    ap.add_argument("--decide", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    run = ROOT / "data" / "content-check" / a.name
    L = run / "lists"
    series = cat.load_series()
    contests = {c["id"]: c for doc in series.values() for c in doc["contests"]}
    sid_of = {c["id"]: sid for sid, doc in series.items() for c in doc["contests"]}
    _p = {}

    def packs(cid):
        if cid not in _p:
            try:
                _p[cid] = {s["url"]: s for s in json.loads((Path(a.packs) / cid / "pack.json").read_text())["sources"]}
            except OSError:
                _p[cid] = {}
        return _p[cid]
    jobs = []
    for k in ("year-reused", "not-document"):
        for r in json.loads((L / f"{k}.json").read_text()):
            if r["contest"] in contests:
                jobs.append(dict(r, list=k))
    cache_p = run / "wayback-history.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    key = lambda j: f'{j["list"]}|{j["contest"]}|{j["url"]}'
    if not a.decide:
        todo = [j for j in jobs if key(j) not in cache]
        stop = time.time() + a.budget
        failed = []
        print(f"{len(jobs)} addresses, {len(todo)} to ask about")

        def work(j):
            if time.time() > stop:
                return
            try:
                r = study(j, contests, packs)
            except Exception as e:
                print("error", key(j), type(e).__name__, e)
                return
            if r is not None and not a.accept_errors and any(x.get("error") for x in r["tried"]) and "pick" not in r:
                with LOCK:
                    failed.append(key(j))
                return
            if r is not None:
                with LOCK:
                    cache[key(j)] = r
                    if len(cache) % 15 == 0:
                        cache_p.write_text(json.dumps(cache, indent=0, ensure_ascii=False))
        with ThreadPoolExecutor(a.workers) as ex:
            list(ex.map(work, todo))
        cache_p.write_text(json.dumps(cache, indent=0, ensure_ascii=False))
        left = sum(1 for j in jobs if key(j) not in cache)
        print("done" if not left else f"{left} left" + (f" ({len(failed)} had a fetch fail; run again, or pass "
                                                        "--accept-errors to settle for what was read)" if failed else ""))
        return 0

    day_tag = a.name.replace("run-", "")
    resolved, recapture, queue, marks = [], [], [], []
    touched = set()
    for j in jobs:
        h = cache.get(key(j))
        cid, url = j["contest"], j["url"]
        c = contests[cid]
        s = cat.find_source(c, url)
        copy = (packs(cid).get(url) or {}).get("copy") or {}
        if s is None:
            continue
        pending = h is None
        h = dict(h or {"window": list(window(c, contests)[0:3:2])})
        h["pick"] = next((x["ts"] for x in h.get("tried") or [] if good(x)), None)
        row = {"contest": cid, "url": url, "roles": s["roles"], "was": j["verdict"], "evidence": j.get("evidence"),
               "belongs_to": j.get("belongs_to"), "captures": h.get("captures"), "first": h.get("first"),
               "tried": h.get("tried"), "copy": copy.get("path")}
        if copy.get("path"):
            why = ("shows another edition" + (f" ({j['belongs_to']})" if j.get("belongs_to") else "")
                   if j["list"] == "year-reused" else "not the document")
            marks.append({"path": copy["path"], "contest": cid, "url": url,
                          "caveat": f"content check {day_tag}: {why}: {(j.get('evidence') or '')[:160]}"})
        kind = capture_kind(s)
        item = None
        if h.get("pick"):
            item = {"contest": cid, "kind": kind, "roles": s["roles"], "url": url, "raw_url": unwrap(url)[0],
                    "pinned_ts": h["pick"], "pivot": h["window"][0]}
        if j["list"] == "year-reused":
            start, end = h["window"]
            other_series = j.get("belongs_to") and sid_of.get(j["belongs_to"]) != sid_of[cid]
            if pending:
                out = "pending"
            elif h.get("pick"):
                out = "keep"
            elif other_series:
                out = "review"
            else:
                first = min([x for x in (h.get("first"), h.get("host_first")) if x] or ["99999999"])
                limit = (datetime.datetime.strptime(end, "%Y%m%d") + datetime.timedelta(days=365)).strftime("%Y%m%d")
                out = "remove" if first[:8] > limit else "lost"
            row.update(outcome=out, as_of=h.get("pick"), window=h["window"], host_first=h.get("host_first"))
            resolved.append(row)
            if a.write:
                if out == "keep":
                    s["as_of"] = h["pick"]
                elif out == "lost":
                    s.pop("as_of", None)
                elif out == "remove":
                    c["sources"].remove(s)
                    if not c["sources"]:
                        del c["sources"]
                if out in ("keep", "lost", "remove"):
                    touched.add(sid_of[cid])
            if out == "keep" and kind:
                queue.append(item)
        else:
            if h.get("pick"):
                out = "snapshot"
                if kind:
                    queue.append(item)
                if a.write and s.get("as_of") != h["pick"]:
                    s["as_of"] = h["pick"]
                    touched.add(sid_of[cid])
            elif pending:
                out = "pending"
            elif copy.get("via") in ("live", "page") or not h.get("captures"):
                out = "browser"
            else:
                out = "none"
            row.update(outcome=out, as_of=h.get("pick"), host=urllib.parse.urlsplit(unwrap(url)[0]).netloc)
            recapture.append(row)
    (L / "year-reused-resolved.json").write_text(json.dumps(resolved, indent=1, ensure_ascii=False) + "\n")
    (L / "recapture.json").write_text(json.dumps(recapture, indent=1, ensure_ascii=False) + "\n")
    print("year-reused:", dict(Counter(r["outcome"] for r in resolved)))
    print("not-document:", dict(Counter(r["outcome"] for r in recapture)))
    print("browser hosts:", Counter(r["host"] for r in recapture if r["outcome"] == "browser").most_common(12))
    print("capture queue:", len(queue), "copies to mark:", len(marks))
    if a.write:
        for sid in sorted(touched):
            for c in series[sid]["contests"]:
                cat.sort_sources(c)
            cat.dump_series(sid, series[sid], "wayback_history.py")
        arch = ROOT.parent / "archive"
        (arch / f"capture-queue-{day_tag}.json").write_text(json.dumps({"generated": day_tag, "queue": queue}, indent=1) + "\n")
        (arch / "reports" / f"content-check-{day_tag}.json").write_text(json.dumps({"generated": day_tag, "marks": marks}, indent=1, ensure_ascii=False) + "\n")
        print("written:", len(touched), "series files, the capture queue and the marks")


if __name__ == "__main__":
    sys.exit(main())
