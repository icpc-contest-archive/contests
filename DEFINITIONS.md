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
  `rankings` (order only). Each entry is `{url, as_of?, archived?, fetched?, note?}`
  (see *Resources* below); `archived` references the (separate) archive repo by
  `<contest-id>/<artifact>/<fetch-date>`.
- `web` — the contest website: a URL, or `{url, as_of}` when the live address is gone
  and the site as of a Wayback snapshot is what is meant; a list for multi-site
  contests. `mirrors[]` and `problemset` take the same form.
- `icpc_standings` — the CMS finder page
  (`https://icpc.global/regionals/finder/<abbrev>-<year>/standings`).
- Series headers may carry `tier: championship` (nac, awc, euc, apc, lac, aec, nadc —
  the layer skipped when deriving hierarchy depth), derived `lineage` events
  (`continues-as` / `continues-from` with the boundary year), `aliases` (old ids), and
  `rotating_host` (Asia host-city series where year gaps are structural).

## Resources

Three things used to be called "URL"; they are distinct.

- A **locator** is a URL as an *address*, with no time attached:
  `http://icpc.baylor.edu/past/EarlyYears.html`. Catalogue fields hold locators only —
  `results.*[].url`, `web`, `mirrors[].url`, `problemset`. A locator has a *health*
  (`url_state` at `url_checked`) but no content of its own; content exists only at a time.
  A locator may carry **`as_of`**, a timestamp meaning "the content we mean is what this
  address served at this time" — recorded when a result was found on the Wayback
  Machine rather than live. It is kept at whatever precision we have (`2011`,
  `20110102`, `20110102183612`, Wayback style) and is never a promise about one
  particular snapshot: tools resolve "nearest snapshot to `as_of`" when they need a
  Wayback link, and the capture is what pins the exact thing.
- A **resource** is a locator observed at a point in time: **(url, time)**. Its content is
  whatever the address served at that moment. Rules for `time`: fetched live by us → our
  fetch time; fetched from the Wayback Machine → the **snapshot's own timestamp**, the
  one Wayback actually served (it redirects to the nearest), not the one we asked for;
  taken from a data dump (CMS/API standings) → the dump time.
- A **capture** is our stored copy of a resource: (url, time) plus `via` (live, wayback,
  api-dump, another archive), the wrapper URL actually fetched, our own fetch time,
  sha256, content type and path. Several captures of one resource should hash
  identically — a useful check. Captures live in the archive repo; the catalogue points
  at them with `archived`.

So **the archive holds resources; the catalogue holds locators** plus pointers to the
captures we hold of them. The catalogue says "look here"; the archive says "this is what
was there on that date".

**Wrapper URLs are never locators.** `https://web.archive.org/web/20110102183612fw_/http://icpc.baylor.edu/past/EarlyYears.html`
is a resource reference: (`http://icpc.baylor.edu/past/EarlyYears.html`, 2011-01-02
18:36:12). Ingest unwraps it — inner URL becomes the locator, the timestamp becomes
`as_of`, the presentation flags (`id_`, `fw_`, `im_`, …) are dropped, a `*` calendar
query carries no time and is dropped, and a wayback-of-a-wayback unwraps to the
innermost URL and timestamp. `validate.py` rejects wrapper URLs in locator fields;
`tools/resources.py` is the one parser (`unwrap`, `wayback_link`, `fmt_time`, `label`).
Other archives with a recoverable inner URL (arquivo.pt, LoC, Stanford SWAP, UKWA) get
the same treatment; archive.today short links don't carry the URL and stay a `via`.

**Presentation.** A resource displays as **`url (time)`** at the precision known —
`2011-01-02 18:36`, `2026-04-15`, `2011`; a bare locator displays as the URL. Link
vocabulary on a result row: *live* = the locator as is; *wayback* = pinned to `as_of`
(or the capture's snapshot) when known, the calendar otherwise; *archived (time)* = our
capture; *raw* = the capture file untouched. Nothing ever links to a Wayback URL of a
Wayback URL.

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
