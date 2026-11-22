"""Notification connector for AWS SES email and optional MS Teams webhooks."""
from __future__ import annotations

import logging

import boto3
import httpx

from agents_for_automation.config import Settings

logger = logging.getLogger(__name__)


class NotifierConnector:
    """Dispatches automation results via AWS SES email and/or MS Teams."""

    def __init__(self, settings: Settings, ses_client: object | None = None) -> None:
        self._ses_region = settings.ses_region
        self._ses_sender = settings.ses_sender_email
        self._email_to = [
            addr.strip() for addr in settings.notify_email_to.split(",") if addr.strip()
        ]
        self._teams_url = settings.teams_webhook_url
        self._dry_run = settings.dry_run
        self._ses_client = ses_client

    def notify(self, title: str, message: str) -> None:
        """Send notification to configured channels (respecting dry_run)."""
        if self._dry_run:
            logger.info("[DRY-RUN] Notification | %s | %s", title, message)
            return

        if self._ses_sender and self._email_to:
            self._send_ses_email(title, message)
        if self._teams_url:
            self._send_teams(title, message)

    def _send_ses_email(self, subject: str, body: str) -> None:
        client = self._ses_client or boto3.client("ses", region_name=self._ses_region)
        client.send_email(
            Source=self._ses_sender,
            Destination={"ToAddresses": self._email_to},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            },
        )

    def _send_teams(self, title: str, message: str) -> None:
        payload = {"title": title, "text": message}
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(self._teams_url, json=payload)
            resp.raise_for_status()
