# sr-notdoc: third reading of the 323 second-reading items "not-the-document" (308) and "cannot-tell" (15)

Source: `data/describe/run1-2026-11-16/second-reading.json` (worktree). Every item has a log line in `data.json`
(`log`, field `cls`; `recapture` = the subset that needs a new capture, with the best snapshot or capture URL).
Helper files in `work/` (rows.json, cdx/, snap/ = Wayback CDX lists and fetched snapshots, build.py, final.py).

## How it was done (rerunnable)
1. For each item: pack copy path from `_describe/run1/<contest>/pack.json`, all captures from `archive/index.json`, text of the held copy.
2. Wayback CDX for the exact address (all 323), then up to 4 snapshots each (nearest after the contest date, one before, one mid) fetched with `id_` and compared with the held copy (title, visible text length, contest year).
3. Live checks from the device shell (GitHub raw, PDFs, Drive, Kattis, CATS, oocities, ...).
4. Rulings used: DEFINITIONS "a copy that is not the document is marked empty and captured again; when the address itself holds nothing, the source goes"; "not web: a CMS finder page".
5. Important finding about the input: most of these were read from a **live** capture although the source was already pinned (`as_of`) to a good Wayback snapshot (61 items). Where a Wayback capture at `as_of` exists, the second reading looked at the wrong copy.

## Counts (323)
| class | n | meaning |
|---|---|---|
| fix-as_of (op) | 4 | as_of points at the wrong snapshot; pinned to the right one |
| recapture-snapshot (op) | 1 | south-russia-2018, new as_of |
| remove (op) | 16 | CMS finder pages filed as `web` |
| recapture-pinned | 61 | already pinned to a good snapshot; capture of it pending or present; no change |
| recapture-raw | 14 | GitHub blob pages; raw PDF works (verified `%PDF-`, HTTP 206) |
| recapture-fullsize | 4 | PDFs cut at 1,048,576 bytes (2 Felix issues, pacnw-2024) and a Drive PDF |
| recapture-live | 3 | live page serves the document, our crawl missed it (poland-2003, torneo-chileno-2019, morocco-2023) |
| recapture-linked | 3 | gran-premio-mexico-2015/18/19: page fine, linked PDF/image not captured |
| recapture-frames | 3 | bare framesets (cerc-2001, neerc-2001, nwerc-2004) |
| recapture-app | 76 | document is built in the browser (Spotboard, CodeChef, NowCoder, Algotester, zibada, xcpcio, CATS, urfu...). Where a pinned Wayback capture exists it is a shell too |
| keep | 2 | caribbean-2014, central-america-2014: the Baekjoon category page is a real 14-slot problem list |
| review-kattis | 70 | Kattis problem-sources pages that say "No data found" |
| review-social / review-login | 11 / 12 | Facebook, LinkedIn, YouTube; eolymp, Codeforces gym, Scribd |
| review-bolivia | 10 | icpcbolivia.org parked |
| lost-or-review / review | 21 / 12 | see below and data.json |

## Ops (`ops.json`, 21, all `ok` in `--check`)
- 16 x `remove`: `icpc.global/regionals/finder/...` (and `icpc.baylor.edu/regionals/finder/Turkey-2011`) filed as `web`: bolivia-national-2015..2023 (9), gran-premio-mexico-2020/2023/2025, hungary-2015, oman-capital-2025/2026, turkey-2010. DEFINITIONS says a CMS finder page is not `web` and a shell/404 holds nothing. Wayback has at most the empty app shell.
- 4 x `set as_of` (old value guarded): amritapuri-2019 (shell -> 20201024063145), chengdu-2007 (pre-contest page -> 20071228191325, the results), ncna-2010 rankorder (2011 edition -> 20101110015354), ukraine-2011 standings (not-started page -> 20110702102132, standings of the 2011-05-21 contest, timer 708:46:34).
- 1 x `set as_of` new: south-russia-2018 codeforces blog 62570 -> 20181024063727 (live copy is the "Codeforces will return in few hours" notice).

## Items for discussion with Fredrik
1. **Kattis problem-sources pages with "No data found" (70).** Question: keep or remove? The names come from the Kattis export (note "export source ..."). Of 804 names in the public list none is among these 70; any unlisted name returns "No data found" (checked NCPC 2019, BAPC 2010...). Wayback has no capture of any of them. Keep: the problems may exist as hidden/unlisted on Kattis and Fredrik can read the export; Remove: the address serves nothing now, and per DEFINITIONS the source then goes. Recommendation: keep until Fredrik checks in the Kattis admin which of these names hold problems, then remove the rest (list in data.json, cls review-kattis; e.g. ecna-1993, swerc-1998 x3, mausa-2010 x8, bapc-2010).
2. **icpcbolivia.org (10 sources, bolivia-national-2015..2025).** The home page is a Gandi parking page at every Wayback capture (first sight 2024-08-10). So the address did not serve any edition as far as Wayback shows, but the host is not simply dead: Wayback holds `scores.icpcbolivia.org/2025/prenacional` (BOCA final scoreboard, 114 teams, A-J, 2025-06-29) and `prenacional.icpcbolivia.org/boca/src/admin/report/score.php?p=0`. Options: (a) remove the home page sources (address never shown to serve) and add the scoreboard to bolivia-national-2025 or its pre-national round; (b) keep as lost. I did not append: it is unclear whether the 114-team June board belongs to bolivia-national-2025 (218 teams, 2025-09-12). Recommendation: (a) after Fredrik says which contest the pre-national board belongs to.
3. **Pages built in the browser (76 recapture-app).** A plain Wayback or live capture is a shell (also the pinned Wayback copies). Question: do we capture rendered pages or the data behind them (Spotboard runs.json, CodeChef API, NowCoder, Algotester, xcpcio)? Implication: korea-2016..2025 (10), codechef (about 30), nowcoder (8), algotester ukraine/turkey (8), zibada.guru wf-2010..2017 (5), urfu urals (7). Recommendation: one browser/API capture lane for these, they are real documents, none should be removed.
4. **GitHub blob pages (14) and other file views.** The document is the PDF; `.../blob/...pdf` -> `.../raw/...pdf` verified for all 14 (capture_url in data.json). Recommendation: capture raw, keep the blob address as the source.
5. **Capture size limit.** erc-1984/1985 (Felix 34 MB / 39 MB) and pacnw-2024 PDF are cut at 1,048,576 bytes by our capture; the live Felix PDFs are complete (13 and 18 pages), the pacnw Wayback 2026-05 snapshot is a complete 28-page PDF. Recommendation: lift the limit for PDFs.
6. **Possible wrong-contest or non-source (not changed):** chennai-2015 ACM15CHN (page titled Kolkata); uzbekistan-2005 (`nerc.itmo.ru/archive/2005/northern/statements.rar`, a valid RAR with statements.ps, looks like the NEERC Northern Subregional); swerc-2006 `ICPCLogo...pdf` filed as editorial; socal-1994 UCLA research guide; dhaka-2001 BUET homepage (general homepage rule); palestine-2014/2018 personal staff page with a truncated URL; taiwan-ncpc-2015 (Taiwan MOE national contest index); ncna-1993 oocities generic archive. Recommendation: remove the logo PDF and the UCLA guide, retitle/move the others once Fredrik confirms.
7. **Address was probably the contest's site but nothing usable exists** (keep as lost, no op): ncna-2000/2003 (rankorder earliest capture Dec 2004), nwerc-2005 (KTH Standings.html, site root archived 2021 but not this file), socal-1990..1993, nena-atlantic-2008, nwerc-2002 chipcie, bapc-prelims-2021, dhaka-2014 (JS), manila-2002 dledge.com (parked in 2004), korea-2011/2012 phpBB ("not authorised" at every capture), west-neerc-1998..2002 acm.bsu.by (testing-system home page; first capture 2015), taiwan-2009 ("Coming Soon" in 2009-05), algeria-2024 acpc.global/event/alcpc2024 (live 404, no Wayback), seerc-2000 (known seerc domain item). Recommendation: keep, mark lost.
8. **Social media (11) and login walls (12).** Facebook pages show only the title; LinkedIn/Facebook captures are login pages; eolymp 3388/3423 (4 Latin America sources), Codeforces gym 105020 (standings behind captcha; `/my` is a personal submissions page that can never be the contest's document), Scribd acpc-2013. Recommendation: Facebook/LinkedIn/YouTube are not `web` (not own site) anyway: decide in the web-role review; gym `/my` should be removed.
9. **Frame sites:** cerc-2001..2003 (cepc.mimuw.edu.pl framesets; pins already right: CEPC 2002/2003 titles), neerc-2001, nwerc-2004: the documents are the frame pages (menu.html, pages/welcome.html); the capture needs to follow frames.

## Not done / blockers
- No op for the 61 pinned items (nothing to change in the catalogue; capture rounds will fetch the pinned snapshot).
- Wayback and the device shell were slow and rate limited; 2 CDX lookups (socal 243 archive.org item) not completed.
- bolivia scoreboard find (item 2) and the Kattis question are outside what I could settle without Fredrik.
