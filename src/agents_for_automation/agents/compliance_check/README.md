# Compliance Check Agent (`compliance_check`)

Validates submitted document sets against built-in rulesets or a custom `required_documents` list for missing documents, inconsistent entity names/IDs, and expired dates.

## Metadata

| Field | Value |
| :--- | :--- |
| **Category** | `validation` |
| **Status** | `beta` |
| **Triggers** | `cli`, `webhook:compliance` |
| **Permissions** | `docs:read`, `ses:send` |
| **Est. time saved** | `30` minutes / run |

## Built-in Rulesets

- **`vendor_onboarding`**: `w9`, `soc2_report`, `insurance_certificate`, `msa`
- **`release_readiness`**: `security_signoff`, `qa_signoff`, `rollback_plan`, `changelog`

## What it does

1. Loads required document types from `required_documents` (if provided) or a built-in `ruleset` (defaults to `vendor_onboarding`). Returns `NEEDS_INFO` if the ruleset is unknown and no `required_documents` list is given.
2. Checks submitted `documents` for:
   - **Missing documents**: required types not present in the submission.
   - **Inconsistencies**: mismatched entity names or IDs across submitted documents.
   - **Expired documents**: expiration dates earlier than today's date.
3. If any issues are found, returns `ISSUES_FOUND` and sends an alert summary via `NotifierConnector`.

## Inputs

| Input | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `ruleset` | `string` | No | `vendor_onboarding` | Built-in ruleset name (`vendor_onboarding` or `release_readiness`) |
| `json` | `path` | No | — | Path to a JSON file containing `ruleset` (or `required_documents`) and `documents` |

## Outputs & Statuses

- **`COMPLETED`**: All checks passed (`passed: true`, empty issue lists).
- **`ISSUES_FOUND`**: One or more checks failed (outputs: `passed: false`, `missing_documents`, `inconsistencies`, `expired_documents`).
- **`NEEDS_INFO`**: Unknown ruleset and no custom `required_documents` provided.

## Run locally

```bash
afa info compliance_check
afa run compliance_check --json src/agents_for_automation/agents/compliance_check/examples/sample_input.json
```
