"""Tests for AWS SES NotifierConnector."""
from __future__ import annotations

from typing import Any

from agents_for_automation.config import Settings
from agents_for_automation.core.connectors.notifier import NotifierConnector


class _FakeSESClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send_email(self, **kwargs: Any) -> dict[str, str]:
        self.calls.append(kwargs)
        return {"MessageId": "fake-msg-id"}


def test_ses_email_sent_when_live() -> None:
    fake_ses = _FakeSESClient()
    settings = Settings(
        dry_run=False,
        ses_region="us-east-1",
        ses_sender_email="automation@flexera.com",
        notify_email_to="psingh@flexera.com, team@flexera.com",
    )
    notifier = NotifierConnector(settings, ses_client=fake_ses)
    notifier.notify("[SQ-32775] PR Opened", "PR: https://github.com/flexera/cco-databricks/pull/1")

    assert len(fake_ses.calls) == 1
    call = fake_ses.calls[0]
    assert call["Source"] == "automation@flexera.com"
    assert call["Destination"]["ToAddresses"] == ["psingh@flexera.com", "team@flexera.com"]
    assert call["Message"]["Subject"]["Data"] == "[SQ-32775] PR Opened"


def test_ses_email_skipped_in_dry_run() -> None:
    fake_ses = _FakeSESClient()
    settings = Settings(
        dry_run=True,
        ses_sender_email="automation@flexera.com",
        notify_email_to="psingh@flexera.com",
    )
    notifier = NotifierConnector(settings, ses_client=fake_ses)
    notifier.notify("Test", "Body")
    assert fake_ses.calls == []
