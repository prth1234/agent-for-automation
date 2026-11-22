"""Dependency wiring for workflows and server."""
from __future__ import annotations

from agents_for_automation.config import Settings
from agents_for_automation.core.connectors.github import GitHubConnector
from agents_for_automation.core.connectors.jira import JiraConnector
from agents_for_automation.core.connectors.notifier import NotifierConnector
from agents_for_automation.core.llm import create_chat_model
from agents_for_automation.core.registry import RepoRegistry
from agents_for_automation.core.state import TicketStateStore
from agents_for_automation.workflows.support_ticket.classifier import TicketClassifier
from agents_for_automation.workflows.support_ticket.workflow import SupportTicketWorkflow


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
