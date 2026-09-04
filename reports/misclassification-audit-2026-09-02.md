# Misclassification audit — 2026-09-02

Method: joined every catalogue `cms_ids` link (2,107 ids across 2,405 contests) against the
CMS (`api_contest` 4,635 rows + relax `contest` table + backfill sweep), checked year/region/
date congruence, ran structural checks (parent-season, next-chains, duplicate ids), reverse-
scanned all unlinked CMS rows for mainline-looking contests, and web-verified the disputed
cases against organizer sources. Headline: the catalogue is in very good shape — 3 hard year
mismatches and 1 wrong link in 2,107 — but the reverse scan found four **missing real
regionals** (one with 446 teams).

## A. Wrong in the catalogue — ready to fix on your go

Machine-readable version: `data/misclass-fix-candidates.json`.

| # | contest | problem | fix |
|---|---|---|---|
| 1 | **uzbekistan-2019** | cms_ids `[4194]` = "East Siberian Subregional Contest", an empty 0-team shell — an adjacent-row slip (4192–4194 are East Siberian rows) | → `[4191]` "The 2019 Uzbekistan Regional Contest" (date 2019-11-10 matches ours exactly, 74 teams / 148 results; finder `Uzbekistan-Regional-2020`) |
| 2 | **kuwait-2010/2011/2012** | seasons shifted +1: catalogue says 2012/2013/2014, CMS icpc_year says 2011/2012/2013, dates are Oct of the name year, and kuwait-2014+ all follow name+1. Kuwait simply skipped 2013 (CMS id space jumps 1350→2721); the catalogue stretched 3 editions across the gap. Internal parent/season congruence hid it — entries were shifted *consistently* | seasons → 2011/2012/2013; parents acpc-2011/2012/2013 → **acpc-2010/2011/2012** (acpc-2010 = 2010-11-27, right after Kuwait's 2010-10-16 ✓); next-chain unchanged (2012→2014 gap is real) |
| 3 | **kanpur-2022** | date 2023-10-04 fits nothing (its cohort ran spring 2023; awc-2022 was May 2023) | → **2023-04-09** — organizer archive kanpurarchive2022.indiaicpc.in: "regional round will be held on 08 April – 09 April, 2023" (gla.ac.in/icpc/Dates.html agrees; main round on the 9th). NB: CMS's own 2023-03-03 is *also* wrong |
| 4 | **south-america-south-2021** | date 2023-03-17 is sas-**2022**'s date — CMS row 4711 wrongly carries 5523's date and our yaml inherited it | → ~**2022-04-02** (siblings: SA-North-2021 = 2022-04-02, Brazil-2021 finals = 2022-04-01; LatAm finals share the weekend). Confirm exact day via icpclatam/scorelatam before applying |
| 5 | **kuala-lumpur-2014** | linked 2607 is the 0-team canonical shell; the actual data lives in CMS dupe **2710** "Asia Kuala Lumpur Onsite Regional Contest" (54 teams / 53 results, same date) — the only unlinked pre-2020 "Regional" row with data in the entire CMS | cms_ids `[2607]` → `[2607, 2710]` |
| 6 | **nena-2026** | missing `status: upcoming` (gny/ecna/mausa/scusa/seusa-2026 all have it) | add it |

## B. Missing real contests (adds to ratify — all verified in CMS with posted results)

* **wuhan-2025** — CMS 9483, **446 teams / 446 results**, 2025-11-01. Wuhan returned as an
  Asia East regional last season; our wuhan series ends at **2009**. Finder live:
  `ICPC-Asia-Wuhan-2026` (+standings); XCPCIO archived board at
  `board.xcpcio.com/icpc/50th/wuhan` (「华为杯」第 50 届…武汉站). Parent per convention:
  wf-2026. Distinct from the "China Hubei(Wuhan) National Invitational" spring series
  (8669/9065/9191/9625 — feeder layer).
* **peradeniya-2025** — CMS 9238, 23 teams / 23 results. New Sri Lanka Asia West site
  (2024 edition 9091 was cancelled — its absence is correct). The onsite ran **Sun 25 Jan 2026**
  per the University of Peradeniya's own post-event blog (eng.pdn.ac.lk); CMS's 2025-11-08 on
  9238 duplicates the *preliminary's* date (9831, 81 teams — the feeder) — one more CMS date
  bug. Web candidates: icpc.ieee.lk, the eng.pdn.ac.lk write-up. Parent awc-2025; finder
  `Asia-Peradeniya-2026`. New series file.
* **tajikistan-2023/2024/2025** — CMS 8567 (8/7 teams, 2023-11-19), 8896 (20/16, 2024-11-24),
  9169 (14/10, 2025-11-15). Tajikistan split out of the "Uzbekistan and Tajikistan
  Qualification" into its own NERC-country regional — exactly parallel to the uzbekistan /
  kazakhstan / kyrgyzstan series we already carry. Parent nerc-{y}; finder `TjRC-{y+1}`.
* **turkmenistan-2025** — CMS 9485, 39 teams / 34 results, 2025-11-15. New NERC-country
  regional. Parent nerc-2025; finder `Turkmenistan-2026`; clist.by has an aggregator copy of
  the standings (eyeball before adopting).
* Upcoming (2026-27) shells to add with the next season sync: wuhan-2026 (9648),
  nanchang-2026 (9851), hefei-2026 (9606), jinan-2026 (9607), kunming-2026 (9612),
  peradeniya-2026 (9662), tajikistan-2026 (9796), turkmenistan-2026 (9787). (hefei/jinan were
  cancelled in 2025 but are announced for 2026.)

Proposed stubs (season/parent/next per existing conventions; results URLs to hunt separately):

```yaml
# wuhan.yaml — append; also set wuhan-2009 next: wuhan-2025
- id: wuhan-2025
  season: 2026
  name: The 2025 ICPC Asia Wuhan Regional Contest
  date: 2025-11-01
  parent: wf-2026
  next: wuhan-2026
  icpc_standings: https://icpc.global/regionals/finder/ICPC-Asia-Wuhan-2026/standings
  cms_ids: [9483]

# peradeniya.yaml (new)
- id: peradeniya-2025
  season: 2026
  name: The 2025 ICPC Asia Peradeniya Regional Contest
  date: 2025-11-08
  parent: awc-2025
  next: peradeniya-2026
  icpc_standings: https://icpc.global/regionals/finder/Asia-Peradeniya-2026/standings
  cms_ids: [9238]

# tajikistan.yaml (new) — 2023 (8567), 2024 (8896), 2025 (9169), dates above,
#   parent nerc-{start year}, finder TjRC-{season}
# turkmenistan.yaml (new) — 2025 (9485), parent nerc-2025, finder Turkmenistan-2026
```

## C. CMS data bugs (catalogue is right; worth reporting upstream)

* **Name/date year contradictions** — contest date exactly ~+1 year vs the contest's own name:
  1238 (Dhaka 2001 → dated 2002-11-27, previously known), 1001 (SCUSA 2002 → 2003-11-07),
  1229 (Manila 2003 → 2004-11-06), 1059 (ECNA 2001 → 2002-11-08), 644 (ECNA 2010 →
  2011-10-21), 1118 (SEERC 1998 → 1999-10-22), 1208 (SEERC 1999 → 2000-10-19),
  1236 (South Pacific 2001 → 2002-09-13).
* **5637 (awc-2022)** dated 2023-01-14; the organizer's own schedule page
  (icpc.green.edu.bd/asia-west-continent-schedule) says the main contest was **May 20, 2023**
  — our date is correct.
* **4685 (scusa-2021)** dated 2022-10-22; the delayed contest actually ran 2022-03-05 (ours).
* **4711 (sas-2021)** carries sas-2022's 2023-03-17 (the bug we inherited, item A4).
* **5647 (kanpur-2022)** dated 2023-03-03; organizer says Apr 8–9, 2023 (item A3).
* **8916 vs 9324** are both named "The 2025 ICPC North America Division Championships"
  (icpc_year 2025 and 2026) — 8916 should read 2024.
* Placeholder dates (Aug 1 / Aug 15 / Sep 15) on 4231 (Nanchang 2019), 4211 (Yinchuan 2019),
  1010 (NEERC 1999); real dates are the November ones we already carry.
* Sub-40-day diffs (start-of-event-week vs contest day, e.g. wf-2013 6-30 vs 7-04;
  tehran-2022 5-18 vs our 4-28) — 84 rows, list reproducible from the join; not season-relevant.

## D. Verified anomalies — look wrong, are right (no action)

* **tehran-2023 ran AFTER its championship** (2024-05-31 vs awc-2023 2024-03-30) — CMS
  agrees on both dates (7489 = 2024-05-30). Iran's regional simply ran late again.
* **The delayed Asia West cascade** is internally consistent and CMS-confirmed:
  the "2021" cohort ran Oct–Dec 2022 (amritapuri/gwalior-pune/dhaka-2021, awc-2021
  2022-12-24), the "2022" cohort spring 2023, converging back to normal by kanpur-2023
  (2023-12-23). Only kanpur-2022's yaml date broke the pattern (item A3).
* **kanpur-2021 = 4829 "Asia Kanpur Contest"** (1599 teams, 2022-08-22) — the online round
  effectively *was* the regional that cycle; the onsite row 4828 is an empty cancelled shell
  (correctly excluded). Same pattern as kanpur-2020 = 4503 (Kanpur-Mathura Online). Perhaps
  worth a provenance note on the entry, nothing more.
* **east-na / south-na division entries** share their member regionals' cms_ids by design
  (all 24 "duplicate id" hits are these). Composition: south-na = SEUSA+SCUSA+MAUSA
  throughout; east-na = NENA+ECNA in 2023–2025 but **NENA+ECNA+GNY in 2026** (9768 also on
  gny-2026). If NADC regrouped divisions for 2026-27 that's correct — worth one glance at
  na.icpc.global before trusting.
* **tehran-2020 = 4498/4499 era**: catalogue correctly has tehran-2020 (online regional) and
  correctly *lacks* tehran-2021 (CMS 4841 = 0-team cancelled shell). Season-2022 Iran gap is real.
* **south-africa** correctly ends at 2019 — CMS 2020–2023 editions are cancelled shells
  (4406 has 1 team, rest 0); no 2024+ rows exist. Matches the audit's lethbridge-style check.
* **hungary-2012** is real per CMS (1318: 28 teams registered). **hungary-2013's CMS row
  (id 2012) is a 0-team shell** — which *weakens* the case that the 2013 edition ran;
  the uhunt vcontest board is currently the only results evidence. Strengthens the case for
  asking an ELTE contact before trusting either uhunt board.
* wf-2020/2021/2022/2023 "odd" dates are the covid/joint-Luxor reality; wf-2024 (Sep,
  Astana), wf-2025 (Sep, Baku), wf-2026 (Nov, planned) are fine.
* Dhaka's recent CMS dupes ("Regional" vs "Regional Onsite", e.g. 8861/8864 both 304 teams):
  catalogue links the rows that carry results (8861, 9239) — correct as is.

## E. Registry & triage state

* **proposed (850)**: name-scan found **zero** mainline-looking rows — safe to merge on that axis.
* **excluded (1,100)**: sound. "Structural" = continental groupings ✓; cancelled shells
  (tehran/kanpur/mathura-2021, hangzhou/xian CMS dupes, south-africa 2020–23, hefei/jinan-2025,
  peradeniya-2024, Ukraine "NoRegion" rows) all correctly out. One imprecision: the Asia West
  2020/2021 shells are tagged `structural` where `cancelled` fits better — cosmetic.
* **4 CMS rows are in no bucket** (created after the last sync): 9850 "2026 ASU Collegiate
  Programming Contest" (67 teams — Ain Shams / ACPC feeder → minor), 9851 nanchang-2026 (→ B),
  9852/9854 "Asia Regionals Online Contest I/II" 2026 (→ first-round).
* **Layer precedent worth noting for the open policy question**: the catalogue already carries
  the NEERC national first-round layer as first-class series (armenia, azerbaijan, georgia,
  kazakhstan, kyrgyzstan, uzbekistan — CMS names them "Subregional"), alongside nena-east/west
  and bapc-prelims. The excluded-but-identical layers elsewhere (Ukraine oblasts 2010–2026 —
  6 contests/yr with 40–240 teams each, Brazil First Phase, Taiwan/Thailand/Vietnam/Indonesia/
  Japan nationals, Tehran Internet rounds at 400–900 teams, Kazakhstan Octafinal) remain the
  audit §3 decision. The precedent cuts toward inclusion.
* `no_season` metadata inconsistency: all 70 are alberta/lethbridge/naq/nzpc/caribbean-2009
  entries (e.g. nzpc-2002 has no season but other nzpc do) — tidy-up, not misclassification.

## F. Sources

* icpc.green.edu.bd/asia-west-continent-schedule (AWC-2022 = May 19–20, 2023)
* kanpurarchive2022.indiaicpc.in + gla.ac.in/icpc/Dates.html (Kanpur-Mathura 2022 = Apr 8–9, 2023)
* icpc.global/regionals/finder/ICPC-Asia-Wuhan-2026 (wuhan-2025 live standings)
* CMS `api_contest` snapshot (icpc-nopii.db) + relax `contest` table + backfill sweep
* Join artifacts: `misclass-extract.json` (repo root, regenerable scratch — deletable),
  flags in this session's workspace
