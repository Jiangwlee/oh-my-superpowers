"""Invoice field validation for mail-pipeline.

Field recognition itself is cognitive work and belongs to the calling AI
agent (it reads the staged PDF and submits fields via `submit`). This module
only validates and cross-checks what the agent submitted.
"""

from __future__ import annotations

from datetime import date

INVOICE_REQUIRED_FIELDS = ["invoice_date", "invoice_number", "amount", "tax_rate", "purchase_content", "seller"]


def validate_invoice_fields(fields: dict) -> dict:
    """Validate agent-submitted invoice fields.

    `amount` is the tax-inclusive total (价税合计). Raises ValueError on
    missing or malformed fields.
    """
    if not isinstance(fields, dict):
        raise ValueError("fields must be a JSON object")
    missing = [key for key in INVOICE_REQUIRED_FIELDS if not str(fields.get(key) or "").strip()]
    if missing:
        raise ValueError("missing invoice fields: " + ", ".join(missing))
    try:
        date.fromisoformat(str(fields["invoice_date"]))
        float(fields["amount"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"malformed invoice field: {exc}") from exc
    keys = INVOICE_REQUIRED_FIELDS + ["confidence", "currency"]
    return {key: fields[key] for key in keys if key in fields}


def cross_check(fields: dict, provider_meta: dict) -> list[str]:
    """Compare agent-submitted fields against provider metadata.

    Returns a list of mismatch descriptions; empty when consistent or when
    no provider metadata is available.
    """
    mismatches: list[str] = []
    if not provider_meta:
        return mismatches
    meta_number = str(provider_meta.get("invoice_number") or "").strip()
    if meta_number and meta_number != str(fields["invoice_number"]).strip():
        mismatches.append(f"invoice_number: agent={fields['invoice_number']} provider={meta_number}")
    meta_amount = provider_meta.get("amount")
    if meta_amount is not None and abs(float(meta_amount) - float(fields["amount"])) > 0.01:
        mismatches.append(f"amount: agent={fields['amount']} provider={meta_amount}")
    # Provider dates reflect issuing-request time, not the invoice date on the
    # PDF face (observed on nuonuo) — only strong identifiers are compared.
    return mismatches
