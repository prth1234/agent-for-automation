"""Main Support Ticket Automation workflow orchestrator."""
from __future__ import annotations

from agents_for_automation.config import Settings
from agents_for_automation.core.connectors.github import GitHubConnector, build_branch_name
from agents_for_automation.core.connectors.jira import JiraConnector
from agents_for_automation.core.connectors.notifier import NotifierConnector
from agents_for_automation.core.models import (
    TicketContext,
    TicketIntent,
    TicketStatus,
    WorkflowResult,
)
from agents_for_automation.core.registry import RepoRegistry
from agents_for_automation.core.state import TicketStateStore
from agents_for_automation.workflows.support_ticket.classifier import TicketClassifier
from agents_for_automation.workflows.support_ticket.handlers.code_investigation import (
    investigate_bug,
)
from agents_for_automation.workflows.support_ticket.handlers.genie_onboarding import (
    add_genie_org_id,
)


class SupportTicketWorkflow:
    """End-to-end handler for Jira SQ tickets."""

    name = "support_ticket"

    def __init__(
        self,
        settings: Settings,
        registry: RepoRegistry,
        classifier: TicketClassifier,
        jira: JiraConnector,
        github: GitHubConnector,
        notifier: NotifierConnector,
        state_store: TicketStateStore,
        llm: object | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._classifier = classifier
        self._jira = jira
        self._github = github
        self._notifier = notifier
        self._state = state_store
        self._llm = llm

    def run(self, ticket: TicketContext) -> WorkflowResult:
        """Process a Jira support ticket through classification, action, PR, and notification."""
        existing_status = self._state.get_status(ticket.ticket_key)
        if existing_status in (TicketStatus.PR_OPENED, TicketStatus.ALREADY_EXISTS):
            entry = self._state.get(ticket.ticket_key) or {}
            return WorkflowResult(
                ticket_key=ticket.ticket_key,
                status=existing_status,
                message=f"Ticket {ticket.ticket_key} already processed ({existing_status}).",
                pr_url=entry.get("pr_url"),
            )

        if self._settings.post_initial_ack and existing_status is None:
            assignee_note = f" Assigned to {ticket.assignee}." if ticket.assignee else ""
            self._jira.post_comment(
                ticket.ticket_key,
                f"We have received your query ({ticket.ticket_key}).{assignee_note} "
                "Our automation agent is reviewing it now.",
            )
            self._state.set(ticket.ticket_key, TicketStatus.RECEIVED)

        classification = self._classifier.classify(ticket)
        repo = self._registry.get(classification.target_repo) if classification.target_repo else None

        if repo is None:
            msg = (
                f"Could not route {ticket.ticket_key} to a registered repository "
                f"(reasoning: {classification.reasoning}). Escalating to assignee."
            )
            self._state.set(ticket.ticket_key, TicketStatus.ESCALATED)
            self._notifier.notify(f"[{ticket.ticket_key}] Escalated", msg)
            return WorkflowResult(
                ticket_key=ticket.ticket_key,
                status=TicketStatus.ESCALATED,
                message=msg,
            )

        if classification.missing_fields:
            question = classification.clarifying_question or (
                f"To proceed with this request, could you please provide: "
                f"{', '.join(classification.missing_fields)}?"
            )
            self._jira.post_comment(ticket.ticket_key, question)
            self._state.set(ticket.ticket_key, TicketStatus.NEEDS_INFO)
            return WorkflowResult(
                ticket_key=ticket.ticket_key,
                status=TicketStatus.NEEDS_INFO,
                message=question,
                target_repo=repo.name,
            )

        if classification.intent == TicketIntent.GENIE_ONBOARDING:
            return self._handle_genie_onboarding(
                ticket=ticket,
                repo=repo,
                org_id=classification.org_id or "",
                region_or_env=classification.region_or_env or "",
            )

        if classification.intent == TicketIntent.BUG_INVESTIGATION and self._llm is not None:
            return self._handle_bug_investigation(ticket=ticket, repo=repo)

        msg = f"Unsupported or unclear intent '{classification.intent}' for {ticket.ticket_key}."
        self._state.set(ticket.ticket_key, TicketStatus.ESCALATED)
        return WorkflowResult(
            ticket_key=ticket.ticket_key,
            status=TicketStatus.ESCALATED,
            message=msg,
            target_repo=repo.name,
        )

    def _handle_genie_onboarding(
        self,
        ticket: TicketContext,
        repo: object,
        org_id: str,
        region_or_env: str,
    ) -> WorkflowResult:
        from agents_for_automation.core.models import RepoConfig

        assert isinstance(repo, RepoConfig)
        from pathlib import Path

        self._github.ensure_repo_ready(
            repo_path=Path(repo.local_path),
            github_repo=repo.github_repo,
            base_branch=repo.base_branch,
        )
        update = add_genie_org_id(
            repo=repo,
            org_id=org_id,
            region_or_env=region_or_env,
            dry_run=self._settings.dry_run,
        )

        if update.already_exists:
            self._jira.post_comment(ticket.ticket_key, update.reason)
            self._state.set(ticket.ticket_key, TicketStatus.ALREADY_EXISTS)
            self._notifier.notify(f"[{ticket.ticket_key}] Already Onboarded", update.reason)
            return WorkflowResult(
                ticket_key=ticket.ticket_key,
                status=TicketStatus.ALREADY_EXISTS,
                message=update.reason,
                target_repo=repo.name,
            )

        if not update.changed:
            self._jira.post_comment(ticket.ticket_key, update.reason)
            self._state.set(ticket.ticket_key, TicketStatus.NEEDS_INFO)
            return WorkflowResult(
                ticket_key=ticket.ticket_key,
                status=TicketStatus.NEEDS_INFO,
                message=update.reason,
                target_repo=repo.name,
            )

        branch_name = build_branch_name(ticket.ticket_key, ticket.summary)
        pr_title = f"[{ticket.ticket_key}] Enable Genie Space for {update.env_name} org {org_id}"
        pr_body = (
            f"Automated PR for Jira ticket **{ticket.ticket_key}**.\n\n"
            f"- Environment: `{update.env_name}`\n"
            f"- Org ID: `{org_id}`\n"
            f"- File: `{update.relative_file_path}`\n"
        )
        pr_url = self._github.create_pr_from_working_tree(
            repo_path=__import__("pathlib").Path(repo.local_path),
            github_repo=repo.github_repo,
            base_branch=repo.base_branch,
            ticket_key=ticket.ticket_key,
            pr_title=pr_title,
            pr_body=pr_body,
            branch_name=branch_name,
            files_to_stage=[update.relative_file_path],
        )
        comment = f"Opened PR for {ticket.ticket_key}: {pr_url}"
        self._jira.post_comment(ticket.ticket_key, comment)
        self._state.set(ticket.ticket_key, TicketStatus.PR_OPENED, pr_url=pr_url)
        self._notifier.notify(pr_title, comment)
        return WorkflowResult(
            ticket_key=ticket.ticket_key,
            status=TicketStatus.PR_OPENED,
            message=comment,
            target_repo=repo.name,
            branch_name=branch_name,
            pr_url=pr_url,
            changed_files=[update.relative_file_path],
        )

    def _handle_bug_investigation(self, ticket: TicketContext, repo: object) -> WorkflowResult:
        from agents_for_automation.core.models import RepoConfig

        assert isinstance(repo, RepoConfig)
        from pathlib import Path

        self._github.ensure_repo_ready(
            repo_path=Path(repo.local_path),
            github_repo=repo.github_repo,
            base_branch=repo.base_branch,
        )
        report, changed_files = investigate_bug(
            llm=self._llm,  # type: ignore[arg-type]
            repo=repo,
            ticket=ticket,
            dry_run=self._settings.dry_run,
        )
        if changed_files:
            branch_name = build_branch_name(ticket.ticket_key, ticket.summary)
            pr_title = f"[{ticket.ticket_key}] Fix: {ticket.summary[:60]}"
            pr_body = (
                f"Automated investigation & fix for **{ticket.ticket_key}**.\n\n"
                f"**Root cause:** {report.root_cause}\n"
                f"**Fix summary:** {report.proposed_fix_summary}\n"
            )
            pr_url = self._github.create_pr_from_working_tree(
                repo_path=__import__("pathlib").Path(repo.local_path),
                github_repo=repo.github_repo,
                base_branch=repo.base_branch,
                ticket_key=ticket.ticket_key,
                pr_title=pr_title,
                pr_body=pr_body,
                branch_name=branch_name,
                files_to_stage=changed_files,
            )
            msg = f"Opened fix PR for {ticket.ticket_key}: {pr_url}"
            self._jira.post_comment(ticket.ticket_key, msg)
            self._state.set(ticket.ticket_key, TicketStatus.PR_OPENED, pr_url=pr_url)
            self._notifier.notify(pr_title, msg)
            return WorkflowResult(
                ticket_key=ticket.ticket_key,
                status=TicketStatus.PR_OPENED,
                message=msg,
                target_repo=repo.name,
                branch_name=branch_name,
                pr_url=pr_url,
                changed_files=changed_files,
            )

        msg = (
            f"Investigation complete for {ticket.ticket_key} (confidence: {report.confidence}).\n"
            f"Root cause: {report.root_cause}\n"
            f"Proposed fix: {report.proposed_fix_summary}"
        )
        self._state.set(ticket.ticket_key, TicketStatus.ESCALATED)
        self._notifier.notify(f"[{ticket.ticket_key}] Investigation Report", msg)
        return WorkflowResult(
            ticket_key=ticket.ticket_key,
            status=TicketStatus.ESCALATED,
            message=msg,
            target_repo=repo.name,
            details=report.model_dump(),
        )
