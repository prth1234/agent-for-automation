# Document Generator Agent (`doc_generator`)

Generates structured Markdown documents from built-in templates or custom `template_text` and JSON payloads, validating all placeholders before rendering.

## Metadata

| Field | Value |
| :--- | :--- |
| **Category** | `templates` |
| **Status** | `beta` |
| **Triggers** | `cli`, `webhook:doc` |
| **Permissions** | `docs:write`, `llm:invoke` |
| **Est. time saved** | `35` minutes / run |

## Built-in Templates

- **`board_resolution`**: `company_name`, `effective_date`, `resolution_subject`, `authorized_officer`, `chair_name`
- **`offer_letter`**: `offer_date`, `candidate_name`, `company_name`, `role_title`, `manager_name`, `start_date`, `base_salary`
- **`compliance_filing`**: `entity_name`, `jurisdiction`, `filing_type`, `reporting_period`, `due_date`, `preparer_name`

## What it does

1. Resolves the template from `template_text` (custom) or `template` (built-in, defaults to `board_resolution`).
2. Extracts all `{placeholder}` fields from the template and verifies every field is present and non-empty.
3. Returns `NEEDS_INFO` with `missing_fields` if the template is unknown or any required placeholders are missing; otherwise renders and returns the Markdown document.

## Inputs

| Input | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `template` | `string` | No | `board_resolution` | Built-in template name (`board_resolution`, `offer_letter`, `compliance_filing`) or custom identifier |
| `json` | `path` | No | — | Path to a JSON file (or inline dict) with template name, optional `template_text`, and field values |

## Outputs & Statuses

- **`COMPLETED`**: Document rendered (outputs include `template` and `document_markdown`).
- **`NEEDS_INFO`**: Unknown template name or missing placeholder fields (`missing_fields`).

## Run locally

```bash
afa info doc_generator
afa run doc_generator --json src/agents_for_automation/agents/doc_generator/examples/sample_input.json
```
