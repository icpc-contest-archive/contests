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

## Rulings of 2026-11-24 and what was done

Fredrik answered the questions above the same day: 1–11, 13, 14, 16, 19 and 20 agreed; 12 → (b); 17 → (a); 15 "these admin groups are not actually locations — we should not list them at all"; 18 "not even in the hover; keep the data, but avoid such notes on the site". The extra questions: aec-2024's source dropped ("obviously broken"); the 193 sets without `repo` left for now (some are held but not yet in the archive org); description spellings normalised; letters → (a).

- **1, websites held through a crawl.** Each crawl's own first address became a `web` source of its contest where the crawl is that contest's site or edition page: 220 contests (32 own pages, 186 NEERC subregionals whose crawl is the NEERC season page with a section for them, 2 alternatives). 182 crawls were skipped: a generic front page (43), already cited (37), a file (30), a NEERC season page with nothing for that subregional (29), another edition (16), another contest (13), a results or report page (11), empty (3). Website *held* is now a held copy of one of the contest's web sources, the same answer as its Website section: "with the website" went from 1,736 to 1,556. List: `findings/websites/report.md`.
- **2, Baekjoon** is `status: active`; an open judge's problem links go to the problem as it is now (the snapshot time stays in the data).
- **3–5, the words of the answers.** *None* only ever means there is none to have (grey). A hole is *not held* (material, results) or *missing* (metadata) (white). *Wanted* is everything short of the best answer, with its own filter value (`statements=wanted`). Website answers: held · no copy · no address · none. *Link only* is the one label for blue, with one hover text.
- **6–8.** A *none* answer is left out of a share (CMS id 99%). The results share is labelled *scoreboard*. Every group table carries the same ten bars.
- **9.** *Sd* is standings; *St* only statements.
- **10.** `url (at T)` everywhere; the website column's hover names the source with its time.
- **11.** *Lost* counts sources of every type; a mark for a lost source is outlined red.
- **12.** The 19 copies were triaged: turkey-2020…2023 got their inzva reports and turkey-2023 its algoleague leaderboard (a scoreboard, link only: our copies are an empty app shell); the rest were news items, other contests' pages or SEERC pages. Contest pages now list only the sources the catalogue cites.
- **13–14.** Location pages count a contest's online sites, marked *online*; places in the US, Canada and Australia read `Springfield, MO, United States`.
- **15.** 305 CMS group sites typed `administrative` (106 labels); 13 bare `{type: online}` markers keep naq-2015…2026 and vietnam-2021 "Online"; online rooms that are not places are never listed; the free-text location drops the contest's own group names, "unofficial" and "Africa and Arab"; five real venues that were typed administrative (gny-2008, nena-atlantic-2010/2011, nena-north-2011…2013) were untyped.
- **16.** Problem set and problem pages have a Sources section; a judge logo opens the source page when we hold a copy of that judge page.
- **17.** The 24 registry contests' 64 sources are in the resource graph and have source pages; non-mainline.html links them like any list of sources; online judge pages count catalogue contests, registry ones apart ("+21 non-mainline").
- **18–19.** No check dates on the site; no link to the private repo's issues (Contribute says review mode is being set up).
- **20.** Place years from dates; the season's places are a fact, not a tile; heat maps in grey; one reading order for the coverage groups (Results, Website, Contest metadata, Problem metadata, Problems); source page rows *address · Wayback · archive* with pill answers; "problem archive" column; the location filter labelled *location*; an address with no time whose checks disagree by season is a source per season; `coverage.py` says its numbers are not the site's.
- **Data.** 44 contests got their problem count and letters from held scoreboards (`reports/scoreboard-letters-2026-11-24.md`). The four 2014 Latin America sites and ukiepc-2013 got their own letter maps (their problem set booklets); south-na-2025/2026 got `divisions` maps from their own Kattis pages; a contest is never shown another contest's letters. shenyang-2025's two Chinese titles got the English names of the contest's own set ("Collision Damage", "Leo"), the Chinese kept as other titles. Eight judge list pages typed `problem` are now `problemset`. Source descriptions use British spelling in our own text (organise, emphasise, finalise, judgement, labelled, towards …; quotations unchanged; *color*, *center*, *favor* left alone because they are often titles or file names).

## Still open

1. **NEERC season pages as subregional websites** (186 contests): the crawl is `neerc.ifmo.ru/archive/<year>.html`, the NEERC page of that season, which has a section for the subregional. Added as their website; drop them if a season page should not count.
2. **Shared crawls** (26 contests cite the crawled address but the graph credits the crawl to one contest only). mcpc-2012 is clean (its `as_of` is the crawl's time) and would be fixed by crediting a shared crawl to every contest whose crawl it is; the other 25 are snapshots 4–28 years from the contest.
3. **80 contests have a crawl but no `web` source** (nzpc-2015…2023, wf-1977…1990, south-pacific-1991…1997, romania-2017…2023 …). The same step could give them their crawl's address after the same screening.
4. **central-america-2006** probably did not sit latam-2006: its own problem set (problems2006.pdf, "11th México and Central America ACM ICPC 2006") has six other problems. Give it its own set?
5. **Sibling letter maps that mix divisions** in south-na-2025/2026 (scusa, seusa, mausa read off whichever division's board was captured).
6. **Sites:** macau-2023's "not available" placeholders (Hong Kong in the CMS); vietnam-2022…2025 now read "not known" (host cities wanted); 62 real venues still unplaced (list in `findings/sites/report.md`) and three location nodes that are CMS groups (wf-2007, wf-2010).
7. **Checks on the Mac** for the registry sources and the new website sources (no live or Wayback answer yet) — the commands are in the reply.
