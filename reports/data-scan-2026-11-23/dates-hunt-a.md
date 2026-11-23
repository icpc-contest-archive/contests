# dates-hunt-a: missing dates, regions North America / Europe / Northern Eurasia / International

Scope: contests that ran (no `status: upcoming`), no `date`, series region in the four above: **220** at the start (list in work/targets.json). Rule: `date` = the day the contest ran; multi-day or multi-round events whose contest day cannot be pinned stay blank.

## What I checked (rerunnable)
- work/grep_dates.py: greps every held text/PDF under `archive/<series>/<id>/` for dates (ru/en months, numeric, ISO); output work/grep_all.txt. work/ctx.py `<id> <regex>` prints context. Most hits are contamination: the neerc.ifmo.ru whole-host crawls carry other contests' headers (e.g. every 2006 subregion holds the Northern "November 5, 2006" PDF), so each hit was read in context.
- Live pages from the device shell: udel.edu (Mid-Atlantic 1996), tekmovanja.acm.si calendar, versenyek.inf.elte.hu, inzva reports, cs.uleth.ca, olymp.nstu.ru, acm.bsu.by, sp.urfu.ru, contest.sgu.ru, cs.bme.hu.
- Codeforces (problem pages, gyms) and acm.sgu.ru are Cloudflare/unreachable from here, so the SGU "Date:" header was only usable from our held copies.

## Ops: 32 (16 `set` date, old null + 16 provenance `append`); `--check`: 32 ok, 0 failed (re-run at the end)
| contest | date | evidence |
|---|---|---|
| mausa-1996 | 1996-11-16 | udel.edu regional96/schedule.html "Saturday, November 16, 1996 ... Contest begins 12:30" |
| central-russia-2002 | 2002-10-17 | standings heading "Central Subregion Rybinsk, October 17, 2002" (region's span was Oct 15-18) |
| moscow-2005 / 2007 | 2005-10-23 / 2007-10-21 | statement headers (Codeforces gym PDFs, held) |
| south-russia-2002 / 2003 / 2004 | 2002-10-10 / 2003-10-09 / 2004-10-07 | SGU problem pages "Date:" field (held); all Thursdays, as 2003 central etc. |
| slovenia-2016 / 2017 / 2022 | 2016-10-15 / 2017-10-14 / 2022-10-15 | tekmovanja.acm.si/?q=koledar, rows "finale UPM" (also confirms 2018-10-13, 2019-10-12, 2023-10-14, 2024-10-19) |
| turkey-2021 / 2022 / 2023 | 2021-12-19 / 2022-09-17 / 2023-11-04 | inzva OPC reports (held in web-mirror) |
| hungary-2024 | 2024-10-19 | ELTE announcement 2024-09-22 (pre-announcement, medium) |
| lethbridge-2025 | 2025-03-01 | cs.uleth.ca LCPC/2025 "Time: March 1" - see item 3 |
| rmc-1991 | 1991-11-09 | Usenet post of that Saturday "contest ... is just finished" (medium) |

## Left blank on purpose (with the reason)
- **Urals 1998-2005**: championship runs 3-6 days with two scored rounds on different days (urals-2001: round I Apr 18, round II Apr 20; 2003 days 1/2 = 24/25 Apr; 2004 12-15 Apr; 2005 20-23 Apr). No single contest day.
- **East Siberia 2003 (1-3 Nov), 2006 (4-6 Nov), 2007 (27-29 Oct)**: span only on the organisers' page; the middle day is a guess.
- **West Siberia 2005/2006**: olymp.nstu.ru/contests dates "ACM 2005" 2005-10-28 (Fri) and "ACM 2006" 2006-11-09 (Thu). Plausible but the OlympSystem entries were created long after, and weekdays are odd; not applied (see item 4).
- **Turkey-2020**: two rounds, 12 and 26 Dec 2020 (qualification + final). **Turkey-2021** also had an earlier qualification; I took the organisers' stated day for the final (Dec 19).
- **Hungary-2025**: announcement says Oct 11 but the held scoreboard shows "Last Update Sun 12 Oct 2025"; unresolved.
- **Greece-2025**: the GRCPC register page says "The competition date is 18 of October" (2025 is plausible, CMS says 17th) but the page now mixes 2025 and 2026 text; not applied.
- **bapc-prelims-2009/2015/2025, croatia-2014, rmc-1993 (Usenet results post 1993-11-07 00:02, contest probably Sat Nov 6), socal-1994 (results post Nov 14), ecna-1992/1993, nena-*, NEERC subregionals 1998-2007 other than the above**: no day found in held copies or live pages. neerc.ifmo.ru / nerc.itmo.ru archive pages (2003-2007) carry no dates at all; only the Moscow/Southern/Central headers above.

## Items for discussion with Fredrik
1. **Where can the remaining ~190 NEERC-subregional / old US dates come from?** Held copies are exhausted. Options: (a) accept blanks; (b) Codeforces gym statement PDFs (they carry "City, Month D, YYYY" headers, e.g. Moscow 2005/2007) and SGU/acm.timus problem-source pages; I could not reach Codeforces from here, so a browser session on your Mac (Chrome) could pull the header of one statement per gym for Moscow 2003/2004/2006, Southern 2005-2007, Northern/Western, etc.; (c) ask subregion organisers. Recommendation (b), it is mechanical.
2. **Multi-round championships (Urals, Turkey-2020, Slovenia 2021 online, Croatia 2014, bapc-prelims-2021/25)**: one `date` field cannot hold two rounds. Option A leave blank; option B final round day; option C `date_end`/second date. Recommendation as dates-a: (c) or B when the later round decides who advances (Urals 1998-2005: round II, the day before the closing; Turkey-2020: Dec 26).
3. **lethbridge-2025 id/season mapping.** The attached sources (cs.uleth.ca/~cheng/LCPC/2025/ and its scoreboard) describe a spring LCPC on 2025-03-01 (season 2024/25), while the series is `season-start` with fall contests (2013-09-21, 2018-09-28, 2019-10-05) and lethbridge-2024's source is the Lethbridge-teams page for Oct 2024. I set 2025-03-01 because the sources attached to that id say so; if the id was meant for a fall-2025 edition the date and sources both need moving. Related: **lethbridge-2020..2023** archive dirs hold Kattis captures of the *Alberta Collegiate Programming Contest* (acpc20d1.kattis.com etc., 2020-11-14, 2021-11-27, 2022-11-26, 2023-11-25, 2024-10-26, 2025-10-18); that is the `alberta` series (alberta-2020..2025), not the Lethbridge contest. I did not use those dates for lethbridge-*; the captures look misfiled, structure agent please check.
4. **West Siberia 2005/2006 weekday dates** (NSTU list, Fri 2005-10-28, Thu 2006-11-09): apply or not? For: only dated source, the series' later entries (2008+) in the same list match our dates. Against: weekday, entries created retroactively. Recommendation: apply only if a second source (statement PDF header) turns up.
5. **swerc-1997 = 2nd-hand 23 November 1997** (QOJ description "held at the University of Ulm on 23 November 1997", Sunday) not applied: no organiser source seen.
6. Not mine but noticed: swerc-1993/-1994, ncna-1993 and werc-1994 hold ETH/Karrels pages whose text is the ECNA "Battle of Waterloo" (5-6 Nov 1993, 11-12 Nov 1994): crawl contamination; those texts are the ECNA dates (ecna-1993 span 5-6 Nov 1993, 1994 11-12 Nov).
