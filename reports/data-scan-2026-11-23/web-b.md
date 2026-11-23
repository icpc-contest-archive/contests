# web-b — missing contest websites (Europe, Northern Eurasia, Africa & Arab, Asia Pacific, Asia West, Asia East)

Scan agent `web-b`, data scan 2026-11-23. Area: contests that ran, in series whose header `region` is one of the six
regions above, with no source whose roles include `web` and no `none: [web]`. Definition used (ruling): `web` = a page or
site by the organisers or the host about that edition; a single results page is not `web`.

## How (rerunnable)

1. Targets: `work/make_data.py` (catalogue helpers, `cat.has_role(c, 'web')`, `status != upcoming`, region from the series header).
2. Leads, in this order:
   - links inside our held copies of the contest's other sources (`work/links.py` → `work/links.json`);
   - sibling editions' `web` URLs in the same series (`work/sibling_web.txt`) → the same pattern for this year
     (NNNN.bapc.eu, nerc.itmo.ru/subregions/X.html, ukiepc.info/NNNN/, icpcNNNN.algotester.com, amritaicpc.in/archive/…);
   - organisers' own lists: the ICPC China contest list `icpc.pku.edu.cn/ssxx/index*.htm` and notices `tzgg/index*.htm`,
     the ACPC events API `acpc.global/wp-json/tribe/events/v1/events`, `versenyek.inf.elte.hu/YYYY/MM/` archives;
   - Wayback CDX over the organisers' domains for the contest year (`work/cdx.py`, `work/nerc_sub.py`, and the
     domain-wide CDX for acmacpc.org / acpc.global / icpc.amrita.ac.in), every snapshot opened (`work/wb.py`) before use;
   - web search (English, and Chinese for the Asia East contests).
3. Every added page was opened (live, or the Wayback snapshot named in `as_of`). When the live address now serves a later
   edition (NERC subregion pages, amppz.edu.pl, amritaicpc.in, icpc.green.edu.bd, NNNN.bapc.eu that no longer answer),
   the source is added with `as_of` pinned to a snapshot that shows this edition. Live, year-specific pages get no `as_of`.
4. `work/build_ops.py` turns `work/found.jsonl` into `ops.json` (append to `sources`, `unique_keys: [url, as_of]`, roles
   `[web]`, note `found by the data scan 2026-11-23 (<how>)`); it skips a contest that has a `web` source in the worktree.
   Checked with `python3 tools/apply_scan_ops.py --check ../findings/web-b/ops.json` — all ops `ok`.

Note: the worktree moved during the scan (it was re-pointed to commit b8a2252, "Structure: next chains…", 09:15 UTC).
The target list grew from 362 to 380 (web roles were removed from some sources elsewhere: acpc-2022, egypt-2023,
romania-2017…2022, vietnam-national-2016/2022–2024, cerc-1995–1997, swerc-1996/2008, …) and 8 of my targets got a
`web` source from someone else (greece-2026, moscow-2026, south-russia-2026, ukraine-2026, south-pacific-2026,
south-pacific-division-2026, amritapuri-2021, morocco-2013). Ops are built and checked against the moved worktree.


## Counts

- Targets at the end (moved worktree): 381 contests that ran with no `web` source.
- **Found and prepared: 116 contests → 117 ops**, all `append` of a `sources` entry with roles `[web]` (53 with `as_of` pinned to a Wayback snapshot, 64 live).
- Looked, nothing usable found: 20 (listed in data.json with what was tried).
- Not reached (time): 245 — newest seasons were done first only for the series with a usable pattern; see the per-region table.

| region | found | nothing found | not reached |
|---|---|---|---|
| Africa & Arab | 14 | 6 | 132 |
| Asia East | 34 | 0 | 11 |
| Asia Pacific | 10 | 1 | 58 |
| Asia West | 9 | 8 | 5 |
| Europe | 19 | 2 | 35 |
| Northern Eurasia | 30 | 3 | 4 |

## What the ops add (grouped)

**NERC subregion page (as it stood for the edition, `as_of` pinned unless the live page shows this edition)** (27)

- armenia-2026 → https://nerc.itmo.ru/subregions/armenia.html
- central-russia-2018 → http://neerc.ifmo.ru/subregions/central.html @ 20181211080444
- central-russia-2021 → http://nerc.itmo.ru/subregions/central.html @ 20211207005325
- central-russia-2022 → https://nerc.itmo.ru/subregions/central.html @ 20230129195452
- central-russia-2025 → http://neerc.ifmo.ru/subregions/central.html @ 20260118072403
- central-russia-2026 → https://nerc.itmo.ru/subregions/central.html
- east-siberia-2022 → https://nerc.itmo.ru/subregions/east-siberian.html @ 20230129182732
- far-east-russia-2018 → http://neerc.ifmo.ru/subregions/far-eastern.html @ 20181224014310
- far-east-russia-2023 → https://neerc.ifmo.ru/subregions/far-eastern.html @ 20231128151714
- far-east-russia-2024 → https://neerc.ifmo.ru/subregions/far-eastern.html @ 20241102103505
- georgia-2023 → https://neerc.ifmo.ru/subregions/georgia.html @ 20231203174158
- georgia-2024 → https://neerc.ifmo.ru/subregions/georgia.html @ 20250515033359
- kyrgyzstan-2026 → https://nerc.itmo.ru/subregions/kyrgyzstan.html
- south-russia-2021 → http://nerc.itmo.ru/subregions/southern.html @ 20211206231450
- south-russia-2022 → https://nerc.itmo.ru/subregions/southern.html @ 20230129184655
- tajikistan-2023 → https://neerc.ifmo.ru/subregions/tajikistan.html @ 20240519102135
- tajikistan-2025 → http://neerc.ifmo.ru/subregions/tajikistan.html @ 20260118080923
- turkmenistan-2025 → http://neerc.ifmo.ru/subregions/turkmenistan.html @ 20260118081645
- uzbekistan-2023 → https://neerc.ifmo.ru/subregions/uzbekistan.html @ 20240415153608
- uzbekistan-2026 → https://nerc.itmo.ru/subregions/uzbekistan.html
- west-neerc-2021 → http://nerc.itmo.ru/subregions/western.html @ 20211207005256
- west-neerc-2022 → https://nerc.itmo.ru/subregions/western.html @ 20230129193940
- west-neerc-2023 → https://neerc.ifmo.ru/subregions/western.html @ 20231128154041
- west-neerc-2026 → https://nerc.itmo.ru/subregions/western.html
- west-siberia-2021 → http://nerc.itmo.ru/subregions/west-siberian.html @ 20211206230832
- west-siberia-2023 → https://neerc.ifmo.ru/subregions/west-siberian.html @ 20240415165112
- west-siberia-2025 → http://neerc.ifmo.ru/subregions/west-siberian.html @ 20260118074956

**Other host/organiser sites** (39)

- amritapuri-2022 → http://amritaicpc.in/ @ 20230322114453
- amritapuri-2023 → https://amritaicpc.in/ @ 20231202105448
- amritapuri-2024 → https://amritaicpc.in/archive/icpc_Amritapuri_2024
- cerc-2019 → https://contest.felk.cvut.cz/19cerc/
- chennai-2024 → https://iiitdm.ac.in/icpc
- cyprus-2026 → https://grcpc.upatras.gr/grcpc-2026/
- dhaka-2022 → https://icpc.green.edu.bd/ @ 20230109093645
- greece-2023 → https://grcpc.upatras.gr/grcpc-2023/
- hong-kong-2025 → https://cse.hkust.edu.hk/icpc2025/
- hungary-2019 → http://versenyek.inf.elte.hu/versenyek/orszagos-acm-verseny/ @ 20191024182754
- hungary-2024 → https://versenyek.inf.elte.hu/2024/09/22/icpc-2024/
- hungary-2025 → https://versenyek.inf.elte.hu/2025/09/18/icpc-2025/
- nerc-2025 → https://nerc.itmo.ru/regional/nef-2025.html
- nordic-2002 → https://www.ida.liu.se/projects/progcontest/progsm/2002/
- nordic-2004 → https://www.ida.liu.se/projects/progcontest/progsm/2004/
- pakistan-2021 → https://giki.edu.pk/ICPC @ 20220109110534
- pakistan-2022 → https://giki.edu.pk/icpc/ @ 20230528193131
- pakistan-2025 → https://giki.edu.pk/icpc/ @ 20251118131942
- peradeniya-2025 → https://icpc.ieee.lk/ @ 20260204103040
- poland-2024 → https://amppz.edu.pl/ @ 20241114112644
- poland-2025 → https://amppz.edu.pl/ @ 20251018200027
- qatar-2024 → https://www.qatar.cmu.edu/event/qatar-collegiate-programming-contest
- qatar-2025 → https://www.qatar.cmu.edu/event/qatar-collegiate-programming-contest-2025/
- qatar-2026 → https://www.qatar.cmu.edu/event/qatar-collegiate-programming-contest-2026/
- south-pacific-2021 → https://sppcontests.org/south-pacific-icpc/ @ 20211123041827
- south-pacific-2025 → https://sppcontests.org/south-pacific-icpc/ @ 20250909095001
- south-pacific-division-2022 → https://sppcontests.org/south-pacific-icpc/ @ 20220627092430
- south-pacific-division-2025 → https://sppcontests.org/south-pacific-icpc/ @ 20250909095001
- thailand-2025 → http://icpc.cp.eng.chula.ac.th/2025/
- tunisia-2017 → http://acmtcpc.org/ @ 20170429121436
- ukiepc-2022 → https://ukiepc.info/2022/
- ukraine-2024 → https://icpc2024.algotester.com/en
- vietnam-2020 → http://acm-icpc.olp.vn/ @ 20201204111809
- vietnam-2021 → https://acm-icpc.olp.vn/ @ 20220630013446
- vietnam-2022 → https://acm-icpc.olp.vn/ @ 20230221160025
- vietnam-2023 → https://acm-icpc.olp.vn/ @ 20231207234937
- vietnam-2024 → https://acm-icpc.olp.vn/ @ 20241208123642
- west-siberia-2020 → https://olymp.nstu.ru/contests/52/rules
- west-siberia-2022 → https://olymp.nstu.ru/contests/58/rules

**BAPC year sites carrying the preliminaries** (7)

- bapc-prelims-2012 → http://2012.bapc.eu/ @ 20131031214322
- bapc-prelims-2014 → http://2014.bapc.eu/ @ 20160813132241
- bapc-prelims-2017 → https://2017.bapc.eu/
- bapc-prelims-2022 → https://2022.bapc.eu/ @ 20221116172934
- bapc-prelims-2023 → https://2023.bapc.eu/
- bapc-prelims-2024 → https://2024.bapc.eu/ @ 20241015000407
- bapc-prelims-2026 → https://2026.bapc.eu/

**ACPC organisers (acpc.global archive pages and events calendar, acmacpc.org country pages)** (11)

- acpc-2014 → http://acpc.global/archive/y2014/ @ 20200224050220
- acpc-2016 → http://acpc.global/archive/y2016/ @ 20200224045545
- acpc-2017 → http://acpc.global/archive/y2017/ @ 20200224050225
- acpc-2018 → http://acpc.global/archive/y2018/ @ 20200921021009
- angola-2024 → https://acpc.global/event/aolcpc2024/
- egypt-2024 → https://acpc.global/event/acpc-2024-ecpc-contest-day/
- jordan-2014 → http://acmacpc.org/jordan @ 20141104183807
- jordan-2016 → http://acmacpc.org/jcpc/ @ 20190604042928
- lebanon-2024 → https://acpc.global/event/lcpc2024/
- qatar-2024 → https://acpc.global/event/qcpc2024/
- syria-2014 → http://acmacpc.org/syria @ 20140924221413

**ICPC Asia East Continent pages on icpc.pku.edu.cn (ICPC 北京总部, Běijīng zǒngbù = ICPC Beijing headquarters): ssxx 赛事 (sàishì = contests) / tzgg 公告 (gōnggào = notices)** (33)

- aec-2022 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_142613.htm
- aec-2023 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_151095.htm
- aec-2025 → https://icpc.pku.edu.cn/tzgg/29c98d873cee441ea8709973cc564217.htm
- chengdu-2024 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_158934.htm
- chengdu-2025 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_169372.htm
- chengdu-2026 → https://icpc.pku.edu.cn/ssxx/d3a6d950ffeb45a4b51bed26c6ffc2ee.htm
- hangzhou-2022 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_142611.htm
- hangzhou-2023 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_151093.htm
- hangzhou-2024 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_158937.htm
- hefei-2022 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_142607.htm
- hefei-2023 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_151092.htm
- jinan-2021 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_130711.htm
- jinan-2022 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_142608.htm
- jinan-2023 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_151094.htm
- kunming-2021 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_130715.htm
- nanjing-2021 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_130713.htm
- nanjing-2022 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_142604.htm
- nanjing-2023 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_151089.htm
- nanjing-2024 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_158935.htm
- nanjing-2025 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_169374.htm
- shanghai-2021 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_130712.htm
- shanghai-2022 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_142613.htm
- shanghai-2024 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_158938.htm
- shanghai-2025 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_169376.htm
- shenyang-2021 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_130710.htm
- shenyang-2022 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_142605.htm
- shenyang-2023 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_151091.htm
- shenyang-2024 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_158939.htm
- shenyang-2025 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_169375.htm
- wuhan-2025 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_169373.htm
- wuhan-2026 → https://icpc.pku.edu.cn/ssxx/70c9cc6c136a478aabf394b0f1d44d9d.htm
- xian-2025 → https://icpc.pku.edu.cn/ssxx/1119_icpcbjzb_169371.htm
- xian-2026 → https://icpc.pku.edu.cn/ssxx/99587d1ae53b46468022c30b43cbb01f.htm

## Items for discussion with Fredrik

### D1. Pages the organisers overwrite every year: pin `as_of` on the older siblings too?

- **Question.** The NERC subregion pages (`neerc.ifmo.ru/subregions/<x>.html`, now `nerc.itmo.ru/…`) show only the
  current edition at the top, plus an archive list. I added them for 22 older editions with `as_of` pinned to a snapshot
  that shows that edition's dates. But 260 sources on 256 sibling editions (armenia, central-russia, far-east-russia, georgia,
  north-russia … 1998–2026) already cite the same address with no `as_of`, so they all mean "the page as it is now".
- **What it implies.** Unpinned, every one of those sources is "the 2026 page", which says nothing about, for example,
  georgia-2009. Pinned, each gets its own copy of the page as it stood for that edition, where the Wayback Machine has one.
- **For pinning.** It follows ruling 16 (an address showing a later year gets `as_of` when a copy of the right edition
  exists), and `work/nerc_sub.py` already finds the right snapshot from the "Contest Dates" / "took place … on" line.
- **For leaving them.** The page's archive section links every year's standings, so the current page still covers
  each edition in a weak sense. Many old editions have no snapshot, so they would be kept as lost anyway.
- **Examples.** georgia-2009, central-russia-2015, far-east-russia-2012 (all `https://neerc.ifmo.ru/subregions/…html`, no `as_of`).
- **Recommendation.** Pin them. Run `nerc_sub.py` over all the siblings as a separate pass. Where no snapshot shows the
  edition, keep the source as lost.

### D2. Thin organiser pages: do they count as `web`?

- **Question.** Some added pages are by the organisers and about the edition, but they say very little:
  - ACPC event-calendar entries (`acpc.global/event/qcpc2024/`, `lcpc2024/`, `aolcpc2024/`): a date and a country.
  - ICPC China pages (`icpc.pku.edu.cn/ssxx/…`): the tentative date, slot allocation (名额分配 míng'é fēnpèi) and the
    invitation and registration guide (邀请函 yāoqǐnghán / 报名指南 bàomíng zhǐnán).
  - NSTU OlympSystem contest pages (`olymp.nstu.ru/contests/52/rules`): the contest header and date, the rules, and
    downloads of the statements and tests.
- **What it implies.** "Website: have" on the coverage page would then sometimes mean only a calendar entry.
- **For counting them.** The ruling's wording ("a page … by the organisers or the host about this edition") covers
  them, and the 2026 siblings (and algeria-2024, west-siberia-2026) already use exactly these kinds of page.
- **Against.** Coverage is meant to tell where a real site exists. A calendar entry is closer to `report`.
- **Examples.** qatar-2024, lebanon-2024 (calendar says 4–5 Oct 2024; catalogue says 2024-11-09), nanjing-2025, west-siberia-2020.
- **Recommendation.** Count the ICPC China and OlympSystem pages as `web`: they are the organisers' official page for
  the edition. Count the ACPC calendar entries too, since they are the regional organiser's own page for the national
  contest, but you could drop the three if you want `web` to mean a real site.

### D3. One page for two contests: BAPC preliminaries, Cyprus with GRCPC, Shanghai with the EC Final

- **Question.** Is a page that covers two catalogue contests a `web` source of both?
  - bapc-prelims-2012/2014/2017/2022/2023/2024/2026 → the BAPC year site (`NNNN.bapc.eu`), which carries the
    preliminaries' problems, solutions and scoreboard. Siblings 2011–2021/2025 already do this.
  - cyprus-2026 → `grcpc.upatras.gr/grcpc-2026/` (the Cyprus on-site ran as part of GRCPC 2026, and the page links the
    ICPCCyprus-2027 standings). icpc-cyprus.com has no 2026 page.
  - shanghai-2022 and aec-2022 → `icpc.pku.edu.cn/ssxx/1119_icpcbjzb_142613.htm`, labelled "2022 ICPC Asia EC 上海站"
    (Shànghǎi zhàn = Shanghai site), which is the 2022 Asia-East Continent Final (2023-03-24/26). Both contests share
    qoj contest 1197 and have separate xcpcio boards (47th/shanghai, 47th/ec-final). The same holds for 2023
    ("上海站（EC Final）", which I added to aec-2023).
- **What it implies.** These follow the ruling that a page covering several contests is a source of each. Separately,
  you may want to confirm that shanghai-2022/aec-2022 (and shanghai-2023/aec-2023) are really two contests (two CMS ids)
  run at one event.
- **Recommendation.** Keep these as added. Leave the shanghai/aec pairing to the structure agent.

### D4. Sibling `web` sources that never served their edition

These were seen while hunting. They are not fixed here, because removing a source needs its own check.

- `icpc.bubt.edu.bd/<YYYY>` (dhaka-1997…2018, 14 sources): every year path now serves the 2025 BUBT front page.
  BUBT hosted only some editions, and nothing shows these paths ever served 1997–2018. They are probably sheet-era
  guesses. Per the ruling they should be removed unless a snapshot shows the edition.
- `versenyek.inf.elte.hu/<YYYY>/` (hungary-2016, 2020–2022): these are ELTE's yearly news archives for all of its
  competitions, not ICPC pages. The ICPC posts inside them are the better sources (for example
  `versenyek.inf.elte.hu/2024/09/22/icpc-2024/`, which I added for hungary-2024).
- `http://xxx.yyy.edu` (amritapuri-2019, nanjing-2019, shenyang-2019, yinchuan-2019): placeholder addresses.
- Social-media pages used as `web` (facebook.com/…CPC for kuwait, lebanon, palestine, sudan, togo, benin, …; t.me/icpcuz).
  The ruling says a social-media post is not `web`, but an organiser's page is arguable.
- `icpc.kateb.edu.af` (kabul): the live address now serves a gambling spam page ("DOLANTOGEL"), so the domain looks
  hijacked. The kabul-2018/2019/2020 sources are pinned with `as_of`, but kabul-2025's `icpc.kateb.edu.af/blogs/…` is
  not, so its next live capture would store spam. It should be pinned to a snapshot from before the hijack, the
  2026-02-15 snapshot is still the real site.
- **Recommendation.** Hand this list to the source-roles / wrong-source agents (sr-wrong) and keep it out of this scan's ops.

### D5. Dates on the pages that differ from the catalogue (facts, not my area)

- central-russia-2021: the page says the contest takes place on October 9 and November 7, 2021; the catalogue has 2021-11-20.
- west-siberia-2021: the page says November 20, 2021; the catalogue has 2021-11-29.
- west-siberia-2023: the page says November 18, 2023; the catalogue has 2023-11-30.
- lebanon-2024: the ACPC calendar says October 4–5, 2024; the catalogue has 2024-11-09 (it was perhaps postponed).
- hungary-2024 and hungary-2025 have no date. The ELTE pages say "The Hungarian qualification contest will be held on
  October 19 [2024]" and "on October 11 [2025]", in the ELTE "Lovarda" lab.
- chennai-2024: the IIITDM page says the Chennai site regional is on 14–15 December 2024; the catalogue has 2025-01-04.
- south-pacific-2025: sppcontests.org says the Regional Finals are on 24–26 October 2025 at UNSW Sydney; the catalogue
  has 2025-10-27. south-pacific-division-2025 has no date, and the page says the Preliminary Contest is on 14 September 2025.
- **Recommendation.** Leave these to the contest-facts agent. These are pre-contest announcements, so they are weaker
  than the results pages.

### D6. Leads for other agents

- acpc-2021: `http://acpc.global/acpc2021/` at Wayback 20211205104336 is the live, frozen scoreboard of ACPC 2021
  ("Scoreboard will be frozen with 1 hour remaining"). It is a candidate `frozen_scoreboard`/`scoreboard` source.
- dhaka-2024: the host was Daffodil International University. Its news item "Daffodil International University hosts
  ICPC-2024 Asia Regional Dhaka Site on 7 December, 2024" is a host page. I did not add it, because I don't know whether
  you want host news items as `web`.

### D7. Pages that turn our fetcher away

hong-kong-2025 (`cse.hkust.edu.hk/icpc2025/`, HTTP 403) and the three CMU-Q QCPC event pages (qatar-2024/2025/2026,
Cloudflare 403) were confirmed through WebFetch, not with our device fetcher. By the ruling they are *blocked*, not
dead, but the capture round will probably not get a copy. If a copy is wanted, it has to be saved by hand through a
browser or by Save Page Now.


## Not reached

245 contests were not examined (full list with season/series in data.json, status `not reached`). The largest groups: Africa & Arab national contests 2013–2026 (egypt, jordan, lebanon, palestine, qatar, kuwait, syria, tunisia, morocco, oman, algeria, sudan, ethiopia, angola, …), nzpc 1998–2023, south-pacific 1991–1997 and its divisions, taiwan 1994–1997, vietnam 2020–2024 / vietnam-national, the 1980s erc/werc editions, and the Asia West regionals kharagpur/pakistan/chennai/gwalior/kabul/peradeniya. Promising next leads: acpc.global/events/category/contest/YYYY-MM/ month pages (2025 national contests), acm-icpc.olp.vn Wayback snapshots (vietnam), sppcontests.org snapshots (south-pacific), giki.edu.pk/icpc snapshots (pakistan), acm.iitkgp.ac.in snapshots (kharagpur), icpc.kateb.edu.af (kabul-2026), icpc.ieee.lk (peradeniya-2025).
