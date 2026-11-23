#!/usr/bin/env python3
"""Fetch candidate logos for the online judges that have none (tools/site_assets/judges/<id>.png).

For every judge without a logo: the icons its front page names (<link rel="icon">, apple-touch-icon,
og:image) and /favicon.ico, saved as they come into ../_hunt/logos/<judge>/. For a closed judge the
front page is asked of the Wayback Machine, and for the Live Archive every image the Wayback Machine
holds under a few folders of the site is taken too (EXTRA). Nothing is put on the site: the files are
candidates to look at; the one chosen is made into tools/site_assets/judges/<id>.png by hand.

Needs the network: run on the Mac.
  cd ~/Claude/icpc-contests/contests && env no_proxy='*' NO_PROXY='*' python3 tools/fetch_judge_logos.py
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "_hunt" / "logos"
UA = "icpc-contest-archive-logos/1.0 (github.com/icpc-contest-archive)"
# addresses to take as they are: (address, Wayback timestamp or None)
EXTRA = {"livearchive": [("https://icpcarchive.ecs.baylor.edu/uhunt/images/uhunt_la.png", "20220126233940"),
                         ("https://icpcarchive.ecs.baylor.edu/favicon.ico", "2015"),
                         ("https://icpcarchive.ecs.baylor.edu/templates/xp.winupdate.like/favicon.ico", "2015")],
         "sgu": [("https://acm.sgu.ru/favicon.ico", "2015"), ("https://codeforces.com/favicon.ico", None)]}
# folders of a closed site whose images the Wayback Machine may hold
FOLDERS = {"livearchive": ["icpcarchive.ecs.baylor.edu/uhunt/images", "icpcarchive.ecs.baylor.edu/templates",
                           "icpcarchive.ecs.baylor.edu/images", "icpcarchive.ecs.baylor.edu/uhunt/img"]}
HOME = {"sgu": "https://codeforces.com/problemsets/acmsguru", "bailian": "http://bailian.openjudge.cn/"}


def get(url: str, timeout: int = 60) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("content-type", "")


def wb(url: str, ts: str) -> str:
    return f"https://web.archive.org/web/{ts}id_/{url}"


def save(d: Path, n: int, url: str, body: bytes, ctype: str) -> None:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1] or "icon")[:60]
    if "." not in name:
        name += {"image/png": ".png", "image/x-icon": ".ico", "image/vnd.microsoft.icon": ".ico", "image/svg+xml": ".svg",
                 "image/jpeg": ".jpg", "image/gif": ".gif"}.get(ctype.split(";")[0].strip(), ".bin")
    (d / f"{n:02d}-{name}").write_bytes(body)
    print(f"    {n:02d}-{name}  {len(body)} bytes  {url}")


def icons_of(page_url: str, body: bytes) -> list[str]:
    html = body.decode("utf-8", "replace")
    found = re.findall(r'<link[^>]+rel=["\'][^"\']*icon[^"\']*["\'][^>]*>', html, re.I) + re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]*>', html, re.I)
    out = []
    for tag in found:
        m = re.search(r'(?:href|content)=["\']([^"\']+)["\']', tag)
        if m:
            out.append(urllib.parse.urljoin(page_url, m.group(1)))
    return out + [urllib.parse.urljoin(page_url, "/favicon.ico")]


def main() -> int:
    judges = yaml.safe_load((ROOT / "judges.yaml").read_text())["judges"]
    only = set(sys.argv[1:])
    for j in judges:
        jid = j["id"]
        if (ROOT / "tools" / "site_assets" / "judges" / f"{jid}.png").exists() or (only and jid not in only):
            continue
        d = OUT / jid
        d.mkdir(parents=True, exist_ok=True)
        closed = j.get("status") == "closed"
        home = HOME.get(jid, j["url"])
        print(f"{jid}: {j['name']} ({home}{', closed: from the Wayback Machine' if closed else ''})")
        cands: list[tuple[str, str | None]] = list(EXTRA.get(jid, []))
        try:
            body, _ct = get(wb(home, "2019") if closed else home)
            cands += [(u, "2019" if closed else None) for u in icons_of(home, body)]
        except Exception as e:
            print(f"    front page: {type(e).__name__}: {e}")
            cands.append((urllib.parse.urljoin(home, "/favicon.ico"), "2019" if closed else None))
        for folder in FOLDERS.get(jid, []):
            q = ("https://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(folder, safe="") + "&matchType=prefix&collapse=urlkey"
                 "&fl=original,timestamp&filter=statuscode:200&filter=mimetype:image.*&limit=80&output=json")
            try:
                body, _ct = get(q, 120)
                cands += [(u, ts) for u, ts in json.loads(body.decode() or "[]")[1:]]
            except Exception as e:
                print(f"    listing {folder}: {type(e).__name__}: {e}")
            time.sleep(3)
        seen, n = set(), 0
        for url, ts in cands:
            if url in seen:
                continue
            seen.add(url)
            try:
                body, ct = get(wb(url, ts) if ts else url)
            except Exception as e:
                print(f"    -- {url}: {type(e).__name__}: {str(e)[:80]}")
                continue
            if not body or "html" in ct:
                continue
            n += 1
            save(d, n, url, body, ct)
            time.sleep(3 if ts else 0.5)
    print(f"candidates are in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
