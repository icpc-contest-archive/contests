# results-na — missing results for North America contests (data scan 2026-11-23)

## What was checked, and how (rerunnable)

Targets: every contest in a series whose header `region` is North America, without `status: upcoming`, with no
source whose roles include scoreboard / frozen_scoreboard / standings / rankings / teams — **68 contests**
(`work/targets.json`, built with `catalogue.load_series()` from the worktree at the start of the run).

For each, roughly most recent first:

1. **Our holdings**: every crawl/capture under `archive/<series>/<contest>/` scanned (site manifests) for
   standings/results/score/rank/team pages and their links followed; the contest's `provenance` lines (mostly the
   2026-10-22 existence hunt) read for result leads (`work/target_provenance.json`).
2. **CMS**: the three standings dumps (`icpc_all_standings.json`, `icpc_new_standings_from_db.json`,
   `icpc_standings_topup.json`) checked for rows under each cms id; slugs from `data/cms-shortnames.json`, confirmed
   with `/api/contest/public/<slug>`. The live standings endpoint (`/api/contest/public/search/contest/<id>`)
   answered "unexpected error" on 2026-11-23 for every id that has rows (and `[]` for empty ones), so ids missing
   from the dumps (naq-2013's 12 ids, the 2026 ids) could not be checked live.
3. **Sibling patterns**: Kattis subdomains (`<site>19`, `acpc19*`, `naq12/13`, `clarkson16-18`, `oswego16-18` …),
   the organisers' sites (Oswego `~mohammad/contest`, Clarkson `clubs/acm/icpcYYYY.htm`, uleth LCPC, McGill prelims,
   unomaha `acmregn/standYY`, udel `~saunders/regionalYY`, Baylor `past/icpc98`, socalcontest.org history).
4. **Wayback CDX** from the device shell over those hosts (`work/cdx/`).
5. **Web / Usenet**: WebSearch; Google Groups comp.org.acm searches through WebFetch (works; usenetarchives.com is
   Cloudflare-walled). Pages accepted only after opening them (live, Wayback `id_`, a PDF read with pdftotext, the
   CONTENTdm OCR API, or WebFetch where curl hits a bot wall — marked in the evidence).

`work/build_ops.py` turns `work/found.json` + `work/rolechanges.json` into `ops.json`; `work/build_data.py` writes
`data.json`. `python3 tools/apply_scan_ops.py --check ../findings/results-na/ops.json` → **23 ok, 0 failed**.

## Counts

68 targets: **20 get a result source** (19 new sources; 2 existing sources get a results role), **4 were already
fixed in the worktree by another scan agent** (east-na/ecna/gny/nena-2026: the East Division PC^2 scoreboard at
east.na.icpc.global/scoreboard/2026/eastdiv/ and its region pages, which I found too; my duplicate ops were dropped),
**44 nothing found** (one line each in `data.json` with what was tried).

## What the ops do (23 ops)

- **CMS standings that were in the dumps but never filed** (4 appends, role `standings`):
  nena-atlantic-2013 `UPEI-2014` (21 rows), nena-west-2013 `SUNY-Oswego-Preliminary-2014` (16),
  nena-north-2013 `Clarkson-Preliminary-2014` (6), nena-central-2013 `WNE-Preliminary-2014` (18). The bake step
  (`tools/bake_icpc_standings.py`) will give them copies from `icpc_new_standings_from_db.json`.
- **Kattis / PC^2 boards** (2 appends): nena-central-2019 `hamilton19.kattis.com/contests/hamilton19/standings`
  (scoreboard, 15 teams, A–H); nena-north-2008 `www.cs.mcgill.ca/~acm/prelim2008/Standings.html` (standings, PC^2,
  5 teams, the "Scores" link of the held prelim page).
- **Second-hand accounts giving an order** (12 appends, roles `report` + `rankings` with `scope`, following the
  sr-roles-b convention for news/Usenet):
  ecna-1996 (U Michigan University Record 1996-12-17: Michigan first of 63; champions);
  gny-1997 (Stony Brook team page and Cornell coach's page: Stony Brook, Queens, Cornell; top 3);
  gny-1996 (Cornell coach's page: Cornell 2nd, at Manhattan College; one team's place);
  ncna-1995, scusa-1995 (Radev's comp.org.acm compile of 1995-12-14, already gny-1995's source; top 3);
  scusa-1994 (Radev 1995-01-07 in "ACM contest finals list", already gny-1994's source: Baylor, Louisiana Tech,
  "3rd place: Texas Tech"; top 3);
  socal-1988 (Caltech News Feb 1989 p.5: Caltech 1st and 2nd; top 2); socal-1985/1986/1987 (same article:
  "for the fourth straight year" — champions, see D6);
  socal-1979 (Daily Sundial 14 Nov 1980: "Pomona won the competition last year … CSUN came in third").
- **Team list** (1 append): socal-1980, the same Sundial preview naming the six competing schools (`report`+`teams`).
- **Role added to an existing source** (4 sets): mcpc-1996 `csc.smsu.edu/~mcpc/oldIndex.html` (held copy: "This
  year the three top teams from the region are: UMR (A), Northwest Missouri State (A), Louisville (A)") → `web,
  rankings`, scope top 3; seusa-1995 UCF team-record page (held copy: "1995-1996 Regionals: 2nd, 7th & 8th") →
  `web, rankings`, scope UCF teams' places (as it already is for seusa-1996/1990).

## Items for discussion with Fredrik

**D1. Thirteen SoCal `web` sources are addresses that never existed.** socal-1979…1988, 1990, 1991, 1993 each cite
`http://www.socalcontest.org/history/<year>/results-<year>.shtml`. Live: 404; Wayback: no capture; our crawls: empty;
the site's `/history/` tree starts at 1995 (the 2026-09-06 dark-contest research already corrected itself on this).
*Implies*: by ruling 16 ("remove when the address never served that edition") they go; they currently make these
contests look as if they had a site. *For removing*: nothing ever served there; they were guesses from the 1995+
pattern. *For keeping*: harmless placeholders until someone looks again. Example: socal-1983. **Recommendation:
remove all 13** (list in `data.json` → `guessed_socal_urls`).

**D2. Do regional World Finals participant lists count as results?** Radev's "ACM'95 Finals Participants"
(comp.org.acm 1995-01-13) and Cormack's WF-1994 results list each region's finalists, unordered. They would give
something to mcpc-1993/1994, ncna-1994, rmc-1994 and many regionals elsewhere. *Precedent*: gny-1994 already cites
the "ACM contest finals list" thread as `rankings` (there GNY has "Columbia (first)"). *For*: they say who came out
on top. *Against*: advancing ≠ order (wild cards, one team per school), so they are not a ranking by the 2026-11-14
criteria. **Recommendation: not results; at most `report`**, unless a list states places (as the scusa-1994 entry
does, which I used).

**D3. Known results addresses with no copy anywhere.** naq-2012: the organiser's page links "final standings for each
institution" `https://icpc-qual-12.contest.scrool.se/standings/` (Wayback: 3 captures, all "Could not connect to
database"); nena-west-2008: Oswego's page links "Final Standings Fall 2008 Contest" `scoreboard08_FINAL.htm`, never
captured. *Question*: add them as lost result sources? *For*: ruling 16 keeps lost sources that were the contest's,
and it records that results existed. *Against*: nothing confirms the content; `results_known` would rise with no
copy. **Recommendation: add them (role standings, shown lost)** — your call, not in ops.

**D4. ecna-1997's only `web` source is not about ECNA.** `uwaterloo.ca/international-collegiate-programming-contest/
past-successes` is Waterloo's World Finals placings ("teams … ranked among the top 20 universities in the ICPC World
Finals"; 1997 → 5). **Recommendation: remove it from ecna-1997** (it is, at most, a one-team ranking of wf-* contests).

**D5. ECNA 1990 or 1991 champion = Alma College?** Alma's photo record "1991 Computer Team (Regional Winners and 4th
in Nationals) … finished first of 56 at the ACM East Central Region Programming Contest"
(dspace.alma.edu/xmlui/handle/123456789/7730). Alma is not 4th in our WF-1991 or WF-1992 standings, so the season is
unclear. **Recommendation: leave out** unless another account fixes the year.

**D6. Champions by arithmetic.** socal-1985/1986/1987 get Caltech as champion from the Feb-1989 sentence "For the
fourth straight year, a Caltech team has placed first in the southern California regional". *For*: explicit
statement, consistent with Caltech's WF-1986/1988 wins. *Against*: it is an inference across years. **Recommendation:
accept** (ops are in; drop ops #14–16 if you disagree).

**D7. 99 catalogue contests have CMS standings rows in the dumps but no CMS standings source** (32 of them from 2013,
the unmerged `icpc_new_standings_from_db.json` block). I filed the 4 in my area; the other 9 in North America
(ecna-2013, gny-2013, lethbridge-2013, nena-east-2013, pacnw-2013, rmc-2013, rmc-2021, scusa-2013, socal-2013) already
have other results, and 86 are elsewhere (results-latam lists the same gap). **Recommendation: one pass that adds the
CMS source for all 99, then bake** (`data.json` → `cms_rows_but_no_cms_source`).

**D8. alberta-2019's result is one ambiguous table.** cpc.cpsc.ucalgary.ca/contests/past_winners has a single
unlabelled 2019 table (Div I victorz.ca 6/7, Div II Bullfrogs 5/7) that may be the March CCPC or the November ACPC;
the ACPC-2019 editorial has 8 problems, which does not fit "6/7". Not filed.

## Side finds for other agents (not in ops)

Dates/locations: nena-central-2019 ran **2019-10-26** (Kattis start time and the Hamilton page), catalogue says
2019-11-09; nena-north-2013 2013-10-19 (Clarkson page, CMS); ncna-1995 1995-11-04 (unomaha sites95.html);
scusa-1994 1994-11-05 at Texas Tech; gny-1996 at Manhattan College, Bronx. Problems: alberta-2019 editorial
`cpc.cpsc.ucalgary.ca/contests/acpc/2019/files/ACPC19.pdf` (8 problem titles); east-na-2026 statements
`east.na.icpc.global/scoreboard/2026/eastdiv/problems/A.pdf`…`N.pdf`. Details in `data.json` → `side_finds`.

## Not done / blocked

- The live CMS standings endpoint errors for non-empty contests (2026-11-23), so naq-2013 (12 ids) is unchecked.
- Several hosts do not answer from either shell (cpc.cpsc.ucalgary.ca — read via WebFetch; cs.oswego.edu;
  cs.drexel.edu); the Wayback Machine was intermittently "temporarily offline".
- Not reached in depth: newspaper archives for socal-1981–1984 and 1989–1993 (Daily Bruin reels, SDSU Daily Aztec,
  UNLV Rebel Yell hits are unread PDFs), the Rice Thresher for scusa-1989/1990, the 1980s ECNA (pre-Usenet).
- The session was interrupted twice; everything is rebuilt from `work/` files.
