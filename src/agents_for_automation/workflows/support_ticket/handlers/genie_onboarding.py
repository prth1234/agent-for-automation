"""Deterministic Terraform handler for cco-databricks Genie Space onboarding."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from agents_for_automation.core.models import RepoConfig

_DEFAULT_LIST_RE = re.compile(
    r'(variable\s+"(?P<var>\w+)"\s*\{[^}]*?default\s*=\s*\[)(?P<items>[^\]]*)(\])',
    re.DOTALL,
)


@dataclass(frozen=True)
class GenieUpdateResult:
    changed: bool
    already_exists: bool
    env_name: str
    relative_file_path: str
    reason: str


def resolve_env_name(region_or_env: str, region_env_map: dict[str, str]) -> str | None:
    """Map a ticket region/env string (e.g. 'NAM') to a Terraform env directory."""
    normalized = region_or_env.strip().upper()
    if normalized in region_env_map:
        return region_env_map[normalized]
    # Also allow direct lowercase env names present as map values
    lower = region_or_env.strip().lower()
    if lower in region_env_map.values():
        return lower
    return None


def add_genie_org_id(
    repo: RepoConfig,
    org_id: str,
    region_or_env: str,
    dry_run: bool = True,
) -> GenieUpdateResult:
    """Add org_id to var.genie_org_ids in the target environment's variables.tf."""
    cfg = repo.genie_onboarding
    region_env_map: dict[str, str] = cfg.get("region_env_map", {})
    env_name = resolve_env_name(region_or_env, region_env_map)
    if not env_name:
        return GenieUpdateResult(
            changed=False,
            already_exists=False,
            env_name=region_or_env,
            relative_file_path="",
            reason=f"Unknown region/environment '{region_or_env}'. Known values: {sorted(region_env_map)}",
        )

    rel_template = cfg.get(
        "variables_path_template",
        "_infra/terraform/databricks/envs/{env}/variables.tf",
    )
    var_name = cfg.get("variable_name", "genie_org_ids")
    rel_path = rel_template.format(env=env_name)
    full_path = Path(repo.local_path) / rel_path

    if not full_path.exists():
        return GenieUpdateResult(
            changed=False,
            already_exists=False,
            env_name=env_name,
            relative_file_path=rel_path,
            reason=f"Terraform file not found: {full_path}",
        )

    content = full_path.read_text(encoding="utf-8")
    updated, already_exists = _insert_org_id_in_hcl(content, var_name, org_id)

    if already_exists:
        return GenieUpdateResult(
            changed=False,
            already_exists=True,
            env_name=env_name,
            relative_file_path=rel_path,
            reason=f"Org ID '{org_id}' is already present in {rel_path}.",
        )

    if not dry_run:
        full_path.write_text(updated, encoding="utf-8")

    return GenieUpdateResult(
        changed=True,
        already_exists=False,
        env_name=env_name,
        relative_file_path=rel_path,
        reason=f"Added Org ID '{org_id}' to {var_name} in {rel_path}.",
    )


def _insert_org_id_in_hcl(content: str, var_name: str, org_id: str) -> tuple[str, bool]:
    """Insert org_id into the `default = [...]` list of `variable "<var_name>"`."""
    for match in _DEFAULT_LIST_RE.finditer(content):
        if match.group("var") != var_name:
            continue
        raw_items = match.group("items")
        existing = re.findall(r'"([^"]+)"', raw_items)
        if org_id in existing:
            return content, True

        new_items = [*existing, org_id]
        formatted_list = ", ".join(f'"{item}"' for item in new_items)
        replacement = f"{match.group(1)}{formatted_list}{match.group(4)}"
        updated = content[: match.start()] + replacement + content[match.end() :]
        return updated, False

    raise ValueError(f'Could not find variable "{var_name}" with a default list in Terraform file')
