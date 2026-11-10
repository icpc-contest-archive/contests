#!/usr/bin/env python3
"""Poll approved Form submissions and reconcile their publication state.

GitHub YAML remains authoritative. The Sheet is a review queue and a projection
of PR/deployment state; this program never treats Sheet data as a competing
catalogue. See pilot/README.md for the operational contract.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "pilot" / "config.yaml"
FINAL_STATES = {"PUBLISHED", "REJECTED", "NO_CHANGE"}
OPEN_STATES = {"APPROVED", "PR_OPEN", "MERGED_AWAITING_DEPLOYMENT", "CONFLICT", "FAILED"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{5,63}$")


class PilotError(RuntimeError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True, capture_output=True)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text())
    if config.get("version") != 1:
        raise PilotError("unsupported pilot config version")
    if not config.get("allowed_series") or not config.get("headers"):
        raise PilotError("pilot config requires allowed_series and headers")
    return config


def column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


@dataclass
class Submission:
    row: int
    values: dict[str, str]

    def get(self, key: str) -> str:
        return self.values.get(key, "").strip()


class SheetClient:
    def __init__(self, config: dict[str, Any]) -> None:
        raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        self.spreadsheet_id = os.environ.get("PILOT_SHEET_ID", "")
        if not raw or not self.spreadsheet_id:
            raise PilotError("GOOGLE_SERVICE_ACCOUNT_JSON and PILOT_SHEET_ID are required")
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        info = json.loads(raw)
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        credentials.refresh(Request())
        self.token = credentials.token
        self.sheet_name = config["sheet_name"]
        self.headers = config["headers"]
        self.header_positions: dict[str, int] = {}

    def _request(self, method: str, url: str, body: dict[str, Any] | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            url, data=data, method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise PilotError(f"Google Sheets API {exc.code}: {detail}") from exc

    def rows(self) -> list[Submission]:
        quoted = urllib.parse.quote(f"'{self.sheet_name}'!A:ZZ", safe="!:'")
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values/{quoted}"
        values = self._request("GET", url).get("values", [])
        if not values:
            raise PilotError("pilot sheet is empty")
        names = [str(value).strip() for value in values[0]]
        missing = [name for name in self.headers.values() if name not in names]
        if missing:
            raise PilotError("pilot sheet is missing columns: " + ", ".join(missing))
        self.header_positions = {key: names.index(name) + 1 for key, name in self.headers.items()}
        result = []
        for row_number, row in enumerate(values[1:], 2):
            logical = {
                key: str(row[position - 1]) if position <= len(row) else ""
                for key, position in self.header_positions.items()
            }
            if any(logical.values()):
                result.append(Submission(row_number, logical))
        return result

    def update(self, submission: Submission, updates: dict[str, Any]) -> None:
        if not self.header_positions:
            raise PilotError("rows() must be called before update()")
        data = []
        for key, value in updates.items():
            if key not in self.header_positions:
                raise PilotError(f"unknown logical Sheet column: {key}")
            cell = f"'{self.sheet_name}'!{column_name(self.header_positions[key])}{submission.row}"
            data.append({"range": cell, "values": [[str(value)]]})
            submission.values[key] = str(value)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/values:batchUpdate"
        self._request("POST", url, {"valueInputOption": "RAW", "data": data})


class GitHubClient:
    def __init__(self) -> None:
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.repository = os.environ.get("GITHUB_REPOSITORY", "")
        if not self.token or not self.repository:
            raise PilotError("GITHUB_TOKEN and GITHUB_REPOSITORY are required")
        self.owner, self.repo = self.repository.split("/", 1)

    def api(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = "https://api.github.com" + path
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response) if response.length != 0 else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise PilotError(f"GitHub API {exc.code} {path}: {detail}") from exc

    def pull(self, number: int) -> dict[str, Any]:
        return self.api("GET", f"/repos/{self.repository}/pulls/{number}")

    def existing_pull(self, branch: str) -> dict[str, Any] | None:
        head = urllib.parse.quote(f"{self.owner}:{branch}")
        pulls = self.api("GET", f"/repos/{self.repository}/pulls?state=all&head={head}&per_page=20")
        return pulls[0] if pulls else None

    def create_pull(self, branch: str, submission: Submission) -> dict[str, Any]:
        title = f"Pilot: add source for {submission.get('contest_id')}"
        marker = f"<!-- icpc-pilot-submission:{submission.get('submission_id')} -->"
        body = (
            f"{marker}\n\nAutomated controlled-pilot submission.\n\n"
            f"- Submission: `{submission.get('submission_id')}`\n"
            f"- Contest: `{submission.get('contest_id')}`\n"
            f"- Source: {submission.get('source_url')}\n"
            f"- Reviewer: `{submission.get('reviewed_by')}`\n"
            f"- Base blob: `{submission.get('base_blob_sha')}`\n"
        )
        return self.api("POST", f"/repos/{self.repository}/pulls", {
            "title": title, "head": branch, "base": "main", "body": body,
        })

    def deployment_succeeded(self, sha: str) -> bool:
        encoded = urllib.parse.quote(sha)
        deployments = self.api(
            "GET", f"/repos/{self.repository}/deployments?sha={encoded}&environment=github-pages&per_page=20"
        )
        for deployment in deployments:
            statuses = self.api(
                "GET", f"/repos/{self.repository}/deployments/{deployment['id']}/statuses?per_page=1"
            )
            if statuses and statuses[0].get("state") == "success":
                return True
        return False


def approval_signature(submission: Submission, secret: str) -> str:
    payload = "|".join([
        submission.get("submission_id"), submission.get("base_blob_sha"),
        submission.get("reviewed_by").lower(),
        submission.get("series_id"), submission.get("contest_id"),
        submission.get("source_url"), submission.get("roles"),
        submission.get("judge"), submission.get("note"),
    ])
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def validate_submission(submission: Submission, config: dict[str, Any]) -> None:
    submission_id = submission.get("submission_id")
    if not ID_RE.fullmatch(submission_id):
        raise PilotError("submission_id must be 6-64 lowercase URL-safe characters")
    series_id = submission.get("series_id")
    contest_id = submission.get("contest_id")
    if series_id not in config["allowed_series"]:
        raise PilotError(f"series {series_id!r} is outside the pilot")
    if not contest_id.startswith(series_id + "-"):
        raise PilotError("contest_id does not belong to series_id")
    url = urllib.parse.urlparse(submission.get("source_url"))
    if url.scheme not in {"http", "https"} or not url.netloc:
        raise PilotError("source_url must be an absolute HTTP(S) URL")
    roles = [role.strip() for role in submission.get("roles").split(",") if role.strip()]
    if not roles or any(role not in config["allowed_roles"] for role in roles):
        raise PilotError("roles contains a missing or unsupported role")
    judge = submission.get("judge")
    if "judge_page" in roles:
        judges = yaml.safe_load((ROOT / "judges.yaml").read_text()).get("judges", [])
        known_judges = {item.get("id") for item in judges}
        if not judge or judge not in known_judges:
            raise PilotError("judge_page requires a judge ID from judges.yaml")
    elif judge:
        raise PilotError("judge is only valid when roles contains judge_page")
    allowed_reviewers = {
        value.strip().lower() for value in os.environ.get("PILOT_REVIEWERS", "").split(",") if value.strip()
    }
    reviewer = submission.get("reviewed_by").lower()
    if not allowed_reviewers or reviewer not in allowed_reviewers:
        raise PilotError("reviewed_by is not in PILOT_REVIEWERS")
    if config.get("require_base_blob_sha") and not re.fullmatch(r"[0-9a-f]{40}", submission.get("base_blob_sha")):
        raise PilotError("a 40-character base_blob_sha is required")
    if config.get("require_signed_approval"):
        secret = os.environ.get("PILOT_APPROVAL_HMAC_SECRET", "")
        if not secret or not hmac.compare_digest(
            approval_signature(submission, secret), submission.get("approval_token").lower()
        ):
            raise PilotError("approval signature is missing or invalid")


def yaml_blob_sha(path: Path, revision: str = "HEAD") -> str:
    relative = path.relative_to(ROOT).as_posix()
    result = run("git", "rev-parse", f"{revision}:{relative}")
    return result.stdout.strip()


def seed_base_revision(sheet: SheetClient, submission: Submission, config: dict[str, Any]) -> bool:
    if submission.get("base_blob_sha") or submission.get("review_status") not in {"", "SUBMITTED"}:
        return False
    series_id = submission.get("series_id")
    path = ROOT / "series" / f"{series_id}.yaml"
    if series_id not in config["allowed_series"] or not path.exists():
        sheet.update(submission, {"publication_status": "FAILED", "error": "Invalid pilot series", "updated_at": now()})
        return True
    sheet.update(submission, {
        "base_blob_sha": yaml_blob_sha(path), "publication_status": "PENDING_REVIEW",
        "error": "", "updated_at": now(),
    })
    return True


def patch_catalogue(submission: Submission) -> tuple[Path, bool]:
    path = ROOT / "series" / f"{submission.get('series_id')}.yaml"
    expected = submission.get("base_blob_sha")
    actual = yaml_blob_sha(path)
    if actual != expected:
        raise PilotError(f"base revision conflict: expected {expected}, found {actual}")

    roundtrip = YAML()
    roundtrip.preserve_quotes = True
    data = roundtrip.load(path.read_text())
    contest = next((item for item in data["contests"] if item.get("id") == submission.get("contest_id")), None)
    if contest is None:
        raise PilotError("contest_id is not present in the selected series")
    sources = contest.setdefault("sources", [])
    source_url = submission.get("source_url")
    roles = [role.strip() for role in submission.get("roles").split(",") if role.strip()]
    existing = next((item for item in sources if item.get("url") == source_url), None)
    if existing:
        before = json.dumps(existing, sort_keys=True)
        judge = submission.get("judge")
        if judge and existing.get("judge") not in {None, judge}:
            raise PilotError("existing source URL has a different judge")
        existing_roles = list(existing.get("roles") or [])
        existing["roles"] = existing_roles + [role for role in roles if role not in existing_roles]
        if judge and not existing.get("judge"):
            existing["judge"] = judge
        if submission.get("note") and not existing.get("note"):
            existing["note"] = submission.get("note")
        changed = before != json.dumps(existing, sort_keys=True)
    else:
        entry: dict[str, Any] = {"url": source_url, "roles": roles}
        if submission.get("judge"):
            entry["judge"] = submission.get("judge")
        if submission.get("note"):
            entry["note"] = submission.get("note")
        sources.append(entry)
        changed = True
    if changed:
        with path.open("w") as handle:
            roundtrip.dump(data, handle)
    return path, changed


def open_or_reconcile_pr(sheet: SheetClient, github: GitHubClient, submission: Submission) -> None:
    config = load_config()
    validate_submission(submission, config)
    branch = "pilot/" + re.sub(r"[^a-z0-9._-]", "-", submission.get("submission_id"))
    existing = github.existing_pull(branch)
    if existing:
        if existing.get("state") == "open":
            state = "PR_OPEN"
        elif existing.get("merged_at"):
            state = "MERGED_AWAITING_DEPLOYMENT"
        else:
            state = "REJECTED"
        sheet.update(submission, {
            "publication_status": state,
            "pr_number": existing["number"], "pr_url": existing["html_url"], "error": "", "updated_at": now(),
        })
        return

    run("git", "checkout", "--detach", "origin/main")
    path, changed = patch_catalogue(submission)
    if not changed:
        sheet.update(submission, {"publication_status": "NO_CHANGE", "error": "Source already present", "updated_at": now()})
        return
    run(sys.executable, "tools/validate.py")
    run("git", "checkout", "-B", branch)
    run("git", "add", str(path.relative_to(ROOT)))
    run("git", "-c", "user.name=icpc-pilot[bot]", "-c", "user.email=icpc-pilot[bot]@users.noreply.github.com",
        "commit", "-m", f"Pilot source submission {submission.get('submission_id')}")
    run("git", "push", "--force-with-lease", "origin", f"HEAD:refs/heads/{branch}")
    pull = github.create_pull(branch, submission)
    sheet.update(submission, {
        "publication_status": "PR_OPEN", "pr_number": pull["number"], "pr_url": pull["html_url"],
        "error": "", "updated_at": now(),
    })


def ingest(sheet: SheetClient, github: GitHubClient, config: dict[str, Any]) -> None:
    for submission in sheet.rows():
        try:
            if seed_base_revision(sheet, submission, config):
                continue
            if submission.get("review_status") != "APPROVED":
                continue
            if submission.get("publication_status") not in {"APPROVED", "FAILED", "CONFLICT", ""}:
                continue
            open_or_reconcile_pr(sheet, github, submission)
        except Exception as exc:  # one bad row must not block the queue
            state = "CONFLICT" if "revision conflict" in str(exc) else "FAILED"
            sheet.update(submission, {"publication_status": state, "error": str(exc)[:500], "updated_at": now()})


def reconcile(sheet: SheetClient, github: GitHubClient) -> None:
    for submission in sheet.rows():
        if submission.get("publication_status") in FINAL_STATES or not submission.get("pr_number"):
            continue
        try:
            pull = github.pull(int(submission.get("pr_number")))
            if pull.get("state") == "open":
                mergeable_state = pull.get("mergeable_state")
                state = "CONFLICT" if mergeable_state == "dirty" else "PR_OPEN"
                sheet.update(submission, {"publication_status": state, "error": "PR has conflicts" if state == "CONFLICT" else "", "updated_at": now()})
            elif not pull.get("merged_at"):
                sheet.update(submission, {"publication_status": "REJECTED", "error": "PR closed without merge", "updated_at": now()})
            else:
                sha = pull.get("merge_commit_sha", "")
                if sha and github.deployment_succeeded(sha):
                    sheet.update(submission, {"publication_status": "PUBLISHED", "published_sha": sha, "error": "", "updated_at": now()})
                else:
                    sheet.update(submission, {"publication_status": "MERGED_AWAITING_DEPLOYMENT", "error": "", "updated_at": now()})
        except Exception as exc:
            sheet.update(submission, {"publication_status": "FAILED", "error": str(exc)[:500], "updated_at": now()})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["ingest", "reconcile", "run", "validate-config"])
    args = parser.parse_args()
    config = load_config()
    if args.mode == "validate-config":
        print("pilot config: valid")
        return 0
    sheet = SheetClient(config)
    github = GitHubClient()
    if args.mode in {"ingest", "run"}:
        ingest(sheet, github, config)
    if args.mode in {"reconcile", "run"}:
        reconcile(sheet, github)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
