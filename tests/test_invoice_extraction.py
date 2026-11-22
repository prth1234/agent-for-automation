"""Unit tests for the invoice_extraction agent module."""
from __future__ import annotations

import json
from pathlib import Path

from agents_for_automation.config import Settings
from agents_for_automation.runtime import run_agent


def test_invoice_extraction_valid_json(tmp_path: Path) -> None:
    sample = tmp_path / "invoice.json"
    sample.write_text(
        json.dumps(
            {
                "vendor": "Acme Cloud Services Inc.",
                "invoice_number": "INV-2026-0418",
                "date": "2026-11-15",
                "currency": "USD",
                "line_items": [
                    {"description": "Compute", "amount": 1200.00},
                    {"description": "Storage", "amount": 300.00},
                ],
                "subtotal": 1500.00,
                "tax": 120.00,
                "total_amount": 1620.00,
            }
        ),
        encoding="utf-8",
    )
    result = run_agent(
        "invoice_extraction",
        inputs={"json": str(sample)},
        settings=Settings(dry_run=True),
    )
    assert result.agent_name == "invoice_extraction"
    assert result.status == "COMPLETED"
    assert result.dry_run is True
    assert result.time_saved_minutes == 25
    assert result.outputs["validation_errors"] == []
    assert result.outputs["extracted"]["vendor"] == "Acme Cloud Services Inc."
    assert result.outputs["extracted"]["total_amount"] == 1620.00
    assert result.outputs["accounting_payload"]["invoice_number"] == "INV-2026-0418"


def test_invoice_extraction_raw_text() -> None:
    raw_text = """
    Vendor: Globex Logistics LLC
    Invoice Number: GLX-9081
    Invoice Date: 2026-11-10
    Currency: EUR
    Subtotal: €500.00
    Tax: €50.00
    Total: €550.00
    """
    result = run_agent(
        "invoice_extraction",
        inputs={"text": raw_text},
        settings=Settings(dry_run=True),
    )
    assert result.status == "COMPLETED"
    extracted = result.outputs["extracted"]
    assert extracted["vendor"] == "Globex Logistics LLC"
    assert extracted["invoice_number"] == "GLX-9081"
    assert extracted["date"] == "2026-11-10"
    assert extracted["currency"] == "EUR"
    assert extracted["subtotal"] == 500.00
    assert extracted["tax"] == 50.00
    assert extracted["total_amount"] == 550.00
    assert result.outputs["validation_errors"] == []


def test_invoice_extraction_mismatched_total_fails_validation() -> None:
    result = run_agent(
        "invoice_extraction",
        inputs={
            "json": {
                "vendor": "Initech Corp",
                "invoice_number": "INI-1002",
                "date": "2026-11-01",
                "currency": "USD",
                "line_items": [{"description": "Consulting", "amount": 400.00}],
                "subtotal": 400.00,
                "tax": 40.00,
                "total_amount": 500.00,
            }
        },
        settings=Settings(dry_run=True),
    )
    assert result.status == "VALIDATION_FAILED"
    assert len(result.outputs["validation_errors"]) == 1
    assert "does not match total_amount" in result.outputs["validation_errors"][0]
    assert result.outputs["accounting_payload"] == {}
