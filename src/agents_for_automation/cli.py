"""CLI entrypoint for browsing and running AFA marketplace agent modules."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import uvicorn

from agents_for_automation.config import Settings
from agents_for_automation.core.agent_registry import AgentRegistry
from agents_for_automation.core.models import TicketContext
from agents_for_automation.integrations.jira import JiraConnector
from agents_for_automation.runtime import build_support_ticket_workflow, run_agent


def _parse_kv_inputs(pairs: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Invalid --input '{item}'; expected key=value")
        key, value = item.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _cmd_list(registry: AgentRegistry) -> int:
    agents = registry.list_agents()
    if not agents:
        print("No agents found.")
        return 0

    name_w = max(len(a.name) for a in agents)
    cat_w = max(len(a.category) for a in agents)
    status_w = max(len(a.status) for a in agents)
    for agent in agents:
        print(
            f"{agent.name:<{name_w}}  v{agent.version}  "
            f"[{agent.category:<{cat_w}} | {agent.status:<{status_w}}]  {agent.description}"
        )
    return 0


def _cmd_info(registry: AgentRegistry, name: str) -> int:
    entry = registry.get(name)
    if entry is None:
        print(f"Error: Agent '{name}' not found.", file=sys.stderr)
        return 1

    m = entry.manifest
    print(f"Name:        {m.name} (v{m.version})")
    print(f"Category:    {m.category} | Status: {m.status}")
    print(f"Description: {m.description}")
    print(f"Triggers:    {', '.join(m.triggers) or '(none)'}")
    print(f"Permissions: {', '.join(m.permissions) or '(none)'}")
    print(f"Config:      {', '.join(m.config_files) or '(none)'}")
    print(f"Est. Saved:  {m.estimated_time_saved_minutes} min/run")
    print("Inputs:")
    if not m.inputs:
        print("  (none)")
    for inp in m.inputs:
        req = "required" if inp.required else "optional"
        print(f"  - {inp.name} ({inp.type}, {req}): {inp.description}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="afa", description="Agents for Automation Marketplace CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all available agent modules")

    p_info = sub.add_parser("info", help="Show manifest, inputs, and permissions for an agent")
    p_info.add_argument("agent_name", help="Agent module name, e.g. support_ticket")

    p_run = sub.add_parser("run", help="Run a marketplace agent module")
    p_run.add_argument("agent_name", help="Agent module name, e.g. support_ticket")
    p_run.add_argument("--ticket", help="Jira ticket key (e.g. SQ-32775)")
    p_run.add_argument("--json", dest="json_path", type=Path, help="Path to JSON input payload")
    p_run.add_argument(
        "--input",
        action="append",
        default=[],
        help="Additional key=value input (repeatable)",
    )
    p_run.add_argument("--live", action="store_true", help="Disable dry-run mode")

    p_ticket = sub.add_parser("run-ticket", help="Shortcut: run support_ticket for a Jira key")
    p_ticket.add_argument("ticket_key", help="Jira issue key, e.g. SQ-32775")
    p_ticket.add_argument("--live", action="store_true", help="Disable dry-run mode")

    p_json = sub.add_parser("run-json", help="Shortcut: run support_ticket from a JSON file")
    p_json.add_argument("json_path", type=Path, help="Path to TicketContext JSON")
    p_json.add_argument("--live", action="store_true", help="Disable dry-run mode")

    p_serve = sub.add_parser("serve", help="Start the FastAPI marketplace & webhook server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8080)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    registry = AgentRegistry.discover()

    if args.command == "list":
        return _cmd_list(registry)

    if args.command == "info":
        return _cmd_info(registry, args.agent_name)

    if args.command == "serve":
        uvicorn.run("agents_for_automation.server:app", host=args.host, port=args.port, reload=False)
        return 0

    if args.command == "run":
        settings = Settings(dry_run=not args.live)
        inputs = _parse_kv_inputs(args.input)
        if args.ticket:
            inputs["ticket"] = args.ticket
        if args.json_path:
            inputs["json"] = str(args.json_path)
        result = run_agent(args.agent_name, inputs=inputs, settings=settings, registry=registry)
        print(result.model_dump_json(indent=2))
        return 0

    settings = Settings(dry_run=not args.live)
    workflow = build_support_ticket_workflow(settings)
    if args.command == "run-ticket":
        ticket = JiraConnector(settings).fetch_issue(args.ticket_key)
    else:
        raw = json.loads(args.json_path.read_text(encoding="utf-8"))
        ticket = TicketContext.model_validate(raw)

    wf_result = workflow.run(ticket)
    print(wf_result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
