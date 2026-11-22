"""Invoice Extraction Agent module."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from agents_for_automation.core.base import AgentContext, AgentRunResult
from agents_for_automation.core.manifest import AgentManifest

_CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
}

_VENDOR_RE = re.compile(
    r"^\s*(?:Vendor|From|Supplier|Bill(?:ed)?\s*From)\s*[:\-]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
_INVOICE_NUM_RE = re.compile(
    r"(?:Invoice\s*(?:No\.?|Number|#)|Inv\.?\s*(?:No\.?|#))\s*[:\-]?\s*([A-Za-z0-9\-_/]+)",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"(?:Invoice\s*Date|Date)\s*[:\-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)
_CURRENCY_CODE_RE = re.compile(
    r"(?:Currency\s*[:\-]\s*)?\b(USD|EUR|GBP|INR|CAD|AUD)\b",
    re.IGNORECASE,
)
_SUBTOTAL_RE = re.compile(
    r"^\s*Subtotal\s*[:\-]?\s*([$€£])?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE | re.MULTILINE,
)
_TAX_RE = re.compile(
    r"^\s*Tax(?:\s*\([^)]*\))?\s*[:\-]?\s*([$€£])?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE | re.MULTILINE,
)
_TOTAL_RE = re.compile(
    r"^\s*(?:Grand\s*Total|Total\s*Due|Total\s*Amount|Amount\s*Due|Total)\s*[:\-]?\s*([$€£])?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE | re.MULTILINE,
)


def _parse_amount(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return round(float(raw), 2)
    cleaned = str(raw).replace(",", "").strip()
    for sym in _CURRENCY_SYMBOLS:
        cleaned = cleaned.lstrip(sym).strip()
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def _extract_from_text(text: str) -> dict[str, Any]:
    vendor_match = _VENDOR_RE.search(text)
    inv_match = _INVOICE_NUM_RE.search(text)
    date_match = _DATE_RE.search(text)
    subtotal_match = _SUBTOTAL_RE.search(text)
    tax_match = _TAX_RE.search(text)
    total_match = _TOTAL_RE.search(text)

    currency: str | None = None
    code_match = _CURRENCY_CODE_RE.search(text)
    if code_match:
        currency = code_match.group(1).upper()
    else:
        for m in (total_match, subtotal_match, tax_match):
            if m and m.group(1) in _CURRENCY_SYMBOLS:
                currency = _CURRENCY_SYMBOLS[m.group(1)]
                break

    return {
        "vendor": vendor_match.group(1).strip() if vendor_match else None,
        "invoice_number": inv_match.group(1).strip() if inv_match else None,
        "date": date_match.group(1).strip() if date_match else None,
        "currency": currency or "USD",
        "subtotal": _parse_amount(subtotal_match.group(2)) if subtotal_match else None,
        "tax": _parse_amount(tax_match.group(2)) if tax_match else None,
        "total_amount": _parse_amount(total_match.group(2)) if total_match else None,
        "line_items": [],
    }


def _normalize_json_payload(data: dict[str, Any]) -> dict[str, Any]:
    total_raw = data.get("total_amount", data.get("total"))
    tax_raw = data.get("tax", data.get("tax_amount"))
    date_raw = data.get("date", data.get("invoice_date"))
    return {
        "vendor": str(data["vendor"]).strip() if data.get("vendor") else None,
        "invoice_number": str(data["invoice_number"]).strip() if data.get("invoice_number") else None,
        "date": str(date_raw).strip() if date_raw else None,
        "currency": str(data.get("currency") or "USD").upper(),
        "subtotal": _parse_amount(data.get("subtotal")),
        "tax": _parse_amount(tax_raw),
        "total_amount": _parse_amount(total_raw),
        "line_items": list(data.get("line_items") or []),
    }


def _validate_extracted(extracted: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("vendor", "invoice_number", "total_amount"):
        val = extracted.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"Missing required field: '{field}'.")

    subtotal = extracted.get("subtotal")
    tax = extracted.get("tax")
    total_amount = extracted.get("total_amount")
    line_items: list[dict[str, Any]] = extracted.get("line_items") or []

    if line_items:
        items_sum = 0.0
        for idx, item in enumerate(line_items):
            amount = _parse_amount(item.get("amount", item.get("total")))
            if amount is None:
                qty = item.get("quantity", 1)
                unit_price = _parse_amount(item.get("unit_price"))
                if unit_price is not None:
                    amount = round(float(qty) * unit_price, 2)
            if amount is None:
                errors.append(f"Line item {idx + 1} is missing an amount or unit_price.")
            else:
                items_sum = round(items_sum + amount, 2)

        if subtotal is not None and abs(items_sum - subtotal) > 0.01:
            errors.append(
                f"Line-item sum ({items_sum:.2f}) does not match subtotal ({subtotal:.2f})."
            )
        elif subtotal is None and total_amount is not None:
            expected_from_items = round(items_sum + (tax or 0.0), 2)
            if abs(expected_from_items - total_amount) > 0.01:
                errors.append(
                    f"Line-item sum + tax ({expected_from_items:.2f}) does not match total_amount ({total_amount:.2f})."
                )

    if subtotal is not None and total_amount is not None:
        expected_total = round(subtotal + (tax or 0.0), 2)
        if abs(expected_total - total_amount) > 0.01:
            errors.append(
                f"Subtotal ({subtotal:.2f}) + tax ({(tax or 0.0):.2f}) = {expected_total:.2f}, "
                f"which does not match total_amount ({total_amount:.2f})."
            )

    return errors


class InvoiceExtractionAgent:
    """Extracts and validates invoice fields from JSON or raw text for accounting."""

    def __init__(self, manifest: AgentManifest) -> None:
        self.manifest = manifest

    def run(self, inputs: dict[str, Any], ctx: AgentContext) -> AgentRunResult:
        started = time.perf_counter()
        json_val = inputs.get("json")
        text_val = inputs.get("text")

        if json_val:
            if isinstance(json_val, dict):
                raw_data = json_val
            else:
                raw_data = json.loads(Path(str(json_val)).read_text(encoding="utf-8"))
            extracted = _normalize_json_payload(raw_data)
        elif text_val and str(text_val).strip():
            extracted = _extract_from_text(str(text_val))
        else:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return AgentRunResult(
                agent_name=self.manifest.name,
                status="NEEDS_INFO",
                message="Provide either 'json' (path or dict) or 'text' (raw invoice text).",
                dry_run=ctx.dry_run,
                duration_ms=elapsed_ms,
                outputs={
                    "extracted": {},
                    "validation_errors": ["No invoice input provided."],
                    "accounting_payload": {},
                },
            )

        validation_errors = _validate_extracted(extracted)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if validation_errors:
            return AgentRunResult(
                agent_name=self.manifest.name,
                status="VALIDATION_FAILED",
                message=f"Invoice validation failed: {'; '.join(validation_errors)}",
                dry_run=ctx.dry_run,
                time_saved_minutes=0,
                duration_ms=elapsed_ms,
                outputs={
                    "extracted": extracted,
                    "validation_errors": validation_errors,
                    "accounting_payload": {},
                },
            )

        accounting_payload = {
            "vendor": extracted["vendor"],
            "invoice_number": extracted["invoice_number"],
            "invoice_date": extracted["date"],
            "currency": extracted["currency"],
            "subtotal": extracted["subtotal"],
            "tax": extracted["tax"],
            "total_amount": extracted["total_amount"],
            "line_items": extracted["line_items"],
            "dry_run": ctx.dry_run,
        }

        return AgentRunResult(
            agent_name=self.manifest.name,
            status="COMPLETED",
            message=(
                f"Extracted and validated invoice {extracted['invoice_number']} "
                f"from {extracted['vendor']} ({extracted['currency']} {extracted['total_amount']:.2f})."
            ),
            dry_run=ctx.dry_run,
            time_saved_minutes=self.manifest.estimated_time_saved_minutes,
            duration_ms=elapsed_ms,
            outputs={
                "extracted": extracted,
                "validation_errors": [],
                "accounting_payload": accounting_payload,
            },
        )


def create_agent(manifest: AgentManifest) -> InvoiceExtractionAgent:
    """Factory function referenced by `entrypoint: agent:create_agent` in agent.yaml."""
    return InvoiceExtractionAgent(manifest=manifest)
