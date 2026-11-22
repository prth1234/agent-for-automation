"""Bedrock Converse API adapter mirroring finops-ai-assistant's LLM setup."""
from __future__ import annotations

import os
from typing import Any

from langchain_aws import ChatBedrock

from agents_for_automation.config import Settings


def create_chat_model(settings: Settings, temperature: float | None = None) -> ChatBedrock:
    """Create a Bedrock Converse chat model using ambient AWS credentials (IAM / AWS_PROFILE)."""
    if settings.aws_profile and "AWS_PROFILE" not in os.environ:
        os.environ["AWS_PROFILE"] = settings.aws_profile

    effective_model_id = settings.bedrock_inference_profile_arn or settings.llm_model_id
    temp = settings.llm_temperature if temperature is None else temperature

    kwargs: dict[str, Any] = {
        "model_id": effective_model_id,
        "region_name": settings.bedrock_region,
        "beta_use_converse_api": True,
        "model_kwargs": {"temperature": temp},
    }
    if settings.llm_max_tokens is not None:
        kwargs["model_kwargs"]["max_tokens"] = settings.llm_max_tokens
    if effective_model_id.startswith("arn:"):
        kwargs["provider"] = settings.llm_model_id.split(".", maxsplit=1)[0].lower() or "anthropic"

    return ChatBedrock(**kwargs)
