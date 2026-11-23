# psets-b — missing problem sets: Latin America, Africa & Arab, Asia Pacific, Asia West, Asia East

Data scan 2026-11-23, agent psets-b. Output: `ops.json` (67 ops, `apply_scan_ops.py --check`: 67 ok), `data.json` (targets, every find with its evidence, problem names read, what was tried per contest, the discussion lists), scratch scripts in `work/`.

## Scope and method (rerunnable)

Targets: every contest of a series whose header `region` is one of the five, that ran (no `status: upcoming`) and has no source with role `problemset` or `problem`: **329 contests** at the start (`work/targets.py`). By region: Africa & Arab 142, Latin America 61, Asia Pacific 51, Asia East 38, Asia West 37. **55 of them get a problem-set source** from ops.json (Latin America 25, Asia East 23, Asia West 4, Asia Pacific 3, Africa & Arab 0).

1. **Own holdings:** every `archive/<series>/*/website/*/site-manifest.json` of the target series (fetched pages, unfetched in-scope links, offsite links) scanned for statement-like URLs (`work/scan_holdings.py`, `work/filt.py`), then each candidate copy opened (pdftotext / HTML) and checked for edition, date and titles.
2. **Host indexes:** scorelatam.naquadah.com.br, sppcontests.org/archive, onlinejudge.org/contests/ (all 207 hosted-contest directories titled), aapc.org.ar/tap-ediciones-anteriores/ (held), the Maratona SBC first-phase booklets (their cover lists the contests that sat the same set), icpcvn.github.io, kitihounel/competitive-programming-africa, Dinneen's Auckland archive, wc.indiaicpc.in via Wayback.
3. **Online judges:** HDU problem-archive search by source (`work/hdu.py`, `work/hdu_batch.py`, `work/hdu_results.json`), compared title by title with each set; POJ source and title search; the public Codeforces gym list (`work/cf_gyms.json`).
4. Wayback CDX from the device shell for dead hosts.

Every added source was opened and tied to the edition (title page and date, or all of the set's own titles). `contains` says what the document holds; HDU lists are `judge: hdu`, `contains: [names]`.

## What the ops do (61 appends, 6 sets)

- **Latin American shared sets (25 contests).** The Maratona SBC first-phase booklets 2020–2025 say on their cover which contests used the same set; the booklet (the same address the brazil-first-phase contest cites) is added to tap-2020, bolivia-national-2022..2025, torneo-chileno-2023 and, with `scope` naming the round, gran-premio-mexico-2020/2021/2024/2025 and gran-premio-centroamerica-2020..2025 (16 ops). torneo-chileno-2018/2019 get the joint "Torneo (Chileno—Argentino) de Programación" booklets and tap-2020 the organisers' Spanish booklet, from aapc.org.ar. colombia-maraton-2023..2026 get their UVa hosted-contest directories (385–388; same form as 2012–2018). mexico-2026, south-america-north-2026 and south-america-south-2026 get the `problemset` role and `contains: [statement]` on their existing scorelatam latam-2026/ source, as their sibling contests already have (6 `set` ops).
- **Chinese regionals 2007–2013 (23 contests):** HDU source-search lists whose titles equal the set's (sets that came from the Live Archive volumes): beijing-2007/2008/2011, changchun-2012/2013, changsha-2013, chengdu-2007/2008/2010/2011/2012, dalian-2011, fuzhou-2010/2011, hangzhou-2008/2010/2012, harbin-2008/2010, jinhua-2012, ningbo-2009, tianjin-2010/2012.
- **Statements in our own crawls** (`as_of` = the snapshot): awc-2022 (wc.indiaicpc.in/problem_sets.pdf), kabul-2017, taiwan-2015, kanpur-2004 (IIT Kanpur acm2004/questions.html), manila-2005 (problems.html plus the 8 per-problem statement pages as `problem` sources, per the 2026-11-14 index-page ruling), pakistan-2017 (live UMT PDF linked from the held page), south-pacific-division-2021 (sppcontests archive).

Problem names and letters read from the documents for contests without names are in `data.json` → `names` (awc-2022, kabul-2017 letters, manila-2005, south-pacific-division-2021, colombia-maraton-2023..2026, torneo-chileno-2018/2019). Creating or updating sets is for the problems agents.

## Items for discussion with Fredrik

Full lists and links in `data.json` → `discussion`.

1. **awc-2019's problem set is the AWC 2022 set.** The source on awc-2019 (wc.indiaicpc.in/problem_sets.pdf @20240205) was created on 2023-05-19. It holds the 11 problems of the Asia West Continent Championship 2022, which ran on 2023-05-20; the Contest Director's report on the same site gives 11 problems. Set awc-2019 (11 names) came from that file. awc-2022's own set has only 10 labels, read from a codemarshal "dhaka-22" scoreboard that looks like the Dhaka regional. *For moving:* the file's date and the report agree. *Against:* nothing found. *Recommend:* move the set and the source to awc-2022. ops.json only adds the source to awc-2022.
2. **Rounds of the Gran Premio de México / Centroamérica.** One catalogue contest per year, but several rounds ("fechas") with different sets. ops.json adds the round that used the Brazilian first-phase set, with `scope`. The other rounds are Codeforces gyms (16 listed for 2020–2026). I could not open them from here: Codeforces refuses the fetchers, and its standings API needs a login. *For adding them with scope:* the same approach is already used for 2023 and 2026. *Against:* a set membership would make the contest's problem list partial, because the model has rounds-as-divisions only for divisions. *Recommend:* add the gyms with scope from a logged-in browser. Leave the GP contests without set membership, or model rounds like divisions.
3. **Set membership for the shared Latin American sets.** tap-2020 (whole contest) should join brazil-first-phase-2020. torneo-chileno-2018/2019 sat the TAP sets: the booklet is titled "Torneo (Chileno—Argentino)" and the contest day is the same, so that is two independent sources. Those TAP sets carry English titles, while the statements are Spanish. Under the statement-title ruling the Spanish titles should be the names. *Recommend:* add the members, use the Spanish names with the English ones as other_names, and decide the set name (joint, or TAP's if TAP lent it).
4. **Misfiled or truncated sources found on the way** (not in my target list, so no ops): tap-2018/2019/2021/2022 all cite the truncated https://codeforces.com/group/YjFmW2O15Q/contest/10; the organisers' page gives the right contest and statement PDF per year. taiwan-ncpc-2014/2015 are the summer private-university contests, but they cite the autumn NCPC's 歷年題庫 (lìnián tíkù, "past years' problem bank") at ncpc.ntnu.edu.tw/files.html. *Recommend:* fix the TAP URLs. Check CMS 2553/2969 before moving the Taiwan sources.
5. **Small fixes for the problems/names agents:** three set titles with import glitches (chengdu-2011 "Holiday's Accommodatio", fuzhou-2010 "… Description", hangzhou-2008 "D&eacute;j&agrave; vu"). colombia-maraton-2026 is named "XXXIX", but the 2026 set is the XL Maratón. HDU's hefei-2008 list is the online qualifier and was left out on purpose.

## Not found / not reached

`data.json` → `tried_nothing_found` (47 entries): what was tried per contest. This covers the 2026 Chinese regionals (no statement published that is reachable yet), the lost Taiwan 2004/2007 and SPPC 2017 divisional PDFs, Hong Kong 2018, Chinese 2006–2009 sets that are on neither HDU nor POJ, JCPC/SCPC zips that exist in Wayback only as 404, and others. `not_reached` (227) lists contests not individually hunted. They are mostly the Africa & Arab national contests, which have CMS standings only: the veins checked for them (kitihounel repo, ACPC/national crawls in our archive, the Codeforces gym list) gave nothing for the target years. The rest are older Asia Pacific/West nationals.

## Limits

- The device shell was cut off several times; results were saved after every step and the ops re-checked at the end. While I worked, the worktree changed under me (other agents' ops were applied). One of my finds (latam-2026 contest.en.pdf) had already been added and was dropped.
- QOJ, SPOJ and Codeforces gym pages are blocked from the device and from the cloud fetcher. COJ (coj.uci.cu) does not answer. vjudge is no longer a registered judge.
