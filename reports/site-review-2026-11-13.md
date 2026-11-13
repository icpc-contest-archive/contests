# Site review of 2026-11-13: eight random pages

Fredrik's comments on eight pages opened with *Random*, the general issue behind each, and what was
changed everywhere. Numbers are of 2026-11-13.

## 1. What a source is

**Before.** The source page was built around the *address*: a health chip for the address now, a link
to the Wayback *calendar*, then "snapshots" (the address at different times), "captures" and a
table of "checks". Whether we held a copy was a fourth thing, shown elsewhere. Lists showed only the
health chip.

**Now.** A source is one document a contest points at: an address *as the contest means it*. It can
be found in up to three places, shown as one unit, in this order, wherever a source is listed
(contest pages, judge pages, the source lists, mirrors):

| mark | place | values |
| --- | --- | --- |
| `live` | the address now | live · changed · blocked · empty · replaced · dead · could not tell · not checked |
| `WB` | the Wayback Machine | snapshot · empty snapshot · no snapshot · excluded · not checked |
| `ours` | our archive | held · empty copy · missing |

Green = there; amber = something is there but not the document; grey, struck = not there; dashed =
nobody has looked. *lost* = dead, no snapshot, no copy.

The source page says what the source is ("The website of japan-2000, as it was on 2007-11-05"),
then *Where to find it* — three rows, each with its status, what is known, and the link that opens
it. The Wayback link opens the snapshot that shows the document; the calendar is offered only when no
snapshot is known. Then *Copies in our archive*, and *Set aside* for files we fetched that are not
the document. The checks are no longer shown (they stay in `data/resources.json`).

**One address, several sources.** 9,551 of 10,327 addresses are cited by one contest. 440 are cited
by several (a results page reused every year: `socalcontest.org/current/index.shtml` by 32
contests). Such a page now has a row per contest — its time, its snapshot, its copy.

*"Used by"* said which contests cite the address and as what. It is now the first sentence of the page.

## 2. Things that were wrong in the data behind those pages

- **A crawl we hold was called junk** (`icpc.score.is.tsukuba.ac.jp`, 82 pages). The audit judged
  a site by its front page, and a frameset or a redirect has almost no text. It now follows frames
  and redirects into the crawl (`archive/tools/audit_not_there.py`, `entry_page`): 20 websites are
  held after all (japan-2000, cerc-2001..2003, swerc-2004/2005, mausa-2001, nwerc-1997, …).
- **An empty capture was called held** (the AOJ page). The audit had not been run since 2026-10-22;
  1,600 captures were newer. Re-run and applied: 194 more captures are set aside — app shells (AOJ,
  Google Drive viewers, bapc.eu), login walls, 80 generic pages served for unrelated contests.
  One address filed under several contests and identical PDFs are no longer taken for generic pages
  (the Timus problem list for five contests; the shared Latin America problem set).
- **"dead" that is not dead.** 133 addresses without a copy are recorded dead because the server
  turned our fetcher away: HTTP 401/403, or a certificate the fetcher does not trust
  (`ikit.sfu-kras.ru`, east-siberia-2001's standings). They show as *blocked* and never as *lost*.
  The verdict in the data is unchanged; the capture tool should learn the difference.

## 3. Why sources were "link only" (season 2001–2002)

At the start 3,073 of 10,327 addresses had no usable copy. The largest group was not waiting for
anything on the web:

- **ICPC standings: 1,342.** These are pages of the CMS — an app; a fetched page is an empty shell.
  The data behind them was on disk all along (`../icpc_all_standings.json`), but only the 286
  contests whose ICPC standings were their *only* result had been rendered from it.
  `tools/bake_icpc_standings.py` rendered the rest: **1,021** copies. `tools/topup_icpc_standings.py`
  asked the open API for the 357 CMS ids the dumps lacked: **32** more. The other **314** contests
  have no standings in the API at all: their page is empty (`data/icpc-standings-empty.json`). They
  show as *empty*, their `I` mark is grey, and a contest whose only result is such a page says
  *results: none*.

What is left without a copy, 2,027 addresses:

| why | addresses | what it takes |
| ---: | ---: | --- |
| never checked | 728 | a capture round — 634 are judge pages added 2026-11-12 |
| fetched, but empty or not the document | 305 | another way to fetch: a browser, or the site's API |
| ICPC standings page with nothing on it | 297 | a ruling: keep them marked empty, or drop them |
| gone; a Wayback snapshot is known | 205 | a capture round |
| gone; Wayback not checked | 151 | a capture round (132 judge pages) |
| the server refuses our fetcher | 133 | a browser, or a fetcher that trusts the certificate |
| at its address, never captured | 127 | a capture round |
| lost | 81 | someone who kept a copy |

The queues for the capture round are written: `archive/capture-queue-2026-11-13.json` (7,844
items; the tool skips what is held) and `archive/site-queue-2026-11-13.json`.

## 4. Other pages

- **Judge pages.** "offers" is gone (it was a flag on the judge, not a fact about a page), so are the
  judge's notes; the two counts read *contests* and *problems*. Same on the judge list.
- **Series, seasons, locations.** The tiles read *results · problem sets · websites*, each with its
  share of the contests that ran. "archived" is gone.
- **Season outliers.** The line now reads *outside these dates* and says why: the contest belongs to
  the season but ran well apart from the rest, and the season's dates are those of its main run
  (from the first cluster of three contests within 45 days to the World Finals). `ctuo-1996` ran in
  May 1996, five months before the season's regionals.
- **Hendrix College Div. 1.** 187 sites on 121 contests had a name and no location. A division
  label hid the name, or the name was an alias or an institution the tree lacked.
  `tools/place_sites_2026_11_13.py`: 75 placed (29 institutions and 18 cities added), 35 CMS
  groups marked administrative (`GGGGGG`, `zzz Site for future use`, `UPE`, registration groups),
  77 left — the tool lists them. Garden City (Nassau Community College) moved from New Jersey to
  New York.

## Open

1. The 314 empty ICPC standings pages: keep them as sources marked empty, or remove them?
2. 77 unplaced sites: about 30 are preliminary contests the CMS filed as sites (`Sichuan University
   Programming Contest` under chengdu-2005), 14 are regional groups (NAQ, NAC, World Finals), the
   rest are sites named after the contest. A `preliminary` site type would keep the first kind
   apart from bookkeeping groups.
3. Wrong state for a city, seen on mcpc pages and not fixed (a node's id starts with its city's,
   so moving one changes its address): University of Illinois Springfield hangs under Springfield,
   Missouri; Southeast Missouri State University under St. Louis. The tree picked one city per
   name; it needs a pass of its own.
4. Blocked addresses (133) and app pages (AOJ and others among the 305): they need a
   browser-driven capture, or the judge's API. Not built.
5. The capture round itself (run on the Mac).
