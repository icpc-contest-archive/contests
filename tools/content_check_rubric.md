# Content check: what a reader does with one contest's pack

You are checking the sources of ONE ICPC contest against the documents themselves. For each
source: is its role right, does it belong to this contest and edition, and what facts does it
give? You read, judge and write one verdict file. You change nothing else: no catalogue file,
no git, no web.

## Input

`<pack dir>/pack.json`: what the catalogue says about the contest (name, date, location, known
problems) and its `sources`. Each source has `n`, `url`, `roles`, `scope`, `judge`, `as_of`,
`cms_page`, `note` and `copy`. When `copy` is not null, `<pack dir>/s<n>.txt` is a digest of the
copy we hold: title, headings, the largest tables (first and last rows), links, the start of the
text; for a PDF the text of the first pages; for a crawled website the file list and first page.
`copy.file` is the full copy on disk. Open it (python3, pdftotext, gunzip when it starts with the
gzip magic) only when the digest is not enough to decide — e.g. to count rows exactly, to see
the middle of a table, or to read another page of a crawled website.

A source with `copy: null` cannot be read: verdict `no-copy`, nothing else. Do not fetch anything.

## Roles (what a document IS, not where it is)

Results, from most to least information:
- `scoreboard`: per team AND per problem: solved or not, final state. Tries/times are usual but not needed: a grid (or a string of letters per team) that only says which problems were solved is a scoreboard; set `solved-only`.
- `frozen_scoreboard`: the same shape, but the state at the freeze (pending cells, "frozen", last hour hidden).
- `standings`: per team: rank and/or number solved (and maybe time), no per-problem detail. Top places ranked and the rest listed unranked (Honorable Mention) is a COMPLETE list, normal for ICPC: do not set `partial` for that.
- `rankings`: teams in order, nothing more. A list of champions/medallists/top N counts: set `partial` and give `scope` ("champions", "top 10"). An account by somebody else (news, a university's achievements page) counts when it gives the order.
Other:
- `teams`: a list of the participating teams that is not a results page (registration list).
- `web`: a page or site by the organisers or the host about this edition (the series' site as it stood for this edition counts; so does the old CMS's "past regionals" page of a contest, icpc.baylor.edu/past/.../Regionals/...). NOT web: a single results page (that is a results source), somebody else's news article, a social-media post, a university's general homepage, a CMS finder page.
- `problemset`: this contest's problems in any form: statements, a list of names, a judge's contest page.
- `problem`: exactly one problem of this contest.
- `editorial`: solutions explained (slides, analysis, write-up). An archive of bare solutions or test data is not an editorial: it is a `problemset` (material: solutions, data).
A document can have several roles (a page with the scoreboard and the problem list).
A crawled website is ONE document with the role `web`, whatever pages it contains: do not add
`scoreboard`, `teams` or `problemset` to it because the site has such pages. List those pages
under facts `inside` instead; they are candidates for sources of their own.
`none`: the document is none of these for this contest (error page, login wall, empty app
shell, unrelated page, a different contest or year).

## Verdict per source

- `confirm`: the roles in the pack are right.
- `correct`: they are not; give the right `roles` (may be `[]` = it is not a source of this contest).
- `not-the-document`: the copy is an error page, login wall, empty shell, parked domain. Say what it is.
- `wrong-contest`: a real document, but of another contest or edition. Put what the document names in facts `contest_named`, and the catalogue id it belongs to in facts `belongs_to` when you can tell (ids are `<series>-<year>`, the series as in this contest's id).
- `same-as`: add facts `same_as: <n>` when the copy is the same document as another source of this contest (identical content at another address).
- `no-copy`: nothing to read.
- `cannot-tell`: read it, still unsure. Say why.

`confidence`: `high` (I saw the thing that decides it), `medium`, `low`.
`evidence`: ONE sentence naming what you saw ("table of 87 rows with columns Rank, Team, A..J").

## Flags (set every one that applies)

- `partial`: a results list that does not cover all teams (top 10, medallists, one site).
- `solved-only`: a per-problem grid with solved/unsolved only, no tries or times.
- `outside-participants`: the board mixes virtual/unofficial/practice participants with the official teams (say whether the official ones are distinguishable).
- `combined`: one board or set shared by several contests or sites.
- `division`: covers one division/part only (give it in `scope`).
- `second-hand`: a results or contest account written by someone other than the organisers or host (news article, a team's university page, blog). Do NOT set it for problem sets on online judges or archives.
- `not-own-site`: filed as `web` but it is not the contest's own site (a host's news page, a CMS page, a social-media post).
- `mirror-differs`: an `also_at` address is plainly not the same site.
- `year-reused`: the address serves a different edition now than the one meant.
- `translated`: problem statements re-typed or translated by a third party.

## Facts (only what the document shows; never guess; omit what it does not say)

- results: `teams` (number of ranked rows), `problems` (number of problem columns), `problem_labels` (e.g. "A-K"), `top3` (team names in order, with institution if shown), `columns` (header cells), `final_or_frozen`, `has_times`, `has_tries`.
- problemset/problem: `problems` (count), `list` ([[letter, name], ...] as far as visible), `material` (any of: statements, names-only, data, solutions, package), `language`.
- web: `date` (contest date as stated), `place`, `host`, `inside` ([{"address": "...", "is": "teams|scoreboard|standings|rankings|problemset|editorial", "already_a_source": true|false}] for the pages of the crawl that are such documents; look at the page before listing it).
- editorial: `covers` (letters), `by` (jury / third party).
- any: `contest_named` (how the document names the contest and year, verbatim), `language`.

Also `contest_facts`: anything the documents state about the contest itself that differs from or
is missing in the pack (date, location, number of teams, number of problems), each with the
source `n` it came from.

## Output

Write `<pack dir>/verdict.json` (valid JSON, UTF-8), exactly this shape:

```json
{"contest": "<id>", "rubric": 3,
 "sources": [{"n": 1, "verdict": "confirm", "roles": ["scoreboard"], "scope": null,
              "confidence": "high", "evidence": "…", "flags": [], "facts": {}, "opened_full_copy": false}],
 "contest_facts": [{"fact": "date", "value": "2013-11-24", "from": 2, "pack_says": "2013-11-23"}],
 "notes": "anything a human should look at, or empty"}
```

One entry per source in the pack, in order. Then reply with ONE line:
`<contest>: <n sources> — <k confirm>, <k correct>, <k other>; <seconds spent, roughly>`.
