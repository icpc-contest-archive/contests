# Definitions and data model

This repo catalogues **ICPC contests**: contests, in the ICPC ecosystem, in the mainline
contest hierarchy of the ICPC. Operationally, a contest is *mainline* iff it is a World
Finals, or performing well in it could advance a team toward a World Finals — i.e. its
`parent` chain reaches a `wf-*` contest. Everything the CMS DB contains that fails this
test is not in the catalogue; it is accounted for in the registries instead, so that every
CMS DB entry remains *considered*.

## The three stores

- `series/<series>.yaml` — the catalogue. Mainline contests only: ones that ran, plus
  `status: upcoming` for future editions. One file per series, contests in chronological
  order.
- `registry/cms-triage.yaml` — every CMS DB contest id that is **not** a mainline contest,
  with the reason: `cancelled` (no proof it happened; the CMS auto-copies contests across
  years, so ghost entries are common), `camp` (training camps), `challenge`
  (challenge-style contests), `junk` (test/garbage entries), `minor` (real contests
  outside the mainline), `structural` (hierarchy nodes, not contests).
- `registry/non-mainline.yaml` — real contests with no CMS id that exist outside the
  hierarchy (university opens etc.). Reference material, not catalogue members.

## Naming

`<contest-id>` = `<series>-<year>`, lowercase. The year follows ICPC season convention as
used historically: fall regionals carry the season-start year; World Finals and
championships carry the season-end year. `season` stores the season **end** year
explicitly (equals the CMS DB's `icpc_year`), so `nwerc-2018` has `season: 2019` and
feeds `wf-2019`. Dates can drift from the name year (January contests, COVID
postponements — `wf-2022` ran in Luxor on 2024-04-19); the name year is the season label,
not the calendar date.

## Field semantics

- **Absent field = not yet researched. `null` = confirmed none.** This replaces the
  sheet-era `-` / blank / `n/a` sentinels everywhere.
- `parent` — the contest a team advances *to* (regional → championship/WF). May be a
  list (NAQ feeds many regionals). `wf-*` contests have `parent: null`.
- `next` — the following edition. May be a list for series splits
  (`swerc-1998` → `[swerc-1999, mcerc-1999]`); merges are several contests sharing one
  `next`. **Cancelled editions are not chain members**: `awc-2019 → awc-2021`, and the
  cancelled awc-2020 lives in cms-triage.
- `cms_ids` — CMS DB ids; a list because one contest can span several DB entries
  (naq-2012 = ids 1537–1547). `[]` = known to have no CMS entry; `cms_status: pre-cms`
  marks the pre-1998/99 era (until backfilled upstream). Each CMS id belongs to exactly
  one contest across catalogue + triage, except along a `subset_of` edge.
- `subset_of` — the NA-division double layer: `seusa-2024` is a regional-level view of
  the combined `south-na-2024` division contest, sharing its CMS ids. Both are real;
  counting or coverage tooling must dedupe along this edge.
- `results` — per-artifact source lists, in decreasing information order:
  `scoreboard` (full, per-problem) > `frozen_scoreboard` > `standings` (totals only) >
  `rankings` (order only). Each entry is `{url, archived?, wayback?, fetched?, note?}`;
  `archived` references the (separate) archive repo by
  `<contest-id>/<artifact>/<fetch-date>`.
- `icpc_standings` — the CMS finder page
  (`https://icpc.global/regionals/finder/<abbrev>-<year>/standings`).
- Series headers may carry `tier: championship` (nac, awc, euc, apc, lac, aec, nadc —
  the layer skipped when deriving hierarchy depth), derived `lineage` events
  (`continues-as` / `continues-from` with the boundary year), `aliases` (old ids), and
  `rotating_host` (Asia host-city series where year gaps are structural).

## Levels

Tier labels drift across eras (NWERC moved under the EUC in season 2024 unchanged; ACPC
was renamed a Championship), so **level is derived from the graph**, never stored per
contest: WF → championship layer (flagged series) → regional → subregional → below.
Below-subregional currently exists only twice: BAPC preliminaries (2009–) and the African
national contests under the South Africa regional (2016–2019).

## Provenance

The initial import came from the "ICPC contest list / Main list" sheet
(`data/import/`, mechanical fixes logged in `CONVERSION-FIXES.md`). From this import on,
**this repo is the source of truth**; edits happen here, with git history as the audit
trail. `sources:` and `notes:` on a contest record where facts came from;
`reports/open-warnings.md` tracks the judgment calls still open.
