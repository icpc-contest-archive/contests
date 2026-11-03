#!/usr/bin/env python3
"""Build the static catalogue site into site/ (relative links only, mountable anywhere).

Optional inputs, used when present:
  data/archive-index.json  — captures held by the (private) archive repo
  data/replay-index.json   — pages baked into the public replay shard(s)
  data/website-index.json  — archived contest websites (tools/index_websites.py)

"local" links point at the local archive server (tools/serve.py, 127.0.0.1:8123)
and only work while it is running; LOCAL_ARCHIVE_BASE overrides the host (serve.py
sets it to "" so the links are same-origin when browsing locally).
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from resources import fmt_time, label as res_label, norm_key, unwrap, wayback_link  # noqa: E402
from catalogue import (RESULT_ROLES, also_at, archived, best_result, by_role, has_role, load_judges,  # noqa: E402
                       load_sets, set_letters, set_of, sources)
import site_resources  # noqa: E402

# the four published result tiers (RESULT_ROLES minus the CMS's own icpc_standings)
RESULT_KINDS = tuple(r for r in RESULT_ROLES if r != "icpc_standings")

RES = site_resources.Resources(ROOT)  # locator/resource page lookups (data/resources.json)
REPLAY_BASE = os.environ.get("REPLAY_BASE", "https://icpc-contest-archive.github.io/replay")
LOCAL_BASE = os.environ.get("LOCAL_ARCHIVE_BASE", "http://127.0.0.1:8123")
STATE_TITLE = {
    "live": "live: the address still serves the contest-era content (identical or ≥75% similar to the near-contest snapshot, or mentions the contest year)",
    "changed": "changed: same place, drifted content (30–75% similar to the snapshot, never mentions the year, or a JS shell / login wall)",
    "replaced": "replaced: something else lives there now (redirects off-host, or <30% similar to the snapshot) — use wayback/archived",
    "dead": "dead: the live fetch failed (connection error, 404, over size cap) — use wayback/archived",
    "unknown": "unknown: fetched but nothing to judge against (no snapshot and no year signal) — not yet re-verified",
}
LOCAL_TITLE = "local archive server — works only while tools/serve.py is running on this machine"

CHAMPIONSHIPS: set = set()   # series with tier: championship (filled by derive_regions)
# World regions come from the series headers (`region`, tools/migrate_series_headers.py);
# finals + championships get their own bucket on the overview pages.
REGION_NAMES = ["North America", "Latin America", "Europe", "Northern Eurasia", "Africa & Arab",
                "Asia West", "Asia Pacific", "Asia East"]
REGION_GROUPS: dict = {"World Finals & championships": []} | {r: [] for r in REGION_NAMES}
SERIES_REGION: dict = {}


def derive_regions(series_docs: dict, contests: dict) -> None:
    """Fill SERIES_REGION / REGION_GROUPS / CHAMPIONSHIPS from the series headers."""
    for sid, doc in series_docs.items():
        h = doc["series"]
        if h.get("tier") == "championship":
            CHAMPIONSHIPS.add(sid)
        if sid == "wf" or h.get("tier") == "championship":
            REGION_GROUPS["World Finals & championships"].append(sid)
        if h.get("region"):
            SERIES_REGION[sid] = h["region"]
            if sid != "wf" and h.get("tier") != "championship":
                REGION_GROUPS[h["region"]].append(sid)


CSS = """
:root { --fg:#1a1a1a; --muted:#666; --line:#ddd; --accent:#0b5cad; --bg:#fff; --chip:#f0f4f8; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e8e8e8; --muted:#9a9a9a; --line:#333; --accent:#6fb1e8; --bg:#111; --chip:#1d2733; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { margin:0; padding:1.2rem 1.6rem; }  /* full width: the links are the content */
a { color:var(--accent); text-decoration:none; } a:hover { text-decoration:underline; }
h1 { font-size:1.5rem; margin:.4rem 0 .8rem; } h2 { font-size:1.15rem; margin:1.4rem 0 .5rem; }
table { border-collapse:collapse; width:100%; } .tablewrap { overflow-x:auto; }
th,td { text-align:left; padding:.28rem .55rem; border-bottom:1px solid var(--line);
  vertical-align:top; white-space:nowrap; }
td.wrap { white-space:normal; word-break:break-all; }
th.grp { text-align:center; font-weight:500; color:var(--muted); border-bottom:none; }
td:last-child { white-space:nowrap; }
dl.fields dd { word-break:break-all; }
.muted { color:var(--muted); } .small { font-size:.85em; }
th.sorted { text-decoration:underline; }
input.tfilter { width:100%; max-width:22rem; padding:.3rem .5rem; margin:.3rem 0; font-size:.9rem;
  border:1px solid var(--line); border-radius:.4rem; background:var(--bg); color:var(--fg); }
.state { margin:.2rem 0 .8rem; }
.chip { background:var(--chip); border-radius:.6em; padding:.05em .55em; font-size:.85em;
  display:inline-block; margin:0 .15em .15em 0; }
nav.top { border-bottom:1px solid var(--line); }
nav.top div { margin:0; padding:.55rem 1.6rem; }
nav.top a { margin-right:1.1rem; }
.grid td, .grid th { border:none; padding:1px; }
.grid .lbl { position:sticky; left:0; background:var(--bg); white-space:nowrap;
  padding-right:.6rem; font-size:.82em; z-index:2; }
.grid .grp td { padding-top:.9rem; font-weight:600; color:var(--muted); }
.cell { display:block; width:15px; height:15px; border-radius:3px; }
.c-sb { background:var(--accent); }
.c-res { background:color-mix(in srgb, var(--accent) 55%, var(--bg)); }
.c-ist { background:color-mix(in srgb, var(--accent) 28%, var(--bg)); }
.c-none { background:transparent; box-shadow:inset 0 0 0 1px var(--line); }
.c-up { background:transparent; box-shadow:inset 0 0 0 1px var(--accent); opacity:.6; }
.c-lin { color:var(--muted); font-size:.8em; text-align:center; display:block; width:15px; }
.grid thead th { position:sticky; top:0; background:var(--bg); font-size:.7em;
  writing-mode:vertical-rl; transform:rotate(180deg); padding:2px 1px; z-index:1; }
.tree details { margin-left:1.1rem; } .tree > details { margin-left:0; }
.tree .leaf { margin-left:2.35rem; padding:.06rem 0; }
.tree summary { cursor:pointer; padding:.06rem 0; }
.tree .meta { color:var(--muted); font-size:.85em; margin-left:.5rem; }
.mark { display:inline-block; min-width:1.2em; text-align:center; padding:0 .28em;
  margin-right:.22em; border-radius:.35em; font-size:.82em; line-height:1.45; }
.m-arch { background:var(--accent); color:var(--bg); }
.m-arch:hover { text-decoration:none; opacity:.85; }
.m-live { box-shadow:inset 0 0 0 1px var(--accent); }
.m-ist { box-shadow:inset 0 0 0 1px var(--line); color:var(--muted); }
.m-arch.m-ist { background:var(--muted); color:var(--bg); box-shadow:none; }
a.local { border-bottom:1px dashed var(--accent); }
a.local::after { content:"local"; font-size:.7em; margin-left:.25em; padding:0 .35em;
  border-radius:.5em; background:var(--chip); color:var(--muted); vertical-align:.15em; }
dl.fields dt { float:left; clear:left; width:9.5rem; color:var(--muted); }
dl.fields dd { margin:0 0 .3rem 10.5rem; }
input#q { width:100%; max-width:28rem; padding:.45rem .6rem; font-size:1rem;
  border:1px solid var(--line); border-radius:.4rem; background:var(--bg); color:var(--fg); }
td.num, th.num { text-align:right; }
.bar { display:inline-block; width:3.6rem; height:.5em; margin-left:.45em; border-radius:.25em;
  background:var(--chip); overflow:hidden; vertical-align:baseline; }
.bar i { display:block; height:100%; background:var(--accent); }
h2.rgn { margin-top:1.6rem; }
.h-full { background:var(--accent); color:var(--bg); }
.h-part { box-shadow:inset 0 0 0 1px var(--accent); color:var(--accent); }
.h-none { box-shadow:inset 0 0 0 1px var(--line); color:var(--muted); opacity:.7; }
.h-unk { color:var(--muted); opacity:.5; }
td.letter { font-weight:600; text-align:center; }
"""

TABLE_JS = r"""
(function(){
  const num = s => { const t = s.replace(/[%,\s]/g,''); return t !== '' && !isNaN(t) ? parseFloat(t) : null; };
  document.querySelectorAll('table').forEach(tbl => {
    if (tbl.classList.contains('grid') || tbl.id === 'hits') return;
    const rows = Array.from(tbl.querySelectorAll('tr')).filter(r => r.querySelector('td'));
    const heads = Array.from(tbl.querySelectorAll('tr')).filter(r => r.querySelector('th') && !r.querySelector('td'));
    if (rows.length < 2 || !heads.length) return;
    const hdr = heads[heads.length - 1];
    const ths = Array.from(hdr.children);
    ths.forEach((th, i) => {
      if (th.getAttribute('colspan')) return;
      th.style.cursor = 'pointer'; th.title = (th.title ? th.title + ' — ' : '') + 'click to sort';
      let asc = true;
      th.addEventListener('click', () => {
        const idx = Array.from(hdr.children).indexOf(th);
        const key = r => { const c = r.children[idx]; return c ? c.textContent.trim() : ''; };
        const allNum = rows.every(r => key(r) === '' || num(key(r)) !== null);
        rows.sort((a, b) => { const x = key(a), y = key(b);
          if (allNum) { const nx = num(x), ny = num(y); return (nx === null) - (ny === null) || (nx ?? 0) - (ny ?? 0); }
          return x.localeCompare(y, undefined, {numeric: true}); });
        if (!asc) rows.reverse(); asc = !asc;
        ths.forEach(t => t.classList.remove('sorted')); th.classList.add('sorted');
        rows.forEach(r => r.parentNode.appendChild(r));
      });
    });
    if (rows.length >= 30) {
      const box = document.createElement('input');
      box.placeholder = 'filter ' + rows.length + ' rows…'; box.className = 'tfilter'; box.autocomplete = 'off';
      tbl.parentNode.insertBefore(box, tbl);
      box.addEventListener('input', () => { const q = box.value.toLowerCase();
        rows.forEach(r => { r.style.display = !q || r.textContent.toLowerCase().includes(q) ? '' : 'none'; }); });
    }
  });
})();
"""

SEARCH_JS = """
const idx = fetch(REL + 'search.json').then(r => r.json());
const q = document.getElementById('q'), out = document.getElementById('hits');
q.addEventListener('input', async () => {
  const term = q.value.trim().toLowerCase();
  if (term.length < 2) { out.innerHTML = ''; return; }
  const data = await idx;
  const hits = data.filter(c => c.id.includes(term) ||
    (c.name && c.name.toLowerCase().includes(term)) || c.series.includes(term) ||
    (c.cms || []).some(x => x === term) || (c.hosts || []).some(h => h.includes(term)) ||
    (c.region && c.region.toLowerCase().includes(term)) ||
    (c.problems || []).some(p => p.toLowerCase().includes(term))).slice(0, 60);
  out.innerHTML = hits.map(c =>
    `<tr><td><a href="${REL}contest/${c.id}.html">${c.id}</a></td>` +
    `<td class="wrap">${c.name || ''}</td><td>${c.date || ''}</td>` +
    `<td class="small muted">${(c.cms || []).join(', ')}</td><td class="small muted wrap">${(c.hosts || []).slice(0, 3).join(' ')}</td></tr>`).join('');
});
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def refs(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def result_sources(c) -> list[dict]:
    """Sources serving any of the four published result tiers (not icpc_standings),
    each once however many tiers it serves."""
    return [s for s in sources(c) if any(r in s["roles"] for r in RESULT_KINDS)]


def held_path(e: dict) -> str | None:
    """The archived capture to link as "the" copy: the first entry of `archived` that we
    hold without a content caveat, else the first entry, else None."""
    paths = archived(e)
    if not paths:
        return None
    for p in paths:
        if not (capture_info.get(p) or {}).get("content_caveat"):
            return p
    return paths[0]


def held_capture(e: dict) -> bool:
    """The source points at a capture we hold and that capture is the real thing."""
    return any(not (capture_info.get(p) or {}).get("content_caveat") for p in archived(e))


def page(title: str, body: str, rel: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body>
<nav class="top"><div><a href="{rel}index.html">ICPC contest archive</a>
<a href="{rel}grid.html">grid</a> <a href="{rel}series/index.html">series</a>
<a href="{rel}seasons.html">seasons</a> <a href="{rel}coverage.html">coverage</a>
<a href="{rel}resources/index.html">resources</a> <a href="{rel}problems/index.html">problems</a> <a href="{rel}problemsets/index.html">problem sets</a> <a href="{rel}wanted.html">wanted</a>
<a href="{rel}cms.html">cms ids</a> <a href="{rel}local.html">local</a></div></nav>
<main>{body}</main>
<script>{TABLE_JS}</script></body></html>"""


CONTESTS: dict = {}  # filled by load(); lets every link carry the same tooltip


def link_contest(cid: str, rel: str, chip: bool = False) -> str:
    """The one way a contest is rendered as a link: id, with name · date on hover and an
    'upcoming' chip where the context lists contests that ran (chip=True)."""
    c = CONTESTS.get(cid) or {}
    tip = " · ".join(x for x in (c.get("name"), c.get("date")) if x)
    out = f'<a href="{rel}contest/{esc(cid)}.html"' + (f' title="{esc(tip)}"' if tip else "") + f'>{esc(cid)}</a>'
    if chip and c.get("status") == "upcoming":
        out += ' <span class="chip" title="has not run yet">upcoming</span>'
    return out


def best_tier(c) -> str:
    """The ONE tier ladder used by the grid, coverage, wanted list and marks:
    scoreboard > frozen_scoreboard > standings > rankings > icpc > none."""
    br = best_result(c)
    if not br:
        return "none"
    return "icpc" if br[0] == "icpc_standings" else br[0]


def web_state(c) -> str:
    """'link' (a web source), 'none' (confirmed none: web under `none:`), 'unknown' (not researched)."""
    if has_role(c, "web"):
        return "link"
    return "none" if "web" in (c.get("none") or []) else "unknown"


TIERS = (("scoreboard", "S"), ("frozen_scoreboard", "F"),
         ("standings", "St"), ("rankings", "R"))
MARK_LEGEND = ('<p class="small muted"><b>S</b> scoreboard · <b>F</b> frozen scoreboard · '
               '<b>St</b> standings · <b>R</b> rankings · <b>I</b> ICPC standings (lowest tier) — '
               '<span class="mark m-arch">filled</span> = archived copy held, '
               '<span class="mark m-live">outlined</span> = live link only (not yet archived)</p>')


def tier_marks(c):
    """One styled marker per artifact tier; preservation state = style, not a letter."""
    out = []
    for key, letter in TIERS:
        entries = by_role(c, key)
        if not entries:
            continue
        arch = next((e for e in entries if held_capture(e)), None)
        kind = key.replace("_", " ")
        if arch:
            out.append(f'<a class="mark m-arch" href="{REPLAY_BASE}/a/{esc(held_path(arch))}" '
                       f'title="{kind} — archived copy">{letter}</a>')
        else:
            out.append(f'<a class="mark m-live" href="{esc(entries[0]["url"])}" '
                       f'title="{kind} — live link only, not yet archived">{letter}</a>')
    ist = by_role(c, "icpc_standings")
    if ist:
        e = next((x for x in ist if held_capture(x)), None)
        if e:
            out.append(f'<a class="mark m-arch m-ist" href="{REPLAY_BASE}/a/{esc(held_path(e))}" '
                       f'title="ICPC standings — archived copy (rendered from the API dump)">I</a>')
        else:
            out.append(f'<a class="mark m-ist" href="{esc(ist[0]["url"])}" '
                       f'title="ICPC standings (CMS data) — live link only">I</a>')
    return "".join(out)


CMS_SLUGS: dict = {}


def load():
    global CMS_SLUGS
    p = ROOT / "data" / "cms-shortnames.json"
    if p.exists():
        CMS_SLUGS = {int(k): v for k, v in json.loads(p.read_text()).items()}
    series_docs = {}
    for f in sorted((ROOT / "series").glob("*.yaml")):
        series_docs[f.stem] = yaml.safe_load(f.read_text())
    contests, series_of = {}, {}
    for sid, doc in series_docs.items():
        for c in doc["contests"]:
            contests[c["id"]] = c
            series_of[c["id"]] = sid
    CONTESTS.clear()
    CONTESTS.update(contests)
    prev, children, subsets = defaultdict(list), defaultdict(list), defaultdict(list)
    for cid, c in contests.items():
        for n in refs(c.get("next")):
            prev[n].append(cid)
        for p in refs(c.get("parent")):
            children[p].append(cid)
        if c.get("subset_of"):
            subsets[c["subset_of"]].append(cid)
    aux = {}
    for name in ("archive-index", "replay-index", "website-index"):
        p = ROOT / "data" / f"{name}.json"
        aux[name] = json.loads(p.read_text()) if p.exists() else None
    return series_docs, contests, series_of, prev, children, subsets, aux


def health_chip(url: str, e: dict | None = None, rel: str = "") -> str:
    """The locator's health, one way everywhere: the source's url_state if it has one,
    else the resource graph's verdict (also_at mirrors and old entries have no field for it)."""
    st, when = None, None
    if e and e.get("url_state"):
        st, when = e["url_state"], e.get("url_checked")
    else:
        h = RES.health(url)
        if h:
            st, when = h.get("state"), h.get("checked")
    if not st:
        return ""
    t = STATE_TITLE.get(st, "") + (f" (checked {when})" if when else "")
    return f' <span class="chip" title="{esc(t)}">{esc(st)}</span>'


TIER_LABEL = {"scoreboard": "scoreboard", "frozen_scoreboard": "frozen scoreboard", "standings": "standings",
              "rankings": "rankings", "icpc": "ICPC standings only", "none": "no result"}


def lost_locators(c) -> list:
    """Result/web locators of this contest that are dead live AND have no Wayback snapshot:
    whatever we hold is the only copy; if we hold nothing, the material is lost."""
    out = []
    urls = [s["url"] for s in sources(c) if "web" in s["roles"] or any(r in s["roles"] for r in RESULT_KINDS)]
    for u in urls:
        L = RES.locs.get(site_resources.lid(u))
        if not L:
            continue
        h, wb = L.get("health") or {}, L.get("wayback") or {}
        if h.get("state") == "dead" and wb.get("state") in ("none", "excluded"):
            held = any(R.get("held") for R in L["resources"].values())
            out.append((u, wb["state"], held))
    return out


def state_line(c, cid: str) -> str:
    """One line per contest, same vocabulary everywhere: best tier held, archived or not,
    website state, and whether anything is lost (dead live + no snapshot + not held)."""
    bt = best_tier(c)
    bits = []
    if c.get("status") == "upcoming":
        bits.append('<span class="chip">upcoming</span>')
    tier = TIER_LABEL[bt]
    held = any(held_capture(e) for e in result_sources(c))
    ist_held = any(held_capture(e) for e in by_role(c, "icpc_standings"))
    if bt == "none":
        bits.append('<span class="chip" title="no result link of any tier">dark</span>')
    else:
        bits.append(f'<span class="chip">{esc(tier)}</span>'
                    + (" archived" if (held or (bt == "icpc" and ist_held)) else " <span class=\"muted\">live link only</span>"))
    ws = web_state(c)
    if ws == "link":
        bits.append("website archived" if cid in website_of else '<span class="muted">website not archived</span>')
    elif ws == "none":
        bits.append('<span class="muted">no website (confirmed)</span>')
    else:
        bits.append('<span class="muted">website unknown</span>')
    lost = lost_locators(c)
    if lost:
        gone = [u for u, _w, held in lost if not held]
        if gone:
            bits.append(f'<span class="chip" title="{esc("; ".join(gone))}">{len(gone)} lost</span>'
                        ' <span class="muted small">dead live, no snapshot, nothing held</span>')
        else:
            bits.append(f'<span class="chip" title="{esc("; ".join(u for u, *_ in lost))}">{len(lost)} only here</span>'
                        ' <span class="muted small">dead live, no snapshot — our copy is the only one</span>')
    return '<p class="state small">' + " · ".join(bits) + "</p>"


def local_link(path: str, label: str = "local") -> str:
    return f'<a class="local" href="{LOCAL_BASE}/{esc(path)}" title="{LOCAL_TITLE}">{label}</a>'


def result_links(cid, key, entries, replay_lookup, rel, matched_paths):
    rows = []
    for i, e in enumerate(entries):
        url = e["url"]
        as_of = e.get("as_of")
        parts = [f'<a href="{esc(url)}">live</a>']
        parts.append(f'<a href="{esc(wayback_link(url, as_of))}">wayback</a>')
        # every capture of this address gets a link; the preferred (held, no caveat) one first
        paths = archived(e)
        first = held_path(e)
        if first:
            paths = [first] + [p for p in paths if p != first]
        cap = capture_info.get(first or "")
        if paths:
            for n, pth in enumerate(paths):
                cp = capture_info.get(pth)
                when = fmt_time(cap_time(cp)) if cp else ""
                caveat = (cp or {}).get("content_caveat")
                baked = "a/" + pth
                matched_paths.add(baked)
                lab = "archived" if n == 0 else f"archived {n + 1}"
                title = "our copy of this resource" + (f" — caveat: {caveat}" if caveat else "")
                parts.append(f'<a href="{REPLAY_BASE}/{esc(baked)}" title="{esc(title)}">'
                             f'{lab}{" (" + when + ")" if when else ""}</a>'
                             + (' <span class="muted small">(caveat)</span>' if caveat else ""))
                parts.append(local_link("archive/" + pth, "raw"))
        else:
            baked = replay_lookup.get((cid, norm_key(url)))
            if baked:
                matched_paths.add(baked)
                parts.append(f'<a href="{REPLAY_BASE}/{esc(baked)}" title="our copy of this resource">archived</a>')
        rows.append(
            f'<div class="small"><span class="chip">{esc(key.replace("_", " ")) if key != "icpc_standings" else "ICPC standings"}</span> '
            + " · ".join(parts) + f' <span class="muted">{RES.label_link(url, as_of or cap_time(cap), rel, esc(res_label(url, as_of)))}</span>{health_chip(url, e)}</div>'
        )
    return rows


capture_info: dict = {}  # archive path -> capture entry (from data/archive-index.json)
website_of: dict = {}    # contest -> primary website capture (from data/website-index.json)


def cms_links(i) -> str:
    """`<id> (admin · finder)` for one CMS id."""
    lk = [f'<a href="https://icpc.global/private/contest/{i}/" '
          f'title="CMS admin page (login required)">admin</a>']
    slug = CMS_SLUGS.get(int(i))
    if slug:
        lk.append(f'<a href="https://icpc.global/regionals/finder/{esc(slug)}" '
                  f'title="public finder page">finder</a>')
    return f'{i} <span class="small">({" · ".join(lk)})</span>'


def cms_cell(c) -> str:
    ids = c.get("cms_ids")
    if ids:
        return ", ".join(cms_links(i) for i in ids)
    if ids == []:
        return '<span class="muted small">' + ("pre-CMS" if c.get("cms_status") == "pre-cms" else "none") + "</span>"
    return ""


def web_cell(c, cid: str) -> str:
    """Website links: host as label (full url in the tooltip), pinned wayback, and the
    local archived-site link when a crawl is held."""
    parts = []
    site = website_of.get(cid)
    if web_state(c) == "none":
        return '<span class="muted small">confirmed none</span>'
    for n, s in enumerate(by_role(c, "web")):
        w, as_of = s["url"], s.get("as_of")
        host = re.sub(r"^https?://(www\.)?", "", w).rstrip("/")
        host = host if len(host) <= 40 else host[:39] + "…"
        wb_ts = (site.get("wayback_timestamp") if site and n == 0 else None) or as_of
        bit = (f'<a href="{esc(w)}" title="{esc(res_label(w, as_of, 200))}">{esc(host)}</a>{health_chip(w, s)} '
               f'<a class="small" href="{esc(wayback_link(w, wb_ts))}">wb</a>')
        if RES.locator_href(w, "../"):
            bit += f' <a class="small" href="{RES.locator_href(w, "../")}" title="resource page">res</a>'
        if site and n == 0:
            bit += " " + local_link(f"site/{cid}/", "archived")
        parts.append(bit)
    return " · ".join(parts)


def cap_time(cap: dict):
    """The resource time of a capture: the served Wayback snapshot for wayback-sourced
    captures, else our own fetch time."""
    if not cap:
        return None
    ts = cap.get("wayback_timestamp") or unwrap(cap.get("wayback_url") or "")[1]
    if ts:
        return ts
    f = cap.get("fetched") or ""
    return re.sub(r"[^0-9]", "", f.split("+")[0].replace("Z", ""))[:14] or None


# ---- problems (DEFINITIONS.md, Problems) ----
# Phase B (2026-11-02): problem sets are objects. problemsets/<set-id>.yaml holds the
# holdings, the problems and the per-contest letter maps; a contest carries only
# `problems: {set: <set-id>, note?}`. judges.yaml is the registry of online judges.
SETS: dict = {}       # set id -> parsed problemsets/<set-id>.yaml
JUDGES: dict = {}     # judge id -> judges.yaml entry
PROBLEMS: dict = {}   # problem id -> {"rows": [(set id, problem row)], "apps": [(set id, contest id, letter|None)]}
REPLAY_LOOKUP: dict = {}  # (contest, norm_key(url)) -> baked replay path, filled by build()
REPLAY_PROBLEMSET: dict = {}  # the same, problem-set pages only
PROBLEMSET_CAPS: dict = {}  # (contest, norm_key(url)) -> archive path of a held problem-set capture (not published)
HELD_KINDS = (("statement", "St", "statements"), ("data", "D", "test data"),
              ("solutions", "So", "solutions"), ("package", "P", "complete packages"))
HELD_LEGEND = ('<p class="small muted"><b>St</b> statements · <b>D</b> test data · <b>So</b> solutions · '
               '<b>P</b> complete problem packages — <span class="mark h-full">filled</span> = held for every '
               'problem, <span class="mark h-part">outlined</span> = for some (hover for the number), '
               '<span class="mark h-none">grey</span> = none</p>')
HAVE_LEGEND = ('<p class="small muted"><b>St</b> statement · <b>D</b> test data · <b>IV</b>/<b>OV</b> input/output '
               'validator · <b>So</b> solutions · <b>P</b> complete package — filled = held.</p>')
REPO_URL = "https://github.com/icpc-contest-archive/contests/blob/main/"


def load_problem_sets():
    """Read problemsets/*.yaml and judges.yaml; index every problem by id with its
    appearances (set, contest, letter) — a problem id can sit in several sets (reused WF problems)."""
    SETS.clear()
    SETS.update(load_sets())
    JUDGES.clear()
    JUDGES.update(load_judges())
    PROBLEMS.clear()
    for sid, doc in SETS.items():
        for p in doc.get("problems") or []:
            ent = PROBLEMS.setdefault(p["id"], {"rows": [], "apps": []})
            ent["rows"].append((sid, p))
            for m in doc.get("contests") or []:
                inv = {pid: L for L, pid in (m.get("letters") or {}).items()}
                ent["apps"].append((sid, m["contest"], inv.get(p["id"])))


def set_for(c: dict) -> dict:
    """The set a contest used, or {} (also {} for a contest that has not run: nothing about
    its problems is public — DEFINITIONS.md, Problems, publication rule)."""
    if c.get("status") == "upcoming":
        return {}
    return set_of(c, SETS) or {}


def letter_of(doc: dict, cid: str, pid: str) -> str | None:
    """The letter problem `pid` had in contest `cid` (from the set's per-contest letter map)."""
    for L, x in set_letters(doc, cid).items():
        if x == pid:
            return L
    return None


def set_problems_in_order(doc: dict, cid: str | None = None) -> list[tuple[str | None, dict]]:
    """(letter, problem row) pairs: in letter order for the contest when it has a letter map
    (letterless problems after), else in file order with the letter from any member contest."""
    probs = doc.get("problems") or []
    if not probs:
        return []
    members = [m["contest"] for m in doc.get("contests") or []]
    use = cid if cid and set_letters(doc, cid) else next((m for m in members if set_letters(doc, m)), None)
    if not use:
        return [(None, p) for p in probs]
    inv = {pid: L for L, pid in set_letters(doc, use).items()}
    key = lambda L: (0, (len(L), L)) if L else (1, ("", ""))  # noqa: E731
    return sorted(((inv.get(p["id"]), p) for p in probs), key=lambda t: key(t[0]))


def problem_name(pid: str) -> str:
    rows = PROBLEMS.get(pid, {}).get("rows") or []
    return rows[0][1]["name"] if rows else pid


def contest_ref(cid: str, rel: str) -> str:
    """A contest link when the contest is in the mainline catalogue, else its id with a
    non-mainline chip (the registry contests have no page)."""
    if cid in CONTESTS:
        return link_contest(cid, rel)
    return f'{esc(cid)} <span class="chip" title="outside the mainline hierarchy (registry/non-mainline.yaml)">non-mainline</span>'


def set_link(sid: str, rel: str, label: str | None = None) -> str:
    doc = SETS.get(sid) or {}
    tip = doc.get("name") or ""
    return f'<a href="{rel}problemset/{esc(sid)}.html"' + (f' title="{esc(tip)}"' if tip else "") + f'>{esc(label or sid)}</a>'


def problem_link(pid: str, rel: str, label: str | None = None) -> str:
    return f'<a href="{rel}problem/{esc(pid)}.html">{esc(label or pid)}</a>'


def repo_link(pb: dict) -> str:
    repo = pb.get("repo")
    if not repo:
        return ""
    name = repo.split("/", 1)[1]
    tip = "statements only, in the shared statement-only repo" if name == "statement-only" else "problem archive repo (private)"
    return f'<a href="https://github.com/{esc(repo)}" title="{tip}">{esc(name)}</a>'


def held_marks(pb: dict) -> str:
    """One mark per kind of material, state = style: full / partial (n of count) / none."""
    out = []
    for key, letter, what in HELD_KINDS:
        st = pb.get(key)
        if st is None:
            out.append(f'<span class="mark h-unk" title="{what}: not recorded">{letter}</span>')
            continue
        n = (pb.get("counts") or {}).get(key)
        cnt = pb.get("count")
        detail = {"full": f"all {cnt} problems" if cnt else "every problem",
                  "partial": f"{n} of {cnt} problems" if n is not None and cnt else "some problems",
                  "none": "none held"}[st]
        out.append(f'<span class="mark h-{ {"full": "full", "partial": "part", "none": "none"}[st]}" '
                   f'title="{what}: {detail}">{letter}</span>')
    return "".join(out)


def held_chips(pb: dict) -> str:
    """The holdings as words: `statements: full` … with n/count for partial kinds."""
    words = []
    for key, _l, what in HELD_KINDS:
        st = pb.get(key)
        if not st:
            continue
        n = (pb.get("counts") or {}).get(key)
        words.append(f'<span class="chip">{what}: {st}' + (f" ({n}/{pb.get('count')})" if st == "partial" and n is not None else "") + "</span>")
    return " ".join(words)


JUDGE_CAPS: dict = {}  # (contest, norm_key(url)) -> archive path of a held judge-page capture (private, like problem sets)


def judge_name(jid: str) -> str:
    return (JUDGES.get(jid) or {}).get("name") or jid


def judge_closed_chip(jid: str) -> str:
    """A `closed <date>` chip for a judge the registry marks closed (Baekjoon, 2026-04-28)."""
    j = JUDGES.get(jid) or {}
    if j.get("status") != "closed":
        return ""
    when = j.get("closed") or ""
    return (f' <span class="chip" title="{esc(j.get("notes") or "this judge has shut down; pages survive only in Wayback snapshots")}">'
            f'closed{" " + esc(when) if when else ""}</span>')


def judge_links(j: dict | None, sep: str = " · ", cid: str | None = None) -> str:
    """Links grouped by judge: `{<judge>: url | {url, as_of} | [...]}`, numbered when a judge has several."""
    parts = []
    for key, v in (j or {}).items():
        locs = v if isinstance(v, list) else [v]
        lab = judge_name(key)
        for i, loc in enumerate(locs):
            url = loc["url"] if isinstance(loc, dict) else loc
            as_of = loc.get("as_of") if isinstance(loc, dict) else None
            href = wayback_link(url, as_of) if as_of else url
            bit = (f'<a href="{esc(href)}" title="{esc(res_label(url, as_of, 200))}">{esc(lab)}'
                   + (f" {i + 1}" if len(locs) > 1 else "") + ("</a> <span class=\"small muted\">(wayback)</span>" if as_of else "</a>"))
            if cid and (cid, norm_key(url)) in JUDGE_CAPS:
                bit += " " + local_link("archive/" + JUDGE_CAPS[(cid, norm_key(url))], "archived")
            bit += judge_closed_chip(key)
            parts.append(bit)
    return sep.join(parts)


def problem_judge_links(p: dict, sep: str = " · ") -> str:
    """A problem's `judges: [{judge, url, id?, as_of?}]` as links, the judge's own id in the tooltip."""
    parts = []
    for j in p.get("judges") or []:
        url, as_of = j["url"], j.get("as_of")
        href = wayback_link(url, as_of) if as_of else url
        tip = res_label(url, as_of, 200) + (f" — {judge_name(j['judge'])} id {j['id']}" if j.get("id") else "")
        parts.append(f'<a href="{esc(href)}" title="{esc(tip)}">{esc(judge_name(j["judge"]))}</a>'
                     + (' <span class="small muted">(wayback)</span>' if as_of else "") + judge_closed_chip(j["judge"]))
    return sep.join(parts)


def judge_page_links(c: dict, sep: str = " · ", cid: str | None = None) -> str:
    """The contest's judge pages: sources with role judge_page, grouped by `judge`
    (numbered when a judge has several), rendered like the per-problem judge links."""
    groups: dict[str, list] = {}
    for s in by_role(c, "judge_page"):
        groups.setdefault(s.get("judge") or "judge", []).append(
            {"url": s["url"], "as_of": s["as_of"]} if s.get("as_of") else s["url"])
    return judge_links(groups, sep, cid)


def problem_have_marks(p: dict) -> str:
    if "have" not in p:
        return '<span class="small muted" title="what the archive holds for this problem is not recorded yet">—</span>'
    have = set(p.get("have") or [])
    out = []
    for key, letter, what in (("statement", "St", "statement"), ("data", "D", "test data"),
                              ("input_validator", "IV", "input validator"), ("output_validator", "OV", "output validator"),
                              ("solutions", "So", "solutions"), ("package", "P", "complete package")):
        cls = "h-full" if key in have else "h-none"
        out.append(f'<span class="mark {cls}" title="{what}: {"held" if key in have else "not held"}">{letter}</span>')
    return "".join(out)


def problem_name_cell(p: dict, rel: str, link: bool = True) -> str:
    """name (linked to the problem page) · short name · private chip · uuid."""
    nm = problem_link(p["id"], rel, p["name"]) if link else esc(p["name"])
    if p.get("short_name"):
        nm += f' <span class="small muted">{esc(p["short_name"])}</span>'
    if p.get("status") == "private":
        nm += ' <span class="chip" title="kept private after the contest; name and uuid are public">private</span>'
    if p.get("uuid"):
        nm += f' <span class="small muted" title="problem package uuid">{esc(p["uuid"])}</span>'
    return nm


def problem_row(letter, p: dict, rel: str, first_cells: str = "") -> str:
    """One table row: [first_cells] letter · name · held · solve online · notes. A private
    problem shows name and uuid only (publication rule)."""
    private = p.get("status") == "private"
    return (f'<tr>{first_cells}<td class="letter">{esc(letter or "?")}</td><td class="wrap">{problem_name_cell(p, rel)}</td>'
            + ("<td></td><td></td><td></td>" if private else
               f'<td>{problem_have_marks(p)}</td><td class="small">{problem_judge_links(p)}</td>'
               f'<td class="wrap small muted">{esc(p.get("notes", ""))}</td>') + "</tr>")


def problems_section(cid: str, c: dict, rel: str) -> list[str]:
    """The Problems block of a contest page: the set's holdings, judge links, per-problem table."""
    pb = set_for(c)
    if not pb and not has_role(c, "problemset") and not has_role(c, "judge_page"):
        return []
    link = c.get("problems") or {}
    b = ['<h2 id="problems">Problems</h2>', '<dl class="fields">']
    if pb:
        others = [m["contest"] for m in pb.get("contests") or [] if m["contest"] != cid]
        b.append(f'<dt>problem set</dt><dd>{set_link(pb["id"], rel)}'
                 + (f' <span class="muted">{esc(pb["name"])}</span>' if pb.get("name") else "")
                 + (' <span class="small muted">— also used by ' + ", ".join(contest_ref(x, rel) for x in others) + "</span>" if others else "")
                 + "</dd>")
    if pb.get("count"):
        b.append(f"<dt>problems</dt><dd>{pb['count']}</dd>")
    if pb.get("repo"):
        b.append(f"<dt>archive repo</dt><dd>{repo_link(pb)} <span class=\"small muted\">(icpc-problem-archive, private)</span></dd>")
    if any(pb.get(k) for k, *_ in HELD_KINDS):
        b.append("<dt>held</dt><dd>" + held_chips(pb) + "</dd>")
    for s in by_role(c, "problemset"):
        w, as_of = s["url"], s.get("as_of")
        parts = [f'<a href="{esc(w)}">{esc(res_label(w, as_of, 80))}</a>',
                 f'<a href="{esc(wayback_link(w, as_of))}">wayback</a>']
        k = (cid, norm_key(w))
        # the problem-set capture of this address first (a source may also be a result page,
        # whose replay is linked under Results), else whatever replay page we have of it
        baked = REPLAY_PROBLEMSET.get(k)
        if baked:
            parts.append(f'<a href="{REPLAY_BASE}/{esc(baked)}" title="our copy of this resource">archived</a>')
        elif k in PROBLEMSET_CAPS:  # 2026-11-02: problem-set captures stay in the private archive
            parts.append(local_link("archive/" + PROBLEMSET_CAPS[k], "archived"))
        elif REPLAY_LOOKUP.get(k):
            parts.append(f'<a href="{REPLAY_BASE}/{esc(REPLAY_LOOKUP[k])}" title="our copy of this resource">archived</a>')
        if RES.locator_href(w, rel):
            parts.append(RES.label_link(w, as_of, rel, "resource"))
        b.append("<dt>published set</dt><dd>" + " · ".join(parts) + health_chip(w, s) + "</dd>")
    if has_role(c, "judge_page"):
        b.append("<dt>solve online</dt><dd>" + judge_page_links(c, cid=cid) + "</dd>")
    if pb.get("notes"):
        b.append(f'<dt>notes</dt><dd class="wrap">{esc(pb["notes"])}</dd>')
    if link.get("note"):
        b.append(f'<dt>note</dt><dd class="wrap">{esc(link["note"])}</dd>')
    if pb.get("provenance"):
        b.append('<dt>source</dt><dd class="small muted wrap">' + "; ".join(esc(x) for x in dict.fromkeys(pb["provenance"])) + "</dd>")
    b.append("</dl>")
    if pb.get("problems"):
        notes = []
        if not set_letters(pb, cid):
            notes.append("letters not known yet" if pb.get("letters") == "unknown"
                         or not any(set_letters(pb, m["contest"]) for m in pb["contests"])
                         else "no letter map for this contest (shown with another contest's letters)")
        if pb.get("complete") is False:
            notes.append(f"{len(pb['problems'])} of {pb.get('count') or '?'} problems listed")
        if notes:
            b.append('<p class="small muted">' + " · ".join(notes) + "</p>")
        b.append('<div class="tablewrap"><table><tr><th>#</th><th>problem</th><th>held</th><th>solve online</th><th>notes</th></tr>')
        for L, p in set_problems_in_order(pb, cid):
            b.append(problem_row(L, p, rel))
        b.append("</table></div>")
        b.append(HAVE_LEGEND[:-4] + f' Data: <a href="{REPO_URL}problemsets/{esc(pb["id"])}.yaml">problemsets/{esc(pb["id"])}.yaml</a>.</p>')
    return b


def problemset_page(sid: str, doc: dict, rel: str) -> str:
    """problemset/<set-id>.html — the set as an object: holdings, member contests with
    their letter maps, the problem table, provenance."""
    b = [f"<h1>{esc(doc.get('name') or sid)}</h1>"]
    if doc.get("name"):
        b.append(f'<p class="muted">{esc(sid)}</p>')
    b.append('<p class="small muted">problem set — <a href="../problemsets/index.html">all sets</a> · '
             '<a href="../problems/index.html">problem holdings</a></p>')
    d = ['<dl class="fields">', f"<dt>set id</dt><dd>{esc(sid)}</dd>"]
    members = [m["contest"] for m in doc.get("contests") or []]
    d.append("<dt>used by</dt><dd>" + ", ".join(contest_ref(m, rel) for m in members) + "</dd>")
    if doc.get("count"):
        d.append(f"<dt>problems</dt><dd>{doc['count']}" + (' <span class="small muted">(list incomplete)</span>' if doc.get("complete") is False and doc.get("problems") else "") + "</dd>")
    if doc.get("repo"):
        d.append(f"<dt>archive repo</dt><dd>{repo_link(doc)} <span class=\"small muted\">(icpc-problem-archive, private)</span></dd>")
    if any(doc.get(k) for k, *_ in HELD_KINDS):
        d.append("<dt>held</dt><dd>" + held_chips(doc) + " " + held_marks(doc) + "</dd>")
    if doc.get("letters") == "unknown":
        d.append('<dt>letters</dt><dd class="muted">not known for any contest (list came from an online judge)</dd>')
    if doc.get("notes"):
        d.append(f'<dt>notes</dt><dd class="wrap">{esc(doc["notes"])}</dd>')
    if doc.get("provenance"):
        d.append('<dt>provenance</dt><dd class="wrap small muted">' + "; ".join(esc(x) for x in dict.fromkeys(doc["provenance"])) + "</dd>")
    d.append(f'<dt>data</dt><dd class="small"><a href="{REPO_URL}problemsets/{esc(sid)}.yaml">problemsets/{esc(sid)}.yaml</a></dd>')
    d.append("</dl>")
    b += d
    probs = doc.get("problems") or []
    with_letters = [m for m in members if set_letters(doc, m)]
    if probs:
        b.append(f"<h2>Problems ({len(probs)}" + (f" of {doc['count']}" if doc.get("complete") is False and doc.get("count") else "") + ")</h2>")
        if len(members) > 1 and with_letters:
            b.append('<p class="small muted">The # column shows the letter in each contest that has a letter map: '
                     + " · ".join(f"{esc(m)}" for m in with_letters) + ".</p>")
        b.append('<div class="tablewrap"><table><tr><th>#</th><th>problem</th><th>internal id</th><th>held</th><th>solve online</th><th>notes</th></tr>')
        for L, p in set_problems_in_order(doc):
            if len(with_letters) > 1:
                ls = [letter_of(doc, m, p["id"]) for m in with_letters]
                L = " / ".join(x or "?" for x in ls) if len(set(ls)) > 1 else ls[0]
            private = p.get("status") == "private"
            b.append(f'<tr><td class="letter">{esc(L or "?")}</td><td class="wrap">{problem_name_cell(p, rel)}</td>'
                     f'<td class="small">{problem_link(p["id"], rel)}</td>'
                     + ("<td></td><td></td><td></td>" if private else
                        f'<td>{problem_have_marks(p)}</td><td class="small">{problem_judge_links(p)}</td>'
                        f'<td class="wrap small muted">{esc(p.get("notes", ""))}</td>') + "</tr>")
        b.append("</table></div>" + HAVE_LEGEND)
    else:
        b.append('<p class="muted">Only the holdings are recorded for this set; no per-problem list yet'
                 + (f" ({doc['count']} problems)" if doc.get("count") else "") + ".</p>")
    if len(with_letters) > 1 or (with_letters and len(members) > 1):
        b.append("<h2>Letter maps</h2>")
        for m in members:
            lm = set_letters(doc, m)
            b.append(f"<p><b>{contest_ref(m, rel)}</b>: " + (" · ".join(
                f'<span class="letter">{esc(L)}</span> {problem_link(pid, rel, problem_name(pid))}'
                for L, pid in sorted(lm.items(), key=lambda t: (len(t[0]), t[0]))) if lm else '<span class="muted">no letter map</span>') + "</p>")
    return page(doc.get("name") or sid, "\n".join(b), rel)


def problem_page(pid: str, ent: dict, rel: str) -> str:
    """problem/<pid>.html — one problem: name, uuid, ids, every appearance (set + contest +
    letter), holdings, judge links, status."""
    rows = ent["rows"]
    p = rows[0][1]  # the first set's row carries the name/uuid; others agree (same uuid)
    private = any(r.get("status") == "private" for _s, r in rows)
    b = [f"<h1>{esc(p['name'])}</h1>",
         '<p class="small muted">problem — <a href="../problems/list.html">every listed problem</a> · '
         '<a href="../problemsets/index.html">all sets</a></p>',
         '<dl class="fields">', f"<dt>internal id</dt><dd>{esc(pid)}</dd>"]
    uuids = sorted({r["uuid"] for _s, r in rows if r.get("uuid")})
    if uuids:
        b.append("<dt>uuid</dt><dd>" + ", ".join(esc(u) for u in uuids) + "</dd>")
    aliases = sorted({a for _s, r in rows for a in r.get("aliases") or []})
    if aliases:
        b.append("<dt>aliases</dt><dd>" + ", ".join(esc(a) for a in aliases) + "</dd>")
    shorts = sorted({r["short_name"] for _s, r in rows if r.get("short_name")})
    if shorts:
        b.append("<dt>short name</dt><dd>" + ", ".join(esc(x) for x in shorts) + "</dd>")
    apps = []
    for sid, cid, L in ent["apps"]:
        apps.append(f'{contest_ref(cid, rel)} <span class="small muted">({set_link(sid, rel)})</span>'
                    + (f' — <span class="letter">{esc(L)}</span>' if L else ""))
    b.append("<dt>appearances</dt><dd>" + "<br>".join(apps) + "</dd>")
    if private:
        b.append('<dt>status</dt><dd><span class="chip">private</span> <span class="small muted">kept private after the contest; name and uuid are public</span></dd>')
    else:
        have_rows = [r for _s, r in rows if "have" in r]
        if have_rows:
            b.append(f"<dt>held</dt><dd>{problem_have_marks(have_rows[0])}</dd>")
        else:
            b.append('<dt>held</dt><dd class="muted">not recorded yet</dd>')
        seen, jl = set(), []
        for _s, r in rows:
            for j in r.get("judges") or []:
                if j["url"] not in seen:
                    seen.add(j["url"])
                    jl.append(problem_judge_links({"judges": [j]}) + (f' <span class="small muted">id {esc(j["id"])}</span>' if j.get("id") else ""))
        if jl:
            b.append("<dt>solve online</dt><dd>" + "<br>".join(jl) + "</dd>")
        notes = [r["notes"] for _s, r in rows if r.get("notes")]
        if notes:
            b.append('<dt>notes</dt><dd class="wrap">' + "; ".join(esc(x) for x in dict.fromkeys(notes)) + "</dd>")
    b.append('<dt>data</dt><dd class="small">' + ", ".join(
        f'<a href="{REPO_URL}problemsets/{esc(s)}.yaml">problemsets/{esc(s)}.yaml</a>' for s, _r in rows) + "</dd>")
    b.append("</dl>")
    if not private:
        b.append(HAVE_LEGEND)
    return page(p["name"], "\n".join(b), rel)


def build(out: Path):
    series_docs, contests, series_of, prev, children, subsets, aux = load()
    derive_regions(series_docs, contests)
    load_problem_sets()
    out.mkdir(parents=True, exist_ok=True)
    (out / "contest").mkdir(exist_ok=True)
    (out / "series").mkdir(exist_ok=True)
    for sub in ("problemset", "problem", "problemsets", "judges"):
        (out / sub).mkdir(exist_ok=True)

    replay_lookup = REPLAY_LOOKUP
    replay_lookup.clear()
    REPLAY_PROBLEMSET.clear()
    replay_by_contest = defaultdict(list)
    if aux["replay-index"]:
        for e in aux["replay-index"]["pages"]:
            if e.get("url"):
                k = (e["contest"], norm_key(e["url"]))
                replay_lookup[k] = e["path"]
                if e.get("artifact") == "problemset":
                    REPLAY_PROBLEMSET[k] = e["path"]
            replay_by_contest[e["contest"]].append(e)
    archived_by_contest = defaultdict(list)
    PROBLEMSET_CAPS.clear()
    JUDGE_CAPS.clear()
    if aux["archive-index"]:
        for e in aux["archive-index"]["captures"]:
            archived_by_contest[e["contest"]].append(e)
            capture_info[e["path"]] = e
            if e.get("artifact") == "problemset" and e.get("url") and not e.get("content_caveat"):
                PROBLEMSET_CAPS.setdefault((e["contest"], norm_key(e["url"])), e["path"])
            if str(e.get("artifact", "")).startswith("judge-") and e.get("url") and not e.get("content_caveat"):
                JUDGE_CAPS.setdefault((e["contest"], norm_key(e["url"])), e["path"])
    website_of.clear()  # contest -> primary website capture entry
    if aux["website-index"]:
        for e in aux["website-index"]["sites"]:
            if e.get("primary") and not e.get("empty") and not e.get("shell"):  # empty/shell crawls are checks, not archives
                website_of[e["contest"]] = e

    # ---- contest pages ----
    for cid, c in contests.items():
        rel = "../"
        sid = series_of[cid]
        b = [f"<h1>{esc(cid)}</h1>"]
        if c.get("name"):
            b.append(f'<p class="muted">{esc(c["name"])}</p>')
        b.append(state_line(c, cid))
        d = ['<dl class="fields">']
        if c.get("status") == "upcoming":
            d.append("<dt>status</dt><dd>upcoming</dd>")
        if c.get("season"):
            d.append(f"<dt>season</dt><dd>{c['season'] - 1}–{c['season']}</dd>")
        if c.get("date"):
            d.append(f"<dt>date</dt><dd>{esc(c['date'])}</dd>")
        if c.get("location"):
            d.append(f"<dt>location</dt><dd>{esc(c['location'])}</dd>")
        d.append(f'<dt>series</dt><dd><a href="{rel}series/{esc(sid)}.html">{esc(sid)}</a></dd>')
        for label, ids in (
            ("advances to", refs(c.get("parent"))),
            ("feeders", sorted(children.get(cid, []))),
            ("next edition", refs(c.get("next"))),
            ("previous", sorted(prev.get(cid, []))),
            ("part of", [c["subset_of"]] if c.get("subset_of") else []),
            ("regional views", sorted(subsets.get(cid, []))),
        ):
            if ids:
                d.append(f"<dt>{label}</dt><dd>"
                         + ", ".join(link_contest(x, rel) for x in ids) + "</dd>")
        if c.get("parent") is None and "parent" in c:
            d.append('<dt>advances to</dt><dd class="muted">— (top of hierarchy)</dd>')
        ids = c.get("cms_ids")
        if ids:
            d.append("<dt>CMS ids</dt><dd>" + ", ".join(cms_links(i) for i in ids) + "</dd>")
        elif ids == []:
            d.append("<dt>CMS ids</dt><dd class='muted'>"
                     + ("pre-CMS era" if c.get("cms_status") == "pre-cms" else "none") + "</dd>")
        site = website_of.get(cid)
        for n_w, ws in enumerate(by_role(c, "web")):
            w, as_of = ws["url"], ws.get("as_of")
            wb_ts = as_of
            extra = ""
            if site and n_w == 0:
                if site.get("wayback_timestamp"):
                    wb_ts = site["wayback_timestamp"]  # the snapshot the crawl actually used
                npages = site.get("html_pages") or site.get("pages") or 0
                when = site.get("wayback_timestamp") or site.get("fetched", "")
                extra = (" · " + local_link(f"site/{cid}/", "archived site")
                         + f' <span class="muted">({npages} pages, '
                         + ("snapshot " if site.get("mode") == "wayback" else "live crawl ")
                         + esc(fmt_time(site.get("wayback_timestamp")) if site.get("wayback_timestamp")
                               else str(site.get("fetched", ""))[:10]) + ")</span>")
            d.append(f'<dt>web</dt><dd><a href="{esc(w)}">{esc(res_label(w, as_of, 80))}</a> · '
                     f'<a href="{esc(wayback_link(w, wb_ts))}">wayback</a>{extra}'
                     + (f' · {RES.label_link(w, wb_ts, rel, "resource")}' if RES.locator_href(w, rel) else "")
                     + health_chip(w, ws) + "</dd>")
        if web_state(c) == "none":
            d.append('<dt>web</dt><dd class="muted">confirmed none (see notes)</dd>')
        if c.get("notes"):
            d.append(f'<dt>notes</dt><dd class="wrap">{esc(c["notes"])}</dd>')
        if c.get("provenance"):
            d.append('<dt>provenance</dt><dd class="wrap small muted">'
                     + "; ".join(esc(x) for x in refs(c["provenance"])) + "</dd>")
        d.append("</dl>")
        b += d
        if best_result(c) or replay_by_contest.get(cid):
            b.append("<h2>Results</h2>")
            matched_paths: set = set()
            # one row per (tier, source): a source serving two tiers appears under each
            for key in RESULT_ROLES:
                b += result_links(cid, key, by_role(c, key), replay_lookup, rel, matched_paths)
            extra = [e for e in replay_by_contest.get(cid, []) if e["path"] not in matched_paths
                     and e.get("artifact") != "problemset"]
            for e in extra:
                u = e.get("url") or ""
                b.append(f'<div class="small"><span class="chip">{esc(e["artifact"])}</span> '
                         + (f'<a href="{esc(u)}">live</a>{health_chip(u)} · <a href="{esc(wayback_link(u))}">wayback</a> · ' if u else "")
                         + f'<a href="{REPLAY_BASE}/{esc(e["path"])}">archived</a> '
                         + f'<span class="muted">{RES.label_link(u, None, rel, esc(u[:90])) if u else ""}</span></div>')
        b += problems_section(cid, c, rel)
        caps = archived_by_contest.get(cid)
        if caps:
            b.append(f'<p class="small muted">{len(caps)} raw capture(s) in the archive repo '
                     f'({local_link(f"archive/{series_of[cid]}/{cid}/", "raw files")}).</p>')
        (out / "contest" / f"{cid}.html").write_text(page(cid, "\n".join(b), rel))

    # ---- series pages ----
    for sid, doc in series_docs.items():
        rel = "../"
        s = doc["series"]
        b = [f"<h1>{esc(sid)}</h1>"]
        if s.get("name"):
            b.append(f'<p class="muted">{esc(s["name"])}</p>')
        chips = []
        if s.get("tier"):
            chips.append(f'<span class="chip">{esc(s["tier"])}</span>')
        for ev in s.get("lineage", []):
            chips.append(f'<span class="chip">{esc(ev["type"])} '
                         f'<a href="{esc(ev["series"])}.html">{esc(ev["series"])}</a> ({ev["year"]})</span>')
        if chips:
            b.append("<p>" + " ".join(chips) + "</p>")
        ran = [c for c in doc["contests"] if c.get("status") != "upcoming"]
        if ran:
            tiers = defaultdict(int)
            for c in ran:
                tiers[best_tier(c)] += 1
            n_arch = sum(1 for c in ran if any(held_capture(e) for e in result_sources(c)))
            n_site = sum(1 for c in ran if c["id"] in website_of)
            n_lost = sum(1 for c in ran if any(not held for _u, _w, held in lost_locators(c)))
            parts = [f'{tiers[k]} {TIER_LABEL[k]}' for k in ("scoreboard", "frozen_scoreboard", "standings", "rankings", "icpc", "none") if tiers[k]]
            b.append(f'<p class="state small">{len(ran)} editions ran'
                     + (f' (+{len(doc["contests"]) - len(ran)} upcoming)' if len(doc["contests"]) > len(ran) else "")
                     + ": " + ", ".join(parts) + f" · {n_arch} with an archived result · {n_site} websites archived"
                     + (f' · <span class="chip">{n_lost} lost</span>' if n_lost else "") + "</p>")
        b.append(MARK_LEGEND)
        has_probs = any(set_for(c) or has_role(c, "judge_page") for c in doc["contests"])
        if has_probs:
            b.append(HELD_LEGEND)
        b.append('<div class="tablewrap"><table><tr><th>contest</th><th>date</th>'
                 "<th>advances to</th><th>results</th>" + ("<th>problems</th>" if has_probs else "")
                 + "<th>CMS id</th><th>website</th></tr>")
        for c in reversed(doc["contests"]):  # latest first
            pcell = ""
            if has_probs:
                pb = set_for(c)
                pcell = ("<td>" + (f'<span class="small muted">{pb["count"]}</span> ' if pb.get("count") else "")
                         + held_marks(pb) + (f' <span class="small">{set_link(pb["id"], rel, "set")}</span>' if pb.get("problems") else "")
                         + "</td>") if pb else "<td></td>"
            b.append(
                "<tr><td>" + link_contest(c["id"], rel, chip=True) + "</td>"
                f"<td>{esc(c.get('date', ''))}</td>"
                "<td>" + ", ".join(link_contest(p, rel) for p in refs(c.get("parent"))) + "</td>"
                f"<td>{tier_marks(c)}</td>{pcell}<td>{cms_cell(c)}</td>"
                f'<td class="wrap">{web_cell(c, c["id"])}</td></tr>'
            )
        b.append("</table></div>")
        (out / "series" / f"{sid}.html").write_text(page(sid, "\n".join(b), rel))

    # series index
    rel = "../"
    rows = []
    for sid in sorted(series_docs):
        doc = series_docs[sid]
        years = [int(c["id"].rsplit("-", 1)[1]) for c in doc["contests"]]
        tier = doc["series"].get("tier") or ("World Finals" if sid == "wf" else "")
        rows.append(f'<tr><td><a href="{esc(sid)}.html">{esc(sid)}</a></td>'
                    f"<td>{len(years)}</td><td>{min(years)}–{max(years)}</td>"
                    f'<td class="small muted">{esc(SERIES_REGION.get(sid, "Other"))}</td>'
                    f'<td>{("<span class=chip>" + esc(tier) + "</span>") if tier else ""}</td>'
                    f'<td class="wrap">{esc(doc["series"].get("name", ""))}</td></tr>')
    (out / "series" / "index.html").write_text(page(
        "Series", "<h1>Series</h1><div class='tablewrap'><table>"
        "<tr><th>series</th><th>editions</th><th>years</th><th>region</th><th>tier</th><th>name</th></tr>"
        + "\n".join(rows) + "</table></div>", rel))

    # ---- season tree pages ----
    (out / "season").mkdir(exist_ok=True)
    by_season = defaultdict(list)
    for cid, c in contests.items():
        if c.get("season"):
            by_season[c["season"]].append(cid)
    for season, members in by_season.items():
        rel = "../"
        mset = set(members)
        seen: set = set()

        def node(cid):
            seen.add(cid)
            c = contests[cid]
            kids = sorted(k for k in children.get(cid, []) if k in mset and k not in seen)
            extra = " · ".join(x for x in (cms_cell(c), web_cell(c, cid)) if x)
            label = (link_contest(cid, rel, chip=True)
                     + f'<span class="meta">{esc(c.get("date", ""))} {tier_marks(c)}'
                     + (f' <span class="small">{extra}</span>' if extra else "") + "</span>")
            if not kids:
                return f'<div class="leaf">{label}</div>'
            inner = "\n".join(node(k) for k in kids)
            return f"<details open><summary>{label}</summary>{inner}</details>"

        wf_id = f"wf-{season}"
        body = [f"<h1>Season {season - 1}–{season}</h1>", MARK_LEGEND]
        if wf_id in contests:
            body.append(f'<div class="tree">{node(wf_id)}</div>')
        unplaced = sorted(m for m in mset if m not in seen)
        if unplaced:
            body.append(f'<h2>Not yet placed in the tree ({len(unplaced)})</h2><p class="small">'
                        + ", ".join(link_contest(x, rel) for x in unplaced) + "</p>")
        (out / "season" / f"{season}.html").write_text(
            page(f"Season {season - 1}–{season}", "\n".join(body), rel))

    # ---- seasons index ----
    rel = ""
    rows = []
    for season in sorted(by_season, reverse=True):
        ids = by_season[season]
        wf = [x for x in ids if x.startswith("wf-")]
        wfc = [contests[x] for x in sorted(wf)]
        rows.append(f'<tr><td><a href="season/{season}.html">{season - 1}–{season}</a></td>'
                    "<td>" + ", ".join(link_contest(x, rel) for x in sorted(wf)) + "</td>"
                    "<td>" + ", ".join(esc(c.get("date", "")) for c in wfc) + "</td>"
                    "<td>" + "; ".join(cms_cell(c) for c in wfc if cms_cell(c)) + "</td>"
                    '<td class="wrap">' + " · ".join(web_cell(c, c["id"]) for c in wfc if web_cell(c, c["id"])) + "</td>"
                    f"<td>{len(ids)}</td></tr>")
    (out / "seasons.html").write_text(page(
        "Seasons", "<h1>Seasons</h1><p class='muted'>Each season links to its full "
        "advancement tree.</p><div class='tablewrap'><table>"
        "<tr><th>season</th><th>World Finals</th><th>date</th><th>CMS id</th><th>website</th><th>contests</th></tr>"
        + "\n".join(rows) + "</table></div>", rel))

    # ---- the grid ----
    rel = ""
    years_all = [int(cid.rsplit("-", 1)[1]) for cid in contests]
    y0, y1 = min(years_all), max(years_all)
    by_sy = {(cid.rsplit("-", 1)[0], int(cid.rsplit("-", 1)[1])): cid for cid in contests}
    lineage_at = defaultdict(list)
    for sid, doc in series_docs.items():
        for ev in doc["series"].get("lineage", []):
            if ev["type"] == "continues-as":
                lineage_at[(sid, ev["year"])].append(ev["series"])

    def cell_class(c):
        if c.get("status") == "upcoming":
            return "c-up", "upcoming"
        bt = best_tier(c)
        return {"scoreboard": ("c-sb", "scoreboard"), "frozen_scoreboard": ("c-sb", "frozen scoreboard"),
                "standings": ("c-res", "standings only"), "rankings": ("c-res", "rankings only"),
                "icpc": ("c-ist", "ICPC standings only"), "none": ("c-none", "no results yet")}[bt]

    def region_rows(sids):
        return sorted(sids, key=lambda s: (min(int(c["id"].rsplit("-", 1)[1])
                                               for c in series_docs[s]["contests"]), s))

    groups = [("World Finals", ["wf"]),
              ("Championships", region_rows([s for s in series_docs if s in CHAMPIONSHIPS]))]
    for gname in REGION_GROUPS:
        groups.append((gname, region_rows([s for s in series_docs
                                           if SERIES_REGION.get(s) == gname])))
    leftover = [s for s in series_docs
                if s != "wf" and s not in CHAMPIONSHIPS and s not in SERIES_REGION]
    if leftover:
        groups.append(("Other", region_rows(leftover)))
        print("grid: unassigned series in 'Other':", leftover)

    g = ['<div class="tablewrap"><table class="grid"><thead><tr><th class="lbl"></th>']
    g += [f"<th>{y}</th>" for y in range(y0, y1 + 1)]
    g.append("</tr></thead>")
    ncols = y1 - y0 + 2
    for gname, sids in groups:
        if not sids:
            continue
        g.append(f'<tr class="grp"><td class="lbl" colspan="{ncols}">{esc(gname)}</td></tr>')
        for sid in sids:
            g.append(f'<tr><td class="lbl"><a href="series/{esc(sid)}.html">{esc(sid)}</a></td>')
            for y in range(y0, y1 + 1):
                cid = by_sy.get((sid, y))
                if cid:
                    cls, why = cell_class(contests[cid])
                    cc = contests[cid]
                    g.append(f'<td><a class="cell {cls}" href="contest/{esc(cid)}.html" '
                             f'title="{esc(cid)}{" · " + esc(cc["date"]) if cc.get("date") else ""} — {why}"></a></td>')
                elif lineage_at.get((sid, y)):
                    tgt = lineage_at[(sid, y)][0]
                    g.append(f'<td><a class="c-lin" href="series/{esc(tgt)}.html" '
                             f'title="continues as {esc(tgt)} ({y})">→</a></td>')
                else:
                    g.append("<td></td>")
            g.append("</tr>")
    g.append("</table></div>")
    legend = ('<p class="small"><span class="chip">legend</span> '
              '<span class="cell c-sb" style="display:inline-block;vertical-align:middle"></span> scoreboard · '
              '<span class="cell c-res" style="display:inline-block;vertical-align:middle"></span> standings/rankings · '
              '<span class="cell c-ist" style="display:inline-block;vertical-align:middle"></span> ICPC standings only · '
              '<span class="cell c-none" style="display:inline-block;vertical-align:middle"></span> no results yet · '
              '<span class="cell c-up" style="display:inline-block;vertical-align:middle"></span> upcoming · '
              '→ series continues under a new name</p>')
    (out / "grid.html").write_text(page(
        "The grid", "<h1>Every ICPC contest, one screen</h1>"
        "<p class='muted'>Rows are series, grouped by level and region; columns are years; "
        "color shows how much of the results we hold. Click any cell.</p>"
        + legend + "".join(g), rel))

    # ---- coverage (era / season / series / world region) ----
    def cov_flags(c):
        """Result coverage is measured per tier, cumulatively down the information
        order scoreboard > frozen scoreboard > standings > rankings > ICPC standings:
        each flag means "holds this tier or a better one". Web coverage separately:
        a site link, and an archived crawl of it."""
        sb = has_role(c, "scoreboard")
        fr = sb or has_role(c, "frozen_scoreboard")
        st = fr or has_role(c, "standings")
        rk = st or has_role(c, "rankings")
        any_ = rk or has_role(c, "icpc_standings")
        return {"n": 1, "date": bool(c.get("date")),
                "sb": sb, "fr": fr, "st": st, "rk": rk, "any": any_,
                "arch": any(held_capture(e) for e in result_sources(c)),
                "web": web_state(c) == "link",
                "web_none": web_state(c) == "none",
                "web_arch": c["id"] in website_of}

    ran_rows = []  # (year, series, region, flags)
    for cid, c in contests.items():
        if c.get("status") == "upcoming":
            continue
        s = series_of[cid]
        ran_rows.append((int(cid.rsplit("-", 1)[1]), s,
                         SERIES_REGION.get(s, "Other"), cov_flags(c)))
    missing_regions = sorted({s for _, s, r, _ in ran_rows if r == "Other"})
    if missing_regions:
        print(f"  warn: series without a world region: {missing_regions}")

    def agg(flag_iter):
        t = defaultdict(int)
        for f in flag_iter:
            for k, v in f.items():
                t[k] += int(v)
        return t

    def pcell(part, total):
        if not total:
            return '<td class="num muted">–</td>'
        p = round(100 * part / total)
        return f'<td class="num">{p}%<span class="bar"><i style="width:{p}%"></i></span></td>'

    COV_HDR = ('<tr><th rowspan="2">{}</th><th rowspan="2" class="num">contests</th>'
               '<th colspan="5" class="grp">results — holds this tier or better</th>'
               '<th rowspan="2" class="num" title="a result capture held in this project">archived<br>result</th>'
               '<th colspan="2" class="grp">website</th>'
               '<th rowspan="2" class="num">dated</th>'
               '<th rowspan="2" class="num" title="no result link of any tier">missing</th></tr>'
               '<tr><th class="num" title="full per-problem scoreboard">scoreboard</th>'
               '<th class="num" title="frozen scoreboard or better">≥ frozen</th>'
               '<th class="num" title="standings (totals) or better">≥ standings</th>'
               '<th class="num" title="rankings (order only) or better">≥ rankings</th>'
               '<th class="num" title="any result link incl. the ICPC standings system">≥ ICPC</th>'
               '<th class="num" title="a contest-website link">link</th>'
               '<th class="num" title="an archived crawl of the website">archived</th></tr>')

    def cov_row(label, t):
        return (f'<tr><td class="wrap">{label}</td><td class="num">{t["n"]}</td>'
                + pcell(t["sb"], t["n"]) + pcell(t["fr"], t["n"]) + pcell(t["st"], t["n"])
                + pcell(t["rk"], t["n"]) + pcell(t["any"], t["n"]) + pcell(t["arch"], t["n"])
                + pcell(t["web"], t["n"]) + pcell(t["web_arch"], t["n"]) + pcell(t["date"], t["n"])
                + f'<td class="num">{t["n"] - t["any"]}</td></tr>')

    tot = agg(f for *_x, f in ran_rows)
    cov = ["<h1>Collection coverage</h1>",
           f'<p class="muted">{tot["n"]} contests that ran. '
           f'Results, by best tier held: {tot["sb"]} ({round(100 * tot["sb"] / tot["n"])}%) a full '
           f'scoreboard, {tot["fr"]} at least a frozen scoreboard, {tot["st"]} at least standings, '
           f'{tot["rk"]} at least rankings, {tot["any"]} ({round(100 * tot["any"] / tot["n"])}%) '
           f'any result at all (counting the ICPC standings system); {tot["arch"]} have a result '
           f'capture in this project. Websites: {tot["web"]} have a link, {tot["web_arch"]} an '
           f'archived crawl. {tot["n"] - tot["any"]} are still dark — see the '
           f'<a href="wanted.html">wanted list</a>.</p>',
           '<p class="small muted">jump to: <a href="#era">era</a> · <a href="#season">year</a> · '
           '<a href="#region">world region</a> · <a href="#series">series</a> — result columns are '
           'cumulative down the information order scoreboard &gt; frozen scoreboard &gt; standings '
           '&gt; rankings &gt; ICPC standings ("≥ standings" = standings or better); hover a '
           'column header for its definition.</p>']

    eras = [("1970–1998", 0, 1998), ("1999–2007", 1999, 2007),
            ("2008–2015", 2008, 2015), ("2016–present", 2016, 9999)]
    cov.append('<h2 id="era">By era</h2><div class="tablewrap"><table>' + COV_HDR.format("era"))
    for label, lo, hi in eras:
        cov.append(cov_row(label, agg(f for y, *_x, f in ran_rows if lo <= y <= hi)))
    cov.append("</table></div>")

    cov.append('<h2 id="season">By year</h2><p class="small muted">Regionals are listed under '
               'the year they ran (season start); finals and championships under their own year. '
               'Season trees live under <a href="seasons.html">seasons</a>.</p>'
               '<div class="tablewrap"><table>' + COV_HDR.format("year"))
    for y in sorted({y for y, *_x in ran_rows}, reverse=True):
        cov.append(cov_row(str(y), agg(f for yy, *_x, f in ran_rows if yy == y)))
    cov.append("</table></div>")

    region_names = list(REGION_GROUPS) + (["Other"] if missing_regions else [])
    cov.append('<h2 id="region">By world region</h2><div class="tablewrap"><table>'
               + COV_HDR.format("world region"))
    for g in region_names:
        cov.append(cov_row(g, agg(f for _y, _s, r, f in ran_rows if r == g)))
    cov.append("</table></div>")

    per_series = defaultdict(list)
    for y, s, _r, f in ran_rows:
        per_series[s].append((y, f))
    cov.append('<h2 id="series">By series</h2><p class="small muted">Sorted by missing count — '
               'the top of this table is the hunting worklist. "website link" excludes contests '
               'whose website is confirmed none.</p>'
               '<div class="tablewrap"><table>'
               + COV_HDR.format("series").replace("<th>series</th>",
                                                  "<th>series</th><th>region</th><th>years</th>"))
    srows = []
    for s, lst in per_series.items():
        t = agg(f for _y, f in lst)
        ys = [y for y, _f in lst]
        label = (f'<a href="series/{esc(s)}.html">{esc(s)}</a></td>'
                 f'<td class="small muted">{esc(SERIES_REGION.get(s, "Other"))}</td>'
                 f'<td class="small">{min(ys)}–{max(ys)}')
        srows.append((t["n"] - t["any"], t["n"], s, cov_row(label, t)))
    for _m, _n, _s, r in sorted(srows, key=lambda x: (-x[0], -x[1], x[2])):
        cov.append(r)
    cov.append("</table></div>")
    (out / "coverage.html").write_text(page("Coverage", "\n".join(cov), ""))

    # ---- URL indexes per artifact ----
    (out / "resources").mkdir(exist_ok=True)

    def wb_href(e):
        return wayback_link(e["url"], e["as_of"]) if e.get("as_of") else None

    url_tables = {k: [] for k, _ in TIERS}
    for k in ("icpc_standings", "web", "mirror", "problemset"):
        url_tables[k] = []
    for cid in sorted(contests):
        c = contests[cid]
        # a source is listed under each role it serves; `also_at` addresses are the mirrors
        for k in url_tables:
            if k != "mirror":
                url_tables[k] += [(cid, e) for e in by_role(c, k)]
        for s in sources(c):
            for m in also_at(s):
                url_tables["mirror"].append((cid, m))
    art_order = ["scoreboard", "frozen_scoreboard", "standings", "rankings",
                 "icpc_standings", "web", "mirror", "problemset"]
    counts = {k: len(url_tables[k]) for k in art_order}
    for k in art_order:
        nav_line = " · ".join(
            (f'<b>{kk.replace("_", " ")} ({counts[kk]})</b>' if kk == k else
             f'<a href="{kk}.html">{kk.replace("_", " ")} ({counts[kk]})</a>')
            for kk in art_order)
        rows_h = []
        for cid, e in url_tables[k]:
            extras = []
            hc = health_chip(e["url"], e)
            if hc:
                extras.append(hc.strip())
            wb = wb_href(e)
            if wb:
                extras.append(f'<a class="small" href="{esc(wb)}">wayback</a>')
            for n, pth in enumerate(archived(e)):
                extras.append(f'<a class="small" href="{REPLAY_BASE}/a/{esc(pth)}">'
                              + ("archived" if n == 0 else f"archived {n + 1}") + '</a>')
            if e.get("note") and k == "mirror":
                extras.append(f'<span class="muted small">{esc(e["note"])}</span>')
            rows_h.append(f'<tr><td>{link_contest(cid, "../")}</td>'
                          f'<td class="wrap">{RES.label_link(e["url"], e.get("as_of"), "../", esc(res_label(e["url"], e.get("as_of"), 110)))}'
                          f' <a class="small" href="{esc(e["url"])}">live</a></td>'
                          f'<td>{" ".join(extras)}</td></tr>')
        legend = " · ".join(f'<span class="chip" title="{esc(v)}">{k}</span>' for k, v in STATE_TITLE.items())
        body = (f'<h1>{k.replace("_", " ")} resources</h1><p class="small muted">{nav_line}</p>'
                f'<p class="small muted">A resource is a URL at a time — <code>url (time)</code> when the '
                f'content meant is a dated snapshot (see <a href="../local.html">definitions</a>). '
                f'Chips are the locator\'s health at the last live check (hover for the rule): {legend}</p>'
                '<div class="tablewrap"><table><tr><th>contest</th><th>resource</th><th></th></tr>'
                + "\n".join(rows_h) + "</table></div>")
        (out / "resources" / f"{k}.html").write_text(page(f"{k.replace('_', ' ')} resources", body, "../"))
    # old address: a redirect stub per page so bookmarks keep working
    (out / "urls").mkdir(exist_ok=True)
    for k in art_order + ["index"]:
        (out / "urls" / f"{k}.html").write_text(
            f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=../resources/{k}.html">'
            f'<title>moved</title><p>Moved to <a href="../resources/{k}.html">resources/{k}.html</a>.</p>')
    (out / "resources" / "index.html").write_text(page("Resources", (
        "<h1>Every resource in the catalogue, by artifact</h1><ul>"
        + "".join(f'<li><a href="{k}.html">{k.replace("_", " ")}</a> — {counts[k]} resources</li>'
                  for k in art_order)
        + "</ul><p class='small muted'>A resource is a URL at a time; a bare URL is a locator "
        "whose live content is what is meant. Chips show the last live-check verdict where one has "
        "been recorded (hover a chip for the rule); wayback/archived links point at the pinned "
        "snapshot and this project's own captured copy.</p>"), "../"))

    # ---- wanted list ----
    WANT_COLS = [  # (best tier held, column title, what is wanted)
        ("none", "nothing", "no result of any kind, not even in the ICPC standings system"),
        ("icpc", "ICPC standings only", "only the CMS's own result data (formally official, often "
                 "wrong in practice) — the published scoreboard is wanted"),
        ("rankings", "rankings only", "order of teams only — standings or scoreboard wanted"),
        ("standings", "standings only", "totals per team — the per-problem scoreboard wanted"),
        ("frozen_scoreboard", "frozen only", "frozen scoreboard — the final scoreboard wanted"),
    ]
    WEB_COLS = [("nolink", "no website link"), ("noarch", "website not archived"),
                ("lost", "lost")]  # confirmed-none sites are not wanted; lost = dead live, no snapshot, nothing held

    def site_mark(cid):
        return (" " + local_link(f"site/{cid}/", "site")) if cid in website_of else ""

    wl_tot = defaultdict(int)
    sections = []
    for g in region_names:
        sec = []
        for sname in sorted(per_series):
            if SERIES_REGION.get(sname, "Other") != g:
                continue
            cells = defaultdict(list)
            for c in series_docs[sname]["contests"]:
                if c.get("status") == "upcoming":
                    continue
                cid = c["id"]
                bt = best_tier(c)
                if bt != "scoreboard":
                    cells[bt].append(link_contest(cid, "") + site_mark(cid))
                    wl_tot[bt] += 1
                ws = web_state(c)
                if ws == "unknown":
                    cells["nolink"].append(link_contest(cid, ""))
                    wl_tot["nolink"] += 1
                elif ws == "link" and cid not in website_of:
                    cells["noarch"].append(link_contest(cid, ""))
                    wl_tot["noarch"] += 1
                gone = [u for u, _w, held in lost_locators(c) if not held]
                if gone:
                    cells["lost"].append(link_contest(cid, "") + f'<span class="small muted" title="{esc("; ".join(gone))}"> ×{len(gone)}</span>')
                    wl_tot["lost"] += 1
            if cells:
                sec.append(f'<tr><td><a href="series/{esc(sname)}.html">{esc(sname)}</a></td>'
                           + "".join(f'<td class="wrap">{" ".join(cells[k])}</td>'
                                     for k, *_ in WANT_COLS + WEB_COLS) + "</tr>")
        if sec:
            hdr = ("<tr><th>series</th>" + "".join(
                f'<th title="{esc(w)}">{t}</th>' for _k, t, w in WANT_COLS)
                + "".join(f'<th title="{"dead live, no Wayback snapshot, nothing held here: the material is gone unless someone kept a copy" if _k == "lost" else ""}">{t}</th>' for _k, t in WEB_COLS) + "</tr>")
            sections.append(f'<h2 class="rgn">{g}</h2><div class="tablewrap"><table>'
                            + hdr + "\n".join(sec) + "</table></div>")
    wl = ["<h1>Most wanted</h1>",
          '<p class="muted">Every contest that ran, filed under the <b>best result tier we hold</b>, '
          "from nothing at all up to a frozen scoreboard; anything better than that is wanted "
          "(a contest with a full scoreboard is not listed). The two right-hand columns track the "
          "contest <b>website</b>: no link known, or a link we have not yet archived; <b>lost</b> lists contests "
          "with a result/web locator that is dead live, has no Wayback snapshot and nothing held here — "
          "only a private copy can recover those. Hover a column "
          "header for the definition. Know where any of these live? "
          '<a href="https://github.com/icpc-contest-archive/contests">Open an issue.</a></p>',
          '<p class="small muted">Totals: ' + " · ".join(
              f"<b>{wl_tot[k]}</b> {t}" for k, t, _w in WANT_COLS) + " · " + " · ".join(
              f"<b>{wl_tot[k]}</b> {t}" for k, t in WEB_COLS)
          + '. A <span class="local-ex">site</span> mark after a contest means its website is '
          "archived here — often the place to start looking for the missing results.</p>"]
    wl += sections
    (out / "wanted.html").write_text(page("Most wanted", "\n".join(wl), ""))

    # ---- CMS id ledger ----
    cms_rows = {}
    for cid, c in contests.items():
        for i in (c.get("cms_ids") or []):
            cms_rows[int(i)] = ("mainline", link_contest(cid, ""), esc(c.get("name") or ""))
    tri = yaml.safe_load((ROOT / "registry" / "cms-triage.yaml").read_text())
    for e in (tri.get("excluded") or []):
        cms_rows.setdefault(int(e["cms_id"]),
                            (f'excluded: {e.get("reason")}', "", esc(str(e.get("name") or ""))))
    prop_p = ROOT / "registry" / "cms-triage-proposed.yaml"
    if prop_p.exists():
        for e in (yaml.safe_load(prop_p.read_text()).get("proposed") or []):
            cms_rows.setdefault(int(e["cms_id"]),
                                (f'proposed: {e.get("reason")}', "", esc(str(e.get("name") or ""))))
    wl_p = ROOT / "data" / "reconciliation-worklist.json"
    if wl_p.exists():
        for e in json.loads(wl_p.read_text()):
            try:
                i = int(e.get("Contest ID"))
            except (TypeError, ValueError):
                continue
            cms_rows.setdefault(i, ("unreviewed", "", esc(str(e.get("Full name") or ""))))
    counts_cms = defaultdict(int)
    for st, _l, _n in cms_rows.values():
        counts_cms[st.split(":")[0]] += 1
    ledger = ["<h1>CMS id ledger</h1>",
              f'<p class="muted">Every CMS contest id this project knows about: '
              f'{len(cms_rows)} ids — {counts_cms["mainline"]} in the mainline catalogue, '
              f'{counts_cms["excluded"]} excluded with a reason, {counts_cms["proposed"]} with a '
              f'proposed (unreviewed) triage class, {counts_cms["unreviewed"]} not yet judged.</p>',
              '<p class="small muted"><b>mainline</b> = a real contest in the advancement hierarchy '
              '(linked). <b>excluded</b> = judged not part of the mainline catalogue — the reason says '
              'why (cancelled, camp, challenge, junk, minor, structural). <b>proposed</b> = '
              'auto-classified, awaiting review. <b>unreviewed</b> = a CMS id nobody has judged yet.</p>',
              '<div class="tablewrap"><table><tr><th class="num">cms id</th><th>contest</th>'
              '<th>status</th><th>CMS name</th><th>CMS links</th></tr>']
    for i in sorted(cms_rows):
        st, link, name = cms_rows[i]
        ledger.append(f'<tr><td class="num">{i}</td><td>{link}</td>'
                      f'<td><span class="chip">{esc(st)}</span></td>'
                      f'<td class="wrap small">{name}</td>'
                      f'<td class="small">{cms_links(i).split(" ", 1)[1]}</td></tr>')
    ledger.append("</table></div>")
    (out / "cms.html").write_text(page("CMS id ledger", "\n".join(ledger), ""))

    # ---- problems: coverage + every contest with archive holdings + every problem ----
    (out / "problems").mkdir(exist_ok=True)
    nm_doc = yaml.safe_load((ROOT / "registry" / "non-mainline.yaml").read_text())
    nm_with = [c for c in nm_doc["non_mainline_contests"] if set_for(c) or has_role(c, "judge_page")]
    rel = "../"

    def pflags(c):
        pb = set_for(c)
        f = {"n": 1, "rec": bool(pb) or has_role(c, "judge_page"), "repo": bool(pb.get("repo")), "count": bool(pb.get("count")),
             "judges": has_role(c, "judge_page"), "file": bool(pb.get("problems")),
             "nprob": pb.get("count") or 0}
        for key, *_ in HELD_KINDS:
            f[key + "_full"] = pb.get(key) == "full"
            f[key + "_any"] = pb.get(key) in ("full", "partial")
        return f

    prows = []  # (year, series, region, flags)
    for cid, c in contests.items():
        if c.get("status") == "upcoming":
            continue
        sname = series_of[cid]
        prows.append((int(cid.rsplit("-", 1)[1]), sname, SERIES_REGION.get(sname, "Other"), pflags(c)))
    ptot = agg(f for *_x, f in prows)

    PCOV_HDR = ('<tr><th rowspan="2">{}</th><th rowspan="2" class="num">contests</th>'
                '<th rowspan="2" class="num" title="the problem archive has looked at this contest (count or holdings recorded)">recorded</th>'
                '<th rowspan="2" class="num" title="a repo in icpc-problem-archive holds material">repo</th>'
                '<th colspan="4" class="grp">held for every problem</th>'
                '<th colspan="4" class="grp">held for at least one problem</th>'
                '<th rowspan="2" class="num" title="a link to an online judge where the problems can be solved">solve online</th></tr>'
                '<tr>' + "".join(f'<th class="num">{w}</th>' for _k, _l, w in HELD_KINDS) * 2 + "</tr>")

    def pcov_row(label, t):
        return (f'<tr><td class="wrap">{label}</td><td class="num">{t["n"]}</td>'
                + pcell(t["rec"], t["n"]) + pcell(t["repo"], t["n"])
                + "".join(pcell(t[k + "_full"], t["n"]) for k, *_ in HELD_KINDS)
                + "".join(pcell(t[k + "_any"], t["n"]) for k, *_ in HELD_KINDS)
                + pcell(t["judges"], t["n"]) + "</tr>")

    n_problems_listed = sum(len(d.get("problems") or []) for d in SETS.values())
    sets_listed = [sid for sid, d in SETS.items() if d.get("problems")]
    contests_listed = sorted({m["contest"] for sid in sets_listed for m in SETS[sid]["contests"]})
    pidx = ["<h1>Problems</h1>",
            f'<p class="muted">What the <b>ICPC Problem Archive</b> holds, per contest: of {ptot["n"]} contests that ran, '
            f'{ptot["rec"]} ({round(100 * ptot["rec"] / ptot["n"])}%) have their problem holdings recorded, '
            f'{ptot["repo"]} have a repo in the archive, {ptot["statement_full"]} have every statement, '
            f'{ptot["data_full"]} every test-data set, {ptot["solutions_full"]} every solution and '
            f'{ptot["package_full"]} a complete package for every problem; {ptot["nprob"]} problems counted in all. '
            f'{ptot["judges"]} contests link to an online judge where the problems can be solved. '
            f'{len(contests_listed)} contests have a per-problem list ({len(sets_listed)} problem sets, {n_problems_listed} problems; '
            f'{len(PROBLEMS)} distinct problems) — <a href="list.html">all listed problems</a> · '
            f'<a href="../problemsets/index.html">all {len(SETS)} problem sets</a> · <a href="../judges/index.html">online judges</a>.</p>',
            '<p class="small muted">The archive repos are private; this page tracks what exists. Names and counts are '
            'published only for contests that have run (enforced by the validator); problems kept private after a '
            'contest still have their names listed. Model: '
            '<a href="https://github.com/icpc-contest-archive/contests/blob/main/DEFINITIONS.md#problems">DEFINITIONS.md</a>. '
            'jump to: <a href="#region">world region</a> · <a href="#series">series</a> · <a href="#contests">every contest</a></p>',
            HELD_LEGEND]
    pidx.append('<h2 id="region">By world region</h2><div class="tablewrap"><table>' + PCOV_HDR.format("world region"))
    for g in region_names:
        pidx.append(pcov_row(g, agg(f for _y, _s, r, f in prows if r == g)))
    pidx.append(pcov_row("<b>all</b>", ptot))
    pidx.append("</table></div>")
    pidx.append('<h2 id="series">By series</h2><p class="small muted">Only series with at least one recorded contest; '
                'sorted by contests without a record.</p><div class="tablewrap"><table>'
                + PCOV_HDR.format("series").replace("<th rowspan=\"2\">series</th>",
                                                    "<th rowspan=\"2\">series</th><th rowspan=\"2\">region</th><th rowspan=\"2\">years</th>"))
    pser = defaultdict(list)
    for y, sname, _r, f in prows:
        pser[sname].append((y, f))
    srows = []
    for sname, lst in pser.items():
        t = agg(f for _y, f in lst)
        if not t["rec"]:
            continue
        ys = [y for y, _f in lst]
        label = (f'<a href="../series/{esc(sname)}.html">{esc(sname)}</a></td>'
                 f'<td class="small muted">{esc(SERIES_REGION.get(sname, "Other"))}</td>'
                 f'<td class="small">{min(ys)}–{max(ys)}')
        srows.append((t["n"] - t["rec"], t["n"], sname, pcov_row(label, t)))
    for *_x, r in sorted(srows, key=lambda x: (-x[0], -x[1], x[2])):
        pidx.append(r)
    pidx.append("</table></div>")
    pidx.append('<h2 id="contests">Every contest with a record</h2><p class="small muted">Click a column header to sort; '
                'the box filters. <b>#</b> = number of problems; <i>list</i> = a per-problem list exists.</p>'
                '<div class="tablewrap"><table><tr><th>contest</th><th>date</th><th>region</th><th class="num">#</th>'
                '<th>held</th><th>archive repo</th><th>solve online</th><th>per-problem</th><th>notes</th></tr>')
    all_rows = [(cid, c, SERIES_REGION.get(series_of[cid], "Other"), True) for cid, c in contests.items()
                if set_for(c) or has_role(c, "judge_page")]
    all_rows += [(c["id"], c, "non-mainline", False) for c in nm_with]
    for cid, c, region, linked in sorted(all_rows, key=lambda x: x[0]):
        pb = set_for(c)
        pidx.append(
            "<tr><td>" + (link_contest(cid, rel, chip=True) if linked else f'{esc(cid)} <span class="chip" title="outside the mainline hierarchy (registry/non-mainline.yaml)">non-mainline</span>') + "</td>"
            f"<td>{esc(c.get('date', ''))}</td><td class=\"small muted\">{esc(region)}</td>"
            f'<td class="num">{pb.get("count", "")}</td><td>{held_marks(pb)}</td>'
            f'<td>{repo_link(pb)}</td><td class="small">{judge_page_links(c)}</td>'
            + (f'<td>{set_link(pb["id"], rel, "list")}</td>' if pb.get("problems") else "<td></td>")
            + f'<td class="wrap small muted">{esc(pb.get("notes", ""))}</td></tr>')
    pidx.append("</table></div>")
    (out / "problems" / "index.html").write_text(page("Problems", "\n".join(pidx), rel))

    plist = ["<h1>Every listed problem</h1>",
             f'<p class="muted">{n_problems_listed} problems from {len(sets_listed)} problem sets used by {len(contests_listed)} contests '
             f'(<a href="index.html">problem holdings by contest</a> · <a href="../problemsets/index.html">all sets</a>). '
             'One row per problem per set; a set used by several contests lists them all. The box filters by any column — contest, set, letter, name.</p>',
             HAVE_LEGEND,
             '<div class="tablewrap"><table><tr><th>contest</th><th>set</th><th>#</th><th>problem</th><th>held</th><th>solve online</th><th>notes</th></tr>']
    for sid in sorted(sets_listed):
        doc = SETS[sid]
        members = [m["contest"] for m in doc["contests"]]
        with_letters = [m for m in members if set_letters(doc, m)]
        for L, p in set_problems_in_order(doc):
            if len(with_letters) > 1:
                ls = [letter_of(doc, m, p["id"]) for m in with_letters]
                L = " / ".join(x or "?" for x in ls) if len(set(ls)) > 1 else ls[0]
            first = ('<td class="wrap">' + ", ".join(contest_ref(m, rel) for m in members) + "</td>"
                     + f'<td class="small">{set_link(sid, rel)}</td>')
            plist.append(problem_row(L, p, rel, first))
    plist.append("</table></div>")
    (out / "problems" / "list.html").write_text(page("Every listed problem", "\n".join(plist), rel))
    (out / "problems" / "problems.json").write_text(json.dumps(
        {"generated": datetime.date.today().isoformat(), "sets": SETS, "judges": JUDGES}, ensure_ascii=False))
    print(f"  problems: {len(all_rows)} contests with holdings, {len(SETS)} sets, {n_problems_listed} problems listed in {len(sets_listed)} sets")

    # ---- problem sets index, set pages, problem pages, judges ----
    srows = []
    for sid in sorted(SETS):
        doc = SETS[sid]
        members = [m["contest"] for m in doc["contests"]]
        n_list = len(doc.get("problems") or [])
        srows.append(f'<tr><td>{set_link(sid, rel)}</td><td class="wrap small">{esc(doc.get("name", ""))}</td>'
                     f'<td class="wrap">{", ".join(contest_ref(m, rel) for m in members)}</td>'
                     f'<td class="num">{doc.get("count", "")}</td><td class="num">{n_list or ""}</td>'
                     f'<td>{held_marks(doc)}</td><td>{repo_link(doc)}</td>'
                     f'<td class="wrap small muted">{esc(doc.get("notes", ""))}</td></tr>')
    n_shared = sum(1 for d in SETS.values() if len(d["contests"]) > 1)
    sidx = ["<h1>Problem sets</h1>",
            f'<p class="muted">{len(SETS)} problem sets: a set is the object a contest used — one set can serve several contests '
            f'({n_shared} shared sets, e.g. NCPC + UKIEPC). {len(sets_listed)} sets have a per-problem list ({n_problems_listed} rows, '
            f'{len(PROBLEMS)} distinct problems); the rest record only what the ICPC Problem Archive holds. '
            f'See also <a href="../problems/index.html">holdings by contest</a>, <a href="../problems/list.html">every listed problem</a> and '
            f'<a href="../judges/index.html">online judges</a>.</p>',
            HELD_LEGEND,
            '<div class="tablewrap"><table><tr><th>set</th><th>name</th><th>used by</th><th class="num">#</th>'
            '<th class="num" title="problems listed">listed</th><th>held</th><th>archive repo</th><th>notes</th></tr>'
            + "\n".join(srows) + "</table></div>"]
    (out / "problemsets" / "index.html").write_text(page("Problem sets", "\n".join(sidx), rel))
    for sid, doc in SETS.items():
        (out / "problemset" / f"{sid}.html").write_text(problemset_page(sid, doc, rel))
    for pid, ent in PROBLEMS.items():
        (out / "problem" / f"{pid}.html").write_text(problem_page(pid, ent, rel))

    n_prob_links = defaultdict(set)   # judge -> problem ids linking to it
    n_page_links = defaultdict(set)   # judge -> contests with a judge_page source
    for pid, ent in PROBLEMS.items():
        for _s, r in ent["rows"]:
            for j in r.get("judges") or []:
                n_prob_links[j["judge"]].add(pid)
    for c in list(contests.values()) + nm_doc["non_mainline_contests"]:
        for s in by_role(c, "judge_page"):
            n_page_links[s.get("judge") or "judge"].add(c["id"])
    jrows = []
    for jid, j in JUDGES.items():
        st = esc(j.get("status", ""))
        if j.get("closed"):
            st += f' {esc(j["closed"])}'
        jrows.append(f'<tr><td>{esc(jid)}</td><td><a href="{esc(j["url"])}">{esc(j.get("name", jid))}</a></td>'
                     f'<td><span class="chip">{st}</span></td>'
                     f'<td class="num">{len(n_prob_links.get(jid, ()))}</td><td class="num">{len(n_page_links.get(jid, ()))}</td>'
                     f'<td class="small">{"statements" if j.get("statements") else ""}{" · " if j.get("statements") and j.get("submissions") else ""}{"submissions" if j.get("submissions") else ""}</td>'
                     f'<td class="wrap small muted">{esc(j.get("notes", ""))}</td></tr>')
    unknown = sorted(set(n_prob_links) | set(n_page_links)) 
    unknown = [x for x in unknown if x not in JUDGES]
    jidx = ["<h1>Online judges</h1>",
            f'<p class="muted">The {len(JUDGES)} judges in <a href="{REPO_URL}judges.yaml">judges.yaml</a>, the registry every judge link '
            'refers to: per-problem links (<i>problems</i>) and contest-level judge pages (<i>contest pages</i>, sources with role judge_page). '
            'A closed judge\'s pages survive only in Wayback snapshots taken before the closing date.</p>',
            '<div class="tablewrap"><table><tr><th>id</th><th>judge</th><th>status</th><th class="num">problems</th>'
            '<th class="num">contest pages</th><th>offers</th><th>notes</th></tr>' + "\n".join(jrows) + "</table></div>"]
    if unknown:
        jidx.append('<p class="small muted">Judge ids used but not in the registry: ' + ", ".join(esc(x) for x in unknown) + "</p>")
    (out / "judges" / "index.html").write_text(page("Online judges", "\n".join(jidx), rel))
    print(f"  problem sets: {len(SETS)} set pages, {len(PROBLEMS)} problem pages, {len(JUDGES)} judges")

    # ---- machine-readable dump ----
    dump = {}
    for sid, doc in series_docs.items():
        d2 = dict(doc)
        d2["series"] = {**doc["series"], "region": SERIES_REGION.get(sid, "Other")}
        dump[sid] = d2
    (out / "catalogue.json").write_text(json.dumps(
        {"generated": datetime.date.today().isoformat(), "series": dump},
        ensure_ascii=False))

    # ---- search + landing ----
    def hosts_of(c):
        """Hosts of the website and result sources (what people search by)."""
        hs = set()
        for s in sources(c):
            if "web" in s["roles"] or any(r in s["roles"] for r in RESULT_KINDS):
                hs.add(re.sub(r"^https?://(www\.)?", "", s["url"]).split("/")[0])
        return sorted(hs)

    search = [{"id": cid, "name": c.get("name"), "date": c.get("date"), "series": series_of[cid],
               "cms": [str(i) for i in (c.get("cms_ids") or [])], "hosts": hosts_of(c),
               "region": SERIES_REGION.get(series_of[cid], ""),
               "problems": [p["name"] for p in set_for(c).get("problems") or []] or None}
              for cid, c in sorted(contests.items())]
    (out / "search.json").write_text(json.dumps(search, ensure_ascii=False))
    ran = sum(1 for c in contests.values() if c.get("status") != "upcoming")
    landing = f"""<h1>ICPC contest archive</h1>
<p>A catalogue of the mainline ICPC contest hierarchy through history:
<b>{ran}</b> contests that ran (plus {len(contests) - ran} upcoming) across
<b>{len(series_docs)}</b> series, with links to results — live, on the Wayback Machine,
and in this project's own archive.</p>
<p><input id="q" placeholder="search contests… (id, name, series, host, CMS id, region, problem name)"
   autocomplete="off"></p>
<div class="tablewrap"><table id="hits"></table></div>
<h2>Start somewhere</h2>
<p>{link_contest('wf-2025', '')} · <a href="series/wf.html">World Finals series</a> ·
<a href="series/index.html">all series</a> · <a href="seasons.html">seasons</a> ·
<a href="coverage.html">collection coverage</a> · <a href="problems/index.html">problems</a> · <a href="problemsets/index.html">problem sets</a> · <a href="resources/index.html">all resources</a> ·
<a href="wanted.html">most wanted</a> · <a href="catalogue.json">catalogue.json</a> ·
<a href="local.html">local archive</a></p>
<p class="small muted">Data: <a href="https://github.com/icpc-contest-archive/contests">
icpc-contest-archive/contests</a>. Corrections welcome.</p>
<script>const REL='';{SEARCH_JS}</script>"""
    (out / "index.html").write_text(page("ICPC contest archive", landing, ""))

    n_sites = len(website_of)
    n_raw = len(archived_by_contest)
    local = f"""<h1>Local archive</h1>
<p>Besides the result pages published on the replay site, this project holds a much larger
private archive: raw captures of every result page and full crawls of
<b>{n_sites}</b> contest websites ({n_raw} contests with raw captures in all). That is far too
big for GitHub Pages, so it is not published yet.</p>
<p>Links marked <a class="local" href="{LOCAL_BASE}/" title="{LOCAL_TITLE}">like this</a>
point at a small server on <b>your own machine</b> (<code>{LOCAL_BASE or "this host"}</code>).
They work only if you have the <code>archive</code> repository checked out next to
<code>contests</code> and the server running; for everyone else they give
"unable to connect". Nothing is probed in the background — a link is just a link.</p>
<h2>Running it</h2>
<pre><code># in your checkout of the contests repo (archive checked out alongside it)
python3 tools/index_websites.py     # after new site crawls
python3 tools/serve.py              # rebuilds the site with local links, serves on 127.0.0.1:8123</code></pre>
<p>Then browse the catalogue at <code>http://127.0.0.1:8123/</code> — the same pages as the
public site, with every local link live. The public site's local links point at the same
address, so they work in any browser while the server is up.</p>
<h2>What the links are</h2>
<ul>
<li><b>archived site</b> (on a contest's <i>web</i> line): the crawled website, played back
page by page from the capture with in-site links kept inside the capture. Links to pages that
were not captured go to the Wayback Machine (for crawls taken from a snapshot) or to the live
site. The <i>wayback</i> link next to it is pinned to the exact snapshot the crawl used.</li>
<li><b>raw</b> (on a result row): the captured file exactly as fetched, no banner, no rewriting.</li>
<li><b>raw files</b>: the contest's folder in the archive repository — every capture as stored
(hashed filenames, manifests), results and website alike; for inspection, not for reading.</li>
</ul>
<h2>Resources</h2>
<p>A <b>resource</b> is a URL at a time, shown as <code>url (time)</code> when the content
meant is a dated snapshot rather than whatever the address serves today; a bare URL is a
<b>locator</b>. Archive captures are resources; the catalogue holds locators and points at the
captures held of them. Full definitions in
<a href="https://github.com/icpc-contest-archive/contests/blob/main/DEFINITIONS.md#resources">DEFINITIONS.md</a>.</p>
<p class="small muted">When the archive gets a public home the only change is the host these
links point at (<code>LOCAL_ARCHIVE_BASE</code> in <code>tools/build_site.py</code>).</p>"""
    (out / "local.html").write_text(page("Local archive", local, ""))

    # ---- locator + resource pages ----
    if RES.locs:
        nres = site_resources.build(out, RES, page, link_contest, local_link, REPLAY_BASE, contests)
        print(f"  {nres} locator/resource pages")

    n = len(list(out.rglob("*.html")))
    print(f"site: {n} pages -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "site"))
    build(Path(ap.parse_args().out))
