# Data scan 2026-11-23: catalogue vs archive (agent `archive`)

Scope: how well the catalogue (worktree `contests/`, branch data-scan-2026-11-23) and the private archive
(`archive/`) agree: `archived:` pointers, index vs disk, what the copies actually contain, orphans, and
sources whose copies are missing or bad. Read-only for both. Full lists are in `data.json`; the scripts are in `work/`.

**Caveat: the archive changed while I scanned.** A capture run was writing during the scan: `index.json`
went from 19,536 captures (04:30 UTC, identical to the worktree's `data/archive-index.json`) to 19,587
(05:47). I froze a copy (`work/index-snapshot.json`, 05:47) and used it for every check below.

## How to rerun

From `findings/archive/work/`, in this order: `inventory.py` (catalogue vs index vs disk; needs
`capdirs.txt`/`capfiles.tsv` from `find archive -mindepth 4/5`), `orphans.py`, `scan.py 0 30000` (fingerprints
every capture → `scan.jsonl`), `scan_compressed.py` (decodes gzip/zstd-stored captures and fingerprints them),
`classify.py`, `twins.py`, `rollup.py` (judges each source's copies), `wrongyear.py`, `livenocopy.py`,
`webmismatch.py` (run from `contests/`), `cmsslug.py` (from `contests/`), `cands.py`, `cdx.py
recapture_cands.json 14` (repeat until done; about 1 request/s), `recap.py`, `assemble.py`. `shacheck.py` re-hashes every capture.

## Integrity: all clean

| check | result |
|---|---|
| `archived:` paths in series files | 8,827 paths on 4,816 of 12,348 sources. **All exist** on disk and all are in the index. |
| index entries vs disk | 19,587 entries. 0 missing, 0 size mismatches, **0 sha256 mismatches** (every file re-hashed). |
| capture folders vs index | 22,070 capture folders = 19,587 indexed captures + 2,483 website crawls. All 2,483 crawls are in `data/website-index.json`. The 20 folders that briefly had no index entry were the running capture; they were indexed at 05:47. |
| worktree `data/archive-index.json` | Byte-identical to `archive/index.json` as of 04:30. It is 51 captures behind now, because of the running capture. |
| contest folders whose id is not in the catalogue | 8 folders, `turkey/turkey-2011` … `turkey-2018`. These are not renamed ids. Each holds a website crawl of the old CMS finder page; the ids were removed by ruling Q1 (2026-09-07) and now live in `registry/cms-triage.yaml` (family `turkey-shells`). `data/website-index.json` still lists the 8 crawls. Harmless. |
| `archived:` pointer to a capture of a different URL | 1. In `rmc-2022`, the source `…/Rocky-Mountain-2023/standings` also cites the capture of the CMS's own wrong link `…/Rocky-Mountain-2022/standings`. That capture is a caveated husk. The source's note already explains this, so I made no op. |
| `archived:` paths filed under another contest's folder | 19, all from sources moved between contests: brazil-first-phase-2024/2025 → `brazil/`, harbin-2010 and tianjin-2010 → `harbin-2009/`, nena-2019 → `nena-north-2019/`, seerc-2019/2022/2023 → `ukraine/`, rmc-2024 → `rmc-2025/`, tunisia-2022 → `tunisia-2024/`, ukraine-2025 → `ukraine-2024/`. The paths work; this is cosmetic. |

## Ops (3; all `ok` under `apply_scan_ops.py --check` when written at 08:54 UTC)

**Already applied.** All three changes are now in the worktree: they were applied at 09:08 UTC from `applied-urls.jsonl`, the `urls` agent's identical ops. So a `--check` of this file now reports 3 failures, each because its guard finds the new value. That is expected. Do not apply this file again.

| op | contest | what | evidence |
|---|---|---|---|
| set url | central-russia-2023 | `…/Central-Regional-2026/standings` → `…/Central-Regional-2024/standings` | `Central-Regional-2026` is the CMS page of central-russia-2025 (cms 9167). This contest is cms 7732, whose page is `Central-Regional-2024` (`data/cms-shortnames.json`; `all_contests.csv`). Because both contests cite one address, the site joins both API dumps to one source. The capture's own title reads "The 2023 ICPC Central Russia Regional Contest". **Archive side:** that dump's manifest (`central-russia/central-russia-2023/standings/api-20260904/`) also carries the wrong URL. Re-bake it (`bake_icpc_standings.py`) after applying the op. |
| remove source | cerc-2000 | web `https://contest.felk.cvut.cz/20cerc/rank.html` | `/20cerc/` is the 2020 edition. All three copies are titled "Central European Regional Contest 2020 in Prague", and cerc-2020 already has this URL as its scoreboard. The content check had moved it from cerc-2019 to cerc-2000, but its evidence was about the `/00cerc/` crawl, not this address (see D3). |
| set as_of | wf-2004 | `http://icpc.baylor.edu/icpc/finals/Standings.html`: `20020406103146` → `20040418003402` | I opened the 2004-04-18 snapshot: "2004 ACM ICPC World Finals Official Standings … Prague, March 31, 2004". The 2002 snapshot was already caveated as "shows another edition (wf-2002)". |

The other CMS-slug mismatches have no captures, so I left them to the CMS agent (`data.json` `cms_slug_mismatches`): gwalior-pune-2021 (cites cms 4500's slug), kanpur-2022 (`ICPC-Mathura-2023`; should be `Asia-Kanpur-2023`), kharagpur-2020 (should be `Kharagpur-2021`), and wuhan-2025 (slug unknown).

## Findings

**Copies that contradict their kind or name.** I fingerprinted every capture: HTML title and visible text, magic bytes, error, login, bot-check, parked and spam patterns, and shared bytes. Then I judged each source's copies against its roles.

- **226 bad copies have no `content_caveat`.** These count as "held" on the site:
  - **148 are byte-identical to a capture that already carries an intrinsic caveat** (husk, error, login and the like, or the content check's "not the document"). Examples: korea-2016…2025 empty Spotboard shells; kabul-2020/23/24/25 "DOLANTOGEL … Bandar Toto" gambling spam on the expired domain; thailand-2009/2011 "BK8" casino spam; tehran-2015…2017 boards; awc-2024/2025 Next.js landing; cerc-2002/2003 MIMUW stub; ecna-1989 directory listing.
  - 37 husks: JS app shells. These are kyrgyzstan-2005…2025 `olymp.krsu.kg` (20 captures, 2026-11-22), tianjin-2010 and romania-2013 (`acm.tju.edu.cn` now a Vue app), shenyang-2026 xcpcio, amritapuri-2020 codedrills, aec-2020/2021 luogu, awc-2024.
  - 21 type mismatches, where a `.pdf` is really HTML:
    - GitHub blob viewer pages (egypt-2019/2020/2024, ethiopia-2020, nigeria-2016/2017, senegal/togo-2017, togo-2016, tap-2014);
    - soft-404 homepages (kanpur-2020/2024/2025 "ICPC Kanpur Regional 2026", nwerc-2016 "University of Bath", ukiepc-2014 "UKIEPC");
    - a Google sign-in page (swerc-2006);
    - a MediaFire viewer (vietnam-national-2014).
  - 5 directory listings filed as results (brazil-first-phase-2014/2015, ecna-1989, lethbridge-2014, palestine-2022 frozen).
  - 5 login pages (qingdao-2016/2018 `acm.upc.edu.cn` "登录 - i上编程" (dēnglù, "log in" – i Shàng Biānchéng, "i-Programming")).
  - 3 bot checks (dhaka-2025 standings and teams, ecna-2008 problems, ecna-2011 "One moment, please...").
  - 2 copies of the WISV homepage (38,290 B): bapc-2020 and bapc-prelims-2021 external-standings.
  - The rest are smaller groups. Full list: `uncaveated_bad_captures`.
- **130 of the 226 were fetched on or after 2026-11-14**, after the last not-there audit. Later rounds fetched the same junk again under a new capture folder, and nothing caveated the new copy. See D1.
- **Effect on the site:** 43 sources show as *held* only because of such twins (`recapture` category `held-only-by-junk-twins`). Example: the korea-2016 scoreboard locator in `data/resources.json` has two held resources, both empty Spotboard shells.

**Sources with no good copy.** Every source's copies were judged (website crawls counted when they are not shell or empty): 11,339 held, **503 only bad copies**, 506 no copy at all.
- Of the 503: 168 are already on a content-check list (recapture or year-reused), 213 have only caveated copies, and 45 are new.
- **351 sources whose address is live/changed/unknown have no good copy** (`live_without_good_copy`). Of these, 169 were never captured, mostly `web` sources of 2026 editions; 182 hold only bad copies.

**Compressed bytes stored as-is.** 497 captures are gzip and 10 are zstd. One more (wf-2024 `icpc2024.pdf`) is neither PDF nor gzip/zstd, probably brotli; I could not verify this without installing a decoder. 505 of them came from Wayback. `audit_not_there.py` and `capture_urls.py` do not decode them; only `content_check_pack.py` does. So these copies were never audited: 53 are caveated, and the rest have never been looked at. Decoded, 2 are PDFs (pakistan-2025 Event-Report, wf-1983 `1983.pdf`) that tools see as "not a PDF". Decoded, 21 more are the Baekjoon closure notice (all caveated). List: `compressed_stored_captures`.

**Wayback time recorded vs served.** For 636 Wayback captures, the recorded `wayback_timestamp` is the timestamp we asked for, not the one Wayback served (`final_url`). That breaks the rule in DEFINITIONS.md ("the snapshot's own timestamp"). 386 differ by more than 30 days, up to 4 years (e.g. tehran-2001 recorded 2002-06-28, served 2006-09-25). 356 of these are from the 2026-11-22/23 per-problem top-up (`wayback_pick: pinned by catalogue wayback link`). Another 972 older Wayback captures have no `wayback_timestamp` at all. The capture-folder names carry the requested time too.

**Orphans.** 2,837 captures have a URL that no contest source cites:
- 2,339 are per-problem pages cited by `problemsets/*.yaml`. Fine.
- About 391 are statement attachments of cited judge pages (379 `qoj.ac/download.php?type=statement` PDFs from today, plus Codeforces gym attachments). Fine.
- About 60 are addresses the catalogue dropped. Most went on purpose, through the content check's `remove-wrong` (aec-2019/2023 gyms, north-russia-2019…2024 `nwq-*-statements.pdf`, japan-2006/2014 problems, tap-2020, swerc-1998, tehran-2010 editorial, south-africa-2008 IOI blog, taiwan-ncpc-2007/2013, turkey-2010).
- About 20 left with no trace I could find (see D5).

80 more captures are filed under a contest whose URL now belongs only to other contests, after moves. They are joined by URL, so it is cosmetic. 237 result captures of cited sources are not in the source's `archived:` list: 151 caveated, 86 not, mostly from the 09-01 and 11-22/23 rounds.

**Website crawls shown under another address.** `build_site.py` attaches a contest's primary crawl to its first `web` source even when the crawl's seed is not that source. This happens for 547 contests:
- 181 where the seed is a page below the web source (fine);
- 346 on the same host but a different path (e.g. armenia-2004…2024 crawls of `neerc.ifmo.ru/archive/YYYY.html`, shown under `neerc.ifmo.ru/subregions/armenia.html`);
- **20 on another host**, which is plain junk: crawls of `facebook.com` (algeria-2024, egypt-2011, palestine-2014, turkey-2010), `t.me` (ethiopia-2019/2022), the `archive.org` root (socal-1990/1991/1993), a Bolivian law gazette (bolivia-national-2010), image files (gran-premio-centroamerica-2023, nena-atlantic-2008).

Separately, 691 crawls have a seed that no source cites at all (524 of them non-empty).

**Wrong-year titles (suspects; title-based).** 91 sources have an uncaveated copy whose title names only other years. 49 of them are already on content-check lists. In 14 of the rest, the newest copy (the one the site shows) is the wrong year. Examples:
- bapc-2021 `scoreboard.bapc.eu`, as_of 20241103 = "bapc2024test", the only snapshot;
- coimbatore-2005 `amrita.edu/icpc/`, newest copy "ICPC 2021";
- poland-2023 amppz news pages, live copy "AMPPZ 2026";
- mausa-2006 (2012 summary);
- vietnam-2010/2013;
- nena-east-2017.

I checked some by eye; false positives are in `false_positives_checked_by_eye` (e.g. seerc-2012, whose title is a stale template).

**Baekjoon is serving again.** The 2026-11-22 live capture of `acmicpc.net/category/detail/4319` is a real "BAPC 2024" category page (asset version 2026111301). My own request today got the same: HTTP 200, real content. Yet 862 of the 863 Baekjoon sources are `url_state: dead`, and 134 have no good copy.

## Items for discussion with Fredrik

**D1. Should the "bad copy" mark go by content (checksum) rather than by capture?**
- Today a caveat marks one capture. Every later capture of the same bytes counts as held again: 148 such copies, and 43 sources look held that are not.
- *For marking by checksum:* a husk or an error page is junk wherever it shows up, and the site would stop counting it at once.
- *For keeping per-capture marks:* "shows another edition" is only true for one contest. I already excluded those caveats and `generic-shared`.
- Examples: korea-2016 scoreboard; kabul-2023 standings (gambling spam); kyrgyzstan-2005 (`olymp.krsu.kg`, a JS app).
- **Recommendation:** have `apply_not_there.py` and `apply_content_check.py` also mark every capture with the same sha256 when the reason is intrinsic. Re-run `audit_not_there.py` after every capture round, and teach it to gunzip/zstd first (see D2).

**D2. Should stored gzip/zstd/brotli bodies be decoded?**
- 508 captures keep compressed bodies. The raw-bytes rule says never edit, but the auditing tools don't decode, so 455 copies were never audited, and 2 real PDFs look like junk.
- *For decoding at capture time from now on:* "raw bytes" should mean the document, not its transfer encoding.
- *For decoding only in the readers:* it keeps the immutability promise for what is already held.
- Examples: `wf/wf-1983/problemset/20250401-wayback-c35f5413/1983.pdf` (gzip of a valid PDF), `pakistan-2025 …/Event-Report_Regionals-2025.pdf`, wf-2024 `icpc2024.pdf` (likely brotli).
- **Recommendation:** decode in `capture_urls.py` from now on (record `content_encoding` in the manifest). Add a decode-on-read helper to `audit_not_there.py` and the replay bake for the 508 already held.

**D3. Should a website crawl show only under the address it crawled?**
- `build_site.py` falls back to `webs[0]`, so 547 contests show a crawl of another address as the copy of their web source. 20 of these are junk on another host.
- This also misled the content check: it judged the crawl shown under cerc-2019's web source and moved `20cerc/rank.html` to cerc-2000 (fixed by an op above).
- *For keeping the fallback:* many seeds are deeper pages of the same site.
- *Against:* it presents copies of address A as copies of address B.
- **Recommendation:** attach a crawl only to a web source whose URL is the seed or a prefix of it. Treat the 20 other-host crawls as junk (list `website_crawls_shown_under_other_address`, class `different host`). Review the 346 same-host-other-path crawls by host.

**D4. Is Baekjoon back, and should the closure rule change?**
- The brief says only snapshots before 2026-04-27 are real, but acmicpc.net served real pages on 2026-11-22 and today.
- *For re-checking now:* 862 sources marked dead, and 134 without a copy, could be captured live.
- *Against:* it may be a temporary or read-only mirror.
- **Recommendation:** re-run the live check on the 863 Baekjoon sources, and capture the 134. Keep the closure-notice snapshots (2026-06-18) caveated as they are.

**D5. Should the ~20 dropped addresses we hold copies of come back?**
- These are organiser and news pages captured as `web-mirror` in September/October whose sources are gone, with no `remove-wrong` or other trace I could find.
- *For re-adding:* they are organiser reports about the edition: inzva reports for turkey-2020…2023, algoleague boards, upb.ro/cronicaromana for romania-2020, lnu.edu.ua for ukraine-2024, the algotester board for ukraine-2023.
- *Against:* they may have been dropped on purpose when `also_at` went away.
- Examples: `turkey/turkey-2021/web-mirror/20221124-wayback-b95d7c29` (inzva 2021 report); `ukraine/ukraine-2023/web-mirror/20241206-wayback-b2b9cfce`.
- **Recommendation:** re-add them as `report` (or `web`) sources with `as_of` = the held snapshot, unless you remember dropping them. List: `orphan_captures.rest`, artifact `web-mirror`.

**D6. Where an address only ever served a later edition, keep the source as lost or remove it?**
- *For keeping it as lost:* the CMS link proves the address was the contest's.
- *For removing it:* nothing shows it ever served this edition.
- Examples:
  - bapc-2021 `https://scoreboard.bapc.eu/` (as_of 20241103, the only snapshot is "bapc2024test"; the CMS listed it for bapc-2021);
  - wf-2001 and wf-2003 `icpc.baylor.edu/icpc/finals/Standings.html` (as_of 2002, no snapshot from their year; WF 2003 has no snapshot at all);
  - coimbatore-2005 `amrita.edu/icpc/` (only copy shows 2021).
- **Recommendation:** for each, drop the wrong `as_of` and keep the source as lost (the address was the contest's). Set `as_of` to the year (`'2003'`) where the address's role is certain.

**D7. Should the Wayback time follow the served snapshot?**
- 636 captures record the requested time instead of the served one. This misdates copies by up to 4 years and can hide closure-era snapshots.
- **Recommendation:** fix `capture_urls.py` to take the timestamp from `final_url`. Backfill `wayback_timestamp` in the index from `final_url` (manifests unchanged, or a `served_timestamp` field). List: `wayback_timestamp_recorded_not_served`.

## Recapture list (`data.json` → `recapture`, 199 sources)

CDX was queried for every URL, about 1 request/s. A suggested snapshot is given where one exists other than the bad one we already hold:
- earliest after the contest date;
- a "before contest date" pick is flagged as such;
- 41 sources have a pick.

Breakdown:
- 54 new only-bad sources;
- 44 held only by junk twins;
- 101 whose copies are all caveated and not on a content-check list.

Hints by host:
- GitHub blob URLs: fetch `?raw=1`;
- Google Drive / MediaFire viewers: use the download link;
- JS apps (`olymp.krsu.kg`, xcpcio, codedrills, luogu contest, Spotboard): `capture_browser.py`.

Also capture live: the 169 never-captured live sources (`live_without_good_copy`, kind `no-copy`) and the 134 Baekjoon sources (D4).

## Not done / limits

- The content judgments are pattern-based. I checked about 40 by eye; the wrong-year list is suspects only.
- The website crawls were not fingerprinted page by page; only `website-index` shell/empty flags were used.
- I did not decode brotli (I would have needed to install a package).
