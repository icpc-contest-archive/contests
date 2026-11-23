# Data scan 2026-11-23 — shared brief for every scan agent

Fredrik Niemelä (ICPC Problem Archive Director; Nordic RCD) keeps a catalogue of every ICPC contest
from which a team could advance toward a World Finals, plus an archive of copies of their sources.
He asked for a scan of the data for issues and missing data: **fix what can be fixed directly, report
the rest so it can be discussed.** You are one of many agents, each with its own area. Stay in yours.

## Where things are (device shell: `mcp__remote-devices__device_bash`)

Load the device tools first: `ToolSearch` with query
`select:mcp__remote-devices__device_bash,mcp__remote-devices__device_stage_files`.
All paths below are inside the device shell (`$HOME/mnt/icpc-contests/...`).

- `$HOME/mnt/icpc-contests/_scan-2026-11-23/contests/` — **a git worktree of the catalogue at a fixed
  commit (branch data-scan-2026-11-23). READ-ONLY for you.** Never edit, never run git there.
  Another session is working in the main checkout (`.../icpc-contests/contests/`): never touch that one.
- `.../icpc-contests/archive/` — the private archive of captures (`<series>/<contest>/<kind>/<capture>/...`),
  READ-ONLY. A source's `archived:` paths are relative to this folder.
- `.../icpc-contests/*.json`, `regionals-*.json`, `new_regionals-*.json`, `all_contests.csv`,
  `cms-map.json`, `icpc_all_standings.json` … — icpc.global (CMS) API dumps, read-only.
- **Your output folder: `$HOME/mnt/icpc-contests/_scan-2026-11-23/findings/<your-id>/`** — the only place
  you write. Scratch files go there too (in a `work/` subfolder).

Each device_bash call is a fresh `bash -c` (≤180 s; pass `timeout_ms` up to 180000; split long jobs and
keep state in files). Python 3.10 with PyYAML, plus pdftotext, tesseract, curl, jq. Use the catalogue's own
helpers: `sys.path.insert(0, 'tools'); import catalogue as cat` (`cat.load_contests()`, `load_sets()`,
`load_series()`, `load_judges()`, `load_locations()`, `cat.sources(c)`, …) from inside the worktree.

Network: WebSearch / WebFetch work from your own tools (cloud). From the device shell, curl reaches most
sites and the Wayback CDX API (`curl -s 'https://web.archive.org/cdx/search/cdx?url=...&output=json'`;
if the proxy refuses, retry with `env no_proxy='*' curl ...`). web.archive.org is often refused to
WebFetch — use the device shell for it. Be gentle with every site (no floods; ≤ 1 request/s per host).
acmicpc.net (Baekjoon) closed 2026-04-28: only Wayback snapshots from before 2026-04-27 are real.

## Read first

`contests/DEFINITIONS.md` (the data model: sources, roles, `contains`, `as_of`, coverage, problems,
locations, levels, provenance) and `contests/tools/catalogue.py`. Skim the relevant `contests/reports/*.md`
for earlier work in your area so you do not redo it.

## Fredrik's standing rulings (respect them; they are the definitions of "correct")

- A **source is an address at a time** (`as_of` pins the time). The same URL meant at two different times
  is two sources. A Wayback URL is unwrapped to the raw URL + `as_of` (never a wayback of a wayback).
- Roles: web, scoreboard, frozen_scoreboard, standings, rankings, teams, problemset, problem, editorial,
  report. Results ladder: scoreboard > standings > rankings > teams (a frozen scoreboard is beside it).
  `judge_page`, `icpc_standings` and `also_at` no longer exist; a mirror is its own source.
- Source criteria (2026-11-14): champions-only / top-N lists are `rankings` with `scope`; ranked top places
  plus an unranked Honorable Mention tail is complete `standings`; a solved-or-not grid is a `scoreboard`;
  outside-participant boards count only when official teams are distinguishable; a page covering several
  contests is a source of each, with `scope`; second-hand accounts are `rankings`; final + frozen on one
  page gets both roles; `web` = a page/site by the organisers or host about that edition (a single results
  page is not `web`); bare solutions or test data are `problemset`, an `editorial` explains; `teams` only
  for non-results team lists; `report` for the old-style contest reports.
- A live site that now shows a later year: pin `as_of` when a copy of the right edition exists; keep as
  lost when the address was the contest's site but no copy exists; remove when the address never served
  that edition.
- Being on an online judge does not make a source secondary; we don't care where we got data as long as
  it is correct. Online judge ≠ online contest.
- ICPC CMS (icpc.global) data: registration *indicates* a contest ran, never proves it; CMS standings are
  not often wrong but can be, and when they conflict with other sources they tend to be the wrong one.
  Notes say "indicates", never "proves".
- Contest id `<series>-<year>`, the year from the half of the season the contest *typically* runs in; a
  delayed or early edition keeps the pattern. `season` = the season's END year (regional-YYYY feeds
  wf-(YYYY+1)). Cancelled editions are not in the catalogue (they live in registry/cms-triage.yaml) and do
  not join next-chains.
- Absent field = not researched; `null` = confirmed none; `none: [role]` = confirmed no source of that role.
- **Problem disclosure: never add problem names, letters or even counts for a contest that has not
  happened yet.**
- A contest whose statement we hold must have its problem names (read them from the statement). The
  statement's title replaces a judge's short title (the judge's title kept as an alias). For complete,
  high-confidence readings the document's problem count wins. For two-division contests `count` = distinct
  problems, letters kept per division. A contest whose scoreboard we hold should have at least its number
  of problems and very probably the letters.
- Problem sets: if the lettering differs between two contests it is not the same set (two sets sharing
  problems). Sharing is regional (South Pacific divisions, Latin America, some Russian subregions); a set
  shared between contests NOT run at the same time is almost certainly an error. A set lent by region X to
  Y is named after X. Agreement of two independent sources is accepted as evidence of sharing.
  wf-2022 and wf-2023 sharing five problems is correct.
- Locations: administrative sites are never relevant (keep the data, never show them). Show locations,
  not countries.
- Provenance stays in the data (notes are hidden on the site, not deleted).

## Known open items — do NOT re-report these unless you bring new evidence or a resolution

- All 6,119 Live Archive problem links are wrong (LA numbers on onlinejudge.org = unrelated UVa problems).
- Whether to scrub the 1,320 "rendered from the icpc.global API…" notes; whether to publish reports.
- The catalogue still names seerc.icpc.global (moved to seerc.euc.icpc.global).
- From the description round (`contests/reports/source-descriptions-2026-11-21.md`): the 533 fact
  differences, 1,074 second readings, 29 medium-confidence fills and 8 span-date contests are unapplied —
  some agents are assigned exactly these; others leave them alone.
- Validator warnings (tools/validate.py): 5 parent-dated-earlier, wf-2026 upcoming-but-past, 97 contests
  whose parent is unknown — the structure agent owns these.
- 2026-11-01 held-back items: ecna-2016/ecna-2019/mcpc-2015/naq-2022/socal-2020 Kattis lists more problems
  than the set count; shared North-America regional sets 2019–2023; nwerc-2010 Kattis link → NWERC 2011;
  nwerc-2003 likely 9 problems. (Re-check only if your area is problems; report the state.)

## What counts as a fix you may prepare

A change that is (1) inside your area, (2) backed by strong evidence you actually looked at (a held copy,
a live page, a Wayback snapshot, the CMS API), and (3) consistent with the data model and the rulings.
Examples: a missing date/location read from an official page; a new source whose page you opened and that
is clearly this contest's (right year, right event); a wrong role per the criteria above; a broken
reference; a missing cms id that the CMS API matches unambiguously. When in doubt, it goes in the report.
Never remove data on a hunch. Never invent: every value must be one you saw.

## Output — exactly these files in `findings/<your-id>/`

1. `ops.json` — a JSON list of fix operations for `contests/tools/apply_scan_ops.py` (read its docstring).
   Operation shape:
   `{"file": "series/nordic.yaml", "path": ["contests", {"id": "nordic-2004"}, "date"], "op": "set",
     "value": "2004-10-02", "old": null, "reason": "...", "evidence": "URL or archive path + what it shows"}`
   - ops: `set`, `unset`, `append`, `remove`, `insert_contest`, `create_file` (problemsets only).
   - Always give `"old"` on `set`/`unset` (the value you expect now; `null` for absent) so stale ops fail.
   - Select sources with `{"url": ...}` (add `"as_of"` when the URL occurs twice in that contest).
   - A new source: `append` to `["contests", {"id": X}, "sources"]` a mapping with `url`, `roles`, and as
     applicable `contains` (for problemset/problem), `scope`, `judge`, `as_of` (14-digit Wayback timestamp
     when the content meant is a snapshot), and `note: "found by the data scan 2026-11-23 (<how>)"`. Use
     `"unique_keys": ["url", "as_of"]`. Do not set url_state/url_checked/archived (capture rounds do that).
   - A changed fact (date, location, count, cms id…): also append to `["contests", {"id": X}, "provenance"]`
     the line `"<fact> <value> read from <url> (data scan 2026-11-23)"`.
   - **Check before you finish**: `cd $HOME/mnt/icpc-contests/_scan-2026-11-23/contests &&
     python3 tools/apply_scan_ops.py --check ../findings/<your-id>/ops.json` — every op must say `ok`.
     Drop or repair any that fail. (This only reads; it never writes.)
2. `report.md` — what you checked and how (so it can be rerun), counts, what the ops fix (grouped), and the
   **items for discussion with Fredrik**. Frame each discussion item the way he likes: the question, what
   it implies, the best argument for each option, 1–3 example links/contest ids, and your recommendation.
   Group many similar cases into one question with the full list in data.json.
3. `data.json` (optional) — full lists behind the report.

Do not write to memory, do not commit, do not push, never send email. Do not edit anything outside your
findings folder. If something blocks you, write what you have and say so in report.md.

Your final message (≤ 250 words): ops count by kind, the top 3–5 discussion items, anything that blocked you.
