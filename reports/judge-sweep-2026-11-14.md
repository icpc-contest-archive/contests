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
- **Problem lists the catalogue lacks** (new problems, not links):
  - SGU (acm.sgu.ru on Codeforces): NEERC Southern Subregional 2002 (9), 2003 (9), 2004 (11);
    Northern Subregional 2002 (9). south-russia-2002/2003/2004 have no problem set today.
  - KRSU: Kyrgyzstan Subregional 2005 (8, Russian titles); kyrgyzstan-2005 has no problem set.
  - beecrowd: 24 Maratona / South America stragglers outside the matched runs.
- **Needs matching by letter, not title**: LibreOJ World Finals 2018–2025 (97, Chinese titles);
  Luogu Nanjing 2022–2024, Jinan 2023 and World Finals 2022/2023 (Chinese titles).
- **Not catalogue contests**: VNOJ provincial rounds (north/central/south, 2021–2024), TLX IDEAFUSE
  Sumatra rounds, HihoCoder Beijing online rounds, AtCoder JAG practice, Toph and HackerRank local contests.
- **Nothing ICPC found**: CSES, DMOJ*, SCU, 51Nod, CSAcademy, Yukicoder, Yosupo, NowCoder*, LightOJ,
  EIJudge, Szkopuł, UVA, Z_trening, ACMP, USACO, OpenJ_NOI, OpenJ_POJ, CodeChef*, OJUZ, Daimayuan,
  Minieye, UniversalOJ, Kilonova, CSG, ACdream, NBUT, TopCoder. (* vjudge carries no source for these;
  the judge itself was hunted directly on 2026-11-03.) UVA has no source field on vjudge either, so
  the sweep says nothing about it.

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
