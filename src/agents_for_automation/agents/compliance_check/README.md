# Compliance Check Agent (`compliance_check`)

Validates submitted compliance documents against built-in rulesets (`vendor_onboarding`, `release_readiness`) or a custom `required_documents` list for missing documents, inconsistent entity names/IDs, and expired dates, sending a notification via `NotifierConnector` when issues are flagged.

## Run locally

```bash
afa info compliance_check
afa run compliance_check --json src/agents_for_automation/agents/compliance_check/examples/sample_input.json
```
