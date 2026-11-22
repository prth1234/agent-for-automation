# Document Generator Agent (`doc_generator`)

Generates structured legal and compliance Markdown documents from built-in templates (`board_resolution`, `offer_letter`, `compliance_filing`) or custom `template_text` and JSON payloads.

## Built-in Templates

- `board_resolution`: `company_name`, `effective_date`, `resolution_subject`, `authorized_officer`, `chair_name`
- `offer_letter`: `offer_date`, `candidate_name`, `company_name`, `role_title`, `manager_name`, `start_date`, `base_salary`
- `compliance_filing`: `entity_name`, `jurisdiction`, `filing_type`, `reporting_period`, `due_date`, `preparer_name`

## Run locally

```bash
afa info doc_generator
afa run doc_generator --json src/agents_for_automation/agents/doc_generator/examples/sample_input.json
```
