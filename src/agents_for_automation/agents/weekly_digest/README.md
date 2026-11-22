# Weekly Digest Agent (`weekly_digest`)

Summarises tickets, PRs, and automation metrics into a clean Markdown digest and sends it via the shared `NotifierConnector` (SES / Teams).

## Run locally

```bash
afa info weekly_digest
afa run weekly_digest --json src/agents_for_automation/agents/weekly_digest/examples/sample_input.json
```
