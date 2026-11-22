#!/usr/bin/env python3
"""Queue what we hold no copy of, one file per way of fetching it.

Sources (an address a contest cites) that our archive has no good copy of:
  topup-pages-<day>.json      capture_urls.py: the address answers, or the Wayback Machine has a
                              snapshot (pinned when known)
  topup-sites-<day>.json      capture_site.py: a website address. A contest with no crawl gets its
                              normal item; a contest that has one gets an item for the missing address
                              alone, with a budget of 25 pages, once however many contests cite it
                              (capture_site.py never revisits a site it has crawled, so an address
                              added later is otherwise never fetched)
  topup-curl-<day>.json       capture_urls_curl.py: the host refuses our client (address "blocked");
                              curl is often served. The hosts are printed for --hosts.
  topup-browser-<day>.json    capture_browser.py: hosts a plain fetch gets nothing from (NEEDS_BROWSER),
                              and bad copies whose address answers (the same fetch gives the same)
Statements, for the problems of every set whose statements we do not all hold, one page per problem:
  topup-problems-<day>.json           capture_urls.py --no-wayback: judges a plain fetch works on
  topup-problems-wayback-<day>.json   capture_urls.py --no-live: closed judges, the snapshot the link names
  topup-problems-browser-<day>.json   capture_browser.py: judges that need a browser

Left out, each counted in the summary: contests still to come (captured once they have run); a website
address that is already a page of a crawl we hold; website addresses that need a browser (a crawl cannot
be made that way); Live Archive problem links (see LIVEARCHIVE below).

The files are named so that the default queue lookup of the capture tools never picks them.
Builds the site into a scratch folder to judge every source exactly as the site does (about a minute).
Needs pyyaml and the archive checkout.
"""
from __future__ import annotations

import contextlib
import datetime
import io
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT.parent / "archive"
OUT = Path(__import__("os").environ.get("TOPUP_OUT") or ARCHIVE)   # where the queues are written
sys.path.insert(0, str(ROOT / "tools"))
import build_site as B  # noqa: E402
from catalogue import load_contests, sources  # noqa: E402
from make_capture_queue import capture_kind  # noqa: E402
from make_site_queue import scope_for  # noqa: E402
from resources import norm_key, unwrap  # noqa: E402

# a plain fetch gets a bot wall, a login page or an empty app shell from these
NEEDS_BROWSER = {"qoj.ac", "codeforces.com", "drive.google.com", "docs.google.com", "www.facebook.com",
                 "github.com", "board.xcpcio.com", "onlinejudge.u-aizu.ac.jp", "groups.google.com", "dmoj.ca",
                 "usenetarchives.com", "www.instagram.com", "omegaup.com", "tlx.toki.id", "www.mediafire.com",
                 "ac.nowcoder.com", "pintia.cn", "www.codechef.com", "vjudge.net"}
TOPUP_PAGES = 25   # page budget of an item for one missing address (capture_site.py >= 1.17)

# judges by how a problem's page is fetched, in order of preference (one page per problem)
JUDGE_PLAIN = ("kattis", "timus", "codeforces", "hdu", "poj", "spoj", "spoj-br", "spoj-vn", "szkopul",
               "eolymp", "luogu", "bailian", "cats", "sgu", "loj")
JUDGE_BROWSER = ("qoj", "aoj", "codechef", "nowcoder", "pintia", "hackerrank", "tlx", "omegaup", "dmoj",
                 "vnoj", "beecrowd")
# LIVEARCHIVE: the recorded links put the Live Archive's problem numbers on onlinejudge.org, where the
# same numbers are other (UVa) problems (checked 2026-11-22: 3 of 3). Not queued until the links are right.
JUDGE_SKIP = ("livearchive",)


def needs_browser(url: str) -> bool:
    host = urlsplit(url).netloc.lower()
    return host in NEEDS_BROWSER or host.endswith("icpc.global")


def crawled(cid: str) -> tuple[bool, set[str]]:
    """Has the contest a website crawl, and the addresses it holds a file for."""
    held, any_crawl = set(), False
    for mf in (ARCHIVE / cid.rsplit("-", 1)[0] / cid / "website").glob("*/site-manifest.json"):
        any_crawl = True
        for u, pg in (json.loads(mf.read_text()).get("pages") or {}).items():
            if pg.get("file"):
                held.add(norm_key(unwrap(u)[0]))
    return any_crawl, held


def pivot_of(c: dict) -> str:
    year = int(c["id"].rsplit("-", 1)[1])
    return (c.get("date") or "").replace("-", "") or (f"{year}0701" if c.get("season") == year + 1 else f"{year}0101")


def source_queues(contests: dict, stats: Counter) -> dict[str, list]:
    q: dict[str, list] = {"pages": [], "sites": [], "curl": [], "browser": []}
    seen, crawls = set(), {}
    for c in contests.values():
        cid, pivot = c["id"], pivot_of(c)
        year = int(cid.rsplit("-", 1)[1])
        new_seeds = []
        for s in sources(c):
            url = s["url"]
            if not url.startswith("http"):
                continue
            a = B.avail(url, cid)
            ours, live = a["ours"]["word"], a["live"]["word"]
            if ours == "held":
                continue
            answers = live in ("live", "changed")
            snap = a["wb"].get("ts") if a["wb"]["word"] == "snapshot" else None
            there = answers or live in ("blocked", "unverified")   # not confirmed gone
            if not there and not snap:
                continue
            if c.get("status") == "upcoming":
                stats["left out: contest still to come"] += 1
                continue
            raw, ts, _via = unwrap(url)
            kind = capture_kind(s)
            if kind is not None:
                if (cid, kind, raw) in seen:
                    continue
                seen.add((cid, kind, raw))
                item = {"contest": cid, "kind": kind, "roles": list(s["roles"]), "url": url, "pivot": pivot, "raw_url": raw}
                ts = s.get("as_of") or ts or snap
                if snap and not needs_browser(url) or (snap and not there):
                    item["pinned_ts"] = ts
                    q["pages"].append(item)
                    stats["pages: snapshot"] += 1
                elif needs_browser(url) or (ours == "bad copy" and live != "blocked"):
                    q["browser"].append(item)
                    stats[f"browser: {'bad copy to replace' if ours == 'bad copy' else 'never captured'}"] += 1
                elif live == "blocked":
                    q["curl"].append(item)
                    stats["curl: host refuses our client"] += 1
                elif answers:
                    q["pages"].append(item)
                    stats["pages: address answers"] += 1
            elif "web" in s["roles"]:
                if cid not in crawls:
                    crawls[cid] = crawled(cid)
                any_crawl, held = crawls[cid]
                if norm_key(raw) in held:
                    stats["left out: website address already a page of a crawl we hold"] += 1
                    continue
                if not snap and (needs_browser(url) or not answers):
                    stats["left out: website address that needs a browser"] += 1
                    continue
                if not any_crawl:
                    new_seeds.append((url, s.get("as_of")))
                    continue
                when = None if answers else (s.get("as_of") or snap)
                if (norm_key(raw), when) in seen:   # cited by several contests: one fetch
                    stats["left out: the same address and time queued for another contest"] += 1
                    continue
                seen.add((norm_key(raw), when))
                p = urlsplit(raw)
                item = {"contest": cid, "seeds": [raw], "pivot": pivot, "max_pages": TOPUP_PAGES,
                        "scopes": [{"host": p.netloc, "path": p.path or "/", "rule": "missing address of a crawled site"}]}
                if when:
                    item["snapshot"] = when
                q["sites"].append(item)
                stats[f"sites, address missing from its crawl: {'address answers' if answers else 'snapshot'}"] += 1
        if new_seeds:   # no crawl yet: the item make_site_queue.py would write
            item = {"contest": cid, "seeds": [u for u, _ in new_seeds], "pivot": pivot,
                    "scopes": [scope_for(u, year) for u, _ in new_seeds]}
            snapshot = next((t for _, t in new_seeds if t), None)
            if snapshot:
                item["snapshot"] = snapshot
            q["sites"].append(item)
            stats["sites: never crawled"] += 1
    return q


def problem_queues(contests: dict, stats: Counter) -> dict[str, list]:
    """One page per problem of every set whose statements we do not all hold."""
    registry = yaml.safe_load((ROOT / "judges.yaml").read_text())
    registry = registry["judges"] if isinstance(registry, dict) else registry
    closed = {j["id"] for j in registry if j.get("status") == "closed"}
    rank = {j: i for i, j in enumerate(JUDGE_PLAIN + tuple(sorted(closed)) + JUDGE_BROWSER)}
    q: dict[str, list] = {"problems": [], "problems-wayback": [], "problems-browser": []}
    seen = set()
    for sid, doc in B.SETS.items():
        if B.COV.set_record(sid)["statement"] == "all":
            continue
        members = [m for m in B.set_members(doc) if m in contests]
        if not members or contests[members[0]].get("status") == "upcoming":
            continue
        c = contests[members[0]]
        for p in doc.get("problems") or []:
            links = [j for j in p.get("judges") or [] if j.get("url")]
            if not links:
                stats["problems: no link to an online judge"] += 1
                continue
            usable = [j for j in links if j["judge"] in rank and (j["judge"] not in closed or j.get("as_of"))]
            if not usable:
                only = "Live Archive only (links wrong)" if all(j["judge"] in JUDGE_SKIP for j in links) else "no usable link"
                stats[f"problems: {only}"] += 1
                continue
            j = min(usable, key=lambda j: rank[j["judge"]])
            if j["url"] in seen:
                continue
            seen.add(j["url"])
            item = {"contest": c["id"], "kind": f"judge-{j['judge']}", "roles": ["problem"], "url": j["url"],
                    "raw_url": j["url"], "pivot": pivot_of(c), "problem": p["id"], "set": sid}
            if j["judge"] in closed:
                item["pinned_ts"] = j["as_of"]
                name = "problems-wayback"
            else:
                name = "problems" if j["judge"] in JUDGE_PLAIN else "problems-browser"
            q[name].append(item)
            stats[f"{name}: {j['judge']}"] += 1
    return q


def main() -> int:
    with contextlib.redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory() as tmp:
        B.build(Path(tmp))
    today = datetime.date.today().isoformat()
    contests = load_contests()
    stats: Counter = Counter()
    queues = {**source_queues(contests, stats), **problem_queues(contests, stats)}
    for name, queue in queues.items():
        out = OUT / f"topup-{name}-{today}.json"
        out.write_text(json.dumps({"generated": today, "queue": queue}, indent=1))
        print(f"{len(queue):5d} -> {out.name}")
    for k, n in sorted(stats.items()):
        print(f"  {n:5d}  {k}")
    for name in ("curl", "browser", "problems-browser"):
        hosts = Counter(urlsplit(i["raw_url"]).netloc for i in queues[name])
        print(f"{name} hosts: " + ",".join(h for h, _ in hosts.most_common()))
        print("   " + ", ".join(f"{h} {n}" for h, n in hosts.most_common(12)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
