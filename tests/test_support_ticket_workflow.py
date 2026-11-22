"""End-to-end tests for SupportTicketWorkflow using a fake classifier."""
from __future__ import annotations

from pathlib import Path

from agents_for_automation.config import Settings
from agents_for_automation.core.connectors.github import GitHubConnector
from agents_for_automation.core.connectors.jira import JiraConnector
from agents_for_automation.core.connectors.notifier import NotifierConnector
from agents_for_automation.core.models import (
    RepoConfig,
    TicketClassification,
    TicketContext,
    TicketIntent,
    TicketStatus,
)
from agents_for_automation.core.registry import RepoRegistry
from agents_for_automation.core.state import TicketStateStore
from agents_for_automation.workflows.support_ticket.workflow import SupportTicketWorkflow

SAMPLE_TFVARS = """\
variable "genie_org_ids" {
  type    = list(string)
  default = ["44118"]
}
"""


class _FakeClassifier:
    def __init__(self, result: TicketClassification) -> None:
        self._result = result

    def classify(self, ticket: TicketContext) -> TicketClassification:
        return self._result


def _build_workflow(tmp_path: Path, classification: TicketClassification) -> SupportTicketWorkflow:
    tf_file = tmp_path / "repo/_infra/terraform/databricks/envs/prod-us-west-2/variables.tf"
    tf_file.parent.mkdir(parents=True, exist_ok=True)
    tf_file.write_text(SAMPLE_TFVARS, encoding="utf-8")

    registry = RepoRegistry(
        {
            "cco-databricks": RepoConfig(
                name="cco-databricks",
                github_repo="flexera/cco-databricks",
                local_path=str(tmp_path / "repo"),
                genie_onboarding={
                    "variables_path_template": "_infra/terraform/databricks/envs/{env}/variables.tf",
                    "variable_name": "genie_org_ids",
                    "region_env_map": {"NAM": "prod-us-west-2"},
                },
            )
        }
    )
    settings = Settings(dry_run=True, state_file_path=tmp_path / "state.json")
    return SupportTicketWorkflow(
        settings=settings,
        registry=registry,
        classifier=_FakeClassifier(classification),  # type: ignore[arg-type]
        jira=JiraConnector(settings),
        github=GitHubConnector(settings),
        notifier=NotifierConnector(settings),
        state_store=TicketStateStore(settings.state_file_path),
    )


def test_genie_onboarding_opens_pr_and_is_idempotent(tmp_path: Path) -> None:
    wf = _build_workflow(
        tmp_path,
        TicketClassification(
            target_repo="cco-databricks",
            intent=TicketIntent.GENIE_ONBOARDING,
            org_id="60030",
            region_or_env="NAM",
        ),
    )
    ticket = TicketContext(
        ticket_key="SQ-32775",
        summary="enable FlexAI on NAM org 60030",
        assignee="Parth Singh",
        org_id="60030",
    )

    first = wf.run(ticket)
    assert first.status == TicketStatus.PR_OPENED
    assert first.branch_name == "SQ-32775-enable-flexai-on-nam-org-60030"
    assert first.pr_url == "https://github.com/flexera/cco-databricks/pull/DRY-RUN-SQ-32775"

    # Second run should short-circuit without opening a duplicate PR
    second = wf.run(ticket)
    assert second.status == TicketStatus.PR_OPENED
    assert "already processed" in second.message


def test_missing_region_asks_clarifying_question(tmp_path: Path) -> None:
    wf = _build_workflow(
        tmp_path,
        TicketClassification(
            target_repo="cco-databricks",
            intent=TicketIntent.GENIE_ONBOARDING,
            org_id="60030",
            region_or_env=None,
            missing_fields=["region_or_env"],
            clarifying_question="Which region (NAM, EMEA, APAC, staging) is org 60030 in?",
        ),
    )
    ticket = TicketContext(ticket_key="SQ-99999", summary="enable FlexAI for org 60030")
    res = wf.run(ticket)
    assert res.status == TicketStatus.NEEDS_INFO
    assert "Which region" in res.message
