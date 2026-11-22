"""Slack Q&A Agent module grounded in internal SOPs."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from agents_for_automation.core.base import AgentContext, AgentRunResult
from agents_for_automation.core.manifest import AgentManifest

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "do",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "my",
        "of",
        "on",
        "or",
        "our",
        "that",
        "the",
        "this",
        "to",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "with",
        "you",
    }
)

DEFAULT_SOPS: list[dict[str, str]] = [
    {
        "title": "Production Deployment and Rollback",
        "source": "sops/deployment.md",
        "content": (
            "## Standard Deployment\n"
            "Merge your PR to main after 2 approvals and passing CI checks. "
            "ArgoCD syncs staging automatically; promote to production via the release workflow.\n\n"
            "## Emergency Rollback\n"
            "To roll back a bad production release, run `argocd app rollback prod-api` "
            "or revert the merge commit on main and notify #deployments."
        ),
    },
    {
        "title": "On-Call Escalation Policy",
        "source": "sops/oncall_escalation.md",
        "content": (
            "## Severity 1 Incidents\n"
            "Page the primary on-call engineer via PagerDuty and open an incident channel "
            "using `/inc open` in Slack. Escalate to the engineering manager if unacknowledged after 10 minutes."
        ),
    },
    {
        "title": "VPN and Production Access",
        "source": "sops/access_requests.md",
        "content": (
            "## Requesting VPN or Database Access\n"
            "Submit an access request ticket in Jira under the SEC project with your manager's approval. "
            "Temporary production read access expires automatically after 4 hours."
        ),
    },
]


class SlackQAAgent:
    """Answers Slack questions grounded in internal SOPs with exact source citations."""

    def __init__(self, manifest: AgentManifest) -> None:
        self.manifest = manifest

    def run(self, inputs: dict[str, Any], ctx: AgentContext) -> AgentRunResult:
        started = time.perf_counter()
        payload = self._load_payload(inputs)
        question = str(inputs.get("question") or payload.get("question") or "").strip()
        if not question:
            return AgentRunResult(
                agent_name=self.manifest.name,
                status="NEEDS_INFO",
                message="Missing required input: 'question'.",
                dry_run=ctx.dry_run,
            )

        sops = self._load_sops(inputs, payload)
        matches = self._rank_sections(question, sops)

        if not matches:
            confidence = 0.0
            sources: list[str] = []
            answer = (
                "I couldn't find a matching SOP with enough confidence to answer this question. "
                "Please escalate to #ops-help or the on-call engineer for verification."
            )
            message = "No matching SOP found; returned low-confidence escalation response."
        else:
            top_matches = matches[:3]
            sources = list(dict.fromkeys(m["source"] for m in top_matches if m["source"]))
            confidence = round(min(1.0, top_matches[0]["score"]), 2)
            answer_lines = [f"Answer grounded in {len(sources)} SOP source(s):"]
            for match in top_matches:
                answer_lines.append(
                    f"- **{match['title']}** (`{match['source']}`): {match['section']}"
                )
            answer_lines.append("")
            answer_lines.append(f"Sources: {', '.join(sources)}")
            answer = "\n".join(answer_lines)
            message = f"Answered question using {len(sources)} SOP source(s) (confidence={confidence})."

        ctx.integrations.notifier.notify(f"Slack Q&A: {question[:60]}", answer)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return AgentRunResult(
            agent_name=self.manifest.name,
            status="COMPLETED",
            message=message,
            dry_run=ctx.dry_run,
            time_saved_minutes=self.manifest.estimated_time_saved_minutes,
            duration_ms=elapsed_ms,
            outputs={
                "question": question,
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
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
    def _load_sops(inputs: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, str]]:
        raw_sops = payload.get("sops") or inputs.get("sops")
        if isinstance(raw_sops, list) and raw_sops:
            return [
                {
                    "title": str(item.get("title", "Untitled SOP")),
                    "content": str(item.get("content", "")),
                    "source": str(item.get("source", "unknown")),
                }
                for item in raw_sops
                if isinstance(item, dict)
            ]

        sop_dir_val = inputs.get("sop_dir") or payload.get("sop_dir")
        if sop_dir_val:
            sop_dir = Path(str(sop_dir_val))
            if sop_dir.is_dir():
                loaded: list[dict[str, str]] = []
                for path in sorted(sop_dir.rglob("*")):
                    if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
                        loaded.append(
                            {
                                "title": path.stem.replace("_", " ").replace("-", " ").title(),
                                "content": path.read_text(encoding="utf-8"),
                                "source": str(path.relative_to(sop_dir)),
                            }
                        )
                if loaded:
                    return loaded

        return DEFAULT_SOPS

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        filtered = tokens - _STOPWORDS
        return filtered or tokens

    @classmethod
    def _split_sections(cls, content: str) -> list[str]:
        parts = [part.strip() for part in re.split(r"\n\s*\n+", content.strip()) if part.strip()]
        return parts or ([content.strip()] if content.strip() else [])

    @classmethod
    def _rank_sections(cls, question: str, sops: list[dict[str, str]]) -> list[dict[str, Any]]:
        q_tokens = cls._tokenize(question)
        if not q_tokens:
            return []

        ranked: list[dict[str, Any]] = []
        for sop in sops:
            title = sop.get("title", "Untitled SOP")
            source = sop.get("source", "unknown")
            title_tokens = cls._tokenize(title)
            for section in cls._split_sections(sop.get("content", "")):
                section_tokens = cls._tokenize(section)
                overlap = q_tokens & (section_tokens | title_tokens)
                if not overlap:
                    continue
                base_score = len(overlap) / len(q_tokens)
                title_bonus = 0.1 * (len(q_tokens & title_tokens) / len(q_tokens))
                score = min(1.0, base_score + title_bonus)
                ranked.append(
                    {
                        "title": title,
                        "source": source,
                        "section": " ".join(section.splitlines()),
                        "score": score,
                    }
                )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked


def create_agent(manifest: AgentManifest) -> SlackQAAgent:
    """Factory function referenced by agent.yaml."""
    return SlackQAAgent(manifest=manifest)
