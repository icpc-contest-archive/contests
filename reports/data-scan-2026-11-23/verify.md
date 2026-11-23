# Independent check of the data scan 2026-11-23 — sampled applied changes

Checker: verify (did not make any of the changes). Read-only on the worktree and archive; network reads only (live pages, Wayback `id_` snapshots and CDX, icpc.global API, Google Groups, CONTENTdm, CodeChef, HDU, Kattis). No git.

## Sample

- `random.seed(23)`; for each of the 23 `applied-*.jsonl` files in sorted order, `random.sample(eligible, 4)`; then 10 more from the rest of `applied-la.jsonl`: **102 ops** (the brief's "about 70" assumed fewer files; 23×4+10 = 102).
- Eligible = every logged op except provenance appends (path ends in `provenance`) and ops whose `_result` is `unchanged` / `already present` (they changed nothing). 12,251 eligible ops in all.
- Each op was judged on the catalogue as it now is in the worktree (e.g. for Live Archive links, the final url + as_of after both the url and as_of ops), against the page the evidence cites or a held copy. Scripts: `work/sample.py`, `work/fetch_la.py`, `work/fetch_wb.py`, `work/show.py`, `work/verdicts.py`, `work/build.py` (rerun `python3 work/sample.py` from `_scan-2026-11-23/` to reproduce the sample).

## Result

- **99 CORRECT, 3 WRONG, 0 UNVERIFIABLE** of 102.
- Error rate (unweighted, strict): **3/102 = 2.9%** (95% Wilson 1.0–8.3%). Lenient (not counting the japan-2007 scope case, whose role fits the page): 2/102 = 2.0% (0.5–6.9%).
- Weighted by each file's number of eligible ops (the sample is stratified, not proportional; 9,631 of 12,251 ops are Live Archive links, 0/14 wrong): about **1.2%** of all applied ops (crude: each file's sample rate times its op count; all of it comes from loc, names and sr-roles-a).
- With 4 ops per file, a file-level 0/4 only says the file is not grossly wrong (upper 95% bound ≈ 49%); 1/4 is a signal to look, not a rate.

| agent file | n | correct | wrong | unverifiable | error rate |
|---|---|---|---|---|---|
| applied-cms.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-cmsst.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-current-season.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-dates-a.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-dates-b.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-dates.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-judge-links.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-la.jsonl | 14 | 14 | 0 | 0 | 0% |
| applied-loc.jsonl | 4 | 3 | 1 | 0 | 25% |
| applied-merge.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-missing.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-names.jsonl | 4 | 3 | 1 | 0 | 25% |
| applied-pins.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-problems.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-psets.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-results.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-sr-notdoc.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-sr-roles-a.jsonl | 4 | 3 | 1 | 0 | 25% |
| applied-sr-roles-b.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-sr-wrong.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-struct.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-urls.jsonl | 4 | 4 | 0 | 0 | 0% |
| applied-web.jsonl | 4 | 4 | 0 | 0 | 0% |
| **all** | 102 | 99 | 3 | 0 | 2.9% |

## The WRONG cases

- **west-neerc-1998** (applied-loc.jsonl line 393): append sources: {"url": "http://neerc.ifmo.ru/Archive/98/results.htm", "roles": ["scoreboard"], "scope": "…
  - Why: same snapshot: the 'Western Subregion (Minsk)' section is only Team + Rank (ties as 12-16 etc.), no per-problem or solved columns; the other five sections are grids
  - Right value: roles [rankings] (scope Western Subregion), not scoreboard
- **rmc-2004** (applied-names.jsonl line 96): set labels = ["A", "B", "C", "D", "E", "F", "G", "H", "I"] (was null)
  - Why: the cited capture rmc-2004/scoreboard/2026-09-01-live is the 2005 contest: page title '2005 Rocky Mountain Regional ACM Scoreboard by Rank', columns tire/randomwalk/paint/openclose/hourglass/mindiff/odometer/digits/suit = rmc-2005's set; the catalogue already files that address under rmc-2005. RMC 2004's own problems.zip (held) has 8 problems and Baekjoon category 189 lists A-H
  - Right value: labels A-H (8 problems); the companion op count 8->9 (applied-names line 94) and complete:false (line 95) are wrong too: count stays 8
- **japan-2007** (applied-sr-roles-a.jsonl line 91): set sources.source.roles = ["standings"] (was ["rankings"])
  - Why: held copy is '国内予選の結果' (Japanese kokunai yosen no kekka: 'results of the domestic preliminary') - results of the Japanese domestic qualifier held 2007-07-06, not of the Tokyo regional (2007-11-03); the agent noted 'SCOPE ISSUE' but filed it as japan-2007's unscoped standings. The table shape (rank/team/solved/time) would be standings
  - Right value: not a results source of japan-2007 as it stands: give it a scope ('domestic qualifier, 2007-07-06') or move it to a domestic-qualifier contest. Same pattern on japan-2008/2010/2011/2017 (no coverage-level change: each already has regional standings)
  - Note: the role fits the page; the error is the contest/scope, and it was misfiled before the change too

Related wrong ops outside the sample: applied-names line 94 (rmc-2004 count 8→9) and line 95 (complete: false) share the rmc-2004 root cause; japan-2008, japan-2010, japan-2011 and japan-2017 got the same domestic-qualifier-as-standings change as japan-2007 (no coverage level changed: each already has regional standings).

Systematic follow-ups run to size the two root causes: (1) every held capture cited by a names/problems op (168) was matched against the sources of the contest it is filed under — only rmc-2004 cites a capture of another edition; (2) all six sections of the 1998 NEERC results page were read — only the Western one is ranks only, so the other 1998 subregionals that got it as `scoreboard` are right.

## Correct, with a side issue worth knowing

- taiwan-2025 (applied-dates-b.jsonl): cited address is now 404; verified from the held crawl
- rmc-1991 (applied-dates.jsonl): medium confidence (same-day account), as the op says
- nzpc-2004 (applied-dates.jsonl): pre-contest announcement only; no post-contest page with the date found
- west-siberia-2006 (applied-loc.jsonl): the same page gives the date 2006-11-09, still blank in the catalogue
- mausa-1990 (applied-missing.jsonl): region not named in the article; Mid-Atlantic is inferred (Tech won the Mid-Atlantic regional at Maryland in Oct 1991)
- seusa-1986 (applied-missing.jsonl): region identity in 1986 inferred from UCF's present region
- pacnw-1992 (applied-missing.jsonl): 'Pacific' = pacnw lineage is an inference (pacnw-1994's own standings say '(Pacific)')
- ncna-2024 (applied-problems.jsonl): the set also lists 'Which Number Kind Is it?' (whichnumberkindisit2), not on that board; Kattis source 'North Central Regional Programming Contest 2024' also has 'modal' - if those are a second division's problems, count (distinct problems) would be higher
- amritapuri-2025 (applied-problems.jsonl): the letter is now lost: amritapuri-2025 keeps no other_names/alias of the judge title and letters stay unknown (chennai-2025 kept other_names). Same for all 11 amritapuri-2025 name ops
- seusa-2000 (applied-sr-roles-b.jsonl): no problem: <letter> set on the source
- south-america-2003 (applied-sr-roles-b.jsonl): the page is the Argentina site's board; no scope
- wf-1981 (applied-sr-roles-b.jsonl): no scope set although the page covers 21 contests
- tehran-2023 (applied-struct.jsonl): overrides the CMS hierarchy; consistent with the ruling that the CMS tends to be the wrong one in a conflict

## Full table

| # | agent file | contest | change | verdict | why |
|---|---|---|---|---|---|
| 0 | cms | west-siberia-1999 | set cms_ids = [9929] (was []) | CORRECT | CMS regionalresults/2000: 9929 'The 1999 ACM Siberian Subregional Contest' under 1010 (NEERC 1999); the only 1999 Siberian edition in the catalogue (east-siberia starts 2000); id not used elsewhere |
| 1 | cms | central-russia-2007 | set cms_ids = [9906] (was []) | CORRECT | regionalresults/2008: 9906 'The 2007 Central Subregional Contest' under 1180 (NEERC 2007); unique |
| 2 | cms | north-russia-1999 | set cms_ids = [9901] (was []) | CORRECT | regionalresults/2000: 9901 'The 1999 Northern Subregional Contest' under 1010; unique |
| 3 | cms | west-neerc-1999 | set cms_ids = [9930] (was []) | CORRECT | regionalresults/2000: 9930 'The 1999 ACM Western Subregional Contest' under 1010; unique |
| 4 | cmsst | romania-2013 | append sources: {"url": "https://icpc.global/regionals/finder/Romania-2014/standings", "roles": ["standing… | CORRECT | API contest 2004 today: 39 rows, 39 ranked, 33 with solved>0, rank 1 Gold Crocopups 7/1066; data/cms-shortnames.json 2004=Romania-2014 = romania-2013's cms id; rows give solved -> standings |
| 5 | cmsst | nordic-2025 | append sources: {"url": "https://icpc.global/regionals/finder/Nordic-2026/standings", "roles": ["standings… | CORRECT | API 9374: 268 rows, 228 with solved, rank 1 snowman (Copenhagen) 10/1216; slug Nordic-2026 |
| 6 | cmsst | vietnam-national-2014 | append sources: {"url": "https://icpc.global/regionals/finder/Vietnam-National-HoChiMinh-city-2015/standin… | CORRECT | API 2130: 107 rows, 103 ranked/solved, rank 1 Brainf*ck 8/1215; slug Vietnam-National-HoChiMinh-city-2015 |
| 7 | cmsst | neerc-2013 | append sources: {"url": "https://icpc.global/regionals/finder/Northeastern-Europe-2014/standings", "roles"… | CORRECT | API 2025: 228 rows, 223 with solved, rank 1 SPb SU 4 8/613; slug Northeastern-Europe-2014 |
| 8 | current-season | west-siberia-2026 | append sources: {"url": "https://olymp.nstu.ru/contests/3068/downloadproblems", "roles": ["problemset"]} | CORRECT | live PDF (206 KB) first page 'The 2026 ICPC West Siberian Regional Contest, Novosibirsk, November 21, 2026' + statements; contest already ran (no disclosure issue) |
| 9 | current-season | central-russia-2026 | set date = "2026-10-31" (was "2026-11-01") | CORRECT | nerc.itmo.ru/subregions/central.html live: 'Contest Dates: 31 Oct, 26' (the 03 Oct entry is the qualification) |
| 10 | current-season | nena-2026 | append sources: {"url": "https://east.na.icpc.global/scoreboard/2026/eastdiv/index_Northeast%20NA.html", "… | CORRECT | live page: 'Final Scoreboard ... Northeast NA Standings', generated Mon Nov 09 21:17 UTC 2026, per-problem columns A-N |
| 11 | current-season | kazakhstan-2026 | append sources: {"url": "https://icpc.global/regionals/finder/Kazakhstan-Regional-2027/standings", "roles"… | CORRECT | API 9798: 171 ranked rows (138 with solved>0), slug Kazakhstan-Regional-2027 |
| 12 | dates-a | bulgaria-2011 | set date = "2011-05-14" (was "2011-05-15") | CORRECT | bcpc.eu/XXIII/ live: 'На 14 май ... ще се проведе XXIII републиканска студентска олимпиада' (Bulgarian: 'On 14 May ... the 23rd national student programming olympiad will be held') and timeanddate link iso=20110514T10 (event header says 13-14 May) |
| 13 | dates-a | nwerc-2020 | set date = "2021-03-28" (was "2021-03-27") | CORRECT | 2020.nwerc.eu/standings/ live: contest start 2021-03-28 11:00 CEST, end 16:00; site says March 27-28 (27 = practice) |
| 14 | dates-a | west-neerc-2023 | set date = "2023-11-05" (was "2023-11-04") | CORRECT | acm.bsu.by/contests/225/standings/ live: 'Belarus Regional Contest 2023 (XXVI NERC Western regional contest)' / '5 ноября 2023 г.' (Russian: 5 November 2023) |
| 15 | dates-a | slovenia-2011 | set date = "2011-10-22" (was null) | CORRECT | dist.famnit.upr.si/?p=168 live: UPM finals 'on Saturday, 22.10.2011 co-organised by ACM Slovenia' |
| 16 | dates-b | taiwan-2025 | set date = "2025-11-16" (was "2025-11-17") | CORRECT | cited page now 404; our crawl of icpc.tw/2025 (archive taiwan-2025/website/2026-09-05-live) says 'From 9:30 AM to 2:30 PM (5 hours) on November 16, 2025' |
| 17 | dates-b | acpc-2013 | set date = "2013-11-23" (was "2013-11-26") | CORRECT | live PDF now 404; Wayback 20160429140824 copy: every page headed 'Egypt, Sharm El Sheikh, November 23rd, 2013' |
| 18 | dates-b | brazil-2023 | set date = "2023-10-21" (was "2023-10-19") | CORRECT | live contest.pdf cover: '2023 Latin American Regional Contests, October 21, 2023'; brazil-2023 cites the same latam-2023 board/set |
| 19 | dates-b | brazil-2022 | set date = "2023-03-18" (was "2023-03-16") | CORRECT | live contest.pdf cover: '2022 Latin American Regional Contests, March 18, 2023' |
| 20 | dates | rmc-1991 | set date = "1991-11-09" (was null) | CORRECT | held copy rmc-1991/report/20261116-live: post timestamp 689730527 = 1991-11-09 23:48 UTC (afternoon US time, a Saturday): 'The 1991 contest for the Mountain Region is just finished' |
| 21 | dates | moscow-2007 | set date = "2007-10-21" (was null) | CORRECT | held PDF moscow-2007/judge-codeforces/20261122-live: 'NEERC Moscow Subregional Contest, Moscow, October 21, 2007' |
| 22 | dates | central-russia-2002 | set date = "2002-10-17" (was null) | CORRECT | Wayback 20030510042818: table heading 'ACM ICPC 2002-2003 NEERC, Central Subregion / Rybinsk, October 17, 2002' (event Oct 15-18) |
| 23 | dates | nzpc-2004 | set date = "2004-08-14" (was null) | CORRECT | Wayback 20040713232350 of NZinfo.html: 'The next NZ Programming Contest is Saturday August 14th' (14 Aug 2004 is a Saturday) |
| 24 | judge-links | cerc-2010 | set judges.source.as_of = "20191113004947" (was null) | CORRECT | Wayback 20191113004947 of LA problem=2976 shows '4975 - Casting Spells' = catalogue name |
| 25 | judge-links | nwerc-2005 | set judges.source.as_of = "20191216070851" (was null) | CORRECT | Wayback 20191216070851 problem=1413 shows '3412 - Pesky Heroes' |
| 26 | judge-links | acpc-2003 | set judges.source.as_of = "20150309145147" (was null) | CORRECT | Wayback 20150309145147 category=146 problem=984 shows '2983 - XML+XPATH=XSLT' |
| 27 | judge-links | korea-2007 | set judges.source.as_of = "20191208133428" (was null) | CORRECT | Wayback 20191208133428 problem=1907 shows '3906 - Signals' |
| 28 | la | cerc-2012 | set judges.source.url = "https://icpcarchive.ecs.baylor.edu/index.php?option=com_onlinejudge&Itemid=8&category=567… (was "https://icpcarchive.ecs.baylor.edu/inde…) | CORRECT | final link category=567 problem=4268 @20150309140127 shows '6257 - Chemist's vows' |
| 29 | la | latam-2017 | set judges.source.as_of = "20220123220125" (was null) | CORRECT | final link category=788 problem=6217 @20220123220125 shows '8195 - Hard choice' |
| 30 | la | beijing-2007 | set judges.source.as_of = "20150309154719" (was null) | CORRECT | problem=2032 @20150309154719 shows '4031 - Integer Transmission' |
| 31 | la | seerc-1997 | set judges.source.url = "https://icpcarchive.ecs.baylor.edu/index.php?option=com_onlinejudge&Itemid=8&category=482… (was "https://icpcarchive.ecs.baylor.edu/inde…) | CORRECT | category=482 problem=3295 @20150309151103 shows '5294 - Tile Puzzle' |
| 32 | la | kanpur-2012 | set judges.source.as_of = "20150309140022" (was null) | CORRECT | category=561 problem=4303 @20150309140022 shows '6292 - A HEXAGONAL COMPLEX' |
| 33 | la | mausa-1996 | set judges.source.url = "https://icpcarchive.ecs.baylor.edu/index.php?option=com_onlinejudge&Itemid=8&category=473… (was "https://icpcarchive.ecs.baylor.edu/inde…) | CORRECT | category=473 problem=3429 @20150309151253 shows '5428 - Making the Grade' |
| 34 | la | scusa-2013 | set judges.source.as_of = "20150309135710" (was null) | CORRECT | category=624 problem=4485 @20150309135710 shows '6474 - Drop Zone' |
| 35 | la | wf-2014 | set judges.source.as_of = "20150309134026" (was null) | CORRECT | category=590 problem=4790 @20150309134026 shows '6778 - Sensor Network' |
| 36 | la | seerc-1997 | set judges.source.as_of = "20150309155802" (was null) | CORRECT | problem=3293 @20150309155802 shows '5292 - Critical Links' |
| 37 | la | xian-2006 | set judges.source.as_of = "20150309152645" (was null) | CORRECT | problem=1783 @20150309152645 shows '3782 - Bigger is Better' |
| 38 | la | neerc-2015 | set judges.source.url = "https://icpcarchive.ecs.baylor.edu/index.php?option=onlinejudge&Itemid=8&category=698&pag… (was "https://icpcarchive.ecs.baylor.edu/inde…) | CORRECT | option=onlinejudge category=698 problem=5499 @20200929114359 shows '7477 - Landscape Improved' |
| 39 | la | nwerc-2016 | set judges.source.as_of = "20200922215840" (was null) | CORRECT | category=749 problem=5786 @20200922215840 shows '7764 - Free Weights' |
| 40 | la | xian-2014 | set judges.source.as_of = "20150309134745" (was null) | CORRECT | category=652 problem=5050 @20150309134745 shows '7038 - The Diameter of Tree' |
| 41 | la | dhaka-2009 | set judges.source.as_of = "20150309153108" (was null) | CORRECT | problem=2500 @20150309153108 shows '4499 - Camera in the Museum' |
| 42 | loc | far-east-russia-1998 | append sources: {"url": "http://neerc.ifmo.ru/Archive/98/results.htm", "roles": ["scoreboard"], "scope": "… | CORRECT | Wayback 20030516090449: section 'Far Eastern Subregional Quarter Final, Vladivostok, October 24, 1998' is a per-problem grid (A-F, = , Time, Rank) -> scoreboard with scope |
| 43 | loc | nwerc-2024 | set location = "Delft University of Technology, Delft" (was "Administrative Site Location; Reykjavík…) | CORRECT | 2024.nwerc.eu live: 'The contest was held on the campus of the Delft University of Technology' |
| 44 | loc | west-neerc-1998 | append sources: {"url": "http://neerc.ifmo.ru/Archive/98/results.htm", "roles": ["scoreboard"], "scope": "… | WRONG | same snapshot: the 'Western Subregion (Minsk)' section is only Team + Rank (ties as 12-16 etc.), no per-problem or solved columns; the other five sections are grids |
| 45 | loc | west-siberia-2006 | set location = "Novosibirsk, Novosibirsk State Technical University" (was null) | CORRECT | Wayback 20070221013224: 'Host city: Novosibirsk / Host university: Novosibirsk State Technical University' and 'took place in Novosibirsk on November 9, 2006' |
| 46 | merge | rmc-2023 | set sources.source.as_of = "20240329112337" (was null) | CORRECT | Wayback 20240329112337 of rocky.icpc.io: 'Contest: November 4, 2023 ... final standings at rmc23.kattis.com' |
| 47 | merge | ncna-2009 | remove sources.source http://cs.unomaha.edu/acmregn/index.html | CORRECT | ncna-2009 keeps one entry of the address (roles web, as_of 20091116120639); the removed one was the duplicate appended by sr-wrong |
| 48 | merge | pacnw-1999 | unset sources.source.contains (was ["package"]) | CORRECT | Wayback 20020112012652: PC^2 'Contest Reports/Stats' with a Problem Solution Grid (teams x A-I) and team-by-team solutions -> scoreboard; the page only links Problems.ZIP, so contains:[package] does not belong |
| 49 | merge | nordic-2002 | remove sources.source https://www.ida.liu.se/projects/progcontest/progsm/2002/ | CORRECT | nordic-2002 keeps one entry (as_of 20040105005213) whose roles now include web; nothing lost |
| 50 | missing | mausa-1990 | insert contest mausa-1990 | CORRECT | Wayback 20191116003259: Roanoke Times 1991-03-22 'UVA had finished second to Tech in a regional qualifying match held in the fall' |
| 51 | missing | seusa-1986 | insert contest seusa-1986 | CORRECT | held copy (seusa-1988/rankings/20140630-wayback): '1986-1987 Regionals: 1st Finals: 2nd'; page says 'UCF is in the Southeast USA Region' |
| 52 | missing | werc-1992 | append sources: {"url": "https://groups.google.com/g/comp.org.acm/c/P3ys4igw6Mk", "roles": ["rankings"], "… | CORRECT | groups.google.com thread live: Mark Huizer 'The results of the (Western-)European region: 1: RU Leiden 2: TU Eindhoven' |
| 53 | missing | pacnw-1992 | insert contest pacnw-1992 | CORRECT | thread live: Dragomir 1992-12-05 'Pacific : Berkeley, Stanford (non-confirmed officially)' (finals in Indiana = wf-1993) |
| 54 | names | rmc-2004 | set labels = ["A", "B", "C", "D", "E", "F", "G", "H", "I"] (was null) | WRONG | the cited capture rmc-2004/scoreboard/2026-09-01-live is the 2005 contest: page title '2005 Rocky Mountain Regional ACM Scoreboard by Rank', columns tire/randomwalk/paint/openclose/hourglass/mindiff/odometer/digits/suit = rmc-2005's set; the catalogue already files that address under rmc-2005. RMC 2004's own problems.zip (held) has 8 problems and Baekjoon category 189 lists A-H |
| 55 | names | seerc-1998 | set labels = ["A", "B", "C", "D", "E", "F", "G"] (was null) | CORRECT | held copy of acm.win.tue.nl ProblemSetArchive/B_EU_SERC/1998 index lists A.PS-G.PS; set count 7 |
| 56 | names | south-pacific-2010 | set labels = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"] (was null) | CORRECT | held sppcontests.org '2010 ICPC Results' table: Rank Name Points Time A-K Total; set count 11 |
| 57 | names | syria-2011 | set labels = ["A", "B", "C", "D", "E", "F", "G", "H"] (was null) | CORRECT | held 'SCPC 2011 result' table: Rank Name Solved Time A-H; set count 8 |
| 58 | pins | nwerc-2018 | unset sources.source.as_of (was "20200225021122") | CORRECT | Wayback 20200225021122 = 'NWERC 2019 final standings'; CDX in 2018-11..2020-02: 20181128084517 (tiny, no board), 20191027 404, 20191226/20200225 the 2019 board -> no 2018 copy, keep as lost |
| 59 | pins | south-russia-2007 | set sources.source.as_of = "20071124014833" (was null) | CORRECT | Wayback 20071124014833: 'Southern subregional contest took place in Saratov on October 13, 2007' |
| 60 | pins | ecna-2000 | unset sources.source.as_of (was "20010302231745") | CORRECT | Wayback 20010302231745 = 'The 2001/2002 ACM ECNA'; CDX: the 2000-10-06 and 2001-02-26 captures are framesets (logo/menubar/banner frames), no opening frame archived |
| 61 | pins | far-east-russia-2019 | set sources.source.as_of = "20191130003237" (was null) | CORRECT | Wayback 20191130003237: 'Far Eastern Russia Regional Contest will take place in Vladivostok on November 10, 2019' |
| 62 | problems | ncna-2024 | set count = 12 (was null) | CORRECT | held ncna24.kattis.com standings: 12 problem columns A-L |
| 63 | problems | amritapuri-2025 | set name = "XOR Product MST" (was "K - XOR Product MST") | CORRECT | CodeChef XORPRODMST is titled 'K - XOR Product MST'; the 'K - ' is the contest letter |
| 64 | problems | ncna-2024 | set letters = {"B": "p-f8ca789e", "E": "p-82f20ba9", "F": "p-746624ce", "H": "p-c55e3bc8"} (was null) | CORRECT | board column order: hungryaardvark=B, expectedflightdelay=E, guardevaders=F, legoloverstriangle=H; the four set problems carry those Kattis ids |
| 65 | problems | chennai-2025 | set name = "Minimum Divides Maximum" (was "F - Minimum Divides Maximum") | CORRECT | CodeChef MINDIVMAX titled 'F - Minimum Divides Maximum'; other_names keeps the judge title |
| 66 | psets | georgia-2017 | append sources: {"url": "https://nerc.itmo.ru/archive/2017/northern/north-2017-statements.pdf", "roles": [… | CORRECT | georgia-2017 is a member of problemsets/north-russia-2017 with the same letters; held Georgia standings (20171107) carry the 12 titles; taurida-2017 cites the same PDF |
| 67 | psets | chengdu-2011 | append sources: {"url": "https://acm.hdu.edu.cn/search.php?field=problem&key=2011+Asia+Chengdu+Regional&so… | CORRECT | HDU source search live: 4111-4120 Alice and Bob ... Ji-Tu Problem = set chengdu-2011's 10 titles |
| 68 | psets | norway-2001 | append sources: {"url": "http://heim.ifi.uio.no/~db/nm-i-programmering/nm2001/bridge/oppgave.pdf", "roles"… | CORRECT | held crawl file db47cfb8b840870d.pdf = .../nm2001/bridge/oppgave.pdf (Wayback 20061030105536): 'Problem G / Bridge placements'; set letter G = Bridge placements |
| 69 | psets | gran-premio-mexico-2024 | append sources: {"url": "https://maratona.sbc.org.br/hist/2024/primfase24/contest-pf2024/maratona.pdf", "r… | CORRECT | live PDF: 'Maratona ... 31 de Agosto de 2024' and 'também está sendo utilizado ... The 2024 ICPC Gran Premio de Mexico' (Portuguese: 'is also being used [simultaneously in] ...'); GP Mexico runs several 'fechas', so scope fits (fechas = rounds) |
| 70 | results | bolivia-national-2011 | append sources: {"url": "http://www.icpc-bolivia.edu.bo/resultados/fase_1_Bolivia_2011/LaPaz-final.html", … | CORRECT | held crawl file 527791aed65f9916.html = LaPaz-final.html @20111026012902: PC^2 summary with A-G tries/time per team |
| 71 | results | socal-1979 | append sources: {"url": "https://digital-collections.csun.edu/digital/collection/Sundial/id/20282", "roles… | CORRECT | CONTENTdm OCR: Daily Sundial 14 Nov 1980 'Pomona won the competition last year ... CSUN came in third last year' |
| 72 | results | urals-2001 | append sources: {"url": "https://sp.urfu.ru/chu/2001/final.html", "roles": ["scoreboard"]} | CORRECT | live chu/2001/final.html: per-problem A1-H2 grid; chu/2001/ says the 5th Ural Championship (16-21 April 2001) 'являлся четвертьфиналом ... сезона 2001-2002' (Russian: 'was the quarterfinal of the 2001-2002 season') |
| 73 | results | bapc-prelims-2016 | set sources.source.scope = "scoreboards of the DAPC, EAPC, LAPC, NKP, AAPP, UvA and Utrecht preliminaries" (was null) | CORRECT | held copy of the page (live fetch timed out): 7 scoreboard images dapc, eapc, lapc, nkp, aapp, uva, scorebord_ukp(Utrecht) |
| 74 | sr-notdoc | bolivia-national-2020 | remove sources.source https://icpc.global/regionals/finder/Bolivia-Preliminary-2021 | CORRECT | DEFINITIONS: a CMS finder page is not web and not a source; held crawl is the empty app shell; cms id kept |
| 75 | sr-notdoc | bolivia-national-2022 | remove sources.source https://icpc.global/regionals/finder/Bolivia-Preliminary-2023 | CORRECT | as 74; the /standings source remains |
| 76 | sr-notdoc | bolivia-national-2018 | remove sources.source https://icpc.global/regionals/finder/Bolivia-Preliminary-2019 | CORRECT | as 74; the /standings source remains |
| 77 | sr-notdoc | bolivia-national-2017 | remove sources.source https://icpc.global/regionals/finder/Bolivia-Preliminary-2018 | CORRECT | as 74; the /standings source remains |
| 78 | sr-roles-a | egypt-2023 | set sources.source.roles = ["frozen_scoreboard"] (was ["web", "frozen_scoreboard"]) | CORRECT | held copy (gzip): single ECPC scoreboard table, 245 rows, Rank/Name/Solved/Time/A-O, no site pages -> not web |
| 79 | sr-roles-a | kharagpur-2019 | set sources.source.roles = ["web"] (was ["web", "standings"]) | CORRECT | held copy: Kharagpur site home page (announcements, menu item 'IITKGP Ranks'), no standings table |
| 80 | sr-roles-a | bapc-prelims-2013 | set sources.source.roles = ["problemset"] (was ["standings"]) | CORRECT | held copy: Eolymp 'BAPC 2013, Preliminary' page, 11 problems, sign-in wall, no standings |
| 81 | sr-roles-a | japan-2007 | set sources.source.roles = ["standings"] (was ["rankings"]) | WRONG | held copy is '国内予選の結果' (Japanese kokunai yosen no kekka: 'results of the domestic preliminary') - results of the Japanese domestic qualifier held 2007-07-06, not of the Tokyo regional (2007-11-03); the agent noted 'SCOPE ISSUE' but filed it as japan-2007's unscoped standings. The table shape (rank/team/solved/time) would be standings |
| 82 | sr-roles-b | vietnam-2012 | set sources.source.roles = ["scoreboard"] (was ["scoreboard", "standings"]) | CORRECT | held copy: 'FINAL SCOREBOARD Created by CSUS PC^2 9.2.3', per-problem A-J -> scoreboard (standings redundant) |
| 83 | sr-roles-b | seusa-2000 | set sources.source.roles = ["problem"] (was ["problemset"]) | CORRECT | Wayback 20010211194623: one statement, 'Charity Begins at Home-page' (charity.in); it is in set seusa-2000 |
| 84 | sr-roles-b | south-america-2003 | set sources.source.roles = ["standings"] (was ["scoreboard"]) | CORRECT | held copy: Rank/Name/Solved/Score for 10 teams + 'Honorable Mention' tail -> complete standings by the 2026-11-14 criteria |
| 85 | sr-roles-b | wf-1981 | set sources.source.roles = ["rankings"] (was ["web", "rankings"]) | CORRECT | held copy: 'The Early Years - World Finals Champions' 1977-1997, places per year -> rankings; a multi-year history page is not this edition's web |
| 86 | sr-wrong | central-russia-1999 | remove sources.source https://acm.timus.ru/problemset.aspx?space=1&tag=qf | CORRECT | Timus problemset tag=qf live: sources are NEERC Central 2000-2003, Northern 2001, Eastern 2006-2015; none 1999 |
| 87 | sr-wrong | brazil-2025 | remove sources.source https://scorelatam.naquadah.com.br/subbr-2025/ | CORRECT | live scorelatam subbr-2025: 'The 2025 ICPC South America/Brazil First Phase'; brazil-first-phase-2025 has the same url+as_of |
| 88 | sr-wrong | seerc-2021 | unset sources.source.as_of (was "20250312194116") | CORRECT | Wayback 20250312194116 of acm.ro/results.htm: '2024-2025 SEERC: Standings' (Bucharest/Lviv); pins later re-pinned 20220226192513 to the 2021 frameset |
| 89 | sr-wrong | nwerc-2009 | append sources: {"url": "https://nwerc.eu/", "roles": ["web"], "as_of": "20090928114801"} | CORRECT | Wayback 20090928114801 of nwerc.eu: 'NWERC 2009 - Nuremberg, November 6-8, 2009' |
| 90 | struct | tehran-2023 | set parent = "wf-2024" (was "awc-2023") | CORRECT | CMS tree puts Tehran 7489 under AWC 7470, but awc-2023 ran 2024-03-30, before Tehran (2024-05-30), its 72 teams include no Iranian school, and WF 2024 standings list Sharif 13th ('Asia West') and U Tehran HM |
| 91 | struct | nzpc-2003 | set next = "nzpc-2004" (was null) | CORRECT | nzpc-2004 exists (season 2005) and nothing else points to it |
| 92 | struct | caribbean-national-2019 | set next = "caribbean-national-2020" (was null) | CORRECT | caribbean-national-2020 exists (cms 4469, season 2021) and had no predecessor |
| 93 | struct | hong-kong | set series.rotating_host = true (was null) | CORRECT | hong-kong editions 2000, 2016-2019, 2022, 2024-2026: an Asia host-city series like the 25 others with rotating_host |
| 94 | urls | south-america-north-2013 | append sources: {"url": "https://icpcarchive.github.io/Latin%20American%20Contests/Latin%20American%20Regi… | CORRECT | held copy of that address: 'ACM ICPC 2013 Latin American Regional Contests November 8th-9th, 2013', created 2013-11-07 -> 2013 document; south-america-north-2013 ran 2013-11-09 |
| 95 | urls | caribbean-2010 | unset sources.source.as_of (was "20111128230921") | CORRECT | held copy of 20111128230921: 'Tercera edición el 4 y 5 de noviembre de 2011' (Spanish: third edition, 4-5 November 2011); CDX has no capture between 2010 and 2011-11-28 |
| 96 | urls | cerc-2000 | remove sources.source http://contest.felk.cvut.cz:80/00cerc/solved/index.html | CORRECT | cerc-2000 keeps https://contest.felk.cvut.cz/00cerc/solved/ with the same roles and as_of 20010123232800 |
| 97 | urls | lethbridge-2022 | remove sources.source https://www.cs.uleth.ca/~cheng/contest/2022.html | CORRECT | held copy: 'University of Lethbridge 2022 Teams' - U of L teams and their ranks at the Alberta CPC and Rocky Mountain regional, not a Lethbridge contest |
| 98 | web | ncna-2020 | append sources: {"url": "https://ncna-region.unl.edu/", "roles": ["web"], "as_of": "20210303083453"} | CORRECT | Wayback 20210303083453: UNL NCNA page, 'Final Rankings: ncna20.kattis.com ... Saturday, February 27, 2021 CONTEST DAY' |
| 99 | web | pakistan-2022 | append sources: {"url": "https://giki.edu.pk/icpc/", "roles": ["web"], "as_of": "20230528193131"} | CORRECT | Wayback 20230528193131: GIKI ICPC page 'ICPC Asia Topi 2022-2023 Onsite Contest', '2022 ICPC Asia Topi Regional On-site Contest Problems: ICPC_Feb2023' |
| 100 | web | naq-2022 | append sources: {"url": "https://na.icpc.global/2022-23/naq/", "roles": ["web"], "as_of": "20240324170110"… | CORRECT | Wayback 20240324170110: 'NAQ 2022-23 ... Sat, 4 Feb 2023 ... naq22.kattis.com' |
| 101 | web | ncna-2021 | append sources: {"url": "https://na.icpc.global/home/regionals/ncna-home/ncna-regional-contest-2021-2022/"… | CORRECT | Wayback 20230202224755: 'NCNA REGIONALS 2021-2022 ... PRACTICE DAY FRIDAY FEB 25 ... Saturday, Feb 26th', ncna21.kattis.com |
