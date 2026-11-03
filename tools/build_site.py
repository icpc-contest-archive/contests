#!/usr/bin/env python3
"""Build the static catalogue site into site/ (relative links only, mountable anywhere).

Objects and their pages (DEFINITIONS.md; 2026-11-02 redesign):
  season/<end-year>.html      hierarchy tree with the WF at the root, date window, statistics
  series/<id>.html            header, lineage, the editions
  contest/<id>.html           one contest: season, date, sites, hierarchy, CMS ids, sources by role, problems
  source/<id>/index.html      one source (a catalogued address): roles, health, snapshot timeline with captures
  problemset/<set-id>.html    one problem set; problem/<pid>.html one problem
  judge/<id>.html             one online judge; location/<id>.html one node of the location tree
Each object has an index (…/index.html) with client-side filters and sorting. Old addresses
(locator/, problemsets/index.html, judges/, seasons.html, resources/, urls/, local.html,
problems/list.html) are kept as redirect stubs.

Optional inputs, used when present:
  data/archive-index.json  — captures held by the (private) archive repo
  data/replay-index.json   — pages baked into the public replay shard(s)
  data/website-index.json  — archived contest websites (tools/index_websites.py)
  data/resources.json      — the source/snapshot/capture graph (tools/build_resources.py)

"local" links point at the local archive server (tools/serve.py, 127.0.0.1:8123)
and only work while it is running; LOCAL_ARCHIVE_BASE overrides the host (serve.py
sets it to "" so the links are same-origin when browsing locally).

  python3 tools/build_site.py [--out site] [--check-links]
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
from resources import fmt_time, label as res_label, norm_key, unwrap, wayback_link  # noqa: E402
from catalogue import (RANK, RESULT_ROLES, also_at, archived, best_result, by_role, has_role,  # noqa: E402
                       load_judges, load_locations, load_non_mainline, load_sets, location_chain,
                       set_kind_count, set_letters, set_of, sources)
import site_resources  # noqa: E402

# the four published result tiers (RESULT_ROLES minus the CMS's own icpc_standings)
RESULT_KINDS = tuple(r for r in RESULT_ROLES if r != "icpc_standings")

RES = site_resources.Resources(ROOT)  # source/snapshot lookups (data/resources.json)
lid = site_resources.lid
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
VIA_HELP = {
    "wayback": "fetched from the Wayback Machine; time = the snapshot Wayback served",
    "live": "fetched from the origin host by this project; time = our fetch time",
    "api-dump": "rendered from the ICPC standings API dump; time = the dump time",
    "direct": "stored directly (sheet-era import); time = the import date",
    "mirror": "the same content served from a mirror address",
}
WB_HELP = {"ok": "a snapshot is served", "none": "no snapshot exists",
           "excluded": "the Wayback Machine refuses to serve this URL (domain excluded by policy) — snapshots may exist but are blocked"}
OUT_HELP = {"content": "something was served", "absent": "nothing there",
            "junk": "something was served, but it is not this resource (error page, app shell, hub page, login wall…)",
            "blocked": "could not look (access refused)", "undetermined": "answered, but nothing to judge by"}

CHAMPIONSHIPS: set = set()   # series with tier: championship (filled by derive_regions)
REGION_NAMES = ["North America", "Latin America", "Europe", "Northern Eurasia", "Africa & Arab",
                "Asia West", "Asia Pacific", "Asia East"]
REGION_GROUPS: dict = {"World Finals & championships": []} | {r: [] for r in REGION_NAMES}
SERIES_REGION: dict = {}
SERIES_TIER: dict = {}


def derive_regions(series_docs: dict, contests: dict) -> None:
    """Fill SERIES_REGION / SERIES_TIER / REGION_GROUPS / CHAMPIONSHIPS from the series headers."""
    for sid, doc in series_docs.items():
        h = doc["series"]
        SERIES_TIER[sid] = h.get("tier") or ("world-finals" if sid == "wf" else "")
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
h3 { font-size:1rem; margin:1.1rem 0 .4rem; }
table { border-collapse:collapse; width:100%; } .tablewrap { overflow-x:auto; }
th,td { text-align:left; padding:.28rem .55rem; border-bottom:1px solid var(--line);
  vertical-align:top; white-space:nowrap; }
td.wrap, th.wrap { white-space:normal; word-break:break-word; }
td.url { white-space:normal; word-break:break-all; }
th.grp { text-align:center; font-weight:500; color:var(--muted); border-bottom:none; }
dl.fields dd { word-break:break-word; }
.muted { color:var(--muted); } .small { font-size:.85em; }
th.sorted { text-decoration:underline; }
input.tfilter { width:100%; max-width:22rem; padding:.3rem .5rem; margin:.3rem 0; font-size:.9rem;
  border:1px solid var(--line); border-radius:.4rem; background:var(--bg); color:var(--fg); }
.fbar { display:flex; flex-wrap:wrap; gap:.4rem .6rem; align-items:center; margin:.4rem 0 .6rem; }
.fbar input.tfilter { max-width:16rem; margin:0; }
.fbar select { padding:.3rem .4rem; font-size:.85rem; border:1px solid var(--line); border-radius:.4rem;
  background:var(--bg); color:var(--fg); max-width:16rem; }
.fbar .fcount { margin-left:auto; }
.state { margin:.2rem 0 .8rem; }
.chip { background:var(--chip); border-radius:.6em; padding:.05em .55em; font-size:.85em;
  display:inline-block; margin:0 .15em .15em 0; }
nav.top { border-bottom:1px solid var(--line); }
nav.top div { margin:0; padding:.55rem 1.6rem; }
nav.top a { margin-right:1.1rem; } nav.top a.brand { font-weight:600; }
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
.loctree ul { list-style:none; padding-left:1.1rem; margin:0; } .loctree > ul { padding-left:0; }
.loctree li { padding:.04rem 0; } .loctree summary { cursor:pointer; }
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
.srcrow { margin:.25rem 0 .35rem; padding-left:.2rem; }
.srcrow .sub { margin-left:1.6rem; color:var(--muted); }
.snap { border-left:3px solid var(--line); padding:.2rem 0 .3rem .9rem; margin:.7rem 0; }
.snap:target { border-left-color:var(--accent); }
.snap h3 { margin:.2rem 0 .3rem; }
.crumb a { white-space:nowrap; }
.stats { display:flex; flex-wrap:wrap; gap:.6rem 1.6rem; margin:.4rem 0 .8rem; }
.stats div b { display:block; font-size:1.3rem; }
code { font-size:.9em; }
"""

TABLE_JS = r"""
(function(){
  const num = s => { const t = s.replace(/[%,\s]/g,''); return t !== '' && !isNaN(t) ? parseFloat(t) : null; };
  const cellv = c => c ? (c.dataset.v !== undefined ? c.dataset.v : c.textContent).trim() : '';
  document.querySelectorAll('table').forEach(tbl => {
    if (tbl.classList.contains('grid') || tbl.classList.contains('nosort') || tbl.id === 'hits') return;
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
        const key = r => cellv(r.children[idx]);
        const allNum = rows.every(r => key(r) === '' || num(key(r)) !== null);
        rows.sort((a, b) => { const x = key(a), y = key(b);
          if (allNum) { const nx = num(x), ny = num(y); return (nx === null) - (ny === null) || (nx ?? 0) - (ny ?? 0); }
          return x.localeCompare(y, undefined, {numeric: true}); });
        if (!asc) rows.reverse(); asc = !asc;
        ths.forEach(t => t.classList.remove('sorted')); th.classList.add('sorted');
        rows.forEach(r => r.parentNode.appendChild(r));
      });
    });
    // filter bar: a text box, plus one select per header marked data-f (values = that column's
    // cells; data-v overrides the text, data-vs is a space-separated list of values)
    const want = tbl.classList.contains('flt') || rows.length >= 30;
    if (!want) return;
    const bar = document.createElement('div'); bar.className = 'fbar';
    const box = document.createElement('input');
    box.placeholder = 'filter ' + rows.length + ' rows…'; box.className = 'tfilter'; box.autocomplete = 'off';
    bar.appendChild(box);
    const sels = [];
    const vals = c => c ? (c.dataset.vs !== undefined ? c.dataset.vs.split(' ').filter(Boolean) : [cellv(c)]) : [''];
    ths.forEach((th, i) => {
      if (!th.hasAttribute('data-f')) return;
      const cnt = new Map();
      rows.forEach(r => { for (const v of vals(r.children[i])) cnt.set(v, (cnt.get(v) || 0) + 1); });
      if (cnt.size < 2) return;
      const sel = document.createElement('select'); sel.dataset.col = i;
      const o = document.createElement('option'); o.value = ''; o.textContent = th.textContent.trim() + ': all'; sel.appendChild(o);
      Array.from(cnt.keys()).sort((a, b) => a.localeCompare(b, undefined, {numeric: true})).forEach(v => {
        const o = document.createElement('option'); o.value = v; o.textContent = (v || '—') + ' (' + cnt.get(v) + ')'; sel.appendChild(o); });
      bar.appendChild(sel); sels.push(sel);
    });
    const count = document.createElement('span'); count.className = 'small muted fcount'; bar.appendChild(count);
    const wrap = tbl.closest('.tablewrap') || tbl;
    wrap.parentNode.insertBefore(bar, wrap);
    const apply = () => {
      const q = box.value.toLowerCase(); let n = 0;
      rows.forEach(r => {
        let ok = !q || r.textContent.toLowerCase().includes(q);
        if (ok) for (const s of sels) { if (!s.value) continue; if (!vals(r.children[+s.dataset.col]).includes(s.value)) { ok = false; break; } }
        r.style.display = ok ? '' : 'none'; if (ok) n++;
      });
      count.textContent = n === rows.length ? rows.length + ' rows' : n + ' of ' + rows.length + ' rows';
      const h = sels.filter(s => s.value).map(s => s.dataset.col + '=' + encodeURIComponent(s.value)).join('&');
      if (h || location.hash.startsWith('#f:')) history.replaceState(null, '', h ? '#f:' + h : location.pathname);
    };
    if (location.hash.startsWith('#f:')) location.hash.slice(3).split('&').forEach(kv => {
      const [c, v] = kv.split('='); const s = sels.find(s => s.dataset.col === c); if (s) s.value = decodeURIComponent(v || ''); });
    box.addEventListener('input', apply); sels.forEach(s => s.addEventListener('change', apply)); apply();
  });
})();
"""

SEARCH_JS = """
const idx = fetch(REL + 'search.json').then(r => r.json());
const q = document.getElementById('q'), out = document.getElementById('hits');
const HREF = {c: 'contest/', r: 'series/', s: 'problemset/', p: 'problem/', l: 'location/', j: 'judge/'};
const KIND = {c: 'contest', r: 'series', s: 'problem set', p: 'problem', l: 'location', j: 'judge'};
q.addEventListener('input', async () => {
  const term = q.value.trim().toLowerCase();
  if (term.length < 2) { out.innerHTML = ''; return; }
  const data = await idx;
  const hits = data.filter(c => c.id.includes(term) ||
    (c.name && c.name.toLowerCase().includes(term)) || (c.series || '').includes(term) ||
    (c.cms || []).some(x => x === term) || (c.hosts || []).some(h => h.includes(term)) ||
    (c.region && c.region.toLowerCase().includes(term)) ||
    (c.aliases || []).some(a => a.toLowerCase().includes(term)) ||
    (c.problems || []).some(p => p.toLowerCase().includes(term))).slice(0, 80);
  out.innerHTML = hits.map(c =>
    `<tr><td class="small muted">${KIND[c.t]}</td><td><a href="${REL}${HREF[c.t]}${c.id}.html">${c.id}</a></td>` +
    `<td class="wrap">${c.name || ''}</td><td>${c.date || ''}</td>` +
    `<td class="small muted wrap">${(c.cms || []).join(', ')}${(c.hosts || []).slice(0, 3).join(' ')}${c.extra || ''}</td></tr>`).join('');
});
"""

NAV = (("season/index.html", "seasons"), ("series/index.html", "series"), ("contest/index.html", "contests"),
       ("problemset/index.html", "problem sets"), ("problem/index.html", "problems"), ("source/index.html", "sources"),
       ("judge/index.html", "judges"), ("location/index.html", "locations"), ("coverage.html", "coverage"),
       ("about.html", "about"))


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def refs(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def page(title: str, body: str, rel: str) -> str:
    nav = " ".join(f'<a href="{rel}{h}">{t}</a>' for h, t in NAV)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body>
<nav class="top"><div><a class="brand" href="{rel}index.html">ICPC contest archive</a> {nav}</div></nav>
<main>{body}</main>
<script>{TABLE_JS}</script></body></html>"""


def stub(path: Path, target: str) -> None:
    """A tiny meta-refresh page at an old address so existing links keep working."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={esc(target)}">'
                    f'<title>moved</title><p>Moved to <a href="{esc(target)}">{esc(target)}</a>.</p>')


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


CONTESTS: dict = {}  # filled by load(); lets every link carry the same tooltip
SERIES_OF: dict = {}


def link_contest(cid: str, rel: str, chip: bool = False) -> str:
    """The one way a contest is rendered as a link: id, with name · date on hover and an
    'upcoming' chip where the context lists contests that ran (chip=True)."""
    c = CONTESTS.get(cid) or {}
    tip = " · ".join(x for x in (c.get("name"), c.get("date")) if x)
    out = f'<a href="{rel}contest/{esc(cid)}.html"' + (f' title="{esc(tip)}"' if tip else "") + f'>{esc(cid)}</a>'
    if chip and c.get("status") == "upcoming":
        out += ' <span class="chip" title="has not run yet">upcoming</span>'
    return out


def link_series(sid: str, rel: str) -> str:
    return f'<a href="{rel}series/{esc(sid)}.html">{esc(sid)}</a>'


def link_season(season, rel: str, label: str | None = None) -> str:
    if not season:
        return ""
    return f'<a href="{rel}season/{season}.html">{esc(label or f"{season - 1}–{season}")}</a>'


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
    SERIES_OF.clear()
    SERIES_OF.update(series_of)
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
    """The source's health, one way everywhere: the source's url_state if it has one,
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


# ---- source pages: where a `url (time)` links ----
def src_href(url: str, rel: str, ts: str | None = None) -> str | None:
    """The source page of an address (source/<id>/index.html), with a #s-<ts> anchor on the
    snapshot when `ts` (or a prefix of it — a partial as_of) names one; None when unknown."""
    k = lid(url)
    L = RES.locs.get(k)
    if not L:
        return None
    h = f"{rel}source/{k}/index.html"
    if ts:
        ts = str(ts)
        if ts in L["resources"]:
            return h + f"#s-{ts}"
        for t in L["resources"]:
            if t.startswith(ts) or ts.startswith(t):
                return h + f"#s-{t}"
    return h


def src_link(url: str, ts, rel: str, text: str, title: str = "source page") -> str:
    """`text` wrapped in a link to the source page (snapshot anchor when known), else plain."""
    href = src_href(url, rel, ts)
    return f'<a href="{href}" title="{title}">{text}</a>' if href else text


TIER_LABEL = {"scoreboard": "scoreboard", "frozen_scoreboard": "frozen scoreboard", "standings": "standings",
              "rankings": "rankings", "icpc": "ICPC standings only", "none": "no result"}
ROLE_LABEL = {"icpc_standings": "ICPC standings", "judge_page": "judge page", "frozen_scoreboard": "frozen scoreboard",
              "problemset": "problem set", "web": "website"}


def role_label(r: str) -> str:
    return ROLE_LABEL.get(r, r.replace("_", " "))


def role_chip(r: str) -> str:
    return f'<span class="chip">{esc(role_label(r))}</span>'


def lost_locators(c) -> list:
    """Result/web sources of this contest that are dead live AND have no Wayback snapshot:
    whatever we hold is the only copy; if we hold nothing, the material is lost."""
    out = []
    urls = [s["url"] for s in sources(c) if "web" in s["roles"] or any(r in s["roles"] for r in RESULT_KINDS)]
    for u in urls:
        L = RES.locs.get(lid(u))
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


def web_cell(c, cid: str, rel: str = "../") -> str:
    """Website links: host as label (full url in the tooltip), pinned wayback, the source
    page, and the local archived-site link when a crawl is held."""
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
        if src_href(w, rel):
            bit += f' <a class="small" href="{src_href(w, rel)}" title="source page">src</a>'
        if site and n == 0:
            bit += " " + local_link(f"site/{cid}/", "archived")
        parts.append(bit)
    return " · ".join(parts)


def cap_time(cap: dict):
    """The snapshot time of a capture: the served Wayback snapshot for wayback-sourced
    captures, else our own fetch time."""
    if not cap:
        return None
    ts = cap.get("wayback_timestamp") or unwrap(cap.get("wayback_url") or "")[1]
    if ts:
        return ts
    f = cap.get("fetched") or ""
    return re.sub(r"[^0-9]", "", f.split("+")[0].replace("Z", ""))[:14] or None


# ---- locations (DEFINITIONS.md, Locations) ----
LOC: dict = {}                      # node id -> node
LOC_KIDS: dict = defaultdict(list)  # node id -> child ids
LOC_DIRECT: dict = defaultdict(list)  # node id -> [(contest id, site)] for sites placed exactly here
LOC_SUB: dict = {}                  # node id -> set of contest ids anywhere in the subtree
TYPE_ORDER = {"country": 0, "region": 1, "city": 2, "institution": 3}


def load_locations_tree(contests: dict) -> None:
    LOC.clear()
    LOC.update(load_locations())
    LOC_KIDS.clear()
    LOC_DIRECT.clear()
    LOC_SUB.clear()
    for nid, n in LOC.items():
        if n.get("parent"):
            LOC_KIDS[n["parent"]].append(nid)
    for k in LOC_KIDS.values():
        k.sort(key=lambda x: LOC[x]["name"])
    for cid, c in contests.items():
        for s in c.get("sites") or []:
            if s.get("location") in LOC:
                LOC_DIRECT[s["location"]].append((cid, s))

    def sub(nid):
        acc = {cid for cid, _s in LOC_DIRECT.get(nid, [])}
        for k in LOC_KIDS.get(nid, []):
            acc |= sub(k)
        LOC_SUB[nid] = acc
        return acc
    for nid, n in LOC.items():
        if not n.get("parent"):
            sub(nid)


def loc_link(nid: str, rel: str, label: str | None = None) -> str:
    n = LOC.get(nid)
    if not n:
        return esc(label or nid)
    return f'<a href="{rel}location/{esc(nid)}.html" title="{esc(n["type"])}">{esc(label or n["name"])}</a>'


def loc_crumb(nid: str, rel: str, from_node: bool = True) -> str:
    """institution › city › region › country, each linked (most specific first)."""
    chain = location_chain(LOC, nid)
    if not from_node:
        chain = chain[1:]
    return '<span class="crumb">' + " › ".join(loc_link(n["id"], rel) for n in chain) + "</span>"


def site_line(s: dict, rel: str) -> str:
    """One site of a contest: breadcrumb (or the free label), the site's own name/date, type."""
    nid = s.get("location")
    muted = s.get("type") in ("administrative", "online")
    parts = []
    if nid in LOC:
        parts.append(loc_crumb(nid, rel))
        if s.get("name") and s["name"] != LOC[nid]["name"] and s["name"] not in (LOC[nid].get("aliases") or []):
            parts.append(f'<span class="muted">— {esc(s["name"])}</span>')
    elif s.get("name"):
        parts.append(f'{esc(s["name"])} <span class="chip" title="this site label could not be placed in the location tree">unplaced</span>')
    else:
        parts.append('<span class="muted">—</span>')
    if s.get("date"):
        parts.append(f'<span class="small muted">{esc(s["date"])}</span>')
    if s.get("type"):
        title = "the CMS&#39;s non-physical bookkeeping site" if s["type"] == "administrative" else "teams competing remotely"
        parts.append(f'<span class="chip" title="{title}">{esc(s["type"])}</span>')
    out = " ".join(parts)
    return f'<span class="muted">{out}</span>' if muted else out


def physical_sites(c: dict) -> list[dict]:
    return [s for s in c.get("sites") or [] if s.get("type") not in ("administrative", "online") and s.get("location") in LOC]


def city_country(nid: str) -> tuple[str, str]:
    """(city-or-lower-level name, country name) for a node."""
    chain = location_chain(LOC, nid)
    country = next((n["name"] for n in chain if n["type"] == "country"), "")
    city = next((n["name"] for n in chain if n["type"] == "city"), None)
    if city is None:
        city = next((n["name"] for n in chain if n["type"] in ("region", "institution")), "")
    return city, country


def country_of(c: dict) -> str | None:
    """The country node id of the first physical site (None when unknown)."""
    for s in physical_sites(c):
        for n in location_chain(LOC, s["location"]):
            if n["type"] == "country":
                return n["id"]
    return None


def place_cell(c: dict, rel: str, maxn: int = 3) -> str:
    """Compact where-held cell: `City, Country` from the sites (distinct, linked), else the
    free-text location."""
    seen, out = [], []
    for s in physical_sites(c):
        city, country = city_country(s["location"])
        key = (city, country)
        if key in seen:
            continue
        seen.append(key)
        out.append(f'<a href="{rel}location/{esc(s["location"])}.html">{esc(city)}</a>' + (f", {esc(country)}" if country and country != city else ""))
    if out:
        more = f' <span class="small muted">+{len(out) - maxn} more</span>' if len(out) > maxn else ""
        return "; ".join(out[:maxn]) + more
    online = [s for s in c.get("sites") or [] if s.get("type") == "online" and s.get("location") in LOC]
    if online:
        city, country = city_country(online[0]["location"])
        return (f'<span class="muted">online</span> · <a href="{rel}location/{esc(online[0]["location"])}.html">{esc(city)}</a>'
                + (f", {esc(country)}" if country and country != city else "") + (f' <span class="small muted">+{len(online) - 1} more</span>' if len(online) > 1 else ""))
    if any(s.get("type") == "online" for s in c.get("sites") or []):
        return '<span class="muted">online</span>'
    if c.get("location"):
        t = c["location"]
        return f'<span class="muted" title="{esc(t)}">{esc(t if len(t) <= 50 else t[:49] + "…")}</span>'
    return ""


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
    if any(c["id"] == cid for c in NM):
        return f'{esc(cid)} <span class="chip" title="outside the mainline hierarchy (registry/non-mainline.yaml)">non-mainline</span>'
    return f'{esc(cid)} <span class="chip" title="this id is not in the catalogue (stale pointer in an index)">not catalogued</span>'


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
        if src_href(w, rel):
            parts.append(src_link(w, as_of, rel, "source"))
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
    b.append('<p class="small muted">problem set — <a href="../problemset/index.html">all sets</a> · '
             '<a href="../problems/index.html">holdings by contest</a></p>')
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
         '<p class="small muted">problem — <a href="../problem/index.html">every listed problem</a> · '
         '<a href="../problemset/index.html">all sets</a></p>',
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


# ---- contest pages ----
REPLAY_BY_CONTEST: dict = defaultdict(list)
ARCHIVED_BY_CONTEST: dict = defaultdict(list)
CHILDREN: dict = {}
PREV: dict = {}
SUBSETS: dict = {}


def capture_links(cid: str, e: dict, matched: set) -> list[str]:
    """Links for every capture of a source: `archived (time)` on the public replay, `raw` on
    the local server; the preferred (held, no caveat) capture first. Falls back to the
    replay index when the catalogue has no `archived` pointer."""
    parts = []
    paths = archived(e)
    first = held_path(e)
    if first:
        paths = [first] + [p for p in paths if p != first]
    if paths:
        for n, pth in enumerate(paths):
            cp = capture_info.get(pth)
            when = fmt_time(cap_time(cp)) if cp else ""
            caveat = (cp or {}).get("content_caveat")
            baked = "a/" + pth
            matched.add(baked)
            lab = "archived" if n == 0 else f"archived {n + 1}"
            title = "our capture of this snapshot" + (f" — caveat: {caveat}" if caveat else "")
            parts.append(f'<a href="{REPLAY_BASE}/{esc(baked)}" title="{esc(title)}">'
                         f'{lab}{" (" + when + ")" if when else ""}</a>'
                         + (' <span class="muted small">(caveat)</span>' if caveat else ""))
            parts.append(local_link("archive/" + pth, "raw"))
    else:
        baked = REPLAY_LOOKUP.get((cid, norm_key(e["url"])))
        if baked:
            matched.add(baked)
            parts.append(f'<a href="{REPLAY_BASE}/{esc(baked)}" title="our capture of this snapshot">archived</a>')
    return parts


def source_row(cid: str, e: dict, rel: str, matched: set, badges: bool = True) -> str:
    """One source of a contest: role badges, live · wayback (pinned to as_of) · every
    capture · raw, the `url (time)` label linked to the source page, health, mirrors."""
    url, as_of = e["url"], e.get("as_of")
    cap = capture_info.get(held_path(e) or "")
    parts = [f'<a href="{esc(url)}">live</a>', f'<a href="{esc(wayback_link(url, as_of))}">wayback</a>']
    parts += capture_links(cid, e, matched)
    chips = "".join(role_chip(r) for r in sorted(e["roles"], key=lambda r: RANK[r])) if badges else ""
    if e.get("judge"):
        chips += f'<span class="chip">{esc(judge_name(e["judge"]))}</span>' + judge_closed_chip(e["judge"])
    line = (f'<div class="srcrow small">{chips} ' + " · ".join(parts)
            + f' <span class="muted">{src_link(url, as_of or cap_time(cap), rel, esc(res_label(url, as_of, 110)))}</span>'
            + health_chip(url, e)
            + (f' <span class="muted">— {esc(e["note"])}</span>' if e.get("note") else ""))
    for m in also_at(e):
        mu, mts = m["url"], m.get("as_of")
        line += (f'<div class="sub">also at {src_link(mu, mts, rel, esc(res_label(mu, mts, 100)))} · '
                 f'<a href="{esc(mu)}">live</a> · <a href="{esc(wayback_link(mu, mts))}">wayback</a>{health_chip(mu)}'
                 + (f' — {esc(m["note"])}' if m.get("note") else "") + "</div>")
    return line + "</div>"


def website_block(cid: str, c: dict, rel: str, matched: set) -> list[str]:
    b = []
    site = website_of.get(cid)
    webs = by_role(c, "web")
    if not webs and web_state(c) != "none":
        return b
    b.append('<h2 id="website">Website</h2>')
    if web_state(c) == "none":
        b.append('<p class="muted small">confirmed none (see notes)</p>')
    for n_w, ws in enumerate(webs):
        b.append(source_row(cid, ws, rel, matched, badges=len(ws["roles"]) > 1))
        if site and n_w == 0:
            npages = site.get("html_pages") or site.get("pages") or 0
            wb_ts = site.get("wayback_timestamp")
            b.append('<div class="srcrow small"><span class="chip">archived site</span> '
                     + local_link(f"site/{cid}/", "play back") + f' · <a href="{esc(wayback_link(ws["url"], wb_ts or ws.get("as_of")))}">wayback</a>'
                     + f' <span class="muted">{npages} pages, ' + ("snapshot " if site.get("mode") == "wayback" else "live crawl ")
                     + esc(fmt_time(wb_ts) if wb_ts else str(site.get("fetched", ""))[:10]) + "</span></div>")
    return b


def results_block(cid: str, c: dict, rel: str, matched: set) -> list[str]:
    """Every result source, best tier first, one row per source (role badges when a source
    serves several tiers); then replay pages the catalogue does not point at."""
    rows = []
    seen = set()
    for key in RESULT_ROLES:
        for e in by_role(c, key):
            if id(e) in seen:
                continue
            seen.add(id(e))
            if "web" in e["roles"]:  # shown under Website with its role badges; say so here
                rows.append(f'<div class="srcrow small">{"".join(role_chip(r) for r in e["roles"] if r in RESULT_ROLES)} '
                            f'<span class="muted">the website above (<a href="#website">{esc(res_label(e["url"], e.get("as_of"), 80))}</a>)</span></div>')
                continue
            rows.append(source_row(cid, e, rel, matched))
    extra = [e for e in REPLAY_BY_CONTEST.get(cid, []) if e["path"] not in matched and e.get("artifact") != "problemset"]
    for e in extra:
        u = e.get("url") or ""
        rows.append(f'<div class="srcrow small"><span class="chip">{esc(e["artifact"].replace("_", " "))}</span> '
                    + (f'<a href="{esc(u)}">live</a> · <a href="{esc(wayback_link(u))}">wayback</a> · ' if u else "")
                    + f'<a href="{REPLAY_BASE}/{esc(e["path"])}">archived</a> '
                    + (f'<span class="muted">{src_link(u, None, rel, esc(u[:100]))}</span>{health_chip(u)}' if u else "")
                    + "</div>")
        matched.add(e["path"])
    if not rows:
        return []
    return ["<h2>Results</h2>",
            '<p class="small muted">Best tier first. <i>live</i> = the address as is · <i>wayback</i> = pinned to the '
            'time meant when known · <i>archived (time)</i> = our capture, on the public replay · <i>raw</i> = the capture file untouched.</p>'] + rows


def other_sources_block(cid: str, c: dict, rel: str, matched: set) -> list[str]:
    others = [s for s in sources(c) if not (set(s["roles"]) & (set(RESULT_ROLES) | {"web", "problemset", "judge_page"}))]
    if not others:
        return []
    return ["<h2>Other sources</h2>"] + [source_row(cid, s, rel, matched) for s in others]


def contest_page(cid: str, c: dict, rel: str) -> str:
    sid = SERIES_OF[cid]
    b = [f"<h1>{esc(cid)}</h1>"]
    if c.get("name"):
        b.append(f'<p class="muted">{esc(c["name"])}</p>')
    b.append(state_line(c, cid))
    d = ['<dl class="fields">']
    if c.get("status") == "upcoming":
        d.append("<dt>status</dt><dd>upcoming</dd>")
    d.append(f"<dt>series</dt><dd>{link_series(sid, rel)}"
             + (f' <span class="muted">{esc(SERIES_TIER.get(sid, ""))}' + (f' · {esc(SERIES_REGION[sid])}' if SERIES_REGION.get(sid) else "") + "</span>" if SERIES_TIER.get(sid) else "")
             + "</dd>")
    if c.get("season"):
        d.append(f"<dt>season</dt><dd>{link_season(c['season'], rel)}"
                 ' <span class="small muted">(the year in the id is the season label, not the date)</span></dd>')
    if c.get("date"):
        d.append(f"<dt>date</dt><dd>{esc(c['date'])}</dd>")
    sites = c.get("sites") or []
    if sites:
        d.append("<dt>sites</dt><dd>" + "<br>".join(site_line(s, rel) for s in sites)
                 + (f'<br><span class="small muted">as recorded: {esc(c["location"])}</span>' if c.get("location") and not physical_sites(c) else "") + "</dd>")
    elif c.get("location"):
        d.append(f'<dt>location</dt><dd>{esc(c["location"])} <span class="small muted">(free text; not yet placed in the location tree)</span></dd>')
    for label, ids in (
        ("advances to", refs(c.get("parent"))),
        ("feeders", sorted(CHILDREN.get(cid, []))),
        ("next edition", refs(c.get("next"))),
        ("previous edition", sorted(PREV.get(cid, []))),
        ("subset of", [c["subset_of"]] if c.get("subset_of") else []),
        ("regional views", sorted(SUBSETS.get(cid, []))),
    ):
        if ids:
            d.append(f"<dt>{label}</dt><dd>" + ", ".join(link_contest(x, rel, chip=True) for x in ids) + "</dd>")
    if c.get("parent") is None and "parent" in c:
        d.append('<dt>advances to</dt><dd class="muted">— (top of hierarchy)</dd>')
    ids = c.get("cms_ids")
    if ids:
        d.append("<dt>CMS ids</dt><dd>" + ", ".join(cms_links(i) for i in ids) + "</dd>")
    elif ids == []:
        d.append("<dt>CMS ids</dt><dd class='muted'>" + ("pre-CMS era" if c.get("cms_status") == "pre-cms" else "none") + "</dd>")
    none = c.get("none") or []
    if none:
        d.append("<dt>confirmed none</dt><dd>" + ", ".join(role_label(r) for r in none) + ' <span class="small muted">(looked, there is no such source)</span></dd>')
    if c.get("notes"):
        d.append(f'<dt>notes</dt><dd class="wrap">{esc(c["notes"])}</dd>')
    if c.get("provenance"):
        d.append('<dt>provenance</dt><dd class="wrap small muted">' + "; ".join(esc(x) for x in refs(c["provenance"])) + "</dd>")
    d.append("</dl>")
    b += d
    matched: set = set()
    b += website_block(cid, c, rel, matched)
    b += results_block(cid, c, rel, matched)
    b += problems_section(cid, c, rel)
    b += other_sources_block(cid, c, rel, matched)
    caps = ARCHIVED_BY_CONTEST.get(cid)
    if caps:
        b.append(f'<p class="small muted">{len(caps)} raw capture(s) in the archive repo '
                 f'({local_link(f"archive/{sid}/{cid}/", "raw files")}).</p>')
    return page(cid, "\n".join(b), rel)


def contest_index(contests: dict, rel: str) -> str:
    rows = []
    for cid, c in sorted(contests.items()):
        sid = SERIES_OF[cid]
        pb = set_for(c)
        pstate = "listed" if pb.get("problems") else ("holdings" if pb else ("judge page" if has_role(c, "judge_page") else "none"))
        ws = web_state(c)
        wstate = "archived" if cid in website_of else {"link": "link only", "none": "confirmed none", "unknown": "unknown"}[ws]
        cc = country_of(c)
        rows.append(f'<tr><td>{link_contest(cid, rel, chip=True)}</td><td class="wrap small">{esc(c.get("name", ""))}</td>'
                    f'<td>{link_series(sid, rel)}</td><td data-v="{c.get("season", "")}">{link_season(c.get("season"), rel)}</td>'
                    f'<td>{esc(c.get("date", ""))}</td><td class="wrap small">{place_cell(c, rel, 2)}</td>'
                    f'<td data-v="{esc(LOC[cc]["name"]) if cc else ""}" class="small">{loc_link(cc, rel) if cc else ""}</td>'
                    f'<td class="small muted">{esc(SERIES_REGION.get(sid, "—"))}</td><td class="small muted">{esc(SERIES_TIER.get(sid, ""))}</td>'
                    f'<td data-v="{esc(TIER_LABEL[best_tier(c)]) if c.get("status") != "upcoming" else "upcoming"}">{tier_marks(c)}</td>'
                    f'<td data-v="{pstate}">{held_marks(pb) if pb else ""}</td>'
                    f'<td data-v="{wstate}" class="wrap small">{web_cell(c, cid, rel)}</td><td class="small">{cms_cell(c)}</td></tr>')
    body = ["<h1>Contests</h1>",
            f'<p class="muted">{len(contests)} contests in the mainline hierarchy. Filters: the drop-downs below '
            'select on a column\'s values; the box matches any text; click a header to sort. '
            f'Other views: the <a href="{rel}grid.html">grid</a> (series × year), <a href="{rel}season/index.html">seasons</a> (advancement trees), '
            f'<a href="{rel}coverage.html">coverage</a>, <a href="{rel}wanted.html">most wanted</a>.</p>', MARK_LEGEND, HELD_LEGEND,
            '<div class="tablewrap"><table class="flt"><tr><th>contest</th><th>name</th><th data-f>series</th><th data-f>season</th><th>date</th>'
            '<th>where</th><th data-f>country</th><th data-f>region</th><th data-f>level</th><th data-f>best result</th><th data-f>problems</th>'
            '<th data-f>website</th><th>CMS id</th></tr>' + "\n".join(rows) + "</table></div>"]
    return page("Contests", "\n".join(body), rel)


# ---- series pages ----
def series_years(doc: dict) -> tuple[int, int]:
    ys = [int(c["id"].rsplit("-", 1)[1]) for c in doc["contests"]]
    return min(ys), max(ys)


def series_page(sid: str, doc: dict, rel: str) -> str:
    s = doc["series"]
    b = [f"<h1>{esc(sid)}</h1>"]
    if s.get("name"):
        b.append(f'<p class="muted">{esc(s["name"])}</p>')
    y0, y1 = series_years(doc)
    d = ['<dl class="fields">']
    if s.get("tier"):
        d.append(f'<dt>tier</dt><dd>{esc(s["tier"])} <span class="small muted">(level in the hierarchy is derived from the graph; this is the series\' own label)</span></dd>')
    if s.get("region"):
        d.append(f"<dt>region</dt><dd>{esc(s['region'])}</dd>")
    if s.get("naming"):
        d.append(f'<dt>naming</dt><dd>{esc(s["naming"])} <span class="small muted">— the year in a contest id names the '
                 + ("season's first half (fall regionals)" if s["naming"] == "season-start" else "season's end (finals, championships)") + "</span></dd>")
    d.append(f"<dt>editions</dt><dd>{len(doc['contests'])} ({y0}–{y1})"
             + (f' <span class="small muted">— seasons {link_season(min(c["season"] for c in doc["contests"] if c.get("season")), rel)} to '
                f'{link_season(max(c["season"] for c in doc["contests"] if c.get("season")), rel)}</span>' if any(c.get("season") for c in doc["contests"]) else "") + "</dd>")
    lineage = s.get("lineage") or []
    if lineage or s.get("aliases"):
        bits = [f'<span class="chip">{esc(ev["type"])} {link_series(ev["series"], rel)} ({ev["year"]})</span>' for ev in lineage]
        bits += [f'<span class="chip" title="old id">alias {esc(a)}</span>' for a in s.get("aliases") or []]
        d.append("<dt>lineage</dt><dd>" + " ".join(bits) + "</dd>")
    if s.get("rotating_host"):
        d.append('<dt>rotating host</dt><dd>yes <span class="small muted">— a host-city series; year gaps are structural</span></dd>')
    if s.get("notes"):
        d.append(f'<dt>notes</dt><dd class="wrap">{esc(s["notes"])}</dd>')
    d.append("</dl>")
    b += d
    ran = [c for c in doc["contests"] if c.get("status") != "upcoming"]
    if ran:
        tiers = Counter(best_tier(c) for c in ran)
        n_arch = sum(1 for c in ran if any(held_capture(e) for e in result_sources(c)))
        n_site = sum(1 for c in ran if c["id"] in website_of)
        n_lost = sum(1 for c in ran if any(not held for _u, _w, held in lost_locators(c)))
        n_sets = sum(1 for c in ran if set_for(c))
        parts = [f'{tiers[k]} {TIER_LABEL[k]}' for k in ("scoreboard", "frozen_scoreboard", "standings", "rankings", "icpc", "none") if tiers[k]]
        b.append(f'<p class="state small">{len(ran)} editions ran'
                 + (f' (+{len(doc["contests"]) - len(ran)} upcoming)' if len(doc["contests"]) > len(ran) else "")
                 + ": " + ", ".join(parts) + f" · {n_arch} with an archived result · {n_site} websites archived · {n_sets} with a problem set"
                 + (f' · <span class="chip">{n_lost} lost</span>' if n_lost else "") + "</p>")
    b.append(MARK_LEGEND)
    has_probs = any(set_for(c) or has_role(c, "judge_page") for c in doc["contests"])
    if has_probs:
        b.append(HELD_LEGEND)
    b.append('<div class="tablewrap"><table><tr><th>contest</th><th>season</th><th>date</th><th>where</th>'
             "<th>advances to</th><th>results</th>" + ("<th>problems</th>" if has_probs else "")
             + "<th>website</th><th>CMS id</th></tr>")
    for c in reversed(doc["contests"]):  # latest first
        pcell = ""
        if has_probs:
            pb = set_for(c)
            pcell = ("<td>" + (f'<span class="small muted">{pb["count"]}</span> ' if pb.get("count") else "")
                     + held_marks(pb) + f' <span class="small">{set_link(pb["id"], rel, "set")}</span></td>') if pb else "<td></td>"
        b.append(
            "<tr><td>" + link_contest(c["id"], rel, chip=True) + "</td>"
            f'<td data-v="{c.get("season", "")}">{link_season(c.get("season"), rel)}</td>'
            f"<td>{esc(c.get('date', ''))}</td><td class=\"wrap small\">{place_cell(c, rel)}</td>"
            "<td>" + ", ".join(link_contest(p, rel) for p in refs(c.get("parent"))) + "</td>"
            f"<td>{tier_marks(c)}</td>{pcell}"
            f'<td class="wrap">{web_cell(c, c["id"], rel)}</td><td>{cms_cell(c)}</td></tr>'
        )
    b.append("</table></div>")
    return page(sid, "\n".join(b), rel)


def series_index(series_docs: dict, rel: str) -> str:
    rows = []
    for sid in sorted(series_docs):
        doc = series_docs[sid]
        y0, y1 = series_years(doc)
        tier = SERIES_TIER.get(sid, "")
        ran = [c for c in doc["contests"] if c.get("status") != "upcoming"]
        n_res = sum(1 for c in ran if best_tier(c) != "none")
        lin = " ".join(f'<span class="chip">{esc(ev["type"])} {link_series(ev["series"], rel)} ({ev["year"]})</span>' for ev in doc["series"].get("lineage") or [])
        rows.append(f'<tr><td>{link_series(sid, rel)}</td><td class="wrap">{esc(doc["series"].get("name", ""))}</td>'
                    f'<td class="small muted">{esc(SERIES_REGION.get(sid, "—"))}</td><td class="small">{esc(tier)}</td>'
                    f'<td class="small muted">{esc(doc["series"].get("naming", ""))}</td>'
                    f'<td class="num">{len(doc["contests"])}</td><td>{y0}–{y1}</td>'
                    f'<td class="num" title="editions that ran with any result source">{n_res}/{len(ran)}</td><td class="wrap small">{lin}</td></tr>')
    return page("Series", "<h1>Series</h1>"
                f'<p class="muted">{len(series_docs)} series — a series is a line of editions under one name; '
                'renamings are recorded as lineage (continues-as / continues-from). Filter by region or tier; click a header to sort.</p>'
                "<div class='tablewrap'><table class='flt'>"
                "<tr><th>series</th><th>name</th><th data-f>region</th><th data-f>tier</th><th data-f>naming</th>"
                "<th class='num'>editions</th><th>years</th><th class='num'>with results</th><th>lineage</th></tr>"
                + "\n".join(rows) + "</table></div>", rel)


# ---- seasons ----
BY_SEASON: dict = defaultdict(list)


def full_date(c: dict) -> str | None:
    d = c.get("date")
    return d if d and len(d) == 10 else None


def season_window(season: int, members: list[str]):
    """(start, end, early outliers, late outliers, wf date): the season's mainline date range
    is [earliest contest date, WF date]; a lone early (or post-WF) edition does not stretch
    it — the start is the first date with at least two more contests within 45 days."""
    dated = sorted((full_date(CONTESTS[m]), m) for m in members if full_date(CONTESTS[m]))
    if not dated:
        return None
    wf_date = next((d for d, m in dated if m.startswith("wf-")), None)
    ds = [d for d, _m in dated]
    P = datetime.date.fromisoformat
    start = ds[0]
    if len(ds) >= 4:
        for d in ds:
            if sum(1 for x in ds if 0 <= (P(x) - P(d)).days <= 45) >= 3:
                start = d
                break
    end = wf_date or ds[-1]
    if end < start:
        end = ds[-1]
    early = [(d, m) for d, m in dated if d < start]
    late = [(d, m) for d, m in dated if d > end and not m.startswith("wf-")]
    return start, end, early, late, wf_date


def season_stats(members: list[str]) -> dict:
    cs = [CONTESTS[m] for m in members]
    ran = [c for c in cs if c.get("status") != "upcoming"]
    sets = {}
    for c in ran:
        pb = set_for(c)
        if pb:
            sets[pb["id"]] = pb
    st = {"n": len(cs), "ran": len(ran), "upcoming": len(cs) - len(ran),
          "tiers": Counter(best_tier(c) for c in ran),
          "arch": sum(1 for c in ran if any(held_capture(e) for e in result_sources(c))),
          "sets": len(sets), "problems": sum(d.get("count") or len(d.get("problems") or []) for d in sets.values()),
          "web": sum(1 for c in ran if c["id"] in website_of),
          "web_link": sum(1 for c in ran if web_state(c) == "link"),
          "sites": sum(len(physical_sites(c)) for c in cs),
          "countries": len({country_of(c) for c in cs if country_of(c)})}
    for k, *_ in HELD_KINDS:
        st[k] = sum(set_kind_count(d, k) for d in sets.values())
    return st


def season_tree(season: int, members: list[str], rel: str, root: str | None = None):
    """(tree html or '', unplaced ids): the advancement tree with the WF at the root (via
    `parent`), then every member with no path to it."""
    mset, seen = set(members), set()

    def node(cid):
        seen.add(cid)
        c = CONTESTS[cid]
        kids = sorted(k for k in CHILDREN.get(cid, []) if k in mset and k not in seen)
        extra = " · ".join(x for x in (place_cell(c, rel, 1), cms_cell(c), web_cell(c, cid, rel)) if x)
        label = (link_contest(cid, rel, chip=True)
                 + f'<span class="meta">{esc(c.get("date", ""))} {tier_marks(c)}'
                 + (f' <span class="small">{extra}</span>' if extra else "") + "</span>")
        if not kids:
            return f'<div class="leaf">{label}</div>'
        inner = "\n".join(node(k) for k in kids)
        return f"<details open><summary>{label}</summary>{inner}</details>"

    wf_id = root or f"wf-{season}"
    tree = f'<div class="tree">{node(wf_id)}</div>' if wf_id in CONTESTS and wf_id in mset else ""
    return tree, sorted(m for m in mset if m not in seen)


def stats_strip(st: dict) -> str:
    tiers = " · ".join(f"{st['tiers'][k]} {TIER_LABEL[k]}" for k in ("scoreboard", "frozen_scoreboard", "standings", "rankings", "icpc", "none") if st["tiers"][k])
    held = " · ".join(f"{st[k]} with {w}" for k, _l, w in HELD_KINDS)
    return ('<div class="stats">'
            f'<div><b>{st["ran"]}</b> contests ran' + (f' <span class="small muted">+{st["upcoming"]} upcoming</span>' if st["upcoming"] else "") + "</div>"
            f'<div><b>{st["arch"]}</b> archived results <span class="small muted">best tier: {tiers}</span></div>'
            f'<div><b>{st["sets"]}</b> problem sets <span class="small muted">{st["problems"]} problems; {held}</span></div>'
            f'<div><b>{st["web"]}</b> websites archived <span class="small muted">of {st["web_link"]} known</span></div>'
            f'<div><b>{st["sites"]}</b> sites <span class="small muted">in {st["countries"]} countries</span></div>'
            '<div><b>—</b> unique teams <span class="small muted">not yet computed</span></div></div>')


def season_page(season: int, members: list[str], rel: str) -> str:
    body = [f"<h1>Season {season - 1}–{season}</h1>"]
    win = season_window(season, members)
    d = ['<dl class="fields">']
    wf_id = f"wf-{season}"
    if wf_id in CONTESTS:
        c = CONTESTS[wf_id]
        d.append(f"<dt>World Finals</dt><dd>{link_contest(wf_id, rel, chip=True)}" + (f' <span class="muted">{esc(c["name"])}</span>' if c.get("name") else "")
                 + (f' · {esc(c["date"])}' if c.get("date") else "") + (f' · {place_cell(c, rel)}' if place_cell(c, rel) else "") + "</dd>")
    else:
        d.append('<dt>World Finals</dt><dd class="muted">none in the catalogue for this season</dd>')
    if win:
        start, end, early, late, _wf = win
        d.append(f"<dt>dates</dt><dd>{esc(start)} – {esc(end)}" + ("" if _wf else ' <span class="small muted">(no dated World Finals: ends at the last contest)</span>') + "</dd>")
        if early or late:
            foot = []
            if early:
                foot.append("earlier: " + ", ".join(f"{link_contest(m, rel)} ({esc(dd)})" for dd, m in early))
            if late:
                foot.append("after the finals: " + ", ".join(f"{link_contest(m, rel)} ({esc(dd)})" for dd, m in late))
            d.append('<dt>outliers</dt><dd class="small">' + "; ".join(foot) + ' <span class="muted">— not counted in the range</span></dd>')
    d.append(f'<dt>contests</dt><dd>{len(members)} <span class="small muted">(<a href="{rel}contest/index.html#f:3={season}">as a table</a>)</span></dd>')
    d.append("</dl>")
    body += d
    body.append(stats_strip(season_stats(members)))
    body.append(MARK_LEGEND)
    tree, unplaced = season_tree(season, members, rel)
    body.append("<h2>Hierarchy</h2>")
    if tree:
        body.append('<p class="small muted">The World Finals at the root; each contest under the one it advances to (championship layer when present, regionals, subregionals).</p>')
        body.append(tree)
    else:
        body.append('<p class="muted">No World Finals in this season to root the tree.</p>')
    if unplaced:
        body.append(f'<h2>Free-floating ({len(unplaced)})</h2><p class="small muted">Contests of this season with no path to its World Finals '
                    '(parent not researched, or pointing outside the season).</p><div class="tree">'
                    + "\n".join(f'<div class="leaf">{link_contest(x, rel, chip=True)}<span class="meta">{esc(CONTESTS[x].get("date", ""))} {tier_marks(CONTESTS[x])}'
                                + (f' → {", ".join(link_contest(p, rel) for p in refs(CONTESTS[x].get("parent")))}' if refs(CONTESTS[x].get("parent")) else "")
                                + "</span></div>" for x in unplaced) + "</div>")
    return page(f"Season {season - 1}–{season}", "\n".join(body), rel)


def season_index(rel: str) -> str:
    rows = []
    for season in sorted(BY_SEASON, reverse=True):
        ids = BY_SEASON[season]
        wf = [x for x in ids if x.startswith("wf-")]
        wfc = [CONTESTS[x] for x in sorted(wf)]
        st = season_stats(ids)
        win = season_window(season, ids)
        rows.append(f'<tr><td>{link_season(season, rel)}</td>'
                    "<td>" + ", ".join(link_contest(x, rel, chip=True) for x in sorted(wf)) + "</td>"
                    "<td>" + ", ".join(esc(c.get("date", "")) for c in wfc) + "</td>"
                    f'<td class="small">{esc(win[0]) + " – " + esc(win[1]) if win else ""}</td>'
                    f'<td class="num">{len(ids)}</td><td class="num">{st["arch"]}</td><td class="num">{st["sets"]}</td><td class="num">{st["web"]}</td>'
                    '<td class="wrap small">' + " · ".join(web_cell(c, c["id"], rel) for c in wfc if web_cell(c, c["id"], rel)) + "</td></tr>")
    return page("Seasons", "<h1>Seasons</h1><p class='muted'>A season runs from the first regional to the World Finals it feeds; "
                "the id year of a contest is its season label (fall regionals carry the season-start year, finals the end year). "
                "Each season page shows the full advancement tree.</p><div class='tablewrap'><table>"
                "<tr><th>season</th><th>World Finals</th><th>WF date</th><th>dates</th><th class='num'>contests</th>"
                "<th class='num' title='contests with an archived result capture'>archived results</th><th class='num'>problem sets</th>"
                "<th class='num'>websites archived</th><th>WF website</th></tr>"
                + "\n".join(rows) + "</table></div>", rel)


# ---- source pages (DEFINITIONS.md, Resources: source = locator, snapshot = resource, capture) ----
ALSO_AT: dict = defaultdict(list)    # source id -> [(mirror url, as_of, note)] from the catalogue's also_at
MIRROR_OF: dict = defaultdict(list)  # mirror's source id -> [primary url]
SRC_ROLES: dict = defaultdict(set)   # source id -> roles it serves anywhere in the catalogue


def index_sources(contests: dict) -> None:
    ALSO_AT.clear()
    MIRROR_OF.clear()
    SRC_ROLES.clear()
    for c in contests.values():
        for s in sources(c):
            k = lid(s["url"])
            SRC_ROLES[k].update(s["roles"])
            for m in also_at(s):
                ALSO_AT[k].append((m["url"], m.get("as_of"), m.get("note")))
                MIRROR_OF[lid(m["url"])].append(s["url"])
                SRC_ROLES[lid(m["url"])].add("mirror")


def field_chip(field: str) -> str:
    if field.startswith("judge-"):
        return f'<span class="chip">judge page · {esc(judge_name(field[6:]))}</span>'
    return role_chip(field)


def capture_table(caps: list[dict], url: str, rel: str) -> str:
    """Provenance of every capture of one snapshot: contest, artifact, wrapper URL fetched,
    fetch time, sha256, size, content type, path (raw), replay."""
    b = ['<div class="tablewrap"><table class="nosort small"><tr><th>contest</th><th>artifact</th><th>fetched</th><th>via</th>'
         '<th>fetched from</th><th>type</th><th class="num">size</th><th>sha256</th><th>path</th><th>links</th></tr>']
    for c in caps:
        flags = []
        if c.get("wrapper_fetched"):
            flags.append('<span class="chip" title="fetched through the Wayback wrapper rather than the raw id_ endpoint; Wayback chrome is stripped at bake/playback">wrapper</span>')
        if c.get("caveat"):
            flags.append(f'<span class="chip" title="{esc(c["caveat"])}">caveat</span>')
        links = []
        if c.get("replay"):
            links.append(f'<a href="{REPLAY_BASE}/{esc(c["replay"])}">replay</a>')
        links.append(local_link("archive/" + c["path"], "raw"))
        fu = c.get("fetch_url") or url
        b.append(f'<tr><td>{contest_ref(c["contest"], rel)}</td><td>{esc(c["artifact"].replace("_", " "))} {" ".join(flags)}</td>'
                 f'<td>{esc(str(c.get("fetched") or "")[:16].replace("T", " "))}</td><td>{esc(c.get("source") or "")}</td>'
                 f'<td class="url"><a href="{esc(fu)}">{esc(fu if len(fu) <= 90 else fu[:89] + "…")}</a></td>'
                 f'<td>{esc((c.get("content_type") or "").split(";")[0])}</td><td class="num">{c.get("size") or ""}</td>'
                 f'<td><code title="{esc(c.get("sha256") or "")}">{esc((c.get("sha256") or "")[:16])}</code></td>'
                 f'<td class="url small muted">{esc(c["path"])}</td><td>{" · ".join(links)}</td></tr>')
    b.append("</table></div>")
    return "\n".join(b)


def website_crawl(site: dict, rel: str) -> str:
    d = ['<dl class="fields small">', f'<dt>website crawl</dt><dd>{contest_ref(site["contest"], rel)} · mode {esc(site.get("mode") or "")}'
         + (' <span class="chip" title="crawl seeded with a Wayback wrapper URL before the resource model; Wayback chrome stripped at playback">legacy wrapper</span>' if site.get("legacy_wrapper") else "")
         + f' · fetched {esc(str(site.get("fetched") or "")[:16].replace("T", " "))}' + (f' ({esc(site.get("tool"))})' if site.get("tool") else "") + "</dd>"]
    if site.get("scopes"):
        d.append('<dt>scope</dt><dd class="wrap">' + "; ".join(
            f'{esc(s.get("host", ""))}{esc(s.get("path", ""))} <span class="muted">({esc(s.get("rule", ""))})</span>' for s in site["scopes"]) + "</dd>")
    d.append(f'<dt>size</dt><dd>{site.get("pages") or 0} pages ({site.get("html_pages") or 0} html), {round((site.get("bytes") or 0) / 1e6, 1)} MB'
             + (f'; {site["unfetched"]} in scope not fetched, {site["offsite"]} offsite links' if "unfetched" in site else "") + "</dd>")
    cap_dir = site["dir"].rsplit("/", 1)[-1]
    pb = local_link(f"site/{site['contest']}/{cap_dir}/", "archived site")
    rf = local_link("archive/" + site["dir"] + "/", "raw files")
    d.append(f"<dt>play back</dt><dd>{pb} · {rf}</dd>")
    d.append("</dl>")
    pl = site.get("page_list")
    if pl:
        d.append(f'<details><summary class="small">pages ({len(pl)})</summary><div class="tablewrap"><table class="nosort small"><tr><th>url</th><th>status</th><th>type</th><th class="num">size</th><th>snapshot</th></tr>')
        for u, status, size, pts, ctype in sorted(pl, key=lambda x: str(x[0])):
            pl_link = local_link(f"site/{site['contest']}/{cap_dir}/{u}", "local") if str(status) == "200" else ""
            d.append(f'<tr><td class="url"><a href="{esc(u)}">{esc(u[:110])}</a> {pl_link}</td><td>{esc(status)}</td><td>{esc(ctype or "")}</td>'
                     f'<td class="num">{size or ""}</td><td>{esc(fmt_time(pts)) if pts else ""}</td></tr>')
        d.append("</table></div></details>")
    return "\n".join(d)


def source_page(k: str, L: dict, rel: str) -> str:
    url = L["url"]
    health = L.get("health") or {}
    b = [f'<h1 class="wrap" style="word-break:break-all">{esc(url)}</h1>',
         f'<p class="muted">source <code>{k}</code> · match key <code>{esc(L["key"])}</code> · '
         f'<a href="{rel}source/index.html">all sources</a></p>', '<dl class="fields">',
         f'<dt>live</dt><dd class="url"><a href="{esc(url)}">{esc(url)}</a></dd>',
         f'<dt>wayback</dt><dd><a href="{esc(wayback_link(url))}">calendar of snapshots</a></dd>']
    roles = sorted(SRC_ROLES.get(k, set()), key=lambda r: RANK.get(r, 99))
    if roles:
        b.append("<dt>roles</dt><dd>" + "".join(role_chip(r) if r != "mirror" else '<span class="chip">mirror</span>' for r in roles) + "</dd>")
    if health:
        st = health.get("state", "")
        b.append(f'<dt>health</dt><dd><span class="chip" title="{esc(STATE_TITLE.get(st, ""))}">{esc(st)}</span>'
                 + (f' checked {esc(health["checked"])}' if health.get("checked") else "")
                 + (f' <span class="muted small">— {esc(health["evidence"])}</span>' if health.get("evidence") else "")
                 + (f' <span class="muted small">({esc(health["note"])})</span>' if health.get("note") else "")
                 + f'<br><span class="small muted">{esc(STATE_TITLE.get(st, ""))}</span></dd>')
    else:
        b.append('<dt>health</dt><dd class="muted">never live-checked</dd>')
    wb = L.get("wayback")
    if wb:
        b.append(f'<dt>wayback status</dt><dd><span class="chip" title="{esc(WB_HELP.get(wb["state"], ""))}">{esc(wb["state"])}</span>'
                 + (f' checked {esc(wb["checked"])}' if wb.get("checked") else "")
                 + (f' <span class="muted small">— {esc(wb["evidence"])}</span>' if wb.get("evidence") else "") + "</dd>")
    seen, items = set(), []
    for r in L.get("refs") or []:
        key = (r["contest"], r["field"])
        if key in seen:
            continue
        seen.add(key)
        extra = f' <span class="muted small">as of {fmt_time(r["as_of"])}</span>' if r.get("as_of") else ""
        if r.get("note"):
            extra += f' <span class="muted small">— {esc(r["note"])}</span>'
        items.append(f'{contest_ref(r["contest"], rel)} {field_chip(r["field"])}{extra}')
    if items:
        b.append(f'<dt>referenced by</dt><dd class="wrap">{"<br>".join(items)}</dd>')
    if ALSO_AT.get(k):
        b.append('<dt>also at</dt><dd class="wrap">' + "<br>".join(
            f'{src_link(mu, mts, rel, esc(res_label(mu, mts, 110)))} · <a href="{esc(mu)}">live</a> · <a href="{esc(wayback_link(mu, mts))}">wayback</a>{health_chip(mu)}'
            + (f' <span class="muted small">— {esc(note)}</span>' if note else "") for mu, mts, note in ALSO_AT[k]) + "</dd>")
    if MIRROR_OF.get(k):
        b.append('<dt>mirror of</dt><dd class="wrap">' + "<br>".join(src_link(pu, None, rel, esc(pu[:110])) for pu in dict.fromkeys(MIRROR_OF[k])) + "</dd>")
    b.append("</dl>")
    res = L["resources"]
    b.append(f"<h2>Snapshots ({len(res)})</h2>")
    if not res:
        b.append('<p class="muted">No snapshot: nothing has ever been observed at this address by this project. See the checks below for what was tried.</p>')
    else:
        b.append('<p class="small muted">One entry per time this address is known at: Wayback snapshots we captured, our live fetches, '
                 'and times the catalogue declares (as_of) without a capture. Each capture is our stored copy, with its provenance.</p>')
    for ts in sorted(res, key=lambda t: (t == "unknown", t)):
        Rr = res[ts]
        caps = Rr.get("captures") or []
        via = Rr.get("via") or ""
        held = Rr.get("held")
        b.append(f'<div class="snap" id="s-{esc(ts)}"><h3>{esc(fmt_time(ts) if ts != "unknown" else "time unknown")} '
                 + (f'<span class="chip" title="{esc(VIA_HELP.get(via, ""))}">{esc(via)}</span>' if via else "")
                 + (' <span class="chip">held</span>' if held else ' <span class="chip" title="declared in the catalogue (as_of); no capture">declared only</span>')
                 + f' <span class="small muted">{k}@{esc(ts)}</span></h3>')
        d = ['<dl class="fields small">']
        if ts != "unknown":
            d.append(f'<dt>wayback</dt><dd><a href="{esc(wayback_link(url, ts))}">snapshot nearest {esc(fmt_time(ts))}</a></dd>')
        arts = sorted({c["artifact"] for c in caps} | ({"website"} if Rr.get("website") else set()))
        if arts:
            d.append(f'<dt>artifacts</dt><dd>{" · ".join(esc(a.replace("_", " ")) for a in arts)}</dd>')
        rr = Rr.get("refs") or []
        if rr:
            d.append('<dt>referenced by</dt><dd class="wrap">' + " · ".join(f'{contest_ref(r["contest"], rel)} {field_chip(r["field"])}' for r in rr) + "</dd>")
        if len(caps) > 1:
            shas = {c.get("sha256") for c in caps if c.get("sha256")}
            d.append('<dt>consistency</dt><dd>' + ("all captures hash identically — the same content was fetched each time" if len(shas) == 1
                                                    else f"{len(shas)} distinct content hashes among {len(caps)} captures — the content differed between fetches") + "</dd>")
        d.append("</dl>")
        b += d
        if caps:
            b.append(capture_table(caps, url, rel))
        if Rr.get("website"):
            b.append(website_crawl(Rr["website"], rel))
        b.append("</div>")
    probes = L.get("probes") or []
    if probes:
        b.append(f"<h2>Checks ({len(probes)})</h2>")
        b.append('<p class="small muted">Every time this address was looked at and what came back. A check that found no content is a record of the attempt, not a snapshot.</p>')
        b.append('<div class="tablewrap"><table><tr><th>when</th><th>via</th><th>outcome</th><th>evidence</th></tr>')
        for pr in probes:
            extra = ""
            if pr.get("dir"):
                extra = f' <span class="muted small">({contest_ref(pr["contest"], rel)} crawl {esc(pr["dir"].rsplit("/", 1)[-1])})</span>'
            elif pr.get("path"):
                extra = (f' <span class="muted small">({contest_ref(pr["contest"], rel)} {esc(pr.get("artifact") or "")} · '
                         f'{local_link("archive/" + pr["path"], "raw")})</span>')
            b.append(f'<tr><td>{esc(fmt_time(pr.get("ts")) if pr.get("ts") else "")}</td><td>{esc(pr.get("via") or "")}</td>'
                     f'<td><span class="chip" title="{esc(OUT_HELP.get(pr.get("outcome"), ""))}">{esc(pr.get("outcome") or "")}</span></td>'
                     f'<td class="wrap">{esc(pr.get("evidence") or "")}{extra}</td></tr>')
        b.append("</table></div>")
    return page(url[:80], "\n".join(b), rel)


def source_index(rel: str) -> str:
    rows = []
    for k, L in RES.locs.items():
        url = L["url"]
        roles = sorted(SRC_ROLES.get(k, set()), key=lambda r: RANK.get(r, 99))
        h = (L.get("health") or {})
        cs = sorted({r["contest"] for r in L.get("refs") or []})
        res = L["resources"]
        ncap = sum(len(R.get("captures") or []) for R in res.values())
        vias = sorted({R.get("via") or "" for R in res.values()} - {""})
        rows.append(f'<tr><td class="url"><a href="{rel}source/{k}/index.html">{esc(url if len(url) <= 90 else url[:89] + "…")}</a></td>'
                    f'<td data-vs="{esc(" ".join(roles))}" class="small">{esc(", ".join(role_label(r) for r in roles))}</td>'
                    f'<td data-v="{esc(h.get("state") or "unchecked")}" class="small">{esc(h.get("state") or "")}</td>'
                    f'<td class="small">{esc(h.get("checked") or "")}</td>'
                    f'<td data-v="{len(cs)}" class="small">{", ".join(contest_ref(c, rel) for c in cs[:3])}{" +" + str(len(cs) - 3) if len(cs) > 3 else ""}</td>'
                    f'<td class="num">{len(res)}</td><td class="num">{ncap}</td><td data-vs="{esc(" ".join(vias))}" class="small muted">{esc(", ".join(vias))}</td>'
                    f'<td data-v="{"yes" if ncap else "no"}" class="small">{"yes" if ncap else ""}</td></tr>')
    by_role_links = " · ".join(f'<a href="by-role/{r}.html">{role_label(r)}</a>' for r in ROLE_PAGES)
    return page("Sources", "<h1>Sources</h1>"
                f'<p class="muted">{len(RES.locs)} sources — every catalogued address (and mirror). A <b>source</b> is an address with roles and a health; '
                'a <b>snapshot</b> is that address at one time (a Wayback snapshot, or our live fetch); a <b>capture</b> is our stored copy of a snapshot. '
                f'Filter by role, health or via; the box matches the address or a contest id. Per-role lists with wayback/archived links: {by_role_links}.</p>'
                '<p class="small muted">Health chips (hover for the rule): ' + " · ".join(f'<span class="chip" title="{esc(v)}">{kk}</span>' for kk, v in STATE_TITLE.items()) + "</p>"
                '<div class="tablewrap"><table class="flt"><tr><th>address</th><th data-f>roles</th><th data-f>health</th><th>checked</th>'
                '<th>contests</th><th class="num">snapshots</th><th class="num">captures</th><th data-f>via</th><th data-f>held</th></tr>'
                + "\n".join(rows) + "</table></div>", rel)


ROLE_PAGES = ["scoreboard", "frozen_scoreboard", "standings", "rankings", "icpc_standings", "web", "mirror", "problemset", "judge_page", "teams"]


def role_pages(out: Path, contests: dict) -> None:
    """source/by-role/<role>.html — every source serving a role, with wayback/archived links
    (the old resources/<role>.html lists)."""
    rel = "../../"
    tables = {k: [] for k in ROLE_PAGES}
    for cid in sorted(contests):
        c = contests[cid]
        for k in ROLE_PAGES:
            if k != "mirror":
                tables[k] += [(cid, e) for e in by_role(c, k)]
        for s in sources(c):
            for m in also_at(s):
                tables["mirror"].append((cid, m))
    counts = {k: len(tables[k]) for k in ROLE_PAGES}
    legend = " · ".join(f'<span class="chip" title="{esc(v)}">{k}</span>' for k, v in STATE_TITLE.items())
    for k in ROLE_PAGES:
        nav_line = " · ".join((f'<b>{role_label(kk)} ({counts[kk]})</b>' if kk == k else f'<a href="{kk}.html">{role_label(kk)} ({counts[kk]})</a>') for kk in ROLE_PAGES)
        rows_h = []
        for cid, e in tables[k]:
            extras = []
            hc = health_chip(e["url"], e)
            if hc:
                extras.append(hc.strip())
            if e.get("as_of"):
                extras.append(f'<a class="small" href="{esc(wayback_link(e["url"], e["as_of"]))}">wayback</a>')
            for n, pth in enumerate(archived(e)):
                extras.append(f'<a class="small" href="{REPLAY_BASE}/a/{esc(pth)}">' + ("archived" if n == 0 else f"archived {n + 1}") + "</a>")
            if e.get("note"):
                extras.append(f'<span class="muted small">{esc(e["note"])}</span>')
            rows_h.append(f'<tr><td>{contest_ref(cid, rel)}</td>'
                          f'<td class="url">{src_link(e["url"], e.get("as_of"), rel, esc(res_label(e["url"], e.get("as_of"), 110)))}'
                          f' <a class="small" href="{esc(e["url"])}">live</a></td><td>{" ".join(extras)}</td></tr>')
        body = (f'<h1>{esc(role_label(k))} sources</h1><p class="small muted">{nav_line} · <a href="../index.html">every source</a></p>'
                f'<p class="small muted">A source shows as <code>url (time)</code> when the content meant is a dated snapshot. '
                f'Chips are the source\'s health at the last live check (hover for the rule): {legend}</p>'
                '<div class="tablewrap"><table><tr><th>contest</th><th>source</th><th></th></tr>' + "\n".join(rows_h) + "</table></div>")
        (out / "source" / "by-role" / f"{k}.html").write_text(page(f"{role_label(k)} sources", body, rel))


# ---- judges ----
def judge_page(jid: str, j: dict, contests: dict, nm: list, rel: str) -> str:
    b = [f'<h1>{esc(j.get("name") or jid)}</h1>', f'<p class="muted">online judge <code>{esc(jid)}</code> · <a href="index.html">all judges</a></p>', '<dl class="fields">']
    b.append(f'<dt>site</dt><dd><a href="{esc(j["url"])}">{esc(j["url"])}</a></dd>')
    st = esc(j.get("status", ""))
    if j.get("closed"):
        st += f" {esc(j['closed'])}"
    b.append(f'<dt>status</dt><dd><span class="chip">{st}</span>' + (' <span class="small muted">— pages survive only in Wayback snapshots taken before the closing date</span>' if j.get("status") == "closed" else "") + "</dd>")
    for key, lab in (("problem_url", "problem url"), ("contest_url", "contest url")):
        if j.get(key):
            b.append(f'<dt>{lab}</dt><dd><code>{esc(j[key])}</code></dd>')
    offers = [w for w, k in (("statements", "statements"), ("submissions", "submissions")) if j.get(k)]
    if offers:
        b.append(f'<dt>offers</dt><dd>{" · ".join(offers)}</dd>')
    if j.get("notes"):
        b.append(f'<dt>notes</dt><dd class="wrap">{esc(j["notes"])}</dd>')
    pages = [(c["id"], s) for c in list(contests.values()) + nm for s in by_role(c, "judge_page") if s.get("judge") == jid]
    probs = [(pid, r) for pid, ent in PROBLEMS.items() for _s, r in ent["rows"][:1] for jj in r.get("judges") or [] if jj["judge"] == jid]
    b.append(f'<dt>coverage</dt><dd>{len({c for c, _s in pages})} contests with a judge page · {len({p for p, _r in probs})} problems linking here</dd>')
    b.append(f'<dt>data</dt><dd class="small"><a href="{REPO_URL}judges.yaml">judges.yaml</a></dd></dl>')
    if pages:
        b.append(f"<h2>Contest pages ({len(pages)})</h2><div class='tablewrap'><table><tr><th>contest</th><th>date</th><th>page</th><th></th></tr>")
        for cid, s in sorted(pages, key=lambda t: (t[0], t[1]["url"])):
            c = CONTESTS.get(cid) or {}
            b.append(f'<tr><td>{contest_ref(cid, rel)}</td><td>{esc(c.get("date", ""))}</td>'
                     f'<td class="url">{src_link(s["url"], s.get("as_of"), rel, esc(res_label(s["url"], s.get("as_of"), 100)))}</td>'
                     f'<td class="small"><a href="{esc(s["url"])}">live</a> · <a href="{esc(wayback_link(s["url"], s.get("as_of")))}">wayback</a>{health_chip(s["url"], s)}</td></tr>')
        b.append("</table></div>")
    if probs:
        b.append(f"<h2>Problems ({len(probs)})</h2><div class='tablewrap'><table><tr><th>problem</th><th>judge id</th><th>link</th><th>sets</th></tr>")
        for pid, r in sorted(probs, key=lambda t: r_name(t[1])):
            jl = [jj for jj in r.get("judges") or [] if jj["judge"] == jid]
            b.append(f'<tr><td class="wrap">{problem_name_cell(r, rel)}</td><td class="small">{", ".join(esc(jj.get("id") or "") for jj in jl)}</td>'
                     f'<td class="small">{problem_judge_links({"judges": jl})}</td>'
                     f'<td class="small">{", ".join(set_link(s, rel) for s, _r in PROBLEMS[pid]["rows"])}</td></tr>')
        b.append("</table></div>")
    return page(j.get("name") or jid, "\n".join(b), rel)


def r_name(r: dict) -> str:
    return r.get("name") or ""


# ---- locations ----
def loc_count(nid: str) -> int:
    return len(LOC_SUB.get(nid, ()))


def location_page(nid: str, rel: str) -> str:
    n = LOC[nid]
    b = [f"<h1>{esc(n['name'])}</h1>", f'<p class="muted">{esc(n["type"])} <code>{esc(nid)}</code>'
         + (" · " + loc_crumb(nid, rel, from_node=False) if n.get("parent") else "") + f' · <a href="{rel}location/index.html">all locations</a></p>', '<dl class="fields">']
    for key, lab in (("iso", "ISO code"), ("code", "code"), ("geonameid", "GeoNames")):
        if n.get(key):
            v = f'<a href="https://www.geonames.org/{n[key]}/">{n[key]}</a>' if key == "geonameid" else esc(n[key])
            b.append(f"<dt>{lab}</dt><dd>{v}</dd>")
    if n.get("aliases"):
        b.append("<dt>aliases</dt><dd>" + ", ".join(esc(a) for a in n["aliases"]) + "</dd>")
    if n.get("notes"):
        b.append(f'<dt>notes</dt><dd class="wrap">{esc(n["notes"])}</dd>')
    direct = LOC_DIRECT.get(nid, [])
    sub = LOC_SUB.get(nid, set())
    b.append(f'<dt>contests</dt><dd>{len({c for c, _s in direct})} held exactly here · {len(sub)} in the subtree</dd>')
    kids = LOC_KIDS.get(nid, [])
    if kids:
        b.append(f'<dt>contains</dt><dd class="wrap">' + ", ".join(f'{loc_link(k, rel)} <span class="small muted">({loc_count(k)})</span>' for k in kids) + "</dd>")
    b.append(f'<dt>data</dt><dd class="small"><a href="{REPO_URL}locations.yaml">locations.yaml</a></dd></dl>')

    def table(rows, with_site=True):
        t = ['<div class="tablewrap"><table><tr><th>contest</th><th>season</th><th>date</th><th>series</th>' + ("<th>site</th>" if with_site else "<th>where</th>") + "<th>results</th></tr>"]
        for cid, s in rows:
            c = CONTESTS[cid]
            cell = (site_line(s, rel) if with_site else place_cell(c, rel, 2)) if s is not None else ""
            t.append(f'<tr><td>{link_contest(cid, rel, chip=True)}</td><td data-v="{c.get("season", "")}">{link_season(c.get("season"), rel)}</td><td>{esc(c.get("date", ""))}</td>'
                     f'<td>{link_series(SERIES_OF[cid], rel)}</td><td class="wrap small">{cell}</td><td>{tier_marks(c)}</td></tr>')
        t.append("</table></div>")
        return t
    if direct:
        b.append(f"<h2>Held here ({len({c for c, _s in direct})})</h2>")
        b += table(sorted(direct, key=lambda t: (CONTESTS[t[0]].get("date") or "", t[0])))
    rest = sorted(sub - {c for c, _s in direct}, key=lambda c: (CONTESTS[c].get("date") or "", c))
    if rest:
        b.append(f"<h2>Elsewhere in {esc(n['name'])} ({len(rest)})</h2>")
        if len(rest) <= 400:
            b += table([(c, None) for c in rest], with_site=False)
        else:
            b.append('<p class="small muted">Too many to list here — follow the children above (counts in brackets), or '
                     f'filter the <a href="{rel}contest/index.html#f:6={esc(n["name"])}">contest table</a> by country.</p>')
    return page(n["name"], "\n".join(b), rel)


def location_index(rel: str) -> str:
    def li(nid):
        n = LOC[nid]
        kids = LOC_KIDS.get(nid, [])
        cnt = loc_count(nid)
        lab = f'{loc_link(nid, rel)} <span class="small muted">{cnt}</span>' + (f' <span class="small muted">· {esc(n["type"])}</span>' if n["type"] == "region" else "")
        if not kids:
            return f"<li>{lab}</li>"
        return f"<li><details><summary>{lab}</summary><ul>" + "".join(li(k) for k in kids) + "</ul></details></li>"
    countries = sorted((nid for nid, n in LOC.items() if n["type"] == "country"), key=lambda x: (-loc_count(x), LOC[x]["name"]))
    types = Counter(n["type"] for n in LOC.values())
    return page("Locations", "<h1>Locations</h1>"
                f'<p class="muted">{types["country"]} countries, {types["region"]} regions, {types["city"]} cities, {types["institution"]} institutions — '
                'one tree (country › region › city › institution); the number after a name is the contests held anywhere under it. '
                'Countries are ordered by that count; expand to drill down.</p>'
                '<div class="loctree"><ul>' + "".join(li(c) for c in countries) + "</ul></div>", rel)


NM: list = []  # registry/non-mainline.yaml


def build(out: Path):
    t0 = time.time()
    series_docs, contests, series_of, prev, children, subsets, aux = load()
    derive_regions(series_docs, contests)
    load_problem_sets()
    load_locations_tree(contests)
    index_sources(contests)
    NM[:] = load_non_mainline()
    CHILDREN.clear(); CHILDREN.update(children)  # noqa: E702
    PREV.clear(); PREV.update(prev)  # noqa: E702
    SUBSETS.clear(); SUBSETS.update(subsets)  # noqa: E702
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("contest", "series", "season", "problemset", "problem", "problems", "judge", "location", "source", "source/by-role"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    replay_lookup = REPLAY_LOOKUP
    replay_lookup.clear()
    REPLAY_PROBLEMSET.clear()
    REPLAY_BY_CONTEST.clear()
    if aux["replay-index"]:
        for e in aux["replay-index"]["pages"]:
            if e.get("url"):
                k = (e["contest"], norm_key(e["url"]))
                replay_lookup[k] = e["path"]
                if e.get("artifact") == "problemset":
                    REPLAY_PROBLEMSET[k] = e["path"]
            REPLAY_BY_CONTEST[e["contest"]].append(e)
    ARCHIVED_BY_CONTEST.clear()
    PROBLEMSET_CAPS.clear()
    JUDGE_CAPS.clear()
    capture_info.clear()
    if aux["archive-index"]:
        for e in aux["archive-index"]["captures"]:
            ARCHIVED_BY_CONTEST[e["contest"]].append(e)
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
    archived_by_contest = ARCHIVED_BY_CONTEST
    BY_SEASON.clear()
    for cid, c in contests.items():
        if c.get("season"):
            BY_SEASON[c["season"]].append(cid)

    # ---- contests ----
    for cid, c in contests.items():
        (out / "contest" / f"{cid}.html").write_text(contest_page(cid, c, "../"))
    (out / "contest" / "index.html").write_text(contest_index(contests, "../"))

    # ---- series ----
    for sid, doc in series_docs.items():
        (out / "series" / f"{sid}.html").write_text(series_page(sid, doc, "../"))
    (out / "series" / "index.html").write_text(series_index(series_docs, "../"))

    # ---- seasons ----
    for season, members in BY_SEASON.items():
        (out / "season" / f"{season}.html").write_text(season_page(season, members, "../"))
    (out / "season" / "index.html").write_text(season_index("../"))
    stub(out / "seasons.html", "season/index.html")
    by_season = BY_SEASON
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
           '<p class="small muted">Other views: <a href="grid.html">the grid</a> (every contest on one screen) · '
           '<a href="wanted.html">most wanted</a> · <a href="problems/index.html">problem holdings by contest</a> · '
           '<a href="cms.html">CMS id ledger</a> · <a href="non-mainline.html">non-mainline registry</a> · '
           '<a href="catalogue.json">catalogue.json</a></p>',
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
               'Season trees live under <a href="season/index.html">seasons</a>.</p>'
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
          "with a result/web source that is dead live, has no Wayback snapshot and nothing held here — "
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
    nm_with = [c for c in NM if set_for(c) or has_role(c, "judge_page")]
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
    pidx = ["<h1>Problem holdings by contest</h1>",
            f'<p class="muted">What the <b>ICPC Problem Archive</b> holds, per contest: of {ptot["n"]} contests that ran, '
            f'{ptot["rec"]} ({round(100 * ptot["rec"] / ptot["n"])}%) have their problem holdings recorded, '
            f'{ptot["repo"]} have a repo in the archive, {ptot["statement_full"]} have every statement, '
            f'{ptot["data_full"]} every test-data set, {ptot["solutions_full"]} every solution and '
            f'{ptot["package_full"]} a complete package for every problem; {ptot["nprob"]} problems counted in all. '
            f'{ptot["judges"]} contests link to an online judge where the problems can be solved. '
            f'{len(contests_listed)} contests have a per-problem list ({len(sets_listed)} problem sets, {n_problems_listed} problems; '
            f'{len(PROBLEMS)} distinct problems) — <a href="../problem/index.html">all listed problems</a> · '
            f'<a href="../problemset/index.html">all {len(SETS)} problem sets</a> · <a href="../judge/index.html">online judges</a>.</p>',
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
    (out / "problems" / "index.html").write_text(page("Problem holdings by contest", "\n".join(pidx), rel))

    stub(out / "problems" / "list.html", "../problem/index.html")
    (out / "problems" / "problems.json").write_text(json.dumps(
        {"generated": datetime.date.today().isoformat(), "sets": SETS, "judges": JUDGES}, ensure_ascii=False))

    # ---- problem index: every listed problem, filterable ----
    def first_contest(doc):
        for m in doc["contests"]:
            if m["contest"] in contests:
                return contests[m["contest"]]
        return {}

    plist = ["<h1>Problems</h1>",
             f'<p class="muted">{n_problems_listed} problems from {len(sets_listed)} problem sets used by {len(contests_listed)} contests '
             f'({len(PROBLEMS)} distinct problems; a problem reused across sets appears once per set). '
             f'See also <a href="../problems/index.html">holdings by contest</a> (coverage of the whole archive, including the {len(SETS) - len(sets_listed)} sets '
             f'without a per-problem list) · <a href="../problemset/index.html">all sets</a> · <a href="../judge/index.html">online judges</a>. '
             'Filter by judge, held material, season or region; the box matches any column.</p>',
             HAVE_LEGEND,
             '<div class="tablewrap"><table class="flt"><tr><th>contest</th><th>set</th><th data-f>season</th><th data-f>region</th><th>#</th><th>problem</th>'
             '<th data-f>held</th><th data-f>solve online</th><th>notes</th></tr>']
    for sid in sorted(sets_listed):
        doc = SETS[sid]
        members = [m["contest"] for m in doc["contests"]]
        with_letters = [m for m in members if set_letters(doc, m)]
        fc = first_contest(doc)
        region = SERIES_REGION.get(series_of.get(fc.get("id"), ""), "non-mainline" if not fc else "—")
        for L, p in set_problems_in_order(doc):
            if len(with_letters) > 1:
                ls = [letter_of(doc, m, p["id"]) for m in with_letters]
                L = " / ".join(x or "?" for x in ls) if len(set(ls)) > 1 else ls[0]
            private = p.get("status") == "private"
            have = [] if private else [k for k in (p.get("have") or [])]
            hv = " ".join(have) if "have" in p and not private else ("private" if private else "unrecorded")
            judges = " ".join(sorted({j["judge"] for j in p.get("judges") or []})) if not private else ""
            plist.append(f'<tr><td class="wrap">{", ".join(contest_ref(m, rel) for m in members)}</td><td class="small">{set_link(sid, rel)}</td>'
                         f'<td data-v="{fc.get("season", "")}">{link_season(fc.get("season"), rel)}</td><td class="small muted">{esc(region)}</td>'
                         f'<td class="letter">{esc(L or "?")}</td><td class="wrap">{problem_name_cell(p, rel)}</td>'
                         + ("<td data-vs=\"private\"></td><td></td><td></td>" if private else
                            f'<td data-vs="{esc(hv)}">{problem_have_marks(p)}</td><td data-vs="{esc(judges or "none")}" class="small">{problem_judge_links(p)}</td>'
                            f'<td class="wrap small muted">{esc(p.get("notes", ""))}</td>') + "</tr>")
    plist.append("</table></div>")
    (out / "problem" / "index.html").write_text(page("Problems", "\n".join(plist), rel))

    # ---- problem set index, set pages, problem pages ----
    srows = []
    for sid in sorted(SETS):
        doc = SETS[sid]
        members = [m["contest"] for m in doc["contests"]]
        n_list = len(doc.get("problems") or [])
        fc = first_contest(doc)
        region = SERIES_REGION.get(series_of.get(fc.get("id"), ""), "non-mainline" if not fc else "—")
        full = " ".join(w for k, _l, w in HELD_KINDS if doc.get(k) == "full")
        srows.append(f'<tr><td>{set_link(sid, rel)}</td><td class="wrap small">{esc(doc.get("name", ""))}</td>'
                     f'<td class="wrap">{", ".join(contest_ref(m, rel) for m in members)}</td>'
                     f'<td data-v="{fc.get("season", "")}">{link_season(fc.get("season"), rel)}</td><td class="small muted">{esc(region)}</td>'
                     f'<td class="num">{doc.get("count", "")}</td><td class="num" data-v="{"yes" if n_list else "no"}">{n_list or ""}</td>'
                     f'<td data-vs="{esc(full or "none")}">{held_marks(doc)}</td><td>{repo_link(doc)}</td>'
                     f'<td class="wrap small muted">{esc(doc.get("notes", ""))}</td></tr>')
    n_shared = sum(1 for d in SETS.values() if len(d["contests"]) > 1)
    sidx = ["<h1>Problem sets</h1>",
            f'<p class="muted">{len(SETS)} problem sets: a set is the object a contest used — one set can serve several contests '
            f'({n_shared} shared sets, e.g. NCPC + UKIEPC). {len(sets_listed)} sets have a per-problem list ({n_problems_listed} rows, '
            f'{len(PROBLEMS)} distinct problems); the rest record only what the ICPC Problem Archive holds. '
            f'See also <a href="../problems/index.html">holdings by contest</a>, <a href="../problem/index.html">every listed problem</a> and '
            f'<a href="../judge/index.html">online judges</a>. Filter by region, season, whether problems are listed, or the kinds held in full.</p>',
            HELD_LEGEND,
            '<div class="tablewrap"><table class="flt"><tr><th>set</th><th>name</th><th>used by</th><th data-f>season</th><th data-f>region</th><th class="num">#</th>'
            '<th class="num" data-f title="problems listed">listed</th><th data-f title="kinds held for every problem">held</th><th>archive repo</th><th>notes</th></tr>'
            + "\n".join(srows) + "</table></div>"]
    (out / "problemset" / "index.html").write_text(page("Problem sets", "\n".join(sidx), rel))
    stub(out / "problemsets" / "index.html", "../problemset/index.html")
    for sid, doc in SETS.items():
        (out / "problemset" / f"{sid}.html").write_text(problemset_page(sid, doc, rel))
    for pid, ent in PROBLEMS.items():
        (out / "problem" / f"{pid}.html").write_text(problem_page(pid, ent, rel))

    # ---- judges ----
    n_prob_links = defaultdict(set)   # judge -> problem ids linking to it
    n_page_links = defaultdict(set)   # judge -> contests with a judge_page source
    for pid, ent in PROBLEMS.items():
        for _s, r in ent["rows"]:
            for j in r.get("judges") or []:
                n_prob_links[j["judge"]].add(pid)
    for c in list(contests.values()) + NM:
        for s in by_role(c, "judge_page"):
            n_page_links[s.get("judge") or "judge"].add(c["id"])
    jrows = []
    for jid, j in JUDGES.items():
        st = esc(j.get("status", ""))
        if j.get("closed"):
            st += f' {esc(j["closed"])}'
        jrows.append(f'<tr><td><a href="{esc(jid)}.html">{esc(jid)}</a></td><td><a href="{esc(j["url"])}">{esc(j.get("name", jid))}</a></td>'
                     f'<td><span class="chip">{st}</span></td>'
                     f'<td class="num">{len(n_prob_links.get(jid, ()))}</td><td class="num">{len(n_page_links.get(jid, ()))}</td>'
                     f'<td class="small">{"statements" if j.get("statements") else ""}{" · " if j.get("statements") and j.get("submissions") else ""}{"submissions" if j.get("submissions") else ""}</td>'
                     f'<td class="wrap small muted">{esc(j.get("notes", ""))}</td></tr>')
        (out / "judge" / f"{jid}.html").write_text(judge_page(jid, j, contests, NM, rel))
    unknown = [x for x in sorted(set(n_prob_links) | set(n_page_links)) if x not in JUDGES]
    jidx = ["<h1>Online judges</h1>",
            f'<p class="muted">The {len(JUDGES)} judges in <a href="{REPO_URL}judges.yaml">judges.yaml</a>, the registry every judge link '
            'refers to: per-problem links (<i>problems</i>) and contest-level judge pages (<i>contest pages</i>, sources with role judge_page). '
            'A closed judge\'s pages survive only in Wayback snapshots taken before the closing date.</p>',
            '<div class="tablewrap"><table><tr><th>id</th><th>judge</th><th>status</th><th class="num">problems</th>'
            '<th class="num">contest pages</th><th>offers</th><th>notes</th></tr>' + "\n".join(jrows) + "</table></div>"]
    if unknown:
        jidx.append('<p class="small muted">Judge ids used but not in the registry: ' + ", ".join(esc(x) for x in unknown) + "</p>")
    (out / "judge" / "index.html").write_text(page("Online judges", "\n".join(jidx), rel))
    stub(out / "judges" / "index.html", "../judge/index.html")
    print(f"  problem sets: {len(SETS)} set pages, {len(PROBLEMS)} problem pages, {len(JUDGES)} judges")

    # ---- locations ----
    for nid in LOC:
        (out / "location" / f"{nid}.html").write_text(location_page(nid, rel))
    (out / "location" / "index.html").write_text(location_index(rel))
    print(f"  locations: {len(LOC)} pages")

    # ---- non-mainline registry ----
    nrows = []
    for c in sorted(NM, key=lambda c: c["id"]):
        pb = set_for(c)
        srcs = " · ".join(f'<a href="{esc(s["url"])}">{esc(role_label(s["roles"][0]))}</a>' for s in sources(c))
        nrows.append(f'<tr><td>{esc(c["id"])}</td><td class="wrap">{esc(c.get("name", ""))}</td><td>{esc(c.get("date", ""))}</td>'
                     f'<td class="wrap small">{esc(c.get("reason", ""))}</td><td class="small">{srcs}</td>'
                     f'<td>{set_link(pb["id"], "") if pb else ""}</td><td class="small">{cms_cell(c)}</td></tr>')
    (out / "non-mainline.html").write_text(page("Non-mainline registry", "<h1>Non-mainline registry</h1>"
        f'<p class="muted">{len(NM)} real contests outside the ICPC advancement hierarchy (university opens and the like), kept for reference in '
        f'<a href="{REPO_URL}registry/non-mainline.yaml">registry/non-mainline.yaml</a>. They are not catalogue members and have no contest page; '
        'their problem sets, when recorded, do. The other appendix is the <a href="cms.html">CMS id ledger</a>.</p>'
        '<div class="tablewrap"><table><tr><th>id</th><th>name</th><th>date</th><th>reason</th><th>sources</th><th>problem set</th><th>CMS id</th></tr>'
        + "\n".join(nrows) + "</table></div>", ""))

    # ---- machine-readable dump ----
    dump = {}
    for sid, doc in series_docs.items():
        d2 = dict(doc)
        d2["series"] = {**doc["series"], "region": SERIES_REGION.get(sid, "Other")}
        dump[sid] = d2
    (out / "catalogue.json").write_text(json.dumps(
        {"generated": datetime.date.today().isoformat(), "series": dump}, ensure_ascii=False))

    # ---- search + landing ----
    def hosts_of(c):
        """Hosts of the website and result sources (what people search by)."""
        hs = set()
        for s in sources(c):
            if "web" in s["roles"] or any(r in s["roles"] for r in RESULT_KINDS):
                hs.add(re.sub(r"^https?://(www\.)?", "", s["url"]).split("/")[0])
        return sorted(hs)

    search = [{"t": "c", "id": cid, "name": c.get("name"), "date": c.get("date"), "series": series_of[cid],
               "cms": [str(i) for i in (c.get("cms_ids") or [])], "hosts": hosts_of(c),
               "region": SERIES_REGION.get(series_of[cid], ""),
               "problems": [p["name"] for p in set_for(c).get("problems") or []] or None}
              for cid, c in sorted(contests.items())]
    search += [{"t": "r", "id": sid, "name": doc["series"].get("name"), "region": SERIES_REGION.get(sid, ""),
                "aliases": doc["series"].get("aliases") or None, "extra": f"{len(doc['contests'])} editions"} for sid, doc in series_docs.items()]
    search += [{"t": "s", "id": sid, "name": doc.get("name"), "extra": "used by " + ", ".join(m["contest"] for m in doc["contests"]),
                "problems": [p["name"] for p in doc.get("problems") or []] or None} for sid, doc in SETS.items()]
    search += [{"t": "p", "id": pid, "name": ent["rows"][0][1]["name"], "aliases": [r.get("uuid") for _s, r in ent["rows"] if r.get("uuid")] or None,
                "extra": ", ".join(dict.fromkeys(cid for _s, cid, _L in ent["apps"]))} for pid, ent in PROBLEMS.items()]
    search += [{"t": "l", "id": nid, "name": n["name"], "aliases": n.get("aliases") or None,
                "extra": f'{n["type"]} · {" › ".join(x["name"] for x in location_chain(LOC, nid)[1:])} · {loc_count(nid)} contests'} for nid, n in LOC.items()]
    search += [{"t": "j", "id": jid, "name": j.get("name"), "extra": j.get("status")} for jid, j in JUDGES.items()]
    (out / "search.json").write_text(json.dumps(search, ensure_ascii=False))

    ran = sum(1 for c in contests.values() if c.get("status") != "upcoming")
    latest = max((s for s in BY_SEASON if any(contests[m].get("status") != "upcoming" for m in BY_SEASON[s])), default=None)
    tree_html = ""
    if latest:
        tree, unplaced = season_tree(latest, BY_SEASON[latest], "")
        tree_html = (f'<h2>Season {latest - 1}–{latest}</h2>{stats_strip(season_stats(BY_SEASON[latest]))}'
                     f'<p class="small muted">The latest season with contests that ran — {link_season(latest, "", "full season page")}'
                     + (f" · {len(unplaced)} free-floating" if unplaced else "") + "</p>" + MARK_LEGEND + tree)
    n_src = len(RES.locs)
    n_caps = sum(len(R.get("captures") or []) for L in RES.locs.values() for R in L["resources"].values())
    landing = f"""<h1>ICPC contest archive</h1>
<p>A catalogue of the mainline ICPC contest hierarchy through history — every contest from which a team
could advance toward a World Finals — with where its results, websites and problems live: live, on the
Wayback Machine, and in this project's own archive.</p>
<div class="stats">
<div><b>{len(BY_SEASON)}</b> <a href="season/index.html">seasons</a></div>
<div><b>{len(series_docs)}</b> <a href="series/index.html">series</a></div>
<div><b>{ran}</b> <a href="contest/index.html">contests</a> <span class="small muted">+{len(contests) - ran} upcoming</span></div>
<div><b>{len(SETS)}</b> <a href="problemset/index.html">problem sets</a> <span class="small muted">{len(PROBLEMS)} <a href="problem/index.html">problems</a> listed</span></div>
<div><b>{n_src}</b> <a href="source/index.html">sources</a> <span class="small muted">{n_caps} captures</span></div>
<div><b>{len(JUDGES)}</b> <a href="judge/index.html">judges</a></div>
<div><b>{sum(1 for n in LOC.values() if n["type"] == "country")}</b> countries <span class="small muted">{len(LOC)} <a href="location/index.html">locations</a></span></div>
<div><b>{len(website_of)}</b> websites archived</div>
</div>
<p><input id="q" placeholder="search… (contest, series, problem set, problem, location, judge; id, name, host, CMS id, alias)"
   autocomplete="off"></p>
<div class="tablewrap"><table id="hits"></table></div>
{tree_html}
<h2>Start somewhere</h2>
<p>{link_contest('wf-2025', '')} · <a href="series/wf.html">World Finals series</a> ·
<a href="grid.html">the grid</a> (every contest, one screen) · <a href="coverage.html">collection coverage</a> ·
<a href="wanted.html">most wanted</a> · <a href="cms.html">CMS id ledger</a> · <a href="non-mainline.html">non-mainline registry</a> ·
<a href="catalogue.json">catalogue.json</a> · <a href="about.html">about this site &amp; the local archive</a></p>
<p class="small muted">Data: <a href="https://github.com/icpc-contest-archive/contests">
icpc-contest-archive/contests</a>. Corrections welcome.</p>
<script>const REL='';{SEARCH_JS}</script>"""
    (out / "index.html").write_text(page("ICPC contest archive", landing, ""))

    n_sites = len(website_of)
    n_raw = len(archived_by_contest)
    about = f"""<h1>About</h1>
<h2>What is here</h2>
<p>The catalogue is a graph of objects, each with its own page: <b><a href="season/index.html">seasons</a></b>
(first regional to World Finals, with the advancement tree), <b><a href="series/index.html">series</a></b> (a line of
editions under one name, renamings recorded as lineage), <b><a href="contest/index.html">contests</a></b> (the
edition: date, sites, what it advances to and who feeds it, CMS ids, its sources and problem set),
<b><a href="source/index.html">sources</a></b> (every catalogued address), <b><a href="problemset/index.html">problem
sets</a></b> and <b><a href="problem/index.html">problems</a></b> (what the ICPC Problem Archive holds),
<b><a href="judge/index.html">online judges</a></b> and <b><a href="location/index.html">locations</a></b> (one tree:
country › region › city › institution). The <a href="coverage.html">coverage</a> pages, the <a href="grid.html">grid</a>,
the <a href="wanted.html">wanted list</a> and the two appendices (<a href="cms.html">CMS id ledger</a>,
<a href="non-mainline.html">non-mainline registry</a>) are views over the same data. Every list page filters client-side
on its columns and sorts by clicking a header.</p>
<h2>Words</h2>
<p>A <b>source</b> is an address (URL) the catalogue knows, with the <b>roles</b> it serves (website, scoreboard, frozen
scoreboard, standings, rankings, ICPC standings, problem set, judge page, teams) and a <b>health</b> (live, changed,
replaced, dead, unknown — the verdict of the last live check, hover any chip for the rule). A <b>snapshot</b> is that
address at one time: a Wayback snapshot, or our own live fetch. A <b>capture</b> is our stored copy of a snapshot, with
provenance (what was fetched, when, sha256, size, type). The catalogue holds sources; the archive holds captures. Links on a
result row: <i>live</i> = the address as is; <i>wayback</i> = pinned to the time meant (as_of) when known, the calendar
otherwise; <i>archived (time)</i> = our capture on the public replay; <i>raw</i> = the capture file untouched. A contest
<i>advances to</i> its parent; its <i>feeders</i> are the contests whose parent it is. The year in a contest id is the
season label (fall regionals carry the season-start year, finals the season-end year), not the date — pages always show
both. Nothing about a contest's problems is public before it has run; problems kept private afterwards show name and uuid
only. Full definitions: <a href="https://github.com/icpc-contest-archive/contests/blob/main/DEFINITIONS.md">DEFINITIONS.md</a>.</p>
<h2>Local archive</h2>
<p>Besides the result pages published on the replay site, this project holds a much larger
private archive: raw captures of every result page and full crawls of
<b>{n_sites}</b> contest websites ({n_raw} contests with raw captures in all). That is far too
big for GitHub Pages, so it is not published yet.</p>
<p>Links marked <a class="local" href="{LOCAL_BASE}/" title="{LOCAL_TITLE}">like this</a>
point at a small server on <b>your own machine</b> (<code>{LOCAL_BASE or "this host"}</code>).
They work only if you have the <code>archive</code> repository checked out next to
<code>contests</code> and the server running; for everyone else they give
"unable to connect". Nothing is probed in the background — a link is just a link.</p>
<pre><code># in your checkout of the contests repo (archive checked out alongside it)
python3 tools/index_websites.py     # after new site crawls
python3 tools/serve.py              # rebuilds the site with local links, serves on 127.0.0.1:8123</code></pre>
<p>Then browse the catalogue at <code>http://127.0.0.1:8123/</code> — the same pages as the
public site, with every local link live. The public site's local links point at the same
address, so they work in any browser while the server is up.</p>
<ul>
<li><b>archived site</b> / <b>play back</b> (on a contest's website line): the crawled website, played back
page by page from the capture with in-site links kept inside the capture. Links to pages that
were not captured go to the Wayback Machine (for crawls taken from a snapshot) or to the live
site. The <i>wayback</i> link next to it is pinned to the exact snapshot the crawl used.</li>
<li><b>raw</b> (on a result row or a capture row): the captured file exactly as fetched, no banner, no rewriting.</li>
<li><b>raw files</b>: the contest's folder in the archive repository — every capture as stored
(hashed filenames, manifests), results and website alike; for inspection, not for reading.</li>
</ul>
<p class="small muted">When the archive gets a public home the only change is the host these
links point at (<code>LOCAL_ARCHIVE_BASE</code> in <code>tools/build_site.py</code>).</p>"""
    (out / "about.html").write_text(page("About", about, ""))
    stub(out / "local.html", "about.html")

    # ---- source pages + redirect stubs from the old locator/ addresses ----
    nsrc = 0
    if RES.locs:
        rel2 = "../../"
        for k, L in RES.locs.items():
            d = out / "source" / k
            d.mkdir(exist_ok=True)
            (d / "index.html").write_text(source_page(k, L, rel2))
            nsrc += 1
            od = out / "locator" / k
            od.mkdir(parents=True, exist_ok=True)
            stub(od / "index.html", f"../../source/{k}/index.html")
            for ts in L["resources"]:
                stub(od / f"{ts}.html", f"../../source/{k}/index.html#s-{ts}")
        (out / "source" / "index.html").write_text(source_index("../"))
        role_pages(out, contests)
        for k in ROLE_PAGES + ["index"]:
            tgt = f"../source/by-role/{k}.html" if k != "index" else "../source/index.html"
            stub(out / "resources" / f"{k}.html", tgt)
            stub(out / "urls" / f"{k}.html", tgt)
        print(f"  {nsrc} source pages")

    n = len(list(out.rglob("*.html")))
    n_stubs = sum(1 for p in out.rglob("*.html") if p.parts[len(out.parts)] in ("locator", "resources", "urls", "problemsets", "judges") or p.name in ("seasons.html", "local.html", "list.html"))
    print(f"site: {n} pages ({n - n_stubs} content pages, {n_stubs} redirect stubs) -> {out} in {time.time() - t0:.1f}s")


def check_links(out: Path) -> int:
    """Every relative href ending in .html or / (or with a #anchor) must resolve to a built file."""
    href_re = re.compile(r'href="([^"]+)"')
    files = list(out.rglob("*.html"))
    anchors_cache: dict = {}

    def anchors(p: Path) -> set:
        if p not in anchors_cache:
            anchors_cache[p] = set(re.findall(r' id="([^"]+)"', p.read_text()))
        return anchors_cache[p]
    broken = []
    for f in files:
        txt = f.read_text()
        for h in href_re.findall(txt):
            if re.match(r"^(https?:|mailto:|#|javascript:)", h) or h.startswith(LOCAL_BASE + "/") or h.startswith("/") or "${" in h:
                continue
            path, _, frag = h.partition("#")
            path = path.split("?")[0]
            if not (path.endswith(".html") or path.endswith("/") or path.endswith(".json")):
                continue
            tgt = (f.parent / html.unescape(path)).resolve()
            if path.endswith("/"):
                tgt = tgt / "index.html"
            if not tgt.exists():
                broken.append((str(f.relative_to(out)), h))
            elif frag and not frag.startswith("f:") and tgt.suffix == ".html" and frag not in anchors(tgt):
                broken.append((str(f.relative_to(out)), h + " (anchor)"))
    for f, h in broken[:30]:
        print(f"  broken: {f} -> {h}")
    print(f"link check: {len(files)} pages, {len(broken)} broken internal links")
    return len(broken)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "site"))
    ap.add_argument("--check-links", action="store_true", help="verify every relative link in the built site resolves")
    a = ap.parse_args()
    build(Path(a.out))
    if a.check_links:
        sys.exit(1 if check_links(Path(a.out)) else 0)
