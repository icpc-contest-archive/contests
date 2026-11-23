# loc-b report (locations: Latin America, Africa & Arab, Asia Pacific/West/East; locations.yaml integrity)

Partial: the session was interrupted once; area 1 blank-contest fills were not completed.

## Method
- Worktree helpers (`cat.load_contests/load_series/load_locations`); series in the 5 regions: 125 series, 1,145 contests.
- Inputs: 151 `fact: location` entries in run1 contest-facts (116 high conflicts, 32 medium conflicts, 2 same, 1 medium fill). I compared each with `sites`, kept only cases where the catalogue named a different city/country, and used the official page already cited by the fact (`seen` text).
- Blank contests (no `location`, no `sites`) in my regions: 42 (list in work/in.json).
- Area 2: script over locations.yaml and all contests (see data.json).

## Ops (23, all `--check` ok): 7 contests with the wrong place + brazil-2024 text
- brazil-2025: admin "Brazilian Finals" site pointed at Campina Grande; official final page: FECAP, Sao Paulo -> br-sao-paulo-fecap.
- brazil-2024: text said Campina Grande, sites and official page say Joao Pessoa (IFPB) -> text fixed.
- malaysia-national-2016: site was `ph` (Philippines); IIUM Kuala Lumpur -> my-kuala-lumpur-iium.
- myanmar-mcpc-2019: site/text Philippines; UCSY page says Yangon -> mm-yangon.
- thailand-national-2015: Bangkok -> Salaya, Nakhon Pathom (Mahidol article).
- taiwan-2022, taiwan-2023: Taipei -> Taoyuan (official pages; CMS site label already said Taoyuan).
- south-pacific-2015: site node was UNSW Sydney, label "Regional Finals (Auckland)"; results page: AUT Tech Central -> nz-auckland-aut.
Most other facts (~125) are only more detail (institution, venue) and were not applied.

## Area 2: locations.yaml integrity (2,622 nodes)
Clean: no duplicate ids, missing parents, wrong type order, countries without iso, institutions directly under a country, duplicate name+parent, duplicate geonameid; no site ids missing from the tree.
Only unused node: `id-dumai` (report only).
`location` text vs `sites` disagreement: 189 contests flagged by a name test; nearly all are noise (admin label, "xxxx", a country name, spelling, "Internet"). Full list in data.json `mismatch`.

## Items for discussion
1. Junk free-text locations ("xxxxx" Chinese series aec/dalian/nanjing/shenyang/xian/xuzhou, "Administrative Site Location", "Sudan" for morocco-2025, "Phukett" for thailand-2016/17 with sites Bangkok/Nakhon Pathom, "UPR-B", "Nigiria"). Question: clean `location` strings or wait until the field is dropped? Recommendation: drop the field as planned; meanwhile leave. Check morocco-2025 ("Sudan" vs Ben Guerir) and thailand-2016/17 (Phuket vs sites) against official pages: both look like real conflicts, not fixed for lack of time.
2. Medium/high conflicts left for evidence: hong-kong-2019 (official page venue is in Shenzhen, catalogue Hong Kong), philippines-national-2015 (Tuguegarao vs Quezon City; no Tuguegarao node), macau-2023 (two HK sites "not available" plus Macau; text says Hong Kong first), macau-2021, nanjing-2007, shanghai-2006/2015 (ECUST vs Shanghai University), manila-2006 (Holiday Inn Ortigas vs site node `jp-asso-inter-universities...` which is a wrong-country node), taiwan-2024, kuwait-2017, vietnam-national-2025/2026, brazil-2007 (UFMG final vs 30+ site list), south-pacific-2022/2024 hosting.
3. Blank contests (42): NZPC 1998-2023 (nzpc-2012/13 have sites; the rest none): held copies show only site codes (AKL, DUD, HLZ, WEL, CCH...) so a multi-site list could be derived; South Pacific 1991-1997 results pages hold only champions (no venue). I did not fill these. Recommendation: one question for Fredrik whether site-code lists count as "primary source states location".
   Also brazil-first-phase 2005-07 (no source with location), caribbean-2009, central-america-1997, dhaka-1997, australia-1998, shanghai-2022 (xcpcio board; Shanghai is known from series), hefei/jinan/kunming-2026 (upcoming).
4. `manila-2006` site node `jp-asso-inter-universities-programming-competition` is a Japan node on a Manila contest (wrong-country node); recommend remove after check.
