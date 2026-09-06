# Dark-contest research round 9 — 2026-09-06

Scope: the 7 sites that failed capture twice, plus every real catalogue contest with
**nothing archived**: 242 with no URLs on file, 79 whose known URLs all proved dead or
snapshot-less. 328 targets total, researched by 6 agents (breadth-first, findings in
`data/research-round9-findings.json`).

**Verdicts: 144 found-urls · 142 needs-more · 42 likely-nothing-ever-online.**
321 new URL candidates + 322 wayback-probe targets recorded.

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

## Honest gaps (shared search budget ran out at 200 calls)

Zero-search targets to re-run when budget refreshes: **turkey-2010..2023 (13)**,
**ukraine-2023..2025 (3)**, **India cluster: amritapuri/chennai/gwalior/kharagpur (5)**,
**saudi/sudan/togo/tunisia (9)**, **bolivia-national-2009..14 + colombia-maraton-2008..14 +
tap-2012/13 (15)**, **Oman sub-region finder prefixes (7)**. All are marked needs-more with
their leads recorded.

## Next steps

1. CDX-probe the 322 wayback targets from the Mac (existing verify pipeline).
2. Plain-HTTP/wayback fetch of the socalcontest.org history tree (14 contests).
3. API standings top-up for cms_id-bearing dark contests (with the existing 50-gap list).
4. Follow-up search pass on the ~52 zero/low-search targets.
5. Feed `found-urls` candidates through verify_url_candidates → capture queue as usual.
6. url_state correction: UCF team-record page live, not dead.
