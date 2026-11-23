# la-wayback: Live Archive links -> old LA address + Wayback snapshot (data scan 2026-11-23)

Task: every `judge: livearchive` link in problemsets/*.yaml (5,971 in the worktree) gets the old LA address of its own problem
and an `as_of` snapshot (ruling 2026-11-22: LA is gone, links go to Wayback snapshots of the old pages, never to UVa).

## Result (ops.json: 9,429 ops, all `ok` with `--check`, re-run at the end)

| outcome | links |
| --- | ---: |
| already fixed by `judge-links` (in the worktree, skipped) | 90 |
| **problem-page snapshot** (ops.json) | **5,628** |
|   - plain address `...&Itemid=8&page=show_problem&problem=N` | 1,908 |
|   - the `&category=C&` form (only form snapshotted) | 3,588 |
|   - another form (`option=onlinejudge`, `Itemid=99999999`) | 132 |
| **statement file snapshot** (`/external/<LA div 100>/<LA>.pdf`, ops.json) | 40 |
| no snapshot of problem page or statement, link left (list below) | 204 |
| LA number unreadable / catalogue discrepancy, link left | 9 |

So 5,758 of 5,971 (96.4%) now carry a snapshot: 5,718 (95.8%) the right problem page, 40 the statement. Ops: 5,668 `as_of` sets plus
3,761 `url` sets (3,721 problem-page links whose internal number was wrong or form changed, 40 statement links); each `url` op is
guarded with `old`, each `as_of` op with `old: null`. The `as_of` op comes first, selecting the link by its old url.
1,858 of the 5,628 page links had a wrong internal number (they opened another problem); the rest only needed `as_of`.

## How (rerun from `work/`)

1. `cats_raw.txt`: one Wayback CDX query for every 200 snapshot under `icpcarchive.ecs.baylor.edu/index.php` with `category=` in it
   (823 distinct category numbers; 45,734 URL variants incl. show_problem/problem_stats pages). `show_nocat.txt`: same for show_problem
   without category. With `judge-links/work/net/cdx_la_show.txt` and `cdx_la_ext.txt` these give the snapshot inventory.
2. `fetch_cats.py` (resumable, 6-12 shards, about 1 request/s overall): fetches the latest snapshot of every category page (`cat/N.html`,
   823 of 823; 8 needed a second snapshot variant). Each lists `LA number - title -> internal problem number`: 6,642 LA numbers.
   (judge-links held 283 category pages / 2,215 numbers; this covers all but 37 of the catalogue's LA numbers.)
3. `analyze.py`: for each link, the internal number of its LA number whose title equals the catalogue name (or an other_name);
   5,932 of 5,934 mapped links match by title. `plan.py`: per link the snapshot choice: plain page, else category-form page, else other
   form (latest 200 snapshot of that exact address), else statement PDF (or html), else the old host `livearchive.onlinejudge.org`
   statements (none needed). `make_ops.py` writes the ops.
4. `verify.py`: sample of the chosen snapshots fetched and read (`<h3>LA number - title</h3>`): 58 fetched, 58 show the link's LA
   number and title (the other 18 attempts timed out on Wayback and were not counted). Together with judge-links' 82% estimate this
   confirms that the title match on LA's own category page is a reliable proxy; the remaining links are not individually fetched.

## Left as is (data.json)

- **204 links, 21 sets** (mostly 2016-2018 contests, LA numbers 8xxx: thailand-2017, vietnam-2015/2017, acpc-2017, amritapuri-2017,
  chennai-2017, kharagpur-2016/2017, kolkata-2016, qingdao-2017, yangon-2016 ...): category page gives the right internal number, but
  Wayback holds no snapshot of the problem page and no statement file. `ops_optional_unsnapshotted.json` (202 ops, checked ok, NOT in
  ops.json) would set `url` to the right internal address without `as_of` (202 of the 204 already have the right number).
- **9 links**: korea-2017 (5: LA 8089, 8094, 8097-8099), shanghai-2014 Top ACMers (7149), wf-2015 Asteroids and Tours (7151, 7160): LA
  number on no category page we could read, no snapshot of the statement. **nanning-2017 Abiyoyo**: its LA number 2317 is LA's
  "Control Break" (the id looks wrong; LA number for Abiyoyo unknown).
- wf-2010 "Chocolate" (LA 4794) is LA's "Sharing Chocolate"; accepted (the WF problem), name is an alias question only.

## Items for discussion with Fredrik

1. **204 links with no snapshot at all.** Question: correct the address anyway (optional ops file) or leave the wrong number? Implies:
   the link opens nothing either way in Wayback; with the fix the address is at least the problem's own, so a later capture or a Wayback
   save would be right. For leaving: nothing is verified by a snapshot and the brief says to leave such links. Recommendation: apply the
   optional file (the address is evidenced by LA's own category page), without `as_of`, and mark them lost on the site.
2. **Statement-file links (40) and the category-form links (3,588).** The category-form address (`&category=C&`) is what Wayback
   actually holds for most LA problems; the plain `judges.yaml` problem_url pattern would not open a snapshot for them. Question: keep
   per-link `url` as is (the address meant at that time) - recommendation yes; no change needed to `judges.yaml`.
3. **nanning-2017 Abiyoyo LA 2317** is a different problem in LA; fix the LA number or drop the link (example: nanning-2017 p-... "Abiyoyo").
