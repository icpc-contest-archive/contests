#!/usr/bin/env python3
"""Build the static catalogue site into site/ (relative links only, mountable anywhere).

Optional inputs, used when present:
  data/archive-index.json  — captures held by the (private) archive repo
  data/replay-index.json   — pages baked into the public replay shard(s)
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPLAY_BASE = os.environ.get("REPLAY_BASE", "https://icpc-contest-archive.github.io/replay")

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
    "Asia Pacific": ["japan","korea","taiwan","singapore","manila","jakarta","kuala-lumpur",
        "thailand","vietnam","yangon","south-pacific","south-pacific-west","south-pacific-central",
        "south-pacific-east","south-pacific-division","nzpc","australia"],
    "Asia East": ["hong-kong","macau","pyongyang","beijing","shanghai","chengdu","hangzhou","xian",
        "harbin","wuhan","fuzhou","hefei","nanjing","dalian","changchun","changsha","jinan","jinhua",
        "jiaozuo","kunming","mudanjiang","nanchang","nanning","ningbo","qingdao","shenyang",
        "tianjin","urumqi","xuzhou","yinchuan","anshan","guangzhou"],
}
SERIES_REGION = {s: g for g, ss in REGION_GROUPS.items() for s in ss}

CSS = """
:root { --fg:#1a1a1a; --muted:#666; --line:#ddd; --accent:#0b5cad; --bg:#fff; --chip:#f0f4f8; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e8e8e8; --muted:#9a9a9a; --line:#333; --accent:#6fb1e8; --bg:#111; --chip:#1d2733; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:64rem; margin:0 auto; padding:1.2rem; }
a { color:var(--accent); text-decoration:none; } a:hover { text-decoration:underline; }
h1 { font-size:1.5rem; margin:.4rem 0 .8rem; } h2 { font-size:1.15rem; margin:1.4rem 0 .5rem; }
table { border-collapse:collapse; width:100%; } .tablewrap { overflow-x:auto; }
th,td { text-align:left; padding:.28rem .55rem; border-bottom:1px solid var(--line);
  vertical-align:top; white-space:nowrap; }
td.wrap { white-space:normal; }
.muted { color:var(--muted); } .small { font-size:.85em; }
.chip { background:var(--chip); border-radius:.6em; padding:.05em .55em; font-size:.85em;
  display:inline-block; margin:0 .15em .15em 0; }
nav.top { border-bottom:1px solid var(--line); }
nav.top div { max-width:64rem; margin:0 auto; padding:.55rem 1.2rem; }
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
dl.fields dt { float:left; clear:left; width:9.5rem; color:var(--muted); }
dl.fields dd { margin:0 0 .3rem 10.5rem; }
input#q { width:100%; max-width:28rem; padding:.45rem .6rem; font-size:1rem;
  border:1px solid var(--line); border-radius:.4rem; background:var(--bg); color:var(--fg); }
td.num, th.num { text-align:right; }
.bar { display:inline-block; width:3.6rem; height:.5em; margin-left:.45em; border-radius:.25em;
  background:var(--chip); overflow:hidden; vertical-align:baseline; }
.bar i { display:block; height:100%; background:var(--accent); }
h2.rgn { margin-top:1.6rem; }
"""

SEARCH_JS = """
const idx = fetch(REL + 'search.json').then(r => r.json());
const q = document.getElementById('q'), out = document.getElementById('hits');
q.addEventListener('input', async () => {
  const term = q.value.trim().toLowerCase();
  if (term.length < 2) { out.innerHTML = ''; return; }
  const data = await idx;
  const hits = data.filter(c => c.id.includes(term) ||
    (c.name && c.name.toLowerCase().includes(term))).slice(0, 40);
  out.innerHTML = hits.map(c =>
    `<tr><td><a href="${REL}contest/${c.id}.html">${c.id}</a></td>` +
    `<td class="wrap">${c.name || ''}</td><td>${c.date || ''}</td></tr>`).join('');
});
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def refs(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def page(title: str, body: str, rel: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body>
<nav class="top"><div><a href="{rel}index.html">ICPC contest archive</a>
<a href="{rel}grid.html">grid</a> <a href="{rel}series/index.html">series</a>
<a href="{rel}seasons.html">seasons</a> <a href="{rel}coverage.html">coverage</a>
<a href="{rel}urls/index.html">urls</a> <a href="{rel}wanted.html">wanted</a></div></nav>
<main>{body}</main></body></html>"""


def link_contest(cid: str, rel: str) -> str:
    return f'<a href="{rel}contest/{esc(cid)}.html">{esc(cid)}</a>'


TIERS = (("scoreboard", "S"), ("frozen_scoreboard", "F"),
         ("standings", "St"), ("rankings", "R"))
MARK_LEGEND = ('<p class="small muted"><b>S</b> scoreboard · <b>F</b> frozen scoreboard · '
               '<b>St</b> standings · <b>R</b> rankings · <b>I</b> ICPC standings — '
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
        arch = next((e for e in entries if e.get("archived")), None)
        kind = key.replace("_", " ")
        if arch:
            out.append(f'<a class="mark m-arch" href="{REPLAY_BASE}/a/{esc(arch["archived"])}" '
                       f'title="{kind} — archived copy">{letter}</a>')
        else:
            out.append(f'<a class="mark m-live" href="{esc(entries[0]["url"])}" '
                       f'title="{kind} — live link only, not yet archived">{letter}</a>')
    if c.get("icpc_standings"):
        out.append(f'<a class="mark m-ist" href="{esc(c["icpc_standings"])}" '
                   f'title="ICPC standings (CMS data; archived via the API dump)">I</a>')
    return "".join(out)


def load():
    series_docs = {}
    for f in sorted((ROOT / "series").glob("*.yaml")):
        series_docs[f.stem] = yaml.safe_load(f.read_text())
    contests, series_of = {}, {}
    for sid, doc in series_docs.items():
        for c in doc["contests"]:
            contests[c["id"]] = c
            series_of[c["id"]] = sid
    prev, children, subsets = defaultdict(list), defaultdict(list), defaultdict(list)
    for cid, c in contests.items():
        for n in refs(c.get("next")):
            prev[n].append(cid)
        for p in refs(c.get("parent")):
            children[p].append(cid)
        if c.get("subset_of"):
            subsets[c["subset_of"]].append(cid)
    aux = {}
    for name in ("archive-index", "replay-index"):
        p = ROOT / "data" / f"{name}.json"
        aux[name] = json.loads(p.read_text()) if p.exists() else None
    return series_docs, contests, series_of, prev, children, subsets, aux


def result_links(cid, key, entries, replay_lookup, rel, matched_paths):
    rows = []
    for i, e in enumerate(entries):
        url = e["url"]
        parts = [f'<a href="{esc(url)}">live</a>']
        wb = e.get("wayback") or f"https://web.archive.org/web/*/{url}"
        parts.append(f'<a href="{esc(wb)}">wayback</a>')
        baked = ("a/" + e["archived"]) if e.get("archived") else replay_lookup.get((cid, url))
        if baked:
            matched_paths.add(baked)
            parts.append(f'<a href="{REPLAY_BASE}/{esc(baked)}">archived</a>')
        rows.append(
            f'<div class="small"><span class="chip">{esc(key.replace("_", " "))}</span> '
            + " · ".join(parts) + f' <span class="muted">{esc(url[:90])}</span></div>'
        )
    return rows


def build(out: Path):
    series_docs, contests, series_of, prev, children, subsets, aux = load()
    out.mkdir(parents=True, exist_ok=True)
    (out / "contest").mkdir(exist_ok=True)
    (out / "series").mkdir(exist_ok=True)

    replay_lookup = {}
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

    # ---- contest pages ----
    for cid, c in contests.items():
        rel = "../"
        sid = series_of[cid]
        b = [f"<h1>{esc(cid)}</h1>"]
        if c.get("name"):
            b.append(f'<p class="muted">{esc(c["name"])}</p>')
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
            d.append("<dt>CMS ids</dt><dd>" + ", ".join(map(str, ids)) + "</dd>")
        elif ids == []:
            d.append("<dt>CMS ids</dt><dd class='muted'>"
                     + ("pre-CMS era" if c.get("cms_status") == "pre-cms" else "none") + "</dd>")
        for w in refs(c.get("web", [])):
            d.append(f'<dt>web</dt><dd><a href="{esc(w)}">{esc(w[:80])}</a> · '
                     f'<a href="https://web.archive.org/web/*/{esc(w)}">wayback</a></dd>')
        if c.get("icpc_standings"):
            d.append(f'<dt>ICPC standings</dt><dd><a href="{esc(c["icpc_standings"])}">finder page</a></dd>')
        if c.get("notes"):
            d.append(f'<dt>notes</dt><dd class="wrap">{esc(c["notes"])}</dd>')
        d.append("</dl>")
        b += d
        res = c.get("results", {})
        if res or replay_by_contest.get(cid):
            b.append("<h2>Results</h2>")
            matched_paths: set = set()
            for key in ("scoreboard", "frozen_scoreboard", "standings", "rankings"):
                if key in res:
                    b += result_links(cid, key, res[key], replay_lookup, rel, matched_paths)
            extra = [e for e in replay_by_contest.get(cid, []) if e["path"] not in matched_paths]
            for e in extra:
                b.append(f'<div class="small"><span class="chip">{esc(e["artifact"])}</span> '
                         f'<a href="{REPLAY_BASE}/{esc(e["path"])}">archived copy</a> '
                         f'<span class="muted">{esc((e.get("url") or "")[:90])}</span></div>')
        caps = archived_by_contest.get(cid)
        if caps:
            b.append(f'<p class="small muted">{len(caps)} raw capture(s) in the archive repo.</p>')
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
        b.append(MARK_LEGEND)
        b.append('<div class="tablewrap"><table><tr><th>contest</th><th>date</th>'
                 "<th>advances to</th><th>results</th></tr>")
        for c in reversed(doc["contests"]):  # latest first
            b.append(
                "<tr><td>" + link_contest(c["id"], rel) + "</td>"
                f"<td>{esc(c.get('date', ''))}</td>"
                "<td>" + ", ".join(link_contest(p, rel) for p in refs(c.get("parent"))) + "</td>"
                f"<td>{tier_marks(c)}</td></tr>"
            )
        b.append("</table></div>")
        (out / "series" / f"{sid}.html").write_text(page(sid, "\n".join(b), rel))

    # series index
    rel = "../"
    rows = []
    for sid in sorted(series_docs):
        doc = series_docs[sid]
        years = [int(c["id"].rsplit("-", 1)[1]) for c in doc["contests"]]
        rows.append(f'<tr><td><a href="{esc(sid)}.html">{esc(sid)}</a></td>'
                    f"<td>{len(years)}</td><td>{min(years)}–{max(years)}</td>"
                    f'<td class="wrap">{esc(doc["series"].get("name", ""))}</td></tr>')
    (out / "series" / "index.html").write_text(page(
        "Series", "<h1>Series</h1><div class='tablewrap'><table>"
        "<tr><th>series</th><th>editions</th><th>years</th><th>name</th></tr>"
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
            label = (link_contest(cid, rel)
                     + f'<span class="meta">{esc(c.get("date", ""))} {tier_marks(c)}</span>')
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
        rows.append(f'<tr><td><a href="season/{season}.html">{season - 1}–{season}</a></td>'
                    "<td>" + ", ".join(link_contest(x, rel) for x in sorted(wf)) + "</td>"
                    f"<td>{len(ids)}</td></tr>")
    (out / "seasons.html").write_text(page(
        "Seasons", "<h1>Seasons</h1><p class='muted'>Each season links to its full "
        "advancement tree.</p><div class='tablewrap'><table>"
        "<tr><th>season</th><th>World Finals</th><th>contests</th></tr>"
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
        res = c.get("results", {})
        if "scoreboard" in res or "frozen_scoreboard" in res:
            return "c-sb", "scoreboard"
        if res:
            return "c-res", "standings/rankings only"
        if c.get("icpc_standings"):
            return "c-ist", "ICPC standings only"
        return "c-none", "no results yet"

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
                    g.append(f'<td><a class="cell {cls}" href="contest/{esc(cid)}.html" '
                             f'title="{esc(cid)} — {why}"></a></td>')
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
        res = c.get("results", {})
        return {"n": 1, "date": bool(c.get("date")),
                "sb": ("scoreboard" in res or "frozen_scoreboard" in res),
                "res": bool(res),
                "any": bool(res) or bool(c.get("icpc_standings")),
                "arch": any(e.get("archived") for lst in res.values() for e in lst),
                "web": bool(c.get("web"))}

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

    COV_HDR = ('<tr><th>{}</th><th class="num">contests</th><th class="num">any result</th>'
               '<th class="num">scoreboard</th><th class="num">archived</th>'
               '<th class="num">web</th><th class="num">dated</th><th class="num">missing</th></tr>')

    def cov_row(label, t):
        return (f'<tr><td class="wrap">{label}</td><td class="num">{t["n"]}</td>'
                + pcell(t["any"], t["n"]) + pcell(t["sb"], t["n"]) + pcell(t["arch"], t["n"])
                + pcell(t["web"], t["n"]) + pcell(t["date"], t["n"])
                + f'<td class="num">{t["n"] - t["any"]}</td></tr>')

    tot = agg(f for *_x, f in ran_rows)
    cov = ["<h1>Collection coverage</h1>",
           f'<p class="muted">{tot["n"]} contests that ran. '
           f'{tot["any"]} ({round(100 * tot["any"] / tot["n"])}%) have at least one result link, '
           f'{tot["sb"]} a full scoreboard, {tot["arch"]} an archived copy in this project, '
           f'{tot["web"]} a contest-website link. '
           f'{tot["n"] - tot["any"]} are still dark — see the <a href="wanted.html">wanted list</a>.</p>',
           '<p class="small muted">jump to: <a href="#era">era</a> · <a href="#season">year</a> · '
           '<a href="#region">world region</a> · <a href="#series">series</a> — '
           '"any result" counts a result link of any tier or ICPC standings; "archived" means '
           'this project holds a captured copy; "missing" = contests with no result link at all.</p>']

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
               'the top of this table is the hunting worklist.</p>'
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
    (out / "urls").mkdir(exist_ok=True)

    def wb_href(e):
        w = e.get("wayback")
        if not w:
            return None
        return w if str(w).startswith("http") else f"https://web.archive.org/web/{w}/{e['url']}"

    url_tables = {k: [] for k, _ in TIERS}
    url_tables["icpc_standings"] = []
    url_tables["web"] = []
    for cid in sorted(contests):
        c = contests[cid]
        for k, _l in TIERS:
            for e in c.get("results", {}).get(k, []):
                url_tables[k].append((cid, e))
        if c.get("icpc_standings"):
            url_tables["icpc_standings"].append((cid, {"url": c["icpc_standings"]}))
        for w in refs(c.get("web")):
            url_tables["web"].append((cid, {"url": w}))
    art_order = ["scoreboard", "frozen_scoreboard", "standings", "rankings",
                 "icpc_standings", "web"]
    counts = {k: len(url_tables[k]) for k in art_order}
    for k in art_order:
        nav_line = " · ".join(
            (f'<b>{kk.replace("_", " ")} ({counts[kk]})</b>' if kk == k else
             f'<a href="{kk}.html">{kk.replace("_", " ")} ({counts[kk]})</a>')
            for kk in art_order)
        rows_h = []
        for cid, e in url_tables[k]:
            extras = []
            if e.get("url_state"):
                extras.append(f'<span class="chip">{esc(e["url_state"])}</span>')
            wb = wb_href(e)
            if wb:
                extras.append(f'<a class="small" href="{esc(wb)}">wayback</a>')
            if e.get("archived"):
                extras.append(f'<a class="small" href="{REPLAY_BASE}/a/{esc(e["archived"])}">'
                              'archived</a>')
            rows_h.append(f'<tr><td>{link_contest(cid, "../")}</td>'
                          f'<td class="wrap"><a href="{esc(e["url"])}">{esc(e["url"][:110])}</a></td>'
                          f'<td>{" ".join(extras)}</td></tr>')
        body = (f'<h1>{k.replace("_", " ")} URLs</h1><p class="small muted">{nav_line}</p>'
                '<div class="tablewrap"><table><tr><th>contest</th><th>url</th><th></th></tr>'
                + "\n".join(rows_h) + "</table></div>")
        (out / "urls" / f"{k}.html").write_text(page(f"{k.replace('_', ' ')} URLs", body, "../"))
    (out / "urls" / "index.html").write_text(page("URL indexes", (
        "<h1>Every URL in the catalogue, by artifact</h1><ul>"
        + "".join(f'<li><a href="{k}.html">{k.replace("_", " ")}</a> — {counts[k]} links</li>'
                  for k in art_order)
        + "</ul><p class='small muted'>Chips show the last live-check verdict where one has "
        "been recorded; wayback/archived links point at the pinned snapshot and this "
        "project's own captured copy.</p>"), "../"))

    # ---- wanted list ----
    wl = ["<h1>Most wanted</h1>",
          '<p class="muted">Contests with no result link at all (<b>dark</b>) and contests '
          'where the only trace is the ICPC standings system (<b>ICPC-only</b>). '
          "Know where any of these results live? "
          '<a href="https://github.com/icpc-contest-archive/contests">Open an issue.</a></p>']
    for g in region_names:
        sec = []
        for s in sorted(per_series):
            if SERIES_REGION.get(s, "Other") != g:
                continue
            dark, fonly = [], []
            for c in series_docs[s]["contests"]:
                if c.get("status") == "upcoming" or c.get("results"):
                    continue
                (fonly if c.get("icpc_standings") else dark).append(c["id"])
            if dark or fonly:
                sec.append(f'<tr><td><a href="series/{esc(s)}.html">{esc(s)}</a></td>'
                           f'<td class="wrap">{" ".join(link_contest(x, "") for x in dark)}</td>'
                           f'<td class="wrap">{" ".join(link_contest(x, "") for x in fonly)}</td></tr>')
        if sec:
            wl.append(f'<h2 class="rgn">{g}</h2><div class="tablewrap"><table>'
                      '<tr><th>series</th><th>dark</th><th>ICPC-only</th></tr>'
                      + "\n".join(sec) + "</table></div>")
    (out / "wanted.html").write_text(page("Most wanted", "\n".join(wl), ""))

    # ---- machine-readable dump ----
    import datetime
    (out / "catalogue.json").write_text(json.dumps(
        {"generated": datetime.date.today().isoformat(), "series": series_docs},
        ensure_ascii=False))

    # ---- search + landing ----
    search = [{"id": cid, "name": c.get("name"), "date": c.get("date")}
              for cid, c in sorted(contests.items())]
    (out / "search.json").write_text(json.dumps(search, ensure_ascii=False))
    ran = sum(1 for c in contests.values() if c.get("status") != "upcoming")
    landing = f"""<h1>ICPC contest archive</h1>
<p>A catalogue of the mainline ICPC contest hierarchy through history:
<b>{ran}</b> contests that ran (plus {len(contests) - ran} upcoming) across
<b>{len(series_docs)}</b> series, with links to results — live, on the Wayback Machine,
and in this project's own archive.</p>
<p><input id="q" placeholder="search contests… (e.g. nwerc, world finals, 1994)"
   autocomplete="off"></p>
<div class="tablewrap"><table id="hits"></table></div>
<h2>Start somewhere</h2>
<p>{link_contest('wf-2025', '')} · <a href="series/wf.html">World Finals series</a> ·
<a href="series/index.html">all series</a> · <a href="seasons.html">seasons</a> ·
<a href="coverage.html">collection coverage</a> · <a href="urls/index.html">all URLs</a> ·
<a href="wanted.html">most wanted</a> · <a href="catalogue.json">catalogue.json</a></p>
<p class="small muted">Data: <a href="https://github.com/icpc-contest-archive/contests">
icpc-contest-archive/contests</a>. Corrections welcome.</p>
<script>const REL='';{SEARCH_JS}</script>"""
    (out / "index.html").write_text(page("ICPC contest archive", landing, ""))

    n = len(list(out.rglob("*.html")))
    print(f"site: {n} pages -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "site"))
    build(Path(ap.parse_args().out))
