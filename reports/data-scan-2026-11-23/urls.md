# Data scan 2026-11-23 — area `urls`: hygiene of source addresses

Scope: every `sources:` entry of the 195 series files (2,589 contests, 12,348 sources) at the worktree commit
of 2026-11-23. Output: `ops.json` (110 operations, all `ok` under `apply_scan_ops.py --check`), `data.json`
(every list behind the numbers), this report. Scripts are in `work/` (rerunnable, read-only on the worktree).

## How it was checked (to rerun)

| Check | How | Script |
|---|---|---|
| Dump | every source with its contest's id, year, season, date | `work/dump.py` -> `work/sources.json` |
| Same address twice in a contest | `norm_key` plus: `index/default/home.(html,htm,php,asp,aspx,shtml,jsp)` dropped, default port, sorted query, tracking params (`utm_*`, `fbclid`, `gclid`, ...) dropped | `work/dups.py` |
| Wayback/other wrappers in `url` | `resources.is_wrapper` + any archive.org/archive.today/webcache host | inline |
| `as_of` | format (4-14 digits), real date, future, before 1996; before the contest date on a results/problems source; > 1 year before the contest; after the next edition on an address with no year in it | `work/timesus.py` |
| Vocabularies | roles vs `catalogue.ROLES`, `contains` vs `CONTAINS`, `url_state` vs the five verdicts of `apply_url_states.py`, `judge` vs `judges.yaml`, `problem:` letter, `scope` values | inline -> `work/fields.json` |
| `archived` paths | existence under `archive/`, manifest URL vs source URL (`norm_key`), path under another contest's folder | inline |
| Year in the address | 4-digit years (judge ids excluded) not in {id year, season, date year}; addresses whose only year is the season-end year (non-CMS); 2-digit years next to a contest word (`/00cerc/`, `rmc24`) | `work/years.py`, `years2.py`, `years3.py` |
| Same address, several seasons | group by `norm_key`; time of a citation = `as_of`, else the Wayback time of its own copy; clash = two seasons at one time | `work/cross.py` |
| CMS standings addresses | slug vs `data/cms-shortnames.json` for the contest's `cms_ids` | inline -> `work/cms_slug_mismatch.json` |
| Notes vs data | dead/live words vs `url_state`; a second `as_of` in a note; "shows/is the YYYY" | inline |
| Evidence | held copies read from `archive/`; Wayback CDX + `id_` snapshots fetched from the device (about 1 request / 2 s, cached in `work/cache/`) | `work/wb.py`, `work/resolve.py`, `work/peek.py` |

The ops are built by `work/build_ops.py` from `work/decisions.py` (every decision with its evidence string).
They were applied to a scratch copy (`work/sim/`) and `tools/validate.py` run there: 0 errors (as before),
4 new warnings, all "a description is filed for <old address>" (item 9).

## Clean results (no action)

- No Wayback/other wrapper URLs in `url` (the 7 archive.org hits are Internet Archive items, not wrappers).
- `as_of`: 6,442 x 14 digits, 2 x 8 digits (alberta-2005, scusa-2022); none malformed, in the future or before 1996.
- Roles, `contains` values, `url_state` (live/changed/replaced/dead/unknown), `judge` ids: all within vocabulary;
  no `contains`/`judge` on non-problem sources.
- `archived`: all 8,827 paths exist; 1 manifest URL differs from its source (rmc-2022 CMS copy filed under the
  2022 slug); 19 paths sit under another contest's folder (left by moves; harmless, but see item 1).

## What the ops fix (110 ops: 49 set, 47 remove, 8 unset, 6 append)

**A. Same address spelled twice in one contest (3 merges, 6 ops).** 5 groups found (validate.py catches only
`norm_key` twins, not `index.html`). Merged: cerc-2000 (`.../00cerc/solved/` + `:80/.../index.html`),
scusa-2001 (`https://.../problems/` + `http://.../problems/index.html`), ncna-2000 (`/acmregn/` +
`/acmregn/index.html`; its `as_of` 2009 showed the NCNA 2009 site, re-pinned to 20001022201555,
"Saturday, November 11, 2000"). Kept: bapc-2016 and swerc-1995 (two different `as_of`; item 8).

**B. Content-check moves/removals undone by `tools/enrich_from_archive.py` (33 removes + 15 archived unions).**
32 sources the content check of 2026-11-15 moved (21) or removed (11) at high confidence are back in the
original contest, each with note `from archived capture (...)`: enrich re-adds a source to whatever contest
folder a capture sits in. I re-read every held copy; all agree with the content check (harbin-2009 holds the
2010 Harbin and 2010 Tianjin ranklists, pacnw-1999 the "1998 Pacific Northwest" standings, ecna-2010 "The 2011
ACM ECNA", rmc-2025 the `rmc24` board, ...). Removed again; their capture pointers are added to the destination
source. Also removed `codeforces.com/gym/105020/my` from tunisia-2022 (a user's "My submissions" page; the
gym's `/standings` is already a source). This will happen again: item 1.

**C. `as_of` that cannot show this edition (31 re-pins, 8 drops).** Each new value is a snapshot I opened:
- wf-2004 -> 20040418003402 ("2004 ... Prague ... March 31, 2004"); wf-2001, wf-2003 -> dropped (every
  snapshot in their window is the 2002 Finals page; wf-2002 keeps it).
- korea-2001/2002 `standing.html`, korea-2002/2003 `problem.html`; nena-2003 `results.html`/`problems.html`;
  south-africa-2001 `Standings.html` and -2002 `Problems.html` (the two had each other's snapshot); cerc-2003
  `problems.html` (Dec 2003 still links `problems2002.tgz`, Feb 2004 links `cepc-2003.tgz`); seerc-2003
  results/problems; neerc-2003; neerc-2005/2006 (pinned to a 2013 snapshot = NEERC 2011); pacnw-2001;
  chengdu-2007 (pinned copy read "under construction"); aec-2018, xian-2014, xian-2017 (`acm.nwpu.edu.cn`
  pinned to the 2019 Xi'an Invitational page); gwalior-kanpur-2009; ncna-2010.
- `acm.ro/results.htm`: 16 SEERC editions 2005-2024 were all pinned to 20250312194116 = "2024-2025 SEERC:
  Standings" (right for seerc-2024 only). Re-pinned 11 (2005, 2006, 2008, 2010, 2014, 2016, 2017, 2018, 2020,
  2022, 2023), dropped seerc-2009 (no snapshot 2009-10..2010-08); 2012, 2015, 2021 left (item 4).
- Dropped as lost: taiwan-2009 (only snapshot "Coming Soon"), south-russia-2024 (pinned copy is the 2025
  contest), caribbean-2010 (pinned copy is the 2011 edition), romania-2015 (pinned copy predates it),
  germany-2026 (pinned copy is April's empty results page; the live address has the final results).
- 35 of these sources hold copies of another time and need a capture at the new time:
  `data.json` -> `recapture_after_as_of_changes`.

**D. Another edition's document, moved (14 ops).** awc-2022 `wc.indiaicpc.in/result.pdf` -> awc-2021 (PDF made
2022-12-30, before awc-2022; same top three as the held AWC 2021 board). nwerc-2011 `www.nwerc.eu/score/` ->
nwerc-2010 ("NWERC 2010 contest final standings"). south-america-north-2012 icpcarchive "2012 Latin American"
`problems.pdf` -> south-america-north-2013 (held copy: "2013 Latin American Regional ... November 8th-9th,
2013"). urals-2024/-2025 `qf/<year>/nwrrc-2023-tutorial.pdf` -> north-russia-2023 (both files are the NWRRC
2023 tutorial, "November 5, 2023"). mausa-2006 + mausa-2009 `midatl.radford.edu/docs/scoreboard/` @2016 ->
mausa-2012 ("The 2012 Mid-Atlantic USA Regional"). Removed where the right edition already cites it:
ukiepc-2016 `ukiepc.info/2015/` (the UKIEPC 2015 page) and cerc-2000 `.../20cerc/rank.html` ("CERC 2020 Final
Standings"; the content check had moved it there from cerc-2019 on the evidence of a crawl of `/00cerc/`).

**E. CMS standings addresses with the wrong slug (4 ops).** central-russia-2023 cited `Central-Regional-2026`
(= central-russia-2025) though its copy is rendered from cms 7732 -> `Central-Regional-2024`; wuhan-2025
`ICPC-Asia-Wuhan-2026` (no such slug) -> `Wuhan-2026`. kharagpur-2020 and gwalior-pune-2021 cited the previous
edition's page while their own CMS standings are empty (`icpc_standings_topup.json`,
`data/icpc-standings-empty.json`) -> removed (an empty CMS page is not a source).

## Items for discussion with Fredrik

**1. `enrich_from_archive.py` undoes moves and removals.** Question: how should a capture filed under contest X
stop re-creating a source in X once the source has moved or gone? Implies: the 32 cases in B were undone once
already, and every remove/move in this scan whose capture lives in the old folder (B, D, tunisia) comes back at
the next enrich run. Options: (a) enrich skips any capture path already referenced by a source anywhere in the
catalogue, plus the archive's `content_caveat` for removed ones; (b) a `belongs_to` field in the manifest;
(c) stop running enrich. For (a): one small change, no archive edits except marking 12 removed sources'
captures (`data.json` -> `archive_side_marks_for_removed_sources`). For (b): explicit, but edits manifests of an
archive that is never edited. Examples: harbin-2009, pacnw-1999, awc-2022. Recommendation: (a), done before
the next enrich run (ideally before these ops are applied).

**2. Series sites cited as `web` of many editions with no `as_of` (125 addresses, about 600 citations).**
E.g. `icpcbolivia.org` (11 editions), `nerc.itmo.ru` (12), `acmicpc-pacnw.org/results.htm` (20),
`cs.rit.edu/~icpc` (12), Facebook pages. Under "a source is an address at a time" each is one source showing
today's page. Question: pin each edition to a Wayback snapshot of its season, or accept an undated series site
as `web` of every edition? Pinning is the ruling-16 machinery (mechanical where Wayback has the season, "lost"
otherwise); accepting keeps links to today's page, which the 2026-11-14 criteria say is not `web` "about that
edition". Social-media pages are not `web` by those criteria either. Recommendation: run the pin pass on these;
retier or drop the social posts. 33 more addresses are genuinely multi-edition pages (history pages,
`neerc.ifmo.ru/subregions/*.html`, judge lists): fine, some lack `scope`.

**3. The content check's 328 pending `year-reused` items.** This scan resolved 39 of them by hand with the same
window rule (200 days before the contest to 60 days before the next edition). Recommendation: run
`tools/wayback_history.py --name run-2026-11-15`, then `--decide`, for the other 289; my results can check its
decisions.

**4. Unresolved shared-time results (8 groups) and three SEERC years.** `socalcontest.org/current/index.shtml`
@20071106 for socal-1998..2006 (7 editions; the page shows the 2007 contest); `cs.smsu.edu/~mcpc` @1999 for
mcpc-2001..2003; `cs.smsu.edu/~rcjudge` @2001 for mcpc-2001/2002; `icpc.cs.bme.hu/main.php?p=2|12` for
cerc-2004..2006; `bombonera.org/board` (caribbean-2015/2016, central-america-2015; domain now parked);
`amrita.edu/icpc` (4 editions; copies show "ICPC 2021"); `icpc.nwpu.edu.cn` @20200204 for xian-2022/2023 and
aec-2024, aec-2020/2021 undated: every copy is the app shell "页面加载中" (yemian jiazai zhong, "page loading");
seerc-2012/2015/2021 (the snapshots in the window are a 2011 summary, a 395-byte stub and a frameset).
Recommendation: fold into item 3; for the app hosts, drop `standings` from the roles (the shell never shows
results).

**5. CMS addresses built from `abbr` + `year`.** Three contests got another edition's slug that way
(kharagpur-2020, gwalior-pune-2021, kanpur-2022), and `data/icpc-standings-empty.json` stores those wrong
addresses. kanpur-2022 (cms 5647, empty) cites `ICPC-Mathura-2023`, the page of mathura-2022 (cms 5649, "The
2022 ICPC Asia Mathura Kanpur Regional", same date 2023-04-09). Question: are kanpur-2022 and mathura-2022 one
contest? Recommendation: build CMS addresses only from `data/cms-shortnames.json`; give the kanpur/mathura pair
to the structure agent; left as is here.

**6. Qualifier rounds filed as the regional's results, no `scope`.** amritapuri-2016 `results2016V1.pdf`
(online round), beijing-2007 `Result_CN.aspx` (网络预选赛 wangluo yuxuansai, "online preliminary"),
beijing-2016 `schoolrank.txt` (online-round school ranking), japan-2008/2010 domestic-contest results,
tehran-2025 `iipc/P25.pdf` (the online qualifier's problems, before the regional). Options: `scope: online
preliminary` (a page covering several rounds is a source of each, with scope) or remove. Recommendation: scope.

**7. A second time hidden in notes (138 sources).** Notes like "as_of 20060901130612 for rankings" are leftovers
of role merges; under the address-at-a-time model a second time is a second source when the content differs.
Sampled ones are the same document at two snapshots. Recommendation: leave; split only where the edition differs.

**8. Two entries of one address with different `as_of`, kept.** bapc-2016 `2016.bapc.eu/en/results/` (2017) and
`.../results/index.html` (2023): the same static page; swerc-1995 ETH archive dir (web, 2003) and
dir/index.html (problemset, 1998). Recommendation: merge bapc-2016 (one document); keep swerc-1995.

**9. Description files keyed by addresses changed here.** After applying, update `url` in
`data/source-descriptions/` for central-russia-2023, wuhan-2025 (new slugs) and the merged cerc-2000 and
scusa-2001 entries (`data.json` -> `description_files_to_update`); validate.py warns until then.

**10. Unverifiable or doubtful, left as is.** east-siberia-2002 `neerc.ifmo.ru/Subregions/east-siberian.html`
@20020124: a results table with no year, taken 9 months before the 2002 contest (so 2001's): move to
east-siberia-2001 or drop the `as_of`? amritapuri-2012 editorial of the "2011 Online Contest" (live 403, no
Wayback); malaysia-national-2018 two PDFs named after the Kuala Lumpur 2014 regional (404, no Wayback);
mcpc-1993/1994 `catsofwywop.com/.../mcpc/2000/browse.html` (empty reply); ethiopia-2019/2022 a LinkedIn post
tagged `#icpc2022`. Malformed: aec-2024 `http://http:/icpc.nwpu.edu.cn` (with `as_of` 2020), amritapuri-2025 raw
spaces, poland-2023 `?fbclid=...`. URL rewrites of sources that hold captures wait for item 1 (enrich would
re-add the old spelling).

**11. `contains` missing on 1,248 problem sources.** 716 are on judges (qoj 360, baekjoon 150, kattis 78, ...),
532 are not (521 without a copy). 1,218 other judge sources carry `[statement]`. Recommendation: fill judge
sources mechanically by judge, leave the rest to the next content check. Also 11 `problem` sources lack
`problem:` (`data.json` -> `field_checks`).

## Not checked / limits

Wayback was used only for the ~70 sources above; the 351 "pinned after the next edition" cases are listed in
`data.json`, not resolved (most are pages that kept old content and were confirmed by the content check).
About 10 live pages fetched. Nothing was written outside `findings/urls/`.
