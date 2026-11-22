<div align="center">
  <img src="docs/assets/hero.svg?v=3" alt="Agents for Automation" width="100%" />
</div>

<br/>

## The idea

Every team has repetitive work: triaging tickets, extracting data from documents, drafting reports, answering the same questions. Most automations get built once, live in one person's repo, and never get reused.

**AFA turns each automation into a self-contained agent module that you can install, configure and run.**

<div align="center">
  <img src="docs/assets/pillars.svg?v=3" alt="Modular, config-driven, safe and measurable" width="100%" />
</div>

## How it works

<div align="center">
  <img src="docs/assets/flow.svg?v=3" alt="Trigger to registry to agent to integrations to result" width="100%" />
</div>

A trigger arrives from a webhook, the CLI or a schedule. The registry finds the right agent by reading its `agent.yaml`. The agent does the work through shared integrations, and the result lands as a pull request, a ticket update or a notification.

## Example: the support ticket agent

A customer raises `SQ-123`: *"Please onboard org 4821 to Genie."* The agent handles it end to end, and a human reviews the pull request before anything merges.

<div align="center">
  <img src="docs/assets/sequence.svg?v=3" alt="Support ticket agent sequence" width="100%" />
</div>

Turnaround drops from about a day to minutes.

<details>
<summary><b>Step-by-step breakdown</b></summary>

<br/>

1. The Jira webhook hits `POST /webhooks/jira`.
2. The registry loads the `support_ticket` agent.
3. The classifier labels the ticket as Genie onboarding, bug investigation or unknown.
4. The handler finds the repo in `config/repos.yaml`, edits Terraform and opens a pull request.
5. Jira is updated with the PR link and the team is notified.
6. The ticket state is stored so it is never processed twice.

</details>

## Quick start

```bash
afa list                                # browse available agents
afa info support_ticket                 # inputs, permissions and config
afa run support_ticket --ticket SQ-123  # run on a live ticket
afa serve                               # start the webhook server
```

## Agent marketplace

<div align="center">
  <img src="docs/assets/marketplace.svg?v=3" alt="Available and planned agents" width="100%" />
</div>

## Build your own agent

```bash
# 1. Copy the template
cp -r src/agents_for_automation/agents/_template \
      src/agents_for_automation/agents/my_agent

# 2. Describe it in agent.yaml and implement it in agent.py

# 3. Confirm it is discovered
afa list
```

<details>
<summary><b>Project structure</b></summary>

```
src/agents_for_automation/
  core/            base classes, registry, manifest schema
  integrations/    Jira, GitHub, LLM, email, Slack and Teams
  agents/
    support_ticket/
    weekly_digest/
    _template/
```

</details>

## Principles

- **Human in the loop.** Agents propose, people approve.
- **Measurable.** Every run logs time saved and duration, so ROI is visible.
- **Safe by default.** Least-privilege credentials, retry and step caps, no silent failures.
- **Handover-friendly.** Rules and templates live in config, not code.

<br/>

<div align="center">
  <img src="docs/assets/footer.svg?v=3" alt="Build once. Reuse everywhere." width="100%" />
</div>
