"""FastAPI marketplace & webhook server for AFA agent modules."""
from __future__ import annotations

import hmac
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from agents_for_automation.config import Settings
from agents_for_automation.core.agent_registry import AgentRegistry
from agents_for_automation.integrations.jira import JiraConnector
from agents_for_automation.runtime import run_agent

app = FastAPI(title="Agents for Automation", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/agents")
def list_agents() -> list[dict[str, Any]]:
    """List all discovered agent modules in the marketplace."""
    registry = AgentRegistry.discover()
    return [m.model_dump() for m in registry.list_agents()]


@app.get("/agents/{agent_name}")
def get_agent(agent_name: str) -> dict[str, Any]:
    """Return manifest details for a specific agent module."""
    registry = AgentRegistry.discover()
    entry = registry.get(agent_name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return entry.manifest.model_dump()


@app.post("/agents/{agent_name}/run")
async def trigger_agent(
    agent_name: str,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Trigger any registered marketplace agent module in the background."""
    registry = AgentRegistry.discover()
    if registry.get(agent_name) is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    payload: dict[str, Any] = await request.json()
    settings = Settings()
    background_tasks.add_task(run_agent, agent_name, payload, settings, registry)
    return {"status": "accepted", "agent_name": agent_name}


@app.post("/webhooks/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature: str | None = Header(default=None),
) -> dict[str, str]:
    """Receive Jira Automation webhook events and dispatch to the support_ticket agent."""
    settings = Settings()

    if settings.jira_webhook_secret and (
        not x_hub_signature or not hmac.compare_digest(x_hub_signature, settings.jira_webhook_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload: dict[str, Any] = await request.json()
    ticket = JiraConnector.parse_issue_payload(payload)
    background_tasks.add_task(
        run_agent,
        "support_ticket",
        {"ticket_context": ticket},
        settings,
    )
    return {"status": "accepted", "agent": "support_ticket", "ticket_key": ticket.ticket_key}
