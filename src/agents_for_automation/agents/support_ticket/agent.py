"""Marketplace entrypoint for the Support Ticket Agent."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agents_for_automation.agents.support_ticket.classifier import TicketClassifier
from agents_for_automation.agents.support_ticket.workflow import SupportTicketWorkflow
from agents_for_automation.core.base import AgentContext, AgentRunResult
from agents_for_automation.core.llm import create_chat_model
from agents_for_automation.core.manifest import AgentManifest
from agents_for_automation.core.models import TicketContext
from agents_for_automation.core.registry import RepoRegistry
from agents_for_automation.core.state import TicketStateStore


class SupportTicketAgent:
    """Self-contained marketplace agent for Jira support ticket triage & PR automation."""

    def __init__(self, manifest: AgentManifest) -> None:
        self.manifest = manifest

    def run(self, inputs: dict[str, Any], ctx: AgentContext) -> AgentRunResult:
        started = time.perf_counter()
        ticket = self._resolve_ticket(inputs, ctx)

        registry = RepoRegistry.from_yaml(
            ctx.settings.repos_config_path,
            workspaces_root=ctx.settings.workspaces_root,
        )
        llm = create_chat_model(ctx.settings)
        workflow = SupportTicketWorkflow(
            settings=ctx.settings,
            registry=registry,
            classifier=TicketClassifier(llm=llm, registry=registry),
            jira=ctx.integrations.jira,
            github=ctx.integrations.github,
            notifier=ctx.integrations.notifier,
            state_store=TicketStateStore(ctx.settings.state_file_path),
            llm=llm,
        )
        result = workflow.run(ticket)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return AgentRunResult(
            agent_name=self.manifest.name,
            status=str(result.status),
            message=result.message,
            dry_run=ctx.dry_run,
            time_saved_minutes=self.manifest.estimated_time_saved_minutes,
            duration_ms=elapsed_ms,
            outputs=result.model_dump(),
        )

    @staticmethod
    def _resolve_ticket(inputs: dict[str, Any], ctx: AgentContext) -> TicketContext:
        if "ticket_context" in inputs:
            raw_ctx = inputs["ticket_context"]
            return (
                raw_ctx
                if isinstance(raw_ctx, TicketContext)
                else TicketContext.model_validate(raw_ctx)
            )
        if inputs.get("ticket"):
            return ctx.integrations.jira.fetch_issue(str(inputs["ticket"]))
        if inputs.get("json"):
            json_val = inputs["json"]
            if isinstance(json_val, dict):
                return TicketContext.model_validate(json_val)
            raw = json.loads(Path(str(json_val)).read_text(encoding="utf-8"))
            return TicketContext.model_validate(raw)
        if "ticket_key" in inputs:
            return TicketContext.model_validate(inputs)
        raise ValueError("support_ticket requires 'ticket' (Jira key) or 'json' (payload/path).")


def create_agent(manifest: AgentManifest) -> SupportTicketAgent:
    """Factory function referenced by agent.yaml."""
    return SupportTicketAgent(manifest=manifest)
