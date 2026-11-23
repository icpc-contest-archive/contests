# Data scan 2026-11-23 — `struct`: structural integrity of the catalogue graph

Worktree commit of branch `data-scan-2026-11-23`, read-only. Everything here is in `findings/struct/`:
`ops.json` (139 ops, all `ok` under `apply_scan_ops.py --check`), `data.json` (full lists), `work/` (scripts and dumps).

## What was checked, and how to rerun

All scripts run from the worktree root (`cd _scan-2026-11-23/contests`):

| check | script | result |
| --- | --- | --- |
| validator | `python3 tools/validate.py` | 0 errors; 7 warnings (5 parent-dated-earlier, wf-2026 upcoming-but-past, 97 parent unknown) |
| next-chains: self, skips, missing links, two predecessors, cross-series vs lineage | `python3 ../findings/struct/work/chains.py` | 1 self-loop, 5 skips, 11 missing, 6 null-but-later, 5 double predecessors, 1 file out of order (nzpc) |
| year gaps | same script + `work/gaps.py` (CMS lookup of every gap year) | 55 series, 302 gap years |
| derived depth vs series `tier`, region vs parent region | `work/tiers.py` | south-africa, thailand-national wrong; below-subregional cases listed |
| catalogue `parent` vs the CMS hierarchy | `work/cmstree.py` (all `regionals-*.json`, `new_regionals-*.json`, plus the season-2014 tree fetched live from `https://icpc.global/api/contest/public/regionalresults/2014` because `regionals-2014.json` is empty), then `work/parent_vs_cms.py` | 63 unknown parents that the CMS has an answer for; 46 disagreements |
| date vs season, parent dated earlier, lineage mirrored, shared result sources | `work/misc_checks.py` | see below; lineage is mirrored everywhere |
| upcoming but past | validator + CMS season-2027 tree (`regionalresults/2027`, fetched 2026-11-23) | wf-2026; 8 more upcoming contests whose CMS date has passed |

The ops were applied to a copy of the catalogue (`work/sim/`) and `validate.py` run there: **0 errors; warnings go from 7 to 2** (nzpc-1998 parent-dated-earlier, 79 contests with no known parent). No new warning is introduced. The derived depth then matches every series header except the open cases below.

## What the ops fix (139 ops: 93 set, 1 unset, 45 provenance appends)

**Next-chains (20).** vietnam-national-2014 pointed at itself (→ vietnam-national-2015). The nzpc chain was cut around the four editions added on 2026-09-02 (2000→2001→2002→2003→2004, 2013→2014→2015). Also caribbean-national-2019→2020, thailand-national-2016→2024→2025 (it skipped 2024), turkey-2010→2019 (2011–18 are ruled shells), and the editions that existed before the autumn-2026 additions: hefei-2023, jinan-2023, kunming-2024 and nanchang-2019 had `next: null` while a 2026 edition exists; peradeniya, tajikistan, turkmenistan and wuhan 2025 had no next.

**Parents (54), each with a provenance line:**
- caribbean-national-2013…2019 → caribbean-YYYY. This is the CMS hierarchy, as for 2020/21.
- caribbean-2009 → wf-2010. The 2009 results page marks the winner UCLV1 "Clasificado para la Final Mundial 2010", and UCLV is in the WF 2010 standings.
- naq-2012, naq-2013 → the 11 NA regionals. In the CMS each NAQ id is the qualifier subcontest of one regional.
- naq-2014…2021 → the NA regionals of the season that came after the NAQ. naq-2021 leaves out mausa-2021, which ran on 2022-02-06, before the NAQ. The basis is the organisers' NAQ page (`https://www.icpc.org/icpc-north-america-qualifier`, Wayback 20210625140009): "an online, pre-regional programming contest to help coaches choose teams for regional competitions", one site per NA region. It also matches DEFINITIONS ("NAQ feeds many regionals").
- **south-africa-2008…2018 → wf-(Y+1)** (was acpc-Y), and the series tier becomes `regional`. The evidence:
  - The CMS puts these regionals directly under the Africa–Middle East super-region.
  - The ACPC standings for 2010–2018 contain no South African or other sub-Saharan team.
  - The WF standings for 2009–2019 have South African teams every year (UCT; Stellenbosch, "Africa and the Middle East Champion" in 2011; Pretoria in 2018).
  - south-africa-2019 stays under acpc-2019, as the CMS has it.
- **The 11 NA regionals of 2020 → nadc-2021** (was nac-2021). The icpc.org 2020-21 timeline (Wayback 20210923173052) gives the order: regionals Feb 27–Mar 7, Division Championships Apr 22, NAC Aug 8–15. In the CMS every 2020 regional sits under ICPC-NADC 4596.
- **tehran-2023 → wf-2024** (was awc-2023). awc-2023 ran on 2024-03-30, before Tehran (2024-05-30/31), and its standings list no Iranian team. The awc-2024 standings do list Iranian teams. The WF 2024 standings list Sharif (13th) and Tehran.
- wf-2026 and wf-2027 had no `parent` key; they get `parent: null` like every other World Finals.

**Dates (4), which resolve the parent-dated-earlier warnings:**
- brazil-first-phase-2010: 2011-09-17 → **2010-09-18**. 2011-09-17 is the CMS copy of the 2011 date. The 2010 date comes from the hist/2010 page, the problem booklet and a BOCA scoreboard stamped 18-09-2010.
- south-america-north-2011: CMS placeholder 2011-06-17 → **2011-11-05**.
- south-america-north-2012: CMS placeholder 2012-10-11 → **2012-11-10**.
- For both south-america-north dates, the sources are the contest's own CMS site dates and the Latin American problem sets used in Colombia and Venezuela ("November 4th-5th, 2011" and "November 9th-10th, 2012", Contest Session). All the Latin American sibling contests carry the same dates.
- **wf-2026: date 2026-11-20 removed; it stays upcoming.** It did not run:
  - `worldfinals.icpc.global/2026/` said "November 15-20, 2026" on 2026-08-28 (Wayback).
  - The same page says "April 4-9, 2027" (Grand Hyatt, Oud Metha, Dubai) from 2026-11-02 (Wayback, and live today).
  - The WF schedule (`docs.icpc.global/wf-schedule/`) gives the contest as "Day 4" with no calendar date, so no date is set.

**Series headers (28):**
- thailand-national tier `regional` → `subregional` (7 of its 8 editions are under the Thailand regional).
- south-africa tier `subregional` → `regional` (see the parents above).
- `rotating_host: true` on 26 Asia host-city regionals whose gaps are structural: beijing, changchun, chengdu, dalian, guangzhou, hangzhou, hefei, jinan, kunming, nanchang, nanjing, shanghai, tianjin, wuhan, xian, hong-kong, macau, kanpur, kharagpur, kolkata, gwalior, mathura, chennai, kuala-lumpur, manila, singapore. No series had the flag before.

The validator's parent-dated-earlier warnings are now answered:
- brazil-first-phase-2010, colombia-maraton-2011 and colombia-maraton-2012 had wrong dates.
- tehran-2023 had a wrong parent.
- nzpc-1998 is discussion item 1.

brazil-first-phase-2010 is probably also among the description round's unapplied fact differences. If another agent sets the same date first, my op fails on its `old` guard, which does no harm.

## Items for discussion with Fredrik

### 1. nzpc-1998 and australia-1998 (validator warning); is the NZPC mainline at all?
- **Question.** nzpc-1998 (1998-10-10) has parent south-pacific-1998 (1998-09-29 in the catalogue; the CMS and every site say 1998-09-19). Is the date wrong, or the parent?
- **Evidence.**
  - The NZPC 1998 statement (`~mjd/prog_contest/problems/NZPC1998.pdf`, OCR) prints "NZ programming Contest 10/10/98", with problems worth 5 points each. So the NZPC ran three weeks *after* the regional and could not feed it. The date is right and the parent is wrong.
  - The standings source of nzpc-1998, `icpc.baylor.edu/past/icpc99/Regionals/NZ98/Standings.htm`, is not the NZPC. It is titled "South Pacific Region – New Zealand", and its teams and scores are exactly the New Zealand rows of the regional's results (`regionalresults1998.pdf`, OCR: "the three little pigs, Otago, 5/710" is regional rank 5).
  - In the same way, **australia-1998** is only `Aus98/Standings.htm`, "South Pacific Region – Australia" = the Australian rows of the same regional. That page is already a source of south-pacific-1998. So australia-1998 duplicates south-pacific-1998.
- **What it implies.** Was the NZPC ever a qualifier?
  - The CMS files it under the South Pacific only in 2012.
  - It is an open national contest with levels, mostly held in August.
  - 18 nzpc editions have no parent; 7 got south-pacific parents by analogy.
- **For keeping NZPC mainline:** the CMS did register it under the regional in 2012, and it usually runs before the regional. **For moving it out:** no document says NZPC results gate the regional, and the 1998 edition ran after it.
- **Recommendation.**
  - Move the NZ98 standings to south-pacific-1998 (`scope: New Zealand`).
  - Retire australia-1998 as a duplicate.
  - Keep nzpc-1998 as the NZPC with `parent` unknown, or move the NZPC series (except 2012/13, which the CMS attests) to `registry/non-mainline.yaml`.
  - The south-pacific-1998 date 1998-09-29 also looks wrong: the CMS and the sites say 1998-09-19.
  - Missing NZPC editions, if the series stays: 1999 (`NZPC1999.pdf` exists) and 1990–97.

### 2. Alberta (23) and Lethbridge (13): qualifiers of the RMC, or not mainline?
- **Evidence.**
  - The CMS files ACPC 2011–2023 and LCPC 2013–2023 as subcontests of Rocky-Mountain.
  - But **alberta-2019 (2019-11-23) and alberta-2023 (2023-11-25) ran after the RMC** (2019-10-26, 2023-11-04).
  - The ACPC site (2024) calls it "an opportunity for university and college students in Alberta to excel in a programming competition". It has cash prizes by division and says nothing about qualification.
  - I found no page saying either contest selects RMC teams.
- **For parent rmc-YYYY (CMS):** the CMS is the formal structure, and the two contests are the same kind as the NENA subregionals. **For non-mainline:** they gate nothing, and two editions came after the regional.
- **Recommendation.** Ask the RMC director (Howard Cheng runs LCPC and is RMC chief judge). The prepared CMS parents, with the before/after-RMC flag, are in `data.json` → `alberta_lethbridge_cms_parents_not_applied`. I did not apply them.

### 3. Asian national contests in the CMS "Asia Provincial / National (non-host)" bucket (18)
- **Contests.** mongolia-national-2013…2019, philippines-national-2014/15/19, taiwan-ncpc-2014…16, malaysia-national-2013/16/18, myanmar-mcpc-2019, vietnam-national-2014.
- **Evidence.**
  - The CMS parent is the provincial bucket directly under Asia, not a regional.
  - These are years when the country hosted no regional; in their other years the catalogue links them to the home regional.
  - The same buckets hold dozens of Chinese, Thai, Indonesian and Vietnamese provincials that are triaged `minor`.
- **For keeping:** "family ruling 2026-09-04"; the winners may have been invited to some Asian regional. **For non-mainline:** this treats them the same as their bucket-mates, and no specific advancement is known.
- **Recommendation.** Move them to non-mainline unless a team's advancement to a named regional can be shown. The list is in `data.json`.

### 4. NAQ 2022–2026 (5): which regionals in the division era?
- From season 2023, mausa, scusa and seusa (and later ecna, nena and gny) are `subset_of` views of south-na and east-na.
- **Proposal.** Use the same rule as the applied 2014–2021 ops: the classic regional-level contests held after the NAQ. The other option is to list the division contests instead of their views.
- The lists are in `data.json` → `naq_2022_2026_parent_proposals_not_applied`. Since 2019 the CMS files the NAQ under NAC/NADC, which does not match what the NAQ is for.

### 5. Duplicates
- **brazil-first-phase-1996 and -1997 are the South America regionals of 1996 and 1997.** Both were single-site, single-stage contests: I CONSUN at UFMG, and II CONSUN at Unicamp with teams from 5 countries. The two-phase format began in 2004. south-america-1997 already exists, and south-america-1996 does not.
  - This was flagged on 2026-10-22 (reports/existence-evidence) and is still open. It also breaks the chain (brazil-first-phase-2008 has two predecessors, 1997 and 2007).
  - Recommendation: merge -1997 into south-america-1997, re-file -1996 as south-america-1996 (parent wf-1997), and add brazil-first-phase-2004.
- **shanghai-2022 and shanghai-2023 vs aec-2022 and aec-2023 (state only).**
  - In the CMS, "ICPC Asia Shanghai Regional" entries 6160 and 7701 sit beside the EC-Final entries 5537 and 7694 under the AEC node, on the same days.
  - Every source of the two Shanghai contests is EC-Final material: the QOJ/UCup stage 11 and 23 boards, a Codeforces announcement, and a JS-only xcpcio board.
  - Unchanged since the earlier reports; still open.
- **australia-1998**: see item 1.

### 6. Asia East: do the 2024/2025 regionals advance to the EC-Final?
- From season 2025 the CMS files every Chinese regional under the AEC (chengdu, hangzhou, hong-kong, kunming, nanjing, shanghai, shenyang, wuhan, xian 2024/2025). Before that it filed them directly under Asia East.
- The catalogue has wf-YYYY for all of them, and no contest has an aec parent. By contrast, the Asia Pacific and Asia West regionals feed apc and awc.
- **Question.** Should `parent` be the EC-Final, `[wf, aec]`, or stay wf?
- **Recommendation:** `[wf-Y, aec-Y]` for seasons where the EC-Final awards WF slots on top of the regionals. This needs the AEC rules of each season.

### 7. thailand-national-2024: the parent awc-2024 is wrong, and the right one is unknown
- awc-2024 is the Asia West championship, and its standings have no Thai team.
- Chulalongkorn did play APC 2025, but the APC 2025 selection names five regionals (Taichung, Seoul, Jakarta, Hanoi, Yokohama) and not the Thailand National.
- The contest's date 2024-11-16 also conflicts with the organiser schedule in its own provenance (national round 7–8 Sep 2024).
- **Recommendation.** Leave it for a ruling: apc-2025, unknown, or remove the parent.

### 8. Upcoming contests whose CMS date has passed (8)
azerbaijan-2026, east-siberia-2026, nanchang-2026, pacnw-2026, pakistan-2026, peradeniya-2026 (CMS 2026-08-15), torneo-chileno-2026 and west-siberia-2026. These are for the upcoming→ran routine (the rule needs a result source). wf-2027 may move too, now that wf-2026 is in April 2027.

### 9. Year gaps (302 in 55 series; `data.json` → `gaps`, each with a verdict)
- **Missing contests that ran** (for `missing-contests`):
  - seusa-1989, -1991, -1992, -1997. The UCF team record (Wayback 20140630, held at `seusa/seusa-1988/rankings/20140630-wayback-54ecd414`) lists SE USA regional placings for every season 1986-87…1998-99.
  - nzpc-1999 (if the NZPC stays mainline).
  - brazil-first-phase-2004.
- **Not held, confirmed:**
  - tehran-2021: the organisers' archive `icpc.sharif.edu/2024/archive` skips 2021. CMS 4841 is triaged "structural" and should be "cancelled".
  - dhaka-2000: "Not hosted".
  - vietnam 2009/2011/2014 and jakarta 2011: absent from the CMS Asia lists of those seasons.
  - awc 2020, poland 2020, ctuo 2020, cyprus 2020–23, torneo-chileno 2020–22, turkey 2011–18 and thailand 2020–22: triaged cancelled or junk.
- **Structural:** the 26 rotating host cities.
- **Unknown (no CMS entry; web not checked): 38**
  - algeria 2015–17 and 2019
  - benin, nigeria and togo 2018
  - cyprus 2024
  - kabul 2021–22
  - kuwait 2013
  - malaysia-national 2015 and 2017
  - morocco 2024
  - nena-north 2010
  - oman 2015
  - philippines-national 2016–18
  - taiwan-ncpc 2008–11
  - thailand-national 2018–23
  - thailand 2010 and 2023–24
  - turkey 2024–25
  - vietnam-national 2016

### 10. CMS ids accounted for nowhere
- 713 ids in the regionals dumps are in neither the catalogue nor `registry/cms-triage.yaml`.
- 652 of them are in the unmerged `registry/cms-triage-proposed.yaml` (2026-09-02).
- The other 61 are nowhere (`data.json` → `cms_ids_unaccounted.nowhere`): mostly 2010–2013 Romanian subregions, Maratona Inter-Universitária, Kanpur preliminaries and Asia-Provincial buckets.
- The validator checks only the catalogue's ids, so "every CMS DB entry remains considered" does not hold yet.
- **Recommendation:** merge or triage the proposed file.

## Smaller findings (no ops)
- **DEFINITIONS, Levels.** Below-subregional now means BAPC preliminaries, ethiopia-2019 (under south-africa-2019 under acpc) and the Oman site contests oman-capital/-coastline/-midland/-oriental/-southern 2025–26 (under oman under acpc). The text naming "African national contests under the South Africa regional (2016–2019)" needs updating after the south-africa fix.
- **CMS-vs-catalogue disagreements left alone** (the catalogue is backed by evidence or is a deliberate model; `data.json` → `parent_vs_cms`):
  - nordic-2006/07 and bapc-2007: the CMS has them directly under the WF.
  - caribbean-2010: the CMS puts it under Mexico & Central America 2010, but WF 2011 has a Havana team.
  - south-pacific-2024: the CMS has the WF; the catalogue has apc-2025.
- **nzpc.yaml order.** Contests are out of chronological order (2000, 2001, 2003 and 2014 sit at the end of the file). It is cosmetic; I did not reorder.
- **Placeholder dates.** gran-premio-mexico-2015…2020 and gran-premio-centroamerica-2018/19 are dated YYYY-01-01, outside their season.
- **Misfiled source (bycatch for the source agents).** The icpcarchive file `…/2012 Latin American Regional Contest/problems.pdf` on south-america-north-2012 is the **2013** Latin American set ("November 8th-9th, 2013").
- **Date doubts (for the facts agents).**
  - colombia-maraton-2011: catalogue 2011-09-08, CMS site dates 2011-10-08.
  - brazil-first-phase-2008: the catalogue has the Final's date; the first phase was 2008-09-20.
  - brazil-first-phase-2017: catalogue 2017-05-31; the documents say 2017-09-09.
  - These two are in the description round's differences.
- **kunming 2022/2023.** The CMS entries are triaged "structural", although they are named "The 2022/2023 ICPC Asia Kunming Regional Contest". Probably "cancelled" is meant.
- **Shared result sources without scope or as_of across editions.** 66 cases, in `data.json` → `misc_checks.shared_result_source_no_scope`, for example rmc23.kattis.com on rmc-2022 and rmc-2023, and acm.ro/results.htm on 16 seerc editions. These are for the source agents.
- **Not blocked.** web.archive.org and icpc.global answered from the device shell. One Wayback/organiser probe for Tehran 2021 timed out, and the organiser's archive page answered instead.
