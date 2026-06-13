# Invoice Registry

## Identity

Use `invoice_number` as the primary invoice identity.

Rules:

- The registry accepts PDF and image invoices (.pdf, .jpg, .jpeg, .png, .webp).
- Scripts must not extract invoice fields from PDF content with regex, text
  scraping, OCR, or PDF parsing libraries. The Agent reads the PDF and submits
  extracted fields explicitly through `omp invoice submit`.
- `submit` rejects duplicate `invoice_number`.
- Files without a readable `invoice_number` stay pending.
- File SHA-256 prevents importing the same file twice.
- Source IDs and source paths are audit fields, not identity fields.

## Required Fields

`submit` requires these JSON fields:

| Field | Meaning |
|---|---|
| `invoice_number` | Invoice number; primary identity. |
| `invoice_date` | `YYYY-MM-DD`. |
| `amount` | Total amount, numeric. |
| `seller` | Seller name. |

Optional fields:

| Field | Meaning |
|---|---|
| `purchase_content` | Goods or service description. |
| `tax_rate` | Tax-rate marker as shown on the invoice. |
| `currency` | Defaults to `CNY`; use values such as `USD` when needed. |

## Purpose

Allowed values:

| Purpose | Meaning |
|---|---|
| `claim` | Intended for normal reimbursement. |
| `substitute` | Held as a future substitute invoice. |

The Agent decides `purpose` after reading the owner's `substitute_rule`.

## Status

Allowed values:

| Status | Meaning |
|---|---|
| `available` | Usable by reimbursement workflows. |
| `used` | Already used or reserved by a reimbursement workflow. |
| `archived` | Hidden from default list output. |

Default `omp invoice list` returns `available` invoices. Use `--status all` to
see non-archived `available` and `used` invoices, and add `--include-archived`
when archived records are needed.

## Pending Discard

Use `omp invoice discard --id <id> --reason <text>` when a pending item is a
duplicate delivery, a non-invoice attachment, or otherwise should not enter the
registry.

Rules:

- `discard` deletes only the registry's copied pending file.
- `discard` never deletes the original `source_path`.
- `discard` records a `pending_discarded` event with the reason.
