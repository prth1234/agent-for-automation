"""Weekly Digest Agent module."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agents_for_automation.core.base import AgentContext, AgentRunResult
from agents_for_automation.core.manifest import AgentManifest


class WeeklyDigestAgent:
    """Builds a structured weekly summary of tickets and PRs and dispatches it."""

    def __init__(self, manifest: AgentManifest) -> None:
        self.manifest = manifest

    def run(self, inputs: dict[str, Any], ctx: AgentContext) -> AgentRunResult:
        started = time.perf_counter()
        payload = self._load_payload(inputs)
        team = str(payload.get("team") or inputs.get("team") or "Engineering")
        tickets: list[dict[str, Any]] = list(payload.get("tickets", []))
        prs: list[dict[str, Any]] = list(payload.get("prs", []))

        lines = [f"# Weekly Digest — {team}", ""]
        lines.append(f"**Tickets processed:** {len(tickets)}")
        for t in tickets:
            lines.append(f"- `{t.get('key', '?')}`: {t.get('summary', '')} ({t.get('status', 'unknown')})")

        lines.append("")
        lines.append(f"**Pull Requests:** {len(prs)}")
        for pr in prs:
            lines.append(f"- {pr.get('title', 'Untitled')} ({pr.get('url', 'no-url')})")

        digest_markdown = "\n".join(lines)
        title = f"[{team}] Weekly Automation Digest"
        ctx.integrations.notifier.notify(title, digest_markdown)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return AgentRunResult(
            agent_name=self.manifest.name,
            status="COMPLETED",
            message=f"Generated weekly digest for {team} ({len(tickets)} tickets, {len(prs)} PRs).",
            dry_run=ctx.dry_run,
            time_saved_minutes=self.manifest.estimated_time_saved_minutes,
            duration_ms=elapsed_ms,
            outputs={
                "team": team,
                "ticket_count": len(tickets),
                "pr_count": len(prs),
                "digest_markdown": digest_markdown,
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


def create_agent(manifest: AgentManifest) -> WeeklyDigestAgent:
    """Factory function referenced by agent.yaml."""
    return WeeklyDigestAgent(manifest=manifest)
