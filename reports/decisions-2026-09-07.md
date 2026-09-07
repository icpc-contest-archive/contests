# Open decisions — 2026-09-07

Numbered Q1–Q12 for easy reference (old D-numbers from the flight pack are retired).
Each: the evidence, the case both ways, my recommendation. Rules cited are your D1
real-contest rules (R1 single-uni, R2 unique problems / sibling-shared OK where the
split gates advancement, R3 must gate the WF path, R4 lean not-online with force-majeure
exception) and the identity lens.

## Q1 — Turkey 2010–2018: what are these rows?

**Evidence.** CMS: turkey-2010 has **21 teams (18 accepted), dated 2010-09-13** — a real
registered event. turkey-2011..2015: **0 teams, no dates** — empty shells. 2016–2018: no
CMS substance either. inzva (2019 organizer, 87 teams accepted in CMS) claims theirs was
"the first official Turkish programming contest ever organized"; two research passes
found no Turkish site 2010–2018 and Turkish teams documented traveling to SEERC abroad.
2021–2023 ran on algoleague (scoreboards recovered) with empty CMS rows.

**For keeping all rows:** CMS rows exist for most years; a registration shell still
documents intent. **Against:** zero teams = nothing gated anything (R3); no venue, no
problems, no participants — these aren't contests by any of the four rules; keeping them
inflates "real contest" counts and the dark-list forever.

**Recommendation.** Three buckets: keep **turkey-2010** (CMS proves it; add a note that
it contradicts inzva's "first" claim); move **2011–2018** to the ledger as never-held
registration shells (lethbridge treatment); keep **2019–2023** mainline (real events;
algoleague capture queued).

## Q2 — Ukraine: merge region rows into one contest per year?

**Evidence.** 2025 regulations verbatim: Stage II runs *simultaneously at all base
universities on a common server with one problemset* (regions at LNU Lviv, NURE Kharkiv,
etc.). Our existing ukraine-<year> rows are already Stage-II-dated; unified national
standings exist at acmallukrainian.ho.ua 2017–24. Stage III finals is a separate, later
event we don't yet model.

**For merging (one contest/year):** one set, one server, one merged ranking = one
contest with distributed venues (R2's sibling-shared clause is satisfied by design);
identity lens says the regions have no separate identity — they are named as fractions
("1/4 першості світу"). **Against:** per-region rows carry venue/host detail that a
merged row flattens; NERC quarterfinals stayed separate rows — but those have distinct
problemsets and dates, so the analogy fails.

**Recommendation.** Merge region rows into ukraine-<year> (venues into location/notes),
and add the missing **Stage III finals layer** as its own edition where evidenced.

## Q3 — Brazil First Phase: mainline?

**Evidence.** Same-day onsite at 42–54 university sites, 556–1,025 teams; **own
SBC-authored problemset** (statement PDFs titled "Sub-Regional Brasil do ICPC"); ~65
teams advance by published vaga rules to the Fase Nacional; online only 2020–21.

**For mainline:** passes every rule — own problems (R2), massive multi-site onsite (R1,
R4; 2020–21 online is textbook force majeure), published advancement gates the WF path
(R3). **Against:** the name "Primeira Fase" reads as a phase of the Brazil contest, not
an event with own identity — but identity is more than a name: own problemset + own
advancement rules is exactly what "preliminary with identity" (BAPC-prelims/NENA
precedent) looks like.

**Recommendation.** Mainline, own series, editions from SBC records.

## Q4 — Vietnam National: mainline despite online judging?

**Evidence.** Gates the Asia Vietnam regional **in writing** (≥1 problem solved required
for selectability); runs ~1 month before it; organized by VAIP; judge is online (Kattis
2018–19, VNOJ 2024) but teams sit at **proctored multi-site centralized venues**.

**For:** hard R3 pass (written gate); proctored physical sites = the GP-Mexico
"presencial-distribuido" pattern you already ruled IN — the judge being remote doesn't
make the contest online in R4's sense. **Against:** R4 purist reading — delivery
platform is an online judge and site discipline varies by year; evidence for proctoring
quality pre-2018 is thin.

**Recommendation.** Mainline (R4-borderline noted per edition where venue evidence is
thin).

## Q5 — Kazakhstan octafinal + Moscow qual + NERC quals: one policy?

**Evidence.** NERC vocabulary: qual = "1/8 финала", subregional = "четвертьфинал", NERC
= semifinal. The quals are **online by design** (NWRRC's was online in 2019, pre-COVID,
and still is), no venue, no own name — pure fractions of the parent.

**For part-of-parent (no own rows):** fails R4 (online by design, no force majeure),
fails identity (named as a fraction), no venue (R1-adjacent). **Against:** they do gate
(R3) — but so does every internal cut-off line; R3 alone doesn't make a contest.

**Recommendation.** One policy, all three instances: part-of-parent — ledger rows with
reason "preliminary", no catalogue editions.

## Q6 — Caribbean CFQ 2020+: continue the series or cut at 2019?

**Evidence.** 2010–2019: per-country simultaneous onsite nationals on one shared set
(already ruled mainline, series ends 2019). 2020+: replaced by **one online contest**
(CFQ/Eliminatoria) that still is the only gate to the Caribbean Finals. It stayed online
after COVID ended.

**For including 2020+:** unbroken function (R3: sole gate), same community, and cutting
at 2019 leaves the gate undocumented. **Against:** online-by-design once COVID passed =
R4 fail exactly like the NERC quals (Q5); including it while excluding NERC quals is
inconsistent unless the "own identity" difference carries it (CFQ has its own name,
registration, and single-event character — the NERC quals don't).

**Recommendation.** Include 2020–21 (force majeure), and from 2022 keep them but as
non-mainline registry entries — unless you weigh own-identity above R4, in which case
mainline throughout. This is the genuinely close one.

## Q7 — Afghanistan: stub or ledger?

**Evidence.** CMS rows exist; no artifacts, no site, no independent trace found in two
research passes; country context makes contemporaneous web evidence unlikely even if
held.

**For stubs:** CMS registration + the archive's completeness mission; absence of web
evidence isn't absence of the event in this region/era. **Against:** with zero teams or
results in CMS (same shell pattern as Turkey 2011–15), there is nothing to catalogue but
the intent.

**Recommendation.** Match the Turkey rule you pick in Q1: shells with zero
teams/results → ledger; any year with accepted teams → keep with "no artifacts
recoverable" note.

## Q8 — Sub-holds: Malaysia, Philippines, DPRK

Same shape as Q7, smaller. Recommendation: apply the Q1/Q7 shell rule mechanically and
I'll bring back only the years that have CMS substance for individual look.

## Q9 — Classification audit (560 flags): approve the mechanical pre-clean?

**Evidence.** 194 husk-dead (byte-signature-provable empty captures), 252 not-results,
219 wrong-year — with proven rotating-domain traps (germany-2012/15 hold the *current*
GCPC-2026 site; poland-2023 = AMPPZ-2025 shell; xian-2014/17 = 2019 content). 7
caveated.

**For mechanical:** husks and JS shells are provably content-free; requeue with pinned
wayback timestamps both fixes them and the rotating-domain family; recapture is now
cheap (fleet + host-leasing). **Against:** wrong-year captures sometimes have adjacent-
era value (a 2008 header on a 2010 page still documents the host); blanket delete loses
that nuance.

**Recommendation.** Mechanical pre-clean for husk + JS-shell classes only (delete +
requeue pinned); wrong-year cluster gets a per-cluster list for your eyeball, seeded
with my keep/requeue suggestion per cluster.

## Q10 — D6 leftovers (audit-leftover-fixes.json)

Four sub-calls: **(a) lethbridge-2020..24** "suspected not held" notes — no trace
anywhere, matches the shell pattern → apply notes (or ledger per Q1 rule).
**(b) nzpc-2000/01/03/14 adds** — proof: the ~mjd problemset archive has per-year PDFs →
apply. **(c) erc-1983..87 adds** — thin, but ChipCie's archive now provably reaches ERC
1988, strengthening series continuity → apply with pre-CMS caveat notes.
**(d) thailand-2024 add** — almost certainly duplicates thailand-national-2024 from the
family ruling → drop after I verify the dedupe.

**Recommendation.** Apply (a)(b)(c), drop (d) after dedupe check.

## Q11 — Schema: where do replacement URLs and problemsets live?

**Evidence.** ~500 verified round-9 URLs were skipped as "web present" — they're
*replacements* for entries whose recorded web URL is dead; the apply tool has no slot.
51 problemset candidates are parked for the same reason (no problemset field/apply
path). Without a slot, none of this reaches the capture queue.

**Options.** (a) Replace `web:` with the live URL, demote the dead era-URL to a
wayback-pinned note — keeps schema flat but demotes the historical identity URL.
(b) Add `mirrors:` (list) + `problemset:` fields — preserves era-URL primacy; capture
queue includes them; costs schema growth. (c) Do nothing — the research value strands.

**Recommendation.** (b): era URL stays canonical in `web:`, replacements/mirrors get
captured, problemsets become first-class. I'd extend validate + make_capture_queue the
same day.

## Q12 — The 18 "suspect" verify verdicts

The verifier's keyword heuristic can't see inside PDFs or terse index pages, so most
suspects are false alarms on exactly the round-9 treasure. Promote to verified:
**karrels ec92–ec97 + weur94 indexes** (live 200s, ~1.1–1.4KB index pages — the
verifier itself just proved the host serves them), **ChipCie erc-1990 scoreboard.pdf +
nwerc-1995/96 PDFs** (200s at 212–400KB), **amritaicpc 2025 problemset PDF** (326KB).
Reject: **icpc.global/community/history-icpc-1991** and the **colombia finder** URL
(both 2.8KB JS shells), **harbin acmicpc.info** (114B husk). Eyeball needed (3):
**maratona 1997 result.html** (6KB but no "1997" on page — may be an undated era page),
**turkey-2021 algoleague** (JS-rendered, year absent from static HTML — browser pass),
**taiwan-ncpc 2015/2016 nsysu page** (one zh-tw problem-bank page covering all years —
fine as source, questionable as per-year problemset link).

**Recommendation.** Bulk-promote the 12, reject the 3, I browser-check the 3 eyeballs.

---
Answer by number ("Q3 yes, Q6 registry from 2022, …") and I'll execute in one batch:
catalogue edits, ledger moves, schema extension, re-validate, and the next capture top-up.
