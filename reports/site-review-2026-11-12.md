# Site review of 2026-11-12 — what changed, what is open

One working session: the four blocked judges retried, the missing World Finals dates found,
a data cleanup, and the site rebuilt around consistent objects. Tools:
`tools/import_qoj_tree.py`, `tools/cleanup_2026_11_12.py` (steps A–I), `tools/build_site.py`
(rewritten), `tools/site_assets/`.

## 1. Judges that were blocked

| judge | reachable from a browser | needs an account | outcome |
|---|---|---|---|
| QOJ / Universal Cup (qoj.ac) | yes — the Cloudflare check passes in a normal browser | no for the ICPC category tree; **yes** for a contest's problem list (login behind a human check) | **525 contest pages** applied as `judge_page` sources on 512 contests (72 had no judge page before) — `reports/qoj-tree-2026-11-12.md` |
| vjudge | yes, no account | no | nothing recorded: its contests are user-made replays pointing at other judges |
| beecrowd | only the login page | **yes** (free; e-mail or social sign-in) | nothing reachable without one |
| PTA 拼题A (pintia.cn) | public dashboard only | yes, and probably not enough: contest sets look visible only to enrolled accounts (not verified) | nothing; its China regional sets are on QOJ, Codeforces gym, Luogu, NowCoder |

Open after the QOJ import:

- **Five contests marked upcoming have their set mirrored on QOJ, so they ran**: chengdu-2026,
  xian-2026, naq-2026, rmc-2026, ukiepc-2026. Their QOJ pages are held back until the status
  and date are set (the publication rule forbids problem data on an upcoming contest).
- **Three QOJ contests have no catalogue entry**: yinchuan-2020, ctuo-1995, ctuo-1996.
- **tehran-online 2023** (qoj.ac/contest/1166): a second, online Tehran regional next to
  tehran-2023 — which contest is it?
- **Per-problem QOJ links** need a logged-in pass over the 525 contest pages.
- QOJ pages cannot be fetched by the capture tools (Cloudflare 403 to scripts); they will show
  as dead/blocked in a capture round.

## 2. World Finals dates

Sixteen editions had no date. Fifteen are now dated from our own captures of the ICPC
headquarters pages (`icpc.baylor.edu/past/EarlyYears.html`, the 1998 standings), each with
the page's line on `provenance`:

1979-02-21 · 1980-02-13 · 1981-02-25 · 1982-02-10 · 1983-02-16 · 1984-02-15 · 1986-02-05 ·
1987-02-18 · 1989-02-22 · 1990-02-21 · 1992-03-04 · 1995-03-01 · 1996-02-17 · 1997-03-02 ·
1998-02-28

**1985-03-13 is not from a primary source.** EarlyYears gives no day for 1985. CLIST's
listing of icpc.global results says March 13, 1985; that is the Wednesday of the conference
week in New Orleans, and every finals 1977–1995 with a known date fell on a Wednesday. The
CMS itself has no dates for the backfilled finals (ids 9875–9896) — these sixteen plus the
six already known could be entered there.

## 3. Data cleanup (`tools/cleanup_2026_11_12.py`)

- **World Finals locations.** 1977–1998 were not placed in the location tree at all; 1999–2027
  were placed wrongly: the CMS clones each finals from the previous one, so staff/guest groups
  kept an earlier host's address (every finals since 2019 said Beijing, 2004 said Dumai). The
  host city is now the first site of every finals 1977–2026; 125 stale group locations dropped.
  New nodes: Detroit, Indianapolis, New Orleans, Phoenix, Nashville, United Arab Emirates, Dubai.
- **Six pseudo-institutions removed** (NAC Guests, NAPC Guests, NAC Technology, NAC Media, NAC
  Operations, RCD) — CMS groups, not places; their sites now point at the city.
- **Seasons** filled for the 70 contests that had none (alberta, lethbridge, naq, nzpc,
  caribbean-2009) from the series' naming rule. This is why their problem sets showed no season.
- **Notes moved from problem sets to contests** (122 sets; `reports/set-notes-moved-2026-11-12.md`):
  "No date, no teams", "2 divisions", "Strange date?", "Also CMS:N" are about the contest.
  A "no date" remark was dropped where the catalogue has a date by now (20).
- **`cms_status: pre-cms` dropped** (133 contests, schema, DEFINITIONS): `cms_ids: []` says it.
- **World Finals series: `region: International`** (schema enum extended).

Not done, worth a pass: 258 contests that ran have no location of any kind, 49 have only a
line of text ("(SoCal)", "Texas Tech"), and other series may carry cloned site locations like
the finals did (a text-vs-tree comparison flagged 47 contests, mostly false alarms).

## 4. The site

Rules (DEFINITIONS.md, *The site*; told to readers on `about.html`): one renderer per object;
a link stays on the site unless marked ↗ and a source's address is linked from its source page
only; three kinds of content per contest with one status vocabulary; one page anatomy; one
word per thing.

Answers to the questions in the review:

- **Chips at the top of a contest** ("dark · website archived"): now one chip per kind of
  content, each with a tooltip, and a (?) to `about.html#status`, which lists every value.
- **Provenance values**: two kinds. Import stamps ("ICPC Problem Archive progress sheet (date)",
  168; "Baekjoon ICPC category tree…", 49) — about the problem set, no longer shown on the
  contest. Hand-collected evidence (368 lines on 138 contests: where a date was read, proof that
  a dark contest ran) — shown as an *Evidence* section. The field is gone
  from the facts list; nothing was deleted from the data.
- **"listed: all/yes/no"** was "does the set have a per-problem list". Now the column **list**:
  complete / partial / none.
- **"#" vs "listed"**: # was the number of problems the contest had, listed the number we know
  by name. Now one column **problems** (the number; "N listed" underneath when partial).
- **Sets without a season**: their contests had no `season` (fixed, §3); the remaining blanks
  are the 21 sets of non-mainline contests (kth, bergen, naipc).
- **"held — not recorded yet"** on a problem: per-problem holdings are recorded for only 324 of
  10,546 problems. A problem now inherits from its set where the set is all-or-nothing, and
  says in words where the marks come from.
- **Link to a data YAML**: a "view source" convenience; removed from set, problem, judge and
  location pages. The repo is linked once, in the footer and under About › Data.
- **Sources page vs per-type pages**: now the same page — same columns, same filters — with the
  role pages as that table cut down, and one row of role tabs on all of them.

Decisions taken that are easy to reverse:

- A problem's online-judge links go straight to the judge (marked ↗) from problem rows, the one
  routine exception to "sources link to their source page".
- Dates link to a **calendar** (`calendar/<year>.html`, the day's contests highlighted) rather
  than each date being an object with its own page.
- The old "problem holdings by contest" page is folded into Coverage; `problems/` redirects.
- The "unique teams — not yet computed" tile is gone until there is a number.
- IBM Plex Sans is vendored in `tools/site_assets/fonts/` (OFL, 80 KB); styles and script moved
  out of the pages into `site/assets/` (the built site went from 701 MB to about 470 MB).

## 5. Suggestion: merge the problem sets that are really one

1,345 of 1,347 sets belong to the one contest of the same id, which makes the set look like
a duplicate of the contest. But 82 sets in 22 groups have identical problem lists: the Latin
America regionals share one set every year (brazil, caribbean, central-america, mexico,
south-america-north/south 2008–2025), and a few North America pairs do (east-na/ecna 2025,
mausa/ncna 2021, scusa/seusa 2020, brazil/brazil-first-phase 2019). Merging them into shared
sets (`latam-2021` used by six contests) would turn 82 sets into 22 and make "used by" mean
something. Needs a ruling on the ids of shared sets.
