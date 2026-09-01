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
REGION_GROUPS = {
    "North America": ["socal","naq","nena","nena-atlantic","nena-central","nena-east","nena-north",
        "nena-west","ecna","scusa","rmc","lethbridge","gny","mcpc","seusa","mausa","pacnw","east-na",
        "south-na","alberta","ncna","east-central-na","north-central-na"],
    "Europe & Northern Eurasia": ["poland","hungary","slovenia","turkey","ukraine","cerc","swerc",
        "nwerc","bapc","bapc-prelims","germany","croatia","romania","bulgaria","greece","cyprus",
        "nordic","sweden","norway","ukiepc","ctuo","neerc","nerc","south-russia","central-russia",
        "north-russia","west-siberia","east-siberia","far-east-russia","urals","moscow","taurida",
        "west-neerc","armenia","azerbaijan","georgia","kazakhstan","kyrgyzstan","uzbekistan",
        "erc","werc","mcerc","seerc"],
    "Asia East & Pacific": ["japan","korea","taiwan","hong-kong","singapore","manila","jakarta",
        "kuala-lumpur","thailand","vietnam","south-pacific","south-pacific-west",
        "south-pacific-central","south-pacific-east","south-pacific-division","nzpc","australia",
        "beijing","shanghai","chengdu","hangzhou","xian","harbin","wuhan","fuzhou","hefei","nanjing",
        "dalian","changchun","changsha","jinan","jinhua","jiaozuo","kunming","macau","mudanjiang",
        "nanchang","nanning","ningbo","qingdao","shenyang","tianjin","urumqi","xuzhou","yinchuan",
        "anshan","guangzhou","yangon","pyongyang"],
    "Latin America, Africa & West Asia": ["brazil","mexico","caribbean","central-america",
        "south-america","south-america-north","south-america-south","cuba","acpc","egypt","jordan",
        "syria","lebanon","kuwait","bahrain","oman","qatar","saudi-arabia","palestine","morocco",
        "tunisia","algeria","sudan","south-africa","angola","benin","burkina-faso","ethiopia",
        "ivory-coast","nigeria","senegal","togo","tehran","pakistan","kabul","dhaka","kanpur",
        "amritapuri","kharagpur","kolkata","gwalior","chennai","coimbatore","bombay","mathura",
        "india","gwalior-kanpur","kolkata-kanpur","kolkata-roorkee","gwalior-pune"],
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
dl.fields dt { float:left; clear:left; width:9.5rem; color:var(--muted); }
dl.fields dd { margin:0 0 .3rem 10.5rem; }
input#q { width:100%; max-width:28rem; padding:.45rem .6rem; font-size:1rem;
  border:1px solid var(--line); border-radius:.4rem; background:var(--bg); color:var(--fg); }
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
<a href="{rel}seasons.html">seasons</a> <a href="{rel}coverage.html">coverage</a></div></nav>
<main>{body}</main></body></html>"""


def link_contest(cid: str, rel: str) -> str:
    return f'<a href="{rel}contest/{esc(cid)}.html">{esc(cid)}</a>'


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
        b.append('<div class="tablewrap"><table><tr><th>contest</th><th>date</th>'
                 "<th>advances to</th><th>results</th></tr>")
        for c in reversed(doc["contests"]):  # latest first
            res = c.get("results", {})
            marks = []
            for key, letter in (("scoreboard", "S"), ("frozen_scoreboard", "F"),
                                ("standings", "St"), ("rankings", "R")):
                if key in res:
                    marks.append(f'<a href="{esc(res[key][0]["url"])}" '
                                 f'title="{key.replace("_", " ")}">{letter}</a>')
            arch = [("a/" + e["archived"]) for lst in res.values() for e in lst if e.get("archived")]
            if not arch:
                arch = [p["path"] for p in replay_by_contest.get(c["id"], [])]
            if arch:
                marks.append(f'<a href="{REPLAY_BASE}/{esc(arch[0])}" title="archived copy">A</a>')
            if c.get("icpc_standings"):
                marks.append(f'<a href="{esc(c["icpc_standings"])}" title="ICPC standings">I</a>')
            b.append(
                "<tr><td>" + link_contest(c["id"], rel) + "</td>"
                f"<td>{esc(c.get('date', ''))}</td>"
                "<td>" + ", ".join(link_contest(p, rel) for p in refs(c.get("parent"))) + "</td>"
                f"<td>{' '.join(marks)}</td></tr>"
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

    # ---- helpers shared by seasons/grid ----
    def marks_for(c):
        res = c.get("results", {})
        marks = []
        for key, letter in (("scoreboard", "S"), ("frozen_scoreboard", "F"),
                            ("standings", "St"), ("rankings", "R")):
            if key in res:
                marks.append(f'<a href="{esc(res[key][0]["url"])}" '
                             f'title="{key.replace("_", " ")}">{letter}</a>')
        if c.get("icpc_standings"):
            marks.append(f'<a href="{esc(c["icpc_standings"])}" title="ICPC standings">I</a>')
        return " ".join(marks)

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
                     + f'<span class="meta">{esc(c.get("date", ""))} {marks_for(c)}</span>')
            if not kids:
                return f'<div class="leaf">{label}</div>'
            inner = "\n".join(node(k) for k in kids)
            return f"<details open><summary>{label}</summary>{inner}</details>"

        wf_id = f"wf-{season}"
        body = [f"<h1>Season {season - 1}–{season}</h1>"]
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

    # ---- coverage ----
    eras = [("pre-1999", 0, 1998), ("1999–2007", 1999, 2007),
            ("2008–2015", 2008, 2015), ("2016+", 2016, 9999)]
    tab = {label: defaultdict(int) for label, *_ in eras}
    for cid, c in contests.items():
        if c.get("status") == "upcoming":
            continue
        y = int(cid.rsplit("-", 1)[1])
        for label, lo, hi in eras:
            if lo <= y <= hi:
                t = tab[label]
                t["n"] += 1
                res = c.get("results", {})
                t["date"] += bool(c.get("date"))
                t["sb"] += ("scoreboard" in res or "frozen_scoreboard" in res)
                t["any"] += bool(res) or bool(c.get("icpc_standings"))
                t["web"] += bool(c.get("web"))
    rows = [f"<tr><td>{label}</td><td>{t['n']}</td><td>{t['date']}</td>"
            f"<td>{t['sb']}</td><td>{t['any']}</td><td>{t['web']}</td></tr>"
            for label, t in ((l, tab[l]) for l, *_ in eras)]
    (out / "coverage.html").write_text(page(
        "Coverage", "<h1>Collection coverage</h1><p class='muted'>Contests that ran, by era.</p>"
        "<div class='tablewrap'><table><tr><th>era</th><th>contests</th><th>dated</th>"
        "<th>scoreboard</th><th>any result</th><th>web url</th></tr>"
        + "\n".join(rows) + "</table></div>", ""))

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
<a href="coverage.html">collection coverage</a></p>
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
