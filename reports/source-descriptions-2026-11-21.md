# Source descriptions: the full round, finished 2026-11-21

Every source whose copy we hold has been read, described and checked. This is the summary; the
lists are in `reports/source-descriptions-run1-2026-11-16.md` and `data/describe/run1-2026-11-16/`.

## What was done

For each contest a reader agent opened our copies of its sources and, per source, (1) judged
whether the copy is the document it is filed as, (2) recorded the facts the document states about
itself, and (3) wrote a description of one to three paragraphs. A second agent then checked every
claim against the copy and corrected it. About 3% were checked a third time by an independent
checker, and those findings were applied. The descriptions are shown on the source pages under
*What it contains*.

| | |
| --- | --- |
| contests read | 2,393 |
| sources | 11,936 |
| sources with no copy (no description possible) | 1,357 |
| sources read | 10,579 |
| descriptions written in this run | 10,020 |
| descriptions on the site, with the pilot's | 10,254 (9,736 source pages) |
| held back (low confidence, or the source has since gone) | 9 |
| average length | 105 words |
| copy is the document it is filed as | 9,574 |
| filed under the wrong kind (role to correct) | 455 |
| not the document (error page, empty shell, login page) | 308 |
| another contest's document | 227 |
| cannot tell | 15 |

A source judged *not the document* or *another contest's* has no description.

## The independent check

340 descriptions (3.4%) were drawn at random, batch range by batch range, and checked claim by
claim against the copy by an agent that had not seen them being written.

| check | batches | checked | accurate | minor | wrong |
| --- | --- | --- | --- | --- | --- |
| c01 | 1-31 | 10 | 6 | 3 | 1 |
| c02 | 32-70 | 20 | 12 | 7 | 1 |
| c03 | 71-98 | 10 | 7 | 3 | 0 |
| c04 | 99-136 | 20 | 14 | 6 | 0 |
| c05 | 137-163 | 10 | 7 | 2 | 1 |
| c06 | 164-202 | 20 | 16 | 3 | 1 |
| c07 | 203-240 | 20 | 17 | 3 | 0 |
| c08 | 241-283 | 20 | 11 | 8 | 1 |
| c09 | 284-319 | 20 | 17 | 3 | 0 |
| c10 | 320-357 | 20 | 17 | 3 | 0 |
| c11 | 358-395 | 20 | 14 | 5 | 1 |
| c12 | 396-433 | 10 | 9 | 1 | 0 |
| c13 | 434-478 | 20 | 11 | 9 | 0 |
| c14 | 479-516 | 20 | 14 | 4 | 2 |
| c15 | 517-554 | 20 | 13 | 6 | 1 |
| c16 | 555-592 | 20 | 14 | 5 | 1 |
| c17 | 593-630 | 10 | 8 | 2 | 0 |
| c18 | 631-668 | 20 | 14 | 3 | 3 |
| c19 | 669-706 | 20 | 12 | 7 | 1 |
| c20 | 707-724 | 10 | 8 | 2 | 0 |
| **all** | | **340** | **241 (71%)** | **85 (25%)** | **14 (4%)** |

*Minor* is a slip that does not mislead about what the document is (an HTML title given where the
page heading differs, a count off by one, a cell notation explained imprecisely). *Wrong* is a
claim the copy contradicts. All findings were applied to the sampled descriptions, except two style
notes that were judged not to be errors (erc-1985, nordic-2008). The findings and what was changed
are in `data/describe/run1-2026-11-16/check/`.

What this says about the 9,680 descriptions that were not sampled: by the same rates about one in
four carries a minor slip and about one in twenty-five a wrong claim, roughly 400 descriptions.
The wrong claims found were of these kinds: an inference stated as fact (teams sharing a rank
called tied, a site said to show its state "as of" a date), a miscount (members per team, problems),
something visible only as an image and so not seen (a banner naming the contest on every page of a
PDF), and the first day of a span of days given as the contest day (corrected everywhere, below).

## Blank dates and locations filled

Where the catalogue had no date or no location and a document states one, with high confidence
and no other document of the contest disagreeing, it was written into the series file with the
provenance line `<fact> read from <address> (description round <date>)`. Nothing already in the
catalogue was overwritten.

- 164 blanks filled: 103 dates and 61 locations, in 53 series files.
- Locations are as the document prints them, so they are free-form ("Linköping, Lund, Stockholm
  and Umeå", "Minsk, Belarusian State University").
- Not written, listed in `contest-facts.json` as `fills-blank`: 29 at medium confidence and 9 at
  low confidence (8 of the 9 are the span cases below).

## Differences from the catalogue, listed and not applied

- 533 contest facts where a document and the catalogue differ: 217 dates and 316 locations.
  Many location differences are only more detail (catalogue "Kuwait", document "Kuwait
  University, Kuwait"). World Finals dates are one day later in the catalogue than in the
  documents for wf-2002, wf-2005, wf-2007, wf-2012 and wf-2019.
- 1,074 sources in the second-reading list: the 455 role corrections, 308 not-the-document, 227
  another contest's document, 15 cannot-tell, and 69 the reader confirms where the content check
  of 2026-11-14 did not. 175 readings disagree with the earlier reader.
- Team and problem counts as documents show them: 1,278 and 407, listed.

## Things that went wrong and how they were handled

- **First day of a span as the contest day.** The rubric said both "the day the contest itself
  ran" and "first day for a range". 183 per-document dates (150 contests) and 8 catalogue fills
  were the first day of an event span. The rubric and the revision instructions were corrected
  (commit 8e60690), the 183 fields were set to empty (log: `span-dates-nulled.json`), the 8 fills
  were reverted, and two audits were run before every later commit.
- **Model limit.** The weekly limit of the model that ran the readers was reached on 17 November;
  the run paused until 21 November. Interrupted batches were resumed; nothing was lost.
- **An overwrite.** One reader overwrote the finished results of acpc-2000, acpc-2001 and
  acpc-2002 (batch 144). They were restored, and a guard that reports any finished result that
  changes has been run after every wave since.

## Decisions waiting

1. **nzpc-1998**: the document prints "NZ programming Contest 10/10/98", now its date
   (1998-10-10). Its parent south-pacific-1998 is dated 1998-09-29 in the catalogue (its own
   sites say 19 September), so the validator warns that the parent is earlier.
2. **Eight contests whose documents give only a span of days**, date left blank: ecna-1993
   ("5-6 November 1993"), ecna-1994 ("11-12 November 1994"), east-siberia-2003 (1-3 Nov),
   east-siberia-2006 (4-6 Nov), east-siberia-2007 (27-29 Oct), croatia-2014 ("19. i 26.
   listopada 2014."), kuwait-2026 (22 and 24 Oct), romania-2026 (7-8 Nov, standings headed
   8 Nov). Either a date per contest or a rule such as "the last day of the span".
3. **The 29 medium-confidence fills**: write them, or leave the fields blank.
4. **The 533 differences and the 1,074 second readings**: nothing was applied.
5. **Description as a unit in review mode**: not built. The marker of a unit carries the
   catalogue's value, and a description is too long to travel in a review link; it needs a
   decision on what the marker carries (for instance the copy it was read from).

## Also done

- `DEFINITIONS.md` has a section *Source descriptions*.
- `tools/validate.py` checks the description files (contest exists and is in that series, every
  entry complete, date format; a description whose address is no longer a source is a warning).
- The site builds with all descriptions (65,535 pages).

## Not done

- 1,357 sources have no copy and so no description.
- A source that gets a new copy has to be read again; nothing does that automatically yet.
