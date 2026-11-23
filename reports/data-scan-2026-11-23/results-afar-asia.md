# Data scan 2026-11-23 - results-afar-asia: missing results in Africa & Arab, Asia Pacific, Asia West, Asia East

## Scope and method (rerunnable)

- Targets: every contest of a series whose header `region` is Africa & Arab, Asia Pacific, Asia West or Asia East, not `status: upcoming`, with no source whose roles include scoreboard, frozen_scoreboard, standings, rankings or teams, at the worktree commit: **79 contests** (`work/targets.json`).
- Hunt, in this order: (1) the ICPC CMS open API (`/api/contest/public/search/contest/<id>` via `../fetch_icpc_api_json.py`, `/regionalresults/<year>` for the finder slug and the CMS external standings/report URLs) and the dumps beside the repo; (2) our own archive: every file of `archive/<series>/<contest>/` grepped for results words in several languages and the site manifests for result-like URLs (`work/grep_archive.py`, `work/archive_hits.json`); (3) sibling editions' result addresses with the year changed; (4) Wayback CDX over the organisers' hosts (`work/cdx.sh`, `work/wb.sh`); (5) known hosts (board.xcpcio.com and github.com/xcpcio/board-data, scoreboard.acpc.global / acpcsb.acpc.global, acmacpc.org, icpc.sharif.edu, the NZPC results folder); (6) web search.
- A page was accepted only after reading it (live, our copy, or its Wayback snapshot) and checking it is this edition: contest name, date, host, teams. `as_of` is set where only a snapshot or our copy showed it.
- The Internet Archive was down for stretches of the run (CDX and snapshots answered "Temporarily Offline"), and the session was cut twice; contests left unhunted are marked so in `data.json`.

## Outcome

| | contests |
|---|---|
| found | 36 |
| partial | 4 |
| none | 39 |
| not yet hunted | 0 |

Best new result level per contest with a find: scoreboard 9, standings 25, frozen scoreboard only 1, rankings 4.

## What the ops do (46 ops: 43 `append` of a source, 3 `set` on one existing source; `apply_scan_ops.py --check`: all ok)

- **CMS standings that were never cited: 26 pages for 24 contests.** The CMS holds standings rows for these contests (API asked 2026-11-23, rows also in `icpc_all_standings.json` / `icpc_new_standings_from_db.json`), but the catalogue never had the standings source, so nothing was baked. Filed as `standings` (rows give problems solved). Contests: malaysia-national-2013/2016, mongolia-national-2013...2018, myanmar-mcpc-2017, oman-capital/coastline/midland-2025, oman-capital/coastline/midland/oriental-2026, taiwan-ncpc-2012 (Groups A, B, C, three scoped pages), taiwan-ncpc-2013 (the NCPU part, scoped), taiwan-ncpc-2014/2015, thailand-national-2012/2013/2014, chengdu-2026. After applying, `tools/bake_icpc_standings.py --write` will render their copies from the dumps (chengdu-2026, cms 9604, needs `tools/topup_icpc_standings.py` first: it is not in the dumps yet).
- **Scoreboards:** acpc-1998 (alakhawayn.ma Standings.html, 1999 snapshot), angola-2017 (COJ scoreboard cid 1612, official Angola group separate from an outside team), egypt-2008 (summaryENC08.html, held), tehran-online-2022 (IIPC scoreboard, held), taiwan-ncpc-2013 (NCPC part, the CMS external standings URL), nzpc-2014 (image PDF), xian-2026, chengdu-2026, yinchuan-2020 (board.xcpcio.com, official/unofficial groups in the data).
- **Standings:** australia-2013 (AuPC report.html), nzpc-2001, nzpc-2003 (results text files).
- **Rankings:** oman-2018 (CMU news: champions, plus a 5th place), kanpur-2021 (preliminary round selection list, scoped), philippines-national-2015 (DLSU news: Metro Manila qualifier top 3), palestine-2018 (Birzeit news: Birzeit 1st, 3rd-6th, 9th, no team names).
- **Frozen scoreboard:** ethiopia-2019 (DOMjudge public board, frozen 60 min before the end, saved as PDF in a participant's GitHub repo that the contest already cites for its problems).
- **Re-roled existing source (3 `set` ops):** lebanon-2018's LAU news article was `web`; it is a top-3 account (rankings + report, `scope: top 3`, `as_of` 20191115100742, since the live address is 403).

## Items for discussion with Fredrik

### 1. CMS standings that exist but were never made sources - a catalogue-wide gap?

- **Question:** should every contest whose CMS ids have standings rows get its CMS standings source, catalogue-wide, by a tool rather than by hand?
- **What it implies:** in my area alone 24 contests (26 pages) had rows in the CMS (and in the dumps on disk since April or August) but no CMS standings source, so they showed "no results". `bake_icpc_standings.py` and `topup_icpc_standings.py` only look at contests that already have a CMS standings source, so they cannot find these. The same gap very likely exists in other regions.
- **For a sweep:** it is mechanical, the data is already on disk, and the CMS is formally the official result. **Against:** a CMS page can be wrong (Taiwan-National-A 2013 has no rank 1 or 2; Myanmar-National-2018 ranks 12 of 65 rows and leaves the rest unranked, which is the normal Honorable Mention shape). And some contests carry several CMS ids, so which contest a page belongs to has to be read off `cms_ids`.
- **Examples:** thailand-national-2014 (`https://icpc.global/regionals/finder/Thai-Nat-On-site-2015/standings`, 113 rows), myanmar-mcpc-2017, taiwan-ncpc-2012.
- **Recommendation:** apply my 26, then run one sweep: for each contest, for each cms id with rows in the dumps or the API and no `/finder/<abbr>-<year>/standings` source, add one (`<abbr>-<icpcYear>` from `/regionalresults/<year>`). Then bake.

### 2. Taiwan NCPC and NCPU are one series in the catalogue

- **Question:** should the National Private Universities contest (NCPU, 全國私立大專校院程式設計競賽, quánguó sīlì dàzhuān xiàoyuàn chéngshì shèjì jìngsài, "national private colleges programming contest") stay merged into `taiwan-ncpc`?
- **What it implies:** taiwan-ncpc-2013 holds CMS 1908 (the NCPC, at NSYSU, about 80 teams, board last updated 19 Oct 2013) and CMS 1909 (the NCPU, at Chang Gung University, 2013-07-03, 38 rows). taiwan-ncpc-2014 and -2015 are NCPU contests only (ncpu2014.pu.edu.tw, ncpu2015.yzu.edu.tw), and earlier reports noted that taiwan-ncpc-2016 is a third contest again. I added the two 2013 result pages with a `scope` naming the part.
- **For merging:** the CMS hangs both under the Taiwan regional as national feeders, and the merge was ruled on 2026-09-04. **For splitting:** they are different contests, months apart, run by different hosts for different sets of universities. A single contest with two results reads as partial coverage when it is not.
- **Recommendation:** split NCPU out (its own series from 2013), and keep taiwan-ncpc for the MOE NCPC. Not done here: it is a structure change.

### 3. Africa & Arab national contests whose CMS record is an empty shell

- **Question:** what counts as evidence that these ran? Should they stay as ran contests with no results, or move to triage until something shows they ran?
- **What it implies:** 21 of my targets have a CMS record with 0 teams and usually no date: algeria-2024/2025, bahrain-2022/2023, benin-2022/2023, morocco-2022/2023, nigeria-2022/2023, sudan-2023/2024, togo-2022/2023, saudi-arabia-2024/2025, oman-2024, kuwait-2011/2012, lebanon-2009, philippines-national-2019 (plus gwalior-2022 and kharagpur-2021, already flagged by the 2026-11-16 hunt). The only other source is usually the national Facebook page, which we cannot read. `scoreboard.acpc.global`, `acpcsb.acpc.global` (live listings and Wayback CDX), `acpc.global/event/*` and `acmacpc.org` hold nothing for them.
- **For keeping:** most of these national contests do run every year, and a 0-team CMS shell is normal when the organisers never upload teams. egypt-2008 is a 0-team record and did run (scoreboard found). **Against:** the CMS auto-copies contests across years. A shell plus a Facebook page is the same evidence a cancelled edition would leave.
- **Examples:** saudi-arabia-2024 (`SaudiCPC-2025`, no date, no teams, no source), togo-2023, morocco-2022.
- **Recommendation:** keep them for now, and spend a targeted round on these organisers' social posts (a person with a Facebook login, or the ACPC office), because that is where the evidence is. Contests with no evidence after that go to triage as `cancelled`-unproven.

### 4. A preliminary round's result as a contest's only result (kanpur-2021)

- **Question:** is the ranked list of teams selected in a regional's own online preliminary a results source of that regional?
- **What it implies:** for kanpur-2021 (CMS 4829, 1599 teams, online, 2022-08-22), the only result found is "Result of Preliminary Online Contest" (kanpur.indiaicpc.in/?page_id=698, snapshot of 2022-09-13). The home page of the same date announces the prelim for 4 Sept 2022 and the onsite round for the end of September 2022. I found nothing showing that the onsite round was held. I added the prelim page as `rankings` with `scope: preliminary online contest`.
- **For counting it:** it is this edition's own round, a ranked list, and the CMS record (1599 teams, online) looks like the prelim's registrations. **Against:** it is not how the contest ended. If the onsite never ran, the contest is really "the prelim".
- **Recommendation:** keep it with the scope, and ask the Asia West RCD or check AWC 2021 (2022-12-24) qualifiers to settle whether the Kanpur onsite ran.

### 5. Wrong-edition or wrong-contest sources I ran into (not changed; other agents' areas)

- lebanon-2009: the website crawl is of `acmacpc.org/archive/y2009` (ACPC 2009 regional), and the bau.edu.lb LCPC event page describes LCPC **2019** (4 Oct 2019, LAU and AUB first and second, BAU sixth of 37). Neither is LCPC 2009.
- oman-southern-2025: its mtcit.gov.om source is the national final (oman-2025: Enigma and Libre of SQU, then Al-Istiqama of GUtech). oman-2025 cites it too.
- oman-capital-2025/2026 and thailand-national-2012/2014 have CMS finder pages (`/regionals/finder/<slug>`) as `web`, which the 2026-11-14 ruling excludes.
- acpc-1998: the archive's `scoreboard/2026-04-16-archive` capture is the ETH problem-set page (its manifest already says so). The real standings are now added.
- pakistan-2018: the "First Round Online Ranking" link on the 2018 UMT page points to an xlsx created 2016-11-23 (the 2016 online round).

### 6. Dates read while hunting (not applied: outside my area)

- nzpc-2001: "the New Zealand Programming Contest held on 25 August 2001" (nz01results.txt). The catalogue has no date.
- nzpc-2014: the scoreboard was last updated "Saturday, 9 August 2014". The catalogue has no date. This is a hint only.
- taiwan-ncpc-2013 (NCPC part): the board was last updated Sat Oct 19 2013. The catalogue has no date.
- lebanon-2018: the LAU article says the contest was on September 28, 2018 (CMS 2018-09-28). The catalogue has 2018-09-29.
- philippines-national-2015: the national final was on 2015-10-19 at the University of St. Louis, Tuguegarao (DLSU article). The catalogue's 2015-09-05 is probably a qualifier date.
- palestine-2018: the contest was on 27-28 Oct 2018 at Birzeit (Birzeit news). The catalogue has 2018-10-27, and the 28th was the competition day.
- By-catch for ethiopia-2020 (not my area): `Standings - The 2020 Ethiopian Collegiate Programming Contest.pdf` is in github.com/mukerem/ICPC-Journey under `2020 ETHCPC/standing/`.


## Per contest

| contest | status | new results sources / what was tried |
|---|---|---|
| acpc-1998 | found | scoreboard http://www.alakhawayn.ma/acmcontest/Standings.html @19990218065719 |
| algeria-2014 | none | CMS 2694 (ALCPC-2015, 98 teams/97 results) has no rows (topup asked 2026-11-13); only the AlgeriaCPC Facebook page is known; not searched further (time) |
| algeria-2018 | none | the held report (red0xff.github.io, a participant) says only that team NerDz placed second at ALCPC 2018 (Biskra, 1-3 Oct 2018); no first place given; CMS 3779 (AlCPC-2019, 42 teams/42 results) has no rows |
| algeria-2024 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| algeria-2025 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| angola-2017 | found | scoreboard http://coj.uci.cu/contest/cscoreboard.xhtml?cid=1612 @20171005031817 |
| angola-2018 | none | CMS 3565 (AOCPC-2019, 29 teams) has no rows; icpcangola.wordpress.com has a 2018/08 ranking-final.jpg (uploaded before the 2018 contest, so probably 2017) that I could not tie to an edition; held angop.ao item is a 2020 article; not searched further (time) |
| australia-2013 | found | standings http://www.cse.unsw.edu.au/~elgindyh/AuPC/report.html @20130921030227 |
| bahrain-2022 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| bahrain-2023 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| benin-2022 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| benin-2023 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| chengdu-2026 | found | standings https://icpc.global/regionals/finder/Chengdu-2027/standings; scoreboard https://board.xcpcio.com/icpc/51st/chengdu |
| egypt-2008 | found | scoreboard http://acm.fci-cu.edu.eg/archive/summaryENC08.html @20091019150710 |
| egypt-2011 | none | CMS 747 (ECPC-2012, 40 teams) has no rows; the held aast.edu crawl has no ECPC page; web search found ECPC results only for other years |
| ethiopia-2019 | partial | frozen_scoreboard https://github.com/mukerem/ICPC-Journey/blob/master/2019%20icpc%20ragional%20practice/2019%20Ethiopian%20National%20Contest/scoreboard_ethiopia.pdf |
| ethiopia-2022 | none | CMS 5481 (EtCPC-2023, 56 teams) has no rows; held copies are LinkedIn/Telegram; mukerem/ICPC-Journey has nothing for 2022; the acpc-cdn scoreboard link in our crawl is for a later edition |
| gwalior-2022 | none | CMS 5660 shell (0 teams); no sources; the 2026-11-16 hunt found Indian season lists show no such regional - existence doubt stands |
| kanpur-2021 | partial | rankings http://kanpur.indiaicpc.in/?page_id=698 @20220913161750 (preliminary online contest) |
| kharagpur-2021 | none | CMS 4839 shell (0 teams, no date); no sources; the 2026-11-16 hunt found no such regional - existence doubt stands |
| kuwait-2011 | none | CMS 748 shell (0 teams, no date); web source is the KCPC Facebook page; no other address known / kcpc2018.wordpress.com/history (held) lists KCPC results only from 2014 on; kuwait-2010 does have CMS standings, so KCPC existed then |
| kuwait-2012 | none | CMS 1350 shell (0 teams, no date); web source is the KCPC Facebook page; no other address known / kcpc2018.wordpress.com/history (held) lists KCPC results only from 2014 on; kuwait-2010 does have CMS standings, so KCPC existed then |
| kuwait-2018 | none | held crawl of kcpc2018.wordpress.com: only pre-contest pages and a History page listing KCPC 2014-2017 winners; no Wayback capture after Sept 2018; CMS 3589 (KCPC-2019, 34 teams/34 results) has no rows |
| lebanon-2009 | none | CMS 565 (Lebanese-2010, 0 teams) has nothing; the held website crawl is of acmacpc.org/archive/y2009 = the ACPC 2009 regional (wrong contest), and the held bau.edu.lb event page is about LCPC 2019 (4 Oct 2019, LAU and AUB first and second) - both look misfiled as lebanon-2009 web sources |
| lebanon-2018 | found | existing web source (LAU news, Wayback 20191115100742) is in fact a top-3 account: re-roled to rankings+report, scope top 3 (extra ops); the article dates the contest September 28 (catalogue 2018-09-29, CMS 2018-09-28) |
| malaysia-national-2013 | found | standings https://icpc.global/regionals/finder/OP-2014/standings |
| malaysia-national-2016 | found | standings https://icpc.global/regionals/finder/Malaysia-AlKhawarizmi-National-2017/standings |
| mongolia-national-2013 | found | standings https://icpc.global/regionals/finder/Provincial-Nine-2014/standings |
| mongolia-national-2014 | found | standings https://icpc.global/regionals/finder/Provincial-Nine-2015/standings |
| mongolia-national-2015 | found | standings https://icpc.global/regionals/finder/Mongolia-National-2016/standings |
| mongolia-national-2016 | found | standings https://icpc.global/regionals/finder/Mongolia-National-2017/standings |
| mongolia-national-2017 | found | standings https://icpc.global/regionals/finder/Mongolia-National-2018/standings |
| mongolia-national-2018 | found | standings https://icpc.global/regionals/finder/Mongolia-National-2019/standings |
| morocco-2012 | none | CMS 1551 (MCPC-2013, 46 teams) has no rows; morocco.acmacpc.org Wayback has only about/contact/rules/index of Dec 2012; acmacpc.org CDX has nothing for MCPC |
| morocco-2022 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| morocco-2023 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| myanmar-mcpc-2017 | found | standings https://icpc.global/regionals/finder/Myanmar-National-2018/standings |
| nigeria-2022 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| nigeria-2023 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| nzpc-2001 | found | standings https://www.cs.auckland.ac.nz/~mjd/prog_contest/results/nz01results.txt @20040830214401 |
| nzpc-2003 | found | standings https://www.cs.auckland.ac.nz/~mjd/prog_contest/results/nz03results.txt @20040830214639 |
| nzpc-2014 | found | scoreboard https://www.cs.auckland.ac.nz/~mjd/prog_contest/results/nz14results.pdf @20160212094251 |
| oman-capital-2025 | found | standings https://icpc.global/regionals/finder/OCPCCap-2026/standings |
| oman-capital-2026 | found | standings https://icpc.global/regionals/finder/OCPCCap-2027/standings |
| oman-coastline-2025 | found | standings https://icpc.global/regionals/finder/OCPCCos-2026/standings |
| oman-coastline-2026 | found | standings https://icpc.global/regionals/finder/OCPCCos-2027/standings |
| oman-midland-2025 | found | standings https://icpc.global/regionals/finder/OCPCMid-2026/standings |
| oman-midland-2026 | found | standings https://icpc.global/regionals/finder/OCPCMid-2027/standings |
| oman-oriental-2026 | found | standings https://icpc.global/regionals/finder/OCPCOri-2027/standings |
| oman-southern-2025 | none | CMS 9313 (OCPCSth-2026, 3 teams) has no standings rows (API asked 2026-11-23); held copies are Facebook shells and the MTCIT news item, which is about the national final (oman-2025: top 3 Enigma SQU, Libre SQU, Al-Istiqama GUtech), not the Southern sub-region round; that MTCIT page looks misfiled as a web source of oman-southern-2025 |
| oman-2018 | found | rankings/report https://www.cs.cmu.edu/news/2018/carnegie-mellon-qatar-team-wins-oman-programming-competition (champions) |
| oman-2023 | none | CMS 7656 (57 teams) has no rows; held nu.edu.om report only says their teams missed top 20; LinkedIn post shell; web search found nothing |
| oman-2024 | none | CMS 8776 has no rows; held UoB pages are about qualifying for OCPC April 2025 (= oman-2025?), not results; web search (OCPC 2024 winners) found nothing first-hand |
| pakistan-2018 | none | held UMT crawl: the 'First Round Online Ranking' link on the 2018 home page points to Final_Result_ICPC qaiser.xlsx, which (Wayback 20240720) was created 2016-11-23 = the 2016 online round; UMT news pages found are 2016/2017 results; CMS 3532 (Asia-Lahoe-2019, 70 teams) has no rows; web search found no 2018 result |
| palestine-2012 | none | staff.ppu.edu/mousa PCPC page (live, the contest's web source) is a history: first PCPC 2012 at Palestine Polytechnic University, 2014 and 2015 at the Arab American University; no results; CMS has no rows |
| palestine-2014 | none | staff.ppu.edu/mousa PCPC page (live, the contest's web source) is a history: first PCPC 2012 at Palestine Polytechnic University, 2014 and 2015 at the Arab American University; no results; CMS has no rows |
| palestine-2018 | partial | rankings/report http://www.birzeit.edu/en/news/birzeit-teams-claim-six-leading-spots-palestinian-collegiate-programming-contest @20181105174809 (champions (university only; Birzeit placed 1st, 3rd-6th, 9th)) |
| philippines-national-2015 | partial | rankings/report https://www.dlsu.edu.ph/?p=36793 (Metro Manila qualifier, top 3) |
| philippines-national-2019 | none | CMS 4178 (0 teams; url sites.google.com/ateneo.edu/pnpc2019) - not checked further in this run |
| saudi-arabia-2024 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| saudi-arabia-2025 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| sudan-2023 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| sudan-2024 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| taiwan-ncpc-2007 | none | CMS 1136 (Taiwan-2008, 92 teams/92 results) has no rows now; the held crawl of ncpc.ntnu.edu.tw/ncpc2007/ is empty and Wayback has only robots.txt for 2007-2009; ncpc.ntnu.edu.tw now only serves the current scoreboard; a Chinese web search (96學年度 得獎名單) found nothing live |
| taiwan-ncpc-2012 | found | standings https://icpc.global/regionals/finder/Taiwan-National-A-2013/standings (Group A); standings https://icpc.global/regionals/finder/Taiwan-National-B-2013/standings (Group B); standings https://icpc.global/regionals/finder/Taiwan-National-C-2013/standings (Group C) |
| taiwan-ncpc-2013 | found | standings https://icpc.global/regionals/finder/Taiwan-Invitational-2014/standings (Taiwan National NCPU Programming Contest); scoreboard http://ncpc2013.nsysu.edu.tw/ezfiles/264/1264/img/1414/summary.html @20131025014016 (Taiwan National Programming Contest (NCPC)) |
| taiwan-ncpc-2014 | found | standings https://icpc.global/regionals/finder/Taiwan-NCPU-2015/standings |
| taiwan-ncpc-2015 | found | standings https://icpc.global/regionals/finder/Taiwan-National-2016/standings |
| taiwan-1994 | none | no CMS id, no sources; the 2026-11-16 hunt already judged it probably a Taiwan-only selection - not hunted again |
| tehran-online-2022 | found | scoreboard http://icpc.sharif.edu/2022/iipc/scoreboard/ @20230326023453 |
| thailand-national-2012 | found | standings https://icpc.global/regionals/finder/Thailand-2013/standings |
| thailand-national-2013 | found | standings https://icpc.global/regionals/finder/Thai-Nat-On-site-2014/standings |
| thailand-national-2014 | found | standings https://icpc.global/regionals/finder/Thai-Nat-On-site-2015/standings |
| togo-2019 | none | CMS 4052 (TogoCPC-2020, 16 teams, 9 results) has no rows; the held crawl of cic.univ-lome.tg has no ICPC page; web search (French/English) found nothing |
| togo-2022 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| togo-2023 | none | CMS record is an empty shell (0 teams, no date; API rows none); held copies are Facebook/LinkedIn shells or announcements; scoreboard.acpc.global and acpcsb.acpc.global (live index + Wayback CDX), acpc.global/event/* and acmacpc.org CDX hold nothing for it; existence question in discussion item 3 |
| vietnam-2008 | none | itweek.org.vn/ACM_ICPC_VN Wayback (75 URLs) has no 2008 results page; CMS 14 (134 results) has no rows now; CMS problems URL HCM2008.pdf only |
| xian-2026 | found | scoreboard https://board.xcpcio.com/icpc/51st/xian |
| yinchuan-2020 | found | scoreboard https://board.xcpcio.com/icpc/45th/yinchuan |

Full lists, evidence per source and notes: `data.json`; scratch in `work/` (found.jsonl, tried.jsonl, api_rows.json, cms-records.json, archive_hits.json).
