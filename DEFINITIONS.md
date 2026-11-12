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
feeds `wf-2019`. Every contest has one: where no parent chain gives it, the series'
`naming` does (season-start: id year + 1). Which pattern a series follows is recorded as `naming` on its header
(`season-start` for fall-named series, `season-end` for the World Finals and
championships); a delayed or early edition keeps the pattern, so a fall regional moved to
January 2021 is still `<series>-2020` — successive editions keep successive numbers. Dates can drift from the name year (January contests, COVID
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
  (naq-2012 = ids 1537–1547). `[]` = known to have no CMS entry (the CMS is being
  backfilled, so there is no separate "pre-CMS" marker any more: the entry simply has no
  id yet). Each CMS id belongs to exactly one contest across catalogue + triage, except
  along a `subset_of` edge.
- `subset_of` — the NA-division double layer: `seusa-2024` is a regional-level view of
  the combined `south-na-2024` division contest, sharing its CMS ids. Both are real;
  counting or coverage tooling must dedupe along this edge.
- `sources` — every address of the contest, one entry per URL with the **roles** it
  serves: `{url, roles: [...], as_of?, also_at?, judge?, archived?, fetched?, url_state?,
  url_checked?, note?}` (see *Resources* below). Roles: `web` (the contest website;
  `also_at` lists mirrors of it), the result tiers in decreasing information order
  `scoreboard` (full, per-problem) > `frozen_scoreboard` > `standings` (totals only) >
  `rankings` (order only) > `icpc_standings` (the CMS finder page,
  `https://icpc.global/regionals/finder/<abbrev>-<year>/standings`), `teams`,
  `problemset`, `problem`, and `judge_page` (an online judge hosting the problems;
  `judge: kattis|livearchive|baekjoon|codeforces`). A page that is both the results and
  the problem set is one source with two roles. `archived` references the (separate)
  archive repo by `<contest-id>/<artifact>/<fetch-date>`. `none: [role, ...]` lists
  roles confirmed to have no source; a role in neither is not yet researched.
  `tools/catalogue.py` is the one reader (`by_role`, `has_role`, `best_result`, …).
- `archived` is a **list**: one address is often captured under several roles or in
  several runs, and every capture pointer is kept. `also_at` entries are a bare URL or
  `{url, as_of}` when the mirror itself is a Wayback-era address.
- `sites` — where the contest was held: `[{location: <locations.yaml node id>, name?, date?,
  type?: administrative|online}]`, one entry per site (see *Locations*). The free-text
  `location` string stays alongside until `sites` covers every contest.
- `provenance` — free-text lines recording where the entry's facts came from: where a
  date was read, proof that a contest with no results ran. The site shows these under
  *Evidence* on the contest page; import stamps (`ICPC Problem Archive progress sheet
  (…)`, `Baekjoon ICPC category tree …`) are about the problem set and are not shown
  there.
- `notes` — remarks about the contest itself (no teams in the CMS, two divisions, a
  doubtful date). Remarks about its problem set go on the set.
- Series headers carry `tier` (`world-finals` | `championship` | `regional` |
  `subregional` — championships are the continental layer skipped when deriving
  hierarchy depth; subregional = qualifiers, national/site rounds and regional-level
  views of a division), `region` (one of the eight ICPC super-regions; championships
  take the region they are the championship of; the World Finals series is
  `International`), `naming`
  (`season-start` | `season-end`: which half of the season the id's year names — see
  *Naming*; validate.py checks every id against it), derived `lineage` events
  (`continues-as` / `continues-from` with the boundary year), `aliases` (old ids), and
  `rotating_host` (Asia host-city series where year gaps are structural).

### Naming the URL layer (2026-11-02 redesign)

The user-facing words are **source** (a catalogued address with roles and health —
what a contest page lists), **snapshot** (that address at one time: a Wayback
snapshot, or our live fetch) and **capture** (our stored copy of a snapshot, with
provenance). The code and the paragraphs below still say *locator* for source and
*resource* for snapshot; they mean the same things.

## Resources

Three things used to be called "URL"; they are distinct.

- A **locator** is a URL as an *address*, with no time attached:
  `http://icpc.baylor.edu/past/EarlyYears.html`. The catalogue holds locators only —
  `sources[].url` and `sources[].also_at[]`. A locator has a *health*
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

**Identifiers.** A locator's id is the first 12 hex digits of sha256 over its match key
(`norm_key`: scheme-, www-, default-port-, case- and trailing-slash-insensitive), so it
survives the usual URL drift; a resource's id is `<locator id>@<ts>`. The site has a page per
source (`source/<id>/`: url, roles, health, references, its snapshot timeline with every capture;
the old `locator/<id>/` and `locator/<id>/<ts>.html` paths redirect there). `tools/build_resources.py` joins catalogue, archive index, website index,
live-check verdicts and replay index into `data/resources.json`, which those pages render from.

**Presentation.** A resource displays as **`url (time)`** at the precision known —
`2011-01-02 18:36`, `2026-04-15`, `2011`; a bare locator displays as the URL. Link
vocabulary on a result row: *live* = the locator as is; *wayback* = pinned to `as_of`
(or the capture's snapshot) when known, the calendar otherwise; *archived (time)* = our
capture; *raw* = the capture file untouched. Nothing ever links to a Wayback URL of a
Wayback URL.

## Problems

The ICPC Problem Archive (the private `icpc-problem-archive` GitHub org) holds the
problem material; this catalogue tracks *what* it holds and where the problems can be
solved online. Since 2026-11-02 a **problem set is its own object** (one set can serve
several contests: NCPC + UKIEPC 2013, shared North American sets):

- **Per contest**, `problems: {set: <set-id>, note?}` — only the link to the set.
- **Per set**, `problemsets/<set-id>.yaml` (`schema/problemsets.schema.json`): `id`,
  optional `name`, `repo` (the archive repo — `icpc-problem-archive/<name>`; the name
  usually equals the contest id but need not, e.g. `benelux-2022` for `bapc-2022`, and
  `statement-only` for statements only), `count`, `complete`, and one of `full` /
  `partial` / `none` for each kind of material: `statement`, `data`, `solutions`,
  `package`, with `counts:` giving the exact number for kinds marked partial.
  `contests:` lists the contests that used the set, each with its own `letters:` map
  (letter → problem id; letters can differ between contests sharing a set);
  `letters: unknown` on the set says no map is known for any contest. `problems:` lists
  the problems when known (`id` = internal permanent `p-xxxxxxxx` id, the page key;
  `uuid` = the package's `problem.yaml` uuid, the same across sets that reuse the
  problem; `name`, `short_name`, `have` (subset of statement, data, input_validator,
  output_validator, solutions, package), `status: private`, `judges`, `notes`). When the
  list is present the holdings must agree with it (validate.py checks).
- **Judges.** `judges.yaml` at the repo root is the registry of online judges (id, name,
  url, `problem_url` pattern, status, `closed` date — Baekjoon closed 2026-04-28). A
  contest's judge *pages* are sources with role `judge_page` (+ `judge: <id>`); a
  problem's judge links are its `judges: [{judge, url, id?, as_of?}]` list. Both refer to
  the registry by id.

**Shared sets.** A set sat by several contests has an id of its own and a `name`: `latam-<year>`
for the Latin America regional (every site sits the same problems; a site with no list of its own
is a member without letters), otherwise the member series joined in alphabetical order
(`nordic-ukiepc-2013`, `scusa-seusa-2020`). When separate sets turn out to be one,
`tools/merge_problemsets.py` merges them: the set's `aliases` keep the ids of the sets it replaces
and each problem's `aliases` the problem ids it replaces. The site redirects those addresses, and
`validate.py` refuses an alias that is also a live id. The first merge (2026-11-12) turned 87 sets
into 20; `reports/problemset-merge-2026-11-12.md` lists them and what was left alone.

The site renders a page per set (`problemset/<set-id>.html`), per problem
(`problem/<pid>.html`, aggregating every appearance), the set index
(`problemset/`) and the judge registry (`judge/`). The two pages divide the facts: the
**contest** page's Problems section says which set it used, lists the problems with this
contest's letters, and lists the sources (published set, judge pages); the **set** page
says what the problem archive holds, problem by problem. Per-problem holdings (`have`)
are recorded for few sets; elsewhere a problem's holdings follow from its set where the
set is all-or-nothing for a kind (`full` → held, `none` → not held, `partial` → not
recorded).

**Publication rule.** Nothing about a contest's problems — not the names, not the count —
is public before the contest has run. `validate.py` fails the build when a contest that is
upcoming or dated in the future carries problem data; in practice the material only
reaches the archive afterwards, so this is a guard, not a workflow. Problems kept private
*after* the contest may have their names and uuids listed.

`problemset:` (above) is different: it is a locator for the published problem set on the
web, a capture target, not a statement about the archive's holdings.

## Locations

Where a contest was held is a reference into one tree, `locations.yaml`
(`schema/locations.schema.json`), not a string. The tree has four node types, strictly
nested: **country** › **region** (state/province; optional, kept for the US, Canada and
Australia) › **city** › **institution** (a university or other venue). Every node has

- `id` — a slug, globally unique: countries are the ISO 3166-1 alpha-2 code in lowercase
  (`us`, `se`); everything below is `<country>-<slug>` (`us-co`, `us-boulder`,
  `us-boulder-cu-boulder`). A city keeps `<country>-<city>` whether or not it hangs under a
  region; an institution's id starts with its city's id. Ids are permanent page keys.
- `name` — the display name: the gazetteer's primary name for cities (`Saint Petersburg`,
  `Århus`), the institution's own name.
- `type`, `parent` (every node but a country), `iso` (country), `code` (region: the
  postal code), `geonameid` (city: the GeoNames populated place it was matched to, absent
  when the node was made from text alone — a village or a town the gazetteer lacks),
  `aliases` (other spellings seen in the sources: `Ekaterinburg`, `Univ. of Colorado,
  Boulder`; unique across nodes, except that an acronym like `UCI` may recur in another
  country), optional `notes`.

**Per contest**, `sites: [{location, name?, date?, type?}]`, one entry per site:

- `location` — the most specific node known: the institution when it is known, else the
  city, else the region or country. It must resolve (validate.py).
- `name` — the site's label as the CMS calls it, kept only when it says more than the
  node's name (`Perth Schools`, a division label, an unplaced institution).
- `date` — the site's own date when it differs from the contest's (staggered sites).
- `type` — `administrative` for the CMS's non-physical bookkeeping sites (its
  "Administrative Site Location", staff, hidden teams: recorded as `{type: administrative}`
  with no location) or `online` for teams competing remotely (with a location when the
  organising site is known).
- An entry with `name` but no `location` is a site the migration could not place; the
  open ones are listed in `data/locations-review-<date>.md`.

**Where a contest was held** is read from `sites` in this order (`held_at` in
`tools/build_site.py`): its physical sites (entries without a `type`); else, for an
online contest, the places its online or organising entries point at; else the city
most of its administrative entries sit in (a single-site event whose CMS record only
has staff, guest and team groups). The CMS clones a contest from the previous edition,
so administrative groups can carry a *stale* location (every World Finals 2019–2027
said Beijing): when the host is known, a group pointing elsewhere loses its location
(`tools/cleanup_2026_11_12.py`, step I). CMS groups are not institutions — "NAC Guests"
is a site label, never a node of the tree.

The free-text `location` string stays on the contest for now (it is what the sheet and the
CMS gave us, multi-site strings joined by `; `); the redesign drops it once `sites` covers
everything. `venue` is in the schema but unused — the venue is the institution node.

**Where it came from.** `tools/migrate_locations.py` built the tree (2026-11-02) from the
CMS site records (`data/cms-sites.json`: ~13k sites, only ~8% with a structured city and
country) and the free-text strings, resolving country (CMS country › a country name in the
text › a city lookup constrained to the series' region › the CMS geographic area), city
(CMS city › the text › the city embedded in the institution's name, "University of X" /
"X University" / "Campus X") and institution (a name with an institution word or a known
acronym) against the offline GeoNames gazetteer (`geonamescache`) and a hand table of
~670 institutions whose city is not in their name (`KNOWN_INSTITUTIONS` in the tool —
extend it there, re-run, and the tree picks the additions up; ids of existing nodes never
change). The tool is deterministic and idempotent: re-running on the committed state
rewrites nothing. Everything it was unsure about — unresolved labels, ambiguous city picks,
cities inferred from institution names, possible duplicate institutions, Israel-in-Europe —
is in `data/locations-review-2026-11-02.md`; fix by editing `locations.yaml` and the
`sites:` by hand (merge two institutions by moving one name into the other's `aliases`
and re-pointing its sites), and validate.py keeps the invariants (resolution, parent
chains, type order, unique ids and aliases).

## Levels

Tier labels drift across eras (NWERC moved under the EUC in season 2024 unchanged; ACPC
was renamed a Championship), so **level is derived from the graph**, never stored per
contest: WF → championship layer (flagged series) → regional → subregional → below.
Below-subregional currently exists only twice: BAPC preliminaries (2009–) and the African
national contests under the South Africa regional (2016–2019).

## Provenance

The initial import came from the "ICPC contest list / Main list" sheet
(`data/import/`, mechanical fixes logged in `CONVERSION-FIXES.md`); the problem-archive
holdings came from the "ICPC Problem Archive progress" sheet (`data/import/`,
`tools/import_problem_archive.py`, disagreements in `reports/problem-archive-import-*.md`). From this import on,
**this repo is the source of truth**; edits happen here, with git history as the audit
trail. `provenance:` and `notes:` on a contest record where facts came from;
`reports/open-warnings.md` tracks the judgment calls still open.

## The site

`tools/build_site.py` renders the catalogue into `site/` (styles, script and fonts from
`tools/site_assets/`, copied to `site/assets/`). It is built by five rules, which
`about.html` also tells the reader:

1. **One renderer per object.** Wherever it is mentioned, a contest is its id linking to
   its page, a series its id, a season `2024–2025`, a location its name, a source its
   address label linking to the *source page*, a problem set its id, a problem its name,
   a date the date linking to its day in the calendar (`calendar/<year>.html`).
2. **A link stays on the site unless marked ↗.** The address of a source is linked from
   its source page only (the address now, the Wayback Machine, our archived copy).
   Deliberate, marked exceptions: a problem's judge links, a contest's CMS links, a
   judge's own site.
3. **Three kinds of content per contest** — website, results, problems — always in that
   order and always present, with one status vocabulary: *held* (green, filled), *known
   but not held* (amber, outlined), *none* (grey), *lost* (red: dead at its address, no
   Wayback snapshot, nothing held).
4. **One anatomy.** List page: title, one paragraph, key, filter bar, sortable table.
   Object page: breadcrumb, title, status chips, facts, sections. Tables of contests
   pick their columns from one set (`CONTEST_COLS`); groups of contests (a season, a
   series, a location) show the same three counts with percentages.
5. **One word per thing**: location, level, results, problems, website, online judge,
   CMS id.

