"""Jira REST API v3 connector with dry-run support."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from agents_for_automation.config import Settings
from agents_for_automation.core.models import TicketContext

logger = logging.getLogger(__name__)


class JiraConnector:
    """Reads Jira issues and posts comments."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.jira_base_url.rstrip("/")
        self._auth = (
            (settings.jira_user_email, settings.jira_api_token)
            if settings.jira_user_email and settings.jira_api_token
            else None
        )
        self._dry_run = settings.dry_run

    def fetch_issue(self, ticket_key: str) -> TicketContext:
        """Fetch an issue from Jira REST API v3."""
        if not self._auth:
            raise RuntimeError("JIRA_USER_EMAIL and JIRA_API_TOKEN are required to fetch issues")
        url = f"{self._base_url}/rest/api/3/issue/{ticket_key}"
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, auth=self._auth)
            resp.raise_for_status()
            return self.parse_issue_payload(resp.json())

    def post_comment(self, ticket_key: str, body_text: str) -> str:
        """Post a plain-text comment (ADF) on a Jira issue."""
        if self._dry_run:
            logger.info("[DRY-RUN] Jira comment on %s:\n%s", ticket_key, body_text)
            return f"dry-run://jira/{ticket_key}/comment"

        if not self._auth:
            raise RuntimeError("JIRA_USER_EMAIL and JIRA_API_TOKEN are required to post comments")

        url = f"{self._base_url}/rest/api/3/issue/{ticket_key}/comment"
        adf_payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body_text}],
                    }
                ],
            }
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, auth=self._auth, json=adf_payload)
            resp.raise_for_status()
            return resp.json().get("self", url)

    @staticmethod
    def parse_issue_payload(payload: dict[str, Any]) -> TicketContext:
        """Normalize a Jira webhook or REST API issue JSON into TicketContext."""
        issue = payload.get("issue", payload)
        fields = issue.get("fields", {})
        comments_raw = (fields.get("comment") or {}).get("comments", [])
        comments = [_extract_adf_text(c.get("body")) for c in comments_raw]

        return TicketContext(
            ticket_key=issue["key"],
            summary=fields.get("summary", ""),
            description=_extract_adf_text(fields.get("description")),
            assignee=(fields.get("assignee") or {}).get("displayName"),
            reporter=(fields.get("reporter") or {}).get("displayName"),
            team=_extract_field_name(fields.get("customfield_team")) or _extract_field_name(fields.get("team")),
            org_id=_extract_org_id(fields),
            comments=[c for c in comments if c],
            raw_fields=fields,
        )


def _extract_field_name(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("name") or value.get("value")
    if isinstance(value, str):
        return value
    return None


def _extract_org_id(fields: dict[str, Any]) -> str | None:
    for key in ("org_id", "Org ID", "customfield_org_id"):
        val = fields.get(key)
        if val is not None:
            return str(val).strip()
    return None


def _extract_adf_text(node: Any) -> str:
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts = [_extract_adf_text(child) for child in node.get("content", [])]
    return " ".join(p for p in parts if p).strip()
