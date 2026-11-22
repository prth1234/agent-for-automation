"""Auto-discovery registry for marketplace agent modules."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path

from agents_for_automation.core.base import AgentModule
from agents_for_automation.core.manifest import AgentManifest

DEFAULT_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"


@dataclass(frozen=True)
class AgentEntry:
    """Discovered agent module metadata and filesystem location."""

    manifest: AgentManifest
    directory: Path
    package: str


class AgentRegistry:
    """Discovers and instantiates agent modules from src/agents_for_automation/agents/."""

    def __init__(self, entries: dict[str, AgentEntry]) -> None:
        self._entries = entries

    @classmethod
    def discover(cls, agents_dir: Path | None = None) -> AgentRegistry:
        """Scan agents_dir for subdirectories containing agent.yaml (skipping _template)."""
        root = agents_dir or DEFAULT_AGENTS_DIR
        entries: dict[str, AgentEntry] = {}
        if not root.exists():
            return cls(entries)

        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("_") or child.name.startswith("."):
                continue
            manifest_path = child / "agent.yaml"
            if not manifest_path.exists():
                continue
            manifest = AgentManifest.from_yaml(manifest_path)
            entries[manifest.name] = AgentEntry(
                manifest=manifest,
                directory=child,
                package=f"agents_for_automation.agents.{child.name}",
            )
        return cls(entries)

    def list_agents(self) -> list[AgentManifest]:
        """Return manifests for all discovered agents."""
        return [entry.manifest for entry in self._entries.values()]

    def get(self, name: str) -> AgentEntry | None:
        """Return the AgentEntry for a given agent name, if registered."""
        return self._entries.get(name)

    def load_agent(self, name: str) -> AgentModule:
        """Dynamically import and instantiate the named agent module."""
        entry = self._entries.get(name)
        if entry is None:
            available = ", ".join(sorted(self._entries)) or "(none)"
            raise KeyError(f"Unknown agent '{name}'. Available agents: {available}")

        module_rel, factory_name = entry.manifest.entrypoint.split(":", 1)
        module = importlib.import_module(f"{entry.package}.{module_rel}")
        factory = getattr(module, factory_name)
        agent: AgentModule = factory(entry.manifest)
        return agent
