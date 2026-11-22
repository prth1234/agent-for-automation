"""Dependency wiring and marketplace runtime helpers."""
from __future__ import annotations

from typing import Any

from agents_for_automation.agents.support_ticket.classifier import TicketClassifier
from agents_for_automation.agents.support_ticket.workflow import SupportTicketWorkflow
from agents_for_automation.config import Settings
from agents_for_automation.core.agent_registry import AgentRegistry
from agents_for_automation.core.base import AgentContext, AgentRunResult
from agents_for_automation.core.llm import create_chat_model
from agents_for_automation.core.registry import RepoRegistry
from agents_for_automation.core.state import TicketStateStore
from agents_for_automation.integrations import GitHubConnector, JiraConnector, NotifierConnector


def run_agent(
    agent_name: str,
    inputs: dict[str, Any] | None = None,
    settings: Settings | None = None,
    registry: AgentRegistry | None = None,
) -> AgentRunResult:
    """Discover, load, and execute a marketplace agent module by name."""
    cfg = settings or Settings()
    reg = registry or AgentRegistry.discover()
    agent = reg.load_agent(agent_name)
    ctx = AgentContext.from_settings(cfg)
    return agent.run(inputs or {}, ctx)


def build_support_ticket_workflow(settings: Settings | None = None) -> SupportTicketWorkflow:
    """Construct a fully wired SupportTicketWorkflow instance."""
    cfg = settings or Settings()
    registry = RepoRegistry.from_yaml(cfg.repos_config_path, workspaces_root=cfg.workspaces_root)
    llm = create_chat_model(cfg)
    return SupportTicketWorkflow(
        settings=cfg,
        registry=registry,
        classifier=TicketClassifier(llm=llm, registry=registry),
        jira=JiraConnector(cfg),
        github=GitHubConnector(cfg),
        notifier=NotifierConnector(cfg),
        state_store=TicketStateStore(cfg.state_file_path),
        llm=llm,
    )
