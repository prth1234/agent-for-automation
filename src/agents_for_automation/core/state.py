"""Lightweight JSON state store for ticket idempotency and status tracking."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agents_for_automation.core.models import TicketStatus


class TicketStateStore:
    """Persists per-ticket automation status to prevent duplicate PRs and track clarifications."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get(self, ticket_key: str) -> dict[str, Any] | None:
        return self._data.get(ticket_key)

    def get_status(self, ticket_key: str) -> TicketStatus | None:
        entry = self.get(ticket_key)
        if not entry:
            return None
        return TicketStatus(entry["status"])

    def set(
        self,
        ticket_key: str,
        status: TicketStatus,
        pr_url: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._data[ticket_key] = {
            "status": status.value,
            "pr_url": pr_url,
            "updated_at": datetime.now(UTC).isoformat(),
            **(extra or {}),
        }
        self._save()
