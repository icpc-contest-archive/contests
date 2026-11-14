# statement-only check — 2026-11-13

Every problem set whose `repo:` is `icpc-problem-archive/statement-only` was compared with the
checkout of that repo (HEAD 82a7b9c, 119 PDFs). Text PDFs were read with pdftotext, the 17 scanned
ones with OCR; problem headers were counted and the catalogued names looked up in the text.
Nothing in the data was changed.

115 sets claim the repo. 104 claims hold as stated (file present, right contest, every problem
of `count` has a statement). The rest:

## Claimed, but no file in the repo (6)

bapc-2006, bapc-prelims-2009, seerc-2021, seerc-2023, seerc-2024, ukiepc-2021 — all from the
progress sheet's Repo column. Either the PDFs were never pushed or the sheet is wrong.

## File named differently (1)

- bapc-2007: the file is `benelux-2007.pdf`.

## Claim wrong or doubtful (4)

- nzpc-2019: `statement: full`, count 16 — the PDF holds problems A–H only (8 of 16; I–P absent).
- bapc-2007: `count: 9`, `letters: unknown` — the PDF has 10 problems, A–J; the set lacks
  E "Lingo" (the HDU mirror skipped it) and the letters are in the PDF. The sheet said 10.
- wf-1982: count 7 — the PDF has problems 1–6 and 8, no problem 7. Either the set had 8
  problems and one statement is missing, or the numbering has a gap.
- nena-2013, nena-2014: `data/solutions/package: partial` (6 and 7 of 8) on a repo that only
  holds a PDF; those files must live somewhere else.

## Statement is all there, but problem rows disagree with the PDF (5)

- wf-1983: rows list "Mousetrap" twice and no "Spanning Trees" (PDF problem 2).
- nzpc-2018 M: PDF says "Eye of the Tiger (4 sec)", row says "SUPERHOT (4 SEC)" (row comes
  from the cs.auckland.ac.nz copy, so the two PDFs differ).
- poland-2017 M: PDF says "Maximal Sandbox", row says "Minimal Variance Tree".
- socal-2019: PDF says "Morse Redux", the one row says "ReMorse".
- nena-2013: PDF has Corridor, DVDs, Maze, Palindrome, Pegs, Pipes, The Innovative Water Clock,
  WordSpin; the 6 rows lack Corridor and the Water Clock.

## Files in the repo that no set points at (10)

- wf-2001 … wf-2009: the sets point at their own repos (`icpc-problem-archive/wf-200x`); the
  statement-only copies are not recorded.
- wf-1974.pdf: the Texas Regional Programming Contest of 1974-04-06 (3 problems visible).
  Consistent with the 2026-11-01 ruling that wf-1974 is a sheet error.

## Notes

- nzpc-2021 has 14 problems lettered A–K, M–O (no L; G is printed as a second "F").
- wf-1983's cover says six problems; the PDF has eight.
- ukraine-2020 carries no year on the page (PDF created 2021-02-12); not otherwise confirmed.

## Repo list (gh, 2026-11-13: 118 repos in icpc-problem-archive)

- Every repo the data names exists. The 16 `benelux-*` names were stale (GitHub already has
  them as `bapc-*`); the sets now say `bapc-*`.
- 7 contest repos had no set pointing at them; `repo:` added, holdings not checked:
  bapc-2025, bapc-prelims-2025, nwerc-2022, seerc-2018, ukiepc-2023, ukiepc-2024, ukiepc-2025.
- bapc-prelims-2009 is an empty repo; its set still points at statement-only, which has no file.
- Not contest repos, not in the data: wf-1978-2000, wf-1974, apc, icpcarchive.ecs.baylor.edu,
  onlinejudge.org (empty), .github-private.

## Applied 2026-11-13

- nzpc-2019: statement partial (8), A–H marked as held.
- bapc-2007: count 10, letters A–J, problem E "Lingo" added.
- Not applied: wf-1983's second "Mousetrap" — the duplicate title is in the Kattis export
  itself (two uuids), so which one is "Spanning Trees" has to be settled in Kattis.

## Holdings from the repos' file trees (2026-11-13, _hunt/repo-trees/)

Filled in for the seven repos that had no set pointing at them:
- bapc-2025 (12), bapc-prelims-2025 (12), ukiepc-2024 (12), ukiepc-2025 (13): full packages.
- ukiepc-2023: 14 full packages, A–N; letters recorded; `count` left unset because the set has a 15th row, "Tetris" (Kattis export),
  that is not in the repo.
- seerc-2018: statement PDF, test data for all 11, solutions for 5 (B, D, F, J, L), no
  packages. The repo's directories are A–G, I–L (no H); the set letters them A–K.
- nwerc-2022: 12 full packages, as already claimed.

Found on the way, not applied:
- `wf-1978-2000` holds full packages for wf-1978 … wf-2000 (164 problems); the sets for
  those years say statement-only with no data. `wf-1974` holds 5 packages.
- Repos that hold only PDFs while the set claims data/solutions/package: nwerc-2009,
  nwerc-2011, swerc-2013, swerc-2014, swerc-2015, cerc-2014, bapc-prelims-2021.
- Repos with full packages where the set says package none or partial: ukiepc-2020 (13),
  germany-2021 (14, set says 4).
