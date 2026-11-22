"""Tests for deterministic cco-databricks Genie Space onboarding handler."""
from __future__ import annotations

from pathlib import Path

from agents_for_automation.core.models import RepoConfig
from agents_for_automation.workflows.support_ticket.handlers.genie_onboarding import (
    add_genie_org_id,
    resolve_env_name,
)

SAMPLE_TFVARS = """\
variable "genie_org_ids" {
  description = "Flexera org ids getting a dedicated Genie Space in this workspace."
  type        = list(string)
  default     = ["44118", "60030"]
}
"""


def _make_repo(tmp_path: Path) -> RepoConfig:
    tf_file = tmp_path / "_infra/terraform/databricks/envs/prod-us-west-2/variables.tf"
    tf_file.parent.mkdir(parents=True, exist_ok=True)
    tf_file.write_text(SAMPLE_TFVARS, encoding="utf-8")
    return RepoConfig(
        name="cco-databricks",
        github_repo="flexera/cco-databricks",
        local_path=str(tmp_path),
        genie_onboarding={
            "variables_path_template": "_infra/terraform/databricks/envs/{env}/variables.tf",
            "variable_name": "genie_org_ids",
            "region_env_map": {"NAM": "prod-us-west-2", "EMEA": "prod-eu"},
        },
    )


def test_resolve_env_name() -> None:
    mapping = {"NAM": "prod-us-west-2", "EMEA": "prod-eu"}
    assert resolve_env_name("NAM", mapping) == "prod-us-west-2"
    assert resolve_env_name("prod-eu", mapping) == "prod-eu"
    assert resolve_env_name("MARS", mapping) is None


def test_add_new_org_id_writes_when_not_dry_run(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    res = add_genie_org_id(repo, org_id="99999", region_or_env="NAM", dry_run=False)
    assert res.changed is True
    assert res.already_exists is False
    assert res.env_name == "prod-us-west-2"
    updated = (
        tmp_path / "_infra/terraform/databricks/envs/prod-us-west-2/variables.tf"
    ).read_text(encoding="utf-8")
    assert '"99999"' in updated


def test_add_existing_org_id_is_idempotent(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    res = add_genie_org_id(repo, org_id="60030", region_or_env="NAM", dry_run=False)
    assert res.changed is False
    assert res.already_exists is True


def test_unknown_region_returns_reason(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    res = add_genie_org_id(repo, org_id="99999", region_or_env="UNKNOWN", dry_run=True)
    assert res.changed is False
    assert "Unknown region" in res.reason
