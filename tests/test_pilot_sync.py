import difflib
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
            "judge": "",
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
        payload = (
            b"pilot-123456|" + b"a" * 40
            + b"|reviewer@example.org|gny|gny-2025|https://example.org/results|"
              b"scoreboard, problemset||"
        )
        expected = hmac.new(
            b"secret", payload, hashlib.sha256
        ).hexdigest()
        self.assertEqual(pilot_sync.approval_signature(submission, "secret"), expected)

    def test_post_approval_payload_edit_invalidates_signature(self):
        submission = self.submission()
        signature = pilot_sync.approval_signature(submission, "secret")
        submission.values["approval_token"] = signature
        submission.values["roles"] = "web"
        with mock.patch.dict(os.environ, {
            "PILOT_REVIEWERS": "reviewer@example.org",
            "PILOT_APPROVAL_HMAC_SECRET": "secret",
        }):
            with self.assertRaisesRegex(pilot_sync.PilotError, "signature"):
                pilot_sync.validate_submission(submission, pilot_sync.load_config())

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

    def test_validate_judge_only_on_problemset_and_against_registry(self):
        config = pilot_sync.load_config()
        env = {"PILOT_REVIEWERS": "reviewer@example.org", "PILOT_APPROVAL_HMAC_SECRET": "secret"}
        with mock.patch.dict(os.environ, env):
            for roles, judge, error in [("problemset", "not-a-real-judge", "judges.yaml"),
                                        ("scoreboard", "kattis", "problemset or problem"),
                                        ("judge_page", "kattis", "unsupported role")]:
                submission = self.submission(roles=roles, judge=judge)
                submission.values["approval_token"] = pilot_sync.approval_signature(submission, "secret")
                with self.assertRaisesRegex(pilot_sync.PilotError, error):
                    pilot_sync.validate_submission(submission, config)
            submission = self.submission(roles="problemset", judge="kattis")
            submission.values["approval_token"] = pilot_sync.approval_signature(submission, "secret")
            pilot_sync.validate_submission(submission, config)

    def test_config_roles_are_catalogue_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            config = pilot_sync.yaml.safe_load(pilot_sync.CONFIG_PATH.read_text())
            config["allowed_roles"].append("icpc_standings")
            path.write_text(pilot_sync.yaml.safe_dump(config))
            with self.assertRaisesRegex(pilot_sync.PilotError, "icpc_standings"):
                pilot_sync.load_config(path)

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

    def test_patch_on_real_catalogue_changes_only_the_new_source(self):
        for series_id, contest_id in [("socal", "socal-2023"), ("gny", "gny-2023"), ("mcpc", "mcpc-2023")]:
            submission = self.submission(series_id=series_id, contest_id=contest_id,
                                         source_url="https://example.org/new", roles="problemset", note="")
            original = (pilot_sync.ROOT / "series" / f"{series_id}.yaml").read_text()
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "series").mkdir()
                path = root / "series" / f"{series_id}.yaml"
                path.write_text(original)
                with mock.patch.object(pilot_sync, "ROOT", root), mock.patch.object(
                    pilot_sync, "yaml_blob_sha", return_value="a" * 40
                ):
                    _, changed = pilot_sync.patch_catalogue(submission)
                self.assertTrue(changed)
                rendered = path.read_text()
            changes = [line for line in difflib.unified_diff(original.splitlines(), rendered.splitlines(), n=0)
                       if line[:1] in "+-" and line[:3] not in {"+++", "---"}]
            self.assertEqual(changes, ["+  - url: https://example.org/new", "+    roles:", "+    - problemset"],
                             series_id)

    def test_unapproved_row_follows_the_current_revision(self):
        submission = self.submission(review_status="SUBMITTED", base_blob_sha="c" * 40,
                                     publication_status="CONFLICT", approval_token="old")

        class Sheet:
            def update(self, item, updates):
                item.values.update({key: str(value) for key, value in updates.items()})

        config = pilot_sync.load_config()
        with mock.patch.object(pilot_sync, "yaml_blob_sha", return_value="d" * 40):
            self.assertTrue(pilot_sync.seed_base_revision(Sheet(), submission, config))
            self.assertEqual(submission.get("base_blob_sha"), "d" * 40)
            self.assertEqual(submission.get("publication_status"), "PENDING_REVIEW")
            self.assertEqual(submission.get("approval_token"), "")
            self.assertFalse(pilot_sync.seed_base_revision(Sheet(), submission, config))
        submission.values["review_status"] = "APPROVED"
        self.assertFalse(pilot_sync.seed_base_revision(Sheet(), submission, config))

    def test_validation_failure_is_reported_and_tree_is_reset(self):
        submission = self.submission(approval_token="signed")
        calls = []

        def fake_run(*args, check=True):
            calls.append(args)
            failed = "tools/validate.py" in args
            return mock.Mock(returncode=1 if failed else 0, stdout="  ERROR: gny.yaml: bad role\n" if failed else "",
                             stderr="")

        class GitHub:
            def existing_pull(self, branch):
                return None

        with mock.patch.object(pilot_sync, "validate_submission"), \
             mock.patch.object(pilot_sync, "patch_catalogue",
                               return_value=(pilot_sync.ROOT / "series" / "gny.yaml", True)), \
             mock.patch.object(pilot_sync, "run", side_effect=fake_run):
            with self.assertRaisesRegex(pilot_sync.PilotError, "ERROR: gny.yaml: bad role"):
                pilot_sync.open_or_reconcile_pr(object(), GitHub(), submission)
        self.assertEqual(calls[0], ("git", "checkout", "--force", "--detach", "origin/main"))

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
             mock.patch.object(pilot_sync, "run", return_value=mock.Mock(returncode=0, stdout="", stderr="")):
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
