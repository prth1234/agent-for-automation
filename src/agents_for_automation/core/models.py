"""Shared domain models across workflows and connectors."""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TicketStatus(StrEnum):
    RECEIVED = "RECEIVED"
    NEEDS_INFO = "NEEDS_INFO"
    IN_PROGRESS = "IN_PROGRESS"
    PR_OPENED = "PR_OPENED"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


class TicketIntent(StrEnum):
    GENIE_ONBOARDING = "genie_onboarding"
    BUG_INVESTIGATION = "bug_investigation"
    UNKNOWN = "unknown"


class TicketContext(BaseModel):
    """Normalized Jira support ticket payload."""

    ticket_key: str
    summary: str
    description: str = ""
    assignee: str | None = None
    reporter: str | None = None
    team: str | None = None
    org_id: str | None = None
    comments: list[str] = Field(default_factory=list)
    raw_fields: dict[str, Any] = Field(default_factory=dict)


class TicketClassification(BaseModel):
    """Structured routing & parameter extraction output from the LLM."""

    target_repo: str | None = None
    intent: TicketIntent = TicketIntent.UNKNOWN
    org_id: str | None = None
    region_or_env: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None
    reasoning: str = ""


class RepoConfig(BaseModel):
    """Configuration for a target repository registered in config/repos.yaml."""

    name: str
    github_repo: str
    local_path: str
    base_branch: str = "main"
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    genie_onboarding: dict[str, Any] = Field(default_factory=dict)
    test_command: str | None = None


class WorkflowResult(BaseModel):
    """Standard outcome returned by any automation workflow."""

    ticket_key: str
    status: TicketStatus
    message: str
    target_repo: str | None = None
    branch_name: str | None = None
    pr_url: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
