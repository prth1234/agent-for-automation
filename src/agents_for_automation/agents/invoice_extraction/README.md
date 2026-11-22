# Invoice Extraction Agent (`invoice_extraction`)

Extracts structured fields (`vendor`, `invoice_number`, `date`, `currency`, `subtotal`, `tax`, `total_amount`, `line_items`) from structured JSON or raw invoice text, validates required fields and line-item/subtotal/tax arithmetic, and produces a normalized accounting payload.

## Run locally

```bash
afa info invoice_extraction
afa run invoice_extraction --json src/agents_for_automation/agents/invoice_extraction/examples/sample_input.json
```
