#!/usr/bin/env python3
"""Ask the Wayback Machine what a series' site showed in each edition's season (decision 26, 2026-11-25).

  python3 tools/series_site_history.py --jobs               # write the list of citations to ask about
  python3 tools/series_site_history.py                      # ask; resumable, run until it prints "done"
  python3 tools/series_site_history.py --report             # what the answers say, per citation

A job is one undated `web` citation of an address that several editions cite. The window of an
edition runs from 200 days before the contest to 60 days before the next edition (the rule of
tools/wayback_history.py). For each address the capture list is asked for once; for each edition up
to four captures in its window are fetched (after the contest first, then before it), each kept on
disk under ../_series-sites/<run>/<address hash>/ with the frames of a frameset, so that every pick
can be read before it is applied. Nothing in the catalogue is changed by this tool.
"""
import argparse, datetime, hashlib, json, re, sys, threading, time, urllib.parse, urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import catalogue as cat
from resources import unwrap, norm_key
from wayback_history import window, text_of, UA

ROOT = Path(__file__).resolve().parent.parent
RUN = "2026-11-25"
OUT = ROOT / "data" / f"series-sites-{RUN}"
BODIES = ROOT.parent / "_series-sites" / RUN
LOCK = threading.Lock()
SOCIAL = re.compile(r"facebook\.com|t\.me/|twitter\.com|//x\.com/|instagram\.com|vk\.com|youtube\.com|linkedin\.com|weibo\.|telegram")
PAUSE = [0.0]


def get(url, timeout=40):
    """(body, content type, final address) or (None, error, None). Waits and tries again when the Machine says slow down."""
    err = ""
    for attempt in range(6):
        wait = PAUSE[0] - time.time()
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(4_000_000), r.headers.get("Content-Type", ""), r.geturl()
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            if " 404" in err:
                return None, err, None
            if " 429" in err or " 503" in err or "refused" in err.lower():
                with LOCK:
                    PAUSE[0] = max(PAUSE[0], time.time() + 45 * (attempt + 1))
            else:
                time.sleep(3 * (attempt + 1))
    return None, err, None


def cdx(raw):
    q = {"url": raw, "output": "json", "fl": "timestamp,statuscode,digest,length", "limit": "20000",
         "filter": "statuscode:[23]..", "collapse": "digest"}
    body, info, _ = get("https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(q), timeout=90)
    if body is None:
        return None
    try:
        rows = json.loads(body or b"[]")
    except ValueError:
        return None
    return rows[1:] if rows else []


def host_first(raw):
    host = urllib.parse.urlsplit(raw if "//" in raw else "http://" + raw).netloc
    q = {"url": host + "/", "output": "json", "fl": "timestamp", "limit": "1", "matchType": "host"}
    body, _, _ = get("https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(q), timeout=90)
    try:
        rows = json.loads(body or b"[]")
        return rows[1][0] if len(rows) > 1 else None
    except Exception:
        return None


def frames_of(html, base):
    out = []
    for m in re.finditer(r"(?is)<i?frame\b[^>]*?\bsrc\s*=\s*[\"']?([^\"'\s>]+)", html):
        out.append(urllib.parse.urljoin(base, m.group(1)))
    m = re.search(r"(?is)<meta[^>]+http-equiv\s*=\s*[\"']?refresh[^>]*?url\s*=\s*([^\"'\s>]+)", html)
    if m:
        out.append(urllib.parse.urljoin(base, m.group(1).strip("'\"")))
    seen, uniq = set(), []
    for u in out:
        if u.startswith("http") and u not in seen and "web.archive.org" not in u:
            seen.add(u)
            uniq.append(u)
    return uniq[:5]


def read_capture(raw, ts, year, folder):
    """Fetch one capture (and the frames it is made of), keep the files, say what they show."""
    body, ctype, final = get(f"https://web.archive.org/web/{ts}id_/{raw}")
    if body is None:
        return {"ts": ts, "error": ctype[:100]}
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{ts}.body").write_bytes(body)
    html = body.decode("utf-8", "replace")
    txt = text_of(body, ctype)
    hit = {"ts": ts, "size": len(body), "text": len(txt), "sha": hashlib.sha256(body).hexdigest()[:16],
           "title": (re.search(r"(?is)<title[^>]*>(.*?)</title>", html) or [None, ""])[1].strip()[:120],
           "names_year": bool(re.search(rf"(?<!\d){year}(?!\d)", txt))}
    m = re.search(r"/web/(\d{14})(?:id_)?/(.*)$", final or "")
    if m and (m.group(1) != ts or norm_key(m.group(2)) != norm_key(raw)):
        hit["forwarded_to"] = {"ts": m.group(1), "url": m.group(2)}
    fr = []
    if b"%PDF" not in body[:1024]:
        for i, fu in enumerate(frames_of(html, (m.group(2) if m else None) or raw)):
            fb, fc, _ = get(f"https://web.archive.org/web/{ts}id_/{fu}")
            if fb is None:
                fr.append({"url": fu, "error": fc[:100]})
                continue
            (folder / f"{ts}.f{i}.body").write_bytes(fb)
            ft = text_of(fb, fc)
            fr.append({"url": fu, "text": len(ft), "names_year": bool(re.search(rf"(?<!\d){year}(?!\d)", ft))})
    if fr:
        hit["frames"] = fr
    hit["shows_year"] = hit["names_year"] and hit["text"] > 80 or any(f.get("names_year") and f.get("text", 0) > 80 for f in fr)
    return hit


def study(addr, jobs, contests):
    raw = unwrap(jobs[0]["url"])[0]
    rows = cdx(raw)
    if rows is None:
        return None
    folder = BODIES / hashlib.sha256(addr.encode()).hexdigest()[:12]
    out = {"address": addr, "raw": raw, "captures": len(rows), "first": rows[0][0] if rows else None,
           "last": rows[-1][0] if rows else None, "editions": {}}
    if not rows or min(j["window"][1] for j in jobs) < rows[0][0][:8]:
        out["host_first"] = host_first(raw)
    done = {}
    for j in jobs:
        start, day, end = j["window"]
        year = j["year"]
        inw = [r for r in rows if start <= r[0][:8] <= end]
        after = sorted([r for r in inw if r[0][:8] >= day], key=lambda r: r[0])
        before = sorted([r for r in inw if r[0][:8] < day], key=lambda r: r[0], reverse=True)
        # the first three after the contest, the last before it, then the middle and the end of the window
        order = after[:3] + before[:1] + ([after[len(after) // 2], after[-1]] if len(after) > 3 else []) + before[1:2]
        cands = [r for i, r in enumerate(order) if r not in order[:i]]
        ed = {"window": [start, end], "day": day, "in_window": len(inw), "tried": []}
        for ts, _st, _dig, _ln in cands[:6]:
            k = (ts, year)
            if k not in done:
                done[k] = read_capture(raw, ts, year, folder)
            ed["tried"].append(done[k])
            if done[k].get("shows_year"):
                ed["pick"] = ts
                break
        if any(t.get("error") for t in ed["tried"]) and "pick" not in ed:
            ed["retry"] = True
        out["editions"][j["contest"]] = ed
    return out


def make_jobs(contests):
    by = defaultdict(list)
    for cid, c in contests.items():
        for s in c.get("sources") or []:
            if "web" in s["roles"] and not s.get("as_of") and not SOCIAL.search(s["url"]):
                by[norm_key(s["url"])].append((cid, s["url"]))
    jobs, skipped = [], Counter()
    for addr, cites in sorted(by.items()):
        if len({cid for cid, _ in cites}) < 2:
            continue
        for cid, url in cites:
            c = contests[cid]
            if c.get("status") == "upcoming" or cid.endswith("-2026"):
                skipped["edition of 2026: today's page is the edition's"] += 1
                continue
            if "/subregions/" in addr:
                skipped["Northern Eurasia subregion page: asked by the data scan of 2026-11-23"] += 1
                continue
            start, day, end, year = window(c, contests)
            jobs.append({"address": addr, "contest": cid, "url": url, "window": [start, day, end], "year": year,
                         "dated": bool(c.get("date"))})
    return jobs, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="ask about this many addresses and stop")
    a = ap.parse_args()
    series = cat.load_series()
    contests = {c["id"]: c for doc in series.values() for c in doc["contests"]}
    OUT.mkdir(parents=True, exist_ok=True)
    jp, hp = OUT / "jobs.json", OUT / "history.json"
    if a.jobs:
        jobs, skipped = make_jobs(contests)
        jp.write_text(json.dumps({"generated": RUN, "skipped": dict(skipped), "jobs": jobs}, indent=1, ensure_ascii=False) + "\n")
        print(len(jobs), "citations of", len({j["address"] for j in jobs}), "addresses ->", jp.relative_to(ROOT), "| skipped:", dict(skipped))
        return 0
    jobs = json.loads(jp.read_text())["jobs"]
    groups = defaultdict(list)
    for j in jobs:
        groups[j["address"]].append(j)
    hist = json.loads(hp.read_text()) if hp.exists() else {}
    if a.report:
        c = Counter()
        for addr, js in groups.items():
            h = hist.get(addr)
            for j in js:
                e = (h or {}).get("editions", {}).get(j["contest"])
                c["not asked" if e is None else "pick" if e.get("pick") else "fetch failed" if e.get("retry") else
                  "captures in the window, none names the year" if e["in_window"] else "no capture in the window"] += 1
        print(dict(c))
        return 0
    todo = [g for g in groups if g not in hist or any(e.get("retry") for e in hist[g]["editions"].values())]
    if a.limit:
        todo = todo[:a.limit]
    print(f"{len(groups)} addresses, {len(todo)} to ask about; files -> {BODIES}", flush=True)
    n = [0]

    def work(addr):
        try:
            r = study(addr, groups[addr], contests)
        except Exception as e:
            print("error", addr, type(e).__name__, e, flush=True)
            return
        with LOCK:
            n[0] += 1
            if r is None:
                print(f"[{n[0]}/{len(todo)}] {addr}: the capture list could not be read; run again", flush=True)
                return
            hist[addr] = r
            picks = sum(1 for e in r["editions"].values() if e.get("pick"))
            print(f"[{n[0]}/{len(todo)}] {addr}: {r['captures']} captures, {picks} of {len(r['editions'])} editions have a pick", flush=True)
            hp.write_text(json.dumps(hist, indent=0, ensure_ascii=False))
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(work, todo))
    hp.write_text(json.dumps(hist, indent=0, ensure_ascii=False))
    left = [g for g in groups if g not in hist or any(e.get("retry") for e in hist[g]["editions"].values())]
    print("done" if not left else f"{len(left)} addresses left (a fetch failed); run the same command again")
    return 0


if __name__ == "__main__":
    sys.exit(main())
