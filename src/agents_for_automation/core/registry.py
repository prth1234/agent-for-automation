"""Repository registry loader for modular multi-repo automation."""
from __future__ import annotations

from pathlib import Path

import yaml

from agents_for_automation.core.models import RepoConfig


class RepoRegistry:
    """Loads and exposes registered target repositories from YAML."""

    def __init__(self, repos: dict[str, RepoConfig]) -> None:
        self._repos = repos

    @classmethod
    def from_yaml(cls, path: Path, workspaces_root: Path | None = None) -> RepoRegistry:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        repos_raw = raw.get("repos", {})
        repos: dict[str, RepoConfig] = {}
        for name, cfg in repos_raw.items():
            repo = RepoConfig(name=name, **cfg)
            if workspaces_root is not None and not Path(repo.local_path).exists():
                repo.local_path = str(workspaces_root / name)
            repos[name] = repo
        return cls(repos)

    def get(self, name: str) -> RepoConfig | None:
        return self._repos.get(name)

    def all(self) -> list[RepoConfig]:
        return list(self._repos.values())

    def describe_for_prompt(self) -> str:
        lines: list[str] = []
        for repo in self._repos.values():
            caps = ", ".join(repo.capabilities) or "general"
            lines.append(
                f"- {repo.name} ({repo.github_repo}): {repo.description.strip()} "
                f"[capabilities: {caps}]"
            )
        return "\n".join(lines)
