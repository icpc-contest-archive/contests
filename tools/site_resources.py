#!/usr/bin/env python3
"""Locator and resource pages for the catalogue site (used by build_site.py).

  locator/<id>/index.html   one locator: url, health, references, its resources
  locator/<id>/<ts>.html    one resource (url, time): captures, website crawl, status

Data: data/resources.json from tools/build_resources.py.  Identifiers: see that tool.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from collections import defaultdict
from pathlib import Path

from resources import fmt_time, norm_key, wayback_link


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def lid(url: str) -> str:
    return hashlib.sha256(norm_key(url).encode()).hexdigest()[:12]


class Resources:
    """Lookup side: lets the other page builders link a `url (time)` to its page."""

    def __init__(self, root: Path):
        p = root / "data" / "resources.json"
        self.locs = json.loads(p.read_text())["locators"] if p.exists() else {}

    def health(self, url: str) -> dict | None:
        L = self.locs.get(lid(url))
        return (L or {}).get("health")

    def locator_href(self, url: str, rel: str) -> str | None:
        k = lid(url)
        return f"{rel}locator/{k}/index.html" if k in self.locs else None

    def resource_href(self, url: str, ts: str | None, rel: str) -> str | None:
        k = lid(url)
        L = self.locs.get(k)
        if not L:
            return None
        if ts and ts in L["resources"]:
            return f"{rel}locator/{k}/{ts}.html"
        # a partial as_of (e.g. 2011) matches the resource that starts with it
        if ts:
            for t in L["resources"]:
                if t.startswith(ts) or ts.startswith(t):
                    return f"{rel}locator/{k}/{t}.html"
        return f"{rel}locator/{k}/index.html"

    def label_link(self, url: str, ts: str | None, rel: str, text: str) -> str:
        """`text` wrapped in a link to the resource/locator page when one exists."""
        href = self.resource_href(url, ts, rel) if ts else self.locator_href(url, rel)
        return f'<a href="{href}" title="resource page">{text}</a>' if href else text


STATE_HELP = {
    "live": "the address still serves the contest-era content",
    "changed": "same place, drifted content",
    "replaced": "something else lives there now",
    "dead": "the live fetch failed",
    "unknown": "fetched but nothing to judge against",
}
VIA_HELP = {
    "wayback": "fetched from the Wayback Machine; time = the snapshot Wayback served",
    "live": "fetched from the origin host by this project; time = our fetch time",
    "api-dump": "rendered from the ICPC standings API dump; time = the dump time",
    "direct": "stored directly (sheet-era import); time = the import date",
}


def build(out: Path, R: Resources, page, link_contest, local_link, replay_base: str,
          contests: dict) -> int:
    rel = "../../"
    (out / "locator").mkdir(exist_ok=True)
    n = 0
    for k, L in R.locs.items():
        d = out / "locator" / k
        d.mkdir(exist_ok=True)
        url = L["url"]
        health = L.get("health") or {}
        # ---- locator page ----
        b = [f'<h1 class="wrap">{esc(url)}</h1>',
             f'<p class="muted">locator <code>{k}</code> · key <code>{esc(L["key"])}</code></p>']
        b.append('<dl class="fields">')
        b.append(f'<dt>live</dt><dd><a href="{esc(url)}">{esc(url)}</a></dd>')
        b.append(f'<dt>wayback</dt><dd><a href="{esc(wayback_link(url))}">calendar of snapshots</a></dd>')
        if health:
            st = health.get("state", "")
            b.append(f'<dt>health</dt><dd><span class="chip" title="{esc(STATE_HELP.get(st, ""))}">{esc(st)}</span>'
                     + (f' checked {esc(health["checked"])}' if health.get("checked") else "")
                     + (f' <span class="muted small">— {esc(health["evidence"])}</span>' if health.get("evidence") else "")
                     + (f' <span class="muted small">({esc(health["note"])})</span>' if health.get("note") else "")
                     + "</dd>")
        else:
            b.append('<dt>health</dt><dd class="muted">never live-checked</dd>')
        wb = L.get("wayback")
        if wb:
            WB_HELP = {"ok": "a snapshot is served", "none": "no snapshot exists",
                       "excluded": "the Wayback Machine refuses to serve this URL (domain excluded by policy) — snapshots may exist but are blocked"}
            b.append(f'<dt>wayback status</dt><dd><span class="chip" title="{esc(WB_HELP.get(wb["state"], ""))}">{esc(wb["state"])}</span>'
                     + (f' checked {esc(wb["checked"])}' if wb.get("checked") else "")
                     + (f' <span class="muted small">— {esc(wb["evidence"])}</span>' if wb.get("evidence") else "") + "</dd>")
        refs = L.get("refs") or []
        if refs:
            seen = set()
            items = []
            for r in refs:
                key = (r["contest"], r["field"])
                if key in seen:
                    continue
                seen.add(key)
                extra = f' <span class="muted small">as of {fmt_time(r["as_of"])}</span>' if r.get("as_of") else ""
                items.append(f'{link_contest(r["contest"], rel)} <span class="chip">{esc(r["field"].replace("_", " ").replace("icpc standings", "ICPC standings"))}</span>{extra}')
            b.append(f'<dt>referenced by</dt><dd class="wrap">{" · ".join(items)}</dd>')
        b.append("</dl>")
        held_res = {t: Rr for t, Rr in L["resources"].items() if Rr.get("held")}
        decl_res = {t: Rr for t, Rr in L["resources"].items() if not Rr.get("held")}
        b.append("<h2>Resources</h2>")
        if not held_res and not decl_res:
            b.append('<p class="muted">No resource: nothing has ever been observed at this address by this project. '
                     'See the checks below for what was tried.</p>')
        else:
            b.append('<p class="small muted">A resource is this locator at a point in time with content observed; one row per time.</p>')
        b.append('<div class="tablewrap"><table><tr><th>time</th><th>via</th><th>held</th>'
                 '<th>captures</th><th>website crawl</th><th>referenced by</th></tr>')
        for ts, Rr in list(held_res.items()) + list(decl_res.items()):
            caps = Rr.get("captures") or []
            site = Rr.get("website")
            shas = {c.get("sha256") for c in caps if c.get("sha256")}
            capcell = (f'{len(caps)} capture{"s" if len(caps) != 1 else ""}'
                       + (f', {len(shas)} distinct content hash{"es" if len(shas) != 1 else ""}' if len(caps) > 1 else ""))
            sitecell = (f'{site.get("html_pages") or site.get("pages") or 0} pages' if site else "")
            refc = ", ".join(sorted({link_contest(r["contest"], rel) for r in (Rr.get("refs") or [])}
                                    | {link_contest(c["contest"], rel) for c in caps}))
            b.append(f'<tr><td><a href="{esc(ts)}.html">{esc(fmt_time(ts) if ts != "unknown" else "unknown")}</a></td>'
                     f'<td>{esc(Rr.get("via") or "")}</td><td>{"yes" if Rr.get("held") else "no — declared in the catalogue (as_of), not held"}</td>'
                     f'<td>{capcell}</td><td>{sitecell}</td><td class="wrap">{refc}</td></tr>')
        b.append("</table></div>")
        probes = L.get("probes") or []
        if probes:
            b.append(f"<h2>Checks ({len(probes)})</h2>")
            b.append('<p class="small muted">Every time this address was looked at and what came back. '
                     'A check that found no content is a record of the attempt, not a resource.</p>')
            b.append('<div class="tablewrap"><table><tr><th>when</th><th>via</th><th>outcome</th><th>evidence</th></tr>')
            OUT_HELP = {"content": "something was served", "absent": "nothing there",
                        "junk": "something was served, but it is not this resource (error page, app shell, hub page, login wall…)",
                        "blocked": "could not look (access refused)", "undetermined": "answered, but nothing to judge by"}
            for pr in probes:
                extra = ""
                if pr.get("dir"):
                    extra = f' <span class="muted small">({link_contest(pr["contest"], rel)} crawl {esc(pr["dir"].rsplit("/", 1)[-1])})</span>'
                elif pr.get("path"):
                    extra = (f' <span class="muted small">({link_contest(pr["contest"], rel)} {esc(pr.get("artifact") or "")} · '
                             f'{local_link("archive/" + pr["path"], "raw")})</span>')
                b.append(f'<tr><td>{esc(fmt_time(pr.get("ts")) if pr.get("ts") else "")}</td><td>{esc(pr.get("via") or "")}</td>'
                         f'<td><span class="chip" title="{esc(OUT_HELP.get(pr.get("outcome"), ""))}">{esc(pr.get("outcome") or "")}</span></td>'
                         f'<td class="wrap">{esc(pr.get("evidence") or "")}{extra}</td></tr>')
            b.append("</table></div>")
        (d / "index.html").write_text(page(url[:80], "\n".join(b), rel))
        n += 1
        # ---- resource pages ----
        for ts, Rr in L["resources"].items():
            b = [f'<h1 class="wrap">{esc(url)} <span class="muted">({esc(fmt_time(ts) if ts != "unknown" else "time unknown")})</span></h1>',
                 f'<p class="muted">resource <code>{k}@{esc(ts)}</code> · <a href="index.html">locator page</a></p>']
            b.append('<dl class="fields">')
            b.append(f'<dt>url</dt><dd><a href="{esc(url)}">{esc(url)}</a> <span class="muted small">(live link — may no longer serve this content)</span></dd>')
            b.append(f'<dt>time</dt><dd>{esc(fmt_time(ts))} <span class="muted small">({esc(ts)})</span></dd>')
            via = Rr.get("via") or ""
            b.append(f'<dt>via</dt><dd>{esc(via)} <span class="muted small">— {esc(VIA_HELP.get(via, ""))}</span></dd>')
            if ts != "unknown":
                b.append(f'<dt>wayback</dt><dd><a href="{esc(wayback_link(url, ts))}">snapshot nearest {esc(fmt_time(ts))}</a></dd>')
            if health:
                b.append(f'<dt>locator health</dt><dd><span class="chip">{esc(health.get("state", ""))}</span>'
                         + (f' checked {esc(health["checked"])}' if health.get("checked") else "") + "</dd>")
            b.append(f'<dt>held locally</dt><dd>{"yes" if Rr.get("held") else "no — known from the catalogue only"}</dd>')
            caps = Rr.get("captures") or []
            arts = sorted({c["artifact"] for c in caps} | ({"website"} if Rr.get("website") else set()))
            if arts:
                b.append(f'<dt>type</dt><dd>{" · ".join(esc(a.replace("_", " ")) for a in arts)}</dd>')
            refs = Rr.get("refs") or []
            if refs:
                b.append('<dt>referenced by</dt><dd class="wrap">' + " · ".join(
                    f'{link_contest(r["contest"], rel)} <span class="chip">{esc(r["field"].replace("_", " "))}</span>'
                    for r in refs) + "</dd>")
            b.append("</dl>")
            if caps:
                b.append(f"<h2>Captures ({len(caps)})</h2>")
                shas = {c.get("sha256") for c in caps if c.get("sha256")}
                if len(caps) > 1:
                    b.append('<p class="small muted">'
                             + ("All captures hash identically — the same content was fetched each time."
                                if len(shas) == 1 else
                                f"{len(shas)} distinct content hashes among {len(caps)} captures — the content differed between fetches (see each row's provenance).")
                             + "</p>")
                b.append('<div class="tablewrap"><table><tr><th>contest</th><th>artifact</th><th>fetched</th>'
                         '<th>source</th><th>type</th><th class="num">size</th><th>sha256</th><th>links</th></tr>')
                for c in caps:
                    links = []
                    if c.get("replay"):
                        links.append(f'<a href="{replay_base}/{esc(c["replay"])}">replay</a>')
                    links.append(local_link("archive/" + c["path"], "raw"))
                    links.append(f'<a class="small" href="{esc(c.get("fetch_url") or url)}">fetch url</a>')
                    flags = []
                    if c.get("wrapper_fetched"):
                        flags.append('<span class="chip" title="fetched through the Wayback wrapper rather than the raw id_ endpoint; Wayback chrome is stripped at bake/playback">wrapper</span>')
                    if c.get("caveat"):
                        flags.append(f'<span class="chip" title="{esc(c["caveat"])}">caveat</span>')
                    b.append(f'<tr><td>{link_contest(c["contest"], rel)}</td><td>{esc(c["artifact"].replace("_", " "))} {" ".join(flags)}</td>'
                             f'<td>{esc(str(c.get("fetched") or "")[:16].replace("T", " "))}</td><td>{esc(c.get("source") or "")}</td>'
                             f'<td>{esc((c.get("content_type") or "").split(";")[0])}</td><td class="num">{c.get("size") or ""}</td>'
                             f'<td><code class="small">{esc((c.get("sha256") or "")[:16])}</code></td>'
                             f'<td>{" · ".join(links)}</td></tr>')
                b.append("</table></div>")
            site = Rr.get("website")
            if site:
                b.append("<h2>Website crawl</h2>")
                b.append('<dl class="fields">')
                b.append(f'<dt>contest</dt><dd>{link_contest(site["contest"], rel)}</dd>')
                b.append(f'<dt>mode</dt><dd>{esc(site.get("mode") or "")}'
                         + (' <span class="chip" title="crawl seeded with a Wayback wrapper URL before the resource model; Wayback chrome stripped at playback">legacy wrapper</span>' if site.get("legacy_wrapper") else "")
                         + "</dd>")
                b.append(f'<dt>fetched</dt><dd>{esc(str(site.get("fetched") or "")[:16].replace("T", " "))}'
                         + (f' <span class="muted small">({esc(site.get("tool"))})</span>' if site.get("tool") else "") + "</dd>")
                if site.get("scopes"):
                    b.append('<dt>scope</dt><dd class="wrap">' + "; ".join(
                        f'{esc(s.get("host", ""))}{esc(s.get("path", ""))} <span class="muted small">({esc(s.get("rule", ""))})</span>'
                        for s in site["scopes"]) + "</dd>")
                b.append(f'<dt>size</dt><dd>{site.get("pages") or 0} pages ({site.get("html_pages") or 0} html), '
                         f'{round((site.get("bytes") or 0) / 1e6, 1)} MB'
                         + (f'; {site["unfetched"]} in scope not fetched, {site["offsite"]} offsite links' if "unfetched" in site else "")
                         + "</dd>")
                cap_dir = site["dir"].rsplit("/", 1)[-1]
                play = local_link(f"site/{site['contest']}/{cap_dir}/", "archived site")
                rawf = local_link("archive/" + site["dir"] + "/", "raw files")
                b.append(f"<dt>play back</dt><dd>{play} · {rawf}</dd>")
                b.append("</dl>")
                pl = site.get("page_list")
                if pl:
                    b.append(f"<h3>Pages ({len(pl)})</h3>")
                    b.append('<div class="tablewrap"><table><tr><th>url</th><th>status</th><th>type</th>'
                             '<th class="num">size</th><th>snapshot</th></tr>')
                    for u, status, size, pts, ctype in sorted(pl, key=lambda x: str(x[0])):
                        pl_link = local_link(f"site/{site['contest']}/{cap_dir}/{u}", "local") if str(status) == "200" else ""
                        b.append(f'<tr><td class="wrap"><a href="{esc(u)}">{esc(u[:110])}</a> {pl_link}</td>'
                                 f'<td>{esc(status)}</td><td>{esc(ctype or "")}</td><td class="num">{size or ""}</td>'
                                 f'<td>{esc(fmt_time(pts)) if pts else ""}</td></tr>')
                    b.append("</table></div>")
                elif site.get("pages"):
                    b.append('<p class="small muted">Page list not available in this build (the crawl manifest lives in the archive checkout).</p>')
            (d / f"{ts}.html").write_text(page(f"{url[:60]} ({fmt_time(ts)})", "\n".join(b), rel))
            n += 1
    return n
