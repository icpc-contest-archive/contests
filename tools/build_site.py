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
from resources import fmt_time, label as res_label, unwrap, wayback_link  # noqa: E402
import site_resources  # noqa: E402

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

CHAMPIONSHIPS = {"nac", "awc", "euc", "apc", "lac", "aec", "nadc"}
# World regions: the top level of the modern ICPC hierarchy (finals + championships
# get their own bucket). Historical series are filed under today's closest region;
# judgment calls: ukraine + turkey under Europe (EUC/SEERC lineage).
REGION_GROUPS = {
    "World Finals & championships": ["wf", "nac", "euc", "apc", "aec", "awc", "lac", "nadc"],
    "North America": ["socal","naq","nena","nena-atlantic","nena-central","nena-east","nena-north",
        "nena-west","ecna","scusa","rmc","lethbridge","gny","mcpc","seusa","mausa","pacnw","east-na",
        "south-na","alberta","ncna"],
    "Latin America": ["brazil","mexico","caribbean","central-america","south-america",
        "south-america-north","south-america-south","cuba"],
    "Europe": ["poland","hungary","slovenia","turkey","ukraine","cerc","swerc","nwerc","bapc",
        "bapc-prelims","germany","croatia","romania","bulgaria","greece","cyprus","nordic","sweden",
        "norway","ukiepc","ctuo","erc","werc","mcerc","seerc"],
    "Northern Eurasia": ["neerc","nerc","south-russia","central-russia","north-russia",
        "west-siberia","east-siberia","far-east-russia","urals","moscow","taurida","west-neerc",
        "armenia","azerbaijan","georgia","kazakhstan","kyrgyzstan","uzbekistan"],
    "Africa & Arab": ["acpc","egypt","jordan","syria","lebanon","kuwait","bahrain","oman","qatar",
        "saudi-arabia","palestine","morocco","tunisia","algeria","sudan","south-africa","angola",
        "benin","burkina-faso","ethiopia","ivory-coast","nigeria","senegal","togo"],
    "Asia West": ["tehran","pakistan","kabul","dhaka","kanpur","amritapuri","kharagpur","kolkata",
        "gwalior","chennai","coimbatore","bombay","mathura","india","gwalior-kanpur",
        "kolkata-kanpur","kolkata-roorkee","gwalior-pune"],
    "Asia Pacific": ["mongolia-national","philippines-national",  # feeders with unlinked parents
        "japan","korea","taiwan","singapore","manila","jakarta","kuala-lumpur",
        "thailand","vietnam","yangon","south-pacific","south-pacific-west","south-pacific-central",
        "south-pacific-east","south-pacific-division","nzpc","australia"],
    "Asia East": ["hong-kong","macau","pyongyang","beijing","shanghai","chengdu","hangzhou","xian",
        "harbin","wuhan","fuzhou","hefei","nanjing","dalian","changchun","changsha","jinan","jinhua",
        "jiaozuo","kunming","mudanjiang","nanchang","nanning","ningbo","qingdao","shenyang",
        "tianjin","urumqi","xuzhou","yinchuan","anshan","guangzhou"],
}
SERIES_REGION = {s: g for g, ss in REGION_GROUPS.items() for s in ss}
# a feeder whose parent is a championship belongs to that championship's region
CHAMPIONSHIP_REGION = {"nac": "North America", "nadc": "North America", "euc": "Europe",
                       "apc": "Asia Pacific", "awc": "Asia West", "aec": "Asia East",
                       "lac": "Latin America"}


def derive_regions(series_docs: dict, contests: dict) -> None:
    """Series not in REGION_GROUPS take the region of the series they advance into
    (walking parent chains from their latest contest); the table stays the override.
    Feeder layers (national/first-phase/sub-regional series) then follow their regional
    automatically instead of needing a table entry each."""
    for _round in range(6):
        changed = False
        for sid, doc in series_docs.items():
            if sid in SERIES_REGION:
                continue
            for c in reversed(doc["contests"]):
                parents = c.get("parent") if isinstance(c.get("parent"), list) else [c.get("parent")]
                for pid in parents:
                    pc = contests.get(pid) if pid else None
                    if not pc:
                        continue
                    pser = pid.rsplit("-", 1)[0]
                    reg = CHAMPIONSHIP_REGION.get(pser) or SERIES_REGION.get(pser)
                    if reg and pser != "wf" and reg != "World Finals & championships":
                        SERIES_REGION[sid] = reg
                        changed = True
                        break
                if sid in SERIES_REGION:
                    break
        if not changed:
            break

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


def locators(v):
    """`web`/`problemset`-style fields: string or {url, as_of} or a list of either
    -> list of (url, as_of|None)."""
    out = []
    for w in refs(v):
        if isinstance(w, dict):
            out.append((w["url"], w.get("as_of")))
        else:
            out.append((w, None))
    return out


def page(title: str, body: str, rel: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body>
<nav class="top"><div><a href="{rel}index.html">ICPC contest archive</a>
<a href="{rel}grid.html">grid</a> <a href="{rel}series/index.html">series</a>
<a href="{rel}seasons.html">seasons</a> <a href="{rel}coverage.html">coverage</a>
<a href="{rel}resources/index.html">resources</a> <a href="{rel}problems/index.html">problems</a> <a href="{rel}wanted.html">wanted</a>
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


def ist_locator(c):
    """icpc_standings as (url, entry-dict) whether it is a bare url or a locator object."""
    v = c.get("icpc_standings")
    if not v:
        return None, None
    return (v["url"], v) if isinstance(v, dict) else (v, {"url": v})


def best_tier(c) -> str:
    """The ONE tier ladder used by the grid, coverage, wanted list and marks:
    scoreboard > frozen_scoreboard > standings > rankings > icpc > none."""
    res = c.get("results", {})
    for k in ("scoreboard", "frozen_scoreboard", "standings", "rankings"):
        if res.get(k):
            return k
    return "icpc" if c.get("icpc_standings") else "none"


def web_state(c) -> str:
    """'link' (a website locator), 'none' (confirmed none: web: null), 'unknown' (not researched)."""
    if c.get("web"):
        return "link"
    return "none" if "web" in c else "unknown"


TIERS = (("scoreboard", "S"), ("frozen_scoreboard", "F"),
         ("standings", "St"), ("rankings", "R"))
MARK_LEGEND = ('<p class="small muted"><b>S</b> scoreboard · <b>F</b> frozen scoreboard · '
               '<b>St</b> standings · <b>R</b> rankings · <b>I</b> ICPC standings (lowest tier) — '
               '<span class="mark m-arch">filled</span> = archived copy held, '
               '<span class="mark m-live">outlined</span> = live link only (not yet archived)</p>')


def tier_marks(c):
    """One styled marker per artifact tier; preservation state = style, not a letter."""
    res = c.get("results", {})
    out = []
    for key, letter in TIERS:
        entries = res.get(key)
        if not entries:
            continue
        arch = next((e for e in entries if e.get("archived")
                     and not (capture_info.get(e["archived"]) or {}).get("content_caveat")), None)
        kind = key.replace("_", " ")
        if arch:
            out.append(f'<a class="mark m-arch" href="{REPLAY_BASE}/a/{esc(arch["archived"])}" '
                       f'title="{kind} — archived copy">{letter}</a>')
        else:
            out.append(f'<a class="mark m-live" href="{esc(entries[0]["url"])}" '
                       f'title="{kind} — live link only, not yet archived">{letter}</a>')
    url, e = ist_locator(c)
    if url:
        if e.get("archived") and not (capture_info.get(e["archived"]) or {}).get("content_caveat"):
            out.append(f'<a class="mark m-arch m-ist" href="{REPLAY_BASE}/a/{esc(e["archived"])}" '
                       f'title="ICPC standings — archived copy (rendered from the API dump)">I</a>')
        else:
            out.append(f'<a class="mark m-ist" href="{esc(url)}" '
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
    """The locator's health, one way everywhere: catalogue url_state if the entry has one,
    else the resource graph's verdict (web/mirror/icpc locators have no field for it)."""
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
    urls = [e["url"] for lst in (c.get("results") or {}).values() for e in lst]
    urls += [w for w, _ in locators(c.get("web"))]
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
    res = c.get("results") or {}
    held = any(e.get("archived") and not (capture_info.get(e["archived"]) or {}).get("content_caveat")
               for lst in res.values() for e in lst)
    _u, ie = ist_locator(c)
    ist_held = bool(ie and ie.get("archived") and not (capture_info.get(ie["archived"]) or {}).get("content_caveat"))
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
        baked = ("a/" + e["archived"]) if e.get("archived") else replay_lookup.get((cid, url))
        cap = capture_info.get(e.get("archived") or "")
        when = fmt_time(cap_time(cap)) if cap else ""
        if baked:
            matched_paths.add(baked)
            parts.append(f'<a href="{REPLAY_BASE}/{esc(baked)}" title="our copy of this resource">'
                         f'archived{" (" + when + ")" if when else ""}</a>')
        if e.get("archived"):
            parts.append(local_link("archive/" + e["archived"], "raw"))
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
    for n, (w, as_of) in enumerate(locators(c.get("web"))):
        host = re.sub(r"^https?://(www\.)?", "", w).rstrip("/")
        host = host if len(host) <= 40 else host[:39] + "…"
        wb_ts = (site.get("wayback_timestamp") if site and n == 0 else None) or as_of
        bit = (f'<a href="{esc(w)}" title="{esc(res_label(w, as_of, 200))}">{esc(host)}</a>{health_chip(w)} '
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
PROBLEM_FILES: dict = {}  # contest id -> parsed problems/<id>.yaml
REPLAY_LOOKUP: dict = {}  # (contest, url) -> baked replay path, filled by build()
HELD_KINDS = (("statement", "St", "statements"), ("data", "D", "test data"),
              ("solutions", "So", "solutions"), ("package", "P", "complete packages"))
JUDGE_LABEL = {"kattis": "Kattis", "livearchive": "Live Archive", "baekjoon": "Baekjoon",
               "codeforces": "Codeforces"}
HELD_LEGEND = ('<p class="small muted"><b>St</b> statements · <b>D</b> test data · <b>So</b> solutions · '
               '<b>P</b> complete problem packages — <span class="mark h-full">filled</span> = held for every '
               'problem, <span class="mark h-part">outlined</span> = for some (hover for the number), '
               '<span class="mark h-none">grey</span> = none</p>')


def load_problem_files():
    PROBLEM_FILES.clear()
    pdir = ROOT / "problems"
    if pdir.exists():
        for f in sorted(pdir.glob("*.yaml")):
            PROBLEM_FILES[f.stem] = yaml.safe_load(f.read_text())


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


def judge_links(j: dict | None, sep: str = " · ") -> str:
    parts = []
    for key, v in (j or {}).items():
        locs = v if isinstance(v, list) else [v]
        lab = JUDGE_LABEL.get(key, key)
        for i, loc in enumerate(locs):
            url = loc["url"] if isinstance(loc, dict) else loc
            as_of = loc.get("as_of") if isinstance(loc, dict) else None
            href = wayback_link(url, as_of) if as_of else url
            parts.append(f'<a href="{esc(href)}" title="{esc(res_label(url, as_of, 200))}">{esc(lab)}'
                         + (f" {i + 1}" if len(locs) > 1 else "") + ("</a> <span class=\"small muted\">(wayback)</span>" if as_of else "</a>"))
    return sep.join(parts)


def problem_have_marks(p: dict) -> str:
    have = set(p.get("have") or [])
    out = []
    for key, letter, what in (("statement", "St", "statement"), ("data", "D", "test data"),
                              ("input_validator", "IV", "input validator"), ("output_validator", "OV", "output validator"),
                              ("solutions", "So", "solutions"), ("package", "P", "complete package")):
        cls = "h-full" if key in have else "h-none"
        out.append(f'<span class="mark {cls}" title="{what}: {"held" if key in have else "not held"}">{letter}</span>')
    return "".join(out)


def problems_section(cid: str, c: dict, rel: str) -> list[str]:
    """The Problems block of a contest page: holdings summary, judge links, per-problem table."""
    pb = c.get("problems")
    pf = PROBLEM_FILES.get(cid)
    if not pb and not pf and not c.get("problemset"):
        return []
    pb = pb or {}
    b = ['<h2 id="problems">Problems</h2>', '<dl class="fields">']
    if pb.get("count"):
        b.append(f"<dt>problems</dt><dd>{pb['count']}</dd>")
    if pb.get("repo"):
        b.append(f"<dt>archive repo</dt><dd>{repo_link(pb)} <span class=\"small muted\">(icpc-problem-archive, private)</span></dd>")
    if any(pb.get(k) for k, *_ in HELD_KINDS):
        words = []
        for key, _l, what in HELD_KINDS:
            st = pb.get(key)
            if not st:
                continue
            n = (pb.get("counts") or {}).get(key)
            words.append(f'<span class="chip">{what}: {st}' + (f" ({n}/{pb.get('count')})" if st == "partial" and n is not None else "") + "</span>")
        b.append("<dt>held</dt><dd>" + " ".join(words) + "</dd>")
    for w, as_of in locators(c.get("problemset")):
        parts = [f'<a href="{esc(w)}">{esc(res_label(w, as_of, 80))}</a>',
                 f'<a href="{esc(wayback_link(w, as_of))}">wayback</a>']
        baked = REPLAY_LOOKUP.get((cid, w))
        if baked:
            parts.append(f'<a href="{REPLAY_BASE}/{esc(baked)}" title="our copy of this resource">archived</a>')
        if RES.locator_href(w, rel):
            parts.append(RES.label_link(w, as_of, rel, "resource"))
        b.append("<dt>problem set</dt><dd>" + " · ".join(parts) + health_chip(w) + "</dd>")
    if pb.get("judges"):
        b.append("<dt>solve online</dt><dd>" + judge_links(pb["judges"]) + "</dd>")
    if pb.get("notes"):
        b.append(f'<dt>notes</dt><dd class="wrap">{esc(pb["notes"])}</dd>')
    if pb.get("source"):
        b.append(f'<dt>source</dt><dd class="small muted">{esc(pb["source"])}</dd>')
    b.append("</dl>")
    if pf:
        b.append('<div class="tablewrap"><table><tr><th>#</th><th>problem</th><th>held</th><th>solve online</th><th>notes</th></tr>')
        for p in pf["problems"]:
            nm = esc(p["name"]) + (f' <span class="small muted">{esc(p["short_name"])}</span>' if p.get("short_name") else "")
            if p.get("status") == "private":
                nm += ' <span class="chip" title="kept private after the contest; name and uuid are public">private</span>'
            if p.get("uuid"):
                nm += f' <span class="small muted" title="problem package uuid">{esc(p["uuid"])}</span>'
            b.append(f'<tr><td class="letter">{esc(p["letter"])}</td><td class="wrap">{nm}</td>'
                     f'<td>{problem_have_marks(p)}</td><td>{judge_links(p.get("judges"))}</td>'
                     f'<td class="wrap small muted">{esc(p.get("notes", ""))}</td></tr>')
        b.append("</table></div>")
        b.append('<p class="small muted"><b>St</b> statement · <b>D</b> test data · <b>IV</b>/<b>OV</b> input/output '
                 'validator · <b>So</b> solutions · <b>P</b> complete package. '
                 f'Data: <a href="https://github.com/icpc-contest-archive/contests/blob/main/problems/{esc(cid)}.yaml">problems/{esc(cid)}.yaml</a>.</p>')
    return b


def build(out: Path):
    series_docs, contests, series_of, prev, children, subsets, aux = load()
    derive_regions(series_docs, contests)
    load_problem_files()
    out.mkdir(parents=True, exist_ok=True)
    (out / "contest").mkdir(exist_ok=True)
    (out / "series").mkdir(exist_ok=True)

    replay_lookup = REPLAY_LOOKUP
    replay_lookup.clear()
    replay_by_contest = defaultdict(list)
    if aux["replay-index"]:
        for e in aux["replay-index"]["pages"]:
            if e.get("url"):
                replay_lookup[(e["contest"], e["url"])] = e["path"]
            replay_by_contest[e["contest"]].append(e)
    archived_by_contest = defaultdict(list)
    if aux["archive-index"]:
        for e in aux["archive-index"]["captures"]:
            archived_by_contest[e["contest"]].append(e)
            capture_info[e["path"]] = e
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
        for n_w, (w, as_of) in enumerate(locators(c.get("web"))):
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
                     + health_chip(w) + "</dd>")
        if web_state(c) == "none":
            d.append('<dt>web</dt><dd class="muted">confirmed none (see notes)</dd>')
        if c.get("notes"):
            d.append(f'<dt>notes</dt><dd class="wrap">{esc(c["notes"])}</dd>')
        d.append("</dl>")
        b += d
        res = c.get("results", {})
        if res or replay_by_contest.get(cid) or c.get("icpc_standings"):
            b.append("<h2>Results</h2>")
            matched_paths: set = set()
            for key in ("scoreboard", "frozen_scoreboard", "standings", "rankings"):
                if key in res:
                    b += result_links(cid, key, res[key], replay_lookup, rel, matched_paths)
            url, e = ist_locator(c)
            if url:  # the ICPC-standings tier, rendered like any other result row
                b += result_links(cid, "icpc_standings", [e], replay_lookup, rel, matched_paths)
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
            n_arch = sum(1 for c in ran if any(e.get("archived") and not (capture_info.get(e["archived"]) or {}).get("content_caveat")
                                               for lst in (c.get("results") or {}).values() for e in lst))
            n_site = sum(1 for c in ran if c["id"] in website_of)
            n_lost = sum(1 for c in ran if any(not held for _u, _w, held in lost_locators(c)))
            parts = [f'{tiers[k]} {TIER_LABEL[k]}' for k in ("scoreboard", "frozen_scoreboard", "standings", "rankings", "icpc", "none") if tiers[k]]
            b.append(f'<p class="state small">{len(ran)} editions ran'
                     + (f' (+{len(doc["contests"]) - len(ran)} upcoming)' if len(doc["contests"]) > len(ran) else "")
                     + ": " + ", ".join(parts) + f" · {n_arch} with an archived result · {n_site} websites archived"
                     + (f' · <span class="chip">{n_lost} lost</span>' if n_lost else "") + "</p>")
        b.append(MARK_LEGEND)
        has_probs = any(c.get("problems") for c in doc["contests"])
        if has_probs:
            b.append(HELD_LEGEND)
        b.append('<div class="tablewrap"><table><tr><th>contest</th><th>date</th>'
                 "<th>advances to</th><th>results</th>" + ("<th>problems</th>" if has_probs else "")
                 + "<th>CMS id</th><th>website</th></tr>")
        for c in reversed(doc["contests"]):  # latest first
            pcell = ""
            if has_probs:
                pb = c.get("problems") or {}
                pcell = ("<td>" + (f'<span class="small muted">{pb["count"]}</span> ' if pb.get("count") else "")
                         + held_marks(pb) + "</td>") if pb else "<td></td>"
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
        res = c.get("results", {})
        sb = "scoreboard" in res
        fr = sb or "frozen_scoreboard" in res
        st = fr or "standings" in res
        rk = st or "rankings" in res
        any_ = rk or bool(c.get("icpc_standings"))
        return {"n": 1, "date": bool(c.get("date")),
                "sb": sb, "fr": fr, "st": st, "rk": rk, "any": any_,
                "arch": any(e.get("archived") and not (capture_info.get(e["archived"]) or {}).get("content_caveat")
                            for lst in res.values() for e in lst),
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
        for k, _l in TIERS:
            for e in c.get("results", {}).get(k, []):
                url_tables[k].append((cid, e))
        url, e = ist_locator(c)
        if url:
            url_tables["icpc_standings"].append((cid, e))
        for w, as_of in locators(c.get("web")):
            url_tables["web"].append((cid, {"url": w, "as_of": as_of}))
        for m in c.get("mirrors") or []:
            url_tables["mirror"].append((cid, m))
        for w, as_of in locators(c.get("problemset")):
            url_tables["problemset"].append((cid, {"url": w, "as_of": as_of}))
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
            if e.get("archived"):
                extras.append(f'<a class="small" href="{REPLAY_BASE}/a/{esc(e["archived"])}">'
                              'archived</a>')
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
    nm_with = [c for c in nm_doc["non_mainline_contests"] if c.get("problems")]
    rel = "../"

    def pflags(c):
        pb = c.get("problems") or {}
        f = {"n": 1, "rec": bool(pb), "repo": bool(pb.get("repo")), "count": bool(pb.get("count")),
             "judges": bool(pb.get("judges")), "file": c["id"] in PROBLEM_FILES,
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

    n_problems_listed = sum(len(d["problems"]) for d in PROBLEM_FILES.values())
    pidx = ["<h1>Problems</h1>",
            f'<p class="muted">What the <b>ICPC Problem Archive</b> holds, per contest: of {ptot["n"]} contests that ran, '
            f'{ptot["rec"]} ({round(100 * ptot["rec"] / ptot["n"])}%) have their problem holdings recorded, '
            f'{ptot["repo"]} have a repo in the archive, {ptot["statement_full"]} have every statement, '
            f'{ptot["data_full"]} every test-data set, {ptot["solutions_full"]} every solution and '
            f'{ptot["package_full"]} a complete package for every problem; {ptot["nprob"]} problems counted in all. '
            f'{ptot["judges"]} contests link to an online judge where the problems can be solved. '
            f'{len(PROBLEM_FILES)} contests have a per-problem list ({n_problems_listed} problems) — '
            f'<a href="list.html">all listed problems</a>.</p>',
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
    all_rows = [(cid, c, SERIES_REGION.get(series_of[cid], "Other"), True) for cid, c in contests.items() if c.get("problems")]
    all_rows += [(c["id"], c, "non-mainline", False) for c in nm_with]
    for cid, c, region, linked in sorted(all_rows, key=lambda x: x[0]):
        pb = c["problems"]
        pidx.append(
            "<tr><td>" + (link_contest(cid, rel, chip=True) if linked else f'{esc(cid)} <span class="chip" title="outside the mainline hierarchy (registry/non-mainline.yaml)">non-mainline</span>') + "</td>"
            f"<td>{esc(c.get('date', ''))}</td><td class=\"small muted\">{esc(region)}</td>"
            f'<td class="num">{pb.get("count", "")}</td><td>{held_marks(pb)}</td>'
            f'<td>{repo_link(pb)}</td><td class="small">{judge_links(pb.get("judges"))}</td>'
            + (f'<td><a href="{rel}contest/{esc(cid)}.html#problems">list</a></td>' if cid in PROBLEM_FILES else "<td></td>")
            + f'<td class="wrap small muted">{esc(pb.get("notes", ""))}</td></tr>')
    pidx.append("</table></div>")
    (out / "problems" / "index.html").write_text(page("Problems", "\n".join(pidx), rel))

    plist = ["<h1>Every listed problem</h1>",
             f'<p class="muted">{n_problems_listed} problems from {len(PROBLEM_FILES)} contests with a per-problem list '
             f'(<a href="index.html">problem holdings by contest</a>). The box filters by any column — contest, letter, name.</p>',
             '<p class="small muted"><b>St</b> statement · <b>D</b> test data · <b>IV</b>/<b>OV</b> input/output validator · '
             '<b>So</b> solutions · <b>P</b> complete package — filled = held.</p>',
             '<div class="tablewrap"><table><tr><th>contest</th><th>#</th><th>problem</th><th>held</th><th>solve online</th><th>notes</th></tr>']
    for cid in sorted(PROBLEM_FILES):
        for p in PROBLEM_FILES[cid]["problems"]:
            nm = esc(p["name"]) + (f' <span class="small muted">{esc(p["short_name"])}</span>' if p.get("short_name") else "")
            if p.get("status") == "private":
                nm += ' <span class="chip">private</span>'
            link = link_contest(cid, rel) if cid in contests else esc(cid)
            plist.append(f'<tr><td>{link}</td><td class="letter">{esc(p["letter"])}</td><td class="wrap">{nm}</td>'
                         f'<td>{problem_have_marks(p)}</td><td class="small">{judge_links(p.get("judges"))}</td>'
                         f'<td class="wrap small muted">{esc(p.get("notes", ""))}</td></tr>')
    plist.append("</table></div>")
    (out / "problems" / "list.html").write_text(page("Every listed problem", "\n".join(plist), rel))
    (out / "problems" / "problems.json").write_text(json.dumps(
        {"generated": datetime.date.today().isoformat(), "contests": PROBLEM_FILES}, ensure_ascii=False))
    print(f"  problems: {len(all_rows)} contests with holdings, {n_problems_listed} problems listed")

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
        hs = set()
        for w, _ in locators(c.get("web")):
            hs.add(re.sub(r"^https?://(www\.)?", "", w).split("/")[0])
        for lst in (c.get("results") or {}).values():
            for e in lst:
                hs.add(re.sub(r"^https?://(www\.)?", "", e["url"]).split("/")[0])
        return sorted(hs)

    search = [{"id": cid, "name": c.get("name"), "date": c.get("date"), "series": series_of[cid],
               "cms": [str(i) for i in (c.get("cms_ids") or [])], "hosts": hosts_of(c),
               "region": SERIES_REGION.get(series_of[cid], ""),
               "problems": [p["name"] for p in PROBLEM_FILES.get(cid, {}).get("problems", [])] or None}
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
<a href="coverage.html">collection coverage</a> · <a href="problems/index.html">problems</a> · <a href="resources/index.html">all resources</a> ·
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
