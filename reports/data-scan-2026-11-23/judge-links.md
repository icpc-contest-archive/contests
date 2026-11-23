# judge-links — data scan 2026-11-23

Area: per-problem online-judge links (`judges:` in problemsets/*.yaml) and `judges.yaml`.
Note: the worktree changed under this scan (another session applied a Live Archive host swap, a new `uva` judge with the
148 UVa links and 17 Dhaka sources, `livearchive` closed, and the CodeChef letter-prefix renames). ops.json is rebased on
the worktree as it stood at 09:31 and passes `--check` (172 ok).

## 1. Statement pages from the 2026-11-22 top-up vs. catalogue names

How (rerun from `work/`): `build_map.py` (judge URL -> problems), `join_queue.py` (top-up queues
`archive/topup-*problems*-2026-11-22.json`, `topup-qoj-statements-2026-11-22.json`, `topup-cf-gym-statements-2026-11-23.json`
joined to `archive/index.json` captures by URL), `extract.py` (title + source/contest line per judge; gzip-stored captures
decompressed), `compare.py` (normalised title vs `name`/`other_names`), `pdfcheck.py` + `ocrcheck.py` (QOJ PDFs: full text, then
OCR of the page top), `letters.py` (judge letter vs set letters), `contest_strings.txt` (judge's contest line per set).

2,727 captured pages + 9 whole-set Codeforces PDFs (99 problems) checked:

| judge | pages | title = catalogue | differs only in form | translation | not the page asked for |
| --- | ---: | ---: | ---: | ---: | ---: |
| Codeforces | 829 + 9 set PDFs | 828 (PDFs: 99/99 names found) | | | 1 |
| Baekjoon (Wayback) | 567 | 563 | | 4 (Korean) | |
| QOJ | 384 | 344 (+28 title-less PDFs confirmed by OCR or body text) | 5 | 6 (Chinese names in catalogue) | 1 (truncated PDF) |
| Kattis | 197 | 197 | | | |
| CodeChef | 190 | 164 | 24 (catalogue name carries the letter) | | 2 ("Error" page) |
| Luogu | 171 | 171 | | | |
| HDU | 159 | 159 | | | |
| PTA | 71 | 70 | | | 1 (generic page) |
| SGU 36, eolymp 36, Timus 33, SPOJ Brasil 31, Szkopuł 13, HackerRank 1 | 150 | 124 | 5 | 21 (Polish/Portuguese) | |

No judge page points at a different problem of the same set. QOJ PDFs with no title text (ACPC 2015, SWERC 2004/2006) were
OCR'd or read: the body matches the catalogue problem in every case.

Findings that are not link errors (no op):
- **Capture faults** (for the capture owners): `acpc-2021` H (Codeforces group 477871/problem/H) was stored from a redirect to
  problem G ("Game of Science"; manifest final_url .../problem/G); 2 CodeChef pages are "Error" (AMR14B, MOBCNT);
  PTA ZOJ 3542 (`dalian-2011` Number String) is the bare app shell; QOJ statement 11013 (`shanghai-2019` Bob's Poor Math) is a
  truncated PDF; 17 Baekjoon Wayback captures are stored gzip-compressed (list in data.json `gzip_captures`).
- **Translations, same problem**: Szkopuł `poland-2023` (13 Polish titles, e.g. "Analiza Autobusowa" = Bus Analysis),
  SPOJ Brasil `south-america-2006` (8 Portuguese, e.g. "Roleta turca" = Turkish Roulette), Baekjoon Korean titles for
  japan-2006 D/E ("서로 다른 소수의 합" = Sum of Different Primes, "맨하탄 배선" = Manhattan Wiring) and mausa-2010
  ("풍선" = Balloons, "팰린드로미터" = Palindrometer). Eolymp 3757 is "John, Bruce and juice" where the catalogue has
  "...and beer" (eolymp's edit). SGU 163 is "Wise King", catalogue "The King" (from Baekjoon; no held statement: left).
- **beijing-2018**: QOJ's PDF for Jin Yong's Wukong Ranking List carries the header "Problem A. Heshen's Account Book" (a
  header slip in the PDF; the text is the Jin Yong problem).
- **Letters**: judge letters differ from set letters only where problems are shared between regionals (Baekjoon files them
  under the other contest: pacnw-2016/2018, mausa-2016, ncna-2014; QOJ pacnw-2020 and gny-2023 PDFs carry the lettering of
  another contest of the shared set). 45 cases in data.json `letters_differ`; relevant to the held-back "shared North-America
  sets 2019-2023" item, not to links.

### Ops prepared (ops.json, 172 ops, all `ok` with `--check`)
- **7 names from held QOJ statement PDFs** (statement title wins, the old title kept in `other_names`, set provenance line
  appended; ruling 2026-11-22: a held online-judge copy counts as the statement): aec-2024 大学之北 (Dàxué zhī běi,
  "north of the university") -> "Norte da Universidade", 考拉兹猜想 (Kǎolāzī cāixiǎng, "Collatz conjecture") ->
  "Collatz Conjecture"; aec-2025 高效快递 (Gāoxiào kuàidì, "efficient express delivery") -> "Efficient Express" (PDF headed
  "The 2025 ICPC Asia East Continent Final Hangzhou ... Problem E"); hong-kong-2025 循环移位 II (Xúnhuán yíwèi, "cyclic shift")
  -> "Cyclic Shift II"; moscow-2023 反转字符串 (Fǎnzhuǎn zìfúchuàn, "reverse a string") -> "Eirt Eht Esrever"; shanghai-2024
  等量 (Děngliàng, "equal amount") -> "Equal Measure"; beijing-2018 "Xor 2" -> "Xor" (PDF "Problem E. Xor"). 20 ops.
- **25 CodeChef headings kept as `other_names`** ("B - Connect 3") for the names another session already stripped
  (chennai-2025 11, kanpur-2025 11, gwalior-pune-2019, kanpur-2019, kharagpur-2019). 25 ops.
- **90 Live Archive links verified against a Wayback snapshot** (section 3): `as_of` set on all 90; `url` corrected on 36
  of them (23 wrong internal problem numbers, 13 only snapshotted in the `&category=` form). 126 ops.
- **judges.yaml**: `eolymp` has `problem_url` twice (YAML duplicate key: `basecamp.eolymp.com/en/problems/{id}` then
  `eolymp.com/problems/{id}`; the loader keeps the second). The op sets the value the loader already sees, so the rewrite
  drops the duplicate line. 1 op. (My `livearchive` fixes - closed, no submissions, old LA addresses - were made in the
  worktree meanwhile by another session and are dropped from ops.json.)

## 2. judges.yaml

Rerun: `work/linkcheck.py`. All 29 ids are used and every id used is registered (no orphans, no unknown ids). Baekjoon:
every link has `as_of`, none after the closure. Status: the Live Archive was `active` with onlinejudge.org as its address;
it is now closed in the worktree (the host does not resolve, 2026-11-23; last Wayback snapshot of its home page
2022-04-19). POJ answers again (200, 2026-11-23). Address patterns that the recorded ids do not fill are by design for
Codeforces (`gym/letter`), HDU (`cid/pid`), NowCoder, TLX, HackerRank, PTA (address ids come from PTA's list, in runs; the
70 captured PTA pages all match their ZOJ number) and 24 CodeChef contest-path links. Two to note: 575 Kattis links go to
contest subdomains (e.g. `https://acpc16.kattis.com/contests/acpc16/problems/bits`) rather than open.kattis.com, and the
290 eolymp links use `basecamp.eolymp.com/en/problems/N`, which redirects to `eolymp.com/problems/N` (36 of 36 captures).

## 3. Live Archive links: the Wayback form (ruling 2026-11-22)

Rerun: `work/la_wayback.py SECONDS` (resumable, state in `work/la_wb.json`, 1 request per 1.5 s, random order so any
prefix is a fair sample). For each link it asks the Wayback Machine for
`icpcarchive.ecs.baylor.edu/index.php?option=com_onlinejudge&Itemid=8[&category=C]&page=show_problem&problem=N`,
reads the snapshot's `<h3>LA number - title</h3>`, and accepts it only when the number is the link's LA number and the
title is the catalogue name or one of LA's own titles for that number. N: from LA's category pages that we hold (283
captures, 2,215 LA numbers), else estimated from the nearest held number, else the stored one; when the snapshot shows
another number, N is shifted by the difference and tried once more.

What the old links got wrong: the LA number (`id`) is right (2,242 of 2,250 checked against LA's own category pages; the 8
others are problems LA lists under two titles, e.g. acpc-2001 "Control Break" = nena-2001 "Give me a break!", LA 2298;
cerc-2001 reused five swerc-2001 problems under other titles), but the internal number in the address was computed as
"LA number - 1999" and similar offsets. Where we hold the category page it is right (2,072 of 2,102); elsewhere about half
are wrong. **The host swap now in the worktree kept those numbers, so about 1,900 of the 5,971 links (half of the 3,869 whose LA number is on no held category page) open another problem
on the old LA too.**

Sample of 110 links (random): 90 verified (82%), 23 of them only after correcting N (all outside the held category pages:
23 of 46 there), 13 only in the `&category=` form; 20 have no snapshot of the problem page, but 11 of those have a snapshot
of the statement itself. The statement files (`/external/<LA div 100>/<LA>.pdf` or `.html`), which depend on the LA number
alone, are in the Wayback Machine for 5,225 of the 5,971 (4,932 PDF, 293 HTML; complete CDX listing, 14,459 addresses);
3 of 3 fetched were the right statements. Problem page or statement: 101 of 110 (92%) have some snapshot.

Verified UVa research, for the record (no data change): 148 of the 6,119 "Live Archive" links were UVa numbers and right on
onlinejudge.org (148 of 148 title and internal number match UVa's volume pages); they are now `uva` in the worktree.

## Items for discussion with Fredrik

1. **Three problem sets are another contest's problems.** The 2026-11-13 gym import took the wrong gym:
   `aec-2023` (EC-Final 2023) holds Codeforces gym 104639 "The 2023 ICPC Asia EC Regionals Online Contest (I)";
   `nanjing-2025` holds gym 106084 "2025 ICPC Asia Taiwan Online Programming Contest"; `south-russia-2018` holds gym 101911
   "... Southern Subregional Contest, Qualification Stage", while our own held copy of codeforces.com/contest/1070 (the
   subregional) lists 13 other problems (Find a Number ... Algoland and Berland). The right lists are in data.json
   `wrong_sets` (EC-Final 2023 = QOJ 8047-8059; Nanjing 2025 = QOJ 14801-14813; Southern 2018 = contest 1070 A-M).
   Implies: 36 problems (names, letters, links) to replace. For replacing: three independent sources disagree with the
   current lists and the gyms' own titles name another event. For keeping: nothing. Recommendation: replace from the lists
   in data.json (QOJ titles to be confirmed from the statements when captured) and drop the wrong problems; neither online
   qualifier is a catalogue contest.
2. **Finish the Live Archive links.** Question: run `work/la_wayback.py` over all 5,971 (about 2.5 hours at one request per
   1.5 s; the device shell stops background jobs, so on the Mac itself), and for the ~9% with no problem-page snapshot link the
   statement PDF instead? For the problem page: it is the address the link always meant. For the statement PDF: its address
   depends only on the LA number, so it cannot point at the wrong problem, it covers 87.5%, and under the 2026-11-22 ruling a
   held copy of it counts as the statement. Recommendation: problem page where verified, statement PDF where not, and capture
   the PDFs. Until then the ~1,900 wrong internal numbers make the links wrong in a new way (example: shenyang-2016
   "Relative atomic mass", LA 7613, problem=5614 is LA 7592 "Hidden Anagrams").
3. **Letters of chennai-2025 and kanpur-2025.** Every CodeChef heading carries the letter (A-K, alphabetical by title), but the
   sets now say `letters: unknown`. Set the two letter maps (in `work/codechef_letters.json`)? For: read off the contest's own
   platform. Against: the order is alphabetical, which a mirror could have imposed. Recommendation: set them.
4. **Capture faults to redo** (not data): acpc-2021 H stored as problem G; CodeChef AMR14B and MOBCNT "Error" pages; PTA ZOJ
   3542 app shell; QOJ statement 11013 truncated; 17 Baekjoon Wayback captures stored gzip-compressed (data.json).
5. Small: SGU calls `north-russia-2002` I "Wise King" (catalogue "The King", from Baekjoon; no held statement); eolymp 3757 says
   "juice" where the statement says "beer". Add the judges' titles as `other_names`? Recommendation: yes for SGU, no for eolymp.

## Files
`ops.json` (172 ops), `data.json` (title-check differences, letter differences, wrong sets with replacement lists, link-pattern
counts, the 148 UVa links), `work/` (scripts above; `la_wb.json` sample results; `net/` fetched UVa volumes and CDX lists).
