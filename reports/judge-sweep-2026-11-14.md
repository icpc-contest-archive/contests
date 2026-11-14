# Judge sweep — 2026-11-14

Question asked: four registered judges had no problems and no problem sets (beecrowd, PTA,
the Universal Cup judge, vjudge). Is there nothing there, are there more judges, and was the
whole vjudge.net list checked?

## The four empty judges

| judge | outcome |
|---|---|
| beecrowd | Not empty. The judge needs a login, but statements are public at `resources.beecrowd.com/repository/UOJ_<id>_en.html`. All 2,489 read; 512 links in 51 sets. |
| PTA (pintia) | Not empty. Hosts the old ZOJ archive publicly (3,179 problems). 1,045 links in 135 sets, matched by title in runs of neighbouring ZOJ numbers (ZOJ keeps no source field there). |
| Universal Cup judge | Dropped: its problems live on QOJ. |
| vjudge | Dropped: it proxies other judges and has no problems of its own. Still the best finding aid. |

## The vjudge.net list

vjudge lists 62 judges. The 2026-11-13 hunt read 11 (UVALive, Gym, QOJ, HDU, POJ, URAL, Aizu, ZOJ,
SPOJ, Jisuanke, EOlymp). The other 51 were swept on 2026-11-14 by source keyword (ICPC, ACM, Regional,
World Finals, NEERC, CERC, … and years where a keyword hit the 400-row cap), then matched by title
to the catalogue within one source string.

### Added

| judge | links | sets | what |
|---|---|---|---|
| Luogu (already registered) | 1,287 new | 111 | read from Luogu's own problem search (2,822 tagged problems), not vjudge |
| Bailian (new) | 485 | 64 | PKU OpenJudge; same numbers as POJ |
| POJ (already registered) | 424 new | 55 | the Bailian matches whose POJ title is identical |
| VNOJ (new) | 133 | 11 | Vietnam regional and Vietnam National 2019–2023, Ho Chi Minh City 2008 |
| TLX (new) | 107 | 9 | Jakarta 2017–2025 |
| HackerRank (new) | 96 | 10 | 2014 regional practice contests, ACPC 2013–2015 |
| LibreOJ (new) | 24 | 2 | World Finals 2017, CERC 2018 |

Lists are in `data/judge-links-2026-11-14/`, applied by `tools/import_judge_links.py`.

### Found but not added

- **Dead judges** (vjudge marks them not alive; a link would go nowhere): HIT (275 matches in 57 sets),
  the three BZOJ copies (179), CSU (97), FZU (71), HRBUST (54), HihoCoder (42), UESTC_old (12).
- **Unclear hosts**: UESTC at cdoj.site (147 matches in 16 sets), HUST at hustoj.org (75). The
  original sites are gone; these are re-hosts and were not checked.
- **Needs matching by letter, not title**: LibreOJ World Finals 2018–2025 (97, Chinese titles);
  Luogu Nanjing 2022–2024, Jinan 2023 and World Finals 2022/2023 (Chinese titles).
- **Not catalogue contests**: VNOJ provincial rounds (north/central/south, 2021–2024), TLX IDEAFUSE
  Sumatra rounds, HihoCoder Beijing online rounds, AtCoder JAG practice, Toph and HackerRank local contests.
- **Nothing ICPC found**: CSES, DMOJ*, SCU, 51Nod, CSAcademy, Yukicoder, Yosupo, NowCoder*, LightOJ,
  EIJudge, Szkopuł, UVA, Z_trening, ACMP, USACO, OpenJ_NOI, OpenJ_POJ, CodeChef*, OJUZ, Daimayuan,
  Minieye, UniversalOJ, Kilonova, CSG, ACdream, NBUT, TopCoder. (* vjudge carries no source for these;
  the judge itself was hunted directly on 2026-11-03.) UVA has no source field on vjudge either, so
  the sweep says nothing about it.

## New problem lists (second round, same day)

`tools/add_problem_lists_2026_11_14.py` created 110 problems in 22 sets, assigned by the judge's own
source string rather than by title:

- New sets: south-russia-2002 (9), south-russia-2003 (9), south-russia-2004 (11) from SGU;
  kyrgyzstan-2005 (8, Russian titles) from KRSU.
- Sets that had one or two names: wf-1995 (1 → 8), north-russia-2002 (2 → 9), beijing-2004 (1 → 9),
  gny-2010 (1 → 9), gny-2003 (1 → 8), gny-2007 (1 → 8, with letters), mausa-2003 (1 → 6).
- Sets completed to their count: cerc-2003, cerc-2000, cerc-2007, ctuo-2008, mcpc-2011, pacnw-2013,
  rmc-2011, nordic-2005, ncna-2014; taiwan-2003 (3 → 8) and shanghai-2011 (8 → 10) have no count.

SGU is registered as a judge (the acm.sgu.ru archive on Codeforces). Names taken from closed judges
(FZU, HIT, CSU, HRBUST), from HUST's re-host and from KRSU carry no link. New sets get no count.
Held back: Bailian's "Ural Collegiate Programming Contest" 1998-2000 groups (8, 8 and 7 problems) —
not clear that these are the Eastern Subregional (urals-1998/1999/2000).

After this, 877 of 2,527 contests that have run still have no problem list (95 from the 2000s, 326
from the 2010s, 329 from the 2020s), and 113 more have fewer names than their count. 203 of the 877
already have a problem-set source recorded that has not been read for names.

## Caveats

- Matching is by title, so a problem whose title was changed on the judge is missed, and two
  different problems with the same title inside one matched run would be confused. Runs had to
  cover at least 60% of a set (4 problems minimum).
- VNOJ answers a Cloudflare human check, so its addresses were built from vjudge's problem codes
  and not opened.
- vjudge's lists are capped at 400 rows per query; the sweep is by source keyword, not a full read.

## Logos

Tables show a judge's logo instead of its name (name on hover; a closed judge greyed). Logos are the
judges' own favicons in `tools/site_assets/judges/`; Kattis is the cat from the open.kattis.com header.
QOJ, Bailian (same icon as POJ), LibreOJ and VNOJ have no usable logo and show a short text badge.

## Third round (same day): SPOJ, Eolymp, DMOJ, GitHub

- **SPOJ** registered as a judge: 325 links in 47 sets, from the 6,289 classical problems vjudge lists
  (resource string names the contest). **Eolymp**: 264 links in 43 sets (it had contest pages only).
  **DMOJ** re-read through its API (5,275 problems, 143 in its ICPC group): 21 more single links,
  nothing new by contest.
- New lists from source strings (`tools/add_problem_lists_2026_11_14b.py`, 57 problems): poland-1998,
  poland-2001 (4 names), palestine-2012, ukraine-2012, ukraine-2013, mongolia-national-2013 (4 names);
  thailand-2011, latam-2008, latam-2012 and ncna-2013 completed.
- **tap-2014** (11 problems) from a statement PDF in a GitHub repo of solutions.
- SPOJ's national sub-sites: br.spoj.com and pl.spoj.com answer a human check to curl and to the
  browser. Wayback has br.spoj's category lists, but Brazil has no gaps left; pl.spoj has no AMPPZ
  category. Jisuanke's problem addresses no longer resolve, so its 11 Urumqi 2017 matches are not linked.
- Not applied: SPOJ's "10th" and "11th Egyptian Collegiate Programming Contest" (9 and 5 problems;
  which years?), "XX Colombian National Programming ACM 2006" (7; no colombia-maraton-2006 in the
  catalogue), Eolymp's Malaysia national 2011 and 2013 lists (titles differ from what we hold).
- GitHub repository search (40 queries by contest name) found solution repos, not jury packages.
  Leads kept in `_hunt/judges-2026-11-14/gh-search.json`.
- Lead: the cover of the 2024 Maratona first-phase problem set names four contests sitting it —
  Brazil's sub-regional, the Competencia Boliviana de Programación, Gran Premio de Centroamérica and
  Gran Premio de México. bolivia-national-2024 currently holds the list of a Codeforces gym called
  "Bolivia Pre-National Contest", which is probably a different contest.
