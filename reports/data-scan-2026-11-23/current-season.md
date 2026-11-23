# Data scan 2026-11-23: current season (agent `current-season`)

Area: every contest of the 2026–27 season (season 2027: 120 contests, of which 46 `upcoming`; wf-2026 left to `struct`), with the contests that ran since about 2026-06-01 in focus.

## How it was checked (rerunnable)

- Inventory from the worktree with `catalogue.load_contests()`: the 46 upcoming contests, and the 65 that ran and are dated 2026-06-01 or later.
- ICPC CMS: the `regionalresults/2027` tree (269 nodes, `work/rr2027.json`). For each of the 115 CMS ids of season 2027, the public record (`/api/contest/public/<abbr>-2027`) and the ranked rows (`/api/contest/public/search/contest/<id>?q=&page=1&size=1000`; **pages are 1-based**, page=0 errors). Script `work/fetch_cms.py`; one JSON per id in `work/cms/`.
- Organiser and host pages, read on 2026-11-23: NERC subregion pages, the regional sites, scorelatam, Kattis contest servers, DOMjudge boards and the ICPC Beijing HQ (Asia East) season table. The evidence quoted in each op is what the page said.
- `work/spec.py` (with `work/mk.py`) writes every op with its evidence: `cd work && python3 spec.py` regenerates `ops.json`. New sources were checked against existing ones with `resources.norm_key`, and one case-only duplicate was dropped (the CMS slug `vietnam-national-2027` against the existing `Vietnam-National-2027`).
- `python3 tools/apply_scan_ops.py --check ../findings/current-season/ops.json`: **111 ok, 0 failed**.
- **Disclosure check:** I looked for problem data on any upcoming or future-dated contest: the `problems:` field, problem-set membership, and sources with `problemset`, `problem`, `editorial` or results roles. **I found none.**

## What the ops fix (111 ops: 88 append, 15 set, 5 unset, 3 insert_contest)

1. **Upcoming contests that have run (5).** Each gets its date, loses `status`, and gains provenance and sources:
   - **azerbaijan-2026**, 2026-11-08. Sources: the NERC page and 68 ranked rows in the CMS.
   - **pacnw-2026**, 2026-11-14. Sources: final D1 and D2 boards, D1 and D2 problem sets, and the CMS standings.
   - **torneo-chileno-2026**, 2026-10-03. Sources: the scorelatam board (it also lists the problem names) and the frozen board.
   - **west-siberia-2026**, 2026-11-21. Sources: the official final standings, the statements PDF and the tests ZIP.
   - **thailand-national-2026**, 2026-09-06. Sources: the host site and the finalized `scoreboard.json` (61 teams, problems A–L).
2. **Wrong dates corrected (3).** The 11-12 tool took the CMS record's last day; the NERC subregion pages give the contest day:
   - moscow-2026: 11-08 → **11-07**
   - central-russia-2026: 11-01 → **10-31**
   - kyrgyzstan-2026: 11-01 → **10-31**
3. **Announced contest day on upcoming contests (4), all 2026-11-29.** Each comes from the official schedule: nwerc-2026, poland-2026 (AMPPZ, Nowy Sącz), jakarta-2026 (day 2 of the rundown) and far-east-russia-2026.
4. **Results sources:**
   - **2026 East Division final scoreboard** (east-na-2026), plus its ECNA, GNY and NENA region views. Before this, east-na, ecna, gny and nena had no results at all.
   - **Moscow:** two full boards.
   - **Uzbekistan:** the opentrains board.
   - **Ukraine:** the final stage-II results.
   - **CMS standings pages for 34 contests.** The CMS holds ranked rows for each, and the contest had no CMS standings source. This includes the four Oman subregionals and tap-2026, which had no results before.
5. **Problems:**
   - The LatAm regional problem-set PDF ("November 7, 2026", 13 problems) on all six LatAm contests.
   - PacNW D1/D2 sets.
   - West Siberian statements and tests.
   - The Greece/Cyprus editorial PDF on greece-2026 and cyprus-2026.
6. **`web` sources (9):** east-na, greece, ukraine, south-russia, moscow, seusa, south-pacific, south-pacific-division and thailand-national.
7. **2026–27 editions missing from the catalogue (3 insert_contest + 3 `next` links):**
   - **croatia-2026:** 2026-11-15, Zagreb and Rijeka. Sources: scoreboard, statements, test data.
   - **hungary-2026:** 2026-10-17, ELTE. Sources: DOMjudge final standings and the ELTE announcement.
   - **alberta-2026:** 2026-10-17. Sources: the Kattis Div 1/Div 2 boards, marked "Unfinalized results", and the problem lists.

   Each copies the shape of its previous edition, and the previous edition's `next` now points to it.

Per-contest lists behind everything below are in `data.json`.

## Items for discussion with Fredrik

**1. Upcoming shells that will not run this season.**
- **The question:** should hefei-2026, jinan-2026 and kunming-2026 be removed?
- **What it implies:** they have no CMS id, no predecessor pointing at them, and the note "upcoming shell from misclass audit 2026-09-02". The official 2026 Asia EC season table lists only nine sites: Xi'an, Chengdu, Wuhan, Nanjing, Shenyang, Shanghai, Nanchang, Hong Kong and the EC Final in Hangzhou ([table](https://icpc.pku.edu.cn/ssxx/bed2c89264fd4d90b08bc93036051186.htm)). The minutes approving the hosts name none of the three.
- **The case for removing them:** the model keeps editions that did not run out of the catalogue. Keeping them leaves three permanent "upcoming" entries.
- **The case for keeping them:** they cost nothing and mark that the series exists. But nothing else in the model uses a shell that way.
- **Recommendation:** remove them. The three `remove` ops are prepared and pass `--check` (`data.json` → `proposed_not_applied_ops`). I did not put them in `ops.json`.

thailand-2026 and manila-2026 are softer cases:
- They have empty CMS shells (9674, 9678), and the only season list leaving them out is unofficial (solved.ac).
- **Recommendation:** keep them until the Asia Pacific director says otherwise.
- This affects thailand-national-2026, which ran on 6 Sep and has `parent: thailand-2026`. If Bangkok is not held, it feeds nothing this season.

**2. 105 CMS ids of season 2027 are in neither the catalogue nor `cms-triage.yaml`.**
- **What they are:** 44 qualifiers/preliminaries, 26 Chinese provincials and invitationals, 18 teens/seniors/high-school contests and 17 others.
- **It is systemic:** season 2026 shows the same gap, for example the Moscow and Kazakhstan qualifications and the ECPC qualification days.
- **The case for bulk triage:** "every CMS entry is considered" is a stated invariant, and the reasons are obvious (`preliminary`, `minor`, `special`).
- **The case for a closer look first:** a few could be in the advancement chain:
  - Dhaka 9657, "Regional Onsite Contest", 2026-11-05, 13 teams; its 2025 twin 9240 is triaged `cancelled`.
  - Taiwan PUPC/TUPC 9672/9673, which feed the Yunlin regional.
  - The SWERC national contests: MIUP 9593, ENS 9594, Ada Byron 9599.
  - The Romanian subregions, 9578–9580.
- **Recommendation:** bulk-triage by keyword, and look at those exceptions by hand. This belongs to whoever owns triage.

**3. Dates taken from the CMS record's last day (5 left unverified).**
- **The contests:** jordan-2026, ethiopia-2026, angola-2026, oman-2026, palestine-2026 (Arab/Africa). Each CMS record spans two days, and the catalogue took the second.
- **Why it matters:** the same heuristic was wrong for all three NERC contests I could check (fixed above).
- **The case for the second day:** for the Arab/Africa contests the second day may well be right. The JCPC 2025 report says the event ran two days with the main contest on day two.
- **Recommendation:** treat these five as unverified. Re-read them when the organisers' scoreboards (scoreboard.acpc.global) are captured. Do not use the CMS last day for new dates.

**4. Contests that ran, with no single contest day:**
- colombia-maraton-2026: the CMS site date is 2026-08-01; the record runs to 10-03.
- kuwait-2026: held 22 and 24 Oct per the host's press release.
- romania-2026: "November 7–8, 2026" per the organisers.
- **Recommendation:** fold these into the open ruling on the 8 span-date contests.

**5. Contests whose date has passed with nothing found:**
- **east-siberia-2026:** 21–22 Nov; the CMS has no rows and its site timed out. Leave it upcoming and re-check this week.
- **pakistan-2026:** only the online preliminary ran (24–25 Oct); the onsite regional is not announced.
- **oman-southern-2026:** its four sister subregionals ran on 2026-04-25 with CMS standings. Southern has nothing and was probably not held. **Recommendation:** ask, or treat it like hefei.

**6. Two smaller modelling questions:**
- **CMS standings on division contests (`south-na-2026`, `east-na-2026`).** I attached the per-region CMS standings only to the regional views. south-na-2026 carries one region's CMS standings unscoped, and south-na-2025 carries a different region's. **Recommendation:** keep the CMS standings on the regional views only, and drop the unscoped one from the division contests (or give it a `scope`).
- **The scorelatam `latam-2026` index page has different roles in the six LatAm contests:**
  - brazil, caribbean: problemset `contains: [statement]`
  - central-america: problemset `contains: [names]`
  - mexico, south-america-north, south-america-south: `scoreboard` only

  **Recommendation:** use one reading everywhere, `[scoreboard, problemset]` with `contains: [names]`. Now that the PDF is a source of its own, it holds the statements.

## Not done, or blocked

- **No problem sets were created.** That includes the new croatia, hungary, alberta, pacnw and west-siberia material, which needs reading once it is captured.
- **Location gaps were not changed.** I listed them in `data.json`. In nanjing-2026, korea-2026 and brazil-2026 the real site is typed `administrative`. thailand-national-2026's CMS site is a stale copy from 2025 (KMITL); the 2026 host was Kasetsart.
- **Sites I could not reach:**
  - Did not answer from here: ikit.sfu-kras.ru (East Siberian), olymp.krsu.kg (the Kyrgyzstan board, `conteststandings/16607`, a lead) and cpc.cpsc.ucalgary.ca.
  - Unreliable: board.xcpcio.com (xian, chengdu and wuhan boards not found).
  - Not used: the Wayback Machine.
- **Trap:** `pnw.na.icpc.global/scoreboard/2026/real_contest/` is a copy of the 2025 board; the 2026 board is `/scoreboard/2026/real/`. Not added.
- **lethbridge-2026:** no 2026 edition found.
