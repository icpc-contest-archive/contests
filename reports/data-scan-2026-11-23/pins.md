# Data scan 2026-11-23 — agent `pins`: `as_of` missing or naming another edition's snapshot

Area: sources at an address that serves each year's edition in turn (ruling 16). Three groups:
**year-reused** (the content check's list `data/content-check/run-2026-11-15/lists/year-reused.json`, 339 items),
**seerc** (`acm.ro/results.htm` and the SEERC home pages), and **nerc-subregion** (the 287 citations of
`neerc.ifmo.ru/subregions/*.html` / `nerc.itmo.ru/subregions/*.html`, 263 of them without `as_of`; added to my area by
the coordinator from web-b's D1).

Rule applied: pin `as_of` to a snapshot whose page shows this edition (I opened it and read the year or date); drop a
wrong pin and keep the source as lost when the address was the contest's but no snapshot shows the edition; remove
nothing (the removal cases are discussion items).

## Output

`ops.json`: **265 ops, all `ok` under `tools/apply_scan_ops.py --check`** (re-run at the end against the moving worktree).

| group | set `as_of` (re-pin / first pin) | unset `as_of` | append (new source) |
|---|---|---|---|
| year-reused | 63 (32 / 31) | 20 | 0 |
| seerc | 1 (0 / 1) | 1 | 4 |
| nerc-subregion | 176 (0 / 176) | 0 | 0 |

`data.json`: every one of the 339 year-reused items with outcome and evidence (`year_reused`), the SEERC table
(`seerc_acm_ro_results`), every NERC citation (`nerc_subregion`, with what was tried for the unpinned ones), page
dates that differ from the catalogue, sources whose held copies are of another time than the new pin
(`recapture_after_as_of_changes`, 240), and `unrelated_pages_listed_as_year_reused` (46).

## How (rerunnable, all in `work/`)

1. `build.py`: joins the year-reused list with the worktree (current `as_of`, roles, copies), the cached
   `wayback-history.json` of `tools/wayback_history.py` (all 339 year-reused items studied, 139 "picks"), and every
   op in `../../applied-*.jsonl` (what wave 1 already did) → `items.json`. 26 items were already gone (moved or
   removed by sr-wrong/urls), 43 had been handled by wave 1, 270 were left.
2. `verify.py` + `show.py`: fetched every pick and every current pin (`https://web.archive.org/web/<ts>id_/<url>`,
   one request per 1.2 s, cached in `work/cache/`) and printed title, head and the text around the year. I read each;
   the decisions with quoted evidence are in `decisions1.py`.
3. `explore.py` + `showx.py`: for the unresolved ones, the CDX (distinct digests), then up to 5 captures in the window
   (200 days before the contest to 60 days before the next edition; post-contest first), and the frames of framesets
   → `decisions2.py`, `decisions3.py`.
4. SEERC: CDX of `acm.ro/results.htm` (32 distinct captures); every capture 2003-2025 opened and compared with the held
   boards (`seerc.icpc.global/<year>/results.htm`, icpc.baylor.edu copies) → `seerc.py`.
5. NERC: `nerc_cdx.py` (CDX of the 18 pages on both hosts), `nerc_verify.py` (per citation, same-host captures in the
   window; the "Contest ... took place / will take place ... on <date>" or "Contest Dates:" line must name the
   contest's year; up to 3 captures), `nerc_build.py`. All 176 pins were printed and read (`nerc_rows.json`).
6. `build_ops.py` → `../ops.json`; `build_data.py` → `../data.json`.

The `wayback_history.py` picks were not taken blindly: 14 of its 137 were wrong (item 7).

## What the ops fix

**A. year-reused, re-pinned (32) or pinned for the first time (31).** E.g. acpc-2000 (1998 page → "ACM Arab and
North-African Regional Programming Contest 2000"), kanpur-2000/2001/2002 and kolkata-roorkee-2003 (all pinned to the
2000 page → each year's own page), ncna-2002..2010 (8), mcpc-2000/2001/2002 (web and the chief judges' page),
socal-2001/2002/2003, pacnw-2001/2002, ecna-2002/2003, tehran-2001/2002/2003, cerc-2004/2005, central-america-2001
(web and problems)/2002/2005, amritapuri-2015, chengdu-2010 (title 2010年ACM国际大学程序设计竞赛亚洲预赛成都赛区,
2010 nian ACM guoji daxue chengxu sheji jingsai Yazhou yusai Chengdu saiqu, "2010 ACM ICPC Asia Regional, Chengdu
site"), chennai-2016, singapore-2007/2015, pakistan-2014/2015, poland-2009, manila-2002, bapc-2010, mausa-2000 and
-2025, south-africa-2002/2005, west-neerc-2008, south-russia-2002, seerc-2001 (problems; cs.pub.ro frameset),
seerc-2002 (acm.ro home: 2014 pin → the 2002-2003 home page), scusa-2023, burkina-faso-2016 (Mapcom dashboard
listing "The 2016 Burkinabe Collegiate Programming Contest"), thailand-2019 (see item 3).

**B. year-reused, wrong pin dropped, kept as lost (20).** No capture shows the edition: amritapuri-2016 problems,
bapc-2021 scoreboard (only a 2024 test-session capture), central-america-2005 problems (every capture predates the
contest), cerc-2008 solutions (only CERC'10), ecna-2000 (frames never archived), jordan-2011, mausa-2003 problems,
moscow-2021 standings (Wayback never captured that URL), nena-1997, nwerc-2018 scoreboard (empty reply, then the 2019
board), poland-2025 ranking (the 2024 ranking before the contest, JS shells after), seerc-2000, seerc-2003 home,
south-africa-2003, south-america-2000/2001, taiwan-2000/2001, xian-2022/2023 (pinned to a 2020 app shell).

**C. Checked and right, no op (41).** socal-2007..2023 (17), south-africa-2009..2017 (7), cerc-2000/2015/2016,
germany-2012/2015, kanpur-2024, hungary-2022, nwerc-2011, pakistan-2018/2023, … (`data.json`).

**D. SEERC `acm.ro/results.htm` (6 ops).** The wave-1 state was checked capture by capture: 2003, 2005, 2006, 2008,
2010, 2014, 2016, 2018, 2020, 2022, 2023, 2024 are right; 2009, 2012, 2015 rightly lost.
- **seerc-2017 unset.** Wave 1 disagreed (sr-wrong unset it, urls pinned 20171024044705; urls' op is what is in the
  worktree). That capture is headed "2017 ACM SEERC: Results" but its table (1 LNU AlgoTesters 8/1196,
  2 UzhNU_MagicalPony 7/1325) is the 2016 board, identical to `seerc.icpc.global/2016/results.htm`; SEERC 2017 was
  won by Echipa Lacheta 10/1348.
- **seerc-2021 pinned** to 20220226192513: an Excel frameset whose frame `Rezults 2021 N0v.fld/sheet001.htm` reads
  "ACM ICPC 2022 SEERC Real Tour"; that frame is **added** as a `scoreboard` source (@20211203131858).
- **Added** `acm.ro/results.htm` to seerc-2002 (@20030505015253, the October 19, 2002 final standings),
  seerc-2007 (@20080430102928, "Bucharest, October 25-28, 2007") and seerc-2011 (@20111120170605, "Summary - ACM SEERC
  2011"). Not added: `acm.ro/problems.htm` @2003-05 (the 2002 set; today held only as seerc-2003's wrong copy).

**E. NERC subregion pages pinned (176).** Each pinned capture's text names the edition ("Armenia subregional contest
took place in Yerevan on October 31, 2004", "Contest Dates: November 4-5, 2023", "Contest Dates: 15 Nov, 25", …);
157 are captures after the contest, 19 are the edition's announcement before it. The 24 already pinned were all
checked and are right. Left unpinned: 45 with no capture in the window, 22 whose captures do not show the edition
(the 2017 pages read "will take place in <city> in ." with no date; the 2020 pages have no contest line; taurida-2024
has only a 2023 page), 17 current (2026) editions whose live page shows them now. azerbaijan-2006/2007 and
north-russia-2002 are counted in group A.

## Items for discussion with Fredrik

**1. Addresses that seem never to have served the edition: remove, or keep as lost?** Ruling 16 removes only when
nothing shows the address ever served it. Four come close: gwalior-2014 `icpcgwalior.org/doc/OnsiteProblem.pdf` (its
only capture, the day after the contest, is "The 2013 ACM ASIA Region Programming Contest Kanpur Site Onsite Contest
Problems"); amritapuri-2016 `icpc.amrita.ac.in/problems/` (only capture, half a year later, is a 2013 practice
session); mausa-2003 `midatl.cs.vt.edu/problems/` (two months after the contest it still lists 1997-2001 only);
central-america-2005 `Problems.html` (every capture before the contest; probably the 2004 set). For removing: the
captures are direct evidence of what the address held around the contest. For keeping: a few captures do not prove
absence. Recommendation: gwalior-2014 is another contest's document (move it to kanpur-2013, which the PDF names, or
remove it); the other three stay lost (done here).

**2. A heading of this edition over another edition's content.** seerc-2017 (2017 heading, 2016 table), taiwan-2007
`final_standings.htm` (2007 header, 2005 table, sr-wrong D6), south-africa-2003 (frameset titled 2003, content frame
still the 2002 page). Question: does "shows this edition" mean the content or the label? Content: the pin is evidence
of results, and these would cite another year's board. Label: the organisers meant the page for this edition.
Recommendation: content wins; none of these is pinned (seerc-2017 unset).

**3. Framesets and JS shells as the snapshot of a `web` source.** I pinned framesets where the replayed frames show the
edition (mausa-2000, seerc-2001, seerc-2021, south-africa-2002/2005) and one app shell whose only text is its title
"ACM Thailand 2019" (thailand-2019). Shells were not pinned for results roles (poland-2025 "AMPPZ 2025",
icpc.nwpu.edu.cn). For counting a shell: it is the edition's own site at that moment. Against: nothing in it can be
read. Recommendation: frames yes; a title-only shell for `web` only, never for results.

**4. Pages in the year-reused list that were never a contest site (about 15 of the 46 in data.json).** University
homepages and news (benin-2019 uac.bj, mongolia-national-2013/2014 news.num.edu.mn, togo-2019 cic.univ-lome.tg,
ukraine-2021 vntu.edu.ua), a personal profile (bolivia-national-2009/2010 derechoteca.com), library pages
(scusa-1989/1990/1994 texashistory.unt.edu, socal-1994 UCLA Daily Bruin guide), social and blog indexes
(saudi-arabia-2023 x.com/SaudiCPC, turkey-2010 codeforces.com/blog/inzva), bulgaria-2010 (the Romania contest's call
for participation). No snapshot can fix these. Recommendation: remove them in a role/criteria pass (outside "pins";
not done). The rest of the 46 are real contest addresses whose crawl caught the wrong page (amrita.edu/icpc,
cs.rit.edu/~icpc, Clarkson ACM club, ifmo.ru/neerc …): they stay lost.

**5. Current-season sites that skip an edition in Wayback.** The 2025 NA regionals (rm/sc/nc/ne/ec.na.icpc.global for
rmc, scusa, south-na, ncna, nena, east-na, ecna-2025) and socal-2025 (`socalcontest.org/current` still read
"2024/2025 Contest: 16-Nov-2024" in October 2025): every capture is the 2024-25 page until the 2026-27 page appears,
so they are lost by the rule. Options: (a) cite the sites' own archive pages ("Archive 2025 – 26") as new sources;
(b) capture current-season reused addresses ourselves after each contest (Save Page Now), so this stops happening.
Recommendation: both; (b) as a standing step of the capture rounds, starting with the 17 NERC 2026 pages.

**6. Dates on the NERC pages that differ from the catalogue (16, `nerc_page_dates_differ_from_catalogue`).** Mostly a
day (announced vs. held), but three are larger: georgia-2022 page "December 20, 2022" vs 2022-11-20, kazakhstan-2022
"October 29, 2022" vs 2022-10-01, far-east-russia-2015 "October 31, 2015" vs 2015-11-14. For the dates owner;
recommendation: check against the standings pages before changing anything.

**7. `wayback_history.py --decide --write` is not safe to run as it is.** Its test is "the year appears in the text".
14 of its 137 picks were wrong: south-america-2000 (the 1999 page mentions the "2000 ... Finals"), university news
sites that mention the year (benin-2019, mongolia-national x2, togo-2019, ukraine-2021), bulgaria-2010, a pre-contest
page for a problem role (mcpc-2002 judges' page), a JS shell (poland-2025), and the stale 2024-25 pages (ncna, rmc,
scusa, south-na, socal-2025). Recommendation: do not run `--write` on run-2026-11-15 (use these ops); if the tool is
kept, require the year in the title or a date line, and a post-contest capture for results and problem roles.

## Not done / limits

- Year-reused items with no `as_of` and no capture in the window (109) were left as they are (already lost); captures
  after the window were not searched.
- south-russia-2001 `contest.sgu.ru` @20011203180939 shows "Final Standings ... The contest is over" for an 8-problem
  contest with no name or year (maybe the 2001 Southern subregional): not pinned.
- vietnam-national-2025 (non-ASCII address; Wayback answered 400) not checked.
- 240 sources hold copies of another time than their new pin (`recapture_after_as_of_changes`): for the capture rounds.
- Wayback was slow (many 20 s timeouts); at most one request per 1.2 s. Nothing was written outside `findings/pins/`.
