"""Bedrock-powered structured ticket classifier and parameter extractor."""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agents_for_automation.core.models import TicketClassification, TicketContext
from agents_for_automation.core.registry import RepoRegistry

CLASSIFIER_SYSTEM_PROMPT = """\
You are a senior Thorium engineering triage agent.
Given a Jira Support Question (SQ) ticket and the registered repositories below, classify:
1. `target_repo`: Which repository owns this request (or null if unclear/out of scope).
2. `intent`:
   - `genie_onboarding`: Request to enable/add/create FlexAI or Genie Space for an org/region.
   - `bug_investigation`: Product issue, error, or unexpected behavior in FinOps AI Assistant.
   - `unknown`: Anything else or insufficient context.
3. `org_id`: Extract the numeric Flexera Org ID if present in fields, summary, description, or comments. NEVER invent one.
4. `region_or_env`: Extract region or environment (e.g., NAM, EMEA, EU, APAC, staging, sandbox, prod-us-west-2, prod-us-east-1, prod-eu, prod-ap). NEVER guess if not stated.
5. `missing_fields`: List any required parameters that are missing (for `genie_onboarding`, both `org_id` and `region_or_env` are required).
6. `clarifying_question`: If `missing_fields` is non-empty, write a concise, polite Jira comment asking the reporter for only the missing details.

Registered repositories:
{repos_context}
"""


class TicketClassifier:
    """Classifies Jira tickets using Bedrock structured output."""

    def __init__(self, llm: BaseChatModel, registry: RepoRegistry) -> None:
        self._structured_llm = llm.with_structured_output(TicketClassification)
        self._registry = registry

    def classify(self, ticket: TicketContext) -> TicketClassification:
        system_prompt = CLASSIFIER_SYSTEM_PROMPT.format(
            repos_context=self._registry.describe_for_prompt()
        )
        comments_block = "\n".join(f"- {c}" for c in ticket.comments) or "(none)"
        user_prompt = (
            f"Ticket: {ticket.ticket_key}\n"
            f"Summary: {ticket.summary}\n"
            f"Team: {ticket.team or '(unset)'}\n"
            f"Org ID field: {ticket.org_id or '(unset)'}\n"
            f"Reporter: {ticket.reporter or '(unset)'}\n"
            f"Description:\n{ticket.description or '(empty)'}\n\n"
            f"Comments:\n{comments_block}"
        )
        result = self._structured_llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        )
        assert isinstance(result, TicketClassification)
        # Prefer explicit Jira Org ID custom field if LLM missed it
        if not result.org_id and ticket.org_id:
            result.org_id = ticket.org_id
            result.missing_fields = [f for f in result.missing_fields if f != "org_id"]
        return result
