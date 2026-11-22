"""Unit tests for the slack_qa agent module."""
from __future__ import annotations

import json
from pathlib import Path

from agents_for_automation.config import Settings
from agents_for_automation.core.agent_registry import AgentRegistry
from agents_for_automation.runtime import run_agent


def test_slack_qa_grounded_answer_with_sources(tmp_path: Path) -> None:
    payload_file = tmp_path / "qa_input.json"
    payload_file.write_text(
        json.dumps(
            {
                "question": "How do I roll back a production release?",
                "sops": [
                    {
                        "title": "Deployment Runbook",
                        "source": "sops/deployment.md",
                        "content": "To roll back a production release, run `argocd app rollback prod-api` and notify #deployments.",
                    },
                    {
                        "title": "Vacation Policy",
                        "source": "sops/hr_pto.md",
                        "content": "Submit PTO requests in Workday at least two weeks in advance.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run_agent(
        "slack_qa",
        inputs={"json": str(payload_file)},
        settings=Settings(dry_run=True),
    )

    assert result.agent_name == "slack_qa"
    assert result.status == "COMPLETED"
    assert result.outputs["question"] == "How do I roll back a production release?"
    assert result.outputs["sources"] == ["sops/deployment.md"]
    assert result.outputs["confidence"] > 0.0
    assert "argocd app rollback prod-api" in result.outputs["answer"]
    assert "sops/deployment.md" in result.outputs["answer"]


def test_slack_qa_sop_dir_loading(tmp_path: Path) -> None:
    sop_dir = tmp_path / "sops"
    sop_dir.mkdir()
    (sop_dir / "vpn_access.md").write_text(
        "Request VPN access via Jira SEC ticket with manager approval.",
        encoding="utf-8",
    )

    result = run_agent(
        "slack_qa",
        inputs={"question": "How do I request VPN access?", "sop_dir": str(sop_dir)},
        settings=Settings(dry_run=True),
    )

    assert result.status == "COMPLETED"
    assert result.outputs["sources"] == ["vpn_access.md"]
    assert result.outputs["confidence"] > 0.0
    assert "Jira SEC" in result.outputs["answer"]


def test_slack_qa_unknown_question_escalates() -> None:
    result = run_agent(
        "slack_qa",
        inputs={"question": "What is the Wi-Fi password for the Mars orbital station?"},
        settings=Settings(dry_run=True),
    )

    assert result.status == "COMPLETED"
    assert result.outputs["sources"] == []
    assert result.outputs["confidence"] == 0.0
    assert "escalate" in result.outputs["answer"].lower()


def test_slack_qa_missing_question_returns_needs_info() -> None:
    result = run_agent(
        "slack_qa",
        inputs={},
        settings=Settings(dry_run=True),
    )

    assert result.agent_name == "slack_qa"
    assert result.status == "NEEDS_INFO"
    assert "question" in result.message.lower()


def test_slack_qa_discovered_by_registry() -> None:
    registry = AgentRegistry.discover()
    names = [m.name for m in registry.list_agents()]
    assert "slack_qa" in names
