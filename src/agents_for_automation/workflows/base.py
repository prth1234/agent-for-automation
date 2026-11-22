"""Base protocol for all automation workflows."""
from __future__ import annotations

from typing import Any, Protocol

from agents_for_automation.core.models import WorkflowResult


class AutomationWorkflow(Protocol):
    """Contract that every automation workflow module implements."""

    name: str

    def run(self, payload: Any) -> WorkflowResult:
        """Execute the workflow for a normalized trigger payload."""
        ...
