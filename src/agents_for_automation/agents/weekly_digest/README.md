# Weekly Digest Agent (`weekly_digest`)

Summarises recent tickets, pull requests, and automation metrics into a structured Markdown digest and dispatches it via the shared `NotifierConnector` (SES / Teams).

## Metadata

| Field | Value |
| :--- | :--- |
| **Category** | `reporting` |
| **Status** | `beta` |
| **Triggers** | `schedule:weekly`, `cli` |
| **Permissions** | `ses:send`, `teams:write` |
| **Est. time saved** | `20` minutes / run |

## What it does

1. Loads `team` (default `Thorium` in `agent.yaml`), `tickets`, and `prs` from the input JSON or CLI flags.
2. Formats a Markdown digest (`# Weekly Digest — <team>`) listing ticket counts, ticket keys/summaries/statuses, and PR titles/URLs.
3. Sends the digest with title `[<team>] Weekly Automation Digest` via `NotifierConnector`.

## Inputs

| Input | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `team` | `string` | No | `Thorium` | Team name for the digest header |
| `json` | `path` | No | — | Path to a JSON file with `team`, `tickets`, and `prs` lists |

## Outputs & Statuses

- **`COMPLETED`**: Digest generated and sent (outputs: `team`, `ticket_count`, `pr_count`, `digest_markdown`).

## Run locally

```bash
afa info weekly_digest
afa run weekly_digest --json src/agents_for_automation/agents/weekly_digest/examples/sample_input.json
```
