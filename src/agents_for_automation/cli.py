"""CLI entrypoint for running automation workflows locally or starting the webhook server."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import uvicorn

from agents_for_automation.config import Settings
from agents_for_automation.core.connectors.jira import JiraConnector
from agents_for_automation.core.models import TicketContext
from agents_for_automation.runtime import build_support_ticket_workflow


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="afa", description="Agents for Automation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ticket = sub.add_parser("run-ticket", help="Fetch a Jira ticket by key and process it")
    p_ticket.add_argument("ticket_key", help="Jira issue key, e.g. SQ-32775")
    p_ticket.add_argument("--live", action="store_true", help="Disable dry-run mode")

    p_json = sub.add_parser("run-json", help="Process a ticket from a local JSON file")
    p_json.add_argument("json_path", type=Path, help="Path to TicketContext JSON")
    p_json.add_argument("--live", action="store_true", help="Disable dry-run mode")

    p_serve = sub.add_parser("serve", help="Start the FastAPI webhook server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8080)

    args = parser.parse_args()

    if args.command == "serve":
        uvicorn.run("agents_for_automation.server:app", host=args.host, port=args.port, reload=False)
        return

    settings = Settings(dry_run=not args.live)
    workflow = build_support_ticket_workflow(settings)

    if args.command == "run-ticket":
        ticket = JiraConnector(settings).fetch_issue(args.ticket_key)
    else:
        raw = json.loads(args.json_path.read_text(encoding="utf-8"))
        ticket = TicketContext.model_validate(raw)

    result = workflow.run(ticket)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
