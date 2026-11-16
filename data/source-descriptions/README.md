# Source descriptions

One file per contest, `<series>/<contest>.yaml`: what a reader of **our copy** of a source wrote
about it. Written by `tools/describe_apply.py`; shown on the source's page under *What it
contains* (`tools/source_descriptions.py`).

```yaml
contest: nordic-2020
sources:
- url: https://ncpc20.kattis.com/contests/ncpc20/standings   # the source, as in the series file
  read: '2026-11-16'        # the day the copy was read
  rubric: 1                 # version of tools/describe_rubric.md
  copy: nordic/nordic-2020/scoreboard/2026-09-01-live-f063d594/page.html   # the copy that was read (archive repo)
  title: …                  # the document's own title, as printed
  title_en: …               # its English translation, when the title is not English
  language: [en]            # ISO 639-1, main language first
  contest_date: '2020-11-07'  # the contest day as the document prints it (not our date for the contest)
  teams: 221                # results documents: teams listed
  problems: 13              # problems the document shows
  times: true               # scoreboards: solve times per problem
  tries: true               # scoreboards: attempts per problem
  pages: 12                 # PDFs
  description: |-           # one to three paragraphs of plain text
    …
```

Rules:

- A description says what the **copy** shows. It is written from the copy and nothing else, by an
  automated reader (a language model), then checked claim by claim against the copy by a second
  one; a sample is checked a third time by an independent checker. It can still be wrong.
- Only sources whose copy we hold, and that the reader took for the document it is filed as,
  have an entry. No copy, an error page, another contest's document: no entry.
- The document facts are the document's, not the catalogue's: `contest_date` here can differ
  from the contest's `date`, and that difference is a lead, listed in
  `data/describe/<run>/contest-facts.json`, never applied on its own.
- An entry belongs to the copy named in `copy`. When a source gets a new copy, read it again.
- To correct a description by hand, edit it here; a later run replaces an entry only when its
  source is read again.

The round: `tools/describe_pack.py` (packs) → reader agents (`tools/describe_agent.md`,
`tools/describe_rubric.md`) → revision agents (`tools/describe_revise_agent.md`) →
`tools/describe_apply.py` (checks, writes these files, lists what needs a ruling in
`data/describe/<run>/` and `reports/source-descriptions-<run>.md`).
