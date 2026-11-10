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


if __name__ == "__main__":
    unittest.main()
