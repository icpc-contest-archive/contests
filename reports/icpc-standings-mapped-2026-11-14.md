# ICPC standings mapped by content, 2026-11-14

The `icpc_standings` role is gone. Each source that had it now says what its page holds; `tools/drop_icpc_standings.py` did it from the fetch of every standings page (2026-11-13) and the copies rendered from the API dumps.

| became | sources |
| --- | --- |
| nothing | 301 |
| rankings | 14 |
| standings | 1338 |

`nothing`: the page has no rows. The role is gone; a source with no other role is removed and recorded in `data/icpc-standings-empty.json`.

## Not plain standings

- bapc-prelims-2021: standings, 167 rows (no ranks)
- bapc-prelims-2023: standings, 184 rows (no ranks)
- chennai-2024: rankings, 105 rows
- dhaka-2010: standings, 142 rows (no ranks)
- jinan-2020: rankings, 498 rows
- lethbridge-2014: rankings, 29 rows
- south-pacific-division-2024: rankings, 119 rows

## Not read: filed as rankings, to be looked at

Not CMS finder pages, and we hold no copy, so the content was not read.

- south-pacific-2004: http://icpc.baylor.edu/icpc/regionals/ViewRegionalStandings.asp?ContestID=679
- wf-1990: https://icpc.global/community/history-icpc-1990
- wf-1991: https://icpc.global/community/history-icpc-1991
- wf-1992: https://icpc.global/community/history-icpc-1992
- wf-1993: https://icpc.global/community/results-1993
- wf-1994: https://icpc.global/community/results-1994
- wf-1995: https://icpc.global/community/results-1995
- wf-1996: https://icpc.global/community/results-1996
- wf-1997: https://icpc.global/community/results-1997
- wf-1998: https://icpc.global/community/results-1998
