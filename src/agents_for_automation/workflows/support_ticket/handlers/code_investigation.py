"""Bedrock-driven codebase investigation handler for product bug tickets."""
from __future__ import annotations

import subprocess
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agents_for_automation.core.models import RepoConfig, TicketContext


class InvestigationReport(BaseModel):
    """Structured root-cause analysis and optional patch proposal."""

    root_cause: str
    relevant_files: list[str] = Field(default_factory=list)
    confidence: str = Field(description="high | medium | low")
    proposed_fix_summary: str
    patch_file: str | None = None
    target_snippet: str | None = None
    replacement_snippet: str | None = None


INVESTIGATION_SYSTEM_PROMPT = """\
You are a senior FinOps AI Assistant engineer investigating a Jira support ticket.
Use ONLY the provided code search snippets and file contents. Do NOT invent file paths or symbols.
If you are confident in a minimal, safe fix, populate `patch_file`, `target_snippet` (exact match),
and `replacement_snippet`. Otherwise leave `patch_file` as null and provide a clear `root_cause`.
"""


def investigate_bug(
    llm: BaseChatModel,
    repo: RepoConfig,
    ticket: TicketContext,
    dry_run: bool = True,
) -> tuple[InvestigationReport, list[str]]:
    """Search the target repo for keywords from the ticket and ask Bedrock to analyze."""
    repo_root = Path(repo.local_path)
    keywords = _extract_search_terms(ticket.summary + " " + ticket.description)
    snippets = _search_repo(repo_root, keywords)

    structured_llm = llm.with_structured_output(InvestigationReport)
    user_prompt = (
        f"Ticket: {ticket.ticket_key}\n"
        f"Summary: {ticket.summary}\n"
        f"Description:\n{ticket.description}\n\n"
        f"Code search matches in {repo.name}:\n{snippets or '(no matches)'}"
    )
    report = structured_llm.invoke(
        [SystemMessage(content=INVESTIGATION_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )
    assert isinstance(report, InvestigationReport)

    changed_files: list[str] = []
    if (
        not dry_run
        and report.confidence == "high"
        and report.patch_file
        and report.target_snippet
        and report.replacement_snippet is not None
    ):
        target_path = (repo_root / report.patch_file).resolve()
        if target_path.is_relative_to(repo_root.resolve()) and target_path.exists():
            text = target_path.read_text(encoding="utf-8")
            if report.target_snippet in text:
                target_path.write_text(
                    text.replace(report.target_snippet, report.replacement_snippet, 1),
                    encoding="utf-8",
                )
                changed_files.append(report.patch_file)

    return report, changed_files


def _extract_search_terms(text: str) -> list[str]:
    tokens = [w.strip(".,:;!?()[]{}\"'") for w in text.split()]
    return [t for t in tokens if len(t) >= 4 and t.isalnum()][:6]


def _search_repo(repo_root: Path, keywords: list[str]) -> str:
    if not keywords or not repo_root.exists():
        return ""
    pattern = "|".join(keywords)
    proc = subprocess.run(
        ["rg", "-n", "--max-count", "3", "-g", "*.py", pattern, str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = proc.stdout.splitlines()[:40]
    return "\n".join(lines)
