# Roadmap (v2 backlog)

v1 (this repo + archive + replay, 2026-08) shipped the catalogue, validators, the site,
and baked replay of already-captured scoreboards. Deliberately deferred:

- **Website capture pipeline** — bounded crawler with map-then-fetch, per-site manifests,
  link-closure completeness checks; wayback-CDX mode for dead sites; `site_state`
  (live / repurposed / dead) per web URL.
- **SPN pass** — submit every catalogued URL to Save Page Now, record job results and
  wayback timestamps in `results[].wayback`; priority queue for rows whose *only* result
  URL is already wayback-only.
- **CMS reconciliation job** — diff catalogue + triage against the live
  `/api/contest/public/` hierarchy; report new/changed/removed ids on a schedule.
- **Archive-public mirror** — CI-generated filtered clone of the archive repo
  (share tiers, takedown exclusions).
- **Normalized standings** — extract clean per-contest rank/team/solved tables from the
  captured scoreboards and the API standings dump; verification workflow.
- **Problemset links** — `problems:` references into the icpc-problem-archive org; the
  public all-statements repo.
- **Additional replay shards** as the archive grows past ~1GB per Pages repo.
- **Pre-1999 backfill** — the big cataloguing gap: 37 contests recorded before 1990
  against a hierarchy that existed from 1977.
- **Data/enrichment passes** — locations (only WFs have them), venues (none),
  the 69 unknown parents, rotating-host flags for Asia city series.
- **Licensing** — pick data + code licenses before wide announcement.
