"""Tests for the AFA agent marketplace registry, CLI, and modules."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from agents_for_automation.cli import main as cli_main
from agents_for_automation.config import Settings
from agents_for_automation.core.agent_registry import AgentRegistry
from agents_for_automation.runtime import run_agent
from agents_for_automation.server import app


def test_registry_discovers_marketplace_agents_and_skips_template() -> None:
    registry = AgentRegistry.discover()
    names = set(m.name for m in registry.list_agents())
    assert {
        "support_ticket",
        "weekly_digest",
        "invoice_extraction",
        "doc_generator",
        "compliance_check",
        "slack_qa",
    }.issubset(names)
    assert "my_agent" not in names


def test_cli_list_and_info(capsys: object) -> None:
    assert cli_main(["list"]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "support_ticket" in captured.out
    assert "weekly_digest" in captured.out

    assert cli_main(["info", "support_ticket"]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "Name:        support_ticket" in captured.out
    assert "jira:read" in captured.out
    assert "config/repos.yaml" in captured.out


def test_run_weekly_digest_agent(tmp_path: Path) -> None:
    sample = tmp_path / "digest.json"
    sample.write_text(
        json.dumps(
            {
                "team": "Thorium",
                "tickets": [{"key": "SQ-1", "summary": "Test", "status": "PR_OPENED"}],
                "prs": [{"title": "PR #1", "url": "https://github.com/org/repo/pull/1"}],
            }
        ),
        encoding="utf-8",
    )
    result = run_agent(
        "weekly_digest",
        inputs={"json": str(sample)},
        settings=Settings(dry_run=True),
    )
    assert result.agent_name == "weekly_digest"
    assert result.status == "COMPLETED"
    assert result.outputs["ticket_count"] == 1
    assert result.outputs["pr_count"] == 1
    assert "SQ-1" in result.outputs["digest_markdown"]


def test_server_marketplace_endpoints() -> None:
    client = TestClient(app)
    resp = client.get("/agents")
    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()]
    assert "support_ticket" in names
    assert "weekly_digest" in names

    detail = client.get("/agents/support_ticket")
    assert detail.status_code == 200
    assert detail.json()["category"] == "engineering"

    missing = client.get("/agents/does_not_exist")
    assert missing.status_code == 404
