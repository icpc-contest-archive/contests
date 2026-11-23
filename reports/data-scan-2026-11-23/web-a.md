# Data scan 2026-11-23 — web-a: missing contest websites (North America, Latin America, International)

Agent `web-a`. Area: contests that ran (not `status: upcoming`) in series whose header `region` is North America,
Latin America or International, with **no source whose roles include `web`**. Ruling used: `web` = a page or
site by the organisers or the host about that edition; one results page is not `web`.

## What I checked and how (rerunnable)

- Targets: `work/targets.json` — 165 contests at scan start (76 Latin America, 76 North America, 13 International;
  one, gny-1995, has `none: [web]`). Built from `cat.load_series()` (header `series.region`), skipping upcoming
  contests and contests where any source has role `web`.
- Hunt, newest seasons first:
  1. links inside our held copies of the contest's other sources (`work/held_links.json`, from every archived
     HTML of each target) and sibling editions' web addresses (`work/sibling_web.txt`) → same pattern this year;
  2. Wayback CDX from the device shell over the organisers' domains for the contest's season
     (`work/bin/cdx.py`), every snapshot opened and read before use (`work/bin/get.py`, `id_` replay);
  3. live pages and web search (super-region and national organiser sites: icpclatam.org, icpccaribe.org,
     icpccentroamerica.org, acis.org.co, aapc.org.ar, maratona.sbc.org.br, na.icpc.global).
- Every candidate is in `work/cands.jsonl` with the text of the page that shows it is this edition; contests where
  nothing was found are in `work/nothing.jsonl` with what was tried. `work/bin/build_ops.py` turns the candidates
  into `ops.json` (it drops a candidate whose URL the contest already has); `work/bin/build_data.py` writes `data.json`.
- `python3 tools/apply_scan_ops.py --check ../findings/web-a/ops.json` → all ops `ok`.
- The worktree moved during the scan (series files rewritten 08:56 UTC, other scan agents' ops applied):
  seusa-2026 and east-na-2026 gained a `web` source from another agent; my duplicates for them were dropped.

## Counts

- Targets at scan start: 165. Another agent's ops added `web` to seusa-2026 and east-na-2026 meanwhile (my
  duplicates dropped).
- **ops.json: 71 operations, all `append` of a new source** to `["contests", {"id": X}, "sources"]`, covering
  **59 contests**; 70 have roles `[web]`, one `[web, problemset]` (ecna-2022, the page lists the problem names).
  Each new source has `note: "found by the data scan 2026-11-23 (...)"`, `unique_keys: [url, as_of]`, and `as_of`
  when the content meant is a Wayback snapshot. No facts were changed (no provenance lines needed).
- Nothing found: 25 contests (list below and in `data.json` → `nothing_found`). Held back: 2 (wf-2015, wf-2022).
- Not reached: 79 (`data.json` → `not_reached`).

## What the ops add (grouped)

- **ICPC Latin America super-region site** www.icpclatam.org (live, one page per edition): `regionals/lar2026/`
  → brazil-2026, caribbean-2026, central-america-2026, south-america-north-2026, south-america-south-2026;
  `lar2025/` → caribbean-, central-america-, south-america-north-, south-america-south-2025; `lar2024/` →
  central-america-, south-america-north-, south-america-south-2024; `championships/lac2025/`, `lac2026/` → lac-2025,
  lac-2026. Plus the host sites it names: pda2025.gruproufba.com.br (lac-2025), latam2026.icpc.cl (lac-2026).
- **Regional / national organiser sites, Latin America**: icpccaribe.org Final Caribeña call (caribbean-2026 live;
  caribbean-2025 @20251005230655); icpc-caribe.com Eliminatoria call (caribbean-national-2020 @20210509123320);
  icpccentroamerica.org (central-america-2026 and gran-premio-centroamerica-2026 live; central-america-2025 and
  gran-premio-centroamerica-2025 @20251205135005); acis.org.co (colombia-maraton-2025 `maraton-nacional-2025`;
  south-america-north-2024/2025/2026 Colombian-site pages, `scope: Colombia`); aapc.org.ar/regional-latinoamericana/
  (south-america-south-2026, `scope: Argentina (Santa Fe site)`); UBA's SA-South site dc.uba.ar/events/icpc/YYYY
  (south-america-south-2009, 2011, 2012, 2013, 2015, 2016, 2017, Wayback); TAP site torneoprogramacion.com.ar
  (tap-2015..2021, Wayback; the per-edition "inscripción abierta" posts) and icpc.com.ar/tap/ (tap-2025
  @20250821004321); maratona.sbc.org.br `hist/YYYY/index.html` (brazil-first-phase-2005/2006/2007, brazil-2017) and
  `final.html` (brazil-2026, live).
- **North America**: na.icpc.global NAQ pages (naq-2022 ×2, naq-2023, naq-2024 Wayback; naq-2026 live); ECNA archive
  page section 2022–23 (ecna-2022); NCNA 2021-22 page (ncna-2021); ncna-region.unl.edu @20210303 (ncna-2020);
  sdsmt Mid-Central 2020 page (mcpc-2020); RIT NENA finals 2019 (nena-2019); cse.buffalo.edu/icpc/ (nena-west-2019,
  live); acm2019.scusa.lsu.edu (scusa-2019); division sites east.na.icpc.global (east-na-2024) and
  south.na.icpc.global (south-na-2026); webdocs.cs.ualberta.ca/~acpc/YYYY/ (alberta-2003, 2004, 2005, 2008, 2009,
  2010, 2013).
- **World Finals**: worldfinals.icpc.global/2021/ (wf-2021, Dhaka) and /2019/ (wf-2019, Porto), both live.

Every snapshot used was opened and read; the text that shows the edition is in each op's `evidence`.

## Items for discussion with Fredrik

1. **ICPC News "World Finals YYYY" pages: `web` or `report`+`rankings`?** news.icpc.global/wfYYYY/ is filed `[web]`
   for wf-2012, wf-2013, wf-2016 but `[rankings, report]` with `scope: champions` for wf-2006, wf-2007, wf-2011,
   wf-2023. The same page exists for wf-2015 and wf-2022 (both without web); I held them back.
   *Web*: it is the organiser's own page about that edition. *Report+rankings*: it is a news/champions item, which
   the 2026-11-14 ruling lists under `report`, and the real edition sites are worldfinals.icpc.global/YYYY/ or the
   host's site. Examples: https://news.icpc.global/wf2016/ (web), https://news.icpc.global/wf2023/ (report).
   **Recommendation:** report + rankings (scope champions) everywhere; re-role wf-2012/2013/2016; then add wf-2015
   and wf-2022 that way. wf-2022/2023 (Luxor) would stay without web: worldfinals.icpc.global/2022/ is 403,
   /2023/ 404, and I found no Luxor site.
2. **One super-region page as `web` of six regional finals.** icpclatam.org/regionals/lar2026/ describes the one
   Latin America Regionals event that the catalogue splits into brazil-, caribbean-, central-america-, mexico-,
   south-america-north- and south-america-south-YYYY. I filed it as `web` of each, without `scope` (the page has no
   per-region sections). *For*: it is the organisers' page of that edition, and the ruling makes a multi-contest page
   a source of each. *Against*: it is not specific to one regional final. **Recommendation:** keep as filed; for the
   country pages (ACIS Colombia, AAPC Argentina) I did add `scope`.
3. **CMS finder pages filed as `web`, against the ruling.** 25 `web` sources are icpc.global (or icpc.baylor.edu)
   `regionals/finder/...` pages (22 Latin America, 3 Asia Pacific), e.g. colombia-maraton-2019/2026,
   gran-premio-centroamerica-2019/2020/2021/2023/2024, gran-premio-mexico-2019/2020/2023/2025, caribbean-national-2013..2019,
   torneo-chileno-2023/2025/2026, south-america-south-2014. The ruling says a CMS finder page is not `web`. They hide
   real gaps from a "no web" check: colombia-maraton-2026 has https://www.acis.org.co/maraton-nacional-2026.
   **Recommendation:** remove these as `web` (or drop the role) in a separate pass, then rerun this hunt on them.
   Full list: `data.json` → `cms_finder_pages_filed_web`.
4. **History and compilation pages filed as `web`.** wf-1992..1999 (icpc.global/community/history-icpc-YYYY),
   central-america-1997 and south-america-1997 (icpccaribe.org history compilations), scusa-1989/1990/1994 (the
   texashistory.unt.edu collection page), mcpc-1993/1994 (catsofwywop.com browse page). The ruling puts history pages
   under `report`. So I did not add history pages for wf-1986..1990. **Recommendation:** re-role them to `report`.
5. **Live-only sources on reused addresses.** naq-2026 (na.icpc.global/naq/), caribbean-2026 (icpccaribe.org
   call), central-america-2026 and gran-premio-centroamerica-2026 (icpccentroamerica.org), south-america-south-2026
   (aapc.org.ar), south-america-north-2026 (acis.org.co maraton-regional-2026) and brazil-2026
   (maratona.sbc.org.br/final.html) show this edition now but are overwritten every season, and Wayback has no copy
   yet. **Recommendation:** have the next capture round copy them now (or Save Page Now), then pin `as_of`;
   otherwise they become year-reused next autumn. naq-2025 is already lost this way: na.icpc.global/naq/ has no
   capture between 2024-11-26 and now.
6. **Thin division sites.** For east-na-2024 and south-na-2026 the only organiser page is the division landing page
   (a few lines plus a scoreboard link). south.na.icpc.global's "Scoreboard 2026-2027" even points to
   ncna26.kattis.com, an organiser error. south-na-2024/2025 instead use sc.na.icpc.global (the South Central
   site). **Recommendation:** accept division sites as the division contest's `web` (as filed); fixing the
   south-na-2024/2025 sources is outside this scan.
7. **Facts seen but not applied (outside my area).** caribbean-national-2020: the organisers' call gives the
   qualifier as **2021-02-20**, but the catalogue has 2021-06-26 (from the CMS). tap-2021 has no date; the
   organisers' post gives **2021-10-30**. south-america-south-2013: the UBA page lists the sites as Buenos Aires,
   Cochabamba, Valparaiso and Lima; the catalogue has Temuco. gran-premio-centroamerica-2026: the catalogue date
   2026-03-24 does not match the site's 2026 qualifier rounds (Apr–Sep 2026). Details: `data.json` →
   `fact_differences_not_applied`. **Recommendation:** pass them to the dates/locations agent.
8. **By-catch results pages (not filed: not `web`).** ACIS results pages for the Colombian national and regional
   marathons 2021–2023 (nacional-2023 is a per-problem scoreboard), TAP results posts 2015–2019 on
   torneoprogramacion.com.ar, and the BOCA report copy maratona.sbc.org.br/latam-2025/. List: `data.json` →
   `bycatch_results_pages_not_filed`. **Recommendation:** hand them to the results agents.

## Contests with nothing found (what was tried)

- `caribbean-national-2021` — icpc-caribe.com/eliminatoria* (snapshots stop 2021-09) and icpccaribe.org/eliminatoria* (snapshots start 2023-01): no copy from the 2021-22 qualifier season; the icpccaribe.org 'clasificados-regional-2021' page is a qualified-teams list, not web
- `lethbridge-2017` — www.cs.uleth.ca/~cheng/LCPC/2017/ (live) holds only '2017 Results' (top 3 per division) and is already a rankings source; per the ruling a single results page is not web; no other page
- `lethbridge-2020` — www.cs.uleth.ca/~cheng/LCPC/2020/ answers 404 (the LCPC/ index lists only 2013-2019 and 2025); the held source is the ~cheng/contest/ results list; no other page found
- `lethbridge-2021` — www.cs.uleth.ca/~cheng/LCPC/2021/ answers 404 (the LCPC/ index lists only 2013-2019 and 2025); the held source is the ~cheng/contest/ results list; no other page found
- `lethbridge-2023` — www.cs.uleth.ca/~cheng/LCPC/2023/ answers 404 (the LCPC/ index lists only 2013-2019 and 2025); the held source is the ~cheng/contest/ results list; no other page found
- `lethbridge-2024` — www.cs.uleth.ca/~cheng/LCPC/2024/ answers 404 (the LCPC/ index lists only 2013-2019 and 2025); the held source is the ~cheng/contest/ results list; no other page found
- `mcpc-2017` — icpc-midcentral.us (mcpc-2015/2016/2018 web): Wayback 20171106102516 still shows the 2014 contest ('Updated Oct 17 2015'), so no copy of the 2017 edition; no other organiser page found
- `naq-2025` — na.icpc.global/naq/ (the series site for naq-2021..2026): CDX + availability API show no snapshot between 20241126 and now (live shows 2026); naq25.kattis.com is a judge, not web
- `nena-2016` — cs.rit.edu/~icpc (NENA site, nena-2005..2015 web): every Wayback capture 2016-01..2019-07 is a 302 http->https with no https capture before 2019-08-21; no other NENA page of this edition found
- `nena-2017` — same as nena-2016: cs.rit.edu/~icpc captures in 2017-2018 are only http->https redirects
- `nena-2018` — same as nena-2016: cs.rit.edu/~icpc captures in 2018-2019 are only redirects (the scoreboard/ capture 20181115220248 is results, not web)
- `nena-2020` — cs.rit.edu/~icpc contests/finals pages captured 2020-08 and 2021-03 still show the 2019 season; ne.na.icpc.global starts with 2023-24; nothing for the online 2021-03-06 contest
- `nena-2021` — as nena-2020; nena21.kattis.com is a judge, not web
- `nena-2022` — cs.rit.edu/~icpc @20230210 is the generic frame (region.html); na.icpc.global/northeast/ only from 2024-09; ne.na.icpc.global archive starts 2023-24
- `nena-atlantic-2012` — scienceatlantic.ca/ocs/mscs/index.php/2012/mscs2012 (Wayback 20120811212046) is a draft MSCS 2012 conference page (Mount Allison, Oct 12-13 2012) with no mention of the programming contest - not filed
- `nena-atlantic-2018` — scienceatlantic.ca/mscs-2018/ (Wayback 20190821095030) is the MSCS 2018 conference page ('October 12-14 at Université de Moncton') but says nothing about the programming contest - not filed; web.cs.dal.ca/~dpc pages are Dalhousie local contests
- `nena-north-2017` — people.clarkson.edu/clubs/acm/icpc2017.htm (pattern of nena-north-2015/2016/2018): 403 live and never captured by the Wayback Machine (CDX of clubs/acm/* 2017-18 has only the 2018 page); nothing else found
- `rmc-2022` — rocky.icpc.io (rmc-2019..2023 web): Wayback has root captures 20211206 then 20240329 - none in the 2022-23 season; na.icpc.global/rocky/ only from 2024-09
- `wf-1986` — news.icpc.global/wf1986/ answers 404 (wf2006+ exist); icpc.baylor.edu/past/EarlyYears.html covers only 1977-1985 (wf-1977..1985 web); the icpc.global/community/history-icpc-YYYY pages are history pages, which by the 2026-11-14 ruling are report, not web - not filed; not searched further
- `wf-1987` — news.icpc.global/wf1987/ answers 404 (wf2006+ exist); icpc.baylor.edu/past/EarlyYears.html covers only 1977-1985 (wf-1977..1985 web); the icpc.global/community/history-icpc-YYYY pages are history pages, which by the 2026-11-14 ruling are report, not web - not filed; not searched further
- `wf-1988` — news.icpc.global/wf1988/ answers 404 (wf2006+ exist); icpc.baylor.edu/past/EarlyYears.html covers only 1977-1985 (wf-1977..1985 web); the icpc.global/community/history-icpc-YYYY pages are history pages, which by the 2026-11-14 ruling are report, not web - not filed; not searched further
- `wf-1989` — news.icpc.global/wf1989/ answers 404 (wf2006+ exist); icpc.baylor.edu/past/EarlyYears.html covers only 1977-1985 (wf-1977..1985 web); the icpc.global/community/history-icpc-YYYY pages are history pages, which by the 2026-11-14 ruling are report, not web - not filed; not searched further
- `wf-1990` — news.icpc.global/wf1990/ answers 404 (wf2006+ exist); icpc.baylor.edu/past/EarlyYears.html covers only 1977-1985 (wf-1977..1985 web); the icpc.global/community/history-icpc-YYYY pages are history pages, which by the 2026-11-14 ruling are report, not web - not filed; not searched further
- `wf-2015` — news.icpc.global/wf2015/ (live, ICPC News 'World Finals 2015' champions page) exists but is held back: the same kind of page is web for wf-2012/2013/2016 and rankings+report for wf-2006/2007/2011/2023 (see discussion)
- `wf-2022` — news.icpc.global/wf2022/ (live, ICPC News 'World Finals 2022' champions page) exists but is held back: the same kind of page is web for wf-2012/2013/2016 and rankings+report for wf-2006/2007/2011/2023 (see discussion); worldfinals.icpc.global/2022/ 403, /2023/ 404; CDX of icpc.global/worldfinals/* 2023-24 shows only generic CMS pages

## Not reached (not judged either way)

The Wayback Machine refused this machine and the cloud container for about an hour mid-scan, and the session was
restarted twice, so I worked newest-first and stopped here:
tap-2024 torneo-chileno-2024 central-america-2023 colombia-maraton-2023 south-america-north-2023 south-america-south-2023 tap-2023 central-america-2022 colombia-maraton-2022 gran-premio-centroamerica-2022 south-america-north-2022 south-america-south-2022 tap-2022 wf-2023 central-america-2021 colombia-maraton-2021 south-america-north-2021 south-america-south-2021 central-america-2020 colombia-maraton-2020 south-america-north-2020 south-america-south-2020 central-america-2019 south-america-north-2019 south-america-south-2019 gran-premio-mexico-2018 south-america-north-2018 south-america-south-2018 colombia-maraton-2017 gran-premio-mexico-2017 south-america-north-2017 gran-premio-mexico-2016 south-america-north-2016 gran-premio-mexico-2015 south-america-north-2015 south-america-north-2013 south-america-north-2012 wf-2011 caribbean-2009 south-america-north-2008 wf-2007 wf-2006 ncna-1999 ecna-1998 ncna-1997 rmc-1997 scusa-1997 ecna-1996 mausa-1996 ncna-1996 rmc-1996 scusa-1996 gny-1995 mausa-1995 ncna-1995 rmc-1995 gny-1994 mausa-1994 ncna-1994 rmc-1994 ecna-1993 gny-1993 rmc-1993 scusa-1993 mcpc-1992 rmc-1992 scusa-1992 rmc-1991 ecna-1990 rmc-1990 rmc-1989 ecna-1988 scusa-1988 seusa-1988 ecna-1987 scusa-1987 ecna-1986 ecna-1985 ecna-1984

Leads for the next pass: central-america-2019..2023 and gran-premio-centroamerica-2022 (icpccentroamerica.org has
no capture before 2024-08; try the Mexico/ITESO pages); south-america-north-2012..2023 (acis.org.co old
`index.php?id=` and `portal/content/` pages); south-america-south-2018..2023 (no UBA site after 2017; try icpc.cl,
icpcbolivia.org); TAP 2022–2024 (torneoprogramacion.com.ar dead from 2022; icpc.com.ar captures only from 2025);
gran-premio-mexico-2015..2018 (eventos.iteso.mx/acm); the 1984–1999 North American regionals (Usenet archives,
icpc.baylor.edu/past/ reports, the old university addresses in sibling editions).
