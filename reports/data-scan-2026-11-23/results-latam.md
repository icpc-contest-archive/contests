# results-latam — missing results in Latin America (data scan 2026-11-23)

## Scope and method

Contests in series whose header `region` is Latin America, that ran (no `status: upcoming`) and have no
source with a role in scoreboard / frozen_scoreboard / standings / rankings / teams: **63 contests**
(list: `work/targets.json`, per-contest outcome: `data.json` → `targets`).

For each, in this order (rerun with the scripts in `work/`):

1. **CMS**: the 2026-11-13 fetch of every CMS standings page (`archive/icpc-global-standings/index.csv` +
   `standings/<file>`), and the `externalStandingsUrl` / `url` the CMS records for the contest
   (`work/cms_fetch.json`, `work/cms_ext.json`). Rows with problems solved → `standings` (the
   `drop_icpc_standings.py` rule).
2. **Our holdings**: the website crawls under `archive/<series>/<contest>/website/` (`work/arch.py SERIES REGEX`
   prints every held page whose URL matches).
3. **Combined boards**: scorelatam.naquadah.com.br (subbr-YYYY, subch-YYYY), counted official teams per
   country (`/AR`, `/BO`, `/CL` logins) and matched them against the CMS row counts and winners.
4. **Organiser domains via Wayback CDX** (`work/cdx.sh`, `work/fetch.sh`, retrying; the Archive was
   "Temporarily Offline" twice during the run): coj.uci.cu, matcomgrader.com, acis.org.co,
   icpc-bolivia.edu.bo, wiki.icpc-bolivia.edu.bo, icpc.coderoad.com, cidi.uaq.mx, torneo-programacion.cl,
   icpc.tec.siua.ac.cr, the old icpc.baylor.edu finder and ViewRegionalStandings pages.
5. Two Spanish web searches (Torneo Chileno 2018) — nothing.

Every accepted page was opened (live, Wayback, or our copy) and checked to be this edition: title/date,
and where the CMS has rows, the winner and the team count agree with the CMS.

## Result

- **57 of 63** contests now have a result source (54 by my ops; 2 — colombia-maraton-2026, tap-2026 — got
  the same CMS page from another agent in the worktree update of 08:56, so my two ops were dropped;
  central-america-1997 got a champion-only `rankings` from another agent, so my role op for it was dropped).
- **6 still have nothing**: bolivia-national-2009, bolivia-national-2013, bolivia-national-2020,
  central-america-2008, gran-premio-centroamerica-2021, torneo-chileno-2018 — what was tried is in
  `data.json` → `targets.<id>.not_found`. None of them is in doubt as to existence: each has a CMS entry
  with registered teams (that indicates, not proves, that it ran), and Bolivia 2009 also has a held
  organiser page listing the teams that qualified from it.

## What `ops.json` does (105 ops, all `ok` in `--check`)

| kind | ops | contests |
| --- | --- | --- |
| CMS standings page (`.../finder/<abbr>-<year>/standings`) with rows → `standings` | 40 | bolivia-national 2015-2019, 2021-2023; caribbean-national 2013-2017, 2019; colombia-maraton 2009-2013, 2015, 2018; gran-premio-centroamerica 2019, 2020, 2023, 2024; gran-premio-mexico 2020, 2022-2025; tap 2012, 2013, 2016-2019, 2021, 2022; torneo-chileno 2017, 2019 |
| combined first-phase BOCA board on scorelatam, with `scope` = country section → `scoreboard` | 7 | tap-2021 & tap-2022 (Argentina), bolivia-national 2022/2023/2025/2026 (Bolivia), torneo-chileno-2023 (Chile) |
| scorelatam board of the edition → `scoreboard` | 1 | torneo-chileno-2025 (subch-2025) |
| Caribbean Online Judge / MatCom grader standings (named by the CMS) → `scoreboard`, Wayback `as_of` | 7 | caribbean-national 2013-2019 (2018 had no CMS rows: this is its only result) |
| ACIS results pages → `scoreboard`, Wayback `as_of` | 8 | colombia-maraton 2008-2013, 2018; south-america-north-2008 (a contest-day "preliminary" board, see D7) |
| Bolivian per-site first-phase boards, `scope` = site, held in our crawls | 25 | bolivia-national-2010 (13), -2011 (12) |
| other organiser boards | 5 | bolivia-national-2014 (icpc.coderoad.com BOCA, as_of 2014-09-24), -2021 (icpcranks BOCA copy named by the CMS), -2026 (icpcbolivia.org Fase 1 and Fase 2 scoreboards + consolidated standings) |
| first-phase results pages (qualifiers per site) → `rankings`, like 2008-2016 | 3 | brazil-first-phase 2005-2007 |
| south-america-1997 → the CONSUN'97 results page as `standings` | 1 | see D3 |
| missing dates read from official pages (+ provenance line each) | 8 | bolivia-national-2011 = 2011-09-24; brazil-first-phase 2005 = 2005-09-10, 2006 = 2006-09-09, 2007 = 2007-09-22 |

Where a CMS board and a better board both exist (e.g. caribbean-national, colombia-maraton 2009-2013,
bolivia-national-2021/2022/2023, tap-2021/2022) both are added: the CMS page is the official result, the
board raises the level to scoreboard.

## Items for discussion

**D1. Uncited CMS standings pages with rows — make it a mechanical pass?**
40 of my 63 contests had a CMS standings page that the 2026-11-13 fetch shows with ranked rows and
problems solved, yet the contest cited only the finder page as `web` (or nothing). The same holds for
**124 more contests** in all regions (79 Latin American incl. mine; e.g. nordic-2013 `Nordic-2014`,
neerc-2013, swerc-2013, all the `*-2013` regionals, mongolia-national 2013-2018, taiwan-ncpc 2012-2016,
oman-* 2025-2026) — list in `data.json` → `cms_standings_with_rows_not_cited_outside_targets` (computed
against the worktree before the 08:56 update). *Implies*: coverage undercounts results for ~160 contests.
*For a tool pass*: the rule already exists (`drop_icpc_standings.py`), the fetch is held, no judgement
needed. *Against*: the CMS can be wrong, and some pages may mix outside teams. *Recommendation*: run one
pass that adds every finder standings page whose fetch has rows (filed by content), then let
`bake_icpc_standings.py` make the copies; I did only my 40.

**D2. Bolivia: one contest, several phases — model as scoped sources?**
The "Bolivia Preliminary Contest" of the CMS is a multi-phase national competition. 2009-2011: *primera
fase* (national eliminatory, at 9-13 sites; the CMS contest) and a second phase that is the Bolivian site
of the Latin American regional (not this contest). 2026: Fase 1 (29 Aug, on the Brazilian first-phase set,
also on scorelatam subbr-2026), Fase 2 (19 Sep, own set) and a consolidated ranking that decides who
advances (icpcbolivia.org/competencias/consolidado/2026/). *Implies*: either one contest with phase- and
site-scoped sources (what my ops do), or extra contests for phases. *For one contest*: the CMS has one
entry and one set of advancing teams; the consolidated standings are the result. *For splitting*: Fase 1
and Fase 2 used different problem sets (two sets for one contest). *Recommendation*: keep one contest,
scoped sources; record the two problem sets later if wanted. Examples: bolivia-national-2026,
bolivia-national-2010 (13 site boards), bolivia-national-2011 (12).

**D3. south-america-1997 and brazil-first-phase-1997 are the same event.**
Both are 13 Dec 1997 at Unicamp. The CONSUN'97 results page
(https://maratona.sbc.org.br/hist/1997/result.html, our copy
`brazil-first-phase/brazil-first-phase-1997/standings/20261023-live-44de29ad/result.html`) ranks PUC-Rio,
UFPE, Universidad de Buenos Aires ... and lists teams from Argentina, Chile, Colombia and Venezuela; the
1997 history page says PUC-Rio was the only South American team to qualify for the 1998 World Finals.
So the "1997 Brazil first phase" is the 1997 South American regional. *Implies*: a duplicate contest.
*Option A* keep south-america-1997 (parent wf-1998) and drop brazil-first-phase-1997 (to
cms-triage/non-mainline, or `subset_of`). *Option B* keep both and say so in notes. *For A*: one event, one
contest. *For B*: the Maratona history counts it as a Maratona edition. *Recommendation*: A; I only
added the results page to south-america-1997. (brazil-first-phase-1996, 1996-11-28, parent None, probably
needs the same look; not checked.)

**D4. Per-site boards: cite each one?**
For Bolivia 2010/2011 I added every site board (no combined board exists). For Brazil 2005-2007 I added
only the organiser's first-phase index page (as `rankings`, like the 2008-2016 pages), although our crawls
hold the site boards (2005: 27 pages, 2006: 43, 2007: ~40 site folders — `data.json` →
`brazil_first_phase_2005_2007_site_boards_held`). *For citing all*: each is a scoreboard; together they
are the whole contest at scoreboard level. *Against*: dozens of sources per contest, many are
runs/stat pages to sort out. *Recommendation*: cite them in a follow-up from the held crawls with a
small tool (board pages only, `scope` = site), not by hand. Related: Bolivia 2009's
`clasificados_final_2009.html` (teams qualified from the 2009 phase, unranked) — `rankings` with scope
"qualified teams", like the Brazilian pages? I left it out.

**D5. Combined first-phase boards filed on the Brazil finals (cross-area, for the source-wrong agents).**
brazil-2020 … brazil-2025 (the Brazilian *finals*) cite scorelatam subbr-2020 … subbr-2025, which are the
*first-phase* boards; brazil-first-phase-2020 … -2023 do not cite them. Likewise brazil-2005/2006/2007 cite
`hist/<year>/primeira-fase/` as a problem set of the finals. *Recommendation*: move them to the
brazil-first-phase contests (I did not touch them).

**D6. Dates and names to check (not changed).**
south-america-north-2008: catalogue 2008-11-30, the ACIS page says the regional was 15 Nov 2008 (CMS
2008-11-14). bolivia-national-2025: catalogue 2025-09-12, while its teams are on the 2025-09-13 Brazilian
first-phase board (the board prints no date). tap-2021 has no date; its teams are on subbr-2021
(Brazilian first phase 2021-10-30), but the board prints no date. colombia-maraton-2026 is named "XXXIX"
in the catalogue, the CMS now says "XL" (2008 = XXII, so 2026 = XL).

**D7. Two sources with caveats.**
south-america-north-2008's only result is ACIS's "Resultados preliminares al 15/11/2008 6:00pm"
(contest-day board, Colombia + Venezuela). bolivia-national-2010's Cobija board has 9 problem columns,
nobody solved anything and the teams are "Grupo 1-5" — the organiser's homepage links it as Cobija's
result, so it is included, but it may be a warm-up. Drop either if you prefer.

## Not done / blocked

- The six contests above remain without results.
- Wayback was offline twice; one CDX (icpc-dbf35.netlify.app, GP Centroamérica 2021) failed and should be
  retried.
- The worktree was updated at 08:56 while I worked; all ops were re-checked against it (105 ok).
