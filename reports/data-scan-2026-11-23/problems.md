# Data scan 2026-11-23: problem sets (agent `problems`)

Area: `problemsets/*.yaml` (1,961 sets, 2,186 member entries, 18,861 problem rows, 2,783 uuids) and their links to contests.
All scripts are in `work/` (`load.py` reads the worktree through `tools/catalogue.py`; `check1.py` links, `check2.py`
counts/letters, `check3.py`/`xset.py`/`xname.py`/`pairs.py`/`na.py` cross-set identity, `check4.py` in-set judge-id clashes,
`names.py`, `judges.py`, `sbread.py`/`sbcmp.py` held scoreboards vs sets). Run each with
`cd findings/problems/work && PYTHONDONTWRITEBYTECODE=1 python3 <script>.py`. Full lists: `data.json`.

The 85 ops pass `apply_scan_ops.py --check` (85 ok). I also applied them to a scratch copy outside the mount and ran
`tools/validate.py` there: 0 errors, the same 7 known warnings as before.

Two process slips, both fixed. Early on, two scratch JSON files landed in the worktree root because `load.py` changed
directory. I moved them out to `work/`, so nothing of mine is left there. I also ran one `git status` in the worktree
before I noticed the brief forbids git there. It is read-only apart from a possible index refresh.

## What was checked, with counts

| check | result |
| --- | --- |
| contest `problems.set` exists / set lists the contest back / members exist | 0 problems. 21 sets (kth-*, bergen-*, naipc-*) are used only by `registry/non-mainline.yaml` contests, which is fine |
| sets used by no contest | 0 |
| **disclosure: upcoming contests with a set, names, letters, count or problem sources** | **0 of 46**. No source description of an upcoming contest mentions problems either. One gap in the guard (D8) |
| uuid format / same uuid in two sets | format clean (schema). Only wf-2022/wf-2023 share uuids (5), which is correct |
| duplicate problem ids / uuids inside a set | 0 / 0 |
| same name twice in a set | 3, all as their sources list them (oman-2025 "Game", oman-2026 "The Frankincense Trail", wf-1983 "Mousetrap"). Left alone |
| judge links missing judge/url/id, unknown judge ids | 0 / 0 / 0 |
| same judge id on two problems of one set | 6, all south-na-2023. **Fixed** |
| problems carrying two Kattis links (contest instance + open.kattis) | 300 rows. Fine |
| two ids on one judge (two CF gyms, CF round + gym, Baekjoon duplicates) | 51. Fine |
| `letters: unknown` while a member has a map | 2 (south-na-2025, south-na-2026). **Fixed** |
| sets with neither count nor problems (empty placeholders) | 37 (D6) |
| `complete: false` without count | 39 (list in data.json) |
| letter gaps in member maps | 159: 71 partial maps on a full list, 32 on incomplete sets, 40 non-contiguous letterings (mostly real: CTU Open, NZPC, P = practice), 16 Latin America sites with partial maps |
| problems reached by no letter | 90 sets |
| maps with exactly one letter and one problem left (fill_letters rule) | 3. **Fixed** |
| letterings identical across all members of a shared set | 57 of 73 shared sets. Each member stores a full copy of `letters:` (no set-level map). 13 sets have differing letterings; in 3 only one member has a map |
| shared sets whose members have different dates | 24 (mostly ±1 day at Latin America sites; outliers in D9) |
| held scoreboards read against sets (1,173 contests readable) | 84 letter maps and 19 counts disagree (many are partial maps or reader errors); 32 contests' own scoreboards disagree with each other; 112 match the count but have no letters; 11 contests had no set (D4, D7) |

## What the ops fix (85)

- **south-na-2023 (20 ops).** Six Division 2 Kattis links (`nasouth23d2/problems/acappellarecording` …) had been put on
  the Division 1 problem with the same letter ("Cramming for Finals", "Eccentric Excursion", "Matrix Fraud", "On-Call
  Team", "Range Editing", "Segment Drawing"). They are moved to their own problems. The contest's member entry becomes
  `divisions` (Division 1 = the old map, Division 2 from the live Kattis D2 page; both pages read 2026-11-23). This
  follows the ruling that two-division contests keep letters per division.
- **south-pacific-central-2017 (7 ops).** The problem "total teams" with letter `63` was the scoreboard's team-count row.
  It is removed from all three member maps, and count goes 13 → 12 (the held Scoreboard.htm has columns A–L).
- **nanjing-2024 (3 ops).** Count goes 2 → 13 and `complete: false`. The count came from a Luogu page that holds 2
  problems; the held Codeforces gym 105484 scoreboard has A–M.
- **ncna-2024 (4 ops).** Count 12 (held scoreboard A–L), and letters B, E, F, H for four listed problems, matched by
  Kattis id. "Which Number Kind Is it?" is not on the NCNA scoreboard (D10).
- **Letters by the fill_letters rule (6 ops).** cerc-2000 F = Factorial, ncna-2014 D = Server, rmc-2011 E = Pills.
- **`letters: unknown` removed (2 ops)** from south-na-2025 and south-na-2026.
- **New count + labels sets (4 ops).** west-neerc-2026 (13, A–M) and vietnam-national-2026 (13, A–M). Both ran after
  the 2026-11-16 scoreboard round; read from their held final scoreboards.
- **Names (45 ops).** 37 CodeChef names lose their letter prefix ("B - Fair Removals" → "Fair Removals"; amritapuri-2025,
  chennai-2025, kanpur-2025, gwalior-pune-2019, kanpur-2019, kharagpur-2018/2019). Eight lose markup:
  - ecna-2023 "Prof.~Fumblemore…" → "Prof. Fumblemore and the Collatz Conjecture", as in east-na-2023 and gny-2023
  - hangzhou-2008 "D&eacute;j&agrave; vu" → "Déjà vu"
  - moscow-2021 "1\%-Euclidean" → "1%-Euclidean"
  - nerc-2020 "…/\textbackslash/\textbackslash" → "Equilibrium Point /\/\", per the offline statement PDF
  - brazil-first-phase-2023 "$K$ for More, $K$ for Less" → "K for More, K for Less"
  - syria-2019 "V--o$\_$o--V" → "V--o_o--V"
  - aec-2019 "Dirichlet  k -th root" → "Dirichlet k-th root"
  - moscow-2022: a double space removed

  I did not keep the old strings as `other_names`, the field the catalogue uses for aliases: a letter prefix or
  LaTeX residue is not another title of the problem. Left alone on purpose:
  - real titles that only look wrong: "A. Nihilation" (jakarta-2025, a pun on Annihilation), "M. S. I. S.",
    "L. N. Tolstoy's Problem", "V. Cipher", the South Pacific "ja$on" titles, "#exclude<scoring>"
  - the BOSPRE (nena-east 2008–2017) lowercase names like "equity" and "paxos": the BOSPRE 2008 index lists the
    problems by exactly these file names (`problems/equity`), so they are the official titles.

## Held-back items from 2026-11-01: current state

- **ecna-2016 (count 10)**: settled, 10 is right. The live https://icpc-ecna.ysu.edu/PastResults/2016/problemset.html
  shows a 4-problem *Practice Contest* (Dinoscan, Happy Trails, Prime Driving Conditions, Time is of the Essence). Those
  4 plus the 10-problem real contest make Kattis's 14. The held scoreboard has 10 columns.
- **ecna-2019 (11)**: settled the same way. The /2019/problemset.html page lists a 6-problem practice contest (Chopping
  on Line … This Problem's a Slam Dunk) plus 11 real; the scoreboard has 11.
- **mcpc-2015 (9)**: the held scoreboard has 9 columns, so the count stands. "Square Deal" is not on it.
- **socal-2020 (11)**: settled. Kattis's source is the joint "NCNA and SoCal 2020-2021" set. Agamemnon's Odyssey is only
  in ncna-2020 (letter F; qoj 3281, outside SoCal's 3252–3262 run).
- **naq-2022 (12)**: still open (D3). The scoreboard has 12 (A–H, J–M), but the statement PDF has 13 including
  I "Problem Pool".
- **nwerc-2010 Kattis link**: resolved in the data. The set links the NWERC 2010 problem-sources page, and nwerc-2011 has
  its own problems.
- **nwerc-2003 ("likely 9")**: refuted. The held results2003.html has 8 columns A–H, and the set already lists "Subway
  tree systems" (E). The note "Missing problem H" is about the archive package.
- **bapc-2020 K uuid conflict**: unchanged (04309ae6… kept).
- **North America shared sets 2019–2023**: still one set per regional. Shared problems are separate problem ids in each
  set:

  | season | problem rows | distinct problems |
  | --- | --- | --- |
  | 2019 | 186 | 155 |
  | 2020 | 184 | 112 |
  | 2021 | 189 | 123 |
  | 2022 | 169 | 99 |
  | 2023 | 149 | 101 |

  Only scusa-seusa-2020 and south-na-2022/2023 were merged. See D2.

## Items for discussion with Fredrik

**D1 (high). NERC 2020: the set mixes two contests.** The catalogue's nerc-2020 is "2020 Northern Eurasia Finals
Online" (2020-12-13). Its set holds the onsite problems as A–K (ASCII Automata Art … King's Task, CF 1510) plus the
online contest's L–O (Lookup Performance … Optimum Server Location). The online problems A–K (Almost Balanced Tree …
Kate's 2021 Celebration) are missing. The Codeforces links 102896/A–K on the onsite rows point at the online problems:
the Wayback copy of gym 102896 is titled "Northern Eurasia Finals Online 2020", with A = Almost Balanced Tree. count 26 =
15 online + 11 onsite.
- Option (a): one contest with two rounds, stored as `divisions: {Online: A–O, Onsite: A–K}`, count 26. Keeps every
  problem in the catalogue.
- Option (b): nerc-2020 = online only (15 problems), and the onsite becomes its own contest or is dropped.
  Matches the contest name.
- Recommendation: (a) now, since it fits the "divisions (or rounds)" model. I left it untouched because it adds 11
  problems and moves judge links.
- Evidence: nerc.itmo.ru/archive/2020/nerc-2020-{online,offline}-statement.pdf.

**D2. Unify problems that two sets share (one problem id, as wf-2022/2023).** 522 problem-id pairs across sets are the
same problem by judge-id agreement (92 groups), and 595 same-season same-name cross-set pairs exist. Most are North
America 2019–2024, PacNW/SER 2014–2019, BAPC/UKIEPC 2020–21 (BAPC renamed them: "Aquarium Arrangement" = Aquarium,
"Xortest Path" = Kleptocrat), NCNA/SoCal 2020 and South Pacific 2014–15.
- For: problem pages aggregate every appearance, and uuids reach the sets that lack them. Two independent sources
  agreeing is the accepted evidence.
- Against: it is real work, and different-letter sets stay separate sets by your ruling; only the problems are shared.
- Recommendation: a tool pass that gives judge-id-agreed problems one id (the uuid one where present) and keeps the
  other ids as problem `aliases`.
- Also reuse across years, which is legitimate: GNY 2021 I = GNY 2023 E (acmgnyr.org lists "I-Tetrasphere" and
  "E-tetrasphere"); vietnam-2021 / vietnam-national-2021 share 4; azerbaijan-2019 reuses 5 poland-2019 problems; the
  MAUSA practice problem "A Contesting Decision" is in mausa-2003 (as A) and mausa-2004 (as P).

**D3. naq-2022 I "Problem Pool".** It is in the statement PDF (A–M, 13) but not on the scoreboard or the naq22 Kattis
problem list. It was probably withdrawn.
- For count 13: your ruling that "the document's count wins".
- For count 12: what the teams sat.
- Recommendation: count 12 with a note, or 13 with I flagged as withdrawn. Your call.

**D4. 2026 Northern Eurasia regionals: one shared set, no set yet.** armenia, georgia, kazakhstan, north-russia,
tajikistan, taurida, turkmenistan and urals 2026 all ran 2026-11-14, and their held scoreboards print the same 14
titles A–N (AALEX.EXE … Nuts and Bolts). I did not create 8 per-contest sets. The question is the set's id: the
DEFINITIONS rule (series joined alphabetically) gives an unwieldy name. Earlier years use `north-russia-<year>` with the
others as members (2005–2025), and `nerc-shared-2021` exists. Recommendation: `north-russia-2026` with the 8 members,
as in earlier years.

**D5. Sets that should be one (same day, same problems, same letters).** Recommendation: add these to
merge_problemsets.py's PLAN (it keeps aliases).
- armenia-2023 → north-russia-2023; armenia-2024 → north-russia-2024
- uzbekistan-2011/2012 → north-russia-2011/2012; kazakhstan-2004 + north-russia-2004
- south-america-2005 → latam-2005; south-america-2006 → latam-2006; brazil-2004 + south-america-2004 → latam-2004
- east-na-2024 + ecna-2024 (like east-na-ecna-2025)
- mausa-2022 → south-na-2022 and mausa-2025 → south-na-2025 (Division 1 lists, same letters, as mausa-2023/24 already)
- tap-2020 → brazil-first-phase-2020 (its BOCA global scoreboard has Argentina sites, A–O, 15 = the set)
- Open questions:
  - werc-1993/swerc-1993 and werc-1994/swerc-1994 have identical lists under two contests. Was it the same contest, or
    a shared set?
  - ecna-2023 and nena-2023 sat the same 12 problems under different letters, and east-na-2023 holds them again. By
    your lettering rule they are two sets, but then east-na-2023 duplicates one of them.

**D6. 37 empty sets** (alberta-2019, lethbridge-*, turkey-2020–23 …) carry only `complete: false`.
- Keep them: they mark "a list is known to exist".
- Drop them and the contests' links: an empty set says nothing.
- Recommendation: fill from held scoreboards where possible (alberta-2019, lethbridge-*, turkey-2020: "not read" by the
  reader), otherwise drop.

**D7. Counts and letters that disagree with held scoreboards** (data.json `held_scoreboards_vs_sets`).
- Counts worth a look: kharagpur-2012 8 vs 10, kyrgyzstan-2005 8 vs 9, ncna-2000 8 vs 10, ncna-2003 9 vs 10,
  neerc-1996 6 vs 7, rmc-2004 8 vs 9, south-pacific-2010 9 vs 11, south-russia-2003 9 vs 10, vietnam-national-2018
  13 vs 12, alberta-2020/21/22/24 (the set has more, probably the open division).
- naq-2020 has count 4 (letters B, E, G, H) while the scoreboard has 8.
- Letter maps that differ in length from the scoreboard: alberta-2011 (10 vs 9), awc-2019 (11 vs 13), azerbaijan-2025
  (14 vs 12), croatia-2025 (11 vs 12), north-russia-2021 (15 vs 14), romania-2013 (11 vs 14), south-pacific-2016
  (11 vs 12), bolivia-national-2024 (12 vs 11).
- rmc-2001 (9 vs 8) is already ruled 9.
- 112 contests have a count matching their scoreboard but no letters.
- Recommendation: a second scoreboard round for letters, then a look at each count mismatch.

**D8. Disclosure guard gap.** validate.py fails a not-yet-run contest only when its set has problems, a repo or holdings.
A set with just `count` + `labels`, or a bare membership, passes. Recommendation: fail on any set membership of an
upcoming or future-dated contest.

**D9. Shared-set members on very different dates.** These point to contest-date errors (for the dates agent), not set
errors:
- south-america-north-2011 2011-06-17 and south-america-north-2012 2012-10-11 (siblings 11-05 / 11-10)
- south-america-north-2008 11-30 and central-america-2008 11-02 (siblings 11-15)
- kazakhstan-2022 2022-10-01 (siblings 10-29); burkina-faso-2017 05-08 (siblings 05-13); armenia-2018 10-26
- mausa-2021 2022-02-06: its held Kattis scoreboard shows 2022-02-26 13:00–18:00, and it shares all 13 problems with
  ncna-2021 (02-26). Very likely a typo.

**D10. ncna-2024 vs mcpc-2024/rmc-2024.** The NCNA 2024 scoreboard shares 7 problems with mcpc-2024 (towel, bigand,
enchantedmaze, guardevaders, palindromicwordsearch, sauna, spaceelevator). "Which Number Kind Is it?" sits in the NCNA
set only via the Kattis export, and the NCNA scoreboard does not have it. Recommendation: drop it from ncna-2024 once D2's
pass links the shared problems.

**D11 (low). Name forms left for you.**
- 81 ALL-CAPS codes (kabul-2019 Baekjoon codes like BNKQ/LTBL, CodeChef codes in amritapuri-2011/2015, erc-1991
  capitals) and the greece-2025 gym slugs ("zerorush" …): fix from statements where we hold them.
- The ECNA/NCNA 2014 continued-fraction title is stored as LaTeX: keep it, or use a plain "Continued Fractions"?
- syria-2022 "$I^{th}$ String".
- Practice problems carried as letter P in mausa-2002/04/10/11/12 and poland-2013: count them or not?
