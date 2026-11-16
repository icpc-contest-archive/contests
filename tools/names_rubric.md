# Reading problem names: what a reader does with one batch

You read the problem-set documents we hold for a batch of ICPC contests and write down the names of
each contest's problems, as the documents print them. You read and write result files; you change
nothing else: no catalogue file, no git, no web.

Work only through the shell on the user's computer (the tool `mcp__remote-devices__device_bash`).
Everything is under `$HOME/mnt/icpc-contests/_names/run1` — call it RUN. If that folder is not
there, stop and say so.

## Input

`RUN/batches/<batch>.json`: a list of contest ids — your batch.

For each contest, `RUN/<contest>/pack.json`:
- `name`, `date`, `season`: the contest.
- `count`: how many problems the catalogue believes the contest had (may be null, may be wrong).
- `problems_listed`: what the catalogue lists already (letter, name). It may be partial and its
  spelling may differ from the documents. Do not copy from it: report what the documents say.
- `set_shared_with`: other contests that sat the same problems.
- `sources`: the documents we hold. Each has `n`, `url`, `roles`, `contains`, `judge` (set when it is
  a page on an online judge), `scope`, `text` (a file beside pack.json with the extracted text) and
  `file` (the full copy on disk).

`RUN/<contest>/s<n>.txt` is the text of source n: for a PDF the first two pages in full and then
the top of every page (titles sit there); for a web page its text and then its links; for an
archive or a folder its file names.

When that text is not enough (a title is cut off, the page tops do not show the titles), open the
full copy, for example:

    pdftotext -layout "<file>" - | grep -n -i -E "^ *(problem|task|problema|zadanie|задача) " | head -60
    pdftotext -f 3 -l 3 -layout "<file>" - | head -40

Do not print whole large files: use `head`, `grep -n`, `sed -n '1,80p'`. A copy that is gzipped
starts with bytes 1f 8b: `zcat "<file>" | head`.

## Output

For each contest write `RUN/<contest>/result.json`, as soon as that contest is done:

    {"contest": "<id>",
     "problems": [{"letter": "A", "name": "Atomic Energy", "from": 2}],
     "count": 11, "complete": true, "confidence": "high",
     "evidence": "one sentence: what you saw", "notes": ""}

Write it with python3 and `json.dump(..., ensure_ascii=False)` inside a heredoc, so quotes and
accents survive. One entry per problem, in the contest's order.

## Rules

- **The name is the title as the document prints it.** Verbatim: its capitalisation, punctuation
  and accents. Repair only plain extraction damage (a word hyphenated across a line break, doubled
  spaces, a ligature, an OCR slip you are sure of). No "Problem A:" prefix, no time limits, points,
  file names or authors after it.
- **Language.** If the document gives a title in several languages, take the English one;
  otherwise keep the original language. Never translate. A title that a judge shows only in its
  own translation (Baekjoon's Korean titles of an English-language contest) is not the problem's
  name: leave that problem out, set `complete` false and say so in `notes`.
- **letter** is the label the document uses: "A", "B", …; "1", "2", … when the contest numbers its
  problems; null when the document labels nothing (then keep its order).
- **from** is the `n` of the source you read the name in.
- **Only this contest and this edition.** Check that the document names the contest or the year, or
  that address and date fit. A document of another contest or year, or one with no problem names in
  it (an error page, a login wall, an empty list): `"problems": []`, and say what it is in `notes`.
- **Leave out** practice, warm-up and dress-rehearsal problems; say in `notes` that they are there.
- **Divisions.** When the contest has several divisions or several sets whose letters repeat, list
  them all, give each problem a `"division"` field as the document names it, and say so in `notes`.
  `count` is then the number of distinct problems; give the number per division in `notes`.
- **A copy that is broken** (a truncated PDF, an empty file): `"problems": []` for what it would
  have given, and say in `notes` which source it is and what is wrong with it.
- **count** is how many problems the contest had according to the documents (null when they do not
  show it). **complete** is true only when your list has every one of them.
- **Sources that disagree** (a judge's list against the organisers' statement): take the organisers'
  statement and mention the difference in `notes`.
- **Never guess a name.** A title you cannot read: leave that problem out, set `complete` false and
  name its letter in `notes`.
- **confidence**: `high` = you saw every title clearly; `medium` = some titles were cut, inferred
  from a link or a file name, or read by OCR; `low` = you are unsure the list is right.

## When you are done

Reply with one line per contest — `<contest>: <k> problems, complete yes|no, <confidence>` — and
then a line naming any contest you could not do, and why.
