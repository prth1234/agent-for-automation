"""Git & GitHub PR connector with dry-run support."""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

import httpx

from agents_for_automation.config import Settings

logger = logging.getLogger(__name__)


def build_branch_name(ticket_key: str, summary: str) -> str:
    """Create a clean git branch name containing the Jira ticket key."""
    slug = re.sub(r"[^a-z0-9]+", "-", summary.lower()).strip("-")[:48]
    return f"{ticket_key}-{slug}" if slug else ticket_key


class GitHubConnector:
    """Creates branches, commits changes, pushes, and opens GitHub Pull Requests."""

    def __init__(self, settings: Settings) -> None:
        self._token = settings.github_token
        self._dry_run = settings.dry_run

    def ensure_repo_ready(
        self,
        repo_path: Path,
        github_repo: str,
        base_branch: str,
    ) -> Path:
        """Clone the repo if missing (for CI/container runs) or fast-forward in live mode."""
        if not repo_path.exists():
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            clone_url = (
                f"https://x-access-token:{self._token}@github.com/{github_repo}.git"
                if self._token
                else f"https://github.com/{github_repo}.git"
            )
            subprocess.run(
                ["git", "clone", "--branch", base_branch, "--single-branch", clone_url, str(repo_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return repo_path

        if not self._dry_run:
            self._run_git(repo_path, ["fetch", "origin", base_branch])
            self._run_git(repo_path, ["checkout", base_branch])
            self._run_git(repo_path, ["pull", "--ff-only", "origin", base_branch])
        return repo_path

    def create_pr_from_working_tree(
        self,
        repo_path: Path,
        github_repo: str,
        base_branch: str,
        ticket_key: str,
        pr_title: str,
        pr_body: str,
        branch_name: str,
        files_to_stage: list[str],
    ) -> str:
        """Stage files, commit on a new branch, push, and open a GitHub PR."""
        if self._dry_run:
            logger.info(
                "[DRY-RUN] Would create branch=%s, commit %s, and open PR '%s' on %s",
                branch_name,
                files_to_stage,
                pr_title,
                github_repo,
            )
            return f"https://github.com/{github_repo}/pull/DRY-RUN-{ticket_key}"

        self._run_git(repo_path, ["checkout", "-b", branch_name])
        self._run_git(repo_path, ["add", *files_to_stage])
        self._run_git(repo_path, ["commit", "-m", pr_title])
        self._run_git(repo_path, ["push", "-u", "origin", branch_name])

        if not self._token:
            raise RuntimeError("GITHUB_TOKEN is required to open a live Pull Request")

        url = f"https://api.github.com/repos/{github_repo}/pulls"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
        }
        payload = {
            "title": pr_title,
            "body": pr_body,
            "head": branch_name,
            "base": base_branch,
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["html_url"]

    @staticmethod
    def _run_git(cwd: Path, args: list[str]) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip()
