#!/usr/bin/env python3
"""Local archive server: rebuilds the site with local links and serves it,
together with the sibling archive and replay checkouts.

Usage: python3 tools/serve.py [--port 8123] [--no-rebuild]

Routes (all on 127.0.0.1:<port>):
  /                         the catalogue site (site/), rebuilt with local links
  /replay/...               ../replay  (baked public result pages), if checked out
  /archive/...              ../archive (raw captures: results, mirrors, …), if checked out
  /site/<contest>/          the contest's archived website, played back from
  /site/<contest>/<url>     its crawl manifest with in-site links rewritten
  /health                   200 "ok" (CORS) — "is the local server up?"

The public site links to this server at http://127.0.0.1:8123/… wherever an
archived copy exists; those links only work while this is running.
"""
from __future__ import annotations

import argparse
import functools
import html
import json
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from resources import fmt_time, unwrap, wayback_link  # noqa: E402

ARCHIVE = ROOT.parent / "archive"
REPLAY = ROOT.parent / "replay"

BANNER_CSS = ("position:sticky;top:0;z-index:2147483647;font:13px/1.4 system-ui,sans-serif;"
              "background:#fff7d6;color:#222;border-bottom:1px solid #d9c66a;padding:.4em .8em;"
              "text-align:left")


# ---------------------------------------------------------------- site playback
def _norm(url: str) -> str:
    """Scheme-insensitive, trailing-slash-insensitive key for manifest lookup.
    Archive wrappers unwrap first: a crawl seeded with a Wayback URL keys its pages
    by the wrapper, and links inside those pages resolve to wrappers too."""
    url = unwrap(url)[0]
    s = urlsplit(url)
    host = (s.hostname or "").lower()
    if s.port and s.port not in (80, 443):
        host += f":{s.port}"
    path = s.path or "/"
    if path != "/":
        path = path.rstrip("/")
    q = f"?{s.query}" if s.query else ""
    return f"{host}{path}{q}"


@functools.lru_cache(maxsize=256)
def load_site(contest: str, capture: str | None = None):
    """Return (capture_dir, manifest, lookup) for a contest's website capture,
    or None. `lookup` maps normalised url -> original manifest key."""
    idx = website_index().get(contest)
    if not idx:
        return None
    entry = None
    if capture:
        entry = next((e for e in idx if e["dir"].rsplit("/", 1)[-1] == capture), None)
    entry = entry or next((e for e in idx if e.get("primary")), idx[0])
    cdir = ARCHIVE / entry["dir"]
    mf = cdir / "site-manifest.json"
    if not mf.exists():
        return None
    m = json.loads(mf.read_text())
    lookup = {}
    for u in m.get("pages", {}):
        lookup.setdefault(_norm(u), u)
    return cdir, m, lookup


_index_cache: dict = {"mtime": None, "data": {}}


def website_index() -> dict:
    """data/website-index.json, reloaded whenever the file changes on disk (a long-
    running server must not keep serving an index from before a re-crawl)."""
    p = ROOT / "data" / "website-index.json"
    mtime = p.stat().st_mtime if p.exists() else None
    if mtime != _index_cache["mtime"]:
        out: dict[str, list] = {}
        if p.exists():
            for e in json.loads(p.read_text())["sites"]:
                out.setdefault(e["contest"], []).append(e)
        _index_cache.update(mtime=mtime, data=out)
        load_site.cache_clear()
    return _index_cache["data"]


_ATTR_RE = re.compile(
    r"""(?i)(\b(?:href|src|action|poster|data)\s*=\s*)(["']?)([^"'\s>]+)(\2)""")
_SRCSET_RE = re.compile(r"""(?i)(\bsrcset\s*=\s*)(["'])(.*?)(\2)""", re.S)
_CSS_URL_RE = re.compile(r"""(?i)url\(\s*(["']?)([^"')]+)(\1)\s*\)""")
_META_REFRESH_RE = re.compile(r"""(?i)(content\s*=\s*["']\s*\d+\s*;\s*url=)([^"']+)""")
_BASE_RE = re.compile(r"(?is)<base\b[^>]*>")
# Wayback's own additions to a page served through its wrapper (not id_): the
# toolbar block, its scripts/stylesheets, the wombat init and the trailing
# "FILE ARCHIVED ON ..." comment.  Legacy captures (seeded with a wrapper URL
# before the resource model) stored pages like that; strip at playback.
_WB_JUNK = [
    re.compile(r"(?is)<!--\s*BEGIN WAYBACK TOOLBAR INSERT\s*-->.*?<!--\s*END WAYBACK TOOLBAR INSERT\s*-->"),
    re.compile(r"(?is)<script[^>]*(?:web-static\.archive\.org|archive\.org/_static/|/_static/js/)[^>]*>\s*</script>"),
    re.compile(r"(?is)<link[^>]*(?:web-static\.archive\.org|archive\.org/_static/|/_static/css/)[^>]*>"),
    re.compile(r"(?is)<script[^>]*>(?:(?!</script>).)*?(?:__wm\.(?:init|wombat|bt|rw)|wombat\.js|wbinfo\s*=)(?:(?!</script>).)*?</script>"),
    re.compile(r"(?is)<!--\s*playback timings.*?-->"),
    re.compile(r"(?is)<!--\s*FILE ARCHIVED ON .*?-->"),
    re.compile(r"(?is)<!--\s*End Wayback Rewrite JS Include\s*-->|<!--\s*Wayback Rewrite JS Include\s*-->"),
]


def strip_wayback_wrapper(text: str) -> tuple[str, bool]:
    before = text
    for rx in _WB_JUNK:
        text = rx.sub("", text)
    return text, text != before


def _local_site_url(contest: str, capture: str, url: str) -> str:
    return f"/site/{contest}/{capture}/{quote(url, safe=':/?&=#%+~@!$,;*()[]')}"


def rewrite_html(body: bytes, contest: str, capture: str, page_url: str, m: dict,
                 lookup: dict) -> bytes:
    """Rewrite links so in-capture targets stay local; others go live (live
    crawl) or to the Wayback Machine at the crawl's pivot (wayback crawl)."""
    try:
        text = body.decode("utf-8")
        enc = "utf-8"
    except UnicodeDecodeError:
        text = body.decode("latin-1")
        enc = "latin-1"
    mode = m.get("mode")
    pivot = m.get("pivot") or ""
    page = m.get("pages", {}).get(page_url, {})
    raw_url, page_ts, page_via = unwrap(page_url)
    page_ts = page.get("wayback_timestamp") or page_ts  # the served snapshot wins

    def target(raw: str) -> str | None:
        raw = raw.strip()
        if not raw or raw.startswith(("#", "javascript:", "mailto:", "data:", "tel:")):
            return None
        absu = urljoin(page_url, html.unescape(raw))
        frag = ""
        if "#" in absu:
            absu, frag = absu.split("#", 1)
            frag = "#" + frag
        key = lookup.get(_norm(absu))
        if key:
            return _local_site_url(contest, capture, key) + frag
        raw_u, ts, via = unwrap(absu)
        if via:  # a wrapper link not in the capture: keep it pinned, never re-wrap
            if not raw_u.startswith(("http://", "https://")):
                return raw_u + frag  # mailto: etc. that Wayback had wrapped
            return (wayback_link(raw_u, ts) if ts else absu) + frag
        if (mode == "wayback" or page_ts) and absu.startswith(("http://", "https://")):
            return f"https://web.archive.org/web/{page_ts or pivot}/{absu}{frag}"
        return absu + frag  # live: leave absolute

    def attr(mo):
        t = target(mo.group(3))
        return mo.group(0) if t is None else f"{mo.group(1)}{mo.group(2)}{html.escape(t, quote=True)}{mo.group(4)}"

    def srcset(mo):
        parts = []
        for cand in mo.group(3).split(","):
            cand = cand.strip()
            if not cand:
                continue
            bits = cand.split(None, 1)
            t = target(bits[0])
            bits[0] = html.escape(t, quote=True) if t else bits[0]
            parts.append(" ".join(bits))
        return f"{mo.group(1)}{mo.group(2)}{', '.join(parts)}{mo.group(4)}"

    def cssurl(mo):
        t = target(mo.group(2))
        return mo.group(0) if t is None else f"url({mo.group(1)}{t}{mo.group(3)})"

    def refresh(mo):
        t = target(mo.group(2))
        return mo.group(0) if t is None else f"{mo.group(1)}{html.escape(t, quote=True)}"

    text = _BASE_RE.sub("", text)
    text, legacy = strip_wayback_wrapper(text) if page_via else (text, False)
    text = _ATTR_RE.sub(attr, text)
    text = _SRCSET_RE.sub(srcset, text)
    text = _CSS_URL_RE.sub(cssurl, text)
    text = _META_REFRESH_RE.sub(refresh, text)

    wb = wayback_link(raw_url, page_ts or (pivot if mode == "wayback" else None))
    if page_ts:
        src = f"Wayback snapshot {fmt_time(page_ts)}"
        if page_via:
            src += (" — legacy capture fetched through the Wayback wrapper; its toolbar and "
                    "scripts are stripped at playback, a clean re-crawl replaces it")
    else:
        src = f"live crawl {str(m.get('fetched', ''))[:10]}"
    shown = f"{raw_url} ({fmt_time(page_ts)})" if page_ts else raw_url
    # Same shape as the replay bake's banner (replay/tools/bake.py):
    #   ICPC contest archive — archived copy of <url (time)> (<provenance>) · catalogue: <contest> · wayback · live
    banner = (
        f'<div id="icpc-archive-banner" style="{BANNER_CSS}">'
        f'<b><a href="/">ICPC contest archive</a></b> — archived copy of '
        f'<a href="{html.escape(raw_url, quote=True)}">{html.escape(shown[:120])}</a> '
        f'({html.escape(src)}; site crawl, {len(m.get("pages", {}))} pages; local playback) · '
        f'catalogue: <a href="/contest/{html.escape(contest)}.html">{html.escape(contest)}</a> · '
        f'<a href="{html.escape(wb, quote=True)}">wayback</a> · '
        f'<a href="{html.escape(raw_url, quote=True)}">live</a>'
        f'</div>')
    mo = re.search(r"(?i)<body\b[^>]*>", text)
    text = text[:mo.end()] + banner + text[mo.end():] if mo else banner + text
    text = re.sub(r"(?i)<head\b[^>]*>", lambda h: h.group(0) + '<meta name="robots" content="noindex">',
                  text, count=1)
    return text.encode(enc, errors="replace"), enc


def rewrite_css(body: bytes, contest: str, capture: str, page_url: str, m: dict,
                lookup: dict) -> bytes:
    text = body.decode("utf-8", errors="replace")

    def cssurl(mo):
        raw = mo.group(2).strip()
        if raw.startswith("data:"):
            return mo.group(0)
        absu = urljoin(page_url, raw)
        key = lookup.get(_norm(absu))
        if key:
            return f"url({mo.group(1)}{_local_site_url(contest, capture, key)}{mo.group(3)})"
        raw_u, ts, via = unwrap(absu)
        if via:
            return f"url({mo.group(1)}{wayback_link(raw_u, ts, 'im_') if ts else absu}{mo.group(3)})"
        if m.get("mode") == "wayback" and m.get("pivot"):
            return f"url({mo.group(1)}https://web.archive.org/web/{m['pivot']}im_/{absu}{mo.group(3)})"
        return f"url({mo.group(1)}{absu}{mo.group(3)})"

    return _CSS_URL_RE.sub(cssurl, text).encode("utf-8")


class Handler(SimpleHTTPRequestHandler):
    mounts: dict[str, Path] = {}

    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0].split("#", 1)[0]
        for prefix, base in sorted(self.mounts.items(), key=lambda kv: -len(kv[0])):
            if prefix and clean.startswith(prefix):
                rel = unquote(clean[len(prefix):]).lstrip("/")
                return str(base / rel)
        return str(self.mounts[""] / unquote(clean).lstrip("/"))

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, to: str):
        self.send_response(302)
        self.send_header("Location", to)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            self._send(200, b"ok", "text/plain", {"Access-Control-Allow-Origin": "*"})
            return
        if self.path.startswith("/site/"):
            self.serve_site()
            return
        super().do_GET()

    def serve_site(self):
        # /site/<contest>/[<capture>/]<original url>
        raw = self.path[len("/site/"):]
        parts = raw.split("/", 1)
        contest = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        idx = website_index().get(contest)
        if not idx:
            self._send(404, f"no archived website for {html.escape(contest)}".encode(),
                       "text/plain; charset=utf-8")
            return
        capture = None
        caps = {e["dir"].rsplit("/", 1)[-1] for e in idx}
        head = rest.split("/", 1)[0]
        if head in caps:
            capture = head
            rest = rest.split("/", 1)[1] if "/" in rest else ""
        loaded = load_site(contest, capture)
        if not loaded:
            self._send(404, b"archive checkout not found (expected ../archive)", "text/plain")
            return
        cdir, m, lookup = loaded
        capture = cdir.name
        url = unquote(rest)
        if not url:
            seed = next((e["seed"] for e in idx if e["dir"].endswith(capture)), None) or \
                next(iter(m.get("pages", {})), None)
            if not seed:
                self._send(404, b"empty capture", "text/plain")
                return
            self._redirect(_local_site_url(contest, capture, seed))
            return
        key = lookup.get(_norm(url))
        if key is None:
            # not captured: hand off to wayback (pinned ts / pivot) or live
            raw_u, ts, via = unwrap(url)
            if ts or (m.get("mode") == "wayback" and m.get("pivot")):
                self._redirect(wayback_link(raw_u, ts or m["pivot"]))
            else:
                self._redirect(raw_u)
            return
        page = m["pages"][key]
        if not page.get("file"):
            # the crawl recorded this page but could not fetch it (404/error at crawl time)
            raw_u, ts, _ = unwrap(key)
            ts = page.get("wayback_timestamp") or ts
            note = (f"This page is in the capture manifest but was not fetched "
                    f"(status at crawl time: {page.get('status')}).")
            body = (f'<!doctype html><meta charset="utf-8"><title>not captured</title>'
                    f'<div style="{BANNER_CSS}"><b>ICPC contest archive</b> — {html.escape(note)} '
                    f'<a href="{html.escape(wayback_link(raw_u, ts))}">try the Wayback Machine</a> · '
                    f'<a href="{html.escape(raw_u)}">live</a> · '
                    f'<a href="/contest/{html.escape(contest)}.html">catalogue: {html.escape(contest)}</a></div>')
            self._send(404, body.encode("utf-8"), "text/html; charset=utf-8")
            return
        f = cdir / "files" / page["file"]
        if not f.exists():
            self._send(404, b"captured file missing on disk", "text/plain")
            return
        body = f.read_bytes()
        ctype = page.get("ctype") or "application/octet-stream"
        base = ctype.split(";", 1)[0].strip().lower()
        if base in ("text/html", "application/xhtml+xml", "application/x-httpd-php") or \
                (base == "application/octet-stream" and page["file"].endswith((".html", ".htm"))):
            body, enc = rewrite_html(body, contest, capture, key, m, lookup)
            ctype = f"text/html; charset={enc}"
        elif base == "text/css":
            body = rewrite_css(body, contest, capture, key, m, lookup)
        self._send(200, body, ctype, {"X-Robots-Tag": "noindex"})

    def log_message(self, fmt, *args):
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--no-rebuild", action="store_true")
    args = ap.parse_args()

    if not args.no_rebuild:
        os.environ["REPLAY_BASE"] = "/replay"
        os.environ["LOCAL_ARCHIVE_BASE"] = ""
        sys.path.insert(0, str(ROOT / "tools"))
        import build_site  # noqa: E402

        build_site.build(ROOT / "site")

    Handler.mounts = {"": ROOT / "site"}
    for name, p in (("replay", REPLAY), ("archive", ARCHIVE)):
        if p.is_dir():
            Handler.mounts[f"/{name}/"] = p
            print(f"mounted ../{name} at /{name}/")
    n = len(website_index())
    print(f"archived websites: {n} contests" + ("" if n else
          " (run tools/index_websites.py with ../archive checked out)"))
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"browsing at http://127.0.0.1:{args.port}/")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
