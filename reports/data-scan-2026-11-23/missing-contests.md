# Missing contests — data scan 2026-11-23 (agent `missing-contests`)

Area: contests that ran in the ICPC hierarchy but are not in the catalogue (the 2026–27 season excluded:
the `current-season` agent has it). Worktree: `_scan-2026-11-23/contests` at the scan commit, read only.

## What was checked, and how (to rerun)

Scripts are in `work/` (run from inside the worktree; they read the CMS dumps in `$HOME/mnt/icpc-contests`):

- `work/dump.py`: catalogue summary → `work/catalogue.json`.
- `work/cmsidx.py`: every CMS id in `all_contests.csv`, `new_all_contests.csv`, `regionals-*.json` and
  `new_regionals-*.json` (4,273 ids) checked against the catalogue, the non-mainline registry, `cms-triage.yaml`
  and `cms-triage-proposed.yaml`. 53 ids are in none of the four (`data.json` → `cms_unaccounted`).
- `work/gaps.py` + `work/gapcms.py`: every year gap inside a series (55 series, 297 gap-years; `rotating_host`
  is not set on any series), each checked against the CMS by name and year (`data.json` → `series_gaps_with_cms_hits`).
- Known candidates from the brief: each was looked up in the catalogue and the registries, then researched on the web
  and in the Wayback Machine (`data.json` → `known_candidates`).
- The 34 "ICPC-looking" problem sources without a mapping (`reports/problem-uuids-import-2026-11-01.md`):
  classified (`data.json` → `problem_sources_34`).
- Online judges: the local Codeforces gym list (`codeforces_gym_contests.json`, 2,535 gyms, April 2026): 580 gyms
  with an ICPC-looking name are not a source of any contest or problem. All 580 were classified (`data.json` →
  `codeforces_gym_unmapped_icpc_looking`). The QOJ ICPC tree's "not in the catalogue" list
  (`reports/qoj-tree-2026-11-12.md`) is already empty. Kattis was not enumerated: its problem-source pages answer
  200 for any name, so they cannot be used to probe.
- Ops checked with `python3 tools/apply_scan_ops.py --check ../findings/missing-contests/ops.json` (17 ok, 0 failed),
  then applied to a copy of the catalogue in `work/vt/` and validated there. My ops add no error or warning. The
  worktree changed during the scan (08:56 UTC), and since then validate.py reports 8 errors in other contests, from
  other agents' changes (dhaka-2022, ncna-2009, pacnw-1999, rmc-2023, south-america-2002, swerc-1999,
  west-neerc-2004, wf-1994). They are there before and after my ops.

## What the ops do (17 ops: 9 `insert_contest`, 6 `set`, 2 `append`)

Every new contest got a date and sources, each opened by me, plus provenance lines.

- **bapc-prelims-2005, -2006, -2007, -2008** (BAPC preliminaries; the series starts in 2009 now). Each year, the
  universities' own contests (DKP Delft, UKP Utrecht, TKP Twente, Eindhoven, Groningen, Leiden, Amsterdam) were run
  on one day with one problem set as the BAPC qualifying rounds. This is the same shape as bapc-prelims-2009, whose
  set is headed "BAPC 2009 Preliminaries".
  - 2005-10-01: the qualifiers PDF ("Qualifying Rounds Problems, October 1, 2005"). The BAPC 2005 site lists
    "preliminary rounds results" for four sites, and the Eindhoven page uses the PDF's problem names.
  - 2006-09-30: `qualif2006.pdf` ("BAPC 2006 Leiden — Qualifying contest"). The jury report covers six sites.
  - 2007-10-06: the bapc.nl news item ("preliminary contests were held on various locations … The problem set for
    these contests is available"), four site scoreboards, and the PDF titled "BAPC preliminary contest".
  - 2008-10-04: the 2008.bapc.eu news item lists "BAPC voorronde Eindhoven/Utrecht", DKP and TKP. **That the sites
    shared one set is inferred** (same day, eight problems A–H at three sites), so the DKP set has scope Delft.
- **brazil-first-phase-2004** (2004-10-02, 14 sites, 34 teams to the final): SBC's history page for 2004 says the
  Maratona ran in two phases for the first time. The problem set is titled "Brazil Sub-Regional, October 2rd, 2004".
  I added the vagas page, the problem page and 13 site result pages. `brazil-first-phase-1997.next` went from
  2008 to 2004: the chain skipped the existing 2005–2007, and 2007 also points to 2008.
- **vietnam-national-2016** (cms 3049; it was in neither the catalogue nor any triage registry). Another agent
  inserted it into the worktree during the scan, with the CMS standings only and no date. My insert was therefore
  turned into four ops on that entry:
  - `date` 2016-10-30, with its provenance line
  - `sites`: Nha Trang University, online
  - a new `scoreboard` source: the Wayback copy (20161106062218) of the DOMjudge final standings, "The 2016 ACM-ICPC
    Vietnam National Online Contest, Hosted by Nha Trang University", start 2016-10-30 08:00 ICT.
  Its CMS record lists 178 ranked teams in our dump.
- **seusa-1989, -1991, -1992, -1997** (year gaps in the Southeast USA series). The UCF team record page ("UCF is in
  the Southeast USA Region") gives UCF's regional places for 1989-90, 1991-92, 1992-93 and 1997-98. The same page is
  already the result source of seusa-1988, 1990, 1993 and 1996. Each new edition has that page as `rankings`
  (scope "UCF teams"); date and host are not set. The `next` of seusa-1988, 1990 and 1996 was re-pointed.

## Known candidates: outcomes

| candidate | outcome |
|---|---|
| Atlantic Canadian 2020–2026 | ran, but no longer an ICPC preliminary → item 1 |
| alberta-2026 | 2026–27 season → current-season agent (Kattis acpc26) |
| Swedish Championships 2002–2004 | already in the catalogue as nordic-2002..2004 (joint Norwegian/Swedish championships); only the problem-source mapping is wrong |
| nwerc-1993 | already in the catalogue as werc-1993 (Swansea; ETH archive `B_EU_NWRC/1993`); a mapping fix |
| swerc-1991 | no evidence of a 1991 SWERC: Europe had one ERC in 1991 (erc-1991, Gent), and the ETH SWERC archive starts 1993. The one problem is probably mislabelled |
| brazil-1999..2003, brazil-first-phase-1998..2003 | not missing: those years the Maratona was the Brazilian sites of the South America regional (hist pages: "Regional Sul-Americana do ICPC") = south-america-1998..2003 |
| brazil-first-phase-2004 | **inserted**; 2005 and 2006 are present |
| ncna-2010, sa-2001 (= south-america-2001), ACPC 2018 | present |
| Calgary CPC 2017–2026, CodeSprintLA 2020 | no CMS record; local contests → non-mainline if wanted |
| 34 unmapped problem sources | 5 map to existing contests, 1 to the new bapc-prelims-2006; the rest are non-mainline, not ICPC, or provincial (`data.json`) |

## Items for discussion with Fredrik

**1. Atlantic Canadian Programming Competition 2020–2026: put it in the non-mainline registry?**
After nena-atlantic-2019 (cms 4079, the last CMS record) the contest kept running on Kattis
(`atlantic-canadaNN.kattis.com`, 2021–2026). Science Atlantic now calls it "ACPC Programming Competition (formerly ICPC
Preliminary Round)". Dalhousie's 2024 news says it "formerly served as the ICPC round for the Atlantic Canadian region".
- For the registry: it is a real contest with its own problems, and our problem archive already holds 2021–2026.
- For leaving it out: it no longer gates anything.
- Examples: https://atlantic-canada22.kattis.com/contests/atlantic-canada22/standings, https://scienceatlantic.ca/committees/compsci/icpc/
- **Recommendation:** non-mainline entries atlantic-canada-2020..2025, and 2026 from the current-season agent.
  nena-atlantic stays ending at 2019.

**2. Taiwan national contests (NCPU / NCTU / TOPC): mainline or not? (30 unaccounted CMS ids, 2015–2025)**
The catalogue has taiwan-ncpc-2014..2016, which are really the NCPU (private universities) and NCTU (technology
universities) contests, with no parent. The same contests for 2017–2025 have CMS ids but are in no registry. The
Taiwan Online Programming Contest (TOPC) also appears every year.
- For mainline: they are ICPC-branded and registered under the Taiwan regional.
- Against: TOPC is an online qualifier (Q5: part-of-parent). Nothing shows NCPU or NCTU gating the regional.
- Examples: cms 4182, 4184, 8744.
- **Recommendation:** TOPC → triage `preliminary`; NCPU/NCTU → triage `minor`, unless you know they gate the
  regional. In that case it is about 18 inserts (two series), and taiwan-ncpc-2014..2016 get parents.

**3. Thailand sub-national contests 2014–2016 (12 unaccounted CMS ids).**
These are the Northern, Southern, Central A/B and Northeastern contests under thailand-national.
- **Recommendation:** triage `minor`, as already done for the Vietnam and Chinese provincial contests. The other
  option is a layer below the national contest.

**4. The early era is mostly empty: a dedicated hunt?**
Contests per season: 1 for 1977–79, 2–4 for 1980–87, 5–8 for 1988–93, and 13 or more only from 1994. Most North
American regionals start between 1992 and 1997 (mausa, pacnw, nena, gny, ncna, mcpc). The UCF record alone shows SER
ran in 1983–87 (seusa-1983..1987 are ready as ops if you want them; `data.json` → `seusa_before_1988`).
- **Recommendation:** a separate early-era hunt (Usenet comp.org.acm, WF programmes, university team pages) rather
  than piecemeal inserts.

**5. NKP 1991–2004 (Nederlands Kampioenschap Programmeren): a new series before BAPC?**
The BAPC 2005 site says BAPC was "formerly known as NKP", and the CHipCie archive lists NKP 1991–2004 with hosts and
dates. A full proposal is in `data.json` → `new_series_proposal_nkp` (13 editions; 1999 is absent from the table).
Open question: did the NKP decide who went to the ERC/WERC/NWERC?
- **Recommendation:** add it only if yes; otherwise put it in the non-mainline registry.

**6. University selection contests that the CMS triage calls "cancelled".**
The Swiss Subregional (ETH & EPFL; CMS 3767, 4131, 4514, 4902, 5415, 7564, all with 0 teams) is triaged
`cancelled`. It ran, though: Codeforces gyms 101597 (2017), 104854, 105461 and 106170. It is EPFL's internal
selection for SWERC (polympiads.ch/ICPC). Other selection contests seen: the Swedish ICPC Qualifier 2009 and the
2015 Baltic Selection Contest (gym 100796).
- **Recommendation:** change the triage reason to `minor` (selection contest), with no catalogue editions.

**7. Other unaccounted CMS ids (for the triage owner).**
- 8864: the 2024 Dhaka onsite contest, 304 teams, a child of dhaka-2024's 8861. It probably belongs in
  dhaka-2024's `cms_ids`.
- 6457: 2022 Dhaka, 3 teams.
- 9363: "2025-2026 ICPC ARC", 6 teams, filed under SWERC 2025 but dated February 2026 → minor.
- 2990, 3114, 3326, 3663: "ACM ICPC Maraton" filed under CTU Open 2015–2018 → needs a look.
- 863 (UCV Venezuela 2011), 4194 (East Siberian subregional, 0 teams), 5573 (structural).

**8. BAPC preliminaries 2005–2008 as single contests.** They were university championships sharing a set, like 2009.
The 2008 shared set is inferred, not read. The 2005 qualifiers PDF is filed under bapc-2005 as a problem set: it
belongs to bapc-prelims-2005 (added there; removing it from bapc-2005 needs its capture pointers moved).
- **Recommendation:** accept as is. Run a capture round on the new sources.

**9. Sites to move (structure/locations).** brazil-2004's CMS record carries the 14 first-phase sites, dated
2004-10-02; brazil-2005 likewise has its first-phase sites, dated 2005-09-10.
- **Recommendation:** move them to the first-phase contests.

**10. Problem-source mappings (problems area).** These should map as follows:
- "Norwegian/Swedish Championships 2002/2003/2004" → nordic-2002/2003/2004
- "Northwestern European Regionals 1993" → werc-1993
- "Benelux Algorithm Programming Contest Qualifier 2006" → bapc-prelims-2006

Still unexplained: "Southwestern European Regional Contest 1991", "2025 ICPC North America Central Division"
(there is no Central division contest in the catalogue), "ICPC 2005", and "Southern California Regional Contest"
(no year).

**11. Gaps not resolved.** I could not find these anywhere, and none has a CMS record: algeria 2015–17 and 2019;
benin, nigeria and togo 2018; kuwait-2013; oman-2015; morocco-2024; nzpc-1999; nena-north-2010;
taiwan-ncpc-2008..2011; turkey 2024–25; malaysia-national 2015 and 2017; dhaka-2000; jakarta-2011; vietnam 2009,
2011 and 2014. The Asia host-city gaps are taken as host rotation: no unaccounted CMS id falls in them.

Also for the sources agent: Codeforces gyms 105327 (brazil-first-phase-2024) and 104022 (yinchuan-2020), and the
Gran Premio de México dates, are mirrors of contests that already exist (`data.json`, class "catalogue contest exists").

## What limited the scan

The Wayback CDX API throttled and the device shell timed out often. Because of that, I did not complete the
ETH/TU/e archive sweep for SER years or check the pre-1993 regionals further. I did not research the 2026–27 season.
