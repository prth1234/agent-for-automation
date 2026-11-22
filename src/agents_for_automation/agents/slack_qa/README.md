# Slack Q&A Agent (`slack_qa`)

Answers Slack questions grounded in internal Standard Operating Procedures (SOPs) with exact source citations, or returns a low-confidence escalation message when no SOP matches.

## Metadata

| Field | Value |
| :--- | :--- |
| **Category** | `chatops` |
| **Status** | `beta` |
| **Triggers** | `cli`, `webhook:slack` |
| **Permissions** | `sop:read`, `slack:write`, `llm:invoke` |
| **Est. time saved** | `10` minutes / run |

## What it does

1. Reads `question` from CLI flags or a JSON payload. Returns `NEEDS_INFO` if `question` is missing.
2. Loads SOPs from the payload (`sops` list) or falls back to built-in `DEFAULT_SOPS`:
   - `sops/deployment.md` — Production Deployment and Rollback
   - `sops/oncall_escalation.md` — On-Call Escalation Policy
   - `sops/access_requests.md` — VPN and Production Access
3. Ranks SOP sections by keyword overlap (filtering stopwords) and selects up to the top 3 matching sections.
4. Returns a grounded Markdown answer with deduplicated `sources` citations and a `confidence` score (`0.0`–`1.0`), or an escalation message pointing to `#ops-help` / on-call if no section matches.
5. Dispatches the answer via `NotifierConnector`.

## Inputs

| Input | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `question` | `string` | No* | Question asked in Slack to answer from internal SOPs |
| `json` | `path` | No* | Path to a JSON file with `question` and optional `sops` list (`title`, `source`, `content`) |

\* Either `question` or `json` containing `question` must be provided.

## Outputs & Statuses

- **`COMPLETED`**: Answer generated (includes `question`, `answer`, `sources`, and `confidence` in `outputs`).
- **`NEEDS_INFO`**: Missing `question` input.

## Run locally

```bash
afa info slack_qa
afa run slack_qa --question "How do I roll back a bad production deploy?"
afa run slack_qa --json src/agents_for_automation/agents/slack_qa/examples/sample_input.json
```
