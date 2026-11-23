# Early years (seasons up to 1994) — data scan 2026-11-23 (agent `early-years`)

Area: the World Finals 1977–1994 and the regionals that fed them. Before this scan the catalogue held 1–9 contests per
season up to 1993 (1977–79: the WF alone). Worktree `_scan-2026-11-23/contests`, read only.

## What was checked, and how (to rerun)

- Read `findings/missing-contests/report.md` + `data.json` (seusa-1983..1987 candidates, NKP proposal, the UCF record) and
  `reports/existence-evidence-2026-10-22.md` (the earlier Usenet / campus-newspaper hunt), so as not to redo them.
- World Finals team lists: our copies of `icpc.baylor.edu/past/EarlyYears.html` (top 4–6, 1977–1997), the Baylor
  `Past/icpcNN/finals/Standings.html` pages (1990–1993), Cormack's `acmresults/1994.html` (35 teams), the 1992 scoreboard
  post (comp.org.acm 1992-03-19).
- Which regions existed per season: the 1991-92 contest rules (13 regions, comp.org.acm 1991-05-17), the 1992-93 list of
  Regional Contest Directors (15 regions, 1992-07-08), the ciiwiki "History - ICPC 1993/1994" pages (Wayback: "fifteen" /
  "15 regional contests"), the 1994 SWERC call (what Europe looked like in 1993). Table in `data.json` → `regions_by_season`.
- Then, region by region, documents about single editions: Google Groups comp.org.acm (its search works through
  WebFetch: `groups.google.com/g/comp.org.acm/search?q=...`), the Harvard Crimson, the Daily Nebraskan and the
  University Daily Kansan (digitised), the Roanoke Times archive (scholar.lib.vt.edu, Wayback), MIT News, team-history
  pages (UCF, Rice, UNL), the Otago NZPC history, the ETH problem-set archive and its Wayback index.
- Ops built by `work/build_ops.py`; proposals by `work/build_proposed.py` (→ `work/proposed_ops.json`, copied into
  `data.json`); `data.json` by `work/build_data.py`. Every op: `python3 tools/apply_scan_ops.py --check
  ../findings/early-years/ops.json` → 30 ok, 0 failed (re-run at the end). Applied to a copy (`work/vt2`) and
  `tools/validate.py` run there: 0 errors, no new warnings (2602 → 2628 contests). The proposals check ok on top of the ops.

## What the ops do (30 ops: 26 `insert_contest`, 4 `append`)

Every new edition has a source I read: one that says this edition ran. Each has `cms_ids: []`, its WF as parent,
provenance lines quoting the document, and a note. All are before the series' first edition or in a gap, so no
neighbour needed a `next` change.

- **seusa-1982 … seusa-1987** (6): the UCF team record (Wayback 2014, already the source of seusa-1988..): "UCF is in the
  Southeast USA Region … Since our first contest in 1982, we have always finished in the top 3 in our region";
  1982-83 2nd (finals 17th), 1983-84 3rd, 1984-85 1st (16th), 1985-86 2nd (4th), 1986-87 1st (2nd), 1987-88 3rd. The
  missing-contests agent had 1983–87; 1982-83 is on the same page.
- **scusa-1980, 1982, 1983, 1985, 1986** (5): Rice's team history (Wayback 2008, already a source of scusa-1987/1988):
  "South Central Regional contest" 1980 1st (→ wf-1981 2nd), 1982 2nd and 3rd (→ wf-1983), 1983 1st, 1985 1st and 3rd
  (→ wf-1986 3rd), 1986 2nd. 1981 and 1984 are "?" there, so they are not added.
- **nena-1983, 1986, 1987, 1988, 1992, 1993** (6; the series started at 1997):
  - 1983: Harvard Crimson 1983-11-29, "led a pack of 25 schools in the Northeast regionals at the Coast Guard Academy
    in New London", RPI 2nd. Date `1983-11` ("last week").
  - 1986, 1987: Crimson 1988-11-07, Harvard won "for the third year in a row" (champion only).
  - 1988: the same article: "Northeast Regional Scholastic Programming Contest" at Western New England College,
    Springfield, 20–30 teams. Date `1988-11` ("on Saturday" in Monday's paper → 1988-11-05, not set).
  - 1992: comp.org.acm, 1992-11-24 and 1992-12-05 (Dragomir Radev, then at Maine): "North East: Harvard, Maine"; Brown,
    Cornell, Toronto, MIT and RPI did not qualify.
  - 1993: MIT News 1994-12-07: the MIT team "also competed in the regional contest last year", second, went to the finals.
- **pacnw-1992**: the 1992-12-05 post: "Pacific: Berkeley, Stanford (non-confirmed officially)".
- **mausa-1990, 1991, 1992** (the series started at 1994):
  - 1990: Roanoke Times 1991-03-22, UVA lost to Tech in the "regional qualifying match held in the fall". The region is not named.
  - 1991: Roanoke Times 1992-03-07, "Tech won the regional competition in October at the University of Maryland".
    Date `1991-10`.
  - 1992: the 1992-12-05 post: "Mid-Atlantic: Virginia Tech, Maryland".
- **ncna-1984, 1985, 1992**:
  - 1985: University Daily Kansan 1985-11-18, "KU was the host of the North Central Computer Programming Contest on
    Saturday in Strong Hall", 20 teams, Nebraska 1st, Northeast Missouri State 2nd, Kansas State 3rd. The Daily Nebraskan
    1985-12-02 gives Lawrence, Nov. 16, and teams from Kansas, Missouri, South Dakota and Illinois. Date 1985-11-16.
  - 1984: the same Nebraskan article, UNL "finished second last year".
  - 1992: UNL's team history page (a copy on HKU's site), "1992-93 … took first in the North Central region".
- **taiwan-1992**: comp.org.acm 1992-12-31, Ji-Tzay Yang (NCTU): Chiao-Tung first in the Taiwan region; "Another team
  representing Asian region will join the contest if the Asian region contest is held."
- **seerc-1993**: the 1994 SWERC call (ETH/VIS, comp.org.acm 1994-08-10): "Last year, Europe was split into West and
  East". Swansea hosted the West European Regional and "the East European Regional Contest was held in Bulgaria". Comenius
  Bratislava and Sofia University are in the wf-1994 standings. Sites: `bg`.
- **New sources on existing contests** (4): ncna-1993 (UNL page: UNL 1st, Macalester 2nd); werc-1992 (comp.org.acm
  1992-11-26: RU Leiden 1st, TU Eindhoven 2nd); seusa-1992 (1992-12-02: Auburn and North Florida advance); socal-1989
  (Otago NZPC history, Wayback 2002: in 1989 New Zealand was assigned to Southern California, and Otago's team "came first
  in the region", then won wf-1990).

Contests per season after the ops (WF included): 1980 2, 1981 3, 1982 2, 1983 4, 1984–1990 6–7, 1991 8, 1992 9, 1993 14,
1994 15 (one of which is the swerc-1993 duplicate, item 2).

## Items for discussion with Fredrik

**1. Editions known only by inference: add them? (11 ready ops in `data.json` → `proposed_ops_not_applied`)**
For some seasons the region list and the number of regionals are documented, and the WF standings have a team from the
region. No document about the edition itself was found.
- 1991-92: nena-1991, gny-1991, ncna-1991, pacnw-1991, taiwan-1991. Basis: 13 regions in the rules; "a dozen
  regional events"; wf-1992 teams such as Rhode Island/Colgate, Drew, Nebraska-Omaha, Victoria BC, National Chiao Tung.
- 1992-93: gny-1992, seerc-1992. Basis: 15 named regions with directors; "fifteen regional contests"; Drew and Comenius in
  wf-1993; Drew going "for their 5th time in 6 years".
- 1993-94: mausa-1993 (Duke 3rd, Virginia Tech 24th) and pacnw-1993 (Berkeley, Simon Fraser). Basis: 15 regionals.
- ncna-1982: Daily Nebraskan 1983-02-22, UNL "second to Washington University of St. Louis in the area regionals last
  October". This one ran for certain; what is uncertain is which series it belongs to, since the region is not named.
- For adding: the rules sent each region's finalists from its regional, so a finalist from region X means X's regional ran.
  The gaps also make the early seasons look emptier than they were.
- For leaving out: invitations existed (wf-1989's "New Zealand!" composite team came by invitation, not via a regional),
  and an entry with no document about itself cannot show a date, a host or results.
- **Recommendation:** add the 1992-93 and 1993-94 ones, where the count and the list match exactly, and ncna-1982, with
  its "inferred" note. Hold 1991-92 until one document per region turns up ("a dozen" is not exactly 13).

**2. swerc-1993 is the West European regional in Swansea (werc-1993), not a contest of its own.**
- Evidence: the 1994 call says Europe was split into West (Swansea) and East (Bulgaria) "last year". The ETH archive's
  "Western and Southwestern European Regional Contest 1993" holds the seven werc-1993 problems (Chess, Compress, Cube,
  Logic, Rename, Spin, Vertex). ETH's own "Swansea 1993 Echo": its two local winners went to the West European regional
  in Swansea.
- What it implies: 1993-94 had 15 regionals (11 North American, South Pacific, Far East, West and East Europe), and
  swerc-1993 is the 16th entry.
- For merging: a duplicate contest inflates counts, and two set files stand for one problem set.
- For keeping: nothing found.
- **Recommendation:** merge swerc-1993 into werc-1993. Move its three sources (the ETH SWERC page, the ETH 1993 set,
  Live Archive category 451) and merge set swerc-1993 into werc-1993 with `merge_problemsets.py`. The swerc series then starts in
  1994. swerc-1994 is real: ETH Zurich, 11–12 Nov 1994, sharing the set with werc-1994 in Amsterdam.

**3. Filing the old regions under today's series.**
I filed by region name and continuity:
- Far East → `taiwan` (taiwan-1993 is already "1993 Far East Regional").
- Eastern/East European (ACMBUL, Bulgaria, 1992–93; Bucharest from 1995, still called "Eastern European" in 1995) → `seerc`.
- Allegheny/Capital (1991-92 rules) = Mid-Atlantic → `mausa`.
- Pacific → `pacnw`.
- The 1980s North Central (Nebraska, Kansas, Missouri, South Dakota, Illinois; Mid-Central split off in 1992) → `ncna`.
For this: one series per region keeps each line unbroken. Against: the boundaries moved, so the 1985 "North Central" is
not today's NCNA.
- **Recommendation:** keep this filing, with the boundary noted. Revisit only if you want lineage events such as
  "Mid-Central continues-from North Central 1992".

**4. 1977–1983 stays almost empty: how far to go?**
- What is known: the early WF had 4-person teams, and there was a SoCal regional from 1979, South Central from 1980,
  Southeast from 1982, Northeast and North Central by 1982–83. The region list before 1991 is unknown. Nothing was found
  for the regionals that fed wf-1977..1979, nor for East Central before 1984 or Mountain before 1989. wf-1984's Alberta
  team implies a Mountain regional in fall 1983.
- The best leads are offline or paywalled: Communications of the ACM and SIGCSE Bulletin contest reports, which ACM DL
  does not serve to us, and student newspapers. The Crimson, the Daily Nebraskan and the Kansan were productive. Others
  to try are the Michigan State News, Purdue Exponent, Daily Bruin, Stanford Daily, The Tech (MIT) and the Washington
  University Student Life.
- **Recommendation:** a newspaper-archive hunt per WF finalist school (the EarlyYears top-4 lists name them). Do not
  infer editions before 1991.

**5. Month-precision and derived dates.** nena-1983 `1983-11` ("last week" in the 29 Nov issue), nena-1988 `1988-11`
(probably Sat 1988-11-05), mausa-1991 `1991-10`.
- **Recommendation:** keep the month. Set the day only from a second document.

**6. taiwan-1992: one contest or two?** Yang's post says the Chiao-Tung team won "the Taiwan region" and that an "Asian
region" contest might add a second team. Only NCTU is in wf-1993.
- **Recommendation:** keep a single taiwan-1992 (the Far East region of the RCD list), with the note.

## Other findings (outside this area, for their owners)

- nena-1994..1996 are missing (season 1995–97). MIT News 1994-12-07: the 1994 northeast regional was at Oswego NY, with
  45 teams; MIT was 1st and 2nd, Harvard 3rd.
- seerc-1994 (Eastern European, fall 1994) is missing.
- swerc-1994: date 1994-11-12 and host ETH Zurich (the 1994 call).
- `locations.yaml`: `us-springfield-western-new-england` (Western New England College, Massachusetts) hangs under
  `us-springfield`, which is Springfield, Missouri. nena-1988's site will show Missouri until that is fixed (locations agent).

## What limited the scan

usenetarchives.com is behind a Cloudflare challenge, and ACM DL refuses us. Google Groups only indexes part of
comp.org.acm before 1994: no 1990–91 regional results posts were found. The Berkeley NZ.89–93 contest PDFs have no text
layer and were not OCR'd. The Far East 1990–91, Eastern European 1992, and Pacific / Mid-Atlantic / GNY before 1992 have
no document of their own yet.
