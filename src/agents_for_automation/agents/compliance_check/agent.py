"""Compliance Check Agent module."""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any

from agents_for_automation.core.base import AgentContext, AgentRunResult
from agents_for_automation.core.manifest import AgentManifest

BUILTIN_RULESETS: dict[str, list[str]] = {
    "vendor_onboarding": [
        "w9",
        "soc2_report",
        "insurance_certificate",
        "msa",
    ],
    "release_readiness": [
        "security_signoff",
        "qa_signoff",
        "rollback_plan",
        "changelog",
    ],
}


class ComplianceCheckAgent:
    """Validates submitted documents for completeness, consistency, and expiration."""

    def __init__(self, manifest: AgentManifest) -> None:
        self.manifest = manifest

    def run(self, inputs: dict[str, Any], ctx: AgentContext) -> AgentRunResult:
        started = time.perf_counter()
        payload = self._load_payload(inputs)

        custom_required = payload.get("required_documents") or inputs.get("required_documents")
        ruleset = str(payload.get("ruleset") or inputs.get("ruleset") or "vendor_onboarding").strip()

        if isinstance(custom_required, list) and custom_required:
            required_documents = [str(doc).strip() for doc in custom_required if str(doc).strip()]
        elif ruleset in BUILTIN_RULESETS:
            required_documents = list(BUILTIN_RULESETS[ruleset])
        else:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return AgentRunResult(
                agent_name=self.manifest.name,
                status="NEEDS_INFO",
                message=f"Unknown ruleset '{ruleset}' and no 'required_documents' list provided.",
                dry_run=ctx.dry_run,
                duration_ms=elapsed_ms,
                outputs={
                    "passed": False,
                    "missing_documents": [],
                    "inconsistencies": [],
                    "expired_documents": [],
                },
            )

        documents: list[dict[str, Any]] = list(payload.get("documents", []))
        today = date.today()

        missing_documents = self._find_missing_documents(required_documents, documents)
        inconsistencies = self._find_inconsistencies(documents)
        expired_documents = self._find_expired_documents(documents, today)

        passed = not (missing_documents or inconsistencies or expired_documents)
        status = "COMPLETED" if passed else "ISSUES_FOUND"

        if not passed:
            summary = self._format_issue_summary(
                ruleset=ruleset,
                missing_documents=missing_documents,
                inconsistencies=inconsistencies,
                expired_documents=expired_documents,
            )
            ctx.integrations.notifier.notify(
                f"[Compliance Check] Issues flagged ({ruleset})",
                summary,
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        message = (
            f"Compliance check passed for ruleset '{ruleset}' ({len(documents)} documents)."
            if passed
            else (
                f"Compliance check flagged issues for ruleset '{ruleset}': "
                f"{len(missing_documents)} missing, "
                f"{len(inconsistencies)} inconsistencies, "
                f"{len(expired_documents)} expired."
            )
        )

        return AgentRunResult(
            agent_name=self.manifest.name,
            status=status,
            message=message,
            dry_run=ctx.dry_run,
            time_saved_minutes=self.manifest.estimated_time_saved_minutes,
            duration_ms=elapsed_ms,
            outputs={
                "passed": passed,
                "missing_documents": missing_documents,
                "inconsistencies": inconsistencies,
                "expired_documents": expired_documents,
            },
        )

    @staticmethod
    def _load_payload(inputs: dict[str, Any]) -> dict[str, Any]:
        json_val = inputs.get("json")
        if isinstance(json_val, dict):
            return json_val
        if json_val:
            return json.loads(Path(str(json_val)).read_text(encoding="utf-8"))
        return inputs

    @staticmethod
    def _find_missing_documents(
        required_documents: list[str],
        documents: list[dict[str, Any]],
    ) -> list[str]:
        submitted_types = {
            str(doc.get("type", "")).strip()
            for doc in documents
            if doc.get("type")
        }
        return [req for req in required_documents if req not in submitted_types]

    @staticmethod
    def _find_inconsistencies(documents: list[dict[str, Any]]) -> list[str]:
        inconsistencies: list[str] = []
        entity_names = sorted(
            {str(doc["entity_name"]).strip() for doc in documents if doc.get("entity_name")}
        )
        entity_ids = sorted(
            {str(doc["entity_id"]).strip() for doc in documents if doc.get("entity_id")}
        )
        if len(entity_names) > 1:
            inconsistencies.append(
                f"Inconsistent entity_name across documents: {', '.join(entity_names)}"
            )
        if len(entity_ids) > 1:
            inconsistencies.append(
                f"Inconsistent entity_id across documents: {', '.join(entity_ids)}"
            )
        return inconsistencies

    @staticmethod
    def _find_expired_documents(
        documents: list[dict[str, Any]],
        today: date,
    ) -> list[dict[str, str]]:
        expired: list[dict[str, str]] = []
        for doc in documents:
            expires_raw = doc.get("expires_on")
            if not expires_raw:
                continue
            expires_str = str(expires_raw).strip()
            try:
                exp_date = date.fromisoformat(expires_str[:10])
            except ValueError:
                continue
            if exp_date < today:
                expired.append(
                    {
                        "type": str(doc.get("type", "unknown")),
                        "expires_on": expires_str,
                    }
                )
        return expired

    @staticmethod
    def _format_issue_summary(
        *,
        ruleset: str,
        missing_documents: list[str],
        inconsistencies: list[str],
        expired_documents: list[dict[str, str]],
    ) -> str:
        lines = [f"# Compliance Check Issues ({ruleset})", ""]
        if missing_documents:
            lines.append("**Missing documents:**")
            lines.extend(f"- {doc}" for doc in missing_documents)
            lines.append("")
        if inconsistencies:
            lines.append("**Inconsistencies:**")
            lines.extend(f"- {item}" for item in inconsistencies)
            lines.append("")
        if expired_documents:
            lines.append("**Expired documents:**")
            lines.extend(
                f"- `{item['type']}` (expired on {item['expires_on']})"
                for item in expired_documents
            )
        return "\n".join(lines).strip()


def create_agent(manifest: AgentManifest) -> ComplianceCheckAgent:
    """Factory function referenced by `entrypoint: agent:create_agent` in agent.yaml."""
    return ComplianceCheckAgent(manifest=manifest)
