"""Tests for the doc_generator marketplace agent module."""
from __future__ import annotations

import json
from pathlib import Path

from agents_for_automation.config import Settings
from agents_for_automation.core.agent_registry import AgentRegistry
from agents_for_automation.runtime import run_agent


def test_registry_discovers_doc_generator() -> None:
    registry = AgentRegistry.discover()
    names = [m.name for m in registry.list_agents()]
    assert "doc_generator" in names


def test_doc_generator_renders_builtin_template(tmp_path: Path) -> None:
    payload_path = tmp_path / "board_res.json"
    payload_path.write_text(
        json.dumps(
            {
                "template": "board_resolution",
                "company_name": "Acme Corp",
                "effective_date": "2026-11-22",
                "resolution_subject": "the FY27 budget",
                "authorized_officer": "Alice Lee",
                "chair_name": "Bob Kim",
            }
        ),
        encoding="utf-8",
    )
    result = run_agent(
        "doc_generator",
        inputs={"json": str(payload_path)},
        settings=Settings(dry_run=True),
    )
    assert result.agent_name == "doc_generator"
    assert result.status == "COMPLETED"
    assert result.outputs["template"] == "board_resolution"
    assert result.outputs["missing_fields"] == []
    assert "Acme Corp" in result.outputs["document_markdown"]
    assert "Alice Lee" in result.outputs["document_markdown"]


def test_doc_generator_returns_needs_info_when_fields_missing() -> None:
    result = run_agent(
        "doc_generator",
        inputs={
            "template": "offer_letter",
            "json": {
                "candidate_name": "Sam Patel",
                "company_name": "Acme Corp",
            },
        },
        settings=Settings(dry_run=True),
    )
    assert result.agent_name == "doc_generator"
    assert result.status == "NEEDS_INFO"
    assert result.outputs["template"] == "offer_letter"
    assert result.outputs["document_markdown"] == ""
    assert "role_title" in result.outputs["missing_fields"]
    assert "base_salary" in result.outputs["missing_fields"]


def test_doc_generator_supports_custom_template_text() -> None:
    result = run_agent(
        "doc_generator",
        inputs={
            "template": "nda_notice",
            "template_text": "# Notice to {recipient}\n\nEffective {date}.",
            "recipient": "Vendor LLC",
            "date": "2026-12-01",
        },
        settings=Settings(dry_run=True),
    )
    assert result.status == "COMPLETED"
    assert result.outputs["template"] == "nda_notice"
    assert result.outputs["document_markdown"] == "# Notice to Vendor LLC\n\nEffective 2026-12-01."
