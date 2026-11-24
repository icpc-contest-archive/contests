# Site consistency scan, 2026-11-24

Fredrik asked: scan all generated pages and make sure every reference to texts, counts and the like
is consistent and uses the same definitions. Eight agents each scanned one area of the 82,262 built pages:

- per-contest facts;
- totals and percentages;
- sources;
- problems and online judges;
- vocabulary;
- definitions and legends;
- seasons, series and locations;
- the standing rulings.

Each agent recomputed the numbers from the catalogue with the generator's own definitions.
A ninth agent reran their scanners on the rebuilt site.

Branch `site-consistency` holds the fixes; main is already merged into it. The rebuilt site has:

- 0 broken internal links (82,336 pages);
- 0 counted numbers that differ from the list they open;
- 0 validator errors.

The verifier checked 100 `fix` items: 94 are fixed, and the 6 others are covered below (3 finished, 2 are data questions, 1 is question 1).

Per-area reports, scanners and lists: `_qa-2026-11-24/findings/<area>/` (not in the repo).

## What was fixed

**One definition per thing**
- "Lost" had two definitions: the chip and filter counted bad copies as lost. Now one definition everywhere.
- On 876 problem-set pages a problem's held marks said "not held" while the set's own card said held. Problem, set and contest pages now agree.
- The marks key explained a grey mark that is never drawn, on about 2,850 pages.
- Grey for "does not apply" and white for "none held" were one look; they now differ.
- Hover texts said "held" for metadata; metadata now says "recorded".
- About and coverage now include the online-judge statement ruling (2026-11-22/23).

**Counts**
- The front-page "contests" tile now counts what its list holds.
- The region and season numbers on the front page are links that include only contests that ran.
- Series, season and location tables count the same way, as "ran +upcoming", and the numbers are links. Location tables used to count upcoming contests.
- Halves round up. 100% only when all, 0% only when none.
- Problem sets: "complete for 1,818 sets" is now the real 1,734, and each count is linked.
- About said 2 shared sets; there are 73.
- The CMS ledger lost 24 contests that share a CMS id with another contest.
- The listed number was shown as the problem count; it now reads "13 listed".
- Plurals are fixed ("1 contests", "1 days", "1 editions").
- Thousands separators are used everywhere, including the filter counts in the browser.

**Rulings**
- Check remarks are no longer shown (282 pages).
- Stamps of our own passes are no longer shown (693 pages).
- The Evidence section is dropped. Where a fact came from stays in the data (ruling 2026-11-16).
- `catalogue.json` and `problems.json` no longer publish notes, provenance or online judges' "offers".
- Administrative site labels are hidden.
- Repo paths and build hints are no longer shown in tooltips.
- The dropped "Every ICPC contest from which…" sentence is gone from the front page.
- Per-problem sources now name and link their problem: 2,729 rows, plus 1,435 sources that had no problem.

**Words**
- "Online judge", never bare "judge".
- Our copies are "our copy", not captures, the archived website or Raw.
- "Problem archive" for the ICPC Problem Archive; "the archive" alone is our archive.
- "Location" in place of "held at", "UUID", "type", "packages", "autumn" and "towards".
- The problem list uses the same words on set pages as everywhere else.
- A separator "·" between contests, so that "/" only separates divisions.

**Structure**
- Places inferred from the CMS are marked "inferred" in every table, tree and location page (329 contests).
- A contest with several parents shows "also advances to …" in the season tree. naq-2012…2019 were shown under ecna only.
- The numbers strip is in the same place on every group page.
- Seasons are written "2017–2018" in the strips.
- "›" appears only in breadcrumbs.
- Season, calendar and busiest-day dates link to their day.
- Contest tables use one column order.
- The calendar h1 is "Calendar 2024".
- cms.html lists the exclusion reasons the data actually has, and includes the non-mainline registry.

**Sources**
- A source has one address state wherever it is shown. Before, 11 sources were live on a contest page and dead on their own page.
- A contest page lists an address once (23 duplicate "not listed yet" rows removed).
- A shared set's card shows its contests' common letters.
- "Not listed yet" rows carry their time and say "website", not "web-mirror".

**Data**
- Springfield MA and Springfield IL are now cities of their own. Western New England College and UIS were under Springfield, Missouri, so 14 NENA contests and the MCPC Springfield ones showed in Missouri.
- `cms-triage.yaml`: a triage note pasted into eight CMS names is split out.
- DEFINITIONS.md is updated for: the problem holdings, the group numbers strip, provenance not being shown, and the source page.

## Questions for Fredrik

1. **Website "held" on 400 contests whose own Website section says not held.**
   - What is wrong: main's change this morning ("A website copy is shown only on the address it is a copy of") stopped crediting a contest's crawl to its cited website when the crawl started at another address. Coverage still counts that crawl, so the card, the W marks and "with the website" (1,736) say held while every website row says not captured. Example: `contest/acpc-2004.html`.
   - Why the crawls exist: 354 of the 400 crawls are of the same site, mostly the edition's own page: the crawl is `acm.kuniv.edu/2005/`, the cited address is `acm.kuniv.edu`, and alberta-2012 is the same. The other 46 are crawls of another host.
   - Options:
     - (a) Add each crawl's first address as a `web` source of its contest. It is then shown and counted as held.
     - (b) Count the website as held only when a cited web source holds a copy. "With the website" drops by about 400.
   - **Recommend (a)** for the 354, plus a look at the 46.
2. **Baekjoon is marked closed (2026-04-28), but it answers normally today.**
   - acmicpc.net/problem/1000 shows a working submit link, and our November checks found 1,597 of its 1,600 sources live. The site greys its logo and sends 5,371 problem links to the Wayback Machine.
   - Options: (a) it is back, so set `status: active`; (b) it is read-only, so reword "closed" and link live.
   - **Recommend (a)** after a look.
3. **"None" means two opposite things.**
   - For problems and results it is the white "none held" (wanted). For the CMS id and the website it is the grey "none exists" (not missing). Both sit side by side on one contest card.
   - **Recommend** renaming the white answer "not held", so that "none" always means none exists. This changes filter tokens such as `statements=none`.
4. **"Missing" means two things.**
   - It means the white answer only, and also anything short of the best answer, as in "779 missing" in the tiles.
   - **Recommend** "wanted" for the second meaning.
5. **The website answers have four vocabularies, and "link only" has six phrasings.**
   - **Recommend** held · no copy · no address · none everywhere (with question 3), and "link only" with one hover text.
6. **"None exists" in percentages.**
   - CMS id shows 87% while only 4 contests are missing one; 329 have none to have.
   - **Recommend** leaving "none exists" out of the denominator (99%).
7. **"Results 59%" is the scoreboard share,** next to "any result 94%". **Recommend** labelling it "scoreboard".
8. **Two sets of bars for group tables.**
   - The series, season and location lists show 5 bars; coverage.html's region and series tables show 9. DEFINITIONS says "the same bars".
   - **Recommend** one set.
9. **"St" is both standings and statements,** in one row. **Recommend** another letter for one of them, for example "Sd" for standings.
10. **How a source's time is written.**
    - The source page says "url (at T)"; lists say "url (T)". The website column shows the host only, with no time.
    - **Recommend** "(at T)" everywhere, and the time in the website column's hover text.
11. **"Lost" scope and colour.**
    - The "N lost" and "only here" chips count result and website sources only, so 11 contests have a red lost problem-set or editorial row and no chip. **Recommend** counting every type on the contest page.
    - Marks that link a lost source are a blue outline ("link only"). **Recommend** red, per the colour ruling.
12. **The remaining "not listed yet" rows** (19 rows, 9 contests).
    - They are copies we hold whose address no contest cites. On romania-2020, turkey-2021 and turkey-2023 they sit under "results: none".
    - **Recommend** dropping them, or adding them as sources.
13. **Online sites and location pages.**
    - In 64 contests, 401 places are named as online sites but don't count on their location pages.
    - **Recommend** counting them, marked "online".
14. **Short place forms drop the state** ("Springfield, United States"). That hid the Springfield error. **Recommend** "Springfield, MO, United States" for the US, Canada and Australia.
15. **CMS groups shown as "not placed" sites.**
    - About 88 labels: "Africa and Arabia", "Alumni (non-advancing teams)", rooms named Dijkstra and Knuth, two people's names (rmc-2021), and guest groups at caribbean-2012…2015, socal-2021…2023 and australia-2013.
    - **Recommend** typing them `administrative` or `online` in the data.
16. **Problem sets and problems list none of their sources.**
    - A held judge copy is reachable only from the contest page. Judge logos link straight to the judge even when that address is a held source.
    - **Recommend** a Sources section on set and problem pages, and the logo opening the source page when there is one.
17. **non-mainline.html.**
    - 64 links go straight to addresses.
    - The reason reads "outside-hierarchy (parent recorded as n/a)".
    - Registry contests appear on the Kattis and QOJ judge pages with placeholder marks.
    - **Recommend** unlinked addresses and plain wording, and leaving registry contests off judge pages.
18. **Check dates.** "(checked 2026-10-21)" on 16,168 source pages and an "address checked" column on the source lists. Is this the hidden "Checks" data? **Recommend** keeping the date in the hover text only.
19. **Contribute links to the private contests repo's issues.** **Recommend** removing the link until `icpc-contest-archive/reviews` exists.
20. **Lower priority:**
    - Location years use the year in the contest id (eg-luxor says 2020–2023; its contests ran 2021–2024).
    - The season "locations" tile counts upcoming contests.
    - Online judge contest counts include non-mainline contests (Kattis 345, of them 21 non-mainline).
    - 432 source pages are built for addresses no contest cites.
    - The calendar and wanted heat maps are green and amber for counts.
    - The panel and the matrix order the groups differently.
    - The source page's row headers are capitalised.
    - The column header reads "archive repo".
    - The contest list's location filter is labelled "country".
    - One source covers several seasons when no time is known (taiwan-ncpc).
    - Three fills for one answer.
    - The `coverage.py` command line counts "held" differently from the site.
    - The "automated reader" line on source descriptions stays (we read it as a disclaimer, not provenance).

## Data found along the way

- **No repo:** 193 sets the problem archive holds have no `repo`, so there is nothing to link (bapc-2012…2014, alberta-2016, …).
- **Letters and counts:** 84 contests whose scoreboard we hold have no problem count, and about 215 have a count but no letters. This needs a round of `tools/letters_from_scoreboards.py`.
- **Problem letters:** 1,509 `problem` sources have no letter; 496 match a problem's judge link exactly and can be filled mechanically.
- **Logos:** QOJ, VNOJ, LOJ and SGU have no logo (11,958 table cells show their short name).
- **Source types:**
  - Eight judge list pages are typed `problem`: Baekjoon categories of dhaka-1998, ecna-1998, kanpur-2000, mausa-2001, seerc-2001, wf-2002 and wf-2010, and nordic-2008's second Kattis page.
  - Some of them carry a single-problem scope ("B Ski Slopes only"), so `problem` with a letter may be meant.
- **Live Archive:** 204 links have no snapshot, so they open the Wayback calendar.
- **aec-2024:** its first source is `http://http:/icpc.nwpu.edu.cn`, as website and standings, with a 2020 snapshot. That is probably not this contest's source at all, not just a typo.
- **Stale list:** scusa-2026 and seusa-2026 are listed in `data/icpc-standings-empty.json`, but their standings had 66 ranked rows on 2026-11-23.
- **Chinese without a translation:**
  - shenyang-2025's problems 碰撞伤害 (*pèngzhuàng shānghài*, "collision damage") and 狮子座 (*shīzizuò*, "Leo").
  - hefei-2022's online site 卢建良 (*Lú Jiànliáng*, a person's name).
- **Letters:** 8 contests show another contest's letters (Latin America 2014 sites, central-america-2006, ukiepc-2013, south-na-2025/2026). Their own letter maps could be recorded.
- **Locations:**
  - Location `gt-guatemala-city-url` is named "URL".
  - The location string "Africa and Arab" is shown as a place.
- **Spelling:** source descriptions mix American and British spellings (organized 26 / organised 72, labeled 2 / labelled 1,008).
