#!/usr/bin/env python3
"""Resources: the shared notion of "a URL at a time" (DEFINITIONS.md, "Resources").

- A *locator* is a bare URL — an address, no time.  Catalogue fields (`url`, `web`,
  `mirrors[].url`, `problemset`) hold locators only.  A locator may carry `as_of`,
  a timestamp meaning "the content we mean is what was there at this time" (the live
  address is dead or repurposed).
- A *resource* is (locator, time).  Archive captures are resources.
- An archive *wrapper* URL (web.archive.org/web/<ts><flags>/<url>, and friends) is a
  resource reference, never a locator: ingest unwraps it into (url, ts).

Timestamps are Wayback-style digit strings, 4–14 digits, at whatever precision we
have: 2011, 20110102, 20110102183612.
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlsplit, urlunsplit

# Wayback Machine.  Flags: id_ (identity/raw), fw_ (frame), im_ (image), if_ (iframe),
# js_, cs_, oe_ — presentation variants of the same snapshot; dropped.  A '*' in the
# timestamp position is a calendar query, not a snapshot.
_WB = re.compile(
    r"^https?://(?:web\.|wayback\.)?archive\.org/(?:web|wayback)/(\d{4,14}\*?|\*)(?:[a-z]{1,2}_?)?/+(.+)$",
    re.I)
# Other wrappers whose inner URL is recoverable: arquivo.pt, Library of Congress,
# Stanford Web Archive Portal, UK Web Archive (all Wayback-derived path layouts).
_OTHER = re.compile(
    r"^https?://(?:arquivo\.pt/wayback|webarchive\.loc\.gov/all|swap\.stanford\.edu/"
    r"|www\.webarchive\.org\.uk/wayback/archive)/(\d{4,14})(?:[a-z]{2}_)?/+(.+)$", re.I)

TS_RE = re.compile(r"^\d{4,14}$")


def canon_url(u: str) -> str:
    """Normalise a locator: scheme/host lowercase, drop default ports and fragments.
    Trailing slashes are kept (they can matter); use `norm_key` for matching."""
    u = (u or "").strip()
    if not u:
        return u
    try:
        s = urlsplit(u)
        port = s.port
    except ValueError:  # malformed (e.g. ':80s3') — leave the string alone
        return u
    host = (s.hostname or "").lower()
    if port and not ((s.scheme == "http" and port == 80) or (s.scheme == "https" and port == 443)):
        host += f":{port}"
    if s.username:
        host = s.username + (f":{s.password}" if s.password else "") + "@" + host
    return urlunsplit((s.scheme.lower(), host, s.path or "/", s.query, ""))


def norm_key(u: str) -> str:
    """Loose match key for a locator: scheme-, www-, case-, default-port- and
    trailing-slash-insensitive, HTML entities unescaped, runs of slashes collapsed."""
    u = html.unescape(u or "")
    u = re.sub(r"^(https?:)/{2,}", r"\1//", u.strip(), flags=re.I)
    u = canon_url(unwrap(u)[0])
    u = re.sub(r"^https?://(www\.)?", "", u, flags=re.I)
    return u.rstrip("/").lower()


def unwrap(u: str):
    """(locator, ts|None, via): parse archive wrapper URLs, repeatedly (a wayback
    of a wayback unwraps to the innermost URL and the *innermost* timestamp, which
    is the one that names the snapshot).  `via` is 'wayback', 'archive', or None.
    A calendar query ('*') unwraps with ts=None."""
    u = (u or "").strip()
    ts, via = None, None
    for _ in range(4):
        m = _WB.match(u)
        if m:
            u, ts, via = m.group(2), (None if "*" in m.group(1) else m.group(1)), "wayback"
            continue
        m = _OTHER.match(u)
        if m:
            u, ts, via = m.group(2), m.group(1), "archive"
            continue
        break
    if via and not re.match(r"^[a-z][a-z0-9+.-]*:", u, re.I):
        u = "http://" + u  # wayback accepts scheme-less inner URLs
    return canon_url(u), ts, via


def is_wrapper(u: str) -> bool:
    return bool(u) and (_WB.match(u.strip()) is not None or _OTHER.match(u.strip()) is not None)


def wayback_link(url: str, as_of: str | None = None, flag: str = "") -> str:
    """Wayback link for a locator: pinned to `as_of` when known (Wayback resolves a
    partial timestamp to the nearest snapshot), else the calendar."""
    url, inner_ts, _ = unwrap(url)
    ts = as_of or inner_ts
    return f"https://web.archive.org/web/{ts}{flag}/{url}" if ts else f"https://web.archive.org/web/*/{url}"


def ts_from(value) -> str | None:
    """Coerce a timestamp-ish value (14-digit, ISO date/datetime) to digit form."""
    if value is None:
        return None
    s = str(value).strip()
    if TS_RE.match(s):
        return s
    d = re.sub(r"[^0-9]", "", s.split("+")[0].replace("Z", ""))
    return d[:14] if 4 <= len(d) else None


def fmt_time(ts: str | None) -> str:
    """Display form at the precision we have: 2011 · 2011-01 · 2011-01-02 · 2011-01-02 18:36."""
    if not ts:
        return ""
    ts = str(ts)
    out = ts[:4]
    if len(ts) >= 6:
        out += "-" + ts[4:6]
    if len(ts) >= 8:
        out += "-" + ts[6:8]
    if len(ts) >= 12:
        out += " " + ts[8:10] + ":" + ts[10:12]
    return out


def label(url: str, as_of: str | None = None, maxlen: int = 90) -> str:
    """`<url> (<time>)` — the resource presentation; plain URL for a bare locator."""
    url = url if len(url) <= maxlen else url[: maxlen - 1] + "…"
    return f"{url} ({fmt_time(as_of)})" if as_of else url
