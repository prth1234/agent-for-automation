"""Shared reusable integrations available to all AFA agent modules."""
from __future__ import annotations

from dataclasses import dataclass

from agents_for_automation.config import Settings
from agents_for_automation.integrations.github import GitHubConnector, build_branch_name
from agents_for_automation.integrations.jira import JiraConnector
from agents_for_automation.integrations.notifier import NotifierConnector


@dataclass
class IntegrationHub:
    """Bundle of shared connectors injected into every agent's execution context."""

    jira: JiraConnector
    github: GitHubConnector
    notifier: NotifierConnector

    @classmethod
    def from_settings(cls, settings: Settings) -> IntegrationHub:
        """Build default connectors from runtime Settings."""
        return cls(
            jira=JiraConnector(settings),
            github=GitHubConnector(settings),
            notifier=NotifierConnector(settings),
        )


__all__ = [
    "GitHubConnector",
    "IntegrationHub",
    "JiraConnector",
    "NotifierConnector",
    "build_branch_name",
]
