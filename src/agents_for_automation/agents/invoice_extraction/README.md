# Invoice Extraction Agent (`invoice_extraction`)

Extracts structured fields from JSON or raw invoice text, validates required fields and arithmetic, and outputs a normalized accounting payload.

## Metadata

| Field | Value |
| :--- | :--- |
| **Category** | `parsing` |
| **Status** | `beta` |
| **Triggers** | `cli`, `webhook:invoice` |
| **Permissions** | `llm:invoke`, `accounting:write` |
| **Est. time saved** | `25` minutes / run |

## What it does

1. Accepts either structured JSON (`json`) or raw invoice text (`text`). Returns `NEEDS_INFO` if neither is provided.
2. Extracts and normalizes `vendor`, `invoice_number`, `date`, `currency` (defaults to `USD`, infers from `$`, `€`, `£` or currency codes), `subtotal`, `tax`, `total_amount`, and `line_items`.
3. Validates that required fields (`vendor`, `invoice_number`, `total_amount`) are present and checks:
   - Line-item amounts (`amount` or `quantity * unit_price`) sum to `subtotal` (or `total_amount - tax`).
   - `subtotal + tax` matches `total_amount` within `0.01`.
4. Returns `VALIDATION_FAILED` with detailed `validation_errors` on mismatch, or `COMPLETED` with the normalized `accounting_payload`.

## Inputs

| Input | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `json` | `path` | No* | Path to a JSON file (or dict) containing structured invoice data |
| `text` | `string` | No* | Raw invoice text to parse into structured fields |

\* Provide either `json` or `text`.

## Outputs & Statuses

- **`COMPLETED`**: Validation passed (outputs: `extracted`, `validation_errors: []`, `accounting_payload`).
- **`VALIDATION_FAILED`**: Missing required fields or arithmetic mismatch (outputs: `extracted`, `validation_errors`, `accounting_payload: {}`).
- **`NEEDS_INFO`**: No `json` or `text` input provided.

## Run locally

```bash
afa info invoice_extraction
afa run invoice_extraction --json src/agents_for_automation/agents/invoice_extraction/examples/sample_input.json
```
