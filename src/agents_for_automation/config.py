"""Application settings loaded from environment variables or .env."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for Bedrock, Jira, GitHub, and notifications."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Bedrock LLM (mirrors finops-ai-assistant/libs/platform_libs/providers/llm)
    llm_provider: str = "bedrock"
    llm_model_id: str = Field(default="us.anthropic.claude-sonnet-4-6", min_length=1)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_max_tokens: int | None = Field(default=4096, gt=0)
    bedrock_region: str = "us-east-1"
    bedrock_inference_profile_arn: str | None = None
    aws_profile: str | None = None

    # Execution safety
    dry_run: bool = True
    post_initial_ack: bool = True

    # Paths
    repos_config_path: Path = Path("config/repos.yaml")
    workspaces_root: Path = Path("/Users/psingh/Desktop/Workyard")
    state_file_path: Path = Path(".afa_state.json")

    # Jira
    jira_base_url: str = "https://flexera.atlassian.net"
    jira_user_email: str = ""
    jira_api_token: str = ""
    jira_webhook_secret: str = ""

    # GitHub
    github_token: str = ""
    github_base_branch: str = "main"

    # Notifications (AWS SES + optional Teams)
    ses_region: str = "us-east-1"
    ses_sender_email: str = ""
    notify_email_to: str = ""
    teams_webhook_url: str = ""
