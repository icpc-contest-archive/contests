#!/usr/bin/env python3
"""Build the static catalogue site into site/ (relative links only, mountable anywhere).

Objects and their pages (DEFINITIONS.md):
  season/<end-year>.html      one season: its World Finals, date window, the advancement tree
  series/<id>.html            one series: header, lineage, every edition
  contest/<id>.html           one contest: facts, then Website / Results / Problems
  problemset/<set-id>.html    one problem set: what the archive holds, problem by problem
  problem/<pid>.html          one problem: appearances, holdings, online judges
  source/<id>/index.html      one source (a catalogued address): where to open it, health, snapshots, captures
  judge/<id>.html             one online judge;  location/<id>.html  one node of the location tree
Each object has an index (<object>/index.html) built from the same parts. Views over the
same data: coverage.html, grid.html, wanted.html, cms.html, non-mainline.html.

Rules the pages are built by (also told to the reader on about.html):
  1. One renderer per object. A contest is always its id linking to its page, a series its id,
     a season "2024–2025", a location its name, a source its address label linking to the
     SOURCE PAGE, a problem set its id, a problem its name.
  2. A link stays on this site unless it is marked ↗. The address of a source is linked ↗ from
     its source page only; a contest's CMS links, a judge's own site and a problem's judge links
     live on (or in rows of) those objects.
  3. A contest has three kinds of content — website, results, problems — always in that order
     and always present, with one status vocabulary: held (green, filled), known but not held
     (amber, outlined), none (grey), lost (red).
  4. Every list page: title, one paragraph, key, filter bar, sortable table. Every object page:
     breadcrumb, title, status, facts, sections.
  5. One word per thing: location, level, results, problems, website, online judge, CMS id.

Styles, script and fonts live in tools/site_assets/ and are copied to site/assets/.
Old addresses (locator/, problemsets/, judges/, seasons.html, resources/, urls/, local.html,
problems/) are kept as redirect stubs.

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
import shutil
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
                       set_letters, set_of, sources)
import site_resources  # noqa: E402

# the four published result tiers (RESULT_ROLES minus the CMS's own icpc_standings)
RESULT_KINDS = tuple(r for r in RESULT_ROLES if r != "icpc_standings")

RES = site_resources.Resources(ROOT)  # source/snapshot lookups (data/resources.json)
lid = site_resources.lid
ASSETS = ROOT / "tools" / "site_assets"
REPO = "https://github.com/icpc-contest-archive/contests"
REPLAY_BASE = os.environ.get("REPLAY_BASE", "https://icpc-contest-archive.github.io/replay")
LOCAL_BASE = os.environ.get("LOCAL_ARCHIVE_BASE", "http://127.0.0.1:8123")
LOCAL_TITLE = "local archive server — works only while tools/serve.py is running on this machine"

# ---- regions and levels (series headers: `region`, `tier`) ----
REGIONS = ["International", "North America", "Latin America", "Europe", "Northern Eurasia", "Africa & Arab",
           "Asia West", "Asia Pacific", "Asia East"]
LEVELS = ["world-finals", "championship", "regional", "subregional"]
LEVEL_LABEL = {"world-finals": "World Finals", "championship": "championship", "regional": "regional", "subregional": "subregional"}
CHAMPIONSHIPS: set = set()   # series with tier: championship
SERIES_REGION: dict = {}
SERIES_TIER: dict = {}


def derive_regions(series_docs: dict) -> None:
    """Fill SERIES_REGION / SERIES_TIER / CHAMPIONSHIPS from the series headers."""
    CHAMPIONSHIPS.clear()
    for sid, doc in series_docs.items():
        h = doc["series"]
        SERIES_TIER[sid] = h.get("tier") or ("world-finals" if sid == "wf" else "")
        if h.get("tier") == "championship":
            CHAMPIONSHIPS.add(sid)
        SERIES_REGION[sid] = h.get("region") or ("International" if sid == "wf" else "Other")


def level_of(sid: str) -> str:
    return LEVEL_LABEL.get(SERIES_TIER.get(sid, ""), SERIES_TIER.get(sid, ""))


# ---- page chrome ----
NAV = (("season/index.html", "Seasons"), ("series/index.html", "Series"), ("contest/index.html", "Contests"),
       ("problemset/index.html", "Problem sets"), ("problem/index.html", "Problems"), ("source/index.html", "Sources"),
       ("judge/index.html", "Judges"), ("location/index.html", "Locations"))
NAV2 = (("coverage.html", "Coverage"), ("about.html", "About"))


def esc(s) -> str:
    return html.escape(str(s), quote=True)


RANDOM_KINDS = (("contest", "contest"), ("series", "series"), ("season", "season"), ("problemset", "problem set"),
                ("problem", "problem"), ("source", "source"), ("location", "location"), ("judge", "judge"))


def random_page() -> str:
    """random.html — opens a page picked at random, for spot checks without choosing what to look at."""
    kinds = " · ".join(f'<a id="{k}" href="#{k}">{label}</a>' for k, label in RANDOM_KINDS)
    return page("Random page", f"""<h1>Random page</h1>
<p class="intro">For spot checks without choosing what to look at. <b>Random</b> in the header, or the key <b>r</b>, opens a
page picked at random: first the kind of page, then one page of that kind, so contests, problems, sources and the rest turn up
equally often. Pick a kind below and Random stays on that kind until you pick another or close the browser.</p>
<p>Open a random <a id="any" href="#any">page of any kind</a> · {kinds}</p>
<p class="note" id="rnd-msg"></p>
<script>
(function () {{
  var rel = document.documentElement.dataset.rel || '';
  function go() {{
    var kind = location.hash.slice(1);
    if (!kind) return;
    try {{ sessionStorage.setItem('rnd', kind); }} catch (e) {{}}
    document.getElementById('rnd-msg').textContent = 'Picking…';
    fetch(rel + 'random.json').then(function (r) {{ return r.json(); }}).then(function (d) {{
      var kinds = Object.keys(d), k = d[kind] ? kind : kinds[Math.floor(Math.random() * kinds.length)];
      var id = d[k][Math.floor(Math.random() * d[k].length)];
      location.replace(rel + (k === 'source' ? 'source/' + id + '/index.html' : k + '/' + id + '.html'));
    }}).catch(function () {{ document.getElementById('rnd-msg').textContent = 'Could not load the page list.'; }});
  }}
  window.addEventListener('hashchange', go);
  go();
}})();
</script>""", "")


def refs(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def page(title: str, body: str, rel: str, nav: str | None = None) -> str:
    """One page. `nav` is the NAV href of the object list this page belongs to (highlighted)."""
    links = "".join(f'<a href="{rel}{h}"' + (' class="on"' if h == nav else "") + f">{t}</a>" for h, t in NAV)
    links += '<span class="sep"></span>' + "".join(
        f'<a href="{rel}{h}"' + (' class="on"' if h == nav else "") + f">{t}</a>" for h, t in NAV2)
    links += f'<a id="rnd" href="{rel}random.html" title="Open a random page — press r">Random</a>'
    return f"""<!doctype html><html lang="en" data-rel="{rel}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — ICPC contest archive</title><link rel="icon" href="{rel}assets/favicon.svg">
<link rel="stylesheet" href="{rel}assets/site.css"></head><body>
<header class="site"><a class="brand" href="{rel}index.html"><span class="logo"><i></i><i></i><i></i></span>ICPC contest archive</a>
<nav>{links}</nav>
<div class="search"><input id="q" type="search" placeholder="Search — press /" autocomplete="off" aria-label="Search the archive"><div id="hits" class="hits"></div></div></header>
<main>{body}
<footer class="site">Every ICPC contest from which a team could advance toward a World Finals. Something missing or wrong?
<a href="{rel}about.html#contribute">Tell us</a> · <a href="{rel}about.html#read">How to read this site</a> ·
<a href="{rel}random.html">Random page</a> ·
Data: <a class="ext" href="{REPO}">icpc-contest-archive/contests</a></footer></main>
<script src="{rel}assets/site.js" defer></script></body></html>"""


def stub(path: Path, target: str) -> None:
    """A tiny meta-refresh page at an old address so existing links keep working."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={esc(target)}">'
                    f'<title>moved</title><p>Moved to <a href="{esc(target)}">{esc(target)}</a>.</p>')


def crumbs(*items: str) -> str:
    """Breadcrumb line above an object page's title: already-rendered links, outermost first."""
    return '<p class="crumbs">' + " › ".join(items) + " ›</p>"


def th(label: str, num: bool = False, f: bool | str = False, title: str | None = None) -> str:
    """A header cell. `f` adds a drop-down filter on the column (a string names it in the filter bar)."""
    a = (' class="num"' if num else "") + (f' data-f="{esc(f)}"' if isinstance(f, str) else (" data-f" if f else ""))
    return f"<th{a}" + (f' title="{esc(title)}"' if title else "") + f">{label}</th>"


def table(heads: list[str], rows: list[str], cls: str = "", tid: str | None = None) -> str:
    return (f'<div class="tw"><table' + (f' class="{cls}"' if cls else "") + (f' id="{tid}"' if tid else "")
            + "><thead><tr>" + "".join(heads) + "</tr></thead><tbody>" + "\n".join(rows) + "</tbody></table></div>")


def chip(text: str, cls: str = "", title: str | None = None) -> str:
    return f'<span class="chip{" " + cls if cls else ""}"' + (f' title="{esc(title)}"' if title else "") + f">{esc(text)}</span>"


def help_link(anchor: str, rel: str, what: str = "what these mean") -> str:
    return f'<a class="help" href="{rel}about.html#{anchor}" title="{esc(what)}" aria-label="{esc(what)}">?</a>'


def pct(part: int, total: int) -> int:
    return round(100 * part / total) if total else 0


def pct_cell(part: int, total: int) -> str:
    """A percentage with a bar; sorts numerically."""
    if not total:
        return '<td class="num muted" data-v="">–</td>'
    p = pct(part, total)
    return f'<td class="num" data-v="{p}">{p}%<span class="bar"><i style="width:{p}%"></i></span></td>'


def num(n) -> str:
    return f"{n:,}"


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
capture_info: dict = {}  # archive path -> capture entry (from data/archive-index.json)
website_of: dict = {}    # contest -> primary website capture (from data/website-index.json)
CMS_SLUGS: dict = {}


# ---- the one way each object is shown as a link ----
def link_contest(cid: str, rel: str, chip_upcoming: bool = True) -> str:
    """A contest: its id, name · date on hover, an `upcoming` chip when it has not run."""
    c = CONTESTS.get(cid) or {}
    tip = " · ".join(x for x in (c.get("name"), c.get("date")) if x)
    out = f'<a href="{rel}contest/{esc(cid)}.html"' + (f' title="{esc(tip)}"' if tip else "") + f">{esc(cid)}</a>"
    if chip_upcoming and c.get("status") == "upcoming":
        out += ' <span class="chip n" title="has not run yet">upcoming</span>'
    return out


def link_series(sid: str, rel: str) -> str:
    name = (SERIES_DOCS.get(sid) or {}).get("series", {}).get("name") or ""
    return f'<a href="{rel}series/{esc(sid)}.html"' + (f' title="{esc(name)}"' if name else "") + f">{esc(sid)}</a>"


def link_season(season, rel: str, label: str | None = None) -> str:
    if not season:
        return ""
    return f'<a href="{rel}season/{season}.html">{esc(label or f"{season - 1}–{season}")}</a>'


SERIES_DOCS: dict = {}


def link_date(d, rel: str) -> str:
    """A date: the date itself, linking to that day in the calendar (what else ran then).
    A partial date (a year, a month) is plain text."""
    if not d:
        return ""
    d = str(d)
    if len(d) == 10:
        return f'<a class="date" href="{rel}calendar/{d[:4]}.html#d-{d}" title="the calendar: what else ran around {d}">{d}</a>'
    return esc(d)


def best_tier(c) -> str:
    """The ONE tier ladder used by the grid, coverage, wanted list and marks:
    scoreboard > frozen_scoreboard > standings > rankings > icpc > none."""
    br = best_result(c)
    if not br:
        return "none"
    if br[0] == "icpc_standings":   # a standings page of the CMS with nothing on it is not a result
        return "none" if all(lid(s["url"]) in EMPTY_STANDINGS and not archived(s) for s in br[1]) else "icpc"
    return br[0]


def web_state(c) -> str:
    """'link' (a web source), 'none' (confirmed none: web under `none:`), 'unknown' (not researched)."""
    if has_role(c, "web"):
        return "link"
    return "none" if "web" in (c.get("none") or []) else "unknown"


TIERS = (("scoreboard", "S"), ("frozen_scoreboard", "F"), ("standings", "St"), ("rankings", "R"), ("icpc_standings", "I"))
TIER_LABEL = {"scoreboard": "scoreboard", "frozen_scoreboard": "frozen scoreboard", "standings": "standings",
              "rankings": "rankings", "icpc": "ICPC standings only", "none": "none"}
ROLE_LABEL = {"icpc_standings": "ICPC standings", "judge_page": "judge page", "frozen_scoreboard": "frozen scoreboard",
              "problemset": "problem set", "web": "website"}
HELD_KINDS = (("statement", "St", "statements"), ("data", "D", "test data"),
              ("solutions", "So", "solutions"), ("package", "P", "complete packages"))


def key_line(rel: str, *parts: str) -> str:
    """The key above a table. Parts: 'results', 'website', 'held', 'have', 'available'."""
    bits = []
    if "results" in parts:
        bits.append("<b>S</b> scoreboard · <b>F</b> frozen scoreboard · <b>St</b> standings · <b>R</b> rankings · <b>I</b> ICPC standings (the CMS's own data)")
    if "website" in parts:
        bits.append("<b>W</b> website")
    if "results" in parts or "website" in parts:
        bits.append('<span class="m h">filled</span> we hold a copy <span class="m l">outlined</span> link only <span class="m n">grey</span> the page is empty')
    if "held" in parts:
        bits.append('problems: <b>St</b> statements · <b>D</b> test data · <b>So</b> solutions · <b>P</b> packages — '
                    '<span class="m h">all</span> <span class="m l">some</span> <span class="m n">none</span> <span class="m u">not recorded</span> held by the problem archive')
    if "have" in parts:
        bits.append('<b>St</b> statement · <b>D</b> test data · <b>IV</b>/<b>OV</b> input/output validator · <b>So</b> solutions · <b>P</b> package — '
                    '<span class="m h">held</span> <span class="m n">not held</span> <span class="m u">not recorded</span>')
    if "available" in parts:
        bits.append('where a source can be found — <b>live</b> at its address now · <b>WB</b> in the Wayback Machine · <b>ours</b> in our archive: '
                    '<span class="m h">there</span> <span class="m l">there, but changed or empty</span> <span class="m n">not there</span> '
                    '<span class="m u">not checked</span>')
    return '<p class="key">' + " &nbsp;·&nbsp; ".join(bits) + " " + help_link("marks", rel) + "</p>"


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


def host_label(url: str, n: int = 30) -> str:
    h = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
    return h if len(h) <= n else h[:n - 1] + "…"


def link_source(url: str, rel: str, label: str | None = None, ts=None) -> str:
    """A source: its label linking to the SOURCE PAGE (snapshot anchor when `ts` names one).
    The address itself is linked from the source page only. A source the resource graph does
    not know yet (data/resources.json older than the catalogue) falls back to the address ↗."""
    lab = esc(label if label is not None else host_label(url))
    href = src_href(url, rel, ts)
    if href:
        return f'<a href="{href}" title="{esc(res_label(url, ts, 200))}">{lab}</a>'
    return f'<a class="ext" href="{esc(url)}" title="{esc(url)} — no source page yet (rebuild data/resources.json)">{lab}</a>'


def role_label(r: str) -> str:
    return ROLE_LABEL.get(r, r.replace("_", " "))


def role_chip(r: str) -> str:
    return f'<span class="chip">{esc(role_label(r))}</span>'


def lost_locators(c) -> list:
    """Result/web sources of this contest that are gone from their address AND not in the
    Wayback Machine: whatever we hold is the only copy; if we hold nothing, the material is
    lost. An address that only refuses our fetcher (403, an untrusted certificate) is not gone."""
    out = []
    for s in sources(c):
        if not ("web" in s["roles"] or any(r in s["roles"] for r in RESULT_KINDS)):
            continue
        a = avail(s["url"], c["id"], s)
        if a["live"]["s"] == "no" and a["live"]["word"] == "dead" and a["wb"]["s"] == "no":
            out.append((s["url"], a["wb"]["word"], a["ours"]["s"] == "yes"))
    return out


def local_link(path: str, label: str = "local") -> str:
    return f'<a class="local" href="{LOCAL_BASE}/{esc(path)}" title="{LOCAL_TITLE}">{label}</a>'


def cap_of(e: dict) -> dict | None:
    return capture_info.get(held_path(e) or "")


def result_marks(c: dict, rel: str) -> str:
    """One mark per result tier present: filled = an archived copy is held, outlined = link
    only. Each mark links to the source page of the address that serves the tier."""
    out = []
    for key, letter in TIERS:
        entries = by_role(c, key)
        if not entries:
            continue
        e = next((x for x in entries if held_capture(x)), None)
        held = e is not None
        e = e or entries[0]
        if key == "icpc_standings" and not held and all(lid(x["url"]) in EMPTY_STANDINGS for x in entries):
            href = src_href(e["url"], rel)
            tip = "ICPC standings — the page is empty: the ICPC API has no standings for this contest"
            out.append(f'<a class="m n" href="{href}" title="{tip}">{letter}</a>' if href else f'<span class="m n" title="{tip}">{letter}</span>')
            continue
        tip = role_label(key) + (" — archived copy held" if held else " — link only, not archived")
        parts = list(dict.fromkeys(x["scope"] for x in entries if x.get("scope")))
        if parts:
            tip += " (" + ", ".join(parts) + ")"
        href = src_href(e["url"], rel, e.get("as_of") or cap_time(cap_of(e)))
        out.append(f'<a class="m {"h" if held else "l"}" href="{href}" title="{tip}">{letter}</a>' if href
                   else f'<span class="m {"h" if held else "l"}" title="{tip}">{letter}</span>')
    return "".join(out)


def results_value(c: dict) -> str:
    """The filter value of a results cell."""
    return "upcoming" if c.get("status") == "upcoming" else TIER_LABEL[best_tier(c)]


def results_held(c: dict) -> bool:
    """We hold an archived copy of a published result (scoreboard, standings or rankings)."""
    return any(held_capture(e) for e in result_sources(c))


def website_cell(c: dict, rel: str, n: int = 24) -> str:
    """`W` (filled = archived, outlined = link only) and the host, linking to the source page."""
    ws = web_state(c)
    if ws == "none":
        return '<span class="muted" title="looked: this contest had no website of its own">none</span>'
    webs = by_role(c, "web")
    if not webs:
        return ""
    held = c["id"] in website_of
    s = webs[0]
    more = f' <span class="small muted" title="{len(webs)} website addresses">+{len(webs) - 1}</span>' if len(webs) > 1 else ""
    return (f'<span class="m {"h" if held else "l"}" title="website — {"archived copy held" if held else "link only, not archived"}">W</span>'
            + link_source(s["url"], rel, host_label(s["url"], n), s.get("as_of")) + more)


def website_value(c: dict) -> str:
    return "archived" if c["id"] in website_of else {"link": "link only", "none": "confirmed none", "unknown": "not known"}[web_state(c)]


def cms_links(i) -> str:
    """`<id> (admin ↗ · finder ↗)` for one CMS id — used where the CMS id is the subject."""
    lk = [f'<a class="ext" href="https://icpc.global/private/contest/{i}/" title="CMS admin page (login required)">admin</a>']
    slug = CMS_SLUGS.get(int(i))
    if slug:
        lk.append(f'<a class="ext" href="https://icpc.global/regionals/finder/{esc(slug)}" title="public finder page">finder</a>')
    return f'{i} <span class="small">({" · ".join(lk)})</span>'


def cms_cell(c: dict) -> str:
    """The CMS id(s) in a table: plain numbers; `none` when the contest is known to have no entry."""
    ids = c.get("cms_ids")
    if ids:
        return ", ".join(str(i) for i in ids)
    return '<span class="muted">none</span>' if ids == [] else ""


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


# ---- availability: a source and the three places it can be found (DEFINITIONS.md, Resources) ----
# A source is an address as a contest means it: what the address served for that contest. The
# same document can be found in up to three places, and every listing of a source shows all
# three as one unit:  live (the address, now) · WB (the Wayback Machine) · ours (our archive).
AV_CLS = {"yes": "h", "part": "l", "no": "n", "unknown": "u"}
AV_PLACES = (("live", "live", "the address now"), ("wb", "WB", "Wayback Machine"), ("ours", "ours", "our archive"))


LIVE_EVIDENCE = (
    (r"nodename nor servname|Name or service not known|getaddrinfo|rep=4", "the host name no longer exists"),
    (r"CERTIFICATE_VERIFY_FAILED", "the server's certificate could not be verified by our fetcher — it may still open in a browser"),
    (r"HTTP 404", "the server answers “not found” (404)"),
    (r"HTTP 403", "the server refuses our fetcher (403) — it may still open in a browser"),
    (r"HTTP 401", "the server asks for a login (401)"),
    (r"HTTP (5\d\d)", "the server reports an error (5xx)"),
    (r"timed out|rep=6", "no answer (timed out)"),
    (r"refused|rep=5", "the connection was refused"),
    (r"SSL|TLS", "the secure connection failed"),
    (r"RemoteDisconnected|reset", "the server closed the connection"),
    (r"never mentions year", "it answers, but never names the contest's year — a different page now, or an app that shows nothing without a browser"),
    (r"app shell answers", "it answers; the page is an app, so only a browser shows its content"),
)


def plain_live(ev: str | None) -> str:
    """The last live check's finding in words a reader can use (the raw error stays in the data)."""
    for rx, words in LIVE_EVIDENCE:
        if re.search(rx, ev or ""):
            return words
    return ev or ""


def plain_why(ev: str | None) -> str:
    """Why a fetched file is not the document, in words (the audit's own line stays in the data)."""
    ev = ev or ""
    pre = "the site's front page is " if ev.startswith("site crawl front page") else ""
    if "generic-shared" in ev:
        return "the same page was served for unrelated contests — a generic page, not this document"
    if "type-mismatch" in ev:
        return "the file is not what its name says: an HTML page where a PDF should be, usually an error page"
    for key, words in (("login-wall", "a login page"), ("parked-domain", "a parked domain's advertising page"),
                       ("placeholder", "a server placeholder page"), ("directory-listing", "a bare directory listing"),
                       ("under-construction", "an “under construction” page"), ("bot-challenge", "a “verify you are human” page"),
                       ("not-found", "an error page"), ("http-error-page", "an error page"), ("forbidden", "an “access denied” page")):
        if key in ev:
            return pre + words
    m = re.search(r"husk[^—]*— (\d+) visible chars: (.*?)(?: \| ->.*)?$", ev)
    if "redirect-stub" in ev:
        to = re.search(r"-> (\S+)", ev)
        return pre + "only a redirect" + (f" to {to.group(1)}" if to else "")
    if m:
        said = m.group(2).strip("'\" ")
        return pre + ("an empty page: an app that shows nothing without a browser, or a blank file" if int(m.group(1)) == 0 or not said
                      else f"nearly empty — all it says is “{said[:80]}”")
    if "seed-not-fetched" in ev:
        return "the front page could not be fetched"
    if re.search(r"\b(empty|tiny)\b", ev):
        return pre + "an empty file"
    return ev
LIVE_WORD = {"live": "live", "changed": "changed", "replaced": "replaced", "dead": "dead", "unknown": "could not tell", "blocked": "blocked"}
BLOCKED = re.compile(r"HTTP (401|403|412|4[5-9]\d)|CERTIFICATE_VERIFY_FAILED")   # the server answered; our fetcher was turned away
LIVE_TIP = {
    "live": "the address still serves this",
    "changed": "the address answers, but what it serves has drifted, or is an app that shows nothing without a browser",
    "replaced": "something else lives at the address now",
    "dead": "the address no longer answers",
    "unknown": "the address answered, but there was nothing to judge it against",
    "blocked": "the server answers but turns our fetcher away (a 403, or a certificate it does not trust) — it may still open in a browser",
    "empty": "the page answers, but there is nothing on it",
}
EXTRA_HELD: dict = defaultdict(list)   # source id -> copies the resource graph files under another address
EMPTY_STANDINGS: dict = {}   # source id -> date asked: ICPC standings pages the open API has no rows for (data/icpc-standings-empty.json)
_CIT: dict = {}
_COPIES: dict = {}


def index_extra_copies(contests: dict) -> None:
    """Copies the catalogue ties to a source but the resource graph files under another address:
    a capture named in `archived` whose own address differs (a redirect target, a mirror), and
    the contest's website crawl when it was seeded from another spelling of the address."""
    EXTRA_HELD.clear()
    _CIT.clear()
    _COPIES.clear()
    for cid, c in contests.items():
        for e in sources(c):
            k = lid(e["url"])
            for p in archived(e):
                ci = capture_info.get(p)
                if not ci or ci.get("content_caveat") or not ci.get("url") or lid(unwrap(ci["url"])[0]) == k:
                    continue
                src = ci.get("source") or "live"
                EXTRA_HELD[k].append({"ts": cap_time(ci) or "unknown", "via": "wayback" if src == "wayback" or unwrap(ci["url"])[2] else src,
                                      "contest": cid, "kind": "capture", "filed_under": unwrap(ci["url"])[0],
                                      "cap": {"path": ci["path"], "contest": ci["contest"], "artifact": ci["artifact"], "sha256": ci.get("sha256"),
                                              "size": ci.get("size"), "content_type": ci.get("content_type"), "fetched": ci.get("fetched"),
                                              "source": src, "fetch_url": ci.get("final_url") or ci["url"], "replay": REPLAY_LOOKUP.get((cid, norm_key(ci["url"])))}})
        site, webs = website_of.get(cid), by_role(c, "web")
        if site and webs:
            e = next((w for w in webs if norm_key(w["url"]) == norm_key(site.get("seed_raw") or site.get("seed") or "")), webs[0])
            if lid(site.get("seed_raw") or site.get("seed") or "") != lid(e["url"]):
                EXTRA_HELD[lid(e["url"])].append({
                    "ts": site.get("wayback_timestamp") or re.sub(r"[^0-9]", "", str(site.get("fetched") or ""))[:14] or "unknown",
                    "via": "wayback" if site.get("mode") == "wayback" else "live", "contest": cid, "kind": "website",
                    "filed_under": site.get("seed_raw") or site.get("seed"), "site": site})


def citations(k: str) -> list[dict]:
    """The contests that cite an address, one entry each (roles merged), in catalogue order."""
    if k not in _CIT:
        out: dict = {}
        for r in (RES.locs.get(k) or {}).get("refs") or []:
            c = out.setdefault(r["contest"], {"contest": r["contest"], "roles": [], "fields": [], "as_of": None, "state": None,
                                              "checked": None, "note": None, "archived": []})
            c["roles"] += [x for x in r.get("roles") or [] if x not in c["roles"]]
            if r["field"] not in c["fields"]:
                c["fields"].append(r["field"])
            c["as_of"] = c["as_of"] or r.get("as_of")
            c["state"] = c["state"] or r.get("url_state")
            c["checked"] = c["checked"] or r.get("url_checked")
            c["note"] = c["note"] or r.get("note")
            c["archived"] += [p for p in r.get("archived") or [] if p not in c["archived"]]
        _CIT[k] = list(out.values())
    return _CIT[k]


def copies(k: str) -> list[dict]:
    """Every copy of an address in our archive that is the real thing: captures of one page and
    crawled websites, each with the time it shows (`ts`) and where it was fetched from (`via`)."""
    if k not in _COPIES:
        out = []
        for ts, R in ((RES.locs.get(k) or {}).get("resources") or {}).items():
            for c in R.get("captures") or []:
                if c.get("sha256") and not c.get("caveat"):
                    out.append({"ts": ts, "via": R.get("via") or c.get("source") or "live", "contest": c["contest"], "kind": "capture", "cap": c})
            w = R.get("website")
            if w and (w.get("pages") or 0) > 0:
                out.append({"ts": ts, "via": R.get("via") or ("wayback" if w.get("mode") == "wayback" else "live"),
                            "contest": w["contest"], "kind": "website", "site": w})
        _COPIES[k] = out + EXTRA_HELD.get(k, [])
    return _COPIES[k]


def copies_for(k: str, cid: str | None = None) -> list[dict]:
    """The copies that are this contest's document. An address cited by one contest has one
    document. An address several contests cite (a page reused every year) has one per contest:
    a copy counts when it was captured for this contest, or for a contest that means the same
    thing by the address (the same `as_of`; with none, the same season — a joint contest)."""
    cs = copies(k)
    cits = {c["contest"]: c for c in citations(k)}
    if cid is None or len(cits) <= 1:
        return cs
    me = cits.get(cid)
    own = [x for x in cs if x["contest"] == cid or (me and x.get("cap") and x["cap"]["path"] in me["archived"])]
    if own or not me:
        return own
    season = (CONTESTS.get(cid) or {}).get("season")
    same = {o for o, c in cits.items() if o != cid and c["as_of"] == me["as_of"]
            and (me["as_of"] or (season and (CONTESTS.get(o) or {}).get("season") == season))}
    return [x for x in cs if x["contest"] in same]


def _nearest(tss: list[str], want: str | None) -> str:
    if not want:
        return max(tss)
    w = int(str(want).ljust(14, "0")[:14])
    return min(tss, key=lambda t: abs(int(str(t).ljust(14, "0")[:14]) - w))


def avail(url: str, cid: str | None = None, e: dict | None = None) -> dict:
    """Where a source can be found. {"live": .., "wb": .., "ours": .., "lost": bool}; each place is
    {"s": yes|part|no|unknown, "word": the one-word status, "tip": the sentence behind it} and the
    Wayback entry also has "ts" (the snapshot to open, when one is known). `cid` picks the
    contest's own document when several contests cite the address; `e` is the catalogue entry
    when the caller has it (its own health verdict and `as_of` win)."""
    k = lid(url)
    L = RES.locs.get(k)
    if not L:
        un = {"s": "unknown", "word": "not checked", "tip": "not in the resource graph yet (rebuild data/resources.json)"}
        return {"live": dict(un), "wb": dict(un, ts=None), "ours": {"s": "no", "word": "missing", "tip": "no copy in our archive"}, "lost": False, "copies": []}
    cit = next((c for c in citations(k) if c["contest"] == cid), None) if cid else None
    h = L.get("health") or {}
    st = (e or {}).get("url_state") or (cit or {}).get("state") or h.get("state")
    when = (e or {}).get("url_checked") or (cit or {}).get("checked") or h.get("checked")
    if st == "dead" and h.get("state") == "dead" and BLOCKED.search(h.get("evidence") or ""):
        st = "blocked"   # recorded as dead by the live check; shown as what it is
    live = {"s": {"live": "yes", "changed": "part", "blocked": "part", "replaced": "no", "dead": "no"}.get(st, "unknown"),
            "word": LIVE_WORD.get(st, "not checked"),
            "tip": (LIVE_TIP.get(st, "the address has not been checked yet") + (f" (checked {when})" if when else "")),
            "checked": when, "evidence": h.get("evidence") if h.get("state") == (st if st != "blocked" else "dead") else None}
    cs = copies_for(k, cid)
    probes = [p for p in L.get("probes") or [] if p.get("outcome") == "junk" and (cid is None or p.get("contest") in (None, cid) or len(citations(k)) <= 1)]
    as_of = (e or {}).get("as_of") or (cit or {}).get("as_of") or (None if cid else next((c["as_of"] for c in citations(k) if c["as_of"]), None))
    wb_held = sorted(x["ts"] for x in cs if x["via"] == "wayback" and x["ts"] != "unknown")
    wb_junk = [p for p in probes if p.get("via") == "wayback"]
    w = L.get("wayback") or {}
    wm = re.search(r"\((\d{8,14})\)", w.get("evidence") or "")
    if wb_held:
        ts = _nearest(wb_held, as_of)
        wb = {"s": "yes", "word": "snapshot", "ts": ts, "tip": f"snapshot of {fmt_time(ts)} — the one our copy was taken from"}
    elif wb_junk:
        wb = {"s": "part", "word": "empty snapshot", "ts": wb_junk[-1].get("ts"),
              "tip": "a snapshot exists, but what it holds is not the document: " + plain_why(wb_junk[-1].get("evidence"))[:160]}
    elif as_of:
        wb = {"s": "yes", "word": "snapshot", "ts": as_of, "tip": f"snapshot of {fmt_time(as_of)}, named by the catalogue; we have not captured it"}
    elif w.get("state") == "ok":
        ts = wm.group(1) if wm else None
        wb = {"s": "yes", "word": "snapshot", "ts": ts, "tip": "a snapshot is served" + (f" ({fmt_time(ts)})" if ts else "") + (f" — checked {w['checked']}" if w.get("checked") else "")}
    elif w.get("state") == "none":
        wb = {"s": "no", "word": "no snapshot", "ts": None, "tip": "the Wayback Machine has no snapshot of this address" + (f" (checked {w['checked']})" if w.get("checked") else "")}
    elif w.get("state") == "excluded":
        wb = {"s": "no", "word": "excluded", "ts": None, "tip": "the Wayback Machine refuses to serve this address (excluded by policy)"}
    else:
        wb = {"s": "unknown", "word": "not checked", "ts": None,
              "tip": "nobody has looked in the Wayback Machine for this address yet" if not w.get("state") else "the last Wayback check failed (throttled); not known"}
    ours_junk = [p for p in probes if p.get("path") or p.get("dir")]
    if cs:
        last = max(cs, key=lambda x: (x["ts"] != "unknown", x["ts"]))
        ours = {"s": "yes", "word": "held", "n": len(cs),
                "tip": (f"{len(cs)} copies" if len(cs) > 1 else "one copy") + f"; the latest shows {fmt_time(last['ts']) if last['ts'] != 'unknown' else 'an unknown time'}, "
                       + ("from the Wayback Machine" if last["via"] == "wayback" else "from the ICPC standings data" if last["via"] in ("api-dump", "icpc-api-archive") else "fetched from the address")
                       + (f" ({last['site'].get('html_pages') or last['site'].get('pages')} pages)" if last["kind"] == "website" else "")}
    elif ours_junk:
        ours = {"s": "part", "word": "empty copy", "n": 0,
                "tip": "we fetched it, but what came back is not the document: " + plain_why(ours_junk[-1].get("evidence"))[:160]}
    else:
        ours = {"s": "no", "word": "missing", "n": 0, "tip": "no copy in our archive"}
    if k in EMPTY_STANDINGS and not cs:
        said = f"the ICPC API has no standings for this contest (asked {EMPTY_STANDINGS[k]})"
        live = dict(live, s="part", word="empty", tip="the page answers, but there is nothing on it: " + said, evidence=None)
        ours = dict(ours, tip="nothing to capture — the page is empty: " + said)
    lost = live["s"] == "no" and wb["s"] == "no" and ours["s"] != "yes"
    return {"live": live, "wb": wb, "ours": ours, "lost": lost, "copies": cs}


def avail_marks(a: dict) -> str:
    """The unit: three marks, always in the order live · WB · ours. Green = it is there, amber =
    something is there but not quite the document, grey = not there, dashed = nobody has looked."""
    out = "".join(f'<span class="m {AV_CLS[a[key]["s"]]}" title="{esc(full + ": " + a[key]["word"] + " — " + a[key]["tip"])}">{lab}</span>'
                  for key, lab, full in AV_PLACES)
    if a["lost"]:
        out += chip("lost", "x", "dead at its address, not in the Wayback Machine, and we hold no copy")
    return f'<span class="av">{out}</span>'


def avail_values(a: dict) -> str:
    """The filter values of an availability cell (one per place)."""
    return f'live: {a["live"]["word"]}|WB: {a["wb"]["word"]}|ours: {a["ours"]["word"]}' + ("|lost" if a["lost"] else "")


def avail_cell(url: str, cid: str | None = None, e: dict | None = None) -> str:
    a = avail(url, cid, e)
    return f'<td class="nw" data-vs="{esc(avail_values(a))}">{avail_marks(a)}</td>'


AVAIL_TH = ('<th data-f="available" title="where the source can be found: live = at its address now, WB = in the Wayback Machine, '
            'ours = in our archive">live · WB · ours</th>')



# ---- locations (DEFINITIONS.md, Locations) ----
LOC: dict = {}                      # node id -> node
LOC_KIDS: dict = defaultdict(list)  # node id -> child ids
LOC_DIRECT: dict = defaultdict(list)  # node id -> contest ids held exactly at this node
LOC_SUB: dict = {}                  # node id -> set of contest ids anywhere in the subtree
TYPE_ORDER = {"country": 0, "region": 1, "city": 2, "institution": 3}


def physical_sites(c: dict) -> list[dict]:
    return [s for s in c.get("sites") or [] if s.get("type") not in ("administrative", "online") and s.get("location") in LOC]


def held_at(c: dict) -> tuple[list[str], str]:
    """(node ids, how we know) — where a contest was held, as nodes of the location tree:
    'sites'    its physical sites;
    'online'   it ran online: the places its online or organising sites point at;
    'inferred' it has no physical site on record: the city its administrative CMS groups
               (staff, guests, teams of a single-site event) sit in.
    Distinct, in site order; ([], '') when nothing is placed."""
    phys = [s["location"] for s in physical_sites(c)]
    if phys:
        return list(dict.fromkeys(phys)), "sites"
    sites = c.get("sites") or []
    is_online = any(s.get("type") == "online" for s in sites)
    located = [s for s in sites if s.get("location") in LOC]
    online = [s["location"] for s in located if s.get("type") == "online"]
    if online:
        return list(dict.fromkeys(online)), "online"
    adm = Counter(s["location"] for s in located if s.get("type") == "administrative")
    if adm:
        cities: Counter = Counter()  # the most common city among the administrative groups
        for nid, n in adm.items():
            city = next((x["id"] for x in location_chain(LOC, nid) if x["type"] in ("city", "region", "country")), nid)
            cities[city] += n
        return [cities.most_common(1)[0][0]], "online" if is_online else "inferred"
    return [], ""


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
        for nid in held_at(c)[0]:
            LOC_DIRECT[nid].append(cid)

    def sub(nid):
        acc = set(LOC_DIRECT.get(nid, []))
        for k in LOC_KIDS.get(nid, []):
            acc |= sub(k)
        LOC_SUB[nid] = acc
        return acc
    for nid, n in LOC.items():
        if not n.get("parent"):
            sub(nid)


def loc_link(nid: str, rel: str, label: str | None = None) -> str:
    """A location: its name linking to its page."""
    n = LOC.get(nid)
    if not n:
        return esc(label or nid)
    return f'<a href="{rel}location/{esc(nid)}.html" title="{esc(n["type"])}">{esc(label or n["name"])}</a>'


def loc_crumb(nid: str, rel: str, from_node: bool = True) -> str:
    """institution › city › region › country, each linked (most specific first)."""
    chain = location_chain(LOC, nid)
    if not from_node:
        chain = chain[1:]
    return " › ".join(loc_link(n["id"], rel) for n in chain)


def city_and_country(nid: str) -> tuple[str | None, str | None]:
    """(the city-level node id, the country node id) above or at a node; the city is None
    for a region or country node."""
    chain = location_chain(LOC, nid)
    return (next((n["id"] for n in chain if n["type"] == "city"), None),
            next((n["id"] for n in chain if n["type"] == "country"), None))


def place_short(nid: str, rel: str) -> str:
    """`City, Country` for a node, both linked into the location tree (a region or country
    node shows what it has)."""
    city, country = city_and_country(nid)
    if city:
        return loc_link(city, rel) + (", " + loc_link(country, rel) if country else "")
    n = LOC[nid]
    if n["type"] == "region" and country:
        return loc_link(nid, rel) + ", " + loc_link(country, rel)
    return loc_link(country or nid, rel)


def place_cell(c: dict, rel: str, maxn: int = 2) -> str:
    """The location cell of a contest row: `City, Country` per distinct place, linked; the
    free-text location (muted, no link) when the contest is not placed in the tree yet."""
    nodes, how = held_at(c)
    seen, out = [], []
    for nid in nodes:
        key = city_and_country(nid) if city_and_country(nid)[0] else (nid, None)
        if key in seen:
            continue
        seen.append(key)
        out.append(place_short(nid, rel))
    if out:
        more = f' <span class="small muted" title="{len(out)} places">+{len(out) - maxn} more</span>' if len(out) > maxn else ""
        pre = '<span class="muted">online · </span>' if how == "online" else ""
        return pre + "; ".join(out[:maxn]) + more
    if any(s.get("type") == "online" for s in c.get("sites") or []):
        return '<span class="muted">online</span>'
    t = free_location(c)
    if t:
        return f'<span class="muted" title="{esc(t)} — as recorded; not placed in the location tree yet">{esc(t if len(t) <= 44 else t[:43] + "…")}</span>'
    return ""


NOT_A_PLACE = re.compile(r"(?i)^(administrative site( location)?|x+|online( contest \d+)?|internet|www|virtual reality|to be selected|any site|preliminary( site)?)$")


def free_location(c: dict) -> str:
    """The free-text location as recorded, without the parts that are CMS group labels rather
    than places (Administrative Site Location, xxxx, Online, …) and without repeats."""
    seen, out = set(), []
    for part in re.split(r"\s*;\s*", c.get("location") or ""):
        if part and not NOT_A_PLACE.match(part) and part.lower() not in seen:
            seen.add(part.lower())
            out.append(part)
    return "; ".join(out)


def place_countries(c: dict) -> list[str]:
    """Country names of a contest (the filter values of a location cell)."""
    out = []
    for nid in held_at(c)[0]:
        country = city_and_country(nid)[1]
        if country and LOC[country]["name"] not in out:
            out.append(LOC[country]["name"])
    return out


def site_line(s: dict, rel: str) -> str:
    """One site of a contest on its own page: breadcrumb (or the free label), the site's own
    name and date, and its type."""
    nid = s.get("location")
    parts = []
    if nid in LOC:
        parts.append(loc_crumb(nid, rel))
        if s.get("name") and s["name"] != LOC[nid]["name"] and s["name"] not in (LOC[nid].get("aliases") or []):
            parts.append(f'<span class="muted">— {esc(s["name"])}</span>')
    elif s.get("name"):
        parts.append(f'{esc(s["name"])} ' + chip("not placed", "n", "this site label could not be placed in the location tree"))
    else:
        return ""
    if s.get("date"):
        parts.append(f'<span class="small muted">{esc(s["date"])}</span>')
    if s.get("type"):
        parts.append(chip(s["type"], "n", "a non-physical bookkeeping group in the CMS (staff, guests, teams)" if s["type"] == "administrative" else "teams competing remotely"))
    return " ".join(parts)


# ---- problems (DEFINITIONS.md, Problems) ----
SETS: dict = {}       # set id -> parsed problemsets/<set-id>.yaml
JUDGES: dict = {}     # judge id -> judges.yaml entry
PROBLEMS: dict = {}   # problem id -> {"rows": [(set id, problem row)], "apps": [(set id, contest id, letter|None)]}
REPLAY_LOOKUP: dict = {}  # (contest, norm_key(url)) -> baked replay path, filled by build()
REPLAY_PROBLEMSET: dict = {}  # the same, problem-set pages only
PROBLEMSET_CAPS: dict = {}  # (contest, norm_key(url)) -> archive path of a held problem-set capture (not published)
JUDGE_CAPS: dict = {}  # (contest, norm_key(url)) -> archive path of a held judge-page capture (private, like problem sets)
NM: list = []  # registry/non-mainline.yaml


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
    chip (the registry contests have no page)."""
    if cid in CONTESTS:
        return link_contest(cid, rel)
    if any(c["id"] == cid for c in NM):
        return f"{esc(cid)} " + chip("non-mainline", "n", "outside the advancement hierarchy (registry/non-mainline.yaml); no contest page")
    return f"{esc(cid)} " + chip("not catalogued", "n", "this id is not in the catalogue (stale pointer in an index)")


def set_link(sid: str, rel: str, label: str | None = None) -> str:
    """A problem set: its id linking to its page."""
    doc = SETS.get(sid) or {}
    tip = doc.get("name") or ""
    return f'<a href="{rel}problemset/{esc(sid)}.html"' + (f' title="{esc(tip)}"' if tip else "") + f">{esc(label or sid)}</a>"


def problem_link(pid: str, rel: str, label: str | None = None) -> str:
    """A problem: its name linking to its page."""
    return f'<a href="{rel}problem/{esc(pid)}.html">{esc(label or problem_name(pid))}</a>'


def set_members(doc: dict) -> list[str]:
    return [m["contest"] for m in doc.get("contests") or []]


def set_own_contest(sid: str, doc: dict) -> bool:
    """The usual case: the set belongs to exactly the contest of the same id."""
    return set_members(doc) == [sid]


def set_counts(doc: dict) -> tuple[int | None, int]:
    """(how many problems the contest had, when known; how many are listed by name)."""
    listed = len(doc.get("problems") or [])
    return doc.get("count") or (listed if listed and doc.get("complete") is not False else None), listed


def set_list_state(doc: dict) -> str:
    """'complete' | 'partial' | 'none' — is the set's problem list there?"""
    total, listed = set_counts(doc)
    if not listed:
        return "none"
    return "partial" if doc.get("complete") is False or (total and listed < total) else "complete"


def held_marks(pb: dict) -> str:
    """What the problem archive holds for a set, one mark per kind of material:
    all / some (n of count) / none / not recorded."""
    out = []
    for key, letter, what in HELD_KINDS:
        st = pb.get(key)
        if st is None:
            out.append(f'<i class="m u" title="{what}: not recorded">{letter}</i>')
            continue
        n = (pb.get("counts") or {}).get(key)
        cnt = pb.get("count")
        detail = {"full": f"all {cnt} problems" if cnt else "every problem",
                  "partial": f"{n} of {cnt} problems" if n is not None and cnt else "some problems",
                  "none": "none held"}[st]
        out.append(f'<i class="m { {"full": "h", "partial": "l", "none": "n"}[st]}" title="{what}: {detail}">{letter}</i>')
    return "".join(out)


def held_value(pb: dict) -> str:
    """Filter values of a held cell: the kinds held for every problem."""
    return "|".join(w for k, _l, w in HELD_KINDS if pb.get(k) == "full") or ("none" if any(pb.get(k) for k, *_ in HELD_KINDS) else "not recorded")


def problems_cell(c: dict, rel: str) -> str:
    """The problems cell of a contest row: the number of problems (linking to the set) and the
    archive's holdings; `src` when only a published set or judge page is known."""
    pb = set_for(c)
    if pb:
        total, listed = set_counts(pb)
        lab = str(total) if total else ("set" if not listed else str(listed))
        return f'<a href="{rel}problemset/{esc(pb["id"])}.html" title="problem set {esc(pb["id"])}: {total or "?"} problems, {listed} listed by name">{lab}</a> ' + held_marks(pb)
    if c.get("status") != "upcoming" and (has_role(c, "problemset") or has_role(c, "judge_page")):
        return '<span class="m l" title="a published problem set or a judge page is known; nothing recorded about the problems yet">src</span>'
    return ""


def problems_value(c: dict) -> str:
    pb = set_for(c)
    if pb:
        return {"complete": "listed", "partial": "partly listed", "none": "count only"}[set_list_state(pb)]
    return "source only" if c.get("status") != "upcoming" and (has_role(c, "problemset") or has_role(c, "judge_page")) else "none"


def repo_link(pb: dict) -> str:
    repo = pb.get("repo")
    if not repo:
        return ""
    name = repo.split("/", 1)[1]
    tip = "statements only, in the shared statement-only repo (private)" if name == "statement-only" else "problem archive repo (private)"
    return f'<a class="ext" href="https://github.com/{esc(repo)}" title="{tip}">{esc(name)}</a>'


def judge_name(jid: str) -> str:
    return (JUDGES.get(jid) or {}).get("name") or jid


def judge_link(jid: str, rel: str) -> str:
    """An online judge: its name linking to its page."""
    if jid in JUDGES:
        return f'<a href="{rel}judge/{esc(jid)}.html">{esc(judge_name(jid))}</a>'
    return esc(jid)


def judge_closed_chip(jid: str) -> str:
    j = JUDGES.get(jid) or {}
    if j.get("status") != "closed":
        return ""
    return " " + chip("closed" + (f' {j["closed"]}' if j.get("closed") else ""), "n",
                      j.get("notes") or "this judge has shut down; its pages survive only in Wayback snapshots")


def problem_judge_links(p: dict, sep: str = " ", by_id: bool = False, tips: bool = True) -> str:
    """A problem's online judges: each the judge's name (or, on the judge's own page, the
    problem's id there), linking ↗ straight to the problem on the judge — the Wayback
    snapshot for a judge that has closed."""
    parts = []
    for j in p.get("judges") or []:
        url, as_of = j["url"], j.get("as_of")
        href = wayback_link(url, as_of) if as_of else url
        tip = res_label(url, as_of, 200) + (f" — {judge_name(j['judge'])} id {j['id']}" if j.get("id") else "") + (" (Wayback snapshot)" if as_of else "")
        lab = (j.get("id") or "open") if by_id else judge_name(j["judge"])
        parts.append(f'<a class="ext" href="{esc(href)}"' + (f' title="{esc(tip)}"' if tips else "") + f">{esc(lab)}</a>")
    return sep.join(parts)


HAVE_KINDS = (("statement", "St", "statement"), ("data", "D", "test data"), ("input_validator", "IV", "input validator"),
              ("output_validator", "OV", "output validator"), ("solutions", "So", "solutions"), ("package", "P", "complete package"))
SET_KIND = {"statement": "statement", "data": "data", "solutions": "solutions", "package": "package"}


def problem_have(p: dict, doc: dict | None) -> dict[str, bool | None]:
    """{kind: held? (None = not recorded)} for one problem. Per-problem holdings are recorded
    for few sets; otherwise the set's own holdings decide where they are all-or-nothing
    (statements held for every problem of the set => held for this one)."""
    if "have" in p:
        have = set(p.get("have") or [])
        return {k: k in have for k, *_ in HAVE_KINDS}
    out: dict[str, bool | None] = {}
    for k, *_ in HAVE_KINDS:
        st = (doc or {}).get(SET_KIND.get(k, ""))
        out[k] = True if st == "full" else False if st == "none" else None
    return out


def problem_have_marks(p: dict, doc: dict | None, tips: bool = True) -> str:
    """`tips=False` leaves the hover text out (the 10,000-row problem index; its key says it all)."""
    hv = problem_have(p, doc)
    exact = "have" in p
    out = []
    for key, letter, what in HAVE_KINDS:
        v = hv[key]
        if v is None and not exact and key in ("input_validator", "output_validator"):
            continue  # validators are only ever known per problem
        cls = "h" if v else "n" if v is False else "u"
        tip = f"{what}: " + ("held" if v else "not held" if v is False else "not recorded for this problem")
        out.append(f'<i class="m {cls}" title="{tip}">{letter}</i>' if tips else f'<i class="m {cls}">{letter}</i>')
    return "".join(out)


def problem_have_value(p: dict, doc: dict | None) -> str:
    hv = problem_have(p, doc)
    held = [w for k, _l, w in HAVE_KINDS if hv[k]]
    return "|".join(held) if held else ("nothing held" if all(v is False for v in hv.values()) else "not recorded")


# ---- content summaries: the same three numbers wherever contests are counted ----
def content_counts(cs: list[dict]) -> dict:
    """Counts over contests: how many ran, and for how many we hold each kind of content."""
    ran = [c for c in cs if c.get("status") != "upcoming"]
    return {"all": len(cs), "n": len(ran), "upcoming": len(cs) - len(ran),
            "results": sum(1 for c in ran if results_held(c)),
            "sets": sum(1 for c in ran if set_for(c)),
            "web": sum(1 for c in ran if c["id"] in website_of)}


CONTENT_HEADS = [
    th("results", num=True, title="contests with an archived copy of a published result (scoreboard, standings or rankings)"), th("%", num=True),
    th("problem sets", num=True, title="contests whose problem set is recorded (problem list or archive holdings)"), th("%", num=True),
    th("websites", num=True, title="contests whose website we hold an archived copy of"), th("%", num=True)]


def content_cells(st: dict) -> str:
    return "".join(f'<td class="num">{st[k]}</td>' + pct_cell(st[k], st["n"]) for k in ("results", "sets", "web"))


def content_nums(st: dict, extra: str = "") -> str:
    """The numbers strip of a group of contests (season, series, location, the whole archive):
    how many ran, then for how many of those we hold each kind of content, with the share."""
    def tile(n, label, of=None):
        if of is None:
            return f"<div><b>{num(n)}</b><span>{label}</span></div>"
        share = f'{pct(n, of)}%' if of else "–"
        return (f'<div><b>{num(n)} <i class="pc">{share}</i></b><span>{label}</span>'
                f'<span class="meter" title="{num(n)} of the {num(of)} contests that ran"><i style="width:{pct(n, of)}%"></i></span></div>')
    return ('<div class="nums">' + tile(st["n"], "contests ran" + (f' <span class="muted">+{st["upcoming"]} upcoming</span>' if st["upcoming"] else ""))
            + tile(st["results"], "results", st["n"]) + tile(st["sets"], "problem sets", st["n"])
            + tile(st["web"], "websites", st["n"]) + extra + "</div>")


# ---- contest rows: the one set of columns every table of contests picks from ----
def _c_contest(c, rel):
    return f'<td class="nw">{link_contest(c["id"], rel)}</td>'


def _c_contest_name(c, rel):
    return (f'<td class="name">{link_contest(c["id"], rel)}'
            + (f'<span class="sub">{esc(c["name"])}</span>' if c.get("name") else "") + "</td>")


CONTEST_COLS = {
    "contest": (th("contest"), _c_contest),
    "contest+name": (th("contest"), _c_contest_name),
    "season": (th("season", f=True), lambda c, rel: f'<td class="nw" data-v="{c.get("season", "")}">{link_season(c.get("season"), rel)}</td>'),
    "date": (th("date"), lambda c, rel: f'<td class="nw" data-v="{esc(c.get("date", ""))}">{link_date(c.get("date"), rel)}</td>'),
    "location": (th("location", f="country"), lambda c, rel: f'<td data-vs="{esc("|".join(place_countries(c)))}">{place_cell(c, rel)}</td>'),
    "series": (th("series", f=True), lambda c, rel: f'<td class="nw">{link_series(SERIES_OF[c["id"]], rel)}</td>'),
    # series with its level and region underneath; the two hidden columns after it carry the filters
    "series+": (th("series", f=True), lambda c, rel: (f'<td class="nw" data-v="{esc(SERIES_OF[c["id"]])}">{link_series(SERIES_OF[c["id"]], rel)}'
                                                     f'<span class="sub">{esc(level_of(SERIES_OF[c["id"]]))} · {esc(SERIES_REGION.get(SERIES_OF[c["id"]], ""))}</span></td>')),
    "region": (th("region", f=True), lambda c, rel: f'<td class="nw">{esc(SERIES_REGION.get(SERIES_OF[c["id"]], ""))}</td>'),
    "level": (th("level", f=True), lambda c, rel: f'<td class="nw">{esc(level_of(SERIES_OF[c["id"]]))}</td>'),
    "region-": ('<th class="hid" data-f>region</th>', lambda c, rel: f'<td class="hid">{esc(SERIES_REGION.get(SERIES_OF[c["id"]], ""))}</td>'),
    "level-": ('<th class="hid" data-f>level</th>', lambda c, rel: f'<td class="hid">{esc(level_of(SERIES_OF[c["id"]]))}</td>'),
    "advances": (th("advances to"), lambda c, rel: '<td class="nw">' + ", ".join(link_contest(p, rel, False) for p in refs(c.get("parent"))) + "</td>"),
    "results": (th("results", f=True), lambda c, rel: f'<td class="nw" data-v="{esc(results_value(c))}">{result_marks(c, rel)}</td>'),
    "problems": (th("problems", f=True), lambda c, rel: f'<td class="nw" data-v="{esc(problems_value(c))}">{problems_cell(c, rel)}</td>'),
    "website": (th("website", f=True), lambda c, rel: f'<td data-v="{esc(website_value(c))}">{website_cell(c, rel)}</td>'),
    "cms": (th("CMS id"), lambda c, rel: f'<td class="nw">{cms_cell(c)}</td>'),
}
CONTEST_INDEX_COLS = ("contest+name", "date", "location", "series+", "region-", "level-", "season", "results", "problems", "website", "cms")
SEASON_COL = CONTEST_INDEX_COLS.index("season")      # for links that open the contest table filtered
REGION_COL = CONTEST_INDEX_COLS.index("region-")
COUNTRY_COL = CONTEST_INDEX_COLS.index("location")


def contest_table(cs: list[dict], rel: str, cols: tuple[str, ...], cls: str = "", tid: str | None = None,
                  extra: tuple[str, callable] | None = None) -> str:
    """A table of contests built from CONTEST_COLS; `extra` appends one context column."""
    heads = [CONTEST_COLS[k][0] for k in cols] + ([extra[0]] if extra else [])
    rows = ["<tr>" + "".join(CONTEST_COLS[k][1](c, rel) for k in cols) + (extra[1](c) if extra else "") + "</tr>" for c in cs]
    return table(heads, rows, cls, tid)



# ---- contest pages ----
REPLAY_BY_CONTEST: dict = defaultdict(list)
ARCHIVED_BY_CONTEST: dict = defaultdict(list)
CHILDREN: dict = {}
PREV: dict = {}
SUBSETS: dict = {}
BOILERPLATE = re.compile(r"^(ICPC Problem Archive progress sheet|Baekjoon ICPC category tree|online-judge pages|"
                         r"Kattis problem export|problem list from the )")


def evidence_lines(c: dict) -> list[str]:
    """The hand-collected lines of `provenance` (where a date came from, proof that a dark
    contest ran). Import stamps about the problem set are not evidence about the contest."""
    return [x for x in refs(c.get("provenance")) if not BOILERPLATE.match(str(x))]


def status_chips(c: dict, cid: str, rel: str) -> str:
    """The contest's status, one chip per kind of content, same words everywhere
    (about.html#status lists every value)."""
    chips = []
    if c.get("status") == "upcoming":
        chips.append(chip("upcoming", "n", "has not run yet"))
    bt = best_tier(c)
    if bt == "none" and c.get("status") == "upcoming":
        pass
    elif bt == "none":
        chips.append(chip("results: none", "n", "no result source of any kind is known"))
    else:
        held = results_held(c) or (bt == "icpc" and any(held_capture(e) for e in by_role(c, "icpc_standings")))
        chips.append(chip(f"results: {TIER_LABEL[bt]}, " + ("archived" if held else "link only"), "h" if held else "l",
                          "the best result we know is a " + TIER_LABEL[bt].replace(" only", "") + ("; we hold an archived copy" if held else "; we only have the link, no archived copy yet")))
    ws = web_state(c)
    if ws == "link":
        held = cid in website_of
        chips.append(chip("website: " + ("archived" if held else "link only"), "h" if held else "l",
                          "we hold a crawl of the contest website" if held else "the website address is known; no archived copy yet"))
    elif ws == "none":
        chips.append(chip("website: none", "n", "looked: this contest had no website of its own"))
    else:
        chips.append(chip("website: not known", "n", "no website address found yet — not the same as there being none"))
    pb = set_for(c)
    if pb:
        total, listed = set_counts(pb)
        state = set_list_state(pb)
        text = {"complete": f"problems: {listed} listed", "partial": f"problems: {listed} of {total or '?'} listed",
                "none": f"problems: {total or '?'}, not listed"}[state]
        full = pb.get("statement") == "full"
        chips.append(chip(text, "h" if full else "l", ("the problem archive holds every statement" if full else "the problem archive does not hold every statement")
                          + {"complete": "; every problem is listed by name", "partial": "; only some problems are listed by name", "none": "; the problems are not listed by name yet"}[state]))
    elif c.get("status") != "upcoming" and (has_role(c, "problemset") or has_role(c, "judge_page")):
        chips.append(chip("problems: source only", "l", "a published problem set or a judge page is known; nothing recorded about the problems yet"))
    elif c.get("status") != "upcoming":
        chips.append(chip("problems: none", "n", "nothing is known about this contest's problems"))
    gone = [u for u, _w, held in lost_locators(c) if not held]
    only = [u for u, _w, held in lost_locators(c) if held]
    if gone:
        chips.append(chip(f"{len(gone)} lost", "x", "dead at its address, no Wayback snapshot, nothing held here: " + "; ".join(gone)))
    if only:
        chips.append(chip(f"{len(only)} only here", "h", "dead at its address and not in the Wayback Machine — our copy is the only one: " + "; ".join(only)))
    return '<p class="status">' + "".join(chips) + " " + help_link("status", rel) + "</p>"


HUNT_STAMP = re.compile(r"\s*\((?:judge hunt|QOJ ICPC category tree) .*\)$")


def source_note(e: dict) -> str:
    """A source's note for display: the import stamp of a judge hunt and a note that only
    repeats the judge's name say nothing to a reader."""
    note = HUNT_STAMP.sub("", e.get("note") or "").strip()
    return "" if e.get("judge") and note in (judge_name(e["judge"]), (JUDGES.get(e["judge"]) or {}).get("name", "")) else note




def source_table(cid: str, entries: list[dict], rel: str, kind: str, extra_rows: list[str] | None = None) -> str:
    """The sources of one kind on a contest page: what each serves, the address (to its source
    page), and where it can be found — live, in the Wayback Machine, in our archive — as one
    unit. Nothing here leaves the site; the copies are opened from the source's own page."""
    rows = []
    for e in entries:
        url, as_of = e["url"], e.get("as_of")
        roles = "".join(role_chip(r) for r in sorted(e["roles"], key=lambda r: RANK[r]))
        if e.get("scope"):
            roles += chip(e["scope"], "sc", "this source covers one part of the contest, not all of it")
        if e.get("judge"):
            roles += f'<span class="chip">{judge_link(e["judge"], rel)}</span>' + judge_closed_chip(e["judge"])
        note = esc(source_note(e))
        for m in also_at(e):
            note += (" · " if note else "") + "also at " + link_source(m["url"], rel, res_label(m["url"], m.get("as_of"), 60), m.get("as_of")) + " " + avail_marks(avail(m["url"], cid))
        rows.append(f"<tr><td>{roles}</td><td class=\"url\">{link_source(url, rel, res_label(url, as_of, 90), as_of or cap_time(cap_of(e)))}</td>"
                    + avail_cell(url, cid, e) + f"<td class=\"small muted\">{note}</td></tr>")
    rows += extra_rows or []
    return table([th("serves"), th("source"), AVAIL_TH, th("note")], rows, "nosort")


def contest_page(cid: str, c: dict, rel: str) -> str:
    sid = SERIES_OF[cid]
    b = [crumbs(f'<a href="{rel}contest/index.html">Contests</a>', link_series(sid, rel)),
         f"<h1>{esc(cid)}</h1>"]
    if c.get("name"):
        b.append(f'<p class="lede">{esc(c["name"])}</p>')
    b.append(status_chips(c, cid, rel))

    # ---- facts ----
    d = ['<dl class="facts">',
         f"<dt>series</dt><dd>{link_series(sid, rel)} <span class=\"muted\">{esc(level_of(sid))} · {esc(SERIES_REGION.get(sid, ''))}</span></dd>"]
    if c.get("season"):
        d.append(f"<dt>season</dt><dd>{link_season(c['season'], rel)}</dd>")
    d.append("<dt>date</dt><dd>" + (link_date(c["date"], rel) if c.get("date") else '<span class="muted">not known</span>') + "</dd>")
    all_sites = c.get("sites") or []
    phys = [x for x in (site_line(s, rel) for s in all_sites if not s.get("type")) if x]
    remote = [x for x in (site_line(s, rel) for s in all_sites if s.get("type") == "online") if x]
    # administrative sites (the CMS's staff, guest and bookkeeping groups) are not places: never listed
    nodes, how = held_at(c)
    lines = []
    if how == "online":
        lines.append("Online" + (", organised from " + "; ".join(dict.fromkeys(place_short(n, rel) for n in nodes[:3])) if nodes else ""))
    elif how == "inferred":
        lines.append("; ".join(place_short(n, rel) for n in nodes) + " "
                     + chip("inferred", "n", "no contest site is recorded; this is the city the contest's CMS record points at"))
    elif not nodes and free_location(c):
        lines.append(f'{esc(free_location(c))} <span class="small muted">— as recorded; not placed in the location tree yet</span>')
    elif not nodes and any(s.get("type") == "online" for s in all_sites):
        lines.append("Online")
    if phys:
        lines.append("<br>".join(phys) if len(phys) <= 6 else f"<details><summary>{len(phys)} sites</summary>{'<br>'.join(phys)}</details>")
    if remote:
        lines.append(f'<details><summary class="small muted">{len(remote)} online site{"s" if len(remote) != 1 else ""}</summary>{"<br>".join(remote)}</details>')
    d.append("<dt>location</dt><dd>" + ("<br>".join(x for x in lines if not x.startswith("<details")) + "".join(x for x in lines if x.startswith("<details"))
                                        if lines else '<span class="muted">not known</span>') + "</dd>")
    for label, ids in (
        ("advances to", refs(c.get("parent"))),
        ("fed by", sorted(CHILDREN.get(cid, []))),
        ("previous edition", sorted(PREV.get(cid, []))),
        ("next edition", refs(c.get("next"))),
        ("subset of", [c["subset_of"]] if c.get("subset_of") else []),
        ("regional views", sorted(SUBSETS.get(cid, []))),
    ):
        if ids:
            d.append(f"<dt>{label}</dt><dd>" + ", ".join(link_contest(x, rel, False) for x in ids) + "</dd>")
    if c.get("parent") is None and "parent" in c:
        d.append('<dt>advances to</dt><dd class="muted">nothing — the top of the hierarchy</dd>')
    ids = c.get("cms_ids")
    if ids:
        d.append("<dt>CMS id</dt><dd>" + ", ".join(cms_links(i) for i in ids) + "</dd>")
    elif ids == []:
        d.append('<dt>CMS id</dt><dd class="muted">none</dd>')
    if c.get("notes"):
        d.append(f"<dt>notes</dt><dd>{esc(c['notes'])}</dd>")
    d.append("</dl>")
    b += d

    # ---- Website ----
    b.append('<h2 id="website">Website</h2>')
    webs = by_role(c, "web")
    if webs:
        b.append(source_table(cid, webs, rel, "web"))
    elif web_state(c) == "none":
        b.append('<p class="empty">This contest had no website of its own — looked for and confirmed.</p>')
    else:
        b.append('<p class="empty">No website known. Nobody has found an address yet; that is not the same as there being none.</p>')

    # ---- Results ----
    b.append('<h2 id="results">Results</h2>')
    res_entries, seen = [], set()
    for key in RESULT_ROLES:  # best tier first
        for e in by_role(c, key):
            if id(e) not in seen:
                seen.add(id(e))
                res_entries.append(e)
    matched = {"a/" + p for e in sources(c) for p in archived(e)} | {REPLAY_LOOKUP.get((cid, norm_key(e["url"]))) for e in sources(c)}
    extra = []
    for e in REPLAY_BY_CONTEST.get(cid, []):  # replay pages the catalogue does not point at
        if e["path"] in matched or e.get("artifact") == "problemset" or not e.get("url"):
            continue
        matched.add(e["path"])
        extra.append(f'<tr><td>{role_chip(e["artifact"])}</td><td class="url">{link_source(e["url"], rel, res_label(e["url"], None, 90))}</td>'
                     + avail_cell(e["url"], cid) + '<td class="small muted">held, not yet listed as a source of this contest</td></tr>')
    ev = evidence_lines(c)
    if res_entries or extra:
        b.append(source_table(cid, res_entries, rel, "results", extra))
    elif c.get("status") == "upcoming":
        b.append('<p class="empty">Not run yet.</p>')
    else:
        b.append('<p class="empty">No results found — no scoreboard, standings or rankings, not even in the ICPC CMS.'
                 + (" What we do know is under Evidence below." if ev else "") + "</p>")

    # ---- Problems ----
    b.append('<h2 id="problems">Problems</h2>')
    pb = set_for(c)
    psrc = [s for s in sources(c) if "problemset" in s["roles"] or "judge_page" in s["roles"]]
    if c.get("status") == "upcoming":
        b.append('<p class="empty">Not run yet — nothing about a contest\'s problems is published before it has run.</p>')
    elif not pb and not psrc:
        b.append('<p class="empty">Nothing is known about this contest\'s problems: no problem set recorded, no published set, no online judge.</p>')
    else:
        if pb:
            total, listed = set_counts(pb)
            others = [m for m in set_members(pb) if m != cid]
            b.append(f'<p>Problem set {set_link(pb["id"], rel)}: ' + (f"{total} problems" if total else "number of problems not known")
                     + (f", {listed} listed by name" if listed and set_list_state(pb) == "partial" else "")
                     + f' &nbsp;{held_marks(pb)} <span class="small muted">what the problem archive holds — details on the set\'s page</span>'
                     + (' <span class="small muted">· shared with ' + ", ".join(contest_ref(x, rel) for x in others) + "</span>" if others else "") + "</p>")
            if (c.get("problems") or {}).get("note"):
                b.append(f'<p class="note">{esc(c["problems"]["note"])}</p>')
            probs = set_problems_in_order(pb, cid)
            if probs:
                b.append('<p class="cols">' + "<br>".join(
                    f'<b>{esc(L or "?")}</b> &nbsp;{problem_link(p["id"], rel, p["name"])}'
                    + (" " + chip("private", "n", "kept private after the contest; name and uuid are public") if p.get("status") == "private" else "")
                    for L, p in probs) + "</p>")
                if not set_letters(pb, cid):
                    b.append('<p class="note">The letters are not known for this contest'
                             + (" (shown with another contest's letters)." if any(set_letters(pb, m) for m in set_members(pb)) else ".") + "</p>")
        else:
            b.append('<p class="empty">No problem set recorded yet; the sources below are where the problems can be found.</p>')
        if psrc:
            b.append(source_table(cid, psrc, rel, "problems"))

    # ---- everything else ----
    others = [s for s in sources(c) if not (set(s["roles"]) & (set(RESULT_ROLES) | {"web", "problemset", "judge_page"}))]
    if others:
        b.append('<h2 id="other">Other sources</h2>' + source_table(cid, others, rel, "other"))
    if ev:
        b.append(f'<h2 id="evidence">Evidence</h2><p class="note">How we know what is said above — where a date came from, proof that the contest ran.</p>'
                 '<ul class="plain small">' + "".join(f"<li>{esc(x)}</li>" for x in ev) + "</ul>")
    return page(cid, "\n".join(b), rel, "contest/index.html")


def contest_index(contests: dict, rel: str) -> str:
    cs = [contests[k] for k in sorted(contests)]
    st = content_counts(cs)
    body = ["<h1>Contests</h1>",
            f'<p class="intro">Every contest in the hierarchy: {num(st["n"])} that ran and {st["upcoming"]} upcoming. '
            f'Other ways in: by <a href="{rel}season/index.html">season</a> (advancement trees), by <a href="{rel}series/index.html">series</a>, '
            f'in date order in the <a href="{rel}calendar/index.html">calendar</a>, on one screen in the <a href="{rel}grid.html">grid</a> (series × year), or by what is still <a href="{rel}wanted.html">wanted</a>.</p>',
            key_line(rel, "results", "website", "held"),
            contest_table(cs, rel, CONTEST_INDEX_COLS, "flt")]
    return page("Contests", "\n".join(body), rel, "contest/index.html")


# ---- series pages ----
def series_years(doc: dict) -> tuple[int, int]:
    ys = [int(c["id"].rsplit("-", 1)[1]) for c in doc["contests"]]
    return min(ys), max(ys)


def lineage_chips(doc: dict, rel: str) -> str:
    bits = [f'<span class="chip">{esc(ev["type"].replace("-", " "))} {link_series(ev["series"], rel)} ({ev["year"]})</span>' for ev in doc["series"].get("lineage") or []]
    bits += [chip(f"formerly {a}", "n", "an old id of this series") for a in doc["series"].get("aliases") or []]
    return " ".join(bits)


def series_page(sid: str, doc: dict, rel: str) -> str:
    s = doc["series"]
    b = [crumbs(f'<a href="{rel}series/index.html">Series</a>'), f"<h1>{esc(sid)}</h1>"]
    if s.get("name"):
        b.append(f'<p class="lede">{esc(s["name"])}</p>')
    y0, y1 = series_years(doc)
    seasons = [c["season"] for c in doc["contests"] if c.get("season")]
    d = ['<dl class="facts">',
         f"<dt>level</dt><dd>{esc(level_of(sid))}</dd>", f"<dt>region</dt><dd>{esc(SERIES_REGION.get(sid, ''))}</dd>",
         f"<dt>editions</dt><dd>{len(doc['contests'])}, {y0}–{y1}"
         + (f' <span class="muted">· seasons {link_season(min(seasons), rel)} to {link_season(max(seasons), rel)}</span>' if seasons else "") + "</dd>"]
    if lineage_chips(doc, rel):
        d.append("<dt>lineage</dt><dd>" + lineage_chips(doc, rel) + "</dd>")
    if s.get("rotating_host"):
        d.append('<dt>host</dt><dd>rotates between cities <span class="muted">— gaps between years are expected</span></dd>')
    if s.get("notes"):
        d.append(f"<dt>notes</dt><dd>{esc(s['notes'])}</dd>")
    d.append("</dl>")
    b += d
    b.append(content_nums(content_counts(doc["contests"])))
    b.append(f'<h2 id="editions">Editions <span class="n">{len(doc["contests"])}</span></h2>')
    b.append('<p class="note">The year in an id is the season label, not the date: here it names the '
             + ("season's first half, so a fall contest postponed into the next year keeps its number." if s.get("naming") != "season-end" else "season's end.") + "</p>")
    b.append(key_line(rel, "results", "website", "held"))
    b.append(contest_table(list(reversed(doc["contests"])), rel,
                           ("contest", "season", "date", "location", "advances", "results", "problems", "website", "cms")))
    return page(sid, "\n".join(b), rel, "series/index.html")


def series_index(series_docs: dict, rel: str) -> str:
    rows = []
    for sid in sorted(series_docs):
        doc = series_docs[sid]
        y0, y1 = series_years(doc)
        st = content_counts(doc["contests"])
        rows.append(f'<tr><td class="name">{link_series(sid, rel)}<span class="sub">{esc(doc["series"].get("name", ""))}</span></td>'
                    f'<td class="nw">{esc(SERIES_REGION.get(sid, ""))}</td><td class="nw">{esc(level_of(sid))}</td>'
                    f'<td class="num">{st["n"]}</td><td class="nw" data-v="{y0}">{y0}–{y1}</td>'
                    + content_cells(st) + f'<td class="small">{lineage_chips(doc, rel)}</td></tr>')
    return page("Series", "<h1>Series</h1>"
                f'<p class="intro">{len(series_docs)} series. A series is a line of editions under one name; when a contest was renamed or split, '
                "the lineage column says what it continues from or as. The contest counts are editions that ran.</p>"
                + table([th("series"), th("region", f=True), th("level", f=True), th("contests", num=True), th("years")] + CONTENT_HEADS + [th("lineage")],
                        rows, "flt"), rel, "series/index.html")


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


def season_tree(season: int, members: list[str], rel: str, root: str | None = None):
    """(tree html or '', unplaced ids): the advancement tree with the World Finals at the
    root (via `parent`), then every member with no path to it."""
    mset, seen = set(members), set()

    def label(cid):
        c = CONTESTS[cid]
        meta = " · ".join(x for x in (link_date(c.get("date"), rel), place_cell(c, rel, 1)) if x)
        return link_contest(cid, rel) + f'<span class="meta">{meta} {result_marks(c, rel)}</span>'

    def node(cid):
        seen.add(cid)
        kids = sorted(k for k in CHILDREN.get(cid, []) if k in mset and k not in seen)
        if not kids:
            return f'<div class="leaf">{label(cid)}</div>'
        return f"<details open><summary>{label(cid)}</summary>" + "\n".join(node(k) for k in kids) + "</details>"

    wf_id = root or f"wf-{season}"
    tree = f'<div class="tree">{node(wf_id)}</div>' if wf_id in CONTESTS and wf_id in mset else ""
    return tree, sorted(m for m in mset if m not in seen), label


def season_page(season: int, members: list[str], rel: str) -> str:
    cs = [CONTESTS[m] for m in members]
    body = [crumbs(f'<a href="{rel}season/index.html">Seasons</a>'), f"<h1>Season {season - 1}–{season}</h1>"]
    win = season_window(season, members)
    d = ['<dl class="facts">']
    wf_id = f"wf-{season}"
    if wf_id in CONTESTS:
        c = CONTESTS[wf_id]
        d.append(f"<dt>World Finals</dt><dd>{link_contest(wf_id, rel)}"
                 + "".join(f' <span class="muted">·</span> {x}' for x in (link_date(c.get("date"), rel), place_cell(c, rel)) if x) + "</dd>")
    else:
        d.append('<dt>World Finals</dt><dd class="muted">none in the catalogue for this season</dd>')
    if win:
        start, end, early, late, _wf = win
        d.append(f"<dt>dates</dt><dd>{esc(start)} to {esc(end)}" + ("" if _wf else ' <span class="muted">— no dated World Finals, so the season ends at its last contest</span>') + "</dd>")
        if early or late:
            foot = []
            if early:
                foot.append("before them: " + ", ".join(f"{link_contest(m, rel, False)} ({esc(dd)})" for dd, m in early))
            if late:
                foot.append("after the World Finals: " + ", ".join(f"{link_contest(m, rel, False)} ({esc(dd)})" for dd, m in late))
            d.append("<dt>outside these dates</dt><dd>" + "; ".join(foot)
                     + ' <span class="muted">— part of this season, but run well apart from the rest of it. The dates above are those of the '
                       "season's main run, from its first cluster of contests to the World Finals, so one early or late contest does not stretch them.</span></dd>")
    d.append(f'<dt>contests</dt><dd>{len(members)} — <a href="{rel}contest/index.html#f:{SEASON_COL}={season}">open them as a table</a></dd>')
    d.append("</dl>")
    body += d
    places = {n for c in cs for n in held_at(c)[0]}
    countries = {city_and_country(n)[1] for n in places} - {None}
    body.append(content_nums(content_counts(cs), f"<div><b>{len(places)}</b><span>locations in {len(countries)} countries</span></div>"))
    tree, unplaced, label = season_tree(season, members, rel)
    body.append('<h2 id="hierarchy">Who advances where</h2>')
    if tree:
        body.append('<p class="note">The World Finals at the top; each contest sits under the one its teams advance to.</p>')
        body.append(key_line(rel, "results"))
        body.append(tree)
    else:
        body.append('<p class="empty">No World Finals in this season to hang the tree from.</p>')
    if unplaced:
        body.append(f'<h2 id="unplaced">Not connected to the World Finals <span class="n">{len(unplaced)}</span></h2>'
                    '<p class="note">Contests of this season whose path to the World Finals is not recorded: what they advance to is unknown, or lies in another season.</p>'
                    '<div class="tree">' + "\n".join(
                        f'<div class="leaf">{label(x)}'
                        + (f' <span class="meta">advances to {", ".join(link_contest(p, rel, False) for p in refs(CONTESTS[x].get("parent")))}</span>' if refs(CONTESTS[x].get("parent")) else "")
                        + "</div>" for x in unplaced) + "</div>")
    return page(f"Season {season - 1}–{season}", "\n".join(body), rel, "season/index.html")


def season_index(rel: str) -> str:
    rows = []
    for season in sorted(BY_SEASON, reverse=True):
        ids = BY_SEASON[season]
        cs = [CONTESTS[x] for x in ids]
        wf = CONTESTS.get(f"wf-{season}")
        st = content_counts(cs)
        win = season_window(season, ids)
        rows.append(f'<tr><td class="nw" data-v="{season}">{link_season(season, rel)}</td>'
                    f'<td class="nw">{link_contest(wf["id"], rel) if wf else ""}</td>'
                    f'<td class="nw" data-v="{esc(wf.get("date", "")) if wf else ""}">{link_date(wf.get("date"), rel) if wf else ""}</td><td>{place_cell(wf, rel, 1) if wf else ""}</td>'
                    f'<td class="nw small">{esc(win[0]) + " to " + esc(win[1]) if win else ""}</td>'
                    f'<td class="num">{st["n"]}' + (f' <span class="small muted">+{st["upcoming"]}</span>' if st["upcoming"] else "") + "</td>"
                    + content_cells(st) + "</tr>")
    return page("Seasons", "<h1>Seasons</h1>"
                f'<p class="intro">{len(BY_SEASON)} seasons. A season runs from its first regional to the World Finals those regionals feed; '
                "its page shows who advances where. The contest counts are contests that ran (upcoming ones after the +); "
                "the percentages are shares of those.</p>"
                + table([th("season"), th("World Finals"), th("date"), th("location"), th("season dates"), th("contests", num=True)] + CONTENT_HEADS, rows),
                rel, "season/index.html")


# ---- the calendar: contests in date order, a page per calendar year ----
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
CAL: dict = defaultdict(lambda: {"dated": [], "undated": []})   # calendar year -> contests


def index_calendar(contests: dict) -> None:
    CAL.clear()
    for c in contests.values():
        d = full_date(c)
        if d:
            CAL[int(d[:4])]["dated"].append(c)
        else:  # no full date: filed under the year its date or id names
            y = int(str(c["date"])[:4]) if c.get("date") else int(c["id"].rsplit("-", 1)[1])
            CAL[y]["undated"].append(c)
    for v in CAL.values():
        v["dated"].sort(key=lambda c: (c["date"], c["id"]))
        v["undated"].sort(key=lambda c: c["id"])


def calendar_page(year: int, rel: str) -> str:
    dated, undated = CAL[year]["dated"], CAL[year]["undated"]
    cols = ("contest+name", "location", "series+", "season", "results", "problems", "website")
    heads = [th("date"), th("day")] + [CONTEST_COLS[k][0] for k in cols]
    rows, prev = [], None
    per_day = Counter(c["date"] for c in dated)
    for c in dated:
        d = c["date"]
        wd = datetime.date.fromisoformat(d).strftime("%a")
        rows.append(f'<tr data-d="{d}"' + (f' id="d-{d}"' if d != prev else "") + f'><td class="nw">{d}</td><td class="nw muted">{wd}</td>'
                    + "".join(CONTEST_COLS[k][1](c, rel) for k in cols) + "</tr>")
        prev = d
    years = sorted(CAL)
    i = years.index(year)
    nav = " ".join(x for x in (f'<a href="{years[i - 1]}.html">← {years[i - 1]}</a>' if i else "",
                               f'<a href="{years[i + 1]}.html">{years[i + 1]} →</a>' if i + 1 < len(years) else "") if x)
    b = [crumbs(f'<a href="{rel}calendar/index.html">Calendar</a>'), f"<h1>{year}</h1>"]
    if dated:
        busiest = per_day.most_common(1)[0]
        b.append(f'<p class="lede">{len(dated)} contests on {len(per_day)} days'
                 + (f"; the busiest was {busiest[0]} with {busiest[1]}" if busiest[1] > 2 else "") + ".</p>")
    b.append(f'<p class="tabs">{nav}</p>')
    if dated:
        b.append(key_line(rel, "results", "website", "held"))
        b.append(table(heads, rows))
    if undated:
        b.append(f'<h2 id="undated">No full date <span class="n">{len(undated)}</span></h2>'
                 '<p class="note">Contests of this year whose day is not known; a year or month is shown where that much is.</p>'
                 + contest_table(undated, rel, ("contest+name", "date", "location", "series+", "season", "results", "problems", "website")))
    return page(f"Calendar {year}", "\n".join(b), rel, "contest/index.html")


def calendar_index(rel: str) -> str:
    rows = []
    top = max((sum(1 for c in v["dated"] if int(c["date"][5:7]) == m) for v in CAL.values() for m in range(1, 13)), default=1)
    for y in sorted(CAL, reverse=True):
        dated, undated = CAL[y]["dated"], CAL[y]["undated"]
        months = Counter(int(c["date"][5:7]) for c in dated)
        cells = "".join(f'<td class="hc" style="background:color-mix(in srgb,var(--held) {round(60 * months[m] / top)}%,var(--paper))">{months[m] or ""}</td>'
                        for m in range(1, 13))
        rows.append(f'<tr><td class="nw"><a href="{y}.html">{y}</a></td><td class="num">{len(dated)}</td><td class="num">{len(undated) or ""}</td>{cells}</tr>')
    n_dated = sum(len(v["dated"]) for v in CAL.values())
    n_all = n_dated + sum(len(v["undated"]) for v in CAL.values())
    return page("Calendar", "<h1>Calendar</h1>"
                f'<p class="intro">Every contest in date order, a page per calendar year: {num(n_dated)} of {num(n_all)} contests have a full date. '
                "A date anywhere on this site links to its day here, so you can see what else ran that day and that weekend. "
                "The months show when in the year contests are held — fall regionals, spring finals.</p>"
                + table([th("year"), th("contests", num=True), th("no full date", num=True)] + [th(m, num=True) for m in MONTHS], rows, "heat"),
                rel, "contest/index.html")



# ---- problem sets and problems ----
def set_first_contest(doc: dict) -> dict:
    for m in set_members(doc):
        if m in CONTESTS:
            return CONTESTS[m]
    return {}


def set_region(doc: dict) -> str:
    fc = set_first_contest(doc)
    return SERIES_REGION.get(SERIES_OF.get(fc.get("id"), ""), "") if fc else "non-mainline"


def set_cell(sid: str, doc: dict, rel: str) -> str:
    """A problem set in a table: its id; the contests after it only when they are not simply
    the contest of the same id (a shared set, or a contest outside the catalogue)."""
    out = set_link(sid, rel)
    if not set_own_contest(sid, doc):
        out += '<span class="sub">used by ' + ", ".join(contest_ref(m, rel) for m in set_members(doc)) + "</span>"
    elif sid not in CONTESTS:
        out += " " + chip("non-mainline", "n", "its contest is outside the advancement hierarchy and has no contest page")
    return out


def set_letter_cells(doc: dict) -> list[tuple[str, dict]]:
    """(letter as shown, problem) rows of a set; a set shared by contests with different
    letterings shows `A / C`."""
    with_letters = [m for m in set_members(doc) if set_letters(doc, m)]
    rows = []
    for L, p in set_problems_in_order(doc):
        if len(with_letters) > 1:
            ls = [letter_of(doc, m, p["id"]) for m in with_letters]
            L = " / ".join(x or "?" for x in ls) if len(set(ls)) > 1 else ls[0]
        rows.append((L or "?", p))
    return rows


def data_from(lines: list) -> str:
    """Import stamps, shortened: where a set's rows came from."""
    out = []
    for x in dict.fromkeys(lines or []):
        x = re.sub(r"^problem list from the (\w+) judge page \((\S+?)\).*$", r"the \1 judge page", str(x))
        out.append(x)
    return "; ".join(esc(x) for x in dict.fromkeys(out))


def problemset_page(sid: str, doc: dict, rel: str) -> str:
    """problemset/<set-id>.html — what the problem archive holds for a set, problem by
    problem. Where the set was published and where it can be solved are sources of the
    contest and stay on the contest page."""
    members = set_members(doc)
    total, listed = set_counts(doc)
    state = set_list_state(doc)
    fc = set_first_contest(doc)
    b = [crumbs(f'<a href="{rel}problemset/index.html">Problem sets</a>'),
         f"<h1>{esc(sid)}</h1>"]
    if doc.get("name"):
        b.append(f'<p class="lede">{esc(doc["name"])}</p>')
    else:
        b.append('<p class="lede">The problem set of ' + " and ".join(esc((CONTESTS.get(m) or {}).get("name") or m) for m in members[:2]) + "</p>")
    chips = [chip({"complete": f"{listed} problems listed", "partial": f"{listed} of {total or '?'} problems listed",
                   "none": (f"{total} problems, not listed" if total else "problems not listed")}[state],
                  {"complete": "h", "partial": "l", "none": "l"}[state],
                  {"complete": "every problem of the set is listed by name", "partial": "only some of the problems are listed by name",
                   "none": "only the archive's holdings are recorded; the problems are not listed by name yet"}[state])]
    for key, _l, what in HELD_KINDS:
        st = doc.get(key)
        if st:
            n = (doc.get("counts") or {}).get(key)
            chips.append(chip(f"{what}: " + {"full": "all", "partial": f"{n} of {doc.get('count')}" if n is not None else "some", "none": "none"}[st],
                              {"full": "h", "partial": "l", "none": "n"}[st], f"{what} held by the problem archive"))
    if not any(doc.get(k) for k, *_ in HELD_KINDS):
        chips.append(chip("archive holdings not recorded", "n", "what the ICPC Problem Archive holds for this set has not been entered"))
    b.append('<p class="status">' + "".join(chips) + " " + help_link("status-set", rel) + "</p>")
    d = ['<dl class="facts">']
    d.append("<dt>used by</dt><dd>" + ", ".join(contest_ref(m, rel) for m in members)
             + (' <span class="muted">— where it was published and where it can be solved online are on the contest page</span>' if any(m in CONTESTS for m in members) else "") + "</dd>")
    if fc.get("season"):
        d.append(f"<dt>season</dt><dd>{link_season(fc['season'], rel)}</dd>")
    d.append("<dt>problems</dt><dd>" + (str(total) if total else '<span class="muted">number not known</span>')
             + (f' <span class="muted">— {listed} listed by name below</span>' if state == "partial" else "") + "</dd>")
    if doc.get("repo"):
        d.append(f"<dt>archive repo</dt><dd>{repo_link(doc)} <span class=\"muted\">in the ICPC Problem Archive (private)</span></dd>")
    if doc.get("aliases"):
        d.append('<dt>replaces</dt><dd class="small">' + ", ".join(esc(a) for a in doc["aliases"])
                 + ' <span class="muted">— these were separate sets with the same problems; their addresses lead here</span></dd>')
    if doc.get("letters") == "unknown":
        d.append('<dt>letters</dt><dd class="muted">not known — the list came from an online judge, which does not keep contest letters</dd>')
    if doc.get("notes"):
        d.append(f"<dt>notes</dt><dd>{esc(doc['notes'])}</dd>")
    if doc.get("provenance"):
        d.append(f'<dt>data from</dt><dd class="small muted">{data_from(doc["provenance"])}</dd>')
    d.append("</dl>")
    b += d
    probs = doc.get("problems") or []
    with_letters = [m for m in members if set_letters(doc, m)]
    same_letters = len({json.dumps(set_letters(doc, m), sort_keys=True) for m in with_letters}) == 1
    if probs:
        b.append(f'<h2 id="problems">Problems <span class="n">{len(probs)}' + (f" of {total}" if state == "partial" and total else "") + "</span></h2>")
        if len(members) > 1 and len(with_letters) > 1 and not same_letters:
            b.append('<p class="note">Several letters in the # column: the letter in ' + " / ".join(esc(m) for m in with_letters) + ".</p>")
        b.append(key_line(rel, "have"))
        rows = []
        for L, p in set_letter_cells(doc):
            private = p.get("status") == "private"
            rows.append(f'<tr><td class="letter">{esc(L)}</td><td>{problem_link(p["id"], rel, p["name"])}'
                        + (" " + chip("private", "n", "kept private after the contest; name and uuid are public") if private else "") + "</td>"
                        + ("<td></td><td></td>" if private else
                           f'<td class="nw">{problem_have_marks(p, doc)}</td><td>{problem_judge_links(p)}</td>') + "</tr>")
        b.append(table([th("#"), th("problem"), th("held"), th("online judge")], rows))
    else:
        b.append('<h2 id="problems">Problems</h2><p class="empty">The problems of this set are not listed by name yet'
                 + (f" — {total} problems; only what the archive holds is recorded." if total else ".") + "</p>")
    if len(members) > 1 and same_letters:
        without = [m for m in members if m not in with_letters]
        b.append('<h2 id="letters">Letters per contest</h2><p>'
                 + (f"The {len(with_letters)} contests with a recorded lettering used the same letters, the ones in the # column"
                    if len(with_letters) > 1 else f"{contest_ref(with_letters[0], rel)} used the letters in the # column")
                 + (". No lettering is recorded for " + ", ".join(contest_ref(m, rel) for m in without) if without else "") + ".</p>")
    elif len(members) > 1:
        b.append('<h2 id="letters">Letters per contest</h2>')
        for m in members:
            lm = set_letters(doc, m)
            b.append(f"<p>{contest_ref(m, rel)}: " + (" · ".join(
                f"<b>{esc(L)}</b> {problem_link(pid, rel)}"
                for L, pid in sorted(lm.items(), key=lambda t: (len(t[0]), t[0]))) if lm else '<span class="muted">letters not known</span>') + "</p>")
    return page(sid, "\n".join(b), rel, "problemset/index.html")


def problem_page(pid: str, ent: dict, rel: str) -> str:
    """problem/<pid>.html — one problem: where it appeared, what the archive holds, where it
    can be solved."""
    rows = ent["rows"]
    p = rows[0][1]  # the first set's row carries the name/uuid; others agree (same uuid)
    first_doc = SETS.get(rows[0][0])
    private = any(r.get("status") == "private" for _s, r in rows)
    b = [crumbs(f'<a href="{rel}problem/index.html">Problems</a>', *[set_link(s, rel) for s, _r in rows[:3]]),
         f"<h1>{esc(p['name'])}</h1>"]
    if private:
        b.append('<p class="status">' + chip("private", "n", "kept private after the contest; only the name and uuid are public") + "</p>")
    d = ['<dl class="facts">']
    apps = []
    for sid, cid, L in ent["apps"]:
        apps.append((f"problem <b>{esc(L)}</b> of " if L else "") + contest_ref(cid, rel)
                    + (f' <span class="muted">· set {set_link(sid, rel)}</span>' if sid != cid else ""))
    d.append("<dt>appeared as</dt><dd>" + "<br>".join(apps) + "</dd>")
    if not private:
        seen, jl = set(), []
        for _s, r in rows:
            for j in r.get("judges") or []:
                if j["url"] not in seen:
                    seen.add(j["url"])
                    jl.append(problem_judge_links({"judges": [j]}) + (f' <span class="muted">id {esc(j["id"])}</span>' if j.get("id") else "")
                              + judge_closed_chip(j["judge"]) + f' <span class="small muted">· about {judge_link(j["judge"], rel)}</span>')
        d.append("<dt>online judge</dt><dd>" + ("<br>".join(jl) if jl else '<span class="muted">none known</span>') + "</dd>")
        have_row = next((r for _s, r in rows if "have" in r), None)
        hv = problem_have(have_row or p, first_doc)
        if have_row is not None:
            src = "recorded for this problem"
        elif any(v is not None for v in hv.values()):
            src = "from the set's holdings: only what is held for every problem of the set, or for none, is certain; the rest is not recorded per problem"
        else:
            src = "the problem archive's holdings for this set have not been entered yet"
        d.append(f"<dt>held</dt><dd>{problem_have_marks(have_row or p, first_doc)} <span class=\"small muted\">— {src}</span></dd>")
    uuids = sorted({r["uuid"] for _s, r in rows if r.get("uuid")})
    d.append("<dt>UUID</dt><dd>" + (", ".join(f"<code>{esc(u)}</code>" for u in uuids) if uuids
                                    else '<span class="muted">none yet — the problem has no package in the archive</span>') + "</dd>")
    shorts = sorted({r["short_name"] for _s, r in rows if r.get("short_name")})
    if shorts:
        d.append("<dt>short name</dt><dd>" + ", ".join(f"<code>{esc(x)}</code>" for x in shorts) + "</dd>")
    # `aliases` (ids merged into this one) are not shown: they are internal and only keep old addresses working
    notes = [r["notes"] for _s, r in rows if r.get("notes")] if not private else []
    if notes:
        d.append("<dt>notes</dt><dd>" + "; ".join(esc(x) for x in dict.fromkeys(notes)) + "</dd>")
    d.append("</dl>")
    b += d
    if not private:
        b.append(key_line(rel, "have"))
    return page(p["name"], "\n".join(b), rel, "problem/index.html")


def problemset_index(rel: str) -> str:
    rows = []
    for sid in sorted(SETS):
        doc = SETS[sid]
        total, listed = set_counts(doc)
        state = set_list_state(doc)
        fc = set_first_contest(doc)
        count = (str(total) if total else "") + (f'<span class="sub">{listed} listed</span>' if state == "partial" else "")
        rows.append(f'<tr><td class="name">{set_cell(sid, doc, rel)}</td>'
                    f'<td class="num">{len(doc["contests"])}</td>'
                    f'<td class="nw" data-v="{fc.get("season", "")}">{link_season(fc.get("season"), rel)}</td><td class="nw">{esc(set_region(doc))}</td>'
                    f'<td class="num" data-v="{total or ""}">{count}</td><td class="nw">{ {"complete": "complete", "partial": "partial", "none": "none"}[state]}</td>'
                    f'<td class="nw" data-vs="{esc(held_value(doc))}">{held_marks(doc)}</td><td class="nw">{repo_link(doc)}</td>'
                    f'<td class="small muted">{esc(doc.get("notes", ""))}</td></tr>')
    n_listed = sum(1 for d in SETS.values() if d.get("problems"))
    shared = [sid for sid, d in SETS.items() if len(d["contests"]) > 1]
    return page("Problem sets", "<h1>Problem sets</h1>"
                f'<p class="intro">{num(len(SETS))} problem sets. Most belong to the one contest of the same id; '
                f'{len(shared)} were sat by several contests, such as the Latin America regional, where every site has the same problems '
                "(sort by <b>contests</b> to see them). "
                "A set's page says what the ICPC Problem Archive holds for it; where the set was published and where it can be solved are on the contest page. "
                f"<b>Problems</b> is how many the contest had; <b>list</b> says whether we know them by name — complete for {num(n_listed)} sets, "
                "partial when only some are listed, none when only the archive's holdings are recorded.</p>"
                + key_line(rel, "held")
                + table([th("problem set"), th("contests", num=True, title="how many contests sat this set"), th("season", f=True), th("region", f=True),
                         th("problems", num=True), th("list", f="problem list"),
                         th("held", f="held for every problem"), th("archive repo"), th("notes")], rows, "flt"),
                rel, "problemset/index.html")


def problem_index(rel: str) -> str:
    rows = []
    n = 0
    for sid in sorted(SETS):
        doc = SETS[sid]
        if not doc.get("problems"):
            continue
        fc = set_first_contest(doc)
        tail = (f'<td>{set_cell(sid, doc, rel)}</td><td class="nw" data-v="{fc.get("season", "")}">{link_season(fc.get("season"), rel)}</td>'
                f'<td class="hid">{esc(set_region(doc))}</td>')
        for L, p in set_letter_cells(doc):
            n += 1
            private = p.get("status") == "private"
            judges = "|".join(sorted({judge_name(j["judge"]) for j in p.get("judges") or []})) if not private else ""
            rows.append(f'<tr><td class="name">{problem_link(p["id"], rel, p["name"])}'
                        + (" " + chip("private", "n", "kept private after the contest; name and uuid are public") if private else "") + "</td>"
                        f'<td class="nw small"><code>{esc(p.get("uuid", ""))}</code></td><td class="small sn">{esc(p.get("short_name", ""))}</td>'
                        f'<td class="letter">{esc(L)}</td>{tail}'
                        + ('<td data-vs="private"></td><td data-vs=""></td>' if private else
                           f'<td class="nw" data-vs="{esc(problem_have_value(p, doc))}">{problem_have_marks(p, doc, tips=False)}</td>'
                           f'<td data-vs="{esc(judges or "none")}">{problem_judge_links(p, tips=False)}</td>') + "</tr>")
    n_sets = sum(1 for d in SETS.values() if d.get("problems"))
    return page("Problems", "<h1>Problems</h1>"
                f'<p class="intro">{num(n)} problems from the {num(n_sets)} problem sets that are listed by name ({num(len(PROBLEMS))} distinct problems — '
                "one reused in a second set has a row in each). <b>#</b> is the letter the problem had in its contest; a <b>UUID</b> is the identity of the "
                "problem's package in the archive, where there is one. Names of problems kept private after their contest are listed; nothing else about them is.</p>"
                + key_line(rel, "have")
                + table([th("name"), th("UUID"), th("short name"), th("#"), th("problem set"), th("season", f=True), '<th class="hid" data-f>region</th>',
                         th("held", f=True), th("online judge", f=True)], rows, "flt"),
                rel, "problem/index.html")



# ---- sources (DEFINITIONS.md, Resources: source = locator, snapshot = resource, capture) ----
ALSO_AT: dict = defaultdict(list)    # source id -> [(mirror url, as_of, note)] from the catalogue's also_at
MIRROR_OF: dict = defaultdict(list)  # mirror's source id -> [primary url]
SRC_ROLES: dict = defaultdict(set)   # source id -> roles it serves anywhere in the catalogue
SRC_SCOPE: dict = defaultdict(set)   # source id -> the part(s) of a contest it covers (`scope`), when not the whole
ROLE_PAGES = ["web", "scoreboard", "frozen_scoreboard", "standings", "rankings", "icpc_standings", "problemset", "judge_page", "teams", "mirror"]


def index_sources(contests: dict) -> None:
    ALSO_AT.clear()
    MIRROR_OF.clear()
    SRC_ROLES.clear()
    SRC_SCOPE.clear()
    for c in contests.values():
        for s in sources(c):
            k = lid(s["url"])
            SRC_ROLES[k].update(s["roles"])
            if s.get("scope"):
                SRC_SCOPE[k].add(s["scope"])
            for m in also_at(s):
                ALSO_AT[k].append((m["url"], m.get("as_of"), m.get("note")))
                MIRROR_OF[lid(m["url"])].append(s["url"])
                SRC_ROLES[lid(m["url"])].add("mirror")


def field_chip(field: str) -> str:
    if field.startswith("judge-"):
        return f'<span class="chip">judge page · {esc(judge_name(field[6:]))}</span>'
    return role_chip(field)


def capture_table(caps: list[dict], url: str, rel: str, with_contest: bool = False) -> str:
    """The captures that make up one copy: when each was fetched and from where, what it is,
    and the links that open it."""
    rows = []
    for c in caps:
        flags = []
        if c.get("wrapper_fetched"):
            flags.append(chip("wrapper", "n", "fetched through the Wayback wrapper rather than the raw id_ endpoint; Wayback chrome is stripped at bake/playback"))
        links = []
        if c.get("replay"):
            links.append(f'<a class="ext" href="{REPLAY_BASE}/{esc(c["replay"])}">our copy</a>')
        links.append(local_link("archive/" + c["path"], "raw file"))
        fu = c.get("fetch_url") or url
        via = {"live": "the address", "wayback": "Wayback Machine", "icpc-api-archive": "ICPC standings data", "direct": "import"}.get(c.get("source") or "", c.get("source") or "")
        rows.append("<tr>" + (f'<td class="nw">{contest_ref(c["contest"], rel)}</td>' if with_contest else "")
                    + f'<td class="nw">{esc(str(c.get("fetched") or "")[:16].replace("T", " "))}</td>'
                    f'<td><a class="ext" href="{esc(fu)}" title="{esc(fu)}">{esc(via)}</a> {" ".join(flags)}</td>'
                    f'<td>{esc(c["artifact"].replace("_", " "))}</td>'
                    f'<td>{esc((c.get("content_type") or "").split(";")[0])}</td><td class="num">{num(c["size"]) if c.get("size") else ""}</td>'
                    f'<td><code title="sha256 {esc(c.get("sha256") or "")} · {esc(c["path"])}">{esc((c.get("sha256") or "")[:12])}</code></td>'
                    f'<td class="nw">{" · ".join(links)}</td></tr>')
    return table(([th("contest")] if with_contest else []) + [th("fetched"), th("fetched from"), th("filed as"), th("type"), th("size", num=True),
                 th("sha256"), th("open")], rows, "nosort small")


def website_crawl(site: dict, rel: str) -> str:
    """A crawled website under one snapshot: mode, scope, size, playback, and its page list."""
    d = ['<dl class="facts small">', f'<dt>website crawl</dt><dd>{contest_ref(site["contest"], rel)} · mode {esc(site.get("mode") or "")}'
         + (" " + chip("legacy wrapper", "n", "crawl seeded with a Wayback wrapper URL before the resource model; Wayback chrome stripped at playback") if site.get("legacy_wrapper") else "")
         + f' · fetched {esc(str(site.get("fetched") or "")[:16].replace("T", " "))}' + (f' ({esc(site.get("tool"))})' if site.get("tool") else "") + "</dd>"]
    if site.get("scopes"):
        d.append("<dt>scope</dt><dd>" + "; ".join(
            f'{esc(s.get("host", ""))}{esc(s.get("path", ""))} <span class="muted">({esc(s.get("rule", ""))})</span>' for s in site["scopes"]) + "</dd>")
    d.append(f'<dt>size</dt><dd>{site.get("pages") or 0} pages ({site.get("html_pages") or 0} html), {round((site.get("bytes") or 0) / 1e6, 1)} MB'
             + (f'; {site["unfetched"]} in scope not fetched, {site["offsite"]} offsite links' if "unfetched" in site else "") + "</dd>")
    cap_dir = site["dir"].rsplit("/", 1)[-1]
    d.append("<dt>open</dt><dd>" + local_link(f"site/{site['contest']}/{cap_dir}/", "archived website") + " · "
             + local_link("archive/" + site["dir"] + "/", "raw files") + "</dd>")
    d.append("</dl>")
    pl = site.get("page_list")
    if pl:
        rows = []
        for u, status, size, pts, ctype in sorted(pl, key=lambda x: str(x[0])):
            pl_link = " " + local_link(f"site/{site['contest']}/{cap_dir}/{u}", "our copy") if str(status) == "200" else ""
            rows.append(f'<tr><td class="url"><a class="ext" href="{esc(u)}">{esc(u[:110])}</a>{pl_link}</td><td>{esc(status)}</td><td>{esc(ctype or "")}</td>'
                        f'<td class="num">{size or ""}</td><td class="nw">{esc(fmt_time(pts)) if pts else ""}</td></tr>')
        d.append(f'<details><summary class="small">{len(pl)} pages</summary>'
                 + table([th("address"), th("status"), th("type"), th("size", num=True), th("snapshot")], rows, "nosort small") + "</details>")
    return "\n".join(d)


def best_open(cs: list[dict]) -> str:
    """The links that open the best copy among `cs` (a source's own page is the only place they
    appear): the newest capture the public replay serves, else a crawled website on the local
    archive server, else a raw capture."""
    order = sorted(cs, key=lambda x: (x["ts"] != "unknown", x["ts"]), reverse=True)
    for x in order:
        if x["kind"] == "capture" and x["cap"].get("replay"):
            return f'<a class="ext" href="{REPLAY_BASE}/{esc(x["cap"]["replay"])}">open our copy</a>'
    for x in order:
        if x["kind"] == "website":
            w = x["site"]
            return local_link(f"site/{w['contest']}/{w['dir'].rsplit('/', 1)[-1]}/", "open the archived website")
    for x in order:
        if x["kind"] == "capture":
            return local_link("archive/" + x["cap"]["path"], "open our copy")
    return ""


def serves_words(c: dict, rel: str) -> str:
    """What a citation uses the address for, in words: `website`, `judge page on Kattis`."""
    out = []
    for r in sorted(c["roles"], key=lambda r: RANK.get(r, 99)):
        if r == "judge_page":
            j = next((f[6:] for f in c["fields"] if f.startswith("judge-")), None)
            out.append("judge page" + (f" on {judge_link(j, rel)}" if j and j != "unknown" else ""))
        else:
            out.append(esc(role_label(r)))
    if "mirror" in c["fields"]:
        out = ["mirror of the website"]
    return ", ".join(out) or "source"


def place_rows(url: str, a: dict) -> list[str]:
    """The three places as table rows: status, what is known, the link that opens it."""
    live, wb, ours = a["live"], a["wb"], a["ours"]
    ccls = {"yes": "h", "part": "l", "no": "n", "unknown": "n"}
    det = (f'checked {esc(live["checked"])}' if live.get("checked") else "not checked yet") + (f' — {esc(plain_live(live["evidence"]))}' if live.get("evidence") else "")
    rows = [f'<tr><th>The address now</th><td>{chip(live["word"], ccls[live["s"]], LIVE_TIP.get(live["word"]))}</td><td class="small">{det}</td>'
            f'<td class="nw"><a class="ext" href="{esc(url)}">open the address</a></td></tr>']
    if wb.get("ts") and wb["s"] != "no":
        wlink = f'<a class="ext" href="{esc(wayback_link(url, wb["ts"]))}">open the snapshot</a>'
    elif wb["s"] == "unknown":
        wlink = f'<a class="ext" href="{esc(wayback_link(url))}">look for snapshots</a>'
    else:
        wlink = ""
    rows.append(f'<tr><th>Wayback Machine</th><td>{chip(wb["word"], ccls[wb["s"]])}</td><td class="small">{esc(wb["tip"])}</td><td class="nw">{wlink}</td></tr>')
    if ours["s"] == "no":
        tip = "nothing captured yet" + (" — the address turns our fetcher away; it needs a browser, or a fetcher that trusts its certificate" if live["word"] == "blocked" else
                                        " — it can be captured from the address" if live["s"] in ("yes", "part") else
                                        " — it can be captured from the Wayback snapshot" if wb["s"] == "yes" else
                                        " — and nowhere left to capture it from" if a["lost"] else "")
    else:
        tip = ours["tip"]
    rows.append(f'<tr><th>Our archive</th><td>{chip(ours["word"], "x" if a["lost"] else ccls[ours["s"]])}</td><td class="small">{esc(tip)}</td>'
                f'<td class="nw">{best_open(a["copies"])}</td></tr>')
    return rows


def source_page(k: str, L: dict, rel: str) -> str:
    """One source: what it is (which contest's what), then the three places it can be found —
    the address now, the Wayback Machine, our archive — and the copies we hold. An address that
    several contests cite gets a row per contest, since each means a different time."""
    url = L["url"]
    cits = citations(k)
    single = cits[0] if len(cits) == 1 else None
    a = avail(url, single["contest"] if single else None)
    scope = "".join(chip(x, "sc", "this source covers one part of the contest, not all of it") for x in sorted(SRC_SCOPE.get(k, ())))
    if single:
        lede = (f'The {serves_words(single, rel)} {scope}of {contest_ref(single["contest"], rel)}'
                + (f', as it was on {esc(fmt_time(single["as_of"]))}' if single["as_of"] else "") + ".")
    elif cits:
        lede = f"An address {len(cits)} contests cite. Each means what it served for that contest, so each has a row of its own below."
    else:
        lede = "No contest cites this address now; what we hold of it was filed under an earlier catalogue entry."
    b = [crumbs(f'<a href="{rel}source/index.html">Sources</a>'), f"<h1>{esc(url)}</h1>", f'<p class="lede">{lede}</p>',
         '<p class="status">' + avail_marks(a) + " " + help_link("sources", rel) + "</p>"]
    note = HUNT_STAMP.sub("", (single or {}).get("note") or "").strip()
    if note:
        b.append(f'<p class="note">{esc(note)}</p>')

    # ---- the one place the address, a Wayback snapshot and our copies are linked ----
    b.append('<h2 id="where">Where to find it</h2>')
    if single or not cits:
        b.append('<div class="tw"><table class="where nosort"><tbody>' + "\n".join(place_rows(url, a)) + "</tbody></table></div>")
    else:
        b.append('<div class="tw"><table class="where nosort"><tbody>' + place_rows(url, a)[0] + "</tbody></table></div>")
        ccls = {"yes": "h", "part": "l", "no": "n", "unknown": "n"}
        rows = []
        for c in cits:
            ac = avail(url, c["contest"])
            wb, ours = ac["wb"], ac["ours"]
            wl = f' <a class="ext" href="{esc(wayback_link(url, wb["ts"]))}">open the snapshot</a>' if wb.get("ts") and wb["s"] != "no" else ""
            rows.append(f'<tr><td class="nw">{contest_ref(c["contest"], rel)}</td><td>{serves_words(c, rel)}</td>'
                        f'<td class="nw">{esc(fmt_time(c["as_of"])) if c["as_of"] else "<span class=muted>no time named</span>"}</td>'
                        f'<td class="nw">{chip(ac["live"]["word"], ccls[ac["live"]["s"]], ac["live"]["tip"])}</td>'
                        f'<td>{chip(wb["word"], ccls[wb["s"]], wb["tip"])}{wl}</td>'
                        f'<td>{chip(ours["word"], "x" if ac["lost"] else ccls[ours["s"]], ours["tip"])} {best_open(ac["copies"])}</td></tr>')
        b.append('<p class="note">The address is one, the documents are several: what it served for each contest. '
                 "For each, whether the address still serves it, the Wayback snapshot that shows it, and our copy.</p>"
                 + table([th("contest"), th("serves"), th("as it was on"), th("the address now"), th("Wayback Machine"), th("our archive")], rows, "nosort"))

    # ---- our copies ----
    res = L["resources"]
    held = copies(k)
    shown = set()
    b.append(f'<h2 id="copies">Copies in our archive <span class="n">{len(held)}</span></h2>')
    if not held:
        b.append('<p class="empty">None.</p>')
    by_ts: dict = defaultdict(list)
    for x in held:
        by_ts[x["ts"]].append(x)
    for ts in sorted(by_ts, key=lambda t: (t == "unknown", t)):
        xs = by_ts[ts]
        via = xs[0]["via"]
        when = fmt_time(ts) if ts != "unknown" else "an unknown time"
        if via == "wayback":
            head = f"The Wayback snapshot of {esc(when)}"
            extra = f' <a class="ext small" href="{esc(wayback_link(url, ts))}">the snapshot</a>' if ts != "unknown" else ""
        elif via in ("api-dump", "icpc-api-archive"):
            head, extra = f"The ICPC standings data as of {esc(when)}", ""
        else:
            head, extra = f"The address as it was on {esc(when)}", ""
        shown.add(ts)
        b.append(f'<div class="snap" id="s-{esc(ts)}"><h3>{head}{extra}</h3>')
        caps = [x["cap"] for x in xs if x["kind"] == "capture" and not x.get("filed_under")]
        if len(caps) > 1:
            shas = {c.get("sha256") for c in caps if c.get("sha256")}
            b.append('<p class="note">' + ("Fetched more than once; every fetch returned the same bytes." if len(shas) == 1
                                           else f"Fetched {len(caps)} times; the content differed between fetches ({len(shas)} different hashes).") + "</p>")
        if caps:
            b.append(capture_table(caps, url, rel, with_contest=len(cits) > 1))
        for x in xs:
            if x.get("filed_under"):
                b.append(f'<p>Filed under {link_source(x["filed_under"], rel, res_label(x["filed_under"], None, 100))} — the same content at another address'
                         + (f' ({contest_ref(x["contest"], rel)})' if len(cits) > 1 else "") + ".</p>")
            elif x["kind"] == "website":
                b.append(website_crawl(x["site"], rel))
        b.append("</div>")
    # fetched, but not the document: kept and said, never counted as a copy
    junk = [p for p in L.get("probes") or [] if p.get("outcome") == "junk" and (p.get("path") or p.get("dir"))]
    if junk:
        rows = []
        for p in junk:
            what = (local_link("archive/" + p["path"], "raw file") if p.get("path")
                    else local_link("archive/" + p["dir"] + "/", "raw files"))
            rows.append(f'<tr><td class="nw">{esc(fmt_time(p.get("ts")) if p.get("ts") else "")}</td>'
                        f'<td class="nw">{"Wayback Machine" if p.get("via") == "wayback" else "the address"}</td>'
                        + (f'<td class="nw">{contest_ref(p["contest"], rel)}</td>' if len(cits) > 1 else "")
                        + f'<td title="{esc(p.get("evidence") or "")}">{esc(plain_why(p.get("evidence")))}</td><td class="nw">{what}</td></tr>')
        b.append(f'<h3 id="set-aside">Set aside <span class="n">{len(junk)}</span></h3>'
                 '<p class="note">Fetched, but what came back is not the document: an error page, an empty app shell, a login wall, a placeholder. Kept, and not counted as a copy.</p>'
                 + table([th("shows"), th("fetched from")] + ([th("contest")] if len(cits) > 1 else []) + [th("why it is not the document"), th("open")], rows, "nosort small"))
    # anchors that older links point at (a time the catalogue names without a copy)
    b.append("".join(f'<span id="s-{esc(ts)}"></span>' for ts in res if ts not in shown))

    d = []
    if ALSO_AT.get(k):
        d.append("<dt>also at</dt><dd>" + "<br>".join(
            link_source(mu, rel, res_label(mu, mts, 110), mts) + " " + avail_marks(avail(mu))
            + (f' <span class="muted">— {esc(n)}</span>' if n else "") for mu, mts, n in ALSO_AT[k]) + "</dd>")
    if MIRROR_OF.get(k):
        d.append("<dt>mirror of</dt><dd>" + "<br>".join(link_source(pu, rel, pu[:110]) for pu in dict.fromkeys(MIRROR_OF[k])) + "</dd>")
    d.append(f'<dt>source id</dt><dd><code>{k}</code></dd>')
    b.append('<dl class="facts small muted">' + "".join(d) + "</dl>")
    return page(host_label(url, 60), "\n".join(b), rel, "source/index.html")


def source_list(rel: str, role: str | None = None) -> str:
    """source/index.html (every source) and source/by-role/<role>.html (one role): the same
    page, the same columns, the same filters — the role pages are that table cut down."""
    counts = Counter(r for roles in SRC_ROLES.values() for r in roles)
    here = "../" if role else ""
    tabs = ["<span>" + ("<b>all</b>" if not role else f'<a href="{here}index.html">all</a>') + f' <span class="muted small">{num(len(RES.locs))}</span></span>']
    for r in ROLE_PAGES:
        lab = esc(role_label(r))
        tabs.append("<span>" + (f"<b>{lab}</b>" if r == role else f'<a href="{here}by-role/{r}.html">{lab}</a>') + f' <span class="muted small">{num(counts[r])}</span></span>')
    rows = []
    for k, L in RES.locs.items():
        roles = sorted(SRC_ROLES.get(k, set()), key=lambda r: RANK.get(r, 99))
        if role and role not in roles:
            continue
        url = L["url"]
        cs = [c["contest"] for c in citations(k)]
        a = avail(url, cs[0] if len(cs) == 1 else None)
        rows.append(f'<tr><td class="url"><a href="{rel}source/{k}/index.html">{esc(url if len(url) <= 90 else url[:89] + "…")}</a></td>'
                    f'<td data-vs="{esc("|".join(role_label(r) for r in roles))}" class="small">{esc(", ".join(role_label(r) for r in roles))}</td>'
                    f'<td data-v="{len(cs)}" class="small">{", ".join(contest_ref(c, rel) for c in cs[:3])}{" +" + str(len(cs) - 3) if len(cs) > 3 else ""}</td>'
                    f'<td class="nw" data-vs="{esc(avail_values(a))}">{avail_marks(a)}</td>'
                    f'<td class="nw small">{esc(a["live"].get("checked") or "")}</td>'
                    f'<td class="num">{len(copies(k))}</td></tr>')
    title = f"{role_label(role).capitalize()} sources" if role else "Sources"
    return page(title, f"<h1>{esc(title)}</h1>"
                f'<p class="intro">{"Sources serving this role" if role else "Every address the catalogue knows, and its mirrors"}: {num(len(rows))}. '
                "A <b>source</b> is an address as a contest means it: what it served for that contest. It can be found in up to three places — "
                "at its address now, in the Wayback Machine, in our archive — and every list shows the three together. "
                "The address, the snapshot and our copies are opened from the source's own page.</p>"
                '<p class="tabs">' + " ".join(tabs) + "</p>" + key_line(rel, "available")
                + table([th("address"), th("roles", f=True), th("contests"), AVAIL_TH, th("address checked"), th("copies", num=True)], rows, "flt"),
                rel, "source/index.html")


# ---- judges ----
def judge_usage(contests: dict) -> tuple[dict, dict]:
    """(judge -> problem ids linking to it, judge -> [(contest id, source)] judge pages)."""
    probs, pages = defaultdict(set), defaultdict(list)
    for pid, ent in PROBLEMS.items():
        for _s, r in ent["rows"]:
            for j in r.get("judges") or []:
                probs[j["judge"]].add(pid)
    for c in list(contests.values()) + NM:
        for s in by_role(c, "judge_page"):
            pages[s.get("judge") or "judge"].append((c["id"], s))
    return probs, pages


def judge_status(j: dict) -> str:
    st = j.get("status", "")
    return chip(st + (f" {j['closed']}" if j.get("closed") else ""), {"active": "h", "closed": "n"}.get(st, "l"),
                "its pages survive only in Wayback snapshots taken before the closing date" if st == "closed" else None)


def judge_page(jid: str, j: dict, probs: set, pages: list, rel: str) -> str:
    ncon = len({c for c, _s in pages})
    b = [crumbs(f'<a href="{rel}judge/index.html">Judges</a>'), f'<h1>{esc(j.get("name") or jid)}</h1>',
         '<p class="status">' + judge_status(j) + "</p>",
         f'<div class="nums"><div><b>{num(ncon)}</b><span><a href="#contests">contests</a></span></div>'
         f'<div><b>{num(len(probs))}</b><span><a href="#problems">problems</a></span></div></div>',
         '<dl class="facts">', f'<dt>site</dt><dd><a class="ext" href="{esc(j["url"])}">{esc(j["url"])}</a></dd>']
    for key, lab in (("contest_url", "contest address"), ("problem_url", "problem address")):
        if j.get(key):
            b.append(f"<dt>{lab}</dt><dd><code>{esc(j[key])}</code></dd>")
    b.append(f'<dt>judge id</dt><dd><code>{esc(jid)}</code></dd></dl>')
    b.append(f'<h2 id="contests">Contests <span class="n">{ncon}</span></h2>'
             '<p class="note">Contests that have a page on this judge'
             + (f" — {len(pages)} pages, since some contests have more than one." if len(pages) != ncon else ".") + "</p>")
    if pages:
        rows = []
        for cid, s in sorted(pages, key=lambda t: (t[0], t[1]["url"])):
            c = CONTESTS.get(cid) or {}
            found = source_note(s)
            rows.append(f'<tr><td class="nw">{contest_ref(cid, rel)}</td><td class="nw" data-v="{esc(c.get("date", ""))}">{link_date(c.get("date"), rel)}</td>'
                        f'<td class="url">{link_source(s["url"], rel, res_label(s["url"], s.get("as_of"), 100), s.get("as_of"))}</td>'
                        + avail_cell(s["url"], cid, s) + f'<td class="small muted">{esc(found)}</td></tr>')
        b.append(table([th("contest"), th("date"), th("judge page"), AVAIL_TH, th("note")], rows))
    else:
        b.append('<p class="empty">No contest has a page on this judge recorded.</p>')
    b.append(f'<h2 id="problems">Problems <span class="n">{len(probs)}</span></h2>'
             + ('<p class="note">Problems that link to this judge.</p>' if probs else ""))
    if probs:
        rows = []
        for pid in sorted(probs, key=lambda x: problem_name(x).lower()):
            r = PROBLEMS[pid]["rows"][0][1]
            jl = [jj for _s, rr in PROBLEMS[pid]["rows"] for jj in rr.get("judges") or [] if jj["judge"] == jid]
            jl = list({jj["url"]: jj for jj in jl}.values())
            rows.append(f'<tr><td>{problem_link(pid, rel, r["name"])}</td>'
                        f'<td class="nw">{problem_judge_links({"judges": jl}, by_id=True)}</td>'
                        f'<td>{", ".join(set_link(s, rel) for s, _r in PROBLEMS[pid]["rows"])}</td></tr>')
        b.append(table([th("problem"), th("on the judge"), th("problem set")], rows))
    else:
        b.append('<p class="empty">No problem links to this judge yet.</p>')
    return page(j.get("name") or jid, "\n".join(b), rel, "judge/index.html")


def judge_index(probs: dict, pages: dict, rel: str) -> str:
    rows = []
    for jid, j in JUDGES.items():
        rows.append(f'<tr><td class="name">{judge_link(jid, rel)}<span class="sub">{esc(re.sub(r"^https?://", "", j["url"]).rstrip("/"))}</span></td>'
                    f'<td class="nw" data-v="{esc(j.get("status", ""))}">{judge_status(j)}</td>'
                    f'<td class="num">{len({c for c, _s in pages.get(jid, [])})}</td><td class="num">{len(probs.get(jid, ()))}</td></tr>')
    unknown = [x for x in sorted(set(probs) | set(pages)) if x not in JUDGES]
    return page("Online judges", "<h1>Online judges</h1>"
                f'<p class="intro">{len(JUDGES)} online judges where ICPC problems can be solved, or could. <b>Contests</b> counts contests with a page on the judge; '
                "<b>problems</b> counts problems that link to it. A judge that has closed survives only in Wayback snapshots taken before it shut down.</p>"
                + table([th("judge"), th("status", f=True), th("contests", num=True), th("problems", num=True)], rows)
                + ('<p class="note">Judge ids used but not registered: ' + ", ".join(esc(x) for x in unknown) + "</p>" if unknown else ""),
                rel, "judge/index.html")


# ---- locations ----
def loc_years(nid: str) -> tuple[int, int] | None:
    ys = [int(c.rsplit("-", 1)[1]) for c in LOC_SUB.get(nid, ())]
    return (min(ys), max(ys)) if ys else None


def loc_row(nid: str, rel: str, within: str | None = None) -> str:
    """One location in a table: name, type, what it is in, and what was held there."""
    n = LOC[nid]
    chain = location_chain(LOC, nid)[1:]
    if within:
        chain = chain[:next((i for i, x in enumerate(chain) if x["id"] == within), len(chain))]
    country = next((x["name"] for x in location_chain(LOC, nid) if x["type"] == "country"), "")
    ys = loc_years(nid)
    kids = Counter(LOC[k]["type"] for k in LOC_KIDS.get(nid, []))
    below = ", ".join(f"{v} {'cities' if t == 'city' else t + 's'}" if v != 1 else f"1 {t}" for t, v in sorted(kids.items(), key=lambda kv: TYPE_ORDER[kv[0]]))
    return (f'<tr><td>{loc_link(nid, rel)}</td><td class="nw">{esc(n["type"])}</td>'
            f'<td class="small">{" › ".join(loc_link(x["id"], rel) for x in chain)}</td>'
            + ("" if within else f'<td class="nw small">{esc(country)}</td>')
            + f'<td class="num">{len(LOC_SUB.get(nid, ()))}</td><td class="num">{len(set(LOC_DIRECT.get(nid, [])))}</td>'
            f'<td class="nw" data-v="{ys[0] if ys else ""}">{ys[0] if ys else ""}</td><td class="nw" data-v="{ys[1] if ys else ""}">{ys[1] if ys else ""}</td>'
            f'<td class="small muted">{below}</td></tr>')


def location_page(nid: str, rel: str) -> str:
    n = LOC[nid]
    chain = location_chain(LOC, nid)[1:]
    sub = LOC_SUB.get(nid, set())
    cs = [CONTESTS[c] for c in sorted(sub, key=lambda c: (CONTESTS[c].get("date") or c.rsplit("-", 1)[1], c), reverse=True)]
    ys = loc_years(nid)
    b = [crumbs(f'<a href="{rel}location/index.html">Locations</a>', *[loc_link(x["id"], rel) for x in reversed(chain)]),
         f"<h1>{esc(n['name'])}</h1>", f'<p class="lede">{esc(n["type"].capitalize())}'
         + (" in " + ", ".join(esc(x["name"]) for x in chain) if chain else "") + "</p>"]
    st = content_counts(cs)
    series = Counter(SERIES_OF[c["id"]] for c in cs)
    b.append(content_nums(st, (f"<div><b>{ys[0]}–{ys[1]}</b><span>first to latest</span></div>" if ys else "")
                          + f"<div><b>{len(series)}</b><span>series</span></div>"))
    d = ['<dl class="facts">']
    if n.get("aliases"):
        d.append("<dt>also written</dt><dd>" + ", ".join(esc(a) for a in n["aliases"]) + "</dd>")
    if series:
        top = series.most_common(12)
        d.append("<dt>series held here</dt><dd>" + ", ".join(f'{link_series(s, rel)} <span class="muted">{k}</span>' for s, k in top)
                 + (f' <span class="muted">and {len(series) - 12} more</span>' if len(series) > 12 else "") + "</dd>")
    if n.get("iso"):
        d.append(f"<dt>ISO code</dt><dd>{esc(n['iso'])}</dd>")
    if n.get("code"):
        d.append(f"<dt>code</dt><dd>{esc(n['code'])}</dd>")
    if n.get("geonameid"):
        d.append(f'<dt>GeoNames</dt><dd><a class="ext" href="https://www.geonames.org/{n["geonameid"]}/">{n["geonameid"]}</a></dd>')
    if n.get("notes"):
        d.append(f"<dt>notes</dt><dd>{esc(n['notes'])}</dd>")
    d.append(f'<dt>location id</dt><dd><code>{esc(nid)}</code></dd></dl>')
    b += d
    kids = [k for k in LOC_KIDS.get(nid, [])]
    if kids:
        desc = [k for k in LOC if k != nid and any(x["id"] == nid for x in location_chain(LOC, k))] if n["type"] in ("country", "region") else kids
        desc.sort(key=lambda k: (-len(LOC_SUB.get(k, ())), LOC[k]["name"]))
        b.append(f'<h2 id="places">Places in {esc(n["name"])} <span class="n">{len(desc)}</span></h2>')
        b.append(table([th("location"), th("type", f=True), th("in"), th("contests", num=True, title="contests held here or anywhere inside"),
                        th("exactly here", num=True, title="contests whose site is this very place"), th("first"), th("latest"), th("contains")],
                       [loc_row(k, rel, within=nid) for k in desc]))
    b.append(f'<h2 id="contests">Contests <span class="n">{len(cs)}</span></h2>')
    if cs:
        def at(c):
            here = [x for x in held_at(c)[0] if x == nid or any(a["id"] == nid for a in location_chain(LOC, x))]
            spots = [loc_link(x, rel) for x in dict.fromkeys(here) if x != nid]
            return '<td class="small">' + (", ".join(spots[:3]) + (f" +{len(spots) - 3}" if len(spots) > 3 else "") if spots else '<span class="muted">here</span>') + "</td>"
        b.append(key_line(rel, "results", "website", "held"))
        b.append(contest_table(cs, rel, ("contest+name", "date", "series", "season", "results", "problems", "website"),
                               extra=(th("held at"), at)))
    else:
        b.append('<p class="empty">No contest is recorded here or anywhere inside.</p>')
    return page(n["name"], "\n".join(b), rel, "location/index.html")


def location_index(rel: str) -> str:
    types = Counter(n["type"] for n in LOC.values())
    countries = sorted((nid for nid, n in LOC.items() if n["type"] == "country"), key=lambda x: (-len(LOC_SUB.get(x, ())), LOC[x]["name"]))
    placed = {c for s in LOC_DIRECT.values() for c in s}
    ran = [c for c in CONTESTS.values() if c.get("status") != "upcoming"]
    n_placed = sum(1 for c in ran if c["id"] in placed)
    crows = []
    for nid in countries:
        cs = [CONTESTS[c] for c in LOC_SUB.get(nid, ())]
        st = content_counts(cs)
        ys = loc_years(nid)
        desc = [k for k in LOC if any(x["id"] == nid for x in location_chain(LOC, k)[1:])]
        cities = sorted((k for k in desc if LOC[k]["type"] == "city"), key=lambda k: -len(LOC_SUB.get(k, ())))
        crows.append(f'<tr><td class="nw">{loc_link(nid, rel)}</td><td class="num">{len(cs)}</td>'
                     f'<td class="nw" data-v="{ys[0] if ys else ""}">{f"{ys[0]}–{ys[1]}" if ys else ""}</td>'
                     f'<td class="num">{len(cities)}</td><td class="num">{sum(1 for k in desc if LOC[k]["type"] == "institution")}</td>'
                     f'<td class="small">{", ".join(loc_link(k, rel) + f" <span class=muted>{len(LOC_SUB.get(k, ()))}</span>" for k in cities[:4] if LOC_SUB.get(k))}</td>'
                     + content_cells(st) + "</tr>")
    arows = [loc_row(nid, rel) for nid in sorted(LOC, key=lambda k: (-len(LOC_SUB.get(k, ())), LOC[k]["name"]))]
    return page("Locations", "<h1>Locations</h1>"
                f'<p class="intro">Where contests were held, as one tree: {types["country"]} countries, {types["region"]} states and provinces, '
                f'{num(types["city"])} cities and {num(types["institution"])} institutions. {num(n_placed)} of the {num(len(ran))} contests that ran are placed in it '
                f"({pct(n_placed, len(ran))}%); the rest are known only by a line of text, or not at all. A contest counts for the place it was held and for everything that place is in.</p>"
                f'<div class="nums"><div><b>{types["country"]}</b><span>countries</span></div><div><b>{types["region"]}</b><span>states and provinces</span></div>'
                f'<div><b>{num(types["city"])}</b><span>cities</span></div><div><b>{num(types["institution"])}</b><span>institutions</span></div></div>'
                f'<p class="tabs"><a href="#countries">Countries</a> <a href="#all">Every location</a></p>'
                f'<h2 id="countries">Countries <span class="n">{len(countries)}</span></h2>'
                + table([th("country"), th("contests", num=True), th("years"), th("cities", num=True), th("institutions", num=True), th("most often in")] + CONTENT_HEADS, crows)
                + f'<h2 id="all">Every location <span class="n">{num(len(LOC))}</span></h2>'
                + table([th("location"), th("type", f=True), th("in"), th("country", f=True), th("contests", num=True, title="contests held here or anywhere inside"),
                         th("exactly here", num=True, title="contests whose site is this very place"), th("first"), th("latest"), th("contains")], arows, "flt"),
                rel, "location/index.html")



# ---- coverage ----
COV_COLS = (
    ("any", "any result", "any result source at all, counting the CMS's own ICPC standings"),
    ("pub", "published", "a published scoreboard, standings or rankings (not just the CMS's data)"),
    ("sb", "scoreboard", "a full per-problem scoreboard"),
    ("res_arch", "result archived", "we hold an archived copy of a published result"),
    ("set", "problem set", "the problem set is recorded"),
    ("stmt", "statements", "the problem archive holds every statement"),
    ("judge", "online judge", "the problems are on an online judge"),
    ("web", "website", "a website address is known"),
    ("web_arch", "website archived", "we hold a crawl of the website"),
    ("date", "dated", "the full date is known"),
    ("place", "placed", "placed in the location tree"),
)
ERAS = (("to 1998", 0, 1998), ("1999–2007", 1999, 2007), ("2008–2015", 2008, 2015), ("2016 on", 2016, 9999))


def season_of(c: dict) -> int:
    """The season (end year) of a contest; the id year stands in where none is recorded."""
    return c.get("season") or int(c["id"].rsplit("-", 1)[1])


def cov_flags(c: dict) -> dict:
    pb = set_for(c)
    bt = best_tier(c)
    return {"n": 1, "any": bt != "none", "pub": bt not in ("none", "icpc"), "sb": has_role(c, "scoreboard"),
            "res_arch": results_held(c), "set": bool(pb), "stmt": pb.get("statement") == "full", "judge": has_role(c, "judge_page"),
            "web": web_state(c) == "link", "web_arch": c["id"] in website_of, "date": bool(full_date(c)),
            "place": bool(held_at(c)[0]), "dark": bt == "none",
            "repo": bool(pb.get("repo")), **{k + "_full": pb.get(k) == "full" for k, *_ in HELD_KINDS}}


def agg(flags) -> dict:
    t: dict = defaultdict(int)
    for f in flags:
        for k, v in f.items():
            t[k] += int(v)
    return t


def cov_table(label: str, rows: list[tuple[str, dict]], cls: str = "", extra_heads: list[str] | None = None) -> str:
    """One coverage table: a row per group, the same eleven shares in every table."""
    heads = [th(label)] + (extra_heads or []) + [th("contests", num=True)] + [th(lab, num=True, title=tip) for _k, lab, tip in COV_COLS] \
        + [th("nothing", num=True, title="contests with no result source of any kind")]
    body = [f"<tr>{lab}<td class=\"num\">{t['n']}</td>" + "".join(pct_cell(t[k], t["n"]) for k, *_ in COV_COLS)
            + f'<td class="num">{t["dark"] or ""}</td></tr>' for lab, t in rows]
    return table(heads, body, cls)


def heat_table(title: str, key: str, ran: list[tuple[dict, dict]]) -> str:
    """Region x era, one share per cell, shaded by how much we hold."""
    rows = []
    for r in REGIONS:
        cells = []
        for _lab, lo, hi in ERAS:
            t = agg(f for c, f in ran if SERIES_REGION.get(SERIES_OF[c["id"]]) == r and lo <= season_of(c) <= hi)
            if not t["n"]:
                cells.append('<td class="hc muted">–</td>')
                continue
            p = pct(t[key], t["n"])
            cells.append(f'<td class="hc" style="background:color-mix(in srgb,var(--held) {round(p * .6)}%,var(--paper))" '
                         f'title="{t[key]} of {t["n"]} contests">{p}%</td>')
        rows.append(f'<tr><td class="nw">{esc(r)}</td>' + "".join(cells) + "</tr>")
    return (f'<div><h3>{title}</h3><table class="heat nosort"><thead><tr><th></th>'
            + "".join(f'<th class="num">{esc(lab)}</th>' for lab, *_ in ERAS) + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def coverage_page(series_docs: dict, contests: dict) -> str:
    ran = [(c, cov_flags(c)) for c in contests.values() if c.get("status") != "upcoming"]
    tot = agg(f for _c, f in ran)
    n = tot["n"]

    def funnel(title, steps):
        return (f"<div><h3>{title}</h3><table class=\"nosort heat\"><tbody>" + "".join(
            f'<tr><td>{lab}</td><td class="num">{num(tot[k])}</td>' + pct_cell(tot[k], n) + "</tr>" for k, lab in steps) + "</tbody></table></div>")
    b = ["<h1>Coverage</h1>",
         f'<p class="intro">How much of the {num(n)} contests that ran we can account for. Each of the three kinds of content — results, problems, website — '
         "is counted twice: do we know where it is, and do we hold a copy. Every table below uses the same eleven columns (hover a header for its definition) "
         f'and sorts on any of them. The worklist behind the gaps is <a href="wanted.html">most wanted</a>; the same data, one square per contest, is <a href="grid.html">the grid</a>.</p>',
         '<div class="nums" style="align-items:flex-start;gap:1rem 3rem">'
         + funnel("Results", (("any", "any result source"), ("pub", "a published result"), ("sb", "a full scoreboard"), ("res_arch", "an archived copy")))
         + funnel("Problems", (("set", "problem set recorded"), ("stmt", "every statement held"), ("judge", "on an online judge")))
         + funnel("Website", (("web", "address known"), ("web_arch", "archived")))
         + funnel("Basics", (("date", "full date known"), ("place", "placed in the location tree")))
         + "</div>",
         f'<p class="note">{num(tot["dark"])} contests have no result source of any kind. A website counts as known only when an address was found; '
         "contests confirmed to have had no website are not counted as missing in the wanted list.</p>",
         '<p class="tabs">Jump to: <a href="#where">where the holes are</a> <a href="#region">by region</a> <a href="#season">by season</a> '
         '<a href="#series">by series</a> <a href="#holdings">problem archive holdings</a></p>',
         '<h2 id="where">Where the holes are</h2><p class="note">Share of contests per region and era; darker is fuller. Eras are by season.</p>'
         '<div class="nums" style="align-items:flex-start;gap:1rem 2.5rem">'
         + heat_table("Results archived", "res_arch", ran) + heat_table("Problem set recorded", "set", ran) + heat_table("Website archived", "web_arch", ran) + "</div>"]

    b.append('<h2 id="region">By region</h2>')
    rows = [(f'<td class="nw">{esc(r)}</td>', agg(f for c, f in ran if SERIES_REGION.get(SERIES_OF[c["id"]]) == r)) for r in REGIONS]
    rows.append(('<td class="nw"><b>all</b></td>', tot))
    b.append(cov_table("region", rows))

    b.append('<h2 id="season">By season</h2>')
    by_s = defaultdict(list)
    for c, f in ran:
        by_s[season_of(c)].append(f)
    b.append(cov_table("season", [(f'<td class="nw" data-v="{s}">{link_season(s, "") if s in BY_SEASON else f"{s - 1}–{s}"}</td>', agg(by_s[s])) for s in sorted(by_s, reverse=True)]))

    b.append('<h2 id="series">By series</h2><p class="note">Sorted by the number of contests with nothing at all — the top of this table is where a find matters most.</p>')
    by_ser = defaultdict(list)
    for c, f in ran:
        by_ser[SERIES_OF[c["id"]]].append(f)
    srows = []
    for s, fl in by_ser.items():
        t = agg(fl)
        y0, y1 = series_years(series_docs[s])
        srows.append((t["dark"], t["n"], s, (f'<td class="nw">{link_series(s, "")}</td><td class="nw">{esc(SERIES_REGION.get(s, ""))}</td>'
                                              f'<td class="nw" data-v="{y0}">{y0}–{y1}</td>', t)))
    b.append(cov_table("series", [r for *_x, r in sorted(srows, key=lambda x: (-x[0], -x[1], x[2]))], "flt",
                       [th("region", f=True), th("years")]))

    b.append('<h2 id="holdings">Problem archive holdings</h2><p class="note">What the ICPC Problem Archive holds, as a share of the contests that ran in each region: '
             "a repo exists, and each kind of material is there for every problem of the set.</p>")
    heads = [th("region"), th("contests", num=True), th("problem set", num=True, title="the problem set is recorded"), th("repo", num=True, title="a repo in the problem archive holds material")] \
        + [th(w, num=True, title=f"{w} held for every problem") for _k, _l, w in HELD_KINDS]
    hrows = []
    for r in REGIONS + ["all"]:
        t = tot if r == "all" else agg(f for c, f in ran if SERIES_REGION.get(SERIES_OF[c["id"]]) == r)
        hrows.append(f'<tr><td class="nw">{"<b>all</b>" if r == "all" else esc(r)}</td><td class="num">{t["n"]}</td>' + pct_cell(t["set"], t["n"]) + pct_cell(t["repo"], t["n"])
                     + "".join(pct_cell(t[k + "_full"], t["n"]) for k, *_ in HELD_KINDS) + "</tr>")
    b.append(table(heads, hrows))
    return page("Coverage", "\n".join(b), "", "coverage.html")


# ---- most wanted ----
WANT_COLS = [  # (best tier held, column title, what is wanted)
    ("none", "nothing", "no result of any kind, not even in the ICPC standings system"),
    ("icpc", "ICPC standings only", "only the CMS's own result data (formally official, often wrong in practice) — the published scoreboard is wanted"),
    ("rankings", "rankings only", "order of teams only — standings or scoreboard wanted"),
    ("standings", "standings only", "totals per team — the per-problem scoreboard wanted"),
    ("frozen_scoreboard", "frozen only", "frozen scoreboard — the final scoreboard wanted"),
]
WEB_COLS = [("nolink", "no website known", "no website address found yet (contests confirmed to have had none are not listed)"),
            ("noarch", "website not archived", "the address is known; we hold no copy"),
            ("lost", "lost", "a source that is dead at its address, has no Wayback snapshot and was never captured here: gone unless someone kept a copy")]


def wanted_page(series_docs: dict) -> str:
    tot: dict = defaultdict(int)
    sections = []
    for g in REGIONS:
        sec = []
        for sname in sorted(series_docs):
            if SERIES_REGION.get(sname) != g:
                continue
            cells = defaultdict(list)
            for c in series_docs[sname]["contests"]:
                if c.get("status") == "upcoming":
                    continue
                cid = c["id"]
                bt = best_tier(c)
                if bt != "scoreboard":
                    cells[bt].append(link_contest(cid, "", False))
                    tot[bt] += 1
                ws = web_state(c)
                if ws == "unknown":
                    cells["nolink"].append(link_contest(cid, "", False))
                    tot["nolink"] += 1
                elif ws == "link" and cid not in website_of:
                    cells["noarch"].append(link_contest(cid, "", False))
                    tot["noarch"] += 1
                gone = [u for u, _w, held in lost_locators(c) if not held]
                if gone:
                    cells["lost"].append(link_contest(cid, "", False) + f'<span class="small muted" title="{esc("; ".join(gone))}"> ×{len(gone)}</span>')
                    tot["lost"] += 1
            if cells:
                sec.append(f'<tr><td class="nw">{link_series(sname, "")}</td>'
                           + "".join(f'<td class="small ids">{" ".join(cells[k])}</td>' for k, *_ in WANT_COLS + WEB_COLS) + "</tr>")
        if sec:
            sections.append(f"<h2>{esc(g)}</h2>" + table([th("series")] + [th(t, title=w) for _k, t, w in WANT_COLS + WEB_COLS], sec, "nosort"))
    body = ["<h1>Most wanted</h1>",
            '<p class="intro">Every contest that ran, filed under the <b>best result we know</b> — from nothing at all up to a frozen scoreboard. Anything better is wanted; '
            "a contest with a full scoreboard is not listed. The last three columns are about the website and about sources that are gone. "
            f'Know where any of this lives? <a href="about.html#contribute">Tell us.</a></p>',
            '<div class="nums">' + "".join(f"<div><b>{num(tot[k])}</b><span>{t}</span></div>" for k, t, _w in WANT_COLS + WEB_COLS) + "</div>"]
    return page("Most wanted", "\n".join(body + sections), "", "coverage.html")


# ---- the grid ----
def grid_page(series_docs: dict, contests: dict) -> str:
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
        return {"scoreboard": ("c-sb", "scoreboard"), "frozen_scoreboard": ("c-sb", "frozen scoreboard"),
                "standings": ("c-res", "standings only"), "rankings": ("c-res", "rankings only"),
                "icpc": ("c-ist", "ICPC standings only"), "none": ("c-none", "no result known")}[best_tier(c)]

    def first_year(s):
        return (min(int(c["id"].rsplit("-", 1)[1]) for c in series_docs[s]["contests"]), s)
    groups = [("World Finals", [s for s in series_docs if SERIES_TIER.get(s) == "world-finals"]),
              ("Championships", sorted((s for s in series_docs if s in CHAMPIONSHIPS), key=first_year))]
    for r in REGIONS[1:]:
        groups.append((r, sorted((s for s in series_docs if SERIES_REGION.get(s) == r and s not in CHAMPIONSHIPS and SERIES_TIER.get(s) != "world-finals"), key=first_year)))
    g = ['<div class="tw" style="overflow-x:auto"><table class="grid"><thead><tr><th class="lbl"></th>']
    g += [f"<th>{y}</th>" for y in range(y0, y1 + 1)]
    g.append("</tr></thead><tbody>")
    ncols = y1 - y0 + 2
    for gname, sids in groups:
        if not sids:
            continue
        g.append(f'<tr class="grp"><td class="lbl" colspan="{ncols}">{esc(gname)}</td></tr>')
        for sid in sids:
            g.append(f'<tr><td class="lbl">{link_series(sid, "")}</td>')
            for y in range(y0, y1 + 1):
                cid = by_sy.get((sid, y))
                if cid:
                    cls, why = cell_class(contests[cid])
                    cc = contests[cid]
                    g.append(f'<td><a class="cell {cls}" href="contest/{esc(cid)}.html" '
                             f'title="{esc(cid)}{" · " + esc(cc["date"]) if cc.get("date") else ""} — {why}"></a></td>')
                elif lineage_at.get((sid, y)):
                    tgt = lineage_at[(sid, y)][0]
                    g.append(f'<td><a class="c-lin" href="series/{esc(tgt)}.html" title="continues as {esc(tgt)} ({y})">→</a></td>')
                else:
                    g.append("<td></td>")
            g.append("</tr>")
    g.append("</tbody></table></div>")
    sw = 'style="display:inline-block;vertical-align:-2px"'
    legend = (f'<p class="key"><span class="cell c-sb" {sw}></span> scoreboard &nbsp; <span class="cell c-res" {sw}></span> standings or rankings &nbsp; '
              f'<span class="cell c-ist" {sw}></span> ICPC standings only &nbsp; <span class="cell c-none" {sw}></span> no result known &nbsp; '
              f'<span class="cell c-up" {sw}></span> upcoming &nbsp; → the series continues under another name</p>')
    return page("The grid", "<h1>The grid</h1><p class=\"intro\">Every contest on one screen: a row per series, a column per year, "
                "coloured by the best result we know. Click a square for the contest.</p>" + legend + "".join(g), "", "coverage.html")


# ---- appendices: CMS id ledger, non-mainline registry ----
def cms_page(contests: dict) -> str:
    cms_rows = {}
    for cid, c in contests.items():
        for i in (c.get("cms_ids") or []):
            cms_rows[int(i)] = ("in the catalogue", link_contest(cid, "", False), esc(c.get("name") or ""))
    tri = yaml.safe_load((ROOT / "registry" / "cms-triage.yaml").read_text())
    for e in (tri.get("excluded") or []):
        cms_rows.setdefault(int(e["cms_id"]), (f'excluded: {e.get("reason")}', "", esc(str(e.get("name") or ""))))
    prop_p = ROOT / "registry" / "cms-triage-proposed.yaml"
    if prop_p.exists():
        for e in (yaml.safe_load(prop_p.read_text()).get("proposed") or []):
            cms_rows.setdefault(int(e["cms_id"]), (f'proposed: {e.get("reason")}', "", esc(str(e.get("name") or ""))))
    wl_p = ROOT / "data" / "reconciliation-worklist.json"
    if wl_p.exists():
        for e in json.loads(wl_p.read_text()):
            try:
                i = int(e.get("Contest ID"))
            except (TypeError, ValueError):
                continue
            cms_rows.setdefault(i, ("not judged", "", esc(str(e.get("Full name") or ""))))
    counts = Counter(st.split(":")[0] for st, _l, _n in cms_rows.values())
    rows = [f'<tr><td class="num">{i}</td><td class="nw">{link}</td><td class="nw" data-v="{esc(st)}">{chip(st, "h" if st == "in the catalogue" else "n")}</td>'
            f'<td class="small">{name}</td><td class="nw small">{cms_links(i).split(" ", 1)[1]}</td></tr>'
            for i, (st, link, name) in sorted(cms_rows.items())]
    return page("CMS id ledger", "<h1>CMS id ledger</h1>"
                f'<p class="intro">Every contest id of the ICPC CMS this project has looked at: {num(len(cms_rows))} ids — {num(counts["in the catalogue"])} are contests in the catalogue, '
                f'{num(counts["excluded"])} are excluded with a reason (cancelled, camp, challenge, junk, minor, structural), {num(counts["proposed"])} carry a proposed '
                f'class nobody has reviewed, and {num(counts["not judged"])} have not been judged at all.</p>'
                + table([th("CMS id", num=True), th("contest"), th("status", f=True), th("name in the CMS"), th("in the CMS")], rows, "flt"), "", "coverage.html")


def non_mainline_page() -> str:
    rows = []
    for c in sorted(NM, key=lambda c: c["id"]):
        pb = set_for(c)
        srcs = " ".join(f'<a class="ext" href="{esc(s["url"])}">{esc(role_label(s["roles"][0]))}</a>' for s in sources(c))
        rows.append(f'<tr><td class="name">{esc(c["id"])}<span class="sub">{esc(c.get("name", ""))}</span></td><td class="nw">{esc(c.get("date", ""))}</td>'
                    f'<td class="small">{esc(c.get("reason", ""))}</td><td class="small">{srcs}</td>'
                    f'<td class="nw">{set_link(pb["id"], "") if pb else ""}</td><td class="nw">{cms_cell(c)}</td></tr>')
    return page("Non-mainline registry", "<h1>Non-mainline registry</h1>"
                f'<p class="intro">{len(NM)} real contests outside the advancement hierarchy — university opens and the like — kept for reference. '
                "They are not in the catalogue and have no contest page; their problem sets, where recorded, do.</p>"
                + table([th("contest"), th("date"), th("why it is not in the catalogue"), th("sources"), th("problem set"), th("CMS id")], rows), "", "coverage.html")


# ---- landing and about ----
def landing_page(series_docs: dict, contests: dict) -> str:
    cs = list(contests.values())
    st = content_counts(cs)
    dark = sum(1 for c in cs if c.get("status") != "upcoming" and best_tier(c) == "none")
    n_caps = sum(len(R.get("captures") or []) for L in RES.locs.values() for R in L["resources"].values())
    tiles = [(len(BY_SEASON), "seasons", "season/index.html"), (len(series_docs), "series", "series/index.html"),
             (st["n"], "contests", "contest/index.html"), (len(SETS), "problem sets", "problemset/index.html"),
             (len(PROBLEMS), "problems", "problem/index.html"), (len(RES.locs), "sources", "source/index.html"),
             (len(JUDGES), "judges", "judge/index.html"), (len(LOC), "locations", "location/index.html")]
    seasons = [s for s in sorted(BY_SEASON, reverse=True) if any(contests[m].get("status") != "upcoming" for m in BY_SEASON[s])][:8]
    srows = []
    for s in seasons:
        wf = contests.get(f"wf-{s}")
        n_ran = sum(1 for m in BY_SEASON[s] if contests[m].get("status") != "upcoming")
        finals = ""
        if wf:
            where = place_cell(wf, "", 1)
            finals = " · finals " + link_contest(wf["id"], "", False) + (" in " + where if where else "")
        srows.append("<li>" + link_season(s, "") + f' <span class="muted">{n_ran} contests{finals}</span></li>')
    region_col = REGION_COL
    rrows = []
    for r in REGIONS:
        n = sum(1 for c in cs if SERIES_REGION.get(SERIES_OF[c["id"]]) == r and c.get("status") != "upcoming")
        rrows.append(f'<li><a href="contest/index.html#f:{region_col}={esc(r.replace(" ", "%20").replace("&", "%26"))}">{esc(r)}</a> <span class="muted">{num(n)} contests</span></li>')
    tiles_html = "".join(f'<div><b>{num(n)}</b><span><a href="{h}">{lab}</a></span></div>' for n, lab, h in tiles)
    srows_html, rrows_html = "".join(srows), "".join(rrows)
    nums_html = content_nums(st)
    body = f"""<h1>ICPC contest archive</h1>
<p class="lede">Every ICPC contest from which a team could advance toward a World Finals, back to 1977 — and where its website,
its results and its problems can still be found: at the original address, in the Wayback Machine, or in this project's own archive.</p>
<div class="nums">{tiles_html}</div>
<p class="note">Search everything with the box at the top right (press <code>/</code>): contest and series ids, names, problems, places, CMS ids, website hosts.</p>
<h2>What we hold</h2>
{nums_html}
<p class="note">Of the {num(st["n"])} contests that ran. {num(dark)} of them have no result of any kind yet, and {num(n_caps)} captures are stored in all.
<a href="coverage.html">Coverage</a> breaks this down by region, season and series; <a href="wanted.html">most wanted</a> is the list of what is missing.</p>
<h2>Start somewhere</h2>
<div class="cols">
<div><h3>Recent seasons</h3><ul class="plain">{srows_html}<li><a href="season/index.html">all {len(BY_SEASON)} seasons</a></li></ul></div>
<div><h3>Regions</h3><ul class="plain">{rrows_html}</ul></div>
<div><h3>Other views</h3><ul class="plain">
<li><a href="calendar/index.html">Calendar</a> <span class="muted">every contest in date order</span></li>
<li><a href="grid.html">The grid</a> <span class="muted">every contest on one screen</span></li>
<li><a href="series/wf.html">World Finals</a> <span class="muted">the series at the top</span></li>
<li><a href="coverage.html">Coverage</a> <span class="muted">how much we hold</span></li>
<li><a href="wanted.html">Most wanted</a> <span class="muted">what is missing</span></li>
<li><a href="cms.html">CMS id ledger</a> <span class="muted">every CMS contest id, accounted for</span></li>
<li><a href="non-mainline.html">Non-mainline registry</a> <span class="muted">real contests outside the hierarchy</span></li>
</ul></div>
</div>
<h2>Help fill the gaps</h2>
<p class="intro">Regional directors, judges and former contestants often still have the scoreboard, the problem set or the dates that the web has lost.
If you know where something lives, or see something wrong, <a href="about.html#contribute">tell us</a>.</p>"""
    return page("ICPC contest archive", body, "")


def about_page() -> str:
    n_sites = len(website_of)
    n_raw = len(ARCHIVED_BY_CONTEST)

    def dl(items):
        return '<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in items) + "</dl>"
    places_dl = dl((
    ('<span class="m h">live</span>', "<b>The address now.</b> Green: it still serves the document. Amber: it answers, but the content has drifted, it is an app that shows "
     "nothing without a browser, or the server turns our fetcher away (<i>blocked</i>). Grey: dead, or something else lives there now. Dead is normal for an old contest and no cause for alarm when there is a copy."),
    ('<span class="m h">WB</span>', "<b>The Wayback Machine.</b> Green: a snapshot shows the document; the source page opens that snapshot, not the calendar. "
     "Amber: a snapshot exists but holds something else (an error page, an empty shell). Grey: no snapshot, or the address is excluded there."),
    ('<span class="m h">ours</span>', "<b>Our archive.</b> Green: we hold a copy, captured from the address or from a Wayback snapshot. Amber: we fetched it, but what came back "
     "is not the document. Grey: missing — nothing captured yet."),
    ('<span class="m u">live</span>', "Dashed, in any of the three: nobody has looked yet."),
    (chip("lost", "x"), "Dead at its address, not in the Wayback Machine, and no copy here. Gone unless someone kept one."),
))
    objects_dl = dl((
    ('<a href="season/index.html">Season</a>', "From the first regional to the World Finals it feeds. Shown as <i>2024–2025</i>. Its page is the advancement tree."),
    ('<a href="series/index.html">Series</a>', "A line of editions under one name (<i>nwerc</i>). Renamings and splits are recorded as lineage."),
    ('<a href="contest/index.html">Contest</a>', "One edition (<i>nwerc-2020</i>). The year in the id is the season label, not the date: a fall regional postponed to January keeps its number."),
    ('<a href="problemset/index.html">Problem set</a>', "The problems a contest used; nearly always one set per contest, with the same id. Its page says what the ICPC Problem Archive holds."),
    ('<a href="problem/index.html">Problem</a>', "One problem: where it appeared, what is held, where it can be solved."),
    ('<a href="source/index.html">Source</a>', "An address as a contest means it — what it served for that contest — and where that can be found: at the address now, "
     "in the Wayback Machine, in our archive."),
    ('<a href="judge/index.html">Judge</a>', "An online judge where ICPC problems can be solved."),
    ('<a href="location/index.html">Location</a>', "Where contests were held: country, state or province, city, institution — one tree."),
))
    status_dl = dl((
    (chip("results: scoreboard, archived", "h"), "The best result we know and whether we hold a copy. The best result is one of, from most to least informative: "
     "<b>scoreboard</b> (every team, every problem), <b>frozen scoreboard</b> (as it stood when the board was frozen), <b>standings</b> (totals per team), "
     "<b>rankings</b> (order only), <b>ICPC standings only</b> (just the CMS's own data — formally the official result, in practice the least reliable). "
     "<b>archived</b> = we hold a copy; <b>link only</b> = we know the address but hold nothing."),
    (chip("results: none", "n"), "No result source of any kind is known. If we have other proof that the contest ran, it is under Evidence on its page."),
    (chip("website: archived", "h") + chip("website: link only", "l"), "The contest website's address is known; archived = we hold a crawl of it."),
    (chip("website: not known", "n") + chip("website: none", "n"), "<b>not known</b>: nobody has found an address yet. <b>none</b>: looked for, and the contest had no website of its own."),
    (chip("problems: 12 listed", "h"), "We know the problems by name. Green when the problem archive holds every statement, amber when it does not. "
     "<b>N of M listed</b> = only some are listed by name; <b>N, not listed</b> = only the number and the archive's holdings are recorded."),
    (chip("problems: source only", "l") + chip("problems: none", "n"), "<b>source only</b>: a published problem set or a judge page is known, nothing recorded yet. <b>none</b>: nothing known."),
    (chip("2 lost", "x"), "Sources that are dead at their address, have no Wayback snapshot, and were never captured here. Gone unless someone kept a copy."),
    (chip("1 only here", "h"), "Dead at its address and not in the Wayback Machine, but we hold a copy — as far as we know the only one."),
    (chip("upcoming", "n"), "The contest has not run yet. Nothing about its problems is published before it has."),
))
    marks_dl = dl((
    ('<span class="m h">S</span><span class="m h">F</span><span class="m h">St</span><span class="m h">R</span><span class="m h">I</span>',
     "Results: <b>S</b> scoreboard, <b>F</b> frozen scoreboard, <b>St</b> standings, <b>R</b> rankings, <b>I</b> ICPC standings. One mark per kind that exists."),
    ('<span class="m h">W</span>', "Website."),
    ('<span class="m h">filled</span> <span class="m l">outlined</span>', "Filled green: we hold an archived copy. Outlined amber: link only."),
    ('<span class="m h">St</span><span class="m l">D</span><span class="m n">So</span><span class="m u">P</span>',
     "Problems, what the ICPC Problem Archive holds: <b>St</b> statements, <b>D</b> test data, <b>So</b> solutions, <b>P</b> complete packages "
     "(on a single problem also <b>IV</b>/<b>OV</b>, input and output validators). Filled green: for every problem. Amber: for some. Grey: none. Dashed: not recorded. "
     "The number before the marks is how many problems the contest had."),
    ('<span class="m l">src</span>', "A published problem set or judge page is known, but nothing about the problems has been recorded yet."),
))
    body = f"""<h1>About</h1>
<p class="lede">What is here, how to read it, and how to help.</p>
<p class="tabs"><a href="#read">How to read this site</a> <a href="#status">Contest status</a> <a href="#marks">Marks</a>
<a href="#status-set">Problem sets</a> <a href="#sources">Sources</a> <a href="#contribute">Contribute</a> <a href="#local">Local archive</a> <a href="#data">Data</a></p>

<h2 id="read">How to read this site</h2>
<p class="intro">The catalogue is a set of objects, each with a list page and a page of its own:</p>
{objects_dl}
<p class="intro"><b>Every mention of an object links to its own page</b>, and looks the same wherever it appears. <b>A link stays on this site unless it is
marked <a class="ext" href="#read">like this</a></b>. In particular the address of a source is never linked directly from a contest or a table: the link goes to the
source's page, and that page is where you open the address as it is now, the Wayback Machine, or our archived copy. The exceptions are deliberate and marked:
a problem's online-judge links go straight to the problem on the judge, and a contest's CMS links go to the CMS.
A date links to its day in the <a href="calendar/index.html">calendar</a>, where you can see what else ran that day and that weekend.</p>
<p class="intro">A contest has <b>three kinds of content</b>, always in the same order: its <b>website</b>, its <b>results</b> and its <b>problems</b>. Each is either
<span class="chip h">held</span> (we have a copy), <span class="chip l">known but not held</span> (we have a link), <span class="chip n">none</span>, or
<span class="chip x">lost</span>. The colours are the scoreboard's.</p>
<p class="intro">A <b>location</b> is where the contest was held: its sites, as places in the location tree. The CMS also lists staff, guest and
bookkeeping groups as "sites"; those are not places and are never shown. When no real site is recorded, the city the contest's CMS record points at is shown,
marked <span class="chip n">inferred</span>. A source that covers only part of a contest says so beside its role, like
<span class="chip sc">Division 1</span>.</p>
<p class="intro">For spot checks, <a href="random.html">Random</a> in the header (or the key <b>r</b>) opens a page picked at random.</p>

<h2 id="status">Contest status</h2>
<p class="intro">The chips under a contest's title — one per kind of content, plus anything unusual.</p>
{status_dl}

<h2 id="marks">Marks</h2>
<p class="intro">The small letters in tables. A mark links to the source it stands for.</p>
{marks_dl}

<h2 id="status-set">Problem sets</h2>
<p class="intro">A problem set is nearly always the set of one contest and carries the same id; two sets were shared by two contests. The contest page says where the set
was published and where it can be solved; the set's page says what the ICPC Problem Archive (a private collection of problem packages) holds. A set is
<b>listed</b> when we know its problems by name — completely, partly, or not at all, in which case only the count and the holdings are recorded. What is held for a
single problem is recorded for few sets; elsewhere a problem's marks follow from its set: held if the set holds that kind for every problem, not held if for none,
dashed if for some. A <b>UUID</b> is the identity of a problem's package; a problem reused in another contest keeps it.</p>

<h2 id="sources">Sources</h2>
<p class="intro">A <b>source</b> is one document a contest points at: an address, and what that address served for the contest (its website, scoreboard, frozen
scoreboard, standings, rankings, ICPC standings, problem set, judge page or teams). It is the document that matters, not the address: addresses die and get reused, so a
source that is no longer at its address names the time it is meant at (<i>as it was on 2007-11-05</i>).</p>
<p class="intro">The same document can be found in up to <b>three places</b>, and every list of sources shows all three as one unit, always in this order:</p>
{places_dl}
<p class="intro">Any combination occurs: a scoreboard can be live, in the Wayback Machine and in our archive all at once, or only in one of them. A source's own page is
the only place where the three are opened: the address, the snapshot that shows the document, and our copy. Links <a class="local" href="#local">marked local</a> need the
local archive server (below). When several contests cite one address — a results page reused every year — its page has a row per contest, since each means a different time.</p>

<h2 id="contribute">Contribute</h2>
<p class="intro">If you ran, judged or took part in a contest, you may be the only person who still has its scoreboard, its problem set or its dates.
To add a source, confirm that what we show is right, or correct something, <a class="ext" href="{REPO}/issues/new">open an issue</a> and say which contest
(its id, such as <code>nwerc-2020</code>) and what you know — a link, a file, a date, a place. Every claim is checked and recorded with where it came from.
The <a href="wanted.html">most wanted</a> list shows what is missing.</p>

<h2 id="local">Local archive</h2>
<p class="intro">Besides the result pages on the public replay site, this project holds a much larger private archive: raw captures of every result page and full
crawls of <b>{n_sites}</b> contest websites ({n_raw} contests with raw captures in all). That is too big for GitHub Pages, so it is not published yet.
Links <a class="local" href="{LOCAL_BASE}/" title="{LOCAL_TITLE}">marked like this</a> point at a small server on <b>your own machine</b>
(<code>{LOCAL_BASE or "this host"}</code>). They work only with the <code>archive</code> repository checked out next to <code>contests</code> and the server running;
for everyone else they fail to connect.</p>
<pre><code># in your checkout of the contests repo (archive checked out alongside it)
python3 tools/index_websites.py     # after new site crawls
python3 tools/serve.py              # rebuilds the site with local links, serves on 127.0.0.1:8123</code></pre>
<p class="intro">Then browse <code>http://127.0.0.1:8123/</code> — the same pages as the public site, with every local link live. <b>Archived website</b> plays a crawled
site back page by page; pages that were not captured go to the Wayback Machine or the live site. <b>Raw</b> is a captured file exactly as fetched.</p>

<h2 id="data">Data</h2>
<p class="intro">Everything here is built from plain files in <a class="ext" href="{REPO}">icpc-contest-archive/contests</a>: one YAML file per series and per problem set,
<code>locations.yaml</code> and <code>judges.yaml</code>. The definitions are in
<a class="ext" href="{REPO}/blob/main/DEFINITIONS.md">DEFINITIONS.md</a>; the whole catalogue as one file is <a href="catalogue.json">catalogue.json</a>.
Typeface: IBM Plex Sans (SIL Open Font License).</p>"""
    return page("About", body, "", "about.html")



# ---- build ----
def build(out: Path):
    t0 = time.time()
    series_docs, contests, series_of, prev, children, subsets, aux = load()
    SERIES_DOCS.clear(); SERIES_DOCS.update(series_docs)  # noqa: E702
    derive_regions(series_docs)
    load_problem_sets()
    NM[:] = load_non_mainline()
    CHILDREN.clear(); CHILDREN.update(children)  # noqa: E702
    PREV.clear(); PREV.update(prev)  # noqa: E702
    SUBSETS.clear(); SUBSETS.update(subsets)  # noqa: E702
    load_locations_tree(contests)
    index_sources(contests)
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("contest", "series", "season", "calendar", "problemset", "problem", "problems", "judge", "location", "source", "source/by-role", "assets"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    shutil.copytree(ASSETS, out / "assets", dirs_exist_ok=True)

    REPLAY_LOOKUP.clear()
    REPLAY_PROBLEMSET.clear()
    REPLAY_BY_CONTEST.clear()
    if aux["replay-index"]:
        for e in aux["replay-index"]["pages"]:
            if e.get("url"):
                k = (e["contest"], norm_key(e["url"]))
                REPLAY_LOOKUP[k] = e["path"]
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
    index_extra_copies(contests)
    EMPTY_STANDINGS.clear()
    p = ROOT / "data" / "icpc-standings-empty.json"
    if p.exists():
        EMPTY_STANDINGS.update({lid(v["url"]): v.get("asked") or "" for v in json.loads(p.read_text())["contests"].values()})
    BY_SEASON.clear()
    for cid, c in contests.items():
        if c.get("season"):
            BY_SEASON[c["season"]].append(cid)

    # ---- contests, series, seasons ----
    for cid, c in contests.items():
        (out / "contest" / f"{cid}.html").write_text(contest_page(cid, c, "../"))
    (out / "contest" / "index.html").write_text(contest_index(contests, "../"))
    for sid, doc in series_docs.items():
        (out / "series" / f"{sid}.html").write_text(series_page(sid, doc, "../"))
    (out / "series" / "index.html").write_text(series_index(series_docs, "../"))
    for season, members in BY_SEASON.items():
        (out / "season" / f"{season}.html").write_text(season_page(season, members, "../"))
    (out / "season" / "index.html").write_text(season_index("../"))
    stub(out / "seasons.html", "season/index.html")
    index_calendar(contests)
    for year in CAL:
        (out / "calendar" / f"{year}.html").write_text(calendar_page(year, "../"))
    (out / "calendar" / "index.html").write_text(calendar_index("../"))

    # ---- problem sets, problems, judges ----
    (out / "problemset" / "index.html").write_text(problemset_index("../"))
    for sid, doc in SETS.items():
        (out / "problemset" / f"{sid}.html").write_text(problemset_page(sid, doc, "../"))
    (out / "problem" / "index.html").write_text(problem_index("../"))
    for pid, ent in PROBLEMS.items():
        (out / "problem" / f"{pid}.html").write_text(problem_page(pid, ent, "../"))
    n_alias = 0
    for sid, doc in SETS.items():   # ids of sets merged into another, and of problems merged into another, keep working
        for old in doc.get("aliases") or []:
            if old not in SETS:
                stub(out / "problemset" / f"{old}.html", f"{sid}.html")
                n_alias += 1
        for pr in doc.get("problems") or []:
            for old in pr.get("aliases") or []:
                if old not in PROBLEMS:
                    stub(out / "problem" / f"{old}.html", f"{pr['id']}.html")
                    n_alias += 1
    probs, pages = judge_usage(contests)
    for jid, j in JUDGES.items():
        (out / "judge" / f"{jid}.html").write_text(judge_page(jid, j, probs.get(jid, set()), pages.get(jid, []), "../"))
    (out / "judge" / "index.html").write_text(judge_index(probs, pages, "../"))
    stub(out / "problemsets" / "index.html", "../problemset/index.html")
    stub(out / "judges" / "index.html", "../judge/index.html")
    stub(out / "problems" / "index.html", "../problemset/index.html")   # the old "holdings by contest" view
    stub(out / "problems" / "list.html", "../problem/index.html")
    (out / "problems" / "problems.json").write_text(json.dumps(
        {"generated": datetime.date.today().isoformat(), "sets": SETS, "judges": JUDGES}, ensure_ascii=False))
    print(f"  problem sets: {len(SETS)} set pages, {len(PROBLEMS)} problem pages, {n_alias} redirects from merged ids, {len(JUDGES)} judges")

    # ---- locations ----
    for nid in LOC:
        (out / "location" / f"{nid}.html").write_text(location_page(nid, "../"))
    (out / "location" / "index.html").write_text(location_index("../"))
    print(f"  locations: {len(LOC)} pages")

    # ---- views and appendices ----
    (out / "coverage.html").write_text(coverage_page(series_docs, contests))
    (out / "wanted.html").write_text(wanted_page(series_docs))
    (out / "grid.html").write_text(grid_page(series_docs, contests))
    (out / "cms.html").write_text(cms_page(contests))
    (out / "non-mainline.html").write_text(non_mainline_page())
    (out / "index.html").write_text(landing_page(series_docs, contests))
    (out / "about.html").write_text(about_page())
    (out / "random.html").write_text(random_page())
    (out / "random.json").write_text(json.dumps({
        "contest": sorted(contests), "series": sorted(series_docs), "season": [str(x) for x in sorted(BY_SEASON)],
        "problemset": sorted(SETS), "problem": sorted(PROBLEMS), "source": sorted(RES.locs),
        "location": sorted(LOC), "judge": sorted(JUDGES)}, separators=(",", ":")))
    stub(out / "local.html", "about.html#local")

    # ---- machine-readable dump ----
    dump = {}
    for sid, doc in series_docs.items():
        d2 = dict(doc)
        d2["series"] = {**doc["series"], "region": SERIES_REGION.get(sid, "Other")}
        dump[sid] = d2
    (out / "catalogue.json").write_text(json.dumps(
        {"generated": datetime.date.today().isoformat(), "series": dump}, ensure_ascii=False))

    # ---- search index ----
    def hosts_of(c):
        """Hosts of the website and result sources (what people search by)."""
        hs = set()
        for s in sources(c):
            if "web" in s["roles"] or any(r in s["roles"] for r in RESULT_KINDS):
                hs.add(re.sub(r"^https?://(www\.)?", "", s["url"]).split("/")[0])
        return sorted(hs)

    def clean(d):
        return {k: v for k, v in d.items() if v not in (None, "", [])}
    search = [clean({"t": "e", "id": str(s), "name": f"Season {s - 1}–{s}", "extra": f"{len(BY_SEASON[s])} contests"}) for s in sorted(BY_SEASON)]
    search += [clean({"t": "r", "id": sid, "name": doc["series"].get("name"), "aliases": doc["series"].get("aliases"),
                      "extra": f"{SERIES_REGION.get(sid, '')} · {len(doc['contests'])} editions"}) for sid, doc in series_docs.items()]
    search += [clean({"t": "c", "id": cid, "name": c.get("name"), "date": c.get("date"),
                      "cms": [str(i) for i in (c.get("cms_ids") or [])], "hosts": hosts_of(c)}) for cid, c in sorted(contests.items())]
    search += [clean({"t": "l", "id": nid, "name": n["name"], "aliases": n.get("aliases"),
                      "extra": f'{n["type"]} · {", ".join(x["name"] for x in location_chain(LOC, nid)[1:])} · {len(LOC_SUB.get(nid, ()))} contests'}) for nid, n in LOC.items()]
    search += [clean({"t": "j", "id": jid, "name": j.get("name"), "extra": j.get("status")}) for jid, j in JUDGES.items()]
    search += [clean({"t": "s", "id": sid, "name": doc.get("name"), "aliases": doc.get("aliases"),
                      "extra": "problem set of " + ", ".join(set_members(doc))}) for sid, doc in SETS.items()]
    search += [clean({"t": "p", "id": pid, "name": ent["rows"][0][1]["name"], "aliases": [r.get("uuid") for _s, r in ent["rows"] if r.get("uuid")],
                      "extra": ", ".join(dict.fromkeys(cid for _s, cid, _L in ent["apps"]))}) for pid, ent in PROBLEMS.items()]
    (out / "search.json").write_text(json.dumps(search, ensure_ascii=False, separators=(",", ":")))

    # ---- source pages + redirect stubs from the old locator/ addresses ----
    if RES.locs:
        missing = sorted({s["url"] for c in contests.values() for s in sources(c) if lid(s["url"]) not in RES.locs})
        if missing:
            print(f"  note: {len(missing)} catalogue sources have no source page yet — run tools/build_resources.py (e.g. {missing[0]})")
        for k, L in RES.locs.items():
            d = out / "source" / k
            d.mkdir(exist_ok=True)
            (d / "index.html").write_text(source_page(k, L, "../../"))
            od = out / "locator" / k
            od.mkdir(parents=True, exist_ok=True)
            stub(od / "index.html", f"../../source/{k}/index.html")
            for ts in L["resources"]:
                stub(od / f"{ts}.html", f"../../source/{k}/index.html#s-{ts}")
        (out / "source" / "index.html").write_text(source_list("../"))
        for r in ROLE_PAGES:
            (out / "source" / "by-role" / f"{r}.html").write_text(source_list("../../", r))
        for k in ROLE_PAGES + ["index"]:
            tgt = f"../source/by-role/{k}.html" if k != "index" else "../source/index.html"
            stub(out / "resources" / f"{k}.html", tgt)
            stub(out / "urls" / f"{k}.html", tgt)
        print(f"  {len(RES.locs)} source pages")

    n = len(list(out.rglob("*.html")))
    n_stubs = sum(1 for p in out.rglob("*.html") if p.parts[len(out.parts)] in ("locator", "resources", "urls", "problemsets", "judges", "problems") or p.name in ("seasons.html", "local.html")) + n_alias
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
