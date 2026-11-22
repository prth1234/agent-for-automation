# Support Ticket Agent (`support_ticket`)

Automates triage and resolution of Jira Support Question (`SQ`) tickets.

## What it does

1. Classifies incoming tickets into **Genie onboarding**, **Bug investigation**, or **Unknown**.
2. Routes to the matching repository in `config/repos.yaml`.
3. For Genie onboarding: adds the org ID to Terraform `variables.tf` and opens a GitHub PR.
4. For bug investigation: searches the codebase with `ripgrep` + Bedrock and proposes a fix PR or investigation report.
5. Updates Jira with the PR link and notifies the team via SES / Teams.
6. Persists ticket state in `.afa_state.json` to prevent duplicate runs.

## Run locally

```bash
afa info support_ticket
afa run support_ticket --json src/agents_for_automation/agents/support_ticket/examples/sq_32775.json
afa run support_ticket --ticket SQ-32775 --live
```
