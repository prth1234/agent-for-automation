"""Document Generator Agent module."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from agents_for_automation.core.base import AgentContext, AgentRunResult
from agents_for_automation.core.manifest import AgentManifest

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

BUILTIN_TEMPLATES: dict[str, str] = {
    "board_resolution": (
        "# Unanimous Written Consent of the Board of Directors\n\n"
        "**Company:** {company_name}\n"
        "**Date:** {effective_date}\n\n"
        "## Resolution\n\n"
        "RESOLVED, that the Board of Directors of **{company_name}** hereby approves "
        "{resolution_subject}.\n\n"
        "RESOLVED FURTHER, that **{authorized_officer}** is authorized and directed to "
        "execute all documents and take all actions necessary to carry out the foregoing resolution.\n\n"
        "## Signatures\n\n"
        "- Chair / Director: {chair_name}\n"
        "- Authorized Officer: {authorized_officer}\n"
    ),
    "offer_letter": (
        "# Employment Offer Letter\n\n"
        "**Date:** {offer_date}\n"
        "**Candidate:** {candidate_name}\n"
        "**Company:** {company_name}\n\n"
        "Dear {candidate_name},\n\n"
        "We are pleased to offer you the position of **{role_title}** at **{company_name}**, "
        "reporting to **{manager_name}**, with an anticipated start date of **{start_date}**.\n\n"
        "## Compensation\n\n"
        "- **Base Salary:** {base_salary}\n\n"
        "Sincerely,\n\n"
        "{manager_name}\n"
        "{company_name}\n"
    ),
    "compliance_filing": (
        "# Compliance Filing Summary\n\n"
        "**Entity:** {entity_name}\n"
        "**Jurisdiction:** {jurisdiction}\n"
        "**Filing Type:** {filing_type}\n"
        "**Reporting Period:** {reporting_period}\n"
        "**Due Date:** {due_date}\n\n"
        "## Attestation\n\n"
        "Prepared and reviewed by **{preparer_name}** for submission in **{jurisdiction}**.\n"
    ),
}


class DocGeneratorAgent:
    """Renders legal and compliance Markdown documents from templates and structured data."""

    def __init__(self, manifest: AgentManifest) -> None:
        self.manifest = manifest

    def run(self, inputs: dict[str, Any], ctx: AgentContext) -> AgentRunResult:
        started = time.perf_counter()
        payload = self._load_payload(inputs)
        data: dict[str, Any] = {**inputs, **payload}

        custom_template = data.get("template_text")
        default_name = "custom" if custom_template else "board_resolution"
        template_name = str(data.get("template") or default_name).strip()

        if custom_template is not None and str(custom_template).strip():
            template_body = str(custom_template)
        elif template_name in BUILTIN_TEMPLATES:
            template_body = BUILTIN_TEMPLATES[template_name]
        else:
            available = ", ".join(sorted(BUILTIN_TEMPLATES))
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return AgentRunResult(
                agent_name=self.manifest.name,
                status="NEEDS_INFO",
                message=f"Unknown template '{template_name}'. Available templates: {available}.",
                dry_run=ctx.dry_run,
                duration_ms=elapsed_ms,
                outputs={
                    "template": template_name,
                    "document_markdown": "",
                    "missing_fields": ["template"],
                },
            )

        required_fields = self._extract_placeholders(template_body)
        missing_fields = [
            field for field in required_fields if field not in data or data[field] in (None, "")
        ]

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if missing_fields:
            return AgentRunResult(
                agent_name=self.manifest.name,
                status="NEEDS_INFO",
                message=f"Missing required fields for '{template_name}': {', '.join(missing_fields)}.",
                dry_run=ctx.dry_run,
                duration_ms=elapsed_ms,
                outputs={
                    "template": template_name,
                    "document_markdown": "",
                    "missing_fields": missing_fields,
                },
            )

        rendered = self._render_template(template_body, data)
        return AgentRunResult(
            agent_name=self.manifest.name,
            status="COMPLETED",
            message=f"Generated '{template_name}' document.",
            dry_run=ctx.dry_run,
            time_saved_minutes=self.manifest.estimated_time_saved_minutes,
            duration_ms=elapsed_ms,
            outputs={
                "template": template_name,
                "document_markdown": rendered,
                "missing_fields": [],
            },
        )

    @staticmethod
    def _load_payload(inputs: dict[str, Any]) -> dict[str, Any]:
        json_val = inputs.get("json")
        if isinstance(json_val, dict):
            return json_val
        if json_val:
            return json.loads(Path(str(json_val)).read_text(encoding="utf-8"))
        return {}

    @staticmethod
    def _extract_placeholders(template_body: str) -> list[str]:
        seen: dict[str, None] = {}
        for match in _PLACEHOLDER_RE.finditer(template_body):
            seen.setdefault(match.group(1), None)
        return list(seen.keys())

    @staticmethod
    def _render_template(template_body: str, data: dict[str, Any]) -> str:
        return _PLACEHOLDER_RE.sub(lambda m: str(data[m.group(1)]), template_body)


def create_agent(manifest: AgentManifest) -> DocGeneratorAgent:
    """Factory function referenced by agent.yaml."""
    return DocGeneratorAgent(manifest=manifest)
