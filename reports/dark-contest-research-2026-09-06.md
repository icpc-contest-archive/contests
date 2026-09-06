# Dark-contest research round 9 — 2026-09-06 (follow-up pass merged)

Scope: the 7 sites that failed capture twice, plus every real catalogue contest with
**nothing archived**: 242 with no URLs on file, 79 whose known URLs all proved dead or
snapshot-less. 328 targets total, researched by 6 agents (breadth-first, findings in
`data/research-round9-findings.json`).

**Verdicts after the same-day follow-up pass: 172 found-urls · 86 needs-more ·
70 likely-nothing-ever-online.** 381 URL candidates + 347 wayback-probe targets recorded.
(First pass: 144/142/42; the follow-up covered the 105 zero-search targets.)

## The 7 failed sites

| contest | verdict | best lead |
|---|---|---|
| acpc-2002 | found-urls | drdash.org `/acpc/2002/` CDX target + Baylor's mirror of the aucegypt.edu anarc02 site |
| harbin-2009 | found-urls | `board.acmicpc.info/icpc2009/` + live SDUT ranklist mirror + XCPCIO board-data + `acm.hit.edu.cn` CDX |
| ecna-1989 | found-urls | usenet post (Utzoo-recoverable msg-id) + live official `icpc-ecna.ysu.edu/PastResults/` tree |
| erc-1990 | found-urls | ChipCie (TU Delft) live archive already serves the scoreboard; probe `/archive/1990/nwercpc/` |
| wf-1991 | found-urls | comp.org.acm post in Utzoo range + `cphof.org/standings/icpc/1991` + Baylor `/past/icpc91/` CDX |
| oman-2021 | needs-more | CDX of `twitter.com/ocpc_official` around 2021-11-06; API standings already on file |
| taiwan-1993 | needs-more | soc.culture.china usenet post (post-Utzoo; Google Groups / IA usenet collection) |

## Standout finds

- **socalcontest.org `/history/<year>/results-<year>.shtml`** plausibly covers **all 14 dark
  SoCal years 1979–1993** — the host is HTTP-only and 302-loops HTTPS fetchers; needs a
  plain-HTTP fetch or wayback (browser-pass / Mac).
- **UCF team-record page is ALIVE** — catalogued as dead, but it fetched fine and carries
  per-year SEUSA placements (resolves seusa-1988/1990/1996). Worth a url_state correction.
- **ChipCie NWERC archive is unbroken 1995–2025** — nwerc-1995/1996 problem sets recovered.
- **One academic PDF (kgeorgiy.info) names all 8 NEERC quarterfinal hosts for 2001-02** —
  upgrades five Russian/Belarus subregional entries at once.
- **icpc.global finder-slug pattern** (`<prefix>-<season>`) verified across 8+ series →
  94 of the 106 post-2015 dark contests got finder/API-backed candidates (208 of the 328
  targets carry cms_ids — API standings are one top-up run away).
- **ACPC scoreboard hosts are inconsistently purged** — some `scoreboard.acpc.global`
  contest dirs are still live while catalogued siblings 404: a targeted CDX re-probe of
  exact paths (`/all.html`, `/summary.html`) beats more searching for the Arab qualifiers.
- **Usenet vein for the pre-web era**: three recoverable message-ids (ecna-1989, erc-1990,
  wf-1991) via Utzoo/Wiseman; the GNY negative (official repo starts 1997) is well corroborated.

## Follow-up pass (same day, 105 zero-search targets)

Access requests were frontloaded (~25 constructed-URL prompts raised in one batch;
several hosts confirmed live in the process), then three agents re-ran the gap clusters:

- **karrels.org holds a complete East-Central 1992–1997 problem archive plus a Western
  European 1994 set — seven contests (ecna-1992..1997, werc-1994) from one HTTP-only
  host.** Needs Mac/wayback capture (the host fights HTTPS); recorded as candidates
  pending that verification.
- **Timus Online Judge carries the central-russia-2000 and -2002 problem sets**, labeled
  as NEERC Central Subregional (Rybinsk).
- **Ukraine 2024/2025 live on algotester**: per-stage scoreboards incl. a dedicated
  icpc2025.algotester.com with Stage 1 (635 teams) / Stage 2 (252) / Stage 3. JS-rendered
  → browser pass.
- **amritapuri-2025 has a full official archive at amritaicpc.in** (ranklists, winners,
  problem PDFs); **chennai-2023** scoreboard on CodeDrills; **nena-north-2019 is a live
  Kattis contest site** (mcgill19.kattis.com + open mirror).
- **shanghai-2023 identified as the 2023 EC-Final**, fully mirrored by Universal Cup
  (Stage 23) — the ucup ecosystem mirrors essentially all 2023 China regionals, a
  reusable pattern.
- **PCPC organizer page resolves Palestine 2012–2020** with hosts per edition.
- **Russian quarterfinals 1998–2002: 18 evidence-backed negatives** — organizer paper
  identifies all six subregion hosts, and both neerc.ifmo.ru and contest.sgu.ru archives
  are confirmed blank for those years. Web presence likely never existed.
- **CORRECTION to the first pass:** socalcontest.org's /history/ tree reportedly starts
  at 1995 — per-year result pages for 1979–1994 are NOT there (404s), contradicting the
  first pass's optimistic guess. socal-1989 problems recovered via the ETH/NTHU problem-
  archive mirror instead; the rest of the early SoCal cluster moves to wayback probes.
- **ACPC scoreboard hosts actively purge**: a URL search-indexed months ago now 404s.
  The Tunisia/Gulf candidates there are at risk — wayback capture is urgent, not optional.

Still needs-more after both passes: 86 — mostly Turkey 2010–2023 (organizer domain still
unidentified), Kharagpur (self-hosts on an unreachable domain), gny-1995/96, mausa-1997,
scusa-1989..94 (second problem-archive source corroborates the negatives), romania-2020,
and the Oman finder prefixes.

## Deep round (same day, the 86 needs-more)

Four agents went deep on fewer targets. **Round totals now: 199 found-urls · 87
likely-nothing-ever-online · 42 needs-more.** 242 further candidates in
`data/url-candidates-round9b.json` (supplement — verify separately from round9).

- **Turkey solved, with a structural surprise: no Turkish regional site existed
  2010–2018.** Three independent primary sources (incl. inzva's own "first official
  Turkish programming contest ever organized", Sept 2019) show Turkish teams simply
  traveled to SEERC sites abroad. The catalogue's turkey-2010..2018 rows likely record
  SEERC participation, not standalone contests — **needs a Fredrik ruling** (echoes the
  D1 identity lens). 2020–2023 = inzva-organized, scoreboards recovered on algotester
  (2020) and algoleague (2021–23).
- **The built-in browser renders what WebFetch can't**: the icpc.global finder SPA
  renders fully in a real browser (host/city/dates/team counts per contest), and
  syria-2024's `acpcsb.acpc.global/SCPC2024/all.html` scoreboard is LIVE behind its
  bot-wall — a complete 25-team frozen grid. ~17 targets resolved this way; the
  browser pass is now a first-class tool for JS shells and bot-walled hosts.
- **Bolivia 2009–2014 fully resolved** (host cities, sponsors, dates; slug convention
  `bolivia-preliminary-<season>`); lebanon-2009 got a primary-source correction (LAU
  hosted, not BAU); romania-2020 pinned to the COVID-delayed May 2021 event at UPB.
- **Tunisia 2024/25 upgraded**: the host school's own dated event pages
  (polytecsousse.tn) match catalogue dates; Oman 2025 preliminaries mapped to real
  governorate sites (Sohar/Nizwa/Muscat) via an MTCIT recap.
- **far-east-russia-1998**: `imcs.dvgu.ru/acm` documented as hosting results "since
  1998" in academic citations; domain dead, successor archives only reach 2003 —
  the pre-2003 Russian digitization gap is now corroborated across four subregions.
- **KRSU (Kyrgyzstan) is a site-wide HTTP 401 wall** — browser-pass target, not dead.
- Daily Bruin microfilm reels for socal-1990..94 are keyword-searchable on archive.org
  (item pages wayback-side); Rice Thresher fully digitized at texashistory.unt.edu
  (JS search — browser pass).

## Next steps

1. CDX-probe the 322 wayback targets from the Mac (existing verify pipeline).
2. Plain-HTTP/wayback fetch of the socalcontest.org history tree (14 contests).
3. API standings top-up for cms_id-bearing dark contests (with the existing 50-gap list).
4. Follow-up search pass on the ~52 zero/low-search targets.
5. Feed `found-urls` candidates through verify_url_candidates → capture queue as usual.
6. url_state correction: UCF team-record page live, not dead.
