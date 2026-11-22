"""Tests for the compliance_check marketplace agent module."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from agents_for_automation.config import Settings
from agents_for_automation.core.agent_registry import AgentRegistry
from agents_for_automation.core.base import AgentContext
from agents_for_automation.runtime import run_agent


def _build_agent_and_ctx() -> tuple[object, AgentContext, MagicMock]:
    registry = AgentRegistry.discover()
    manifest = registry.get("compliance_check")
    assert manifest is not None
    agent = registry.load_module("compliance_check")
    ctx = AgentContext.from_settings(Settings(dry_run=True))
    notifier = MagicMock()
    ctx.integrations.notifier = notifier  # type: ignore[assignment]
    return agent, ctx, notifier


def test_compliance_check_passes_builtin_ruleset(tmp_path: Path) -> None:
    sample = tmp_path / "compliance_pass.json"
    sample.write_text(
        json.dumps(
            {
                "ruleset": "vendor_onboarding",
                "documents": [
                    {
                        "type": "w9",
                        "entity_name": "Acme Corp",
                        "entity_id": "ENT-1001",
                        "expires_on": "2099-12-31",
                    },
                    {
                        "type": "soc2_report",
                        "entity_name": "Acme Corp",
                        "entity_id": "ENT-1001",
                        "expires_on": "2099-12-31",
                    },
                    {
                        "type": "insurance_certificate",
                        "entity_name": "Acme Corp",
                        "entity_id": "ENT-1001",
                        "expires_on": "2099-12-31",
                    },
                    {
                        "type": "msa",
                        "entity_name": "Acme Corp",
                        "entity_id": "ENT-1001",
                        "expires_on": "2099-12-31",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    result = run_agent(
        "compliance_check",
        inputs={"json": str(sample)},
        settings=Settings(dry_run=True),
    )
    assert result.agent_name == "compliance_check"
    assert result.status == "COMPLETED"
    assert result.outputs["passed"] is True
    assert result.outputs["missing_documents"] == []
    assert result.outputs["inconsistencies"] == []
    assert result.outputs["expired_documents"] == []


def test_compliance_check_flags_missing_inconsistent_and_expired() -> None:
    agent, ctx, notifier = _build_agent_and_ctx()
    result = agent.run(  # type: ignore[attr-defined]
        {
            "ruleset": "release_readiness",
            "documents": [
                {
                    "type": "security_signoff",
                    "entity_name": "Service Alpha",
                    "entity_id": "SVC-1",
                    "expires_on": "2020-01-01",
                },
                {
                    "type": "qa_signoff",
                    "entity_name": "Service Beta",
                    "entity_id": "SVC-2",
                    "expires_on": "2099-12-31",
                },
            ],
        },
        ctx,
    )
    assert result.status == "ISSUES_FOUND"
    assert result.outputs["passed"] is False
    assert result.outputs["missing_documents"] == ["rollback_plan", "changelog"]
    assert len(result.outputs["inconsistencies"]) == 2
    assert result.outputs["expired_documents"] == [
        {"type": "security_signoff", "expires_on": "2020-01-01"}
    ]
    notifier.notify.assert_called_once()


def test_compliance_check_supports_custom_required_documents() -> None:
    agent, ctx, notifier = _build_agent_and_ctx()
    result = agent.run(  # type: ignore[attr-defined]
        {
            "required_documents": ["dpa", "privacy_review"],
            "documents": [
                {
                    "type": "dpa",
                    "entity_name": "Acme Corp",
                    "entity_id": "ENT-1001",
                }
            ],
        },
        ctx,
    )
    assert result.status == "ISSUES_FOUND"
    assert result.outputs["passed"] is False
    assert result.outputs["missing_documents"] == ["privacy_review"]
    notifier.notify.assert_called_once()
