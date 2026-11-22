# Agents for Automation (AFA)

A marketplace of ready-to-use automation agents. Browse, install, configure and
run workflows for your team's daily work, without rebuilding the plumbing each time.

## The idea

Every team has repetitive work: triaging tickets, extracting data from documents,
drafting reports, answering the same questions. Most automations get built once,
live in one person's repo, and never get reused.

AFA turns each automation into a self-contained **agent module** with:

- a manifest (`agent.yaml`) describing what it does, its inputs and the permissions it needs
- reusable integrations (Jira, GitHub, Slack/Teams, email, LLMs) shared across all agents
- config-driven rules, so non-technical teams can tune behaviour without touching code
- tests, examples and a README so anyone can adopt it in minutes

## How it works

```
Trigger (webhook / CLI / schedule)
        ↓
   Agent Registry  →  finds the right agent
        ↓
   Agent module    →  uses shared integrations (Jira, GitHub, LLM, SES/Teams)
        ↓
   Result          →  PR / Jira update / Slack message / report
```

## Example: Support Ticket Agent

A customer raises `SQ-123`: "Please onboard org 4821 to Genie."

1. The Jira webhook hits `POST /webhooks/jira`.
2. The registry loads the `support_ticket` agent.
3. The classifier labels it **Genie onboarding** (the other labels are *Bug investigation* and *Unknown*).
4. The handler finds the right repo in `config/repos.yaml`, adds the org ID to Terraform, and opens a pull request.
5. Jira is updated with the PR link and the team gets an email.
6. The ticket state is stored so it is never processed twice.

Turnaround drops from about a day to minutes, and a human reviews the PR before it merges.

Run it locally:

```bash
afa list                              # see all available agents
afa info support_ticket               # inputs, permissions, config
afa run support_ticket --ticket SQ-123
afa run support_ticket --json src/agents_for_automation/agents/support_ticket/examples/sq_32775.json
afa serve                             # start the webhook server
```

## Add your own agent

```bash
cp -r src/agents_for_automation/agents/_template \
      src/agents_for_automation/agents/my_agent
```

Edit `agent.yaml` and `agent.py`, add tests, and `afa list` will pick it up automatically.

## Potential agents

| Agent | Status | What it automates |
|---|---|---|
| `support_ticket` | `stable` | Triage Jira tickets, open PRs for fixes and onboarding |
| `weekly_digest` | `beta` | Summarise tickets, PRs or metrics into a digest notification |
| `invoice_extraction` | planned | Read PDFs, validate fields, push to accounting |
| `doc_generator` | planned | Draft resolutions, letters and filings from templates |
| `compliance_check` | planned | Flag missing or inconsistent documents |
| `slack_qa` | planned | Answer staff questions from internal SOPs, with sources |

## Principles

- **Human in the loop:** agents propose, people approve.
- **Measurable:** every run logs time saved and duration, so ROI is visible.
- **Safe by default:** least-privilege credentials, retry and step caps, no silent failures.
- **Handover-friendly:** rules and templates live in config, not code.
