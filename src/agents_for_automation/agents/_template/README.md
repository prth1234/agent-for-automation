# Template Agent

Copy this folder to create a new agent module:

```bash
cp -r src/agents_for_automation/agents/_template \
      src/agents_for_automation/agents/my_agent
```

1. Update `agent.yaml` with your agent's `name`, `description`, `inputs`, and `permissions`.
2. Implement your logic in `agent.py` using `ctx.integrations` (Jira, GitHub, Notifier).
3. Add a sample payload in `examples/sample_input.json` and tests in `tests/`.
4. Run `afa list` and `afa info my_agent` to verify auto-discovery.
