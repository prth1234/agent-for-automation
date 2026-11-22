"""Starter template for a new AFA marketplace agent module."""
from __future__ import annotations

import time
from typing import Any

from agents_for_automation.core.base import AgentContext, AgentRunResult
from agents_for_automation.core.manifest import AgentManifest


class TemplateAgent:
    """Replace this docstring with what your agent automates."""

    def __init__(self, manifest: AgentManifest) -> None:
        self.manifest = manifest

    def run(self, inputs: dict[str, Any], ctx: AgentContext) -> AgentRunResult:
        started = time.perf_counter()
        query = str(inputs.get("query", "")).strip()
        if not query:
            return AgentRunResult(
                agent_name=self.manifest.name,
                status="NEEDS_INFO",
                message="Missing required input: 'query'.",
                dry_run=ctx.dry_run,
            )

        # Use shared integrations via ctx.integrations (jira, github, notifier)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return AgentRunResult(
            agent_name=self.manifest.name,
            status="COMPLETED",
            message=f"Processed query '{query}' (dry_run={ctx.dry_run}).",
            dry_run=ctx.dry_run,
            time_saved_minutes=self.manifest.estimated_time_saved_minutes,
            duration_ms=elapsed_ms,
            outputs={"query": query},
        )


def create_agent(manifest: AgentManifest) -> TemplateAgent:
    """Factory function referenced by `entrypoint: agent:create_agent` in agent.yaml."""
    return TemplateAgent(manifest=manifest)
