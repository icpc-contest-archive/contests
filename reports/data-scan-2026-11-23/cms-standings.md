# cms-standings — CMS standings pages with rows that the catalogue does not cite (data scan 2026-11-23)

## What I checked and how (rerunnable)

Scripts in `work/`, run from the worktree root (`_scan-2026-11-23/contests`), in this order:

1. `scan.py` — for every catalogue contest and each of its `cms_ids`: the page's slug from `data/cms-shortnames.json`
   (cross-checked against the slug the regionalresults tree gives in `archive/icpc-global-standings/index.csv`;
   they agree for all ids but nerc-2020, which already cites the right page), the rows of the 2026-11-13 fetch
   (`archive/icpc-global-standings/standings/<file>`), the rows in the four API dumps, and whether the contest (or
   another contest) cites that address. 2,336 (contest, cms id) pairs; 1,518 with rows.
2. `pending.py` — every CMS address in the other agents' `ops.json` (not yet applied), so I do not add what they add.
3. `live.py` — asked the open API (`/api/contest/public/search/contest/<id>?q=&page=N&size=1000`, 1 request/s) on
   2026-11-23 for every candidate, and for every uncited page that was empty on 2026-11-13 but may have filled
   since (current season, upcoming, new ids). Raw answers in `work/live/<id>.json`.
4. `winners.py` / `compare.py` — the contradiction check: for every candidate, the CMS top 5 against every other
   held result copy (archived scoreboard/standings/rankings): position of the team names, and (fallback) the
   rank-1 solved/time pair; plus the source descriptions (`data/source-descriptions/`) for team counts and winners.
5. `inventory.py` — every source on a `regionals/finder/` address (icpc.global and icpc.baylor.edu), with role,
   the cms id its slug belongs to, and whether that is the contest's own id.
6. `build_ops.py` — writes `ops.json`. Checked with `tools/apply_scan_ops.py --check`: **112 ok, 0 failed**.

Classification follows `tools/drop_icpc_standings.py`: rows with problems solved → `standings`; ranks only →
`rankings`; neither → `teams`. The slug is always the one that belongs to the contest's own cms id (never
abbr + year built by hand).

## Counts

- Uncited CMS standings pages with rows: **121** pages. Of these
  - **86 added by my ops** (84 contests; below),
  - 25 are already in other agents' pending ops (results-afar-asia: malaysia/mongolia/myanmar-2017/oman/taiwan-ncpc
    2012-2015/thailand; results-na: nena-atlantic/central/north/west-2013) — not duplicated,
  - 10 are regional pages under a division contest (`east-na-2024/2025`, `south-na-2022..2025`) whose regional view
    (`subset_of`) already cites them — left alone, see D1.
- Live API on 2026-11-23 = the 2026-11-13 fetch for all 86 (same row counts, same kind).
- Uncited pages that were empty on 2026-11-13 and asked again: 95; none has rows now that is not already cited.
  (gny/nena/ecna/seusa/scusa-2026 and 14 more autumn-2026 pages, cited by the current-season agent, were empty in
  the fetch and have rows now; they need `topup_icpc_standings.py` before baking.)
- Winner contradictions found: **none** (details below).

## What `ops.json` does (112 ops)

**A. 86 appends — new CMS standings sources** (`note: found by the data scan 2026-11-23 (icpc.global CMS standings, N rows)`;
evidence names the API answer, the row/rank/solved counts, rank 1, and the fetch file):
- 85 `standings`, 1 `teams` (myanmar-mcpc-2019: 66 rows, no ranks, no problems solved).
- Scoped: taiwan-ncpc-2016 (two CMS contests: *Taiwan NCTU … for Technology Universities*, *Taiwan NCPU … for
  Private Universities*), vietnam-national-2014 cms 2717 (*First Round*, as the existing Gym source is scoped).
- Contests: aec-2025; bapc-2013, bapc-prelims-2013; bolivia-national-2024; brazil-first-phase-2009…2025 (17);
  caribbean-national-2020/2021; cerc-2013; changchun-2013; changsha-2013; colombia-maraton-2014/2017/2019/2021;
  ctuo-2013; ecna-2013; euc-2026; gny-2013; gran-premio-mexico-2015…2019; kuala-lumpur-2014 (the *Onsite* CMS
  contest; the regional's own id 2607 is empty); lethbridge-2013 (solved + time, no ranks); malaysia-national-2018/2019;
  myanmar-mcpc-2018/2019; neerc-2013; nena-east-2013; nordic-2013, nordic-2025; nwerc-2013; pacnw-2013;
  philippines-national-2014; rmc-2013, rmc-2021; romania-2013; scusa-2013; seerc-2013; socal-2013; south-pacific-2013;
  swerc-2013; taiwan-ncpc-2016 (2); tap-2015; ukiepc-2013; ukraine-2013; uzbekistan-2019; vietnam-national-2012,
  2014 (2), 2017…2025; wf-1999…2005, wf-2014 (WF 2006–2025 already cite their finder pages).
- Contests that had no result source at all before: bapc-prelims-2013, brazil-first-phase-2011/2012,
  vietnam-national-2012. Up to `standings` from a lower level: ecna-2013, philippines-national-2014,
  taiwan-ncpc-2016, tap-2015.
- After applying: `tools/topup_icpc_standings.py` (aec-2025, euc-2026, nordic-2025, vietnam-national-2023 are not
  in the dumps) and `tools/bake_icpc_standings.py --write`.

**B. 25 ops — CMS pages filed as `web`** (the coordinator's extra item; the list is web-a's `cms_finder_pages_filed_web`,
and my own inventory finds exactly the same 25):
- 18 `remove` — bare finder pages `…/regionals/finder/<slug>` (17 icpc.global + 1 icpc.baylor.edu). I opened
  `https://icpc.global/regionals/finder/Bolivia-Preliminary-2025` in a browser: it is the CMS's contest info page
  (schedule, sites, billing, sponsors, "See Teams" / "See Standings" links), no rows. Not `web` by ruling, and not a
  results page, so not a source. For each, the evidence lists the contest's own `/standings` page and whether it has
  rows and is cited (already cited / added by A / pending in results-afar-asia), or is empty. Contests:
  bolivia-national-2024/2025/2026, colombia-maraton-2019/2026, gran-premio-centroamerica-2019/2020/2021/2023/2024,
  gran-premio-mexico-2019, south-america-south-2014 (baylor), thailand-national-2012/2014/2026,
  torneo-chileno-2023/2025/2026 (`finder/TCP`, no year: no CMS id has that slug).
  Empty standings for: bolivia-national-2025/2026, gran-premio-centroamerica-2021, thailand-national-2026,
  torneo-chileno-2023/2025/2026 (API asked 2026-11-23: 0 rows). These contests lose a `web` source and keep none
  from the CMS.
- 6 `set roles [web] → [teams]` — `…/finder/cnc-YYYY/teams` for caribbean-national-2014…2019. I opened them in a browser:
  a site selector over per-site team lists (institution, team, members), e.g. cnc-2019/teams/cuban-finals lists
  100 teams. The API gives `showTeamsInPublicPages: true` for all six. caribbean-national-2018 has no CMS standings
  rows, so this becomes its CMS result (`teams`).
- 1 `remove` — `cnc-2014/teams` (caribbean-national-2013): the CMS hides that edition's teams
  (`showTeamsInPublicPages: false`; the page shows "No data" for every site). Its `/standings` (132 rows) is cited.
- Not done: I did not open the bare icpc.baylor.edu finder page itself (the Wayback Machine was unreachable from
  both shells at the end of the run). Its sibling `/standings` capture shows the old finder's Info/Standings tab
  layout. If you want that removal backed by its own snapshot, drop op #104.

**C. 1 `set as_of`** — south-america-south-2014, `icpc.baylor.edu/regionals/finder/southamerica-south-2014/standings`:
`20190917071919` → `20150309092804`. The 2019 snapshot (1,064 bytes) is the icpc.global app shell. Our copy of the 2015
snapshot shows "Standings for The 2014 ACM-ICPC South America/South Finals".

## Contradiction check (the CMS against other held results)

76 of the 86 pages have at least one other held result copy with text (84 pages have ranked rows to compare). On 59 the
CMS rank 1 is confirmed first by at least one copy: e.g. cerc-2013 (Comenius 9/1054, report + ranking),
nordic-2013 (Omogen Heap), neerc-2013, swerc-2013, wf-1999…2005/2014 (cphof / results pages). The mismatches the
script flagged all have other causes:
- site-only boards (Brazil first-phase site PDFs, a café-com-leite board);
- copies without the table: JS shells (xcpcio aec-2025, scoreboard.euc.icpc.global, ukiepc.info, acis.org.co 2017),
  a scanned PDF (malaysia-national-2018), the iteso.mx Gran Premio pages now showing the 2025/2026 menu;
- the old `icpc.baylor.edu/icpc/finals/Standings.html` copies of another WF edition (already known from wave 1);
- two Gym mirrors (see D6).
The 17 without a confirming copy (aec-2025, bolivia-national-2024, brazil-first-phase-2010/2013/2014/2015,
colombia-maraton-2017, euc-2026, gran-premio-mexico-2015…2019, malaysia-national-2018, ukiepc-2013,
vietnam-national-2014 ×2) are all in the first three groups above or D6, so nothing confirms or contradicts the
CMS there. Across the 76 pages, no copy names a different winner. `data.json` → `winner_checks` has every verdict.

## Items for discussion with Fredrik

**D1. Division contests carry one region's CMS standings, unscoped.**
- *Question:* should a division contest (`east-na-*`, `south-na-*`) cite its regions' CMS standings pages at all?
- *Implies:* today each cites exactly one region's page with no `scope`, so the site reads it as the division's
  standings: east-na-2024 → `Northeast-North-America-2025`, east-na-2025 → `East-Central-NA-2026`,
  south-na-2022 → `Mid-Atlantic-USA-2023`, south-na-2023/2024/2025 → `Southeast-USA-2024/2025/2026`,
  south-na-2026 → `Mid-Atlantic-USA-2027`. The other regions' pages (10, list in `data.json`) sit only on the
  regional views (`subset_of`).
- *For dropping them from the division:* the regional view *is* that part of the division. Coverage dedupes along
  `subset_of`. Every division has its own full board (Kattis / east.na).
- *For keeping them, each with `scope: <region>`:* a page holding part of a contest is its source with a scope
  (taiwan-ncpc groups, vietnam first round), and the division would show all its CMS results.
- *Recommendation:* drop them from the division contests (current-season recommended the same). I made no op.

**D2. wf-2006: the CMS standings page has emptied.**
- *Question:* keep `World-Finals-2006/standings` as a source?
- *Implies:* the API answers `[]` for cms 1092, both on 2026-11-13 and 2026-11-23. The 2026-04-26 dump has 83 rows,
  and our copy (`wf/wf-2006/standings/api-20261113/`) was rendered from that dump. No other cited CMS page has lost
  its rows.
- *For keeping it:* a source is an address at a time, and we hold the copy.
- *For removing it:* "an empty CMS page is not a source".
- *Recommendation:* keep it, pinned to the dump time, with a note that the CMS emptied it. Pass a contest only to
  `icpc-standings-empty.json` when it never had rows.

**D3. kanpur-2022 and mathura-2022 look like one contest** (raised by urls/archive in wave 1; new CMS evidence here).
- kanpur-2022 cites `ICPC-Mathura-2023/standings`, the page of cms 5649 (mathura-2022, 144 rows). Its own page,
  `Asia-Kanpur-2023` (cms 5647), is empty (API asked 2026-11-23).
- In the CMS, 5647 "The 2022 ICPC Asia Kanpur Regional" is the parent of 5648 "Kanpur Preliminary". 5649 "The 2022 ICPC
  Asia Mathura Kanpur Regional" is a sibling of 5647 under 5637. Both contests carry date 2023-04-09 and the same
  problem set.
- *Recommendation:* merge into one contest that holds both cms ids. The page then belongs to it. Until then, no op
  (removing the page would leave kanpur-2022 with no result).

**D4. CMS `/teams` pages as `teams` sources.**
- *Question:* keep a CMS team-list page beside the same contest's CMS standings?
- *Implies:* I set six caribbean `/teams` pages to `teams` by content, as instructed. The CMS has such a page for
  every contest, so the same logic could add thousands.
- *Against adding more:* where the standings have rows they add nothing.
- *Privacy:* the pages list member names. Our CMS copies are rendered team-level only, and the capture rounds would
  store only an app shell.
- *Recommendation:* keep `/teams` only where the CMS standings are empty (here caribbean-national-2018). Otherwise
  leave them out; for caribbean-national-2014…2017/2019 that would mean removing them later.

**D5. CMS rankings that are not plain ICPC order (filed as `standings` anyway).**
- gran-premio-mexico-2015…2019: the ranks are not in solved/time order, so this is a cumulative Gran Premio ranking.
  In 2015, rank 1 has 25 solved / 6779 min and rank 2 has 25 / 5110. In 2015/16 only 106/120 rows of 319/508 are ranked.
- vietnam-national-2014 first round (cms 2717): the ranks start at 32.
- brazil-first-phase 2009-2011 and 2013-2015: per-site ranks (several rank 1s), only 52-90 rows ranked.
- *Recommendation:* fine as `standings` (the rows give problems solved). A short note on the source would help a
  reader; tell me if you want those notes.

**D6. By-catch outside my area: two Gym mirrors filed as official boards.**
- bolivia-national-2024 `clist.by/standings/2024-2025-icpc-bolivia-pre-national-contest-53746608/`: 329 handles,
  international. The CMS winner (Perritos Malvados, UMSS) is not on it.
- vietnam-national-2014 `codeforces.com/gym/100499/standings/` (scope First Round): the top rows are foreign teams.
- By the 2026-11-14 criteria these do not count, because official teams are not distinguishable.
- *Recommendation:* pass them to the source-roles agent.

**Small data fixes not expressible as ops.**
- `data/icpc-standings-empty.json` stores the wrong address for three contests: gwalior-pune-2021 (stored
  `ICPC-Gwalior-Pune-2021` = cms 4500; own `ICPC-Gwalior-Pune-2022`), kharagpur-2020 (stored `Kharagpur-2020`; own
  `Kharagpur-2021`) and kanpur-2022 (stored `ICPC-Mathura-2023`; own `Asia-Kanpur-2023`). All three own pages are
  still empty (asked 2026-11-23).
- Not an error: the four icpc.baylor.edu `/standings` sources (korea-2009 `seoul-2009`, mcpc-2012, mcpc-2014,
  south-america-south-2014) have slugs that map to the previous year's cms id under today's scheme. The old site used
  abbr-*contest year*, and our captures show the right editions. A slug check must skip icpc.baylor.edu.
- wf-1999 and wf-2001 will have two icpc.global addresses with the same CMS rows (`community/results-YYYY`, already
  cited, and the finder page). Both are real pages; I left both.
