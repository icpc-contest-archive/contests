# Flight-pack rulings — state as of 2026-09-04 ~16:30Z

Source: Fredrik's mid-flight reply to reports/flight-pack-2026-09-04.md.

## Ruled / done
- D4 (misclass audit): ALL RATIFIED — edits+adds+shells applied and committed on device
  (77fa97f), validate clean; kanpur-2022 + nena-2026 warnings auto-resolved.
- D3b: girls / seniors / teens are NOT mainline (cannot qualify to WF from them) → registry. FINAL.
- D5a: hungary SZTE rejection stands (his caveat: "the hungarian contest is sometimes strange").
- D5b: RESOLVED + COMMITTED (237023f) — CF gym 102006 = calendar-2018 SCPC = syria-2018
  (finder titles SCPC-2019 "The 2018 Syrian CPC"; gym published 2018-11-23); syria-2018
  already carried the gym from wave 3, so no data change was even needed; syria-2017 stays dark.
- D6 FPC: DROPPED — FPC = Delft Freshmen PC (CHipCie: own SKP/DnAKP lineage 2005-2026),
  not bapc-prelims. My wave-5 hypothesis was wrong.
- D6 shu/nyist: identified — bnuoj/board.acmicpc.info wayback'd PC^2 onsite boards
  (icpc2015/shu_onsite.php + nyist_onsite.php, 2015-16 Chinese season); remaining task =
  open both snapshots and match host (SHU Shanghai Univ / NYIST Nanyang) to catalogue rows.
  Snapshot URLs in data/cdx-bnuoj2-2026-09-02.json.
- D7: RATIFIED — add allegheny (1978-91) + capital (1979-91) stubs, unverified-year flags,
  print-only evidence noted (SIGCSE Bulletin / ACM CSC proceedings; R3 findings).

## Fredrik's D1 decision frame (replaces the O1-O4 tier framing)
Real-contest rules of thumb:
- R1: single-university (or few local universities) = local qualifier, not real.
- R2: must use unique NEW problems; problem-reusers are not real contests.
  (Distinct issue: a set SHARED simultaneously across siblings of one round — siblings may
  "really be one contest"; keeping split entries is fine where qualification depends on the split.)
- R3: must be on the WF path in SOME way; zero qualification effect = not mainline
  (KTH-contest example: multi-university + unique problems but affects nothing, runs after
  its logical parent).
- R4 (leaning, unsettled): mainline = NOT online, with COVID-year exceptions.
Identity-not-tier: "preliminary" = a round with its parent's geography and no identity of
its own; sub-regional vs preliminary is not a clean tier distinction.

## Open — dossier DELIVERED (reports/family-dossier-2026-09-04.md + data/d1-dossier/*.json); awaiting his D1'/D2'/D3' answers from its revised answer sheet
- D1 final wording (esp. the online rule) — decide after seeing which families it flips.
- D2 per-family verdicts — dossier delivers facts + for/against per family against R1-R4.
- D3a oman-subregions: leaning INCLUDE (not the seniors row); pending dossier facts.
- D3c caribbean: nationals→mainline, campus locals→registry (aligned with his reply); pending confirm.
- D3d thailand: national→mainline, group rounds→registry; pending qualification-edge confirm.
- D3e taiwan: advice owed after dossier (TOPC online status + tech/private-univ qualification role).

## Wave-8 research banked (both tranches; 542 candidates in data/*wave8*.json)
Tranche 2 highlights: t2-ukraine STRUCTURAL FINDING — the existing ukraine-<year> rows are
Stage-II-dated, so the 81 region worklist rows merge into EXISTING entries (no
ukraine-stage2-* stubs); the missing layer is the Stage III FINALS; canonical unified
Stage-II standings live at acmallukrainian.ho.ua (2017-2024). t2-dark unlocked 8 more
contests (incl. poland-2025, nena-north-2019, bulgaria-2010); 119 remain dark, documented.
t2-seerc: official SEERC standings 2018-2024; icpcarchive.github.io = problemsets only
(36 series, zero standings). t2-asia: Vietnam 2016-2025 scoreboards via icpcvn.github.io,
Myanmar complete via UCSY; the icpc.global finder (JS) is the canonical source for most
Asia nationals — a headless/API pass would unlock hundreds of standings project-wide.

## Queued for reconnect (laptop offline)
1. Verify/complete the D5b commit (above).
2. Commit container-side changes: tools/apply_misclass_fixes.py note→notes fix (already
   fixed on device pre-commit), this file, wave-8 candidate files, the D1 dossier.
3. Project memory updates (capture-state + url-hunt): D4 done, D5b resolution, FPC drop,
   ukraine terminology correction (macro-region first stages, not oblasts).
4. Allegheny/capital stub generation (D7) — needs device yamls.
5. Delete-permission was re-granted mid-flight; if the session reconnects fresh it may
   need asking again (git lock cleanup).
