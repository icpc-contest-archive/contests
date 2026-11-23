# Data scan 2026-11-23 — agent `cms`: the catalogue against the ICPC CMS (icpc.global)

## What I checked, and how to rerun it

Scripts and scratch: `findings/cms/work/` (scripts in `work/scripts/`, live API copies in `work/live/`).

1. `scripts/fetch_live.sh` — fetched `https://icpc.global/api/contest/public/regionalresults/<year>` for 1977–2027
   (one call every ~1.5 s, 2026-11-23 05:00–05:10 UTC). 1977–1998 hold only the backfilled World Finals (plus SoCal 1989).
2. `scripts/build_universe.py` — walked every tree recursively (`subcontests`) and merged the April/August dumps
   (`regionals-2006..2026.json`, `new_regionals-1977..2008.json`): **4,867 CMS ids, 4,847 live, 20 only in old dumps**.
3. `scripts/reconcile.py` — every id against the catalogue `cms_ids`, `registry/cms-triage.yaml` and
   `registry/cms-triage-proposed.yaml`. `scripts/match.py` — unlinked ids against catalogue contests (same series
   abbreviation + season, or same CMS parent + similar name). `scripts/congruence.py` — every existing link: season,
   year in the name, date, abbreviation. `scripts/parents.py` — CMS parent (walking up past hierarchy nodes to the first
   linked contest) against the catalogue `parent`.
4. `scripts/classify.py` → `work/classified.json`; `scripts/make_ops.py` → `ops.json`; `scripts/build_data.py` → `data.json`.
5. `python3 tools/apply_scan_ops.py --check ../findings/cms/ops.json` → **66 ok, 0 failed**.

Counts: 2,280 ids linked to catalogue contests · 1,676 in cms-triage.yaml · **911 in neither** (806 of them sit only in
the never-merged cms-triage-proposed.yaml, 105 in no file at all). The 24 ids shared by two contests are all along
`subset_of` edges (NA divisions) and consistent (every subset's ids ⊂ superset's; no orphan superset id).

## Fixes in ops.json (66 ops)

**(b) cms ids added — 31 contests (62 ops: `set cms_ids` with `old` guard + a provenance line each)**

- **New CMS backfill of NEERC subregionals (30).** Since the 2026-09-02 sweep the CMS has backfilled the 1999, 2000
  and 2007 NEERC subregionals as ids 9901–9942. Each sits under its NEERC edition (supercontest 1010 = neerc-1999,
  1246 = neerc-2000, 1180 = neerc-2007), with the same series name and season as one catalogue contest that had
  `cms_ids: []`:
  - 1999: north-russia 9901, central-russia 9928, west-siberia 9929 (CMS "Siberian"; neerc-1999's own CMS site record
    puts the Siberian subregional in Novosibirsk), west-neerc 9930, urals 9931 ("Eastern"), far-east-russia 9932, south-russia 9933.
  - 2000: urals 9934, west-neerc 9935, south-russia 9936, north-russia 9937, east-siberia 9938, central-russia 9940,
    west-siberia 9941 ("Siberian", beside a separate "East Siberian"), far-east-russia 9942.
  - 2007: north-russia 9902, east-siberia 9904, azerbaijan 9905, central-russia 9906, armenia 9907, urals 9908,
    kazakhstan 9909, kyrgyzstan 9910, west-siberia 9911, west-neerc 9912, uzbekistan 9913, georgia 9914,
    far-east-russia 9915, moscow 9916, south-russia 9917.
  - The 1999 and 2000 rows carry team counts (24–48); the 2000 Northern/East-Siberian/Central/Siberian rows and all
    2007 rows are still 0-team shells (the backfill looks unfinished — 1998, 2001–2006 are not there yet).
- **naq-2023 + 8666** "The 2023 ICPC North America Qualifier – Encore Edition" (414 teams), same as naq-2024 already
  holds 8932 (its Encore). 8666 was in the proposed file as `structural`.

**(a) one missing edition — `insert_contest` vietnam-national-2016 + `next` of vietnam-national-2015 (2 ops).**
CMS 3049 "Asia Nha Trang National Programming Contest", child of 3048 = vietnam-2016, 198 teams, ranked CMS standings
(1 BK.Juniors, HUST, 8 solved). The series is mainline (Q4) and jumped from 2015 to 2017. Entered with name, season,
cms id, parent, next, the CMS standings page as a `standings` source, provenance; **no date** (the CMS site dates say
2016-10-30 — one source only, noted in `notes`).

**yinchuan-2020: `cms_ids: []` (2 ops).** The field was absent; no Yinchuan entry exists in any 2005–2027 hierarchy
(only 4211/4212 for 2019).

Not done although tempting: `cms_ids` of brazil-first-phase-2005..2007 (absent) — the CMS has no separate first-phase
record before 2008, but brazil-2005..2007's records (975/1124/1257, 184/217/339 teams) look like they include the
first-phase field, so neither "[]" nor an id is certain. hefei/jinan/kunming-2026 (absent, upcoming) — left to the
current-season agent (see (f)).

## (a) The 911 CMS ids that are in neither place

Full list with a recommendation per id: `data.json → uncovered`; the rows ready for `cms-triage.yaml` (registry format,
with `reason_note` and whether the reason differs from the proposed file): `data.json → proposed_triage_rows` (877).

| recommendation | ids |
| --- | --: |
| catalogue cms id (ops above) | 31 |
| new catalogue contest (op above) | 1 |
| registry `minor` | 454 |
| registry `preliminary` | 306 |
| registry `structural` | 92 |
| registry `non-mainline` / `special` / `cancelled` / `camp` / `challenge` / `junk` | 7 / 7 / 4 / 3 / 3 / 1 |
| discuss | 2 |

The 105 ids in no file are: the NEERC backfill (30, now linked), Taiwan rounds (30), Thailand group rounds (17),
CTU Open "Maraton" (4), NAIPC 2016–2019 (4), Vietnam National 2016 (1), and singles (Tokyo Foreign Teams 1519, UCV
863, Northern Eurasia hierarchy nodes 9873/5573, the 0-team ESSC shell 4194 that was on uzbekistan-2019 until the
September audit, Dhaka duplicates 6457/8864, China provincials 3058/4375/8680/8696, ARC 9363, AlgoQueen 9857,
Europe Women's 9861/9862, Huawei Online Challenge 9870, `icpc-api demo contest` 9900, Vietnam National High School
division 9925, Transcaucasian 2000 9939). The 806 proposed rows were re-checked: none looks mainline; 315 get a
different reason from the one proposed (see discussion item 1).

## (c) cms ids on the wrong contest

No link fails season or name-year (the only name-year flag, nadc-2021 "2020-21", is fine); abbreviation and name
similarity outliers all read correctly. The one real misattribution is a whole family — **taiwan-ncpc 2014–2016**
(discussion item 2). Already-known CMS-side errors (dhaka-2001 family +1 year, sas-2021, scusa-2021, awc-2022,
kanpur-2022) still stand in the CMS and are marked in `data.json → date_differences`.

## (d) Dates and names

- 358 links differ by more than a day (`data.json → date_differences`). 254 are −2/−3 days: the CMS `contestDate`
  is the first day of a multi-day event (ACPC, NWERC, CERC, SWERC, Jakarta… consistently), not a disagreement.
  **53 differ by more than a week**; 9 are the known +1-year CMS slips; the rest are listed for the dates agents
  (e.g. nanchang-2019 −120 d, yinchuan-2019 −87 d, peradeniya-2025 −78 d, ukraine-2023 −70 d, turkey-2026 −15 d with a 0-team CMS row).
- 24 catalogue contests have no date while their CMS record has one (`catalogue_date_empty_cms_has_date`), not set
  (no second source checked). Two traps marked there: taiwan-ncpc-2013's CMS date is the NCPU contest's;
  neerc-2001's 2002-11-25 is a +1-year slip. Lead for the dates agents: neerc-1999's `sites` (from the CMS) already
  carry the 1999 subregional dates (Central 10-06, Siberian 10-24, Western 10-21, Far Eastern 10-30, Northern 11-01, Southern 09-30).
- Names: no material differences beyond the above.

## (e) CMS parent ≠ catalogue parent — 142 links (`data.json → parent_differences`, with a `category`)

- 87: catalogue parent absent, CMS gives one — alberta-2011..2023 and lethbridge-2013..2023 → rmc; caribbean-national-2013..2019
  → caribbean; naq-2012/2013 (per-site rows → each regional), naq-2014..2026 → wf / nac; Asia national contests
  (malaysia, mongolia, philippines, taiwan-ncpc, vietnam-national-2014, myanmar) → wf via Asia hierarchy nodes.
  These overlap the structure agent's "97 parent unknown"; the CMS answer is in the data.
- 22: Chinese regionals 2024–2026 sit under the Asia East Continent Final (aec-YYYY) in the CMS; catalogue says wf.
- 11: the 2020 NA regionals sit under NADC 2020-21 (nadc-2021) in the CMS; catalogue says nac-2021, though nadc-2021 → nac-2021 exists.
- 11: south-africa-2008..2018 are siblings of ACPC under the CMS's "Africa and the Middle East Regional" node (direct to WF); catalogue says acpc-YYYY.
- 10 other: nordic-2006/2007 and bapc-2007 directly under WF in the CMS (catalogue nwerc — catalogue right);
  caribbean-2010 under central-america-2010 in the CMS (catalogue wf-2011); nzpc-2012/2013 and australia-2013 under the
  CMS's South Pacific hierarchy node (catalogue south-pacific — fine); azerbaijan/georgia-2021 under the "South
  Caucasus Championship" 5828 (item 3); south-pacific-2024 → wf via "Asia Pacific Contests" (catalogue apc-2025).

## (f) Live 2026 and 2027 hierarchies (`data.json → new_in_cms`)

306 live ids of icpcYear 2026/2027 are not catalogue ids: 112 already in cms-triage, 184 only in the proposed file,
**10 in no file**: 9363 ARC, 9396/9397/9398 Taiwan PUPC/TUPC/Online 2025, 9857 AlgoQueen 2026, 9861/9862 Europe
Women's 2026 (+ qualifier), 9870 Huawei Online Challenge, 9900 `icpc-api demo contest`, 9925 Vietnam National 2026
High School division — none mainline; rows proposed. Catalogue side: **hefei-2026, jinan-2026, kunming-2026**
(upcoming "shells from the misclassification audit", no `cms_ids` field) have **no entry in the live 2027 hierarchy**
— and Hefei/Jinan/Kunming 2025 (9230/9219/9225) are 0-team triage rows; alberta/lethbridge/croatia/hungary-2025 have
no CMS entry either. All catalogue 2026/2027 cms ids are live.

Registry housekeeping: cms-triage-proposed.yaml still lists 24 ids that are now catalogue ids and 20 ids that left the
CMS; 22 triage ids are gone from the live CMS (e.g. 9013 hefei-2024) — harmless, listed in `data.json`.

## Items for discussion with Fredrik

**1. Merge the proposed triage rows — with online qualifiers as `preliminary`?**
The 806 rows of `cms-triage-proposed.yaml` (2026-09-02, by name pattern) plus 73 new ones have never been merged, so
911 CMS ids are "considered" nowhere. The proposed file calls online first rounds, preliminaries and NERC
qualifications `structural` (a hierarchy node), but your Q5 ruling made such part-of-parent rounds `preliminary`, and
the registry already does so (japan-first-round, tehran-online). *Merge as proposed:* one step, nothing lost. *Merge
with the remap:* `structural` keeps meaning "node, not a contest"; 271 online rounds/qualifiers → `preliminary`, 15 Korea
first rounds → `preliminary` (new family korea-first-round), Japan first rounds 2012–2015 → `preliminary`
(japan-first-round), 16 university qualifiers → `minor`, 2 Saudi individual qualifiers → `special` (kickoff-individual),
CFQ 2022+ → `non-mainline` (Q6), 2 NERC nodes `cancelled` → `structural`. Examples: 4155 (Korea first round 2019,
753 teams), 9171 (Moscow Qualification 2025, 670 teams), 3092 (Dhaka online preliminary 2016, 1,753 teams).
**Recommendation:** merge `data.json → proposed_triage_rows` as is (reasons already remapped, `changed_from_proposed`
marks the 315), then delete the proposed file.

**2. Taiwan: what are taiwan-ncpc-2014..2016, and where do TUPC/PUPC/TOPC go?**
The series is the MOE NCPC (October, ncpc.ntnu.edu.tw), but taiwan-ncpc-2014 = 2553 "Taiwan **NCPU** National" (June),
-2015 = 2969 (NCPU, July), -2016 = 3075/3076 (**NCTU** + NCPU, July), and -2013 merges 1908 (NCPC) with 1909 (NCPU). The
same contests continue as 2017–2025 NCTU/NCPU → TUPC/PUPC (19 ids, in no file), and the Taiwan Online Programming
Contest (11 ids). The 2026-09-04 dossier said "NCPC mainline / TOPC part-of-parent / TUPC-PUPC registry". *If
TUPC/PUPC are registry:* move 1909/2553/2969/3075/3076 to the registry and either find the real MOE NCPC 2014–2016 or
drop those stubs. *If they are mainline:* a new series (or two) for 2013–2026 and taiwan-ncpc keeps only 2007/2012/2013.
Examples: https://icpc.global/regionals/finder/Taiwan-NCPU-2015, https://icpc.global/regionals/finder/AsiaTaiwanPUPC-2026.
**Recommendation:** registry for TUPC/PUPC (as the dossier), TOPC `preliminary`; repair taiwan-ncpc-2014..2016 (I have
prepared the 30 registry rows on that basis but no catalogue op).

**3. Ranked contests that sit in the registry.**
Six CMS rows with their own ranked results are registry entries that look mainline by the existing rulings:
1283/1291 Colombia XX/XXI Maratón 2006/2007 (88/86 teams; colombia-maraton starts 2008 and is mainline) — `minor`;
891/1434 Caribbean National Contests 2011/2012 (149/98 teams; caribbean-national starts 2013, and Q6 said the
2010–2019 nationals are mainline) — `non-mainline`; 4586 "2020-2021 Northern Eurasia Finals Offline" (50 teams, 48
results; nerc-2020 holds only the online final 4551) — `structural`; 5828 "2022 NEF South Caucasus Championship"
(21 teams, 21 results; the CMS parent of azerbaijan-2021 and georgia-2021) — `structural`. *For moving them:* each has
its own standings and follows a ruling already made. *Against:* catalogue contests need evidence beyond the CMS
(registration indicates, never proves). Links: https://icpc.global/regionals/finder/Colombia-2007,
https://icpc.global/regionals/finder/Caribbean-National-2012, https://icpc.global/regionals/finder/NERC-SC-2022.
**Recommendation:** Colombia 2006/2007 and Caribbean 2011/2012 → catalogue editions; 4586 → a second id of nerc-2020;
5828 → research first (a separate South Caucasus final for the 2021-22 season would change two parents).

**4. Parents where the CMS disagrees.**
(a) south-africa-2008..2018: the CMS makes the South Africa regional a sibling of ACPC under "Africa and the Middle
East", i.e. direct to the WF; the catalogue says acpc-YYYY (and the series is tier `subregional`). (b) the 2020 NA
regionals: CMS → nadc-2021, catalogue → nac-2021 although nadc-2021 → nac-2021 is in the catalogue. (c) Chinese
regionals 2024–2026: CMS → aec-YYYY, catalogue → wf. Examples: https://icpc.global/regionals/finder/South-Africa-2013,
https://icpc.global/regionals/finder/East-Central-NA-2021, https://icpc.global/regionals/finder/Chengdu-2025.
*Follow the CMS:* it records who advanced where. *Keep:* the CMS also misfiles (it puts NCPC 2006/2007 straight under
the WF). **Recommendation:** (a) and (b) follow the CMS (structure agent to apply); (c) needs your call on whether the
EC Final is a step between the Chinese regionals and the WF since 2024 (parent list `[aec, wf]` is possible).

**5. Two possible new contests from the CMS.**
9939 "The 2000 ACM Transcaucasian Subregional Contest" (backfill, 0 teams; NEERC 2000/2001's CMS sites list a
"Transcaucasian group") — new `transcaucasus-2000`, or registry `cancelled`? 933 "The 2011 Argentina Preliminary
Contest" (31 teams, 28 results) under south-america-south-2011, the sibling of 837 "Bolivia Preliminary" which is
bolivia-national-2011 in the catalogue; tap starts 2012 — is this tap-2011?
**Recommendation:** 933 → tap-2011 if the Torneo Argentino's own history counts 2011 (one search); 9939 → registry
`cancelled` until the backfill fills it.

**6. hefei/jinan/kunming-2026.**
Upcoming shells created from the September audit; the live 2027 hierarchy has no Hefei, Jinan or Kunming regional,
and the 2025 rows were 0-team ghosts (triaged cancelled). **Recommendation:** leave them to the current-season agent for
now; if no CMS entry or other sign appears by the end of the season, drop them (an upcoming shell with no evidence is
not a contest that ran).

## Memory / context used
Background on the 2026-09-02 misclassification audit (uzbekistan-2019 4194 slip, the +1-year CMS-bug list) and the
Q1–Q12 rulings came from the project memory and `reports/misclassification-audit-2026-09-02.md`,
`reports/decisions-2026-09-07.md`, `reports/triage-review-2026-09-04.md`, `reports/family-dossier-2026-09-04.md`.

## Nothing blocked me
The public API answered every call; nothing was written outside `findings/cms/`.
