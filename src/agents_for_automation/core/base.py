"""Base contracts and execution context for marketplace agent modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field

from agents_for_automation.config import Settings
from agents_for_automation.core.manifest import AgentManifest
from agents_for_automation.integrations import IntegrationHub


class AgentRunResult(BaseModel):
    """Standard outcome returned by any marketplace agent module."""

    agent_name: str
    status: str
    message: str
    dry_run: bool = True
    time_saved_minutes: int = 0
    duration_ms: int = 0
    outputs: dict[str, Any] = Field(default_factory=dict)


@dataclass
class AgentContext:
    """Runtime context passed to every agent module execution."""

    settings: Settings
    integrations: IntegrationHub

    @property
    def dry_run(self) -> bool:
        return self.settings.dry_run

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> AgentContext:
        cfg = settings or Settings()
        return cls(settings=cfg, integrations=IntegrationHub.from_settings(cfg))


class AgentModule(Protocol):
    """Contract that every self-contained agent module implements."""

    manifest: AgentManifest

    def run(self, inputs: dict[str, Any], ctx: AgentContext) -> AgentRunResult:
        """Execute the agent module with normalized inputs and shared integrations."""
        ...
