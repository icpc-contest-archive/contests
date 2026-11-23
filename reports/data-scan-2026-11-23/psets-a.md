# psets-a — missing problem sets, Europe / Northern Eurasia / North America / International (data scan 2026-11-23)

## Scope and how to rerun

Targets: every contest that ran (no `status: upcoming`) in a series whose header `region` is Europe,
Northern Eurasia, North America or International, with no source whose roles include `problemset` or
`problem`: **339 contests** (Northern Eurasia 209, North America 82, Europe 47, International 1).
List: `work/targets.json` (built from `cat.load_contests()` in the read-only worktree).

What was tried, in order (scripts in `work/`):

1. **Shared sets** (`propagate.py`, `verify_plan.py`): for a target whose `problems: set` is shared, take the
   statements a sibling contest of the set already carries (the nerc.itmo.ru form with `as_of` that
   taurida/urals/uzbekistan use), and check our archive copy of it with pdftotext against the set's
   problem names. All PDFs held every name of their set (11/11 .. 14/14); the 2005 RAR holds statements.ps,
   the 2008 PostScript is headed "ACM ICPC 2008-2009, St Petersburg, November 1, 2008".
2. **nerc.itmo.ru/archive/<year>.html** 1998-2026 parsed per subregion section (`nerc_parse.py`).
3. **Own holdings**: every `site-manifest.json` of the targets' website crawls (3,904 document-like files),
   filtered by the contest's year (`crawl_files.json`, `crawl_year_docs.json`).
4. **Codeforces gym list** (API live 2026-11-23 + the April dump), **Kattis problem-sources** (all 9 pages),
   **icpcarchive.github.io** (NA, NE, Europe indexes).
5. **Wayback CDX** of specific hosts: acm.ro, vntu.edu.ua, socalcontest.org/history, ncna-region.unl.edu,
   cs.oswego.edu, cs.hamilton.edu, cs.uleth.ca; live probes of 2026 addresses (pattern of the 2025 edition).
6. Earlier dead ends (reports/problemset-hunt-2026-11-02.md, no-sources-hunt-2026-11-16.md) were not
   repeated; Wayback, blocked for those rounds, was used here.

Every op passes `python3 tools/apply_scan_ops.py --check ../findings/psets-a/ops.json` (81 ok, 0 failed).

## What the ops do (81 `append` ops, 68 contests)

| group | ops | contests |
|---|---|---|
| Northern subregional statements added to the NERC subregionals that sat the same set (sets north-russia-2005..2025, nerc-shared-2021) | 52 | armenia 2012-2022, 2025; azerbaijan 2015-2018, 2021, 2023; georgia 2005, 2006, 2008-2014, 2017, 2018, 2025; kazakhstan 2005-2016, 2018-2023, 2025; taurida-2016; turkmenistan-2025; west-neerc-2022 |
| NA South Division 2026 Division 1 problems page (Kattis) on its regional views | 2 | mausa-2026, seusa-2026 |
| Northwestern Russia 2026 statements on the subregionals whose 2026 standings show the same 14 titles | 4 | armenia-2026, georgia-2026, kazakhstan-2026, taurida-2026 |
| UCPC 2026 II stage statements (acmallukrainian.ho.ua/2026/2/statements_eng.pdf, as for 2025) | 1 | ukraine-2026 |
| Codeforces gyms named by the gym API as this edition (page itself Cloudflare-blocked, `contains` left unrecorded) | 2 | kyrgyzstan-2026 (gym 106802), south-russia-2026 (gym 106825) |
| AUCPC 2nd stage statements on vntu.edu.ua via Wayback | 3 | ukraine-2013, ukraine-2014, ukraine-2015 |
| Statements held in our own website crawls | 16 | alberta-2014 (9 `problem` sources A-I), norway-2001 (5 `problem` sources A, C, D, G, H), urals-2003 (2 rounds, `scope`) |
| SUNY Oswego Fall 2010 questions page (Wayback) | 1 | nena-west-2010 |

Each source carries `contains` (statement, or unrecorded for the two gyms), `judge` where on a judge,
`as_of` for Wayback/crawl copies, and `note: found by the data scan 2026-11-23 (...)`; the evidence field
names the archive copy or snapshot opened.

`data.json`: `finds` (all 81, with evidence), `names` (letters → names read from the added documents for
contests with no set: armenia/georgia/kazakhstan/taurida-2026, ukraine-2026, ukraine-2014, ukraine-2015,
nena-west-2010 (numbered 1-5); plus a letter map for ukraine-2013's existing set), `nothing_found` (271
contests, with what was tried), `leads`, `by_catch`.

Nothing was found for 271 targets: most are NERC subregionals whose own sets (Armenia/Azerbaijan/Georgia
2019-2022, Kyrgyzstan, Uzbekistan, Central/East Siberia/West Siberia/South Russia before ~2012, Western 1998-2023)
exist only as standings headers, and pre-1998 North American regionals (SoCal 1979-1998, RMC, SEUSA, PacNW
1994-96, GNY 1993-96) with no surviving set.

## Items for discussion with Fredrik

**1. One problem-set source per contest that sat a shared set?** 52 of the ops copy the Northern
subregional statements PDF onto every NERC subregional that sat that set (e.g. armenia-2019, kazakhstan-2019
get nerc.itmo.ru/archive/2019/northern/nwrrc-2019-statements.pdf, which already sits on north-russia-2019,
taurida-2019, urals-2019). *Implies*: coverage for "statements" turns green on ~50 more contests; the source
page shows several contests. *For*: DEFINITIONS says contests of one season sharing a set share the source;
taurida/urals/uzbekistan already do this. *Against*: the coverage record could derive it from the set instead,
without repeating the address. Recommendation: apply (consistent with the existing practice); later, consider
letting coverage follow the set.

**2. The 2026 NERC subregionals sat one set that has no `problems: set` yet.** armenia, georgia, kazakhstan,
taurida, tajikistan, turkmenistan, urals and north-russia 2026 all show the same 14 titles A-N (AALEX.EXE ..
Nuts and Bolts; standings fetched 2026-11-23). *Implies*: the problems agents should create one shared set
`north-russia-2026` with eight members (names in data.json). Recommendation: create it (agreement of eight
independent standings headers plus the statements PDF).

**3. north-russia-2021 vs nerc-shared-2021.** The Northern 2021 statements PDF holds all 14 problems of
`nerc-shared-2021` (Anno Domini 2022 .. New White-Black Tree), the set of Armenia/Azerbaijan/Kazakhstan/
Taurida/Ural 2021; north-russia-2021 itself points at a 15-problem set with Russian titles (Изгороди ..).
*Implies*: either north-russia-2021's set is another contest's, or the Northern 2021 contest had two sets.
Recommendation: problems agent checks https://nerc.itmo.ru/archive/2021/northern/standings.html; if it shows
the 14 titles, move north-russia-2021 into nerc-shared-2021.

**4. Turkey: is the inzva "Online Programming Contest" the ICPC Turkey contest?** The OPC 2021 Final
(algoleague, 2021-12-19) says plagiarists "will be banned from the Turkish Programming Contest 2022", i.e.
OPC and TPC are different events. turkey-2022's scoreboard source is the algoleague OPC 2022 leaderboard,
and the no-sources hunt proposed OPC finals for turkey-2021/2023 "by series continuity". *For OPC*: the CMS
entries have no teams and inzva ran no TPC 2020-2023 that we know of. *Against*: the organisers' own words.
Recommendation: do not add the OPC problem sets (not added here); re-examine turkey-2022's scoreboard.

**5. Gyms identified by the API title alone.** kyrgyzstan-2026 (106802 "2026-2027 ICPC NERC, Kyrgyzstan
Regional Contest", Bishkek) and south-russia-2026 (106825 "2026-2027 ICPC, NERC, Southern and Volga Russian
Regional Contest", Saratov) are added with `contains` unrecorded, since codeforces.com/gym pages are behind
Cloudflare from here. Recommendation: accept; a session with browser access can fill `contains`.

**6. SoCal "previous contest problems".** socalcontest.org/current/prev_probs/ holds 11 single statements
marked "Southern California Regional ... PREVIOUS CONTEST PROBLEM" with copyright 1995 (7), 1996 (2), 1998 (1)
(+1 undated). No letter or contest is named, and socal-1995..1998 have no problem names to match.
Recommendation: leave out unless a results page with problem titles turns up; listed in data.json leads.

**7. By-catch outside this area (for the facts/sources agents)**: bulgaria-2010's only source is a Romania
page (acm.ro/Romania/call_for_participation.htm); romania-2010's website crawl is SEERC 2010; statement dates
differ by a day from the catalogue for ukraine-2014 (Sep 13 vs 14), ukraine-2015 (Sep 12 vs 13) and
romania-2010 (May 22 vs 23); ukraine-2013's set lacks H «Sum» (the PDF has 10 problems A-J); urals-2003 was a
two-round contest whose set holds only the 8 day-1 labels.

## Blocked / not done

- codeforces.com gym pages and olymp.krsu.kg could not be opened (Cloudflare / no answer); the proxy bypass
  was refused, so it was not used.
- The 2026 East Division (ECNA, GNY, NENA) and SoCal 2026 sets are not published yet (403/404 on the 2025
  patterns); re-check later.
- Not done for lack of time: Wayback CDX of people.clarkson.edu (nena-north), midatl.radford.edu
  (mausa-2013/14), psc.cpsc.ucalgary.ca (alberta-2013/2015), versenyek.inf.elte.hu (hungary), icpc.az/acm.ge
  style hosts of the Caucasus/Central Asian subregionals. The device session was interrupted twice.
