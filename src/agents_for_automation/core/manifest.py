"""Agent manifest schema loaded from each agent module's agent.yaml."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AgentInputSpec(BaseModel):
    """Describes a single input parameter accepted by an agent module."""

    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    default: Any = None


class AgentManifest(BaseModel):
    """Declarative metadata for a marketplace agent module (agent.yaml)."""

    name: str
    version: str = "0.1.0"
    description: str
    category: str = "general"
    status: str = "stable"
    triggers: list[str] = Field(default_factory=lambda: ["cli"])
    permissions: list[str] = Field(default_factory=list)
    inputs: list[AgentInputSpec] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    estimated_time_saved_minutes: int = 15
    entrypoint: str = "agent:create_agent"

    @classmethod
    def from_yaml(cls, path: Path) -> AgentManifest:
        """Load and validate an AgentManifest from a YAML file."""
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(raw)
