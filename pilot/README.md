# Controlled Form → Sheet → GitHub pilot

This pilot keeps `series/*.yaml` authoritative while using a Google Form and its
response Sheet as a review queue. GitHub Actions polls every ten minutes; Apps
Script does **not** hold a GitHub credential or dispatch workflows.

Pilot scope: Greater New York (`gny`), Mid-Central (`mcpc`), and Southern
California (`socal`). A submission adds or extends one `sources:` entry on one
existing contest. It cannot create contests or edit unrelated catalogue data.

## State flow

`SUBMITTED/PENDING_REVIEW` → `APPROVED` → `PR_OPEN` →
`MERGED_AWAITING_DEPLOYMENT` → `PUBLISHED`

Terminal states are `PUBLISHED`, `REJECTED`, and `NO_CHANGE`. Validation or
integration errors use `FAILED`; an authoritative YAML revision mismatch or a
dirty PR uses `CONFLICT`.

## Sheet contract

Create the columns named in `pilot/config.yaml`. The Form should collect the
human-entered fields `series_id`, `contest_id`, `source_url`, `roles`, and
`note`; include `judge` when `roles` contains `judge_page`. The remaining
columns are controlled by Apps Script or GitHub Actions.

The polling workflow first writes `base_blob_sha` for a submitted row. An
authorized reviewer then changes `review_status` to `APPROVED`. The installed
Apps Script trigger verifies the reviewer's Google identity and signs the
submission ID, base revision, reviewer, and every proposed YAML field. GitHub
rejects an editable status cell without that signature, and rejects any payload
field changed after approval.

## One-time configuration

1. Bind `pilot/apps-script/Code.gs` to the response Sheet.
2. Set Apps Script properties `PILOT_REVIEWERS` and
   `PILOT_APPROVAL_HMAC_SECRET`; optionally set `PILOT_SHEET_NAME`.
3. Run `installPilotTriggers()` once and approve the Google permission prompt.
4. Share only the response Sheet (not broader Drive content) with a Google
   service account as editor.
5. Add repository secrets:
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `PILOT_SHEET_ID`
   - `PILOT_REVIEWERS`
   - `PILOT_APPROVAL_HMAC_SECRET`
   - `PILOT_GITHUB_APP_ID`
   - `PILOT_GITHUB_APP_PRIVATE_KEY`
6. Install that GitHub App only on this repository with Contents and Pull
   requests write plus Deployments read. The workflow mints a short-lived token;
   it does not use a long-lived PAT. A separate App token is required because
   pull requests created by the built-in `GITHUB_TOKEN` do not trigger normal
   pull-request CI.
7. Ensure Pages uses the
   existing `CI` workflow.

The HMAC secret must be the same in Apps Script and GitHub. Rotate it after any
suspected disclosure; previously approved but unprocessed rows must then be
approved again.

## Idempotency and recovery

The stable submission ID determines branch `pilot/<submission_id>`. Before
creating a PR, the worker searches all PR states for that branch and reconciles
the existing PR instead of opening another. A retry can therefore create at
most one PR. Existing source URLs are merged by role and never duplicated.

The worker compares the approved `base_blob_sha` with the current authoritative
series file. A mismatch becomes `CONFLICT`; the reviewer must inspect the new
YAML, return the row to `SUBMITTED`, let polling seed the new revision, and
approve again.

`PUBLISHED` is written only after the PR is merged and GitHub reports a
successful deployment of the merged SHA to the `github-pages` environment.

## Acceptance test

1. Submit one new source URL for an existing contest in one pilot series.
2. Wait for `base_blob_sha` and `PENDING_REVIEW`.
3. Approve as an allowlisted reviewer; verify a single PR reaches `PR_OPEN`.
4. Confirm validation passes, review and merge normally.
5. Confirm Pages deployment succeeds and the Sheet becomes `PUBLISHED` with
   `published_sha` and the PR URL.
6. Re-run the workflow twice; confirm no duplicate PR or source entry appears.
7. Repeat with an obsolete base SHA, unauthorized reviewer, rejected PR, and an
   interrupted run; confirm `CONFLICT`, failed approval, `REJECTED`, and safe
   reconciliation respectively.

Engineering owns the workflow and secrets; archive reviewers own approvals and
merge decisions; the repository's incident owner disables `pilot-sync.yml` and
rotates both credentials if unexpected writes occur.
