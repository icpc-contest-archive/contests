# results-eu-ne — missing results, Europe / Northern Eurasia / International (data scan 2026-11-23)

## What was checked, and how (rerunnable)

- **Targets**: every contest in a series whose header `region` is Europe, Northern Eurasia or International, without
  `status: upcoming`, with no source whose roles include scoreboard / frozen_scoreboard / standings / rankings / teams:
  **73 contests** (`work/scan_targets.py`, list in `work/targets.json`). 24 European (1983-2023), 49 Northern Eurasia
  (mostly NEERC subregionals 1998-2002, plus azerbaijan-2006/2007/2010).
- **Own holdings first**: indexed every page of every `website/*/site-manifest.json` crawl in the archive for the NEERC/NERC
  series and for the European series (`work/build_index.py` -> `work/idx_ne.json` 8,223 URLs, `work/idx_eu.json` 18,040 URLs),
  then searched the URLs for year + results words and read the pages (`work/txt.py` handles cp1251/KOI8-R). This found
  the old NEERC site's per-subregion result pages (`/Archive/2000|2001|2002/<subregion>.html`), the NEERC 1998 site's
  "Subregional Quarter Finals Results", the Ural championship result pages on sp.urfu.ru, the Far-Eastern results pages
  on imcs.dvgu.ru and the BAPC 2015 per-site preliminary scoreboards — all already held in other contests' crawls and never cited.
- **CMS**: `icpc_standings_topup.json` and the open API (`/api/contest/public/search/contest/<id>`) for every target CMS id:
  all empty (`[]`).
- **Live / Wayback**: device-shell curl; Wayback CDX over neerc.ifmo.ru (`/Archive/`, `/Subregions/`), acm.ngg.hu,
  people.inf.elte.hu/bzsr/acm/, uhunt vcontests, www.acm.inf.ethz.ch/PastContests.html. The Wayback Machine was slow and
  often timed out or refused (port 443 refused; plain http worked intermittently), and the session was cut twice.
- Every page behind an op was opened (held copy, live page or snapshot) and confirmed to be that edition's results.

## Counts

- **44 ops, all `ok` under `apply_scan_ops.py --check`**: 42 `append` (new results sources) + 2 `set` (one role fix).
- **29 of the 73 contests get a results source** (24 NEERC subregionals, turkey-2021, turkey-2023, hungary-2018,
  bapc-prelims-2015, bapc-prelims-2016). 44 remain; each has a line in `data.json` (`not_fixed`) with what was tried.

## What the ops fix (grouped)

1. **Old NEERC site, /Archive/<year>/<subregion>.html (2000, 2001, 2002)** — full grids per subregion, Wayback-only
   (`as_of` = snapshot): north-russia-2000/2001/2002, central-russia-2000/2001/2002, south-russia-2000/2001/2002,
   west-neerc-2000/2001, urals-2000/2001 (scoreboard: total + both rounds' grids), urals-2002 (standings, two-day totals),
   far-east-russia-2001, uzbekistan-2002 ("Middle-Asia Subregion", host Tashkent UIT), west-siberia-2000 (the page calls it
   "Siberian Subregion", host Novosibirsk STU — the later West-Siberian subregion).
2. **NEERC 1998 site, `http://neerc.ifmo.ru/Archive/98/results.htm` @20030516090449** — one page, two sections:
   north-russia-1998 (scope Northern Subregion, 24 Oct 1998, IFMO) and south-russia-1998 (scope Southern Subregion, Saratov 6-10 Oct 1998).
3. **Ural championships = Eastern subregional quarterfinals (sp.urfu.ru, live)** — urals-1998 (`/chu/1998/results.htm`),
   urals-1999 (`/chu/1999/results.html`), urals-2000 and urals-2001 (`/chu/<y>/final.html`, both rounds' grids),
   urals-2002 (`results.html` standings + `results1.html`/`results2.html` round grids with scope). Each index page says
   the championship "одновременно являлся четвертьфиналом ... сезона Y-Y+1" (was also the quarterfinal of season Y/Y+1),
   which matches the catalogue's id/season pattern (spring championship Y -> urals-Y -> neerc-Y).
4. **Far-Eastern results pages (imcs.dvgu.ru/acm/results<Y>.html, Wayback 2006)** — far-east-russia-1999, -2000, -2001, -2002
   (students section; the pages also carry the school championship).
5. **BAPC preliminaries** — bapc-prelims-2015: 7 per-site final scoreboards linked from 2015.bapc.eu/contest.html
   ("Preliminaries / Final Scoreboards": DKP, EAPC, LKP, UKP DOMjudge pages, Groningen PNG, UvA and VU AAPP PDFs; host now
   answers 403, so `as_of` = 2020 snapshots); bapc-prelims-2016: the existing `web` source
   `https://2016.bapc.eu/en/contest/preliminaries/` carries the final scoreboards of 7 of the 12 sites as images (viewed:
   "Scoreboard Delft Algorithm Programming Contest 2016, final standings", Utrecht grid A-K) -> roles `[web, scoreboard]`
   with a `scope`. Its first captures were filed under scoreboard/standings; a later round left it `web` only.
6. **hungary-2018** — ELTE post "ACM verseny országos forduló eredményei" (2018-11-13): solved-or-not grid, 29 teams from
   ELTE, BUTE, SZTE, Debrecen -> scoreboard.
7. **turkey-2021, turkey-2023** — inzva's Online Programming Contest leaderboards on algoleague (JS app; data verified
   through `api.algoleague.com/api/app/contests-score`), plus inzva's OPC 2021 report (report + rankings, top 3). See item A.

## Items for discussion with Fredrik

**A. Turkey 2021/2023 = inzva's OPC? (ops included, easy to drop)**
- Question: may the ICPC Turkey contest of 2021 (CMS 4910) and 2023 (CMS 7583), both empty CMS shells, be identified with
  inzva's Online Programming Contest for Universities on algoleague?
- For: turkey-2022 already cites OPC 2022 on algoleague; turkey-2019/2020 are inzva contests; OPC follows ICPC rules,
  teams of three from one Turkish university, and its 2021 rules threaten a ban "from the Turkish Programming Contest 2022".
- Against: no page says OPC was the ICPC qualifier; the live 2021 board disagrees with inzva's own report on 3rd place
  (report: unagi; board now: etliekmek 3rd, Unagi 5th), so the board may have changed after the contest.
- Links: https://algoleague.com/contest/online-programming-contest-2021-final-contest/leaderboard ,
  https://inzva.com/reports/2021/online-programming-contest-for-universities-2021-report ,
  https://algoleague.com/contest/online-programming-contest-2023/leaderboard
- Recommendation: keep the ops (consistent with turkey-2022); ask the Turkey site director to confirm once.

**B. JS-only results pages whose copies cannot hold the rows (hungary-2012 ... 2017)**
- Question: add the Hungarian contest's uHunt "virtual contest" pages as `scoreboard` sources although no copy holds the
  ranklist (the browser built it from the uHunt API, which now answers 502)?
- Implication: 6 contests would get a results source that will show as a bad/empty copy; the alternative is to leave them
  without results.
- For adding: they are the organisers' own results addresses, linked as "eredmény" (results) from
  people.inf.elte.hu/bzsr/acm/ and from ELTE's 2016 results post; the 2014/2015/2017 snapshots show the title
  ("Hungarian ACM 2017. - Contest"), the start time (= catalogue date), team names and the UVa problem numbers.
- Against: the rule "a page with no rows holds nothing and is not a source" (CMS empty pages) points the other way.
- Examples: http://acm.ngg.hu/v.html @20171011213229 (hungary-2017), http://people.inf.elte.hu/bzsr/acm/r2014.htm
  @20151028214929 (hungary-2014), http://uhunt.felix-halim.net/vcontest/96abdb9798d5213e0916d688a46bd6fe (hungary-2013).
- Recommendation: add them as `scoreboard` with a note (lost-content addresses, like ruling 16's "keep as lost"), not as
  standings; full list with `as_of` in `data.json` -> `leads_for_discussion`. No ops written.

**C. hungary-2020 and hungary-2021 probably did not run**
- Question: move them to `registry/cms-triage.yaml` as cancelled?
- Evidence: CMS 4529 and 4894 have no date and 0 teams; ELTE's posts say teams entered the postponed CERC 2020 directly
  ("Akárhány csapat részt vehet", 2021-08-26) and were picked for CERC 2021 by application form and earlier contests
  (2022-04-05). No national round is mentioned anywhere on versenyek.inf.elte.hu.
- For keeping: the CMS created the shells, and other Hungarian universities might have run something unpublicised.
- Recommendation: move both to cms-triage (cancelled), note "indicates".

**D. romania-2020 is probably an administrative shell** (CMS 4537: 74 registered teams, no standings, no site anywhere;
SEERC 2020 at UPB two weeks later). Same recommendation as C, lower confidence; already listed as "nothing found" by the
no-sources hunt of 2026-11-16.

**E. NEERC 1998/1999 subregionals and the 2001-2002 West-Siberian / 2002 Western contests: nothing survives that we
could reach.** The NEERC 1999 site (`/Archive/1999.html`) is a 404 in the Wayback Machine, the 1998 results page holds
only the Northern and Southern sections, the 2001 Siberian page has an empty Results section, and the 2002 archive has no
western/siberian pages. Open veins: Belarusian SU pages (www.fpmi.bsu.by/acmicpc/, Wayback CDX timed out), NSTU
(olymp.nstu.ru). The ETH SWERC site's PastContests.html (Wayback 1997) was opened: problem sets only. Recommendation: one more
Wayback pass on those hosts when the Machine is responsive.

## By-catch (not applied; other agents' areas)

Dates/places read on the results pages (north-russia-1998 24 Oct 1998; south-russia-1998 6-10 Oct 1998; urals-1998..2001
dates; far-east-russia-1999/2000; central-russia-2002 17 Oct 2002) and the UVa problem numbers of hungary-2014/2015/2017/2018
are in `data.json`.

## Blocked / not done

- The Wayback Machine refused or timed out most CDX queries from the device; background jobs do not survive a call; the
  session was cut twice. Not reached beyond our own holdings: bulgaria-2010, slovenia-2009/2010, turkey-2010,
  azerbaijan-2006/2007/2010, bapc-prelims-2009/2010/2011, cerc/nwerc/swerc/werc 1992-1997, erc-1983/1986/1991.
