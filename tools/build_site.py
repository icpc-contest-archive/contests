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
  6. Coverage is one record per contest (tools/coverage.py, DEFINITIONS.md Coverage), and every
     page reads it. Its questions are one list (coverage.FACETS); every view is drawn from it with
     one colour per kind of answer (facet_q): the stacked bars of the coverage panel (the archive,
     a season, a series, a location), a contest's coverage card, the matrices (a series by edition,
     a season by contest), the strips through the seasons, the grid. Anything that counts contests
     — a bar segment, a label, a number — is a link carrying its count (data-n) into the contest
     list, filtered by name (#f:region=Europe&website=missing) to exactly those contests;
     tools/check_coverage_links.py follows every such link and checks the count.

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
import hashlib
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
import review_units as R  # noqa: E402  (review mode: the units a reader can confirm, correct or add to)
from resources import fmt_time, label as res_label, norm_key, unwrap, wayback_link  # noqa: E402
from urllib.parse import quote  # noqa: E402
from catalogue import (CMS_STANDINGS, RANK, RESULT_LADDER, archived, find_source, by_role, has_role, judge_sources,  # noqa: E402
                       load_judges, load_locations, load_non_mainline, load_sets, location_chain, primary_role,
                       set_divisions, set_id_of, set_letters, set_of, sources)
import coverage as CV  # noqa: E402  (the one coverage record per contest; every page reads it)
from coverage import set_counts, set_list_state  # noqa: E402
import site_resources  # noqa: E402
import source_descriptions  # noqa: E402

# the result roles: the ladder (scoreboard > standings > rankings > team list), then the frozen
# scoreboard, which is kept beside the ladder (a standings page of the ICPC CMS is filed by what it
# holds, like any other source)
RESULT_KINDS = RESULT_LADDER + ("frozen_scoreboard",)

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
       ("judge/index.html", "Online judges"), ("location/index.html", "Locations"))
NAV2 = (("coverage.html", "Coverage"), ("about.html", "About"))


def esc(s) -> str:
    return html.escape(str(s), quote=True)


RANDOM_KINDS = (("contest", "contest"), ("series", "series"), ("season", "season"), ("problemset", "problem set"),
                ("problem", "problem"), ("source", "source"), ("location", "location"), ("judge", "online judge"))


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


RANDOM_OF_NAV = {f"{k}/index.html": (k, label) for k, label in RANDOM_KINDS}


def random_link(body: str, rel: str, nav: str | None) -> str:
    """Put a "Random <kind>" link beside the title of every list and object page of one kind."""
    if nav not in RANDOM_OF_NAV or "<h1" not in body:
        return body
    k, label = RANDOM_OF_NAV[nav]
    a = (f'<a class="rnd-kind" href="{rel}random.html#{k}" title="Open a random {label} page '
         f'(the header Random and the key r then stay on {label} pages)">Random {label}</a>')
    i = body.index("<h1")
    return body[:i] + a + body[i:]


def page(title: str, body: str, rel: str, nav: str | None = None) -> str:
    """One page. `nav` is the NAV href of the object list this page belongs to (highlighted)."""
    body = random_link(body, rel, nav)
    links = "".join(f'<a href="{rel}{h}"' + (' class="on"' if h == nav else "") + f">{t}</a>" for h, t in NAV)
    links += '<span class="sep"></span>' + "".join(
        f'<a href="{rel}{h}"' + (' class="on"' if h == nav else "") + f">{t}</a>" for h, t in NAV2)
    links += f'<a id="rnd" href="{rel}random.html" title="Open a random page — press r">Random</a>'
    links += R.header_link(rel)
    return f"""<!doctype html><html lang="en" data-rel="{rel}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — ICPC contest archive</title><link rel="icon" href="{rel}assets/favicon.svg">
<link rel="stylesheet" href="{rel}assets/site.css"></head><body>
<header class="site"><a class="brand" href="{rel}index.html"><span class="logo"><i></i><i></i><i></i></span>ICPC contest archive</a>
<nav>{links}</nav>
<div class="search"><input id="q" type="search" placeholder="Search — press /" autocomplete="off" aria-label="Search the archive"><div id="hits" class="hits"></div></div></header>
<main>{body}
<footer class="site">Something missing or wrong? <a href="{rel}about.html#contribute">Tell us</a> ·
<a href="{rel}about.html#read">How to read this site</a> · <a href="{rel}random.html">Random page</a></footer></main>
<script src="{rel}assets/site.js" defer></script></body></html>"""


def stub(path: Path, target: str) -> None:
    """A tiny meta-refresh page at an old address so existing links keep working."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={esc(target)}">'
                    f'<title>moved</title><p>Moved to <a href="{esc(target)}">{esc(target)}</a>.</p>')


def crumbs(*items: str) -> str:
    """Breadcrumb line above an object page's title: already-rendered links, outermost first."""
    return '<p class="crumbs">' + " › ".join(items) + " ›</p>"


def th(label: str, num: bool = False, f: bool | str = False, title: str | None = None,
       k: str | None = None, g: bool = False, o: tuple | None = None, hid: bool = False) -> str:
    """A header cell. `f` adds a drop-down filter on the column (a string names it in the filter bar);
    `k` is the filter's name in a link (#f:k=value), `g` puts it on the bar's Coverage line, `o` is
    the order of its values, `hid` hides the column (it is there for its filter only)."""
    cls = " ".join(x for x in ("num" if num else "", "hid" if hid else "") if x)
    a = (f' class="{cls}"' if cls else "") + (f' data-f="{esc(f)}"' if isinstance(f, str) else (" data-f" if f else ""))
    a += (f' data-k="{esc(k)}"' if k else "") + (' data-g="c"' if g else "") + (f' data-o="{esc("|".join(o))}"' if o else "")
    return f"<th{a}" + (f' title="{esc(title)}"' if title else "") + f">{label}</th>"


def flt_href(rel: str, f: dict) -> str:
    """The contest list, filtered: flt_href(rel, {"season": 2024, "website": "missing"})."""
    return f"{rel}contest/index.html#f:" + "&".join(f"{k}={quote(str(v), safe='')}" for k, v in f.items() if v not in (None, ""))


RAN = {"status": "ran"}   # every coverage number counts contests that ran; so does every link behind one


def n_link(n, rel: str, f: dict | None, text: str | None = None, title: str | None = None) -> str:
    """A count that opens the contests it counts (`f`: the filters; None or a zero count = no link)."""
    s = text if text is not None else num(n)
    if not n or f is None:
        return s
    return f'<a class="nl" data-n="{n}" href="{esc(flt_href(rel, {**RAN, **f}))}"' + (f' title="{esc(title)}"' if title else "") + f">{s}</a>"


def table(heads: list[str], rows: list[str], cls: str = "", tid: str | None = None) -> str:
    return (f'<div class="tw"><table' + (f' class="{cls}"' if cls else "") + (f' id="{tid}"' if tid else "")
            + "><thead><tr>" + "".join(heads) + "</tr></thead><tbody>" + "\n".join(rows) + "</tbody></table></div>")


def chip(text: str, cls: str = "", title: str | None = None) -> str:
    return f'<span class="chip{" " + cls if cls else ""}"' + (f' title="{esc(title)}"' if title else "") + f">{esc(text)}</span>"


def help_link(anchor: str, rel: str, what: str = "what these mean") -> str:
    return f'<a class="help" href="{rel}about.html#{anchor}" title="{esc(what)}" aria-label="{esc(what)}">?</a>'


def pct(part: int, total: int) -> int:
    return round(100 * part / total) if total else 0


def pct_cell(part: int, total: int, rel: str = "", f: dict | None = None) -> str:
    """A percentage with a bar; sorts numerically. With `f` it opens the contests it counts."""
    if not total:
        return '<td class="num muted" data-v="">–</td>'
    p = pct(part, total)
    return (f'<td class="num" data-v="{p}" title="{num(part)} of {num(total)}">' + n_link(part, rel, f, f"{p}%")
            + f'<span class="bar"><i style="width:{p}%"></i></span></td>')


def num(n) -> str:
    return f"{n:,}"


def result_sources(c) -> list[dict]:
    """Sources serving any result role, each once however many it serves."""
    return [s for s in sources(c) if any(r in s["roles"] for r in RESULT_KINDS)]


# ---- coverage: one record per contest (tools/coverage.py) ----
COV: CV.Coverage | None = None
_HELD: dict = {}


def src_held(c: dict, s: dict) -> bool:
    """We hold a copy of this source that is the document: the same answer as the `ours` mark
    wherever the source is listed (avail)."""
    k = (c["id"], s["url"])
    if k not in _HELD:
        _HELD[k] = avail(s["url"], c["id"], s)["ours"]["s"] == "yes"
    return _HELD[k]


def copy_held(url: str) -> bool:
    """We hold a good copy of this address, whether or not a contest cites it (a problem's page or
    statement file on an online judge)."""
    L = RES.locs.get(lid(url))
    return bool(L) and any(c.get("sha256") and not c.get("caveat") for R in (L.get("resources") or {}).values() for c in R.get("captures") or [])


def rec(c: dict) -> dict:
    """The coverage record of a contest (coverage.Coverage.record)."""
    return COV.record(c)


def did_run(c: dict) -> bool:
    return c.get("status") != "upcoming"


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


def web_state(c) -> str:
    """'link' (a web source), 'none' (confirmed none: web under `none:`), 'unknown' (not researched)."""
    if has_role(c, "web"):
        return "link"
    return "none" if "web" in (c.get("none") or []) else "unknown"


# the marks of a results cell: the ladder, best first, then the frozen scoreboard beside it
TIERS = (("scoreboard", "S"), ("standings", "St"), ("rankings", "R"), ("teams", "T"), ("frozen_scoreboard", "F"))
TIER_LABEL = CV.LEVEL_LABEL
ROLE_LABEL = {"frozen_scoreboard": "frozen scoreboard", "teams": "team list",
              "problemset": "problem set", "web": "website"}
HELD_KINDS = (("statement", "St", "statements"), ("data", "D", "test data"),
              ("solutions", "So", "solutions"), ("package", "P", "complete packages"))
# what a problem set or problem source holds (`contains:`), in the words of a page
CONTAINS = (("names", "problem names"), ("statement", "statements"), ("data", "test data"), ("solutions", "solutions"), ("package", "complete packages"))


def key_line(rel: str, *parts: str) -> str:
    """The key above a table. Parts: 'results', 'website', 'held', 'have', 'available'."""
    bits = []
    if "results" in parts:
        bits.append('<span class="m q4">S</span> scoreboard <span class="m q3">St</span> standings <span class="m q2">R</span> rankings '
                    '<span class="m q1">T</span> team list · <b>F</b> frozen scoreboard')
    if "website" in parts:
        bits.append("<b>W</b> website")
    if "results" in parts or "website" in parts:
        bits.append('<span class="m h">filled</span> we hold a copy <span class="m k">outlined</span> link only')
    if "held" in parts:
        bits.append('problems: <b>St</b> statements · <b>D</b> test data · <b>So</b> solutions · <b>P</b> packages · <b>E</b> editorial — '
                    '<span class="m h">all</span> <span class="m l">some</span> held, in the problem archive or in a source we hold a copy of · '
                    '<span class="m k">link only</span> <span class="m n">none</span> <span class="m u">not recorded</span>')
    if "have" in parts:
        bits.append('<b>St</b> statement · <b>D</b> test data · <b>IV</b>/<b>OV</b> input/output validator · <b>So</b> solutions · <b>P</b> package — '
                    '<span class="m h">held</span> <span class="m n">not held</span> <span class="m u">not recorded</span>')
    if "available" in parts:
        bits.append('where a source is found — at its <b>address</b> now · in the <b>Wayback</b> Machine · in our <b>archive</b>: '
                    '<span class="m h">there</span> <span class="m l">there, in doubt</span> <span class="m x">confirmed not there</span> '
                    '<span class="m p">not done yet</span> <span class="m g">does not apply</span>')
    return '<p class="key">' + " &nbsp;·&nbsp; ".join(bits) + " " + help_link("sources" if parts == ("available",) else "marks", rel) + "</p>"


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




def src_href(url: str, rel: str, ts: str | None = None, cid: str | None = None) -> str | None:
    """The page of a source (source/<id>/index.html): the one `cid` means by the address when the
    address has several (one per time it is meant at); None when the address is unknown."""
    d = doc_for(url, cid)
    return f"{rel}source/{d['id']}/index.html" if d else None


def host_label(url: str, n: int = 30) -> str:
    h = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
    return h if len(h) <= n else h[:n - 1] + "…"


def link_source(url: str, rel: str, label: str | None = None, ts=None, cid: str | None = None) -> str:
    """A source: its label linking to the SOURCE PAGE (the one `cid` means, when the address has several).
    The address itself is linked from the source page only. A source the resource graph does
    not know yet (data/resources.json older than the catalogue) falls back to the address ↗."""
    lab = esc(label if label is not None else host_label(url))
    href = src_href(url, rel, ts, cid)
    if href:
        return f'<a href="{href}" title="{esc(res_label(url, ts, 200))}">{lab}</a>'
    return f'<a class="ext" href="{esc(url)}" title="{esc(url)} — no source page yet (rebuild data/resources.json)">{lab}</a>'


def role_label(r: str) -> str:
    return ROLE_LABEL.get(r, r.replace("_", " "))


def role_chip(r: str) -> str:
    return f'<span class="chip">{esc(role_label(r))}</span>'


def lost_locators(c) -> list:
    """Result/web sources of this contest that are gone from their address (dead or replaced) AND not in
    the Wayback Machine, by the same answers as their address · Wayback · archive marks (avail): held
    = ours is the only copy; archive `lost` = the material is lost. A bad copy is neither (its archive
    mark says so); an address that only refuses our fetcher (403, an untrusted certificate) is not gone."""
    out = []
    for s in sources(c):
        if not ("web" in s["roles"] or any(r in s["roles"] for r in RESULT_KINDS)):
            continue
        a = avail(s["url"], c["id"], s)
        if a["lost"] or (a["live"]["s"] == "no" and a["wb"]["s"] == "no" and a["ours"]["s"] == "yes"):
            out.append((s["url"], a["wb"]["word"], a["ours"]["s"] == "yes"))
    return out


def local_link(path: str, label: str = "local") -> str:
    return f'<a class="local" href="{LOCAL_BASE}/{esc(path)}" title="{LOCAL_TITLE}">{label}</a>'


def cap_of(e: dict) -> dict | None:
    return capture_info.get(held_path(e) or "")


# a held result's mark has the colour of its level on the ladder, the same as in every bar and square
MARK_Q = {"scoreboard": "q4", "standings": "q3", "rankings": "q2", "teams": "q1", "frozen_scoreboard": "q4"}


def result_marks(c: dict, rel: str) -> str:
    """One mark per result tier present: filled = an archived copy is held, outlined = link
    only. Each mark links to the source page of the address that serves the tier."""
    out = []
    for key, letter in TIERS:
        entries = by_role(c, key)
        if not entries:
            continue
        e = next((x for x in entries if src_held(c, x)), None)
        held = e is not None
        e = e or entries[0]
        tip = role_label(key) + (" — we hold a copy" if held else " — link only, no copy held")
        parts = list(dict.fromkeys(x["scope"] for x in entries if x.get("scope")))
        if parts:
            tip += " (" + ", ".join(parts) + ")"
        href = src_href(e["url"], rel, e.get("as_of"), c["id"])
        cls = MARK_Q[key] if held else "k"
        out.append(f'<a class="m {cls}" href="{href}" title="{tip}">{letter}</a>' if href
                   else f'<span class="m {cls}" title="{tip}">{letter}</span>')
    return "".join(out)


ERAS = (("to 1998", 0, 1998), ("1999–2007", 1999, 2007), ("2008–2015", 2008, 2015), ("2016 on", 2016, 9999))
# the name of each component's filter in a link (#f:statements=missing)
COMP_KEY = {"statement": "statements", "data": "data", "solutions": "solutions", "package": "packages", "editorial": "editorial"}


def season_of(c: dict) -> int:
    """The season (end year) of a contest; the id year stands in where none is recorded."""
    return c.get("season") or int(c["id"].rsplit("-", 1)[1])


def toks(*tokens: str) -> str:
    """Filter values of one cell (data-vs)."""
    return "|".join(t for t in tokens if t)


RESULT_ORDER = tuple(TIER_LABEL[k] for k in CV.LEVELS) + ("any result", "no scoreboard", "upcoming")
STATE_ORDER = CV.STATES + ("missing",)


def results_value(c: dict) -> str:
    """The filter values of a results cell: the level we hold (the ladder), and `any result`."""
    if not did_run(c):
        return "upcoming"
    lv = rec(c)["results"]
    return toks(TIER_LABEL[lv], "any result" if lv != "none" else "", "no scoreboard" if lv != "scoreboard" else "")


def fetch_value(c: dict) -> str:
    """A better result than the one we hold is known at an address we have no copy of: its level."""
    f = rec(c)["fetch"] if did_run(c) else ""
    return toks(TIER_LABEL[f], "any") if f else ""


def also_value(c: dict) -> str:
    """What is said about a contest's results beside their level."""
    if not did_run(c):
        return ""
    r = rec(c)
    return toks(f"frozen scoreboard: {r['frozen']}" if r["frozen"] else "", "partial result" if r["partial"] else "",
                "lost source" if any(not held for _u, _w, held in lost_locators(c)) else "")


def component_value(c: dict, key: str) -> str:
    """One kind of problem material: its state, and `missing` for anything short of all."""
    if not did_run(c):
        return ""
    st = rec(c)["problems"][key]
    return toks(st, "missing" if st != "all" else "")


def pmeta_value(c: dict) -> str:
    if not did_run(c):
        return ""
    pm = rec(c)["pmeta"]
    return toks(*(f"{lab}: {pm[k]}" for k, lab in CV.PMETA), *(f"{lab}: missing" for k, lab in CV.PMETA if pm[k] != "all"))


def meta_value(c: dict) -> str:
    return toks(*(f"{lab}: {rec(c)['meta'][k]}" for k, lab in CV.META)) if did_run(c) else ""


def era_of(c: dict) -> str:
    s = season_of(c)
    return next((lab for lab, lo, hi in ERAS if lo <= s <= hi), "")


def website_cell(c: dict, rel: str, n: int = 24) -> str:
    """`W` (filled = archived, outlined = link only) and the host, linking to the source page."""
    ws = web_state(c)
    if ws == "none":
        return '<span class="muted" title="looked: this contest had no website of its own">none</span>'
    webs = by_role(c, "web")
    if not webs:
        return ""
    held = rec(c)["website"] == "have"
    s = webs[0]
    more = f' <span class="small muted" title="{len(webs)} website addresses">+{len(webs) - 1}</span>' if len(webs) > 1 else ""
    return (f'<span class="m {"h" if held else "k"}" title="website — {"we hold a copy" if held else "link only, no copy held"}">W</span>'
            + link_source(s["url"], rel, host_label(s["url"], n), s.get("as_of"), c["id"]) + more)


WEB_VALUES = {"have": "have", "no copy": "missing|missing: no copy", "no address": "missing|missing: no address", "confirmed none": "confirmed none"}
WEB_ORDER = ("have", "missing", "missing: no copy", "missing: no address", "confirmed none")


def website_value(c: dict) -> str:
    """Have (we hold a copy) or missing, and why it is missing."""
    return WEB_VALUES[rec(c)["website"]]


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
# One vocabulary for the three places, used by every mark, chip, pill, key and filter (ruling of 2026-11-16):
#   place     green (it is there)   amber (there, in doubt)                  red (confirmed not there)   blue (not done yet)   grey (does not apply)
#   address   live                  changed · blocked · unverified · empty   dead · replaced             not checked
#   Wayback   snapshot              bad snapshot                             no snapshot · excluded      not checked           n/a
#   archive   held                  bad copy                                 lost                        not captured          n/a
# The label of a mark is the place and never changes; its colour is the answer.
AV_CLS = {"yes": "h", "part": "l", "no": "x", "pending": "p", "na": "g"}       # .m and .chip classes
AV_Q = {"yes": "q4", "part": "q2", "no": "qr", "pending": "ql", "na": "qx"}    # pill classes: the colours of every coverage bar
AV_PLACES = (("live", "address", "the address now"), ("wb", "Wayback", "the Wayback Machine"), ("ours", "archive", "our archive"))


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
    # anything else (the content check's reading, an audit line) stays in the data: say what it found, not how
    if "another edition" in ev:
        return pre + "of another edition of the contest" if pre else "another edition of the contest"
    return pre + "another document" if pre else "another document"
LIVE_WORD = {"live": "live", "changed": "changed", "blocked": "blocked", "unknown": "unverified", "replaced": "replaced", "dead": "dead"}
LIVE_S = {"live": "yes", "changed": "part", "blocked": "part", "unknown": "part", "replaced": "no", "dead": "no"}
BLOCKED = re.compile(r"HTTP (401|403|412|4[5-9]\d)|CERTIFICATE_VERIFY_FAILED")   # the server answered; our fetcher was turned away
PLACE_TIP = {   # the sentence behind each word, the same wherever the word is shown
    "live": "the address still serves the document",
    "changed": "the address answers, but what it serves differs from the document; it needs a look",
    "blocked": "the server answers but turns our fetcher away; it may still open in a browser",
    "unverified": "the address answers, but there was nothing to compare the page against",
    "empty": "the page answers, but there is nothing on it",
    "replaced": "something else is at the address now",
    "dead": "the address no longer answers",
    "snapshot": "a Wayback snapshot shows the document",
    "bad snapshot": "a snapshot exists, but what it holds is not the document",
    "no snapshot": "the Wayback Machine has no snapshot of this address",
    "excluded": "the Wayback Machine refuses to serve this address",
    "held": "we hold a copy",
    "bad copy": "we fetched it, but what came back is not the document",
    "lost": "gone from its address, not in the Wayback Machine, and we hold no copy",
    "not captured": "we hold no copy yet",
    "not checked": "nobody has looked yet",
    "n/a": "does not apply",
}
EXTRA_HELD: dict = defaultdict(list)   # source id -> copies the resource graph files under another address
EMPTY_STANDINGS: dict = {}   # source id -> date asked: ICPC standings pages the open API has no rows for (data/icpc-standings-empty.json)
_CIT: dict = {}
_COPIES: dict = {}


def index_extra_copies(contests: dict) -> None:
    """Copies the catalogue ties to a source but the resource graph files under another address:
    a capture named in `archived` whose own address differs (a redirect target, a mirror), the
    contest's website crawl when it was seeded from another spelling of the address, and a crawl
    that holds the address as one of its pages."""
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
    # an address the catalogue cites that is a page of a crawl we hold, not the crawl's first address:
    # that page is our copy of it
    cited = {lid(e["url"]) for c in contests.values() for e in sources(c)}
    for L in RES.locs.values():
        for R in (L.get("resources") or {}).values():
            w = R.get("website")
            for ru, status, size, wts, _ctype in (w or {}).get("page_list") or []:
                k2 = lid(ru)
                if status != 200 or not size or k2 == L["id"] or k2 not in cited:
                    continue
                if any((x.get("site") or {}).get("dir") == w["dir"] for x in EXTRA_HELD[k2]):
                    continue
                EXTRA_HELD[k2].append({"ts": wts or R["ts"], "via": "wayback" if w.get("mode") == "wayback" else "live",
                                       "contest": w["contest"], "kind": "website", "filed_under": L["url"], "site": w})


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


# ---- sources: an address at a time (ruling of 2026-11-13; one page each since 2026-11-16) ----
DOCS: dict = {}      # source id -> {"id", "k" (address id), "url", "time", "cits": the citations that mean this document}
DOCS_OF: dict = {}   # address id -> its sources, oldest first; the one with no time (the address as it is) last
DOC_FOR: dict = {}   # (address id, contest id) -> source id
DOC_ALIAS: dict = {}  # address id -> source id, for an address whose every source names a time (the old page address leads to the latest)


def _cit_time(k: str, c: dict) -> str | None:
    """The time a citation means the address at: the catalogue's `as_of`, else the Wayback snapshot
    its own copy was taken from, else None (the address as it is)."""
    if c["as_of"]:
        return str(c["as_of"])
    own = sorted(x["ts"] for x in copies(k) if x["via"] == "wayback" and x["ts"] != "unknown"
                 and (x["contest"] == c["contest"] or (x.get("cap") and x["cap"]["path"] in c["archived"])))
    return own[0] if own else None


def _problem_page_only(L: dict) -> bool:
    """An address no contest cites whose copies are all pages of an online judge (a problem's statement
    page or file, fetched for the problem's set)."""
    caps = [c for R in (L.get("resources") or {}).values() for c in R.get("captures") or []]
    return bool(caps) and all(str(c.get("artifact") or "").startswith("judge-") for c in caps)


def index_docs() -> None:
    """Split every address into its sources. A source is an address at a time. One address cited by
    one contest is one source. An address several contests cite is one source per time it is meant
    at: contests that name the same time, and contests of one season (a joint contest, a shared
    problem set), mean the same document; a page reused year after year is a source per year."""
    DOCS.clear(); DOCS_OF.clear(); DOC_FOR.clear(); DOC_ALIAS.clear()  # noqa: E702
    for k, L in RES.locs.items():
        cits = citations(k)
        if not cits and _problem_page_only(L):
            continue   # a problem's page on an online judge, held for its statement: not a source of a contest
        groups: dict = {}
        if len(cits) <= 1:
            groups[(str(cits[0]["as_of"]) if cits and cits[0]["as_of"] else None)] = list(cits)
        else:
            season = lambda c: (CONTESTS.get(c["contest"]) or {}).get("season")  # noqa: E731
            times = {c["contest"]: _cit_time(k, c) for c in cits}
            # times read off copies (not named by the catalogue) on one day are one visit to the page: one source
            first: dict = {}
            for c in cits:
                t = times[c["contest"]]
                if t and not c["as_of"] and len(t) >= 8:
                    first[t[:8]] = min(first.get(t[:8], t), t)
            for c in cits:
                t = times[c["contest"]]
                if t and not c["as_of"] and len(t) >= 8:
                    times[c["contest"]] = first[t[:8]]
            of_season: dict = {}
            for named in (True, False):   # a time the catalogue names wins over one read off a copy
                for c in cits:
                    if bool(c["as_of"]) == named and times[c["contest"]] and season(c):
                        of_season.setdefault(season(c), times[c["contest"]])
            for c in cits:
                t = times[c["contest"]] if c["as_of"] else of_season.get(season(c), times[c["contest"]])
                groups.setdefault(t, []).append(c)
        order = sorted(groups, key=lambda t: (t is None, t or ""))
        docs = []
        for t in order:
            sid = k if (len(order) == 1 or t is None) else hashlib.sha256(f"{L['key']}@{t}".encode()).hexdigest()[:12]
            d = {"id": sid, "k": k, "url": L["url"], "time": t, "cits": groups[t]}
            DOCS[sid] = d
            docs.append(d)
            for c in groups[t]:
                DOC_FOR[(k, c["contest"])] = sid
        DOCS_OF[k] = docs
        if k not in DOCS:
            DOC_ALIAS[k] = docs[-1]["id"]


def doc_for(url: str, cid: str | None = None) -> dict | None:
    """The source a contest means by an address; with no contest, the address as it is (else its latest)."""
    k = lid(url)
    ds = DOCS_OF.get(k)
    if not ds:
        return None
    return DOCS.get(DOC_FOR.get((k, cid))) or ds[-1]


def doc_copies(d: dict) -> list[dict]:
    """The copies we hold of one source: every copy of the address when it is its only source, else
    the copies captured for the contests that mean this source."""
    cs = copies(d["k"])
    if len(DOCS_OF[d["k"]]) == 1:
        return cs
    mine = {c["contest"] for c in d["cits"]}
    paths = {p for c in d["cits"] for p in c["archived"]}
    return [x for x in cs if x["contest"] in mine or (x.get("cap") and x["cap"]["path"] in paths)]


def _nearest(tss: list[str], want: str | None) -> str:
    if not want:
        return max(tss)
    w = int(str(want).ljust(14, "0")[:14])
    return min(tss, key=lambda t: abs(int(str(t).ljust(14, "0")[:14]) - w))


def current_copy(cs: list[dict], want: str | None = None) -> dict | None:
    """The one copy that counts, of those we hold: the newest the public replay serves, else a crawled
    website, else the newest capture. `want` (a time) picks the copy nearest that time instead: used
    when the address has since changed, so that a late fetch does not stand in for the document."""
    if not cs:
        return None
    if want:
        dated = [x for x in cs if x["ts"] != "unknown"]
        if dated:
            near = _nearest([x["ts"] for x in dated], want)
            return next(x for x in dated if x["ts"] == near)
    order = sorted(cs, key=lambda x: (x["ts"] != "unknown", x["ts"]), reverse=True)
    return (next((x for x in order if x["kind"] == "capture" and x["cap"].get("replay")), None)
            or next((x for x in order if x["kind"] == "website"), None) or order[0])


def open_copy(x: dict | None) -> str:
    """The link that opens a copy (a source's own page is the only place it appears)."""
    if not x:
        return ""
    if x["kind"] == "website":
        w = x["site"]
        return local_link(f"site/{w['contest']}/{w['dir'].rsplit('/', 1)[-1]}/", "open the archived website")
    if x["cap"].get("replay"):
        return f'<a class="ext" href="{replay_url(x["cap"]["replay"])}">open our copy</a>'
    return local_link("archive/" + x["cap"]["path"], "open our copy")


def _place(s: str, word: str, tip: str | None = None, **more) -> dict:
    return {"s": s, "word": word, "tip": tip or PLACE_TIP[word], **more}


def avail(url: str, cid: str | None = None, e: dict | None = None) -> dict:
    """Where a source can be found. {"live": .., "wb": .., "ours": .., "lost": bool, "current": the
    copy that counts}; each place is {"s": yes|part|no|pending|na, "word": its one word, "tip": the
    sentence behind it}; the address also has "checked", the Wayback entry "ts" (the snapshot to
    open), ours "ts" (the time its copy shows). `cid` picks the contest's own source when the
    address has several; `e` is the catalogue entry when the caller has it (its verdict wins)."""
    k = lid(url)
    L = RES.locs.get(k)
    d = doc_for(url, cid)
    if not L or not d:
        return {"live": _place("pending", "not checked", checked=None), "wb": _place("pending", "not checked", ts=None),
                "ours": _place("pending", "not captured", ts=None), "lost": False, "copies": [], "current": None, "doc": None}
    cit = next((c for c in d["cits"] if c["contest"] == cid), None) or (d["cits"][0] if d["cits"] else None)
    h = L.get("health") or {}
    st = (e or {}).get("url_state") or (cit or {}).get("state") or h.get("state")
    when = (e or {}).get("url_checked") or (cit or {}).get("checked") or h.get("checked")
    if st == "dead" and h.get("state") == "dead" and BLOCKED.search(h.get("evidence") or ""):
        st = "blocked"   # recorded as dead by the live check; shown as what it is
    live = _place(LIVE_S[st], LIVE_WORD[st], checked=when) if st in LIVE_S else _place("pending", "not checked", checked=None)
    cs = doc_copies(d)
    mine = {c["contest"] for c in d["cits"]}
    one = len(DOCS_OF[k]) == 1
    probes = [p for p in L.get("probes") or [] if p.get("outcome") == "junk" and (one or p.get("contest") in mine or p.get("contest") is None)]
    as_of = (e or {}).get("as_of") or (cit or {}).get("as_of") or d["time"]
    wb_held = sorted(x["ts"] for x in cs if x["via"] == "wayback" and x["ts"] != "unknown")
    wb_junk = [p for p in probes if p.get("via") == "wayback"]
    w = L.get("wayback") or {}
    wm = re.search(r"\((\d{8,14})\)", w.get("evidence") or "")
    if wb_held:
        wb = _place("yes", "snapshot", ts=_nearest(wb_held, as_of))
    elif wb_junk:
        wb = _place("part", "bad snapshot", PLACE_TIP["bad snapshot"] + ": " + plain_why(wb_junk[-1].get("evidence"))[:160], ts=wb_junk[-1].get("ts"))
    elif as_of:
        wb = _place("yes", "snapshot", ts=as_of)
    elif CMS_STANDINGS.match(url):
        wb = _place("na", "n/a", "does not apply: the page is an app, and a snapshot of it shows nothing", ts=None)
    elif w.get("state") == "ok":
        wb = _place("yes", "snapshot", ts=wm.group(1) if wm else None)
    elif w.get("state") == "none":
        wb = _place("no", "no snapshot", ts=None)
    elif w.get("state") == "excluded":
        wb = _place("no", "excluded", ts=None)
    else:
        wb = _place("pending", "not checked", ts=None)
    ours_junk = [p for p in probes if p.get("path") or p.get("dir")]
    cur = None
    if cs:
        cur = current_copy(cs, as_of if st in ("changed", "replaced") else None)
        ours = _place("yes", "held", ts=cur["ts"] if cur["ts"] != "unknown" else None)
    elif k in EMPTY_STANDINGS:
        live = _place("part", "empty", checked=when)
        ours = _place("na", "n/a", "does not apply: the page is empty, there is nothing to hold", ts=None)
    elif ours_junk:
        ours = _place("part", "bad copy", PLACE_TIP["bad copy"] + ": " + plain_why(ours_junk[-1].get("evidence"))[:160], ts=None)
    elif live["s"] == "no" and wb["s"] == "no":
        ours = _place("no", "lost", ts=None)
    else:
        ours = _place("pending", "not captured", PLACE_TIP["not captured"] + (
            "; the address turns our fetcher away, so it needs a browser" if live["word"] == "blocked" else
            "; it can be captured from the address" if live["s"] in ("yes", "part") else
            "; it can be captured from the Wayback snapshot" if wb["s"] == "yes" else ""), ts=None)
    return {"live": live, "wb": wb, "ours": ours, "lost": ours["word"] == "lost", "copies": cs, "current": cur, "doc": d}


def avail_marks(a: dict) -> str:
    """The unit: three marks, always address · Wayback · archive. The label is the place; the colour
    is the answer (green there, amber in doubt, red confirmed not there, blue not done yet, grey n/a)."""
    return '<span class="av">' + "".join(
        f'<span class="m {AV_CLS[a[key]["s"]]}" title="{esc(full + ": " + a[key]["word"] + " — " + a[key]["tip"])}">{lab}</span>'
        for key, lab, full in AV_PLACES) + "</span>"


def avail_pills(a: dict) -> str:
    """The same three answers as pills with their words, for the card at the top of a source's page."""
    return "".join(f'<a class="pl {AV_Q[a[key]["s"]]}" href="#where" title="{esc(full + ": " + a[key]["tip"])}">{lab}: {esc(a[key]["word"])}</a>'
                   for key, lab, full in AV_PLACES)


def avail_values(a: dict) -> str:
    """The filter values of an availability cell (one per place)."""
    return "|".join(f'{lab}: {a[key]["word"]}' for key, lab, _full in AV_PLACES)


def avail_cell(url: str, cid: str | None = None, e: dict | None = None) -> str:
    a = avail(url, cid, e)
    return f'<td class="nw" data-vs="{esc(avail_values(a))}">{avail_marks(a)}</td>'


AVAIL_TH = ('<th data-f="found at" title="where the source can be found: at its address now, in the Wayback Machine, in our archive">'
            "address · Wayback · archive</th>")



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


_LOC_OF: dict = {}


def loc_tokens(c: dict) -> list[str]:
    """Every node of the location tree a contest is counted under (its places and all they lie in):
    exactly the nodes whose page lists it."""
    if not _LOC_OF:
        for nid, cids in LOC_SUB.items():
            for cid in cids:
                _LOC_OF.setdefault(cid, []).append(nid)
        _LOC_OF[""] = []
    return sorted(_LOC_OF.get(c["id"], []))


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
REPLAY_REPO: dict = {}    # baked replay path -> the repository of its shard, when not the first ("replay-2"; replay/tools/bake.py SHARDS)


def replay_url(path: str) -> str:
    """The public address of a baked page: the replay tree is split over several Pages repositories
    by the contest's year, replay, replay-2, ... (REPLAY_BASE is the first one's address)."""
    repo = REPLAY_REPO.get(path, "replay")
    return f"{REPLAY_BASE}{repo.removeprefix('replay')}/{esc(path)}"
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
                inv = {pid: L for L, pid in set_letters(doc, m["contest"]).items()}
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


def set_labels(doc: dict, cid: str) -> list[str]:
    """The letters alone that a contest's problems carried (`labels`, read off its scoreboard),
    for a set whose problems are not listed."""
    return next((m.get("labels") for m in doc.get("contests") or [] if m.get("contest") == cid), None) or []


def set_members(doc: dict) -> list[str]:
    return [m["contest"] for m in doc.get("contests") or []]


def set_own_contest(sid: str, doc: dict) -> bool:
    """The usual case: the set belongs to exactly the contest of the same id."""
    return set_members(doc) == [sid]


STATE_CLS = {"all": "h", "some": "l", "link only": "k", "none": "n", "not recorded": "u"}
STATE_TIP = {"all": "held for every problem", "some": "held for some problems", "link only": "a source that has it is known; we hold no copy",
             "none": "none held, none known", "not recorded": "a source is known, but what it holds is not recorded"}


def comp_marks(states: dict) -> str:
    """One mark per kind of problem material (coverage.COMPONENTS), from wherever we have it:
    the problem archive, or a source we hold a copy of."""
    return "".join(f'<i class="m {STATE_CLS[states[k]]}" title="{what}: {"an editorial is held" if k == "editorial" and states[k] == "all" else STATE_TIP[states[k]]}">{letter}</i>'
                   for k, letter, what in CV.COMPONENTS)


def held_marks(pb: dict) -> str:
    """The marks of a problem set (comp_marks of its coverage record)."""
    return comp_marks(COV.set_record(pb["id"]))



def problems_cell(c: dict, rel: str) -> str:
    """The problems cell of a contest row: the number of problems (linking to the set) and the
    archive's holdings; `src` when only a published set or judge page is known."""
    pb = set_for(c)
    if pb:
        total, listed = set_counts(pb)
        lab = str(total) if total else ("set" if not listed else f"{listed} listed")
        return f'<a href="{rel}problemset/{esc(pb["id"])}.html" title="problem set {esc(pb["id"])}: {total or "?"} problems, {listed} listed by name">{lab}</a> ' + held_marks(pb)
    if c.get("status") != "upcoming" and (has_role(c, "problemset") or has_role(c, "problem")):
        return ('<span class="m u" title="no problem set recorded; a published set or a page of one of its problems is known — the marks after it say what we hold of it">src</span> '
                + comp_marks(rec(c)["problems"]))
    return ""


def problems_value(c: dict) -> str:
    """The problem list: listed / partly listed / count only / source only / none, and `set recorded`."""
    if not did_run(c):
        return "upcoming"
    st = rec(c)["set"]
    return toks(st, "set recorded" if st not in ("source only", "none") else "no set", "not listed" if st != "listed" else "")


def repo_link(pb: dict) -> str:
    repo = pb.get("repo")
    if not repo:
        return ""
    name = repo.split("/", 1)[1]
    tip = "statements only, in the shared statement-only repo (private)" if name == "statement-only" else "problem archive repo (private)"
    return f'<a class="ext" href="https://github.com/{esc(repo)}" title="{tip}">{esc(name)}</a>'


def judge_name(jid: str) -> str:
    return (JUDGES.get(jid) or {}).get("name") or jid


def judge_mark(jid: str, tag: str = "span", attrs: str = "", tip: str = "") -> str:
    """An online judge as its logo (tools/site_assets/judges/<id>.png, drawn by a rule that
    main() adds to site.css), or its short name when there is no logo. The judge's name is
    the hover text. A closed judge's logo is greyed."""
    j = JUDGES.get(jid) or {}
    closed = " jc" if j.get("status") == "closed" else ""
    title = f' title="{esc(tip or judge_name(jid))}"'
    role = "" if tag == "a" else ' role="img"'
    if (ASSETS / "judges" / f"{jid}.png").exists():
        return f'<{tag} class="jl j-{esc(jid)}{closed}"{attrs}{title}{role} aria-label="{esc(j.get("short") or judge_name(jid))}"></{tag}>'
    return f'<{tag} class="jl jt{closed}"{attrs}{title}>{esc(j.get("short") or judge_name(jid))}</{tag}>'


def judge_link(jid: str, rel: str, logo: bool = False) -> str:
    """An online judge linking to its page: by name in running text, by logo in a table."""
    if jid in JUDGES:
        if logo:
            return judge_mark(jid, "a", f' href="{rel}judge/{esc(jid)}.html"')
        return f'<a href="{rel}judge/{esc(jid)}.html">{esc(judge_name(jid))}</a>'
    return esc(jid)


def judge_closed_chip(jid: str) -> str:
    j = JUDGES.get(jid) or {}
    if j.get("status") != "closed":
        return ""
    return " " + chip("closed" + (f' {j["closed"]}' if j.get("closed") else ""), "n",
                      "this online judge has shut down; its pages survive only in Wayback snapshots")


def problem_judge_links(p: dict, sep: str = " ", by_id: bool = False, tips: bool = True) -> str:
    """A problem's online judges: each the judge's logo (or, on the judge's own page, the
    problem's id there), linking straight to the problem on the judge — the Wayback
    snapshot for a judge that has closed."""
    parts = []
    for j in p.get("judges") or []:
        url, as_of = j["url"], j.get("as_of")
        closed = (JUDGES.get(j["judge"]) or {}).get("status") == "closed"
        # a closed judge's own address leads nowhere: its link opens the Wayback Machine, at the snapshot when one is named
        href = wayback_link(url, as_of) if as_of or closed else url
        tip = res_label(url, as_of, 200) + (f" — {judge_name(j['judge'])} id {j['id']}" if j.get("id") else "") + (" (Wayback snapshot)" if as_of else " (Wayback Machine)" if closed else "")
        if by_id:
            parts.append(f'<a class="ext" href="{esc(href)}"' + (f' title="{esc(tip)}"' if tips else "") + f'>{esc(j.get("id") or "open")}</a>')
        else:
            parts.append(judge_mark(j["judge"], "a", f' href="{esc(href)}"', f"{judge_name(j['judge'])} — {tip}" if tips else ""))
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
        out = {k: k in have for k, *_ in HAVE_KINDS}
    else:
        out = {}
        for k, *_ in HAVE_KINDS:
            st = (doc or {}).get(SET_KIND.get(k, ""))
            out[k] = True if st == "full" else False if st == "none" else None
    if COV is not None and doc and doc.get("id") in SETS:
        # what we hold of the whole set, from the archive or from a source we hold a copy of (the set card's pills):
        # held for every problem => held for this one; held for some, archive none => which ones is not recorded
        whole = COV.set_record(doc["id"])
        for k in SET_KIND:
            if whole[k] == "all":
                out[k] = True
            elif whole[k] == "some" and out[k] is False and "have" not in p:
                out[k] = None
    if not out["statement"] and COV is not None and doc and p["id"] in COV.statements_held(doc):
        out["statement"] = True   # the problem has a held statement of its own among its contests' sources
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
    """How many of these contests there are, how many ran, how many are upcoming."""
    n = sum(1 for c in cs if c.get("status") != "upcoming")
    return {"all": len(cs), "n": n, "upcoming": len(cs) - n}


# the coverage columns of a table whose rows are groups of contests (series, seasons, countries):
# one small bar per question, the same bars as everywhere else. One or two questions per kind of content.
INDEX_FACETS = ("results", "list", "statement", "website", "date")


def group_heads(keys: tuple = INDEX_FACETS) -> list[str]:
    return [th(esc(CV.FACET[k][1]), title=f"{CV.FACET[k][1]}: the contests of the row split by answer; the percentage is the share in the best one "
                                          f"({CV.FACET[k][3][0]}). Sorts on that share; a segment opens its contests.") for k in keys]


def group_cells(cs: list[dict], rel: str, scope: dict | None, keys: tuple = INDEX_FACETS) -> str:
    """The coverage cells of one row: per question a small stacked bar and the share in the best answer."""
    cs = [c for c in cs if did_run(c)]
    n = len(cs)
    if not n:
        return "".join('<td class="gb muted" data-v="">–</td>' for _k in keys)
    out = []
    for k in keys:
        p = pct(sum(1 for c in cs if good(c, k)), n)
        out.append(f'<td class="gb" data-v="{p}">' + sbar(cs, k, rel, scope, "sm", False) + f'<span class="gp">{p}%</span></td>')
    return "".join(out)


# ---- contest rows: the one set of columns every table of contests picks from ----
def _c_contest(c, rel):
    return f'<td class="nw">{link_contest(c["id"], rel)}</td>'


def _c_contest_name(c, rel):
    return (f'<td class="name">{link_contest(c["id"], rel)}'
            + (f'<span class="sub">{esc(c["name"])}</span>' if c.get("name") else "") + "</td>")


CONTEST_COLS = {
    "contest": (th("contest"), _c_contest),
    "contest+name": (th("contest"), _c_contest_name),
    "season": (th("season", f=True, k="season"), lambda c, rel: f'<td class="nw" data-v="{c.get("season", "")}">{link_season(c.get("season"), rel)}</td>'),
    "date": (th("date"), lambda c, rel: f'<td class="nw" data-v="{esc(c.get("date", ""))}">{link_date(c.get("date"), rel)}</td>'),
    "location": (th("location", f="country", k="country"), lambda c, rel: f'<td data-vs="{esc("|".join(place_countries(c)))}">{place_cell(c, rel)}</td>'),
    "series": (th("series", f=True, k="series"), lambda c, rel: f'<td class="nw">{link_series(SERIES_OF[c["id"]], rel)}</td>'),
    # series with its level and region underneath; the two hidden columns after it carry the filters
    "series+": (th("series", f=True, k="series"), lambda c, rel: (f'<td class="nw" data-v="{esc(SERIES_OF[c["id"]])}">{link_series(SERIES_OF[c["id"]], rel)}'
                                                     f'<span class="sub">{esc(level_of(SERIES_OF[c["id"]]))} · {esc(SERIES_REGION.get(SERIES_OF[c["id"]], ""))}</span></td>')),
    "region": (th("region", f=True, k="region"), lambda c, rel: f'<td class="nw">{esc(SERIES_REGION.get(SERIES_OF[c["id"]], ""))}</td>'),
    "level": (th("level", f=True, k="level"), lambda c, rel: f'<td class="nw">{esc(level_of(SERIES_OF[c["id"]]))}</td>'),
    "region-": (th("region", f=True, k="region", hid=True), lambda c, rel: f'<td class="hid">{esc(SERIES_REGION.get(SERIES_OF[c["id"]], ""))}</td>'),
    "level-": (th("level", f=True, k="level", hid=True), lambda c, rel: f'<td class="hid">{esc(level_of(SERIES_OF[c["id"]]))}</td>'),
    "advances": (th("advances to"), lambda c, rel: '<td class="nw">' + ", ".join(link_contest(p, rel, False) for p in refs(c.get("parent"))) + "</td>"),
    # the three kinds of content: what is shown is the marks; the filter is the coverage record (coverage.py)
    "results": (th("results", f=True, k="results", g=True, o=RESULT_ORDER, title="the best result we hold a copy of"),
                lambda c, rel: f'<td class="nw" data-vs="{esc(results_value(c))}">{result_marks(c, rel)}</td>'),
    "problems": (th("problems", f="problem list", k="problems", g=True, o=CV.SET_STATES + ("set recorded", "no set", "not listed", "upcoming")),
                 lambda c, rel: f'<td class="nw" data-vs="{esc(problems_value(c))}">{problems_cell(c, rel)}</td>'),
    "website": (th("website", f=True, k="website", g=True, o=WEB_ORDER), lambda c, rel: f'<td data-vs="{esc(website_value(c))}">{website_cell(c, rel)}</td>'),
    "cms": (th("CMS id"), lambda c, rel: f'<td class="nw">{cms_cell(c)}</td>'),
    # hidden columns: they are there for their filter (the contest list; every coverage number links into it)
    "status-": (th("status", f=True, k="status", hid=True), lambda c, rel: f'<td class="hid">{"ran" if did_run(c) else "upcoming"}</td>'),
    "era-": (th("era", f=True, k="era", hid=True, o=tuple(lab for lab, *_ in ERAS)), lambda c, rel: f'<td class="hid">{esc(era_of(c))}</td>'),
    "fetch-": (th("fetch", f="known, not held", k="fetch", g=True, hid=True, o=RESULT_ORDER + ("any",),
                  title="a better result than the one we hold is known at an address we have no copy of"),
               lambda c, rel: f'<td class="hid" data-vs="{esc(fetch_value(c))}"></td>'),
    "also-": (th("also", f="results also", k="also", g=True, hid=True), lambda c, rel: f'<td class="hid" data-vs="{esc(also_value(c))}"></td>'),
    **{f"{key}-": (th(what, f=what, k=COMP_KEY[key], g=True, hid=True, o=STATE_ORDER),
                   (lambda key: lambda c, rel: f'<td class="hid" data-vs="{esc(component_value(c, key))}"></td>')(key))
       for key, _m, what in CV.COMPONENTS},
    "pmeta-": (th("problem metadata", f="problem metadata", k="pmeta", g=True, hid=True,
                  o=tuple(f"{lab}: {s}" for _k, lab in CV.PMETA for s in ("all", "some", "none", "missing"))),
               lambda c, rel: f'<td class="hid" data-vs="{esc(pmeta_value(c))}"></td>'),
    "meta-": (th("contest metadata", f="contest metadata", k="meta", g=True, hid=True,
                 o=tuple(f"{lab}: {s}" for _k, lab in CV.META for s in ("have", "missing", "none"))),
              lambda c, rel: f'<td class="hid" data-vs="{esc(meta_value(c))}"></td>'),
}
CONTEST_COLS["loc-"] = ('<th class="hid" data-k="loc" data-p="location">location</th>',
                        lambda c, rel: f'<td class="hid" data-vs="{esc("|".join(loc_tokens(c)))}"></td>')
COVERAGE_COLS = ("loc-", "fetch-", "also-") + tuple(f"{key}-" for key, *_ in CV.COMPONENTS) + ("pmeta-", "meta-")
CONTEST_INDEX_COLS = (("contest+name", "date", "location", "series+", "region-", "level-", "season", "era-", "status-",
                       "results", "problems", "website", "cms") + COVERAGE_COLS)


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


STAMP = re.compile(r"\s*\[(?:existence hunt|url[- ]hunt|content check|judge hunt)[^\]]*\]")   # which pass of ours found a line
BOOKKEEPING = re.compile(r"\bruling \d{4}-|misclass audit|icpc-history|icpc-nopii|master_contests|problem archive sheet|\btools/\w+\.py")


def evidence_lines(c: dict) -> list[str]:
    """The hand-collected lines of `provenance` (where a date came from, proof that a dark
    contest ran). Import stamps about the problem set are not evidence about the contest."""
    out = []
    for x in refs(c.get("provenance")):
        x = STAMP.sub("", str(x)).strip()
        if x and not BOILERPLATE.match(x) and not BOOKKEEPING.search(x):
            out.append(x)
    return out


def status_chips(c: dict, cid: str, rel: str) -> str:
    """Under a contest's title: anything unusual as chips (upcoming, lost sources, copies only we hold),
    then its coverage card: every question coverage asks, answered for this contest, and what is wanted."""
    chips = []
    if c.get("status") == "upcoming":
        chips.append(chip("upcoming", "n", "has not run yet"))
    gone = [u for u, _w, held in lost_locators(c) if not held]
    only = [u for u, _w, held in lost_locators(c) if held]
    if gone:
        chips.append(chip(f"{len(gone)} lost", "x", "gone from its address, not in the Wayback Machine, and no copy here: " + "; ".join(gone)))
    if only:
        chips.append(chip(f"{len(only)} only here", "h", "gone from its address and not in the Wayback Machine — our copy is the only one: " + "; ".join(only)))
    return ('<p class="status">' + "".join(chips) + " " + help_link("status", rel) + "</p>" if chips else "") + contest_coverage(c, rel)


HUNT_STAMP = re.compile(r"\s*\((?:judge hunt|QOJ ICPC category tree) .*\)$")


def source_time(e: dict, cid: str | None) -> str | None:
    """The time a contest means a source at: the catalogue's `as_of`, else the time of the source
    the contest means when the address has several."""
    return e.get("as_of") or (doc_for(e["url"], cid) or {}).get("time")


def source_problem(c: dict, e: dict, rel: str) -> str:
    """The problem a per-problem source is about, linked, when it is in the problem list: by its letter in
    the contest, else by its address (one of the problem's online-judge links: coverage.Coverage._problem_of)."""
    doc = set_for(c) if "problem" in e.get("roles", ()) else {}
    pid = COV._problem_of(doc, c, e) if doc and COV is not None else None
    if not isinstance(pid, str):
        return f' <b title="problem {esc(e["problem"])}">{esc(e["problem"])}</b> ' if e.get("problem") else ""
    L = letter_of(doc, c["id"], pid)
    return " " + (f"<b>{esc(L)}</b> " if L else "") + problem_link(pid, rel) + " "


def source_table(cid: str, entries: list[dict], rel: str, kind: str, extra_rows: list[str] | None = None) -> str:
    """The sources of one kind on a contest page: the type of each (and which problem, which part
    of the contest, which online judge), the source (to its own page), and where it is found —
    at its address, in the Wayback Machine, in our archive — as one unit. Nothing here leaves
    the site; a copy is opened from the source's own page."""
    rows = []
    for e in entries:
        url = e["url"]
        roles = R.U("source", "".join(role_chip(r) for r in sorted(e["roles"], key=lambda r: RANK[r])), " ".join(sorted(e["roles"])), url)
        roles += source_problem(CONTESTS.get(cid) or {"id": cid}, e, rel)
        if e.get("scope"):
            roles += R.U("division", chip(e["scope"], "sc", "this source covers one part of the contest, not all of it"), e["scope"], url)
        if e.get("judge"):
            roles += judge_link(e["judge"], rel, logo=True) + judge_closed_chip(e["judge"])
        t = source_time(e, cid)
        rows.append(f"<tr><td>{roles}</td><td class=\"url\">{link_source(url, rel, res_label(url, t, 90), t, cid)}</td>" + avail_cell(url, cid, e) + "</tr>")
    rows += extra_rows or []
    return table([th("type"), th("source"), AVAIL_TH], rows, "nosort")


def contest_page(cid: str, c: dict, rel: str) -> str:
    sid = SERIES_OF[cid]
    b = [crumbs(f'<a href="{rel}contest/index.html">Contests</a>', link_series(sid, rel)),
         f"<h1{R.at('contest', cid)}>{esc(cid)}</h1>"]
    if c.get("name"):
        b.append(f'<p class="lede">{R.U("name", esc(c["name"]), c["name"])}</p>')
    else:
        b.append(R.line("name", "no name recorded"))
    b.append(status_chips(c, cid, rel))
    upcoming = c.get("status") == "upcoming"
    b.append(R.line("ran", "Has not run yet" if upcoming else "Took place", "upcoming" if upcoming else "yes"))

    # ---- facts ----
    d = ['<dl class="facts">',
         f"<dt>series</dt><dd>{R.U('series', link_series(sid, rel), sid)} <span class=\"muted\">{esc(level_of(sid))} · {esc(SERIES_REGION.get(sid, ''))}</span></dd>"]
    if c.get("season"):
        d.append(f"<dt>season</dt><dd>{R.U('season', link_season(c['season'], rel), c['season'])}</dd>")
    d.append("<dt>date</dt><dd>" + R.U("date", link_date(c["date"], rel) if c.get("date") else '<span class="muted">not known</span>', c.get("date") or "") + "</dd>")
    all_sites = c.get("sites") or []
    def site_unit(s):  # one site as a reviewable unit, and its own date as another; the key is the place and the name it goes by
        x = site_line(s, rel)
        key = ("online: " if s.get("type") == "online" else "") + " ".join(str(v) for v in (s.get("location"), s.get("name")) if v)
        when = f'<span class="small muted">{esc(s["date"])}</span>' if s.get("date") else None
        if x and when and " " + when in x:
            return R.U("site", x.replace(" " + when, "", 1), key, key) + " " + R.U("site_date", when, s["date"], key)
        return R.U("site", x, key, key) if x else ""
    phys = [x for x in (site_unit(s) for s in all_sites if not s.get("type")) if x]
    remote = [x for x in (site_unit(s) for s in all_sites if s.get("type") == "online") if x]
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
                                        if lines else '<span class="muted">not known</span>') + " " + R.slot("site", "add a site") + "</dd>")
    for label, ids in (
        ("advances to", refs(c.get("parent"))),
        ("fed by", sorted(CHILDREN.get(cid, []))),
        ("previous edition", sorted(PREV.get(cid, []))),
        ("next edition", refs(c.get("next"))),
        ("subset of", [c["subset_of"]] if c.get("subset_of") else []),
        ("regional views", sorted(SUBSETS.get(cid, []))),
    ):
        # every relation is reviewed where it is shown, also the ones stored on the other contest (fed by, previous edition, regional views)
        unit = {"advances to": "advances", "fed by": "fed_by", "previous edition": "previous", "next edition": "next",
                "subset of": "subset_of", "regional views": "views"}[label]
        if ids:
            d.append(f"<dt>{label}</dt><dd>" + R.U(unit, ", ".join(link_contest(x, rel, False) for x in ids), ",".join(ids)) + "</dd>")
        elif unit not in ("fed_by", "views") and not (unit == "advances" and "parent" in c):
            d.append(R.row(unit, label))
    if c.get("parent") is None and "parent" in c:
        d.append('<dt>advances to</dt><dd class="muted">' + R.U("advances", "nothing — the top of the hierarchy", "nothing") + "</dd>")
    ids = c.get("cms_ids")
    if ids:
        d.append("<dt>CMS id</dt><dd>" + R.U("cms_id", ", ".join(cms_links(i) for i in ids), ",".join(str(i) for i in ids)) + "</dd>")
    elif ids == []:
        d.append('<dt>CMS id</dt><dd class="muted">' + R.U("cms_id", "none", "none") + "</dd>")
    else:
        d.append(R.row("cms_id", "CMS id"))
    d.append("</dl>")
    b += d

    # ---- Website ----
    b.append('<h2 id="website">Website</h2>')
    webs = by_role(c, "web")
    if webs:
        b.append(source_table(cid, webs, rel, "web"))
    elif rec(c)["website"] == "confirmed none":
        b.append('<p class="empty">' + R.U("none", "This contest had no website of its own — looked for and confirmed.", "none", "website") + "</p>")
    else:
        b.append('<p class="empty">' + R.U("none", "No website known. Nobody has found an address yet; that is not the same as there being none.", "", "website") + "</p>")
    b.append(R.slot("source", "add a website", "website", tag="p"))

    # ---- Results ----
    b.append('<h2 id="results">Results</h2>')
    res_entries, seen = [], set()
    for key in RESULT_KINDS:  # the ladder, best first, then the frozen scoreboard
        for e in by_role(c, key):
            if id(e) not in seen:
                seen.add(id(e))
                res_entries.append(e)
    matched = {"a/" + p for e in sources(c) for p in archived(e)} | {REPLAY_LOOKUP.get((cid, norm_key(e["url"]))) for e in sources(c)}
    extra = []
    for e in REPLAY_BY_CONTEST.get(cid, []):  # replay pages the catalogue does not point at
        if e["path"] in matched or e.get("at") in matched or e.get("artifact") == "problemset" or not e.get("url"):
            continue
        matched.add(e["path"])
        extra.append(f'<tr><td>{role_chip(e["artifact"])}{chip("not listed yet", "n", "we hold a copy; it is not yet listed as a source of this contest")}</td>'
                     f'<td class="url">{link_source(e["url"], rel, res_label(e["url"], None, 90), None, cid)}</td>' + avail_cell(e["url"], cid) + "</tr>")
    ev = evidence_lines(c)
    if res_entries or extra:
        b.append(source_table(cid, res_entries, rel, "results", extra))
    elif c.get("status") == "upcoming":
        b.append('<p class="empty">Not run yet.</p>')
    else:
        b.append('<p class="empty">' + R.U("none", "No results found — no scoreboard, standings, rankings or team list, not even in the ICPC CMS.", "", "results")
                 + (" What we do know is under Evidence below." if ev else "") + "</p>")
    if not upcoming:
        b.append(R.slot("source", "add a result source", "results", tag="p"))

    # ---- Problems ----
    b.append('<h2 id="problems">Problems</h2>')
    pb = set_for(c)
    psrc = [s for s in sources(c) if {"problemset", "problem", "editorial"} & set(s["roles"])]
    if c.get("status") == "upcoming":
        b.append('<p class="empty">Not run yet — nothing about a contest\'s problems is published before it has run.</p>')
    elif not pb and not psrc:
        b.append('<p class="empty">' + R.U("problemset", "Nothing is known about this contest\'s problems: no problem set recorded, no published set, no online judge.", "") + "</p>")
    else:
        if pb:
            total, listed = set_counts(pb)
            others = [m for m in set_members(pb) if m != cid]
            b.append(f'<p>Problem set {R.U("problemset", set_link(pb["id"], rel), pb["id"])}: ' + (f"{total} problems" if total else "number of problems not known")
                     + (f", {listed} listed by name" if listed and set_list_state(pb) == "partial" else "")
                     + f' &nbsp;{held_marks(pb)} <span class="small muted">what we hold of it — details on the set\'s page</span>'
                     + (' <span class="small muted">· shared with ' + ", ".join(contest_ref(x, rel) for x in others) + "</span>" if others else "") + "</p>")
            probs = set_problems_in_order(pb, cid)
            if not probs and set_labels(pb, cid):
                b.append("<p>Letters: " + " · ".join(f"<b>{esc(x)}</b>" for x in set_labels(pb, cid))
                         + ' <span class="small muted">— the problems are not listed by name yet</span></p>')
            if probs:
                b.append('<p class="cols">' + "<br>".join(
                    R.U("letter", f'<b>{esc(L or "?")}</b>', (L or "") if set_letters(pb, cid) else "", p["id"], p["name"]) + f' &nbsp;{problem_link(p["id"], rel, p["name"])}'
                    + (" " + chip("private", "n", "kept private after the contest; name and uuid are public") if p.get("status") == "private" else "")
                    for L, p in probs) + "</p>")
                dv = set_divisions(pb, cid)
                if dv:
                    b.append('<p class="note">' + ("Letters per division: " + " / ".join(f"{esc(n)} ({len(lm)} problems)" for n, lm in dv.items())
                                                    + "; – where a problem was not in that division." if len(dv) > 1 else
                                                    f"Letters in {esc(next(iter(dv)))} ({len(next(iter(dv.values())))} problems); the other divisions' letters are not known.") + "</p>")
                if not set_letters(pb, cid):
                    b.append('<p class="note">The letters are not known for this contest'
                             + (" (shown with another contest's letters)." if any(set_letters(pb, m) for m in set_members(pb)) else ".") + "</p>")
        else:
            b.append('<p class="empty">' + R.U("problemset", "No problem set recorded yet; the sources below are where the problems can be found.", "") + "</p>")
        if psrc:
            b.append(source_table(cid, psrc, rel, "problems"))
    if not upcoming:
        b.append(R.slot("source", "add a problem set or a problem", "problems", tag="p"))

    # ---- everything else ----
    others = [s for s in sources(c) if not (set(s["roles"]) & (set(RESULT_KINDS) | {"web", "problemset", "problem", "editorial"}))]
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


def lineage_chips(doc: dict, rel: str, units: bool = False) -> str:
    """`units`: on the series' own page, where each chip is a reviewable unit."""
    bits = [(f'<span class="chip">{esc(ev["type"].replace("-", " "))} {link_series(ev["series"], rel)} ({ev["year"]})</span>',
             "lineage", f'{ev["type"]} {ev["series"]} {ev["year"]}') for ev in doc["series"].get("lineage") or []]
    bits += [(chip(f"formerly {a}", "n", "an old id of this series"), "aliases", a) for a in doc["series"].get("aliases") or []]
    return " ".join(R.U(u, h, v, v) if units else h for h, u, v in bits)


def series_page(sid: str, doc: dict, rel: str) -> str:
    s = doc["series"]
    b = [crumbs(f'<a href="{rel}series/index.html">Series</a>'), f"<h1{R.at('series', sid)}>{esc(sid)}</h1>"]
    if s.get("name"):
        b.append(f'<p class="lede">{R.U("name", esc(s["name"]), s["name"])}</p>')
    else:
        b.append(R.line("name", "no name recorded"))
    y0, y1 = series_years(doc)
    seasons = [c["season"] for c in doc["contests"] if c.get("season")]
    d = ['<dl class="facts">',
         f"<dt>level</dt><dd>{R.U('level', esc(level_of(sid)), SERIES_TIER.get(sid, ''))}</dd>",
         f"<dt>region</dt><dd>{R.U('region', esc(SERIES_REGION.get(sid, '')), SERIES_REGION.get(sid, ''))}</dd>",
         f"<dt>editions</dt><dd>{len(doc['contests'])}, {y0}–{y1}"
         + (f' <span class="muted">· seasons {link_season(min(seasons), rel)} to {link_season(max(seasons), rel)}</span>' if seasons else "") + "</dd>"]
    d.append(("<dt>lineage</dt><dd>" if lineage_chips(doc, rel) else '<dt class="rvo">lineage</dt><dd class="rvo">') + lineage_chips(doc, rel, True)
             + " " + R.slot("lineage", "add a link to another series") + " " + R.slot("aliases", "add another name") + "</dd>")
    if s.get("rotating_host"):
        d.append("<dt>host</dt><dd>" + R.U("rotating_host", 'rotates between cities <span class="muted">— gaps between years are expected</span>', "yes") + "</dd>")
    else:
        d.append(R.row("rotating_host", "host", "not recorded as rotating"))
    d.append("</dl>")
    b += d
    b.append(group_nums(doc["contests"], rel, {"series": sid}))
    b.append('<p class="tabs">Jump to: <a href="#coverage">coverage</a> <a href="#where">edition by edition</a> <a href="#editions">editions</a></p>')
    b.append(coverage_section(doc["contests"], rel, {"series": sid}, "this series", "Edition by edition",
                              "A column per edition, oldest first; a row per question. A square opens the contest, <i>n missing</i> opens those editions as a list. A faint outlined square has not run yet.",
                              edition_matrix(doc["contests"], rel, {"series": sid})))
    b.append(f'<h2 id="editions">Editions <span class="n">{len(doc["contests"])}</span></h2>')
    b.append(R.slot("contest", "add a missing contest", tag="p"))
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
                    + group_cells(doc["contests"], rel, {"series": sid}) + f'<td class="small">{lineage_chips(doc, rel)}</td></tr>')
    return page("Series", "<h1>Series</h1>"
                f'<p class="intro">{len(series_docs)} series. A series is a line of editions under one name; when a contest was renamed or split, '
                "the lineage column says what it continues from or as. The contest counts are editions that ran.</p>"
                + table([th("series"), th("region", f=True), th("level", f=True), th("contests", num=True), th("years")] + group_heads() + [th("lineage")],
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
    d.append(f'<dt>contests</dt><dd>{len(members)} — <a href="{esc(flt_href(rel, {"season": season}))}">open them as a table</a></dd>')
    d.append("</dl>")
    body += d
    places = {n for c in cs for n in held_at(c)[0]}
    countries = {city_and_country(n)[1] for n in places} - {None}
    body.append(group_nums(cs, rel, {"season": season}, f'<div class="pt"><b>{len(places)}</b><span class="tl-l">locations in {len(countries)} countries</span></div>'))
    body.append('<p class="tabs">Jump to: <a href="#coverage">coverage</a> <a href="#where">contest by contest</a> <a href="#hierarchy">who advances where</a></p>')
    by_r = [(r, sorted((c for c in cs if SERIES_REGION.get(SERIES_OF[c["id"]]) == r), key=lambda c: c["id"])) for r in REGIONS]
    body.append(coverage_section(cs, rel, {"season": season}, "this season's contests", "Contest by contest",
                                 "A row per contest, a column per question. A square opens the contest; a faint outlined one has not run yet.", contest_matrix(by_r, rel)))
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
                    + group_cells(cs, rel, {"season": season}) + "</tr>")
    return page("Seasons", "<h1>Seasons</h1>"
                f'<p class="intro">{len(BY_SEASON)} seasons. A season runs from its first regional to the World Finals those regionals feed; '
                "its page shows who advances where. The contest counts are contests that ran (upcoming ones after the +); "
                "the percentages are shares of those.</p>"
                + table([th("season"), th("World Finals"), th("date"), th("location"), th("season dates"), th("contests", num=True)] + group_heads(), rows),
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


def set_card(sid: str, doc: dict, rel: str) -> str:
    """The card at the top of a problem set's page: the same pills, in the same colours and the same
    order, as the problem part of a contest's coverage card (what the catalogue records about the
    problems, then what we hold of them, from the problem archive or from a source we hold)."""
    members = set_members(doc)
    fc = set_first_contest(doc)
    pr = COV.problems(fc if fc and set_id_of(fc) == sid else {"id": (members or [sid])[0], "problems": {"set": sid}, "sources": []})
    s = {"list": pr["set"], **pr["pmeta"], **pr["problems"]}
    groups = []
    for g in ("Problem metadata", "Problems"):
        pills = []
        for key in (x[0] for x in CV.FACETS if x[2] == g):
            lab, sts, q = CV.FACET[key][1], CV.FACET[key][3], facet_q(key)
            a = s[key]
            cls = q[sts.index(a)]
            pill = f'<span class="pl {cls}" title="{esc(lab)}: {esc(a)} — {q_word(key, cls)}">{esc(lab if a == sts[0] else f"{lab}: {a}")}</span>'
            pills.append(R.U("complete", pill, set_list_state(doc)) if key == "list" else pill)
        groups.append(f'<div class="cc-g"><b>{esc(g)}</b>' + "".join(pills) + "</div>")
    return '<div class="cc">' + "".join(groups) + " " + help_link("status", rel, "what the colours mean") + "</div>"


def problemset_page(sid: str, doc: dict, rel: str) -> str:
    """problemset/<set-id>.html — a problem set: what is recorded and held of it, problem by
    problem. Where the set was published and where it can be solved are sources of the
    contest and stay on the contest page."""
    members = set_members(doc)
    total, listed = set_counts(doc)
    state = set_list_state(doc)
    fc = set_first_contest(doc)
    b = [crumbs(f'<a href="{rel}problemset/index.html">Problem sets</a>'),
         f"<h1{R.at('problemset', sid)}>{esc(sid)}</h1>"]
    if doc.get("name"):
        b.append(f'<p class="lede">{R.U("name", esc(doc["name"]), doc["name"])}</p>')
    else:
        b.append('<p class="lede">' + R.U("name", "The problem set of " + " and ".join(esc((CONTESTS.get(m) or {}).get("name") or m) for m in members[:2]), "") + "</p>")
    b.append(set_card(sid, doc, rel))
    d = ['<dl class="facts">']
    d.append(f'<dt>contest{"s" if len(members) > 1 else ""}</dt><dd>' + ", ".join(R.U("contest", contest_ref(m, rel), m, m) for m in members) + " " + R.slot("contest", "add a contest") + "</dd>")
    if fc.get("season"):
        d.append(f"<dt>season</dt><dd>{link_season(fc['season'], rel)}</dd>")
    d.append("<dt>problems</dt><dd>" + R.U("count", str(total) if total else '<span class="muted">number not known</span>', total or "")
             + (f' <span class="muted">— {listed} listed by name below</span>' if state == "partial" else "") + "</dd>")
    arch = []
    for key, _l, what in HELD_KINDS:
        st = doc.get(key)
        if st:
            n = (doc.get("counts") or {}).get(key)
            arch.append(f"{what}: " + {"full": "all", "partial": f"{n} of {doc.get('count')}" if n is not None else "some", "none": "none"}[st])
    d.append('<dt title="what the ICPC Problem Archive holds for this set">problem archive</dt><dd>'
             + (", ".join(esc(x) for x in arch) if arch else '<span class="muted">holdings not recorded</span>')
             + (f" · {repo_link(doc)} <span class=\"muted\">(private)</span>" if doc.get("repo") else "") + "</dd>")
    if doc.get("aliases"):
        d.append('<dt>replaces</dt><dd class="small">' + ", ".join(esc(a) for a in doc["aliases"])
                 + ' <span class="muted">— these were separate sets with the same problems; their addresses lead here</span></dd>')
    with_letters = [m for m in members if set_letters(doc, m)]
    same_letters = len({json.dumps(set_letters(doc, m), sort_keys=True) for m in with_letters}) == 1
    lab = [(m, set_labels(doc, m)) for m in members if set_labels(doc, m)]
    if doc.get("letters") == "unknown":
        d.append('<dt>letters</dt><dd class="muted">not known — the list came from an online judge, which does not keep contest letters</dd>')
    elif lab and not doc.get("problems"):
        d.append("<dt>letters</dt><dd>" + "<br>".join((f"{contest_ref(m, rel)}: " if len(members) > 1 else "") + " · ".join(f"<b>{esc(x)}</b>" for x in ls) for m, ls in lab) + "</dd>")
    elif len(members) > 1 and with_letters and len(with_letters) < len(members):
        d.append('<dt>letters</dt><dd>not recorded for ' + ", ".join(contest_ref(m, rel) for m in members if m not in with_letters) + "</dd>")
    for m in members:
        dv = set_divisions(doc, m)
        if dv:
            d.append("<dt>divisions</dt><dd>" + (f"{contest_ref(m, rel)}: " if len(members) > 1 else "")
                     + ", ".join(f"{esc(n)} ({len(lm)} problems)" for n, lm in dv.items())
                     + (' <span class="small muted">— a problem in two divisions is one problem here; the # column gives its letter in each, in this order, – where it was not in that division</span>'
                        if len(dv) > 1 else ' <span class="small muted">— the # column gives the letter in this division; the other divisions\' letters are not known</span>') + "</dd>")
    d.append("</dl>")
    b += d
    probs = doc.get("problems") or []
    if probs:
        b.append(f'<h2 id="problems">Problems <span class="n">{len(probs)}' + (f" of {total}" if state == "partial" and total else "") + "</span></h2>")
        if len(members) > 1 and len(with_letters) > 1 and not same_letters:
            b.append('<p class="note">Several letters in the # column: the letter in ' + " / ".join(esc(m) for m in with_letters) + ".</p>")
        b.append(key_line(rel, "have"))
        rows = []
        for L, p in set_letter_cells(doc):
            private = p.get("status") == "private"
            rows.append(f'<tr><td class="letter">{esc(L)}</td><td>{R.U("member", problem_link(p["id"], rel, p["name"]), p["id"], p["id"], p["name"])}'
                        + (" " + chip("private", "n", "kept private after the contest; name and uuid are public") if private else "") + "</td>"
                        + ("<td></td><td></td>" if private else
                           f'<td class="nw">{problem_have_marks(p, doc)}</td><td>{problem_judge_links(p)}</td>') + "</tr>")
        b.append(table([th("#"), th("problem"), th("held"), th("online judge")], rows))
    else:
        b.append('<h2 id="problems">Problems</h2><p class="empty">The problems of this set are not listed by name yet'
                 + (f" — {total} problems." if total else ".") + "</p>")
    b.append(R.slot("member", "add a missing problem", tag="p"))
    # the letters contest by contest, only where they differ: contests that sat the set under the same letters need no table
    if len(with_letters) > 1 and not same_letters:
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
         f"<h1{R.at('problem', pid)}>{R.U('name', esc(p['name']), p['name'])}</h1>"]
    if private:
        b.append('<p class="status">' + chip("private", "n", "kept private after the contest; only the name and uuid are public") + "</p>")
    d = ['<dl class="facts">']
    apps = []
    for sid, cid, L in ent["apps"]:
        apps.append(R.U("appearance", (f"problem <b>{esc(L)}</b> of " if L else "") + contest_ref(cid, rel)
                        + (f' <span class="muted">· set {set_link(sid, rel)}</span>' if sid != cid else ""), (f"{L} of " if L else "") + cid, cid))
    d.append("<dt>appeared as</dt><dd>" + "<br>".join(apps) + " " + R.slot("appearance", "add a contest it appeared in") + "</dd>")
    if not private:
        seen, jl = set(), []
        for _s, r in rows:
            for j in r.get("judges") or []:
                if j["url"] not in seen:
                    seen.add(j["url"])
                    jl.append(R.U("judge_link", problem_judge_links({"judges": [j]}) + (f' <span class="muted">id {esc(j["id"])}</span>' if j.get("id") else "")
                                  + judge_closed_chip(j["judge"]) + f' <span class="small muted">· about {judge_link(j["judge"], rel)}</span>', j["url"], j["url"]))
        d.append("<dt>online judge</dt><dd>" + ("<br>".join(jl) if jl else '<span class="muted">none known</span>') + " " + R.slot("judge_link", "add a link") + "</dd>")
        have_row = next((r for _s, r in rows if "have" in r), None)
        hv = problem_have(have_row or p, first_doc)
        if have_row is not None:
            src = "recorded for this problem"
        elif any(v is not None for v in hv.values()):
            src = "from the set's holdings: only what is held for every problem of the set, or for none, is certain; the rest is not recorded per problem"
        else:
            src = "the problem archive's holdings for this set have not been entered yet"
        d.append(f"<dt>held</dt><dd>{problem_have_marks(have_row or p, first_doc)} <span class=\"small muted\">— {src}</span></dd>")
    repos = [(s, SETS[s]) for s, _r in rows if (SETS.get(s) or {}).get("repo")]
    if repos and not private:
        d.append("<dt>problem archive</dt><dd>" + "<br>".join(
            f'{repo_link(doc)} <span class="muted">(private) — the repository of problem set {set_link(s, rel)}; the problem is in it</span>' for s, doc in repos) + "</dd>")
    uuids = sorted({r["uuid"] for _s, r in rows if r.get("uuid")})
    pkg = problem_have(next((r for _s, r in rows if "have" in r), p), first_doc)["package"]
    d.append("<dt>UUID</dt><dd>" + (", ".join(f"<code>{esc(u)}</code>" for u in uuids) if uuids
                                    else '<span class="muted">none — the problem has no package in the archive</span>' if pkg is False
                                    else '<span class="muted">not recorded yet</span>') + "</dd>")
    shorts = sorted({r["short_name"] for _s, r in rows if r.get("short_name")})
    if shorts:
        d.append("<dt>short name</dt><dd>" + ", ".join(f"<code>{esc(x)}</code>" for x in shorts) + "</dd>")
    others = sorted({o for _s, r in rows for o in r.get("other_names") or []})
    if others:
        d.append("<dt>other titles</dt><dd>" + ", ".join(esc(x) for x in others)
                 + ' <span class="small muted">— the same problem under another title (an online judge\'s, or the statement\'s where the name here is the archive package\'s)</span></dd>')
    # `aliases` (ids merged into this one) are not shown: they are internal and only keep old addresses working
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
                    f'<td class="num" data-v="{total or ""}">{count}</td><td class="nw">{ {"complete": "listed", "partial": "partly listed", "none": "count only"}[state]}</td>'
                    f'<td class="nw">{held_marks(doc)}</td><td class="nw">{repo_link(doc)}</td>'
                    + "".join(f'<td class="hid" data-vs="{esc(toks(st, "missing" if st != "all" else ""))}"></td>'
                              for st in (COV.set_record(sid)[k] for k, *_ in CV.COMPONENTS)) + "</tr>")
    n_listed = sum(1 for d in SETS.values() if set_list_state(d) == "complete")
    shared = [sid for sid, d in SETS.items() if len(d["contests"]) > 1]
    return page("Problem sets", "<h1>Problem sets</h1>"
                f'<p class="intro">{num(len(SETS))} problem sets. Most belong to the one contest of the same id; '
                f'{len(shared)} were sat by several contests, such as the Latin America regional, where every site has the same problems '
                "(sort by <b>contests</b> to see them). "
                "<b>Held</b> is what we hold of the set, kind by kind, from the ICPC Problem Archive or from a source we hold a copy of; "
                "the set's page says which, and where the set was published and where it can be solved are on the contest page. "
                f"<b>Problems</b> is how many the contest had; <b>list</b> says whether we know them by name — <i>listed</i> (every one) for {num(n_listed)} sets, "
                "<i>partly listed</i> when only some are, <i>count only</i> when none are and only the number and the holdings are recorded.</p>"
                + key_line(rel, "held")
                + table([th("problem set"), th("contests", num=True, title="how many contests sat this set"), th("season", f=True), th("region", f=True),
                         th("problems", num=True), th("list", f="problem list"),
                         th("held"), th("archive repo")]
                        + [th(what, f=what, k=COMP_KEY[key], g=True, hid=True, o=STATE_ORDER) for key, _m, what in CV.COMPONENTS], rows, "flt"),
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
_SAME: dict = {}                     # checksum of a held copy -> source ids holding it (same_as)
SRC_ROLES: dict = defaultdict(set)   # source id -> roles it serves anywhere in the catalogue
SRC_SCOPE: dict = defaultdict(set)   # source id -> the part(s) of a contest it covers (`scope`), when not the whole
ROLE_PAGES = ["web", "scoreboard", "frozen_scoreboard", "standings", "rankings", "problemset", "problem", "editorial", "teams", "report"]


def index_sources(contests: dict) -> None:
    _SAME.clear()
    SRC_ROLES.clear()
    SRC_SCOPE.clear()
    for c in contests.values():
        for s in sources(c):
            k = lid(s["url"])
            SRC_ROLES[k].update(s["roles"])
            if s.get("scope"):
                SRC_SCOPE[k].add(s["scope"])


def role_link(r: str, rel: str) -> str:
    """A source type as a chip that opens the list of sources of that type."""
    return f'<a class="chip" href="{rel}source/by-role/{r}.html" title="every {esc(role_label(r))} source">{esc(role_label(r))}</a>'


def doc_roles(d: dict) -> list[str]:
    return sorted({r for c in d["cits"] for r in c["roles"]}, key=lambda r: RANK.get(r, 99))


def doc_entries(d: dict) -> list[tuple[dict, dict]]:
    """(contest, its catalogue entry for the address) for every contest that means this source."""
    out = []
    for c in d["cits"]:
        con = CONTESTS.get(c["contest"]) or next((x for x in NM if x["id"] == c["contest"]), None)
        e = find_source(con, d["url"]) if con else None
        if con and e:
            out.append((con, e))
    return out


def doc_label(d: dict, n: int = 90) -> str:
    return res_label(d["url"], d["time"], n)


FORMATS = (("application/pdf", "PDF"), ("text/html", "web page"), ("application/xhtml", "web page"), ("text/plain", "plain text"),
           ("application/postscript", "PostScript"), ("application/msword", "Word document"), ("wordprocessingml", "Word document"),
           ("application/rtf", "RTF"), ("text/rtf", "RTF"), ("gzip", "gzip archive"), ("zip", "zip archive"), ("x-tar", "tar archive"), ("rar", "rar archive"), ("octet-stream", "file of unrecorded type"),
           ("spreadsheet", "spreadsheet"), ("ms-excel", "spreadsheet"), ("text/csv", "CSV"), ("application/json", "JSON"), ("image/", "image"),
           ("text/xml", "XML"), ("application/xml", "XML"), ("x-tex", "TeX"), ("x-dvi", "DVI"))


def copy_format(x: dict | None) -> str:
    """What kind of file the copy that counts is: PDF, web page, a crawled website."""
    if not x:
        return ""
    if x["kind"] == "website":
        w = x["site"]
        n = w.get("html_pages") or w.get("pages") or 0
        return f"website, {n} pages" if n else "website"
    ct = (x["cap"].get("content_type") or "").lower()
    return next((lab for key, lab in FORMATS if key in ct), ct.split(";")[0])


def same_as(k: str) -> list[str]:
    """Other addresses of which we hold a copy that is byte for byte a copy we hold of this one:
    the same document at another address. Read off the copies' checksums, never stored."""
    if not _SAME:
        for o in RES.locs:
            for x in copies(o):
                cap = x.get("cap")
                if cap and cap.get("sha256") and (cap.get("size") or 0) >= 1000:
                    _SAME.setdefault(cap["sha256"], set()).add(o)
        _SAME[""] = set()
    out = set()
    for x in copies(k):
        cap = x.get("cap")
        if cap and cap.get("sha256"):
            out |= _SAME.get(cap["sha256"], set())
    return sorted(out - {k})


def place_rows(url: str, a: dict) -> list[str]:
    """The three places as table rows: the place, its answer (the same word and colour as its mark),
    what is known, and the link that opens it. No free text: every cell is a fixed word or a date."""
    live, wb, ours = a["live"], a["wb"], a["ours"]
    rows = []
    for (key, _lab, full), p in zip(AV_PLACES, (live, wb, ours)):
        if key == "live":
            what = p["tip"] + (f' (checked {p["checked"]})' if p.get("checked") else "")
            link = f'<a class="ext" href="{esc(url)}">open the address</a>'
        elif key == "wb":
            what = f'snapshot of {fmt_time(p["ts"])}' if p["s"] == "yes" and p.get("ts") else p["tip"]
            link = (f'<a class="ext" href="{esc(wayback_link(url, p["ts"]))}">open the snapshot</a>' if p.get("ts") and p["s"] in ("yes", "part")
                    else f'<a class="ext" href="{esc(wayback_link(url))}">look for snapshots</a>' if p["s"] == "pending" else "")
        else:
            what = (f'copy of {fmt_time(p["ts"])}' if p.get("ts") else "copy of an unknown time") if p["s"] == "yes" else p["tip"]
            link = open_copy(a["current"])
        rows.append(f'<tr><th>{esc(full[0].upper() + full[1:])}</th><td>{chip(p["word"], AV_CLS[p["s"]], p["tip"])}</td>'
                    f'<td class="small">{esc(what)}</td><td class="nw">{link}</td></tr>')
    return rows


def source_page(d: dict, rel: str) -> str:
    """One source: an address at a time. What it is, as linked facts (type, contest, problem set,
    problem), and the three places it can be found: the address now, the Wayback Machine, our
    archive. Of our copies only the one that counts is linked; the others stay in the archive."""
    k, url = d["k"], d["url"]
    cits = d["cits"]
    ents = doc_entries(d)
    a = avail(url, cits[0]["contest"] if cits else None)
    roles = doc_roles(d)
    at = f' <span class="at">(at {esc(fmt_time(d["time"]))})</span>' if d["time"] else ""
    b = [crumbs(f'<a href="{rel}source/index.html">Sources</a>', *[f'<a href="{rel}source/by-role/{r}.html">{esc(role_label(r))}</a>' for r in roles[:1]]),
         f"<h1{R.at('source', d['id'])}>{esc(url)}{at}</h1>",
         f'<div class="cc"><div class="cc-g"><b>Found at</b>{avail_pills(a)}</div> {help_link("sources", rel, "what the colours mean")}</div>',
         R.line("moved", "Not recorded as moved to another address")]

    # ---- what it is: facts, every one a link ----
    fx = ['<dl class="facts">']
    if roles:
        scopes = sorted({e["scope"] for _c, e in ents if e.get("scope")})
        judges = sorted({e["judge"] for _c, e in ents if e.get("judge")})
        fx.append("<dt>type</dt><dd>" + "".join(role_link(r, rel) for r in roles)
                  + "".join(chip(x, "sc", "this source covers one part of the contest, not all of it") for x in scopes)
                  + ("".join(f" on {judge_link(j, rel)}" for j in judges if j in JUDGES)) + "</dd>")
    else:
        fx.append('<dt>type</dt><dd class="muted">not recorded: no contest lists this address now</dd>')
    if cits:
        fx.append(f'<dt>contest{"s" if len(cits) > 1 else ""}</dt><dd>' + ", ".join(contest_ref(c["contest"], rel) for c in cits) + "</dd>")
    if {"problemset", "problem", "editorial"} & set(roles):
        sets = list(dict.fromkeys(s["id"] for s in (set_for(c) for c, _e in ents) if s))
        fx.append("<dt>problem set</dt><dd>" + (", ".join(set_link(s, rel) for s in sets) if sets else '<span class="muted">none recorded yet</span>') + "</dd>")
        probs = []
        for c, e in ents:
            if "problem" not in e["roles"]:
                continue
            x = source_problem(c, e, rel).strip()
            if x and "problem/" not in x:
                x += ' <span class="muted">not in the problem list yet</span>'
            if x:
                probs.append(x)
        if probs:
            fx.append("<dt>problem</dt><dd>" + ", ".join(dict.fromkeys(probs)) + "</dd>")
        held = {x for _c, e in ents for x in (e.get("contains") or [])}
        holds = [x for x, _w in CONTAINS if x in held]
        if holds:
            fx.append("<dt>holds</dt><dd>" + ", ".join(esc(dict(CONTAINS).get(x, x)) for x in holds) + "</dd>")
    fmt = copy_format(a["current"])
    if fmt:
        fx.append(f"<dt>format</dt><dd>{esc(fmt)}</dd>")
    others = [o for o in DOCS_OF[k] if o["id"] != d["id"]]
    if others:
        fx.append('<dt>same address, other times</dt><dd>' + "<br>".join(
            f'<a href="{rel}source/{o["id"]}/index.html">{esc(fmt_time(o["time"]) if o["time"] else "as it is now")}</a> <span class="muted">·</span> '
            + ", ".join(contest_ref(c["contest"], rel) for c in o["cits"][:4]) + (f' <span class="muted">+{len(o["cits"]) - 4}</span>' if len(o["cits"]) > 4 else "")
            for o in others) + "</dd>")
    same = same_as(k)
    if same:
        fx.append('<dt title="a copy we hold of each is byte for byte the same">same document at</dt><dd>' + "<br>".join(
            link_source(RES.locs[o]["url"], rel, RES.locs[o]["url"][:110]) for o in same[:12])
            + (f' <span class="muted">and {len(same) - 12} more</span>' if len(same) > 12 else "") + "</dd>")
    fx.append("</dl>")
    b += fx

    b.append(source_descriptions.block(url, cits, rel, contest_ref, help_link))

    # ---- the one place the address, the Wayback snapshot and our copy are opened ----
    b.append('<h2 id="where">Where to find it</h2>'
             '<div class="tw"><table class="where nosort"><tbody>' + "\n".join(place_rows(url, a)) + "</tbody></table></div>")
    return page(host_label(url, 60), "\n".join(b), rel, "source/index.html")


def cited_docs() -> dict:
    """The sources: the addresses-at-a-time that a contest cites. An address in the resource graph that
    no contest cites (the seed of a crawl under another spelling, a mirror that was dropped, an address
    that was only ever probed) still has its page, for old links, but is not a source and is not counted
    or listed as one."""
    return {sid: d for sid, d in DOCS.items() if d["cits"]}


def source_list(rel: str, role: str | None = None) -> str:
    """source/index.html (every source) and source/by-role/<role>.html (one type): the same
    page, the same columns, the same filters — the type pages are that table cut down."""
    docs = cited_docs()
    counts = Counter(r for d in docs.values() for r in doc_roles(d))
    here = "../" if role else ""
    tabs = ["<span>" + ("<b>all</b>" if not role else f'<a href="{here}index.html">all</a>') + f' <span class="muted small">{num(len(docs))}</span></span>']
    for r in ROLE_PAGES:
        lab = esc(role_label(r))
        tabs.append("<span>" + (f"<b>{lab}</b>" if r == role else f'<a href="{here}by-role/{r}.html">{lab}</a>') + f' <span class="muted small">{num(counts[r])}</span></span>')
    rows = []
    for sid, d in docs.items():
        roles = doc_roles(d)
        if role and role not in roles:
            continue
        cs = [c["contest"] for c in d["cits"]]
        a = avail(d["url"], cs[0] if cs else None)
        rows.append(f'<tr><td class="url"><a href="{rel}source/{sid}/index.html">{esc(doc_label(d))}</a></td>'
                    f'<td data-vs="{esc("|".join(role_label(r) for r in roles))}" class="small">{esc(", ".join(role_label(r) for r in roles))}</td>'
                    f'<td data-v="{len(cs)}" class="small">{", ".join(contest_ref(c, rel) for c in cs[:3])}{" +" + str(len(cs) - 3) if len(cs) > 3 else ""}</td>'
                    f'<td class="nw" data-vs="{esc(avail_values(a))}">{avail_marks(a)}</td>'
                    f'<td class="nw small">{esc(a["live"].get("checked") or "")}</td></tr>')
    title = f"{role_label(role).capitalize()} sources" if role else "Sources"
    return page(title, f"<h1>{esc(title)}</h1>"
                f'<p class="intro">{"Sources of this type" if role else "Every source the catalogue knows"}: {num(len(rows))}. '
                "A <b>source</b> is an address at a point in time: what the address served for a contest. It can be found in up to three places — "
                "at its address now, in the Wayback Machine, in our archive — and every list shows the three together, in the same colours. "
                "The address, the snapshot and our copy are opened from the source's own page.</p>"
                '<p class="tabs">' + " ".join(tabs) + "</p>" + key_line(rel, "available")
                + table([th("source"), th("type", f=True), th("contests"), AVAIL_TH, th("address checked")], rows, "flt"),
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
        for s in judge_sources(c):
            pages[s.get("judge") or "judge"].append((c["id"], s))
    return probs, pages


def judge_status(j: dict) -> str:
    st = j.get("status", "")
    return chip(st + (f" {j['closed']}" if j.get("closed") else ""), {"active": "h", "closed": "n"}.get(st, "l"),
                "its pages survive only in Wayback snapshots taken before the closing date" if st == "closed" else None)


def judge_page(jid: str, j: dict, probs: set, pages: list, rel: str) -> str:
    ncon = len({c for c, _s in pages})
    b = [crumbs(f'<a href="{rel}judge/index.html">Online judges</a>'), f'<h1{R.at("judge", jid)}>{judge_mark(jid)}{R.U("name", esc(j.get("name") or jid), j.get("name") or "")}</h1>',
         '<p class="status">' + R.U("status", judge_status(j), (j.get("status", "") + " " + str(j.get("closed") or "")).strip()) + "</p>",
         f'<div class="nums"><div><b>{num(ncon)}</b><span><a href="#contests">contests</a></span></div>'
         f'<div><b>{num(len(probs))}</b><span><a href="#problems">problems</a></span></div></div>',
         '<dl class="facts">', "<dt>site</dt><dd>" + R.U("url", f'<a class="ext" href="{esc(wayback_link(j["url"]) if j.get("status") == "closed" else j["url"])}">{esc(j["url"])}</a>', j["url"]) + "</dd>"]
    offers = [w for w in ("statements", "submissions") if j.get(w)]
    b.append('<dt class="rvo">offers</dt><dd class="rvo">' + R.U("offers", " and ".join(offers) or "neither", "+".join(offers) or "neither") + "</dd>")
    for key, lab in (("contest_url", "contest address"), ("problem_url", "problem address")):
        if j.get(key):
            b.append(f"<dt>{lab}</dt><dd><code>{esc(j[key])}</code></dd>")
    b.append("</dl>")
    nps = sum(1 for _c, s in pages if "problemset" in s["roles"])
    b.append(f'<h2 id="contests">Contests <span class="n">{ncon}</span></h2>'
             '<p class="note">Contests that have a page on this online judge: the page of its problem set, or a problem\'s own page or statement that we hold a copy of'
             + (f" — {len(pages)} pages: {nps} problem-set pages, {len(pages) - nps} problem pages." if len(pages) != ncon else ".") + "</p>")
    if pages:
        rows = []
        for cid, s in sorted(pages, key=lambda t: (t[0], t[1]["url"])):
            c = CONTESTS.get(cid) or {}
            rows.append(f'<tr><td class="nw">{contest_ref(cid, rel)}</td><td class="nw" data-v="{esc(c.get("date", ""))}">{link_date(c.get("date"), rel)}</td>'
                        f'<td class="nw">{role_chip(primary_role(s))}{source_problem(c, s, rel)}</td>'
                        f'<td class="url">{link_source(s["url"], rel, res_label(s["url"], source_time(s, cid), 100), s.get("as_of"), cid)}</td>'
                        + avail_cell(s["url"], cid, s) + "</tr>")
        b.append(table([th("contest"), th("date"), th("type", f=True), th("source"), AVAIL_TH], rows))
    else:
        b.append('<p class="empty">No contest has a page on this online judge recorded.</p>')
    b.append(f'<h2 id="problems">Problems <span class="n">{len(probs)}</span></h2>'
             + ('<p class="note">Problems that link to this online judge.</p>' if probs else ""))
    if probs:
        rows = []
        for pid in sorted(probs, key=lambda x: problem_name(x).lower()):
            r = PROBLEMS[pid]["rows"][0][1]
            jl = [jj for _s, rr in PROBLEMS[pid]["rows"] for jj in rr.get("judges") or [] if jj["judge"] == jid]
            jl = list({jj["url"]: jj for jj in jl}.values())
            rows.append(f'<tr><td>{problem_link(pid, rel, r["name"])}</td>'
                        f'<td class="nw">{problem_judge_links({"judges": jl}, by_id=True)}</td>'
                        f'<td>{", ".join(set_link(s, rel) for s, _r in PROBLEMS[pid]["rows"])}</td></tr>')
        b.append(table([th("problem"), th("on this online judge"), th("problem set")], rows))
    else:
        b.append('<p class="empty">No problem links to this online judge yet.</p>')
    return page(j.get("name") or jid, "\n".join(b), rel, "judge/index.html")


def judge_index(probs: dict, pages: dict, rel: str) -> str:
    rows = []
    for jid, j in JUDGES.items():
        rows.append(f'<tr><td class="name">{judge_mark(jid)}{judge_link(jid, rel)}<span class="sub">{esc(re.sub(r"^https?://", "", j["url"]).rstrip("/"))}</span></td>'
                    f'<td class="nw" data-v="{esc(j.get("status", ""))}">{judge_status(j)}</td>'
                    f'<td class="num">{len({c for c, _s in pages.get(jid, [])})}</td><td class="num">{len(probs.get(jid, ()))}</td></tr>')
    unknown = [x for x in sorted(set(probs) | set(pages)) if x not in JUDGES]
    return page("Online judges", "<h1>Online judges</h1>"
                f'<p class="intro">{len(JUDGES)} online judges where ICPC problems can be solved, or could. <b>Contests</b> counts contests with a page on it; '
                "<b>problems</b> counts problems that link to it. An online judge that has closed survives only in Wayback snapshots taken before it shut down.</p>"
                + table([th("online judge"), th("status", f=True), th("contests", num=True), th("problems", num=True)], rows)
                + ('<p class="note">Online judges used but not registered: ' + ", ".join(esc(x) for x in unknown) + "</p>" if unknown else ""),
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
         f"<h1{R.at('location', nid)}>{R.U('name', esc(n['name']), n['name'])}</h1>", f'<p class="lede">{R.U("type", esc(n["type"].capitalize()), n["type"])}'
         + (" in " + R.U("parent", ", ".join(esc(x["name"]) for x in chain), n.get("parent") or "") if chain else "") + "</p>"]
    st = content_counts(cs)
    series = Counter(SERIES_OF[c["id"]] for c in cs)
    b.append(group_nums(cs, rel, {"loc": nid}, (f'<div class="pt"><b>{ys[0]}–{ys[1]}</b><span class="tl-l">first to latest</span></div>' if ys else "")
                        + f'<div class="pt"><b>{len(series)}</b><span class="tl-l">series</span></div>'))
    d = ['<dl class="facts">']
    d.append(("<dt>also written</dt><dd>" if n.get("aliases") else '<dt class="rvo">also written</dt><dd class="rvo">')
             + ", ".join(R.U("aliases", esc(a), a, a) for a in n.get("aliases") or []) + " " + R.slot("aliases", "add another name") + "</dd>")
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
    d.append(f'<dt>location id</dt><dd><code>{esc(nid)}</code></dd></dl>')
    b += d
    if st["n"] >= 3:   # with fewer, the contest table below says it all
        b.append('<p class="tabs">Jump to: <a href="#coverage">coverage</a> <a href="#where">season by season</a>'
                 + (' <a href="#places">places</a>' if LOC_KIDS.get(nid) else "") + ' <a href="#contests">contests</a></p>')
        b.append(coverage_section(cs, rel, {"loc": nid}, "the contests held here", "Season by season",
                                  "A column per season, a row per question; each cell is that season's contests here split by answer, held at the bottom. "
                                  "A cell opens the contests of that season that are missing it.", season_strips([c for c in cs if did_run(c)], rel, {"loc": nid})))
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
                     + group_cells(cs, rel, {"loc": nid}) + "</tr>")
    arows = [loc_row(nid, rel) for nid in sorted(LOC, key=lambda k: (-len(LOC_SUB.get(k, ())), LOC[k]["name"]))]
    return page("Locations", "<h1>Locations</h1>"
                f'<p class="intro">Where contests were held, as one tree: {types["country"]} countries, {types["region"]} states and provinces, '
                f'{num(types["city"])} cities and {num(types["institution"])} institutions. {num(n_placed)} of the {num(len(ran))} contests that ran are placed in it '
                f"({pct(n_placed, len(ran))}%); the rest are known only by a line of text, or not at all. A contest counts for the place it was held and for everything that place is in.</p>"
                f'<div class="nums"><div><b>{types["country"]}</b><span>countries</span></div><div><b>{types["region"]}</b><span>states and provinces</span></div>'
                f'<div><b>{num(types["city"])}</b><span>cities</span></div><div><b>{num(types["institution"])}</b><span>institutions</span></div></div>'
                f'<p class="tabs"><a href="#countries">Countries</a> <a href="#all">Every location</a></p>'
                f'<h2 id="countries">Countries <span class="n">{len(countries)}</span></h2>'
                + table([th("country"), th("contests", num=True), th("years"), th("cities", num=True), th("institutions", num=True), th("most often in")] + group_heads(), crows)
                + f'<h2 id="all">Every location <span class="n">{num(len(LOC))}</span></h2>'
                + table([th("location"), th("type", f=True), th("in"), th("country", f=True), th("contests", num=True, title="contests held here or anywhere inside"),
                         th("exactly here", num=True, title="contests whose site is this very place"), th("first"), th("latest"), th("contains")], arows, "flt"),
                rel, "location/index.html")



# ---- coverage ----
# One coverage record per contest (tools/coverage.py). Every number on these pages is the size of a
# SHARE: the contests that ran and pass one filter of the contest list. The number and the list
# behind its link are worked out from the same filter values, so they cannot disagree
# (tools/check_coverage_links.py follows every counted link and checks).
FILTER_VALUES = {
    "results": results_value, "fetch": fetch_value, "also": also_value, "problems": problems_value,
    "website": website_value, "pmeta": pmeta_value, "meta": meta_value,
    **{COMP_KEY[key]: (lambda key: lambda c: component_value(c, key))(key) for key, *_ in CV.COMPONENTS},
}
_TOK: dict = {}


def in_share(c: dict, f: dict) -> bool:
    """Does this contest pass the filter `f` ({filter name: value}) of the contest list?"""
    t = _TOK.setdefault(c["id"], {})
    for k, v in f.items():
        if k not in t:
            t[k] = set(FILTER_VALUES[k](c).split("|"))
        if v not in t[k]:
            return False
    return True


def share(cs: list[dict], f: dict) -> int:
    return sum(1 for c in cs if in_share(c, f))


# ---- facets on a page: one colour vocabulary, one filter per answer ----
FKEYS = [f[0] for f in CV.FACETS]
GROUPS = list(dict.fromkeys(f[2] for f in CV.FACETS))   # Results, Problems, Problem metadata, Website, Metadata
_PM = {k: lab for k, lab in CV.PMETA}
_MT = {k: lab for k, lab in CV.META}
WEB_TOKEN = {"have": "have", "no copy": "missing: no copy", "no address": "missing: no address", "confirmed none": "confirmed none"}
# what an answer looks like: q4 held ... q1 a little held (shades of one green), ql a link we hold no copy of,
# q0 nothing (a hole), qu not recorded (hatched), qx there is none to have (not a hole)
Q_WORD = {"q4": "held", "q3": "held", "q2": "partly held", "q1": "partly held", "ql": "known, no copy", "q0": "missing", "qu": "not recorded", "qx": "none exists"}
Q_WORD_RECORDED = {"q4": "recorded", "q2": "partly recorded", "q1": "partly recorded", "ql": "a source is known, nothing recorded"}


def q_word(key: str, cls: str) -> str:
    """The word for an answer's colour in a pill's hover text: metadata is recorded, not held (GROUP_NOTE),
    and a lower rung of the results ladder is a lesser result, not a part of one (COV_KEY)."""
    if CV.FACET[key][2] in ("Problem metadata", "Contest metadata"):
        return Q_WORD_RECORDED.get(cls, Q_WORD[cls])
    if key == "results" and cls in ("q3", "q2", "q1"):
        return "a lesser result"
    return Q_WORD[cls]
_ST: dict = {}


def facet_q(key: str) -> tuple:
    if key == "results":
        return ("q4", "q3", "q2", "q1", "q0")
    if key == "list":
        return ("q4", "q2", "q1", "ql", "q0")
    if key in COMP_KEY:
        return ("q4", "q2", "ql", "q0", "qu")
    if key == "website":
        return ("q4", "ql", "q0", "qx")
    return ("q4", "q2", "q0") if key in _PM else ("q4", "q0", "qx")


def facet_filter(key: str, s: str) -> dict:
    """The filter of the contest list that selects the contests whose answer to `key` is `s`."""
    if key == "results":
        return {"results": s}
    if key == "list":
        return {"problems": s}
    if key in COMP_KEY:
        return {COMP_KEY[key]: s}
    if key == "website":
        return {"website": WEB_TOKEN[s]}
    return {"pmeta": f"{_PM[key]}: {s}"} if key in _PM else {"meta": f"{_MT[key]}: {s}"}


def facet_missing(key: str) -> dict:
    """The worklist of a facet: the contests that do not have its best answer (and could)."""
    if key == "results":
        return {"results": "no scoreboard"}
    if key == "list":
        return {"problems": "not listed"}
    if key in COMP_KEY:
        return {COMP_KEY[key]: "missing"}
    if key == "website":
        return {"website": "missing"}
    return {"pmeta": f"{_PM[key]}: missing"} if key in _PM else {"meta": f"{_MT[key]}: missing"}


def facet_anchor(key: str) -> str:
    """Where on a contest's page a facet is shown."""
    g = CV.FACET[key][2]
    return {"Results": "#results", "Problems": "#problems", "Problem metadata": "#problems", "Website": "#website"}.get(g, "")


def st(c: dict) -> dict:
    """{facet: answer} of a contest."""
    if c["id"] not in _ST:
        _ST[c["id"]] = CV.states(rec(c))
    return _ST[c["id"]]


def good(c: dict, key: str) -> bool:
    return st(c)[key] == CV.FACET[key][3][0]


# ---- the stacked bar: one facet of a set of contests ----
def sbar(cs: list[dict], key: str, rel: str, scope: dict | None, cls: str = "", inner: bool = True) -> str:
    """One facet as a bar split by answer, best first. Every segment opens its contests
    (`scope`: what picks these contests in the contest list; None = no links)."""
    n = len(cs)
    cnt = Counter(st(c)[key] for c in cs)
    lab = CV.FACET[key][1]
    segs = []
    for s, q in zip(CV.FACET[key][3], facet_q(key)):
        k = cnt[s]
        if not k:
            continue
        tip = f"{lab}: {s} — {num(k)} of {num(n)} ({pct(k, n)}%)"
        txt = num(k) if inner and k / n >= .04 * len(num(k)) + .03 else ""   # only where the segment is wide enough for it
        if scope is None:
            segs.append(f'<i class="{q}" style="flex:{k}" title="{esc(tip)}">{txt}</i>')
        else:
            segs.append(f'<a class="{q}" style="flex:{k}" data-n="{k}" href="{esc(flt_href(rel, {**RAN, **scope, **facet_filter(key, s)}))}" title="{esc(tip)}">{txt}</a>')
    return f'<span class="sb{" " + cls if cls else ""}">' + "".join(segs) + "</span>"


def schips(cs: list[dict], key: str, rel: str, scope: dict | None) -> str:
    """The legend of a bar: a swatch, the answer and its count; each one opens its contests."""
    cnt = Counter(st(c)[key] for c in cs)
    out = []
    for s, q in zip(CV.FACET[key][3], facet_q(key)):
        k = cnt[s]
        if not k:
            continue
        body = f'<i class="sw {q}"></i>{esc(s)} <b>{num(k)}</b>'
        out.append(f'<span class="ch">{body}</span>' if scope is None else
                   f'<a class="ch" data-n="{k}" href="{esc(flt_href(rel, {**RAN, **scope, **facet_filter(key, s)}))}">{body}</a>')
    return '<div class="fc">' + "".join(out) + "</div>"


RESULT_NOTES = (   # said about a contest's results beside their level: (label, filter, what it means)
    ("a better result is known, not held", {"fetch": "any"}, "a source gives a higher level than the one we hold, and we have no copy of it"),
    ("frozen scoreboard held", {"also": "frozen scoreboard: held"}, "the scoreboard as it stood at the freeze: kept beside the result, it does not say how the contest ended"),
    ("frozen scoreboard, link only", {"also": "frozen scoreboard: link only"}, "a frozen scoreboard is known at an address; we hold no copy"),
    ("partial result", {"also": "partial result"}, "the result we hold covers only a part of the contest: one division, the top places"),
    ("a source is lost", {"also": "lost source"}, "a result or website source gone from its address, not in the Wayback Machine, no copy here"),
)


# the panel's three columns: results, website and contest metadata; what is recorded about the problems; what is held of them
PANEL_COLS = (("Results", "Website", "Contest metadata"), ("Problem metadata",), ("Problems",))
GROUP_NOTE = {
    "Problem metadata": "Contests, by what the catalogue records about their problems: the list itself, then names, letters, short names and UUIDs "
                        "(<b>all</b> = for every problem of the contest). Recorded is not the same as held: we can hold a statement without its problems being listed yet.",
    "Problems": "Contests, by what we hold of their problems — not a count of problems. <b>all</b> = for every problem of the contest, <b>some</b> = for part of them.",
}


def coverage_panel(cs: list[dict], rel: str, scope: dict | None) -> str:
    """What we hold of a set of contests: every facet as a bar, every answer a link to its contests.
    The same panel wherever contests are counted: the archive, a season, a series, a location."""
    cs = [c for c in cs if did_run(c)]
    n = len(cs)
    if not n:
        return '<p class="empty">No contest here has run yet.</p>'
    cards = {}
    for g in GROUPS:
        keys = [f[0] for f in CV.FACETS if f[2] == g]
        rows = [f'<p class="note gn">{GROUP_NOTE[g]}</p>'] if g in GROUP_NOTE else []
        for key in keys:
            lab = CV.FACET[key][1]
            k = sum(1 for c in cs if good(c, key))
            rows.append('<div class="fr">' + (f'<span class="fl">{esc(lab)}</span>' if len(keys) > 1 else "")
                        + sbar(cs, key, rel, scope)
                        + f'<span class="fp" title="{esc(lab)}: {esc(CV.FACET[key][3][0])} for {num(k)} of {num(n)} contests">{pct(k, n)}%</span></div>'
                        + schips(cs, key, rel, scope))
        if g == "Results":
            notes = []
            for lab, f, tip in RESULT_NOTES:
                k = share(cs, f)
                if k:
                    notes.append(f'<span class="ch" title="{esc(tip)}">{esc(lab)} <b>{num(k)}</b></span>' if scope is None else
                                 f'<a class="ch" data-n="{k}" href="{esc(flt_href(rel, {**RAN, **scope, **f}))}" title="{esc(tip)}">{esc(lab)} <b>{num(k)}</b></a>')
            if notes:
                rows.append('<div class="fc fn">' + "".join(notes) + "</div>")
        cards[g] = f'<div class="cp-g cp-{len(keys)}"><h3>{esc(g)}</h3>' + "".join(rows) + "</div>"
    return '<div class="cp">' + "".join('<div class="cp-c">' + "".join(cards[g] for g in col) + "</div>" for col in PANEL_COLS) + "</div>"


def coverage_section(cs: list[dict], rel: str, scope: dict | None, what: str, where_title: str, where_note: str, where_html: str,
                     title: str = "Coverage", hid: str = "coverage") -> str:
    """The coverage of a group of contests, the same wherever it is shown and always in this order:
    the key, the panel (what we hold, counted), then where it is missing along the group's own axis
    (an archive or a location season by season, a series edition by edition, a season contest by contest)."""
    return (f'<h2 id="{hid}">{title}</h2><p class="note">What we hold of {what}. One bar per question, split by answer; '
            "every segment and every label under a bar opens those contests as a list.</p>" + COV_KEY + coverage_panel(cs, rel, scope)
            + f'<h3 id="where">{where_title}</h3><p class="note">{where_note} White is a hole.</p>' + where_html)


COV_KEY = ('<p class="key ck"><b>Every bar counts contests.</b> <i class="sw q4"></i> held <i class="sw q3"></i><i class="sw q2 j"></i><i class="sw q1 j"></i> partly held, or a lesser result '
           '<i class="sw ql"></i> known at an address, no copy <i class="sw q0"></i> missing <i class="sw qu"></i> a source is known, not what it holds '
           '<i class="sw qx"></i> none exists (not missing)</p>')


# ---- a contest's own coverage: what we hold of it, what is wanted ----
WANT_WORD = {"results": "a scoreboard", "list": "the list of problems", "statement": "the statements", "data": "the test data", "solutions": "solutions",
             "package": "complete packages", "editorial": "an editorial", "names": "the problem names", "letters": "the problem letters",
             "short_names": "short names", "uuids": "UUIDs", "website": "a copy of the website", "name": "the contest's name", "date": "the full date",
             "location": "the location", "cms": "the CMS id"}


def contest_coverage(c: dict, rel: str) -> str:
    """The coverage card of one contest: every facet as a pill in the colour of its answer, then what is wanted."""
    if not did_run(c):
        return ""
    s, r = st(c), rec(c)
    groups, wanted = [], []
    for g in GROUPS:
        pills = []
        for key in (f[0] for f in CV.FACETS if f[2] == g):
            lab, sts, q = CV.FACET[key][1], CV.FACET[key][3], facet_q(key)
            a = s[key]
            cls = q[sts.index(a)]
            text = a if key in ("results", "website") else (lab if a == sts[0] else f"{lab}: {a}")
            if key == "website":
                text = {"have": "held", "no copy": "address known, no copy", "no address": "no address known", "confirmed none": "had none"}[a]
            pills.append(f'<a class="pl {cls}" href="{facet_anchor(key) or "#"}" title="{esc(lab)}: {esc(a)} — {q_word(key, cls)}">{esc(text)}</a>')
            if cls not in ("q4", "qx") and not (key in _PM and s["list"] in ("source only", "none")):
                wanted.append("the website (no address known)" if key == "website" and a == "no address"
                              else WANT_WORD[key] + (f" (we hold {a})" if key == "results" and a != "none" else ""))
        if g == "Results":
            if r["fetch"]:
                pills.append(f'<a class="pl ql" href="#results" title="{TIER_LABEL[r["fetch"]]}: a better result than the one we hold is known at an address; we hold no copy of it yet">{TIER_LABEL[r["fetch"]]}: link only</a>')
            if r["frozen"]:
                pills.append(f'<a class="pl {"q4" if r["frozen"] == "held" else "ql"}" href="#results" title="the scoreboard as it stood at the freeze; '
                             f'kept beside the result, not counted as one">frozen scoreboard{"" if r["frozen"] == "held" else ": link only"}</a>')
            if r["partial"]:
                pills.append('<a class="pl q2" href="#results" title="the result we hold covers only a part of the contest: one division, the top places">partial</a>')
        groups.append(f'<div class="cc-g"><b>{esc(g)}</b>' + "".join(pills) + "</div>")
    want = ('<p class="cc-w"><b>Wanted</b> ' + ", ".join(esc(w) for w in wanted) + f'. <a href="{rel}about.html#contribute">Have any of it?</a></p>' if wanted
            else '<p class="cc-w"><b>Complete</b> — we hold everything we track for this contest.</p>')
    return '<div class="cc">' + "".join(groups) + want.replace("</p>", " " + help_link("status", rel, "what the colours mean") + "</p>") + "</div>"


# ---- matrices: where exactly something is missing ----
def _mcell(c: dict, key: str, rel: str) -> str:
    if not did_run(c):
        return '<td><i class="mc mu" title="upcoming"></i></td>'
    sts, a = CV.FACET[key][3], st(c)[key]
    q = facet_q(key)[sts.index(a)]
    return (f'<td><a class="mc {q}" href="{rel}contest/{esc(c["id"])}.html{facet_anchor(key)}" '
            f'title="{esc(c["id"])} — {esc(CV.FACET[key][1])}: {esc(a)}"></a></td>')


def edition_matrix(cs: list[dict], rel: str, scope: dict) -> str:
    """A series through time: a column per edition (oldest first), a row per facet. Holes are white.
    A square opens the contest; a row's label opens the editions that are missing it."""
    cs = sorted(cs, key=lambda c: (int(c["id"].rsplit("-", 1)[1]), c["id"]))
    ran_cs = [c for c in cs if did_run(c)]
    head = '<tr><th></th>' + "".join(f'<th class="vy"><a href="{rel}contest/{esc(c["id"])}.html" title="{esc(c["id"])}">{esc(c["id"].rsplit("-", 1)[1])}</a></th>' for c in cs) + "<th></th></tr>"
    body = []
    for g in GROUPS:
        body.append(f'<tr class="mg"><td colspan="{len(cs) + 2}">{esc(g)}</td></tr>')
        for key in (f[0] for f in CV.FACETS if f[2] == g):
            miss = share(ran_cs, facet_missing(key))
            body.append(f'<tr><td class="ml">{esc(CV.FACET[key][1])}</td>' + "".join(_mcell(c, key, rel) for c in cs)
                        + '<td class="mn">' + (n_link(miss, rel, {**scope, **facet_missing(key)}, f"{miss} missing") if miss else '<span class="muted">complete</span>') + "</td></tr>")
    return f'<div class="tw"><table class="mx nosort"><thead>{head}</thead><tbody>' + "".join(body) + "</tbody></table></div>"


def contest_matrix(groups: list[tuple[str, list[dict]]], rel: str) -> str:
    """Many contests of one time (a season): a row per contest, a column per facet."""
    heads = '<tr><th></th>' + "".join(
        f'<th class="vy{" gs" if i and CV.FACETS[i][2] != CV.FACETS[i - 1][2] else ""}">{esc(f[1])}</th>' for i, f in enumerate(CV.FACETS)) + "</tr>"
    body = []
    for name, cs in groups:
        if not cs:
            continue
        body.append(f'<tr class="mg"><td colspan="{len(CV.FACETS) + 1}">{esc(name)}</td></tr>')
        for c in cs:
            cells = "".join(_mcell(c, f[0], rel).replace("<td>", '<td class="gs">', 1) if i and CV.FACETS[i][2] != CV.FACETS[i - 1][2] else _mcell(c, f[0], rel)
                            for i, f in enumerate(CV.FACETS))
            body.append(f'<tr><td class="ml">{link_contest(c["id"], rel)}</td>{cells}</tr>')
    return f'<div class="tw"><table class="mx nosort">{"<thead>" + heads + "</thead>"}<tbody>' + "".join(body) + "</tbody></table></div>"


def season_strips(cs: list[dict], rel: str, scope: dict) -> str:
    """The archive through time: a row per facet, a column per season, each cell that season's contests
    split by answer (held at the bottom). A cell opens the contests of that season that are missing it."""
    by_s = defaultdict(list)
    for c in cs:
        by_s[season_of(c)].append(c)
    seasons = sorted(by_s)
    head = '<tr><th></th>' + "".join(f'<th class="vy">{link_season(s, rel, str(s)) if s in BY_SEASON else s}</th>' for s in seasons) + "</tr>"
    body = []
    for g in GROUPS:
        body.append(f'<tr class="mg"><td colspan="{len(seasons) + 1}">{esc(g)}</td></tr>')
        for key in (f[0] for f in CV.FACETS if f[2] == g):
            sts, q = CV.FACET[key][3], facet_q(key)
            cells = []
            for s in seasons:
                cnt = Counter(st(c)[key] for c in by_s[s])
                n = len(by_s[s])
                miss = share(by_s[s], facet_missing(key))
                tip = f"{s - 1}–{s} · {CV.FACET[key][1]}: " + ", ".join(f"{a} {cnt[a]}" for a in sts if cnt[a]) + (f" — open the {miss} missing" if miss else " — complete")
                segs = "".join(f'<i class="{qq}" style="flex:{cnt[a]}"></i>' for a, qq in zip(sts, q) if cnt[a])
                f = {**scope, "season": s, **(facet_missing(key) if miss else {})}
                cells.append(f'<td><a class="tc" data-n="{miss or n}" href="{esc(flt_href(rel, {**RAN, **f}))}" title="{esc(tip)}">{segs}</a></td>')
            body.append(f'<tr><td class="ml">{esc(CV.FACET[key][1])}</td>' + "".join(cells) + "</tr>")
    return f'<div class="tw"><table class="mx tl nosort"><thead>{head}</thead><tbody>' + "".join(body) + "</tbody></table></div>"


GROUP_FACETS = ("results", "statement", "data", "solutions", "package", "editorial", "website", "date", "location")


def group_bars(label: str, rows: list[tuple[str, list[dict], dict]], cls: str = "", extra_heads: list[str] | None = None) -> str:
    """Groups of contests side by side (regions, series): a row per group, a small bar per facet.
    Sorts on the share held; every segment opens its contests."""
    heads = [th(label)] + (extra_heads or []) + [th("contests", num=True)] + group_heads(GROUP_FACETS)
    body = [f'<tr>{lab}<td class="num">{n_link(len(cs), "", scope)}</td>{group_cells(cs, "", scope, GROUP_FACETS)}</tr>' for lab, cs, scope in rows]
    return table(heads, body, cls)


# ---- the headline measures ----
MEASURES = (   # every one counts contests: (label, the list of those that have it, the list of those that do not)
    ("with a scoreboard", {"results": "scoreboard"}, {"results": "no scoreboard"}),
    ("with any result", {"results": "any result"}, {"results": "none"}),
    ("with every statement", {"statements": "all"}, {"statements": "missing"}),
    ("with every package", {"packages": "all"}, {"packages": "missing"}),
    ("with the website", {"website": "have"}, {"website": "missing"}),
    ("with the full date", {"meta": "full date: have"}, {"meta": "full date: missing"}),
)


def headline_tiles(cs: list[dict], rel: str, scope: dict | None) -> str:
    """The six headline numbers of a set of contests, each with two links: the contests that
    have it, and the ones that do not."""
    cs = [c for c in cs if did_run(c)]
    n = len(cs)
    tiles = []
    for lab, have, miss in MEASURES:
        k, m = share(cs, have), share(cs, miss)
        tiles.append(f'<div class="pt"><b>{n_link(k, rel, None if scope is None else {**scope, **have})} <i class="pc">{pct(k, n)}%</i></b>'
                     f'<span class="tl-l">{esc(lab)}</span><span class="meter"><i style="width:{pct(k, n)}%"></i></span>'
                     + (f'<span class="tm">{n_link(m, rel, None if scope is None else {**scope, **miss}, f"{num(m)} missing")}</span>' if m else "") + "</div>")
    return "".join(tiles)


def group_nums(cs: list[dict], rel: str, scope: dict | None, extra: str = "") -> str:
    """The numbers strip of a group of contests, the same wherever contests are counted (the archive, a
    season, a series, a location): how many ran, then the six headline counts, each with its share and
    the list of what is missing. `scope`: what picks these contests in the contest list; `extra`: more tiles."""
    st = content_counts(cs)
    first = (f'<div class="pt"><b>{n_link(st["n"], rel, scope)}</b><span class="tl-l">contests ran'
             + (f' <span class="muted">+{st["upcoming"]} upcoming</span>' if st["upcoming"] else "") + "</span></div>")
    return '<div class="pts">' + first + headline_tiles(cs, rel, scope) + extra + "</div>"


def coverage_page(series_docs: dict, contests: dict) -> str:
    cs = [c for c in contests.values() if did_run(c)]
    n = len(cs)
    b = ["<h1>Coverage</h1>",
         f'<p class="intro">What we hold of the {n_link(n, "", {})} contests that ran: results, problems, website and contest metadata. '
         "<b>Held</b> always means we hold a copy; an address we only know is a link, and is shown as one. "
         "<b>Everything here is a link</b>: a segment of a bar, a label under it, a square, a number all open the contest list filtered to exactly those contests, "
         "where the filters can be combined further.</p>",
         group_nums(cs, "", {}),
         '<p class="tabs">Jump to: <a href="#hold">what we hold</a> <a href="#where">season by season</a> <a href="#region">by region</a> '
         '<a href="#series">by series</a> · <a href="wanted.html">most wanted</a> <a href="grid.html">the grid</a></p>',
         coverage_section(cs, "", {}, "the contests that ran", "Season by season",
                          "A column per season, a row per question; each cell is that season's contests split by answer, held at the bottom. "
                          "A cell opens the contests of that season that are missing it.", season_strips(cs, "", {}), title="What we hold", hid="hold")
         + '<p class="note">A complete package counts as statement, test data and solutions too. Material counts wherever it comes from: the problem archive, '
           "or a source we hold a copy of. A problem set's page on an online judge is a link, not a copy: what we hold of it is the judge's list of problems, not the statements; "
           "a problem's own page on a judge, when we hold it, counts as that problem's statement.</p>"]

    b.append('<h2 id="region">By region</h2><p class="note">The percentage is the share in the best answer; click a header to sort by it. Every segment opens its contests.</p>')
    by_reg = {r: [c for c in cs if SERIES_REGION.get(SERIES_OF[c["id"]]) == r] for r in REGIONS}
    rows = [(f'<td class="nw">{n_link(len(by_reg[r]), "", {"region": r}, esc(r))}</td>', by_reg[r], {"region": r}) for r in REGIONS]
    rows.append(('<td class="nw"><b>all</b></td>', cs, {}))
    b.append(group_bars("region", rows))

    b.append('<h2 id="series">By series</h2><p class="note">Sorted by the number of contests we hold no result of — the top of this table is where a find matters most. '
             "A series' own page shows it edition by edition.</p>")
    by_ser = defaultdict(list)
    for c in cs:
        by_ser[SERIES_OF[c["id"]]].append(c)
    srows = []
    for s, lst in by_ser.items():
        y0, y1 = series_years(series_docs[s])
        srows.append((share(lst, {"results": "none"}), len(lst), s, (f'<td class="nw">{link_series(s, "")}</td><td class="nw">{esc(SERIES_REGION.get(s, ""))}</td>'
                                                                       f'<td class="nw" data-v="{y0}">{y0}–{y1}</td>', lst, {"series": s})))
    b.append(group_bars("series", [r for *_x, r in sorted(srows, key=lambda x: (-x[0], -x[1], x[2]))], "flt", [th("region", f=True), th("years")]))
    return page("Coverage", "\n".join(b), "", "coverage.html")


# ---- most wanted: what is missing, by region; every label and number opens its contests ----
WANTED = (
    ("Results", (
        ("no result held", {"results": "none"}, "we hold no scoreboard, standings, rankings or team list"),
        ("team list only", {"results": "team list"}, "who took part, not how it ended — any result is wanted"),
        ("rankings only", {"results": "rankings"}, "the order of teams only — standings or a scoreboard wanted"),
        ("standings only", {"results": "standings"}, "totals per team — the per-problem scoreboard wanted"),
        ("better result known, not held", {"fetch": "any"}, "a source gives a higher level than the one we hold; a copy of it is wanted"),
        ("partial result", {"also": "partial result"}, "what we hold covers one division or the top places only"),
        ("a source is lost", {"also": "lost source"}, "a result or website source gone from its address, not in the Wayback Machine, no copy here: gone unless someone kept one"))),
    ("Website", (
        ("no address", {"website": "missing: no address"}, "no website address found yet (contests confirmed to have had none are not counted)"),
        ("address known, no copy", {"website": "missing: no copy"}, "the address is known; we hold no copy"))),
    ("Problems", (
        ("no problem set recorded", {"problems": "no set"}, "neither a list of the problems nor the archive's holdings"),
        ("names not listed", {"pmeta": "names: none"}, "the problems are not listed by name"),
        ("letters not known", {"pmeta": "letters: none"}, "which problem had which letter is not known"))
        + tuple((f"{what} missing", {COMP_KEY[key]: "missing"}, f"we do not hold {what} for every problem") for key, _m, what in CV.COMPONENTS)),
    ("Contest metadata", tuple((f"{lab} missing", {"meta": f"{lab}: missing"}, "") for _k, lab in CV.META)),
)


def wanted_page(series_docs: dict) -> str:
    cs = [c for c in CONTESTS.values() if did_run(c)]
    by_r = {r: [c for c in cs if SERIES_REGION.get(SERIES_OF[c["id"]]) == r] for r in REGIONS}
    heads = [th("what is missing")] + [th("all", num=True)] + [th(n_link(len(by_r[r]), "", {"region": r}, esc(r)), num=True) for r in REGIONS]
    rows = []
    for group, items in WANTED:
        rows.append(f'<tr class="grp"><td colspan="{len(REGIONS) + 2}"><b>{group}</b></td></tr>')
        for lab, f, tip in items:
            k = share(cs, f)
            cells = []
            for r in REGIONS:
                kr = share(by_r[r], f)
                p = pct(kr, len(by_r[r]))
                cells.append(f'<td class="num hw" style="background:color-mix(in srgb,var(--part) {round(p * .45)}%,var(--paper))" title="{kr} of {len(by_r[r])} contests in {esc(r)} ({p}%)">'
                             + (n_link(kr, "", {"region": r, **f}) if kr else '<span class="muted">–</span>') + "</td>")
            rows.append(f'<tr><td' + (f' title="{esc(tip)}"' if tip else "") + f'>{n_link(k, "", f, esc(lab)) if k else esc(lab)}</td>'
                        f'<td class="num"><b>{n_link(k, "", f) if k else "–"}</b></td>' + "".join(cells) + "</tr>")
    body = ["<h1>Most wanted</h1>",
            f'<p class="intro">What is missing, of the {num(len(cs))} contests that ran, by region; darker means a larger share of that region\'s contests. '
            "Every label and every number opens the contest list filtered to exactly those contests; add a season or a series there to narrow it down. "
            f'<a href="coverage.html">Coverage</a> has the other side: what we hold. Know where any of this lives? <a href="about.html#contribute">Tell us.</a></p>',
            table(heads, rows, "nosort")]
    return page("Most wanted", "\n".join(body), "", "coverage.html")


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
    rq = facet_q("results")

    def cell(c):
        cid = c["id"]
        head = esc(cid) + (" · " + esc(c["date"]) if c.get("date") else "")
        if not did_run(c):
            return f'<td><a class="cell c-up" href="contest/{esc(cid)}.html" title="{head} — upcoming"></a></td>'
        s = st(c)
        code = CV.encode(rec(c))
        return (f'<td><a class="cell {rq[int(code[0])]}" data-q="{code}" data-t="{head}" href="contest/{esc(cid)}.html" '
                f'title="{head} — results: {esc(s["results"])}"></a></td>')

    def first_year(s):
        return (min(int(c["id"].rsplit("-", 1)[1]) for c in series_docs[s]["contests"]), s)
    groups = [("World Finals", [s for s in series_docs if SERIES_TIER.get(s) == "world-finals"]),
              ("Championships", sorted((s for s in series_docs if s in CHAMPIONSHIPS), key=first_year))]
    for r in REGIONS[1:]:
        groups.append((r, sorted((s for s in series_docs if SERIES_REGION.get(s) == r and s not in CHAMPIONSHIPS and SERIES_TIER.get(s) != "world-finals"), key=first_year)))
    g = ['<div class="tw" style="overflow-x:auto"><table class="grid" id="grid"><thead><tr><th class="lbl"></th>']
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
                    g.append(cell(contests[cid]))
                elif lineage_at.get((sid, y)):
                    tgt = lineage_at[(sid, y)][0]
                    g.append(f'<td><a class="c-lin" href="series/{esc(tgt)}.html" title="continues as {esc(tgt)} ({y})">→</a></td>')
                else:
                    g.append("<td></td>")
            g.append("</tr>")
    g.append("</tbody></table></div>")
    facets = [[k, CV.FACET[k][1], CV.FACET[k][2], list(CV.FACET[k][3]), list(facet_q(k))] for k in FKEYS]
    pick = '<p class="key" id="gridby">Colour by: <select id="gridsel" aria-label="Colour the grid by">' + "".join(
        f'<optgroup label="{esc(gr)}">' + "".join(f'<option value="{i}">{esc(lab)}</option>' for i, (k, lab, g2, *_x) in enumerate(facets) if g2 == gr) + "</optgroup>"
        for gr in GROUPS) + '</select> <span id="gridkey"></span> &nbsp; <span class="cell c-up" style="display:inline-block;vertical-align:-2px"></span> upcoming &nbsp; → the series continues under another name</p>'
    script = ("<script>(function(){var F=" + json.dumps(facets, separators=(",", ":")) + ";var sel=document.getElementById('gridsel'),key=document.getElementById('gridkey');"
              "var cells=document.querySelectorAll('#grid a.cell[data-q]');"
              "function paint(i){var f=F[i];cells.forEach(function(a){var s=+a.dataset.q.charAt(i);a.className='cell '+f[4][s];a.title=a.dataset.t+' \\u2014 '+f[1]+': '+f[3][s];});"
              "key.innerHTML=f[3].map(function(s,j){return '<span class=\"cell '+f[4][j]+'\" style=\"display:inline-block;vertical-align:-2px\"></span> '+s;}).join(' &nbsp; ');"
              "history.replaceState(null,'',i?'#by='+f[0]:location.pathname);}"
              "sel.addEventListener('change',function(){paint(+sel.value);});"
              "var m=/^#by=(\\w+)/.exec(location.hash),i0=m?F.findIndex(function(f){return f[0]===m[1];}):0;if(i0<0)i0=0;sel.value=i0;paint(i0);})();</script>")
    return page("The grid", "<h1>The grid</h1><p class=\"intro\">Every contest on one screen: a row per series, a column per year. "
                "Pick what the squares are coloured by — any of the questions coverage asks. Green is held; lime, amber and orange are less, the further from green the less; white is a hole. "
                "Click a square for the contest.</p>" + pick + "".join(g) + script, "", "coverage.html")


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
    reasons = ", ".join(sorted({st.split(": ", 1)[1] for st, _l, _n in cms_rows.values() if st.startswith("excluded: ")}))
    rows = [f'<tr><td class="num">{i}</td><td class="nw">{link}</td><td class="nw" data-v="{esc(st)}">{chip(st, "h" if st == "in the catalogue" else "n")}</td>'
            f'<td class="small">{name}</td><td class="nw small">{cms_links(i).split(" ", 1)[1]}</td></tr>'
            for i, (st, link, name) in sorted(cms_rows.items())]
    return page("CMS id ledger", "<h1>CMS id ledger</h1>"
                f'<p class="intro">Every contest id of the ICPC CMS this project has looked at: {num(len(cms_rows))} ids — {num(counts["in the catalogue"])} are contests in the catalogue, '
                f'{num(counts["excluded"])} are excluded with a reason ({reasons}), {num(counts["proposed"])} carry a proposed '
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
    dark = sum(1 for c in cs if did_run(c) and rec(c)["results"] == "none")
    n_caps = sum(len(R.get("captures") or []) for L in RES.locs.values() for R in L["resources"].values())
    tiles = [(len(BY_SEASON), "seasons", "season/index.html"), (len(series_docs), "series", "series/index.html"),
             (st["n"], "contests", "contest/index.html"), (len(SETS), "problem sets", "problemset/index.html"),
             (len(PROBLEMS), "problems", "problem/index.html"), (len(cited_docs()), "sources", "source/index.html"),
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
    rrows = []
    for r in REGIONS:
        n = sum(1 for c in cs if SERIES_REGION.get(SERIES_OF[c["id"]]) == r and c.get("status") != "upcoming")
        rrows.append(f'<li><a href="{esc(flt_href("", {"region": r}))}">{esc(r)}</a> <span class="muted">{num(n)} contests</span></li>')
    tiles_html = "".join(f'<div><b>{num(n)}</b><span><a href="{h}">{lab}</a></span></div>' for n, lab, h in tiles)
    srows_html, rrows_html = "".join(srows), "".join(rrows)
    nums_html = '<div class="pts">' + headline_tiles(cs, "", {}) + "</div>"
    dark_html = n_link(dark, "", {"results": "none"})
    body = f"""<h1>ICPC contest archive</h1>
<p class="lede">Every ICPC contest from which a team could advance toward a World Finals, back to 1977 — and where its website,
its results and its problems can still be found: at the original address, in the Wayback Machine, or in this project's own archive.</p>
<div class="nums">{tiles_html}</div>
<p class="note">Search everything with the box at the top right (press <code>/</code>): contest and series ids, names, problems, places, CMS ids, website hosts.</p>
<h2>What we hold</h2>
{nums_html}
<p class="note">Of the {num(st["n"])} contests that ran; a number opens the contests it counts, and <i>missing</i> the ones still wanted.
We hold no result at all for {dark_html} of them, and {num(n_caps)} captures are stored in all.
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
    n_shared = sum(1 for d in SETS.values() if len(d.get("contests") or []) > 1)
    n_raw = len(ARCHIVED_BY_CONTEST)

    def dl(items):
        return '<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in items) + "</dl>"
    places_dl = dl((
    ('<span class="m h">address</span>', "<b>The address now.</b> <i>live</i>: it still serves the document. In doubt: <i>changed</i> (it answers, but what it serves differs), "
     "<i>blocked</i> (the server turns our fetcher away; a browser may still get in), <i>unverified</i> (it answers; there was nothing to compare it against), "
     "<i>empty</i>. Confirmed not there: <i>dead</i>, or <i>replaced</i> by something else. Dead is normal for an old contest and no cause for alarm when there is a copy. "
     "<i>not checked</i>: nobody has looked yet."),
    ('<span class="m h">Wayback</span>', "<b>The Wayback Machine.</b> <i>snapshot</i>: a snapshot shows the document; the source's page opens that snapshot, not the calendar. "
     "In doubt: <i>bad snapshot</i> (one exists, but it holds an error page or an empty shell). Confirmed not there: <i>no snapshot</i>, or <i>excluded</i>. "
     "<i>n/a</i>: the page is an app, and a snapshot of it shows nothing. <i>not checked</i>: nobody has looked yet."),
    ('<span class="m h">archive</span>', "<b>Our archive.</b> <i>held</i>: we hold a copy; the source's page opens the one that counts, the current one. "
     "In doubt: <i>bad copy</i> (we fetched it, but what came back is not the document). <i>not captured</i>: no copy yet, and there is still somewhere to take one from. "
     "<i>lost</i>: gone from its address, not in the Wayback Machine, and no copy here. Gone unless someone kept one. <i>n/a</i>: the page is empty, there is nothing to hold."),
    ('<span class="m h">green</span> <span class="m l">amber</span> <span class="m x">red</span> <span class="m p">blue</span> <span class="m g">grey</span>',
     "The label of a mark is the place and never changes; the colour is the answer, the same for all three: <b>green</b> it is there, <b>amber</b> something is there but "
     "it is in doubt and needs a look, <b>red</b> confirmed not there, <b>blue</b> not done yet (not checked, not captured: work of ours that is pending), <b>grey</b> does not apply."),
))
    objects_dl = dl((
    ('<a href="season/index.html">Season</a>', "From the first regional to the World Finals it feeds. Shown as <i>2024–2025</i>. Its page is the advancement tree."),
    ('<a href="series/index.html">Series</a>', "A line of editions under one name (<i>nwerc</i>). Renamings and splits are recorded as lineage."),
    ('<a href="contest/index.html">Contest</a>', "One edition (<i>nwerc-2020</i>). The year in the id is the season label, not the date: a fall regional postponed to January keeps its number."),
    ('<a href="problemset/index.html">Problem set</a>', "The problems a contest used; nearly always one set per contest, with the same id. Its page says what we hold of it, and what of that the ICPC Problem Archive holds."),
    ('<a href="problem/index.html">Problem</a>', "One problem: where it appeared, what is held, where it can be solved."),
    ('<a href="source/index.html">Source</a>', "An address at a point in time — what it served for a contest — and where that can be found: at the address now, "
     "in the Wayback Machine, in our archive."),
    ('<a href="judge/index.html">Online judge</a>', "A site where ICPC problems can be solved."),
    ('<a href="location/index.html">Location</a>', "Where contests were held: country, state or province, city, institution — one tree."),
))
    status_dl = dl((
    ('<span class="pl q4">scoreboard</span>', "<b>Held.</b> The first pill is the best result we hold a copy of. A contest has one level, the highest it reaches: "
     "<b>scoreboard</b> (every team, every problem), <b>standings</b> (totals per team), <b>rankings</b> (order only), <b>team list</b> (who took part). "
     "A standings page of the ICPC CMS is one of these like any other source; where it disagrees with another source, it tends to be the one that is wrong."),
    ('<span class="pl q3">standings</span> <span class="pl q2">test data: some</span> <span class="pl q1">team list</span>',
     "<b>Partly held, or a lesser result</b>: lime, amber, orange — the further from green, the less. For results these are the lower levels "
     "(standings, rankings, team list); elsewhere amber means we hold it for some of the problems."),
    ('<span class="pl ql">editorial: link only</span>', "<b>Known at an address, no copy held.</b> A problem set's page on an online judge counts as this for statements and data: "
     "what we hold of it is the judge's list of problems, not the material. A problem's own page on a judge, when we hold it, counts as that problem's statement."),
    ('<span class="pl q0">packages: none</span>', "<b>Missing</b> — a hole. Everything white is something wanted."),
    ('<span class="pl qu">solutions: not recorded</span>', "A source is known, but what it holds has not been recorded yet."),
    ('<span class="pl qx">CMS id: none</span>', "<b>None exists</b>: looked, and there is none to have (no CMS entry; a contest that had no website). Not missing."),
    ('<span class="pl q4">frozen scoreboard</span>', "The scoreboard as it stood at the freeze. It is kept beside the result, not counted as one: it does not say how the contest ended."),
    ('<span class="pl q2">partial</span>', "The result we hold covers only a part of the contest: one division, the top places."),
    ('<span class="pl ql">scoreboard: link only</span>', "Beside the result: a better result than the one we hold is known at an address, and we hold no copy of it yet."),
    ("<b>Wanted</b>", "Under the pills: everything that is not held and could be, in words."),
    (chip("2 lost", "x"), "Result or website sources that are gone from their address (dead, or replaced by something else), are not in the Wayback Machine, "
     "and of which we hold no copy: their archive mark says <i>lost</i>. Gone unless someone kept one."),
    (chip("1 only here", "h"), "A result or website source gone from its address and not in the Wayback Machine, but we hold a copy — as far as we know the only one."),
    (chip("upcoming", "n"), "The contest has not run yet. Nothing about its problems is published before it has."),
    (chip("not listed yet", "n"), "Beside a row of the results: we hold a copy of a page about this contest that is not yet listed as one of its sources."),
))
    marks_dl = dl((
    ('<span class="m q4">S</span><span class="m q3">St</span><span class="m q2">R</span><span class="m q1">T</span><span class="m q4">F</span>',
     "Results: <b>S</b> scoreboard, <b>St</b> standings, <b>R</b> rankings, <b>T</b> team list, and beside them <b>F</b> frozen scoreboard. One mark per kind that exists; "
     "a mark we hold a copy of is filled in the colour of its level, the same colours as in every bar."),
    ('<span class="m h">W</span>', "Website."),
    ('<span class="m h">filled</span> <span class="m k">outlined</span>', "Filled: we hold a copy (green; a result in the colour of its level). Outlined blue: link only."),
    ('<span class="m h">St</span><span class="m l">D</span><span class="m k">So</span><span class="m n">P</span><span class="m u">E</span>',
     "Problems, what we hold of each kind of material: <b>St</b> statements, <b>D</b> test data, <b>So</b> solutions, <b>P</b> complete packages, <b>E</b> editorial. "
     "It counts wherever it comes from: the ICPC Problem Archive, or a source we hold a copy of. Filled green: for every problem. Amber: for some. "
     "Blue outline: link only — a source that has it is known, we hold no copy (a problem set's page on an online judge is this: our copy is the judge's list, "
     "not the material; a problem's own page on a judge, when we hold it, counts as that problem's statement). "
     "White, outlined: none held and none known — wanted. Dashed: a source is known, but what it holds is not recorded. A complete package counts as statement, test data and solutions too. "
     "On a single problem the marks say what we hold of that problem, from the same places (held for every problem of its set counts for each one; a statement also counts when we hold the problem's own page or statement file on an online judge), "
     "with <b>IV</b>/<b>OV</b> for input and output validators. "
     "The number before the marks is how many problems the contest had (how many are listed by name when that is not known; <i>set</i> when neither is)."),
    ('<span class="m u">src</span>', "No problem set is recorded for the contest, but a published set or a problem's page is known (on the web or on an online judge); "
     "the marks after it say what we hold of that material."),
    (judge_mark("kattis") + judge_mark("codeforces") + judge_mark("baekjoon") + judge_mark("qoj"),
     "An online judge, shown by its logo (its short name where it has none); hover for the name. Beside a problem the logo opens the problem "
     "on that judge. Grey: the judge has closed, and the link goes to a Wayback snapshot."),
))
    body = f"""<h1>About</h1>
<p class="lede">What is here, how to read it, and how to help.</p>
<p class="tabs"><a href="#read">How to read this site</a> <a href="#status">Contest status</a> <a href="#coverage">Coverage</a> <a href="#marks">Marks</a>
<a href="#status-set">Problem sets</a> <a href="#sources">Sources</a> <a href="#contribute">Contribute</a> <a href="#local">Local archive</a> <a href="#data">Data</a></p>

<h2 id="read">How to read this site</h2>
<p class="intro">The catalogue is a set of objects, each with a list page and a page of its own:</p>
{objects_dl}
<p class="intro"><b>Every mention of an object links to its own page</b>, and looks the same wherever it appears. <b>A link stays on this site unless it is
marked <a class="ext" href="#read">like this</a></b>. In particular the address of a source is never linked directly from a contest or a table: the link goes to the
source's page, and that page is where you open the address as it is now, the Wayback Machine, or our archived copy. The exceptions are deliberate and marked:
a problem's online-judge links go straight to the problem on the judge, a contest's CMS links go to the CMS, and an online judge's own site,
a problem set's repository in the (private) problem archive and a place's GeoNames entry are linked from their own pages.
A date links to its day in the <a href="calendar/index.html">calendar</a>, where you can see what else ran that day and that weekend.</p>
<p class="intro">A contest has <b>three kinds of content</b>, always in the same order: its <b>website</b>, its <b>results</b> and its <b>problems</b>.</p>
<p class="intro"><b>One set of colours, everywhere</b> — every pill, mark, bar and square: <span class="pl q4">green</span> we hold it (it is there);
<span class="pl q2">amber</span> partly, or in doubt; <span class="pl ql">blue</span> known but not ours yet, or not done yet: work that is pending;
<span class="pl qr">red</span> lost, confirmed not available anywhere; <span class="pl qx">grey</span> none exists, or it does not apply — nothing to do;
<span class="pl q0">white</span> missing, and wanted; <span class="pl qu">hatched</span> not recorded.</p>
<p class="intro">A <b>location</b> is where the contest was held: its sites, as places in the location tree. The CMS also lists staff, guest and
bookkeeping groups as "sites"; those are not places and are never shown. When no real site is recorded, the city the contest's CMS record points at is shown,
marked <span class="chip n">inferred</span>; a site the CMS names that is not in the tree yet is marked <span class="chip n">not placed</span>, and teams that
competed remotely <span class="chip n">online</span>. A source that covers only part of a contest says so beside its role, like
<span class="chip sc">Division 1</span>.</p>
<p class="intro">For spot checks, <a href="random.html">Random</a> in the header (or the key <b>r</b>) opens a page picked at random.</p>

<h2 id="status">Contest status</h2>
<p class="intro">The card under a contest's title answers every question <a href="#coverage">coverage</a> asks, for that contest: a pill per question,
in the colour of its answer. The same colours are used in every bar, square and strip on the site.</p>
{status_dl}

<h2 id="coverage">Coverage</h2>
<p class="intro">Coverage asks the same questions of every contest that ran, in four kinds. <b>Results</b>: one level per contest, the best we hold.
<b>Problems</b>: what the catalogue records about them (<i>problem metadata</i>: the list, names, letters, short names, UUIDs) and what we hold of them
(statements, test data, solutions, packages, editorial), each on its own. <b>Website</b>: held; missing (an address with no copy, or no address known); or none, when the contest had no website of its own. <b>Contest metadata</b>: name, full date, location, CMS id.
<b>Held always means we hold a copy</b>; an address we only know is a link. <b>Everything is counted in contests</b>: “statements: all” is the number of contests
for which we hold every statement, not a number of problems; and recorded is not the same as held, so a contest whose statements we hold can still have
its problems unlisted. What a contest advances to and the editions before and after it are not part of coverage: “none” is a valid answer there, so they
are never missing — they can only be wrong, and a correction is welcome (see <a href="#contribute">Contribute</a>).</p>
<p class="intro">Wherever contests are counted — the <a href="coverage.html">whole archive</a>, a season, a series, a location — coverage is shown the same way and
in the same order: the headline numbers, then a panel with a bar per question split by answer, then where it is missing along the group's own axis. <b>Every segment, every label under a bar, every square and every number is a link</b>: it opens the <a href="contest/index.html">contest list</a>
filtered to exactly those contests. The filters are in the bar above that list, the coverage ones on its second line, and they combine; the page
address carries them (<code>contest/index.html#f:region=Europe&amp;website=missing</code>), so a filtered list can be shared. To see <i>where</i> something is missing:
a series' page has a square per edition and question, a season's page a square per contest and question, the coverage page and a location's page a strip per question
season by season; in a table of series, seasons or countries each row carries the same bars in small;
<a href="wanted.html">most wanted</a> counts what is missing by region, and <a href="grid.html">the grid</a> colours every contest by any one question.</p>

<h2 id="marks">Marks</h2>
<p class="intro">The small letters in tables. A result mark links to the source it stands for.</p>
{marks_dl}

<h2 id="status-set">Problem sets</h2>
<p class="intro">A problem set is nearly always the set of one contest and carries the same id; {n_shared} were sat by several contests (a joint contest, or a regional whose sites all sat the same problems). The contest page says where the set
was published and where it can be solved; the set's page says what we hold of it, and what of that is in the ICPC Problem Archive (a private collection of problem packages). A contest's problem list is
<b>listed</b> when we know every problem by name, <b>partly listed</b> when we know some, <b>count only</b> when we know how many there were but not their names,
<b>source only</b> when no set is recorded but a published set or a problem's page is known, and <b>none</b> when nothing is. What is held for a
single problem is recorded for few sets; elsewhere a problem's marks follow from its set: held if the set holds that kind for every problem, not held if for none,
dashed if for some. A <b>UUID</b> is the identity of a problem's package; a problem reused in another contest keeps it.</p>

<h2 id="sources">Sources</h2>
<p class="intro">A <b>source</b> is an address at a point in time: one document a contest points at. Its <b>type</b> says what the document is: website, scoreboard, frozen
scoreboard, standings, rankings, problem set, problem, editorial, team list or report. It is the document that matters, not the address: addresses die and get reused, so a
source that is no longer at its address names the time it is meant at, as <i>address (at 2007-11-05)</i>. A page that is reused year after year is a source per year;
each one's page links to the others.</p>
<p class="intro">The same document can be found in up to <b>three places</b>, and every list of sources shows all three as one unit, always in this order and always under these names:</p>
{places_dl}
<p class="intro">Any combination occurs: a scoreboard can be live, in the Wayback Machine and in our archive all at once, or only in one of them. A source's own page is
the only place where the three are opened: the address, the snapshot that shows the document, and our copy. Links <a class="local" href="#local">marked local</a> need the
local archive server (below).</p>

{source_descriptions.ABOUT}

<h2 id="contribute">Contribute</h2>
{R.about_text(REPO)}

<h2 id="local">Local archive</h2>
<p class="intro">Besides the result pages on the public replay site, this project holds a much larger private archive: raw captures of every result page and full
crawls of <b>{n_sites}</b> contest websites ({n_raw} contests with raw captures in all). That is too big for GitHub Pages, so it is not published yet.
Links <a class="local" href="{LOCAL_BASE}/" title="{LOCAL_TITLE}">marked like this</a> point at a small server on <b>your own machine</b>
(<code>{LOCAL_BASE or "this host"}</code>). They work only with the <code>archive</code> repository checked out next to <code>contests</code> and the server running;
for everyone else they fail to connect.</p>
<pre><code># in your checkout of the contests repo (archive checked out alongside it)
python3 tools/index_websites.py     # after new site crawls
python3 tools/serve.py              # rebuilds the site with local links, serves on 127.0.0.1:8123</code></pre>
<p class="intro">Then browse <code>http://127.0.0.1:8123/</code> — the same pages as the public site, with every local link live. <b>Open the archived website</b> (on a source's page) plays a crawled
site back page by page; pages that were not captured go to the Wayback Machine or the live site.</p>

<h2 id="data">Data</h2>
<p class="intro">The whole catalogue as one file is <a href="catalogue.json">catalogue.json</a>. Typeface: IBM Plex Sans (SIL Open Font License).</p>"""
    return page("About", body, "", "about.html")



def source_words(d: dict) -> str:
    """What a source is, in a few plain words, for the search box: `problem set of north-russia-2016`."""
    cits = d["cits"]
    if not cits:
        return "no contest cites it now"
    roles = sorted({r for c in cits for r in c["roles"]}, key=lambda r: RANK.get(r, 99))
    ids = [c["contest"] for c in cits]
    return ((", ".join(role_label(r) for r in roles) or "source") + " of " + ", ".join(ids[:3]) + (f" and {len(ids) - 3} more" if len(ids) > 3 else "")
            + (f" at {fmt_time(d['time'])}" if d["time"] and len(DOCS_OF[d["k"]]) > 1 else ""))


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
    with (out / "assets" / "site.css").open("a") as css:   # one rule per judge logo (judge_mark)
        css.write("\n/* ---- judge logos (generated) ---- */\n" + "".join(
            f".j-{f.stem} {{ background-image:url(judges/{f.name}); }}\n" for f in sorted((ASSETS / "judges").glob("*.png"))))
    (out / "assets" / "units.js").write_text(R.units_js())  # the unit list for review mode
    (out / "build.json").write_text(json.dumps({"built": datetime.date.today().isoformat()}))

    REPLAY_LOOKUP.clear()
    REPLAY_REPO.clear()
    REPLAY_PROBLEMSET.clear()
    REPLAY_BY_CONTEST.clear()
    if aux["replay-index"]:
        for e in aux["replay-index"]["pages"]:
            at = e.get("at") or e["path"]     # a file published once sits under another copy's path (bake.py)
            if e.get("repo") and e["repo"] != "replay":
                REPLAY_REPO[e["path"]] = REPLAY_REPO[at] = e["repo"]
            if e.get("url"):
                k = (e["contest"], norm_key(e["url"]))
                REPLAY_LOOKUP[k] = at
                if e.get("artifact") == "problemset":
                    REPLAY_PROBLEMSET[k] = at
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
    index_docs()
    EMPTY_STANDINGS.clear()
    p = ROOT / "data" / "icpc-standings-empty.json"
    if p.exists():
        EMPTY_STANDINGS.update({lid(v["url"]): v.get("asked") or "" for v in json.loads(p.read_text())["contests"].values()})
    BY_SEASON.clear()
    for cid, c in contests.items():
        if c.get("season"):
            BY_SEASON[c["season"]].append(cid)
    global COV
    _HELD.clear(); _ST.clear(); _TOK.clear(); _LOC_OF.clear()  # noqa: E702
    # a website is held when the contest has a `web` source and we hold a crawl of it (or a copy of the source):
    # a crawl seeded from a document that is not a website source (a PDF, a results page) is not a website
    COV = CV.Coverage(series_docs, SETS, held=src_held, placed=lambda c: bool(held_at(c)[0]),
                      web_held=lambda c: bool(by_role(c, "web")) and (c["id"] in website_of or any(src_held(c, s) for s in by_role(c, "web"))))

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
    hide = ("provenance", "notes", "note", "statements", "submissions")   # not published: where the data comes from, remarks, judge "offers"
    pub = lambda d: {k: v for k, v in d.items() if k not in hide}  # noqa: E731
    (out / "problems" / "problems.json").write_text(json.dumps(
        {"generated": datetime.date.today().isoformat(),
         "sets": {sid: {**pub(d), "contests": [pub(m) for m in d.get("contests") or []], "problems": [pub(x) for x in d.get("problems") or []]}
                  for sid, d in SETS.items()},
         "judges": {jid: pub(j) for jid, j in JUDGES.items()}}, ensure_ascii=False))
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
        "problemset": sorted(SETS), "problem": sorted(PROBLEMS), "source": sorted(cited_docs()),
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
        for sid, d in DOCS.items():
            sd = out / "source" / sid
            sd.mkdir(exist_ok=True)
            (sd / "index.html").write_text(source_page(d, "../../"))
        for k, to in DOC_ALIAS.items():   # an address whose every source names a time: its old page leads to the latest
            stub(out / "source" / k / "index.html", f"../{to}/index.html")
        for k, L in RES.locs.items():     # the old locator/ addresses
            if not DOCS_OF.get(k):
                continue                  # not a source (a problem's page on an online judge): never had one
            to = DOC_ALIAS.get(k, k)
            stub(out / "locator" / k / "index.html", f"../../source/{to}/index.html")
            for ts in L["resources"]:
                stub(out / "locator" / k / f"{ts}.html", f"../../source/{to}/index.html")
        (out / "source" / "index.html").write_text(source_list("../"))
        # the address index of the search box: [address, source page, what it serves]; site.js loads it when the box holds an address
        (out / "source-urls.json").write_text(json.dumps([[d["url"], sid, source_words(d)] for sid, d in cited_docs().items()],
                                                         ensure_ascii=False, separators=(",", ":")))
        for r in ROLE_PAGES:
            (out / "source" / "by-role" / f"{r}.html").write_text(source_list("../../", r))
        stub(out / "source" / "by-role" / "mirror.html", "web.html")  # also_at was dropped 2026-11-14
        stub(out / "source" / "by-role" / "icpc_standings.html", "standings.html")  # the role was dropped 2026-11-14
        stub(out / "source" / "by-role" / "judge_page.html", "problemset.html")  # the role was dropped 2026-11-14
        for k in ROLE_PAGES + ["index"]:
            tgt = f"../source/by-role/{k}.html" if k != "index" else "../source/index.html"
            stub(out / "resources" / f"{k}.html", tgt)
            stub(out / "urls" / f"{k}.html", tgt)
        print(f"  {len(cited_docs())} sources; {len(DOCS)} source pages for {len(RES.locs)} addresses ({sum(1 for v in DOCS_OF.values() if len(v) > 1)} addresses are several sources, one per time)")

    n = len(list(out.rglob("*.html")))
    n_stubs = sum(1 for p in out.rglob("*.html") if p.parts[len(out.parts)] in ("locator", "resources", "urls", "problemsets", "judges", "problems") or p.name in ("seasons.html", "local.html")) + n_alias
    print("  review mode: " + ", ".join(f"{n} units on {k} pages" for k, n in R.STATS.items())
          + ("" if R.OPEN else " (not open yet: reached by ?review=1)"))
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
