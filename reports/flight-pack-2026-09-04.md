# Flight pack — decisions to work through offline

*2026-09-04. Everything you need is in this file plus three reference reports that are
already on your disk in `contests/reports/`: `layer-policy-brief-2026-09-04.md` (the
options in depth), `triage-review-2026-09-04.md` (all 775 rows, grouped), and
`misclassification-audit-2026-09-02.md` (full evidence per fix). This file is
self-contained for every decision; open the references only when you want the raw rows.*

**How to answer:** edit this file in place — every question ends in an `ANSWER:` line.
Shorthand is fine ("O2+UA", "all", "all except X"). When you're back online, just tell
Claude "flight pack answered" — I'll read this file from the repo and apply everything
mechanically (edits and stub generation are scripted; nothing is applied until you rule).

---

## D1. Layer policy — where is the mainline line? (the big one)

The catalogue includes all finals/championships/regionals, plus an ad-hoc subset of the
lower tiers (nena divisions, NEERC country contests, bapc-prelims, SP divisions), while
excluding the same layers elsewhere (Ukraine oblasts, Brazil First Phase, LatAm/Asia
nationals). Your own icpc-history inventory frames five tiers:
finals / championship / regional / sub-regional / preliminary.

| option | rule | effect |
|---|---|---|
| O1 | line at sub-regional, no exceptions | adds ~100 series (~600 eds); **ejects** bapc-prelims + SP divisions |
| O2 | O1 + grandfather list (status quo formalized) | same adds; keeps the two historical exceptions; Ukraine oblasts stay out |
| **O2+UA** | O2 + adopt Ukraine oblasts as a third documented exception | + 80 real editions, med. 123 teams, the war-years record — **recommended** |
| O3 | "own-competition" rule (top round of its own named competition) | adds nationals (~350 eds); keeps out all prelims/first phases; would also eject bapc-prelims unless grandfathered |
| O4 | results-bearing rule (ranked public standings ⇒ in) | everything incl. Dhaka's 1,757-team prelims (~800+ eds); "mainline" blurs |

Implementation on ruling: `tier:` field in series metadata (machine-checkable), a written
exception list, mechanical stub generation from the CMS DB (naming per your hierarchy
slugs: ukraine-east-YYYY, brazil-first-phase-YYYY, miup-YYYY, …).

**ANSWER D1 (O1 / O2 / O2+UA / O3 / O4, plus any modification):**

---

## D2. Family verdicts — 775 unresolved CMS rows in 33 families

One verdict per family. Vocabulary: **mainline** (becomes catalogue series/editions),
**grandfather** (kept by documented exception), **registry** (tracked, excluded),
**merge** (CMS id of an existing edition), **hold** (future shells). The *suggested*
column assumes O2+UA; the O-columns show each family's fate under the other rules.
Full row lists per family: `triage-review-2026-09-04.md`.

| family | tier | rows | span | med/max teams | O1 | O2 | O2+UA | O3 | O4 | suggested |
|---|---|--:|---|---|---|---|---|---|---|---|
| ukraine-oblasts | preliminary | 81 | 2009-2024 | 124/241 | out | out | in | out | in | mainline (the third exception) |
| taiwan-rounds | sub-regional | 39 | 2007-2025 | 57/294 | in | in | in | out | in | mainline (grouped, see D3e) |
| asia-nationals-misc | sub-regional | 27 | 2013-2020 | 31/149 | in | in | in | in | in | mainline (one series per country) |
| caribbean | sub-regional | 24 | 2011-2021 | 144/260 | in | in | in | in | in | mainline national; registry locals (D3c) |
| tehran-online | sub-regional | 24 | 2013-2025 | 203/889 | in | in | in | out | in | mainline; per-site Iran rows merge |
| colombia-maraton | sub-regional | 23 | 2008-2025 | 102/123 | in | in | in | in | in | mainline |
| thailand-rounds | sub-regional | 23 | 2012-2025 | 60/116 | in | in | in | out | in | mainline national; registry group rounds (D3d) |
| brazil-first-phase | sub-regional | 18 | 2008-2025 | 641/1025 | in | in | in | out | in | mainline |
| torneo-argentino | sub-regional | 14 | 2012-2025 | 83/168 | in | in | in | in | in | mainline |
| jakarta-indonesia-national | sub-regional | 14 | 2012-2025 | 600/820 | in | in | in | in | in | mainline |
| vietnam-national | sub-regional | 12 | 2014-2025 | 262/490 | in | in | in | in | in | mainline |
| gran-premio-mexico | sub-regional | 10 | 2015-2024 | 834/1281 | in | in | in | in | in | mainline |
| japan-first-round | sub-regional | 10 | 2016-2025 | 359/495 | in | in | in | out | in | mainline |
| gran-premio-centroamerica | sub-regional | 9 | 2018-2026 | 57/126 | in | in | in | in | in | mainline |
| oman-subregions | preliminary | 9 | 2025-2026 | 20/80 | out | out | out | out | in | registry (unless UA-style, D3a) |
| venezuela-finals | sub-regional | 8 | 2014-2025 | 42/64 | in | in | in | in | in | mainline |
| china-provincial | sub-regional | 7 | 2013-2026 | 224/255 | in | in | in | out | in | mainline (thin CMS presence) |
| south-pacific-legacy | varies | 6 | 2008-2021 | 75/92 | gf | gf | gf | gf | in | grandfather (existing exception) |
| torneo-chileno | sub-regional | 6 | 2017-2025 | 40/60 | in | in | in | in | in | mainline |
| moscow-open | sub-regional | 4 | 2017-2019 | 354/423 | in | in | in | in | in | mainline |
| slovenia-rounds | preliminary | 3 | 2011-2012 | 0/0 | out | out | out | out | in | registry (year-level UPM already mainline) |
| bolivia | sub-regional | 2 | 2024-2025 | 293/293 | in | in | in | in | in | mainline |
| india-area-rounds | sub-regional | 1 | 2012 | 467/467 | in | in | in | out | in | mainline |
| kazakhstan-octafinal | sub-regional | 1 | 2024 | 185/185 | in | in | in | out | in | mainline if it recurs |
| seniors-masters | special | 13 | 2019-2024 | 16/43 | out | out | out | out | out | registry |
| girls-special | special | 11 | 2017-2025 | 305/792 | out | out | out | out | in | registry now; revisit (D3b) |
| kickoff-individual | special | 8 | 2020-2025 | 2573/6036 | out | out | out | out | out | registry (individual format) |
| handled-elsewhere | - | 10 | 2014-2025 | 31/446 | - | - | - | - | - | misclass runner / cms_ids merge |
| arab-uni-locals | minor | 246 | 2012-2025 | 26/142 | out | out | out | out | out | registry (minor) |
| mexico-locals | minor | 52 | 2009-2016 | 50/473 | out | out | out | out | out | registry (minor) |
| angola-local | minor | 3 | 2017-2019 | 29/29 | out | out | out | out | out | registry (minor) |
| future-shells | - | 40 | - | - | - | - | - | - | - | hold until run |
| unmatched | ? | 2 | 2022-2026 | 15/71 | ? | ? | ? | ? | ? | manual: "2022 Northern Eurasia Contests" umbrella row + "2025-26 ICPC ARC" |

**ANSWER D2 ("all suggested", or exceptions as `family: verdict`, one per line):**

---

## D3. Families worth an individual thought

**D3a. oman-subregions** (9 rows, 2025-2026): Oman quietly grew a per-sub-region
structure (Capital/Coastline/Midland/Southern/Oriental + a seniors row) — the same shape
as Ukraine's oblasts but only 2 seasons old and ~20-80 teams. Registry for now, or the
UA-style exception from day one?
**ANSWER D3a (registry / mainline-like-UA):**

**D3b. girls-special** (11 rows: Africa&Arab Girls ×6, Girls-only ×3, AlgoQueen ×2;
median 305 teams, max 792): real ranked collegiate events. Registry for now — or their
own series group in mainline (they are official ICPC-adjacent events with real fields)?
**ANSWER D3b (registry / own series group):**

**D3c. caribbean**: "National Contests" rows read as the country layer (peer of other
LatAm nationals → mainline); "Local Contests"/"Competición Local" rows are per-campus.
Suggested: nationals mainline, locals registry.
**ANSWER D3c (as suggested / other):**

**D3d. thailand-rounds**: National On-site = the top national round (mainline);
Southern/Northeastern/Northern group rounds = its feeders (registry under O2).
**ANSWER D3d (as suggested / all mainline / other):**

**D3e. taiwan-rounds** (39 rows): several parallel per-year rounds — Online, National,
Technology-University, Private-University, plus Kaohsiung Group-A/B/C one-offs. If
mainline, they need series grouping. Proposal: three series (taiwan-online,
taiwan-tech-univ, taiwan-private-univ) + fold the National/Kaohsiung variants into
taiwan-online's lineage with notes.
**ANSWER D3e (proposal ok / different grouping):**

---

## D4. Misclassification audit — ratify the fixes

Machine file is ready; each item applies only if you ratify it, and each edit is guarded
(refuses if the catalogue value moved since the audit). Full evidence:
`misclassification-audit-2026-09-02.md`.

Edits (all currently pass their guards):

| # | id | change | evidence (short) |
|---|---|---|---|
| 1 | uzbekistan-2019 | cms 4194 → 4191 | 4194 = empty East-Siberian shell (adjacent-row slip); 4191 = real 74-team row |
| 2 | kuwait-2010 | season 2012→2011, parent →acpc-2010 | CMS icpc_year 2011; contest Oct 2010 |
| 3 | kuwait-2011 | season 2013→2012, parent →acpc-2011 | CMS icpc_year 2012 |
| 4 | kuwait-2012 | season 2014→2013, parent →acpc-2012 | CMS icpc_year 2013 (Kuwait skipped 2013) |
| 5 | kanpur-2022 | date 2023-10-04 → 2023-04-09 | organizer archive (gla.ac.in Dates.html); CMS date also wrong |
| 6 | south-america-south-2021 | date 2023-03-17 → 2022-04-02 | CMS 4711 carries sas-2022's date; siblings ran 2022-04-01/02 |
| 7 | kuala-lumpur-2014 | cms += 2710 | 2710 holds the 54-team data; 2607 is the 0-team canonical shell |
| 8 | nena-2026 | status → upcoming | all division siblings have it |

Adds (new editions, stubs with CMS ids + finder standings links):
wuhan-2025 (446 teams, parent wf-2026), peradeniya-2025 (23 teams — onsite ran
2026-01-25 per the university's own blog; CMS date is another bug),
tajikistan-2023/2024/2025 (new NERC country series), turkmenistan-2025 (39 teams).

Shells (upcoming, status: upcoming): wuhan/nanchang/hefei/jinan/kunming/peradeniya/
tajikistan/turkmenistan-2026.

**ANSWER D4-edits ("all" or numbers to skip):**
**ANSWER D4-adds ("all" or ids to skip):**
**ANSWER D4-shells ("all" / "none" / ids):**

---

## D5. Wave-7 eyeball items

**D5a. Hungary via SZTE — RESOLVED while assembling this pack, veto if you disagree.**
I fetched inf.szte.hu/acm/korabbi-versenyek: the page says explicitly these are Szeged's
*local rounds* — "helyi fordulójának célja … kiválasszuk, kik képviselik a Szegedi
Tudományegyetemet" (purpose of the local round: select who represents the University of
Szeged at the Central European regional). So the six hungary-2014..2021 candidates are
SZTE site rounds, **not** national Hungarian results — I'm marking them rejected for the
national series (they'd belong to the locals/registry layer at most). The national
Hungarian results remain dark for those years.
**ANSWER D5a (agree / veto with reason):**

**D5b. syria-2017 vs syria-2018 — which edition is CF gym 102006?**
The gym is titled "2018 ACM-ICPC, Syrian Collegiate Programming Contest". Catalogue
context: syria-2017 has season 2018, finder SCPC-2018, no date, NO results (a note says
Nov/Dec 2017); syria-2018 has season 2019, ran 2018-08-11, and already HAS results. If
the gym is season-named (ICPC style), it's the missing syria-2017 standings — the win.
If it's calendar-named, it duplicates syria-2018. My read: ICPC gyms are usually
season-named, and the syria-2018 edition already has standings from another source, so
gym 102006 most plausibly = syria-2017. Apply to syria-2017?
**ANSWER D5b (apply to syria-2017 / leave for online check / other):**

---

## D6. Older audit leftovers (quick verdicts)

| item | context | recommendation |
|---|---|---|
| lethbridge-2020..2024 | not-real suspects (no trace anywhere); lethbridge-2025 pending eyeball | mark 2020-24 status: unverified-probably-not-held (or delete?) |
| nzpc-2000/2001/2003/2014 | missing real editions (mjd archive proves the series ran) | add stubs |
| thailand-2024 | missing real edition | add stub |
| erc-1983..1987 | missing early European editions per audit | add stubs (thin metadata ok?) |
| FPC-Delft boards | Delft FPC results as bapc-prelims editions | adopt as bapc-prelims? |
| icpc2015 shu/nyist | the two Chinese university-site candidates parked for your look | your call |
| hungary-2013 | CMS row is a 0-team shell; only evidence is a uhunt board; an email to ELTE organizers is the only path | you email? or park |

**ANSWER D6 (per line, shorthand fine):**

---

## D7. Allegheny + Capital

Your inventory lists **allegheny (1978-1991, 14 eds)** and **capital (1979-1991,
13 eds)** as NA sub-regionals; the catalogue has neither series. They come in under any
O1/O2 ruling, but they're also simply a discovered gap.
**ANSWER D7 (add stubs now / wait for layer ruling):**

---

## While you fly

Capture queues were regenerated before you left: site queue **982 → 1,751** (the wave-6
homepage harvest nearly doubled it), URL queue 3,206 → 3,222. When you want captures
running again: re-add boxes on line 21 of `finish-captures.sh`, e.g.
`BOXES=("niemela@kitten-02.scrool.se" "niemela@kitten-03.scrool.se")` (test kitten-01
first: `ssh -o BatchMode=yes niemela@kitten-01.scrool.se true`), then
`caffeinate -i bash finish-captures.sh`. One Ctrl-C now stops everything within ~10s.

Meanwhile I'm running ~12h of container-side research (no dependency on your laptop):
XCPCIO board-data harvest for Chinese regionals, LatAm nationals URL groundwork for the
D2 families, problemset-column expansion, 1980s US regionals archaeology, and pre-writing
the appliers so your answers in this file turn into catalogue changes in one command.
