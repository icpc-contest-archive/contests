import hashlib
import hmac
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import pilot_sync


class PilotSyncTests(unittest.TestCase):
    def submission(self, **updates):
        values = {
            "submission_id": "pilot-123456",
            "series_id": "gny",
            "contest_id": "gny-2025",
            "source_url": "https://example.org/results",
            "roles": "scoreboard, problemset",
            "review_status": "APPROVED",
            "reviewed_by": "reviewer@example.org",
            "base_blob_sha": "a" * 40,
            "approval_token": "",
        }
        values.update(updates)
        return pilot_sync.Submission(2, values)

    def test_column_name(self):
        self.assertEqual(pilot_sync.column_name(1), "A")
        self.assertEqual(pilot_sync.column_name(26), "Z")
        self.assertEqual(pilot_sync.column_name(27), "AA")
        self.assertEqual(pilot_sync.column_name(702), "ZZ")

    def test_signature_matches_apps_script_contract(self):
        submission = self.submission()
        expected = hmac.new(
            b"secret", b"pilot-123456|" + b"a" * 40 + b"|reviewer@example.org", hashlib.sha256
        ).hexdigest()
        self.assertEqual(pilot_sync.approval_signature(submission, "secret"), expected)

    def test_validate_rejects_series_outside_pilot(self):
        config = pilot_sync.load_config()
        submission = self.submission(series_id="wf", contest_id="wf-2025")
        with mock.patch.dict(os.environ, {"PILOT_REVIEWERS": "reviewer@example.org", "PILOT_APPROVAL_HMAC_SECRET": "secret"}):
            submission.values["approval_token"] = pilot_sync.approval_signature(submission, "secret")
            with self.assertRaisesRegex(pilot_sync.PilotError, "outside the pilot"):
                pilot_sync.validate_submission(submission, config)

    def test_validate_requires_signed_authorized_approval(self):
        config = pilot_sync.load_config()
        submission = self.submission()
        with mock.patch.dict(os.environ, {"PILOT_REVIEWERS": "reviewer@example.org", "PILOT_APPROVAL_HMAC_SECRET": "secret"}):
            with self.assertRaisesRegex(pilot_sync.PilotError, "signature"):
                pilot_sync.validate_submission(submission, config)
            submission.values["approval_token"] = pilot_sync.approval_signature(submission, "secret")
            pilot_sync.validate_submission(submission, config)

    def test_patch_deduplicates_source_and_merges_roles(self):
        submission = self.submission(source_url="https://example.org/results", roles="problemset")
        yaml_text = """series:\n  id: gny\ncontests:\n- id: gny-2025\n  sources:\n  - url: https://example.org/results\n    roles:\n    - scoreboard\n"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "series").mkdir()
            path = root / "series" / "gny.yaml"
            path.write_text(yaml_text)
            with mock.patch.object(pilot_sync, "ROOT", root), mock.patch.object(
                pilot_sync, "yaml_blob_sha", return_value="a" * 40
            ):
                _, changed = pilot_sync.patch_catalogue(submission)
            self.assertTrue(changed)
            rendered = path.read_text()
            self.assertEqual(rendered.count("https://example.org/results"), 1)
            self.assertIn("scoreboard", rendered)
            self.assertIn("problemset", rendered)

    def test_retry_reconciles_one_existing_pr_without_creating_a_duplicate(self):
        submission = self.submission(approval_token="signed")

        class Sheet:
            def update(self, item, updates):
                item.values.update({key: str(value) for key, value in updates.items()})

        class GitHub:
            created = 0
            pull = None

            def existing_pull(self, branch):
                self.branch = branch
                return self.pull

            def create_pull(self, branch, item):
                self.created += 1
                self.pull = {
                    "number": 17,
                    "html_url": "https://github.example/pull/17",
                    "state": "open",
                    "merged_at": None,
                }
                return self.pull

        github = GitHub()
        with mock.patch.object(pilot_sync, "validate_submission"), \
             mock.patch.object(
                 pilot_sync, "patch_catalogue",
                 return_value=(pilot_sync.ROOT / "series" / "gny.yaml", True),
             ), \
             mock.patch.object(pilot_sync, "run"):
            pilot_sync.open_or_reconcile_pr(Sheet(), github, submission)
            pilot_sync.open_or_reconcile_pr(Sheet(), github, submission)

        self.assertEqual(github.created, 1)
        self.assertEqual(github.branch, "pilot/pilot-123456")
        self.assertEqual(submission.get("pr_number"), "17")
        self.assertEqual(submission.get("publication_status"), "PR_OPEN")

    def test_ingest_marks_stale_authoritative_revision_as_conflict(self):
        submission = self.submission(publication_status="APPROVED", approval_token="signed")

        class Sheet:
            def rows(self):
                return [submission]

            def update(self, item, updates):
                item.values.update({key: str(value) for key, value in updates.items()})

        with mock.patch.object(pilot_sync, "seed_base_revision", return_value=False), \
             mock.patch.object(
                 pilot_sync, "open_or_reconcile_pr",
                 side_effect=pilot_sync.PilotError("base revision conflict: expected old, found new"),
             ):
            pilot_sync.ingest(Sheet(), object(), pilot_sync.load_config())

        self.assertEqual(submission.get("publication_status"), "CONFLICT")
        self.assertIn("revision conflict", submission.get("error"))

    def test_reconcile_requires_successful_pages_deployment_before_published(self):
        submission = self.submission(publication_status="PR_OPEN", pr_number="17")

        class Sheet:
            def rows(self):
                return [submission]

            def update(self, item, updates):
                item.values.update({key: str(value) for key, value in updates.items()})

        class GitHub:
            deployed = False

            def pull(self, number):
                self.number = number
                return {
                    "state": "closed",
                    "merged_at": "2026-11-10T00:00:00Z",
                    "merge_commit_sha": "b" * 40,
                }

            def deployment_succeeded(self, sha):
                self.sha = sha
                return self.deployed

        github = GitHub()
        sheet = Sheet()
        pilot_sync.reconcile(sheet, github)
        self.assertEqual(submission.get("publication_status"), "MERGED_AWAITING_DEPLOYMENT")
        self.assertEqual(submission.get("published_sha"), "")

        github.deployed = True
        pilot_sync.reconcile(sheet, github)
        self.assertEqual(submission.get("publication_status"), "PUBLISHED")
        self.assertEqual(submission.get("published_sha"), "b" * 40)
        self.assertEqual(github.number, 17)
        self.assertEqual(github.sha, "b" * 40)

    def test_reconcile_closed_unmerged_pr_as_rejected(self):
        submission = self.submission(publication_status="PR_OPEN", pr_number="17")

        class Sheet:
            def rows(self):
                return [submission]

            def update(self, item, updates):
                item.values.update({key: str(value) for key, value in updates.items()})

        class GitHub:
            def pull(self, number):
                return {"state": "closed", "merged_at": None}

        pilot_sync.reconcile(Sheet(), GitHub())
        self.assertEqual(submission.get("publication_status"), "REJECTED")
        self.assertEqual(submission.get("error"), "PR closed without merge")


if __name__ == "__main__":
    unittest.main()
