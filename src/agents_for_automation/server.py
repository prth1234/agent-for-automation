"""FastAPI webhook server for Jira and future automation triggers."""
from __future__ import annotations

import hmac
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from agents_for_automation.config import Settings
from agents_for_automation.core.connectors.jira import JiraConnector
from agents_for_automation.runtime import build_support_ticket_workflow

app = FastAPI(title="Agents for Automation", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/jira")
async def jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature: str | None = Header(default=None),
) -> dict[str, str]:
    """Receive Jira Automation webhook events and run SupportTicketWorkflow in the background."""
    settings = Settings()

    if settings.jira_webhook_secret and (
        not x_hub_signature or not hmac.compare_digest(x_hub_signature, settings.jira_webhook_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload: dict[str, Any] = await request.json()
    ticket = JiraConnector.parse_issue_payload(payload)
    workflow = build_support_ticket_workflow(settings)
    background_tasks.add_task(workflow.run, ticket)
    return {"status": "accepted", "ticket_key": ticket.ticket_key}
