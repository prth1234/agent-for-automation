# Support Ticket Agent (`support_ticket`)

Automates triage and resolution of Jira Support Question (`SQ`) tickets, from classification to pull request creation and team notification.

## Metadata

| Field | Value |
| :--- | :--- |
| **Category** | `engineering` |
| **Status** | `stable` |
| **Triggers** | `webhook:jira`, `cli` |
| **Permissions** | `jira:read`, `jira:write`, `github:pr`, `ses:send`, `bedrock:invoke` |
| **Config files** | `config/repos.yaml` |
| **Est. time saved** | `30` minutes / run |

## What it does

1. Classifies incoming tickets into **Genie onboarding**, **Bug investigation**, or **Unknown**.
2. Routes to the matching repository configured in `config/repos.yaml`.
3. For **Genie onboarding**: adds the org ID to Terraform `variables.tf` and opens a GitHub PR.
4. For **Bug investigation**: searches the codebase with `ripgrep` + Bedrock and proposes a fix PR or investigation report.
5. Updates Jira with the PR link and notifies the team via SES / Teams.
6. Persists ticket state in `.afa_state.json` to prevent duplicate runs.

## Inputs

| Input | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `ticket` | `string` | No* | Jira ticket key to fetch and process (e.g. `SQ-32775`) |
| `json` | `path` | No* | Path to a local `TicketContext` JSON payload |

\* Provide either `ticket` or `json`.

## Run locally

```bash
afa info support_ticket
afa run support_ticket --json src/agents_for_automation/agents/support_ticket/examples/sq_32775.json
afa run support_ticket --ticket SQ-32775 --live
```
