# ICPC contest catalogue

A catalogue of every contest in the mainline ICPC hierarchy through history — series,
editions, advancement structure (`parent`), succession (`next`), and links to results —
plus registries accounting for every CMS DB entry that is *not* a mainline contest.

**2,400 contests · 171 series · 1977–present.** See [DEFINITIONS.md](DEFINITIONS.md) for
the data model, and `reports/open-warnings.md` for known open questions.

## Layout

```
series/<series>.yaml         one file per series (the catalogue itself)
registry/cms-triage.yaml     every excluded CMS id -> reason
registry/non-mainline.yaml   real contests outside the hierarchy
schema/catalogue.schema.json JSON Schema for the files above
tools/                       importer, validator, site generator, local server
data/import/                 the sheet export this repo was seeded from
CONVERSION-FIXES.md          what the import fixed, and what it deliberately didn't
```

## Working with it

```
pip install pyyaml jsonschema
python3 tools/validate.py         # schema + invariants; CI runs this on every push
python3 tools/build_site.py       # static site -> site/
python3 tools/serve.py            # browse locally; add ../archive for local replay
```

CI validates every push and deploys the site to GitHub Pages. Sibling repos:
[`archive`](https://github.com/icpc-contest-archive/archive) (canonical raw captures,
private) and [`replay`](https://github.com/icpc-contest-archive/replay) (public baked
replay of archived result pages).

Corrections and additions welcome — every claim should come with a source (URL or
citation) in the contest's `sources:`/`notes:` fields.
