# Definitions and data model

This repo catalogues **ICPC contests**: contests, in the ICPC ecosystem, in the mainline
contest hierarchy of the ICPC. Operationally, a contest is *mainline* iff it is a World
Finals, or performing well in it could advance a team toward a World Finals — i.e. its
`parent` chain reaches a `wf-*` contest. Everything the CMS DB contains that fails this
test is not in the catalogue; it is accounted for in the registries instead, so that every
CMS DB entry remains *considered*.

**Qualifiers.** "Advance a team" is meant broadly. From a contest called a qualifier, such as the
North America Qualifier or the subregionals under NWERC, no team is itself qualified: universities
use the result to choose which teams they send, and the regional above hands out places to
universities by it. Such a contest is mainline, and its parent is the regional or regionals it
serves (ruling of 2026-11-25). A contest whose pages say nothing of the kind, such as a prize contest
of a province or a university, is not.

## The three stores

- `series/<series>.yaml` — the catalogue. Mainline contests only: ones that ran, plus
  `status: upcoming` for future editions. One file per series, contests in chronological
  order.
- `registry/cms-triage.yaml` — every CMS DB contest id that is **not** a mainline contest,
  with the reason: `cancelled` (no proof it happened; the CMS auto-copies contests across
  years, so ghost entries are common), `camp` (training camps), `challenge`
  (challenge-style contests), `junk` (test/garbage entries), `minor` (real contests
  outside the mainline), `structural` (hierarchy nodes, not contests), `preliminary` (an online
  first round or qualifier of a contest in the catalogue), `special` (contests for a particular
  group: women's, teens', team-formation rounds), `non-mainline` (a family ruled out of the mainline
  as a whole, such as the Caribbean qualifier from 2022).
- `registry/non-mainline.yaml` — real contests that exist outside the hierarchy: university
  opens, and prize contests of a province or a university from which no team advances (the Alberta
  and Lethbridge contests, ruling of 2026-11-25). Some have a CMS record; the ledger lists those ids
  as the registry's. Reference material, not catalogue members: no contest
  page, not counted as contests anywhere (an online judge's page counts them apart). Their
  sources are in the resource graph like any other and have source pages (ruling of 2026-11-24).

**The date of a contest** is the day the contest itself ran, and a contest that ran always has one
(ruling 2026-11-25). When its documents give only a span of days ("5-6 November", a three-day
event), the day is taken in this order: a schedule, results header or report that names the contest
day; else the day the same series used in neighbouring editions whose contest day is known (East
Siberia: the middle day of three; the Atlantic Canadian preliminary: the Friday that opens the
conference); else the last day of the span, or the second to last for a span of four days or more.
A day chosen this way says so in the contest's provenance ("the contest day is not confirmed"), so
that it can be confirmed or corrected when a source is read; `data/span-dates-2026-11-25.json` lists
them. Local rounds held on different days are dated by the last of them. A contest that sat a shared problem
set takes the day of the set's session (the day on the set's cover, or the day its other members
hold) when its own documents state no day or put it a day or two off; a member whose own document
names another day keeps it and is listed for a look (`data/shared-set-dates-2026-11-25.json`). Where a document names the contest day and the catalogue held another (ruling of 2026-11-26): a
document of the contest itself wins (the statement's cover or running header, the organisers'
schedule or report, the judge's start time read in the local time of the site); a third party's
page (a judge's mirror, a note on a problem archive, a participant's post) changes the day only
where no document of the contest says otherwise, and the day is then marked not confirmed; a gap
of a week or more is looked into before anything changes (`data/printed-dates-2026-11-26.json`).
This is the catalogue's
rule; a source description still reports only what its document says, and a span there gives no
contest date.

**Rounds are contests.** Two rounds of one event are two contests, since they have different problems
(ruling of 2026-11-24): each has its own entry, date, results and problem set, and the earlier one
advances to the later. The Northern Eurasia Finals of 2020-21 are `nerc-online-2020` (13 December
2020) and `nerc-2020` (the onsite round of 4 April 2021).
One exception (same ruling): Egypt's qualification days from 2022 on are one contest a year,
`egypt-qualification-YYYY`, with one CMS id, one sitting (`sites`) and one standings source per day.
Each day seats a different group of universities, and the days are believed to share one problem set.

**Asia's national contests.** In Asia a regional is open to teams of other countries: one region
with no political boundaries until 2009, and from 2010 a result counts toward the World Finals only
in the team's home sub-region (the Asia rules of 2001 to 2019). A national contest of a country that
hosts a regional advances to that regional. One of a country with no regional that season advances
to the regionals its schools entered, read from the standings and marked `inferred` in its
provenance; where none is found the parent stays empty (ruling of 2026-11-25). Naming every Asian
regional would state the rule, not where the teams went.

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
  serves: `{url, roles: [...], as_of?, judge?, archived?, fetched?, url_state?,
  url_checked?, note?}` (see *Resources* below). Roles: `web` (the contest website; another
  address of it is a `web` source of its own), the results ladder in decreasing information order
  `scoreboard` (full, per-problem) > `standings` (totals only) > `rankings` (order only) >
  `teams` (a team list), and beside it `frozen_scoreboard` (the scoreboard as it stood at the
  freeze: ancillary, not a level of the ladder — see *Coverage*),
  `problemset` (the contest's problems, in whatever form the document gives them; `contains:`
  says which: any of `names`, `statement`, `data`, `solutions`, `package`),
  `problem` (one problem; `problem: <letter>` says which, so that the source's page can link it), `report` (an account of the contest that is neither its website nor a
  results list: a news item, a press release, a history page; common for the early years, and often
  the only proof that a contest ran; added 2026-11-14), and `editorial` (solutions explained after the contest: the jury's
  solution slides or problem analysis, or somebody else's write-up; added 2026-11-14 — it names
  the problems by letter, so it also shows what the contest's problems were when the statements
  are lost). A role says what the document is, not where it is: a problem
  set or problem that is on an online judge carries `judge: <id of judges.yaml>`, and
  that is all that marks it (the `judge_page` role was dropped 2026-11-14; the 2,609
  sources that had it are problem sets). A page that is both the results and
  the problem set is one source with two roles. `archived` references the (separate)
  archive repo by `<contest-id>/<artifact>/<fetch-date>`. `none: [role, ...]` lists
  roles confirmed to have no source; a role in neither is not yet researched.
  `tools/catalogue.py` is the one reader (`by_role`, `has_role`, `best_result`, …).
- `archived` is a **list**: one address is often captured under several roles or in
  several runs, and every capture pointer is kept. Two sources that are the same
  document at two addresses are not linked in the data (`also_at` was dropped 2026-11-14): the site
  reads it off the copies, which have the same checksum, and says so on the source page.
- `sites` — where the contest was held: `[{location: <locations.yaml node id>, name?, date?,
  type?: administrative|online}]`, one entry per site (see *Locations*). The free-text
  `location` string stays alongside until `sites` covers every contest.
- `provenance` — free-text lines recording where the entry's facts came from: where a
  date was read, proof that a contest with no results ran. Kept in the data, never shown
  on the site or in its published dumps (ruling of 2026-11-16: where data comes from is
  not published).
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

### Sources (2026-11-13: one model; 2026-11-16: an address at a time)

A **source** is an address at a point in time: one document a contest points at, what the address
served for that contest. It is the document that matters, not the address: addresses die and get
reused, so a source that is no longer at its address carries the time it is meant at (`as_of`).
One entry of a contest's `sources:` is one source, and its `roles` are its **type**.

The same document can be found in up to **three places**. The site shows the three together,
always in this order and under these names, wherever a source is listed (`avail()` in
`tools/build_site.py`). One vocabulary, one colour per kind of answer, the same for every mark,
chip, pill, key and filter:

| place | green: it is there | amber: there, in doubt | red: confirmed not there | blue: not done yet | grey: does not apply |
| --- | --- | --- | --- | --- | --- |
| **address** — the address now | live | changed · blocked · unverified · empty | dead · replaced | not checked | |
| **Wayback** — the Wayback Machine | snapshot | bad snapshot | no snapshot · excluded | not checked | n/a |
| **archive** — our archive | held | bad copy | lost | not captured | n/a |

The label of a mark is the place and never changes (it is never struck through); the colour is the
answer. *blocked* = the server answered but turned our fetcher away (HTTP 401/403, a certificate it
does not trust): the live check records `dead`, the site shows what it is, and it never counts
toward *lost*. *unverified* = the address answers and there was nothing to compare the page with
(the checker's `unknown`). *bad* (snapshot or copy) = something was stored, but it is not the
document: an error page, a login wall, the shell of an app (`archive/tools/audit_not_there.py`
decides; `content_caveat` records it). *lost* = gone from its address, no snapshot, no copy; *not
captured* = no copy yet while there is still somewhere to take one from. *n/a*: the Wayback Machine
for a standings page of the ICPC CMS (an app: a snapshot of it shows nothing), our archive for a
page that is empty. *changed* is judged on the tables of a results page before the whole page
(`archive/tools/capture_urls.py` 2.20, `tools/rejudge_changed.py`): a scoreboard whose table is what
it was is live, whatever the site did to its header and menus.

A **copy** is what we hold: a capture of one page, or a crawl of a website, taken from the address
or from a Wayback snapshot, with the time it shows. Only the **current copy** is shown and linked,
the one that counts: the newest the public replay serves, else a crawled website, else the newest
capture (when the address has since changed, the copy nearest the source's time). Earlier copies
stay in the archive, for debugging, and are not listed on the site; nor are the files that were
fetched and judged not to be the document. The words *snapshot* and *capture* remain in the tools
(a snapshot is an address at one time; a capture is one stored fetch), and the code and the
paragraphs below still say *locator* for the address and *resource* for an address at a time.

**One address, several sources.** Most addresses are cited by one contest: address and source
coincide, and the source's id is the address's (`source/<id>/`). An address several contests cite
is one source per time it is meant at (`index_docs`): contests that name the same `as_of`, and
contests of one season (a joint contest, a shared problem set), mean the same document and share
the source; a page reused year after year is a source per year, each with its own page, its own
copies, and links to the others (*same address, other times*). The time of a citation is its
`as_of`, else the Wayback snapshot its own copy was taken from, else none (the address as it is,
which keeps the address's id; a source with a time has an id of its own, the hash of address and
time). 170 of 11,234 addresses are several sources (2026-11-16).

**What a source page says** is facts, each one a link, and no free text: its type (to the list of
sources of that type), its contest, and for a problem set, problem or editorial the problem set
and, with `problem: <letter>`, the problem; what it holds (`contains`), the format of the current
copy, and where it is found. `note` and `notes` fields, the evidence of a check and the internal
ids are not shown anywhere on the site (ruling of 2026-11-16): they say where data came from and
how, which is bookkeeping.

**ICPC standings** are the standings pages of the CMS
(`https://icpc.global/regionals/finder/<abbrev>-<year>/standings`). They have no role of their own
(the `icpc_standings` role was dropped 2026-11-14): such a page is filed by what it holds —
`standings` when its rows give problems solved, `rankings` when they give ranks only, `teams` when
they give neither — and that it is the CMS is read off its address (`catalogue.is_cms`). A page with
no rows holds nothing and is not a source; `data/icpc-standings-empty.json` records those pages and
when they were asked. The CMS is formally the official result. It is not often wrong, but it can be,
and where it disagrees with another source it tends to be the one that is wrong.
The pages are an app, so a fetched page is an empty shell: their copies are rendered from the open
API's data instead (`tools/bake_icpc_standings.py`, source `icpc-api-archive`, time = the dump's
date), and the capture rounds leave them alone. `reports/icpc-standings-mapped-2026-11-14.md` lists
what each page became.

**What makes a source right (rulings of 2026-11-14).** Every source must be about this contest and
this edition, hold what its role says, and say with `scope` when it covers only a part.

- `scoreboard`: per team and per problem, solved or not. Tries and times are usual but not needed: a
  grid that only says which problems each team solved is a scoreboard, the weakest kind.
- `frozen_scoreboard`: the same shape as it stood at the freeze. A page with final totals and a
  frozen grid has both roles.
- `standings`: per team, rank and/or problems solved, no per-problem detail. A list that ranks the top
  places and gives the rest unranked (Honorable Mention) is complete: that is normal for ICPC
  standings, not a partial list.
- `rankings`: teams in order, nothing more. A list of the champions or the top N counts, with `scope`
  saying what it covers (`champions`, `top 10`). An account by somebody else (a university's
  achievements page, a news item) counts when it gives the order.
- A board that mixes outside participants (virtual, unofficial, practice) with the official teams is a
  results source only when the official teams can be told apart on the page.
- A page that covers several contests or rounds is a source of each contest it covers, with `scope`
  naming the section when the page has separate ones.
- `web`: a page or site by the organisers or the host about this edition (the series' site as it
  stood for this edition counts, and so does the old CMS's "past regionals" page of a contest). Not
  `web`: one results page, somebody else's news, a social-media post, a university's general
  homepage, a CMS finder page.
- `teams`: a list of the participating teams that is not a results page.
- `problemset` / `problem`: about this contest's problems, in any form, an archive of bare solutions
  or test data included. `editorial`: explains how to solve them.
- A source that turns out to be another edition's document moves to that contest when the document
  names it and the contest exists; otherwise it is removed and listed.
- A copy that is not the document (an error page, a login wall, an empty list, an app's shell) is
  marked empty and captured again; when the address itself holds nothing, the source goes, as the
  empty CMS standings pages did.

**An address that now shows another year (ruling 16).** Many contest sites live at one address
and are overwritten each season. When our copy of such an address shows a different edition, what
happens to the source depends on what the address once held: if the Wayback Machine or our archive
has the right edition, the source stays and `as_of` names that capture; if the address was this
contest's site but no copy of that edition survives, the source stays and is shown as lost; if
nothing shows the address ever served this edition, the source is removed. A copy of the wrong
edition is never by itself a reason to remove such a source. The content check lists these cases
(`data/content-check/<run>/lists/year-reused.json`) instead of acting on them.

**Sources: `scope`.** A source that covers one part of a contest, not all of it, says which:
`scope: Division 1`. `tools/label_scopes.py` sets it from the archived capture (the Kattis filter
heading, the page title), the address (`/div2/`, `acpc20d1.kattis.com`) or the note; the site shows
it beside the role.

**Upcoming.** `status: upcoming` ends when the contest's date has passed and a result source or a
judge page shows it ran (ranked standings in the ICPC CMS count). A contest that is one region's
view of a larger one (`subset_of`) follows the larger one. `tools/apply_ran_2026.py` did this for
autumn 2026 from a frozen probe of the CMS and of last year's addresses with the year moved on.

### Source descriptions (2026-11-16)

A source whose copy we hold can carry a **description**: one to three paragraphs on what the
document is and what it contains, with the facts the document states about itself (title,
language, the contest date it prints, teams and problems shown, per-problem times and tries,
pages). Descriptions are not in the series files; they live one file per contest in
`data/source-descriptions/<series>/<contest>.yaml` (format and rules in the README there) and
the source page shows them under *What it contains*.

- A description is about the **copy**, written from the copy and nothing else. It is not a claim
  of ours about the contest: where a document is wrong, so is its description.
- A source has a description only when a copy is held and the reader took it for the document it
  is filed as. No copy, an error page, an empty application shell or another contest's document:
  no description, and the reading is listed for a ruling in
  `data/describe/<run>/second-reading.json`, never applied on its own.
- `contest_date` in a description is the day the contest ran **as the document states it**. A
  span of event days ("5-6 November") with no statement of which day the contest was on gives no
  date; only a contest that itself ran over several days takes its first day.
- A document fact can differ from the catalogue (`date`, `location`). Differences are listed in
  `data/describe/<run>/contest-facts.json`. One case is written (a ruling of the first round): a **blank**
  `date` or `location` is filled from a document that states it, with high confidence, when no
  other document of the contest disagrees, and the contest gets the provenance line
  `<fact> read from <address> (description round <date>)`. A value already in the catalogue is
  never overwritten.
- Descriptions say what a document shows, not where our copy of it came from.
- How they are made: a reader agent writes, a second agent checks every claim against the copy
  and corrects, and about 3% are checked a third time by an independent checker whose findings
  are applied (`tools/describe_pack.py`, `describe_agent.md`, `describe_rubric.md`,
  `describe_revise_agent.md`, `describe_check_agent.md`, `describe_fix_agent.md`,
  `describe_apply.py`). `tools/validate.py` checks that every description file belongs to a
  contest of that series and that each entry is complete; a description whose address is no
  longer a source of the contest is a warning.
- An entry belongs to the copy named in its `copy`. When a source gets a new copy, it is read
  again; a hand correction is made in the file and stays until then.

## Coverage

What we hold of a contest is one **coverage record**, worked out in one place
(`tools/coverage.py`, `Coverage.record`) and read by every page of the site. It tracks four
things (rulings of 2026-11-15). **Have always means we hold a copy** — a copy that is the
document, the `ours` of a source. An address we only know is a link, never counted as held.

- **Results** — one level per contest, the highest it reaches on the ladder
  **scoreboard > standings > rankings > team list > none**. Only the highest matters. The record
  has the level we hold (`results`), the level any source gives (`results_known`), and `fetch`:
  the known level when it is better than the held one (a copy is wanted). Beside the level, not
  on the ladder: `frozen` (a frozen scoreboard, held or link only — it says how things stood at
  the freeze, not how the contest ended, so a contest whose only result is a frozen scoreboard
  has level none) and `partial` (the held level is reached only through sources with a `scope`:
  one division, the top places; two or more division scopes together count as the whole).
- **Problems** — not a ladder: six kinds, each on its own. *Problem metadata* (the problem
  list itself, then `names`, `letters`, `short_names`, `uuids`: all / some / missing, from the set's
  problem list), and the material
  `statement`, `data`, `solutions`, `package`, `editorial`, each **all / some / link only / not held /
  not recorded**. A complete `package` implies statement, data and solutions (never editorial);
  that is derived, and `validate.py` refuses a set that says otherwise. Where the material comes
  from does not matter: a kind counts when the problem archive holds it (the set's `statement:` …
  `package:`), or when a `problemset`/`problem` source of any contest that used the set
  `contains:` it and we hold a copy of that source (a `problemset` source gives it for all
  problems, `problem` sources for some). *link only*: such a source is known, we hold no copy.
  A `problemset` source on an online judge is always link only for material: our copy of it is the
  judge's list page, not the statements or data. A problem's own page on a judge is different: when
  we hold a copy of it (or of the statement file behind it, `statement_url` on the problem's judge
  link) it is a `problem` source of every contest that used the set and counts like any other
  (ruled 2026-11-22/23; tools/problem_sources_from_judge_copies.py). Judge links we hold no copy of
  stay links. *not recorded*: a source is known, but its `contains:`
  is not. `editorial` is have-or-not per set, from `editorial` sources.
  `contains:` was filled on 2026-11-15 from the content check's reading of our copies
  (`tools/fill_contains.py`); `[]` means read, and it holds none of these.
- **Website** — **held / no copy / no address / none**. Held = the contest has a `web` source
  and we hold a copy of it (a crawl counts only for the addresses it holds: its first address, or
  one of its pages). Wanted has two reasons, because the work differs: `no copy` (the address is
  known) and `no address`. `none` (`none: [web]`: the contest had no website) is not wanted.
- **Contest metadata** — a few kinds, each **have / missing / none**: `name`, `date` (the full
  date), `location` (placed in the location tree), `cms` (CMS id; `[]` = none). *none* means
  looked, and there is none: it is not missing. What a contest advances to (`parent`) and the
  editions before and after it (`next`) are **not** coverage (ruling of 2026-11-15): "none" is a
  valid answer for them, so they are never missing, only possibly wrong — a matter for
  fact-checking (review mode), not for coverage.

Everything is **counted in contests**: "statements: all" is the number of contests for which we
hold every statement, not a number of problems. And *recorded* (problem metadata: what the
catalogue lists) is not the same as *held* (material): a contest whose statement we hold can still
have its problems unlisted.

**Facets.** The questions above are one list, `coverage.FACETS`: 16 facets in five groups —
Results (1); Problem metadata (the problem list, names, letters, short names, UUIDs); Problems
(statements, test data, solutions, packages, editorial); Website (1); Contest metadata (name, full
date, location, CMS id) — each with its answers in order, best first. Every view on the site is
drawn from that list with one colour vocabulary (`build_site.facet_q`), which the marks in tables
share: held (green), partly held or a lesser result (lime, amber, orange: the further from green,
the less), link only: known at an address with no copy (blue), a hole (white: *not held* for
material, *missing* for metadata), a source known but its contents not recorded (hatched), *none*:
there is none to have (grey — not a hole). The words are fixed (ruling of 2026-11-24): *none*
always means there is none to have; *wanted* is everything short of the best answer, the
worklist of a facet (a filter value of its own, `statements=wanted`). Website answers: held, no
copy, no address, none.

**Every category is a link, and it is a list of contests.** The contest list
(`contest/index.html`) has a filter for every answer, addressable by name in the page address:
`contest/index.html#f:status=ran&region=Europe&website=wanted`. Names: `country`, `series`,
`region`, `level`, `season`, `era`, `status`, `loc` (a node of the location tree; set by links
only), `results`, `fetch`, `also` (frozen scoreboard, partial result, lost source), `problems`
(the list), `statements`, `data`, `solutions`, `packages`, `editorial`, `pmeta`, `website`, `meta`.
Filters combine. Anything on the site that counts contests — a segment of a bar, the label under
it, a number — links to the list filtered to exactly those contests and carries its count
(`data-n`); `tools/check_coverage_links.py` follows every such link of a built site and compares.
Coverage counts contests that ran, so every such link carries `status=ran`. A category that is
about a source (frozen scoreboard held, a source is lost) still opens contests: the source is one
click further, on the contest's row.

**Where coverage is shown — one design, everywhere.** A group of contests (the whole archive
on `coverage.html`, a season, a series, a location with three or more contests) shows its coverage
the same way and in the same order (`build_site.group_nums`, `coverage_section`): the headline
numbers; then the panel, a bar per facet with its answers as linked labels, in three columns
(results, website and contest metadata; problem metadata; problems); then *where* it is missing
along the group's own axis — the archive and a location season by season (a strip per facet), a
series edition by edition, a season contest by contest (a square per contest and facet). The
members of the group (editions, the advancement tree, contests) come after. A table whose rows are
groups (the series, season and location lists, the regions and series on `coverage.html`) carries
the same bars in small (`group_cells`). A contest's page has its own card: a pill per facet and,
in words, what is wanted. `wanted.html` counts what is missing by region, and `grid.html` colours
every contest by any one facet (`grid.html#by=data`).

## Resources

Three things used to be called "URL"; they are distinct.

- A **locator** is a URL as an *address*, with no time attached:
  `http://icpc.baylor.edu/past/EarlyYears.html`. The catalogue holds locators only —
  `sources[].url`. A locator has a *health*
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
source (`source/<id>/`: the address and its time, its type and contests, the three places it can be found and the one copy that counts;
the old `locator/<id>/` and `locator/<id>/<ts>.html` paths redirect there). `tools/build_resources.py` joins catalogue, archive index, website index,
live-check verdicts and replay index into `data/resources.json`, which those pages render from.

**Presentation.** A resource displays as **`url (at time)`** everywhere (ruling of 2026-11-24), at the precision known —
`2011-01-02 18:36`, `2026-04-15`, `2011`; a bare locator displays as the URL. Everywhere
but its own page a source links to its source page; that page opens the address as it is
(*open the address*), the Wayback snapshot pinned to `as_of` (or the copy's snapshot) when
known and the calendar otherwise (*open the snapshot*, *look for snapshots*), and our
current copy (*open our copy*). Nothing ever links to a Wayback URL of a Wayback URL.

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
  `package`, with `counts:` giving the exact number for kinds marked partial. These four say
  what the problem archive holds; what we hold from anywhere is the coverage record
  (*Coverage*).
  `count` is the number of *distinct* problems: a problem used in two divisions counts once
  (ruling 2026-11-15).
  `contests:` lists the contests that used the set, each with its own `letters:` map
  (letter → problem id; letters can differ between contests sharing a set);
  `labels: [A, B, …]` on a member holds the letters alone, read off the contest's scoreboard,
  while the problems are not listed (a scoreboard has a column per problem, so a contest whose
  scoreboard we hold always has at least a `count` and `labels`: tools/letters_from_scoreboards.py);
  `letters: unknown` on the set says no map is known for any contest. A contest whose
  divisions (or rounds) had problem sets of their own has `divisions:` instead of `letters:`
  — division name → letter map, in the divisions' order; the site shows such a problem's
  letter as `A/N` (its letter in each division, `–` where it was not in that division). `problems:` lists
  the problems when known (`id` = internal permanent `p-xxxxxxxx` id, the page key;
  `uuid` = the package's `problem.yaml` uuid, the same across sets that reuse the
  problem; `name` — the title in the organisers' statement where we hold it, which replaces
  a judge's short title (ruling 2026-11-15); `other_names` — the other titles the problem
  goes by (the judge's, or the statement's where `name` is the archive package's); `short_name`, `have` (subset of statement, data, input_validator,
  output_validator, solutions, package), `status: private`, `judges`, `notes`). When the
  list is present the holdings must agree with it (validate.py checks).
- **Judges.** `judges.yaml` at the repo root is the registry of online judges (id, name,
  url, `problem_url` pattern, status, `closed` date — the ICPC Live Archive closed; a closed judge's links open Wayback snapshots, an open judge's go to the problem as it is now). A
  contest's judge *pages* are its `problemset` sources that carry `judge: <id>`; a
  problem's judge links are its `judges: [{judge, url, id?, as_of?}]` list. Both refer to
  the registry by id.
- **Live Archive links** (`judge: livearchive`; the site is gone, links open its Wayback
  snapshots, ruled 2026-11-22). `id` is the problem number everyone cites; the address carries
  the Live Archive's internal page number, which is *not* `id - 1999` (that holds for 57 %).
  The map between them is `data/livearchive-problems.json`, read off Wayback copies of the
  Live Archive's 767 category pages plus single problem pages
  (`tools/build_livearchive_map.py`); every tool that writes such a link takes the address from
  it (`tools/livearchive.py`), and `validate.py` refuses a link whose page is another problem.

**Shared sets.** A set sat by several contests has an id of its own and a `name`: `latam-<year>`
for the Latin America regional (every site sits the same problems; a site with no list of its own
is a member without letters), otherwise the member series joined in alphabetical order
(`nordic-ukiepc-2013`, `scusa-seusa-2020`). The set the Northern Eurasia regionals share is the
Northwestern Russia regional's and keeps that contest's id, `north-russia-<year>`, with no `name`
(ruling of 2026-11-25). A problem list that turns out to be another contest's (a qualification's, an
online round's) moves to that contest's set; where the contest is not in the catalogue the list is
taken off and kept in `data/problem-lists-of-other-contests-2026-11-26.json` (ruling of 2026-11-26). A lighter
version of that set, sat by some of the regionals on the same day, is a set of its own,
`north-russia-light-<year>` (2007, 2017): it has the same titles, but several of its problems are
different problems, so the same titles do not show the same set. Problems whose statements are the
same keep one id in both sets. A contest placed on the full set by a standings header alone carries a
`note` saying that it is not confirmed which of the two it sat (ruling of 2026-11-26). When separate sets turn out to be one,
`tools/merge_problemsets.py` merges them: the set's `aliases` keep the ids of the sets it replaces
and each problem's `aliases` the problem ids it replaces. The site redirects those addresses, and
`validate.py` refuses an alias that is also a live id. The first merge (2026-11-12) turned 87 sets
into 20; `reports/problemset-merge-2026-11-12.md` lists them and what was left alone.

**Shared problems.** Sets that stay separate (different letters, different contests) can still share
a problem. It then has one problem id and one row in each set: the rows carry the same judge links,
each keeps its set's title, and the other titles are under `other_names`. Two rows are the same
problem when they have the same uuid or point at the same page of an online judge; where the titles
differ, two judges must agree. `tools/unify_shared_problems.py` does this (ruling of 2026-11-26; 335
problems the first time) and lists what it left alone in `data/shared-problems-2026-11-26.json`;
`validate.py` refuses rows of one id that disagree.

**Judge links and sources.** A problem's link to an online judge is a `problem` source of its
contests when we hold a copy of the page or of the statement file behind it (ruling of 2026-11-23,
`tools/problem_sources_from_judge_copies.py`). A problem we hold no statement of, and that has no
source of its own, gets one of its judge links as a source to be captured (ruling of 2026-11-27,
`tools/problem_sources_for_missing_statements.py`); its other links stay links. The statement file
of a whole set kept on a judge (a Codeforces gym's attached PDF) is a `problemset` source, and a
held copy of it counts as the set's statements; the judge's page that lists the set does not.

`tools/fill_letters.py` gives a problem its letter when the set is complete and exactly one letter
and one problem are left; nothing else about letters is inferred.

The site renders a page per set (`problemset/<set-id>.html`), per problem
(`problem/<pid>.html`, aggregating every appearance), the set index
(`problemset/`) and the judge registry (`judge/`). The two pages divide the facts: the
**contest** page's Problems section says which set it used, lists the problems with this
contest's letters, and lists the sources (published set, judge pages); the **set** page
says what we hold, problem by problem, wherever it comes from (the problem archive, or a
source we hold a copy of). Per-problem holdings (`have`) are recorded for few sets;
elsewhere a problem's holdings follow from its set where the set is all-or-nothing for a
kind: held for every problem (in the archive, or in a held problem-set source) → held,
`none` → not held, `partial` → not recorded. A problem's own held statement copy (a
`problem` source) counts as its statement.

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
  "Administrative Site Location", staff, hidden teams, placeholder and registration groups:
  recorded as `{type: administrative}` with no location; `tools/place_sites_2026_11_13.py`
  marked 35 more and placed 75 sites whose name was a known place under a division label, an
  alias, or an institution the tree lacked) or `online` for teams competing remotely (with a location when the
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

**Shown on the site.** Sites of type `administrative` (the CMS's staff, guest and bookkeeping
groups) stay in the data and are never shown. A contest with no real site shows the city its CMS
record points at, marked *inferred*.

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

A provenance note is free text and nothing reads it. A document that data was read from is therefore also recorded as a
**source** of the contest, which gives it a source page, lets the search box find it and has the capture rounds archive it. For
problem names read from a published statement, `tools/apply_statement_titles.py` does this itself, and
`tools/add_statement_sources.py` backfills it from the sets' provenance notes: each becomes a `problemset`, with `judge: <id>` when it is a problem list on a judge of
`judges.yaml`; a Wayback address is written as the original address plus `as_of`, and a GitHub
address with its branch, not `HEAD`.

## The site

`tools/build_site.py` renders the catalogue into `site/` (styles, script and fonts from
`tools/site_assets/`, copied to `site/assets/`). It is built by five rules, which
`about.html` also tells the reader:

1. **One renderer per object.** Wherever it is mentioned, a contest is its id linking to
   its page, a series its id, a season `2024–2025`, a location its name, a source its
   address label linking to the *source page*, a problem set its id, a problem its name,
   a date the date linking to its day in the calendar (`calendar/<year>.html`).
2. **A link stays on the site unless marked ↗.** The address of a source is linked from
   its source page only (the address now, the Wayback snapshot that shows the document — never
   the calendar when a snapshot is known — and our copy).
   Deliberate, marked exceptions: a problem's judge links (unless the address is a source
   of a contest, a copy of the problem's page we hold: then the logo opens that source's
   page), a contest's CMS links, a judge's own site. Problem set and problem pages list the
   sources their contests cite for them (ruling of 2026-11-24).
3. **Three kinds of content per contest** — website, results, problems — always in that
   order and always present. **One set of colours everywhere** (every pill, mark, bar and
   square; ruling of 2026-11-16): green = we hold it / it is there; amber = partly, or in doubt;
   blue = known but not ours yet, or not done yet (pending work); red = lost, confirmed not
   available; grey = none exists, or does not apply; white = missing and wanted; hatched = not
   recorded. The card at the top of a contest, problem set and source page is the same component.
   A source's availability is one unit of three marks, `address · Wayback · archive` (above, *Sources*),
   shown wherever a source is listed; the checks behind it stay in `data/resources.json`
   and are not shown.
4. **One anatomy.** List page: title, one paragraph, key, filter bar, sortable table.
   Object page: breadcrumb, title, status chips, facts, sections. Tables of contests
   pick their columns from one set (`CONTEST_COLS`); groups of contests (a season, a
   series, a location, the whole archive) show the same numbers strip (`group_nums`): how many
   contests ran (+ upcoming), then the six headline counts, each with its percentage.
5. **One word per thing**: location, level, results, problems, website, online judge
   (never just "judge" in a label or heading), CMS id, type (of a source), address · Wayback ·
   archive (the three places).

## Review mode

Review mode lets a reader confirm, correct and add to what the catalogue says, on the page that says it. It has three parts.

**Units.** A unit is one claim that can be right or wrong on its own. `tools/review_units.py` holds the one list (`UNITS`: 43 units on
seven kinds of object) and the helpers `build_site.py` wraps them with: `U()` for a unit that is on the page, `row()` and `line()` for
one the page does not show, `slot()` for the place where one more can be added. A page is reviewed as it reads: a fact is a unit wherever an
object's page states it in its facts, also when the catalogue stores it on another object (a contest's previous edition is the other
contest's `next`; `previous`, `fed_by`, `views` and a problem's `appearance` are such units, and reading a review translates them to
where the fact is stored). Tables that list many objects carry no units. The
marker carries the unit's key, the catalogue's value and, when the object has several, which one:
`<span class="u" data-u="date" data-v="2017-10-21">`. The object is named by `<h1 data-at="contest/alberta-2017">`. Rows and slots for
units without a value have the class `rvo` and are hidden unless review mode is on. The build prints how many units it wrote per kind
of page; a unit key that is not in `UNITS` stops the build.

**The script.** `tools/site_assets/review.js` (with `review.css`) is loaded only while review mode is on. It puts ✓ (confirm),
✎ (correct) and + (add) on the units, keeps the marks in the browser's local storage (`icpc-review`) across pages and tabs, and at
"Submit review" hands them as JSON to the issue form `review.yml` of the repository named in `review_units.REPO`: in the link itself
when they fit, by copy and paste when not. Nothing is sent from the site itself.

**Open or not.** `review_units.OPEN` is False until that repository and its form exist: no Review button in the header, the About page
unchanged. A link ending in `?review=1` switches review mode on for that browser regardless, which is how it is tried before it opens.

A review travels as JSON, grouped by page so that it is short, one fact per line:
`{"review": 2, "site": <build day>, "count": n, "confirm": {page: {unit: value}}, "correct": {page: {unit: {"saw", "to", "why"}}},
"add": {page: [{"unit", "of", "to", "why", "file": {name, size, sha256}}]}}`, with only the parts that apply. A page is `kind/id`. A unit
that an object has several of is written `unit which-one`, such as `letter p-ec3a0975`; a site is named by itself.
A review that names files starts with a `"reminder"` line for the reviewer.

A review whose link stays within 4,500 characters is carried by the link, which fills the form's box. GitHub keeps a link of about 5,000
characters through its sign-in page, loses the review from a longer one, and refuses links from about 7,100 (measured 2026-11-13; not
documented). A larger review is copied and pasted, and one too large for a single issue is split, each part carrying `"part": [k, n]`.
