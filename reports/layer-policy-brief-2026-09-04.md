# Layer-policy decision brief — below-regional contests in the catalogue

*2026-09-04. Question on the table since the 09-02 audit (§3): the catalogue includes
nena-east/west, bapc-prelims, and the NEERC country contests, but excludes the same layer
elsewhere (Ukraine oblasts, Brazil First Phase, national tournaments, online prelims).
Either those come in, or the included ones need an explicit carve-out. This brief gives the
evidence and framed options. Sources: your own icpc-history contest-inventory (the five-tier
hierarchy with feeder mappings), archive/notes/cerc-national-feeders.md, the CMS registration
DB (team counts), and the current catalogue.*

## 1. Your own model already frames this

The icpc-history inventory classifies every ICPC-registered contest into five prime tiers —
**finals / championship / regional / sub-regional / preliminary** — with explicit feeder
edges (`ukraine-east → ukraine → seerc`). Totals there: 251 regional series (2,285 editions),
**249 sub-regional series (1,189 editions)**, **38 preliminary series (226 editions)**.

The catalogue today = *all* of finals+championship+regional, **plus an ad-hoc subset of the
lower two tiers**, adopted family by family:

| in catalogue today | tier in your model | editions |
|---|---|--:|
| nordic, bapc, ctuo, poland, germany, hungary, romania, ukraine (national), croatia, slovenia, bulgaria, turkey, ukiepc, cyprus, greece, sweden | sub-regional | ~250 |
| nena-atlantic/central/east/west/north | sub-regional | 59 |
| naq, alberta, lethbridge | sub-regional | ~40 |
| armenia…uzbekistan, moscow, urals, taurida, east-siberia… | **regional** (post-2017 NERC structure) | ~300 |
| **bapc-prelims** | **preliminary** | 16 |
| **south-pacific-central/east/west (+division)** | **preliminary** | ~20 |

So the *de facto* rule is roughly "sub-regional in, preliminary out" — with exactly two
preliminary-tier exceptions already grandfathered in (bapc-prelims, South Pacific divisions),
both admitted because they carry real public standings.

## 2. The excluded families, with evidence

CMS registration counts ("real" = editions with ≥5 registered teams; the DB *understates*
reality — see §3):

| family | tier | real eds | span | med. teams | max | notes |
|---|---|--:|---|--:|--:|---|
| **Ukraine oblast contests** (E/W/N/S/C/Kiev/SW) | preliminary | **80** | 2011–2027 | **123** | 241 | 6–7 per year, every year incl. wartime; the richest excluded trove |
| **Brazil First Phase** | sub-regional | 18 | 2009–2027 | **641** | 1025 | the qualifying phase of brazil finals |
| Gran Premio de Mexico | sub-regional | 12 | 2016–2027 | 834 | 1281 | |
| Gran Premio de Centroamerica | sub-regional | 9 | 2019–2027 | 69 | 115 | |
| Torneo Argentino (TAP) | sub-regional | 14 | 2013–2027 | 85 | 191 | |
| Bolivia (Preliminary/Competencia) | sub-regional | 17 | 2010–2027 | 156 | 293 | |
| Colombia Maratón Nacional | sub-regional | 19 | 2007–2027 | 102 | 123 | ACIS/REDIS, 20 years! |
| Venezuela Finals | sub-regional | 14 | 2011–2027 | 37 | 64 | |
| Torneo Chileno / Ecuador | sub-regional | 6 / 2 | 2018+ | 44 / 12 | | |
| Caribbean National + Local | sub-regional | 9+9 | 2012–2020 | 120/216 | 260 | |
| **Korea National First Round** | sub-regional | 14 | 2013–2027 | **466** | 697 | |
| **Japan Online First-Round** | sub-regional | 11 | 2017–2027 | **355** | 495 | |
| Jakarta – Indonesia National | sub-regional | 13 | 2013–2027 | **619** | 820 | |
| Vietnam National | sub-regional | 11 | 2015–2027 | 339 | 490 | |
| Taiwan Online / univ. contests | sub-regional | 11+12 | 2016–2027 | 146/40 | 294 | |
| Thailand national + group rounds | sub-regional | 6+11 | 2013–2027 | 104/60 | 116 | |
| **Tehran Internet/Online rounds** | sub-regional | 12 | 2014–2027 | **394** | 889 | |
| Dhaka online preliminaries | sub-regional | 9 | 2017–2025 | **1757** | 2580 | biggest fields in all of ICPC |
| Amritapuri online preliminary | sub-regional | 15* | 2012–2027 | ~3000 | 3108 | *DB holds recent only; series runs 2012+ |
| **NEERC qualifications** (per-subregion) | sub-regional | 65 | 2018–2027 | 174 | 581 | the layer *below* the included country contests |
| Kazakhstan Octafinal | sub-regional | 1 | 2025 | 185 | | |
| Moscow Programming Contest (open) | sub-regional | 4 | 2018–2022 | 327 | 423 | |
| **MIUP (Portugal)** | sub-regional | 14 | 2010–2027 | 17 | 22 | SWERC's feeder — peer of the included nationals |
| AdaByron (Spain) | sub-regional | 6 | 2024–2027 | 37 | 47 | |
| Moldova | sub-regional | **0** | 2014–2024 | — | — | 11 empty shells — Putka-style case, see §3 |
| Swiss subregional / Slovenian rounds / AMPPZ prelims | sub-reg / prelim | 0 | | — | — | empty shells |

## 3. Two facts that should discipline any rule

**(a) Empty registration ≠ didn't happen.** Your cerc-national-feeders note documents this
exactly: Slovenia's UPM ran continuously 2012–2026 on its own Putka judge while its ICPC rows
are all 0-team shells; Croatia and Hungary partially likewise. Moldova's 11 empty shells are
the same pattern until proven otherwise. So a rule keyed to CMS team counts would silently
erase real contests; tier + community evidence has to drive inclusion, with CMS counts as
supporting data only.

**(b) The catalogue already crossed the preliminary line, on merit.** bapc-prelims and the
South Pacific divisions were admitted because they are *results-bearing*: real ranked events
with surviving standings. That is a defensible principle — it just was never written down.

## 4. Options

**O1 — tier line at sub-regional, preliminaries out, no exceptions.**
Adds ~100 excluded sub-regional series (~600 real editions: everything in §2 except the
Ukraine oblasts and Slovenian/AMPPZ rounds). *Ejects* bapc-prelims and the South Pacific
divisions. Clean but destructive — rejected on that ground alone.

**O2 — tier line at sub-regional + grandfathered preliminaries (status quo formalized).**
Same additions as O1; bapc-prelims + SP divisions stay via an explicit, documented exception
list; Ukraine oblasts stay out (preliminary tier). Consistent, minimal surgery — but it
excludes the single richest excluded results trove (80 editions × ~123 teams).

**O3 — "own-competition" rule.** In: any contest that is the top round of its *own named
competition* (national championships, standalone tournaments). Out: internal qualifying
rounds *of* an included contest (online prelims, quals, first phases, oblast rounds).
Adds the LatAm nationals, Asia nationals, MIUP, Moldova, AdaByron (~350 editions); keeps out
Ukraine oblasts, Brazil First Phase, Dhaka/Amritapuri/Tehran prelims, NEERC quals — and
would also *eject* bapc-prelims + SP divisions unless grandfathered. Philosophically neat;
loses the biggest fields (Dhaka 1,757-team prelims, Brazil 641-team first phase).

**O4 — results-bearing rule ("if ranked public standings exist or existed, it belongs in the
archive").** Everything in §2 comes in as evidence permits, prelims included. Maximal
archive value, maximal work (~800+ editions), and the catalogue's "mainline" framing blurs.

## 5. Recommendation

**O2, plus one deliberate exception: adopt the Ukraine oblasts** (and mark Kazakhstan's
octafinal the same way if it recurs). Rationale: the tier line matches your own model and
current practice; the grandfather list makes the two historical exceptions honest; and the
Ukraine oblasts earn the third exception on the same merit that admitted bapc-prelims —
80 real, ranked, publicly-scored editions that are the primary record of Ukraine's community
through war years. Everything else at preliminary tier (Dhaka/Amritapuri/Tehran online
rounds, NEERC quals, Slovenian rounds) stays out of mainline but remains tracked in the
triage registry — nothing is lost, it is just not *mainline*.

Two implementation notes if you rule this way:

* Add a `tier:` field to series metadata (finals/championship/regional/sub-regional/
  preliminary-exception) so the rule is machine-checkable by the validator, and write the
  exception list into registry docs.
* Stub generation is mechanical for every family with CMS presence (ids, dates, team counts
  all in the DB; naming per your hierarchy slugs: ukraine-east-YYYY, brazil-first-phase-YYYY,
  miup-YYYY, tap-YYYY, korea-first-round-YYYY…). Slovenia-rounds/Moldova need non-CMS
  sourcing (Putka archive; Moldova TBD) if ever admitted — flagged, not blocking.
* Independent of the ruling: your inventory lists **allegheny (1978–1991, 14 eds)** and
  **capital (1979–1991, 13 eds)** as NA sub-regionals — the catalogue has neither. Under
  O2 they come in with the rest; they are also simply a discovered gap worth stubs even
  under the status quo.

## 6. Impact summary (O2 + Ukraine exception)

~105 new series / ~700 new editions in mainline, of which ~620 have CMS ids for instant
linking; an estimated 400+ carry finder standings and ~200 have independent web/results
sources already known (icpclatam wayback, NERC quals pages, Putka, contest sites). The 850
triage-proposed rows resolve almost entirely: minor/first-round classes stay excluded,
sub-regional classes migrate to mainline per the rule.
