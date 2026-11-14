# Content check applied, 2026-11-15

Every source with a held copy was read by an agent (rubric 4, run `run-2026-11-15`: 2,498 contests,
11,566 sources). `tools/content_check_apply.py` turned the verdicts into the changes below. The rows
behind every number are in `data/content-check/run-2026-11-15/lists/<name>.json`.

## Verdicts

| Verdict | Sources |
|---|---|
| confirmed | 7,901 |
| corrected | 1,177 |
| same document as another source | 478 |
| wrong contest | 407 |
| copy is not the document | 370 |
| cannot tell | 44 |
| no copy to read | 1,189 |

## Applied to the catalogue (high confidence only)

| List | Sources | What was done |
|---|---|---|
| `retier` | 990 | roles set to what the document is |
| `scope` | 1 | scope added |
| `move` | 58 | moved to the edition the document is about |
| `remove-wrong` | 44 | removed: about a contest that is not in the catalogue |

Most common role changes:

| From | To | Sources |
|---|---|---|
| standings | scoreboard | 529 |
| scoreboard+problemset | problemset | 83 |
| standings | rankings | 46 |
| scoreboard+standings | scoreboard | 36 |
| web+scoreboard | web | 33 |
| standings+rankings | rankings | 24 |
| standings | web | 15 |
| web+standings | web | 13 |
| web | report+rankings | 13 |
| standings | scoreboard+standings | 13 |
| problemset | problem | 11 |
| scoreboard+standings | standings | 11 |
| web+scoreboard | rankings | 10 |
| scoreboard | standings | 9 |
| standings+rankings | standings | 8 |

## Listed, not applied

| List | Sources | Why |
|---|---|---|
| `year-reused` | 339 | wrong edition at an address that is reused each year or carries no number (ruling 16); needs the Wayback history |
| `not-document` | 430 | our copy is not the document or holds nothing about the contest (ruling 17); needs a recapture |
| `review` | 372 | everything else (ruling 18) |

Review list by reason:

| Reason | Sources |
|---|---|
| correction below high confidence | 308 |
| cannot-tell | 44 |
| wrong contest below high confidence | 20 |

Not-the-document list by current role:

| Roles | Sources |
|---|---|
| problemset | 158 |
| web | 95 |
| standings | 70 |
| scoreboard | 67 |
| web+standings | 11 |
| web+scoreboard | 9 |
| scoreboard+standings | 8 |
| scoreboard+problemset | 4 |
