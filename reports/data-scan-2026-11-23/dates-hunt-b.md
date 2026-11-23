# dates-hunt-b: blank dates, Latin America / Africa & Arab / Asia Pacific / Asia West / Asia East

Area: contests that ran (not `status: upcoming`) with no `date`, in those regions. 79 found in the worktree (`work/targets.json`).
Rule: `date` = the contest day itself.

## Ops: 28 (14 `set` date, old null, + 14 provenance `append`), `--check`: 28 ok, 0 failed
Not duplicated: dates-b's ops already cover nzpc-2000, nzpc-2023, south-america-north-2020/2022, south-america-1997 (not yet applied in the worktree; my nzpc-2023 reading agrees: nzprogcontest.org.nz/results says Saturday 19 August 2023).

NZPC (11), evidence is the organisers' own announcement pages via Wayback (all dates are Saturdays):
- 2004-08-14 (cs.auckland.ac.nz/~mjd/prog_contest/NZinfo.html, 20040713), 2007-08-04, 2008-08-09, 2009-08-22, 2010-08-07 (nzprogcontest.org.nz/NZPCNews.php snapshots 2007-2010; news log), 2011-08-06 (NZContestHome.html 20110717), 2014-08-09, 2015-08-08, 2017-08-19 (public.webdev.aut.ac.nz/NZPC/Contest/ home snapshots), 2020-09-26 (registration PDF updated 1 Sep 2020; moved from 12 Sep), 2021-09-11 (registration PDF + NewHomePage.aspx; results page says held online).
Central America (3), by the shared-set ruling: central-america-2019 2019-11-09, central-america-2020 2021-07-10 (also: the held scorelatam latam-2020 scoreboard is its own source, as_of 20210710), central-america-2021 2022-04-02. Medium evidence (sibling contests on the same latam set, none states Central America's day itself).

## Checked, not resolved (contest left blank)
- NZPC 2016, 2018, 2019, 2022: no announcement snapshot found (Wayback was refusing connections intermittently). Hints: 2016 scoreboard "Last Update: Monday, 8 August 2016" (so contest probably Sat 2016-08-06); 2018 Open scoreboard "Last Update: Sat 15 Sep 2018" (candidate 2018-09-15, not applied: a last-update stamp). 2002, 2001, 2003: nothing found (PDFs undated; the old Auckland ~mjd pages hold no dates).
- South Pacific 1991-1997 (sppcontests.org archive pages/PDFs, OCR'd 1993/94/95/97 result PDFs): the pages and the scanned result sheets carry no contest date. Other 1990s dates not found on the web either.
- Taiwan 1994-97, Shanghai 1996/97, Dhaka 1997, Australia 1998: held swt.edu / Baylor pages give rankings only, no dates.
- Held-copy scan (`work/scan.py`, `work/scan_out.json`) of all 79 contests' archive folders: no usable dates for the African/Arab national contests (Facebook-only sources), gran-premio-centroamerica 2021/2023/2025, kharagpur 2020/21, saudi-arabia, shenyang-2019 (placeholder `xxx.yyy.edu` source), colombia-maraton-2026 (JS-only page), amritapuri-2020 (page mentions an award ceremony "21st August" but not the contest day).
- kuwait-2026: unchanged (see dates-b item 3).

## Items for discussion with Fredrik
1. **morocco-2023 has a source from the wrong edition.** https://www.uir.ac.ma/en/actualite/mcpc-programming-competition says "weekend of October 16th and 17th, 2021" (the MCPC 2021, already `morocco-2021`, date 2021-10-17). By the "remove when the address never served that edition" ruling it should go (or be moved to morocco-2021 as web). Not removed by me. Recommendation: move it to morocco-2021.
2. **Old pre-1998 dates (South Pacific 1991-97, Taiwan/Shanghai/Dhaka 1994-97):** the only sources are results without dates. Option: leave blank (recommended) or accept the year only. The sppcontests.org "Contest Report" for 1997 could hold a date but has no separate link.
3. **NZPC 2018** candidate 2018-09-15 from the scoreboard stamp: apply? Recommendation: wait for a news page.
4. Wayback intermittently refused connections from the device shell (use `env no_proxy='*'` + retries; `work/wb.sh`), which limited the NZPC 2016-2022 pass; a rerun later should find the 2016/2018/2019/2022 home snapshots (public.webdev.aut.ac.nz/NZPC/Contest/Default.aspx has snapshots 2013-2023; CDX lists them).
